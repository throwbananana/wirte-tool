"""
Event Analysis Dialog - 事件分析 GUI 对话框

功能:
- 显示分析摘要统计
- 列出发现的问题 (Treeview)
- 双击问题跳转到对应事件
- 导出分析报告
- 简易事件流程图视图
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional

from writer_app.core.event_analyzer import (
    AnalysisIssue,
    AnalysisIssueType,
    AnalysisReport,
    EventAnalyzer,
    IssueSeverity,
)


class EventAnalysisDialog(tk.Toplevel):
    """GUI dialog showing event analysis results."""

    SEVERITY_ICONS = {
        IssueSeverity.ERROR: "X",
        IssueSeverity.WARNING: "!",
        IssueSeverity.INFO: "i",
    }

    SEVERITY_COLORS = {
        IssueSeverity.ERROR: "#D32F2F",
        IssueSeverity.WARNING: "#F57C00",
        IssueSeverity.INFO: "#1976D2",
    }

    ISSUE_TYPE_NAMES = {
        AnalysisIssueType.MISSING_REFERENCE: "引用缺失",
        AnalysisIssueType.CYCLE_DETECTED: "循环依赖",
        AnalysisIssueType.DEAD_END: "死路径",
        AnalysisIssueType.ORPHAN_EVENT: "孤立事件",
        AnalysisIssueType.INVALID_EFFECT: "无效效果",
        AnalysisIssueType.DUPLICATE_ID: "重复ID",
        AnalysisIssueType.MISSING_REQUIRED_FIELD: "缺少字段",
    }

    def __init__(
        self,
        parent,
        events: List[Dict],
        on_navigate: Optional[Callable[[str], None]] = None,
        title: str = "事件逻辑分析",
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("900x700")
        self.minsize(700, 500)

        self.events = events
        self.on_navigate = on_navigate

        # Run analysis
        analyzer = EventAnalyzer(events)
        self.report = analyzer.analyze()

        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        """Setup the dialog UI."""
        # Summary panel at top
        summary_frame = ttk.LabelFrame(self, text="分析摘要", padding=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        self._setup_summary(summary_frame)

        # Main content with notebook
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tab 1: Issues list
        issues_frame = ttk.Frame(notebook, padding=5)
        notebook.add(issues_frame, text=f"发现的问题 ({len(self.report.issues)})")
        self._setup_issues_panel(issues_frame)

        # Tab 2: Event flow graph
        graph_frame = ttk.Frame(notebook, padding=5)
        notebook.add(graph_frame, text="事件流程图")
        self._setup_graph_panel(graph_frame)

        # Tab 3: Full report text
        report_frame = ttk.Frame(notebook, padding=5)
        notebook.add(report_frame, text="完整报告")
        self._setup_report_panel(report_frame)

        # Bottom buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="导出报告", command=self._export_report, width=12).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="刷新分析", command=self._refresh_analysis, width=12).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="关闭", command=self.destroy, width=10).pack(
            side=tk.RIGHT, padx=5
        )

    def _setup_summary(self, parent):
        """Setup the summary statistics panel."""
        stats = [
            ("总事件数", self.report.total_events, "#333333"),
            ("单独事件", self.report.single_count, "#666666"),
            ("条件链式", self.report.conditional_chain_count, "#4A90D9"),
            ("即时链式", self.report.immediate_chain_count, "#4A90D9"),
            ("可重复", self.report.repeatable_count, "#2E7D32"),
            ("一次性", self.report.total_events - self.report.repeatable_count, "#666666"),
        ]

        # First row of stats
        row1 = ttk.Frame(parent)
        row1.pack(fill=tk.X)

        for i, (label, value, color) in enumerate(stats):
            stat_frame = ttk.Frame(row1)
            stat_frame.pack(side=tk.LEFT, padx=15, pady=5)

            ttk.Label(stat_frame, text=label, foreground="#666666").pack()
            value_label = ttk.Label(
                stat_frame,
                text=str(value),
                font=("Segoe UI", 16, "bold"),
                foreground=color,
            )
            value_label.pack()

        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Issue summary row
        row2 = ttk.Frame(parent)
        row2.pack(fill=tk.X)

        error_count = self.report.error_count
        warning_count = self.report.warning_count
        info_count = len(self.report.issues) - error_count - warning_count

        issue_stats = [
            ("错误", error_count, self.SEVERITY_COLORS[IssueSeverity.ERROR]),
            ("警告", warning_count, self.SEVERITY_COLORS[IssueSeverity.WARNING]),
            ("信息", info_count, self.SEVERITY_COLORS[IssueSeverity.INFO]),
        ]

        for label, count, color in issue_stats:
            stat_frame = ttk.Frame(row2)
            stat_frame.pack(side=tk.LEFT, padx=15, pady=5)

            ttk.Label(stat_frame, text=label).pack(side=tk.LEFT, padx=2)
            count_label = ttk.Label(
                stat_frame,
                text=str(count),
                font=("Segoe UI", 12, "bold"),
                foreground=color if count > 0 else "#999999",
            )
            count_label.pack(side=tk.LEFT)

        # Overall status
        if self.report.has_errors:
            status_text = "发现严重问题，建议修复后继续"
            status_color = self.SEVERITY_COLORS[IssueSeverity.ERROR]
        elif warning_count > 0:
            status_text = "发现潜在问题，建议检查"
            status_color = self.SEVERITY_COLORS[IssueSeverity.WARNING]
        else:
            status_text = "事件逻辑正常"
            status_color = "#2E7D32"

        status_label = ttk.Label(
            row2,
            text=status_text,
            foreground=status_color,
            font=("Segoe UI", 10),
        )
        status_label.pack(side=tk.RIGHT, padx=15)

    def _setup_issues_panel(self, parent):
        """Setup the issues list panel."""
        if not self.report.issues:
            # Empty state
            empty_label = ttk.Label(
                parent,
                text="未发现问题",
                font=("Segoe UI", 12),
                foreground="#2E7D32",
            )
            empty_label.pack(expand=True)
            return

        # Treeview for issues
        columns = ("severity", "type", "event_id", "message")

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.issues_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.issues_tree.heading("severity", text="严重度")
        self.issues_tree.heading("type", text="类型")
        self.issues_tree.heading("event_id", text="事件ID")
        self.issues_tree.heading("message", text="描述")

        self.issues_tree.column("severity", width=70, minwidth=60)
        self.issues_tree.column("type", width=100, minwidth=80)
        self.issues_tree.column("event_id", width=120, minwidth=100)
        self.issues_tree.column("message", width=400, minwidth=200)

        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.issues_tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.issues_tree.xview)
        self.issues_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.issues_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Populate issues
        for issue in self.report.issues:
            icon = self.SEVERITY_ICONS.get(issue.severity, "?")
            severity_text = f"[{icon}] {issue.severity.value}"
            type_name = self.ISSUE_TYPE_NAMES.get(issue.issue_type, str(issue.issue_type))

            item_id = self.issues_tree.insert(
                "",
                tk.END,
                values=(severity_text, type_name, issue.event_id, issue.message),
                tags=(issue.severity.value,),
            )

        # Configure tag colors
        self.issues_tree.tag_configure("error", foreground=self.SEVERITY_COLORS[IssueSeverity.ERROR])
        self.issues_tree.tag_configure("warning", foreground=self.SEVERITY_COLORS[IssueSeverity.WARNING])
        self.issues_tree.tag_configure("info", foreground=self.SEVERITY_COLORS[IssueSeverity.INFO])

        # Double-click to navigate
        self.issues_tree.bind("<Double-1>", self._on_issue_double_click)

        # Hint label
        hint_label = ttk.Label(
            parent,
            text="双击问题行可跳转到对应事件" if self.on_navigate else "",
            foreground="#888888",
        )
        hint_label.pack(anchor=tk.W, pady=(5, 0))

    def _setup_graph_panel(self, parent):
        """Setup the event flow graph panel."""
        # Simple text-based graph for now
        # A full graphical implementation would use Canvas

        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.graph_text = tk.Text(
            text_frame,
            wrap=tk.NONE,
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )

        v_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.graph_text.yview)
        h_scroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.graph_text.xview)
        self.graph_text.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.graph_text.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        # Generate graph text
        lines = []
        lines.append("事件流程图 (简化视图)")
        lines.append("=" * 50)
        lines.append("")

        # Group events by type
        chain_events = []
        single_events = []

        for event_id, targets in self.report.event_graph.items():
            if targets:
                chain_events.append((event_id, targets))
            else:
                single_events.append(event_id)

        if chain_events:
            lines.append("链式事件:")
            lines.append("-" * 30)
            for event_id, targets in chain_events:
                lines.append(f"  {event_id}")
                for target in targets:
                    lines.append(f"    -> {target}")
            lines.append("")

        if single_events:
            lines.append("独立事件:")
            lines.append("-" * 30)
            for event_id in single_events[:20]:  # Limit display
                lines.append(f"  {event_id}")
            if len(single_events) > 20:
                lines.append(f"  ... 还有 {len(single_events) - 20} 个")

        self.graph_text.insert("1.0", "\n".join(lines))
        self.graph_text.configure(state=tk.DISABLED)

    def _setup_report_panel(self, parent):
        """Setup the full report text panel."""
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.report_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            padx=10,
            pady=10,
        )

        v_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=v_scroll.set)

        self.report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Insert report text
        self.report_text.insert("1.0", self.report.to_text())
        self.report_text.configure(state=tk.DISABLED)

    def _on_issue_double_click(self, event):
        """Handle double-click on an issue row."""
        selection = self.issues_tree.selection()
        if not selection:
            return

        item = self.issues_tree.item(selection[0])
        event_id = item["values"][2]  # event_id column

        if self.on_navigate:
            self.on_navigate(event_id)

    def _export_report(self):
        """Export analysis report to file."""
        path = filedialog.asksaveasfilename(
            title="导出分析报告",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("Markdown files", "*.md"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.report.to_text())
            messagebox.showinfo("导出成功", f"报告已导出到:\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _refresh_analysis(self):
        """Refresh the analysis with current events."""
        analyzer = EventAnalyzer(self.events)
        self.report = analyzer.analyze()

        # Rebuild UI
        for widget in self.winfo_children():
            widget.destroy()
        self._setup_ui()


def show_analysis_dialog(
    parent,
    events: List[Dict],
    on_navigate: Optional[Callable[[str], None]] = None,
) -> EventAnalysisDialog:
    """Convenience function to show the analysis dialog."""
    return EventAnalysisDialog(parent, events, on_navigate)
