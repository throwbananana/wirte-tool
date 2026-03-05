"""
悬浮助手 - 人际关系网络系统 (Relationship Network System)
管理NPC之间的关系、社交圈层、关系可视化
"""
import random
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
import logging
import math

logger = logging.getLogger(__name__)


class RelationType(Enum):
    """关系类型"""
    # 正面关系
    FRIENDSHIP = "friendship"           # 友情
    BEST_FRIEND = "best_friend"         # 挚友
    ADMIRATION = "admiration"           # 崇拜
    CRUSH = "crush"                     # 暗恋
    MUTUAL_LOVE = "mutual_love"         # 相互喜欢
    MENTORSHIP = "mentorship"           # 师徒
    SIBLING = "sibling"                 # 兄弟姐妹
    FAMILY = "family"                   # 家人
    ALLIANCE = "alliance"               # 同盟

    # 中性关系
    ACQUAINTANCE = "acquaintance"       # 认识
    CLASSMATE = "classmate"             # 同学
    CLUBMATE = "clubmate"               # 社团伙伴
    NEIGHBOR = "neighbor"               # 邻居

    # 负面关系
    RIVALRY = "rivalry"                 # 竞争
    TENSION = "tension"                 # 紧张
    JEALOUSY = "jealousy"               # 嫉妒
    CONFLICT = "conflict"               # 冲突
    ESTRANGED = "estranged"             # 疏远

    # 特殊关系
    SECRET = "secret"                   # 秘密关系
    COMPLICATED = "complicated"         # 复杂关系
    UNKNOWN = "unknown"                 # 未知关系


class RelationStrength(Enum):
    """关系强度"""
    VERY_WEAK = 1                       # 非常弱
    WEAK = 2                            # 弱
    NORMAL = 3                          # 一般
    STRONG = 4                          # 强
    VERY_STRONG = 5                     # 非常强


class SocialCircleType(Enum):
    """社交圈类型"""
    CLUB = "club"                       # 社团
    CLASS = "class"                     # 班级
    INTEREST = "interest"               # 兴趣小组
    SECRET = "secret"                   # 秘密组织
    INFORMAL = "informal"               # 非正式圈子


# 关系类型显示配置
RELATION_DISPLAY = {
    RelationType.FRIENDSHIP: {"name": "朋友", "color": "#4CAF50", "icon": "👫"},
    RelationType.BEST_FRIEND: {"name": "挚友", "color": "#2196F3", "icon": "💙"},
    RelationType.ADMIRATION: {"name": "崇拜", "color": "#9C27B0", "icon": "✨"},
    RelationType.CRUSH: {"name": "暗恋", "color": "#E91E63", "icon": "💗"},
    RelationType.MUTUAL_LOVE: {"name": "相恋", "color": "#FF4081", "icon": "💕"},
    RelationType.MENTORSHIP: {"name": "师徒", "color": "#FF9800", "icon": "📚"},
    RelationType.SIBLING: {"name": "兄妹", "color": "#795548", "icon": "👨‍👩‍👧"},
    RelationType.FAMILY: {"name": "家人", "color": "#8D6E63", "icon": "🏠"},
    RelationType.ALLIANCE: {"name": "同盟", "color": "#607D8B", "icon": "🤝"},
    RelationType.ACQUAINTANCE: {"name": "认识", "color": "#9E9E9E", "icon": "👋"},
    RelationType.CLASSMATE: {"name": "同学", "color": "#03A9F4", "icon": "🎒"},
    RelationType.CLUBMATE: {"name": "社友", "color": "#00BCD4", "icon": "🎭"},
    RelationType.NEIGHBOR: {"name": "邻居", "color": "#8BC34A", "icon": "🏘️"},
    RelationType.RIVALRY: {"name": "竞争", "color": "#FF5722", "icon": "⚔️"},
    RelationType.TENSION: {"name": "紧张", "color": "#F44336", "icon": "😤"},
    RelationType.JEALOUSY: {"name": "嫉妒", "color": "#673AB7", "icon": "😒"},
    RelationType.CONFLICT: {"name": "冲突", "color": "#D32F2F", "icon": "💢"},
    RelationType.ESTRANGED: {"name": "疏远", "color": "#757575", "icon": "💔"},
    RelationType.SECRET: {"name": "秘密", "color": "#311B92", "icon": "🤫"},
    RelationType.COMPLICATED: {"name": "复杂", "color": "#455A64", "icon": "❓"},
    RelationType.UNKNOWN: {"name": "未知", "color": "#BDBDBD", "icon": "❔"},
}


