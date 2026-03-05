"""
Event Logic Analyzer - 事件逻辑分析工具

命令行参数:
  --data-dir  指定 writer_data 目录
  --file      指定要分析的 JSON 文件
  --gui       启动 GUI 分析对话框

示例:
  python analyze_events.py                    # 分析默认文件
  python analyze_events.py --gui              # 打开 GUI 对话框
  python analyze_events.py --file custom.json # 分析指定文件
"""

import argparse
import json
import logging
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None
    messagebox = None


def _resolve_data_dir():
    """Resolve the writer_data directory path."""
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
    """Setup logging to file."""
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "analyze_events.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        filename=str(log_path),
        filemode="a",
    )
    return log_path


def _show_info(title: str, message: str) -> None:
    """Show info message (GUI or console)."""
    if messagebox and tk:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(title, message)
        root.destroy()
    else:
        print(f"{title}: {message}")


def _show_error(title: str, message: str) -> None:
    """Show error message (GUI or console)."""
    if messagebox and tk:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    else:
        print(f"[ERROR] {title}: {message}")


def run_gui_mode(events_path: Path) -> int:
    """Launch GUI analysis dialog."""
    if not tk:
        print("错误: GUI 模式需要 tkinter")
        return 1

    if not events_path.exists():
        _show_error("错误", f"未找到事件文件: {events_path}")
        return 1

    try:
        with open(events_path, "r", encoding="utf-8") as f:
            events = json.load(f)
    except Exception as exc:
        _show_error("错误", f"无法读取 JSON: {exc}")
        return 1

    # Import the analysis dialog
    try:
        from writer_app.ui.event_analysis_dialog import EventAnalysisDialog
    except ImportError as exc:
        _show_error("导入错误", f"无法导入分析对话框模块: {exc}")
        return 1

    # Create and show dialog
    root = tk.Tk()
    root.title("事件分析工具")
    root.geometry("100x50")  # Small window, dialog will be main UI

    # Hide main window
    root.withdraw()

    # Show analysis dialog
    dialog = EventAnalysisDialog(root, events, title=f"事件分析 - {events_path.name}")
    dialog.protocol("WM_DELETE_WINDOW", lambda: (dialog.destroy(), root.destroy()))

    # Wait for dialog to close
    dialog.wait_window()
    root.destroy()

    return 0


def run_cli_mode(events_path: Path, report_path: Path) -> int:
    """Run analysis in CLI mode using the new EventAnalyzer."""
    if not events_path.exists():
        _show_error("错误", f"未找到事件文件: {events_path}")
        return 1

    try:
        with open(events_path, "r", encoding="utf-8") as f:
            events = json.load(f)
    except Exception as exc:
        _show_error("错误", f"无法读取 JSON: {exc}")
        logging.exception("JSON load failed")
        return 1

    # Use the new EventAnalyzer
    try:
        from writer_app.core.event_analyzer import EventAnalyzer
        analyzer = EventAnalyzer(events)
        report = analyzer.analyze()
        report_text = report.to_text()
    except ImportError:
        # Fallback to legacy analysis if new analyzer not available
        report_text = _legacy_analyze(events)

    # Print to console
    print(report_text)

    # Write to file
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\n报告已保存到: {report_path}")
    except Exception:
        logging.exception("Failed to write report file")

    _show_info("分析完成", f"事件分析完成。\n报告: {report_path}")
    return 0


def _legacy_analyze(events: list) -> str:
    """Legacy analysis for backward compatibility."""
    lines = []
    lines.append(f"Total Events: {len(events)}")
    lines.append("")

    ids = {e.get("id") for e in events}

    single_count = 0
    conditional_chain_count = 0
    immediate_chain_count = 0
    repeatable_count = 0
    warning_count = 0

    lines.append("--- Event Logic Analysis ---")

    for e in events:
        e_id = e.get("id", "UNKNOWN")
        title = e.get("title", "Untitled")
        is_repeatable = e.get("repeatable", True)
        prereqs = e.get("prerequisites", [])

        has_immediate_next = False
        for c in e.get("choices", []):
            if c.get("next_event_id"):
                has_immediate_next = True
                next_id = c.get("next_event_id")
                if next_id not in ids:
                    lines.append(f"[WARNING] Event '{e_id}' choice links to missing event '{next_id}'")
                    warning_count += 1

        e_type = e.get("type", "single")

        if prereqs:
            e_type = "chain_conditional"
            conditional_chain_count += 1
            for p in prereqs:
                if p not in ids:
                    lines.append(f"[WARNING] Event '{e_id}' requires missing prerequisite '{p}'")
                    warning_count += 1
        elif has_immediate_next:
            e_type = "chain_immediate"
            immediate_chain_count += 1
        else:
            single_count += 1

        if is_repeatable:
            repeatable_count += 1

        lines.append(
            f"ID: {e_id:<20} | Title: {title:<15} | Type: {e_type:<18} | Repeat: {str(is_repeatable):<5}"
        )

    lines.append("")
    lines.append("--- Summary ---")
    lines.append(f"Single Events:              {single_count}")
    lines.append(f"Conditional Chain Events:   {conditional_chain_count}")
    lines.append(f"Immediate Chain Events:     {immediate_chain_count}")
    lines.append(f"Repeatable Events:          {repeatable_count}")
    lines.append(f"Single-use Events:          {len(events) - repeatable_count}")
    lines.append(f"Warnings:                   {warning_count}")

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="事件逻辑分析工具 - 分析事件文件的逻辑完整性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python analyze_events.py                    # 分析默认文件 (school_events.json)
  python analyze_events.py --gui              # 打开 GUI 分析对话框
  python analyze_events.py --file events.json # 分析指定文件
  python analyze_events.py --data-dir /path   # 指定数据目录
        """,
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="",
        help="Path to writer_data directory",
    )
    parser.add_argument(
        "--file",
        type=str,
        default="",
        help="Event JSON file name or absolute path",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch GUI analysis dialog",
    )
    args = parser.parse_args()

    # Resolve paths
    data_dir = Path(args.data_dir).resolve() if args.data_dir else _resolve_data_dir()
    log_path = _setup_logging(data_dir)

    if args.file:
        events_path = Path(args.file)
        if not events_path.is_absolute():
            events_path = (data_dir / args.file).resolve()
    else:
        events_path = data_dir / "school_events.json"

    logging.info("Analyze events: %s (log: %s, gui: %s)", events_path, log_path, args.gui)

    # Run in appropriate mode
    if args.gui:
        return run_gui_mode(events_path)
    else:
        report_path = data_dir / "logs" / "analyze_events_report.txt"
        return run_cli_mode(events_path, report_path)


if __name__ == "__main__":
    raise SystemExit(main())
