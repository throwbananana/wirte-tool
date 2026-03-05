"""
悬浮助手 - 事件序列追踪器 (Event Sequence Tracker)
负责追踪事件序列、识别用户行为模式、提供双向反馈循环
"""
import time
import json
from collections import deque, Counter
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import re


@dataclass
class EventRecord:
    """事件记录"""
    event_type: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    user_response: Optional[str] = None  # 用户对该事件的响应
    outcome: Optional[str] = None  # 结果评价 (positive/neutral/negative)


@dataclass
class PatternMatch:
    """模式匹配结果"""
    pattern_id: str
    pattern_name: str
    confidence: float
    events: List[str]
    insight: str
    suggested_action: Optional[str] = None


# 预定义的行为模式
BEHAVIOR_PATTERNS = {
    # 规划型写作者：先大纲后填充
    "planner": {
        "sequence": ["outline_changed", "character_added", "scene_added"],
        "name": "规划型写作者",
        "insight": "你喜欢先规划好结构再填充内容，这是很专业的写作习惯！",
        "weight": 1.0
    },
    # 发现型写作者：直接开始写场景
    "discovery_writer": {
        "sequence": ["scene_added", "scene_updated", "character_added"],
        "name": "发现型写作者",
        "insight": "你喜欢在写作中发现角色和情节，这种自由探索的方式很有创意！",
        "weight": 1.0
    },
    # 角色驱动：先创建角色再发展剧情
    "character_driven": {
        "sequence": ["character_added", "character_updated", "relationship_link_added"],
        "name": "角色驱动型",
        "insight": "你非常重视角色塑造，角色关系是你故事的核心驱动力！",
        "weight": 1.2
    },
    # 世界构建者：大量使用wiki和设定
    "worldbuilder": {
        "sequence": ["wiki_entry_added", "wiki_entry_added", "wiki_entry_updated"],
        "name": "世界构建者",
        "insight": "你花大量时间构建世界观，这会让故事更加立体和可信！",
        "weight": 1.1
    },
    # 时间线控制者：重视时间线管理
    "timeline_master": {
        "sequence": ["timeline_event_added", "timeline_event_updated", "scene_added"],
        "name": "时间线大师",
        "insight": "你非常注重故事的时间逻辑，这对悬疑和复杂叙事很重要！",
        "weight": 1.2
    },
    # 灵感捕手：经常记录灵感
    "idea_catcher": {
        "sequence": ["idea_added", "idea_added", "research_added"],
        "name": "灵感捕手",
        "insight": "你善于捕捉灵感并进行研究，这是创作的宝贵习惯！",
        "weight": 1.0
    },
    # 修改狂魔：频繁修改已有内容
    "perfectionist": {
        "sequence": ["scene_updated", "scene_updated", "scene_updated"],
        "name": "完美主义者",
        "insight": "你对作品精益求精，不过也要注意平衡进度和质量哦！",
        "weight": 0.8
    },
    # 快速迭代：添加后立即修改
    "rapid_iteration": {
        "sequence": ["scene_added", "scene_updated", "scene_added"],
        "name": "快速迭代型",
        "insight": "你习惯快速推进然后回头修改，这种节奏很高效！",
        "weight": 1.0
    },
    # 证据收集者：悬疑写作专用
    "evidence_collector": {
        "sequence": ["evidence_node_added", "clue_added", "evidence_link_added"],
        "name": "证据收集者",
        "insight": "你在精心布置谜题的线索，这种缜密思维是悬疑写作的关键！",
        "weight": 1.3
    },
    # 多线程操作：快速切换不同模块
    "multitasker": {
        "sequence": ["outline_changed", "character_updated", "scene_added", "wiki_entry_added"],
        "name": "多线程创作者",
        "insight": "你能同时处理多个创作维度，大脑运转得很快呢！",
        "weight": 1.1
    },
}

# 时间相关模式
TIME_PATTERNS = {
    "morning_burst": {
        "time_range": (5, 9),
        "min_events": 10,
        "name": "晨间爆发",
        "insight": "你在清晨创作力最强！这个时段的效率是平时的两倍。"
    },
    "night_owl": {
        "time_range": (22, 3),
        "min_events": 15,
        "name": "夜猫子模式",
        "insight": "深夜是你的灵感时刻，不过也要注意休息哦。"
    },
    "lunch_writer": {
        "time_range": (11, 14),
        "min_events": 5,
        "name": "午间写手",
        "insight": "午休时间也在创作，这份热情真让人感动！"
    },
    "weekend_warrior": {
        "weekday_range": (5, 6),  # Saturday, Sunday
        "min_events": 20,
        "name": "周末战士",
        "insight": "周末是你的主要创作时间，充分利用休息日的你很棒！"
    }
}


