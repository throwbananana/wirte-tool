"""
分析类 AI 工具 - 提供故事分析、节奏分析、情节检测等功能

用法:
    这些工具通过 AIToolRegistry 自动注册，可被 AI 调用
"""

from typing import Dict, List, Any
from writer_app.core.ai_tools import AITool, ToolParameter, ToolResult


class GetSceneStatsTool(AITool):
    """获取场景统计信息"""

    name = "get_scene_stats"
    description = "获取项目的场景统计信息，包括总场景数、字数、地点分布、角色出场等"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()

            # 统计数据
            total_words = 0
            locations = {}
            char_appearances = {}
            tags_count = {}

            for scene in scenes:
                content = scene.get('content', '')
                total_words += len(content)

                # 地点统计
                loc = scene.get('location', '未指定')
                locations[loc] = locations.get(loc, 0) + 1

                # 角色出场统计
                for char in scene.get('characters', []):
                    char_appearances[char] = char_appearances.get(char, 0) + 1

                # 标签统计
                for tag in scene.get('tags', []):
                    tags_count[tag] = tags_count.get(tag, 0) + 1

            stats = {
                "total_scenes": len(scenes),
                "total_characters": len(characters),
                "total_words": total_words,
                "avg_words_per_scene": total_words // len(scenes) if scenes else 0,
                "locations": locations,
                "character_appearances": char_appearances,
                "tags_distribution": tags_count
            }

            return ToolResult.success(
                message=f"场景统计完成：共 {len(scenes)} 个场景，{total_words} 字",
                data=stats
            )

        except Exception as e:
            return ToolResult.error(f"获取统计信息失败: {e}")


class AnalyzePacingTool(AITool):
    """分析故事节奏"""

    name = "analyze_pacing"
    description = "分析故事的节奏分布，识别高潮、低谷和过渡场景"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            if not scenes:
                return ToolResult.error("没有场景可分析")

            pacing_data = []
            for idx, scene in enumerate(scenes):
                content = scene.get('content', '')
                word_count = len(content)

                # 简单的节奏分析指标
                has_dialogue = '"' in content or '"' in content or '「' in content
                has_action = any(w in content for w in ['跑', '冲', '打', '杀', '逃', '追'])
                has_emotion = any(w in content for w in ['哭', '笑', '怒', '怕', '爱', '恨'])

                intensity = 0
                if has_dialogue:
                    intensity += 1
                if has_action:
                    intensity += 2
                if has_emotion:
                    intensity += 1
                if word_count > 500:
                    intensity += 1

                pacing_type = "过渡"
                if intensity >= 3:
                    pacing_type = "高潮"
                elif intensity >= 2:
                    pacing_type = "紧张"
                elif intensity <= 1:
                    pacing_type = "舒缓"

                pacing_data.append({
                    "scene_index": idx,
                    "scene_name": scene.get('name', f'场景{idx+1}'),
                    "word_count": word_count,
                    "intensity": intensity,
                    "pacing_type": pacing_type
                })

            # 统计节奏分布
            pacing_distribution = {}
            for p in pacing_data:
                t = p['pacing_type']
                pacing_distribution[t] = pacing_distribution.get(t, 0) + 1

            result = {
                "scene_pacing": pacing_data,
                "distribution": pacing_distribution,
                "total_scenes": len(scenes)
            }

            return ToolResult.success(
                message=f"节奏分析完成：高潮{pacing_distribution.get('高潮', 0)}场，"
                        f"紧张{pacing_distribution.get('紧张', 0)}场，"
                        f"舒缓{pacing_distribution.get('舒缓', 0)}场",
                data=result
            )

        except Exception as e:
            return ToolResult.error(f"节奏分析失败: {e}")


