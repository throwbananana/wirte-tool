"""
数据访问门面层 - 提供缓存和智能查询功能

用法:
    from writer_app.core.data_facade import DataFacade, get_data_facade

    facade = get_data_facade(project_manager)

    # 使用缓存的查询方法
    scenes = facade.get_scenes_by_character("Alice")
    stats = facade.get_scene_statistics()
"""

from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import logging

from writer_app.core.event_bus import get_event_bus, Events

logger = logging.getLogger(__name__)


def cached(cache_key: str = None, invalidate_on: List[str] = None):
    """
    缓存装饰器，支持事件驱动的失效。

    Args:
        cache_key: 缓存键前缀，默认使用函数名
        invalidate_on: 使缓存失效的事件类型列表
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self: 'DataFacade', *args, **kwargs):
            # 构建缓存键
            key = cache_key or func.__name__
            full_key = f"{key}:{args}:{tuple(sorted(kwargs.items()))}"

            # 检查缓存
            if full_key in self._cache and self._cache_valid.get(full_key, False):
                logger.debug(f"缓存命中: {key}")
                return self._cache[full_key]

            # 执行函数并缓存结果
            result = func(self, *args, **kwargs)
            self._cache[full_key] = result
            self._cache_valid[full_key] = True

            # 记录失效事件
            if invalidate_on:
                for event_type in invalidate_on:
                    if full_key not in self._invalidation_map.get(event_type, set()):
                        if event_type not in self._invalidation_map:
                            self._invalidation_map[event_type] = set()
                        self._invalidation_map[event_type].add(full_key)

            logger.debug(f"缓存写入: {key}")
            return result
        return wrapper
    return decorator


class DataFacade:
    """
    数据访问门面，提供缓存和智能查询。

    特性:
    - 事件驱动的缓存失效
    - 智能查询方法
    - 统计数据聚合
    """

    _instance: Optional['DataFacade'] = None

    def __init__(self, project_manager):
        self.pm = project_manager
        self._cache: Dict[str, Any] = {}
        self._cache_valid: Dict[str, bool] = {}
        self._invalidation_map: Dict[str, set] = {}  # event_type -> set of cache keys
        self._setup_invalidation()

    def _setup_invalidation(self):
        """订阅事件以使缓存失效"""
        bus = get_event_bus()

        # 场景相关事件
        scene_events = [
            Events.SCENE_ADDED, Events.SCENE_UPDATED,
            Events.SCENE_DELETED, Events.SCENE_MOVED
        ]
        for event in scene_events:
            bus.subscribe(event, lambda et, **kw: self._invalidate_group('scenes'))

        # 角色相关事件
        char_events = [
            Events.CHARACTER_ADDED, Events.CHARACTER_UPDATED,
            Events.CHARACTER_DELETED
        ]
        for event in char_events:
            bus.subscribe(event, lambda et, **kw: self._invalidate_group('characters'))

        # 大纲相关事件
        outline_events = [
            Events.OUTLINE_NODE_ADDED, Events.OUTLINE_NODE_DELETED,
            Events.OUTLINE_NODE_MOVED, Events.OUTLINE_CHANGED
        ]
        for event in outline_events:
            bus.subscribe(event, lambda et, **kw: self._invalidate_group('outline'))

        # 项目加载时清除所有缓存
        bus.subscribe(Events.PROJECT_LOADED, lambda et, **kw: self.clear_all())
        bus.subscribe(Events.PROJECT_NEW, lambda et, **kw: self.clear_all())

    def _invalidate_group(self, group: str):
        """使指定组的所有缓存失效"""
        keys_to_invalidate = []
        for key in self._cache_valid:
            if group in key or key.startswith(group):
                keys_to_invalidate.append(key)

        for key in keys_to_invalidate:
            self._cache_valid[key] = False

        if keys_to_invalidate:
            logger.debug(f"缓存失效 (组={group}): {len(keys_to_invalidate)} 项")
            get_event_bus().publish(Events.CACHE_INVALIDATED, group=group)

    def _invalidate(self, cache_key: str):
        """使指定缓存键失效"""
        for key in list(self._cache_valid.keys()):
            if key.startswith(cache_key):
                self._cache_valid[key] = False
        logger.debug(f"缓存失效: {cache_key}")

    def clear_all(self):
        """清除所有缓存"""
        self._cache.clear()
        self._cache_valid.clear()
        logger.info("已清除所有数据缓存")

    # ============ 场景相关查询 ============

    @cached(cache_key='scenes_by_character', invalidate_on=[Events.SCENE_UPDATED, Events.SCENE_DELETED])
    def get_scenes_by_character(self, char_name: str) -> List[Dict]:
        """获取指定角色出现的所有场景"""
        result = []
        for idx, scene in enumerate(self.pm.get_scenes()):
            characters = scene.get('characters', [])
            if char_name in characters:
                result.append({'index': idx, 'scene': scene})
        return result

    @cached(cache_key='scenes_by_time_order')
    def get_scenes_by_time_order(self) -> List[Dict]:
        """获取按时间排序的场景列表"""
        scenes = list(enumerate(self.pm.get_scenes()))

        def get_time_key(item):
            idx, scene = item
            time_str = scene.get('time', '') or ''
            # 尝试提取时间信息进行排序
            return (time_str, idx)

        sorted_scenes = sorted(scenes, key=get_time_key)
        return [{'index': idx, 'scene': scene} for idx, scene in sorted_scenes]

    @cached(cache_key='scenes_by_location')
    def get_scenes_by_location(self, location: str) -> List[Dict]:
        """获取指定地点的所有场景"""
        result = []
        for idx, scene in enumerate(self.pm.get_scenes()):
            if scene.get('location', '') == location:
                result.append({'index': idx, 'scene': scene})
        return result

    # ============ 角色相关查询 ============

    @cached(cache_key='character_timeline')
    def get_character_timeline(self, char_name: str) -> List[Dict]:
        """获取角色的时间线（按场景顺序的事件列表）"""
        timeline = []
        for idx, scene in enumerate(self.pm.get_scenes()):
            if char_name in scene.get('characters', []):
                timeline.append({
                    'scene_index': idx,
                    'scene_name': scene.get('name', ''),
                    'time': scene.get('time', ''),
                    'location': scene.get('location', ''),
                    'content_preview': scene.get('content', '')[:100]
                })
        return timeline

    @cached(cache_key='character_appearances')
    def get_character_appearances(self) -> Dict[str, int]:
        """获取所有角色的出场次数统计"""
        appearances = {}
        for scene in self.pm.get_scenes():
            for char_name in scene.get('characters', []):
                appearances[char_name] = appearances.get(char_name, 0) + 1
        return appearances

    @cached(cache_key='character_pairs')
    def get_character_pair_scenes(self, char_a: str, char_b: str) -> List[Dict]:
        """获取两个角色同时出现的场景"""
        result = []
        for idx, scene in enumerate(self.pm.get_scenes()):
            characters = scene.get('characters', [])
            if char_a in characters and char_b in characters:
                result.append({'index': idx, 'scene': scene})
        return result

    # ============ 统计相关查询 ============

    @cached(cache_key='scene_statistics')
    def get_scene_statistics(self) -> Dict:
        """获取场景统计信息"""
        scenes = self.pm.get_scenes()
        total_words = 0
        locations = set()
        characters_set = set()

        for scene in scenes:
            content = scene.get('content', '')
            total_words += len(content)
            if scene.get('location'):
                locations.add(scene['location'])
            for char in scene.get('characters', []):
                characters_set.add(char)

        return {
            'total_scenes': len(scenes),
            'total_words': total_words,
            'avg_words_per_scene': total_words / len(scenes) if scenes else 0,
            'unique_locations': len(locations),
            'unique_characters': len(characters_set),
            'locations': list(locations),
            'characters': list(characters_set)
        }

    @cached(cache_key='outline_depth_stats')
    def get_outline_depth_stats(self) -> Dict:
        """获取大纲深度统计"""
        outline = self.pm.get_outline()
        if not outline:
            return {'max_depth': 0, 'total_nodes': 0, 'nodes_by_depth': {}}

        nodes_by_depth = {}
        max_depth = 0
        total_nodes = 0

        def traverse(node, depth):
            nonlocal max_depth, total_nodes
            if not node:
                return
            max_depth = max(max_depth, depth)
            total_nodes += 1
            nodes_by_depth[depth] = nodes_by_depth.get(depth, 0) + 1
            for child in node.get('children', []):
                traverse(child, depth + 1)

        traverse(outline, 0)

        return {
            'max_depth': max_depth,
            'total_nodes': total_nodes,
            'nodes_by_depth': nodes_by_depth
        }

    @cached(cache_key='project_summary')
    def get_project_summary(self) -> Dict:
        """获取项目摘要"""
        scenes = self.pm.get_scenes()
        characters = self.pm.get_characters()
        world_entries = self.pm.get_world_entries()
        outline = self.pm.get_outline()

        # 计算大纲节点数
        def count_nodes(node):
            if not node:
                return 0
            return 1 + sum(count_nodes(c) for c in node.get('children', []))

        return {
            'scene_count': len(scenes),
            'character_count': len(characters),
            'wiki_entry_count': len(world_entries),
            'outline_node_count': count_nodes(outline),
            'total_word_count': sum(len(s.get('content', '')) for s in scenes),
            'project_type': self.pm.get_project_type(),
            'project_length': self.pm.get_project_length()
        }

    # ============ 搜索相关查询 ============

    def search_content(self, query: str, case_sensitive: bool = False) -> List[Dict]:
        """全文搜索（不缓存，因为查询可能变化）"""
        if not case_sensitive:
            query = query.lower()

        results = []

        # 搜索场景
        for idx, scene in enumerate(self.pm.get_scenes()):
            content = scene.get('content', '')
            name = scene.get('name', '')
            search_text = content + ' ' + name
            if not case_sensitive:
                search_text = search_text.lower()

            if query in search_text:
                results.append({
                    'type': 'scene',
                    'index': idx,
                    'name': name,
                    'context': self._extract_context(content, query, case_sensitive)
                })

        # 搜索角色
        for idx, char in enumerate(self.pm.get_characters()):
            desc = char.get('description', '')
            name = char.get('name', '')
            search_text = desc + ' ' + name
            if not case_sensitive:
                search_text = search_text.lower()

            if query in search_text:
                results.append({
                    'type': 'character',
                    'index': idx,
                    'name': name,
                    'context': self._extract_context(desc, query, case_sensitive)
                })

        # 搜索Wiki
        for idx, entry in enumerate(self.pm.get_world_entries()):
            content = entry.get('content', '')
            name = entry.get('name', '')
            search_text = content + ' ' + name
            if not case_sensitive:
                search_text = search_text.lower()

            if query in search_text:
                results.append({
                    'type': 'wiki',
                    'index': idx,
                    'name': name,
                    'context': self._extract_context(content, query, case_sensitive)
                })

        return results

    def _extract_context(self, text: str, query: str, case_sensitive: bool, context_len: int = 50) -> str:
        """提取搜索结果的上下文"""
        search_text = text if case_sensitive else text.lower()
        search_query = query if case_sensitive else query.lower()

        pos = search_text.find(search_query)
        if pos == -1:
            return text[:context_len * 2] + '...'

        start = max(0, pos - context_len)
        end = min(len(text), pos + len(query) + context_len)

        prefix = '...' if start > 0 else ''
        suffix = '...' if end < len(text) else ''

        return prefix + text[start:end] + suffix


# 全局单例
_facade_instance: Optional[DataFacade] = None


def get_data_facade(project_manager=None) -> DataFacade:
    """
    获取数据门面单例。

    Args:
        project_manager: 首次调用时必须提供

    Returns:
        DataFacade 实例
    """
    global _facade_instance
    if _facade_instance is None:
        if project_manager is None:
            raise ValueError("首次获取 DataFacade 时必须提供 project_manager")
        _facade_instance = DataFacade(project_manager)
    return _facade_instance


def reset_data_facade():
    """重置数据门面单例（用于测试）"""
    global _facade_instance
    if _facade_instance:
        _facade_instance.clear_all()
    _facade_instance = None