@dataclass
class RelationshipEvent:
    """关系事件记录"""
    event_id: str
    timestamp: str
    npc_a: str
    npc_b: str
    event_type: str                     # 事件类型
    description: str
    relation_change: int = 0            # 关系强度变化
    discovered_by_player: bool = False  # 是否被玩家发现


@dataclass
class NPCRelationship:
    """NPC之间的关系"""
    npc_a: str                          # NPC A的ID
    npc_b: str                          # NPC B的ID
    relation_type: RelationType         # 关系类型
    strength: int = 50                  # 关系强度 (0-100)
    is_mutual: bool = True              # 是否双向

    # 关系详情
    started_date: str = ""              # 开始日期
    description: str = ""               # 关系描述
    history: List[RelationshipEvent] = field(default_factory=list)

    # 玩家视角
    discovered: bool = False            # 玩家是否已发现这段关系
    discovery_date: str = ""            # 发现日期
    discovery_event: str = ""           # 发现时的事件

    # 动态状态
    current_mood: str = "neutral"       # 当前状态
    recent_interaction: str = ""        # 最近互动

    def to_dict(self) -> Dict:
        return {
            "npc_a": self.npc_a,
            "npc_b": self.npc_b,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "is_mutual": self.is_mutual,
            "started_date": self.started_date,
            "description": self.description,
            "history": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp,
                    "npc_a": e.npc_a,
                    "npc_b": e.npc_b,
                    "event_type": e.event_type,
                    "description": e.description,
                    "relation_change": e.relation_change,
                    "discovered_by_player": e.discovered_by_player
                }
                for e in self.history[-20:]  # 只保留最近20条
            ],
            "discovered": self.discovered,
            "discovery_date": self.discovery_date,
            "discovery_event": self.discovery_event,
            "current_mood": self.current_mood,
            "recent_interaction": self.recent_interaction
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "NPCRelationship":
        rel = cls(
            npc_a=data.get("npc_a", ""),
            npc_b=data.get("npc_b", ""),
            relation_type=RelationType(data.get("relation_type", "acquaintance")),
            strength=data.get("strength", 50),
            is_mutual=data.get("is_mutual", True)
        )

        rel.started_date = data.get("started_date", "")
        rel.description = data.get("description", "")

        for h in data.get("history", []):
            rel.history.append(RelationshipEvent(
                event_id=h.get("event_id", ""),
                timestamp=h.get("timestamp", ""),
                npc_a=h.get("npc_a", ""),
                npc_b=h.get("npc_b", ""),
                event_type=h.get("event_type", ""),
                description=h.get("description", ""),
                relation_change=h.get("relation_change", 0),
                discovered_by_player=h.get("discovered_by_player", False)
            ))

        rel.discovered = data.get("discovered", False)
        rel.discovery_date = data.get("discovery_date", "")
        rel.discovery_event = data.get("discovery_event", "")
        rel.current_mood = data.get("current_mood", "neutral")
        rel.recent_interaction = data.get("recent_interaction", "")

        return rel