class EventSequenceTracker:
    """事件序列追踪器：追踪事件序列，识别用户行为模式"""

    def __init__(self, data_dir: Optional[str] = None, max_history: int = 500):
        self.sequence: deque = deque(maxlen=max_history)
        self.pattern_cache: Dict[str, PatternMatch] = {}
        self.detected_patterns: List[PatternMatch] = []
        self.pattern_history: List[Dict] = []  # 历史检测到的模式

        # 统计数据
        self.event_counts: Counter = Counter()
        self.hourly_distribution: Dict[int, int] = {i: 0 for i in range(24)}
        self.daily_distribution: Dict[int, int] = {i: 0 for i in range(7)}

        # 持久化路径
        self.data_dir = Path(data_dir) if data_dir else None
        self._load_state()

    def _load_state(self):
        """加载持久化状态"""
        if not self.data_dir:
            return

        state_file = self.data_dir / "event_sequence_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.event_counts = Counter(data.get("event_counts", {}))
                    self.hourly_distribution = {int(k): v for k, v in data.get("hourly_distribution", {}).items()}
                    self.daily_distribution = {int(k): v for k, v in data.get("daily_distribution", {}).items()}
                    self.pattern_history = data.get("pattern_history", [])[-50:]  # 保留最近50条
            except Exception:
                pass

    def _save_state(self):
        """保存持久化状态"""
        if not self.data_dir:
            return

        self.data_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.data_dir / "event_sequence_state.json"
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "event_counts": dict(self.event_counts),
                    "hourly_distribution": self.hourly_distribution,
                    "daily_distribution": self.daily_distribution,
                    "pattern_history": self.pattern_history[-50:]
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def record(self, event_type: str, context: Optional[Dict] = None) -> Optional[PatternMatch]:
        """
        记录事件并检测模式

        Args:
            event_type: 事件类型
            context: 事件上下文

        Returns:
            如果检测到新模式，返回 PatternMatch
        """
        now = time.time()
        dt = datetime.fromtimestamp(now)

        record = EventRecord(
            event_type=event_type,
            timestamp=now,
            context=context or {}
        )
        self.sequence.append(record)

        # 更新统计
        self.event_counts[event_type] += 1
        self.hourly_distribution[dt.hour] = self.hourly_distribution.get(dt.hour, 0) + 1
        self.daily_distribution[dt.weekday()] = self.daily_distribution.get(dt.weekday(), 0) + 1

        # 检测模式
        pattern = self._detect_patterns()

        # 定期保存
        if len(self.sequence) % 20 == 0:
            self._save_state()

        return pattern

    def record_event(self, event_type: str, context: Optional[Dict] = None) -> None:
        """
        记录事件 (简化接口，兼容 event_system 调用)

        Args:
            event_type: 事件类型
            context: 事件上下文
        """
        self.record(event_type, context)

    @property
    def event_history(self) -> List[EventRecord]:
        """事件历史记录"""
        return list(self.sequence)

    def detect_pattern(self) -> Optional[Dict[str, Any]]:
        """
        检测用户行为模式 (简化接口，返回字典)

        Returns:
            包含 pattern_id, confidence 等的字典，或 None
        """
        pattern = self._detect_patterns()
        if pattern:
            return {
                "pattern_id": pattern.pattern_id,
                "pattern_name": pattern.pattern_name,
                "confidence": pattern.confidence,
                "insight": pattern.insight,
                "suggested_action": pattern.suggested_action,
            }
        return None

    def get_detected_patterns(self) -> List[Dict[str, Any]]:
        """
        获取所有已检测到的模式

        Returns:
            模式列表
        """
        result = []
        for record in self.pattern_history:
            result.append({
                "pattern_id": record.get("pattern_id"),
                "pattern_name": record.get("pattern_name"),
                "timestamp": record.get("timestamp"),
                "confidence": record.get("confidence", 0),
            })
        return result

    def record_response(self, event_type: str, response: str, outcome: str = "neutral"):
        """
        记录用户对事件的响应（用于反馈学习）

        Args:
            event_type: 事件类型
            response: 用户响应内容
            outcome: 结果评价 (positive/neutral/negative)
        """
        # 找到最近的匹配事件
        for record in reversed(self.sequence):
            if record.event_type == event_type and record.user_response is None:
                record.user_response = response
                record.outcome = outcome
                break

    def _detect_patterns(self) -> Optional[PatternMatch]:
        """检测行为模式"""
        if len(self.sequence) < 3:
            return None

        # 获取最近的事件类型序列
        recent_events = [r.event_type for r in list(self.sequence)[-20:]]

        best_match = None
        best_confidence = 0.0

        for pattern_id, pattern_def in BEHAVIOR_PATTERNS.items():
            confidence = self._match_pattern(recent_events, pattern_def["sequence"])
            weighted_confidence = confidence * pattern_def.get("weight", 1.0)

            if weighted_confidence > best_confidence and weighted_confidence > 0.6:
                # 检查冷却（同一模式不频繁触发）
                if self._check_pattern_cooldown(pattern_id):
                    best_confidence = weighted_confidence
                    best_match = PatternMatch(
                        pattern_id=pattern_id,
                        pattern_name=pattern_def["name"],
                        confidence=confidence,
                        events=pattern_def["sequence"],
                        insight=pattern_def["insight"]
                    )

        if best_match:
            self.detected_patterns.append(best_match)
            self.pattern_history.append({
                "pattern_id": best_match.pattern_id,
                "timestamp": time.time(),
                "confidence": best_match.confidence
            })
            self._save_state()

        return best_match

    def _match_pattern(self, events: List[str], pattern: List[str]) -> float:
        """
        模式匹配算法

        Returns:
            匹配置信度 (0.0-1.0)
        """
        if len(events) < len(pattern):
            return 0.0

        # 滑动窗口匹配
        best_score = 0.0
        window_size = len(pattern)

        for i in range(len(events) - window_size + 1):
            window = events[i:i + window_size]
            matches = sum(1 for a, b in zip(window, pattern) if a == b)
            score = matches / len(pattern)

            # 考虑顺序的相似度
            if self._check_subsequence(window, pattern):
                score = min(1.0, score + 0.2)

            best_score = max(best_score, score)

        return best_score

    def _check_subsequence(self, events: List[str], pattern: List[str]) -> bool:
        """检查pattern是否是events的子序列（保持顺序）"""
        pattern_idx = 0
        for event in events:
            if pattern_idx < len(pattern) and event == pattern[pattern_idx]:
                pattern_idx += 1
        return pattern_idx == len(pattern)

    def _check_pattern_cooldown(self, pattern_id: str, cooldown_hours: float = 4.0) -> bool:
        """检查模式冷却"""
        now = time.time()
        cooldown_seconds = cooldown_hours * 3600

        for record in reversed(self.pattern_history):
            if record["pattern_id"] == pattern_id:
                if now - record["timestamp"] < cooldown_seconds:
                    return False
                break

        return True

    def detect_time_patterns(self) -> Optional[PatternMatch]:
        """检测时间相关模式"""
        now = datetime.now()
        current_hour = now.hour
        current_weekday = now.weekday()

        # 统计最近一周的事件
        one_week_ago = time.time() - 7 * 24 * 3600
        recent_events = [r for r in self.sequence if r.timestamp > one_week_ago]

        for pattern_id, pattern_def in TIME_PATTERNS.items():
            if "time_range" in pattern_def:
                start, end = pattern_def["time_range"]
                # 处理跨午夜的时间范围
                if start > end:
                    in_range = current_hour >= start or current_hour <= end
                else:
                    in_range = start <= current_hour <= end

                if in_range:
                    # 统计该时间段的事件数
                    range_events = [r for r in recent_events
                                  if self._is_in_time_range(r.timestamp, start, end)]
                    if len(range_events) >= pattern_def["min_events"]:
                        return PatternMatch(
                            pattern_id=pattern_id,
                            pattern_name=pattern_def["name"],
                            confidence=min(1.0, len(range_events) / (pattern_def["min_events"] * 2)),
                            events=[],
                            insight=pattern_def["insight"]
                        )

            elif "weekday_range" in pattern_def:
                start, end = pattern_def["weekday_range"]
                if start <= current_weekday <= end:
                    weekend_events = [r for r in recent_events
                                    if datetime.fromtimestamp(r.timestamp).weekday() in range(start, end + 1)]
                    if len(weekend_events) >= pattern_def["min_events"]:
                        return PatternMatch(
                            pattern_id=pattern_id,
                            pattern_name=pattern_def["name"],
                            confidence=min(1.0, len(weekend_events) / (pattern_def["min_events"] * 2)),
                            events=[],
                            insight=pattern_def["insight"]
                        )

        return None

    def _is_in_time_range(self, timestamp: float, start_hour: int, end_hour: int) -> bool:
        """检查时间戳是否在指定小时范围内"""
        hour = datetime.fromtimestamp(timestamp).hour
        if start_hour > end_hour:
            return hour >= start_hour or hour <= end_hour
        return start_hour <= hour <= end_hour

    def get_user_profile(self) -> Dict[str, Any]:
        """
        生成用户画像

        Returns:
            包含用户行为特征的字典
        """
        if not self.sequence:
            return {}

        # 最常用的事件类型
        top_events = self.event_counts.most_common(10)

        # 最活跃的时间段
        peak_hours = sorted(self.hourly_distribution.items(), key=lambda x: x[1], reverse=True)[:3]

        # 最活跃的日期
        peak_days = sorted(self.daily_distribution.items(), key=lambda x: x[1], reverse=True)[:2]
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        # 检测到的主要模式
        pattern_counts = Counter(r["pattern_id"] for r in self.pattern_history)
        dominant_patterns = pattern_counts.most_common(3)

        # 计算写作风格标签
        style_tags = self._compute_style_tags()

        return {
            "total_events": sum(self.event_counts.values()),
            "top_events": top_events,
            "peak_hours": [(h, c) for h, c in peak_hours],
            "peak_days": [(day_names[d], c) for d, c in peak_days],
            "dominant_patterns": [
                {
                    "id": pid,
                    "name": BEHAVIOR_PATTERNS.get(pid, {}).get("name", pid),
                    "count": count
                }
                for pid, count in dominant_patterns
            ],
            "style_tags": style_tags,
            "activity_level": self._compute_activity_level()
        }

    def _compute_style_tags(self) -> List[str]:
        """计算写作风格标签"""
        tags = []
        total = sum(self.event_counts.values())
        if total == 0:
            return tags

        # 基于事件比例判断风格
        outline_ratio = self.event_counts.get("outline_changed", 0) / total
        character_ratio = (self.event_counts.get("character_added", 0) +
                          self.event_counts.get("character_updated", 0)) / total
        scene_ratio = (self.event_counts.get("scene_added", 0) +
                      self.event_counts.get("scene_updated", 0)) / total
        wiki_ratio = (self.event_counts.get("wiki_entry_added", 0) +
                     self.event_counts.get("wiki_entry_updated", 0)) / total

        if outline_ratio > 0.15:
            tags.append("结构主义者")
        if character_ratio > 0.2:
            tags.append("角色塑造师")
        if scene_ratio > 0.3:
            tags.append("场景构建者")
        if wiki_ratio > 0.1:
            tags.append("世界观架构师")

        # 基于时间分布
        night_events = sum(self.hourly_distribution.get(h, 0) for h in range(22, 24)) + \
                      sum(self.hourly_distribution.get(h, 0) for h in range(0, 5))
        morning_events = sum(self.hourly_distribution.get(h, 0) for h in range(5, 10))

        if night_events > morning_events * 2:
            tags.append("夜行者")
        elif morning_events > night_events * 2:
            tags.append("早起鸟")

        return tags

    def _compute_activity_level(self) -> str:
        """计算活跃度等级"""
        total = sum(self.event_counts.values())
        days = len(set(datetime.fromtimestamp(r.timestamp).date() for r in self.sequence))

        if days == 0:
            return "新手"

        avg_per_day = total / days

        if avg_per_day > 50:
            return "狂热创作者"
        elif avg_per_day > 20:
            return "高产作家"
        elif avg_per_day > 10:
            return "稳定创作者"
        elif avg_per_day > 5:
            return "休闲写手"
        else:
            return "间歇创作者"

    def get_sequence_summary(self, last_n: int = 20) -> str:
        """获取最近事件序列的可读摘要"""
        if not self.sequence:
            return "暂无事件记录"

        recent = list(self.sequence)[-last_n:]
        event_names = {
            "outline_changed": "修改大纲",
            "scene_added": "添加场景",
            "scene_updated": "更新场景",
            "character_added": "添加角色",
            "character_updated": "更新角色",
            "wiki_entry_added": "添加设定",
            "idea_added": "记录灵感",
            "research_added": "添加资料",
            "timeline_event_added": "添加时间线",
            "evidence_node_added": "添加证据",
            "clue_added": "添加线索",
        }

        summary_parts = []
        for record in recent:
            name = event_names.get(record.event_type, record.event_type)
            summary_parts.append(name)

        return " → ".join(summary_parts)

    def get_recommendations(self) -> List[str]:
        """基于行为模式生成建议"""
        recommendations = []
        profile = self.get_user_profile()

        # 基于主要模式的建议
        for pattern in profile.get("dominant_patterns", []):
            pattern_id = pattern["id"]

            if pattern_id == "perfectionist":
                recommendations.append("建议：尝试先完成初稿再回头修改，可能会更高效哦~")
            elif pattern_id == "planner":
                recommendations.append("你的规划能力很强，可以尝试更大胆地突破大纲限制探索新可能！")
            elif pattern_id == "discovery_writer":
                recommendations.append("自由写作很棒！偶尔整理一下思路可能会有意外收获~")

        # 基于时间分布的建议
        peak_hours = profile.get("peak_hours", [])
        if peak_hours:
            best_hour = peak_hours[0][0]
            if best_hour >= 22 or best_hour <= 3:
                recommendations.append("你在深夜创作效率最高，但也要注意休息哦！")
            elif 5 <= best_hour <= 8:
                recommendations.append("清晨是你的黄金创作时间，保持这个好习惯！")

        return recommendations


