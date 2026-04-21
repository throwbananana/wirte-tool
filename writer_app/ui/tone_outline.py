import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from writer_app.controllers.base_controller import BaseController
from writer_app.core.commands import UpdateToneOutlineCommand
from writer_app.core.tone_outline import (
    DEFAULT_INTERACTION_TYPE,
    DEFAULT_NODE_TYPE,
    DEFAULT_NOTE_TYPE,
    DEFAULT_PLOT_LINE_UID,
    DEFAULT_SEGMENT_ARC,
    DEFAULT_SEGMENT_CURVE,
    INTERACTION_TYPE_LABELS,
    NODE_TYPE_LABELS,
    NOTE_TYPE_LABELS,
    analyze_merge_conflicts,
    axis_in_segment,
    build_axis_nodes_from_scenes,
    build_line_summary,
    build_plot_summary,
    build_relation_summary,
    build_timeline_summary,
    clone_tone_outline,
    duplicate_segment,
    ensure_tone_outline_defaults,
    get_axis_index_map,
    get_display_segments,
    get_next_tone_line_color,
    get_interaction_label,
    get_node_type_label,
    get_note_type_label,
    merge_adjacent_segments,
    split_segment,
)


def _range_text(axis_map, segment):
    start_uid = segment.get("start_axis_uid")
    end_uid = segment.get("end_axis_uid")
    start_text = axis_map.get(start_uid, {}).get("title", "未设置")
    if not end_uid:
        return start_text
    end_text = axis_map.get(end_uid, {}).get("title", "未设置")
    return f"{start_text} -> {end_text}"


def _preview_text(value, limit=24, empty="无"):
    text = str(value or "").strip().replace("\r", " ").replace("\n", " / ")
    if not text:
        return empty
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1]}…"


INTERACTION_TYPE_OPTIONS = list(INTERACTION_TYPE_LABELS.items())
INTERACTION_LABEL_TO_TYPE = {label: key for key, label in INTERACTION_TYPE_OPTIONS}
NODE_TYPE_OPTIONS = list(NODE_TYPE_LABELS.items())
NODE_LABEL_TO_TYPE = {label: key for key, label in NODE_TYPE_OPTIONS}
NOTE_TYPE_OPTIONS = list(NOTE_TYPE_LABELS.items())
NOTE_LABEL_TO_TYPE = {label: key for key, label in NOTE_TYPE_OPTIONS}


def find_points_in_selection(point_positions, line_uid, segment_uid, start_x, start_y, end_x, end_y):
    if not line_uid or not segment_uid:
        return []
    left, right = sorted((float(start_x), float(end_x)))
    top, bottom = sorted((float(start_y), float(end_y)))
    matches = [
        item
        for item in point_positions or []
        if item.get("line_uid") == line_uid
        and item.get("segment_uid") == segment_uid
        and left <= float(item.get("x", -10**9)) <= right
        and top <= float(item.get("y", -10**9)) <= bottom
    ]
    matches.sort(key=lambda item: (float(item.get("x", 0)), float(item.get("y", 0))))
    return [item.get("point_uid", "") for item in matches if item.get("point_uid")]


def find_virtual_point_axes(axis_nodes, segment, axis_index_map):
    if not segment:
        return []
    start_uid = segment.get("start_axis_uid")
    end_uid = segment.get("end_axis_uid") or start_uid
    if start_uid not in axis_index_map or end_uid not in axis_index_map:
        return []
    start_index = axis_index_map[start_uid]
    end_index = axis_index_map[end_uid]
    if end_index < start_index:
        start_index, end_index = end_index, start_index
    occupied_axis_uids = {
        point.get("axis_uid")
        for point in segment.get("points", [])
        if point.get("axis_uid") in axis_index_map
    }
    return [
        axis.get("uid", "")
        for axis in axis_nodes[start_index:end_index + 1]
        if axis.get("uid") and axis.get("uid") not in occupied_axis_uids
    ]


