import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import math

from writer_app.core.event_bus import get_event_bus, Events
from writer_app.ui.components.empty_state_panel import EmptyStatePanel, EmptyStateConfig


class TimelinePanel(ttk.Frame):
    def __init__(self, parent, project_manager, command_executor, theme_manager=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager
        
        # Data & State
        self.scenes = []
        self.filtered_scenes = []
        
        self.mode = "sequence" # "sequence" (plot order) or "chronological" (story time)
        self.zoom = 1.0
        self.offset_x = 50
        self.offset_y = 50
        
        self.drag_data = {"item": None, "x": 0, "y": 0, "start_x": 0, "start_index": -1}
        self.hover_item = None

        # Layout Constants
        self.LANE_HEIGHT = 100
        self.HEADER_HEIGHT = 60
        self.NODE_WIDTH = 120
        self.NODE_HEIGHT = 40
        self.DATE_PIXELS_PER_DAY = 50

        self.setup_ui()

        # Apply initial theme
        self._apply_theme()

        # Register theme listener
        if self.theme_manager:
            self.theme_manager.add_listener(self._on_theme_change)

        # 订阅事件总线
        self._subscribe_events()

    def _on_theme_change(self):
        """响应主题变化"""
        self._apply_theme()
        self.refresh()

    def _apply_theme(self):
        """应用主题颜色"""
        if self.theme_manager:
            bg = self.theme_manager.get_color("canvas_bg")
        else:
            bg = "white"
        
        if hasattr(self, 'canvas'):
            self.canvas.configure(bg=bg)

    def _subscribe_events(self):
        """订阅相关事件"""
        bus = get_event_bus()
        bus.subscribe(Events.TIMELINE_UPDATED, self._on_timeline_changed)
        bus.subscribe(Events.TIMELINE_EVENT_ADDED, self._on_timeline_changed)
        bus.subscribe(Events.TIMELINE_EVENT_UPDATED, self._on_timeline_changed)
        bus.subscribe(Events.TIMELINE_EVENT_DELETED, self._on_timeline_changed)
        bus.subscribe(Events.SCENE_ADDED, self._on_scene_changed)
        bus.subscribe(Events.SCENE_UPDATED, self._on_scene_changed)
        bus.subscribe(Events.SCENE_DELETED, self._on_scene_changed)
        bus.subscribe(Events.SCENE_MOVED, self._on_scene_changed)
        bus.subscribe(Events.PROJECT_LOADED, self._on_project_loaded)

    def _on_timeline_changed(self, event_type, **kwargs):
        """时间线变更时刷新"""
        self.refresh()

    def _on_scene_changed(self, event_type, **kwargs):
        """场景变更时刷新"""
        self.refresh()

    def _on_project_loaded(self, event_type, **kwargs):
        """项目加载时刷新"""
        self.refresh()

    def setup_ui(self):
        # --- Toolbar ---
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Mode Switch
        ttk.Label(toolbar, text="视图模式:").pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value="剧情顺序 (Plot)")
        mode_combo = ttk.Combobox(toolbar, textvariable=self.mode_var, state="readonly", width=15)
        mode_combo["values"] = ["剧情顺序 (Plot)", "时间顺序 (Story)"]
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)
        mode_combo.pack(side=tk.LEFT)
        
        # Filters
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Label(toolbar, text="角色:").pack(side=tk.LEFT, padx=5)
        self.filter_char_var = tk.StringVar(value="全部")
        self.char_filter = ttk.Combobox(toolbar, textvariable=self.filter_char_var, state="readonly", width=10)
        self.char_filter.pack(side=tk.LEFT)
        self.char_filter.bind("<<ComboboxSelected>>", self.refresh)
        
        ttk.Label(toolbar, text="标签:").pack(side=tk.LEFT, padx=5)
        self.filter_tag_var = tk.StringVar(value="全部")
        self.tag_filter = ttk.Combobox(toolbar, textvariable=self.filter_tag_var, state="readonly", width=10)
        self.tag_filter.pack(side=tk.LEFT)
        self.tag_filter.bind("<<ComboboxSelected>>", self.refresh)
        
        # Actions
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="导出图片", command=self.export_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="重置视图", command=self.reset_view).pack(side=tk.LEFT, padx=2)

        # Instructions
        ttk.Label(toolbar, text="[操作: 拖拽移动/重排 | 滚轮缩放 | 右键拖拽平移]", foreground="gray").pack(side=tk.RIGHT, padx=5)
        
        # --- Canvas ---
        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Events
        self.canvas.bind("<ButtonPress-1>", self.on_left_down)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
        
        self.canvas.bind("<ButtonPress-3>", self.on_right_down)
        self.canvas.bind("<B3-Motion>", self.on_right_drag)
        
        self.canvas.bind("<MouseWheel>", self.on_wheel) # Windows
        self.canvas.bind("<Button-4>", self.on_wheel)   # Linux/Mac
        self.canvas.bind("<Button-5>", self.on_wheel)
        
        self.canvas.bind("<Motion>", self.on_hover_motion)

        # Empty state panel
        config = EmptyStateConfig.TIMELINE
        self._empty_state = EmptyStatePanel(
            self,
            self.theme_manager,
            icon=config["icon"],
            title=config["title"],
            description=config["description"],
            action_text=config["action_text"],
            action_callback=self._on_empty_state_action
        )
        self._empty_state_visible = False

    def _on_empty_state_action(self):
        """Handle empty state action button click."""
        # This would typically open a dialog to add a new event/scene
        # For now, just show a message
        messagebox.showinfo("提示", "请在剧本写作中添加场景，场景会自动显示在时间线上。")

    def _show_empty_state(self, show: bool):
        """Show or hide the empty state panel."""
        if show and not self._empty_state_visible:
            self.canvas.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True)
            self._empty_state_visible = True
        elif not show and self._empty_state_visible:
            self._empty_state.pack_forget()
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self._empty_state_visible = False

    # --- Data Loading ---
    def load_data(self):
        self.scenes = self.project_manager.get_scenes()
        
        # Update filters
        chars = sorted(list(set(c["name"] for s in self.scenes for c in self.project_manager.get_characters() if c["name"] in s.get("characters", []))))
        tags = sorted(list(set(t for s in self.scenes for t in s.get("tags", []))))
        
        self.char_filter["values"] = ["全部"] + chars
        self.tag_filter["values"] = ["全部"] + tags
        
        # Filter
        f_char = self.filter_char_var.get()
        f_tag = self.filter_tag_var.get()
        
        self.filtered_scenes = []
        for i, s in enumerate(self.scenes):
            if f_char != "全部" and f_char not in s.get("characters", []):
                continue
            if f_tag != "全部" and f_tag not in s.get("tags", []):
                continue
            # Store original index for updates
            s_copy = s.copy()
            s_copy["_index"] = i 
            self.filtered_scenes.append(s_copy)

    def refresh(self, event=None):
        self.load_data()
        self.draw()

    def on_mode_change(self, event=None):
        val = self.mode_var.get()
        if "Plot" in val:
            self.mode = "sequence"
        else:
            self.mode = "chronological"
        self.reset_view()

    def reset_view(self):
        self.zoom = 1.0
        self.offset_x = 50
        self.offset_y = 50
        self.draw()

    # --- Drawing ---
    def draw(self):
        self.canvas.delete("all")

        # Show empty state if no scenes
        if not self.filtered_scenes:
            self._show_empty_state(True)
            return

        self._show_empty_state(False)

        if self.mode == "sequence":
            self.draw_sequence()
        else:
            self.draw_chronological()

    def _get_colors(self):
        if self.theme_manager:
            return {
                "lane_bg": self.theme_manager.get_color("timeline_lane_bg"),
                "canvas_bg": self.theme_manager.get_color("canvas_bg"),
                "text": self.theme_manager.get_color("fg_primary"),
                "line": self.theme_manager.get_color("border"),
                "link": "#999999" if self.theme_manager.current_theme == "Light" else "#777777"
            }
        else:
            return {
                "lane_bg": "#F5F5F5",
                "canvas_bg": "#FFFFFF",
                "text": "#555555",
                "line": "#DDDDDD",
                "link": "#999999"
            }

    def draw_sequence(self):
        colors = self._get_colors()
        
        # Group by location for swimlanes
        locations = sorted(list(set(s.get("location", "未分类") for s in self.filtered_scenes)))
        if not locations: locations = ["未分类"]
        
        # Draw Lanes
        max_width = len(self.filtered_scenes) * (self.NODE_WIDTH + 50) * self.zoom + 200
        if max_width < self.winfo_width(): max_width = self.winfo_width()
        
        for i, loc in enumerate(locations):
            y = self.offset_y + i * self.LANE_HEIGHT * self.zoom + self.HEADER_HEIGHT
            # Lane Bg
            fill_color = colors["lane_bg"] if i % 2 == 0 else colors["canvas_bg"]
            self.canvas.create_rectangle(0, y, max_width*2, y + self.LANE_HEIGHT * self.zoom, 
                                         fill=fill_color, outline="")
            # Label
            self.canvas.create_text(10, y + 20, text=loc, anchor="w", font=("Arial", int(10*self.zoom), "bold"), fill=colors["text"])
            # Line
            self.canvas.create_line(0, y, max_width*2, y, fill=colors["line"])

        # Draw Nodes
        start_x = self.offset_x
        gap = 40 * self.zoom
        
        # Link lines first
        prev_coords = None
        for i, scene in enumerate(self.filtered_scenes):
            loc = scene.get("location", "未分类")
            try:
                lane_idx = locations.index(loc)
            except:
                lane_idx = 0
            
            x = start_x + i * (self.NODE_WIDTH * self.zoom + gap)
            y = self.offset_y + lane_idx * self.LANE_HEIGHT * self.zoom + self.HEADER_HEIGHT + 40 * self.zoom
            
            curr_coords = (x + self.NODE_WIDTH*self.zoom/2, y)
            
            if prev_coords:
                self.canvas.create_line(prev_coords[0], prev_coords[1], curr_coords[0], curr_coords[1], 
                                        arrow=tk.LAST, fill=colors["link"], width=2)
            prev_coords = curr_coords

        # Nodes on top
        for i, scene in enumerate(self.filtered_scenes):
            loc = scene.get("location", "未分类")
            try:
                lane_idx = locations.index(loc)
            except:
                lane_idx = 0
            
            x = start_x + i * (self.NODE_WIDTH * self.zoom + gap)
            y = self.offset_y + lane_idx * self.LANE_HEIGHT * self.zoom + self.HEADER_HEIGHT + 40 * self.zoom
            
            w = self.NODE_WIDTH * self.zoom
            h = self.NODE_HEIGHT * self.zoom
            
            # Store coordinates in scene object for hit testing (optional, but using tags is better)
            tag = f"scene:{scene['_index']}"
            
            color = "#BBDEFB"
            if scene.get("type") == "action": color = "#FFCDD2" # Reddish
            
            self.canvas.create_rectangle(x, y - h/2, x + w, y + h/2, fill=color, outline="#1976D2", tags=("node", tag))
            
            # Text
            font_size = max(6, int(9 * self.zoom))
            name = scene.get("name", f"Scene {i+1}")
            if len(name) > 10: name = name[:9] + ".."
            # Node text always black for now as node bg is light
            self.canvas.create_text(x + w/2, y, text=name, width=w-5, justify="center", font=("Arial", font_size), tags=("node", tag), fill="black")
            
            # Badge for index
            self.canvas.create_oval(x-5, y-h/2-5, x+15, y-h/2+15, fill="#FFF", outline="#1976D2")
            self.canvas.create_text(x+5, y-h/2+5, text=str(i+1), font=("Arial", int(8*self.zoom), "bold"), fill="black")
            
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def draw_chronological(self):
        colors = self._get_colors()
        
        # Parse dates
        valid_scenes = []
        min_date = None
        max_date = None
        
        from writer_app.core.analysis import AnalysisUtils
        
        for s in self.filtered_scenes:
            d_str = s.get("time", "")
            # Basic parsing YYYY-MM-DD
            try:
                parsed = AnalysisUtils.parse_date(d_str)
                if parsed and "-" in parsed:  # Check if valid date format
                    dt = datetime.datetime.strptime(parsed, "%Y-%m-%d")
                    s["_dt"] = dt
                    if min_date is None or dt < min_date:
                        min_date = dt
                    if max_date is None or dt > max_date:
                        max_date = dt
                    valid_scenes.append(s)
            except (ValueError, TypeError) as e:
                # Skip scenes with invalid or unparseable dates
                continue
        
        if not valid_scenes:
            self.canvas.create_text(self.winfo_width()/2, self.winfo_height()/2, text="没有找到带有有效日期 (YYYY-MM-DD) 的场景。", font=("Arial", 14), fill=colors["text"])
            return

        # Timeline Range
        days_span = (max_date - min_date).days + 14 # Add padding
        if days_span < 10: days_span = 10
        
        pixels_per_day = self.DATE_PIXELS_PER_DAY * self.zoom
        
        # Draw Axis
        axis_y = self.offset_y + 40
        start_x = self.offset_x
        end_x = start_x + days_span * pixels_per_day
        
        self.canvas.create_line(start_x, axis_y, end_x, axis_y, width=2, arrow=tk.LAST, fill=colors["text"])
        
        # Ticks
        curr = min_date
        for i in range(days_span + 1):
            x = start_x + i * pixels_per_day
            if i % 7 == 0: # Weekly ticks
                self.canvas.create_line(x, axis_y, x, axis_y + 10, width=2, fill=colors["text"])
                date_str = curr.strftime("%Y-%m-%d")
                self.canvas.create_text(x, axis_y + 20, text=date_str, font=("Arial", int(8*self.zoom)), fill=colors["text"])
            else:
                self.canvas.create_line(x, axis_y, x, axis_y + 5, width=1, fill=colors["text"])
            curr += datetime.timedelta(days=1)
            
        # Draw Scenes
        locations = sorted(list(set(s.get("location", "未分类") for s in valid_scenes)))
        
        for i, s in enumerate(valid_scenes):
            dt = s["_dt"]
            days_diff = (dt - min_date).days
            
            x = start_x + days_diff * pixels_per_day
            
            loc = s.get("location", "未分类")
            try:
                lane_idx = locations.index(loc)
            except:
                lane_idx = 0
            
            y = axis_y + 50 + lane_idx * 60 * self.zoom
            
            w = 100 * self.zoom
            h = 30 * self.zoom
            
            tag = f"scene:{s['_index']}"
            
            self.canvas.create_line(x, axis_y, x, y, dash=(2, 2), fill=colors["line"])
            self.canvas.create_rectangle(x - w/2, y - h/2, x + w/2, y + h/2, fill="#E1BEE7", outline="#8E24AA", tags=("node", tag))
            self.canvas.create_text(x, y, text=s.get("name"), width=w-5, font=("Arial", int(8*self.zoom)), tags=("node", tag), fill="black")

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # --- Interaction ---
    def on_wheel(self, event):
        scale = 1.1
        if event.num == 5 or event.delta < 0:
            scale = 0.9
        
        self.zoom *= scale
        if self.zoom < 0.1: self.zoom = 0.1
        if self.zoom > 5.0: self.zoom = 5.0
        
        self.draw()

    def on_right_down(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_right_drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        self.offset_x += dx
        self.offset_y += dy
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.draw()

    def on_left_down(self, event):
        item = self.canvas.find_closest(event.x, event.y, halo=5)
        tags = self.canvas.gettags(item)
        
        scene_index = -1
        for t in tags:
            if t.startswith("scene:"):
                scene_index = int(t.split(":")[1])
                break
        
        if scene_index != -1:
            self.drag_data["item"] = item # Store canvas item
            self.drag_data["scene_index"] = scene_index
            self.drag_data["start_x"] = event.x
            self.drag_data["start_y"] = event.y
            self.canvas.itemconfig(item, outline="red", width=2)
            self.canvas.config(cursor="fleur")
        else:
            self.drag_data["item"] = None

    def on_left_drag(self, event):
        if self.drag_data["item"]:
            # Calculate movement delta
            dx = event.x - self.drag_data["start_x"]
            dy = event.y - self.drag_data["start_y"]

            # Move all items with the same scene tag
            tag = f"scene:{self.drag_data['scene_index']}"
            self.canvas.move(tag, dx, dy)

            self.drag_data["start_x"] = event.x
            self.drag_data["start_y"] = event.y

    def on_left_up(self, event):
        if self.drag_data["item"]:
            self.canvas.config(cursor="")
            
            # Logic to apply change
            idx = self.drag_data["scene_index"]
            final_x = event.x
            
            if self.mode == "sequence":
                # Calculate new index based on X
                # Rough estimate: (x - offset) / (width + gap)
                gap = 40 * self.zoom
                width = self.NODE_WIDTH * self.zoom
                relative_x = final_x - self.offset_x
                new_pos_idx = int(relative_x / (width + gap))
                if new_pos_idx < 0: new_pos_idx = 0
                if new_pos_idx >= len(self.filtered_scenes): new_pos_idx = len(self.filtered_scenes) - 1
                
                # Check if changed
                if len(self.filtered_scenes) == len(self.scenes):
                    if new_pos_idx != idx:
                         # We need to call controller method (not yet implemented)
                         # self.controller.move_scene(idx, new_pos_idx)
                         if hasattr(self.controller, "move_scene"):
                            self.controller.move_scene(idx, new_pos_idx)
                         else:
                            # Fallback if controller not updated yet
                            pass
                else:
                    messagebox.showinfo("提示", "请在无过滤状态下拖拽排序。")

            elif self.mode == "chronological":
                # Calculate new date
                pixels = self.DATE_PIXELS_PER_DAY * self.zoom
                diff_pixels = final_x - self.offset_x
                days_diff = int(diff_pixels / pixels)
                
                # Find min_date again 
                from writer_app.core.analysis import AnalysisUtils
                valid_dates = [datetime.datetime.strptime(AnalysisUtils.parse_date(s.get("time")), "%Y-%m-%d") 
                               for s in self.scenes if AnalysisUtils.parse_date(s.get("time"))]
                if valid_dates:
                    min_date = min(valid_dates)
                    new_date = min_date + datetime.timedelta(days=days_diff)
                    new_date_str = new_date.strftime("%Y-%m-%d")
                    
                    if hasattr(self.controller, "update_scene_date"):
                        if messagebox.askyesno("修改时间", f"将场景时间更改为 {new_date_str}?"):
                            self.controller.update_scene_date(idx, new_date_str)
                    
            self.drag_data["item"] = None
            self.refresh() # Redraw to snap to grid

    def on_hover_motion(self, event):
        item = self.canvas.find_closest(event.x, event.y, halo=5)
        tags = self.canvas.gettags(item)
        if any(t.startswith("scene:") for t in tags):
            self.canvas.config(cursor="hand2")
        else:
            self.canvas.config(cursor="")

    def export_image(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".ps", filetypes=[("PostScript", "*.ps")])
        if file_path:
            self.canvas.postscript(file=file_path, colormode="color")
            messagebox.showinfo("导出成功", f"时间轴已导出为: {file_path}\n(提示: 可使用Photoshop或在线工具转换为PNG/JPG)")