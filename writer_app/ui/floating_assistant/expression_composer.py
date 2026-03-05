"""
悬浮助手 - 表情组合管理器 (Expression Composer)
高级表情组合系统，支持情绪混合、过渡动画、上下文感知表情
"""
import random
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EmotionCategory(Enum):
    """情绪类别"""
    POSITIVE = "positive"       # 正面情绪
    NEGATIVE = "negative"       # 负面情绪
    NEUTRAL = "neutral"         # 中性情绪
    COMPLEX = "complex"         # 复杂情绪
    SPECIAL = "special"         # 特殊情绪


class ExpressionIntensity(Enum):
    """表情强度"""
    SUBTLE = "subtle"           # 微弱
    MILD = "mild"               # 轻微
    MODERATE = "moderate"       # 中等
    STRONG = "strong"           # 强烈
    EXTREME = "extreme"         # 极端


@dataclass
class EmotionDefinition:
    """情绪定义"""
    emotion_id: str
    name: str
    category: EmotionCategory
    base_expression: str           # 基础表情ID
    description: str = ""

    # 表情部件配置 (不同强度)
    intensity_variants: Dict[ExpressionIntensity, Dict[str, str]] = field(default_factory=dict)

    # 情绪特征
    valence: float = 0.0           # 效价 (-1 负面 ~ 1 正面)
    arousal: float = 0.5           # 唤醒度 (0 低 ~ 1 高)

    # 触发条件
    triggers: List[str] = field(default_factory=list)

    # 兼容的混合情绪
    compatible_mix: List[str] = field(default_factory=list)


@dataclass
class ExpressionTransition:
    """表情过渡"""
    from_expression: str
    to_expression: str
    duration: int = 300            # 过渡时长(毫秒)
    easing: str = "ease_in_out"    # 缓动函数
    intermediate_frames: List[str] = field(default_factory=list)


@dataclass
class MicroExpression:
    """微表情"""
    expression_id: str
    name: str
    parts: Dict[str, str]          # 部件ID映射
    duration: int = 200            # 持续时间(毫秒)
    probability: float = 0.1       # 出现概率
    triggers: List[str] = field(default_factory=list)


