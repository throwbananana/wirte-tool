"""
JSON Text Editor - JSON 语法高亮文本编辑器

功能:
- JSON 语法高亮 (键、字符串、数字、布尔值、括号)
- 内置撤销/重做 (Ctrl+Z / Ctrl+Y)
- 格式化 JSON (Ctrl+Shift+F)
- 行号显示
- 错误提示
"""

from __future__ import annotations

import json
import re
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, List, Optional, Tuple


class JsonTextEditor(tk.Frame):
    """Text widget with JSON syntax highlighting and formatting."""

    # Syntax highlighting colors (VS Code dark theme inspired)
    SYNTAX_TAGS = {
        "key": {"foreground": "#9CDCFE"},       # Light blue for keys
        "string": {"foreground": "#CE9178"},    # Orange for string values
        "number": {"foreground": "#B5CEA8"},    # Green for numbers
        "boolean": {"foreground": "#569CD6"},   # Blue for true/false
        "null": {"foreground": "#569CD6"},      # Blue for null
        "bracket": {"foreground": "#FFD700"},   # Gold for brackets
        "error": {"foreground": "#FF6B6B", "underline": True},  # Red for errors
    }

    # Light theme colors
    SYNTAX_TAGS_LIGHT = {
        "key": {"foreground": "#0451A5"},
        "string": {"foreground": "#A31515"},
        "number": {"foreground": "#098658"},
        "boolean": {"foreground": "#0000FF"},
        "null": {"foreground": "#0000FF"},
        "bracket": {"foreground": "#000000"},
        "error": {"foreground": "#D32F2F", "underline": True},
    }

    def __init__(
        self,
        parent,
        height: int = 20,
        width: int = 60,
        show_line_numbers: bool = True,
        dark_theme: bool = True,
        on_change: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent)
        self.on_change = on_change
        self.dark_theme = dark_theme
        self.show_line_numbers = show_line_numbers

        # Undo/Redo stacks
        self._undo_stack: List[str] = []
        self._redo_stack: List[str] = []
        self._last_content: str = ""
        self._undo_delay_job = None

        self._setup_ui(height, width, **kwargs)
        self._setup_tags()
        self._setup_bindings()

    def _setup_ui(self, height: int, width: int, **kwargs):
        """Setup the UI components."""
        # Main container
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Line numbers (optional)
        if self.show_line_numbers:
            self.line_numbers = tk.Text(
                self,
                width=4,
                padx=3,
                takefocus=0,
                border=0,
                state=tk.DISABLED,
                wrap=tk.NONE,
            )
            self.line_numbers.grid(row=0, column=0, sticky="nsew")

        # Main text widget
        bg_color = "#1E1E1E" if self.dark_theme else "#FFFFFF"
        fg_color = "#D4D4D4" if self.dark_theme else "#000000"
        insert_color = "#FFFFFF" if self.dark_theme else "#000000"

        self.text = tk.Text(
            self,
            height=height,
            width=width,
            wrap=tk.NONE,
            undo=False,  # We handle undo ourselves
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color,
            selectbackground="#264F78" if self.dark_theme else "#ADD6FF",
            font=("Consolas", 10),
            **kwargs
        )
        self.text.grid(row=0, column=1, sticky="nsew")

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._on_scroll_y)
        v_scroll.grid(row=0, column=2, sticky="ns")
        self.text.configure(yscrollcommand=v_scroll.set)

        h_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.text.xview)
        h_scroll.grid(row=1, column=1, sticky="ew")
        self.text.configure(xscrollcommand=h_scroll.set)

        # Line number styling
        if self.show_line_numbers:
            ln_bg = "#252526" if self.dark_theme else "#F0F0F0"
            ln_fg = "#858585" if self.dark_theme else "#999999"
            self.line_numbers.configure(bg=ln_bg, fg=ln_fg, font=("Consolas", 10))

    def _on_scroll_y(self, *args):
        """Sync line numbers with text scroll."""
        self.text.yview(*args)
        if self.show_line_numbers:
            self.line_numbers.yview(*args)

    def _setup_tags(self):
        """Configure syntax highlighting tags."""
        tags = self.SYNTAX_TAGS if self.dark_theme else self.SYNTAX_TAGS_LIGHT
        for tag, config in tags.items():
            self.text.tag_configure(tag, **config)

    def _setup_bindings(self):
        """Setup keyboard bindings."""
        self.text.bind("<KeyRelease>", self._on_key_release)
        self.text.bind("<Control-z>", self._undo)
        self.text.bind("<Control-Z>", self._undo)
        self.text.bind("<Control-y>", self._redo)
        self.text.bind("<Control-Y>", self._redo)
        self.text.bind("<Control-Shift-F>", self._format_json)
        self.text.bind("<Control-Shift-f>", self._format_json)

        # Update line numbers on various events
        if self.show_line_numbers:
            self.text.bind("<Configure>", lambda e: self._update_line_numbers())
            self.text.bind("<MouseWheel>", lambda e: self.after(10, self._update_line_numbers))

    def _on_key_release(self, event=None):
        """Handle key release - update highlighting and save undo state."""
        # Ignore modifier keys
        if event and event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R",
                                       "Alt_L", "Alt_R", "Caps_Lock"):
            return

        self._highlight_syntax()
        self._update_line_numbers()
        self._schedule_undo_save()

        if self.on_change:
            self.on_change()

    def _schedule_undo_save(self):
        """Schedule undo state save with debounce."""
        if self._undo_delay_job:
            self.after_cancel(self._undo_delay_job)
        self._undo_delay_job = self.after(500, self._save_undo_state)

    def _save_undo_state(self):
        """Save current state to undo stack."""
        current = self.text.get("1.0", tk.END)
        if current != self._last_content:
            self._undo_stack.append(self._last_content)
            self._redo_stack.clear()
            self._last_content = current
            # Limit stack size
            if len(self._undo_stack) > 100:
                self._undo_stack.pop(0)

    def _highlight_syntax(self):
        """Apply syntax highlighting to JSON content."""
        content = self.text.get("1.0", tk.END)

        # Clear all tags
        for tag in self.SYNTAX_TAGS:
            self.text.tag_remove(tag, "1.0", tk.END)

        # Pattern matching for JSON elements
        patterns = [
            # Keys (quoted strings followed by colon)
            (r'"[^"\\]*(?:\\.[^"\\]*)*"\s*:', "key"),
            # String values (quoted strings after colon)
            (r':\s*"[^"\\]*(?:\\.[^"\\]*)*"', "string"),
            # Numbers
            (r':\s*-?\d+\.?\d*(?:[eE][+-]?\d+)?', "number"),
            # Booleans
            (r':\s*(true|false)\b', "boolean"),
            # Null
            (r':\s*null\b', "null"),
            # Brackets
            (r'[\[\]{}]', "bracket"),
        ]

        for pattern, tag in patterns:
            try:
                for match in re.finditer(pattern, content):
                    start_idx = f"1.0+{match.start()}c"
                    end_idx = f"1.0+{match.end()}c"
                    self.text.tag_add(tag, start_idx, end_idx)
            except re.error:
                pass

    def _update_line_numbers(self):
        """Update line numbers display."""
        if not self.show_line_numbers:
            return

        self.line_numbers.configure(state=tk.NORMAL)
        self.line_numbers.delete("1.0", tk.END)

        # Count lines in text widget
        content = self.text.get("1.0", tk.END)
        line_count = content.count("\n")

        # Generate line numbers
        line_numbers_text = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert("1.0", line_numbers_text)
        self.line_numbers.configure(state=tk.DISABLED)

        # Sync scroll position
        self.line_numbers.yview_moveto(self.text.yview()[0])

    def _format_json(self, event=None):
        """Format JSON with proper indentation."""
        try:
            content = self.text.get("1.0", tk.END).strip()
            if not content:
                return "break"

            parsed = json.loads(content)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)

            self._save_undo_state()
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", formatted)
            self._last_content = self.text.get("1.0", tk.END)
            self._highlight_syntax()
            self._update_line_numbers()

            if self.on_change:
                self.on_change()

        except json.JSONDecodeError as e:
            messagebox.showerror("JSON 格式错误", f"无法格式化: {e}")

        return "break"

    def _undo(self, event=None):
        """Undo last change."""
        if self._undo_stack:
            current = self.text.get("1.0", tk.END)
            self._redo_stack.append(current)
            previous = self._undo_stack.pop()
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", previous.rstrip("\n"))
            self._last_content = self.text.get("1.0", tk.END)
            self._highlight_syntax()
            self._update_line_numbers()

            if self.on_change:
                self.on_change()

        return "break"

    def _redo(self, event=None):
        """Redo last undone change."""
        if self._redo_stack:
            current = self.text.get("1.0", tk.END)
            self._undo_stack.append(current)
            next_state = self._redo_stack.pop()
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", next_state.rstrip("\n"))
            self._last_content = self.text.get("1.0", tk.END)
            self._highlight_syntax()
            self._update_line_numbers()

            if self.on_change:
                self.on_change()

        return "break"

    # Public API methods

    def get(self, start: str = "1.0", end: str = tk.END) -> str:
        """Get text content."""
        return self.text.get(start, end)

    def get_content(self) -> str:
        """Get text content stripped."""
        return self.text.get("1.0", tk.END).strip()

    def set_content(self, content: str):
        """Set text content and update highlighting."""
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self._last_content = self.text.get("1.0", tk.END)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._highlight_syntax()
        self._update_line_numbers()

    def delete(self, start: str, end: str):
        """Delete text."""
        self.text.delete(start, end)

    def insert(self, index: str, text: str):
        """Insert text."""
        self.text.insert(index, text)

    def validate_json(self) -> Tuple[bool, Optional[str]]:
        """Validate JSON content. Returns (is_valid, error_message)."""
        content = self.text.get("1.0", tk.END).strip()
        if not content:
            return True, None

        try:
            json.loads(content)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)

    def get_json(self) -> Optional[any]:
        """Parse and return JSON content, or None if invalid."""
        content = self.text.get("1.0", tk.END).strip()
        if not content:
            return None

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def set_json(self, data: any):
        """Set content from JSON data."""
        formatted = json.dumps(data, indent=2, ensure_ascii=False)
        self.set_content(formatted)

    def set_theme(self, dark: bool):
        """Switch between dark and light theme."""
        self.dark_theme = dark
        bg_color = "#1E1E1E" if dark else "#FFFFFF"
        fg_color = "#D4D4D4" if dark else "#000000"
        insert_color = "#FFFFFF" if dark else "#000000"
        select_bg = "#264F78" if dark else "#ADD6FF"

        self.text.configure(
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color,
            selectbackground=select_bg,
        )

        if self.show_line_numbers:
            ln_bg = "#252526" if dark else "#F0F0F0"
            ln_fg = "#858585" if dark else "#999999"
            self.line_numbers.configure(bg=ln_bg, fg=ln_fg)

        self._setup_tags()
        self._highlight_syntax()

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def focus_set(self):
        """Set focus to the text widget."""
        self.text.focus_set()
