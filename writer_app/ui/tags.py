import tkinter as tk
from tkinter import ttk, colorchooser, simpledialog, messagebox
from writer_app.core.commands import Command
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.core.icon_manager import IconManager
import json

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

def get_icon_font(size=12):
    return IconManager().get_font(size=size)


# --- Tag Commands ---


class AddTagDefinitionCommand(Command):
    """添加标签定义命令"""

    def __init__(self, project_manager, tag_name, color):
        super().__init__("定义标签")
        self.project_manager = project_manager
        self.tag_name = tag_name
        self.color = color

    def execute(self):
        tags = self.project_manager.get_tags_config()
        # Check duplicate
        for t in tags:
            if t["name"] == self.tag_name:
                return False
        tags.append({"name": self.tag_name, "color": self.color})
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.TAGS_UPDATED, tag_name=self.tag_name)
        return True

    def undo(self):
        tags = self.project_manager.get_tags_config()
        for i, t in enumerate(tags):
            if t["name"] == self.tag_name:
                del tags[i]
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.TAGS_UPDATED, tag_name=self.tag_name)
                return True
        return False


class DeleteTagDefinitionCommand(Command):
    """删除标签定义命令 - 支持撤销"""

    def __init__(self, project_manager, tag_name):
        super().__init__("删除标签")
        self.project_manager = project_manager
        self.tag_name = tag_name
        self.deleted_tag = None
        self.deleted_index = -1
        self.nodes_with_tag = []  # 记录使用此标签的节点，用于撤销时恢复

    def execute(self):
        tags = self.project_manager.get_tags_config()
        for i, t in enumerate(tags):
            if t["name"] == self.tag_name:
                self.deleted_tag = t.copy()
                self.deleted_index = i
                del tags[i]
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.TAGS_UPDATED, tag_name=self.tag_name)
                return True
        return False

    def undo(self):
        if self.deleted_tag is None:
            return False
        tags = self.project_manager.get_tags_config()
        # 恢复到原位置
        if 0 <= self.deleted_index <= len(tags):
            tags.insert(self.deleted_index, self.deleted_tag)
        else:
            tags.append(self.deleted_tag)
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.TAGS_UPDATED, tag_name=self.tag_name)
        return True


class RenameTagCommand(Command):
    """重命名标签命令"""

    def __init__(self, project_manager, old_name, new_name):
        super().__init__("重命名标签")
        self.project_manager = project_manager
        self.old_name = old_name
        self.new_name = new_name

    def execute(self):
        tags = self.project_manager.get_tags_config()
        # 检查新名称是否已存在
        for t in tags:
            if t["name"] == self.new_name:
                return False

        # 重命名标签定义
        for t in tags:
            if t["name"] == self.old_name:
                t["name"] = self.new_name
                break
        else:
            return False

        # 更新所有使用此标签的节点
        self._update_tag_references(self.old_name, self.new_name)
        self.project_manager.mark_modified()
        get_event_bus().publish(
            Events.TAGS_UPDATED,
            old_name=self.old_name,
            new_name=self.new_name
        )
        return True

    def undo(self):
        tags = self.project_manager.get_tags_config()
        for t in tags:
            if t["name"] == self.new_name:
                t["name"] = self.old_name
                break
        else:
            return False

        self._update_tag_references(self.new_name, self.old_name)
        self.project_manager.mark_modified()
        get_event_bus().publish(
            Events.TAGS_UPDATED,
            old_name=self.new_name,
            new_name=self.old_name
        )
        return True

    def _update_tag_references(self, from_name, to_name):
        """更新所有节点中的标签引用"""
        # 更新大纲节点
        outline = self.project_manager.get_outline()
        self._update_node_tags_recursive(outline, from_name, to_name)

        # 更新场景
        for scene in self.project_manager.get_scenes():
            if from_name in scene.get("tags", []):
                scene["tags"] = [to_name if t == from_name else t for t in scene["tags"]]

        # 更新角色
        for char in self.project_manager.get_characters():
            if from_name in char.get("tags", []):
                char["tags"] = [to_name if t == from_name else t for t in char["tags"]]

    def _update_node_tags_recursive(self, node, from_name, to_name):
        if from_name in node.get("tags", []):
            node["tags"] = [to_name if t == from_name else t for t in node["tags"]]
        for child in node.get("children", []):
            self._update_node_tags_recursive(child, from_name, to_name)


