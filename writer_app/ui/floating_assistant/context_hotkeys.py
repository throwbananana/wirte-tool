"""
上下文感知和快捷键支持模块 (Context Awareness and Hotkey Support)

提供：
- 编辑器文本获取（选中文本、当前段落）
- 全局快捷键支持
- 剪贴板监听
"""

import tkinter as tk
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time


@dataclass
class EditorContext:
    """编辑器上下文数据"""
    selected_text: str = ""
    current_paragraph: str = ""
    cursor_position: tuple = (0, 0)  # (line, column)
    total_chars: int = 0
    current_scene: Optional[str] = None
    current_character: Optional[str] = None

    def has_selection(self) -> bool:
        return bool(self.selected_text.strip())

    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        parts = []
        if self.selected_text:
            preview = self.selected_text[:50] + "..." if len(self.selected_text) > 50 else self.selected_text
            parts.append(f"选中: {preview}")
        if self.current_scene:
            parts.append(f"场景: {self.current_scene}")
        if self.current_character:
            parts.append(f"角色: {self.current_character}")
        return " | ".join(parts) if parts else "无上下文"


class ContextProvider:
    """上下文提供器 - 从编辑器获取上下文信息"""

    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self._editor_widget: Optional[tk.Text] = None
        self._script_controller = None

    def set_editor_widget(self, widget: tk.Text):
        """设置编辑器控件引用"""
        self._editor_widget = widget

    def set_script_controller(self, controller):
        """设置脚本控制器引用"""
        self._script_controller = controller

    def get_context(self) -> EditorContext:
        """获取当前编辑器上下文"""
        ctx = EditorContext()

        if self._editor_widget:
            try:
                # 获取选中文本
                try:
                    ctx.selected_text = self._editor_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    ctx.selected_text = ""

                # 获取光标位置
                cursor = self._editor_widget.index(tk.INSERT)
                if cursor:
                    parts = cursor.split(".")
                    if len(parts) == 2:
                        ctx.cursor_position = (int(parts[0]), int(parts[1]))

                # 获取当前段落
                ctx.current_paragraph = self._get_current_paragraph()

                # 获取总字数
                all_text = self._editor_widget.get("1.0", tk.END)
                ctx.total_chars = len(all_text.strip())

            except Exception:
                pass

        # 从项目管理器获取场景/角色信息
        if self.project_manager and self._script_controller:
            try:
                # 获取当前场景
                if hasattr(self._script_controller, 'current_scene_index'):
                    idx = self._script_controller.current_scene_index
                    scenes = self.project_manager.get_scenes()
                    if 0 <= idx < len(scenes):
                        ctx.current_scene = scenes[idx].get("name", "")

                        # 获取场景中的角色
                        chars = scenes[idx].get("characters", [])
                        if chars:
                            ctx.current_character = ", ".join(chars[:3])
            except Exception:
                pass

        return ctx

    def _get_current_paragraph(self) -> str:
        """获取光标所在的当前段落"""
        if not self._editor_widget:
            return ""

        try:
            # 获取当前行
            cursor = self._editor_widget.index(tk.INSERT)
            line_num = int(cursor.split(".")[0])

            # 向上查找段落开始
            start_line = line_num
            while start_line > 1:
                prev_line = self._editor_widget.get(f"{start_line-1}.0", f"{start_line-1}.end")
                if not prev_line.strip():
                    break
                start_line -= 1

            # 向下查找段落结束
            end_line = line_num
            total_lines = int(self._editor_widget.index(tk.END).split(".")[0])
            while end_line < total_lines:
                next_line = self._editor_widget.get(f"{end_line+1}.0", f"{end_line+1}.end")
                if not next_line.strip():
                    break
                end_line += 1

            # 获取段落文本
            paragraph = self._editor_widget.get(f"{start_line}.0", f"{end_line}.end")
            return paragraph.strip()

        except Exception:
            return ""

    def get_selected_or_paragraph(self) -> str:
        """获取选中文本，如果没有选中则返回当前段落"""
        ctx = self.get_context()
        if ctx.has_selection():
            return ctx.selected_text
        return ctx.current_paragraph

    def get_surrounding_context(self, lines_before: int = 3, lines_after: int = 3) -> str:
        """获取光标周围的上下文"""
        if not self._editor_widget:
            return ""

        try:
            cursor = self._editor_widget.index(tk.INSERT)
            line_num = int(cursor.split(".")[0])
            total_lines = int(self._editor_widget.index(tk.END).split(".")[0])

            start_line = max(1, line_num - lines_before)
            end_line = min(total_lines, line_num + lines_after)

            return self._editor_widget.get(f"{start_line}.0", f"{end_line}.end")
        except Exception:
            return ""


