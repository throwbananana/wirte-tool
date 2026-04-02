class ShortcutRegistry:
    """Register global keyboard shortcuts for the desktop shell."""

    def __init__(self, app):
        self.app = app

    def bind(self):
        app = self.app
        app.root.bind("<Control-n>", lambda e: app.new_project())
        app.root.bind("<Control-o>", lambda e: app.open_project())
        app.root.bind("<Control-s>", lambda e: app.save_project())
        app.root.bind("<Control-f>", lambda e: app.open_search_dialog())
        app.root.bind("<Control-h>", lambda e: app.open_search_dialog(focus_replace=True))
        app.root.bind("<F1>", lambda e: app.show_help())
        app.root.bind("<Control-slash>", lambda e: app.show_shortcuts())
        app.root.bind("<Control-question>", lambda e: app.show_shortcuts())
        app.root.bind("<F5>", lambda e: app.refresh_all())
        app.root.bind("<F2>", lambda e: app.toggle_floating_assistant())
        app.root.bind("<F9>", lambda e: app.toggle_typewriter_mode())
        app.root.bind("<F10>", lambda e: app.toggle_focus_mode())
        app.root.bind("<Control-Shift-F>", lambda e: app._cycle_focus_level())
        app.root.bind("<Control-Shift-exclam>", lambda e: app.set_focus_level("line"))
        app.root.bind("<Control-Shift-at>", lambda e: app.set_focus_level("sentence"))
        app.root.bind("<Control-Shift-numbersign>", lambda e: app.set_focus_level("paragraph"))
        app.root.bind("<Control-Shift-dollar>", lambda e: app.set_focus_level("dialogue"))
        app.root.bind("<F11>", lambda e: app.toggle_zen_mode())
        app.root.bind("<Escape>", lambda e: app._handle_escape())
        app.root.bind("<Control-z>", lambda e: app.undo())
        app.root.bind("<Control-y>", lambda e: app.redo())
        app.root.bind("<Control-Tab>", lambda e: app._switch_tab(1))
        app.root.bind("<Control-Shift-Tab>", lambda e: app._switch_tab(-1))
        app.root.bind("<Control-ISO_Left_Tab>", lambda e: app._switch_tab(-1))
        for i in range(1, 10):
            app.root.bind(f"<Alt-Key-{i}>", lambda e, idx=i - 1: app._select_tab_by_index(idx))
        app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
