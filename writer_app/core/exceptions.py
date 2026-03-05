"""
自定义异常类 - 提供更精确的错误处理

用法:
    from writer_app.core.exceptions import ProjectLoadError, AIServiceError

    try:
        project_manager.load_project(path)
    except ProjectLoadError as e:
        print(f"加载失败: {e}")
        if e.cause:
            print(f"原因: {e.cause}")
"""

from typing import Optional, Any


class WriterToolError(Exception):
    """
    Writer Tool 基础异常类。

    所有自定义异常都应继承此类。
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        Args:
            message: 错误消息
            cause: 原始异常（用于异常链）
        """
        super().__init__(message)
        self.cause = cause
        self.message = message

    def __str__(self):
        if self.cause:
            return f"{self.message} (原因: {self.cause})"
        return self.message


# --- 项目相关异常 ---

class ProjectError(WriterToolError):
    """项目操作相关的基础异常。"""
    pass


class ProjectLoadError(ProjectError):
    """项目加载错误。"""

    def __init__(self, message: str, file_path: str = None, cause: Exception = None):
        super().__init__(message, cause)
        self.file_path = file_path


class ProjectSaveError(ProjectError):
    """项目保存错误。"""

    def __init__(self, message: str, file_path: str = None, cause: Exception = None):
        super().__init__(message, cause)
        self.file_path = file_path


class ProjectValidationError(ProjectError):
    """项目数据验证错误。"""

    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


# --- AI服务异常 ---

class AIServiceError(WriterToolError):
    """AI服务相关的基础异常。"""

    def __init__(self, message: str, cause: Exception = None, retryable: bool = False):
        """
        Args:
            message: 错误消息
            cause: 原始异常
            retryable: 是否可重试
        """
        super().__init__(message, cause)
        self.retryable = retryable


class AIConnectionError(AIServiceError):
    """AI服务连接错误。"""

    def __init__(self, message: str = "无法连接到AI服务", cause: Exception = None):
        super().__init__(message, cause, retryable=True)


class AITimeoutError(AIServiceError):
    """AI服务超时错误。"""

    def __init__(self, message: str = "AI请求超时", timeout: float = None, cause: Exception = None):
        super().__init__(message, cause, retryable=True)
        self.timeout = timeout


class AIResponseError(AIServiceError):
    """AI响应解析错误。"""

    def __init__(self, message: str, response_text: str = None, cause: Exception = None):
        super().__init__(message, cause, retryable=False)
        self.response_text = response_text


class AIConfigError(AIServiceError):
    """AI配置错误。"""

    def __init__(self, message: str = "AI接口配置不完整"):
        super().__init__(message, retryable=False)


# --- 数据验证异常 ---

class ValidationError(WriterToolError):
    """数据验证错误。"""

    def __init__(self, message: str, field: str = None, value: Any = None):
        """
        Args:
            message: 错误消息
            field: 出错的字段名
            value: 出错的值
        """
        super().__init__(message)
        self.field = field
        self.value = value

    def __str__(self):
        if self.field:
            return f"{self.field}: {self.message}"
        return self.message


class RequiredFieldError(ValidationError):
    """必填字段缺失。"""

    def __init__(self, field: str):
        super().__init__(f"不能为空", field=field)


class DuplicateError(ValidationError):
    """重复数据错误。"""

    def __init__(self, message: str, field: str = None, existing_value: Any = None):
        super().__init__(message, field)
        self.existing_value = existing_value


class InvalidFormatError(ValidationError):
    """格式无效错误。"""

    def __init__(self, message: str, field: str = None, expected_format: str = None):
        super().__init__(message, field)
        self.expected_format = expected_format


# --- 命令执行异常 ---

class CommandError(WriterToolError):
    """命令执行相关的基础异常。"""
    pass


class CommandExecutionError(CommandError):
    """命令执行失败。"""

    def __init__(self, message: str, command_name: str = None, cause: Exception = None):
        super().__init__(message, cause)
        self.command_name = command_name


class CommandUndoError(CommandError):
    """命令撤销失败。"""

    def __init__(self, message: str, command_name: str = None, cause: Exception = None):
        super().__init__(message, cause)
        self.command_name = command_name


# --- 资源相关异常 ---

class ResourceError(WriterToolError):
    """资源操作相关的基础异常。"""
    pass


class ResourceNotFoundError(ResourceError):
    """资源未找到。"""

    def __init__(self, resource_type: str, resource_id: str = None):
        message = f"{resource_type} 未找到"
        if resource_id:
            message = f"{resource_type} '{resource_id}' 未找到"
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ResourceLimitError(ResourceError):
    """资源限制错误。"""

    def __init__(self, message: str, limit: int = None, current: int = None):
        super().__init__(message)
        self.limit = limit
        self.current = current


# --- 导出相关异常 ---

class ExportError(WriterToolError):
    """导出相关的基础异常。"""

    def __init__(self, message: str, format_type: str = None, cause: Exception = None):
        super().__init__(message, cause)
        self.format_type = format_type


class ExportFormatError(ExportError):
    """导出格式不支持。"""

    def __init__(self, format_type: str, supported_formats: list = None):
        message = f"不支持的导出格式: {format_type}"
        super().__init__(message, format_type)
        self.supported_formats = supported_formats or []