class ExpressionComposer:
    """
    表情组合管理器

    功能：
    1. 情绪到表情的映射
    2. 表情强度控制
    3. 混合表情生成
    4. 表情过渡动画
    5. 微表情系统
    6. 上下文感知表情
    """

    def __init__(self):
        # 情绪库
        self.emotions: Dict[str, EmotionDefinition] = {}

        # 过渡库
        self.transitions: Dict[str, ExpressionTransition] = {}

        # 微表情库
        self.micro_expressions: Dict[str, MicroExpression] = {}

        # 当前状态
        self.current_emotion: Optional[str] = None
        self.current_intensity: ExpressionIntensity = ExpressionIntensity.MODERATE
        self.emotion_stack: List[Tuple[str, float]] = []  # (emotion_id, weight)

        # 情绪历史 (用于趋势分析)
        self.emotion_history: List[Dict[str, Any]] = []
        self._history_max_size = 100

        # 回调
        self.on_emotion_change: Optional[Callable[[str, ExpressionIntensity], None]] = None
        self.on_micro_expression: Optional[Callable[[str], None]] = None

        # 初始化默认情绪
        self._init_default_emotions()
        self._init_default_transitions()
        self._init_micro_expressions()

    def _init_default_emotions(self):
        """初始化默认情绪库"""
        # 正面情绪
        self.emotions["happy"] = EmotionDefinition(
            emotion_id="happy",
            name="开心",
            category=EmotionCategory.POSITIVE,
            base_expression="happy",
            description="愉快、高兴的情绪",
            valence=0.8,
            arousal=0.6,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_soft", "mouth": "mouth_slight_smile"},
                ExpressionIntensity.MILD: {"eyes": "eyes_happy", "mouth": "mouth_smile"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_happy", "mouth": "mouth_smile", "blush": "blush_light"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_sparkle", "mouth": "mouth_big_smile", "blush": "blush_medium"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_sparkle", "mouth": "mouth_laugh", "blush": "blush_heavy", "effect": "sparkles"},
            },
            triggers=["praise", "achievement", "good_news", "gift"],
            compatible_mix=["excited", "grateful", "proud"]
        )

        self.emotions["excited"] = EmotionDefinition(
            emotion_id="excited",
            name="兴奋",
            category=EmotionCategory.POSITIVE,
            base_expression="excited",
            description="激动、期待的情绪",
            valence=0.9,
            arousal=0.9,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_bright", "mouth": "mouth_smile"},
                ExpressionIntensity.MILD: {"eyes": "eyes_sparkle", "mouth": "mouth_smile"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_sparkle", "mouth": "mouth_big_smile"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_sparkle", "mouth": "mouth_big_smile", "effect": "sparkles"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_star", "mouth": "mouth_open_smile", "effect": "explosion"},
            },
            triggers=["surprise_gift", "big_achievement", "special_event"],
            compatible_mix=["happy", "anticipation"]
        )

        self.emotions["love"] = EmotionDefinition(
            emotion_id="love",
            name="心动",
            category=EmotionCategory.POSITIVE,
            base_expression="love",
            description="喜爱、心动的情绪",
            valence=0.95,
            arousal=0.7,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_soft", "blush": "blush_light"},
                ExpressionIntensity.MILD: {"eyes": "eyes_loving", "mouth": "mouth_smile", "blush": "blush_light"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_heart", "mouth": "mouth_smile", "blush": "blush_medium"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_heart", "mouth": "mouth_smile", "blush": "blush_heavy"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_heart", "mouth": "mouth_smile", "blush": "blush_heavy", "effect": "hearts"},
            },
            triggers=["affection_high", "romantic_event", "confession"],
            compatible_mix=["happy", "shy"]
        )

        self.emotions["grateful"] = EmotionDefinition(
            emotion_id="grateful",
            name="感激",
            category=EmotionCategory.POSITIVE,
            base_expression="grateful",
            description="感谢、感恩的情绪",
            valence=0.7,
            arousal=0.4,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_soft", "mouth": "mouth_slight_smile"},
                ExpressionIntensity.MILD: {"eyes": "eyes_soft", "mouth": "mouth_smile"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_touched", "mouth": "mouth_smile"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_touched", "mouth": "mouth_smile", "tears": "tears_joy"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_cry_happy", "mouth": "mouth_smile", "tears": "tears_joy"},
            },
            triggers=["help_received", "gift", "kindness"],
            compatible_mix=["happy", "touched"]
        )

        self.emotions["proud"] = EmotionDefinition(
            emotion_id="proud",
            name="自豪",
            category=EmotionCategory.POSITIVE,
            base_expression="proud",
            description="骄傲、自豪的情绪",
            valence=0.7,
            arousal=0.5,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_confident", "mouth": "mouth_slight_smile"},
                ExpressionIntensity.MILD: {"eyes": "eyes_confident", "mouth": "mouth_smirk"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_confident", "mouth": "mouth_proud_smile"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_sparkle", "mouth": "mouth_proud_smile"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_sparkle", "mouth": "mouth_proud_smile", "effect": "shine"},
            },
            triggers=["achievement", "praise", "success"],
            compatible_mix=["happy", "confident"]
        )

        # 负面情绪
        self.emotions["sad"] = EmotionDefinition(
            emotion_id="sad",
            name="难过",
            category=EmotionCategory.NEGATIVE,
            base_expression="sad",
            description="悲伤、难过的情绪",
            valence=-0.7,
            arousal=0.3,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_downcast", "mouth": "mouth_flat"},
                ExpressionIntensity.MILD: {"eyes": "eyes_sad", "mouth": "mouth_down"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_sad", "mouth": "mouth_sad"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_teary", "mouth": "mouth_sad", "tears": "tears_light"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_crying", "mouth": "mouth_cry", "tears": "tears_heavy"},
            },
            triggers=["rejection", "failure", "bad_news", "goodbye"],
            compatible_mix=["disappointed", "lonely"]
        )

        self.emotions["angry"] = EmotionDefinition(
            emotion_id="angry",
            name="生气",
            category=EmotionCategory.NEGATIVE,
            base_expression="angry",
            description="愤怒、生气的情绪",
            valence=-0.8,
            arousal=0.8,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_narrowed", "eyebrows": "brows_slight_frown"},
                ExpressionIntensity.MILD: {"eyes": "eyes_annoyed", "eyebrows": "brows_frown", "mouth": "mouth_flat"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_angry", "eyebrows": "brows_angry", "mouth": "mouth_angry"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_angry", "eyebrows": "brows_angry", "mouth": "mouth_angry", "effect": "vein"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_furious", "eyebrows": "brows_angry", "mouth": "mouth_yell", "effect": "flames"},
            },
            triggers=["insult", "unfair", "repeated_mistake"],
            compatible_mix=["frustrated", "annoyed"]
        )

        self.emotions["scared"] = EmotionDefinition(
            emotion_id="scared",
            name="害怕",
            category=EmotionCategory.NEGATIVE,
            base_expression="scared",
            description="恐惧、害怕的情绪",
            valence=-0.6,
            arousal=0.8,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_wide", "mouth": "mouth_small"},
                ExpressionIntensity.MILD: {"eyes": "eyes_scared", "mouth": "mouth_small", "sweat": "sweat_light"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_scared", "mouth": "mouth_scared", "sweat": "sweat_medium"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_terrified", "mouth": "mouth_scared", "sweat": "sweat_heavy"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_terrified", "mouth": "mouth_scream", "sweat": "sweat_heavy", "effect": "shake"},
            },
            triggers=["horror", "threat", "sudden_scare"],
            compatible_mix=["anxious", "nervous"]
        )

        self.emotions["anxious"] = EmotionDefinition(
            emotion_id="anxious",
            name="焦虑",
            category=EmotionCategory.NEGATIVE,
            base_expression="anxious",
            description="焦虑、不安的情绪",
            valence=-0.4,
            arousal=0.6,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_uncertain", "mouth": "mouth_slight_frown"},
                ExpressionIntensity.MILD: {"eyes": "eyes_worried", "mouth": "mouth_worried"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_worried", "mouth": "mouth_worried", "sweat": "sweat_light"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_anxious", "mouth": "mouth_anxious", "sweat": "sweat_medium"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_panic", "mouth": "mouth_panic", "sweat": "sweat_heavy"},
            },
            triggers=["deadline", "uncertainty", "waiting"],
            compatible_mix=["nervous", "worried"]
        )

        # 中性情绪
        self.emotions["neutral"] = EmotionDefinition(
            emotion_id="neutral",
            name="平静",
            category=EmotionCategory.NEUTRAL,
            base_expression="neutral",
            description="平静、中性的状态",
            valence=0.0,
            arousal=0.3,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_relaxed", "mouth": "mouth_relaxed"},
                ExpressionIntensity.MILD: {"eyes": "eyes_normal", "mouth": "mouth_normal"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_normal", "mouth": "mouth_normal"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_normal", "mouth": "mouth_normal"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_normal", "mouth": "mouth_normal"},
            },
            triggers=["idle", "default"],
            compatible_mix=["calm", "content"]
        )

        self.emotions["thinking"] = EmotionDefinition(
            emotion_id="thinking",
            name="思考",
            category=EmotionCategory.NEUTRAL,
            base_expression="thinking",
            description="思考、沉思的状态",
            valence=0.1,
            arousal=0.4,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_side", "mouth": "mouth_normal"},
                ExpressionIntensity.MILD: {"eyes": "eyes_thinking", "mouth": "mouth_hmm"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_thinking", "mouth": "mouth_hmm", "eyebrows": "brows_thinking"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_deep_thought", "mouth": "mouth_hmm", "eyebrows": "brows_focused"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_deep_thought", "mouth": "mouth_concentrating", "effect": "question_marks"},
            },
            triggers=["question", "analysis", "planning"],
            compatible_mix=["curious", "focused"]
        )

        self.emotions["curious"] = EmotionDefinition(
            emotion_id="curious",
            name="好奇",
            category=EmotionCategory.NEUTRAL,
            base_expression="curious",
            description="好奇、感兴趣的状态",
            valence=0.3,
            arousal=0.5,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_interested", "mouth": "mouth_slight_open"},
                ExpressionIntensity.MILD: {"eyes": "eyes_curious", "mouth": "mouth_o"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_curious", "eyebrows": "brows_raised", "mouth": "mouth_o"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_wide_curious", "eyebrows": "brows_raised", "mouth": "mouth_wow"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_sparkle_curious", "eyebrows": "brows_raised", "mouth": "mouth_wow", "effect": "question_mark"},
            },
            triggers=["new_topic", "interesting_info", "mystery"],
            compatible_mix=["interested", "excited"]
        )

        # 特殊情绪
        self.emotions["shy"] = EmotionDefinition(
            emotion_id="shy",
            name="害羞",
            category=EmotionCategory.SPECIAL,
            base_expression="shy",
            description="害羞、羞涩的情绪",
            valence=0.2,
            arousal=0.5,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_averted", "blush": "blush_faint"},
                ExpressionIntensity.MILD: {"eyes": "eyes_shy", "mouth": "mouth_small", "blush": "blush_light"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_shy", "mouth": "mouth_embarrassed", "blush": "blush_medium"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_shy_hide", "mouth": "mouth_embarrassed", "blush": "blush_heavy"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_covered", "mouth": "mouth_embarrassed", "blush": "blush_heavy", "sweat": "sweat_light"},
            },
            triggers=["compliment", "attention", "intimate_topic"],
            compatible_mix=["embarrassed", "happy"]
        )

        self.emotions["surprised"] = EmotionDefinition(
            emotion_id="surprised",
            name="惊讶",
            category=EmotionCategory.SPECIAL,
            base_expression="surprised",
            description="惊讶、震惊的情绪",
            valence=0.0,
            arousal=0.9,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_widened", "mouth": "mouth_slight_open"},
                ExpressionIntensity.MILD: {"eyes": "eyes_wide", "mouth": "mouth_o"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_shocked", "mouth": "mouth_open"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_shocked", "mouth": "mouth_gasp"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_shocked", "mouth": "mouth_scream", "effect": "shock_lines"},
            },
            triggers=["unexpected", "revelation", "sudden_event"],
            compatible_mix=["confused", "scared", "happy"]
        )

        self.emotions["sleepy"] = EmotionDefinition(
            emotion_id="sleepy",
            name="困倦",
            category=EmotionCategory.SPECIAL,
            base_expression="sleepy",
            description="困倦、疲惫的状态",
            valence=-0.1,
            arousal=0.1,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_tired", "mouth": "mouth_normal"},
                ExpressionIntensity.MILD: {"eyes": "eyes_droopy", "mouth": "mouth_yawn_small"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_sleepy", "mouth": "mouth_yawn"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_half_closed", "mouth": "mouth_yawn"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_closed", "mouth": "mouth_sleeping", "effect": "zzz"},
            },
            triggers=["late_night", "long_session", "bored"],
            compatible_mix=["tired", "bored"]
        )

        self.emotions["determined"] = EmotionDefinition(
            emotion_id="determined",
            name="坚定",
            category=EmotionCategory.SPECIAL,
            base_expression="determined",
            description="决心、坚定的情绪",
            valence=0.4,
            arousal=0.7,
            intensity_variants={
                ExpressionIntensity.SUBTLE: {"eyes": "eyes_focused", "mouth": "mouth_firm"},
                ExpressionIntensity.MILD: {"eyes": "eyes_determined", "eyebrows": "brows_firm", "mouth": "mouth_firm"},
                ExpressionIntensity.MODERATE: {"eyes": "eyes_determined", "eyebrows": "brows_firm", "mouth": "mouth_determined"},
                ExpressionIntensity.STRONG: {"eyes": "eyes_burning", "eyebrows": "brows_firm", "mouth": "mouth_determined"},
                ExpressionIntensity.EXTREME: {"eyes": "eyes_fire", "eyebrows": "brows_firm", "mouth": "mouth_determined", "effect": "flames"},
            },
            triggers=["challenge", "goal_set", "encouragement"],
            compatible_mix=["confident", "excited"]
        )

    def _init_default_transitions(self):
        """初始化默认过渡"""
        # 常见的表情过渡
        common_transitions = [
            ("neutral", "happy", 250),
            ("neutral", "sad", 350),
            ("neutral", "surprised", 150),
            ("happy", "neutral", 300),
            ("happy", "excited", 200),
            ("happy", "love", 400),
            ("sad", "neutral", 400),
            ("sad", "happy", 500),
            ("angry", "neutral", 600),
            ("surprised", "happy", 200),
            ("surprised", "scared", 150),
            ("shy", "happy", 300),
            ("thinking", "excited", 250),
        ]

        for from_expr, to_expr, duration in common_transitions:
            key = f"{from_expr}_to_{to_expr}"
            self.transitions[key] = ExpressionTransition(
                from_expression=from_expr,
                to_expression=to_expr,
                duration=duration
            )

    def _init_micro_expressions(self):
        """初始化微表情"""
        self.micro_expressions = {
            "glance_away": MicroExpression(
                expression_id="glance_away",
                name="看向别处",
                parts={"eyes": "eyes_side"},
                duration=150,
                probability=0.05,
                triggers=["shy", "thinking"]
            ),
            "blink": MicroExpression(
                expression_id="blink",
                name="眨眼",
                parts={"eyes": "eyes_closed"},
                duration=100,
                probability=0.2,
                triggers=["any"]
            ),
            "lip_bite": MicroExpression(
                expression_id="lip_bite",
                name="咬唇",
                parts={"mouth": "mouth_bite"},
                duration=200,
                probability=0.03,
                triggers=["nervous", "thinking", "anxious"]
            ),
            "nose_scrunch": MicroExpression(
                expression_id="nose_scrunch",
                name="皱鼻",
                parts={"nose": "nose_scrunch"},
                duration=180,
                probability=0.02,
                triggers=["annoyed", "disgusted"]
            ),
            "eyebrow_raise": MicroExpression(
                expression_id="eyebrow_raise",
                name="挑眉",
                parts={"eyebrows": "brows_raised_one"},
                duration=250,
                probability=0.04,
                triggers=["curious", "skeptical", "surprised"]
            ),
        }

    def set_emotion(self, emotion_id: str, intensity: ExpressionIntensity = None) -> bool:
        """设置当前情绪"""
        if emotion_id not in self.emotions:
            logger.warning(f"未知情绪: {emotion_id}")
            return False

        old_emotion = self.current_emotion
        self.current_emotion = emotion_id

        if intensity:
            self.current_intensity = intensity

        # 记录历史
        self._record_emotion(emotion_id, intensity or self.current_intensity)

        # 触发回调
        if self.on_emotion_change:
            self.on_emotion_change(emotion_id, self.current_intensity)

        return True

    def set_intensity(self, intensity: ExpressionIntensity):
        """设置表情强度"""
        self.current_intensity = intensity

        if self.on_emotion_change and self.current_emotion:
            self.on_emotion_change(self.current_emotion, intensity)

    def _record_emotion(self, emotion_id: str, intensity: ExpressionIntensity):
        """记录情绪历史"""
        record = {
            "emotion": emotion_id,
            "intensity": intensity.value,
            "timestamp": time.time()
        }

        self.emotion_history.append(record)

        # 限制历史大小
        if len(self.emotion_history) > self._history_max_size:
            self.emotion_history = self.emotion_history[-self._history_max_size:]

    def get_expression_parts(self, emotion_id: str = None,
                            intensity: ExpressionIntensity = None) -> Dict[str, str]:
        """获取表情部件配置"""
        emotion_id = emotion_id or self.current_emotion
        intensity = intensity or self.current_intensity

        if not emotion_id or emotion_id not in self.emotions:
            return {}

        emotion = self.emotions[emotion_id]

        # 获取对应强度的部件配置
        if intensity in emotion.intensity_variants:
            return emotion.intensity_variants[intensity].copy()

        # 回退到MODERATE
        if ExpressionIntensity.MODERATE in emotion.intensity_variants:
            return emotion.intensity_variants[ExpressionIntensity.MODERATE].copy()

        return {}

    def mix_emotions(self, emotions: List[Tuple[str, float]]) -> Dict[str, str]:
        """
        混合多个情绪生成表情

        Args:
            emotions: [(emotion_id, weight), ...] 情绪及权重列表

        Returns:
            混合后的表情部件配置
        """
        if not emotions:
            return {}

        # 标准化权重
        total_weight = sum(w for _, w in emotions)
        if total_weight == 0:
            return {}

        normalized = [(e, w / total_weight) for e, w in emotions]

        # 按权重排序，取最高的作为基础
        normalized.sort(key=lambda x: x[1], reverse=True)

        primary_emotion, primary_weight = normalized[0]

        # 基础表情
        result = self.get_expression_parts(primary_emotion)

        # 混合次要情绪的特征
        if len(normalized) > 1:
            secondary_emotion, secondary_weight = normalized[1]

            # 检查是否兼容
            primary_def = self.emotions.get(primary_emotion)
            if primary_def and secondary_emotion in primary_def.compatible_mix:
                secondary_parts = self.get_expression_parts(secondary_emotion)

                # 根据权重决定是否覆盖某些部件
                if secondary_weight > 0.3:
                    # 混合腮红和特效
                    if "blush" in secondary_parts:
                        result["blush"] = secondary_parts["blush"]
                    if "effect" in secondary_parts:
                        result["effect"] = secondary_parts["effect"]

        return result

    def push_emotion(self, emotion_id: str, weight: float = 1.0):
        """压入情绪到栈"""
        self.emotion_stack.append((emotion_id, weight))
        # 重新计算混合
        self._update_from_stack()

    def pop_emotion(self) -> Optional[Tuple[str, float]]:
        """弹出最近的情绪"""
        if self.emotion_stack:
            result = self.emotion_stack.pop()
            self._update_from_stack()
            return result
        return None

    def clear_emotion_stack(self):
        """清空情绪栈"""
        self.emotion_stack.clear()
        self.current_emotion = "neutral"
        self.current_intensity = ExpressionIntensity.MODERATE

    def _update_from_stack(self):
        """根据情绪栈更新当前状态"""
        if not self.emotion_stack:
            self.current_emotion = "neutral"
            return

        # 取最后压入的情绪作为当前情绪
        self.current_emotion = self.emotion_stack[-1][0]

    def get_transition(self, from_emotion: str, to_emotion: str) -> Optional[ExpressionTransition]:
        """获取过渡配置"""
        key = f"{from_emotion}_to_{to_emotion}"
        return self.transitions.get(key)

    def should_show_micro_expression(self, trigger: str = None) -> Optional[MicroExpression]:
        """
        检查是否应该显示微表情

        Args:
            trigger: 触发条件

        Returns:
            如果应该显示，返回微表情定义；否则返回None
        """
        for micro_id, micro in self.micro_expressions.items():
            # 检查触发条件
            if trigger:
                if "any" not in micro.triggers and trigger not in micro.triggers:
                    continue

            # 概率检查
            if random.random() < micro.probability:
                if self.on_micro_expression:
                    self.on_micro_expression(micro_id)
                return micro

        return None

    def get_emotion_from_context(self, context: Dict[str, Any]) -> Tuple[str, ExpressionIntensity]:
        """
        根据上下文推断情绪

        Args:
            context: 包含各种上下文信息的字典

        Returns:
            (emotion_id, intensity)
        """
        # 检查各种上下文因素
        affection = context.get("affection", 50)
        mood = context.get("mood", 50)
        time_of_day = context.get("time_of_day", "day")
        recent_event = context.get("recent_event", None)
        writing_progress = context.get("writing_progress", 0)

        # 基于最近事件
        if recent_event:
            event_emotion_map = {
                "praise": ("happy", ExpressionIntensity.STRONG),
                "achievement": ("excited", ExpressionIntensity.STRONG),
                "gift": ("love", ExpressionIntensity.MODERATE),
                "failure": ("sad", ExpressionIntensity.MODERATE),
                "long_idle": ("sleepy", ExpressionIntensity.MILD),
                "question": ("thinking", ExpressionIntensity.MODERATE),
            }

            if recent_event in event_emotion_map:
                return event_emotion_map[recent_event]

        # 基于好感度
        if affection >= 90:
            return ("love", ExpressionIntensity.MODERATE)
        elif affection >= 70:
            return ("happy", ExpressionIntensity.MODERATE)
        elif affection <= 20:
            return ("sad", ExpressionIntensity.MILD)

        # 基于心情
        if mood >= 80:
            return ("happy", ExpressionIntensity.MILD)
        elif mood <= 30:
            return ("sad", ExpressionIntensity.MILD)

        # 基于时间
        if time_of_day == "night":
            return ("sleepy", ExpressionIntensity.SUBTLE)

        # 基于写作进度
        if writing_progress >= 100:
            return ("proud", ExpressionIntensity.MODERATE)

        # 默认
        return ("neutral", ExpressionIntensity.MODERATE)

    def get_emotion_trend(self) -> Dict[str, Any]:
        """分析情绪趋势"""
        if not self.emotion_history:
            return {"trend": "stable", "dominant": "neutral"}

        # 统计各情绪出现次数
        emotion_counts: Dict[str, int] = {}
        for record in self.emotion_history[-20:]:  # 最近20条
            emotion = record["emotion"]
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        # 找出主导情绪
        dominant = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"

        # 分析趋势
        if len(self.emotion_history) >= 5:
            recent = self.emotion_history[-5:]
            older = self.emotion_history[-10:-5] if len(self.emotion_history) >= 10 else []

            recent_valence = sum(
                self.emotions.get(r["emotion"], EmotionDefinition("", "", EmotionCategory.NEUTRAL, "")).valence
                for r in recent
            ) / len(recent)

            if older:
                older_valence = sum(
                    self.emotions.get(r["emotion"], EmotionDefinition("", "", EmotionCategory.NEUTRAL, "")).valence
                    for r in older
                ) / len(older)

                if recent_valence > older_valence + 0.2:
                    trend = "improving"
                elif recent_valence < older_valence - 0.2:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "dominant": dominant,
            "counts": emotion_counts,
            "recent_valence": recent_valence if len(self.emotion_history) >= 5 else None
        }

    def get_all_emotions(self) -> List[Dict[str, Any]]:
        """获取所有可用情绪"""
        return [
            {
                "id": emotion.emotion_id,
                "name": emotion.name,
                "category": emotion.category.value,
                "valence": emotion.valence,
                "arousal": emotion.arousal
            }
            for emotion in self.emotions.values()
        ]


