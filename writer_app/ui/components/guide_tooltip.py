"""
Guide Tooltip Component

A styled tooltip/callout with arrow pointing to target elements.
Used during guided tours to provide contextual instructions.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Tuple
import math


class GuideTooltip(tk.Toplevel):
    """
    A tooltip with an arrow pointing to a target element.

    Features:
    - Arrow pointing in 4 directions (top, bottom, left, right)
    - Styled appearance with rounded corners simulation
    - Auto-positioning based on available space
    - Theme support
    - Optional action buttons

    Usage:
        tooltip = GuideTooltip(
            root,
            theme_manager,
            text="Click this button to add a new item",
            target_widget=add_button,
            position="bottom"
        )
        tooltip.show()
    """

    # Constants
    ARROW_SIZE = 12
    PADDING_X = 16
    PADDING_Y = 12
    MAX_WIDTH = 350
    MIN_WIDTH = 200
    BORDER_RADIUS = 8
    POSITION_RETRY_DELAY_MS = 80
    POSITION_RETRY_LIMIT = 12

    def __init__(
        self,
        root: tk.Tk,
        theme_manager=None,
        text: str = "",
        target_widget: tk.Widget = None,
        position: str = "bottom",  # "top", "bottom", "left", "right", "auto"
        title: str = None,
        has_arrow: bool = True,
        primary_button: str = None,
        secondary_button: str = None,
        on_primary: Callable = None,
        on_secondary: Callable = None,
        on_close: Callable = None,
        **kwargs
    ):
        super().__init__(root, **kwargs)

        self.root = root
        self.theme_manager = theme_manager
        self._text = text
        self._title = title
        self._target_widget = target_widget
        self._position = position
        self._has_arrow = has_arrow
        self._primary_button = primary_button
        self._secondary_button = secondary_button
        self._on_primary = on_primary
        self._on_secondary = on_secondary
        self._on_close = on_close
        self._position_retries = 0

        # Colors
        self._bg_color = "#FFFDE7"  # Light yellow
        self._fg_color = "#333333"
        self._title_color = "#1565C0"
        self._border_color = "#FFC107"
        self._arrow_color = "#FFFDE7"
        self._update_colors()

        # Configure window
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.withdraw()  # Start hidden

        self._setup_ui()

        # Register theme listener
        if self.theme_manager:
            self.theme_manager.add_listener(self._apply_theme)

    def _update_colors(self):
        """Update colors from theme."""
        if self.theme_manager:
            current = self.theme_manager.current_theme
            if current == "Dark":
                self._bg_color = "#424242"
                self._fg_color = "#E0E0E0"
                self._title_color = "#64B5F6"
                self._border_color = "#757575"
                self._arrow_color = "#424242"
            else:
                self._bg_color = "#FFFDE7"
                self._fg_color = "#333333"
                self._title_color = "#1565C0"
                self._border_color = "#FFC107"
                self._arrow_color = "#FFFDE7"

    def _setup_ui(self):
        """Setup the tooltip UI."""
        # Main container with border
        self._container = tk.Frame(
            self,
            bg=self._border_color,
            padx=2,
            pady=2
        )
        self._container.pack(fill=tk.BOTH, expand=True)

        # Inner frame
        self._inner_frame = tk.Frame(
            self._container,
            bg=self._bg_color,
            padx=self.PADDING_X,
            pady=self.PADDING_Y
        )
        self._inner_frame.pack(fill=tk.BOTH, expand=True)

        # Close button
        self._close_btn = tk.Label(
            self._inner_frame,
            text="×",
            font=("Arial", 14, "bold"),
            fg="#888888",
            bg=self._bg_color,
            cursor="hand2"
        )
        self._close_btn.place(relx=1.0, rely=0, anchor="ne", x=-2, y=2)
        self._close_btn.bind("<Button-1>", self._on_close_click)
        self._close_btn.bind("<Enter>", lambda e: self._close_btn.configure(fg="#333333"))
        self._close_btn.bind("<Leave>", lambda e: self._close_btn.configure(fg="#888888"))

        # Title (optional)
        if self._title:
            self._title_label = tk.Label(
                self._inner_frame,
                text=self._title,
                font=("Microsoft YaHei", 11, "bold"),
                fg=self._title_color,
                bg=self._bg_color,
                anchor="w",
                justify=tk.LEFT
            )
            self._title_label.pack(fill=tk.X, pady=(0, 8))

        # Text content
        self._text_label = tk.Label(
            self._inner_frame,
            text=self._text,
            font=("Microsoft YaHei", 10),
            fg=self._fg_color,
            bg=self._bg_color,
            wraplength=self.MAX_WIDTH - self.PADDING_X * 2 - 20,
            justify=tk.LEFT,
            anchor="w"
        )
        self._text_label.pack(fill=tk.X, pady=(0, 8) if self._primary_button else 0)

        # Button frame
        if self._primary_button or self._secondary_button:
            self._button_frame = tk.Frame(self._inner_frame, bg=self._bg_color)
            self._button_frame.pack(fill=tk.X, pady=(8, 0))

            if self._secondary_button:
                self._sec_btn = ttk.Button(
                    self._button_frame,
                    text=self._secondary_button,
                    command=self._on_secondary_click,
                    style="Secondary.TButton"
                )
                self._sec_btn.pack(side=tk.LEFT, padx=(0, 8))

            if self._primary_button:
                self._pri_btn = ttk.Button(
                    self._button_frame,
                    text=self._primary_button,
                    command=self._on_primary_click,
                    style="Accent.TButton"
                )
                self._pri_btn.pack(side=tk.RIGHT)

        # Arrow canvas (will be positioned separately)
        self._arrow_canvas = None

    def _on_close_click(self, event=None):
        """Handle close button click."""
        self.hide()
        if self._on_close:
            self._on_close()

    def _on_primary_click(self):
        """Handle primary button click."""
        if self._on_primary:
            self._on_primary()
        self.hide()

    def _on_secondary_click(self):
        """Handle secondary button click."""
        if self._on_secondary:
            self._on_secondary()

    def _apply_theme(self):
        """Apply theme colors."""
        self._update_colors()

        self._container.configure(bg=self._border_color)
        self._inner_frame.configure(bg=self._bg_color)
        self._text_label.configure(fg=self._fg_color, bg=self._bg_color)
        self._close_btn.configure(bg=self._bg_color)

        if hasattr(self, "_title_label"):
            self._title_label.configure(fg=self._title_color, bg=self._bg_color)

        if hasattr(self, "_button_frame"):
            self._button_frame.configure(bg=self._bg_color)

    def _is_target_ready(self) -> bool:
        if not self._target_widget:
            return False
        try:
            if not self._target_widget.winfo_viewable():
                return False
            self._target_widget.update_idletasks()
            return self._target_widget.winfo_width() > 1 and self._target_widget.winfo_height() > 1
        except tk.TclError:
            return False

    def _center_on_root(self):
        """Center the tooltip on the root window."""
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        try:
            rx = self.root.winfo_rootx()
            ry = self.root.winfo_rooty()
            rw = self.root.winfo_width()
            rh = self.root.winfo_height()
        except tk.TclError:
            self._center_on_screen()
            return
        if rw <= 1 or rh <= 1:
            self._center_on_screen()
            return
        x = rx + (rw - w) // 2
        y = ry + (rh - h) // 2
        # 确保不超出屏幕边界
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(10, min(x, screen_w - w - 10))
        y = max(10, min(y, screen_h - h - 10))
        self.geometry(f"+{x}+{y}")

    def _schedule_position_retry(self):
        if self._position_retries >= self.POSITION_RETRY_LIMIT:
            return
        self._position_retries += 1
        self.after(self.POSITION_RETRY_DELAY_MS, self._retry_position)

    def _retry_position(self):
        if not self.winfo_exists() or not self.winfo_viewable() or not self._target_widget:
            return
        if not self._is_target_ready():
            self._schedule_position_retry()
            return
        self._position_near_widget()
        if self._has_arrow:
            self._draw_arrow()

    def show(self):
        """Show the tooltip near the target widget."""
        self.update_idletasks()
        self._position_retries = 0

        positioned = False
        if self._target_widget and self._is_target_ready():
            self._position_near_widget()
            positioned = True
        elif self._target_widget:
            self._center_on_root()
        else:
            # Center on screen
            self._center_on_screen()

        self.deiconify()

        if self._has_arrow and self._target_widget and positioned:
            self._draw_arrow()
        if self._target_widget and not positioned:
            self._schedule_position_retry()

    def _position_near_widget(self):
        """Position the tooltip near the target widget."""
        if not self._target_widget:
            return

        self._target_widget.update_idletasks()

        # Get target position and size
        tx = self._target_widget.winfo_rootx()
        ty = self._target_widget.winfo_rooty()
        tw = self._target_widget.winfo_width()
        th = self._target_widget.winfo_height()

        # Get tooltip size
        self.update_idletasks()
        tooltip_w = self.winfo_reqwidth()
        tooltip_h = self.winfo_reqheight()

        # Get screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Auto-select position if needed
        position = self._position
        if position == "auto":
            position = self._calculate_best_position(
                tx, ty, tw, th,
                tooltip_w, tooltip_h,
                screen_w, screen_h
            )

        # Calculate position
        gap = self.ARROW_SIZE + 4

        if position == "bottom":
            x = tx + tw // 2 - tooltip_w // 2
            y = ty + th + gap
        elif position == "top":
            x = tx + tw // 2 - tooltip_w // 2
            y = ty - tooltip_h - gap
        elif position == "right":
            x = tx + tw + gap
            y = ty + th // 2 - tooltip_h // 2
        elif position == "left":
            x = tx - tooltip_w - gap
            y = ty + th // 2 - tooltip_h // 2
        else:
            x = tx + tw // 2 - tooltip_w // 2
            y = ty + th + gap

        # Clamp to screen bounds
        x = max(10, min(x, screen_w - tooltip_w - 10))
        y = max(10, min(y, screen_h - tooltip_h - 10))

        self._actual_position = position
        self.geometry(f"+{int(x)}+{int(y)}")

    def _calculate_best_position(
        self, tx, ty, tw, th, tooltip_w, tooltip_h, screen_w, screen_h
    ) -> str:
        """Calculate the best position for the tooltip."""
        gap = self.ARROW_SIZE + 4

        # Check available space in each direction
        space_bottom = screen_h - (ty + th + gap)
        space_top = ty - gap
        space_right = screen_w - (tx + tw + gap)
        space_left = tx - gap

        # Prefer bottom, then top, then right, then left
        if space_bottom >= tooltip_h:
            return "bottom"
        elif space_top >= tooltip_h:
            return "top"
        elif space_right >= tooltip_w:
            return "right"
        elif space_left >= tooltip_w:
            return "left"
        else:
            return "bottom"  # Default fallback

    def _center_on_screen(self):
        """Center the tooltip on screen."""
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"+{x}+{y}")

    def _draw_arrow(self):
        """Draw an arrow pointing to the target widget."""
        if not self._target_widget or not hasattr(self, "_actual_position"):
            return

        # Remove existing arrow
        if self._arrow_canvas:
            try:
                self._arrow_canvas.destroy()
            except tk.TclError:
                pass

        # Create arrow canvas as separate toplevel
        self._arrow_canvas = tk.Toplevel(self.root)
        self._arrow_canvas.overrideredirect(True)
        self._arrow_canvas.attributes("-topmost", True)

        # Make transparent (Windows)
        try:
            self._arrow_canvas.attributes("-transparentcolor", "magenta")
        except tk.TclError:
            pass

        arrow_size = self.ARROW_SIZE
        canvas_size = arrow_size * 2

        canvas = tk.Canvas(
            self._arrow_canvas,
            width=canvas_size,
            height=canvas_size,
            bg="magenta",
            highlightthickness=0
        )
        canvas.pack()

        # Draw arrow based on position
        position = self._actual_position
        points = self._get_arrow_points(position, arrow_size, canvas_size)

        canvas.create_polygon(
            points,
            fill=self._arrow_color,
            outline=self._border_color,
            width=2
        )

        # Position arrow
        self.update_idletasks()
        tooltip_x = self.winfo_x()
        tooltip_y = self.winfo_y()
        tooltip_w = self.winfo_width()
        tooltip_h = self.winfo_height()

        self._target_widget.update_idletasks()
        tx = self._target_widget.winfo_rootx()
        ty = self._target_widget.winfo_rooty()
        tw = self._target_widget.winfo_width()
        th = self._target_widget.winfo_height()

        # 计算目标控件中心
        target_center_x = tx + tw // 2
        target_center_y = ty + th // 2

        if position == "bottom":
            # 箭头X应该指向目标中心，但需要限制在提示框宽度范围内
            ax = target_center_x - arrow_size
            # 限制箭头在提示框水平范围内（留出边距）
            min_ax = tooltip_x + 10
            max_ax = tooltip_x + tooltip_w - canvas_size - 10
            ax = max(min_ax, min(ax, max_ax))
            ay = tooltip_y - arrow_size
        elif position == "top":
            ax = target_center_x - arrow_size
            min_ax = tooltip_x + 10
            max_ax = tooltip_x + tooltip_w - canvas_size - 10
            ax = max(min_ax, min(ax, max_ax))
            ay = tooltip_y + tooltip_h - arrow_size
        elif position == "right":
            ax = tooltip_x - arrow_size
            ay = target_center_y - arrow_size
            # 限制箭头在提示框垂直范围内
            min_ay = tooltip_y + 10
            max_ay = tooltip_y + tooltip_h - canvas_size - 10
            ay = max(min_ay, min(ay, max_ay))
        elif position == "left":
            ax = tooltip_x + tooltip_w - arrow_size
            ay = target_center_y - arrow_size
            min_ay = tooltip_y + 10
            max_ay = tooltip_y + tooltip_h - canvas_size - 10
            ay = max(min_ay, min(ay, max_ay))
        else:
            ax = tooltip_x + tooltip_w // 2 - arrow_size
            ay = tooltip_y - arrow_size

        self._arrow_canvas.geometry(f"{canvas_size}x{canvas_size}+{int(ax)}+{int(ay)}")

    def _get_arrow_points(self, position: str, arrow_size: int, canvas_size: int) -> list:
        """Get arrow polygon points based on position."""
        mid = canvas_size // 2

        if position == "bottom":
            # Arrow pointing up
            return [mid, 0, canvas_size, canvas_size, 0, canvas_size]
        elif position == "top":
            # Arrow pointing down
            return [mid, canvas_size, 0, 0, canvas_size, 0]
        elif position == "right":
            # Arrow pointing left
            return [0, mid, canvas_size, 0, canvas_size, canvas_size]
        elif position == "left":
            # Arrow pointing right
            return [canvas_size, mid, 0, 0, 0, canvas_size]
        else:
            return [mid, 0, canvas_size, canvas_size, 0, canvas_size]

    def hide(self):
        """Hide the tooltip."""
        self.withdraw()
        if self._arrow_canvas:
            try:
                self._arrow_canvas.destroy()
            except tk.TclError:
                pass
            self._arrow_canvas = None

    def update_text(self, text: str, title: str = None):
        """Update the tooltip text."""
        self._text = text
        self._text_label.configure(text=text)

        if title is not None and hasattr(self, "_title_label"):
            self._title_label.configure(text=title)

    def update_target(self, widget: tk.Widget, position: str = None):
        """Update the target widget."""
        self._target_widget = widget
        if position:
            self._position = position

        self._position_retries = 0
        if self.winfo_viewable():
            if self._target_widget and self._is_target_ready():
                self._position_near_widget()
                if self._has_arrow:
                    self._draw_arrow()
            elif self._target_widget:
                self._schedule_position_retry()

    def destroy(self):
        """Clean up resources."""
        if self._arrow_canvas:
            try:
                self._arrow_canvas.destroy()
            except tk.TclError:
                pass

        if self.theme_manager:
            self.theme_manager.remove_listener(self._apply_theme)

        super().destroy()


class TooltipSequence:
    """
    Manages a sequence of tooltips for step-by-step guidance.

    Usage:
        seq = TooltipSequence(root, theme_manager)
        seq.add_step(widget1, "Step 1", "First instruction")
        seq.add_step(widget2, "Step 2", "Second instruction")
        seq.start()
    """

    def __init__(self, root: tk.Tk, theme_manager=None):
        self.root = root
        self.theme_manager = theme_manager
        self._steps = []
        self._current_step = -1
        self._tooltip: Optional[GuideTooltip] = None
        self._on_complete: Optional[Callable] = None

    def add_step(
        self,
        widget: tk.Widget,
        title: str,
        text: str,
        position: str = "auto"
    ):
        """Add a step to the sequence."""
        self._steps.append({
            "widget": widget,
            "title": title,
            "text": text,
            "position": position
        })

    def start(self, on_complete: Optional[Callable] = None):
        """Start the tooltip sequence."""
        self._on_complete = on_complete
        self._current_step = -1
        self.next_step()

    def next_step(self):
        """Move to the next step."""
        self._current_step += 1

        if self._current_step >= len(self._steps):
            self._complete()
            return

        self._show_current_step()

    def previous_step(self):
        """Move to the previous step."""
        if self._current_step > 0:
            self._current_step -= 1
            self._show_current_step()

    def _show_current_step(self):
        """Show the current step tooltip."""
        if self._tooltip:
            self._tooltip.destroy()

        step = self._steps[self._current_step]
        step_num = self._current_step + 1
        total = len(self._steps)

        self._tooltip = GuideTooltip(
            self.root,
            self.theme_manager,
            text=step["text"],
            title=f"{step['title']} ({step_num}/{total})",
            target_widget=step["widget"],
            position=step["position"],
            primary_button="下一步" if self._current_step < len(self._steps) - 1 else "完成",
            secondary_button="上一步" if self._current_step > 0 else None,
            on_primary=self.next_step,
            on_secondary=self.previous_step,
            on_close=self.skip
        )
        self._tooltip.show()

    def skip(self):
        """Skip the sequence."""
        self._complete()

    def _complete(self):
        """Complete the sequence."""
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

        if self._on_complete:
            self._on_complete()

    def destroy(self):
        """Clean up resources."""
        if self._tooltip:
            self._tooltip.destroy()