@dataclass
class HotkeyBinding:
    """快捷键绑定"""
    key_combination: str  # e.g., "Control-Shift-a"
    callback: Callable
    description: str
    enabled: bool = True


class HotkeyManager:
    """快捷键管理器"""

    # 预定义快捷键配置
    DEFAULT_HOTKEYS = {
        "toggle_assistant": {
            "key": "Control-grave",  # Ctrl + `
            "description": "显示/隐藏写作助手",
        },
        "quick_prompt": {
            "key": "Control-Shift-p",
            "description": "抽取写作提示卡",
        },
        "roll_dice": {
            "key": "Control-Shift-d",
            "description": "掷骰子",
        },
        "name_generator": {
            "key": "Control-Shift-n",
            "description": "打开起名生成器",
        },
        "word_count": {
            "key": "Control-Shift-w",
            "description": "显示字数统计",
        },
        "ai_expand": {
            "key": "Control-Shift-e",
            "description": "AI扩写选中内容",
        },
        "ai_polish": {
            "key": "Control-Shift-r",
            "description": "AI润色选中内容",
        },
        "send_to_assistant": {
            "key": "Control-Shift-Return",
            "description": "将选中文本发送到助手",
        },
        "timer_toggle": {
            "key": "Control-Shift-t",
            "description": "开始/停止计时器",
        },
        "quick_note": {
            "key": "Control-Shift-m",
            "description": "快速笔记",
        },
    }

    def __init__(self, root: tk.Tk, config_manager=None):
        self.root = root
        self.config_manager = config_manager
        self.bindings: Dict[str, HotkeyBinding] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._enabled = True

        # 加载用户配置
        self._load_config()

    def _load_config(self):
        """加载快捷键配置"""
        if self.config_manager:
            saved = self.config_manager.get("assistant_hotkeys", {})
            for action, config in self.DEFAULT_HOTKEYS.items():
                key = saved.get(action, config["key"])
                self.bindings[action] = HotkeyBinding(
                    key_combination=key,
                    callback=lambda: None,  # 稍后设置
                    description=config["description"],
                    enabled=True
                )
        else:
            for action, config in self.DEFAULT_HOTKEYS.items():
                self.bindings[action] = HotkeyBinding(
                    key_combination=config["key"],
                    callback=lambda: None,
                    description=config["description"],
                    enabled=True
                )

    def register_callback(self, action: str, callback: Callable):
        """注册快捷键回调"""
        self._callbacks[action] = callback
        if action in self.bindings:
            self.bindings[action].callback = callback

    def bind_all(self):
        """绑定所有快捷键到根窗口"""
        for action, binding in self.bindings.items():
            if binding.enabled and action in self._callbacks:
                try:
                    key = f"<{binding.key_combination}>"
                    self.root.bind_all(key, lambda e, a=action: self._on_hotkey(a))
                except Exception:
                    pass

    def unbind_all(self):
        """解绑所有快捷键"""
        for action, binding in self.bindings.items():
            try:
                key = f"<{binding.key_combination}>"
                self.root.unbind_all(key)
            except Exception:
                pass

    def _on_hotkey(self, action: str):
        """处理快捷键事件"""
        if not self._enabled:
            return

        callback = self._callbacks.get(action)
        if callback:
            try:
                callback()
            except Exception:
                pass

    def set_enabled(self, enabled: bool):
        """启用/禁用快捷键"""
        self._enabled = enabled

    def update_binding(self, action: str, new_key: str):
        """更新快捷键绑定"""
        if action in self.bindings:
            old_binding = self.bindings[action]

            # 解绑旧键
            try:
                self.root.unbind_all(f"<{old_binding.key_combination}>")
            except Exception:
                pass

            # 更新并绑定新键
            old_binding.key_combination = new_key
            if action in self._callbacks:
                try:
                    self.root.bind_all(f"<{new_key}>", lambda e, a=action: self._on_hotkey(a))
                except Exception:
                    pass

            # 保存配置
            self._save_config()

    def _save_config(self):
        """保存快捷键配置"""
        if self.config_manager:
            config = {action: b.key_combination for action, b in self.bindings.items()}
            self.config_manager.set("assistant_hotkeys", config)
            self.config_manager.save()

    def get_hotkey_list(self) -> List[Dict[str, str]]:
        """获取快捷键列表（用于显示）"""
        result = []
        for action, binding in self.bindings.items():
            result.append({
                "action": action,
                "key": binding.key_combination,
                "description": binding.description,
                "enabled": binding.enabled,
            })
        return result


