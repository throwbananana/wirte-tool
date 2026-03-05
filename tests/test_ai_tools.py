"""
AI工具注册表单元测试
"""

import unittest
from writer_app.core.ai_tools import AITool, AIToolRegistry, ToolResult


class MockTool(AITool):
    """用于测试的模拟工具。"""
    name = "mock_tool"
    description = "A mock tool for testing"

    def execute(self, project_manager, command_executor, params):
        return ToolResult(
            success=True,
            message="Mock tool executed",
            data={"param_value": params.get("test_param")}
        )


class FailingTool(AITool):
    """总是失败的工具。"""
    name = "failing_tool"
    description = "A tool that always fails"

    def execute(self, project_manager, command_executor, params):
        return ToolResult(
            success=False,
            message="Tool intentionally failed"
        )


class TestAIToolRegistry(unittest.TestCase):
    def setUp(self):
        # 保存原始注册表状态
        self.original_tools = AIToolRegistry._tools.copy()

    def tearDown(self):
        # 恢复原始注册表状态
        AIToolRegistry._tools = self.original_tools

    def test_register_tool(self):
        """测试注册工具。"""
        tool = MockTool()
        AIToolRegistry.register(tool)

        self.assertIn("mock_tool", AIToolRegistry._tools)
        self.assertIs(AIToolRegistry._tools["mock_tool"], tool)

    def test_get_tool(self):
        """测试获取工具。"""
        tool = MockTool()
        AIToolRegistry.register(tool)

        retrieved = AIToolRegistry.get("mock_tool")
        self.assertIs(retrieved, tool)

    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具返回None。"""
        result = AIToolRegistry.get("nonexistent_tool")
        self.assertIsNone(result)

    def test_execute_tool(self):
        """测试执行工具。"""
        tool = MockTool()
        AIToolRegistry.register(tool)

        result = AIToolRegistry.execute(
            "mock_tool",
            project_manager=None,
            command_executor=None,
            params={"test_param": "test_value"}
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data["param_value"], "test_value")

    def test_execute_nonexistent_tool(self):
        """测试执行不存在的工具返回失败结果。"""
        result = AIToolRegistry.execute(
            "nonexistent_tool",
            project_manager=None,
            command_executor=None,
            params={}
        )

        self.assertFalse(result.success)
        self.assertIn("未知工具", result.message)

    def test_execute_failing_tool(self):
        """测试执行失败的工具。"""
        tool = FailingTool()
        AIToolRegistry.register(tool)

        result = AIToolRegistry.execute(
            "failing_tool",
            project_manager=None,
            command_executor=None,
            params={}
        )

        self.assertFalse(result.success)

    def test_list_tools(self):
        """测试列出所有工具。"""
        tool1 = MockTool()
        tool1.name = "tool1"
        tool2 = MockTool()
        tool2.name = "tool2"

        AIToolRegistry.register(tool1)
        AIToolRegistry.register(tool2)

        tools = AIToolRegistry.list_tools()

        self.assertIn("tool1", tools)
        self.assertIn("tool2", tools)

    def test_tool_result_to_dict(self):
        """测试ToolResult转换为字典。"""
        result = ToolResult(
            success=True,
            message="Test message",
            data={"key": "value"}
        )

        d = result.to_dict()

        self.assertEqual(d["success"], True)
        self.assertEqual(d["message"], "Test message")
        self.assertEqual(d["data"]["key"], "value")

    def test_register_duplicate_tool(self):
        """测试注册重复工具会覆盖。"""
        tool1 = MockTool()
        tool2 = MockTool()

        AIToolRegistry.register(tool1)
        AIToolRegistry.register(tool2)

        self.assertIs(AIToolRegistry._tools["mock_tool"], tool2)


class TestBuiltinTools(unittest.TestCase):
    """测试内置工具是否已注册。"""

    def test_builtin_tools_loaded(self):
        """测试内置工具已加载。"""
        # 导入时会自动注册工具
        from writer_app.core.ai_tools.creation_tools import (
            CreateNodeTool, AddCharacterTool, AddSceneTool
        )

        # 验证这些工具类存在
        self.assertTrue(hasattr(CreateNodeTool, 'name'))
        self.assertTrue(hasattr(AddCharacterTool, 'name'))
        self.assertTrue(hasattr(AddSceneTool, 'name'))


if __name__ == "__main__":
    unittest.main()
