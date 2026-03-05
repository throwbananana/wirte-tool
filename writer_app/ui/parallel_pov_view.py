"""
Parallel POV View - Side-by-side view for comparing scenes from different POVs.

Provides:
- Split view showing same scene from different perspectives
- Sync scrolling
- Difference highlighting
- AI helper for "How would X see this differently?"

Usage:
    view = ParallelPOVView(parent, project_manager)
    view.load_scene(scene_index)
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Dict, Any, List, Tuple
import logging

from writer_app.core.pov_manager import POVManager, NarrativeVoice

logger = logging.getLogger(__name__)


class ParallelPOVView(ttk.Frame):
    """
    Split view showing a scene from two different POVs.

    Features:
    - Left pane: Original scene content
    - Right pane: Same scene rewritten from alternate POV
    - Synchronized scrolling
    - POV selector for each pane
    - Difference highlighting
    - AI integration for rewriting suggestions
    """

    def __init__(
        self,
        parent,
        project_manager,
        on_save: callable = None,
        ai_client=None
    ):
        """
        Initialize the parallel POV view.

        Args:
            parent: Parent widget
            project_manager: ProjectManager instance
            on_save: Callback when content is saved
            ai_client: Optional AI client for rewriting suggestions
        """
        super().__init__(parent)
        self.pm = project_manager
        self.pov_manager = POVManager(project_manager)
        self.on_save = on_save
        self.ai_client = ai_client

        self._current_scene_index: Optional[int] = None
        self._original_content: str = ""
        self._sync_scroll = tk.BooleanVar(value=True)

        self._setup_ui()

    def _setup_ui(self):
        """Build the parallel view UI."""
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(toolbar, text="\u5e76\u884c\u89c6\u89d2\u5bf9\u6bd4").pack(side=tk.LEFT)

        # Sync scroll checkbox
        ttk.Checkbutton(
            toolbar,
            text="\u540c\u6b65\u6eda\u52a8",
            variable=self._sync_scroll
        ).pack(side=tk.LEFT, padx=(20, 0))

        # AI helper button
        if self.ai_client:
            ttk.Button(
                toolbar,
                text="\u91cd\u5199\u5efa\u8bae",
                command=self._request_rewrite
            ).pack(side=tk.RIGHT)

        # Main split view
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left pane (original)
        left_frame = ttk.LabelFrame(paned, text="\u539f\u59cb\u89c6\u89d2", padding="5")
        paned.add(left_frame, weight=1)

        self._build_pane(left_frame, "left")

        # Right pane (alternate)
        right_frame = ttk.LabelFrame(paned, text="\u66ff\u4ee3\u89c6\u89d2", padding="5")
        paned.add(right_frame, weight=1)

        self._build_pane(right_frame, "right")

    def _build_pane(self, parent, side: str):
        """Build a single pane with POV selector and text area."""
        # POV selector row
        selector_frame = ttk.Frame(parent)
        selector_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(selector_frame, text="POV:").pack(side=tk.LEFT)

        combo = ttk.Combobox(selector_frame, state="readonly", width=15)
        combo.pack(side=tk.LEFT, padx=(5, 0))

        # Store reference
        if side == "left":
            self.left_pov_combo = combo
        else:
            self.right_pov_combo = combo

        # Voice indicator
        voice_label = ttk.Label(selector_frame, text="", foreground="gray")
        voice_label.pack(side=tk.LEFT, padx=(10, 0))

        if side == "left":
            self.left_voice_label = voice_label
        else:
            self.right_voice_label = voice_label

        # Text area
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True)

        text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 11)
        )
        text.pack(fill=tk.BOTH, expand=True)

        if side == "left":
            self.left_text = text
            text.config(state=tk.DISABLED)  # Original is read-only
        else:
            self.right_text = text

        # Bind scroll sync
        text.vbar.bind("<B1-Motion>", lambda e, s=side: self._on_scroll(s))
        text.bind("<MouseWheel>", lambda e, s=side: self._on_scroll(s))

    def _on_scroll(self, source_side: str):
        """Handle scroll sync between panes."""
        if not self._sync_scroll.get():
            return

        # Get scroll position from source
        if source_side == "left":
            pos = self.left_text.yview()
            self.right_text.yview_moveto(pos[0])
        else:
            pos = self.right_text.yview()
            self.left_text.yview_moveto(pos[0])

    def load_scene(self, scene_index: int):
        """
        Load a scene for parallel POV editing.

        Args:
            scene_index: Index of the scene to load
        """
        scenes = self.pm.get_scenes()
        if scene_index < 0 or scene_index >= len(scenes):
            return

        self._current_scene_index = scene_index
        scene = scenes[scene_index]

        self._original_content = scene.get("content", "")

        # Populate POV selectors
        self._populate_pov_selectors()

        # Set current POV
        pov_uid = scene.get("pov_character", "")
        self._set_pov_selection(self.left_pov_combo, pov_uid)

        # Update voice label
        voice = scene.get("narrative_voice", "third_limited")
        self.left_voice_label.config(text=NarrativeVoice.get_display_name(voice))

        # Load content into left pane
        self.left_text.config(state=tk.NORMAL)
        self.left_text.delete("1.0", tk.END)
        self.left_text.insert("1.0", self._original_content)
        self.left_text.config(state=tk.DISABLED)

        # Clear right pane
        self.right_text.delete("1.0", tk.END)
        self.right_voice_label.config(text="")

    def _populate_pov_selectors(self):
        """Populate POV character dropdowns."""
        values = ["-- \u672a\u8bbe\u7f6e --"]
        self._pov_uid_map = {"-- \u672a\u8bbe\u7f6e --": ""}

        for char in self.pm.get_characters():
            name = char.get("name", "")
            uid = char.get("uid", "")
            if name and uid:
                values.append(name)
                self._pov_uid_map[name] = uid

        self.left_pov_combo["values"] = values
        self.right_pov_combo["values"] = values

    def _set_pov_selection(self, combo: ttk.Combobox, pov_uid: str):
        """Set POV combobox selection by UID."""
        if not pov_uid:
            combo.set("-- \u672a\u8bbe\u7f6e --")
            return

        for name, uid in self._pov_uid_map.items():
            if uid == pov_uid:
                combo.set(name)
                return

        combo.set("-- \u672a\u8bbe\u7f6e --")

    def _request_rewrite(self):
        """Request AI to rewrite scene from alternate POV."""
        if not self.ai_client:
            return

        # Get selected alternate POV
        alt_pov_name = self.right_pov_combo.get()
        alt_pov_uid = self._pov_uid_map.get(alt_pov_name, "")

        if not alt_pov_uid:
            return

        # Find character info
        alt_char = None
        for c in self.pm.get_characters():
            if c.get("uid") == alt_pov_uid:
                alt_char = c
                break

        if not alt_char:
            return

        # Get original POV character
        orig_pov_name = self.left_pov_combo.get()

        # Build prompt
        prompt = f"""请将以下场景从「{orig_pov_name}」的视角改写为「{alt_pov_name}」的视角。

