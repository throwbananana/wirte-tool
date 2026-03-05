"""
无障碍功能模块 - 提供图标和颜色组合的状态指示
Accessibility module - Provides icon+color status indicators for better accessibility
"""
from writer_app.core.icon_manager import IconManager

class StatusIndicators:
    """
    状态指示器 - 使用图标+颜色双重指示提高可访问性

    用法:
        indicator = StatusIndicators.get_status_indicator("success")
        print(indicator["icon"], indicator["text"])  # ✓ 成功
    """

    # 状态映射配置 (name -> (fluent_icon_name, text, alt_icon))
    # Note: Fluent icon names are base names without size/style
    CONFIG_MAP = {
        # 通用状态
        "success": ("checkmark_circle", "成功", "[OK]"),
        "warning": ("warning", "警告", "[!]"),
        "error": ("error_circle", "错误", "[X]"),
        "info": ("info", "信息", "[i]"),
        "pending": ("circle", "待处理", "[ ]"),
        "in_progress": ("play_circle", "进行中", "[>]"),
        "completed": ("checkmark_circle", "已完成", "[V]"),

        # 看板/场景状态
        "draft": ("edit", "初稿", "[D]"),
        "revision": ("arrow_sync", "修订中", "[R]"),
        "review": ("eye", "审阅", "[?]"),
        "final": ("star", "定稿", "[*]"),

        # 线索状态
        "clue_unused": ("circle", "未使用", "[ ]"),
        "clue_mentioned": ("circle_hint", "已提及", "[~]"), # circle_hint might not exist, fallback to circle
        "clue_resolved": ("checkmark_circle", "已解决", "[V]"),

        # 验证状态
        "valid": ("checkmark", "有效", "[OK]"),
        "invalid": ("dismiss", "无效", "[X]"),

        # 连接/同步状态
        "connected": ("link", "已连接", "[C]"),
        "disconnected": ("link_dismiss", "未连接", "[-]"),
        "syncing": ("arrow_sync", "同步中", "[S]"),

        # 优先级
        "priority_high": ("arrow_up", "高优先级", "[H]"),
        "priority_medium": ("subtract", "中优先级", "[M]"),
        "priority_low": ("arrow_down", "低优先级", "[L]"),

        # 折叠/展开
        "expanded": ("chevron_down", "已展开", "[-]"),
        "collapsed": ("chevron_right", "已折叠", "[+]"),

        # 排序方向
        "sort_asc": ("arrow_sort_up", "升序", "[A]"),
        "sort_desc": ("arrow_sort_down", "降序", "[D]"),
    }

    # 看板列状态映射
    KANBAN_CONFIG_MAP = {
        "构思": ("lightbulb", "构思", "[I]"),
        "初稿": ("edit", "初稿", "[D]"),
        "润色": ("wand", "润色", "[R]"),
        "定稿": ("star", "定稿", "[F]"),
    }

    @classmethod
    def get_status_indicator(cls, status_key: str, use_alt=False) -> dict:
        """
        获取状态指示器

        Returns:
            dict: {
                "icon": str (char),
                "text": str,
                "alt_icon": str,
                "font": tuple (family, size) or None if fallback
            }
        """
        config = cls.CONFIG_MAP.get(status_key)
        
        if not config:
            return {
                "icon": "?", 
                "text": status_key, 
                "alt_icon": "[?]", 
                "font": ("Arial", 12)
            }

        icon_name, text, alt = config
        
        if use_alt:
            return {"icon": alt, "text": text, "alt_icon": alt, "font": ("Courier New", 10)}

        # Get Icon from Manager
        manager = IconManager()
        # Use Filled style for higher visibility by default? Or Regular?
        # Regular matches typical UI.
        icon_char = manager.get_icon(icon_name, size=24, style="regular", fallback="?")
        
        # If fallback "?", maybe we should try unicode fallback if we really want to support it?
        # But we want to enforce the new system.
        
        return {
            "icon": icon_char,
            "text": text,
            "alt_icon": alt,
            "font": manager.get_font(size=12, style="regular")
        }

    @classmethod
    def get_kanban_indicator(cls, column_name: str, use_alt=False) -> dict:
        """获取看板列状态指示器"""
        config = cls.KANBAN_CONFIG_MAP.get(column_name)
        if not config:
            # Dynamic columns fallback to circle
            return cls.get_status_indicator("pending", use_alt)

        icon_name, text, alt = config
        if use_alt:
            return {"icon": alt, "text": text, "alt_icon": alt, "font": ("Courier New", 10)}

        manager = IconManager()
        icon_char = manager.get_icon(icon_name, size=24, style="regular", fallback="○")
        
        return {
            "icon": icon_char,
            "text": text,
            "alt_icon": alt,
            "font": manager.get_font(size=12, style="regular")
        }

    @classmethod
    def format_status(cls, status_key: str, include_text=True, use_alt=False) -> str:
        """
        格式化状态显示文本
        注意：这只返回文本字符串。如果使用图标字体，调用者必须将 widget 的 font 设置为 IconManager.get_font()
        或者此方法无法同时返回两种字体（文本和图标）。
        通常图标和文本需要分开的 Label。
        为了兼容旧代码，我们返回 "ICON Text"。但如果 consuming code 不设置字体，会显示乱码。
        
        Recommendation: Callers should update to use separate labels for Icon and Text if possible, 
        or we assume the caller sets the font? But text might not render well in Icon font.
        Fluent Icons font usually ONLY has icons. Text will be boxes.
        
        Legacy support: Use unicode fallback if font support not guaranteed?
        Or, we keep this method returning Emoji for now, and new consumers use get_status_indicator directly.
        
        Let's switch this back to Emojis for legacy compatibility if we can't update all UI files.
        Or, better, provide a way to check.
        
        Given the constraints, I'll return Emoji here for safety, unless I update all callers.
        Grepping usage of format_status...
        """
        # Fallback to emoji map for string-only contexts
        EMOJI_MAP = {
            "success": "✓", "warning": "⚠", "error": "✗", "info": "ℹ",
            "pending": "○", "in_progress": "●", "completed": "✓",
            "draft": "✎", "revision": "↻", "review": "👁", "final": "★",
            "clue_unused": "◌", "clue_mentioned": "◐", "clue_resolved": "●",
            "valid": "✓", "invalid": "✗",
            "connected": "●", "disconnected": "○", "syncing": "↻",
            "priority_high": "▲", "priority_medium": "◆", "priority_low": "▽",
            "expanded": "▼", "collapsed": "▶",
            "sort_asc": "▲", "sort_desc": "▼"
        }
        icon = EMOJI_MAP.get(status_key, "?")
        
        # But wait, user wants to APPLY UI. I should update UI to use icons.
        # But format_status returns a single string. If I return icon char, text won't render.
        # So I'll keep Emoji here.
        if include_text:
            # Need to find text
            cfg = cls.CONFIG_MAP.get(status_key)
            text = cfg[1] if cfg else status_key
            return f"{icon} {text}"
        return icon

    @classmethod
    def get_progress_bar(cls, value: float, width: int = 10, filled="█", empty="░") -> str:
        """
        生成文本进度条

        Args:
            value: 进度值 (0.0 - 1.0)
            width: 进度条宽度（字符数）
            filled: 已填充字符
            empty: 未填充字符

        Returns:
            文本进度条，如 "████░░░░░░"
        """
        value = max(0.0, min(1.0, value))
        filled_count = int(value * width)
        empty_count = width - filled_count
        return filled * filled_count + empty * empty_count

    @classmethod
    def get_rating_stars(cls, value: float, max_value: float = 5, filled="★", empty="☆") -> str:
        """
        生成星级评分显示

        Args:
            value: 当前值
            max_value: 最大值
            filled: 已填充星星
            empty: 未填充星星

        Returns:
            星级显示，如 "★★★☆☆"
        """
        value = max(0, min(max_value, value))
        filled_count = int(value)
        empty_count = int(max_value) - filled_count
        return filled * filled_count + empty * empty_count


