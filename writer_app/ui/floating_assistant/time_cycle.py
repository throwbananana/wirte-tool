"""
悬浮助手 - 时间周期系统 (Time Cycle System)
管理游戏时间流逝、日程安排、特殊日期、天气系统
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
import logging
import math

logger = logging.getLogger(__name__)


class TimePeriod(Enum):
    """时间段"""
    EARLY_MORNING = "early_morning"     # 清晨 (6:00-8:00)
    MORNING = "morning"                 # 上午 (8:00-12:00)
    NOON = "noon"                       # 中午 (12:00-14:00)
    AFTERNOON = "afternoon"             # 下午 (14:00-17:00)
    EVENING = "evening"                 # 傍晚 (17:00-19:00)
    NIGHT = "night"                     # 晚上 (19:00-22:00)
    LATE_NIGHT = "late_night"           # 深夜 (22:00-6:00)


class DayOfWeek(Enum):
    """星期"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class Season(Enum):
    """季节"""
    SPRING = "spring"   # 春季 (3-5月)
    SUMMER = "summer"   # 夏季 (6-8月)
    AUTUMN = "autumn"   # 秋季 (9-11月)
    WINTER = "winter"   # 冬季 (12-2月)


class Weather(Enum):
    """天气"""
    SUNNY = "sunny"             # 晴天
    CLOUDY = "cloudy"           # 多云
    OVERCAST = "overcast"       # 阴天
    RAINY = "rainy"             # 雨天
    STORMY = "stormy"           # 暴风雨
    SNOWY = "snowy"             # 雪天
    FOGGY = "foggy"             # 雾天
    WINDY = "windy"             # 大风


class SpecialDateType(Enum):
    """特殊日期类型"""
    HOLIDAY = "holiday"                 # 节假日
    SCHOOL_EVENT = "school_event"       # 学校活动
    EXAM_PERIOD = "exam_period"         # 考试周
    CLUB_EVENT = "club_event"           # 社团活动
    PERSONAL = "personal"               # 个人事件
    STORY = "story"                     # 剧情事件


# 时间段显示配置
TIME_PERIOD_DISPLAY = {
    TimePeriod.EARLY_MORNING: {
        "name": "清晨", "icon": "🌅", "color": "#FFE082",
        "description": "天刚蒙蒙亮", "hours": (6, 8)
    },
    TimePeriod.MORNING: {
        "name": "上午", "icon": "🌤️", "color": "#FFF59D",
        "description": "阳光正好", "hours": (8, 12)
    },
    TimePeriod.NOON: {
        "name": "中午", "icon": "☀️", "color": "#FFD54F",
        "description": "午餐时间", "hours": (12, 14)
    },
    TimePeriod.AFTERNOON: {
        "name": "下午", "icon": "🌤️", "color": "#FFCA28",
        "description": "温暖的午后", "hours": (14, 17)
    },
    TimePeriod.EVENING: {
        "name": "傍晚", "icon": "🌇", "color": "#FFA726",
        "description": "夕阳西下", "hours": (17, 19)
    },
    TimePeriod.NIGHT: {
        "name": "晚上", "icon": "🌙", "color": "#7986CB",
        "description": "夜幕降临", "hours": (19, 22)
    },
    TimePeriod.LATE_NIGHT: {
        "name": "深夜", "icon": "🌃", "color": "#5C6BC0",
        "description": "万籁俱寂", "hours": (22, 6)
    },
}

# 星期显示
DAY_OF_WEEK_DISPLAY = {
    DayOfWeek.MONDAY: {"name": "周一", "short": "一", "is_weekend": False},
    DayOfWeek.TUESDAY: {"name": "周二", "short": "二", "is_weekend": False},
    DayOfWeek.WEDNESDAY: {"name": "周三", "short": "三", "is_weekend": False},
    DayOfWeek.THURSDAY: {"name": "周四", "short": "四", "is_weekend": False},
    DayOfWeek.FRIDAY: {"name": "周五", "short": "五", "is_weekend": False},
    DayOfWeek.SATURDAY: {"name": "周六", "short": "六", "is_weekend": True},
    DayOfWeek.SUNDAY: {"name": "周日", "short": "日", "is_weekend": True},
}

