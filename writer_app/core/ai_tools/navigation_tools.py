"""
导航工具 - 用于获取统计信息和UI导航

包含工具:
    - get_stats: 获取项目统计数据
    - navigate_to: 跳转到指定标签页
"""

from typing import Dict, Any, Callable
from . import AITool, ToolResult, ToolParameter, AIToolRegistry


class GetStatsTool(AITool):
    """获取项目统计数据工具。"""

    name = "get_stats"
    description = "获取当前项目的统计数据，包括总字数、场景数、角色数等。"
    parameters = []

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        script = project_manager.get_script()
        scenes = script.get("scenes", [])
        chars = script.get("characters", [])
        entries = project_manager.get_world_entries()
        ideas = project_manager.get_ideas()

        # 计算总字数
        total_words = sum(len(s.get("content", "")) for s in scenes)

        # 计算平均场景长度
        avg_words = total_words // len(scenes) if scenes else 0

        # 获取时间轴事件数
        timelines = project_manager.project_data.get("timelines", {})
        truth_events = len(timelines.get("truth_events", []))
        lie_events = len(timelines.get("lie_events", []))

        stats_text = (
            f"项目统计数据:\n"
            f"- 总字数: {total_words}\n"
            f"- 场景数: {len(scenes)}\n"
            f"- 角色数: {len(chars)}\n"
            f"- 百科条目: {len(entries)}\n"
            f"- 灵感数: {len(ideas)}\n"
            f"- 时间轴事件: {truth_events + lie_events}\n"
            f"- 平均场景字数: {avg_words}"
        )

        return ToolResult.success(stats_text, data={
            "total_words": total_words,
            "scene_count": len(scenes),
            "character_count": len(chars),
            "wiki_count": len(entries),
            "idea_count": len(ideas),
            "timeline_events": truth_events + lie_events,
            "avg_scene_words": avg_words
        })


class NavigateToTool(AITool):
    """跳转到指定标签页工具。"""

    name = "navigate_to"
    description = "跳转到指定的功能标签页。支持的目标：大纲、剧本、人物、关系、线索、时间轴、统计、看板、日历、百科。"
    parameters = [
        ToolParameter("target", "目标标签页（如：大纲、剧本、人物、看板等）", "string", required=True),
    ]

    # 标签页映射
    TARGET_MAP = {
        "大纲": "outline", "outline": "outline",
        "剧本": "script", "script": "script",
        "人物": "relationship", "relationship": "relationship",
        "关系": "relationship",
        "线索": "evidence_board", "evidence": "evidence_board", "evidence_board": "evidence_board",
        "时间轴": "timeline", "timeline": "timeline",
        "统计": "analytics", "analytics": "analytics",
        "看板": "kanban", "kanban": "kanban",
        "日历": "calendar", "calendar": "calendar",
        "百科": "wiki", "wiki": "wiki"
    }

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        target = params.get("target", "outline")
        target_lower = target.lower() if target else "outline"

        tab_key = self.TARGET_MAP.get(target_lower, target_lower)

        # 返回导航信息（实际导航由调用方处理）
        return ToolResult.success(
            f"已跳转到: {target}",
            data={"tab_key": tab_key, "original_target": target}
        )


class StartTimerTool(AITool):
    """启动番茄钟工具。"""

    name = "start_timer"
    description = "启动番茄钟计时器，帮助专注写作。"
    parameters = [
        ToolParameter("duration", "计时时长（分钟），默认25分钟", "number", required=False, default=25),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        duration = params.get("duration", 25)

        # 返回计时器信息（实际启动由调用方处理）
        return ToolResult.success(
            f"已启动番茄钟: {duration} 分钟",
            data={"action": "start_timer", "duration": duration}
        )


class StopTimerTool(AITool):
    """停止番茄钟工具。"""

    name = "stop_timer"
    description = "停止当前的番茄钟计时器。"
    parameters = []

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        return ToolResult.success(
            "已停止番茄钟",
            data={"action": "stop_timer"}
        )


def register_tools(registry: 'AIToolRegistry') -> None:
    """注册所有导航工具。"""
    registry.register(GetStatsTool())
    registry.register(NavigateToTool())
    registry.register(StartTimerTool())
    registry.register(StopTimerTool())
