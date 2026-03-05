"""
悬浮助手 - 剧情追踪系统 (Story Tracker System)
管理剧情线、事件触发、标志变量、成就系统
"""
import random
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class StoryLineType(Enum):
    """剧情线类型"""
    MAIN = "main"                       # 主线
    CHARACTER = "character"             # 角色线
    SIDE = "side"                       # 支线
    SECRET = "secret"                   # 隐藏线
    EVENT = "event"                     # 事件线


class StoryNodeType(Enum):
    """剧情节点类型"""
    DIALOGUE = "dialogue"               # 对话
    CHOICE = "choice"                   # 选择
    EVENT = "event"                     # 事件
    BATTLE = "battle"                   # 战斗/竞争
    DISCOVERY = "discovery"             # 发现
    CHECKPOINT = "checkpoint"           # 检查点
    ENDING = "ending"                   # 结局


class TriggerType(Enum):
    """触发类型"""
    AUTO = "auto"                       # 自动触发
    LOCATION = "location"               # 地点触发
    TIME = "time"                       # 时间触发
    INTERACTION = "interaction"         # 互动触发
    FLAG = "flag"                       # 标志触发
    AFFECTION = "affection"             # 好感度触发
    ITEM = "item"                       # 物品触发
    COMPOSITE = "composite"             # 复合条件


class AchievementType(Enum):
    """成就类型"""
    STORY = "story"                     # 剧情成就
    RELATIONSHIP = "relationship"       # 关系成就
    EXPLORATION = "exploration"         # 探索成就
    COLLECTION = "collection"           # 收集成就
    SPECIAL = "special"                 # 特殊成就
    SECRET = "secret"                   # 隐藏成就


# 剧情线显示配置
STORY_LINE_DISPLAY = {
    StoryLineType.MAIN: {"name": "主线", "icon": "📖", "color": "#FFD700"},
    StoryLineType.CHARACTER: {"name": "角色线", "icon": "👤", "color": "#E91E63"},
    StoryLineType.SIDE: {"name": "支线", "icon": "📄", "color": "#4CAF50"},
    StoryLineType.SECRET: {"name": "隐藏线", "icon": "🔮", "color": "#9C27B0"},
    StoryLineType.EVENT: {"name": "事件线", "icon": "🎭", "color": "#FF9800"},
}

# 成就类型显示
ACHIEVEMENT_TYPE_DISPLAY = {
    AchievementType.STORY: {"name": "剧情", "icon": "📜", "color": "#FFD700"},
    AchievementType.RELATIONSHIP: {"name": "关系", "icon": "💕", "color": "#E91E63"},
    AchievementType.EXPLORATION: {"name": "探索", "icon": "🗺️", "color": "#4CAF50"},
    AchievementType.COLLECTION: {"name": "收集", "icon": "🏆", "color": "#2196F3"},
    AchievementType.SPECIAL: {"name": "特殊", "icon": "⭐", "color": "#FF9800"},
    AchievementType.SECRET: {"name": "隐藏", "icon": "🔒", "color": "#9C27B0"},
}


