import tkinter as tk
from tkinter import ttk
from writer_app.core.commands import EditSceneCommand

class HeartbeatTrackerCanvas(tk.Canvas):
    def __init__(self, parent, project_manager, command_executor, load_scene_callback, on_point_select=None, **kwargs):
        super().__init__(parent, bg="#FFF0F5", highlightthickness=0, **kwargs) # Pinkish background
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.load_scene_callback = load_scene_callback
        self.on_point_select = on_point_select
        
        self.points = []
        self.drag_data = {"idx": None, "y": 0}
        self.selected_idx = None
        self._refresh_job = None
        self._refresh_delay_ms = 40
        
        self.bind("<Configure>", lambda e: self._schedule_refresh())
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Double-1>", self.on_double_click)

    def refresh(self):
        self.delete("all")
        self.points = []
        
        scenes = self.project_manager.get_scenes()
        if not scenes:
            self.selected_idx = None
            if self.on_point_select:
                self.on_point_select(None)
            return
        
        w = self.winfo_width()
        h = self.winfo_height()
        margin = 50
        graph_h = h - 2 * margin
        step_x = 80
        
        # Draw Zones
        self.create_rectangle(0, margin, w, margin + graph_h * 0.33, fill="#FFCDD2", outline="", tags="zone") # Passion/High
        self.create_rectangle(0, margin + graph_h * 0.33, w, margin + graph_h * 0.66, fill="#F8BBD0", outline="", tags="zone") # Warm/Mid
        self.create_rectangle(0, margin + graph_h * 0.66, w, h - margin, fill="#FFEBEE", outline="", tags="zone") # Cold/Low
        
        # Axis Labels
        self.create_text(margin - 10, margin, text="热恋/激情 (100)", anchor="e", fill="#D81B60", font=("Arial", 8))
        self.create_text(margin - 10, margin + graph_h/2, text="暧昧/好感 (50)", anchor="e", fill="#D81B60", font=("Arial", 8))
        self.create_text(margin - 10, h - margin, text="陌生/冷淡 (0)", anchor="e", fill="#D81B60", font=("Arial", 8))

        prev_x, prev_y = None, None
        
        for i, scene in enumerate(scenes):
            val = scene.get("heartbeat", 0) # Use specific field 'heartbeat'
            try:
                val = int(val)
            except (ValueError, TypeError):
                val = 0
            
            x = margin + i * step_x
            y = h - margin - (val / 100) * graph_h
            
            # Connect line
            if prev_x is not None:
                self.create_line(prev_x, prev_y, x, y, fill="#E91E63", width=3, smooth=True)
            
            # Heart Node
            size = 10 + (val / 10) # Bigger hearts for higher values
            self._draw_heart(x, y, size, i, val)
            if i == self.selected_idx:
                self.create_oval(
                    x - size - 6,
                    y - size - 6,
                    x + size + 6,
                    y + size + 6,
                    outline="#AD1457",
                    width=2
                )
            
            # Label
            self.create_text(x, h - margin + 20, text=f"{i+1}", fill="#880E4F", font=("Arial", 8))
            self.create_text(x, y - size, text=str(val), fill="#C2185B", font=("Arial", 8))
            
            # Scene Name
            self.create_text(x, h - margin + 35, text=scene.get("name", "")[:6], angle=45, anchor="nw", fill="#555", font=("Arial", 8))

            self.points.append({"idx": i, "x": x, "y": y, "val": val})
            prev_x, prev_y = x, y
            
        self.configure(scrollregion=self.bbox("all"))
        if self.selected_idx is not None and self.selected_idx >= len(scenes):
            self.selected_idx = None
            if self.on_point_select:
                self.on_point_select(None)

    def _schedule_refresh(self):
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(self._refresh_delay_ms, self._do_refresh)

    def _do_refresh(self):
        self._refresh_job = None
        self.refresh()

    def _draw_heart(self, x, y, size, idx, val):
        # Simple heart shape using polygon
        # Top-left, Top-right, Bottom
        half = size / 2
        # A rough heart shape approximation
        pts = [
            x, y + half, # Bottom tip
            x - half, y - half * 0.5, # Left curve start
            x - half, y - size, # Left top
            x, y - half * 0.5, # Center dip
            x + half, y - size, # Right top
            x + half, y - half * 0.5 # Right curve start
        ]
        # Better using two circles and a triangle? Or just a character/image.
        # Let's use unicode ❤ or 💗 if font supports, or polygon.
        # Polygon is safer for sizing.
        # Let's use a simple diamond for now, red color intensity based on val
        
        # Color gradient from pink to deep red
        red = 255
        green = int(200 - (val * 2)) 
        blue = int(200 - (val * 2))
        color = f"#{red:02x}{max(0,green):02x}{max(0,blue):02x}"
        
        self.create_oval(x-half, y-half, x+half, y+half, fill=color, outline="white", width=2, tags=("node", f"node_{idx}"))

    def on_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        item = self.find_closest(x, y, halo=10)[0]
        tags = self.gettags(item)
        for tag in tags:
            if tag.startswith("node_"):
                idx = int(tag.split("_")[1])
                self.drag_data["idx"] = idx
                self._select_point(idx)
                break
        else:
            self._select_point(None)

    def on_drag(self, event):
        if self.drag_data["idx"] is None: return
        y = self.canvasy(event.y)
        h = self.winfo_height()
        margin = 50
        graph_h = h - 2 * margin
        
        # Clamp y
        y = max(margin, min(h - margin, y))
        
        # Calculate val
        val = 100 - ((y - margin) / graph_h * 100)
        val = int(max(0, min(100, val)))
        
        # Update point visually (simple redraw/move logic or just update text)
        # Full refresh is easiest for curves
        
        # Update temp data for responsiveness? 
        # For now, let's just update the stored value in points list and redraw
        self.points[self.drag_data["idx"]]["val"] = val
        # Update project data? No, wait for release to avoid spamming commands
        
        # Visual feedback: just move the node?
        # Actually refresh is fast enough usually
        # But we need to update the scene data temporarily or handle drag visually
        # Let's direct move the node item
        idx = self.drag_data["idx"]
        pt = self.points[idx]
        pt["y"] = y # Update Y for line drawing
        self._schedule_refresh() # Redraw all lines (debounced)

    def on_release(self, event):
        if self.drag_data["idx"] is not None:
            idx = self.drag_data["idx"]
            val = self.points[idx]["val"]
            
            scenes = self.project_manager.get_scenes()
            if 0 <= idx < len(scenes):
                scene = scenes[idx]
                if scene.get("heartbeat") != val:
                    new_scene = dict(scene)
                    new_scene["heartbeat"] = val
                    cmd = EditSceneCommand(self.project_manager, idx, scene, new_scene, f"调整心动值: {val}")
                    self.command_executor(cmd) # This triggers refresh via listener usually
            self._select_point(idx)
            
            self.drag_data["idx"] = None
        self._schedule_refresh()

    def on_double_click(self, event):
        if self.drag_data["idx"] is not None:
            self.load_scene_callback(self.drag_data["idx"])

    def _select_point(self, idx):
        if idx != self.selected_idx:
            self.selected_idx = idx
            self._schedule_refresh()
        if self.on_point_select:
            self.on_point_select(idx)


