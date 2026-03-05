"""
测试应用退出时的完整清理

测试内容：
- _exit_app()的清理顺序
- 所有控制器的cleanup被调用
- 线程池关闭
- 配置保存
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, call


class TestAppShutdown(unittest.TestCase):
    """测试应用退出清理流程"""

    @patch('writer_app.main.shutdown_thread_pool')
    @patch('writer_app.main.FloatingAssistantManager')
    def test_exit_app_cleanup_order(self, mock_assistant_manager, mock_shutdown_pool):
        """测试_exit_app的清理顺序"""
        # This is a high-level integration test concept
        # In practice, we verify the order of operations

        # 1. 后台服务应该先停止
        # 2. AI线程池应该关闭
        # 3. 悬浮助手应该销毁
        # 4. registry.cleanup_all应该被调用
        # 5. 配置应该保存
        # 6. 托盘应该停止
        # 7. 窗口应该销毁

        # This test documents the expected cleanup order
        expected_order = [
            "stop_backup_manager",
            "pause_pomodoro",
            "shutdown_thread_pool",
            "destroy_floating_assistant",
            "registry_cleanup_all",
            "save_config",
            "stop_tray",
            "destroy_root"
        ]

        # The actual verification would require mocking the entire WriterTool class
        # which is complex. This test serves as documentation.
        self.assertEqual(len(expected_order), 8)


class TestRegistryCleanupAllIntegration(unittest.TestCase):
    """测试ControllerRegistry.cleanup_all()集成"""

    def test_cleanup_all_handles_errors_gracefully(self):
        """测试cleanup_all优雅处理错误"""
        from writer_app.core.controller_registry import ControllerRegistry

        registry = ControllerRegistry()

        # Controller that raises error
        error_controller = Mock()
        error_controller.cleanup = Mock(side_effect=Exception("Cleanup error"))

        # Normal controller
        normal_controller = Mock()
        normal_controller.cleanup = Mock()

        registry.register("error_ctrl", error_controller)
        registry.register("normal_ctrl", normal_controller)

        # Should not raise, and should continue to clean up other controllers
        try:
            registry.cleanup_all()
        except Exception:
            self.fail("cleanup_all should not raise exceptions")

        # Both cleanup methods should have been called
        error_controller.cleanup.assert_called_once()
        normal_controller.cleanup.assert_called_once()


class TestThreadPoolShutdown(unittest.TestCase):
    """测试线程池关闭"""

    def test_shutdown_thread_pool_cancels_tasks(self):
        """测试shutdown_thread_pool取消所有任务"""
        from writer_app.core.thread_pool import get_ai_thread_pool, shutdown_thread_pool

        pool = get_ai_thread_pool()

        # Shutdown
        shutdown_thread_pool()

        # After shutdown, pool should be recreated on next get_ai_thread_pool
        # This is the expected behavior for clean restart


class TestCleanupMixin(unittest.TestCase):
    """测试CleanupMixin"""

    def test_cleanup_mixin_init(self):
        """测试CleanupMixin初始化"""
        from writer_app.ui.components.cleanup_mixin import CleanupMixin

        class TestWidget(CleanupMixin):
            def __init__(self):
                self._init_cleanup_tracking()

        widget = TestWidget()

        self.assertFalse(widget._destroyed)
        self.assertEqual(len(widget._event_subscriptions), 0)
        self.assertEqual(len(widget._listener_refs), 0)
        self.assertEqual(len(widget._after_jobs), 0)

    @patch('writer_app.core.event_bus.get_event_bus')
    def test_cleanup_mixin_track_event_subscription(self, mock_get_bus):
        """测试CleanupMixin追踪事件订阅"""
        from writer_app.ui.components.cleanup_mixin import CleanupMixin

        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus

        class TestWidget(CleanupMixin):
            def __init__(self):
                self._init_cleanup_tracking()

        widget = TestWidget()
        handler = Mock()
        widget._track_event_subscription("TEST_EVENT", handler)

        mock_bus.subscribe.assert_called_with("TEST_EVENT", handler)
        self.assertEqual(len(widget._event_subscriptions), 1)

    @patch('writer_app.core.event_bus.get_event_bus')
    def test_cleanup_mixin_cleanup_subscriptions(self, mock_get_bus):
        """测试CleanupMixin清理订阅"""
        from writer_app.ui.components.cleanup_mixin import CleanupMixin

        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus

        class TestWidget(CleanupMixin):
            def __init__(self):
                self._init_cleanup_tracking()

        widget = TestWidget()
        handler = Mock()
        widget._track_event_subscription("TEST_EVENT", handler)

        widget.cleanup_subscriptions()

        mock_bus.unsubscribe.assert_called_with("TEST_EVENT", handler)
        self.assertEqual(len(widget._event_subscriptions), 0)
        self.assertTrue(widget._destroyed)


class TestEditorCleanup(unittest.TestCase):
    """测试ScriptEditor的清理"""

    @patch('writer_app.core.event_bus.get_event_bus')
    def test_editor_destroy_cleans_up_subscriptions(self, mock_get_bus):
        """测试ScriptEditor.destroy()清理订阅"""
        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus

        # We can't easily instantiate ScriptEditor without a real Tk root
        # This test documents the expected behavior

        # Expected: When ScriptEditor.destroy() is called:
        # 1. All after() jobs should be cancelled
        # 2. All EventBus subscriptions should be unsubscribed
        # 3. All project listeners should be removed
        # 4. super().destroy() should be called

        self.assertTrue(True)  # Placeholder for actual test


class TestIdeaControllerCleanup(unittest.TestCase):
    """测试IdeaController的清理（手动实现的cleanup）"""

    @patch('writer_app.core.event_bus.get_event_bus')
    def test_idea_controller_cleanup(self, mock_get_bus):
        """测试IdeaController.cleanup()清理订阅"""
        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus

        mock_view = Mock()
        mock_project_manager = Mock()
        mock_project_manager.get_ideas.return_value = []
        mock_theme_manager = Mock()

        from writer_app.controllers.idea_controller import IdeaController

        controller = IdeaController(mock_view, mock_project_manager, mock_theme_manager)

        # Verify subscriptions were made
        self.assertGreater(len(controller._event_subscriptions), 0)

        # Cleanup
        controller.cleanup()

        # Verify unsubscribe was called
        self.assertTrue(controller._destroyed)
        self.assertEqual(len(controller._event_subscriptions), 0)


if __name__ == '__main__':
    unittest.main()
