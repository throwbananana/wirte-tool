"""
休闲主页面板 (Leisure Home Panel)
展示每日签到与任务进度
"""
import tkinter as tk
from datetime import datetime


class LeisureHomePanel(tk.Frame):
    def __init__(self, parent, assistant, **kwargs):
        super().__init__(parent, **kwargs)
        self.assistant = assistant
        self._event_rotation_job = None
        self._event_rotation_items = []
        self._event_rotation_index = 0
        self._task_completion_state = {}
        self._last_progress_count = None
        self.colors = {
            "bg": "#2B2F36",
            "card": "#313640",
            "accent": "#4CAF50",
            "accent_soft": "#6FCF97",
            "text": "#E6E6E6",
            "muted": "#A8B0BD",
            "border": "#3A404C",
            "warn": "#FFB300",
        }
        self.configure(bg=self.colors["bg"])

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        title_frame = tk.Frame(self, bg=self.colors["accent"], height=22)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="🎈 休闲主页",
            font=("Microsoft YaHei UI", 8, "bold"),
            bg=self.colors["accent"],
            fg="white"
        ).pack(side=tk.LEFT, padx=6)

        # 模式切换
        mode_frame = tk.Frame(self, bg=self.colors["bg"])
        mode_frame.pack(fill=tk.X, padx=8, pady=(6, 2))
        tk.Label(
            mode_frame,
            text="模式",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["bg"],
            fg=self.colors["muted"]
        ).pack(side=tk.LEFT)

        self.mode_buttons = {}
        self.mode_buttons["leisure"] = self._make_mode_button(
            mode_frame, "休闲", self.assistant._enter_leisure_mode
        )
        self.mode_buttons["leisure"].pack(side=tk.LEFT, padx=(6, 4))

        self.mode_buttons["training"] = self._make_mode_button(
            mode_frame, "训练", lambda: self.assistant._open_mode("training")
        )
        self.mode_buttons["training"].pack(side=tk.LEFT, padx=(0, 4))

        self.mode_buttons["reverse_engineering"] = self._make_mode_button(
            mode_frame, "推理", lambda: self.assistant._open_mode("reverse_engineering")
        )
        self.mode_buttons["reverse_engineering"].pack(side=tk.LEFT, padx=(0, 4))

        self.mode_hint = tk.Label(
            self,
            text="",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["bg"],
            fg=self.colors["muted"]
        )
        self.mode_hint.pack(anchor=tk.W, padx=8, pady=(2, 4))

        # 状态条
        status_frame = tk.Frame(self, bg=self.colors["bg"])
        status_frame.pack(fill=tk.X, padx=8, pady=(6, 2))

        self.affection_chip = self._make_chip(status_frame, "好感", "0")
        self.affection_chip.pack(side=tk.LEFT, padx=(0, 6))
        self.level_chip = self._make_chip(status_frame, "等级", "1")
        self.level_chip.pack(side=tk.LEFT, padx=(0, 6))
        self.coin_chip = self._make_chip(status_frame, "金币", "0")
        self.coin_chip.pack(side=tk.LEFT)
        self.mood_chip = self._make_chip(status_frame, "心情", "😊")
        self.mood_chip.pack(side=tk.LEFT, padx=(6, 0))

        # 签到栏
        checkin_frame = tk.Frame(self, bg=self.colors["card"], highlightthickness=1,
                                 highlightbackground=self.colors["border"])
        checkin_frame.pack(fill=tk.X, padx=8, pady=(6, 2))

        tk.Label(
            checkin_frame,
            text="每日签到",
            font=("Microsoft YaHei UI", 9),
            bg=self.colors["card"],
            fg=self.colors["text"]
        ).pack(side=tk.LEFT)

        self.checkin_status = tk.Label(
            checkin_frame,
            text="",
            font=("Microsoft YaHei UI", 9),
            bg=self.colors["card"],
            fg=self.colors["warn"]
        )
        self.checkin_status.pack(side=tk.LEFT, padx=8)

        self.checkin_btn = tk.Label(
            checkin_frame,
            text="签到",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["border"],
            fg="white",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        self.checkin_btn.pack(side=tk.RIGHT)
        self.checkin_btn.bind("<Button-1>", lambda e: self.assistant._manual_daily_checkin())
        self._bind_hover(self.checkin_btn, self.colors["accent"])

        # 任务区
        task_title = tk.Label(
            self,
            text="今日任务",
            font=("Microsoft YaHei UI", 9, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"]
        )
        task_title.pack(anchor=tk.W, padx=8, pady=(6, 2))

        self.tasks_container = tk.Frame(self, bg=self.colors["bg"])
        self.tasks_container.pack(fill=tk.X, padx=8)

        # 今日事件
        event_frame = tk.Frame(self, bg=self.colors["card"], highlightthickness=1,
                               highlightbackground=self.colors["border"])
        event_frame.pack(fill=tk.X, padx=8, pady=(6, 2))
        header = tk.Frame(event_frame, bg=self.colors["card"])
        header.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Label(
            header,
            text="今日小事件",
            font=("Microsoft YaHei UI", 9, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        ).pack(side=tk.LEFT)

        self.event_badge = tk.Label(
            header,
            text="今日 0",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["border"],
            fg=self.colors["muted"],
            padx=6,
            pady=2
        )
        self.event_badge.pack(side=tk.RIGHT)

        self.event_message = tk.Label(
            event_frame,
            text="",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["card"],
            fg=self.colors["muted"],
            wraplength=260,
            justify=tk.LEFT
        )
        self.event_message.pack(anchor=tk.W, padx=8, pady=(2, 6))

        self.event_meta = tk.Label(
            event_frame,
            text="",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["card"],
            fg=self.colors["muted"]
        )
        self.event_meta.pack(anchor=tk.W, padx=8, pady=(0, 6))

        self.event_reward = tk.Label(
            event_frame,
            text="",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["card"],
            fg=self.colors["muted"]
        )
        self.event_reward.pack(anchor=tk.W, padx=8, pady=(0, 6))

        event_actions = tk.Frame(event_frame, bg=self.colors["card"])
        event_actions.pack(fill=tk.X, padx=8, pady=(0, 6))

        self.event_history_btn = tk.Label(
            event_actions,
            text="查看历史",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["border"],
            fg="white",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        self.event_history_btn.pack(side=tk.LEFT)
        self.event_history_btn.bind("<Button-1>", lambda e: self.assistant._show_event_history())
        self._bind_hover(self.event_history_btn, self.colors["accent"])

        self.event_story_btn = tk.Label(
            event_actions,
            text="开启剧情",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["border"],
            fg="white",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        self.event_story_btn.pack(side=tk.LEFT, padx=(6, 0))
        self.event_story_btn.bind("<Button-1>", lambda e: self.assistant._start_leisure_story())
        self._bind_hover(self.event_story_btn, self.colors["accent_soft"])

        self.event_btn = tk.Label(
            event_actions,
            text="触发事件",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["border"],
            fg="white",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        self.event_btn.pack(side=tk.RIGHT)
        self.event_btn.bind("<Button-1>", lambda e: self.assistant._trigger_school_event())
        self._bind_hover(self.event_btn, self.colors["accent"])

        progress_frame = tk.Frame(self, bg=self.colors["bg"])
        progress_frame.pack(fill=tk.X, padx=8, pady=(6, 2))
        tk.Label(
            progress_frame,
            text="今日进度",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["bg"],
            fg=self.colors["muted"]
        ).pack(side=tk.LEFT)
        self.progress_label = tk.Label(
            progress_frame,
            text="0/0",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["bg"],
            fg=self.colors["muted"]
        )
        self.progress_label.pack(side=tk.RIGHT)

        self.progress_bar = tk.Canvas(
            self,
            width=160,
            height=6,
            highlightthickness=0,
            bg=self.colors["bg"]
        )
        self.progress_bar.pack(fill=tk.X, padx=8)

        # 快捷操作
        action_frame = tk.Frame(self, bg=self.colors["bg"])
        action_frame.pack(fill=tk.X, padx=8, pady=(6, 2))

        self._make_action_button(action_frame, "👋 打招呼", self.assistant._quick_greet).pack(side=tk.LEFT, padx=(0, 6))
        self._make_action_button(action_frame, "🍪 投喂", self.assistant._feed_assistant).pack(side=tk.LEFT, padx=(0, 6))
        self._make_action_button(action_frame, "🎮 小游戏", self.assistant._quick_start_game).pack(side=tk.LEFT)

        # 奖励区
        self.claim_frame = tk.Frame(self, bg=self.colors["bg"])
        self.claim_frame.pack(fill=tk.X, padx=8, pady=(6, 6))

        self.claim_btn = tk.Label(
            self.claim_frame,
            text="完成任务领取奖励",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["border"],
            fg=self.colors["muted"],
            padx=8,
            pady=4
        )
        self.claim_btn.pack(side=tk.RIGHT)

        # 模式入口说明卡
        entry_frame = tk.Frame(self, bg=self.colors["card"], highlightthickness=1,
                               highlightbackground=self.colors["border"])
        entry_frame.pack(fill=tk.X, padx=8, pady=(6, 6))

        tk.Label(
            entry_frame,
            text="模式入口",
            font=("Microsoft YaHei UI", 9, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        ).pack(anchor=tk.W, padx=8, pady=(6, 0))

        entry_row = tk.Frame(entry_frame, bg=self.colors["card"])
        entry_row.pack(fill=tk.X, padx=8, pady=(4, 6))

        self.training_entry = self._make_entry_button(
            entry_row,
            "✍ 训练 · 3分钟",
            "小练习，快速提升写作手感",
            lambda: self.assistant._open_mode("training")
        )
        self.training_entry.pack(side=tk.LEFT, padx=(0, 6))

        self.reverse_entry = self._make_entry_button(
            entry_row,
            "🕵 推理 · 拆解",
            "反推结构，学习他人写法",
            lambda: self.assistant._open_mode("reverse_engineering")
        )
        self.reverse_entry.pack(side=tk.LEFT)

    def refresh(self):
        self._refresh_checkin()
        self._refresh_tasks()
        self._refresh_mode()
        self._refresh_event()

    def _refresh_checkin(self):
        today = datetime.now().strftime("%Y-%m-%d")
        last_check = self.assistant.pet_system.data.last_daily_check
        if last_check == today:
            streak = self.assistant.pet_system.data.daily_streak
            suffix = f" · 连续 {streak} 天" if streak else ""
            self.checkin_status.configure(text=f"已签到{suffix}")
            self.checkin_btn.configure(text="已签到", bg="#2E7D32", fg="white")
            self._unbind_button(self.checkin_btn)
        else:
            streak = self.assistant.pet_system.data.daily_streak
            suffix = f" · 连续 {streak} 天" if streak else ""
            self.checkin_status.configure(text=f"未签到{suffix}")
            self.checkin_btn.configure(text="签到", bg=self.colors["border"], fg="white")
            self.checkin_btn.bind("<Button-1>", lambda e: self.assistant._manual_daily_checkin())
            self._bind_hover(self.checkin_btn, self.colors["accent"])

        stats = self.assistant.pet_system.get_stats()
        self.affection_chip.label.configure(text=f"好感 {stats.get('affection', 0)}")
        self.level_chip.label.configure(text=f"Lv.{stats.get('level', 1)}")
        self.coin_chip.label.configure(text=f"金币 {stats.get('coins', 0)}")
        mood_emoji = stats.get("mood_emoji", "😊")
        mood_map = {
            "GREAT": "极好",
            "GOOD": "开心",
            "NORMAL": "平静",
            "BAD": "低落",
            "TERRIBLE": "极差",
        }
        mood_level = stats.get("mood_level", "GOOD")
        mood_name = mood_map.get(mood_level, mood_level)
        self.mood_chip.label.configure(text=f"{mood_emoji} {mood_name}")

    def _refresh_tasks(self):
        for child in self.tasks_container.winfo_children():
            child.destroy()

        status = self.assistant.pet_system.get_daily_task_status()
        prev_completed = dict(self._task_completion_state)
        allow_animate = bool(prev_completed)
        any_new_complete = False
        new_completed_labels = []
        action_map = {
            "greet": self.assistant._quick_greet,
            "feed": self.assistant._feed_assistant,
            "game": self.assistant._quick_start_game,
        }

        for task in status.get("tasks", []):
            row = tk.Frame(self.tasks_container, bg=self.colors["card"], highlightthickness=1,
                           highlightbackground=self.colors["border"])
            row.pack(fill=tk.X, pady=2)

            icon = "✅" if task["completed"] else "○"
            icon_label = tk.Label(
                row,
                text=icon,
                font=("Microsoft YaHei UI", 9),
                bg=self.colors["card"],
                fg=self.colors["accent_soft"] if task["completed"] else self.colors["muted"],
                width=2
            )
            icon_label.pack(side=tk.LEFT)

            tk.Label(
                row,
                text=task["label"],
                font=("Microsoft YaHei UI", 9),
                bg=self.colors["card"],
                fg=self.colors["text"]
            ).pack(side=tk.LEFT)

            progress_text = f"{min(task['progress'], task['target'])}/{task['target']}"
            tk.Label(
                row,
                text=progress_text,
                font=("Microsoft YaHei UI", 8),
                bg=self.colors["card"],
                fg=self.colors["muted"]
            ).pack(side=tk.LEFT, padx=6)

            action = action_map.get(task["id"])
            btn = tk.Label(
                row,
                text="去完成" if not task["completed"] else "已完成",
                font=("Microsoft YaHei UI", 8),
                bg=self.colors["border"] if not task["completed"] else "#2E7D32",
                fg="white",
                padx=6,
                pady=2,
                cursor="hand2" if not task["completed"] else ""
            )
            btn.pack(side=tk.RIGHT)
            if not task["completed"] and action:
                btn.bind("<Button-1>", lambda e, cb=action: cb())
                self._bind_hover(btn, self.colors["accent"])

            if allow_animate and task["completed"] and not prev_completed.get(task["id"], False):
                any_new_complete = True
                self._animate_task_row(row, icon_label)
                new_completed_labels.append(task["label"])

        self._task_completion_state = {t["id"]: t["completed"] for t in status.get("tasks", [])}
        self._refresh_claim(status)
        self._refresh_progress(status)
        if any_new_complete:
            self._pulse_label(self.progress_label)
            self._show_task_complete_popup(new_completed_labels)

    def _refresh_mode(self):
        active = self.assistant._get_active_mode()
        for key, btn in self.mode_buttons.items():
            if key == active:
                btn.configure(bg=self.colors["accent_soft"], fg="#1B1B1B")
            else:
                btn.configure(bg=self.colors["border"], fg="white")

        mode_hints = {
            "leisure": "轻量任务与陪伴互动，适合放松一下。",
            "training": "3分钟小练习，快速提升写作技巧。",
            "reverse_engineering": "拆解文本结构，反推学习与推理。",
        }
        self.mode_hint.configure(text=mode_hints.get(active, ""))

    def _refresh_event(self):
        try:
            message = self.assistant._get_daily_event_hint()
        except Exception:
            message = "今天也要多和我互动哦～"
        self.event_message.configure(text=message)

        rotation_items = [
            message,
            "完成今日任务可领取奖励哦。",
            "点“开启剧情”可以触发小故事。",
            "小游戏也能提升心情~",
        ]
        self._set_event_rotation(rotation_items)
        meta = self.assistant._get_daily_event_meta()
        source = meta.get("source", "system")
        time_text = meta.get("timestamp", "")
        if "T" in time_text:
            time_text = time_text.split("T")[-1][:5]
        self.event_meta.configure(text=f"来源: {source} · {time_text}")

        try:
            reward_hint = self.assistant._get_event_reward_hint()
        except Exception:
            reward_hint = "可能奖励：相册 / 成就 / 好感"
        self.event_reward.configure(text=reward_hint)

        today_count, total = self.assistant._get_event_counts()
        self.event_badge.configure(text=f"今日 {today_count} / 总计 {total}")

    def _set_event_rotation(self, items):
        # 去重保序
        cleaned = []
        seen = set()
        for item in items:
            if not item or item in seen:
                continue
            cleaned.append(item)
            seen.add(item)

        self._event_rotation_items = cleaned
        self._event_rotation_index = 0

        if self._event_rotation_job:
            try:
                self.after_cancel(self._event_rotation_job)
            except Exception:
                pass
            self._event_rotation_job = None

        if len(cleaned) > 1:
            self._event_rotation_job = self.after(7000, self._rotate_event_message)

    def _rotate_event_message(self):
        if not self.winfo_exists():
            return
        if not self._event_rotation_items:
            return
        self._event_rotation_index = (self._event_rotation_index + 1) % len(self._event_rotation_items)
        self.event_message.configure(text=self._event_rotation_items[self._event_rotation_index])
        self._event_rotation_job = self.after(7000, self._rotate_event_message)

    def _refresh_claim(self, status):
        reward = status.get("reward", {})
        reward_text = f"领取奖励 (+{reward.get('xp', 0)}XP +{reward.get('coins', 0)}金币)"

        if status.get("all_completed") and not status.get("claimed"):
            self.claim_btn.configure(
                text=reward_text,
                bg=self.colors["warn"],
                fg="#1B1B1B",
                cursor="hand2"
            )
            self.claim_btn.bind("<Button-1>", lambda e: self.assistant._claim_daily_task_reward())
        elif status.get("claimed"):
            self.claim_btn.configure(
                text="今日奖励已领取",
                bg=self.colors["border"],
                fg=self.colors["muted"],
                cursor=""
            )
            self._unbind_button(self.claim_btn)
        else:
            self.claim_btn.configure(
                text="完成任务领取奖励",
                bg=self.colors["border"],
                fg=self.colors["muted"],
                cursor=""
            )
            self._unbind_button(self.claim_btn)

    def _refresh_progress(self, status):
        tasks = status.get("tasks", [])
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("completed")) if tasks else 0
        ratio = (completed / total) if total else 0

        self.progress_label.configure(text=f"{completed}/{total}")

        if self._last_progress_count is None:
            self._last_progress_count = completed
        elif completed > self._last_progress_count:
            self._animate_progress_count(self._last_progress_count, completed, total)
            self._last_progress_count = completed
        else:
            self._last_progress_count = completed

        self.progress_bar.delete("all")
        width = self.progress_bar.winfo_reqwidth()
        height = 6
        self.progress_bar.create_rectangle(
            0, 0, width, height,
            fill=self.colors["border"],
            outline=""
        )
        if ratio > 0:
            fill_width = int(width * ratio)
            self.progress_bar.create_rectangle(
                0, 0, fill_width, height,
                fill=self.colors["accent_soft"],
                outline=""
            )

    @staticmethod
    def _unbind_button(widget):
        try:
            widget.unbind("<Button-1>")
            widget.unbind("<Enter>")
            widget.unbind("<Leave>")
        except Exception:
            pass

    def _make_chip(self, parent, text, value):
        frame = tk.Frame(parent, bg=self.colors["card"], highlightthickness=1,
                         highlightbackground=self.colors["border"])
        label = tk.Label(
            frame,
            text=f"{text} {value}",
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["card"],
            fg=self.colors["text"],
            padx=6,
            pady=2
        )
        label.pack()
        frame.label = label
        return frame

    def _make_action_button(self, parent, text, callback):
        btn = tk.Label(
            parent,
            text=text,
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["border"],
            fg="white",
            padx=8,
            pady=4,
            cursor="hand2"
        )
        btn.bind("<Button-1>", lambda e: callback())
        self._bind_hover(btn, self.colors["accent"])
        return btn

    def _make_entry_button(self, parent, title, subtitle, callback):
        wrapper = tk.Frame(parent, bg=self.colors["card"])
        btn = tk.Label(
            wrapper,
            text=title,
            font=("Microsoft YaHei UI", 8, "bold"),
            bg=self.colors["border"],
            fg="white",
            padx=8,
            pady=4,
            cursor="hand2"
        )
        btn.pack(fill=tk.X)
        btn.bind("<Button-1>", lambda e: callback())
        self._bind_hover(btn, self.colors["accent_soft"])

        tk.Label(
            wrapper,
            text=subtitle,
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["card"],
            fg=self.colors["muted"],
            padx=6,
            pady=2
        ).pack(anchor=tk.W)
        return wrapper

    def _make_mode_button(self, parent, text, callback):
        btn = tk.Label(
            parent,
            text=text,
            font=("Microsoft YaHei UI", 8),
            bg=self.colors["border"],
            fg="white",
            padx=10,
            pady=2,
            cursor="hand2"
        )
        btn.bind("<Button-1>", lambda e: callback())
        self._bind_hover(btn, self.colors["accent_soft"])
        return btn

    def _bind_hover(self, widget, hover_bg):
        def on_enter(_):
            widget.configure(bg=hover_bg)
        def on_leave(_):
            widget.configure(bg=self.colors["border"])
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _animate_task_row(self, row, icon_label):
        flash_color = "#3E4A3F"
        base_fg = self.colors["accent_soft"]
        base_font = ("Microsoft YaHei UI", 9)
        big_font = ("Microsoft YaHei UI", 11, "bold")

        original_bg = {}
        try:
            original_bg[row] = row.cget("bg")
        except Exception:
            original_bg[row] = None

        for child in row.winfo_children():
            try:
                original_bg[child] = child.cget("bg")
            except Exception:
                original_bg[child] = None

        icon_label.configure(text="✨", font=big_font, fg=base_fg)
        row.configure(bg=flash_color)
        for child in row.winfo_children():
            try:
                child.configure(bg=flash_color)
            except Exception:
                pass

        def step2():
            if not row.winfo_exists():
                return
            icon_label.configure(text="✅", font=base_font, fg=base_fg)
            row.configure(bg=original_bg.get(row) or row.cget("bg"))
            for child in row.winfo_children():
                try:
                    child.configure(bg=original_bg.get(child) or child.cget("bg"))
                except Exception:
                    pass

        def step3():
            if not row.winfo_exists():
                return
            row.configure(bg=flash_color)
            for child in row.winfo_children():
                try:
                    child.configure(bg=flash_color)
                except Exception:
                    pass

        def step4():
            if not row.winfo_exists():
                return
            row.configure(bg=original_bg.get(row) or row.cget("bg"))
            for child in row.winfo_children():
                try:
                    child.configure(bg=original_bg.get(child) or child.cget("bg"))
                except Exception:
                    pass

        self.after(200, step2)
        self.after(320, step3)
        self.after(440, step4)

    def _pulse_label(self, label):
        try:
            label.configure(fg=self.colors["accent_soft"], font=("Microsoft YaHei UI", 9, "bold"))
        except Exception:
            return

        def reset():
            if not label.winfo_exists():
                return
            label.configure(fg=self.colors["muted"], font=("Microsoft YaHei UI", 8))

        self.after(400, reset)

    def _show_task_complete_popup(self, labels):
        if not labels:
            return
        text = " / ".join(labels[:3])
        detail = f"完成：{text}"
        if len(labels) > 3:
            detail += f" 等 {len(labels)} 项"
        if hasattr(self.assistant, "_show_reward_card"):
            self.assistant._show_reward_card("任务完成", detail, accent="#6FCF97", icon="✅")

    def _animate_progress_count(self, start, end, total):
        if start >= end:
            return

        steps = max(1, end - start)
        interval = 120

        def tick(value):
            if not self.progress_label.winfo_exists():
                return
            self.progress_label.configure(text=f"{value}/{total}")
            if value < end:
                self.after(interval, lambda: tick(value + 1))

        tick(start)
