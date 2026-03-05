"""
悬浮助手 - 环境效果渲染器 (Environment Effects Renderer)
为立绘系统提供时间光照、天气效果、季节滤镜、心情色调等后处理效果
"""
import math
import random
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import logging

logger = logging.getLogger(__name__)


class TimeOfDay(Enum):
    """时段"""
    DAWN = "dawn"           # 黎明 (5-7)
    MORNING = "morning"     # 早晨 (7-10)
    NOON = "noon"           # 中午 (10-14)
    AFTERNOON = "afternoon" # 下午 (14-17)
    EVENING = "evening"     # 傍晚 (17-19)
    DUSK = "dusk"           # 黄昏 (19-21)
    NIGHT = "night"         # 夜晚 (21-5)


class Weather(Enum):
    """天气"""
    CLEAR = "clear"         # 晴朗
    CLOUDY = "cloudy"       # 多云
    OVERCAST = "overcast"   # 阴天
    RAIN_LIGHT = "rain_light"   # 小雨
    RAIN_HEAVY = "rain_heavy"   # 大雨
    SNOW_LIGHT = "snow_light"   # 小雪
    SNOW_HEAVY = "snow_heavy"   # 大雪
    FOG = "fog"             # 雾
    STORM = "storm"         # 暴风雨


class Season(Enum):
    """季节"""
    SPRING = "spring"       # 春
    SUMMER = "summer"       # 夏
    AUTUMN = "autumn"       # 秋
    WINTER = "winter"       # 冬


class MoodTone(Enum):
    """心情色调"""
    NEUTRAL = "neutral"     # 中性
    WARM = "warm"           # 温暖
    COOL = "cool"           # 冷淡
    ROMANTIC = "romantic"   # 浪漫
    MELANCHOLY = "melancholy"   # 忧郁
    ENERGETIC = "energetic"     # 活力
    MYSTERIOUS = "mysterious"   # 神秘
    DREAMY = "dreamy"       # 梦幻


@dataclass
class LightingConfig:
    """光照配置"""
    brightness: float = 1.0      # 亮度 (0-2)
    contrast: float = 1.0        # 对比度 (0-2)
    color_temp: int = 6500       # 色温 (K) (2700-10000)
    tint_color: Optional[Tuple[int, int, int]] = None  # 叠加色
    tint_opacity: float = 0.0    # 叠加色透明度
    saturation: float = 1.0      # 饱和度 (0-2)
    gamma: float = 1.0           # 伽马值


@dataclass
class ParticleConfig:
    """粒子效果配置"""
    particle_type: str = "rain"  # 粒子类型
    density: float = 1.0         # 密度
    speed: float = 1.0           # 速度
    angle: float = 0             # 角度（度）
    size_range: Tuple[int, int] = (2, 5)  # 大小范围
    color: Tuple[int, int, int, int] = (255, 255, 255, 128)  # 颜色


@dataclass
class EnvironmentState:
    """环境状态"""
    time_of_day: TimeOfDay = TimeOfDay.NOON
    weather: Weather = Weather.CLEAR
    season: Season = Season.SPRING
    mood_tone: MoodTone = MoodTone.NEUTRAL

    # 额外参数
    indoor: bool = False         # 是否室内
    ambient_light: float = 1.0   # 环境光强度
    custom_lighting: Optional[LightingConfig] = None


