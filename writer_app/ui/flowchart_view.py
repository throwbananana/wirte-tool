import tkinter as tk
import math
import tkinter as tk
from writer_app.ui.components.zoomable_canvas import ZoomableCanvas

class StoryFlowCanvas(ZoomableCanvas):
    def __init__(self, parent, project_manager, on_jump_to_scene=None, on_add_connection=None, **kwargs):
        super().__init__(parent, bg="#FAFAFA", highlightthickness=0, **kwargs)
        self.project_manager = project_manager
        self.on_jump_to_scene = on_jump_to_scene
        self.on_add_connection = on_add_connection
        
        self.node_width = 120
        self.node_height = 50
        self.node_items = {} # scene_name -> {x, y, items: []}
        
        # Dragging
        self.drag_data = {"item": None, "x": 0, "y": 0, "node_name": None}
        self.link_drag_data = {"start_node": None, "line_id": None}
        
        # Simple cache for positions (scene_name -> [x, y])
        # In a real app, we should save this to project_data
        self.positions = {}
        
        # Force Layout
        self.force_layout_active = False
        self.velocity = {} 
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Double-1>", self.on_double_click)
        
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<B3-Motion>", self.on_right_drag)
        self.bind("<ButtonRelease-3>", self.on_right_release)

    def on_double_click(self, event):
        """双击节点跳转到对应场景"""
        if not self.on_jump_to_scene:
            return

        wx, wy = self.canvasx(event.x), self.canvasy(event.y)
        items = self.find_overlapping(wx - 5, wy - 5, wx + 5, wy + 5)
        node_name = None
        for item in items:
            tags = self.gettags(item)
            for t in tags:
                if t.startswith("node_"):
                    node_name = t[5:]
                    break
            if node_name:
                break

        if not node_name:
            return

        scenes = self.project_manager.get_scenes()
        idx = next((i for i, s in enumerate(scenes) if s.get("name") == node_name), None)
        if idx is None:
            return

        self.on_jump_to_scene(idx)

    def refresh(self):
        self.delete("all")
        self.node_items.clear()
        
        scenes = self.project_manager.get_scenes()
        if not scenes: return

        # 1. Build Graph
        # nodes: scene names
        # edges: (src, tgt)
        node_names = [s.get("name", f"Scene {i+1}") for i, s in enumerate(scenes)]
        edges = []
        
        for s in scenes:
            src = s.get("name")
            if not src: continue
            for c in s.get("choices", []):
                tgt = c.get("target_scene")
                if tgt and tgt in node_names:
                    edges.append((src, tgt, c.get("text", ""), c.get("condition", "")))

        # 2. Init Layout
        # If positions empty, do a simple grid or circle
        if not self.positions:
            cols = math.ceil(math.sqrt(len(node_names)))
            spacing_x = 200
            spacing_y = 150
            for i, name in enumerate(node_names):
                r = i // cols
                c = i % cols
                self.positions[name] = [100 + c * spacing_x, 100 + r * spacing_y]
        
        # Ensure all current nodes have positions
        for name in node_names:
            if name not in self.positions:
                self.positions[name] = [100, 100]

        # 3. Draw Links
        for src, tgt, label, condition in edges:
            if src in self.positions and tgt in self.positions:
                self._draw_link(src, tgt, label, condition)

        # 4. Draw Nodes
        for i, scene in enumerate(scenes):
            name = scene.get("name", f"Scene {i+1}")
            pos = self.positions.get(name, [100, 100])
            self._draw_node(name, pos[0], pos[1], scene.get("content", ""))

        if self.scale_factor != 1.0:
            self.scale("all", 0, 0, self.scale_factor, self.scale_factor)
            self.configure(scrollregion=self.bbox("all"))
        
        if not self.force_layout_active:
             self.start_force_layout()

    def _draw_node(self, name, x, y, content):
        w = self.node_width
        h = self.node_height
        tag = f"node_{name}"
        
        # Rect
        color = "#E1F5FE"
        self.create_rectangle(x-w/2, y-h/2, x+w/2, y+h/2, fill=color, outline="#0277BD", width=2, tags=(tag, "node"))
        
        # Text
        display_name = name if len(name) < 15 else name[:12] + "..."
        self.create_text(x, y, text=display_name, font=("Microsoft YaHei", 9, "bold"), tags=(tag, "label"))
        
        self.node_items[name] = {"x": x, "y": y}

    def _draw_link(self, src, tgt, label, condition=None):
        x1, y1 = self.positions[src]
        x2, y2 = self.positions[tgt]
        
        # Style based on condition
        dash = (4, 2) if condition else None
        fill = "#C62828" if condition else "#555" # Red if conditional
        width = 2 if condition else 1
        
        # Simple straight line for now
        self.create_line(x1, y1, x2, y2, arrow=tk.LAST, fill=fill, width=width, dash=dash, tags=("link"))
        
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        
        display_label = label
        if condition:
            display_label += " (?)"
            
        if display_label:
            self.create_text(mid_x, mid_y, text=display_label, font=("Arial", 8), fill=fill, tags=("link_label"))

    def start_force_layout(self):
        if not self.force_layout_active:
            self.force_layout_active = True
            self.velocity = {name: {"vx": 0, "vy": 0} for name in self.positions}
            self._step_force_layout()

    def stop_force_layout(self):
        self.force_layout_active = False

    def _step_force_layout(self):
        if not self.force_layout_active: return
        
        # Simple layout params
        k = 150
        repulsion = 200000
        damping = 0.85
        dt = 0.1
        
        scenes = self.project_manager.get_scenes()
        nodes = list(self.node_items.keys())
        
        forces = {n: {"fx": 0, "fy": 0} for n in nodes}
        
        # Repulsion
        for i, n1 in enumerate(nodes):
            for n2 in nodes[i+1:]:
                x1, y1 = self.positions[n1]
                x2, y2 = self.positions[n2]
                dx = x1 - x2
                dy = y1 - y2
                dist_sq = dx*dx + dy*dy
                if dist_sq < 1: dist_sq = 1
                dist = math.sqrt(dist_sq)
                f = repulsion / dist_sq
                fx = f * dx / dist
                fy = f * dy / dist
                forces[n1]["fx"] += fx
                forces[n1]["fy"] += fy
                forces[n2]["fx"] -= fx
                forces[n2]["fy"] -= fy
        
        # Attraction (Edges)
        for s in scenes:
            src = s.get("name")
            if not src or src not in self.positions: continue
            for c in s.get("choices", []):
                tgt = c.get("target_scene")
                if tgt and tgt in self.positions:
                    x1, y1 = self.positions[src]
                    x2, y2 = self.positions[tgt]
                    dx = x2 - x1
                    dy = y2 - y1
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist < 1: dist = 1
                    f = (dist - k) * 0.5
                    fx = f * dx / dist
                    fy = f * dy / dist
                    
                    forces[src]["fx"] += fx
                    forces[src]["fy"] += fy
                    forces[tgt]["fx"] -= fx
                    forces[tgt]["fy"] -= fy
                    
        # Update
        total_kinetic = 0
        for n in nodes:
            vx = (self.velocity[n]["vx"] + forces[n]["fx"] * dt) * damping
            vy = (self.velocity[n]["vy"] + forces[n]["fy"] * dt) * damping
            self.velocity[n]["vx"] = vx
            self.velocity[n]["vy"] = vy
            self.positions[n][0] += vx * dt
            self.positions[n][1] += vy * dt
            total_kinetic += (vx*vx + vy*vy)
            
        self.refresh() # Full refresh is expensive, but simplest for MVP
        
        if total_kinetic > 1 and self.force_layout_active:
             self.after(50, self._step_force_layout)
        else:
            self.stop_force_layout()

    def on_click(self, event):
        # Hit test
        wx, wy = self.canvasx(event.x), self.canvasy(event.y)
        items = self.find_closest(wx, wy)
        if not items:
            return
        item = items[0]
        tags = self.gettags(item)
        
        node_name = None
        for t in tags:
            if t.startswith("node_"):
                node_name = t[5:]
                break
        
        if node_name:
            self.drag_data["item"] = item
            self.drag_data["x"] = wx
            self.drag_data["y"] = wy
            self.drag_data["node_name"] = node_name

    def on_drag(self, event):
        if self.drag_data["node_name"]:
            wx, wy = self.canvasx(event.x), self.canvasy(event.y)
            dx = wx - self.drag_data["x"]
            dy = wy - self.drag_data["y"]
            
            name = self.drag_data["node_name"]
            self.positions[name][0] += dx
            self.positions[name][1] += dy
            
            self.drag_data["x"] = wx
            self.drag_data["y"] = wy
            self.refresh() # Redraw

    def on_release(self, event):
        self.drag_data["item"] = None
        self.drag_data["node_name"] = None
        # In real app, save positions here

    def on_right_click(self, event):
        # Start linking
        wx, wy = self.canvasx(event.x), self.canvasy(event.y)
        items = self.find_closest(wx, wy)
        if not items:
            return
        item = items[0]
        tags = self.gettags(item)
        node_name = None
        for t in tags:
            if t.startswith("node_"):
                node_name = t[5:]
                break
        
        if node_name:
            self.link_drag_data["start_node"] = node_name
            # Create temp line
            x, y = self.positions[node_name]
            self.link_drag_data["line_id"] = self.create_line(x, y, wx, wy, dash=(4, 4), fill="blue", width=2)

    def on_right_drag(self, event):
        if self.link_drag_data["line_id"]:
            wx, wy = self.canvasx(event.x), self.canvasy(event.y)
            x, y = self.positions[self.link_drag_data["start_node"]]
            self.coords(self.link_drag_data["line_id"], x, y, wx, wy)

    def on_right_release(self, event):
        if self.link_drag_data["line_id"]:
            self.delete(self.link_drag_data["line_id"])
            self.link_drag_data["line_id"] = None
            
            wx, wy = self.canvasx(event.x), self.canvasy(event.y)
            # Check drop target
            # Use 'find_overlapping' for better hit test on release
            items = self.find_overlapping(wx-5, wy-5, wx+5, wy+5)
            target_node = None
            for item in items:
                tags = self.gettags(item)
                for t in tags:
                    if t.startswith("node_"):
                        target_node = t[5:]
                        break
                if target_node: break
            
            start_node = self.link_drag_data["start_node"]
            if target_node and target_node != start_node and self.on_add_connection:
                self.on_add_connection(start_node, target_node)
            
            self.link_drag_data["start_node"] = None
