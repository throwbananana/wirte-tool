import tkinter as tk
from tkinter import ttk, messagebox
from writer_app.ui.outline_views.base_view import BaseOutlineView
from writer_app.core.commands import EditSceneCommand
from writer_app.core.event_bus import get_event_bus, Events
import logging

logger = logging.getLogger(__name__)


class GridView(BaseOutlineView):
    """
    Spreadsheet-like Grid View for Scenes.

    Features:
    - 显示场景的表格视图，支持多列排序
    - 双击单元格可编辑
    - 支持多选和批量操作
    - 与 EventBus 集成实现实时更新
    """

    # 排序状态
    SORT_NONE = 0
    SORT_ASC = 1
    SORT_DESC = 2

    def __init__(self, parent, project_manager, command_executor,
                 on_node_select=None, on_ai_suggest_branch=None,
                 on_generate_scene=None, on_set_tags=None,
                 on_jump_to_scene=None, **kwargs):
        super().__init__(parent, project_manager, command_executor,
                        on_node_select, on_ai_suggest_branch,
                        on_generate_scene, on_set_tags,
                        on_jump_to_scene, **kwargs)

        # 排序状态
        self._sort_column = None
        self._sort_order = self.SORT_NONE

        # 选中状态
        self._selected_scene_indices = set()

        # 订阅事件
        self._subscribe_events()
        
        # We use the Canvas (self) as the container
        self.tree_frame = ttk.Frame(self)
        
        columns = ("name", "location", "time", "tension", "characters", "status")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", selectmode="extended")
        
        # Headers
        headers = {
            "name": "场景名称",
            "location": "地点",
            "time": "时间",
            "tension": "张力(0-100)",
            "characters": "角色",
            "status": "状态"
        }
        
        for col, text in headers.items():
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=100)
            
        self.tree.column("name", width=200)
        self.tree.column("characters", width=200)
        
        # Scrollbars
        ysb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Embed frame in canvas
        self.window_id = self.create_window(0, 0, window=self.tree_frame, anchor="nw")
        
        # Resize handler
        self.bind("<Configure>", self.on_resize)
        
        self.tree.bind("<Double-1>", self.on_double_click)
        
        self.map_id_to_scene_idx = {}

    def on_resize(self, event):
        # Resize the embedded window to match canvas size
        self.itemconfigure(self.window_id, width=event.width, height=event.height)

    def apply_theme(self, theme_manager):
        """Apply theme to Treeview"""
        super().apply_theme(theme_manager)
        
        style = ttk.Style()
        if theme_manager.current_theme == "Dark":
            style.configure("Treeview", 
                          background="#2D2D2D", 
                          foreground="#FFFFFF", 
                          fieldbackground="#2D2D2D")
            style.map("Treeview", background=[("selected", "#0D47A1")])
            style.configure("Treeview.Heading", background="#333333", foreground="#FFFFFF")
        else:
            style.configure("Treeview", 
                          background="#FFFFFF", 
                          foreground="#000000", 
                          fieldbackground="#FFFFFF")
            style.map("Treeview", background=[("selected", "#2196F3")])
            style.configure("Treeview.Heading", background="#F0F0F0", foreground="#000000")

    def refresh(self):
        # Clear
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.map_id_to_scene_idx.clear()
        
        scenes = self.project_manager.get_scenes()
        if not scenes: return
        
        for i, scene in enumerate(scenes):
            vals = (
                scene.get("name", ""),
                scene.get("location", ""),
                scene.get("time", ""),
                scene.get("tension", 0),
                ", ".join(scene.get("characters", [])),
                scene.get("status", "初稿")
            )
            item_id = self.tree.insert("", "end", values=vals)
            self.map_id_to_scene_idx[item_id] = i

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x) # Returns #1, #2...
        
        if not item_id or not col: return
        
        col_idx = int(col.replace("#", "")) - 1
        cols = ["name", "location", "time", "tension", "characters", "status"]
        if 0 <= col_idx < len(cols):
            field = cols[col_idx]
            scene_idx = self.map_id_to_scene_idx.get(item_id)
            if scene_idx is not None:
                self._edit_cell(item_id, field, scene_idx)

    def _edit_cell(self, item_id, field, scene_idx):
        # Simple popup entry for editing
        x, y, w, h = self.tree.bbox(item_id, column=field)
        
        # Create Entry
        entry = tk.Entry(self.tree)
        # Get current value
        curr_val = self.tree.item(item_id, "values")[["name", "location", "time", "tension", "characters", "status"].index(field)]
        entry.insert(0, curr_val)
        entry.select_range(0, tk.END)
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        
        self._editing = True

        def save(e=None):
            if not self._editing: return
            self._editing = False
            
            try:
                new_val = entry.get()
                entry.destroy()
            except tk.TclError:
                return # Already destroyed
            
            # Update Data
            scenes = self.project_manager.get_scenes()
            if 0 <= scene_idx < len(scenes):
                scene = scenes[scene_idx]
                
                # Special handling
                if field == "tension":
                    try:
                        new_val = int(new_val)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"无效的张力值: {new_val}, 错误: {e}")
                        messagebox.showwarning("输入错误", "张力值必须是 0-100 之间的整数")
                        return
                elif field == "characters":
                    new_val = [c.strip() for c in new_val.split(",") if c.strip()]
                
                if scene.get(field) != new_val:
                    new_data = dict(scene)
                    new_data[field] = new_val
                    cmd = EditSceneCommand(self.project_manager, scene_idx, scene, new_data, f"Grid Edit {field}")
                    self.command_executor(cmd)
                    self.refresh()
        
        def cancel(e=None):
            if self._editing:
                self._editing = False
                try:
                    entry.destroy()
                except tk.TclError:
                    pass  # Entry widget 已被销毁

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", lambda e: save() if self._editing else None) # Auto-save on blur
        entry.bind("<Escape>", cancel)

    def sort_by(self, col):
        """
        按列排序场景数据。

        Args:
            col: 列名 (name, location, time, tension, characters, status)
        """
        # 切换排序顺序
        if self._sort_column == col:
            # 循环: 无 -> 升序 -> 降序 -> 无
            self._sort_order = (self._sort_order + 1) % 3
        else:
            self._sort_column = col
            self._sort_order = self.SORT_ASC

        # 如果是无排序，直接刷新
        if self._sort_order == self.SORT_NONE:
            self._sort_column = None
            self._update_column_headers()
            self.refresh()
            return

        # 获取所有项目
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children()]

        # 特殊处理数值列
        if col == "tension":
            try:
                items.sort(key=lambda x: int(x[0]) if x[0] else 0,
                           reverse=(self._sort_order == self.SORT_DESC))
            except ValueError:
                items.sort(key=lambda x: x[0], reverse=(self._sort_order == self.SORT_DESC))
        else:
            items.sort(key=lambda x: x[0].lower() if x[0] else "",
                       reverse=(self._sort_order == self.SORT_DESC))

        # 重新排列
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)

        self._update_column_headers()

    def _update_column_headers(self):
        """更新列标题显示排序指示器"""
        headers = {
            "name": "场景名称",
            "location": "地点",
            "time": "时间",
            "tension": "张力(0-100)",
            "characters": "角色",
            "status": "状态"
        }

        for col, text in headers.items():
            if col == self._sort_column:
                if self._sort_order == self.SORT_ASC:
                    indicator = " ▲"
                elif self._sort_order == self.SORT_DESC:
                    indicator = " ▼"
                else:
                    indicator = ""
                self.tree.heading(col, text=text + indicator)
            else:
                self.tree.heading(col, text=text)

    def _subscribe_events(self):
        """订阅 EventBus 事件"""
        bus = get_event_bus()
        bus.subscribe(Events.SCENE_ADDED, self._on_scene_event)
        bus.subscribe(Events.SCENE_UPDATED, self._on_scene_event)
        bus.subscribe(Events.SCENE_DELETED, self._on_scene_event)
        bus.subscribe(Events.SCENE_MOVED, self._on_scene_event)

    def _on_scene_event(self, event_type, **kwargs):
        """处理场景相关事件"""
        try:
            self.after(10, self.refresh)
        except tk.TclError:
            pass  # Widget 已销毁

    def select_node(self, node_id, add=False):
        """选中指定的场景（通过 outline_ref_id 关联）"""
        if not add:
            self._selected_scene_indices.clear()
            self.tree.selection_remove(self.tree.selection())

        # 根据 node_id 找到关联的场景
        scenes = self.project_manager.get_scenes()
        for idx, scene in enumerate(scenes):
            if scene.get("outline_ref_id") == node_id:
                for item_id, scene_idx in self.map_id_to_scene_idx.items():
                    if scene_idx == idx:
                        self.tree.selection_add(item_id)
                        self._selected_scene_indices.add(idx)
                        self.tree.see(item_id)
                        break

    def deselect_all(self):
        """取消所有选中"""
        self._selected_scene_indices.clear()
        self.tree.selection_remove(self.tree.selection())

    def get_selected_scenes(self):
        """获取选中的场景索引列表"""
        return list(self._selected_scene_indices)

    # Abstract implementations - GridView 使用 Treeview，不需要画布布局
    def _calculate_layout(self, node, *args, **kwargs):
        """GridView 使用 Treeview 组件，不需要手动计算布局"""
        # 返回空字典表示不使用画布布局
        return {}

    def _draw_connections(self, node, positions):
        """GridView 使用 Treeview 组件，不需要绘制连线"""
        # 表格视图没有连线
        pass

    def _draw_nodes(self, node, positions, level=0):
        """GridView 使用 Treeview 组件，节点通过 refresh() 方法填充"""
        # 表格行在 refresh() 中创建
        pass

    def destroy(self):
        """清理资源"""
        # 取消事件订阅
        try:
            bus = get_event_bus()
            bus.unsubscribe(Events.SCENE_ADDED, self._on_scene_event)
            bus.unsubscribe(Events.SCENE_UPDATED, self._on_scene_event)
            bus.unsubscribe(Events.SCENE_DELETED, self._on_scene_event)
            bus.unsubscribe(Events.SCENE_MOVED, self._on_scene_event)
        except Exception as e:
            logger.warning(f"取消事件订阅时出错: {e}")

        self.tree_frame.destroy()
        super().destroy()
