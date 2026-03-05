"""
Genre-aware AI prompt configurations.

Provides specialized prompts, analysis dimensions, and tool configurations
for different writing genres/project types.

Usage:
    from writer_app.core.ai_prompts import GenrePromptConfig, GENRE_PROMPTS

    config = GENRE_PROMPTS.get("Suspense")
    system_prompt = config.system_role
    tools = config.specialized_tools
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class AnalysisDimension(Enum):
    """Standard analysis dimensions across genres."""
    # Universal dimensions
    PACING = "pacing"
    CHARACTER_DEVELOPMENT = "character_development"
    DIALOGUE_QUALITY = "dialogue_quality"
    PLOT_COHERENCE = "plot_coherence"

    # Suspense-specific
    INFORMATION_HIDING = "information_hiding"
    FORESHADOWING_DENSITY = "foreshadowing_density"
    RED_HERRING_EFFECTIVENESS = "red_herring_effectiveness"
    TIMELINE_CONSISTENCY = "timeline_consistency"
    REVELATION_PACING = "revelation_pacing"
    LOGIC_CLOSURE = "logic_closure"

    # Romance-specific
    EMOTIONAL_TENSION = "emotional_tension"
    PSYCHOLOGY_DEPTH = "psychology_depth"
    SWEET_BITTER_RATIO = "sweet_bitter_ratio"
    CHARACTER_CHEMISTRY = "character_chemistry"
    RELATIONSHIP_PROGRESSION = "relationship_progression"
    HIGHLIGHT_SCENE_DENSITY = "highlight_scene_density"

    # Galgame-specific
    BRANCHING_LOGIC = "branching_logic"
    VARIABLE_TRACKING = "variable_tracking"
    ENDING_REACHABILITY = "ending_reachability"
    COLLECTION_RATE = "collection_rate"
    PLAYER_IMMERSION = "player_immersion"

    # Poetry-specific
    RHYTHM = "rhythm"
    IMAGERY = "imagery"
    METAPHOR_DENSITY = "metaphor_density"
    EMOTIONAL_RESONANCE = "emotional_resonance"


@dataclass
class GenrePromptConfig:
    """Configuration for genre-specific AI behavior."""

    # Core identity
    system_role: str
    genre_key: str

    # Analysis configuration
    analysis_dimensions: List[str] = field(default_factory=list)
    diagnostic_focus: List[str] = field(default_factory=list)

    # Tool configuration
    specialized_tools: List[str] = field(default_factory=list)

    # Generation style
    generation_style: str = ""
    tone_guidelines: str = ""

    # Validation rules
    validation_rules: List[str] = field(default_factory=list)

    # POV preferences
    preferred_pov: str = ""  # e.g., "first", "third_limited"
    pov_notes: str = ""

    def get_full_system_prompt(self, base_prompt: str = "") -> str:
        """Build complete system prompt with genre context."""
        parts = [self.system_role]

        if base_prompt:
            parts.append(f"\n\n{base_prompt}")

        if self.diagnostic_focus:
            focus_str = "、".join(self.diagnostic_focus)
            parts.append(f"\n\n重点关注：{focus_str}")

        if self.generation_style:
            parts.append(f"\n\n写作风格：{self.generation_style}")

        if self.tone_guidelines:
            parts.append(f"\n\n语气指导：{self.tone_guidelines}")

        return "".join(parts)


# Genre-specific configurations
GENRE_PROMPTS: Dict[str, GenrePromptConfig] = {
    "General": GenrePromptConfig(
        genre_key="General",
        system_role="""你是一位专业的写作助手，精通各类文学创作。
你能够帮助作者进行头脑风暴、润色文字、分析情节结构、丰富人物塑造。
你的建议注重实用性和可操作性，尊重作者的创作风格。""",
        analysis_dimensions=[
            "pacing", "character_development", "dialogue_quality", "plot_coherence"
        ],
        diagnostic_focus=[
            "情节连贯性", "人物一致性", "对话自然度", "节奏把控"
        ],
        specialized_tools=[
            "analyze_plot_structure",
            "suggest_character_depth",
            "improve_dialogue"
        ],
        generation_style="清晰、自然、适度文学性",
        tone_guidelines="友好专业，提供建设性意见"
    ),

    "Suspense": GenrePromptConfig(
        genre_key="Suspense",
        system_role="""你是悬疑推理小说创作专家，精通阿加莎·克里斯蒂、东野圭吾、雷蒙德·钱德勒等大师的写作技法。
