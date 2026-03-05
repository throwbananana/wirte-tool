"""
悬浮助手 - 用户偏好学习系统 (User Preference Learning System)
追踪用户偏好，提供个性化内容和自适应交互
"""
import time
import json
import random
import math
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum


class InteractionStyle(Enum):
    """交互风格"""
    CASUAL = "casual"           # 轻松随意
    PROFESSIONAL = "professional"  # 专业正式
    PLAYFUL = "playful"         # 活泼可爱
    MINIMAL = "minimal"         # 极简低频
    SUPPORTIVE = "supportive"   # 鼓励支持


class ContentTone(Enum):
    """内容语气"""
    HUMOROUS = "humorous"       # 幽默
    SERIOUS = "serious"         # 严肃
    ENCOURAGING = "encouraging"  # 鼓励
    ANALYTICAL = "analytical"   # 分析性
    EMOTIONAL = "emotional"     # 情感化


@dataclass
class UserPreferences:
    """用户偏好数据"""
    # 交互偏好
    interaction_style: str = "casual"
    preferred_response_length: str = "medium"  # short, medium, long
    notification_frequency: str = "normal"  # low, normal, high

    # 时间偏好
    active_time_preference: str = "flexible"  # morning, afternoon, evening, night, flexible
    peak_hours: List[int] = field(default_factory=lambda: list(range(9, 22)))

    # 内容偏好
    likes_humor: float = 0.5            # 0-1, 喜欢幽默程度
    likes_detailed_feedback: float = 0.5  # 0-1, 喜欢详细反馈程度
    likes_encouragement: float = 0.7     # 0-1, 喜欢鼓励程度
    likes_analysis: float = 0.5          # 0-1, 喜欢分析性内容程度
    likes_proactive: float = 0.5         # 0-1, 接受主动干预程度

    # 题材偏好
    genre_affinity: Dict[str, float] = field(default_factory=dict)

    # 功能使用偏好
    feature_preferences: Dict[str, float] = field(default_factory=dict)

    # 叙事偏好
    narrative_preferences: Dict[str, float] = field(default_factory=dict)

    # 元数据
    total_interactions: int = 0
    last_updated: float = 0.0


@dataclass
class InteractionRecord:
    """交互记录"""
    timestamp: float
    content_type: str  # narrative, feedback, suggestion, etc.
    content_id: str
    user_action: str  # clicked, dismissed, selected, ignored
    duration: float = 0.0  # 用户查看时长（秒）
    context: Dict[str, Any] = field(default_factory=dict)


