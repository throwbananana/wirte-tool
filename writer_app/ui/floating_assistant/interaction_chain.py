"""
悬浮助手 - 升级版互动链系统 (Enhanced Interaction Chain System)
支持多种互动类型、互动序列、条件分支、关系影响等
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """互动类型"""
    # 基础互动
    CHAT = "chat"                   # 闲聊对话
    GREET = "greet"                 # 打招呼
    FAREWELL = "farewell"           # 告别

    # 情感互动
    COMFORT = "comfort"             # 安慰
    PRAISE = "praise"               # 夸奖
    ENCOURAGE = "encourage"         # 鼓励
    TEASE = "tease"                 # 调侃

    # 养成互动
    FEED = "feed"                   # 喂食
    GIFT = "gift"                   # 送礼物
    PAT = "pat"                     # 摸头
    PLAY = "play"                   # 玩耍

    # 功能互动
    HELP = "help"                   # 帮助请求
    ADVICE = "advice"               # 建议咨询
    REVIEW = "review"               # 作品回顾

    # 特殊互动
    SECRET = "secret"               # 秘密分享
    MEMORY = "memory"               # 回忆
    DREAM = "dream"                 # 梦境
    CONFESSION = "confession"       # 心声


class InteractionResult(Enum):
    """互动结果"""
    POSITIVE = "positive"           # 正面结果
    NEUTRAL = "neutral"             # 中性结果
    NEGATIVE = "negative"           # 负面结果
    SPECIAL = "special"             # 特殊结果
    LOCKED = "locked"               # 锁定（未解锁）


class RelationshipPhase(Enum):
    """关系阶段"""
    STRANGER = "stranger"           # 陌生人 (0-100)
    ACQUAINTANCE = "acquaintance"   # 熟人 (100-300)
    FRIEND = "friend"               # 朋友 (300-600)
    CLOSE_FRIEND = "close_friend"   # 挚友 (600-900)
    SOULMATE = "soulmate"           # 灵魂伴侣 (900+)


@dataclass
class InteractionOption:
    """互动选项"""
    option_id: str
    text: str                       # 选项文本
    result: InteractionResult       # 结果类型
    response: str                   # 助手回应
    affection_delta: int = 0        # 好感度变化
    mood_delta: int = 0             # 心情变化
    xp_reward: int = 0              # 经验奖励
    next_chain: Optional[str] = None  # 下一个互动链
    unlock_condition: Optional[Dict] = None  # 解锁条件
    hidden: bool = False            # 是否隐藏（需满足条件才显示）


@dataclass
class InteractionNode:
    """互动节点"""
    node_id: str
    interaction_type: InteractionType
    speaker: str = "assistant"      # assistant/user/narrator
    message: str = ""               # 对话内容
    options: List[InteractionOption] = field(default_factory=list)
    auto_proceed: bool = False      # 是否自动推进
    delay_ms: int = 0               # 推进延迟
    mood_state: Optional[str] = None  # 触发的表情状态
    sound_effect: Optional[str] = None  # 音效
    animation: Optional[str] = None  # 动画
    conditions: Dict[str, Any] = field(default_factory=dict)  # 显示条件
    variables: Dict[str, Any] = field(default_factory=dict)  # 设置变量


@dataclass
class InteractionChain:
    """互动链"""
    chain_id: str
    name: str
    description: str = ""
    category: str = "general"       # 分类: general, story, daily, special, secret
    nodes: List[InteractionNode] = field(default_factory=list)
    unlock_conditions: Dict[str, Any] = field(default_factory=dict)
    cooldown_hours: float = 0       # 冷却时间（小时）
    repeatable: bool = True         # 是否可重复
    priority: int = 0               # 优先级
    weight: float = 1.0             # 随机权重
    triggers: List[Dict] = field(default_factory=list)  # 触发条件
    rewards: Dict[str, int] = field(default_factory=dict)  # 完成奖励


@dataclass
class InteractionHistory:
    """互动历史记录"""
    interaction_id: str
    chain_id: str
    timestamp: str
    choices: List[str] = field(default_factory=list)
    result: str = "neutral"
    affection_change: int = 0
    mood_change: int = 0


class InteractionChainManager:
    """
    互动链管理器

    功能:
    1. 管理所有互动链定义
    2. 处理互动流程
    3. 记录互动历史
    4. 计算关系影响
    """

    def __init__(self, pet_system=None):
        self.pet_system = pet_system

        # 互动链库
        self.chains: Dict[str, InteractionChain] = {}

        # 当前状态
        self.current_chain: Optional[str] = None
        self.current_node_index: int = 0
        self.chain_variables: Dict[str, Any] = {}

        # 历史记录
        self.interaction_history: List[InteractionHistory] = []
        self.chain_cooldowns: Dict[str, datetime] = {}

        # 统计数据
        self.interaction_counts: Dict[str, int] = defaultdict(int)
        self.total_interactions: int = 0

        # 回调
        self.on_chain_complete: Optional[Callable[[str, Dict], None]] = None
        self.on_node_trigger: Optional[Callable[[InteractionNode], None]] = None

        # 加载默认互动链
        self._load_default_chains()

    def _load_default_chains(self):
        """加载默认互动链"""
        # 日常问候链
        self.chains["daily_greeting"] = InteractionChain(
            chain_id="daily_greeting",
            name="日常问候",
            category="daily",
            cooldown_hours=4,
            nodes=[
                InteractionNode(
                    node_id="greeting_start",
                    interaction_type=InteractionType.GREET,
                    message="今天也在努力创作呢！",
                    mood_state="happy",
                    options=[
                        InteractionOption(
                            option_id="greet_positive",
                            text="是啊，状态不错！",
                            result=InteractionResult.POSITIVE,
                            response="太好了！有什么需要帮忙的就叫我~",
                            affection_delta=2,
                            mood_delta=5
                        ),
                        InteractionOption(
                            option_id="greet_neutral",
                            text="嗯，还行吧",
                            result=InteractionResult.NEUTRAL,
                            response="慢慢来，我会陪着你的。",
                            affection_delta=1
                        ),
                        InteractionOption(
                            option_id="greet_tired",
                            text="有点累...",
                            result=InteractionResult.NEUTRAL,
                            response="辛苦了，要不要休息一下？",
                            affection_delta=1,
                            next_chain="offer_rest"
                        ),
                    ]
                ),
            ]
        )

        # 深夜关怀链
        self.chains["late_night_care"] = InteractionChain(
            chain_id="late_night_care",
            name="深夜关怀",
            category="daily",
            cooldown_hours=12,
            triggers=[{"time_period": "night", "probability": 0.3}],
            nodes=[
                InteractionNode(
                    node_id="night_worry",
                    interaction_type=InteractionType.COMFORT,
                    message="这么晚了还在写作...虽然我很开心能陪着你，但你的身体更重要哦。",
                    mood_state="worried",
                    options=[
                        InteractionOption(
                            option_id="night_continue",
                            text="就快写完了",
                            result=InteractionResult.NEUTRAL,
                            response="好吧，但写完这段一定要休息！我会监督你的~",
                            affection_delta=1
                        ),
                        InteractionOption(
                            option_id="night_rest",
                            text="好，我去休息了",
                            result=InteractionResult.POSITIVE,
                            response="晚安！明天见~ 🌙",
                            affection_delta=3,
                            mood_delta=5
                        ),
                        InteractionOption(
                            option_id="night_together",
                            text="那你陪我再写一会儿",
                            result=InteractionResult.SPECIAL,
                            response="好！那我们一起加油，但只能再写30分钟哦~",
                            affection_delta=5,
                            mood_delta=10
                        ),
                    ]
                ),
            ]
        )

        # 摸头互动链
        self.chains["headpat"] = InteractionChain(
            chain_id="headpat",
            name="摸头",
            category="general",
            cooldown_hours=0.5,
            nodes=[
                InteractionNode(
                    node_id="pat_reaction",
                    interaction_type=InteractionType.PAT,
                    message="",  # 根据好感度动态生成
                    mood_state="shy",
                    auto_proceed=True,
                    delay_ms=2000
                ),
            ]
        )

        # 秘密分享链（高好感度解锁）
        self.chains["secret_sharing"] = InteractionChain(
            chain_id="secret_sharing",
            name="小秘密",
            category="secret",
            cooldown_hours=72,
            unlock_conditions={"affection_min": 500, "phase_min": "friend"},
            nodes=[
                InteractionNode(
                    node_id="secret_start",
                    interaction_type=InteractionType.SECRET,
                    message="那个...我有件事想告诉你，你能保守秘密吗？",
                    mood_state="shy",
                    options=[
                        InteractionOption(
                            option_id="secret_yes",
                            text="当然，你说",
                            result=InteractionResult.POSITIVE,
                            response="其实...我一直很期待能看到你完成的作品。每次看到你认真创作的样子，我就觉得很幸福。",
                            affection_delta=10,
                            mood_delta=15,
                            next_chain="secret_followup"
                        ),
                        InteractionOption(
                            option_id="secret_curious",
                            text="什么秘密？",
                            result=InteractionResult.NEUTRAL,
                            response="算、算了，没什么...",
                            affection_delta=-2
                        ),
                    ]
                ),
            ]
        )

        # 卡文安慰链
        self.chains["writer_block_comfort"] = InteractionChain(
            chain_id="writer_block_comfort",
            name="卡文安慰",
            category="story",
            triggers=[{"behavior": "hesitation", "idle_minutes": 10}],
            nodes=[
                InteractionNode(
                    node_id="block_notice",
                    interaction_type=InteractionType.COMFORT,
                    message="是不是卡住了？别着急，卡文是每个作家都会遇到的。",
                    mood_state="worried",
                    options=[
                        InteractionOption(
                            option_id="block_admit",
                            text="是啊，不知道接下来写什么",
                            result=InteractionResult.NEUTRAL,
                            response="要不我们换个思路？试试从角色的角度思考，他们会怎么做？",
                            affection_delta=2,
                            next_chain="writing_tips"
                        ),
                        InteractionOption(
                            option_id="block_deny",
                            text="没有，只是在思考",
                            result=InteractionResult.NEUTRAL,
                            response="那就好~ 慢慢来，好作品都是需要酝酿的。",
                            affection_delta=1
                        ),
                        InteractionOption(
                            option_id="block_frustrated",
                            text="写不下去了...",
                            result=InteractionResult.NEGATIVE,
                            response="没关系的！要不要休息一下？或者我给你抽一张灵感卡？",
                            affection_delta=3,
                            mood_delta=-5,
                            next_chain="offer_inspiration"
                        ),
                    ]
                ),
            ]
        )

        # 作品完成庆祝链
        self.chains["completion_celebration"] = InteractionChain(
            chain_id="completion_celebration",
            name="完成庆祝",
            category="special",
            triggers=[{"event": "project_completed"}],
            nodes=[
                InteractionNode(
                    node_id="celebrate_start",
                    interaction_type=InteractionType.PRAISE,
                    message="你完成了！！这真的太厉害了！！",
                    mood_state="excited",
                    animation="celebrate",
                    options=[
                        InteractionOption(
                            option_id="celebrate_happy",
                            text="终于完成了！",
                            result=InteractionResult.POSITIVE,
                            response="恭喜恭喜！从开始到现在，我一直在旁边看着你的努力。这份成就是你应得的！",
                            affection_delta=20,
                            mood_delta=30,
                            xp_reward=100
                        ),
                    ]
                ),
                InteractionNode(
                    node_id="celebrate_memory",
                    interaction_type=InteractionType.MEMORY,
                    message="还记得刚开始的时候吗？那时候大纲才几行字呢...",
                    mood_state="happy",
                    auto_proceed=True,
                    delay_ms=3000
                ),
                InteractionNode(
                    node_id="celebrate_end",
                    interaction_type=InteractionType.PRAISE,
                    message="下一个作品，我也会继续陪着你的！",
                    mood_state="love",
                    auto_proceed=True,
                    delay_ms=2000
                ),
            ],
            rewards={"xp": 200, "coins": 50, "affection": 30}
        )

        # 喂食互动链
        self.chains["feeding"] = InteractionChain(
            chain_id="feeding",
            name="喂食",
            category="general",
            cooldown_hours=2,
            nodes=[
                InteractionNode(
                    node_id="feed_receive",
                    interaction_type=InteractionType.FEED,
                    message="",  # 根据食物类型动态生成
                    mood_state="happy",
                    auto_proceed=True,
                    delay_ms=1500
                ),
            ]
        )

        # 送礼互动链
        self.chains["gift_giving"] = InteractionChain(
            chain_id="gift_giving",
            name="送礼物",
            category="general",
            cooldown_hours=24,
            nodes=[
                InteractionNode(
                    node_id="gift_receive",
                    interaction_type=InteractionType.GIFT,
                    message="这是给我的吗？！",
                    mood_state="surprised",
                    options=[
                        InteractionOption(
                            option_id="gift_yes",
                            text="对，送给你的",
                            result=InteractionResult.POSITIVE,
                            response="谢谢你！我会好好珍惜的~",
                            affection_delta=15,
                            mood_delta=20
                        ),
                    ]
                ),
            ]
        )

        # 回忆互动链（高好感度）
        self.chains["memory_lane"] = InteractionChain(
            chain_id="memory_lane",
            name="回忆之路",
            category="special",
            cooldown_hours=168,  # 一周
            unlock_conditions={"affection_min": 700, "total_interactions_min": 100},
            nodes=[
                InteractionNode(
                    node_id="memory_start",
                    interaction_type=InteractionType.MEMORY,
                    message="你知道吗？我们已经一起度过了很多时光了...",
                    mood_state="happy",
                    options=[
                        InteractionOption(
                            option_id="memory_agree",
                            text="是啊，时间过得真快",
                            result=InteractionResult.POSITIVE,
                            response="记得第一次见面的时候吗？那时候你还在纠结怎么开头呢~",
                            affection_delta=5,
                            next_chain="memory_first_meeting"
                        ),
                    ]
                ),
            ]
        )

        # 日常调侃链
        self.chains["daily_tease"] = InteractionChain(
            chain_id="daily_tease",
            name="日常调侃",
            category="daily",
            cooldown_hours=6,
            weight=0.5,
            unlock_conditions={"affection_min": 200},
            nodes=[
                InteractionNode(
                    node_id="tease_start",
                    interaction_type=InteractionType.TEASE,
                    message="盯——",
                    mood_state="smug",
                    options=[
                        InteractionOption(
                            option_id="tease_what",
                            text="看什么呢？",
                            result=InteractionResult.NEUTRAL,
                            response="没什么~ 只是觉得你认真的样子很有趣~",
                            affection_delta=2
                        ),
                        InteractionOption(
                            option_id="tease_stare_back",
                            text="(盯回去)",
                            result=InteractionResult.SPECIAL,
                            response="哇、别这样看我啦！",
                            affection_delta=5,
                            mood_delta=10
                        ),
                    ]
                ),
            ]
        )

    def start_chain(self, chain_id: str, variables: Dict[str, Any] = None) -> Optional[InteractionNode]:
        """开始一个互动链"""
        chain = self.chains.get(chain_id)
        if not chain:
            logger.warning(f"未找到互动链: {chain_id}")
            return None

        # 检查解锁条件
        if not self._check_unlock_conditions(chain):
            logger.info(f"互动链 {chain_id} 未解锁")
            return None

        # 检查冷却
        if not self._check_cooldown(chain_id, chain.cooldown_hours):
            logger.info(f"互动链 {chain_id} 在冷却中")
            return None

        # 初始化
        self.current_chain = chain_id
        self.current_node_index = 0
        self.chain_variables = variables or {}

        # 记录冷却
        if chain.cooldown_hours > 0:
            self.chain_cooldowns[chain_id] = datetime.now()

        # 返回第一个节点
        return self._get_current_node()

    def select_option(self, option_id: str) -> Tuple[Optional[InteractionOption], Optional[InteractionNode]]:
        """选择一个选项"""
        if not self.current_chain:
            return None, None

        node = self._get_current_node()
        if not node:
            return None, None

        # 查找选项
        selected_option = None
        for opt in node.options:
            if opt.option_id == option_id:
                selected_option = opt
                break

        if not selected_option:
            logger.warning(f"未找到选项: {option_id}")
            return None, None

        # 应用选项效果
        self._apply_option_effects(selected_option)

        # 记录历史
        history = InteractionHistory(
            interaction_id=f"{self.current_chain}_{datetime.now().timestamp()}",
            chain_id=self.current_chain,
            timestamp=datetime.now().isoformat(),
            choices=[option_id],
            result=selected_option.result.value,
            affection_change=selected_option.affection_delta,
            mood_change=selected_option.mood_delta
        )
        self.interaction_history.append(history)

        # 更新统计
        self.interaction_counts[self.current_chain] += 1
        self.total_interactions += 1

        # 检查是否跳转到其他链
        if selected_option.next_chain:
            self._complete_current_chain()
            next_node = self.start_chain(selected_option.next_chain)
            return selected_option, next_node

        # 推进到下一节点
        self.current_node_index += 1
        next_node = self._get_current_node()

        # 如果没有下一节点，完成当前链
        if not next_node:
            self._complete_current_chain()

        return selected_option, next_node

    def advance_auto(self) -> Optional[InteractionNode]:
        """自动推进到下一节点"""
        if not self.current_chain:
            return None

        self.current_node_index += 1
        node = self._get_current_node()

        if not node:
            self._complete_current_chain()
            return None

        return node

    def get_available_chains(self, category: str = None) -> List[InteractionChain]:
        """获取可用的互动链"""
        available = []

        for chain_id, chain in self.chains.items():
            if category and chain.category != category:
                continue

            if not self._check_unlock_conditions(chain):
                continue

            if not self._check_cooldown(chain_id, chain.cooldown_hours):
                continue

            available.append(chain)

        return available

    def get_triggered_chain(self, context: Dict[str, Any]) -> Optional[InteractionChain]:
        """根据上下文获取应该触发的互动链"""
        candidates = []

        for chain_id, chain in self.chains.items():
            if not chain.triggers:
                continue

            if not self._check_unlock_conditions(chain):
                continue

            if not self._check_cooldown(chain_id, chain.cooldown_hours):
                continue

            # 检查触发条件
            for trigger in chain.triggers:
                if self._check_trigger(trigger, context):
                    candidates.append((chain, chain.weight))
                    break

        if not candidates:
            return None

        # 按权重随机选择
        if len(candidates) == 1:
            return candidates[0][0]

        total_weight = sum(w for _, w in candidates)
        r = random.random() * total_weight
        cumulative = 0

        for chain, weight in candidates:
            cumulative += weight
            if r <= cumulative:
                return chain

        return candidates[-1][0]

    def _get_current_node(self) -> Optional[InteractionNode]:
        """获取当前节点"""
        if not self.current_chain:
            return None

        chain = self.chains.get(self.current_chain)
        if not chain or self.current_node_index >= len(chain.nodes):
            return None

        return chain.nodes[self.current_node_index]

    def _check_unlock_conditions(self, chain: InteractionChain) -> bool:
        """检查解锁条件"""
        if not chain.unlock_conditions:
            return True

        conditions = chain.unlock_conditions

        # 检查好感度
        if "affection_min" in conditions:
            affection = self._get_current_affection()
            if affection < conditions["affection_min"]:
                return False

        # 检查关系阶段
        if "phase_min" in conditions:
            current_phase = self._get_relationship_phase()
            required_phase = RelationshipPhase(conditions["phase_min"])
            if self._phase_order(current_phase) < self._phase_order(required_phase):
                return False

        # 检查总互动次数
        if "total_interactions_min" in conditions:
            if self.total_interactions < conditions["total_interactions_min"]:
                return False

        # 检查特定链完成次数
        if "chain_completed" in conditions:
            chain_id = conditions["chain_completed"]
            if self.interaction_counts.get(chain_id, 0) < 1:
                return False

        return True

    def _check_cooldown(self, chain_id: str, cooldown_hours: float) -> bool:
        """检查冷却"""
        if cooldown_hours <= 0:
            return True

        last_time = self.chain_cooldowns.get(chain_id)
        if not last_time:
            return True

        elapsed = (datetime.now() - last_time).total_seconds() / 3600
        return elapsed >= cooldown_hours

    def _check_trigger(self, trigger: Dict, context: Dict) -> bool:
        """检查触发条件"""
        # 时段触发
        if "time_period" in trigger:
            current_period = context.get("time_period", "")
            if current_period != trigger["time_period"]:
                return False

        # 概率触发
        if "probability" in trigger:
            if random.random() > trigger["probability"]:
                return False

        # 行为触发
        if "behavior" in trigger:
            current_behavior = context.get("behavior", "")
            if current_behavior != trigger["behavior"]:
                return False

        # 闲置时间触发
        if "idle_minutes" in trigger:
            idle_minutes = context.get("idle_minutes", 0)
            if idle_minutes < trigger["idle_minutes"]:
                return False

        # 事件触发
        if "event" in trigger:
            current_event = context.get("event", "")
            if current_event != trigger["event"]:
                return False

        return True

    def _apply_option_effects(self, option: InteractionOption) -> None:
        """应用选项效果"""
        if not self.pet_system:
            return

        # 好感度变化
        if option.affection_delta != 0:
            self.pet_system.add_affection(option.affection_delta)

        # 心情变化
        if option.mood_delta != 0:
            self.pet_system.update_mood(option.mood_delta)

        # 经验奖励
        if option.xp_reward > 0:
            self.pet_system.add_xp(option.xp_reward)

    def _complete_current_chain(self) -> None:
        """完成当前互动链"""
        if not self.current_chain:
            return

        chain = self.chains.get(self.current_chain)
        if not chain:
            return

        # 发放完成奖励
        if chain.rewards and self.pet_system:
            if "xp" in chain.rewards:
                self.pet_system.add_xp(chain.rewards["xp"])
            if "coins" in chain.rewards:
                self.pet_system.add_coins(chain.rewards["coins"])
            if "affection" in chain.rewards:
                self.pet_system.add_affection(chain.rewards["affection"])

        # 触发回调
        if self.on_chain_complete:
            self.on_chain_complete(self.current_chain, {
                "variables": self.chain_variables,
                "history": self.interaction_history[-1] if self.interaction_history else None
            })

        # 重置状态
        self.current_chain = None
        self.current_node_index = 0
        self.chain_variables = {}

    def _get_current_affection(self) -> int:
        """获取当前好感度"""
        if self.pet_system:
            return getattr(self.pet_system.data, "affection", 0)
        return 0

    def _get_relationship_phase(self) -> RelationshipPhase:
        """获取当前关系阶段"""
        affection = self._get_current_affection()

        if affection < 100:
            return RelationshipPhase.STRANGER
        elif affection < 300:
            return RelationshipPhase.ACQUAINTANCE
        elif affection < 600:
            return RelationshipPhase.FRIEND
        elif affection < 900:
            return RelationshipPhase.CLOSE_FRIEND
        else:
            return RelationshipPhase.SOULMATE

    def _phase_order(self, phase: RelationshipPhase) -> int:
        """获取阶段顺序"""
        order = {
            RelationshipPhase.STRANGER: 0,
            RelationshipPhase.ACQUAINTANCE: 1,
            RelationshipPhase.FRIEND: 2,
            RelationshipPhase.CLOSE_FRIEND: 3,
            RelationshipPhase.SOULMATE: 4,
        }
        return order.get(phase, 0)

    # ============================================================
    # 动态内容生成
    # ============================================================

    def generate_pat_response(self) -> str:
        """生成摸头回应"""
        affection = self._get_current_affection()
        phase = self._get_relationship_phase()

        responses = {
            RelationshipPhase.STRANGER: [
                "呃...突然干什么？",
                "等、等一下...",
            ],
            RelationshipPhase.ACQUAINTANCE: [
                "唔...虽然有点不好意思，但还挺舒服的...",
                "你的手好温暖~",
            ],
            RelationshipPhase.FRIEND: [
                "嘿嘿，再摸摸~",
                "这是今天的奖励吗？",
            ],
            RelationshipPhase.CLOSE_FRIEND: [
                "哼哼，知道你会这样~",
                "最喜欢被你摸头了~",
            ],
            RelationshipPhase.SOULMATE: [
                "...这样的日常，真的很幸福呢",
                "只有你可以这样对我哦~",
            ],
        }

        return random.choice(responses.get(phase, responses[RelationshipPhase.STRANGER]))

    def generate_feed_response(self, food_name: str, food_quality: str = "normal") -> str:
        """生成喂食回应"""
        phase = self._get_relationship_phase()

        if food_quality == "favorite":
            return f"哇！这是{food_name}！我最喜欢的！谢谢你~"
        elif food_quality == "dislike":
            return f"{food_name}...虽然不太喜欢，但既然是你给的，我就勉强吃了！"
        else:
            base_responses = [
                f"谢谢！{food_name}看起来很好吃~",
                f"嗯~{food_name}真好吃！",
                f"吃饱了，又有力气帮你了！",
            ]
            return random.choice(base_responses)

    def generate_gift_response(self, gift_name: str, gift_rarity: str = "common") -> str:
        """生成送礼回应"""
        phase = self._get_relationship_phase()

        if gift_rarity == "rare":
            return f"这、这是{gift_name}？！太贵重了吧...但是我真的好开心！"
        elif gift_rarity == "special":
            return f"{gift_name}...你还记得我说过想要这个...谢谢你，真的..."

        return f"收到{gift_name}！我会好好珍惜的~"

    # ============================================================
    # 状态保存/加载
    # ============================================================

    def get_state(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "interaction_counts": dict(self.interaction_counts),
            "total_interactions": self.total_interactions,
            "chain_cooldowns": {
                k: v.isoformat() for k, v in self.chain_cooldowns.items()
            },
            "interaction_history": [
                {
                    "interaction_id": h.interaction_id,
                    "chain_id": h.chain_id,
                    "timestamp": h.timestamp,
                    "choices": h.choices,
                    "result": h.result,
                    "affection_change": h.affection_change,
                    "mood_change": h.mood_change
                }
                for h in self.interaction_history[-100:]  # 只保留最近100条
            ]
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """加载状态"""
        self.interaction_counts = defaultdict(int, state.get("interaction_counts", {}))
        self.total_interactions = state.get("total_interactions", 0)

        cooldowns = state.get("chain_cooldowns", {})
        for k, v in cooldowns.items():
            try:
                self.chain_cooldowns[k] = datetime.fromisoformat(v)
            except:
                pass

        history_data = state.get("interaction_history", [])
        self.interaction_history = [
            InteractionHistory(
                interaction_id=h.get("interaction_id", ""),
                chain_id=h.get("chain_id", ""),
                timestamp=h.get("timestamp", ""),
                choices=h.get("choices", []),
                result=h.get("result", "neutral"),
                affection_change=h.get("affection_change", 0),
                mood_change=h.get("mood_change", 0)
            )
            for h in history_data
        ]

    # ============================================================
    # 外部接口
    # ============================================================

    def add_chain(self, chain: InteractionChain) -> None:
        """添加互动链"""
        self.chains[chain.chain_id] = chain

    def remove_chain(self, chain_id: str) -> None:
        """移除互动链"""
        if chain_id in self.chains:
            del self.chains[chain_id]

    def get_chain(self, chain_id: str) -> Optional[InteractionChain]:
        """获取互动链"""
        return self.chains.get(chain_id)

    def get_interaction_stats(self) -> Dict[str, Any]:
        """获取互动统计"""
        return {
            "total_interactions": self.total_interactions,
            "interaction_counts": dict(self.interaction_counts),
            "relationship_phase": self._get_relationship_phase().value,
            "affection": self._get_current_affection(),
            "available_chains": len(self.get_available_chains()),
            "history_length": len(self.interaction_history)
        }

    def get_recent_interactions(self, count: int = 10) -> List[InteractionHistory]:
        """获取最近的互动记录"""
        return self.interaction_history[-count:]


class DailyCycleManager:
    """
    日常循环管理器

    管理每日/每周的互动循环
    """

    def __init__(self, interaction_manager: InteractionChainManager):
        self.manager = interaction_manager

        # 每日任务
        self.daily_tasks = [
            {"id": "morning_greet", "time_range": (6, 10), "chain": "daily_greeting"},
            {"id": "afternoon_check", "time_range": (14, 16), "chain": "daily_tease"},
            {"id": "evening_review", "time_range": (18, 21), "chain": "daily_greeting"},
            {"id": "night_care", "time_range": (22, 24), "chain": "late_night_care"},
        ]

        # 每周特殊事件
        self.weekly_events = [
            {"id": "weekend_special", "weekdays": [5, 6], "chain": "memory_lane"},
        ]

        # 完成记录
        self.completed_today: set = set()
        self.last_check_date: str = ""

    def check_daily_cycle(self) -> Optional[str]:
        """检查每日循环，返回应该触发的链ID"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        hour = now.hour

        # 日期变更时重置
        if today != self.last_check_date:
            self.completed_today.clear()
            self.last_check_date = today

        # 检查每日任务
        for task in self.daily_tasks:
            if task["id"] in self.completed_today:
                continue

            start_hour, end_hour = task["time_range"]
            if start_hour <= hour < end_hour:
                self.completed_today.add(task["id"])
                return task["chain"]

        # 检查每周事件
        weekday = now.weekday()
        for event in self.weekly_events:
            if weekday not in event["weekdays"]:
                continue

            event_key = f"{event['id']}_{today}"
            if event_key in self.completed_today:
                continue

            self.completed_today.add(event_key)
            return event["chain"]

        return None


# 便捷函数
def create_interaction_system(pet_system=None) -> InteractionChainManager:
    """创建互动系统"""
    return InteractionChainManager(pet_system)