# 季节配置
SEASON_CONFIG = {
    Season.SPRING: {
        "name": "春季", "icon": "🌸", "color": "#E8F5E9",
        "months": [3, 4, 5],
        "weather_weights": {"sunny": 35, "cloudy": 25, "rainy": 30, "foggy": 10},
        "description": "万物复苏，樱花盛开"
    },
    Season.SUMMER: {
        "name": "夏季", "icon": "🌻", "color": "#FFF8E1",
        "months": [6, 7, 8],
        "weather_weights": {"sunny": 40, "cloudy": 20, "rainy": 25, "stormy": 15},
        "description": "炎炎夏日，蝉鸣阵阵"
    },
    Season.AUTUMN: {
        "name": "秋季", "icon": "🍂", "color": "#FFF3E0",
        "months": [9, 10, 11],
        "weather_weights": {"sunny": 45, "cloudy": 30, "windy": 15, "rainy": 10},
        "description": "金风送爽，落叶纷飞"
    },
    Season.WINTER: {
        "name": "冬季", "icon": "❄️", "color": "#E3F2FD",
        "months": [12, 1, 2],
        "weather_weights": {"sunny": 25, "cloudy": 30, "snowy": 25, "overcast": 20},
        "description": "银装素裹，寒风凛冽"
    },
}

# 天气显示
WEATHER_DISPLAY = {
    Weather.SUNNY: {"name": "晴", "icon": "☀️", "effect": "心情愉快"},
    Weather.CLOUDY: {"name": "多云", "icon": "⛅", "effect": "平静"},
    Weather.OVERCAST: {"name": "阴", "icon": "☁️", "effect": "略感沉闷"},
    Weather.RAINY: {"name": "雨", "icon": "🌧️", "effect": "适合待在室内"},
    Weather.STORMY: {"name": "暴风雨", "icon": "⛈️", "effect": "无法外出"},
    Weather.SNOWY: {"name": "雪", "icon": "🌨️", "effect": "浪漫的气氛"},
    Weather.FOGGY: {"name": "雾", "icon": "🌫️", "effect": "神秘感"},
    Weather.WINDY: {"name": "大风", "icon": "💨", "effect": "户外活动不便"},
}


