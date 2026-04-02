from tkinter import ttk

from writer_app.core.controller_registry import RefreshGroups


def build_research_tab(builder):
    from writer_app.controllers.research_controller import ResearchController
    from writer_app.ui.research import ResearchPanel

    app = builder.app
    app.research_frame = ttk.Frame(app.notebook)
    builder._register_tab("research", app.research_frame, "  资料搜集  ")
    app.research_panel = ResearchPanel(app.research_frame, app.project_manager, app.theme_manager)
    app.research_panel.pack(fill="both", expand=True)
    app.research_controller = ResearchController(
        app.research_panel,
        app.project_manager,
        app._execute_command,
    )
    app.registry.register("research", app.research_controller, refresh_groups=[RefreshGroups.ALL])


def build_reverse_engineering_tab(builder):
    from writer_app.ui.reverse_engineering import ReverseEngineeringView

    app = builder.app
    app.reverse_engineering_frame = ttk.Frame(app.notebook)
    builder._register_tab("reverse_engineering", app.reverse_engineering_frame, "  反推导学习  ")
    app.reverse_engineering_view = ReverseEngineeringView(
        app.reverse_engineering_frame,
        app.project_manager,
        app.ai_client,
        app.theme_manager,
        app.config_manager,
        app._execute_command,
        on_navigate=app.navigate_to_module,
    )
    app.reverse_engineering_view.pack(fill="both", expand=True)


def build_analytics_tab(builder):
    from writer_app.controllers.analytics_controller import AnalyticsController

    app = builder.app
    app.analytics_frame = ttk.Frame(app.notebook)
    builder._register_tab("analytics", app.analytics_frame, "  数据统计  ")
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


def build_heartbeat_tab(builder):
    from writer_app.ui.heartbeat_tracker import HeartbeatTrackerController

    app = builder.app
    app.heartbeat_frame = ttk.Frame(app.notebook)
    builder._register_tab("heartbeat", app.heartbeat_frame, "  💗 心动追踪  ")
    app.heartbeat_controller = HeartbeatTrackerController(
        app.heartbeat_frame,
        app.project_manager,
        app._execute_command,
        app.jump_to_scene_by_index,
    )
    app.registry.register("heartbeat", app.heartbeat_controller, refresh_groups=[RefreshGroups.CHARACTER])


def build_alibi_tab(builder):
    from writer_app.ui.alibi_timeline import AlibiTimelineController

    app = builder.app
    app.alibi_frame = ttk.Frame(app.notebook)
    builder._register_tab("alibi", app.alibi_frame, "  🕵️ 不在场证明  ")
    app.alibi_controller = AlibiTimelineController(app.alibi_frame, app.project_manager)
    app.registry.register("alibi", app.alibi_controller, refresh_groups=[RefreshGroups.TIMELINE])


TAB_BUILDERS = {
    "research": build_research_tab,
    "reverse_engineering": build_reverse_engineering_tab,
    "analytics": build_analytics_tab,
    "heartbeat": build_heartbeat_tab,
    "alibi": build_alibi_tab,
}
