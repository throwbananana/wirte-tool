"""
悬浮助手 - 扩展反馈文案模板 (Extended Feedback Templates)
提供更丰富的反馈内容，支持个性化选择
"""
import random
from typing import Dict, List, Optional, Any
from enum import Enum


class FeedbackTone(Enum):
    """反馈语气"""
    CUTE = "cute"           # 可爱
    ENCOURAGING = "encouraging"  # 鼓励
    ANALYTICAL = "analytical"    # 分析
    HUMOROUS = "humorous"        # 幽默
    CALM = "calm"               # 平静


# 语气模板配置
TONE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "cute": {
        "name": "可爱",
        "description": "软萌可爱的语气，使用语气词和颜文字",
        "emoji_style": "kawaii",
        "sentence_enders": ["~", "！", "呢", "哦", "呀"],
        "sample_phrases": ["前辈", "好厉害", "我会加油的"],
    },
    "encouraging": {
        "name": "鼓励",
        "description": "积极正面的鼓励语气",
        "emoji_style": "positive",
        "sentence_enders": ["！", "加油！", "继续！"],
        "sample_phrases": ["做得好", "继续保持", "你可以的"],
    },
    "analytical": {
        "name": "分析",
        "description": "理性客观的分析语气",
        "emoji_style": "minimal",
        "sentence_enders": ["。", "。建议：", "。分析："],
        "sample_phrases": ["数据显示", "建议", "统计"],
    },
    "humorous": {
        "name": "幽默",
        "description": "轻松幽默的调侃语气",
        "emoji_style": "playful",
        "sentence_enders": ["！", "？", "~"],
        "sample_phrases": ["是不是开挂了", "这是什么神仙操作", "我都看呆了"],
    },
    "calm": {
        "name": "平静",
        "description": "沉稳冷静的语气",
        "emoji_style": "subtle",
        "sentence_enders": ["。", "呢。", "吧。"],
        "sample_phrases": ["慢慢来", "不着急", "一步一步"],
    },
}


