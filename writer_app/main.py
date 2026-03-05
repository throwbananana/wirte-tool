import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
import logging

from writer_app.core.models import ProjectManager
from writer_app.core.config import ConfigManager
from writer_app.core.theme import ThemeManager
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.core.commands import (
    AddNodeCommand, DeleteNodesCommand, EditNodeCommand,
    AddCharacterCommand, DeleteCharacterCommand, EditCharacterCommand,
    AddSceneCommand, DeleteSceneCommand, EditSceneContentCommand,
    AddWikiEntryCommand, DeleteWikiEntryCommand, EditWikiEntryCommand,
    GlobalRenameCommand
)
from writer_app.core.history_manager import CommandHistory
from writer_app.core.backup import BackupManager
from writer_app.core.outline_templates import (
    get_outline_template_meta,
    get_outline_template_nodes,
    list_outline_templates,
)
from writer_app.core.gamification import GamificationManager
from writer_app.ui.outline_views import VIEW_TYPE_NAMES
from writer_app.ui.floating_assistant import FloatingAssistantManager
from writer_app.ui.relationship_map import RelationshipMapCanvas
from writer_app.ui.dialogs import CharacterDialog, DiagnosisResultDialog, ValidationResultDialog
from writer_app.ui.tags import TagManagerDialog, TagSelectorDialog, SetNodeTagsCommand
from writer_app.ui.search_dialog import SearchDialog
from writer_app.ui.analytics import AnalyticsPanel
from writer_app.ui.timeline import TimelinePanel
from writer_app.ui.editor import ScriptEditor
from writer_app.ui.kanban import KanbanBoard
from writer_app.ui.calendar_view import CalendarView
from writer_app.ui.evidence_board import EvidenceBoardContainer
from writer_app.ui.swimlanes import SwimlaneView
from writer_app.ui.dual_timeline import DualTimelineView
from writer_app.ui.submission import SubmissionDialog
from writer_app.ui.achievements_dialog import AchievementsDialog
from writer_app.ui.training_panel import TrainingPanel
from writer_app.core.project_types import ProjectTypeManager
from writer_app.utils.ai_client import AIClient
from writer_app.core.exporter import Exporter, ExporterRegistry
from writer_app.core.analysis import AnalysisUtils
from writer_app.ui.story_curve import StoryCurveController
from writer_app.core.logic_validator import get_logic_validator
from writer_app.core.module_sync import init_module_sync, get_module_sync_service
from writer_app.core.controller_registry import ControllerRegistry, RefreshGroups, CONTROLLER_GROUP_MAPPING, Capabilities
from writer_app.core.thread_pool import get_ai_thread_pool, shutdown_thread_pool
from writer_app.core.font_manager import get_font_manager
from writer_app.core.guide_progress import GuideProgress
from writer_app.controllers.script_controller import ScriptController
from writer_app.controllers.mindmap_controller import MindMapController
from writer_app.controllers.chat_controller import ChatController
from writer_app.controllers.training_controller import TrainingController
from writer_app.controllers.flowchart_controller import FlowchartController
from writer_app.controllers.wiki_controller import WikiController
from writer_app.controllers.analytics_controller import AnalyticsController
from writer_app.controllers.relationship_controller import RelationshipController
from writer_app.controllers.dual_timeline_controller import DualTimelineController
from writer_app.controllers.timeline_controller import TimelineController
from writer_app.controllers.kanban_controller import KanbanController
from writer_app.controllers.calendar_controller import CalendarController
from writer_app.controllers.ai_controller import AIController
from writer_app.controllers.pomodoro_controller import PomodoroController
from writer_app.controllers.idea_controller import IdeaController
from writer_app.controllers.research_controller import ResearchController
from writer_app.controllers.guide_controller import GuideController
from writer_app.controllers.sidebar_controller import SidebarController
from writer_app.ui.idea_panel import IdeaPanel
from writer_app.ui.research import ResearchPanel
from writer_app.ui.sidebar import SidebarPanel
from writer_app.ui.name_generator import NameGeneratorDialog
from writer_app.ui.settings_dialog import SettingsDialog
from writer_app.ui.project_settings_dialog import ProjectSettingsDialog
from writer_app.ui.module_catalog_dialog import ModuleCatalogDialog
from writer_app.ui.app_mode_manager import AppModeManager
from writer_app.ui.app_theme import AppThemeController
from writer_app.core.audio import AmbiancePlayer, TypewriterSoundPlayer
from writer_app.ui.heartbeat_tracker import HeartbeatTrackerController
from writer_app.ui.alibi_timeline import AlibiTimelineController
from writer_app.ui.galgame_assets import GalgameAssetsController
from writer_app.ui.world_iceberg import WorldIcebergController
from writer_app.ui.faction_matrix import FactionMatrixController
from writer_app.ui.reverse_engineering import ReverseEngineeringView
from writer_app.ui.character_event_table import CharacterEventTable
from writer_app.controllers.variable_controller import VariableController
from writer_app.utils.logging_utils import setup_logging
from writer_app.utils.tray_manager import TrayManager
from writer_app.core.icon_manager import IconManager
from writer_app.ui.help_dialog import show_help_dialog, show_shortcuts_dialog, show_about_dialog
from writer_app.core.help_manager import get_help_manager

logger = logging.getLogger(__name__)

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

