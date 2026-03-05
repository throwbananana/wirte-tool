"""
资源加载与管理模块

提供:
- 资源预加载器 (ResourceLoader)
- 资产类型注册表 (AssetTypeRegistry)
"""

import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

@dataclass
class AssetTypeInfo:
    """资产类型信息。"""
    key: str                      # 内部键名 (如 sprite, evidence_photo)
    display_name: str             # 显示名称 (如 "立绘", "证据照片")
    icon: str                     # 图标 (emoji)
    color: str                    # 占位符颜色 (hex)
    file_extensions: List[str]   # 支持的扩展名
    category: str = "general"     # 分类 (image, audio, document, other)
    description: str = ""         # 描述


class AssetTypeRegistry:
    """
    资产类型注册表 - 管理所有可用的资产类型定义。

    这是一个全局配置，定义了各种资产类型的显示属性和文件类型。
    项目类型通过 asset_types 列表引用这些定义。
    """

    # 所有已注册的资产类型
    _types: Dict[str, AssetTypeInfo] = {}

    # 默认内置类型
    BUILTIN_TYPES: Dict[str, Dict[str, Any]] = {
        # Galgame 类型
        "sprite": {
            "display_name": "立绘",
            "icon": get_icon("person", "👤"),
            "color": "#4a7c59",
            "file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
            "category": "image",
            "description": "角色立绘图片"
        },
        "background": {
            "display_name": "背景",
            "icon": get_icon("image", "🏞️"),
            "color": "#4a5c7c",
            "file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
            "category": "image",
            "description": "场景背景图片"
        },
        "cg": {
            "display_name": "CG",
            "icon": get_icon("image_copy", "🖼️"),
            "color": "#7c4a6d",
            "file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
            "category": "image",
            "description": "事件CG图片"
        },
        "ui": {
            "display_name": "UI素材",
            "icon": get_icon("color", "🎨"),
            "color": "#7c6a4a",
            "file_extensions": [".png", ".jpg", ".webp", ".svg"],
            "category": "image",
            "description": "用户界面素材"
        },

        # 悬疑类型
        "evidence_photo": {
            "display_name": "证据照片",
            "icon": get_icon("camera", "📷"),
            "color": "#8b4513",
            "file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
            "category": "image",
            "description": "物证、场景照片"
        },
        "location_photo": {
            "display_name": "地点照片",
            "icon": get_icon("map", "🗺️"),
            "color": "#2f4f4f",
            "file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
            "category": "image",
            "description": "地点参考照片"
        },

        # 通用类型
        "reference": {
            "display_name": "参考资料",
            "icon": get_icon("attach", "📎"),
            "color": "#555555",
            "file_extensions": [".png", ".jpg", ".pdf", ".docx", ".txt"],
            "category": "document",
            "description": "写作参考资料"
        },
        "character_image": {
            "display_name": "角色图片",
            "icon": get_icon("person", "👤"),
            "color": "#6b8e23",
            "file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
            "category": "image",
            "description": "角色形象参考"
        },
        "mood_board": {
            "display_name": "情绪板",
            "icon": get_icon("board", "🎭"),
            "color": "#db7093",
            "file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
            "category": "image",
            "description": "氛围/情绪参考图"
        },
        "map": {
            "display_name": "地图",
            "icon": get_icon("map", "🗺️"),
            "color": "#228b22",
            "file_extensions": [".png", ".jpg", ".svg", ".webp"],
            "category": "image",
            "description": "世界/区域地图"
        },
        "tech_diagram": {
            "display_name": "技术图示",
            "icon": get_icon("settings", "⚙️"),
            "color": "#4682b4",
            "file_extensions": [".png", ".jpg", ".svg", ".webp"],
            "category": "image",
            "description": "科技/机械设计图"
        },
        "illustration": {
            "display_name": "插图",
            "icon": get_icon("edit", "🖌️"),
            "color": "#da70d6",
            "file_extensions": [".png", ".jpg", ".jpeg", ".webp"],
            "category": "image",
            "description": "小说插图"
        },

        # 音频类型
        "bgm": {
            "display_name": "背景音乐",
            "icon": get_icon("music", "🎵"),
            "color": "#9932cc",
            "file_extensions": [".mp3", ".ogg", ".wav", ".flac"],
            "category": "audio",
            "description": "背景音乐"
        },
        "sfx": {
            "display_name": "音效",
            "icon": get_icon("speaker_2", "🔊"),
            "color": "#ff6347",
            "file_extensions": [".mp3", ".ogg", ".wav"],
            "category": "audio",
            "description": "场景音效"
        },
        "voice": {
            "display_name": "语音",
            "icon": get_icon("mic", "🎤"),
            "color": "#20b2aa",
            "file_extensions": [".mp3", ".ogg", ".wav"],
            "category": "audio",
            "description": "角色配音"
        },
    }

    @classmethod
    def _ensure_builtin(cls) -> None:
        """确保内置类型已注册。"""
        if not cls._types:
            for key, info in cls.BUILTIN_TYPES.items():
                cls._types[key] = AssetTypeInfo(key=key, **info)

    @classmethod
    def register(cls, asset_type: AssetTypeInfo) -> None:
        """注册新的资产类型。"""
        cls._ensure_builtin()
        cls._types[asset_type.key] = asset_type

    @classmethod
    def get(cls, key: str) -> Optional[AssetTypeInfo]:
        """获取资产类型信息。"""
        cls._ensure_builtin()
        return cls._types.get(key)

    @classmethod
    def get_display_name(cls, key: str) -> str:
        """获取资产类型的显示名称。"""
        info = cls.get(key)
        return info.display_name if info else key

    @classmethod
    def get_icon(cls, key: str) -> str:
        """获取资产类型的图标。"""
        info = cls.get(key)
        return info.icon if info else get_icon("folder", "📁")

    @classmethod
    def get_color(cls, key: str) -> str:
        """获取资产类型的颜色。"""
        info = cls.get(key)
        return info.color if info else "#555"

    @classmethod
    def get_file_filter(cls, key: str) -> List[tuple]:
        """获取资产类型的文件过滤器（用于文件对话框）。"""
        info = cls.get(key)
        if not info:
            return [("所有文件", "*.*")]

        exts = " ".join(f"*{ext}" for ext in info.file_extensions)
        return [(f"{info.display_name}文件", exts), ("所有文件", "*.*")]

    @classmethod
    def get_all_keys(cls) -> List[str]:
        """获取所有已注册的资产类型键。"""
        cls._ensure_builtin()
        return list(cls._types.keys())

    @classmethod
    def get_by_category(cls, category: str) -> List[AssetTypeInfo]:
        """按分类获取资产类型列表。"""
        cls._ensure_builtin()
        return [t for t in cls._types.values() if t.category == category]

    @classmethod
    def get_info_for_types(cls, type_keys: List[str]) -> List[AssetTypeInfo]:
        """获取指定类型键列表的完整信息。"""
        cls._ensure_builtin()
        result = []
        for key in type_keys:
            info = cls._types.get(key)
            if info:
                result.append(info)
        return result


