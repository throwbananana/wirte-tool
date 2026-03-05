"""
悬浮写作助手主窗口 (Floating Writing Assistant Main Window)

整合所有模块的主窗口类
"""

import os
import copy
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from writer_app.core.project_types import ProjectTypeManager

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 导入本模块组件
from .states import (
    AssistantState,
    STATE_NAMES,
    STATE_EMOJIS,
    STATE_FALLBACKS,
    FestivalDetector,
    SeasonDetector,
    TimeDetector,
    InteractionManager,
)
from .weather_service import WeatherService, WeatherDetector
from .event_system import AssistantEventSystem, EventPriority
from .constants import (
    ACHIEVEMENTS,
    FOODS,
    WRITING_PROMPTS,
    IDLE_CHAT_TOPICS,
    EMOTION_KEYWORDS,
    AI_EMOTION_KEYWORDS,
    QUICK_PROMPTS_AI,
    QUICK_TOOLS,
)
from .pet_system import PetSystem, PetData, MoodLevel
from .tools import (
    NameGenerator,
    DiceRoller,
    PomodoroTimer,
    PromptCardDrawer,
    CharacterCardGenerator,
    SceneGenerator,
    WordCounter,
)
from .ai_handler import (
    StreamingAIClient,
    ConversationHistory,
    EmotionDetector,
    ProjectContextBuilder,
    AIAssistantHandler,
)
from .notification_manager import NotificationManager
from .games import MiniGameManager
from .school_events import SchoolEventManager
from .context_menu import AssistantContextMenu
from .components.avatar_view import AvatarView
from .components.chat_view import ChatView
from .components.home_panel import LeisureHomePanel
from .theme import ThemeManager
from .dialogs import (
    NameGeneratorDialog, TimerDialog, QuickNoteDialog, 
    PromptCardDialog, CharacterCardDialog, SceneGeneratorDialog,
    GameDialog, AchievementDialog, CollectionDialog, FeedDialog,
    AffectionDialog, WardrobeDialog, AssistantSettingsDialog, AlbumDialog,
    QuickInputDialog, QuickCharacterDialog, QuickSceneDialog, 
    QuickIdeaDialog, QuickResearchDialog, WeatherSettingsDialog,
    SchoolEventDialog, EventHistoryDialog
)
from .context_hotkeys import (
    ContextProvider,
    HotkeyManager,
    ClipboardMonitor,
    ContextAwareAssistant,
)
from .voice import (
    VoiceAssistant,
    check_voice_dependencies,
    get_installation_guide,
)
from .integrations import (
    AssistantIntegrationManager,
    EventBusIntegration,
    GamificationIntegration,
    CommandExecutor,
    AIControllerBridge,
    StatsIntegration,
)
from .stats_widgets import (
    MiniStatsPanel,
    QuickActionsPanel,
)

from writer_app.core.icon_manager import IconManager
from writer_app.utils.ai_client import AIClient

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

def get_icon_font(size=12):
    return IconManager().get_font(size=size)



