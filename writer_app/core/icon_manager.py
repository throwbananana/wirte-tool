import os
import json
import ctypes
import platform
import logging

logger = logging.getLogger(__name__)

class IconManager:
    _instance = None
    
    FONT_FAMILIES = {
        "regular": "FluentSystemIcons-Regular",
        "filled": "FluentSystemIcons-Filled"
    }
    
    # Aliases for common emoji/names
    ALIASES = {
        "🎉": "sparkle",
        "🏆": "trophy",
        "📝": "edit",
        "💡": "lightbulb",
        "📚": "library",
        "📜": "history",
        "🌟": "calendar_star",
        "📊": "data_usage",
        "🎲": "games",
        "💾": "save",
        "🤖": "bot",
        "⚙": "settings",
        "🎤": "mic",
        "📋": "clipboard_paste",
        "↑": "arrow_up",
        "📢": "alert",
        "🔧": "wrench",
        "❌": "error_circle",
        "⚠️": "warning",
        "ℹ️": "info",
        "✅": "checkmark_circle",
        "🔍": "search",
        "💎": "star",
        "🎯": "target",
        "👗": "t_shirt",
        "📸": "camera",
        "📷": "camera",
        "🖼️": "image",
        "🎨": "color",
        "👤": "person",
        "🏞️": "image",
        "🗺️": "map",
        "📎": "attach",
        "🎭": "board",
        "⚙️": "settings",
        "🖌️": "edit",
        "🎵": "music",
        "🔊": "speaker_2",
        "🎤": "mic",
        "🌱": "leaf_one",
        "🧘": "brain_circuit",
        "🌙": "weather_moon",
        "🔥": "fire",
        "⏰": "clock",
        "⏳": "timer",
        "⏱️": "timer",
        "🍪": "food_cookie",
        "🍰": "food_cake",
        "🍕": "food_pizza",
        "🍎": "food_apple",
        "☕": "drink_coffee",
        "🧋": "drink_tea",
        "🍞": "food_bread",
        "🍣": "food_sushi",
        "🍔": "food_burger",
        "🍜": "food_bowl",
        "🥩": "food_steak",
        "🍝": "food_spaghetti",
        "🐙": "food",
        "🐉": "animal_rabbit", # Fallback for dragon fruit?
        "🐲": "animal_rabbit",
        "❤": "heart",
        "💕": "heart",
        "❤️": "heart",
        "💖": "heart_pulse",
        "💞": "heart",
        "💝": "star", # or gift
        "🌈": "weather_rain",
        "❄️": "weather_snow",
        "🌸": "leaf_one",
        "🌻": "weather_sunny",
        "🍂": "leaf_three",
        "🧧": "gift",
        "🏮": "lightbulb",
        "🌿": "leaf_two",
        "🥮": "food_cake",
        "🏔️": "mountain",
        "🐰": "animal_rabbit",
        "🎃": "dark_theme",
        "🦃": "food",
        "🎄": "gift",
        "💍": "star",
        "🏃": "run",
        "🎀": "ribbon",
        "👙": "weather_sunny",
        "👕": "t_shirt",
        "👔": "person_board",
        "🎓": "hat_graduation",
        "👘": "ribbon",
        "🦇": "dark_theme",
        "✨": "sparkle",
        "⚔️": "shield",
        "🧙‍♀️": "hat_graduation",
        "🍳": "food",
        "🎮": "games",
        "🛍️": "cart",
        "✈️": "airplane",
        "🏖️": "weather_sunny",
        "🏫": "hat_graduation",
        "💼": "briefcase",
        "☀️": "weather_sunny",
        "⛅": "weather_cloudy",
        "🌧️": "weather_rain",
        "🌫️": "weather_fog",
        "⛈️": "weather_squalls",
        "😁": "presence_available",
        "😊": "presence_available",
        "😐": "presence_away",
        "😞": "presence_dnd",
        "😭": "presence_blocked",
        "😯": "hand_draw",
        "😑": "hand_draw",
        "😤": "warning",
        "😱": "alert",
        "🤭": "sparkle",
        "😪": "weather_sunny",
        "😴": "weather_moon",
        "💤": "weather_moon",
        "🙆": "person",
        "✕": "dismiss",
        "×": "dismiss",
        "◀": "chevron_left",
        "▶": "chevron_right",
        "▽": "chevron_down",
        "▲": "chevron_up",
        "•": "circle",
        "○": "circle",
        "●": "circle_filled",
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        self.icons = {} # name -> char
        self.loaded_fonts = set()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(base_dir, "writer_data", "fonts")
        
        self._load_resources()
        self.initialized = True

    def _load_resources(self):
        # Load Fonts
        if platform.system() == "Windows":
            self._load_font_windows("FluentSystemIcons-Regular.ttf")
            self._load_font_windows("FluentSystemIcons-Filled.ttf")
        
        # Load Mappings
        self._load_mapping("FluentSystemIcons-Regular.json", "regular")
        self._load_mapping("FluentSystemIcons-Filled.json", "filled")

    def _load_font_windows(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            logger.warning(f"Font file missing: {path}")
            return
        
        try:
            gdi32 = ctypes.windll.gdi32
            ret = gdi32.AddFontResourceExW(path, 0x10, 0)
            if ret > 0:
                self.loaded_fonts.add(filename)
                logger.info(f"Loaded font: {filename}")
            else:
                logger.error(f"Failed to load font: {filename}")
        except Exception as e:
            logger.error(f"Error loading font {filename}: {e}")

    def _load_mapping(self, filename, style):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    self.icons[k] = chr(v)
        except Exception as e:
            logger.error(f"Error loading icon mapping {filename}: {e}")

    def get_icon(self, name, size=24, style="regular", fallback="?"):
        """
        Get icon character.
        Tries to find 'ic_fluent_{name}_{size}_{style}'.
        """
        # Resolve alias
        name = self.ALIASES.get(name, name)
        
        # 1. Try exact match
        if name in self.icons:
            return self.icons[name]
            
        # 2. Try constructing name
        key = f"ic_fluent_{name}_{size}_{style}"
        if key in self.icons:
            return self.icons[key]
            
        # 3. Try alternative sizes (prefer 24, then others)
        for s in [24, 20, 16, 28, 32, 48]:
            key = f"ic_fluent_{name}_{s}_{style}"
            if key in self.icons:
                return self.icons[key]

        return fallback

    def get_font(self, size=12, style="regular"):
        """Returns the font tuple for Tkinter."""
        family = self.FONT_FAMILIES.get(style, "Segoe UI")
        return (family, size)