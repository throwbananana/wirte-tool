"""
字体管理器 (Font Manager)
负责动态加载本地字体文件 (.ttf, .otf)，使其在 Tkinter 和 PDF 导出中可用。
无需安装到 Windows 系统目录。
"""
import os
import logging
import platform
import glob
from pathlib import Path
import tkinter.font as tkfont
import ctypes
from ctypes import wintypes

logger = logging.getLogger(__name__)

class FontManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.fonts_dir = Path("writer_data") / "fonts"
        self._loaded_fonts = []
        self._ensure_dir()
        self._initialized = True

    def _ensure_dir(self):
        if not self.fonts_dir.exists():
            self.fonts_dir.mkdir(parents=True, exist_ok=True)

    def load_local_fonts(self):
        """扫描并加载本地字体"""
        if platform.system() != "Windows":
            logger.warning("动态字体加载目前仅支持 Windows 系统")
            return

        font_files = list(self.fonts_dir.glob("*.[to]tf")) # .ttf or .otf
        count = 0
        
        for font_path in font_files:
            if self._load_font_windows(str(font_path)):
                self._loaded_fonts.append(font_path)
                count += 1
        
        if count > 0:
            logger.info(f"已加载 {count} 个本地字体")
            # 强制 Tkinter 刷新字体缓存（某些版本需要创建一次字体对象）
            try:
                tkfont.families()
            except Exception:
                pass

    def _load_font_windows(self, font_path: str) -> bool:
        """调用 Windows GDI API 加载字体"""
        try:
            # GDI32.AddFontResourceExW
            # FR_PRIVATE = 0x10 (指定字体为当前进程私有，无需安装)
            # FR_NOT_ENUM = 0x20
            FR_PRIVATE = 0x10
            
            gdi32 = ctypes.windll.gdi32
            # AddFontResourceExW returns the number of fonts added
            num_fonts_added = gdi32.AddFontResourceExW(
                ctypes.c_wchar_p(font_path), 
                FR_PRIVATE, 
                0
            )
            return num_fonts_added > 0
        except Exception as e:
            logger.error(f"加载字体失败 {font_path}: {e}")
            return False

    def get_available_families(self, include_vertical=False) -> list:
        """获取所有可用字体族（包括系统字体和已加载的本地字体）"""
        # 获取 Tkinter 识别到的所有字体
        try:
            root = None
            import tkinter
            # 如果没有 root，临时创建一个（通常此时已有 root）
            try:
                root = tkinter._default_root
            except AttributeError:
                pass
            
            if not root:
                return []

            families = list(tkfont.families(root))
            families.sort()
            
            # 过滤掉以 @ 开头的竖排字体，除非显式请求
            if not include_vertical:
                families = [f for f in families if not f.startswith('@')]
                
            return families
        except Exception as e:
            logger.error(f"获取字体列表失败: {e}")
            return []

    def register_for_reportlab(self):
        """为 PDF 导出注册字体"""
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFError, TTFont
            
            for font_path in self._loaded_fonts:
                try:
                    # 尝试用文件名作为字体名（去除后缀）
                    font_name = font_path.stem
                    # 对于中文字体，最好手动指定一个英文名，但这里自动注册
                    # 注意：ReportLab 需要确切的字体内部名称，这里只是简单注册文件
                    # 复杂的字体家族（Bold/Italic）处理比较麻烦，这里做基础支持
                    pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                    logger.info(f"ReportLab 字体注册成功: {font_name}")
                except Exception as e:
                    logger.warning(f"ReportLab 字体注册失败 {font_path}: {e}")
                    
        except ImportError:
            pass

# 全局访问点
def get_font_manager():
    return FontManager()
