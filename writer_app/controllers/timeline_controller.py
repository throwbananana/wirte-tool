import tkinter as tk
from tkinter import ttk
from writer_app.controllers.base_controller import BaseController
from writer_app.ui.timeline import TimelinePanel
from writer_app.ui.help_dialog import create_module_help_button

from writer_app.core.analysis import AnalysisUtils
import tkinter.messagebox as messagebox
from writer_app.core.commands import AddTimelineEventCommand, MoveSceneCommand, EditSceneCommand
from writer_app.core.event_bus import get_event_bus, Events

class TimelineController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.setup_ui()
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅相关事件以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.SCENE_ADDED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_DELETED, self._on_data_changed)
        self._subscribe_event(Events.TIMELINE_EVENT_ADDED, self._on_data_changed)
        self._subscribe_event(Events.TIMELINE_EVENT_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.TIMELINE_EVENT_DELETED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_MOVED, self._on_data_changed)

    def _on_data_changed(self, event_type=None, **kwargs):
        """响应数据变化事件"""
        self.refresh()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="从剧本同步 (Sync)", command=self.sync_from_script).pack(side=tk.LEFT)

        # 帮助按钮
        help_btn = create_module_help_button(toolbar, "timeline", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        self.view = TimelinePanel(self.parent, self.project_manager, self.command_executor)
        self.view.pack(fill=tk.BOTH, expand=True)
        self.view.controller = self # Inject controller back to view for callbacks
        
        if hasattr(self.view, "canvas"):
            self._add_theme_listener(self.apply_theme)

    def sync_from_script(self):
        """Scan scenes and add events to timeline based on time field."""
        scenes = self.project_manager.get_scenes()
        added_count = 0
        
        # Get existing events to avoid duplicates (naive check)
        existing_timestamps = {e.get("timestamp") for e in self.project_manager.project_data.get("timelines", {}).get("truth_events", [])}
        
        for i, scene in enumerate(scenes):
            time_str = scene.get("time", "").strip()
            date_val = AnalysisUtils.parse_date(time_str)
            
            if date_val and date_val not in existing_timestamps:
                # Create event
                event_data = {
                    "name": scene.get("name", "未命名场景"),
                    "timestamp": date_val,
                    "motive": "",
                    "action": f"场景: {scene.get('location', '')}",
                    "chaos": 50,
                    "location": scene.get("location", ""),
                    "linked_scene_uid": scene.get("uid", "")
                }
                cmd = AddTimelineEventCommand(self.project_manager, "truth", event_data)
                self.command_executor(cmd)
                existing_timestamps.add(date_val)
                added_count += 1
        
        if added_count > 0:
            messagebox.showinfo("同步完成", f"已从剧本添加 {added_count} 个时间点。")
            self.refresh()
        else:
            messagebox.showinfo("同步完成", "没有发现新的有效时间点 (格式: YYYY-MM-DD)。")

    def move_scene(self, from_idx, to_idx):
        """Move scene sequence."""
        cmd = MoveSceneCommand(self.project_manager, from_idx, to_idx)
        self.command_executor(cmd)

    def update_scene_date(self, idx, new_date_str):
        """Update scene date field."""
        scenes = self.project_manager.get_scenes()
        if 0 <= idx < len(scenes):
            old_data = scenes[idx]
            new_data = old_data.copy()
            new_data["time"] = new_date_str
            
            cmd = EditSceneCommand(self.project_manager, idx, old_data, new_data, description="在时间轴调整时间")
            self.command_executor(cmd)

    def apply_theme(self):
        bg = self.theme_manager.get_color("canvas_bg")
        self.view.canvas.configure(bg=bg)

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "timeline")

    def refresh(self):
        if self.view:
            self.view.refresh()
