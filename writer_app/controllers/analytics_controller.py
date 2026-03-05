import tkinter as tk
from tkinter import ttk
from writer_app.controllers.base_controller import BaseController
from writer_app.ui.analytics import AnalyticsPanel
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.ui.help_dialog import create_module_help_button

class AnalyticsController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.setup_ui()
        self._subscribe_events()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(toolbar, text="项目数据统计与可视化分析").pack(side=tk.LEFT, padx=5)

        # 帮助按钮
        help_btn = create_module_help_button(toolbar, "analytics", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        self.view = AnalyticsPanel(self.parent, self.project_manager)
        self.view.pack(fill=tk.BOTH, expand=True)

    def _subscribe_events(self):
        """订阅相关事件以自动刷新统计数据（使用追踪方法以便清理）"""
        self._subscribe_event(Events.SCENE_ADDED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_DELETED, self._on_data_changed)
        self._subscribe_event(Events.CHARACTER_ADDED, self._on_data_changed)
        self._subscribe_event(Events.CHARACTER_DELETED, self._on_data_changed)
        self._subscribe_event(Events.OUTLINE_CHANGED, self._on_data_changed)

    def _on_data_changed(self, event_type=None, **kwargs):
        """响应数据变化事件"""
        self.refresh()

    def refresh(self):
        if self.view:
            self.view.refresh()

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "analytics")

    def apply_theme(self):
        pass # AnalyticsPanel might not need explicit theme update if using ttk
