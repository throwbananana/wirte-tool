"""
Typed project data schemas - defines modular data structures per project type.

This module provides:
1. DataModule enum for all possible data modules
2. TYPE_MODULE_MAP mapping project types to required modules
3. MODULE_SCHEMAS for each module's default structure
4. Helper functions for module management
"""
from enum import Enum
from typing import Dict, Set, List, Any, Callable
from dataclasses import dataclass, field


class DataModule(Enum):
    """Available data modules that can be conditionally loaded."""
    # Core modules (always present)
    OUTLINE = "outline"
    SCRIPT = "script"

    # Common optional modules
    WORLD = "world"
    RELATIONSHIPS = "relationships"
    TAGS = "tags"
    RESEARCH = "research"
    IDEAS = "ideas"

    # Type-specific modules
    TIMELINES = "timelines"           # Suspense: truth/lie events
    FACTIONS = "factions"             # SciFi/Epic: faction matrix
    VARIABLES = "variables"           # Galgame: game state variables
    GALGAME_ASSETS = "galgame_assets" # Galgame/LightNovel: sprites, CGs
    HEARTBEAT = "heartbeat_data"      # Romance: emotion tracking
    EVIDENCE = "evidence_data"        # Suspense: clue board specific data


@dataclass
class ModuleSchema:
    """Defines default structure and cleanup behavior for a data module."""
    key: str
    default_factory: Callable[[], Any]
    cleanup_fields: List[str] = field(default_factory=list)
    description: str = ""


