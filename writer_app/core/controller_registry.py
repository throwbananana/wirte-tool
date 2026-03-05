"""
控制器注册表 - 统一管理所有UI控制器的注册、刷新和销毁

用法:
    from writer_app.core.controller_registry import ControllerRegistry, RefreshGroups, Capabilities

    registry = ControllerRegistry()

    # 注册控制器，指定刷新分组和能力
    registry.register("script", script_controller,
                     refresh_groups=["scene", "character"],
                     capabilities=["ai_mode", "theme"])
    registry.register("timeline", timeline_controller,
                     refresh_groups=["scene", "timeline"],
                     capabilities=["theme"])

    # 按分组刷新
    registry.refresh_group("scene")  # 只刷新场景相关的控制器

    # 按能力获取控制器
    ai_controllers = registry.get_controllers_with_capability("ai_mode")

    # 全量刷新
    registry.refresh_all()
"""

from typing import Dict, List, Optional, Any, Callable, Set
import logging

logger = logging.getLogger(__name__)


class ControllerRegistry:
    """
    统一管理所有控制器的注册、刷新和销毁。

    解决的问题:
    - 消除 main.py 中 76 处 hasattr 检查
    - 实现精细化刷新（按事件类型分组）
    - 统一控制器生命周期管理
    """

    def __init__(self):
        self._controllers: Dict[str, Any] = {}
        self._refresh_groups: Dict[str, List[str]] = {}
        self._tab_frames: Dict[str, Any] = {}  # 存储 tab frame 引用
        self._capabilities: Dict[str, Set[str]] = {}  # capability -> set of controller keys

    def register(self, key: str, controller: Any,
                 refresh_groups: Optional[List[str]] = None,
                 tab_frame: Any = None,
                 capabilities: Optional[List[str]] = None) -> None:
        """
        注册控制器。

        Args:
            key: 控制器唯一标识（如 "script", "timeline"）
            controller: 控制器实例（必须有 refresh() 方法）
            refresh_groups: 刷新分组列表（如 ["scene", "character"]）
            tab_frame: 关联的 tab frame（用于 notebook 切换）
            capabilities: 控制器能力列表（如 ["ai_mode", "theme"]）
        """
        if key in self._controllers:
            logger.warning(f"控制器 '{key}' 已存在，将被覆盖")
            # 清理旧的能力注册
            for cap_set in self._capabilities.values():
                cap_set.discard(key)

        self._controllers[key] = controller

        # 注册到刷新分组
        for group in (refresh_groups or ["all"]):
            if group not in self._refresh_groups:
                self._refresh_groups[group] = []
            if key not in self._refresh_groups[group]:
                self._refresh_groups[group].append(key)

        # 存储 tab frame
        if tab_frame is not None:
            self._tab_frames[key] = tab_frame

        # 注册能力
        for cap in (capabilities or []):
            if cap not in self._capabilities:
                self._capabilities[cap] = set()
            self._capabilities[cap].add(key)

        caps_str = f", 能力: {capabilities}" if capabilities else ""
        logger.debug(f"注册控制器: {key}, 分组: {refresh_groups or ['all']}{caps_str}")

    def unregister(self, key: str) -> bool:
        """
        注销控制器。

        Args:
            key: 控制器标识

        Returns:
            是否成功注销
        """
        if key not in self._controllers:
            return False

        del self._controllers[key]
        self._tab_frames.pop(key, None)

        # 从所有分组中移除
        for group in self._refresh_groups.values():
            if key in group:
                group.remove(key)

        # 从所有能力中移除
        for cap_set in self._capabilities.values():
            cap_set.discard(key)

        logger.debug(f"注销控制器: {key}")
        return True

    def get(self, key: str) -> Optional[Any]:
        """获取控制器。"""
        return self._controllers.get(key)

    def has(self, key: str) -> bool:
        """检查控制器是否存在。"""
        return key in self._controllers

    def get_tab_frame(self, key: str) -> Optional[Any]:
        """获取控制器关联的 tab frame。"""
        return self._tab_frames.get(key)

    def get_controllers_with_capability(self, capability: str) -> List[str]:
        """
        获取具有特定能力的所有控制器键。

        Args:
            capability: 能力名称（如 "ai_mode", "theme"）

        Returns:
            控制器键列表
        """
        return list(self._capabilities.get(capability, set()))

    def has_capability(self, key: str, capability: str) -> bool:
        """
        检查控制器是否具有特定能力。

        Args:
            key: 控制器键
            capability: 能力名称

        Returns:
            是否具有该能力
        """
        return key in self._capabilities.get(capability, set())

    def call_on_controllers_with_capability(
        self,
        capability: str,
        method_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        对具有特定能力的所有控制器调用指定方法。

        Args:
            capability: 能力名称
            method_name: 要调用的方法名
            *args, **kwargs: 传递给方法的参数

        Returns:
            控制器键 -> 返回值的字典
        """
        results = {}
        for key in self.get_controllers_with_capability(capability):
            controller = self._controllers.get(key)
            if controller and hasattr(controller, method_name):
                try:
                    method = getattr(controller, method_name)
                    results[key] = method(*args, **kwargs)
                except Exception as e:
                    logger.error(f"调用 {key}.{method_name} 失败: {e}", exc_info=True)
                    results[key] = None
        return results

    def refresh_group(self, group: str) -> int:
        """
        刷新特定分组的控制器。

        Args:
            group: 分组名称（如 "scene", "character", "outline"）

        Returns:
            刷新的控制器数量
        """
        count = 0
        for key in self._refresh_groups.get(group, []):
            if key in self._controllers:
                try:
                    controller = self._controllers[key]
                    if hasattr(controller, 'refresh'):
                        controller.refresh()
                        count += 1
                except Exception as e:
                    logger.error(f"刷新控制器 '{key}' 失败: {e}", exc_info=True)
        return count

    def refresh_multiple_groups(self, groups: List[str]) -> int:
        """
        刷新多个分组的控制器（去重）。

        Args:
            groups: 分组名称列表

        Returns:
            刷新的控制器数量
        """
        refreshed_keys = set()
        count = 0

        for group in groups:
            for key in self._refresh_groups.get(group, []):
                if key not in refreshed_keys and key in self._controllers:
                    try:
                        controller = self._controllers[key]
                        if hasattr(controller, 'refresh'):
                            controller.refresh()
                            refreshed_keys.add(key)
                            count += 1
                    except Exception as e:
                        logger.error(f"刷新控制器 '{key}' 失败: {e}", exc_info=True)

        return count

    def refresh_all(self) -> int:
        """
        刷新所有控制器。

        Returns:
            刷新的控制器数量
        """
        count = 0
        for key, controller in self._controllers.items():
            try:
                if hasattr(controller, 'refresh'):
                    controller.refresh()
                    count += 1
            except Exception as e:
                logger.error(f"刷新控制器 '{key}' 失败: {e}", exc_info=True)
        return count

    def cleanup_all(self) -> None:
        """清理所有控制器资源。"""
        for key, controller in self._controllers.items():
            try:
                if hasattr(controller, 'cleanup'):
                    controller.cleanup()
                    logger.debug(f"清理控制器: {key}")
            except Exception as e:
                logger.error(f"清理控制器 '{key}' 失败: {e}", exc_info=True)

    def get_all_keys(self) -> List[str]:
        """获取所有已注册的控制器键。"""
        return list(self._controllers.keys())

    def get_groups(self) -> Dict[str, List[str]]:
        """获取所有刷新分组。"""
        return dict(self._refresh_groups)

    def __contains__(self, key: str) -> bool:
        """支持 'in' 操作符。"""
        return key in self._controllers

    def __len__(self) -> int:
        """返回控制器数量。"""
        return len(self._controllers)


# 预定义的刷新分组常量
class RefreshGroups:
    """刷新分组常量。"""
    SCENE = "scene"
    CHARACTER = "character"
    OUTLINE = "outline"
    WIKI = "wiki"
    TIMELINE = "timeline"
    RELATIONSHIP = "relationship"
    KANBAN = "kanban"
    EVIDENCE = "evidence"
    ASSET = "asset"
    ANALYTICS = "analytics"
    ALL = "all"


# 预定义的控制器能力常量
class Capabilities:
    """控制器能力常量，用于批量操作。"""
    AI_MODE = "ai_mode"           # 支持AI模式开关
    THEME = "theme"               # 支持主题切换
    EXPORT = "export"             # 支持导出功能
    SEARCH = "search"             # 支持搜索功能
    UNDO_REDO = "undo_redo"       # 支持撤销/重做
    AUTO_SAVE = "auto_save"       # 支持自动保存
    FOCUS_MODE = "focus_mode"     # 支持专注模式


# 控制器-分组映射建议
CONTROLLER_GROUP_MAPPING = {
    "script": [RefreshGroups.SCENE, RefreshGroups.CHARACTER],
    "timeline": [RefreshGroups.SCENE, RefreshGroups.TIMELINE],
    "kanban": [RefreshGroups.SCENE, RefreshGroups.KANBAN],
    "calendar": [RefreshGroups.SCENE],
    "swimlane": [RefreshGroups.SCENE],
    "story_curve": [RefreshGroups.SCENE],
    "relationship": [RefreshGroups.CHARACTER, RefreshGroups.RELATIONSHIP],
    "wiki": [RefreshGroups.WIKI, RefreshGroups.CHARACTER],
    "mindmap": [RefreshGroups.OUTLINE],
    "analytics": [RefreshGroups.ANALYTICS, RefreshGroups.OUTLINE],
    "dual_timeline": [RefreshGroups.TIMELINE],
    "alibi": [RefreshGroups.TIMELINE],
    "evidence_board": [RefreshGroups.EVIDENCE, RefreshGroups.SCENE, RefreshGroups.CHARACTER],
    "heartbeat": [RefreshGroups.CHARACTER],
    "iceberg": [RefreshGroups.WIKI],
    "faction": [RefreshGroups.RELATIONSHIP],
    "galgame_assets": [RefreshGroups.ASSET],
    "flowchart": [RefreshGroups.OUTLINE],
    "idea": [RefreshGroups.ALL],
    "research": [RefreshGroups.ALL],
}
