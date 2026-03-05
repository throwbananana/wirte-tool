"""
Highlight Overlay Component

Creates a semi-transparent overlay that highlights specific UI elements,
creating a "spotlight" effect for guided tours and tutorials.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, Callable

from writer_app.core.guide_animation import get_animation_manager


class HighlightOverlay:
    """
    A spotlight overlay that highlights specific UI elements.

    Creates a semi-transparent mask over the entire window with a
    transparent "hole" around the target element, drawing attention
    to it during guided tours.

    Features:
    - Widget or region-based highlighting
    - Pulse and glow animations
    - Auto-tracking on window resize
    - Theme support

    Usage:
        overlay = HighlightOverlay(root, theme_manager)
        overlay.highlight_widget(button, animation="pulse")
        # Later...
        overlay.clear()
    """

    # Constants
    OVERLAY_ALPHA = 0.6
    HIGHLIGHT_PADDING = 8
    BORDER_WIDTH = 3
    CORNER_RADIUS = 8

    def __init__(self, root: tk.Tk, theme_manager=None):
        """
        Initialize the highlight overlay.

        Args:
            root: The root Tk window
            theme_manager: Optional ThemeManager for colors
        """
        self.root = root
        self.theme_manager = theme_manager

        self._overlay_window: Optional[tk.Toplevel] = None
        self._canvas: Optional[tk.Canvas] = None
        self._target_widget: Optional[tk.Widget] = None
        self._target_region: Optional[Tuple[int, int, int, int]] = None
        self._animation_id: Optional[str] = None
        self._bind_ids = []
        self._region_provider: Optional[Callable[[], Optional[Tuple[int, int, int, int]]]] = None
        self._escape_bind_id = None
        self._on_escape: Optional[Callable] = None

        # Colors
        self._overlay_color = "#000000"
        self._highlight_color = "#2196F3"
        self._update_colors()

        # Register theme listener
        if self.theme_manager:
            self.theme_manager.add_listener(self._update_colors)

    def _update_colors(self):
        """Update colors from theme."""
        if self.theme_manager:
            self._highlight_color = self.theme_manager.get_color("accent")
            # Overlay is always dark for contrast
            self._overlay_color = "#000000"

    def highlight_widget(
        self,
        widget: tk.Widget,
        padding: int = None,
        animation: str = "pulse",
        on_click_outside: Optional[Callable] = None
    ):
        """
        Highlight a specific widget with a spotlight effect.

        Args:
            widget: The widget to highlight
            padding: Extra padding around the widget (default: HIGHLIGHT_PADDING)
            animation: Animation type ("pulse", "glow", "none")
            on_click_outside: Callback when clicking outside the highlight
        """
        self._target_widget = widget
        self._target_region = None
        self._region_provider = None
        self._on_click_outside = on_click_outside

        # Get widget position
        self._show_overlay(animation, padding or self.HIGHLIGHT_PADDING)

        # Bind to window resize/move
        self._bind_tracking_events()

    def highlight_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        animation: str = "pulse",
        on_click_outside: Optional[Callable] = None,
        region_provider: Optional[Callable[[], Optional[Tuple[int, int, int, int]]]] = None
    ):
        """
        Highlight a specific rectangular region.

        Args:
            x, y: Top-left coordinates (screen coordinates)
            width, height: Size of the region
            animation: Animation type
            on_click_outside: Callback when clicking outside
        """
        self._target_widget = None
        self._target_region = (x, y, width, height)
        self._region_provider = region_provider
        self._on_click_outside = on_click_outside

        self._show_overlay(animation, 0)
        self._bind_tracking_events()

    def bind_escape(self, callback: Optional[Callable]):
        """Bind an Escape key handler to the overlay window."""
        self._on_escape = callback
        if self._overlay_window and self._on_escape:
            if self._escape_bind_id:
                try:
                    self._overlay_window.unbind("<Escape>", self._escape_bind_id)
                except tk.TclError:
                    pass
            self._escape_bind_id = self._overlay_window.bind(
                "<Escape>",
                lambda event: self._on_escape(),
                add="+"
            )

    def _show_overlay(self, animation: str, padding: int):
        """Create and show the overlay window."""
        # Clear existing overlay
        self.clear()

        # Create overlay window
        self._overlay_window = tk.Toplevel(self.root)
        self._overlay_window.overrideredirect(True)
        self._overlay_window.attributes("-topmost", True)

        # Set transparency (Windows)
        try:
            self._overlay_window.attributes("-alpha", self.OVERLAY_ALPHA)
        except tk.TclError:
            pass

        # Position to cover entire screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self._overlay_window.geometry(f"{screen_width}x{screen_height}+0+0")

        # Create canvas for drawing
        self._canvas = tk.Canvas(
            self._overlay_window,
            width=screen_width,
            height=screen_height,
            bg=self._overlay_color,
            highlightthickness=0
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Draw the spotlight effect
        self._draw_spotlight(padding)

        # Start animation
        self._start_animation(animation)

        # Bind click events
        self._canvas.bind("<Button-1>", self._on_canvas_click)
        if self._on_escape:
            self._escape_bind_id = self._overlay_window.bind(
                "<Escape>",
                lambda event: self._on_escape(),
                add="+"
            )

        # Make the highlighted area click-through
        self._setup_click_through()

    def _get_highlight_bounds(self, padding: int) -> Tuple[int, int, int, int]:
        """Get the bounds of the highlighted area (screen coordinates)."""
        if self._region_provider:
            try:
                region = self._region_provider()
            except tk.TclError:
                region = None
            if region:
                self._target_region = region
        if self._target_widget:
            try:
                self._target_widget.update_idletasks()
                x = self._target_widget.winfo_rootx() - padding
                y = self._target_widget.winfo_rooty() - padding
                w = self._target_widget.winfo_width() + padding * 2
                h = self._target_widget.winfo_height() + padding * 2
                return (x, y, w, h)
            except tk.TclError:
                return (0, 0, 100, 100)
        elif self._target_region:
            x, y, w, h = self._target_region
            return (x - padding, y - padding, w + padding * 2, h + padding * 2)
        return (0, 0, 100, 100)

    def _draw_spotlight(self, padding: int):
        """Draw the spotlight effect on the canvas."""
        if not self._canvas:
            return

        self._canvas.delete("all")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Get highlight bounds
        hx, hy, hw, hh = self._get_highlight_bounds(padding)

        # Draw four rectangles around the spotlight area
        # Top
        if hy > 0:
            self._canvas.create_rectangle(
                0, 0, screen_width, hy,
                fill=self._overlay_color,
                outline=""
            )
        # Bottom
        if hy + hh < screen_height:
            self._canvas.create_rectangle(
                0, hy + hh, screen_width, screen_height,
                fill=self._overlay_color,
                outline=""
            )
        # Left
        if hx > 0:
            self._canvas.create_rectangle(
                0, hy, hx, hy + hh,
                fill=self._overlay_color,
                outline=""
            )
        # Right
        if hx + hw < screen_width:
            self._canvas.create_rectangle(
                hx + hw, hy, screen_width, hy + hh,
                fill=self._overlay_color,
                outline=""
            )

        # Draw highlight border (rounded rectangle simulation)
        self._draw_rounded_border(hx, hy, hw, hh)

        # Store bounds for click detection
        self._highlight_bounds = (hx, hy, hx + hw, hy + hh)

    def _draw_rounded_border(self, x: int, y: int, w: int, h: int):
        """Draw a rounded border around the highlight area."""
        r = self.CORNER_RADIUS
        color = self._highlight_color
        width = self.BORDER_WIDTH

        # Create rounded rectangle using arcs and lines
        # Top-left corner
        self._canvas.create_arc(
            x, y, x + r * 2, y + r * 2,
            start=90, extent=90,
            style=tk.ARC, outline=color, width=width
        )
        # Top-right corner
        self._canvas.create_arc(
            x + w - r * 2, y, x + w, y + r * 2,
            start=0, extent=90,
            style=tk.ARC, outline=color, width=width
        )
        # Bottom-right corner
        self._canvas.create_arc(
            x + w - r * 2, y + h - r * 2, x + w, y + h,
            start=270, extent=90,
            style=tk.ARC, outline=color, width=width
        )
        # Bottom-left corner
        self._canvas.create_arc(
            x, y + h - r * 2, x + r * 2, y + h,
            start=180, extent=90,
            style=tk.ARC, outline=color, width=width
        )

        # Lines
        # Top
        self._canvas.create_line(
            x + r, y, x + w - r, y,
            fill=color, width=width
        )
        # Right
        self._canvas.create_line(
            x + w, y + r, x + w, y + h - r,
            fill=color, width=width
        )
        # Bottom
        self._canvas.create_line(
            x + r, y + h, x + w - r, y + h,
            fill=color, width=width
        )
        # Left
        self._canvas.create_line(
            x, y + r, x, y + h - r,
            fill=color, width=width
        )

    def _start_animation(self, animation: str):
        """Start the specified animation."""
        if animation == "none" or not self._canvas:
            return

        anim_manager = get_animation_manager(self.root)
        if not anim_manager:
            return

        hx, hy, hw, hh = self._get_highlight_bounds(self.HIGHLIGHT_PADDING)

        if animation == "pulse":
            self._animation_id = anim_manager.glow_effect(
                self._canvas,
                hx, hy, hw, hh,
                self._highlight_color,
                cycles=0  # Infinite
            )
        elif animation == "glow":
            self._animation_id = anim_manager.glow_effect(
                self._canvas,
                hx, hy, hw, hh,
                self._highlight_color,
                duration_ms=2000,
                cycles=0
            )

    def _setup_click_through(self):
        """Make the highlighted area interactive (click-through)."""
        # On Windows, we can't truly make regions click-through
        # So we'll hide the overlay temporarily when clicking in the highlight area
        pass

    def _on_canvas_click(self, event):
        """Handle clicks on the overlay."""
        if not hasattr(self, "_highlight_bounds"):
            return

        x1, y1, x2, y2 = self._highlight_bounds
        click_x = event.x_root
        click_y = event.y_root

        if x1 <= click_x <= x2 and y1 <= click_y <= y2:
            # Click inside highlight - temporarily hide overlay to pass through
            if self._overlay_window:
                self._overlay_window.withdraw()
                self.root.after(100, self._restore_overlay)
                # Simulate click on target
                if self._target_widget:
                    try:
                        self._target_widget.event_generate("<Button-1>")
                    except tk.TclError:
                        pass
        else:
            # Click outside highlight
            if hasattr(self, "_on_click_outside") and self._on_click_outside:
                self._on_click_outside()

    def _restore_overlay(self):
        """Restore the overlay after click-through."""
        if self._overlay_window:
            try:
                self._overlay_window.deiconify()
            except tk.TclError:
                pass

    def _bind_tracking_events(self):
        """Bind events to track window changes."""
        # Track window move/resize
        bind_id = self.root.bind("<Configure>", self._on_window_configure, add="+")
        self._bind_ids.append(("root", bind_id))

    def _on_window_configure(self, event):
        """Handle window resize/move - update overlay."""
        if self._overlay_window and (self._target_widget or self._region_provider or self._target_region):
            self.root.after(50, lambda: self._refresh_overlay())

    def _refresh_overlay(self):
        """Refresh the overlay position."""
        if not self._overlay_window or not self._canvas:
            return

        # Stop current animation
        if self._animation_id:
            anim_manager = get_animation_manager()
            if anim_manager:
                anim_manager.stop_animation(self._animation_id)
            self._animation_id = None

        # Redraw spotlight
        self._draw_spotlight(self.HIGHLIGHT_PADDING)

        # Restart animation
        self._start_animation("pulse")

    def clear(self):
        """Remove the overlay and clean up."""
        # Stop animation
        if self._animation_id:
            anim_manager = get_animation_manager()
            if anim_manager:
                anim_manager.stop_animation(self._animation_id)
            self._animation_id = None

        # Unbind events
        for widget_type, bind_id in self._bind_ids:
            try:
                if widget_type == "root":
                    self.root.unbind("<Configure>", bind_id)
            except tk.TclError:
                pass
        self._bind_ids = []

        # Destroy overlay window
        if self._overlay_window:
            try:
                if self._escape_bind_id:
                    self._overlay_window.unbind("<Escape>", self._escape_bind_id)
                self._overlay_window.destroy()
            except tk.TclError:
                pass
            self._overlay_window = None
            self._canvas = None
            self._escape_bind_id = None

        self._target_widget = None
        self._target_region = None
        self._region_provider = None

    def is_active(self) -> bool:
        """Check if the overlay is currently active."""
        return self._overlay_window is not None

    def update_target(self, widget: tk.Widget = None, region: Tuple[int, int, int, int] = None):
        """
        Update the highlight target without recreating the overlay.

        Args:
            widget: New target widget (or None to keep current)
            region: New target region (or None to keep current)
        """
        if widget:
            self._target_widget = widget
            self._target_region = None
        elif region:
            self._target_widget = None
            self._target_region = region

        self._refresh_overlay()

    def destroy(self):
        """Clean up all resources."""
        self.clear()
        if self.theme_manager:
            self.theme_manager.remove_listener(self._update_colors)


class SpotlightSequence:
    """
    Manages a sequence of spotlight highlights for multi-step tutorials.

    Usage:
        seq = SpotlightSequence(root, theme_manager)
        seq.add_step(widget1, "First step description")
        seq.add_step(widget2, "Second step")
        seq.start()
    """

    def __init__(self, root: tk.Tk, theme_manager=None):
        self.root = root
        self.theme_manager = theme_manager
        self._overlay = HighlightOverlay(root, theme_manager)
        self._steps = []
        self._current_step = -1
        self._on_complete: Optional[Callable] = None

    def add_step(
        self,
        widget: tk.Widget,
        description: str = "",
        animation: str = "pulse"
    ):
        """Add a step to the sequence."""
        self._steps.append({
            "widget": widget,
            "description": description,
            "animation": animation
        })

    def start(self, on_complete: Optional[Callable] = None):
        """Start the spotlight sequence."""
        self._on_complete = on_complete
        self._current_step = -1
        self.next_step()

    def next_step(self):
        """Move to the next step in the sequence."""
        self._current_step += 1

        if self._current_step >= len(self._steps):
            self._complete()
            return

        step = self._steps[self._current_step]
        self._overlay.highlight_widget(
            step["widget"],
            animation=step["animation"],
            on_click_outside=self.next_step
        )

    def previous_step(self):
        """Move to the previous step."""
        if self._current_step > 0:
            self._current_step -= 2
            self.next_step()

    def skip(self):
        """Skip the entire sequence."""
        self._complete()

    def _complete(self):
        """Complete the sequence."""
        self._overlay.clear()
        if self._on_complete:
            self._on_complete()

    def destroy(self):
        """Clean up resources."""
        self._overlay.destroy()