class FeedbackLoop:
    """反馈循环：收集和分析用户对事件的反馈"""

    def __init__(self, data_dir: Optional[str] = None):
        self.feedback_records: List[Dict] = []
        self.event_scores: Dict[str, List[float]] = {}  # 事件类型 -> 评分列表
        self.content_scores: Dict[str, List[float]] = {}  # 内容ID -> 评分列表

        self.data_dir = Path(data_dir) if data_dir else None
        self._load_state()

    def _load_state(self):
        """加载状态"""
        if not self.data_dir:
            return

        state_file = self.data_dir / "feedback_loop_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.feedback_records = data.get("feedback_records", [])[-200:]
                    self.event_scores = data.get("event_scores", {})
                    self.content_scores = data.get("content_scores", {})
            except Exception:
                pass

    def _save_state(self):
        """保存状态"""
        if not self.data_dir:
            return

        self.data_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.data_dir / "feedback_loop_state.json"
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "feedback_records": self.feedback_records[-200:],
                    "event_scores": self.event_scores,
                    "content_scores": self.content_scores
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def record_feedback(self, event_type: str, content_id: Optional[str],
                       reaction: str, score: float = 0.0):
        """
        记录用户反馈

        Args:
            event_type: 事件类型
            content_id: 内容标识（如消息ID、叙事链ID等）
            reaction: 用户反应类型 (clicked, dismissed, selected_option, etc.)
            score: 评分 (-1.0 到 1.0，负数表示负面反馈)
        """
        record = {
            "timestamp": time.time(),
            "event_type": event_type,
            "content_id": content_id,
            "reaction": reaction,
            "score": score
        }
        self.feedback_records.append(record)

        # 更新评分统计
        if event_type not in self.event_scores:
            self.event_scores[event_type] = []
        self.event_scores[event_type].append(score)

        # 限制列表长度
        if len(self.event_scores[event_type]) > 100:
            self.event_scores[event_type] = self.event_scores[event_type][-100:]

        if content_id:
            if content_id not in self.content_scores:
                self.content_scores[content_id] = []
            self.content_scores[content_id].append(score)

        # 定期保存
        if len(self.feedback_records) % 10 == 0:
            self._save_state()

    def get_event_preference(self, event_type: str) -> float:
        """
        获取用户对特定事件类型的偏好度

        Returns:
            -1.0 到 1.0 的偏好度分数
        """
        scores = self.event_scores.get(event_type, [])
        if not scores:
            return 0.0

        # 使用加权平均，最近的反馈权重更高
        weights = [1.0 + i * 0.1 for i in range(len(scores))]
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        return weighted_sum / sum(weights)

    def get_content_effectiveness(self, content_id: str) -> float:
        """获取特定内容的效果评分"""
        scores = self.content_scores.get(content_id, [])
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def should_show_event(self, event_type: str, threshold: float = -0.3) -> bool:
        """
        判断是否应该显示某类事件

        如果用户对该类事件的反馈持续为负面，可能应该减少或不显示
        """
        preference = self.get_event_preference(event_type)
        return preference >= threshold

    def get_preferred_content_types(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """获取用户最喜欢的内容类型"""
        preferences = [(et, self.get_event_preference(et)) for et in self.event_scores]
        preferences.sort(key=lambda x: x[1], reverse=True)
        return preferences[:top_n]

    def get_feedback_summary(self) -> Dict[str, Any]:
        """获取反馈摘要"""
        if not self.feedback_records:
            return {"total": 0}

        reaction_counts = Counter(r["reaction"] for r in self.feedback_records)
        avg_score = sum(r["score"] for r in self.feedback_records) / len(self.feedback_records)

        return {
            "total": len(self.feedback_records),
            "reaction_distribution": dict(reaction_counts),
            "average_score": avg_score,
            "preferred_events": self.get_preferred_content_types(5)
        }

    @property
    def feedback_history(self) -> List[Dict]:
        """反馈历史记录 (兼容属性访问)"""
        return self.feedback_records

    def load_state(self, state: Dict[str, Any]) -> None:
        """从字典加载状态 (用于 pet_system 恢复)"""
        if not state:
            return

        self.feedback_records = state.get("feedback_records", [])[-200:]
        self.event_scores = state.get("event_scores", {})
        self.content_scores = state.get("content_scores", {})

    def get_state(self) -> Dict[str, Any]:
        """获取可序列化的状态字典"""
        return {
            "feedback_records": self.feedback_records[-200:],
            "event_scores": dict(self.event_scores),
            "content_scores": dict(self.content_scores),
        }

    def get_effectiveness_report(self) -> Dict[str, Any]:
        """获取反馈效果报告"""
        summary = self.get_feedback_summary()

        # 计算正面/负面反馈比例
        positive = sum(1 for r in self.feedback_records if r.get("score", 0) > 0)
        negative = sum(1 for r in self.feedback_records if r.get("score", 0) < 0)
        neutral = len(self.feedback_records) - positive - negative

        return {
            "total_feedback": summary.get("total", 0),
            "average_score": summary.get("average_score", 0),
            "positive_ratio": positive / max(1, len(self.feedback_records)),
            "negative_ratio": negative / max(1, len(self.feedback_records)),
            "neutral_ratio": neutral / max(1, len(self.feedback_records)),
            "preferred_events": summary.get("preferred_events", []),
            "reaction_distribution": summary.get("reaction_distribution", {}),
        }

    def record_feedback(self, feedback_id: str, reaction: str, score: float = None):
        """
        记录用户反馈 (兼容简化调用)

        Args:
            feedback_id: 反馈标识 (可以是 event_type 或 content_id)
            reaction: 用户反应类型
            score: 评分 (可选，自动根据 reaction 推断)
        """
        # 根据 reaction 推断 score
        if score is None:
            reaction_scores = {
                "positive": 1.0,
                "clicked": 0.8,
                "selected": 0.7,
                "completed": 0.9,
                "neutral": 0.0,
                "triggered": 0.1,
                "negative": -0.8,
                "dismissed": -0.5,
                "ignored": -0.3,
            }
            score = reaction_scores.get(reaction, 0.0)

        record = {
            "timestamp": time.time(),
            "event_type": feedback_id,
            "content_id": feedback_id,
            "reaction": reaction,
            "score": score
        }
        self.feedback_records.append(record)

        # 更新评分统计
        if feedback_id not in self.event_scores:
            self.event_scores[feedback_id] = []
        self.event_scores[feedback_id].append(score)

        # 限制列表长度
        if len(self.event_scores[feedback_id]) > 100:
            self.event_scores[feedback_id] = self.event_scores[feedback_id][-100:]

        if feedback_id not in self.content_scores:
            self.content_scores[feedback_id] = []
        self.content_scores[feedback_id].append(score)

        # 定期保存
        if len(self.feedback_records) % 10 == 0:
            self._save_state()
