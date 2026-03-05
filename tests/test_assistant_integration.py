import unittest
from unittest.mock import MagicMock, patch
from writer_app.ui.floating_assistant.integrations import EventBusIntegration
from writer_app.core.event_bus import get_event_bus, Events

class TestEventBusIntegration(unittest.TestCase):

    def setUp(self):
        self.mock_assistant = MagicMock()
        self.mock_assistant.event_system = MagicMock()
        self.mock_project_manager = MagicMock()
        
        self.integration = EventBusIntegration(self.mock_assistant, self.mock_project_manager)
        self.integration.subscribe_all()
        self.bus = get_event_bus()

    def tearDown(self):
        self.integration.unsubscribe_all()

    def test_scene_added_event(self):
        """测试发布场景添加事件是否触发布置处理器"""
        # 我们通过检查 assistant.event_system.handle_project_event 是否被调用来验证
        self.bus.publish(Events.SCENE_ADDED, scene_name="Test Scene")
        
        # 验证 handle_project_event 是否被调用
        self.mock_assistant.event_system.handle_project_event.assert_called_with(
            Events.SCENE_ADDED, scene_name="Test Scene"
        )
        
        # 验证助手是否收到了通知（UI提示）
        self.mock_assistant.notification_manager.notify.assert_called()

    def test_character_added_event(self):
        """测试发布角色添加事件"""
        self.bus.publish(Events.CHARACTER_ADDED, char_name="Hero")
        
        self.mock_assistant.event_system.handle_project_event.assert_called_with(
            Events.CHARACTER_ADDED, char_name="Hero"
        )
        self.mock_assistant.notification_manager.notify.assert_called()

    def test_silent_event(self):
        """测试静默事件（只统计不通知）"""
        # WIKI_ENTRY_ADDED 在 EVENT_HANDLERS 中映射到 _on_silent_event
        self.bus.publish(Events.WIKI_ENTRY_ADDED, entry_name="World History")
        
        # 统计仍然应该被处理
        self.mock_assistant.event_system.handle_project_event.assert_called_with(
            Events.WIKI_ENTRY_ADDED, entry_name="World History"
        )
        
        # 但 notification_manager.notify 不应该被调用（因为是 silent event）
        # 注意：_on_silent_event 什么都不做，所以通知不应该发出
        self.mock_assistant.notification_manager.notify.assert_not_called()

if __name__ == '__main__':
    unittest.main()
