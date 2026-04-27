"""
基调大纲 AI 工具 - 向 LLM 暴露趋势、势差、中介关系的反推理上下文。
"""

from typing import Any, Dict

from writer_app.core.ai_tools import AITool, ToolParameter, ToolResult
from writer_app.core.tone_outline import (
    build_tone_reverse_reasoning_context,
    build_tone_reverse_reasoning_prompt,
)


class GetToneReverseReasoningContextTool(AITool):
    """获取基调大纲的 LLM 反推理上下文和提示词。"""

    name = "get_tone_reverse_reasoning_context"
    description = (
        "获取基调大纲的 LLM 反推理上下文和提示词，用于根据总趋势、小趋势、"
        "人物线势差、跨节点关系和中介结构反推剧情动因、缺口和场景钩子。"
    )
    parameters = [
        ToolParameter(
            "focus",
            "反推重点：all/trend/force/mediation/scene_beats，默认 all",
            "string",
            required=False,
            default="all",
        ),
        ToolParameter(
            "include_prompt",
            "是否同时返回可直接发送给 LLM 的 system_prompt/user_prompt，默认 true",
            "boolean",
            required=False,
            default=True,
        ),
    ]

    def execute(self, project_manager, command_executor, params: Dict[str, Any]) -> ToolResult:
        if not hasattr(project_manager, "get_tone_outline"):
            return ToolResult.error("当前项目管理器不支持基调大纲数据。")

        focus = str(params.get("focus") or "all").strip() or "all"
        include_prompt = params.get("include_prompt", True)
        if isinstance(include_prompt, str):
            include_prompt = include_prompt.strip().lower() not in {"0", "false", "no", "off"}

        tone_outline = project_manager.get_tone_outline()
        context = build_tone_reverse_reasoning_context(tone_outline, focus=focus)
        data: Dict[str, Any] = {"context": context}
        if include_prompt:
            prompt = build_tone_reverse_reasoning_prompt(tone_outline, focus=focus)
            data["prompt"] = prompt
            data["display_text"] = (
                "【基调大纲 LLM 反推提示词】\n"
                f"System:\n{prompt['system_prompt']}\n\n"
                f"User:\n{prompt['user_prompt']}"
            )

        meta = context.get("meta", {})
        message = (
            "已生成基调大纲反推理上下文："
            f"{meta.get('axis_count', 0)} 个节点，"
            f"{meta.get('line_count', 0)} 条线，"
            f"{meta.get('interaction_count', 0)} 个关系。"
        )
        return ToolResult.success(message, data=data)


def register_tools(registry):
    """注册基调大纲工具。"""
    registry.register(GetToneReverseReasoningContextTool())
