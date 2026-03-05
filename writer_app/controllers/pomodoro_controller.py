import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

class PomodoroController:
    MODE_WORK = "work"
    MODE_SHORT_BREAK = "short_break"
    MODE_LONG_BREAK = "long_break"

    def __init__(self, root, config_manager, ui_callback, gamification_manager=None):
        self.root = root
        self.config_manager = config_manager
        self.ui_callback = ui_callback # function(text, color)
        self.gamification_manager = gamification_manager
        
        self.current_mode = self.MODE_WORK
        self.is_running = False
        self.timer_id = None
        
        # Load settings
        self.work_time = int(self.config_manager.get("pomo_work_time", 25))
        self.short_break_time = int(self.config_manager.get("pomo_short_break_time", 5))
        self.long_break_time = int(self.config_manager.get("pomo_long_break_time", 15))
        
        self.remaining_seconds = self.work_time * 60
        self.cycles_completed = 0
        
        self.update_ui()

    def toggle(self, event=None):
        if self.is_running:
            self.pause()
        else:
            self.start()

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.tick()
            self.update_ui()

    def pause(self):
        self.is_running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.update_ui()

    def reset(self, event=None):
        self.pause()
        self.remaining_seconds = self._get_duration(self.current_mode) * 60
        self.update_ui()

    def set_mode(self, mode):
        self.pause()
        self.current_mode = mode
        self.remaining_seconds = self._get_duration(mode) * 60
        self.update_ui()

    def tick(self):
        if not self.is_running:
            return

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_ui()
            # Adjust for drift? Simple after(1000) is usually okay for this.
            self.timer_id = self.root.after(1000, self.tick)
        else:
            self.complete_session()

    def complete_session(self):
        self.is_running = False
        self.timer_id = None
        self.update_ui()
        
        # Play sound? (Tkinter bell is simple)
        self.root.bell()
        
        if self.current_mode == self.MODE_WORK:
            self.cycles_completed += 1
            
            # Record Gamification
            if self.gamification_manager:
                self.gamification_manager.record_pomodoro()
            
            if self.cycles_completed % 4 == 0:
                next_mode = self.MODE_LONG_BREAK
                msg = f"恭喜完成第 {self.cycles_completed} 个番茄钟！\n该休息一下了（长休息 {self.long_break_time} 分钟）。"
            else:
                next_mode = self.MODE_SHORT_BREAK
                msg = f"番茄钟完成！\n休息一下吧（短休息 {self.short_break_time} 分钟）。"
        else:
            next_mode = self.MODE_WORK
            msg = "休息结束，准备开始工作！"
        
        # Bring window to front if possible
        self.root.deiconify()
        self.root.lift()
        
        # Show message
        messagebox.showinfo("番茄闹钟", msg, parent=self.root)
        
        # Auto-switch mode
        self.set_mode(next_mode)

    def _get_duration(self, mode):
        if mode == self.MODE_WORK: return self.work_time
        if mode == self.MODE_SHORT_BREAK: return self.short_break_time
        if mode == self.MODE_LONG_BREAK: return self.long_break_time
        return 25

    def update_ui(self):
        mins, secs = divmod(self.remaining_seconds, 60)
        time_str = f"{mins:02}:{secs:02}"
        
        # Determine Color and Text
        if self.current_mode == self.MODE_WORK:
            mode_text = "Work"
            fg_color = "#D32F2F" if self.is_running else "black" # Red when running
        elif self.current_mode == self.MODE_SHORT_BREAK:
            mode_text = "Short"
            fg_color = "#388E3C" if self.is_running else "#2E7D32" # Green
        else:
            mode_text = "Long"
            fg_color = "#1976D2" if self.is_running else "#1565C0" # Blue
            
        full_text = f"{mode_text} {time_str}"
        self.ui_callback(full_text, fg_color)

    def open_settings(self):
        d = tk.Toplevel(self.root)
        d.title("番茄闹钟设置")
        d.geometry("300x250")
        d.resizable(False, False)
        
        pad_opts = {'padx': 10, 'pady': 5}
        
        tk.Label(d, text="工作时长 (分钟):").pack(anchor=tk.W, **pad_opts)
        work_var = tk.StringVar(value=str(self.work_time))
        tk.Entry(d, textvariable=work_var).pack(fill=tk.X, **pad_opts)
        
        tk.Label(d, text="短休息 (分钟):").pack(anchor=tk.W, **pad_opts)
        short_var = tk.StringVar(value=str(self.short_break_time))
        tk.Entry(d, textvariable=short_var).pack(fill=tk.X, **pad_opts)
        
        tk.Label(d, text="长休息 (分钟):").pack(anchor=tk.W, **pad_opts)
        long_var = tk.StringVar(value=str(self.long_break_time))
        tk.Entry(d, textvariable=long_var).pack(fill=tk.X, **pad_opts)
        
        def save():
            try:
                w = int(work_var.get())
                s = int(short_var.get())
                l = int(long_var.get())
                
                self.work_time = w
                self.short_break_time = s
                self.long_break_time = l
                
                self.config_manager.set("pomo_work_time", w)
                self.config_manager.set("pomo_short_break_time", s)
                self.config_manager.set("pomo_long_break_time", l)
                
                # If timer is not running, update current remaining time to match new setting
                if not self.is_running:
                    self.remaining_seconds = self._get_duration(self.current_mode) * 60
                    self.update_ui()
                
                d.destroy()
                messagebox.showinfo("提示", "设置已保存", parent=self.root)
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字", parent=d)
        
        ttk.Button(d, text="保存", command=save).pack(pady=15)
        
        # Center dialog
        d.transient(self.root)
        d.grab_set()
        self.root.wait_window(d)