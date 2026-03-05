"""
创建工具 - 用于创建节点、角色、场景、百科条目等

包含工具:
    - create_node: 创建大纲节点
    - add_character: 添加角色
    - add_scene: 添加场景
    - add_wiki_entry: 添加百科条目
"""

from typing import Dict, Any, Callable
from . import AITool, ToolResult, ToolParameter, AIToolRegistry

from writer_app.core.commands import (
    AddNodeCommand,
    AddCharacterCommand,
    AddSceneCommand,
    AddWikiEntryCommand
)


class CreateNodeTool(AITool):
    """创建大纲节点工具。"""

    name = "create_node"
    description = "在大纲中创建新节点。可指定父节点UID，如不指定则添加到根节点下。"
    parameters = [
        ToolParameter("name", "节点名称", "string", required=True),
        ToolParameter("content", "节点内容/描述", "string", required=False, default=""),
        ToolParameter("parent_uid", "父节点UID，不指定则为根节点", "string", required=False),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        parent_uid = params.get("parent_uid")

        # 如果没有指定父节点，使用根节点
        if not parent_uid:
            root_outline = project_manager.get_outline()
            parent_uid = root_outline.get("uid")

        new_node = {
            "name": params.get("name", "新节点"),
            "content": params.get("content", ""),
            "children": []
        }

        cmd = AddNodeCommand(project_manager, parent_uid, new_node, "AI创建节点")
        success = command_executor(cmd)

        if success:
            return ToolResult.success(f"已创建节点: {new_node['name']}")
        else:
            return ToolResult.error(f"创建节点失败: {new_node['name']}")


class AddCharacterTool(AITool):
    """添加角色工具。"""

    name = "add_character"
    description = "添加新角色到剧本中，包含姓名、年龄、性别、角色定位和描述。"
    parameters = [
        ToolParameter("name", "角色姓名", "string", required=True),
        ToolParameter("age", "年龄", "string", required=False, default=""),
        ToolParameter("gender", "性别", "string", required=False, default=""),
        ToolParameter("role", "角色定位（如主角、反派、配角）", "string", required=False, default=""),
        ToolParameter("description", "角色描述", "string", required=False, default=""),
        ToolParameter("tags", "标签列表", "array", required=False, default=[]),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        char_data = {
            "name": params.get("name", "新角色"),
            "age": params.get("age", ""),
            "gender": params.get("gender", ""),
            "role": params.get("role", ""),
            "description": params.get("description", ""),
            "tags": params.get("tags", [])
        }

        cmd = AddCharacterCommand(project_manager, char_data, "AI创建角色")
        success = command_executor(cmd)

        if success:
            return ToolResult.success(f"已创建角色: {char_data['name']}")
        else:
            return ToolResult.error(f"创建角色失败: {char_data['name']}")


class AddSceneTool(AITool):
    """添加场景工具。"""

    name = "add_scene"
    description = "添加新场景到剧本中，包含场景名、内容、登场角色、地点和时间。"
    parameters = [
        ToolParameter("name", "场景名称", "string", required=True),
        ToolParameter("content", "场景内容/剧本", "string", required=False, default=""),
        ToolParameter("characters", "登场角色名列表", "array", required=False, default=[]),
        ToolParameter("location", "地点", "string", required=False, default=""),
        ToolParameter("time", "时间", "string", required=False, default=""),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        scene_data = {
            "name": params.get("name", "新场景"),
            "content": params.get("content", ""),
            "characters": params.get("characters", []),
            "location": params.get("location", ""),
            "time": params.get("time", "")
        }

        cmd = AddSceneCommand(project_manager, scene_data, "AI创建场景")
        success = command_executor(cmd)

        if success:
            return ToolResult.success(f"已创建场景: {scene_data['name']}")
        else:
            return ToolResult.error(f"创建场景失败: {scene_data['name']}")


class AddWikiEntryTool(AITool):
    """添加百科条目工具。"""

    name = "add_wiki_entry"
    description = "添加新的世界观/百科条目，包含名称、分类和内容。"
    parameters = [
        ToolParameter("name", "条目名称", "string", required=True),
        ToolParameter("content", "条目内容", "string", required=False, default=""),
        ToolParameter("category", "分类（人物/地点/物品/势力/设定/其他）", "string", required=False, default="其他"),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        entry_data = {
            "name": params.get("name", "新条目"),
            "content": params.get("content", ""),
            "category": params.get("category", "其他")
        }

        cmd = AddWikiEntryCommand(project_manager, entry_data, "AI创建百科")
        success = command_executor(cmd)

        if success:
            return ToolResult.success(f"已创建百科条目: {entry_data['name']}")
        else:
            return ToolResult.error(f"创建百科条目失败: {entry_data['name']}")


class AddIdeaTool(AITool):
    """添加灵感工具。"""

    name = "add_idea"
    description = "添加新灵感到灵感收集箱。"
    parameters = [
        ToolParameter("content", "灵感内容", "string", required=True),
        ToolParameter("tags", "标签列表", "array", required=False, default=[]),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        content = params.get("content", "")

        if not content:
            return ToolResult.error("灵感内容为空")

        tags = params.get("tags", [])
        idea = project_manager.add_idea(content, tags)

        if idea:
            preview = content[:20] + "..." if len(content) > 20 else content
            return ToolResult.success(f"已添加灵感: {preview}")
        else:
            return ToolResult.error("添加灵感失败")


def register_tools(registry: 'AIToolRegistry') -> None:
    """注册所有创建工具。"""
    registry.register(CreateNodeTool())
    registry.register(AddCharacterTool())
    registry.register(AddSceneTool())
    registry.register(AddWikiEntryTool())
    registry.register(AddIdeaTool())