class ContextAwareExpressionManager:
    """
    上下文感知表情管理器

    根据各种上下文自动调整表情
    """

    def __init__(self, composer: ExpressionComposer):
        self.composer = composer

        # 上下文状态
        self.current_context: Dict[str, Any] = {}

        # 自动更新配置
        self.auto_update_enabled = True
        self.update_interval = 30.0  # 秒
        self._last_update_time = 0.0

    def update_context(self, **kwargs):
        """更新上下文"""
        self.current_context.update(kwargs)

        if self.auto_update_enabled:
            self._try_auto_update()

    def _try_auto_update(self):
        """尝试自动更新表情"""
        current_time = time.time()

        if current_time - self._last_update_time < self.update_interval:
            return

        self._last_update_time = current_time

        # 根据上下文推断情绪
        emotion, intensity = self.composer.get_emotion_from_context(self.current_context)
        self.composer.set_emotion(emotion, intensity)

    def force_update(self):
        """强制更新表情"""
        emotion, intensity = self.composer.get_emotion_from_context(self.current_context)
        self.composer.set_emotion(emotion, intensity)
        self._last_update_time = time.time()

    def trigger_event(self, event_type: str, **event_data):
        """触发事件"""
        self.current_context["recent_event"] = event_type
        self.current_context.update(event_data)

        # 事件触发立即更新
        self.force_update()

        # 检查微表情
        micro = self.composer.should_show_micro_expression(event_type)
        if micro:
            return micro

        return None
