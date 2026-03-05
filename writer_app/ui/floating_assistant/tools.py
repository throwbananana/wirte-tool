"""
悬浮写作助手 - 写作工具模块
包含起名器、骰子、计时器、角色卡生成器等
"""
import random
import time
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

from .constants import (
    CHINESE_SURNAMES, CHINESE_NAMES_MALE, CHINESE_NAMES_FEMALE,
    ENGLISH_SURNAMES, ENGLISH_NAMES_MALE, ENGLISH_NAMES_FEMALE,
    JAPANESE_SURNAMES, JAPANESE_NAMES_MALE, JAPANESE_NAMES_FEMALE,
    FANTASY_PREFIXES, FANTASY_ELEMENTS, FANTASY_SUFFIXES,
    WRITING_PROMPTS, CHARACTER_TEMPLATES, SCENE_TEMPLATES,
    FOODS, get_all_prompts
)


class NameType(Enum):
    """名字类型"""
    CHINESE = "chinese"
    ENGLISH = "english"
    JAPANESE = "japanese"
    FANTASY = "fantasy"


class Gender(Enum):
    """性别"""
    MALE = "male"
    FEMALE = "female"
    ANY = "any"


class NameGenerator:
    """名字生成器"""

    @classmethod
    def generate(cls, name_type: NameType, gender: Gender = Gender.ANY, count: int = 5) -> List[str]:
        """
        生成名字

        Args:
            name_type: 名字类型
            gender: 性别倾向
            count: 生成数量

        Returns:
            名字列表
        """
        names = []
        for _ in range(count):
            if name_type == NameType.CHINESE:
                names.append(cls._generate_chinese(gender))
            elif name_type == NameType.ENGLISH:
                names.append(cls._generate_english(gender))
            elif name_type == NameType.JAPANESE:
                names.append(cls._generate_japanese(gender))
            elif name_type == NameType.FANTASY:
                names.append(cls._generate_fantasy())
        return names

    @classmethod
    def _generate_chinese(cls, gender: Gender) -> str:
        """生成中文名"""
        surname = random.choice(CHINESE_SURNAMES)

        if gender == Gender.MALE:
            given_pool = CHINESE_NAMES_MALE
        elif gender == Gender.FEMALE:
            given_pool = CHINESE_NAMES_FEMALE
        else:
            given_pool = CHINESE_NAMES_MALE + CHINESE_NAMES_FEMALE

        # 随机决定单名还是双名
        if random.random() < 0.4:
            return surname + random.choice(given_pool)
        else:
            given1 = random.choice(given_pool)
            given2 = random.choice(given_pool)
            return surname + given1 + given2

    @classmethod
    def _generate_english(cls, gender: Gender) -> str:
        """生成英文名"""
        surname = random.choice(ENGLISH_SURNAMES)

        if gender == Gender.MALE:
            given = random.choice(ENGLISH_NAMES_MALE)
        elif gender == Gender.FEMALE:
            given = random.choice(ENGLISH_NAMES_FEMALE)
        else:
            given = random.choice(ENGLISH_NAMES_MALE + ENGLISH_NAMES_FEMALE)

        return f"{given} {surname}"

    @classmethod
    def _generate_japanese(cls, gender: Gender) -> str:
        """生成日式名"""
        surname = random.choice(JAPANESE_SURNAMES)

        if gender == Gender.MALE:
            given = random.choice(JAPANESE_NAMES_MALE)
        elif gender == Gender.FEMALE:
            given = random.choice(JAPANESE_NAMES_FEMALE)
        else:
            given = random.choice(JAPANESE_NAMES_MALE + JAPANESE_NAMES_FEMALE)

        return f"{surname} {given}"

    @classmethod
    def _generate_fantasy(cls) -> str:
        """生成奇幻/武侠名"""
        style = random.choice(["prefix_element", "element_suffix", "full", "double_element"])

        if style == "prefix_element":
            return random.choice(FANTASY_PREFIXES) + random.choice(FANTASY_ELEMENTS)
        elif style == "element_suffix":
            return random.choice(FANTASY_ELEMENTS) + random.choice(FANTASY_SUFFIXES)
        elif style == "double_element":
            return random.choice(FANTASY_ELEMENTS) + random.choice(FANTASY_ELEMENTS)
        else:
            return (random.choice(FANTASY_PREFIXES) +
                    random.choice(FANTASY_ELEMENTS) +
                    random.choice(FANTASY_SUFFIXES))

    @classmethod
    def generate_nickname(cls, base_name: str) -> List[str]:
        """生成昵称"""
        nicknames = []

        # 叠字昵称
        if len(base_name) >= 2:
            nicknames.append(base_name[-1] + base_name[-1])
            nicknames.append("小" + base_name[-1])
            nicknames.append("阿" + base_name[-1])

        # 尊称
        if len(base_name) >= 2:
            nicknames.append(base_name[-2:] + "哥")
            nicknames.append(base_name[-2:] + "姐")

        return nicknames


