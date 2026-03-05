"""
测试控制器清理功能

测试内容：
- 事件订阅清理
- 监听器清理
- after任务取消
- 完整的cleanup()流程
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import tkinter as tk


class TestBaseControllerCleanup(unittest.TestCase):
    """测试BaseController的清理功能"""

    def setUp(self):
        """设置测试环境"""
        # Create mock dependencies
        self.mock_parent = Mock()
        self.mock_parent.winfo_exists.return_value = True
        self.mock_parent.after_cancel = Mock()

        self.mock_project_manager = Mock()
        self.mock_project_manager.add_listener = Mock()
        self.mock_project_manager.remove_listener = Mock()

        self.mock_command_executor = Mock()

        self.mock_theme_manager = Mock()
        self.mock_theme_manager.add_listener = Mock()
        self.mock_theme_manager.remove_listener = Mock()

    @patch('writer_app.core.event_bus.get_event_bus')
    def test_subscribe_event_tracks_subscription(self, mock_get_bus):
        """测试_subscribe_event正确追踪订阅"""
        from writer_app.controllers.base_controller import BaseController

        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus

        controller = BaseController(
            self.mock_parent,
            self.mock_project_manager,
            self.mock_command_executor,
            self.mock_theme_manager
        )

        handler = Mock()
        controller._subscribe_event("TEST_EVENT", handler)

        # Verify subscription was made
        mock_bus.subscribe.assert_called_with("TEST_EVENT", handler)

        # Verify subscription was tracked
        self.assertEqual(len(controller._event_subscriptions), 1)
        self.assertEqual(controller._event_subscriptions[0], ("TEST_EVENT", handler))

    @patch('writer_app.core.event_bus.get_event_bus')
    def test_cleanup_unsubscribes_events(self, mock_get_bus):
        """测试cleanup()正确取消事件订阅"""
        from writer_app.controllers.base_controller import BaseController

        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus

        controller = BaseController(
            self.mock_parent,
            self.mock_project_manager,
            self.mock_command_executor,
            self.mock_theme_manager
        )

        handler1 = Mock()
        handler2 = Mock()
        controller._subscribe_event("EVENT1", handler1)
        controller._subscribe_event("EVENT2", handler2)

        # Perform cleanup
        controller.cleanup()

        # Verify unsubscribe was called for each subscription
        mock_bus.unsubscribe.assert_any_call("EVENT1", handler1)
        mock_bus.unsubscribe.assert_any_call("EVENT2", handler2)

        # Verify list was cleared
        self.assertEqual(len(controller._event_subscriptions), 0)

    def test_add_theme_listener_tracks_listener(self):
        """测试_add_theme_listener正确追踪监听器"""
        from writer_app.controllers.base_controller import BaseController

        with patch('writer_app.core.event_bus.get_event_bus'):
            controller = BaseController(
                self.mock_parent,
                self.mock_project_manager,
                self.mock_command_executor,
                self.mock_theme_manager
            )

        handler = Mock()
        controller._add_theme_listener(handler)

        # Verify listener was added
        self.mock_theme_manager.add_listener.assert_called_with(handler)

        # Verify listener was tracked
        self.assertEqual(len(controller._theme_listeners), 1)
        self.assertEqual(controller._theme_listeners[0], handler)

    def test_cleanup_removes_theme_listeners(self):
        """测试cleanup()正确移除主题监听器"""
        from writer_app.controllers.base_controller import BaseController

        with patch('writer_app.core.event_bus.get_event_bus'):
            controller = BaseController(
                self.mock_parent,
                self.mock_project_manager,
                self.mock_command_executor,
                self.mock_theme_manager
            )

        handler = Mock()
        controller._add_theme_listener(handler)

        # Perform cleanup
        controller.cleanup()

        # Verify remove_listener was called
        self.mock_theme_manager.remove_listener.assert_called_with(handler)

        # Verify list was cleared
        self.assertEqual(len(controller._theme_listeners), 0)

    def test_add_project_listener_tracks_listener(self):
        """测试_add_project_listener正确追踪监听器"""
        from writer_app.controllers.base_controller import BaseController

        with patch('writer_app.core.event_bus.get_event_bus'):
            controller = BaseController(
                self.mock_parent,
                self.mock_project_manager,
                self.mock_command_executor,
                self.mock_theme_manager
            )

        handler = Mock()
        controller._add_project_listener(handler)

        # Verify listener was added
        self.mock_project_manager.add_listener.assert_called_with(handler)

        # Verify listener was tracked
        self.assertEqual(len(controller._project_listeners), 1)
        self.assertEqual(controller._project_listeners[0], handler)

    def test_cleanup_sets_destroyed_flag(self):
        """测试cleanup()设置_destroyed标志"""
        from writer_app.controllers.base_controller import BaseController

        with patch('writer_app.core.event_bus.get_event_bus'):
            controller = BaseController(
                self.mock_parent,
                self.mock_project_manager,
                self.mock_command_executor,
                self.mock_theme_manager
            )

        self.assertFalse(controller._destroyed)

        controller.cleanup()

        self.assertTrue(controller._destroyed)


class TestSafeAfter(unittest.TestCase):
    """测试安全的after()调用"""

    def test_safe_after_returns_none_when_destroyed(self):
        """测试当widget被销毁时_safe_after返回None"""
        from writer_app.controllers.base_controller import BaseController

        mock_parent = Mock()
        mock_parent.winfo_exists.return_value = False

        with patch('writer_app.core.event_bus.get_event_bus'):
            controller = BaseController(
                mock_parent,
                Mock(),
                Mock(),
                Mock()
            )

        callback = Mock()
        result = controller._safe_after("test_job", 100, callback)

        # Should return None and not schedule
        self.assertIsNone(result)
        mock_parent.after.assert_not_called()

    def test_safe_after_schedules_when_exists(self):
        """测试当widget存在时_safe_after正确调度"""
        from writer_app.controllers.base_controller import BaseController

        mock_parent = Mock()
        mock_parent.winfo_exists.return_value = True
        mock_parent.after.return_value = "job_123"

        with patch('writer_app.core.event_bus.get_event_bus'):
            controller = BaseController(
                mock_parent,
                Mock(),
                Mock(),
                Mock()
            )

        callback = Mock()
        result = controller._safe_after("test_job", 100, callback)

        # Should schedule and return job id
        self.assertEqual(result, "job_123")
        self.assertIn("test_job", controller._after_jobs)

    def test_cancel_after_removes_job(self):
        """测试_cancel_after正确取消任务"""
        from writer_app.controllers.base_controller import BaseController

        mock_parent = Mock()
        mock_parent.winfo_exists.return_value = True
        mock_parent.after.return_value = "job_123"

        with patch('writer_app.core.event_bus.get_event_bus'):
            controller = BaseController(
                mock_parent,
                Mock(),
                Mock(),
                Mock()
            )

        callback = Mock()
        controller._safe_after("test_job", 100, callback)

        # Cancel the job
        result = controller._cancel_after("test_job")

        self.assertTrue(result)
        mock_parent.after_cancel.assert_called_with("job_123")
        self.assertNotIn("test_job", controller._after_jobs)


class TestControllerRegistryCleanup(unittest.TestCase):
    """测试ControllerRegistry的清理功能"""

    def test_cleanup_all_calls_controller_cleanup(self):
        """测试cleanup_all调用所有控制器的cleanup方法"""
        from writer_app.core.controller_registry import ControllerRegistry

        registry = ControllerRegistry()

        controller1 = Mock()
        controller1.cleanup = Mock()
        controller2 = Mock()
        controller2.cleanup = Mock()

        registry.register("ctrl1", controller1)
        registry.register("ctrl2", controller2)

        # Cleanup all
        registry.cleanup_all()

        controller1.cleanup.assert_called_once()
        controller2.cleanup.assert_called_once()

    def test_cleanup_all_handles_missing_cleanup_method(self):
        """测试cleanup_all处理没有cleanup方法的控制器"""
        from writer_app.core.controller_registry import ControllerRegistry

        registry = ControllerRegistry()

        controller1 = Mock(spec=[])  # No cleanup method
        controller2 = Mock()
        controller2.cleanup = Mock()

        registry.register("ctrl1", controller1)
        registry.register("ctrl2", controller2)

        # Should not raise error
        registry.cleanup_all()

        # ctrl2's cleanup should still be called
        controller2.cleanup.assert_called_once()

    def test_call_on_controllers_with_capability(self):
        """测试基于capability调用控制器方法"""
        from writer_app.core.controller_registry import ControllerRegistry, Capabilities

        registry = ControllerRegistry()

        controller1 = Mock()
        controller1.set_ai_mode_enabled = Mock()
        controller2 = Mock()
        controller2.set_ai_mode_enabled = Mock()
        controller3 = Mock()
        controller3.some_other_method = Mock()

        registry.register("ctrl1", controller1, capabilities=[Capabilities.AI_MODE])
        registry.register("ctrl2", controller2, capabilities=[Capabilities.AI_MODE])
        registry.register("ctrl3", controller3, capabilities=["other"])

        # Call on controllers with AI_MODE capability
        registry.call_on_controllers_with_capability(
            Capabilities.AI_MODE,
            "set_ai_mode_enabled",
            True
        )

        controller1.set_ai_mode_enabled.assert_called_once_with(True)
        controller2.set_ai_mode_enabled.assert_called_once_with(True)
        controller3.set_ai_mode_enabled.assert_not_called()


if __name__ == '__main__':
    unittest.main()
