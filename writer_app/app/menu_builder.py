import tkinter as tk

from writer_app.core.exporter import ExporterRegistry
from writer_app.ui.floating_assistant.constants import ASSISTANT_NAME


class MenuBuilder:
    """Build the application menu bar for the main shell."""

    def __init__(self, app):
        self.app = app

    def build(self):
        app = self.app
        app.menubar = tk.Menu(app.root)
        app.root.config(menu=app.menubar)

        file_menu = tk.Menu(app.menubar, tearoff=0)
        app.menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建项目", command=app.new_project, accelerator="Ctrl+N")
        file_menu.add_command(label="打开项目...", command=app.open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="保存项目", command=app.save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为...", command=app.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="项目设置 / 更改类型...", command=app.change_project_type)
        file_menu.add_separator()

        export_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="导出...", menu=export_menu)
        for fmt in ExporterRegistry.list_formats():
            export_menu.add_command(
                label=f"导出为 {fmt.name} ({fmt.extension})",
                command=lambda f=fmt: app.perform_export(f),
            )

        file_menu.add_separator()
        file_menu.add_command(label="退出", command=app.on_closing)

        edit_menu = tk.Menu(app.menubar, tearoff=0)
        app.menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="撤销", command=app.undo, accelerator="Ctrl+Z", state=tk.DISABLED)
        edit_menu.add_command(label="重做", command=app.redo, accelerator="Ctrl+Y", state=tk.DISABLED)
        app.edit_menu = edit_menu
        edit_menu.add_separator()
        edit_menu.add_command(label="查找与替换...", command=app.open_search_dialog, accelerator="Ctrl+F")
        edit_menu.add_command(label="全局替换 (Global Rename)...", command=app.open_global_rename_dialog)
        edit_menu.add_separator()
        edit_menu.add_command(label="运行逻辑校验 (Logic Check)", command=app.run_logic_check)
        edit_menu.add_separator()
        edit_menu.add_command(label="添加子节点", command=app.add_child_node, accelerator="Tab")
        edit_menu.add_command(label="添加同级节点", command=app.add_sibling_node, accelerator="Enter")
        edit_menu.add_command(label="删除节点", command=app.delete_node, accelerator="Delete")
        edit_menu.add_separator()
        edit_menu.add_command(label="展开所有", command=app.expand_all)
        edit_menu.add_command(label="折叠所有", command=app.collapse_all)
        edit_menu.add_separator()
        edit_menu.add_command(label="标签管理...", command=app.open_tag_manager)

        tools_menu = tk.Menu(app.menubar, tearoff=0)
        app.menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="写作冲刺 (Word Sprint)", command=app.open_word_sprint)
        tools_menu.add_command(label="起名助手", command=app.open_name_generator)

        career_menu = tk.Menu(app.menubar, tearoff=0)
        app.menubar.add_cascade(label="生涯", menu=career_menu)
        career_menu.add_command(label="模拟投稿 (Submission)", command=app.open_submission_dialog)
        career_menu.add_separator()
        career_menu.add_command(label="我的成就 (Achievements)", command=app.open_achievements_dialog)

        view_menu = tk.Menu(app.menubar, tearoff=0)
        app.menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="刷新", command=app.refresh_all, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(
            label=f"{ASSISTANT_NAME} (悬浮窗)",
            command=app.toggle_floating_assistant,
            accelerator="F2",
        )
        view_menu.add_separator()
        view_menu.add_command(label="切换主题 (Dark/Light)", command=app.toggle_theme)

        focus_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="专注模式 (Focus Mode)", menu=focus_menu)
        focus_menu.add_command(label="开启/关闭专注模式", command=app.toggle_focus_mode, accelerator="F10")
        focus_menu.add_command(label="打字机模式", command=app.toggle_typewriter_mode, accelerator="F9")
        focus_menu.add_separator()
        focus_menu.add_command(label="行聚焦", command=lambda: app.set_focus_level("line"), accelerator="Ctrl+Shift+1")
        focus_menu.add_command(label="句子聚焦", command=lambda: app.set_focus_level("sentence"), accelerator="Ctrl+Shift+2")
        focus_menu.add_command(label="段落聚焦", command=lambda: app.set_focus_level("paragraph"), accelerator="Ctrl+Shift+3")
        focus_menu.add_command(label="对话聚焦", command=lambda: app.set_focus_level("dialogue"), accelerator="Ctrl+Shift+4")
        focus_menu.add_separator()
        focus_menu.add_command(label="切换聚焦级别", command=app._cycle_focus_level, accelerator="Ctrl+Shift+F")
        focus_menu.add_command(label="专注模式设置...", command=app.open_focus_mode_settings)

        view_menu.add_command(label="沉浸模式 (Zen Mode)", command=app.toggle_zen_mode, accelerator="F11")

        settings_menu = tk.Menu(app.menubar, tearoff=0)
        app.menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label=f"通用/{ASSISTANT_NAME}设置...", command=lambda: app.open_settings_dialog())
        settings_menu.add_separator()
        settings_menu.add_checkbutton(label="AI 模式", variable=app.ai_mode_var, command=app.toggle_ai_mode)

        help_menu = tk.Menu(app.menubar, tearoff=0)
        app.menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=app.show_help, accelerator="F1")
        help_menu.add_command(label="快捷键速查", command=app.show_shortcuts, accelerator="Ctrl+/")
        help_menu.add_separator()
        help_menu.add_command(label="快速入门", command=lambda: app.show_help("getting_started"))
        help_menu.add_command(label="AI 功能说明", command=lambda: app.show_help("ai_features"))
        help_menu.add_command(label="常见问题", command=lambda: app.show_help("troubleshooting"))
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=app.show_about)
