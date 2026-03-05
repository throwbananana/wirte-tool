"""
测试控制器注册管理模块。
"""
import unittest
from unittest.mock import Mock, MagicMock

from writer_app.core.controller_registry import ControllerRegistry, RefreshGroups


class MockController:
    """模拟控制器。"""

    def __init__(self):
        self.refresh_called = False
        self.refresh_count = 0
        self.cleanup_called = False

    def refresh(self):
        self.refresh_called = True
        self.refresh_count += 1

    def cleanup(self):
        self.cleanup_called = True


class TestControllerRegistry(unittest.TestCase):
    """测试 ControllerRegistry 类。"""

    def setUp(self):
        """每个测试前创建新的注册表。"""
        self.registry = ControllerRegistry()

    def test_register_controller(self):
        """测试注册控制器。"""
        controller = MockController()
        self.registry.register("test", controller)

        self.assertIn("test", self.registry._controllers)
        self.assertEqual(self.registry.get("test"), controller)

    def test_register_with_refresh_groups(self):
        """测试带刷新组的注册。"""
        controller = MockController()
        self.registry.register(
            "scene_ctrl",
            controller,
            refresh_groups=[RefreshGroups.SCENE, RefreshGroups.SCRIPT]
        )

        self.assertIn("scene_ctrl", self.registry._groups[RefreshGroups.SCENE])
        self.assertIn("scene_ctrl", self.registry._groups[RefreshGroups.SCRIPT])

    def test_register_with_tab_frame(self):
        """测试带标签页框架的注册。"""
        controller = MockController()
        tab_frame = Mock()
        self.registry.register("tab_ctrl", controller, tab_frame=tab_frame)

        self.assertEqual(self.registry._tabs["tab_ctrl"], tab_frame)

    def test_get_nonexistent(self):
        """测试获取不存在的控制器。"""
        result = self.registry.get("nonexistent")
        self.assertIsNone(result)

    def test_has_controller(self):
        """测试检查控制器是否存在。"""
        controller = MockController()
        self.registry.register("exists", controller)

        self.assertTrue(self.registry.has("exists"))
        self.assertFalse(self.registry.has("not_exists"))

    def test_unregister_controller(self):
        """测试注销控制器。"""
        controller = MockController()
        self.registry.register(
            "to_remove",
            controller,
            refresh_groups=[RefreshGroups.SCENE]
        )

        result = self.registry.unregister("to_remove")

        self.assertTrue(result)
        self.assertNotIn("to_remove", self.registry._controllers)
        self.assertNotIn("to_remove", self.registry._groups[RefreshGroups.SCENE])

    def test_unregister_nonexistent(self):
        """测试注销不存在的控制器。"""
        result = self.registry.unregister("nonexistent")
        self.assertFalse(result)

    def test_refresh_all(self):
        """测试刷新所有控制器。"""
        ctrl1 = MockController()
        ctrl2 = MockController()

        self.registry.register("ctrl1", ctrl1)
        self.registry.register("ctrl2", ctrl2)

        count = self.registry.refresh_all()

        self.assertEqual(count, 2)
        self.assertTrue(ctrl1.refresh_called)
        self.assertTrue(ctrl2.refresh_called)

    def test_refresh_group(self):
        """测试刷新指定组。"""
        scene_ctrl = MockController()
        char_ctrl = MockController()
        other_ctrl = MockController()

        self.registry.register("scene", scene_ctrl, refresh_groups=[RefreshGroups.SCENE])
        self.registry.register("char", char_ctrl, refresh_groups=[RefreshGroups.CHARACTER])
        self.registry.register("other", other_ctrl)

        count = self.registry.refresh_group(RefreshGroups.SCENE)

        self.assertEqual(count, 1)
        self.assertTrue(scene_ctrl.refresh_called)
        self.assertFalse(char_ctrl.refresh_called)
        self.assertFalse(other_ctrl.refresh_called)

    def test_refresh_handles_errors(self):
        """测试刷新时处理错误。"""
        good_ctrl = MockController()
        bad_ctrl = Mock()
        bad_ctrl.refresh = Mock(side_effect=Exception("Refresh failed"))

        self.registry.register("good", good_ctrl)
        self.registry.register("bad", bad_ctrl)

        # 不应该抛出异常
        count = self.registry.refresh_all()

        # good_ctrl 应该被刷新
        self.assertTrue(good_ctrl.refresh_called)

    def test_cleanup_all(self):
        """测试清理所有控制器。"""
        ctrl1 = MockController()
        ctrl2 = MockController()

        self.registry.register("ctrl1", ctrl1)
        self.registry.register("ctrl2", ctrl2)

        count = self.registry.cleanup_all()

        self.assertEqual(count, 2)
        self.assertTrue(ctrl1.cleanup_called)
        self.assertTrue(ctrl2.cleanup_called)

    def test_cleanup_handles_missing_method(self):
        """测试清理时处理没有 cleanup 方法的控制器。"""
        class NoCleanupController:
            def refresh(self):
                pass

        ctrl = NoCleanupController()
        self.registry.register("no_cleanup", ctrl)

        # 不应该抛出异常
        count = self.registry.cleanup_all()
        self.assertEqual(count, 0)

    def test_get_tab(self):
        """测试获取标签页框架。"""
        controller = MockController()
        tab_frame = Mock()
        self.registry.register("tab_ctrl", controller, tab_frame=tab_frame)

        result = self.registry.get_tab("tab_ctrl")
        self.assertEqual(result, tab_frame)

    def test_get_all_tabs(self):
        """测试获取所有标签页。"""
        ctrl1 = MockController()
        ctrl2 = MockController()
        tab1 = Mock()
        tab2 = Mock()

        self.registry.register("ctrl1", ctrl1, tab_frame=tab1)
        self.registry.register("ctrl2", ctrl2, tab_frame=tab2)

        tabs = self.registry.get_all_tabs()

        self.assertEqual(len(tabs), 2)
        self.assertIn("ctrl1", tabs)
        self.assertIn("ctrl2", tabs)

    def test_list_controllers(self):
        """测试列出所有控制器。"""
        self.registry.register("a", MockController())
        self.registry.register("b", MockController())
        self.registry.register("c", MockController())

        result = self.registry.list_controllers()

        self.assertEqual(len(result), 3)
        self.assertIn("a", result)
        self.assertIn("b", result)
        self.assertIn("c", result)

    def test_get_stats(self):
        """测试获取统计信息。"""
        self.registry.register(
            "ctrl1",
            MockController(),
            refresh_groups=[RefreshGroups.SCENE],
            tab_frame=Mock()
        )
        self.registry.register(
            "ctrl2",
            MockController(),
            refresh_groups=[RefreshGroups.SCENE, RefreshGroups.CHARACTER]
        )

        stats = self.registry.get_stats()

        self.assertEqual(stats["total_controllers"], 2)
        self.assertEqual(stats["total_tabs"], 1)
        self.assertIn("groups", stats)


