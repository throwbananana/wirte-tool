"""
编辑工具 - 用于更新场景内容、角色信息等

包含工具:
    - update_scene_content: 更新场景内容
    - update_character: 更新角色信息
"""

from typing import Dict, Any, Callable
from . import AITool, ToolResult, ToolParameter, AIToolRegistry

from writer_app.core.commands import (
    EditSceneContentCommand,
    EditCharacterCommand
)


class UpdateSceneContentTool(AITool):
    """更新场景内容工具。"""

    name = "update_scene_content"
    description = "更新指定场景的内容。通过场景名称查找场景。"
    parameters = [
        ToolParameter("scene_name", "场景名称", "string", required=True),
        ToolParameter("content", "新的场景内容", "string", required=True),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        target_name = params.get("scene_name", "")
        new_content = params.get("content", "")

        if not target_name:
            return ToolResult.error("未指定场景名称")

        scenes = project_manager.get_scenes()
        target_idx = -1

        for i, s in enumerate(scenes):
            if s.get("name") == target_name:
                target_idx = i
                break

        if target_idx >= 0:
            old_content = scenes[target_idx].get("content", "")
            cmd = EditSceneContentCommand(
                project_manager,
                target_idx,
                old_content,
                new_content,
                "AI修改场景内容"
            )
            success = command_executor(cmd)

            if success:
                return ToolResult.success(f"已更新场景 '{target_name}' 的内容")
            else:
                return ToolResult.error(f"更新场景内容失败")
        else:
            return ToolResult.error(f"找不到场景: {target_name}")


class UpdateCharacterTool(AITool):
    """更新角色信息工具。"""

    name = "update_character"
    description = "更新指定角色的信息。通过角色名称查找角色。可以更新描述、年龄、性别等字段。"
    parameters = [
        ToolParameter("name", "角色名称（用于查找）", "string", required=True),
        ToolParameter("age", "年龄（可选更新）", "string", required=False),
        ToolParameter("gender", "性别（可选更新）", "string", required=False),
        ToolParameter("role", "角色定位（可选更新）", "string", required=False),
        ToolParameter("description", "描述（可选更新）", "string", required=False),
        ToolParameter("tags", "标签列表（可选更新）", "array", required=False),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        target_name = params.get("name", "")

        if not target_name:
            return ToolResult.error("未指定角色名称")

        chars = project_manager.get_characters()
        target_idx = -1

        for i, c in enumerate(chars):
            if c.get("name") == target_name:
                target_idx = i
                break

        if target_idx >= 0:
            old_data = chars[target_idx]
            new_data = old_data.copy()

            # 更新提供的字段（不更新name以避免破坏引用）
            updatable_fields = ["age", "gender", "role", "description", "tags"]
            for field in updatable_fields:
                if field in params and params[field] is not None:
                    new_data[field] = params[field]

            cmd = EditCharacterCommand(
                project_manager,
                target_idx,
                old_data,
                new_data,
                "AI更新角色"
            )
            success = command_executor(cmd)

            if success:
                return ToolResult.success(f"已更新角色: {target_name}")
            else:
                return ToolResult.error(f"更新角色失败")
        else:
            return ToolResult.error(f"找不到角色: {target_name}")


def register_tools(registry: 'AIToolRegistry') -> None:
    """注册所有编辑工具。"""
    registry.register(UpdateSceneContentTool())
    registry.register(UpdateCharacterTool())