角色「{alt_pov_name}」的特征：
{alt_char.get('description', '(无描述)')}

叙述风格：{alt_char.get('narrator_voice_style', '默认')}

原始内容：
{self._original_content}

请保持情节不变，但从新角色的视角重写，体现其性格和认知局限。"""

        # This would call AI client - for now just show placeholder
        self.right_text.delete("1.0", tk.END)
        self.right_text.insert("1.0", f"[AI \u91cd\u5199\u4e2d...]\n\n{prompt}")

    def get_alternate_content(self) -> str:
        """Get the alternate POV content."""
        return self.right_text.get("1.0", tk.END).strip()

    def get_alternate_pov(self) -> Optional[str]:
        """Get the selected alternate POV character UID."""
        selection = self.right_pov_combo.get()
        return self._pov_uid_map.get(selection)


class POVComparisonDialog(tk.Toplevel):
    """
    Dialog for comparing multiple POV versions of a scene.
    """

    def __init__(
        self,
        parent,
        project_manager,
        scene_index: int
    ):
        """
        Initialize the POV comparison dialog.

        Args:
            parent: Parent window
            project_manager: ProjectManager instance
            scene_index: Index of the scene to compare
        """
        super().__init__(parent)
        self.pm = project_manager
        self.scene_index = scene_index

        self.title("\u89c6\u89d2\u5bf9\u6bd4")
        self.geometry("900x600")

        self._setup_ui()

        self.transient(parent)

    def _setup_ui(self):
        """Build the dialog UI."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Parallel view
        self.parallel_view = ParallelPOVView(main_frame, self.pm)
        self.parallel_view.pack(fill=tk.BOTH, expand=True)

        # Load scene
        self.parallel_view.load_scene(self.scene_index)

        # Close button
        ttk.Button(main_frame, text="\u5173\u95ed", command=self.destroy).pack(
            side=tk.BOTTOM, pady=(10, 0)
        )


def show_pov_comparison(parent, project_manager, scene_index: int):
    """
    Convenience function to show POV comparison dialog.

    Args:
        parent: Parent window
        project_manager: ProjectManager instance
        scene_index: Index of scene to compare
    """
    dialog = POVComparisonDialog(parent, project_manager, scene_index)
    dialog.wait_window()
