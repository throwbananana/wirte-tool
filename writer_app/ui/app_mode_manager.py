import time
import tkinter as tk
from tkinter import ttk, messagebox

from writer_app.core.event_bus import get_event_bus, Events
from writer_app.ui.dialogs import FocusModeSettingsDialog
from writer_app.ui.sprint_dialog import WordSprintDialog


class AppModeManager:
    def __init__(self, app):
        self.app = app
        self.sound_var = None

    def toggle_focus_mode(self):
        """Toggle focus mode on/off with enhanced features."""
        sc = getattr(self.app, "script_controller", None)
        if not sc or not hasattr(sc, "script_editor"):
            messagebox.showinfo("提示", "请先确保剧本写作模块可用")
            return

        editor = sc.script_editor
        current = editor.focus_mode
        new_state = not current
        editor.toggle_focus_mode(new_state)

        if new_state:
            level_names = {
                "line": "行",
                "sentence": "句子",
                "paragraph": "段落",
                "dialogue": "对话",
            }
            level = editor._focus_level
            level_name = level_names.get(level, level)
            self.app.status_var.set(f"专注模式: 开启 | 级别: {level_name} | F10切换 | Ctrl+Shift+F循环级别")
            self._update_focus_indicator(True)
        else:
            self.app.status_var.set("专注模式: 关闭")
            self._update_focus_indicator(False)

    def set_focus_level(self, level):
        """Set focus level: line, sentence, paragraph, or dialogue."""
        sc = getattr(self.app, "script_controller", None)
        if not sc or not hasattr(sc, "script_editor"):
            messagebox.showinfo("提示", "请先确保剧本写作模块可用")
            return

        editor = sc.script_editor
        editor.set_focus_level(level)

        level_names = {
            "line": "行",
            "sentence": "句子",
            "paragraph": "段落",
            "dialogue": "对话",
        }
        level_name = level_names.get(level, level)
        self.app.status_var.set(f"专注级别已切换为: {level_name}")

        if not editor.focus_mode:
            editor.toggle_focus_mode(True)
            self._update_focus_indicator(True)

    def toggle_typewriter_mode(self):
        """Toggle typewriter mode (scroll to cursor) on/off."""
        sc = getattr(self.app, "script_controller", None)
        if not sc or not hasattr(sc, "script_editor"):
            return

        editor = sc.script_editor
        current_state = editor.typewriter_mode
        new_state = not current_state
        editor.toggle_typewriter_mode(new_state)

        status = "开启" if new_state else "关闭"
        self.app.status_var.set(f"打字机模式已{status}")

    def cycle_focus_level(self):
        """Cycle through focus levels: line -> sentence -> paragraph -> dialogue."""
        sc = getattr(self.app, "script_controller", None)
        if not sc or not hasattr(sc, "script_editor"):
            return

        editor = sc.script_editor
        levels = ["line", "sentence", "paragraph", "dialogue"]
        current_idx = levels.index(editor._focus_level) if editor._focus_level in levels else 0
        next_idx = (current_idx + 1) % len(levels)
        self.set_focus_level(levels[next_idx])

    def handle_escape(self):
        """Handle Escape key - exit zen mode or focus mode."""
        if self.app.is_zen_mode:
            self.toggle_zen_mode()
        elif hasattr(self.app, "script_controller") and hasattr(self.app.script_controller, "script_editor"):
            if self.app.script_controller.script_editor.focus_mode:
                self.toggle_focus_mode()

    def open_focus_mode_settings(self):
        """Open focus mode settings dialog."""
        sc = getattr(self.app, "script_controller", None)
        if not sc or not hasattr(sc, "script_editor"):
            messagebox.showinfo("提示", "请先确保剧本写作模块可用")
            return

        FocusModeSettingsDialog(self.app.root, sc.script_editor, self.app.config_manager)

    def toggle_zen_mode(self):
        sc = getattr(self.app, "script_controller", None)
        if not sc:
            messagebox.showinfo("提示", "请先确保剧本写作模块可用")
            return

        if not self.app.is_zen_mode:
            self.app.is_zen_mode = True
            self.app._zen_start_time = time.time()
            self.app.pre_zen_geometry = self.app.root.geometry()

            self._zen_fade_transition(entering=True)

            self.app.root.attributes("-fullscreen", True)
            self.app.root.config(menu="")
            self.app.status_frame.pack_forget()
            if hasattr(self.app, "script_frame"):
                self.app.notebook.select(self.app.script_frame)
            self._apply_zen_notebook_style(True)

            if hasattr(sc, "script_paned") and hasattr(sc, "char_frame_ui") and hasattr(sc, "scene_frame_ui"):
                sc.script_paned.forget(sc.char_frame_ui)
                sc.script_paned.forget(sc.scene_frame_ui)
            if hasattr(sc, "script_editor"):
                sc.script_editor.toggle_typewriter_mode(True)
                if self.app.config_manager.get("focus_mode_auto_in_zen", True):
                    sc.script_editor.toggle_focus_mode(True, save_config=False)
                sc.script_editor.focus_set()

            self._create_zen_exit_button()

            bus = get_event_bus()
            bus.publish(Events.ZEN_MODE_ENTERED)

            self._create_zen_info_panel()

            self.app.ambiance_player.toggle(True)
            self.app.status_var.set("沉浸模式: 已开启 | 按 F11 退出")
        else:
            self.app.is_zen_mode = False

            self._zen_fade_transition(entering=False)

            self.app.root.attributes("-fullscreen", False)
            if self.app.pre_zen_geometry:
                self.app.root.geometry(self.app.pre_zen_geometry)
            self.app.root.config(menu=self.app.menubar)
            self._apply_zen_notebook_style(False)
            self.app.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.app.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
            if hasattr(self.app, "script_frame"):
                self.app.notebook.select(self.app.script_frame)

            if hasattr(sc, "script_paned") and hasattr(sc, "char_frame_ui") and hasattr(sc, "scene_frame_ui"):
                sc.script_paned.insert(0, sc.scene_frame_ui, weight=1)
                sc.script_paned.insert(0, sc.char_frame_ui, weight=1)
            if hasattr(sc, "script_editor"):
                sc.script_editor.toggle_typewriter_mode(False)
                if self.app.config_manager.get("focus_mode_auto_in_zen", True):
                    sc.script_editor.toggle_focus_mode(False, save_config=False)
                    self._update_focus_indicator(False)

            self._cleanup_zen_ui()

            self.app.ambiance_player.stop()
            self.app.ambiance_player.toggle(False)

            zen_duration = 0
            if hasattr(self.app, "_zen_start_time"):
                zen_duration = time.time() - self.app._zen_start_time
                del self.app._zen_start_time
            bus = get_event_bus()
            bus.publish(Events.ZEN_MODE_EXITED, duration=zen_duration)

    def open_word_sprint(self):
        sc = getattr(self.app, "script_controller", None)
        if not sc or not hasattr(sc, "script_editor"):
            messagebox.showinfo("提示", "请先确保剧本写作模块可用")
            return
        WordSprintDialog(self.app.root, sc.script_editor, self.app.gamification_manager, self.app.config_manager)

    def _update_focus_indicator(self, enabled):
        if hasattr(self.app, "focus_indicator_label"):
            if enabled:
                self.app.focus_indicator_label.configure(text="[专注]", foreground="#4CAF50")
            else:
                self.app.focus_indicator_label.configure(text="")

    def _zen_fade_transition(self, entering: bool):
        try:
            if entering:
                for alpha in [0.7, 0.8, 0.9, 1.0]:
                    self.app.root.attributes("-alpha", alpha)
                    self.app.root.update()
                    self.app.root.after(30)
            else:
                for alpha in [1.0, 0.9, 0.85, 0.9, 1.0]:
                    self.app.root.attributes("-alpha", alpha)
                    self.app.root.update()
                    self.app.root.after(30)
        except Exception:
            pass

    def _create_zen_exit_button(self):
        self.app.zen_exit_frame = tk.Frame(self.app.root, bg="#1a1a1a")
        self.app.zen_exit_frame.place(relx=0.98, rely=0.02, anchor="ne")

        icon = self.app.icon_mgr.get_icon("dismiss", fallback="✕")
        self.app.zen_exit_btn = tk.Button(
            self.app.zen_exit_frame,
            text=f"{icon} 退出沉浸模式",
            command=self.toggle_zen_mode,
            bg="#2d2d2d",
            fg="#888",
            activebackground="#444",
            activeforeground="#fff",
            font=("Microsoft YaHei UI", 9),
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
        )
        self.app.zen_exit_btn.pack()

        def on_enter(_event):
            self.app.zen_exit_btn.config(bg="#444", fg="#fff")

        def on_leave(_event):
            self.app.zen_exit_btn.config(bg="#2d2d2d", fg="#888")

        self.app.zen_exit_btn.bind("<Enter>", on_enter)
        self.app.zen_exit_btn.bind("<Leave>", on_leave)

        self.app.zen_exit_frame.configure(bg="#1a1a1a")

    def _create_zen_info_panel(self):
        self.app.zen_info_frame = tk.Frame(self.app.root, bg="#1a1a1a")
        self.app.zen_info_frame.place(relx=0.02, rely=0.02, anchor="nw")

        word_label = tk.Label(
            self.app.zen_info_frame,
            textvariable=self.app.word_count_var,
            fg="#666",
            bg="#1a1a1a",
            font=("Microsoft YaHei UI", 10),
        )
        word_label.pack(side=tk.LEFT, padx=(0, 15))

        sep = tk.Label(self.app.zen_info_frame, text="│", fg="#444", bg="#1a1a1a")
        sep.pack(side=tk.LEFT, padx=(0, 15))

        self.app.zen_timer_label = tk.Label(
            self.app.zen_info_frame,
            textvariable=self.app.timer_var,
            fg="#666",
            bg="#1a1a1a",
            font=("Microsoft YaHei UI", 10),
            cursor="hand2",
        )
        self.app.zen_timer_label.pack(side=tk.LEFT)
        self.app.zen_timer_label.bind("<Button-1>", self.app.pomodoro_controller.toggle)
        self.app.zen_timer_label.bind("<Button-3>", self.app.show_timer_menu)

        sep2 = tk.Label(self.app.zen_info_frame, text="│", fg="#444", bg="#1a1a1a")
        sep2.pack(side=tk.LEFT, padx=(15, 15))

        music_icon = self.app.icon_mgr.get_icon("music", fallback="🎵")
        music_font = self.app.icon_mgr.get_font(size=10)
        sound_label = tk.Label(
            self.app.zen_info_frame,
            text=music_icon,
            fg="#666",
            bg="#1a1a1a",
            font=music_font,
        )
        sound_label.pack(side=tk.LEFT, padx=(0, 5))

        self.sound_var = tk.StringVar(value="静音")

        scanned_sounds = self.app.ambiance_player.scan_sounds()
        sounds = ["静音"] + [s.capitalize() for s in scanned_sounds]

        style = ttk.Style()
        style.configure(
            "Zen.TCombobox",
            fieldbackground="#2d2d2d",
            background="#2d2d2d",
            foreground="#888",
        )

        cb = ttk.Combobox(
            self.app.zen_info_frame,
            textvariable=self.sound_var,
            values=sounds,
            state="readonly",
            width=12,
            style="Zen.TCombobox",
        )
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", self.on_zen_sound_change)

        sep3 = tk.Label(self.app.zen_info_frame, text="│", fg="#444", bg="#1a1a1a")
        sep3.pack(side=tk.LEFT, padx=(15, 15))

        target_icon = self.app.icon_mgr.get_icon("target", fallback="🎯")
        self.app.zen_focus_indicator = tk.Label(
            self.app.zen_info_frame,
            text=f"{target_icon} 专注中",
            fg="#4CAF50",
            bg="#1a1a1a",
            font=("Microsoft YaHei UI", 9),
        )
        self.app.zen_focus_indicator.pack(side=tk.LEFT)

    def _cleanup_zen_ui(self):
        for widget_name in ["zen_exit_frame", "zen_exit_btn", "zen_info_frame"]:
            widget = getattr(self.app, widget_name, None)
            if widget:
                try:
                    widget.destroy()
                except Exception:
                    pass
                setattr(self.app, widget_name, None)

    def on_zen_sound_change(self, _event):
        if not self.sound_var:
            return
        val = self.sound_var.get()
        if val == "静音":
            self.app.ambiance_player.stop()
        else:
            theme_key = val.lower()
            self.app.ambiance_player.play_theme(theme_key)

    def _apply_zen_notebook_style(self, enable):
        style = ttk.Style()
        if enable:
            if not self.app._zen_style_created:
                style.layout("Zen.TNotebook.Tab", [])
                style.configure("Zen.TNotebook", tabmargins=[0, 0, 0, 0])
                self.app._zen_style_created = True
            self.app.notebook.configure(style="Zen.TNotebook")
        else:
            self.app.notebook.configure(style=self.app._orig_notebook_style or "TNotebook")
