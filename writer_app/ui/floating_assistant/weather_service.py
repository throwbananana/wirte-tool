"""
悬浮写作助手 - 天气服务模块
使用和风天气 API 获取实时天气数据
"""
import time
import json
import gzip
import logging
import threading
import random
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from writer_app.core.thread_pool import get_ai_thread_pool

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """天气数据"""
    code: str = ""           # 天气代码
    text: str = ""           # 天气描述文字
    temp: str = ""           # 温度
    feels_like: str = ""     # 体感温度
    icon: str = ""           # 天气图标代码
    wind_dir: str = ""       # 风向
    wind_scale: str = ""     # 风力等级
    humidity: str = ""       # 相对湿度
    precip: str = ""         # 降水量
    vis: str = ""            # 能见度
    update_time: str = ""    # 更新时间
    location_name: str = ""  # 城市名称


class WeatherService:
    """
    和风天气 API 服务

    API 文档: https://dev.qweather.com/docs/api/weather/weather-now/
    """

    # 和风天气使用用户专属 API Host (2026年起新格式)
    # API Host 格式: abcxyz.qweatherapi.com
    # 认证方式: 请求头 X-QW-Api-Key

    # 天气代码到助手状态的映射
    WEATHER_CODE_MAPPING = {
        # 晴天
        "100": "sunny",
        "150": "sunny",  # 晴(夜间)

        # 多云
        "101": "cloudy",
        "102": "cloudy",
        "103": "cloudy",
        "104": "cloudy",
        "151": "cloudy",
        "152": "cloudy",
        "153": "cloudy",

        # 雨
        "300": "rainy",  # 阵雨
        "301": "rainy",  # 强阵雨
        "305": "rainy",  # 小雨
        "306": "rainy",  # 中雨
        "307": "rainy",  # 大雨
        "308": "rainy",  # 极端降雨
        "309": "rainy",  # 毛毛雨
        "310": "rainy",  # 暴雨
        "311": "rainy",  # 大暴雨
        "312": "rainy",  # 特大暴雨
        "313": "rainy",  # 冻雨
        "314": "rainy",  # 小到中雨
        "315": "rainy",  # 中到大雨
        "316": "rainy",  # 大到暴雨
        "317": "rainy",  # 暴雨到大暴雨
        "318": "rainy",  # 大暴雨到特大暴雨
        "350": "rainy",  # 阵雨(夜间)
        "351": "rainy",  # 强阵雨(夜间)

        # 雷暴
        "302": "stormy",  # 雷阵雨
        "303": "stormy",  # 强雷阵雨
        "304": "stormy",  # 雷阵雨伴有冰雹

        # 雪
        "400": "snowy",  # 小雪
        "401": "snowy",  # 中雪
        "402": "snowy",  # 大雪
        "403": "snowy",  # 暴雪
        "404": "snowy",  # 雨夹雪
        "405": "snowy",  # 雨雪天气
        "406": "snowy",  # 阵雨夹雪
        "407": "snowy",  # 阵雪
        "408": "snowy",  # 小到中雪
        "409": "snowy",  # 中到大雪
        "410": "snowy",  # 大到暴雪
        "456": "snowy",  # 阵雨夹雪(夜间)
        "457": "snowy",  # 阵雪(夜间)

        # 雾/霾
        "500": "foggy",  # 薄雾
        "501": "foggy",  # 雾
        "502": "foggy",  # 霾
        "503": "foggy",  # 扬沙
        "504": "foggy",  # 浮尘
        "507": "foggy",  # 沙尘暴
        "508": "foggy",  # 强沙尘暴
        "509": "foggy",  # 浓雾
        "510": "foggy",  # 强浓雾
        "511": "foggy",  # 中度霾
        "512": "foggy",  # 重度霾
        "513": "foggy",  # 严重霾
        "514": "foggy",  # 大雾
        "515": "foggy",  # 特强浓雾
    }

    # 天气状态到中文描述
    STATE_TO_TEXT = {
        "sunny": "晴朗",
        "cloudy": "多云",
        "rainy": "下雨",
        "stormy": "雷暴",
        "snowy": "下雪",
        "foggy": "雾霾",
    }

    def __init__(self, api_key: str = "", api_host: str = "", location: str = "101010100"):
        """
        初始化天气服务

        Args:
            api_key: 和风天气 API Key
            api_host: 用户专属 API Host (如 abcxyz.qweatherapi.com)
            location: 城市 ID 或坐标 (经度,纬度)
        """
        self.api_key = api_key
        self.api_host = api_host
        self.location = location
        self.location_name = ""

        # 缓存
        self._cache: Optional[WeatherData] = None
        self._cache_time: float = 0
        self.cache_duration: int = 1800  # 30分钟缓存

        # 回调
        self._on_update: Optional[Callable[[WeatherData], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        # 定时更新
        self._timer: Optional[threading.Timer] = None
        self._running: bool = False

    def set_credentials(self, api_key: str, api_host: str, location: str, location_name: str = ""):
        """设置 API 凭证"""
        self.api_key = api_key
        self.api_host = api_host
        self.location = location
        self.location_name = location_name
        self._cache = None  # 清除缓存
        self._cache_time = 0

    def on_update(self, callback: Callable[[WeatherData], None]):
        """设置天气更新回调"""
        self._on_update = callback

    def on_error(self, callback: Callable[[str], None]):
        """设置错误回调"""
        self._on_error = callback

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key and self.api_host and self.location)

    def _parse_response_json(self, response) -> Dict[str, Any]:
        """解析可能被压缩的响应 JSON"""
        content = response.content or b""
        if not content:
            return {}

        should_decompress = False
        encoding_header = response.headers.get("Content-Encoding", "").lower()
        if "gzip" in encoding_header or content[:2] == b"\x1f\x8b":
            should_decompress = True

        if should_decompress:
            try:
                content = gzip.decompress(content)
            except OSError:
                pass

        encoding = response.encoding or "utf-8"
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")

        return json.loads(text)

    def get_current_weather(self, force_refresh: bool = False) -> Optional[WeatherData]:
        """
        获取当前天气

        Args:
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            WeatherData 或 None
        """
        # 检查缓存
        if not force_refresh and self._cache:
            if time.time() - self._cache_time < self.cache_duration:
                return self._cache

        # 如果未配置或无requests库，返回模拟数据
        if not self.is_configured() or not HAS_REQUESTS:
            return self._get_mock_weather()

        try:
            # 使用用户专属 API Host 和请求头认证
            url = f"https://{self.api_host}/v7/weather/now"
            params = {
                "location": self.location,
            }
            headers = {
                "X-QW-Api-Key": self.api_key,
                "User-Agent": "WriterTool/1.0",
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = self._parse_response_json(response)

            if data.get("code") != "200":
                error_msg = f"API error: {data.get('code')}"
                logger.error(error_msg)
                if self._on_error:
                    self._on_error(error_msg)
                return self._get_mock_weather()  # 出错时回退到模拟

            now = data.get("now", {})
            weather_data = WeatherData(
                code=now.get("icon", ""),
                text=now.get("text", ""),
                temp=now.get("temp", ""),
                feels_like=now.get("feelsLike", ""),
                icon=now.get("icon", ""),
                wind_dir=now.get("windDir", ""),
                wind_scale=now.get("windScale", ""),
                humidity=now.get("humidity", ""),
                precip=now.get("precip", ""),
                vis=now.get("vis", ""),
                update_time=data.get("updateTime", ""),
                location_name=self.location_name,
            )

            # 更新缓存
            self._cache = weather_data
            self._cache_time = time.time()

            # 触发回调
            if self._on_update:
                self._on_update(weather_data)

            logger.info(f"Weather updated: {weather_data.text}, {weather_data.temp}°C")
            return weather_data

        except requests.RequestException as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            if self._on_error:
                self._on_error(error_msg)
            return self._get_mock_weather()  # 网络错误回退到模拟

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            if self._on_error:
                self._on_error(error_msg)
            return self._get_mock_weather()

    def _get_mock_weather(self) -> WeatherData:
        """生成模拟天气数据"""
        now = datetime.now()
        month = now.month
        
        # 简单季节判定
        if month in [12, 1, 2]: season = "winter"
        elif month in [3, 4, 5]: season = "spring"
        elif month in [6, 7, 8]: season = "summer"
        else: season = "autumn"
        
        # 权重随机
        options = ["100"] * 4 + ["101"] * 3  # 晴/多云为主
        
        if season == "summer":
            options.extend(["300", "302", "305"] * 2) # 雨/雷
        elif season == "winter":
            options.extend(["400", "404"] * 2) # 雪
        elif season == "spring":
            options.extend(["300", "305"]) # 小雨
            
        code = random.choice(options)
        
        # 模拟温度
        base_temp = {
            "winter": 5,
            "spring": 15,
            "summer": 28,
            "autumn": 18
        }
        temp = base_temp[season] + random.randint(-5, 5)
        
        weather_data = WeatherData(
            code=code,
            text="模拟天气",
            temp=str(temp),
            icon=code,
            location_name="本地(模拟)",
            update_time=now.strftime("%H:%M")
        )
        
        # 更新缓存以避免频繁模拟变化
        self._cache = weather_data
        self._cache_time = time.time()
        
        if self._on_update:
            self._on_update(weather_data)
            
        return weather_data

    def get_weather_state(self) -> Optional[str]:
        """
        获取当前天气对应的助手状态

        Returns:
            状态字符串 (sunny, cloudy, rainy, snowy, foggy, stormy) 或 None
        """
        weather = self.get_current_weather()
        if not weather:
            return None

        # 使用 icon 代码进行映射
        return self.WEATHER_CODE_MAPPING.get(weather.icon, None)

    def get_weather_text(self) -> str:
        """获取天气描述文字"""
        weather = self.get_current_weather()
        if weather:
            return weather.text
        return ""

    def get_weather_for_scene(self) -> str:
        """
        获取用于场景生成的天气描述

        Returns:
            中文天气描述，如 "晴朗"、"下雨"
        """
        state = self.get_weather_state()
        if state:
            return self.STATE_TO_TEXT.get(state, self.get_weather_text())
        return ""

    def search_city(self, keyword: str) -> list:
        """
        搜索城市

        Args:
            keyword: 城市名称关键词

        Returns:
            城市列表 [{id, name, adm1, adm2, country}, ...]
        """
        if not HAS_REQUESTS:
            return []

        if not self.api_key or not self.api_host:
            return []

        try:
            # 使用用户专属 API Host 和请求头认证
            url = f"https://{self.api_host}/geo/v2/city/lookup"
            params = {
                "location": keyword,
            }
            headers = {
                "X-QW-Api-Key": self.api_key,
                "User-Agent": "WriterTool/1.0",
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = self._parse_response_json(response)

            if data.get("code") != "200":
                return []

            cities = []
            for loc in data.get("location", []):
                cities.append({
                    "id": loc.get("id", ""),
                    "name": loc.get("name", ""),
                    "adm1": loc.get("adm1", ""),  # 省/州
                    "adm2": loc.get("adm2", ""),  # 市
                    "country": loc.get("country", ""),
                })
            return cities

        except Exception as e:
            logger.error(f"City search error: {e}")
            return []

    def start_auto_update(self, interval: int = None):
        """
        启动自动更新

        Args:
            interval: 更新间隔（秒），默认使用 cache_duration
        """
        if interval:
            self.cache_duration = interval

        self._running = True
        self._schedule_update()

    def stop_auto_update(self):
        """停止自动更新"""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_update(self):
        """调度下次更新"""
        if not self._running:
            return

        def update_task():
            # 使用线程池执行网络请求
            pool = get_ai_thread_pool()
            pool.submit("weather_update", self.get_current_weather, True)

        # 使用 Timer 仅作为调度器，不执行重任务
        self._timer = threading.Timer(self.cache_duration, lambda: [update_task(), self._schedule_update()])
        self._timer.daemon = True
        self._timer.start()


class WeatherDetector:
    """
    天气检测器 - 包装 WeatherService，提供状态检测和问候语功能
    """

    # 天气问候语
    WEATHER_GREETINGS = {
        "sunny": [
            "今天阳光明媚，适合写作~",
            "晴空万里，灵感也会更充沛吧！",
            "天气真好，希望你的故事也阳光满满！",
        ],
        "cloudy": [
            "多云的天气，适合静下心来写作。",
            "云层遮住了太阳，但遮不住你的灵感~",
            "阴天也有阴天的美，就像故事中的转折。",
        ],
        "rainy": [
            "外面在下雨，正适合窝在室内写作呢~",
            "雨声淅沥，是最好的写作背景音乐。",
            "下雨天，泡杯茶，写写故事，多惬意！",
        ],
        "stormy": [
            "外面雷雨交加，注意安全哦！",
            "雷暴天气，激情澎湃的情节正适合此刻写！",
            "暴风雨中也要坚持创作的勇气！",
        ],
        "snowy": [
            "下雪啦！银装素裹的世界真美~",
            "雪花飘飘，笔下的故事也温柔起来了。",
            "窗外飘雪，最适合写温暖的故事了。",
        ],
        "foggy": [
            "雾蒙蒙的天气，有种神秘感呢。",
            "大雾天气，注意出行安全哦！",
            "朦胧的天气，适合写悬疑故事~",
        ],
    }

    def __init__(self, weather_service: WeatherService):
        self.service = weather_service

    def get_current_weather_state(self) -> Optional[str]:
        """获取当前天气状态"""
        return self.service.get_weather_state()

    def get_weather_greeting(self, state: str) -> str:
        """
        获取天气问候语

        Args:
            state: 天气状态

        Returns:
            问候语字符串
        """
        import random
        greetings = self.WEATHER_GREETINGS.get(state, [])
        if greetings:
            return random.choice(greetings)
        return f"今天天气{self.service.get_weather_text()}~"

    def get_weather_info(self) -> Dict[str, Any]:
        """
        获取完整天气信息

        Returns:
            {state, text, temp, humidity, wind, greeting}
        """
        weather = self.service.get_current_weather()
        state = self.service.get_weather_state()

        if not weather:
            return {}

        return {
            "state": state,
            "text": weather.text,
            "temp": weather.temp,
            "feels_like": weather.feels_like,
            "humidity": weather.humidity,
            "wind_dir": weather.wind_dir,
            "wind_scale": weather.wind_scale,
            "location": weather.location_name,
            "greeting": self.get_weather_greeting(state) if state else "",
        }
