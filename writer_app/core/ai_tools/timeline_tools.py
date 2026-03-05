"""
时间轴工具 - 用于添加时间轴事件和看板任务

包含工具:
    - add_timeline_event: 添加时间轴事件（支持真相/谎言）
    - add_kanban_task: 添加看板任务
    - add_relationship: 添加人物关系
    - link_timeline_events: 关联真相与谎言事件
"""

from typing import Dict, Any, Callable
from . import AITool, ToolResult, ToolParameter, AIToolRegistry

from writer_app.core.commands import (
    AddTimelineEventCommand,
    AddSceneCommand,
    AddLinkCommand
)


class AddTimelineEventTool(AITool):
    """添加时间轴事件工具（完整字段版本）。"""

    name = "add_timeline_event"
    description = "添加新事件到时间轴。可以添加到真相时间轴(truth)或谎言时间轴(lie)。"
    parameters = [
        ToolParameter("name", "事件名称（简短描述）", "string", required=True),
        ToolParameter("timestamp", "事件日期/时间点（格式: YYYY-MM-DD 或 YYYY-MM-DD HH:MM）", "string", required=False, default=""),
        ToolParameter("timeline_type", "时间轴类型：truth（真相）或 lie（谎言）", "string", required=False, default="truth"),
        ToolParameter("location", "事件发生地点", "string", required=False, default=""),
        ToolParameter("action", "事件详细描述/行动内容", "string", required=False, default=""),
        ToolParameter("motive", "动机（真相事件）或借口（谎言事件）", "string", required=False, default=""),
        ToolParameter("chaos", "意外/混乱因素（真相事件专用）", "string", required=False, default=""),
        ToolParameter("gap", "隐瞒的内容（谎言事件专用）", "string", required=False, default=""),
        ToolParameter("bug", "破绽/漏洞（谎言事件专用）", "string", required=False, default=""),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        name = params.get("name", "")
        timestamp = params.get("timestamp", "")
        timeline_type = params.get("timeline_type", "truth").lower()
        location = params.get("location", "")
        action = params.get("action", "")
        motive = params.get("motive", "")

        if not name:
            return ToolResult.error("事件名称不能为空")

        # 根据类型构建不同的事件数据
        if timeline_type == "lie":
            event_data = {
                "name": name,
                "timestamp": timestamp,
                "motive": motive or "AI生成",
                "gap": params.get("gap", action),  # 隐瞒内容
                "bug": params.get("bug", ""),  # 破绽
                "linked_truth_event_uid": ""  # 待关联
            }
        else:
            # 默认为真相事件
            timeline_type = "truth"
            event_data = {
                "name": name,
                "timestamp": timestamp,
                "location": location,
                "action": action or name,
                "motive": motive,
                "chaos": params.get("chaos", ""),
                "linked_scene_uid": ""  # 待关联
            }

        cmd = AddTimelineEventCommand(
            project_manager,
            timeline_type,
            event_data,
            f"AI添加{'谎言' if timeline_type == 'lie' else '真相'}事件"
        )
        success = command_executor(cmd)

        if success:
            time_info = f" ({timestamp})" if timestamp else ""
            type_label = "谎言" if timeline_type == "lie" else "真相"
            return ToolResult.success(f"已添加{type_label}事件: {name}{time_info}")
        else:
            return ToolResult.error("添加时间轴事件失败")


class LinkTimelineEventsTool(AITool):
    """关联真相与谎言事件工具。"""

    name = "link_timeline_events"
    description = "将谎言事件与对应的真相事件进行关联，建立因果/冲突关系。"
    parameters = [
        ToolParameter("lie_event_name", "谎言事件名称", "string", required=True),
        ToolParameter("truth_event_name", "关联的真相事件名称", "string", required=True),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        lie_name = params.get("lie_event_name", "")
        truth_name = params.get("truth_event_name", "")

        if not lie_name or not truth_name:
            return ToolResult.error("必须指定谎言事件和真相事件名称")

        timelines = project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])
        lie_events = timelines.get("lie_events", [])

        # 查找真相事件 UID
        truth_uid = None
        for evt in truth_events:
            if evt.get("name") == truth_name:
                truth_uid = evt.get("uid")
                break

        if not truth_uid:
            return ToolResult.error(f"未找到真相事件: {truth_name}")

        # 查找并更新谎言事件
        updated = False
        for evt in lie_events:
            if evt.get("name") == lie_name:
                evt["linked_truth_event_uid"] = truth_uid
                updated = True
                break

        if updated:
            project_manager.mark_modified()
            return ToolResult.success(f"已关联: {lie_name} -> {truth_name}")
        else:
            return ToolResult.error(f"未找到谎言事件: {lie_name}")


class AddKanbanTaskTool(AITool):
    """添加看板任务工具。"""

    name = "add_kanban_task"
    description = "添加新任务到看板。通过创建场景并设置状态列来实现。"
    parameters = [
        ToolParameter("text", "任务内容", "string", required=True),
        ToolParameter("column", "看板列名（如：构思、初稿、润色、定稿）", "string", required=False, default="构思"),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        text = params.get("text", "新任务")
        column = params.get("column", "构思")

        # 获取可用的看板列
        columns = project_manager.get_kanban_columns()
        if not columns:
            columns = ["构思", "初稿", "润色", "定稿"]

        # 如果请求的列不存在，使用第一列
        target_col = column if column in columns else columns[0]

        scene_data = {
            "name": text,
            "content": "",
            "status": target_col
        }

        cmd = AddSceneCommand(project_manager, scene_data, "AI添加任务")
        success = command_executor(cmd)

        if success:
            return ToolResult.success(f"已添加任务到看板 '{target_col}': {text}")
        else:
            return ToolResult.error("添加看板任务失败")


class AddRelationshipTool(AITool):
    """添加人物关系工具。"""

    name = "add_relationship"
    description = "在关系图中添加两个人物之间的关系连线。"
    parameters = [
        ToolParameter("source", "起点人物名称", "string", required=True),
        ToolParameter("target", "终点人物名称", "string", required=True),
        ToolParameter("relation", "关系描述（如：朋友、恋人、敌人）", "string", required=False, default=""),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        src = params.get("source", "")
        tgt = params.get("target", "")
        rel = params.get("relation", "")

        if not src or not tgt:
            return ToolResult.error("必须指定起点和终点人物")

        link_data = {
            "source": src,
            "target": tgt,
            "label": rel,
            "type": "relates_to"
        }

        cmd = AddLinkCommand(project_manager, link_data)
        success = command_executor(cmd)

        if success:
            rel_text = f" ({rel})" if rel else ""
            return ToolResult.success(f"已建立关系: {src} -> {tgt}{rel_text}")
        else:
            return ToolResult.error("建立关系失败")


def register_tools(registry: 'AIToolRegistry') -> None:
    """注册所有时间轴工具。"""
    registry.register(AddTimelineEventTool())
    registry.register(LinkTimelineEventsTool())
    registry.register(AddKanbanTaskTool())
    registry.register(AddRelationshipTool())