class UserPreferenceTracker:
    """用户偏好追踪器：学习和预测用户偏好"""

    # 学习率
    LEARNING_RATE = 0.1
    # 衰减因子（旧数据权重降低）
    DECAY_FACTOR = 0.95

    def __init__(self, data_dir: Optional[str] = None):
        self.preferences = UserPreferences()
        self.interaction_history: List[InteractionRecord] = []
        self.session_start = time.time()

        # 临时统计
        self._content_exposures: Counter = Counter()  # 内容展示次数
        self._content_clicks: Counter = Counter()     # 内容点击次数
        self._content_durations: Dict[str, List[float]] = defaultdict(list)

        # 持久化
        self.data_dir = Path(data_dir) if data_dir else None
        self._load_state()

    def _load_state(self):
        """加载持久化状态"""
        if not self.data_dir:
            return

        state_file = self.data_dir / "user_preferences.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # 恢复偏好
                    prefs = data.get("preferences", {})
                    self.preferences.interaction_style = prefs.get("interaction_style", "casual")
                    self.preferences.preferred_response_length = prefs.get("preferred_response_length", "medium")
                    self.preferences.notification_frequency = prefs.get("notification_frequency", "normal")
                    self.preferences.active_time_preference = prefs.get("active_time_preference", "flexible")
                    self.preferences.peak_hours = prefs.get("peak_hours", list(range(9, 22)))
                    self.preferences.likes_humor = prefs.get("likes_humor", 0.5)
                    self.preferences.likes_detailed_feedback = prefs.get("likes_detailed_feedback", 0.5)
                    self.preferences.likes_encouragement = prefs.get("likes_encouragement", 0.7)
                    self.preferences.likes_analysis = prefs.get("likes_analysis", 0.5)
                    self.preferences.likes_proactive = prefs.get("likes_proactive", 0.5)
                    self.preferences.genre_affinity = prefs.get("genre_affinity", {})
                    self.preferences.feature_preferences = prefs.get("feature_preferences", {})
                    self.preferences.narrative_preferences = prefs.get("narrative_preferences", {})
                    self.preferences.total_interactions = prefs.get("total_interactions", 0)
                    self.preferences.last_updated = prefs.get("last_updated", 0)

                    # 恢复统计
                    self._content_exposures = Counter(data.get("content_exposures", {}))
                    self._content_clicks = Counter(data.get("content_clicks", {}))

            except Exception:
                pass

    def _save_state(self):
        """保存状态"""
        if not self.data_dir:
            return

        self.data_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.data_dir / "user_preferences.json"

        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "preferences": {
                        "interaction_style": self.preferences.interaction_style,
                        "preferred_response_length": self.preferences.preferred_response_length,
                        "notification_frequency": self.preferences.notification_frequency,
                        "active_time_preference": self.preferences.active_time_preference,
                        "peak_hours": self.preferences.peak_hours,
                        "likes_humor": self.preferences.likes_humor,
                        "likes_detailed_feedback": self.preferences.likes_detailed_feedback,
                        "likes_encouragement": self.preferences.likes_encouragement,
                        "likes_analysis": self.preferences.likes_analysis,
                        "likes_proactive": self.preferences.likes_proactive,
                        "genre_affinity": self.preferences.genre_affinity,
                        "feature_preferences": self.preferences.feature_preferences,
                        "narrative_preferences": self.preferences.narrative_preferences,
                        "total_interactions": self.preferences.total_interactions,
                        "last_updated": self.preferences.last_updated,
                    },
                    "content_exposures": dict(self._content_exposures),
                    "content_clicks": dict(self._content_clicks),
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def record_interaction(self, content_type: str, content_id: str,
                          action: str, duration: float = 0.0,
                          context: Optional[Dict] = None):
        """
        记录用户交互

        Args:
            content_type: 内容类型 (narrative, feedback, suggestion, tool, etc.)
            content_id: 内容标识
            action: 用户动作 (clicked, dismissed, selected, ignored, completed)
            duration: 查看时长
            context: 额外上下文
        """
        record = InteractionRecord(
            timestamp=time.time(),
            content_type=content_type,
            content_id=content_id,
            user_action=action,
            duration=duration,
            context=context or {}
        )
        self.interaction_history.append(record)

        # 更新统计
        self._content_exposures[content_id] += 1
        if action in ("clicked", "selected", "completed"):
            self._content_clicks[content_id] += 1

        if duration > 0:
            self._content_durations[content_id].append(duration)

        # 学习偏好
        self._learn_from_interaction(record)

        self.preferences.total_interactions += 1
        self.preferences.last_updated = time.time()

        # 定期保存
        if len(self.interaction_history) % 10 == 0:
            self._save_state()

    def _learn_from_interaction(self, record: InteractionRecord):
        """从交互中学习偏好"""
        action = record.user_action
        content_type = record.content_type
        content_id = record.content_id
        context = record.context

        # 正面反馈权重
        positive_weight = 1.0 if action in ("clicked", "selected", "completed") else -0.5
        if action == "ignored":
            positive_weight = -0.3
        if action == "dismissed":
            positive_weight = -0.7

        # 学习内容偏好
        lr = self.LEARNING_RATE

        # 叙事偏好
        if content_type == "narrative":
            chain_id = context.get("chain_id", content_id)
            current = self.preferences.narrative_preferences.get(chain_id, 0.5)
            new_value = current + lr * positive_weight * (1.0 - current if positive_weight > 0 else current)
            self.preferences.narrative_preferences[chain_id] = max(0.0, min(1.0, new_value))

        # 功能偏好
        elif content_type == "tool":
            tool_id = context.get("tool_id", content_id)
            current = self.preferences.feature_preferences.get(tool_id, 0.5)
            new_value = current + lr * positive_weight * (1.0 - current if positive_weight > 0 else current)
            self.preferences.feature_preferences[tool_id] = max(0.0, min(1.0, new_value))

        # 反馈偏好
        elif content_type == "feedback":
            feedback_type = context.get("feedback_type", "general")

            if "humor" in feedback_type or context.get("is_humorous"):
                self.preferences.likes_humor += lr * positive_weight * 0.3
                self.preferences.likes_humor = max(0.0, min(1.0, self.preferences.likes_humor))

            if "detailed" in feedback_type or context.get("is_detailed"):
                self.preferences.likes_detailed_feedback += lr * positive_weight * 0.3
                self.preferences.likes_detailed_feedback = max(0.0, min(1.0, self.preferences.likes_detailed_feedback))

            if "encouragement" in feedback_type or context.get("is_encouraging"):
                self.preferences.likes_encouragement += lr * positive_weight * 0.3
                self.preferences.likes_encouragement = max(0.0, min(1.0, self.preferences.likes_encouragement))

            if "analysis" in feedback_type or context.get("is_analytical"):
                self.preferences.likes_analysis += lr * positive_weight * 0.3
                self.preferences.likes_analysis = max(0.0, min(1.0, self.preferences.likes_analysis))

        # 主动干预偏好
        elif content_type == "proactive":
            self.preferences.likes_proactive += lr * positive_weight * 0.5
            self.preferences.likes_proactive = max(0.0, min(1.0, self.preferences.likes_proactive))

        # 题材偏好
        genre = context.get("genre") or context.get("project_type")
        if genre:
            current = self.preferences.genre_affinity.get(genre, 0.5)
            new_value = current + lr * positive_weight * 0.2
            self.preferences.genre_affinity[genre] = max(0.0, min(1.0, new_value))

    def update_time_preference(self):
        """更新时间偏好（基于活跃时间统计）"""
        if not self.interaction_history:
            return

        # 统计每小时的活跃度
        hourly_activity = Counter()
        for record in self.interaction_history[-200:]:
            hour = datetime.fromtimestamp(record.timestamp).hour
            hourly_activity[hour] += 1

        if not hourly_activity:
            return

        # 找出高峰时段
        total = sum(hourly_activity.values())
        avg = total / 24

        self.preferences.peak_hours = [
            hour for hour, count in hourly_activity.items()
            if count > avg * 1.2
        ]

        # 判断时间偏好类型
        morning_activity = sum(hourly_activity.get(h, 0) for h in range(5, 12))
        afternoon_activity = sum(hourly_activity.get(h, 0) for h in range(12, 18))
        evening_activity = sum(hourly_activity.get(h, 0) for h in range(18, 22))
        night_activity = sum(hourly_activity.get(h, 0) for h in list(range(22, 24)) + list(range(0, 5)))

        max_activity = max(morning_activity, afternoon_activity, evening_activity, night_activity)

        if max_activity == morning_activity and morning_activity > total * 0.4:
            self.preferences.active_time_preference = "morning"
        elif max_activity == afternoon_activity and afternoon_activity > total * 0.4:
            self.preferences.active_time_preference = "afternoon"
        elif max_activity == evening_activity and evening_activity > total * 0.4:
            self.preferences.active_time_preference = "evening"
        elif max_activity == night_activity and night_activity > total * 0.4:
            self.preferences.active_time_preference = "night"
        else:
            self.preferences.active_time_preference = "flexible"

    def get_content_ctr(self, content_id: str) -> float:
        """获取内容点击率"""
        exposures = self._content_exposures.get(content_id, 0)
        if exposures == 0:
            return 0.5  # 默认值
        clicks = self._content_clicks.get(content_id, 0)
        return clicks / exposures

    def get_content_engagement(self, content_id: str) -> float:
        """获取内容参与度（基于时长）"""
        durations = self._content_durations.get(content_id, [])
        if not durations:
            return 0.5

        avg_duration = sum(durations) / len(durations)
        # 假设5秒是基准阅读时长
        return min(1.0, avg_duration / 5.0)

    def get_narrative_preference(self, chain_id: str) -> float:
        """获取对特定叙事链的偏好度"""
        return self.preferences.narrative_preferences.get(chain_id, 0.5)

    def get_feature_preference(self, feature_id: str) -> float:
        """获取对特定功能的偏好度"""
        return self.preferences.feature_preferences.get(feature_id, 0.5)

    def get_genre_preference(self, genre: str) -> float:
        """获取对特定题材的偏好度"""
        return self.preferences.genre_affinity.get(genre, 0.5)

    def should_show_proactive_content(self) -> bool:
        """是否应该显示主动内容"""
        # 考虑用户对主动干预的接受度
        if self.preferences.likes_proactive < 0.3:
            return False

        # 考虑当前是否在活跃时段
        current_hour = datetime.now().hour
        if self.preferences.peak_hours and current_hour not in self.preferences.peak_hours:
            # 非高峰时段，降低主动干预概率
            return random.random() < 0.3

        return True

    def get_preferred_tone(self) -> ContentTone:
        """获取用户偏好的内容语气"""
        tones = [
            (ContentTone.HUMOROUS, self.preferences.likes_humor),
            (ContentTone.ANALYTICAL, self.preferences.likes_analysis),
            (ContentTone.ENCOURAGING, self.preferences.likes_encouragement),
        ]

        # 返回偏好度最高的语气
        tones.sort(key=lambda x: x[1], reverse=True)
        return tones[0][0]

    def get_preferred_length(self) -> str:
        """获取用户偏好的内容长度"""
        if self.preferences.likes_detailed_feedback > 0.7:
            return "long"
        elif self.preferences.likes_detailed_feedback < 0.3:
            return "short"
        return "medium"


