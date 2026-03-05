import os
try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

class AmbiancePlayer:
    """
    Manages background ambiance sounds using Pygame.
    Supports looping tracks like Rain, Cafe, White Noise.
    """

    # 天气状态到环境音映射
    WEATHER_MAPPINGS = {
        "rainy": "rain",
        "stormy": "rain",
        "snowy": "nature",
        "foggy": "nature",
        "sunny": None,      # 晴天不自动播放
        "cloudy": None,     # 多云不自动播放
    }

    def __init__(self, data_dir):
        global HAS_PYGAME
        
        self.enabled = False
        self.current_sound = None
        self.sound_dir = os.path.join(data_dir, "sounds")
        self.volume = 0.5
        
        if not os.path.exists(self.sound_dir):
            os.makedirs(self.sound_dir)
            
        if HAS_PYGAME:
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"Failed to init pygame mixer: {e}")
                HAS_PYGAME = False

    def scan_sounds(self):
        """Scan sound directory and return list of available themes (filenames without extension)."""
        if not os.path.exists(self.sound_dir):
            return []
        
        themes = set()
        valid_exts = {".mp3", ".wav", ".ogg"}
        
        for f in os.listdir(self.sound_dir):
            base, ext = os.path.splitext(f)
            if ext.lower() in valid_exts:
                themes.add(base)
        
        return sorted(list(themes))

    def toggle(self, enable):
        """Toggle audio on/off globally."""
        self.enabled = enable
        if not enable:
            self.stop()
        else:
            # If we were playing something before, maybe resume? 
            # For now, just enable state. 
            # Actual playback starts when play_theme is called or if we had a default.
            pass

    def play_smart(self, context_text):
        """
        Analyze context text (location, tags, time) and play appropriate sound.
        """
        if not self.enabled or not context_text: return

        text = context_text.lower()
        theme = None

        # Keyword mapping
        mappings = {
            "rain": ["rain", "storm", "雨", "雷", "stormy"],
            "cafe": ["cafe", "coffee", "restaurant", "bar", "咖啡", "餐厅"],
            "night": ["night", "crickets", "evening", "夜", "晚"],
            "city": ["city", "street", "traffic", "urban", "街", "市"],
            "nature": ["forest", "park", "nature", "wind", "forest", "林", "公园", "风"],
            "sea": ["sea", "ocean", "beach", "waves", "海", "滩"],
            "fire": ["fire", "fireplace", "camp", "火", "炉"],
            "horror": ["horror", "scary", "creep", "dungeon", "恐怖", "鬼", "地牢"],
            "battle": ["battle", "war", "fight", "action", "战", "打"]
        }

        # Check keywords
        for key, keywords in mappings.items():
            if any(k in text for k in keywords):
                theme = key
                break
        
        # Priority overrides? Rain > Night usually.
        
        if theme:
            if theme != self.current_sound:
                self.play_theme(theme)
        # Else: keep playing current or silence? 
        # Usually keep current is less jarring, unless we want silence for unmatched.
        # Let's keep current for now.

    def play_theme(self, theme_name):
        """
        Play a specific ambiance theme (e.g., 'rain', 'cafe').
        Expects files like 'rain.mp3' or 'rain.wav' in writer_data/sounds/
        """
        if not self.enabled or not HAS_PYGAME:
            return

        # Stop current
        self.stop()
        
        # Find file
        exts = [".mp3", ".wav", ".ogg"]
        found_path = None
        for ext in exts:
            path = os.path.join(self.sound_dir, theme_name + ext)
            if os.path.exists(path):
                found_path = path
                break
        
        if found_path:
            try:
                pygame.mixer.music.load(found_path)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play(-1) # Loop indefinitely
                self.current_sound = theme_name
            except Exception as e:
                print(f"Error playing {theme_name}: {e}")
        else:
            print(f"Sound file for '{theme_name}' not found in {self.sound_dir}")

    def stop(self):
        if HAS_PYGAME:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.current_sound = None

    def set_volume(self, val):
        self.volume = max(0.0, min(1.0, val))
        if HAS_PYGAME:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass

    def is_playing(self):
        return self.current_sound is not None

    def play_for_weather(self, weather_state: str) -> bool:
        """
        根据天气状态播放对应环境音

        Args:
            weather_state: 天气状态 (rainy, stormy, snowy, foggy, sunny, cloudy)

        Returns:
            是否成功播放
        """
        theme = self.WEATHER_MAPPINGS.get(weather_state)
        if theme:
            self.play_theme(theme)
            return True
        return False

    def get_weather_theme(self, weather_state: str) -> str:
        """
        获取天气对应的环境音主题

        Args:
            weather_state: 天气状态

        Returns:
            环境音主题名称，如果没有对应则返回空字符串
        """
        return self.WEATHER_MAPPINGS.get(weather_state, "") or ""


