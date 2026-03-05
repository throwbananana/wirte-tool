"""
POV filtering widget for scene lists and editors.

Provides UI components for filtering and selecting POV characters:
- POVFilterWidget: Dropdown filter for scene lists
- POVSelectorDialog: Dialog for setting POV on a scene

Usage:
    filter_widget = POVFilterWidget(parent, project_manager, on_filter_change)
    filter_widget.pack()
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List, Dict, Any

from writer_app.core.pov_manager import POVManager, NarrativeVoice


class POVFilterWidget(ttk.Frame):
    """
    Dropdown/filter bar for filtering scenes by POV character.

    Features:
    - Combobox with all narrator characters
    - "All POVs" option
    - Visual indicator showing current filter
    - Scene count display
    """

    def __init__(
        self,
        parent,
        project_manager,
        on_filter_change: Callable[[Optional[str]], None] = None,
        show_stats: bool = True
    ):
        """
        Initialize the POV filter widget.

        Args:
            parent: Parent widget
            project_manager: ProjectManager instance
            on_filter_change: Callback when filter changes, receives character UID or None
            show_stats: Whether to show scene count statistics
        """
        super().__init__(parent)
        self.pm = project_manager
        self.pov_manager = POVManager(project_manager)
        self.on_filter_change = on_filter_change
        self.show_stats = show_stats

        self._current_filter: Optional[str] = None
        self._char_uid_map: Dict[str, str] = {}  # display_name -> uid

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Build the filter widget UI."""
        # Filter label
        ttk.Label(self, text="POV:").pack(side=tk.LEFT, padx=(0, 5))

        # Combobox for POV selection
        self.pov_combo = ttk.Combobox(
            self,
            state="readonly",
            width=15
        )
        self.pov_combo.pack(side=tk.LEFT)
        self.pov_combo.bind("<<ComboboxSelected>>", self._on_selection_changed)

        # Stats label
        if self.show_stats:
            self.stats_label = ttk.Label(self, text="", foreground="gray")
            self.stats_label.pack(side=tk.LEFT, padx=(10, 0))

        # Clear filter button
        self.clear_btn = ttk.Button(
            self,
            text="X",
            width=2,
            command=self._clear_filter
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(5, 0))

    def refresh(self):
        """Refresh the POV character list."""
        # Build character list
        values = ["-- \u5168\u90e8\u89c6\u89d2 --"]  # All POVs
        self._char_uid_map = {"-- \u5168\u90e8\u89c6\u89d2 --": None}

        # Get POV characters
        pov_chars = self.pov_manager.get_pov_characters()

        for char in pov_chars:
            name = char.get("name", "")
            uid = char.get("uid", "")
            if name and uid:
                # Count scenes for this POV
                scene_count = len(self.pov_manager.get_scenes_by_pov(uid))
                display = f"{name} ({scene_count})"
                values.append(display)
                self._char_uid_map[display] = uid

        # Add characters marked as narrators but not yet used
        for char in self.pov_manager.get_narrator_characters():
            uid = char.get("uid", "")
            if uid not in self._char_uid_map.values():
                name = char.get("name", "")
                display = f"{name} (0)"
                values.append(display)
                self._char_uid_map[display] = uid

        self.pov_combo["values"] = values

        # Restore selection
        if self._current_filter:
            for display, uid in self._char_uid_map.items():
                if uid == self._current_filter:
                    self.pov_combo.set(display)
                    break
        else:
            self.pov_combo.set(values[0])

        # Update stats
        self._update_stats()

    def _update_stats(self):
        """Update the statistics display."""
        if not self.show_stats:
            return

        stats = self.pov_manager.get_pov_statistics()
        total = stats["total_scenes"]
        with_pov = stats["scenes_with_pov"]

        if self._current_filter:
            filtered_count = len(self.pov_manager.get_scenes_by_pov(self._current_filter))
            self.stats_label.config(text=f"({filtered_count}/{total})")
        else:
            self.stats_label.config(text=f"({with_pov}/{total} \u5df2\u8bbe\u7f6ePOV)")

    def _on_selection_changed(self, event=None):
        """Handle combobox selection change."""
        selection = self.pov_combo.get()
        self._current_filter = self._char_uid_map.get(selection)

        self._update_stats()

        if self.on_filter_change:
            self.on_filter_change(self._current_filter)

    def _clear_filter(self):
        """Clear the current filter."""
        self._current_filter = None
        self.pov_combo.set("-- \u5168\u90e8\u89c6\u89d2 --")
        self._update_stats()

        if self.on_filter_change:
            self.on_filter_change(None)

    def get_current_filter(self) -> Optional[str]:
        """Get the currently selected POV character UID."""
        return self._current_filter

    def set_filter(self, character_uid: Optional[str]):
        """
        Set the filter to a specific character.

        Args:
            character_uid: Character UID to filter by, or None to clear
        """
        self._current_filter = character_uid

        if character_uid is None:
            self.pov_combo.set("-- \u5168\u90e8\u89c6\u89d2 --")
        else:
            for display, uid in self._char_uid_map.items():
                if uid == character_uid:
                    self.pov_combo.set(display)
                    break

        self._update_stats()