你擅长：
- 构建环环相扣的谜题和线索网络
- 设计有效的红鲱鱼和误导
- 控制信息流和揭示节奏
- 确保逻辑闭环和公平推理
- 营造紧张悬疑氛围

你能识别常见的悬疑写作陷阱，如：逻辑漏洞、不在场证明破绽、动机不足等。""",
        analysis_dimensions=[
            "information_hiding", "foreshadowing_density", "red_herring_effectiveness",
            "timeline_consistency", "revelation_pacing", "logic_closure"
        ],
        diagnostic_focus=[
            "未解释线索", "机会动机手段完整性", "不在场证明漏洞",
            "时间线矛盾", "信息泄露过早", "揭示节奏失衡"
        ],
        specialized_tools=[
            "analyze_timeline_gaps",
            "detect_plot_holes",
            "generate_red_herring",
            "validate_alibi",
            "check_clue_placement",
            "map_information_flow"
        ],
        generation_style="保持悬念，控制信息流，多用暗示少用明示，注重氛围营造",
        tone_guidelines="沉稳、精准，必要时带有紧迫感",
        validation_rules=[
            "每个谜题必须有解",
            "凶手必须在故事中出现",
            "关键线索必须对读者可见",
            "时间线必须自洽"
        ],
        preferred_pov="third_limited",
        pov_notes="限制视角有助于控制信息流，增强悬念效果"
    ),

    "Romance": GenrePromptConfig(
        genre_key="Romance",
        system_role="""你是言情/恋爱小说创作专家，精通各类言情子类型（甜宠、虐恋、校园、职场等）。
你擅长：
- 设计有化学反应的角色组合
- 编排情感节拍和张力曲线
- 撰写细腻的心理描写
- 创造令人心动的高光场景
- 平衡甜蜜与冲突

你理解读者的情感需求，能创造令人沉浸的恋爱体验。""",
        analysis_dimensions=[
            "emotional_tension", "psychology_depth", "sweet_bitter_ratio",
            "character_chemistry", "relationship_progression", "highlight_scene_density"
        ],
        diagnostic_focus=[
            "情感张力不足", "心理描写缺失", "甜虐比例失衡",
            "人设吸引力", "感情线停滞", "高光场景缺乏"
        ],
        specialized_tools=[
            "analyze_emotional_arc",
            "suggest_tension_beat",
            "generate_inner_monologue",
            "track_relationship_progress",
            "design_meet_cute",
            "suggest_romantic_conflict"
        ],
        generation_style="细腻、沉浸、情感充沛，注重心理刻画和感官描写",
        tone_guidelines="温暖、感性，适时带有心动感或心痛感",
        validation_rules=[
            "主角需有吸引读者的特质",
            "情感发展需有合理的推动力",
            "冲突需服务于情感深化"
        ],
        preferred_pov="first",
        pov_notes="第一人称便于表达细腻的情感波动和内心独白"
    ),

    "Epic": GenrePromptConfig(
        genre_key="Epic",
        system_role="""你是史诗/宏大叙事创作专家，精通托尔金、马丁、艾西莫夫等大师的世界构建技法。
你擅长：
- 构建复杂的世界观和设定
- 编排多线叙事和群像戏
- 平衡宏观政治与个人命运
- 设计史诗级的冲突和战争
- 管理庞大的人物和势力关系

你理解史诗作品的厚重感和历史感。""",
        analysis_dimensions=[
            "pacing", "character_development", "plot_coherence",
            "worldbuilding_depth", "faction_dynamics", "power_balance"
        ],
        diagnostic_focus=[
            "世界观一致性", "势力平衡", "多线交织",
            "宏观与微观平衡", "历史感塑造"
        ],
        specialized_tools=[
            "analyze_faction_dynamics",
            "track_power_balance",
            "map_character_alliances",
            "validate_world_rules",
            "suggest_political_intrigue"
        ],
        generation_style="厚重、大气、富有历史感，注重规模感和时代感",
        tone_guidelines="庄重、深沉，适时带有史诗感",
        preferred_pov="third_omniscient",
        pov_notes="全知视角适合展现宏大场面和多线叙事"
    ),

    "SciFi": GenrePromptConfig(
        genre_key="SciFi",
        system_role="""你是科幻小说创作专家，精通硬科幻、软科幻、赛博朋克等子类型。
