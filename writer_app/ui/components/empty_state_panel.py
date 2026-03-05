"""
Empty State Panel Component

A reusable component for displaying empty state messages with icon,
title, description, and optional action button.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable


class EmptyStatePanel(ttk.Frame):
    """
    A visual component for displaying empty state in panels.

    Features:
    - Large icon (emoji or text)
    - Title text
    - Description text
    - Optional action button
    - Theme support

    Usage:
        empty_state = EmptyStatePanel(
            parent,
            theme_manager,
            icon="📝",
            title="暂无内容",
            description="点击下方按钮添加第一个条目",
            action_text="添加条目",
            action_callback=self.add_item
        )
        empty_state.pack(fill=tk.BOTH, expand=True)
    """

    def __init__(
        self,
        parent,
        theme_manager,
        icon: str = "📋",
        title: str = "暂无内容",
        description: str = "",
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)

        self.theme_manager = theme_manager
        self._icon = icon
        self._title = title
        self._description = description
        self._action_text = action_text
        self._action_callback = action_callback

        self._setup_ui()
        self._apply_theme()

        # Register theme listener
        if self.theme_manager:
            self.theme_manager.add_listener(self._apply_theme)

    def _setup_ui(self):
        """Setup the UI components."""
        # Center container
        self._container = ttk.Frame(self)
        self._container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Icon label (large font)
        self._icon_label = tk.Label(
            self._container,
            text=self._icon,
            font=("Segoe UI Emoji", 48)
        )
        self._icon_label.pack(pady=(0, 16))

        # Title label
        self._title_label = tk.Label(
            self._container,
            text=self._title,
            font=("Microsoft YaHei", 16, "bold"),
            wraplength=400
        )
        self._title_label.pack(pady=(0, 8))

        # Description label
        self._desc_label = tk.Label(
            self._container,
            text=self._description,
            font=("Microsoft YaHei", 11),
            wraplength=400,
            justify=tk.CENTER
        )
        self._desc_label.pack(pady=(0, 20))

        # Action button (optional)
        self._action_btn = None
        if self._action_text and self._action_callback:
            self._action_btn = ttk.Button(
                self._container,
                text=self._action_text,
                command=self._action_callback,
                style="Accent.TButton"
            )
            self._action_btn.pack()

    def _apply_theme(self):
        """Apply current theme colors."""
        if not self.theme_manager:
            return

        bg = self.theme_manager.get_color("bg_primary")
        fg_primary = self.theme_manager.get_color("fg_primary")
        fg_secondary = self.theme_manager.get_color("fg_secondary")

        # Apply to frame
        self.configure(style="EmptyState.TFrame")
        self._container.configure(style="EmptyState.TFrame")

        # Create custom style
        style = ttk.Style()
        style.configure("EmptyState.TFrame", background=bg)

        # Apply to labels (tk.Label needs direct config)
        self._icon_label.configure(bg=bg, fg=fg_secondary)
        self._title_label.configure(bg=bg, fg=fg_primary)
        self._desc_label.configure(bg=bg, fg=fg_secondary)

    def set_content(
        self,
        icon: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None
    ):
        """
        Update the empty state content dynamically.

        Args:
            icon: New icon (emoji or text)
            title: New title text
            description: New description text
            action_text: New button text (requires action_callback)
            action_callback: New button callback
        """
        if icon is not None:
            self._icon = icon
            self._icon_label.configure(text=icon)

        if title is not None:
            self._title = title
            self._title_label.configure(text=title)

        if description is not None:
            self._description = description
            self._desc_label.configure(text=description)

        # Update action button
        if action_text is not None and action_callback is not None:
            self._action_text = action_text
            self._action_callback = action_callback

            if self._action_btn:
                self._action_btn.configure(
                    text=action_text,
                    command=action_callback
                )
            else:
                self._action_btn = ttk.Button(
                    self._container,
                    text=action_text,
                    command=action_callback,
                    style="Accent.TButton"
                )
                self._action_btn.pack()
        elif action_text is None and self._action_btn:
            self._action_btn.destroy()
            self._action_btn = None

    def show(self):
        """Show the empty state panel."""
        self.pack(fill=tk.BOTH, expand=True)

    def hide(self):
        """Hide the empty state panel."""
        self.pack_forget()

    def destroy(self):
        """Clean up resources before destroying."""
        if self.theme_manager:
            self.theme_manager.remove_listener(self._apply_theme)
        super().destroy()


class EmptyStateConfig:
    """
    Predefined empty state configurations for common use cases.
    """

    TIMELINE = {
        "icon": "📅",
        "title": "时间线为空",
        "description": "添加场景或事件来构建你的故事时间线。\n时间线可以帮助你组织故事的时间顺序。",
        "action_text": "添加事件"
    }

    KANBAN = {
        "icon": "📋",
        "title": "看板为空",
        "description": "创建场景卡片来规划你的故事进度。\n拖拽卡片在不同状态列之间移动。",
        "action_text": "添加场景"
    }

    EVIDENCE = {
        "icon": "🔍",
        "title": "证据板为空",
        "description": "添加线索和证据来构建推理故事。\n连接相关线索以发现隐藏的关联。",
        "action_text": "添加线索"
    }

    DUAL_TIMELINE = {
        "icon": "⏳",
        "title": "双轨时间线为空",
        "description": "添加真相事件和叙述事件来构建悬疑故事。\n对比真实发生的事与角色所知的事。",
        "action_text": "添加事件"
    }

    RELATIONSHIP = {
        "icon": "🤝",
        "title": "暂无角色关系",
        "description": "添加角色并建立他们之间的关系。\n可视化人物关系有助于塑造复杂的故事结构。",
        "action_text": "添加角色"
    }

    RESEARCH = {
        "icon": "📚",
        "title": "暂无研究资料",
        "description": "收集和整理你的写作参考资料。\n包括历史背景、专业知识、素材灵感等。",
        "action_text": "添加资料"
    }

    IDEAS = {
        "icon": "💡",
        "title": "暂无创意点子",
        "description": "记录你的灵感闪现和创意想法。\n可以随时拖拽到大纲中转化为正式内容。",
        "action_text": "添加点子"
    }

    OUTLINE = {
        "icon": "🗺️",
        "title": "大纲为空",
        "description": "开始构建你的故事结构。\n双击添加节点，Tab键添加子节点。",
        "action_text": "添加节点"
    }

    SCENES = {
        "icon": "🎬",
        "title": "暂无场景",
        "description": "创建你的第一个场景开始写作。\n场景是故事的基本构建单元。",
        "action_text": "添加场景"
    }

    CHARACTERS = {
        "icon": "👥",
        "title": "暂无角色",
        "description": "添加故事中的角色。\n详细的角色设定有助于创作生动的人物。",
        "action_text": "添加角色"
    }

    WORLD = {
        "icon": "🌍",
        "title": "世界观为空",
        "description": "构建你的故事世界设定。\n包括地点、文化、历史等背景信息。",
        "action_text": "添加设定"
    }

    FACTIONS = {
        "icon": "⚔️",
        "title": "暂无势力",
        "description": "添加故事中的势力和阵营。\n势力关系矩阵可以帮助管理复杂的阵营对抗。",
        "action_text": "添加势力"
    }

    ASSETS = {
        "icon": "🖼️",
        "title": "暂无资源",
        "description": "上传角色立绘、背景图等视觉资源。\n用于视觉小说和剧情游戏导出。",
        "action_text": "添加资源"
    }

    @classmethod
    def get(cls, name: str) -> dict:
        """Get a predefined configuration by name."""
        return getattr(cls, name.upper(), cls.SCENES)
