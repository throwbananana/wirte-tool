from writer_app.app.builders.analysis_pages import TAB_BUILDERS as ANALYSIS_TAB_BUILDERS
from writer_app.app.builders.scene_pages import TAB_BUILDERS as SCENE_TAB_BUILDERS
from writer_app.app.builders.tool_pages import TAB_BUILDERS as TOOL_TAB_BUILDERS
from writer_app.app.builders.world_pages import TAB_BUILDERS as WORLD_TAB_BUILDERS

TAB_BUILDERS = {
    **SCENE_TAB_BUILDERS,
    **WORLD_TAB_BUILDERS,
    **ANALYSIS_TAB_BUILDERS,
    **TOOL_TAB_BUILDERS,
}

__all__ = ["TAB_BUILDERS"]