# Module schemas define the default structure for each module
MODULE_SCHEMAS: Dict[DataModule, ModuleSchema] = {
    DataModule.OUTLINE: ModuleSchema(
        key="outline",
        default_factory=lambda: {"name": "项目大纲", "children": [], "uid": "", "flat_draft": []},
        cleanup_fields=[],
        description="项目大纲结构"
    ),
    DataModule.SCRIPT: ModuleSchema(
        key="script",
        default_factory=lambda: {
            "title": "未命名剧本",
            "characters": [],
            "scenes": []
        },
        cleanup_fields=[],
        description="剧本内容（角色、场景）"
    ),
    DataModule.WORLD: ModuleSchema(
        key="world",
        default_factory=lambda: {"entries": []},
        cleanup_fields=["entries"],
        description="世界观百科"
    ),
    DataModule.RELATIONSHIPS: ModuleSchema(
        key="relationships",
        default_factory=lambda: {
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
        cleanup_fields=["relationship_links", "evidence_links", "nodes", "snapshots"],
        description="角色关系和证据连线"
    ),
    DataModule.TAGS: ModuleSchema(
        key="tags",
        default_factory=lambda: [],
        cleanup_fields=[],
        description="标签系统"
    ),
    DataModule.RESEARCH: ModuleSchema(
        key="research",
        default_factory=lambda: [],
        cleanup_fields=[],
        description="研究资料"
    ),
    DataModule.IDEAS: ModuleSchema(
        key="ideas",
        default_factory=lambda: [],
        cleanup_fields=[],
        description="灵感收集"
    ),
    DataModule.TIMELINES: ModuleSchema(
        key="timelines",
        default_factory=lambda: {
            "truth_events": [],
            "lie_events": []
        },
        cleanup_fields=["truth_events", "lie_events"],
        description="悬疑时间线（真相 vs 叙述）"
    ),
    DataModule.FACTIONS: ModuleSchema(
        key="factions",
        default_factory=lambda: {
            "groups": [],
            "matrix": {}
        },
        cleanup_fields=["groups", "matrix"],
        description="势力阵营和关系矩阵"
    ),
    DataModule.VARIABLES: ModuleSchema(
        key="variables",
        default_factory=lambda: [],
        cleanup_fields=[],
        description="游戏状态变量（Galgame 分支）"
    ),
    DataModule.GALGAME_ASSETS: ModuleSchema(
        key="galgame_assets",
        default_factory=lambda: [],
        cleanup_fields=[],
        description="游戏资源（立绘、背景、CG）"
    ),
    DataModule.HEARTBEAT: ModuleSchema(
        key="heartbeat_data",
        default_factory=lambda: {
            "tension_history": [],
            "emotional_beats": []
        },
        cleanup_fields=["tension_history", "emotional_beats"],
        description="情感节奏追踪（言情）"
    ),
    DataModule.EVIDENCE: ModuleSchema(
        key="evidence_data",
        default_factory=lambda: {
            "clues": [],
            "connections": [],
            "reveals": []
        },
        cleanup_fields=["clues", "connections", "reveals"],
        description="证据板专用数据（悬疑）"
    ),
}


# Core modules that are always present regardless of project type
CORE_MODULES: Set[DataModule] = {
    DataModule.OUTLINE,
    DataModule.SCRIPT,
    DataModule.TAGS,
    DataModule.RESEARCH,
    DataModule.IDEAS,
}


# Type-to-modules mapping - defines which modules each project type needs
TYPE_MODULE_MAP: Dict[str, Set[DataModule]] = {
    "General": CORE_MODULES | {
        DataModule.WORLD,
        DataModule.RELATIONSHIPS,
    },
    "Suspense": CORE_MODULES | {
        DataModule.WORLD,
        DataModule.RELATIONSHIPS,
        DataModule.TIMELINES,
        DataModule.EVIDENCE,
    },
    "Romance": CORE_MODULES | {
        DataModule.WORLD,
        DataModule.RELATIONSHIPS,
        DataModule.HEARTBEAT,
    },
    "Epic": CORE_MODULES | {
        DataModule.WORLD,
        DataModule.RELATIONSHIPS,
        DataModule.FACTIONS,
    },
    "SciFi": CORE_MODULES | {
        DataModule.WORLD,
        DataModule.RELATIONSHIPS,
        DataModule.FACTIONS,
    },
    "Poetry": CORE_MODULES,  # Minimal - just core modules
    "LightNovel": CORE_MODULES | {
        DataModule.WORLD,
        DataModule.RELATIONSHIPS,
        DataModule.GALGAME_ASSETS,
    },
    "Galgame": CORE_MODULES | {
        DataModule.WORLD,
        DataModule.RELATIONSHIPS,
        DataModule.VARIABLES,
        DataModule.GALGAME_ASSETS,
    },
}


def get_required_modules(project_type: str) -> Set[DataModule]:
    """
    Get modules required for a project type.

    Args:
        project_type: The project type key (e.g., "Suspense", "Romance")

    Returns:
        Set of DataModule enums required for this type
    """
    return TYPE_MODULE_MAP.get(project_type, TYPE_MODULE_MAP["General"])


def get_optional_modules(project_type: str) -> Set[DataModule]:
    """
    Get modules that are NOT required for a project type.

    Args:
        project_type: The project type key

    Returns:
        Set of DataModule enums not used by this type
    """
    all_modules = set(DataModule)
    required = get_required_modules(project_type)
    return all_modules - required


def get_incompatible_modules(old_type: str, new_type: str) -> Set[DataModule]:
    """
    Get modules that exist in old_type but not in new_type.
    These are candidates for cleanup/archival when switching types.

    Args:
        old_type: Current project type
        new_type: Target project type

    Returns:
        Set of DataModule enums that will become unused
    """
    old_modules = get_required_modules(old_type)
    new_modules = get_required_modules(new_type)
    return old_modules - new_modules


def get_new_modules(old_type: str, new_type: str) -> Set[DataModule]:
    """
    Get modules that will be added when switching from old_type to new_type.

    Args:
        old_type: Current project type
        new_type: Target project type

    Returns:
        Set of DataModule enums that will be newly added
    """
    old_modules = get_required_modules(old_type)
    new_modules = get_required_modules(new_type)
    return new_modules - old_modules


def get_module_schema(module: DataModule) -> ModuleSchema:
    """
    Get the schema for a specific module.

    Args:
        module: The DataModule enum

    Returns:
        ModuleSchema with default factory and cleanup info
    """
    return MODULE_SCHEMAS.get(module)


def get_module_key(module: DataModule) -> str:
    """
    Get the JSON key name for a module.

    Args:
        module: The DataModule enum

    Returns:
        String key used in project_data dict
    """
    schema = get_module_schema(module)
    return schema.key if schema else module.value


def create_module_data(module: DataModule) -> Any:
    """
    Create default data structure for a module.

    Args:
        module: The DataModule enum

    Returns:
        Default data structure for this module
    """
    schema = get_module_schema(module)
    if schema:
        return schema.default_factory()
    return None


def get_modules_with_data(project_data: Dict) -> Set[DataModule]:
    """
    Determine which modules have non-empty data in a project.

    Args:
        project_data: The project data dictionary

    Returns:
        Set of DataModule enums that have actual data
    """
    result = set()

    for module in DataModule:
        schema = get_module_schema(module)
        if not schema:
            continue

        key = schema.key
        data = project_data.get(key)

        if data is None:
            continue

        # Check if data is non-empty
        if isinstance(data, dict):
            # For dicts, check if any cleanup fields have data
            has_data = False
            if schema.cleanup_fields:
                for field in schema.cleanup_fields:
                    field_data = data.get(field)
                    if field_data and (isinstance(field_data, list) and len(field_data) > 0):
                        has_data = True
                        break
                    elif field_data and isinstance(field_data, dict) and len(field_data) > 0:
                        has_data = True
                        break
            else:
                # No cleanup fields - check if dict has any meaningful content
                has_data = len(data) > 0

            if has_data:
                result.add(module)

        elif isinstance(data, list):
            if len(data) > 0:
                result.add(module)

    return result


def get_cleanup_info(old_type: str, new_type: str, project_data: Dict) -> List[Dict[str, Any]]:
    """
    Get detailed cleanup information when switching project types.

    Args:
        old_type: Current project type
        new_type: Target project type
        project_data: Current project data

    Returns:
        List of dicts with module info and data counts for user confirmation
    """
    incompatible = get_incompatible_modules(old_type, new_type)
    modules_with_data = get_modules_with_data(project_data)

    # Only report modules that actually have data
    affected = incompatible & modules_with_data

    result = []
    for module in affected:
        schema = get_module_schema(module)
        key = schema.key
        data = project_data.get(key)

        # Count items
        item_count = 0
        if isinstance(data, list):
            item_count = len(data)
        elif isinstance(data, dict):
            for field in schema.cleanup_fields:
                field_data = data.get(field)
                if isinstance(field_data, list):
                    item_count += len(field_data)
                elif isinstance(field_data, dict):
                    item_count += len(field_data)

        result.append({
            "module": module,
            "key": key,
            "description": schema.description,
            "item_count": item_count
        })

    return result


def archive_module_data(project_data: Dict, module: DataModule) -> None:
    """
    Archive a module's data by moving it to _archived_xxx key.

    Args:
        project_data: The project data dictionary (modified in place)
        module: The module to archive
    """
    schema = get_module_schema(module)
    if not schema:
        return

    key = schema.key
    if key in project_data:
        archived_key = f"_archived_{key}"
        project_data[archived_key] = project_data.pop(key)


def restore_archived_module(project_data: Dict, module: DataModule) -> bool:
    """
    Restore a module from archived state.

    Args:
        project_data: The project data dictionary (modified in place)
        module: The module to restore

    Returns:
        True if restored, False if no archive found
    """
    schema = get_module_schema(module)
    if not schema:
        return False

    key = schema.key
    archived_key = f"_archived_{key}"

    if archived_key in project_data:
        project_data[key] = project_data.pop(archived_key)
        return True
    return False


def delete_module_data(project_data: Dict, module: DataModule) -> None:
    """
    Permanently delete a module's data.

    Args:
        project_data: The project data dictionary (modified in place)
        module: The module to delete
    """
    schema = get_module_schema(module)
    if not schema:
        return

    key = schema.key
    if key in project_data:
        del project_data[key]


def ensure_module_exists(project_data: Dict, module: DataModule) -> None:
    """
    Ensure a module exists in project data, creating it if necessary.

    Args:
        project_data: The project data dictionary (modified in place)
        module: The module to ensure exists
    """
    schema = get_module_schema(module)
    if not schema:
        return

    key = schema.key

    # First check if there's archived data to restore
    archived_key = f"_archived_{key}"
    if archived_key in project_data:
        project_data[key] = project_data.pop(archived_key)
        return

    # Create new if doesn't exist
    if key not in project_data:
        project_data[key] = schema.default_factory()


def create_typed_project_data(project_type: str, uid_generator: Callable[[], str]) -> Dict:
    """
    Create a new project data structure with only the modules needed for the type.

    Args:
        project_type: The project type key
        uid_generator: Function to generate UIDs

    Returns:
        New project data dictionary with type-appropriate modules
    """
    required_modules = get_required_modules(project_type)

    # Always include meta
    project_data = {
        "meta": {
            "type": project_type,
            "length": "Long",
            "outline_template_style": "default",
            "created_at": "",
            "version": "1.0",
            "kanban_columns": ["构思", "初稿", "润色", "定稿"]
        }
    }

    # Add required modules
    for module in required_modules:
        schema = get_module_schema(module)
        if schema:
            data = schema.default_factory()
            # Special handling for outline UID
            if module == DataModule.OUTLINE and isinstance(data, dict):
                data["uid"] = uid_generator()
            project_data[schema.key] = data

    return project_data


def migrate_project_type(
    project_data: Dict,
    old_type: str,
    new_type: str,
    cleanup_action: str = "archive",
    uid_generator: Callable[[], str] = None
) -> Dict[str, Any]:
    """
    Migrate project data from one type to another.

    Args:
        project_data: The project data dictionary (modified in place)
        old_type: Current project type
        new_type: Target project type
        cleanup_action: "archive" to keep data, "delete" to remove
        uid_generator: Function to generate UIDs for new modules

    Returns:
        Dict with migration summary:
        {
            "archived": List of archived module keys,
            "deleted": List of deleted module keys,
            "added": List of newly added module keys,
            "restored": List of restored from archive module keys
        }
    """
    result = {
        "archived": [],
        "deleted": [],
        "added": [],
        "restored": []
    }

    # Handle incompatible modules
    incompatible = get_incompatible_modules(old_type, new_type)
    for module in incompatible:
        schema = get_module_schema(module)
        if not schema:
            continue

        key = schema.key
        if key in project_data:
            if cleanup_action == "archive":
                archive_module_data(project_data, module)
                result["archived"].append(key)
            elif cleanup_action == "delete":
                delete_module_data(project_data, module)
                result["deleted"].append(key)

    # Handle new modules
    new_modules = get_new_modules(old_type, new_type)
    for module in new_modules:
        schema = get_module_schema(module)
        if not schema:
            continue

        key = schema.key
        archived_key = f"_archived_{key}"

        if archived_key in project_data:
            # Restore from archive
            restore_archived_module(project_data, module)
            result["restored"].append(key)
        elif key not in project_data:
            # Create new
            data = schema.default_factory()
            if module == DataModule.OUTLINE and isinstance(data, dict) and uid_generator:
                data["uid"] = uid_generator()
            project_data[key] = data
            result["added"].append(key)

    # Update meta type
    if "meta" not in project_data:
        project_data["meta"] = {}
    project_data["meta"]["type"] = new_type

    return result
