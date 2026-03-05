import json
import uuid
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set

from writer_app.core.exceptions import (
    ProjectLoadError,
    ProjectSaveError,
    ProjectValidationError,
    ResourceNotFoundError
)
from writer_app.core.validators import ProjectValidator
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.core.typed_data import (
    create_typed_project_data,
    migrate_project_type as typed_migrate,
    get_required_modules,
    get_cleanup_info,
    ensure_module_exists,
    DataModule
)

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manages the project data structure, loading, and saving."""

    def __init__(self):
        self.current_file = None
        self.project_data = self._create_empty_project()
        self.modified = False
        self._listeners = []

    def add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def notify_listeners(self, event_type="all"):
        for callback in self._listeners:
            callback(event_type)

    def _create_empty_project(self, project_type: str = "General"):
        """
        Create an empty project with only modules needed for the specified type.

        Args:
            project_type: The project type key (default: "General")

        Returns:
            Dict with type-appropriate data structure
        """
        project_data = create_typed_project_data(project_type, self._gen_uid)
        from writer_app.core.project_types import ProjectTypeManager
        meta = project_data.setdefault("meta", {})
        preset = ProjectTypeManager.get_preset_config(
            project_type,
            meta.get("genre_tags", []),
            meta.get("length", "Long")
        )
        meta["enabled_tools"] = ProjectTypeManager.get_default_tools_list(
            project_type,
            meta.get("length", "Long"),
            meta.get("genre_tags", [])
        )
        meta.setdefault("genre_tags", [])
        meta["custom_wiki_categories"] = preset.get("wiki_categories", [])
        from writer_app.core.module_registry import get_module_info
        modules_to_ensure = set()
        for tool_key in meta.get("enabled_tools", []):
            info = get_module_info(tool_key)
            if info:
                modules_to_ensure.update(info.data_modules)
        for module in modules_to_ensure:
            ensure_module_exists(project_data, module)
        return project_data

    def _create_legacy_project(self):
        """
        Create a legacy project structure with all modules.
        Used for backward compatibility when loading old projects.
        """
        return {
            "meta": {
                "type": "General",
                "length": "Long",
                "outline_template_style": "default",
                "created_at": "",
                "version": "1.0",
                "kanban_columns": ["构思", "初稿", "润色", "定稿"]
            },
            "outline": {"name": "项目大纲", "children": [], "uid": self._gen_uid(), "flat_draft": []},
            "script": {
                "title": "未命名剧本",
                "characters": [],
                "scenes": []
            },
            "world": {
                "entries": []
            },
            "relationships": {
                "layout": {},
                "character_layout": {},
                "evidence_layout": {},
                "relationship_links": [],
                "evidence_links": [],
                "links": [],
                "nodes": [],
                "snapshots": [],
                "relationship_events": []
            },
            "factions": {
                "groups": [],
                "matrix": {}
            },
            "variables": [],
            "research": [],
            "ideas": [],
            "timelines": {
                "truth_events": [],
                "lie_events": []
            },
            "tags": []
        }

    def do_migrate_project_type(self, new_type: str, cleanup_action: str = "archive") -> Dict[str, Any]:
        """
        Migrate the current project to a new type.

        Args:
            new_type: Target project type
            cleanup_action: "archive" to keep unused data, "delete" to remove

        Returns:
            Migration result summary:
            {
                "archived": list of archived module keys,
                "deleted": list of deleted module keys,
                "added": list of new module keys,
                "restored": list of restored module keys
            }
        """
        old_type = self.get_project_type()

        if old_type == new_type:
            return {"archived": [], "deleted": [], "added": [], "restored": []}

        result = typed_migrate(
            self.project_data,
            old_type,
            new_type,
            cleanup_action,
            self._gen_uid
        )

        # Update outline template style if it was default
        current_style = self.project_data.get("meta", {}).get("outline_template_style", "default")
        if current_style in ("default", "", None):
            from writer_app.core.project_types import ProjectTypeManager
            self.project_data["meta"]["outline_template_style"] = ProjectTypeManager.get_default_outline_view(new_type)

        self.mark_modified()
        get_event_bus().publish(Events.PROJECT_TYPE_CHANGED, old_type=old_type, new_type=new_type)
        get_event_bus().publish(Events.PROJECT_CONFIG_CHANGED, fields=["type"])

        logger.info(f"Project migrated from {old_type} to {new_type}: {result}")
        return result

    def get_migration_preview(self, new_type: str) -> List[Dict[str, Any]]:
        """
        Get a preview of what data would be affected when migrating to a new type.

        Args:
            new_type: Target project type

        Returns:
            List of dicts with module info and data counts
        """
        old_type = self.get_project_type()
        return get_cleanup_info(old_type, new_type, self.project_data)

    def ensure_module(self, module: DataModule) -> None:
        """
        Ensure a specific data module exists, creating it if necessary.

        Args:
            module: The DataModule to ensure exists
        """
        ensure_module_exists(self.project_data, module)

    def new_project(self, project_type: str = "General"):
        """
        Create a new empty project.

        Args:
            project_type: The project type for the new project (default: "General")
        """
        self.project_data = self._create_empty_project(project_type)
        self.current_file = None
        self.modified = False
        self.notify_listeners()
        get_event_bus().publish(Events.PROJECT_NEW)

    def load_project(self, file_path: str) -> bool:
        """
        加载项目文件。

        Args:
            file_path: 项目文件路径

        Returns:
            True 表示加载成功

        Raises:
            ProjectLoadError: 加载失败时抛出
        """
        path = Path(file_path)

        if not path.exists():
            raise ProjectLoadError(f"文件不存在: {file_path}", file_path=file_path)

        if not path.suffix.lower() == '.writerproj':
            logger.warning(f"文件扩展名不是 .writerproj: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ProjectLoadError(f"JSON 格式错误: {e}", file_path=file_path, cause=e)
        except PermissionError as e:
            raise ProjectLoadError(f"没有读取权限: {file_path}", file_path=file_path, cause=e)
        except IOError as e:
            raise ProjectLoadError(f"读取文件失败: {e}", file_path=file_path, cause=e)

        # 验证项目结构
        validation_errors = ProjectValidator.validate_structure(data)
        if validation_errors:
            logger.warning(f"项目数据不完整，将尝试修复: {validation_errors}")

        # 迁移旧版本数据
        self.project_data = ProjectValidator.migrate(data)

        # 确保大纲节点有 UID（使用迭代算法）
        self._ensure_outline_uids_iterative(self.project_data.get("outline"))

        self.current_file = file_path
        self.modified = False
        logger.info(f"项目加载成功: {file_path}")
        self.notify_listeners()
        get_event_bus().publish(Events.PROJECT_LOADED, file_path=file_path)
        return True

    def save_project(self, file_path: str = None) -> bool:
        """
        保存项目文件。

        Args:
            file_path: 保存路径，为空则使用当前文件路径

        Returns:
            True 表示保存成功

        Raises:
            ProjectSaveError: 保存失败时抛出
        """
        path = file_path or self.current_file
        if not path:
            raise ProjectSaveError("未指定保存路径")

        try:
            # 创建副本以清理临时属性
            save_data = json.loads(json.dumps(self.project_data))
            self._ensure_outline_uids_iterative(save_data.get("outline"))
            self._clean_temp_attrs_iterative(save_data.get("outline"))

            # 确保父目录存在
            Path(path).parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

        except PermissionError as e:
            raise ProjectSaveError(f"没有写入权限: {path}", file_path=path, cause=e)
        except IOError as e:
            raise ProjectSaveError(f"写入文件失败: {e}", file_path=path, cause=e)
        except Exception as e:
            raise ProjectSaveError(f"保存失败: {e}", file_path=path, cause=e)

        self.current_file = path
        self.modified = False
        logger.info(f"项目保存成功: {path}")
        self.notify_listeners()
        get_event_bus().publish(Events.PROJECT_SAVED, file_path=path)
        return True

    def _clean_temp_attrs_iterative(self, root: dict) -> None:
        """使用迭代算法清理临时属性（如 _collapsed）。"""
        if root is None:
            return

        stack = [root]
        while stack:
            node = stack.pop()
            if "_collapsed" in node:
                del node["_collapsed"]
            # 将子节点加入栈
            for child in node.get("children", []):
                stack.append(child)

    def mark_modified(self, event_type="all"):
        self.modified = True
        self.notify_listeners(event_type)

    # --- Data Access Helpers ---

    def get_project_data(self) -> Dict[str, Any]:
        return self.project_data
    
    def get_outline(self):
        return self.project_data.get("outline", {})

    def set_outline(self, outline_data):
        self._ensure_outline_uids(outline_data)
        self.project_data["outline"] = outline_data
        self.mark_modified("outline")

    def get_flat_draft_entries(self):
        outline = self.get_outline() or {}
        entries = outline.get("flat_draft")
        if not isinstance(entries, list):
            entries = []
            outline["flat_draft"] = entries
        return entries

    def set_flat_draft_entries(self, entries):
        outline = self.get_outline() or {}
        outline["flat_draft"] = list(entries)
        self.mark_modified("outline")

    def get_script(self):
        return self.project_data.get("script", {})
    
    def get_characters(self):
        chars = self.project_data.get("script", {}).get("characters", [])
        for c in chars:
            c.setdefault("events", [])
        return chars

    def get_character_by_name(self, name):
        for c in self.get_characters():
            if c["name"] == name:
                return c
        return None

    def add_character_event(self, char_name, event_data):
        """
        Add an event to a character's personal timeline.
        event_data: { "summary": str, "time": str, "type": str, "source": str }
        """
        char = self.get_character_by_name(char_name)
        if char:
            if "events" not in char: char["events"] = []
            if "uid" not in event_data: event_data["uid"] = self._gen_uid()
            char["events"].append(event_data)
            self.mark_modified("script")
            return True
        return False

    def get_character_events(self, char_name):
        char = self.get_character_by_name(char_name)
        return char.get("events", []) if char else []

    def get_scenes(self):
        return self.project_data.get("script", {}).get("scenes", [])

    def get_world_entries(self):
        return self.project_data.get("world", {}).get("entries", [])

    def sync_to_wiki(self, name, category, action="add", content=None, old_name=None):
        """
        Synchronize entity changes to the Wiki (World Settings).
        
        Args:
            name: Name of the entity (Character, Location, etc.)
            category: Wiki category (e.g., "人物", "地点")
            action: "add", "update", "delete"
            content: Optional initial content for the wiki entry
            old_name: Required if action is "update" and name changed
        """
        entries = self.get_world_entries()
        
        if action == "add":
            # Check if exists
            if any(e.get("name") == name for e in entries):
                return # Already exists
            
            new_entry = {
                "name": name,
                "category": category,
                "content": content or f"自动生成的{category}条目。",
                "iceberg_depth": "surface",
                "image_path": ""
            }
            entries.append(new_entry)
            self.mark_modified("wiki")
            
        elif action == "update":
            target_name = old_name if old_name else name
            for entry in entries:
                if entry.get("name") == target_name:
                    if name != target_name:
                        entry["name"] = name
                    # Only update content if specifically provided (don't overwrite user edits)
                    if content and len(content) > len(entry.get("content", "")): 
                         entry["content"] = content
                    self.mark_modified("wiki")
                    break
                    
        elif action == "delete":
            # Optional: Ask user? For now, we don't auto-delete to preserve data safety
            # unless strictly required. The user asked for "sync", but deleting wiki
            # just because char is deleted might be dangerous if wiki has lots of info.
            # Let's mark it as [已归档] instead or do nothing. 
            # Per user request "wiki能够及时对应", let's rename to include [Deleted] tag
            for entry in entries:
                if entry.get("name") == name:
                    entry["name"] = f"{name} [已删除]"
                    self.mark_modified("wiki")
                    break

    # --- Faction Helpers ---
    def get_factions(self):
        return self.project_data.get("factions", {}).get("groups", [])

    def get_faction_matrix(self):
        return self.project_data.get("factions", {}).get("matrix", {})

    def add_faction(self, name, color="#999"):
        if "factions" not in self.project_data:
            self.project_data["factions"] = {"groups": [], "matrix": {}}
        
        uid = self._gen_uid()
        self.project_data["factions"]["groups"].append({
            "uid": uid, "name": name, "color": color, "desc": ""
        })
        
        # Auto-create Wiki entry for the faction
        entries = self.get_world_entries()
        if not any(e.get("name") == name for e in entries):
            entries.append({
                "name": name,
                "category": "势力",
                "content": "自动生成的势力条目。",
                "iceberg_depth": "surface",
                "faction_uid": uid # Link back
            })
            
        self.mark_modified("factions")
        return uid

    def update_faction_relation(self, uid_a, uid_b, value):
        if "factions" not in self.project_data: return
        matrix = self.project_data["factions"]["matrix"]
        
        if uid_a not in matrix: matrix[uid_a] = {}
        matrix[uid_a][uid_b] = value
        
        # Symmetric? Usually relation is mutual, but politics can be one-sided.
        # Let's assume mutual for simplicity in this matrix view unless specified.
        # But for storage, let's store both to allow asymmetry if needed later.
        if uid_b not in matrix: matrix[uid_b] = {}
        matrix[uid_b][uid_a] = value
        
        self.mark_modified("factions")

    # --- Variable Helpers (Galgame State) ---
    def get_variables(self):
        return self.project_data.get("variables", [])

    def add_variable(self, name, var_type="bool", value=None, desc=""):
        """
        Add a global variable.
        var_type: "bool", "int", "str"
        """
        if "variables" not in self.project_data:
            self.project_data["variables"] = []

        # Default values based on type
        if value is None:
            if var_type == "bool": value = False
            elif var_type == "int": value = 0
            else: value = ""

        # Check for duplicates
        if any(v["name"] == name for v in self.project_data["variables"]):
            return None # Fail

        var = {
            "uid": self._gen_uid(),
            "name": name,
            "type": var_type,
            "value": value,
            "desc": desc
        }
        self.project_data["variables"].append(var)
        self.mark_modified("variables")
        return var["uid"]

    def update_variable(self, uid, updated_data):
        """Update variable definition."""
        vars_list = self.get_variables()
        for i, var in enumerate(vars_list):
            if var.get("uid") == uid:
                vars_list[i].update(updated_data)
                self.mark_modified("variables")
                return True
        return False

    def delete_variable(self, uid):
        vars_list = self.get_variables()
        for i, var in enumerate(vars_list):
            if var.get("uid") == uid:
                del vars_list[i]
                self.mark_modified("variables")
                return True
        return False

    def get_ideas(self):
        return self.project_data.get("ideas", [])

    def add_idea(self, content, tags=None):
        if tags is None: tags = []
        idea = {
            "uid": self._gen_uid(),
            "content": content,
            "tags": tags,
            "created_at": "" # In a real app, use datetime.now().isoformat()
        }
        if "ideas" not in self.project_data:
            self.project_data["ideas"] = []
        self.project_data["ideas"].insert(0, idea)
        self.mark_modified("ideas")
        get_event_bus().publish(Events.IDEA_ADDED, idea_uid=idea["uid"])
        get_event_bus().publish(Events.IDEAS_UPDATED)
        return idea

    def delete_idea(self, uid):
        ideas = self.get_ideas()
        for i, idea in enumerate(ideas):
            if idea.get("uid") == uid:
                del ideas[i]
                self.mark_modified("ideas")
                get_event_bus().publish(Events.IDEA_DELETED, idea_uid=uid)
                get_event_bus().publish(Events.IDEAS_UPDATED)
                return True
        return False
    
    def get_relationships(self):
        return self.project_data.get(
            "relationships",
            {
                "layout": {},
                "character_layout": {},
                "evidence_layout": {},
                "relationship_links": [],
                "evidence_links": [],
                "links": [],
                "relationship_events": []
            }
        )

    def get_relationship_snapshots(self):
        return self.get_relationships().get("snapshots", [])

    def add_relationship_snapshot(self, name):
        rels = self.get_relationships()
        if "snapshots" not in rels: rels["snapshots"] = []
        
        # Capture current links
        current_links = [dict(l) for l in rels.get("relationship_links", [])]
        
        snapshot = {
            "name": name,
            "links": current_links,
            "timestamp": time.time()
        }
        rels["snapshots"].append(snapshot)
        self.mark_modified("relationships")
        return len(rels["snapshots"]) - 1

    def delete_relationship_snapshot(self, index):
        rels = self.get_relationships()
        snapshots = rels.get("snapshots", [])
        if 0 <= index < len(snapshots):
            del snapshots[index]
            self.mark_modified("relationships")
            return True
        return False

    def update_relationship_snapshot(self, index, name=None):
        rels = self.get_relationships()
        snapshots = rels.get("snapshots", [])
        if 0 <= index < len(snapshots):
            if name: snapshots[index]["name"] = name
            self.mark_modified("relationships")
            return True
        return False

    def get_tags_config(self):
        return self.project_data.get("tags", [])

    def get_project_type(self):
        return self.project_data.get("meta", {}).get("type", "General")

    def get_project_length(self):
        return self.project_data.get("meta", {}).get("length", "Long")

    def get_custom_type_name(self) -> str:
        meta = self.project_data.get("meta", {})
        name = meta.get("custom_type_name", "")
        return name if isinstance(name, str) else ""

    def get_project_type_display_name(self) -> str:
        from writer_app.core.project_types import ProjectTypeManager
        return ProjectTypeManager.get_type_display_name(
            self.get_project_type(),
            self.get_custom_type_name()
        )

    def get_genre_tags(self) -> List[str]:
        meta = self.project_data.get("meta", {})
        tags = meta.get("genre_tags", [])
        return list(tags) if isinstance(tags, list) else []

    def get_enabled_tools(self) -> Set[str]:
        meta = self.project_data.get("meta", {})
        tools = meta.get("enabled_tools")
        from writer_app.core.project_types import ProjectTypeManager
        if tools is None:
            return ProjectTypeManager.get_default_tools(
                self.get_project_type(),
                self.get_project_length(),
                self.get_genre_tags()
            )
        enabled = set(tools)
        enabled.update(ProjectTypeManager.get_required_tools())
        return enabled

    def set_enabled_tools(self, tools: List[str]) -> None:
        if "meta" not in self.project_data:
            self.project_data["meta"] = {}

        from writer_app.core.project_types import ProjectTypeManager
        from writer_app.core.module_registry import get_module_info, get_ordered_module_keys

        normalized = []
        seen = set()
        for tool in ProjectTypeManager.REQUIRED_TOOLS:
            if tool not in seen:
                normalized.append(tool)
                seen.add(tool)

        tools_set = set(tools or [])
        for tool in get_ordered_module_keys(visible_only=False):
            if tool in tools_set and tool not in seen:
                normalized.append(tool)
                seen.add(tool)

        for tool in tools or []:
            if tool not in seen:
                normalized.append(tool)
                seen.add(tool)

        self.project_data["meta"]["enabled_tools"] = normalized

        modules_to_ensure = set()
        for tool in normalized:
            info = get_module_info(tool)
            if info:
                modules_to_ensure.update(info.data_modules)

        for module in modules_to_ensure:
            ensure_module_exists(self.project_data, module)

        self.mark_modified("meta")
        get_event_bus().publish(Events.PROJECT_CONFIG_CHANGED, fields=["enabled_tools"])

    def set_genre_tags(self, tags: List[str]) -> None:
        if "meta" not in self.project_data:
            self.project_data["meta"] = {}

        normalized = []
        seen = set()
        for tag in tags or []:
            if tag and tag not in seen:
                normalized.append(tag)
                seen.add(tag)

        self.project_data["meta"]["genre_tags"] = normalized
        self.mark_modified("meta")
        get_event_bus().publish(Events.PROJECT_CONFIG_CHANGED, fields=["genre_tags"])

    def set_custom_type_name(self, name: str) -> None:
        if "meta" not in self.project_data:
            self.project_data["meta"] = {}

        value = (name or "").strip()
        if value:
            self.project_data["meta"]["custom_type_name"] = value
        else:
            self.project_data["meta"].pop("custom_type_name", None)

        self.mark_modified("meta")
        get_event_bus().publish(Events.PROJECT_CONFIG_CHANGED, fields=["custom_type_name"])
    
    def get_kanban_columns(self):
        return self.project_data.get("meta", {}).get("kanban_columns", ["构思", "初稿", "润色", "定稿"])

    def set_kanban_columns(self, columns):
        if "meta" not in self.project_data:
            self.project_data["meta"] = {}
        self.project_data["meta"]["kanban_columns"] = columns
        self.mark_modified("kanban")

    def set_project_type(self, type_key, cleanup_action: str = None):
        """
        Set the project type.

        For simple type changes without data migration, use this method directly.
        For type changes that require data migration, use do_migrate_project_type().

        Args:
            type_key: The new project type key
            cleanup_action: If provided, perform migration with this action ("archive"/"delete")
                           If None, just change the type without data migration
        """
        if "meta" not in self.project_data:
            self.project_data["meta"] = {}

        old_type = self.project_data["meta"].get("type", "General")

        if cleanup_action and old_type != type_key:
            # Use migration system
            self.do_migrate_project_type(type_key, cleanup_action)
        else:
            # Simple type change
            self.project_data["meta"]["type"] = type_key
            # Update outline style when not specified
            current_style = self.project_data["meta"].get("outline_template_style", "default")
            if current_style in ("default", "", None):
                from writer_app.core.project_types import ProjectTypeManager
                self.project_data["meta"]["outline_template_style"] = ProjectTypeManager.get_default_outline_view(type_key)
            self.mark_modified()

        if old_type != type_key:
            get_event_bus().publish(Events.PROJECT_TYPE_CHANGED, old_type=old_type, new_type=type_key)
            get_event_bus().publish(Events.PROJECT_CONFIG_CHANGED, fields=["type"])

    def get_outline_template_style(self):
        return self.project_data.get("meta", {}).get("outline_template_style", "default")

    def set_outline_template_style(self, style_key):
        if "meta" not in self.project_data:
            self.project_data["meta"] = {}
        self.project_data["meta"]["outline_template_style"] = style_key
        self.mark_modified("style")

    def set_project_length(self, length_key):
        if "meta" not in self.project_data:
            self.project_data["meta"] = {}
        old_length = self.project_data["meta"].get("length")
        self.project_data["meta"]["length"] = length_key
        self.mark_modified()
        if old_length != length_key:
            get_event_bus().publish(Events.PROJECT_CONFIG_CHANGED, fields=["length"])

    def get_wiki_categories(self) -> List[str]:
        """
        获取当前项目的百科分类列表。
        优先使用项目自定义分类，否则使用项目类型默认分类。
        """
        # 先检查项目自定义分类
        custom_categories = self.project_data.get("meta", {}).get("custom_wiki_categories")
        if custom_categories:
            return custom_categories

        # 使用项目类型默认分类
        from writer_app.core.project_types import ProjectTypeManager
        project_type = self.get_project_type()
        return ProjectTypeManager.get_wiki_categories(project_type)

    def set_wiki_categories(self, categories: List[str]):
        """设置项目自定义百科分类。"""
        if "meta" not in self.project_data:
            self.project_data["meta"] = {}
        self.project_data["meta"]["custom_wiki_categories"] = categories
        self.mark_modified("wiki")
        get_event_bus().publish(Events.PROJECT_CONFIG_CHANGED, fields=["wiki_categories"])

    def reset_wiki_categories(self):
        """重置为项目类型默认的百科分类。"""
        if "meta" in self.project_data and "custom_wiki_categories" in self.project_data["meta"]:
            del self.project_data["meta"]["custom_wiki_categories"]
            self.mark_modified("wiki")
            get_event_bus().publish(Events.PROJECT_CONFIG_CHANGED, fields=["wiki_categories"])

    def get_asset_types(self) -> List[str]:
        """获取当前项目的资源类型列表。"""
        from writer_app.core.project_types import ProjectTypeManager
        project_type = self.get_project_type()
        return ProjectTypeManager.get_asset_types(project_type)

    # --- Helpers ---
    def _gen_uid(self) -> str:
        """生成唯一标识符。"""
        return uuid.uuid4().hex

    def _ensure_outline_uids_iterative(self, root: dict) -> None:
        """使用迭代算法确保每个大纲节点都有稳定的 UID。"""
        if root is None:
            return

        stack = [root]
        while stack:
            node = stack.pop()
            if "uid" not in node or not node["uid"]:
                node["uid"] = self._gen_uid()
            # 将子节点加入栈
            for child in node.get("children", []):
                stack.append(child)

    # 保留原方法名以兼容旧代码
    def _ensure_outline_uids(self, node):
        """兼容性别名 -> _ensure_outline_uids_iterative。"""
        self._ensure_outline_uids_iterative(node)

    # --- Outline Node Helpers (used by commands) ---
    def find_node_by_uid(self, root: dict, target_uid: str) -> Optional[dict]:
        """
        使用迭代算法在大纲中查找指定 UID 的节点。

        Args:
            root: 大纲根节点
            target_uid: 目标节点的 UID

        Returns:
            找到的节点，或 None
        """
        if root is None or not target_uid:
            return None

        stack = [root]
        while stack:
            node = stack.pop()
            if node.get("uid") == target_uid:
                return node
            # 将子节点加入栈
            for child in node.get("children", []):
                stack.append(child)
        return None

    def find_parent_of_node_by_uid(self, root: dict, target_node_uid: str) -> Optional[dict]:
        """
        使用迭代算法查找目标节点的父节点。

        Args:
            root: 大纲根节点
            target_node_uid: 目标节点的 UID

        Returns:
            父节点，或 None
        """
        if root is None or not target_node_uid:
            return None

        stack = [root]
        while stack:
            node = stack.pop()
            for child in node.get("children", []):
                if child.get("uid") == target_node_uid:
                    return node
                stack.append(child)
        return None

    # --- Bidirectional Navigation Helpers ---

    def get_scenes_by_outline_uid(self, outline_uid):
        """
        Get all scenes linked to a specific outline node.

        Args:
            outline_uid: UID of the outline node

        Returns:
            List of (scene_index, scene_data) tuples
        """
        result = []
        for i, scene in enumerate(self.get_scenes()):
            if scene.get("outline_ref_id") == outline_uid:
                result.append((i, scene))
        return result

    def get_outline_node_for_scene(self, scene_index):
        """
        Get the outline node linked to a specific scene.

        Args:
            scene_index: Index of the scene in the scenes list

        Returns:
            Outline node dict or None if not linked
        """
        scenes = self.get_scenes()
        if 0 <= scene_index < len(scenes):
            scene = scenes[scene_index]
            outline_uid = scene.get("outline_ref_id")
            if outline_uid:
                return self.find_node_by_uid(self.get_outline(), outline_uid)
        return None

    def get_outline_scene_links(self):
        """
        Get a mapping of outline UIDs to their linked scene indices.

        Returns:
            Dict mapping outline_uid -> list of scene indices
        """
        links = {}
        for i, scene in enumerate(self.get_scenes()):
            outline_uid = scene.get("outline_ref_id")
            if outline_uid:
                if outline_uid not in links:
                    links[outline_uid] = []
                links[outline_uid].append(i)
        return links

    def link_scene_to_outline(self, scene_index, outline_uid):
        """
        Link a scene to an outline node.

        Args:
            scene_index: Index of the scene
            outline_uid: UID of the outline node to link to

        Returns:
            True if successful
        """
        scenes = self.get_scenes()
        if 0 <= scene_index < len(scenes):
            outline_node = self.find_node_by_uid(self.get_outline(), outline_uid)
            if outline_node:
                scenes[scene_index]["outline_ref_id"] = outline_uid
                scenes[scene_index]["outline_ref_path"] = self.get_outline_path(outline_uid)
                self.mark_modified()
                return True
        return False

    def unlink_scene_from_outline(self, scene_index):
        """
        Remove the outline link from a scene.

        Args:
            scene_index: Index of the scene

        Returns:
            True if successful
        """
        scenes = self.get_scenes()
        if 0 <= scene_index < len(scenes):
            scenes[scene_index]["outline_ref_id"] = ""
            scenes[scene_index]["outline_ref_path"] = ""
            self.mark_modified()
            return True
        return False

    def get_outline_path(self, target_uid: str, separator: str = " / ") -> str:
        """
        使用迭代算法获取大纲节点的路径字符串（如 "根节点 / 第一章 / 场景A"）。

        Args:
            target_uid: 目标节点的 UID
            separator: 路径分隔符

        Returns:
            路径字符串，如果未找到则返回空字符串
        """
        if not target_uid:
            return ""

        root = self.get_outline()
        if root is None:
            return ""

        # 使用栈来跟踪路径: (节点, 路径列表)
        stack = [(root, [])]

        while stack:
            node, path = stack.pop()
            current_path = path + [node.get("name", "")]

            if node.get("uid") == target_uid:
                return separator.join(current_path)

            # 将子节点加入栈（反向添加以保持顺序）
            for child in reversed(node.get("children", [])):
                stack.append((child, current_path))

        return ""

    def get_characters_in_scene(self, scene_index):
        """
        Get list of character names that appear in a scene.

        Args:
            scene_index: Index of the scene

        Returns:
            List of character names
        """
        scenes = self.get_scenes()
        if 0 <= scene_index < len(scenes):
            return scenes[scene_index].get("characters", [])
        return []

    def get_scenes_with_character(self, character_name):
        """
        Get all scenes where a character appears.

        Args:
            character_name: Name of the character

        Returns:
            List of (scene_index, scene_data) tuples
        """
        result = []
        for i, scene in enumerate(self.get_scenes()):
            if character_name in scene.get("characters", []):
                result.append((i, scene))
        return result

    def get_scenes_with_character_pair(self, char_a, char_b):
        """
        Get all scenes where BOTH characters appear.
        
        Args:
            char_a: Name of character A
            char_b: Name of character B
            
        Returns:
            List of (scene_index, scene_data) tuples
        """
        result = []
        for i, scene in enumerate(self.get_scenes()):
            chars = scene.get("characters", [])
            if char_a in chars and char_b in chars:
                result.append((i, scene))
        return result

    def get_character_scene_matrix(self):
        """
        Get a matrix showing which characters appear in which scenes.

        Returns:
            Dict with structure: {character_name: [scene_indices]}
        """
        matrix = {}
        for char in self.get_characters():
            name = char.get("name")
            if name:
                matrix[name] = []

        for i, scene in enumerate(self.get_scenes()):
            for char_name in scene.get("characters", []):
                if char_name in matrix:
                    matrix[char_name].append(i)

        return matrix

    def get_scenes_containing_text(self, query):
        """
        Find all scenes that contain the given text in their content or name.

        Args:
            query: Text to search for

        Returns:
            List of (scene_index, scene_data) tuples
        """
        if not query:
            return []
        
        query_lower = query.lower()
        result = []
        for i, scene in enumerate(self.get_scenes()):
            name = scene.get("name", "").lower()
            content = scene.get("content", "").lower()
            if query_lower in name or query_lower in content:
                result.append((i, scene))
        return result

    def auto_generate_relationships(self, threshold=1):
        """
        Scan all scenes and create links between characters that appear together.
        
        Args:
            threshold: Minimum number of co-occurrences to create a link.
            
        Returns:
            Number of new links created.
        """
        matrix = {} # (char_a, char_b) -> count
        
        # 1. Count co-occurrences
        for scene in self.get_scenes():
            chars = sorted(list(set(scene.get("characters", [])))) # unique and sorted
            for i in range(len(chars)):
                for j in range(i+1, len(chars)):
                    pair = (chars[i], chars[j])
                    matrix[pair] = matrix.get(pair, 0) + 1
                    
        # 2. Add links
        rels = self.get_relationships()
        existing_links = set()
        for link in rels.get("relationship_links", []):
            # Sort to ignore direction for existence check
            pair = tuple(sorted([link["source"], link["target"]]))
            existing_links.add(pair)
            
        added_count = 0
        for pair, count in matrix.items():
            if count >= threshold:
                if pair not in existing_links:
                    new_link = {
                        "source": pair[0],
                        "target": pair[1],
                        "label": f"共现 {count} 次",
                        "color": "#666666"
                    }
                    rels["relationship_links"].append(new_link)
                    existing_links.add(pair)
                    added_count += 1
        
        if added_count > 0:
            self.mark_modified("relationships")
            
        return added_count

    def search_all(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        全局搜索项目所有数据。

        Args:
            query: 搜索文本
            case_sensitive: 是否区分大小写

        Returns:
            搜索结果列表，每个结果包含:
            {
                "type": "scene"|"character"|"wiki"|"outline",
                "index": 索引或 UID,
                "name": 显示名称,
                "context": 预览文本,
                "match_field": 匹配的字段名
            }
        """
        if not query:
            return []

        results = []
        q = query if case_sensitive else query.lower()

        def check(text: str) -> bool:
            return q in (text if case_sensitive else text.lower())

        def get_context(content: str, match_query: str) -> str:
            """获取匹配上下文。"""
            idx = content.find(match_query) if case_sensitive else content.lower().find(q)
            start = max(0, idx - 10)
            end = min(len(content), idx + 20)
            return content[start:end].replace("\n", " ") + "..."

        # 1. 搜索场景
        for i, scene in enumerate(self.get_scenes()):
            name = scene.get("name", "")
            content = scene.get("content", "")
            if check(name):
                results.append({"type": "scene", "index": i, "name": name, "context": "(标题匹配)", "match_field": "name"})
            elif check(content):
                results.append({"type": "scene", "index": i, "name": name, "context": get_context(content, query), "match_field": "content"})

        # 2. 搜索角色
        for i, char in enumerate(self.get_characters()):
            name = char.get("name", "")
            desc = char.get("description", "")
            if check(name):
                results.append({"type": "character", "index": i, "name": name, "context": "(姓名匹配)", "match_field": "name"})
            elif check(desc):
                results.append({"type": "character", "index": i, "name": name, "context": desc[:30] + "...", "match_field": "description"})

        # 3. 搜索百科
        for i, entry in enumerate(self.get_world_entries()):
            name = entry.get("name", "")
            content = entry.get("content", "")
            if check(name):
                results.append({"type": "wiki", "index": i, "name": name, "context": "(词条名匹配)", "match_field": "name"})
            elif check(content):
                results.append({"type": "wiki", "index": i, "name": name, "context": get_context(content, query), "match_field": "content"})

        # 4. 搜索大纲（使用迭代算法）
        root = self.get_outline()
        if root:
            stack = [root]
            while stack:
                node = stack.pop()
                uid = node.get("uid")
                name = node.get("name", "")
                content = node.get("content", "")

                if check(name):
                    results.append({"type": "outline", "index": uid, "name": name, "context": "(节点名匹配)", "match_field": "name"})
                elif check(content):
                    results.append({"type": "outline", "index": uid, "name": name, "context": get_context(content, query), "match_field": "content"})

                # 将子节点加入栈
                for child in node.get("children", []):
                    stack.append(child)

        return results

    # --- Galgame Assets Helpers ---
    def get_galgame_assets(self):
        """Get list of all Galgame assets (sprites, backgrounds, CGs, UI)."""
        if "galgame_assets" not in self.project_data:
            self.project_data["galgame_assets"] = []
        return self.project_data["galgame_assets"]

    def add_galgame_asset(self, asset):
        """
        Add a new Galgame asset.

        Args:
            asset: Dict with keys: uid, name, type (sprite/background/cg/ui),
                   path, character, expression, tags
        """
        if "galgame_assets" not in self.project_data:
            self.project_data["galgame_assets"] = []

        # Ensure uid
        if "uid" not in asset or not asset["uid"]:
            asset["uid"] = self._gen_uid()

        self.project_data["galgame_assets"].append(asset)
        self.mark_modified("galgame_assets")
        return asset["uid"]

    def update_galgame_asset(self, uid, updated_data):
        """
        Update an existing Galgame asset.

        Args:
            uid: UID of the asset to update
            updated_data: Dict with updated fields
        """
        assets = self.get_galgame_assets()
        for i, asset in enumerate(assets):
            if asset.get("uid") == uid:
                assets[i].update(updated_data)
                self.mark_modified("galgame_assets")
                return True
        return False

    def delete_galgame_asset(self, uid):
        """
        Delete a Galgame asset by UID.

        Args:
            uid: UID of the asset to delete
        """
        assets = self.get_galgame_assets()
        for i, asset in enumerate(assets):
            if asset.get("uid") == uid:
                del assets[i]
                self.mark_modified("galgame_assets")
                return True
        return False

    def get_galgame_assets_by_type(self, asset_type):
        """
        Get Galgame assets filtered by type.

        Args:
            asset_type: One of "sprite", "background", "cg", "ui"

        Returns:
            List of matching assets
        """
        return [a for a in self.get_galgame_assets() if a.get("type") == asset_type]

    def get_galgame_assets_by_character(self, character_name):
        """
        Get all assets associated with a specific character.

        Args:
            character_name: Name of the character

        Returns:
            List of matching assets
        """
        return [a for a in self.get_galgame_assets() if a.get("character") == character_name]

    def get_character_sprites(self, character_name):
        """
        Get all sprite assets for a character, organized by expression.

        Args:
            character_name: Name of the character

        Returns:
            Dict mapping expression -> asset
        """
        sprites = {}
        for asset in self.get_galgame_assets():
            if asset.get("type") == "sprite" and asset.get("character") == character_name:
                expr = asset.get("expression", "default")
                sprites[expr] = asset
        return sprites

    # --- Research Helpers ---
    def get_research_items(self):
        return self.project_data.get("research", [])

    def add_research_item(self, title, content, source_url="", tags=None):
        if tags is None: tags = []
        item = {
            "uid": self._gen_uid(),
            "title": title,
            "content": content,
            "source_url": source_url,
            "tags": tags,
            "created_at": "" # Should use datetime
        }
        if "research" not in self.project_data:
            self.project_data["research"] = []
        self.project_data["research"].insert(0, item)
        self.mark_modified("research")
        return item

    def update_research_item(self, uid, updated_data):
        items = self.get_research_items()
        for i, item in enumerate(items):
            if item.get("uid") == uid:
                items[i].update(updated_data)
                self.mark_modified("research")
                return True
        return False

    def delete_research_item(self, uid):
        items = self.get_research_items()
        for i, item in enumerate(items):
            if item.get("uid") == uid:
                del items[i]
                self.mark_modified("research")
                return True
        return False
