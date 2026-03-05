"""
POV Timeline View - Visual timeline showing POV transitions across scenes.

Provides:
- Horizontal timeline with color-coded bars for each POV character
- Vertical lines for scene boundaries
- Reliability gradient display
- Hover tooltips showing POV details
- Click to jump to scene

Usage:
    timeline = POVTimelineView(parent, project_manager, on_scene_click)
    timeline.pack()
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, List, Callable, Tuple
import logging
import colorsys

from writer_app.core.pov_manager import POVManager, NarrativeVoice

logger = logging.getLogger(__name__)


def generate_color_for_index(index: int, total: int = 8) -> str:
    """Generate a distinct color for a given index."""
    hue = (index * (360 / total)) % 360
    rgb = colorsys.hsv_to_rgb(hue / 360, 0.6, 0.85)
    return f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"


class POVTimelineView(ttk.Frame):
    """
    Visual timeline showing POV transitions across scenes.

    Features:
    - Color-coded bars for each POV character
    - Scene boundary markers
    - Reliability gradient (darker = less reliable)
    - Hover tooltips
    - Click to jump to scene
    """

    def __init__(
        self,
        parent,
        project_manager,
        on_scene_click: Callable[[int], None] = None,
        height: int = 100
    ):
        """
        Initialize the POV timeline view.

        Args:
            parent: Parent widget
            project_manager: ProjectManager instance
            on_scene_click: Callback when a scene bar is clicked
            height: Height of the timeline canvas
        """
        super().__init__(parent)
        self.pm = project_manager
        self.pov_manager = POVManager(project_manager)
        self.on_scene_click = on_scene_click
        self._height = height

        self._char_colors: Dict[str, str] = {}
        self._scene_rects: Dict[int, int] = {}  # canvas_id -> scene_index

        self._setup_ui()

    def _setup_ui(self):
        """Build the timeline UI."""
        # Header with legend
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(header, text="POV \u65f6\u95f4\u7ebf", font=("", 10, "bold")).pack(side=tk.LEFT)

        # Legend frame (will be populated on refresh)
        self.legend_frame = ttk.Frame(header)
        self.legend_frame.pack(side=tk.RIGHT)

        # Canvas with scrollbar
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            height=self._height,
            bg="white",
            highlightthickness=1,
            highlightbackground="#ddd"
        )
        self.canvas.pack(side=tk.TOP, fill=tk.X, expand=True)

        self.h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(xscrollcommand=self.h_scrollbar.set)

        # Bind events
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)

        # Tooltip
        self._tooltip = None

    def refresh(self):
        """Refresh the timeline display."""
        self.canvas.delete("all")
        self._scene_rects.clear()

        scenes = self.pm.get_scenes()
        if not scenes:
            return

        # Assign colors to POV characters
        self._assign_colors()

        # Calculate dimensions
        bar_width = 50  # Width per scene
        total_width = len(scenes) * bar_width + 40  # Extra padding
        bar_height = self._height - 40  # Leave room for labels

        self.canvas.config(scrollregion=(0, 0, total_width, self._height))

        # Draw scene bars
        for i, scene in enumerate(scenes):
            x1 = 20 + i * bar_width
            x2 = x1 + bar_width - 4
            y1 = 20
            y2 = y1 + bar_height

            pov_uid = scene.get("pov_character", "")
            reliability = scene.get("narrator_reliability", 1.0)

            # Get color for POV
            if pov_uid:
                base_color = self._char_colors.get(pov_uid, "#cccccc")
            else:
                base_color = "#eeeeee"

            # Adjust color for reliability (darker = less reliable)
            fill_color = self._adjust_color_for_reliability(base_color, reliability)

            # Draw rectangle
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=fill_color,
                outline="#999999",
                width=1,
                tags=("scene", f"scene_{i}")
            )
            self._scene_rects[rect_id] = i

            # Draw scene number
            self.canvas.create_text(
                (x1 + x2) / 2, y2 + 10,
                text=str(i + 1),
                font=("", 8),
                tags=("label",)
            )

            # Draw voice indicator (small icon at top)
            voice = scene.get("narrative_voice", "third_limited")
            voice_symbol = self._get_voice_symbol(voice)
            self.canvas.create_text(
                (x1 + x2) / 2, y1 - 8,
                text=voice_symbol,
                font=("", 8),
                fill="#666666",
                tags=("voice",)
            )

        # Update legend
        self._update_legend()

    def _assign_colors(self):
        """Assign colors to POV characters."""
        self._char_colors.clear()

        # Get unique POV characters
        pov_uids = set()
        for scene in self.pm.get_scenes():
            pov = scene.get("pov_character")
            if pov:
                pov_uids.add(pov)

        # Assign colors
        for i, uid in enumerate(sorted(pov_uids)):
            self._char_colors[uid] = generate_color_for_index(i, max(len(pov_uids), 8))

    def _adjust_color_for_reliability(self, hex_color: str, reliability: float) -> str:
        """Adjust color darkness based on reliability."""
        # Parse hex color
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)

        # Convert to HSV, adjust value based on reliability
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

        # Lower reliability = darker (lower value)
        # Map reliability 0-1 to value modifier 0.5-1.0
        v_modifier = 0.5 + (reliability * 0.5)
        v = v * v_modifier

        # Convert back to RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)

        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def _get_voice_symbol(self, voice: str) -> str:
        """Get symbol for narrative voice."""
        symbols = {
            "first": "\u2460",        # Circled 1
            "second": "\u2461",       # Circled 2
            "third_limited": "\u2462", # Circled 3
            "third_omniscient": "\u2299"  # Circled dot
        }
        return symbols.get(voice, "\u25cb")

    def _update_legend(self):
        """Update the color legend."""
        # Clear existing legend
        for widget in self.legend_frame.winfo_children():
            widget.destroy()

        # Build character name map
        char_names = {}
        for char in self.pm.get_characters():
            char_names[char.get("uid")] = char.get("name", "")

        # Add legend items
        for uid, color in self._char_colors.items():
            name = char_names.get(uid, "???")

            item_frame = ttk.Frame(self.legend_frame)
            item_frame.pack(side=tk.LEFT, padx=(10, 0))

            # Color swatch
            swatch = tk.Label(
                item_frame,
                bg=color,
                width=2,
                height=1
            )
            swatch.pack(side=tk.LEFT)

            # Name
            ttk.Label(item_frame, text=name, font=("", 9)).pack(side=tk.LEFT, padx=(2, 0))

        # Add "no POV" indicator
        if any(not s.get("pov_character") for s in self.pm.get_scenes()):
            item_frame = ttk.Frame(self.legend_frame)
            item_frame.pack(side=tk.LEFT, padx=(10, 0))

            swatch = tk.Label(item_frame, bg="#eeeeee", width=2, height=1)
            swatch.pack(side=tk.LEFT)

            ttk.Label(item_frame, text="\u672a\u8bbe\u7f6e", font=("", 9), foreground="gray").pack(
                side=tk.LEFT, padx=(2, 0)
            )

    def _on_click(self, event):
        """Handle click on timeline."""
        # Find clicked item
        item = self.canvas.find_closest(event.x, event.y)
        if item:
            scene_idx = self._scene_rects.get(item[0])
            if scene_idx is not None and self.on_scene_click:
                self.on_scene_click(scene_idx)

    def _on_motion(self, event):
        """Handle mouse motion for tooltip."""
        # Find item under cursor
        item = self.canvas.find_closest(event.x, event.y)
        if item:
            scene_idx = self._scene_rects.get(item[0])
            if scene_idx is not None:
                self._show_tooltip(event, scene_idx)
                return

        self._hide_tooltip()

    def _on_leave(self, event):
        """Handle mouse leaving canvas."""
        self._hide_tooltip()

    def _show_tooltip(self, event, scene_idx: int):
        """Show tooltip for a scene."""
        scenes = self.pm.get_scenes()
        if scene_idx < 0 or scene_idx >= len(scenes):
            return

        scene = scenes[scene_idx]

        # Build tooltip text
        lines = [
            f"\u573a\u666f {scene_idx + 1}: {scene.get('name', '')}",
        ]

        pov_uid = scene.get("pov_character")
        if pov_uid:
            pov_name = "???"
            for char in self.pm.get_characters():
                if char.get("uid") == pov_uid:
                    pov_name = char.get("name", "???")
                    break
            lines.append(f"POV: {pov_name}")

        voice = scene.get("narrative_voice", "third_limited")
        lines.append(f"\u53d9\u8ff0: {NarrativeVoice.get_display_name(voice)}")

        reliability = scene.get("narrator_reliability", 1.0)
        lines.append(f"\u53ef\u9760\u5ea6: {int(reliability * 100)}%")

        tooltip_text = "\n".join(lines)

        # Create or update tooltip
        if self._tooltip:
            self._tooltip.destroy()

        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)

        label = ttk.Label(
            self._tooltip,
            text=tooltip_text,
            background="#ffffcc",
            relief="solid",
            borderwidth=1,
            padding=(5, 3)
        )
        label.pack()

        # Position tooltip
        x = self.winfo_rootx() + event.x + 10
        y = self.winfo_rooty() + event.y + 10
        self._tooltip.wm_geometry(f"+{x}+{y}")

    def _hide_tooltip(self):
        """Hide the tooltip."""
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    def highlight_scene(self, scene_idx: int):
        """Highlight a specific scene on the timeline."""
        # Reset all outlines
        for rect_id in self._scene_rects:
            self.canvas.itemconfig(rect_id, outline="#999999", width=1)

        # Find and highlight the target scene
        for rect_id, idx in self._scene_rects.items():
            if idx == scene_idx:
                self.canvas.itemconfig(rect_id, outline="#ff0000", width=2)
                # Scroll to show it
                coords = self.canvas.coords(rect_id)
                if coords:
                    self.canvas.xview_moveto(coords[0] / self.canvas.winfo_width())
                break


class POVTimelinePanel(ttk.Frame):
    """
    Full POV timeline panel with statistics and controls.
    """

    def __init__(
        self,
        parent,
        project_manager,
        on_scene_click: Callable[[int], None] = None
    ):
        """
        Initialize the POV timeline panel.

        Args:
            parent: Parent widget
            project_manager: ProjectManager instance
            on_scene_click: Callback when scene is clicked
        """
        super().__init__(parent)
        self.pm = project_manager
        self.pov_manager = POVManager(project_manager)
        self.on_scene_click = on_scene_click

        self._setup_ui()

    def _setup_ui(self):
        """Build the panel UI."""
        # Statistics bar
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, pady=(0, 5))

        self.stats_label = ttk.Label(stats_frame, text="")
        self.stats_label.pack(side=tk.LEFT)

        # Conflict warning
        self.conflict_label = ttk.Label(stats_frame, text="", foreground="orange")
        self.conflict_label.pack(side=tk.RIGHT)

        # Timeline view
        self.timeline = POVTimelineView(
            self,
            self.pm,
            on_scene_click=self.on_scene_click,
            height=80
        )
        self.timeline.pack(fill=tk.X)

    def refresh(self):
        """Refresh the panel."""
        # Update timeline
        self.timeline.refresh()

        # Update statistics
        stats = self.pov_manager.get_pov_statistics()
        self.stats_label.config(
            text=f"{stats['scenes_with_pov']}/{stats['total_scenes']} \u573a\u666f\u5df2\u8bbe\u7f6ePOV | "
                 f"\u5e73\u5747\u53ef\u9760\u5ea6: {int(stats['avg_reliability'] * 100)}%"
        )

        # Check for conflicts
        conflicts = self.pov_manager.detect_perspective_conflicts()
        if conflicts:
            errors = sum(1 for c in conflicts if c.severity == "error")
            warnings = sum(1 for c in conflicts if c.severity == "warning")
            self.conflict_label.config(
                text=f"\u26a0 {errors} \u9519\u8bef, {warnings} \u8b66\u544a"
            )
        else:
            self.conflict_label.config(text="")

    def highlight_scene(self, scene_idx: int):
        """Highlight a scene on the timeline."""
        self.timeline.highlight_scene(scene_idx)
