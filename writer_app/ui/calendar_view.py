import tkinter as tk
from tkinter import ttk
import calendar
from datetime import datetime
import re
import logging

from writer_app.core.event_bus import get_event_bus, Events
from writer_app.core.commands import EditSceneCommand

logger = logging.getLogger(__name__)


class CalendarView(ttk.Frame):
    """
    场景日历视图 - 按日期展示场景。

    Features:
    - 月历视图展示场景时间分布
    - 支持拖放场景到日期单元格
    - 与 EventBus 集成实现实时更新
    - 点击场景标签跳转到场景编辑器
    """
    def __init__(self, parent, project_manager, on_scene_select, theme_manager, command_executor=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.on_scene_select = on_scene_select
        self.theme_manager = theme_manager
        self.command_executor = command_executor

        self.current_year = datetime.now().year
        self.current_month = datetime.now().month

        # 拖放状态
        self.drag_data = None
        self.drag_win = None

        self.setup_ui()
        self.theme_manager.add_listener(self.apply_theme)

        # 订阅事件
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅 EventBus 事件"""
        bus = get_event_bus()
        bus.subscribe(Events.SCENE_ADDED, self._on_scene_event)
        bus.subscribe(Events.SCENE_UPDATED, self._on_scene_event)
        bus.subscribe(Events.SCENE_DELETED, self._on_scene_event)

    def _on_scene_event(self, event_type, **kwargs):
        """处理场景相关事件"""
        try:
            self.after(10, self.refresh)
        except tk.TclError:
            pass  # Widget 已销毁

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(toolbar, text="< 上个月", command=self.prev_month).pack(side="left")
        self.month_label = ttk.Label(toolbar, text="", font=("Arial", 12, "bold"))
        self.month_label.pack(side="left", padx=20)
        ttk.Button(toolbar, text="下个月 >", command=self.next_month).pack(side="left")
        
        # Grid
        self.grid_frame = ttk.Frame(self)
        self.grid_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Days headers
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for i, d in enumerate(days):
            self.grid_frame.columnconfigure(i, weight=1)
            lbl = ttk.Label(self.grid_frame, text=d, anchor="center")
            lbl.grid(row=0, column=i, sticky="ew", pady=2)
            
        self.day_cells = []
        for r in range(6):
            self.grid_frame.rowconfigure(r+1, weight=1)
            row_cells = []
            for c in range(7):
                cell = tk.Frame(self.grid_frame, bd=1, relief="solid")
                cell.grid(row=r+1, column=c, sticky="nsew", padx=1, pady=1)
                
                date_lbl = tk.Label(cell, text="", anchor="nw", padx=2, pady=2, font=("Arial", 10, "bold"))
                date_lbl.pack(fill="x")
                
                content_frame = tk.Frame(cell, bg="")
                content_frame.pack(fill="both", expand=True)
                
                # Make cell valid drop target
                cell.dnd_accept = self.dnd_accept
                cell.dnd_enter = self.dnd_enter
                cell.dnd_leave = self.dnd_leave
                cell.dnd_commit = self.dnd_commit
                
                # Simple custom drag and drop support since Tkinter dnd is limited
                # We will bind mouse release to check position
                
                row_cells.append({"frame": cell, "date_lbl": date_lbl, "content": content_frame, "date": None})
            self.day_cells.append(row_cells)

    def dnd_accept(self, source, event):
        """
        DND 接受检查 - 判断是否接受拖放。

        Args:
            source: 拖放源
            event: 事件对象

        Returns:
            self 表示接受，None 表示拒绝
        """
        # 检查是否是场景拖放
        if hasattr(source, 'scene_idx'):
            return self
        return self  # 默认接受

    def dnd_enter(self, source, event):
        """
        DND 进入 - 鼠标拖动进入目标区域。

        提供视觉反馈。
        """
        try:
            # 高亮当前单元格
            cell_frame = event.widget
            if hasattr(cell_frame, 'configure'):
                cell_frame.configure(relief="sunken")
        except (tk.TclError, AttributeError) as e:
            logger.debug(f"DND enter 视觉反馈失败: {e}")

    def dnd_leave(self, source, event):
        """
        DND 离开 - 鼠标拖动离开目标区域。

        恢复视觉状态。
        """
        try:
            # 恢复单元格样式
            cell_frame = event.widget
            if hasattr(cell_frame, 'configure'):
                cell_frame.configure(relief="solid")
        except (tk.TclError, AttributeError) as e:
            logger.debug(f"DND leave 视觉反馈失败: {e}")

    def dnd_commit(self, source, event):
        """
        DND 提交 - 完成拖放操作。

        更新场景的时间属性。
        """
        try:
            # 获取目标日期
            target_date = None
            x_root, y_root = event.x_root, event.y_root

            for row in self.day_cells:
                for cell in row:
                    f = cell["frame"]
                    if f.winfo_rootx() <= x_root <= f.winfo_rootx() + f.winfo_width() and \
                       f.winfo_rooty() <= y_root <= f.winfo_rooty() + f.winfo_height():
                        target_date = cell["date"]
                        break
                if target_date:
                    break

            if target_date and hasattr(source, 'scene_idx'):
                self._update_scene_time_with_command(source.scene_idx, target_date)
                self.refresh()

        except Exception as e:
            logger.error(f"DND commit 失败: {e}")

    def refresh(self):
        self.month_label.config(text=f"{self.current_year}年 {self.current_month}月")
        
        # Clear cells
        for row in self.day_cells:
            for cell in row:
                cell["date_lbl"].config(text="")
                cell["date"] = None
                for child in cell["content"].winfo_children():
                    child.destroy()
        
        # Get dates from scenes
        # Supported format: "YYYY-MM-DD" inside 'time' field
        # We'll look for regex match
        scene_dates = {} # "YYYY-MM-DD" -> [scene_idx]
        scenes = self.project_manager.get_scenes()
        for idx, scene in enumerate(scenes):
            t = scene.get("time", "")
            match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", t)
            if match:
                y, m, d = match.groups()
                date_str = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                if date_str not in scene_dates:
                    scene_dates[date_str] = []
                scene_dates[date_str].append(idx)
        
        # Fill Calendar
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        
        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                if r >= len(self.day_cells): break
                
                cell = self.day_cells[r][c]
                cell["date_lbl"].config(text=str(day))
                
                date_str = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
                cell["date"] = date_str
                
                if date_str in scene_dates:
                    for s_idx in scene_dates[date_str]:
                        s = scenes[s_idx]
                        btn = tk.Label(cell["content"], text=s.get("name"), bg="#E3F2FD", fg="black", cursor="hand2", anchor="w")
                        btn.pack(fill="x", pady=1)
                        btn.bind("<Button-1>", lambda e, i=s_idx: self.on_scene_select(i))
                        
                        # Add drag start
                        btn.bind("<B1-Motion>", lambda e, i=s_idx: self._on_drag_start(e, i))
                        btn.bind("<ButtonRelease-1>", lambda e: self._on_drag_stop(e))

        self.apply_theme()

    def _on_drag_start(self, event, scene_idx):
        if not hasattr(self, "drag_win") or not self.drag_win:
            self.drag_data = {"scene_idx": scene_idx}
            self.drag_win = tk.Toplevel(self)
            self.drag_win.overrideredirect(True)
            self.drag_win.attributes("-alpha", 0.6)
            name = self.project_manager.get_scenes()[scene_idx].get("name")
            tk.Label(self.drag_win, text=name, bg="yellow").pack()
        
        if self.drag_win:
            x, y = event.x_root, event.y_root
            self.drag_win.geometry(f"{x}+{y}")

    def _on_drag_stop(self, event):
        if hasattr(self, "drag_win") and self.drag_win:
            self.drag_win.destroy()
            self.drag_win = None
            
            # Find drop target date
            x_root, y_root = event.x_root, event.y_root
            target_date = None
            
            for row in self.day_cells:
                for cell in row:
                    # Check if coordinates inside cell
                    f = cell["frame"]
                    if f.winfo_rootx() <= x_root <= f.winfo_rootx() + f.winfo_width() and \
                       f.winfo_rooty() <= y_root <= f.winfo_rooty() + f.winfo_height():
                        target_date = cell["date"]
                        break
                if target_date: break
            
            if target_date and self.drag_data:
                self._update_scene_time(self.drag_data["scene_idx"], target_date)
                self.refresh() # Manually refresh to show change immediately

    def _update_scene_time(self, idx, new_date):
        """
        更新场景时间（旧方法，直接修改数据）。

        Args:
            idx: 场景索引
            new_date: 新日期字符串 (YYYY-MM-DD)
        """
        self._update_scene_time_with_command(idx, new_date)

    def _update_scene_time_with_command(self, idx, new_date):
        """
        使用命令模式更新场景时间，支持撤销/重做。

        Args:
            idx: 场景索引
            new_date: 新日期字符串 (YYYY-MM-DD)
        """
        scenes = self.project_manager.get_scenes()
        if idx < 0 or idx >= len(scenes):
            logger.warning(f"无效的场景索引: {idx}")
            return

        scene = scenes[idx]
        old_time = scene.get("time", "")

        # 智能替换或追加日期
        if re.search(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", old_time):
            new_time = re.sub(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", new_date, old_time)
        else:
            new_time = f"{new_date} {old_time}".strip()

        if new_time != old_time:
            new_scene = dict(scene)
            new_scene["time"] = new_time

            # 使用命令模式（如果有 command_executor）
            if self.command_executor:
                cmd = EditSceneCommand(
                    self.project_manager,
                    idx,
                    scene,
                    new_scene,
                    f"设置场景日期为 {new_date}"
                )
                self.command_executor(cmd)
                logger.debug(f"通过命令更新场景 {idx} 日期为 {new_date}")
            else:
                # 回退到直接修改
                self.project_manager.project_data["script"]["scenes"][idx] = new_scene
                self.project_manager.mark_modified()
                logger.debug(f"直接更新场景 {idx} 日期为 {new_date}")

            # 发布事件通知其他组件
            bus = get_event_bus()
            bus.publish(Events.SCENE_UPDATED, scene_idx=idx)

    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.refresh()

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.refresh()

    def apply_theme(self):
        theme = self.theme_manager.current_theme
        bg = self.theme_manager.get_color("bg_secondary")
        cell_bg = self.theme_manager.get_color("canvas_bg")
        fg = self.theme_manager.get_color("fg_primary")
        
        # Grid cells
        for row in self.day_cells:
            for cell in row:
                cell["frame"].configure(bg=cell_bg)
                cell["date_lbl"].configure(bg=cell_bg, fg=fg)
                cell["content"].configure(bg=cell_bg)
                
                # Update event buttons
                for child in cell["content"].winfo_children():
                    if theme == "Dark":
                        child.configure(bg="#264F78", fg="#FFFFFF")
                    else:
                        child.configure(bg="#E3F2FD", fg="#000000")