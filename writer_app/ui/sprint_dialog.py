import tkinter as tk
from tkinter import ttk, messagebox
import time

class WordSprintDialog(tk.Toplevel):
    def __init__(self, parent, editor, gamification_manager, config_manager=None):
        super().__init__(parent)
        self.title("写作冲刺 (Word Sprint)")
        self.geometry("400x350")
        self.editor = editor
        self.gamification_manager = gamification_manager
        self.config_manager = config_manager

        self.start_word_count = self.editor.get_word_count()
        self.duration_mins = 15
        self.remaining_seconds = 0
        self.running = False
        self._focus_mode_was_enabled = False  # Track if focus mode was enabled before sprint

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.setup_ui()
        
    def setup_ui(self):
        self.main_frame = ttk.Frame(self, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Setup Phase
        self.setup_frame = ttk.Frame(self.main_frame)
        self.setup_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.setup_frame, text="准备好进行一次高强度的写作冲刺了吗?", font=("Arial", 12)).pack(pady=10)
        
        time_frame = ttk.Frame(self.setup_frame)
        time_frame.pack(pady=10)
        ttk.Label(time_frame, text="时长 (分钟):").pack(side=tk.LEFT)
        self.time_var = tk.IntVar(value=15)
        ttk.Spinbox(time_frame, from_=1, to=120, textvariable=self.time_var, width=5).pack(side=tk.LEFT, padx=5)

        # Focus mode option
        self.focus_mode_var = tk.BooleanVar(value=self._get_auto_focus_setting())
        focus_frame = ttk.Frame(self.setup_frame)
        focus_frame.pack(pady=5)
        ttk.Checkbutton(
            focus_frame, text="冲刺时启用专注模式",
            variable=self.focus_mode_var
        ).pack(side=tk.LEFT)

        ttk.Button(self.setup_frame, text="开始冲刺!", command=self.start_sprint).pack(pady=20)
        
        # Running Phase
        self.run_frame = ttk.Frame(self.main_frame)
        
        self.timer_label = ttk.Label(self.run_frame, text="00:00", font=("Arial", 36, "bold"), foreground="#E91E63")
        self.timer_label.pack(pady=20)
        
        self.stats_label = ttk.Label(self.run_frame, text="当前产出: 0 字", font=("Arial", 14))
        self.stats_label.pack(pady=10)
        
        ttk.Button(self.run_frame, text="放弃 / 结束", command=self.stop_sprint).pack(pady=10)
        
        # Result Phase
        self.result_frame = ttk.Frame(self.main_frame)
        self.result_label = ttk.Label(self.result_frame, text="", font=("Arial", 12), justify=tk.CENTER)
        self.result_label.pack(pady=20)
        ttk.Button(self.result_frame, text="关闭", command=self.destroy).pack(pady=10)

    def _get_auto_focus_setting(self):
        """Get auto-focus setting from config."""
        if self.config_manager:
            return self.config_manager.get("focus_mode_auto_in_sprint", True)
        return True

    def start_sprint(self):
        self.duration_mins = self.time_var.get()
        self.remaining_seconds = self.duration_mins * 60
        self.start_word_count = self.editor.get_word_count()

        # Enable focus mode if requested
        if self.focus_mode_var.get():
            self._focus_mode_was_enabled = self.editor.focus_mode
            if not self._focus_mode_was_enabled:
                self.editor.toggle_focus_mode(True, save_config=False)

        self.setup_frame.pack_forget()
        self.run_frame.pack(fill=tk.BOTH, expand=True)

        self.running = True
        self.update_timer()

    def update_timer(self):
        if not self.running:
            return
            
        if self.remaining_seconds <= 0:
            self.finish_sprint()
            return
            
        mins, secs = divmod(self.remaining_seconds, 60)
        self.timer_label.config(text=f"{mins:02d}:{secs:02d}")
        
        # Update word count
        current = self.editor.get_word_count()
        diff = current - self.start_word_count
        self.stats_label.config(text=f"当前产出: {diff} 字")
        
        self.remaining_seconds -= 1
        self.after(1000, self.update_timer)

    def stop_sprint(self):
        if messagebox.askyesno("确认", "确定要提前结束冲刺吗?"):
            self.finish_sprint()

    def finish_sprint(self):
        self.running = False
        self.run_frame.pack_forget()
        self.result_frame.pack(fill=tk.BOTH, expand=True)

        # Restore focus mode to previous state
        if self.focus_mode_var.get() and not self._focus_mode_was_enabled:
            self.editor.toggle_focus_mode(False, save_config=False)

        current = self.editor.get_word_count()
        words = current - self.start_word_count
        words = max(0, words)

        # Calculate rewards
        # Base: 1 point per 10 words
        # Bonus: 50 points for finishing
        points = (words // 10) + 50

        self.gamification_manager.add_points(points, f"完成 {self.duration_mins} 分钟写作冲刺")
        self.gamification_manager.record_words(words)

        msg = f"冲刺结束!\n\n时长: {self.duration_mins} 分钟\n产出: {words} 字\n获得经验: {points} XP"
        self.result_label.config(text=msg)

    def on_close(self):
        if self.running:
            if messagebox.askyesno("警告", "冲刺正在进行中，关闭将丢失进度。确定退出?"):
                self.running = False
                self.destroy()
        else:
            self.destroy()