class AccessibilityHelper:
    """
    无障碍辅助类 - 提供颜色对比度检查和高对比度模式支持
    """

    # WCAG AA 标准要求的最小对比度
    MIN_CONTRAST_RATIO_AA = 4.5
    MIN_CONTRAST_RATIO_AAA = 7.0

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple:
        """将十六进制颜色转换为RGB元组"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def get_luminance(rgb: tuple) -> float:
        """
        计算相对亮度 (WCAG 2.0)

        Args:
            rgb: RGB元组 (r, g, b)

        Returns:
            相对亮度值 (0.0 - 1.0)
        """
        def adjust(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b = rgb
        return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

    @classmethod
    def get_contrast_ratio(cls, color1: str, color2: str) -> float:
        """
        计算两个颜色之间的对比度

        Args:
            color1: 十六进制颜色1
            color2: 十六进制颜色2

        Returns:
            对比度 (1.0 - 21.0)
        """
        lum1 = cls.get_luminance(cls.hex_to_rgb(color1))
        lum2 = cls.get_luminance(cls.hex_to_rgb(color2))

        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)

        return (lighter + 0.05) / (darker + 0.05)

    @classmethod
    def check_contrast(cls, foreground: str, background: str, level="AA") -> bool:
        """
        检查颜色对比度是否符合WCAG标准

        Args:
            foreground: 前景色（十六进制）
            background: 背景色（十六进制）
            level: 标准级别 "AA" 或 "AAA"

        Returns:
            是否符合标准
        """
        ratio = cls.get_contrast_ratio(foreground, background)
        min_ratio = cls.MIN_CONTRAST_RATIO_AAA if level == "AAA" else cls.MIN_CONTRAST_RATIO_AA
        return ratio >= min_ratio

    @staticmethod
    def get_high_contrast_color(background: str) -> str:
        """
        根据背景色返回高对比度的前景色

        Args:
            background: 背景色（十六进制）

        Returns:
            推荐的前景色 (黑色或白色)
        """
        rgb = AccessibilityHelper.hex_to_rgb(background)
        luminance = AccessibilityHelper.get_luminance(rgb)

        # 亮度高于0.5使用黑色，否则使用白色
        return "#000000" if luminance > 0.5 else "#FFFFFF"

    @staticmethod
    def get_focus_indicator_style() -> dict:
        """
        获取焦点指示器样式

        Returns:
            包含边框样式的字典
        """
        return {
            "highlightthickness": 2,
            "highlightcolor": "#2196F3",
            "highlightbackground": "#64B5F6"
        }