# ============ 时段光照预设 ============
TIME_LIGHTING_PRESETS: Dict[TimeOfDay, LightingConfig] = {
    TimeOfDay.DAWN: LightingConfig(
        brightness=0.85,
        contrast=0.95,
        color_temp=4000,
        tint_color=(255, 200, 150),
        tint_opacity=0.15,
        saturation=0.9
    ),
    TimeOfDay.MORNING: LightingConfig(
        brightness=1.0,
        contrast=1.0,
        color_temp=5500,
        tint_color=(255, 245, 230),
        tint_opacity=0.08,
        saturation=1.05
    ),
    TimeOfDay.NOON: LightingConfig(
        brightness=1.1,
        contrast=1.05,
        color_temp=6500,
        tint_color=None,
        tint_opacity=0,
        saturation=1.1
    ),
    TimeOfDay.AFTERNOON: LightingConfig(
        brightness=1.05,
        contrast=1.02,
        color_temp=5800,
        tint_color=(255, 240, 220),
        tint_opacity=0.05,
        saturation=1.05
    ),
    TimeOfDay.EVENING: LightingConfig(
        brightness=0.95,
        contrast=1.0,
        color_temp=4500,
        tint_color=(255, 180, 120),
        tint_opacity=0.2,
        saturation=1.0
    ),
    TimeOfDay.DUSK: LightingConfig(
        brightness=0.8,
        contrast=1.05,
        color_temp=3500,
        tint_color=(255, 130, 80),
        tint_opacity=0.25,
        saturation=0.95
    ),
    TimeOfDay.NIGHT: LightingConfig(
        brightness=0.6,
        contrast=0.9,
        color_temp=8000,
        tint_color=(100, 120, 180),
        tint_opacity=0.3,
        saturation=0.7
    ),
}

# ============ 天气效果配置 ============
WEATHER_EFFECTS: Dict[Weather, Dict[str, Any]] = {
    Weather.CLEAR: {
        "lighting_mod": {"brightness": 1.05, "saturation": 1.1},
        "particles": None,
        "overlay": None
    },
    Weather.CLOUDY: {
        "lighting_mod": {"brightness": 0.95, "contrast": 0.95, "saturation": 0.9},
        "particles": None,
        "overlay": {"color": (200, 200, 210), "opacity": 0.1}
    },
    Weather.OVERCAST: {
        "lighting_mod": {"brightness": 0.85, "contrast": 0.9, "saturation": 0.75},
        "particles": None,
        "overlay": {"color": (180, 180, 190), "opacity": 0.2}
    },
    Weather.RAIN_LIGHT: {
        "lighting_mod": {"brightness": 0.85, "contrast": 0.95, "saturation": 0.8},
        "particles": ParticleConfig("rain", density=0.5, speed=1.0, angle=10),
        "overlay": {"color": (150, 160, 180), "opacity": 0.15}
    },
    Weather.RAIN_HEAVY: {
        "lighting_mod": {"brightness": 0.7, "contrast": 0.9, "saturation": 0.6},
        "particles": ParticleConfig("rain", density=1.0, speed=1.5, angle=15),
        "overlay": {"color": (130, 140, 160), "opacity": 0.25}
    },
    Weather.SNOW_LIGHT: {
        "lighting_mod": {"brightness": 1.05, "contrast": 0.95, "saturation": 0.85},
        "particles": ParticleConfig("snow", density=0.5, speed=0.3, angle=5),
        "overlay": {"color": (230, 235, 245), "opacity": 0.1}
    },
    Weather.SNOW_HEAVY: {
        "lighting_mod": {"brightness": 0.95, "contrast": 0.9, "saturation": 0.7},
        "particles": ParticleConfig("snow", density=1.0, speed=0.5, angle=10),
        "overlay": {"color": (220, 225, 240), "opacity": 0.2}
    },
    Weather.FOG: {
        "lighting_mod": {"brightness": 0.9, "contrast": 0.7, "saturation": 0.6},
        "particles": None,
        "overlay": {"color": (220, 220, 230), "opacity": 0.35, "blur": 2}
    },
    Weather.STORM: {
        "lighting_mod": {"brightness": 0.5, "contrast": 1.1, "saturation": 0.5},
        "particles": ParticleConfig("rain", density=1.5, speed=2.0, angle=25),
        "overlay": {"color": (80, 90, 110), "opacity": 0.3}
    },
}

# ============ 季节滤镜 ============
SEASON_FILTERS: Dict[Season, Dict[str, Any]] = {
    Season.SPRING: {
        "tint": (255, 240, 245),  # 淡粉
        "tint_opacity": 0.08,
        "saturation": 1.1,
        "brightness": 1.02
    },
    Season.SUMMER: {
        "tint": (255, 250, 230),  # 暖黄
        "tint_opacity": 0.1,
        "saturation": 1.15,
        "brightness": 1.05
    },
    Season.AUTUMN: {
        "tint": (255, 220, 180),  # 橙调
        "tint_opacity": 0.12,
        "saturation": 1.05,
        "brightness": 0.98
    },
    Season.WINTER: {
        "tint": (220, 235, 255),  # 冷蓝
        "tint_opacity": 0.1,
        "saturation": 0.85,
        "brightness": 0.95
    },
}

