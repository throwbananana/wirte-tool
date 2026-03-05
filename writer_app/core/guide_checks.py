from typing import Tuple


def check_project_saved(app) -> Tuple[bool, str]:
    if app.project_manager.current_file:
        return True, "已检测到项目文件。"
    return False, "请先新建或保存一个项目文件。"


def check_outline_added(app) -> Tuple[bool, str]:
    outline = app.project_manager.get_outline() or {}
    if outline.get("children"):
        return True, "已检测到大纲节点。"
    return False, "请在大纲中新增至少一个节点。"


def check_scene_written(app) -> Tuple[bool, str]:
    scenes = app.project_manager.get_scenes() or []
    for scene in scenes:
        if scene.get("content", "").strip():
            return True, "已检测到有内容的场景。"
    return False, "请在剧本写作中新增场景并填写内容。"


def check_timeline_added(app) -> Tuple[bool, str]:
    timelines = app.project_manager.project_data.get("timelines", {})
    truth_events = timelines.get("truth_events", []) or []
    lie_events = timelines.get("lie_events", []) or []
    if truth_events or lie_events:
        return True, "已检测到时间线事件。"
    return False, "请在时间轴中新增至少一个事件。"

def check_dual_timeline_added(app) -> Tuple[bool, str]:
    timelines = app.project_manager.project_data.get("timelines", {})
    truth_events = timelines.get("truth_events", []) or []
    lie_events = timelines.get("lie_events", []) or []
    if truth_events and lie_events:
        return True, "已检测到双轨时间线事件。"
    return False, "请在双轨时间线中新增真相/叙述事件。"


def check_evidence_added(app) -> Tuple[bool, str]:
    rels = app.project_manager.get_relationships()
    nodes = rels.get("nodes", []) or []
    links = rels.get("evidence_links", []) or []
    if nodes or links:
        return True, "已检测到证据板内容。"
    return False, "请在证据板新增线索或关联。"


def check_relationship_linked(app) -> Tuple[bool, str]:
    rels = app.project_manager.get_relationships()
    links = rels.get("relationship_links", []) or []
    if links:
        return True, "已检测到人物关系连接。"
    return False, "请在人物关系图中新增一条关系。"


def check_heartbeat_added(app) -> Tuple[bool, str]:
    scenes = app.project_manager.get_scenes() or []
    for scene in scenes:
        if scene.get("heartbeat", 0):
            return True, "已检测到心动事件。"
    return False, "请在心动追踪中标记至少一个心动节点。"


def check_faction_added(app) -> Tuple[bool, str]:
    factions = app.project_manager.project_data.get("factions", {})
    groups = factions.get("groups", []) or []
    if groups:
        return True, "已检测到势力条目。"
    return False, "请在势力矩阵中新增一个势力。"


def check_world_entry_added(app) -> Tuple[bool, str]:
    entries = app.project_manager.get_world_entries() or []
    if entries:
        return True, "已检测到世界观条目。"
    return False, "请在世界观百科中新增一个条目。"


def check_iceberg_entry_added(app) -> Tuple[bool, str]:
    entries = app.project_manager.get_world_entries() or []
    for entry in entries:
        depth = entry.get("iceberg_depth", "surface")
        if depth and depth != "surface":
            return True, "已检测到冰山层级条目。"
    return False, "请在世界冰山中调整一个条目层级。"


def check_variable_added(app) -> Tuple[bool, str]:
    variables = app.project_manager.project_data.get("variables", []) or []
    if variables:
        return True, "已检测到变量条目。"
    return False, "请在变量管理中新增一个变量。"


def check_flowchart_linked(app) -> Tuple[bool, str]:
    scenes = app.project_manager.get_scenes() or []
    for scene in scenes:
        choices = scene.get("choices", []) or []
        for choice in choices:
            if choice.get("target_scene"):
                return True, "已检测到剧情流向连接。"
    return False, "请在剧情流向中创建并连接节点。"


def check_scene_time_set(app) -> Tuple[bool, str]:
    scenes = app.project_manager.get_scenes() or []
    for scene in scenes:
        if scene.get("time"):
            return True, "已检测到场景时间信息。"
    return False, "请为至少一个场景填写时间信息。"


def check_export_done(app, progress_key: str) -> Tuple[bool, str]:
    if app.guide_progress.is_completed(progress_key):
        return True, "已记录导出完成。"
    return False, "请通过“文件 → 导出”完成一次导出。"
