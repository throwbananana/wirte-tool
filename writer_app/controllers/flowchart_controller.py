import tkinter as tk
from tkinter import ttk
from writer_app.controllers.base_controller import BaseController
from writer_app.core.commands import EditSceneCommand
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.ui.flowchart_view import StoryFlowCanvas
from writer_app.ui.help_dialog import create_module_help_button

class FlowchartController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager, on_jump_to_scene=None):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.on_jump_to_scene = on_jump_to_scene

        self.setup_ui()
        self._add_theme_listener(self.apply_theme)
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅事件总线以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.SCENE_ADDED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_DELETED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_MOVED, self._on_data_changed)
        self._subscribe_event(Events.OUTLINE_CHANGED, self._on_data_changed)
        self._subscribe_event(Events.PROJECT_LOADED, self._on_data_changed)

    def _on_data_changed(self, event_type=None, **kwargs):
        """响应数据变化事件"""
        self.refresh()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Label(toolbar, text="右键拖拽节点可创建分支").pack(side=tk.LEFT, padx=5)

        # 帮助按钮
        help_btn = create_module_help_button(toolbar, "flowchart", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        self.view = StoryFlowCanvas(
            self.parent,
            self.project_manager,
            on_jump_to_scene=self.on_jump_to_scene,
            on_add_connection=self.add_connection
        )
        self.view.pack(fill=tk.BOTH, expand=True)

    def add_connection(self, src_name, tgt_name):
        scenes = self.project_manager.get_scenes()
        src_index = next((i for i, s in enumerate(scenes) if s.get("name") == src_name), None)
        if src_index is None:
            return

        src_scene = scenes[src_index]
        choices = list(src_scene.get("choices", []))
        if any(c.get("target_scene") == tgt_name for c in choices):
            return

        choices.append({
            "text": f"前往 {tgt_name}",
            "target_scene": tgt_name
        })
        new_scene = dict(src_scene)
        new_scene["choices"] = choices

        cmd = EditSceneCommand(
            self.project_manager,
            src_index,
            src_scene,
            new_scene,
            f"添加分支: {src_name} -> {tgt_name}"
        )
        if self.command_executor:
            self.command_executor(cmd)
        else:
            scenes[src_index] = new_scene
            self.project_manager.mark_modified()
            self.refresh()

    def refresh(self):
        if hasattr(self.view, "refresh"):
            self.view.refresh()

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "flowchart")

    def apply_theme(self):
        """
        应用当前主题到流程图视图。
        """
        if not self.theme_manager:
            return

        try:
            # 获取主题颜色
            canvas_bg = self.theme_manager.get_color("canvas_bg")
            fg_primary = self.theme_manager.get_color("fg_primary")
            fg_secondary = self.theme_manager.get_color("fg_secondary")

            # 应用到视图
            if hasattr(self.view, 'configure'):
                self.view.configure(bg=canvas_bg)

            # 如果视图有自己的主题方法，调用它
            if hasattr(self.view, 'apply_theme'):
                self.view.apply_theme(self.theme_manager)

            # 刷新视图
            self.refresh()

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"应用流程图主题时出错: {e}")
