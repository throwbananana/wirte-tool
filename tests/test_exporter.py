"""
导出器插件系统单元测试
"""

import unittest
from writer_app.core.models import ProjectManager
from writer_app.core.exporter import (
    ExportFormat, ExporterRegistry, ExportResult
)


class TestExportResult(unittest.TestCase):
    def test_success_result(self):
        """测试成功结果。"""
        result = ExportResult(success=True, message="导出成功", file_path="/path/to/file.md")
        self.assertTrue(result.success)
        self.assertEqual(result.message, "导出成功")
        self.assertEqual(result.file_path, "/path/to/file.md")

    def test_failure_result(self):
        """测试失败结果。"""
        result = ExportResult(success=False, message="导出失败")
        self.assertFalse(result.success)
        self.assertIsNone(result.file_path)


class TestExporterRegistry(unittest.TestCase):
    def test_builtin_formats_registered(self):
        """测试内置格式已注册。"""
        formats = ExporterRegistry.list_keys()
        self.assertIn("markdown", formats)
        self.assertIn("html", formats)
        self.assertIn("fountain", formats)
        self.assertIn("fdx", formats)

    def test_get_format(self):
        """测试获取格式信息。"""
        md = ExporterRegistry.get("markdown")
        self.assertIsNotNone(md)
        self.assertEqual(md.key, "markdown")

    def test_get_display_name(self):
        """测试获取显示名称。"""
        name = ExporterRegistry.get_display_name("markdown")
        self.assertIn("Markdown", name)

    def test_get_file_extension(self):
        """测试获取文件扩展名。"""
        ext = ExporterRegistry.get_file_extension("markdown")
        self.assertEqual(ext, ".md")

        ext_html = ExporterRegistry.get_file_extension("html")
        self.assertEqual(ext_html, ".html")

    def test_export_markdown(self):
        """测试导出Markdown。"""
        pm = ProjectManager()
        # 设置测试数据
        pm.project_data["script"]["title"] = "测试剧本"
        pm.project_data["script"]["scenes"].append({
            "name": "场景1",
            "location": "咖啡厅",
            "time": "下午",
            "content": "测试内容",
            "characters": ["张三"]
        })

        result = ExporterRegistry.export("markdown", pm)
        self.assertTrue(result.success)
        self.assertIn("测试剧本", result.content)
        self.assertIn("场景1", result.content)
        self.assertIn("测试内容", result.content)

    def test_export_unknown_format(self):
        """测试导出未知格式。"""
        pm = ProjectManager()
        result = ExporterRegistry.export("nonexistent_format", pm)
        self.assertFalse(result.success)
        self.assertIn("Unknown", result.message)

    def test_list_formats(self):
        """测试列出所有格式。"""
        formats = ExporterRegistry.list_keys()
        self.assertIsInstance(formats, list)
        self.assertTrue(len(formats) >= 4)

    def test_get_available_formats(self):
        """测试获取可用格式详情。"""
        available = ExporterRegistry.get_available_formats()
        self.assertTrue(len(available) >= 4)

        # 检查每个格式都有必要的属性
        for fmt in available:
            self.assertIn("key", fmt)
            self.assertIn("display_name", fmt)
            self.assertIn("file_extension", fmt)

    def test_export_with_options(self):
        """测试带选项的导出。"""
        pm = ProjectManager()
        pm.project_data["script"]["title"] = "测试"

        # 使用选项
        result = ExporterRegistry.export("markdown", pm, include_outline=True)
        self.assertTrue(result.success)


class TestMarkdownExport(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()
        self.pm.project_data["script"]["title"] = "测试剧本"
        self.pm.project_data["script"]["scenes"] = [
            {
                "name": "第一场",
                "location": "办公室",
                "time": "早上",
                "content": "张三走进办公室。\n张三：早上好！",
                "characters": ["张三"]
            }
        ]
        self.pm.project_data["script"]["characters"] = [
            {"name": "张三", "description": "主角"}
        ]

    def test_markdown_has_title(self):
        """测试Markdown包含标题。"""
        result = ExporterRegistry.export("markdown", self.pm)
        self.assertIn("测试剧本", result.content)

    def test_markdown_has_scenes(self):
        """测试Markdown包含场景。"""
        result = ExporterRegistry.export("markdown", self.pm)
        self.assertIn("第一场", result.content)
        self.assertIn("办公室", result.content)

    def test_markdown_has_dialogue(self):
        """测试Markdown包含对话。"""
        result = ExporterRegistry.export("markdown", self.pm)
        self.assertIn("张三", result.content)


class TestFountainExport(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()
        self.pm.project_data["script"]["title"] = "测试电影"
        self.pm.project_data["script"]["scenes"] = [
            {
                "name": "内景 - 办公室 - 日",
                "location": "办公室",
                "time": "白天",
                "content": "张三\n你好！\n\n李四\n你好！",
                "characters": ["张三", "李四"]
            }
        ]

    def test_fountain_format(self):
        """测试Fountain格式输出。"""
        result = ExporterRegistry.export("fountain", self.pm)
        self.assertTrue(result.success)
        # Fountain格式应该包含场景标题
        self.assertIn("测试电影", result.content.upper() if result.content else "")


class TestHTMLExport(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()
        self.pm.project_data["script"]["title"] = "HTML测试"

    def test_html_has_structure(self):
        """测试HTML包含基本结构。"""
        result = ExporterRegistry.export("html", self.pm)
        self.assertTrue(result.success)
        content = result.content or ""
        self.assertIn("<html", content.lower())
        self.assertIn("HTML测试", content)


if __name__ == "__main__":
    unittest.main()