class TestRefreshGroups(unittest.TestCase):
    """测试刷新组常量。"""

    def test_group_constants_exist(self):
        """测试刷新组常量存在。"""
        self.assertEqual(RefreshGroups.SCENE, "scene")
        self.assertEqual(RefreshGroups.CHARACTER, "character")
        self.assertEqual(RefreshGroups.OUTLINE, "outline")
        self.assertEqual(RefreshGroups.WIKI, "wiki")
        self.assertEqual(RefreshGroups.RELATIONSHIP, "relationship")
        self.assertEqual(RefreshGroups.TIMELINE, "timeline")
        self.assertEqual(RefreshGroups.KANBAN, "kanban")
        self.assertEqual(RefreshGroups.ANALYTICS, "analytics")


class TestControllerRegistryIntegration(unittest.TestCase):
    """测试控制器注册表集成场景。"""

    def setUp(self):
        self.registry = ControllerRegistry()

    def test_multiple_controllers_same_group(self):
        """测试同一组多个控制器。"""
        ctrls = [MockController() for _ in range(3)]

        for i, ctrl in enumerate(ctrls):
            self.registry.register(
                f"scene_ctrl_{i}",
                ctrl,
                refresh_groups=[RefreshGroups.SCENE]
            )

        count = self.registry.refresh_group(RefreshGroups.SCENE)

        self.assertEqual(count, 3)
        for ctrl in ctrls:
            self.assertTrue(ctrl.refresh_called)

    def test_controller_in_multiple_groups(self):
        """测试控制器属于多个组。"""
        ctrl = MockController()
        self.registry.register(
            "multi_group",
            ctrl,
            refresh_groups=[RefreshGroups.SCENE, RefreshGroups.CHARACTER, RefreshGroups.OUTLINE]
        )

        # 刷新任意一个组都应该触发
        self.registry.refresh_group(RefreshGroups.SCENE)
        self.assertTrue(ctrl.refresh_called)

        ctrl.refresh_called = False
        self.registry.refresh_group(RefreshGroups.CHARACTER)
        self.assertTrue(ctrl.refresh_called)


if __name__ == "__main__":
    unittest.main()
