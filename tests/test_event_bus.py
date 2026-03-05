"""
事件总线单元测试
"""

import unittest
from writer_app.core.event_bus import EventBus, get_event_bus


class TestEventBus(unittest.TestCase):
    def setUp(self):
        # 创建新的EventBus实例用于测试（不使用单例）
        self.bus = EventBus()
        self.received_events = []

    def tearDown(self):
        self.received_events.clear()

    def test_subscribe_and_publish(self):
        """测试基本的订阅和发布功能。"""
        def handler(event_type=None, **kwargs):
            self.received_events.append(kwargs)

        self.bus.subscribe("scene_added", handler)
        self.bus.publish("scene_added", scene_id=1, name="Test Scene")

        self.assertEqual(len(self.received_events), 1)
        self.assertEqual(self.received_events[0]["scene_id"], 1)
        self.assertEqual(self.received_events[0]["name"], "Test Scene")

    def test_multiple_subscribers(self):
        """测试多个订阅者接收同一事件。"""
        results = []

        def handler1(event_type=None, **kwargs):
            results.append("handler1")

        def handler2(event_type=None, **kwargs):
            results.append("handler2")

        self.bus.subscribe("scene_updated", handler1)
        self.bus.subscribe("scene_updated", handler2)
        self.bus.publish("scene_updated", scene_id=1)

        self.assertEqual(len(results), 2)
        self.assertIn("handler1", results)
        self.assertIn("handler2", results)

    def test_unsubscribe(self):
        """测试取消订阅。"""
        def handler(event_type=None, **kwargs):
            self.received_events.append(kwargs)

        self.bus.subscribe("scene_deleted", handler)
        self.bus.publish("scene_deleted", scene_id=1)
        self.assertEqual(len(self.received_events), 1)

        self.bus.unsubscribe("scene_deleted", handler)
        self.bus.publish("scene_deleted", scene_id=2)
        # 应该还是只有1个事件
        self.assertEqual(len(self.received_events), 1)

    def test_invalid_event_type(self):
        """测试无效事件类型仍可订阅（仅警告，不抛出异常）。"""
        def handler(event_type=None, **kwargs):
            self.received_events.append(kwargs)

        # 无效事件类型应该可以订阅（只是会记录警告）
        self.bus.subscribe("invalid_event_type", handler)
        self.bus.publish("invalid_event_type", data="test")

        # 验证处理器仍被调用
        self.assertEqual(len(self.received_events), 1)
        self.assertEqual(self.received_events[0]["data"], "test")

    def test_batch_events(self):
        """测试批量事件处理。"""
        call_count = 0

        def handler(event_type=None, **kwargs):
            nonlocal call_count
            call_count += 1

        self.bus.subscribe("scene_added", handler)

        # 开始批量操作
        self.bus.begin_batch()
        self.bus.publish("scene_added", scene_id=1)
        self.bus.publish("scene_added", scene_id=2)
        self.bus.publish("scene_added", scene_id=3)

        # 批量期间不触发
        self.assertEqual(call_count, 0)

        # 结束批量
        self.bus.end_batch()

        # 批量结束后触发（合并为1次）
        self.assertEqual(call_count, 1)

    def test_publish_all(self):
        """测试publish_all发布多个事件。"""
        scene_events = []
        character_events = []

        def scene_handler(event_type=None, **kwargs):
            scene_events.append(kwargs)

        def character_handler(event_type=None, **kwargs):
            character_events.append(kwargs)

        self.bus.subscribe("scene_added", scene_handler)
        self.bus.subscribe("character_added", character_handler)

        self.bus.publish_all(["scene_added", "character_added"], id=1)

        self.assertEqual(len(scene_events), 1)
        self.assertEqual(len(character_events), 1)

    def test_singleton(self):
        """测试单例模式。"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        self.assertIs(bus1, bus2)

    def test_subscribe_to_multiple_events(self):
        """测试一个处理器订阅多个事件类型。"""
        for event_type in ["scene_added", "scene_updated", "scene_deleted"]:
            self.bus.subscribe(event_type, lambda et=None, event_type=event_type, **kw: self.received_events.append(event_type))

        self.bus.publish("scene_added", scene_id=1)
        self.bus.publish("scene_updated", scene_id=2)
        self.bus.publish("scene_deleted", scene_id=3)

        self.assertEqual(len(self.received_events), 3)


if __name__ == "__main__":
    unittest.main()
