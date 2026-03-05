"""
Guide Animation Utilities

Provides animation helpers for the guide system using Tkinter's after() mechanism.
Supports pulse, fade, bounce, and glow effects.
"""

import tkinter as tk
from typing import Optional, Callable, Dict, Any
import uuid


class GuideAnimationManager:
    """
    Manages animations for the guide system.

    Uses Tkinter's after() mechanism for smooth animations.
    Tracks active animations for proper cleanup.

    Usage:
        manager = GuideAnimationManager(root)
        anim_id = manager.pulse_border(widget, "#2196F3")
        # Later...
        manager.stop_animation(anim_id)
    """

    # Animation timing constants
    PULSE_DURATION_MS = 1500
    PULSE_STEPS = 30
    FADE_DURATION_MS = 300
    FADE_STEPS = 15
    BOUNCE_DURATION_MS = 500
    BOUNCE_STEPS = 20
    GLOW_DURATION_MS = 1000
    GLOW_STEPS = 25

    def __init__(self, root: tk.Tk):
        """
        Initialize the animation manager.

        Args:
            root: The root Tk window for scheduling animations
        """
        self.root = root
        self._active_animations: Dict[str, Dict[str, Any]] = {}

    def pulse_border(
        self,
        widget: tk.Widget,
        color: str,
        duration_ms: int = None,
        cycles: int = 3,
        on_complete: Optional[Callable] = None
    ) -> str:
        """
        Animate a widget's border with a pulsing effect.

        Args:
            widget: The widget to animate
            color: The pulse color (hex)
            duration_ms: Duration of one pulse cycle
            cycles: Number of pulse cycles (0 = infinite)
            on_complete: Callback when animation completes

        Returns:
            Animation ID for stopping the animation
        """
        duration = duration_ms or self.PULSE_DURATION_MS
        anim_id = self._generate_id()

        state = {
            "widget": widget,
            "color": color,
            "step": 0,
            "cycles_done": 0,
            "max_cycles": cycles,
            "duration": duration,
            "on_complete": on_complete,
            "after_id": None,
            "original_style": {}
        }

        # Store original style
        try:
            if hasattr(widget, "cget"):
                state["original_style"]["highlightbackground"] = widget.cget("highlightbackground")
                state["original_style"]["highlightthickness"] = widget.cget("highlightthickness")
        except tk.TclError:
            pass

        self._active_animations[anim_id] = state
        self._do_pulse_step(anim_id)
        return anim_id

    def _do_pulse_step(self, anim_id: str):
        """Execute one step of the pulse animation."""
        if anim_id not in self._active_animations:
            return

        state = self._active_animations[anim_id]
        widget = state["widget"]
        step = state["step"]
        total_steps = self.PULSE_STEPS

        # Calculate intensity (0 -> 1 -> 0)
        progress = step / total_steps
        if progress < 0.5:
            intensity = progress * 2
        else:
            intensity = 2 - progress * 2

        # Apply border effect
        try:
            thickness = int(2 + intensity * 4)
            widget.configure(
                highlightbackground=state["color"],
                highlightthickness=thickness
            )
        except tk.TclError:
            self.stop_animation(anim_id)
            return

        # Next step
        state["step"] = (step + 1) % total_steps

        if step == 0 and state["step"] != 0:
            # Completed one cycle
            state["cycles_done"] += 1
            if state["max_cycles"] > 0 and state["cycles_done"] >= state["max_cycles"]:
                self.stop_animation(anim_id)
                if state["on_complete"]:
                    state["on_complete"]()
                return

        # Schedule next step
        interval = state["duration"] // total_steps
        state["after_id"] = self.root.after(interval, lambda: self._do_pulse_step(anim_id))

    def glow_effect(
        self,
        canvas: tk.Canvas,
        x: int,
        y: int,
        width: int,
        height: int,
        color: str,
        duration_ms: int = None,
        cycles: int = 0,
        on_complete: Optional[Callable] = None
    ) -> str:
        """
        Create a glowing rectangle effect on a canvas.

        Args:
            canvas: The canvas to draw on
            x, y: Top-left coordinates
            width, height: Dimensions of the glow area
            color: Glow color (hex)
            duration_ms: Duration of one glow cycle
            cycles: Number of cycles (0 = infinite)
            on_complete: Callback when animation completes

        Returns:
            Animation ID for stopping the animation
        """
        duration = duration_ms or self.GLOW_DURATION_MS
        anim_id = self._generate_id()

        state = {
            "canvas": canvas,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "color": color,
            "step": 0,
            "cycles_done": 0,
            "max_cycles": cycles,
            "duration": duration,
            "on_complete": on_complete,
            "after_id": None,
            "items": []
        }

        self._active_animations[anim_id] = state
        self._do_glow_step(anim_id)
        return anim_id

    def _do_glow_step(self, anim_id: str):
        """Execute one step of the glow animation."""
        if anim_id not in self._active_animations:
            return

        state = self._active_animations[anim_id]
        canvas = state["canvas"]
        step = state["step"]
        total_steps = self.GLOW_STEPS

        # Clear previous items
        for item in state["items"]:
            try:
                canvas.delete(item)
            except tk.TclError:
                pass
        state["items"] = []

        # Calculate glow intensity
        progress = step / total_steps
        if progress < 0.5:
            intensity = progress * 2
        else:
            intensity = 2 - progress * 2

        # Draw glow rings
        x, y, w, h = state["x"], state["y"], state["width"], state["height"]
        color = state["color"]

        for i in range(3):
            offset = int((1 - intensity) * 5 * (i + 1))
            alpha_hex = hex(int(255 * intensity * (1 - i * 0.3)))[2:].zfill(2)

            try:
                item = canvas.create_rectangle(
                    x - offset, y - offset,
                    x + w + offset, y + h + offset,
                    outline=color,
                    width=2 - i * 0.5,
                    tags=("glow_effect", f"glow_{anim_id}")
                )
                state["items"].append(item)
            except tk.TclError:
                self.stop_animation(anim_id)
                return

        # Next step
        state["step"] = (step + 1) % total_steps

        if step == 0 and state["step"] != 0:
            state["cycles_done"] += 1
            if state["max_cycles"] > 0 and state["cycles_done"] >= state["max_cycles"]:
                self.stop_animation(anim_id)
                if state["on_complete"]:
                    state["on_complete"]()
                return

        interval = state["duration"] // total_steps
        state["after_id"] = self.root.after(interval, lambda: self._do_glow_step(anim_id))

    def fade_in(
        self,
        toplevel: tk.Toplevel,
        duration_ms: int = None,
        on_complete: Optional[Callable] = None
    ) -> str:
        """
        Fade in a Toplevel window.

        Args:
            toplevel: The Toplevel window to fade in
            duration_ms: Duration of the fade
            on_complete: Callback when animation completes

        Returns:
            Animation ID for stopping the animation
        """
        duration = duration_ms or self.FADE_DURATION_MS
        anim_id = self._generate_id()

        state = {
            "toplevel": toplevel,
            "step": 0,
            "duration": duration,
            "on_complete": on_complete,
            "after_id": None,
            "direction": "in"
        }

        # Start fully transparent
        try:
            toplevel.attributes("-alpha", 0.0)
        except tk.TclError:
            pass

        self._active_animations[anim_id] = state
        self._do_fade_step(anim_id)
        return anim_id

    def fade_out(
        self,
        toplevel: tk.Toplevel,
        duration_ms: int = None,
        on_complete: Optional[Callable] = None
    ) -> str:
        """
        Fade out a Toplevel window.

        Args:
            toplevel: The Toplevel window to fade out
            duration_ms: Duration of the fade
            on_complete: Callback when animation completes

        Returns:
            Animation ID for stopping the animation
        """
        duration = duration_ms or self.FADE_DURATION_MS
        anim_id = self._generate_id()

        state = {
            "toplevel": toplevel,
            "step": 0,
            "duration": duration,
            "on_complete": on_complete,
            "after_id": None,
            "direction": "out"
        }

        self._active_animations[anim_id] = state
        self._do_fade_step(anim_id)
        return anim_id

    def _do_fade_step(self, anim_id: str):
        """Execute one step of the fade animation."""
        if anim_id not in self._active_animations:
            return

        state = self._active_animations[anim_id]
        toplevel = state["toplevel"]
        step = state["step"]
        total_steps = self.FADE_STEPS
        direction = state["direction"]

        # Calculate alpha
        progress = step / total_steps
        if direction == "in":
            alpha = progress
        else:
            alpha = 1.0 - progress

        try:
            toplevel.attributes("-alpha", alpha)
        except tk.TclError:
            self.stop_animation(anim_id)
            return

        state["step"] += 1

        if state["step"] >= total_steps:
            self.stop_animation(anim_id)
            if state["on_complete"]:
                state["on_complete"]()
            return

        interval = state["duration"] // total_steps
        state["after_id"] = self.root.after(interval, lambda: self._do_fade_step(anim_id))

    def bounce(
        self,
        widget: tk.Widget,
        distance: int = 10,
        duration_ms: int = None,
        cycles: int = 2,
        on_complete: Optional[Callable] = None
    ) -> str:
        """
        Bounce a widget up and down for attention.

        Args:
            widget: The widget to bounce
            distance: Maximum bounce distance in pixels
            duration_ms: Duration of one bounce cycle
            cycles: Number of bounce cycles
            on_complete: Callback when animation completes

        Returns:
            Animation ID for stopping the animation
        """
        duration = duration_ms or self.BOUNCE_DURATION_MS
        anim_id = self._generate_id()

        # Get original position
        original_y = widget.winfo_y()

        state = {
            "widget": widget,
            "original_y": original_y,
            "distance": distance,
            "step": 0,
            "cycles_done": 0,
            "max_cycles": cycles,
            "duration": duration,
            "on_complete": on_complete,
            "after_id": None
        }

        self._active_animations[anim_id] = state
        self._do_bounce_step(anim_id)
        return anim_id

    def _do_bounce_step(self, anim_id: str):
        """Execute one step of the bounce animation."""
        if anim_id not in self._active_animations:
            return

        state = self._active_animations[anim_id]
        widget = state["widget"]
        step = state["step"]
        total_steps = self.BOUNCE_STEPS

        # Calculate bounce offset using sine wave
        import math
        progress = step / total_steps
        offset = int(-state["distance"] * math.sin(progress * math.pi))

        try:
            widget.place(y=state["original_y"] + offset)
        except tk.TclError:
            self.stop_animation(anim_id)
            return

        state["step"] = (step + 1) % total_steps

        if step == 0 and state["step"] != 0:
            state["cycles_done"] += 1
            if state["cycles_done"] >= state["max_cycles"]:
                # Reset to original position
                try:
                    widget.place(y=state["original_y"])
                except tk.TclError:
                    pass
                self.stop_animation(anim_id)
                if state["on_complete"]:
                    state["on_complete"]()
                return

        interval = state["duration"] // total_steps
        state["after_id"] = self.root.after(interval, lambda: self._do_bounce_step(anim_id))

    def attention_ring(
        self,
        canvas: tk.Canvas,
        x: int,
        y: int,
        radius: int,
        color: str,
        cycles: int = 3,
        on_complete: Optional[Callable] = None
    ) -> str:
        """
        Create an expanding ring animation for drawing attention.

        Args:
            canvas: The canvas to draw on
            x, y: Center coordinates
            radius: Maximum radius of the ring
            color: Ring color
            cycles: Number of animation cycles
            on_complete: Callback when animation completes

        Returns:
            Animation ID
        """
        anim_id = self._generate_id()
        total_steps = 30

        state = {
            "canvas": canvas,
            "x": x,
            "y": y,
            "max_radius": radius,
            "color": color,
            "step": 0,
            "cycles_done": 0,
            "max_cycles": cycles,
            "on_complete": on_complete,
            "after_id": None,
            "item": None
        }

        self._active_animations[anim_id] = state
        self._do_attention_ring_step(anim_id, total_steps)
        return anim_id

    def _do_attention_ring_step(self, anim_id: str, total_steps: int):
        """Execute one step of the attention ring animation."""
        if anim_id not in self._active_animations:
            return

        state = self._active_animations[anim_id]
        canvas = state["canvas"]
        step = state["step"]

        # Clear previous item
        if state["item"]:
            try:
                canvas.delete(state["item"])
            except tk.TclError:
                pass

        # Calculate current radius and opacity
        progress = step / total_steps
        current_radius = int(state["max_radius"] * progress)
        opacity = 1.0 - progress

        x, y = state["x"], state["y"]

        try:
            # Draw ring (as oval outline)
            state["item"] = canvas.create_oval(
                x - current_radius, y - current_radius,
                x + current_radius, y + current_radius,
                outline=state["color"],
                width=max(1, int(3 * opacity)),
                tags=("attention_ring", f"ring_{anim_id}")
            )
        except tk.TclError:
            self.stop_animation(anim_id)
            return

        state["step"] = (step + 1) % total_steps

        if step == 0 and state["step"] != 0:
            state["cycles_done"] += 1
            if state["cycles_done"] >= state["max_cycles"]:
                if state["item"]:
                    try:
                        canvas.delete(state["item"])
                    except tk.TclError:
                        pass
                self.stop_animation(anim_id)
                if state["on_complete"]:
                    state["on_complete"]()
                return

        interval = 1000 // total_steps
        state["after_id"] = self.root.after(interval, lambda: self._do_attention_ring_step(anim_id, total_steps))

    def stop_animation(self, anim_id: str):
        """
        Stop a specific animation.

        Args:
            anim_id: The animation ID to stop
        """
        if anim_id not in self._active_animations:
            return

        state = self._active_animations[anim_id]

        # Cancel scheduled callback
        if state.get("after_id"):
            try:
                self.root.after_cancel(state["after_id"])
            except tk.TclError:
                pass

        # Restore original state if applicable
        if "original_style" in state:
            widget = state.get("widget")
            if widget:
                try:
                    for key, value in state["original_style"].items():
                        if value is not None:
                            widget.configure(**{key: value})
                except tk.TclError:
                    pass

        # Clean up canvas items
        if "items" in state:
            canvas = state.get("canvas")
            if canvas:
                for item in state["items"]:
                    try:
                        canvas.delete(item)
                    except tk.TclError:
                        pass

        del self._active_animations[anim_id]

    def stop_all(self):
        """Stop all active animations."""
        for anim_id in list(self._active_animations.keys()):
            self.stop_animation(anim_id)

    def is_animating(self, anim_id: str) -> bool:
        """Check if an animation is currently active."""
        return anim_id in self._active_animations

    def _generate_id(self) -> str:
        """Generate a unique animation ID."""
        return f"anim_{uuid.uuid4().hex[:8]}"


# Singleton instance
_animation_manager: Optional[GuideAnimationManager] = None


def get_animation_manager(root: tk.Tk = None) -> Optional[GuideAnimationManager]:
    """
    Get the global animation manager instance.

    Args:
        root: The root Tk window (required for first call)

    Returns:
        The GuideAnimationManager instance
    """
    global _animation_manager
    if _animation_manager is None and root is not None:
        _animation_manager = GuideAnimationManager(root)
    return _animation_manager


def shutdown_animation_manager():
    """Stop all animations and cleanup."""
    global _animation_manager
    if _animation_manager:
        _animation_manager.stop_all()
        _animation_manager = None
