"""
悬浮助手 - NPC角色系统 (NPC Character System)
完整的NPC定义、性格、日程、好感度管理
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class NPCRole(Enum):
    """NPC角色类型"""
    CLASSMATE = "classmate"           # 同班同学
    UPPERCLASSMAN = "upperclassman"   # 学长/学姐
    UNDERCLASSMAN = "underclassman"   # 学弟/学妹
    TEACHER = "teacher"               # 老师
    CLUB_MEMBER = "club_member"       # 社团成员
    CLUB_PRESIDENT = "club_president" # 社长
    STUDENT_COUNCIL = "student_council"  # 学生会成员
    LIBRARIAN = "librarian"           # 图书管理员
    SHOPKEEPER = "shopkeeper"         # 小卖部店员
    MYSTERIOUS = "mysterious"         # 神秘人物


class NPCPersonality(Enum):
    """NPC性格特质"""
    # 外向性
    OUTGOING = "outgoing"             # 外向
    INTROVERTED = "introverted"       # 内向

    # 情绪稳定性
    CALM = "calm"                     # 冷静
    EMOTIONAL = "emotional"           # 感性

    # 态度
    FRIENDLY = "friendly"             # 友善
    TSUNDERE = "tsundere"             # 傲娇
    KUUDERE = "kuudere"               # 冷淡
    DANDERE = "dandere"               # 害羞

    # 特殊
    BOOKWORM = "bookworm"             # 书呆子
    SPORTY = "sporty"                 # 运动系
    ARTISTIC = "artistic"             # 艺术系
    MYSTERIOUS = "mysterious"         # 神秘
    CHEERFUL = "cheerful"             # 开朗
    SERIOUS = "serious"               # 认真
    LAZY = "lazy"                     # 懒散
    PERFECTIONIST = "perfectionist"   # 完美主义


class NPCRelationPhase(Enum):
    """与NPC的关系阶段"""
    UNKNOWN = "unknown"               # 不认识 (0)
    KNOWN = "known"                   # 知道名字 (1-20)
    ACQUAINTANCE = "acquaintance"     # 点头之交 (21-50)
    CLASSMATE = "classmate"           # 普通同学 (51-100)
    FRIENDLY = "friendly"             # 友好 (101-200)
    GOOD_FRIEND = "good_friend"       # 好友 (201-400)
    BEST_FRIEND = "best_friend"       # 挚友 (401-700)
    CONFIDANT = "confidant"           # 知心人 (701+)


class GiftReaction(Enum):
    """礼物反应"""
    LOVE = "love"                     # 超喜欢 (+15好感)
    LIKE = "like"                     # 喜欢 (+8好感)
    NEUTRAL = "neutral"               # 一般 (+3好感)
    DISLIKE = "dislike"               # 不喜欢 (+0好感)
    HATE = "hate"                     # 讨厌 (-5好感)


@dataclass
class NPCScheduleEntry:
    """NPC日程条目"""
    time_start: str                   # 开始时间 "HH:MM"
    time_end: str                     # 结束时间 "HH:MM"
    location: str                     # 地点ID
    activity: str                     # 活动描述
    interruptible: bool = True        # 是否可打断
    probability: float = 1.0          # 出现概率


@dataclass
class NPCMemory:
    """NPC记忆条目"""
    memory_id: str
    timestamp: str
    event_type: str                   # 事件类型
    description: str
    emotional_impact: int             # 情感影响 (-10 到 +10)
    keywords: List[str] = field(default_factory=list)


@dataclass
class NPCCharacter:
    """NPC角色完整定义"""
    # 基础信息
    npc_id: str
    name: str
    nickname: str = ""                # 昵称
    gender: str = "female"            # 性别
    age: int = 17                     # 年龄
    birthday: str = ""                # 生日 "MM-DD"
    blood_type: str = ""              # 血型

    # 角色定位
    role: NPCRole = NPCRole.CLASSMATE
    class_name: str = ""              # 班级
    club: str = ""                    # 社团

    # 性格与特质
    personality: List[NPCPersonality] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)  # 额外特质标签

    # 兴趣爱好
    interests: List[str] = field(default_factory=list)
    favorite_topics: List[str] = field(default_factory=list)
    disliked_topics: List[str] = field(default_factory=list)

    # 日程安排
    weekday_schedule: List[NPCScheduleEntry] = field(default_factory=list)
    weekend_schedule: List[NPCScheduleEntry] = field(default_factory=list)

    # 礼物偏好
    favorite_gifts: List[str] = field(default_factory=list)
    liked_gifts: List[str] = field(default_factory=list)
    disliked_gifts: List[str] = field(default_factory=list)
    hated_gifts: List[str] = field(default_factory=list)

    # 故事背景
    backstory: str = ""               # 背景故事
    secrets: List[str] = field(default_factory=list)  # 隐藏秘密
    goals: List[str] = field(default_factory=list)    # 个人目标

    # 对话风格
    speech_style: str = ""            # 说话风格描述
    catchphrases: List[str] = field(default_factory=list)  # 口头禅

    # 资源
    sprites: Dict[str, str] = field(default_factory=dict)  # 立绘 {emotion: path}
    portrait: str = ""                # 头像
    voice_id: str = ""                # 语音ID
    theme_color: str = "#FFFFFF"      # 主题色

    # 特殊标记
    is_unlocked: bool = True          # 是否已解锁
    unlock_condition: Dict[str, Any] = field(default_factory=dict)
    is_dateable: bool = False         # 是否可攻略
    route_available: bool = False     # 是否有专属路线

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "npc_id": self.npc_id,
            "name": self.name,
            "nickname": self.nickname,
            "gender": self.gender,
            "age": self.age,
            "birthday": self.birthday,
            "blood_type": self.blood_type,
            "role": self.role.value,
            "class_name": self.class_name,
            "club": self.club,
            "personality": [p.value for p in self.personality],
            "traits": self.traits,
            "interests": self.interests,
            "favorite_topics": self.favorite_topics,
            "disliked_topics": self.disliked_topics,
            "weekday_schedule": [
                {
                    "time_start": s.time_start,
                    "time_end": s.time_end,
                    "location": s.location,
                    "activity": s.activity,
                    "interruptible": s.interruptible,
                    "probability": s.probability
                }
                for s in self.weekday_schedule
            ],
            "weekend_schedule": [
                {
                    "time_start": s.time_start,
                    "time_end": s.time_end,
                    "location": s.location,
                    "activity": s.activity,
                    "interruptible": s.interruptible,
                    "probability": s.probability
                }
                for s in self.weekend_schedule
            ],
            "favorite_gifts": self.favorite_gifts,
            "liked_gifts": self.liked_gifts,
            "disliked_gifts": self.disliked_gifts,
            "hated_gifts": self.hated_gifts,
            "backstory": self.backstory,
            "secrets": self.secrets,
            "goals": self.goals,
            "speech_style": self.speech_style,
            "catchphrases": self.catchphrases,
            "sprites": self.sprites,
            "portrait": self.portrait,
            "voice_id": self.voice_id,
            "theme_color": self.theme_color,
            "is_unlocked": self.is_unlocked,
            "unlock_condition": self.unlock_condition,
            "is_dateable": self.is_dateable,
            "route_available": self.route_available,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "NPCCharacter":
        """从字典创建"""
        npc = cls(
            npc_id=data.get("npc_id", ""),
            name=data.get("name", ""),
            nickname=data.get("nickname", ""),
            gender=data.get("gender", "female"),
            age=data.get("age", 17),
            birthday=data.get("birthday", ""),
            blood_type=data.get("blood_type", ""),
        )

        role_str = data.get("role", "classmate")
        try:
            npc.role = NPCRole(role_str)
        except:
            npc.role = NPCRole.CLASSMATE

        npc.class_name = data.get("class_name", "")
        npc.club = data.get("club", "")

        personality_list = data.get("personality", [])
        for p in personality_list:
            try:
                npc.personality.append(NPCPersonality(p))
            except:
                pass

        npc.traits = data.get("traits", [])
        npc.interests = data.get("interests", [])
        npc.favorite_topics = data.get("favorite_topics", [])
        npc.disliked_topics = data.get("disliked_topics", [])

        for sched in data.get("weekday_schedule", []):
            npc.weekday_schedule.append(NPCScheduleEntry(
                time_start=sched.get("time_start", ""),
                time_end=sched.get("time_end", ""),
                location=sched.get("location", ""),
                activity=sched.get("activity", ""),
                interruptible=sched.get("interruptible", True),
                probability=sched.get("probability", 1.0)
            ))

        for sched in data.get("weekend_schedule", []):
            npc.weekend_schedule.append(NPCScheduleEntry(
                time_start=sched.get("time_start", ""),
                time_end=sched.get("time_end", ""),
                location=sched.get("location", ""),
                activity=sched.get("activity", ""),
                interruptible=sched.get("interruptible", True),
                probability=sched.get("probability", 1.0)
            ))

        npc.favorite_gifts = data.get("favorite_gifts", [])
        npc.liked_gifts = data.get("liked_gifts", [])
        npc.disliked_gifts = data.get("disliked_gifts", [])
        npc.hated_gifts = data.get("hated_gifts", [])

        npc.backstory = data.get("backstory", "")
        npc.secrets = data.get("secrets", [])
        npc.goals = data.get("goals", [])

        npc.speech_style = data.get("speech_style", "")
        npc.catchphrases = data.get("catchphrases", [])

        npc.sprites = data.get("sprites", {})
        npc.portrait = data.get("portrait", "")
        npc.voice_id = data.get("voice_id", "")
        npc.theme_color = data.get("theme_color", "#FFFFFF")

        npc.is_unlocked = data.get("is_unlocked", True)
        npc.unlock_condition = data.get("unlock_condition", {})
        npc.is_dateable = data.get("is_dateable", False)
        npc.route_available = data.get("route_available", False)

        return npc


@dataclass
class NPCRelationData:
    """与NPC的关系数据"""
    npc_id: str
    affection: int = 0                # 好感度
    phase: NPCRelationPhase = NPCRelationPhase.UNKNOWN

    # 互动统计
    total_interactions: int = 0
    total_gifts: int = 0
    total_conversations: int = 0

    # 记忆
    memories: List[NPCMemory] = field(default_factory=list)

    # 发现的信息
    known_interests: List[str] = field(default_factory=list)
    known_secrets: List[str] = field(default_factory=list)

    # 特殊状态
    first_met_date: str = ""
    last_interaction_date: str = ""
    consecutive_days: int = 0         # 连续互动天数

    # 剧情进度
    story_progress: Dict[str, int] = field(default_factory=dict)
    unlocked_events: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict:
        return {
            "npc_id": self.npc_id,
            "affection": self.affection,
            "phase": self.phase.value,
            "total_interactions": self.total_interactions,
            "total_gifts": self.total_gifts,
            "total_conversations": self.total_conversations,
            "memories": [
                {
                    "memory_id": m.memory_id,
                    "timestamp": m.timestamp,
                    "event_type": m.event_type,
                    "description": m.description,
                    "emotional_impact": m.emotional_impact,
                    "keywords": m.keywords
                }
                for m in self.memories[-50:]  # 只保留最近50条
            ],
            "known_interests": self.known_interests,
            "known_secrets": self.known_secrets,
            "first_met_date": self.first_met_date,
            "last_interaction_date": self.last_interaction_date,
            "consecutive_days": self.consecutive_days,
            "story_progress": self.story_progress,
            "unlocked_events": list(self.unlocked_events)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "NPCRelationData":
        rel = cls(npc_id=data.get("npc_id", ""))
        rel.affection = data.get("affection", 0)

        try:
            rel.phase = NPCRelationPhase(data.get("phase", "unknown"))
        except:
            rel.phase = NPCRelationPhase.UNKNOWN

        rel.total_interactions = data.get("total_interactions", 0)
        rel.total_gifts = data.get("total_gifts", 0)
        rel.total_conversations = data.get("total_conversations", 0)

        for m in data.get("memories", []):
            rel.memories.append(NPCMemory(
                memory_id=m.get("memory_id", ""),
                timestamp=m.get("timestamp", ""),
                event_type=m.get("event_type", ""),
                description=m.get("description", ""),
                emotional_impact=m.get("emotional_impact", 0),
                keywords=m.get("keywords", [])
            ))

        rel.known_interests = data.get("known_interests", [])
        rel.known_secrets = data.get("known_secrets", [])
        rel.first_met_date = data.get("first_met_date", "")
        rel.last_interaction_date = data.get("last_interaction_date", "")
        rel.consecutive_days = data.get("consecutive_days", 0)
        rel.story_progress = data.get("story_progress", {})
        rel.unlocked_events = set(data.get("unlocked_events", []))

        return rel


class NPCManager:
    """
    NPC管理器

    功能:
    1. 管理所有NPC角色定义
    2. 管理与NPC的关系数据
    3. 处理NPC日程和位置
    4. 生成NPC对话和反应
    """

    # 关系阶段阈值
    PHASE_THRESHOLDS = {
        NPCRelationPhase.UNKNOWN: 0,
        NPCRelationPhase.KNOWN: 1,
        NPCRelationPhase.ACQUAINTANCE: 21,
        NPCRelationPhase.CLASSMATE: 51,
        NPCRelationPhase.FRIENDLY: 101,
        NPCRelationPhase.GOOD_FRIEND: 201,
        NPCRelationPhase.BEST_FRIEND: 401,
        NPCRelationPhase.CONFIDANT: 701,
    }

    # 关系阶段名称
    PHASE_NAMES = {
        NPCRelationPhase.UNKNOWN: "陌生人",
        NPCRelationPhase.KNOWN: "认识",
        NPCRelationPhase.ACQUAINTANCE: "点头之交",
        NPCRelationPhase.CLASSMATE: "普通同学",
        NPCRelationPhase.FRIENDLY: "友好",
        NPCRelationPhase.GOOD_FRIEND: "好友",
        NPCRelationPhase.BEST_FRIEND: "挚友",
        NPCRelationPhase.CONFIDANT: "知心人",
    }

    def __init__(self, pet_system=None):
        self.pet_system = pet_system

        # NPC角色库
        self.npcs: Dict[str, NPCCharacter] = {}

        # 关系数据
        self.relations: Dict[str, NPCRelationData] = {}

        # 缓存
        self._location_cache: Dict[str, List[str]] = {}  # location -> [npc_ids]
        self._cache_time: datetime = None

        # 回调
        self.on_phase_change: Optional[callable] = None
        self.on_secret_discovered: Optional[callable] = None

        # 加载数据
        self._load_npc_definitions()
        self._load_relation_data()

        # 创建默认NPC
        if not self.npcs:
            self._create_default_npcs()

    def _load_npc_definitions(self):
        """加载NPC定义"""
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "npc_characters.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for npc_data in data:
                    npc = NPCCharacter.from_dict(npc_data)
                    self.npcs[npc.npc_id] = npc
                logger.info(f"加载了 {len(self.npcs)} 个NPC定义")
        except Exception as e:
            logger.warning(f"加载NPC定义失败: {e}")

    def _load_relation_data(self):
        """加载关系数据"""
        if not self.pet_system:
            return

        try:
            saved = getattr(self.pet_system.data, "npc_relation_data", {}) or {}
            for npc_id, rel_data in saved.items():
                self.relations[npc_id] = NPCRelationData.from_dict(rel_data)
        except Exception as e:
            logger.warning(f"加载关系数据失败: {e}")

    def _save_relation_data(self):
        """保存关系数据"""
        if not self.pet_system:
            return

        try:
            self.pet_system.data.npc_relation_data = {
                npc_id: rel.to_dict()
                for npc_id, rel in self.relations.items()
            }
            self.pet_system.save()
        except Exception as e:
            logger.warning(f"保存关系数据失败: {e}")

    def _create_default_npcs(self):
        """创建默认NPC角色"""
        default_npcs = [
            NPCCharacter(
                npc_id="xiaoxia",
                name="夏小晴",
                nickname="小夏",
                gender="female",
                age=17,
                birthday="07-15",
                blood_type="O",
                role=NPCRole.CLASSMATE,
                class_name="2年3班",
                club="文学社",
                personality=[NPCPersonality.CHEERFUL, NPCPersonality.FRIENDLY],
                traits=["开朗", "热心", "有点冒失"],
                interests=["阅读", "写作", "追剧"],
                favorite_topics=["小说", "动漫", "学校八卦"],
                disliked_topics=["数学", "早起"],
                weekday_schedule=[
                    NPCScheduleEntry("08:00", "12:00", "classroom", "上课"),
                    NPCScheduleEntry("12:00", "13:00", "cafeteria", "午餐"),
                    NPCScheduleEntry("13:00", "17:00", "classroom", "上课"),
                    NPCScheduleEntry("17:00", "18:30", "club_room", "社团活动"),
                ],
                weekend_schedule=[
                    NPCScheduleEntry("10:00", "12:00", "library", "看书"),
                    NPCScheduleEntry("14:00", "17:00", "cafe", "写作"),
                ],
                favorite_gifts=["小说", "文具", "奶茶"],
                liked_gifts=["零食", "发饰"],
                disliked_gifts=["教辅书"],
                backstory="文学社的活跃分子，梦想成为作家。性格开朗，喜欢帮助他人，但有时候太过热心反而帮倒忙。",
                secrets=["其实曾经在网上发表过小说，但因为差评删掉了"],
                goals=["写出一部大家喜欢的作品"],
                speech_style="活泼、直率，经常用网络用语",
                catchphrases=["诶嘿~", "这个梗我懂！", "绝绝子！"],
                theme_color="#FF9E9E",
                is_dateable=True,
                route_available=True,
            ),
            NPCCharacter(
                npc_id="xuechang",
                name="林墨言",
                nickname="学长",
                gender="male",
                age=18,
                birthday="03-21",
                blood_type="A",
                role=NPCRole.UPPERCLASSMAN,
                class_name="3年1班",
                club="文学社",
                personality=[NPCPersonality.CALM, NPCPersonality.SERIOUS, NPCPersonality.BOOKWORM],
                traits=["沉稳", "博学", "有点古板"],
                interests=["古典文学", "书法", "围棋"],
                favorite_topics=["文学", "历史", "哲学"],
                disliked_topics=["游戏", "八卦"],
                weekday_schedule=[
                    NPCScheduleEntry("07:30", "12:00", "classroom", "上课"),
                    NPCScheduleEntry("12:00", "12:30", "cafeteria", "午餐"),
                    NPCScheduleEntry("12:30", "13:00", "library", "自习"),
                    NPCScheduleEntry("13:00", "17:00", "classroom", "上课"),
                    NPCScheduleEntry("17:00", "19:00", "club_room", "社团活动"),
                ],
                weekend_schedule=[
                    NPCScheduleEntry("09:00", "12:00", "library", "学习"),
                    NPCScheduleEntry("14:00", "17:00", "bookstore", "选书"),
                ],
                favorite_gifts=["古籍", "好茶", "文房四宝"],
                liked_gifts=["书籍", "棋谱"],
                disliked_gifts=["零食", "漫画"],
                backstory="文学社现任社长，成绩优异，是老师眼中的模范生。表面严肃，但对真心热爱写作的人会给予帮助。",
                secrets=["小时候其实是个调皮鬼，被祖父的严厉教育改变了"],
                goals=["考上理想的大学中文系"],
                speech_style="文雅、正式，偶尔引经据典",
                catchphrases=["学海无涯...", "这个典故是...", "你的进步我看在眼里"],
                theme_color="#4A90D9",
                is_dateable=False,
                route_available=True,
            ),
            NPCCharacter(
                npc_id="meimei",
                name="陈诗雨",
                nickname="诗诗",
                gender="female",
                age=16,
                birthday="09-08",
                blood_type="AB",
                role=NPCRole.UNDERCLASSMAN,
                class_name="1年2班",
                club="文学社",
                personality=[NPCPersonality.INTROVERTED, NPCPersonality.DANDERE, NPCPersonality.ARTISTIC],
                traits=["安静", "敏感", "才华横溢"],
                interests=["诗歌", "绘画", "音乐"],
                favorite_topics=["艺术", "情感", "自然"],
                disliked_topics=["吵闹的话题", "运动"],
                weekday_schedule=[
                    NPCScheduleEntry("08:00", "12:00", "classroom", "上课"),
                    NPCScheduleEntry("12:00", "13:00", "rooftop", "独自午餐", probability=0.7),
                    NPCScheduleEntry("13:00", "17:00", "classroom", "上课"),
                    NPCScheduleEntry("17:00", "18:00", "art_room", "画画"),
                ],
                weekend_schedule=[
                    NPCScheduleEntry("10:00", "12:00", "park", "写生"),
                    NPCScheduleEntry("14:00", "16:00", "home", "在家创作"),
                ],
                favorite_gifts=["画具", "诗集", "花"],
                liked_gifts=["音乐盒", "手帐"],
                disliked_gifts=["运动器材"],
                backstory="文学社新成员，擅长写诗和绘画。不善言辞，但文字和画作充满感情。",
                secrets=["父母离异，和奶奶住在一起"],
                goals=["用作品传达无法说出口的心情"],
                speech_style="简短、诗意，说话声音很小",
                catchphrases=["嗯...", "这样啊...", "...谢谢"],
                theme_color="#E6D5FF",
                is_dateable=True,
                route_available=True,
            ),
            NPCCharacter(
                npc_id="teacher_wang",
                name="王静文",
                nickname="王老师",
                gender="female",
                age=32,
                birthday="11-03",
                role=NPCRole.TEACHER,
                class_name="语文组",
                club="文学社",
                personality=[NPCPersonality.CALM, NPCPersonality.FRIENDLY],
                traits=["温柔", "有耐心", "偶尔犀利"],
                interests=["现代文学", "旅行", "咖啡"],
                favorite_topics=["写作技巧", "文学作品", "人生感悟"],
                disliked_topics=["学生不交作业"],
                weekday_schedule=[
                    NPCScheduleEntry("07:30", "12:00", "classroom", "授课"),
                    NPCScheduleEntry("12:00", "13:00", "teacher_office", "午休"),
                    NPCScheduleEntry("13:00", "17:00", "classroom", "授课/备课"),
                    NPCScheduleEntry("17:00", "18:00", "club_room", "指导社团", probability=0.5),
                ],
                weekend_schedule=[],
                favorite_gifts=["好咖啡", "书籍"],
                liked_gifts=["花", "巧克力"],
                backstory="文学社的指导老师，曾经也是这个学校文学社的成员。温柔但在写作上要求严格。",
                secrets=["年轻时写的小说差点获奖"],
                goals=["培养出优秀的年轻作家"],
                speech_style="温和、鼓励性，点评时一针见血",
                catchphrases=["写作最重要的是真诚", "这里可以再打磨一下", "进步很大呢"],
                theme_color="#8B7355",
                is_dateable=False,
                route_available=False,
            ),
        ]

        for npc in default_npcs:
            self.npcs[npc.npc_id] = npc

        logger.info(f"创建了 {len(default_npcs)} 个默认NPC")

    # ============================================================
    # 关系管理
    # ============================================================

    def get_relation(self, npc_id: str) -> NPCRelationData:
        """获取与NPC的关系数据"""
        if npc_id not in self.relations:
            self.relations[npc_id] = NPCRelationData(npc_id=npc_id)
        return self.relations[npc_id]

    def add_affection(self, npc_id: str, amount: int, reason: str = "") -> Dict[str, Any]:
        """
        增加与NPC的好感度

        Returns:
            {
                "old_affection": int,
                "new_affection": int,
                "old_phase": str,
                "new_phase": str,
                "phase_changed": bool,
                "new_phase_name": str
            }
        """
        rel = self.get_relation(npc_id)
        old_affection = rel.affection
        old_phase = rel.phase

        rel.affection = max(0, rel.affection + amount)
        rel.total_interactions += 1
        rel.last_interaction_date = datetime.now().strftime("%Y-%m-%d")

        # 更新关系阶段
        new_phase = self._calculate_phase(rel.affection)
        phase_changed = new_phase != old_phase
        rel.phase = new_phase

        # 添加记忆
        if amount != 0:
            memory = NPCMemory(
                memory_id=f"affection_{datetime.now().timestamp()}",
                timestamp=datetime.now().isoformat(),
                event_type="affection_change",
                description=reason or f"好感度变化 {'+' if amount > 0 else ''}{amount}",
                emotional_impact=min(10, max(-10, amount // 2)),
                keywords=[]
            )
            rel.memories.append(memory)

        self._save_relation_data()

        # 触发阶段变化回调
        if phase_changed and self.on_phase_change:
            self.on_phase_change(npc_id, old_phase, new_phase)

        return {
            "old_affection": old_affection,
            "new_affection": rel.affection,
            "old_phase": old_phase.value,
            "new_phase": new_phase.value,
            "phase_changed": phase_changed,
            "new_phase_name": self.PHASE_NAMES.get(new_phase, "")
        }

    def _calculate_phase(self, affection: int) -> NPCRelationPhase:
        """计算关系阶段"""
        current_phase = NPCRelationPhase.UNKNOWN

        for phase, threshold in sorted(self.PHASE_THRESHOLDS.items(),
                                       key=lambda x: x[1], reverse=True):
            if affection >= threshold:
                current_phase = phase
                break

        return current_phase

    def meet_npc(self, npc_id: str) -> bool:
        """第一次遇见NPC"""
        rel = self.get_relation(npc_id)

        if rel.first_met_date:
            return False  # 已经见过

        rel.first_met_date = datetime.now().strftime("%Y-%m-%d")
        rel.affection = 1  # 初始好感
        rel.phase = NPCRelationPhase.KNOWN

        # 添加记忆
        npc = self.npcs.get(npc_id)
        npc_name = npc.name if npc else npc_id

        memory = NPCMemory(
            memory_id=f"first_meet_{npc_id}",
            timestamp=datetime.now().isoformat(),
            event_type="first_meet",
            description=f"第一次认识了{npc_name}",
            emotional_impact=3,
            keywords=["初遇", "认识"]
        )
        rel.memories.append(memory)

        self._save_relation_data()
        return True

    def discover_interest(self, npc_id: str, interest: str) -> bool:
        """发现NPC的兴趣"""
        rel = self.get_relation(npc_id)

        if interest in rel.known_interests:
            return False

        rel.known_interests.append(interest)
        self._save_relation_data()
        return True

    def discover_secret(self, npc_id: str, secret_index: int) -> Optional[str]:
        """发现NPC的秘密"""
        npc = self.npcs.get(npc_id)
        if not npc or secret_index >= len(npc.secrets):
            return None

        rel = self.get_relation(npc_id)
        secret = npc.secrets[secret_index]

        if secret in rel.known_secrets:
            return None

        rel.known_secrets.append(secret)

        # 添加记忆
        memory = NPCMemory(
            memory_id=f"secret_{npc_id}_{secret_index}",
            timestamp=datetime.now().isoformat(),
            event_type="secret_discovered",
            description=f"发现了关于{npc.name}的秘密",
            emotional_impact=5,
            keywords=["秘密", "发现"]
        )
        rel.memories.append(memory)

        self._save_relation_data()

        if self.on_secret_discovered:
            self.on_secret_discovered(npc_id, secret)

        return secret

    # ============================================================
    # 礼物系统
    # ============================================================

    def give_gift(self, npc_id: str, gift_id: str) -> Dict[str, Any]:
        """
        送礼物给NPC

        Returns:
            {
                "reaction": str,
                "affection_change": int,
                "response": str,
                "is_favorite": bool
            }
        """
        npc = self.npcs.get(npc_id)
        if not npc:
            return {"error": "NPC不存在"}

        rel = self.get_relation(npc_id)
        rel.total_gifts += 1

        # 判断礼物反应
        if gift_id in npc.favorite_gifts:
            reaction = GiftReaction.LOVE
            affection_change = 15
            response = self._generate_gift_response(npc, "love")
        elif gift_id in npc.liked_gifts:
            reaction = GiftReaction.LIKE
            affection_change = 8
            response = self._generate_gift_response(npc, "like")
        elif gift_id in npc.hated_gifts:
            reaction = GiftReaction.HATE
            affection_change = -5
            response = self._generate_gift_response(npc, "hate")
        elif gift_id in npc.disliked_gifts:
            reaction = GiftReaction.DISLIKE
            affection_change = 0
            response = self._generate_gift_response(npc, "dislike")
        else:
            reaction = GiftReaction.NEUTRAL
            affection_change = 3
            response = self._generate_gift_response(npc, "neutral")

        # 应用好感度变化
        result = self.add_affection(npc_id, affection_change, f"送礼物: {gift_id}")

        return {
            "reaction": reaction.value,
            "affection_change": affection_change,
            "response": response,
            "is_favorite": reaction == GiftReaction.LOVE,
            "phase_changed": result.get("phase_changed", False),
            "new_phase_name": result.get("new_phase_name", "")
        }

    def _generate_gift_response(self, npc: NPCCharacter, reaction_type: str) -> str:
        """生成礼物回应"""
        responses = {
            "love": [
                f"这是...给我的？太开心了！谢谢你！",
                f"哇！我超喜欢这个！你怎么知道的？",
                f"这正是我想要的！{npc.name}好感动！"
            ],
            "like": [
                f"谢谢你！我很喜欢~",
                f"这个不错呢，谢谢~",
                f"给我的？嘿嘿，谢谢啦~"
            ],
            "neutral": [
                f"嗯...谢谢？",
                f"这个...还行吧，谢谢。",
                f"收到了，谢谢你的心意。"
            ],
            "dislike": [
                f"这个...我不太需要呢...",
                f"唔...谢谢，不过...",
                f"额...心意我收下了。"
            ],
            "hate": [
                f"你是认真的吗...？",
                f"这个我真的不行...",
                f"你是不是对我有什么误解..."
            ]
        }

        templates = responses.get(reaction_type, responses["neutral"])
        return random.choice(templates)

    # ============================================================
    # 日程与位置
    # ============================================================

    def get_npc_location(self, npc_id: str, time: datetime = None) -> Optional[str]:
        """获取NPC当前位置"""
        npc = self.npcs.get(npc_id)
        if not npc:
            return None

        if time is None:
            time = datetime.now()

        time_str = time.strftime("%H:%M")
        is_weekend = time.weekday() >= 5

        schedule = npc.weekend_schedule if is_weekend else npc.weekday_schedule

        for entry in schedule:
            if entry.time_start <= time_str <= entry.time_end:
                # 检查概率
                if random.random() <= entry.probability:
                    return entry.location

        return None

    def get_npcs_at_location(self, location: str, time: datetime = None) -> List[str]:
        """获取某个地点的所有NPC"""
        if time is None:
            time = datetime.now()

        npcs_here = []

        for npc_id, npc in self.npcs.items():
            if not npc.is_unlocked:
                continue

            loc = self.get_npc_location(npc_id, time)
            if loc == location:
                npcs_here.append(npc_id)

        return npcs_here

    def get_npc_activity(self, npc_id: str, time: datetime = None) -> Optional[str]:
        """获取NPC当前活动"""
        npc = self.npcs.get(npc_id)
        if not npc:
            return None

        if time is None:
            time = datetime.now()

        time_str = time.strftime("%H:%M")
        is_weekend = time.weekday() >= 5

        schedule = npc.weekend_schedule if is_weekend else npc.weekday_schedule

        for entry in schedule:
            if entry.time_start <= time_str <= entry.time_end:
                return entry.activity

        return "空闲"

    # ============================================================
    # 对话生成
    # ============================================================

    def generate_greeting(self, npc_id: str) -> str:
        """生成NPC问候语"""
        npc = self.npcs.get(npc_id)
        rel = self.get_relation(npc_id)

        if not npc:
            return "......"

        phase = rel.phase

        greetings = {
            NPCRelationPhase.UNKNOWN: [
                "...你是谁？",
                "（没有注意到你）",
            ],
            NPCRelationPhase.KNOWN: [
                "嗯？是你啊。",
                "你好。",
            ],
            NPCRelationPhase.ACQUAINTANCE: [
                "哦，是你。",
                "你好呀。",
            ],
            NPCRelationPhase.CLASSMATE: [
                "嘿，今天也在呢。",
                "你好~",
            ],
            NPCRelationPhase.FRIENDLY: [
                f"是{self._get_player_nickname()}！今天过得怎么样？",
                "又见面啦~",
            ],
            NPCRelationPhase.GOOD_FRIEND: [
                f"哇，{self._get_player_nickname()}来了！",
                "你来了！我正想找你呢。",
            ],
            NPCRelationPhase.BEST_FRIEND: [
                f"{self._get_player_nickname()}！等你好久了~",
                "你终于来了！快过来快过来！",
            ],
            NPCRelationPhase.CONFIDANT: [
                f"看到你就开心~",
                "你来了...太好了。",
            ],
        }

        templates = greetings.get(phase, greetings[NPCRelationPhase.KNOWN])
        base_greeting = random.choice(templates)

        # 添加口头禅
        if npc.catchphrases and random.random() < 0.3:
            base_greeting = f"{random.choice(npc.catchphrases)} {base_greeting}"

        return base_greeting

    def _get_player_nickname(self) -> str:
        """获取玩家称呼"""
        return "你"  # 可以从pet_system获取自定义称呼

    def generate_topic_response(self, npc_id: str, topic: str) -> Tuple[str, int]:
        """
        生成NPC对话题的反应

        Returns:
            (response_text, affection_change)
        """
        npc = self.npcs.get(npc_id)
        if not npc:
            return ("......", 0)

        # 检查话题偏好
        if topic in npc.favorite_topics:
            responses = [
                f"你也喜欢{topic}吗？！太棒了！",
                f"说到{topic}，我可有很多想聊的！",
                f"哇，{topic}！这是我最喜欢的话题！",
            ]
            return (random.choice(responses), 5)

        elif topic in npc.disliked_topics:
            responses = [
                f"{topic}啊...我不太感兴趣呢...",
                f"这个话题...能换一个吗？",
                f"唔...{topic}不太是我的菜...",
            ]
            return (random.choice(responses), -1)

        else:
            responses = [
                f"{topic}？嗯...还行吧。",
                f"这样啊，说说看？",
                f"关于{topic}...你想聊什么？",
            ]
            return (random.choice(responses), 1)

    # ============================================================
    # 查询接口
    # ============================================================

    def get_npc(self, npc_id: str) -> Optional[NPCCharacter]:
        """获取NPC角色"""
        return self.npcs.get(npc_id)

    def get_all_npcs(self) -> List[NPCCharacter]:
        """获取所有NPC"""
        return list(self.npcs.values())

    def get_unlocked_npcs(self) -> List[NPCCharacter]:
        """获取已解锁的NPC"""
        return [npc for npc in self.npcs.values() if npc.is_unlocked]

    def get_npcs_by_club(self, club: str) -> List[NPCCharacter]:
        """按社团获取NPC"""
        return [npc for npc in self.npcs.values() if npc.club == club and npc.is_unlocked]

    def get_npcs_by_role(self, role: NPCRole) -> List[NPCCharacter]:
        """按角色类型获取NPC"""
        return [npc for npc in self.npcs.values() if npc.role == role and npc.is_unlocked]

    def get_npc_summary(self, npc_id: str) -> Dict[str, Any]:
        """获取NPC摘要信息"""
        npc = self.npcs.get(npc_id)
        rel = self.get_relation(npc_id)

        if not npc:
            return {}

        return {
            "npc_id": npc_id,
            "name": npc.name,
            "nickname": npc.nickname,
            "role": npc.role.value,
            "club": npc.club,
            "affection": rel.affection,
            "phase": rel.phase.value,
            "phase_name": self.PHASE_NAMES.get(rel.phase, ""),
            "total_interactions": rel.total_interactions,
            "known_interests": rel.known_interests,
            "known_secrets_count": len(rel.known_secrets),
            "total_secrets": len(npc.secrets),
            "is_dateable": npc.is_dateable,
            "portrait": npc.portrait,
            "theme_color": npc.theme_color,
        }

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """获取所有NPC摘要"""
        return [
            self.get_npc_summary(npc_id)
            for npc_id in self.npcs.keys()
            if self.npcs[npc_id].is_unlocked
        ]

    def is_birthday(self, npc_id: str) -> bool:
        """检查今天是否是NPC生日"""
        npc = self.npcs.get(npc_id)
        if not npc or not npc.birthday:
            return False

        today = datetime.now().strftime("%m-%d")
        return npc.birthday == today

    def get_birthday_npcs(self) -> List[str]:
        """获取今天过生日的NPC"""
        return [
            npc_id for npc_id, npc in self.npcs.items()
            if self.is_birthday(npc_id)
        ]


# 便捷函数
def create_npc_system(pet_system=None) -> NPCManager:
    """创建NPC系统"""
    return NPCManager(pet_system)
