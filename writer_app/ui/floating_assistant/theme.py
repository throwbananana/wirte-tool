"""
悬浮助手主题管理 (Floating Assistant Theme Manager)
集中管理颜色、字体和样式配置，支持深色/浅色模式切换
"""
from dataclasses import dataclass

@dataclass
class AssistantTheme:
    # 基础背景
    BG_PRIMARY: str
    BG_SECONDARY: str  # 输入框、列表项
    BG_TERTIARY: str   # 聊天显示区
    
    # 强调色
    ACCENT_COLOR: str  # 按钮、工具栏
    ACCENT_HOVER: str
    
    # 文本颜色
    TEXT_PRIMARY: str
    TEXT_SECONDARY: str # 提示文本、次要信息
    TEXT_ON_ACCENT: str # 强调色背景上的文字
    
    # 状态色
    COLOR_SUCCESS: str
    COLOR_WARNING: str
    COLOR_ERROR: str
    
    # 特殊
    TRANSPARENT_KEY: str # 透明抠图色
    
    # 字体
    FONT_FAMILY: str
    FONT_SIZE_MAIN: int
    FONT_SIZE_SMALL: int

# 预设深色主题 (默认)
DARK_THEME = AssistantTheme(
    BG_PRIMARY="#2D2D2D",
    BG_SECONDARY="#3D3D3D",
    BG_TERTIARY="#1E1E1E",
    ACCENT_COLOR="#1E88E5",
    ACCENT_HOVER="#1976D2",
    TEXT_PRIMARY="#FFFFFF",
    TEXT_SECONDARY="#B0BEC5",
    TEXT_ON_ACCENT="#FFFFFF",
    COLOR_SUCCESS="#81C784",
    COLOR_WARNING="#FFB74D",
    COLOR_ERROR="#EF5350",
    TRANSPARENT_KEY="#000001",
    FONT_FAMILY="Microsoft YaHei",
    FONT_SIZE_MAIN=9,
    FONT_SIZE_SMALL=8
)

# 预设浅色主题
LIGHT_THEME = AssistantTheme(
    BG_PRIMARY="#F5F5F5",
    BG_SECONDARY="#FFFFFF",
    BG_TERTIARY="#E0E0E0", # 聊天背景稍深一点
    ACCENT_COLOR="#2196F3",
    ACCENT_HOVER="#1E88E5",
    TEXT_PRIMARY="#212121",
    TEXT_SECONDARY="#757575",
    TEXT_ON_ACCENT="#FFFFFF",
    COLOR_SUCCESS="#4CAF50",
    COLOR_WARNING="#FF9800",
    COLOR_ERROR="#F44336",
    TRANSPARENT_KEY="#000001",
    FONT_FAMILY="Microsoft YaHei",
    FONT_SIZE_MAIN=9,
    FONT_SIZE_SMALL=8
)

class ThemeManager:
    _current_theme = DARK_THEME
    
    @classmethod
    def get_theme(cls) -> AssistantTheme:
        return cls._current_theme
    
    @classmethod
    def set_mode(cls, mode: str):
        if mode == "Light":
            cls._current_theme = LIGHT_THEME
        else:
            cls._current_theme = DARK_THEME
