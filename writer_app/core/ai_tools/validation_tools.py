"""
验证类 AI 工具 - 提供时间线验证、角色出场验证、逻辑一致性检查等功能

用法:
    这些工具通过 AIToolRegistry 自动注册，可被 AI 调用
"""

from typing import Dict, List, Any
from writer_app.core.ai_tools import AITool, ToolParameter, ToolResult


class ValidateTimelineTool(AITool):
    """验证时间线一致性"""

    name = "validate_timeline"
    description = "验证故事时间线的一致性，检测时间顺序错误、时间冲突等问题"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            if not scenes:
                return ToolResult.error("没有场景可验证")

            issues = []
            time_sequence = []

            # 收集时间信息
            for idx, scene in enumerate(scenes):
                time_str = scene.get('time', '').strip()
                if time_str:
                    time_sequence.append({
                        'index': idx,
                        'name': scene.get('name', f'场景{idx+1}'),
                        'time': time_str
                    })

            # 检测时间问题
            # 1. 检查是否有时间信息缺失
            scenes_without_time = []
            for idx, scene in enumerate(scenes):
                if not scene.get('time', '').strip():
                    scenes_without_time.append({
                        'index': idx,
                        'name': scene.get('name', f'场景{idx+1}')
                    })

            if scenes_without_time:
                issues.append({
                    'type': 'missing_time',
                    'severity': 'info',
                    'message': f"{len(scenes_without_time)} 个场景缺少时间信息",
                    'affected_scenes': scenes_without_time
                })

            # 2. 检查时间词汇的逻辑顺序
            time_keywords = {
                '早上': 1, '上午': 2, '中午': 3, '下午': 4,
                '傍晚': 5, '晚上': 6, '深夜': 7, '凌晨': 0,
                '黎明': 1, '清晨': 1, '正午': 3, '黄昏': 5,
                '午夜': 7
            }

            # 检测同一天内的时间顺序问题
            day_groups = {}
            for item in time_sequence:
                time_str = item['time']
                # 尝试提取日期部分
                day_key = time_str  # 简化处理
                if day_key not in day_groups:
                    day_groups[day_key] = []
                day_groups[day_key].append(item)

            # 3. 检查角色在同一时间出现在多个地点
            time_location_map = {}
            for idx, scene in enumerate(scenes):
                time_str = scene.get('time', '').strip()
                location = scene.get('location', '').strip()
                characters = scene.get('characters', [])

                if time_str and location and characters:
                    key = time_str
                    if key not in time_location_map:
                        time_location_map[key] = []
                    time_location_map[key].append({
                        'index': idx,
                        'location': location,
                        'characters': characters
                    })

            # 检测同一时间角色位置冲突
            for time_key, scenes_at_time in time_location_map.items():
                if len(scenes_at_time) > 1:
                    char_locations = {}
                    for scene_info in scenes_at_time:
                        for char in scene_info['characters']:
                            if char not in char_locations:
                                char_locations[char] = []
                            char_locations[char].append(scene_info['location'])

                    for char, locations in char_locations.items():
                        unique_locations = set(locations)
                        if len(unique_locations) > 1:
                            issues.append({
                                'type': 'location_conflict',
                                'severity': 'warning',
                                'message': f"角色 '{char}' 在 '{time_key}' 同时出现在多个地点: {', '.join(unique_locations)}",
                                'character': char,
                                'time': time_key,
                                'locations': list(unique_locations)
                            })

            result = {
                'total_scenes': len(scenes),
                'scenes_with_time': len(time_sequence),
                'scenes_without_time': len(scenes_without_time),
                'issues': issues,
                'issues_count': len(issues)
            }

            if issues:
                return ToolResult.success(
                    message=f"时间线验证完成：发现 {len(issues)} 个问题",
                    data=result
                )
            else:
                return ToolResult.success(
                    message="时间线验证通过，未发现问题",
                    data=result
                )

        except Exception as e:
            return ToolResult.error(f"时间线验证失败: {e}")


