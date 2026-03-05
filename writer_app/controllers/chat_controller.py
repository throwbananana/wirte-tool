import tkinter as tk
from tkinter import ttk
from writer_app.controllers.base_controller import BaseController
from writer_app.ui.chat_panel import ChatPanel
from writer_app.core.event_bus import get_event_bus, Events
import json

class ChatController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager, ai_client, config_manager, ai_controller):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.ai_client = ai_client
        self.config_manager = config_manager
        self.ai_controller = ai_controller

        self.setup_ui()
        self._add_theme_listener(self.apply_theme)
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅事件总线以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.PROJECT_LOADED, self._on_project_loaded)
        self._subscribe_event(Events.CHARACTER_ADDED, self._on_data_changed)
        self._subscribe_event(Events.CHARACTER_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.CHARACTER_DELETED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_ADDED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_DELETED, self._on_data_changed)

    def _on_project_loaded(self, event_type=None, **kwargs):
        """响应项目加载事件"""
        self.refresh()

    def _on_data_changed(self, event_type=None, **kwargs):
        """响应数据变化事件 - 刷新角色列表"""
        self.refresh()

    def setup_ui(self):
        self.view = ChatPanel(
            self.parent,
            ai_client=self.ai_client,
            context_provider=self._get_full_project_context,
            config_provider=self._get_ai_config,
            project_manager=self.project_manager,
            ai_controller=self.ai_controller,
            ai_mode_provider=self._get_ai_mode
        )
        self.view.pack(fill=tk.BOTH, expand=True)

    def _get_full_project_context(self):
        lines = []
        lines.append("【项目大纲】")
        self._export_node(self.project_manager.get_outline(), 0, lines)
        lines.append("")
        
        # Factions (Sci-Fi)
        factions = self.project_manager.get_factions()
        if factions:
            lines.append("【势力外交】")
            matrix = self.project_manager.get_faction_matrix()
            for f in factions:
                lines.append(f"- {f['name']}: {f.get('desc','')}")
                rels = []
                f_mat = matrix.get(f['uid'], {})
                for other_uid, val in f_mat.items():
                    other_name = next((of['name'] for of in factions if of['uid'] == other_uid), "未知")
                    rels.append(f"{other_name}({val})")
                if rels: lines.append(f"  关系: {', '.join(rels)}")
            lines.append("")

        lines.append("【剧本内容】")
        lines.append(self._collect_script_text())
        lines.append("")
        lines.append("【世界观百科 (Iceberg)】")
        for entry in self.project_manager.get_world_entries():
            depth = entry.get("iceberg_depth", "surface").upper()
            lines.append(f"- [{depth}] [{entry.get('category')}] {entry.get('name')}: {entry.get('content')}")
        return "\n".join(lines)

    def _export_node(self, node, level, lines):
        if not node: return
        indent = "  " * level
        lines.append(f"{indent}- {node.get('name', 'Untitled')}")
        content = node.get("content", "").strip()
        if content:
            lines.append(f"{indent}  内容: {content[:100]}...")
        for child in node.get("children", []):
            self._export_node(child, level + 1, lines)

    def _collect_script_text(self):
        lines = []
        for scene in self.project_manager.get_scenes():
            lines.append(f"场景: {scene.get('name', '')}")
            lines.append(scene.get('content', '')[:200] + "...")
        return "\n".join(lines)

    def _get_ai_config(self):
        # We need to get these from somewhere. 
        # In main.py they were in StringVars.
        # Here we can read from config_manager or let the view hold its own vars if needed.
        # But config_manager is standard.
        url = self.config_manager.get("lm_api_url", "http://localhost:1234/v1/chat/completions")
        model = self.config_manager.get("lm_api_model", "local-model")
        key = self.config_manager.get("lm_api_key", "")
        return (url, model, key)

    def _get_ai_mode(self):
        return self.config_manager.get("ai_mode_enabled", True)

    def apply_theme(self):
        theme = self.theme_manager
        if hasattr(self.view, "history_text"):
            self.view.history_text.configure(bg=theme.get_color("editor_bg"), fg=theme.get_color("editor_fg"))
        if hasattr(self.view, "input_text"):
            self.view.input_text.configure(bg=theme.get_color("editor_bg"), fg=theme.get_color("editor_fg"))

    def refresh(self):
        if hasattr(self.view, "refresh_char_list"):
            self.view.refresh_char_list()

    def set_ai_mode_enabled(self, enabled: bool):
        if hasattr(self.view, "set_ai_mode_enabled"):
            self.view.set_ai_mode_enabled(enabled)
