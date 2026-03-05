"""
双时间轴控制器 - 管理真相线/谎言线的业务逻辑

功能：
- 继承 BaseController 统一错误处理
- 通过 Command 模式进行数据操作（支持撤销/重做）
- 订阅事件总线自动刷新
- 与场景同步
"""
import tkinter as tk
from tkinter import ttk, messagebox
import uuid
import json

from writer_app.controllers.base_controller import BaseController
from writer_app.ui.dual_timeline import DualTimelineView
from writer_app.ui.dialogs_suspense import TruthEventDialog, LieEventDialog
from writer_app.ui.help_dialog import create_module_help_button
from writer_app.core.commands import (
    AddTimelineEventCommand,
    EditTimelineEventCommand,
    DeleteTimelineEventCommand,
    EditSceneCommand
)
from writer_app.core.event_bus import get_event_bus, Events


class DualTimelineController(BaseController):
    """双时间轴控制器"""

    def __init__(self, parent, project_manager, command_executor, theme_manager):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.setup_ui()
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅事件总线以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.TIMELINE_EVENT_ADDED, self._on_data_changed)
        self._subscribe_event(Events.TIMELINE_EVENT_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.TIMELINE_EVENT_DELETED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_ADDED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_UPDATED, self._on_data_changed)
        self._subscribe_event(Events.SCENE_DELETED, self._on_data_changed)
        self._subscribe_event(Events.PROJECT_LOADED, self._on_data_changed)

    def _on_data_changed(self, event_type=None, **kwargs):
        """响应数据变化事件"""
        self.refresh()

    def setup_ui(self):
        """设置 UI 组件"""
        # Toolbar
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="添加真相事件", command=self.add_truth_event).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="添加谎言事件", command=self.add_lie_event).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(toolbar, text="重置视图", command=self._reset_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="从剧本同步", command=self._sync_from_script).pack(side=tk.LEFT, padx=2)

        # Help text
        ttk.Label(toolbar, text="[操作: 滚轮缩放 | 中键/Ctrl+拖拽平移 | 双击编辑 | 右键菜单]",
                  foreground="gray").pack(side=tk.RIGHT, padx=5)

        # 帮助按钮
        help_btn = create_module_help_button(toolbar, "dual_timeline", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        # View
        self.view = DualTimelineView(
            self.parent,
            self.project_manager,
            self.theme_manager,
            controller=self
        )
        self.view.pack(fill=tk.BOTH, expand=True)

        # Register theme listener (使用追踪方法以便清理)
        self._add_theme_listener(self.apply_theme)

    def pack(self, **kwargs):
        """Pack the view (for compatibility)"""
        self.view.pack(**kwargs)

    def apply_theme(self):
        """应用主题"""
        self.view.refresh()

    def refresh(self):
        """刷新视图"""
        if self.view:
            self.view.refresh()

    def _reset_view(self):
        """重置视图"""
        if self.view:
            self.view.reset_view()

    def _sync_from_script(self):
        """从剧本场景同步事件到时间轴"""
        try:
            from writer_app.core.analysis import AnalysisUtils

            scenes = self.project_manager.get_scenes()
            existing_uids = set()

            # Get existing linked scene UIDs
            timelines = self.project_manager.project_data.get("timelines", {})
            for event in timelines.get("truth_events", []):
                if event.get("linked_scene_uid"):
                    existing_uids.add(event.get("linked_scene_uid"))

            added_count = 0
            for scene in scenes:
                scene_uid = scene.get("uid")
                if not scene_uid or scene_uid in existing_uids:
                    continue

                time_str = scene.get("time", "").strip()
                date_val = AnalysisUtils.parse_date(time_str)

                if date_val:
                    event_data = {
                        "name": scene.get("name", "未命名场景"),
                        "timestamp": date_val,
                        "motive": "",
                        "action": f"场景: {scene.get('location', '')}",
                        "chaos": 50,
                        "location": scene.get("location", ""),
                        "linked_scene_uid": scene_uid
                    }

                    cmd = AddTimelineEventCommand(
                        self.project_manager,
                        "truth",
                        event_data,
                        "从剧本同步事件"
                    )
                    self.command_executor(cmd)
                    added_count += 1

            if added_count > 0:
                messagebox.showinfo("同步完成", f"已从剧本添加 {added_count} 个时间点。")
            else:
                messagebox.showinfo("同步完成", "没有发现新的有效时间点 (格式: YYYY-MM-DD)。")

            self.refresh()
        except Exception as e:
            self.handle_error(e, "同步事件时出错")

    # --- Truth Event Operations ---

    def add_truth_event(self):
        """添加真相事件"""
        try:
            dlg = TruthEventDialog(self.view.winfo_toplevel())
            self.view.wait_window(dlg)

            if dlg.result:
                # Ensure UID
                if "uid" not in dlg.result or not dlg.result["uid"]:
                    dlg.result["uid"] = uuid.uuid4().hex

                cmd = AddTimelineEventCommand(
                    self.project_manager,
                    "truth",
                    dlg.result,
                    "添加真相事件"
                )
                self.command_executor(cmd)
                self.refresh()
        except Exception as e:
            self.handle_error(e, "添加真相事件时出错")

    def edit_truth_event(self, event_data):
        """编辑真相事件"""
        try:
            event_uid = event_data.get("uid")
            if not event_uid:
                messagebox.showerror("错误", "事件缺少 UID，无法编辑")
                return

            # Get fresh data from model
            events = self.project_manager.project_data.get("timelines", {}).get("truth_events", [])
            current_data = None
            for evt in events:
                if evt.get("uid") == event_uid:
                    current_data = evt
                    break

            if not current_data:
                messagebox.showerror("错误", "找不到该事件")
                return

            # Open dialog with current data
            dlg = TruthEventDialog(self.view.winfo_toplevel(), current_data)
            self.view.wait_window(dlg)

            if dlg.result:
                cmd = EditTimelineEventCommand(
                    self.project_manager,
                    "truth",
                    event_uid,
                    current_data,
                    dlg.result,
                    "编辑真相事件"
                )
                self.command_executor(cmd)

                # Sync to linked scene if exists
                self._sync_event_to_scene(dlg.result)
                self.refresh()
        except Exception as e:
            self.handle_error(e, "编辑真相事件时出错")

    def delete_truth_event(self, event_data):
        """删除真相事件"""
        try:
            if messagebox.askyesno("确认删除", "确定删除此真相事件？"):
                event_uid = event_data.get("uid")
                if not event_uid:
                    return

                cmd = DeleteTimelineEventCommand(
                    self.project_manager,
                    "truth",
                    event_uid,
                    "删除真相事件"
                )
                self.command_executor(cmd)
                self.refresh()
        except Exception as e:
            self.handle_error(e, "删除真相事件时出错")

    # --- Lie Event Operations ---

    def add_lie_event(self):
        """添加谎言事件"""
        try:
            dlg = LieEventDialog(self.view.winfo_toplevel())
            self.view.wait_window(dlg)

            if dlg.result:
                if "uid" not in dlg.result or not dlg.result["uid"]:
                    dlg.result["uid"] = uuid.uuid4().hex

                cmd = AddTimelineEventCommand(
                    self.project_manager,
                    "lie",
                    dlg.result,
                    "添加谎言事件"
                )
                self.command_executor(cmd)
                self.refresh()
        except Exception as e:
            self.handle_error(e, "添加谎言事件时出错")

    def edit_lie_event(self, event_data):
        """编辑谎言事件"""
        try:
            event_uid = event_data.get("uid")
            if not event_uid:
                messagebox.showerror("错误", "事件缺少 UID，无法编辑")
                return

            events = self.project_manager.project_data.get("timelines", {}).get("lie_events", [])
            current_data = None
            for evt in events:
                if evt.get("uid") == event_uid:
                    current_data = evt
                    break

            if not current_data:
                messagebox.showerror("错误", "找不到该事件")
                return

            dlg = LieEventDialog(self.view.winfo_toplevel(), current_data)
            self.view.wait_window(dlg)

            if dlg.result:
                cmd = EditTimelineEventCommand(
                    self.project_manager,
                    "lie",
                    event_uid,
                    current_data,
                    dlg.result,
                    "编辑谎言事件"
                )
                self.command_executor(cmd)
                self.refresh()
        except Exception as e:
            self.handle_error(e, "编辑谎言事件时出错")

    def delete_lie_event(self, event_data):
        """删除谎言事件"""
        try:
            if messagebox.askyesno("确认删除", "确定删除此谎言事件？"):
                event_uid = event_data.get("uid")
                if not event_uid:
                    return

                cmd = DeleteTimelineEventCommand(
                    self.project_manager,
                    "lie",
                    event_uid,
                    "删除谎言事件"
                )
                self.command_executor(cmd)
                self.refresh()
        except Exception as e:
            self.handle_error(e, "删除谎言事件时出错")

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "dual_timeline")

    def _sync_event_to_scene(self, event_data):
        """将时间轴事件同步到关联的场景"""
        try:
            scene_uid = event_data.get("linked_scene_uid")
            if not scene_uid:
                return

            scenes = self.project_manager.get_scenes()
            for idx, scene in enumerate(scenes):
                if scene.get("uid") == scene_uid:
                    old_scene_data = json.loads(json.dumps(scene))
                    new_scene_data = json.loads(json.dumps(scene))

                    # Sync basic fields
                    new_scene_data["name"] = event_data.get("name", scene.get("name"))
                    new_scene_data["location"] = event_data.get("location", scene.get("location"))
                    new_scene_data["time"] = event_data.get("timestamp", scene.get("time"))

                    if old_scene_data != new_scene_data:
                        cmd = EditSceneCommand(
                            self.project_manager,
                            idx,
                            old_scene_data,
                            new_scene_data,
                            "从时间轴同步场景"
                        )
                        self.command_executor(cmd)
                    break
        except Exception as e:
            self.handle_error(e, "同步场景时出错")