# ============ 心情色调 ============
MOOD_TONES: Dict[MoodTone, Dict[str, Any]] = {
    MoodTone.NEUTRAL: {
        "tint": None,
        "saturation": 1.0,
        "brightness": 1.0,
        "contrast": 1.0
    },
    MoodTone.WARM: {
        "tint": (255, 230, 200),
        "tint_opacity": 0.15,
        "saturation": 1.1,
        "brightness": 1.02
    },
    MoodTone.COOL: {
        "tint": (200, 220, 255),
        "tint_opacity": 0.15,
        "saturation": 0.9,
        "brightness": 0.98
    },
    MoodTone.ROMANTIC: {
        "tint": (255, 200, 220),
        "tint_opacity": 0.2,
        "saturation": 1.15,
        "brightness": 1.0,
        "vignette": 0.3
    },
    MoodTone.MELANCHOLY: {
        "tint": (180, 190, 210),
        "tint_opacity": 0.2,
        "saturation": 0.7,
        "brightness": 0.9,
        "contrast": 0.95
    },
    MoodTone.ENERGETIC: {
        "tint": (255, 240, 200),
        "tint_opacity": 0.1,
        "saturation": 1.25,
        "brightness": 1.1,
        "contrast": 1.1
    },
    MoodTone.MYSTERIOUS: {
        "tint": (150, 130, 180),
        "tint_opacity": 0.2,
        "saturation": 0.8,
        "brightness": 0.85,
        "contrast": 1.1
    },
    MoodTone.DREAMY: {
        "tint": (230, 220, 255),
        "tint_opacity": 0.15,
        "saturation": 0.85,
        "brightness": 1.05,
        "blur": 1,
        "vignette": 0.2
    },
}


