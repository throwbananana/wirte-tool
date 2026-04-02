import tkinter as tk
from tkinter import ttk

from writer_app.app.builders import TAB_BUILDERS
from writer_app.controllers.sidebar_controller import SidebarController
from writer_app.core.project_types import ProjectTypeManager
from writer_app.ui.sidebar import SidebarPanel


class WorkspaceBuilder:
    """Build and rebuild the main workspace UI from the active project config."""

    def __init__(self, app):
        self.app = app

    def build(self):
        self._build_layout()
        current_type = self.app.project_manager.get_project_type()
        current_length = self.app.project_manager.get_project_length()
        enabled_tools = self.app.project_manager.get_enabled_tools()

        self._build_tabs(enabled_tools)
        self._setup_sidebar(enabled_tools, current_type)
        self._update_project_badge(current_type, current_length)

        self.app.apply_theme()
        self.app.refresh_all()

    def _build_layout(self):
        app = self.app
        app.main_paned = ttk.PanedWindow(app.root, orient=tk.HORIZONTAL)
        app.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        app.sidebar = SidebarPanel(
            app.main_paned,
            app.theme_manager,
            app._on_sidebar_select,
            app.config_manager,
        )
        app.main_paned.add(app.sidebar, weight=0)

        app.content_area = ttk.Frame(app.main_paned)
        app.main_paned.add(app.content_area, weight=1)

        app.notebook = ttk.Notebook(app.content_area)
        app._orig_notebook_style = app.notebook.cget("style") or ""
        app.notebook.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.layout("Hidden.TNotebook.Tab", [])
        app.notebook.configure(style="Hidden.TNotebook")

        app._toolbox_tab = None
        app._last_real_tab = None

    def _build_tabs(self, enabled_tools):
        for tool_key in enabled_tools:
            builder = TAB_BUILDERS.get(tool_key)
            if builder:
                builder(self)

    def _register_tab(self, key: str, frame, text: str):
        self.app.notebook.add(frame, text=text)
        self.app.tabs[key] = frame
        return frame

    def _setup_sidebar(self, enabled_tools, current_type):
        app = self.app
        app._toolbox_tab = None
        app.sidebar_controller = SidebarController(
            app.sidebar,
            app.notebook,
            app.config_manager,
            on_item_changed=app._on_sidebar_item_changed,
        )

        for key, frame in app.tabs.items():
            app.sidebar_controller.register_tab(key, frame)

        app.sidebar.update_visibility(enabled_tools)

        default_key = ProjectTypeManager.get_default_tab_key(current_type)
        if default_key in app.tabs:
            app.sidebar.select_item_by_key(default_key)
            app.notebook.select(app.tabs[default_key])
        elif app.tabs:
            first_key = next(iter(app.tabs.keys()))
            app.sidebar.select_item_by_key(first_key)
            app.notebook.select(app.tabs[first_key])

        app._last_real_tab = app.notebook.select() if app.tabs else None

    def _update_project_badge(self, current_type, current_length):
        app = self.app
        type_name = app.project_manager.get_project_type_display_name()
        length_name = ProjectTypeManager.get_length_info(current_length)["name"]
        if hasattr(app, "type_lbl") and app.type_lbl:
            app.type_lbl.config(text=f"[{type_name} | {length_name}]")