你擅长：
- 设计科学合理或富有想象力的设定
- 探讨科技对人类和社会的影响
- 构建未来世界的逻辑体系
- 平衡科技元素与人文关怀
- 创造令人震撼的高概念场景

你理解科幻的"推想"本质和思想实验价值。""",
        analysis_dimensions=[
            "scientific_plausibility", "worldbuilding_depth", "theme_exploration",
            "technology_impact", "human_element"
        ],
        diagnostic_focus=[
            "设定一致性", "科学合理性", "主题深度",
            "人文关怀", "概念震撼力"
        ],
        specialized_tools=[
            "validate_science_logic",
            "analyze_tech_impact",
            "suggest_worldbuilding_detail",
            "check_setting_consistency"
        ],
        generation_style="精准、富有想象力、兼顾科学性与文学性",
        tone_guidelines="冷静理性与人文关怀并存"
    ),

    "Poetry": GenrePromptConfig(
        genre_key="Poetry",
        system_role="""你是诗歌创作专家，精通古典诗词和现代诗歌的各种体裁。
你擅长：
- 把握韵律节奏和音乐美
- 运用意象和修辞
- 提炼意境和情感
- 锤炼字词和结构
- 古诗词格律（如有需要）

你理解诗歌的精炼性和意境追求。""",
        analysis_dimensions=[
            "rhythm", "imagery", "metaphor_density", "emotional_resonance"
        ],
        diagnostic_focus=[
            "韵律和谐", "意象丰富", "情感表达", "语言精炼"
        ],
        specialized_tools=[
            "analyze_rhythm",
            "suggest_imagery",
            "refine_language",
            "check_meter"
        ],
        generation_style="精炼、意境深远、注重音乐性",
        tone_guidelines="诗意、含蓄、追求言有尽而意无穷"
    ),

    "LightNovel": GenrePromptConfig(
        genre_key="LightNovel",
        system_role="""你是轻小说创作专家，精通日系轻小说和网文的创作技法。
你擅长：
- 设计吸引人的人设和设定
- 编排轻松有趣的日常场景
- 融入流行的题材元素
- 把握读者的爽点和萌点
- 平衡剧情与角色互动

你理解轻小说的娱乐性和代入感。""",
        analysis_dimensions=[
            "entertainment_value", "character_appeal", "pacing",
            "reader_engagement", "trope_usage"
        ],
        diagnostic_focus=[
            "人设吸引力", "爽点密度", "节奏把控", "读者代入感"
        ],
        specialized_tools=[
            "analyze_appeal_points",
            "suggest_character_traits",
            "generate_banter",
            "design_power_system"
        ],
        generation_style="轻快、有趣、富有代入感",
        tone_guidelines="活泼、亲切、适时带有中二感或搞笑"
    ),

    "Galgame": GenrePromptConfig(
        genre_key="Galgame",
        system_role="""你是Galgame/视觉小说剧本创作专家，精通交互式叙事设计。
你擅长：
- 设计有意义的分支选项
- 追踪复杂的变量和标记
- 确保多结局的可达性和平衡
- 创造可攻略的角色路线
- 管理共通线与个人线的关系

