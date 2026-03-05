"""
悬浮助手聊天视图组件 (Chat View Component)
负责聊天记录显示、输入框、快捷按钮及剪贴板通知
"""
import tkinter as tk
from tkinter import ttk
from ..constants import QUICK_PROMPTS_AI, QUICK_TOOLS
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

def get_icon_font(size=12):
    return IconManager().get_font(size=size)

class ChatView(tk.Frame):
    def __init__(self, parent, assistant):
        super().__init__(parent, bg="#2D2D2D")
        self.assistant = assistant
        self.icon_mgr = IconManager()
        
        self._setup_ui()
        
    def _setup_ui(self):
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 顶部工具条
        self._setup_toolbar()
        # 聊天显示区
        self._setup_chat_display()
        # 快捷按钮栏
        self._setup_quick_buttons()
        # 输入区
        self._setup_input_area()

    def _setup_toolbar(self):
        self.tool_bar = tk.Frame(self, bg="#1E88E5", height=24)
        self.tool_bar.pack(fill=tk.X)

        # 模式标签
        self.mode_label_frame = tk.Frame(self.tool_bar, bg="#1E88E5")
        self.mode_label_frame.pack(side=tk.LEFT, padx=5)
        
        self.mode_icon_lbl = tk.Label(self.mode_label_frame, text="", font=get_icon_font(10), bg="#1E88E5", fg="white")
        self.mode_icon_lbl.pack(side=tk.LEFT)
        
        self.mode_text_lbl = tk.Label(self.mode_label_frame, text="", font=("Microsoft YaHei", 8), bg="#1E88E5", fg="white")
        self.mode_text_lbl.pack(side=tk.LEFT)

        # 推理模式快捷切换
        self.mode_switch_btn = tk.Label(
            self.tool_bar,
            text="推理",
            font=("Microsoft YaHei", 8),
            bg="#1E88E5",
            fg="white",
            cursor="hand2"
        )
        self.mode_switch_btn.pack(side=tk.RIGHT, padx=6)
        self.mode_switch_btn.bind("<Button-1>", lambda e: self.assistant._toggle_reverse_mode())

        self.update_mode_label()

        # 关闭按钮
        btn_close = tk.Label(
            self.tool_bar,
            text=get_icon("dismiss", "×"),
            font=get_icon_font(10),
            bg="#1E88E5",
            fg="white",
            cursor="hand2"
        )
        btn_close.pack(side=tk.RIGHT, padx=5)
        btn_close.bind("<Button-1>", self.assistant._toggle_expand)

    def _setup_chat_display(self):
        self.chat_display = tk.Text(
            self,
            wrap=tk.WORD,
            bg="#1E1E1E",
            fg="#FFFFFF",
            font=("Microsoft YaHei", 9),
            relief=tk.FLAT,
            padx=5,
            pady=5,
            height=8,
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # 配置标签样式
        tag_styles = [
            ("user", "#64B5F6", ("Microsoft YaHei", 9, "bold")),
            ("assistant", "#81C784", ("Microsoft YaHei", 9, "bold")),
            ("system", "#FFB74D", ("Microsoft YaHei", 8, "italic")),
            ("error", "#EF5350", ("Microsoft YaHei", 9)),
            ("content", "#E0E0E0", ("Microsoft YaHei", 9)),
            ("action", "#F06292", ("Microsoft YaHei", 9)),
            ("tool", "#CE93D8", ("Microsoft YaHei", 9)),
            ("streaming", "#90CAF9", ("Microsoft YaHei", 9)),
            ("icon", "#FFFFFF", get_icon_font(10)), # Special tag for font icons in text
        ]

        for tag, color, font in tag_styles:
            self.chat_display.tag_configure(tag, foreground=color, font=font)

    def _setup_quick_buttons(self):
        self.quick_frame = tk.Frame(self, bg="#2D2D2D")
        self.quick_frame.pack(fill=tk.X, pady=2)

        # 更多按钮
        self.more_btn = tk.Label(
            self.quick_frame,
            text=get_icon("settings", "⚙"),
            font=get_icon_font(10),
            bg="#424242",
            fg="#FFFFFF",
            padx=5,
            pady=2,
            cursor="hand2"
        )
        self.more_btn.pack(side=tk.RIGHT, padx=2)
        self.more_btn.bind("<Button-1>", self.assistant._show_context_menu)

        self.update_quick_buttons()

    def _setup_input_area(self):
        self.input_frame = tk.Frame(self, bg="#2D2D2D")
        self.input_frame.pack(fill=tk.X, pady=(2, 5), padx=5)

        # 语音按钮
        self.voice_btn = tk.Label(
            self.input_frame,
            text=get_icon("mic", "🎤"),
            font=get_icon_font(10),
            bg="#424242",
            fg="white",
            width=3,
            cursor="hand2"
        )
        self.voice_btn.pack(side=tk.LEFT, padx=(0, 2), fill=tk.Y)
        self.voice_btn.bind("<Button-1>", self.assistant._toggle_voice_input)
        
        # 输入框
        self.input_text = tk.Text(
            self.input_frame,
            height=2,
            wrap=tk.WORD,
            bg="#3D3D3D",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            font=("Microsoft YaHei", 9),
            relief=tk.FLAT,
            padx=5,
            pady=5
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_text.bind("<Return>", self.assistant._on_enter)
        self.input_text.bind("<Shift-Return>", lambda e: None)
        self.input_text.bind("<FocusIn>", self._on_input_focus_in)
        self.input_text.bind("<FocusOut>", self._on_input_focus_out)

        # 上下文按钮
        self.context_btn = tk.Label(
            self.input_frame,
            text=get_icon("clipboard_paste", "📋"),
            font=get_icon_font(10),
            bg="#424242",
            fg="white",
            width=3,
            cursor="hand2"
        )
        self.context_btn.pack(side=tk.RIGHT, padx=(2, 0), fill=tk.Y)
        self.context_btn.bind("<Button-1>", self.assistant._insert_context)

        # 发送按钮
        self.send_btn = tk.Label(
            self.input_frame,
            text=get_icon("arrow_up", "↑"),
            font=get_icon_font(12),
            bg="#1E88E5",
            fg="white",
            width=3,
            cursor="hand2"
        )
        self.send_btn.pack(side=tk.RIGHT, padx=(2, 0), fill=tk.Y)
        self.send_btn.bind("<Button-1>", self.assistant._on_send)

    def update_quick_buttons(self):
        """更新快捷按钮"""
        # 清除现有按钮（保留more_btn）
        for widget in self.quick_frame.winfo_children():
            if widget != self.more_btn:
                widget.destroy()

        if self.assistant.ai_mode_enabled:
            # AI模式按钮
            for i, (name, _) in enumerate(QUICK_PROMPTS_AI[:3]):
                btn = tk.Label(
                    self.quick_frame,
                    text=name,
                    font=("Microsoft YaHei", 8),
                    bg="#424242",
                    fg="#FFFFFF",
                    padx=5,
                    pady=2,
                    cursor="hand2"
                )
                btn.pack(side=tk.LEFT, padx=2)
                btn.bind("<Button-1>", lambda e, idx=i: self.assistant._use_ai_prompt(idx))
        else:
            # 工具模式按钮
            for name, tool_id in QUICK_TOOLS[:4]:
                btn = tk.Label(
                    self.quick_frame,
                    text=name,
                    font=("Microsoft YaHei", 8),
                    bg="#7B1FA2" if tool_id in ["name_generator", "dice"] else "#424242",
                    fg="#FFFFFF",
                    padx=5,
                    pady=2,
                    cursor="hand2"
                )
                btn.pack(side=tk.LEFT, padx=2)
                btn.bind("<Button-1>", lambda e, tid=tool_id: self.assistant._use_tool(tid))

    def append_message(self, tag: str, content: str):
        """追加消息"""
        self.chat_display.configure(state=tk.NORMAL)
        
        # In a text widget, we can't easily switch font mid-line unless we use multiple inserts with different tags.
        from ..constants import ASSISTANT_NAME
        
        if tag == "user":
            self.chat_display.insert(tk.END, "用户: ", tag)
        elif tag == "assistant":
            self.chat_display.insert(tk.END, f"{ASSISTANT_NAME}: ", tag)
        elif tag == "system":
            self.chat_display.insert(tk.END, "[系统] ", tag)
        elif tag == "tool":
            self.chat_display.insert(tk.END, get_icon("wrench", "🔧") + " ", ("icon", "tool"))
        elif tag == "error":
            self.chat_display.insert(tk.END, get_icon("error_circle", "❌") + " ", ("icon", "error"))

        self.chat_display.insert(tk.END, f"{content}\n\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.configure(state=tk.DISABLED)

    def append_streaming_token(self, token: str):
        """追加流式token"""
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, token, "streaming")
        self.chat_display.see(tk.END)
        self.chat_display.configure(state=tk.DISABLED)

    def clear_chat(self):
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.configure(state=tk.DISABLED)

    def get_input(self) -> str:
        return self.input_text.get("1.0", tk.END).strip()

    def set_input(self, text: str):
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)

    def clear_input(self):
        self.input_text.delete("1.0", tk.END)

    def focus_input(self):
        self.input_text.focus_set()

    def insert_input(self, text: str):
        self.input_text.insert(tk.INSERT, text)

    def update_mode_label(self):
        if self.assistant.ai_mode_enabled:
            icon = get_icon("bot", "🤖")
            text = " AI模式"
        else:
            icon = get_icon("games", "🎮")
            text = " 工具模式"
        
        self.mode_icon_lbl.configure(text=icon)
        self.mode_text_lbl.configure(text=text)

        # 根据当前模式更新切换按钮文案
        if hasattr(self, "mode_switch_btn"):
            try:
                active_mode = self.assistant._get_active_mode()
            except Exception:
                active_mode = "leisure"
            if active_mode == "reverse_engineering":
                self.mode_switch_btn.configure(text="返回")
            else:
                self.mode_switch_btn.configure(text="推理")

    def update_voice_button(self, is_listening: bool):
        bg = "#F44336" if is_listening else "#424242"
        self.voice_btn.configure(bg=bg)

    def show_clipboard_actions(self, actions: list, on_action: callable, on_cancel: callable):
        """显示剪贴板操作按钮"""
        # 清除现有按钮
        for widget in self.quick_frame.winfo_children():
            widget.destroy()

        # 添加操作按钮
        for label, action_type, prompt in actions[:4]:
            btn = ttk.Button(
                self.quick_frame,
                text=label,
                width=6,
                command=lambda p=prompt: on_action(p)
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)

        # 添加取消按钮
        cancel_btn = tk.Label(
            self.quick_frame,
            text=get_icon("dismiss", "✕"),
            font=get_icon_font(10),
            bg="#424242",
            fg="white",
            padx=5,
            pady=2,
            cursor="hand2"
        )
        cancel_btn.pack(side=tk.LEFT, padx=2, pady=2)
        cancel_btn.bind("<Button-1>", lambda e: on_cancel())

    def show_action_buttons(self, actions: list, on_cancel: callable = None, cancel_label: str = "取消"):
        """显示自定义操作按钮"""
        for widget in self.quick_frame.winfo_children():
            if widget != self.more_btn:
                widget.destroy()

        def _restore():
            if on_cancel:
                on_cancel()
            self.update_quick_buttons()

        for label, callback in actions[:4]:
            btn = ttk.Button(
                self.quick_frame,
                text=label,
                width=8,
                command=lambda cb=callback: self._run_action(cb)
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)

        cancel_btn = tk.Label(
            self.quick_frame,
            text=cancel_label,
            font=("Microsoft YaHei", 8),
            bg="#424242",
            fg="white",
            padx=5,
            pady=2,
            cursor="hand2"
        )
        cancel_btn.pack(side=tk.LEFT, padx=2, pady=2)
        cancel_btn.bind("<Button-1>", lambda e: _restore())

    def _run_action(self, callback):
        try:
            callback()
        finally:
            self.update_quick_buttons()

    def _on_input_focus_in(self, event):
        """输入框获得焦点，展开"""
        self.input_text.configure(height=5)

    def _on_input_focus_out(self, event):
        """输入框失去焦点，收起"""
        content = self.get_input()
        if len(content) < 50 and content.count('\n') < 2:
            self.input_text.configure(height=2)
