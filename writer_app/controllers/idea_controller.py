import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import List, Tuple, Callable
from writer_app.core.event_bus import get_event_bus, Events

class IdeaController:
    """灵感控制器 - 管理灵感面板的业务逻辑"""

    def __init__(self, view, project_manager, theme_manager):
        self.view = view
        self.project_manager = project_manager
        self.theme_manager = theme_manager

        # Lifecycle tracking
        self._event_subscriptions: List[Tuple[str, Callable]] = []
        self._destroyed = False

        self.view.set_add_command(self.add_idea)
        self.view.set_delete_command(self.delete_idea)
        self.view.set_copy_command(self.copy_to_clipboard)

        self._subscribe_events()
        self.refresh()

    def _subscribe_event(self, event_type: str, handler: Callable) -> None:
        """订阅事件并追踪以便清理"""
        bus = get_event_bus()
        bus.subscribe(event_type, handler)
        self._event_subscriptions.append((event_type, handler))

    def _subscribe_events(self):
        """订阅相关事件以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.IDEAS_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.IDEA_ADDED, self._on_data_changed)
        self._subscribe_event(Events.IDEA_DELETED, self._on_data_changed)

    def cleanup(self) -> None:
        """清理所有追踪的资源"""
        self._destroyed = True

        # Unsubscribe from EventBus
        bus = get_event_bus()
        for event_type, handler in self._event_subscriptions:
            try:
                bus.unsubscribe(event_type, handler)
            except Exception:
                pass
        self._event_subscriptions.clear()

    def _on_data_changed(self, event_type=None, **kwargs):
        """响应数据变化事件"""
        self.refresh()

    def refresh(self):
        ideas = self.project_manager.get_ideas()
        self.view.display_ideas(ideas)

    def add_idea(self, content):
        if not content.strip():
            return
        self.project_manager.add_idea(content)
        self.refresh()

    def delete_idea(self, idea_uid):
        if self.project_manager.delete_idea(idea_uid):
            self.refresh()

    def copy_to_clipboard(self, content):
        self.view.master.clipboard_clear()
        self.view.master.clipboard_append(content)
        self.view.show_message("已复制到剪贴板")

    def apply_theme(self):
        """
        应用当前主题到灵感面板视图。
        """
        if not self.theme_manager:
            return

        try:
            # 如果视图有自己的主题方法，调用它
            if hasattr(self.view, 'apply_theme'):
                self.view.apply_theme(self.theme_manager)

            # 刷新视图
            self.refresh()

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"应用灵感面板主题时出错: {e}")
