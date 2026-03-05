"""
放射/发散图视图 (Radial View)
根节点在中心，子节点向四周发散
"""
import tkinter as tk
from tkinter import messagebox
from writer_app.core.commands import AddNodeCommand, DeleteNodesCommand, EditNodeCommand, MoveNodeCommand
from .base_view import BaseOutlineView
from writer_app.ui.components.zoomable_canvas import ZoomableCanvas
import math


class RadialView(BaseOutlineView, ZoomableCanvas):
    """放射发散图视图 - 根节点在中心，子节点环绕分布"""

    def __init__(self, parent, project_manager, command_executor,
                 on_node_select=None, on_ai_suggest_branch=None,
                 on_generate_scene=None, on_set_tags=None, 
                 on_jump_to_scene=None, **kwargs):
        BaseOutlineView.__init__(self, parent, project_manager, command_executor,
                        on_node_select, on_ai_suggest_branch,
                        on_generate_scene, on_set_tags, 
                        on_jump_to_scene, **kwargs)
        ZoomableCanvas.__init__(self, parent, **kwargs)

        # 布局参数
        self.node_radius = 35  # 节点半径（圆形节点）
        self.center_radius = 45  # 中心节点半径
        self.level_spacing = 120  # 层级间距
        self.min_angle_gap = 0.15  # 最小角度间隔（弧度）

        # 拖拽相关
        self.drag_data = {"node_id": None, "start_x": 0, "start_y": 0,
                          "dragging": False, "target_id": None}
        self.drop_target_item = None
        self.drag_threshold = 5

        # 绑定事件
        self._bind_events()

    def _bind_events(self):
        """绑定鼠标和键盘事件"""
        self.bind("<Button-1>", self.on_click)
        self.bind("<Control-Button-1>", self.on_ctrl_click)
        self.bind("<Double-1>", self.on_double_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<MouseWheel>", self.on_mousewheel)
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Delete>", self.on_delete_key)
        self.bind("<Tab>", self.on_tab_key)
        self.bind("<Return>", self.on_enter_key)
        self.bind("<Escape>", self.on_escape_key)

    # ==================== 布局算法 ====================

    def refresh(self):
        """刷新画布"""
        super().refresh()

        if not self.root_node:
            return

        self.current_style = self.project_manager.get_outline_template_style()

        # 计算画布中心
        canvas_width = max(self.winfo_width(), 800)
        canvas_height = max(self.winfo_height(), 600)
        center_x = canvas_width / 2
        center_y = canvas_height / 2

        # 计算布局
        positions = {}
        self._calculate_layout(self.root_node, 0, center_x, center_y, 0, 2 * math.pi, positions)

        if not positions:
            fg = "#AAAAAA" if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark" else "#888888"
            self.create_text(center_x, center_y, text="无匹配的标签节点",
                           fill=fg, font=("Microsoft YaHei", 11))
            self.configure(scrollregion=(0, 0, canvas_width, canvas_height))
            return

        # 先绘制连线，再绘制节点
        self._draw_connections(self.root_node, positions)
        self._draw_nodes(self.root_node, positions, 0)

        # 更新滚动区域
        bbox = self.bbox("all")
        if bbox:
            padding = 100
            self.configure(scrollregion=(bbox[0] - padding, bbox[1] - padding,
                                         bbox[2] + padding, bbox[3] + padding))
            
        # Apply current zoom scale
        if hasattr(self, 'scale_factor') and self.scale_factor != 1.0:
            self.scale("all", 0, 0, self.scale_factor, self.scale_factor)
            self.configure(scrollregion=self.bbox("all"))

        # 恢复选中状态
        valid_ids = set()
        for node_id in self._selected_node_ids:
            if node_id in self.node_items:
                self._highlight_node(node_id, True)
                valid_ids.add(node_id)
        self._selected_node_ids = valid_ids

    def _calculate_layout(self, node, level, center_x, center_y, start_angle, end_angle, positions):
        """计算节点布局位置 - 放射布局"""
        if not self._subtree_matches_filter(node):
            return

        node_id = node.get("uid")
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]
        is_collapsed = node.get("_collapsed", False)

        if level == 0:
            # 根节点在中心
            positions[node_id] = (center_x, center_y, self.center_radius)
        else:
            # 其他节点基于角度和层级计算位置
            mid_angle = (start_angle + end_angle) / 2
            radius = level * self.level_spacing
            x = center_x + radius * math.cos(mid_angle)
            y = center_y + radius * math.sin(mid_angle)
            positions[node_id] = (x, y, self.node_radius)

        # 计算子节点
        if children and not is_collapsed:
            angle_range = end_angle - start_angle
            child_count = len(children)

            # 计算每个子节点的角度范围
            if level == 0:
                # 根节点的子节点均匀分布在整个圆周
                child_angle = 2 * math.pi / child_count
                for i, child in enumerate(children):
                    child_start = i * child_angle - math.pi / 2  # 从顶部开始
                    child_end = child_start + child_angle
                    self._calculate_layout(child, level + 1, center_x, center_y,
                                         child_start, child_end, positions)
            else:
                # 其他层级的子节点在父节点的角度范围内分布
                child_angle = angle_range / child_count
                for i, child in enumerate(children):
                    child_start = start_angle + i * child_angle
                    child_end = child_start + child_angle
                    self._calculate_layout(child, level + 1, center_x, center_y,
                                         child_start, child_end, positions)

    def _draw_connections(self, node, positions):
        """绘制连接线"""
        node_id = node.get("uid")
        if node_id not in positions:
            return

        if node.get("_collapsed", False):
            return

        x, y, r = positions[node_id]
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]

        line_color = "#666666" if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark" else "#B0B0B0"

        for child in children:
            child_id = child.get("uid")
            if child_id in positions:
                cx, cy, cr = positions[child_id]

                # 计算连线端点（从节点边缘开始）
                angle = math.atan2(cy - y, cx - x)
                start_x = x + r * math.cos(angle)
                start_y = y + r * math.sin(angle)
                end_x = cx - cr * math.cos(angle)
                end_y = cy - cr * math.sin(angle)

                # 绘制曲线连接
                mid_x = (start_x + end_x) / 2
                mid_y = (start_y + end_y) / 2
                # 添加一点弯曲
                ctrl_offset = 0.2
                ctrl_x = mid_x + (y - cy) * ctrl_offset
                ctrl_y = mid_y + (cx - x) * ctrl_offset

                self.create_line(start_x, start_y, ctrl_x, ctrl_y, end_x, end_y,
                               smooth=True, width=2, fill=line_color, tags="connection")
                self._draw_connections(child, positions)

    def _draw_nodes(self, node, positions, level):
        """绘制节点"""
        node_id = node.get("uid")
        if node_id not in positions:
            return

        x, y, r = positions[node_id]

        # 获取场景状态颜色
        status_color = None
        uid = node.get("uid", "")
        scenes = self.project_manager.get_scenes()
        for scene in scenes:
            if scene.get("outline_ref_id") == uid:
                status = scene.get("status")
                if status == "定稿":
                    status_color = "#28A745"
                elif status in ["初稿", "润色"]:
                    status_color = "#007BFF"
                break

        # 获取颜色
        if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark":
            color_idx = min(level, len(self.NODE_COLORS) - 1)
            bg_color, _ = self.NODE_COLORS[color_idx]
            text_color = "#FFFFFF"
            border_color = status_color if status_color else "#AAAAAA"
            border_width = 3 if status_color else 2
        else:
            color_idx = min(level, len(self.NODE_COLORS) - 1)
            bg_color, text_color = self.NODE_COLORS[color_idx]
            border_color = status_color if status_color else "#333333"
            border_width = 3 if status_color else 2

        # 绘制节点（圆形）
        rect = self.create_oval(x - r, y - r, x + r, y + r,
                               fill=bg_color, outline=border_color, width=border_width,
                               tags=("node", f"node_{node_id}", "node_rect"))

        # 绘制文本
        name = node.get("name", "未命名")
        max_chars = 6 if level > 0 else 8
        display_name = name if len(name) <= max_chars else name[:max_chars - 1] + "…"
        cnt = self.scene_counts.get(uid, 0)
        if cnt:
            display_name = f"{display_name}\n({cnt})"

        font_size = 9 if level > 0 else 11
        text = self.create_text(x, y, text=display_name, fill=text_color,
                               font=("Microsoft YaHei", font_size, "bold"),
                               tags=("node", f"node_{node_id}", "node_text"),
                               justify=tk.CENTER)

        # 绘制标签点
        node_tags = node.get("tags", [])
        if node_tags:
            tag_configs = {t["name"]: t["color"] for t in self.project_manager.get_tags_config()}
            dot_angle = -math.pi / 4  # 从右上角开始
            for i, tag_name in enumerate(node_tags[:4]):
                color = tag_configs.get(tag_name, "#999999")
                dot_x = x + (r + 5) * math.cos(dot_angle + i * 0.4)
                dot_y = y + (r + 5) * math.sin(dot_angle + i * 0.4)
                self.create_oval(dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4,
                               fill=color, outline="#666", tags=f"node_{node_id}")

        # 折叠指示器
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]
        if children:
            is_collapsed = node.get("_collapsed", False)
            indicator_text = f"+{len(children)}" if is_collapsed else f"-{len(children)}"
            indicator_color = "#FF6600" if is_collapsed else "#666666"
            if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark" and not is_collapsed:
                indicator_color = "#BBBBBB"

            # 放在节点下方
            btn_y = y + r + 12
            self.create_oval(x - 12, btn_y - 8, x + 12, btn_y + 8,
                           fill="white", outline=indicator_color, width=1,
                           tags=(f"node_{node_id}", "collapse_btn", f"collapse_{node_id}"))
            self.create_text(x, btn_y, text=indicator_text, fill=indicator_color,
                           font=("Arial", 7, "bold"),
                           tags=(f"node_{node_id}", "collapse_btn", f"collapse_{node_id}"))

        # 内容标记
        if node.get("content", "").strip():
            self.create_oval(x - r + 5, y - r + 5, x - r + 15, y - r + 15,
                           fill="#FFD700", outline="#FFA500",
                           tags=(f"node_{node_id}", "content_indicator"))

        # 存储节点信息
        self.node_items[node_id] = {
            "rect": rect, "text": text, "node": node,
            "level": level, "x": x - r, "y": y - r,
            "width": r * 2, "height": r * 2, "radius": r,
            "center_x": x, "center_y": y
        }

        # 递归绘制子节点
        if not node.get("_collapsed", False):
            for child in children:
                self._draw_nodes(child, positions, level + 1)

    # ==================== 事件处理方法 ====================

    def _get_node_at(self, x, y):
        """获取指定位置的节点ID（考虑圆形节点）"""
        for node_id, info in self.node_items.items():
            cx = info.get("center_x", info["x"] + info["width"] / 2)
            cy = info.get("center_y", info["y"] + info["height"] / 2)
            r = info.get("radius", info["width"] / 2)
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist <= r:
                return node_id
        return None

    def _get_collapse_btn_at(self, x, y):
        """获取指定位置的折叠按钮对应的节点ID"""
        items = self.find_overlapping(x - 2, y - 2, x + 2, y + 2)
        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith("collapse_"):
                    return tag[9:]
        return None

    def _highlight_node(self, node_id, highlight):
        """高亮或取消高亮节点"""
        if node_id not in self.node_items:
            return

        node_info = self.node_items[node_id]
        rect = node_info.get("rect")
        if rect:
            if highlight:
                self.itemconfig(rect, width=4, outline="#2196F3")
            else:
                level = node_info.get("level", 0)
                border_color = "#333333"
                if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark":
                    border_color = "#AAAAAA"
                self.itemconfig(rect, width=2, outline=border_color)

    def on_motion(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)

        if self.drag_data.get("dragging"):
            self._hide_tooltip()
            return

        node_id = self._get_node_at(x, y)
        if node_id != self.hover_node_id:
            self.hover_node_id = node_id
            self._hide_tooltip()
            if node_id:
                self._show_tooltip(node_id, event.x_root, event.y_root)
        elif node_id and self.tooltip_window:
            self._position_tooltip(event.x_root, event.y_root)

    def on_leave(self, event):
        self.hover_node_id = None
        self._hide_tooltip()

    def on_mousewheel(self, event):
        if event.state & 0x0004: # Control key
             self.on_zoom(event)
        else:
             self.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_right_click(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        node_id = self._get_node_at(x, y)
        if node_id and node_id not in self._selected_node_ids:
            self.select_node(node_id)
        self._update_status_menu()
        self._apply_ai_menu_state()
        self.context_menu.post(event.x_root, event.y_root)

    def on_delete_key(self, event):
        self.delete_selected_node()

    def on_tab_key(self, event):
        self.add_child_to_selected()
        return "break"

    def on_enter_key(self, event):
        if self.editing_node_id:
            self._close_edit_entry()
        else:
            self.add_sibling_to_selected()
        return "break"

    def on_escape_key(self, event):
        if self.editing_node_id:
            self._close_edit_entry(save=False)
        else:
            self.deselect_all()

    def on_click(self, event):
        self.focus_set()
        self._close_edit_entry()
        self._hide_tooltip()

        x = self.canvasx(event.x)
        y = self.canvasy(event.y)

        collapse_btn_node_id = self._get_collapse_btn_at(x, y)
        if collapse_btn_node_id:
            self._toggle_collapse(collapse_btn_node_id)
            return

        node_id = self._get_node_at(x, y)
        if node_id:
            self.select_node(node_id)
            self.drag_data["node_id"] = node_id
            self.drag_data["start_x"] = x
            self.drag_data["start_y"] = y
            self.drag_data["dragging"] = False
        else:
            self.deselect_all()

    def on_ctrl_click(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        node_id = self._get_node_at(x, y)
        if node_id:
            if node_id in self._selected_node_ids:
                self._selected_node_ids.remove(node_id)
                self._highlight_node(node_id, False)
            else:
                self.select_node(node_id, add=True)

    def on_double_click(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        node_id = self._get_node_at(x, y)
        if node_id:
            self.select_node(node_id)
            self._start_edit(node_id)

    def on_drag(self, event):
        self._hide_tooltip()
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)

        if self.drag_data["node_id"]:
            dx = abs(x - self.drag_data["start_x"])
            dy = abs(y - self.drag_data["start_y"])

            if self.drag_data["dragging"] or dx > self.drag_threshold or dy > self.drag_threshold:
                self.drag_data["dragging"] = True
                self.configure(cursor="fleur")

                target_id = self._get_node_at(x, y)

                if self.drop_target_item:
                    self.delete(self.drop_target_item)
                    self.drop_target_item = None

                self.drag_data["target_id"] = None

                if target_id and target_id != self.drag_data["node_id"]:
                    node_info = self.node_items.get(target_id)
                    if node_info:
                        cx = node_info.get("center_x", node_info["x"] + node_info["width"] / 2)
                        cy = node_info.get("center_y", node_info["y"] + node_info["height"] / 2)
                        r = node_info.get("radius", node_info["width"] / 2)

                        self.drop_target_item = self.create_oval(cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5,
                                                                outline="#2196F3", width=3, dash=(4, 2), tags="drop_target")
                        self.drag_data["target_id"] = target_id

    def on_release(self, event):
        if self.drag_data["dragging"]:
            target_id = self.drag_data.get("target_id")
            node_id = self.drag_data["node_id"]

            if target_id and node_id:
                command = MoveNodeCommand(self.project_manager, node_id, target_id)
                if self.command_executor(command):
                    self.refresh()

            if self.drop_target_item:
                self.delete(self.drop_target_item)
                self.drop_target_item = None

        self.drag_data["node_id"] = None
        self.drag_data["dragging"] = False
        self.drag_data["target_id"] = None
        self.configure(cursor="")

    # ==================== 节点操作方法 ====================

    def add_child_to_selected(self):
        if len(self._selected_node_ids) == 1:
            self._add_child_node(list(self._selected_node_ids)[0])
        elif not self._selected_node_ids and self.root_node:
            self._add_child_node(self.root_node.get("uid"))

    def add_sibling_to_selected(self):
        if len(self._selected_node_ids) != 1:
            return

        selected_node_id = list(self._selected_node_ids)[0]
        selected_node = self.node_items.get(selected_node_id, {}).get("node")
        if not selected_node:
            return

        parent = self._find_parent(self.root_node, selected_node)
        if parent:
            new_node = {"name": "新节点", "content": "", "children": []}
            children = parent.get("children", [])
            idx = children.index(selected_node) if selected_node in children else len(children)

            command = AddNodeCommand(self.project_manager, parent.get("uid"), new_node, "添加同级节点", insert_index=idx + 1)
            if self.command_executor(command):
                self.refresh()
                new_node_id = command.added_node_uid
                if new_node_id:
                    self.after(50, lambda nid=new_node_id: self._select_and_edit(nid))

    def _add_child_node(self, parent_node_id):
        if parent_node_id not in self.node_items:
            return

        parent_node = self.node_items[parent_node_id]["node"]
        new_node = {"name": "新节点", "content": "", "children": []}
        command = AddNodeCommand(self.project_manager, parent_node_id, new_node, "添加子节点")
        if self.command_executor(command):
            parent_node["_collapsed"] = False
            self.refresh()
            new_node_id = command.added_node_uid
            if new_node_id:
                self.after(50, lambda nid=new_node_id: self._select_and_edit(nid))

    def delete_selected_node(self):
        if not self._selected_node_ids:
            return

        count = len(self._selected_node_ids)
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {count} 个节点及其所有子节点吗?"):
            return

        command = DeleteNodesCommand(self.project_manager, self._selected_node_ids, "删除节点")
        if self.command_executor(command):
            self._selected_node_ids.clear()
            self.refresh()

    def _toggle_collapse(self, node_id):
        if node_id not in self.node_items:
            return
        node = self.node_items[node_id]["node"]
        node["_collapsed"] = not node.get("_collapsed", False)
        self.refresh()

    def _start_edit(self, node_id):
        """开始编辑节点 - 覆盖基类方法以适应圆形节点"""
        if node_id not in self.node_items:
            return

        self._close_edit_entry()

        node_info = self.node_items[node_id]
        node = node_info["node"]
        cx = node_info.get("center_x", node_info["x"] + node_info["width"] / 2)
        cy = node_info.get("center_y", node_info["y"] + node_info["height"] / 2)

        self.editing_node_id = node_id

        self.edit_entry = tk.Entry(
            self,
            font=("Microsoft YaHei", 10),
            justify=tk.CENTER,
            width=12
        )
        self.edit_entry.insert(0, node.get("name", ""))
        self.edit_entry.select_range(0, tk.END)

        self.create_window(cx, cy, window=self.edit_entry, tags="edit_entry")

        self.edit_entry.focus_set()
        self.edit_entry.bind("<Return>", lambda e: self._close_edit_entry(save=True))
        self.edit_entry.bind("<Escape>", lambda e: self._close_edit_entry(save=False))
        self.edit_entry.bind("<FocusOut>", lambda e: self._close_edit_entry(save=True))
