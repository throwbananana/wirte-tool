"""
大纲视图抽象基类
BaseOutlineView - Abstract base class for all outline visualization views
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from abc import ABC, abstractmethod
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
import os
import tempfile


class BaseOutlineView(tk.Canvas, ABC):
    """
    大纲视图抽象基类
    所有大纲可视化视图（水平树、垂直树、放射图、表格等）都应继承此类
    """

    # 默认节点颜色配置
    NODE_COLORS = [
        ("#4A90D9", "#FFFFFF"),  # 根节点: 蓝色
        ("#5CB85C", "#FFFFFF"),  # 一级: 绿色
        ("#F0AD4E", "#FFFFFF"),  # 二级: 橙色
        ("#D9534F", "#FFFFFF"),  # 三级: 红色
        ("#9B59B6", "#FFFFFF"),  # 四级: 紫色
        ("#1ABC9C", "#FFFFFF"),  # 五级: 青色
    ]

    def __init__(self, parent, project_manager, command_executor,
                 on_node_select=None, on_ai_suggest_branch=None,
                 on_generate_scene=None, on_set_tags=None, 
                 on_jump_to_scene=None, **kwargs):
        """
        初始化基类

        Args:
            parent: 父容器
            project_manager: 项目管理器实例
            command_executor: 命令执行函数
            on_node_select: 节点选中回调
            on_ai_suggest_branch: AI建议分支回调
            on_generate_scene: 生成场景回调
            on_set_tags: 设置标签回调
            on_jump_to_scene: 跳转到关联场景回调
        """
        super().__init__(parent, bg="#F8F9FA", highlightthickness=0, **kwargs)

        self.project_manager = project_manager
        self.command_executor = command_executor
        self.on_node_select = on_node_select
        self.on_ai_suggest_branch = on_ai_suggest_branch
        self.on_generate_scene = on_generate_scene
        self.on_set_tags = on_set_tags
        self.on_jump_to_scene = on_jump_to_scene
        self.ai_mode_enabled = True

        # 通用数据
        self.root_node = None
        self.node_items = {}  # node_id -> {"rect": item, "text": item, "node": data, ...}
        self._selected_node_ids = set()

        # 场景计数和标签过滤
        self.scene_counts = {}
        self.tag_filter = None
        self.current_theme_manager = None

        # 编辑状态
        self.editing_node_id = None
        self.edit_entry = None
        self.hover_node_id = None
        self.tooltip_window = None

        # 使canvas可以获取焦点
        self.configure(takefocus=True)

        # 右键菜单
        self.context_menu = tk.Menu(self, tearoff=0)
        self._setup_context_menu()
        self._apply_ai_menu_state()

    def export_to_image(self):
        """导出当前画布为图片"""
        if not HAS_PIL:
            messagebox.showerror("错误", "未安装 PIL (Pillow) 库，无法导出图片。\n请运行 pip install pillow")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            title="导出思维导图"
        )
        
        if not file_path:
            return
            
        try:
            # 获取画布内容的边界框
            bbox = self.bbox("all")
            if not bbox:
                messagebox.showwarning("提示", "画布为空，无法导出")
                return
                
            x1, y1, x2, y2 = bbox
            # 增加一些内边距
            padding = 20
            x1 -= padding
            y1 -= padding
            x2 += padding
            y2 += padding
            
            # 生成 PostScript
            # 注意: pageheight/width 必须足够大以包含内容
            width = x2 - x1
            height = y2 - y1
            
            ps_data = self.postscript(colormode='color', x=x1, y=y1, width=width, height=height)
            
            if ps_data:
                # 使用临时文件保存 PS 数据，然后用 PIL 读取
                # 直接传给 Image.open(io.BytesIO(ps_data)) 有时会出错，特别是 Windows 上
                with tempfile.NamedTemporaryFile(suffix='.ps', delete=False) as tmp_ps:
                    tmp_ps.write(ps_data.encode('utf-8'))
                    tmp_ps_path = tmp_ps.name
                
                try:
                    img = Image.open(tmp_ps_path)
                    # 提高分辨率 (可选)
                    # img.load(scale=2) 
                    img.save(file_path, "PNG")
                    messagebox.showinfo("成功", f"图片已导出至:\n{file_path}")
                finally:
                    if os.path.exists(tmp_ps_path):
                        os.unlink(tmp_ps_path)
            else:
                messagebox.showerror("错误", "生成 PostScript 数据失败")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("导出失败", f"导出图片时发生错误:\n{str(e)}")

    @property
    def selected_node_ids(self):
        """获取选中的节点ID集合"""
        return self._selected_node_ids

    @selected_node_ids.setter
    def selected_node_ids(self, value):
        """设置选中的节点ID集合"""
        self._selected_node_ids = value

    # ==================== 抽象方法 - 子类必须实现 ====================

    @abstractmethod
    def _calculate_layout(self, node, *args, **kwargs):
        """
        计算节点布局位置
        子类需要实现自己的布局算法
        """
        pass

    @abstractmethod
    def _draw_connections(self, node, positions):
        """
        绘制节点之间的连接线
        子类需要实现自己的连线风格
        """
        pass

    @abstractmethod
    def _draw_nodes(self, node, positions, level):
        """
        绘制所有节点
        子类可以覆盖以实现不同的节点样式
        """
        pass

    # ==================== 通用方法 ====================

    def _setup_context_menu(self):
        """设置右键菜单"""
        self.context_menu.add_command(label="添加子节点", command=self.add_child_to_selected, accelerator="Tab")
        self.context_menu.add_command(label="添加同级节点", command=self.add_sibling_to_selected, accelerator="Enter")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="编辑节点", command=self.edit_selected_node)
        self.context_menu.add_command(label="删除节点", command=self.delete_selected_node, accelerator="Delete")
        self.context_menu.add_separator()
        
        # 场景状态子菜单
        self.status_menu = tk.Menu(self.context_menu, tearoff=0)
        self.context_menu.add_cascade(label="修改关联场景状态", menu=self.status_menu)
        
        self.context_menu.add_separator()
        self.context_menu.add_command(label="跳转到关联场景", command=self._on_jump_to_linked_scene)
        self.context_menu.add_command(label="生成剧本场景", command=self._on_generate_scene_script)
        self.context_menu.add_command(label="生成建议子节点...", command=self._on_generate_ai_branch)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="设置标签...", command=self._on_set_tags)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="展开子节点", command=self.expand_selected)
        self.context_menu.add_command(label="折叠子节点", command=self.collapse_selected)

    def set_ai_mode_enabled(self, enabled: bool):
        self.ai_mode_enabled = bool(enabled)
        self._apply_ai_menu_state()

    def _apply_ai_menu_state(self):
        state = tk.NORMAL if self.ai_mode_enabled else tk.DISABLED
        for label in ("生成剧本场景", "生成建议子节点..."):
            try:
                self.context_menu.entryconfig(label, state=state)
            except tk.TclError:
                pass

    def _update_status_menu(self):
        """根据当前选中节点更新状态菜单"""
        self.status_menu.delete(0, tk.END)
        if len(self._selected_node_ids) != 1:
            self.status_menu.add_command(label="请先选择一个节点", state=tk.DISABLED)
            return

        node_id = list(self._selected_node_ids)[0]
        scenes = self.project_manager.get_scenes_by_outline_uid(node_id)
        if not scenes:
            self.status_menu.add_command(label="无关联场景", state=tk.DISABLED)
            return

        columns = self.project_manager.get_kanban_columns()
        for col in columns:
            self.status_menu.add_command(
                label=col,
                command=lambda c=col: self._change_linked_scenes_status(node_id, c)
            )

    def _change_linked_scenes_status(self, node_id, new_status):
        """修改与大纲节点关联的所有场景的状态"""
        scenes = self.project_manager.get_scenes_by_outline_uid(node_id)
        if not scenes: return
        
        from writer_app.core.commands import EditSceneCommand
        for idx, scene_data in scenes:
            if scene_data.get("status") != new_status:
                old_data = dict(scene_data)
                new_data = dict(scene_data)
                new_data["status"] = new_status
                cmd = EditSceneCommand(self.project_manager, idx, old_data, new_data, f"更改场景状态为 {new_status}")
                self.command_executor(cmd)
        
        self.refresh()

    def _get_node_status_info(self, node_id):
        """获取节点的关联场景状态信息"""
        scenes = self.project_manager.get_scenes_by_outline_uid(node_id)
        if not scenes:
            return None, None
            
        # 如果有多个场景，取第一个的状态（通常大纲节点与场景是一一或一对多）
        status = scenes[0][1].get("status")
        columns = self.project_manager.get_kanban_columns()
        
        if not status or status not in columns:
            return status, 0
            
        try:
            idx = columns.index(status)
            progress = (idx + 1) / len(columns)
            return status, progress
        except ValueError:
            return status, 0

    def _on_jump_to_linked_scene(self):
        """跳转到与当前选中节点关联的第一个场景"""
        if self.on_jump_to_scene and len(self._selected_node_ids) == 1:
            node_id = list(self._selected_node_ids)[0]
            scenes = self.project_manager.get_scenes_by_outline_uid(node_id)
            if scenes:
                # Jump to the first linked scene
                scene_idx, _ = scenes[0]
                self.on_jump_to_scene(scene_idx)
            else:
                messagebox.showinfo("提示", "该节点尚未关联任何场景。可在剧本编辑器的场景信息中进行关联。")

    def set_data(self, root_node):
        """设置数据并重绘"""
        self.root_node = root_node
        self.refresh()

    def set_scene_counts(self, counts):
        """接收外部传入的关联场景数量映射：outline_uid -> count"""
        self.scene_counts = counts or {}

    def set_tag_filter(self, tags):
        """设置标签过滤；None或空表示不过滤；可传入字符串或可迭代集合"""
        if not tags:
            self.tag_filter = None
        elif isinstance(tags, (list, set, tuple)):
            self.tag_filter = set(tags)
        else:
            self.tag_filter = {tags}

    def apply_theme(self, theme_manager):
        """应用主题"""
        self.current_theme_manager = theme_manager
        self.configure(bg=theme_manager.get_color("canvas_bg"))
        self.refresh()

    def refresh(self):
        """刷新画布 - 子类可以覆盖但应调用此基类方法"""
        self._close_edit_entry()
        self._hide_tooltip()
        self.delete("all")
        self.node_items.clear()

    def _subtree_matches_filter(self, node):
        """检查节点或其子孙是否满足标签过滤"""
        if not self.tag_filter:
            return True
        if not node:
            return False
        filters = set(self.tag_filter) if isinstance(self.tag_filter, (list, set, tuple)) else {self.tag_filter}
        if filters.intersection(set(node.get("tags", []))):
            return True
        for child in node.get("children", []):
            if self._subtree_matches_filter(child):
                return True
        return False

    # ==================== 节点选择方法 ====================

    def select_node(self, node_id, add=False):
        """选中节点"""
        if not add:
            for old_id in self._selected_node_ids:
                self._highlight_node(old_id, False)
            self._selected_node_ids.clear()

        if node_id in self.node_items:
            self._selected_node_ids.add(node_id)
            self._highlight_node(node_id, True)

            if self.on_node_select and not add:
                node = self.node_items[node_id]["node"]
                self.on_node_select(node)

    def deselect_all(self):
        """取消所有选中"""
        for node_id in self._selected_node_ids:
            self._highlight_node(node_id, False)
        self._selected_node_ids.clear()

    def _highlight_node(self, node_id, highlight):
        """高亮或取消高亮节点"""
        if node_id not in self.node_items:
            return

        node_info = self.node_items[node_id]
        rect = node_info.get("rect")
        if rect:
            if highlight:
                self.itemconfig(rect, width=3, outline="#2196F3")
            else:
                level = node_info.get("level", 0)
                border_color = "#333333"
                if self.current_theme_manager and self.current_theme_manager.current_theme == "Dark":
                    border_color = "#AAAAAA"
                self.itemconfig(rect, width=2, outline=border_color)

    # ==================== 编辑相关方法 ====================

    def _close_edit_entry(self, save=True):
        """关闭编辑输入框"""
        if self.edit_entry and self.editing_node_id:
            if save:
                new_name = self.edit_entry.get().strip()
                if new_name:
                    node = self.node_items.get(self.editing_node_id, {}).get("node")
                    if node and new_name != node.get("name", ""):
                        from writer_app.core.commands import EditNodeCommand
                        command = EditNodeCommand(
                            self.project_manager,
                            self.editing_node_id,
                            {"name": new_name},
                            "编辑节点名称"
                        )
                        if self.command_executor(command):
                            self.refresh()

            self.edit_entry.destroy()
            self.edit_entry = None
            self.editing_node_id = None

    def _start_edit(self, node_id):
        """开始编辑节点"""
        if node_id not in self.node_items:
            return

        self._close_edit_entry()

        node_info = self.node_items[node_id]
        node = node_info["node"]
        x, y = node_info.get("x", 0), node_info.get("y", 0)
        width = node_info.get("width", 140)
        height = node_info.get("height", 36)

        self.editing_node_id = node_id

        self.edit_entry = tk.Entry(
            self,
            font=("Microsoft YaHei", 10),
            justify=tk.CENTER,
            width=15
        )
        self.edit_entry.insert(0, node.get("name", ""))
        self.edit_entry.select_range(0, tk.END)

        self.create_window(
            x + width / 2,
            y + height / 2,
            window=self.edit_entry,
            tags="edit_entry"
        )

        self.edit_entry.focus_set()
        self.edit_entry.bind("<Return>", lambda e: self._close_edit_entry(save=True))
        self.edit_entry.bind("<Escape>", lambda e: self._close_edit_entry(save=False))
        self.edit_entry.bind("<FocusOut>", lambda e: self._close_edit_entry(save=True))

    def _select_and_edit(self, node_id):
        """选中并开始编辑节点"""
        if node_id in self.node_items:
            self.select_node(node_id)
            self._start_edit(node_id)

    # ==================== 提示框方法 ====================

    def _show_tooltip(self, node_id, x_root, y_root):
        """显示节点提示"""
        node = self.node_items.get(node_id, {}).get("node")
        if not node:
            return

        full_name = node.get("name", "未命名")
        tag_text = ", ".join(node.get("tags", []))
        content_text = node.get("content", "").strip().replace("\n", " ")
        if len(content_text) > 80:
            content_text = content_text[:77] + "..."

        lines = [full_name]
        if tag_text:
            lines.append(f"标签: {tag_text}")
        if content_text:
            lines.append(f"备注: {content_text}")

        tooltip_text = "\n".join(lines)

        self.tooltip_window = tk.Toplevel(self)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes("-topmost", True)

        bg = "#333333"
        fg = "#FFFFFF"
        if self.current_theme_manager and self.current_theme_manager.current_theme == "Light":
            bg = "#FFFFE0"
            fg = "#000000"

        label = tk.Label(
            self.tooltip_window,
            text=tooltip_text,
            bg=bg,
            fg=fg,
            justify=tk.LEFT,
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=5,
            font=("Microsoft YaHei", 9)
        )
        label.pack()
        self._position_tooltip(x_root, y_root)

    def _position_tooltip(self, x_root, y_root):
        """根据鼠标位置调整提示框位置"""
        if self.tooltip_window:
            self.tooltip_window.geometry(f"+{int(x_root) + 12}+{int(y_root) + 12}")

    def _hide_tooltip(self):
        """隐藏悬浮提示"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    # ==================== 回调方法 ====================

    def _on_generate_ai_branch(self):
        """调用AI生成建议子节点"""
        if self.on_ai_suggest_branch and len(self._selected_node_ids) == 1:
            node_id = list(self._selected_node_ids)[0]
            node = self.node_items.get(node_id, {}).get("node")
            if node:
                self.on_ai_suggest_branch(node)

    def _on_generate_scene_script(self):
        """调用生成剧本场景"""
        if self.on_generate_scene and len(self._selected_node_ids) == 1:
            node_id = list(self._selected_node_ids)[0]
            node = self.node_items.get(node_id, {}).get("node")
            if node:
                self.on_generate_scene(node)

    def _on_set_tags(self):
        """设置标签"""
        if self.on_set_tags and len(self._selected_node_ids) == 1:
            node_id = list(self._selected_node_ids)[0]
            node = self.node_items[node_id]["node"]
            self.on_set_tags(node)

    # ==================== 节点操作方法 (通用实现，子类可覆盖) ====================

    def add_child_to_selected(self):
        """为选中节点添加子节点"""
        if len(self._selected_node_ids) == 1:
            self._add_child_node(list(self._selected_node_ids)[0])
        elif not self._selected_node_ids and self.root_node:
            self._add_child_node(self.root_node.get("uid"))

    def _add_child_node(self, parent_node_id):
        """添加子节点的内部实现"""
        if parent_node_id not in self.node_items:
            # 如果是根节点，直接使用root_node
            if self.root_node and self.root_node.get("uid") == parent_node_id:
                parent_node = self.root_node
            else:
                return
        else:
            parent_node = self.node_items[parent_node_id]["node"]

        from writer_app.core.commands import AddNodeCommand
        new_node = {"name": "新节点", "content": "", "children": []}
        command = AddNodeCommand(self.project_manager, parent_node_id, new_node, "添加子节点")
        if self.command_executor(command):
            parent_node["_collapsed"] = False
            self.refresh()
            new_node_id = command.added_node_uid
            if new_node_id:
                self.after(50, lambda nid=new_node_id: self._select_and_edit(nid))

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
            from writer_app.core.commands import AddNodeCommand
            new_node = {"name": "新节点", "content": "", "children": []}
            children = parent.get("children", [])
            idx = children.index(selected_node) if selected_node in children else len(children)

            command = AddNodeCommand(self.project_manager, parent.get("uid"), new_node, "添加同级节点", insert_index=idx + 1)
            if self.command_executor(command):
                self.refresh()
                new_node_id = command.added_node_uid
                if new_node_id:
                    self.after(50, lambda nid=new_node_id: self._select_and_edit(nid))

    def edit_selected_node(self):
        """编辑选中的节点"""
        if len(self._selected_node_ids) == 1:
            self._start_edit(list(self._selected_node_ids)[0])

    def delete_selected_node(self):
        """删除选中的节点"""
        if not self._selected_node_ids:
            return

        count = len(self._selected_node_ids)
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {count} 个节点及其所有子节点吗?"):
            return

        from writer_app.core.commands import DeleteNodesCommand
        command = DeleteNodesCommand(self.project_manager, self._selected_node_ids, "删除节点")
        if self.command_executor(command):
            self._selected_node_ids.clear()
            self.refresh()

    def expand_selected(self):
        """展开选中节点"""
        for node_id in self._selected_node_ids:
            if node_id in self.node_items:
                node = self.node_items[node_id]["node"]
                node["_collapsed"] = False
        self.refresh()

    def collapse_selected(self):
        """折叠选中节点"""
        for node_id in self._selected_node_ids:
            if node_id in self.node_items:
                node = self.node_items[node_id]["node"]
                node["_collapsed"] = True
        self.refresh()

    # ==================== 辅助方法 ====================

    def _find_parent(self, root, target):
        """递归查找目标节点的父节点"""
        for child in root.get("children", []):
            if child is target:
                return root
            result = self._find_parent(child, target)
            if result:
                return result
        return None

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