@dataclass
class SpecialDate:
    """特殊日期定义"""
    date_id: str
    name: str
    date_type: SpecialDateType
    month: int
    day: int
    year: Optional[int] = None          # None表示每年重复
    description: str = ""

    # 影响
    school_closed: bool = False         # 学校是否放假
    affected_locations: List[str] = field(default_factory=list)  # 受影响的地点
    special_events: List[str] = field(default_factory=list)      # 触发的特殊事件
    npc_schedules: Dict[str, str] = field(default_factory=dict)  # NPC特殊日程

    # 显示
    icon: str = ""
    color: str = "#FF9800"

    def to_dict(self) -> Dict:
        return {
            "date_id": self.date_id,
            "name": self.name,
            "date_type": self.date_type.value,
            "month": self.month,
            "day": self.day,
            "year": self.year,
            "description": self.description,
            "school_closed": self.school_closed,
            "affected_locations": self.affected_locations,
            "special_events": self.special_events,
            "npc_schedules": self.npc_schedules,
            "icon": self.icon,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SpecialDate":
        return cls(
            date_id=data.get("date_id", ""),
            name=data.get("name", ""),
            date_type=SpecialDateType(data.get("date_type", "holiday")),
            month=data.get("month", 1),
            day=data.get("day", 1),
            year=data.get("year"),
            description=data.get("description", ""),
            school_closed=data.get("school_closed", False),
            affected_locations=data.get("affected_locations", []),
            special_events=data.get("special_events", []),
            npc_schedules=data.get("npc_schedules", {}),
            icon=data.get("icon", ""),
            color=data.get("color", "#FF9800")
        )


@dataclass
class ScheduleEntry:
    """日程条目"""
    time_period: TimePeriod
    location_id: str
    activity: str
    priority: int = 0                   # 优先级（越高越优先）
    conditions: Dict = field(default_factory=dict)  # 触发条件


@dataclass
class NPCSchedule:
    """NPC日程表"""
    npc_id: str
    weekday_schedule: Dict[TimePeriod, ScheduleEntry] = field(default_factory=dict)
    weekend_schedule: Dict[TimePeriod, ScheduleEntry] = field(default_factory=dict)
    special_schedules: Dict[str, Dict[TimePeriod, ScheduleEntry]] = field(default_factory=dict)

    def get_current_schedule(self, period: TimePeriod, is_weekend: bool,
                             special_date_id: str = None) -> Optional[ScheduleEntry]:
        """获取当前时段的日程"""
        # 优先检查特殊日期
        if special_date_id and special_date_id in self.special_schedules:
            if period in self.special_schedules[special_date_id]:
                return self.special_schedules[special_date_id][period]

        # 检查周末/工作日日程
        if is_weekend:
            return self.weekend_schedule.get(period)
        return self.weekday_schedule.get(period)


@dataclass
class GameTime:
    """游戏时间"""
    year: int = 2025
    month: int = 4
    day: int = 1
    period: TimePeriod = TimePeriod.MORNING
    day_of_week: DayOfWeek = DayOfWeek.TUESDAY

    def to_dict(self) -> Dict:
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "period": self.period.value,
            "day_of_week": self.day_of_week.value
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GameTime":
        return cls(
            year=data.get("year", 2025),
            month=data.get("month", 4),
            day=data.get("day", 1),
            period=TimePeriod(data.get("period", "morning")),
            day_of_week=DayOfWeek(data.get("day_of_week", 1))
        )

    def get_date_string(self) -> str:
        """获取日期字符串"""
        day_display = DAY_OF_WEEK_DISPLAY[self.day_of_week]
        return f"{self.year}年{self.month}月{self.day}日 {day_display['name']}"

    def get_time_string(self) -> str:
        """获取时间段字符串"""
        period_display = TIME_PERIOD_DISPLAY[self.period]
        return period_display["name"]

    def get_full_string(self) -> str:
        """获取完整时间字符串"""
        return f"{self.get_date_string()} {self.get_time_string()}"


class TimeCycleManager:
    """
    时间周期管理器

    功能:
    1. 管理游戏时间流逝
    2. 管理NPC日程
    3. 管理特殊日期
    4. 天气系统
    """

    def __init__(self, pet_system=None, npc_manager=None, location_manager=None):
        self.pet_system = pet_system
        self.npc_manager = npc_manager
        self.location_manager = location_manager

        # 当前时间
        self.current_time = GameTime()

        # 当前天气
        self.current_weather = Weather.SUNNY

        # NPC日程
        self.npc_schedules: Dict[str, NPCSchedule] = {}

        # 特殊日期
        self.special_dates: Dict[str, SpecialDate] = {}

        # 天气预报（未来几天）
        self.weather_forecast: List[Weather] = []

        # 回调
        self.on_time_advanced: Optional[Callable] = None
        self.on_day_changed: Optional[Callable] = None
        self.on_weather_changed: Optional[Callable] = None
        self.on_special_date: Optional[Callable] = None

        # 加载数据
        self._load_data()
        self._load_state()

        # 初始化天气
        if not self.weather_forecast:
            self._generate_weather_forecast()

    def _load_data(self):
        """加载数据定义"""
        # 加载特殊日期
        self._load_special_dates()
        # 加载NPC日程
        self._load_npc_schedules()

    def _load_special_dates(self):
        """加载特殊日期"""
        # 默认特殊日期
        default_dates = [
            SpecialDate(
                date_id="new_year",
                name="元旦",
                date_type=SpecialDateType.HOLIDAY,
                month=1, day=1,
                description="新年的第一天",
                school_closed=True,
                icon="🎉"
            ),
            SpecialDate(
                date_id="valentines",
                name="情人节",
                date_type=SpecialDateType.HOLIDAY,
                month=2, day=14,
                description="充满粉红色气泡的一天",
                school_closed=False,
                special_events=["valentine_confession", "chocolate_giving"],
                icon="💝"
            ),
            SpecialDate(
                date_id="cherry_blossom_festival",
                name="樱花祭",
                date_type=SpecialDateType.SCHOOL_EVENT,
                month=4, day=5,
                description="学校一年一度的樱花祭活动",
                school_closed=False,
                affected_locations=["campus_garden", "main_gate"],
                special_events=["sakura_viewing", "festival_booth"],
                icon="🌸"
            ),
            SpecialDate(
                date_id="midterm_exam",
                name="期中考试",
                date_type=SpecialDateType.EXAM_PERIOD,
                month=4, day=20,
                description="期中考试周开始",
                school_closed=False,
                affected_locations=["library", "classroom"],
                icon="📝"
            ),
            SpecialDate(
                date_id="summer_festival",
                name="夏日祭",
                date_type=SpecialDateType.SCHOOL_EVENT,
                month=7, day=15,
                description="盛大的夏日祭典",
                school_closed=False,
                special_events=["fireworks", "yukata_event", "festival_date"],
                icon="🎆"
            ),
            SpecialDate(
                date_id="literature_contest",
                name="文学社征文比赛",
                date_type=SpecialDateType.CLUB_EVENT,
                month=5, day=10,
                description="文学社年度征文比赛",
                affected_locations=["club_room"],
                special_events=["submit_story", "writing_workshop"],
                icon="✍️"
            ),
            SpecialDate(
                date_id="christmas",
                name="圣诞节",
                date_type=SpecialDateType.HOLIDAY,
                month=12, day=25,
                description="圣诞快乐！",
                school_closed=True,
                special_events=["christmas_party", "gift_exchange"],
                icon="🎄"
            ),
        ]

        for date in default_dates:
            self.special_dates[date.date_id] = date

        # 尝试从文件加载
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "special_dates.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for date_data in data.get("dates", []):
                    date = SpecialDate.from_dict(date_data)
                    self.special_dates[date.date_id] = date
        except Exception as e:
            logger.warning(f"加载特殊日期失败: {e}")

    def _load_npc_schedules(self):
        """加载NPC日程"""
        # 创建默认日程
        self._create_default_schedules()

        # 尝试从文件加载
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "npc_schedules.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 解析日程数据...
                logger.info("已加载NPC日程")
        except Exception as e:
            logger.warning(f"加载NPC日程失败: {e}")

    def _create_default_schedules(self):
        """创建默认日程"""
        # 小夏的日程
        xiaoxia_schedule = NPCSchedule(npc_id="xiaoxia")

        # 工作日日程
        xiaoxia_schedule.weekday_schedule = {
            TimePeriod.EARLY_MORNING: ScheduleEntry(
                time_period=TimePeriod.EARLY_MORNING,
                location_id="school_gate",
                activity="来学校的路上"
            ),
            TimePeriod.MORNING: ScheduleEntry(
                time_period=TimePeriod.MORNING,
                location_id="classroom_2_3",
                activity="上课中"
            ),
            TimePeriod.NOON: ScheduleEntry(
                time_period=TimePeriod.NOON,
                location_id="cafeteria",
                activity="吃午饭"
            ),
            TimePeriod.AFTERNOON: ScheduleEntry(
                time_period=TimePeriod.AFTERNOON,
                location_id="classroom_2_3",
                activity="上课中"
            ),
            TimePeriod.EVENING: ScheduleEntry(
                time_period=TimePeriod.EVENING,
                location_id="club_room_literature",
                activity="参加文学社活动"
            ),
            TimePeriod.NIGHT: ScheduleEntry(
                time_period=TimePeriod.NIGHT,
                location_id="home",
                activity="回家了"
            ),
        }

        # 周末日程
        xiaoxia_schedule.weekend_schedule = {
            TimePeriod.MORNING: ScheduleEntry(
                time_period=TimePeriod.MORNING,
                location_id="home",
                activity="睡懒觉"
            ),
            TimePeriod.NOON: ScheduleEntry(
                time_period=TimePeriod.NOON,
                location_id="shopping_district",
                activity="逛街"
            ),
            TimePeriod.AFTERNOON: ScheduleEntry(
                time_period=TimePeriod.AFTERNOON,
                location_id="library",
                activity="在图书馆看书"
            ),
            TimePeriod.EVENING: ScheduleEntry(
                time_period=TimePeriod.EVENING,
                location_id="cafe_moonlight",
                activity="在咖啡厅写作"
            ),
        }

        self.npc_schedules["xiaoxia"] = xiaoxia_schedule

        # 学长的日程
        xuechang_schedule = NPCSchedule(npc_id="xuechang")

        xuechang_schedule.weekday_schedule = {
            TimePeriod.MORNING: ScheduleEntry(
                time_period=TimePeriod.MORNING,
                location_id="classroom_3_1",
                activity="上课中"
            ),
            TimePeriod.NOON: ScheduleEntry(
                time_period=TimePeriod.NOON,
                location_id="rooftop",
                activity="独自吃便当"
            ),
            TimePeriod.AFTERNOON: ScheduleEntry(
                time_period=TimePeriod.AFTERNOON,
                location_id="library",
                activity="在图书馆自习"
            ),
            TimePeriod.EVENING: ScheduleEntry(
                time_period=TimePeriod.EVENING,
                location_id="club_room_literature",
                activity="主持文学社活动"
            ),
        }

        self.npc_schedules["xuechang"] = xuechang_schedule

        logger.info(f"创建了 {len(self.npc_schedules)} 个NPC日程")

    def _load_state(self):
        """加载状态"""
        if not self.pet_system:
            return

        try:
            state = getattr(self.pet_system.data, "time_cycle_state", {}) or {}

            if "current_time" in state:
                self.current_time = GameTime.from_dict(state["current_time"])

            if "current_weather" in state:
                self.current_weather = Weather(state["current_weather"])

            if "weather_forecast" in state:
                self.weather_forecast = [Weather(w) for w in state["weather_forecast"]]

        except Exception as e:
            logger.warning(f"加载时间状态失败: {e}")

    def _save_state(self):
        """保存状态"""
        if not self.pet_system:
            return

        try:
            state = {
                "current_time": self.current_time.to_dict(),
                "current_weather": self.current_weather.value,
                "weather_forecast": [w.value for w in self.weather_forecast]
            }
            self.pet_system.data.time_cycle_state = state
            self.pet_system.save()
        except Exception as e:
            logger.warning(f"保存时间状态失败: {e}")

    # ============================================================
    # 时间管理
    # ============================================================

    def get_current_time(self) -> GameTime:
        """获取当前时间"""
        return self.current_time

    def get_season(self) -> Season:
        """获取当前季节"""
        month = self.current_time.month
        for season, config in SEASON_CONFIG.items():
            if month in config["months"]:
                return season
        return Season.SPRING

    def is_weekend(self) -> bool:
        """是否是周末"""
        return DAY_OF_WEEK_DISPLAY[self.current_time.day_of_week]["is_weekend"]

    def is_school_day(self) -> bool:
        """是否是上学日"""
        if self.is_weekend():
            return False

        # 检查特殊日期
        special = self.get_current_special_date()
        if special and special.school_closed:
            return False

        return True

    def advance_time(self, periods: int = 1) -> Dict[str, Any]:
        """
        推进时间

        Args:
            periods: 推进的时间段数

        Returns:
            变化信息
        """
        result = {
            "old_time": self.current_time.to_dict(),
            "day_changed": False,
            "weather_changed": False,
            "special_date": None
        }

        period_order = list(TimePeriod)
        current_index = period_order.index(self.current_time.period)

        for _ in range(periods):
            current_index += 1

            # 检查是否进入新的一天
            if current_index >= len(period_order):
                current_index = 0
                self._advance_day()
                result["day_changed"] = True

            self.current_time.period = period_order[current_index]

        result["new_time"] = self.current_time.to_dict()

        # 检查特殊日期
        special = self.get_current_special_date()
        if special:
            result["special_date"] = special.to_dict()
            if self.on_special_date:
                self.on_special_date(special)

        self._save_state()

        if self.on_time_advanced:
            self.on_time_advanced(result)

        return result

    def _advance_day(self):
        """推进一天"""
        old_day = self.current_time.day
        old_month = self.current_time.month

        # 推进日期
        self.current_time.day += 1

        # 检查月份变化
        days_in_month = self._get_days_in_month(
            self.current_time.year, self.current_time.month
        )

        if self.current_time.day > days_in_month:
            self.current_time.day = 1
            self.current_time.month += 1

            if self.current_time.month > 12:
                self.current_time.month = 1
                self.current_time.year += 1

        # 推进星期
        day_of_week_value = (self.current_time.day_of_week.value + 1) % 7
        self.current_time.day_of_week = DayOfWeek(day_of_week_value)

        # 更新天气
        self._update_weather()

        if self.on_day_changed:
            self.on_day_changed(self.current_time)

    def _get_days_in_month(self, year: int, month: int) -> int:
        """获取某月的天数"""
        if month in [4, 6, 9, 11]:
            return 30
        elif month == 2:
            # 闰年判断
            if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
                return 29
            return 28
        else:
            return 31

    def set_time(self, year: int = None, month: int = None, day: int = None,
                 period: TimePeriod = None):
        """设置时间"""
        if year is not None:
            self.current_time.year = year
        if month is not None:
            self.current_time.month = max(1, min(12, month))
        if day is not None:
            max_day = self._get_days_in_month(
                self.current_time.year, self.current_time.month
            )
            self.current_time.day = max(1, min(max_day, day))
        if period is not None:
            self.current_time.period = period

        # 重新计算星期
        self._recalculate_day_of_week()
        self._save_state()

    def _recalculate_day_of_week(self):
        """重新计算星期"""
        # 使用Zeller公式计算星期
        y = self.current_time.year
        m = self.current_time.month
        d = self.current_time.day

        if m < 3:
            m += 12
            y -= 1

        k = y % 100
        j = y // 100

        f = d + (13 * (m + 1)) // 5 + k + k // 4 + j // 4 - 2 * j
        day_of_week = (f % 7 + 6) % 7  # 调整为0=周一

        self.current_time.day_of_week = DayOfWeek(day_of_week)

    # ============================================================
    # 天气系统
    # ============================================================

    def get_weather(self) -> Weather:
        """获取当前天气"""
        return self.current_weather

    def get_weather_display(self) -> Dict[str, str]:
        """获取天气显示信息"""
        return WEATHER_DISPLAY.get(self.current_weather, {})

    def _generate_weather_forecast(self, days: int = 7):
        """生成天气预报"""
        self.weather_forecast = []
        season = self.get_season()
        weights = SEASON_CONFIG[season]["weather_weights"]

        weather_options = []
        for weather_name, weight in weights.items():
            try:
                weather = Weather(weather_name)
                weather_options.extend([weather] * weight)
            except ValueError:
                pass

        for _ in range(days):
            if weather_options:
                self.weather_forecast.append(random.choice(weather_options))
            else:
                self.weather_forecast.append(Weather.SUNNY)

    def _update_weather(self):
        """更新天气（进入新的一天时调用）"""
        old_weather = self.current_weather

        if self.weather_forecast:
            self.current_weather = self.weather_forecast.pop(0)
            # 补充预报
            self._generate_weather_forecast(1)
            self.weather_forecast.append(self.weather_forecast[-1])
        else:
            self._generate_weather_forecast()
            self.current_weather = self.weather_forecast[0]

        if old_weather != self.current_weather and self.on_weather_changed:
            self.on_weather_changed(old_weather, self.current_weather)

    def get_forecast(self, days: int = 3) -> List[Dict]:
        """获取天气预报"""
        result = []
        for i, weather in enumerate(self.weather_forecast[:days]):
            display = WEATHER_DISPLAY.get(weather, {})
            result.append({
                "day": i + 1,
                "weather": weather.value,
                "name": display.get("name", "未知"),
                "icon": display.get("icon", "❓")
            })
        return result

    # ============================================================
    # 特殊日期
    # ============================================================

    def get_current_special_date(self) -> Optional[SpecialDate]:
        """获取当前日期的特殊事件"""
        for date in self.special_dates.values():
            if date.month == self.current_time.month and date.day == self.current_time.day:
                if date.year is None or date.year == self.current_time.year:
                    return date
        return None

    def get_upcoming_special_dates(self, days: int = 30) -> List[SpecialDate]:
        """获取未来的特殊日期"""
        upcoming = []

        current = datetime(
            self.current_time.year,
            self.current_time.month,
            self.current_time.day
        )

        for date in self.special_dates.values():
            # 计算今年的日期
            try:
                year = date.year or self.current_time.year
                date_obj = datetime(year, date.month, date.day)

                # 如果已经过了，看明年
                if date_obj < current and date.year is None:
                    date_obj = datetime(year + 1, date.month, date.day)

                diff = (date_obj - current).days
                if 0 <= diff <= days:
                    upcoming.append((diff, date))
            except ValueError:
                pass

        # 按日期排序
        upcoming.sort(key=lambda x: x[0])
        return [date for _, date in upcoming]

    def add_special_date(self, date: SpecialDate):
        """添加特殊日期"""
        self.special_dates[date.date_id] = date

    # ============================================================
    # NPC日程
    # ============================================================

    def get_npc_location(self, npc_id: str) -> Optional[str]:
        """获取NPC当前位置"""
        schedule = self.npc_schedules.get(npc_id)
        if not schedule:
            return None

        special_date = self.get_current_special_date()
        special_id = special_date.date_id if special_date else None

        entry = schedule.get_current_schedule(
            self.current_time.period,
            self.is_weekend(),
            special_id
        )

        if entry:
            return entry.location_id
        return None

    def get_npc_activity(self, npc_id: str) -> Optional[str]:
        """获取NPC当前活动"""
        schedule = self.npc_schedules.get(npc_id)
        if not schedule:
            return None

        special_date = self.get_current_special_date()
        special_id = special_date.date_id if special_date else None

        entry = schedule.get_current_schedule(
            self.current_time.period,
            self.is_weekend(),
            special_id
        )

        if entry:
            return entry.activity
        return None

    def get_npcs_at_location(self, location_id: str) -> List[str]:
        """获取某个地点的所有NPC"""
        npcs = []
        for npc_id, schedule in self.npc_schedules.items():
            if self.get_npc_location(npc_id) == location_id:
                npcs.append(npc_id)
        return npcs

    def get_npc_daily_schedule(self, npc_id: str, is_weekend: bool = None) -> List[Dict]:
        """获取NPC一天的日程"""
        if is_weekend is None:
            is_weekend = self.is_weekend()

        schedule = self.npc_schedules.get(npc_id)
        if not schedule:
            return []

        day_schedule = schedule.weekend_schedule if is_weekend else schedule.weekday_schedule

        result = []
        for period in TimePeriod:
            entry = day_schedule.get(period)
            period_display = TIME_PERIOD_DISPLAY[period]

            if entry:
                result.append({
                    "period": period.value,
                    "period_name": period_display["name"],
                    "icon": period_display["icon"],
                    "location": entry.location_id,
                    "activity": entry.activity
                })
            else:
                result.append({
                    "period": period.value,
                    "period_name": period_display["name"],
                    "icon": period_display["icon"],
                    "location": "unknown",
                    "activity": "不明"
                })

        return result

    # ============================================================
    # 信息获取
    # ============================================================

    def get_time_display(self) -> Dict[str, Any]:
        """获取时间显示信息"""
        period_display = TIME_PERIOD_DISPLAY[self.current_time.period]
        day_display = DAY_OF_WEEK_DISPLAY[self.current_time.day_of_week]
        season = self.get_season()
        season_config = SEASON_CONFIG[season]
        weather_display = WEATHER_DISPLAY.get(self.current_weather, {})

        return {
            "date": self.current_time.get_date_string(),
            "full_date": f"{self.current_time.year}年{self.current_time.month}月{self.current_time.day}日",
            "day_of_week": day_display["name"],
            "is_weekend": day_display["is_weekend"],
            "period": period_display["name"],
            "period_icon": period_display["icon"],
            "period_description": period_display["description"],
            "season": season_config["name"],
            "season_icon": season_config["icon"],
            "weather": weather_display.get("name", "未知"),
            "weather_icon": weather_display.get("icon", "❓"),
            "weather_effect": weather_display.get("effect", ""),
            "is_school_day": self.is_school_day()
        }

    def get_atmosphere_description(self) -> str:
        """获取氛围描述"""
        period_display = TIME_PERIOD_DISPLAY[self.current_time.period]
        season_config = SEASON_CONFIG[self.get_season()]
        weather_display = WEATHER_DISPLAY.get(self.current_weather, {})

        templates = [
            "{season}的{period}，{weather}。",
            "这是一个{weather}的{period}。{season_desc}",
            "{period}时分，天空{weather_desc}。"
        ]

        weather_desc_map = {
            Weather.SUNNY: "晴朗明媚",
            Weather.CLOUDY: "飘着几朵白云",
            Weather.OVERCAST: "阴沉沉的",
            Weather.RAINY: "下着淅淅沥沥的雨",
            Weather.STORMY: "电闪雷鸣",
            Weather.SNOWY: "飘着雪花",
            Weather.FOGGY: "弥漫着薄雾",
            Weather.WINDY: "刮着大风",
        }

        return random.choice(templates).format(
            season=season_config["name"],
            period=period_display["name"],
            weather=weather_display.get("name", ""),
            season_desc=season_config["description"],
            weather_desc=weather_desc_map.get(self.current_weather, "")
        )


# 便捷函数
def create_time_cycle(pet_system=None, npc_manager=None,
                      location_manager=None) -> TimeCycleManager:
    """创建时间周期系统"""
    return TimeCycleManager(pet_system, npc_manager, location_manager)