class FloatingAssistant(tk.Toplevel):
    """悬浮写作助手主窗口类"""

    # 状态类别（用于衣橱）
    STATE_CATEGORIES = {
        "基础状态": [
            ("idle", "待机"),
            ("thinking", "思考"),
            ("success", "成功"),
            ("error", "出错"),
        ],
        "情绪表情": [
            ("happy", "开心"),
            ("sad", "难过"),
            ("excited", "兴奋"),
            ("shy", "害羞"),
            ("angry", "生气"),
            ("surprised", "惊讶"),
            ("curious", "好奇"),
            ("love", "喜爱"),
            ("worried", "担忧"),
            ("cheering", "加油"),
            ("blush", "脸红"),
            ("trust", "信任"),
            ("devoted", "亲密"),
        ],
        "节日状态": [
            ("new_year", "元旦"),
            ("spring_festival", "春节"),
            ("lantern", "元宵"),
            ("qingming", "清明"),
            ("dragon_boat", "端午"),
            ("qixi", "七夕"),
            ("mid_autumn", "中秋"),
            ("double_ninth", "重阳"),
            ("valentines", "情人节"),
            ("easter", "复活节"),
            ("halloween", "万圣节"),
            ("thanksgiving", "感恩节"),
            ("christmas", "圣诞节"),
            ("birthday", "生日"),
            ("anniversary", "周年"),
        ],
        "季节状态": [
            ("spring", "春天"),
            ("summer", "夏天"),
            ("autumn", "秋天"),
            ("winter", "冬天"),
        ],
        "时间状态": [
            ("morning", "早晨"),
            ("night", "夜晚"),
            ("midnight", "深夜"),
        ],
        "服装状态": [
            ("sportswear", "运动装"),
            ("maid", "女仆装"),
            ("swimsuit", "泳装"),
            ("casual", "休闲装"),
            ("formal", "正装"),
            ("pajamas", "睡衣"),
            ("uniform", "制服"),
            ("kimono", "和服"),
            ("cheongsam", "旗袍"),
            ("gothic", "哥特"),
            ("lolita", "洛丽塔"),
            ("fantasy", "奇幻"),
            ("knight", "骑士"),
            ("witch", "魔女"),
            ("idol", "偶像"),
        ],
        "场景状态": [
            ("cooking", "烹饪"),
            ("gaming", "游戏"),
            ("music", "音乐"),
            ("reading", "阅读"),
            ("shopping", "购物"),
            ("travel", "旅行"),
            ("beach", "海滩"),
            ("mountain", "山岳"),
            ("cafe", "咖啡馆"),
            ("school", "学校"),
            ("office", "办公室"),
        ],
        "互动状态": [
            ("poked", "被戳"),
            ("poked_again", "再被戳"),
            ("annoyed", "被烦"),
            ("startled", "惊吓"),
            ("tickled", "挠痒"),
            ("patted", "摸头"),
            ("hugged", "拥抱"),
            ("waking_up", "醒来"),
            ("sleepy_disturbed", "惊扰"),
            ("dozing", "打盹"),
            ("stretching", "伸懒腰"),
        ],
    }

    def __init__(self, parent, project_manager=None, config_manager=None):
        super().__init__(parent)

        self.parent = parent
        self.project_manager = project_manager
        self.config_manager = config_manager

        # 初始化主题
        if config_manager:
            ThemeManager.set_mode(config_manager.get("theme", "Dark"))

        # 初始化检测器
        self.festival_detector = FestivalDetector()
        self.season_detector = SeasonDetector()
        self.time_detector = TimeDetector()
        self.emotion_detector = EmotionDetector()

        # 初始化养成系统
        self._init_pet_system()
        self.event_system = AssistantEventSystem(self, self.pet_system, self.project_manager)

        # 初始化AI处理器
        self._init_ai_handler()

        # 初始化游戏管理器
        self.game_manager = MiniGameManager()
        self.school_event_manager = SchoolEventManager(self.pet_system)

        # 初始化通知管理器
        self.notification_manager = NotificationManager(self._safe_append_message)

        # 初始化工具
        self.name_generator = NameGenerator()
        self.dice_roller = DiceRoller()
        self.timer = PomodoroTimer()
        self.prompt_drawer = PromptCardDrawer()
        self.char_generator = CharacterCardGenerator()
        self.scene_generator = SceneGenerator()
        self.word_counter = WordCounter()

        # UI状态
        self.is_expanded = self.config_manager.get("assistant_start_expanded", False) if config_manager else False
        self.ai_mode_enabled = True
        self.state = AssistantState.IDLE
        self._active_mode = "leisure"
        self._default_expanded_size = None
        self._reverse_expanded_size = None
        self.reverse_engineering_view = None
        self._reverse_container = None
        self._reverse_ai_client = None
        self._drag_data = {"x": 0, "y": 0, "start_time": 0, "start_x": 0, "start_y": 0}
        self.edge_snapped = False
        self.snap_side = None

        # 互动管理器
        self.interaction_manager = InteractionManager()

        # 计时器状态
        self.timer_running = False
        self.timer_id = None
        self.timer_end_time = 0

        # 闲聊状态
        self.idle_timer_id = None
        self.last_activity_time = datetime.now()

        # 立绘系统
        self.skins = self._load_skins()
        self.current_skin = self.config_manager.get("assistant_current_skin", "Default") if config_manager else "Default"
        self.avatar_images: Dict[str, Any] = {}
        self.current_avatar_image = None
        self.avatar_ratio = 1.0
        self.avatar_render_size = (0, 0)

        # 相册数据
        self.photos = self._load_photos()
        self._check_photo_achievements()

        # 对话历史
        self.conversation_history = ConversationHistory(max_messages=20)

        # 初始化上下文感知
        self._init_context_provider()

        # 初始化语音功能
        self._init_voice()

        # 初始化音频控制（环境音、打字机音效）
        self._init_audio_players()

        # 初始化天气服务
        self._init_weather_service()

        # 初始化集成管理器（联动其他模块）
        self._init_integrations()

        # 设置窗口
        self._setup_window()
        self._setup_ui()
        self._load_avatar_images()
        self._set_state(AssistantState.IDLE)

        # 启动闲聊定时器
        self._start_idle_timer()

        # 启动维护定时器（检查日期变更）
        self._start_maintenance_timer()

        # 检查节日/季节
        self._check_special_occasions()

        # 启动集成监听
        self._start_integrations()

    def _init_pet_system(self):
        """初始化养成系统"""
        self.pet_system = PetSystem(self.config_manager)

        # 注册回调
        self.pet_system.on_achievement(self._on_achievement_unlocked_callback)
        self.pet_system.on_level_up(self._on_level_up_callback)

        # 快捷访问属性
        self.affection = self.pet_system.data.affection
        self.total_chats = self.pet_system.data.total_chats
        self.achievements = self.pet_system.data.unlocked_achievements
        self.collection = self.pet_system.data.collected_foods
        self.created_at = self.pet_system.data.created_at

        # 工具计数器
        self.name_gen_count = self.pet_system.data.name_gen_count
        self.prompt_count = self.pet_system.data.prompt_count
        self.consecutive_sixes = self.pet_system.data.consecutive_sixes # Sync this too

    def _init_ai_handler(self):
        """初始化AI处理器"""
        self.ai_handler = AIAssistantHandler(
            config_manager=self.config_manager,
            project_manager=self.project_manager
        )

    def _init_context_provider(self):
        """初始化上下文提供器"""
        self.context_provider = ContextProvider(self.project_manager)

    def _init_voice(self):
        """初始化语音功能"""
        self.voice_assistant = VoiceAssistant(
            on_voice_input=self._on_voice_input,
            on_command=self._on_voice_command
        )
        self.voice_enabled = self.config_manager.get("assistant_voice_enabled", False) if self.config_manager else False
        self.auto_speak = self.config_manager.get("assistant_auto_speak", False) if self.config_manager else False

    def _init_audio_players(self):
        """初始化音频播放器（环境音、打字机音效）"""
        # 环境音播放器（外部设置）
        self._ambiance_player = None
        self._ambiance_enabled = False
        self._current_ambiance = None

        # 打字机音效播放器（外部设置）
        self._typewriter_player = None
        self._typewriter_enabled = self.config_manager.get("assistant_typewriter_sound", False) if self.config_manager else False

        # 可用的环境音主题
        self._ambiance_themes = [
            {"key": "rain", "name": "雨声", "icon": get_icon("weather_rain", "🌧️")},
            {"key": "cafe", "name": "咖啡厅", "icon": get_icon("drink_coffee", "☕")},
            {"key": "nature", "name": "自然", "icon": get_icon("leaf_one", "🌿")},
            {"key": "night", "name": "夜晚", "icon": get_icon("weather_moon", "🌙")},
            {"key": "fire", "name": "壁炉", "icon": get_icon("fire", "🔥")},
            {"key": "sea", "name": "海浪", "icon": get_icon("weather_rain", "🌊")},
        ]


    def _init_weather_service(self):
        """初始化天气服务"""
        self.weather_service = None
        self.weather_detector = None
        self._weather_timer_id = None

        if not self.config_manager:
            return

        weather_config = self.config_manager.get_weather_config()
        if not weather_config.get("enabled"):
            return

        api_key = weather_config.get("api_key", "")
        api_host = weather_config.get("api_host", "")
        location = weather_config.get("location", "101010100")
        location_name = weather_config.get("location_name", "北京")

        if not api_key or not api_host:
            return

        # 创建天气服务
        self.weather_service = WeatherService(api_key, api_host, location)
        self.weather_service.location_name = location_name
        self.weather_detector = WeatherDetector(self.weather_service)

        # 设置回调
        self.weather_service.on_update(self._on_weather_update)
        self.weather_service.on_error(self._on_weather_error)

        # 启动定时更新
        interval = weather_config.get("update_interval", 1800)
        self.weather_service.cache_duration = interval
        self._start_weather_timer()

    def _start_weather_timer(self):
        """启动天气更新定时器"""
        if not self.weather_service:
            return

        # 立即获取一次天气
        self.after(1000, self._fetch_weather)

    def _fetch_weather(self):
        """获取天气（在后台线程中执行）"""
        if not self.weather_service:
            return

        import threading

        def do_fetch():
            try:
                self.weather_service.get_current_weather(force_refresh=True)
            except Exception as e:
                print(f"Weather fetch error: {e}")

        thread = threading.Thread(target=do_fetch, daemon=True)
        thread.start()

        # 调度下次更新
        interval = self.weather_service.cache_duration * 1000  # 转为毫秒
        self._weather_timer_id = self.after(interval, self._fetch_weather)

    def _on_weather_update(self, weather_data):
        """天气更新回调"""
        # 在主线程中更新 UI
        self.after(0, lambda: self._handle_weather_update(weather_data))

    def _handle_weather_update(self, weather_data):
        """处理天气更新（主线程）"""
        if not self.weather_detector:
            return

        state = self.weather_service.get_weather_state()

        # 同步天气到场景生成器
        if self.config_manager and self.config_manager.get("weather_show_in_scene", True):
            weather_text = self.weather_service.get_weather_for_scene()
            if weather_text:
                SceneGenerator.set_real_weather(weather_text)

        if state:
            # 更新助手状态
            if state in self.avatar_images:
                greeting = self.weather_detector.get_weather_greeting(state)
                self._set_state(state)
                # 可选：显示天气消息
                temp = weather_data.temp
                text = weather_data.text
                location = weather_data.location_name
                self._append_message("system", f"🌤️ {location}：{text} {temp}°C\n{greeting}")

            # 联动环境音
            if self.config_manager and self.config_manager.get("weather_auto_ambiance"):
                self._sync_ambiance_to_weather(state)

    def _on_weather_error(self, error_msg):
        """天气错误回调"""
        print(f"Weather error: {error_msg}")

    def _sync_ambiance_to_weather(self, weather_state: str):
        """根据天气同步环境音"""
        if not self._ambiance_player:
            return

        weather_to_ambiance = {
            AssistantState.RAINY: "rain",
            AssistantState.STORMY: "rain",
            AssistantState.SNOWY: "nature",
        }

        ambiance = weather_to_ambiance.get(weather_state)
        if ambiance:
            self._ambiance_player.play_theme(ambiance)
            self._current_ambiance = ambiance
            self._ambiance_enabled = True

    def set_ambiance_player(self, player):
        """设置环境音播放器"""
        self._ambiance_player = player
        if player:
            # 扫描可用的声音
            available = player.scan_sounds()
            # 更新可用主题列表
            self._update_available_ambiances(available)

    def set_typewriter_player(self, player):
        """设置打字机音效播放器"""
        self._typewriter_player = player
        if player and self._typewriter_enabled:
            player.toggle(True)

    def _update_available_ambiances(self, available_sounds):
        """更新可用的环境音主题"""
        if not available_sounds:
            return
        # 标记哪些主题是可用的
        available_set = set(s.lower() for s in available_sounds)
        for theme in self._ambiance_themes:
            theme["available"] = theme["key"] in available_set

    def toggle_ambiance(self, theme_key: str = None):
        """切换环境音"""
        if not self._ambiance_player:
            self._append_message("system", "环境音播放器未初始化")
            return

        if theme_key:
            # 播放指定主题
            if theme_key == self._current_ambiance:
                # 关闭当前主题
                self._ambiance_player.stop()
                self._current_ambiance = None
                self._ambiance_enabled = False
                self._append_message("system", "🔇 环境音已关闭")
            else:
                self._ambiance_player.toggle(True)
                self._ambiance_player.play_theme(theme_key)
                self._current_ambiance = theme_key
                self._ambiance_enabled = True
                # 找到主题名称
                theme_name = next((t["name"] for t in self._ambiance_themes if t["key"] == theme_key), theme_key)
                self._append_message("system", f"🎵 正在播放: {theme_name}")
        else:
            # 切换开关
            if self._ambiance_enabled:
                self._ambiance_player.stop()
                self._ambiance_enabled = False
                self._append_message("system", "🔇 环境音已关闭")
            else:
                self._append_message("system", "请选择一个环境音主题")

    def toggle_typewriter_sound(self, enabled: bool = None):
        """切换打字机音效"""
        if enabled is None:
            enabled = not self._typewriter_enabled

        self._typewriter_enabled = enabled
        if self._typewriter_player:
            self._typewriter_player.toggle(enabled)

        if self.config_manager:
            self.config_manager.set("assistant_typewriter_sound", enabled)
            self.config_manager.save()

        status = "开启" if enabled else "关闭"
        self._append_message("system", f"⌨️ 打字机音效已{status}")

    def get_ambiance_themes(self):
        """获取环境音主题列表"""
        return self._ambiance_themes

    def _show_ambiance_menu(self):
        """显示环境音选择菜单"""
        if not self._ambiance_player:
            self._append_message("system", "⚠️ 环境音播放器未初始化，请先确保已正确设置")
            return

        menu = tk.Menu(self, tearoff=0, bg="#424242", fg="white")

        # 添加关闭选项
        if self._ambiance_enabled:
            menu.add_command(
                label="🔇 关闭环境音",
                command=lambda: self.toggle_ambiance(self._current_ambiance)
            )
            menu.add_separator()

        # 添加各个主题
        for theme in self._ambiance_themes:
            available = theme.get("available", True)
            icon = theme["icon"]
            name = theme["name"]
            key = theme["key"]

            # 标记当前播放的主题
            if key == self._current_ambiance:
                label = f"▶ {icon} {name} (正在播放)"
            elif not available:
                label = f"○ {icon} {name} (无音频文件)"
            else:
                label = f"  {icon} {name}"

            if available or key == self._current_ambiance:
                menu.add_command(label=label, command=lambda k=key: self.toggle_ambiance(k))
            else:
                menu.add_command(label=label, state="disabled")

        menu.add_separator()
        menu.add_command(label="ℹ️ 音频文件说明", command=self._show_ambiance_help)

        # 显示菜单
        try:
            x = self.winfo_x() + 50
            y = self.winfo_y() + 100
            menu.post(x, y)
        except Exception:
            pass

    def _show_ambiance_help(self):
        """显示环境音帮助信息"""
        help_text = """环境音功能说明：

将音频文件放入 writer_data/sounds/ 目录即可。

支持的文件格式：.mp3, .wav, .ogg

文件命名规则：
  - rain.mp3 → 雨声
  - cafe.mp3 → 咖啡厅
  - night.mp3 → 夜晚
  - city.mp3 → 城市
  - nature.mp3 → 自然
  - sea.mp3 → 海浪
  - fire.mp3 → 壁炉

您可以根据需要添加自己的环境音文件。"""
        self._append_message("system", help_text)

    def _init_integrations(self):
        """初始化集成管理器"""
        # 获取数据目录
        data_dir = None
        if self.config_manager:
            data_dir = getattr(self.config_manager, 'config_dir', None)
        if not data_dir:
            data_dir = str(Path.home() / ".writer_tool")

        # 创建集成管理器（延迟初始化外部依赖）
        self.integration_manager = AssistantIntegrationManager(
            assistant=self,
            project_manager=self.project_manager,
            gamification_manager=None,  # 将在set_gamification_manager中设置
            command_executor=None,  # 将在set_command_executor中设置
            ai_controller=None,  # 将在set_ai_controller中设置
            stats_manager=None,  # 将在set_stats_manager中设置
            data_dir=data_dir
        )

        # 立绘动态关联映射表
        self._portrait_mappings = {
            # 项目状态 -> 立绘状态
            "scene_added": AssistantState.SUCCESS,
            "character_added": AssistantState.HAPPY,
            "word_milestone": AssistantState.CHEERING,
            "idea_added": AssistantState.EXCITED,
            "research_added": AssistantState.CURIOUS,
            "project_saved": AssistantState.HAPPY,
            "achievement_unlocked": AssistantState.EXCITED,
            "level_up": AssistantState.CHEERING,
            "timeline_event": AssistantState.THINKING,
            "evidence_added": AssistantState.CURIOUS,
        }

    def _start_integrations(self):
        """启动集成监听"""
        if hasattr(self, 'integration_manager'):
            self.integration_manager.start()

    def set_gamification_manager(self, manager):
        """设置游戏化管理器"""
        if hasattr(self, 'integration_manager'):
            self.integration_manager.gamification.set_manager(manager)

    def set_command_executor(self, executor):
        """设置命令执行器（用于Undo/Redo）"""
        if hasattr(self, 'integration_manager'):
            self.integration_manager.commands.set_executor(executor)

    def set_ai_controller(self, controller):
        """设置AI控制器"""
        if hasattr(self, 'integration_manager'):
            self.integration_manager.ai_bridge.set_controller(controller)

    def set_stats_manager(self, manager):
        """设置统计管理器"""
        if hasattr(self, 'integration_manager'):
            self.integration_manager.stats.set_manager(manager)

    def on_project_event(self, event_type: str, **kwargs):
        """处理项目事件（用于立绘动态关联）"""
        # 更新立绘状态
        if event_type in self._portrait_mappings:
            new_state = self._portrait_mappings[event_type]
            self._set_state(new_state, duration=2000)

        # 特殊事件处理
        if event_type == "level_up":
            level = kwargs.get("level", 1)
            self._append_message("system", f"{get_icon('sparkle', '🎉')} 恭喜！你升到了 {level} 级！")
        elif event_type == "achievement_unlocked":
            achievement = kwargs.get("achievement", "")
            self._append_message("system", f"{get_icon('trophy', '🏆')} 成就解锁：{achievement}")
        elif event_type == "word_milestone":
            count = kwargs.get("count", 0)
            self._append_message("system", f"{get_icon('edit', '📝')} 里程碑！今日已写 {count} 字")
        elif event_type == "idea_added":
            title = kwargs.get("title", "")
            self._append_message("system", f"{get_icon('lightbulb', '💡')} 灵感已记录：{title}")
        elif event_type == "research_added":
            title = kwargs.get("title", "")
            self._append_message("system", f"{get_icon('library', '📚')} 研究笔记已添加：{title}")

    def show_mode_guide(self, project_type: str, force: bool = False):
        if not project_type:
            return
        if not hasattr(self, "_last_mode_guide_type"):
            self._last_mode_guide_type = None
            self._last_mode_guide_at = None

        if not force and self._last_mode_guide_type == project_type:
            return

        self._last_mode_guide_type = project_type
        self._last_mode_guide_at = datetime.now()

        type_info = ProjectTypeManager.get_type_info(project_type)
        type_name = type_info.get("name", project_type)

        if project_type == "Suspense":
            message = (
                f"🔎 {type_name} 模式引导\n"
                "悬疑创作 Checklist：\n"
                "1) 受害者/现场/第一发现人已明确\n"
                "2) 关键线索补全“来源 + 揭示场景”\n"
                "3) 双轨时间线对齐（真相 vs 叙述）\n"
                "4) 逻辑校验可随时查看断点"
            )
        elif project_type == "Galgame":
            message = (
                f"🎮 {type_name} 模式引导\n"
                "要不要我帮你生成分支选项提示？\n"
                "告诉我：分支数量、选项口吻、涉及的变量或关键事件。"
            )
        else:
            message = None

        if message:
            self._append_message("assistant", message)


    def _on_voice_input(self, text: str):
        """处理语音输入"""
        if not text:
            return

        # 将语音输入放入输入框并发送
        if hasattr(self, 'chat_view'):
            self.chat_view.set_input(text)
            self._on_send()

    def _on_voice_command(self, command: str):
        """处理语音命令"""
        command_map = {
            "name_generator": self._open_name_generator,
            "dice": self._roll_dice,
            "prompt_card": self._draw_prompt_card,
            "timer": self._toggle_timer,
            "word_count": self._show_word_count,
            "stop": lambda: self.voice_assistant.stop_reading(),
            "help": lambda: self._append_message("assistant", "可用命令：起名、骰子、提示卡、计时、字数统计"),
        }

        if command in command_map:
            command_map[command]()
            self._append_message("system", f"执行语音命令：{command}")

    def set_editor_widget(self, widget):
        """设置编辑器控件引用（用于上下文获取）"""
        self.context_provider.set_editor_widget(widget)

    def set_script_controller(self, controller):
        """设置脚本控制器引用"""
        self.context_provider.set_script_controller(controller)

    def get_context(self):
        """获取当前编辑器上下文"""
        return self.context_provider.get_context()

    def get_selected_text(self) -> str:
        """获取编辑器中选中的文本"""
        ctx = self.context_provider.get_context()
        return ctx.selected_text if ctx.has_selection() else ""

    def _load_skins(self) -> Dict[str, Dict[str, str]]:
        """加载皮肤配置"""
        if self.config_manager:
            skins = self.config_manager.get("assistant_skins", None)
            if skins:
                return skins

        # 默认皮肤
        return {"Default": {}}

    def _load_photos(self) -> list:
        """加载相册数据"""
        if self.config_manager:
            return self.config_manager.get("assistant_photos", [])
        return []

    def _save_pet_system(self):
        """保存养成系统数据"""
        if not self.config_manager:
            return

        # 更新数据
        self.pet_system.data.affection = self.affection
        self.pet_system.data.total_chats = self.total_chats
        self.pet_system.data.unlocked_achievements = self.achievements
        self.pet_system.data.collected_foods = self.collection
        self.pet_system.data.name_gen_count = self.name_gen_count
        self.pet_system.data.prompt_count = self.prompt_count

        self.pet_system.save()


    def _update_avatar_ratio(self):
        """更新当前皮肤的宽高比缓存"""
        self.avatar_ratio = self._get_avatar_ratio()
        self.avatar_render_size = self._calculate_avatar_render_size(self.avatar_size)

    def _get_avatar_ratio(self) -> float:
        """获取当前皮肤的宽高比"""
        if not HAS_PIL:
            return 1.0

        skin_data = self.skins.get(self.current_skin, {})
        if not skin_data:
            return 1.0

        preferred_states = [
            AssistantState.IDLE,
            AssistantState.HAPPY,
            AssistantState.THINKING,
            AssistantState.SUCCESS,
            AssistantState.WRITING,
        ]
        for state in preferred_states:
            ratio = self._read_image_ratio(skin_data.get(state, ""))
            if ratio:
                return ratio

        for path in skin_data.values():
            ratio = self._read_image_ratio(path)
            if ratio:
                return ratio

        return 1.0

    def _read_image_ratio(self, path: str) -> Optional[float]:
        if not path or not os.path.exists(path):
            return None
        try:
            with Image.open(path) as img:
                width, height = img.size
            if width > 0 and height > 0:
                return width / height
        except Exception:
            return None
        return None

    def _calculate_avatar_render_size(self, base_size: int) -> tuple:
        """根据宽高比计算渲染尺寸（以高度为基准）"""
        ratio = self.avatar_ratio if hasattr(self, "avatar_ratio") and self.avatar_ratio else 1.0
        width = max(1, int(base_size * ratio))
        return (width, base_size)

    def _setup_window(self):
        """设置窗口属性"""
        from .constants import ASSISTANT_NAME
        self.title(ASSISTANT_NAME)
        self.overrideredirect(True)  # 无边框
        self.attributes("-topmost", True)  # 置顶

        # 透明度
        alpha = 0.95
        if self.config_manager:
            alpha = float(self.config_manager.get("assistant_alpha", 0.95))
        self.attributes("-alpha", alpha)

        # 透明色（Windows）
        theme = ThemeManager.get_theme()
        self.transparent_color = theme.TRANSPARENT_KEY
        self.configure(bg=self.transparent_color)
        if os.name == "nt":
            self.attributes("-transparentcolor", self.transparent_color)

        # 计算尺寸
        size = 120
        if self.config_manager:
            size = int(self.config_manager.get("assistant_avatar_size", 120))

        self.avatar_size = size
        self._update_avatar_ratio()
        self.collapsed_size = (self.avatar_render_size[0] + 30, self.avatar_render_size[1] + 30)
        self.expanded_size = (max(self.avatar_render_size[0] + 80, 300), self.avatar_render_size[1] + 380)

        # 初始位置
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - self.expanded_size[0] - 50
        y = screen_height - self.expanded_size[1] - 100

        curr_size = self.expanded_size if self.is_expanded else self.collapsed_size
        self.geometry(f"{curr_size[0]}x{curr_size[1]}+{x}+{y}")
        self._default_expanded_size = self.expanded_size

    def _setup_ui(self):
        """设置UI组件"""
        # 主容器
        self.main_frame = tk.Frame(self, bg=self.transparent_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 形象区域
        self._setup_avatar_area()

        # 2. 交互区域
        self._setup_content_area()

        # 初始状态
        if not self.is_expanded:
            self.content_container.pack_forget()

    def _setup_avatar_area(self):
        """设置形象区域"""
        self.avatar_frame = tk.Frame(self.main_frame, bg=self.transparent_color)
        self.avatar_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        self.avatar_view = AvatarView(self.avatar_frame, self)
        self.avatar_view.pack(fill=tk.BOTH, expand=True)

        # Alias for compatibility with external integrations
        self.avatar_label = self.avatar_view.avatar_label
        self.status_label = self.avatar_view.status_label
        self.level_label = self.avatar_view.level_label
        self.mood_label = self.avatar_view.mood_label

    def _setup_content_area(self):
        """设置内容区域"""
        self.content_container = tk.Frame(self.main_frame, bg="#2D2D2D")
        self.content_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 模式内容区（休闲/反推导等）
        self.mode_container = tk.Frame(self.content_container, bg="#2D2D2D")
        self.mode_container.pack(fill=tk.BOTH, expand=True)

        self.home_panel = LeisureHomePanel(self.mode_container, self)
        self.home_panel.pack(fill=tk.BOTH, expand=True, padx=2, pady=(2, 6))

        self.chat_view = ChatView(self.content_container, self)
        
        # Aliases for compatibility
        self.input_text = self.chat_view.input_text
        self.chat_display = self.chat_view.chat_display
        self.quick_frame = self.chat_view.quick_frame
        self.voice_btn = self.chat_view.voice_btn

    def _update_quick_buttons(self):
        """更新快捷按钮"""
        if hasattr(self, 'chat_view'):
            self.chat_view.update_quick_buttons()

    def _load_avatar_images(self):
        """加载立绘图片"""
        if hasattr(self, 'avatar_view'):
            self.avatar_view.load_images()
            self.avatar_render_size = self.avatar_view.avatar_render_size

    # ============================================================
    # 状态管理
    # ============================================================

    def set_state(self, state: str, duration: int = 0):
        """设置助手状态（公共接口）"""
        self._set_state(state, duration)

    def _set_state(self, state: str, duration: int = 0):
        """设置助手状态"""
        self.state = state
        self._update_avatar()

        if duration > 0:
            self.after(duration, lambda: self._set_state(AssistantState.IDLE))

    def _update_avatar(self):
        """更新头像显示"""
        if hasattr(self, 'avatar_view'):
            self.avatar_view.update_avatar()

    # ============================================================
    # 专注模式联动
    # ============================================================

    def _enter_focus_mode(self):
        """进入专注模式 - 减少干扰"""
        self._is_in_focus_mode = True
        # 暂停闲聊
        if hasattr(self, '_idle_chat_job') and self._idle_chat_job:
            self.after_cancel(self._idle_chat_job)
            self._idle_chat_job = None
        # 最小化聊天窗口
        if self.chat_visible:
            self._toggle_chat()

    def _exit_focus_mode(self):
        """退出专注模式 - 恢复正常"""
        self._is_in_focus_mode = False
        # 恢复闲聊
        self._schedule_idle_chat()

    def _enter_zen_mode(self):
        """进入禅模式 - 最小化所有干扰"""
        self._is_in_zen_mode = True
        self._enter_focus_mode()  # 继承专注模式行为
        # 最小化助手窗口到托盘区域
        self._pre_zen_opacity = self.attributes("-alpha")
        self.attributes("-alpha", 0.3)  # 半透明

    def _exit_zen_mode(self):
        """退出禅模式 - 恢复显示"""
        self._is_in_zen_mode = False
        # 恢复透明度
        if hasattr(self, '_pre_zen_opacity'):
            self.attributes("-alpha", self._pre_zen_opacity)
        else:
            self.attributes("-alpha", 0.95)
        self._exit_focus_mode()

    @property
    def is_in_focus_mode(self) -> bool:
        """检查是否处于专注模式"""
        return getattr(self, '_is_in_focus_mode', False)

    @property
    def is_in_zen_mode(self) -> bool:
        """检查是否处于禅模式"""
        return getattr(self, '_is_in_zen_mode', False)

    # ============================================================
    # 拖拽和边缘吸附
    # ============================================================



    def _on_avatar_click(self):
        """处理头像点击互动"""
        # 特殊场景：学校事件
        if self.state == AssistantState.SCHOOL:
            if self._trigger_school_event():
                return

        # 获取互动结果
        result = self.interaction_manager.get_interaction(
            self.state,
            self.affection
        )

        if result:
            target_state, duration, dialogue = result

            # 特殊处理：醒来序列
            if target_state == AssistantState.WAKING_UP:
                self._play_wake_up_sequence()
                return

            # 设置新状态
            if target_state:
                self._set_state(target_state, duration)

            # 显示对话（如果有）
            if dialogue:
                self._append_message("assistant", dialogue)

            # 增加好感度（被互动时小幅增加）
            if target_state not in [AssistantState.ANNOYED]:
                self.pet_system.add_affection(1)
                self.affection = self.pet_system.data.affection

    def _play_wake_up_sequence(self):
        """播放醒来动画序列"""
        sequence = self.interaction_manager.get_wake_up_sequence()
        if not sequence:
            return

        def play_step(index: int):
            if index >= len(sequence):
                # 序列结束，恢复idle
                self._set_state(AssistantState.IDLE)
                return

            state, duration, dialogue = sequence[index]
            self._set_state(state)

            if dialogue:
                self._append_message("assistant", dialogue)

            # 调度下一步
            self.after(duration, lambda: play_step(index + 1))

        play_step(0)

    def _toggle_expand(self, event=None):
        """切换展开/收起"""
        self._refresh_activity()
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.content_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            self.geometry(f"{self.expanded_size[0]}x{self.expanded_size[1]}")
        else:
            self.content_container.pack_forget()
            self.geometry(f"{self.collapsed_size[0]}x{self.collapsed_size[1]}")

    def _clamp_avatar_size(self, size: int) -> int:
        """限制头像尺寸范围"""
        return max(30, min(500, size))

    def _apply_avatar_size(self, new_size: int, save: bool = True, force_reload: bool = False):
        """应用头像尺寸调整"""
        new_size = self._clamp_avatar_size(new_size)
        
        # Avoid redundant updates
        if not force_reload and new_size == self.avatar_size:
            if hasattr(self, 'avatar_view') and self.avatar_view.avatar_render_size == self.avatar_render_size:
                return

        self.avatar_size = new_size

        if hasattr(self, 'avatar_view'):
            self.avatar_view.load_images()
            self.avatar_render_size = self.avatar_view.avatar_render_size
            self.avatar_view.update_avatar()
        else:
            return 

        self.collapsed_size = (self.avatar_render_size[0] + 30, self.avatar_render_size[1] + 30)
        self.expanded_size = (max(self.avatar_render_size[0] + 80, 300), self.avatar_render_size[1] + 380)
        if getattr(self, "_active_mode", "leisure") != "reverse_engineering":
            self._default_expanded_size = self.expanded_size

        curr_size = self.expanded_size if self.is_expanded else self.collapsed_size
        self.geometry(f"{curr_size[0]}x{curr_size[1]}")

        if self.config_manager and save:
            self.config_manager.set("assistant_avatar_size", new_size)
            self.config_manager.save()

    # ============================================================
    # 右键菜单
    # ============================================================

    def _show_context_menu(self, event=None):
        """显示右键菜单"""
        self._refresh_activity()
        AssistantContextMenu(self).show(event)

    # ============================================================
    # 消息处理
    # ============================================================

    def _get_affection_tier(self) -> str:
        """根据好感度获取语气层级"""
        if self.affection >= 200:
            return "close"
        if self.affection >= 100:
            return "warm"
        if self.affection >= 50:
            return "friendly"
        return "neutral"

    def _apply_affection_tone(self, content: str) -> str:
        """根据好感度微调助手语气（不显式显示数值）"""
        if not content or "\n" in content or len(content) > 120:
            return content

        if content.endswith(("～", "~")) or content[-1] in ("呢", "呀", "啦"):
            return content

        tier = self._get_affection_tier()
        if tier == "neutral":
            return content

        suffix_map = {
            "friendly": ("呢", "呀"),
            "warm": ("呀", "～"),
            "close": ("呢", "呀", "～", "啦"),
        }
        suffixes = suffix_map.get(tier, ())
        if not suffixes:
            return content

        # 适度随机，避免每句都带尾音
        chance = {"friendly": 0.4, "warm": 0.7, "close": 0.85}.get(tier, 0.5)
        if random.random() > chance:
            return content

        suffix = random.choice(suffixes)
        if content.endswith(("。", "！", "?", "？", "!")):
            return f"{content[:-1]}{suffix}{content[-1]}"
        return f"{content}{suffix}"

    def _safe_append_message(self, tag: str, content: str):
        """线程安全的追加消息"""
        self.after(0, lambda: self._append_message(tag, content))

    def _append_message(self, tag: str, content: str):
        """追加消息到聊天区"""
        if tag == "assistant":
            content = self._apply_affection_tone(content)
        
        if hasattr(self, 'chat_view'):
            self.chat_view.append_message(tag, content)

    def _append_streaming_token(self, token: str):
        """追加流式输出的token"""
        if hasattr(self, 'chat_view'):
            self.chat_view.append_streaming_token(token)

    def _show_clipboard_notification(self, title: str, preview: str, actions: list):
        """显示剪贴板内容检测通知"""
        self._pending_clipboard_text = self.clipboard_monitor.get_current() if hasattr(self, 'clipboard_monitor') else ""
        self._pending_clipboard_actions = actions

        action_labels = "、".join([a[0] for a in actions[:3]])
        self._append_message("system", f"📋 {title}\n预览: {preview}\n可用操作: {action_labels}")

        if hasattr(self, 'chat_view'):
            self.chat_view.show_clipboard_actions(
                actions,
                self._execute_clipboard_action,
                self._cancel_clipboard_action
            )

    def _execute_clipboard_action(self, prompt: str):
        """执行剪贴板操作"""
        if hasattr(self, '_pending_clipboard_text') and self._pending_clipboard_text:
            full_prompt = f"{prompt}\n\n{self._pending_clipboard_text}"
            if hasattr(self, 'chat_view'):
                self.chat_view.set_input(full_prompt)
            self._on_send()

        if hasattr(self, 'chat_view'):
            self.chat_view.update_quick_buttons()

    def _cancel_clipboard_action(self):
        """取消剪贴板操作"""
        self._pending_clipboard_text = ""
        self._pending_clipboard_actions = []
        if hasattr(self, 'chat_view'):
            self.chat_view.update_quick_buttons()
        self._append_message("system", "已取消剪贴板操作")

    def _on_enter(self, event):
        """处理回车键"""
        if not (event.state & 0x1):  # 不是Shift+Enter
            self._on_send()
            return "break"

    def _on_send(self, event=None):
        """发送消息"""
        self._refresh_activity()

        if self.state == AssistantState.THINKING:
            return

        if not hasattr(self, 'chat_view'):
            return

        user_input = self.chat_view.get_input()
        if not user_input:
            return

        self.chat_view.clear_input()
        self._append_message("user", user_input)

        # 记录对话 (自动处理首次成就、计数)
        self.pet_system.record_chat()
        self.total_chats = self.pet_system.data.total_chats # Sync local
        self._save_pet_system()
        self._refresh_home_panel()

        # 检查是否在游戏中
        if self.game_manager.current_game:
            self._handle_game_input(user_input)
            return

        if self.ai_mode_enabled:
            if hasattr(self.conversation_history, "add_user_message"):
                self.conversation_history.add_user_message(user_input)
            else:
                self.conversation_history.add("user", user_input)
            self._send_to_ai(user_input)
        else:
            self._handle_non_ai_input(user_input)

    def _build_ai_messages(self) -> list:
        """构建带项目上下文的AI消息"""
        system_prompt = self.ai_handler.DEFAULT_SYSTEM_PROMPT

        project_context = ProjectContextBuilder.build(self.project_manager)

        ctx = self.context_provider.get_context()
        ctx_parts = []
        if ctx.current_scene:
            ctx_parts.append(f"当前场景: {ctx.current_scene}")
        if ctx.current_character:
            ctx_parts.append(f"相关角色: {ctx.current_character}")
        if ctx.selected_text:
            preview = ctx.selected_text[:200] + "..." if len(ctx.selected_text) > 200 else ctx.selected_text
            ctx_parts.append(f"选中内容: {preview}")
        elif ctx.current_paragraph:
            preview = ctx.current_paragraph[:200] + "..." if len(ctx.current_paragraph) > 200 else ctx.current_paragraph
            ctx_parts.append(f"当前段落: {preview}")

        if ctx_parts:
            context_hint = "\n".join(ctx_parts)
            if project_context:
                project_context += f"\n\n【编辑器上下文】\n{context_hint}"
            else:
                project_context = f"【编辑器上下文】\n{context_hint}"

        messages = [{"role": "system", "content": system_prompt}]
        if project_context:
            messages[0]["content"] += f"\n\n{project_context}"

        messages.extend(self.conversation_history.get_messages())
        return messages

    def _send_to_ai(self, user_input: str):
        """发送到AI"""
        self._set_state(AssistantState.THINKING)
        self._append_message("assistant", "")  # 占位

        def on_token(token):
            if hasattr(self, 'chat_view'):
                # 确保在主线程更新UI
                self.after(0, lambda: self.chat_view.append_streaming_token(token))

        def on_complete(response):
            self.after(0, lambda: self._on_ai_complete(response))

        def on_error(error):
            self.after(0, lambda: self._on_ai_error(str(error)))

        try:
            messages = self._build_ai_messages()
            self.ai_handler.client.chat_stream(
                messages=messages,
                on_token=on_token,
                on_complete=on_complete,
                on_error=on_error
            )
        except Exception as e:
            on_error(str(e))

    def _on_ai_complete(self, response: str):
        """AI响应完成"""
        if hasattr(self.conversation_history, "add_assistant_message"):
            self.conversation_history.add_assistant_message(response)
        else:
            self.conversation_history.add("assistant", response)

        # 检测AI响应中的情绪
        detected = self.emotion_detector.detect(response, AI_EMOTION_KEYWORDS)
        if detected:
            state = self._get_emotion_state(detected)
            self._set_state(state, duration=2000)
        else:
            self._set_state(AssistantState.SUCCESS, duration=1500)

        # 完成后换行
        if hasattr(self, 'chat_view'):
            self.chat_view.append_streaming_token("\n\n")

        # 自动朗读响应
        self._read_response(response)

        self._add_affection(1)
        self._save_pet_system()

    def _on_ai_error(self, error: str):
        """AI错误处理"""
        self._set_state(AssistantState.ERROR, duration=2000)
        self._append_message("error", f"AI响应失败: {error}")

    def _handle_non_ai_input(self, user_input: str):
        """处理无AI模式的输入"""
        user_input_lower = user_input.lower()

        # 情绪检测
        detected = self.emotion_detector.detect(user_input)

        # 关键词匹配
        if any(k in user_input_lower for k in ["起名", "名字", "取名", "命名"]):
            self._set_state(AssistantState.CURIOUS, duration=1500)
            self._append_message("assistant", "好的，我来帮你起名！")
            self._open_name_generator()
        elif any(k in user_input_lower for k in ["灵感", "提示", "卡片", "写什么"]):
            self._set_state(AssistantState.EXCITED, duration=2000)
            self._append_message("assistant", "来抽一张写作提示卡吧~")
            self._draw_prompt_card()
        elif any(k in user_input_lower for k in ["骰子", "随机", "掷"]):
            self._set_state(AssistantState.EXCITED, duration=1500)
            self._append_message("assistant", "让我来掷骰子！")
            self._roll_dice()
        elif any(k in user_input_lower for k in ["计时", "番茄", "专注"]):
            self._set_state(AssistantState.CHEERING, duration=1500)
            self._toggle_timer()
        elif any(k in user_input_lower for k in ["字数", "统计"]):
            self._set_state(AssistantState.READING, duration=1500)
            self._show_word_count()
        elif any(k in user_input_lower for k in ["你好", "嗨", "hi", "hello", "早", "晚"]):
            self._greet_assistant()
        elif any(k in user_input_lower for k in ["加油", "鼓励"]):
            self._cheer_user()
        elif any(k in user_input_lower for k in ["晚安", "睡了"]):
            self._say_goodnight()
        elif detected == "sad" or detected == "worried":
            self._comfort_user(detected)
        elif detected == "love":
            self._respond_to_love()
        else:
            # 随机回复
            responses = [
                "我在听呢~",
                "有什么我能帮到你的吗？",
                "继续写作吧，我会一直陪着你~",
                "需要灵感可以抽提示卡哦~",
                "今天的状态挺好呢~",
            ]
            self._append_message("assistant", random.choice(responses))
            self._add_affection(1)

    # ============================================================
    # 工具功能
    # ============================================================

    def _use_tool(self, tool_id: str):
        """使用工具"""
        self._refresh_activity()

        if tool_id == "name_generator":
            self._open_name_generator()
        elif tool_id == "prompt_card":
            self._draw_prompt_card()
        elif tool_id == "dice":
            self._roll_dice()
        elif tool_id == "timer":
            self._toggle_timer()
        elif tool_id == "word_count":
            self._show_word_count()
        elif tool_id == "quick_note":
            self._open_quick_note()
        elif tool_id == "character_card":
            self._open_character_card()
        elif tool_id == "scene_generator":
            self._open_scene_generator()
        elif tool_id == "ambiance":
            self._show_ambiance_menu()
        elif tool_id == "typewriter":
            self.toggle_typewriter_sound()

    def _use_ai_prompt(self, idx: int):
        """使用AI提示"""
        self._refresh_activity()
        if not hasattr(self, 'chat_view'):
            return

        if idx < len(QUICK_PROMPTS_AI):
            name, prompt = QUICK_PROMPTS_AI[idx]
            current = self.chat_view.get_input()
            if current:
                self.chat_view.set_input(f"{prompt}\n\n{current}")
            else:
                self.chat_view.set_input(prompt)
            self.chat_view.focus_input()

    def _open_name_generator(self):
        """打开起名生成器"""
        dlg = NameGeneratorDialog(self)
        self.wait_window(dlg)

        if dlg.result:
            self._append_message("tool", f"📝 生成的名字：\n{dlg.result}")
            # 记录使用次数并处理成就
            self.pet_system.record_name_gen()
            self.name_gen_count = self.pet_system.data.name_gen_count # Sync local

    def _draw_prompt_card(self):
        """抽取提示卡"""
        prompt = random.choice(WRITING_PROMPTS)
        self._append_message("tool", f"💡 写作提示卡：\n「{prompt}」")
        
        # 记录抽取并处理成就
        self.pet_system.record_prompt_draw()
        self.prompt_count = self.pet_system.data.prompt_count # Sync local

        self._set_state(AssistantState.HAPPY, duration=1500)

    def _roll_dice(self):
        """掷骰子"""
        result = self.dice_roller.roll()
        self._append_message("tool", result["display"])
        
        # 使用 PetSystem 记录骰子（自动处理成就）
        if self.pet_system.record_dice_roll(result["value"]):
             self._unlock_achievement("dice_lucky")

    def _toggle_timer(self):
        """切换计时器"""
        if self.timer_running:
            self.timer_running = False
            if self.timer_id:
                self.after_cancel(self.timer_id)
            self._append_message("tool", "⏹️ 计时已停止")
            self.status_label.configure(text="")
        else:
            dlg = TimerDialog(self)
            self.wait_window(dlg)

            if dlg.result:
                minutes = dlg.result
                self.timer_running = True
                self.timer_end_time = datetime.now().timestamp() + minutes * 60
                self._append_message("tool", f"⏱️ 开始计时 {minutes} 分钟")
                self._update_timer()

    def _update_timer(self):
        """更新计时器"""
        if not self.timer_running:
            return

        remaining = self.timer_end_time - datetime.now().timestamp()
        if remaining <= 0:
            self.timer_running = False
            self._append_message("tool", "🔔 时间到！")
            self.status_label.configure(text="")
            
            # 记录计时器完成
            self.pet_system.record_timer_complete()
            
            self._set_state(AssistantState.HAPPY, duration=2000)
        else:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            self.status_label.configure(text=f"⏱️ {mins:02d}:{secs:02d}")
            self.timer_id = self.after(1000, self._update_timer)

    def _show_word_count(self):
        """显示字数统计"""
        if not self.project_manager:
            self._append_message("tool", "📊 无法统计：未加载项目")
            return

        stats = self.word_counter.count_project(self.project_manager)

        self._append_message("tool",
            f"📊 字数统计：\n"
            f"场景数量: {stats['scene_count']}\n"
            f"场景字数: {stats['scene_chars']:,}\n"
            f"大纲字数: {stats['outline_chars']:,}\n"
            f"总计: {stats['total']:,}")

    def _open_quick_note(self):
        """打开快速笔记"""
        dlg = QuickNoteDialog(self, self.config_manager)
        self.wait_window(dlg)

    def _open_character_card(self):
        """打开角色卡生成器"""
        dlg = CharacterCardDialog(self, self.char_generator)
        self.wait_window(dlg)

    def _open_scene_generator(self):
        """打开场景生成器"""
        dlg = SceneGeneratorDialog(self, self.scene_generator)
        self.wait_window(dlg)

    # ============================================================
    # 学校事件
    # ============================================================

    def _trigger_school_event(self) -> bool:
        """触发学校事件"""
        event = self.school_event_manager.get_random_event()
        if not event:
            return False

        from .dialogs import SchoolEventDialog
        
        while event:
            dlg = SchoolEventDialog(self, event, self.school_event_manager)
            self.wait_window(dlg)

            if dlg.result_index >= 0:
                result = self.school_event_manager.process_choice(dlg.result_index)
                if result["success"]:
                    # 显示结果
                    self._append_message("system", f"{result['message']}")
                    
                    # 应用表情状态
                    if result.get("mood_change", 0) > 0:
                        self._set_state(AssistantState.HAPPY, duration=2000)
                    elif result.get("mood_change", 0) < 0:
                         self._set_state(AssistantState.SAD, duration=2000)

                    # 检查成就
                    if result.get("achievement"):
                        self._unlock_achievement(result["achievement"])
                        
                    self._save_pet_system()
                    
                    # Check for narrative trigger
                    narrative_id = result.get("trigger_narrative_id")
                    if narrative_id:
                        event_data = self.event_system.narrative_manager.start_chain(narrative_id)
                        if event_data:
                            self.event_system._enqueue_event(EventPriority.HIGH, "narrative", **event_data)

                    # Check for immediate next event
                    event = result.get("next_event")
                    if event:
                        continue # Loop to show next event immediately
                    
                    return True # 事件处理完毕
            
            # If dialog closed without choice or no next event
            break

        return True # 事件已触发（即使被忽略）

    # ============================================================
    # 游戏功能
    # ============================================================

    def _start_game(self, game_type: str):
        """开始游戏"""
        self._refresh_activity()

        result = self.game_manager.start_game(game_type)
        if result["success"]:
            self.pet_system.record_game_play()
            self._set_state(AssistantState.EXCITED, duration=1500)
            self._append_message("assistant", result["message"])
            self._refresh_home_panel()
        else:
            self._append_message("error", result.get("message", "无法开始游戏"))

    def _handle_game_input(self, user_input: str):
        """处理游戏输入"""
        result = self.game_manager.process_input(user_input)

        if result.get("message"):
            self._append_message("assistant", result["message"])

        if result.get("won"):
            self._set_state(AssistantState.HAPPY, duration=2000)
            # 使用 PetSystem 记录胜利（自动处理奖励和成就）
            self.pet_system.record_game_win()
            # self._unlock_achievement("game_winner") # record_game_win already checks this
        elif result.get("lost"):
            self._set_state(AssistantState.SAD, duration=1500)
        elif result.get("ended"):
            self._set_state(AssistantState.IDLE)
        else:
            # 游戏继续中
            self._set_state(AssistantState.CURIOUS, duration=1000)

    # ============================================================
    # 互动功能
    # ============================================================

    def _trigger_asana_event(self):
        """触发神本朝奈的随机事件（AI模式）"""
        if not self.ai_mode_enabled or not self.ai_handler.is_ai_enabled():
            return self._idle_chat()  # 回退到普通闲聊

        # 随机事件类型
        event_types = [
            ("poke", 0.3),        # 戳一戳/提醒
            ("comment", 0.4),     # 评价当前写作
            ("encourage", 0.3),   # 加油打气
        ]
        
        # 加权随机
        total = sum(w for t, w in event_types)
        r = random.uniform(0, total)
        upto = 0
        selected_event = "comment"
        for t, w in event_types:
            if upto + w >= r:
                selected_event = t
                break
            upto += w

        prompt = ""
        if selected_event == "poke":
            prompt = "用户正在发呆。请以神本朝奈的身份，用调皮可爱的语气戳一戳用户，或者问问是不是卡文了。可以提供一个脑洞作为建议。"
        elif selected_event == "comment":
            # 获取上下文
            ctx_text = self.get_selected_text() or "（用户当前没有选中文本，可能正在构思）"
            prompt = f"用户正在写作。请以神本朝奈的身份，基于以下片段发表一句简短的感想或吐槽（50字以内）。\n片段：{ctx_text[-200:]}"
        elif selected_event == "encourage":
            prompt = "用户可能累了。请以神本朝奈的身份，用充满元气的语气给前辈加油打气，或者邀请前辈休息一下喝杯茶。"

        # 发送静默请求（不显示在用户发送历史中）
        self.ai_handler.send_system_instruction(prompt)
        self._set_state(AssistantState.HAPPY, duration=3000)

    def _feed_assistant(self):
        """喂食"""
        dlg = FeedDialog(self, FOODS)
        self.wait_window(dlg)

        if dlg.result:
            food = dlg.result
            food_id = next((k for k, v in FOODS.items() if v == food), None)
            
            if not food_id:
                # Fallback if we only have the value object but need the key
                # This depends on how FeedDialog returns result. 
                # Assuming FeedDialog returns the value dict from FOODS.
                # Let's try to reverse lookup or just use a generic ID if not found, 
                # but ideally FeedDialog should return the key or the ID.
                # Looking at FeedDialog implementation (read earlier), it returns the food dict.
                # We need the key for record_feed.
                for k, v in FOODS.items():
                    if v["name"] == food["name"]:
                        food_id = k
                        break
            
            if not food_id:
                food_id = "cookie" # Fallback

            # 使用 PetSystem 记录喂食（自动处理好感、心情、成就）
            result = self.pet_system.record_feed(food_id)
            
            self._append_message("action", f"你喂了{food['name']}~")
            
            # 显示获得的奖励
            affection_gain = result.get("affection_gained", 0)
            mood_gain = result.get("mood_gained", 0)
            # self._append_message("system", f"好感 +{affection_gain}, 心情 +{mood_gain}")

            # 反应
            if food.get("rarity") == "稀有":
                self._set_state(AssistantState.LOVE, duration=2000)
                self._append_message("assistant", f"哇！{food['name']}！这是给我的吗？最喜欢前辈了！💕")
            elif food.get("rarity") == "传说":
                self._set_state(AssistantState.DEVOTED, duration=3000)
                self._append_message("assistant", f"这是...{food['name']}！！前辈太破费了...我会好好珍藏的！🥺💕")
                # unlock call is handled inside record_feed -> check_and_unlock_achievements -> unlock_achievement
                # But record_feed only checks feed counts and collection.
                # legendary_food achievement logic needs to be explicit or inside record_feed logic.
                # Current record_feed implementation in pet_system.py DOES NOT check specifically for 'legendary_food' achievement based on rarity.
                # So we unlock it manually here if rarity is legendary.
                self._unlock_achievement("legendary_food")
            else:
                self._set_state(AssistantState.HAPPY, duration=1500)
                self._append_message("assistant", f"谢谢前辈的{food['name']}~ 味道不错呢！")

            # 同步本地状态变量（用于UI显示）
            self.affection = self.pet_system.data.affection
            self.collection = self.pet_system.data.collected_foods
            self._refresh_home_panel()
            self._show_toast("投喂完成")

    def _greet_assistant(self):
        """打招呼"""
        self._refresh_activity()

        hour = datetime.now().hour
        greeting = ""
        
        if 5 <= hour < 12:
            options = ["前辈早安！今天要写多少字呢？", "新的一天开始了~ 文学部活动也要加油哦！(ง •_•)ง", "早安~ 昨晚睡得好吗？"]
            greeting = random.choice(options)
            self._set_state(AssistantState.MORNING if AssistantState.MORNING in self.avatar_images else AssistantState.HAPPY, duration=2000)
        elif 12 <= hour < 18:
            options = ["午安前辈！", "写作辛苦啦~ 要不要喝杯茶？", "下午好！今天的阳光真不错呢~"]
            greeting = random.choice(options)
            self._set_state(AssistantState.HAPPY, duration=1500)
        else:
            options = ["晚上好前辈！", "今晚是灵感爆发的时间吗？", "夜深了，前辈要注意眼睛哦~"]
            greeting = random.choice(options)
            self._set_state(AssistantState.NIGHT if AssistantState.NIGHT in self.avatar_images else AssistantState.IDLE, duration=2000)

        self._append_message("assistant", greeting)
        self._add_affection(1)
        self.pet_system.record_daily_task("greet")
        self._save_pet_system()
        self._refresh_home_panel()

    def _show_affection(self):
        dlg = AffectionDialog(self, self.pet_system)
        self.wait_window(dlg)

    def _show_achievements(self):
        """显示成就"""
        dlg = AchievementDialog(self, self.achievements, ACHIEVEMENTS)
        self.wait_window(dlg)

    def _show_collection(self):
        """显示收藏"""
        dlg = CollectionDialog(self, self.collection)
        self.wait_window(dlg)

    def _show_event_history(self):
        """显示事件历史"""
        if hasattr(self, "event_system"):
            dlg = EventHistoryDialog(self, self.event_system)
            self.wait_window(dlg)

    def _cheer_user(self):
        """给用户加油"""
        cheers = [
            "加油加油！你一定可以的！💪",
            "相信自己，你写的故事一定很棒！✨",
            "坚持就是胜利！我会一直陪着你~",
            "每一个字都是进步，继续加油！",
            "有我在，慢慢来就好~",
        ]
        self._set_state(AssistantState.CHEERING, duration=2000)
        self._append_message("assistant", random.choice(cheers))
        self._add_affection(2)
        self._save_pet_system()

    def _say_goodnight(self):
        """说晚安"""
        goodnights = [
            "晚安~做个好梦~🌙",
            "早点休息哦，明天继续加油~",
            "晚安，今天辛苦了~",
            "好好休息，明天见~💤",
        ]
        self._set_state(AssistantState.NIGHT if AssistantState.NIGHT in self.avatar_images else AssistantState.IDLE, duration=2000)
        self._append_message("assistant", random.choice(goodnights))
        self._add_affection(2)
        self._save_pet_system()

    def _comfort_user(self, emotion: str):
        """安慰用户"""
        if emotion == "sad":
            comforts = [
                "别难过，一切都会好起来的~",
                "我陪着你呢，有什么想说的吗？",
                "难过的时候，就写下来吧~",
                "抱抱~💕",
            ]
        else:  # worried
            comforts = [
                "别担心，我相信你可以的~",
                "慢慢来，不着急~",
                "深呼吸，你做得很好~",
                "有我陪着你呢~",
            ]

        self._set_state(AssistantState.WORRIED, duration=2000)
        self._append_message("assistant", random.choice(comforts))
        self._add_affection(3)
        self._save_pet_system()

    def _respond_to_love(self):
        """回应喜爱"""
        if self.affection >= 200:
            responses = [
                "我...我也很喜欢你...💕",
                "能一直陪着你，我很幸福~",
                "你是最特别的主人~💕",
            ]
            self._set_state(AssistantState.DEVOTED, duration=3000)
        elif self.affection >= 100:
            responses = [
                "谢谢你~我也很喜欢你~💕",
                "嘿嘿，我们是好朋友~",
                "你真好~💕",
            ]
            self._set_state(AssistantState.BLUSH, duration=2000)
        else:
            responses = [
                "嘿嘿，谢谢~",
                "你真好~",
                "我会继续努力的~",
            ]
            self._set_state(AssistantState.SHY, duration=1500)

        self._append_message("assistant", random.choice(responses))
        self._add_affection(5)
        self._save_pet_system()

    # ============================================================
    # 好感度和成就系统
    # ============================================================

    def _on_achievement_unlocked_callback(self, achievement_id: str):
        """成就解锁回调"""
        achievement = ACHIEVEMENTS.get(achievement_id)
        if achievement:
            self._append_message("system", f"🏆 成就解锁：{achievement['name']}！\n(XP +{achievement.get('xp', 0)})")
            self._set_state(AssistantState.HAPPY, duration=2000)
            
            if hasattr(self, "event_system"):
                self.event_system.handle_achievement_unlocked(achievement_id)

    def _on_level_up_callback(self, new_level: int):
        """升级回调"""
        if hasattr(self, 'level_label'):
            self.level_label.configure(text=f"Lv.{new_level}")
        self._append_message("system", f"🎉 等级提升！现在是 Lv.{new_level}！")
        self._set_state(AssistantState.CHEERING, duration=3000)

    def _add_affection(self, amount: int):
        """增加好感度"""
        # PetSystem 不会自动增加 XP (除了 record_* 方法), 所以这里手动加
        self.pet_system.add_xp(amount * 10)
        
        # 增加好感度 (PetSystem 会自动检查成就)
        self.pet_system.add_affection(amount)
        
        # 同步本地状态
        self.affection = self.pet_system.data.affection

    def _unlock_achievement(self, achievement_id: str):
        """解锁成就 (手动触发)"""
        self.pet_system.unlock_achievement(achievement_id)

    # ============================================================
    # 相册功能
    # ============================================================

    def _save_photos(self):
        """保存相册数据"""
        if self.config_manager:
            self.config_manager.set("assistant_photos", self.photos)
            self.config_manager.save()

    def _resolve_photo_path(self, state: str) -> str:
        """解析当前皮肤下可用的立绘路径"""
        skin_data = self.skins.get(self.current_skin, {})

        if state:
            path = skin_data.get(state, "")
            if path and os.path.exists(path):
                return path

        if state in STATE_FALLBACKS:
            for fallback in STATE_FALLBACKS[state]:
                path = skin_data.get(fallback, "")
                if path and os.path.exists(path):
                    return path

        return ""

    def _add_photo_entry(self, state: str, path: str = "", caption: str = "",
                         source: str = "manual", event_id: str = ""):
        """添加照片记录（统一入口）"""
        if not path:
            path = self._resolve_photo_path(state)
        if not path:
            return None

        photo = {
            "id": str(datetime.now().timestamp()),
            "state": state,
            "state_name": STATE_NAMES.get(state, "未知"),
            "timestamp": datetime.now().isoformat(),
            "path": path,
            "caption": caption,
            "source": source,
            "event_id": event_id,
        }

        self.photos.append(photo)
        self._save_photos()
        self._check_photo_achievements()
        return photo

    def _add_event_photo(self, state: str, event_id: str = "", announce: bool = False):
        """事件系统添加照片"""
        photo = self._add_photo_entry(state=state, source="event", event_id=event_id)
        if photo and announce:
            emoji = STATE_EMOJIS.get(state, "📸")
            name = STATE_NAMES.get(state, state)
            self._append_message("system", f"{emoji} 相册新增：{name}")
        return photo

    def _check_photo_achievements(self):
        """检查相册相关成就"""
        total = len(self.photos)
        if total >= 1:
            self._unlock_achievement("first_photo")
        if total >= 10:
            self._unlock_achievement("photo_collector")

        unique_states = {p.get("state") for p in self.photos if p.get("state") and p.get("state") != "custom"}
        if len(unique_states) >= 10:
            self._unlock_achievement("diverse_collector")
        if len(unique_states) >= 20:
            self._unlock_achievement("master_collector")

        festival_states = {key for key, _ in self.STATE_CATEGORIES.get("节日状态", [])}
        costume_states = {key for key, _ in self.STATE_CATEGORIES.get("服装状态", [])}
        season_states = {key for key, _ in self.STATE_CATEGORIES.get("季节状态", [])}

        if festival_states and festival_states.issubset(unique_states):
            self._unlock_achievement("festival_master")
        if costume_states and costume_states.issubset(unique_states):
            self._unlock_achievement("costume_master")
        if season_states and season_states.issubset(unique_states):
            self._unlock_achievement("season_master")

    def _capture_current(self):
        """拍摄当前立绘"""
        if not self.current_avatar_image:
            messagebox.showinfo("提示", "当前没有可拍摄的立绘")
            return

        photo = self._add_photo_entry(state=self.state)
        if not photo:
            messagebox.showinfo("提示", "当前立绘未配置路径，无法拍摄")
            return

        self._append_message("system", f"📸 拍摄成功！{STATE_EMOJIS.get(self.state, '')} {STATE_NAMES.get(self.state, '')}")
        self._set_state(AssistantState.HAPPY, duration=1500)

    def _open_album(self):
        """打开相册"""
        dlg = AlbumDialog(self, self.photos, self.config_manager, STATE_EMOJIS)
        self.wait_window(dlg)

        if dlg.result:
            self.photos = dlg.result
            self._save_photos()

    def _show_album_stats(self):
        """显示相册统计"""
        total = len(self.photos)
        state_counts = {}
        for photo in self.photos:
            state = photo.get("state", "unknown")
            state_counts[state] = state_counts.get(state, 0) + 1

        stats_text = f"📷 相册统计\n总计：{total} 张照片\n\n"
        for state, count in sorted(state_counts.items(), key=lambda x: -x[1])[:10]:
            emoji = STATE_EMOJIS.get(state, "📷")
            name = STATE_NAMES.get(state, state)
            stats_text += f"{emoji} {name}: {count}\n"

        messagebox.showinfo("相册统计", stats_text)

    # ============================================================
    # 设置功能
    # ============================================================

    def _open_wardrobe(self):
        """打开衣橱"""
        dlg = WardrobeDialog(self, self.skins, self.current_skin, self.STATE_CATEGORIES)
        self.wait_window(dlg)

        if dlg.result:
            self.skins = dlg.result["skins"]
            self.current_skin = dlg.result["current"]

            if self.config_manager:
                self.config_manager.set("assistant_skins", self.skins)
                self.config_manager.set("assistant_current_skin", self.current_skin)
                self.config_manager.save()

            # 重新加载立绘并更新尺寸比例
            self._update_avatar_ratio()
            self._apply_avatar_size(self.avatar_size, save=False, force_reload=True)

    def _open_settings(self):
        """打开设置"""
        dlg = AssistantSettingsDialog(self, self.config_manager)
        self.wait_window(dlg)

        if dlg.result:
            FloatingAssistantManager.apply_settings(
                self.config_manager,
                dlg.result,
                save=True
            )
            if dlg.result.get("photos_updated"):
                self.photos = self._load_photos()
                self._check_photo_achievements()

    def _clear_conversation(self):
        """清空对话"""
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.configure(state=tk.DISABLED)
        self.conversation_history.clear()
        self._append_message("system", "对话已清空")

    def show_option_dialog(self, message: str, options: list, callback):
        """显示选项对话框 (用于叙事链)"""
        dlg = tk.Toplevel(self)
        dlg.title("互动")
        # 动态高度
        height = 100 + len(options) * 40
        dlg.geometry(f"350x{height}")
        dlg.transient(self)
        dlg.grab_set()
        
        # 居中显示在助手附近
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - 175
            y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
            dlg.geometry(f"+{x}+{y}")
        except:
            pass
        
        # 消息内容
        ttk.Label(dlg, text=message, wraplength=320, padding=15, 
                  font=("Microsoft YaHei", 10), anchor="center").pack(fill=tk.BOTH, expand=True)
        
        # 选项按钮
        btn_frame = ttk.Frame(dlg, padding=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        for i, opt in enumerate(options):
            text = opt.get("text", "选项")
            ttk.Button(btn_frame, text=text, 
                       command=lambda idx=i: [callback(idx), dlg.destroy()]).pack(fill=tk.X, pady=3)

    # ============================================================
    # 语音功能
    # ============================================================

    def _toggle_voice_input(self, event=None):
        """切换语音输入"""
        self._refresh_activity()

        if not self.voice_assistant.has_recognition:
            deps = check_voice_dependencies()
            if not deps["speech_recognition"]:
                self._append_message("error", "语音识别不可用。请安装：pip install SpeechRecognition pyaudio")
                return

        if self.voice_assistant.recognizer.state.value == "listening":
            # 停止监听
            self.voice_assistant.stop_voice_input()
            self._update_voice_button()
            self._append_message("system", "🎤 语音输入已停止")
        else:
            # 开始监听
            self.voice_assistant.start_voice_input(continuous=False)
            self._update_voice_button()
            self._append_message("system", "🎤 正在监听...请说话")
            self._set_state(AssistantState.CURIOUS, duration=5000)

    def _update_voice_button(self):
        """更新语音按钮状态"""
        if hasattr(self, 'chat_view'):
            is_listening = self.voice_assistant.recognizer.state.value == "listening"
            self.chat_view.update_voice_button(is_listening)

    def _read_response(self, text: str):
        """朗读AI响应"""
        if self.auto_speak and self.voice_assistant.has_tts:
            self.voice_assistant.read_text(text)

    def _stop_reading(self):
        """停止朗读"""
        if self.voice_assistant.has_tts:
            self.voice_assistant.stop_reading()

    def _read_last_response(self):
        """朗读最后一条响应"""
        if not self.voice_assistant.has_tts:
            return

        # 获取最后一条助手消息
        messages = self.conversation_history.get_messages()
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                self.voice_assistant.read_text(msg.get("content", ""))
                self._append_message("system", "🔊 正在朗读...")
                break

    def _toggle_auto_speak(self):
        """切换自动朗读"""
        self.auto_speak = not self.auto_speak
        if self.config_manager:
            self.config_manager.set("assistant_auto_speak", self.auto_speak)
            self.config_manager.save()

        status = "已开启" if self.auto_speak else "已关闭"
        self._append_message("system", f"🔊 自动朗读{status}")

    def _show_voice_install_guide(self):
        """显示语音安装指南"""
        guide = get_installation_guide()
        messagebox.showinfo("语音功能安装指南", guide)

    # ============================================================
    # 上下文功能
    # ============================================================

    def _insert_context(self, event=None):
        """插入编辑器上下文到输入框"""
        self._refresh_activity()

        ctx = self.context_provider.get_context()

        if ctx.has_selection():
            # 有选中文本，直接插入
            self.input_text.insert(tk.END, ctx.selected_text)
            self._append_message("system", f"📋 已插入选中文本 ({len(ctx.selected_text)}字)")
        elif ctx.current_paragraph:
            # 插入当前段落
            self.input_text.insert(tk.END, ctx.current_paragraph)
            self._append_message("system", f"📋 已插入当前段落 ({len(ctx.current_paragraph)}字)")
        else:
            self._append_message("system", "📋 没有可用的上下文（请在编辑器中选中文本或将光标放在段落中）")

    def _show_context_info(self):
        """显示当前上下文信息"""
        ctx = self.context_provider.get_context()

        info = f"📋 上下文信息：\n"
        info += f"光标位置: 第{ctx.cursor_position[0]}行，第{ctx.cursor_position[1]}列\n"
        info += f"总字数: {ctx.total_chars}\n"

        if ctx.current_scene:
            info += f"当前场景: {ctx.current_scene}\n"
        if ctx.current_character:
            info += f"相关角色: {ctx.current_character}\n"
        if ctx.selected_text:
            preview = ctx.selected_text[:100] + "..." if len(ctx.selected_text) > 100 else ctx.selected_text
            info += f"选中文本: {preview}\n"

        self._append_message("tool", info)

    def send_selected_for_expansion(self):
        """将选中文本发送进行扩写"""
        text = self.context_provider.get_selected_or_paragraph()
        if text:
            prompt = f"请扩写以下内容，增加细节和描写：\n\n{text}"
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", prompt)
            self._on_send()
        else:
            self._append_message("error", "请先在编辑器中选中要扩写的文本")

    def send_selected_for_polish(self):
        """将选中文本发送进行润色"""
        text = self.context_provider.get_selected_or_paragraph()
        if text:
            prompt = f"请润色以下内容，使其更加流畅优美：\n\n{text}"
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", prompt)
            self._on_send()
        else:
            self._append_message("error", "请先在编辑器中选中要润色的文本")

    def send_selected_for_continue(self):
        """将选中文本发送进行续写"""
        text = self.context_provider.get_selected_or_paragraph()
        if text:
            prompt = f"请续写以下内容：\n\n{text}"
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", prompt)
            self._on_send()
        else:
            self._append_message("error", "请先在编辑器中选中要续写的文本")

    # ============================================================
    # 辅助方法
    # ============================================================

    def _get_emotion_state(self, emotion: str) -> str:
        """将情绪映射到状态"""
        mapping = {
            "happy": AssistantState.HAPPY,
            "sad": AssistantState.SAD,
            "excited": AssistantState.EXCITED,
            "shy": AssistantState.SHY,
            "angry": AssistantState.ANGRY,
            "surprised": AssistantState.SURPRISED,
            "curious": AssistantState.CURIOUS,
            "love": AssistantState.LOVE,
            "worried": AssistantState.WORRIED,
            "cheering": AssistantState.CHEERING,
            "success": AssistantState.SUCCESS,
        }
        return mapping.get(emotion, AssistantState.IDLE)

    def _refresh_activity(self):
        """刷新活动时间"""
        self.last_activity_time = datetime.now()
        if hasattr(self, "event_system"):
            self.event_system.check_time_events()

    def _start_idle_timer(self):
        """启动闲聊定时器"""
        enable = False
        interval = 10

        if self.config_manager:
            enable = self.config_manager.get("enable_idle_chat", False)
            interval = self.config_manager.get("idle_interval", 10)

        if not enable:
            return

        def check_idle():
            if not self.winfo_exists():
                return

            elapsed = (datetime.now() - self.last_activity_time).total_seconds() / 60
            if elapsed >= interval:
                self._idle_chat()

            self.idle_timer_id = self.after(60000, check_idle)  # 每分钟检查

        self.idle_timer_id = self.after(60000, check_idle)

    def apply_theme(self, global_theme=None):
        """应用主题"""
        if global_theme:
            # 根据全局主题名称同步本地主题管理器
            ThemeManager.set_mode(global_theme.current_theme)
        
        theme = ThemeManager.get_theme()
        
        # 更新窗口透明背景色
        self.transparent_color = theme.TRANSPARENT_KEY
        self.configure(bg=self.transparent_color)
        if os.name == "nt":
            self.attributes("-transparentcolor", self.transparent_color)
            
        # 刷新子组件
        if hasattr(self, 'avatar_view'):
            self.avatar_view.apply_theme()
        if hasattr(self, 'chat_view'):
            self.chat_view.apply_theme()

    def _start_maintenance_timer(self):
        """启动维护定时器（检查日期变更等）"""
        self._last_check_date = datetime.now().date()

        def do_maintenance():
            if not self.winfo_exists():
                return

            # 检查日期变更
            today = datetime.now().date()
            if today != self._last_check_date:
                self._last_check_date = today
                self._check_special_occasions()

            # 心情自然衰减
            self.pet_system.decay_mood()
            
            # 检查时间段事件 (早鸟/夜猫等)
            if hasattr(self, "event_system"):
                self.event_system.check_time_events()

            # 每10分钟检查一次
            self.after(600000, do_maintenance)

        self.after(600000, do_maintenance)

    def _idle_chat(self):
        """闲聊"""
        if self.state == AssistantState.THINKING:
            return

        topic = random.choice(IDLE_CHAT_TOPICS)
        self._append_message("assistant", topic)
        self._set_state(AssistantState.CURIOUS, duration=2000)
        self._refresh_activity()

    def _check_special_occasions(self):
        """检查特殊场合"""
        # 检查节日
        # 使用助手固定生日 5月9日
        festival = self.festival_detector.get_current_festival(
            birthday="05-09",
            created_at=getattr(self, 'created_at', None)
        )
        if festival:
            greeting = self.festival_detector.get_festival_greeting(festival)
            self._append_message("system", greeting)
            
            # 通知事件系统触发成就和照片
            if hasattr(self, 'event_system'):
                self.event_system.handle_festival_event(festival)

            # 如果有对应立绘则切换，否则仅提示
            if festival in self.avatar_images:
                self._set_state(festival)
            return

        # 检查季节
        season = self.season_detector.get_current_season()
        if season:
            greeting = self.season_detector.get_season_greeting(season)
            # 季节提示仅在每天第一次打开时或特定条件下显示比较好，
            # 但这里遵循原逻辑，如果有立绘则可能切换。
            # 为了不频繁干扰，可以只在有立绘时切换状态，但消息可以保留。
            if season in self.avatar_images:
                self._set_state(season)
                # 仅在有状态变化时发送季节问候，避免重复
                self._append_message("system", greeting)
                return

        # 检查每日签到
        daily_result = self.pet_system.check_daily()
        if daily_result.get("is_new_day"):
            bonus = daily_result.get("bonus_affection", 5)
            streak = daily_result.get("streak", 1)
            self._append_message("system", f"🎉 每日签到成功！(已连续 {streak} 天)")
            # pet_system.check_daily() 已自动发放奖励，无需再次调用 _add_affection

        self._refresh_home_panel()

    # ============================================================
    # 快速创建功能（联动项目数据）
    # ============================================================

    def quick_add_character(self):
        """快速添加角色到项目"""
        self._refresh_activity()

        dlg = QuickCharacterDialog(self)
        self.wait_window(dlg)

        if dlg.result:
            name = dlg.result.get("name", "")
            description = dlg.result.get("description", "")
            role = dlg.result.get("role", "配角")

            # 通过集成管理器执行命令
            if hasattr(self, 'integration_manager'):
                success = self.integration_manager.commands.add_character(
                    name=name,
                    description=description,
                    tags=[role]
                )
                if success:
                    self._append_message("system", f"✅ 角色 [{name}] 已添加到项目")
                    self.on_project_event("character_added", name=name)
                else:
                    self._append_message("error", "添加角色失败，请确保项目已打开")
            else:
                self._append_message("error", "集成管理器未初始化")

    def quick_add_scene(self):
        """快速添加场景到项目"""
        self._refresh_activity()

        # 获取项目中已有的地点
        locations = []
        if self.project_manager:
            scenes = self.project_manager.get_scenes()
            locations = list(set(s.get("location", "") for s in scenes if s.get("location")))

        dlg = QuickSceneDialog(self, locations if locations else None)
        self.wait_window(dlg)

        if dlg.result:
            name = dlg.result.get("name", "")
            location = dlg.result.get("location", "")
            time = dlg.result.get("time", "")
            description = dlg.result.get("description", "")

            # 通过集成管理器执行命令
            if hasattr(self, 'integration_manager'):
                success = self.integration_manager.commands.add_scene(
                    name=name,
                    location=location,
                    time=time,
                    content=description
                )
                if success:
                    self._append_message("system", f"✅ 场景 [{name}] 已添加到项目")
                    self.on_project_event("scene_added", name=name)
                else:
                    self._append_message("error", "添加场景失败，请确保项目已打开")
            else:
                self._append_message("error", "集成管理器未初始化")

    def quick_add_idea(self):
        """快速记录灵感"""
        self._refresh_activity()

        # 获取项目中已有的分类
        categories = []
        if self.project_manager and hasattr(self.project_manager, 'project_data'):
            ideas = self.project_manager.project_data.get("ideas", [])
            categories = list(set(i.get("category", "") for i in ideas if i.get("category")))

        dlg = QuickIdeaDialog(self, categories if categories else None)
        self.wait_window(dlg)

        if dlg.result:
            title = dlg.result.get("title", "")
            category = dlg.result.get("category", "")
            content = dlg.result.get("content", "")

            # 直接添加到项目数据（灵感不需要Command模式）
            if self.project_manager and hasattr(self.project_manager, 'project_data'):
                ideas = self.project_manager.project_data.setdefault("ideas", [])
                idea = {
                    "title": title,
                    "category": category,
                    "content": content,
                    "created_at": datetime.now().isoformat(),
                    "status": "pending"
                }
                ideas.append(idea)

                if hasattr(self.project_manager, 'mark_modified'):
                    self.project_manager.mark_modified()

                self._append_message("system", f"💡 灵感 [{title}] 已记录")
                self.on_project_event("idea_added", title=title)

                # 通过EventBus发布事件
                if hasattr(self, 'integration_manager'):
                    self.integration_manager.event_bus.publish_event("idea_added", idea=idea)
            else:
                self._append_message("error", "无法记录灵感，请确保项目已打开")

    def quick_add_research(self):
        """快速添加研究笔记"""
        self._refresh_activity()

        # 获取项目中已有的分类
        categories = []
        if self.project_manager and hasattr(self.project_manager, 'project_data'):
            research = self.project_manager.project_data.get("research", [])
            categories = list(set(r.get("category", "") for r in research if r.get("category")))

        dlg = QuickResearchDialog(self, categories if categories else None)
        self.wait_window(dlg)

        if dlg.result:
            title = dlg.result.get("title", "")
            category = dlg.result.get("category", "")
            content = dlg.result.get("content", "")
            source = dlg.result.get("source", "")

            # 直接添加到项目数据
            if self.project_manager and hasattr(self.project_manager, 'project_data'):
                research = self.project_manager.project_data.setdefault("research", [])
                note = {
                    "title": title,
                    "category": category,
                    "content": content,
                    "source": source,
                    "created_at": datetime.now().isoformat()
                }
                research.append(note)

                if hasattr(self.project_manager, 'mark_modified'):
                    self.project_manager.mark_modified()

                self._append_message("system", f"📚 研究笔记 [{title}] 已添加")
                self.on_project_event("research_added", title=title)

                # 通过EventBus发布事件
                if hasattr(self, 'integration_manager'):
                    self.integration_manager.event_bus.publish_event("research_added", note=note)
            else:
                self._append_message("error", "无法添加研究笔记，请确保项目已打开")

    def get_project_stats(self) -> Dict[str, Any]:
        """获取项目统计信息"""
        stats = {
            "scenes": 0,
            "characters": 0,
            "ideas": 0,
            "research": 0,
            "words": 0,
            "level": 1,
            "xp": 0,
            "daily_words": 0,
        }

        if self.project_manager and hasattr(self.project_manager, 'project_data'):
            data = self.project_manager.project_data
            stats["scenes"] = len(data.get("script", {}).get("scenes", []))
            stats["characters"] = len(data.get("script", {}).get("characters", []))
            stats["ideas"] = len(data.get("ideas", []))
            stats["research"] = len(data.get("research", []))

            # 计算总字数
            for scene in data.get("script", {}).get("scenes", []):
                stats["words"] += len(scene.get("content", ""))

        # 获取游戏化数据
        if hasattr(self, 'integration_manager') and self.integration_manager.gamification:
            gstats = self.integration_manager.gamification.get_stats()
            stats.update(gstats)

        return stats

    def show_stats_panel(self):
        """显示统计面板"""
        self._refresh_activity()

        stats = self.get_project_stats()
        stats_text = f"""📊 项目统计

📝 场景: {stats['scenes']} 个
👥 角色: {stats['characters']} 个
💡 灵感: {stats['ideas']} 条
📚 研究: {stats['research']} 条

✍️ 总字数: {stats['words']} 字
📅 今日字数: {stats.get('daily_words', 0)} 字

⭐ 等级: Lv.{stats.get('level', 1)}
💫 经验: {stats.get('xp', 0)} XP"""

        self._append_message("tool", stats_text)
        self._set_state(AssistantState.SUCCESS, duration=1500)

    def _refresh_home_panel(self):
        if hasattr(self, "home_panel") and self.home_panel:
            try:
                self.home_panel.refresh()
            except Exception:
                pass

    def _get_active_mode(self) -> str:
        """获取主界面当前模式"""
        mode = getattr(self, "_active_mode", None)
        if mode:
            return mode
        if self.parent and hasattr(self.parent, "writer_app"):
            app = getattr(self.parent, "writer_app", None)
            if app and hasattr(app, "sidebar_controller"):
                _, item = app.sidebar_controller.get_current()
                if item in {"training", "reverse_engineering"}:
                    return item
        return "leisure"

    def _open_mode(self, item_key: str):
        """打开主界面并切换到指定模块"""
        if item_key == "reverse_engineering":
            self._enter_reverse_engineering_mode()
            self._maybe_show_mode_tip(item_key)
            return

        self._enter_leisure_mode(hide_main=False)
        if item_key == "training":
            self._active_mode = "training"
            self._refresh_home_panel()

        if not self.parent or not hasattr(self.parent, "writer_app"):
            return
        app = getattr(self.parent, "writer_app", None)
        if not app:
            return
        self._show_main_window()
        if hasattr(app, "sidebar_controller"):
            app.sidebar_controller.navigate_to(item_key)
        self._maybe_show_mode_tip(item_key)

    def _enter_leisure_mode(self, hide_main: bool = True):
        """回到休闲模式（隐藏主界面）"""
        self._active_mode = "leisure"
        if hasattr(self, "home_panel"):
            self._show_mode_panel(self.home_panel)
        self._restore_chat_view()
        self._apply_default_expanded_size()
        if hasattr(self, "chat_view"):
            self.chat_view.update_mode_label()
        if hide_main:
            self._hide_main_window()
        self._refresh_home_panel()

    def _enter_reverse_engineering_mode(self):
        """进入反推导学习模式（嵌入悬浮助手）"""
        self._active_mode = "reverse_engineering"
        self._ensure_reverse_engineering_view()
        if not self.is_expanded:
            self._toggle_expand()
        if self._reverse_container:
            self._show_mode_panel(self._reverse_container)
        if hasattr(self, "chat_view") and self.chat_view.winfo_ismapped():
            self.chat_view.pack_forget()
        self._apply_reverse_expanded_size()
        if hasattr(self, "chat_view"):
            self.chat_view.update_mode_label()

    def _show_mode_panel(self, panel):
        """切换模式面板显示"""
        if not hasattr(self, "mode_container") or not panel:
            return
        for child in self.mode_container.winfo_children():
            child.pack_forget()
        panel.pack(fill=tk.BOTH, expand=True, padx=2, pady=(2, 6))

    def _restore_chat_view(self):
        if hasattr(self, "chat_view") and not self.chat_view.winfo_ismapped():
            self.chat_view.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _apply_default_expanded_size(self):
        if not self._default_expanded_size:
            self._default_expanded_size = self.expanded_size
        self._set_expanded_size(self._default_expanded_size)

    def _apply_reverse_expanded_size(self):
        self._set_expanded_size(self._get_reverse_expanded_size())

    def _set_expanded_size(self, size):
        if not size:
            return
        self.expanded_size = size
        if self.is_expanded:
            x = self.winfo_x()
            y = self.winfo_y()
            self.geometry(f"{size[0]}x{size[1]}+{x}+{y}")

    def _get_reverse_expanded_size(self):
        if self._reverse_expanded_size:
            return self._reverse_expanded_size
        custom_w = 0
        custom_h = 0
        if self.config_manager:
            try:
                custom_w = int(self.config_manager.get("assistant_reverse_width", 0))
                custom_h = int(self.config_manager.get("assistant_reverse_height", 0))
            except Exception:
                custom_w = 0
                custom_h = 0
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        avail_w = max(640, screen_w - 80)
        avail_h = max(480, screen_h - 120)
        target_w = min(1200, avail_w) if custom_w <= 0 else min(custom_w, avail_w)
        target_h = min(900, avail_h) if custom_h <= 0 else min(custom_h, avail_h)
        self._reverse_expanded_size = (target_w, target_h)
        return self._reverse_expanded_size

    def _toggle_reverse_mode(self):
        """在休闲/推理间切换"""
        if self._get_active_mode() == "reverse_engineering":
            self._enter_leisure_mode()
        else:
            self._enter_reverse_engineering_mode()

    def _ensure_reverse_engineering_view(self):
        if self.reverse_engineering_view and self._reverse_container and self._reverse_container.winfo_exists():
            return

        from writer_app.ui.reverse_engineering import ReverseEngineeringView

        self._reverse_container = tk.Frame(self.mode_container, bg="#2D2D2D")

        header = tk.Frame(self._reverse_container, bg="#1E88E5")
        header.pack(fill=tk.X)

        back_btn = tk.Label(
            header,
            text="← 返回",
            font=("Microsoft YaHei UI", 8),
            bg="#1E88E5",
            fg="white",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        back_btn.pack(side=tk.LEFT, padx=(6, 2))
        back_btn.bind("<Button-1>", lambda e: self._enter_leisure_mode())

        title_lbl = tk.Label(
            header,
            text="反推导学习",
            font=("Microsoft YaHei UI", 9, "bold"),
            bg="#1E88E5",
            fg="white"
        )
        title_lbl.pack(side=tk.LEFT, padx=6)

        open_main_btn = tk.Label(
            header,
            text="在主界面打开",
            font=("Microsoft YaHei UI", 8),
            bg="#1E88E5",
            fg="white",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        open_main_btn.pack(side=tk.RIGHT, padx=6)
        open_main_btn.bind("<Button-1>", lambda e: self._open_main_module("reverse_engineering"))

        save_size_btn = tk.Label(
            header,
            text="保存尺寸",
            font=("Microsoft YaHei UI", 8),
            bg="#1E88E5",
            fg="white",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        save_size_btn.pack(side=tk.RIGHT, padx=6)
        save_size_btn.bind("<Button-1>", lambda e: self._save_reverse_window_size())

        body = tk.Frame(self._reverse_container, bg="#2D2D2D")
        body.pack(fill=tk.BOTH, expand=True)

        ai_client = self._get_reverse_ai_client()
        theme_manager = None
        command_executor = None
        app = getattr(self.parent, "writer_app", None) if self.parent else None
        if app:
            theme_manager = getattr(app, "theme_manager", None)
            command_executor = getattr(app, "_execute_command", None)
        if hasattr(self, "integration_manager") and self.integration_manager:
            command_executor = self.integration_manager.commands.execute

        self.reverse_engineering_view = ReverseEngineeringView(
            body,
            self.project_manager,
            ai_client,
            theme_manager,
            self.config_manager,
            command_executor,
            on_navigate=self._navigate_to_module
        )
        self.reverse_engineering_view.pack(fill=tk.BOTH, expand=True)
        self.reverse_engineering_view.set_ai_mode_enabled(self.ai_mode_enabled)

    def _get_reverse_ai_client(self):
        if self._reverse_ai_client:
            return self._reverse_ai_client
        app = getattr(self.parent, "writer_app", None) if self.parent else None
        if app and hasattr(app, "ai_client"):
            self._reverse_ai_client = app.ai_client
        else:
            self._reverse_ai_client = AIClient()
        return self._reverse_ai_client

    def _navigate_to_module(self, item_key: str):
        """从悬浮助手跳转到主界面模块"""
        self._open_main_module(item_key)

    def _open_main_module(self, item_key: str):
        if not self.parent or not hasattr(self.parent, "writer_app"):
            return
        app = getattr(self.parent, "writer_app", None)
        if not app:
            return
        self._show_main_window()
        if hasattr(app, "sidebar_controller"):
            app.sidebar_controller.navigate_to(item_key)

    def _save_reverse_window_size(self):
        """保存当前推理模式窗口尺寸为默认值"""
        if not self.config_manager:
            return
        try:
            width = int(self.winfo_width())
            height = int(self.winfo_height())
        except Exception:
            return
        if width <= 0 or height <= 0:
            return
        self.config_manager.set("assistant_reverse_width", width)
        self.config_manager.set("assistant_reverse_height", height)
        self.config_manager.save()
        self._reverse_expanded_size = (width, height)
        self._append_message("system", f"推理窗口尺寸已保存：{width}×{height}")

    def _get_daily_event_hint(self) -> str:
        """获取今日小事件提示"""
        from datetime import datetime

        if hasattr(self, "event_system") and self.event_system:
            try:
                today = datetime.now().date()
                for item in reversed(self.event_system.get_event_log() or []):
                    ts = item.get("timestamp")
                    if not ts:
                        continue
                    try:
                        when = datetime.fromisoformat(ts).date()
                    except Exception:
                        continue
                    if when == today and item.get("message"):
                        return item.get("message")
            except Exception:
                pass

        fallback = [
            "今天也要多和我互动哦～",
            "如果累了，可以先玩一局小游戏再继续。",
            "要不要试试抽一张灵感卡？",
            "我准备了一点小惊喜，随时可以触发~",
        ]
        try:
            return random.choice(fallback)
        except Exception:
            return "今天也要多和我互动哦～"

    def _get_daily_event_meta(self):
        """获取今日事件的简要元数据"""
        from datetime import datetime

        meta = {
            "title": "休闲小事件",
            "source": "",
            "timestamp": "",
        }

        if hasattr(self, "event_system") and self.event_system:
            try:
                today = datetime.now().date()
                for item in reversed(self.event_system.get_event_log() or []):
                    ts = item.get("timestamp")
                    if not ts:
                        continue
                    try:
                        when = datetime.fromisoformat(ts).date()
                    except Exception:
                        continue
                    if when == today:
                        meta["source"] = item.get("id", "") or "system"
                        meta["timestamp"] = ts
                        break
            except Exception:
                pass

        if not meta["timestamp"]:
            meta["timestamp"] = datetime.now().replace(microsecond=0).isoformat()
        return meta

    def _get_event_counts(self):
        """获取事件统计（今日/累计）"""
        from datetime import datetime

        total = 0
        today_count = 0
        if hasattr(self, "event_system") and self.event_system:
            try:
                today = datetime.now().date()
                for item in self.event_system.get_event_log() or []:
                    total += 1
                    ts = item.get("timestamp")
                    if not ts:
                        continue
                    try:
                        when = datetime.fromisoformat(ts).date()
                    except Exception:
                        continue
                    if when == today:
                        today_count += 1
            except Exception:
                pass
        return today_count, total

    def _get_event_reward_hint(self) -> str:
        """获取事件奖励提示"""
        return "可能奖励：相册 / 成就 / 好感"

    def _start_leisure_story(self):
        """启动一段休闲剧情链"""
        if not hasattr(self, "event_system") or not self.event_system:
            return
        try:
            event_data = self.event_system.narrative_manager.start_chain("leisure_daily")
            if event_data:
                self.event_system._enqueue_event(EventPriority.HIGH, "narrative", **event_data)
                self._show_toast("剧情已开启")
            else:
                self._show_toast("剧情稍后触发")
        except Exception:
            self._show_toast("剧情暂时不可用")

    def _show_toast(self, text: str, duration: int = 1800, accent: str = "#4CAF50"):
        """简洁奖励提示弹窗"""
        try:
            if hasattr(self, "_toast_window") and self._toast_window:
                if self._toast_window.winfo_exists():
                    self._toast_window.destroy()
        except Exception:
            pass

        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.0)

        bg = "#2D3138"
        frame = tk.Frame(toast, bg=bg, highlightthickness=1, highlightbackground="#3A404C")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame,
            text="✨",
            font=("Segoe UI Emoji", 12),
            bg=bg,
            fg=accent,
            padx=6,
            pady=6
        ).pack(side=tk.LEFT)
        tk.Label(
            frame,
            text=text,
            font=("Microsoft YaHei UI", 9),
            bg=bg,
            fg="#E6E6E6",
            padx=6,
            pady=6
        ).pack(side=tk.LEFT)

        toast.update_idletasks()
        width = toast.winfo_width()
        height = toast.winfo_height()
        x = self.winfo_x() + max(12, (self.winfo_width() - width) // 2)
        y = self.winfo_y() + 12
        toast.geometry(f"{width}x{height}+{x}+{y}")

        self._toast_window = toast

        def fade_in(alpha=0.0):
            if not toast.winfo_exists():
                return
            alpha = min(0.95, alpha + 0.1)
            toast.attributes("-alpha", alpha)
            if alpha < 0.95:
                toast.after(30, lambda: fade_in(alpha))

        def fade_out(alpha=0.95):
            if not toast.winfo_exists():
                return
            alpha = max(0.0, alpha - 0.08)
            toast.attributes("-alpha", alpha)
            if alpha > 0:
                toast.after(30, lambda: fade_out(alpha))
            else:
                try:
                    toast.destroy()
                except Exception:
                    pass

        fade_in()
        toast.after(duration, fade_out)

    def _show_reward_card(self, title: str, detail: str, duration: int = 2400,
                          accent: str = "#FFB300", icon: str = "🎁"):
        """奖励卡片弹窗"""
        try:
            if hasattr(self, "_reward_window") and self._reward_window:
                if self._reward_window.winfo_exists():
                    self._reward_window.destroy()
        except Exception:
            pass

        win = tk.Toplevel(self)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.0)

        bg = "#1F232B"
        border = "#3A404C"
        frame = tk.Frame(win, bg=bg, highlightthickness=1, highlightbackground=border)
        frame.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(frame, bg=bg)
        header.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(
            header,
            text=icon,
            font=("Segoe UI Emoji", 14),
            bg=bg,
            fg=accent
        ).pack(side=tk.LEFT)
        tk.Label(
            header,
            text=title,
            font=("Microsoft YaHei UI", 10, "bold"),
            bg=bg,
            fg="#E6E6E6"
        ).pack(side=tk.LEFT, padx=6)

        tk.Label(
            frame,
            text=detail,
            font=("Microsoft YaHei UI", 9),
            bg=bg,
            fg="#A8B0BD",
            padx=12,
            pady=10,
            justify=tk.LEFT
        ).pack(anchor=tk.W)

        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        x = self.winfo_x() + max(12, (self.winfo_width() - width) // 2)
        y = self.winfo_y() + 16
        win.geometry(f"{width}x{height}+{x}+{y}")

        self._reward_window = win

        def fade_in(alpha=0.0):
            if not win.winfo_exists():
                return
            alpha = min(0.95, alpha + 0.1)
            win.attributes("-alpha", alpha)
            if alpha < 0.95:
                win.after(30, lambda: fade_in(alpha))

        def fade_out(alpha=0.95):
            if not win.winfo_exists():
                return
            alpha = max(0.0, alpha - 0.08)
            win.attributes("-alpha", alpha)
            if alpha > 0:
                win.after(30, lambda: fade_out(alpha))
            else:
                try:
                    win.destroy()
                except Exception:
                    pass

        fade_in()
        win.after(duration, fade_out)

    def _maybe_show_mode_tip(self, item_key: str):
        """首次进入模式时提示"""
        if not self.config_manager:
            return
        shown = self.config_manager.get("assistant_mode_tips_shown", {}) or {}
        if shown.get(item_key):
            return

        tips = {
            "training": ("模式提示", "训练模式：3分钟小练习，快速进入写作状态。"),
            "reverse_engineering": ("模式提示", "推理模式：拆解文本结构，学习写作技巧。"),
        }
        tip = tips.get(item_key)
        if not tip:
            return

        title, detail = tip
        self._show_reward_card(title, detail, accent="#42A5F5", icon="🧭")
        shown[item_key] = True
        self.config_manager.set("assistant_mode_tips_shown", shown)
        self.config_manager.save()

    def _quick_greet(self):
        """快速打招呼（休闲入口）"""
        self._greet_assistant()

    def _quick_start_game(self):
        """快速开始一个小游戏"""
        self._start_game("guess_number")

    def _manual_daily_checkin(self):
        """手动触发每日签到"""
        result = self.pet_system.check_daily()
        if result.get("is_new_day"):
            streak = result.get("streak", 1)
            self._append_message("system", f"🎉 每日签到成功！(已连续 {streak} 天)")
            bonus_aff = result.get("bonus_affection", 0)
            bonus_coins = result.get("bonus_coins", 0)
            self._show_toast(f"签到奖励 +{bonus_aff}好感 +{bonus_coins}金币")
        else:
            self._append_message("system", "今日已签到~")
            self._show_toast("今日已签到")

        self.affection = self.pet_system.data.affection
        self._refresh_home_panel()

    def _claim_daily_task_reward(self):
        """领取每日任务奖励"""
        rewards = self.pet_system.claim_daily_task_reward()
        if rewards:
            reward_text = " / ".join(rewards)
            self._append_message("system", f"🎁 今日任务奖励已领取：{reward_text}")
            self._set_state(AssistantState.SUCCESS, duration=1500)
            self._show_toast(f"任务奖励 {reward_text}")
            self.affection = self.pet_system.data.affection
        else:
            self._append_message("system", "请先完成今日任务~")
            self._show_toast("任务未完成")
        self._refresh_home_panel()

    def _show_main_window(self):
        """显示主界面窗口"""
        if not self.parent or not self.parent.winfo_exists():
            return
        try:
            self.parent.deiconify()
            self.parent.lift()
            self.parent.focus_force()
        except Exception:
            pass

    def _hide_main_window(self):
        """隐藏主界面窗口"""
        if not self.parent or not self.parent.winfo_exists():
            return
        try:
            self.parent.withdraw()
        except Exception:
            pass

    def _toggle_main_window(self):
        """切换主界面窗口显示状态"""
        if not self.parent or not self.parent.winfo_exists():
            return
        try:
            if self.parent.state() == "withdrawn" or not self.parent.winfo_viewable():
                self._show_main_window()
            else:
                self._hide_main_window()
        except Exception:
            self._show_main_window()

    def _exit_application(self):
        """退出整个应用"""
        if self.parent and hasattr(self.parent, "writer_app"):
            app = getattr(self.parent, "writer_app", None)
            if app and hasattr(app, "_exit_app"):
                app._exit_app()
                return
        if self.parent and self.parent.winfo_exists():
            try:
                self.parent.destroy()
            except Exception:
                pass

    def _on_close(self):
        """关闭/隐藏窗口"""
        self.withdraw()

    def show(self):
        """显示窗口"""
        self.deiconify()
        self._refresh_activity()

    def set_ai_mode_enabled(self, enabled: bool):
        """设置AI模式"""
        self.ai_mode_enabled = enabled
        if hasattr(self, 'chat_view'):
            self.chat_view.update_mode_label()
        if hasattr(self, "reverse_engineering_view") and self.reverse_engineering_view:
            try:
                self.reverse_engineering_view.set_ai_mode_enabled(enabled)
            except Exception:
                pass
        self._update_quick_buttons()

    def apply_config_changes(self, settings: Dict, old_size: int):
        """应用配置更改"""
        # 透明度
        alpha = settings.get("alpha", 0.95)
        self.attributes("-alpha", alpha)

        # 尺寸变化
        new_size = settings.get("avatar_size", 120)
        if new_size != old_size:
            self._apply_avatar_size(new_size, save=False)

        # 反推导窗口尺寸更新
        if "reverse_width" in settings or "reverse_height" in settings:
            self._reverse_expanded_size = None
            if self._get_active_mode() == "reverse_engineering":
                self._apply_reverse_expanded_size()

    def destroy(self):
        """清理所有资源和定时器"""
        # 取消所有定时器
        timers_to_cancel = [
            getattr(self, 'timer_id', None),
            getattr(self, 'idle_timer_id', None),
            getattr(self, '_weather_timer_id', None),
            getattr(self, '_idle_chat_job', None),
            getattr(self, '_animation_job', None),
            getattr(self, '_typewriter_job', None),
        ]

        for timer_id in timers_to_cancel:
            if timer_id:
                try:
                    self.after_cancel(timer_id)
                except Exception:
                    pass

        # 保存养成系统数据
        if hasattr(self, 'pet_system') and self.pet_system:
            try:
                self.pet_system.save()
            except Exception:
                pass

        # 停止AI处理器
        if hasattr(self, 'ai_handler') and self.ai_handler:
            try:
                self.ai_handler.stop_generation()
            except Exception:
                pass

        # 停止集成管理器
        if hasattr(self, 'integration_manager') and self.integration_manager:
            try:
                self.integration_manager.stop()
            except Exception:
                pass

        # 调用父类的 destroy
        super().destroy()

    # ============================================================
    # 主题支持
    # ============================================================

    def apply_theme(self, theme_manager):
        """应用主题颜色"""
        if not theme_manager:
            return

        # 获取主题颜色
        bg_primary = theme_manager.get_color("bg_primary")
        bg_secondary = theme_manager.get_color("bg_secondary")
        fg_primary = theme_manager.get_color("fg_primary")
        fg_secondary = theme_manager.get_color("fg_secondary")
        accent = theme_manager.get_color("accent")
        editor_bg = theme_manager.get_color("editor_bg")
        editor_fg = theme_manager.get_color("editor_fg")
        border = theme_manager.get_color("border")

        # 主容器
        if hasattr(self, 'content_container'):
            self.content_container.configure(bg=bg_secondary)

        # 工具栏
        if hasattr(self, 'tool_bar'):
            self.tool_bar.configure(bg=accent)
            for child in self.tool_bar.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=accent, fg="white")

        # 聊天显示区
        if hasattr(self, 'chat_display'):
            self.chat_display.configure(bg=editor_bg, fg=editor_fg)

        # 快捷按钮区
        if hasattr(self, 'quick_frame'):
            self.quick_frame.configure(bg=bg_secondary)
            for child in self.quick_frame.winfo_children():
                if isinstance(child, tk.Button):
                    child.configure(bg=border, fg=fg_primary,
                                    activebackground=bg_primary,
                                    activeforeground=fg_primary)

        # 输入区
        if hasattr(self, 'input_frame'):
            self.input_frame.configure(bg=bg_secondary)

        if hasattr(self, 'input_text'):
            self.input_text.configure(bg=editor_bg, fg=editor_fg,
                                      insertbackground=fg_primary)

        # 工具按钮
        tool_buttons = ['more_btn', 'voice_btn', 'context_btn', 'send_btn']
        for btn_name in tool_buttons:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                if btn_name == 'send_btn':
                    btn.configure(bg=accent, fg="white",
                                  activebackground=accent,
                                  activeforeground="white")
                else:
                    btn.configure(bg=border, fg=fg_primary,
                                  activebackground=bg_primary,
                                  activeforeground=fg_primary)


class FloatingAssistantManager:
    """悬浮助手管理器（单例）"""
    _instance: Optional[FloatingAssistant] = None
    _hotkey_manager: Optional[HotkeyManager] = None
    _context_aware: Optional[ContextAwareAssistant] = None
    _pending_editor_widget = None
    _pending_script_controller = None

    @classmethod
    def toggle(cls, parent, project_manager, config_manager):
        """切换助手显示"""
        if cls._instance and cls._instance.winfo_exists():
            if cls._instance.winfo_viewable():
                cls._instance.withdraw()
            else:
                cls._instance.show()
        else:
            cls._instance = FloatingAssistant(parent, project_manager, config_manager)

            if cls._pending_editor_widget:
                cls._instance.set_editor_widget(cls._pending_editor_widget)
            if cls._pending_script_controller:
                cls._instance.set_script_controller(cls._pending_script_controller)

            # 初始化快捷键管理器
            if not cls._hotkey_manager:
                cls._hotkey_manager = HotkeyManager(parent, config_manager)
                cls._setup_hotkeys()

            # 初始化上下文感知
            if not cls._context_aware:
                cls._context_aware = ContextAwareAssistant(parent, project_manager, config_manager)
                cls._context_aware.set_assistant(cls._instance)

            if hasattr(project_manager, "get_project_type"):
                cls._instance.show_mode_guide(project_manager.get_project_type())

    @classmethod
    def _setup_hotkeys(cls):
        """设置快捷键"""
        if not cls._hotkey_manager or not cls._instance:
            return

        # 注册回调
        cls._hotkey_manager.register_callback("toggle_assistant", cls._toggle_from_hotkey)
        cls._hotkey_manager.register_callback("quick_prompt", lambda: cls._instance._draw_prompt_card() if cls._instance else None)
        cls._hotkey_manager.register_callback("roll_dice", lambda: cls._instance._roll_dice() if cls._instance else None)
        cls._hotkey_manager.register_callback("name_generator", lambda: cls._instance._open_name_generator() if cls._instance else None)
        cls._hotkey_manager.register_callback("word_count", lambda: cls._instance._show_word_count() if cls._instance else None)
        cls._hotkey_manager.register_callback("ai_expand", lambda: cls._instance.send_selected_for_expansion() if cls._instance else None)
        cls._hotkey_manager.register_callback("ai_polish", lambda: cls._instance.send_selected_for_polish() if cls._instance else None)
        cls._hotkey_manager.register_callback("send_to_assistant", lambda: cls._instance._insert_context() if cls._instance else None)
        cls._hotkey_manager.register_callback("timer_toggle", lambda: cls._instance._toggle_timer() if cls._instance else None)
        cls._hotkey_manager.register_callback("quick_note", lambda: cls._instance._open_quick_note() if cls._instance else None)

        # 绑定快捷键
        cls._hotkey_manager.bind_all()

    @classmethod
    def _toggle_from_hotkey(cls):
        """快捷键切换助手显示"""
        if cls._instance and cls._instance.winfo_exists():
            if cls._instance.winfo_viewable():
                cls._instance.withdraw()
            else:
                cls._instance.show()
                cls._instance.focus_force()

    @classmethod
    def apply_settings(cls, config_manager, settings: Dict, save: bool = False):
        """应用设置"""
        if not settings:
            return

        try:
            old_size = int(config_manager.get("assistant_avatar_size", 120))
        except Exception:
            old_size = 120

        config_manager.set("enable_idle_chat", settings.get("enable_idle_chat", False))
        config_manager.set("idle_interval", settings.get("idle_interval", 10))
        config_manager.set("assistant_alpha", settings.get("alpha", 0.95))
        config_manager.set("assistant_start_expanded", settings.get("start_expanded", False))
        config_manager.set("assistant_avatar_size", settings.get("avatar_size", 120))
        config_manager.set("assistant_reverse_width", settings.get("reverse_width", 0))
        config_manager.set("assistant_reverse_height", settings.get("reverse_height", 0))
        # 背景移除设置
        if "bg_remove_mode" in settings:
            config_manager.set("assistant_bg_remove_mode", settings.get("bg_remove_mode", "ai"))
        if "bg_remove_tolerance" in settings:
            config_manager.set("assistant_bg_remove_tolerance", settings.get("bg_remove_tolerance", 30))

        if save:
            config_manager.save()

        if cls._instance and cls._instance.winfo_exists():
            cls._instance.apply_config_changes(settings, old_size)

    @classmethod
    def apply_ai_mode(cls, enabled: bool):
        """设置AI模式"""
        if cls._instance and cls._instance.winfo_exists():
            cls._instance.set_ai_mode_enabled(enabled)

    @classmethod
    def show_mode_guide(cls, project_type: str, force: bool = False):
        if cls._instance and cls._instance.winfo_exists():
            cls._instance.show_mode_guide(project_type, force=force)

    @classmethod
    def get_instance(cls) -> Optional[FloatingAssistant]:
        """获取实例"""
        return cls._instance

    @classmethod
    def set_editor_widget(cls, widget):
        """设置编辑器控件引用"""
        cls._pending_editor_widget = widget
        if cls._instance:
            cls._instance.set_editor_widget(widget)
        if cls._context_aware:
            cls._context_aware.set_editor_widget(widget)

    @classmethod
    def set_script_controller(cls, controller):
        """设置脚本控制器引用"""
        cls._pending_script_controller = controller
        if cls._instance:
            cls._instance.set_script_controller(controller)
        if cls._context_aware:
            cls._context_aware.set_script_controller(controller)

    @classmethod
    def get_hotkey_list(cls) -> list:
        """获取快捷键列表"""
        if cls._hotkey_manager:
            return cls._hotkey_manager.get_hotkey_list()
        return []

    @classmethod
    def update_hotkey(cls, action: str, new_key: str):
        """更新快捷键绑定"""
        if cls._hotkey_manager:
            cls._hotkey_manager.update_binding(action, new_key)

    @classmethod
    def enable_hotkeys(cls, enabled: bool = True):
        """启用/禁用快捷键"""
        if cls._hotkey_manager:
            cls._hotkey_manager.set_enabled(enabled)

    @classmethod
    def set_gamification_manager(cls, manager):
        """设置游戏化管理器"""
        if cls._instance:
            cls._instance.set_gamification_manager(manager)

    @classmethod
    def set_command_executor(cls, executor):
        """设置命令执行器"""
        if cls._instance:
            cls._instance.set_command_executor(executor)

    @classmethod
    def set_ai_controller(cls, controller):
        """设置AI控制器"""
        if cls._instance:
            cls._instance.set_ai_controller(controller)

    @classmethod
    def set_stats_manager(cls, manager):
        """设置统计管理器"""
        if cls._instance:
            cls._instance.set_stats_manager(manager)

    @classmethod
    def setup_integrations(cls, gamification_manager=None, command_executor=None,
                           ai_controller=None, stats_manager=None,
                           ambiance_player=None, typewriter_player=None):
        """一次性设置所有集成管理器"""
        if cls._instance:
            if gamification_manager:
                cls._instance.set_gamification_manager(gamification_manager)
            if command_executor:
                cls._instance.set_command_executor(command_executor)
            if ai_controller:
                cls._instance.set_ai_controller(ai_controller)
            if stats_manager:
                cls._instance.set_stats_manager(stats_manager)
            if ambiance_player:
                cls._instance.set_ambiance_player(ambiance_player)
            if typewriter_player:
                cls._instance.set_typewriter_player(typewriter_player)

    @classmethod
    def set_ambiance_player(cls, player):
        """设置环境音播放器"""
        if cls._instance:
            cls._instance.set_ambiance_player(player)

    @classmethod
    def set_typewriter_player(cls, player):
        """设置打字机音效播放器"""
        if cls._instance:
            cls._instance.set_typewriter_player(player)

    @classmethod
    def on_project_event(cls, event_type: str, **kwargs):
        """传递项目事件到助手"""
        if cls._instance:
            cls._instance.on_project_event(event_type, **kwargs)

    @classmethod
    def cleanup(cls):
        """清理资源"""
        if cls._hotkey_manager:
            cls._hotkey_manager.unbind_all()
            cls._hotkey_manager = None

        if cls._context_aware:
            cls._context_aware.stop_clipboard_monitor()
            cls._context_aware = None

        if cls._instance:
            # 停止集成监听
            if hasattr(cls._instance, 'integration_manager'):
                cls._instance.integration_manager.stop()

            try:
                cls._instance.destroy()
            except Exception:
                pass
            cls._instance = None