class EnvironmentEffectsRenderer:
    """
    环境效果渲染器

    功能:
    1. 时间光照效果
    2. 天气粒子和滤镜
    3. 季节色调
    4. 心情滤镜
    5. 自定义后处理
    """

    def __init__(self):
        self.current_state = EnvironmentState()

        # 粒子系统状态
        self._particles: List[Dict] = []
        self._particle_seed = 0

        # 缓存
        self._effect_cache: Dict[str, Image.Image] = {}
        self._cache_key: str = ""

        # 自动检测时间
        self.auto_time_detection = True

    def set_state(self, **kwargs):
        """设置环境状态"""
        if "time_of_day" in kwargs:
            self.current_state.time_of_day = kwargs["time_of_day"]
        if "weather" in kwargs:
            self.current_state.weather = kwargs["weather"]
        if "season" in kwargs:
            self.current_state.season = kwargs["season"]
        if "mood_tone" in kwargs:
            self.current_state.mood_tone = kwargs["mood_tone"]
        if "indoor" in kwargs:
            self.current_state.indoor = kwargs["indoor"]
        if "ambient_light" in kwargs:
            self.current_state.ambient_light = kwargs["ambient_light"]

        self._invalidate_cache()

    def auto_detect_time(self) -> TimeOfDay:
        """自动检测当前时段"""
        hour = datetime.now().hour

        if 5 <= hour < 7:
            return TimeOfDay.DAWN
        elif 7 <= hour < 10:
            return TimeOfDay.MORNING
        elif 10 <= hour < 14:
            return TimeOfDay.NOON
        elif 14 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 19:
            return TimeOfDay.EVENING
        elif 19 <= hour < 21:
            return TimeOfDay.DUSK
        else:
            return TimeOfDay.NIGHT

    def auto_detect_season(self) -> Season:
        """自动检测当前季节"""
        month = datetime.now().month

        if month in [3, 4, 5]:
            return Season.SPRING
        elif month in [6, 7, 8]:
            return Season.SUMMER
        elif month in [9, 10, 11]:
            return Season.AUTUMN
        else:
            return Season.WINTER

    def update_auto_state(self):
        """更新自动检测的状态"""
        if self.auto_time_detection:
            self.current_state.time_of_day = self.auto_detect_time()
            self.current_state.season = self.auto_detect_season()

    def apply_effects(self, image: Image.Image,
                     state: Optional[EnvironmentState] = None) -> Image.Image:
        """
        应用所有环境效果

        Args:
            image: 原始图像
            state: 环境状态（可选，默认使用当前状态）

        Returns:
            处理后的图像
        """
        state = state or self.current_state
        result = image.copy().convert("RGBA")

        # 1. 应用时间光照
        result = self._apply_time_lighting(result, state.time_of_day, state.indoor)

        # 2. 应用天气效果
        result = self._apply_weather_effects(result, state.weather)

        # 3. 应用季节滤镜
        result = self._apply_season_filter(result, state.season)

        # 4. 应用心情色调
        result = self._apply_mood_tone(result, state.mood_tone)

        # 5. 应用环境光强度
        if state.ambient_light != 1.0:
            result = self._adjust_ambient_light(result, state.ambient_light)

        # 6. 应用自定义光照（如果有）
        if state.custom_lighting:
            result = self._apply_custom_lighting(result, state.custom_lighting)

        return result

    def _apply_time_lighting(self, image: Image.Image,
                            time_of_day: TimeOfDay,
                            indoor: bool) -> Image.Image:
        """应用时间光照"""
        config = TIME_LIGHTING_PRESETS.get(time_of_day)
        if not config:
            return image

        result = image.copy()

        # 室内效果减弱
        intensity = 0.5 if indoor else 1.0

        # 亮度
        if config.brightness != 1.0:
            brightness_val = 1.0 + (config.brightness - 1.0) * intensity
            enhancer = ImageEnhance.Brightness(result)
            result = enhancer.enhance(brightness_val)

        # 对比度
        if config.contrast != 1.0:
            contrast_val = 1.0 + (config.contrast - 1.0) * intensity
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(contrast_val)

        # 饱和度
        if config.saturation != 1.0:
            sat_val = 1.0 + (config.saturation - 1.0) * intensity
            enhancer = ImageEnhance.Color(result)
            result = enhancer.enhance(sat_val)

        # 色温/着色
        if config.tint_color and config.tint_opacity > 0:
            opacity = config.tint_opacity * intensity
            result = self._apply_color_overlay(result, config.tint_color, opacity)

        return result

    def _apply_weather_effects(self, image: Image.Image,
                              weather: Weather) -> Image.Image:
        """应用天气效果"""
        effects = WEATHER_EFFECTS.get(weather)
        if not effects:
            return image

        result = image.copy()

        # 光照修改
        lighting_mod = effects.get("lighting_mod", {})
        if lighting_mod:
            if "brightness" in lighting_mod:
                enhancer = ImageEnhance.Brightness(result)
                result = enhancer.enhance(lighting_mod["brightness"])
            if "contrast" in lighting_mod:
                enhancer = ImageEnhance.Contrast(result)
                result = enhancer.enhance(lighting_mod["contrast"])
            if "saturation" in lighting_mod:
                enhancer = ImageEnhance.Color(result)
                result = enhancer.enhance(lighting_mod["saturation"])

        # 覆盖层
        overlay = effects.get("overlay")
        if overlay:
            color = overlay.get("color", (200, 200, 200))
            opacity = overlay.get("opacity", 0.1)
            blur = overlay.get("blur", 0)

            result = self._apply_color_overlay(result, color, opacity)

            if blur > 0:
                result = result.filter(ImageFilter.GaussianBlur(radius=blur))

        # 粒子效果（生成静态粒子层）
        particles_config = effects.get("particles")
        if particles_config:
            particle_layer = self._generate_particle_layer(
                result.size, particles_config
            )
            result = Image.alpha_composite(result, particle_layer)

        return result

    def _apply_season_filter(self, image: Image.Image,
                            season: Season) -> Image.Image:
        """应用季节滤镜"""
        filter_config = SEASON_FILTERS.get(season)
        if not filter_config:
            return image

        result = image.copy()

        # 着色
        tint = filter_config.get("tint")
        opacity = filter_config.get("tint_opacity", 0)
        if tint and opacity > 0:
            result = self._apply_color_overlay(result, tint, opacity)

        # 饱和度
        saturation = filter_config.get("saturation", 1.0)
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(result)
            result = enhancer.enhance(saturation)

        # 亮度
        brightness = filter_config.get("brightness", 1.0)
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(result)
            result = enhancer.enhance(brightness)

        return result

    def _apply_mood_tone(self, image: Image.Image,
                        mood: MoodTone) -> Image.Image:
        """应用心情色调"""
        tone_config = MOOD_TONES.get(mood)
        if not tone_config:
            return image

        result = image.copy()

        # 着色
        tint = tone_config.get("tint")
        opacity = tone_config.get("tint_opacity", 0)
        if tint and opacity > 0:
            result = self._apply_color_overlay(result, tint, opacity)

        # 饱和度
        saturation = tone_config.get("saturation", 1.0)
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(result)
            result = enhancer.enhance(saturation)

        # 亮度
        brightness = tone_config.get("brightness", 1.0)
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(result)
            result = enhancer.enhance(brightness)

        # 对比度
        contrast = tone_config.get("contrast", 1.0)
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(contrast)

        # 模糊
        blur = tone_config.get("blur", 0)
        if blur > 0:
            result = result.filter(ImageFilter.GaussianBlur(radius=blur))

        # 暗角
        vignette = tone_config.get("vignette", 0)
        if vignette > 0:
            result = self._apply_vignette(result, vignette)

        return result

    def _apply_custom_lighting(self, image: Image.Image,
                              config: LightingConfig) -> Image.Image:
        """应用自定义光照"""
        result = image.copy()

        if config.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(result)
            result = enhancer.enhance(config.brightness)

        if config.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(config.contrast)

        if config.saturation != 1.0:
            enhancer = ImageEnhance.Color(result)
            result = enhancer.enhance(config.saturation)

        if config.tint_color and config.tint_opacity > 0:
            result = self._apply_color_overlay(
                result, config.tint_color, config.tint_opacity
            )

        return result

    def _adjust_ambient_light(self, image: Image.Image,
                             intensity: float) -> Image.Image:
        """调整环境光强度"""
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(intensity)

    def _apply_color_overlay(self, image: Image.Image,
                            color: Tuple[int, int, int],
                            opacity: float) -> Image.Image:
        """应用颜色叠加"""
        if opacity <= 0:
            return image

        result = image.copy()
        overlay = Image.new("RGBA", image.size, (*color, int(255 * opacity)))

        # 使用柔光混合模式的简化版本
        result = Image.alpha_composite(result, overlay)

        return result

    def _apply_vignette(self, image: Image.Image,
                       strength: float) -> Image.Image:
        """应用暗角效果"""
        width, height = image.size
        result = image.copy()

        # 创建暗角遮罩
        mask = Image.new("L", (width, height), 255)
        draw = ImageDraw.Draw(mask)

        center_x, center_y = width // 2, height // 2
        max_dist = math.sqrt(center_x ** 2 + center_y ** 2)

        # 绘制渐变
        for y in range(height):
            for x in range(width):
                dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                normalized = dist / max_dist
                # 从边缘开始变暗
                if normalized > 0.5:
                    darkness = int((normalized - 0.5) * 2 * strength * 255)
                    current = mask.getpixel((x, y))
                    mask.putpixel((x, y), max(0, current - darkness))

        # 应用遮罩
        dark_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        dark_solid = Image.new("RGBA", image.size, (0, 0, 0, 255))

        # 反转遮罩用于暗角
        inv_mask = Image.eval(mask, lambda x: 255 - x)
        dark_layer.paste(dark_solid, mask=inv_mask)

        result = Image.alpha_composite(result, dark_layer)

        return result

    def _generate_particle_layer(self, size: Tuple[int, int],
                                config: ParticleConfig) -> Image.Image:
        """生成粒子效果层"""
        width, height = size
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        # 计算粒子数量
        base_count = int((width * height) / 5000)  # 基础密度
        particle_count = int(base_count * config.density)

        random.seed(self._particle_seed)

        if config.particle_type == "rain":
            # 雨滴
            angle_rad = math.radians(config.angle)
            for _ in range(particle_count):
                x = random.randint(0, width)
                y = random.randint(0, height)
                length = random.randint(10, 25) * config.speed

                # 计算终点
                end_x = x + int(length * math.sin(angle_rad))
                end_y = y + int(length * math.cos(angle_rad))

                # 绘制雨滴
                draw.line(
                    [(x, y), (end_x, end_y)],
                    fill=(200, 210, 230, random.randint(80, 150)),
                    width=1
                )

        elif config.particle_type == "snow":
            # 雪花
            for _ in range(particle_count):
                x = random.randint(0, width)
                y = random.randint(0, height)
                size_val = random.randint(*config.size_range)

                # 绘制雪花（简单圆形）
                alpha = random.randint(100, 200)
                draw.ellipse(
                    [x - size_val, y - size_val, x + size_val, y + size_val],
                    fill=(255, 255, 255, alpha)
                )

        # 更新种子以便下次生成不同位置
        self._particle_seed += 1

        return layer

    def _invalidate_cache(self):
        """使缓存失效"""
        self._effect_cache.clear()
        self._cache_key = ""

    def get_current_state_description(self) -> str:
        """获取当前状态描述"""
        state = self.current_state
        parts = []

        time_names = {
            TimeOfDay.DAWN: "黎明",
            TimeOfDay.MORNING: "早晨",
            TimeOfDay.NOON: "中午",
            TimeOfDay.AFTERNOON: "下午",
            TimeOfDay.EVENING: "傍晚",
            TimeOfDay.DUSK: "黄昏",
            TimeOfDay.NIGHT: "夜晚",
        }
        parts.append(time_names.get(state.time_of_day, "未知"))

        weather_names = {
            Weather.CLEAR: "晴",
            Weather.CLOUDY: "多云",
            Weather.OVERCAST: "阴",
            Weather.RAIN_LIGHT: "小雨",
            Weather.RAIN_HEAVY: "大雨",
            Weather.SNOW_LIGHT: "小雪",
            Weather.SNOW_HEAVY: "大雪",
            Weather.FOG: "雾",
            Weather.STORM: "暴风雨",
        }
        parts.append(weather_names.get(state.weather, ""))

        season_names = {
            Season.SPRING: "春",
            Season.SUMMER: "夏",
            Season.AUTUMN: "秋",
            Season.WINTER: "冬",
        }
        parts.append(season_names.get(state.season, ""))

        return " · ".join(filter(None, parts))


