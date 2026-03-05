"""
Writer Tool 外置工具启动器

提供统一的图形界面入口，可启动:
- 资源管理器 (Asset Editor)
- 助手配置编辑器 (Assistant Config Editor)
- 事件分析工具 (Event Analyzer)

双击此文件或运行 python start_tools.py 启动
"""

import logging
import subprocess
import sys
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    print("错误: 未找到 tkinter 模块")
    sys.exit(1)


class ToolsLauncher(tk.Tk):
    """Unified tools launcher with modern UI."""

    TOOLS = [
        {
            "name": "资源管理器",
            "desc": "管理项目资源、编辑事件\n支持 .writerproj 项目文件",
            "script": "start_asset_editor.py",
            "icon": "📦",
            "color": "#4A90D9",
        },
        {
            "name": "助手配置编辑器",
            "desc": "配置浮动助手的事件和行为\nJSON 语法高亮编辑",
            "script": "start_assistant_event_editor.py",
            "icon": "⚙️",
            "color": "#7B68EE",
        },
        {
            "name": "事件分析工具",
            "desc": "分析事件逻辑、检测问题\n循环检测、死路径检测",
            "script": "analyze_events.py",
            "args": ["--gui"],
            "icon": "🔍",
            "color": "#2E7D32",
        },
    ]

    def __init__(self):
        super().__init__()
        self.title("Writer Tool - 工具箱")
        self.geometry("500x420")
        self.resizable(False, False)

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 420) // 2
        self.geometry(f"+{x}+{y}")

        self.script_dir = Path(__file__).resolve().parent
        self._setup_ui()

    def _setup_ui(self):
        """Setup the launcher UI."""
        # Header
        header = tk.Frame(self, bg="#2C3E50", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_label = tk.Label(
            header,
            text="Writer Tool 工具箱",
            font=("Microsoft YaHei UI", 18, "bold"),
            fg="white",
            bg="#2C3E50",
        )
        title_label.pack(pady=20)

        # Tools container
        container = tk.Frame(self, bg="#F5F5F5")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        for i, tool in enumerate(self.TOOLS):
            self._create_tool_card(container, tool, i)

        # Footer
        footer = tk.Frame(self, bg="#F5F5F5")
        footer.pack(fill=tk.X, padx=20, pady=(0, 15))

        version_label = tk.Label(
            footer,
            text="Writer Tool v1.02 | 外置工具启动器",
            font=("Microsoft YaHei UI", 9),
            fg="#888888",
            bg="#F5F5F5",
        )
        version_label.pack(side=tk.LEFT)

        help_btn = tk.Button(
            footer,
            text="帮助",
            font=("Microsoft YaHei UI", 9),
            relief=tk.FLAT,
            bg="#F5F5F5",
            fg="#666666",
            cursor="hand2",
            command=self._show_help,
        )
        help_btn.pack(side=tk.RIGHT)

    def _create_tool_card(self, parent, tool: dict, index: int):
        """Create a tool card widget."""
        card = tk.Frame(
            parent,
            bg="white",
            relief=tk.FLAT,
            highlightbackground="#E0E0E0",
            highlightthickness=1,
        )
        card.pack(fill=tk.X, pady=8)

        # Inner content
        inner = tk.Frame(card, bg="white")
        inner.pack(fill=tk.X, padx=15, pady=12)

        # Icon and title row
        icon_label = tk.Label(
            inner,
            text=tool["icon"],
            font=("Segoe UI Emoji", 24),
            bg="white",
        )
        icon_label.pack(side=tk.LEFT)

        text_frame = tk.Frame(inner, bg="white")
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15)

        name_label = tk.Label(
            text_frame,
            text=tool["name"],
            font=("Microsoft YaHei UI", 12, "bold"),
            fg="#333333",
            bg="white",
            anchor=tk.W,
        )
        name_label.pack(anchor=tk.W)

        desc_label = tk.Label(
            text_frame,
            text=tool["desc"],
            font=("Microsoft YaHei UI", 9),
            fg="#666666",
            bg="white",
            anchor=tk.W,
            justify=tk.LEFT,
        )
        desc_label.pack(anchor=tk.W)

        # Launch button
        launch_btn = tk.Button(
            inner,
            text="启动",
            font=("Microsoft YaHei UI", 10),
            fg="white",
            bg=tool["color"],
            activebackground=tool["color"],
            activeforeground="white",
            relief=tk.FLAT,
            width=8,
            height=1,
            cursor="hand2",
            command=lambda t=tool: self._launch_tool(t),
        )
        launch_btn.pack(side=tk.RIGHT, padx=5)

        # Hover effect
        def on_enter(e, c=card):
            c.configure(highlightbackground=tool["color"], highlightthickness=2)

        def on_leave(e, c=card):
            c.configure(highlightbackground="#E0E0E0", highlightthickness=1)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        for widget in [inner, icon_label, text_frame, name_label, desc_label]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _launch_tool(self, tool: dict):
        """Launch a tool in a new process."""
        script_path = self.script_dir / tool["script"]

        if not script_path.exists():
            messagebox.showerror("错误", f"找不到脚本文件:\n{script_path}")
            return

        try:
            args = [sys.executable, str(script_path)]
            if "args" in tool:
                args.extend(tool["args"])

            # Launch detached process
            if sys.platform == "win32":
                subprocess.Popen(
                    args,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=str(self.script_dir),
                )
            else:
                subprocess.Popen(
                    args,
                    start_new_session=True,
                    cwd=str(self.script_dir),
                )

            # Minimize launcher
            self.iconify()

        except Exception as e:
            messagebox.showerror("启动失败", f"无法启动工具:\n{e}")

    def _show_help(self):
        """Show help dialog."""
        help_text = """Writer Tool 外置工具说明

【资源管理器】
用于管理视觉小说/游戏的资源文件和事件。
- 打开 .writerproj 项目文件
- 管理图片、音频等资源
- 编辑游戏事件

【助手配置编辑器】
配置浮动助手的行为和事件触发。
- 编辑事件映射配置
- 设置里程碑和成就
- JSON 格式，支持语法高亮

【事件分析工具】
分析事件文件的逻辑完整性。
- 检测循环引用
- 检测死路径
- 检测缺失的事件引用
- 生成分析报告

快捷键:
- Ctrl+Z: 撤销
- Ctrl+Y: 重做
- Ctrl+S: 保存
- Ctrl+Shift+F: 格式化 JSON
"""
        dialog = tk.Toplevel(self)
        dialog.title("帮助")
        dialog.geometry("450x500")
        dialog.transient(self)

        text = tk.Text(
            dialog,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            padx=15,
            pady=15,
        )
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", help_text)
        text.configure(state=tk.DISABLED)

        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)


def main():
    app = ToolsLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