class ToneOutlineCanvas(tk.Canvas):
    def __init__(
        self,
        parent,
        on_axis_selected,
        on_segment_selected,
        on_point_selected,
        on_points_selected,
        on_context_requested,
        on_interaction_selected,
        on_segment_arc_drag,
        on_drag_preview,
        on_point_drag,
        on_point_drag_preview,
        on_interaction_created,
        on_interaction_retarget,
        on_interaction_preview,
        theme_manager=None,
        **kwargs,
    ):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.on_axis_selected = on_axis_selected
        self.on_segment_selected = on_segment_selected
        self.on_point_selected = on_point_selected
        self.on_points_selected = on_points_selected
        self.on_context_requested = on_context_requested
        self.on_interaction_selected = on_interaction_selected
        self.on_segment_arc_drag = on_segment_arc_drag
        self.on_drag_preview = on_drag_preview
        self.on_point_drag = on_point_drag
        self.on_point_drag_preview = on_point_drag_preview
        self.on_interaction_created = on_interaction_created
        self.on_interaction_retarget = on_interaction_retarget
        self.on_interaction_preview = on_interaction_preview
        self.theme_manager = theme_manager
        self.data = None
        self.selected_axis_uid = ""
        self.selected_line_uid = ""
        self.selected_segment_uid = ""
        self.selected_point_uid = ""
        self.selected_point_uids = []
        self.selected_interaction_uid = ""
        self._axis_positions = {}
        self._axis_slots = {}
        self._point_positions = []
        self._virtual_point_positions = []
        self._chart_bounds = (0, 0, 0)
        self._chart_x_bounds = (0, 0)
        self._dragging_boundary = None
        self._dragging_point = None
        self._interaction_arm = None
        self._dragging_interaction = None
        self._selection_box = None
        self._apply_theme()
        self.bind("<ButtonPress-1>", self._handle_press)
        self.bind("<B1-Motion>", self._handle_drag)
        self.bind("<ButtonRelease-1>", self._handle_release)
        self.bind("<Button-3>", self._handle_context_menu)
        self.bind("<Configure>", lambda _event: self.refresh())

    def _theme_color(self, key, fallback):
        if not self.theme_manager:
            return fallback
        try:
            return self.theme_manager.get_color(key)
        except Exception:
            return fallback

    def _apply_theme(self):
        self.configure(bg=self._theme_color("canvas_bg", "#FFFFFF"))

    def set_state(
        self,
        data,
        selected_axis_uid="",
        selected_line_uid="",
        selected_segment_uid="",
        selected_point_uid="",
        selected_point_uids=None,
        selected_interaction_uid="",
    ):
        self.data = clone_tone_outline(data or {})
        self.selected_axis_uid = selected_axis_uid or ""
        self.selected_line_uid = selected_line_uid or ""
        self.selected_segment_uid = selected_segment_uid or ""
        self.selected_point_uid = selected_point_uid or ""
        self.selected_point_uids = [
            point_uid for point_uid in (selected_point_uids or []) if point_uid
        ]
        if self.selected_point_uid and self.selected_point_uid not in self.selected_point_uids:
            self.selected_point_uids.insert(0, self.selected_point_uid)
        self.selected_interaction_uid = selected_interaction_uid or ""
        self.refresh()

    def update_selection(
        self,
        selected_axis_uid="",
        selected_line_uid="",
        selected_segment_uid="",
        selected_point_uid="",
        selected_point_uids=None,
        selected_interaction_uid="",
    ):
        self.selected_axis_uid = selected_axis_uid or ""
        self.selected_line_uid = selected_line_uid or ""
        self.selected_segment_uid = selected_segment_uid or ""
        self.selected_point_uid = selected_point_uid or ""
        self.selected_point_uids = [
            point_uid for point_uid in (selected_point_uids or []) if point_uid
        ]
        if self.selected_point_uid and self.selected_point_uid not in self.selected_point_uids:
            self.selected_point_uids.insert(0, self.selected_point_uid)
        self.selected_interaction_uid = selected_interaction_uid or ""
        self.refresh()

    def arm_interaction_creation(
        self,
        source_line_uid,
        source_segment_uid,
        source_point_uid,
        axis_uid,
        interaction_type,
    ):
        self._interaction_arm = {
            "source_line_uid": source_line_uid,
            "source_segment_uid": source_segment_uid,
            "source_point_uid": source_point_uid,
            "axis_uid": axis_uid,
            "interaction_type": interaction_type or DEFAULT_INTERACTION_TYPE,
        }
        self._dragging_interaction = None
        self.delete("interaction-preview")
        self._emit_interaction_preview("已进入箭头拖拽模式：请从当前点拖到同轴的其他线段。")

    def clear_interaction_creation(self):
        self._interaction_arm = None
        self._dragging_interaction = None
        self.delete("interaction-preview")
        self._emit_interaction_preview("")

    def refresh(self):
        self.delete("all")
        self._apply_theme()
        data = ensure_tone_outline_defaults(clone_tone_outline(self.data or {}))
        axis_nodes = data.get("axis_nodes", [])
        width = max(self.winfo_width(), 820)
        height = max(self.winfo_height(), 460)
        self.configure(scrollregion=(0, 0, width, height))

        colors = {
            "grid": self._theme_color("border", "#D1D5DB"),
            "text": self._theme_color("fg_primary", "#111827"),
            "muted": self._theme_color("fg_secondary", "#6B7280"),
            "axis": self._theme_color("border", "#9CA3AF"),
            "selected": self._theme_color("accent", "#2563EB"),
            "bg": self._theme_color("canvas_bg", "#FFFFFF"),
        }

        if not axis_nodes:
            self.create_text(
                width / 2,
                height / 2 - 14,
                text="暂无基调节点。先在右侧新增主轴节点，或直接从场景生成主轴。",
                fill=colors["text"],
                font=("Microsoft YaHei", 11),
            )
            self.create_text(
                width / 2,
                height / 2 + 12,
                text="先创建主轴节点和人物线，再直接拖拽真实点或虚拟点生成波动关系。",
                fill=colors["muted"],
                font=("Microsoft YaHei", 9),
            )
            return

        margin_left = 84
        margin_right = 90
        label_top = 32
        chart_top = 96
        chart_bottom = height - 46
        baseline_y = (chart_top + chart_bottom) / 2
        step_x = 160
        total_width = max(
            width,
            margin_left + margin_right + max(0, len(axis_nodes) - 1) * step_x + 150,
        )
        self.configure(scrollregion=(0, 0, total_width, height))
        amplitude_scale = (chart_bottom - chart_top) / 220.0
        axis_index_map = get_axis_index_map(data)
        last_axis_uid = axis_nodes[-1]["uid"]
        selected_point_uids = set(self.selected_point_uids)
        if self.selected_point_uid:
            selected_point_uids.add(self.selected_point_uid)
        self._chart_bounds = (chart_top, chart_bottom, baseline_y)
        self._chart_x_bounds = (margin_left, total_width - margin_right)
        self._point_positions = []
        self._virtual_point_positions = []

        self.create_line(
            margin_left,
            baseline_y,
            total_width - margin_right,
            baseline_y,
            fill=colors["axis"],
            width=2,
        )
        self.create_line(
            margin_left,
            chart_top,
            total_width - margin_right,
            chart_top,
            fill=colors["grid"],
            dash=(4, 4),
        )
        self.create_line(
            margin_left,
            chart_bottom,
            total_width - margin_right,
            chart_bottom,
            fill=colors["grid"],
            dash=(4, 4),
        )
        self.create_text(margin_left - 12, chart_top, text="+100", anchor="e", fill=colors["muted"], font=("Arial", 8))
        self.create_text(margin_left - 12, baseline_y, text="0", anchor="e", fill=colors["muted"], font=("Arial", 8))
        self.create_text(margin_left - 12, chart_bottom, text="-100", anchor="e", fill=colors["muted"], font=("Arial", 8))

        self._axis_positions = {}
        self._axis_slots = {}
        for index, axis in enumerate(axis_nodes):
            x = margin_left + index * step_x
            self._axis_positions[axis["uid"]] = x
            is_selected = axis["uid"] == self.selected_axis_uid
            outline = colors["selected"] if is_selected else colors["axis"]
            fill = "#EFF6FF" if is_selected else colors["bg"]
            self.create_line(x, label_top + 18, x, chart_bottom, fill=colors["grid"], dash=(2, 6))
            self.create_oval(
                x - 8,
                label_top - 8,
                x + 8,
                label_top + 8,
                fill=fill,
                outline=outline,
                width=2,
                tags=("axis", f"axis:{axis['uid']}"),
            )
            self.create_text(
                x,
                label_top + 24,
                text=f"{index + 1}. {axis.get('title', '未命名节点')}",
                fill=colors["text"],
                width=126,
                font=("Microsoft YaHei", 9, "bold" if is_selected else "normal"),
                tags=("axis_label", f"axis:{axis['uid']}"),
            )
            if axis.get("description"):
                self.create_text(x + 30, label_top - 10, text="●", fill="#D97706", font=("Arial", 8))

        label_offset = 0
        for line in data.get("lines", []):
            if not line.get("visible", True):
                continue
            display_segments = get_display_segments(data, line)
            if not display_segments:
                continue
            for segment_index, segment in enumerate(display_segments):
                start_uid = segment.get("start_axis_uid")
                end_uid = segment.get("end_axis_uid") or last_axis_uid
                if start_uid not in self._axis_positions or end_uid not in self._axis_positions:
                    continue
                segment_uid = segment.get("uid") or ""
                sampled = self._sample_curve(
                    self._build_segment_points(
                        line,
                        segment,
                        start_uid,
                        end_uid,
                        baseline_y,
                        amplitude_scale,
                        margin_left,
                        total_width - margin_right,
                        axis_index_map,
                    )
                )
                segment_tags = ("segment", f"line:{line['uid']}", f"segment:{line['uid']}:{segment_uid}")
                if len(sampled) >= 4:
                    is_selected = (
                        line.get("uid") == self.selected_line_uid
                        and segment_uid == self.selected_segment_uid
                    )
                    width_px = 4 if is_selected else (3 if line.get("line_type") == "plot" else 2)
                    if is_selected:
                        self.create_line(
                            *[value for point in sampled for value in point],
                            fill="#93C5FD",
                            width=width_px + 5,
                            tags=segment_tags,
                            smooth=True,
                        )
                    self.create_line(
                        *[value for point in sampled for value in point],
                        fill=line.get("color") or "#2563EB",
                        width=width_px,
                        tags=segment_tags,
                        smooth=True,
                    )
                    if is_selected:
                        arc_handle = self._get_segment_arc_handle_position(
                            segment,
                            start_uid,
                            end_uid,
                            baseline_y,
                            amplitude_scale,
                        )
                        if arc_handle:
                            arc_x, arc_y, _arc_height = arc_handle
                            curve_tags = segment_tags + (f"curvehandle:{line['uid']}:{segment_uid}",)
                            self.create_line(
                                arc_x,
                                baseline_y,
                                arc_x,
                                arc_y,
                                fill="#60A5FA",
                                width=1,
                                dash=(4, 3),
                                tags=curve_tags,
                            )
                            self.create_oval(
                                arc_x - 6,
                                arc_y - 6,
                                arc_x + 6,
                                arc_y + 6,
                                fill="#F0FDFA",
                                outline=colors["selected"],
                                width=2,
                                tags=curve_tags,
                            )
                label_offset += 1
                status_suffix = ""
                if line.get("line_type") == "plot":
                    status_suffix = " / 全程"
                self.create_text(
                    self._axis_positions[start_uid] + 16,
                    baseline_y + 16 + ((label_offset % 4) * 14),
                    text=f"{line.get('name', '未命名线')}#{segment_index + 1}{status_suffix}",
                    anchor="w",
                    fill=line.get("color") or "#2563EB",
                    font=("Microsoft YaHei", 8),
                    tags=segment_tags,
                )

                for point in segment.get("points", []):
                    axis_uid = point.get("axis_uid")
                    if axis_uid not in self._axis_positions:
                        continue
                    current_index = axis_index_map.get(axis_uid, -1)
                    start_index = axis_index_map.get(start_uid, 0)
                    end_index = axis_index_map.get(end_uid, start_index)
                    if not start_index <= current_index <= end_index:
                        continue
                    x = self._axis_positions[axis_uid]
                    y = baseline_y - float(point.get("amplitude", 0)) * amplitude_scale
                    point_uid = point.get("uid", "")
                    is_selected = (
                        line.get("uid") == self.selected_line_uid
                        and segment_uid == self.selected_segment_uid
                        and point_uid in selected_point_uids
                    )
                    is_primary = (
                        line.get("uid") == self.selected_line_uid
                        and segment_uid == self.selected_segment_uid
                        and point_uid == self.selected_point_uid
                    )
                    radius = 7 if is_primary else (6 if is_selected else 5)
                    tags = (
                        "point",
                        f"line:{line['uid']}",
                        f"segment:{line['uid']}:{segment_uid}",
                        f"point:{line['uid']}:{segment_uid}:{point_uid}",
                    )
                    self.create_oval(
                        x - radius,
                        y - radius,
                        x + radius,
                        y + radius,
                        fill=line.get("color") or "#2563EB",
                        outline=colors["selected"] if is_selected else "#FFFFFF",
                        width=3 if is_primary else 2,
                        tags=tags,
                    )
                    self._point_positions.append(
                        {
                            "line_uid": line.get("uid", ""),
                            "segment_uid": segment_uid,
                            "point_uid": point_uid,
                            "axis_uid": axis_uid,
                            "x": x,
                            "y": y,
                        }
                    )
                    label = point.get("label")
                    if not label:
                        if point.get("node_type", DEFAULT_NODE_TYPE) != DEFAULT_NODE_TYPE:
                            label = get_node_type_label(point.get("node_type", DEFAULT_NODE_TYPE))
                        else:
                            label = f"{int(round(float(point.get('amplitude', 0)))):+d}"
                    self.create_text(
                        x,
                        y - 16,
                        text=label,
                        fill=line.get("color") or "#2563EB",
                        font=("Arial", 8),
                        tags=tags,
                    )
                if line.get("uid") == self.selected_line_uid:
                    self._draw_virtual_points_for_segment(
                        axis_nodes,
                        axis_index_map,
                        line,
                        segment,
                        sampled,
                        baseline_y,
                        amplitude_scale,
                        colors,
                    )

        selected_line = next(
            (
                line for line in data.get("lines", [])
                if line.get("uid") == self.selected_line_uid
            ),
            None,
        )
        if (
            selected_line
            and selected_line.get("visible", True)
            and not get_display_segments(data, selected_line)
        ):
            self._draw_virtual_points_for_empty_line(
                axis_nodes,
                baseline_y,
                amplitude_scale,
                selected_line,
                colors,
            )

        self._rebuild_axis_slots(data, baseline_y, amplitude_scale)
        self._draw_interactions(data)
        if self._dragging_point:
            self._draw_point_drag_preview()
        if self._dragging_boundary:
            self._draw_drag_preview()
        if self._dragging_interaction:
            self._draw_interaction_preview()
        if self._selection_box:
            self._draw_selection_preview()

    def _rebuild_axis_slots(self, data, baseline_y, amplitude_scale):
        axis_nodes = data.get("axis_nodes", [])
        axis_index_map = get_axis_index_map(data)
        last_axis_uid = axis_nodes[-1]["uid"] if axis_nodes else ""
        slots = {axis.get("uid"): [] for axis in axis_nodes if axis.get("uid")}
        for line in data.get("lines", []):
            if not line.get("visible", True):
                continue
            for segment in get_display_segments(data, line):
                start_uid = segment.get("start_axis_uid")
                end_uid = segment.get("end_axis_uid") or last_axis_uid
                if start_uid not in axis_index_map or end_uid not in axis_index_map:
                    continue
                sampled = self._sample_curve(
                    self._build_segment_points(
                        line,
                        segment,
                        start_uid,
                        end_uid,
                        baseline_y,
                        amplitude_scale,
                        self._chart_x_bounds[0],
                        self._chart_x_bounds[1],
                        axis_index_map,
                    )
                )
                point_y_map = {
                    point.get("axis_uid"): baseline_y - float(point.get("amplitude", 0)) * amplitude_scale
                    for point in segment.get("points", [])
                    if point.get("axis_uid") in self._axis_positions
                }
                start_index = axis_index_map.get(start_uid, 0)
                end_index = axis_index_map.get(end_uid, start_index)
                if end_index < start_index:
                    start_index, end_index = end_index, start_index
                for axis in axis_nodes[start_index:end_index + 1]:
                    axis_uid = axis.get("uid")
                    if axis_uid not in self._axis_positions:
                        continue
                    y = point_y_map.get(axis_uid)
                    if y is None:
                        y = self._estimate_curve_y(sampled, self._axis_positions[axis_uid], baseline_y)
                    slots.setdefault(axis_uid, []).append(
                        {
                            "axis_uid": axis_uid,
                            "line_uid": line.get("uid", ""),
                            "line_name": line.get("name") or "未命名线",
                            "segment_uid": segment.get("uid", ""),
                            "y": y,
                            "color": line.get("color") or "#2563EB",
                        }
                    )
        self._axis_slots = slots

    @staticmethod
    def _estimate_curve_y(sampled, axis_x, default_y):
        if not sampled:
            return default_y
        nearest = min(sampled, key=lambda item: abs(item[0] - axis_x))
        return nearest[1]

    def _find_point_context(self, point_uid):
        if not self.data or not point_uid:
            return None
        data = ensure_tone_outline_defaults(clone_tone_outline(self.data or {}))
        for line in data.get("lines", []):
            for segment in line.get("segments", []):
                for point in segment.get("points", []):
                    if point.get("uid") == point_uid:
                        return {
                            "axis_uid": point.get("axis_uid", ""),
                            "line_uid": line.get("uid", ""),
                            "line_name": line.get("name") or "未命名线",
                            "segment_uid": segment.get("uid", ""),
                            "segment": segment,
                            "point": point,
                        }
        return None

    def _find_virtual_point_context(self, line_uid, segment_uid, axis_uid):
        for item in self._virtual_point_positions:
            if (
                item.get("line_uid") == line_uid
                and item.get("segment_uid", "") == (segment_uid or "")
                and item.get("axis_uid") == axis_uid
            ):
                return item
        return None

    def _get_slot_for_segment(self, axis_uid, line_uid, segment_uid):
        for slot in self._axis_slots.get(axis_uid, []):
            if slot.get("line_uid") == line_uid and slot.get("segment_uid") == segment_uid:
                return slot
        return None

    def _get_interaction_target_slot(self, drag_state, canvas_y):
        axis_uid = drag_state.get("axis_uid", "")
        source_line_uid = drag_state.get("source_line_uid", "")
        source_segment_uid = drag_state.get("source_segment_uid", "")
        slots = [
            slot for slot in self._axis_slots.get(axis_uid, [])
            if not (
                slot.get("line_uid") == source_line_uid
                and slot.get("segment_uid") == source_segment_uid
            )
        ]
        if not slots:
            return None
        return min(slots, key=lambda slot: abs(float(slot.get("y", 0)) - canvas_y))

    def _interaction_offsets(self, interactions):
        grouped = {}
        for interaction in interactions:
            grouped.setdefault(interaction.get("axis_uid", ""), []).append(interaction)
        offsets = {}
        for axis_uid, items in grouped.items():
            total = len(items)
            for index, interaction in enumerate(items):
                offsets[interaction.get("uid", "")] = (index - (total - 1) / 2.0) * 10
        return offsets

    def _draw_connector_bundle(self, x, y1, y2, interaction_type, color, tags, selected=False):
        top_y = min(y1, y2)
        bottom_y = max(y1, y2)
        if abs(bottom_y - top_y) < 10:
            return
        is_dashed = interaction_type.startswith("dashed")
        line_dash = (6, 4) if is_dashed else None
        arrowshape = (10, 12, 5)
        highlight_color = "#BFDBFE"
        width = 2 if not selected else 3
        bundle = []

        if interaction_type in ("solid_single", "dashed_single"):
            bundle.append({"x": x, "y1": y1, "y2": y2, "arrow": tk.LAST})
        elif interaction_type == "solid_opposed_double":
            bundle.extend(
                [
                    {"x": x - 4, "y1": top_y, "y2": bottom_y, "arrow": tk.FIRST},
                    {"x": x + 4, "y1": top_y, "y2": bottom_y, "arrow": tk.LAST},
                ]
            )
        elif interaction_type == "dashed_facing_double":
            mid_y = (top_y + bottom_y) / 2
            bundle.extend(
                [
                    {"x": x - 4, "y1": top_y, "y2": mid_y, "arrow": tk.LAST},
                    {"x": x + 4, "y1": bottom_y, "y2": mid_y, "arrow": tk.LAST},
                ]
            )
        else:
            mid_y = y1 + ((y2 - y1) * 0.55)
            bundle.extend(
                [
                    {"x": x - 4, "y1": y1, "y2": y2, "arrow": tk.LAST},
                    {"x": x + 4, "y1": y1, "y2": mid_y, "arrow": tk.LAST},
                ]
            )

        for item in bundle:
            if selected:
                self.create_line(
                    item["x"],
                    item["y1"],
                    item["x"],
                    item["y2"],
                    fill=highlight_color,
                    width=width + 3,
                    arrow=item["arrow"],
                    arrowshape=arrowshape,
                    tags=tags,
                    dash=line_dash,
                )
            self.create_line(
                item["x"],
                item["y1"],
                item["x"],
                item["y2"],
                fill=color,
                width=width,
                arrow=item["arrow"],
                arrowshape=arrowshape,
                tags=tags,
                dash=line_dash,
            )

    def _draw_interactions(self, data):
        interactions = data.get("interactions", [])
        if not interactions:
            return
        offsets = self._interaction_offsets(interactions)
        for interaction in interactions:
            axis_uid = interaction.get("axis_uid", "")
            if axis_uid not in self._axis_positions:
                continue
            source_context = self._find_point_context(interaction.get("source_point_uid", ""))
            if not source_context:
                continue
            source_y = self._get_slot_for_segment(
                axis_uid,
                source_context.get("line_uid", ""),
                source_context.get("segment_uid", ""),
            )
            target_y = self._get_slot_for_segment(
                axis_uid,
                interaction.get("target_line_uid", ""),
                interaction.get("target_segment_uid", ""),
            )
            if not source_y or not target_y:
                continue
            x = self._axis_positions[axis_uid] + offsets.get(interaction.get("uid", ""), 0)
            tags = ("interaction", f"interaction:{interaction.get('uid', '')}")
            self._draw_connector_bundle(
                x,
                float(source_y.get("y", 0)),
                float(target_y.get("y", 0)),
                interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE),
                source_y.get("color", "#2563EB"),
                tags,
                selected=interaction.get("uid") == self.selected_interaction_uid,
            )

    def _build_segment_points(
        self,
        line,
        segment,
        start_uid,
        end_uid,
        baseline_y,
        amplitude_scale,
        min_x,
        max_x,
        axis_index_map,
    ):
        start_x = self._axis_positions[start_uid]
        end_x = self._axis_positions[end_uid]
        anchor_pad = 0 if line.get("line_type") == "plot" else 22
        start_anchor_x = max(min_x, start_x - anchor_pad) if start_x != end_x else start_x
        end_anchor_x = min(max_x, end_x + anchor_pad) if start_x != end_x else end_x
        arc_height = max(-100.0, min(100.0, float(segment.get("arc_height", DEFAULT_SEGMENT_ARC))))

        points = [
            {
                "x": start_anchor_x,
                "y": baseline_y,
                "curvature": DEFAULT_SEGMENT_CURVE,
            }
        ]
        for point in segment.get("points", []):
            points.append(
                {
                    "x": self._axis_positions[point.get("axis_uid")],
                    "y": baseline_y - float(point.get("amplitude", 0)) * amplitude_scale,
                    "curvature": float(point.get("curvature", 0.45)),
                }
            )
        if abs(arc_height) > 0.01 and end_anchor_x != start_anchor_x:
            arc_x = (start_anchor_x + end_anchor_x) / 2.0
            if any(abs(item["x"] - arc_x) < 1.0 for item in points):
                arc_x += 0.5
            points.append(
                {
                    "x": arc_x,
                    "y": baseline_y - arc_height * amplitude_scale,
                    "curvature": 0.55,
                }
            )
        if end_anchor_x != start_anchor_x or len(points) == 1:
            points.append(
                {
                    "x": end_anchor_x,
                    "y": baseline_y,
                    "curvature": DEFAULT_SEGMENT_CURVE,
                }
            )
        points.sort(key=lambda item: item["x"])
        return points

    def _draw_virtual_points_for_segment(
        self,
        axis_nodes,
        axis_index_map,
        line,
        segment,
        sampled,
        baseline_y,
        amplitude_scale,
        colors,
    ):
        for axis_uid in find_virtual_point_axes(axis_nodes, segment, axis_index_map):
            if axis_uid not in self._axis_positions:
                continue
            x = self._axis_positions[axis_uid]
            y = self._estimate_curve_y(sampled, x, baseline_y)
            self._draw_virtual_point_handle(
                line.get("uid", ""),
                segment.get("uid", ""),
                axis_uid,
                x,
                y,
                line.get("color") or "#2563EB",
                colors["selected"],
                baseline_y,
                amplitude_scale,
            )

    def _draw_virtual_points_for_empty_line(
        self,
        axis_nodes,
        baseline_y,
        amplitude_scale,
        line,
        colors,
    ):
        default_segment_uid = ""
        segments = line.get("segments", [])
        if segments:
            default_segment_uid = segments[0].get("uid", "")
        for axis in axis_nodes:
            axis_uid = axis.get("uid")
            if axis_uid not in self._axis_positions:
                continue
            self._draw_virtual_point_handle(
                line.get("uid", ""),
                default_segment_uid,
                axis_uid,
                self._axis_positions[axis_uid],
                baseline_y,
                line.get("color") or "#2563EB",
                colors["selected"],
                baseline_y,
                amplitude_scale,
            )

    def _draw_virtual_point_handle(
        self,
        line_uid,
        segment_uid,
        axis_uid,
        x,
        y,
        line_color,
        selected_color,
        baseline_y,
        amplitude_scale,
    ):
        tags = (
            "ghostpoint",
            f"line:{line_uid}",
            f"ghostpoint:{line_uid}:{segment_uid}:{axis_uid}",
        )
        self.create_oval(
            x - 5,
            y - 5,
            x + 5,
            y + 5,
            fill="#FFFFFF",
            outline=line_color,
            width=2,
            dash=(2, 2),
            tags=tags,
        )
        self.create_oval(
            x - 2,
            y - 2,
            x + 2,
            y + 2,
            fill=selected_color,
            outline="",
            tags=tags,
        )
        self._virtual_point_positions.append(
            {
                "line_uid": line_uid,
                "segment_uid": segment_uid or "",
                "axis_uid": axis_uid,
                "x": x,
                "y": y,
                "amplitude": (baseline_y - y) / amplitude_scale if amplitude_scale else 0.0,
            }
        )

    def _get_segment_arc_handle_position(
        self,
        segment,
        start_uid,
        end_uid,
        baseline_y,
        amplitude_scale,
    ):
        if start_uid not in self._axis_positions or end_uid not in self._axis_positions:
            return None
        start_x = self._axis_positions[start_uid]
        end_x = self._axis_positions[end_uid]
        arc_height = max(-100.0, min(100.0, float(segment.get("arc_height", DEFAULT_SEGMENT_ARC))))
        return (
            (start_x + end_x) / 2.0,
            baseline_y - arc_height * amplitude_scale,
            arc_height,
        )

    def _sample_curve(self, points):
        if len(points) < 2:
            return []
        sampled = []
        for index in range(len(points) - 1):
            p0 = points[index]
            p1 = points[index + 1]
            dx = p1["x"] - p0["x"]
            if dx <= 0:
                continue
            handle_factor = min(0.45, max(0.12, (p0["curvature"] + p1["curvature"]) / 4.0))
            handle = dx * handle_factor
            c1 = (p0["x"] + handle, p0["y"])
            c2 = (p1["x"] - handle, p1["y"])
            steps = 18
            for step in range(steps + 1):
                t = step / steps
                x = (
                    ((1 - t) ** 3) * p0["x"]
                    + 3 * ((1 - t) ** 2) * t * c1[0]
                    + 3 * (1 - t) * (t ** 2) * c2[0]
                    + (t ** 3) * p1["x"]
                )
                y = (
                    ((1 - t) ** 3) * p0["y"]
                    + 3 * ((1 - t) ** 2) * t * c1[1]
                    + 3 * (1 - t) * (t ** 2) * c2[1]
                    + (t ** 3) * p1["y"]
                )
                if sampled and step == 0:
                    continue
                sampled.append((x, y))
        return sampled

    def _nearest_axis_uid(self, canvas_x):
        if not self._axis_positions:
            return ""
        return min(
            self._axis_positions,
            key=lambda axis_uid: abs(self._axis_positions[axis_uid] - canvas_x),
        )

    def _tags_at(self, canvas_x, canvas_y, padding=6):
        items = self.find_overlapping(
            canvas_x - padding,
            canvas_y - padding,
            canvas_x + padding,
            canvas_y + padding,
        )
        for item_id in reversed(items):
            tags = self.gettags(item_id)
            if tags:
                return tags
        return ()

    def _is_chart_area(self, canvas_y):
        chart_top, chart_bottom, _baseline_y = self._chart_bounds
        return chart_top <= canvas_y <= chart_bottom

    @staticmethod
    def _selection_drag_threshold():
        return 8

    def _selection_box_is_drag(self):
        if not self._selection_box:
            return False
        return (
            abs(float(self._selection_box.get("current_x", 0)) - float(self._selection_box.get("start_x", 0))) >= self._selection_drag_threshold()
            or abs(float(self._selection_box.get("current_y", 0)) - float(self._selection_box.get("start_y", 0))) >= self._selection_drag_threshold()
        )

    def _selection_box_point_uids(self):
        if not self._selection_box:
            return []
        return find_points_in_selection(
            self._point_positions,
            self._selection_box.get("line_uid", ""),
            self._selection_box.get("segment_uid", ""),
            self._selection_box.get("start_x", 0),
            self._selection_box.get("start_y", 0),
            self._selection_box.get("current_x", 0),
            self._selection_box.get("current_y", 0),
        )

    def _draw_selection_preview(self):
        self.delete("selection-preview")
        if not self._selection_box:
            return
        start_x = float(self._selection_box.get("start_x", 0))
        start_y = float(self._selection_box.get("start_y", 0))
        current_x = float(self._selection_box.get("current_x", start_x))
        current_y = float(self._selection_box.get("current_y", start_y))
        if abs(current_x - start_x) < 1 and abs(current_y - start_y) < 1:
            return
        left, right = sorted((start_x, current_x))
        top, bottom = sorted((start_y, current_y))
        preview_color = self._theme_color("accent", "#2563EB")
        self.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline=preview_color,
            width=2,
            dash=(6, 4),
            tags=("selection-preview",),
        )

    def _draw_drag_preview(self):
        self.delete("drag-preview")
        if not self._dragging_boundary:
            return
        chart_top, chart_bottom, baseline_y = self._chart_bounds
        preview_color = self._theme_color("accent", "#2563EB")
        preview_glow = "#DBEAFE"
        preview = self._get_arc_preview_segment()
        if not preview:
            return
        line, segment, axis_index_map, axis_nodes = preview
        start_uid = segment.get("start_axis_uid")
        end_uid = segment.get("end_axis_uid") or (axis_nodes[-1]["uid"] if axis_nodes else "")
        if start_uid not in self._axis_positions or end_uid not in self._axis_positions:
            return
        min_x, max_x = self._chart_x_bounds
        amplitude_scale = (chart_bottom - chart_top) / 220.0 if chart_bottom > chart_top else 1.0
        sampled = self._sample_curve(
            self._build_segment_points(
                line,
                segment,
                start_uid,
                end_uid,
                baseline_y,
                amplitude_scale,
                min_x,
                max_x,
                axis_index_map,
            )
        )
        if len(sampled) >= 4:
            flattened = [value for point in sampled for value in point]
            self.create_line(
                *flattened,
                fill=preview_glow,
                width=7,
                tags=("drag-preview",),
                smooth=True,
            )
            self.create_line(
                *flattened,
                fill=preview_color,
                width=3,
                dash=(10, 6),
                tags=("drag-preview",),
                smooth=True,
            )
        arc_handle = self._get_segment_arc_handle_position(
            segment,
            start_uid,
            end_uid,
            baseline_y,
            amplitude_scale,
        )
        if arc_handle:
            arc_x, arc_y, _arc_height = arc_handle
            self.create_line(
                arc_x,
                baseline_y,
                arc_x,
                arc_y,
                fill="#60A5FA",
                width=2,
                dash=(6, 4),
                tags=("drag-preview",),
            )
            self.create_oval(
                arc_x - 8,
                arc_y - 8,
                arc_x + 8,
                arc_y + 8,
                fill=preview_glow,
                outline=preview_color,
                width=2,
                tags=("drag-preview",),
            )

    def _get_arc_preview_segment(self):
        if not self.data or not self._dragging_boundary or self._dragging_boundary.get("mode") != "arc":
            return None
        data = ensure_tone_outline_defaults(clone_tone_outline(self.data or {}))
        line_uid = self._dragging_boundary.get("line_uid")
        segment_uid = self._dragging_boundary.get("segment_uid")
        line = next((item for item in data.get("lines", []) if item.get("uid") == line_uid), None)
        segment = next((item for item in (line or {}).get("segments", []) if item.get("uid") == segment_uid), None)
        if not line or not segment:
            return None
        preview_segment = dict(segment)
        preview_segment["arc_height"] = float(
            self._dragging_boundary.get("target_arc_height", segment.get("arc_height", DEFAULT_SEGMENT_ARC))
        )
        return line, preview_segment, get_axis_index_map(data), data.get("axis_nodes", [])

    def _emit_drag_preview(self):
        if not self.on_drag_preview:
            return
        if not self._dragging_boundary:
            self.on_drag_preview("")
            return
        arc_height = float(self._dragging_boundary.get("target_arc_height", DEFAULT_SEGMENT_ARC))
        self.on_drag_preview(f"拖拽预览：中段拱度 {arc_height:+.0f}")

    def _emit_point_preview(self, message):
        if self.on_point_drag_preview:
            self.on_point_drag_preview(message)

    def _emit_interaction_preview(self, message):
        if self.on_interaction_preview:
            self.on_interaction_preview(message)

    def _emit_context_request(self, kind, payload, x_root, y_root):
        if self.on_context_requested:
            self.on_context_requested(kind, payload, x_root, y_root)

    def _get_point_drag_preview_sample(self):
        if not self.data or not self._dragging_point:
            return [], ""
        line_uid = self._dragging_point.get("line_uid", "")
        segment_uid = self._dragging_point.get("segment_uid", "")
        point_uid = self._dragging_point.get("point_uid", "")
        target_axis_uid = self._dragging_point.get("target_axis_uid", "")
        data = self.data or {}
        line = next(
            (item for item in data.get("lines", []) if item.get("uid") == line_uid),
            None,
        )
        segment = next(
            (item for item in (line or {}).get("segments", []) if item.get("uid") == segment_uid),
            None,
        )
        axis_nodes = data.get("axis_nodes", [])
        if not line or not axis_nodes or not target_axis_uid:
            return [], ""
        preview_segment = dict(segment or {})
        preview_points = []
        if segment:
            for point in segment.get("points", []):
                preview_point = dict(point)
                if preview_point.get("uid") == point_uid:
                    preview_point["axis_uid"] = target_axis_uid
                    preview_point["amplitude"] = float(
                        self._dragging_point.get("target_amplitude", preview_point.get("amplitude", 0))
                    )
                preview_points.append(preview_point)
        if not point_uid:
            preview_points.append(
                {
                    "uid": "",
                    "axis_uid": target_axis_uid,
                    "amplitude": float(self._dragging_point.get("target_amplitude", 0)),
                    "curvature": 0.45,
                }
            )
        preview_segment["points"] = preview_points
        point_axis_uids = [
            point.get("axis_uid")
            for point in preview_points
            if point.get("axis_uid") in self._axis_positions
        ]
        if not point_axis_uids:
            return [], line.get("color") or "#2563EB"
        axis_index_map = get_axis_index_map(data)
        point_axis_uids.sort(key=lambda axis_uid: axis_index_map.get(axis_uid, 10**6))
        start_uid = point_axis_uids[0]
        end_uid = point_axis_uids[-1]
        if start_uid not in self._axis_positions or end_uid not in self._axis_positions:
            return [], ""

        chart_top, chart_bottom, baseline_y = self._chart_bounds
        amplitude_scale = (chart_bottom - chart_top) / 220.0 if chart_bottom > chart_top else 1.0
        sampled = self._sample_curve(
            self._build_segment_points(
                line,
                preview_segment,
                start_uid,
                end_uid,
                baseline_y,
                amplitude_scale,
                self._chart_x_bounds[0],
                self._chart_x_bounds[1],
                axis_index_map,
            )
        )
        return sampled, line.get("color") or "#2563EB"

    def _draw_point_drag_preview(self):
        self.delete("point-preview")
        if not self._dragging_point:
            return
        sampled, line_color = self._get_point_drag_preview_sample()
        if len(sampled) >= 2:
            self.create_line(
                *[value for point in sampled for value in point],
                fill="#BFDBFE",
                width=8,
                smooth=True,
                tags=("point-preview",),
            )
            self.create_line(
                *[value for point in sampled for value in point],
                fill=line_color or self._theme_color("accent", "#2563EB"),
                width=3,
                smooth=True,
                tags=("point-preview",),
            )
        axis_uid = self._dragging_point.get("target_axis_uid", "")
        if axis_uid not in self._axis_positions:
            return
        chart_top, chart_bottom, baseline_y = self._chart_bounds
        amplitude_scale = (chart_bottom - chart_top) / 220.0
        amplitude = float(self._dragging_point.get("target_amplitude", 0))
        x = self._axis_positions[axis_uid]
        y = baseline_y - amplitude * amplitude_scale
        preview_color = self._theme_color("accent", "#2563EB")
        self.create_line(
            x,
            chart_top,
            x,
            chart_bottom,
            fill="#60A5FA",
            width=2,
            dash=(6, 4),
            tags=("point-preview",),
        )
        self.create_oval(
            x - 8,
            y - 8,
            x + 8,
            y + 8,
            fill="#FFFFFF",
            outline=preview_color,
            width=2,
            tags=("point-preview",),
        )
        self.create_text(
            x,
            y - 18,
            text=f"{int(round(amplitude)):+d}",
            fill=preview_color,
            font=("Arial", 8, "bold"),
            tags=("point-preview",),
        )

    def _draw_interaction_preview(self):
        self.delete("interaction-preview")
        if not self._dragging_interaction:
            return
        drag_state = self._dragging_interaction
        source_context = self._find_point_context(drag_state.get("source_point_uid", ""))
        target_slot = drag_state.get("target_slot")
        if not source_context or not target_slot:
            return
        axis_uid = drag_state.get("axis_uid", "")
        source_slot = self._get_slot_for_segment(
            axis_uid,
            source_context.get("line_uid", ""),
            source_context.get("segment_uid", ""),
        )
        if not source_slot or axis_uid not in self._axis_positions:
            return
        x = self._axis_positions[axis_uid]
        self._draw_connector_bundle(
            x + 14,
            float(source_slot.get("y", 0)),
            float(target_slot.get("y", 0)),
            drag_state.get("interaction_type", DEFAULT_INTERACTION_TYPE),
            source_slot.get("color", "#2563EB"),
            ("interaction-preview",),
            selected=True,
        )

    def _start_interaction_retarget(self, interaction_uid):
        if not self.data or not interaction_uid:
            return False
        data = ensure_tone_outline_defaults(clone_tone_outline(self.data or {}))
        interaction = next(
            (
                item for item in data.get("interactions", [])
                if item.get("uid") == interaction_uid
            ),
            None,
        )
        if not interaction:
            return False
        self._dragging_interaction = {
            "mode": "retarget",
            "interaction_uid": interaction_uid,
            "source_line_uid": interaction.get("source_line_uid", ""),
            "source_segment_uid": interaction.get("source_segment_uid", ""),
            "source_point_uid": interaction.get("source_point_uid", ""),
            "axis_uid": interaction.get("axis_uid", ""),
            "interaction_type": interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE),
            "target_slot": self._get_slot_for_segment(
                interaction.get("axis_uid", ""),
                interaction.get("target_line_uid", ""),
                interaction.get("target_segment_uid", ""),
            ),
        }
        self._draw_interaction_preview()
        self._emit_interaction_preview("拖拽中：沿同一主轴节点上下改到新的目标线段。")
        return True

    def _handle_press(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        tags = self._tags_at(x, y)
        if self._interaction_arm:
            source_point_tag = (
                f"point:{self._interaction_arm['source_line_uid']}:"
                f"{self._interaction_arm['source_segment_uid']}:"
                f"{self._interaction_arm['source_point_uid']}"
            )
            if source_point_tag in tags:
                self._dragging_interaction = dict(self._interaction_arm)
                self._dragging_interaction["target_slot"] = self._get_interaction_target_slot(
                    self._dragging_interaction,
                    y,
                )
                self._draw_interaction_preview()
                self._emit_interaction_preview("拖拽中：沿同一主轴节点上下选择目标线段。")
                return
        for tag in tags:
            if tag.startswith("interaction:"):
                interaction_uid = tag.split(":", 1)[1]
                if interaction_uid == self.selected_interaction_uid and self._start_interaction_retarget(interaction_uid):
                    return
                self.on_interaction_selected(interaction_uid)
                return
        for tag in tags:
            if tag.startswith("curvehandle:"):
                _, line_uid, segment_uid = tag.split(":", 2)
                current_arc = DEFAULT_SEGMENT_ARC
                if self.data:
                    line = next((item for item in (self.data or {}).get("lines", []) if item.get("uid") == line_uid), None)
                    segment = next((item for item in (line or {}).get("segments", []) if item.get("uid") == segment_uid), None)
                    if segment:
                        current_arc = float(segment.get("arc_height", DEFAULT_SEGMENT_ARC))
                self._dragging_boundary = {
                    "mode": "arc",
                    "line_uid": line_uid,
                    "segment_uid": segment_uid,
                    "target_arc_height": current_arc,
                }
                self.on_segment_selected(line_uid, segment_uid)
                self._emit_drag_preview()
                self._draw_drag_preview()
                return
        for tag in tags:
            if tag.startswith("ghostpoint:"):
                _, line_uid, segment_uid, axis_uid = tag.split(":", 3)
                self.on_segment_selected(line_uid, segment_uid)
                ghost_context = self._find_virtual_point_context(line_uid, segment_uid, axis_uid) or {}
                self._dragging_point = {
                    "line_uid": line_uid,
                    "segment_uid": segment_uid,
                    "point_uid": "",
                    "target_axis_uid": axis_uid,
                    "target_amplitude": float(ghost_context.get("amplitude", 0)),
                }
                self._draw_point_drag_preview()
                self._emit_point_preview("拖拽预览：从虚拟节点拖出真实波动点，可上下调强度、左右延展关系。")
                return
        for tag in tags:
            if tag.startswith("point:"):
                _, line_uid, segment_uid, point_uid = tag.split(":", 3)
                self.on_point_selected(line_uid, segment_uid, point_uid)
                context = self._find_point_context(point_uid)
                current_point = (context or {}).get("point", {})
                self._dragging_point = {
                    "line_uid": line_uid,
                    "segment_uid": segment_uid,
                    "point_uid": point_uid,
                    "target_axis_uid": current_point.get("axis_uid", ""),
                    "target_amplitude": float(current_point.get("amplitude", 0)),
                }
                self._draw_point_drag_preview()
                self._emit_point_preview("拖拽预览：沿时间轴移动节点并上下调整强度。")
                return
        for tag in tags:
            if tag.startswith("segment:"):
                _, line_uid, segment_uid = tag.split(":", 2)
                self.on_segment_selected(line_uid, segment_uid)
                return
        for tag in tags:
            if tag.startswith("axis:"):
                self.on_axis_selected(tag.split(":", 1)[1])
                return
        if (
            not self._interaction_arm
            and self.selected_line_uid
            and self.selected_segment_uid
            and self._is_chart_area(y)
        ):
            self._selection_box = {
                "line_uid": self.selected_line_uid,
                "segment_uid": self.selected_segment_uid,
                "start_x": x,
                "start_y": y,
                "current_x": x,
                "current_y": y,
            }
            self._draw_selection_preview()
            self._emit_point_preview("框选预览：拖拽覆盖当前过程段的多个波动点。")

    def _handle_drag(self, event):
        if self._selection_box:
            self._selection_box["current_x"] = self.canvasx(event.x)
            self._selection_box["current_y"] = self.canvasy(event.y)
            self._draw_selection_preview()
            point_count = len(self._selection_box_point_uids()) if self._selection_box_is_drag() else 0
            self._emit_point_preview(f"框选预览：已命中 {point_count} 个波动点。")
            return
        if self._dragging_point:
            canvas_x = self.canvasx(event.x)
            canvas_y = self.canvasy(event.y)
            chart_top, chart_bottom, baseline_y = self._chart_bounds
            amplitude_scale = (chart_bottom - chart_top) / 220.0 if chart_bottom > chart_top else 1.0
            amplitude = max(-100.0, min(100.0, (baseline_y - canvas_y) / amplitude_scale))
            target_axis_uid = self._nearest_axis_uid(canvas_x)
            axis_title = target_axis_uid
            if self.data:
                axis_title = next(
                    (
                        axis.get("title", target_axis_uid)
                        for axis in (self.data or {}).get("axis_nodes", [])
                        if axis.get("uid") == target_axis_uid
                    ),
                    target_axis_uid,
                )
            self._dragging_point["target_axis_uid"] = target_axis_uid
            self._dragging_point["target_amplitude"] = amplitude
            self._draw_point_drag_preview()
            self._emit_point_preview(
                f"拖拽预览：{int(round(amplitude)):+d} / {axis_title or '未命名节点'}"
            )
            return
        if self._dragging_interaction:
            canvas_y = self.canvasy(event.y)
            self._dragging_interaction["target_slot"] = self._get_interaction_target_slot(
                self._dragging_interaction,
                canvas_y,
            )
            target_slot = self._dragging_interaction.get("target_slot")
            if target_slot:
                self._emit_interaction_preview(
                    f"拖拽预览：指向 {target_slot.get('line_name', '未命名线')}"
                )
            else:
                self._emit_interaction_preview("拖拽预览：当前节点没有其他可连接线段。")
            self._draw_interaction_preview()
            return
        if not self._dragging_boundary:
            return
        canvas_y = self.canvasy(event.y)
        chart_top, chart_bottom, baseline_y = self._chart_bounds
        amplitude_scale = (chart_bottom - chart_top) / 220.0 if chart_bottom > chart_top else 1.0
        self._dragging_boundary["target_arc_height"] = max(
            -100.0,
            min(100.0, (baseline_y - canvas_y) / amplitude_scale),
        )
        self._emit_drag_preview()
        self._draw_drag_preview()

    def _handle_release(self, event):
        if self._selection_box:
            point_uids = self._selection_box_point_uids() if self._selection_box_is_drag() else None
            selection_box = dict(self._selection_box)
            self._selection_box = None
            self.delete("selection-preview")
            self._emit_point_preview("")
            if point_uids is not None and self.on_points_selected:
                self.on_points_selected(
                    selection_box.get("line_uid", ""),
                    selection_box.get("segment_uid", ""),
                    point_uids,
                )
            return
        if self._dragging_point:
            dragging_point = dict(self._dragging_point)
            self._dragging_point = None
            self.delete("point-preview")
            self._emit_point_preview("")
            target_axis_uid = dragging_point.get("target_axis_uid", "")
            if target_axis_uid:
                self.on_point_drag(
                    dragging_point.get("line_uid", ""),
                    dragging_point.get("segment_uid", ""),
                    dragging_point.get("point_uid", ""),
                    target_axis_uid,
                    float(dragging_point.get("target_amplitude", 0)),
                )
            return
        if self._dragging_interaction:
            dragging_info = dict(self._dragging_interaction)
            target_slot = dragging_info.get("target_slot")
            self._dragging_interaction = None
            self.delete("interaction-preview")
            self._emit_interaction_preview("")
            was_creation = not dragging_info.get("interaction_uid")
            if was_creation:
                self._interaction_arm = None
            if target_slot:
                if dragging_info.get("interaction_uid"):
                    self.on_interaction_retarget(
                        dragging_info.get("interaction_uid", ""),
                        target_slot.get("line_uid", ""),
                        target_slot.get("segment_uid", ""),
                    )
                else:
                    self.on_interaction_created(
                        dragging_info.get("source_line_uid", ""),
                        dragging_info.get("source_segment_uid", ""),
                        dragging_info.get("source_point_uid", ""),
                        target_slot.get("line_uid", ""),
                        target_slot.get("segment_uid", ""),
                        dragging_info.get("axis_uid", ""),
                        dragging_info.get("interaction_type", DEFAULT_INTERACTION_TYPE),
                    )
            return
        if not self._dragging_boundary:
            return
        dragging_info = dict(self._dragging_boundary)
        self._dragging_boundary = None
        self.delete("drag-preview")
        self._emit_drag_preview()
        if self.on_segment_arc_drag:
            self.on_segment_arc_drag(
                dragging_info.get("line_uid", ""),
                dragging_info.get("segment_uid", ""),
                float(dragging_info.get("target_arc_height", DEFAULT_SEGMENT_ARC)),
            )

    def _handle_context_menu(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        tags = self._tags_at(x, y, padding=8)
        if not tags:
            return
        for tag in tags:
            if tag.startswith("interaction:"):
                interaction_uid = tag.split(":", 1)[1]
                self.on_interaction_selected(interaction_uid)
                self._emit_context_request(
                    "interaction",
                    {"interaction_uid": interaction_uid},
                    event.x_root,
                    event.y_root,
                )
                return
        for tag in tags:
            if tag.startswith("point:"):
                _, line_uid, segment_uid, point_uid = tag.split(":", 3)
                if point_uid not in self.selected_point_uids or len(self.selected_point_uids) <= 1:
                    self.on_point_selected(line_uid, segment_uid, point_uid)
                self._emit_context_request(
                    "point",
                    {
                        "line_uid": line_uid,
                        "segment_uid": segment_uid,
                        "point_uid": point_uid,
                    },
                    event.x_root,
                    event.y_root,
                )
                return
        for tag in tags:
            if tag.startswith("segment:"):
                _, line_uid, segment_uid = tag.split(":", 2)
                self.on_segment_selected(line_uid, segment_uid)
                self._emit_context_request(
                    "segment",
                    {"line_uid": line_uid, "segment_uid": segment_uid},
                    event.x_root,
                    event.y_root,
                )
                return
        for tag in tags:
            if tag.startswith("axis:"):
                axis_uid = tag.split(":", 1)[1]
                self.on_axis_selected(axis_uid)
                self._emit_context_request(
                    "axis",
                    {"axis_uid": axis_uid},
                    event.x_root,
                    event.y_root,
                )
                return

class ToneOutlineSummaryPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()

    @staticmethod
    def _create_tree(parent, root_text, columns):
        column_ids = [column_key for column_key, _column_label, _width, _anchor in columns]
        tree = ttk.Treeview(parent, columns=column_ids, show="tree headings", height=16)
        tree.heading("#0", text=root_text)
        for column_key, column_label, width, anchor in columns:
            tree.heading(column_key, text=column_label)
            tree.column(column_key, width=width, anchor=anchor)
        tree.column("#0", width=220, anchor="w")
        tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        return tree

    def _setup_ui(self):
        ttk.Label(
            self,
            text="汇总按“线、情节、时间、关系”四个视角展开，节点类型、说明分类、隐藏状态都会同步显示。",
        ).pack(anchor="w", padx=8, pady=(8, 4))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        line_frame = ttk.Frame(notebook)
        plot_frame = ttk.Frame(notebook)
        axis_frame = ttk.Frame(notebook)
        relation_frame = ttk.Frame(notebook)
        notebook.add(line_frame, text="按线 / 人物")
        notebook.add(plot_frame, text="按情节")
        notebook.add(axis_frame, text="按时间")
        notebook.add(relation_frame, text="关系表")

        summary_columns = (
            ("state", "状态", 90, "center"),
            ("strength", "强度", 70, "center"),
            ("curve", "曲率/类型", 100, "center"),
            ("note", "说明", 260, "w"),
        )
        self.line_tree = self._create_tree(line_frame, "线 / 过程 / 节点", summary_columns)
        self.plot_tree = self._create_tree(plot_frame, "情节节点 / 响应线", summary_columns)
        self.axis_tree = self._create_tree(axis_frame, "节点 / 对应线", summary_columns)
        self.relation_tree = self._create_tree(
            relation_frame,
            "来源线",
            (
                ("time", "时间点", 120, "center"),
                ("type", "关系", 120, "center"),
                ("target", "目标", 140, "center"),
                ("note", "备注", 260, "w"),
            ),
        )

    def refresh(self, tone_outline_data):
        for tree in (self.line_tree, self.plot_tree, self.axis_tree, self.relation_tree):
            for item_id in tree.get_children():
                tree.delete(item_id)

        for line in build_line_summary(tone_outline_data):
            line_text = line["name"]
            if line["line_type"] == "character" and line["character_name"]:
                line_text = f"{line['name']} ({line['character_name']})"
            line_parent = self.line_tree.insert(
                "",
                "end",
                text=line_text,
                    values=(line["status_text"], "", "", ""),
                    open=True,
                )
            for segment in line["segments"]:
                segment_note_parts = [
                    part for part in (
                        segment.get("segment_title", ""),
                        segment.get("segment_note_type", ""),
                        segment.get("segment_note", ""),
                    )
                    if part
                ]
                segment_parent = self.line_tree.insert(
                    line_parent,
                    "end",
                    text=segment["range_text"],
                    values=(
                        segment["state_text"],
                        "",
                        segment.get("curve_text", ""),
                        " / ".join(segment_note_parts),
                    ),
                    open=True,
                )
                for item in segment["items"]:
                    note_parts = [item.get("description") or item.get("label") or ""]
                    if item.get("note_type"):
                        note_parts.append(item["note_type"])
                    if item.get("tags"):
                        note_parts.append(", ".join(item["tags"]))
                    self.line_tree.insert(
                        segment_parent,
                        "end",
                        text=item["axis_title"],
                        values=(
                            item.get("node_type") and get_node_type_label(item["node_type"]) or "节点",
                            item["strength"],
                            item["curvature"],
                            " / ".join([part for part in note_parts if part]),
                        ),
                    )
                for interaction in segment.get("interactions", []):
                    note = interaction.get("note") or f"指向 {interaction.get('target_line_name', '未命名线')}"
                    self.line_tree.insert(
                        segment_parent,
                        "end",
                        text=interaction.get("axis_title", "未命名节点"),
                        values=(
                            interaction.get("state_text", "作用"),
                            "",
                            interaction.get("type_text", ""),
                            note,
                        ),
                    )

        for axis in build_plot_summary(tone_outline_data):
            plot_match = axis.get("plot_match") or {}
            plot_note = plot_match.get("description") or axis.get("axis_description", "")
            plot_parent = self.plot_tree.insert(
                "",
                "end",
                text=axis.get("axis_title", "未命名节点"),
                values=(
                    plot_match.get("state_text", "情节节点"),
                    plot_match.get("strength", ""),
                    plot_match.get("curvature", ""),
                    plot_note,
                ),
                open=True,
            )
            for match in axis.get("related_lines", []):
                note = match.get("description") or match.get("label") or ""
                if match.get("note_type"):
                    note = " / ".join(filter(None, [note, match.get("note_type")]))
                self.plot_tree.insert(
                    plot_parent,
                    "end",
                    text=match["line_name"],
                    values=(
                        match["state_text"],
                        match["strength"],
                        match["curvature"],
                        note,
                    ),
                )
            for relation in axis.get("relations", []):
                self.plot_tree.insert(
                    plot_parent,
                    "end",
                    text=relation["line_name"],
                    values=(
                        relation["state_text"],
                        relation["strength"],
                        relation["curvature"],
                        relation["description"],
                    ),
                )

        for axis in build_timeline_summary(tone_outline_data):
            parent = self.axis_tree.insert(
                "",
                "end",
                text=axis["axis_title"],
                values=("主轴节点", "", "", axis["axis_description"]),
                open=True,
            )
            for match in axis["matches"]:
                note_parts = [match.get("description") or match.get("label") or ""]
                if match.get("note_type"):
                    note_parts.append(match["note_type"])
                if match.get("tags"):
                    note_parts.append(", ".join(match["tags"]))
                self.axis_tree.insert(
                    parent,
                    "end",
                    text=match["line_name"],
                    values=(
                        match["state_text"],
                        match["strength"],
                        match["curvature"],
                        " / ".join([part for part in note_parts if part]),
                    ),
                )

        for relation in build_relation_summary(tone_outline_data):
            self.relation_tree.insert(
                "",
                "end",
                text=relation["source_line_name"],
                values=(
                    relation["axis_title"],
                    relation["relation_label"],
                    relation["target_line_name"],
                    relation["note"],
                ),
            )


class ToneOutlineEditor(ttk.Frame):
    def __init__(self, parent, project_manager, command_executor, theme_manager=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager

        self.selected_axis_uid = ""
        self.selected_line_uid = DEFAULT_PLOT_LINE_UID
        self.selected_segment_uid = ""
        self.selected_point_uid = ""
        self.selected_point_uids = []
        self.selected_interaction_uid = ""
        self.axis_order = []
        self.active_line_order = []
        self.segment_order = []
        self.point_order = []
        self.interaction_order = []
        self._synced_selection_snapshot = {}

        self.axis_title_var = tk.StringVar()
        self.line_name_var = tk.StringVar()
        self.line_type_var = tk.StringVar()
        self.line_character_var = tk.StringVar()
        self.line_status_var = tk.StringVar()
        self.line_visible_var = tk.BooleanVar(value=True)
        self.segment_range_var = tk.StringVar()
        self.segment_status_var = tk.StringVar()
        self.segment_start_var = tk.StringVar()
        self.segment_end_var = tk.StringVar()
        self.segment_title_var = tk.StringVar()
        self.segment_note_type_var = tk.StringVar(value=NOTE_TYPE_LABELS[DEFAULT_NOTE_TYPE])
        self.segment_arc_display_var = tk.StringVar()
        self.point_axis_var = tk.StringVar()
        self.point_label_var = tk.StringVar()
        self.point_node_type_var = tk.StringVar(value=NODE_TYPE_LABELS[DEFAULT_NODE_TYPE])
        self.point_note_type_var = tk.StringVar(value=NOTE_TYPE_LABELS[DEFAULT_NOTE_TYPE])
        self.point_tags_var = tk.StringVar()
        self.point_status_var = tk.StringVar()
        self.point_amplitude_var = tk.DoubleVar(value=0.0)
        self.point_curvature_var = tk.DoubleVar(value=0.45)
        self.point_amplitude_display_var = tk.StringVar()
        self.point_curvature_display_var = tk.StringVar()
        self.interaction_type_var = tk.StringVar(value=INTERACTION_TYPE_LABELS[DEFAULT_INTERACTION_TYPE])
        self.interaction_status_var = tk.StringVar()
        self.interaction_source_var = tk.StringVar()
        self.interaction_target_var = tk.StringVar()

        self._bind_scale_display(
            self.point_amplitude_var,
            self.point_amplitude_display_var,
            lambda value: f"{int(round(float(value))):+d}",
        )
        self._bind_scale_display(
            self.point_curvature_var,
            self.point_curvature_display_var,
            lambda value: f"{float(value):.2f}",
        )

        self._setup_ui()
        self.refresh()

    def _bind_scale_display(self, source_var, display_var, formatter):
        def _update(*_args):
            display_var.set(formatter(source_var.get()))

        source_var.trace_add("write", _update)
        _update()

    def _snap_scale_value(self, variable, step, digits=2):
        value = float(variable.get())
        snapped = round(value / step) * step
        snapped = round(snapped, digits)
        if abs(value - snapped) > 1e-9:
            variable.set(snapped)

    def _create_labeled_scale(
        self,
        parent,
        variable,
        display_var,
        from_,
        to,
        step,
        digits=2,
        orient=tk.HORIZONTAL,
        length=220,
    ):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=6, pady=(0, 2))
        scale = ttk.Scale(
            row,
            from_=from_,
            to=to,
            variable=variable,
            orient=orient,
            length=length,
            command=lambda _value: self._snap_scale_value(variable, step, digits),
        )
        if orient == tk.VERTICAL:
            scale.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        else:
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(row, textvariable=display_var, width=7, anchor="e").pack(side=tk.RIGHT, padx=(8, 0))
        return scale

    def _clear_point_selection(self):
        self.selected_point_uid = ""
        self.selected_point_uids = []

    def _set_selected_points(self, point_uids):
        ordered_uids = []
        seen = set()
        for point_uid in point_uids or []:
            if point_uid and point_uid not in seen:
                ordered_uids.append(point_uid)
                seen.add(point_uid)
        self.selected_point_uids = ordered_uids
        self.selected_point_uid = ordered_uids[0] if ordered_uids else ""

    def _capture_selection_snapshot(self):
        return {
            "axis_uid": self.selected_axis_uid or "",
            "line_uid": self.selected_line_uid or "",
            "segment_uid": self.selected_segment_uid or "",
            "point_uid": self.selected_point_uid or "",
            "point_uids": list(self.selected_point_uids),
            "interaction_uid": self.selected_interaction_uid or "",
        }

    def _remember_synced_selection_snapshot(self):
        self._synced_selection_snapshot = self._capture_selection_snapshot()

    def _restore_selection_snapshot(self, snapshot):
        snapshot = snapshot or {}
        self.selected_axis_uid = snapshot.get("axis_uid", "") or ""
        self.selected_line_uid = snapshot.get("line_uid", "") or self.selected_line_uid
        self.selected_segment_uid = snapshot.get("segment_uid", "") or ""
        point_uids = list(snapshot.get("point_uids") or [])
        point_uid = snapshot.get("point_uid", "") or ""
        if point_uid and point_uid not in point_uids:
            point_uids.insert(0, point_uid)
        self._set_selected_points(point_uids)
        self.selected_interaction_uid = snapshot.get("interaction_uid", "") or ""

    def _prepare_view_state(self, data):
        self.axis_order = [axis["uid"] for axis in data.get("axis_nodes", [])]
        if self.selected_axis_uid not in self.axis_order:
            self.selected_axis_uid = self.axis_order[0] if self.axis_order else ""

        active_lines = list(data.get("lines", []))
        self.active_line_order = [line["uid"] for line in active_lines]

        all_line_ids = set(self.active_line_order)
        if self.selected_line_uid not in all_line_ids:
            self.selected_line_uid = (
                DEFAULT_PLOT_LINE_UID
                if DEFAULT_PLOT_LINE_UID in all_line_ids
                else (self.active_line_order[0] if self.active_line_order else "")
            )

        selected_line = self._find_line(data, self.selected_line_uid)
        self.segment_order = [segment.get("uid") for segment in selected_line.get("segments", [])] if selected_line else []
        if self.selected_segment_uid not in self.segment_order:
            default_segment = None
            if selected_line:
                if selected_line.get("segments"):
                    default_segment = selected_line["segments"][0]
            self.selected_segment_uid = default_segment.get("uid") if default_segment else ""

        segment = self._find_segment(selected_line, self.selected_segment_uid) if selected_line else None
        valid_point_uids = {
            point.get("uid")
            for point in (segment or {}).get("points", [])
            if point.get("uid")
        }
        if valid_point_uids:
            selected_point_uids = [uid for uid in self.selected_point_uids if uid in valid_point_uids]
            if self.selected_point_uid in valid_point_uids and self.selected_point_uid not in selected_point_uids:
                selected_point_uids.insert(0, self.selected_point_uid)
            self._set_selected_points(selected_point_uids)
        else:
            self._clear_point_selection()

        if self.selected_interaction_uid and not self._find_interaction(data, self.selected_interaction_uid):
            self.selected_interaction_uid = ""

        return active_lines

    def _sync_axis_list_selection(self):
        self.axis_list.selection_clear(0, tk.END)
        if self.selected_axis_uid in self.axis_order:
            self.axis_list.selection_set(self.axis_order.index(self.selected_axis_uid))

    def _sync_line_list_selection(self):
        self.active_line_list.selection_clear(0, tk.END)
        if self.selected_line_uid in self.active_line_order:
            self.active_line_list.selection_set(self.active_line_order.index(self.selected_line_uid))

    def _sync_selection_ui(self, data=None):
        data = data or self.project_manager.get_tone_outline()
        self._prepare_view_state(data)
        self._sync_axis_list_selection()
        self._sync_line_list_selection()
        self._refresh_segment_history(data)
        self._refresh_point_list(data)
        self._refresh_interaction_list(data)
        self._load_axis_form(data)
        self._load_line_form(data)
        self._load_segment_form(data)
        self._load_point_form(data)
        self._load_interaction_form(data)
        self.canvas.update_selection(
            self.selected_axis_uid,
            self.selected_line_uid,
            self.selected_segment_uid,
            self.selected_point_uid,
            self.selected_point_uids,
            self.selected_interaction_uid,
        )
        self._remember_synced_selection_snapshot()

    def _bind_config_mousewheel(self, _event=None):
        if hasattr(self, "_config_canvas") and self._config_canvas.winfo_exists():
            self._config_canvas.bind_all("<MouseWheel>", self._on_config_mousewheel)

    def _unbind_config_mousewheel(self, _event=None):
        if hasattr(self, "_config_canvas") and self._config_canvas.winfo_exists():
            self._config_canvas.unbind_all("<MouseWheel>")

    def _on_config_mousewheel(self, event):
        if hasattr(self, "_config_canvas") and self._config_canvas.winfo_exists():
            self._config_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _update_config_scrollregion(self, _event=None):
        if hasattr(self, "_config_canvas") and self._config_canvas.winfo_exists():
            self._config_canvas.configure(scrollregion=self._config_canvas.bbox("all"))

    def _sync_config_width(self, event):
        if hasattr(self, "_config_canvas_window"):
            self._config_canvas.itemconfigure(self._config_canvas_window, width=event.width)

    def _setup_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(
            toolbar,
            text="人物线直接由真实波动点决定范围，可在任意主轴节点拖拽实点或虚拟点生成关系。",
        ).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="从场景生成主轴", command=self.import_axis_from_scenes).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.RIGHT)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        canvas_frame = ttk.LabelFrame(paned, text="基调图")
        config_outer = ttk.Frame(paned)
        paned.add(canvas_frame, weight=3)
        paned.add(config_outer, weight=2)

        canvas_container = ttk.Frame(canvas_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        self.canvas = ToneOutlineCanvas(
            canvas_container,
            on_axis_selected=self.select_axis,
            on_segment_selected=self.select_segment,
            on_point_selected=self.select_point,
            on_points_selected=self.select_points,
            on_context_requested=self.show_canvas_context_menu,
            on_interaction_selected=self.select_interaction,
            on_segment_arc_drag=self.move_segment_arc,
            on_drag_preview=self.preview_drag_status,
            on_point_drag=self.move_point_by_drag,
            on_point_drag_preview=self.preview_point_drag_status,
            on_interaction_created=self.create_interaction_from_drag,
            on_interaction_retarget=self.retarget_interaction_from_drag,
            on_interaction_preview=self.preview_interaction_status,
            theme_manager=self.theme_manager,
        )
        h_scroll = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=h_scroll.set)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        h_scroll.pack(fill=tk.X)

        self._config_canvas = tk.Canvas(config_outer, highlightthickness=0, borderwidth=0)
        config_scroll = ttk.Scrollbar(config_outer, orient=tk.VERTICAL, command=self._config_canvas.yview)
        self._config_canvas.configure(yscrollcommand=config_scroll.set)
        config_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._config_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        config_frame = ttk.Frame(self._config_canvas)
        self._config_canvas_window = self._config_canvas.create_window((0, 0), window=config_frame, anchor="nw")
        config_frame.bind("<Configure>", self._update_config_scrollregion)
        self._config_canvas.bind("<Configure>", self._sync_config_width)
        for widget in (config_outer, self._config_canvas, config_frame):
            widget.bind("<Enter>", self._bind_config_mousewheel)
            widget.bind("<Leave>", self._unbind_config_mousewheel)

        axis_frame = ttk.LabelFrame(config_frame, text="主轴节点")
        axis_frame.pack(fill=tk.X, pady=(0, 8))
        self.axis_list = tk.Listbox(axis_frame, height=6, exportselection=False)
        self.axis_list.pack(fill=tk.X, padx=6, pady=(6, 4))
        self.axis_list.bind("<<ListboxSelect>>", self._on_axis_list_select)

        axis_btns = ttk.Frame(axis_frame)
        axis_btns.pack(fill=tk.X, padx=6)
        ttk.Button(axis_btns, text="新增", command=self.add_axis).pack(side=tk.LEFT)
        ttk.Button(axis_btns, text="删除", command=self.delete_axis).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(axis_btns, text="前移", command=lambda: self.move_axis(-1)).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(axis_btns, text="后移", command=lambda: self.move_axis(1)).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(axis_frame, text="节点标题").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Entry(axis_frame, textvariable=self.axis_title_var).pack(fill=tk.X, padx=6)
        ttk.Label(axis_frame, text="节点说明").pack(anchor="w", padx=6, pady=(6, 0))
        self.axis_desc_text = tk.Text(axis_frame, height=3, wrap="word")
        self.axis_desc_text.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(axis_frame, text="保存节点", command=self.save_axis).pack(anchor="e", padx=6, pady=(0, 6))

        line_frame = ttk.LabelFrame(config_frame, text="线管理")
        line_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(line_frame, text="线列表").pack(anchor="w", padx=6, pady=(6, 0))
        self.active_line_list = tk.Listbox(line_frame, height=4, exportselection=False)
        self.active_line_list.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.active_line_list.bind("<<ListboxSelect>>", self._on_active_line_select)

        line_btns = ttk.Frame(line_frame)
        line_btns.pack(fill=tk.X, padx=6, pady=(2, 0))
        ttk.Button(line_btns, text="新增人物线", command=self.add_character_line).pack(side=tk.LEFT)
        ttk.Button(line_btns, text="删除线", command=self.delete_line).pack(side=tk.LEFT, padx=(12, 0))

        ttk.Label(line_frame, text="线名").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Entry(line_frame, textvariable=self.line_name_var).pack(fill=tk.X, padx=6)
        ttk.Label(line_frame, text="类型 / 状态").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(line_frame, textvariable=self.line_type_var).pack(anchor="w", padx=6)
        ttk.Label(line_frame, textvariable=self.line_status_var, foreground="#666666").pack(anchor="w", padx=6, pady=(0, 2))
        ttk.Checkbutton(line_frame, text="显示这条线", variable=self.line_visible_var).pack(anchor="w", padx=6, pady=(2, 0))
        ttk.Label(line_frame, text="人物名").pack(anchor="w", padx=6, pady=(4, 0))
        ttk.Entry(line_frame, textvariable=self.line_character_var).pack(fill=tk.X, padx=6)
        ttk.Button(line_frame, text="保存线信息", command=self.save_line).pack(anchor="e", padx=6, pady=(6, 4))

        segment_frame = ttk.LabelFrame(config_frame, text="过程段")
        segment_frame.pack(fill=tk.X, pady=(0, 8))
        self.segment_history = tk.Listbox(segment_frame, height=5, exportselection=False)
        self.segment_history.pack(fill=tk.X, padx=6, pady=(6, 4))
        self.segment_history.bind("<<ListboxSelect>>", self._on_segment_list_select)

        segment_btns = ttk.Frame(segment_frame)
        segment_btns.pack(fill=tk.X, padx=6)
        ttk.Button(segment_btns, text="复制一段", command=self.copy_segment).pack(side=tk.LEFT)
        ttk.Button(segment_btns, text="在当前节点拆分", command=self.split_selected_segment).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(segment_btns, text="合并相邻段", command=self.merge_selected_segment).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(segment_btns, text="删除过程段", command=self.delete_segment).pack(side=tk.LEFT, padx=(12, 0))

        ttk.Label(segment_frame, text="当前过程段").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(segment_frame, textvariable=self.segment_range_var).pack(anchor="w", padx=6)
        ttk.Label(segment_frame, textvariable=self.segment_status_var, foreground="#666666").pack(anchor="w", padx=6)
        ttk.Label(segment_frame, text="阶段标题").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Entry(segment_frame, textvariable=self.segment_title_var).pack(fill=tk.X, padx=6)
        ttk.Label(segment_frame, text="说明分类").pack(anchor="w", padx=6, pady=(6, 0))
        self.segment_note_type_combo = ttk.Combobox(
            segment_frame,
            values=[label for _key, label in NOTE_TYPE_OPTIONS],
            textvariable=self.segment_note_type_var,
            state="readonly",
        )
        self.segment_note_type_combo.pack(fill=tk.X, padx=6)
        ttk.Label(segment_frame, text="起点").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(segment_frame, textvariable=self.segment_start_var).pack(anchor="w", padx=6)
        ttk.Label(segment_frame, text="终点").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(segment_frame, textvariable=self.segment_end_var).pack(anchor="w", padx=6)
        ttk.Label(segment_frame, text="中段拱度").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(segment_frame, textvariable=self.segment_arc_display_var, foreground="#0F766E").pack(anchor="w", padx=6)
        ttk.Label(
            segment_frame,
            text="在画布中拖动当前过程段中间圆点，上下调整整体弧度。",
            foreground="#666666",
            wraplength=220,
            justify=tk.LEFT,
        ).pack(anchor="w", padx=6, pady=(2, 0))
        ttk.Label(segment_frame, text="阶段说明").pack(anchor="w", padx=6, pady=(6, 0))
        self.segment_desc_text = tk.Text(segment_frame, height=3, wrap="word")
        self.segment_desc_text.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(segment_frame, text="保存过程段", command=self.save_segment).pack(anchor="e", padx=6, pady=(6, 6))

        point_frame = ttk.LabelFrame(config_frame, text="波动点")
        point_frame.pack(fill=tk.BOTH, expand=True)
        self.point_list = tk.Listbox(point_frame, height=6, exportselection=False, selectmode=tk.EXTENDED)
        self.point_list.pack(fill=tk.X, padx=6, pady=(6, 4))
        self.point_list.bind("<<ListboxSelect>>", self._on_point_list_select)

        point_btns = ttk.Frame(point_frame)
        point_btns.pack(fill=tk.X, padx=6)
        ttk.Button(point_btns, text="在当前节点新增", command=self.add_point).pack(side=tk.LEFT)
        ttk.Button(point_btns, text="删除波动点", command=self.delete_point).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(point_btns, text="清空选择", command=self.clear_point_selection).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(point_frame, text="当前节点").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(point_frame, textvariable=self.point_axis_var).pack(anchor="w", padx=6)
        ttk.Label(point_frame, textvariable=self.point_status_var, foreground="#666666").pack(anchor="w", padx=6, pady=(0, 2))
        ttk.Label(point_frame, text="节点类型").pack(anchor="w", padx=6, pady=(4, 0))
        self.point_node_type_combo = ttk.Combobox(
            point_frame,
            values=[label for _key, label in NODE_TYPE_OPTIONS],
            textvariable=self.point_node_type_var,
            state="readonly",
        )
        self.point_node_type_combo.pack(fill=tk.X, padx=6)
        ttk.Label(point_frame, text="说明分类").pack(anchor="w", padx=6, pady=(6, 0))
        self.point_note_type_combo = ttk.Combobox(
            point_frame,
            values=[label for _key, label in NOTE_TYPE_OPTIONS],
            textvariable=self.point_note_type_var,
            state="readonly",
        )
        self.point_note_type_combo.pack(fill=tk.X, padx=6)
        ttk.Label(point_frame, text="波动强度").pack(anchor="w", padx=6, pady=(6, 0))
        self._create_labeled_scale(
            point_frame,
            self.point_amplitude_var,
            self.point_amplitude_display_var,
            -100,
            100,
            1,
            digits=0,
            orient=tk.HORIZONTAL,
            length=180,
        )
        ttk.Label(point_frame, text="节点曲率").pack(anchor="w", padx=6, pady=(6, 0))
        self._create_labeled_scale(
            point_frame,
            self.point_curvature_var,
            self.point_curvature_display_var,
            0.10,
            1.50,
            0.05,
            digits=2,
            length=180,
        )
        ttk.Label(point_frame, text="标签").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Entry(point_frame, textvariable=self.point_label_var).pack(fill=tk.X, padx=6)
        ttk.Label(point_frame, text="标签组").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Entry(point_frame, textvariable=self.point_tags_var).pack(fill=tk.X, padx=6)
        ttk.Label(point_frame, text="情节/人物说明").pack(anchor="w", padx=6, pady=(6, 0))
        self.point_desc_text = tk.Text(point_frame, height=4, wrap="word")
        self.point_desc_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        ttk.Button(point_frame, text="保存 / 批量应用", command=self.save_point).pack(anchor="e", padx=6, pady=(0, 6))

        ttk.Separator(point_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=(2, 6))
        ttk.Label(point_frame, text="作用箭头").pack(anchor="w", padx=6)
        self.interaction_list = tk.Listbox(point_frame, height=4, exportselection=False)
        self.interaction_list.pack(fill=tk.X, padx=6, pady=(4, 4))
        self.interaction_list.bind("<<ListboxSelect>>", self._on_interaction_list_select)

        interaction_btns = ttk.Frame(point_frame)
        interaction_btns.pack(fill=tk.X, padx=6)
        ttk.Button(interaction_btns, text="拖拽新增", command=self.arm_interaction_drag).pack(side=tk.LEFT)
        ttk.Button(interaction_btns, text="删除箭头", command=self.delete_interaction).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(point_frame, text="箭头类型").pack(anchor="w", padx=6, pady=(6, 0))
        self.interaction_type_combo = ttk.Combobox(
            point_frame,
            values=[label for _key, label in INTERACTION_TYPE_OPTIONS],
            textvariable=self.interaction_type_var,
            state="readonly",
        )
        self.interaction_type_combo.pack(fill=tk.X, padx=6)
        ttk.Label(point_frame, text="来源").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(point_frame, textvariable=self.interaction_source_var).pack(anchor="w", padx=6)
        ttk.Label(point_frame, text="目标").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(point_frame, textvariable=self.interaction_target_var).pack(anchor="w", padx=6)
        ttk.Label(point_frame, text="箭头备注").pack(anchor="w", padx=6, pady=(6, 0))
        self.interaction_note_text = tk.Text(point_frame, height=3, wrap="word")
        self.interaction_note_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))
        ttk.Label(point_frame, textvariable=self.interaction_status_var, foreground="#666666").pack(anchor="w", padx=6, pady=(4, 2))
        ttk.Button(point_frame, text="保存箭头", command=self.save_interaction).pack(anchor="e", padx=6, pady=(0, 6))

    def refresh(self):
        data = self.project_manager.get_tone_outline()
        active_lines = self._prepare_view_state(data)
        self._refresh_axis_list(data)
        self._refresh_line_lists(active_lines)
        self._refresh_segment_history(data)
        self._refresh_point_list(data)
        self._refresh_interaction_list(data)
        self._load_axis_form(data)
        self._load_line_form(data)
        self._load_segment_form(data)
        self._load_point_form(data)
        self._load_interaction_form(data)
        self.canvas.set_state(
            data,
            self.selected_axis_uid,
            self.selected_line_uid,
            self.selected_segment_uid,
            self.selected_point_uid,
            self.selected_point_uids,
            self.selected_interaction_uid,
        )
        self._remember_synced_selection_snapshot()

    def select_axis(self, axis_uid):
        self.selected_axis_uid = axis_uid or ""
        self._clear_point_selection()
        self.selected_interaction_uid = ""
        self._sync_selection_ui()

    def select_line(self, line_uid):
        self.selected_line_uid = line_uid or ""
        self._clear_point_selection()
        self.selected_interaction_uid = ""
        self._sync_selection_ui()

    def select_segment(self, line_uid, segment_uid):
        self.selected_line_uid = line_uid or ""
        self.selected_segment_uid = segment_uid or ""
        self._clear_point_selection()
        self.selected_interaction_uid = ""
        self._sync_selection_ui()

    def select_point(self, line_uid, segment_uid, point_uid):
        self.selected_line_uid = line_uid or ""
        self.selected_segment_uid = segment_uid or ""
        self._set_selected_points([point_uid])
        self.selected_interaction_uid = ""
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        point = self._find_point(segment, self.selected_point_uid) if segment else None
        if point:
            self.selected_axis_uid = point.get("axis_uid") or self.selected_axis_uid
        self._sync_selection_ui(data)

    def select_points(self, line_uid, segment_uid, point_uids):
        self.selected_line_uid = line_uid or self.selected_line_uid
        self.selected_segment_uid = segment_uid or self.selected_segment_uid
        self._set_selected_points(point_uids)
        self.selected_interaction_uid = ""
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        point = self._find_point(segment, self.selected_point_uid) if segment else None
        if point:
            self.selected_axis_uid = point.get("axis_uid") or self.selected_axis_uid
        self._sync_selection_ui(data)

    def select_interaction(self, interaction_uid):
        data = self.project_manager.get_tone_outline()
        interaction = self._find_interaction(data, interaction_uid)
        if not interaction:
            return
        self.selected_interaction_uid = interaction_uid or ""
        self.selected_line_uid = interaction.get("source_line_uid", "") or self.selected_line_uid
        self.selected_segment_uid = interaction.get("source_segment_uid", "") or self.selected_segment_uid
        self._set_selected_points([interaction.get("source_point_uid", "") or self.selected_point_uid])
        self.selected_axis_uid = interaction.get("axis_uid", "") or self.selected_axis_uid
        self._sync_selection_ui(data)

    def move_segment_arc(self, line_uid, segment_uid, arc_height):
        self.selected_line_uid = line_uid or ""
        self.selected_segment_uid = segment_uid or ""
        self._clear_point_selection()
        normalized_arc = max(-100.0, min(100.0, float(arc_height)))

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            target_segment = self._find_segment(target_line, self.selected_segment_uid) if target_line else None
            if target_segment:
                target_segment["arc_height"] = normalized_arc

        self._apply_update(mutate, "调整过程段拱度")

    def preview_drag_status(self, message):
        if not message:
            data = self.project_manager.get_tone_outline()
            self._load_segment_form(data)
            return
        self.segment_status_var.set(message)

    def preview_interaction_status(self, message):
        if not message:
            data = self.project_manager.get_tone_outline()
            self._load_interaction_form(data)
            return
        self.interaction_status_var.set(message)

    def preview_point_drag_status(self, message):
        if not message:
            data = self.project_manager.get_tone_outline()
            self._load_point_form(data)
            return
        self.point_status_var.set(message)

    def move_point_by_drag(self, line_uid, segment_uid, point_uid, axis_uid, amplitude):
        if not line_uid or not axis_uid:
            return
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, line_uid)
        segment = self._find_segment(line, segment_uid) if line and segment_uid else None
        point = self._find_point(segment, point_uid) if segment and point_uid else None
        if not line:
            return
        if point_uid and not point:
            return
        if segment and any(
            other_point.get("uid") != point_uid and other_point.get("axis_uid") == axis_uid
            for other_point in segment.get("points", [])
        ):
            messagebox.showinfo(
                "提示",
                "当前过程段在该主轴节点上已经存在一个波动点，不能重复占用同一时间点。",
                parent=self.winfo_toplevel(),
            )
            existing = next(
                (
                    other_point
                    for other_point in segment.get("points", [])
                    if other_point.get("axis_uid") == axis_uid
                ),
                None,
            )
            if existing:
                self.selected_line_uid = line_uid
                self.selected_segment_uid = segment_uid
                self._set_selected_points([existing.get("uid", "")])
                self.selected_axis_uid = axis_uid
            self._sync_selection_ui(data)
            return

        created_segment_uid = ""
        created_point_uid = ""
        self.selected_line_uid = line_uid
        self.selected_segment_uid = segment_uid or ""
        self._set_selected_points([point_uid] if point_uid else [])
        self.selected_axis_uid = axis_uid

        def mutate(new_data):
            nonlocal created_segment_uid, created_point_uid
            target_line = self._find_line(new_data, line_uid)
            target_segment = self._find_segment(target_line, segment_uid) if target_line and segment_uid else None
            if target_line and not target_segment:
                created_segment_uid = self.project_manager._gen_uid()
                target_segment = {
                    "uid": created_segment_uid,
                    "start_axis_uid": axis_uid,
                    "end_axis_uid": axis_uid,
                    "arc_height": DEFAULT_SEGMENT_ARC,
                    "start_curve": DEFAULT_SEGMENT_CURVE,
                    "end_curve": DEFAULT_SEGMENT_CURVE,
                    "title": "",
                    "description": "",
                    "note_type": DEFAULT_NOTE_TYPE,
                    "points": [],
                }
                target_line.setdefault("segments", []).append(target_segment)
                self.selected_segment_uid = created_segment_uid
            if not target_segment:
                return
            target_point = self._find_point(target_segment, point_uid) if point_uid else None
            if target_point:
                target_point["axis_uid"] = axis_uid
                target_point["amplitude"] = float(amplitude)
                self.selected_segment_uid = target_segment.get("uid", "")
                self._set_selected_points([target_point.get("uid", "")])
                return
            created_point_uid = self.project_manager._gen_uid()
            target_segment.setdefault("points", []).append(
                {
                    "uid": created_point_uid,
                    "axis_uid": axis_uid,
                    "amplitude": float(amplitude),
                    "curvature": 0.45,
                    "label": "",
                    "description": "",
                    "node_type": DEFAULT_NODE_TYPE,
                    "note_type": DEFAULT_NOTE_TYPE,
                    "tags": [],
                }
            )
            self.selected_segment_uid = target_segment.get("uid", "") or created_segment_uid
            self._set_selected_points([created_point_uid])

        self._apply_update(mutate, "拖拽调整波动点" if point_uid else "拖拽生成波动点")

    def create_interaction_from_drag(
        self,
        source_line_uid,
        source_segment_uid,
        source_point_uid,
        target_line_uid,
        target_segment_uid,
        axis_uid,
        interaction_type,
    ):
        new_uid = self.project_manager._gen_uid()

        def mutate(data):
            data.setdefault("interactions", []).append(
                {
                    "uid": new_uid,
                    "axis_uid": axis_uid,
                    "source_line_uid": source_line_uid,
                    "source_segment_uid": source_segment_uid,
                    "source_point_uid": source_point_uid,
                    "target_line_uid": target_line_uid,
                    "target_segment_uid": target_segment_uid,
                    "interaction_type": interaction_type or DEFAULT_INTERACTION_TYPE,
                    "note": "",
                }
            )

        self.selected_interaction_uid = new_uid
        self._apply_update(mutate, "新增作用箭头")

    def retarget_interaction_from_drag(self, interaction_uid, target_line_uid, target_segment_uid):
        if not interaction_uid:
            return

        def mutate(data):
            target = self._find_interaction(data, interaction_uid)
            if target:
                target["target_line_uid"] = target_line_uid
                target["target_segment_uid"] = target_segment_uid

        self.selected_interaction_uid = interaction_uid
        self._apply_update(mutate, "调整作用箭头目标")

    def _refresh_axis_list(self, data):
        self.axis_list.delete(0, tk.END)
        for index, axis in enumerate(data.get("axis_nodes", [])):
            self.axis_list.insert(tk.END, f"{index + 1}. {axis.get('title', '未命名节点')}")
        if self.selected_axis_uid in self.axis_order:
            idx = self.axis_order.index(self.selected_axis_uid)
            self.axis_list.selection_clear(0, tk.END)
            self.axis_list.selection_set(idx)

    def _refresh_line_lists(self, active_lines):
        self.active_line_list.delete(0, tk.END)

        for line in active_lines:
            status = "主轴" if line.get("line_type") == "plot" else "人物"
            if not line.get("visible", True):
                status = f"{status}/隐藏"
            self.active_line_list.insert(tk.END, f"[{status}] {line.get('name', '未命名线')}")

        if self.selected_line_uid in self.active_line_order:
            idx = self.active_line_order.index(self.selected_line_uid)
            self.active_line_list.selection_clear(0, tk.END)
            self.active_line_list.selection_set(idx)

    def _refresh_segment_history(self, data):
        self.segment_history.delete(0, tk.END)
        line = self._find_line(data, self.selected_line_uid)
        if not line:
            self.segment_order = []
            return
        self.segment_order = [segment.get("uid") for segment in line.get("segments", [])]
        axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
        display_by_uid = {
            segment.get("uid"): segment
            for segment in get_display_segments(data, line)
        }

        if not self.segment_order and line.get("line_type") == "character":
            self.segment_history.insert(tk.END, "当前还没有波动点，可直接在主轴节点新增")
            self.selected_segment_uid = ""
            return

        for index, segment_uid in enumerate(self.segment_order):
            segment = display_by_uid.get(segment_uid) or self._find_segment(line, segment_uid) or {}
            if line.get("line_type") == "plot":
                text = f"情节段: {_range_text(axis_map, segment)}"
            else:
                text = f"第{index + 1}段: {_range_text(axis_map, segment)}"
            if segment.get("title"):
                text = f"{text} / {segment.get('title')}"
            self.segment_history.insert(tk.END, text)

        if self.selected_segment_uid in self.segment_order:
            idx = self.segment_order.index(self.selected_segment_uid)
            self.segment_history.selection_clear(0, tk.END)
            self.segment_history.selection_set(idx)
        elif self.segment_order:
            self.selected_segment_uid = self.segment_order[0]
            self.segment_history.selection_clear(0, tk.END)
            self.segment_history.selection_set(0)

    def _refresh_point_list(self, data):
        self.point_list.delete(0, tk.END)
        self.point_order = []
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
        axis_index_map = get_axis_index_map(data)
        if not segment:
            return
        points = sorted(
            segment.get("points", []),
            key=lambda item: axis_index_map.get(item.get("axis_uid"), 0),
        )
        for point in points:
            axis_title = axis_map.get(point.get("axis_uid"), {}).get("title", "未命名节点")
            amplitude = int(round(float(point.get("amplitude", 0))))
            label = point.get("label") or ""
            type_label = get_node_type_label(point.get("node_type", DEFAULT_NODE_TYPE))
            extra = f" / {label}" if label else f" / {type_label}"
            self.point_list.insert(tk.END, f"{axis_title} | {amplitude:+d}{extra}")
            self.point_order.append(point.get("uid"))
        selected_uids = [uid for uid in self.selected_point_uids if uid in self.point_order]
        if self.selected_point_uid in self.point_order and self.selected_point_uid not in selected_uids:
            selected_uids.insert(0, self.selected_point_uid)
        if selected_uids:
            self.point_list.selection_clear(0, tk.END)
            for point_uid in selected_uids:
                self.point_list.selection_set(self.point_order.index(point_uid))
            self._set_selected_points(selected_uids)
        elif self.selected_point_uid or self.selected_point_uids:
            self._clear_point_selection()

    def _refresh_interaction_list(self, data):
        self.interaction_list.delete(0, tk.END)
        self.interaction_order = []
        if len(self.selected_point_uids) > 1:
            self.selected_interaction_uid = ""
            return
        interactions = [
            interaction for interaction in data.get("interactions", [])
            if interaction.get("source_point_uid") == self.selected_point_uid
        ]
        line_map = {line.get("uid"): line for line in data.get("lines", [])}
        for interaction in interactions:
            target_line = line_map.get(interaction.get("target_line_uid"), {})
            label = get_interaction_label(interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE))
            note = _preview_text(interaction.get("note"), limit=12, empty="")
            note_suffix = f" / {note}" if note else ""
            self.interaction_list.insert(
                tk.END,
                f"{label} -> {target_line.get('name') or '未命名线'}{note_suffix}",
            )
            self.interaction_order.append(interaction.get("uid"))
        if self.selected_interaction_uid in self.interaction_order:
            idx = self.interaction_order.index(self.selected_interaction_uid)
            self.interaction_list.selection_clear(0, tk.END)
            self.interaction_list.selection_set(idx)
        elif self.selected_interaction_uid:
            self.selected_interaction_uid = ""

    def _load_axis_form(self, data):
        axis = self._find_axis(data, self.selected_axis_uid)
        self.axis_title_var.set(axis.get("title", "") if axis else "")
        self.axis_desc_text.delete("1.0", tk.END)
        if axis:
            self.axis_desc_text.insert("1.0", axis.get("description", ""))

    def _load_line_form(self, data):
        line = self._find_line(data, self.selected_line_uid)
        if not line:
            self.line_name_var.set("")
            self.line_type_var.set("")
            self.line_character_var.set("")
            self.line_status_var.set("")
            return
        self.line_name_var.set(line.get("name", ""))
        self.line_type_var.set("情节线" if line.get("line_type") == "plot" else "人物线")
        self.line_character_var.set(line.get("character_name", ""))
        self.line_visible_var.set(bool(line.get("visible", True)))
        if line.get("line_type") == "plot":
            self.line_status_var.set("情节线只在已有波动点范围内成形，新增空节点不会自动连线。")
        else:
            self.line_status_var.set("人物线可直接在任意主轴节点加点或拖点延展，不再区分引入/收束。")
        if not line.get("visible", True):
            self.line_status_var.set(f"{self.line_status_var.get()} 当前处于隐藏状态。")

    def _load_segment_form(self, data):
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        display_segment = self._find_display_segment(data, line, self.selected_segment_uid) if line else None
        axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
        self.segment_range_var.set("")
        self.segment_status_var.set("")
        self.segment_start_var.set("")
        self.segment_end_var.set("")
        self.segment_title_var.set("")
        self.segment_note_type_var.set(NOTE_TYPE_LABELS[DEFAULT_NOTE_TYPE])
        self.segment_arc_display_var.set("拱度 +0")
        self.segment_desc_text.delete("1.0", tk.END)
        if not line or not segment:
            return
        display_segment = display_segment or segment
        arc_height = float(display_segment.get("arc_height", segment.get("arc_height", DEFAULT_SEGMENT_ARC)))
        self.segment_range_var.set(_range_text(axis_map, display_segment))
        self.segment_title_var.set(segment.get("title", ""))
        self.segment_note_type_var.set(
            get_note_type_label(segment.get("note_type", DEFAULT_NOTE_TYPE))
        )
        self.segment_start_var.set(axis_map.get(display_segment.get("start_axis_uid"), {}).get("title", "未设置"))
        end_title = axis_map.get(display_segment.get("end_axis_uid"), {}).get("title", "未设置")
        self.segment_end_var.set(end_title)
        self.segment_arc_display_var.set(f"拱度 {arc_height:+.0f}")
        self.segment_desc_text.insert("1.0", segment.get("description", ""))
        if line.get("line_type") == "plot":
            self.segment_status_var.set("情节线范围由已有波动点自动决定，拖动点到新节点就会延展，新增空节点不会自动连线。")
        elif not segment.get("points"):
            self.segment_status_var.set("当前过程段还没有波动点，可直接在任意主轴节点新增。")
        else:
            self.segment_status_var.set("人物线范围会随波动点自动延展，左右拖点即可把关系续到下一个节点。")

    def _load_point_form(self, data):
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        selected_uids = []
        if segment:
            point_uids = {point.get("uid") for point in segment.get("points", []) if point.get("uid")}
            for point_uid in self.selected_point_uids:
                if point_uid in point_uids:
                    selected_uids.append(point_uid)
            if self.selected_point_uid in point_uids and self.selected_point_uid not in selected_uids:
                selected_uids.insert(0, self.selected_point_uid)
        point = self._find_point(segment, selected_uids[0]) if segment and selected_uids else None
        if selected_uids:
            self._set_selected_points(selected_uids)
        axis = self._find_axis(data, self.selected_axis_uid)
        self.point_axis_var.set(axis.get("title", "未选择节点") if axis else "未选择节点")
        self.point_status_var.set("")
        self.point_desc_text.delete("1.0", tk.END)
        if not point:
            self.point_label_var.set("")
            self.point_node_type_var.set(NODE_TYPE_LABELS[DEFAULT_NODE_TYPE])
            self.point_note_type_var.set(NOTE_TYPE_LABELS[DEFAULT_NOTE_TYPE])
            self.point_tags_var.set("")
            self.point_amplitude_var.set(0.0)
            self.point_curvature_var.set(0.45)
            if segment:
                self.point_status_var.set("可直接拖拽画布上的实点或虚拟节点；虚拟节点落下后会生成真实波动点，框选仍可批量应用。")
            elif line and line.get("line_type") == "character":
                self.point_status_var.set("当前人物线还没有波动点，可直接拖动画布上的虚拟节点生成第一处波动。")
            return
        if len(selected_uids) > 1:
            axis_map = {item.get("uid"): item.get("title", "未命名节点") for item in data.get("axis_nodes", [])}
            axis_titles = [
                axis_map.get(
                    (self._find_point(segment, point_uid) or {}).get("axis_uid"),
                    "未命名节点",
                )
                for point_uid in selected_uids[:3]
            ]
            preview = "、".join(axis_titles)
            if len(selected_uids) > 3:
                preview = f"{preview} 等"
            self.point_axis_var.set(f"已选 {len(selected_uids)} 个节点：{preview}")
        self.point_label_var.set(point.get("label", ""))
        self.point_node_type_var.set(
            get_node_type_label(point.get("node_type", DEFAULT_NODE_TYPE))
        )
        self.point_note_type_var.set(
            get_note_type_label(point.get("note_type", DEFAULT_NOTE_TYPE))
        )
        self.point_tags_var.set(", ".join(point.get("tags", [])))
        self.point_amplitude_var.set(float(point.get("amplitude", 0)))
        self.point_curvature_var.set(float(point.get("curvature", 0.45)))
        self.point_desc_text.insert("1.0", point.get("description", ""))
        if len(selected_uids) > 1:
            self.point_status_var.set(
                f"已选中 {len(selected_uids)} 个波动点，保存将批量应用当前表单值。拖拽和作用箭头仅支持单点。"
            )
        else:
            self.point_status_var.set("可在画布上直接拖拽这个波动点，调整发生时机与强度。")

    def _load_interaction_form(self, data):
        interaction = self._find_interaction(data, self.selected_interaction_uid)
        line_map = {line.get("uid"): line for line in data.get("lines", [])}
        axis_map = {axis.get("uid"): axis for axis in data.get("axis_nodes", [])}
        self.interaction_type_var.set(INTERACTION_TYPE_LABELS[DEFAULT_INTERACTION_TYPE])
        self.interaction_source_var.set("未选择波动点")
        self.interaction_target_var.set("未选择目标线段")
        self.interaction_note_text.delete("1.0", tk.END)
        if not interaction:
            if len(self.selected_point_uids) > 1:
                self.interaction_source_var.set("已选中多个波动点")
                self.interaction_status_var.set("请只保留一个波动点后，再创建或编辑作用箭头。")
            elif self.selected_point_uid:
                point = self._find_point(
                    self._find_segment(
                        self._find_line(data, self.selected_line_uid),
                        self.selected_segment_uid,
                    ),
                    self.selected_point_uid,
                )
                axis_title = axis_map.get((point or {}).get("axis_uid"), {}).get("title", "未命名节点")
                self.interaction_source_var.set(axis_title)
                self.interaction_status_var.set("可选择类型后点击“拖拽新增”，从当前点拖到同轴其他线段。")
            else:
                self.interaction_status_var.set("请先选中一个波动点，再创建作用箭头。")
            self.interaction_target_var.set("")
            return
        self.interaction_type_var.set(get_interaction_label(interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE)))
        source_line = line_map.get(interaction.get("source_line_uid"), {})
        target_line = line_map.get(interaction.get("target_line_uid"), {})
        axis_title = axis_map.get(interaction.get("axis_uid"), {}).get("title", "未命名节点")
        self.interaction_source_var.set(
            f"{source_line.get('name') or '未命名线'} / {axis_title}"
        )
        self.interaction_target_var.set(target_line.get("name") or "未命名线")
        self.interaction_note_text.insert("1.0", interaction.get("note") or "")
        self.interaction_status_var.set(
            "选中箭头后可修改类型、备注，也可以直接在画布上拖拽到新的目标线段。"
        )

    def _on_axis_list_select(self, _event=None):
        selection = self.axis_list.curselection()
        if not selection:
            return
        self.selected_axis_uid = self.axis_order[selection[0]]
        self._clear_point_selection()
        self.selected_interaction_uid = ""
        self._sync_selection_ui()

    def _on_active_line_select(self, _event=None):
        selection = self.active_line_list.curselection()
        if not selection:
            return
        self.selected_line_uid = self.active_line_order[selection[0]]
        self._clear_point_selection()
        self.selected_interaction_uid = ""
        self._sync_selection_ui()

    def _on_segment_list_select(self, _event=None):
        selection = self.segment_history.curselection()
        if not selection or not self.segment_order:
            return
        self.selected_segment_uid = self.segment_order[selection[0]]
        self._clear_point_selection()
        self.selected_interaction_uid = ""
        self._sync_selection_ui()

    def _on_point_list_select(self, _event=None):
        selection = self.point_list.curselection()
        if not selection:
            return
        point_uids = [
            self.point_order[index]
            for index in selection
            if 0 <= index < len(self.point_order)
        ]
        self._set_selected_points(point_uids)
        self.selected_interaction_uid = ""
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        point = self._find_point(segment, self.selected_point_uid) if segment else None
        if point:
            self.selected_axis_uid = point.get("axis_uid") or self.selected_axis_uid
        self._sync_selection_ui(data)

    def clear_point_selection(self):
        self._clear_point_selection()
        self.selected_interaction_uid = ""
        self._sync_selection_ui()

    def _selected_point_uid_list(self):
        point_uids = list(self.selected_point_uids)
        if self.selected_point_uid and self.selected_point_uid not in point_uids:
            point_uids.insert(0, self.selected_point_uid)
        return [point_uid for point_uid in point_uids if point_uid]

    def _ask_text_block(self, title, initial_value="", prompt=""):
        dialog = tk.Toplevel(self.winfo_toplevel())
        dialog.title(title)
        dialog.transient(self.winfo_toplevel())
        dialog.resizable(True, True)
        dialog.geometry("460x280")
        result = {"value": None}

        ttk.Frame(dialog, padding=10).pack(fill=tk.BOTH, expand=True)
        body = dialog.winfo_children()[0]
        if prompt:
            ttk.Label(body, text=prompt).pack(anchor="w", pady=(0, 6))
        text = tk.Text(body, wrap="word", height=10)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", initial_value or "")
        text.focus_set()

        buttons = ttk.Frame(body)
        buttons.pack(fill=tk.X, pady=(8, 0))

        def _confirm(_event=None):
            result["value"] = text.get("1.0", tk.END).strip()
            dialog.destroy()

        def _cancel(_event=None):
            dialog.destroy()

        ttk.Button(buttons, text="确定", command=_confirm).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="取消", command=_cancel).pack(side=tk.RIGHT, padx=(0, 6))
        dialog.bind("<Escape>", _cancel)
        dialog.bind("<Control-Return>", _confirm)
        dialog.protocol("WM_DELETE_WINDOW", _cancel)
        dialog.grab_set()
        self.winfo_toplevel().wait_window(dialog)
        return result["value"]

    def _update_axis_fields(self, axis_uid, description, **fields):
        if not axis_uid:
            return
        self.selected_axis_uid = axis_uid

        def mutate(data):
            axis = self._find_axis(data, axis_uid)
            if axis:
                axis.update(fields)

        self._apply_update(mutate, description)

    def _update_segment_fields(self, line_uid, segment_uid, description, **fields):
        if not line_uid or not segment_uid:
            return
        self.selected_line_uid = line_uid
        self.selected_segment_uid = segment_uid

        def mutate(data):
            line = self._find_line(data, line_uid)
            segment = self._find_segment(line, segment_uid) if line else None
            if segment:
                segment.update(fields)

        self._apply_update(mutate, description)

    def _update_point_fields(self, line_uid, segment_uid, point_uids, description, **fields):
        point_uids = [point_uid for point_uid in point_uids if point_uid]
        if not line_uid or not segment_uid or not point_uids:
            return
        self.selected_line_uid = line_uid
        self.selected_segment_uid = segment_uid
        self._set_selected_points(point_uids)

        def mutate(data):
            line = self._find_line(data, line_uid)
            segment = self._find_segment(line, segment_uid) if line else None
            if not segment:
                return
            for point_uid in point_uids:
                point = self._find_point(segment, point_uid)
                if point:
                    point.update(fields)

        self._apply_update(mutate, description)

    def _update_interaction_fields(self, interaction_uid, description, **fields):
        if not interaction_uid:
            return
        self.selected_interaction_uid = interaction_uid

        def mutate(data):
            interaction = self._find_interaction(data, interaction_uid)
            if interaction:
                interaction.update(fields)

        self._apply_update(mutate, description)

    def show_canvas_context_menu(self, kind, payload, x_root, y_root):
        menu = tk.Menu(self, tearoff=False)
        if kind == "axis":
            self._populate_axis_context_menu(menu, payload.get("axis_uid", ""))
        elif kind == "segment":
            self._populate_segment_context_menu(
                menu,
                payload.get("line_uid", ""),
                payload.get("segment_uid", ""),
            )
        elif kind == "point":
            self._populate_point_context_menu(
                menu,
                payload.get("line_uid", ""),
                payload.get("segment_uid", ""),
                payload.get("point_uid", ""),
            )
        elif kind == "interaction":
            self._populate_interaction_context_menu(menu, payload.get("interaction_uid", ""))
        if menu.index("end") is None:
            return
        try:
            menu.tk_popup(x_root, y_root)
        finally:
            menu.grab_release()

    def _populate_axis_context_menu(self, menu, axis_uid):
        data = self.project_manager.get_tone_outline()
        axis = self._find_axis(data, axis_uid)
        if not axis:
            return

        def edit_title():
            value = simpledialog.askstring(
                "编辑节点标题",
                "输入节点标题：",
                initialvalue=axis.get("title", ""),
                parent=self.winfo_toplevel(),
            )
            if value is None:
                return
            self._update_axis_fields(axis_uid, "右键编辑主轴节点标题", title=value.strip() or "未命名节点")

        def edit_description():
            value = self._ask_text_block("编辑节点说明", axis.get("description", ""), "输入当前主轴节点说明：")
            if value is None:
                return
            self._update_axis_fields(axis_uid, "右键编辑主轴节点说明", description=value)

        menu.add_command(label="编辑节点标题...", command=edit_title)
        menu.add_command(label="编辑节点说明...", command=edit_description)
        menu.add_separator()
        menu.add_command(label="前移节点", command=lambda: (self.select_axis(axis_uid), self.move_axis(-1)))
        menu.add_command(label="后移节点", command=lambda: (self.select_axis(axis_uid), self.move_axis(1)))
        menu.add_separator()
        menu.add_command(label="删除节点", command=lambda: (self.select_axis(axis_uid), self.delete_axis()))

    def _populate_segment_context_menu(self, menu, line_uid, segment_uid):
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, line_uid)
        segment = self._find_segment(line, segment_uid) if line else None
        if not line or not segment:
            return

        def edit_title():
            value = simpledialog.askstring(
                "编辑阶段标题",
                "输入阶段标题：",
                initialvalue=segment.get("title", ""),
                parent=self.winfo_toplevel(),
            )
            if value is None:
                return
            self._update_segment_fields(line_uid, segment_uid, "右键编辑过程段标题", title=value.strip())

        def edit_description():
            value = self._ask_text_block("编辑阶段说明", segment.get("description", ""), "输入当前过程段说明：")
            if value is None:
                return
            self._update_segment_fields(line_uid, segment_uid, "右键编辑过程段说明", description=value)

        menu.add_command(label="编辑阶段标题...", command=edit_title)
        menu.add_command(label="编辑阶段说明...", command=edit_description)

        note_menu = tk.Menu(menu, tearoff=False)
        for note_key, note_label in NOTE_TYPE_OPTIONS:
            note_menu.add_command(
                label=note_label,
                command=lambda value=note_key: self._update_segment_fields(
                    line_uid,
                    segment_uid,
                    "右键切换过程段说明分类",
                    note_type=value,
                ),
            )
        menu.add_cascade(label="说明分类", menu=note_menu)
        menu.add_separator()
        menu.add_command(label="复制一段", command=lambda: (self.select_segment(line_uid, segment_uid), self.copy_segment()))
        menu.add_command(
            label="删除过程段",
            state=tk.DISABLED if line.get("line_type") == "plot" else tk.NORMAL,
            command=lambda: (self.select_segment(line_uid, segment_uid), self.delete_segment()),
        )

    def _populate_point_context_menu(self, menu, line_uid, segment_uid, point_uid):
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, line_uid)
        segment = self._find_segment(line, segment_uid) if line else None
        point = self._find_point(segment, point_uid) if segment else None
        if not line or not segment or not point:
            return
        point_uids = self._selected_point_uid_list()
        if point_uid not in point_uids:
            point_uids = [point_uid]
        count = len(point_uids)
        action_prefix = f"批量设置 {count} 个波动点" if count > 1 else "编辑波动点"

        def edit_label():
            value = simpledialog.askstring(
                "编辑标签",
                "输入波动点标签：",
                initialvalue=point.get("label", ""),
                parent=self.winfo_toplevel(),
            )
            if value is None:
                return
            self._update_point_fields(line_uid, segment_uid, point_uids, f"{action_prefix}标签", label=value.strip())

        def edit_description():
            value = self._ask_text_block("编辑说明", point.get("description", ""), "输入波动点说明：")
            if value is None:
                return
            self._update_point_fields(line_uid, segment_uid, point_uids, f"{action_prefix}说明", description=value)

        def edit_tags():
            value = simpledialog.askstring(
                "编辑标签组",
                "输入标签组，使用逗号分隔：",
                initialvalue=", ".join(point.get("tags", [])),
                parent=self.winfo_toplevel(),
            )
            if value is None:
                return
            tags = [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
            self._update_point_fields(line_uid, segment_uid, point_uids, f"{action_prefix}标签组", tags=tags)

        def edit_float(field_name, title, prompt, min_value, max_value):
            value = simpledialog.askfloat(
                title,
                prompt,
                initialvalue=float(point.get(field_name, 0)),
                minvalue=min_value,
                maxvalue=max_value,
                parent=self.winfo_toplevel(),
            )
            if value is None:
                return
            digits = 2 if field_name == "curvature" else 0
            normalized = round(float(value), digits)
            self._update_point_fields(line_uid, segment_uid, point_uids, f"{action_prefix}{title}", **{field_name: normalized})

        menu.add_command(label="编辑标签...", command=edit_label)
        menu.add_command(label="编辑说明...", command=edit_description)
        menu.add_command(label="编辑标签组...", command=edit_tags)
        menu.add_command(label="编辑波动强度...", command=lambda: edit_float("amplitude", "波动强度", "输入强度（-100 到 100）：", -100.0, 100.0))
        menu.add_command(label="编辑节点曲率...", command=lambda: edit_float("curvature", "节点曲率", "输入曲率（0.10 到 1.50）：", 0.10, 1.50))

        node_type_menu = tk.Menu(menu, tearoff=False)
        for node_key, node_label in NODE_TYPE_OPTIONS:
            node_type_menu.add_command(
                label=node_label,
                command=lambda value=node_key: self._update_point_fields(
                    line_uid,
                    segment_uid,
                    point_uids,
                    f"{action_prefix}节点类型",
                    node_type=value,
                ),
            )
        menu.add_cascade(label="节点类型", menu=node_type_menu)

        note_menu = tk.Menu(menu, tearoff=False)
        for note_key, note_label in NOTE_TYPE_OPTIONS:
            note_menu.add_command(
                label=note_label,
                command=lambda value=note_key: self._update_point_fields(
                    line_uid,
                    segment_uid,
                    point_uids,
                    f"{action_prefix}说明分类",
                    note_type=value,
                ),
            )
        menu.add_cascade(label="说明分类", menu=note_menu)
        menu.add_separator()
        if count == 1:
            menu.add_command(label="创建作用箭头", command=lambda: (self.select_point(line_uid, segment_uid, point_uid), self.arm_interaction_drag()))
        menu.add_command(label="删除波动点", command=lambda: (self._set_selected_points(point_uids), self.delete_point()))

    def _populate_interaction_context_menu(self, menu, interaction_uid):
        data = self.project_manager.get_tone_outline()
        interaction = self._find_interaction(data, interaction_uid)
        if not interaction:
            return

        def edit_note():
            value = self._ask_text_block("编辑箭头备注", interaction.get("note", ""), "输入作用箭头备注：")
            if value is None:
                return
            self._update_interaction_fields(interaction_uid, "右键编辑作用箭头备注", note=value)

        menu.add_command(label="编辑箭头备注...", command=edit_note)
        type_menu = tk.Menu(menu, tearoff=False)
        for interaction_key, interaction_label in INTERACTION_TYPE_OPTIONS:
            type_menu.add_command(
                label=interaction_label,
                command=lambda value=interaction_key: self._update_interaction_fields(
                    interaction_uid,
                    "右键切换作用箭头类型",
                    interaction_type=value,
                ),
            )
        menu.add_cascade(label="箭头类型", menu=type_menu)
        menu.add_separator()
        menu.add_command(label="删除作用箭头", command=lambda: (self.select_interaction(interaction_uid), self.delete_interaction()))

    def _on_interaction_list_select(self, _event=None):
        selection = self.interaction_list.curselection()
        if not selection or not self.interaction_order:
            return
        self.selected_interaction_uid = self.interaction_order[selection[0]]
        self._sync_selection_ui()

    def add_axis(self):
        title = simpledialog.askstring("新增主轴节点", "输入节点标题：", parent=self.winfo_toplevel())
        if not title:
            return
        new_uid = self.project_manager._gen_uid()

        def mutate(data):
            axis_nodes = data.setdefault("axis_nodes", [])
            insert_index = len(axis_nodes)
            if self.selected_axis_uid in [axis.get("uid") for axis in axis_nodes]:
                insert_index = [axis.get("uid") for axis in axis_nodes].index(self.selected_axis_uid) + 1
            axis_nodes.insert(insert_index, {"uid": new_uid, "title": title.strip(), "description": ""})

        self.selected_axis_uid = new_uid
        self._apply_update(mutate, "新增基调节点")

    def delete_axis(self):
        if not self.selected_axis_uid:
            return
        if not messagebox.askyesno(
            "删除节点",
            "删除主轴节点会移除该节点上的波动点，并调整引用它的过程段。是否继续？",
            parent=self.winfo_toplevel(),
        ):
            return
        deleted_uid = self.selected_axis_uid
        old_axis_order = list(self.axis_order)

        def mutate(data):
            axis_nodes = data.get("axis_nodes", [])
            data["axis_nodes"] = [axis for axis in axis_nodes if axis.get("uid") != deleted_uid]
            remaining = [axis.get("uid") for axis in data.get("axis_nodes", [])]
            deleted_index = old_axis_order.index(deleted_uid)
            prev_uid = next((uid for uid in reversed(old_axis_order[:deleted_index]) if uid in remaining), "")
            next_uid = next((uid for uid in old_axis_order[deleted_index + 1 :] if uid in remaining), "")

            for line in data.get("lines", []):
                for segment in line.get("segments", []):
                    segment["points"] = [
                        point for point in segment.get("points", [])
                        if point.get("axis_uid") != deleted_uid
                    ]
                    if line.get("line_type") == "plot":
                        continue
                    start_uid = segment.get("start_axis_uid")
                    end_uid = segment.get("end_axis_uid") or ""
                    if start_uid == deleted_uid:
                        start_uid = next_uid or prev_uid
                    if end_uid == deleted_uid:
                        end_uid = prev_uid
                    segment["start_axis_uid"] = start_uid
                    segment["end_axis_uid"] = end_uid
                if line.get("line_type") == "character":
                    line["segments"] = [
                        segment for segment in line.get("segments", [])
                        if segment.get("start_axis_uid")
                    ]

        self.selected_axis_uid = ""
        self._clear_point_selection()
        self._apply_update(mutate, "删除基调节点")

    def move_axis(self, delta):
        data = self.project_manager.get_tone_outline()
        axis_ids = [axis.get("uid") for axis in data.get("axis_nodes", [])]
        if self.selected_axis_uid not in axis_ids:
            return

        def mutate(new_data):
            axis_nodes = new_data.get("axis_nodes", [])
            index = [axis.get("uid") for axis in axis_nodes].index(self.selected_axis_uid)
            new_index = max(0, min(len(axis_nodes) - 1, index + delta))
            if new_index == index:
                return
            axis = axis_nodes.pop(index)
            axis_nodes.insert(new_index, axis)

        self._apply_update(mutate, "调整主轴节点顺序")

    def save_axis(self):
        if not self.selected_axis_uid:
            return
        title = self.axis_title_var.get().strip() or "未命名节点"
        description = self.axis_desc_text.get("1.0", tk.END).strip()

        def mutate(data):
            axis = self._find_axis(data, self.selected_axis_uid)
            if axis:
                axis["title"] = title
                axis["description"] = description

        self._apply_update(mutate, "编辑主轴节点")

    def add_character_line(self):
        axis_nodes = self.project_manager.get_tone_outline().get("axis_nodes", [])
        if not axis_nodes:
            messagebox.showinfo("提示", "请先建立主轴节点。", parent=self.winfo_toplevel())
            return
        character_name = simpledialog.askstring("新增人物线", "输入人物名：", parent=self.winfo_toplevel())
        if not character_name:
            return
        new_uid = self.project_manager._gen_uid()

        def mutate(data):
            data.setdefault("lines", []).append(
                {
                    "uid": new_uid,
                    "name": f"{character_name.strip()}线",
                    "line_type": "character",
                    "character_name": character_name.strip(),
                    "color": get_next_tone_line_color(data.get("lines", [])),
                    "visible": True,
                    "segments": [],
                }
            )

        self.selected_line_uid = new_uid
        self.selected_segment_uid = ""
        self._clear_point_selection()
        self._apply_update(mutate, "新增人物基调线")

    def delete_line(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        if not line:
            return
        if line.get("line_type") == "plot":
            messagebox.showinfo("提示", "情节线是固定主线，不支持删除。", parent=self.winfo_toplevel())
            return

        def mutate(data):
            data["lines"] = [item for item in data.get("lines", []) if item.get("uid") != self.selected_line_uid]

        self._clear_point_selection()
        self.selected_segment_uid = ""
        self.selected_line_uid = DEFAULT_PLOT_LINE_UID
        self._apply_update(mutate, "删除人物线")

    def save_line(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        if not line:
            return
        name = self.line_name_var.get().strip() or line.get("name") or "未命名线"
        character_name = self.line_character_var.get().strip()
        visible = bool(self.line_visible_var.get())

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            if target_line:
                target_line["name"] = name
                target_line["visible"] = visible
                if target_line.get("line_type") == "character":
                    target_line["character_name"] = character_name

        self._apply_update(mutate, "编辑线信息")

    def copy_segment(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        if not line or not segment:
            return
        if line.get("line_type") == "plot":
            messagebox.showinfo("提示", "情节线固定全程，不支持复制过程段。", parent=self.winfo_toplevel())
            return

        new_segment_uid = ""

        def mutate(data):
            nonlocal new_segment_uid
            target_line = self._find_line(data, self.selected_line_uid)
            if target_line:
                new_segment_uid = duplicate_segment(
                    target_line,
                    self.selected_segment_uid,
                    uid_generator=self.project_manager._gen_uid,
                )
            if new_segment_uid:
                self.selected_segment_uid = new_segment_uid
                self._clear_point_selection()

        self._apply_update(mutate, "复制过程段")

    def split_selected_segment(self):
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        if not line or not segment:
            return
        if line.get("line_type") == "plot":
            messagebox.showinfo("提示", "情节线固定全程，不支持拆分过程段。", parent=self.winfo_toplevel())
            return
        if not self.selected_axis_uid:
            messagebox.showinfo("提示", "请先选择一个用于拆分的主轴节点。", parent=self.winfo_toplevel())
            return

        axis_index_map = get_axis_index_map(data)
        last_axis_uid = data.get("axis_nodes", [])[-1]["uid"] if data.get("axis_nodes") else ""
        display_segment = self._find_display_segment(data, line, self.selected_segment_uid) or segment
        if not axis_in_segment(
            self.selected_axis_uid,
            display_segment,
            axis_index_map,
            last_axis_uid=last_axis_uid,
        ):
            messagebox.showinfo("提示", "拆分节点不在当前过程段内。", parent=self.winfo_toplevel())
            return

        left_uid = ""
        right_uid = ""

        def mutate(new_data):
            nonlocal left_uid, right_uid
            target_line = self._find_line(new_data, self.selected_line_uid)
            if target_line:
                left_uid, right_uid = split_segment(
                    target_line,
                    self.selected_segment_uid,
                    self.selected_axis_uid,
                    get_axis_index_map(new_data),
                    uid_generator=self.project_manager._gen_uid,
                    last_axis_uid=new_data.get("axis_nodes", [])[-1]["uid"] if new_data.get("axis_nodes") else "",
                )
            if right_uid:
                self.selected_segment_uid = right_uid
                self._clear_point_selection()

        self._apply_update(mutate, "拆分过程段")
        if not left_uid:
            messagebox.showinfo(
                "提示",
                "拆分节点必须位于过程段内部，不能等于起点或终点。",
                parent=self.winfo_toplevel(),
            )

    def merge_selected_segment(self):
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        if not line or not self.selected_segment_uid:
            return
        if line.get("line_type") == "plot":
            messagebox.showinfo("提示", "情节线固定全程，不支持合并过程段。", parent=self.winfo_toplevel())
            return
        segments = line.get("segments", [])
        if len(segments) < 2:
            messagebox.showinfo("提示", "当前线没有可合并的相邻过程段。", parent=self.winfo_toplevel())
            return
        current_index = next(
            (index for index, segment in enumerate(segments) if segment.get("uid") == self.selected_segment_uid),
            -1,
        )
        if current_index < 0:
            return

        first_uid = ""
        second_uid = ""
        if current_index == 0:
            first_uid = segments[0].get("uid", "")
            second_uid = segments[1].get("uid", "")
        elif current_index == len(segments) - 1:
            first_uid = segments[-2].get("uid", "")
            second_uid = segments[-1].get("uid", "")
        else:
            decision = messagebox.askyesnocancel(
                "合并相邻段",
                "选择“是”与上一段合并，选择“否”与下一段合并。",
                parent=self.winfo_toplevel(),
            )
            if decision is None:
                return
            if decision:
                first_uid = segments[current_index - 1].get("uid", "")
                second_uid = segments[current_index].get("uid", "")
            else:
                first_uid = segments[current_index].get("uid", "")
                second_uid = segments[current_index + 1].get("uid", "")

        conflict_strategy = "first"
        axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
        conflicts = analyze_merge_conflicts(line, first_uid, second_uid)
        if conflicts:
            blocks = []
            for conflict in conflicts:
                axis_title = axis_map.get(conflict.get("axis_uid"), {}).get("title", conflict.get("axis_uid") or "未命名节点")
                first_point = conflict.get("first_point", {})
                second_point = conflict.get("second_point", {})
                blocks.append(
                    f"{axis_title}\n"
                    f"  前段：强度 {int(round(float(first_point.get('amplitude', 0)))):+d}"
                    f" | 曲率 {float(first_point.get('curvature', 0.45)):.2f}"
                    f" | 标签 {_preview_text(first_point.get('label'), limit=14, empty='无标签')}"
                    f" | 说明 {_preview_text(first_point.get('description'), limit=22)}\n"
                    f"  后段：强度 {int(round(float(second_point.get('amplitude', 0)))):+d}"
                    f" | 曲率 {float(second_point.get('curvature', 0.45)):.2f}"
                    f" | 标签 {_preview_text(second_point.get('label'), limit=14, empty='无标签')}"
                    f" | 说明 {_preview_text(second_point.get('description'), limit=22)}"
                )
            detail_text = "\n\n".join(blocks[:3])
            if len(blocks) > 3:
                detail_text += f"\n\n... 另有 {len(blocks) - 3} 个冲突节点"
            decision = messagebox.askyesnocancel(
                "合并冲突",
                "相邻过程段在同一节点上存在不同波动值。\n"
                f"{detail_text}\n\n"
                "选择“是”保留前段节点值，选择“否”保留后段节点值。",
                parent=self.winfo_toplevel(),
            )
            if decision is None:
                return
            conflict_strategy = "first" if decision else "second"

        merged_uid = ""

        def mutate(new_data):
            nonlocal merged_uid
            target_line = self._find_line(new_data, self.selected_line_uid)
            if target_line:
                merged_uid = merge_adjacent_segments(
                    target_line,
                    first_uid,
                    second_uid,
                    get_axis_index_map(new_data),
                    uid_generator=self.project_manager._gen_uid,
                    conflict_strategy=conflict_strategy,
                )
            if merged_uid:
                self.selected_segment_uid = merged_uid
                self._clear_point_selection()

        self._apply_update(mutate, "合并过程段")

    def delete_segment(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        if not line or not self.selected_segment_uid:
            return
        if line.get("line_type") == "plot":
            messagebox.showinfo("提示", "情节线固定全程，不支持删除唯一过程段。", parent=self.winfo_toplevel())
            return

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            if target_line:
                target_line["segments"] = [
                    segment for segment in target_line.get("segments", [])
                    if segment.get("uid") != self.selected_segment_uid
                ]

        self._clear_point_selection()
        self.selected_segment_uid = ""
        self._apply_update(mutate, "删除过程段")

    def save_segment(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        if not segment:
            return
        title = self.segment_title_var.get().strip()
        note_type = NOTE_LABEL_TO_TYPE.get(
            self.segment_note_type_var.get(),
            DEFAULT_NOTE_TYPE,
        )
        description = self.segment_desc_text.get("1.0", tk.END).strip()

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            target_segment = self._find_segment(target_line, self.selected_segment_uid) if target_line else None
            if target_segment:
                target_segment["title"] = title
                target_segment["note_type"] = note_type
                target_segment["description"] = description

        self._apply_update(mutate, "编辑过程段")

    def add_point(self):
        if not self.selected_line_uid or not self.selected_axis_uid:
            messagebox.showinfo("提示", "请先选择一条线和一个主轴节点。", parent=self.winfo_toplevel())
            return
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        if not line:
            return
        new_segment_uid = ""

        def mutate(new_data):
            nonlocal new_segment_uid
            target_line = self._find_line(new_data, self.selected_line_uid)
            target_segment = self._find_segment(target_line, self.selected_segment_uid) if target_line else None
            if target_line and not target_segment:
                new_segment_uid = self.project_manager._gen_uid()
                target_segment = {
                    "uid": new_segment_uid,
                    "start_axis_uid": self.selected_axis_uid,
                    "end_axis_uid": self.selected_axis_uid,
                    "arc_height": DEFAULT_SEGMENT_ARC,
                    "start_curve": DEFAULT_SEGMENT_CURVE,
                    "end_curve": DEFAULT_SEGMENT_CURVE,
                    "title": "",
                    "description": "",
                    "note_type": DEFAULT_NOTE_TYPE,
                    "points": [],
                }
                target_line.setdefault("segments", []).append(target_segment)
                self.selected_segment_uid = new_segment_uid
            if not target_segment:
                return
            existing = next(
                (
                    point for point in target_segment.get("points", [])
                    if point.get("axis_uid") == self.selected_axis_uid
                ),
                None,
            )
            if existing:
                self._set_selected_points([existing.get("uid")])
                return
            point_uid = self.project_manager._gen_uid()
            target_segment.setdefault("points", []).append(
                {
                    "uid": point_uid,
                    "axis_uid": self.selected_axis_uid,
                    "amplitude": 0,
                    "curvature": 0.45,
                    "label": "",
                    "description": "",
                    "node_type": DEFAULT_NODE_TYPE,
                    "note_type": DEFAULT_NOTE_TYPE,
                    "tags": [],
                }
            )
            self._set_selected_points([point_uid])

        self._apply_update(mutate, "新增波动点")

    def delete_point(self):
        point_uids = list(self.selected_point_uids)
        if self.selected_point_uid and self.selected_point_uid not in point_uids:
            point_uids.insert(0, self.selected_point_uid)
        point_uids = [point_uid for point_uid in point_uids if point_uid]
        if not point_uids:
            return
        point_uid_set = set(point_uids)

        def mutate(data):
            line = self._find_line(data, self.selected_line_uid)
            segment = self._find_segment(line, self.selected_segment_uid) if line else None
            if segment:
                segment["points"] = [
                    point for point in segment.get("points", [])
                    if point.get("uid") not in point_uid_set
                ]

        self._clear_point_selection()
        self._apply_update(mutate, "批量删除波动点" if len(point_uids) > 1 else "删除波动点")

    def save_point(self):
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        point_uids = list(self.selected_point_uids)
        if self.selected_point_uid and self.selected_point_uid not in point_uids:
            point_uids.insert(0, self.selected_point_uid)
        point_uids = [point_uid for point_uid in point_uids if point_uid]
        point = self._find_point(segment, point_uids[0]) if segment and point_uids else None
        if not point:
            return
        label = self.point_label_var.get().strip()
        description = self.point_desc_text.get("1.0", tk.END).strip()
        node_type = NODE_LABEL_TO_TYPE.get(
            self.point_node_type_var.get(),
            DEFAULT_NODE_TYPE,
        )
        note_type = NOTE_LABEL_TO_TYPE.get(
            self.point_note_type_var.get(),
            DEFAULT_NOTE_TYPE,
        )
        tags = [item.strip() for item in self.point_tags_var.get().replace("，", ",").split(",") if item.strip()]
        amplitude = float(self.point_amplitude_var.get())
        curvature = float(self.point_curvature_var.get())

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            target_segment = self._find_segment(target_line, self.selected_segment_uid) if target_line else None
            if not target_segment:
                return
            for point_uid in point_uids:
                target_point = self._find_point(target_segment, point_uid)
                if not target_point:
                    continue
                target_point["label"] = label
                target_point["description"] = description
                target_point["node_type"] = node_type
                target_point["note_type"] = note_type
                target_point["tags"] = tags
                target_point["amplitude"] = amplitude
                target_point["curvature"] = curvature

        self._set_selected_points(point_uids)
        self._apply_update(mutate, "批量编辑波动点" if len(point_uids) > 1 else "编辑波动点")

    def arm_interaction_drag(self):
        point_uids = list(self.selected_point_uids)
        if self.selected_point_uid and self.selected_point_uid not in point_uids:
            point_uids.insert(0, self.selected_point_uid)
        point_uids = [point_uid for point_uid in point_uids if point_uid]
        if len(point_uids) > 1:
            messagebox.showinfo("提示", "请只保留一个波动点后，再拖拽创建作用箭头。", parent=self.winfo_toplevel())
            return
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        segment = self._find_segment(line, self.selected_segment_uid) if line else None
        point_uid = point_uids[0] if point_uids else self.selected_point_uid
        point = self._find_point(segment, point_uid) if segment else None
        if not line or not segment or not point:
            messagebox.showinfo("提示", "请先选中一个波动点，再拖拽创建作用箭头。", parent=self.winfo_toplevel())
            return
        interaction_type = INTERACTION_LABEL_TO_TYPE.get(
            self.interaction_type_var.get(),
            DEFAULT_INTERACTION_TYPE,
        )
        self._set_selected_points([point_uid])
        self.selected_interaction_uid = ""
        self.canvas.arm_interaction_creation(
            self.selected_line_uid,
            self.selected_segment_uid,
            point_uid,
            point.get("axis_uid", ""),
            interaction_type,
        )
        self.interaction_status_var.set("已进入拖拽模式：从当前点拖到同轴的其他线段。")

    def save_interaction(self):
        interaction = self._find_interaction(
            self.project_manager.get_tone_outline(),
            self.selected_interaction_uid,
        )
        if not interaction:
            return
        interaction_type = INTERACTION_LABEL_TO_TYPE.get(
            self.interaction_type_var.get(),
            DEFAULT_INTERACTION_TYPE,
        )
        note = self.interaction_note_text.get("1.0", tk.END).strip()

        def mutate(data):
            target = self._find_interaction(data, self.selected_interaction_uid)
            if target:
                target["interaction_type"] = interaction_type
                target["note"] = note

        self._apply_update(mutate, "编辑作用箭头")

    def delete_interaction(self):
        if not self.selected_interaction_uid:
            return
        interaction_uid = self.selected_interaction_uid

        def mutate(data):
            data["interactions"] = [
                interaction
                for interaction in data.get("interactions", [])
                if interaction.get("uid") != interaction_uid
            ]

        self.selected_interaction_uid = ""
        self.canvas.clear_interaction_creation()
        self._apply_update(mutate, "删除作用箭头")

    def import_axis_from_scenes(self):
        scenes = self.project_manager.get_scenes()
        if not scenes:
            messagebox.showinfo("提示", "当前项目没有场景，无法自动生成主轴。", parent=self.winfo_toplevel())
            return
        if self.project_manager.get_tone_outline().get("axis_nodes") and not messagebox.askyesno(
            "覆盖主轴",
            "从场景生成会重建主轴节点，并清空所有线段与波动点。是否继续？",
            parent=self.winfo_toplevel(),
        ):
            return

        def mutate(data):
            axis_nodes = build_axis_nodes_from_scenes(scenes, self.project_manager._gen_uid)
            data["axis_nodes"] = axis_nodes
            for line in data.get("lines", []):
                if line.get("line_type") == "plot":
                    for segment in line.get("segments", []):
                        segment["points"] = []
                        segment["arc_height"] = DEFAULT_SEGMENT_ARC
                        segment["start_curve"] = DEFAULT_SEGMENT_CURVE
                        segment["end_curve"] = DEFAULT_SEGMENT_CURVE
                else:
                    line["segments"] = []
            data["interactions"] = []
            if axis_nodes:
                self.selected_axis_uid = axis_nodes[0]["uid"]

        self.selected_segment_uid = ""
        self._clear_point_selection()
        self.selected_interaction_uid = ""
        self._apply_update(mutate, "从场景生成主轴")

    def _apply_update(self, mutator, description):
        before_selection = dict(self._synced_selection_snapshot or self._capture_selection_snapshot())
        old_data = clone_tone_outline(self.project_manager.get_tone_outline())
        new_data = clone_tone_outline(old_data)
        mutator(new_data)
        ensure_tone_outline_defaults(new_data, uid_generator=self.project_manager._gen_uid)
        after_selection = self._capture_selection_snapshot()
        if old_data == new_data:
            self._sync_selection_ui(old_data)
            return
        command = UpdateToneOutlineCommand(
            self.project_manager,
            old_data,
            new_data,
            description,
            before_selection=before_selection,
            after_selection=after_selection,
            selection_restorer=self._restore_selection_snapshot,
        )
        if self.command_executor(command):
            self.refresh()

    def _find_display_segment(self, data, line, segment_uid):
        if not line:
            return None
        for segment in get_display_segments(data, line):
            if segment.get("uid") == segment_uid:
                return segment
        return None

    @staticmethod
    def _find_axis(data, axis_uid):
        for axis in data.get("axis_nodes", []):
            if axis.get("uid") == axis_uid:
                return axis
        return None

    @staticmethod
    def _find_line(data, line_uid):
        if not data:
            return None
        for line in data.get("lines", []):
            if line.get("uid") == line_uid:
                return line
        return None

    @staticmethod
    def _find_segment(line, segment_uid):
        if not line:
            return None
        for segment in line.get("segments", []):
            if segment.get("uid") == segment_uid:
                return segment
        return None

    @staticmethod
    def _find_point(segment, point_uid):
        if not segment:
            return None
        for point in segment.get("points", []):
            if point.get("uid") == point_uid:
                return point
        return None

    @staticmethod
    def _find_interaction(data, interaction_uid):
        if not data:
            return None
        for interaction in data.get("interactions", []):
            if interaction.get("uid") == interaction_uid:
                return interaction
        return None


class ToneOutlineController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.setup_ui()
        self._add_project_listener(self.on_project_data_changed)
        self._add_theme_listener(self.refresh)

    def setup_ui(self):
        self.view = ttk.Notebook(self.parent)
        self.view.pack(fill=tk.BOTH, expand=True)

        editor_frame = ttk.Frame(self.view)
        summary_frame = ttk.Frame(self.view)
        self.view.add(editor_frame, text="基调图")
        self.view.add(summary_frame, text="汇总")

        self.editor = ToneOutlineEditor(
            editor_frame,
            self.project_manager,
            self.command_executor,
            self.theme_manager,
        )
        self.editor.pack(fill=tk.BOTH, expand=True)

        self.summary = ToneOutlineSummaryPanel(summary_frame)
        self.summary.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def on_project_data_changed(self, event_type="all"):
        if event_type in ("all", "script", "tone_outline", "meta"):
            self.refresh()

    def refresh(self):
        tone_outline = self.project_manager.get_tone_outline()
        self.editor.refresh()
        self.summary.refresh(tone_outline)