class DynamicLightingController:
    """
    动态光照控制器

    支持光照的平滑过渡和自动变化
    """

    def __init__(self, renderer: EnvironmentEffectsRenderer):
        self.renderer = renderer

        # 过渡状态
        self._transitioning = False
        self._transition_progress = 0.0
        self._transition_duration = 2.0  # 秒
        self._from_state: Optional[EnvironmentState] = None
        self._to_state: Optional[EnvironmentState] = None

        # 回调
        self.on_state_changed: Optional[Callable[[EnvironmentState], None]] = None

    def start_transition(self, to_state: EnvironmentState, duration: float = 2.0):
        """开始状态过渡"""
        self._from_state = EnvironmentState(
            time_of_day=self.renderer.current_state.time_of_day,
            weather=self.renderer.current_state.weather,
            season=self.renderer.current_state.season,
            mood_tone=self.renderer.current_state.mood_tone,
            indoor=self.renderer.current_state.indoor,
            ambient_light=self.renderer.current_state.ambient_light
        )
        self._to_state = to_state
        self._transition_progress = 0.0
        self._transition_duration = duration
        self._transitioning = True

    def update(self, delta_time: float):
        """更新过渡状态"""
        if not self._transitioning:
            return

        self._transition_progress += delta_time / self._transition_duration

        if self._transition_progress >= 1.0:
            self._transition_progress = 1.0
            self._transitioning = False

            # 应用最终状态
            self.renderer.current_state = self._to_state

            if self.on_state_changed:
                self.on_state_changed(self._to_state)

    def get_interpolated_ambient_light(self) -> float:
        """获取插值后的环境光"""
        if not self._transitioning or not self._from_state or not self._to_state:
            return self.renderer.current_state.ambient_light

        from_light = self._from_state.ambient_light
        to_light = self._to_state.ambient_light

        # 使用缓动函数
        t = self._ease_in_out(self._transition_progress)
        return from_light + (to_light - from_light) * t

    def _ease_in_out(self, t: float) -> float:
        """缓入缓出函数"""
        if t < 0.5:
            return 2 * t * t
        else:
            return 1 - (-2 * t + 2) ** 2 / 2

    @property
    def is_transitioning(self) -> bool:
        return self._transitioning


