import tkinter as tk
from tkinter import ttk


class AppThemeController:
    def __init__(self, app):
        self.app = app

    def on_theme_changed(self):
        self.apply_theme()
        self.app.config_manager.set("theme", self.app.theme_manager.current_theme)

    def toggle_theme(self):
        self.app.theme_manager.toggle_theme()

    def apply_theme(self):
        theme = self.app.theme_manager
        style = ttk.Style(self.app.root)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = theme.get_color("bg_secondary")
        fg = theme.get_color("fg_primary")
        menu_bg = theme.get_color("bg_primary")
        menu_fg = theme.get_color("fg_primary")
        accent = theme.get_color("accent")

        self.app.root.option_add("*Menu.background", menu_bg)
        self.app.root.option_add("*Menu.foreground", menu_fg)
        self.app.root.option_add("*Menu.activeBackground", accent)
        self.app.root.option_add("*Menu.activeForeground", "#FFFFFF")
        self.app.root.option_add("*Menu.selectColor", accent)

        ui_font = self.app.config_manager.get("ui_font", "Microsoft YaHei")
        if ui_font and ui_font.startswith("@"):
            ui_font = ui_font[1:]

        ui_size = self.app.config_manager.get("ui_font_size", 9)
        if ui_font:
            style.configure(".", font=(ui_font, ui_size))

        self.app.root.configure(bg=bg)
        style.configure(".", background=bg, foreground=fg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("TLabelframe", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        style.configure("TButton", background=bg, foreground=fg)
        style.map(
            "TButton",
            background=[("active", theme.get_color("highlight")), ("pressed", theme.get_color("accent"))],
            foreground=[("active", fg)],
        )
        style.configure("TNotebook", background=bg, tabmargins=[2, 5, 2, 0])
        style.configure(
            "TNotebook.Tab",
            background=theme.get_color("bg_primary"),
            foreground=theme.get_color("fg_secondary"),
            padding=[10, 2],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", bg)],
            foreground=[("selected", fg)],
            expand=[("selected", [1, 1, 1, 0])],
        )

        if hasattr(self.app, "menubar"):
            self._update_menu_colors(self.app.menubar, menu_bg, menu_fg, accent, "#FFFFFF")

        # Apply theme to controllers - wrapped in try/except to handle rebuild_tabs scenarios
        # where widgets may have been destroyed but controller references still exist
        self._safe_apply_theme("script_controller")
        self._safe_apply_theme("mindmap_controller")
        self._safe_apply_theme("relationship_controller")
        self._safe_apply_theme("wiki_controller")
        self._safe_apply_theme("timeline_controller")
        self._safe_apply_theme("kanban_controller")
        self._safe_apply_theme("calendar_controller")
        self._safe_apply_theme("dual_timeline_controller")
        self._safe_apply_theme("flowchart_controller")
        self._safe_apply_theme("analytics_controller")
        self._safe_apply_theme("idea_controller")
        self._safe_apply_theme("evidence_board")
        self._safe_apply_theme("research_panel")
        self._safe_apply_theme("training_panel")
        self._safe_apply_theme("idea_panel")

        if hasattr(self.app, "outline_view_manager"):
            try:
                self.app.outline_view_manager.apply_theme(theme)
            except tk.TclError:
                pass

        if hasattr(self.app, "chat_panel"):
            try:
                self.app.chat_panel.history_text.configure(
                    bg=theme.get_color("editor_bg"),
                    fg=theme.get_color("editor_fg"),
                )
                self.app.chat_panel.input_text.configure(
                    bg=theme.get_color("editor_bg"),
                    fg=theme.get_color("editor_fg"),
                )
            except tk.TclError:
                pass

        if hasattr(self.app, "relationship_canvas"):
            try:
                self.app.relationship_canvas.configure(bg=theme.get_color("canvas_bg"))
            except tk.TclError:
                pass

        if hasattr(self.app, "floating_assistant") and self.app.floating_assistant:
            try:
                self.app.floating_assistant.apply_theme(theme)
            except tk.TclError:
                pass

        # Sidebar theming
        self._safe_apply_theme("sidebar")
        self._safe_apply_theme("sidebar_controller")

    def _safe_apply_theme(self, attr_name):
        """Safely apply theme to a controller/component, handling destroyed widgets."""
        obj = getattr(self.app, attr_name, None)
        if obj and hasattr(obj, "apply_theme"):
            try:
                obj.apply_theme()
            except tk.TclError:
                # Widget was destroyed (e.g., during rebuild_tabs)
                pass
            except Exception:
                # Other errors - silently ignore during theme application
                pass

    def _update_menu_colors(self, menu, bg, fg, active_bg, active_fg):
        try:
            menu.configure(bg=bg, fg=fg, activebackground=active_bg, activeforeground=active_fg)
            for child in menu.winfo_children():
                if isinstance(child, tk.Menu):
                    self._update_menu_colors(child, bg, fg, active_bg, active_fg)
        except Exception:
            pass
