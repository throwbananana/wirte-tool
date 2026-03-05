import tkinter as tk
from tkinter import ttk
from writer_app.core.commands import EditWikiEntryCommand

class WorldIcebergCanvas(tk.Canvas):
    def __init__(self, parent, project_manager, command_executor, theme_manager=None, **kwargs):
        # Default bg will be set by _apply_theme
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager
        
        self.entries = [] # List of {idx, x, y, name, depth}
        self.drag_data = {"idx": None, "x": 0, "y": 0}
        
        self.bind("<Configure>", lambda e: self.refresh())
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)

        # Apply initial theme
        self._apply_theme()

        # Register theme listener
        if self.theme_manager:
            self.theme_manager.add_listener(self._on_theme_change)

    def _on_theme_change(self):
        """Handle theme change event."""
        self._apply_theme()
        self.refresh()

    def _apply_theme(self):
        """Apply theme colors."""
        if self.theme_manager:
            bg = self.theme_manager.get_color("iceberg_bg")
        else:
            bg = "#E0F7FA"
        self.configure(bg=bg)

    def refresh(self):
        self.delete("all")
        self.entries = []
        
        # Get theme colors
        if self.theme_manager:
            deep_bg = self.theme_manager.get_color("iceberg_deep_bg")
            shallow_bg = self.theme_manager.get_color("iceberg_shallow_bg")
            surface_bg = self.theme_manager.get_color("iceberg_surface_bg")
            line_color = self.theme_manager.get_color("iceberg_line")
            text_color = self.theme_manager.get_color("iceberg_text")
        else:
            deep_bg = "#006064"
            shallow_bg = "#0097A7"
            surface_bg = "#4DD0E1"
            line_color = "#0277BD"
            text_color = "#FFFFFF"

        w = self.winfo_width()
        h = self.winfo_height()
        if h < 100: h = 600
        
        # Draw Iceberg Zones (Triangle visual)
        # Deep (Bottom)
        self.create_polygon(0, h, w, h, w/2, h/2, fill=deep_bg, outline="")
        self.create_text(w/2, h - 30, text="Deep (隐秘设定)", fill=text_color, font=("Arial", 12, "bold"))
        
        # Shallow (Middle)
        self.create_polygon(0, h/2, w, h/2, w/2, h/4, fill=shallow_bg, outline="")
        self.create_text(w/2, h/2 + 30, text="Shallow (暗示/传说)", fill=text_color, font=("Arial", 12, "bold"))
        
        # Surface (Top/Tip)
        self.create_polygon(w/4, h/4, w*0.75, h/4, w/2, 0, fill=surface_bg, outline="")
        self.create_text(w/2, h/8 + 20, text="Surface (显性信息)", fill=text_color, font=("Arial", 12, "bold"))
        
        # Draw Water Line
        self.create_line(0, h/4, w, h/4, fill=line_color, width=3, dash=(4,2))
        
        # Plot Entries
        wiki_entries = self.project_manager.get_world_entries()
        
        # Group by depth
        zones = {"surface": [], "shallow": [], "deep": []}
        
        for i, entry in enumerate(wiki_entries):
            depth = entry.get("iceberg_depth", "surface")
            if depth not in zones: depth = "surface"
            zones[depth].append((i, entry))
            
        # Layout items in zones
        # Surface: Top area
        self._layout_zone(zones["surface"], w/2, h/8, w/3, h/6, "surface")
        # Shallow: Mid area
        self._layout_zone(zones["shallow"], w/2, h*0.375, w*0.6, h/4, "shallow")
        # Deep: Bottom area
        self._layout_zone(zones["deep"], w/2, h*0.75, w*0.8, h/3, "deep")

    def _layout_zone(self, items, cx, cy, width, height, zone_name):
        if not items: return
        
        import math
        # Simple grid or scatter
        cols = int(math.sqrt(len(items))) + 1
        rows = math.ceil(len(items) / cols)
        
        step_x = width / (cols + 1)
        step_y = height / (rows + 1)
        
        start_x = cx - width/2
        start_y = cy - height/2
        
        for i, (idx, entry) in enumerate(items):
            r = i // cols
            c = i % cols
            
            x = start_x + (c+1) * step_x
            y = start_y + (r+1) * step_y
            
            self._draw_entry(x, y, entry["name"], idx, zone_name)

    def _draw_entry(self, x, y, name, idx, depth):
        if self.theme_manager:
            bg = self.theme_manager.get_color("iceberg_entry_bg")
            fg = self.theme_manager.get_color("iceberg_entry_fg")
            outline = self.theme_manager.get_color("iceberg_entry_outline")
        else:
            bg = "white"
            fg = "black"
            outline = "#00838F"
        
        w = len(name) * 12 + 10
        h = 24
        
        tag = f"entry_{idx}"
        self.create_rectangle(x - w/2, y - h/2, x + w/2, y + h/2, fill=bg, outline=outline, width=2, tags=(tag, "item"))
        self.create_text(x, y, text=name, fill=fg, font=("Arial", 9), tags=(tag, "item"))
        
        self.entries.append({"idx": idx, "x": x, "y": y, "name": name, "depth": depth})

    def on_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        item = self.find_closest(x, y, halo=5)[0]
        tags = self.gettags(item)
        for tag in tags:
            if tag.startswith("entry_"):
                idx = int(tag.split("_")[1])
                self.drag_data["idx"] = idx
                self.drag_data["x"] = x
                self.drag_data["y"] = y
                break

    def on_drag(self, event):
        idx = self.drag_data["idx"]
        if idx is None: return
        
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        dx = x - self.drag_data["x"]
        dy = y - self.drag_data["y"]
        
        self.move(f"entry_{idx}", dx, dy)
        self.drag_data["x"] = x
        self.drag_data["y"] = y

    def on_release(self, event):
        idx = self.drag_data["idx"]
        if idx is None: return
        
        # Determine new zone based on Y
        y = self.canvasy(event.y)
        h = self.winfo_height()
        
        new_depth = "surface"
        if y > h * 0.6:
            new_depth = "deep"
        elif y > h * 0.3:
            new_depth = "shallow"
            
        entries = self.project_manager.get_world_entries()
        if 0 <= idx < len(entries):
            entry = entries[idx]
            if entry.get("iceberg_depth") != new_depth:
                old_data = dict(entry)
                new_data = dict(entry)
                new_data["iceberg_depth"] = new_depth
                cmd = EditWikiEntryCommand(self.project_manager, idx, old_data, new_data)
                self.command_executor(cmd)
        
        self.drag_data["idx"] = None
        self.refresh()

class WorldIcebergController:
    def __init__(self, parent, project_manager, command_executor, theme_manager=None):
        self.view = WorldIcebergCanvas(parent, project_manager, command_executor, theme_manager)
        self.view.pack(fill=tk.BOTH, expand=True)
        
    def refresh(self):
        self.view.refresh()
