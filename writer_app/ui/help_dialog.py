# -*- coding: utf-8 -*-
"""
帮助对话框模块
提供使用说明、快捷键速查、关于信息等帮助界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import webbrowser

from writer_app.core.help_manager import get_help_manager, HelpTopic
from writer_app.core.icon_manager import IconManager


def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)


def get_icon_font(size=12):
    return IconManager().get_font(size=size)


class HelpDialog(tk.Toplevel):
    """帮助对话框 - 提供完整的使用说明"""

    def __init__(self, parent, initial_topic: Optional[str] = None):
        super().__init__(parent)
        self.title("使用说明 - 写作助手")
        self.geometry("900x650")
        self.minsize(700, 500)

        self.help_manager = get_help_manager()
        self.current_topic: Optional[HelpTopic] = None

        self.transient(parent)

        self.setup_ui()
        self.load_topics()

        # 加载初始主题
        if initial_topic:
            self.select_topic(initial_topic)
        else:
            self.select_topic("getting_started")

        # 居中显示
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def setup_ui(self):
        """设置界面"""
        # 主框架
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部搜索栏
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(search_frame, text="清除", command=self._clear_search, width=8).pack(side=tk.LEFT, padx=(5, 0))

        # 分割面板
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 左侧主题列表
        left_frame = ttk.Frame(paned, width=200)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="帮助主题", font=("", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        # 主题列表
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.topic_listbox = tk.Listbox(
            list_frame,
            font=("Microsoft YaHei", 10),
            selectbackground="#0078D4",
            selectforeground="white",
            activestyle="none"
        )
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.topic_listbox.yview)
        self.topic_listbox.configure(yscrollcommand=scrollbar.set)

        self.topic_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.topic_listbox.bind("<<ListboxSelect>>", self._on_topic_selected)

        # 右侧内容区域
        right_frame = ttk.Frame(paned, width=600)
        paned.add(right_frame, weight=3)

        # 标题
        self.title_label = ttk.Label(right_frame, text="", font=("Microsoft YaHei", 14, "bold"))
        self.title_label.pack(anchor=tk.W, pady=(0, 10))

        # 内容文本
        content_frame = ttk.Frame(right_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        self.content_text = tk.Text(
            content_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10),
            padx=10,
            pady=10,
            state=tk.DISABLED,
            cursor="arrow"
        )
        content_scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=content_scrollbar.set)

        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 配置文本样式
        self._configure_text_tags()

        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="快捷键速查", command=self._show_shortcuts).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="关于", command=self._show_about).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT)

    def _configure_text_tags(self):
        """配置文本样式标签"""
        self.content_text.tag_configure("h1", font=("Microsoft YaHei", 16, "bold"), spacing1=10, spacing3=5)
        self.content_text.tag_configure("h2", font=("Microsoft YaHei", 14, "bold"), spacing1=8, spacing3=4)
        self.content_text.tag_configure("h3", font=("Microsoft YaHei", 12, "bold"), spacing1=6, spacing3=3)
        self.content_text.tag_configure("bold", font=("Microsoft YaHei", 10, "bold"))
        self.content_text.tag_configure("italic", font=("Microsoft YaHei", 10, "italic"))
        self.content_text.tag_configure("code", font=("Consolas", 10), background="#f0f0f0")
        self.content_text.tag_configure("bullet", lmargin1=20, lmargin2=35)
        self.content_text.tag_configure("table_header", font=("Microsoft YaHei", 10, "bold"), background="#e0e0e0")

    def load_topics(self):
        """加载主题列表"""
        self.topic_listbox.delete(0, tk.END)
        self._topic_ids = []

        topics = self.help_manager.get_all_topics()
        for topic in topics:
            self.topic_listbox.insert(tk.END, f"  {topic.title}")
            self._topic_ids.append(topic.id)

    def select_topic(self, topic_id: str):
        """选择并显示主题"""
        topic = self.help_manager.get_topic(topic_id)
        if not topic:
            return

        self.current_topic = topic
        self.title_label.configure(text=topic.title)

        # 更新列表选中状态
        if topic_id in self._topic_ids:
            idx = self._topic_ids.index(topic_id)
            self.topic_listbox.selection_clear(0, tk.END)
            self.topic_listbox.selection_set(idx)
            self.topic_listbox.see(idx)

        # 渲染内容
        self._render_content(topic.content)

    def _render_content(self, content: str):
        """渲染 Markdown 风格内容"""
        self.content_text.configure(state=tk.NORMAL)
        self.content_text.delete("1.0", tk.END)

        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()

            # 标题
            if stripped.startswith("### "):
                self.content_text.insert(tk.END, stripped[4:] + "\n", "h3")
            elif stripped.startswith("## "):
                self.content_text.insert(tk.END, stripped[3:] + "\n", "h2")
            elif stripped.startswith("# "):
                self.content_text.insert(tk.END, stripped[2:] + "\n", "h1")
            # 列表项
            elif stripped.startswith("- "):
                self._render_inline(stripped[2:], prefix="  - ", tags=("bullet",))
            elif stripped.startswith("* "):
                self._render_inline(stripped[2:], prefix="  - ", tags=("bullet",))
            # 表格行
            elif stripped.startswith("|") and stripped.endswith("|"):
                self._render_table_row(stripped)
            # 普通段落
            else:
                self._render_inline(line)

        self.content_text.configure(state=tk.DISABLED)

    def _render_inline(self, text: str, prefix: str = "", tags: tuple = ()):
        """渲染行内格式"""
        if prefix:
            self.content_text.insert(tk.END, prefix)

        # 简单的加粗处理 **text**
        import re
        parts = re.split(r'(\*\*[^*]+\*\*)', text)

        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                self.content_text.insert(tk.END, part[2:-2], tags + ("bold",))
            else:
                if tags:
                    self.content_text.insert(tk.END, part, tags)
                else:
                    self.content_text.insert(tk.END, part)

        self.content_text.insert(tk.END, "\n")

    def _render_table_row(self, row: str):
        """渲染表格行"""
        # 跳过分隔行
        if "---" in row:
            return

        cells = [c.strip() for c in row.split("|")[1:-1]]
        line = "  " + "  |  ".join(cells) + "\n"

        # 判断是否是表头（简单判断：第一行通常是表头）
        self.content_text.insert(tk.END, line)

    def _on_topic_selected(self, event):
        """主题选择事件"""
        selection = self.topic_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self._topic_ids):
                self.select_topic(self._topic_ids[idx])

    def _on_search_changed(self, *args):
        """搜索内容改变"""
        query = self.search_var.get().strip()
        if not query:
            self.load_topics()
            return

        results = self.help_manager.search_topics(query)
        self.topic_listbox.delete(0, tk.END)
        self._topic_ids = []

        for topic in results:
            self.topic_listbox.insert(tk.END, f"  {topic.title}")
            self._topic_ids.append(topic.id)

        if results:
            self.topic_listbox.selection_set(0)
            self.select_topic(results[0].id)

    def _clear_search(self):
        """清除搜索"""
        self.search_var.set("")
        self.load_topics()

    def _show_shortcuts(self):
        """显示快捷键速查"""
        ShortcutsDialog(self)

    def _show_about(self):
        """显示关于对话框"""
        AboutDialog(self)


class ShortcutsDialog(tk.Toplevel):
    """快捷键速查对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("快捷键速查")
        self.geometry("500x550")
        self.minsize(400, 400)

        self.help_manager = get_help_manager()

        self.transient(parent)
        self.grab_set()

        self.setup_ui()

        # 居中显示
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def setup_ui(self):
        """设置界面"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="快捷键速查", font=("Microsoft YaHei", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # 分类选择
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="分类:").pack(side=tk.LEFT)
        self.category_var = tk.StringVar(value="全部")
        categories = ["全部"] + self.help_manager.get_shortcut_categories()
        category_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.category_var,
            values=categories,
            state="readonly",
            width=15
        )
        category_combo.pack(side=tk.LEFT, padx=(5, 0))
        category_combo.bind("<<ComboboxSelected>>", self._on_category_changed)

        # 快捷键列表
        columns = ("key", "description")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=20)

        self.tree.heading("key", text="快捷键")
        self.tree.heading("description", text="功能说明")

        self.tree.column("key", width=120, anchor=tk.CENTER)
        self.tree.column("description", width=300)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=15, pady=10)

        ttk.Button(btn_frame, text="复制全部", command=self._copy_all).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT)

        self._load_shortcuts()

    def _load_shortcuts(self, category: Optional[str] = None):
        """加载快捷键"""
        self.tree.delete(*self.tree.get_children())

        if category and category != "全部":
            shortcuts = self.help_manager.get_shortcuts(category)
        else:
            shortcuts = self.help_manager.get_shortcuts()

        current_category = ""
        for shortcut in shortcuts:
            # 添加分类标题
            if shortcut.category != current_category:
                current_category = shortcut.category
                self.tree.insert("", tk.END, values=(f"【{current_category}】", ""), tags=("category",))

            self.tree.insert("", tk.END, values=(shortcut.key, shortcut.description))

        self.tree.tag_configure("category", background="#f0f0f0", font=("", 9, "bold"))

    def _on_category_changed(self, event):
        """分类改变"""
        category = self.category_var.get()
        self._load_shortcuts(None if category == "全部" else category)

    def _copy_all(self):
        """复制全部快捷键"""
        text = self.help_manager.format_shortcuts_text()
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("提示", "已复制到剪贴板", parent=self)


class AboutDialog(tk.Toplevel):
    """关于对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("关于 - 写作助手")
        self.geometry("450x520")
        self.resizable(False, False)

        self.help_manager = get_help_manager()
        self.app_info = self.help_manager.get_app_info()

        self.transient(parent)
        self.grab_set()

        self.setup_ui()

        # 居中显示
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def setup_ui(self):
        """设置界面"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 应用图标和名称
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        # 图标
        icon_label = tk.Label(header_frame, text="", font=("Segoe UI Emoji", 48))
        icon_label.pack(side=tk.LEFT, padx=(0, 15))

        # 名称和版本
        name_frame = ttk.Frame(header_frame)
        name_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(
            name_frame,
            text=self.app_info["name"],
            font=("Microsoft YaHei", 18, "bold")
        ).pack(anchor=tk.W)

        ttk.Label(
            name_frame,
            text=f"版本 {self.app_info['version']}",
            font=("", 11),
            foreground="#666"
        ).pack(anchor=tk.W)

        # 分隔线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # 描述
        ttk.Label(
            main_frame,
            text=self.app_info["description"],
            wraplength=400,
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 15))

        # 主要功能
        features_frame = ttk.LabelFrame(main_frame, text="主要功能", padding=10)
        features_frame.pack(fill=tk.X, pady=(0, 10))

        features_text = "  ".join([f"{get_icon('checkmark', '')} {f}" for f in self.app_info["features"][:4]])
        ttk.Label(features_frame, text=features_text, wraplength=380).pack(anchor=tk.W)

        features_text2 = "  ".join([f"{get_icon('checkmark', '')} {f}" for f in self.app_info["features"][4:]])
        ttk.Label(features_frame, text=features_text2, wraplength=380).pack(anchor=tk.W, pady=(5, 0))

        # 技术信息
        tech_frame = ttk.LabelFrame(main_frame, text="技术信息", padding=10)
        tech_frame.pack(fill=tk.X, pady=(0, 10))

        for tech in self.app_info["tech_stack"]:
            ttk.Label(tech_frame, text=f"  {tech}").pack(anchor=tk.W)

        # 版权信息
        copyright_frame = ttk.Frame(main_frame)
        copyright_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(
            copyright_frame,
            text=self.app_info["copyright"],
            font=("", 9),
            foreground="#888"
        ).pack(anchor=tk.CENTER)

        ttk.Label(
            copyright_frame,
            text=self.app_info["license"],
            font=("", 9),
            foreground="#888"
        ).pack(anchor=tk.CENTER)

        # 底部按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=20, pady=15)

        ttk.Button(btn_frame, text="关闭", command=self.destroy, width=10).pack(side=tk.RIGHT)


class ContextHelpTooltip:
    """上下文帮助提示"""

    def __init__(self, widget, context: str, help_manager=None):
        self.widget = widget
        self.context = context
        self.help_manager = help_manager or get_help_manager()
        self.tooltip_window = None

        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event):
        """鼠标进入"""
        help_text = self.help_manager.get_context_help(self.context)
        if not help_text:
            return

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)

        x = event.x_root + 10
        y = event.y_root + 10
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window,
            text=help_text,
            background="#ffffdd",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Microsoft YaHei", 9),
            padx=8,
            pady=4,
            wraplength=400
        )
        label.pack()

    def _on_leave(self, event):
        """鼠标离开"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def show_help_dialog(parent, initial_topic: Optional[str] = None):
    """显示帮助对话框"""
    dialog = HelpDialog(parent, initial_topic)
    return dialog


