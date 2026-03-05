import tkinter as tk
from tkinter import ttk
from writer_app.controllers.base_controller import BaseController
from writer_app.ui.calendar_view import CalendarView
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.ui.help_dialog import create_module_help_button

class CalendarController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager, navigation_callback):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.navigation_callback = navigation_callback # Callback to jump to script
        self.setup_ui()
        self._subscribe_events()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(toolbar, text="按日期查看场景安排，双击跳转到剧本").pack(side=tk.LEFT, padx=5)

        # 帮助按钮
        help_btn = create_module_help_button(toolbar, "calendar", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        self.view = CalendarView(
            self.parent,
            self.project_manager,
            self.navigation_callback,
            self.theme_manager,
            command_executor=self.command_executor
        )
        self.view.pack(fill=tk.BOTH, expand=True)

    def _subscribe_events(self):
        """订阅相关事件以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.SCENE_ADDED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_DELETED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_MOVED, self._on_data_changed)

    def _on_data_changed(self, event_type=None, **kwargs):
        """响应数据变化事件"""
        self.refresh()

    def refresh(self):
        if self.view:
            self.view.refresh()

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "calendar")

    def apply_theme(self):
        """应用主题"""
        if self.view and hasattr(self.view, 'apply_theme'):
            self.view.apply_theme()
