from tkinter import ttk

from writer_app.core.controller_registry import Capabilities, RefreshGroups


def build_ideas_tab(builder):
    from writer_app.controllers.idea_controller import IdeaController
    from writer_app.ui.idea_panel import IdeaPanel

    app = builder.app
    app.idea_frame = ttk.Frame(app.notebook)
    builder._register_tab("ideas", app.idea_frame, "  灵感箱  ")
    app.idea_panel = IdeaPanel(app.idea_frame, app.project_manager, app.theme_manager)
    app.idea_panel.pack(fill="both", expand=True)
    app.idea_controller = IdeaController(app.idea_panel, app.project_manager, app.theme_manager)
    app.registry.register("idea", app.idea_controller, refresh_groups=[RefreshGroups.ALL])


def build_training_tab(builder):
    from writer_app.controllers.training_controller import TrainingController
    from writer_app.ui.training_panel import TrainingPanel

    app = builder.app
    app.training_frame = ttk.Frame(app.notebook)
    builder._register_tab("training", app.training_frame, "  创意训练  ")
    app.training_panel = TrainingPanel(app.training_frame, theme_manager=app.theme_manager)
    app.training_panel.pack(fill="both", expand=True)
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


def build_chat_tab(builder):
    from writer_app.controllers.chat_controller import ChatController

    app = builder.app
    app.chat_frame = ttk.Frame(app.notebook)
    builder._register_tab("chat", app.chat_frame, "  项目对话  ")
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


TAB_BUILDERS = {
    "ideas": build_ideas_tab,
    "training": build_training_tab,
    "chat": build_chat_tab,
}
