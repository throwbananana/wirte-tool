"""
统计展示组件 (Stats Display Widgets)

提供：
- Mini雷达图
- 进度条
- 热力图缩略
- 统计卡片
"""

import tkinter as tk
from tkinter import ttk
import math
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from writer_app.core.icon_manager import IconManager
from .dialogs import QuickInputDialog


class MiniRadarChart(tk.Canvas):
    """Mini五维雷达图"""

    def __init__(self, parent, size: int = 80, **kwargs):
        super().__init__(parent, width=size, height=size, highlightthickness=0, **kwargs)
        self.size = size
        self.center = size // 2
        self.radius = size // 2 - 10
        self.data: Dict[str, float] = {}
        self.labels = ["创意", "结构", "词汇", "风格", "专注"]
        self.colors = {
            "line": "#4FC3F7",
            "fill": "#4FC3F733",
            "axis": "#555555",
            "text": "#AAAAAA",
        }

    def set_data(self, data: Dict[str, float]):
        """设置数据 (0.0-1.0)"""
        self.data = data
        self._draw()

    def set_colors(self, **colors):
        """设置颜色"""
        self.colors.update(colors)
        self._draw()

    def _draw(self):
        """绘制雷达图"""
        self.delete("all")

        n = len(self.labels)
        if n < 3:
            return

        # 计算角度
        angles = [math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

        # 绘制轴线
        for angle in angles:
            x = self.center + self.radius * math.cos(angle)
            y = self.center - self.radius * math.sin(angle)
            self.create_line(self.center, self.center, x, y, fill=self.colors["axis"], width=1)

        # 绘制同心圆
        for r in [0.25, 0.5, 0.75, 1.0]:
            points = []
            for angle in angles:
                x = self.center + self.radius * r * math.cos(angle)
                y = self.center - self.radius * r * math.sin(angle)
                points.extend([x, y])
            points.extend(points[:2])  # 闭合
            self.create_line(*points, fill=self.colors["axis"], width=1)

        # 绘制数据多边形
        if self.data:
            data_points = []
            for i, label in enumerate(self.labels):
                value = self.data.get(label, 0.5)
                value = max(0, min(1, value))  # 限制在0-1
                x = self.center + self.radius * value * math.cos(angles[i])
                y = self.center - self.radius * value * math.sin(angles[i])
                data_points.extend([x, y])

            if len(data_points) >= 6:
                # 填充
                self.create_polygon(*data_points, fill=self.colors["fill"], outline="")
                # 边框
                data_points.extend(data_points[:2])  # 闭合
                self.create_line(*data_points, fill=self.colors["line"], width=2)

                # 数据点
                for i in range(0, len(data_points) - 2, 2):
                    self.create_oval(
                        data_points[i] - 3, data_points[i + 1] - 3,
                        data_points[i] + 3, data_points[i + 1] + 3,
                        fill=self.colors["line"], outline=""
                    )


class ProgressBar(tk.Canvas):
    """自定义进度条"""

    def __init__(self, parent, width: int = 100, height: int = 8,
                 bg_color: str = "#333333", fill_color: str = "#4CAF50", **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, **kwargs)
        self.bar_width = width
        self.bar_height = height
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.progress = 0.0
        self._draw()

    def set_progress(self, value: float):
        """设置进度 (0.0-1.0)"""
        self.progress = max(0, min(1, value))
        self._draw()

    def set_colors(self, bg: str = None, fill: str = None):
        """设置颜色"""
        if bg:
            self.bg_color = bg
        if fill:
            self.fill_color = fill
        self._draw()

    def _draw(self):
        """绘制进度条"""
        self.delete("all")

        # 背景
        self.create_rectangle(
            0, 0, self.bar_width, self.bar_height,
            fill=self.bg_color, outline=""
        )

        # 进度
        if self.progress > 0:
            fill_width = int(self.bar_width * self.progress)
            self.create_rectangle(
                0, 0, fill_width, self.bar_height,
                fill=self.fill_color, outline=""
            )


class MiniHeatmap(tk.Canvas):
    """Mini热力图（最近7天）"""

    def __init__(self, parent, cell_size: int = 10, days: int = 7, **kwargs):
        width = cell_size * days + (days - 1) * 2
        super().__init__(parent, width=width, height=cell_size, highlightthickness=0, **kwargs)
        self.cell_size = cell_size
        self.days = days
        self.data: Dict[str, int] = {}
        self.max_value = 1000  # 用于颜色计算
        self.colors = ["#1a1a2e", "#16213e", "#0f3460", "#1a508b", "#0d7377", "#14a76c", "#32cd32"]

    def set_data(self, data: Dict[str, int], max_value: int = None):
        """设置数据 {日期字符串: 字数}"""
        self.data = data
        if max_value:
            self.max_value = max_value
        self._draw()

    def _draw(self):
        """绘制热力图"""
        self.delete("all")

        today = date.today()
        for i in range(self.days):
            check_date = today - timedelta(days=self.days - 1 - i)
            date_str = check_date.isoformat()
            value = self.data.get(date_str, 0)

            # 计算颜色级别
            if value == 0:
                color = self.colors[0]
            else:
                level = min(len(self.colors) - 1, int(value / self.max_value * (len(self.colors) - 1)) + 1)
                color = self.colors[level]

            x = i * (self.cell_size + 2)
            self.create_rectangle(
                x, 0, x + self.cell_size, self.cell_size,
                fill=color, outline=""
            )


class StatsCard(tk.Frame):
    """统计卡片"""

    def __init__(self, parent, title: str, value: str = "0",
                 icon: str = "", color: str = "#4CAF50", 
                 font: Tuple[str, int] = ("Segoe UI Emoji", 12), **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg="#2D2D2D")

        # 图标
        if icon:
            self.icon_label = tk.Label(
                self, text=icon, font=font,
                bg="#2D2D2D", fg=color
            )
            self.icon_label.pack(side=tk.LEFT, padx=(5, 2))

        # 内容区
        content_frame = tk.Frame(self, bg="#2D2D2D")
        content_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 数值
        self.value_label = tk.Label(
            content_frame, text=value,
            font=("Microsoft YaHei", 12, "bold"),
            bg="#2D2D2D", fg=color
        )
        self.value_label.pack(anchor=tk.W)

        # 标题
        self.title_label = tk.Label(
            content_frame, text=title,
            font=("Microsoft YaHei", 8),
            bg="#2D2D2D", fg="#888888"
        )
        self.title_label.pack(anchor=tk.W)

    def set_value(self, value: str):
        """更新数值"""
        self.value_label.configure(text=value)


class MiniStatsPanel(tk.Frame):
    """Mini统计面板 - 整合所有统计组件"""

    def __init__(self, parent, integration=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg="#2D2D2D")
        self.integration = integration
        self.icon_mgr = IconManager()

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 标题栏
        title_frame = tk.Frame(self, bg="#1E88E5", height=20)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame, text="📊 创作统计",
            font=("Microsoft YaHei", 8),
            bg="#1E88E5", fg="white"
        ).pack(side=tk.LEFT, padx=5)

        # 刷新按钮
        # Use sync icon
        sync_icon = self.icon_mgr.get_icon("arrow_sync", size=16, fallback="🔄")
        icon_font = self.icon_mgr.get_font(size=10)
        
        refresh_btn = tk.Label(
            title_frame, text=sync_icon,
            font=icon_font,
            bg="#1E88E5", fg="white",
            cursor="hand2"
        )
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        refresh_btn.bind("<Button-1>", lambda e: self.refresh())

        # 内容区
        content = tk.Frame(self, bg="#2D2D2D")
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 第一行：今日字数 + 连续天数
        row1 = tk.Frame(content, bg="#2D2D2D")
        row1.pack(fill=tk.X, pady=2)

        edit_icon = self.icon_mgr.get_icon("edit", fallback="✏️")
        fire_icon = self.icon_mgr.get_icon("fire", fallback="🔥") # Try 'fire' or 'flame'
        if fire_icon == "🔥": fire_icon = self.icon_mgr.get_icon("flame", fallback="🔥")
        
        card_font = self.icon_mgr.get_font(size=12)

        self.today_card = StatsCard(
            row1, title="今日字数", value="0",
            icon=edit_icon, color="#4CAF50", font=card_font
        )
        self.today_card.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.streak_card = StatsCard(
            row1, title="连续天数", value="0",
            icon=fire_icon, color="#FF9800", font=card_font
        )
        self.streak_card.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 第二行：等级 + 称号
        row2 = tk.Frame(content, bg="#2D2D2D")
        row2.pack(fill=tk.X, pady=2)

        star_icon = self.icon_mgr.get_icon("star", fallback="⭐")
        award_icon = self.icon_mgr.get_icon("ribbon", fallback="🏅")
        if award_icon == "🏅": award_icon = self.icon_mgr.get_icon("award", fallback="🏅")

        self.level_card = StatsCard(
            row2, title="等级", value="Lv.1",
            icon=star_icon, color="#FFD700", font=card_font
        )
        self.level_card.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.title_card = StatsCard(
            row2, title="称号", value="文字爱好者",
            icon=award_icon, color="#9C27B0", font=card_font
        )
        self.title_card.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 第三行：热力图
        row3 = tk.Frame(content, bg="#2D2D2D")
        row3.pack(fill=tk.X, pady=5)

        tk.Label(
            row3, text="最近7天",
            font=("Microsoft YaHei", 8),
            bg="#2D2D2D", fg="#888888"
        ).pack(side=tk.LEFT)

        self.heatmap = MiniHeatmap(row3, cell_size=12, days=7, bg="#2D2D2D")
        self.heatmap.pack(side=tk.RIGHT)

        # 第四行：雷达图
        row4 = tk.Frame(content, bg="#2D2D2D")
        row4.pack(fill=tk.X, pady=5)

        tk.Label(
            row4, text="技能雷达",
            font=("Microsoft YaHei", 8),
            bg="#2D2D2D", fg="#888888"
        ).pack(side=tk.LEFT)

        self.radar = MiniRadarChart(row4, size=60, bg="#2D2D2D")
        self.radar.pack(side=tk.RIGHT)

        # 第五行：总字数进度
        row5 = tk.Frame(content, bg="#2D2D2D")
        row5.pack(fill=tk.X, pady=2)

        tk.Label(
            row5, text="总进度",
            font=("Microsoft YaHei", 8),
            bg="#2D2D2D", fg="#888888"
        ).pack(side=tk.LEFT)

        self.total_label = tk.Label(
            row5, text="0 / 50000",
            font=("Microsoft YaHei", 8),
            bg="#2D2D2D", fg="#AAAAAA"
        )
        self.total_label.pack(side=tk.RIGHT)

        self.progress_bar = ProgressBar(
            content, width=150, height=6,
            bg_color="#333333", fill_color="#2196F3",
            bg="#2D2D2D"
        )
        self.progress_bar.pack(fill=tk.X, pady=2)

        # 初始刷新
        self.after(100, self.refresh)

    def refresh(self):
        """刷新统计数据"""
        if not self.integration:
            return

        try:
            stats = self.integration.get_stats_summary()

            # 更新卡片
            self.today_card.set_value(f"{stats.get('today_words', 0):,}")
            self.streak_card.set_value(str(stats.get('streak', 0)))
            self.level_card.set_value(f"Lv.{stats.get('level', 1)}")
            self.title_card.set_value(stats.get('title', '文字爱好者'))

            # 更新热力图
            heatmap_data = self.integration.stats.get_heatmap_data() if hasattr(self.integration, 'stats') else {}
            self.heatmap.set_data(heatmap_data, max_value=2000)

            # 更新雷达图
            radar_data = stats.get('radar', {})
            self.radar.set_data(radar_data)

            # 更新总进度
            total = stats.get('total_words', 0)
            goal = 50000  # 默认目标5万字
            self.total_label.configure(text=f"{total:,} / {goal:,}")
            self.progress_bar.set_progress(total / goal)

        except Exception as e:
            print(f"刷新统计失败: {e}")

    def set_integration(self, integration):
        """设置集成管理器"""
        self.integration = integration
        self.refresh()