def show_shortcuts_dialog(parent):
    """显示快捷键对话框"""
    dialog = ShortcutsDialog(parent)
    return dialog


def show_about_dialog(parent):
    """显示关于对话框"""
    dialog = AboutDialog(parent)
    return dialog


class ModuleHelpButton(ttk.Frame):
    """模块帮助按钮组件 - 可嵌入到各模块的工具栏中"""

    def __init__(self, parent, module_id: str, on_full_help: Callable = None, **kwargs):
        """
        Args:
            parent: 父容器
            module_id: 模块标识符（如 'outline', 'script', 'timeline' 等）
            on_full_help: 点击"查看完整帮助"时的回调函数
        """
        super().__init__(parent, **kwargs)
        self.module_id = module_id
        self.on_full_help = on_full_help
        self.help_manager = get_help_manager()
        self.tooltip_window = None

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 帮助按钮
        self.help_btn = ttk.Button(
            self,
            text="?",
            width=3,
            command=self._show_quick_help
        )
        self.help_btn.pack(side=tk.LEFT)

        # 绑定悬停提示
        self.help_btn.bind("<Enter>", self._on_enter)
        self.help_btn.bind("<Leave>", self._on_leave)

    def _on_enter(self, event):
        """鼠标进入显示简短提示"""
        help_text = self.help_manager.get_context_help(self.module_id)
        if not help_text:
            return

        self.tooltip_window = tk.Toplevel(self)
        self.tooltip_window.wm_overrideredirect(True)

        x = event.x_root + 10
        y = event.y_root + 10
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window,
            text=f"{help_text}\n\n点击查看详细帮助",
            background="#ffffdd",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Microsoft YaHei", 9),
            padx=8,
            pady=4,
            wraplength=350,
            justify=tk.LEFT
        )
        label.pack()

    def _on_leave(self, event):
        """鼠标离开隐藏提示"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def _show_quick_help(self):
        """显示快速帮助弹窗"""
        ModuleHelpPopup(self, self.module_id, self.on_full_help)


class ModuleHelpPopup(tk.Toplevel):
    """模块帮助弹窗 - 显示模块的快速帮助信息"""

    def __init__(self, parent, module_id: str, on_full_help: Callable = None):
        super().__init__(parent)
        self.module_id = module_id
        self.on_full_help = on_full_help
        self.help_manager = get_help_manager()

        self.title("模块帮助")
        self.geometry("400x350")
        self.resizable(False, False)

        self.transient(parent)

        self._setup_ui()

        # 居中显示
        self.update_idletasks()
        x = parent.winfo_rootx() + 50
        y = parent.winfo_rooty() + 50
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """设置UI"""
        module_help = self.help_manager.get_module_help(self.module_id)

        if not module_help:
            ttk.Label(self, text="暂无帮助信息").pack(pady=20)
            return

        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            title_frame,
            text=module_help["title"],
            font=("Microsoft YaHei", 14, "bold")
        ).pack(side=tk.LEFT)

        # 快速提示
        tips_frame = ttk.LabelFrame(main_frame, text="快速提示", padding=10)
        tips_frame.pack(fill=tk.X, pady=(0, 10))

        for tip in module_help.get("quick_tips", []):
            tip_label = ttk.Label(tips_frame, text=f"  {tip}", wraplength=350)
            tip_label.pack(anchor=tk.W, pady=1)

        # 主要功能
        features_frame = ttk.LabelFrame(main_frame, text="主要功能", padding=10)
        features_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        for name, desc in module_help.get("features", []):
            feature_frame = ttk.Frame(features_frame)
            feature_frame.pack(fill=tk.X, pady=2)

            ttk.Label(
                feature_frame,
                text=f"{name}:",
                font=("", 9, "bold"),
                width=12
            ).pack(side=tk.LEFT)

            ttk.Label(
                feature_frame,
                text=desc,
                wraplength=280
            ).pack(side=tk.LEFT, fill=tk.X)

        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        if self.on_full_help:
            ttk.Button(
                btn_frame,
                text="查看完整帮助",
                command=self._open_full_help
            ).pack(side=tk.LEFT)

        ttk.Button(
            btn_frame,
            text="关闭",
            command=self.destroy
        ).pack(side=tk.RIGHT)

    def _open_full_help(self):
        """打开完整帮助"""
        module_help = self.help_manager.get_module_help(self.module_id)
        if module_help and self.on_full_help:
            topic_id = module_help.get("topic_id", "getting_started")
            self.on_full_help(topic_id)
        self.destroy()


class ModuleHelpBar(ttk.Frame):
    """模块帮助条 - 显示在模块顶部的帮助提示条"""

    def __init__(self, parent, module_id: str, on_help_click: Callable = None, **kwargs):
        """
        Args:
            parent: 父容器
            module_id: 模块标识符
            on_help_click: 点击帮助时的回调
        """
        super().__init__(parent, **kwargs)
        self.module_id = module_id
        self.on_help_click = on_help_click
        self.help_manager = get_help_manager()
        self._is_collapsed = False

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 获取上下文帮助
        help_text = self.help_manager.get_context_help(self.module_id)
        module_help = self.help_manager.get_module_help(self.module_id)

        title = module_help.get("title", "帮助") if module_help else "帮助"

        # 帮助图标
        self.icon_label = ttk.Label(self, text="", font=("Segoe UI Emoji", 12))
        self.icon_label.pack(side=tk.LEFT, padx=(5, 5))

        # 帮助文本
        self.help_label = ttk.Label(
            self,
            text=help_text if help_text else f"{title} - 点击 ? 查看帮助",
            font=("Microsoft YaHei", 9),
            foreground="#666"
        )
        self.help_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 帮助按钮
        self.help_btn = ttk.Button(
            self,
            text="?",
            width=3,
            command=self._on_help_click
        )
        self.help_btn.pack(side=tk.RIGHT, padx=5)

        # 折叠按钮
        self.collapse_btn = ttk.Button(
            self,
            text="",
            width=3,
            command=self._toggle_collapse
        )
        self.collapse_btn.pack(side=tk.RIGHT)

    def _on_help_click(self):
        """帮助按钮点击"""
        if self.on_help_click:
            self.on_help_click(self.module_id)
        else:
            ModuleHelpPopup(self, self.module_id)

    def _toggle_collapse(self):
        """折叠/展开帮助条"""
        self._is_collapsed = not self._is_collapsed
        if self._is_collapsed:
            self.help_label.pack_forget()
            self.collapse_btn.configure(text="")
        else:
            self.help_label.pack(side=tk.LEFT, fill=tk.X, expand=True, after=self.icon_label)
            self.collapse_btn.configure(text="")

    def update_help_text(self, text: str):
        """更新帮助文本"""
        self.help_label.configure(text=text)


def create_module_help_button(parent, module_id: str, on_full_help: Callable = None) -> ModuleHelpButton:
    """创建模块帮助按钮的工厂函数"""
    return ModuleHelpButton(parent, module_id, on_full_help)


def create_module_help_bar(parent, module_id: str, on_help_click: Callable = None) -> ModuleHelpBar:
    """创建模块帮助条的工厂函数"""
    return ModuleHelpBar(parent, module_id, on_help_click)
