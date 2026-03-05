"""
悬浮助手 - 动态内容生成器 (Dynamic Content Generator)
基于项目内容和上下文动态生成个性化反馈和建议
"""
import random
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ContentType(Enum):
    """生成内容类型"""
    CHARACTER_COMMENT = "character_comment"
    SCENE_REACTION = "scene_reaction"
    PLOT_SUGGESTION = "plot_suggestion"
    STYLE_TIP = "style_tip"
    ENCOURAGEMENT = "encouragement"
    QUESTION = "question"


@dataclass
class GeneratedContent:
    """生成的内容"""
    content_type: ContentType
    text: str
    confidence: float  # 生成信心度 0-1
    context_used: List[str]  # 使用了哪些上下文


# 角色评论模板
CHARACTER_COMMENT_TEMPLATES = {
    "protagonist": [
        "{name}作为主角，感觉TA的核心动机是{motivation}？这很有深度！",
        "主角{name}的设定很有意思！{trait}这个特点很鲜明~",
        "{name}的故事正在展开...TA会如何成长呢？好期待！",
        "前辈把{name}塑造得很立体，{description}这段描写特别生动！",
    ],
    "antagonist": [
        "{name}作为反派，动机是什么呢？好的反派需要令人信服的理由~",
        "对手{name}的存在让故事更有张力！",
        "{name}和主角的对立很精彩，期待TA们的对决！",
    ],
    "supporting": [
        "配角{name}的存在让故事更丰富了~",
        "{name}和主角的关系很有趣，是{relationship}吗？",
        "{name}虽然是配角，但感觉会有很重要的戏份！",
    ],
    "mysterious": [
        "{name}...这个角色好神秘！一定藏着什么秘密吧？",
        "关于{name}的信息还不多，这种留白很吸引人~",
        "{name}的真实面目是什么呢？好好奇！",
    ],
    "lovable": [
        "{name}好可爱！是走治愈路线的角色吗？",
        "感觉{name}会是读者很喜欢的角色~",
        "{name}的性格设定很讨喜！",
    ],
}

# 场景反应模板
SCENE_REACTION_TEMPLATES = {
    "action": [
        "这场动作戏写得好紧张！{detail}这段特别精彩！",
        "打斗场面的节奏感很棒！能感受到那种紧迫感~",
        "动作描写很有画面感，仿佛能看到{visual}！",
    ],
    "emotional": [
        "这个场景好虐心...{emotion}的描写太细腻了！",
        "读到这里都有点难过了...{character}太不容易了。",
        "感情戏写得好真实！{detail}这段特别动人~",
    ],
    "dialogue": [
        "这段对话信息量好大！潜台词很丰富~",
        "对话写得很自然，{character}的性格跃然纸上！",
        "通过对话推进剧情，节奏把握得很好！",
    ],
    "suspense": [
        "这里的氛围太紧张了！我都屏住呼吸看完的！",
        "悬念设置得恰到好处，好想知道接下来会发生什么！",
        "{mystery}...这个伏笔埋得很妙！",
    ],
    "worldbuilding": [
        "世界观的描写很沉浸！{detail}这个设定很有意思~",
        "通过场景展现世界观，比直接叙述高明多了！",
        "这个世界的{aspect}描写得很细致！",
    ],
    "romance": [
        "这个场景好甜！{characters}的互动太有爱了~",
        "氛围感拉满！恋爱的心跳感扑面而来！",
        "糖！大糖！我先甜为敬！",
    ],
    "revelation": [
        "真相揭露！原来是这样！",
        "伏笔回收！之前的疑惑终于解开了！",
        "这个反转...完全没想到！太精彩了！",
    ],
}

# 情节建议模板
PLOT_SUGGESTION_TEMPLATES = {
    "stuck": [
        "如果卡在这里，不如试试让{character}做一个意外的选择？",
        "可以考虑引入一个突发事件来打破僵局~",
        "换个视角写写看？也许{other_character}的视角会有新发现~",
        "这里可以用「如果最糟糕的事情发生了会怎样」来推进~",
    ],
    "too_smooth": [
        "故事进展得很顺利，但可以考虑加点波折？",
        "是不是可以给{character}设置一个小障碍？",
        "顺利是好事，但适当的困难会让故事更有张力~",
    ],
    "character_passive": [
        "{character}目前比较被动，可以让TA主动做些什么？",
        "主角需要更多主动权，TA的核心目标是什么？",
        "让{character}做一个艰难的选择，会让角色更立体~",
    ],
    "pacing_slow": [
        "这一段节奏可以稍微加快一点？",
        "可以考虑删减一些不必要的描写~",
        "如果是过渡段落，可以更简洁一些~",
    ],
    "pacing_fast": [
        "这里可以稍微放慢脚步，让读者消化一下？",
        "重要的场景可以多花点笔墨~",
        "情感铺垫再多一点，高潮会更有冲击力~",
    ],
}