class HeartbeatScenePreview(ttk.LabelFrame):
    def __init__(self, parent, on_jump_to_scene=None):
        super().__init__(parent, text="场景锚点")
        self.on_jump_to_scene = on_jump_to_scene
        self.current_scene_index = None
        self._build_ui()

    def _build_ui(self):
        self.title_var = tk.StringVar(value="未选择场景")
        self.meta_var = tk.StringVar(value="点击心动点查看场景预览")
        self.heartbeat_var = tk.StringVar(value="")

        ttk.Label(self, textvariable=self.title_var, font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        ttk.Label(self, textvariable=self.meta_var, foreground="#666", wraplength=240).pack(anchor="w", padx=10)
        ttk.Label(self, textvariable=self.heartbeat_var, foreground="#AD1457").pack(anchor="w", padx=10, pady=(6, 6))

        ttk.Label(self, text="剧情预览:", font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        self.preview_text = tk.Text(self, height=8, wrap="word", font=("Arial", 9))
        self.preview_text.configure(state="disabled")
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.jump_btn = ttk.Button(btn_frame, text="跳转到场景", command=self._jump_to_scene, state="disabled")
        self.jump_btn.pack(side=tk.LEFT)

    def show_scene(self, scene, index):
        self.current_scene_index = index
        title = scene.get("name", "未命名")
        time_text = scene.get("time", "") or "未设置时间"
        location = scene.get("location", "") or "未设置地点"
        characters = scene.get("characters", []) or []
        char_text = "、".join(characters) if characters else "未设置角色"
        heartbeat = scene.get("heartbeat", 0)

        self.title_var.set(f"第 {index + 1} 场：{title}")
        self.meta_var.set(f"时间: {time_text} | 地点: {location} | 角色: {char_text}")
        self.heartbeat_var.set(f"心动值: {heartbeat}")

        preview = scene.get("content", "") or ""
        preview = preview.strip()
        if len(preview) > 240:
            preview = preview[:240] + "..."
        if not preview:
            preview = "（暂无剧本内容）"

        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview)
        self.preview_text.configure(state="disabled")

        self.jump_btn.configure(state="normal" if self.on_jump_to_scene else "disabled")

    def clear(self):
        self.current_scene_index = None
        self.title_var.set("未选择场景")
        self.meta_var.set("点击心动点查看场景预览")
        self.heartbeat_var.set("")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.configure(state="disabled")
        self.jump_btn.configure(state="disabled")

    def _jump_to_scene(self):
        if self.on_jump_to_scene and self.current_scene_index is not None:
            self.on_jump_to_scene(self.current_scene_index)

class HeartbeatTrackerController:
    def __init__(self, parent, project_manager, command_executor, load_scene_callback):
        self.parent = parent
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.load_scene_callback = load_scene_callback

        self.paned = ttk.Panedwindow(parent, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(self.paned)
        right_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=3)
        self.paned.add(right_frame, weight=1)

        self.view = HeartbeatTrackerCanvas(
            left_frame,
            project_manager,
            command_executor,
            load_scene_callback,
            on_point_select=self._on_point_selected
        )
        self.view.pack(fill=tk.BOTH, expand=True)

        self.preview_panel = HeartbeatScenePreview(right_frame, on_jump_to_scene=load_scene_callback)
        self.preview_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def refresh(self):
        self.view.refresh()
        self._sync_preview()

    def _on_point_selected(self, idx):
        scenes = self.project_manager.get_scenes()
        if idx is None or idx < 0 or idx >= len(scenes):
            self.preview_panel.clear()
            return
        self.preview_panel.show_scene(scenes[idx], idx)

    def _sync_preview(self):
        idx = self.view.selected_idx
        scenes = self.project_manager.get_scenes()
        if idx is None or idx < 0 or idx >= len(scenes):
            self.preview_panel.clear()
            return
        self.preview_panel.show_scene(scenes[idx], idx)
