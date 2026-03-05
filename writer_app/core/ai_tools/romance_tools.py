"""
言情/恋爱类 AI 工具 - 提供情感弧线分析、张力节拍建议、内心独白生成等功能

用法:
    这些工具通过 AIToolRegistry 自动注册，可被 AI 调用
"""

from typing import Dict, List, Any, Optional
from writer_app.core.ai_tools import AITool, ToolParameter, ToolResult


class AnalyzeEmotionalArcTool(AITool):
    """分析情感弧线"""

    name = "analyze_emotional_arc"
    description = "分析故事的情感弧线，识别情感高峰、低谷和转折点"
    parameters = [
        ToolParameter(
            name="character_pair",
            type="string",
            description="可选：分析特定角色组合的情感线（格式：角色A,角色B）",
            required=False
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            if not scenes:
                return ToolResult.error("没有场景可分析")

            char_pair = params.get("character_pair")
            if char_pair:
                pair_chars = [c.strip() for c in char_pair.split(",")]
            else:
                pair_chars = None

            emotional_beats = []

            # 情感关键词
            positive_keywords = ["喜欢", "爱", "心动", "甜蜜", "幸福", "温暖", "依恋", "思念", "告白", "亲吻"]
            negative_keywords = ["误会", "争吵", "分离", "痛苦", "失望", "嫉妒", "背叛", "决裂", "分手"]
            tension_keywords = ["暧昧", "犹豫", "挣扎", "矛盾", "心跳", "紧张", "试探", "等待"]

            for idx, scene in enumerate(scenes):
                content = scene.get("content", "")
                scene_chars = scene.get("characters", [])

                # 如果指定了角色对，检查是否都在场
                if pair_chars:
                    if not all(c in scene_chars for c in pair_chars):
                        continue

                # 分析情感倾向
                positive_count = sum(1 for kw in positive_keywords if kw in content)
                negative_count = sum(1 for kw in negative_keywords if kw in content)
                tension_count = sum(1 for kw in tension_keywords if kw in content)

                # 计算情感分数 (-100 到 +100)
                total = positive_count + negative_count + tension_count
                if total > 0:
                    score = (positive_count - negative_count) / total * 100
                else:
                    score = 0

                beat_type = "neutral"
                if score > 30:
                    beat_type = "positive"
                elif score < -30:
                    beat_type = "negative"
                elif tension_count > 0:
                    beat_type = "tension"

                emotional_beats.append({
                    "scene_index": idx,
                    "scene_name": scene.get("name", ""),
                    "characters": scene_chars,
                    "emotional_score": round(score, 1),
                    "beat_type": beat_type,
                    "positive_indicators": positive_count,
                    "negative_indicators": negative_count,
                    "tension_indicators": tension_count
                })

            # 识别关键转折点
            turning_points = []
            for i in range(1, len(emotional_beats)):
                prev = emotional_beats[i - 1]
                curr = emotional_beats[i]
                score_change = curr["emotional_score"] - prev["emotional_score"]

                if abs(score_change) > 40:
                    turning_points.append({
                        "scene_index": curr["scene_index"],
                        "scene_name": curr["scene_name"],
                        "change": "positive_shift" if score_change > 0 else "negative_shift",
                        "magnitude": abs(score_change)
                    })

            # 计算整体统计
            if emotional_beats:
                avg_score = sum(b["emotional_score"] for b in emotional_beats) / len(emotional_beats)
                max_score = max(b["emotional_score"] for b in emotional_beats)
                min_score = min(b["emotional_score"] for b in emotional_beats)
            else:
                avg_score = max_score = min_score = 0

            return ToolResult.success(
                message=f"情感弧线分析完成，分析了 {len(emotional_beats)} 个场景",
                data={
                    "emotional_beats": emotional_beats,
                    "turning_points": turning_points,
                    "statistics": {
                        "average_score": round(avg_score, 1),
                        "max_score": round(max_score, 1),
                        "min_score": round(min_score, 1),
                        "total_turning_points": len(turning_points)
                    },
                    "analyzed_pair": pair_chars
                }
            )

        except Exception as e:
            return ToolResult.error(f"情感弧线分析失败: {e}")


class SuggestTensionBeatTool(AITool):
    """建议张力节拍"""

    name = "suggest_tension_beat"
    description = "基于当前情感状态，建议下一个合适的张力节拍"
    parameters = [
        ToolParameter(
            name="current_scene_index",
            type="integer",
            description="当前场景索引",
            required=True
        ),
        ToolParameter(
            name="desired_direction",
            type="string",
            description="期望的方向：'escalate'(升级)、'resolve'(化解)、'twist'(转折)",
            required=False
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            current_idx = params.get("current_scene_index", 0)
            direction = params.get("desired_direction", "escalate")

            if current_idx < 0 or current_idx >= len(scenes):
                return ToolResult.error("无效的场景索引")

            current_scene = scenes[current_idx]

            # 张力节拍模板
            beat_templates = {
                "escalate": [
                    {
                        "name": "秘密揭露",
                        "description": "揭露一个关于角色的秘密，增加情感赌注",
                        "example": "主角意外发现对方一直隐藏的过去"
                    },
                    {
                        "name": "外部压力",
                        "description": "引入外部因素威胁关系",
                        "example": "家人反对、工作调动、第三者出现"
                    },
                    {
                        "name": "承诺考验",
                        "description": "用困境测试双方的感情深度",
                        "example": "一方生病、经济困难、信任危机"
                    },
                    {
                        "name": "情感表白",
                        "description": "重要的情感表达时刻",
                        "example": "告白、求婚、说出「我爱你」"
                    }
                ],
                "resolve": [
                    {
                        "name": "误会澄清",
                        "description": "解开之前的误会",
                        "example": "真相大白，对方的行为有合理解释"
                    },
                    {
                        "name": "互相理解",
                        "description": "双方达成更深的理解",
                        "example": "倾听对方的心声，接受彼此的不完美"
                    },
                    {
                        "name": "外部支持",
                        "description": "获得外界的认可或帮助",
                        "example": "家人接受、朋友支持、障碍消除"
                    }
                ],
                "twist": [
                    {
                        "name": "身份反转",
                        "description": "揭示角色的真实身份或背景",
                        "example": "对方原来是竞争对手的家人"
                    },
                    {
                        "name": "动机反转",
                        "description": "揭示角色的真实动机",
                        "example": "原来一开始的接近是有目的的"
                    },
                    {
                        "name": "情感反转",
                        "description": "情感关系发生意外变化",
                        "example": "发现自己喜欢的其实是另一个人"
                    },
                    {
                        "name": "时间反转",
                        "description": "揭示过去的隐藏联系",
                        "example": "原来小时候就见过面"
                    }
                ]
            }

            suggestions = beat_templates.get(direction, beat_templates["escalate"])

            # 根据当前场景添加情境化建议
            current_chars = current_scene.get("characters", [])
            current_location = current_scene.get("location", "")

            contextual_suggestions = []
            for suggestion in suggestions:
                contextual = {
                    **suggestion,
                    "context": f"在「{current_location}」场景中，可以让{current_chars[0] if current_chars else '主角'}..."
                }
                contextual_suggestions.append(contextual)

            return ToolResult.success(
                message=f"生成了 {len(contextual_suggestions)} 个张力节拍建议",
                data={
                    "direction": direction,
                    "suggestions": contextual_suggestions,
                    "current_scene": {
                        "index": current_idx,
                        "name": current_scene.get("name", ""),
                        "characters": current_chars
                    }
                }
            )

        except Exception as e:
            return ToolResult.error(f"张力节拍建议失败: {e}")


class GenerateInnerMonologueTool(AITool):
    """生成内心独白建议"""

    name = "generate_inner_monologue"
    description = "为特定场景生成角色内心独白的写作建议"
    parameters = [
        ToolParameter(
            name="character_name",
            type="string",
            description="角色名称",
            required=True
        ),
        ToolParameter(
            name="emotional_state",
            type="string",
            description="情感状态：'nervous'、'happy'、'conflicted'、'heartbroken'等",
            required=True
        ),
        ToolParameter(
            name="scene_index",
            type="integer",
            description="场景索引",
            required=False
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            char_name = params.get("character_name")
            emotional_state = params.get("emotional_state", "neutral")
            scene_idx = params.get("scene_index")

            if not char_name:
                return ToolResult.error("必须指定角色名称")

            # 找到角色信息
            characters = project_manager.get_characters()
            target_char = None
            for char in characters:
                if char.get("name") == char_name:
                    target_char = char
                    break

            if not target_char:
                return ToolResult.error(f"未找到角色「{char_name}」")

            # 内心独白模板
            monologue_templates = {
                "nervous": {
                    "physical_cues": ["心跳加速", "手心出汗", "不敢直视", "说话结巴"],
                    "thought_patterns": [
                        "他/她会怎么想？",
                        "我是不是太明显了？",
                        "冷静，要冷静...",
                        "为什么心跳这么快？"
                    ],
                    "writing_tips": "使用短句、省略、自问自答，体现紧张的思绪"
                },
                "happy": {
                    "physical_cues": ["忍不住微笑", "步伐轻快", "眼睛发亮", "语调上扬"],
                    "thought_patterns": [
                        "这是真的吗？",
                        "我从没这么开心过",
                        "如果时间能停在这一刻就好了",
                        "原来被喜欢是这种感觉"
                    ],
                    "writing_tips": "使用感叹、比喻，让幸福感溢于言表"
                },
                "conflicted": {
                    "physical_cues": ["坐立不安", "叹气", "走来走去", "咬嘴唇"],
                    "thought_patterns": [
                        "我到底该怎么办？",
                        "一边是...一边是...",
                        "如果当初没有...",
                        "不管选择哪边，都会伤害另一边"
                    ],
                    "writing_tips": "使用对比、转折，展现内心的拉扯"
                },
                "heartbroken": {
                    "physical_cues": ["眼眶泛红", "呼吸困难", "身体发冷", "无法集中"],
                    "thought_patterns": [
                        "原来他/她从来没有...",
                        "我怎么这么傻",
                        "明明说好了...",
                        "心好像被什么东西狠狠揪住"
                    ],
                    "writing_tips": "使用慢节奏、回忆穿插、感官描写增强痛感"
                },
                "jealous": {
                    "physical_cues": ["握紧拳头", "强装镇定", "目光追随", "声音发紧"],
                    "thought_patterns": [
                        "他们在聊什么？",
                        "我凭什么在意？",
                        "明明跟我没关系...",
                        "为什么看到这一幕这么难受"
                    ],
                    "writing_tips": "使用否定句、自我说服，展现口是心非"
                },
                "longing": {
                    "physical_cues": ["望向远方", "无意识触碰相关物品", "失神", "轻叹"],
                    "thought_patterns": [
                        "不知道他/她现在在做什么",
                        "要是能再见一面就好了",
                        "距离上次见面已经...",
                        "这种感觉什么时候才能停止"
                    ],
                    "writing_tips": "使用时间标记、空间距离，强化思念的漫长"
                }
            }

            template = monologue_templates.get(emotional_state, monologue_templates["conflicted"])

            # 结合角色信息生成个性化建议
            char_desc = target_char.get("description", "")
            char_voice_style = target_char.get("narrator_voice_style", "")

            personalized_tips = []
            if "内向" in char_desc or "害羞" in char_desc:
                personalized_tips.append("角色较内向，内心戏可以更丰富，外在表现更克制")
            if "直率" in char_desc or "开朗" in char_desc:
                personalized_tips.append("角色较直率，内心独白可以更坦诚直接")

            return ToolResult.success(
                message=f"生成了「{char_name}」在「{emotional_state}」状态下的内心独白建议",
                data={
                    "character": char_name,
                    "emotional_state": emotional_state,
                    "physical_cues": template["physical_cues"],
                    "thought_patterns": template["thought_patterns"],
                    "writing_tips": template["writing_tips"],
                    "personalized_tips": personalized_tips,
                    "character_voice_style": char_voice_style
                }
            )

        except Exception as e:
            return ToolResult.error(f"生成内心独白建议失败: {e}")


class TrackRelationshipProgressTool(AITool):
    """追踪感情线进展"""

    name = "track_relationship_progress"
    description = "追踪两个角色之间的感情发展阶段"
    parameters = [
        ToolParameter(
            name="character_a",
            type="string",
            description="角色A名称",
            required=True
        ),
        ToolParameter(
            name="character_b",
            type="string",
            description="角色B名称",
            required=True
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            char_a = params.get("character_a")
            char_b = params.get("character_b")

            if not char_a or not char_b:
                return ToolResult.error("必须指定两个角色")

            scenes = project_manager.get_scenes()

            # 感情发展阶段定义
            stages = [
                {"name": "初遇", "keywords": ["第一次", "初见", "陌生", "认识"]},
                {"name": "了解", "keywords": ["了解", "交流", "聊天", "相处"]},
                {"name": "暧昧", "keywords": ["暧昧", "心动", "在意", "特别"]},
                {"name": "冲突", "keywords": ["误会", "争吵", "冷战", "分开"]},
                {"name": "确认", "keywords": ["告白", "喜欢", "在一起", "确认"]},
                {"name": "深入", "keywords": ["信任", "依赖", "未来", "承诺"]}
            ]

            # 分析共同出现的场景
            shared_scenes = []
            for idx, scene in enumerate(scenes):
                scene_chars = scene.get("characters", [])
                if char_a in scene_chars and char_b in scene_chars:
                    content = scene.get("content", "")

                    # 判断当前阶段
                    current_stage = None
                    for stage in stages:
                        if any(kw in content for kw in stage["keywords"]):
                            current_stage = stage["name"]
                            break

                    shared_scenes.append({
                        "scene_index": idx,
                        "scene_name": scene.get("name", ""),
                        "detected_stage": current_stage,
                        "content_preview": content[:100] + "..." if len(content) > 100 else content
                    })

            # 生成进展总结
            if shared_scenes:
                first_scene = shared_scenes[0]["scene_index"]
                last_scene = shared_scenes[-1]["scene_index"]
                scene_count = len(shared_scenes)
                stages_covered = list(set(s["detected_stage"] for s in shared_scenes if s["detected_stage"]))
            else:
                first_scene = last_scene = scene_count = 0
                stages_covered = []

            # 建议
            suggestions = []
            if scene_count < 5:
                suggestions.append("两人共同场景较少，建议增加互动机会")
            if "冲突" not in stages_covered:
                suggestions.append("考虑添加冲突场景，增加感情线的波折")
            if "暧昧" not in stages_covered and scene_count > 3:
                suggestions.append("考虑添加暧昧元素，为感情升温铺垫")

            return ToolResult.success(
                message=f"追踪了「{char_a}」和「{char_b}」的感情发展",
                data={
                    "character_a": char_a,
                    "character_b": char_b,
                    "shared_scenes": shared_scenes,
                    "statistics": {
                        "total_shared_scenes": scene_count,
                        "first_encounter": first_scene,
                        "last_interaction": last_scene,
                        "stages_covered": stages_covered
                    },
                    "suggestions": suggestions
                }
            )

        except Exception as e:
            return ToolResult.error(f"追踪感情进展失败: {e}")


class DesignMeetCuteTool(AITool):
    """设计初遇场景"""

    name = "design_meet_cute"
    description = "为两个角色设计有趣的初遇场景建议"
    parameters = [
        ToolParameter(
            name="character_a",
            type="string",
            description="角色A名称",
            required=True
        ),
        ToolParameter(
            name="character_b",
            type="string",
            description="角色B名称",
            required=True
        ),
        ToolParameter(
            name="setting",
            type="string",
            description="场景设定（如：校园、职场、咖啡厅）",
            required=False
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            char_a = params.get("character_a")
            char_b = params.get("character_b")
            setting = params.get("setting", "日常")

            if not char_a or not char_b:
                return ToolResult.error("必须指定两个角色")

            # 获取角色信息
            characters = project_manager.get_characters()
            char_a_info = None
            char_b_info = None

            for char in characters:
                if char.get("name") == char_a:
                    char_a_info = char
                elif char.get("name") == char_b:
                    char_b_info = char

            # 初遇模板
            meet_cute_templates = [
                {
                    "type": "collision",
                    "name": "意外碰撞",
                    "description": "两人因为某种意外相遇",
                    "examples": ["撞洒咖啡", "同时伸手拿同一本书", "雨中共用一把伞"],
                    "suitable_for": ["咖啡厅", "图书馆", "街道"]
                },
                {
                    "type": "mistaken_identity",
                    "name": "误认身份",
                    "description": "一方误认另一方的身份",
                    "examples": ["以为是约会对象", "以为是新同事", "以为是送餐员"],
                    "suitable_for": ["职场", "餐厅", "约会场所"]
                },
                {
                    "type": "rescue",
                    "name": "英雄救美",
                    "description": "一方帮助另一方脱困",
                    "examples": ["帮忙搬东西", "帮忙对付骚扰", "帮忙找路"],
                    "suitable_for": ["街道", "公共场所", "旅途中"]
                },
                {
                    "type": "conflict",
                    "name": "欢喜冤家",
                    "description": "初见就产生冲突或不快",
                    "examples": ["抢停车位", "座位之争", "观点对立"],
                    "suitable_for": ["职场", "学校", "公共场所"]
                },
                {
                    "type": "fate",
                    "name": "命运相遇",
                    "description": "多次偶遇后终于正式认识",
                    "examples": ["同一班公交", "住同一栋楼", "经常在同一家店"],
                    "suitable_for": ["日常", "住宅区", "通勤途中"]
                }
            ]

            # 根据设定筛选合适的模板
            suitable_templates = []
            for template in meet_cute_templates:
                if setting in template["suitable_for"] or setting == "日常":
                    suitable_templates.append(template)

            if not suitable_templates:
                suitable_templates = meet_cute_templates

            # 结合角色特点生成个性化建议
            personalized_suggestions = []
            for template in suitable_templates:
                suggestion = {
                    "template": template["name"],
                    "type": template["type"],
                    "base_description": template["description"],
                    "examples": template["examples"],
                    "personalized_hook": f"可以利用「{char_a}」和「{char_b}」的性格差异制造戏剧效果"
                }

                if char_a_info and char_b_info:
                    a_desc = char_a_info.get("description", "")
                    b_desc = char_b_info.get("description", "")

                    if "冷漠" in a_desc and "热情" in b_desc:
                        suggestion["personalized_hook"] = "冷热碰撞：热情的一方主动搭讪，冷漠的一方爱答不理"
                    elif "内向" in a_desc or "害羞" in b_desc:
                        suggestion["personalized_hook"] = "可以设计让内向的一方被迫开口的情境"

                personalized_suggestions.append(suggestion)

            return ToolResult.success(
                message=f"为「{char_a}」和「{char_b}」生成了 {len(personalized_suggestions)} 个初遇场景建议",
                data={
                    "character_a": char_a,
                    "character_b": char_b,
                    "setting": setting,
                    "suggestions": personalized_suggestions
                }
            )

        except Exception as e:
            return ToolResult.error(f"设计初遇场景失败: {e}")


def register_tools(registry):
    """注册所有言情类工具"""
    registry.register(AnalyzeEmotionalArcTool())
    registry.register(SuggestTensionBeatTool())
    registry.register(GenerateInnerMonologueTool())
    registry.register(TrackRelationshipProgressTool())
    registry.register(DesignMeetCuteTool())
