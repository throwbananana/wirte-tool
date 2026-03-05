import json
import os
from pathlib import Path

class ConfigManager:
    """Manages user configuration persistence."""

    def __init__(self, app_name="writer_tool"):
        self.config_dir = Path.home() / f".{app_name}"
        self.config_file = self.config_dir / "config.json"
        self.config_data = self._load_default_config()
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load_default_config(self):
        return {
            "ai_mode_enabled": True,
            "lm_api_url": "http://localhost:1234/v1/chat/completions",
            "lm_api_model": "local-model",
            "lm_api_key": "",
            "window_geometry": "1400x900",
            "last_opened_file": None,
            "theme": "Light",
            # Floating assistant defaults
            "assistant_alpha": 0.95,
            "assistant_avatar_size": 120,
            "assistant_start_expanded": False,
            "assistant_primary_mode": False,
            "assistant_mode_tips_shown": {},
            "assistant_reverse_width": 0,
            "assistant_reverse_height": 0,
            # 背景移除模式: "ai"(适合真实照片), "floodfill"(适合黑白漫画), "none"(不移除)
            "assistant_bg_remove_mode": "ai",
            # 边缘填充法的白色容差 (0-255)，越大越容易识别为背景
            "assistant_bg_remove_tolerance": 30,
            "enable_idle_chat": False,
            "idle_interval": 10,
            "skins": {},
            "current_skin": "Default",
            "avatar_idle": "",
            "avatar_thinking": "",
            "avatar_success": "",
            "avatar_error": "",
            # Clipboard monitoring
            "clipboard_notify_enabled": False,
            "clipboard_check_interval": 2000,
            # AI Prompts
            "prompt_continue_script": "你是一个专业的编剧助手。请根据提供的上下文续写剧本。请只输出续写的内容，不要包含解释性语言。",
            "prompt_rewrite_script": "你是一个专业的剧本润色助手。请将用户提供的文本重写为'{style}'风格。保持原意，仅调整语气和修辞。不要输出任何解释。",
            "prompt_diagnose_outline": "你是一个资深文学编辑。请分析并诊断这份故事大纲在逻辑、节奏、人物动机等方面的优缺点，并给出改进建议。",
            "prompt_generate_outline": "你是一个创意策划。请根据提供的剧本片段或想法，生成一份层级结构清晰的思维导图大纲（JSON格式：{name, content, children}）。要求：1.按幕/章节组织，每个章节作为父节点；2.章节下的场景/事件作为子节点；3.保持前后顺序的逻辑关联。",
            # Export Settings
            "export_pdf_margin": 20,
            "export_pdf_line_spacing": 1.5,
            "export_font_family": "Microsoft YaHei",
            # Focus Mode Settings
            "focus_mode_enabled": False,
            "focus_mode_level": "line",  # line, sentence, paragraph, dialogue
            "focus_mode_context_lines": 3,  # Number of context lines above/below
            "focus_mode_gradient": True,  # Enable gradient dimming effect
            "focus_mode_highlight_current": True,  # Highlight current line background
            "focus_mode_highlight_color_light": "#FFFDE7",  # Current line bg (light theme)
            "focus_mode_highlight_color_dark": "#37474F",  # Current line bg (dark theme)
            "focus_mode_dim_color_light": "#CCCCCC",  # Dimmed text color (light)
            "focus_mode_dim_color_dark": "#555555",  # Dimmed text color (dark)
            "focus_mode_with_typewriter": True,  # Auto-enable typewriter mode
            "focus_mode_auto_in_sprint": True,  # Auto-enable during writing sprint
            "focus_mode_auto_in_zen": True,  # Auto-enable in zen mode
            # Weather API Settings (和风天气)
            "weather_enabled": False,
            "weather_api_key": "",
            "weather_api_host": "",  # 用户专属API Host，如 abcxyz.qweatherapi.com
            "weather_location": "101010100",  # 默认北京
            "weather_location_name": "北京",
            "weather_update_interval": 1800,  # 30分钟更新
            "weather_auto_ambiance": True,    # 天气联动环境音
            "weather_show_in_scene": True,    # 场景生成显示真实天气
            # Close behavior / tray
            "close_behavior": "ask",  # ask/minimize/exit
            "taskbar_date_events": [],
            "dev_notice_dismissed": False,
            "guide_mode_enabled": True,
            "guide_mode_step": 0,
            "custom_project_types": {},
            # Sidebar navigation state
            "sidebar_collapsed": False,
            "sidebar_active_workspace": "writing",
            "sidebar_active_item": "outline",
            "reverse_engineering_auto_link": False,
            "reverse_engineering_linkage_defaults": {},
            "reverse_engineering_request_timeout": 120,
            "reverse_engineering_max_retries": 3,
        }

    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    # Merge with default to ensure all keys exist
                    for key, value in saved_config.items():
                        self.config_data[key] = value
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self.config_data.get(key, default)

    def set(self, key, value):
        self.config_data[key] = value

    def get_config(self):
        """Return a shallow copy of all current config values."""
        return dict(self.config_data)

    def get_ai_config(self):
        """Return AI connection settings in a consistent structure."""
        return {
            "api_url": self.get("lm_api_url"),
            "model": self.get("lm_api_model"),
            "api_key": self.get("lm_api_key")
        }

    def is_ai_enabled(self) -> bool:
        """Return whether AI mode is enabled."""
        return bool(self.get("ai_mode_enabled", True))

    def get_focus_mode_config(self) -> dict:
        """Return focus mode settings in a consistent structure."""
        return {
            "enabled": self.get("focus_mode_enabled", False),
            "level": self.get("focus_mode_level", "line"),
            "context_lines": self.get("focus_mode_context_lines", 3),
            "gradient": self.get("focus_mode_gradient", True),
            "highlight_current": self.get("focus_mode_highlight_current", True),
            "highlight_color_light": self.get("focus_mode_highlight_color_light", "#FFFDE7"),
            "highlight_color_dark": self.get("focus_mode_highlight_color_dark", "#37474F"),
            "dim_color_light": self.get("focus_mode_dim_color_light", "#CCCCCC"),
            "dim_color_dark": self.get("focus_mode_dim_color_dark", "#555555"),
            "with_typewriter": self.get("focus_mode_with_typewriter", True),
            "auto_in_sprint": self.get("focus_mode_auto_in_sprint", True),
            "auto_in_zen": self.get("focus_mode_auto_in_zen", True)
        }

    def set_focus_mode_config(self, config: dict):
        """Update focus mode settings from a dictionary."""
        prefix = "focus_mode_"
        for key, value in config.items():
            self.set(f"{prefix}{key}", value)

    def get_weather_config(self) -> dict:
        """Return weather settings in a consistent structure."""
        return {
            "enabled": self.get("weather_enabled", False),
            "api_key": self.get("weather_api_key", ""),
            "api_host": self.get("weather_api_host", ""),
            "location": self.get("weather_location", "101010100"),
            "location_name": self.get("weather_location_name", "北京"),
            "update_interval": self.get("weather_update_interval", 1800),
            "auto_ambiance": self.get("weather_auto_ambiance", True),
            "show_in_scene": self.get("weather_show_in_scene", True),
        }

    def set_weather_config(self, config: dict):
        """Update weather settings from a dictionary."""
        prefix = "weather_"
        for key, value in config.items():
            self.set(f"{prefix}{key}", value)
        self.save()