class EditTagColorCommand(Command):
    """修改标签颜色命令"""

    def __init__(self, project_manager, tag_name, new_color):
        super().__init__("修改标签颜色")
        self.project_manager = project_manager
        self.tag_name = tag_name
        self.new_color = new_color
        self.old_color = None

    def execute(self):
        tags = self.project_manager.get_tags_config()
        for t in tags:
            if t["name"] == self.tag_name:
                self.old_color = t["color"]
                t["color"] = self.new_color
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.TAGS_UPDATED, tag_name=self.tag_name)
                return True
        return False

    def undo(self):
        if self.old_color is None:
            return False
        tags = self.project_manager.get_tags_config()
        for t in tags:
            if t["name"] == self.tag_name:
                t["color"] = self.old_color
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.TAGS_UPDATED, tag_name=self.tag_name)
                return True
        return False


class SetNodeTagsCommand(Command):
    def __init__(self, project_manager, node, new_tags):
        super().__init__("设置节点标签")
        self.project_manager = project_manager
        self.node = node
        self.new_tags = list(new_tags)
        self.old_tags = list(node.get("tags", []))

    def execute(self):
        self.node["tags"] = self.new_tags
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.TAGS_UPDATED)
        return True

    def undo(self):
        self.node["tags"] = self.old_tags
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.TAGS_UPDATED)
        return True


# --- UI ---