# 写作风格提示
STYLE_TIP_TEMPLATES = {
    "dialogue_heavy": [
        "对话很多，可以适当加点动作和表情描写~",
        "试试用「TA皱眉」代替「TA不高兴地说」？",
        "对话间隙加点环境描写，节奏会更好~",
    ],
    "description_heavy": [
        "描写很细腻！适时推进情节会更抓人~",
        "景物描写可以和人物心理结合~",
        "描写是为了故事服务的，把握好比例~",
    ],
    "repetitive_words": [
        "「{word}」出现得比较频繁，可以用同义词替换一些~",
        "注意词汇的多样性，避免重复~",
    ],
    "sentence_length": [
        "句子普遍偏长，可以拆分一些让阅读更轻松~",
        "长短句结合会让节奏更有变化~",
    ],
    "show_dont_tell": [
        "这里可以试试「展示」而不是「叙述」~",
        "与其说「TA很生气」，不如描写TA的表现~",
    ],
}


class DynamicContentGenerator:
    """动态内容生成器"""

    def __init__(self):
        self.generated_history: List[str] = []  # 避免重复
        self.max_history = 50

    def generate_character_comment(self, character: Dict,
                                   context: Optional[Dict] = None) -> Optional[GeneratedContent]:
        """
        生成角色评论

        Args:
            character: 角色数据
            context: 上下文信息

        Returns:
            生成的内容或 None
        """
        name = character.get("name", "")
        if not name:
            return None

        context = context or {}
        context_used = ["character_name"]

        # 判断角色类型
        role = character.get("role", "").lower()
        description = character.get("description", "")
        tags = character.get("tags", [])

        # 确定模板类别
        if "主角" in role or "protagonist" in role.lower():
            category = "protagonist"
        elif "反派" in role or "antagonist" in role.lower() or any(t in ["反派", "敌人"] for t in tags):
            category = "antagonist"
        elif any(t in ["神秘", "谜"] for t in tags) or "神秘" in description:
            category = "mysterious"
        elif any(t in ["可爱", "治愈", "温柔"] for t in tags):
            category = "lovable"
        else:
            category = "supporting"

        templates = CHARACTER_COMMENT_TEMPLATES.get(category, CHARACTER_COMMENT_TEMPLATES["supporting"])

        # 选择模板
        template = self._select_template(templates)
        if not template:
            return None

        # 准备格式化参数
        format_args = {
            "name": name,
            "description": description[:30] + "..." if len(description) > 30 else description,
            "trait": self._extract_trait(description) or "独特",
            "motivation": self._guess_motivation(character) or "某个目标",
            "relationship": self._guess_relationship(character) or "朋友",
        }

        # 格式化
        try:
            text = template.format(**format_args)
        except KeyError:
            text = template.replace("{name}", name)

        return GeneratedContent(
            content_type=ContentType.CHARACTER_COMMENT,
            text=text,
            confidence=0.7,
            context_used=context_used
        )

    def generate_scene_reaction(self, scene: Dict,
                               context: Optional[Dict] = None) -> Optional[GeneratedContent]:
        """
        生成场景反应

        Args:
            scene: 场景数据
            context: 上下文信息

        Returns:
            生成的内容或 None
        """
        content = scene.get("content", "")
        if not content or len(content) < 50:
            return None

        context = context or {}
        context_used = ["scene_content"]

        # 分析场景类型
        scene_type = self._detect_scene_type(content)
        templates = SCENE_REACTION_TEMPLATES.get(scene_type, [])

        if not templates:
            return None

        template = self._select_template(templates)
        if not template:
            return None

        # 提取细节用于格式化
        format_args = {
            "detail": self._extract_highlight(content) or "这一段",
            "character": self._extract_character_mention(content) or "角色",
            "characters": "他们",
            "visual": self._extract_visual(content) or "那个画面",
            "emotion": self._extract_emotion(content) or "情感",
            "mystery": self._extract_mystery(content) or "这个线索",
            "aspect": "这方面",
        }

        try:
            text = template.format(**format_args)
        except KeyError:
            text = template

        return GeneratedContent(
            content_type=ContentType.SCENE_REACTION,
            text=text,
            confidence=0.6,
            context_used=context_used
        )

    def generate_plot_suggestion(self, analysis_result: Dict,
                                characters: List[Dict] = None) -> Optional[GeneratedContent]:
        """
        生成情节建议

        Args:
            analysis_result: 分析结果
            characters: 角色列表

        Returns:
            生成的内容或 None
        """
        characters = characters or []
        context_used = ["analysis_result"]

        # 确定建议类型
        suggestion_type = None
        if analysis_result.get("character_passive"):
            suggestion_type = "character_passive"
        elif analysis_result.get("pacing_too_fast"):
            suggestion_type = "pacing_fast"
        elif analysis_result.get("pacing_too_slow"):
            suggestion_type = "pacing_slow"
        elif analysis_result.get("conflict_missing"):
            suggestion_type = "too_smooth"
        else:
            suggestion_type = "stuck"

        templates = PLOT_SUGGESTION_TEMPLATES.get(suggestion_type, [])
        if not templates:
            return None

        template = self._select_template(templates)
        if not template:
            return None

        # 获取角色名用于格式化
        char_name = "主角"
        other_char = "其他角色"
        if characters:
            char_name = characters[0].get("name", "主角")
            if len(characters) > 1:
                other_char = characters[1].get("name", "其他角色")

        format_args = {
            "character": char_name,
            "other_character": other_char,
        }

        try:
            text = template.format(**format_args)
        except KeyError:
            text = template

        return GeneratedContent(
            content_type=ContentType.PLOT_SUGGESTION,
            text=text,
            confidence=0.5,
            context_used=context_used
        )

    def generate_style_tip(self, style_analysis: Dict) -> Optional[GeneratedContent]:
        """
        生成写作风格提示

        Args:
            style_analysis: 风格分析结果

        Returns:
            生成的内容或 None
        """
        context_used = ["style_analysis"]

        # 确定提示类型
        tip_type = None
        format_args = {}

        if style_analysis.get("dialogue_ratio", 0) > 0.6:
            tip_type = "dialogue_heavy"
        elif style_analysis.get("description_ratio", 0) > 0.5:
            tip_type = "description_heavy"
        elif style_analysis.get("avg_sentence_length", 0) > 50:
            tip_type = "sentence_length"
        elif style_analysis.get("repetitive_word"):
            tip_type = "repetitive_words"
            format_args["word"] = style_analysis.get("repetitive_word", "")

        if not tip_type:
            return None

        templates = STYLE_TIP_TEMPLATES.get(tip_type, [])
        if not templates:
            return None

        template = self._select_template(templates)
        if not template:
            return None

        try:
            text = template.format(**format_args)
        except KeyError:
            text = template

        return GeneratedContent(
            content_type=ContentType.STYLE_TIP,
            text=text,
            confidence=0.6,
            context_used=context_used
        )

    def generate_encouragement(self, context: Dict) -> GeneratedContent:
        """生成鼓励内容"""
        templates = [
            "继续加油！你的故事正在成长~",
            "每写一个字，都是向完成迈进！",
            "创作是一场马拉松，你已经跑了很远了！",
            "相信自己，你的故事独一无二！",
            "灵感会回来的，保持耐心~",
            "写作的乐趣就在过程中，享受它！",
            "不完美也没关系，先完成再完美！",
            "你比昨天更接近目标了！",
        ]

        return GeneratedContent(
            content_type=ContentType.ENCOURAGEMENT,
            text=random.choice(templates),
            confidence=0.9,
            context_used=[]
        )

    def generate_question(self, scene: Dict = None,
                         character: Dict = None) -> Optional[GeneratedContent]:
        """
        生成互动问题

        Args:
            scene: 当前场景
            character: 相关角色

        Returns:
            生成的问题或 None
        """
        questions = []

        if scene:
            content = scene.get("content", "")
            if "对话" in content or '"' in content or '"' in content:
                questions.append("这段对话背后，角色真正想表达的是什么？")
            if len(content) < 200:
                questions.append("这个场景的核心情感是什么？")

        if character:
            name = character.get("name", "")
            if name:
                questions.extend([
                    f"{name}最害怕的事情是什么？",
                    f"如果{name}必须做一个选择，TA会选什么？",
                    f"{name}有什么不为人知的一面？",
                ])

        if not questions:
            questions = [
                "接下来会发生什么呢？",
                "这个故事的核心主题是什么？",
                "读者看到这里会有什么感受？",
            ]

        return GeneratedContent(
            content_type=ContentType.QUESTION,
            text=random.choice(questions),
            confidence=0.7,
            context_used=["scene", "character"] if scene or character else []
        )

    def _select_template(self, templates: List[str]) -> Optional[str]:
        """选择模板，避免重复"""
        available = [t for t in templates if t not in self.generated_history[-10:]]
        if not available:
            available = templates

        selected = random.choice(available) if available else None

        if selected:
            self.generated_history.append(selected)
            if len(self.generated_history) > self.max_history:
                self.generated_history = self.generated_history[-self.max_history:]

        return selected

    def _detect_scene_type(self, content: str) -> str:
        """检测场景类型"""
        # 动作场景
        action_keywords = ["打", "躲", "跑", "冲", "抓", "战斗", "攻击", "闪避"]
        if sum(content.count(kw) for kw in action_keywords) > 3:
            return "action"

        # 情感场景
        emotion_keywords = ["哭", "泪", "心", "痛", "难过", "开心", "幸福"]
        if sum(content.count(kw) for kw in emotion_keywords) > 3:
            return "emotional"

        # 对话场景
        if content.count('"') + content.count('"') + content.count('「') > 6:
            return "dialogue"

        # 悬疑场景
        suspense_keywords = ["秘密", "真相", "线索", "谜", "发现", "隐藏"]
        if sum(content.count(kw) for kw in suspense_keywords) > 2:
            return "suspense"

        # 浪漫场景
        romance_keywords = ["心跳", "脸红", "目光", "微笑", "手", "温柔"]
        if sum(content.count(kw) for kw in romance_keywords) > 2:
            return "romance"

        # 揭露场景
        revelation_keywords = ["原来", "其实", "没想到", "真相是"]
        if any(kw in content for kw in revelation_keywords):
            return "revelation"

        return "worldbuilding"

    def _extract_trait(self, description: str) -> Optional[str]:
        """从描述中提取特点"""
        trait_patterns = [
            r"(性格\S+)",
            r"(是个\S+的人)",
            r"(非常\S+)",
            r"(总是\S+)",
        ]

        for pattern in trait_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)[:10]

        return None

    def _guess_motivation(self, character: Dict) -> Optional[str]:
        """猜测角色动机"""
        description = character.get("description", "")
        background = character.get("background", "")
        text = description + background

        motivations = {
            "复仇": ["复仇", "报仇", "仇恨", "杀父", "杀母"],
            "守护": ["守护", "保护", "珍视", "家人", "朋友"],
            "追求力量": ["变强", "力量", "实力", "修炼", "成长"],
            "寻找真相": ["真相", "秘密", "答案", "调查", "探索"],
            "追求自由": ["自由", "逃离", "束缚", "限制"],
            "实现梦想": ["梦想", "理想", "目标", "愿望"],
        }

        for motivation, keywords in motivations.items():
            if any(kw in text for kw in keywords):
                return motivation

        return None

    def _guess_relationship(self, character: Dict) -> Optional[str]:
        """猜测角色关系"""
        tags = character.get("tags", [])
        description = character.get("description", "")

        relationships = {
            "朋友": ["朋友", "友人", "挚友", "伙伴"],
            "恋人": ["恋人", "情人", "爱人", "心上人"],
            "对手": ["对手", "敌人", "仇人", "敌对"],
            "导师": ["老师", "师傅", "导师", "前辈"],
            "家人": ["父亲", "母亲", "兄弟", "姐妹", "家人"],
        }

        text = " ".join(tags) + description
        for rel, keywords in relationships.items():
            if any(kw in text for kw in keywords):
                return rel

        return None

    def _extract_highlight(self, content: str) -> Optional[str]:
        """提取内容亮点"""
        # 寻找有引号的对话
        dialogue_match = re.search(r'["「](.{5,20})["」]', content)
        if dialogue_match:
            return f"「{dialogue_match.group(1)}」"

        # 寻找感叹句
        exclaim_match = re.search(r'[^。！？]{5,15}！', content)
        if exclaim_match:
            return exclaim_match.group()

        return None

    def _extract_character_mention(self, content: str) -> Optional[str]:
        """提取角色提及"""
        # 简单匹配：寻找引号后的人名模式
        name_match = re.search(r'["「][^"」]*["」]\s*([^\s，。]{2,4})\s*(?:说|道|问|答|喊)', content)
        if name_match:
            return name_match.group(1)

        return None

    def _extract_visual(self, content: str) -> Optional[str]:
        """提取视觉描写"""
        visual_patterns = [
            r"(看到了?\S{2,8})",
            r"(\S{2,8}的身影)",
            r"(\S{2,8}的画面)",
        ]

        for pattern in visual_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)

        return None

    def _extract_emotion(self, content: str) -> Optional[str]:
        """提取情感"""
        emotions = ["悲伤", "喜悦", "愤怒", "恐惧", "惊讶", "期待", "失落", "温暖"]
        for emotion in emotions:
            if emotion in content:
                return emotion

        return None

    def _extract_mystery(self, content: str) -> Optional[str]:
        """提取悬念"""
        mystery_patterns = [
            r"(为什么\S{2,10})",
            r"(谁是\S{2,8})",
            r"(\S{2,8}的秘密)",
            r"(\S{2,8}究竟\S{2,8})",
        ]

        for pattern in mystery_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)

        return None
