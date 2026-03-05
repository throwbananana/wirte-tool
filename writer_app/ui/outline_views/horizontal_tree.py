"""
水平树形图视图 (Horizontal Tree View)
从左到右的树形结构，这是原始 MindMapCanvas 的重构版本
"""
import tkinter as tk
from tkinter import messagebox
import os
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from writer_app.core.commands import AddNodeCommand, DeleteNodesCommand, EditNodeCommand, MoveNodeCommand
from .base_view import BaseOutlineView
from writer_app.ui.components.zoomable_canvas import ZoomableCanvas
import math


class HorizontalTreeView(BaseOutlineView, ZoomableCanvas):
    """
    水平树形思维导图视图 - 从左到右布局
    Inherits from ZoomableCanvas for Pan/Zoom support.
    """

    def __init__(self, parent, project_manager, command_executor,
                 on_node_select=None, on_ai_suggest_branch=None,
                 on_generate_scene=None, on_set_tags=None, 
                 on_jump_to_scene=None, **kwargs):
        
        BaseOutlineView.__init__(self, parent, project_manager, command_executor,
                        on_node_select, on_ai_suggest_branch,
                        on_generate_scene, on_set_tags, on_jump_to_scene, **kwargs)
        ZoomableCanvas.__init__(self, parent, **kwargs)

        # 布局参数
        self.node_width = 140
        self.node_height = 36
        self.h_spacing = 50  # 水平间距
        self.v_spacing = 15  # 垂直间距
        self.padding = 40

        # Background Image Cache
        self.bg_photo = None
        self.last_bg_path = None
        self.last_opacity = 1.0

        # 拖拽相关
        self.drag_data = {"node_id": None, "start_x": 0, "start_y": 0,
                          "dragging": False, "target_id": None, "action": None}
        self.drop_target_item = None
        self.drag_threshold = 5

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
        # MouseWheel is handled by ZoomableCanvas for Ctrl+Wheel.
        # We keep standard wheel for vertical scroll.
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
        # BaseOutlineView.refresh clears "all"
        super().refresh()

        # Draw Background Image if set
        if HAS_PIL and self.current_theme_manager and hasattr(self.current_theme_manager, "background_image_path"):
            bg_path = self.current_theme_manager.background_image_path
            opacity = getattr(self.current_theme_manager, "background_opacity", 1.0)
            
            if bg_path and os.path.exists(bg_path):
                # Reload only if changed or not loaded
                if bg_path != self.last_bg_path or opacity != self.last_opacity or self.bg_photo is None:
                    try:
                        image = Image.open(bg_path).convert("RGBA")
                        
                        if opacity < 1.0:
                            # Apply alpha channel
                            alpha = image.split()[3]
                            alpha = alpha.point(lambda p: int(p * opacity))
                            image.putalpha(alpha)
                            
                        self.bg_photo = ImageTk.PhotoImage(image)
                        self.last_bg_path = bg_path
                        self.last_opacity = opacity
                    except Exception as e:
                        print(f"Failed to load background image: {e}")
                        self.bg_photo = None
                
                if self.bg_photo:
                    # Draw at 0,0
                    self.create_image(0, 0, image=self.bg_photo, anchor="nw", tags="background")

        if not self.root_node:
            return

        # 获取当前样式
        self.current_style = self.project_manager.get_outline_template_style()

        # 计算布局
        positions = {}
        self._calculate_layout(self.root_node, 0, 0, positions)

        if not positions:
            # 没有匹配过滤条件的节点时显示提示
            width = max(self.winfo_width(), 300)
            height = max(self.winfo_height(), 200)
            self.configure(scrollregion=(0, 0, width, height))
            fg = "#AAAAAA" if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark" else "#888888"
            self.create_text(width / 2, height / 2, text="无匹配的标签节点",
                           fill=fg, font=("Microsoft YaHei", 11))
            return

        # 调整位置
        if positions:
            min_y = min(p[1] for p in positions.values())
            offset_y = self.padding - min_y
            for node_id in positions:
                positions[node_id] = (positions[node_id][0], positions[node_id][1] + offset_y)

        # 先绘制连线，再绘制节点
        self._draw_connections(self.root_node, positions)
        self._draw_nodes(self.root_node, positions, 0)

        # 更新滚动区域
        bbox = self.bbox("all")
        if bbox:
            padding = 50
            self.configure(scrollregion=(bbox[0] - padding, bbox[1] - padding,
                                         bbox[2] + padding, bbox[3] + padding))
            
        # If zoomed, we need to apply scale?
        # ZoomableCanvas.on_zoom scales items relative to current scale.
        # But refresh deletes everything. We need to re-apply current scale_factor.
        if self.scale_factor != 1.0:
            # Re-scaling from 1.0 to self.scale_factor
            # Since we just drew at 1.0 (default coords), we just scale 'all' by self.scale_factor
            self.scale("all", 0, 0, self.scale_factor, self.scale_factor)
            # Adjust scrollregion again
            self.configure(scrollregion=self.bbox("all"))

        # 恢复选中状态
        valid_ids = set()
        for node_id in self._selected_node_ids:
            if node_id in self.node_items:
                self._highlight_node(node_id, True)
                valid_ids.add(node_id)
        self._selected_node_ids = valid_ids

    def _calculate_layout(self, node, level, y_offset, positions):
        """计算节点布局位置 - 水平树形布局"""
        if not self._subtree_matches_filter(node):
            return y_offset

        node_id = node.get("uid")
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]
        is_collapsed = node.get("_collapsed", False)

        x = self.padding + level * (self.node_width + self.h_spacing)

        if not children or is_collapsed:
            positions[node_id] = (x, y_offset)
            return y_offset + self.node_height + self.v_spacing
        else:
            child_start_y = y_offset
            for child in children:
                y_offset = self._calculate_layout(child, level + 1, y_offset, positions)

            child_end_y = y_offset - self.v_spacing
            node_y = (child_start_y + child_end_y - self.node_height) / 2
            positions[node_id] = (x, node_y)
            return y_offset

    def _draw_connections(self, node, positions):
        """绘制连接线 - 贝塞尔曲线"""
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
                start_x = x + self.node_width
                start_y = y + self.node_height / 2
                end_x = cx
                end_y = cy + self.node_height / 2
                ctrl_x = (start_x + end_x) / 2

                self.create_line(start_x, start_y, ctrl_x, start_y, ctrl_x, end_y, end_x, end_y,
                               smooth=True, width=2, fill=line_color, tags="connection")
                self._draw_connections(child, positions)

    def _draw_nodes(self, node, positions, level):
        """绘制节点"""
        node_id = node.get("uid")
        if node_id not in positions:
            return

        x, y = positions[node_id]

        # 获取场景状态信息
        status, progress = self._get_node_status_info(node_id)
        
        status_color = None
        if status:
            if progress >= 1.0: # 定稿
                status_color = "#28A745"
            elif progress >= 0.5: # 润色等
                status_color = "#007BFF"
            else: # 初稿等
                status_color = "#17A2B8"

        # 获取颜色
        if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark":
            color_idx = min(level, len(self.NODE_COLORS) - 1)
            orig_bg, _ = self.NODE_COLORS[color_idx]
            bg_color = orig_bg
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

        # 绘制背景
        rect = self._draw_node_bg(x, y, bg_color, border_color, border_width, shadow_fill, node_id, level)

        # 绘制进度条 (如果有状态)
        if progress is not None and progress > 0:
            bar_h = 4
            self.create_rectangle(x + 5, y + self.node_height - bar_h - 5, 
                                 x + self.node_width - 5, y + self.node_height - 5,
                                 fill="#EEE", outline="", tags=f"node_{node_id}")
            self.create_rectangle(x + 5, y + self.node_height - bar_h - 5, 
                                 x + 5 + (self.node_width - 10) * progress, y + self.node_height - 5,
                                 fill="#4CAF50", outline="", tags=f"node_{node_id}")

        # 绘制文本
        name = node.get("name", "未命名")
        display_name = name if len(name) <= 10 else name[:9] + "..."
        cnt = self.scene_counts.get(node_id, 0)
        if cnt:
            display_name = f"{display_name} ({cnt})"

        text = self.create_text(x + self.node_width / 2, y + self.node_height / 2,
                               text=display_name, fill=text_color,
                               font=("Microsoft YaHei", 10, "bold"),
                               tags=("node", f"node_{node_id}", "node_text"))

        # 绘制标签点
        node_tags = node.get("tags", [])
        if node_tags:
            tag_configs = {t["name"]: t["color"] for t in self.project_manager.get_tags_config()}
            dot_x = x + 10
            dot_y = y - 5
            for tag_name in node_tags:
                color = tag_configs.get(tag_name, "#999999")
                self.create_oval(dot_x, dot_y, dot_x + 8, dot_y + 8,
                               fill=color, outline="#666", tags=f"node_{node_id}")
                dot_x += 10

        # 折叠指示器
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]
        if children:
            is_collapsed = node.get("_collapsed", False)
            indicator_text = f"+{len(children)}" if is_collapsed else f"-{len(children)}"
            indicator_color = "#FF6600" if is_collapsed else "#666666"
            if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark" and not is_collapsed:
                indicator_color = "#BBBBBB"

            self.create_oval(x + self.node_width - 22, y + self.node_height - 18,
                           x + self.node_width - 4, y + self.node_height - 2,
                           fill="white", outline=indicator_color, width=1,
                           tags=(f"node_{node_id}", "collapse_btn", f"collapse_{node_id}"))
            self.create_text(x + self.node_width - 13, y + self.node_height - 10,
                           text=indicator_text, fill=indicator_color,
                           font=("Arial", 7, "bold"),
                           tags=(f"node_{node_id}", "collapse_btn", f"collapse_{node_id}"))

        # 内容标记
        if node.get("content", "").strip():
            self.create_oval(x + 4, y + 4, x + 14, y + 14,
                           fill="#FFD700", outline="#FFA500",
                           tags=(f"node_{node_id}", "content_indicator"))

        # 添加按钮
        btn_x = x + self.node_width + 5
        btn_y = y + self.node_height / 2
        self.create_oval(btn_x - 10, btn_y - 10, btn_x + 10, btn_y + 10,
                        fill="#E8F5E9", outline="#4CAF50", width=2,
                        tags=(f"add_btn_{node_id}", "add_btn"))
        self.create_text(btn_x, btn_y, text="+ ", fill="#4CAF50",
                        font=("Arial", 14, "bold"),
                        tags=(f"add_btn_{node_id}", "add_btn"))

        # 存储节点信息
        # IMPORTANT: We store x,y from draw time. 
        # But if Zoomed, coords are scaled. 
        # x, y passed here are "logical" coordinates (calculated by layout).
        # Interaction events will receive "screen" coordinates and convert to canvas via canvasx/y.
        # So storing logical x,y is fine for layout recalculations, but hit testing might need care?
        # Canvas hit testing uses canvas coordinates.
        self.node_items[node_id] = {
            "rect": rect, "text": text, "node": node,
            "level": level, "x": x, "y": y,
            "width": self.node_width, "height": self.node_height
        }

        # 递归绘制子节点
        if not node.get("_collapsed", False):
            for child in children:
                self._draw_nodes(child, positions, level + 1)

    def _draw_node_bg(self, x, y, bg_color, border_color, border_width, shadow_fill, node_id, level):
        """绘制节点背景"""
        style = getattr(self, "current_style", "default")
        shadow_offset = 3
        tags = ("node", f"node_{node_id}", "node_rect")
        shadow_tags = f"shadow_{node_id}"

        if style == "three_act":
            if level == 0:
                self._create_diamond(x + shadow_offset, y + shadow_offset, self.node_width, self.node_height, fill=shadow_fill, tags=shadow_tags)
                return self._create_diamond(x, y, self.node_width, self.node_height, fill=bg_color, outline=border_color, width=border_width, tags=tags)
            elif level == 1:
                self._create_chamfered_rect(x + shadow_offset, y + shadow_offset, self.node_width, self.node_height, 10, fill=shadow_fill, tags=shadow_tags)
                return self._create_chamfered_rect(x, y, self.node_width, self.node_height, 10, fill=bg_color, outline=border_color, width=border_width, tags=tags)
        elif style == "hero_journey":
            self._create_capsule(x + shadow_offset, y + shadow_offset, self.node_width, self.node_height, fill=shadow_fill, tags=shadow_tags)
            return self._create_capsule(x, y, self.node_width, self.node_height, fill=bg_color, outline=border_color, width=border_width, tags=tags)
        elif style == "comedy_structure":
            if level == 0:
                self._create_cloud(x + shadow_offset, y + shadow_offset, self.node_width, self.node_height, fill=shadow_fill, tags=shadow_tags)
                return self._create_cloud(x, y, self.node_width, self.node_height, fill=bg_color, outline=border_color, width=border_width, tags=tags)
            else:
                self.create_oval(x + shadow_offset, y + shadow_offset, x + self.node_width + shadow_offset, y + self.node_height + shadow_offset, fill=shadow_fill, outline="", tags=shadow_tags)
                return self.create_oval(x, y, x + self.node_width, y + self.node_height, fill=bg_color, outline=border_color, width=border_width, tags=tags)

        # Default: Rounded Rect
        self._create_rounded_rect(x + shadow_offset, y + shadow_offset, x + self.node_width + shadow_offset, y + self.node_height + shadow_offset, 8, fill=shadow_fill, outline="", tags=shadow_tags)
        return self._create_rounded_rect(x, y, x + self.node_width, y + self.node_height, 8, fill=bg_color, outline=border_color, width=border_width, tags=tags)

    # ==================== 形状绘制方法 ====================

    def _create_diamond(self, x, y, w, h, **kwargs):
        points = [x, y + h / 2, x + w / 2, y, x + w, y + h / 2, x + w / 2, y + h]
        return self.create_polygon(points, **kwargs)

    def _create_chamfered_rect(self, x, y, w, h, chamfer, **kwargs):
        points = [x + chamfer, y, x + w - chamfer, y, x + w, y + chamfer,
                  x + w, y + h - chamfer, x + w - chamfer, y + h, x + chamfer, y + h,
                  x, y + h - chamfer, x, y + chamfer]
        return self.create_polygon(points, **kwargs)

    def _create_capsule(self, x, y, w, h, **kwargs):
        radius = h / 2
        return self._create_rounded_rect(x, y, x + w, y + h, radius, **kwargs)

    def _create_cloud(self, x, y, w, h, **kwargs):
        points = []
        steps = 10
        cx, cy = x + w / 2, y + h / 2
        rx, ry = w / 2, h / 2
        for i in range(steps * 2):
            angle = math.pi * i / steps
            r_mod = 1.1 if i % 2 == 0 else 0.9
            px = cx + math.cos(angle) * rx * r_mod
            py = cy + math.sin(angle) * ry * r_mod
            points.extend([px, py])
        return self.create_polygon(points, smooth=True, **kwargs)

    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
                  x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
                  x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    # ==================== 事件处理方法 ====================

    def _get_add_btn_at(self, x, y):
        """获取指定位置的添加按钮对应的节点ID"""
        items = self.find_overlapping(x - 2, y - 2, x + 2, y + 2)
        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith("add_btn_"):
                    return tag[8:]
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
        """鼠标悬停显示提示"""
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
        """鼠标离开"""
        self.hover_node_id = None
        self._hide_tooltip()

    def on_mousewheel(self, event):
        """鼠标滚轮滚动"""
        if event.state & 0x0004: # Control key
             self.on_zoom(event) # Handled by ZoomableCanvas
        else:
             self.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_right_click(self, event):
        """右键菜单"""
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        node_id = self._get_node_at(x, y)
        if node_id and node_id not in self._selected_node_ids:
            self.select_node(node_id)
        
        # 刷新状态菜单内容
        self._update_status_menu()
        self._apply_ai_menu_state()
        self.context_menu.post(event.x_root, event.y_root)

    def on_delete_key(self, event):
        """Delete键删除"""
        self.delete_selected_node()

    def on_tab_key(self, event):
        """Tab键添加子节点"""
        self.add_child_to_selected()
        return "break"

    def on_enter_key(self, event):
        """Enter键"""
        if self.editing_node_id:
            self._close_edit_entry()
        else:
            self.add_sibling_to_selected()
        return "break"

    def on_escape_key(self, event):
        """Escape键"""
        if self.editing_node_id:
            self._close_edit_entry(save=False)
        else:
            self.deselect_all()

    def on_click(self, event):
        """点击事件"""
        self.focus_set()
        self._close_edit_entry()
        self._hide_tooltip()

        x = self.canvasx(event.x)
        y = self.canvasy(event.y)

        # 检查添加按钮
        add_btn_node_id = self._get_add_btn_at(x, y)
        if add_btn_node_id:
            self._add_child_node(add_btn_node_id)
            return

        # 检查折叠按钮
        collapse_btn_node_id = self._get_collapse_btn_at(x, y)
        if collapse_btn_node_id:
            self._toggle_collapse(collapse_btn_node_id)
            return

        # 检查节点
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
        """Ctrl+点击多选"""
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
        """双击编辑"""
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        node_id = self._get_node_at(x, y)
        if node_id:
            self.select_node(node_id)
            self._start_edit(node_id)

    def on_drag(self, event):
        """拖拽事件"""
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
                        nh = self.node_height
                        nw = self.node_width
                        rel_y = y - ny

                        if rel_y < nh * 0.25:
                            self.drop_target_item = self.create_line(nx, ny - 2, nx + nw, ny - 2,
                                                                    fill="#2196F3", width=3, tags="drop_target")
                            self.drag_data["target_id"] = target_id
                            self.drag_data["action"] = "before"
                        elif rel_y > nh * 0.75:
                            self.drop_target_item = self.create_line(nx, ny + nh + 2, nx + nw, ny + nh + 2,
                                                                    fill="#2196F3", width=3, tags="drop_target")
                            self.drag_data["target_id"] = target_id
                            self.drag_data["action"] = "after"
                        else:
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
        """释放事件"""
        if self.rubber_band_rect:
            self.delete(self.rubber_band_rect)
            self.rubber_band_rect = None

        if self.drag_data["dragging"]:
            target_id = self.drag_data.get("target_id")
            action = self.drag_data.get("action")
            node_id = self.drag_data["node_id"]

            if target_id and node_id and action:
                command = None

                if action == "reparent":
                    command = MoveNodeCommand(self.project_manager, node_id, target_id)
                elif action in ("before", "after"):
                    target_node_data = self.node_items.get(target_id, {}).get("node")
                    if target_node_data and target_node_data is not self.root_node:
                        parent_node = self._find_parent(self.root_node, target_node_data)
                        if parent_node:
                            parent_id = parent_node.get("uid")
                            children = parent_node.get("children", [])
                            try:
                                target_idx = children.index(target_node_data)
                                new_index = target_idx if action == "before" else target_idx + 1
                                command = MoveNodeCommand(self.project_manager, node_id, parent_id, index=new_index)
                            except ValueError:
                                pass

                if command and self.command_executor(command):
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
        """添加子节点"""
        if len(self._selected_node_ids) == 1:
            self._add_child_node(list(self._selected_node_ids)[0])
        elif not self._selected_node_ids and self.root_node:
            self._add_child_node(self.root_node.get("uid"))

    def add_sibling_to_selected(self):
        """添加同级节点"""
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
        """添加子节点"""
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
        """删除选中节点"""
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
        """切换折叠状态"""
        if node_id not in self.node_items:
            return
        node = self.node_items[node_id]["node"]
        node["_collapsed"] = not node.get("_collapsed", False)
        self.refresh()
