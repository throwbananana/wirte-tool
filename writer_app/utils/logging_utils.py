import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(data_dir: Path, level=logging.INFO) -> Path:
    """
    Configure a rotating file handler for the app and return the log file path.
    This is idempotent: repeated calls will not add duplicate handlers.
    """
    logs_dir = Path(data_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "writer_tool.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate file handlers when running multiple dialogs/tests
    existing_files = {
        getattr(h, "baseFilename", None) for h in root_logger.handlers
        if isinstance(h, RotatingFileHandler)
    }
    if str(log_file) not in existing_files:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        root_logger.addHandler(file_handler)

    # Ensure we at least log to stderr for visibility when running from CLI
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(logging.Formatter(
            "%(levelname)s %(name)s: %(message)s"
        ))
        root_logger.addHandler(stream_handler)

    return log_file
