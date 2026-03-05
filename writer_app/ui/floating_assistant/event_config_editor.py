"""
悬浮助手事件配置编辑器（GUI）- 增强版

功能:
- JSON 语法高亮
- 字段帮助提示
- 格式化 JSON 按钮
- 撤销/重做支持
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Any, Dict, Optional

from writer_app.core.config import ConfigManager
from writer_app.core.theme import ThemeManager
from writer_app.ui.components.json_text_editor import JsonTextEditor
from writer_app.ui.components.toast import show_toast

from .event_config import (
    DEFAULT_EVENT_CONFIG,
    get_default_config_path,
    load_event_config,
    save_event_config,
)


# Section definitions with help text
SECTION_DEFS = [
    ("事件->模块映射", "event_to_module",
     "映射事件类型到模块名称。\n键: 事件名 (如 'scene_added')\n值: 模块名 (如 'script')"),
    ("创建事件类型", "creation_event_types",
     "触发创作统计的事件类型列表。\n例如: ['scene_added', 'character_added']"),
    ("主题事件类型", "theme_event_types",
     "影响主题标签追踪的事件类型。\n用于统计写作主题偏好。"),
    ("主题忽略前缀", "theme_ignore_prefixes",
     "在统计主题时忽略的标签前缀。\n例如: ['temp_', 'draft_']"),
    ("类型立绘映射", "type_photo_states",
     "根据项目类型映射到助手的立绘状态。\n键: 项目类型, 值: 立绘状态名"),
    ("成就相册奖励", "achievement_photo_rewards",
     "成就解锁时奖励的相册图片。\n键: 成就ID, 值: 图片路径或ID"),
    ("模块里程碑", "module_milestones",
     "各模块的里程碑定义。\n每个里程碑包含: count(次数), title(标题), message(消息)"),
    ("题材里程碑", "type_milestones",
     "按项目题材的里程碑。\n结构同模块里程碑。"),
    ("主题里程碑", "theme_milestones",
     "按写作主题的里程碑。\n结构同模块里程碑。"),
    ("时间段事件", "time_events",
     "按时间段触发的事件定义。\n包含: start_hour, end_hour, events 数组"),
]


class Tooltip:
    """Simple tooltip implementation."""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tooltip_window: Optional[tk.Toplevel] = None

        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tooltip_window:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify=tk.LEFT,
            background="#FFFFCC",
            relief="solid",
            borderwidth=1,
            font=("Microsoft YaHei UI", 9),
            padx=6,
            pady=4,
        )
        label.pack()

    def _hide(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class AssistantEventConfigEditor(tk.Tk):
    """Enhanced event config editor with syntax highlighting and help tooltips."""

    def __init__(self):
        super().__init__()
        self.title("悬浮助手事件配置编辑器")
        self.geometry("1100x800")
        self.minsize(800, 600)

        self.config_path = Path(get_default_config_path())
        self._section_widgets: Dict[str, JsonTextEditor] = {}
        self._modified = False

        # Theme support
        self.app_config = ConfigManager()
        self.theme_manager = ThemeManager(self.app_config.get("theme", "Light"))

        self._build_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._load_config()
        self._apply_theme()

    def _setup_menu(self):
        """Setup menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="保存配置", command=self._save_config, accelerator="Ctrl+S")
        file_menu.add_command(label="重新载入", command=self._load_config, accelerator="Ctrl+R")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.destroy, accelerator="Alt+F4")

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="格式化全部", command=self._format_all, accelerator="Ctrl+Shift+F")
        edit_menu.add_command(label="验证全部", command=self._validate_all)
        edit_menu.add_separator()
        edit_menu.add_command(label="重置为默认", command=self._reset_defaults)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="切换主题", command=self._toggle_theme)

        # Bind keyboard shortcuts
        self.bind("<Control-s>", lambda e: self._save_config())
        self.bind("<Control-r>", lambda e: self._load_config())
        self.bind("<Control-Shift-F>", lambda e: self._format_all())

    def _toggle_theme(self):
        """Toggle between light and dark theme."""
        self.theme_manager.toggle_theme()
        self.app_config.set("theme", self.theme_manager.current_theme)
        self.app_config.save()
        self._apply_theme()

    def _apply_theme(self):
        """Apply current theme to the UI."""
        theme = self.theme_manager
        style = ttk.Style(self)

        try:
            style.theme_use('clam')
        except Exception:
            pass

        bg = theme.get_color("bg_secondary")
        fg = theme.get_color("fg_primary")

        self.configure(bg=bg)
        style.configure(".", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton", background=bg, foreground=fg)
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", background=bg, foreground=fg)
        style.configure("TLabelframe", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)

    def _setup_status_bar(self):
        """Setup status bar at bottom of window."""
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

        self.status_label = ttk.Label(status_frame, text="就绪", foreground="#666666")
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.modified_label = ttk.Label(status_frame, text="", foreground="#D32F2F")
        self.modified_label.pack(side=tk.RIGHT, padx=5)

        file_label = ttk.Label(
            status_frame,
            text=f"配置文件: {self.config_path.name}",
            foreground="#888888"
        )
        file_label.pack(side=tk.RIGHT, padx=10)

    def _update_status(self, text: str):
        """Update status bar text."""
        self.status_label.configure(text=text)

    def _mark_modified(self):
        """Mark config as modified."""
        self._modified = True
        self.modified_label.configure(text="● 有未保存的更改")

    def _build_ui(self):
        # Header with path info
        header = ttk.Frame(self, padding=10)
        header.pack(fill=tk.X)

        path_label = ttk.Label(
            header,
            text=f"配置文件: {self.config_path}",
            foreground="#666666",
        )
        path_label.pack(side=tk.LEFT, expand=True, anchor=tk.W)

        # Keyboard shortcuts hint
        shortcut_label = ttk.Label(
            header,
            text="快捷键: Ctrl+Z 撤销 | Ctrl+Y 重做 | Ctrl+Shift+F 格式化",
            foreground="#888888",
        )
        shortcut_label.pack(side=tk.RIGHT)

        # Action buttons
        actions = ttk.Frame(self, padding=10)
        actions.pack(fill=tk.X)

        btn_save = ttk.Button(actions, text="保存配置", command=self._save_config, width=12)
        btn_reload = ttk.Button(actions, text="重新载入", command=self._load_config, width=12)
        btn_reset = ttk.Button(actions, text="重置为默认", command=self._reset_defaults, width=12)
        btn_format_all = ttk.Button(actions, text="格式化全部", command=self._format_all, width=12)
        btn_validate = ttk.Button(actions, text="验证全部", command=self._validate_all, width=12)

        btn_save.pack(side=tk.LEFT, padx=4)
        btn_reload.pack(side=tk.LEFT, padx=4)
        btn_reset.pack(side=tk.LEFT, padx=4)

        ttk.Separator(actions, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        btn_format_all.pack(side=tk.LEFT, padx=4)
        btn_validate.pack(side=tk.LEFT, padx=4)

        # Search bar
        search_frame = ttk.Frame(self, padding=(10, 5))
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search_change())

        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=2)

        ttk.Button(search_frame, text="查找", command=self._find_next, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="上一个", command=self._find_prev, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="清除", command=lambda: self.search_var.set(""), width=6).pack(side=tk.LEFT, padx=2)

        self.search_count_label = ttk.Label(search_frame, text="", foreground="#666666")
        self.search_count_label.pack(side=tk.LEFT, padx=10)

        # Track search state
        self._search_matches = []
        self._search_index = -1

        # Bind search shortcut
        self.bind("<Control-f>", lambda e: search_entry.focus_set())

        # Notebook with tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for title, key, help_text in SECTION_DEFS:
            frame = ttk.Frame(notebook, padding=6)
            notebook.add(frame, text=title)

            # Help row with info button
            help_frame = ttk.Frame(frame)
            help_frame.pack(fill=tk.X, pady=(0, 6))

            help_label = ttk.Label(
                help_frame,
                text="JSON格式编辑。保存前会进行类型校验。",
                foreground="#666666",
            )
            help_label.pack(side=tk.LEFT)

            # Info button with tooltip
            info_btn = ttk.Button(help_frame, text="?", width=2)
            info_btn.pack(side=tk.LEFT, padx=10)
            Tooltip(info_btn, help_text)

            # Format button for this section
            format_btn = ttk.Button(
                help_frame,
                text="格式化",
                width=8,
                command=lambda k=key: self._format_section(k),
            )
            format_btn.pack(side=tk.RIGHT)

            # JSON editor with syntax highlighting
            editor = JsonTextEditor(
                frame,
                height=25,
                show_line_numbers=True,
                dark_theme=False,
            )
            editor.pack(fill=tk.BOTH, expand=True)

            self._section_widgets[key] = editor

    def _load_config(self):
        """Load config from file."""
        config = load_event_config(self.config_path)
        for _, key, _ in SECTION_DEFS:
            value = config.get(key, DEFAULT_EVENT_CONFIG.get(key, {}))
            self._set_section_content(key, value)
        self._modified = False
        self.modified_label.configure(text="")
        self._update_status(f"已加载 {len(SECTION_DEFS)} 个配置项")

    def _reset_defaults(self):
        """Reset all sections to default values."""
        if not messagebox.askyesno("确认", "确认重置为默认配置吗？所有更改将丢失。"):
            return
        for _, key, _ in SECTION_DEFS:
            self._set_section_content(key, DEFAULT_EVENT_CONFIG.get(key, {}))
        messagebox.showinfo("完成", "已重置为默认配置。")

    def _set_section_content(self, key: str, value: Any):
        """Set content for a section."""
        editor = self._section_widgets[key]
        editor.set_json(value)

    def _get_section_content(self, key: str) -> Any:
        """Get parsed content from a section."""
        editor = self._section_widgets[key]
        content = editor.get_content()
        if not content:
            return DEFAULT_EVENT_CONFIG.get(key, {})
        return json.loads(content)

    def _validate_section(self, key: str, value: Any) -> Optional[str]:
        """Validate a section's value. Returns error message or None."""
        if key in ("event_to_module", "type_photo_states", "achievement_photo_rewards"):
            if not isinstance(value, dict):
                return "必须是JSON对象 ({})"
        elif key in ("creation_event_types", "theme_event_types", "theme_ignore_prefixes"):
            if not isinstance(value, list):
                return "必须是JSON数组 ([])"
        else:
            if not isinstance(value, list):
                return "必须是JSON数组"
            if value and any(not isinstance(item, dict) for item in value):
                return "数组成员必须是JSON对象"
        return None

    def _format_section(self, key: str):
        """Format JSON in a specific section."""
        editor = self._section_widgets[key]
        editor._format_json()

    def _format_all(self):
        """Format JSON in all sections."""
        for _, key, _ in SECTION_DEFS:
            self._format_section(key)
        show_toast(self, "已格式化全部配置", toast_type="success", duration=1500)

    def _validate_all(self):
        """Validate all sections."""
        errors = []
        for title, key, _ in SECTION_DEFS:
            try:
                value = self._get_section_content(key)
                error = self._validate_section(key, value)
                if error:
                    errors.append(f"{title}: {error}")
            except json.JSONDecodeError as e:
                errors.append(f"{title}: JSON语法错误 - {e}")

        if errors:
            messagebox.showerror("验证失败", "\n".join(errors))
        else:
            show_toast(self, "验证通过：所有配置格式正确", toast_type="success", duration=2000)

    # --- Search Functionality ---

    def _get_current_editor(self) -> Optional[JsonTextEditor]:
        """Get the editor for the currently selected tab."""
        try:
            current_tab = self.notebook.index(self.notebook.select())
            key = SECTION_DEFS[current_tab][1]
            return self._section_widgets.get(key)
        except Exception:
            return None

    def _on_search_change(self):
        """Handle search text change."""
        search_text = self.search_var.get()

        # Clear previous highlights
        for key, editor in self._section_widgets.items():
            text_widget = editor.text
            text_widget.tag_remove("search_highlight", "1.0", tk.END)
            text_widget.tag_remove("search_current", "1.0", tk.END)

        if not search_text:
            self.search_count_label.configure(text="")
            self._search_matches = []
            self._search_index = -1
            return

        # Find all matches in current editor
        editor = self._get_current_editor()
        if not editor:
            return

        text_widget = editor.text
        content = text_widget.get("1.0", tk.END)

        # Configure highlight tags
        text_widget.tag_configure("search_highlight", background="#FFFF00", foreground="#000000")
        text_widget.tag_configure("search_current", background="#FF9800", foreground="#000000")

        # Find all matches
        self._search_matches = []
        start_idx = "1.0"

        while True:
            pos = text_widget.search(search_text, start_idx, tk.END, nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(search_text)}c"
            self._search_matches.append((pos, end_pos))
            text_widget.tag_add("search_highlight", pos, end_pos)
            start_idx = end_pos

        # Update count label
        count = len(self._search_matches)
        if count > 0:
            self._search_index = 0
            self._highlight_current_match()
            self.search_count_label.configure(text=f"找到 {count} 个匹配")
        else:
            self._search_index = -1
            self.search_count_label.configure(text="未找到")

    def _highlight_current_match(self):
        """Highlight the current search match."""
        if not self._search_matches or self._search_index < 0:
            return

        editor = self._get_current_editor()
        if not editor:
            return

        text_widget = editor.text

        # Clear current highlight
        text_widget.tag_remove("search_current", "1.0", tk.END)

        # Apply current highlight
        pos, end_pos = self._search_matches[self._search_index]
        text_widget.tag_add("search_current", pos, end_pos)
        text_widget.see(pos)

        # Update count label with position
        self.search_count_label.configure(
            text=f"{self._search_index + 1}/{len(self._search_matches)}"
        )

    def _find_next(self):
        """Find next match."""
        if not self._search_matches:
            return

        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self._highlight_current_match()

    def _find_prev(self):
        """Find previous match."""
        if not self._search_matches:
            return

        self._search_index = (self._search_index - 1) % len(self._search_matches)
        self._highlight_current_match()

    def _save_config(self):
        """Save config to file."""
        config = dict(DEFAULT_EVENT_CONFIG)

        try:
            for title, key, _ in SECTION_DEFS:
                value = self._get_section_content(key)
                error = self._validate_section(key, value)
                if error:
                    messagebox.showerror("校验失败", f"{title}: {error}")
                    return
                config[key] = value
        except json.JSONDecodeError as exc:
            messagebox.showerror("JSON错误", f"JSON语法错误: {exc}")
            return

        try:
            save_event_config(self.config_path, config)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            self._update_status("保存失败")
            return

        self._modified = False
        self.modified_label.configure(text="")
        self._update_status("配置已保存")
        show_toast(self, "配置已保存", toast_type="success", duration=1500)


def run_editor():
    """Entry point for the editor."""
    app = AssistantEventConfigEditor()
    app.mainloop()


if __name__ == "__main__":
    run_editor()
