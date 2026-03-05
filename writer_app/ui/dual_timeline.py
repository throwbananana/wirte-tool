"""
双时间轴视图 - 用于悬疑推理小说的真相线/谎言线可视化

功能：
- Layer 1: 物理真相 (The Truth) - 实际发生的事件
- Layer 2: 谎言线 (The Lie) - 角色宣称的事件
- Layer 3: 叙事呈现 (Narrative Scenes) - 场景链接
- 支持缩放、平移、事件编辑
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from writer_app.core.analysis import AnalysisUtils
from writer_app.ui.components.empty_state_panel import EmptyStatePanel, EmptyStateConfig


class DualTimelineView(tk.Canvas):
    """双时间轴 Canvas 视图"""

    def __init__(self, parent, project_manager, theme_manager, controller=None):
        super().__init__(parent, bg="#222", highlightthickness=0)
        self.project_manager = project_manager
        self.theme_manager = theme_manager
        self.controller = controller

        # Register theme listener
        self.theme_manager.add_listener(self._on_theme_change)

        # Canvas item -> event data mapping
        self.truth_items = {}
        self.lie_items = {}
        self.hover_tooltip = None

        # Zoom & Pan State
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self._drag_data = {"x": 0, "y": 0}

        # Empty state panel
        self._empty_state_visible = False
        config = EmptyStateConfig.DUAL_TIMELINE
        self._empty_state = EmptyStatePanel(
            self,
            self.theme_manager,
            icon=config["icon"],
            title=config["title"],
            description=config["description"],
            action_text=config["action_text"],
            action_callback=self._on_empty_state_action
        )
        self._empty_state_window = None

        # Bind events
        self._bind_events()

    def _bind_events(self):
        """绑定所有交互事件"""
        # Context menu & editing
        self.bind("<Button-3>", self._on_right_click)
        self.bind("<Double-1>", self._on_double_click)

        # Hover tooltip
        self.bind("<Motion>", self._on_hover)
        self.bind("<Leave>", self._hide_tooltip)

        # Pan: Middle click or Ctrl+Left click
        self.bind("<ButtonPress-2>", self._on_pan_start)
        self.bind("<B2-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-2>", self._on_pan_end)
        self.bind("<Control-ButtonPress-1>", self._on_pan_start)
        self.bind("<Control-B1-Motion>", self._on_pan_drag)
        self.bind("<Control-ButtonRelease-1>", self._on_pan_end)

        # Zoom: Mouse wheel
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", self._on_wheel)  # Linux scroll up
        self.bind("<Button-5>", self._on_wheel)  # Linux scroll down

    def _on_theme_change(self):
        """响应主题变化"""
        self.refresh()

    def _on_empty_state_action(self):
        """Handle empty state action button click."""
        if self.controller:
            self.controller.add_truth_event()

    def _show_empty_state(self, show: bool):
        """Show or hide the empty state panel."""
        if show and not self._empty_state_visible:
            # Create canvas window for empty state
            w = self.winfo_width()
            h = self.winfo_height()
            if w < 100:
                w = 800
            if h < 100:
                h = 600
            self._empty_state_window = self.create_window(
                w // 2, h // 2,
                window=self._empty_state,
                width=w - 40,
                height=h - 40,
                anchor=tk.CENTER,
                tags="empty_state"
            )
            self._empty_state_visible = True
        elif not show and self._empty_state_visible:
            if self._empty_state_window:
                self.delete("empty_state")
                self._empty_state_window = None
            self._empty_state_visible = False

    def _on_pan_start(self, event):
        """开始平移"""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.config(cursor="fleur")

    def _on_pan_drag(self, event):
        """平移拖拽"""
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.offset_x += dx
        self.offset_y += dy
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.refresh()

    def _on_pan_end(self, event):
        """结束平移"""
        self.config(cursor="")

    def _on_wheel(self, event):
        """鼠标滚轮缩放（以鼠标位置为中心）"""
        # Determine zoom direction
        if event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            scale = 0.9
        else:
            scale = 1.1

        # Calculate new zoom level
        new_zoom = self.zoom * scale
        new_zoom = max(0.1, min(10.0, new_zoom))

        # Zoom centered on mouse position
        mouse_x = event.x
        mouse_y = event.y

        # Adjust offset to keep mouse position stationary
        zoom_ratio = new_zoom / self.zoom
        self.offset_x = mouse_x - (mouse_x - self.offset_x) * zoom_ratio
        self.offset_y = mouse_y - (mouse_y - self.offset_y) * zoom_ratio

        self.zoom = new_zoom
        self.refresh()

    def refresh(self, event=None):
        """刷新绘制整个时间轴"""
        self.delete("all")
        self.truth_items.clear()
        self.lie_items.clear()
        self._hide_tooltip()
        self.config(cursor="")

        # Get theme colors
        bg = self.theme_manager.get_color("canvas_bg")
        fg = self.theme_manager.get_color("fg_primary")
        self.configure(bg=bg)

        w = self.winfo_width()
        h = self.winfo_height()
        if w < 100:
            w = 800
        if h < 100:
            h = 600

        # Get data first to check for empty state
        timelines = self.project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])
        lie_events = timelines.get("lie_events", [])

        # Show empty state if no events
        if not truth_events and not lie_events:
            self._show_empty_state(True)
            return
        self._show_empty_state(False)

        # Calculate timeline dimensions
        base_padding = 50
        scaled_timeline_width = max(600, (w - 2 * base_padding)) * self.zoom

        # Calculate positions with pan offset
        start_x = base_padding + self.offset_x
        end_x = start_x + scaled_timeline_width

        # Lane Y positions
        lie_lane_y = (h / 4) + self.offset_y
        truth_lane_y = (h * 0.75) + self.offset_y
        scene_lane_y = (h * 0.9) + self.offset_y

        # Draw lanes
        self._draw_lanes(start_x, end_x, lie_lane_y, truth_lane_y, scene_lane_y, fg)

        # Get scenes for linking
        all_scenes = self.project_manager.get_scenes()

        # Draw events
        self._draw_truth_events(truth_events, start_x, end_x, truth_lane_y, scene_lane_y, all_scenes, fg)
        self._draw_lie_events(lie_events, truth_events, start_x, end_x, lie_lane_y, fg)

        # Update scroll region
        self.configure(scrollregion=self.bbox("all") or (0, 0, w, h))

    def _draw_lanes(self, start_x, end_x, lie_lane_y, truth_lane_y, scene_lane_y, fg):
        """绘制时间轴泳道"""
        font_size = max(8, int(12 * self.zoom))

        # Lie Lane (Layer 2)
        self.create_line(start_x, lie_lane_y, end_x, lie_lane_y, fill=fg, arrow=tk.LAST)
        self.create_text(start_x + 10, lie_lane_y - 20,
                         text="Layer 2: 谎言线 (The Lie)", anchor="w",
                         fill=fg, font=("Arial", font_size, "bold"))

        # Truth Lane (Layer 1)
        self.create_line(start_x, truth_lane_y, end_x, truth_lane_y, fill=fg, arrow=tk.LAST)
        self.create_text(start_x + 10, truth_lane_y - 20,
                         text="Layer 1: 物理真相 (The Truth)", anchor="w",
                         fill=fg, font=("Arial", font_size, "bold"))

        # Scene Lane (Layer 3)
        self.create_line(start_x, scene_lane_y, end_x, scene_lane_y, fill=fg, dash=(2, 4))
        self.create_text(start_x + 10, scene_lane_y - 15,
                         text="Layer 3: 叙事呈现 (Narrative Scenes)", anchor="w",
                         fill="#888", font=("Arial", max(6, int(10 * self.zoom)), "italic"))

    def _draw_truth_events(self, events, start_x, end_x, lane_y, scene_lane_y, all_scenes, fg):
        """绘制真相事件"""
        if not events:
            return

        # Sort by timestamp
        sorted_events = sorted(events, key=AnalysisUtils.get_sort_key_for_event)

        # Calculate time range
        valid_times = [AnalysisUtils.get_sort_key_for_event(e) for e in sorted_events]
        valid_times = [t for t in valid_times if t != datetime.max]

        if not valid_times:
            min_time = datetime.now()
            max_time = datetime.now()
        else:
            min_time = min(valid_times)
            max_time = max(valid_times)

        time_range = (max_time - min_time).total_seconds() or 1
        timeline_width = end_x - start_x

        for i, event in enumerate(sorted_events):
            uid = event.get("uid")
            if not uid:
                continue

            ts = AnalysisUtils.get_sort_key_for_event(event)
            if ts == datetime.max:
                norm_x = 0.5 + (i / len(sorted_events)) * 0.4
            else:
                norm_x = (ts - min_time).total_seconds() / time_range if time_range > 0 else 0.5
                norm_x = max(0.05, min(0.95, norm_x))

            x = start_x + norm_x * timeline_width
            y = lane_y

            # Draw event circle
            r = 8 * self.zoom
            item_id = self.create_oval(
                x - r, y - r, x + r, y + r,
                fill="#D9534F", outline="#FFF", width=2,
                tags=("truth_event", f"truth_{uid}")
            )
            self.truth_items[item_id] = event

            # Draw labels
            font_small = max(6, int(8 * self.zoom))
            font_medium = max(7, int(9 * self.zoom))
            self.create_text(x, y + 20 * self.zoom,
                             text=event.get("timestamp", "未知时间"),
                             fill="#AAA", font=("Arial", font_small))
            self.create_text(x, y + 35 * self.zoom,
                             text=event.get("name", ""),
                             fill=fg, font=("Arial", font_medium, "bold"))

            # Link to scene (using scene UID)
            linked_scene_uid = event.get("linked_scene_uid")
            if linked_scene_uid:
                scene_idx = self._find_scene_index_by_uid(all_scenes, linked_scene_uid)
                if scene_idx >= 0:
                    self._draw_scene_link(x, y + r, scene_lane_y, scene_idx)

    def _draw_lie_events(self, events, truth_events, start_x, end_x, lane_y, fg):
        """绘制谎言事件"""
        if not events:
            return

        sorted_events = sorted(events, key=AnalysisUtils.get_sort_key_for_event)

        valid_times = [AnalysisUtils.get_sort_key_for_event(e) for e in sorted_events]
        valid_times = [t for t in valid_times if t != datetime.max]

        if not valid_times:
            min_time = datetime.now()
            max_time = datetime.now()
        else:
            min_time = min(valid_times)
            max_time = max(valid_times)

        time_range = (max_time - min_time).total_seconds() or 1
        timeline_width = end_x - start_x

        for i, event in enumerate(sorted_events):
            uid = event.get("uid")
            if not uid:
                continue

            ts = AnalysisUtils.get_sort_key_for_event(event)
            if ts == datetime.max:
                norm_x = 0.5 + (i / len(sorted_events)) * 0.4
            else:
                norm_x = (ts - min_time).total_seconds() / time_range if time_range > 0 else 0.5
                norm_x = max(0.05, min(0.95, norm_x))

            x = start_x + norm_x * timeline_width
            y = lane_y

            # Determine colors (yellow if bug found)
            bug_found = bool(event.get("bug", "").strip())
            fill_color = "#FFD700" if bug_found else "#4A90D9"
            outline_color = "#FF4500" if bug_found else "#FFF"

            # Draw event circle
            r = 8 * self.zoom
            item_id = self.create_oval(
                x - r, y - r, x + r, y + r,
                fill=fill_color, outline=outline_color, width=2,
                tags=("lie_event", f"lie_{uid}")
            )
            self.lie_items[item_id] = event

            # Draw labels
            font_small = max(6, int(8 * self.zoom))
            font_medium = max(7, int(9 * self.zoom))
            self.create_text(x, y - 20 * self.zoom,
                             text=event.get("timestamp", "未知时间"),
                             fill="#AAA", font=("Arial", font_small))
            self.create_text(x, y - 35 * self.zoom,
                             text=event.get("name", ""),
                             fill=fg, font=("Arial", font_medium, "bold"))

            # Draw conflict link to truth event
            linked_truth_uid = event.get("linked_truth_event_uid")
            if linked_truth_uid:
                self._draw_conflict_link(x, y + r, linked_truth_uid, truth_events)

    def _draw_scene_link(self, x, y_start, scene_lane_y, scene_idx):
        """绘制到场景的链接线"""
        self.create_line(x, y_start, x, scene_lane_y - 10,
                         dash=(2, 2), fill="#555")

        box_w = 40 * self.zoom
        box_h = 10 * self.zoom
        self.create_rectangle(
            x - box_w, scene_lane_y - box_h,
            x + box_w, scene_lane_y + box_h,
            fill="#333", outline="#666"
        )
        self.create_text(x, scene_lane_y,
                         text=f"Scene {scene_idx + 1}",
                         fill="#FFF", font=("Arial", max(6, int(8 * self.zoom))))

    def _draw_conflict_link(self, lie_x, lie_y, truth_uid, truth_events):
        """绘制谎言事件到真相事件的冲突链接"""
        # Find truth event canvas item
        for item_id, event in self.truth_items.items():
            if event.get("uid") == truth_uid:
                coords = self.coords(item_id)
                if coords:
                    r = 8 * self.zoom
                    tx = coords[0] + r
                    ty = coords[1] + r
                    self.create_line(
                        lie_x, lie_y, tx, ty - r,
                        dash=(4, 4), fill="#d9534f", arrow=tk.LAST,
                        tags="conflict_link"
                    )
                break

    def _find_scene_index_by_uid(self, scenes, uid):
        """通过 UID 查找场景索引"""
        for i, scene in enumerate(scenes):
            if scene.get("uid") == uid:
                return i
        return -1

    def _on_right_click(self, event):
        """右键菜单"""
        if not self.controller:
            return

        menu = tk.Menu(self, tearoff=0)
        x_canvas = self.canvasx(event.x)
        y_canvas = self.canvasy(event.y)

        w_height = self.winfo_height()
        mid_point = (w_height / 4 + w_height * 0.75) / 2 + self.offset_y

        # Check if clicked on an item
        clicked_item = self.find_closest(x_canvas, y_canvas, halo=5)

        if clicked_item:
            item_id = clicked_item[0]
            if item_id in self.lie_items:
                event_data = self.lie_items[item_id]
                menu.add_command(label="添加谎言事件", command=self.controller.add_lie_event)
                menu.add_separator()
                menu.add_command(label="编辑谎言事件",
                                 command=lambda e=event_data: self.controller.edit_lie_event(e))
                menu.add_command(label="删除谎言事件",
                                 command=lambda e=event_data: self.controller.delete_lie_event(e))
                menu.add_separator()
                uid = event_data.get("uid", "")
                menu.add_command(label=f"复制UID: {uid[:8]}...",
                                 command=lambda u=uid: self._copy_uid(u))
            elif item_id in self.truth_items:
                event_data = self.truth_items[item_id]
                menu.add_command(label="添加真相事件", command=self.controller.add_truth_event)
                menu.add_separator()
                menu.add_command(label="编辑真相事件",
                                 command=lambda e=event_data: self.controller.edit_truth_event(e))
                menu.add_command(label="删除真相事件",
                                 command=lambda e=event_data: self.controller.delete_truth_event(e))
                menu.add_separator()
                uid = event_data.get("uid", "")
                menu.add_command(label=f"复制UID: {uid[:8]}...",
                                 command=lambda u=uid: self._copy_uid(u))
            else:
                # Clicked on empty area
                if y_canvas < mid_point:
                    menu.add_command(label="添加谎言事件", command=self.controller.add_lie_event)
                else:
                    menu.add_command(label="添加真相事件", command=self.controller.add_truth_event)
        else:
            if y_canvas < mid_point:
                menu.add_command(label="添加谎言事件", command=self.controller.add_lie_event)
            else:
                menu.add_command(label="添加真相事件", command=self.controller.add_truth_event)

        menu.post(event.x_root, event.y_root)

    def _on_double_click(self, event):
        """双击编辑事件"""
        if not self.controller:
            return

        x_canvas = self.canvasx(event.x)
        y_canvas = self.canvasy(event.y)
        items = self.find_closest(x_canvas, y_canvas)

        if items:
            item_id = items[0]
            if item_id in self.truth_items:
                self.controller.edit_truth_event(self.truth_items[item_id])
            elif item_id in self.lie_items:
                self.controller.edit_lie_event(self.lie_items[item_id])

    def _on_hover(self, event):
        """悬停显示详情"""
        x_canvas = self.canvasx(event.x)
        y_canvas = self.canvasy(event.y)
        items = self.find_closest(x_canvas, y_canvas, halo=5)

        if not items:
            self._hide_tooltip()
            return

        item_id = items[0]
        tooltip_text = ""

        if item_id in self.truth_items:
            evt = self.truth_items[item_id]
            tooltip_text = (
                f"【Layer 1: {evt.get('name', '未命名')}】\n"
                f"时间: {evt.get('timestamp', '-')}\n"
                f"地点: {evt.get('location', '-')}\n"
                f"动机: {evt.get('motive', '-')}\n"
                f"行动: {evt.get('action', '-')}\n"
                f"意外: {evt.get('chaos', '-')}"
            )
        elif item_id in self.lie_items:
            evt = self.lie_items[item_id]
            tooltip_text = (
                f"【Layer 2: {evt.get('name', '未命名')}】\n"
                f"宣称时间: {evt.get('timestamp', '-')}\n"
                f"借口: {evt.get('motive', '-')}\n"
                f"隐瞒: {evt.get('gap', '-')}\n"
                f"破绽: {evt.get('bug', '-')}"
            )

        if tooltip_text:
            self._show_tooltip(event.x_root, event.y_root, tooltip_text)
        else:
            self._hide_tooltip()

    def _show_tooltip(self, x, y, text):
        """显示工具提示"""
        self._hide_tooltip()
        self.hover_tooltip = tk.Toplevel(self)
        self.hover_tooltip.wm_overrideredirect(True)
        self.hover_tooltip.wm_attributes("-topmost", True)
        self.hover_tooltip.geometry(f"+{x + 15}+{y + 15}")

        bg = "#333333" if self.theme_manager.current_theme == "Dark" else "#FFFFDD"
        fg = "#FFFFFF" if self.theme_manager.current_theme == "Dark" else "black"

        tk.Label(
            self.hover_tooltip, text=text, bg=bg, fg=fg,
            justify=tk.LEFT, relief="solid", bd=1, wraplength=300
        ).pack()

    def _hide_tooltip(self, event=None):
        """隐藏工具提示"""
        if self.hover_tooltip:
            self.hover_tooltip.destroy()
            self.hover_tooltip = None

    def _copy_uid(self, uid):
        """复制 UID 到剪贴板"""
        if not uid:
            return
        self.clipboard_clear()
        self.clipboard_append(uid)
        messagebox.showinfo("复制成功", f"事件UID已复制:\n{uid}")

    def reset_view(self):
        """重置视图到默认状态"""
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.refresh()
