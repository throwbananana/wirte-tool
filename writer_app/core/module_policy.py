from typing import Iterable, List, Optional, Set, TYPE_CHECKING

from writer_app.core.module_registry import get_module_info, get_ordered_module_keys
from writer_app.core.project_types import ProjectTypeManager

if TYPE_CHECKING:
    from writer_app.core.typed_data import DataModule


def normalize_tool_keys(tool_keys: Iterable[str]) -> List[str]:
    """Deduplicate tool keys while preserving registry order when possible."""
    requested = [key for key in (tool_keys or []) if key]
    requested_set = set(requested)
    ordered: List[str] = []
    seen = set()

    for key in get_ordered_module_keys(visible_only=False):
        if key in requested_set and key not in seen:
            ordered.append(key)
            seen.add(key)

    for key in requested:
        if key not in seen:
            ordered.append(key)
            seen.add(key)

    return ordered


def get_recommended_tools_for_type(
    type_key: str,
    length_key: str = "Long",
    tags: Optional[Iterable[str]] = None,
) -> List[str]:
    return ProjectTypeManager.get_default_tools_list(type_key, length_key, tags)


def get_required_modules_for_tools(tool_keys: Iterable[str]) -> Set["DataModule"]:
    from writer_app.core.typed_data import CORE_MODULES

    modules = set(CORE_MODULES)
    for key in normalize_tool_keys(tool_keys):
        info = get_module_info(key)
        if info:
            modules.update(info.data_modules)
    return modules


def get_required_modules_for_type(
    type_key: str,
    length_key: str = "Long",
    tags: Optional[Iterable[str]] = None,
) -> Set["DataModule"]:
    tool_keys = get_recommended_tools_for_type(type_key, length_key, tags)
    return get_required_modules_for_tools(tool_keys)


def build_type_module_map(type_keys: Optional[Iterable[str]] = None) -> dict[str, Set["DataModule"]]:
    if type_keys is None:
        type_keys = ProjectTypeManager.get_available_types()
    return {
        type_key: get_required_modules_for_type(type_key)
        for type_key in type_keys
    }