class DiceRoller:
    """骰子工具"""

    DICE_FACES = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

    @classmethod
    def roll(cls, sides: int = 6, count: int = 1) -> List[int]:
        """
        投掷骰子

        Args:
            sides: 面数
            count: 骰子数量

        Returns:
            投掷结果列表
        """
        return [random.randint(1, sides) for _ in range(count)]

    @classmethod
    def roll_d6_visual(cls) -> Tuple[int, str]:
        """投掷D6并返回可视化结果"""
        result = random.randint(1, 6)
        return result, cls.DICE_FACES[result - 1]

    @classmethod
    def roll_multiple_visual(cls, count: int = 3) -> Tuple[List[int], str]:
        """投掷多个D6"""
        results = cls.roll(6, count)
        faces = " ".join(cls.DICE_FACES[r - 1] for r in results)
        return results, faces

    @classmethod
    def make_choice(cls, options: List[str]) -> Tuple[int, str]:
        """随机选择"""
        if not options:
            return -1, ""
        idx = random.randint(0, len(options) - 1)
        return idx, options[idx]


@dataclass
class TimerState:
    """计时器状态"""
    running: bool = False
    paused: bool = False
    start_time: float = 0
    pause_time: float = 0
    duration: int = 0  # 秒
    elapsed_when_paused: float = 0


class PomodoroTimer:
    """番茄钟计时器"""

    DEFAULT_WORK_MINUTES = 25
    DEFAULT_BREAK_MINUTES = 5
    DEFAULT_LONG_BREAK_MINUTES = 15

    def __init__(self):
        self.state = TimerState()
        self._on_complete: Optional[Callable[[], None]] = None
        self._on_tick: Optional[Callable[[int, int], None]] = None
        self.completed_count = 0

    def on_complete(self, callback: Callable[[], None]):
        """设置完成回调"""
        self._on_complete = callback

    def on_tick(self, callback: Callable[[int, int], None]):
        """设置每秒回调 (remaining_seconds, total_seconds)"""
        self._on_tick = callback

    def start(self, minutes: int = DEFAULT_WORK_MINUTES):
        """开始计时"""
        self.state = TimerState(
            running=True,
            start_time=time.time(),
            duration=minutes * 60
        )

    def pause(self):
        """暂停"""
        if self.state.running and not self.state.paused:
            self.state.paused = True
            self.state.pause_time = time.time()
            self.state.elapsed_when_paused = self.state.pause_time - self.state.start_time

    def resume(self):
        """继续"""
        if self.state.running and self.state.paused:
            self.state.paused = False
            # 调整开始时间以补偿暂停时间
            pause_duration = time.time() - self.state.pause_time
            self.state.start_time += pause_duration

    def stop(self):
        """停止"""
        self.state = TimerState()

    def get_remaining(self) -> int:
        """获取剩余秒数"""
        if not self.state.running:
            return 0

        if self.state.paused:
            elapsed = self.state.elapsed_when_paused
        else:
            elapsed = time.time() - self.state.start_time

        remaining = self.state.duration - int(elapsed)
        return max(0, remaining)

    def is_complete(self) -> bool:
        """是否完成"""
        return self.state.running and self.get_remaining() <= 0

    def format_remaining(self) -> str:
        """格式化剩余时间"""
        remaining = self.get_remaining()
        minutes = remaining // 60
        seconds = remaining % 60
        return f"{minutes:02d}:{seconds:02d}"

    def complete(self):
        """标记完成"""
        self.completed_count += 1
        self.stop()
        if self._on_complete:
            self._on_complete()


