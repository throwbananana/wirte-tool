"""
悬浮助手 - 校园场景系统 (Campus Locations System)
场景定义、探索、事件触发
"""
import random
import json
from datetime import datetime, time
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LocationType(Enum):
    """场景类型"""
    CLASSROOM = "classroom"           # 教室
    CORRIDOR = "corridor"             # 走廊
    CAFETERIA = "cafeteria"           # 食堂
    LIBRARY = "library"               # 图书馆
    CLUB_ROOM = "club_room"           # 社团教室
    SPORTS = "sports"                 # 运动场所
    OUTDOOR = "outdoor"               # 户外
    SPECIAL = "special"               # 特殊场所
    SECRET = "secret"                 # 隐藏场所


# Backward-compatible aliases for older imports.
LocationCategory = LocationType


class LocationStatus(Enum):
    """场景状态"""
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


class LocationAtmosphere(Enum):
    """场景氛围"""
    PEACEFUL = "peaceful"             # 宁静
    LIVELY = "lively"                 # 热闹
    ROMANTIC = "romantic"             # 浪漫
    MYSTERIOUS = "mysterious"         # 神秘
    EXCITING = "exciting"             # 激动
    MELANCHOLIC = "melancholic"       # 忧郁
    COZY = "cozy"                     # 温馨


class TimeSlot(Enum):
    """时间段"""
    EARLY_MORNING = "early_morning"   # 清晨 06:00-07:30
    MORNING = "morning"               # 上午 07:30-12:00
    NOON = "noon"                     # 中午 12:00-13:30
    AFTERNOON = "afternoon"           # 下午 13:30-17:00
    EVENING = "evening"               # 傍晚 17:00-19:00
    NIGHT = "night"                   # 夜晚 19:00-22:00
    LATE_NIGHT = "late_night"         # 深夜 22:00-06:00


@dataclass
class LocationEvent:
    """场景事件定义"""
    event_id: str
    name: str
    description: str
    probability: float = 0.3          # 触发概率
    time_slots: List[TimeSlot] = field(default_factory=list)  # 可触发时段
    weekdays_only: bool = False       # 仅工作日
    weekend_only: bool = False        # 仅周末
    required_npcs: List[str] = field(default_factory=list)    # 需要的NPC
    excluded_npcs: List[str] = field(default_factory=list)    # 排除的NPC
    min_affection: Dict[str, int] = field(default_factory=dict)  # NPC好感度要求
    unlock_condition: Dict[str, Any] = field(default_factory=dict)  # 解锁条件
    one_time: bool = False            # 是否一次性事件
    cooldown_hours: float = 0         # 冷却时间


@dataclass
class LocationConnection:
    """场景连接"""
    target_location: str              # 目标场景ID
    travel_time: int = 1              # 移动耗时（分钟）
    description: str = ""             # 路线描述
    unlock_condition: Dict = field(default_factory=dict)  # 解锁条件


