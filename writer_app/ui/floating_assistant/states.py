"""
悬浮写作助手 - 状态管理模块
定义所有状态常量、节日检测、季节检测等
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
import math
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

class AssistantState:
    """助手状态常量定义"""

    # 基础状态
    IDLE = "idle"                    # 待机
    THINKING = "thinking"            # 思考中
    SUCCESS = "success"              # 成功/满意
    ERROR = "error"                  # 错误/困惑

    # 情绪状态
    HAPPY = "happy"                  # 开心
    SAD = "sad"                      # 难过
    EXCITED = "excited"              # 兴奋/激动
    SHY = "shy"                      # 害羞
    ANGRY = "angry"                  # 生气
    SURPRISED = "surprised"          # 惊讶
    CURIOUS = "curious"              # 好奇
    LOVE = "love"                    # 喜爱/心动
    WORRIED = "worried"              # 担心
    SCARED = "scared"                # 害怕/恐惧
    SHOCKED = "shocked"              # 震惊
    CRYING = "crying"                # 哭泣

    # 动作状态
    EATING = "eating"                # 进食
    SLEEPING = "sleeping"            # 睡眠
    GREETING = "greeting"            # 打招呼
    CHEERING = "cheering"            # 加油鼓励
    READING = "reading"              # 阅读
    WRITING = "writing"              # 写作
    CELEBRATING = "celebrating"      # 庆祝
    PLAYING = "playing"              # 玩耍

    # 特殊状态（好感度解锁）
    BLUSH = "blush"                  # 脸红（好感度50+）
    TRUST = "trust"                  # 信任微笑（好感度100+）
    DEVOTED = "devoted"              # 专注陪伴（好感度200+）

    # 时间特殊状态
    MORNING = "morning"              # 早安
    NIGHT = "night"                  # 晚安
    MIDNIGHT = "midnight"            # 深夜

    # 季节状态
    SPRING = "spring"                # 春装
    SUMMER = "summer"                # 夏装
    AUTUMN = "autumn"                # 秋装
    WINTER = "winter"                # 冬装

    # 中国传统节日
    NEW_YEAR = "new_year"            # 元旦
    SPRING_FESTIVAL = "spring_festival"  # 春节
    LANTERN = "lantern"              # 元宵节
    QINGMING = "qingming"            # 清明节
    DRAGON_BOAT = "dragon_boat"      # 端午节
    QIXI = "qixi"                    # 七夕
    MID_AUTUMN = "mid_autumn"        # 中秋节
    DOUBLE_NINTH = "double_ninth"    # 重阳节

    # 西方节日
    VALENTINES = "valentines"        # 情人节
    EASTER = "easter"                # 复活节
    HALLOWEEN = "halloween"          # 万圣节
    THANKSGIVING = "thanksgiving"    # 感恩节
    CHRISTMAS = "christmas"          # 圣诞节

    # 特殊纪念日
    BIRTHDAY = "birthday"            # 生日
    ANNIVERSARY = "anniversary"      # 周年纪念

    # 服装状态
    SPORTSWEAR = "sportswear"        # 运动服
    MAID = "maid"                    # 女仆装
    SWIMSUIT = "swimsuit"            # 泳装
    CASUAL = "casual"                # 休闲服
    FORMAL = "formal"                # 正装
    PAJAMAS = "pajamas"              # 睡衣
    UNIFORM = "uniform"              # 制服
    KIMONO = "kimono"                # 和服
    CHEONGSAM = "cheongsam"          # 旗袍
    GOTHIC = "gothic"                # 哥特风
    LOLITA = "lolita"                # 洛丽塔
    FANTASY = "fantasy"              # 幻想风
    KNIGHT = "knight"                # 骑士装
    WITCH = "witch"                  # 魔女装
    IDOL = "idol"                    # 偶像装

    # 场景/活动状态
    COOKING = "cooking"              # 做饭
    GAMING = "gaming"                # 打游戏
    MUSIC = "music"                  # 听音乐/演奏
    SHOPPING = "shopping"            # 购物
    TRAVEL = "travel"                # 旅行
    BEACH = "beach"                  # 海滩
    MOUNTAIN = "mountain"            # 登山
    CAFE = "cafe"                    # 咖啡厅
    SCHOOL = "school"                # 学校
    OFFICE = "office"                # 办公室

    # 天气状态
    SUNNY = "sunny"                  # 晴天
    CLOUDY = "cloudy"                # 多云
    RAINY = "rainy"                  # 下雨
    SNOWY = "snowy"                  # 下雪
    FOGGY = "foggy"                  # 雾天
    STORMY = "stormy"                # 雷暴

    # 心情状态（新增）
    MOOD_GREAT = "mood_great"        # 心情极好
    MOOD_GOOD = "mood_good"          # 心情好
    MOOD_NORMAL = "mood_normal"      # 心情一般
    MOOD_BAD = "mood_bad"            # 心情差
    MOOD_TERRIBLE = "mood_terrible"  # 心情极差

    # 专注/写作状态
    FOCUSED = "focused"              # 专注写作
    ZEN = "zen"                      # 沉浸模式
    TYPING = "typing"                # 打字机模式

    # 互动状态（被点击时触发）
    POKED = "poked"                  # 被戳（轻微反应）
    POKED_AGAIN = "poked_again"      # 再次被戳（有点烦）
    ANNOYED = "annoyed"              # 被烦到了
    STARTLED = "startled"            # 被吓到
    TICKLED = "tickled"              # 被挠痒痒
    PATTED = "patted"                # 被摸头
    HUGGED = "hugged"                # 被拥抱
    WAKING_UP = "waking_up"          # 正在醒来
    SLEEPY_DISTURBED = "sleepy_disturbed"  # 睡眠被打扰
    DOZING = "dozing"                # 打瞌睡
    STRETCHING = "stretching"        # 伸懒腰

    @classmethod
    def all_states(cls) -> List[str]:
        """获取所有状态列表"""
        return [
            cls.IDLE, cls.THINKING, cls.SUCCESS, cls.ERROR,
            cls.HAPPY, cls.SAD, cls.EXCITED, cls.SHY, cls.ANGRY,
            cls.SURPRISED, cls.CURIOUS, cls.LOVE, cls.WORRIED,
            cls.SCARED, cls.SHOCKED, cls.CRYING,
            cls.EATING, cls.SLEEPING, cls.GREETING, cls.CHEERING,
            cls.READING, cls.WRITING, cls.CELEBRATING, cls.PLAYING,
            cls.BLUSH, cls.TRUST, cls.DEVOTED,
            cls.MORNING, cls.NIGHT, cls.MIDNIGHT,
            cls.SPRING, cls.SUMMER, cls.AUTUMN, cls.WINTER,
            cls.NEW_YEAR, cls.SPRING_FESTIVAL, cls.LANTERN, cls.QINGMING,
            cls.DRAGON_BOAT, cls.QIXI, cls.MID_AUTUMN, cls.DOUBLE_NINTH,
            cls.VALENTINES, cls.EASTER, cls.HALLOWEEN, cls.THANKSGIVING,
            cls.CHRISTMAS, cls.BIRTHDAY, cls.ANNIVERSARY,
            cls.SPORTSWEAR, cls.MAID, cls.SWIMSUIT, cls.CASUAL, cls.FORMAL,
            cls.PAJAMAS, cls.UNIFORM, cls.KIMONO, cls.CHEONGSAM, cls.GOTHIC,
            cls.LOLITA, cls.FANTASY, cls.KNIGHT, cls.WITCH, cls.IDOL,
            cls.COOKING, cls.GAMING, cls.MUSIC, cls.SHOPPING, cls.TRAVEL,
            cls.BEACH, cls.MOUNTAIN, cls.CAFE, cls.SCHOOL, cls.OFFICE,
            cls.SUNNY, cls.CLOUDY, cls.RAINY, cls.SNOWY, cls.FOGGY, cls.STORMY,
            cls.MOOD_GREAT, cls.MOOD_GOOD, cls.MOOD_NORMAL, cls.MOOD_BAD, cls.MOOD_TERRIBLE,
            cls.FOCUSED, cls.ZEN, cls.TYPING,
            cls.POKED, cls.POKED_AGAIN, cls.ANNOYED, cls.STARTLED, cls.TICKLED,
            cls.PATTED, cls.HUGGED, cls.WAKING_UP, cls.SLEEPY_DISTURBED, cls.DOZING, cls.STRETCHING
        ]


# 状态显示名称（中文）
STATE_NAMES: Dict[str, str] = {
    "idle": "待机", "thinking": "思考", "success": "成功", "error": "错误",
    "happy": "开心", "sad": "难过", "excited": "兴奋", "shy": "害羞",
    "angry": "生气", "surprised": "惊讶", "curious": "好奇", "love": "喜爱",
    "worried": "担心", "scared": "害怕", "shocked": "震惊", "crying": "哭泣",
    "eating": "进食", "sleeping": "睡眠", "greeting": "问候",
    "cheering": "鼓励", "reading": "阅读", "writing": "写作", "celebrating": "庆祝",
    "playing": "玩耍", "blush": "脸红", "trust": "信任", "devoted": "专注",
    "morning": "早安", "night": "晚安", "midnight": "深夜",
    "spring": "春装", "summer": "夏装", "autumn": "秋装", "winter": "冬装",
    "new_year": "元旦", "spring_festival": "春节", "lantern": "元宵",
    "qingming": "清明", "dragon_boat": "端午", "qixi": "七夕",
    "mid_autumn": "中秋", "double_ninth": "重阳",
    "valentines": "情人节", "easter": "复活节", "halloween": "万圣节",
    "thanksgiving": "感恩节", "christmas": "圣诞节",
    "birthday": "生日", "anniversary": "周年",
    "sportswear": "运动服", "maid": "女仆装", "swimsuit": "泳装",
    "casual": "休闲服", "formal": "正装", "pajamas": "睡衣",
    "uniform": "制服", "kimono": "和服", "cheongsam": "旗袍",
    "gothic": "哥特风", "lolita": "洛丽塔", "fantasy": "幻想风",
    "knight": "骑士装", "witch": "魔女装", "idol": "偶像装",
    "cooking": "做饭", "gaming": "打游戏", "music": "音乐",
    "shopping": "购物", "travel": "旅行", "beach": "海滩",
    "mountain": "登山", "cafe": "咖啡厅", "school": "学校", "office": "办公室",
    "sunny": "晴天", "cloudy": "多云", "rainy": "下雨",
    "snowy": "下雪", "foggy": "雾天", "stormy": "雷暴",
    "mood_great": "心情极好", "mood_good": "心情好", "mood_normal": "心情一般",
    "mood_bad": "心情差", "mood_terrible": "心情极差",
    "focused": "专注", "zen": "沉浸", "typing": "打字",
    "poked": "被戳", "poked_again": "又被戳", "annoyed": "烦躁",
    "startled": "吓到", "tickled": "被挠", "patted": "摸头",
    "hugged": "拥抱", "waking_up": "醒来", "sleepy_disturbed": "睡眠打扰",
    "dozing": "打盹", "stretching": "伸懒腰"
}

# 状态默认图标 (使用 Fluent UI)
STATE_EMOJIS: Dict[str, str] = {
    "idle": get_icon("bot", "🤖"), 
    "thinking": get_icon("brain_circuit", "🤔"), 
    "success": get_icon("checkmark_circle", "😊"), 
    "error": get_icon("error_circle", "😥"),
    "happy": get_icon("presence_available", "😄"), 
    "sad": get_icon("presence_away", "😢"), 
    "excited": get_icon("sparkle", "🤩"), 
    "shy": get_icon("presence_dnd", "😳"),
    "angry": get_icon("warning", "😠"), 
    "surprised": get_icon("alert", "😲"), 
    "curious": get_icon("search", "🧐"), 
    "love": get_icon("heart", "😍"),
    "worried": get_icon("question", "😟"),
    "scared": get_icon("warning", "😨"),
    "shocked": get_icon("alert", "😱"),
    "crying": get_icon("presence_away", "😭"),
    "eating": get_icon("food", "😋"), 
    "sleeping": get_icon("weather_moon", "😴"), 
    "greeting": get_icon("hand_shake", "👋"),
    "cheering": get_icon("trophy", "💪"), 
    "reading": get_icon("book_open", "📖"), 
    "writing": get_icon("edit", "✍️"), 
    "celebrating": get_icon("gift", "🎉"),
    "playing": get_icon("games", "🎮"), 
    "blush": get_icon("presence_dnd", "🥰"), 
    "trust": get_icon("people_community", "🤗"), 
    "devoted": get_icon("star", "💝"),
    "morning": get_icon("weather_sunny", "🌅"), 
    "night": get_icon("weather_moon", "🌙"), 
    "midnight": get_icon("weather_moon", "🦉"),
    "spring": get_icon("leaf_one", "🌸"), 
    "summer": get_icon("weather_sunny", "🌻"), 
    "autumn": get_icon("leaf_three", "🍂"), 
    "winter": get_icon("weather_snow", "❄️"),
    "new_year": get_icon("gift", "🎊"), 
    "spring_festival": get_icon("gift", "🧧"), 
    "lantern": get_icon("lightbulb", "🏮"),
    "qingming": get_icon("leaf_two", "🌿"), 
    "dragon_boat": get_icon("food", "🐲"), 
    "qixi": get_icon("heart", "💕"),
    "mid_autumn": get_icon("weather_moon", "🥮"), 
    "double_ninth": get_icon("mountain", "🏔️"),
    "valentines": get_icon("heart", "💝"), 
    "easter": get_icon("animal_rabbit", "🐰"), 
    "halloween": get_icon("dark_theme", "🎃"),
    "thanksgiving": get_icon("food", "🦃"), 
    "christmas": get_icon("gift", "🎄"),
    "birthday": get_icon("food_cake", "🎂"), 
    "anniversary": get_icon("star", "💍"),
    "sportswear": get_icon("run", "🏃"), 
    "maid": get_icon("ribbon", "🎀"), 
    "swimsuit": get_icon("weather_sunny", "👙"),
    "casual": get_icon("t_shirt", "👕"), 
    "formal": get_icon("person_board", "👔"), 
    "pajamas": get_icon("bed", "🛏️"),
    "uniform": get_icon("hat_graduation", "🎓"), 
    "kimono": get_icon("ribbon", "👘"), 
    "cheongsam": get_icon("ribbon", "🧧"),
    "gothic": get_icon("dark_theme", "🦇"), 
    "lolita": get_icon("ribbon", "🎀"), 
    "fantasy": get_icon("sparkle", "✨"),
    "knight": get_icon("shield", "⚔️"), 
    "witch": get_icon("hat_graduation", "🧙‍♀️"), 
    "idol": get_icon("mic", "🎤"),
    "cooking": get_icon("food", "🍳"), 
    "gaming": get_icon("games", "🎮"), 
    "music": get_icon("music", "🎵"),
    "shopping": get_icon("cart", "🛍️"), 
    "travel": get_icon("airplane", "✈️"), 
    "beach": get_icon("weather_sunny", "🏖️"),
    "mountain": get_icon("mountain", "🏔️"), 
    "cafe": get_icon("drink_coffee", "☕"), 
    "school": get_icon("hat_graduation", "🏫"), 
    "office": get_icon("briefcase", "💼"),
    "sunny": get_icon("weather_sunny", "☀️"), 
    "cloudy": get_icon("weather_cloudy", "⛅"), 
    "rainy": get_icon("weather_rain", "🌧️"),
    "snowy": get_icon("weather_snow", "❄️"), 
    "foggy": get_icon("weather_fog", "🌫️"), 
    "stormy": get_icon("weather_squalls", "⛈️"),
    "mood_great": get_icon("presence_available", "😁"), 
    "mood_good": get_icon("presence_available", "😊"), 
    "mood_normal": get_icon("presence_away", "😐"),
    "mood_bad": get_icon("presence_dnd", "😞"), 
    "mood_terrible": get_icon("presence_blocked", "😭"),
    "focused": get_icon("target", "🎯"), 
    "zen": get_icon("brain_circuit", "🧘"), 
    "typing": get_icon("keyboard", "⌨️"),
    "poked": get_icon("hand_draw", "😯"), 
    "poked_again": get_icon("hand_draw", "😑"), 
    "annoyed": get_icon("warning", "😤"),
    "startled": get_icon("alert", "😱"), 
    "tickled": get_icon("sparkle", "🤭"), 
    "patted": get_icon("person", "😊"),
    "hugged": get_icon("people_community", "🥰"), 
    "waking_up": get_icon("weather_sunny", "😪"), 
    "sleepy_disturbed": get_icon("weather_moon", "😴"),
    "dozing": get_icon("weather_moon", "💤"), 
    "stretching": get_icon("person", "🙆")
}

# 状态回退链
STATE_FALLBACKS: Dict[str, List[str]] = {
    AssistantState.EXCITED: [AssistantState.HAPPY, AssistantState.SUCCESS, AssistantState.IDLE],
    AssistantState.SHY: [AssistantState.BLUSH, AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.ANGRY: [AssistantState.ERROR, AssistantState.IDLE],
    AssistantState.SURPRISED: [AssistantState.CURIOUS, AssistantState.IDLE],
    AssistantState.CURIOUS: [AssistantState.THINKING, AssistantState.IDLE],
    AssistantState.LOVE: [AssistantState.BLUSH, AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.WORRIED: [AssistantState.SAD, AssistantState.THINKING, AssistantState.IDLE],
    AssistantState.SCARED: [AssistantState.WORRIED, AssistantState.SURPRISED, AssistantState.IDLE],
    AssistantState.SHOCKED: [AssistantState.SURPRISED, AssistantState.STARTLED, AssistantState.IDLE],
    AssistantState.CRYING: [AssistantState.SAD, AssistantState.WORRIED, AssistantState.IDLE],
    AssistantState.GREETING: [AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.CHEERING: [AssistantState.EXCITED, AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.READING: [AssistantState.THINKING, AssistantState.IDLE],
    AssistantState.WRITING: [AssistantState.THINKING, AssistantState.IDLE],
    AssistantState.CELEBRATING: [AssistantState.EXCITED, AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.PLAYING: [AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.BLUSH: [AssistantState.SHY, AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.TRUST: [AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.DEVOTED: [AssistantState.LOVE, AssistantState.TRUST, AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.MORNING: [AssistantState.GREETING, AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.NIGHT: [AssistantState.SLEEPING, AssistantState.IDLE],
    AssistantState.MIDNIGHT: [AssistantState.SLEEPING, AssistantState.IDLE],
    AssistantState.SUCCESS: [AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.ERROR: [AssistantState.SAD, AssistantState.IDLE],
    AssistantState.HAPPY: [AssistantState.IDLE],
    AssistantState.SAD: [AssistantState.IDLE],
    AssistantState.EATING: [AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.SLEEPING: [AssistantState.IDLE],
    AssistantState.THINKING: [AssistantState.IDLE],
    # 专注/写作状态回退
    AssistantState.FOCUSED: [AssistantState.WRITING, AssistantState.THINKING, AssistantState.IDLE],
    AssistantState.ZEN: [AssistantState.FOCUSED, AssistantState.DEVOTED, AssistantState.IDLE],
    AssistantState.TYPING: [AssistantState.WRITING, AssistantState.FOCUSED, AssistantState.IDLE],
    # 天气状态回退
    AssistantState.SUNNY: [AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.CLOUDY: [AssistantState.THINKING, AssistantState.IDLE],
    AssistantState.RAINY: [AssistantState.SAD, AssistantState.IDLE],
    AssistantState.SNOWY: [AssistantState.SURPRISED, AssistantState.IDLE],
    AssistantState.FOGGY: [AssistantState.THINKING, AssistantState.IDLE],
    AssistantState.STORMY: [AssistantState.WORRIED, AssistantState.IDLE],
    # 互动状态回退
    AssistantState.POKED: [AssistantState.SURPRISED, AssistantState.IDLE],
    AssistantState.POKED_AGAIN: [AssistantState.POKED, AssistantState.SURPRISED, AssistantState.IDLE],
    AssistantState.ANNOYED: [AssistantState.ANGRY, AssistantState.POKED_AGAIN, AssistantState.IDLE],
    AssistantState.STARTLED: [AssistantState.SURPRISED, AssistantState.IDLE],
    AssistantState.TICKLED: [AssistantState.HAPPY, AssistantState.SHY, AssistantState.IDLE],
    AssistantState.PATTED: [AssistantState.HAPPY, AssistantState.BLUSH, AssistantState.IDLE],
    AssistantState.HUGGED: [AssistantState.LOVE, AssistantState.BLUSH, AssistantState.HAPPY, AssistantState.IDLE],
    AssistantState.WAKING_UP: [AssistantState.SLEEPY_DISTURBED, AssistantState.IDLE],
    AssistantState.SLEEPY_DISTURBED: [AssistantState.SLEEPING, AssistantState.IDLE],
    AssistantState.DOZING: [AssistantState.SLEEPING, AssistantState.IDLE],
    AssistantState.STRETCHING: [AssistantState.WAKING_UP, AssistantState.IDLE],
}


class LunarCalendar:
    """简易农历计算（基于查表法，支持2020-2030年）"""

    # 农历数据（每年的农历月份信息）
    # 格式：闰月(0表示无), 每月大小(1=30天,0=29天)从正月到十二月
    LUNAR_INFO = {
        2020: (4, [0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1]),  # 闰四月
        2021: (0, [0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0]),
        2022: (0, [1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1]),
        2023: (2, [0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1]),  # 闰二月
        2024: (0, [1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1]),
        2025: (6, [1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0]),  # 闰六月
        2026: (0, [1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1]),
        2027: (0, [0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1]),
        2028: (5, [0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0]),  # 闰五月
        2029: (0, [1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0]),
        2030: (0, [0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0]),
    }

    # 各年春节日期（公历）
    SPRING_FESTIVAL_DATES = {
        2020: (1, 25), 2021: (2, 12), 2022: (2, 1), 2023: (1, 22),
        2024: (2, 10), 2025: (1, 29), 2026: (2, 17), 2027: (2, 6),
        2028: (1, 26), 2029: (2, 13), 2030: (2, 3),
    }

    @classmethod
    def get_lunar_date(cls, year: int, month: int, day: int) -> Optional[Tuple[int, int, int, bool]]:
        """
        将公历日期转换为农历日期

        Args:
            year: 公历年
            month: 公历月
            day: 公历日

        Returns:
            (农历年, 农历月, 农历日, 是否闰月) 或 None
        """
        if year not in cls.SPRING_FESTIVAL_DATES:
            return None

        sf_month, sf_day = cls.SPRING_FESTIVAL_DATES[year]
        sf_date = datetime(year, sf_month, sf_day)
        target_date = datetime(year, month, day)

        # 计算与春节的天数差
        diff = (target_date - sf_date).days

        if diff < 0:
            # 在春节之前，属于上一年农历
            if year - 1 not in cls.LUNAR_INFO:
                return None
            return cls._calc_lunar_from_diff(year - 1, diff + 365)

        return cls._calc_lunar_from_diff(year, diff)

    @classmethod
    def _calc_lunar_from_diff(cls, lunar_year: int, diff: int) -> Optional[Tuple[int, int, int, bool]]:
        """根据与春节的天数差计算农历日期"""
        if lunar_year not in cls.LUNAR_INFO:
            return None

        leap_month, month_days = cls.LUNAR_INFO[lunar_year]

        # 从正月初一开始累加
        lunar_month = 1
        lunar_day = 1 + diff
        is_leap = False

        month_idx = 0
        while lunar_day > 0:
            days_in_month = 30 if month_days[month_idx] else 29

            if lunar_day <= days_in_month:
                break

            lunar_day -= days_in_month
            month_idx += 1

            # 检查是否进入闰月
            if leap_month > 0 and lunar_month == leap_month and not is_leap:
                is_leap = True
            else:
                is_leap = False
                lunar_month += 1

            if lunar_month > 12:
                return None  # 超出范围

        return (lunar_year, lunar_month, lunar_day, is_leap)

    @classmethod
    def get_lunar_festival(cls, year: int, month: int, day: int, tolerance_days: int = 3) -> Optional[str]:
        """
        检测是否为农历节日

        Args:
            year, month, day: 公历日期
            tolerance_days: 容差天数

        Returns:
            节日状态常量 或 None
        """
        lunar = cls.get_lunar_date(year, month, day)
        if not lunar:
            return None

        lunar_year, lunar_month, lunar_day, is_leap = lunar

        # 不考虑闰月的节日
        if is_leap:
            return None

        # 农历节日定义
        festivals = {
            (1, 1): AssistantState.SPRING_FESTIVAL,    # 春节
            (1, 15): AssistantState.LANTERN,           # 元宵
            (5, 5): AssistantState.DRAGON_BOAT,        # 端午
            (7, 7): AssistantState.QIXI,               # 七夕
            (8, 15): AssistantState.MID_AUTUMN,        # 中秋
            (9, 9): AssistantState.DOUBLE_NINTH,       # 重阳
        }

        for (f_month, f_day), state in festivals.items():
            # 简化检测：只检查当天
            if lunar_month == f_month and abs(lunar_day - f_day) <= tolerance_days:
                return state

        return None


class FestivalDetector:
    """节日检测器"""

    # 固定日期节日（公历）
    FIXED_FESTIVALS = {
        (1, 1): AssistantState.NEW_YEAR,       # 元旦
        (2, 14): AssistantState.VALENTINES,    # 情人节
        (4, 5): AssistantState.QINGMING,       # 清明（近似）
        (10, 31): AssistantState.HALLOWEEN,    # 万圣节
        (12, 25): AssistantState.CHRISTMAS,    # 圣诞节
    }

    # 感恩节（11月第4个周四）
    @staticmethod
    def get_thanksgiving(year: int) -> Tuple[int, int]:
        """计算感恩节日期"""
        nov_first = datetime(year, 11, 1)
        # 找到11月第一个周四
        days_until_thursday = (3 - nov_first.weekday()) % 7
        first_thursday = nov_first + timedelta(days=days_until_thursday)
        # 第四个周四
        thanksgiving = first_thursday + timedelta(weeks=3)
        return (11, thanksgiving.day)

    # 复活节（春分后第一个满月后的第一个周日）
    @staticmethod
    def get_easter(year: int) -> Tuple[int, int]:
        """计算复活节日期（简化算法）"""
        # 使用Meeus/Jones/Butcher算法
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return (month, day)

    @classmethod
    def get_current_festival(cls, tolerance_days: int = 3,
                              birthday: Optional[str] = None,
                              created_at: Optional[str] = None) -> Optional[str]:
        """
        获取当前节日状态 (优先级：生日 > 纪念日 > 农历节日 > 公历节日)

        Args:
            tolerance_days: 节日前后多少天内算作节日期间
            birthday: 用户设置的助手生日（格式："MM-DD"）
            created_at: 助手创建时间（ISO格式）

        Returns:
            节日状态常量，如果不是节日期间则返回None
        """
        today = datetime.now()
        year = today.year
        month = today.month
        day = today.day

        # 1. 检查生日 (最高优先级)
        if birthday:
            try:
                parts = birthday.split("-")
                if len(parts) >= 2:
                    b_month, b_day = int(parts[0]), int(parts[1])
                    if month == b_month and abs(day - b_day) <= tolerance_days:
                        return AssistantState.BIRTHDAY
            except (ValueError, TypeError):
                pass

        # 2. 检查相识周年
        if created_at:
            try:
                # 尝试解析ISO格式，处理可能的毫秒部分
                if "." in created_at:
                    created_at = created_at.split(".")[0]
                created = datetime.fromisoformat(created_at)
                if (month == created.month and
                        abs(day - created.day) <= tolerance_days and
                        year > created.year):
                    return AssistantState.ANNIVERSARY
            except (ValueError, TypeError):
                pass

        # 3. 检查农历节日 (传统节日优先)
        lunar_festival = LunarCalendar.get_lunar_festival(year, month, day, tolerance_days)
        if lunar_festival:
            return lunar_festival

        # 4. 检查固定日期节日
        for (f_month, f_day), state in cls.FIXED_FESTIVALS.items():
            try:
                festival_date = datetime(year, f_month, f_day)
                diff = abs((today - festival_date).days)
                if diff <= tolerance_days:
                    return state
            except ValueError:
                continue

        # 5. 检查变动日期节日
        # 感恩节
        thanks_month, thanks_day = cls.get_thanksgiving(year)
        if month == thanks_month and abs(day - thanks_day) <= tolerance_days:
            return AssistantState.THANKSGIVING

        # 复活节
        easter_month, easter_day = cls.get_easter(year)
        if month == easter_month and abs(day - easter_day) <= tolerance_days:
            return AssistantState.EASTER

        return None

    @classmethod
    def get_festival_greeting(cls, festival: str) -> str:
        """获取节日问候语"""
        greetings = {
            AssistantState.NEW_YEAR: "元旦快乐！新的一年也要加油写作哦~",
            AssistantState.SPRING_FESTIVAL: "春节快乐！愿你岁岁常欢愉，万事皆胜意。",
            AssistantState.LANTERN: "元宵节快乐！吃汤圆了吗？",
            AssistantState.QINGMING: "清明时节雨纷纷，又是怀念的季节。",
            AssistantState.DRAGON_BOAT: "端午安康！记得吃粽子哦~",
            AssistantState.QIXI: "七夕快乐！愿有情人终成眷属。",
            AssistantState.MID_AUTUMN: "中秋快乐！月圆人团圆。",
            AssistantState.DOUBLE_NINTH: "重阳快乐！登高远眺，灵感广进。",
            AssistantState.VALENTINES: "情人节快乐！今天的故事也要甜甜的~",
            AssistantState.HALLOWEEN: "万圣节快乐！不给灵感就捣蛋~",
            AssistantState.CHRISTMAS: "圣诞快乐！愿你的写作之旅充满奇迹。",
            AssistantState.BIRTHDAY: f"{get_icon('food_cake', '🎂')} 祝我生日快乐！很高兴能一直陪伴在你身边创作~",
            AssistantState.ANNIVERSARY: f"{get_icon('heart', '💖')} 周年纪念快乐！我们已经一起创作这么久了呢~",
        }
        return greetings.get(festival, f"节日快乐！今天是{STATE_NAMES.get(festival, festival)}~")


class SeasonDetector:
    """季节检测器"""

    SEASON_MONTHS = {
        AssistantState.SPRING: [3, 4, 5],
        AssistantState.SUMMER: [6, 7, 8],
        AssistantState.AUTUMN: [9, 10, 11],
        AssistantState.WINTER: [12, 1, 2],
    }

    @classmethod
    def get_current_season(cls) -> str:
        """获取当前季节状态"""
        month = datetime.now().month
        for season, months in cls.SEASON_MONTHS.items():
            if month in months:
                return season
        return AssistantState.SPRING  # 默认返回春季

    @classmethod
    def get_season_greeting(cls, season: str) -> str:
        """获取季节问候语"""
        greetings = {
            AssistantState.SPRING: "春天到了，万物复苏，正是播种灵感的好时节。",
            AssistantState.SUMMER: "夏天来了，愿你的文思如夏日阳光般炽热。",
            AssistantState.AUTUMN: "秋天是收获的季节，你的故事也要迎来高潮了吧？",
            AssistantState.WINTER: "冬天虽然寒冷，但文字是有温度的。",
        }
        return greetings.get(season, f"时节变换，注意身体哦~")


class TimeDetector:
    """时间段检测器"""

    @classmethod
    def get_time_state(cls) -> Optional[str]:
        """根据当前时间获取特殊状态"""
        hour = datetime.now().hour

        if 5 <= hour < 9:
            return AssistantState.MORNING
        elif 11 <= hour < 14:
            return "noon"
        elif 14 <= hour < 17:
            return "afternoon"
        elif 22 <= hour or hour < 2:
            return AssistantState.NIGHT
        elif 2 <= hour < 5:
            return AssistantState.MIDNIGHT
        return None

    @classmethod
    def get_greeting_period(cls) -> str:
        """获取当前问候时段"""
        hour = datetime.now().hour

        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"


class InteractionManager:
    """
    互动管理器 - 处理点击互动和状态转换

    功能：
    1. 根据当前状态和点击次数决定互动反应
    2. 管理状态转换链（如：睡觉 -> 被打扰 -> 醒来）
    3. 记录互动历史用于特殊反应
    """

    # 每个状态被点击时的反应链
    # 格式: {当前状态: [(点击次数阈值, 目标状态, 持续时间ms, 台词), ...]}
    INTERACTION_CHAINS: Dict[str, List[Tuple[int, str, int, str]]] = {
        # 睡觉状态的互动
        AssistantState.SLEEPING: [
            (1, AssistantState.SLEEPY_DISTURBED, 1500, "唔...别吵..."),
            (2, AssistantState.SLEEPY_DISTURBED, 1500, "让我再睡一会儿..."),
            (3, AssistantState.DOZING, 2000, "嗯...好困..."),
            (4, AssistantState.WAKING_UP, 2000, "好啦好啦，我起来了..."),
            (5, AssistantState.STRETCHING, 2000, "啊～伸个腰～"),
        ],

        # 待机状态的互动
        AssistantState.IDLE: [
            (1, AssistantState.POKED, 1000, "嗯？怎么了？"),
            (2, AssistantState.POKED, 1000, "有什么事吗？"),
            (3, AssistantState.POKED_AGAIN, 1200, "你...你干嘛一直戳我..."),
            (5, AssistantState.ANNOYED, 1500, "好了好了！别戳了！"),
            (7, AssistantState.TICKLED, 1500, "哈哈哈，好痒！"),
        ],

        # 思考状态的互动
        AssistantState.THINKING: [
            (1, AssistantState.STARTLED, 1000, "啊！吓我一跳！"),
            (2, AssistantState.POKED, 1000, "等等，我在想事情..."),
            (3, AssistantState.ANNOYED, 1500, "别打扰我思考！"),
        ],

        # 开心状态的互动
        AssistantState.HAPPY: [
            (1, AssistantState.PATTED, 1500, "嘿嘿～"),
            (2, AssistantState.TICKLED, 1500, "好开心呀！"),
            (3, AssistantState.HUGGED, 2000, "抱抱～"),
        ],

        # 难过状态的互动
        AssistantState.SAD: [
            (1, AssistantState.PATTED, 2000, "谢谢你的安慰..."),
            (2, AssistantState.HUGGED, 2500, "呜...谢谢你陪着我..."),
            (3, AssistantState.HAPPY, 2000, "好多了，谢谢你！"),
        ],

        # 生气状态的互动
        AssistantState.ANGRY: [
            (1, AssistantState.ANNOYED, 1500, "哼！"),
            (2, AssistantState.ANNOYED, 1500, "还戳！"),
            (4, AssistantState.PATTED, 2000, "好啦...我不气了..."),
        ],

        # 深夜状态的互动
        AssistantState.MIDNIGHT: [
            (1, AssistantState.SLEEPY_DISTURBED, 1500, "这么晚还不睡？"),
            (2, AssistantState.DOZING, 2000, "我好困...你也早点休息吧..."),
        ],

        # 专注状态的互动
        AssistantState.FOCUSED: [
            (1, AssistantState.POKED, 1000, "嗯？"),
            (2, AssistantState.ANNOYED, 1500, "我在认真工作呢..."),
            (3, AssistantState.STARTLED, 1200, "啊！你打断我思路了！"),
        ],

        # 阅读状态的互动
        AssistantState.READING: [
            (1, AssistantState.CURIOUS, 1500, "这本书很有趣哦！"),
            (2, AssistantState.POKED, 1000, "嗯？有事？"),
            (3, AssistantState.ANNOYED, 1500, "让我看完这一页好不好..."),
        ],
    }

    # 特殊互动台词（根据好感度和互动次数）
    SPECIAL_DIALOGUES: Dict[str, List[str]] = {
        "high_affection_patted": [
            "最喜欢你了～",
            "嘿嘿，再摸摸～",
            "你的手好温暖...",
        ],
        "high_affection_hugged": [
            "我也好喜欢你！",
            "抱紧紧～",
            "不许放开哦！",
        ],
        "first_interaction": [
            "你好呀，第一次戳我吗？",
            "欢迎～以后请多多互动哦！",
        ],
    }

    def __init__(self):
        self.click_count = 0
        self.current_base_state = AssistantState.IDLE
        self.last_click_time = 0
        self.total_interactions = 0
        self.click_reset_delay = 5000  # 5秒无点击后重置计数

    def reset_click_count(self):
        """重置点击计数"""
        self.click_count = 0

    def on_state_changed(self, new_state: str):
        """当状态改变时调用"""
        # 只有非互动状态才更新基础状态
        if new_state not in [
            AssistantState.POKED, AssistantState.POKED_AGAIN,
            AssistantState.ANNOYED, AssistantState.STARTLED,
            AssistantState.TICKLED, AssistantState.PATTED,
            AssistantState.HUGGED, AssistantState.WAKING_UP,
            AssistantState.SLEEPY_DISTURBED, AssistantState.DOZING,
            AssistantState.STRETCHING
        ]:
            self.current_base_state = new_state
            self.click_count = 0

    def get_interaction(self, current_state: str, affection: int = 0) -> Optional[Tuple[str, int, str]]:
        """
        获取点击互动结果

        Args:
            current_state: 当前状态
            affection: 好感度

        Returns:
            (目标状态, 持续时间ms, 台词) 或 None
        """
        import time
        import random

        current_time = int(time.time() * 1000)

        # 检查是否需要重置点击计数
        if current_time - self.last_click_time > self.click_reset_delay:
            self.click_count = 0

        self.click_count += 1
        self.total_interactions += 1
        self.last_click_time = current_time

        # 获取互动链
        chain = self.INTERACTION_CHAINS.get(current_state)
        if not chain:
            # 没有定义互动链，使用默认反应
            chain = self.INTERACTION_CHAINS.get(AssistantState.IDLE, [])

        # 查找匹配的互动
        result = None
        for threshold, target_state, duration, dialogue in chain:
            if self.click_count >= threshold:
                result = (target_state, duration, dialogue)

        if not result:
            return None

        target_state, duration, dialogue = result

        # 高好感度特殊台词
        if affection >= 100:
            if target_state == AssistantState.PATTED:
                special = self.SPECIAL_DIALOGUES.get("high_affection_patted", [])
                if special:
                    dialogue = random.choice(special)
            elif target_state == AssistantState.HUGGED:
                special = self.SPECIAL_DIALOGUES.get("high_affection_hugged", [])
                if special:
                    dialogue = random.choice(special)

        # 第一次互动特殊台词
        if self.total_interactions == 1:
            special = self.SPECIAL_DIALOGUES.get("first_interaction", [])
            if special:
                dialogue = random.choice(special)

        return (target_state, duration, dialogue)

    def get_wake_up_sequence(self) -> List[Tuple[str, int, str]]:
        """
        获取完整的醒来动画序列

        Returns:
            [(状态, 持续时间ms, 台词), ...]
        """
        return [
            (AssistantState.SLEEPY_DISTURBED, 1000, "唔..."),
            (AssistantState.WAKING_UP, 1500, "嗯...几点了..."),
            (AssistantState.STRETCHING, 2000, "啊～伸个懒腰～"),
            (AssistantState.IDLE, 0, "好啦，我醒了！"),
        ]

    def should_fall_asleep(self) -> bool:
        """检查是否应该进入睡眠状态（长时间无互动）"""
        import time
        current_time = int(time.time() * 1000)
        idle_time = current_time - self.last_click_time

        # 超过10分钟无互动
        return idle_time > 600000