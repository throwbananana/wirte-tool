import tkinter as tk
from tkinter import ttk
import random
from writer_app.core.event_bus import get_event_bus, Events

class SwimlaneView(tk.Canvas):
    def __init__(self, parent, project_manager, theme_manager):
        super().__init__(parent, bg="white")
        self.project_manager = project_manager
        self.theme_manager = theme_manager

        self.cell_width = 150
        self.row_height = 80
        self.header_height = 40
        self.sidebar_width = 100

        self.theme_manager.add_listener(self.refresh)
        self._subscribe_events()

        # Scrollbars
        self.h_scroll = ttk.Scrollbar(parent, orient="horizontal", command=self.xview)
        self.v_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.yview)
        self.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

    def _subscribe_events(self):
        """订阅相关事件以自动刷新"""
        bus = get_event_bus()
        bus.subscribe(Events.SCENE_ADDED, self._on_data_changed)
        bus.subscribe(Events.SCENE_UPDATED, self._on_data_changed)
        bus.subscribe(Events.SCENE_DELETED, self._on_data_changed)
        bus.subscribe(Events.SCENE_MOVED, self._on_data_changed)
        bus.subscribe(Events.CHARACTER_ADDED, self._on_data_changed)
        bus.subscribe(Events.CHARACTER_DELETED, self._on_data_changed)

    def _on_data_changed(self, event_type=None, **kwargs):
        """响应数据变化事件"""
        self.refresh()

    def pack_controls(self):
        self.pack(side="left", fill="both", expand=True)
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")

    def refresh(self):
        self.delete("all")
        bg = self.theme_manager.get_color("canvas_bg")
        fg = self.theme_manager.get_color("fg_primary")
        self.configure(bg=bg)
        
        scenes = self.project_manager.get_scenes()
        characters = self.project_manager.get_characters()
        
        if not scenes or not characters:
            self.create_text(200, 100, text="需要至少一个场景和角色来生成泳道图", fill=fg)
            return

        # Y-Axis: Characters
        rows = [c["name"] for c in characters]
        
        # X-Axis: Scenes (Linear Time)
        cols = scenes
        
        # Draw Grid
        total_w = self.sidebar_width + len(cols) * self.cell_width
        total_h = self.header_height + len(rows) * self.row_height
        self.configure(scrollregion=(0, 0, total_w, total_h))
        
        # 1. Draw Sidebar (Characters)
        for i, char in enumerate(rows):
            y = self.header_height + i * self.row_height
            # Row Background
            self.create_rectangle(0, y, total_w, y + self.row_height, fill=bg if i%2==0 else self._darken(bg), outline="")
            # Label
            self.create_text(10, y + self.row_height/2, text=char, anchor="w", font=("Arial", 10, "bold"), fill=fg)
            # Divider
            self.create_line(0, y+self.row_height, total_w, y+self.row_height, fill="#CCC")

        # 2. Draw Header (Scenes)
        for j, scene in enumerate(cols):
            x = self.sidebar_width + j * self.cell_width
            self.create_text(x + self.cell_width/2, self.header_height/2, text=f"Scene {j+1}", fill=fg)
            self.create_line(x, 0, x, total_h, fill="#EEE", dash=(2,2))

        # 3. Draw Plot Blocks
        for j, scene in enumerate(cols):
            x = self.sidebar_width + j * self.cell_width
            scene_chars = scene.get("characters", [])
            
            for char_name in scene_chars:
                if char_name in rows:
                    i = rows.index(char_name)
                    y = self.header_height + i * self.row_height
                    
                    # Draw Block
                    # Color coding? Random for now or based on status
                    fill_c = "#4DA3FF"
                    self.create_rectangle(x+10, y+10, x+self.cell_width-10, y+self.row_height-10, fill=fill_c, outline="")
                    self.create_text(x+self.cell_width/2, y+self.row_height/2, text=scene.get("name"), width=self.cell_width-20, font=("Arial", 8), fill="white")

    def _darken(self, hex_color):
        if not hex_color or not hex_color.startswith('#'):
            return "#EEEEEE" # Default fallback
        
        try:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 3:
                hex_color = "".join([c*2 for c in hex_color])
            
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            # Darken by 5%
            new_rgb = tuple(max(0, int(c * 0.95)) for c in rgb)
            return '#{:02x}{:02x}{:02x}'.format(*new_rgb)
        except (ValueError, IndexError):
            return hex_color
