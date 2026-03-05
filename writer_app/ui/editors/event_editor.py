"""
Event Editor Panel - 增强版事件编辑器

功能:
- 搜索/过滤事件列表
- Treeview 列表显示
- 标签页详情编辑 (基本信息/选项编辑/触发条件/JSON源码)
- 撤销/重做 (Command 模式)
- 复制/粘贴事件
- 拖拽重排序
- 事件分析
"""

from __future__ import annotations

import json
import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from writer_app.core.commands_event import (
    AddEventCommand,
    BatchEventCommand,
    DeleteEventCommand,
    DuplicateEventCommand,
    MoveEventCommand,
    UpdateEventCommand,
)
from writer_app.core.event_analyzer import EventAnalyzer
from writer_app.core.history_manager import CommandHistory
from writer_app.ui.components.choice_editor import ChoiceEditorPanel
from writer_app.ui.components.json_text_editor import JsonTextEditor

logger = logging.getLogger(__name__)


class EventEditorPanel(ttk.Frame):
    """Enhanced event editor with visual editing, undo/redo, search, and drag reorder."""

    def __init__(
        self,
        parent,
        file_path: Optional[Path] = None,
        events: Optional[List[Dict]] = None,
        on_modified: Optional[Callable[[], None]] = None,
        mode: str = "file",  # "file" or "memory"
    ):
        super().__init__(parent)

        # Mode: "file" = read/write to JSON file, "memory" = work with in-memory events
        self.mode = mode

        # Data
        self.events: List[Dict] = events if events is not None else []
        self.file_path = file_path or (self._get_default_path() if mode == "file" else None)
        self.selected_index: int = -1
        self.clipboard: Optional[Dict] = None
        self.on_modified = on_modified

        # Undo/Redo
        self.command_history = CommandHistory(max_history=50)
        self.command_history.add_listener(self._update_undo_buttons)

        # Search/Filter
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *a: self._on_filter_change())
        self.type_filter_var = tk.StringVar(value="all")

        # Drag state
        self._drag_item: Optional[str] = None
        self._drag_start_index: int = -1

        # Filtered indices mapping (display index -> actual index)
        self._filtered_indices: List[int] = []

        # Load and setup
        if mode == "file" and not events:
            self._load_data()
        self._setup_ui()
        self._refresh_list()

    def _get_default_path(self) -> Path:
        """Get default event file path."""
        return Path(__file__).parent.parent.parent.parent / "writer_data" / "school_events.json"

    def _load_data(self):
        """Load events from file."""
        if self.file_path and self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.events = json.load(f)
                logger.info(f"Loaded {len(self.events)} events from {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to load events: {e}")
                messagebox.showerror("加载失败", f"无法加载事件文件:\n{e}")
                self.events = []
        else:
            self.events = []

    def _save_data(self):
        """Save events to file or notify parent (depending on mode)."""
        if self.mode == "memory":
            # In memory mode, just notify parent and let it handle saving
            self._notify_modified()
            self.status_label.configure(text=f"已更新 {len(self.events)} 个事件")
            return

        # File mode: save to file
        if not self.file_path:
            messagebox.showwarning("保存失败", "未指定保存文件路径")
            return

        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.events, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("保存成功", f"已保存 {len(self.events)} 个事件")
            logger.info(f"Saved {len(self.events)} events to {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to save events: {e}")
            messagebox.showerror("保存失败", f"无法保存事件文件:\n{e}")

    def _setup_ui(self):
        """Setup the main UI layout."""
        # Main paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left panel: List with toolbar
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        self._setup_list_toolbar(left_frame)
        self._setup_event_list(left_frame)

        # Right panel: Detail editor
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=3)

        self._setup_detail_toolbar(right_frame)
        self._setup_detail_notebook(right_frame)

    def _setup_list_toolbar(self, parent):
        """Setup the list toolbar with search and filters."""
        # Search row
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=2)
        search_entry = ttk.Entry(search_frame, textvariable=self.filter_var, width=15)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Clear search button
        ttk.Button(search_frame, text="✕", width=2,
                   command=lambda: self.filter_var.set("")).pack(side=tk.LEFT)

        # Type filter row
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_frame, text="类型:").pack(side=tk.LEFT, padx=2)
        type_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.type_filter_var,
            values=["all", "single", "chain", "repeatable", "one-time"],
            state="readonly",
            width=12,
        )
        type_combo.pack(side=tk.LEFT, padx=2)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._on_filter_change())

        # Count label
        self.count_label = ttk.Label(filter_frame, text="")
        self.count_label.pack(side=tk.RIGHT, padx=5)

        # Action buttons row
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(btn_frame, text="+ 添加", command=self._add_event, width=7).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="复制", command=self._copy_event, width=5).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="粘贴", command=self._paste_event, width=5).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="删除", command=self._delete_event, width=5).pack(side=tk.LEFT, padx=1)

        # File operations row
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=tk.X, pady=(0, 5))

        save_text = "应用" if self.mode == "memory" else "保存"
        ttk.Button(file_frame, text=save_text, command=self._save_data, width=6).pack(side=tk.LEFT, padx=1)

        if self.mode == "file":
            ttk.Button(file_frame, text="重载", command=self._reload_data, width=6).pack(side=tk.LEFT, padx=1)

        ttk.Button(file_frame, text="分析", command=self._show_analysis, width=6).pack(side=tk.LEFT, padx=1)

        if self.mode == "file":
            ttk.Button(file_frame, text="打开...", command=self._open_file, width=6).pack(side=tk.LEFT, padx=1)

    def _setup_event_list(self, parent):
        """Setup the event list with Treeview."""
        # Treeview with columns
        columns = ("id", "title", "type", "weight")

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # Configure columns
        self.tree.heading("id", text="ID", command=lambda: self._sort_by_column("id"))
        self.tree.heading("title", text="标题", command=lambda: self._sort_by_column("title"))
        self.tree.heading("type", text="类型", command=lambda: self._sort_by_column("type"))
        self.tree.heading("weight", text="权重", command=lambda: self._sort_by_column("weight"))

        self.tree.column("id", width=100, minwidth=80)
        self.tree.column("title", width=120, minwidth=80)
        self.tree.column("type", width=60, minwidth=50)
        self.tree.column("weight", width=50, minwidth=40)

        # Scrollbars
        v_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Delete>", lambda e: self._delete_event())
        self.tree.bind("<Control-c>", lambda e: self._copy_event())
        self.tree.bind("<Control-v>", lambda e: self._paste_event())
        self.tree.bind("<Control-z>", lambda e: self._undo())
        self.tree.bind("<Control-y>", lambda e: self._redo())

        # Drag and drop bindings
        self.tree.bind("<ButtonPress-1>", self._on_drag_start)
        self.tree.bind("<B1-Motion>", self._on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_drag_end)

    def _setup_detail_toolbar(self, parent):
        """Setup the detail panel toolbar."""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        # Undo/Redo buttons
        self.undo_btn = ttk.Button(toolbar, text="↶ 撤销", command=self._undo, state=tk.DISABLED, width=8)
        self.undo_btn.pack(side=tk.LEFT, padx=2)

        self.redo_btn = ttk.Button(toolbar, text="↷ 重做", command=self._redo, state=tk.DISABLED, width=8)
        self.redo_btn.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Update button
        self.update_btn = ttk.Button(toolbar, text="更新事件", command=self._update_current, width=10)
        self.update_btn.pack(side=tk.RIGHT, padx=5)

        # Status label
        self.status_label = ttk.Label(toolbar, text="")
        self.status_label.pack(side=tk.RIGHT, padx=10)

    def _setup_detail_notebook(self, parent):
        """Setup the tabbed detail editor."""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Basic Info
        basic_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(basic_frame, text="基本信息")
        self._setup_basic_fields(basic_frame)

        # Tab 2: Choices (Visual Editor)
        choices_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(choices_frame, text="选项编辑")
        self.choice_editor = ChoiceEditorPanel(choices_frame, on_change=self._on_detail_change)
        self.choice_editor.pack(fill=tk.BOTH, expand=True)

        # Tab 3: Conditions & Prerequisites
        conditions_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(conditions_frame, text="触发条件")
        self._setup_conditions_panel(conditions_frame)

        # Tab 4: Raw JSON
        json_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(json_frame, text="JSON源码")
        self._setup_json_editor(json_frame)

    def _setup_basic_fields(self, parent):
        """Setup basic field inputs."""
        # Scrollable frame for many fields
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Field definitions
        fields = [
            ("ID", "id", "entry", None),
            ("标题", "title", "entry", None),
            ("描述", "description", "text", 4),
            ("事件类型", "type", "combo", ["random", "scheduled", "story", "special", "chain"]),
            ("权重", "weight", "spinbox", (0, 100)),
            ("最低好感度", "min_affection", "spinbox", (0, 100)),
            ("可重复", "repeatable", "checkbox", None),
            ("图标", "icon", "entry", None),
            ("背景", "background", "entry", None),
            ("BGM", "bgm", "entry", None),
        ]

        self.field_vars: Dict[str, Any] = {}
        self.field_widgets: Dict[str, Any] = {}

        for row, (label, key, widget_type, config) in enumerate(fields):
            ttk.Label(scrollable_frame, text=f"{label}:").grid(
                row=row, column=0, sticky="ne", padx=5, pady=3
            )

            if widget_type == "entry":
                var = tk.StringVar()
                widget = ttk.Entry(scrollable_frame, textvariable=var, width=40)
                widget.grid(row=row, column=1, sticky="w", padx=5, pady=3)

            elif widget_type == "text":
                var = None
                widget = tk.Text(scrollable_frame, height=config, width=40)
                widget.grid(row=row, column=1, sticky="w", padx=5, pady=3)

            elif widget_type == "spinbox":
                var = tk.IntVar(value=0)
                widget = ttk.Spinbox(
                    scrollable_frame,
                    textvariable=var,
                    from_=config[0],
                    to=config[1],
                    width=10,
                )
                widget.grid(row=row, column=1, sticky="w", padx=5, pady=3)

            elif widget_type == "checkbox":
                var = tk.BooleanVar(value=True)
                widget = ttk.Checkbutton(scrollable_frame, variable=var)
                widget.grid(row=row, column=1, sticky="w", padx=5, pady=3)

            elif widget_type == "combo":
                var = tk.StringVar()
                widget = ttk.Combobox(
                    scrollable_frame,
                    textvariable=var,
                    values=config,
                    width=15,
                )
                widget.grid(row=row, column=1, sticky="w", padx=5, pady=3)

            self.field_vars[key] = var
            self.field_widgets[key] = widget

    def _setup_conditions_panel(self, parent):
        """Setup the conditions/prerequisites panel."""
        # Prerequisites section
        prereq_frame = ttk.LabelFrame(parent, text="前置事件 (prerequisites)", padding=5)
        prereq_frame.pack(fill=tk.X, pady=5)

        self.prereq_text = tk.Text(prereq_frame, height=3, width=50)
        self.prereq_text.pack(fill=tk.X)
        ttk.Label(prereq_frame, text="每行一个事件ID", foreground="gray").pack(anchor=tk.W)

        # Conditions section
        cond_frame = ttk.LabelFrame(parent, text="触发条件 (conditions) - JSON格式", padding=5)
        cond_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.conditions_editor = JsonTextEditor(
            cond_frame,
            height=10,
            show_line_numbers=False,
            on_change=self._on_detail_change,
        )
        self.conditions_editor.pack(fill=tk.BOTH, expand=True)

    def _setup_json_editor(self, parent):
        """Setup the raw JSON editor tab."""
        # Instructions
        ttk.Label(
            parent,
            text="直接编辑事件的完整JSON数据。修改后点击\"从JSON更新\"应用更改。",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 5))

        # JSON editor
        self.json_editor = JsonTextEditor(
            parent,
            height=20,
            show_line_numbers=True,
            on_change=self._on_detail_change,
        )
        self.json_editor.pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="从JSON更新", command=self._apply_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="格式化", command=lambda: self.json_editor._format_json()).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="验证", command=self._validate_json).pack(side=tk.LEFT, padx=2)

    # --- List Operations ---

    def _refresh_list(self):
        """Refresh the event list with current filter."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get filtered events
        filtered = self._filter_events()
        self._filtered_indices = [idx for idx, _ in filtered]

        # Populate tree
        for display_idx, (actual_idx, event) in enumerate(filtered):
            event_id = event.get("id", event.get("event_id", f"index_{actual_idx}"))
            title = event.get("title", "无标题")
            event_type = self._classify_event(event)
            weight = event.get("weight", 10)

            self.tree.insert(
                "",
                tk.END,
                iid=str(display_idx),
                values=(event_id, title, event_type, weight),
                tags=(event_type,)
            )

        # Update count label
        total = len(self.events)
        shown = len(filtered)
        if total == shown:
            self.count_label.configure(text=f"共 {total} 个事件")
        else:
            self.count_label.configure(text=f"显示 {shown}/{total}")

        # Configure row colors
        self.tree.tag_configure("chain", foreground="#4A90D9")
        self.tree.tag_configure("single", foreground="#666666")
        self.tree.tag_configure("repeatable", foreground="#2E7D32")

    def _filter_events(self) -> List[Tuple[int, Dict]]:
        """Filter events based on search text and type filter."""
        filter_text = self.filter_var.get().lower().strip()
        type_filter = self.type_filter_var.get()

        results = []
        for i, event in enumerate(self.events):
            # Text filter
            if filter_text:
                searchable = " ".join([
                    str(event.get("id", "")),
                    str(event.get("title", "")),
                    str(event.get("description", "")),
                ]).lower()
                if filter_text not in searchable:
                    continue

            # Type filter
            if type_filter != "all":
                event_type = self._classify_event(event)
                if type_filter == "one-time" and event.get("repeatable", True):
                    continue
                elif type_filter == "repeatable" and not event.get("repeatable", True):
                    continue
                elif type_filter in ("single", "chain") and event_type != type_filter:
                    continue

            results.append((i, event))

        return results

    def _classify_event(self, event: Dict) -> str:
        """Classify event type for display."""
        prereqs = event.get("prerequisites", [])
        has_next = any(c.get("next_event_id") for c in event.get("choices", []))

        if prereqs or has_next:
            return "chain"
        return "single"

    def _on_filter_change(self):
        """Handle filter change."""
        self._refresh_list()

    def _sort_by_column(self, column: str):
        """Sort list by column."""
        reverse = getattr(self, f"_sort_{column}_reverse", False)

        key_map = {
            "id": lambda e: e.get("id", ""),
            "title": lambda e: e.get("title", ""),
            "type": lambda e: self._classify_event(e),
            "weight": lambda e: e.get("weight", 0),
        }

        if column in key_map:
            self.events.sort(key=key_map[column], reverse=reverse)
            setattr(self, f"_sort_{column}_reverse", not reverse)
            self._refresh_list()

    # --- Selection and Detail Loading ---

    def _on_select(self, event=None):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if not selection:
            self.selected_index = -1
            return

        display_idx = int(selection[0])
        if display_idx < len(self._filtered_indices):
            self.selected_index = self._filtered_indices[display_idx]
            self._load_event_details()

    def _on_double_click(self, event):
        """Handle double-click to expand details."""
        self.notebook.select(0)  # Switch to basic info tab

    def _load_event_details(self):
        """Load selected event into detail panels."""
        if self.selected_index < 0 or self.selected_index >= len(self.events):
            return

        event = self.events[self.selected_index]

        # Load basic fields
        for key, var in self.field_vars.items():
            value = event.get(key, "")
            widget = self.field_widgets.get(key)

            if var is None and widget:  # Text widget
                widget.delete("1.0", tk.END)
                widget.insert("1.0", str(value) if value else "")
            elif isinstance(var, tk.BooleanVar):
                var.set(bool(value) if value is not None else True)
            elif isinstance(var, tk.IntVar):
                try:
                    var.set(int(value) if value else 0)
                except (ValueError, TypeError):
                    var.set(0)
            elif var:
                var.set(str(value) if value else "")

        # Load choices
        self.choice_editor.set_choices(event.get("choices", []))

        # Load prerequisites
        self.prereq_text.delete("1.0", tk.END)
        prereqs = event.get("prerequisites", [])
        if prereqs:
            self.prereq_text.insert("1.0", "\n".join(prereqs))

        # Load conditions
        conditions = event.get("conditions", [])
        self.conditions_editor.set_json(conditions if conditions else [])

        # Load full JSON
        self.json_editor.set_json(event)

        self.status_label.configure(text=f"已加载: {event.get('id', '')}")

    def _on_detail_change(self):
        """Handle detail panel changes."""
        pass  # Can be used for auto-save or dirty tracking

    # --- CRUD Operations with Undo/Redo ---

    def _add_event(self):
        """Add a new event."""
        new_event = {
            "id": f"new_event_{len(self.events) + 1}",
            "title": "新事件",
            "description": "",
            "type": "random",
            "choices": [],
            "weight": 10,
            "repeatable": True,
        }

        cmd = AddEventCommand(self, new_event)
        if self.command_history.execute_command(cmd):
            self._refresh_list()
            self._select_event_by_index(len(self.events) - 1)
            self._notify_modified()

    def _delete_event(self):
        """Delete selected event."""
        if self.selected_index < 0:
            return

        event = self.events[self.selected_index]
        if not messagebox.askyesno("确认删除", f"确定要删除事件 '{event.get('title', '')}'?"):
            return

        cmd = DeleteEventCommand(self, self.selected_index)
        if self.command_history.execute_command(cmd):
            self._refresh_list()
            self.selected_index = -1
            self._notify_modified()

    def _update_current(self):
        """Update current event from form data."""
        if self.selected_index < 0:
            return

        old_data = self.events[self.selected_index].copy()
        new_data = self._collect_form_data()

        if old_data == new_data:
            self.status_label.configure(text="无更改")
            return

        cmd = UpdateEventCommand(self, self.selected_index, old_data, new_data)
        if self.command_history.execute_command(cmd):
            self._refresh_list()
            self._select_event_by_index(self.selected_index)
            self.status_label.configure(text="已更新")
            self._notify_modified()

    def _collect_form_data(self) -> Dict:
        """Collect data from all form fields."""
        data = {}

        # Collect basic fields
        for key, var in self.field_vars.items():
            widget = self.field_widgets.get(key)

            if var is None and widget:  # Text widget
                value = widget.get("1.0", tk.END).strip()
            elif isinstance(var, tk.BooleanVar):
                value = var.get()
            elif isinstance(var, tk.IntVar):
                value = var.get()
            else:
                value = var.get() if var else ""

            if value or key in ("id", "title", "repeatable"):
                data[key] = value

        # Collect choices
        data["choices"] = self.choice_editor.get_choices()

        # Collect prerequisites
        prereq_text = self.prereq_text.get("1.0", tk.END).strip()
        if prereq_text:
            data["prerequisites"] = [p.strip() for p in prereq_text.split("\n") if p.strip()]

        # Collect conditions
        conditions = self.conditions_editor.get_json()
        if conditions:
            data["conditions"] = conditions

        return data

    def _copy_event(self):
        """Copy selected event to clipboard."""
        if self.selected_index < 0:
            return

        self.clipboard = json.loads(json.dumps(self.events[self.selected_index]))
        self.status_label.configure(text="已复制")

    def _paste_event(self):
        """Paste event from clipboard."""
        if not self.clipboard:
            return

        cmd = DuplicateEventCommand(self, self.selected_index if self.selected_index >= 0 else len(self.events) - 1)
        # Use AddEventCommand with clipboard data instead
        paste_data = json.loads(json.dumps(self.clipboard))
        paste_data["id"] = paste_data.get("id", "event") + "_copy"

        # Ensure unique ID
        existing_ids = {e.get("id") for e in self.events}
        base_id = paste_data["id"]
        counter = 1
        while paste_data["id"] in existing_ids:
            paste_data["id"] = f"{base_id}_{counter}"
            counter += 1

        cmd = AddEventCommand(self, paste_data)
        if self.command_history.execute_command(cmd):
            self._refresh_list()
            self._select_event_by_index(len(self.events) - 1)
            self.status_label.configure(text="已粘贴")
            self._notify_modified()

    def _undo(self):
        """Undo last operation."""
        if self.command_history.undo():
            self._refresh_list()
            self.status_label.configure(text="已撤销")
            self._notify_modified()

    def _redo(self):
        """Redo last undone operation."""
        if self.command_history.redo():
            self._refresh_list()
            self.status_label.configure(text="已重做")
            self._notify_modified()

    def _update_undo_buttons(self):
        """Update undo/redo button states."""
        self.undo_btn.configure(
            state=tk.NORMAL if self.command_history.can_undo() else tk.DISABLED
        )
        self.redo_btn.configure(
            state=tk.NORMAL if self.command_history.can_redo() else tk.DISABLED
        )

    # --- Drag and Drop ---

    def _on_drag_start(self, event):
        """Start drag operation."""
        item = self.tree.identify_row(event.y)
        if item:
            self._drag_item = item
            self._drag_start_index = int(item)

    def _on_drag_motion(self, event):
        """Handle drag motion."""
        if self._drag_item is None:
            return

        target = self.tree.identify_row(event.y)
        if target and target != self._drag_item:
            # Visual feedback
            self.tree.selection_set(target)

    def _on_drag_end(self, event):
        """End drag operation and apply move."""
        if self._drag_item is None:
            return

        target = self.tree.identify_row(event.y)
        if target and target != self._drag_item:
            target_display_idx = int(target)
            source_display_idx = self._drag_start_index

            # Convert to actual indices
            if source_display_idx < len(self._filtered_indices) and target_display_idx < len(self._filtered_indices):
                source_actual = self._filtered_indices[source_display_idx]
                target_actual = self._filtered_indices[target_display_idx]

                cmd = MoveEventCommand(self, source_actual, target_actual)
                if self.command_history.execute_command(cmd):
                    self._refresh_list()
                    self._notify_modified()

        self._drag_item = None
        self._drag_start_index = -1

    # --- JSON Operations ---

    def _apply_json(self):
        """Apply changes from JSON editor."""
        if self.selected_index < 0:
            return

        new_data = self.json_editor.get_json()
        if new_data is None:
            messagebox.showerror("JSON错误", "无效的JSON格式")
            return

        old_data = self.events[self.selected_index].copy()

        cmd = UpdateEventCommand(self, self.selected_index, old_data, new_data)
        if self.command_history.execute_command(cmd):
            self._refresh_list()
            self._load_event_details()
            self.status_label.configure(text="已从JSON更新")
            self._notify_modified()

    def _validate_json(self):
        """Validate JSON in editor."""
        is_valid, error = self.json_editor.validate_json()
        if is_valid:
            messagebox.showinfo("验证通过", "JSON格式正确")
        else:
            messagebox.showerror("验证失败", f"JSON格式错误:\n{error}")

    # --- File Operations ---

    def _reload_data(self):
        """Reload data from file."""
        if messagebox.askyesno("重新加载", "确定要重新加载? 未保存的更改将丢失。"):
            self._load_data()
            self._refresh_list()
            self.command_history.clear()
            self.selected_index = -1
            self.status_label.configure(text="已重新加载")

    def _open_file(self):
        """Open a different event file."""
        path = filedialog.askopenfilename(
            title="打开事件文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.file_path = Path(path)
            self._load_data()
            self._refresh_list()
            self.command_history.clear()
            self.selected_index = -1

    def _show_analysis(self):
        """Show event analysis dialog."""
        if not self.events:
            messagebox.showinfo("分析", "没有事件可分析")
            return

        analyzer = EventAnalyzer(self.events)
        report = analyzer.analyze()

        # Create analysis dialog
        dialog = tk.Toplevel(self)
        dialog.title("事件分析报告")
        dialog.geometry("600x500")
        dialog.transient(self)

        # Report text
        text = tk.Text(dialog, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)

        text.insert("1.0", report.to_text())
        text.configure(state=tk.DISABLED)

        # Close button
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)

    # --- Helper Methods ---

    def _select_event_by_index(self, actual_index: int):
        """Select event by actual index."""
        try:
            display_idx = self._filtered_indices.index(actual_index)
            self.tree.selection_set(str(display_idx))
            self.tree.see(str(display_idx))
            self.selected_index = actual_index
            self._load_event_details()
        except ValueError:
            pass

    def _notify_modified(self):
        """Notify parent of modifications."""
        if self.on_modified:
            self.on_modified()

    # --- Public API ---

    def refresh(self):
        """Public refresh method."""
        self._refresh_list()

    def get_events(self) -> List[Dict]:
        """Get current events list."""
        return self.events

    def set_events(self, events: List[Dict]):
        """Set events list."""
        self.events = events
        self._refresh_list()
