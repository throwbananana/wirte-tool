"""
Choice Editor - 可视化选项编辑器

功能:
- 可折叠的选项卡片
- 效果编辑器 (好感度、心情、跳转等)
- 拖拽排序
- 添加/删除选项
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional


class ChoiceEditorPanel(ttk.Frame):
    """Visual editor for event choices."""

    def __init__(
        self,
        parent,
        on_change: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.choices: List[Dict] = []
        self.on_change = on_change
        self.choice_widgets: List[ChoiceItemWidget] = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI layout."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="+ 添加选项", command=self._add_choice).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="展开全部", command=self._expand_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="折叠全部", command=self._collapse_all).pack(side=tk.LEFT, padx=2)

        # Scrollable container for choices
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)

        self.choices_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.choices_frame, anchor="nw", tags="inner"
        )

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind resize events
        self.choices_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_frame_configure(self, event=None):
        """Update scroll region when frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        """Update inner frame width when canvas resizes."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_choices(self, choices: List[Dict]):
        """Load choices data into the editor."""
        self.choices = choices if choices else []
        self._rebuild_widgets()

    def get_choices(self) -> List[Dict]:
        """Get current choices data from widgets."""
        result = []
        for widget in self.choice_widgets:
            result.append(widget.get_data())
        return result

    def _rebuild_widgets(self):
        """Rebuild all choice widgets."""
        # Clear existing widgets
        for widget in self.choice_widgets:
            widget.destroy()
        self.choice_widgets.clear()

        # Create new widgets
        for i, choice_data in enumerate(self.choices):
            self._add_choice_widget(choice_data, i)

    def _add_choice(self):
        """Add a new empty choice."""
        new_choice = {
            "text": "新选项",
            "outcome_text": "",
            "effects": [],
        }
        self.choices.append(new_choice)
        self._add_choice_widget(new_choice, len(self.choices) - 1)
        self._notify_change()

    def _add_choice_widget(self, choice_data: Dict, index: int):
        """Add a single choice widget."""
        widget = ChoiceItemWidget(
            self.choices_frame,
            choice_data,
            index,
            on_delete=self._delete_choice,
            on_move_up=lambda i: self._move_choice(i, -1),
            on_move_down=lambda i: self._move_choice(i, 1),
            on_change=self._notify_change,
        )
        widget.pack(fill=tk.X, pady=2, padx=2)
        self.choice_widgets.append(widget)

    def _delete_choice(self, index: int):
        """Delete a choice by index."""
        if 0 <= index < len(self.choices):
            del self.choices[index]
            self._rebuild_widgets()
            self._notify_change()

    def _move_choice(self, index: int, direction: int):
        """Move a choice up or down."""
        new_index = index + direction
        if 0 <= new_index < len(self.choices):
            self.choices[index], self.choices[new_index] = (
                self.choices[new_index],
                self.choices[index],
            )
            self._rebuild_widgets()
            self._notify_change()

    def _expand_all(self):
        """Expand all choice widgets."""
        for widget in self.choice_widgets:
            widget.expand()

    def _collapse_all(self):
        """Collapse all choice widgets."""
        for widget in self.choice_widgets:
            widget.collapse()

    def _notify_change(self):
        """Notify parent of changes."""
        # Update internal data from widgets
        self.choices = self.get_choices()
        if self.on_change:
            self.on_change()


class ChoiceItemWidget(ttk.Frame):
    """Single choice item with collapsible details."""

    def __init__(
        self,
        parent,
        choice_data: Dict,
        index: int,
        on_delete: Callable[[int], None],
        on_move_up: Callable[[int], None],
        on_move_down: Callable[[int], None],
        on_change: Callable[[], None],
    ):
        super().__init__(parent, relief="groove", borderwidth=1)
        self.choice_data = choice_data
        self.index = index
        self.on_delete = on_delete
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down
        self.on_change = on_change
        self.expanded = False

        self.effect_widgets: Dict[str, Any] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget UI."""
        # Header row (always visible)
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=5, pady=3)

        # Expand button
        self.expand_btn = ttk.Button(
            header, text="▶", width=2, command=self._toggle_expand
        )
        self.expand_btn.pack(side=tk.LEFT)

        # Index label
        ttk.Label(header, text=f"选项 {self.index + 1}:", width=8).pack(side=tk.LEFT, padx=2)

        # Choice text entry
        self.text_var = tk.StringVar(value=self.choice_data.get("text", ""))
        self.text_entry = ttk.Entry(header, textvariable=self.text_var)
        self.text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.text_var.trace_add("write", lambda *a: self.on_change())

        # Control buttons
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="▲", width=2, command=lambda: self.on_move_up(self.index)).pack(
            side=tk.LEFT
        )
        ttk.Button(btn_frame, text="▼", width=2, command=lambda: self.on_move_down(self.index)).pack(
            side=tk.LEFT
        )
        ttk.Button(btn_frame, text="✕", width=2, command=lambda: self.on_delete(self.index)).pack(
            side=tk.LEFT, padx=(5, 0)
        )

        # Detail panel (collapsible)
        self.detail_frame = ttk.Frame(self)
        self._setup_details()

    def _setup_details(self):
        """Setup the detail panel content."""
        # Outcome text
        outcome_frame = ttk.Frame(self.detail_frame)
        outcome_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(outcome_frame, text="结果描述:").pack(anchor=tk.W)
        self.outcome_text = tk.Text(outcome_frame, height=3, width=50)
        self.outcome_text.pack(fill=tk.X, pady=2)
        self.outcome_text.insert("1.0", self.choice_data.get("outcome_text", ""))
        self.outcome_text.bind("<KeyRelease>", lambda e: self.on_change())

        # Effects section
        effects_frame = ttk.LabelFrame(self.detail_frame, text="效果", padding=5)
        effects_frame.pack(fill=tk.X, padx=10, pady=5)

        # Common effect fields
        effect_fields = [
            ("affection_change", "好感度变化:", "spinbox", (-100, 100)),
            ("mood_change", "心情变化:", "spinbox", (-100, 100)),
            ("next_event_id", "跳转事件ID:", "entry", None),
            ("unlock_achievement", "解锁成就:", "entry", None),
        ]

        for i, (key, label, widget_type, config) in enumerate(effect_fields):
            row_frame = ttk.Frame(effects_frame)
            row_frame.pack(fill=tk.X, pady=2)

            ttk.Label(row_frame, text=label, width=14, anchor=tk.E).pack(side=tk.LEFT)

            current_value = self.choice_data.get(key, "")

            if widget_type == "spinbox":
                var = tk.IntVar(value=int(current_value) if current_value else 0)
                widget = ttk.Spinbox(
                    row_frame,
                    textvariable=var,
                    from_=config[0],
                    to=config[1],
                    width=10,
                )
                var.trace_add("write", lambda *a: self.on_change())
            else:
                var = tk.StringVar(value=str(current_value) if current_value else "")
                widget = ttk.Entry(row_frame, textvariable=var, width=30)
                var.trace_add("write", lambda *a: self.on_change())

            widget.pack(side=tk.LEFT, padx=5)
            self.effect_widgets[key] = var

        # Conditions section (simplified)
        conditions_frame = ttk.LabelFrame(self.detail_frame, text="触发条件", padding=5)
        conditions_frame.pack(fill=tk.X, padx=10, pady=5)

        cond_row = ttk.Frame(conditions_frame)
        cond_row.pack(fill=tk.X, pady=2)

        ttk.Label(cond_row, text="最低好感度:", width=14, anchor=tk.E).pack(side=tk.LEFT)
        self.req_affection_var = tk.IntVar(
            value=int(self.choice_data.get("required_affection", 0) or 0)
        )
        ttk.Spinbox(
            cond_row,
            textvariable=self.req_affection_var,
            from_=0,
            to=100,
            width=10,
        ).pack(side=tk.LEFT, padx=5)
        self.req_affection_var.trace_add("write", lambda *a: self.on_change())

    def _toggle_expand(self):
        """Toggle expanded state."""
        if self.expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        """Expand the detail panel."""
        self.expanded = True
        self.expand_btn.configure(text="▼")
        self.detail_frame.pack(fill=tk.X)

    def collapse(self):
        """Collapse the detail panel."""
        self.expanded = False
        self.expand_btn.configure(text="▶")
        self.detail_frame.pack_forget()

    def get_data(self) -> Dict:
        """Extract current data from widgets."""
        data = {
            "text": self.text_var.get(),
            "outcome_text": self.outcome_text.get("1.0", tk.END).strip(),
        }

        # Collect effects
        for key, var in self.effect_widgets.items():
            value = var.get()
            if value:
                if key in ("affection_change", "mood_change"):
                    try:
                        int_val = int(value)
                        if int_val != 0:
                            data[key] = int_val
                    except (ValueError, TypeError):
                        pass
                else:
                    if str(value).strip():
                        data[key] = str(value).strip()

        # Collect conditions
        req_aff = self.req_affection_var.get()
        if req_aff > 0:
            data["required_affection"] = req_aff

        return data

    def update_index(self, new_index: int):
        """Update the displayed index."""
        self.index = new_index


