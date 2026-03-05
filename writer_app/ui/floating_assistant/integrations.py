"""
悬浮助手联动集成模块 (Floating Assistant Integration Module)

实现与writer_app核心系统的全面联动：
- EventBus事件订阅和响应
- GamificationManager游戏化系统集成
- Command执行支持Undo/Redo
- AIController工具调用联动
- 灵感/研究面板同步
- 统计数据显示
"""

import json
import random
import time
import math
from typing import Optional, Callable, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import threading
from writer_app.core.icon_manager import IconManager
from writer_app.core.module_recommendations import recommend_modules
from writer_app.core.scale_advisor import get_scale_metrics, recommend_scale
from writer_app.core.project_types import ProjectTypeManager
from writer_app.core.module_registry import get_module_display_name

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)


# 尝试导入核心模块
try:
    from writer_app.core.event_bus import get_event_bus, Events
    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False
    Events = None

try:
    from writer_app.core.commands import (
        AddCharacterCommand,
        AddSceneCommand,
        AddNodeCommand,
        AddWikiEntryCommand,
    )
    HAS_COMMANDS = True
except ImportError:
    HAS_COMMANDS = False

try:
    from writer_app.core.gamification import GamificationManager
    HAS_GAMIFICATION = True
except ImportError:
    HAS_GAMIFICATION = False

try:
    from writer_app.core.stats_manager import StatsManager
    HAS_STATS = True
except ImportError:
    HAS_STATS = False


class EventType(Enum):
    """助手内部事件类型"""
    PROJECT_LOADED = "project_loaded"
    SCENE_CHANGED = "scene_changed"
    CHARACTER_CHANGED = "character_changed"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    LEVEL_UP = "level_up"
    WORD_COUNT_MILESTONE = "word_count_milestone"
    VALIDATION_ISSUE = "validation_issue"


@dataclass
class ProjectContext:
    """项目上下文数据"""
    project_name: str = ""
    total_scenes: int = 0
    total_characters: int = 0
    total_words: int = 0
    current_scene_index: int = -1
    current_scene_name: str = ""
    current_scene_mood: str = ""
    recent_characters: List[str] = field(default_factory=list)
    project_type: str = "General"


