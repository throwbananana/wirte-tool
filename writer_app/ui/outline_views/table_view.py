"""
大纲表格视图 (Table View)
类似Word大纲视图的可折叠缩进列表
"""
import tkinter as tk
from tkinter import ttk, messagebox
from writer_app.core.commands import AddNodeCommand, DeleteNodesCommand, EditNodeCommand, MoveNodeCommand
from .base_view import BaseOutlineView


class TableView(BaseOutlineView):
    """大纲表格视图 - 使用Treeview实现的缩进列表"""

    def __init__(self, parent, project_manager, command_executor,
                 on_node_select=None, on_ai_suggest_branch=None,
                 on_generate_scene=None, on_set_tags=None, 
                 on_jump_to_scene=None, **kwargs):
        # 移除Canvas特有的参数
        kwargs.pop('xscrollcommand', None)
        kwargs.pop('yscrollcommand', None)

        # 保存parent引用
        self._parent = parent

        super().__init__(parent, project_manager, command_executor,
                        on_node_select, on_ai_suggest_branch,
                        on_generate_scene, on_set_tags, 
                        on_jump_to_scene, **kwargs)

        # 创建Treeview容器 - 嵌入到Canvas中
        self.tree_frame = tk.Frame(self, bg="#FFFFFF")
        
        # 创建Treeview控件
        columns = ("tags", "scenes", "status", "word_count", "pov")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, selectmode="extended")

        # 排序状态
        self._sort_column = None
        self._sort_reverse = False

        # 配置列（点击标题排序）
        self.tree.heading("#0", text="节点名称 ▽", anchor=tk.W,
                          command=lambda: self._sort_by_column("#0"))
        self.tree.heading("tags", text="标签", anchor=tk.W,
                          command=lambda: self._sort_by_column("tags"))
        self.tree.heading("scenes", text="场景", anchor=tk.CENTER,
                          command=lambda: self._sort_by_column("scenes"))
        self.tree.heading("status", text="状态", anchor=tk.CENTER,
                          command=lambda: self._sort_by_column("status"))
        self.tree.heading("word_count", text="字数", anchor=tk.CENTER,
                          command=lambda: self._sort_by_column("word_count"))
        self.tree.heading("pov", text="视角(POV)", anchor=tk.W,
                          command=lambda: self._sort_by_column("pov"))

        # 配置列宽 - stretch=True允许列自动扩展填充空间
        self.tree.column("#0", width=250, minwidth=150, stretch=True)
        self.tree.column("tags", width=120, minwidth=80, stretch=True)
        self.tree.column("scenes", width=50, minwidth=40, stretch=False)
        self.tree.column("status", width=70, minwidth=60, stretch=False)
        self.tree.column("word_count", width=60, minwidth=50, stretch=False)
        self.tree.column("pov", width=80, minwidth=60, stretch=True)

        # 滚动条
        y_scroll = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(self.tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        # 嵌入到Canvas
        self.window_id = self.create_window(0, 0, window=self.tree_frame, anchor="nw")
        self.bind("<Configure>", self.on_resize)

        # 节点ID映射
        self.tree_item_to_node = {}  # tree item id -> node data
        self.node_to_tree_item = {}  # node uid -> tree item id

        # 绑定事件
        self._bind_events()

        # 配置样式
        self._setup_styles()

    def on_resize(self, event):
        self.itemconfigure(self.window_id, width=event.width, height=event.height)

    def _sort_by_column(self, column):
        """点击列标题排序"""
        # 更新排序状态
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = False

        # 更新列标题显示排序方向
        columns = ["#0", "tags", "scenes", "status", "word_count", "pov"]
        column_names = ["节点名称", "标签", "场景", "状态", "字数", "视角(POV)"]

        for col, name in zip(columns, column_names):
            if col == column:
                arrow = " ▲" if self._sort_reverse else " ▽"
                self.tree.heading(col, text=name + arrow)
            else:
                self.tree.heading(col, text=name)

        # 收集所有顶级项目并排序
        items = list(self.tree.get_children(""))
        if not items:
            return

        # 获取排序键
        def get_sort_key(item):
            if column == "#0":
                return self.tree.item(item, "text").lower()
            else:
                values = self.tree.item(item, "values")
                col_idx = columns.index(column) - 1  # -1 因为#0不在values中
                if col_idx < 0 or col_idx >= len(values):
                    return ""
                val = values[col_idx]
                # 数字列特殊处理
                if column in ("scenes", "word_count"):
                    try:
                        return int(val) if val else 0
                    except ValueError:
                        return 0
                return str(val).lower()

        # 排序并重新排列
        items.sort(key=get_sort_key, reverse=self._sort_reverse)

        for idx, item in enumerate(items):
            self.tree.move(item, "", idx)

    def _setup_styles(self):
        """配置Treeview样式"""
        style = ttk.Style()

        # 配置行高
        style.configure("Treeview", rowheight=28)

        # 配置颜色标签
        self.tree.tag_configure("level_0", background="#E3F2FD")
        self.tree.tag_configure("level_1", background="#E8F5E9")
        self.tree.tag_configure("level_2", background="#FFF3E0")
        self.tree.tag_configure("level_3", background="#FCE4EC")
        self.tree.tag_configure("level_4", background="#F3E5F5")
        self.tree.tag_configure("level_5", background="#E0F7FA")
        self.tree.tag_configure("has_content", foreground="#1565C0")
        self.tree.tag_configure("status_draft", foreground="#1976D2")
        self.tree.tag_configure("status_final", foreground="#2E7D32")

    def _bind_events(self):
        """绑定事件"""
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<Delete>", self.on_delete_key)
        self.tree.bind("<Tab>", self.on_tab_key)
        self.tree.bind("<Return>", self.on_enter_key)

    # ==================== 布局实现 ====================

    def _calculate_layout(self, node, *args, **kwargs):
        """表格视图不需要计算布局"""
        pass

    def _draw_connections(self, node, positions):
        """表格视图不需要绘制连线"""
        pass

    def _draw_nodes(self, node, positions, level):
        """表格视图不需要绘制节点（由Treeview处理）"""
        pass

    def refresh(self):
        """刷新视图"""
        # 清理
        self._hide_tooltip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_to_node.clear()
        self.node_to_tree_item.clear()
        self.node_items.clear()

        if not self.root_node:
            return

        # 递归添加节点
        self._add_tree_node(self.root_node, "", 0)

        # 展开所有节点（或根据折叠状态）
        self._restore_expand_state(self.root_node)

    def _add_tree_node(self, node, parent_item, level):
        """递归添加树节点"""
        if not self._subtree_matches_filter(node):
            return None

        node_id = node.get("uid")
        name = node.get("name", "未命名")

        # 获取标签
        tags_list = node.get("tags", [])
        tags_str = ", ".join(tags_list) if tags_list else ""

        # 获取场景数、状态、字数、POV
        scene_count = self.scene_counts.get(node_id, 0)
        scene_str = str(scene_count) if scene_count else ""
        
        status_str = ""
        word_count = 0
        pov_list = set()
        
        scenes = self.project_manager.get_scenes()
        for scene in scenes:
            if scene.get("outline_ref_id") == node_id:
                if not status_str and scene.get("status"):
                    status_str = scene.get("status")
                word_count += len(scene.get("content", ""))
                # POV extraction: Try to find "POV: Name" in scene text or metadata
                # For now, simplistic check if POV is a field in scene data (future proofing)
                if "pov" in scene: pov_list.add(scene["pov"])
        
        word_count_str = str(word_count) if word_count > 0 else ""
        pov_str = ", ".join(pov_list)

        # 添加到树
        tree_tags = [f"level_{min(level, 5)}"]
        if node.get("content", "").strip():
            tree_tags.append("has_content")
        if status_str in ["初稿", "润色"]:
            tree_tags.append("status_draft")
        elif status_str == "定稿":
            tree_tags.append("status_final")

        item_id = self.tree.insert(
            parent_item, "end",
            text=name,
            values=(tags_str, scene_str, status_str, word_count_str, pov_str),
            tags=tree_tags,
            open=not node.get("_collapsed", False)
        )

        # 保存映射
        self.tree_item_to_node[item_id] = node
        self.node_to_tree_item[node_id] = item_id
        self.node_items[node_id] = {"node": node, "tree_item": item_id, "level": level}

        # 递归添加子节点
        children = [child for child in node.get("children", []) if self._subtree_matches_filter(child)]
        for child in children:
            self._add_tree_node(child, item_id, level + 1)

        return item_id

    def _restore_expand_state(self, node):
        """恢复展开/折叠状态"""
        node_id = node.get("uid")
        tree_item = self.node_to_tree_item.get(node_id)
        if tree_item:
            if node.get("_collapsed", False):
                self.tree.item(tree_item, open=False)
            else:
                self.tree.item(tree_item, open=True)

        for child in node.get("children", []):
            self._restore_expand_state(child)

    # ==================== 事件处理 ====================

    def on_tree_select(self, event):
        """树选择事件"""
        selected = self.tree.selection()
        self._selected_node_ids.clear()

        for item in selected:
            node = self.tree_item_to_node.get(item)
            if node:
                node_id = node.get("uid")
                self._selected_node_ids.add(node_id)

        # 回调
        if self.on_node_select and len(selected) == 1:
            node = self.tree_item_to_node.get(selected[0])
            if node:
                self.on_node_select(node)

    def on_double_click(self, event):
        """双击编辑"""
        item = self.tree.identify_row(event.y)
        if item:
            self._start_tree_edit(item)

    def on_right_click(self, event):
        """右键菜单"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.on_tree_select(None)
        self._update_status_menu()
        self._apply_ai_menu_state()
        self.context_menu.post(event.x_root, event.y_root)

    def on_delete_key(self, event):
        """删除键"""
        self.delete_selected_node()

    def on_tab_key(self, event):
        """Tab键添加子节点"""
        self.add_child_to_selected()
        return "break"

    def on_enter_key(self, event):
        """Enter键"""
        if self.editing_node_id:
            self._finish_tree_edit()
        else:
            self.add_sibling_to_selected()
        return "break"

    # ==================== 编辑功能 ====================

    def _start_tree_edit(self, item):
        """开始编辑树节点"""
        node = self.tree_item_to_node.get(item)
        if not node:
            return

        self.editing_node_id = node.get("uid")

        # 获取项目位置
        bbox = self.tree.bbox(item, "#0")
        if not bbox:
            return

        x, y, width, height = bbox

        # 创建编辑框
        self.edit_entry = tk.Entry(self.tree, font=("Microsoft YaHei", 10))
        self.edit_entry.insert(0, node.get("name", ""))
        self.edit_entry.select_range(0, tk.END)

        self.edit_entry.place(x=x + 20, y=y, width=width - 20, height=height)
        self.edit_entry.focus_set()

        self.edit_entry.bind("<Return>", lambda e: self._finish_tree_edit())
        self.edit_entry.bind("<Escape>", lambda e: self._cancel_tree_edit())
        self.edit_entry.bind("<FocusOut>", lambda e: self._finish_tree_edit())

    def _finish_tree_edit(self):
        """完成编辑"""
        if not self.edit_entry or not self.editing_node_id:
            return

        new_name = self.edit_entry.get().strip()
        if new_name:
            node_id = self.editing_node_id
            node = self.node_items.get(node_id, {}).get("node")
            if node and new_name != node.get("name", ""):
                from writer_app.core.commands import EditNodeCommand
                command = EditNodeCommand(
                    self.project_manager,
                    node_id,
                    {"name": new_name},
                    "编辑节点名称"
                )
                if self.command_executor(command):
                    tree_item = self.node_to_tree_item.get(node_id)
                    if tree_item:
                        self.tree.item(tree_item, text=new_name)

        self._cleanup_edit()

    def _cancel_tree_edit(self):
        """取消编辑"""
        self._cleanup_edit()

    def _cleanup_edit(self):
        """清理编辑状态"""
        if self.edit_entry:
            self.edit_entry.destroy()
            self.edit_entry = None
        self.editing_node_id = None

    # ==================== 节点操作 ====================

    def select_node(self, node_id, add=False):
        """选中节点"""
        tree_item = self.node_to_tree_item.get(node_id)
        if not tree_item:
            return

        if not add:
            self.tree.selection_set(tree_item)
        else:
            self.tree.selection_add(tree_item)

        self.tree.see(tree_item)
        self.on_tree_select(None)

    def deselect_all(self):
        """取消选择"""
        self.tree.selection_set()
        self._selected_node_ids.clear()

    def add_child_to_selected(self):
        """添加子节点"""
        if len(self._selected_node_ids) == 1:
            parent_id = list(self._selected_node_ids)[0]
            self._add_child_node(parent_id)
        elif not self._selected_node_ids and self.root_node:
            self._add_child_node(self.root_node.get("uid"))

    def add_sibling_to_selected(self):
        """添加同级节点"""
        if len(self._selected_node_ids) != 1:
            return

        selected_id = list(self._selected_node_ids)[0]
        selected_node = self.node_items.get(selected_id, {}).get("node")
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
                    self.after(50, lambda: self._select_and_start_edit(new_node_id))

    def _add_child_node(self, parent_id):
        """添加子节点"""
        parent_node = self.node_items.get(parent_id, {}).get("node")
        if not parent_node:
            return

        new_node = {"name": "新节点", "content": "", "children": []}
        command = AddNodeCommand(self.project_manager, parent_id, new_node, "添加子节点")
        if self.command_executor(command):
            parent_node["_collapsed"] = False
            self.refresh()
            new_node_id = command.added_node_uid
            if new_node_id:
                self.after(50, lambda: self._select_and_start_edit(new_node_id))

    def _select_and_start_edit(self, node_id):
        """选中并开始编辑"""
        self.select_node(node_id)
        tree_item = self.node_to_tree_item.get(node_id)
        if tree_item:
            self._start_tree_edit(tree_item)

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

    def expand_selected(self):
        """展开选中节点"""
        for node_id in self._selected_node_ids:
            node = self.node_items.get(node_id, {}).get("node")
            tree_item = self.node_to_tree_item.get(node_id)
            if node and tree_item:
                node["_collapsed"] = False
                self.tree.item(tree_item, open=True)

    def collapse_selected(self):
        """折叠选中节点"""
        for node_id in self._selected_node_ids:
            node = self.node_items.get(node_id, {}).get("node")
            tree_item = self.node_to_tree_item.get(node_id)
            if node and tree_item:
                node["_collapsed"] = True
                self.tree.item(tree_item, open=False)

    def edit_selected_node(self):
        """编辑选中节点"""
        if len(self._selected_node_ids) == 1:
            node_id = list(self._selected_node_ids)[0]
            tree_item = self.node_to_tree_item.get(node_id)
            if tree_item:
                self._start_tree_edit(tree_item)

    # ==================== 主题和显示 ====================

    def apply_theme(self, theme_manager):
        """应用主题"""
        self.current_theme_manager = theme_manager

        # 更新Treeview样式
        style = ttk.Style()
        bg_primary = theme_manager.get_color("bg_primary")
        fg_primary = theme_manager.get_color("fg_primary")
        select_bg = theme_manager.get_color("editor_select_bg")
        
        style.configure("Treeview",
                      background=bg_primary,
                      foreground=fg_primary,
                      fieldbackground=bg_primary)
        style.map("Treeview", background=[("selected", select_bg)])

        # Update tags using ThemeManager keys
        self.tree.tag_configure("level_0", background=theme_manager.get_color("table_level_0_bg"))
        self.tree.tag_configure("level_1", background=theme_manager.get_color("table_level_1_bg"))
        self.tree.tag_configure("level_2", background=theme_manager.get_color("table_level_2_bg"))
        self.tree.tag_configure("level_3", background=theme_manager.get_color("table_level_3_bg"))
        self.tree.tag_configure("level_4", background=theme_manager.get_color("table_level_4_bg"))
        self.tree.tag_configure("level_5", background=theme_manager.get_color("table_level_5_bg"))
        self.tree.tag_configure("has_content", foreground=theme_manager.get_color("table_has_content_fg"))
        self.tree.tag_configure("status_draft", foreground=theme_manager.get_color("table_status_draft_fg"))
        self.tree.tag_configure("status_final", foreground=theme_manager.get_color("table_status_final_fg"))

    def destroy(self):
        """销毁视图"""
        if hasattr(self, 'tree_frame'):
            self.tree_frame.destroy()
        super().destroy()
