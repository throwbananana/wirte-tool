import logging
import sys
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None
    messagebox = None


def _resolve_data_dir():
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir / "writer_data"
    if candidate.exists():
        return candidate
    try:
        from writer_app.core.config import ConfigManager
        config_dir = ConfigManager().config_dir
        fallback = config_dir / "writer_data"
        if fallback.exists():
            return fallback
    except Exception:
        pass
    return candidate


def _setup_logging(data_dir: Path) -> Path:
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "assistant_event_editor.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        filename=str(log_path),
        filemode="a",
    )
    return log_path


def _show_error(title: str, message: str) -> None:
    if messagebox and tk:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    else:
        print(f"{title}: {message}")


def main() -> int:
    data_dir = _resolve_data_dir()
    log_path = _setup_logging(data_dir)

    try:
        from writer_app.ui.floating_assistant.event_config_editor import run_editor
    except ImportError as exc:
        msg = f"无法导入事件编辑器模块。\n详情: {exc}\n日志: {log_path}"
        _show_error("启动失败", msg)
        logging.exception("Import failed")
        return 1

    try:
        run_editor()
        return 0
    except Exception as exc:
        msg = f"事件编辑器启动失败。\n详情: {exc}\n日志: {log_path}"
        _show_error("启动失败", msg)
        logging.exception("Run failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
