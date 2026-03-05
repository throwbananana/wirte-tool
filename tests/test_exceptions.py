"""
测试自定义异常模块。
"""
import unittest

from writer_app.core.exceptions import (
    WriterToolError,
    ProjectError,
    ProjectLoadError,
    ProjectSaveError,
    ProjectValidationError,
    AIServiceError,
    AIConnectionError,
    AITimeoutError,
    AIResponseError,
    AIConfigError,
    ValidationError,
    RequiredFieldError,
    DuplicateError,
    InvalidFormatError,
    CommandError,
    CommandExecutionError,
    CommandUndoError,
    ResourceError,
    ResourceNotFoundError,
    ResourceLimitError,
    ExportError,
    ExportFormatError
)


class TestWriterToolError(unittest.TestCase):
    """测试基础异常类。"""

    def test_basic_error(self):
        """测试基本错误。"""
        error = WriterToolError("测试错误")
        self.assertEqual(str(error), "测试错误")
        self.assertEqual(error.message, "测试错误")
        self.assertIsNone(error.cause)

    def test_error_with_cause(self):
        """测试带原因的错误。"""
        cause = ValueError("原始错误")
        error = WriterToolError("包装错误", cause=cause)
        self.assertIn("原因", str(error))
        self.assertEqual(error.cause, cause)


class TestProjectErrors(unittest.TestCase):
    """测试项目相关异常。"""

    def test_project_load_error(self):
        """测试项目加载错误。"""
        error = ProjectLoadError("无法加载", file_path="/test/path.writerproj")
        self.assertEqual(error.file_path, "/test/path.writerproj")
        self.assertIn("无法加载", str(error))

    def test_project_save_error(self):
        """测试项目保存错误。"""
        error = ProjectSaveError("保存失败", file_path="/test/path.writerproj")
        self.assertEqual(error.file_path, "/test/path.writerproj")

    def test_project_validation_error(self):
        """测试项目验证错误。"""
        errors = ["缺少字段A", "缺少字段B"]
        error = ProjectValidationError("验证失败", errors=errors)
        self.assertEqual(error.errors, errors)


class TestAIServiceErrors(unittest.TestCase):
    """测试 AI 服务异常。"""

    def test_ai_service_error_retryable(self):
        """测试可重试的 AI 错误。"""
        error = AIServiceError("服务错误", retryable=True)
        self.assertTrue(error.retryable)

    def test_ai_connection_error(self):
        """测试 AI 连接错误（默认可重试）。"""
        error = AIConnectionError()
        self.assertTrue(error.retryable)
        self.assertIn("无法连接", str(error))

    def test_ai_timeout_error(self):
        """测试 AI 超时错误。"""
        error = AITimeoutError(timeout=30.0)
        self.assertTrue(error.retryable)
        self.assertEqual(error.timeout, 30.0)

    def test_ai_response_error(self):
        """测试 AI 响应错误（不可重试）。"""
        error = AIResponseError("解析失败", response_text='{"invalid": }')
        self.assertFalse(error.retryable)
        self.assertEqual(error.response_text, '{"invalid": }')

    def test_ai_config_error(self):
        """测试 AI 配置错误（不可重试）。"""
        error = AIConfigError()
        self.assertFalse(error.retryable)


class TestValidationErrors(unittest.TestCase):
    """测试验证异常。"""

    def test_validation_error_with_field(self):
        """测试带字段的验证错误。"""
        error = ValidationError("无效值", field="name", value="test")
        self.assertEqual(error.field, "name")
        self.assertEqual(error.value, "test")
        self.assertIn("name", str(error))

    def test_required_field_error(self):
        """测试必填字段错误。"""
        error = RequiredFieldError("用户名")
        self.assertEqual(error.field, "用户名")
        self.assertIn("不能为空", str(error))

    def test_duplicate_error(self):
        """测试重复错误。"""
        error = DuplicateError("已存在", field="name", existing_value="张三")
        self.assertEqual(error.existing_value, "张三")

    def test_invalid_format_error(self):
        """测试格式错误。"""
        error = InvalidFormatError("格式错误", field="email", expected_format="xxx@xxx.com")
        self.assertEqual(error.expected_format, "xxx@xxx.com")


class TestCommandErrors(unittest.TestCase):
    """测试命令执行异常。"""

    def test_command_execution_error(self):
        """测试命令执行错误。"""
        error = CommandExecutionError("执行失败", command_name="AddScene")
        self.assertEqual(error.command_name, "AddScene")

    def test_command_undo_error(self):
        """测试命令撤销错误。"""
        error = CommandUndoError("撤销失败", command_name="DeleteScene")
        self.assertEqual(error.command_name, "DeleteScene")


class TestResourceErrors(unittest.TestCase):
    """测试资源异常。"""

    def test_resource_not_found_error(self):
        """测试资源未找到错误。"""
        error = ResourceNotFoundError("角色", resource_id="char_001")
        self.assertEqual(error.resource_type, "角色")
        self.assertEqual(error.resource_id, "char_001")
        self.assertIn("char_001", str(error))

    def test_resource_limit_error(self):
        """测试资源限制错误。"""
        error = ResourceLimitError("超出限制", limit=100, current=150)
        self.assertEqual(error.limit, 100)
        self.assertEqual(error.current, 150)


class TestExportErrors(unittest.TestCase):
    """测试导出异常。"""

    def test_export_error(self):
        """测试导出错误。"""
        error = ExportError("导出失败", format_type="pdf")
        self.assertEqual(error.format_type, "pdf")

    def test_export_format_error(self):
        """测试不支持的格式错误。"""
        error = ExportFormatError("xyz", supported_formats=["pdf", "docx", "html"])
        self.assertEqual(error.supported_formats, ["pdf", "docx", "html"])
        self.assertIn("xyz", str(error))


class TestExceptionHierarchy(unittest.TestCase):
    """测试异常继承层级。"""

    def test_project_errors_inherit_from_base(self):
        """测试项目错误继承自基础类。"""
        self.assertTrue(issubclass(ProjectError, WriterToolError))
        self.assertTrue(issubclass(ProjectLoadError, ProjectError))
        self.assertTrue(issubclass(ProjectSaveError, ProjectError))

    def test_ai_errors_inherit_from_base(self):
        """测试 AI 错误继承自基础类。"""
        self.assertTrue(issubclass(AIServiceError, WriterToolError))
        self.assertTrue(issubclass(AIConnectionError, AIServiceError))
        self.assertTrue(issubclass(AITimeoutError, AIServiceError))

    def test_validation_errors_inherit_from_base(self):
        """测试验证错误继承自基础类。"""
        self.assertTrue(issubclass(ValidationError, WriterToolError))
        self.assertTrue(issubclass(RequiredFieldError, ValidationError))

    def test_can_catch_by_base_class(self):
        """测试可以通过基类捕获。"""
        try:
            raise ProjectLoadError("测试")
        except WriterToolError as e:
            self.assertIsInstance(e, ProjectLoadError)


if __name__ == "__main__":
    unittest.main()