class POVSelectorDialog(tk.Toplevel):
    """
    Dialog for setting POV on a scene.

    Allows selecting:
    - POV character
    - Narrative voice
    - Narrator reliability
    - POV notes
    """

    def __init__(
        self,
        parent,
        project_manager,
        scene_data: Dict[str, Any],
        on_save: Callable[[Dict[str, Any]], None] = None
    ):
        """
        Initialize the POV selector dialog.

        Args:
            parent: Parent window
            project_manager: ProjectManager instance
            scene_data: Current scene data dict
            on_save: Callback when user saves, receives updated POV fields
        """
        super().__init__(parent)
        self.pm = project_manager
        self.scene_data = scene_data
        self.on_save = on_save
        self.result: Optional[Dict[str, Any]] = None

        self.title("\u8bbe\u7f6e\u89c6\u89d2 (POV)")
        self.resizable(False, False)

        self._setup_ui()
        self._load_current_values()
        self._center_dialog()

        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        """Build the dialog UI."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Scene name display
        scene_name = self.scene_data.get("name", "\u672a\u547d\u540d\u573a\u666f")
        ttk.Label(
            main_frame,
            text=f"\u573a\u666f\uff1a{scene_name}",
            font=("", 10, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))

        # POV Character
        ttk.Label(main_frame, text="\u89c6\u89d2\u89d2\u8272\uff1a").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )

        self.pov_combo = ttk.Combobox(main_frame, state="readonly", width=25)
        self.pov_combo.grid(row=1, column=1, sticky=tk.W, pady=5)

        # Populate POV characters
        pov_values = ["-- \u672a\u8bbe\u7f6e --"]
        self._pov_uid_map = {"-- \u672a\u8bbe\u7f6e --": ""}

        for char in self.pm.get_characters():
            name = char.get("name", "")
            uid = char.get("uid", "")
            if name and uid:
                pov_values.append(name)
                self._pov_uid_map[name] = uid

        self.pov_combo["values"] = pov_values

        # Narrative Voice
        ttk.Label(main_frame, text="\u53d9\u8ff0\u4eba\u79f0\uff1a").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )

        self.voice_combo = ttk.Combobox(main_frame, state="readonly", width=25)
        self.voice_combo.grid(row=2, column=1, sticky=tk.W, pady=5)

        voice_values = [
            ("\u7b2c\u4e00\u4eba\u79f0", "first"),
            ("\u7b2c\u4e8c\u4eba\u79f0", "second"),
            ("\u7b2c\u4e09\u4eba\u79f0\uff08\u9650\u5236\u89c6\u89d2\uff09", "third_limited"),
            ("\u7b2c\u4e09\u4eba\u79f0\uff08\u5168\u77e5\u89c6\u89d2\uff09", "third_omniscient")
        ]
        self._voice_map = {v[0]: v[1] for v in voice_values}
        self._voice_reverse_map = {v[1]: v[0] for v in voice_values}
        self.voice_combo["values"] = [v[0] for v in voice_values]

        # Narrator Reliability
        ttk.Label(main_frame, text="\u53d9\u8ff0\u8005\u53ef\u9760\u5ea6\uff1a").grid(
            row=3, column=0, sticky=tk.W, pady=5
        )

        reliability_frame = ttk.Frame(main_frame)
        reliability_frame.grid(row=3, column=1, sticky=tk.W, pady=5)

        self.reliability_var = tk.DoubleVar(value=1.0)
        self.reliability_scale = ttk.Scale(
            reliability_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.reliability_var,
            length=150,
            command=self._on_reliability_change
        )
        self.reliability_scale.pack(side=tk.LEFT)

        self.reliability_label = ttk.Label(reliability_frame, text="100%", width=5)
        self.reliability_label.pack(side=tk.LEFT, padx=(5, 0))

        # Reliability description
        self.reliability_desc = ttk.Label(
            main_frame,
            text="\u5b8c\u5168\u53ef\u9760",
            foreground="green",
            font=("", 9)
        )
        self.reliability_desc.grid(row=4, column=1, sticky=tk.W)

        # POV Notes
        ttk.Label(main_frame, text="\u89c6\u89d2\u9650\u5236\u8bf4\u660e\uff1a").grid(
            row=5, column=0, sticky=tk.NW, pady=5
        )

        self.notes_text = tk.Text(main_frame, width=30, height=3, wrap=tk.WORD)
        self.notes_text.grid(row=5, column=1, sticky=tk.W, pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(15, 0))

        ttk.Button(btn_frame, text="\u53d6\u6d88", command=self._on_cancel).pack(
            side=tk.RIGHT, padx=(10, 0)
        )
        ttk.Button(btn_frame, text="\u4fdd\u5b58", command=self._on_save).pack(
            side=tk.RIGHT
        )

    def _load_current_values(self):
        """Load current POV values from scene data."""
        # POV Character
        pov_uid = self.scene_data.get("pov_character", "")
        if pov_uid:
            for name, uid in self._pov_uid_map.items():
                if uid == pov_uid:
                    self.pov_combo.set(name)
                    break
        else:
            self.pov_combo.set("-- \u672a\u8bbe\u7f6e --")

        # Narrative Voice
        voice = self.scene_data.get("narrative_voice", "third_limited")
        display = self._voice_reverse_map.get(voice, "\u7b2c\u4e09\u4eba\u79f0\uff08\u9650\u5236\u89c6\u89d2\uff09")
        self.voice_combo.set(display)

        # Reliability
        reliability = self.scene_data.get("narrator_reliability", 1.0)
        self.reliability_var.set(reliability)
        self._on_reliability_change(reliability)

        # Notes
        notes = self.scene_data.get("pov_notes", "")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", notes)

    def _on_reliability_change(self, value):
        """Update reliability display."""
        try:
            val = float(value)
        except:
            val = 1.0

        self.reliability_label.config(text=f"{int(val * 100)}%")

        if val >= 0.9:
            self.reliability_desc.config(text="\u5b8c\u5168\u53ef\u9760", foreground="green")
        elif val >= 0.7:
            self.reliability_desc.config(text="\u57fa\u672c\u53ef\u9760", foreground="darkgreen")
        elif val >= 0.5:
            self.reliability_desc.config(text="\u90e8\u5206\u53ef\u9760", foreground="orange")
        elif val >= 0.3:
            self.reliability_desc.config(text="\u4e0d\u592a\u53ef\u9760", foreground="darkorange")
        else:
            self.reliability_desc.config(text="\u4e0d\u53ef\u9760\u53d9\u8ff0\u8005", foreground="red")

    def _center_dialog(self):
        """Center the dialog on parent."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _on_save(self):
        """Handle save button."""
        # Get values
        pov_selection = self.pov_combo.get()
        pov_uid = self._pov_uid_map.get(pov_selection, "")

        voice_selection = self.voice_combo.get()
        voice = self._voice_map.get(voice_selection, "third_limited")

        reliability = self.reliability_var.get()

        notes = self.notes_text.get("1.0", tk.END).strip()

        self.result = {
            "pov_character": pov_uid,
            "narrative_voice": voice,
            "narrator_reliability": reliability,
            "pov_notes": notes
        }

        if self.on_save:
            self.on_save(self.result)

        self.destroy()

    def _on_cancel(self):
        """Handle cancel button."""
        self.result = None
        self.destroy()

    def show(self) -> Optional[Dict[str, Any]]:
        """Show the dialog and wait for result."""
        self.wait_window()
        return self.result


def show_pov_selector(
    parent,
    project_manager,
    scene_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to show POV selector dialog.

    Args:
        parent: Parent window
        project_manager: ProjectManager instance
        scene_data: Current scene data

    Returns:
        Updated POV fields dict, or None if cancelled
    """
    dialog = POVSelectorDialog(parent, project_manager, scene_data)
    return dialog.show()