class TagManagerDialog(tk.Toplevel):
    """标签管理对话框 - 支持添加、删除、重命名、修改颜色"""

    def __init__(self, parent, project_manager, command_executor):
        super().__init__(parent)
        self.title("标签管理")
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.geometry("400x450")
        self.minsize(300, 350)

        self.transient(parent)
        self.grab_set()

        self.setup_ui()
        self.refresh_list()

        self.bind("<Escape>", lambda e: self.destroy())

    def setup_ui(self):
        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text=f"{get_icon('add', '➕')} 新建", command=self.add_tag, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text=f"{get_icon('edit', '✏️')} 重命名", command=self.rename_tag, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text=f"{get_icon('color', '🎨')} 颜色", command=self.change_color, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text=f"{get_icon('delete', '🗑️')} 删除", command=self.delete_tag, width=8).pack(side=tk.LEFT, padx=2)


        # 标签列表
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 使用 Treeview 以便更好地展示
        columns = ("name", "color", "usage")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("name", text="标签名称")
        self.tree.heading("color", text="颜色")
        self.tree.heading("usage", text="使用次数")

        self.tree.column("name", width=150, minwidth=100)
        self.tree.column("color", width=80, minwidth=60, anchor="center")
        self.tree.column("usage", width=80, minwidth=60, anchor="center")

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击编辑颜色
        self.tree.bind("<Double-1>", lambda e: self.change_color())

        # 统计信息
        self.stats_label = ttk.Label(self, text="")
        self.stats_label.pack(fill=tk.X, padx=5, pady=5)

        # 关闭按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT)

    def refresh_list(self):
        """刷新标签列表"""
        self.tree.delete(*self.tree.get_children())

        tags = self.project_manager.get_tags_config()
        usage_counts = self._count_tag_usage()

        for t in tags:
            name = t["name"]
            color = t["color"]
            usage = usage_counts.get(name, 0)

            item_id = self.tree.insert("", tk.END, values=(name, color, usage))
            # 设置标签颜色作为背景 (需要配置 tag)
            self.tree.tag_configure(name, background=color)
            self.tree.item(item_id, tags=(name,))

        total = len(tags)
        self.stats_label.config(text=f"共 {total} 个标签")

    def _count_tag_usage(self):
        """统计每个标签的使用次数"""
        usage = {}

        # 统计大纲节点
        outline = self.project_manager.get_outline()
        self._count_node_tags(outline, usage)

        # 统计场景
        for scene in self.project_manager.get_scenes():
            for tag in scene.get("tags", []):
                usage[tag] = usage.get(tag, 0) + 1

        # 统计角色
        for char in self.project_manager.get_characters():
            for tag in char.get("tags", []):
                usage[tag] = usage.get(tag, 0) + 1

        return usage

    def _count_node_tags(self, node, usage):
        for tag in node.get("tags", []):
            usage[tag] = usage.get(tag, 0) + 1
        for child in node.get("children", []):
            self._count_node_tags(child, usage)

    def _get_selected_tag(self):
        """获取选中的标签名称"""
        selection = self.tree.selection()
        if not selection:
            return None
        item = self.tree.item(selection[0])
        return item["values"][0] if item["values"] else None

    def add_tag(self):
        """添加新标签"""
        name = simpledialog.askstring("新建标签", "标签名称:", parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return

        # 检查重复
        for t in self.project_manager.get_tags_config():
            if t["name"] == name:
                messagebox.showwarning("重复", f"标签 '{name}' 已存在", parent=self)
                return

        color = colorchooser.askcolor(title="选择颜色", parent=self)[1]
        if not color:
            color = "#CCCCCC"

        cmd = AddTagDefinitionCommand(self.project_manager, name, color)
        if self.command_executor(cmd):
            self.refresh_list()

    def delete_tag(self):
        """删除标签"""
        tag_name = self._get_selected_tag()
        if not tag_name:
            messagebox.showinfo("提示", "请先选择一个标签", parent=self)
            return

        # 检查使用情况
        usage = self._count_tag_usage().get(tag_name, 0)
        warning = ""
        if usage > 0:
            warning = f"\n\n⚠️ 该标签正在被 {usage} 个项目使用！"

        if not messagebox.askyesno("确认删除",
                                    f"确定要删除标签 '{tag_name}' 吗？{warning}\n\n删除后可通过撤销恢复。",
                                    parent=self):
            return

        cmd = DeleteTagDefinitionCommand(self.project_manager, tag_name)
        if self.command_executor(cmd):
            self.refresh_list()

    def rename_tag(self):
        """重命名标签"""
        tag_name = self._get_selected_tag()
        if not tag_name:
            messagebox.showinfo("提示", "请先选择一个标签", parent=self)
            return

        new_name = simpledialog.askstring("重命名标签",
                                           f"将 '{tag_name}' 重命名为:",
                                           initialvalue=tag_name,
                                           parent=self)
        if not new_name or new_name == tag_name:
            return
        new_name = new_name.strip()
        if not new_name:
            return

        cmd = RenameTagCommand(self.project_manager, tag_name, new_name)
        if self.command_executor(cmd):
            self.refresh_list()
        else:
            messagebox.showwarning("错误", f"重命名失败，标签 '{new_name}' 可能已存在", parent=self)

    def change_color(self):
        """修改标签颜色"""
        tag_name = self._get_selected_tag()
        if not tag_name:
            messagebox.showinfo("提示", "请先选择一个标签", parent=self)
            return

        # 获取当前颜色
        current_color = "#CCCCCC"
        for t in self.project_manager.get_tags_config():
            if t["name"] == tag_name:
                current_color = t["color"]
                break

        new_color = colorchooser.askcolor(initialcolor=current_color,
                                           title=f"选择 '{tag_name}' 的颜色",
                                           parent=self)[1]
        if not new_color or new_color == current_color:
            return

        cmd = EditTagColorCommand(self.project_manager, tag_name, new_color)
        if self.command_executor(cmd):
            self.refresh_list()


class TagSelectorDialog(tk.Toplevel):
    """标签选择对话框 - 用于为节点选择标签"""

    def __init__(self, parent, project_manager, current_tags):
        super().__init__(parent)
        self.title("选择标签")
        self.project_manager = project_manager
        self.selected_tags = set(current_tags)
        self.result = None
        self.geometry("300x400")
        self.minsize(250, 300)
        self.transient(parent)
        self.grab_set()

        self.setup_ui()
        self.wait_window()

    def setup_ui(self):
        # 搜索框
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(search_frame, text=get_icon("search", "🔍"), font=get_icon_font(10)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)


        # 标签列表
        self.vars = {}
        self.checkbuttons = {}

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 使用 Canvas + Frame 实现滚动
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮支持
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._populate_tags()

        # 快捷操作
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(action_frame, text="全选", command=self._select_all, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="全不选", command=self._deselect_all, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="反选", command=self._toggle_all, width=6).pack(side=tk.LEFT, padx=2)

        # 按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="确定", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT)

    def _populate_tags(self):
        """填充标签列表"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.vars.clear()
        self.checkbuttons.clear()

        for t in self.project_manager.get_tags_config():
            name = t["name"]
            var = tk.BooleanVar(value=name in self.selected_tags)
            self.vars[name] = var

            cb_frame = ttk.Frame(self.scrollable_frame)
            cb_frame.pack(fill=tk.X, pady=2)

            # 颜色指示器
            color_label = tk.Label(cb_frame, text=get_icon("circle_filled", "●"), fg=t["color"], font=get_icon_font(10))
            color_label.pack(side=tk.LEFT, padx=(0, 5))


            cb = ttk.Checkbutton(cb_frame, text=name, variable=var)
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.checkbuttons[name] = (cb_frame, cb)

    def _on_search(self, *args):
        """搜索过滤"""
        query = self.search_var.get().lower()

        for name, (frame, cb) in self.checkbuttons.items():
            if query in name.lower():
                frame.pack(fill=tk.X, pady=2)
            else:
                frame.pack_forget()

    def _select_all(self):
        for var in self.vars.values():
            var.set(True)

    def _deselect_all(self):
        for var in self.vars.values():
            var.set(False)

    def _toggle_all(self):
        for var in self.vars.values():
            var.set(not var.get())

    def on_ok(self):
        self.result = [name for name, var in self.vars.items() if var.get()]
        self.destroy()
