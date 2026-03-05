"""
不在场证明时间轴视图 - 展示每个时间段角色的所在地

功能：
- 角色作为行（Y轴），时间作为列（X轴）
- 显示每个角色在每个时间点的位置
- 支持缩放和平移
- 支持主题切换
"""
import tkinter as tk
from tkinter import ttk


class AlibiTimelineCanvas(tk.Canvas):
    """不在场证明时间轴 Canvas"""

    def __init__(self, parent, project_manager, theme_manager=None, **kwargs):
        # Remove custom kwargs before passing to Canvas
        self.project_manager = project_manager
        self.theme_manager = theme_manager

        super().__init__(parent, highlightthickness=0, **kwargs)

        self.time_slots = []
        self.char_lanes = {}

        # State
        self.zoom = 1.0
        self._drag_data = {"x": 0, "y": 0}

        # Apply initial theme
        self._apply_theme()

        # Register theme listener
        if self.theme_manager:
            self.theme_manager.add_listener(self._on_theme_change)

        # Bind events
        self._bind_events()

    def _bind_events(self):
        """绑定交互事件"""
        # Refresh on resize
        self.bind("<Configure>", lambda e: self.after_idle(self.refresh))

        # Pan using scan_mark/scan_dragto
        self.bind("<ButtonPress-1>", self._on_pan_start)
        self.bind("<B1-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-1>", self._on_pan_end)

        # Also support middle button
        self.bind("<ButtonPress-2>", self._on_pan_start)
        self.bind("<B2-Motion>", self._on_pan_drag)
        self.bind("<ButtonRelease-2>", self._on_pan_end)

        # Zoom with mouse wheel
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", self._on_wheel)  # Linux scroll up
        self.bind("<Button-5>", self._on_wheel)  # Linux scroll down

    def _on_theme_change(self):
        """响应主题变化"""
        self._apply_theme()
        self.refresh()

    def _apply_theme(self):
        """应用主题颜色"""
        if self.theme_manager:
            bg = self.theme_manager.get_color("canvas_bg")
        else:
            bg = "#263238"  # Default dark theme
        self.configure(bg=bg)

    def _get_theme_colors(self):
        """获取当前主题颜色"""
        if self.theme_manager:
            return {
                "bg": self.theme_manager.get_color("alibi_bg"),
                "header_bg": self.theme_manager.get_color("alibi_header_bg"),
                "header_text": self.theme_manager.get_color("alibi_header_fg"),
                "grid_line": self.theme_manager.get_color("alibi_grid"),
                "text": self.theme_manager.get_color("alibi_text"),
                "cell_bg": self.theme_manager.get_color("alibi_cell_bg"),
                "cell_outline": self.theme_manager.get_color("alibi_cell_outline"),
                "cell_text": self.theme_manager.get_color("alibi_cell_text")
            }
        else:
            # Fallback if no theme manager
            return {
                "bg": "#FAFAFA",
                "header_bg": "#E0E0E0",
                "header_text": "#333333",
                "grid_line": "#BDBDBD",
                "text": "#424242",
                "cell_bg": "#90CAF9",
                "cell_outline": "#42A5F5",
                "cell_text": "#1A237E"
            }

    def _on_pan_start(self, event):
        """开始平移"""
        self.scan_mark(event.x, event.y)
        self.config(cursor="fleur")

    def _on_pan_drag(self, event):
        """平移拖拽"""
        self.scan_dragto(event.x, event.y, gain=1)

    def _on_pan_end(self, event):
        """结束平移"""
        self.config(cursor="")

    def _on_wheel(self, event):
        """鼠标滚轮缩放"""
        if event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            scale = 0.9
        else:
            scale = 1.1

        self.zoom *= scale
        self.zoom = max(0.5, min(3.0, self.zoom))

        self.refresh()

    def refresh(self):
        """刷新绘制"""
        self.delete("all")

        colors = self._get_theme_colors()
        self.configure(bg=colors["bg"])

        # Gather data
        scenes = self.project_manager.get_scenes()
        times = sorted(list(set(s.get("time", "") for s in scenes if s.get("time"))))

        if not times:
            self.create_text(
                self.winfo_width() / 2,
                self.winfo_height() / 2,
                text="暂无带时间的场景。请在场景信息中填写时间。",
                fill=colors["text"]
            )
            return

        chars = [c["name"] for c in self.project_manager.get_characters()]
        if not chars:
            self.create_text(
                self.winfo_width() / 2,
                self.winfo_height() / 2,
                text="暂无角色。",
                fill=colors["text"]
            )
            return

        # Calculate dimensions
        margin_left = 100 * self.zoom
        margin_top = 60 * self.zoom
        row_height = 50 * self.zoom
        col_width = 150 * self.zoom

        total_w = margin_left + len(times) * col_width + 100
        total_h = margin_top + len(chars) * row_height + 100

        self.configure(scrollregion=(0, 0, total_w, total_h))

        # Draw grid & headers
        self._draw_time_headers(times, margin_left, margin_top, col_width, total_h, colors)
        self._draw_char_headers(chars, margin_left, margin_top, row_height, total_w, colors)
        self._draw_alibi_cells(scenes, times, chars, margin_left, margin_top, row_height, col_width, colors)

    def _draw_time_headers(self, times, margin_left, margin_top, col_width, total_h, colors):
        """绘制时间表头"""
        font_size = max(8, int(10 * self.zoom))

        for i, t in enumerate(times):
            x = margin_left + i * col_width
            self.create_text(
                x + col_width / 2, margin_top / 2,
                text=t, fill=colors["text"],
                font=("Arial", font_size, "bold")
            )
            self.create_line(
                x, 0, x, total_h,
                fill=colors["grid_line"], dash=(2, 2)
            )

    def _draw_char_headers(self, chars, margin_left, margin_top, row_height, total_w, colors):
        """绘制角色表头"""
        font_size = max(7, int(9 * self.zoom))
        self.char_lanes.clear()

        for i, char in enumerate(chars):
            y = margin_top + i * row_height
            # Draw header background
            self.create_rectangle(
                0, y, margin_left, y + row_height,
                fill=colors["header_bg"], outline=colors["grid_line"]
            )
            self.create_text(
                margin_left / 2, y + row_height / 2,
                text=char, fill=colors["header_text"],
                font=("Arial", font_size, "bold")
            )
            self.create_line(
                0, y + row_height, total_w, y + row_height,
                fill=colors["grid_line"]
            )
            self.char_lanes[char] = y

    def _draw_alibi_cells(self, scenes, times, chars, margin_left, margin_top, row_height, col_width, colors):
        """绘制不在场证明单元格"""
        font_size = max(6, int(8 * self.zoom))
        padding = 5 * self.zoom

        for scene in scenes:
            t = scene.get("time")
            if not t:
                continue

            try:
                col_idx = times.index(t)
            except ValueError:
                continue

            loc = scene.get("location", "未知")
            scene_chars = scene.get("characters", [])

            for char in scene_chars:
                if char in self.char_lanes:
                    y = self.char_lanes[char]
                    x = margin_left + col_idx * col_width

                    # Draw alibi block
                    self.create_rectangle(
                        x + padding, y + padding,
                        x + col_width - padding, y + row_height - padding,
                        fill=colors["cell_bg"], outline=colors["cell_outline"]
                    )
                    self.create_text(
                        x + col_width / 2, y + row_height / 2,
                        text=loc, fill=colors["cell_text"],
                        font=("Arial", font_size),
                        width=col_width - 2 * padding
                    )


class AlibiTimelineController:
    """不在场证明时间轴控制器"""

    def __init__(self, parent, project_manager, theme_manager=None):
        self.parent = parent
        self.project_manager = project_manager
        self.theme_manager = theme_manager

        # Container with scrollbars
        self.container = ttk.Frame(parent)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.view = AlibiTimelineCanvas(
            self.container,
            project_manager,
            theme_manager
        )

        # Scrollbars
        scroll_x = ttk.Scrollbar(self.container, orient=tk.HORIZONTAL, command=self.view.xview)
        scroll_y = ttk.Scrollbar(self.container, orient=tk.VERTICAL, command=self.view.yview)

        self.view.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

        # Layout
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bottom info
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(
            info_frame,
            text="不在场证明视图: 展示每个时间段角色的所在地。支持滚轮缩放和鼠标拖拽。"
        ).pack()

    def refresh(self):
        """刷新视图"""
        self.view.refresh()
