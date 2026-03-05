"""
模块同步服务 - 协调各模块之间的事件传递和数据同步

主要职责:
    - 监听核心数据变更事件
    - 触发相关模块的同步更新
    - 维护跨模块数据一致性（如时间轴-场景关联）
"""

from typing import Optional, Dict, Any, Callable, List
import logging

from writer_app.core.event_bus import get_event_bus, Events

logger = logging.getLogger(__name__)


class ModuleSyncService:
    """
    模块同步服务单例。

    负责协调以下模块之间的同步：
    - 时间轴 (timeline) <-> 场景 (scene)
    - 时间轴 (timeline) <-> 证据板 (evidence)
    - 反推导 (reverse_engineering) <-> 时间轴 (timeline)
    - 逻辑验证器 (logic_validator) <-> 所有模块
    """

    _instance: Optional['ModuleSyncService'] = None

    def __new__(cls) -> 'ModuleSyncService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._project_manager = None
        self._validation_callback: Optional[Callable] = None
        self._sync_handlers: Dict[str, List[Callable]] = {}
        self._enabled = True
        self._initialized = True

    def initialize(self, project_manager) -> None:
        """
        初始化服务并订阅事件。

        Args:
            project_manager: ProjectManager 实例
        """
        self._project_manager = project_manager
        self._subscribe_events()
        logger.info("ModuleSyncService 已初始化")

    def _subscribe_events(self) -> None:
        """订阅需要同步的事件。"""
        bus = get_event_bus()

        # 场景变更 -> 更新时间轴关联
        bus.subscribe(Events.SCENE_ADDED, self._on_scene_added)
        bus.subscribe(Events.SCENE_DELETED, self._on_scene_deleted)
        bus.subscribe(Events.SCENE_UPDATED, self._on_scene_updated)

        # 大纲节点删除 -> 清理场景的 outline_ref_id
        bus.subscribe(Events.OUTLINE_NODE_DELETED, self._on_outline_node_deleted)
        bus.subscribe(Events.OUTLINE_CHANGED, self._on_outline_changed)

        # 角色变更 -> 同步关系图
        bus.subscribe(Events.CHARACTER_ADDED, self._on_character_added)
        bus.subscribe(Events.CHARACTER_UPDATED, self._on_character_updated)
        bus.subscribe(Events.CHARACTER_DELETED, self._on_character_deleted)

        # 时间轴变更 -> 触发验证和场景同步
        bus.subscribe(Events.TIMELINE_EVENT_ADDED, self._on_timeline_changed)
        bus.subscribe(Events.TIMELINE_EVENT_UPDATED, self._on_timeline_changed)
        bus.subscribe(Events.TIMELINE_EVENT_DELETED, self._on_timeline_changed)

        # 证据变更 -> 触发验证
        bus.subscribe(Events.EVIDENCE_NODE_ADDED, self._on_evidence_changed)
        bus.subscribe(Events.EVIDENCE_NODE_DELETED, self._on_evidence_changed)
        bus.subscribe(Events.EVIDENCE_LINK_ADDED, self._on_evidence_changed)
        bus.subscribe(Events.EVIDENCE_UPDATED, self._on_evidence_changed)
        bus.subscribe(Events.CLUE_ADDED, self._on_evidence_changed)
        bus.subscribe(Events.CLUE_UPDATED, self._on_evidence_changed)
        bus.subscribe(Events.CLUE_DELETED, self._on_evidence_changed)

        # 项目加载 -> 重新初始化
        bus.subscribe(Events.PROJECT_LOADED, self._on_project_loaded)

        # 看板变更 -> 场景同步
        bus.subscribe(Events.KANBAN_TASK_UPDATED, self._on_kanban_task_updated)
        bus.subscribe(Events.KANBAN_TASK_MOVED, self._on_kanban_task_moved)

        # 素材变更 -> 场景引用同步
        bus.subscribe(Events.ASSET_DELETED, self._on_asset_deleted)

        # Wiki变更 -> 角色/地点同步
        bus.subscribe(Events.WIKI_ENTRY_ADDED, self._on_wiki_entry_added)
        bus.subscribe(Events.WIKI_ENTRY_UPDATED, self._on_wiki_entry_updated)
        bus.subscribe(Events.WIKI_ENTRY_DELETED, self._on_wiki_entry_deleted)

        # 灵感变更
        bus.subscribe(Events.IDEA_ADDED, self._on_idea_added)

    def set_validation_callback(self, callback: Callable) -> None:
        """
        设置验证回调函数。

        Args:
            callback: 当数据变更需要重新验证时调用的函数
        """
        self._validation_callback = callback

    def register_sync_handler(self, event_type: str, handler: Callable) -> None:
        """
        注册同步处理器。

        Args:
            event_type: 事件类型
            handler: 处理器函数
        """
        if event_type not in self._sync_handlers:
            self._sync_handlers[event_type] = []
        if handler not in self._sync_handlers[event_type]:
            self._sync_handlers[event_type].append(handler)

    def unregister_sync_handler(self, event_type: str, handler: Callable) -> bool:
        """
        取消注册同步处理器。

        Args:
            event_type: 事件类型
            handler: 处理器函数

        Returns:
            是否成功取消
        """
        if event_type in self._sync_handlers and handler in self._sync_handlers[event_type]:
            self._sync_handlers[event_type].remove(handler)
            return True
        return False

    def _call_sync_handlers(self, event_type: str, **kwargs) -> None:
        """调用注册的同步处理器。"""
        handlers = self._sync_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event_type, **kwargs)
            except Exception as e:
                logger.error(f"同步处理器错误 [{event_type}]: {e}", exc_info=True)

    def _on_scene_added(self, event_type: str, **kwargs) -> None:
        """
        场景添加时，尝试自动关联到时间轴和大纲。

        Args:
            event_type: 事件类型
            **kwargs: 包含 scene_uid, scene_name 等
        """
        if not self._enabled or not self._project_manager:
            return

        scene_uid = kwargs.get("scene_uid", "")
        scene_name = kwargs.get("scene_name", "")

        if not scene_uid or not scene_name:
            return

        # 尝试匹配时间轴事件
        timelines = self._project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])

        scene_name_lower = scene_name.strip().lower()
        matched = False

        for evt in truth_events:
            if evt.get("linked_scene_uid"):
                continue  # 已关联

            evt_name = evt.get("name", "").strip().lower()
            # 精确匹配或包含匹配
            if evt_name == scene_name_lower or evt_name in scene_name_lower or scene_name_lower in evt_name:
                evt["linked_scene_uid"] = scene_uid
                matched = True
                logger.info(f"自动关联场景 '{scene_name}' 到时间轴事件 '{evt.get('name')}'")
                break

        if matched:
            self._project_manager.mark_modified("timelines")

        self._call_sync_handlers(event_type, **kwargs)

    def _on_scene_deleted(self, event_type: str, **kwargs) -> None:
        """
        场景删除时，清理时间轴事件中的关联。

        Args:
            event_type: 事件类型
            **kwargs: 包含 scene_uid 或 scene_index
        """
        if not self._enabled or not self._project_manager:
            return

        scene_uid = kwargs.get("scene_uid", "")
        if not scene_uid:
            return

        timelines = self._project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])

        modified = False
        for evt in truth_events:
            if evt.get("linked_scene_uid") == scene_uid:
                evt["linked_scene_uid"] = ""
                modified = True
                logger.info(f"清除真相事件 '{evt.get('name')}' 的场景关联")

        if modified:
            self._project_manager.mark_modified()
            # 触发时间轴更新事件
            get_event_bus().publish(Events.TIMELINE_UPDATED, source="module_sync")

        self._call_sync_handlers(event_type, **kwargs)

    def _on_scene_updated(self, event_type: str, **kwargs) -> None:
        """
        场景更新时，检查时间同步。

        Args:
            event_type: 事件类型
            **kwargs: 包含 scene_uid 和更新数据
        """
        if not self._enabled or not self._project_manager:
            return

        # 通知同步处理器
        self._call_sync_handlers(event_type, **kwargs)

    def _on_outline_node_deleted(self, event_type: str, **kwargs) -> None:
        """
        大纲节点删除时，清理场景中的 outline_ref_id 引用。

        Args:
            event_type: 事件类型
            **kwargs: 包含 node_uids (被删除节点的UID列表)
        """
        if not self._enabled or not self._project_manager:
            return

        deleted_uids = kwargs.get("node_uids", [])
        if not deleted_uids:
            return

        deleted_uid_set = set(deleted_uids)
        scenes = self._project_manager.get_scenes()

        modified = False
        for scene in scenes:
            outline_ref_id = scene.get("outline_ref_id", "")
            if outline_ref_id and outline_ref_id in deleted_uid_set:
                scene["outline_ref_id"] = ""
                scene["outline_ref_path"] = ""
                modified = True
                logger.info(f"清除场景 '{scene.get('name')}' 的大纲关联 (节点已删除)")

        if modified:
            self._project_manager.mark_modified()
            get_event_bus().publish(Events.SCENE_UPDATED, source="module_sync")

        self._call_sync_handlers(event_type, **kwargs)

    def _on_outline_changed(self, event_type: str, **kwargs) -> None:
        """
        大纲变更时，刷新场景的 outline_ref_path 并清理失效引用。
        """
        if not self._enabled or not self._project_manager:
            return

        self._refresh_outline_paths()
        self._call_sync_handlers(event_type, **kwargs)

    def _refresh_outline_paths(self) -> None:
        """根据 outline_ref_id 重新生成 outline_ref_path。"""
        outline_root = self._project_manager.get_outline()
        scenes = self._project_manager.get_scenes()
        modified = False

        for scene in scenes:
            outline_uid = scene.get("outline_ref_id", "")
            if not outline_uid:
                continue
            node = self._project_manager.find_node_by_uid(outline_root, outline_uid)
            if not node:
                scene["outline_ref_id"] = ""
                scene["outline_ref_path"] = ""
                modified = True
                continue
            new_path = self._project_manager.get_outline_path(outline_uid)
            if scene.get("outline_ref_path", "") != new_path:
                scene["outline_ref_path"] = new_path
                modified = True

        if modified:
            self._project_manager.mark_modified()

    def _on_character_added(self, event_type: str, **kwargs) -> None:
        """
        角色添加时，自动添加到关系图节点列表。

        Args:
            event_type: 事件类型
            **kwargs: 包含 char_name, char_index 等
        """
        if not self._enabled or not self._project_manager:
            return

        char_name = kwargs.get("char_name", "")
        if not char_name:
            return

        rels = self._project_manager.get_relationships()
        nodes = rels.get("nodes", [])

        # 检查是否已存在
        existing_ids = {n.get("id") for n in nodes}
        if char_name in existing_ids:
            return

        # 自动添加到关系图节点
        new_node = {
            "id": char_name,
            "type": "character",
            "x": 100 + len(nodes) * 50,  # 简单的位置分布
            "y": 100 + (len(nodes) % 5) * 80
        }
        nodes.append(new_node)
        self._project_manager.mark_modified("relationships")
        logger.info(f"自动添加角色 '{char_name}' 到关系图")

        self._call_sync_handlers(event_type, **kwargs)

    def _on_character_deleted(self, event_type: str, **kwargs) -> None:
        """
        角色删除时，清理关系图中的相关 links。

        Args:
            event_type: 事件类型
            **kwargs: 包含 char_index 或 char_name
        """
        if not self._enabled or not self._project_manager:
            return

        char_index = kwargs.get("char_index")
        char_name = kwargs.get("char_name", "")

        # 如果没有角色名，尝试从索引获取（但角色已删除，需要从事件中传递）
        if not char_name and char_index is not None:
            # 角色已经删除，无法从索引获取名称
            # 需要在 DeleteCharacterCommand 中传递角色名
            return

        if not char_name:
            return

        rels = self._project_manager.get_relationships()
        links = rels.get("links", [])
        nodes = rels.get("nodes", [])

        # 删除与该角色相关的所有连接
        original_len = len(links)
        links[:] = [
            link for link in links
            if link.get("source") != char_name and link.get("target") != char_name
        ]

        # 删除角色节点
        nodes[:] = [
            node for node in nodes
            if node.get("id") != char_name
        ]

        if len(links) < original_len or len(nodes) < len(rels.get("nodes", [])):
            self._project_manager.mark_modified("relationships")
            get_event_bus().publish(Events.RELATIONSHIPS_UPDATED, source="module_sync")
            logger.info(f"清除角色 '{char_name}' 的关系图关联")

        self._call_sync_handlers(event_type, **kwargs)

    def _on_character_updated(self, event_type: str, **kwargs) -> None:
        """角色更新时，同步角色图片到百科。"""
        if not self._enabled or not self._project_manager:
            return

        if kwargs.get("source") == "module_sync":
            return

        char_name = kwargs.get("char_name", "")
        if not char_name:
            self._call_sync_handlers(event_type, **kwargs)
            return

        characters = self._project_manager.get_characters()
        char = next((c for c in characters if c.get("name") == char_name), None)
        if not char:
            self._call_sync_handlers(event_type, **kwargs)
            return

        self._sync_character_image_to_wiki(char_name, char.get("image_path", ""))
        self._call_sync_handlers(event_type, **kwargs)

    def _on_timeline_changed(self, event_type: str, **kwargs) -> None:
        """
        时间轴变更时，触发相关同步。

        Args:
            event_type: 事件类型
            **kwargs: 包含 event_uid, track_type 等
        """
        if not self._enabled:
            return

        # 触发验证（延迟执行，避免频繁验证）
        self._request_validation()

        # 通知同步处理器
        self._call_sync_handlers(event_type, **kwargs)

    def _on_evidence_changed(self, event_type: str, **kwargs) -> None:
        """
        证据变更时，触发验证。

        Args:
            event_type: 事件类型
            **kwargs: 包含 node_uid 等
        """
        if not self._enabled:
            return

        # 触发验证
        self._request_validation()

        # 通知同步处理器
        self._call_sync_handlers(event_type, **kwargs)

    def _on_project_loaded(self, event_type: str, **kwargs) -> None:
        """
        项目加载时，执行完整性检查。

        Args:
            event_type: 事件类型
            **kwargs: 项目信息
        """
        if not self._enabled or not self._project_manager:
            return

        # 检查并修复无效的场景关联（时间轴 -> 场景）
        self._cleanup_invalid_scene_links()

        # 检查并修复无效的真相事件关联（谎言 -> 真相）
        self._cleanup_invalid_truth_links()

        # 检查并修复无效的大纲引用（场景 -> 大纲）
        self._cleanup_invalid_outline_refs()

        # 检查并修复无效的角色关系图引用
        self._cleanup_invalid_relationship_links()

        # 刷新大纲路径引用
        self._refresh_outline_paths()

        # 通知同步处理器
        self._call_sync_handlers(event_type, **kwargs)

    def _cleanup_invalid_scene_links(self) -> None:
        """清理无效的场景关联。"""
        if not self._project_manager:
            return

        scenes = self._project_manager.get_scenes()
        scene_uids = {s.get("uid") for s in scenes if s.get("uid")}

        timelines = self._project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])

        modified = False
        for evt in truth_events:
            linked_uid = evt.get("linked_scene_uid", "")
            if linked_uid and linked_uid not in scene_uids:
                evt["linked_scene_uid"] = ""
                modified = True
                logger.warning(f"清除真相事件 '{evt.get('name')}' 的无效场景关联")

        if modified:
            self._project_manager.mark_modified()

    def _cleanup_invalid_truth_links(self) -> None:
        """清理无效的真相事件关联。"""
        if not self._project_manager:
            return

        timelines = self._project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])
        lie_events = timelines.get("lie_events", [])

        truth_uids = {e.get("uid") for e in truth_events if e.get("uid")}

        modified = False
        for evt in lie_events:
            linked_uid = evt.get("linked_truth_event_uid", "")
            if linked_uid and linked_uid not in truth_uids:
                evt["linked_truth_event_uid"] = ""
                modified = True
                logger.warning(f"清除谎言事件 '{evt.get('name')}' 的无效真相关联")

        if modified:
            self._project_manager.mark_modified()

    def _cleanup_invalid_outline_refs(self) -> None:
        """清理无效的大纲引用（场景 -> 大纲）。"""
        if not self._project_manager:
            return

        # 收集所有有效的大纲节点 UID
        outline_root = self._project_manager.get_outline()
        valid_uids = set()

        def collect_uids(node):
            if not node:
                return
            uid = node.get("uid")
            if uid:
                valid_uids.add(uid)
            for child in node.get("children", []):
                collect_uids(child)

        collect_uids(outline_root)

        # 检查场景的 outline_ref_id
        scenes = self._project_manager.get_scenes()
        modified = False
        for scene in scenes:
            outline_ref_id = scene.get("outline_ref_id", "")
            if outline_ref_id and outline_ref_id not in valid_uids:
                scene["outline_ref_id"] = ""
                scene["outline_ref_path"] = ""
                modified = True
                logger.warning(f"清除场景 '{scene.get('name')}' 的无效大纲引用")

        if modified:
            self._project_manager.mark_modified()

    def _cleanup_invalid_relationship_links(self) -> None:
        """清理无效的角色关系图引用。"""
        if not self._project_manager:
            return

        # 收集所有有效的角色名
        characters = self._project_manager.get_characters()
        valid_char_names = {c.get("name") for c in characters if c.get("name")}

        # 收集所有有效的势力名
        factions = self._project_manager.get_factions()
        valid_faction_names = {f.get("name") for f in factions if f.get("name")}

        rels = self._project_manager.get_relationships()
        links = rels.get("links", [])
        nodes = rels.get("nodes", [])

        # 过滤无效的连接
        original_link_count = len(links)
        valid_links = []
        for link in links:
            source = link.get("source", "")
            target = link.get("target", "")
            target_type = link.get("target_type", "character")

            # 检查 source（通常是角色）
            source_valid = source in valid_char_names or source in valid_faction_names

            # 检查 target
            if target_type == "faction":
                target_valid = target in valid_faction_names
            else:
                target_valid = target in valid_char_names

            if source_valid and target_valid:
                valid_links.append(link)
            else:
                logger.warning(f"清除无效关系: {source} -> {target}")

        # 过滤无效的节点
        original_node_count = len(nodes)
        valid_nodes = [
            node for node in nodes
            if node.get("id") in valid_char_names or node.get("id") in valid_faction_names
        ]

        if len(valid_links) < original_link_count or len(valid_nodes) < original_node_count:
            rels["links"] = valid_links
            rels["nodes"] = valid_nodes
            self._project_manager.mark_modified("relationships")
            logger.info(f"关系图清理完成: 移除 {original_link_count - len(valid_links)} 条连接, {original_node_count - len(valid_nodes)} 个节点")

    def _request_validation(self) -> None:
        """请求重新验证。"""
        if self._validation_callback:
            try:
                self._validation_callback()
            except Exception as e:
                logger.error(f"验证回调错误: {e}", exc_info=True)

    def sync_timeline_to_scene(self, event_uid: str, scene_uid: str) -> bool:
        """
        同步时间轴事件到场景。

        Args:
            event_uid: 时间轴事件 UID
            scene_uid: 场景 UID

        Returns:
            是否成功
        """
        if not self._project_manager:
            return False

        timelines = self._project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])

        for evt in truth_events:
            if evt.get("uid") == event_uid:
                evt["linked_scene_uid"] = scene_uid
                self._project_manager.mark_modified()
                get_event_bus().publish(
                    Events.TIMELINE_EVENT_UPDATED,
                    event_uid=event_uid,
                    track_type="truth",
                    source="module_sync"
                )
                return True

        return False

    def sync_lie_to_truth(self, lie_uid: str, truth_uid: str) -> bool:
        """
        同步谎言事件到真相事件。

        Args:
            lie_uid: 谎言事件 UID
            truth_uid: 真相事件 UID

        Returns:
            是否成功
        """
        if not self._project_manager:
            return False

        timelines = self._project_manager.project_data.get("timelines", {})
        lie_events = timelines.get("lie_events", [])

        for evt in lie_events:
            if evt.get("uid") == lie_uid:
                evt["linked_truth_event_uid"] = truth_uid
                self._project_manager.mark_modified()
                get_event_bus().publish(
                    Events.TIMELINE_EVENT_UPDATED,
                    event_uid=lie_uid,
                    track_type="lie",
                    source="module_sync"
                )
                return True

        return False

    def get_linked_truth_events(self, scene_uid: str) -> List[Dict[str, Any]]:
        """
        获取与场景关联的真相事件列表。

        Args:
            scene_uid: 场景 UID

        Returns:
            关联的真相事件列表
        """
        if not self._project_manager:
            return []

        timelines = self._project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])

        return [evt for evt in truth_events if evt.get("linked_scene_uid") == scene_uid]

    def get_linked_lie_events(self, truth_uid: str) -> List[Dict[str, Any]]:
        """
        获取与真相事件关联的谎言事件列表。

        Args:
            truth_uid: 真相事件 UID

        Returns:
            关联的谎言事件列表
        """
        if not self._project_manager:
            return []

        timelines = self._project_manager.project_data.get("timelines", {})
        lie_events = timelines.get("lie_events", [])

        return [evt for evt in lie_events if evt.get("linked_truth_event_uid") == truth_uid]

    # ========== 看板同步处理器 ==========

    def _on_kanban_task_updated(self, event_type: str, **kwargs) -> None:
        """
        看板任务更新时，同步场景状态。

        Args:
            event_type: 事件类型
            **kwargs: 包含 scene_uid, status 等
        """
        if not self._enabled or not self._project_manager:
            return

        scene_uid = kwargs.get("scene_uid", "")
        new_status = kwargs.get("status", "")

        if not scene_uid or not new_status:
            self._call_sync_handlers(event_type, **kwargs)
            return

        # 更新场景的看板状态
        scenes = self._project_manager.get_scenes()
        for scene in scenes:
            if scene.get("uid") == scene_uid:
                old_status = scene.get("kanban_status", "")
                if old_status != new_status:
                    scene["kanban_status"] = new_status
                    self._project_manager.mark_modified()
                    logger.info(f"同步场景 '{scene.get('name')}' 看板状态: {old_status} -> {new_status}")
                break

        self._call_sync_handlers(event_type, **kwargs)

    def _on_kanban_task_moved(self, event_type: str, **kwargs) -> None:
        """
        看板任务移动时，更新场景顺序和状态。

        Args:
            event_type: 事件类型
            **kwargs: 包含 scene_uid, from_column, to_column, new_index 等
        """
        if not self._enabled or not self._project_manager:
            return

        scene_uid = kwargs.get("scene_uid", "")
        to_column = kwargs.get("to_column", "")

        if scene_uid and to_column:
            scenes = self._project_manager.get_scenes()
            for scene in scenes:
                if scene.get("uid") == scene_uid:
                    scene["kanban_status"] = to_column
                    self._project_manager.mark_modified()
                    logger.info(f"场景 '{scene.get('name')}' 移动到看板列: {to_column}")
                    break

        self._call_sync_handlers(event_type, **kwargs)

    # ========== 素材同步处理器 ==========

    def _on_asset_deleted(self, event_type: str, **kwargs) -> None:
        """
        素材删除时，清理场景中的素材引用。

        Args:
            event_type: 事件类型
            **kwargs: 包含 asset_id, asset_type 等
        """
        if not self._enabled or not self._project_manager:
            return

        asset_id = kwargs.get("asset_id", "")
        if not asset_id:
            self._call_sync_handlers(event_type, **kwargs)
            return

        scenes = self._project_manager.get_scenes()
        modified = False

        for scene in scenes:
            # 清理场景的素材引用列表
            asset_refs = scene.get("asset_refs", [])
            if asset_id in asset_refs:
                asset_refs.remove(asset_id)
                modified = True
                logger.info(f"清除场景 '{scene.get('name')}' 的素材引用: {asset_id}")

            # 清理场景的背景图引用
            if scene.get("background_asset") == asset_id:
                scene["background_asset"] = ""
                modified = True
                logger.info(f"清除场景 '{scene.get('name')}' 的背景素材引用")

            # 清理场景的音乐引用
            if scene.get("music_asset") == asset_id:
                scene["music_asset"] = ""
                modified = True
                logger.info(f"清除场景 '{scene.get('name')}' 的音乐素材引用")

        if modified:
            self._project_manager.mark_modified()
            get_event_bus().publish(Events.SCENE_UPDATED, source="module_sync")

        self._call_sync_handlers(event_type, **kwargs)

    # ========== Wiki同步处理器 ==========

    def _is_character_category(self, category: str) -> bool:
        """判断是否为角色类百科分类。"""
        cat = (category or "").strip().lower()
        return cat in ("人物", "角色", "character", "npc")

    def _find_character_index(self, name: str) -> Optional[int]:
        if not name:
            return None
        characters = self._project_manager.get_characters()
        for idx, char in enumerate(characters):
            if char.get("name") == name:
                return idx
        return None

    def _sync_character_image_to_wiki(self, char_name: str, image_path: str) -> None:
        """将角色图片同步到对应百科条目（人物类）。"""
        if not self._project_manager or not char_name:
            return

        entries = self._project_manager.get_world_entries()
        for idx, entry in enumerate(entries):
            if entry.get("name") != char_name:
                continue
            if not self._is_character_category(entry.get("category", "")):
                continue

            current = entry.get("image_path", "")
            if current == image_path:
                return

            # 仅在角色有图片或百科缺图时覆盖，避免误清空
            if image_path or not current:
                entry["image_path"] = image_path or ""
                self._project_manager.mark_modified("wiki")
                get_event_bus().publish(
                    Events.WIKI_ENTRY_UPDATED,
                    entry_idx=idx,
                    entry_name=entry.get("name", ""),
                    source="module_sync"
                )
            return

    def _sync_wiki_image_to_character(self, entry_name: str, image_path: str) -> None:
        """将百科图片同步到角色数据。"""
        if not self._project_manager or not entry_name:
            return

        idx = self._find_character_index(entry_name)
        if idx is None:
            return

        characters = self._project_manager.get_characters()
        char = characters[idx]
        current = char.get("image_path", "")
        if current == image_path:
            return

        # 仅在百科有图片或角色缺图时覆盖，避免误清空
        if image_path or not current:
            char["image_path"] = image_path or ""
            self._project_manager.mark_modified("script")
            get_event_bus().publish(
                Events.CHARACTER_UPDATED,
                char_index=idx,
                char_name=char.get("name", ""),
                source="module_sync"
            )

    def _on_wiki_entry_added(self, event_type: str, **kwargs) -> None:
        """
        Wiki条目添加时，尝试同步到角色或地点。

        Args:
            event_type: 事件类型
            **kwargs: 包含 entry_name, category 等
        """
        if not self._enabled or not self._project_manager:
            return

        if kwargs.get("source") == "module_sync":
            return

        entry_name = kwargs.get("entry_name", "")
        category = kwargs.get("category", "").lower()
        entry_idx = kwargs.get("entry_idx")

        if not entry_name and entry_idx is not None:
            entries = self._project_manager.get_world_entries()
            if 0 <= entry_idx < len(entries):
                entry = entries[entry_idx]
                entry_name = entry.get("name", "")
                category = entry.get("category", "").lower()

        if not entry_name:
            self._call_sync_handlers(event_type, **kwargs)
            return

        # 如果Wiki条目是角色类别，检查是否需要同步到角色列表
        if self._is_character_category(category):
            characters = self._project_manager.get_characters()
            existing_names = {c.get("name", "").lower() for c in characters}

            if entry_name.lower() not in existing_names:
                # 可选：自动创建角色（需要用户确认，这里只记录日志）
                logger.info(f"Wiki条目 '{entry_name}' (类别: {category}) 可同步为角色")
            else:
                # 同步图片到角色（只在百科有图或角色缺图时）
                entry = next((e for e in self._project_manager.get_world_entries() if e.get("name") == entry_name), None)
                if entry:
                    self._sync_wiki_image_to_character(entry_name, entry.get("image_path", ""))

        # 如果Wiki条目是地点类别，检查是否需要同步
        elif category in ("地点", "location", "场所", "地方"):
            logger.info(f"Wiki条目 '{entry_name}' (类别: {category}) 可用于场景地点")

        self._call_sync_handlers(event_type, **kwargs)

    def _on_wiki_entry_updated(self, event_type: str, **kwargs) -> None:
        """Wiki条目更新时，同步角色图片。"""
        if not self._enabled or not self._project_manager:
            return

        if kwargs.get("source") == "module_sync":
            return

        entry_idx = kwargs.get("entry_idx")
        entry_name = kwargs.get("entry_name", "")
        entries = self._project_manager.get_world_entries()

        entry = None
        if entry_idx is not None and 0 <= entry_idx < len(entries):
            entry = entries[entry_idx]
        elif entry_name:
            entry = next((e for e in entries if e.get("name") == entry_name), None)

        if not entry:
            self._call_sync_handlers(event_type, **kwargs)
            return

        if self._is_character_category(entry.get("category", "")):
            self._sync_wiki_image_to_character(entry.get("name", ""), entry.get("image_path", ""))

        self._call_sync_handlers(event_type, **kwargs)

    def _on_wiki_entry_deleted(self, event_type: str, **kwargs) -> None:
        """
        Wiki条目删除时，清理相关引用。

        Args:
            event_type: 事件类型
            **kwargs: 包含 entry_name, entry_uid 等
        """
        if not self._enabled or not self._project_manager:
            return

        entry_name = kwargs.get("entry_name", "")
        entry_uid = kwargs.get("entry_uid", "")

        if not entry_name and not entry_uid:
            self._call_sync_handlers(event_type, **kwargs)
            return

        # 清理场景中的Wiki引用
        scenes = self._project_manager.get_scenes()
        modified = False

        for scene in scenes:
            wiki_refs = scene.get("wiki_refs", [])
            # 按名称或UID匹配
            original_len = len(wiki_refs)
            wiki_refs[:] = [
                ref for ref in wiki_refs
                if ref.get("name") != entry_name and ref.get("uid") != entry_uid
            ]
            if len(wiki_refs) < original_len:
                modified = True
                logger.info(f"清除场景 '{scene.get('name')}' 的Wiki引用: {entry_name or entry_uid}")

        # 清理角色描述中的Wiki链接（可选，复杂度高，暂不实现）

        if modified:
            self._project_manager.mark_modified()

        self._call_sync_handlers(event_type, **kwargs)

    # ========== 灵感同步处理器 ==========

    def _on_idea_added(self, event_type: str, **kwargs) -> None:
        """
        灵感添加时，检查是否可关联到大纲或场景。

        Args:
            event_type: 事件类型
            **kwargs: 包含 idea_content, idea_tags 等
        """
        if not self._enabled or not self._project_manager:
            return

        idea_content = kwargs.get("idea_content", "")
        idea_tags = kwargs.get("idea_tags", [])
        idea_uid = kwargs.get("idea_uid", "")

        if not idea_content:
            self._call_sync_handlers(event_type, **kwargs)
            return

        # 检查灵感内容是否与现有大纲节点相关
        outline_root = self._project_manager.get_outline()
        matched_nodes = []

        def find_matching_nodes(node, content_lower):
            if not node:
                return
            node_name = node.get("name", "").lower()
            # 简单的关键词匹配
            if node_name and (node_name in content_lower or content_lower in node_name):
                matched_nodes.append(node.get("name"))
            for child in node.get("children", []):
                find_matching_nodes(child, content_lower)

        find_matching_nodes(outline_root, idea_content.lower()[:100])

        if matched_nodes:
            logger.info(f"灵感可能与大纲节点相关: {matched_nodes[:3]}")

        # 检查灵感标签是否与角色相关
        if idea_tags:
            characters = self._project_manager.get_characters()
            char_names = {c.get("name", "").lower() for c in characters}
            matching_tags = [tag for tag in idea_tags if tag.lower() in char_names]
            if matching_tags:
                logger.info(f"灵感标签与角色相关: {matching_tags}")

        self._call_sync_handlers(event_type, **kwargs)

    def enable(self) -> None:
        """启用同步服务。"""
        self._enabled = True

    def disable(self) -> None:
        """禁用同步服务。"""
        self._enabled = False

    def is_enabled(self) -> bool:
        """检查同步服务是否启用。"""
        return self._enabled


# 全局单例访问函数
_sync_service_instance: Optional[ModuleSyncService] = None


def get_module_sync_service() -> ModuleSyncService:
    """获取模块同步服务单例。"""
    global _sync_service_instance
    if _sync_service_instance is None:
        _sync_service_instance = ModuleSyncService()
    return _sync_service_instance


def init_module_sync(project_manager) -> ModuleSyncService:
    """
    初始化模块同步服务。

    Args:
        project_manager: ProjectManager 实例

    Returns:
        ModuleSyncService 实例
    """
    service = get_module_sync_service()
    service.initialize(project_manager)
    return service