# 扩展的行为反馈模板
EXTENDED_BEHAVIOR_FEEDBACK = {
    # =============================================================
    # 心流状态反馈
    # =============================================================
    "flow_enter": {
        "cute": [
            "哇，前辈进入状态了！我要安静一点~",
            "键盘在唱歌！我不打扰你~",
            "这个节奏...是心流！我看着就好~",
        ],
        "encouraging": [
            "很好的状态！保持住！",
            "进入心流了！这是创作的最佳时刻！",
            "灵感正在涌现，继续！",
        ],
        "humorous": [
            "手速起飞！键盘要冒烟了！",
            "是在和时间赛跑吗？加油！",
            "这个输出速度...是开挂了吧？",
        ],
    },

    "flow_finish": {
        "cute": [
            "刚才的{minutes}分钟里，你的键盘都要冒烟了！这就是传说中的心流吗？",
            "好厉害！一口气专注了{minutes}分钟，这就是职业作家的气场吧！",
            "呼...刚才都不敢打扰你，{minutes}分钟的深度创作，辛苦啦！",
            "{minutes}分钟的专注创作！前辈太厉害了，我都看呆了~",
            "刚才那一波输出太猛了！{minutes}分钟转瞬即逝呢！",
        ],
        "encouraging": [
            "{minutes}分钟的高效创作，这就是专业！",
            "完美的心流体验！{minutes}分钟的专注产出一定很可观！",
            "状态极佳！{minutes}分钟的深度工作值得庆祝！",
            "这{minutes}分钟的产出，足以证明你的实力！",
        ],
        "analytical": [
            "统计：心流持续{minutes}分钟，期间平均输出速度约{wpm}字/分钟。",
            "本次心流session：{minutes}分钟，属于{level}级别的专注度。",
            "心流结束。持续时间：{minutes}分钟。建议短暂休息后继续。",
        ],
        "humorous": [
            "{minutes}分钟不带喘气的！这是人类该有的手速吗？",
            "刚才那阵子，我都以为你被键盘附体了！{minutes}分钟啊！",
            "停！你已经超神了！{minutes}分钟连续创作需要冷静一下！",
            "我严重怀疑你开了倍速！{minutes}分钟飞一样过去了！",
        ],
    },

    # =============================================================
    # 润色/修改反馈
    # =============================================================
    "refactoring": {
        "cute": [
            "反复推敲、精雕细琢...这一定是很重要的段落吧？",
            "修改是写作的灵魂。我也觉得这里还可以更完美！",
            "这种精益求精的态度，我很佩服哦。",
            "一个字一个字地调整...这就是匠人精神！",
            "看你这么认真地修改，这段一定会变得很棒的！",
        ],
        "encouraging": [
            "好文章是改出来的！继续打磨！",
            "每一次修改都是进步！",
            "精益求精是优秀作者的特质！",
            "不满足于初稿，这才是专业态度！",
        ],
        "analytical": [
            "检测到反复编辑模式。当前段落修改次数较多，可能需要换个角度思考。",
            "建议：如果卡在某个表达上超过5分钟，可以先跳过继续写，稍后回来可能会有新灵感。",
        ],
        "humorous": [
            "又改了！你对这段话是有什么执念吗？",
            "修修改改...这是在和自己下棋吧？",
            "你和这个段落杠上了！谁先投降？",
        ],
    },

    # =============================================================
    # 架构师模式反馈
    # =============================================================
    "architect": {
        "cute": [
            "大纲、角色、正文...你的大脑在飞速运转呢，要喝杯水吗？",
            "统筹全局的感觉很棒吧？不过也要注意脑力消耗哦。",
            "哇，感觉你在构建一个庞大的世界呢！",
            "在各个模块之间跳转...前辈是在编织一张大网吗？",
            "左边大纲右边正文，上面角色下面设定...好忙好忙！",
        ],
        "encouraging": [
            "全局视野！这是优秀创作者的特质！",
            "多维度思考，你的故事一定很立体！",
            "架构清晰的故事更容易写下去！",
        ],
        "analytical": [
            "检测到跨模块操作。当前正在同时处理：大纲、角色、正文。建议一次专注一个维度。",
            "多模块切换可能导致思路分散。如果感到混乱，可以用便签记录当前思路。",
        ],
        "humorous": [
            "你是在写小说还是在下多线程象棋？",
            "切换得这么快，CPU不会过热吗？",
            "大纲角色正文齐飞！这是同时开三局吧！",
        ],
    },

    # =============================================================
    # 犹豫/卡文反馈
    # =============================================================
    "hesitation": {
        "cute": [
            "盯着屏幕发呆好久了...是不是卡文了？可以试试抽一张灵感卡哦。",
            "如果觉得累了，休息一下也没关系。欲速则不达嘛。",
            "唔...遇到瓶颈了吗？要不要和我聊聊思路？",
            "（小声）前辈，需要帮忙吗？",
            "卡住了吗？这很正常的，每个作者都会遇到~",
        ],
        "encouraging": [
            "遇到瓶颈是创作的一部分。换个思路，灵感会回来的！",
            "休息一下，有时候答案会自己浮现。",
            "卡文不可怕，可怕的是放弃。你能行的！",
            "每个伟大的作品背后都有无数次卡顿。坚持住！",
        ],
        "analytical": [
            "检测到编辑停滞。可能的原因：1)情节卡点 2)表达困难 3)需要休息。建议尝试：写下任意内容保持输出。",
            "当前场景编辑时间较长。建议：跳过困难部分，先写后面的内容，稍后回来处理。",
        ],
        "humorous": [
            "对着屏幕发呆的样子也很可爱...但是该写了吧？",
            "我看到光标在那里孤独地闪烁...它在等你！",
            "如果是在冥想的话...冥想结束了吗？",
            "发呆归发呆，别忘了存档啊！",
        ],
    },

    # =============================================================
    # 连续创作天数反馈
    # =============================================================
    "streak_3": {
        "cute": [
            "连续三天都在创作！养成习惯了呢~",
            "三天打卡成功！小成就解锁！",
        ],
        "encouraging": [
            "三天连续创作！习惯正在形成！",
            "坚持三天了！再坚持几天就能形成习惯！",
        ],
    },
    "streak_7": {
        "cute": [
            "连续7天创作达成！这种坚持太帅气了！",
            "一周全勤！你是最棒的！",
            "整整一周！每天都在进步呢~",
        ],
        "encouraging": [
            "7天连续创作！这是真正的坚持！",
            "一周不间断！你的故事正在成长！",
            "连续一周！这份毅力值得尊敬！",
        ],
        "humorous": [
            "7天全勤！你是要卷死谁啊！",
            "连续七天...你确定不是AI吧？",
        ],
    },
    "streak_14": {
        "cute": [
            "两周连续创作！真是太厉害了！",
            "14天！半个月的坚持，我好感动！",
        ],
        "encouraging": [
            "两周连续创作！习惯已经养成！",
            "14天的坚持证明了你的决心！",
        ],
    },
    "streak_30": {
        "cute": [
            "一个月都在坚持创作，这是伟大的里程碑！",
            "连续30天的努力，我都看在眼里哦。",
            "30天！这已经不是坚持，是热爱了！",
        ],
        "encouraging": [
            "30天连续创作！你已经证明了自己！",
            "一个月的坚持！你的故事一定很精彩！",
            "30天不间断！这是专业作家的节奏！",
        ],
        "humorous": [
            "30天！你是永动机吗？！",
            "一个月啊！这份执念我服了！",
        ],
    },

    # =============================================================
    # 复合规则反馈
    # =============================================================
    "late_night_flow": {
        "cute": [
            "夜深了，灵感却还在燃烧...要注意身体哦，我的大作家。",
            "虽然深夜效率很高，但也别忘了休息。我会一直陪着你的。",
            "月亮都打瞌睡了，你还在战斗...好敬业！",
        ],
        "encouraging": [
            "深夜的专注令人敬佩！不过也要照顾好身体！",
            "夜深人静最适合创作，但健康第一！",
        ],
        "humorous": [
            "深夜心流？你是吸血鬼作家吗？",
            "月亮：'歇歇吧求你了'",
        ],
    },
    "weekend_warrior": {
        "cute": [
            "周末还在这么努力地写作，这份热情一定能传达给读者的！",
            "难得的周末，把时间献给梦想的样子真迷人。",
            "别人在玩，你在创作...这就是差距！",
        ],
        "encouraging": [
            "周末高产！你在用行动证明对创作的热爱！",
            "周末也在努力，成功只是时间问题！",
        ],
    },
    "high_yield_streak": {
        "cute": [
            "不仅连续打卡，字数还这么多！你是在燃烧生命写作吗？",
            "太强了...连续的高产出，请收下我的膝盖！",
            "这个产量...是开了外挂吧？！",
        ],
        "encouraging": [
            "持续高产！你的作品在快速成长！",
            "连续高效输出！保持这个状态！",
        ],
        "humorous": [
            "日产千字还连续多天？人形打字机！",
            "这效率...你是不是有分身？",
        ],
    },
    "early_bird_sprint": {
        "cute": [
            "一日之计在于晨！早起写作的鸟儿有虫吃，效率真高！",
            "清晨的你好有精神！今天也是美好的创作日~",
        ],
        "encouraging": [
            "早起创作！一天的好开始！",
            "清晨高产！这是成功者的习惯！",
        ],
    },
    "marathoner": {
        "cute": [
            "单日突破5000字？！这是人类的手速吗？请收下我的膝盖！",
            "五千字！马拉松级别的产出！",
        ],
        "encouraging": [
            "5000字！今天是大丰收的一天！",
            "单日五千！你创造了属于自己的纪录！",
        ],
        "humorous": [
            "5000字！你的手指还好吗？需要我叫救护车吗？",
            "日产五千...你是文字印刷机吧？",
        ],
    },

    # =============================================================
    # 项目进度反馈
    # =============================================================
    "scene_count_10": {
        "cute": [
            "10个场景了！故事开始成型了呢~",
            "场景数达到两位数！很有进展！",
        ],
        "encouraging": [
            "10个场景！你的故事正在展开！",
            "进入两位数！继续推进！",
        ],
    },
    "scene_count_30": {
        "cute": [
            "30个场景！这已经是一个完整的故事了！",
            "30场景达成！前辈的故事好丰富~",
        ],
        "encouraging": [
            "30个场景！内容量相当可观！",
            "故事越来越饱满了！继续！",
        ],
    },
    "character_count_5": {
        "cute": [
            "5个角色了！人物关系开始丰富起来~",
            "第五个角色登场！热闹起来了！",
        ],
        "encouraging": [
            "5个角色！故事的人物谱系正在成形！",
            "角色越来越多！记得给每个人独特的个性！",
        ],
    },
    "word_count_10000": {
        "cute": [
            "一万字！这是一个重要的里程碑！",
            "破万了！前辈的故事已经有相当的体量了！",
        ],
        "encouraging": [
            "10000字！你的故事正在茁壮成长！",
            "万字达成！这是值得庆祝的成就！",
        ],
        "humorous": [
            "一万字！这都能出一本小册子了！",
            "破万！恭喜你可以申请作协了！（大概）",
        ],
    },
    "word_count_50000": {
        "cute": [
            "五万字！这已经是一部完整的中篇小说了！",
            "50000字！前辈真的太厉害了！",
        ],
        "encouraging": [
            "50000字！你创作了一部真正的作品！",
            "五万字的里程碑！你是真正的作家！",
        ],
    },

    # =============================================================
    # 模块使用反馈
    # =============================================================
    "first_use_timeline": {
        "cute": [
            "第一次使用时间线！这个工具对梳理剧情很有帮助哦~",
            "时间线工具解锁！故事的时间逻辑会更清晰！",
        ],
    },
    "first_use_evidence": {
        "cute": [
            "证据板！这是悬疑写作的利器！",
            "证据和线索管理工具，推理小说必备~",
        ],
    },
    "first_use_relationship": {
        "cute": [
            "人物关系图！角色之间的羁绊一目了然~",
            "关系网络可视化！人物关系更清楚了！",
        ],
    },
    "first_use_kanban": {
        "cute": [
            "看板模式！用来管理场景进度很方便哦~",
            "场景看板解锁！写作进度更好把控！",
        ],
    },

    # =============================================================
    # 时间相关反馈
    # =============================================================
    "morning_greeting": {
        "cute": [
            "早安！新的一天，新的创作~",
            "早上好！今天也要加油哦~",
            "清晨的第一缕阳光...和第一个字！",
        ],
        "encouraging": [
            "早安！美好的一天从创作开始！",
            "新的一天，新的可能！加油！",
        ],
    },
    "afternoon_check": {
        "cute": [
            "下午了~状态怎么样？",
            "下午茶时间~要不要休息一下？",
        ],
    },
    "evening_wrap": {
        "cute": [
            "傍晚了，今天的创作还顺利吗？",
            "夕阳西下，今天也辛苦了~",
        ],
    },
    "night_reminder": {
        "cute": [
            "夜深了...记得保存哦！",
            "快到睡觉时间了，今天的进度怎么样？",
        ],
        "encouraging": [
            "夜深了，但你的故事正在成长！",
            "晚安前记得存档！明天继续！",
        ],
    },
}


