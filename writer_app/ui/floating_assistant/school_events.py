"""
悬浮写作助手 - 学校事件模块 (升级版)
处理学校场景下的随机事件、互动和剧情
集成NPC系统、时间周期、位置系统、社交行动和剧情追踪
"""
import random
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple, Any, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    RANDOM = "random"                   # 随机事件
    SCHEDULED = "scheduled"             # 定时事件
    LOCATION = "location"               # 地点触发
    NPC_INTERACTION = "npc_interaction" # NPC互动
    STORY = "story"                     # 剧情事件
    SPECIAL = "special"                 # 特殊事件
    CHAIN = "chain"                     # 连锁事件


class EventPriority(Enum):
    """事件优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20
    STORY = 50                          # 剧情事件最高优先


# 事件类型显示
EVENT_TYPE_DISPLAY = {
    EventType.RANDOM: {"name": "日常", "icon": "🎲", "color": "#9E9E9E"},
    EventType.SCHEDULED: {"name": "定时", "icon": "⏰", "color": "#2196F3"},
    EventType.LOCATION: {"name": "地点", "icon": "📍", "color": "#4CAF50"},
    EventType.NPC_INTERACTION: {"name": "互动", "icon": "💬", "color": "#E91E63"},
    EventType.STORY: {"name": "剧情", "icon": "📖", "color": "#FFD700"},
    EventType.SPECIAL: {"name": "特殊", "icon": "⭐", "color": "#FF9800"},
    EventType.CHAIN: {"name": "连锁", "icon": "🔗", "color": "#9C27B0"},
}


@dataclass
class EventCondition:
    """事件触发条件"""
    condition_type: str                 # location, time, affection, flag, npc_present, weather等
    target: str                         # 目标值
    operator: str = "=="
    value: Any = None
    description: str = ""

    def check(self, context: Dict) -> bool:
        """检查条件"""
        if self.condition_type == "location":
            return context.get("current_location") == self.target

        elif self.condition_type == "time_period":
            current = context.get("time_period", "")
            if isinstance(self.value, list):
                return current in self.value
            return current == self.value

        elif self.condition_type == "day_of_week":
            current = context.get("day_of_week", 0)
            if isinstance(self.value, list):
                return current in self.value
            return current == self.value

        elif self.condition_type == "is_weekend":
            return context.get("is_weekend", False) == self.value

        elif self.condition_type == "weather":
            return context.get("weather", "") == self.target

        elif self.condition_type == "season":
            return context.get("season", "") == self.target

        elif self.condition_type == "affection":
            affection = context.get("affection", 0)
            if self.operator == ">=":
                return affection >= self.value
            elif self.operator == ">":
                return affection > self.value
            elif self.operator == "<=":
                return affection <= self.value
            elif self.operator == "<":
                return affection < self.value
            return affection == self.value

        elif self.condition_type == "npc_affection":
            npc_affections = context.get("npc_affections", {})
            affection = npc_affections.get(self.target, 0)
            if self.operator == ">=":
                return affection >= self.value
            return affection == self.value

        elif self.condition_type == "npc_present":
            npcs_present = context.get("npcs_at_location", [])
            return self.target in npcs_present

        elif self.condition_type == "flag":
            flags = context.get("flags", {})
            flag_value = flags.get(self.target, False)
            if self.operator == "==":
                return flag_value == self.value
            elif self.operator == "!=":
                return flag_value != self.value
            return bool(flag_value)

        elif self.condition_type == "event_completed":
            completed = context.get("completed_events", set())
            return self.target in completed

        elif self.condition_type == "phase":
            npc_phases = context.get("npc_phases", {})
            phase = npc_phases.get(self.target, "stranger")
            if isinstance(self.value, list):
                return phase in self.value
            return phase == self.value

        elif self.condition_type == "special_date":
            return context.get("special_date_id") == self.target

        return True

    def to_dict(self) -> Dict:
        return {
            "condition_type": self.condition_type,
            "target": self.target,
            "operator": self.operator,
            "value": self.value,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "EventCondition":
        return cls(
            condition_type=data.get("condition_type", ""),
            target=data.get("target", ""),
            operator=data.get("operator", "=="),
            value=data.get("value"),
            description=data.get("description", "")
        )


@dataclass
class EventEffect:
    """事件效果"""
    effect_type: str                    # affection, npc_affection, flag, item, achievement等
    target: str                         # 目标
    value: Any = 0                      # 值
    description: str = ""

    def apply(self, context: Dict, manager: "SchoolEventManager") -> Dict:
        """应用效果"""
        result = {"type": self.effect_type, "target": self.target, "change": self.value}

        if self.effect_type == "affection":
            if manager.pet_system:
                manager.pet_system.add_affection(self.value)
            result["description"] = f"好感度 {'+'if self.value > 0 else ''}{self.value}"

        elif self.effect_type == "npc_affection":
            if manager.npc_manager:
                manager.npc_manager.change_affection(self.target, self.value)
            result["description"] = f"{self.target} 好感度 {'+'if self.value > 0 else ''}{self.value}"

        elif self.effect_type == "mood":
            if manager.pet_system:
                manager.pet_system.update_mood(self.value)
            result["description"] = f"心情 {'+'if self.value > 0 else ''}{self.value}"

        elif self.effect_type == "npc_mood":
            if manager.npc_manager:
                npc = manager.npc_manager.get_npc(self.target)
                if npc:
                    npc.mood = max(0, min(100, npc.mood + self.value))
            result["description"] = f"{self.target} 心情变化"

        elif self.effect_type == "flag":
            if manager.story_tracker:
                manager.story_tracker.set_flag(self.target, self.value)
            result["description"] = f"标志 {self.target} = {self.value}"

        elif self.effect_type == "item":
            if manager.story_tracker:
                manager.story_tracker.collected_items.add(self.target)
            result["description"] = f"获得物品: {self.target}"

        elif self.effect_type == "achievement":
            if manager.story_tracker:
                manager.story_tracker.unlock_achievement(self.target)
            result["description"] = f"成就解锁: {self.target}"

        elif self.effect_type == "unlock_location":
            if manager.location_manager:
                manager.location_manager.unlock_location(self.target)
            result["description"] = f"解锁地点: {self.target}"

        elif self.effect_type == "time_advance":
            if manager.time_manager:
                manager.time_manager.advance_time(self.value)
            result["description"] = f"时间流逝"

        return result

    def to_dict(self) -> Dict:
        return {
            "effect_type": self.effect_type,
            "target": self.target,
            "value": self.value,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "EventEffect":
        return cls(
            effect_type=data.get("effect_type", ""),
            target=data.get("target", ""),
            value=data.get("value", 0),
            description=data.get("description", "")
        )


@dataclass
class SchoolEventChoice:
    """事件选项"""
    choice_id: str
    text: str
    outcome_text: str

    # 条件
    conditions: List[EventCondition] = field(default_factory=list)
    required_affection: int = 0

    # 效果
    effects: List[EventEffect] = field(default_factory=list)

    # 后续
    next_event_id: str = ""             # 后续事件
    trigger_narrative_id: str = ""      # 触发叙事链
    trigger_story_node: str = ""        # 触发剧情节点

    # 兼容旧版
    affection_change: int = 0
    mood_change: int = 0
    npc_affection_change: Dict[str, int] = field(default_factory=dict)
    unlock_achievement: str = ""

    def is_available(self, context: Dict) -> Tuple[bool, str]:
        """检查选项是否可用"""
        # 检查好感度
        if self.required_affection > 0:
            if context.get("affection", 0) < self.required_affection:
                return False, f"需要好感度 {self.required_affection}"

        # 检查其他条件
        for condition in self.conditions:
            if not condition.check(context):
                return False, condition.description or "条件不满足"

        return True, ""

    def to_dict(self) -> Dict:
        return {
            "choice_id": self.choice_id,
            "text": self.text,
            "outcome_text": self.outcome_text,
            "conditions": [c.to_dict() for c in self.conditions],
            "required_affection": self.required_affection,
            "effects": [e.to_dict() for e in self.effects],
            "next_event_id": self.next_event_id,
            "trigger_narrative_id": self.trigger_narrative_id,
            "trigger_story_node": self.trigger_story_node,
            "affection_change": self.affection_change,
            "mood_change": self.mood_change,
            "npc_affection_change": self.npc_affection_change,
            "unlock_achievement": self.unlock_achievement
        }

    @classmethod
    def from_dict(cls, data: Dict, index: int = 0) -> "SchoolEventChoice":
        choice = cls(
            choice_id=data.get("choice_id", f"choice_{index}"),
            text=data.get("text", ""),
            outcome_text=data.get("outcome_text", "")
        )

        choice.conditions = [
            EventCondition.from_dict(c) for c in data.get("conditions", [])
        ]
        choice.required_affection = data.get("required_affection", 0)
        choice.effects = [EventEffect.from_dict(e) for e in data.get("effects", [])]

        choice.next_event_id = data.get("next_event_id", "")
        choice.trigger_narrative_id = data.get("trigger_narrative_id", "")
        choice.trigger_story_node = data.get("trigger_story_node", "")

        # 兼容旧版
        choice.affection_change = data.get("affection_change", 0)
        choice.mood_change = data.get("mood_change", 0)
        choice.npc_affection_change = data.get("npc_affection_change", {})
        choice.unlock_achievement = data.get("unlock_achievement", "")

        return choice


@dataclass
class SchoolEvent:
    """学校事件"""
    event_id: str
    title: str
    description: str
    event_type: EventType = EventType.RANDOM

    # 选项
    choices: List[SchoolEventChoice] = field(default_factory=list)

    # 触发条件
    conditions: List[EventCondition] = field(default_factory=list)
    min_affection: int = 0
    prerequisites: List[str] = field(default_factory=list)  # 前置事件ID

    # 属性
    weight: int = 10                    # 权重
    priority: EventPriority = EventPriority.NORMAL
    repeatable: bool = True
    cooldown_minutes: int = 30          # 冷却时间（分钟）

    # 关联
    related_npc: str = ""               # 关联NPC
    related_location: str = ""          # 关联地点
    related_story_line: str = ""        # 关联剧情线

    # 时间限制
    valid_time_periods: List[str] = field(default_factory=list)
    valid_days: List[int] = field(default_factory=list)  # 0-6 周一到周日
    valid_seasons: List[str] = field(default_factory=list)

    # 内容增强
    speaker: str = ""                   # 说话者
    background: str = ""                # 背景图
    bgm: str = ""                       # 背景音乐

    # 效果（所有选项共有）
    common_effects: List[EventEffect] = field(default_factory=list)

    # 运行时状态
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    # 显示
    icon: str = ""
    color: str = ""

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type.value,
            "choices": [c.to_dict() for c in self.choices],
            "conditions": [c.to_dict() for c in self.conditions],
            "min_affection": self.min_affection,
            "prerequisites": self.prerequisites,
            "weight": self.weight,
            "priority": self.priority.value,
            "repeatable": self.repeatable,
            "cooldown_minutes": self.cooldown_minutes,
            "related_npc": self.related_npc,
            "related_location": self.related_location,
            "related_story_line": self.related_story_line,
            "valid_time_periods": self.valid_time_periods,
            "valid_days": self.valid_days,
            "valid_seasons": self.valid_seasons,
            "speaker": self.speaker,
            "background": self.background,
            "bgm": self.bgm,
            "common_effects": [e.to_dict() for e in self.common_effects],
            "icon": self.icon,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SchoolEvent":
        event = cls(
            event_id=data.get("event_id", data.get("id", "")),
            title=data.get("title", ""),
            description=data.get("description", ""),
            event_type=EventType(data.get("event_type", data.get("type", "random")))
        )

        # 解析选项
        for i, c in enumerate(data.get("choices", [])):
            event.choices.append(SchoolEventChoice.from_dict(c, i))

        # 解析条件
        event.conditions = [
            EventCondition.from_dict(c) for c in data.get("conditions", [])
        ]

        event.min_affection = data.get("min_affection", 0)
        event.prerequisites = data.get("prerequisites", [])

        event.weight = data.get("weight", 10)
        event.priority = EventPriority(data.get("priority", 5))
        event.repeatable = data.get("repeatable", True)
        event.cooldown_minutes = data.get("cooldown_minutes", 30)

        event.related_npc = data.get("related_npc", "")
        event.related_location = data.get("related_location", "")
        event.related_story_line = data.get("related_story_line", "")

        event.valid_time_periods = data.get("valid_time_periods", [])
        event.valid_days = data.get("valid_days", [])
        event.valid_seasons = data.get("valid_seasons", [])

        event.speaker = data.get("speaker", "")
        event.background = data.get("background", "")
        event.bgm = data.get("bgm", "")

        event.common_effects = [
            EventEffect.from_dict(e) for e in data.get("common_effects", [])
        ]

        event.icon = data.get("icon", "")
        event.color = data.get("color", "")

        return event


class SchoolEventManager:
    """
    学校事件管理器 (升级版)

    功能:
    1. 管理和触发事件
    2. 与各系统集成
    3. 智能事件选择
    4. 事件链和叙事
    """

    def __init__(self, pet_system=None, npc_manager=None, time_manager=None,
                 location_manager=None, story_tracker=None, action_manager=None):
        self.pet_system = pet_system
        self.npc_manager = npc_manager
        self.time_manager = time_manager
        self.location_manager = location_manager
        self.story_tracker = story_tracker
        self.action_manager = action_manager

        # 事件数据
        self.events: Dict[str, SchoolEvent] = {}

        # 当前状态
        self.active_event: Optional[SchoolEvent] = None
        self.event_queue: List[str] = []  # 待触发事件队列

        # 历史记录
        self.event_history: List[Dict] = []

        # 辅助数据
        self.diary_data: Dict = {}
        self.npc_data: Dict = {}

        # 回调
        self.on_event_triggered: Optional[Callable] = None
        self.on_event_completed: Optional[Callable] = None

        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载数据"""
        self._load_events()
        self._load_diary_content()
        self._load_npc_data()

    def _load_events(self):
        """加载事件"""
        # 创建默认事件
        self._create_default_events()

        # 从文件加载
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "school_events.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for item in data:
                    event = SchoolEvent.from_dict(item)
                    self.events[event.event_id] = event

                logger.info(f"加载了 {len(data)} 个外部事件")
        except Exception as e:
            logger.warning(f"加载外部事件失败: {e}")

    def _create_default_events(self):
        """创建默认事件"""
        default_events = [
            # 随机日常事件
            SchoolEvent(
                event_id="morning_greeting",
                title="早晨的问候",
                description="走进校门，微风拂面，新的一天开始了。",
                event_type=EventType.RANDOM,
                choices=[
                    SchoolEventChoice(
                        choice_id="greet_friendly",
                        text="元气满满地和同学打招呼",
                        outcome_text="你热情地和路过的同学打招呼，大家都回以微笑。",
                        effects=[
                            EventEffect("mood", "", 5),
                            EventEffect("affection", "", 2)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="walk_quietly",
                        text="安静地走向教室",
                        outcome_text="你默默地走向教室，享受清晨的宁静。",
                        effects=[
                            EventEffect("mood", "", 2)
                        ]
                    ),
                ],
                valid_time_periods=["early_morning", "morning"],
                weight=15,
                icon="🌅"
            ),

            # NPC相关事件
            SchoolEvent(
                event_id="xiaoxia_library_encounter",
                title="图书馆的偶遇",
                description="你在图书馆看书时，小夏悄悄坐到了你旁边...",
                event_type=EventType.NPC_INTERACTION,
                related_npc="xiaoxia",
                related_location="library",
                conditions=[
                    EventCondition("npc_present", "xiaoxia"),
                    EventCondition("location", "library")
                ],
                choices=[
                    SchoolEventChoice(
                        choice_id="start_chat",
                        text="主动搭话",
                        outcome_text="你们聊起了最近在看的书，气氛很融洽。",
                        effects=[
                            EventEffect("npc_affection", "xiaoxia", 10),
                            EventEffect("affection", "", 5)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="continue_reading",
                        text="继续专注看书",
                        outcome_text="你们各自安静地看着书，偶尔交换一个眼神。",
                        effects=[
                            EventEffect("npc_affection", "xiaoxia", 3)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="recommend_book",
                        text="推荐一本书给她",
                        outcome_text="\"这本书很好看哦！\" 小夏接过书，眼睛亮了起来。",
                        required_affection=50,
                        effects=[
                            EventEffect("npc_affection", "xiaoxia", 15),
                            EventEffect("affection", "", 8)
                        ]
                    ),
                ],
                min_affection=20,
                weight=20,
                speaker="xiaoxia",
                icon="📚"
            ),

            # 地点触发事件
            SchoolEvent(
                event_id="rooftop_view",
                title="天台的风景",
                description="你来到天台，城市的风景尽收眼底。微风轻拂，思绪飘远...",
                event_type=EventType.LOCATION,
                related_location="rooftop",
                conditions=[
                    EventCondition("location", "rooftop")
                ],
                choices=[
                    SchoolEventChoice(
                        choice_id="enjoy_view",
                        text="静静欣赏风景",
                        outcome_text="你深呼吸，感受这片刻的宁静。心情变得很平静。",
                        effects=[
                            EventEffect("mood", "", 15)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="think_story",
                        text="构思小说情节",
                        outcome_text="俯瞰校园，灵感涌现。你在脑海中勾勒出新的故事线索。",
                        effects=[
                            EventEffect("flag", "got_inspiration", True),
                            EventEffect("mood", "", 10)
                        ]
                    ),
                ],
                valid_time_periods=["afternoon", "evening"],
                weight=12,
                icon="🌆"
            ),

            # 特殊日期事件
            SchoolEvent(
                event_id="sakura_festival",
                title="樱花祭的邀请",
                description="樱花祭就要到了，走廊里贴满了宣传海报...",
                event_type=EventType.SPECIAL,
                conditions=[
                    EventCondition("special_date", "cherry_blossom_festival")
                ],
                choices=[
                    SchoolEventChoice(
                        choice_id="join_preparation",
                        text="参与准备工作",
                        outcome_text="你和同学们一起布置会场，忙碌而充实。",
                        effects=[
                            EventEffect("affection", "", 10),
                            EventEffect("flag", "helped_festival", True)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="invite_xiaoxia",
                        text="邀请小夏一起参加",
                        outcome_text="\"一起去看樱花吗？\" 小夏脸红了一下，轻轻点头。",
                        required_affection=100,
                        effects=[
                            EventEffect("npc_affection", "xiaoxia", 25),
                            EventEffect("flag", "festival_date_xiaoxia", True)
                        ],
                        trigger_story_node="xiaoxia_festival_date"
                    ),
                ],
                priority=EventPriority.HIGH,
                weight=30,
                repeatable=False,
                icon="🌸"
            ),

            # 午餐事件
            SchoolEvent(
                event_id="lunch_time",
                title="午餐时间",
                description="肚子咕咕叫了起来，该去吃午饭了。",
                event_type=EventType.SCHEDULED,
                valid_time_periods=["noon"],
                choices=[
                    SchoolEventChoice(
                        choice_id="cafeteria",
                        text="去食堂吃饭",
                        outcome_text="你来到热闹的食堂，选了一份看起来不错的套餐。",
                        effects=[
                            EventEffect("mood", "", 5)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="convenience_store",
                        text="去便利店买东西",
                        outcome_text="你买了一份便当和一瓶饮料，找了个安静的地方享用。",
                        effects=[
                            EventEffect("mood", "", 3)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="club_room",
                        text="在社团室吃便当",
                        outcome_text="你带着便当来到文学社，也许能遇到社员一起吃。",
                        effects=[
                            EventEffect("mood", "", 5),
                            EventEffect("affection", "", 3)
                        ]
                    ),
                ],
                weight=20,
                icon="🍱"
            ),

            # 社团活动事件
            SchoolEvent(
                event_id="club_meeting",
                title="文学社例会",
                description="今天是文学社的例行活动日，社员们陆续到来。",
                event_type=EventType.SCHEDULED,
                related_location="club_room_literature",
                conditions=[
                    EventCondition("day_of_week", "", "in", [2, 4]),  # 周三和周五
                    EventCondition("time_period", "", "in", ["afternoon", "evening"])
                ],
                choices=[
                    SchoolEventChoice(
                        choice_id="participate_actively",
                        text="积极参与讨论",
                        outcome_text="你分享了自己的想法，获得了大家的认可。",
                        effects=[
                            EventEffect("affection", "", 8),
                            EventEffect("flag", "active_member", True)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="listen_quietly",
                        text="安静地聆听",
                        outcome_text="你认真听着前辈们的讨论，学到了很多。",
                        effects=[
                            EventEffect("affection", "", 3)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="read_submission",
                        text="朗读自己的作品",
                        outcome_text="你鼓起勇气朗读了自己的作品，心跳加速...",
                        required_affection=80,
                        effects=[
                            EventEffect("affection", "", 15),
                            EventEffect("achievement", "brave_reader", True)
                        ]
                    ),
                ],
                weight=25,
                priority=EventPriority.HIGH,
                icon="📝"
            ),

            # 下雨事件
            SchoolEvent(
                event_id="rainy_day",
                title="突然下雨了",
                description="天空突然暗了下来，雨点噼里啪啦地落下...",
                event_type=EventType.RANDOM,
                conditions=[
                    EventCondition("weather", "rainy")
                ],
                choices=[
                    SchoolEventChoice(
                        choice_id="wait_inside",
                        text="在走廊等雨停",
                        outcome_text="你靠在栏杆上，听着雨声，思绪飘远。",
                        effects=[
                            EventEffect("mood", "", 5)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="run_in_rain",
                        text="冒雨奔跑",
                        outcome_text="你冲进雨中，感受雨水打在脸上的清凉。有点冷，但很爽快！",
                        effects=[
                            EventEffect("mood", "", 10)
                        ]
                    ),
                    SchoolEventChoice(
                        choice_id="share_umbrella",
                        text="和遇到的人一起打伞",
                        outcome_text="\"一起走吧！\" 你们挤在一把伞下，距离突然变近了...",
                        conditions=[
                            EventCondition("npc_present", "xiaoxia")
                        ],
                        effects=[
                            EventEffect("npc_affection", "xiaoxia", 20),
                            EventEffect("affection", "", 10)
                        ]
                    ),
                ],
                weight=15,
                icon="🌧️"
            ),
        ]

        for event in default_events:
            self.events[event.event_id] = event

        logger.info(f"创建了 {len(default_events)} 个默认事件")

    def _load_diary_content(self) -> Dict:
        """加载日记内容"""
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "diary_content.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.diary_data = json.load(f)
        except Exception as e:
            logger.warning(f"加载日记内容失败: {e}")

    def _load_npc_data(self) -> Dict:
        """加载NPC数据"""
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "npc_data.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.npc_data = json.load(f)
        except Exception as e:
            logger.warning(f"加载NPC数据失败: {e}")

    # ============================================================
    # 上下文构建
    # ============================================================

    def _build_context(self) -> Dict:
        """构建事件检查上下文"""
        context = {
            "affection": 0,
            "current_location": "",
            "time_period": "",
            "day_of_week": 0,
            "is_weekend": False,
            "season": "",
            "weather": "",
            "special_date_id": None,
            "flags": {},
            "completed_events": set(),
            "npc_affections": {},
            "npc_phases": {},
            "npcs_at_location": []
        }

        # 从pet_system获取基础信息
        if self.pet_system:
            context["affection"] = self.pet_system.data.affection
            context["completed_events"] = self.pet_system.data.completed_events

        # 从time_manager获取时间信息
        if self.time_manager:
            game_time = self.time_manager.get_current_time()
            context["time_period"] = game_time.period.value
            context["day_of_week"] = game_time.day_of_week.value
            context["is_weekend"] = self.time_manager.is_weekend()
            context["season"] = self.time_manager.get_season().value
            context["weather"] = self.time_manager.get_weather().value

            special_date = self.time_manager.get_current_special_date()
            if special_date:
                context["special_date_id"] = special_date.date_id

        # 从location_manager获取位置信息
        if self.location_manager:
            context["current_location"] = self.location_manager.current_location

        # 从npc_manager获取NPC信息
        if self.npc_manager:
            for npc_id in ["xiaoxia", "xuechang", "meimei"]:
                relation = self.npc_manager.get_relation(npc_id)
                if relation:
                    context["npc_affections"][npc_id] = relation.affection
                    context["npc_phases"][npc_id] = relation.phase.value

        # 获取当前位置的NPC
        if self.time_manager and context["current_location"]:
            context["npcs_at_location"] = self.time_manager.get_npcs_at_location(
                context["current_location"]
            )

        # 从story_tracker获取标志
        if self.story_tracker:
            context["flags"] = self.story_tracker.flags

        return context

    # ============================================================
    # 事件选择
    # ============================================================

    def get_available_events(self) -> List[SchoolEvent]:
        """获取所有可用事件"""
        context = self._build_context()
        available = []
        now = datetime.now()

        for event in self.events.values():
            # 检查基础条件
            if not self._check_event_availability(event, context, now):
                continue

            available.append(event)

        return available

    def _check_event_availability(self, event: SchoolEvent, context: Dict,
                                   now: datetime) -> bool:
        """检查事件是否可触发"""
        # 检查好感度
        if event.min_affection > context.get("affection", 0):
            return False

        # 检查重复性
        if not event.repeatable:
            if event.event_id in context.get("completed_events", set()):
                return False

        # 检查冷却
        if event.last_triggered:
            elapsed = (now - event.last_triggered).total_seconds()
            if elapsed < event.cooldown_minutes * 60:
                return False

        # 检查前置事件
        for prereq in event.prerequisites:
            if prereq not in context.get("completed_events", set()):
                return False

        # 检查时间段
        if event.valid_time_periods:
            if context.get("time_period") not in event.valid_time_periods:
                return False

        # 检查星期
        if event.valid_days:
            if context.get("day_of_week") not in event.valid_days:
                return False

        # 检查季节
        if event.valid_seasons:
            if context.get("season") not in event.valid_seasons:
                return False

        # 检查所有条件
        for condition in event.conditions:
            if not condition.check(context):
                return False

        return True

    def get_random_event(self) -> Optional[SchoolEvent]:
        """获取随机事件"""
        # 先检查事件队列
        if self.event_queue:
            next_id = self.event_queue.pop(0)
            if next_id in self.events:
                event = self.events[next_id]
                self.active_event = event
                return event

        available = self.get_available_events()
        if not available:
            return None

        context = self._build_context()
        now = datetime.now()

        # 计算动态权重
        weighted_events = []
        for event in available:
            weight = self._calculate_dynamic_weight(event, context, now)
            if weight > 0:
                weighted_events.append((event, weight))

        if not weighted_events:
            return None

        # 按优先级排序后加权选择
        weighted_events.sort(key=lambda x: -x[0].priority.value)

        # 优先触发高优先级事件
        high_priority = [e for e in weighted_events if e[0].priority.value >= EventPriority.HIGH.value]
        if high_priority and random.random() < 0.7:  # 70%概率触发高优先级
            events, weights = zip(*high_priority)
        else:
            events, weights = zip(*weighted_events)

        event = random.choices(events, weights=weights, k=1)[0]

        self.active_event = event
        event.last_triggered = now
        event.trigger_count += 1

        if self.on_event_triggered:
            self.on_event_triggered(event)

        return event

    def _calculate_dynamic_weight(self, event: SchoolEvent, context: Dict,
                                   now: datetime) -> float:
        """计算动态权重"""
        weight = float(event.weight)

        # 时间相关调整
        hour = now.hour
        is_lunch = 11 <= hour <= 13
        is_dinner = 17 <= hour <= 19
        is_night = hour >= 22 or hour <= 5

        # 根据事件标题和类型调整
        title = event.title.lower()

        if "午餐" in event.title or "食堂" in event.title:
            weight *= 3 if is_lunch else (2 if is_dinner else 0.2)

        if "深夜" in event.title or "夜" in event.title:
            weight *= 2.5 if is_night else 0.1

        # NPC相关事件：如果NPC在场，增加权重
        if event.related_npc:
            if event.related_npc in context.get("npcs_at_location", []):
                weight *= 2

        # 地点相关事件：如果在相关地点，增加权重
        if event.related_location:
            if event.related_location == context.get("current_location"):
                weight *= 2
            else:
                weight *= 0.3  # 不在相关地点时降低

        # 天气相关调整
        weather = context.get("weather", "")
        if "雨" in event.title and weather == "rainy":
            weight *= 3
        elif "雪" in event.title and weather == "snowy":
            weight *= 3

        # 剧情事件加成
        if event.event_type == EventType.STORY:
            weight *= 1.5

        # 避免权重过低
        return max(1, weight)

    # ============================================================
    # 事件处理
    # ============================================================

    def trigger_event(self, event_id: str) -> Optional[Dict]:
        """
        直接触发指定事件

        Returns:
            事件数据
        """
        event = self.events.get(event_id)
        if not event:
            return None

        self.active_event = event
        event.last_triggered = datetime.now()
        event.trigger_count += 1

        if self.on_event_triggered:
            self.on_event_triggered(event)

        return self._format_event_for_display(event)

    def _format_event_for_display(self, event: SchoolEvent) -> Dict:
        """格式化事件用于显示"""
        context = self._build_context()
        type_display = EVENT_TYPE_DISPLAY.get(event.event_type, {})

        # 格式化选项
        choices = []
        for i, choice in enumerate(event.choices):
            available, reason = choice.is_available(context)

            choice_data = {
                "index": i,
                "choice_id": choice.choice_id,
                "text": choice.text,
                "available": available,
                "reason": reason
            }

            # 添加好感度要求提示
            if choice.required_affection > 0:
                choice_data["text"] = f"{choice.text} (需好感{choice.required_affection})"

            choices.append(choice_data)

        return {
            "event_id": event.event_id,
            "title": event.title,
            "description": event.description,
            "event_type": event.event_type.value,
            "type_name": type_display.get("name", ""),
            "type_icon": type_display.get("icon", ""),
            "choices": choices,
            "speaker": event.speaker,
            "background": event.background,
            "bgm": event.bgm,
            "icon": event.icon or type_display.get("icon", "🎲")
        }

    def process_choice(self, choice_index: int) -> Dict:
        """
        处理玩家选择

        Returns:
            处理结果
        """
        if not self.active_event:
            return {"success": False, "message": "没有活动事件"}

        if choice_index >= len(self.active_event.choices):
            return {"success": False, "message": "无效的选择"}

        choice = self.active_event.choices[choice_index]
        context = self._build_context()

        # 检查选项条件
        available, reason = choice.is_available(context)
        if not available:
            return {
                "success": False,
                "message": reason or "条件不满足"
            }

        # 应用效果
        effects_applied = []

        # 应用选项效果
        for effect in choice.effects:
            result = effect.apply(context, self)
            effects_applied.append(result)

        # 应用共有效果
        for effect in self.active_event.common_effects:
            result = effect.apply(context, self)
            effects_applied.append(result)

        # 兼容旧版效果
        if choice.affection_change:
            if self.pet_system:
                self.pet_system.add_affection(choice.affection_change)
            effects_applied.append({
                "type": "affection",
                "change": choice.affection_change
            })

        if choice.mood_change:
            if self.pet_system:
                self.pet_system.update_mood(choice.mood_change)
            effects_applied.append({
                "type": "mood",
                "change": choice.mood_change
            })

        for npc_id, change in choice.npc_affection_change.items():
            if self.npc_manager:
                self.npc_manager.change_affection(npc_id, change)
            effects_applied.append({
                "type": "npc_affection",
                "target": npc_id,
                "change": change
            })

        if choice.unlock_achievement:
            if self.story_tracker:
                self.story_tracker.unlock_achievement(choice.unlock_achievement)

        # 记录完成
        if self.pet_system:
            self.pet_system.data.completed_events.add(self.active_event.event_id)

        # 记录历史
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_id": self.active_event.event_id,
            "title": self.active_event.title,
            "choice_id": choice.choice_id,
            "choice_text": choice.text,
            "outcome_text": choice.outcome_text,
            "effects": effects_applied
        }
        self.event_history.insert(0, history_entry)
        if len(self.event_history) > 100:
            self.event_history = self.event_history[:100]

        # 处理日记
        diary_unlocked = False
        event_diaries = self.diary_data.get(self.active_event.event_id)
        if event_diaries and self.pet_system:
            content = event_diaries.get(str(choice_index))
            if content:
                diary_unlocked = self.pet_system.add_diary_entry(
                    event_id=self.active_event.event_id,
                    title=self.active_event.title,
                    content=content,
                    choice_index=choice_index
                )

        # 处理后续事件
        next_event = None
        if choice.next_event_id:
            self.event_queue.insert(0, choice.next_event_id)
            next_event = self.events.get(choice.next_event_id)

        # 触发剧情节点
        if choice.trigger_story_node and self.story_tracker:
            self.story_tracker.trigger_node(choice.trigger_story_node)

        # 回调
        if self.on_event_completed:
            self.on_event_completed(self.active_event, choice)

        # 构建结果消息
        result_message = choice.outcome_text

        # 添加效果描述
        effect_descriptions = []
        for effect in effects_applied:
            if "description" in effect:
                effect_descriptions.append(effect["description"])
            elif effect.get("type") == "affection" and effect.get("change"):
                change = effect["change"]
                effect_descriptions.append(f"好感度 {'+'if change > 0 else ''}{change}")
            elif effect.get("type") == "npc_affection":
                npc_name = effect.get("target", "")
                change = effect.get("change", 0)
                effect_descriptions.append(f"{npc_name} {'+'if change > 0 else ''}{change}")

        if effect_descriptions:
            result_message += "\n\n" + " | ".join(effect_descriptions)

        if diary_unlocked:
            result_message += "\n\n📖 【日记已更新】"

        current_event = self.active_event
        self.active_event = next_event

        return {
            "success": True,
            "message": result_message,
            "effects": effects_applied,
            "diary_unlocked": diary_unlocked,
            "next_event": self._format_event_for_display(next_event) if next_event else None,
            "trigger_narrative_id": choice.trigger_narrative_id,
            "trigger_story_node": choice.trigger_story_node
        }

    # ============================================================
    # 查询方法
    # ============================================================

    def get_event(self, event_id: str) -> Optional[SchoolEvent]:
        """获取事件"""
        return self.events.get(event_id)

    def get_events_by_type(self, event_type: EventType) -> List[SchoolEvent]:
        """按类型获取事件"""
        return [e for e in self.events.values() if e.event_type == event_type]

    def get_npc_events(self, npc_id: str) -> List[SchoolEvent]:
        """获取NPC相关事件"""
        return [e for e in self.events.values() if e.related_npc == npc_id]

    def get_location_events(self, location_id: str) -> List[SchoolEvent]:
        """获取地点相关事件"""
        return [e for e in self.events.values() if e.related_location == location_id]

    def get_event_history(self, limit: int = 20) -> List[Dict]:
        """获取事件历史"""
        return self.event_history[:limit]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        completed = set()
        if self.pet_system:
            completed = self.pet_system.data.completed_events

        total = len(self.events)
        completed_count = len(completed)

        by_type = {}
        for event_type in EventType:
            type_events = self.get_events_by_type(event_type)
            type_completed = sum(1 for e in type_events if e.event_id in completed)
            by_type[event_type.value] = {
                "total": len(type_events),
                "completed": type_completed
            }

        return {
            "total_events": total,
            "completed_events": completed_count,
            "completion_rate": completed_count / total if total > 0 else 0,
            "by_type": by_type,
            "history_count": len(self.event_history)
        }


# 便捷函数
def create_event_manager(pet_system=None, npc_manager=None, time_manager=None,
                         location_manager=None, story_tracker=None,
                         action_manager=None) -> SchoolEventManager:
    """创建事件管理器"""
    return SchoolEventManager(
        pet_system=pet_system,
        npc_manager=npc_manager,
        time_manager=time_manager,
        location_manager=location_manager,
        story_tracker=story_tracker,
        action_manager=action_manager
    )
