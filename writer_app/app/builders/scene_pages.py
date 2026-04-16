from tkinter import ttk

from writer_app.core.controller_registry import Capabilities, RefreshGroups


def build_outline_tab(builder):
    from writer_app.controllers.mindmap_controller import MindMapController

    app = builder.app
    app.outline_frame = ttk.Frame(app.notebook)
    builder._register_tab("outline", app.outline_frame, "  思维导图/大纲  ")
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


def build_script_tab(builder):
    from writer_app.controllers.script_controller import ScriptController
    from writer_app.ui.floating_assistant import FloatingAssistantManager

    app = builder.app
    app.script_frame = ttk.Frame(app.notebook)
    builder._register_tab("script", app.script_frame, "  剧本写作  ")
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


def build_char_events_tab(builder):
    from writer_app.ui.character_event_table import CharacterEventTable

    app = builder.app
    app.char_event_frame = ttk.Frame(app.notebook)
    builder._register_tab("char_events", app.char_event_frame, "  人物事件  ")
    app.char_event_table = CharacterEventTable(
        app.char_event_frame,
        app.project_manager,
        app.theme_manager,
        app._execute_command,
    )
    app.char_event_table.pack(fill="both", expand=True)


def build_relationship_tab(builder):
    from writer_app.controllers.relationship_controller import RelationshipController

    app = builder.app
    app.relationship_frame = ttk.Frame(app.notebook)
    builder._register_tab("relationship", app.relationship_frame, "  人物关系图  ")
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


def build_evidence_board_tab(builder):
    from writer_app.ui.evidence_board import EvidenceBoardContainer

    app = builder.app
    app.evidence_frame = ttk.Frame(app.notebook)
    builder._register_tab("evidence_board", app.evidence_frame, "  线索墙 (悬疑)  ")
    app.evidence_board = EvidenceBoardContainer(
        app.evidence_frame,
        app.project_manager,
        app._execute_command,
        app.theme_manager,
        on_navigate_to_scene=app.jump_to_scene_by_index,
    )
    app.evidence_board.pack(fill="both", expand=True)
    app.registry.register(
        "evidence_board",
        app.evidence_board,
        refresh_groups=[RefreshGroups.EVIDENCE, RefreshGroups.SCENE, RefreshGroups.CHARACTER],
    )


def build_timeline_tab(builder):
    from writer_app.controllers.timeline_controller import TimelineController

    app = builder.app
    app.timeline_frame = ttk.Frame(app.notebook)
    builder._register_tab("timeline", app.timeline_frame, "  时间轴  ")
    app.timeline_controller = TimelineController(
        app.timeline_frame,
        app.project_manager,
        app._execute_command,
        app.theme_manager,
    )
    app.registry.register(
        "timeline",
        app.timeline_controller,
        refresh_groups=[RefreshGroups.TIMELINE, RefreshGroups.SCENE],
    )


def build_story_curve_tab(builder):
    from writer_app.ui.story_curve import StoryCurveController

    app = builder.app
    app.story_curve_frame = ttk.Frame(app.notebook)
    builder._register_tab("story_curve", app.story_curve_frame, "  故事曲线  ")
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


def build_tone_outline_tab(builder):
    from writer_app.ui.tone_outline import ToneOutlineController

    app = builder.app
    app.tone_outline_frame = ttk.Frame(app.notebook)
    builder._register_tab("tone_outline", app.tone_outline_frame, "  基调大纲  ")
    app.tone_outline_controller = ToneOutlineController(
        app.tone_outline_frame,
        app.project_manager,
        app._execute_command,
        app.theme_manager,
    )
    app.registry.register(
        "tone_outline",
        app.tone_outline_controller,
        refresh_groups=[RefreshGroups.SCENE, RefreshGroups.CHARACTER],
    )


def build_swimlanes_tab(builder):
    from writer_app.ui.swimlanes import SwimlaneView

    app = builder.app
    app.swimlane_frame = ttk.Frame(app.notebook)
    builder._register_tab("swimlanes", app.swimlane_frame, "  故事泳道  ")
    app.swimlane_view = SwimlaneView(app.swimlane_frame, app.project_manager, app.theme_manager)
    app.swimlane_view.pack_controls()


def build_dual_timeline_tab(builder):
    from writer_app.controllers.dual_timeline_controller import DualTimelineController

    app = builder.app
    app.dual_timeline_frame = ttk.Frame(app.notebook)
    builder._register_tab("dual_timeline", app.dual_timeline_frame, "  表里双轨图  ")
    app.dual_timeline_controller = DualTimelineController(
        app.dual_timeline_frame,
        app.project_manager,
        app._execute_command,
        app.theme_manager,
    )
    app.dual_timeline_controller.pack(fill="both", expand=True)
    app.registry.register(
        "dual_timeline",
        app.dual_timeline_controller,
        refresh_groups=[RefreshGroups.TIMELINE],
    )


def build_kanban_tab(builder):
    from writer_app.controllers.kanban_controller import KanbanController

    app = builder.app
    app.kanban_frame = ttk.Frame(app.notebook)
    builder._register_tab("kanban", app.kanban_frame, "  场次看板  ")
    app.kanban_controller = KanbanController(
        app.kanban_frame,
        app.project_manager,
        app._execute_command,
        app.theme_manager,
    )
    app.registry.register(
        "kanban",
        app.kanban_controller,
        refresh_groups=[RefreshGroups.SCENE, RefreshGroups.KANBAN],
    )


def build_calendar_tab(builder):
    from writer_app.controllers.calendar_controller import CalendarController

    app = builder.app
    app.calendar_frame = ttk.Frame(app.notebook)
    builder._register_tab("calendar", app.calendar_frame, "  故事日历  ")
    app.calendar_controller = CalendarController(
        app.calendar_frame,
        app.project_manager,
        app._execute_command,
        app.theme_manager,
        app.jump_to_scene_by_index,
    )
    app.registry.register(
        "calendar",
        app.calendar_controller,
        refresh_groups=[RefreshGroups.SCENE],
    )


def build_flowchart_tab(builder):
    from writer_app.controllers.flowchart_controller import FlowchartController

    app = builder.app
    app.flowchart_frame = ttk.Frame(app.notebook)
    builder._register_tab("flowchart", app.flowchart_frame, "  🕸️ 剧情流向  ")
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


TAB_BUILDERS = {
    "outline": build_outline_tab,
    "script": build_script_tab,
    "char_events": build_char_events_tab,
    "relationship": build_relationship_tab,
    "evidence_board": build_evidence_board_tab,
    "timeline": build_timeline_tab,
    "story_curve": build_story_curve_tab,
    "tone_outline": build_tone_outline_tab,
    "swimlanes": build_swimlanes_tab,
    "dual_timeline": build_dual_timeline_tab,
    "kanban": build_kanban_tab,
    "calendar": build_calendar_tab,
    "flowchart": build_flowchart_tab,
}