class QuickActionsPanel(tk.Frame):
    """快捷操作面板"""

    def __init__(self, parent, integration=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg="#2D2D2D")
        self.integration = integration
        self._callbacks: Dict[str, callable] = {}

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # 标题栏
        title_frame = tk.Frame(self, bg="#7B1FA2", height=20)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame, text="⚡ 快捷操作",
            font=("Microsoft YaHei", 8),
            bg="#7B1FA2", fg="white"
        ).pack(side=tk.LEFT, padx=5)

        # 按钮区
        content = tk.Frame(self, bg="#2D2D2D")
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 按钮配置
        buttons = [
            ("📝 添加场景", "add_scene", "#4CAF50"),
            ("👤 添加角色", "add_character", "#2196F3"),
            ("💡 记录灵感", "add_idea", "#FF9800"),
            ("📚 添加研究", "add_research", "#9C27B0"),
        ]

        for text, action, color in buttons:
            btn = tk.Label(
                content, text=text,
                font=("Microsoft YaHei", 9),
                bg="#424242", fg="white",
                padx=10, pady=5,
                cursor="hand2"
            )
            btn.pack(fill=tk.X, pady=2)
            btn.bind("<Button-1>", lambda e, a=action: self._on_action(a))
            btn.bind("<Enter>", lambda e, b=btn, c=color: b.configure(bg=c))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg="#424242"))

    def _on_action(self, action: str):
        """处理操作"""
        if action in self._callbacks:
            self._callbacks[action]()
        elif self.integration:
            if action == "add_scene":
                self._show_add_scene_dialog()
            elif action == "add_character":
                self._show_add_character_dialog()
            elif action == "add_idea":
                self._show_add_idea_dialog()
            elif action == "add_research":
                self._show_add_research_dialog()

    def register_callback(self, action: str, callback: callable):
        """注册回调"""
        self._callbacks[action] = callback

    def _show_add_scene_dialog(self):
        """显示添加场景对话框"""
        dlg = QuickInputDialog(self, "添加场景", "场景名称:")
        self.wait_window(dlg)
        if dlg.result and self.integration:
            self.integration.add_scene(dlg.result)

    def _show_add_character_dialog(self):
        """显示添加角色对话框"""
        dlg = QuickInputDialog(self, "添加角色", "角色名称:")
        self.wait_window(dlg)
        if dlg.result and self.integration:
            self.integration.add_character(dlg.result)

    def _show_add_idea_dialog(self):
        """显示添加灵感对话框"""
        dlg = QuickInputDialog(self, "记录灵感", "灵感内容:", multiline=True)
        self.wait_window(dlg)
        if dlg.result and self.integration:
            self.integration.add_idea(dlg.result)

    def _show_add_research_dialog(self):
        """显示添加研究对话框"""
        dlg = QuickInputDialog(self, "添加研究", "研究标题:")
        self.wait_window(dlg)
        if dlg.result and self.integration:
            self.integration.add_research(dlg.result, "")

    def set_integration(self, integration):
        """设置集成管理器"""
        self.integration = integration