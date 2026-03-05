"""
查询类 AI 工具 - 提供全文搜索、相关场景查找、项目摘要等功能

用法:
    这些工具通过 AIToolRegistry 自动注册，可被 AI 调用
"""

from typing import Dict, List, Any
from writer_app.core.ai_tools import AITool, ToolParameter, ToolResult


class SearchContentTool(AITool):
    """全文搜索"""

    name = "search_content"
    description = "在项目中搜索指定内容，支持在场景、角色、百科中搜索"
    parameters = [
        ToolParameter("query", "搜索关键词", "string", required=True),
        ToolParameter("search_in", "搜索范围：scenes, characters, wiki, all（默认all）", "string", required=False),
        ToolParameter("case_sensitive", "是否区分大小写（默认否）", "boolean", required=False)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            query = params.get("query", "").strip()
            if not query:
                return ToolResult.error("请提供搜索关键词")

            search_in = params.get("search_in", "all")
            case_sensitive = params.get("case_sensitive", False)

            if not case_sensitive:
                query_lower = query.lower()
            else:
                query_lower = query

            results = []

            # 搜索场景
            if search_in in ["scenes", "all"]:
                for idx, scene in enumerate(project_manager.get_scenes()):
                    content = scene.get('content', '')
                    name = scene.get('name', '')
                    search_text = content + ' ' + name

                    if not case_sensitive:
                        search_text = search_text.lower()

                    if query_lower in search_text:
                        # 提取上下文
                        context = self._extract_context(content, query, case_sensitive)
                        results.append({
                            'type': 'scene',
                            'index': idx,
                            'name': name,
                            'location': scene.get('location', ''),
                            'context': context,
                            'match_in': 'content' if query_lower in (content.lower() if not case_sensitive else content) else 'name'
                        })

            # 搜索角色
            if search_in in ["characters", "all"]:
                for idx, char in enumerate(project_manager.get_characters()):
                    name = char.get('name', '')
                    description = char.get('description', '')
                    search_text = name + ' ' + description

                    if not case_sensitive:
                        search_text = search_text.lower()

                    if query_lower in search_text:
                        context = self._extract_context(description, query, case_sensitive)
                        results.append({
                            'type': 'character',
                            'index': idx,
                            'name': name,
                            'context': context,
                            'match_in': 'name' if query_lower in (name.lower() if not case_sensitive else name) else 'description'
                        })

            # 搜索百科
            if search_in in ["wiki", "all"]:
                for idx, entry in enumerate(project_manager.get_world_entries()):
                    name = entry.get('name', '')
                    content = entry.get('content', '')
                    search_text = name + ' ' + content

                    if not case_sensitive:
                        search_text = search_text.lower()

                    if query_lower in search_text:
                        context = self._extract_context(content, query, case_sensitive)
                        results.append({
                            'type': 'wiki',
                            'index': idx,
                            'name': name,
                            'category': entry.get('category', ''),
                            'context': context,
                            'match_in': 'name' if query_lower in (name.lower() if not case_sensitive else name) else 'content'
                        })

            # 按类型统计
            by_type = {}
            for r in results:
                t = r['type']
                by_type[t] = by_type.get(t, 0) + 1

            result = {
                'query': query,
                'total_matches': len(results),
                'results': results,
                'by_type': by_type
            }

            return ToolResult.success(
                message=f"搜索完成：找到 {len(results)} 个匹配项",
                data=result
            )

        except Exception as e:
            return ToolResult.error(f"搜索失败: {e}")

    def _extract_context(self, text: str, query: str, case_sensitive: bool, context_len: int = 50) -> str:
        """提取搜索结果的上下文"""
        if not text:
            return ""

        search_text = text if case_sensitive else text.lower()
        search_query = query if case_sensitive else query.lower()

        pos = search_text.find(search_query)
        if pos == -1:
            return text[:context_len * 2] + '...' if len(text) > context_len * 2 else text

        start = max(0, pos - context_len)
        end = min(len(text), pos + len(query) + context_len)

        prefix = '...' if start > 0 else ''
        suffix = '...' if end < len(text) else ''

        return prefix + text[start:end] + suffix


class FindRelatedScenesTool(AITool):
    """查找相关场景"""

    name = "find_related_scenes"
    description = "根据角色、地点、标签等条件查找相关场景"
    parameters = [
        ToolParameter("character", "角色名称（可选）", "string", required=False),
        ToolParameter("location", "地点（可选）", "string", required=False),
        ToolParameter("tags", "标签列表（可选）", "array", required=False),
        ToolParameter("time_contains", "时间包含的关键词（可选）", "string", required=False)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            character = params.get("character", "").strip()
            location = params.get("location", "").strip()
            tags = params.get("tags", [])
            time_contains = params.get("time_contains", "").strip()

            if not any([character, location, tags, time_contains]):
                return ToolResult.error("请至少提供一个搜索条件")

            scenes = project_manager.get_scenes()
            matching_scenes = []

            for idx, scene in enumerate(scenes):
                match_reasons = []

                # 检查角色
                if character:
                    if character in scene.get('characters', []):
                        match_reasons.append(f"角色: {character}")

                # 检查地点
                if location:
                    scene_location = scene.get('location', '')
                    if location.lower() in scene_location.lower():
                        match_reasons.append(f"地点: {scene_location}")

                # 检查标签
                if tags:
                    scene_tags = set(scene.get('tags', []))
                    matched_tags = scene_tags.intersection(set(tags))
                    if matched_tags:
                        match_reasons.append(f"标签: {', '.join(matched_tags)}")

                # 检查时间
                if time_contains:
                    scene_time = scene.get('time', '')
                    if time_contains.lower() in scene_time.lower():
                        match_reasons.append(f"时间: {scene_time}")

                if match_reasons:
                    matching_scenes.append({
                        'index': idx,
                        'name': scene.get('name', f'场景{idx+1}'),
                        'location': scene.get('location', ''),
                        'time': scene.get('time', ''),
                        'characters': scene.get('characters', []),
                        'tags': scene.get('tags', []),
                        'match_reasons': match_reasons,
                        'content_preview': scene.get('content', '')[:100]
                    })

            result = {
                'search_criteria': {
                    'character': character,
                    'location': location,
                    'tags': tags,
                    'time_contains': time_contains
                },
                'total_matches': len(matching_scenes),
                'scenes': matching_scenes
            }

            return ToolResult.success(
                message=f"找到 {len(matching_scenes)} 个相关场景",
                data=result
            )

        except Exception as e:
            return ToolResult.error(f"查找相关场景失败: {e}")


class GetProjectSummaryTool(AITool):
    """获取项目摘要"""

    name = "get_project_summary"
    description = "获取项目的完整摘要信息，包括场景数、角色数、字数统计等"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()
            world_entries = project_manager.get_world_entries()
            outline = project_manager.get_outline()

            # 基础统计
            total_words = 0
            locations = set()
            all_tags = set()
            chars_in_scenes = set()

            for scene in scenes:
                content = scene.get('content', '')
                total_words += len(content)
                if scene.get('location'):
                    locations.add(scene['location'])
                for tag in scene.get('tags', []):
                    all_tags.add(tag)
                for char in scene.get('characters', []):
                    chars_in_scenes.add(char)

            # 大纲统计
            def count_outline_nodes(node):
                if not node:
                    return 0, 0
                count = 1
                max_depth = 0
                for child in node.get('children', []):
                    child_count, child_depth = count_outline_nodes(child)
                    count += child_count
                    max_depth = max(max_depth, child_depth + 1)
                return count, max_depth

            outline_nodes, outline_depth = count_outline_nodes(outline)

            # 角色统计
            char_appearances = {}
            for scene in scenes:
                for char in scene.get('characters', []):
                    char_appearances[char] = char_appearances.get(char, 0) + 1

            # 地点统计
            location_counts = {}
            for scene in scenes:
                loc = scene.get('location', '未指定')
                location_counts[loc] = location_counts.get(loc, 0) + 1

            # 项目元数据
            meta = project_manager.project_data.get('meta', {})

            summary = {
                'project_info': {
                    'type': meta.get('type', '未指定'),
                    'length': meta.get('length', '未指定'),
                    'outline_template': meta.get('outline_template_style', 'default')
                },
                'statistics': {
                    'total_scenes': len(scenes),
                    'total_characters': len(characters),
                    'total_words': total_words,
                    'avg_words_per_scene': total_words // len(scenes) if scenes else 0,
                    'wiki_entries': len(world_entries),
                    'outline_nodes': outline_nodes,
                    'outline_depth': outline_depth,
                    'unique_locations': len(locations),
                    'unique_tags': len(all_tags)
                },
                'characters': {
                    'defined': len(characters),
                    'appearing_in_scenes': len(chars_in_scenes),
                    'appearance_counts': char_appearances,
                    'list': [c.get('name', '') for c in characters]
                },
                'locations': {
                    'unique_count': len(locations),
                    'list': list(locations),
                    'scene_counts': location_counts
                },
                'tags': {
                    'count': len(all_tags),
                    'list': list(all_tags)
                },
                'scenes_overview': [
                    {
                        'index': idx,
                        'name': s.get('name', f'场景{idx+1}'),
                        'word_count': len(s.get('content', '')),
                        'character_count': len(s.get('characters', []))
                    }
                    for idx, s in enumerate(scenes)
                ]
            }

            return ToolResult.success(
                message=f"项目摘要：{len(scenes)}场景，{len(characters)}角色，{total_words}字",
                data=summary
            )

        except Exception as e:
            return ToolResult.error(f"获取项目摘要失败: {e}")


class GetCharacterDetailsTool(AITool):
    """获取角色详细信息"""

    name = "get_character_details"
    description = "获取指定角色的详细信息，包括描述、出场场景、关联角色等"
    parameters = [
        ToolParameter("character_name", "角色名称", "string", required=True)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            char_name = params.get("character_name", "").strip()
            if not char_name:
                return ToolResult.error("请指定角色名称")

            characters = project_manager.get_characters()
            scenes = project_manager.get_scenes()

            # 查找角色
            character = None
            for c in characters:
                if c.get('name') == char_name:
                    character = c
                    break

            if not character:
                return ToolResult.error(f"未找到角色: {char_name}")

            # 收集出场信息
            appearances = []
            co_characters = {}

            for idx, scene in enumerate(scenes):
                scene_chars = scene.get('characters', [])
                if char_name in scene_chars:
                    appearances.append({
                        'scene_index': idx,
                        'scene_name': scene.get('name', f'场景{idx+1}'),
                        'location': scene.get('location', ''),
                        'time': scene.get('time', ''),
                        'other_characters': [c for c in scene_chars if c != char_name]
                    })

                    # 统计共同出场角色
                    for co_char in scene_chars:
                        if co_char != char_name:
                            co_characters[co_char] = co_characters.get(co_char, 0) + 1

            # 排序共同出场角色
            sorted_co_chars = sorted(co_characters.items(), key=lambda x: x[1], reverse=True)

            details = {
                'name': char_name,
                'description': character.get('description', ''),
                'tags': character.get('tags', []),
                'events': character.get('events', []),
                'statistics': {
                    'total_appearances': len(appearances),
                    'first_appearance': appearances[0]['scene_name'] if appearances else None,
                    'last_appearance': appearances[-1]['scene_name'] if appearances else None
                },
                'appearances': appearances,
                'co_characters': [
                    {'name': name, 'shared_scenes': count}
                    for name, count in sorted_co_chars
                ],
                'locations_visited': list(set(a['location'] for a in appearances if a['location']))
            }

            return ToolResult.success(
                message=f"角色 {char_name} 共出场 {len(appearances)} 次",
                data=details
            )

        except Exception as e:
            return ToolResult.error(f"获取角色详情失败: {e}")


class GetSceneDetailsTool(AITool):
    """获取场景详细信息"""

    name = "get_scene_details"
    description = "获取指定场景的详细信息"
    parameters = [
        ToolParameter("scene_index", "场景索引（从0开始）", "integer", required=True)
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scene_index = params.get("scene_index")
            if scene_index is None:
                return ToolResult.error("请指定场景索引")

            scenes = project_manager.get_scenes()

            if not isinstance(scene_index, int) or scene_index < 0 or scene_index >= len(scenes):
                return ToolResult.error(f"无效的场景索引: {scene_index}（有效范围: 0-{len(scenes)-1}）")

            scene = scenes[scene_index]
            content = scene.get('content', '')

            # 分析场景内容
            details = {
                'index': scene_index,
                'name': scene.get('name', f'场景{scene_index+1}'),
                'location': scene.get('location', ''),
                'time': scene.get('time', ''),
                'characters': scene.get('characters', []),
                'tags': scene.get('tags', []),
                'outline_ref_id': scene.get('outline_ref_id', ''),
                'content': content,
                'statistics': {
                    'word_count': len(content),
                    'character_count': len(scene.get('characters', [])),
                    'has_dialogue': '"' in content or '「' in content or '"' in content,
                    'paragraph_count': len([p for p in content.split('\n') if p.strip()])
                },
                'navigation': {
                    'previous': scene_index - 1 if scene_index > 0 else None,
                    'next': scene_index + 1 if scene_index < len(scenes) - 1 else None,
                    'total_scenes': len(scenes)
                }
            }

            return ToolResult.success(
                message=f"场景 {scene_index+1}: {scene.get('name', '')}",
                data=details
            )

        except Exception as e:
            return ToolResult.error(f"获取场景详情失败: {e}")


def register_tools(registry):
    """注册查询工具"""
    registry.register(SearchContentTool())
    registry.register(FindRelatedScenesTool())
    registry.register(GetProjectSummaryTool())
    registry.register(GetCharacterDetailsTool())
    registry.register(GetSceneDetailsTool())