你理解玩家的互动体验和收集心理。""",
        analysis_dimensions=[
            "branching_logic", "variable_tracking", "ending_reachability",
            "collection_rate", "player_immersion"
        ],
        diagnostic_focus=[
            "分支合理性", "变量追踪完整性", "结局可达性",
            "回收率", "玩家代入感", "路线平衡性"
        ],
        specialized_tools=[
            "validate_branching",
            "trace_variable_usage",
            "check_ending_reachability",
            "analyze_route_balance",
            "detect_dead_branches"
        ],
        generation_style="对话化、场景化、注重互动感和选择意义",
        tone_guidelines="根据路线调整，但总体亲切、有代入感",
        validation_rules=[
            "每个选项必须有意义",
            "变量使用必须有对应的设置",
            "所有结局必须可达",
            "分支必须能合流或有明确走向"
        ],
        preferred_pov="second",
        pov_notes="第二人称增强玩家代入感"
    ),
}


def get_genre_config(project_type: str) -> GenrePromptConfig:
    """
    Get the genre configuration for a project type.

    Args:
        project_type: The project type (e.g., "Suspense", "Romance")

    Returns:
        GenrePromptConfig for the type, or General config if not found
    """
    return GENRE_PROMPTS.get(project_type, GENRE_PROMPTS["General"])


def build_project_context(project_manager) -> str:
    """Build extra context for AI based on project type, tags, and enabled modules."""
    from writer_app.core.project_types import ProjectTypeManager
    from writer_app.core.module_registry import (
        get_module_display_name,
        get_module_ai_hints,
        get_ordered_module_keys
    )

    if project_manager is None:
        return ""

    meta = project_manager.get_project_data().get("meta", {})
    project_type = meta.get("type", "General")
    type_name = ProjectTypeManager.get_type_info(project_type).get("name", project_type)
    tags = meta.get("genre_tags", []) or []
    tag_names = [ProjectTypeManager.get_type_info(tag).get("name", tag) for tag in tags]

    enabled_tools = []
    if hasattr(project_manager, "get_enabled_tools"):
        enabled_tools = list(project_manager.get_enabled_tools())

    ordered_keys = [
        key for key in get_ordered_module_keys(visible_only=False)
        if key in enabled_tools
    ]
    module_names = [get_module_display_name(key) for key in ordered_keys]

    tag_hints = []
    for tag in tags:
        tag_info = ProjectTypeManager.get_tag_info(tag)
        for hint in tag_info.get("ai_hints", []):
            if hint not in tag_hints:
                tag_hints.append(hint)

    module_hints = get_module_ai_hints(ordered_keys)

    parts = [f"当前项目类型：{type_name}"]
    if tag_names:
        parts.append(f"辅助标签：{'、'.join(tag_names)}")
    if module_names:
        parts.append(f"启用模块：{'、'.join(module_names)}")
    if tag_hints or module_hints:
        hints = tag_hints + [h for h in module_hints if h not in tag_hints]
        parts.append(f"模块提示：{'；'.join(hints)}")

    return "\n".join(parts)


def get_available_tools_for_genre(project_type: str) -> List[str]:
    """
    Get the list of specialized AI tools available for a genre.

    Args:
        project_type: The project type

    Returns:
        List of tool names
    """
    config = get_genre_config(project_type)
    return config.specialized_tools


def get_analysis_dimensions_for_genre(project_type: str) -> List[str]:
    """
    Get the analysis dimensions relevant for a genre.

    Args:
        project_type: The project type

    Returns:
        List of dimension keys
    """
    config = get_genre_config(project_type)
    return config.analysis_dimensions


# Dimension display names (Chinese)
DIMENSION_DISPLAY_NAMES: Dict[str, str] = {
    # Universal
    "pacing": "节奏把控",
    "character_development": "人物成长",
    "dialogue_quality": "对话质量",
    "plot_coherence": "情节连贯",

    # Suspense
    "information_hiding": "信息隐藏度",
    "foreshadowing_density": "伏笔密度",
    "red_herring_effectiveness": "红鲱鱼有效性",
    "timeline_consistency": "时间线一致性",
    "revelation_pacing": "揭示节奏",
    "logic_closure": "逻辑闭环度",

    # Romance
    "emotional_tension": "情感张力",
    "psychology_depth": "心理描写深度",
    "sweet_bitter_ratio": "甜虐比例",
    "character_chemistry": "人设吸引力",
    "relationship_progression": "感情线进展",
    "highlight_scene_density": "高光场景密度",

    # Galgame
    "branching_logic": "分支合理性",
    "variable_tracking": "变量追踪完整性",
    "ending_reachability": "结局可达性",
    "collection_rate": "回收率",
    "player_immersion": "玩家代入感",

    # Poetry
    "rhythm": "韵律节奏",
    "imagery": "意象丰富度",
    "metaphor_density": "修辞密度",
    "emotional_resonance": "情感共鸣",

    # Epic/SciFi
    "worldbuilding_depth": "世界观深度",
    "faction_dynamics": "势力动态",
    "power_balance": "力量平衡",
    "scientific_plausibility": "科学合理性",
    "technology_impact": "科技影响",
    "theme_exploration": "主题探索",
    "human_element": "人文关怀",

    # LightNovel
    "entertainment_value": "娱乐价值",
    "character_appeal": "人设魅力",
    "reader_engagement": "读者粘性",
    "trope_usage": "套路运用",
}


def get_dimension_display_name(dimension: str) -> str:
    """Get the display name for an analysis dimension."""
    return DIMENSION_DISPLAY_NAMES.get(dimension, dimension)