# 题材特定反馈
GENRE_SPECIFIC_FEEDBACK = {
    "Suspense": {
        "scene_added": [
            "新场景！会有什么线索埋在里面呢？",
            "又一个场景...诡计的拼图又多了一块！",
        ],
        "character_added": [
            "新角色登场...是嫌疑人？还是关键证人？",
            "每个新角色都可能是凶手...或者受害者。",
        ],
    },
    "Romance": {
        "scene_added": [
            "新场景~会有什么甜蜜的展开吗？",
            "又一个场景...恋爱进度+1？",
        ],
        "character_added": [
            "新角色！是情敌？还是神助攻？",
            "新人物登场...三角关系要来了吗？",
        ],
    },
    "Horror": {
        "scene_added": [
            "新场景...我要鼓起勇气看下去！",
            "又一个场景...希望没有jump scare...",
        ],
        "character_added": [
            "新角色...千万别是下一个受害者！",
            "又有人登场了...能活到最后吗？",
        ],
    },
    "Fantasy": {
        "scene_added": [
            "新场景！这个世界又展开了一角~",
            "又一个场景...会有什么奇遇呢？",
        ],
        "character_added": [
            "新角色登场！是敌是友？",
            "又有新伙伴了！队伍在壮大~",
        ],
    },
    "SciFi": {
        "scene_added": [
            "新场景...又是一个未来世界的角落！",
            "科技与想象力的结合~期待！",
        ],
        "character_added": [
            "新角色...是人类？还是AI？或者外星人？",
            "科幻世界的新住民登场！",
        ],
    },
}


