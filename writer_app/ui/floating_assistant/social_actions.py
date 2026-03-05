"""
悬浮助手 - 社交行动系统 (Social Actions System)
管理玩家与NPC之间的互动行为、效果计算、条件检查
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ActionCategory(Enum):
    """行动类别"""
    CONVERSATION = "conversation"       # 对话
    GIFT = "gift"                       # 送礼
    ACTIVITY = "activity"               # 活动
    SPECIAL = "special"                 # 特殊行动
    ROMANTIC = "romantic"               # 浪漫行动
    HELP = "help"                       # 帮助
    STUDY = "study"                     # 学习


class ActionResult(Enum):
    """行动结果"""
    SUCCESS = "success"                 # 成功
    PARTIAL_SUCCESS = "partial"         # 部分成功
    NEUTRAL = "neutral"                 # 中性结果
    FAILURE = "failure"                 # 失败
    CRITICAL_SUCCESS = "critical"       # 大成功
    REJECTED = "rejected"               # 被拒绝


class ActionCost(Enum):
    """行动消耗类型"""
    TIME = "time"                       # 时间
    ENERGY = "energy"                   # 精力
    MONEY = "money"                     # 金钱
    ITEM = "item"                       # 物品
    REPUTATION = "reputation"           # 声望


# 行动类别显示配置
ACTION_CATEGORY_DISPLAY = {
    ActionCategory.CONVERSATION: {"name": "对话", "icon": "💬", "color": "#4CAF50"},
    ActionCategory.GIFT: {"name": "送礼", "icon": "🎁", "color": "#E91E63"},
    ActionCategory.ACTIVITY: {"name": "活动", "icon": "🎯", "color": "#2196F3"},
    ActionCategory.SPECIAL: {"name": "特殊", "icon": "⭐", "color": "#FF9800"},
    ActionCategory.ROMANTIC: {"name": "浪漫", "icon": "💕", "color": "#F48FB1"},
    ActionCategory.HELP: {"name": "帮助", "icon": "🤝", "color": "#00BCD4"},
    ActionCategory.STUDY: {"name": "学习", "icon": "📚", "color": "#9C27B0"},
}

# 行动结果显示配置
ACTION_RESULT_DISPLAY = {
    ActionResult.SUCCESS: {"name": "成功", "icon": "✅", "color": "#4CAF50"},
    ActionResult.PARTIAL_SUCCESS: {"name": "还行", "icon": "👍", "color": "#8BC34A"},
    ActionResult.NEUTRAL: {"name": "一般", "icon": "😐", "color": "#9E9E9E"},
    ActionResult.FAILURE: {"name": "失败", "icon": "❌", "color": "#F44336"},
    ActionResult.CRITICAL_SUCCESS: {"name": "大成功", "icon": "🌟", "color": "#FFD700"},
    ActionResult.REJECTED: {"name": "被拒绝", "icon": "🚫", "color": "#D32F2F"},
}


@dataclass
class ActionCondition:
    """行动条件"""
    condition_type: str                 # 条件类型
    target: str                         # 目标
    operator: str = ">="                # 比较符
    value: Any = 0                      # 值
    description: str = ""               # 条件描述

    def check(self, context: Dict) -> Tuple[bool, str]:
        """
        检查条件是否满足

        Args:
            context: 包含各种状态值的上下文

        Returns:
            (是否满足, 原因)
        """
        actual_value = context.get(self.target, 0)

        if self.operator == ">=":
            result = actual_value >= self.value
        elif self.operator == ">":
            result = actual_value > self.value
        elif self.operator == "<=":
            result = actual_value <= self.value
        elif self.operator == "<":
            result = actual_value < self.value
        elif self.operator == "==":
            result = actual_value == self.value
        elif self.operator == "!=":
            result = actual_value != self.value
        elif self.operator == "in":
            result = actual_value in self.value
        elif self.operator == "has":
            result = self.value in actual_value if isinstance(actual_value, (list, set)) else False
        else:
            result = False

        if result:
            return True, ""
        return False, self.description or f"需要{self.target} {self.operator} {self.value}"

    def to_dict(self) -> Dict:
        return {
            "condition_type": self.condition_type,
            "target": self.target,
            "operator": self.operator,
            "value": self.value,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ActionCondition":
        return cls(
            condition_type=data.get("condition_type", ""),
            target=data.get("target", ""),
            operator=data.get("operator", ">="),
            value=data.get("value", 0),
            description=data.get("description", "")
        )


@dataclass
class ActionEffect:
    """行动效果"""
    effect_type: str                    # 效果类型
    target: str                         # 目标
    value: Any = 0                      # 值
    is_percentage: bool = False         # 是否百分比
    condition: str = ""                 # 生效条件

    def apply(self, context: Dict) -> Dict:
        """
        应用效果

        Returns:
            变化信息
        """
        old_value = context.get(self.target, 0)

        if self.is_percentage:
            change = int(old_value * self.value / 100)
        else:
            change = self.value

        new_value = old_value + change

        return {
            "target": self.target,
            "old_value": old_value,
            "new_value": new_value,
            "change": change
        }

    def to_dict(self) -> Dict:
        return {
            "effect_type": self.effect_type,
            "target": self.target,
            "value": self.value,
            "is_percentage": self.is_percentage,
            "condition": self.condition
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ActionEffect":
        return cls(
            effect_type=data.get("effect_type", ""),
            target=data.get("target", ""),
            value=data.get("value", 0),
            is_percentage=data.get("is_percentage", False),
            condition=data.get("condition", "")
        )


@dataclass
class SocialAction:
    """社交行动定义"""
    action_id: str
    name: str
    category: ActionCategory
    description: str = ""

    # 条件
    conditions: List[ActionCondition] = field(default_factory=list)
    required_phase: str = ""            # 需要的关系阶段
    required_location: str = ""         # 需要在特定地点
    required_time_periods: List[str] = field(default_factory=list)  # 需要的时间段
    required_items: List[str] = field(default_factory=list)  # 需要的物品

    # 效果
    success_effects: List[ActionEffect] = field(default_factory=list)
    failure_effects: List[ActionEffect] = field(default_factory=list)

    # 消耗
    time_cost: int = 1                  # 时间消耗（时间段数）
    energy_cost: int = 0                # 精力消耗
    money_cost: int = 0                 # 金钱消耗

    # 成功率
    base_success_rate: float = 0.8      # 基础成功率
    affection_bonus: float = 0.001      # 好感度加成（每点好感）
    mood_modifier: float = 0.1          # 心情修正

    # 冷却
    cooldown_periods: int = 0           # 冷却时间段数
    daily_limit: int = 0                # 每日限制次数（0=无限）

    # 变体和响应
    dialogue_variants: Dict[str, List[str]] = field(default_factory=dict)
    npc_responses: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)

    # 解锁条件
    unlock_condition: str = ""
    is_hidden: bool = False

    # 显示
    icon: str = ""
    color: str = ""

    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "conditions": [c.to_dict() for c in self.conditions],
            "required_phase": self.required_phase,
            "required_location": self.required_location,
            "required_time_periods": self.required_time_periods,
            "required_items": self.required_items,
            "success_effects": [e.to_dict() for e in self.success_effects],
            "failure_effects": [e.to_dict() for e in self.failure_effects],
            "time_cost": self.time_cost,
            "energy_cost": self.energy_cost,
            "money_cost": self.money_cost,
            "base_success_rate": self.base_success_rate,
            "affection_bonus": self.affection_bonus,
            "mood_modifier": self.mood_modifier,
            "cooldown_periods": self.cooldown_periods,
            "daily_limit": self.daily_limit,
            "dialogue_variants": self.dialogue_variants,
            "npc_responses": self.npc_responses,
            "unlock_condition": self.unlock_condition,
            "is_hidden": self.is_hidden,
            "icon": self.icon,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SocialAction":
        action = cls(
            action_id=data.get("action_id", ""),
            name=data.get("name", ""),
            category=ActionCategory(data.get("category", "conversation")),
            description=data.get("description", "")
        )

        action.conditions = [ActionCondition.from_dict(c) for c in data.get("conditions", [])]
        action.required_phase = data.get("required_phase", "")
        action.required_location = data.get("required_location", "")
        action.required_time_periods = data.get("required_time_periods", [])
        action.required_items = data.get("required_items", [])

        action.success_effects = [ActionEffect.from_dict(e) for e in data.get("success_effects", [])]
        action.failure_effects = [ActionEffect.from_dict(e) for e in data.get("failure_effects", [])]

        action.time_cost = data.get("time_cost", 1)
        action.energy_cost = data.get("energy_cost", 0)
        action.money_cost = data.get("money_cost", 0)

        action.base_success_rate = data.get("base_success_rate", 0.8)
        action.affection_bonus = data.get("affection_bonus", 0.001)
        action.mood_modifier = data.get("mood_modifier", 0.1)

        action.cooldown_periods = data.get("cooldown_periods", 0)
        action.daily_limit = data.get("daily_limit", 0)

        action.dialogue_variants = data.get("dialogue_variants", {})
        action.npc_responses = data.get("npc_responses", {})

        action.unlock_condition = data.get("unlock_condition", "")
        action.is_hidden = data.get("is_hidden", False)

        action.icon = data.get("icon", "")
        action.color = data.get("color", "")

        return action


@dataclass
class ActionHistory:
    """行动历史记录"""
    action_id: str
    npc_id: str
    timestamp: str
    result: ActionResult
    effects: List[Dict] = field(default_factory=list)
    dialogue: str = ""
    response: str = ""


class SocialActionManager:
    """
    社交行动管理器

    功能:
    1. 管理可用行动
    2. 检查行动条件
    3. 执行行动并计算效果
    4. 管理冷却和限制
    """

    def __init__(self, pet_system=None, npc_manager=None, time_manager=None):
        self.pet_system = pet_system
        self.npc_manager = npc_manager
        self.time_manager = time_manager

        # 行动定义
        self.actions: Dict[str, SocialAction] = {}

        # 行动历史
        self.action_history: List[ActionHistory] = []

        # 冷却状态 {action_id: 剩余冷却时间}
        self.cooldowns: Dict[str, int] = {}

        # 每日计数 {action_id: {npc_id: count}}
        self.daily_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.last_reset_date: str = ""

        # 已解锁的特殊行动
        self.unlocked_actions: Set[str] = set()

        # 回调
        self.on_action_executed: Optional[Callable] = None
        self.on_action_unlocked: Optional[Callable] = None

        # 加载数据
        self._load_actions()
        self._load_state()

    def _load_actions(self):
        """加载行动定义"""
        # 创建默认行动
        self._create_default_actions()

        # 尝试从文件加载
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "social_actions.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for action_data in data.get("actions", []):
                    action = SocialAction.from_dict(action_data)
                    self.actions[action.action_id] = action
        except Exception as e:
            logger.warning(f"加载行动定义失败: {e}")

    def _create_default_actions(self):
        """创建默认行动"""
        default_actions = [
            # 基础对话行动
            SocialAction(
                action_id="chat",
                name="闲聊",
                category=ActionCategory.CONVERSATION,
                description="和对方进行轻松的闲聊",
                time_cost=1,
                base_success_rate=0.9,
                success_effects=[
                    ActionEffect("affection", "affection", 3),
                    ActionEffect("intimacy", "intimacy", 1)
                ],
                dialogue_variants={
                    "default": [
                        "今天过得怎么样？",
                        "最近有什么有趣的事吗？",
                        "你在想什么？"
                    ]
                },
                icon="💬"
            ),
            SocialAction(
                action_id="deep_talk",
                name="深入交谈",
                category=ActionCategory.CONVERSATION,
                description="进行深入的话题交流，增进了解",
                time_cost=2,
                base_success_rate=0.7,
                conditions=[
                    ActionCondition("affection", "affection", ">=", 50, "需要好感度达到50")
                ],
                success_effects=[
                    ActionEffect("affection", "affection", 8),
                    ActionEffect("intimacy", "intimacy", 5)
                ],
                failure_effects=[
                    ActionEffect("affection", "affection", -2)
                ],
                dialogue_variants={
                    "default": [
                        "我想更了解你...",
                        "能和我分享你的想法吗？",
                        "我们聊聊更深入的话题吧"
                    ]
                },
                icon="💭"
            ),
            SocialAction(
                action_id="compliment",
                name="称赞",
                category=ActionCategory.CONVERSATION,
                description="真诚地称赞对方",
                time_cost=0,
                base_success_rate=0.85,
                daily_limit=3,
                success_effects=[
                    ActionEffect("affection", "affection", 5),
                    ActionEffect("mood", "mood", 10)
                ],
                failure_effects=[
                    ActionEffect("affection", "affection", -3),
                ],
                dialogue_variants={
                    "default": [
                        "你今天看起来很有精神呢",
                        "和你在一起很开心",
                        "你真的很厉害"
                    ]
                },
                icon="✨"
            ),

            # 送礼行动
            SocialAction(
                action_id="give_gift_small",
                name="送小礼物",
                category=ActionCategory.GIFT,
                description="送一份小礼物表达心意",
                time_cost=0,
                money_cost=50,
                base_success_rate=0.95,
                daily_limit=1,
                success_effects=[
                    ActionEffect("affection", "affection", 10)
                ],
                icon="🎁"
            ),
            SocialAction(
                action_id="give_gift_favorite",
                name="送喜欢的礼物",
                category=ActionCategory.GIFT,
                description="送对方喜欢的礼物",
                time_cost=0,
                money_cost=100,
                base_success_rate=1.0,
                daily_limit=1,
                success_effects=[
                    ActionEffect("affection", "affection", 25),
                    ActionEffect("mood", "mood", 20)
                ],
                icon="🎀"
            ),

            # 活动行动
            SocialAction(
                action_id="study_together",
                name="一起学习",
                category=ActionCategory.STUDY,
                description="一起在图书馆学习",
                time_cost=2,
                required_location="library",
                base_success_rate=0.8,
                success_effects=[
                    ActionEffect("affection", "affection", 8),
                    ActionEffect("intimacy", "intimacy", 3),
                    ActionEffect("study_progress", "study_progress", 10)
                ],
                icon="📖"
            ),
            SocialAction(
                action_id="eat_together",
                name="一起吃饭",
                category=ActionCategory.ACTIVITY,
                description="邀请对方一起吃饭",
                time_cost=1,
                required_time_periods=["noon", "evening"],
                base_success_rate=0.75,
                conditions=[
                    ActionCondition("affection", "affection", ">=", 30, "需要好感度达到30")
                ],
                success_effects=[
                    ActionEffect("affection", "affection", 12),
                    ActionEffect("intimacy", "intimacy", 5)
                ],
                icon="🍱"
            ),
            SocialAction(
                action_id="walk_together",
                name="一起散步",
                category=ActionCategory.ACTIVITY,
                description="邀请对方一起散步",
                time_cost=1,
                required_time_periods=["afternoon", "evening"],
                base_success_rate=0.7,
                conditions=[
                    ActionCondition("affection", "affection", ">=", 50, "需要好感度达到50")
                ],
                success_effects=[
                    ActionEffect("affection", "affection", 15),
                    ActionEffect("intimacy", "intimacy", 8)
                ],
                icon="🚶"
            ),
            SocialAction(
                action_id="club_activity",
                name="社团活动",
                category=ActionCategory.ACTIVITY,
                description="一起参加社团活动",
                time_cost=2,
                required_location="club_room_literature",
                required_time_periods=["afternoon", "evening"],
                base_success_rate=0.85,
                success_effects=[
                    ActionEffect("affection", "affection", 10),
                    ActionEffect("club_reputation", "club_reputation", 5)
                ],
                icon="🎭"
            ),

            # 帮助行动
            SocialAction(
                action_id="help_study",
                name="帮忙补习",
                category=ActionCategory.HELP,
                description="帮助对方学习",
                time_cost=2,
                energy_cost=10,
                base_success_rate=0.85,
                success_effects=[
                    ActionEffect("affection", "affection", 15),
                    ActionEffect("trust", "trust", 5)
                ],
                icon="📝"
            ),
            SocialAction(
                action_id="help_carry",
                name="帮忙搬东西",
                category=ActionCategory.HELP,
                description="帮对方搬运物品",
                time_cost=1,
                energy_cost=15,
                base_success_rate=0.95,
                success_effects=[
                    ActionEffect("affection", "affection", 8),
                    ActionEffect("trust", "trust", 3)
                ],
                icon="📦"
            ),
            SocialAction(
                action_id="comfort",
                name="安慰",
                category=ActionCategory.HELP,
                description="安慰心情不好的对方",
                time_cost=1,
                conditions=[
                    ActionCondition("target_mood", "mood", "<", 30, "对方心情需要较低")
                ],
                base_success_rate=0.7,
                success_effects=[
                    ActionEffect("affection", "affection", 20),
                    ActionEffect("trust", "trust", 10),
                    ActionEffect("target_mood", "mood", 30)
                ],
                icon="🤗"
            ),

            # 浪漫行动（需要解锁）
            SocialAction(
                action_id="hold_hands",
                name="牵手",
                category=ActionCategory.ROMANTIC,
                description="尝试牵起对方的手",
                time_cost=0,
                required_phase="close",
                base_success_rate=0.6,
                success_effects=[
                    ActionEffect("affection", "affection", 20),
                    ActionEffect("intimacy", "intimacy", 15)
                ],
                failure_effects=[
                    ActionEffect("affection", "affection", -10)
                ],
                unlock_condition="phase_close",
                is_hidden=True,
                icon="👫"
            ),
            SocialAction(
                action_id="watch_sunset",
                name="看夕阳",
                category=ActionCategory.ROMANTIC,
                description="一起看夕阳",
                time_cost=1,
                required_phase="close",
                required_time_periods=["evening"],
                required_location="rooftop",
                base_success_rate=0.8,
                success_effects=[
                    ActionEffect("affection", "affection", 25),
                    ActionEffect("intimacy", "intimacy", 20)
                ],
                unlock_condition="phase_close",
                is_hidden=True,
                icon="🌅"
            ),
            SocialAction(
                action_id="confession",
                name="告白",
                category=ActionCategory.SPECIAL,
                description="向对方表白心意",
                time_cost=1,
                required_phase="crush",
                conditions=[
                    ActionCondition("affection", "affection", ">=", 500, "需要好感度达到500"),
                    ActionCondition("intimacy", "intimacy", ">=", 100, "需要亲密度达到100")
                ],
                base_success_rate=0.5,
                affection_bonus=0.0005,
                success_effects=[
                    ActionEffect("affection", "affection", 100),
                    ActionEffect("phase", "phase", "lover")
                ],
                failure_effects=[
                    ActionEffect("affection", "affection", -50),
                    ActionEffect("cooldown", "confession_cooldown", 30)
                ],
                cooldown_periods=30,
                unlock_condition="affection_500",
                is_hidden=True,
                icon="💗"
            ),
        ]

        for action in default_actions:
            self.actions[action.action_id] = action

        logger.info(f"创建了 {len(default_actions)} 个默认行动")

    def _load_state(self):
        """加载状态"""
        if not self.pet_system:
            return

        try:
            state = getattr(self.pet_system.data, "social_actions_state", {}) or {}

            self.cooldowns = state.get("cooldowns", {})
            self.unlocked_actions = set(state.get("unlocked_actions", []))
            self.last_reset_date = state.get("last_reset_date", "")

            # 加载每日计数
            daily = state.get("daily_counts", {})
            for action_id, npc_counts in daily.items():
                for npc_id, count in npc_counts.items():
                    self.daily_counts[action_id][npc_id] = count

            # 加载历史
            for h in state.get("history", [])[-50:]:  # 只保留最近50条
                self.action_history.append(ActionHistory(
                    action_id=h.get("action_id", ""),
                    npc_id=h.get("npc_id", ""),
                    timestamp=h.get("timestamp", ""),
                    result=ActionResult(h.get("result", "neutral")),
                    effects=h.get("effects", []),
                    dialogue=h.get("dialogue", ""),
                    response=h.get("response", "")
                ))

            # 检查是否需要重置每日计数
            self._check_daily_reset()

        except Exception as e:
            logger.warning(f"加载行动状态失败: {e}")

    def _save_state(self):
        """保存状态"""
        if not self.pet_system:
            return

        try:
            state = {
                "cooldowns": self.cooldowns,
                "unlocked_actions": list(self.unlocked_actions),
                "daily_counts": {
                    action_id: dict(npc_counts)
                    for action_id, npc_counts in self.daily_counts.items()
                },
                "last_reset_date": self.last_reset_date,
                "history": [
                    {
                        "action_id": h.action_id,
                        "npc_id": h.npc_id,
                        "timestamp": h.timestamp,
                        "result": h.result.value,
                        "effects": h.effects,
                        "dialogue": h.dialogue,
                        "response": h.response
                    }
                    for h in self.action_history[-50:]
                ]
            }
            self.pet_system.data.social_actions_state = state
            self.pet_system.save()
        except Exception as e:
            logger.warning(f"保存行动状态失败: {e}")

    def _check_daily_reset(self):
        """检查并重置每日计数"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_reset_date != today:
            self.daily_counts = defaultdict(lambda: defaultdict(int))
            self.last_reset_date = today

    # ============================================================
    # 行动管理
    # ============================================================

    def get_action(self, action_id: str) -> Optional[SocialAction]:
        """获取行动定义"""
        return self.actions.get(action_id)

    def get_available_actions(self, npc_id: str, context: Dict = None) -> List[Dict]:
        """
        获取对某个NPC可用的行动列表

        Args:
            npc_id: NPC ID
            context: 上下文信息（好感度、位置等）

        Returns:
            可用行动列表
        """
        if context is None:
            context = self._build_context(npc_id)

        available = []

        for action_id, action in self.actions.items():
            # 检查是否隐藏
            if action.is_hidden and action_id not in self.unlocked_actions:
                continue

            # 检查可用性
            check_result = self.check_action_availability(action_id, npc_id, context)

            if check_result["available"] or check_result.get("show_locked", False):
                available.append({
                    "action_id": action_id,
                    "name": action.name,
                    "category": action.category.value,
                    "category_name": ACTION_CATEGORY_DISPLAY[action.category]["name"],
                    "description": action.description,
                    "icon": action.icon or ACTION_CATEGORY_DISPLAY[action.category]["icon"],
                    "available": check_result["available"],
                    "reason": check_result.get("reason", ""),
                    "time_cost": action.time_cost,
                    "success_rate": self._calculate_success_rate(action, context)
                })

        # 按类别排序
        category_order = [c.value for c in ActionCategory]
        available.sort(key=lambda x: (
            category_order.index(x["category"]) if x["category"] in category_order else 99,
            not x["available"],
            x["name"]
        ))

        return available

    def check_action_availability(self, action_id: str, npc_id: str,
                                   context: Dict = None) -> Dict[str, Any]:
        """
        检查行动是否可用

        Returns:
            {"available": bool, "reason": str, "show_locked": bool}
        """
        action = self.actions.get(action_id)
        if not action:
            return {"available": False, "reason": "行动不存在"}

        if context is None:
            context = self._build_context(npc_id)

        # 检查解锁状态
        if action.is_hidden and action_id not in self.unlocked_actions:
            return {"available": False, "reason": "未解锁", "show_locked": False}

        # 检查冷却
        if action_id in self.cooldowns and self.cooldowns[action_id] > 0:
            return {
                "available": False,
                "reason": f"冷却中（还需{self.cooldowns[action_id]}个时间段）",
                "show_locked": True
            }

        # 检查每日限制
        if action.daily_limit > 0:
            current_count = self.daily_counts[action_id].get(npc_id, 0)
            if current_count >= action.daily_limit:
                return {
                    "available": False,
                    "reason": f"今日已达上限（{action.daily_limit}次）",
                    "show_locked": True
                }

        # 检查关系阶段
        if action.required_phase:
            current_phase = context.get("phase", "stranger")
            phase_order = ["stranger", "acquaintance", "friend", "close", "crush", "lover"]
            if action.required_phase in phase_order:
                required_index = phase_order.index(action.required_phase)
                current_index = phase_order.index(current_phase) if current_phase in phase_order else 0
                if current_index < required_index:
                    return {
                        "available": False,
                        "reason": f"需要关系达到「{action.required_phase}」",
                        "show_locked": True
                    }

        # 检查位置
        if action.required_location:
            current_location = context.get("location", "")
            if current_location != action.required_location:
                return {
                    "available": False,
                    "reason": f"需要在特定地点",
                    "show_locked": True
                }

        # 检查时间段
        if action.required_time_periods:
            current_period = context.get("time_period", "")
            if current_period not in action.required_time_periods:
                return {
                    "available": False,
                    "reason": f"需要在特定时间",
                    "show_locked": True
                }

        # 检查自定义条件
        for condition in action.conditions:
            satisfied, reason = condition.check(context)
            if not satisfied:
                return {
                    "available": False,
                    "reason": reason,
                    "show_locked": True
                }

        # 检查消耗
        if action.energy_cost > 0:
            current_energy = context.get("energy", 100)
            if current_energy < action.energy_cost:
                return {
                    "available": False,
                    "reason": f"精力不足（需要{action.energy_cost}）",
                    "show_locked": True
                }

        if action.money_cost > 0:
            current_money = context.get("money", 0)
            if current_money < action.money_cost:
                return {
                    "available": False,
                    "reason": f"金钱不足（需要{action.money_cost}）",
                    "show_locked": True
                }

        return {"available": True}

    def _build_context(self, npc_id: str) -> Dict:
        """构建上下文"""
        context = {
            "npc_id": npc_id,
            "affection": 0,
            "intimacy": 0,
            "phase": "stranger",
            "mood": 50,
            "location": "",
            "time_period": "",
            "energy": 100,
            "money": 0
        }

        # 从NPC管理器获取信息
        if self.npc_manager:
            relation = self.npc_manager.get_relation(npc_id)
            if relation:
                context["affection"] = relation.affection
                context["intimacy"] = relation.intimacy
                context["phase"] = relation.phase.value

            npc = self.npc_manager.get_npc(npc_id)
            if npc:
                context["mood"] = npc.mood

        # 从时间管理器获取信息
        if self.time_manager:
            current_time = self.time_manager.get_current_time()
            context["time_period"] = current_time.period.value

            # 获取NPC当前位置
            npc_location = self.time_manager.get_npc_location(npc_id)
            if npc_location:
                context["location"] = npc_location

        # 从宠物系统获取玩家状态
        if self.pet_system:
            context["energy"] = getattr(self.pet_system.data, "energy", 100)
            context["money"] = getattr(self.pet_system.data, "money", 0)

        return context

    # ============================================================
    # 执行行动
    # ============================================================

    def execute_action(self, action_id: str, npc_id: str,
                       options: Dict = None) -> Dict[str, Any]:
        """
        执行社交行动

        Args:
            action_id: 行动ID
            npc_id: NPC ID
            options: 额外选项

        Returns:
            执行结果
        """
        action = self.actions.get(action_id)
        if not action:
            return {"success": False, "error": "行动不存在"}

        context = self._build_context(npc_id)

        # 检查可用性
        availability = self.check_action_availability(action_id, npc_id, context)
        if not availability["available"]:
            return {
                "success": False,
                "error": availability.get("reason", "无法执行此行动")
            }

        # 计算成功率
        success_rate = self._calculate_success_rate(action, context)

        # 判定结果
        roll = random.random()
        if roll < success_rate * 0.1:  # 10%的成功概率变成大成功
            result = ActionResult.CRITICAL_SUCCESS
        elif roll < success_rate:
            result = ActionResult.SUCCESS
        elif roll < success_rate + 0.1:  # 失败边缘，部分成功
            result = ActionResult.PARTIAL_SUCCESS
        else:
            result = ActionResult.FAILURE

        # 获取对话和响应
        dialogue = self._get_dialogue(action, context)
        response = self._get_response(action, npc_id, result, context)

        # 应用效果
        effects = []
        if result in [ActionResult.SUCCESS, ActionResult.CRITICAL_SUCCESS]:
            effects = self._apply_effects(action.success_effects, npc_id, context)
            if result == ActionResult.CRITICAL_SUCCESS:
                # 大成功效果加成
                for effect in effects:
                    effect["bonus"] = int(effect.get("change", 0) * 0.5)
        elif result == ActionResult.PARTIAL_SUCCESS:
            # 部分成功，效果减半
            partial_effects = []
            for e in action.success_effects:
                partial = ActionEffect(
                    e.effect_type, e.target,
                    e.value // 2 if isinstance(e.value, int) else e.value,
                    e.is_percentage
                )
                partial_effects.append(partial)
            effects = self._apply_effects(partial_effects, npc_id, context)
        else:
            effects = self._apply_effects(action.failure_effects, npc_id, context)

        # 消耗
        self._apply_costs(action)

        # 更新冷却
        if action.cooldown_periods > 0:
            self.cooldowns[action_id] = action.cooldown_periods

        # 更新每日计数
        if action.daily_limit > 0:
            self.daily_counts[action_id][npc_id] += 1

        # 记录历史
        history = ActionHistory(
            action_id=action_id,
            npc_id=npc_id,
            timestamp=datetime.now().isoformat(),
            result=result,
            effects=effects,
            dialogue=dialogue,
            response=response
        )
        self.action_history.append(history)

        # 保存状态
        self._save_state()

        # 回调
        if self.on_action_executed:
            self.on_action_executed(action_id, npc_id, result, effects)

        result_display = ACTION_RESULT_DISPLAY.get(result, {})

        return {
            "success": True,
            "action_name": action.name,
            "result": result.value,
            "result_name": result_display.get("name", ""),
            "result_icon": result_display.get("icon", ""),
            "dialogue": dialogue,
            "response": response,
            "effects": effects,
            "time_cost": action.time_cost
        }

    def _calculate_success_rate(self, action: SocialAction, context: Dict) -> float:
        """计算成功率"""
        rate = action.base_success_rate

        # 好感度加成
        affection = context.get("affection", 0)
        rate += affection * action.affection_bonus

        # 心情修正
        mood = context.get("mood", 50)
        if mood > 70:
            rate += action.mood_modifier
        elif mood < 30:
            rate -= action.mood_modifier

        return max(0.1, min(0.95, rate))

    def _get_dialogue(self, action: SocialAction, context: Dict) -> str:
        """获取对话内容"""
        variants = action.dialogue_variants.get("default", [])
        if not variants:
            return ""
        return random.choice(variants)

    def _get_response(self, action: SocialAction, npc_id: str,
                      result: ActionResult, context: Dict) -> str:
        """获取NPC响应"""
        # 检查是否有NPC专属响应
        npc_responses = action.npc_responses.get(npc_id, {})
        result_key = result.value

        if result_key in npc_responses:
            return random.choice(npc_responses[result_key])

        # 默认响应
        default_responses = {
            ActionResult.SUCCESS: ["好的~", "嗯！", "太好了！"],
            ActionResult.CRITICAL_SUCCESS: ["哇！太开心了！", "真的吗！", "谢谢你！"],
            ActionResult.PARTIAL_SUCCESS: ["嗯...", "也行吧", "好吧..."],
            ActionResult.FAILURE: ["抱歉...", "现在不太方便", "下次吧"],
            ActionResult.REJECTED: ["不要...", "我不想...", "请不要这样"]
        }

        responses = default_responses.get(result, ["..."])
        return random.choice(responses)

    def _apply_effects(self, effects: List[ActionEffect], npc_id: str,
                       context: Dict) -> List[Dict]:
        """应用效果"""
        applied = []

        for effect in effects:
            result = effect.apply(context)

            # 实际应用效果
            if effect.target == "affection" and self.npc_manager:
                old = context.get("affection", 0)
                new = self.npc_manager.change_affection(npc_id, result["change"])
                result["new_value"] = new

            elif effect.target == "mood" and self.npc_manager:
                npc = self.npc_manager.get_npc(npc_id)
                if npc:
                    old = npc.mood
                    npc.mood = max(0, min(100, npc.mood + result["change"]))
                    result["new_value"] = npc.mood

            applied.append(result)

        return applied

    def _apply_costs(self, action: SocialAction):
        """应用消耗"""
        if self.pet_system:
            if action.energy_cost > 0:
                current = getattr(self.pet_system.data, "energy", 100)
                self.pet_system.data.energy = max(0, current - action.energy_cost)

            if action.money_cost > 0:
                current = getattr(self.pet_system.data, "money", 0)
                self.pet_system.data.money = max(0, current - action.money_cost)

        if action.time_cost > 0 and self.time_manager:
            self.time_manager.advance_time(action.time_cost)

    # ============================================================
    # 解锁系统
    # ============================================================

    def unlock_action(self, action_id: str) -> bool:
        """解锁行动"""
        action = self.actions.get(action_id)
        if not action or not action.is_hidden:
            return False

        if action_id in self.unlocked_actions:
            return False

        self.unlocked_actions.add(action_id)
        self._save_state()

        if self.on_action_unlocked:
            self.on_action_unlocked(action_id, action)

        return True

    def check_unlock_conditions(self, context: Dict) -> List[str]:
        """检查并解锁满足条件的行动"""
        unlocked = []

        for action_id, action in self.actions.items():
            if not action.is_hidden:
                continue
            if action_id in self.unlocked_actions:
                continue

            # 检查解锁条件
            should_unlock = False

            if action.unlock_condition == "phase_close":
                if context.get("phase") in ["close", "crush", "lover"]:
                    should_unlock = True
            elif action.unlock_condition == "affection_500":
                if context.get("affection", 0) >= 500:
                    should_unlock = True
            # 可以添加更多解锁条件...

            if should_unlock:
                self.unlock_action(action_id)
                unlocked.append(action_id)

        return unlocked

    # ============================================================
    # 冷却管理
    # ============================================================

    def tick_cooldowns(self, periods: int = 1):
        """推进冷却时间"""
        for action_id in list(self.cooldowns.keys()):
            self.cooldowns[action_id] = max(0, self.cooldowns[action_id] - periods)
            if self.cooldowns[action_id] <= 0:
                del self.cooldowns[action_id]
        self._save_state()

    def get_cooldown(self, action_id: str) -> int:
        """获取行动剩余冷却时间"""
        return self.cooldowns.get(action_id, 0)

    # ============================================================
    # 历史和统计
    # ============================================================

    def get_action_history(self, npc_id: str = None, limit: int = 10) -> List[Dict]:
        """获取行动历史"""
        history = self.action_history
        if npc_id:
            history = [h for h in history if h.npc_id == npc_id]

        result = []
        for h in history[-limit:]:
            action = self.actions.get(h.action_id)
            result.append({
                "action_id": h.action_id,
                "action_name": action.name if action else h.action_id,
                "npc_id": h.npc_id,
                "timestamp": h.timestamp,
                "result": h.result.value,
                "dialogue": h.dialogue,
                "response": h.response
            })

        return result

    def get_stats(self, npc_id: str = None) -> Dict[str, Any]:
        """获取统计信息"""
        history = self.action_history
        if npc_id:
            history = [h for h in history if h.npc_id == npc_id]

        total = len(history)
        success = sum(1 for h in history if h.result in [ActionResult.SUCCESS, ActionResult.CRITICAL_SUCCESS])
        critical = sum(1 for h in history if h.result == ActionResult.CRITICAL_SUCCESS)

        # 按行动类型统计
        by_action = defaultdict(int)
        for h in history:
            by_action[h.action_id] += 1

        return {
            "total_actions": total,
            "success_count": success,
            "critical_count": critical,
            "success_rate": success / total if total > 0 else 0,
            "by_action": dict(by_action)
        }


# 便捷函数
def create_social_action_manager(pet_system=None, npc_manager=None,
                                  time_manager=None) -> SocialActionManager:
    """创建社交行动系统"""
    return SocialActionManager(pet_system, npc_manager, time_manager)
