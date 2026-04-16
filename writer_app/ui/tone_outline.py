import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from writer_app.controllers.base_controller import BaseController
from writer_app.core.commands import UpdateToneOutlineCommand
from writer_app.core.tone_outline import (
    DEFAULT_PLOT_LINE_UID,
    build_axis_nodes_from_scenes,
    build_line_summary,
    build_timeline_summary,
    clone_tone_outline,
    ensure_tone_outline_defaults,
    get_axis_index_map,
    get_display_segments,
    get_next_tone_line_color,
    get_open_segment,
    is_character_line_potential,
    line_covers_axis,
)


def _range_text(axis_map, segment):
    start_uid = segment.get("start_axis_uid")
    end_uid = segment.get("end_axis_uid")
    start_text = axis_map.get(start_uid, {}).get("title", "未设置")
    if not end_uid:
        return f"{start_text} -> 进行中"
    end_text = axis_map.get(end_uid, {}).get("title", "未设置")
    return f"{start_text} -> {end_text}"


class ToneOutlineCanvas(tk.Canvas):
    def __init__(
        self,
        parent,
        on_axis_selected,
        on_line_selected,
        on_point_selected,
        theme_manager=None,
        **kwargs,
    ):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.on_axis_selected = on_axis_selected
        self.on_line_selected = on_line_selected
        self.on_point_selected = on_point_selected
        self.theme_manager = theme_manager
        self.data = None
        self.selected_axis_uid = ""
        self.selected_line_uid = ""
        self.selected_point_uid = ""
        self._axis_positions = {}
        self._apply_theme()
        self.bind("<Button-1>", self._handle_click)
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

    def set_state(self, data, selected_axis_uid="", selected_line_uid="", selected_point_uid=""):
        self.data = clone_tone_outline(data or {})
        self.selected_axis_uid = selected_axis_uid or ""
        self.selected_line_uid = selected_line_uid or ""
        self.selected_point_uid = selected_point_uid or ""
        self.refresh()

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
                text="人物线会先进入潜在栏，在任意节点引入；收束后回到潜在栏，可再次跨节点引入。",
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
            display_segments = get_display_segments(data, line)
            if not display_segments:
                continue
            sorted_nodes = sorted(
                line.get("nodes", []),
                key=lambda item: axis_index_map.get(item.get("axis_uid"), 0),
            )
            for segment in display_segments:
                start_uid = segment.get("start_axis_uid")
                end_uid = segment.get("end_axis_uid") or last_axis_uid
                if start_uid not in self._axis_positions or end_uid not in self._axis_positions:
                    continue
                points = [
                    {
                        "x": self._axis_positions[start_uid],
                        "y": baseline_y,
                        "curvature": 0.35,
                    }
                ]
                for node in sorted_nodes:
                    if not line_covers_axis(data, line, node.get("axis_uid")):
                        continue
                    axis_uid = node.get("axis_uid")
                    if axis_uid not in axis_index_map:
                        continue
                    current_index = axis_index_map[axis_uid]
                    start_index = axis_index_map.get(start_uid, 0)
                    end_index = axis_index_map.get(end_uid, start_index)
                    if start_index <= current_index <= end_index:
                        points.append(
                            {
                                "x": self._axis_positions[axis_uid],
                                "y": baseline_y - float(node.get("amplitude", 0)) * amplitude_scale,
                                "curvature": float(node.get("curvature", 0.45)),
                            }
                        )
                if end_uid != start_uid:
                    points.append(
                        {
                            "x": self._axis_positions[end_uid],
                            "y": baseline_y,
                            "curvature": 0.35,
                        }
                    )
                points.sort(key=lambda item: item["x"])
                sampled = self._sample_curve(points)
                if len(sampled) >= 4:
                    width_px = 4 if line.get("uid") == self.selected_line_uid else (3 if line.get("line_type") == "plot" else 2)
                    self.create_line(
                        *[value for point in sampled for value in point],
                        fill=line.get("color") or "#2563EB",
                        width=width_px,
                    )

                label_offset += 1
                status_suffix = " (进行中)" if line.get("line_type") == "character" and not segment.get("end_axis_uid") else ""
                self.create_text(
                    self._axis_positions[start_uid] + 16,
                    baseline_y + 16 + ((label_offset % 4) * 14),
                    text=f"{line.get('name', '未命名线')}{status_suffix}",
                    anchor="w",
                    fill=line.get("color") or "#2563EB",
                    font=("Microsoft YaHei", 8),
                    tags=("line_label", f"line:{line['uid']}"),
                )

                for node in sorted_nodes:
                    axis_uid = node.get("axis_uid")
                    if axis_uid not in self._axis_positions or not line_covers_axis(data, line, axis_uid):
                        continue
                    current_index = axis_index_map[axis_uid]
                    start_index = axis_index_map.get(start_uid, 0)
                    end_index = axis_index_map.get(end_uid, start_index)
                    if not start_index <= current_index <= end_index:
                        continue
                    x = self._axis_positions[axis_uid]
                    y = baseline_y - float(node.get("amplitude", 0)) * amplitude_scale
                    is_selected = (
                        line.get("uid") == self.selected_line_uid
                        and node.get("uid") == self.selected_point_uid
                    )
                    radius = 7 if is_selected else 5
                    self.create_oval(
                        x - radius,
                        y - radius,
                        x + radius,
                        y + radius,
                        fill=line.get("color") or "#2563EB",
                        outline=colors["selected"] if is_selected else "#FFFFFF",
                        width=2,
                        tags=("point", f"point:{line['uid']}:{node['uid']}", f"line:{line['uid']}"),
                    )
                    label = node.get("label") or f"{int(round(float(node.get('amplitude', 0)))):+d}"
                    self.create_text(
                        x,
                        y - 16,
                        text=label,
                        fill=line.get("color") or "#2563EB",
                        font=("Arial", 8),
                        tags=(f"point:{line['uid']}:{node['uid']}", f"line:{line['uid']}"),
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

    def _handle_click(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        item = self.find_closest(x, y)
        if not item:
            return
        tags = self.gettags(item[0])
        for tag in tags:
            if tag.startswith("point:"):
                _, line_uid, point_uid = tag.split(":", 2)
                self.on_point_selected(line_uid, point_uid)
                return
        for tag in tags:
            if tag.startswith("line:"):
                self.on_line_selected(tag.split(":", 1)[1])
                return
        for tag in tags:
            if tag.startswith("axis:"):
                self.on_axis_selected(tag.split(":", 1)[1])
                return


class ToneOutlineSummaryPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        ttk.Label(
            self,
            text="汇总按“线”和“节点”双向展开。潜在线会单独标出，活动线则显示各段过程及对应节点强度。",
        ).pack(anchor="w", padx=8, pady=(8, 4))

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        line_frame = ttk.LabelFrame(paned, text="按线汇总")
        axis_frame = ttk.LabelFrame(paned, text="按节点 / 平级对应汇总")
        paned.add(line_frame, weight=1)
        paned.add(axis_frame, weight=1)

        self.line_tree = ttk.Treeview(
            line_frame,
            columns=("state", "strength", "curve", "note"),
            show="tree headings",
            height=16,
        )
        self.line_tree.heading("#0", text="线 / 过程 / 节点")
        self.line_tree.heading("state", text="状态")
        self.line_tree.heading("strength", text="强度")
        self.line_tree.heading("curve", text="曲率")
        self.line_tree.heading("note", text="说明")
        self.line_tree.column("#0", width=220, anchor="w")
        self.line_tree.column("state", width=90, anchor="center")
        self.line_tree.column("strength", width=70, anchor="center")
        self.line_tree.column("curve", width=70, anchor="center")
        self.line_tree.column("note", width=230, anchor="w")
        self.line_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.axis_tree = ttk.Treeview(
            axis_frame,
            columns=("state", "strength", "curve", "note"),
            show="tree headings",
            height=16,
        )
        self.axis_tree.heading("#0", text="节点 / 对应线")
        self.axis_tree.heading("state", text="状态")
        self.axis_tree.heading("strength", text="强度")
        self.axis_tree.heading("curve", text="曲率")
        self.axis_tree.heading("note", text="说明")
        self.axis_tree.column("#0", width=220, anchor="w")
        self.axis_tree.column("state", width=90, anchor="center")
        self.axis_tree.column("strength", width=70, anchor="center")
        self.axis_tree.column("curve", width=70, anchor="center")
        self.axis_tree.column("note", width=230, anchor="w")
        self.axis_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def refresh(self, tone_outline_data):
        for tree in (self.line_tree, self.axis_tree):
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
                segment_parent = self.line_tree.insert(
                    line_parent,
                    "end",
                    text=segment["range_text"],
                    values=(segment["state_text"], "", "", ""),
                    open=True,
                )
                for item in segment["items"]:
                    note = item["description"] or item["label"]
                    self.line_tree.insert(
                        segment_parent,
                        "end",
                        text=item["axis_title"],
                        values=(
                            "节点",
                            item["strength"],
                            item["curvature"],
                            note,
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
                note = match["description"] or match["label"]
                self.axis_tree.insert(
                    parent,
                    "end",
                    text=match["line_name"],
                    values=(
                        match["state_text"],
                        match["strength"],
                        match["curvature"],
                        note,
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
        self.selected_point_uid = ""
        self.axis_order = []
        self.active_line_order = []
        self.potential_line_order = []
        self.point_order = []

        self.axis_title_var = tk.StringVar()
        self.line_name_var = tk.StringVar()
        self.line_type_var = tk.StringVar()
        self.line_character_var = tk.StringVar()
        self.line_status_var = tk.StringVar()
        self.point_axis_var = tk.StringVar()
        self.point_label_var = tk.StringVar()
        self.point_amplitude_var = tk.DoubleVar(value=0.0)
        self.point_curvature_var = tk.DoubleVar(value=0.45)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(
            toolbar,
            text="人物线先进入潜在栏，选中主轴节点后可引入；收束后保留到潜在栏，可再次跨节点引入。",
        ).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="从场景生成主轴", command=self.import_axis_from_scenes).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.RIGHT)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        canvas_frame = ttk.LabelFrame(paned, text="基调图")
        config_frame = ttk.Frame(paned)
        paned.add(canvas_frame, weight=3)
        paned.add(config_frame, weight=2)

        canvas_container = ttk.Frame(canvas_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        self.canvas = ToneOutlineCanvas(
            canvas_container,
            on_axis_selected=self.select_axis,
            on_line_selected=self.select_line,
            on_point_selected=self.select_point,
            theme_manager=self.theme_manager,
        )
        h_scroll = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=h_scroll.set)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        h_scroll.pack(fill=tk.X)

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

        ttk.Label(line_frame, text="活动线").pack(anchor="w", padx=6, pady=(6, 0))
        self.active_line_list = tk.Listbox(line_frame, height=4, exportselection=False)
        self.active_line_list.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.active_line_list.bind("<<ListboxSelect>>", self._on_active_line_select)

        ttk.Label(line_frame, text="潜在栏").pack(anchor="w", padx=6, pady=(4, 0))
        self.potential_line_list = tk.Listbox(line_frame, height=4, exportselection=False)
        self.potential_line_list.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.potential_line_list.bind("<<ListboxSelect>>", self._on_potential_line_select)

        line_btns = ttk.Frame(line_frame)
        line_btns.pack(fill=tk.X, padx=6, pady=(2, 0))
        ttk.Button(line_btns, text="新增人物线", command=self.add_character_line).pack(side=tk.LEFT)
        ttk.Button(line_btns, text="在当前节点引入", command=self.introduce_line).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(line_btns, text="在当前节点收束", command=self.converge_line).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(line_btns, text="删除线", command=self.delete_line).pack(side=tk.LEFT, padx=(12, 0))

        ttk.Label(line_frame, text="线名").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Entry(line_frame, textvariable=self.line_name_var).pack(fill=tk.X, padx=6)
        ttk.Label(line_frame, text="类型 / 状态").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(line_frame, textvariable=self.line_type_var).pack(anchor="w", padx=6)
        ttk.Label(line_frame, textvariable=self.line_status_var, foreground="#666666").pack(anchor="w", padx=6, pady=(0, 2))
        ttk.Label(line_frame, text="人物名").pack(anchor="w", padx=6, pady=(4, 0))
        ttk.Entry(line_frame, textvariable=self.line_character_var).pack(fill=tk.X, padx=6)
        ttk.Button(line_frame, text="保存线信息", command=self.save_line).pack(anchor="e", padx=6, pady=(6, 4))

        ttk.Label(line_frame, text="过程段历史").pack(anchor="w", padx=6, pady=(2, 0))
        self.segment_history = tk.Listbox(line_frame, height=4)
        self.segment_history.pack(fill=tk.X, padx=6, pady=(0, 6))

        point_frame = ttk.LabelFrame(config_frame, text="波动点")
        point_frame.pack(fill=tk.BOTH, expand=True)
        self.point_list = tk.Listbox(point_frame, height=6, exportselection=False)
        self.point_list.pack(fill=tk.X, padx=6, pady=(6, 4))
        self.point_list.bind("<<ListboxSelect>>", self._on_point_list_select)

        point_btns = ttk.Frame(point_frame)
        point_btns.pack(fill=tk.X, padx=6)
        ttk.Button(point_btns, text="在当前节点新增", command=self.add_point).pack(side=tk.LEFT)
        ttk.Button(point_btns, text="删除波动点", command=self.delete_point).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(point_frame, text="当前节点").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(point_frame, textvariable=self.point_axis_var).pack(anchor="w", padx=6)
        ttk.Label(point_frame, text="波动强度").pack(anchor="w", padx=6, pady=(6, 0))
        tk.Scale(
            point_frame,
            from_=100,
            to=-100,
            resolution=1,
            orient=tk.VERTICAL,
            variable=self.point_amplitude_var,
            length=120,
        ).pack(anchor="w", padx=6)
        ttk.Label(point_frame, text="曲率").pack(anchor="w", padx=6, pady=(6, 0))
        tk.Scale(
            point_frame,
            from_=0.10,
            to=1.50,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            variable=self.point_curvature_var,
            length=180,
        ).pack(anchor="w", padx=6)
        ttk.Label(point_frame, text="标签").pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Entry(point_frame, textvariable=self.point_label_var).pack(fill=tk.X, padx=6)
        ttk.Label(point_frame, text="情节/人物说明").pack(anchor="w", padx=6, pady=(6, 0))
        self.point_desc_text = tk.Text(point_frame, height=4, wrap="word")
        self.point_desc_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        ttk.Button(point_frame, text="保存波动点", command=self.save_point).pack(anchor="e", padx=6, pady=(0, 6))

    def refresh(self):
        data = self.project_manager.get_tone_outline()
        self.axis_order = [axis["uid"] for axis in data.get("axis_nodes", [])]
        if self.selected_axis_uid not in self.axis_order:
            self.selected_axis_uid = self.axis_order[0] if self.axis_order else ""

        active_lines = []
        potential_lines = []
        for line in data.get("lines", []):
            if line.get("line_type") == "plot" or not is_character_line_potential(line):
                active_lines.append(line)
            else:
                potential_lines.append(line)
        self.active_line_order = [line["uid"] for line in active_lines]
        self.potential_line_order = [line["uid"] for line in potential_lines]

        all_line_ids = set(self.active_line_order + self.potential_line_order)
        if self.selected_line_uid not in all_line_ids:
            self.selected_line_uid = DEFAULT_PLOT_LINE_UID if DEFAULT_PLOT_LINE_UID in all_line_ids else (self.active_line_order[0] if self.active_line_order else (self.potential_line_order[0] if self.potential_line_order else ""))

        self._refresh_axis_list(data)
        self._refresh_line_lists(active_lines, potential_lines)
        self._refresh_segment_history(data)
        self._refresh_point_list(data)
        self._load_axis_form(data)
        self._load_line_form(data)
        self._load_point_form(data)
        self.canvas.set_state(data, self.selected_axis_uid, self.selected_line_uid, self.selected_point_uid)

    def select_axis(self, axis_uid):
        self.selected_axis_uid = axis_uid or ""
        self.selected_point_uid = ""
        self.refresh()

    def select_line(self, line_uid):
        self.selected_line_uid = line_uid or ""
        self.selected_point_uid = ""
        self.refresh()

    def select_point(self, line_uid, point_uid):
        self.selected_line_uid = line_uid or ""
        self.selected_point_uid = point_uid or ""
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        point = self._find_point(line, self.selected_point_uid) if line else None
        if point:
            self.selected_axis_uid = point.get("axis_uid") or self.selected_axis_uid
        self.refresh()

    def _refresh_axis_list(self, data):
        self.axis_list.delete(0, tk.END)
        for index, axis in enumerate(data.get("axis_nodes", [])):
            self.axis_list.insert(tk.END, f"{index + 1}. {axis.get('title', '未命名节点')}")
        if self.selected_axis_uid in self.axis_order:
            idx = self.axis_order.index(self.selected_axis_uid)
            self.axis_list.selection_clear(0, tk.END)
            self.axis_list.selection_set(idx)

    def _refresh_line_lists(self, active_lines, potential_lines):
        self.active_line_list.delete(0, tk.END)
        self.potential_line_list.delete(0, tk.END)

        for line in active_lines:
            status = "主轴" if line.get("line_type") == "plot" else "活动"
            self.active_line_list.insert(tk.END, f"[{status}] {line.get('name', '未命名线')}")
        for line in potential_lines:
            history_count = len(line.get("segments", []))
            label = f"{line.get('name', '未命名线')} / 历史段 {history_count}"
            self.potential_line_list.insert(tk.END, label)

        if self.selected_line_uid in self.active_line_order:
            idx = self.active_line_order.index(self.selected_line_uid)
            self.active_line_list.selection_clear(0, tk.END)
            self.active_line_list.selection_set(idx)
            self.potential_line_list.selection_clear(0, tk.END)
        elif self.selected_line_uid in self.potential_line_order:
            idx = self.potential_line_order.index(self.selected_line_uid)
            self.potential_line_list.selection_clear(0, tk.END)
            self.potential_line_list.selection_set(idx)
            self.active_line_list.selection_clear(0, tk.END)

    def _refresh_segment_history(self, data):
        self.segment_history.delete(0, tk.END)
        line = self._find_line(data, self.selected_line_uid)
        if not line:
            return
        axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
        display_segments = get_display_segments(data, line)
        if not display_segments and line.get("line_type") == "character":
            self.segment_history.insert(tk.END, "当前未引入，保存在潜在栏")
            return
        for index, segment in enumerate(display_segments):
            suffix = " / 进行中" if line.get("line_type") == "character" and not segment.get("end_axis_uid") else ""
            self.segment_history.insert(tk.END, f"第{index + 1}段: {_range_text(axis_map, segment)}{suffix}")

    def _refresh_point_list(self, data):
        self.point_list.delete(0, tk.END)
        self.point_order = []
        line = self._find_line(data, self.selected_line_uid)
        axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
        axis_index_map = get_axis_index_map(data)
        if not line:
            return
        visible_nodes = [
            node for node in line.get("nodes", [])
            if line.get("line_type") == "plot" or line_covers_axis(data, line, node.get("axis_uid"))
        ]
        visible_nodes.sort(key=lambda item: axis_index_map.get(item.get("axis_uid"), 0))
        for node in visible_nodes:
            axis_title = axis_map.get(node.get("axis_uid"), {}).get("title", "未命名节点")
            amplitude = int(round(float(node.get("amplitude", 0))))
            label = node.get("label") or ""
            extra = f" / {label}" if label else ""
            self.point_list.insert(tk.END, f"{axis_title} | {amplitude:+d}{extra}")
            self.point_order.append(node.get("uid"))
        if self.selected_point_uid in self.point_order:
            idx = self.point_order.index(self.selected_point_uid)
            self.point_list.selection_clear(0, tk.END)
            self.point_list.selection_set(idx)
        elif self.selected_point_uid and self.selected_point_uid not in self.point_order:
            self.selected_point_uid = ""

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
        line_type = "情节线" if line.get("line_type") == "plot" else "人物线"
        self.line_type_var.set(line_type)
        self.line_character_var.set(line.get("character_name", ""))
        if line.get("line_type") == "plot":
            self.line_status_var.set("固定主线，始终围绕平铺主轴展开。")
        else:
            open_segment = get_open_segment(line)
            if open_segment:
                axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
                self.line_status_var.set(f"当前活动中：{_range_text(axis_map, open_segment)}")
            else:
                self.line_status_var.set("当前已收束，保存在潜在栏，可在任意节点再次引入。")

    def _load_point_form(self, data):
        line = self._find_line(data, self.selected_line_uid)
        point = self._find_point(line, self.selected_point_uid) if line else None
        axis = self._find_axis(data, self.selected_axis_uid)
        self.point_axis_var.set(axis.get("title", "未选择节点") if axis else "未选择节点")
        self.point_desc_text.delete("1.0", tk.END)
        if not point:
            self.point_label_var.set("")
            self.point_amplitude_var.set(0.0)
            self.point_curvature_var.set(0.45)
            return
        self.point_label_var.set(point.get("label", ""))
        self.point_amplitude_var.set(float(point.get("amplitude", 0)))
        self.point_curvature_var.set(float(point.get("curvature", 0.45)))
        self.point_desc_text.insert("1.0", point.get("description", ""))

    def _on_axis_list_select(self, _event=None):
        selection = self.axis_list.curselection()
        if not selection:
            return
        self.selected_axis_uid = self.axis_order[selection[0]]
        self.selected_point_uid = ""
        self.refresh()

    def _on_active_line_select(self, _event=None):
        selection = self.active_line_list.curselection()
        if not selection:
            return
        self.selected_line_uid = self.active_line_order[selection[0]]
        self.selected_point_uid = ""
        self.refresh()

    def _on_potential_line_select(self, _event=None):
        selection = self.potential_line_list.curselection()
        if not selection:
            return
        self.selected_line_uid = self.potential_line_order[selection[0]]
        self.selected_point_uid = ""
        self.refresh()

    def _on_point_list_select(self, _event=None):
        selection = self.point_list.curselection()
        if not selection:
            return
        self.selected_point_uid = self.point_order[selection[0]]
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        point = self._find_point(line, self.selected_point_uid) if line else None
        if point:
            self.selected_axis_uid = point.get("axis_uid") or self.selected_axis_uid
        self.refresh()

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
                line["nodes"] = [node for node in line.get("nodes", []) if node.get("axis_uid") != deleted_uid]
                if line.get("line_type") != "character":
                    continue
                new_segments = []
                for segment in line.get("segments", []):
                    start_uid = segment.get("start_axis_uid")
                    end_uid = segment.get("end_axis_uid") or ""
                    if start_uid == deleted_uid:
                        start_uid = next_uid or prev_uid
                    if end_uid == deleted_uid:
                        end_uid = prev_uid
                    if not start_uid:
                        continue
                    segment["start_axis_uid"] = start_uid
                    segment["end_axis_uid"] = end_uid if end_uid != start_uid else end_uid
                    new_segments.append(segment)
                line["segments"] = new_segments

        self.selected_axis_uid = ""
        self.selected_point_uid = ""
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
                    "segments": [],
                    "nodes": [],
                }
            )

        self.selected_line_uid = new_uid
        self.selected_point_uid = ""
        self._apply_update(mutate, "新增人物基调线")

    def introduce_line(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        if not line or line.get("line_type") == "plot":
            messagebox.showinfo("提示", "请选择一条潜在人物线。", parent=self.winfo_toplevel())
            return
        if not self.selected_axis_uid:
            messagebox.showinfo("提示", "请先选择一个主轴节点。", parent=self.winfo_toplevel())
            return
        if get_open_segment(line):
            messagebox.showinfo("提示", "该人物线当前已经处于活动中，请先收束。", parent=self.winfo_toplevel())
            return
        new_segment_uid = self.project_manager._gen_uid()

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            if target_line:
                target_line.setdefault("segments", []).append(
                    {
                        "uid": new_segment_uid,
                        "start_axis_uid": self.selected_axis_uid,
                        "end_axis_uid": "",
                    }
                )

        self._apply_update(mutate, "引入人物线")

    def converge_line(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        if not line or line.get("line_type") == "plot":
            messagebox.showinfo("提示", "请选择一条活动中的人物线。", parent=self.winfo_toplevel())
            return
        if not self.selected_axis_uid:
            messagebox.showinfo("提示", "请先选择收束所在的主轴节点。", parent=self.winfo_toplevel())
            return
        open_segment = get_open_segment(line)
        if not open_segment:
            messagebox.showinfo("提示", "该人物线当前已经在潜在栏中。", parent=self.winfo_toplevel())
            return
        axis_index_map = get_axis_index_map(self.project_manager.get_tone_outline())
        start_index = axis_index_map.get(open_segment.get("start_axis_uid"), 0)
        end_index = axis_index_map.get(self.selected_axis_uid, 0)
        if end_index < start_index:
            messagebox.showinfo("提示", "收束节点不能早于引入节点。", parent=self.winfo_toplevel())
            return

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            target_open_segment = get_open_segment(target_line) if target_line else None
            if target_open_segment:
                target_open_segment["end_axis_uid"] = self.selected_axis_uid

        self._apply_update(mutate, "收束人物线")

    def delete_line(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        if not line:
            return
        if line.get("line_type") == "plot":
            messagebox.showinfo("提示", "情节线是固定主线，不支持删除。", parent=self.winfo_toplevel())
            return

        def mutate(data):
            data["lines"] = [item for item in data.get("lines", []) if item.get("uid") != self.selected_line_uid]

        self.selected_point_uid = ""
        self.selected_line_uid = DEFAULT_PLOT_LINE_UID
        self._apply_update(mutate, "删除人物线")

    def save_line(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        if not line:
            return
        name = self.line_name_var.get().strip() or line.get("name") or "未命名线"
        character_name = self.line_character_var.get().strip()

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            if target_line:
                target_line["name"] = name
                if target_line.get("line_type") == "character":
                    target_line["character_name"] = character_name

        self._apply_update(mutate, "编辑线信息")

    def add_point(self):
        if not self.selected_line_uid or not self.selected_axis_uid:
            messagebox.showinfo("提示", "请先选择一条线和一个主轴节点。", parent=self.winfo_toplevel())
            return
        data = self.project_manager.get_tone_outline()
        line = self._find_line(data, self.selected_line_uid)
        if not line:
            return
        if line.get("line_type") == "character" and not line_covers_axis(data, line, self.selected_axis_uid):
            messagebox.showinfo(
                "提示",
                "当前节点不在这条人物线的任何过程段内。请先引入这条线，或选择已有过程中的节点。",
                parent=self.winfo_toplevel(),
            )
            return

        def mutate(new_data):
            target_line = self._find_line(new_data, self.selected_line_uid)
            if not target_line:
                return
            existing = next((node for node in target_line.get("nodes", []) if node.get("axis_uid") == self.selected_axis_uid), None)
            if existing:
                self.selected_point_uid = existing.get("uid")
                return
            point_uid = self.project_manager._gen_uid()
            target_line.setdefault("nodes", []).append(
                {
                    "uid": point_uid,
                    "axis_uid": self.selected_axis_uid,
                    "amplitude": 0,
                    "curvature": 0.45,
                    "label": "",
                    "description": "",
                }
            )
            self.selected_point_uid = point_uid

        self._apply_update(mutate, "新增波动点")

    def delete_point(self):
        if not self.selected_point_uid:
            return
        point_uid = self.selected_point_uid

        def mutate(data):
            line = self._find_line(data, self.selected_line_uid)
            if line:
                line["nodes"] = [node for node in line.get("nodes", []) if node.get("uid") != point_uid]

        self.selected_point_uid = ""
        self._apply_update(mutate, "删除波动点")

    def save_point(self):
        line = self._find_line(self.project_manager.get_tone_outline(), self.selected_line_uid)
        point = self._find_point(line, self.selected_point_uid) if line else None
        if not point:
            return
        label = self.point_label_var.get().strip()
        description = self.point_desc_text.get("1.0", tk.END).strip()
        amplitude = float(self.point_amplitude_var.get())
        curvature = float(self.point_curvature_var.get())

        def mutate(data):
            target_line = self._find_line(data, self.selected_line_uid)
            target_point = self._find_point(target_line, self.selected_point_uid) if target_line else None
            if target_point:
                target_point["label"] = label
                target_point["description"] = description
                target_point["amplitude"] = amplitude
                target_point["curvature"] = curvature

        self._apply_update(mutate, "编辑波动点")

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
                line["nodes"] = []
                if line.get("line_type") == "character":
                    line["segments"] = []
            if axis_nodes:
                self.selected_axis_uid = axis_nodes[0]["uid"]

        self.selected_point_uid = ""
        self._apply_update(mutate, "从场景生成主轴")

    def _apply_update(self, mutator, description):
        old_data = clone_tone_outline(self.project_manager.get_tone_outline())
        new_data = clone_tone_outline(old_data)
        mutator(new_data)
        ensure_tone_outline_defaults(new_data, uid_generator=self.project_manager._gen_uid)
        if old_data == new_data:
            self.refresh()
            return
        command = UpdateToneOutlineCommand(self.project_manager, old_data, new_data, description)
        if self.command_executor(command):
            self.refresh()

    @staticmethod
    def _find_axis(data, axis_uid):
        for axis in data.get("axis_nodes", []):
            if axis.get("uid") == axis_uid:
                return axis
        return None

    @staticmethod
    def _find_line(data, line_uid):
        for line in data.get("lines", []):
            if line.get("uid") == line_uid:
                return line
        return None

    @staticmethod
    def _find_point(line, point_uid):
        if not line:
            return None
        for node in line.get("nodes", []):
            if node.get("uid") == point_uid:
                return node
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
