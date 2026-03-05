from typing import Dict

from writer_app.core.typed_data import DataModule
from writer_app.core.module_registry import MODULES


def _count_outline_nodes(outline: dict) -> int:
    if not outline:
        return 0
    count = 0
    stack = list(outline.get("children", []))
    while stack:
        node = stack.pop()
        count += 1
        stack.extend(node.get("children", []))
    return count


def _count_script_items(script: dict) -> int:
    if not script:
        return 0
    return len(script.get("scenes", [])) + len(script.get("characters", []))


def _count_relationship_items(relationships: dict) -> int:
    if not relationships:
        return 0
    return (
        len(relationships.get("nodes", []))
        + len(relationships.get("links", []))
        + len(relationships.get("relationship_links", []))
        + len(relationships.get("evidence_links", []))
    )


def get_data_module_counts(project_data: dict) -> Dict[DataModule, int]:
    counts: Dict[DataModule, int] = {
        DataModule.OUTLINE: _count_outline_nodes(project_data.get("outline", {})),
        DataModule.SCRIPT: _count_script_items(project_data.get("script", {})),
        DataModule.WORLD: len(project_data.get("world", {}).get("entries", [])),
        DataModule.RELATIONSHIPS: _count_relationship_items(project_data.get("relationships", {})),
        DataModule.TAGS: len(project_data.get("tags", [])),
        DataModule.RESEARCH: len(project_data.get("research", [])),
        DataModule.IDEAS: len(project_data.get("ideas", [])),
        DataModule.TIMELINES: (
            len(project_data.get("timelines", {}).get("truth_events", []))
            + len(project_data.get("timelines", {}).get("lie_events", []))
        ),
        DataModule.FACTIONS: len(project_data.get("factions", {}).get("groups", [])),
        DataModule.VARIABLES: len(project_data.get("variables", [])),
        DataModule.GALGAME_ASSETS: len(project_data.get("galgame_assets", [])),
        DataModule.HEARTBEAT: (
            len(project_data.get("heartbeat_data", {}).get("tension_history", []))
            + len(project_data.get("heartbeat_data", {}).get("emotional_beats", []))
        ),
        DataModule.EVIDENCE: (
            len(project_data.get("evidence_data", {}).get("clues", []))
            + len(project_data.get("evidence_data", {}).get("connections", []))
            + len(project_data.get("evidence_data", {}).get("reveals", []))
        ),
    }
    return counts


def get_module_usage_counts(project_data: dict) -> Dict[str, int]:
    data_counts = get_data_module_counts(project_data)
    module_counts: Dict[str, int] = {}

    for key, info in MODULES.items():
        total = 0
        for module in info.data_modules:
            total += data_counts.get(module, 0)
        module_counts[key] = total

    return module_counts
