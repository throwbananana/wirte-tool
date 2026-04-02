import tkinter as tk
from tkinter import ttk

from writer_app.controllers.ai_controller import AIController
from writer_app.controllers.analytics_controller import AnalyticsController
from writer_app.controllers.chat_controller import ChatController
from writer_app.controllers.flowchart_controller import FlowchartController
from writer_app.controllers.guide_controller import GuideController
from writer_app.controllers.idea_controller import IdeaController
from writer_app.controllers.kanban_controller import KanbanController
from writer_app.controllers.mindmap_controller import MindMapController
from writer_app.controllers.relationship_controller import RelationshipController
from writer_app.controllers.research_controller import ResearchController
from writer_app.controllers.script_controller import ScriptController
from writer_app.controllers.sidebar_controller import SidebarController
from writer_app.controllers.timeline_controller import TimelineController
from writer_app.controllers.training_controller import TrainingController
from writer_app.controllers.variable_controller import VariableController
from writer_app.controllers.wiki_controller import WikiController
from writer_app.controllers.dual_timeline_controller import DualTimelineController
from writer_app.controllers.calendar_controller import CalendarController
from writer_app.core.controller_registry import Capabilities, RefreshGroups
from writer_app.core.project_types import ProjectTypeManager
from writer_app.ui.alibi_timeline import AlibiTimelineController
from writer_app.ui.character_event_table import CharacterEventTable
from writer_app.ui.evidence_board import EvidenceBoardContainer
from writer_app.ui.faction_matrix import FactionMatrixController
from writer_app.ui.floating_assistant import FloatingAssistantManager
from writer_app.ui.idea_panel import IdeaPanel
from writer_app.ui.research import ResearchPanel
from writer_app.ui.reverse_engineering import ReverseEngineeringView
from writer_app.ui.sidebar import SidebarPanel
from writer_app.ui.story_curve import StoryCurveController
from writer_app.ui.swimlanes import SwimlaneView
from writer_app.ui.training_panel import TrainingPanel
from writer_app.ui.heartbeat_tracker import HeartbeatTrackerController
from writer_app.ui.world_iceberg import WorldIcebergController


