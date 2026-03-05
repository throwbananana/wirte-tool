"""
Toast Notification Component - 非阻塞提示组件

用于显示短暂的通知消息，不会阻塞用户操作。
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional


class Toast:
    """Non-blocking toast notification that auto-dismisses."""

    def __init__(
        self,
        parent,
        message: str,
        duration: int = 2000,  # milliseconds
        toast_type: str = "info",  # info, success, warning, error
        position: str = "bottom-right",  # bottom-right, bottom-left, top-right, top-left, center
    ):
        self.parent = parent
        self.message = message
        self.duration = duration
        self.toast_type = toast_type
        self.position = position
        self.toast_window: Optional[tk.Toplevel] = None
        self._after_id: Optional[str] = None

    def show(self):
        """Show the toast notification."""
        if self.toast_window:
            self.toast_window.destroy()

        # Create toast window
        self.toast_window = tk.Toplevel(self.parent)
        self.toast_window.wm_overrideredirect(True)
        self.toast_window.attributes("-topmost", True)

        # Configure colors based on type
        colors = {
            "info": ("#1976D2", "#FFFFFF"),
            "success": ("#2E7D32", "#FFFFFF"),
            "warning": ("#F57C00", "#000000"),
            "error": ("#D32F2F", "#FFFFFF"),
        }
        bg_color, fg_color = colors.get(self.toast_type, colors["info"])

        # Create content frame with rounded corners effect
        frame = tk.Frame(
            self.toast_window,
            bg=bg_color,
            padx=15,
            pady=10,
        )
        frame.pack()

        # Icon based on type
        icons = {
            "info": "ℹ️",
            "success": "✓",
            "warning": "⚠",
            "error": "✕",
        }
        icon = icons.get(self.toast_type, "")

        # Message label
        label = tk.Label(
            frame,
            text=f"{icon}  {self.message}",
            bg=bg_color,
            fg=fg_color,
            font=("Microsoft YaHei UI", 10),
            padx=10,
            pady=5,
        )
        label.pack()

        # Position the toast
        self._position_toast()

        # Set opacity (if supported)
        try:
            self.toast_window.attributes("-alpha", 0.95)
        except Exception:
            pass

        # Schedule auto-dismiss
        self._after_id = self.parent.after(self.duration, self._fade_out)

        # Click to dismiss
        self.toast_window.bind("<Button-1>", lambda e: self.dismiss())
        label.bind("<Button-1>", lambda e: self.dismiss())

    def _position_toast(self):
        """Position the toast based on the specified position."""
        self.toast_window.update_idletasks()

        # Get toast dimensions
        toast_width = self.toast_window.winfo_width()
        toast_height = self.toast_window.winfo_height()

        # Get parent window position and dimensions
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        # Calculate position
        margin = 20

        if self.position == "bottom-right":
            x = parent_x + parent_width - toast_width - margin
            y = parent_y + parent_height - toast_height - margin
        elif self.position == "bottom-left":
            x = parent_x + margin
            y = parent_y + parent_height - toast_height - margin
        elif self.position == "top-right":
            x = parent_x + parent_width - toast_width - margin
            y = parent_y + margin
        elif self.position == "top-left":
            x = parent_x + margin
            y = parent_y + margin
        elif self.position == "center":
            x = parent_x + (parent_width - toast_width) // 2
            y = parent_y + (parent_height - toast_height) // 2
        else:
            x = parent_x + parent_width - toast_width - margin
            y = parent_y + parent_height - toast_height - margin

        self.toast_window.geometry(f"+{x}+{y}")

    def _fade_out(self):
        """Fade out and dismiss the toast."""
        if self.toast_window:
            try:
                # Simple fade effect
                current_alpha = self.toast_window.attributes("-alpha")
                if current_alpha > 0.1:
                    self.toast_window.attributes("-alpha", current_alpha - 0.1)
                    self._after_id = self.parent.after(30, self._fade_out)
                else:
                    self.dismiss()
            except Exception:
                self.dismiss()

    def dismiss(self):
        """Dismiss the toast immediately."""
        if self._after_id:
            try:
                self.parent.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

        if self.toast_window:
            try:
                self.toast_window.destroy()
            except Exception:
                pass
            self.toast_window = None


def show_toast(
    parent,
    message: str,
    toast_type: str = "info",
    duration: int = 2000,
    position: str = "bottom-right",
) -> Toast:
    """Convenience function to show a toast notification.

    Args:
        parent: Parent window
        message: Message to display
        toast_type: Type of toast (info, success, warning, error)
        duration: How long to show the toast (milliseconds)
        position: Where to position the toast

    Returns:
        Toast instance (can be used to dismiss early)
    """
    toast = Toast(parent, message, duration, toast_type, position)
    toast.show()
    return toast