@dataclass
class CampusLocation:
    """校园场景定义"""
    location_id: str
    name: str
    short_name: str = ""              # 简称
    description: str = ""
    location_type: LocationType = LocationType.CLASSROOM

    # 开放时间
    open_time: str = "00:00"          # 开放时间
    close_time: str = "23:59"         # 关闭时间
    open_weekdays: bool = True        # 工作日开放
    open_weekends: bool = True        # 周末开放

    # 氛围与特点
    atmosphere: LocationAtmosphere = LocationAtmosphere.PEACEFUL
    tags: List[str] = field(default_factory=list)  # 标签

    # NPC相关
    typical_npcs: List[str] = field(default_factory=list)  # 常见NPC
    max_npcs: int = 5                 # 最大NPC数量

    # 事件
    event_pool: List[str] = field(default_factory=list)  # 可触发事件ID池
    special_events: List[LocationEvent] = field(default_factory=list)  # 特殊事件

    # 连接
    connections: List[LocationConnection] = field(default_factory=list)

    # 解锁
    is_unlocked: bool = True
    unlock_condition: Dict[str, Any] = field(default_factory=dict)
    unlock_hint: str = ""             # 解锁提示

    # 资源
    background_images: Dict[str, str] = field(default_factory=dict)  # 不同时段背景
    ambient_sound: str = ""           # 环境音效
    bgm: str = ""                     # 背景音乐

    # 统计
    visit_count: int = 0
    first_visit_date: str = ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "location_id": self.location_id,
            "name": self.name,
            "short_name": self.short_name,
            "description": self.description,
            "location_type": self.location_type.value,
            "open_time": self.open_time,
            "close_time": self.close_time,
            "open_weekdays": self.open_weekdays,
            "open_weekends": self.open_weekends,
            "atmosphere": self.atmosphere.value,
            "tags": self.tags,
            "typical_npcs": self.typical_npcs,
            "max_npcs": self.max_npcs,
            "event_pool": self.event_pool,
            "special_events": [
                {
                    "event_id": e.event_id,
                    "name": e.name,
                    "description": e.description,
                    "probability": e.probability,
                    "time_slots": [t.value for t in e.time_slots],
                    "weekdays_only": e.weekdays_only,
                    "weekend_only": e.weekend_only,
                    "required_npcs": e.required_npcs,
                    "excluded_npcs": e.excluded_npcs,
                    "min_affection": e.min_affection,
                    "unlock_condition": e.unlock_condition,
                    "one_time": e.one_time,
                    "cooldown_hours": e.cooldown_hours,
                }
                for e in self.special_events
            ],
            "connections": [
                {
                    "target_location": c.target_location,
                    "travel_time": c.travel_time,
                    "description": c.description,
                    "unlock_condition": c.unlock_condition,
                }
                for c in self.connections
            ],
            "is_unlocked": self.is_unlocked,
            "unlock_condition": self.unlock_condition,
            "unlock_hint": self.unlock_hint,
            "background_images": self.background_images,
            "ambient_sound": self.ambient_sound,
            "bgm": self.bgm,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CampusLocation":
        """从字典创建"""
        loc = cls(
            location_id=data.get("location_id", ""),
            name=data.get("name", ""),
            short_name=data.get("short_name", ""),
            description=data.get("description", ""),
        )

        try:
            loc.location_type = LocationType(data.get("location_type", "classroom"))
        except:
            loc.location_type = LocationType.CLASSROOM

        loc.open_time = data.get("open_time", "00:00")
        loc.close_time = data.get("close_time", "23:59")
        loc.open_weekdays = data.get("open_weekdays", True)
        loc.open_weekends = data.get("open_weekends", True)

        try:
            loc.atmosphere = LocationAtmosphere(data.get("atmosphere", "peaceful"))
        except:
            loc.atmosphere = LocationAtmosphere.PEACEFUL

        loc.tags = data.get("tags", [])
        loc.typical_npcs = data.get("typical_npcs", [])
        loc.max_npcs = data.get("max_npcs", 5)
        loc.event_pool = data.get("event_pool", [])

        for ev_data in data.get("special_events", []):
            time_slots = []
            for ts in ev_data.get("time_slots", []):
                try:
                    time_slots.append(TimeSlot(ts))
                except:
                    pass

            loc.special_events.append(LocationEvent(
                event_id=ev_data.get("event_id", ""),
                name=ev_data.get("name", ""),
                description=ev_data.get("description", ""),
                probability=ev_data.get("probability", 0.3),
                time_slots=time_slots,
                weekdays_only=ev_data.get("weekdays_only", False),
                weekend_only=ev_data.get("weekend_only", False),
                required_npcs=ev_data.get("required_npcs", []),
                excluded_npcs=ev_data.get("excluded_npcs", []),
                min_affection=ev_data.get("min_affection", {}),
                unlock_condition=ev_data.get("unlock_condition", {}),
                one_time=ev_data.get("one_time", False),
                cooldown_hours=ev_data.get("cooldown_hours", 0),
            ))

        for conn_data in data.get("connections", []):
            loc.connections.append(LocationConnection(
                target_location=conn_data.get("target_location", ""),
                travel_time=conn_data.get("travel_time", 1),
                description=conn_data.get("description", ""),
                unlock_condition=conn_data.get("unlock_condition", {}),
            ))

        loc.is_unlocked = data.get("is_unlocked", True)
        loc.unlock_condition = data.get("unlock_condition", {})
        loc.unlock_hint = data.get("unlock_hint", "")
        loc.background_images = data.get("background_images", {})
        loc.ambient_sound = data.get("ambient_sound", "")
        loc.bgm = data.get("bgm", "")

        return loc