class FeedbackSelector:
    """反馈选择器：根据用户偏好和上下文选择最合适的反馈"""

    def __init__(self, preference_tracker=None):
        self.preference_tracker = preference_tracker
        self.last_used: Dict[str, List[str]] = {}  # 记录最近使用的反馈，避免重复

    def select_feedback(self, category: str, context: Optional[Dict] = None,
                       preferred_tone: Optional[FeedbackTone] = None) -> str:
        """
        选择反馈文案

        Args:
            category: 反馈类别
            context: 上下文信息（用于格式化）
            preferred_tone: 偏好的语气

        Returns:
            选中的反馈文案
        """
        context = context or {}
        templates = EXTENDED_BEHAVIOR_FEEDBACK.get(category, {})

        if not templates:
            return ""

        # 确定语气
        tone = preferred_tone
        if tone is None and self.preference_tracker:
            # 从用户偏好推断
            prefs = self.preference_tracker.preferences
            if prefs.likes_humor > 0.7:
                tone = FeedbackTone.HUMOROUS
            elif prefs.likes_encouragement > 0.7:
                tone = FeedbackTone.ENCOURAGING
            elif prefs.likes_analysis > 0.7:
                tone = FeedbackTone.ANALYTICAL
            else:
                tone = FeedbackTone.CUTE

        if tone is None:
            tone = FeedbackTone.CUTE

        # 获取对应语气的模板
        tone_templates = templates.get(tone.value, [])
        if not tone_templates:
            # 回退到cute
            tone_templates = templates.get("cute", [])
        if not tone_templates:
            # 使用任何可用的
            for t in templates.values():
                if t:
                    tone_templates = t
                    break

        if not tone_templates:
            return ""

        # 避免重复
        used = self.last_used.get(category, [])
        available = [t for t in tone_templates if t not in used]
        if not available:
            available = tone_templates
            self.last_used[category] = []

        selected = random.choice(available)

        # 记录使用
        if category not in self.last_used:
            self.last_used[category] = []
        self.last_used[category].append(selected)
        if len(self.last_used[category]) > len(tone_templates) // 2:
            self.last_used[category] = self.last_used[category][-3:]

        # 格式化
        try:
            return selected.format(**context)
        except KeyError:
            return selected

    def get_genre_feedback(self, genre: str, event_type: str) -> Optional[str]:
        """获取题材特定反馈"""
        genre_templates = GENRE_SPECIFIC_FEEDBACK.get(genre, {})
        templates = genre_templates.get(event_type, [])

        if templates:
            return random.choice(templates)
        return None

    def load_preferences(self, prefs: Dict[str, Any]) -> None:
        """加载偏好设置"""
        self._stored_preferences = prefs or {}

    def get_preferences(self) -> Dict[str, Any]:
        """获取偏好设置"""
        return getattr(self, '_stored_preferences', {})

    def adjust_tone(self, message: str, preferred_tone: str) -> str:
        """
        根据偏好语气调整消息

        Args:
            message: 原始消息
            preferred_tone: 偏好语气 (cute, encouraging, analytical, humorous, calm)

        Returns:
            调整后的消息
        """
        if not message or not preferred_tone:
            return message

        # 语气调整规则
        tone_adjustments = {
            "cute": {
                "prefix": "",
                "suffix_options": ["~", "呢~", "哦~", "！"],
                "emoji_pool": ["✨", "💫", "🌟", "💕"],
            },
            "encouraging": {
                "prefix_options": ["", "加油！"],
                "suffix_options": ["！继续保持！", "！你很棒！", "！"],
                "emoji_pool": ["💪", "🎉", "👏", "⭐"],
            },
            "analytical": {
                "prefix": "",
                "suffix": "。",
                "remove_emojis": True,
            },
            "humorous": {
                "suffix_options": ["~哈哈", "~", "！嘿嘿"],
                "emoji_pool": ["😄", "🤣", "😎", "🎭"],
            },
            "calm": {
                "prefix": "",
                "suffix": "。",
                "remove_emojis": True,
            },
        }

        adjustment = tone_adjustments.get(preferred_tone)
        if not adjustment:
            return message

        result = message.rstrip("。！~")

        # 添加后缀
        suffix_options = adjustment.get("suffix_options")
        if suffix_options:
            result += random.choice(suffix_options)
        elif adjustment.get("suffix"):
            result += adjustment["suffix"]

        # 添加前缀
        prefix_options = adjustment.get("prefix_options")
        if prefix_options:
            prefix = random.choice(prefix_options)
            if prefix:
                result = prefix + result
        elif adjustment.get("prefix"):
            result = adjustment["prefix"] + result

        # 添加emoji (20%概率)
        emoji_pool = adjustment.get("emoji_pool")
        if emoji_pool and random.random() < 0.2:
            result = random.choice(emoji_pool) + " " + result

        return result

    def select_feedback(self, category: str, preferences: Dict = None,
                       context: Optional[Dict] = None) -> str:
        """
        选择反馈文案 (兼容 event_system 的调用方式)

        Args:
            category: 反馈类别
            preferences: 用户偏好
            context: 上下文信息

        Returns:
            选中的反馈文案
        """
        preferences = preferences or {}
        context = context or {}

        # 确定语气
        preferred_tone_str = preferences.get("preferred_tone", "cute")
        try:
            tone = FeedbackTone(preferred_tone_str)
        except ValueError:
            tone = FeedbackTone.CUTE

        templates = EXTENDED_BEHAVIOR_FEEDBACK.get(category, {})

        if not templates:
            # 尝试题材特定反馈
            project_type = context.get("project_type")
            if project_type:
                genre_feedback = self.get_genre_feedback(project_type, category)
                if genre_feedback:
                    return genre_feedback
            return ""

        # 获取对应语气的模板
        tone_templates = templates.get(tone.value, [])
        if not tone_templates:
            tone_templates = templates.get("cute", [])
        if not tone_templates:
            for t in templates.values():
                if t:
                    tone_templates = t
                    break

        if not tone_templates:
            return ""

        # 避免重复
        used = self.last_used.get(category, [])
        available = [t for t in tone_templates if t not in used]
        if not available:
            available = tone_templates
            self.last_used[category] = []

        selected = random.choice(available)

        # 记录使用
        if category not in self.last_used:
            self.last_used[category] = []
        self.last_used[category].append(selected)
        if len(self.last_used[category]) > len(tone_templates) // 2:
            self.last_used[category] = self.last_used[category][-3:]

        # 格式化
        try:
            return selected.format(**context)
        except KeyError:
            return selected


def get_all_feedback_templates() -> Dict[str, Any]:
    """获取所有反馈模板（合并原始和扩展）"""
    from .behavior_config import BEHAVIOR_FEEDBACK

    all_templates = {}

    # 转换原始模板格式
    for key, values in BEHAVIOR_FEEDBACK.items():
        if isinstance(values, list):
            all_templates[key] = {"cute": values}
        else:
            all_templates[key] = values

    # 合并扩展模板
    for key, values in EXTENDED_BEHAVIOR_FEEDBACK.items():
        if key in all_templates:
            # 合并
            for tone, templates in values.items():
                if tone not in all_templates[key]:
                    all_templates[key][tone] = []
                all_templates[key][tone].extend(templates)
        else:
            all_templates[key] = values

    return all_templates