class AdaptiveContentSelector:
    """自适应内容选择器：根据用户偏好选择最合适的内容"""

    def __init__(self, preference_tracker: UserPreferenceTracker):
        self.tracker = preference_tracker

    def select_narrative(self, candidates: List[Dict[str, Any]],
                        context: Optional[Dict] = None) -> Optional[Dict]:
        """
        从候选叙事链中选择最合适的

        Args:
            candidates: 候选叙事链列表，每个包含 id, priority, etc.
            context: 当前上下文

        Returns:
            选中的叙事链或 None
        """
        if not candidates:
            return None

        context = context or {}
        scored_candidates = []

        for candidate in candidates:
            score = self._score_narrative(candidate, context)
            scored_candidates.append((candidate, score))

        # 按分数排序
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # 使用softmax选择（有一定随机性，避免总是选同一个）
        if len(scored_candidates) > 1:
            scores = [s for _, s in scored_candidates]
            probs = self._softmax(scores, temperature=0.5)

            # 加权随机选择
            r = random.random()
            cumsum = 0
            for i, prob in enumerate(probs):
                cumsum += prob
                if r <= cumsum:
                    return scored_candidates[i][0]

        return scored_candidates[0][0]

    def _score_narrative(self, narrative: Dict, context: Dict) -> float:
        """计算叙事链的适合度分数"""
        score = 0.0

        chain_id = narrative.get("id", "")

        # 基础优先级
        score += narrative.get("priority", 50) / 100.0

        # 用户偏好
        pref = self.tracker.get_narrative_preference(chain_id)
        score += pref * 0.3

        # 点击率历史
        ctr = self.tracker.get_content_ctr(chain_id)
        score += ctr * 0.2

        # 题材匹配
        genre = context.get("project_type")
        if genre:
            genre_pref = self.tracker.get_genre_preference(genre)
            if narrative.get("genre") == genre:
                score += genre_pref * 0.2

        # 时间匹配
        current_hour = datetime.now().hour
        if current_hour in self.tracker.preferences.peak_hours:
            score += 0.1  # 高峰时段加分

        return score

    def select_feedback_variant(self, feedback_templates: List[str],
                                context: Optional[Dict] = None) -> str:
        """
        从反馈模板中选择最合适的变体

        Args:
            feedback_templates: 候选反馈文案列表
            context: 上下文信息

        Returns:
            选中的反馈文案
        """
        if not feedback_templates:
            return ""

        if len(feedback_templates) == 1:
            return feedback_templates[0]

        context = context or {}
        scored = []

        for template in feedback_templates:
            score = self._score_feedback(template, context)
            scored.append((template, score))

        # softmax 选择
        scores = [s for _, s in scored]
        probs = self._softmax(scores, temperature=0.7)

        r = random.random()
        cumsum = 0
        for i, prob in enumerate(probs):
            cumsum += prob
            if r <= cumsum:
                return scored[i][0]

        return scored[0][0]

    def _score_feedback(self, template: str, context: Dict) -> float:
        """计算反馈文案的适合度分数"""
        score = 0.5
        prefs = self.tracker.preferences

        # 检测文案特征
        is_humorous = any(c in template for c in ["~", "！", "嘿嘿", "哈哈", "呢"])
        is_detailed = len(template) > 50
        is_encouraging = any(w in template for w in ["加油", "太棒", "厉害", "继续", "坚持"])
        is_analytical = any(w in template for w in ["分析", "建议", "可以试试", "考虑"])

        # 根据偏好调整分数
        if is_humorous:
            score += (prefs.likes_humor - 0.5) * 0.3
        if is_detailed:
            score += (prefs.likes_detailed_feedback - 0.5) * 0.3
        if is_encouraging:
            score += (prefs.likes_encouragement - 0.5) * 0.3
        if is_analytical:
            score += (prefs.likes_analysis - 0.5) * 0.3

        return max(0.1, score)

    def _softmax(self, scores: List[float], temperature: float = 1.0) -> List[float]:
        """Softmax 函数，temperature 控制随机性"""
        if not scores:
            return []

        # 防止溢出
        max_score = max(scores)
        exp_scores = [math.exp((s - max_score) / temperature) for s in scores]
        total = sum(exp_scores)

        if total == 0:
            return [1.0 / len(scores)] * len(scores)

        return [e / total for e in exp_scores]

    def adapt_message(self, message: str, context: Optional[Dict] = None) -> str:
        """
        根据用户偏好调整消息

        Args:
            message: 原始消息
            context: 上下文

        Returns:
            调整后的消息
        """
        prefs = self.tracker.preferences

        # 根据偏好长度调整
        length_pref = self.tracker.get_preferred_length()

        if length_pref == "short" and len(message) > 50:
            # 尝试缩短（保留第一句）
            sentences = message.split("。")
            if len(sentences) > 1:
                message = sentences[0] + "。"

        # 根据语气偏好调整
        tone = self.tracker.get_preferred_tone()

        if tone == ContentTone.ENCOURAGING and prefs.likes_encouragement > 0.7:
            # 添加鼓励性后缀
            if not any(w in message for w in ["加油", "继续", "坚持"]):
                suffixes = ["加油！", "继续保持！", "你很棒！"]
                message = message.rstrip("。！") + "，" + random.choice(suffixes)

        return message

    def should_interrupt(self, event_type: str, urgency: float = 0.5) -> bool:
        """
        判断是否应该打断用户

        Args:
            event_type: 事件类型
            urgency: 紧急程度 (0-1)

        Returns:
            是否应该打断
        """
        prefs = self.tracker.preferences

        # 极简模式：只响应高紧急度事件
        if prefs.notification_frequency == "low":
            return urgency > 0.8

        # 正常模式
        if prefs.notification_frequency == "normal":
            return urgency > 0.4

        # 高频模式
        return urgency > 0.2


