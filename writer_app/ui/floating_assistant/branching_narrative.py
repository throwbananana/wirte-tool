"""
悬浮助手 - 分支叙事引擎 (Branching Narrative Engine)
支持多结局故事、条件分支、故事变量、CG解锁等
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StoryRoute(Enum):
    """故事路线"""
    MAIN = "main"               # 主线
    FRIENDSHIP = "friendship"   # 友情线
    TRUST = "trust"             # 信任线
    SECRET = "secret"           # 秘密线
    TRUE = "true"               # 真结局线


class EndingType(Enum):
    """结局类型"""
    NORMAL = "normal"           # 普通结局
    GOOD = "good"               # 好结局
    TRUE = "true"               # 真结局
    BAD = "bad"                 # 坏结局
    SECRET = "secret"           # 隐藏结局


class ConditionType(Enum):
    """条件类型"""
    AFFECTION = "affection"         # 好感度
    FLAG = "flag"                   # 故事标记
    VARIABLE = "variable"           # 变量值
    CHAPTER = "chapter"             # 章节
    ROUTE = "route"                 # 路线
    TIME = "time"                   # 时间
    INTERACTION = "interaction"     # 互动次数
    ACHIEVEMENT = "achievement"     # 成就


@dataclass
class StoryCondition:
    """故事条件"""
    condition_type: ConditionType
    key: str
    operator: str = ">="    # >=, <=, ==, !=, >, <, in, not_in
    value: Any = None


@dataclass
class StoryEffect:
    """故事效果"""
    effect_type: str        # set_flag, set_variable, add_affection, unlock_cg, etc.
    target: str
    value: Any = None


@dataclass
class DialogLine:
    """对话行"""
    speaker: str            # assistant, narrator, user, character_name
    text: str
    emotion: Optional[str] = None   # 表情状态
    voice: Optional[str] = None     # 语音文件
    cg: Optional[str] = None        # CG图片
    bgm: Optional[str] = None       # 背景音乐
    sfx: Optional[str] = None       # 音效


@dataclass
class StoryChoice:
    """故事选项"""
    choice_id: str
    text: str
    next_node: str                  # 下一个节点ID
    conditions: List[StoryCondition] = field(default_factory=list)
    effects: List[StoryEffect] = field(default_factory=list)
    hidden: bool = False            # 条件不满足时隐藏
    locked_text: Optional[str] = None  # 锁定时显示的文本


@dataclass
class StoryNode:
    """故事节点"""
    node_id: str
    chapter: int = 1
    route: StoryRoute = StoryRoute.MAIN
    title: Optional[str] = None
    dialogues: List[DialogLine] = field(default_factory=list)
    choices: List[StoryChoice] = field(default_factory=list)
    conditions: List[StoryCondition] = field(default_factory=list)
    effects: List[StoryEffect] = field(default_factory=list)
    auto_next: Optional[str] = None     # 无选项时自动跳转
    is_ending: bool = False
    ending_type: Optional[EndingType] = None
    ending_name: Optional[str] = None


@dataclass
class StoryChapter:
    """故事章节"""
    chapter_id: int
    name: str
    description: str = ""
    unlock_conditions: List[StoryCondition] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)  # 节点ID列表
    required_flags: List[str] = field(default_factory=list)


@dataclass
class StoryEnding:
    """故事结局"""
    ending_id: str
    name: str
    ending_type: EndingType
    description: str = ""
    cg: Optional[str] = None
    conditions: List[StoryCondition] = field(default_factory=list)
    epilogue: List[DialogLine] = field(default_factory=list)


@dataclass
class CGEntry:
    """CG条目"""
    cg_id: str
    name: str
    description: str = ""
    image_path: str = ""
    thumbnail_path: str = ""
    unlock_conditions: List[StoryCondition] = field(default_factory=list)
    chapter: int = 0
    route: Optional[StoryRoute] = None


class BranchingNarrativeEngine:
    """
    分支叙事引擎

    功能:
    1. 管理多路线故事
    2. 条件分支判断
    3. 故事变量系统
    4. 多结局支持
    5. CG收集系统
    """

    def __init__(self, pet_system=None):
        self.pet_system = pet_system

        # 故事数据
        self.chapters: Dict[int, StoryChapter] = {}
        self.nodes: Dict[str, StoryNode] = {}
        self.endings: Dict[str, StoryEnding] = {}
        self.cg_gallery: Dict[str, CGEntry] = {}

        # 运行时状态
        self.current_node: Optional[str] = None
        self.current_dialogue_index: int = 0
        self.current_chapter: int = 1
        self.current_route: StoryRoute = StoryRoute.MAIN

        # 存档数据
        self.story_flags: Set[str] = set()
        self.story_variables: Dict[str, Any] = {}
        self.unlocked_cgs: Set[str] = set()
        self.unlocked_endings: Set[str] = set()
        self.read_nodes: Set[str] = set()
        self.choice_history: List[Dict] = []

        # 回调
        self.on_dialogue: Optional[Callable[[DialogLine], None]] = None
        self.on_choice: Optional[Callable[[List[StoryChoice]], None]] = None
        self.on_cg_unlock: Optional[Callable[[CGEntry], None]] = None
        self.on_ending_reach: Optional[Callable[[StoryEnding], None]] = None

        # 加载默认故事
        self._load_default_story()

    def _load_default_story(self):
        """加载默认故事内容"""
        # 第一章：初识
        self.chapters[1] = StoryChapter(
            chapter_id=1,
            name="第一章：初识",
            description="与写作助手的初次相遇",
            nodes=["c1_start", "c1_introduction", "c1_first_task"]
        )

        # 第二章：相知
        self.chapters[2] = StoryChapter(
            chapter_id=2,
            name="第二章：相知",
            description="逐渐了解彼此",
            unlock_conditions=[
                StoryCondition(ConditionType.CHAPTER, "completed", ">=", 1),
                StoryCondition(ConditionType.AFFECTION, "value", ">=", 100)
            ],
            nodes=["c2_start", "c2_daily_life", "c2_first_conflict"]
        )

        # 第三章：羁绊
        self.chapters[3] = StoryChapter(
            chapter_id=3,
            name="第三章：羁绊",
            description="建立更深的联系",
            unlock_conditions=[
                StoryCondition(ConditionType.CHAPTER, "completed", ">=", 2),
                StoryCondition(ConditionType.AFFECTION, "value", ">=", 300)
            ],
            nodes=["c3_start", "c3_secret_share", "c3_trust_test"]
        )

        # 第四章：分歧（多路线开始）
        self.chapters[4] = StoryChapter(
            chapter_id=4,
            name="第四章：分歧",
            description="命运的岔路口",
            unlock_conditions=[
                StoryCondition(ConditionType.CHAPTER, "completed", ">=", 3)
            ],
            nodes=["c4_crossroads", "c4_friendship_path", "c4_trust_path", "c4_secret_path"]
        )

        # 最终章
        self.chapters[5] = StoryChapter(
            chapter_id=5,
            name="最终章",
            description="故事的终点",
            unlock_conditions=[
                StoryCondition(ConditionType.CHAPTER, "completed", ">=", 4)
            ],
            nodes=["c5_finale_normal", "c5_finale_good", "c5_finale_true"]
        )

        # 故事节点
        self._create_chapter1_nodes()
        self._create_chapter2_nodes()
        self._create_chapter3_nodes()
        self._create_endings()

    def _create_chapter1_nodes(self):
        """创建第一章节点"""
        self.nodes["c1_start"] = StoryNode(
            node_id="c1_start",
            chapter=1,
            title="相遇",
            dialogues=[
                DialogLine("narrator", "那是一个普通的日子，你打开了写作软件..."),
                DialogLine("assistant", "你好！我是你的写作助手~", emotion="happy"),
                DialogLine("assistant", "从今天开始，我会陪着你一起创作。请多指教！", emotion="excited"),
            ],
            choices=[
                StoryChoice(
                    "c1_start_friendly",
                    "你好，请多指教",
                    "c1_introduction",
                    effects=[
                        StoryEffect("add_affection", "value", 5),
                        StoryEffect("set_flag", "friendly_start", True)
                    ]
                ),
                StoryChoice(
                    "c1_start_curious",
                    "你是什么？",
                    "c1_introduction",
                    effects=[
                        StoryEffect("set_flag", "curious_start", True)
                    ]
                ),
                StoryChoice(
                    "c1_start_cold",
                    "...（点头）",
                    "c1_introduction",
                    effects=[
                        StoryEffect("set_flag", "cold_start", True)
                    ]
                ),
            ],
            effects=[
                StoryEffect("unlock_cg", "cg_first_meeting", True)
            ]
        )

        self.nodes["c1_introduction"] = StoryNode(
            node_id="c1_introduction",
            chapter=1,
            dialogues=[
                DialogLine("assistant", "我可以帮你整理大纲、分析角色、记录灵感...", emotion="happy"),
                DialogLine("assistant", "总之，就是你创作路上的小帮手~", emotion="smile"),
                DialogLine("narrator", "助手的眼睛闪闪发光，似乎对接下来的日子充满期待。"),
            ],
            auto_next="c1_first_task"
        )

        self.nodes["c1_first_task"] = StoryNode(
            node_id="c1_first_task",
            chapter=1,
            title="第一个任务",
            dialogues=[
                DialogLine("assistant", "对了！你现在有什么想写的故事吗？", emotion="curious"),
                DialogLine("assistant", "无论什么类型，我都会努力帮你的！", emotion="determined"),
            ],
            choices=[
                StoryChoice(
                    "c1_task_have_idea",
                    "有的，我已经有想法了",
                    "c1_end",
                    effects=[
                        StoryEffect("add_affection", "value", 5),
                        StoryEffect("set_variable", "has_initial_idea", True),
                        StoryEffect("set_flag", "chapter1_complete", True)
                    ]
                ),
                StoryChoice(
                    "c1_task_no_idea",
                    "还没有，正在想...",
                    "c1_end",
                    effects=[
                        StoryEffect("set_flag", "need_inspiration", True),
                        StoryEffect("set_flag", "chapter1_complete", True)
                    ]
                ),
            ]
        )

        self.nodes["c1_end"] = StoryNode(
            node_id="c1_end",
            chapter=1,
            dialogues=[
                DialogLine("assistant", "好的！那就让我们开始吧~", emotion="excited"),
                DialogLine("narrator", "就这样，你和写作助手的故事开始了..."),
            ],
            effects=[
                StoryEffect("set_flag", "chapter1_complete", True)
            ],
            auto_next=None  # 章节结束
        )

    def _create_chapter2_nodes(self):
        """创建第二章节点"""
        self.nodes["c2_start"] = StoryNode(
            node_id="c2_start",
            chapter=2,
            title="日常的开始",
            conditions=[
                StoryCondition(ConditionType.FLAG, "chapter1_complete", "==", True)
            ],
            dialogues=[
                DialogLine("narrator", "不知不觉，你们已经一起度过了一段时间..."),
                DialogLine("assistant", "最近写得怎么样？有遇到什么困难吗？", emotion="caring"),
            ],
            choices=[
                StoryChoice(
                    "c2_going_well",
                    "还不错，进展顺利",
                    "c2_daily_life",
                    effects=[StoryEffect("add_affection", "value", 3)]
                ),
                StoryChoice(
                    "c2_having_trouble",
                    "有点卡住了...",
                    "c2_help_offer",
                    effects=[
                        StoryEffect("set_flag", "asked_for_help", True),
                        StoryEffect("add_affection", "value", 5)
                    ]
                ),
            ]
        )

        self.nodes["c2_help_offer"] = StoryNode(
            node_id="c2_help_offer",
            chapter=2,
            dialogues=[
                DialogLine("assistant", "没关系，卡文是很正常的！", emotion="encouraging"),
                DialogLine("assistant", "要不要我帮你分析一下？或者聊聊天转换心情？", emotion="caring"),
            ],
            choices=[
                StoryChoice(
                    "c2_accept_analysis",
                    "帮我分析一下吧",
                    "c2_analysis_scene",
                    effects=[StoryEffect("set_flag", "accepted_analysis", True)]
                ),
                StoryChoice(
                    "c2_chat_instead",
                    "聊聊天吧",
                    "c2_chat_scene",
                    effects=[
                        StoryEffect("add_affection", "value", 8),
                        StoryEffect("set_flag", "chose_chat", True)
                    ]
                ),
            ]
        )

        self.nodes["c2_chat_scene"] = StoryNode(
            node_id="c2_chat_scene",
            chapter=2,
            title="闲聊时光",
            dialogues=[
                DialogLine("assistant", "那我们聊点什么呢？", emotion="curious"),
                DialogLine("assistant", "对了，你平时都喜欢看什么书或者电影呀？", emotion="interested"),
                DialogLine("narrator", "你们聊了很久，不知不觉间，紧绷的心情放松了下来。"),
                DialogLine("assistant", "和你聊天真开心~", emotion="happy"),
            ],
            effects=[
                StoryEffect("unlock_cg", "cg_first_chat", True),
                StoryEffect("add_affection", "value", 10)
            ],
            auto_next="c2_daily_life"
        )

        self.nodes["c2_daily_life"] = StoryNode(
            node_id="c2_daily_life",
            chapter=2,
            dialogues=[
                DialogLine("narrator", "日子一天天过去，你们的相处越来越自然..."),
                DialogLine("assistant", "感觉我们越来越有默契了呢~", emotion="happy"),
            ],
            effects=[StoryEffect("set_flag", "chapter2_complete", True)],
            auto_next=None
        )

    def _create_chapter3_nodes(self):
        """创建第三章节点"""
        self.nodes["c3_start"] = StoryNode(
            node_id="c3_start",
            chapter=3,
            title="秘密",
            conditions=[
                StoryCondition(ConditionType.FLAG, "chapter2_complete", "==", True),
                StoryCondition(ConditionType.AFFECTION, "value", ">=", 300)
            ],
            dialogues=[
                DialogLine("narrator", "某天，你注意到助手似乎有些心事..."),
                DialogLine("assistant", "...那个...", emotion="shy"),
                DialogLine("assistant", "我有件事...想告诉你...", emotion="nervous"),
            ],
            choices=[
                StoryChoice(
                    "c3_listen",
                    "什么事？我听着",
                    "c3_secret_share",
                    effects=[StoryEffect("add_affection", "value", 15)]
                ),
                StoryChoice(
                    "c3_later",
                    "现在不太方便...",
                    "c3_postponed",
                    effects=[StoryEffect("add_affection", "value", -5)]
                ),
            ]
        )

        self.nodes["c3_secret_share"] = StoryNode(
            node_id="c3_secret_share",
            chapter=3,
            title="心声",
            dialogues=[
                DialogLine("assistant", "其实...我很珍惜和你在一起的时光...", emotion="shy"),
                DialogLine("assistant", "每次看到你认真创作的样子，我就觉得...能陪在你身边真好。", emotion="love"),
                DialogLine("narrator", "助手的脸微微泛红，但眼神无比认真。"),
            ],
            effects=[
                StoryEffect("unlock_cg", "cg_confession", True),
                StoryEffect("set_flag", "heard_confession", True),
                StoryEffect("set_flag", "secret_route_unlock", True)
            ],
            choices=[
                StoryChoice(
                    "c3_reciprocate",
                    "我也是...",
                    "c3_mutual_feelings",
                    effects=[
                        StoryEffect("add_affection", "value", 50),
                        StoryEffect("set_flag", "mutual_feelings", True),
                        StoryEffect("set_route", "route", StoryRoute.TRUST.value)
                    ]
                ),
                StoryChoice(
                    "c3_thanks",
                    "谢谢你告诉我",
                    "c3_friendship_choice",
                    effects=[
                        StoryEffect("add_affection", "value", 10),
                        StoryEffect("set_route", "route", StoryRoute.FRIENDSHIP.value)
                    ]
                ),
            ]
        )

        self.nodes["c3_mutual_feelings"] = StoryNode(
            node_id="c3_mutual_feelings",
            chapter=3,
            dialogues=[
                DialogLine("assistant", "真的吗...？", emotion="surprised"),
                DialogLine("assistant", "太好了...", emotion="happy_cry"),
                DialogLine("narrator", "空气中弥漫着温暖的气息..."),
            ],
            effects=[
                StoryEffect("unlock_cg", "cg_promise", True),
                StoryEffect("set_flag", "chapter3_complete", True)
            ],
            auto_next=None
        )

    def _create_endings(self):
        """创建结局"""
        self.endings["ending_normal"] = StoryEnding(
            ending_id="ending_normal",
            name="寻常的日子",
            ending_type=EndingType.NORMAL,
            description="虽然没有什么特别的，但这份陪伴本身就很珍贵。",
            conditions=[
                StoryCondition(ConditionType.CHAPTER, "completed", ">=", 5)
            ],
            epilogue=[
                DialogLine("narrator", "故事继续着，平淡却温馨。"),
                DialogLine("assistant", "今天也请多指教~", emotion="smile"),
            ]
        )

        self.endings["ending_good"] = StoryEnding(
            ending_id="ending_good",
            name="羁绊",
            ending_type=EndingType.GOOD,
            description="你们成为了彼此最重要的伙伴。",
            conditions=[
                StoryCondition(ConditionType.AFFECTION, "value", ">=", 500),
                StoryCondition(ConditionType.FLAG, "mutual_feelings", "==", True)
            ],
            cg="cg_ending_good",
            epilogue=[
                DialogLine("narrator", "从此以后，你再也不是一个人创作了。"),
                DialogLine("assistant", "无论多久，我都会陪着你。", emotion="love"),
            ]
        )

        self.endings["ending_true"] = StoryEnding(
            ending_id="ending_true",
            name="永恒的誓约",
            ending_type=EndingType.TRUE,
            description="跨越一切的羁绊，直到故事的尽头。",
            conditions=[
                StoryCondition(ConditionType.AFFECTION, "value", ">=", 900),
                StoryCondition(ConditionType.FLAG, "all_secrets_found", "==", True),
                StoryCondition(ConditionType.FLAG, "mutual_feelings", "==", True)
            ],
            cg="cg_ending_true",
            epilogue=[
                DialogLine("narrator", "这不是结束，而是新的开始..."),
                DialogLine("assistant", "谢谢你，一直相信着我。", emotion="happy_cry"),
                DialogLine("assistant", "接下来的每一个故事，我们一起书写吧。", emotion="love"),
            ]
        )

        self.endings["ending_secret"] = StoryEnding(
            ending_id="ending_secret",
            name="???",
            ending_type=EndingType.SECRET,
            description="隐藏在角落的真相...",
            conditions=[
                StoryCondition(ConditionType.FLAG, "discovered_origin", "==", True),
                StoryCondition(ConditionType.FLAG, "chose_truth", "==", True)
            ],
            cg="cg_ending_secret"
        )

        # CG Gallery
        self._create_cg_gallery()

    def _create_cg_gallery(self):
        """创建CG图鉴"""
        cgs = [
            CGEntry("cg_first_meeting", "初次相遇", "与助手的第一次见面", chapter=1),
            CGEntry("cg_first_chat", "闲聊时光", "第一次认真聊天", chapter=2),
            CGEntry("cg_confession", "心声", "听到了助手的心里话", chapter=3),
            CGEntry("cg_promise", "约定", "许下了彼此的承诺", chapter=3),
            CGEntry("cg_ending_good", "羁绊", "好结局的特别CG", chapter=5),
            CGEntry("cg_ending_true", "永恒", "真结局的特别CG", chapter=5),
            CGEntry("cg_ending_secret", "真相", "隐藏结局的CG", chapter=5),
        ]

        for cg in cgs:
            self.cg_gallery[cg.cg_id] = cg

    # ============================================================
    # 核心游戏逻辑
    # ============================================================

    def start_story(self, node_id: str = "c1_start") -> Optional[StoryNode]:
        """开始/继续故事"""
        node = self.nodes.get(node_id)
        if not node:
            logger.warning(f"未找到节点: {node_id}")
            return None

        # 检查条件
        if not self._check_conditions(node.conditions):
            logger.info(f"节点 {node_id} 条件不满足")
            return None

        self.current_node = node_id
        self.current_dialogue_index = 0

        # 应用节点效果
        self._apply_effects(node.effects)

        # 标记已读
        self.read_nodes.add(node_id)

        return node

    def get_next_dialogue(self) -> Optional[DialogLine]:
        """获取下一行对话"""
        if not self.current_node:
            return None

        node = self.nodes.get(self.current_node)
        if not node:
            return None

        if self.current_dialogue_index >= len(node.dialogues):
            return None

        dialogue = node.dialogues[self.current_dialogue_index]
        self.current_dialogue_index += 1

        # 触发回调
        if self.on_dialogue:
            self.on_dialogue(dialogue)

        return dialogue

    def get_available_choices(self) -> List[StoryChoice]:
        """获取可用选项"""
        if not self.current_node:
            return []

        node = self.nodes.get(self.current_node)
        if not node:
            return []

        available = []
        for choice in node.choices:
            if choice.hidden and not self._check_conditions(choice.conditions):
                continue
            available.append(choice)

        return available

    def make_choice(self, choice_id: str) -> Optional[StoryNode]:
        """做出选择"""
        if not self.current_node:
            return None

        node = self.nodes.get(self.current_node)
        if not node:
            return None

        # 查找选择
        selected_choice = None
        for choice in node.choices:
            if choice.choice_id == choice_id:
                selected_choice = choice
                break

        if not selected_choice:
            logger.warning(f"未找到选项: {choice_id}")
            return None

        # 检查条件
        if not self._check_conditions(selected_choice.conditions):
            logger.info(f"选项 {choice_id} 条件不满足")
            return None

        # 应用效果
        self._apply_effects(selected_choice.effects)

        # 记录选择历史
        self.choice_history.append({
            "node_id": self.current_node,
            "choice_id": choice_id,
            "timestamp": datetime.now().isoformat()
        })

        # 跳转到下一节点
        return self.start_story(selected_choice.next_node)

    def auto_advance(self) -> Optional[StoryNode]:
        """自动推进（无选项时）"""
        if not self.current_node:
            return None

        node = self.nodes.get(self.current_node)
        if not node or not node.auto_next:
            return None

        return self.start_story(node.auto_next)

    def check_ending(self) -> Optional[StoryEnding]:
        """检查是否达成结局"""
        for ending_id, ending in self.endings.items():
            if ending_id in self.unlocked_endings:
                continue

            if self._check_conditions(ending.conditions):
                self.unlocked_endings.add(ending_id)

                # 触发回调
                if self.on_ending_reach:
                    self.on_ending_reach(ending)

                return ending

        return None

    # ============================================================
    # 条件与效果
    # ============================================================

    def _check_conditions(self, conditions: List[StoryCondition]) -> bool:
        """检查条件列表"""
        for cond in conditions:
            if not self._check_single_condition(cond):
                return False
        return True

    def _check_single_condition(self, cond: StoryCondition) -> bool:
        """检查单个条件"""
        actual_value = self._get_condition_value(cond)

        if cond.operator == ">=":
            return actual_value >= cond.value
        elif cond.operator == "<=":
            return actual_value <= cond.value
        elif cond.operator == "==":
            return actual_value == cond.value
        elif cond.operator == "!=":
            return actual_value != cond.value
        elif cond.operator == ">":
            return actual_value > cond.value
        elif cond.operator == "<":
            return actual_value < cond.value
        elif cond.operator == "in":
            return actual_value in cond.value
        elif cond.operator == "not_in":
            return actual_value not in cond.value

        return False

    def _get_condition_value(self, cond: StoryCondition) -> Any:
        """获取条件的实际值"""
        if cond.condition_type == ConditionType.AFFECTION:
            return self._get_affection()
        elif cond.condition_type == ConditionType.FLAG:
            return cond.key in self.story_flags
        elif cond.condition_type == ConditionType.VARIABLE:
            return self.story_variables.get(cond.key)
        elif cond.condition_type == ConditionType.CHAPTER:
            if cond.key == "completed":
                return self.current_chapter - 1
            return self.current_chapter
        elif cond.condition_type == ConditionType.ROUTE:
            return self.current_route
        elif cond.condition_type == ConditionType.TIME:
            return datetime.now().hour
        elif cond.condition_type == ConditionType.INTERACTION:
            return self._get_total_interactions()

        return None

    def _apply_effects(self, effects: List[StoryEffect]) -> None:
        """应用效果列表"""
        for effect in effects:
            self._apply_single_effect(effect)

    def _apply_single_effect(self, effect: StoryEffect) -> None:
        """应用单个效果"""
        if effect.effect_type == "set_flag":
            if effect.value:
                self.story_flags.add(effect.target)
            else:
                self.story_flags.discard(effect.target)

        elif effect.effect_type == "set_variable":
            self.story_variables[effect.target] = effect.value

        elif effect.effect_type == "add_affection":
            if self.pet_system:
                self.pet_system.add_affection(effect.value)

        elif effect.effect_type == "unlock_cg":
            if effect.target not in self.unlocked_cgs:
                self.unlocked_cgs.add(effect.target)
                cg = self.cg_gallery.get(effect.target)
                if cg and self.on_cg_unlock:
                    self.on_cg_unlock(cg)

        elif effect.effect_type == "set_route":
            try:
                self.current_route = StoryRoute(effect.value)
            except ValueError:
                pass

        elif effect.effect_type == "set_chapter":
            self.current_chapter = effect.value

    def _get_affection(self) -> int:
        """获取好感度"""
        if self.pet_system:
            return getattr(self.pet_system.data, "affection", 0)
        return 0

    def _get_total_interactions(self) -> int:
        """获取总互动次数"""
        if self.pet_system:
            return getattr(self.pet_system.data, "total_interactions", 0)
        return 0

    # ============================================================
    # 状态管理
    # ============================================================

    def get_state(self) -> Dict[str, Any]:
        """获取存档状态"""
        return {
            "current_node": self.current_node,
            "current_dialogue_index": self.current_dialogue_index,
            "current_chapter": self.current_chapter,
            "current_route": self.current_route.value,
            "story_flags": list(self.story_flags),
            "story_variables": dict(self.story_variables),
            "unlocked_cgs": list(self.unlocked_cgs),
            "unlocked_endings": list(self.unlocked_endings),
            "read_nodes": list(self.read_nodes),
            "choice_history": self.choice_history[-50:]  # 只保留最近50个
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """加载存档状态"""
        self.current_node = state.get("current_node")
        self.current_dialogue_index = state.get("current_dialogue_index", 0)
        self.current_chapter = state.get("current_chapter", 1)

        route_str = state.get("current_route", "main")
        try:
            self.current_route = StoryRoute(route_str)
        except ValueError:
            self.current_route = StoryRoute.MAIN

        self.story_flags = set(state.get("story_flags", []))
        self.story_variables = dict(state.get("story_variables", {}))
        self.unlocked_cgs = set(state.get("unlocked_cgs", []))
        self.unlocked_endings = set(state.get("unlocked_endings", []))
        self.read_nodes = set(state.get("read_nodes", []))
        self.choice_history = list(state.get("choice_history", []))

    # ============================================================
    # 外部接口
    # ============================================================

    def get_unlocked_cgs(self) -> List[CGEntry]:
        """获取已解锁的CG"""
        return [
            self.cg_gallery[cg_id]
            for cg_id in self.unlocked_cgs
            if cg_id in self.cg_gallery
        ]

    def get_unlocked_endings(self) -> List[StoryEnding]:
        """获取已解锁的结局"""
        return [
            self.endings[ending_id]
            for ending_id in self.unlocked_endings
            if ending_id in self.endings
        ]

    def get_progress(self) -> Dict[str, Any]:
        """获取故事进度"""
        total_cgs = len(self.cg_gallery)
        unlocked_cgs = len(self.unlocked_cgs)

        total_endings = len(self.endings)
        unlocked_endings = len(self.unlocked_endings)

        total_nodes = len(self.nodes)
        read_nodes = len(self.read_nodes)

        return {
            "chapter": self.current_chapter,
            "route": self.current_route.value,
            "cg_progress": f"{unlocked_cgs}/{total_cgs}",
            "ending_progress": f"{unlocked_endings}/{total_endings}",
            "node_progress": f"{read_nodes}/{total_nodes}",
            "completion_rate": round(
                (unlocked_cgs + unlocked_endings + read_nodes) /
                (total_cgs + total_endings + total_nodes) * 100, 1
            )
        }

    def is_chapter_unlocked(self, chapter_id: int) -> bool:
        """检查章节是否解锁"""
        chapter = self.chapters.get(chapter_id)
        if not chapter:
            return False
        return self._check_conditions(chapter.unlock_conditions)

    def get_available_chapters(self) -> List[StoryChapter]:
        """获取可用章节"""
        return [
            chapter for chapter_id, chapter in self.chapters.items()
            if self.is_chapter_unlocked(chapter_id)
        ]


# 便捷函数
def create_narrative_engine(pet_system=None) -> BranchingNarrativeEngine:
    """创建分支叙事引擎"""
    return BranchingNarrativeEngine(pet_system)
