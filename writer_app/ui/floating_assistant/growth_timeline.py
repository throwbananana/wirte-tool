"""
悬浮助手 - 成长轨迹系统 (Growth Timeline System)
记录用户的创作旅程、里程碑、关系发展等成长历程
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    # 创作相关
    FIRST_WRITE = "first_write"         # 第一次写作
    WORD_MILESTONE = "word_milestone"   # 字数里程碑
    CHAPTER_COMPLETE = "chapter_complete"  # 章节完成
    PROJECT_COMPLETE = "project_complete"  # 项目完成
    STREAK_RECORD = "streak_record"     # 连续记录

    # 关系相关
    AFFECTION_MILESTONE = "affection_milestone"  # 好感度里程碑
    RELATIONSHIP_UPGRADE = "relationship_upgrade"  # 关系升级
    SPECIAL_INTERACTION = "special_interaction"   # 特殊互动

    # 系统相关
    FIRST_MEETING = "first_meeting"     # 初次相遇
    ANNIVERSARY = "anniversary"         # 周年纪念
    ACHIEVEMENT_UNLOCK = "achievement_unlock"  # 成就解锁
    SECRET_DISCOVER = "secret_discover"  # 发现秘密

    # 日常相关
    DAILY_LOGIN = "daily_login"         # 每日登录
    FEATURE_DISCOVER = "feature_discover"  # 功能发现
    SPECIAL_DATE = "special_date"       # 特殊日期


class EventImportance(Enum):
    """事件重要性"""
    TRIVIAL = 1         # 琐碎
    MINOR = 2           # 次要
    NORMAL = 3          # 普通
    MAJOR = 4           # 重要
    MILESTONE = 5       # 里程碑
    LEGENDARY = 6       # 传奇


@dataclass
class TimelineEvent:
    """时间线事件"""
    event_id: str
    event_type: EventType
    importance: EventImportance
    title: str
    description: str = ""
    timestamp: str = ""             # ISO格式时间
    icon: str = ""                  # 事件图标
    color: str = "#808080"          # 事件颜色
    related_data: Dict[str, Any] = field(default_factory=dict)  # 关联数据
    tags: List[str] = field(default_factory=list)
    photo_id: Optional[str] = None  # 关联照片
    is_hidden: bool = False         # 是否隐藏（需要解锁）


@dataclass
class GrowthStats:
    """成长统计"""
    date: str                       # YYYY-MM-DD
    words_written: int = 0          # 当日字数
    time_spent: int = 0             # 花费时间（分钟）
    interactions: int = 0           # 互动次数
    mood_score: float = 5.0         # 心情分数 (1-10)
    affection_change: int = 0       # 好感度变化


@dataclass
class RelationshipPhase:
    """关系阶段"""
    phase_id: str
    name: str
    description: str = ""
    affection_required: int = 0
    start_date: Optional[str] = None
    special_events: List[str] = field(default_factory=list)


class GrowthTimeline:
    """
    成长轨迹系统

    功能:
    1. 记录成长事件
    2. 追踪写作统计
    3. 关系发展历程
    4. 里程碑系统
    5. 时间线可视化
    """

    def __init__(self, pet_system=None):
        self.pet_system = pet_system

        # 事件库
        self.events: Dict[str, TimelineEvent] = {}

        # 每日统计
        self.daily_stats: Dict[str, GrowthStats] = {}

        # 关系阶段历史
        self.relationship_history: List[RelationshipPhase] = []
        self.current_phase_id: str = "stranger"

        # 里程碑记录
        self.milestones_achieved: Dict[str, str] = {}  # milestone_id -> date

        # 统计汇总
        self.total_words: int = 0
        self.total_time: int = 0
        self.total_days: int = 0
        self.max_streak: int = 0
        self.current_streak: int = 0

        # 起始日期
        self.start_date: Optional[str] = None

        # 回调
        self.on_milestone_reached: Optional[Callable[[TimelineEvent], None]] = None
        self.on_phase_change: Optional[Callable[[RelationshipPhase], None]] = None

        # 初始化关系阶段
        self._init_relationship_phases()
        self._init_milestone_definitions()

    def _init_relationship_phases(self):
        """初始化关系阶段"""
        phases = [
            RelationshipPhase(
                phase_id="stranger",
                name="陌生人",
                description="初次相遇，彼此还不了解",
                affection_required=0
            ),
            RelationshipPhase(
                phase_id="acquaintance",
                name="熟人",
                description="开始有了基本的了解",
                affection_required=100
            ),
            RelationshipPhase(
                phase_id="friend",
                name="朋友",
                description="建立了友谊的基础",
                affection_required=300
            ),
            RelationshipPhase(
                phase_id="close_friend",
                name="挚友",
                description="彼此信任，分享秘密",
                affection_required=600
            ),
            RelationshipPhase(
                phase_id="soulmate",
                name="灵魂伴侣",
                description="无需言语也能理解彼此",
                affection_required=900
            ),
        ]

        for phase in phases:
            self.relationship_history.append(phase)

    def _init_milestone_definitions(self):
        """初始化里程碑定义"""
        self.milestone_definitions = {
            # 字数里程碑
            "words_1k": {"type": EventType.WORD_MILESTONE, "value": 1000, "title": "千字小成", "color": "#4CAF50"},
            "words_5k": {"type": EventType.WORD_MILESTONE, "value": 5000, "title": "五千字达成", "color": "#4CAF50"},
            "words_10k": {"type": EventType.WORD_MILESTONE, "value": 10000, "title": "万字里程碑", "color": "#2196F3"},
            "words_50k": {"type": EventType.WORD_MILESTONE, "value": 50000, "title": "五万字突破", "color": "#9C27B0"},
            "words_100k": {"type": EventType.WORD_MILESTONE, "value": 100000, "title": "十万字大作", "color": "#FF9800"},
            "words_500k": {"type": EventType.WORD_MILESTONE, "value": 500000, "title": "五十万字传说", "color": "#F44336"},

            # 连续天数里程碑
            "streak_7": {"type": EventType.STREAK_RECORD, "value": 7, "title": "一周坚持", "color": "#4CAF50"},
            "streak_30": {"type": EventType.STREAK_RECORD, "value": 30, "title": "月度勤奋", "color": "#2196F3"},
            "streak_100": {"type": EventType.STREAK_RECORD, "value": 100, "title": "百日传奇", "color": "#FF9800"},
            "streak_365": {"type": EventType.STREAK_RECORD, "value": 365, "title": "一年如一日", "color": "#F44336"},

            # 好感度里程碑
            "affection_100": {"type": EventType.AFFECTION_MILESTONE, "value": 100, "title": "初识", "color": "#E91E63"},
            "affection_300": {"type": EventType.AFFECTION_MILESTONE, "value": 300, "title": "友谊萌芽", "color": "#E91E63"},
            "affection_500": {"type": EventType.AFFECTION_MILESTONE, "value": 500, "title": "心有灵犀", "color": "#9C27B0"},
            "affection_800": {"type": EventType.AFFECTION_MILESTONE, "value": 800, "title": "羁绊深厚", "color": "#673AB7"},
            "affection_1000": {"type": EventType.AFFECTION_MILESTONE, "value": 1000, "title": "永恒羁绊", "color": "#FF5722"},

            # 时间里程碑
            "days_7": {"type": EventType.ANNIVERSARY, "value": 7, "title": "一周纪念", "color": "#00BCD4"},
            "days_30": {"type": EventType.ANNIVERSARY, "value": 30, "title": "满月纪念", "color": "#00BCD4"},
            "days_100": {"type": EventType.ANNIVERSARY, "value": 100, "title": "百日纪念", "color": "#009688"},
            "days_365": {"type": EventType.ANNIVERSARY, "value": 365, "title": "周年纪念", "color": "#FF9800"},
        }

    # ============================================================
    # 事件记录
    # ============================================================

    def record_event(self,
                    event_type: EventType,
                    title: str,
                    description: str = "",
                    importance: EventImportance = EventImportance.NORMAL,
                    related_data: Dict = None,
                    tags: List[str] = None,
                    photo_id: str = None) -> TimelineEvent:
        """记录事件"""
        now = datetime.now()
        event_id = f"evt_{now.strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

        # 确定颜色
        color_map = {
            EventType.FIRST_WRITE: "#4CAF50",
            EventType.WORD_MILESTONE: "#2196F3",
            EventType.CHAPTER_COMPLETE: "#9C27B0",
            EventType.PROJECT_COMPLETE: "#FF9800",
            EventType.STREAK_RECORD: "#4CAF50",
            EventType.AFFECTION_MILESTONE: "#E91E63",
            EventType.RELATIONSHIP_UPGRADE: "#9C27B0",
            EventType.SPECIAL_INTERACTION: "#FF4081",
            EventType.FIRST_MEETING: "#673AB7",
            EventType.ANNIVERSARY: "#00BCD4",
            EventType.ACHIEVEMENT_UNLOCK: "#FFD700",
            EventType.SECRET_DISCOVER: "#795548",
        }

        event = TimelineEvent(
            event_id=event_id,
            event_type=event_type,
            importance=importance,
            title=title,
            description=description,
            timestamp=now.isoformat(),
            color=color_map.get(event_type, "#808080"),
            related_data=related_data or {},
            tags=tags or [],
            photo_id=photo_id
        )

        self.events[event_id] = event

        # 检查是否需要触发回调
        if importance.value >= EventImportance.MAJOR.value:
            if self.on_milestone_reached:
                self.on_milestone_reached(event)

        return event

    def record_first_meeting(self) -> TimelineEvent:
        """记录初次相遇"""
        now = datetime.now()
        self.start_date = now.strftime("%Y-%m-%d")

        return self.record_event(
            event_type=EventType.FIRST_MEETING,
            title="初次相遇",
            description="这是我们相遇的日子，一切从这里开始...",
            importance=EventImportance.LEGENDARY,
            tags=["beginning", "special"]
        )

    def record_daily_stats(self, words: int = 0, time_minutes: int = 0, interactions: int = 0) -> GrowthStats:
        """记录每日统计"""
        today = datetime.now().strftime("%Y-%m-%d")

        if today in self.daily_stats:
            stats = self.daily_stats[today]
            stats.words_written += words
            stats.time_spent += time_minutes
            stats.interactions += interactions
        else:
            stats = GrowthStats(
                date=today,
                words_written=words,
                time_spent=time_minutes,
                interactions=interactions
            )
            self.daily_stats[today] = stats
            self.total_days += 1

            # 更新连续天数
            self._update_streak()

        # 更新总计
        self.total_words += words
        self.total_time += time_minutes

        # 检查字数里程碑
        self._check_word_milestones()

        # 检查时间里程碑
        self._check_time_milestones()

        return stats

    def _update_streak(self) -> None:
        """更新连续天数"""
        if not self.daily_stats:
            self.current_streak = 1
            return

        sorted_dates = sorted(self.daily_stats.keys())
        if len(sorted_dates) < 2:
            self.current_streak = 1
            return

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        if yesterday in self.daily_stats:
            self.current_streak += 1
        else:
            self.current_streak = 1

        # 更新最大连续
        if self.current_streak > self.max_streak:
            self.max_streak = self.current_streak
            self._check_streak_milestones()

    def _check_word_milestones(self) -> None:
        """检查字数里程碑"""
        milestones = [
            ("words_1k", 1000),
            ("words_5k", 5000),
            ("words_10k", 10000),
            ("words_50k", 50000),
            ("words_100k", 100000),
            ("words_500k", 500000),
        ]

        for milestone_id, threshold in milestones:
            if milestone_id in self.milestones_achieved:
                continue

            if self.total_words >= threshold:
                self._achieve_milestone(milestone_id)

    def _check_streak_milestones(self) -> None:
        """检查连续天数里程碑"""
        milestones = [
            ("streak_7", 7),
            ("streak_30", 30),
            ("streak_100", 100),
            ("streak_365", 365),
        ]

        for milestone_id, threshold in milestones:
            if milestone_id in self.milestones_achieved:
                continue

            if self.current_streak >= threshold:
                self._achieve_milestone(milestone_id)

    def _check_time_milestones(self) -> None:
        """检查时间里程碑"""
        if not self.start_date:
            return

        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        days_passed = (datetime.now() - start).days

        milestones = [
            ("days_7", 7),
            ("days_30", 30),
            ("days_100", 100),
            ("days_365", 365),
        ]

        for milestone_id, threshold in milestones:
            if milestone_id in self.milestones_achieved:
                continue

            if days_passed >= threshold:
                self._achieve_milestone(milestone_id)

    def _achieve_milestone(self, milestone_id: str) -> None:
        """达成里程碑"""
        if milestone_id in self.milestones_achieved:
            return

        definition = self.milestone_definitions.get(milestone_id)
        if not definition:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        self.milestones_achieved[milestone_id] = today

        # 记录事件
        importance = EventImportance.MILESTONE
        if "100k" in milestone_id or "365" in milestone_id:
            importance = EventImportance.LEGENDARY

        self.record_event(
            event_type=definition["type"],
            title=definition["title"],
            description=f"在{today}达成了{definition['title']}里程碑！",
            importance=importance,
            related_data={"milestone_id": milestone_id, "value": definition["value"]},
            tags=["milestone", milestone_id.split("_")[0]]
        )

    def check_affection_milestone(self, affection: int) -> None:
        """检查好感度里程碑"""
        milestones = [
            ("affection_100", 100),
            ("affection_300", 300),
            ("affection_500", 500),
            ("affection_800", 800),
            ("affection_1000", 1000),
        ]

        for milestone_id, threshold in milestones:
            if milestone_id in self.milestones_achieved:
                continue

            if affection >= threshold:
                self._achieve_milestone(milestone_id)

        # 检查关系阶段变化
        self._check_relationship_phase(affection)

    def _check_relationship_phase(self, affection: int) -> None:
        """检查关系阶段变化"""
        new_phase_id = "stranger"

        for phase in self.relationship_history:
            if affection >= phase.affection_required:
                new_phase_id = phase.phase_id

        if new_phase_id != self.current_phase_id:
            old_phase = self.current_phase_id
            self.current_phase_id = new_phase_id

            # 找到新阶段信息
            new_phase = None
            for phase in self.relationship_history:
                if phase.phase_id == new_phase_id:
                    new_phase = phase
                    phase.start_date = datetime.now().strftime("%Y-%m-%d")
                    break

            if new_phase:
                # 记录事件
                self.record_event(
                    event_type=EventType.RELATIONSHIP_UPGRADE,
                    title=f"关系升级: {new_phase.name}",
                    description=new_phase.description,
                    importance=EventImportance.MAJOR,
                    related_data={"from_phase": old_phase, "to_phase": new_phase_id},
                    tags=["relationship", "upgrade"]
                )

                # 触发回调
                if self.on_phase_change:
                    self.on_phase_change(new_phase)

    # ============================================================
    # 查询功能
    # ============================================================

    def get_events_by_type(self, event_type: EventType) -> List[TimelineEvent]:
        """按类型获取事件"""
        return [e for e in self.events.values() if e.event_type == event_type]

    def get_events_by_date_range(self, start_date: str, end_date: str) -> List[TimelineEvent]:
        """按日期范围获取事件"""
        return [
            e for e in self.events.values()
            if start_date <= e.timestamp[:10] <= end_date
        ]

    def get_events_by_importance(self, min_importance: EventImportance) -> List[TimelineEvent]:
        """按重要性获取事件"""
        return [e for e in self.events.values() if e.importance.value >= min_importance.value]

    def get_recent_events(self, count: int = 10) -> List[TimelineEvent]:
        """获取最近的事件"""
        sorted_events = sorted(self.events.values(), key=lambda e: e.timestamp, reverse=True)
        return sorted_events[:count]

    def get_daily_stats_range(self, start_date: str, end_date: str) -> List[GrowthStats]:
        """获取日期范围内的统计"""
        return [
            stats for date, stats in self.daily_stats.items()
            if start_date <= date <= end_date
        ]

    def get_current_phase(self) -> Optional[RelationshipPhase]:
        """获取当前关系阶段"""
        for phase in self.relationship_history:
            if phase.phase_id == self.current_phase_id:
                return phase
        return None

    def get_next_phase(self) -> Optional[RelationshipPhase]:
        """获取下一个关系阶段"""
        found_current = False
        for phase in self.relationship_history:
            if found_current:
                return phase
            if phase.phase_id == self.current_phase_id:
                found_current = True
        return None

    # ============================================================
    # 统计分析
    # ============================================================

    def get_summary(self) -> Dict[str, Any]:
        """获取成长摘要"""
        days_since_start = 0
        if self.start_date:
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            days_since_start = (datetime.now() - start).days

        current_phase = self.get_current_phase()
        next_phase = self.get_next_phase()

        affection = 0
        if self.pet_system:
            affection = getattr(self.pet_system.data, "affection", 0)

        return {
            "start_date": self.start_date,
            "days_since_start": days_since_start,
            "total_words": self.total_words,
            "total_time_hours": round(self.total_time / 60, 1),
            "total_days_active": self.total_days,
            "current_streak": self.current_streak,
            "max_streak": self.max_streak,
            "milestones_count": len(self.milestones_achieved),
            "events_count": len(self.events),
            "current_phase": current_phase.name if current_phase else "未知",
            "next_phase": next_phase.name if next_phase else "已达最高",
            "affection_to_next": (next_phase.affection_required - affection) if next_phase else 0,
            "average_daily_words": round(self.total_words / max(1, self.total_days), 0)
        }

    def get_weekly_summary(self) -> Dict[str, Any]:
        """获取周统计"""
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_start_str = week_start.strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        week_stats = self.get_daily_stats_range(week_start_str, today_str)

        total_words = sum(s.words_written for s in week_stats)
        total_time = sum(s.time_spent for s in week_stats)
        active_days = len(week_stats)

        return {
            "week_start": week_start_str,
            "words_this_week": total_words,
            "time_this_week_hours": round(total_time / 60, 1),
            "active_days": active_days,
            "daily_breakdown": [
                {
                    "date": s.date,
                    "words": s.words_written,
                    "time": s.time_spent
                }
                for s in week_stats
            ]
        }

    def get_monthly_summary(self) -> Dict[str, Any]:
        """获取月统计"""
        today = datetime.now()
        month_start_str = today.strftime("%Y-%m-01")
        today_str = today.strftime("%Y-%m-%d")

        month_stats = self.get_daily_stats_range(month_start_str, today_str)

        total_words = sum(s.words_written for s in month_stats)
        total_time = sum(s.time_spent for s in month_stats)
        active_days = len(month_stats)

        return {
            "month": today.strftime("%Y-%m"),
            "words_this_month": total_words,
            "time_this_month_hours": round(total_time / 60, 1),
            "active_days": active_days,
            "average_daily_words": round(total_words / max(1, active_days), 0)
        }

    def get_milestone_progress(self) -> Dict[str, Dict[str, Any]]:
        """获取里程碑进度"""
        progress = {}

        # 字数进度
        word_milestones = [1000, 5000, 10000, 50000, 100000, 500000]
        for threshold in word_milestones:
            milestone_id = f"words_{threshold // 1000}k"
            progress[milestone_id] = {
                "current": self.total_words,
                "target": threshold,
                "progress": min(100, round(self.total_words / threshold * 100, 1)),
                "achieved": milestone_id in self.milestones_achieved
            }

        # 连续天数进度
        streak_milestones = [7, 30, 100, 365]
        for threshold in streak_milestones:
            milestone_id = f"streak_{threshold}"
            progress[milestone_id] = {
                "current": self.current_streak,
                "target": threshold,
                "progress": min(100, round(self.current_streak / threshold * 100, 1)),
                "achieved": milestone_id in self.milestones_achieved
            }

        return progress

    # ============================================================
    # 时间线生成
    # ============================================================

    def generate_timeline_data(self, max_events: int = 50) -> List[Dict[str, Any]]:
        """生成时间线数据（用于可视化）"""
        sorted_events = sorted(
            self.events.values(),
            key=lambda e: e.timestamp,
            reverse=True
        )[:max_events]

        timeline = []
        for event in sorted_events:
            timeline.append({
                "id": event.event_id,
                "type": event.event_type.value,
                "importance": event.importance.value,
                "title": event.title,
                "description": event.description,
                "timestamp": event.timestamp,
                "date": event.timestamp[:10],
                "color": event.color,
                "tags": event.tags,
                "has_photo": event.photo_id is not None
            })

        return timeline

    def generate_growth_chart_data(self, days: int = 30) -> Dict[str, List]:
        """生成成长图表数据"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        dates = []
        words = []
        cumulative_words = 0
        cumulative = []

        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            dates.append(date_str)

            stats = self.daily_stats.get(date_str)
            day_words = stats.words_written if stats else 0
            words.append(day_words)

            cumulative_words += day_words
            cumulative.append(cumulative_words)

            current += timedelta(days=1)

        return {
            "dates": dates,
            "daily_words": words,
            "cumulative_words": cumulative
        }

    # ============================================================
    # 状态持久化
    # ============================================================

    def get_state(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "events": {
                eid: {
                    "event_id": e.event_id,
                    "event_type": e.event_type.value,
                    "importance": e.importance.value,
                    "title": e.title,
                    "description": e.description,
                    "timestamp": e.timestamp,
                    "color": e.color,
                    "related_data": e.related_data,
                    "tags": e.tags,
                    "photo_id": e.photo_id,
                    "is_hidden": e.is_hidden
                }
                for eid, e in self.events.items()
            },
            "daily_stats": {
                date: {
                    "date": s.date,
                    "words_written": s.words_written,
                    "time_spent": s.time_spent,
                    "interactions": s.interactions,
                    "mood_score": s.mood_score,
                    "affection_change": s.affection_change
                }
                for date, s in self.daily_stats.items()
            },
            "milestones_achieved": self.milestones_achieved,
            "current_phase_id": self.current_phase_id,
            "total_words": self.total_words,
            "total_time": self.total_time,
            "total_days": self.total_days,
            "max_streak": self.max_streak,
            "current_streak": self.current_streak,
            "start_date": self.start_date
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """加载状态"""
        # 加载事件
        events_data = state.get("events", {})
        for eid, edata in events_data.items():
            try:
                self.events[eid] = TimelineEvent(
                    event_id=edata["event_id"],
                    event_type=EventType(edata["event_type"]),
                    importance=EventImportance(edata["importance"]),
                    title=edata["title"],
                    description=edata.get("description", ""),
                    timestamp=edata["timestamp"],
                    color=edata.get("color", "#808080"),
                    related_data=edata.get("related_data", {}),
                    tags=edata.get("tags", []),
                    photo_id=edata.get("photo_id"),
                    is_hidden=edata.get("is_hidden", False)
                )
            except Exception as e:
                logger.warning(f"加载事件 {eid} 失败: {e}")

        # 加载每日统计
        stats_data = state.get("daily_stats", {})
        for date, sdata in stats_data.items():
            self.daily_stats[date] = GrowthStats(
                date=sdata["date"],
                words_written=sdata.get("words_written", 0),
                time_spent=sdata.get("time_spent", 0),
                interactions=sdata.get("interactions", 0),
                mood_score=sdata.get("mood_score", 5.0),
                affection_change=sdata.get("affection_change", 0)
            )

        # 加载其他数据
        self.milestones_achieved = state.get("milestones_achieved", {})
        self.current_phase_id = state.get("current_phase_id", "stranger")
        self.total_words = state.get("total_words", 0)
        self.total_time = state.get("total_time", 0)
        self.total_days = state.get("total_days", 0)
        self.max_streak = state.get("max_streak", 0)
        self.current_streak = state.get("current_streak", 0)
        self.start_date = state.get("start_date")


# 便捷函数
def create_growth_timeline(pet_system=None) -> GrowthTimeline:
    """创建成长轨迹系统"""
    return GrowthTimeline(pet_system)