class TypewriterSoundPlayer:
    """
    打字机音效播放器 - 在打字时播放机械键盘/打字机声音
    """

    # 可用的打字机音效类型
    SOUND_TYPES = {
        "typewriter": "经典打字机",
        "mechanical": "机械键盘",
        "soft": "轻柔按键",
        "vintage": "复古打字机",
    }

    def __init__(self, data_dir):
        self.enabled = False
        self.sound_type = "typewriter"
        self.volume = 0.3  # 默认音量较小，避免影响写作
        self.sound_dir = os.path.join(data_dir, "sounds", "typewriter")
        self._sounds = {}
        self._last_play_time = 0
        self._min_interval = 0.05  # 最小播放间隔（秒），防止声音堆叠

        if not os.path.exists(self.sound_dir):
            os.makedirs(self.sound_dir)

        self._load_sounds()

    def _load_sounds(self):
        """加载打字机音效文件"""
        if not HAS_PYGAME:
            return

        try:
            pygame.mixer.init()
        except Exception:
            return

        valid_exts = {".mp3", ".wav", ".ogg"}

        for sound_type in self.SOUND_TYPES.keys():
            # 尝试加载每种类型的音效
            for ext in valid_exts:
                # 普通按键音
                key_path = os.path.join(self.sound_dir, f"{sound_type}_key{ext}")
                if os.path.exists(key_path):
                    try:
                        self._sounds[f"{sound_type}_key"] = pygame.mixer.Sound(key_path)
                    except Exception:
                        pass

                # 回车音效
                enter_path = os.path.join(self.sound_dir, f"{sound_type}_enter{ext}")
                if os.path.exists(enter_path):
                    try:
                        self._sounds[f"{sound_type}_enter"] = pygame.mixer.Sound(enter_path)
                    except Exception:
                        pass

                # 空格音效
                space_path = os.path.join(self.sound_dir, f"{sound_type}_space{ext}")
                if os.path.exists(space_path):
                    try:
                        self._sounds[f"{sound_type}_space"] = pygame.mixer.Sound(space_path)
                    except Exception:
                        pass

    def toggle(self, enable: bool):
        """开启/关闭打字机音效"""
        self.enabled = enable

    def set_sound_type(self, sound_type: str):
        """设置打字机音效类型"""
        if sound_type in self.SOUND_TYPES:
            self.sound_type = sound_type

    def set_volume(self, vol: float):
        """设置音量 (0.0 - 1.0)"""
        self.volume = max(0.0, min(1.0, vol))

        # 更新已加载音效的音量
        for sound in self._sounds.values():
            try:
                sound.set_volume(self.volume)
            except Exception:
                pass

    def play_key(self, key_char: str = None):
        """播放按键音效"""
        if not self.enabled or not HAS_PYGAME:
            return

        import time
        current_time = time.time()
        if current_time - self._last_play_time < self._min_interval:
            return

        self._last_play_time = current_time

        # 根据按键类型选择音效
        if key_char == "\n" or key_char == "Return":
            sound_key = f"{self.sound_type}_enter"
        elif key_char == " ":
            sound_key = f"{self.sound_type}_space"
        else:
            sound_key = f"{self.sound_type}_key"

        # 播放音效
        sound = self._sounds.get(sound_key)
        if not sound:
            # 回退到普通按键音
            sound = self._sounds.get(f"{self.sound_type}_key")

        if sound:
            try:
                sound.set_volume(self.volume)
                sound.play()
            except Exception:
                pass

    def get_available_types(self):
        """获取可用的音效类型列表"""
        available = []
        for type_key, type_name in self.SOUND_TYPES.items():
            key = f"{type_key}_key"
            if key in self._sounds:
                available.append({"key": type_key, "name": type_name})
        return available

    def is_available(self) -> bool:
        """检查是否有可用的打字机音效"""
        return len(self._sounds) > 0