class PromptCardDrawer:
    """写作提示卡抽取器"""

    def __init__(self, config_dir=None):
        self.config_dir = config_dir
        self._drawn_history: List[str] = []
        self._favorites: List[str] = []

    def draw(self, avoid_recent: int = 5) -> str:
        """
        抽取提示卡

        Args:
            avoid_recent: 避免最近抽到的N张

        Returns:
            提示内容
        """
        all_prompts = get_all_prompts(self.config_dir)

        # 过滤最近抽过的
        available = [p for p in all_prompts if p not in self._drawn_history[-avoid_recent:]]
        if not available:
            available = all_prompts

        prompt = random.choice(available)
        self._drawn_history.append(prompt)

        return prompt

    def add_favorite(self, prompt: str):
        """收藏提示卡"""
        if prompt not in self._favorites:
            self._favorites.append(prompt)

    def remove_favorite(self, prompt: str):
        """取消收藏"""
        if prompt in self._favorites:
            self._favorites.remove(prompt)

    def get_favorites(self) -> List[str]:
        """获取收藏列表"""
        return self._favorites.copy()

    def draw_by_category(self, category: str) -> str:
        """按类别抽取"""
        # 根据关键词分类
        categories = {
            "scene": ["描写", "场景", "画面"],
            "emotion": ["情感", "心情", "内心"],
            "character": ["角色", "人物", "性格"],
            "dialogue": ["对话", "交谈", "说"],
            "challenge": ["挑战", "用", "只用"],
        }

        keywords = categories.get(category, [])
        all_prompts = get_all_prompts(self.config_dir)

        matching = [p for p in all_prompts if any(k in p for k in keywords)]
        if not matching:
            matching = all_prompts

        return random.choice(matching)


class CharacterCardGenerator:
    """角色卡生成器"""

    @classmethod
    def generate_basic(cls, name_type: NameType = NameType.CHINESE,
                        gender: Gender = Gender.ANY) -> Dict[str, str]:
        """生成基础角色卡"""
        name = NameGenerator.generate(name_type, gender, 1)[0]

        # 随机年龄
        age_ranges = [(18, 25), (25, 35), (35, 50), (15, 18)]
        age_range = random.choice(age_ranges)
        age = random.randint(*age_range)

        # 随机性格特征
        personalities = [
            "开朗", "内向", "温和", "急躁", "理性", "感性",
            "乐观", "悲观", "谨慎", "冲动", "冷静", "热情",
            "独立", "依赖", "坚强", "敏感", "幽默", "严肃"
        ]

        # 随机特长
        skills = [
            "音乐", "绘画", "写作", "运动", "烹饪", "编程",
            "演讲", "手工", "游戏", "摄影", "舞蹈", "武术",
            "语言", "科学", "历史", "医学", "商业", "法律"
        ]

        return {
            "姓名": name,
            "年龄": str(age),
            "性别": "男" if gender == Gender.MALE else "女" if gender == Gender.FEMALE else random.choice(["男", "女"]),
            "性格": random.choice(personalities) + "、" + random.choice(personalities),
            "特长": random.choice(skills),
            "外貌特征": cls._generate_appearance(),
        }

    @classmethod
    def _generate_appearance(cls) -> str:
        """生成外貌描述"""
        hair = random.choice(["黑色长发", "棕色短发", "金色卷发", "银白长发", "深蓝短发", "红色马尾"])
        eyes = random.choice(["黑色眼眸", "棕色眼睛", "蓝色眼睛", "绿色眼睛", "金色瞳孔", "紫色眼眸"])
        feature = random.choice(["戴眼镜", "有小虎牙", "脸上有痣", "总是微笑", "眉头紧锁", "面无表情"])
        return f"{hair}，{eyes}，{feature}"

    @classmethod
    def generate_from_template(cls, template_name: str) -> Dict[str, str]:
        """从模板生成角色卡"""
        template = CHARACTER_TEMPLATES.get(template_name)
        if not template:
            return cls.generate_basic()

        card = {}
        for field in template["fields"]:
            card[field] = ""  # 留空让用户填写

        # 预填充名字
        card["姓名"] = NameGenerator.generate(NameType.CHINESE, Gender.ANY, 1)[0]

        return card


