"""
批量操作 AI 工具 - 提供批量编辑、批量添加等功能

用法:
    这些工具通过 AIToolRegistry 自动注册，可被 AI 调用
"""

from typing import Dict, List, Any
from writer_app.core.ai_tools import AITool, ToolParameter, ToolResult
from writer_app.core.commands import (
    AddCharacterCommand, EditSceneCommand, AddSceneCommand
)


class BulkEditScenesTool(AITool):
    """批量编辑多个场景"""

    name = "bulk_edit_scenes"
    description = "批量编辑多个场景的属性，如地点、时间、标签等"
    parameters = [
        ToolParameter("scene_indices", "要编辑的场景索引列表", "array", required=True),
        ToolParameter("location", "新地点（可选）", "string", required=False),
        ToolParameter("time", "新时间（可选）", "string", required=False),
        ToolParameter("add_tags", "要添加的标签列表（可选）", "array", required=False),
        ToolParameter("remove_tags", "要移除的标签列表（可选）", "array", required=False)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scene_indices = params.get("scene_indices", [])
            if not scene_indices:
                return ToolResult.error("请指定要编辑的场景索引")

            scenes = project_manager.get_scenes()
            edited_count = 0
            errors = []

            for idx in scene_indices:
                if not isinstance(idx, int) or idx < 0 or idx >= len(scenes):
                    errors.append(f"无效的场景索引: {idx}")
                    continue

                old_scene = scenes[idx]
                new_scene = dict(old_scene)

                # 更新属性
                if params.get("location"):
                    new_scene["location"] = params["location"]
                if params.get("time"):
                    new_scene["time"] = params["time"]

                # 处理标签
                current_tags = set(new_scene.get("tags", []))
                if params.get("add_tags"):
                    current_tags.update(params["add_tags"])
                if params.get("remove_tags"):
                    current_tags -= set(params["remove_tags"])
                new_scene["tags"] = list(current_tags)

                # 执行编辑命令
                cmd = EditSceneCommand(
                    project_manager, idx, old_scene, new_scene,
                    f"批量编辑场景 {idx+1}"
                )
                if command_executor(cmd):
                    edited_count += 1
                else:
                    errors.append(f"编辑场景 {idx+1} 失败")

            result = {
                "edited_count": edited_count,
                "total_requested": len(scene_indices),
                "errors": errors
            }

            if errors:
                return ToolResult.success(
                    message=f"批量编辑完成：成功 {edited_count} 个，失败 {len(errors)} 个",
                    data=result
                )
            else:
                return ToolResult.success(
                    message=f"批量编辑完成：成功编辑 {edited_count} 个场景",
                    data=result
                )

        except Exception as e:
            return ToolResult.error(f"批量编辑失败: {e}")


class BulkAddCharactersTool(AITool):
    """批量添加角色"""

    name = "bulk_add_characters"
    description = "批量添加多个角色到项目中"
    parameters = [
        ToolParameter("characters", "角色列表，每个包含 name 和 description", "array", required=True)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            characters = params.get("characters", [])
            if not characters:
                return ToolResult.error("请提供要添加的角色列表")

            existing_chars = {c.get("name") for c in project_manager.get_characters()}
            added_count = 0
            skipped = []
            errors = []

            for char_data in characters:
                if not isinstance(char_data, dict):
                    errors.append(f"无效的角色数据: {char_data}")
                    continue

                name = char_data.get("name", "").strip()
                if not name:
                    errors.append("角色名称不能为空")
                    continue

                if name in existing_chars:
                    skipped.append(name)
                    continue

                # 构建角色数据
                new_char = {
                    "name": name,
                    "description": char_data.get("description", ""),
                    "tags": char_data.get("tags", []),
                    "events": []
                }

                cmd = AddCharacterCommand(
                    project_manager, new_char,
                    f"添加角色: {name}"
                )
                if command_executor(cmd):
                    added_count += 1
                    existing_chars.add(name)
                else:
                    errors.append(f"添加角色 '{name}' 失败")

            result = {
                "added_count": added_count,
                "skipped": skipped,
                "errors": errors
            }

            msg_parts = [f"成功添加 {added_count} 个角色"]
            if skipped:
                msg_parts.append(f"跳过 {len(skipped)} 个已存在角色")
            if errors:
                msg_parts.append(f"失败 {len(errors)} 个")

            return ToolResult.success(
                message="批量添加完成：" + "，".join(msg_parts),
                data=result
            )

        except Exception as e:
            return ToolResult.error(f"批量添加角色失败: {e}")


class BatchTagScenesTool(AITool):
    """批量为场景添加标签"""

    name = "batch_tag_scenes"
    description = "批量为多个场景添加或移除标签"
    parameters = [
        ToolParameter("scene_indices", "场景索引列表，使用 'all' 表示所有场景", "array", required=True),
        ToolParameter("add_tags", "要添加的标签列表", "array", required=False),
        ToolParameter("remove_tags", "要移除的标签列表", "array", required=False)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scene_indices = params.get("scene_indices", [])
            add_tags = params.get("add_tags", [])
            remove_tags = params.get("remove_tags", [])

            if not add_tags and not remove_tags:
                return ToolResult.error("请指定要添加或移除的标签")

            scenes = project_manager.get_scenes()

            # 处理 'all' 参数
            if scene_indices == ["all"] or scene_indices == "all":
                scene_indices = list(range(len(scenes)))

            modified_count = 0
            errors = []

            for idx in scene_indices:
                if not isinstance(idx, int) or idx < 0 or idx >= len(scenes):
                    errors.append(f"无效的场景索引: {idx}")
                    continue

                old_scene = scenes[idx]
                new_scene = dict(old_scene)

                current_tags = set(new_scene.get("tags", []))
                original_tags = current_tags.copy()

                if add_tags:
                    current_tags.update(add_tags)
                if remove_tags:
                    current_tags -= set(remove_tags)

                # 只有标签有变化才执行命令
                if current_tags != original_tags:
                    new_scene["tags"] = list(current_tags)
                    cmd = EditSceneCommand(
                        project_manager, idx, old_scene, new_scene,
                        f"批量标签场景 {idx+1}"
                    )
                    if command_executor(cmd):
                        modified_count += 1
                    else:
                        errors.append(f"修改场景 {idx+1} 标签失败")

            result = {
                "modified_count": modified_count,
                "total_checked": len(scene_indices),
                "errors": errors
            }

            return ToolResult.success(
                message=f"批量标签完成：修改了 {modified_count} 个场景",
                data=result
            )

        except Exception as e:
            return ToolResult.error(f"批量标签失败: {e}")


class BulkAddScenesTool(AITool):
    """批量添加场景"""

    name = "bulk_add_scenes"
    description = "批量添加多个场景到项目中"
    parameters = [
        ToolParameter("scenes", "场景列表，每个包含 name, content, location, time, characters", "array", required=True)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes_data = params.get("scenes", [])
            if not scenes_data:
                return ToolResult.error("请提供要添加的场景列表")

            added_count = 0
            errors = []

            for scene_data in scenes_data:
                if not isinstance(scene_data, dict):
                    errors.append(f"无效的场景数据: {scene_data}")
                    continue

                name = scene_data.get("name", "").strip()
                if not name:
                    name = f"新场景 {added_count + 1}"

                new_scene = {
                    "name": name,
                    "content": scene_data.get("content", ""),
                    "location": scene_data.get("location", ""),
                    "time": scene_data.get("time", ""),
                    "characters": scene_data.get("characters", []),
                    "tags": scene_data.get("tags", [])
                }

                cmd = AddSceneCommand(
                    project_manager, new_scene,
                    f"批量添加场景: {name}"
                )
                if command_executor(cmd):
                    added_count += 1
                else:
                    errors.append(f"添加场景 '{name}' 失败")

            result = {
                "added_count": added_count,
                "total_requested": len(scenes_data),
                "errors": errors
            }

            return ToolResult.success(
                message=f"批量添加完成：成功添加 {added_count} 个场景",
                data=result
            )

        except Exception as e:
            return ToolResult.error(f"批量添加场景失败: {e}")


def register_tools(registry):
    """注册批量操作工具"""
    registry.register(BulkEditScenesTool())
    registry.register(BulkAddCharactersTool())
    registry.register(BatchTagScenesTool())
    registry.register(BulkAddScenesTool())