class PersonalizationEngine:
    """个性化引擎：统一管理用户偏好和内容选择"""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else None
        self.tracker = UserPreferenceTracker(data_dir)
        self.selector = AdaptiveContentSelector(self.tracker)

    def record(self, content_type: str, content_id: str,
              action: str, duration: float = 0.0,
              context: Optional[Dict] = None):
        """记录用户交互"""
        self.tracker.record_interaction(content_type, content_id, action, duration, context)

    def select_best_content(self, candidates: List[Dict],
                           content_type: str = "narrative",
                           context: Optional[Dict] = None) -> Optional[Dict]:
        """选择最佳内容"""
        if content_type == "narrative":
            return self.selector.select_narrative(candidates, context)
        return candidates[0] if candidates else None

    def adapt_message(self, message: str, context: Optional[Dict] = None) -> str:
        """调整消息"""
        return self.selector.adapt_message(message, context)

    def get_user_profile(self) -> Dict[str, Any]:
        """获取用户画像"""
        prefs = self.tracker.preferences

        return {
            "interaction_style": prefs.interaction_style,
            "active_time": prefs.active_time_preference,
            "peak_hours": prefs.peak_hours,
            "preferences": {
                "humor": prefs.likes_humor,
                "detail": prefs.likes_detailed_feedback,
                "encouragement": prefs.likes_encouragement,
                "analysis": prefs.likes_analysis,
                "proactive": prefs.likes_proactive,
            },
            "genre_affinity": prefs.genre_affinity,
            "total_interactions": prefs.total_interactions,
            "preferred_tone": self.tracker.get_preferred_tone().value,
            "preferred_length": self.tracker.get_preferred_length(),
        }

    def is_good_time_to_engage(self) -> bool:
        """当前是否适合主动互动"""
        return self.tracker.should_show_proactive_content()

    def should_show_notification(self, urgency: float = 0.5) -> bool:
        """是否应该显示通知"""
        return self.selector.should_interrupt("notification", urgency)

    def save(self):
        """保存状态"""
        self.tracker._save_state()

    def load_state(self, state: Dict[str, Any]) -> None:
        """从字典加载状态 (用于从 pet_system 恢复)"""
        if not state:
            return

        prefs = state.get("preferences", {})
        if prefs:
            self.tracker.preferences.interaction_style = prefs.get("interaction_style", "casual")
            self.tracker.preferences.likes_humor = prefs.get("likes_humor", 0.5)
            self.tracker.preferences.likes_detailed_feedback = prefs.get("likes_detailed_feedback", 0.5)
            self.tracker.preferences.likes_encouragement = prefs.get("likes_encouragement", 0.7)
            self.tracker.preferences.likes_analysis = prefs.get("likes_analysis", 0.5)
            self.tracker.preferences.likes_proactive = prefs.get("likes_proactive", 0.5)
            self.tracker.preferences.genre_affinity = prefs.get("genre_affinity", {})
            self.tracker.preferences.feature_preferences = prefs.get("feature_preferences", {})
            self.tracker.preferences.total_interactions = prefs.get("total_interactions", 0)

    def get_state(self) -> Dict[str, Any]:
        """获取可序列化的状态字典 (用于 pet_system 持久化)"""
        prefs = self.tracker.preferences
        return {
            "preferences": {
                "interaction_style": prefs.interaction_style,
                "likes_humor": prefs.likes_humor,
                "likes_detailed_feedback": prefs.likes_detailed_feedback,
                "likes_encouragement": prefs.likes_encouragement,
                "likes_analysis": prefs.likes_analysis,
                "likes_proactive": prefs.likes_proactive,
                "genre_affinity": dict(prefs.genre_affinity),
                "feature_preferences": dict(prefs.feature_preferences),
                "total_interactions": prefs.total_interactions,
            }
        }

    def get_preferences(self) -> Dict[str, Any]:
        """获取用户偏好 (简化接口)"""
        return self.get_user_profile()

    def record_interaction(self, interaction_type: str, context: Dict = None) -> None:
        """记录交互 (简化接口，兼容 event_system 调用)"""
        context = context or {}
        content_id = context.get("content_id", interaction_type)
        action = context.get("action", "triggered")
        self.record(interaction_type, content_id, action, context=context)

    def update_preference(self, key: str, value: Any) -> None:
        """更新单个偏好值"""
        prefs = self.tracker.preferences

        # 直接属性映射
        direct_mapping = {
            "likes_humor": "likes_humor",
            "likes_detailed_feedback": "likes_detailed_feedback",
            "likes_encouragement": "likes_encouragement",
            "likes_analysis": "likes_analysis",
            "likes_proactive": "likes_proactive",
            "interaction_style": "interaction_style",
            "notification_frequency": "notification_frequency",
        }

        if key in direct_mapping:
            setattr(prefs, direct_mapping[key], value)
        elif key == "feedback_reaction":
            # 根据反馈反应调整偏好
            if value == "positive":
                prefs.likes_proactive = min(1.0, prefs.likes_proactive + 0.05)
            elif value in ("negative", "dismissed"):
                prefs.likes_proactive = max(0.0, prefs.likes_proactive - 0.1)
        elif key == "feedback_frequency":
            # 调整通知频率
            if isinstance(value, float):
                if value < 0.5:
                    prefs.notification_frequency = "low"
                elif value > 1.2:
                    prefs.notification_frequency = "high"
                else:
                    prefs.notification_frequency = "normal"
        elif key == "preferred_tone":
            # 根据语气调整相关偏好
            if value == "humorous":
                prefs.likes_humor = min(1.0, prefs.likes_humor + 0.1)
            elif value == "encouraging":
                prefs.likes_encouragement = min(1.0, prefs.likes_encouragement + 0.1)
            elif value == "analytical":
                prefs.likes_analysis = min(1.0, prefs.likes_analysis + 0.1)

    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取单个偏好值"""
        prefs = self.tracker.preferences

        direct_mapping = {
            "likes_humor": prefs.likes_humor,
            "likes_detailed_feedback": prefs.likes_detailed_feedback,
            "likes_encouragement": prefs.likes_encouragement,
            "likes_analysis": prefs.likes_analysis,
            "likes_proactive": prefs.likes_proactive,
            "interaction_style": prefs.interaction_style,
            "notification_frequency": prefs.notification_frequency,
            "preferred_tone": self.tracker.get_preferred_tone().value,
            "preferred_length": self.tracker.get_preferred_length(),
            "feedback_frequency": 1.0 if prefs.notification_frequency == "normal" else (0.5 if prefs.notification_frequency == "low" else 1.5),
        }

        return direct_mapping.get(key, default)