@dataclass
class TriggerCondition:
    """触发条件"""
    trigger_type: TriggerType
    target: str                         # 目标（地点ID、NPC ID等）
    operator: str = "=="                # 比较符
    value: Any = None                   # 值
    description: str = ""

    def check(self, context: Dict) -> bool:
        """检查条件是否满足"""
        if self.trigger_type == TriggerType.LOCATION:
            return context.get("current_location") == self.target

        elif self.trigger_type == TriggerType.TIME:
            current_time = context.get("time_period", "")
            if isinstance(self.value, list):
                return current_time in self.value
            return current_time == self.value

        elif self.trigger_type == TriggerType.FLAG:
            flags = context.get("flags", {})
            flag_value = flags.get(self.target, False)

            if self.operator == "==":
                return flag_value == self.value
            elif self.operator == "!=":
                return flag_value != self.value
            elif self.operator == ">=":
                return flag_value >= self.value
            elif self.operator == ">":
                return flag_value > self.value

        elif self.trigger_type == TriggerType.AFFECTION:
            affections = context.get("affections", {})
            affection = affections.get(self.target, 0)

            if self.operator == ">=":
                return affection >= self.value
            elif self.operator == ">":
                return affection > self.value
            elif self.operator == "==":
                return affection == self.value

        elif self.trigger_type == TriggerType.ITEM:
            items = context.get("items", [])
            return self.target in items

        elif self.trigger_type == TriggerType.INTERACTION:
            npc_id = context.get("interacting_npc")
            return npc_id == self.target

        elif self.trigger_type == TriggerType.AUTO:
            return True

        return False

    def to_dict(self) -> Dict:
        return {
            "trigger_type": self.trigger_type.value,
            "target": self.target,
            "operator": self.operator,
            "value": self.value,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TriggerCondition":
        return cls(
            trigger_type=TriggerType(data.get("trigger_type", "auto")),
            target=data.get("target", ""),
            operator=data.get("operator", "=="),
            value=data.get("value"),
            description=data.get("description", "")
        )


@dataclass
class StoryChoice:
    """剧情选择"""
    choice_id: str
    text: str                           # 选项文本
    next_node: str = ""                 # 下一个节点
    requirements: List[TriggerCondition] = field(default_factory=list)
    effects: Dict[str, Any] = field(default_factory=dict)  # 效果
    is_hidden: bool = False             # 是否隐藏（条件不满足时）


@dataclass
class StoryNode:
    """剧情节点"""
    node_id: str
    name: str
    node_type: StoryNodeType
    story_line: str                     # 所属剧情线ID

    # 内容
    content: str = ""                   # 主要内容/对话
    speaker: str = ""                   # 说话者（对话节点）
    background: str = ""                # 背景/CG
    bgm: str = ""                       # 背景音乐

    # 选择（choice类型）
    choices: List[StoryChoice] = field(default_factory=list)

    # 触发
    triggers: List[TriggerCondition] = field(default_factory=list)
    priority: int = 0                   # 优先级（同时满足多个时）

    # 效果
    set_flags: Dict[str, Any] = field(default_factory=dict)  # 设置标志
    give_items: List[str] = field(default_factory=list)      # 给予物品
    affection_changes: Dict[str, int] = field(default_factory=dict)  # 好感度变化
    unlock_achievements: List[str] = field(default_factory=list)     # 解锁成就

    # 流程
    next_node: str = ""                 # 下一个节点（非选择类型）
    is_repeatable: bool = False         # 是否可重复

    # 状态
    is_completed: bool = False
    completion_date: str = ""

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "story_line": self.story_line,
            "content": self.content,
            "speaker": self.speaker,
            "background": self.background,
            "bgm": self.bgm,
            "choices": [
                {
                    "choice_id": c.choice_id,
                    "text": c.text,
                    "next_node": c.next_node,
                    "requirements": [r.to_dict() for r in c.requirements],
                    "effects": c.effects,
                    "is_hidden": c.is_hidden
                }
                for c in self.choices
            ],
            "triggers": [t.to_dict() for t in self.triggers],
            "priority": self.priority,
            "set_flags": self.set_flags,
            "give_items": self.give_items,
            "affection_changes": self.affection_changes,
            "unlock_achievements": self.unlock_achievements,
            "next_node": self.next_node,
            "is_repeatable": self.is_repeatable,
            "is_completed": self.is_completed,
            "completion_date": self.completion_date
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "StoryNode":
        node = cls(
            node_id=data.get("node_id", ""),
            name=data.get("name", ""),
            node_type=StoryNodeType(data.get("node_type", "dialogue")),
            story_line=data.get("story_line", "")
        )

        node.content = data.get("content", "")
        node.speaker = data.get("speaker", "")
        node.background = data.get("background", "")
        node.bgm = data.get("bgm", "")

        for c in data.get("choices", []):
            choice = StoryChoice(
                choice_id=c.get("choice_id", ""),
                text=c.get("text", ""),
                next_node=c.get("next_node", ""),
                requirements=[TriggerCondition.from_dict(r) for r in c.get("requirements", [])],
                effects=c.get("effects", {}),
                is_hidden=c.get("is_hidden", False)
            )
            node.choices.append(choice)

        node.triggers = [TriggerCondition.from_dict(t) for t in data.get("triggers", [])]
        node.priority = data.get("priority", 0)
        node.set_flags = data.get("set_flags", {})
        node.give_items = data.get("give_items", [])
        node.affection_changes = data.get("affection_changes", {})
        node.unlock_achievements = data.get("unlock_achievements", [])
        node.next_node = data.get("next_node", "")
        node.is_repeatable = data.get("is_repeatable", False)
        node.is_completed = data.get("is_completed", False)
        node.completion_date = data.get("completion_date", "")

        return node


@dataclass
class StoryLine:
    """剧情线"""
    line_id: str
    name: str
    line_type: StoryLineType
    description: str = ""

    # 关联
    related_npc: str = ""               # 关联NPC（角色线）
    related_location: str = ""          # 关联地点

    # 节点
    start_node: str = ""                # 起始节点
    nodes: List[str] = field(default_factory=list)  # 节点ID列表

    # 解锁条件
    unlock_conditions: List[TriggerCondition] = field(default_factory=list)
    is_unlocked: bool = False
    unlock_date: str = ""

    # 进度
    current_node: str = ""              # 当前节点
    completed_nodes: List[str] = field(default_factory=list)
    is_completed: bool = False
    completion_date: str = ""

    # 显示
    icon: str = ""
    color: str = ""

    def get_progress(self) -> float:
        """获取进度"""
        if not self.nodes:
            return 0.0
        return len(self.completed_nodes) / len(self.nodes)

    def to_dict(self) -> Dict:
        return {
            "line_id": self.line_id,
            "name": self.name,
            "line_type": self.line_type.value,
            "description": self.description,
            "related_npc": self.related_npc,
            "related_location": self.related_location,
            "start_node": self.start_node,
            "nodes": self.nodes,
            "unlock_conditions": [c.to_dict() for c in self.unlock_conditions],
            "is_unlocked": self.is_unlocked,
            "unlock_date": self.unlock_date,
            "current_node": self.current_node,
            "completed_nodes": self.completed_nodes,
            "is_completed": self.is_completed,
            "completion_date": self.completion_date,
            "icon": self.icon,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "StoryLine":
        line = cls(
            line_id=data.get("line_id", ""),
            name=data.get("name", ""),
            line_type=StoryLineType(data.get("line_type", "side")),
            description=data.get("description", "")
        )

        line.related_npc = data.get("related_npc", "")
        line.related_location = data.get("related_location", "")
        line.start_node = data.get("start_node", "")
        line.nodes = data.get("nodes", [])
        line.unlock_conditions = [
            TriggerCondition.from_dict(c) for c in data.get("unlock_conditions", [])
        ]
        line.is_unlocked = data.get("is_unlocked", False)
        line.unlock_date = data.get("unlock_date", "")
        line.current_node = data.get("current_node", "")
        line.completed_nodes = data.get("completed_nodes", [])
        line.is_completed = data.get("is_completed", False)
        line.completion_date = data.get("completion_date", "")
        line.icon = data.get("icon", "")
        line.color = data.get("color", "")

        return line


@dataclass
class Achievement:
    """成就"""
    achievement_id: str
    name: str
    achievement_type: AchievementType
    description: str = ""
    hint: str = ""                      # 获取提示

    # 条件
    conditions: List[TriggerCondition] = field(default_factory=list)
    required_flags: List[str] = field(default_factory=list)

    # 奖励
    rewards: Dict[str, Any] = field(default_factory=dict)

    # 状态
    is_unlocked: bool = False
    unlock_date: str = ""

    # 显示
    icon: str = ""
    icon_locked: str = "🔒"
    points: int = 10                    # 成就点数

    # 隐藏
    is_secret: bool = False             # 是否为隐藏成就

    def to_dict(self) -> Dict:
        return {
            "achievement_id": self.achievement_id,
            "name": self.name,
            "achievement_type": self.achievement_type.value,
            "description": self.description,
            "hint": self.hint,
            "conditions": [c.to_dict() for c in self.conditions],
            "required_flags": self.required_flags,
            "rewards": self.rewards,
            "is_unlocked": self.is_unlocked,
            "unlock_date": self.unlock_date,
            "icon": self.icon,
            "icon_locked": self.icon_locked,
            "points": self.points,
            "is_secret": self.is_secret
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Achievement":
        return cls(
            achievement_id=data.get("achievement_id", ""),
            name=data.get("name", ""),
            achievement_type=AchievementType(data.get("achievement_type", "story")),
            description=data.get("description", ""),
            hint=data.get("hint", ""),
            conditions=[TriggerCondition.from_dict(c) for c in data.get("conditions", [])],
            required_flags=data.get("required_flags", []),
            rewards=data.get("rewards", {}),
            is_unlocked=data.get("is_unlocked", False),
            unlock_date=data.get("unlock_date", ""),
            icon=data.get("icon", ""),
            icon_locked=data.get("icon_locked", "🔒"),
            points=data.get("points", 10),
            is_secret=data.get("is_secret", False)
        )


class StoryTracker:
    """
    剧情追踪系统

    功能:
    1. 管理剧情线和节点
    2. 管理标志变量
    3. 管理成就系统
    4. 触发剧情事件
    """

    def __init__(self, pet_system=None, npc_manager=None, time_manager=None):
        self.pet_system = pet_system
        self.npc_manager = npc_manager
        self.time_manager = time_manager

        # 剧情数据
        self.story_lines: Dict[str, StoryLine] = {}
        self.story_nodes: Dict[str, StoryNode] = {}

        # 标志变量
        self.flags: Dict[str, Any] = {}

        # 成就
        self.achievements: Dict[str, Achievement] = {}

        # 收集要素
        self.collected_items: Set[str] = set()
        self.discovered_secrets: Set[str] = set()
        self.visited_locations: Set[str] = set()

        # CG收藏
        self.unlocked_cgs: Set[str] = set()

        # 结局记录
        self.achieved_endings: Set[str] = set()

        # 当前状态
        self.active_node: Optional[str] = None  # 当前活动的剧情节点

        # 回调
        self.on_story_triggered: Optional[Callable] = None
        self.on_flag_changed: Optional[Callable] = None
        self.on_achievement_unlocked: Optional[Callable] = None
        self.on_story_completed: Optional[Callable] = None

        # 加载数据
        self._load_data()
        self._load_state()

    def _load_data(self):
        """加载数据定义"""
        self._create_default_story_lines()
        self._create_default_achievements()

        # 尝试从文件加载
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "story_data.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for line_data in data.get("story_lines", []):
                    line = StoryLine.from_dict(line_data)
                    self.story_lines[line.line_id] = line

                for node_data in data.get("story_nodes", []):
                    node = StoryNode.from_dict(node_data)
                    self.story_nodes[node.node_id] = node

                for ach_data in data.get("achievements", []):
                    ach = Achievement.from_dict(ach_data)
                    self.achievements[ach.achievement_id] = ach

        except Exception as e:
            logger.warning(f"加载剧情数据失败: {e}")

    def _create_default_story_lines(self):
        """创建默认剧情线"""
        # 主线
        main_line = StoryLine(
            line_id="main_story",
            name="文学社的故事",
            line_type=StoryLineType.MAIN,
            description="你加入文学社后发生的故事",
            start_node="main_001",
            nodes=["main_001", "main_002", "main_003"],
            is_unlocked=True,
            icon="📖",
            color="#FFD700"
        )
        self.story_lines["main_story"] = main_line

        # 小夏角色线
        xiaoxia_line = StoryLine(
            line_id="xiaoxia_story",
            name="小夏的秘密",
            line_type=StoryLineType.CHARACTER,
            description="关于小夏的故事线",
            related_npc="xiaoxia",
            start_node="xiaoxia_001",
            nodes=["xiaoxia_001", "xiaoxia_002", "xiaoxia_003"],
            unlock_conditions=[
                TriggerCondition(TriggerType.AFFECTION, "xiaoxia", ">=", 100)
            ],
            icon="🌸",
            color="#FFB7C5"
        )
        self.story_lines["xiaoxia_story"] = xiaoxia_line

        # 学长角色线
        xuechang_line = StoryLine(
            line_id="xuechang_story",
            name="学长的过去",
            line_type=StoryLineType.CHARACTER,
            description="学长不为人知的故事",
            related_npc="xuechang",
            start_node="xuechang_001",
            nodes=["xuechang_001", "xuechang_002"],
            unlock_conditions=[
                TriggerCondition(TriggerType.AFFECTION, "xuechang", ">=", 150)
            ],
            icon="📚",
            color="#5C6BC0"
        )
        self.story_lines["xuechang_story"] = xuechang_line

        # 隐藏线
        secret_line = StoryLine(
            line_id="secret_room",
            name="地下室之谜",
            line_type=StoryLineType.SECRET,
            description="图书馆地下室隐藏着什么秘密？",
            related_location="library_basement",
            start_node="secret_001",
            nodes=["secret_001", "secret_002"],
            unlock_conditions=[
                TriggerCondition(TriggerType.FLAG, "found_old_key", "==", True)
            ],
            is_unlocked=False,
            icon="🔮",
            color="#9C27B0"
        )
        self.story_lines["secret_room"] = secret_line

        # 创建默认节点
        self._create_default_nodes()

    def _create_default_nodes(self):
        """创建默认剧情节点"""
        # 主线节点
        self.story_nodes["main_001"] = StoryNode(
            node_id="main_001",
            name="初入文学社",
            node_type=StoryNodeType.DIALOGUE,
            story_line="main_story",
            content="你推开文学社活动室的门，一群人正在热烈地讨论着什么...",
            triggers=[TriggerCondition(TriggerType.AUTO, "")],
            set_flags={"joined_club": True},
            next_node="main_002"
        )

        self.story_nodes["main_002"] = StoryNode(
            node_id="main_002",
            name="第一次社团活动",
            node_type=StoryNodeType.CHOICE,
            story_line="main_story",
            content="学长问你想参与什么样的活动...",
            speaker="xuechang",
            choices=[
                StoryChoice(
                    choice_id="choice_writing",
                    text="我想尝试创作",
                    next_node="main_003_a",
                    effects={"set_flag": {"chose_writing": True}}
                ),
                StoryChoice(
                    choice_id="choice_reading",
                    text="我更喜欢阅读和讨论",
                    next_node="main_003_b",
                    effects={"set_flag": {"chose_reading": True}}
                ),
            ],
            triggers=[
                TriggerCondition(TriggerType.FLAG, "joined_club", "==", True),
                TriggerCondition(TriggerType.TIME, "", "==", ["afternoon", "evening"])
            ]
        )

        # 小夏节点
        self.story_nodes["xiaoxia_001"] = StoryNode(
            node_id="xiaoxia_001",
            name="小夏的烦恼",
            node_type=StoryNodeType.DIALOGUE,
            story_line="xiaoxia_story",
            content="你发现小夏独自坐在窗边，似乎有些心事...",
            speaker="xiaoxia",
            triggers=[
                TriggerCondition(TriggerType.AFFECTION, "xiaoxia", ">=", 100),
                TriggerCondition(TriggerType.LOCATION, "club_room_literature")
            ],
            affection_changes={"xiaoxia": 20},
            next_node="xiaoxia_002"
        )

        # 隐藏线节点
        self.story_nodes["secret_001"] = StoryNode(
            node_id="secret_001",
            name="神秘的钥匙",
            node_type=StoryNodeType.DISCOVERY,
            story_line="secret_room",
            content="你在一本旧书中发现了一把古老的钥匙...",
            triggers=[
                TriggerCondition(TriggerType.LOCATION, "library"),
                TriggerCondition(TriggerType.FLAG, "found_old_book", "==", True)
            ],
            set_flags={"found_old_key": True},
            give_items=["old_key"],
            unlock_achievements=["explorer_1"]
        )

    def _create_default_achievements(self):
        """创建默认成就"""
        default_achievements = [
            Achievement(
                achievement_id="first_meeting",
                name="初次相遇",
                achievement_type=AchievementType.STORY,
                description="完成与所有主要角色的初次对话",
                icon="🤝",
                points=10
            ),
            Achievement(
                achievement_id="friendship_xiaoxia",
                name="小夏的朋友",
                achievement_type=AchievementType.RELATIONSHIP,
                description="与小夏成为朋友",
                conditions=[
                    TriggerCondition(TriggerType.AFFECTION, "xiaoxia", ">=", 100)
                ],
                icon="🌸",
                points=20
            ),
            Achievement(
                achievement_id="club_member",
                name="文学社员",
                achievement_type=AchievementType.STORY,
                description="正式加入文学社",
                required_flags=["joined_club"],
                icon="📚",
                points=10
            ),
            Achievement(
                achievement_id="explorer_1",
                name="初级探索者",
                achievement_type=AchievementType.EXPLORATION,
                description="发现第一个隐藏场所",
                icon="🗺️",
                points=15
            ),
            Achievement(
                achievement_id="all_locations",
                name="校园通",
                achievement_type=AchievementType.EXPLORATION,
                description="探索校园所有可访问的地点",
                icon="🏫",
                points=30
            ),
            Achievement(
                achievement_id="true_ending",
                name="真正的结局",
                achievement_type=AchievementType.SECRET,
                description="达成真结局",
                is_secret=True,
                icon="🌟",
                points=100
            ),
            Achievement(
                achievement_id="all_cg",
                name="记忆收藏家",
                achievement_type=AchievementType.COLLECTION,
                description="收集所有CG",
                icon="🖼️",
                points=50
            ),
        ]

        for ach in default_achievements:
            self.achievements[ach.achievement_id] = ach

    def _load_state(self):
        """加载状态"""
        if not self.pet_system:
            return

        try:
            state = getattr(self.pet_system.data, "story_tracker_state", {}) or {}

            self.flags = state.get("flags", {})
            self.collected_items = set(state.get("collected_items", []))
            self.discovered_secrets = set(state.get("discovered_secrets", []))
            self.visited_locations = set(state.get("visited_locations", []))
            self.unlocked_cgs = set(state.get("unlocked_cgs", []))
            self.achieved_endings = set(state.get("achieved_endings", []))

            # 恢复剧情线状态
            for line_id, line_state in state.get("story_lines", {}).items():
                if line_id in self.story_lines:
                    line = self.story_lines[line_id]
                    line.is_unlocked = line_state.get("is_unlocked", False)
                    line.current_node = line_state.get("current_node", "")
                    line.completed_nodes = line_state.get("completed_nodes", [])
                    line.is_completed = line_state.get("is_completed", False)

            # 恢复节点状态
            for node_id, node_state in state.get("story_nodes", {}).items():
                if node_id in self.story_nodes:
                    node = self.story_nodes[node_id]
                    node.is_completed = node_state.get("is_completed", False)

            # 恢复成就状态
            for ach_id, ach_state in state.get("achievements", {}).items():
                if ach_id in self.achievements:
                    self.achievements[ach_id].is_unlocked = ach_state.get("is_unlocked", False)
                    self.achievements[ach_id].unlock_date = ach_state.get("unlock_date", "")

        except Exception as e:
            logger.warning(f"加载剧情状态失败: {e}")

    def _save_state(self):
        """保存状态"""
        if not self.pet_system:
            return

        try:
            state = {
                "flags": self.flags,
                "collected_items": list(self.collected_items),
                "discovered_secrets": list(self.discovered_secrets),
                "visited_locations": list(self.visited_locations),
                "unlocked_cgs": list(self.unlocked_cgs),
                "achieved_endings": list(self.achieved_endings),
                "story_lines": {
                    line_id: {
                        "is_unlocked": line.is_unlocked,
                        "current_node": line.current_node,
                        "completed_nodes": line.completed_nodes,
                        "is_completed": line.is_completed
                    }
                    for line_id, line in self.story_lines.items()
                },
                "story_nodes": {
                    node_id: {"is_completed": node.is_completed}
                    for node_id, node in self.story_nodes.items()
                },
                "achievements": {
                    ach_id: {
                        "is_unlocked": ach.is_unlocked,
                        "unlock_date": ach.unlock_date
                    }
                    for ach_id, ach in self.achievements.items()
                }
            }

            self.pet_system.data.story_tracker_state = state
            self.pet_system.save()

        except Exception as e:
            logger.warning(f"保存剧情状态失败: {e}")

    # ============================================================
    # 标志变量管理
    # ============================================================

    def set_flag(self, flag_name: str, value: Any):
        """设置标志"""
        old_value = self.flags.get(flag_name)
        self.flags[flag_name] = value
        self._save_state()

        if self.on_flag_changed:
            self.on_flag_changed(flag_name, old_value, value)

        # 检查是否触发新剧情
        self._check_unlocks()

    def get_flag(self, flag_name: str, default: Any = None) -> Any:
        """获取标志"""
        return self.flags.get(flag_name, default)

    def increment_flag(self, flag_name: str, amount: int = 1) -> int:
        """增加标志值"""
        current = self.flags.get(flag_name, 0)
        new_value = current + amount
        self.set_flag(flag_name, new_value)
        return new_value

    # ============================================================
    # 剧情触发
    # ============================================================

    def check_triggers(self, context: Dict) -> List[StoryNode]:
        """
        检查可触发的剧情节点

        Args:
            context: 当前上下文

        Returns:
            可触发的节点列表
        """
        triggered = []

        # 添加标志到上下文
        context["flags"] = self.flags

        # 添加好感度到上下文
        if self.npc_manager:
            context["affections"] = {}
            for npc_id in ["xiaoxia", "xuechang", "meimei"]:
                relation = self.npc_manager.get_relation(npc_id)
                if relation:
                    context["affections"][npc_id] = relation.affection

        for node_id, node in self.story_nodes.items():
            # 跳过已完成且不可重复的
            if node.is_completed and not node.is_repeatable:
                continue

            # 检查剧情线是否解锁
            line = self.story_lines.get(node.story_line)
            if line and not line.is_unlocked:
                continue

            # 检查所有触发条件
            all_satisfied = True
            for trigger in node.triggers:
                if not trigger.check(context):
                    all_satisfied = False
                    break

            if all_satisfied:
                triggered.append(node)

        # 按优先级排序
        triggered.sort(key=lambda n: -n.priority)

        return triggered

    def trigger_node(self, node_id: str) -> Optional[Dict]:
        """
        触发剧情节点

        Returns:
            节点数据（用于显示）
        """
        node = self.story_nodes.get(node_id)
        if not node:
            return None

        self.active_node = node_id

        # 应用效果
        for flag_name, value in node.set_flags.items():
            self.set_flag(flag_name, value)

        for item in node.give_items:
            self.collected_items.add(item)

        for npc_id, change in node.affection_changes.items():
            if self.npc_manager:
                self.npc_manager.change_affection(npc_id, change)

        for ach_id in node.unlock_achievements:
            self.unlock_achievement(ach_id)

        # 回调
        if self.on_story_triggered:
            self.on_story_triggered(node)

        # 返回节点数据
        result = {
            "node_id": node.node_id,
            "name": node.name,
            "node_type": node.node_type.value,
            "content": node.content,
            "speaker": node.speaker,
            "background": node.background,
            "bgm": node.bgm,
        }

        # 如果是选择节点，添加选项
        if node.node_type == StoryNodeType.CHOICE:
            result["choices"] = []
            context = {"flags": self.flags}

            for choice in node.choices:
                # 检查选项条件
                available = True
                for req in choice.requirements:
                    if not req.check(context):
                        available = False
                        break

                if available or not choice.is_hidden:
                    result["choices"].append({
                        "choice_id": choice.choice_id,
                        "text": choice.text,
                        "available": available
                    })

        return result

    def make_choice(self, choice_id: str) -> Optional[str]:
        """
        做出选择

        Returns:
            下一个节点ID
        """
        if not self.active_node:
            return None

        node = self.story_nodes.get(self.active_node)
        if not node or node.node_type != StoryNodeType.CHOICE:
            return None

        for choice in node.choices:
            if choice.choice_id == choice_id:
                # 应用选择效果
                effects = choice.effects
                if "set_flag" in effects:
                    for flag, value in effects["set_flag"].items():
                        self.set_flag(flag, value)

                # 完成当前节点
                self._complete_node(node.node_id)

                return choice.next_node

        return None

    def advance_story(self) -> Optional[str]:
        """
        推进剧情（非选择节点）

        Returns:
            下一个节点ID
        """
        if not self.active_node:
            return None

        node = self.story_nodes.get(self.active_node)
        if not node:
            return None

        # 完成当前节点
        self._complete_node(node.node_id)

        return node.next_node

    def _complete_node(self, node_id: str):
        """完成节点"""
        node = self.story_nodes.get(node_id)
        if not node:
            return

        node.is_completed = True
        node.completion_date = datetime.now().strftime("%Y-%m-%d")

        # 更新剧情线进度
        line = self.story_lines.get(node.story_line)
        if line:
            if node_id not in line.completed_nodes:
                line.completed_nodes.append(node_id)

            # 检查剧情线是否完成
            if set(line.nodes) <= set(line.completed_nodes):
                line.is_completed = True
                line.completion_date = datetime.now().strftime("%Y-%m-%d")

                if self.on_story_completed:
                    self.on_story_completed(line)

        self.active_node = None
        self._save_state()

    def _check_unlocks(self):
        """检查并解锁剧情线和成就"""
        context = {"flags": self.flags}

        if self.npc_manager:
            context["affections"] = {}
            for npc_id in ["xiaoxia", "xuechang", "meimei"]:
                relation = self.npc_manager.get_relation(npc_id)
                if relation:
                    context["affections"][npc_id] = relation.affection

        # 检查剧情线解锁
        for line in self.story_lines.values():
            if line.is_unlocked:
                continue

            all_satisfied = True
            for condition in line.unlock_conditions:
                if not condition.check(context):
                    all_satisfied = False
                    break

            if all_satisfied:
                line.is_unlocked = True
                line.unlock_date = datetime.now().strftime("%Y-%m-%d")
                line.current_node = line.start_node

        # 检查成就
        for ach in self.achievements.values():
            if ach.is_unlocked:
                continue

            # 检查标志条件
            flags_satisfied = all(
                self.flags.get(flag, False) for flag in ach.required_flags
            )

            # 检查触发条件
            conditions_satisfied = all(
                c.check(context) for c in ach.conditions
            )

            if flags_satisfied and conditions_satisfied:
                self.unlock_achievement(ach.achievement_id)

        self._save_state()

    # ============================================================
    # 成就系统
    # ============================================================

    def unlock_achievement(self, achievement_id: str) -> bool:
        """解锁成就"""
        ach = self.achievements.get(achievement_id)
        if not ach or ach.is_unlocked:
            return False

        ach.is_unlocked = True
        ach.unlock_date = datetime.now().strftime("%Y-%m-%d")
        self._save_state()

        if self.on_achievement_unlocked:
            self.on_achievement_unlocked(ach)

        return True

    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """获取成就"""
        return self.achievements.get(achievement_id)

    def get_achievements_by_type(self, ach_type: AchievementType) -> List[Achievement]:
        """按类型获取成就"""
        return [
            ach for ach in self.achievements.values()
            if ach.achievement_type == ach_type
        ]

    def get_unlocked_achievements(self) -> List[Achievement]:
        """获取已解锁成就"""
        return [ach for ach in self.achievements.values() if ach.is_unlocked]

    def get_achievement_progress(self) -> Dict[str, Any]:
        """获取成就进度"""
        total = len(self.achievements)
        unlocked = len([a for a in self.achievements.values() if a.is_unlocked])
        points = sum(a.points for a in self.achievements.values() if a.is_unlocked)
        max_points = sum(a.points for a in self.achievements.values())

        by_type = {}
        for ach_type in AchievementType:
            type_achs = self.get_achievements_by_type(ach_type)
            type_unlocked = [a for a in type_achs if a.is_unlocked]
            by_type[ach_type.value] = {
                "total": len(type_achs),
                "unlocked": len(type_unlocked)
            }

        return {
            "total": total,
            "unlocked": unlocked,
            "progress": unlocked / total if total > 0 else 0,
            "points": points,
            "max_points": max_points,
            "by_type": by_type
        }

    # ============================================================
    # 信息获取
    # ============================================================

    def get_story_progress(self) -> Dict[str, Any]:
        """获取剧情进度"""
        total_lines = len(self.story_lines)
        completed_lines = len([l for l in self.story_lines.values() if l.is_completed])
        unlocked_lines = len([l for l in self.story_lines.values() if l.is_unlocked])

        total_nodes = len(self.story_nodes)
        completed_nodes = len([n for n in self.story_nodes.values() if n.is_completed])

        return {
            "total_lines": total_lines,
            "completed_lines": completed_lines,
            "unlocked_lines": unlocked_lines,
            "total_nodes": total_nodes,
            "completed_nodes": completed_nodes,
            "overall_progress": completed_nodes / total_nodes if total_nodes > 0 else 0
        }

    def get_unlocked_story_lines(self) -> List[Dict]:
        """获取已解锁的剧情线"""
        result = []
        for line in self.story_lines.values():
            if not line.is_unlocked:
                continue

            display = STORY_LINE_DISPLAY.get(line.line_type, {})
            result.append({
                "line_id": line.line_id,
                "name": line.name,
                "type": line.line_type.value,
                "type_name": display.get("name", ""),
                "icon": line.icon or display.get("icon", ""),
                "color": line.color or display.get("color", ""),
                "description": line.description,
                "progress": line.get_progress(),
                "is_completed": line.is_completed,
                "related_npc": line.related_npc
            })

        return result

    def get_collection_progress(self) -> Dict[str, Any]:
        """获取收集进度"""
        return {
            "items": len(self.collected_items),
            "secrets": len(self.discovered_secrets),
            "locations": len(self.visited_locations),
            "cgs": len(self.unlocked_cgs),
            "endings": len(self.achieved_endings)
        }

    def visit_location(self, location_id: str):
        """记录访问地点"""
        if location_id not in self.visited_locations:
            self.visited_locations.add(location_id)
            self._save_state()

            # 检查探索成就
            self._check_unlocks()


# 便捷函数
def create_story_tracker(pet_system=None, npc_manager=None,
                         time_manager=None) -> StoryTracker:
    """创建剧情追踪系统"""
    return StoryTracker(pet_system, npc_manager, time_manager)
