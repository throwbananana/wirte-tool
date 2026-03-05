import tkinter as tk
from tkinter import ttk
import math
import logging

from writer_app.core.commands import EditSceneCommand, MoveSceneCommand

logger = logging.getLogger(__name__)

class StoryCurveCanvas(tk.Canvas):
    def __init__(self, parent, project_manager, command_executor, load_scene_callback, theme_manager=None, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.load_scene_callback = load_scene_callback
        self.theme_manager = theme_manager
        
        self.scene_nodes = [] # List of {idx, x, y, scene_data}
        self.drag_data = {"idx": None, "start_y": 0, "start_x": 0, "start_val": 0, "target_idx": None}
        self.drop_indicator = None
        
        # Config
        self.margin_left = 50
        self.margin_right = 50
        self.margin_top = 40
        self.margin_bottom = 50
        self.node_radius = 6
        self.scene_step_x = 80 # pixels per scene
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Double-1>", self.on_double_click)
        self.bind("<Configure>", lambda e: self.refresh())

        # Apply theme
        self._apply_theme()
        if self.theme_manager:
            self.theme_manager.add_listener(self._on_theme_change)

    def _on_theme_change(self):
        self._apply_theme()
        self.refresh()

    def _apply_theme(self):
        if self.theme_manager:
            bg = self.theme_manager.get_color("canvas_bg")
        else:
            bg = "white"
        self.configure(bg=bg)

    def _get_colors(self):
        if self.theme_manager:
            return {
                "axis": self.theme_manager.get_color("border"),
                "text": self.theme_manager.get_color("fg_secondary"),
                "grid": self.theme_manager.get_color("border"),
                "label": self.theme_manager.get_color("fg_primary"),
                "val_label": self.theme_manager.get_color("fg_secondary"),
                "node_bg": self.theme_manager.get_color("canvas_bg")
            }
        else:
            return {
                "axis": "#ccc",
                "text": "#999",
                "grid": "#ccc",
                "label": "#555",
                "val_label": "#999",
                "node_bg": "white"
            }

    def refresh(self):
        self.delete("all")
        self.scene_nodes = []
        self.drop_indicator = None
        
        scenes = self.project_manager.get_scenes()
        colors = self._get_colors()

        if not scenes:
            self.create_text(self.winfo_width()/2, self.winfo_height()/2, text="暂无场景，请先添加场景。", fill=colors["text"])
            return

        h = self.winfo_height()
        if h < 200: h = 400 # Default if not packed yet
        
        # Calculate Geometry
        graph_h = h - self.margin_top - self.margin_bottom
        total_w = max(self.winfo_width(), self.margin_left + self.margin_right + len(scenes) * self.scene_step_x)
        self.configure(scrollregion=(0, 0, total_w, h))

        # Draw Axis
        self.create_line(self.margin_left, self.margin_top, self.margin_left, h - self.margin_bottom, fill=colors["axis"], width=2) # Y axis
        self.create_line(self.margin_left, h - self.margin_bottom, total_w - self.margin_right, h - self.margin_bottom, fill=colors["axis"], width=2) # X axis
        
        # Draw Y Labels (0, 50, 100)
        for val in [0, 50, 100]:
            y = self._val_to_y(val, graph_h)
            self.create_text(self.margin_left - 10, y, text=str(val), fill=colors["text"], anchor="e", font=("Arial", 8))
            self.create_line(self.margin_left - 5, y, self.margin_left, y, fill=colors["grid"])

        # Plot Points
        tension_points = []
        pacing_points = []
        valence_points = []
        
        for i, scene in enumerate(scenes):
            # 1. Manual Tension (0-100) - Blue
            tension = scene.get("tension", 50)
            try:
                tension = int(tension)
            except (ValueError, TypeError):
                tension = 50
            
            x = self.margin_left + i * self.scene_step_x + self.scene_step_x / 2
            
            # Tension Point
            y_tension = self._val_to_y(tension, graph_h)
            tension_points.append((x, y_tension))
            
            self.scene_nodes.append({"idx": i, "x": x, "y": y_tension, "val": tension, "type": "tension", "name": scene.get("name")})

            # 2. AI Pacing (1-10) -> Map to 10-100 - Red
            pacing = scene.get("ai_pacing")
            if pacing is not None:
                try:
                    pacing_val = float(pacing) * 10
                    y_pacing = self._val_to_y(pacing_val, graph_h)
                    pacing_points.append((x, y_pacing))
                    self.create_oval(x-4, y_pacing-4, x+4, y_pacing+4, fill="#E91E63", outline=colors["node_bg"], tags=("node_ai", f"pacing_{i}"))
                except (ValueError, TypeError) as e:
                    logger.debug(f"场景 {i} 的 AI pacing 值无效: {pacing}, 错误: {e}")

            # 3. AI Valence (-5 to +5) -> Map to 0-100 (0=-5, 50=0, 100=5) - Green
            valence = scene.get("ai_valence")
            if valence is not None:
                try:
                    # Map -5..5 to 0..100
                    # val = (v + 5) * 10
                    valence_val = (float(valence) + 5) * 10
                    y_valence = self._val_to_y(valence_val, graph_h)
                    valence_points.append((x, y_valence))
                    self.create_oval(x-4, y_valence-4, x+4, y_valence+4, fill="#4CAF50", outline=colors["node_bg"], tags=("node_ai", f"valence_{i}"))
                except (ValueError, TypeError) as e:
                    logger.debug(f"场景 {i} 的 AI valence 值无效: {valence}, 错误: {e}")

        # Draw Curves
        if len(tension_points) > 1:
            self.create_line(tension_points, fill="#2196F3", width=3, smooth=True, tags="curve_tension")
        if len(pacing_points) > 1:
            self.create_line(pacing_points, fill="#E91E63", width=2, dash=(4, 2), smooth=True, tags="curve_pacing")
        if len(valence_points) > 1:
            self.create_line(valence_points, fill="#4CAF50", width=2, dash=(2, 2), smooth=True, tags="curve_valence")

        # Draw Nodes & Labels (Only for primary tension node for interactions)
        for node in [n for n in self.scene_nodes if n["type"] == "tension"]:
            x, y = node["x"], node["y"]
            r = self.node_radius
            tag = f"node_{node['idx']}"
            self.create_oval(x-r, y-r, x+r, y+r, fill="#1976D2", outline=colors["node_bg"], width=2, tags=("node", tag))
            
            lbl_y = h - self.margin_bottom + 10
            if node['idx'] % 2 == 1: lbl_y += 15
            self.create_text(x, lbl_y, text=node["name"], font=("Arial", 9), fill=colors["label"], tags=("label", f"label_{node['idx']}"))
            self.create_text(x, y - 15, text=str(node["val"]), font=("Arial", 8), fill=colors["val_label"], tags=("val_label", tag))
            
        # Legend
        lx = self.margin_left
        ly = 10
        self.create_line(lx, ly, lx+20, ly, fill="#2196F3", width=3)
        self.create_text(lx+25, ly, text="手动张力", anchor="w", fill=colors["label"], font=("Arial", 8))
        
        self.create_line(lx+80, ly, lx+100, ly, fill="#E91E63", width=2, dash=(4,2))
        self.create_text(lx+105, ly, text="AI节奏(Pacing)", anchor="w", fill=colors["label"], font=("Arial", 8))
        
        self.create_line(lx+180, ly, lx+200, ly, fill="#4CAF50", width=2, dash=(2,2))
        self.create_text(lx+205, ly, text="AI情绪(Valence)", anchor="w", fill=colors["label"], font=("Arial", 8))


    def _val_to_y(self, val, graph_h):
        # 0 at bottom, 100 at top
        # y = margin_top + (1 - val/100) * graph_h
        return self.margin_top + (1 - max(0, min(100, val)) / 100.0) * graph_h

    def _y_to_val(self, y, graph_h):
        rel_y = y - self.margin_top
        val = 100 * (1 - rel_y / graph_h)
        return max(0, min(100, int(val)))

    def on_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        closest = self.find_closest(x, y, halo=self.node_radius)
        if not closest:
            return
        item = closest[0]
        tags = self.gettags(item)
        
        self.drag_data["idx"] = None
        for tag in tags:
            if tag.startswith("node_") and not tag.startswith("node_rect"):
                idx = int(tag.split("_")[1])
                # Find the tension node
                node = next((n for n in self.scene_nodes if n["idx"] == idx and n["type"] == "tension"), None)
                if node:
                    self.drag_data["idx"] = idx
                    self.drag_data["start_y"] = y
                    self.drag_data["start_x"] = x
                    self.drag_data["start_val"] = node["val"]
                    self.drag_data["target_idx"] = idx
                break

    def on_drag(self, event):
        if self.drag_data["idx"] is None:
            return
            
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        idx = self.drag_data["idx"]
        colors = self._get_colors()
        
        # Calculate new value for display
        h = self.winfo_height()
        graph_h = h - self.margin_top - self.margin_bottom
        new_val = self._y_to_val(y, graph_h)
        
        # Visual Update of the Node
        r = self.node_radius
        self.coords(f"node_{idx}", x-r, y-r, x+r, y+r)
        self.delete(f"val_label") # Clear value label to avoid clutter or update it
        self.create_text(x, y - 15, text=str(new_val), font=("Arial", 8), fill=colors["label"], tags="val_label")

        # Determine drop target index
        # Calculate visual index based on x
        # x starts at margin_left + step/2
        # index = (x - margin_left) / step
        raw_idx = (x - self.margin_left) / self.scene_step_x
        # We need total count of scenes to clamp
        total_scenes = len([n for n in self.scene_nodes if n["type"] == "tension"])
        target_idx = max(0, min(total_scenes, int(round(raw_idx))))
        
        self.drag_data["target_idx"] = target_idx
        
        # Draw Drop Indicator
        if self.drop_indicator:
            self.delete(self.drop_indicator)
            
        if target_idx != idx:
            # Draw vertical line at target slot
            line_x = self.margin_left + target_idx * self.scene_step_x
            self.drop_indicator = self.create_line(line_x, self.margin_top, line_x, h - self.margin_bottom, fill="#FF5722", width=2, dash=(4, 4))

    def on_release(self, event):
        if self.drop_indicator:
            self.delete(self.drop_indicator)
            self.drop_indicator = None

        if self.drag_data["idx"] is not None:
            idx = self.drag_data["idx"]
            target_idx = self.drag_data["target_idx"]
            start_val = self.drag_data["start_val"]
            
            x, y = self.canvasx(event.x), self.canvasy(event.y)
            h = self.winfo_height()
            graph_h = h - self.margin_top - self.margin_bottom
            final_val = self._y_to_val(y, graph_h)
            
            scenes = self.project_manager.get_scenes()
            current_scene = scenes[idx] if 0 <= idx < len(scenes) else None
            
            commands_executed = False

            # 1. Handle Move
            if target_idx != idx and 0 <= target_idx <= len(scenes):
                # Adjust target_idx logic for move command
                # If we drag right, target_idx is the slot *after* the item.
                # Logic: standard MoveSceneCommand handles it.
                cmd = MoveSceneCommand(self.project_manager, idx, target_idx)
                self.command_executor(cmd, refresh_mindmap=False)
                # After move, the scene is at a new index.
                # If target > idx, it's at target_idx - 1 (inserted) ? No, checking MoveSceneCommand logic.
                # If to > from: target_idx -= 1.
                # So the new index of our scene is:
                new_scene_idx = target_idx if target_idx <= idx else target_idx - 1
                idx = new_scene_idx # Update idx for next step
                current_scene = scenes[idx] # Re-fetch just in case
                commands_executed = True

            # 2. Handle Value Edit
            if current_scene and final_val != start_val:
                new_scene_data = dict(current_scene)
                new_scene_data["tension"] = final_val
                cmd = EditSceneCommand(self.project_manager, idx, current_scene, new_scene_data, f"调整场景 '{current_scene.get('name')}' 情绪值")
                self.command_executor(cmd, refresh_mindmap=False)
                commands_executed = True
            
            if commands_executed:
                self.refresh()
            else:
                # Just snap back
                self.refresh()
            
            self.drag_data["idx"] = None

    def on_double_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        item = self.find_closest(x, y, halo=self.node_radius)[0]
        tags = self.gettags(item)
        for tag in tags:
            if tag.startswith("node_") and not tag.startswith("node_rect"):
                idx = int(tag.split("_")[1])
                if self.load_scene_callback:
                    self.load_scene_callback(idx)
                break

class StoryCurveController:

    def __init__(self, parent, project_manager, command_executor, theme_manager, load_scene_callback, ai_controller=None):
        self.parent = parent
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.load_scene_callback = load_scene_callback
        self.ai_controller = ai_controller
        self.theme_manager = theme_manager
        self.ai_analyze_btn = None
        self.toolbar_btn_frame = None
        
        self.setup_ui()
        
    def setup_ui(self):
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(toolbar, text="拖动蓝色节点调整手动张力 | 双击跳转", foreground="#666").pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side=tk.RIGHT)
        self.toolbar_btn_frame = btn_frame
        
        if self.ai_controller:
            ttk.Button(btn_frame, text="🤖 AI全部分析", command=self.analyze_all).pack(side=tk.LEFT, padx=5)
            
        ttk.Button(btn_frame, text="刷新", command=self.refresh).pack(side=tk.LEFT)
        
        container = ttk.Frame(self.parent)
        container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = StoryCurveCanvas(
            container, 
            self.project_manager, 
            self.command_executor, 
            self.load_scene_callback,
            self.theme_manager
        )
        
        h_scroll = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=h_scroll.set)
        
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.refresh()

    def _cache_ai_button(self):
        if self.ai_analyze_btn or not self.toolbar_btn_frame:
            return
        for child in self.toolbar_btn_frame.winfo_children():
            try:
                if "AI全部分析" in child.cget("text"):
                    self.ai_analyze_btn = child
                    break
            except Exception:
                continue

    def set_ai_mode_enabled(self, enabled: bool):
        self._cache_ai_button()
        if self.ai_analyze_btn:
            state = tk.NORMAL if enabled else tk.DISABLED
            self.ai_analyze_btn.config(state=state)

    def analyze_all(self):
        scenes = []
        for i, s in enumerate(self.project_manager.get_scenes()):
            scenes.append({"idx": i, "name": s.get("name"), "content": s.get("content", "")})
            
        if not scenes: return
        
        def on_done(results):
            # Apply results
            for idx, res in results.items():
                if 0 <= idx < len(self.project_manager.get_scenes()):
                    scene = self.project_manager.get_scenes()[idx]
                    # Update directly or via command? Command is safer for undo/listeners
                    old_data = dict(scene)
                    new_data = dict(scene)
                    new_data["ai_pacing"] = res["pacing"]
                    new_data["ai_valence"] = res["valence"]
                    
                    if old_data != new_data:
                        cmd = EditSceneCommand(self.project_manager, idx, old_data, new_data, "AI分析更新")
                        self.command_executor(cmd, refresh_mindmap=False)
            self.refresh()
            
        self.ai_controller.analyze_scene_pacing(scenes, on_done)

    def refresh(self):
        self.canvas.refresh()
