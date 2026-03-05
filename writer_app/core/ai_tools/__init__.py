"""
AI工具插件系统 - 提供可扩展的AI工具注册和执行机制

用法:
    from writer_app.core.ai_tools import AIToolRegistry, AITool, ToolResult

    # 定义工具
    class MyTool(AITool):
        name = "my_tool"
        description = "我的自定义工具"

        def execute(self, project_manager, command_executor, params):
            # 工具逻辑
            return ToolResult.success("操作完成")

    # 注册工具
    AIToolRegistry.register(MyTool())

    # 执行工具
    result = AIToolRegistry.execute("my_tool", project_manager, command_executor, {"param1": "value"})
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """工具执行结果。"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化或测试断言。"""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data
        }

    @classmethod
    def ok(cls, message: str, data: Dict[str, Any] = None) -> 'ToolResult':
        """创建成功结果。"""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error(cls, message: str, data: Dict[str, Any] = None) -> 'ToolResult':
        """创建失败结果。"""
        return cls(success=False, message=message, data=data)

    @classmethod
    def fail(cls, message: str, data: Dict[str, Any] = None) -> 'ToolResult':
        """创建失败结果（别名）。"""
        return cls.error(message, data)


# 保持成功别名，同时避免与字段名冲突
ToolResult.success = classmethod(ToolResult.ok.__func__)


@dataclass
class ToolParameter:
    """工具参数定义。"""
    name: str
    description: str
    type: str = "string"  # string, number, boolean, array, object
    required: bool = False
    default: Any = None


class AITool(ABC):
    """
    AI工具基类。所有工具必须继承此类。

    属性:
        name: 工具名称（唯一标识符）
        description: 工具描述（供AI理解）
        parameters: 参数定义列表
    """

    name: str = ""
    description: str = ""
    parameters: List[ToolParameter] = []

    @abstractmethod
    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        """
        执行工具。

        Args:
            project_manager: ProjectManager实例
            command_executor: 命令执行函数 (command) -> bool
            params: AI传递的参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        验证参数。

        Args:
            params: 待验证参数

        Returns:
            错误信息，如果有效返回None
        """
        for param in self.parameters:
            if param.required and param.name not in params:
                return f"缺少必需参数: {param.name}"
        return None

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的JSON Schema（供AI使用）。"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class AIToolRegistry:
    """
    AI工具注册表。管理所有已注册的工具。
    """

    _tools: Dict[str, AITool] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, tool: AITool) -> None:
        """
        注册工具。

        Args:
            tool: AITool实例
        """
        if not tool.name:
            raise ValueError("工具必须有名称")

        if tool.name in cls._tools:
            logger.warning(f"工具 '{tool.name}' 已存在，将被覆盖")

        cls._tools[tool.name] = tool
        logger.debug(f"注册AI工具: {tool.name}")

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        取消注册工具。

        Args:
            name: 工具名称

        Returns:
            是否成功移除
        """
        if name in cls._tools:
            del cls._tools[name]
            return True
        return False

    @classmethod
    def get(cls, name: str) -> Optional[AITool]:
        """
        获取工具。

        Args:
            name: 工具名称

        Returns:
            AITool实例或None
        """
        cls._ensure_initialized()
        return cls._tools.get(name)

    @classmethod
    def execute(
        cls,
        name: str,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        """
        执行工具。

        Args:
            name: 工具名称
            project_manager: ProjectManager实例
            command_executor: 命令执行函数
            params: 参数字典

        Returns:
            ToolResult: 执行结果
        """
        cls._ensure_initialized()

        tool = cls._tools.get(name)
        if not tool:
            return ToolResult.error(f"未知工具: {name}")

        # 验证参数
        validation_error = tool.validate_params(params)
        if validation_error:
            return ToolResult.error(validation_error)

        try:
            return tool.execute(project_manager, command_executor, params)
        except Exception as e:
            logger.error(f"工具执行错误 [{name}]: {e}", exc_info=True)
            return ToolResult.error(f"执行错误: {str(e)}")

    @classmethod
    def list_tools(cls) -> List[str]:
        """获取所有已注册工具的名称列表。"""
        cls._ensure_initialized()
        return list(cls._tools.keys())

    @classmethod
    def get_all_tools(cls) -> Dict[str, AITool]:
        """获取所有已注册的工具。"""
        cls._ensure_initialized()
        return cls._tools.copy()

    @classmethod
    def get_tools_schema(cls) -> List[Dict[str, Any]]:
        """获取所有工具的Schema（供AI使用）。"""
        cls._ensure_initialized()
        return [tool.get_schema() for tool in cls._tools.values()]

    @classmethod
    def clear(cls) -> None:
        """清除所有已注册的工具（用于测试）。"""
        cls._tools.clear()
        cls._initialized = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """确保内置工具已加载。"""
        if cls._initialized:
            return

        cls._initialized = True

        # 延迟导入并注册所有内置工具
        try:
            from . import creation_tools
            from . import editing_tools
            from . import navigation_tools
            from . import timeline_tools
            from . import evidence_tools
            from . import asset_tools
            # 新增工具模块
            from . import analysis_tools
            from . import batch_tools
            from . import validation_tools
            from . import query_tools
            # 题材专属工具
            from . import suspense_tools
            from . import romance_tools
            from . import galgame_tools

            # 注册所有工具
            for module in [creation_tools, editing_tools, navigation_tools,
                          timeline_tools, evidence_tools, asset_tools,
                          analysis_tools, batch_tools, validation_tools, query_tools,
                          suspense_tools, romance_tools, galgame_tools]:
                if hasattr(module, 'register_tools'):
                    module.register_tools(cls)

            logger.info(f"已加载 {len(cls._tools)} 个AI工具")
        except ImportError as e:
            logger.warning(f"加载AI工具模块失败: {e}")


# 工具装饰器（简化注册）
def ai_tool(name: str, description: str = "", parameters: List[ToolParameter] = None):
    """
    工具装饰器，用于将函数注册为AI工具。

    用法:
        @ai_tool("my_tool", "我的工具描述")
        def my_tool(project_manager, command_executor, params):
            return ToolResult.success("完成")
    """
    if parameters is None:
        parameters = []

    def decorator(func: Callable) -> Callable:
        class FunctionTool(AITool):
            pass

        FunctionTool.name = name
        FunctionTool.description = description or func.__doc__ or ""
        FunctionTool.parameters = parameters

        def execute(self, project_manager, command_executor, params):
            return func(project_manager, command_executor, params)

        FunctionTool.execute = execute

        # 自动注册
        AIToolRegistry.register(FunctionTool())

        return func

    return decorator


# 导出
__all__ = [
    'AITool',
    'AIToolRegistry',
    'ToolResult',
    'ToolParameter',
    'ai_tool'
]