class ResourceLoader:
    """
    Simple background resource preloader for images and audio.
    Used in Galgame mode to ensure smooth playback.
    """
    def __init__(self):
        self._cache = {}
        self._queue = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def preload(self, paths):
        """Add paths to preload queue."""
        with self._lock:
            for p in paths:
                if p and p not in self._cache and p not in self._queue:
                    self._queue.append(p)

    def get(self, path):
        """Get resource from cache (if loaded), else return path (lazy)."""
        return self._cache.get(path, path)

    def _worker(self):
        while not self._stop_event.is_set():
            path_to_load = None
            with self._lock:
                if self._queue:
                    path_to_load = self._queue.pop(0)
            
            if path_to_load:
                self._load_file(path_to_load)
            else:
                time.sleep(0.1)

    def _load_file(self, path):
        # Simulate loading / OS caching. 
        # For actual Python objects (like PIL Image or PyGame sound), 
        # we would load them here and store in _cache.
        # Since Tkinter images must be loaded in main thread usually, 
        # and audio players handle their own buffering, 
        # this is mostly to warm up the OS file cache or download remote assets.
        
        # If we were using PyGame:
        # sound = pygame.mixer.Sound(path)
        # self._cache[path] = sound
        
        try:
            p = Path(path)
            if p.exists():
                with open(p, "rb") as f:
                    # Read to memory to warm up OS cache
                    f.read()
                # Mark as cached
                self._cache[path] = True
        except Exception as e:
            print(f"Failed to preload {path}: {e}")

    def stop(self):
        self._stop_event.set()