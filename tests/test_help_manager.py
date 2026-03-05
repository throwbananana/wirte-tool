# -*- coding: utf-8 -*-
"""
帮助管理器测试模块
"""

import unittest
import sys
import os

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from writer_app.core.help_manager import HelpManager, get_help_manager, HelpTopic, ShortcutInfo


class TestHelpManager(unittest.TestCase):
    """测试帮助管理器"""

    def setUp(self):
        """测试前准备"""
        self.help_manager = get_help_manager()

    def test_singleton(self):
        """测试单例模式"""
        hm1 = get_help_manager()
        hm2 = get_help_manager()
        self.assertIs(hm1, hm2)

    def test_get_all_topics(self):
        """测试获取所有主题"""
        topics = self.help_manager.get_all_topics()
        self.assertIsInstance(topics, list)
        self.assertGreater(len(topics), 0)
        for topic in topics:
            self.assertIsInstance(topic, HelpTopic)

    def test_get_topic(self):
        """测试获取单个主题"""
        topic = self.help_manager.get_topic("getting_started")
        self.assertIsNotNone(topic)
        self.assertEqual(topic.id, "getting_started")
        self.assertIn("快速入门", topic.title)

    def test_get_nonexistent_topic(self):
        """测试获取不存在的主题"""
        topic = self.help_manager.get_topic("nonexistent")
        self.assertIsNone(topic)

    def test_search_topics(self):
        """测试搜索功能"""
        # 搜索AI相关主题
        results = self.help_manager.search_topics("AI")
        self.assertGreater(len(results), 0)

        # 搜索不存在的内容
        results = self.help_manager.search_topics("xyznonsense123")
        self.assertEqual(len(results), 0)

    def test_get_shortcuts(self):
        """测试获取快捷键"""
        shortcuts = self.help_manager.get_shortcuts()
        self.assertIsInstance(shortcuts, list)
        self.assertGreater(len(shortcuts), 0)
        for shortcut in shortcuts:
            self.assertIsInstance(shortcut, ShortcutInfo)

    def test_get_shortcuts_by_category(self):
        """测试按分类获取快捷键"""
        # 获取编辑类快捷键
        shortcuts = self.help_manager.get_shortcuts("编辑")
        self.assertGreater(len(shortcuts), 0)
        for shortcut in shortcuts:
            self.assertEqual(shortcut.category, "编辑")

    def test_get_shortcut_categories(self):
        """测试获取快捷键分类列表"""
        categories = self.help_manager.get_shortcut_categories()
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)
        self.assertIn("文件", categories)
        self.assertIn("编辑", categories)

    def test_get_context_help(self):
        """测试上下文帮助"""
        # 获取大纲上下文帮助
        help_text = self.help_manager.get_context_help("outline")
        self.assertIsInstance(help_text, str)
        self.assertGreater(len(help_text), 0)

        # 获取不存在的上下文
        help_text = self.help_manager.get_context_help("nonexistent")
        self.assertEqual(help_text, "")

    def test_get_app_info(self):
        """测试获取应用信息"""
        info = self.help_manager.get_app_info()
        self.assertIsInstance(info, dict)
        self.assertIn("name", info)
        self.assertIn("version", info)
        self.assertIn("description", info)
        self.assertIn("features", info)

    def test_format_shortcuts_text(self):
        """测试格式化快捷键文本"""
        text = self.help_manager.format_shortcuts_text()
        self.assertIsInstance(text, str)
        self.assertIn("快捷键速查", text)
        self.assertIn("Ctrl+S", text)

    def test_topic_has_required_fields(self):
        """测试主题包含必需字段"""
        for topic in self.help_manager.get_all_topics():
            self.assertTrue(topic.id)
            self.assertTrue(topic.title)
            self.assertTrue(topic.content)
            self.assertIsInstance(topic.keywords, list)

    def test_shortcut_has_required_fields(self):
        """测试快捷键包含必需字段"""
        for shortcut in self.help_manager.get_shortcuts():
            self.assertTrue(shortcut.key)
            self.assertTrue(shortcut.description)
            self.assertTrue(shortcut.category)


class TestHelpTopic(unittest.TestCase):
    """测试帮助主题数据类"""

    def test_create_topic(self):
        """测试创建帮助主题"""
        topic = HelpTopic(
            id="test",
            title="测试主题",
            icon="test_icon",
            content="测试内容",
            keywords=["测试", "test"]
        )
        self.assertEqual(topic.id, "test")
        self.assertEqual(topic.title, "测试主题")
        self.assertEqual(topic.icon, "test_icon")
        self.assertEqual(topic.content, "测试内容")
        self.assertEqual(topic.keywords, ["测试", "test"])

    def test_default_keywords(self):
        """测试默认关键词为空列表"""
        topic = HelpTopic(
            id="test",
            title="测试",
            icon="icon",
            content="内容"
        )
        self.assertEqual(topic.keywords, [])


class TestShortcutInfo(unittest.TestCase):
    """测试快捷键信息数据类"""

    def test_create_shortcut(self):
        """测试创建快捷键信息"""
        shortcut = ShortcutInfo(
            key="Ctrl+T",
            description="测试快捷键",
            category="测试"
        )
        self.assertEqual(shortcut.key, "Ctrl+T")
        self.assertEqual(shortcut.description, "测试快捷键")
        self.assertEqual(shortcut.category, "测试")


if __name__ == "__main__":
    unittest.main()
