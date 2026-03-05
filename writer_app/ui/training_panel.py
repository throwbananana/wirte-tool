import difflib
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Toplevel
from writer_app.core.training import MODES
from writer_app.core.icon_manager import IconManager
from writer_app.ui.help_dialog import create_module_help_button

# UI 常量
FEEDBACK_AREA_HEIGHT = 8


def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)


def get_icon_font(size=12):
    return IconManager().get_font(size=size)


class TrainingPanel(ttk.Frame):
    def __init__(self, parent, controller=None, theme_manager=None):
        super().__init__(parent)
        self.controller = controller
        self.theme_manager = theme_manager
        self.icon_mgr = IconManager()

        self.words_var = tk.StringVar(value="请选择模式和难度后开始。")
        self.level_var = tk.StringVar()
        self.mode_var = tk.StringVar()
        self.tag_var = tk.StringVar()
        self.topic_var = tk.StringVar()
        self.time_limit_var = tk.StringVar(value="无限制")
        self.timer_var = tk.StringVar(value="00:00")
        self.timer_running = False
        self.timer_seconds = 0
        self.is_analyzing = False
        self.ai_mode_enabled = True

        self.setup_ui()

        if self.theme_manager:
            self.apply_theme()

    def setup_ui(self):
        # --- 顶部控制栏 ---
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        # 第1行：模式 & 难度 & 主题
        r1 = ttk.Frame(control_frame)
        r1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(r1, text="训练模块:").pack(side=tk.LEFT)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(r1, textvariable=self.category_var, state="readonly", width=12)
        self.category_combo.pack(side=tk.LEFT, padx=5)
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_change)

        ttk.Label(r1, text="具体模式:").pack(side=tk.LEFT, padx=5)
        self.mode_combo = ttk.Combobox(r1, textvariable=self.mode_var, state="readonly", width=20)
        self.mode_combo.pack(side=tk.LEFT, padx=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)

        ttk.Label(r1, text="难度等级:").pack(side=tk.LEFT, padx=5)
        self.level_combo = ttk.Combobox(r1, textvariable=self.level_var, state="readonly", width=20)
        self.level_combo.pack(side=tk.LEFT, padx=5)

        ttk.Label(r1, text="标签筛选:").pack(side=tk.LEFT, padx=5)
        self.tag_combo = ttk.Combobox(r1, textvariable=self.tag_var, state="readonly", width=15)
        self.tag_combo.pack(side=tk.LEFT, padx=5)

        ttk.Label(r1, text="自定义主题:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(r1, textvariable=self.topic_var, width=15).pack(side=tk.LEFT, padx=5)

        # 帮助按钮
        help_btn = create_module_help_button(r1, "training", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        self.history_btn = ttk.Button(r1, text=f"{get_icon('history', '📜')} 历史记录", command=self.on_history)
        self.history_btn.pack(side=tk.RIGHT)

        # 挑战模式按钮
        self.challenge_btn = ttk.Button(r1, text=f"{get_icon('trophy', '🏆')} 挑战模式", command=self.open_challenge_browser)
        self.challenge_btn.pack(side=tk.RIGHT, padx=5)

        self.daily_btn = ttk.Button(r1, text=f"{get_icon('calendar_star', '🌟')} 每日任务", command=self.on_daily_quest)
        self.daily_btn.pack(side=tk.RIGHT, padx=5)

        # 工具按钮
        self.editor_btn = ttk.Button(r1, text=f"{get_icon('edit', '📝')} 词库管理", command=self.on_open_editor)
        self.editor_btn.pack(side=tk.RIGHT, padx=5)

        self.stats_btn = ttk.Button(r1, text=f"{get_icon('data_usage', '📊')} 统计数据", command=self.on_show_stats)
        self.stats_btn.pack(side=tk.RIGHT, padx=5)

        # 第2行：计时器 & 操作 & 字数统计
        r2 = ttk.Frame(control_frame)
        r2.pack(fill=tk.X)

        self.generate_btn = ttk.Button(r2, text=f"{get_icon('games', '🎲')} 生成题目", command=self.on_generate)
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Separator(r2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # 计时器控件
        ttk.Label(r2, text="定时:").pack(side=tk.LEFT, padx=5)
        self.timer_combo = ttk.Combobox(r2, textvariable=self.time_limit_var, state="readonly", width=10)
        self.timer_combo['values'] = ["无限制", "5 分钟", "10 分钟", "15 分钟", "30 分钟"]
        self.timer_combo.pack(side=tk.LEFT, padx=5)

        self.timer_lbl = ttk.Label(r2, textvariable=self.timer_var, font=("Consolas", 12, "bold"), foreground="blue")
        self.timer_lbl.pack(side=tk.LEFT, padx=10)

        self.timer_btn = ttk.Button(r2, text="开始", command=self.toggle_timer, state="disabled")
        self.timer_btn.pack(side=tk.LEFT)

        ttk.Separator(r2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # 字数统计控件
        ttk.Label(r2, text="目标字数:").pack(side=tk.LEFT, padx=5)
        self.target_word_var = tk.StringVar(value="0")
        self.target_word_entry = ttk.Entry(r2, textvariable=self.target_word_var, width=5)
        self.target_word_entry.pack(side=tk.LEFT, padx=2)

        self.word_count_lbl = ttk.Label(r2, text="字数: 0", font=("Microsoft YaHei UI", 9))
        self.word_count_lbl.pack(side=tk.LEFT, padx=10)

        # 游戏化UI
        ttk.Separator(r2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        self.level_label = ttk.Label(r2, text="等级1 新手", font=("Microsoft YaHei UI", 9, "bold"))
        self.level_label.pack(side=tk.LEFT, padx=5)
        self.xp_bar = ttk.Progressbar(r2, length=80, mode='determinate', maximum=100, value=0)
        self.xp_bar.pack(side=tk.LEFT, padx=2)
        self.xp_text = ttk.Label(r2, text="0/100 经验", font=("Microsoft YaHei UI", 8))
        self.xp_text.pack(side=tk.LEFT, padx=5)

        self.analyze_btn = ttk.Button(r2, text=f"{get_icon('sparkle', '✨')} 提交评分", command=self.on_analyze)
        self.analyze_btn.pack(side=tk.RIGHT, padx=5)

        # --- 题目/指导显示 ---
        self.prompt_frame = ttk.LabelFrame(self, text="题目 / 指导")
        self.prompt_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.word_label = ttk.Label(self.prompt_frame, textvariable=self.words_var, font=("Microsoft YaHei UI", 11), anchor="center", wraplength=800)
        self.word_label.pack(fill=tk.X, padx=10, pady=10)

        # --- 内容区域 ---
        content_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        content_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 写作区域
        write_frame = ttk.LabelFrame(content_pane, text="你的创作")
        content_pane.add(write_frame, weight=3)

        # 写作工具栏
        write_toolbar = ttk.Frame(write_frame)
        write_toolbar.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(write_toolbar, text=f"{get_icon('save', '💾')} 保存到灵感", command=self.on_save_idea).pack(side=tk.RIGHT)

        self.text_area = scrolledtext.ScrolledText(write_frame, font=("Consolas", 11), wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_area.bind("<KeyRelease>", self.on_text_change)

        # 反馈区域及操作按钮
        feedback_container = ttk.Frame(content_pane)
        content_pane.add(feedback_container, weight=1)

        self.feedback_frame = ttk.LabelFrame(feedback_container, text="AI 评分与分析")
        self.feedback_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        self.feedback_area = scrolledtext.ScrolledText(self.feedback_frame, font=("Microsoft YaHei UI", 10), wrap=tk.WORD, state="disabled", height=FEEDBACK_AREA_HEIGHT)
        self.feedback_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # AI操作按钮（反馈区底部）
        self.action_bar = ttk.Frame(feedback_container)
        self.action_bar.pack(fill=tk.X, pady=2)

        self.rewrite_btn = ttk.Button(self.action_bar, text=f"{get_icon('bot', '🤖')} 查看 AI 改写", command=self.on_rewrite, state="disabled")
        self.rewrite_btn.pack(side=tk.RIGHT, padx=5)

        self.polish_btn = ttk.Button(self.action_bar, text=f"{get_icon('wand', '🪄')} AI 润色", command=self.on_polish, state="disabled")
        self.polish_btn.pack(side=tk.RIGHT, padx=5)

        # 教练聊天区域
        self.chat_frame = ttk.LabelFrame(feedback_container, text=f"{get_icon('chat', '💬')} 咨询教练")
        self.chat_frame.pack(fill=tk.X, expand=False, side=tk.BOTTOM, pady=(5, 0))

        self.chat_input = ttk.Entry(self.chat_frame)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.chat_input.bind("<Return>", self.on_chat_submit)

        self.chat_btn = ttk.Button(self.chat_frame, text="提问", command=self.on_chat_submit)
        self.chat_btn.pack(side=tk.RIGHT, padx=5)

    def set_controller(self, controller):
        self.controller = controller
        if self.controller:
            levels = self.controller.get_levels()
            self.level_combo['values'] = levels
            if levels:
                self.level_combo.current(0)

            tags = self.controller.get_tags()
            self.tag_combo['values'] = [""] + tags
            self.tag_combo.current(0)

            # 设置类别
            cats = list(self.controller.manager.get_categories().keys())
            self.category_combo['values'] = cats
            if cats:
                self.category_combo.current(1)  # 默认选择创意训练
                self.on_category_change()
            self._update_tag_state()

    def select_mode_by_key(self, mode_key):
        if not self.controller:
            return

        categories = self.controller.manager.get_categories()
        for category, mode_keys in categories.items():
            if mode_key in mode_keys:
                self.category_var.set(category)
                self.on_category_change()
                mode_name = self.controller.manager.get_modes().get(mode_key, "")
                if mode_name:
                    self.mode_var.set(mode_name)
                    try:
                        idx = list(self.mode_combo['values']).index(mode_name)
                        self.mode_combo.current(idx)
                    except ValueError:
                        pass
                self._update_tag_state()
                return

        mode_name = self.controller.manager.get_modes().get(mode_key)
        if mode_name:
            self.mode_var.set(mode_name)
        self._update_tag_state()

    def on_category_change(self, event=None):
        cat = self.category_var.get()
        if not cat or not self.controller:
            return

        mode_keys = self.controller.manager.get_categories().get(cat, [])
        mode_names = [self.controller.manager.get_modes()[k] for k in mode_keys]
        self.mode_combo['values'] = mode_names
        if mode_names:
            self.mode_combo.current(0)
            self.on_mode_change()

    def on_mode_change(self, event=None):
        self.words_var.set("点击「生成题目」开始练习。")
        self._update_tag_state()
        if self.controller and hasattr(self.controller, "on_mode_changed"):
            self.controller.on_mode_changed()

    def _update_tag_state(self):
        mode_key = self.get_selected_mode_key()
        if mode_key in ("keywords", "brainstorm"):
            self.tag_combo.config(state="readonly")
        else:
            self.tag_var.set("")
            self.tag_combo.config(state="disabled")

    def on_generate(self):
        if self.controller:
            self.controller.generate_prompt()
            self.timer_btn.config(state="normal")
            self.reset_timer()

    def on_analyze(self):
        if self.controller:
            self.controller.analyze_content()

    def on_history(self):
        if self.controller:
            self.controller.show_history()

    def on_open_editor(self):
        if self.controller:
            self.controller.open_editor()

    def on_show_stats(self):
        if self.controller:
            self.controller.show_stats()

    def on_daily_quest(self):
        if self.controller:
            self.controller.load_daily_quest()

    def open_challenge_browser(self):
        if not self.controller:
            return
        dialog = Toplevel(self)
        dialog.title("训练挑战")
        dialog.geometry("700x500")

        tree = ttk.Treeview(dialog, columns=("Status", "Title", "Category", "Score"), show="headings")
        tree.heading("Status", text="状态")
        tree.heading("Title", text="挑战名称")
        tree.heading("Category", text="类别")
        tree.heading("Score", text="目标分数")
        tree.column("Status", width=80)
        tree.column("Title", width=250)
        tree.column("Category", width=150)
        tree.column("Score", width=80)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        challenges = self.controller.get_challenges()
        for c in challenges:
            status = "🔒 未解锁"
            if c["completed"]:
                status = "✅ 已完成"
            elif c["unlocked"]:
                status = "🔓 开放中"
            tree.insert("", tk.END, values=(status, c["title"], c["category"], c["min_score"]), tags=(c["id"],))

        def load_selected():
            item = tree.selection()
            if not item:
                return
            c_id = tree.item(item, "tags")[0]
            self.controller.load_challenge(c_id)
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="开始挑战", command=load_selected).pack(side=tk.RIGHT)
        tree.bind("<Double-1>", lambda e: load_selected())

    def on_rewrite(self):
        if self.controller:
            self.controller.ai_rewrite()

    def on_save_idea(self):
        content = self.get_content()
        if self.controller:
            self.controller.save_to_ideas(content)

    def on_chat_submit(self, event=None):
        msg = self.chat_input.get().strip()
        if msg and self.controller:
            self.controller.ask_coach(msg)
            self.chat_input.delete(0, tk.END)

    def on_polish(self):
        if self.controller:
            self.controller.ai_polish()

    def update_prompt_display(self, text):
        self.words_var.set(text)

    def set_content(self, text):
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text)

    def get_content(self):
        return self.text_area.get("1.0", tk.END).strip()

    def get_selected_mode_key(self):
        val = self.mode_var.get()
        for k, v in MODES.items():
            if v == val:
                return k
        return "keywords"

    def show_feedback(self, text):
        self.feedback_area.config(state="normal")
        self.feedback_area.delete("1.0", tk.END)
        self.feedback_area.insert("1.0", text)
        self.feedback_area.config(state="disabled")
        if self.ai_mode_enabled:
            self.rewrite_btn.config(state="normal")
            self.polish_btn.config(state="normal")
        else:
            self.rewrite_btn.config(state="disabled")
            self.polish_btn.config(state="disabled")

    def set_analyzing(self, state):
        self.is_analyzing = state
        state_str = "disabled" if state else "normal"
        self.analyze_btn.config(state=state_str, text="正在分析..." if state else f"{get_icon('sparkle', '✨')} 提交评分")
        self.generate_btn.config(state=state_str)

    def toggle_timer(self):
        if self.timer_running:
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        limit_str = self.time_limit_var.get()
        if limit_str == "无限制":
            return
        # 解析分钟数
        minutes = int(limit_str.split()[0])
        self.timer_seconds = minutes * 60
        self.timer_running = True
        self.timer_btn.config(text="停止")
        self._tick()

    def stop_timer(self):
        self.timer_running = False
        self.timer_btn.config(text="开始")

    def reset_timer(self):
        self.stop_timer()
        self.timer_var.set("00:00")

    def _tick(self):
        if not self.timer_running:
            return
        if self.timer_seconds > 0:
            self.timer_seconds -= 1
            m, s = divmod(self.timer_seconds, 60)
            self.timer_var.set(f"{m:02d}:{s:02d}")
            if self.timer_seconds < 60:
                self.timer_lbl.config(foreground="red")
            else:
                self.timer_lbl.config(foreground="blue")
            self.after(1000, self._tick)
        else:
            self.stop_timer()
            messagebox.showinfo("时间到!", "时间已到，请停止写作。")

    def apply_theme(self):
        # 使用编辑器颜色确保正确主题
        text_bg = self.theme_manager.get_color("editor_bg")
        text_fg = self.theme_manager.get_color("editor_fg")

        # 只对文本组件应用颜色以保持深色/浅色模式的可读性
        self.text_area.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        self.feedback_area.configure(bg=text_bg, fg=text_fg)

    def set_ai_mode_enabled(self, enabled: bool):
        self.ai_mode_enabled = bool(enabled)

        if self.ai_mode_enabled:
            if hasattr(self, "feedback_frame"):
                self.feedback_frame.configure(text="AI 评分与分析")
            # 显示AI功能
            self.rewrite_btn.pack(side=tk.RIGHT, padx=5)
            self.polish_btn.pack(side=tk.RIGHT, padx=5)
            self.chat_frame.pack(fill=tk.X, expand=False, side=tk.BOTTOM, pady=(5, 0))

            # 恢复状态
            self.analyze_btn.config(state="normal")
            self.set_analyzing(self.is_analyzing)
        else:
            if hasattr(self, "feedback_frame"):
                self.feedback_frame.configure(text="评分与分析（离线）")
            # 隐藏AI功能
            self.rewrite_btn.pack_forget()
            self.polish_btn.pack_forget()
            self.chat_frame.pack_forget()

            # 评分按钮应可用，因为有离线回退
            self.analyze_btn.config(state="normal")

    def on_text_change(self, event=None):
        content = self.text_area.get("1.0", tk.END).strip()
        count = len(content)
        target = 0
        try:
            target = int(self.target_word_var.get())
        except ValueError:
            pass

        if target > 0:
            self.word_count_lbl.config(text=f"字数: {count} / {target}")
            if count >= target:
                self.word_count_lbl.config(foreground="green")
            else:
                # 使用空字符串重置为默认主题颜色，避免深色主题兼容问题
                self.word_count_lbl.config(foreground="")
        else:
            self.word_count_lbl.config(text=f"字数: {count}")

    def update_gamification_ui(self, level, title, xp, next_xp):
        self.level_label.config(text=f"等级{level} {title}")
        self.xp_bar.config(maximum=next_xp, value=xp)
        self.xp_text.config(text=f"{xp}/{next_xp} 经验")

    def show_diff_dialog(self, original, new_text, title="AI 改写对比"):
        win = Toplevel(self)
        win.title(title)
        win.geometry("900x600")

        # 分割逻辑
        pane = ttk.PanedWindow(win, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)

        # 原始内容
        f1 = ttk.LabelFrame(pane, text="原始内容")
        pane.add(f1, weight=1)
        txt1 = scrolledtext.ScrolledText(f1, wrap=tk.WORD, font=("Consolas", 10))
        txt1.pack(fill=tk.BOTH, expand=True)
        txt1.insert("1.0", original)
        txt1.config(state="disabled")

        # 差异/新内容
        f2 = ttk.LabelFrame(pane, text="AI 改写（红色=删除，绿色=新增）")
        pane.add(f2, weight=1)
        txt2 = scrolledtext.ScrolledText(f2, wrap=tk.WORD, font=("Consolas", 10))
        txt2.pack(fill=tk.BOTH, expand=True)

        # 计算差异
        seq = difflib.SequenceMatcher(None, original, new_text)

        txt2.tag_config("add", background="#e6ffec", foreground="#006400")  # 浅绿
        txt2.tag_config("del", background="#ffebe9", foreground="#8b0000", overstrike=True)  # 浅红
        txt2.tag_config("common", foreground="black")

        # 在两个窗口中高亮变化
        txt1.config(state="normal")
        txt1.delete("1.0", tk.END)
        txt2.delete("1.0", tk.END)

        txt1.tag_config("del", background="#ffebe9", foreground="#8b0000")

        for opcode, a0, a1, b0, b1 in seq.get_opcodes():
            if opcode == 'equal':
                txt1.insert(tk.END, original[a0:a1])
                txt2.insert(tk.END, new_text[b0:b1])
            elif opcode == 'insert':
                # 新增的内容
                txt2.insert(tk.END, new_text[b0:b1], "add")
            elif opcode == 'delete':
                # 删除的内容
                txt1.insert(tk.END, original[a0:a1], "del")
            elif opcode == 'replace':
                # 替换的内容
                txt1.insert(tk.END, original[a0:a1], "del")
                txt2.insert(tk.END, new_text[b0:b1], "add")

        txt1.config(state="disabled")
        txt2.config(state="disabled")

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.winfo_toplevel(), topic_id or "training")