class WriterTool:
    """写作助手主程序"""

    def __init__(self, root):
        self.root = root
        self.root.title("写作助手 - Writer Tool")
        self.root.writer_app = self
        
        self.data_dir = Path(__file__).parent.parent / "writer_data"
        self.data_dir.mkdir(exist_ok=True)
        self.log_file_path = setup_logging(self.data_dir)
        
        # Load local fonts
        try:
            get_font_manager().load_local_fonts()
        except Exception as e:
            logger.error(f"Failed to load fonts: {e}")
        
        # Initialize IconManager to load fonts
        self.icon_mgr = IconManager()
        
        self.ambiance_player = AmbiancePlayer(str(self.data_dir))
        self.typewriter_player = TypewriterSoundPlayer(str(self.data_dir))

        self.config_manager = ConfigManager()
        self.ai_mode_var = tk.BooleanVar(value=self.config_manager.get("ai_mode_enabled", True))
        self.theme_manager = ThemeManager(self.config_manager.get("theme", "Light"))
        self.theme_manager.set_custom_colors(self.config_manager.get("custom_theme_colors", {}))
        self.theme_manager.set_background_image(self.config_manager.get("background_image", ""))
        self.theme_manager.set_background_opacity(self.config_manager.get("background_opacity", 1.0))
        self.theme_controller = AppThemeController(self)
        self.theme_manager.add_listener(self._on_theme_changed)
        geometry = self.config_manager.get("window_geometry", "1400x900")
        self.root.geometry(geometry)

        self.project_manager = ProjectManager()
        self.ai_client = AIClient()
        self.history_manager = CommandHistory()
        self.search_dialog = None
        self.messagebox = messagebox
        self.guide_progress = GuideProgress(self.data_dir)
        self.guide_controller = GuideController(self)

        # 初始化事件总线
        self.event_bus = get_event_bus()
        self._setup_event_subscriptions()

        # 初始化模块同步服务
        self.module_sync = init_module_sync(self.project_manager)
        self._last_validation_report = None
        self._last_validation_issue_count = None
        self.module_sync.set_validation_callback(self._run_logic_validation_silent)

        self.data_dir = Path(__file__).parent.parent / "writer_data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.gamification_manager = GamificationManager(self.data_dir)
        self.gamification_manager.add_listener(self.on_gamification_update)
        
        self.backup_manager = BackupManager(self.project_manager)
        self.backup_manager.start()

        self.lm_api_url = tk.StringVar(value=self.config_manager.get("lm_api_url", "http://localhost:1234/v1/chat/completions"))
        self.lm_api_model = tk.StringVar(value=self.config_manager.get("lm_api_model", "local-model"))
        self.lm_api_key = tk.StringVar(value=self.config_manager.get("lm_api_key", ""))
        
        self.ai_controller = AIController(self)
        
        self.ai_status_var = tk.StringVar(value="使用本地 LM Studio 分析剧本并生成思维导图")
        self.ai_generating = False
        self.script_ai_status_var = tk.StringVar(value="使用大纲生成剧本结构与场景")
        self.script_ai_generating = False
        self.outline_helper_status_var = tk.StringVar(value="选择节点后可用AI补全内容或生成子节点（右键生成建议分支）")
        self.outline_helper_hint_var = tk.StringVar(value="")
        self.outline_helper_running = False
        self.status_var = tk.StringVar(value="就绪 | 双击节点编辑 | Tab添加子节点 | Enter添加同级 | Delete删除 | 框选多选 | F1帮助")
        
        self.word_count_var = tk.StringVar(value="Words: 0")
        self.last_word_count = 0
        self.timer_var = tk.StringVar(value="Work 25:00")
        
        self.pomodoro_controller = PomodoroController(
            self.root, 
            self.config_manager, 
            self._update_timer_ui,
            self.gamification_manager
        )
        self.mode_manager = AppModeManager(self)

        self.close_behavior = self.config_manager.get("close_behavior", "ask")
        self.taskbar_date_events = list(self.config_manager.get("taskbar_date_events", []))
        self.tray_manager = TrayManager(
            self.root,
            on_show=self._show_main_window,
            on_hide=self._hide_main_window,
            on_exit=self.exit_app
        )
        self.tray_manager.set_events(self.taskbar_date_events)
        
        self.daily_goal = 2000
        self.daily_count = 0
        self.wiki_categories = ["人物", "地点", "物品", "势力", "设定", "其他"]
        
        stats = self.gamification_manager.get_stats()
        self.level_var = tk.StringVar(value=f"Lv.{stats['level']}")
        self.points_var = tk.StringVar(value=f"💎 {stats['points']}")

        # Notebook tab registry; maps tool keys to their frames
        self.tabs = {}

        # 控制器注册表
        self.registry = ControllerRegistry()

        self.setup_ui()
        self.setup_menu()
        self.bind_shortcuts()
        
        self.is_zen_mode = False
        self.pre_zen_geometry = None
        self.zen_exit_btn = None
        self.zen_info_frame = None
        self._orig_notebook_style = ""
        self._zen_style_created = False
        self.mindmap_tag_filters = set()
        self.current_selected_node = None

        self.project_manager.add_listener(self.on_project_data_changed)

        self.refresh_all()
        
        last_file = self.config_manager.get("last_opened_file")
        if last_file and Path(last_file).exists():
            try:
                self.project_manager.load_project(last_file)
                self.refresh_all()
                self.update_title()
                self.status_var.set(f"已恢复: {last_file}")
            except Exception as e:
                print(f"Failed to autoload: {e}")
        
        self.apply_theme()
        self.apply_ai_mode(self.ai_mode_var.get())
        self.root.after(200, self._apply_assistant_primary_mode_startup)
        # self.root.after(200, self.guide_controller.show_dev_notice_if_needed)

    def setup_ui(self):
        # Create main paned window with sidebar + content area
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create sidebar panel (left)
        self.sidebar = SidebarPanel(
            self.main_paned,
            self.theme_manager,
            self._on_sidebar_select,
            self.config_manager
        )
        self.main_paned.add(self.sidebar, weight=0)

        # Content area (right) with notebook (tabs hidden)
        self.content_area = ttk.Frame(self.main_paned)
        self.main_paned.add(self.content_area, weight=1)

        self.notebook = ttk.Notebook(self.content_area)
        self._orig_notebook_style = self.notebook.cget("style") or ""
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Hide notebook tabs using style
        style = ttk.Style()
        style.layout("Hidden.TNotebook.Tab", [])  # Empty layout = hidden tabs
        self.notebook.configure(style="Hidden.TNotebook")

        self._toolbox_tab = None
        self._last_real_tab = None

        current_type = self.project_manager.get_project_type()
        current_length = self.project_manager.get_project_length()
        enabled_tools = self.project_manager.get_enabled_tools()
        
        if "outline" in enabled_tools:
            self.outline_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.outline_frame, text="  思维导图/大纲  ")
            self.mindmap_controller = MindMapController(
                self.outline_frame,
                self.project_manager,
                self._execute_command,
                self.theme_manager,
                self.ai_client,
                self.config_manager,
                self.ai_controller
            )
            self.registry.register("mindmap", self.mindmap_controller,
                refresh_groups=[RefreshGroups.OUTLINE],
                capabilities=[Capabilities.AI_MODE])
            self.tabs["outline"] = self.outline_frame

        if "script" in enabled_tools:
            self.script_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.script_frame, text="  剧本写作  ")
            self.script_controller = ScriptController(
                self.script_frame,
                self.project_manager,
                self._execute_command,
                self.theme_manager,
                self.ai_client,
                self.config_manager,
                on_wiki_click=self.jump_to_wiki_entry,
                ai_controller=self.ai_controller,
                ambiance_player=self.ambiance_player
            )
            FloatingAssistantManager.set_script_controller(self.script_controller)
            if hasattr(self.script_controller, "script_editor"):
                FloatingAssistantManager.set_editor_widget(self.script_controller.script_editor)
            self.registry.register("script", self.script_controller,
                refresh_groups=[RefreshGroups.SCENE, RefreshGroups.CHARACTER],
                capabilities=[Capabilities.AI_MODE])
            self.tabs["script"] = self.script_frame

        if "char_events" in enabled_tools:
            self.char_event_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.char_event_frame, text="  人物事件  ")
            self.char_event_table = CharacterEventTable(
                self.char_event_frame,
                self.project_manager,
                self.theme_manager,
                self._execute_command
            )
            self.char_event_table.pack(fill=tk.BOTH, expand=True)
            self.tabs["char_events"] = self.char_event_frame

        if "relationship" in enabled_tools:
            self.relationship_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.relationship_frame, text="  人物关系图  ")
            self.relationship_controller = RelationshipController(
                self.relationship_frame,
                self.project_manager,
                self._execute_command,
                self.theme_manager,
                self.config_manager,
                on_jump_to_scene=self.jump_to_scene_by_index,
                on_jump_to_outline=self.jump_to_outline_node
            )
            self.registry.register("relationship", self.relationship_controller,
                refresh_groups=[RefreshGroups.CHARACTER, RefreshGroups.RELATIONSHIP])
            self.tabs["relationship"] = self.relationship_frame

        if "evidence_board" in enabled_tools:
            self.evidence_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.evidence_frame, text="  线索墙 (悬疑)  ")
            self.evidence_board = EvidenceBoardContainer(
                self.evidence_frame,
                self.project_manager,
                self._execute_command,
                self.theme_manager,
                on_navigate_to_scene=self.jump_to_scene_by_index
            )
            self.evidence_board.pack(fill=tk.BOTH, expand=True)
            self.registry.register("evidence_board", self.evidence_board,
                refresh_groups=[RefreshGroups.EVIDENCE, RefreshGroups.SCENE, RefreshGroups.CHARACTER])
            self.tabs["evidence_board"] = self.evidence_frame

        if "timeline" in enabled_tools:
            self.timeline_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.timeline_frame, text="  时间轴  ")
            self.setup_timeline_ui()
            self.tabs["timeline"] = self.timeline_frame

        if "story_curve" in enabled_tools:
            self.story_curve_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.story_curve_frame, text="  故事曲线  ")
            self.story_curve_controller = StoryCurveController(
                self.story_curve_frame,
                self.project_manager,
                self._execute_command,
                self.theme_manager,
                self.jump_to_scene_by_index,
                self.ai_controller
            )
            self.registry.register("story_curve", self.story_curve_controller,
                refresh_groups=[RefreshGroups.SCENE],
                capabilities=[Capabilities.AI_MODE])
            self.tabs["story_curve"] = self.story_curve_frame

        if "swimlanes" in enabled_tools:
            self.swimlane_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.swimlane_frame, text="  故事泳道  ")
            self.swimlane_view = SwimlaneView(self.swimlane_frame, self.project_manager, self.theme_manager)
            self.swimlane_view.pack_controls()
            self.tabs["swimlanes"] = self.swimlane_frame

        if "dual_timeline" in enabled_tools:
            self.dual_timeline_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.dual_timeline_frame, text="  表里双轨图  ")
            self.dual_timeline_controller = DualTimelineController(self.dual_timeline_frame, self.project_manager, self._execute_command, self.theme_manager)
            self.dual_timeline_controller.pack(fill=tk.BOTH, expand=True)
            self.registry.register("dual_timeline", self.dual_timeline_controller,
                refresh_groups=[RefreshGroups.TIMELINE])
            self.tabs["dual_timeline"] = self.dual_timeline_frame

        if "kanban" in enabled_tools:
            self.kanban_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.kanban_frame, text="  场次看板  ")
            self.setup_kanban_ui()
            self.tabs["kanban"] = self.kanban_frame

        if "calendar" in enabled_tools:
            self.calendar_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.calendar_frame, text="  故事日历  ")
            self.setup_calendar_ui()
            self.tabs["calendar"] = self.calendar_frame

        if "wiki" in enabled_tools:
            self.wiki_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.wiki_frame, text="  世界观百科  ")
            self.setup_wiki_ui()
            self.tabs["wiki"] = self.wiki_frame
        
        if "research" in enabled_tools:
            self.research_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.research_frame, text="  资料搜集  ")
            self.research_panel = ResearchPanel(self.research_frame, self.project_manager, self.theme_manager)
            self.research_panel.pack(fill=tk.BOTH, expand=True)
            self.research_controller = ResearchController(self.research_panel, self.project_manager, self._execute_command)
            self.registry.register("research", self.research_controller,
                refresh_groups=[RefreshGroups.ALL])
            self.tabs["research"] = self.research_frame

        # Reverse Engineering Tab
        if "reverse_engineering" in enabled_tools:
            self.reverse_engineering_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.reverse_engineering_frame, text="  反推导学习  ")
            self.reverse_engineering_view = ReverseEngineeringView(
                self.reverse_engineering_frame,
                self.project_manager,
                self.ai_client,
                self.theme_manager,
                self.config_manager,
                self._execute_command,
                on_navigate=self.navigate_to_module
            )
            self.reverse_engineering_view.pack(fill=tk.BOTH, expand=True)
            self.tabs["reverse_engineering"] = self.reverse_engineering_frame

        if "analytics" in enabled_tools:
            self.analytics_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.analytics_frame, text="  数据统计  ")
            self.analytics_controller = AnalyticsController(self.analytics_frame, self.project_manager, self._execute_command, self.theme_manager)
            self.registry.register("analytics", self.analytics_controller,
                refresh_groups=[RefreshGroups.ANALYTICS, RefreshGroups.OUTLINE])
            self.tabs["analytics"] = self.analytics_frame
        
        # --- Specialized Modules ---
        if "heartbeat" in enabled_tools:
            self.heartbeat_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.heartbeat_frame, text="  💗 心动追踪  ")
            self.heartbeat_controller = HeartbeatTrackerController(
                self.heartbeat_frame,
                self.project_manager,
                self._execute_command,
                self.jump_to_scene_by_index
            )
            self.registry.register("heartbeat", self.heartbeat_controller,
                refresh_groups=[RefreshGroups.CHARACTER])
            self.tabs["heartbeat"] = self.heartbeat_frame

        if "alibi" in enabled_tools:
            self.alibi_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.alibi_frame, text="  🕵️ 不在场证明  ")
            self.alibi_controller = AlibiTimelineController(self.alibi_frame, self.project_manager)
            self.registry.register("alibi", self.alibi_controller,
                refresh_groups=[RefreshGroups.TIMELINE])
            self.tabs["alibi"] = self.alibi_frame

        if "iceberg" in enabled_tools:
            self.iceberg_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.iceberg_frame, text="  🏔️ 世界冰山  ")
            self.iceberg_controller = WorldIcebergController(self.iceberg_frame, self.project_manager, self._execute_command)
            self.registry.register("iceberg", self.iceberg_controller,
                refresh_groups=[RefreshGroups.WIKI])
            self.tabs["iceberg"] = self.iceberg_frame

        if "faction" in enabled_tools:
            self.faction_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.faction_frame, text="  ⚔️ 势力矩阵  ")
            self.faction_controller = FactionMatrixController(self.faction_frame, self.project_manager, self._execute_command)
            self.registry.register("faction", self.faction_controller,
                refresh_groups=[RefreshGroups.RELATIONSHIP])
            self.tabs["faction"] = self.faction_frame

        # Galgame Assets moved to separate tool (start_asset_editor.py)
        # if "galgame_assets" in enabled_tools:
        #     self.galgame_assets_frame = ttk.Frame(self.notebook)
        #     self.notebook.add(self.galgame_assets_frame, text="  🎨 资源管理  ")
        #     self.galgame_assets_controller = GalgameAssetsController(
        #         self.galgame_assets_frame,
        #         self.project_manager,
        #         self._execute_command
        #     )
        #     self.registry.register("galgame_assets", self.galgame_assets_controller,
        #         refresh_groups=[RefreshGroups.ASSET])
        #     self.tabs["galgame_assets"] = self.galgame_assets_frame

        if "variable" in enabled_tools:
            self.variable_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.variable_frame, text="  🔢 变量管理  ")
            self.variable_controller = VariableController(
                self.variable_frame,
                self.project_manager,
                self._execute_command
            )
            self.registry.register("variable", self.variable_controller,
                refresh_groups=[RefreshGroups.ALL])
            self.tabs["variable"] = self.variable_frame

        if "flowchart" in enabled_tools:
            self.flowchart_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.flowchart_frame, text="  🕸️ 剧情流向  ")
            self.flowchart_controller = FlowchartController(
                self.flowchart_frame,
                self.project_manager,
                self._execute_command,
                self.theme_manager,
                on_jump_to_scene=self.jump_to_scene_by_index
            )
            self.registry.register("flowchart", self.flowchart_controller,
                refresh_groups=[RefreshGroups.OUTLINE, RefreshGroups.SCENE])
            self.tabs["flowchart"] = self.flowchart_frame

        # Always enable Idea Box
        if "ideas" in enabled_tools:
            self.idea_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.idea_frame, text="  灵感箱  ")
            self.idea_panel = IdeaPanel(self.idea_frame, self.project_manager, self.theme_manager)
            self.idea_panel.pack(fill=tk.BOTH, expand=True)
            self.idea_controller = IdeaController(self.idea_panel, self.project_manager, self.theme_manager)
            self.registry.register("idea", self.idea_controller,
                refresh_groups=[RefreshGroups.ALL])
            self.tabs["ideas"] = self.idea_frame

        # Training Module
        if "training" in enabled_tools:
            self.training_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.training_frame, text="  创意训练  ")
            self.training_panel = TrainingPanel(self.training_frame, theme_manager=self.theme_manager)
            self.training_panel.pack(fill=tk.BOTH, expand=True)
            self.training_controller = TrainingController(
                self.training_panel,
                self.project_manager,
                self.theme_manager,
                self.ai_client,
                self.config_manager,
                self.gamification_manager
            )
            self.registry.register("training", self.training_controller,
                refresh_groups=[RefreshGroups.ALL],
                capabilities=[Capabilities.AI_MODE])
            self.tabs["training"] = self.training_frame

        if "chat" in enabled_tools:
            self.chat_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.chat_frame, text="  项目对话  ")
            self.chat_controller = ChatController(
                self.chat_frame,
                self.project_manager,
                self._execute_command,
                self.theme_manager,
                self.ai_client,
                self.config_manager,
                self.ai_controller
            )
            self.registry.register("chat", self.chat_controller,
                refresh_groups=[RefreshGroups.ALL],
                capabilities=[Capabilities.AI_MODE])

        # Toolbox is now in sidebar, no need for notebook tab
        self._toolbox_tab = None

        # Create sidebar controller
        self.sidebar_controller = SidebarController(
            self.sidebar,
            self.notebook,
            self.config_manager,
            on_item_changed=self._on_sidebar_item_changed
        )

        # Register all tabs with sidebar controller
        for key, frame in self.tabs.items():
            self.sidebar_controller.register_tab(key, frame)

        # Update sidebar visibility based on enabled tools
        self.sidebar.update_visibility(enabled_tools)

        # Set initial selection
        default_key = ProjectTypeManager.get_default_tab_key(current_type)
        if default_key in self.tabs:
            self.sidebar.select_item_by_key(default_key)
            self.notebook.select(self.tabs[default_key])
        elif self.tabs:
            first_key = next(iter(self.tabs.keys()))
            self.sidebar.select_item_by_key(first_key)
            self.notebook.select(self.tabs[first_key])
        self._last_real_tab = self.notebook.select() if self.tabs else None

        # 4. Update Status Bar project type/length label
        t_name = self.project_manager.get_project_type_display_name()
        l_name = ProjectTypeManager.get_length_info(current_length)['name']
        if hasattr(self, "type_lbl") and self.type_lbl:
            self.type_lbl.config(text=f"[{t_name} | {l_name}]")

        # 5. Apply theme and refresh
        self.apply_theme()
        self.refresh_all()

    def _on_sidebar_select(self, workspace: str, item_key: str):
        """Handle sidebar item selection."""
        if item_key == "toolbox":
            self.open_module_catalog()
            return

        # Switch to the content frame via sidebar controller
        self.sidebar_controller.on_item_selected(workspace, item_key)

    def _on_sidebar_item_changed(self, workspace: str, item_key: str):
        """Callback when sidebar item changes (for analytics, etc.)."""
        # Update _last_real_tab for compatibility
        if item_key in self.tabs:
            self._last_real_tab = str(self.tabs[item_key])

    def _on_tab_changed(self, event=None):
        """Legacy tab change handler - kept for backward compatibility."""
        selected = self.notebook.select()
        if selected:
            self._last_real_tab = selected

    def open_module_catalog(self):
        if hasattr(self, "_module_catalog_dialog") and self._module_catalog_dialog:
            dialog = self._module_catalog_dialog.dialog
            if dialog.winfo_exists():
                dialog.lift()
                return
        self._module_catalog_dialog = ModuleCatalogDialog(self.root, self.project_manager)

    def rebuild_tabs(self):
        if hasattr(self, "registry"):
            self.registry.cleanup_all()

        # Clear controller references before destroying widgets
        # This prevents old references from being used in refresh_all/apply_theme
        controller_attrs = [
            "mindmap_controller", "script_controller", "wiki_controller",
            "relationship_controller", "timeline_controller", "kanban_controller",
            "calendar_controller", "dual_timeline_controller", "flowchart_controller",
            "analytics_controller", "idea_controller", "training_controller",
            "chat_controller", "research_controller", "sidebar_controller",
            "story_curve_controller", "heartbeat_controller", "alibi_controller",
            "iceberg_controller", "faction_controller", "variable_controller"
        ]
        for attr in controller_attrs:
            if hasattr(self, attr):
                setattr(self, attr, None)

        # Clear panel/view references
        panel_attrs = [
            "evidence_board", "research_panel", "training_panel", "idea_panel",
            "swimlane_view", "char_event_table", "reverse_engineering_view",
            "sidebar"
        ]
        for attr in panel_attrs:
            if hasattr(self, attr):
                setattr(self, attr, None)

        if hasattr(self, "main_paned"):
            self.main_paned.destroy()
        self.tabs = {}
        self.registry = ControllerRegistry()
        self.setup_ui()
        self.apply_ai_mode(self.ai_mode_var.get())

    def setup_wiki_ui(self):
        self.wiki_controller = WikiController(
            self.wiki_frame,
            self.project_manager,
            self._execute_command,
            self.theme_manager,
            self.ai_client,
            self.config_manager,
            on_jump_to_scene=self.jump_to_scene_by_index
        )
        self.registry.register("wiki", self.wiki_controller,
            refresh_groups=[RefreshGroups.WIKI],
            capabilities=[Capabilities.AI_MODE])

    def on_gamification_update(self, event_type, data):
        title = self.gamification_manager.get_current_title()
        self.level_var.set(f"Lv.{data['level']} {title}")
        self.points_var.set(f"{get_icon('star', '💎')} {data['points']}")
        
        if event_type == "levelup" or (event_type == "gain" and data.get("msg")):
            msg = data.get("msg", "")
            if msg: self.status_var.set(msg)
    
    def open_submission_dialog(self):
        SubmissionDialog(self.root, self.project_manager, self.ai_client, self.config_manager, self.gamification_manager)

    def open_achievements_dialog(self):
        AchievementsDialog(self.root, self.gamification_manager)

    def run_logic_check(self):
        """运行全局逻辑校验并显示报告。"""
        validator = get_logic_validator(self.project_manager)
        report = validator.run_full_validation()
        ValidationResultDialog(self.root, report, on_navigate_to_scene=self.jump_to_scene_by_index)

    def update_word_count(self):
        sc = getattr(self, 'script_controller', None)
        if not sc or not hasattr(sc, 'script_editor'):
            return
        count = sc.script_editor.get_word_count()
        self.word_count_var.set(f"字数: {count} / {self.daily_goal}")

        delta = count - self.last_word_count
        if delta >= 100:
            self.gamification_manager.record_words(delta)
            self.last_word_count = count
        elif delta < 0:
            self.last_word_count = count

    def setup_menu(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建项目", command=self.new_project, accelerator="Ctrl+N")
        file_menu.add_command(label="打开项目...", command=self.open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="保存项目", command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为...", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="项目设置 / 更改类型...", command=self.change_project_type)
        file_menu.add_separator()
        
        # Dynamic Export Menu
        export_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="导出...", menu=export_menu)
        
        for fmt in ExporterRegistry.list_formats():
            export_menu.add_command(
                label=f"导出为 {fmt.name} ({fmt.extension})",
                command=lambda f=fmt: self.perform_export(f)
            )
            
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="撤销", command=self.undo, accelerator="Ctrl+Z", state=tk.DISABLED)
        edit_menu.add_command(label="重做", command=self.redo, accelerator="Ctrl+Y", state=tk.DISABLED)
        self.edit_menu = edit_menu
        edit_menu.add_separator()
        edit_menu.add_command(label="查找与替换...", command=self.open_search_dialog, accelerator="Ctrl+F")
        edit_menu.add_command(label="全局替换 (Global Rename)...", command=self.open_global_rename_dialog)
        edit_menu.add_separator()
        edit_menu.add_command(label="运行逻辑校验 (Logic Check)", command=self.run_logic_check)
        edit_menu.add_separator()
        edit_menu.add_command(label="添加子节点", command=self.add_child_node, accelerator="Tab")
        edit_menu.add_command(label="添加同级节点", command=self.add_sibling_node, accelerator="Enter")
        edit_menu.add_command(label="删除节点", command=self.delete_node, accelerator="Delete")
        edit_menu.add_separator()
        edit_menu.add_command(label="展开所有", command=self.expand_all)
        edit_menu.add_command(label="折叠所有", command=self.collapse_all)
        edit_menu.add_separator()
        edit_menu.add_command(label="标签管理...", command=self.open_tag_manager)

        tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="写作冲刺 (Word Sprint)", command=self.open_word_sprint)
        tools_menu.add_command(label="起名助手", command=self.open_name_generator)

        career_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="生涯", menu=career_menu)
        career_menu.add_command(label="模拟投稿 (Submission)", command=self.open_submission_dialog)
        career_menu.add_separator()
        career_menu.add_command(label="我的成就 (Achievements)", command=self.open_achievements_dialog)

        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="刷新", command=self.refresh_all, accelerator="F5")
        view_menu.add_separator()
        from writer_app.ui.floating_assistant.constants import ASSISTANT_NAME
        view_menu.add_command(label=f"{ASSISTANT_NAME} (悬浮窗)", command=self.toggle_floating_assistant, accelerator="F2")
        view_menu.add_separator()
        view_menu.add_command(label="切换主题 (Dark/Light)", command=self.toggle_theme)

        # Focus Mode Submenu
        focus_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="专注模式 (Focus Mode)", menu=focus_menu)
        focus_menu.add_command(label="开启/关闭专注模式", command=self.toggle_focus_mode, accelerator="F10")
        focus_menu.add_command(label="打字机模式", command=self.toggle_typewriter_mode, accelerator="F9")
        focus_menu.add_separator()
        focus_menu.add_command(label="行聚焦", command=lambda: self.set_focus_level("line"), accelerator="Ctrl+Shift+1")
        focus_menu.add_command(label="句子聚焦", command=lambda: self.set_focus_level("sentence"), accelerator="Ctrl+Shift+2")
        focus_menu.add_command(label="段落聚焦", command=lambda: self.set_focus_level("paragraph"), accelerator="Ctrl+Shift+3")
        focus_menu.add_command(label="对话聚焦", command=lambda: self.set_focus_level("dialogue"), accelerator="Ctrl+Shift+4")
        focus_menu.add_separator()
        focus_menu.add_command(label="切换聚焦级别", command=self._cycle_focus_level, accelerator="Ctrl+Shift+F")
        focus_menu.add_command(label="专注模式设置...", command=self.open_focus_mode_settings)

        view_menu.add_command(label="沉浸模式 (Zen Mode)", command=self.toggle_zen_mode, accelerator="F11")

        settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label=f"通用/{ASSISTANT_NAME}设置...", command=lambda: self.open_settings_dialog())
        settings_menu.add_separator()
        settings_menu.add_checkbutton(label="AI 模式", variable=self.ai_mode_var, command=self.toggle_ai_mode)

        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help, accelerator="F1")
        help_menu.add_command(label="快捷键速查", command=self.show_shortcuts, accelerator="Ctrl+/")
        help_menu.add_separator()
        help_menu.add_command(label="快速入门", command=lambda: self.show_help("getting_started"))
        help_menu.add_command(label="AI 功能说明", command=lambda: self.show_help("ai_features"))
        help_menu.add_command(label="常见问题", command=lambda: self.show_help("troubleshooting"))
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=self.show_about)

    def _update_timer_ui(self, text, color):
        self.timer_var.set(text)
        if hasattr(self, "timer_label") and self.timer_label:
            self.timer_label.configure(foreground=color)
        if hasattr(self, "zen_timer_label") and self.zen_timer_label and self.zen_timer_label.winfo_exists():
             try:
                self.zen_timer_label.configure(foreground=color)
             except Exception:
                pass

    def show_timer_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="开始/暂停", command=self.pomodoro_controller.toggle)
        menu.add_command(label="重置当前", command=self.pomodoro_controller.reset)
        menu.add_separator()
        menu.add_command(label="切换到: 工作模式", command=lambda: self.pomodoro_controller.set_mode(PomodoroController.MODE_WORK))
        menu.add_command(label="切换到: 短休息", command=lambda: self.pomodoro_controller.set_mode(PomodoroController.MODE_SHORT_BREAK))
        menu.add_command(label="切换到: 长休息", command=lambda: self.pomodoro_controller.set_mode(PomodoroController.MODE_LONG_BREAK))
        menu.add_separator()
        menu.add_command(label="设置...", command=self.pomodoro_controller.open_settings)
        menu.post(event.x_root, event.y_root)

    def bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.new_project())
        self.root.bind("<Control-o>", lambda e: self.open_project())
        self.root.bind("<Control-s>", lambda e: self.save_project())
        self.root.bind("<Control-f>", lambda e: self.open_search_dialog())
        self.root.bind("<Control-h>", lambda e: self.open_search_dialog(focus_replace=True))
        self.root.bind("<F1>", lambda e: self.show_help())
        self.root.bind("<Control-slash>", lambda e: self.show_shortcuts())
        self.root.bind("<Control-question>", lambda e: self.show_shortcuts())  # Alternative for some keyboards
        self.root.bind("<F5>", lambda e: self.refresh_all())
        self.root.bind("<F2>", lambda e: self.toggle_floating_assistant())
        self.root.bind("<F9>", lambda e: self.toggle_typewriter_mode())  # Typewriter mode shortcut
        self.root.bind("<F10>", lambda e: self.toggle_focus_mode())  # Focus mode shortcut
        self.root.bind("<Control-Shift-F>", lambda e: self._cycle_focus_level())  # Cycle focus levels
        # Direct focus level shortcuts
        self.root.bind("<Control-Shift-exclam>", lambda e: self.set_focus_level("line"))  # Ctrl+Shift+1
        self.root.bind("<Control-Shift-at>", lambda e: self.set_focus_level("sentence"))  # Ctrl+Shift+2
        self.root.bind("<Control-Shift-numbersign>", lambda e: self.set_focus_level("paragraph"))  # Ctrl+Shift+3
        self.root.bind("<Control-Shift-dollar>", lambda e: self.set_focus_level("dialogue"))  # Ctrl+Shift+4
        self.root.bind("<F11>", lambda e: self.toggle_zen_mode())
        self.root.bind("<Escape>", lambda e: self._handle_escape())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        # Tab navigation shortcuts
        self.root.bind("<Control-Tab>", lambda e: self._switch_tab(1))
        self.root.bind("<Control-Shift-Tab>", lambda e: self._switch_tab(-1))
        self.root.bind("<Control-ISO_Left_Tab>", lambda e: self._switch_tab(-1))  # Linux/Mac
        # Direct tab access Alt+1 through Alt+9
        for i in range(1, 10):
            self.root.bind(f"<Alt-Key-{i}>", lambda e, idx=i-1: self._select_tab_by_index(idx))
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _switch_tab(self, direction):
        """Switch to next/previous tab. Direction: 1 for next, -1 for previous."""
        try:
            # Get list of enabled tab keys in order
            tab_keys = list(self.tabs.keys())
            if not tab_keys:
                return

            # Find current tab key
            current_key = None
            if hasattr(self, "sidebar_controller"):
                _, current_key = self.sidebar_controller.get_current()

            if not current_key or current_key not in tab_keys:
                current_idx = 0
            else:
                current_idx = tab_keys.index(current_key)

            # Calculate new index
            new_idx = (current_idx + direction) % len(tab_keys)
            new_key = tab_keys[new_idx]

            # Navigate using sidebar
            if hasattr(self, "sidebar"):
                self.sidebar.select_item_by_key(new_key)
                self.sidebar_controller.show_content(new_key)
        except Exception:
            pass

    def _select_tab_by_index(self, index):
        """Select tab by index (0-based)."""
        try:
            tab_keys = list(self.tabs.keys())
            if 0 <= index < len(tab_keys):
                key = tab_keys[index]
                if hasattr(self, "sidebar"):
                    self.sidebar.select_item_by_key(key)
                    self.sidebar_controller.show_content(key)
        except Exception:
            pass

    def _execute_command(self, command, refresh_mindmap=True, refresh_script_ui=True):
        if self.history_manager.execute_command(command):
            self.update_menu_state()
            return True
        return False

    def undo(self):
        if self.history_manager.can_undo():
            self.history_manager.undo()
            self.status_var.set("已撤销")
        else:
            self.status_var.set("无法撤销")
        self.update_menu_state()

    def redo(self):
        if self.history_manager.can_redo():
            self.history_manager.redo()
            self.status_var.set("已重做")
        else:
            self.status_var.set("无法重做")
        self.update_menu_state()

    def update_menu_state(self):
        if hasattr(self, "edit_menu"):
            self.edit_menu.entryconfig("撤销", state=tk.NORMAL if self.history_manager.can_undo() else tk.DISABLED)
            self.edit_menu.entryconfig("重做", state=tk.NORMAL if self.history_manager.can_redo() else tk.DISABLED)

    def refresh_script_ui(self):
        if hasattr(self, 'script_controller') and self.script_controller:
            self.script_controller.refresh()

    def setup_kanban_ui(self):
        self.kanban_controller = KanbanController(self.kanban_frame, self.project_manager, self._execute_command, self.theme_manager)
        self.registry.register("kanban", self.kanban_controller,
            refresh_groups=[RefreshGroups.SCENE, RefreshGroups.KANBAN])

    def setup_calendar_ui(self):
        self.calendar_controller = CalendarController(self.calendar_frame, self.project_manager, self._execute_command, self.theme_manager, self.jump_to_scene_by_index)
        self.registry.register("calendar", self.calendar_controller,
            refresh_groups=[RefreshGroups.SCENE])

    def setup_timeline_ui(self):
        self.timeline_controller = TimelineController(self.timeline_frame, self.project_manager, self._execute_command, self.theme_manager)
        self.registry.register("timeline", self.timeline_controller,
            refresh_groups=[RefreshGroups.TIMELINE, RefreshGroups.SCENE])

    def setup_story_curve_ui(self):
        self.story_curve_controller = StoryCurveController(
            self.story_curve_frame, 
            self.project_manager, 
            self._execute_command, 
            self.theme_manager,
            self.jump_to_scene_by_index
        )

    def jump_to_scene_by_index(self, idx):
        if 0 <= idx < len(self.project_manager.get_scenes()):
            if hasattr(self, "script_frame") and self.script_frame:
                self.notebook.select(self.script_frame)
                # Sync sidebar selection
                if hasattr(self, "sidebar"):
                    self.sidebar.select_item_by_key("script")
            if hasattr(self, "script_controller") and self.script_controller:
                self.script_controller.jump_to_scene_from_flowchart(idx)

    def jump_to_wiki_entry(self, name):
        """Switch to wiki tab and select entry by name."""
        if hasattr(self, "wiki_frame"):
            self.notebook.select(self.wiki_frame)
            # Sync sidebar selection
            if hasattr(self, "sidebar"):
                self.sidebar.select_item_by_key("wiki")
            if hasattr(self, "wiki_controller"):
                self.wiki_controller.select_entry_by_name(name)

    def navigate_to_module(self, key: str):
        """Switch to a module tab and sync sidebar selection."""
        tabs = getattr(self, "tabs", {})
        if key in tabs:
            self.notebook.select(tabs[key])
        if hasattr(self, "sidebar_controller") and self.sidebar_controller:
            self.sidebar_controller.navigate_to(key)

    def setup_analytics_ui(self):
        self.analytics_panel = AnalyticsPanel(self.analytics_frame, self.project_manager, self.gamification_manager)
        self.analytics_panel.pack(fill=tk.BOTH, expand=True)

    def _build_outline_scene_counts(self):
        counts = {}
        outline_root = self.project_manager.get_outline()
        def _build_path_map(node, prefix=""):
            if not node: return {}
            name = node.get("name", "")
            current_path = f"{prefix} / {name}" if prefix else name
            mapping = {current_path: node.get("uid", "")} 
            for child in node.get("children", []):
                mapping.update(_build_path_map(child, current_path))
            return mapping
        path_map = _build_path_map(outline_root)
        for scene in self.project_manager.get_scenes():
            uid = scene.get("outline_ref_id", "")
            if not uid:
                path = scene.get("outline_ref_path", "") or scene.get("outline_ref", "")
                uid = path_map.get(path, "")
            if uid:
                counts[uid] = counts.get(uid, 0) + 1
        return counts

    def open_tag_manager(self):
        TagManagerDialog(self.root, self.project_manager, self._execute_command)

    def _setup_event_subscriptions(self):
        """
        设置事件总线订阅。

        事件总线允许更精细的更新控制，仅刷新受影响的组件。
        这是对现有 on_project_data_changed 的补充。
        """
        # 场景相关事件
        self.event_bus.subscribe("scene_added", self._on_scene_event)
        self.event_bus.subscribe("scene_updated", self._on_scene_event)
        self.event_bus.subscribe("scene_deleted", self._on_scene_event)

        # 角色相关事件
        self.event_bus.subscribe("character_added", self._on_character_event)
        self.event_bus.subscribe("character_updated", self._on_character_event)
        self.event_bus.subscribe("character_deleted", self._on_character_event)

        # 大纲相关事件
        self.event_bus.subscribe("outline_changed", self._on_outline_event)

        # 百科相关事件
        self.event_bus.subscribe("wiki_entry_added", self._on_wiki_event)
        self.event_bus.subscribe("wiki_entry_updated", self._on_wiki_event)
        self.event_bus.subscribe("wiki_entry_deleted", self._on_wiki_event)

        # 时间线事件
        self.event_bus.subscribe("timeline_event_added", self._on_timeline_event)
        self.event_bus.subscribe("timeline_event_updated", self._on_timeline_event)
        self.event_bus.subscribe("timeline_event_deleted", self._on_timeline_event)

        # 关系图事件
        self.event_bus.subscribe("relationship_added", self._on_relationship_event)
        self.event_bus.subscribe("relationship_updated", self._on_relationship_event)
        self.event_bus.subscribe("faction_relation_changed", self._on_relationship_event)

        # 看板事件
        self.event_bus.subscribe("kanban_task_added", self._on_kanban_event)
        self.event_bus.subscribe("kanban_task_updated", self._on_kanban_event)

        # 证据板事件
        self.event_bus.subscribe("clue_added", self._on_evidence_event)
        self.event_bus.subscribe("clue_updated", self._on_evidence_event)
        self.event_bus.subscribe("clue_deleted", self._on_evidence_event)
        self.event_bus.subscribe("evidence_updated", self._on_evidence_event)
        self.event_bus.subscribe("evidence_node_added", self._on_evidence_event)
        self.event_bus.subscribe("evidence_node_deleted", self._on_evidence_event)
        self.event_bus.subscribe("evidence_link_added", self._on_evidence_event)

        # 资源事件
        self.event_bus.subscribe("asset_added", self._on_asset_event)
        self.event_bus.subscribe("asset_updated", self._on_asset_event)
        self.event_bus.subscribe("asset_deleted", self._on_asset_event)

        # 导航请求事件
        self.event_bus.subscribe("scene_jump_requested", self._on_scene_jump_requested)
        self.event_bus.subscribe("asset_insert_requested", self._on_asset_insert_requested)

        # 专注模式事件
        self.event_bus.subscribe(Events.FOCUS_SESSION_ENDED, self._on_focus_session_ended)
        self.event_bus.subscribe(Events.ZEN_MODE_EXITED, self._on_zen_mode_exited)
        self.event_bus.subscribe(Events.PROJECT_CONFIG_CHANGED, self._on_project_config_changed)
        self.event_bus.subscribe(Events.PROJECT_LOADED, self._on_project_config_changed)
        self.event_bus.subscribe(Events.OPEN_MODULE_CATALOG, self._on_open_module_catalog)

    def _on_focus_session_ended(self, event_type=None, **kwargs):
        """处理专注会话结束事件 - 记录到游戏化系统"""
        duration = kwargs.get("duration", 0)
        if duration > 60:  # 超过1分钟才记录
            self.gamification_manager.record_focus_session(duration, is_zen_mode=False)

    def _on_zen_mode_exited(self, event_type=None, **kwargs):
        """处理禅模式退出事件 - 记录到游戏化系统"""
        duration = kwargs.get("duration", 0)
        if duration > 60:  # 超过1分钟才记录
            self.gamification_manager.record_focus_session(duration, is_zen_mode=True)

    def _on_project_config_changed(self, event_type=None, **kwargs):
        """处理项目配置变更（模块/类型/标签等）。"""
        if hasattr(self, "_config_refresh_job") and self._config_refresh_job:
            try:
                self.root.after_cancel(self._config_refresh_job)
            except tk.TclError:
                pass
        self._config_refresh_job = self.root.after(50, self._apply_project_config_change)

    def _apply_project_config_change(self):
        self._config_refresh_job = None
        self.rebuild_tabs()
        if hasattr(self, "ai_controller"):
            self.ai_controller.on_project_config_changed()

    def _on_scene_jump_requested(self, event_type=None, **kwargs):
        """处理场景跳转请求。"""
        scene_idx = kwargs.get("scene_idx")
        if scene_idx is not None:
            self.jump_to_scene_by_index(scene_idx)

    def _on_open_module_catalog(self, event_type=None, **kwargs):
        """打开模块工具箱。"""
        self.open_module_catalog()

    def _on_asset_insert_requested(self, event_type=None, **kwargs):
        """处理资源插入请求（将资源代码插入编辑器）。"""
        asset_type = kwargs.get("asset_type", "")
        asset_name = kwargs.get("asset_name", "")
        asset_path = kwargs.get("asset_path", "")
        ref_code = kwargs.get("ref_code", "") or ""
        full_ref = kwargs.get("full_ref", "") or ""

        # 构建插入文本
        if ref_code:
            insert_text = ref_code
        elif full_ref:
            insert_text = full_ref
        elif asset_type == "character":
            insert_text = f'show {asset_name}'
        elif asset_type == "background":
            insert_text = f'scene {asset_name}'
        elif asset_type == "audio":
            insert_text = f'play music "{asset_path}"'
        else:
            insert_text = f'# {asset_type}: {asset_name}'

        if insert_text and not insert_text.endswith("\n"):
            insert_text += "\n"

        # 插入到编辑器
        sc = getattr(self, 'script_controller', None)
        if sc and hasattr(sc, 'script_editor'):
            if hasattr(self, "script_frame") and self.script_frame:
                self.notebook.select(self.script_frame)
                # Sync sidebar selection
                if hasattr(self, "sidebar"):
                    self.sidebar.select_item_by_key("script")
            sc.script_editor.insert(tk.INSERT, insert_text)
            sc.script_editor.focus_set()
            self.status_var.set(f"已插入资源: {asset_name}")
            return

        # 回退剪贴板
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(insert_text.strip())
            self.status_var.set(f"资源已复制到剪贴板: {asset_name}")
        except tk.TclError:
            pass

    def _on_scene_event(self, **kwargs):
        """处理场景相关事件。"""
        self.registry.refresh_group(RefreshGroups.SCENE)
        self.update_title()

    def _on_character_event(self, **kwargs):
        """处理角色相关事件。"""
        self.registry.refresh_group(RefreshGroups.CHARACTER)
        self.update_title()

    def _on_outline_event(self, **kwargs):
        """处理大纲相关事件。"""
        self.registry.refresh_group(RefreshGroups.OUTLINE)
        self.update_title()

    def _on_wiki_event(self, **kwargs):
        """处理百科相关事件。"""
        self.registry.refresh_group(RefreshGroups.WIKI)
        self.update_title()

    def _on_timeline_event(self, **kwargs):
        """处理时间线相关事件。"""
        self.registry.refresh_group(RefreshGroups.TIMELINE)
        self.update_title()

    def _on_relationship_event(self, **kwargs):
        """处理关系图相关事件。"""
        self.registry.refresh_group(RefreshGroups.RELATIONSHIP)
        self.update_title()

    def _on_kanban_event(self, **kwargs):
        """处理看板相关事件。"""
        self.registry.refresh_group(RefreshGroups.KANBAN)
        self.update_title()

    def _on_evidence_event(self, **kwargs):
        """处理证据板相关事件。"""
        self.registry.refresh_group(RefreshGroups.EVIDENCE)
        self.update_title()

    def _on_asset_event(self, **kwargs):
        """处理资源相关事件。"""
        self.registry.refresh_group(RefreshGroups.ASSET)
        self.update_title()

    def on_project_data_changed(self, event_type="all"):
        """
        传统的全局刷新处理器（由 ProjectManager.mark_modified 触发）。

        保留此方法以确保向后兼容性。
        新代码应优先使用事件总线进行更精细的更新。
        """
        group_map = {
            "outline": [RefreshGroups.OUTLINE],
            "script": [RefreshGroups.SCENE, RefreshGroups.CHARACTER],
            "world": [RefreshGroups.WIKI],
            "wiki": [RefreshGroups.WIKI],
            "timeline": [RefreshGroups.TIMELINE],
            "relationships": [RefreshGroups.RELATIONSHIP],
            "factions": [RefreshGroups.RELATIONSHIP],
            "kanban": [RefreshGroups.KANBAN],
            "analytics": [RefreshGroups.ANALYTICS],
            "ideas": [RefreshGroups.ALL],
            "meta": [RefreshGroups.ALL],
            "evidence": [RefreshGroups.EVIDENCE]
        }

        groups = group_map.get(event_type)
        if groups:
            self.registry.refresh_multiple_groups(groups)
        else:
            self.registry.refresh_all()
        self.update_title()

    def toggle_floating_assistant(self):
        FloatingAssistantManager.toggle(self.root, self.project_manager, self.config_manager)
        # 设置集成管理器（包括音频播放器）
        FloatingAssistantManager.setup_integrations(
            gamification_manager=self.gamification_manager,
            ambiance_player=self.ambiance_player,
            typewriter_player=self.typewriter_player
        )

    def _run_logic_validation_silent(self):
        """Run logic validation for module sync without blocking UI."""
        try:
            validator = get_logic_validator(self.project_manager)
            report = validator.run_full_validation()
            self._last_validation_report = report
            issue_count = len(report.issues)

            if issue_count > 0:
                if self._last_validation_issue_count != issue_count:
                    self.status_var.set(f"发现 {issue_count} 处逻辑断点，点击“逻辑校验”查看")
                    get_event_bus().publish(Events.VALIDATION_ISSUES_FOUND, report=report)
            else:
                if self._last_validation_issue_count:
                    self.status_var.set("逻辑检查通过")
                    get_event_bus().publish(Events.VALIDATION_PASSED)

            self._last_validation_issue_count = issue_count
        except Exception as exc:
            logger.warning("Logic validation failed: %s", exc)

    def open_settings_dialog(self, initial_tab="general"):
        dlg = SettingsDialog(self.root, self.config_manager, initial_tab=initial_tab, ai_client=self.ai_client)
        self.root.wait_window(dlg)
        if not getattr(dlg, "result", None):
            return

        res = dlg.result
        # AI接口
        self.lm_api_url.set(res.get("lm_api_url", "").strip())
        self.lm_api_model.set(res.get("lm_api_model", "").strip())
        self.lm_api_key.set(res.get("lm_api_key", ""))
        self.config_manager.set("lm_api_url", self.lm_api_url.get())
        self.config_manager.set("lm_api_model", self.lm_api_model.get())
        self.config_manager.set("lm_api_key", self.lm_api_key.get())
        if "ai_mode_enabled" in res:
            self.set_ai_mode(res.get("ai_mode_enabled", True), persist=False)

        # Theme Settings
        if "theme" in res:
            theme_name = res.get("theme")
            bg_image = res.get("background_image")
            bg_opacity = res.get("background_opacity", 1.0)
            custom_colors = res.get("custom_theme_colors")

            self.config_manager.set("theme", theme_name)
            self.config_manager.set("background_image", bg_image)
            self.config_manager.set("background_opacity", bg_opacity)
            self.config_manager.set("custom_theme_colors", custom_colors)
            self.config_manager.set("ui_font", res.get("ui_font"))
            self.config_manager.set("ui_font_size", res.get("ui_font_size"))
            self.config_manager.set("editor_font", res.get("editor_font"))
            self.config_manager.set("editor_font_size", res.get("editor_font_size"))

            self.theme_manager.set_custom_colors(custom_colors)
            self.theme_manager.set_background_image(bg_image)
            self.theme_manager.set_background_opacity(bg_opacity)
            self.theme_manager.set_theme(theme_name)
            self.apply_theme()

        # Templates
        if "character_template" in res:
            self.config_manager.set("character_template", res.get("character_template"))
            
        # AI Prompts
        for key in ["prompt_continue_script", "prompt_rewrite_script", "prompt_diagnose_outline", "prompt_generate_outline"]:
            if key in res:
                self.config_manager.set(key, res.get(key))
                
        # Export Settings
        for key in ["export_pdf_margin", "export_pdf_line_spacing", "export_font_family"]:
            if key in res:
                self.config_manager.set(key, res.get(key))

        # 悬浮助手
        assistant_settings = res.get("assistant", {})
        FloatingAssistantManager.apply_settings(self.config_manager, assistant_settings)
        if "assistant_primary_mode" in res:
            primary_mode = bool(res.get("assistant_primary_mode", False))
            self.config_manager.set("assistant_primary_mode", primary_mode)
            self._apply_assistant_primary_mode(primary_mode)

        # Weather Settings
        for key in ["weather_enabled", "weather_api_key", "weather_api_host", "weather_location",
                    "weather_location_name", "weather_auto_ambiance", "weather_show_in_scene"]:
            if key in res:
                self.config_manager.set(key, res.get(key))

        # Taskbar/close behavior
        if "close_behavior" in res:
            self.close_behavior = res.get("close_behavior", "ask")
            self.config_manager.set("close_behavior", self.close_behavior)
        if "taskbar_date_events" in res:
            self.taskbar_date_events = list(res.get("taskbar_date_events", []))
            self.config_manager.set("taskbar_date_events", self.taskbar_date_events)
            if hasattr(self, "tray_manager"):
                self.tray_manager.set_events(self.taskbar_date_events)

        if "guide_mode_enabled" in res:
            guide_enabled = res.get("guide_mode_enabled", True)
            self.config_manager.set("guide_mode_enabled", guide_enabled)
            if not guide_enabled:
                self.guide_controller.close()
            elif guide_enabled and not self.guide_controller.is_running:
                self.guide_controller.start_if_needed()

        # Update floating assistant weather service if enabled
        if FloatingAssistantManager._instance and res.get("weather_enabled"):
            try:
                FloatingAssistantManager._instance._init_weather_service()
            except Exception as e:
                logger.warning(f"Failed to reinitialize weather service: {e}")

        self.config_manager.save()
        messagebox.showinfo("提示", "设置已保存", parent=self.root)

    def is_ai_mode_enabled(self):
        return bool(self.config_manager.get("ai_mode_enabled", True))

    def toggle_ai_mode(self):
        self.set_ai_mode(self.ai_mode_var.get(), persist=True, show_message=True)

    def set_ai_mode(self, enabled, persist=True, show_message=False):
        enabled = bool(enabled)
        self.ai_mode_var.set(enabled)
        self.config_manager.set("ai_mode_enabled", enabled)
        self.apply_ai_mode(enabled)
        if persist:
            self.config_manager.save()
        if show_message:
            status = "开启" if enabled else "关闭"
            self.status_var.set(f"AI模式: {status}")
            messagebox.showinfo("提示", f"AI 模式已{status}", parent=self.root)

    def apply_ai_mode(self, enabled):
        if not enabled and hasattr(self, "ai_controller") and self.ai_controller:
            self.ai_controller.cancel_all_tasks()

        # Handle Tab hiding/showing
        if hasattr(self, "notebook") and hasattr(self, "chat_frame") and "chat" in self.project_manager.get_enabled_tools():
            if enabled:
                # Add if not present
                found = False
                for tab_id in self.notebook.tabs():
                    if self.notebook.nametowidget(tab_id) == self.chat_frame:
                        found = True
                        break
                if not found:
                    self.notebook.add(self.chat_frame, text="  项目对话  ")
            else:
                # Hide the tab
                try:
                    self.notebook.hide(self.chat_frame)
                except tk.TclError:
                    pass

        # Use capability-based controller lookup instead of multiple hasattr checks
        if hasattr(self, "registry") and self.registry:
            self.registry.call_on_controllers_with_capability(
                Capabilities.AI_MODE,
                "set_ai_mode_enabled",
                enabled
            )

        # Handle non-registered views (reverse_engineering_view is not in registry)
        if hasattr(self, "reverse_engineering_view") and self.reverse_engineering_view:
            if hasattr(self.reverse_engineering_view, "set_ai_mode_enabled"):
                self.reverse_engineering_view.set_ai_mode_enabled(enabled)

        FloatingAssistantManager.apply_ai_mode(enabled)
        get_event_bus().publish(Events.AI_MODE_CHANGED, enabled=enabled)

    def toggle_focus_mode(self):
        self.mode_manager.toggle_focus_mode()

    def set_focus_level(self, level):
        self.mode_manager.set_focus_level(level)

    def toggle_typewriter_mode(self):
        self.mode_manager.toggle_typewriter_mode()

    def _cycle_focus_level(self):
        self.mode_manager.cycle_focus_level()

    def _handle_escape(self):
        self.mode_manager.handle_escape()

    def open_focus_mode_settings(self):
        self.mode_manager.open_focus_mode_settings()

    def toggle_zen_mode(self):
        self.mode_manager.toggle_zen_mode()

    def open_word_sprint(self):
        self.mode_manager.open_word_sprint()

    def _on_theme_changed(self):
        self.theme_controller.on_theme_changed()

    def toggle_theme(self):
        self.theme_controller.toggle_theme()

    def apply_theme(self):
        self.theme_controller.apply_theme()

    def open_search_dialog(self, event=None, focus_replace=False):
        if self.search_dialog and self.search_dialog.winfo_exists():
            self.search_dialog.lift()
            if focus_replace:
                self.search_dialog.focus_replace_field()
            return
        self.search_dialog = SearchDialog(
            self.root,
            self.project_manager,
            self.on_search_navigate,
            command_executor=self._execute_command
        )
        if focus_replace:
            self.search_dialog.focus_replace_field()

    def open_global_rename_dialog(self):
        old_text = simpledialog.askstring("全局替换", "请输入要替换的旧文本:", parent=self.root)
        if not old_text: return
        new_text = simpledialog.askstring("全局替换", f"将 '{old_text}' 替换为:", parent=self.root)
        if new_text is None: return # Cancelled
        
        if messagebox.askyesno("确认替换", f"确定要将整个项目中的 '{old_text}' 替换为 '{new_text}' 吗？\n此操作将影响大纲、剧本、角色名和百科。", icon='warning'):
            cmd = GlobalRenameCommand(self.project_manager, old_text, new_text)
            if self._execute_command(cmd):
                messagebox.showinfo("成功", "替换完成")
                self.refresh_all()

    def jump_to_outline_node(self, uid):
        """Switch to outline tab and select node by UID."""
        if hasattr(self, "outline_frame"):
            self.notebook.select(self.outline_frame)
            # Sync sidebar selection
            if hasattr(self, "sidebar"):
                self.sidebar.select_item_by_key("outline")
            # We need to find the node and select it in the canvas
            # Assuming mindmap_canvas has a method to select by ID
            if hasattr(self, "mindmap_canvas"):
                self.mindmap_canvas.select_node(uid)
                # Ideally, center view on node
                node_item = self.mindmap_canvas.node_items.get(uid)
                if node_item:
                    # Center logic could be added to ZoomableCanvas, but for now selection is enough
                    pass

    def on_search_navigate(self, result):
        res_type = result.get("type")
        idx = result.get("index")

        if res_type == "scene":
            self.jump_to_scene_by_index(idx)
        elif res_type == "character":
            self.notebook.select(self.script_frame)
            # Sync sidebar selection
            if hasattr(self, "sidebar"):
                self.sidebar.select_item_by_key("script")
            if hasattr(self, "char_listbox"):
                self.char_listbox.selection_clear(0, tk.END)
                self.char_listbox.selection_set(idx)
                self.char_listbox.event_generate("<<ListboxSelect>>")
                self.char_listbox.see(idx)
        elif res_type == "wiki":
            # Index is list index, but jump_to_wiki_entry uses name. 
            # Or we can select by index if WikiController supports it.
            # Let's use name since we have it in result.
            self.jump_to_wiki_entry(result.get("name"))
        elif res_type == "outline":
            self.jump_to_outline_node(idx) # idx is uid for outline

    def refresh_all(self):
        if hasattr(self, "mindmap_controller") and self.mindmap_controller:
            self.mindmap_controller.refresh()
        self.refresh_script_ui()
        if hasattr(self, 'refresh_wiki_list'):
            self.refresh_wiki_list()
        if hasattr(self, 'idea_controller') and self.idea_controller:
            self.idea_controller.refresh()
        self.update_title()
        self.update_menu_state()

    def on_mindmap_select(self, node):
        self.current_selected_node = node
        self.node_title_var.set(node.get("name", ""))
        self.node_content_text.delete("1.0", tk.END)
        self.node_content_text.insert("1.0", node.get("content", ""))

    def update_title(self):
        title = "写作助手"
        if self.project_manager.current_file: title += f" - {Path(self.project_manager.current_file).name}"
        else: title += " - 新项目"
        if self.project_manager.modified: title += " *"
        self.root.title(title)

    def add_child_node(self):
        if hasattr(self, "mindmap_controller") and self.mindmap_controller:
            self.mindmap_controller.add_child_node()

    def add_sibling_node(self):
        if hasattr(self, "mindmap_controller") and self.mindmap_controller:
            self.mindmap_controller.add_sibling_node()

    def delete_node(self):
        if hasattr(self, "mindmap_controller") and self.mindmap_controller:
            self.mindmap_controller.delete_node()

    def insert_outline_template(self, template_key):
        parent_obj_id = list(self.mindmap_canvas.selected_node_ids)[0] if self.mindmap_canvas.selected_node_ids else self.project_manager.get_outline().get("uid")
        template_nodes = get_outline_template_nodes(template_key)
        if not template_nodes: return
        
        def _apply(pid, data):
            new_node = {"name": data.get("name", ""), "content": data.get("content", ""), "children": []}
            cmd = AddNodeCommand(self.project_manager, pid, new_node, "Template")
            if self._execute_command(cmd, refresh_mindmap=False):
                for c in data.get("children",[]): _apply(cmd.added_node_uid, c)
        
        for node_data in template_nodes: _apply(parent_obj_id, node_data)
        self.refresh_mindmap_ui()

    def set_mindmap_style(self, style_key):
        self.project_manager.set_outline_template_style(style_key)
        self.mindmap_canvas.refresh()

    def show_outline_template_help(self):
        messagebox.showinfo("Help", "Templates...")

    def expand_all(self):
        if hasattr(self, "mindmap_controller") and self.mindmap_controller:
            self.mindmap_controller.expand_all()

    def collapse_all(self):
        if hasattr(self, "mindmap_controller") and self.mindmap_controller:
            self.mindmap_controller.collapse_all()

    def _set_collapse_all(self, node, collapsed):
        node["_collapsed"] = collapsed
        for child in node.get("children", []): self._set_collapse_all(child, collapsed)

    def save_node_details(self):
        if not self.current_selected_node: return
        old_name = self.current_selected_node.get("name", "")
        old_content = self.current_selected_node.get("content", "")
        new_name = self.node_title_var.get().strip()
        new_content = self.node_content_text.get("1.0", tk.END).strip()
        if old_name != new_name or old_content != new_content:
            command = EditNodeCommand(self.project_manager, self.current_selected_node.get("uid"), old_name, new_name, old_content, new_content, "Edit Node")
            self._execute_command(command)
            self.mindmap_canvas.refresh()

    def on_closing(self):
        behavior = self.close_behavior or "ask"
        if behavior == "ask":
            behavior = self._prompt_close_behavior()
            self.close_behavior = behavior
            self.config_manager.set("close_behavior", behavior)
            self.config_manager.save()

        if behavior == "minimize":
            self._minimize_to_tray()
            return

        self._exit_app()

    def exit_app(self):
        """显式退出入口（托盘/菜单调用）"""
        self._exit_app()

    def _exit_app(self):
        """退出应用程序，按照正确的顺序清理资源"""
        # 1. 停止后台服务
        if hasattr(self, "backup_manager") and self.backup_manager:
            try:
                self.backup_manager.stop()
            except Exception:
                pass

        if hasattr(self, "pomodoro_controller") and self.pomodoro_controller:
            try:
                self.pomodoro_controller.pause()
            except Exception:
                pass

        # 2. 停止AI线程池（取消所有进行中的任务）
        shutdown_thread_pool()

        # 3. 清理悬浮助手
        try:
            inst = FloatingAssistantManager.get_instance()
            if inst and inst.winfo_exists():
                inst.destroy()
        except Exception:
            pass

        # 4. 清理所有注册的控制器（通过registry）
        if hasattr(self, "registry") and self.registry:
            try:
                self.registry.cleanup_all()
            except Exception:
                pass

        # 5. 保存配置
        self.config_manager.set("window_geometry", self.root.geometry())
        if self.project_manager.current_file:
            self.config_manager.set("last_opened_file", str(self.project_manager.current_file))

        # Save AI settings
        self.config_manager.set("lm_api_url", self.lm_api_url.get().strip())
        self.config_manager.set("lm_api_model", self.lm_api_model.get().strip())
        self.config_manager.set("lm_api_key", self.lm_api_key.get().strip())

        self.config_manager.save()
        self.gamification_manager.save()

        # 6. 处理未保存更改
        if self.project_manager.modified:
            if messagebox.askyesno("Save", "Save changes?"):
                self.save_project()

        # 7. 停止系统托盘
        if hasattr(self, "tray_manager") and self.tray_manager:
            try:
                self.tray_manager.stop()
            except Exception:
                pass

        # 8. 销毁窗口
        self.root.destroy()

    def _prompt_close_behavior(self) -> str:
        """首次关闭时询问关闭行为。"""
        answer = messagebox.askyesno(
            "关闭行为",
            "关闭按钮是否改为最小化到托盘？\n选择“是”将最小化，选择“否”将直接退出。",
            parent=self.root
        )
        return "minimize" if answer else "exit"

    def _minimize_to_tray(self):
        """最小化到托盘（若托盘不可用则最小化窗口）。"""
        if hasattr(self, "tray_manager") and self.tray_manager.ensure_started():
            self._hide_main_window()
        else:
            self.root.iconify()

    def _show_main_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _hide_main_window(self):
        self.root.withdraw()

    def _ensure_floating_assistant_visible(self):
        inst = FloatingAssistantManager.get_instance()
        if inst and inst.winfo_exists():
            if not inst.winfo_viewable():
                inst.show()
        else:
            self.toggle_floating_assistant()

    def _apply_assistant_primary_mode(self, enabled: bool):
        if enabled:
            self._ensure_floating_assistant_visible()
            self._hide_main_window()
        else:
            self._show_main_window()

    def _apply_assistant_primary_mode_startup(self):
        if self.config_manager.get("assistant_primary_mode", False):
            self._apply_assistant_primary_mode(True)

    def show_help(self, initial_topic: str = None):
        """显示帮助对话框"""
        # 如果没有指定主题，根据当前标签页提供上下文帮助
        if initial_topic is None:
            initial_topic = self._get_current_context_topic()
        show_help_dialog(self.root, initial_topic)

    def show_shortcuts(self):
        """显示快捷键速查对话框"""
        show_shortcuts_dialog(self.root)

    def show_about(self):
        """显示关于对话框"""
        show_about_dialog(self.root)

    def _get_current_context_topic(self) -> str:
        """根据当前标签页获取对应的帮助主题"""
        try:
            # Use sidebar controller to get current item
            current_item = None
            if hasattr(self, "sidebar_controller"):
                _, current_item = self.sidebar_controller.get_current()

            # Item key to help topic mapping
            topic_mapping = {
                "outline": "outline",
                "script": "script",
                "timeline": "timeline",
                "kanban": "script",
                "relationship": "relationship",
                "evidence_board": "timeline",
                "calendar": "timeline",
                "analytics": "settings",
                "wiki": "script",
                "training": "ai_features",
                "chat": "ai_features",
                "dual_timeline": "timeline",
                "ideas": "getting_started",
                "research": "script",
            }

            if current_item and current_item in topic_mapping:
                return topic_mapping[current_item]

            return "getting_started"
        except Exception:
            return "getting_started"

    def new_project(self):
        if self.project_manager.modified and not messagebox.askyesno("Unsaved", "Discard?"): return
        self.project_manager.new_project()
        self.refresh_all()
    
    def save_project(self):
        # Save current scene content through ScriptController if available
        sc = getattr(self, 'script_controller', None)
        if sc:
            # ScriptController handles saving scene content internally
            if hasattr(sc, 'save_scene_content'):
                sc.save_scene_content()
            # Update script title from ScriptController's variable
            if hasattr(sc, 'script_title_var'):
                self.project_manager.get_script()["title"] = sc.script_title_var.get()

        if self.project_manager.current_file:
            self.project_manager.save_project()
            self.update_title()
        else:
            self.save_project_as()

    def save_project_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".writerproj", initialdir=self.data_dir)
        if path:
            self.project_manager.save_project(path)
            self.update_title()

    def open_project(self):
        if self.project_manager.modified and not messagebox.askyesno("Unsaved", "Discard?"): return
        path = filedialog.askopenfilename(defaultextension=".writerproj", initialdir=self.data_dir)
        if path:
            self.project_manager.load_project(path)
            self.refresh_all()

    def perform_export(self, fmt_class):
        """Generic export handler using ExporterRegistry."""
        if fmt_class.key == "sides":
            self.export_character_sides_dialog()
            return

        if fmt_class.requires_dir:
            path = filedialog.askdirectory(title=f"选择导出目录 ({fmt_class.name})")
        else:
            path = filedialog.asksaveasfilename(
                defaultextension=fmt_class.extension,
                filetypes=[(fmt_class.name, f"*{fmt_class.extension}"), ("All Files", "*.*")],
                title=f"导出为 {fmt_class.name}"
            )
            
        if not path: return
        
        # 获取导出设置
        export_font = self.config_manager.get("export_font_family", "Microsoft YaHei")
        export_margin = self.config_manager.get("export_pdf_margin", 20)
        export_spacing = self.config_manager.get("export_pdf_line_spacing", 1.5)
        
        try:
            ExporterRegistry.export(
                fmt_class.key, 
                self.project_manager.project_data, 
                path,
                font_name=export_font,
                margin=export_margin,
                line_spacing=export_spacing
            )
            self.guide_controller.mark_progress("export_done", {
                "format": fmt_class.key,
                "path": path
            })
            messagebox.showinfo("成功", f"导出成功！\n文件: {path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"错误信息: {str(e)}")

    def export_character_sides_dialog(self):
        chars = [c.get("name") for c in self.project_manager.get_characters()]
        if not chars:
            messagebox.showinfo("提示", "项目中没有角色。 ולא ניתן להמשיך.")
            return
            
        dlg = tk.Toplevel(self.root)
        dlg.title("导出角色台词本")
        dlg.geometry("300x150")
        
        ttk.Label(dlg, text="选择角色:").pack(pady=10)
        cb = ttk.Combobox(dlg, values=chars, state="readonly")
        cb.pack(pady=5)
        if chars: cb.current(0)
        
        def confirm():
            role = cb.get()
            if not role: return
            dlg.destroy()
            filename = tk.filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text File", "*.txt")], initialfile=f"{role}_Sides.txt")
            if filename:
                try:
                    Exporter.export_character_sides(self.project_manager.project_data, filename, role)
                    self.guide_controller.mark_progress("export_done", {
                        "format": "sides",
                        "path": filename
                    })
                    messagebox.showinfo("成功", f"{role} 的台词本已导出！")
                except Exception as e:
                    messagebox.showerror("错误", str(e))
        
        ttk.Button(dlg, text="导出", command=confirm).pack(pady=10)

    def change_project_type(self):
        """Open project settings dialog to change project type/length."""
        current_type = self.project_manager.get_project_type()
        current_length = self.project_manager.get_project_length()
        current_tags = self.project_manager.get_genre_tags()
        current_tools = self.project_manager.get_enabled_tools()
        current_wiki_categories = self.project_manager.get_wiki_categories()

        def on_confirm(new_type, new_length, selected_tags, selected_tools, wiki_categories):
            tools_changed = set(selected_tools) != set(current_tools)
            type_changed = new_type != current_type
            length_changed = new_length != current_length
            tags_changed = set(selected_tags) != set(current_tags)

            if tools_changed or type_changed or length_changed or tags_changed or wiki_categories is not None:
                if type_changed:
                    self.project_manager.set_project_type(new_type)
                if length_changed:
                    self.project_manager.set_project_length(new_length)
                if tags_changed:
                    self.project_manager.set_genre_tags(selected_tags)
                if wiki_categories is not None:
                    self.project_manager.set_wiki_categories(wiki_categories)
                self.project_manager.set_enabled_tools(selected_tools)
                type_label = self.project_manager.get_project_type_display_name()
                length_label = ProjectTypeManager.get_length_info(new_length).get("name", new_length)
                self.status_var.set(f"项目配置已更新: {type_label} / {length_label}")
                if type_changed:
                    FloatingAssistantManager.show_mode_guide(new_type, force=True)

        ProjectSettingsDialog(
            self.root,
            current_type,
            current_length,
            current_tags,
            current_tools,
            current_wiki_categories,
            on_confirm
        )

    def ai_continue_script(self, context): self.ai_controller.continue_script(context)

    def refresh_wiki_list(self):
        if hasattr(self, "wiki_controller") and self.wiki_controller:
            self.wiki_controller.refresh()

    def add_wiki_entry(self):
        self.wiki_controller.add_entry()

    def delete_wiki_entry(self):
        self.wiki_controller.delete_entry()

    def save_wiki_entry(self):
        self.wiki_controller.save_entry()

    def on_wiki_select(self, e):
        self.wiki_controller.on_select(e)

    def open_name_generator(self):
        NameGeneratorDialog(self.root, self.ai_client, self.theme_manager, self.config_manager)

    # --- AI Controller Helper Methods ---

    def _set_ai_generation_state(self, generating, status_text=""):
        """设置AI生成状态（用于大纲生成）"""
        self.ai_generating = generating
        self.ai_status_var.set(status_text)
        if hasattr(self, "mindmap_controller") and self.mindmap_controller:
            self.mindmap_controller.ai_generating = generating
            self.mindmap_controller.ai_status_var.set(status_text)

    def _set_script_ai_state(self, generating, status_text=""):
        """设置剧本AI生成状态"""
        self.script_ai_generating = generating
        self.script_ai_status_var.set(status_text)
        self.status_var.set(status_text)

    def _set_outline_helper_state(self, running, status_text=None):
        """设置大纲助手运行状态"""
        self.outline_helper_running = running
        if status_text:
            self.outline_helper_status_var.set(status_text)
        elif not running:
            self.outline_helper_status_var.set("选择节点后可用AI补全内容或生成子节点")
        if hasattr(self, "mindmap_controller") and self.mindmap_controller:
            self.mindmap_controller.outline_helper_running = running
            if status_text:
                self.mindmap_controller.outline_helper_status_var.set(status_text)

    def _normalize_outline_node(self, data, default_name="未命名"):
        """规范化大纲节点数据结构"""
        if not isinstance(data, dict):
            return None

        normalized = {
            "name": data.get("name", default_name) or default_name,
            "content": data.get("content", "") or "",
            "children": [],
            "uid": data.get("uid") or self.project_manager._gen_uid()
        }

        children = data.get("children", [])
        if isinstance(children, list):
            for child in children:
                norm_child = self._normalize_outline_node(child, "子节点")
                if norm_child:
                    normalized["children"].append(norm_child)

        return normalized

    def _apply_ai_outline(self, normalized_data):
        """应用AI生成的大纲数据"""
        if not self.is_ai_mode_enabled():
            return
        if not normalized_data:
            messagebox.showerror("错误", "无效的大纲数据")
            return

        # 替换整个大纲
        self.project_manager.project_data["outline"] = normalized_data
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.OUTLINE_CHANGED, source="ai")
        self.refresh_all()
        self.status_var.set("AI大纲生成完成")

    def _apply_ai_node_result(self, target_node, norm, mode):
        """应用AI生成的节点结果"""
        if not self.is_ai_mode_enabled():
            return
        if not target_node or not norm:
            return

        target_uid = target_node.get("uid")
        root = self.project_manager.get_outline()
        actual_node = self.project_manager.find_node_by_uid(root, target_uid)

        if not actual_node:
            messagebox.showerror("错误", "未找到目标节点")
            return

        if mode == "complete_content":
            # 补全当前节点内容
            actual_node["content"] = norm.get("content", actual_node.get("content", ""))
        elif mode == "generate_children":
            # 生成子节点
            new_children = norm.get("children", [])
            if "children" not in actual_node:
                actual_node["children"] = []
            actual_node["children"].extend(new_children)
        elif mode == "replace":
            # 替换节点
            actual_node["name"] = norm.get("name", actual_node.get("name", ""))
            actual_node["content"] = norm.get("content", "")
            actual_node["children"] = norm.get("children", [])

        self.project_manager.mark_modified()
        get_event_bus().publish(Events.OUTLINE_CHANGED, source="ai")
        self.refresh_all()
        self.status_var.set("AI节点处理完成")

    def _normalize_script_data(self, data):
        """规范化剧本数据结构"""
        if not isinstance(data, dict):
            return None

        normalized = {
            "title": data.get("title", "未命名剧本") or "未命名剧本",
            "characters": [],
            "scenes": []
        }

        # 处理角色
        characters = data.get("characters", [])
        if isinstance(characters, list):
            for char in characters:
                if isinstance(char, dict):
                    normalized["characters"].append({
                        "name": char.get("name", "未命名角色"),
                        "description": char.get("description", ""),
                        "tags": char.get("tags", [])
                    })
                elif isinstance(char, str):
                    normalized["characters"].append({
                        "name": char,
                        "description": "",
                        "tags": []
                    })

        # 处理场景
        scenes = data.get("scenes", [])
        if isinstance(scenes, list):
            for scene in scenes:
                if isinstance(scene, dict):
                    normalized["scenes"].append({
                        "name": scene.get("name", "未命名场景"),
                        "location": scene.get("location", ""),
                        "time": scene.get("time", ""),
                        "content": scene.get("content", ""),
                        "characters": scene.get("characters", []),
                        "tags": scene.get("tags", []),
                        "outline_ref_id": scene.get("outline_ref_id", "")
                    })

        return normalized

    def _apply_ai_script(self, normalized_data):
        """应用AI生成的剧本数据"""
        if not self.is_ai_mode_enabled():
            return
        if not normalized_data:
            messagebox.showerror("错误", "无效的剧本数据")
            return

        script = self.project_manager.get_script()
        script["title"] = normalized_data.get("title", script.get("title", ""))
        script["characters"] = normalized_data.get("characters", [])
        script["scenes"] = normalized_data.get("scenes", [])

        self.project_manager.mark_modified()
        get_event_bus().publish(Events.SCENE_UPDATED, source="ai")
        get_event_bus().publish(Events.CHARACTER_UPDATED, source="ai")
        self.refresh_all()
        self.status_var.set("AI剧本生成完成")

    def _add_generated_scene(self, name, content, outline_uid, outline_path):
        """添加AI生成的场景"""
        if not self.is_ai_mode_enabled():
            return
        new_scene = {
            "name": name,
            "location": "",
            "time": "",
            "content": content,
            "characters": [],
            "tags": [],
            "outline_ref_id": outline_uid,
            "outline_ref_path": outline_path
        }

        cmd = AddSceneCommand(self.project_manager, new_scene, f"添加场景: {name}")
        if self._execute_command(cmd):
            self.status_var.set(f"已添加场景: {name}")
            # 跳转到新场景
            scenes = self.project_manager.get_scenes()
            if scenes:
                self.jump_to_scene_by_index(len(scenes) - 1)

    def _insert_ai_text(self, text):
        """在编辑器中插入AI生成的文本"""
        if not self.is_ai_mode_enabled():
            return
        sc = getattr(self, 'script_controller', None)
        if sc and hasattr(sc, 'script_editor'):
            sc.script_editor.insert(tk.INSERT, text)
            self.status_var.set("AI续写内容已插入")
        else:
            messagebox.showinfo("提示", f"AI生成内容:\n\n{text[:500]}...")

def main():
    root = tk.Tk()
    app = WriterTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()
