"""
事件总线系统 - 提供基于主题的事件发布/订阅机制

用法:
    from writer_app.core.event_bus import EventBus, get_event_bus

    # 获取单例
    bus = get_event_bus()

    # 订阅事件
    def on_scene_changed(event_type, **kwargs):
        scene_id = kwargs.get('scene_id')
        print(f"场景 {scene_id} 已更新")

    bus.subscribe("scene_updated", on_scene_changed)

    # 发布事件
    bus.publish("scene_updated", scene_id=1)

    # 取消订阅
    bus.unsubscribe("scene_updated", on_scene_changed)
"""

from typing import Callable, Dict, List, Set, Any, Optional
from collections import defaultdict
import threading
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """
    单例事件总线，支持主题订阅和通配符匹配。

    事件类型约定:
        - "scene_added", "scene_updated", "scene_deleted" - 场景相关
        - "character_added", "character_updated", "character_deleted" - 角色相关
        - "outline_updated", "outline_changed" - 大纲相关
        - "wiki_updated", "wiki_entry_updated" - 百科相关
        - "relationships_updated", "relationship_added" - 关系图相关
        - "timeline_updated", "timeline_event_updated" - 时间轴相关
        - "kanban_updated", "kanban_task_updated" - 看板相关
        - "evidence_updated", "clue_added" - 证据板/线索相关
        - "factions_updated" - 阵营相关
        - "ideas_updated" - 灵感相关
        - "asset_updated" - 素材相关
        - "project_loaded", "project_saved" - 项目生命周期
        - "galgame_assets_updated" - Galgame资源相关
        - "all" - 通配符，接收所有事件
    """

    _instance: Optional['EventBus'] = None
    _lock = threading.Lock()

    # 预定义的事件类型
    EVENT_TYPES: Set[str] = {
        # 场景
        "scene_added", "scene_updated", "scene_deleted", "scene_moved",
        "scene_jump_requested",  # 请求跳转到场景
        # 角色
        "character_added", "character_updated", "character_deleted",
        # 大纲
        "outline_updated", "outline_changed", "outline_node_added", "outline_node_deleted", "outline_node_moved",
        "outline_node_selected",  # 大纲节点被选中
        # 百科
        "wiki_updated", "wiki_entry_added", "wiki_entry_updated", "wiki_entry_deleted",
        # 关系
        "relationships_updated", "relationship_added", "relationship_updated", "relationship_link_added", "relationship_link_deleted",
        # 时间轴
        "timeline_updated", "timeline_event_added", "timeline_event_updated", "timeline_event_deleted",
        # 看板
        "kanban_updated", "kanban_task_added", "kanban_task_updated", "kanban_task_moved",
        # 证据板 / 线索
        "evidence_updated", "evidence_node_added", "evidence_node_deleted", "evidence_link_added",
        "clue_added", "clue_updated", "clue_deleted",
        # 素材
        "asset_added", "asset_updated", "asset_deleted",
        "asset_insert_requested",  # 请求插入资产到编辑器
        # 阵营
        "factions_updated", "faction_added", "faction_relation_changed",
        # 灵感
        "ideas_updated", "idea_added", "idea_deleted",
        # Galgame资源
        "galgame_assets_updated", "galgame_asset_added", "galgame_asset_deleted",
        # 项目生命周期
        "project_loaded", "project_saved", "project_new", "project_config_changed",
        # 标签
        "tags_updated",
        # 样式
        "style_updated",
        # 编辑器
        "editor_content_changed",  # 编辑器内容变化
        "editor_selection_changed",  # 编辑器选择变化
        # 视图切换
        "view_changed",  # 视图切换
        "tab_changed",  # 标签页切换
        # 验证事件
        "validation_issues_found", "validation_passed",
        # 缓存事件
        "cache_invalidated",
        # 布局事件
        "character_layout_updated", "evidence_layout_updated",
        # 研究事件
        "research_added", "research_updated", "research_deleted",
        # 素材引用事件
        "asset_reference_added", "asset_reference_removed",
        # 专注模式事件
        "focus_mode_changed", "focus_level_changed", "typewriter_mode_changed",
        "zen_mode_entered", "zen_mode_exited",
        "focus_session_started", "focus_session_ended", "focus_stats_updated",
        # AI模式
        "ai_mode_changed",
        # 训练事件
        "training_completed",
        # UI 控制事件
        "open_module_catalog",
        # 通配符
        "all"
    }

    def __new__(cls) -> 'EventBus':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._subscriber_lock = threading.RLock()
        self._enabled = True
        self._batch_mode = False
        self._batch_events: List[tuple] = []
        self._initialized = True

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        订阅事件。

        Args:
            event_type: 事件类型，可以是具体类型或 "all" 通配符
            handler: 回调函数，签名为 handler(event_type: str, **kwargs)
        """
        if event_type not in self.EVENT_TYPES:
            logger.warning(f"未知事件类型: {event_type}，仍然允许订阅")

        with self._subscriber_lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(f"订阅事件: {event_type} -> {handler.__name__ if hasattr(handler, '__name__') else handler}")

    def subscribe_multiple(self, event_types: List[str], handler: Callable) -> None:
        """
        订阅多个事件类型。

        Args:
            event_types: 事件类型列表
            handler: 回调函数
        """
        for event_type in event_types:
            self.subscribe(event_type, handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """
        取消订阅事件。

        Args:
            event_type: 事件类型
            handler: 要移除的回调函数

        Returns:
            是否成功移除
        """
        with self._subscriber_lock:
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"取消订阅: {event_type} -> {handler.__name__ if hasattr(handler, '__name__') else handler}")
                return True
        return False

    def unsubscribe_all(self, handler: Callable) -> int:
        """
        从所有事件类型取消订阅指定处理器。

        Args:
            handler: 要移除的回调函数

        Returns:
            移除的订阅数量
        """
        count = 0
        with self._subscriber_lock:
            for event_type in list(self._subscribers.keys()):
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)
                    count += 1
        logger.debug(f"移除订阅: {count} 个事件类型")
        return count

    def publish(self, event_type: str, **kwargs) -> None:
        """
        发布事件。

        Args:
            event_type: 事件类型
            **kwargs: 传递给处理器的参数
        """
        if not self._enabled:
            return

        if self._batch_mode:
            self._batch_events.append((event_type, kwargs))
            return

        self._dispatch(event_type, **kwargs)

    def publish_all(self, event_types: List[str], **kwargs) -> None:
        """
        向多个事件类型发布相同的数据。

        Args:
            event_types: 事件类型列表
            **kwargs: 传递给处理器的参数
        """
        for event_type in event_types:
            self.publish(event_type, **kwargs)

    def _dispatch(self, event_type: str, **kwargs) -> None:
        """内部分发事件到订阅者。"""
        handlers_to_call = []

        with self._subscriber_lock:
            # 收集特定事件类型的处理器
            handlers_to_call.extend(self._subscribers.get(event_type, []))
            # 收集通配符处理器
            if event_type != "all":
                handlers_to_call.extend(self._subscribers.get("all", []))

        # 在锁外调用处理器，避免死锁
        for handler in handlers_to_call:
            try:
                handler(event_type, **kwargs)
            except Exception as e:
                logger.error(f"事件处理器错误 [{event_type}]: {e}", exc_info=True)

    def begin_batch(self) -> None:
        """开始批量事件模式，事件将被暂存直到 end_batch() 调用。"""
        self._batch_mode = True
        self._batch_events = []

    def end_batch(self) -> None:
        """
        结束批量模式并分发所有暂存的事件。
        对于相同类型的事件，只分发最后一个。
        """
        self._batch_mode = False

        # 去重：保留每种事件类型的最后一个
        final_events: Dict[str, dict] = {}
        for event_type, kwargs in self._batch_events:
            final_events[event_type] = kwargs

        self._batch_events = []

        # 分发去重后的事件
        for event_type, kwargs in final_events.items():
            self._dispatch(event_type, **kwargs)

    def cancel_batch(self) -> None:
        """取消批量模式，丢弃所有暂存的事件。"""
        self._batch_mode = False
        self._batch_events = []

    def enable(self) -> None:
        """启用事件分发。"""
        self._enabled = True

    def disable(self) -> None:
        """禁用事件分发（静默丢弃所有事件）。"""
        self._enabled = False

    def is_enabled(self) -> bool:
        """检查事件分发是否启用。"""
        return self._enabled

    def get_subscribers_count(self, event_type: str = None) -> int:
        """
        获取订阅者数量。

        Args:
            event_type: 指定事件类型，None 表示所有

        Returns:
            订阅者数量
        """
        with self._subscriber_lock:
            if event_type:
                return len(self._subscribers.get(event_type, []))
            return sum(len(handlers) for handlers in self._subscribers.values())

    def clear_all(self) -> None:
        """清除所有订阅（用于测试或重置）。"""
        with self._subscriber_lock:
            self._subscribers.clear()
        logger.info("已清除所有事件订阅")


# 全局单例访问函数
_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线单例。"""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance


# 便捷函数
def subscribe(event_type: str, handler: Callable) -> None:
    """便捷订阅函数。"""
    get_event_bus().subscribe(event_type, handler)


def unsubscribe(event_type: str, handler: Callable) -> bool:
    """便捷取消订阅函数。"""
    return get_event_bus().unsubscribe(event_type, handler)


def publish(event_type: str, **kwargs) -> None:
    """便捷发布函数。"""
    get_event_bus().publish(event_type, **kwargs)


# 事件类型常量（便于IDE自动补全）
class Events:
    """事件类型常量。"""
    # 场景
    SCENE_ADDED = "scene_added"
    SCENE_UPDATED = "scene_updated"
    SCENE_DELETED = "scene_deleted"
    SCENE_MOVED = "scene_moved"
    SCENE_JUMP_REQUESTED = "scene_jump_requested"

    # 角色
    CHARACTER_ADDED = "character_added"
    CHARACTER_UPDATED = "character_updated"
    CHARACTER_DELETED = "character_deleted"

    # 大纲
    OUTLINE_UPDATED = "outline_updated"
    OUTLINE_CHANGED = "outline_changed"
    OUTLINE_NODE_ADDED = "outline_node_added"
    OUTLINE_NODE_DELETED = "outline_node_deleted"
    OUTLINE_NODE_MOVED = "outline_node_moved"
    OUTLINE_NODE_SELECTED = "outline_node_selected"

    # 百科
    WIKI_UPDATED = "wiki_updated"
    WIKI_ENTRY_ADDED = "wiki_entry_added"
    WIKI_ENTRY_UPDATED = "wiki_entry_updated"
    WIKI_ENTRY_DELETED = "wiki_entry_deleted"

    # 关系
    RELATIONSHIPS_UPDATED = "relationships_updated"
    RELATIONSHIP_ADDED = "relationship_added"
    RELATIONSHIP_UPDATED = "relationship_updated"
    RELATIONSHIP_LINK_ADDED = "relationship_link_added"
    RELATIONSHIP_LINK_DELETED = "relationship_link_deleted"

    # 时间轴
    TIMELINE_UPDATED = "timeline_updated"
    TIMELINE_EVENT_ADDED = "timeline_event_added"
    TIMELINE_EVENT_UPDATED = "timeline_event_updated"
    TIMELINE_EVENT_DELETED = "timeline_event_deleted"

    # 看板
    KANBAN_UPDATED = "kanban_updated"
    KANBAN_TASK_ADDED = "kanban_task_added"
    KANBAN_TASK_UPDATED = "kanban_task_updated"
    KANBAN_TASK_MOVED = "kanban_task_moved"

    # 证据板
    EVIDENCE_UPDATED = "evidence_updated"
    EVIDENCE_NODE_ADDED = "evidence_node_added"
    EVIDENCE_NODE_DELETED = "evidence_node_deleted"
    EVIDENCE_LINK_ADDED = "evidence_link_added"
    CLUE_ADDED = "clue_added"
    CLUE_UPDATED = "clue_updated"
    CLUE_DELETED = "clue_deleted"

    # 素材
    ASSET_ADDED = "asset_added"
    ASSET_UPDATED = "asset_updated"
    ASSET_DELETED = "asset_deleted"
    ASSET_INSERT_REQUESTED = "asset_insert_requested"

    # 阵营
    FACTIONS_UPDATED = "factions_updated"
    FACTION_ADDED = "faction_added"
    FACTION_RELATION_CHANGED = "faction_relation_changed"

    # 灵感
    IDEAS_UPDATED = "ideas_updated"
    IDEA_ADDED = "idea_added"
    IDEA_DELETED = "idea_deleted"

    # Galgame资源
    GALGAME_ASSETS_UPDATED = "galgame_assets_updated"
    GALGAME_ASSET_ADDED = "galgame_asset_added"
    GALGAME_ASSET_DELETED = "galgame_asset_deleted"

    # 项目生命周期
    PROJECT_LOADED = "project_loaded"
    PROJECT_SAVED = "project_saved"
    PROJECT_NEW = "project_new"
    PROJECT_TYPE_CHANGED = "project_type_changed"
    PROJECT_CONFIG_CHANGED = "project_config_changed"

    # 标签
    TAGS_UPDATED = "tags_updated"

    # 样式
    STYLE_UPDATED = "style_updated"

    # 编辑器
    EDITOR_CONTENT_CHANGED = "editor_content_changed"
    EDITOR_SELECTION_CHANGED = "editor_selection_changed"

    # 视图切换
    VIEW_CHANGED = "view_changed"
    TAB_CHANGED = "tab_changed"

    # 验证事件
    VALIDATION_ISSUES_FOUND = "validation_issues_found"
    VALIDATION_PASSED = "validation_passed"

    # 缓存事件
    CACHE_INVALIDATED = "cache_invalidated"

    # 布局事件
    CHARACTER_LAYOUT_UPDATED = "character_layout_updated"
    EVIDENCE_LAYOUT_UPDATED = "evidence_layout_updated"

    # 研究事件
    RESEARCH_ADDED = "research_added"
    RESEARCH_UPDATED = "research_updated"
    RESEARCH_DELETED = "research_deleted"

    # 素材引用事件
    ASSET_REFERENCE_ADDED = "asset_reference_added"
    ASSET_REFERENCE_REMOVED = "asset_reference_removed"

    # 专注模式事件
    FOCUS_MODE_CHANGED = "focus_mode_changed"
    FOCUS_LEVEL_CHANGED = "focus_level_changed"
    TYPEWRITER_MODE_CHANGED = "typewriter_mode_changed"
    ZEN_MODE_ENTERED = "zen_mode_entered"
    ZEN_MODE_EXITED = "zen_mode_exited"
    FOCUS_SESSION_STARTED = "focus_session_started"
    FOCUS_SESSION_ENDED = "focus_session_ended"
    FOCUS_STATS_UPDATED = "focus_stats_updated"

    # AI模式事件
    AI_MODE_CHANGED = "ai_mode_changed"

    # 训练事件
    TRAINING_COMPLETED = "training_completed"

    # UI 控制事件
    OPEN_MODULE_CATALOG = "open_module_catalog"

    # 通配符
    ALL = "all"