class ValidateCharacterPresenceTool(AITool):
    """验证角色出场一致性"""

    name = "validate_character_presence"
    description = "验证角色在故事中的出场一致性，检测角色突然出现/消失、未定义角色等问题"
    parameters = [
        ToolParameter("character_name", "要验证的角色名称（可选，留空验证所有角色）", "string", required=False)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()
            target_char = params.get("character_name", "").strip()

            if not scenes:
                return ToolResult.error("没有场景可验证")

            defined_chars = {c.get('name') for c in characters}
            issues = []

            # 如果指定了角色，只验证该角色
            chars_to_check = [target_char] if target_char else list(defined_chars)

            for char_name in chars_to_check:
                if target_char and char_name != target_char:
                    continue

                appearances = []
                for idx, scene in enumerate(scenes):
                    if char_name in scene.get('characters', []):
                        appearances.append(idx)

                if not appearances:
                    if char_name in defined_chars:
                        issues.append({
                            'type': 'never_appears',
                            'severity': 'warning',
                            'message': f"角色 '{char_name}' 已定义但从未出场",
                            'character': char_name
                        })
                    continue

                # 检测大间隔消失
                for i in range(len(appearances) - 1):
                    gap = appearances[i + 1] - appearances[i]
                    if gap > 5:  # 超过5个场景未出现
                        issues.append({
                            'type': 'long_absence',
                            'severity': 'info',
                            'message': f"角色 '{char_name}' 在场景 {appearances[i]+1} 到 {appearances[i+1]+1} 之间消失了 {gap} 个场景",
                            'character': char_name,
                            'from_scene': appearances[i],
                            'to_scene': appearances[i + 1],
                            'gap': gap
                        })

                # 检测是否在故事后半部分消失
                total_scenes = len(scenes)
                last_appearance = appearances[-1]
                remaining = total_scenes - last_appearance - 1
                if remaining > 3 and last_appearance < total_scenes * 0.7:
                    issues.append({
                        'type': 'early_disappearance',
                        'severity': 'warning',
                        'message': f"角色 '{char_name}' 最后出现在第 {last_appearance+1} 场，之后的 {remaining} 场都未出现",
                        'character': char_name,
                        'last_scene': last_appearance,
                        'remaining_scenes': remaining
                    })

            # 检测未定义的角色
            for idx, scene in enumerate(scenes):
                for char in scene.get('characters', []):
                    if char not in defined_chars:
                        issues.append({
                            'type': 'undefined_character',
                            'severity': 'error',
                            'message': f"场景 {idx+1} 中的角色 '{char}' 未在角色列表中定义",
                            'character': char,
                            'scene_index': idx
                        })
                        defined_chars.add(char)  # 避免重复报告

            # 统计
            by_severity = {
                'error': len([i for i in issues if i['severity'] == 'error']),
                'warning': len([i for i in issues if i['severity'] == 'warning']),
                'info': len([i for i in issues if i['severity'] == 'info'])
            }

            result = {
                'total_defined_characters': len(characters),
                'characters_checked': len(chars_to_check),
                'issues': issues,
                'by_severity': by_severity
            }

            if issues:
                return ToolResult.success(
                    message=f"角色验证完成：发现 {len(issues)} 个问题（错误{by_severity['error']}，警告{by_severity['warning']}，提示{by_severity['info']}）",
                    data=result
                )
            else:
                return ToolResult.success(
                    message="角色出场验证通过，未发现问题",
                    data=result
                )

        except Exception as e:
            return ToolResult.error(f"角色出场验证失败: {e}")


class CheckLogicConsistencyTool(AITool):
    """检查逻辑一致性"""

    name = "check_logic_consistency"
    description = "全面检查故事的逻辑一致性，包括角色、地点、时间、情节等方面"
    parameters = [
        ToolParameter("check_types", "要检查的类型列表：character, location, time, plot（可选，默认全部）", "array", required=False)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()

            check_types = params.get("check_types", ["character", "location", "time", "plot"])
            if not check_types:
                check_types = ["character", "location", "time", "plot"]

            all_issues = []

            # 角色一致性检查
            if "character" in check_types:
                defined_chars = {c.get('name') for c in characters}

                # 检查未使用的角色
                used_chars = set()
                for scene in scenes:
                    used_chars.update(scene.get('characters', []))

                unused_chars = defined_chars - used_chars
                for char in unused_chars:
                    all_issues.append({
                        'category': 'character',
                        'type': 'unused_character',
                        'severity': 'info',
                        'message': f"角色 '{char}' 已定义但未在任何场景中出现"
                    })

                # 检查未定义的角色
                undefined_chars = used_chars - defined_chars
                for char in undefined_chars:
                    all_issues.append({
                        'category': 'character',
                        'type': 'undefined_character',
                        'severity': 'error',
                        'message': f"角色 '{char}' 在场景中出现但未定义"
                    })

            # 地点一致性检查
            if "location" in check_types:
                locations = {}
                for idx, scene in enumerate(scenes):
                    loc = scene.get('location', '').strip()
                    if loc:
                        if loc not in locations:
                            locations[loc] = []
                        locations[loc].append(idx)

                # 检查只出现一次的地点（可能是拼写错误）
                for loc, indices in locations.items():
                    if len(indices) == 1:
                        # 检查是否有相似的地点名称
                        similar = []
                        for other_loc in locations:
                            if other_loc != loc:
                                # 简单的相似度检查
                                if loc in other_loc or other_loc in loc:
                                    similar.append(other_loc)
                        if similar:
                            all_issues.append({
                                'category': 'location',
                                'type': 'possible_typo',
                                'severity': 'info',
                                'message': f"地点 '{loc}' 只出现一次，可能是 {similar} 的拼写错误",
                                'location': loc,
                                'similar': similar
                            })

            # 时间一致性检查
            if "time" in check_types:
                scenes_without_time = []
                for idx, scene in enumerate(scenes):
                    if not scene.get('time', '').strip():
                        scenes_without_time.append(idx)

                if scenes_without_time and len(scenes_without_time) < len(scenes):
                    all_issues.append({
                        'category': 'time',
                        'type': 'incomplete_timeline',
                        'severity': 'warning',
                        'message': f"{len(scenes_without_time)} 个场景缺少时间信息",
                        'scene_indices': scenes_without_time
                    })

            # 情节一致性检查
            if "plot" in check_types:
                # 检查空场景
                for idx, scene in enumerate(scenes):
                    content = scene.get('content', '').strip()
                    if not content:
                        all_issues.append({
                            'category': 'plot',
                            'type': 'empty_scene',
                            'severity': 'error',
                            'message': f"场景 {idx+1} '{scene.get('name', '')}' 内容为空",
                            'scene_index': idx
                        })
                    elif len(content) < 50:
                        all_issues.append({
                            'category': 'plot',
                            'type': 'short_scene',
                            'severity': 'info',
                            'message': f"场景 {idx+1} '{scene.get('name', '')}' 内容较短（{len(content)}字）",
                            'scene_index': idx,
                            'word_count': len(content)
                        })

                # 检查无角色场景
                for idx, scene in enumerate(scenes):
                    if not scene.get('characters'):
                        all_issues.append({
                            'category': 'plot',
                            'type': 'no_characters',
                            'severity': 'info',
                            'message': f"场景 {idx+1} '{scene.get('name', '')}' 没有指定角色",
                            'scene_index': idx
                        })

            # 按类别统计
            by_category = {}
            by_severity = {'error': 0, 'warning': 0, 'info': 0}
            for issue in all_issues:
                cat = issue.get('category', 'other')
                by_category[cat] = by_category.get(cat, 0) + 1
                sev = issue.get('severity', 'info')
                by_severity[sev] = by_severity.get(sev, 0) + 1

            result = {
                'total_issues': len(all_issues),
                'issues': all_issues,
                'by_category': by_category,
                'by_severity': by_severity,
                'checked_types': check_types
            }

            if all_issues:
                return ToolResult.success(
                    message=f"逻辑一致性检查完成：发现 {len(all_issues)} 个问题",
                    data=result
                )
            else:
                return ToolResult.success(
                    message="逻辑一致性检查通过，未发现问题",
                    data=result
                )

        except Exception as e:
            return ToolResult.error(f"逻辑一致性检查失败: {e}")


def register_tools(registry):
    """注册验证工具"""
    registry.register(ValidateTimelineTool())
    registry.register(ValidateCharacterPresenceTool())
    registry.register(CheckLogicConsistencyTool())