class EventBusIntegration:
    """EventBus事件订阅和响应"""

    # 订阅的事件类型映射到处理方法
    EVENT_HANDLERS = {
        Events.SCENE_ADDED: "_on_scene_added",
        Events.SCENE_UPDATED: "_on_scene_updated",
        Events.SCENE_DELETED: "_on_scene_deleted",
        Events.CHARACTER_ADDED: "_on_character_added",
        Events.CHARACTER_UPDATED: "_on_character_updated",
        Events.CHARACTER_DELETED: "_on_character_deleted",
        Events.PROJECT_LOADED: "_on_project_loaded",
        Events.PROJECT_SAVED: "_on_project_saved",
        Events.OUTLINE_CHANGED: "_on_outline_changed",
        Events.VALIDATION_ISSUES_FOUND: "_on_validation_issues",
        Events.IDEA_ADDED: "_on_idea_added",
        Events.RESEARCH_ADDED: "_on_research_added",
        Events.EDITOR_CONTENT_CHANGED: "_on_editor_changed",
        # 模块使用统计（静默）
        Events.WIKI_ENTRY_ADDED: "_on_silent_event",
        Events.WIKI_ENTRY_UPDATED: "_on_silent_event",
        Events.WIKI_ENTRY_DELETED: "_on_silent_event",
        Events.TIMELINE_EVENT_ADDED: "_on_silent_event",
        Events.TIMELINE_EVENT_UPDATED: "_on_silent_event",
        Events.TIMELINE_EVENT_DELETED: "_on_silent_event",
        Events.EVIDENCE_NODE_ADDED: "_on_silent_event",
        Events.EVIDENCE_LINK_ADDED: "_on_silent_event",
        Events.CLUE_ADDED: "_on_silent_event",
        Events.KANBAN_TASK_ADDED: "_on_silent_event",
        Events.KANBAN_TASK_UPDATED: "_on_silent_event",
        Events.KANBAN_TASK_MOVED: "_on_silent_event",
        Events.RELATIONSHIP_LINK_ADDED: "_on_silent_event",
        Events.RELATIONSHIP_LINK_DELETED: "_on_silent_event",
        Events.GALGAME_ASSET_ADDED: "_on_silent_event",
        Events.ASSET_ADDED: "_on_silent_event",
        Events.ASSET_UPDATED: "_on_silent_event",
        Events.ASSET_DELETED: "_on_silent_event",
        Events.FACTION_ADDED: "_on_silent_event",
        Events.FACTION_RELATION_CHANGED: "_on_silent_event",
        # 专注模式事件
        Events.FOCUS_MODE_CHANGED: "_on_focus_mode_changed",
        Events.FOCUS_LEVEL_CHANGED: "_on_focus_level_changed",
        Events.TYPEWRITER_MODE_CHANGED: "_on_typewriter_mode_changed",
        Events.ZEN_MODE_ENTERED: "_on_zen_mode_entered",
        Events.ZEN_MODE_EXITED: "_on_zen_mode_exited",
        Events.FOCUS_SESSION_STARTED: "_on_focus_session_started",
        Events.FOCUS_SESSION_ENDED: "_on_focus_session_ended",
        Events.TRAINING_COMPLETED: "_on_silent_event",
    }

    def __init__(self, assistant, project_manager=None):
        self.assistant = assistant
        self.project_manager = project_manager
        self._event_bus = None
        self._subscribed = False
        self._callbacks: Dict[str, List[Callable]] = {}
        self._recommendation_history = {}
        self._recommendation_cooldown = 1800
        self._scale_advice_last_shown = 0
        self._scale_advice_cooldown = 3600

        if HAS_EVENT_BUS:
            self._event_bus = get_event_bus()

    def subscribe_all(self):
        """订阅所有关注的事件"""
        if not self._event_bus or self._subscribed:
            return

        for event_type in self.EVENT_HANDLERS.keys():
            self._event_bus.subscribe(event_type, self._dispatch_event)

        self._subscribed = True

    def unsubscribe_all(self):
        """取消所有订阅"""
        if not self._event_bus or not self._subscribed:
            return

        for event_type in self.EVENT_HANDLERS.keys():
            self._event_bus.unsubscribe(event_type, self._dispatch_event)

        self._subscribed = False

    def add_callback(self, event_type: str, callback: Callable):
        """添加外部回调"""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def _dispatch_event(self, event_type: str, **kwargs):
        """分发事件到对应处理器"""
        handler_name = self.EVENT_HANDLERS.get(event_type)
        if handler_name and hasattr(self, handler_name):
            try:
                handler = getattr(self, handler_name)
                handler(**kwargs)
            except Exception as e:
                print(f"事件处理错误 [{event_type}]: {e}")

        # 事件系统模块统计
        if hasattr(self.assistant, "event_system"):
            try:
                self.assistant.event_system.handle_project_event(event_type, **kwargs)
            except Exception:
                pass

        # 调用外部回调
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(event_type, **kwargs)
            except Exception:
                pass

    # ============================================================
    # 事件处理器
    # ============================================================

    def _on_scene_added(self, **kwargs):
        """场景添加事件"""
        scene_name = kwargs.get("scene_name", "新场景")
        self._notify_assistant("scene_change", f"新场景「{scene_name}」已添加！")
        self._update_assistant_mood("curious")

    def _on_scene_updated(self, **kwargs):
        """场景更新事件"""
        scene_name = kwargs.get("scene_name", "")
        if scene_name:
            self._notify_assistant("scene_change", f"场景「{scene_name}」已更新")

    def _on_scene_deleted(self, **kwargs):
        """场景删除事件"""
        self._notify_assistant("scene_change", "场景已删除")

    def _on_character_added(self, **kwargs):
        """角色添加事件"""
        char_name = kwargs.get("char_name", "新角色")
        self._notify_assistant("character_change", f"新角色「{char_name}」加入了故事！")
        self._update_assistant_mood("happy")

    def _on_character_updated(self, **kwargs):
        """角色更新事件"""
        char_name = kwargs.get("char_name", "")
        old_name = kwargs.get("old_name", "")
        if old_name and char_name != old_name:
            self._notify_assistant("character_change", f"角色「{old_name}」已更名为「{char_name}」")
        elif char_name:
            self._notify_assistant("character_change", f"角色「{char_name}」信息已更新")

    def _on_character_deleted(self, **kwargs):
        """角色删除事件"""
        char_name = kwargs.get("char_name", "")
        if char_name:
            self._notify_assistant("character_change", f"角色「{char_name}」已离开故事")
            self._update_assistant_mood("sad")

    def _on_project_loaded(self, **kwargs):
        """项目加载事件"""
        self._notify_assistant("project", "项目已加载，准备好开始创作了！")
        self._update_assistant_mood("happy")

        # 更新项目上下文
        if self.project_manager:
            self._update_project_context()
            if hasattr(self.assistant, "show_mode_guide"):
                self.assistant.show_mode_guide(self.project_manager.get_project_type())

    def _on_project_saved(self, **kwargs):
        """项目保存事件"""
        self._notify_assistant("project", "项目已保存~")
        self._update_assistant_mood("success")

    def _on_outline_changed(self, **kwargs):
        """大纲变化事件"""
        # 不需要每次都通知，可能太频繁
        pass

    def _on_validation_issues(self, **kwargs):
        """验证问题事件"""
        issues = kwargs.get("issues", [])
        count = len(issues)
        if count > 0:
            self._notify_assistant("validation", f"发现 {count} 个逻辑问题，需要注意哦~")
            self._update_assistant_mood("worried")

    def _on_idea_added(self, **kwargs):
        """灵感添加事件"""
        self._notify_assistant("idea", "新灵感已记录！")
        self._update_assistant_mood("excited")

    def _on_research_added(self, **kwargs):
        """研究资料添加事件"""
        self._notify_assistant("research", "研究资料已添加~")

    def _on_editor_changed(self, **kwargs):
        """编辑器内容变化事件"""
        # 记录写作活动，但不频繁通知
        word_count = kwargs.get("word_count", 0)
        if word_count > 0 and word_count % 500 == 0:
            self._notify_assistant("milestone", f"已写 {word_count} 字，继续加油！")
            self._update_assistant_mood("cheering")

        text_snippet = kwargs.get("text_snippet", "")
        if text_snippet:
            self._maybe_recommend_modules(text_snippet)
        self._maybe_recommend_scale()

    def _on_silent_event(self, **kwargs):
        """静默事件（仅用于统计，不提示）"""
        pass

    # ============================================================
    # 专注模式事件处理器
    # ============================================================

    def _on_focus_mode_changed(self, **kwargs):
        """专注模式变化事件"""
        enabled = kwargs.get("enabled", False)
        level = kwargs.get("level", "line")
        level_names = {
            "line": "行聚焦",
            "sentence": "句子聚焦",
            "paragraph": "段落聚焦",
            "dialogue": "对话聚焦"
        }
        level_name = level_names.get(level, level)

        if enabled:
            self._notify_assistant("focus", f"专注模式已开启 ({level_name})，加油写作！")
            self._update_assistant_mood("focused")
            # 进入专注时隐藏助手闲聊
            if hasattr(self.assistant, '_enter_focus_mode'):
                try:
                    self.assistant.after(0, self.assistant._enter_focus_mode)
                except Exception:
                    pass
        else:
            self._notify_assistant("focus", "专注模式已关闭，休息一下吧~")
            self._update_assistant_mood("normal")
            # 退出专注时恢复助手
            if hasattr(self.assistant, '_exit_focus_mode'):
                try:
                    self.assistant.after(0, self.assistant._exit_focus_mode)
                except Exception:
                    pass

    def _on_focus_level_changed(self, **kwargs):
        """专注级别变化事件"""
        new_level = kwargs.get("new_level", "line")
        level_names = {
            "line": "行聚焦",
            "sentence": "句子聚焦",
            "paragraph": "段落聚焦",
            "dialogue": "对话聚焦"
        }
        level_name = level_names.get(new_level, new_level)
        self._notify_assistant("focus", f"专注级别切换为: {level_name}")

    def _on_typewriter_mode_changed(self, **kwargs):
        """打字机模式变化事件"""
        enabled = kwargs.get("enabled", False)
        if enabled:
            self._update_assistant_mood("typing")

    def _on_zen_mode_entered(self, **kwargs):
        """禅模式进入事件"""
        self._notify_assistant("zen", "进入沉浸写作模式，享受创作吧！")
        self._update_assistant_mood("zen")
        # 禅模式下最小化助手干扰
        if hasattr(self.assistant, '_enter_zen_mode'):
            try:
                self.assistant.after(0, self.assistant._enter_zen_mode)
            except Exception:
                pass

    def _on_zen_mode_exited(self, **kwargs):
        """禅模式退出事件"""
        duration = kwargs.get("duration", 0)
        if duration > 60:  # 超过1分钟才显示统计
            minutes = int(duration // 60)
            self._notify_assistant("zen", f"沉浸写作结束，共持续 {minutes} 分钟，辛苦了！")
        else:
            self._notify_assistant("zen", "沉浸写作结束~")
        self._update_assistant_mood("happy")
        # 恢复助手
        if hasattr(self.assistant, '_exit_zen_mode'):
            try:
                self.assistant.after(0, self.assistant._exit_zen_mode)
            except Exception:
                pass

    def _on_focus_session_started(self, **kwargs):
        """专注会话开始事件"""
        level = kwargs.get("level", "line")
        # 记录开始时间用于统计
        self._focus_session_start = datetime.now()

    def _on_focus_session_ended(self, **kwargs):
        """专注会话结束事件"""
        duration = kwargs.get("duration", 0)
        level = kwargs.get("level", "line")

        # 向游戏化系统报告专注时长
        if duration > 60 and hasattr(self, '_focus_session_start'):
            minutes = int(duration // 60)
            # 通知外部回调（如游戏化系统）
            for callback in self._callbacks.get("focus_stats", []):
                try:
                    callback("focus_session_ended", duration=duration, level=level)
                except Exception:
                    pass

    # ============================================================
    # 辅助方法
    # ============================================================

    def _notify_assistant(self, event_type: str, message: str):
        """通知助手显示消息"""
        if hasattr(self.assistant, 'notification_manager'):
            # 使用通知管理器进行节流
            self.assistant.notification_manager.notify(
                message,
                "system",
                group_id=event_type
            )
        elif hasattr(self.assistant, '_append_message'):
            # 在主线程中执行
            try:
                self.assistant.after(0, lambda: self.assistant._append_message("system", message))
            except Exception:
                pass

    def _update_assistant_mood(self, mood: str):
        """更新助手心情/状态"""
        if hasattr(self.assistant, '_set_state'):
            from .states import AssistantState
            state_map = {
                "happy": AssistantState.HAPPY,
                "sad": AssistantState.SAD,
                "excited": AssistantState.EXCITED,
                "curious": AssistantState.CURIOUS,
                "worried": AssistantState.WORRIED,
                "cheering": AssistantState.CHEERING,
                "success": AssistantState.SUCCESS,
                # 专注模式状态
                "focused": AssistantState.FOCUSED,
                "zen": AssistantState.ZEN,
                "typing": AssistantState.TYPING,
                "normal": AssistantState.IDLE,
            }
            state = state_map.get(mood)
            if state:
                try:
                    # 专注/禅模式使用更长的持续时间
                    duration = 2000
                    if mood in ("focused", "zen", "typing"):
                        duration = 0  # 持续到下一个状态变化
                    self.assistant.after(0, lambda s=state, d=duration: self.assistant._set_state(s, duration=d))
                except Exception:
                    pass

    def _maybe_recommend_modules(self, text_snippet: str):
        if not self.project_manager:
            return
        enabled = self.project_manager.get_enabled_tools()
        recommendations = recommend_modules(text_snippet, enabled, max_results=1)
        if not recommendations:
            return
        now = time.time()
        for recommendation in recommendations:
            last = self._recommendation_history.get(recommendation.module_key, 0)
            if now - last < self._recommendation_cooldown:
                continue
            self._recommendation_history[recommendation.module_key] = now
            name = get_module_display_name(recommendation.module_key)
            message = f"检测到{recommendation.reason}，建议开启【{name}】模块。可直接点击下方按钮启用。"
            self._notify_assistant(
                f"module_recommendation_{recommendation.module_key}",
                message
            )
            self._update_assistant_mood("curious")
            self._show_module_actions(recommendation.module_key, name)

    def _maybe_recommend_scale(self):
        if not self.project_manager:
            return
        now = time.time()
        if now - self._scale_advice_last_shown < self._scale_advice_cooldown:
            return
        current_length = self.project_manager.get_project_length()
        metrics = get_scale_metrics(self.project_manager.get_project_data())
        recommendation = recommend_scale(current_length, metrics)
        if not recommendation:
            return

        project_type = self.project_manager.get_project_type()
        tags = self.project_manager.get_genre_tags()
        recommended_tools = ProjectTypeManager.get_default_tools_list(
            project_type,
            recommendation.target_length,
            tags
        )
        enabled = self.project_manager.get_enabled_tools()
        missing = [key for key in recommended_tools if key not in enabled]
        missing_names = [get_module_display_name(key) for key in missing]
        missing_preview = "、".join(missing_names[:3])
        missing_suffix = "..." if len(missing_names) > 3 else ""

        reasons = "、".join(recommendation.reasons)
        message = f"项目规模已达到长篇阈值（{reasons}）。建议切换为“长篇”。"
        if missing_preview:
            message += f"可开启：{missing_preview}{missing_suffix}。"
        message += "可在“项目设置”或“+ 工具箱”中启用。"

        self._notify_assistant("scale_hint", message)
        self._update_assistant_mood("curious")
        self._scale_advice_last_shown = now

    def _show_module_actions(self, module_key: str, module_name: str):
        if not hasattr(self.assistant, "chat_view"):
            return
        actions = [
            (f"开启 {module_name}", lambda: self._enable_module(module_key)),
            ("打开工具箱", lambda: self._open_module_catalog(module_key)),
            ("忽略", lambda: self._snooze_recommendation(module_key)),
        ]
        self.assistant.chat_view.show_action_buttons(actions)

    def _enable_module(self, module_key: str):
        if not self.project_manager:
            return
        enabled = set(self.project_manager.get_enabled_tools())
        if module_key in enabled:
            return
        enabled.add(module_key)
        self.project_manager.set_enabled_tools(list(enabled))
        name = get_module_display_name(module_key)
        self._notify_assistant("module_enabled", f"已开启【{name}】模块。")
        self._update_assistant_mood("success")

    def _open_module_catalog(self, module_key: str = None):
        if self._event_bus and Events:
            self._event_bus.publish(Events.OPEN_MODULE_CATALOG, module_key=module_key)

    def _snooze_recommendation(self, module_key: str):
        self._recommendation_history[module_key] = time.time()

    def _update_project_context(self):
        """更新项目上下文"""
        if not self.project_manager:
            return

        try:
            ctx = ProjectContext()
            script = self.project_manager.get_script()
            scenes = script.get("scenes", [])
            characters = script.get("characters", [])

            ctx.total_scenes = len(scenes)
            ctx.total_characters = len(characters)
            ctx.total_words = sum(len(s.get("content", "")) for s in scenes)
            ctx.recent_characters = [c.get("name", "") for c in characters[:5]]

            try:
                ctx.project_type = self.project_manager.get_project_type()
            except Exception:
                ctx.project_type = "General"

            # 存储到助手
            if hasattr(self.assistant, 'project_context'):
                self.assistant.project_context = ctx
        except Exception:
            pass

    def publish_event(self, event_type: str, **kwargs):
        """发布事件到EventBus"""
        if self._event_bus:
            try:
                self._event_bus.publish(event_type, **kwargs)
            except Exception as e:
                print(f"发布事件失败 [{event_type}]: {e}")

    def get_project_context(self) -> ProjectContext:
        """获取当前项目上下文"""
        self._update_project_context()
        if hasattr(self.assistant, 'project_context'):
            return self.assistant.project_context
        return ProjectContext()


class GamificationIntegration:
    """GamificationManager游戏化系统集成"""

    def __init__(self, assistant, gamification_manager=None, data_dir: str = None):
        self.assistant = assistant
        self._manager = gamification_manager
        self._data_dir = data_dir
        self._initialized = False

        # 如果没有传入manager但有data_dir，尝试创建
        if not self._manager and self._data_dir and HAS_GAMIFICATION:
            try:
                self._manager = GamificationManager(self._data_dir)
                self._initialized = True
            except Exception:
                pass
        elif self._manager:
            self._initialized = True

    @property
    def is_available(self) -> bool:
        return self._initialized and self._manager is not None

    def set_manager(self, manager):
        """设置游戏化管理器"""
        self._manager = manager
        if manager:
            self._initialized = True
            self.setup_listener()

    def setup_listener(self):
        """设置游戏化事件监听"""
        if not self._manager:
            return

        self._manager.add_listener(self._on_gamification_event)

    def _on_gamification_event(self, event_type: str, data: dict):
        """处理游戏化事件"""
        if event_type == "levelup":
            self._on_level_up(data)
        elif event_type == "achievement":
            self._on_achievement(data)
        elif event_type == "gain":
            self._on_xp_gain(data)

    def _on_level_up(self, data: dict):
        """等级提升事件"""
        level = data.get("level", 1)
        msg = data.get("msg", f"升级到 Lv.{level}！")

        # 显示庆祝
        self._show_celebration(f"{get_icon('sparkle', '🎉')} {msg}")


        # 更新助手状态
        self._update_assistant_level(level)

        # 特殊立绘
        if hasattr(self.assistant, '_set_state'):
            from .states import AssistantState
            self.assistant.after(0, lambda: self.assistant._set_state(AssistantState.HAPPY, duration=3000))

    def _on_achievement(self, data: dict):
        """成就解锁事件"""
        msg = data.get("msg", "成就解锁！")
        self._show_celebration(msg)

        # 同步到助手成就系统
        if hasattr(self.assistant, 'pet_system'):
            # 获取成就信息
            achievement_id = msg.split(":")[-1].strip() if ":" in msg else ""
            if achievement_id and hasattr(self.assistant, '_unlock_achievement'):
                # 映射到助手成就
                pass

    def _on_xp_gain(self, data: dict):
        """XP获取事件"""
        # 静默更新，不打扰用户
        if hasattr(self.assistant, 'pet_system'):
            xp = data.get("xp", 0)
            if xp > 0:
                self.assistant.pet_system.add_xp(xp // 10)  # 转换比例

    def _show_celebration(self, message: str):
        """显示庆祝消息"""
        if hasattr(self.assistant, '_append_message'):
            try:
                self.assistant.after(0, lambda: self.assistant._append_message("system", message))
            except Exception:
                pass

    def _update_assistant_level(self, level: int):
        """更新助手显示的等级"""
        if hasattr(self.assistant, 'level_label'):
            try:
                self.assistant.after(0, lambda: self.assistant.level_label.configure(text=f"Lv.{level}"))
            except Exception:
                pass

    def get_stats(self) -> dict:
        """获取统计数据"""
        if self._manager:
            return self._manager.get_stats()
        return {}

    def get_achievements_status(self) -> List[dict]:
        """获取成就状态"""
        if self._manager:
            return self._manager.get_achievements_status()
        return []

    def get_current_title(self) -> str:
        """获取当前称号"""
        if self._manager:
            return self._manager.get_current_title()
        return "文字爱好者"

    def record_words(self, count: int):
        """记录写作字数"""
        if self._manager and count > 0:
            self._manager.record_words(count)

    def record_pomodoro(self):
        """记录番茄钟完成"""
        if self._manager:
            self._manager.record_pomodoro()


class CommandExecutor:
    """Command执行器 - 支持Undo/Redo"""

    def __init__(self, project_manager=None, command_executor: Callable = None):
        self.project_manager = project_manager
        self._executor = command_executor  # main_app._execute_command

    def set_executor(self, executor: Callable):
        """设置命令执行器"""
        self._executor = executor

    def execute(self, command) -> bool:
        """执行命令"""
        if self._executor:
            try:
                return self._executor(command)
            except Exception as e:
                print(f"命令执行错误: {e}")
                return False
        elif hasattr(command, 'execute'):
            # 直接执行（无Undo支持）
            return command.execute()
        return False

    # ============================================================
    # 便捷命令方法
    # ============================================================

    def add_character(self, name: str, description: str = "", tags: List[str] = None) -> bool:
        """添加角色"""
        if not self.project_manager or not HAS_COMMANDS:
            return False

        char_data = {
            "name": name,
            "description": description,
            "tags": tags or [],
            "appearance": "",
            "personality": "",
            "background": "",
        }
        cmd = AddCharacterCommand(self.project_manager, char_data, f"添加角色: {name}")
        return self.execute(cmd)

    def add_scene(self, name: str, content: str = "", location: str = "",
                  time: str = "", characters: List[str] = None) -> bool:
        """添加场景"""
        if not self.project_manager or not HAS_COMMANDS:
            return False

        scene_data = {
            "name": name,
            "content": content,
            "location": location,
            "time": time,
            "characters": characters or [],
            "tags": [],
        }
        cmd = AddSceneCommand(self.project_manager, scene_data, f"添加场景: {name}")
        return self.execute(cmd)

    def add_outline_node(self, parent_uid: str, name: str, content: str = "") -> bool:
        """添加大纲节点"""
        if not self.project_manager or not HAS_COMMANDS:
            return False

        node_data = {
            "name": name,
            "content": content,
            "children": [],
        }
        cmd = AddNodeCommand(self.project_manager, parent_uid, node_data, f"添加节点: {name}")
        return self.execute(cmd)

    def add_wiki_entry(self, name: str, category: str, content: str = "") -> bool:
        """添加百科词条"""
        if not self.project_manager or not HAS_COMMANDS:
            return False

        entry_data = {
            "name": name,
            "category": category,
            "content": content,
        }
        cmd = AddWikiEntryCommand(self.project_manager, entry_data, f"添加词条: {name}")
        return self.execute(cmd)

    def add_idea(self, content: str, tags: List[str] = None) -> bool:
        """添加灵感"""
        if not self.project_manager:
            return False

        try:
            ideas = self.project_manager.project_data.setdefault("ideas", [])
            idea = {
                "id": str(datetime.now().timestamp()),
                "content": content,
                "tags": tags or [],
                "created_at": datetime.now().isoformat(),
            }
            ideas.append(idea)
            self.project_manager.mark_modified()

            # 发布事件
            if HAS_EVENT_BUS:
                get_event_bus().publish(Events.IDEA_ADDED, idea=idea)

            return True
        except Exception:
            return False

    def add_research(self, title: str, content: str, url: str = "") -> bool:
        """添加研究资料"""
        if not self.project_manager:
            return False

        try:
            research = self.project_manager.project_data.setdefault("research", [])
            entry = {
                "id": str(datetime.now().timestamp()),
                "title": title,
                "content": content,
                "url": url,
                "created_at": datetime.now().isoformat(),
            }
            research.append(entry)
            self.project_manager.mark_modified()

            # 发布事件
            if HAS_EVENT_BUS:
                get_event_bus().publish(Events.RESEARCH_ADDED, research=entry)

            return True
        except Exception:
            return False


class AIControllerBridge:
    """AIController桥接 - 联动AI工具调用"""

    def __init__(self, assistant, ai_controller=None):
        self.assistant = assistant
        self._controller = ai_controller

    def set_controller(self, controller):
        """设置AI控制器"""
        self._controller = controller

    @property
    def is_available(self) -> bool:
        return self._controller is not None

    def handle_tool_response(self, response_text: str, callback: Callable):
        """处理AI响应中的工具调用"""
        if not self._controller:
            callback(response_text)
            return

        try:
            self._controller.handle_chat_response(response_text, callback)
        except Exception as e:
            callback(response_text + f"\n\n[系统] 工具执行错误: {str(e)}")

    def get_project_summary(self) -> str:
        """获取项目摘要（用于AI上下文）"""
        if self._controller and hasattr(self._controller, '_get_project_stats_summary'):
            return self._controller._get_project_stats_summary()
        return ""


class StatsIntegration:
    """统计数据集成"""

    def __init__(self, stats_manager=None, gamification_manager=None):
        self._stats = stats_manager
        self._gamification = gamification_manager

    @property
    def is_available(self) -> bool:
        return self._stats is not None or self._gamification is not None

    def set_manager(self, manager):
        """设置统计管理器"""
        self._stats = manager

    def set_gamification(self, manager):
        """设置游戏化管理器"""
        self._gamification = manager

    def get_radar_data(self) -> Dict[str, float]:
        """获取五维雷达图数据"""
        if self._stats and hasattr(self._stats, 'get_radar_data'):
            return self._stats.get_radar_data()
        return {
            "创意": 0.5,
            "结构": 0.5,
            "词汇": 0.5,
            "风格": 0.5,
            "专注": 0.5,
        }

    def get_heatmap_data(self) -> Dict[str, int]:
        """获取热力图数据（每日字数）"""
        if self._gamification:
            stats = self._gamification.get_stats()
            return stats.get("daily_activity", {})
        return {}

    def get_streak(self) -> int:
        """获取连续创作天数"""
        heatmap = self.get_heatmap_data()
        if not heatmap:
            return 0

        # 计算连续天数
        today = date.today()
        streak = 0
        check_date = today

        while True:
            date_str = check_date.isoformat()
            if date_str in heatmap and heatmap[date_str] > 0:
                streak += 1
                check_date = date(check_date.year, check_date.month, check_date.day - 1)
                if check_date.day < 1:
                    break
            else:
                break

        return streak

    def get_today_words(self) -> int:
        """获取今日字数"""
        heatmap = self.get_heatmap_data()
        today_str = date.today().isoformat()
        return heatmap.get(today_str, 0)

    def get_total_words(self) -> int:
        """获取总字数"""
        if self._gamification:
            stats = self._gamification.get_stats()
            return stats.get("total_words_tracked", 0)
        return 0


class AssistantIntegrationManager:
    """
    悬浮助手集成管理器 - 统一管理所有集成

    使用方法:
        integration = AssistantIntegrationManager(
            assistant=floating_assistant,
            project_manager=pm,
            gamification_manager=gm,
            command_executor=app._execute_command,
            ai_controller=ai_ctrl
        )
        integration.initialize()
    """

    def __init__(self,
                 assistant,
                 project_manager=None,
                 gamification_manager=None,
                 command_executor: Callable = None,
                 ai_controller=None,
                 stats_manager=None,
                 data_dir: str = None):

        self.assistant = assistant

        # 创建各个集成组件
        self.event_bus = EventBusIntegration(assistant, project_manager)
        self.gamification = GamificationIntegration(assistant, gamification_manager, data_dir)
        self.commands = CommandExecutor(project_manager, command_executor)
        self.ai_bridge = AIControllerBridge(assistant, ai_controller)
        self.stats = StatsIntegration(stats_manager, gamification_manager)

        # 项目上下文
        self.project_context = ProjectContext()
        
        # 分析缓存
        self._last_analysis_time = 0
        self._cached_analysis = {}

        self._initialized = False

    def initialize(self):
        """初始化所有集成"""
        if self._initialized:
            return

        # 订阅EventBus事件
        self.event_bus.subscribe_all()

        # 设置游戏化监听
        self.gamification.setup_listener()

        # 存储到助手实例
        self.assistant.integration = self

        self._initialized = True

    def cleanup(self):
        """清理资源"""
        self.event_bus.unsubscribe_all()
        self._initialized = False

    def start(self):
        """启动集成（initialize的别名）"""
        self.initialize()

    def stop(self):
        """停止集成（cleanup的别名）"""
        self.cleanup()

    # ============================================================
    # 便捷方法 - 转发到具体集成组件
    # ============================================================

    def add_character(self, name: str, description: str = "") -> bool:
        """添加角色"""
        return self.commands.add_character(name, description)

    def add_scene(self, name: str, content: str = "") -> bool:
        """添加场景"""
        return self.commands.add_scene(name, content)

    def add_idea(self, content: str) -> bool:
        """添加灵感"""
        return self.commands.add_idea(content)

    def add_research(self, title: str, content: str) -> bool:
        """添加研究"""
        return self.commands.add_research(title, content)

    def get_stats_summary(self) -> dict:
        """获取统计摘要"""
        return {
            "today_words": self.stats.get_today_words(),
            "total_words": self.stats.get_total_words(),
            "streak": self.stats.get_streak(),
            "radar": self.stats.get_radar_data(),
            "level": self.gamification.get_stats().get("level", 1),
            "title": self.gamification.get_current_title(),
            "analysis_results": self.get_deep_analysis()
        }
        
    def get_deep_analysis(self) -> Dict[str, Any]:
        """获取深度项目分析报告 (带缓存)"""
        now = time.time()
        if now - self._last_analysis_time < 300:  # 5分钟缓存
            return self._cached_analysis
            
        report = {}
        if not self.event_bus.project_manager:
            return report
            
        try:
            script = self.event_bus.project_manager.get_script()
            scenes = script.get("scenes", [])
            characters = script.get("characters", [])
            
            if not scenes:
                return report
                
            # 1. 角色深度分析 (Protagonist Presence)
            # 检查主角是否存在感是否过低
            protagonists = [c["name"] for c in characters if c.get("role") == "主角"]
            if protagonists:
                prota_mentions = 0
                total_mentions = 0
                for s in scenes:
                    scene_chars = s.get("characters", [])
                    total_mentions += len(scene_chars)
                    for char in scene_chars:
                        if char in protagonists:
                            prota_mentions += 1
                
                # 如果总提及数足够，但主角占比低
                if total_mentions > 10 and (prota_mentions / total_mentions) < 0.15:
                    report["character_flat"] = True
            
            # 2. 节奏分析 (Pacing)
            lengths = [len(s.get("content", "")) for s in scenes]
            if len(lengths) >= 3:
                # 检查是否全是短场景
                short_scenes = sum(1 for l in lengths if l < 200)
                if short_scenes / len(lengths) > 0.6:
                    report["pacing_too_fast"] = True
                
                # 检查是否长时间未分段 (全是超长场景)
                long_scenes = sum(1 for l in lengths if l > 3000)
                if long_scenes / len(lengths) > 0.6:
                    report["pacing_too_slow"] = True
                    
        except Exception:
            pass
            
        self._cached_analysis = report
        self._last_analysis_time = now
        return report

    def record_writing(self, word_count: int):
        """记录写作"""
        self.gamification.record_words(word_count)

    def handle_ai_response(self, response: str, callback: Callable):
        """处理AI响应"""
        self.ai_bridge.handle_tool_response(response, callback)