class ClipboardMonitor:
    """剪贴板监听器"""

    def __init__(self, root: tk.Tk, callback: Callable[[str], None] = None):
        self.root = root
        self.callback = callback
        self._last_content = ""
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 1.0  # 秒

    def start(self):
        """开始监听"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止监听"""
        self._running = False

    def _monitor_loop(self):
        """监听循环"""
        while self._running:
            try:
                current = self.root.clipboard_get()
                if current != self._last_content:
                    self._last_content = current
                    if self.callback:
                        # 在主线程中执行回调
                        self.root.after(0, lambda c=current: self.callback(c))
            except tk.TclError:
                pass  # 剪贴板为空或不可访问
            except Exception:
                pass

            time.sleep(self._check_interval)

    def get_current(self) -> str:
        """获取当前剪贴板内容"""
        try:
            return self.root.clipboard_get()
        except Exception:
            return ""

    def set_content(self, text: str):
        """设置剪贴板内容"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            pass

    @staticmethod
    def get_quick_actions(text: str) -> List[tuple]:
        """根据文本内容返回可用的快捷操作

        Returns:
            List of (label, action_type, prompt) tuples
        """
        if not text or len(text.strip()) < 10:
            return []

        actions = []
        text_len = len(text.strip())

        # 根据文本长度提供不同操作
        if text_len > 30:
            actions.append(("润色", "polish", "请润色以下内容，使其更加流畅优美："))
        if text_len > 50:
            actions.append(("缩写", "shorten", "请精简以下内容，保留核心要点："))
        if text_len > 150:
            actions.append(("总结", "summarize", "请总结以下内容的要点："))
        if text_len < 200:
            actions.append(("扩写", "expand", "请扩写以下内容，增加细节和描写："))
        if text_len > 20:
            actions.append(("续写", "continue", "请续写以下内容："))

        return actions


class ContextAwareAssistant:
    """上下文感知助手 - 整合上下文获取和快捷键"""

    def __init__(self, root: tk.Tk, project_manager=None, config_manager=None):
        self.root = root
        self.project_manager = project_manager
        self.config_manager = config_manager

        # 初始化组件
        self.context_provider = ContextProvider(project_manager)
        self.hotkey_manager = HotkeyManager(root, config_manager)
        self.clipboard_monitor = ClipboardMonitor(root)

        # 助手实例引用（稍后设置）
        self._assistant = None

        # 剪贴板监听状态
        self._clipboard_listening = False

    def set_assistant(self, assistant):
        """设置助手实例引用"""
        self._assistant = assistant
        self._setup_hotkey_callbacks()

    def set_editor_widget(self, widget: tk.Text):
        """设置编辑器控件"""
        self.context_provider.set_editor_widget(widget)

    def set_script_controller(self, controller):
        """设置脚本控制器"""
        self.context_provider.set_script_controller(controller)

    def _setup_hotkey_callbacks(self):
        """设置快捷键回调"""
        if not self._assistant:
            return

        callbacks = {
            "toggle_assistant": self._toggle_assistant,
            "quick_prompt": self._quick_prompt,
            "roll_dice": self._roll_dice,
            "name_generator": self._name_generator,
            "word_count": self._word_count,
            "ai_expand": self._ai_expand,
            "ai_polish": self._ai_polish,
            "send_to_assistant": self._send_to_assistant,
            "timer_toggle": self._timer_toggle,
            "quick_note": self._quick_note,
        }

        for action, callback in callbacks.items():
            self.hotkey_manager.register_callback(action, callback)

    def bind_hotkeys(self):
        """绑定快捷键"""
        self.hotkey_manager.bind_all()

    def start_clipboard_monitor(self, callback: Callable[[str], None] = None):
        """开始剪贴板监听"""
        self.clipboard_monitor.callback = callback or self._on_clipboard_change
        self.clipboard_monitor.start()
        self._clipboard_listening = True

    def stop_clipboard_monitor(self):
        """停止剪贴板监听"""
        self.clipboard_monitor.stop()
        self._clipboard_listening = False

    def _on_clipboard_change(self, content: str):
        """剪贴板内容变化回调"""
        if not self._assistant or not content:
            return

        # 检查是否启用了剪贴板监听提示
        if self.config_manager:
            if not self.config_manager.get("clipboard_notify_enabled", False):
                return

        # 获取可用的快捷操作
        actions = ClipboardMonitor.get_quick_actions(content)
        if not actions:
            return

        # 存储剪贴板内容供后续使用
        self._clipboard_content = content
        self._clipboard_actions = actions

        # 如果助手窗口存在，显示剪贴板提示
        if self._assistant.winfo_exists():
            text_preview = content[:50] + "..." if len(content) > 50 else content
            self._assistant._show_clipboard_notification(
                f"检测到 {len(content)} 字文本",
                text_preview,
                actions
            )

    # ============================================================
    # 快捷键回调实现
    # ============================================================

    def _toggle_assistant(self):
        """切换助手显示"""
        if self._assistant:
            if self._assistant.winfo_viewable():
                self._assistant.withdraw()
            else:
                self._assistant.deiconify()

    def _quick_prompt(self):
        """抽取提示卡"""
        if self._assistant and self._assistant.winfo_exists():
            self._assistant._draw_prompt_card()
            self._assistant.show()

    def _roll_dice(self):
        """掷骰子"""
        if self._assistant and self._assistant.winfo_exists():
            self._assistant._roll_dice()
            self._assistant.show()

    def _name_generator(self):
        """打开起名生成器"""
        if self._assistant and self._assistant.winfo_exists():
            self._assistant._open_name_generator()

    def _word_count(self):
        """显示字数统计"""
        if self._assistant and self._assistant.winfo_exists():
            self._assistant._show_word_count()
            self._assistant.show()

    def _ai_expand(self):
        """AI扩写选中内容"""
        if not self._assistant or not self._assistant.winfo_exists():
            return

        text = self.context_provider.get_selected_or_paragraph()
        if text:
            self._assistant.show()
            self._assistant.input_text.delete("1.0", tk.END)
            self._assistant.input_text.insert("1.0", f"请扩写以下内容，增加细节和描写：\n\n{text}")
            self._assistant._on_send()

    def _ai_polish(self):
        """AI润色选中内容"""
        if not self._assistant or not self._assistant.winfo_exists():
            return

        text = self.context_provider.get_selected_or_paragraph()
        if text:
            self._assistant.show()
            self._assistant.input_text.delete("1.0", tk.END)
            self._assistant.input_text.insert("1.0", f"请润色以下内容，使其更加流畅优美：\n\n{text}")
            self._assistant._on_send()

    def _send_to_assistant(self):
        """将选中文本发送到助手"""
        if not self._assistant or not self._assistant.winfo_exists():
            return

        text = self.context_provider.get_selected_or_paragraph()
        if text:
            self._assistant.show()
            self._assistant.input_text.delete("1.0", tk.END)
            self._assistant.input_text.insert("1.0", text)
            self._assistant.input_text.focus_set()

    def _timer_toggle(self):
        """切换计时器"""
        if self._assistant and self._assistant.winfo_exists():
            self._assistant._toggle_timer()

    def _quick_note(self):
        """快速笔记"""
        if self._assistant and self._assistant.winfo_exists():
            self._assistant._open_quick_note()

    def get_context(self) -> EditorContext:
        """获取当前上下文"""
        return self.context_provider.get_context()

    def get_context_for_ai(self) -> str:
        """获取用于AI的上下文字符串"""
        ctx = self.context_provider.get_context()
        parts = []

        if ctx.current_scene:
            parts.append(f"当前场景: {ctx.current_scene}")
        if ctx.current_character:
            parts.append(f"相关角色: {ctx.current_character}")
        if ctx.selected_text:
            parts.append(f"选中内容: {ctx.selected_text[:200]}...")
        elif ctx.current_paragraph:
            parts.append(f"当前段落: {ctx.current_paragraph[:200]}...")

        return "\n".join(parts) if parts else ""
