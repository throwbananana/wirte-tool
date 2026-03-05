"""
垂直树形图视图 (Vertical Tree View)
从上到下的树形结构
"""
import tkinter as tk
from tkinter import messagebox
from writer_app.core.commands import AddNodeCommand, DeleteNodesCommand, EditNodeCommand, MoveNodeCommand, ConvertIdeaToNodeCommand
from .base_view import BaseOutlineView
from writer_app.ui.dnd_manager import DragAndDropManager
import math
import json


class VerticalTreeView(BaseOutlineView):
    """垂直树形图视图 - 从上到下布局"""

    def __init__(self, parent, project_manager, command_executor,
                 on_node_select=None, on_ai_suggest_branch=None,
                 on_generate_scene=None, on_set_tags=None, 
                 on_jump_to_scene=None, **kwargs):
        super().__init__(parent, project_manager, command_executor,
                        on_node_select, on_ai_suggest_branch,
                        on_generate_scene, on_set_tags, 
                        on_jump_to_scene, **kwargs)

        # 布局参数
        self.node_width = 120
        self.node_height = 40
        self.h_spacing = 20   # 水平间距（同级节点之间）
        self.v_spacing = 60   # 垂直间距（父子节点之间）
        self.padding = 50

        # 拖拽相关
        self.drag_data = {"node_id": None, "start_x": 0, "start_y": 0,
                          "dragging": False, "target_id": None, "action": None}
        self.drop_target_item = None
        self.drag_threshold = 5
        
        # 外部拖拽管理器
        self.dnd_manager = DragAndDropManager()

        # 框选相关
        self.rubber_band_rect = None
        self.selection_start = (0, 0)

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

        # 计算布局
        positions = {}
        subtree_widths = {}
        self._calculate_subtree_widths(self.root_node, subtree_widths)
        self._calculate_layout(self.root_node, 0, self.padding, positions, subtree_widths)

        if not positions:
            width = max(self.winfo_width(), 300)
            height = max(self.winfo_height(), 200)
            self.configure(scrollregion=(0, 0, width, height))
            fg = "#AAAAAA" if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark" else "#888888"
            self.create_text(width / 2, height / 2, text="无匹配的标签节点",
                           fill=fg, font=("Microsoft YaHei", 11))
            return

        # 先绘制连线，再绘制节点
        self._draw_connections(self.root_node, positions)
        self._draw_nodes(self.root_node, positions, 0)

        # 更新滚动区域
        bbox = self.bbox("all")
        if bbox:
            padding = 50
            self.configure(scrollregion=(bbox[0] - padding, bbox[1] - padding,
                                         bbox[2] + padding, bbox[3] + padding))

        # 恢复选中状态
        valid_ids = set()
        for node_id in self._selected_node_ids:
            if node_id in self.node_items:
                self._highlight_node(node_id, True)
                valid_ids.add(node_id)
        self._selected_node_ids = valid_ids

    def _calculate_subtree_widths(self, node, widths):
        """计算每个节点子树的总宽度"""
        if not self._subtree_matches_filter(node):
            return 0

        node_id = node.get("uid")
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]
        is_collapsed = node.get("_collapsed", False)

        if not children or is_collapsed:
            widths[node_id] = self.node_width
            return self.node_width

        total_width = 0
        for child in children:
            total_width += self._calculate_subtree_widths(child, widths)
        total_width += self.h_spacing * (len(children) - 1)

        widths[node_id] = max(total_width, self.node_width)
        return widths[node_id]

    def _calculate_layout(self, node, level, x_offset, positions, subtree_widths):
        """计算节点布局位置 - 垂直树形布局"""
        if not self._subtree_matches_filter(node):
            return

        node_id = node.get("uid")
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]
        is_collapsed = node.get("_collapsed", False)

        y = self.padding + level * (self.node_height + self.v_spacing)
        subtree_width = subtree_widths.get(node_id, self.node_width)
        x = x_offset + (subtree_width - self.node_width) / 2

        positions[node_id] = (x, y)

        if children and not is_collapsed:
            child_x = x_offset
            for child in children:
                child_id = child.get("uid")
                child_width = subtree_widths.get(child_id, self.node_width)
                self._calculate_layout(child, level + 1, child_x, positions, subtree_widths)
                child_x += child_width + self.h_spacing

    def _draw_connections(self, node, positions):
        """绘制连接线 - 垂直方向"""
        node_id = node.get("uid")
        if node_id not in positions:
            return

        if node.get("_collapsed", False):
            return

        x, y = positions[node_id]
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]

        line_color = "#666666" if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark" else "#B0B0B0"

        for child in children:
            child_id = child.get("uid")
            if child_id in positions:
                cx, cy = positions[child_id]
                start_x = x + self.node_width / 2
                start_y = y + self.node_height
                end_x = cx + self.node_width / 2
                end_y = cy
                mid_y = (start_y + end_y) / 2

                # 绘制曲线连接
                self.create_line(start_x, start_y, start_x, mid_y, end_x, mid_y, end_x, end_y,
                               smooth=True, width=2, fill=line_color, tags="connection")
                self._draw_connections(child, positions)

    def _draw_nodes(self, node, positions, level):
        """绘制节点"""
        node_id = node.get("uid")
        if node_id not in positions:
            return

        x, y = positions[node_id]

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
            shadow_fill = "#222222"
        else:
            color_idx = min(level, len(self.NODE_COLORS) - 1)
            bg_color, text_color = self.NODE_COLORS[color_idx]
            border_color = status_color if status_color else "#333333"
            border_width = 3 if status_color else 2
            shadow_fill = "#DDDDDD"

        # 绘制阴影和节点
        shadow_offset = 3
        self._create_rounded_rect(x + shadow_offset, y + shadow_offset,
                                 x + self.node_width + shadow_offset, y + self.node_height + shadow_offset,
                                 8, fill=shadow_fill, outline="", tags=f"shadow_{node_id}")
        rect = self._create_rounded_rect(x, y, x + self.node_width, y + self.node_height,
                                        8, fill=bg_color, outline=border_color, width=border_width,
                                        tags=("node", f"node_{node_id}", "node_rect"))

        # 绘制文本
        name = node.get("name", "未命名")
        display_name = name if len(name) <= 8 else name[:7] + "..."
        cnt = self.scene_counts.get(uid, 0)
        if cnt:
            display_name = f"{display_name}({cnt})"

        text = self.create_text(x + self.node_width / 2, y + self.node_height / 2,
                               text=display_name, fill=text_color,
                               font=("Microsoft YaHei", 9, "bold"),
                               tags=("node", f"node_{node_id}", "node_text"))

        # 绘制标签点
        node_tags = node.get("tags", [])
        if node_tags:
            tag_configs = {t["name"]: t["color"] for t in self.project_manager.get_tags_config()}
            dot_x = x + 6
            dot_y = y - 4
            for tag_name in node_tags[:3]:  # 最多显示3个
                color = tag_configs.get(tag_name, "#999999")
                self.create_oval(dot_x, dot_y, dot_x + 6, dot_y + 6,
                               fill=color, outline="#666", tags=f"node_{node_id}")
                dot_x += 8

        # 折叠指示器
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]
        if children:
            is_collapsed = node.get("_collapsed", False)
            indicator_text = f"+{len(children)}" if is_collapsed else f"-{len(children)}"
            indicator_color = "#FF6600" if is_collapsed else "#666666"
            if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark" and not is_collapsed:
                indicator_color = "#BBBBBB"

            btn_x = x + self.node_width / 2
            btn_y = y + self.node_height + 8
            self.create_oval(btn_x - 10, btn_y - 8, btn_x + 10, btn_y + 8,
                           fill="white", outline=indicator_color, width=1,
                           tags=(f"node_{node_id}", "collapse_btn", f"collapse_{node_id}"))
            self.create_text(btn_x, btn_y, text=indicator_text, fill=indicator_color,
                           font=("Arial", 7, "bold"),
                           tags=(f"node_{node_id}", "collapse_btn", f"collapse_{node_id}"))

        # 内容标记
        if node.get("content", "").strip():
            self.create_oval(x + 4, y + 4, x + 12, y + 12,
                           fill="#FFD700", outline="#FFA500",
                           tags=(f"node_{node_id}", "content_indicator"))

        # 存储节点信息
        self.node_items[node_id] = {
            "rect": rect, "text": text, "node": node,
            "level": level, "x": x, "y": y,
            "width": self.node_width, "height": self.node_height
        }

        # 递归绘制子节点
        if not node.get("_collapsed", False):
            for child in children:
                self._draw_nodes(child, positions, level + 1)

    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
                  x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
                  x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    # ==================== 事件处理方法 ====================

    def _get_node_at(self, x, y):
        """获取指定位置的节点ID"""
        items = self.find_overlapping(x - 2, y - 2, x + 2, y + 2)
        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith("node_") and not tag.startswith("node_rect") and not tag.startswith("node_text"):
                    node_id = tag[5:]
                    if node_id in self.node_items:
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

    def on_motion(self, event):
        """鼠标悬停显示提示，以及处理外部拖拽高亮"""
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)

        # 1. 内部拖拽
        if self.drag_data.get("dragging"):
            self._hide_tooltip()
            return

        # 2. 外部拖拽 (Idea Drop)
        external_data = self.dnd_manager.get_data()
        if external_data and external_data.get("type") == "idea":
            self.configure(cursor="hand2") # Visual feedback
            
            target_id = self._get_node_at(x, y)
            
            # Clear previous highlighting if target changed
            if self.drop_target_item:
                self.delete(self.drop_target_item)
                self.drop_target_item = None
                
            if target_id:
                node_info = self.node_items.get(target_id)
                if node_info:
                    nx, ny = node_info["x"], node_info["y"]
                    nw, nh = self.node_width, self.node_height
                    self.drop_target_item = self._create_rounded_rect(nx - 3, ny - 3, nx + nw + 3, ny + nh + 3, 8,
                                                                     outline="#4CAF50", width=3, dash=(4, 2), tags="drop_target")
            return

        # 3. 普通悬停
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
            self.selection_start = (x, y)
            if self.rubber_band_rect:
                self.delete(self.rubber_band_rect)
            self.rubber_band_rect = self.create_rectangle(x, y, x, y, outline="#2196F3", width=1, dash=(2, 2), tags="rubber_band")

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
                self.drag_data["action"] = None

                if target_id and target_id != self.drag_data["node_id"]:
                    node_info = self.node_items.get(target_id)
                    if node_info:
                        nx, ny = node_info["x"], node_info["y"]
                        nw, nh = self.node_width, self.node_height

                        self.drop_target_item = self._create_rounded_rect(nx - 3, ny - 3, nx + nw + 3, ny + nh + 3, 8,
                                                                         outline="#2196F3", width=3, dash=(4, 2), tags="drop_target")
                        self.drag_data["target_id"] = target_id
                        self.drag_data["action"] = "reparent"

        elif self.rubber_band_rect:
            start_x, start_y = self.selection_start
            self.coords(self.rubber_band_rect, start_x, start_y, x, y)
            x1, y1 = min(start_x, x), min(start_y, y)
            x2, y2 = max(start_x, x), max(start_y, y)
            overlapping = self.find_overlapping(x1, y1, x2, y2)
            current_ids = set()
            for item in overlapping:
                tags = self.gettags(item)
                for tag in tags:
                    if tag.startswith("node_") and not tag.startswith("node_rect") and not tag.startswith("node_text"):
                        current_ids.add(tag[5:])
            self.deselect_all()
            for nid in current_ids:
                self.select_node(nid, add=True)

    def on_release(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        
        # 1. External Drop (Idea)
        external_data = self.dnd_manager.get_data()
        if external_data and external_data.get("type") == "idea":
            target_id = self._get_node_at(x, y)
            if target_id:
                # Convert Idea to Child Node
                cmd = ConvertIdeaToNodeCommand(
                    self.project_manager, 
                    external_data["uid"], 
                    target_id, 
                    f"灵感转节点: {external_data['content'][:10]}..."
                )
                if self.command_executor(cmd):
                    self.refresh()
            
            # Clean up
            if self.drop_target_item:
                self.delete(self.drop_target_item)
                self.drop_target_item = None
            self.dnd_manager.stop_drag() # Explicitly stop to clear data
            self.configure(cursor="")
            return

        # 2. Internal Drag
        if self.rubber_band_rect:
            self.delete(self.rubber_band_rect)
            self.rubber_band_rect = None

        if self.drag_data["dragging"]:
            target_id = self.drag_data.get("target_id")
            action = self.drag_data.get("action")
            node_id = self.drag_data["node_id"]

            if target_id and node_id and action == "reparent":
                command = MoveNodeCommand(self.project_manager, node_id, target_id)
                if self.command_executor(command):
                    self.refresh()

            if self.drop_target_item:
                self.delete(self.drop_target_item)
                self.drop_target_item = None

        self.drag_data["node_id"] = None
        self.drag_data["dragging"] = False
        self.drag_data["target_id"] = None
        self.drag_data["action"] = None
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