class SpecialEffectsLibrary:
    """
    特殊效果库

    提供预定义的特殊场景效果
    """

    # 特殊场景预设
    PRESETS: Dict[str, EnvironmentState] = {
        "sunset_romantic": EnvironmentState(
            time_of_day=TimeOfDay.DUSK,
            weather=Weather.CLEAR,
            season=Season.AUTUMN,
            mood_tone=MoodTone.ROMANTIC
        ),
        "rainy_melancholy": EnvironmentState(
            time_of_day=TimeOfDay.AFTERNOON,
            weather=Weather.RAIN_LIGHT,
            season=Season.AUTUMN,
            mood_tone=MoodTone.MELANCHOLY
        ),
        "snowy_dreamy": EnvironmentState(
            time_of_day=TimeOfDay.EVENING,
            weather=Weather.SNOW_LIGHT,
            season=Season.WINTER,
            mood_tone=MoodTone.DREAMY
        ),
        "morning_energetic": EnvironmentState(
            time_of_day=TimeOfDay.MORNING,
            weather=Weather.CLEAR,
            season=Season.SPRING,
            mood_tone=MoodTone.ENERGETIC
        ),
        "night_mysterious": EnvironmentState(
            time_of_day=TimeOfDay.NIGHT,
            weather=Weather.FOG,
            season=Season.AUTUMN,
            mood_tone=MoodTone.MYSTERIOUS
        ),
        "summer_noon": EnvironmentState(
            time_of_day=TimeOfDay.NOON,
            weather=Weather.CLEAR,
            season=Season.SUMMER,
            mood_tone=MoodTone.ENERGETIC
        ),
        "cozy_indoor": EnvironmentState(
            time_of_day=TimeOfDay.EVENING,
            weather=Weather.RAIN_LIGHT,
            season=Season.AUTUMN,
            mood_tone=MoodTone.WARM,
            indoor=True
        ),
    }

    @classmethod
    def get_preset(cls, name: str) -> Optional[EnvironmentState]:
        """获取预设场景"""
        return cls.PRESETS.get(name)

    @classmethod
    def get_preset_names(cls) -> List[str]:
        """获取所有预设名称"""
        return list(cls.PRESETS.keys())

    @classmethod
    def get_mood_for_emotion(cls, emotion: str) -> MoodTone:
        """根据情绪获取对应的心情色调"""
        emotion_mood_map = {
            # 正面情绪
            "happy": MoodTone.WARM,
            "excited": MoodTone.ENERGETIC,
            "love": MoodTone.ROMANTIC,
            "peaceful": MoodTone.DREAMY,

            # 负面情绪
            "sad": MoodTone.MELANCHOLY,
            "angry": MoodTone.COOL,
            "scared": MoodTone.MYSTERIOUS,
            "lonely": MoodTone.MELANCHOLY,

            # 中性情绪
            "neutral": MoodTone.NEUTRAL,
            "thinking": MoodTone.COOL,
            "surprised": MoodTone.NEUTRAL,
        }
        return emotion_mood_map.get(emotion.lower(), MoodTone.NEUTRAL)


# 便捷函数
def create_environment_renderer() -> EnvironmentEffectsRenderer:
    """创建环境效果渲染器"""
    renderer = EnvironmentEffectsRenderer()
    renderer.update_auto_state()
    return renderer


def apply_quick_effect(image: Image.Image,
                      preset_name: str) -> Image.Image:
    """快速应用预设效果"""
    renderer = EnvironmentEffectsRenderer()
    state = SpecialEffectsLibrary.get_preset(preset_name)
    if state:
        return renderer.apply_effects(image, state)
    return image
