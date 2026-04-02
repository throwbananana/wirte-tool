from tkinter import ttk

from writer_app.core.controller_registry import Capabilities, RefreshGroups


def build_wiki_tab(builder):
    from writer_app.controllers.wiki_controller import WikiController

    app = builder.app
    app.wiki_frame = ttk.Frame(app.notebook)
    builder._register_tab("wiki", app.wiki_frame, "  世界观百科  ")
    app.wiki_controller = WikiController(
        app.wiki_frame,
        app.project_manager,
        app._execute_command,
        app.theme_manager,
        app.ai_client,
        app.config_manager,
        on_jump_to_scene=app.jump_to_scene_by_index,
    )
    app.registry.register(
        "wiki",
        app.wiki_controller,
        refresh_groups=[RefreshGroups.WIKI],
        capabilities=[Capabilities.AI_MODE],
    )


def build_iceberg_tab(builder):
    from writer_app.ui.world_iceberg import WorldIcebergController

    app = builder.app
    app.iceberg_frame = ttk.Frame(app.notebook)
    builder._register_tab("iceberg", app.iceberg_frame, "  🏔️ 世界冰山  ")
    app.iceberg_controller = WorldIcebergController(
        app.iceberg_frame,
        app.project_manager,
        app._execute_command,
    )
    app.registry.register("iceberg", app.iceberg_controller, refresh_groups=[RefreshGroups.WIKI])


def build_faction_tab(builder):
    from writer_app.ui.faction_matrix import FactionMatrixController

    app = builder.app
    app.faction_frame = ttk.Frame(app.notebook)
    builder._register_tab("faction", app.faction_frame, "  ⚔️ 势力矩阵  ")
    app.faction_controller = FactionMatrixController(
        app.faction_frame,
        app.project_manager,
        app._execute_command,
    )
    app.registry.register("faction", app.faction_controller, refresh_groups=[RefreshGroups.RELATIONSHIP])


def build_variable_tab(builder):
    from writer_app.controllers.variable_controller import VariableController

    app = builder.app
    app.variable_frame = ttk.Frame(app.notebook)
    builder._register_tab("variable", app.variable_frame, "  🔢 变量管理  ")
    app.variable_controller = VariableController(
        app.variable_frame,
        app.project_manager,
        app._execute_command,
    )
    app.registry.register("variable", app.variable_controller, refresh_groups=[RefreshGroups.ALL])


TAB_BUILDERS = {
    "wiki": build_wiki_tab,
    "iceberg": build_iceberg_tab,
    "faction": build_faction_tab,
    "variable": build_variable_tab,
}