@dataclass
class SocialCircle:
    """社交圈定义"""
    circle_id: str
    name: str
    circle_type: SocialCircleType
    description: str = ""

    # 成员
    members: List[str] = field(default_factory=list)  # NPC ID列表
    leader: str = ""                    # 核心人物
    founder: str = ""                   # 创始人

    # 属性
    is_public: bool = True              # 是否公开
    entry_condition: Dict = field(default_factory=dict)  # 加入条件
    activities: List[str] = field(default_factory=list)  # 活动

    # 玩家状态
    player_reputation: int = 0          # 玩家在圈子中的声望 (-100 到 100)
    player_is_member: bool = False      # 玩家是否是成员
    discovered: bool = False            # 玩家是否已发现

    # 专属事件
    event_pool: List[str] = field(default_factory=list)

    # 资源
    icon: str = ""
    color: str = "#FFFFFF"

    def to_dict(self) -> Dict:
        return {
            "circle_id": self.circle_id,
            "name": self.name,
            "circle_type": self.circle_type.value,
            "description": self.description,
            "members": self.members,
            "leader": self.leader,
            "founder": self.founder,
            "is_public": self.is_public,
            "entry_condition": self.entry_condition,
            "activities": self.activities,
            "player_reputation": self.player_reputation,
            "player_is_member": self.player_is_member,
            "discovered": self.discovered,
            "event_pool": self.event_pool,
            "icon": self.icon,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SocialCircle":
        circle = cls(
            circle_id=data.get("circle_id", ""),
            name=data.get("name", ""),
            circle_type=SocialCircleType(data.get("circle_type", "informal")),
            description=data.get("description", "")
        )

        circle.members = data.get("members", [])
        circle.leader = data.get("leader", "")
        circle.founder = data.get("founder", "")
        circle.is_public = data.get("is_public", True)
        circle.entry_condition = data.get("entry_condition", {})
        circle.activities = data.get("activities", [])
        circle.player_reputation = data.get("player_reputation", 0)
        circle.player_is_member = data.get("player_is_member", False)
        circle.discovered = data.get("discovered", False)
        circle.event_pool = data.get("event_pool", [])
        circle.icon = data.get("icon", "")
        circle.color = data.get("color", "#FFFFFF")

        return circle


class RelationshipNetworkManager:
    """
    人际关系网络管理器

    功能:
    1. 管理NPC之间的关系
    2. 管理社交圈
    3. 生成可视化数据
    4. 处理关系发现和变化
    """

    def __init__(self, pet_system=None, npc_manager=None):
        self.pet_system = pet_system
        self.npc_manager = npc_manager

        # 关系数据
        self.relationships: Dict[str, NPCRelationship] = {}  # key: "npcA_npcB"

        # 社交圈数据
        self.circles: Dict[str, SocialCircle] = {}

        # 关系图缓存
        self._graph_cache = None
        self._cache_dirty = True

        # 回调
        self.on_relationship_discovered: Optional[callable] = None
        self.on_relationship_changed: Optional[callable] = None
        self.on_circle_joined: Optional[callable] = None

        # 加载数据
        self._load_definitions()
        self._load_state()

        # 创建默认数据
        if not self.relationships:
            self._create_default_relationships()
        if not self.circles:
            self._create_default_circles()

    def _get_relation_key(self, npc_a: str, npc_b: str) -> str:
        """获取关系键（确保顺序一致）"""
        return "_".join(sorted([npc_a, npc_b]))

    def _load_definitions(self):
        """加载关系定义"""
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "npc_relationships.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for rel_data in data.get("relationships", []):
                    rel = NPCRelationship.from_dict(rel_data)
                    key = self._get_relation_key(rel.npc_a, rel.npc_b)
                    self.relationships[key] = rel

                for circle_data in data.get("circles", []):
                    circle = SocialCircle.from_dict(circle_data)
                    self.circles[circle.circle_id] = circle

                logger.info(f"加载了 {len(self.relationships)} 段关系和 {len(self.circles)} 个社交圈")
        except Exception as e:
            logger.warning(f"加载关系定义失败: {e}")

    def _load_state(self):
        """加载状态"""
        if not self.pet_system:
            return

        try:
            state = getattr(self.pet_system.data, "relationship_network_state", {}) or {}

            # 加载发现状态
            for key, discovered in state.get("discovered_relationships", {}).items():
                if key in self.relationships:
                    self.relationships[key].discovered = discovered

            # 加载玩家圈子状态
            for circle_id, circle_state in state.get("circle_states", {}).items():
                if circle_id in self.circles:
                    self.circles[circle_id].player_reputation = circle_state.get("reputation", 0)
                    self.circles[circle_id].player_is_member = circle_state.get("is_member", False)
                    self.circles[circle_id].discovered = circle_state.get("discovered", False)

        except Exception as e:
            logger.warning(f"加载关系状态失败: {e}")

    def _save_state(self):
        """保存状态"""
        if not self.pet_system:
            return

        try:
            state = {
                "discovered_relationships": {
                    key: rel.discovered
                    for key, rel in self.relationships.items()
                },
                "circle_states": {
                    circle_id: {
                        "reputation": circle.player_reputation,
                        "is_member": circle.player_is_member,
                        "discovered": circle.discovered
                    }
                    for circle_id, circle in self.circles.items()
                }
            }
            self.pet_system.data.relationship_network_state = state
            self.pet_system.save()
        except Exception as e:
            logger.warning(f"保存关系状态失败: {e}")

    def _create_default_relationships(self):
        """创建默认关系"""
        default_relationships = [
            # 文学社内部关系
            NPCRelationship(
                npc_a="xiaoxia",
                npc_b="xuechang",
                relation_type=RelationType.ADMIRATION,
                strength=70,
                description="小夏很崇拜学长的文学素养",
                discovered=True
            ),
            NPCRelationship(
                npc_a="xiaoxia",
                npc_b="meimei",
                relation_type=RelationType.FRIENDSHIP,
                strength=60,
                description="文学社的好朋友，经常一起讨论创作",
                discovered=True
            ),
            NPCRelationship(
                npc_a="xuechang",
                npc_b="meimei",
                relation_type=RelationType.MENTORSHIP,
                strength=55,
                description="学长有时会指导诗诗的写作",
                discovered=False
            ),
            NPCRelationship(
                npc_a="xuechang",
                npc_b="teacher_wang",
                relation_type=RelationType.MENTORSHIP,
                strength=80,
                description="王老师对学长寄予厚望",
                discovered=True
            ),
            NPCRelationship(
                npc_a="xiaoxia",
                npc_b="teacher_wang",
                relation_type=RelationType.FRIENDSHIP,
                strength=50,
                description="老师和学生的良好关系",
                discovered=True
            ),
            # 一些隐藏关系
            NPCRelationship(
                npc_a="meimei",
                npc_b="teacher_wang",
                relation_type=RelationType.SECRET,
                strength=40,
                description="诗诗似乎和王老师有什么不为人知的联系...",
                discovered=False
            ),
        ]

        for rel in default_relationships:
            key = self._get_relation_key(rel.npc_a, rel.npc_b)
            self.relationships[key] = rel

        self._cache_dirty = True
        logger.info(f"创建了 {len(default_relationships)} 段默认关系")

    def _create_default_circles(self):
        """创建默认社交圈"""
        default_circles = [
            SocialCircle(
                circle_id="literature_club",
                name="文学社",
                circle_type=SocialCircleType.CLUB,
                description="学校的文学社团，定期举办创作活动和读书会",
                members=["xiaoxia", "xuechang", "meimei", "teacher_wang"],
                leader="xuechang",
                founder="teacher_wang",
                is_public=True,
                activities=["读书会", "创作交流", "社刊编辑"],
                player_reputation=0,
                player_is_member=True,
                discovered=True,
                icon="📚",
                color="#4A90D9"
            ),
            SocialCircle(
                circle_id="class_2_3",
                name="2年3班",
                circle_type=SocialCircleType.CLASS,
                description="你所在的班级",
                members=["xiaoxia"],
                is_public=True,
                player_is_member=True,
                discovered=True,
                icon="🎒",
                color="#4CAF50"
            ),
            SocialCircle(
                circle_id="anime_lovers",
                name="追番党",
                circle_type=SocialCircleType.INTEREST,
                description="一群喜欢看动漫的同学组成的非正式小圈子",
                members=["xiaoxia"],
                is_public=True,
                activities=["讨论新番", "漫展", "cosplay"],
                discovered=False,
                icon="🎬",
                color="#E91E63"
            ),
            SocialCircle(
                circle_id="secret_writers",
                name="地下写手联盟",
                circle_type=SocialCircleType.SECRET,
                description="据说是一群匿名发表作品的神秘写手...",
                members=["xuechang"],
                is_public=False,
                discovered=False,
                entry_condition={"event_completed": "secret_room_explore"},
                icon="🎭",
                color="#311B92"
            ),
        ]

        for circle in default_circles:
            self.circles[circle.circle_id] = circle

        logger.info(f"创建了 {len(default_circles)} 个默认社交圈")

    # ============================================================
    # 关系管理
    # ============================================================

    def get_relationship(self, npc_a: str, npc_b: str) -> Optional[NPCRelationship]:
        """获取两个NPC之间的关系"""
        key = self._get_relation_key(npc_a, npc_b)
        return self.relationships.get(key)

    def set_relationship(self, npc_a: str, npc_b: str,
                         relation_type: RelationType,
                         strength: int = 50,
                         description: str = "") -> NPCRelationship:
        """设置两个NPC之间的关系"""
        key = self._get_relation_key(npc_a, npc_b)

        rel = NPCRelationship(
            npc_a=npc_a,
            npc_b=npc_b,
            relation_type=relation_type,
            strength=strength,
            description=description,
            started_date=datetime.now().strftime("%Y-%m-%d")
        )

        self.relationships[key] = rel
        self._cache_dirty = True
        self._save_state()

        return rel

    def update_relationship_strength(self, npc_a: str, npc_b: str, delta: int,
                                     reason: str = "") -> Optional[Dict]:
        """更新关系强度"""
        rel = self.get_relationship(npc_a, npc_b)
        if not rel:
            return None

        old_strength = rel.strength
        rel.strength = max(0, min(100, rel.strength + delta))

        # 记录历史
        event = RelationshipEvent(
            event_id=f"strength_change_{datetime.now().timestamp()}",
            timestamp=datetime.now().isoformat(),
            npc_a=npc_a,
            npc_b=npc_b,
            event_type="strength_change",
            description=reason,
            relation_change=delta
        )
        rel.history.append(event)

        self._cache_dirty = True
        self._save_state()

        if self.on_relationship_changed:
            self.on_relationship_changed(npc_a, npc_b, old_strength, rel.strength)

        return {
            "old_strength": old_strength,
            "new_strength": rel.strength,
            "delta": delta
        }

    def discover_relationship(self, npc_a: str, npc_b: str,
                              discovery_event: str = "") -> Optional[Dict]:
        """发现一段关系"""
        rel = self.get_relationship(npc_a, npc_b)
        if not rel or rel.discovered:
            return None

        rel.discovered = True
        rel.discovery_date = datetime.now().strftime("%Y-%m-%d")
        rel.discovery_event = discovery_event

        self._save_state()

        if self.on_relationship_discovered:
            self.on_relationship_discovered(npc_a, npc_b, rel)

        display = RELATION_DISPLAY.get(rel.relation_type, {})

        return {
            "npc_a": npc_a,
            "npc_b": npc_b,
            "relation_type": rel.relation_type.value,
            "relation_name": display.get("name", "未知"),
            "description": rel.description,
            "icon": display.get("icon", "❔")
        }

    def get_npc_relationships(self, npc_id: str, discovered_only: bool = True) -> List[Dict]:
        """获取某个NPC的所有关系"""
        results = []

        for key, rel in self.relationships.items():
            if npc_id not in [rel.npc_a, rel.npc_b]:
                continue

            if discovered_only and not rel.discovered:
                continue

            other_npc = rel.npc_b if rel.npc_a == npc_id else rel.npc_a
            display = RELATION_DISPLAY.get(rel.relation_type, {})

            results.append({
                "npc_id": other_npc,
                "relation_type": rel.relation_type.value,
                "relation_name": display.get("name", "未知"),
                "strength": rel.strength,
                "icon": display.get("icon", "❔"),
                "color": display.get("color", "#BDBDBD"),
                "description": rel.description
            })

        return results

    # ============================================================
    # 社交圈管理
    # ============================================================

    def get_circle(self, circle_id: str) -> Optional[SocialCircle]:
        """获取社交圈"""
        return self.circles.get(circle_id)

    def get_npc_circles(self, npc_id: str) -> List[SocialCircle]:
        """获取NPC所属的社交圈"""
        return [
            circle for circle in self.circles.values()
            if npc_id in circle.members
        ]

    def get_discovered_circles(self) -> List[SocialCircle]:
        """获取已发现的社交圈"""
        return [circle for circle in self.circles.values() if circle.discovered]

    def discover_circle(self, circle_id: str) -> bool:
        """发现社交圈"""
        circle = self.circles.get(circle_id)
        if not circle or circle.discovered:
            return False

        circle.discovered = True
        self._save_state()
        return True

    def join_circle(self, circle_id: str) -> Dict[str, Any]:
        """加入社交圈"""
        circle = self.circles.get(circle_id)
        if not circle:
            return {"success": False, "message": "社交圈不存在"}

        if circle.player_is_member:
            return {"success": False, "message": "你已经是成员了"}

        # 检查加入条件
        if circle.entry_condition:
            condition = circle.entry_condition

            # 检查事件完成条件
            if "event_completed" in condition:
                required_event = condition["event_completed"]
                completed_events = set()
                if self.pet_system and hasattr(self.pet_system, 'data'):
                    completed_events = getattr(self.pet_system.data, 'completed_events', set()) or set()
                if required_event not in completed_events:
                    return {"success": False, "message": f"需要先完成特定事件才能加入"}

            # 检查声望条件
            if "min_reputation" in condition:
                min_rep = condition["min_reputation"]
                if circle.player_reputation < min_rep:
                    return {"success": False, "message": f"需要声望达到 {min_rep} 才能加入"}

            # 检查好感度条件
            if "min_affection" in condition:
                min_aff = condition["min_affection"]
                if self.pet_system and hasattr(self.pet_system, 'data'):
                    current_aff = getattr(self.pet_system.data, 'affection', 0)
                    if current_aff < min_aff:
                        return {"success": False, "message": f"需要好感度达到 {min_aff} 才能加入"}

            # 检查成员介绍条件
            if "introduced_by" in condition:
                introducer = condition["introduced_by"]
                # 检查是否与介绍人有足够好的关系
                if self.npc_manager:
                    npc = self.npc_manager.get_npc(introducer)
                    if npc:
                        affection = getattr(npc, 'player_affection', 0)
                        if affection < 50:
                            return {"success": False, "message": f"需要与 {npc.name} 建立更好的关系才能获得介绍"}

        circle.player_is_member = True
        self._save_state()

        if self.on_circle_joined:
            self.on_circle_joined(circle_id)

        return {
            "success": True,
            "message": f"成功加入{circle.name}！",
            "circle": circle
        }

    def update_reputation(self, circle_id: str, delta: int) -> Optional[int]:
        """更新玩家在社交圈的声望"""
        circle = self.circles.get(circle_id)
        if not circle:
            return None

        circle.player_reputation = max(-100, min(100, circle.player_reputation + delta))
        self._save_state()
        return circle.player_reputation

    # ============================================================
    # 可视化数据生成
    # ============================================================

    def get_network_graph_data(self, discovered_only: bool = True,
                                include_player: bool = True) -> Dict[str, Any]:
        """
        生成关系网络图数据（用于可视化）

        Returns:
            {
                "nodes": [
                    {"id": "npc_id", "name": "名字", "group": "circle_id", ...}
                ],
                "links": [
                    {"source": "npc_a", "target": "npc_b", "type": "friendship", ...}
                ],
                "circles": [...]
            }
        """
        nodes = []
        links = []
        npc_set = set()

        # 生成关系边
        for key, rel in self.relationships.items():
            if discovered_only and not rel.discovered:
                continue

            npc_set.add(rel.npc_a)
            npc_set.add(rel.npc_b)

            display = RELATION_DISPLAY.get(rel.relation_type, {})

            links.append({
                "source": rel.npc_a,
                "target": rel.npc_b,
                "type": rel.relation_type.value,
                "name": display.get("name", "未知"),
                "strength": rel.strength,
                "color": display.get("color", "#BDBDBD"),
                "icon": display.get("icon", "❔"),
                "description": rel.description if rel.discovered else "???"
            })

        # 生成节点
        for npc_id in npc_set:
            node_data = {
                "id": npc_id,
                "name": npc_id,
                "group": "unknown",
                "is_player": False
            }

            # 从NPC管理器获取详细信息
            if self.npc_manager:
                npc = self.npc_manager.get_npc(npc_id)
                if npc:
                    node_data["name"] = npc.name
                    node_data["portrait"] = npc.portrait
                    node_data["color"] = npc.theme_color
                    node_data["role"] = npc.role.value

                # 获取与玩家的关系
                rel = self.npc_manager.get_relation(npc_id)
                if rel:
                    node_data["player_affection"] = rel.affection
                    node_data["player_phase"] = rel.phase.value

            # 确定主要社交圈
            npc_circles = self.get_npc_circles(npc_id)
            if npc_circles:
                node_data["group"] = npc_circles[0].circle_id
                node_data["circles"] = [c.circle_id for c in npc_circles]

            nodes.append(node_data)

        # 添加玩家节点
        if include_player:
            player_node = {
                "id": "player",
                "name": "你",
                "is_player": True,
                "color": "#FFD700",
                "group": "player"
            }
            nodes.append(player_node)

            # 添加玩家与NPC的关系边
            if self.npc_manager:
                for npc_id in npc_set:
                    rel = self.npc_manager.get_relation(npc_id)
                    if rel and rel.affection > 0:
                        # 根据好感度确定关系类型
                        player_rel_type = self._get_player_relation_type(rel.affection)
                        display = RELATION_DISPLAY.get(player_rel_type, {})

                        links.append({
                            "source": "player",
                            "target": npc_id,
                            "type": player_rel_type.value,
                            "name": display.get("name", "认识"),
                            "strength": min(100, rel.affection // 7),  # 转换为0-100
                            "color": "#FFD700",
                            "is_player_link": True
                        })

        # 社交圈数据
        circles_data = []
        for circle in self.circles.values():
            if discovered_only and not circle.discovered:
                continue

            circles_data.append({
                "id": circle.circle_id,
                "name": circle.name,
                "type": circle.circle_type.value,
                "members": circle.members,
                "leader": circle.leader,
                "color": circle.color,
                "icon": circle.icon,
                "player_is_member": circle.player_is_member,
                "player_reputation": circle.player_reputation
            })

        return {
            "nodes": nodes,
            "links": links,
            "circles": circles_data
        }

    def _get_player_relation_type(self, affection: int) -> RelationType:
        """根据好感度获取玩家关系类型"""
        if affection < 21:
            return RelationType.ACQUAINTANCE
        elif affection < 100:
            return RelationType.CLASSMATE
        elif affection < 200:
            return RelationType.FRIENDSHIP
        elif affection < 400:
            return RelationType.FRIENDSHIP
        else:
            return RelationType.BEST_FRIEND

    def get_relationship_chart_data(self, center_npc: str) -> Dict[str, Any]:
        """
        生成以某个NPC为中心的关系图数据

        Returns:
            {
                "center": {...},
                "first_degree": [...],  # 直接关系
                "second_degree": [...], # 间接关系
            }
        """
        first_degree = []
        second_degree = []
        first_degree_npcs = set()

        # 获取中心NPC信息
        center_data = {"id": center_npc, "name": center_npc}
        if self.npc_manager:
            npc = self.npc_manager.get_npc(center_npc)
            if npc:
                center_data["name"] = npc.name
                center_data["portrait"] = npc.portrait
                center_data["color"] = npc.theme_color

        # 一度关系
        for key, rel in self.relationships.items():
            if not rel.discovered:
                continue

            if center_npc not in [rel.npc_a, rel.npc_b]:
                continue

            other_npc = rel.npc_b if rel.npc_a == center_npc else rel.npc_a
            first_degree_npcs.add(other_npc)

            display = RELATION_DISPLAY.get(rel.relation_type, {})

            node_data = {
                "id": other_npc,
                "name": other_npc,
                "relation_type": rel.relation_type.value,
                "relation_name": display.get("name", "未知"),
                "strength": rel.strength,
                "color": display.get("color", "#BDBDBD")
            }

            if self.npc_manager:
                npc = self.npc_manager.get_npc(other_npc)
                if npc:
                    node_data["name"] = npc.name
                    node_data["portrait"] = npc.portrait

            first_degree.append(node_data)

        # 二度关系
        for first_npc in first_degree_npcs:
            for key, rel in self.relationships.items():
                if not rel.discovered:
                    continue

                if first_npc not in [rel.npc_a, rel.npc_b]:
                    continue

                other_npc = rel.npc_b if rel.npc_a == first_npc else rel.npc_a

                if other_npc == center_npc:
                    continue
                if other_npc in first_degree_npcs:
                    continue

                # 检查是否已添加
                if any(n["id"] == other_npc for n in second_degree):
                    continue

                display = RELATION_DISPLAY.get(rel.relation_type, {})

                node_data = {
                    "id": other_npc,
                    "name": other_npc,
                    "via": first_npc,
                    "relation_type": rel.relation_type.value,
                    "color": display.get("color", "#BDBDBD")
                }

                if self.npc_manager:
                    npc = self.npc_manager.get_npc(other_npc)
                    if npc:
                        node_data["name"] = npc.name

                second_degree.append(node_data)

        return {
            "center": center_data,
            "first_degree": first_degree,
            "second_degree": second_degree
        }

    # ============================================================
    # 统计与分析
    # ============================================================

    def get_network_stats(self) -> Dict[str, Any]:
        """获取关系网络统计"""
        total_relationships = len(self.relationships)
        discovered_relationships = sum(1 for r in self.relationships.values() if r.discovered)

        # 关系类型分布
        type_distribution = defaultdict(int)
        for rel in self.relationships.values():
            if rel.discovered:
                type_distribution[rel.relation_type.value] += 1

        # 社交圈统计
        total_circles = len(self.circles)
        discovered_circles = sum(1 for c in self.circles.values() if c.discovered)
        joined_circles = sum(1 for c in self.circles.values() if c.player_is_member)

        return {
            "total_relationships": total_relationships,
            "discovered_relationships": discovered_relationships,
            "discovery_progress": discovered_relationships / total_relationships if total_relationships > 0 else 0,
            "type_distribution": dict(type_distribution),
            "total_circles": total_circles,
            "discovered_circles": discovered_circles,
            "joined_circles": joined_circles
        }

    def get_undiscovered_hints(self) -> List[Dict]:
        """获取未发现关系的提示"""
        hints = []

        for key, rel in self.relationships.items():
            if rel.discovered:
                continue

            # 生成模糊提示
            hint = {
                "hint_type": "relationship",
                "involved_npcs": [rel.npc_a, rel.npc_b],
                "hint_text": self._generate_relationship_hint(rel)
            }
            hints.append(hint)

        for circle in self.circles.values():
            if circle.discovered:
                continue

            hint = {
                "hint_type": "circle",
                "circle_id": circle.circle_id,
                "hint_text": f"据说有一个叫「{circle.name}」的圈子..."
            }
            hints.append(hint)

        return hints

    def _generate_relationship_hint(self, rel: NPCRelationship) -> str:
        """生成关系提示"""
        templates = [
            "似乎{npc_a}和{npc_b}之间有什么特别的联系...",
            "有传言说{npc_a}和{npc_b}的关系不一般...",
            "{npc_a}提到{npc_b}时，表情有些微妙...",
            "在{npc_a}的身边，经常能看到{npc_b}的身影..."
        ]

        npc_a_name = rel.npc_a
        npc_b_name = rel.npc_b

        if self.npc_manager:
            npc_a = self.npc_manager.get_npc(rel.npc_a)
            npc_b = self.npc_manager.get_npc(rel.npc_b)
            if npc_a:
                npc_a_name = npc_a.name
            if npc_b:
                npc_b_name = npc_b.name

        return random.choice(templates).format(npc_a=npc_a_name, npc_b=npc_b_name)


# 便捷函数
def create_relationship_network(pet_system=None, npc_manager=None) -> RelationshipNetworkManager:
    """创建关系网络系统"""
    return RelationshipNetworkManager(pet_system, npc_manager)