class CampusLocationManager:
    """
    校园场景管理器

    功能:
    1. 管理所有场景定义
    2. 处理场景探索
    3. 触发场景事件
    4. 管理场景解锁
    """

    def __init__(self, pet_system=None, npc_manager=None):
        self.pet_system = pet_system
        self.npc_manager = npc_manager

        # 场景库
        self.locations: Dict[str, CampusLocation] = {}

        # 当前状态
        self.current_location: Optional[str] = None
        self.previous_location: Optional[str] = None

        # 探索记录
        self.visit_history: List[Dict] = []
        self.triggered_events: Set[str] = set()
        self.event_cooldowns: Dict[str, datetime] = {}

        # 回调
        self.on_location_change: Optional[callable] = None
        self.on_event_trigger: Optional[callable] = None
        self.on_location_unlock: Optional[callable] = None

        # 加载数据
        self._load_location_definitions()
        self._load_state()

        # 创建默认场景
        if not self.locations:
            self._create_default_locations()

    def _load_location_definitions(self):
        """加载场景定义"""
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "campus_locations.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for loc_data in data:
                    loc = CampusLocation.from_dict(loc_data)
                    self.locations[loc.location_id] = loc
                logger.info(f"加载了 {len(self.locations)} 个场景定义")
        except Exception as e:
            logger.warning(f"加载场景定义失败: {e}")

    def _load_state(self):
        """加载状态"""
        if not self.pet_system:
            return

        try:
            state = getattr(self.pet_system.data, "campus_state", {}) or {}
            self.current_location = state.get("current_location")
            self.triggered_events = set(state.get("triggered_events", []))

            for loc_id, visits in state.get("location_visits", {}).items():
                if loc_id in self.locations:
                    self.locations[loc_id].visit_count = visits.get("count", 0)
                    self.locations[loc_id].first_visit_date = visits.get("first_visit", "")

            for loc_id in state.get("unlocked_locations", []):
                if loc_id in self.locations:
                    self.locations[loc_id].is_unlocked = True

        except Exception as e:
            logger.warning(f"加载场景状态失败: {e}")

    def _save_state(self):
        """保存状态"""
        if not self.pet_system:
            return

        try:
            state = {
                "current_location": self.current_location,
                "triggered_events": list(self.triggered_events),
                "location_visits": {
                    loc_id: {
                        "count": loc.visit_count,
                        "first_visit": loc.first_visit_date
                    }
                    for loc_id, loc in self.locations.items()
                    if loc.visit_count > 0
                },
                "unlocked_locations": [
                    loc_id for loc_id, loc in self.locations.items()
                    if loc.is_unlocked
                ]
            }
            self.pet_system.data.campus_state = state
            self.pet_system.save()
        except Exception as e:
            logger.warning(f"保存场景状态失败: {e}")

    def _create_default_locations(self):
        """创建默认场景"""
        default_locations = [
            CampusLocation(
                location_id="classroom",
                name="教室",
                short_name="教室",
                description="2年3班的教室，窗边的位置阳光充足。黑板上还留着上节课的板书，课桌整齐排列。",
                location_type=LocationType.CLASSROOM,
                open_time="07:00",
                close_time="18:00",
                atmosphere=LocationAtmosphere.PEACEFUL,
                tags=["学习", "日常", "同学"],
                typical_npcs=["xiaoxia"],
                event_pool=["classroom_chat", "classroom_study", "classroom_nap"],
                special_events=[
                    LocationEvent(
                        event_id="classroom_love_letter",
                        name="神秘情书",
                        description="课桌里发现了一封没有署名的信...",
                        probability=0.05,
                        time_slots=[TimeSlot.MORNING],
                        one_time=True
                    ),
                ],
                connections=[
                    LocationConnection("corridor", 1, "走出教室"),
                    LocationConnection("cafeteria", 5, "去食堂"),
                ],
                background_images={
                    "morning": "classroom_morning.png",
                    "afternoon": "classroom_afternoon.png",
                    "evening": "classroom_evening.png",
                },
            ),
            CampusLocation(
                location_id="corridor",
                name="走廊",
                short_name="走廊",
                description="连接各个教室的走廊，窗外能看到操场。课间总是很热闹。",
                location_type=LocationType.CORRIDOR,
                atmosphere=LocationAtmosphere.LIVELY,
                tags=["过道", "偶遇", "课间"],
                event_pool=["corridor_encounter", "corridor_rush"],
                connections=[
                    LocationConnection("classroom", 1, "回教室"),
                    LocationConnection("library", 3, "去图书馆"),
                    LocationConnection("rooftop", 2, "上天台"),
                    LocationConnection("club_room", 2, "去社团教室"),
                ],
            ),
            CampusLocation(
                location_id="cafeteria",
                name="食堂",
                short_name="食堂",
                description="学校食堂，到了饭点就人满为患。窗边的位置比较安静，适合聊天。",
                location_type=LocationType.CAFETERIA,
                open_time="06:30",
                close_time="20:00",
                atmosphere=LocationAtmosphere.LIVELY,
                tags=["吃饭", "聊天", "热闹"],
                typical_npcs=["xiaoxia"],
                max_npcs=10,
                event_pool=["cafeteria_lunch", "cafeteria_share", "cafeteria_queue"],
                special_events=[
                    LocationEvent(
                        event_id="cafeteria_special_menu",
                        name="今日特餐",
                        description="今天有限定菜单！",
                        probability=0.1,
                        time_slots=[TimeSlot.NOON],
                    ),
                ],
                connections=[
                    LocationConnection("classroom", 5, "回教室"),
                    LocationConnection("corridor", 3, "去走廊"),
                ],
                background_images={
                    "noon": "cafeteria_busy.png",
                    "evening": "cafeteria_quiet.png",
                },
            ),
            CampusLocation(
                location_id="library",
                name="图书馆",
                short_name="图书馆",
                description="藏书丰富的图书馆，需要保持安静。角落的自习区是写作的好地方。",
                location_type=LocationType.LIBRARY,
                open_time="08:00",
                close_time="21:00",
                open_weekends=True,
                atmosphere=LocationAtmosphere.PEACEFUL,
                tags=["安静", "学习", "阅读", "写作"],
                typical_npcs=["xuechang", "meimei"],
                event_pool=["library_study", "library_find_book", "library_whisper"],
                special_events=[
                    LocationEvent(
                        event_id="library_old_book",
                        name="泛黄的旧书",
                        description="在书架深处发现了一本似乎很久没人翻过的书...",
                        probability=0.08,
                        one_time=True
                    ),
                    LocationEvent(
                        event_id="library_secret_note",
                        name="书中便签",
                        description="翻开一本书，里面夹着一张手写的便签...",
                        probability=0.05,
                        min_affection={"xuechang": 100},
                    ),
                ],
                connections=[
                    LocationConnection("corridor", 3, "出去"),
                ],
                ambient_sound="library_ambient.mp3",
            ),
            CampusLocation(
                location_id="club_room",
                name="文学社教室",
                short_name="社团室",
                description="文学社的专属教室，墙上贴满了社刊和获奖作品。书架上有历届社员的作品集。",
                location_type=LocationType.CLUB_ROOM,
                open_time="12:00",
                close_time="19:00",
                atmosphere=LocationAtmosphere.COZY,
                tags=["社团", "写作", "文学", "创作"],
                typical_npcs=["xiaoxia", "xuechang", "meimei", "teacher_wang"],
                event_pool=["club_meeting", "club_critique", "club_chat"],
                special_events=[
                    LocationEvent(
                        event_id="club_anniversary",
                        name="社团纪念日",
                        description="今天是文学社成立纪念日！",
                        probability=0.02,
                        one_time=False,
                        cooldown_hours=720,  # 30天
                    ),
                    LocationEvent(
                        event_id="club_secret_archive",
                        name="秘密档案",
                        description="在储物柜深处发现了一个落满灰尘的文件夹...",
                        probability=0.03,
                        min_affection={"xuechang": 200},
                        one_time=True
                    ),
                ],
                connections=[
                    LocationConnection("corridor", 2, "出去"),
                ],
            ),
            CampusLocation(
                location_id="rooftop",
                name="天台",
                short_name="天台",
                description="学校的天台，可以俯瞰整个校园。傍晚的夕阳很美，是个适合思考的地方。",
                location_type=LocationType.OUTDOOR,
                open_time="12:00",
                close_time="18:00",
                open_weekdays=True,
                atmosphere=LocationAtmosphere.ROMANTIC,
                tags=["安静", "放空", "风景", "浪漫"],
                typical_npcs=["meimei"],
                max_npcs=3,
                event_pool=["rooftop_view", "rooftop_breeze", "rooftop_sunset"],
                special_events=[
                    LocationEvent(
                        event_id="rooftop_confession",
                        name="心声",
                        description="有人在天台等你...",
                        probability=0.02,
                        time_slots=[TimeSlot.EVENING],
                        min_affection={"meimei": 300},
                    ),
                    LocationEvent(
                        event_id="rooftop_stargazing",
                        name="看星星",
                        description="今晚的星空特别美...",
                        probability=0.15,
                        time_slots=[TimeSlot.NIGHT],
                        weekend_only=True,
                    ),
                ],
                connections=[
                    LocationConnection("corridor", 2, "下楼"),
                ],
                background_images={
                    "noon": "rooftop_day.png",
                    "evening": "rooftop_sunset.png",
                    "night": "rooftop_night.png",
                },
            ),
            CampusLocation(
                location_id="garden",
                name="花园",
                short_name="花园",
                description="学校后面的小花园，四季都有不同的花开放。长椅上适合阅读或发呆。",
                location_type=LocationType.OUTDOOR,
                atmosphere=LocationAtmosphere.PEACEFUL,
                tags=["花草", "安静", "自然", "放松"],
                event_pool=["garden_rest", "garden_flowers", "garden_bird"],
                connections=[
                    LocationConnection("corridor", 5, "回教学楼"),
                    LocationConnection("lake", 3, "去湖边"),
                ],
            ),
            CampusLocation(
                location_id="lake",
                name="湖边",
                short_name="湖边",
                description="校园里的小湖，湖边有几棵老柳树。很少有人来这里，非常安静。",
                location_type=LocationType.OUTDOOR,
                atmosphere=LocationAtmosphere.MELANCHOLIC,
                tags=["安静", "隐蔽", "自然", "思考"],
                typical_npcs=["meimei"],
                max_npcs=2,
                event_pool=["lake_reflection", "lake_fish", "lake_rain"],
                special_events=[
                    LocationEvent(
                        event_id="lake_secret_spot",
                        name="秘密角落",
                        description="发现了一个被柳枝遮蔽的角落...",
                        probability=0.1,
                        one_time=True,
                    ),
                ],
                connections=[
                    LocationConnection("garden", 3, "回花园"),
                ],
            ),
            CampusLocation(
                location_id="bookstore",
                name="校外书店",
                short_name="书店",
                description="学校附近的旧书店，店主是个和蔼的老人。经常能淘到绝版书籍。",
                location_type=LocationType.SPECIAL,
                open_time="10:00",
                close_time="20:00",
                open_weekdays=True,
                open_weekends=True,
                atmosphere=LocationAtmosphere.COZY,
                tags=["书籍", "淘宝", "安静"],
                typical_npcs=["xuechang"],
                event_pool=["bookstore_browse", "bookstore_find", "bookstore_chat"],
                special_events=[
                    LocationEvent(
                        event_id="bookstore_rare_find",
                        name="珍稀发现",
                        description="在角落发现了一本稀有的绝版书...",
                        probability=0.05,
                    ),
                ],
                is_unlocked=False,
                unlock_condition={"npc_affection": {"xuechang": 50}},
                unlock_hint="也许某位学长知道附近有好去处...",
                connections=[],
            ),
            CampusLocation(
                location_id="cafe",
                name="咖啡店",
                short_name="咖啡店",
                description="学校附近的小咖啡店，环境温馨，适合写作。店里的拿铁很好喝。",
                location_type=LocationType.SPECIAL,
                open_time="09:00",
                close_time="22:00",
                atmosphere=LocationAtmosphere.COZY,
                tags=["咖啡", "写作", "约会", "休闲"],
                typical_npcs=["xiaoxia"],
                event_pool=["cafe_write", "cafe_chat", "cafe_order"],
                is_unlocked=False,
                unlock_condition={"npc_affection": {"xiaoxia": 100}},
                unlock_hint="小夏好像知道一家不错的咖啡店...",
                connections=[],
            ),
            CampusLocation(
                location_id="secret_room",
                name="旧档案室",
                short_name="???",
                description="图书馆地下的旧档案室，据说封存着学校的历史资料。很少有人知道这里。",
                location_type=LocationType.SECRET,
                atmosphere=LocationAtmosphere.MYSTERIOUS,
                tags=["神秘", "历史", "秘密"],
                event_pool=["secret_explore", "secret_find"],
                special_events=[
                    LocationEvent(
                        event_id="secret_old_story",
                        name="尘封的故事",
                        description="发现了一份很久以前的文学社社刊...",
                        probability=0.2,
                        one_time=True,
                    ),
                ],
                is_unlocked=False,
                unlock_condition={
                    "event_completed": "library_old_book",
                    "npc_affection": {"xuechang": 300}
                },
                unlock_hint="图书馆里似乎藏着什么秘密...",
                connections=[
                    LocationConnection("library", 1, "离开"),
                ],
            ),
        ]

        for loc in default_locations:
            self.locations[loc.location_id] = loc

        # 设置初始位置
        self.current_location = "classroom"

        logger.info(f"创建了 {len(default_locations)} 个默认场景")

    # ============================================================
    # 场景导航
    # ============================================================

    def get_current_time_slot(self) -> TimeSlot:
        """获取当前时间段"""
        now = datetime.now()
        hour = now.hour

        if 6 <= hour < 7.5:
            return TimeSlot.EARLY_MORNING
        elif 7.5 <= hour < 12:
            return TimeSlot.MORNING
        elif 12 <= hour < 13.5:
            return TimeSlot.NOON
        elif 13.5 <= hour < 17:
            return TimeSlot.AFTERNOON
        elif 17 <= hour < 19:
            return TimeSlot.EVENING
        elif 19 <= hour < 22:
            return TimeSlot.NIGHT
        else:
            return TimeSlot.LATE_NIGHT

    def is_location_open(self, location_id: str) -> bool:
        """检查场景是否开放"""
        loc = self.locations.get(location_id)
        if not loc:
            return False

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        is_weekend = now.weekday() >= 5

        # 检查开放日期
        if is_weekend and not loc.open_weekends:
            return False
        if not is_weekend and not loc.open_weekdays:
            return False

        # 检查开放时间
        if loc.open_time <= current_time <= loc.close_time:
            return True

        return False

    def can_visit(self, location_id: str) -> Tuple[bool, str]:
        """
        检查是否可以访问场景

        Returns:
            (can_visit, reason)
        """
        loc = self.locations.get(location_id)
        if not loc:
            return False, "场景不存在"

        if not loc.is_unlocked:
            return False, loc.unlock_hint or "该场景尚未解锁"

        if not self.is_location_open(location_id):
            return False, f"该场景目前不开放（开放时间: {loc.open_time}-{loc.close_time}）"

        return True, ""

    def visit_location(self, location_id: str) -> Dict[str, Any]:
        """
        访问场景

        Returns:
            {
                "success": bool,
                "message": str,
                "location": CampusLocation,
                "npcs_present": List[str],
                "triggered_event": Optional[Dict]
            }
        """
        can_visit, reason = self.can_visit(location_id)
        if not can_visit:
            return {"success": False, "message": reason}

        loc = self.locations[location_id]

        # 更新位置
        self.previous_location = self.current_location
        self.current_location = location_id

        # 更新访问统计
        loc.visit_count += 1
        if not loc.first_visit_date:
            loc.first_visit_date = datetime.now().strftime("%Y-%m-%d")

        # 记录历史
        self.visit_history.append({
            "location_id": location_id,
            "timestamp": datetime.now().isoformat(),
            "from_location": self.previous_location
        })

        # 保持历史记录在合理范围
        if len(self.visit_history) > 100:
            self.visit_history = self.visit_history[-100:]

        # 获取当前在场的NPC
        npcs_present = self._get_npcs_at_location(location_id)

        # 尝试触发事件
        triggered_event = self._try_trigger_event(location_id, npcs_present)

        self._save_state()

        # 触发回调
        if self.on_location_change:
            self.on_location_change(self.previous_location, location_id)

        return {
            "success": True,
            "message": f"来到了{loc.name}",
            "location": loc,
            "npcs_present": npcs_present,
            "triggered_event": triggered_event,
            "description": self._generate_arrival_description(loc, npcs_present)
        }

    def _get_npcs_at_location(self, location_id: str) -> List[str]:
        """获取场景中的NPC"""
        if not self.npc_manager:
            return []

        loc = self.locations.get(location_id)
        if not loc:
            return []

        present_npcs = []

        # 检查哪些NPC在这个位置
        for npc_id in loc.typical_npcs:
            npc_location = self.npc_manager.get_npc_location(npc_id)
            if npc_location == location_id:
                present_npcs.append(npc_id)

        # 限制数量
        if len(present_npcs) > loc.max_npcs:
            present_npcs = random.sample(present_npcs, loc.max_npcs)

        return present_npcs

    def _generate_arrival_description(self, loc: CampusLocation, npcs: List[str]) -> str:
        """生成到达描述"""
        desc = loc.description

        if npcs and self.npc_manager:
            npc_names = []
            for npc_id in npcs:
                npc = self.npc_manager.get_npc(npc_id)
                if npc:
                    npc_names.append(npc.name)

            if len(npc_names) == 1:
                desc += f"\n\n{npc_names[0]}也在这里。"
            elif len(npc_names) > 1:
                desc += f"\n\n{', '.join(npc_names[:-1])}和{npc_names[-1]}也在这里。"

        return desc

    # ============================================================
    # 事件触发
    # ============================================================

    def _try_trigger_event(self, location_id: str, npcs_present: List[str]) -> Optional[Dict]:
        """尝试触发场景事件"""
        loc = self.locations.get(location_id)
        if not loc:
            return None

        current_slot = self.get_current_time_slot()
        is_weekend = datetime.now().weekday() >= 5

        # 候选事件
        candidates = []

        for event in loc.special_events:
            # 检查是否已触发（一次性事件）
            if event.one_time and event.event_id in self.triggered_events:
                continue

            # 检查冷却
            if event.event_id in self.event_cooldowns:
                cooldown_end = self.event_cooldowns[event.event_id]
                if datetime.now() < cooldown_end:
                    continue

            # 检查时间段
            if event.time_slots and current_slot not in event.time_slots:
                continue

            # 检查星期
            if event.weekdays_only and is_weekend:
                continue
            if event.weekend_only and not is_weekend:
                continue

            # 检查NPC要求
            if event.required_npcs:
                if not all(npc in npcs_present for npc in event.required_npcs):
                    continue

            if event.excluded_npcs:
                if any(npc in npcs_present for npc in event.excluded_npcs):
                    continue

            # 检查好感度要求
            if event.min_affection and self.npc_manager:
                affection_met = True
                for npc_id, min_aff in event.min_affection.items():
                    rel = self.npc_manager.get_relation(npc_id)
                    if rel.affection < min_aff:
                        affection_met = False
                        break
                if not affection_met:
                    continue

            # 检查解锁条件
            if event.unlock_condition:
                if not self._check_unlock_condition(event.unlock_condition):
                    continue

            # 添加到候选
            candidates.append(event)

        # 随机选择一个事件触发
        for event in candidates:
            if random.random() < event.probability:
                # 触发事件
                self.triggered_events.add(event.event_id)

                # 设置冷却
                if event.cooldown_hours > 0:
                    from datetime import timedelta
                    self.event_cooldowns[event.event_id] = datetime.now() + timedelta(hours=event.cooldown_hours)

                if self.on_event_trigger:
                    self.on_event_trigger(event)

                return {
                    "event_id": event.event_id,
                    "name": event.name,
                    "description": event.description,
                    "location": location_id,
                    "npcs": npcs_present
                }

        return None

    def _check_unlock_condition(self, condition: Dict) -> bool:
        """检查解锁条件"""
        # 检查事件完成
        if "event_completed" in condition:
            if condition["event_completed"] not in self.triggered_events:
                return False

        # 检查NPC好感度
        if "npc_affection" in condition and self.npc_manager:
            for npc_id, min_aff in condition["npc_affection"].items():
                rel = self.npc_manager.get_relation(npc_id)
                if rel.affection < min_aff:
                    return False

        return True

    # ============================================================
    # 场景解锁
    # ============================================================

    def check_unlock_progress(self) -> List[Dict]:
        """检查所有场景的解锁进度"""
        progress = []

        for loc_id, loc in self.locations.items():
            if loc.is_unlocked:
                continue

            prog = {
                "location_id": loc_id,
                "name": loc.name,
                "hint": loc.unlock_hint,
                "conditions": loc.unlock_condition,
                "progress": self._calculate_unlock_progress(loc.unlock_condition)
            }
            progress.append(prog)

        return progress

    def _calculate_unlock_progress(self, condition: Dict) -> Dict[str, float]:
        """计算解锁进度"""
        progress = {}

        if "event_completed" in condition:
            event_id = condition["event_completed"]
            progress["event"] = 1.0 if event_id in self.triggered_events else 0.0

        if "npc_affection" in condition and self.npc_manager:
            for npc_id, min_aff in condition["npc_affection"].items():
                rel = self.npc_manager.get_relation(npc_id)
                progress[f"affection_{npc_id}"] = min(1.0, rel.affection / min_aff)

        return progress

    def try_unlock_location(self, location_id: str) -> bool:
        """尝试解锁场景"""
        loc = self.locations.get(location_id)
        if not loc or loc.is_unlocked:
            return False

        if not loc.unlock_condition:
            loc.is_unlocked = True
            self._save_state()
            return True

        if self._check_unlock_condition(loc.unlock_condition):
            loc.is_unlocked = True
            self._save_state()

            if self.on_location_unlock:
                self.on_location_unlock(location_id)

            return True

        return False

    def check_all_unlocks(self) -> List[str]:
        """检查并解锁所有符合条件的场景"""
        newly_unlocked = []

        for loc_id, loc in self.locations.items():
            if loc.is_unlocked:
                continue

            if self.try_unlock_location(loc_id):
                newly_unlocked.append(loc_id)

        return newly_unlocked

    # ============================================================
    # 查询接口
    # ============================================================

    def get_location(self, location_id: str) -> Optional[CampusLocation]:
        """获取场景"""
        return self.locations.get(location_id)

    def get_all_locations(self) -> List[CampusLocation]:
        """获取所有场景"""
        return list(self.locations.values())

    def get_unlocked_locations(self) -> List[CampusLocation]:
        """获取已解锁场景"""
        return [loc for loc in self.locations.values() if loc.is_unlocked]

    def get_available_connections(self) -> List[Dict]:
        """获取当前可以去的地方"""
        if not self.current_location:
            return []

        loc = self.locations.get(self.current_location)
        if not loc:
            return []

        available = []
        for conn in loc.connections:
            target = self.locations.get(conn.target_location)
            if not target:
                continue

            can_visit, reason = self.can_visit(conn.target_location)
            available.append({
                "location_id": conn.target_location,
                "name": target.name,
                "description": conn.description,
                "travel_time": conn.travel_time,
                "can_visit": can_visit,
                "reason": reason if not can_visit else ""
            })

        return available

    def get_location_summary(self, location_id: str) -> Dict[str, Any]:
        """获取场景摘要"""
        loc = self.locations.get(location_id)
        if not loc:
            return {}

        return {
            "location_id": location_id,
            "name": loc.name,
            "short_name": loc.short_name,
            "description": loc.description,
            "type": loc.location_type.value,
            "atmosphere": loc.atmosphere.value,
            "is_open": self.is_location_open(location_id),
            "is_unlocked": loc.is_unlocked,
            "visit_count": loc.visit_count,
            "tags": loc.tags,
            "typical_npcs": loc.typical_npcs,
        }

    def get_visit_stats(self) -> Dict[str, Any]:
        """获取访问统计"""
        total_visits = sum(loc.visit_count for loc in self.locations.values())
        locations_visited = sum(1 for loc in self.locations.values() if loc.visit_count > 0)

        return {
            "total_visits": total_visits,
            "locations_visited": locations_visited,
            "total_locations": len(self.locations),
            "unlocked_locations": len(self.get_unlocked_locations()),
            "events_triggered": len(self.triggered_events),
            "current_location": self.current_location,
            "favorite_location": max(
                self.locations.items(),
                key=lambda x: x[1].visit_count,
                default=(None, None)
            )[0]
        }


# 便捷函数
def create_campus_system(pet_system=None, npc_manager=None) -> CampusLocationManager:
    """创建校园场景系统"""
    return CampusLocationManager(pet_system, npc_manager)


def create_location_manager(pet_system=None, npc_manager=None) -> CampusLocationManager:
    """兼容旧接口"""
    return create_campus_system(pet_system, npc_manager)