class EffectListEditor(ttk.Frame):
    """Editor for a list of effects (advanced mode)."""

    def __init__(
        self,
        parent,
        effects: Optional[List[Dict]] = None,
        on_change: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.effects = effects if effects else []
        self.on_change = on_change
        self.effect_rows: List[ttk.Frame] = []

        self._setup_ui()
        self._rebuild_rows()

    def _setup_ui(self):
        """Setup the UI."""
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X)

        ttk.Button(header, text="+ 添加效果", command=self._add_effect).pack(side=tk.LEFT)

        # Effects container
        self.effects_frame = ttk.Frame(self)
        self.effects_frame.pack(fill=tk.BOTH, expand=True)

    def _rebuild_rows(self):
        """Rebuild effect rows."""
        for row in self.effect_rows:
            row.destroy()
        self.effect_rows.clear()

        for i, effect in enumerate(self.effects):
            self._add_effect_row(effect, i)

    def _add_effect(self):
        """Add a new effect."""
        new_effect = {"effect_type": "affection", "value": 0}
        self.effects.append(new_effect)
        self._add_effect_row(new_effect, len(self.effects) - 1)
        self._notify_change()

    def _add_effect_row(self, effect: Dict, index: int):
        """Add a single effect row."""
        row = ttk.Frame(self.effects_frame)
        row.pack(fill=tk.X, pady=2)

        # Effect type dropdown
        effect_types = [
            "affection", "mood", "flag", "item",
            "achievement", "unlock_location", "time_advance"
        ]
        type_var = tk.StringVar(value=effect.get("effect_type", "affection"))
        type_combo = ttk.Combobox(row, textvariable=type_var, values=effect_types, width=15)
        type_combo.pack(side=tk.LEFT, padx=2)
        type_var.trace_add("write", lambda *a: self._on_row_change(index, "effect_type", type_var.get()))

        # Target entry
        ttk.Label(row, text="目标:").pack(side=tk.LEFT, padx=(5, 2))
        target_var = tk.StringVar(value=effect.get("target", ""))
        target_entry = ttk.Entry(row, textvariable=target_var, width=15)
        target_entry.pack(side=tk.LEFT, padx=2)
        target_var.trace_add("write", lambda *a: self._on_row_change(index, "target", target_var.get()))

        # Value entry
        ttk.Label(row, text="值:").pack(side=tk.LEFT, padx=(5, 2))
        value_var = tk.StringVar(value=str(effect.get("value", "")))
        value_entry = ttk.Entry(row, textvariable=value_var, width=10)
        value_entry.pack(side=tk.LEFT, padx=2)
        value_var.trace_add("write", lambda *a: self._on_row_change(index, "value", value_var.get()))

        # Delete button
        ttk.Button(
            row, text="✕", width=2, command=lambda i=index: self._delete_effect(i)
        ).pack(side=tk.RIGHT)

        self.effect_rows.append(row)

    def _on_row_change(self, index: int, key: str, value: str):
        """Handle change in an effect row."""
        if 0 <= index < len(self.effects):
            # Try to convert value to int for numeric fields
            if key == "value":
                try:
                    value = int(value)
                except ValueError:
                    pass
            self.effects[index][key] = value
            self._notify_change()

    def _delete_effect(self, index: int):
        """Delete an effect."""
        if 0 <= index < len(self.effects):
            del self.effects[index]
            self._rebuild_rows()
            self._notify_change()

    def get_effects(self) -> List[Dict]:
        """Get current effects list."""
        return self.effects

    def set_effects(self, effects: List[Dict]):
        """Set effects list."""
        self.effects = effects if effects else []
        self._rebuild_rows()

    def _notify_change(self):
        """Notify parent of changes."""
        if self.on_change:
            self.on_change()