class SceneGenerator:
    """场景生成器"""

    # 用于存储当前真实天气（由外部设置）
    _real_weather: Optional[str] = None

    @classmethod
    def set_real_weather(cls, weather: str):
        """
        设置真实天气（由天气服务调用）

        Args:
            weather: 真实天气描述，如 "晴朗"、"下雨"
        """
        cls._real_weather = weather

    @classmethod
    def get_real_weather(cls) -> Optional[str]:
        """获取当前真实天气"""
        return cls._real_weather

    @classmethod
    def generate_random(cls, category: str = None,
                        use_real_weather: bool = True) -> Dict[str, str]:
        """
        生成随机场景

        Args:
            category: 场景类别 (indoor/outdoor/fantasy/scifi)
            use_real_weather: 是否使用真实天气（默认True）

        Returns:
            场景信息字典
        """
        if category and category in SCENE_TEMPLATES:
            location = random.choice(SCENE_TEMPLATES[category])
        else:
            all_locations = []
            for locs in SCENE_TEMPLATES.values():
                all_locations.extend(locs)
            location = random.choice(all_locations)

        # 时间
        times = ["清晨", "上午", "中午", "下午", "黄昏", "傍晚", "深夜", "凌晨"]
        time_of_day = random.choice(times)

        # 天气 - 优先使用真实天气
        if use_real_weather and cls._real_weather:
            weather = cls._real_weather
        else:
            weathers = ["晴朗", "多云", "阴天", "小雨", "大雨", "雷电", "下雪", "大雾", "微风"]
            weather = random.choice(weathers)

        # 氛围
        atmospheres = ["宁静", "热闹", "紧张", "神秘", "浪漫", "诡异", "温馨", "压抑", "活力"]
        atmosphere = random.choice(atmospheres)

        return {
            "地点": location,
            "时间": time_of_day,
            "天气": weather,
            "氛围": atmosphere,
        }

    @classmethod
    def generate_description(cls, scene: Dict[str, str]) -> str:
        """根据场景信息生成描述"""
        return f"{scene['时间']}的{scene['地点']}，{scene['天气']}，{scene['氛围']}的气氛。"


class WordCounter:
    """字数统计工具"""

    @classmethod
    def count(cls, text: str) -> Dict[str, int]:
        """
        统计字数

        Returns:
            {
                "characters": 总字符数,
                "characters_no_space": 不含空格字符数,
                "chinese": 中文字符数,
                "english_words": 英文单词数,
                "numbers": 数字数,
                "punctuation": 标点数,
                "lines": 行数,
                "paragraphs": 段落数,
            }
        """
        import re

        text = text or ""

        # 总字符
        total = len(text)
        no_space = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

        # 中文字符
        chinese = len(re.findall(r'[\u4e00-\u9fff]', text))

        # 英文单词
        english_words = len(re.findall(r'[a-zA-Z]+', text))

        # 数字
        numbers = len(re.findall(r'\d+', text))

        # 标点 (使用双反斜杠转义方括号)
        punctuation = len(re.findall(r"[，。！？、；：""''（）【】《》—…·,.!?;:'\"()\\[\\]<>-]", text))

        # 行数
        lines = len(text.split('\n'))

        # 段落数（以空行分隔）
        paragraphs = len([p for p in text.split('\n\n') if p.strip()])

        return {
            "characters": total,
            "characters_no_space": no_space,
            "chinese": chinese,
            "english_words": english_words,
            "numbers": numbers,
            "punctuation": punctuation,
            "lines": lines,
            "paragraphs": paragraphs,
        }

    @classmethod
    def estimate_reading_time(cls, text: str, wpm: int = 300) -> int:
        """估算阅读时间（分钟）"""
        stats = cls.count(text)
        # 中文按每分钟300字，英文按每分钟200词
        chinese_time = stats["chinese"] / wpm
        english_time = stats["english_words"] / 200
        return max(1, int(chinese_time + english_time))


class FoodSelector:
    """食物选择器（用于喂食）"""

    @classmethod
    def select_random(cls) -> Tuple[str, Dict]:
        """
        随机选择食物（带稀有度权重）

        Returns:
            (food_id, food_data)
        """
        # 稀有度权重
        rarity_weights = {"common": 70, "rare": 25, "legendary": 5}
        roll = random.randint(1, 100)

        if roll <= rarity_weights["legendary"]:
            rarity = "legendary"
        elif roll <= rarity_weights["legendary"] + rarity_weights["rare"]:
            rarity = "rare"
        else:
            rarity = "common"

        available = [(fid, fdata) for fid, fdata in FOODS.items()
                     if fdata["rarity"] == rarity]

        if not available:
            available = list(FOODS.items())

        food_id, food_data = random.choice(available)
        return food_id, food_data

    @classmethod
    def get_by_rarity(cls, rarity: str) -> List[Tuple[str, Dict]]:
        """按稀有度获取食物列表"""
        return [(fid, fdata) for fid, fdata in FOODS.items()
                if fdata["rarity"] == rarity]
