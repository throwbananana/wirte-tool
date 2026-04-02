import logging
from pathlib import Path

from writer_app.core.audio import AmbiancePlayer, TypewriterSoundPlayer
from writer_app.core.backup import BackupManager
from writer_app.core.config import ConfigManager
from writer_app.core.gamification import GamificationManager
from writer_app.core.history_manager import CommandHistory
from writer_app.core.icon_manager import IconManager
from writer_app.core.models import ProjectManager
from writer_app.core.module_sync import init_module_sync
from writer_app.core.theme import ThemeManager
from writer_app.core.guide_progress import GuideProgress
from writer_app.core.font_manager import get_font_manager
from writer_app.ui.app_theme import AppThemeController
from writer_app.utils.ai_client import AIClient
from writer_app.utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)


def bootstrap_core_services(app) -> None:
    """Initialize filesystem, configuration, project, and runtime services."""
    app.data_dir = Path(__file__).resolve().parents[2] / "writer_data"
    app.data_dir.mkdir(exist_ok=True)
    app.log_file_path = setup_logging(app.data_dir)

    try:
        get_font_manager().load_local_fonts()
    except Exception as exc:
        logger.error("Failed to load fonts: %s", exc)

    app.icon_mgr = IconManager()
    app.ambiance_player = AmbiancePlayer(str(app.data_dir))
    app.typewriter_player = TypewriterSoundPlayer(str(app.data_dir))

    app.config_manager = ConfigManager()
    app.theme_manager = ThemeManager(app.config_manager.get("theme", "Light"))
    app.theme_manager.set_custom_colors(app.config_manager.get("custom_theme_colors", {}))
    app.theme_manager.set_background_image(app.config_manager.get("background_image", ""))
    app.theme_manager.set_background_opacity(app.config_manager.get("background_opacity", 1.0))
    app.theme_controller = AppThemeController(app)
    app.theme_manager.add_listener(app._on_theme_changed)
    app.root.geometry(app.config_manager.get("window_geometry", "1400x900"))

    app.project_manager = ProjectManager()
    app.ai_client = AIClient()
    app.history_manager = CommandHistory()
    app.search_dialog = None
    app.messagebox = None
    app.guide_progress = GuideProgress(app.data_dir)

    app.module_sync = init_module_sync(app.project_manager)
    app._last_validation_report = None
    app._last_validation_issue_count = None
    app.module_sync.set_validation_callback(app._run_logic_validation_silent)

    app.gamification_manager = GamificationManager(app.data_dir)
    app.gamification_manager.add_listener(app.on_gamification_update)

    app.backup_manager = BackupManager(app.project_manager)
    app.backup_manager.start()