class GetCharacterArcTool(AITool):
    """获取角色发展弧线"""

    name = "get_character_arc"
    description = "分析指定角色在故事中的发展弧线，包括出场场景、关键事件等"
    parameters = [
        ToolParameter("character_name", "角色名称", "string", required=True)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            char_name = params.get("character_name", "").strip()
            if not char_name:
                return ToolResult.error("请指定角色名称")

            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()

            # 查找角色
            character = None
            for c in characters:
                if c.get('name') == char_name:
                    character = c
                    break

            if not character:
                return ToolResult.error(f"未找到角色: {char_name}")

            # 分析角色弧线
            appearances = []
            for idx, scene in enumerate(scenes):
                if char_name in scene.get('characters', []):
                    content = scene.get('content', '')
                    # 提取角色相关内容摘要
                    appearances.append({
                        "scene_index": idx,
                        "scene_name": scene.get('name', f'场景{idx+1}'),
                        "time": scene.get('time', ''),
                        "location": scene.get('location', ''),
                        "content_preview": content[:200] if content else ''
                    })

            # 角色事件
            character_events = character.get('events', [])

            arc_data = {
                "character_name": char_name,
                "description": character.get('description', ''),
                "total_appearances": len(appearances),
                "appearances": appearances,
                "events": character_events,
                "first_appearance": appearances[0]['scene_name'] if appearances else None,
                "last_appearance": appearances[-1]['scene_name'] if appearances else None
            }

            return ToolResult.success(
                message=f"角色 {char_name} 共出场 {len(appearances)} 次",
                data=arc_data
            )

        except Exception as e:
            return ToolResult.error(f"角色弧线分析失败: {e}")


class DetectPlotHolesTool(AITool):
    """检测情节漏洞"""

    name = "detect_plot_holes"
    description = "检测故事中可能存在的情节漏洞，如角色消失、时间线矛盾等"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()

            issues = []

            # 检测1: 角色突然消失
            char_last_seen = {}
            for idx, scene in enumerate(scenes):
                for char in scene.get('characters', []):
                    char_last_seen[char] = idx

            defined_chars = {c.get('name') for c in characters}
            for char, last_idx in char_last_seen.items():
                if char in defined_chars and last_idx < len(scenes) - 3:
                    # 如果主要角色在后半部分消失
                    issues.append({
                        "type": "character_disappearance",
                        "severity": "warning",
                        "message": f"角色 '{char}' 最后出现在第 {last_idx+1} 场，之后未再出现",
                        "scene_index": last_idx
                    })

            # 检测2: 空场景
            for idx, scene in enumerate(scenes):
                if not scene.get('content', '').strip():
                    issues.append({
                        "type": "empty_scene",
                        "severity": "error",
                        "message": f"场景 '{scene.get('name', idx+1)}' 内容为空",
                        "scene_index": idx
                    })

            # 检测3: 无角色场景
            for idx, scene in enumerate(scenes):
                if not scene.get('characters'):
                    issues.append({
                        "type": "no_characters",
                        "severity": "info",
                        "message": f"场景 '{scene.get('name', idx+1)}' 没有指定角色",
                        "scene_index": idx
                    })

            # 检测4: 未定义角色
            for idx, scene in enumerate(scenes):
                for char in scene.get('characters', []):
                    if char not in defined_chars:
                        issues.append({
                            "type": "undefined_character",
                            "severity": "warning",
                            "message": f"场景 '{scene.get('name', idx+1)}' 中的角色 '{char}' 未在角色列表中定义",
                            "scene_index": idx
                        })

            result = {
                "total_issues": len(issues),
                "issues": issues,
                "by_severity": {
                    "error": len([i for i in issues if i['severity'] == 'error']),
                    "warning": len([i for i in issues if i['severity'] == 'warning']),
                    "info": len([i for i in issues if i['severity'] == 'info'])
                }
            }

            return ToolResult.success(
                message=f"检测完成：发现 {len(issues)} 个潜在问题",
                data=result
            )

        except Exception as e:
            return ToolResult.error(f"情节漏洞检测失败: {e}")


def register_tools(registry):
    """注册分析工具"""
    registry.register(GetSceneStatsTool())
    registry.register(AnalyzePacingTool())
    registry.register(GetCharacterArcTool())
    registry.register(DetectPlotHolesTool())