class WorkspaceBuilder:
    """Build and rebuild the main workspace UI from the active project config."""

    def __init__(self, app):
        self.app = app

    def build(self):
        self._build_layout()
        current_type = self.app.project_manager.get_project_type()
        current_length = self.app.project_manager.get_project_length()
        enabled_tools = self.app.project_manager.get_enabled_tools()

        self._build_tabs(enabled_tools)
        self._setup_sidebar(enabled_tools, current_type)
        self._update_project_badge(current_type, current_length)

        self.app.apply_theme()
        self.app.refresh_all()

    def _build_layout(self):
        app = self.app
        app.main_paned = ttk.PanedWindow(app.root, orient=tk.HORIZONTAL)
        app.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        app.sidebar = SidebarPanel(
            app.main_paned,
            app.theme_manager,
            app._on_sidebar_select,
            app.config_manager,
        )
        app.main_paned.add(app.sidebar, weight=0)

        app.content_area = ttk.Frame(app.main_paned)
        app.main_paned.add(app.content_area, weight=1)

        app.notebook = ttk.Notebook(app.content_area)
        app._orig_notebook_style = app.notebook.cget("style") or ""
        app.notebook.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.layout("Hidden.TNotebook.Tab", [])
        app.notebook.configure(style="Hidden.TNotebook")

        app._toolbox_tab = None
        app._last_real_tab = None

    def _build_tabs(self, enabled_tools):
        for tool_key in enabled_tools:
            builder = getattr(self, f"_build_{tool_key}_tab", None)
            if builder:
                builder()

    def _register_tab(self, key: str, frame, text: str):
        self.app.notebook.add(frame, text=text)
        self.app.tabs[key] = frame
        return frame

    def _build_outline_tab(self):
        app = self.app
        app.outline_frame = ttk.Frame(app.notebook)
        self._register_tab("outline", app.outline_frame, "  思维导图/大纲  ")
        app.mindmap_controller = MindMapController(
            app.outline_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
            app.ai_client,
            app.config_manager,
            app.ai_controller,
        )
        app.registry.register(
            "mindmap",
            app.mindmap_controller,
            refresh_groups=[RefreshGroups.OUTLINE],
            capabilities=[Capabilities.AI_MODE],
        )

    def _build_script_tab(self):
        app = self.app
        app.script_frame = ttk.Frame(app.notebook)
        self._register_tab("script", app.script_frame, "  剧本写作  ")
        app.script_controller = ScriptController(
            app.script_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
            app.ai_client,
            app.config_manager,
            on_wiki_click=app.jump_to_wiki_entry,
            ai_controller=app.ai_controller,
            ambiance_player=app.ambiance_player,
        )
        FloatingAssistantManager.set_script_controller(app.script_controller)
        if hasattr(app.script_controller, "script_editor"):
            FloatingAssistantManager.set_editor_widget(app.script_controller.script_editor)
        app.registry.register(
            "script",
            app.script_controller,
            refresh_groups=[RefreshGroups.SCENE, RefreshGroups.CHARACTER],
            capabilities=[Capabilities.AI_MODE],
        )

    def _build_char_events_tab(self):
        app = self.app
        app.char_event_frame = ttk.Frame(app.notebook)
        self._register_tab("char_events", app.char_event_frame, "  人物事件  ")
        app.char_event_table = CharacterEventTable(
            app.char_event_frame,
            app.project_manager,
            app.theme_manager,
            app._execute_command,
        )
        app.char_event_table.pack(fill=tk.BOTH, expand=True)

    def _build_relationship_tab(self):
        app = self.app
        app.relationship_frame = ttk.Frame(app.notebook)
        self._register_tab("relationship", app.relationship_frame, "  人物关系图  ")
        app.relationship_controller = RelationshipController(
            app.relationship_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
            app.config_manager,
            on_jump_to_scene=app.jump_to_scene_by_index,
            on_jump_to_outline=app.jump_to_outline_node,
        )
        app.registry.register(
            "relationship",
            app.relationship_controller,
            refresh_groups=[RefreshGroups.CHARACTER, RefreshGroups.RELATIONSHIP],
        )

    def _build_evidence_board_tab(self):
        app = self.app
        app.evidence_frame = ttk.Frame(app.notebook)
        self._register_tab("evidence_board", app.evidence_frame, "  线索墙 (悬疑)  ")
        app.evidence_board = EvidenceBoardContainer(
            app.evidence_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
            on_navigate_to_scene=app.jump_to_scene_by_index,
        )
        app.evidence_board.pack(fill=tk.BOTH, expand=True)
        app.registry.register(
            "evidence_board",
            app.evidence_board,
            refresh_groups=[RefreshGroups.EVIDENCE, RefreshGroups.SCENE, RefreshGroups.CHARACTER],
        )

    def _build_timeline_tab(self):
        app = self.app
        app.timeline_frame = ttk.Frame(app.notebook)
        self._register_tab("timeline", app.timeline_frame, "  时间轴  ")
        app.setup_timeline_ui()

    def _build_story_curve_tab(self):
        app = self.app
        app.story_curve_frame = ttk.Frame(app.notebook)
        self._register_tab("story_curve", app.story_curve_frame, "  故事曲线  ")
        app.story_curve_controller = StoryCurveController(
            app.story_curve_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
            app.jump_to_scene_by_index,
            app.ai_controller,
        )
        app.registry.register(
            "story_curve",
            app.story_curve_controller,
            refresh_groups=[RefreshGroups.SCENE],
            capabilities=[Capabilities.AI_MODE],
        )

    def _build_swimlanes_tab(self):
        app = self.app
        app.swimlane_frame = ttk.Frame(app.notebook)
        self._register_tab("swimlanes", app.swimlane_frame, "  故事泳道  ")
        app.swimlane_view = SwimlaneView(app.swimlane_frame, app.project_manager, app.theme_manager)
        app.swimlane_view.pack_controls()

    def _build_dual_timeline_tab(self):
        app = self.app
        app.dual_timeline_frame = ttk.Frame(app.notebook)
        self._register_tab("dual_timeline", app.dual_timeline_frame, "  表里双轨图  ")
        app.dual_timeline_controller = DualTimelineController(
            app.dual_timeline_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
        )
        app.dual_timeline_controller.pack(fill=tk.BOTH, expand=True)
        app.registry.register(
            "dual_timeline",
            app.dual_timeline_controller,
            refresh_groups=[RefreshGroups.TIMELINE],
        )

    def _build_kanban_tab(self):
        app = self.app
        app.kanban_frame = ttk.Frame(app.notebook)
        self._register_tab("kanban", app.kanban_frame, "  场次看板  ")
        app.setup_kanban_ui()

    def _build_calendar_tab(self):
        app = self.app
        app.calendar_frame = ttk.Frame(app.notebook)
        self._register_tab("calendar", app.calendar_frame, "  故事日历  ")
        app.setup_calendar_ui()

    def _build_wiki_tab(self):
        app = self.app
        app.wiki_frame = ttk.Frame(app.notebook)
        self._register_tab("wiki", app.wiki_frame, "  世界观百科  ")
        app.setup_wiki_ui()

    def _build_research_tab(self):
        app = self.app
        app.research_frame = ttk.Frame(app.notebook)
        self._register_tab("research", app.research_frame, "  资料搜集  ")
        app.research_panel = ResearchPanel(app.research_frame, app.project_manager, app.theme_manager)
        app.research_panel.pack(fill=tk.BOTH, expand=True)
        app.research_controller = ResearchController(
            app.research_panel,
            app.project_manager,
            app._execute_command,
        )
        app.registry.register("research", app.research_controller, refresh_groups=[RefreshGroups.ALL])

    def _build_reverse_engineering_tab(self):
        app = self.app
        app.reverse_engineering_frame = ttk.Frame(app.notebook)
        self._register_tab("reverse_engineering", app.reverse_engineering_frame, "  反推导学习  ")
        app.reverse_engineering_view = ReverseEngineeringView(
            app.reverse_engineering_frame,
            app.project_manager,
            app.ai_client,
            app.theme_manager,
            app.config_manager,
            app._execute_command,
            on_navigate=app.navigate_to_module,
        )
        app.reverse_engineering_view.pack(fill=tk.BOTH, expand=True)

    def _build_analytics_tab(self):
        app = self.app
        app.analytics_frame = ttk.Frame(app.notebook)
        self._register_tab("analytics", app.analytics_frame, "  数据统计  ")
        app.analytics_controller = AnalyticsController(
            app.analytics_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
        )
        app.registry.register(
            "analytics",
            app.analytics_controller,
            refresh_groups=[RefreshGroups.ANALYTICS, RefreshGroups.OUTLINE],
        )

    def _build_heartbeat_tab(self):
        app = self.app
        app.heartbeat_frame = ttk.Frame(app.notebook)
        self._register_tab("heartbeat", app.heartbeat_frame, "  💗 心动追踪  ")
        app.heartbeat_controller = HeartbeatTrackerController(
            app.heartbeat_frame,
            app.project_manager,
            app._execute_command,
            app.jump_to_scene_by_index,
        )
        app.registry.register("heartbeat", app.heartbeat_controller, refresh_groups=[RefreshGroups.CHARACTER])

    def _build_alibi_tab(self):
        app = self.app
        app.alibi_frame = ttk.Frame(app.notebook)
        self._register_tab("alibi", app.alibi_frame, "  🕵️ 不在场证明  ")
        app.alibi_controller = AlibiTimelineController(app.alibi_frame, app.project_manager)
        app.registry.register("alibi", app.alibi_controller, refresh_groups=[RefreshGroups.TIMELINE])

    def _build_iceberg_tab(self):
        app = self.app
        app.iceberg_frame = ttk.Frame(app.notebook)
        self._register_tab("iceberg", app.iceberg_frame, "  🏔️ 世界冰山  ")
        app.iceberg_controller = WorldIcebergController(
            app.iceberg_frame,
            app.project_manager,
            app._execute_command,
        )
        app.registry.register("iceberg", app.iceberg_controller, refresh_groups=[RefreshGroups.WIKI])

    def _build_faction_tab(self):
        app = self.app
        app.faction_frame = ttk.Frame(app.notebook)
        self._register_tab("faction", app.faction_frame, "  ⚔️ 势力矩阵  ")
        app.faction_controller = FactionMatrixController(
            app.faction_frame,
            app.project_manager,
            app._execute_command,
        )
        app.registry.register("faction", app.faction_controller, refresh_groups=[RefreshGroups.RELATIONSHIP])

    def _build_variable_tab(self):
        app = self.app
        app.variable_frame = ttk.Frame(app.notebook)
        self._register_tab("variable", app.variable_frame, "  🔢 变量管理  ")
        app.variable_controller = VariableController(
            app.variable_frame,
            app.project_manager,
            app._execute_command,
        )
        app.registry.register("variable", app.variable_controller, refresh_groups=[RefreshGroups.ALL])

    def _build_flowchart_tab(self):
        app = self.app
        app.flowchart_frame = ttk.Frame(app.notebook)
        self._register_tab("flowchart", app.flowchart_frame, "  🕸️ 剧情流向  ")
        app.flowchart_controller = FlowchartController(
            app.flowchart_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
            on_jump_to_scene=app.jump_to_scene_by_index,
        )
        app.registry.register(
            "flowchart",
            app.flowchart_controller,
            refresh_groups=[RefreshGroups.OUTLINE, RefreshGroups.SCENE],
        )

    def _build_ideas_tab(self):
        app = self.app
        app.idea_frame = ttk.Frame(app.notebook)
        self._register_tab("ideas", app.idea_frame, "  灵感箱  ")
        app.idea_panel = IdeaPanel(app.idea_frame, app.project_manager, app.theme_manager)
        app.idea_panel.pack(fill=tk.BOTH, expand=True)
        app.idea_controller = IdeaController(app.idea_panel, app.project_manager, app.theme_manager)
        app.registry.register("idea", app.idea_controller, refresh_groups=[RefreshGroups.ALL])

    def _build_training_tab(self):
        app = self.app
        app.training_frame = ttk.Frame(app.notebook)
        self._register_tab("training", app.training_frame, "  创意训练  ")
        app.training_panel = TrainingPanel(app.training_frame, theme_manager=app.theme_manager)
        app.training_panel.pack(fill=tk.BOTH, expand=True)
        app.training_controller = TrainingController(
            app.training_panel,
            app.project_manager,
            app.theme_manager,
            app.ai_client,
            app.config_manager,
            app.gamification_manager,
        )
        app.registry.register(
            "training",
            app.training_controller,
            refresh_groups=[RefreshGroups.ALL],
            capabilities=[Capabilities.AI_MODE],
        )

    def _build_chat_tab(self):
        app = self.app
        app.chat_frame = ttk.Frame(app.notebook)
        self._register_tab("chat", app.chat_frame, "  项目对话  ")
        app.chat_controller = ChatController(
            app.chat_frame,
            app.project_manager,
            app._execute_command,
            app.theme_manager,
            app.ai_client,
            app.config_manager,
            app.ai_controller,
        )
        app.registry.register(
            "chat",
            app.chat_controller,
            refresh_groups=[RefreshGroups.ALL],
            capabilities=[Capabilities.AI_MODE],
        )

    def _setup_sidebar(self, enabled_tools, current_type):
        app = self.app
        app._toolbox_tab = None
        app.sidebar_controller = SidebarController(
            app.sidebar,
            app.notebook,
            app.config_manager,
            on_item_changed=app._on_sidebar_item_changed,
        )

        for key, frame in app.tabs.items():
            app.sidebar_controller.register_tab(key, frame)

        app.sidebar.update_visibility(enabled_tools)

        default_key = ProjectTypeManager.get_default_tab_key(current_type)
        if default_key in app.tabs:
            app.sidebar.select_item_by_key(default_key)
            app.notebook.select(app.tabs[default_key])
        elif app.tabs:
            first_key = next(iter(app.tabs.keys()))
            app.sidebar.select_item_by_key(first_key)
            app.notebook.select(app.tabs[first_key])

        app._last_real_tab = app.notebook.select() if app.tabs else None

    def _update_project_badge(self, current_type, current_length):
        app = self.app
        type_name = app.project_manager.get_project_type_display_name()
        length_name = ProjectTypeManager.get_length_info(current_length)["name"]
        if hasattr(app, "type_lbl") and app.type_lbl:
            app.type_lbl.config(text=f"[{type_name} | {length_name}]")
