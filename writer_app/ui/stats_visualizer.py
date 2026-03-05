import tkinter as tk
import math
from typing import Dict

class StatsVisualizer(tk.Toplevel):
    def __init__(self, parent, data: Dict[str, float], title="Skill Profile"):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x550")
        self.data = data
        self.configure(bg="#f0f0f0")
        
        self.canvas = tk.Canvas(self, width=400, height=400, bg="white", highlightthickness=0)
        self.canvas.pack(pady=20, expand=True)
        
        self.draw_radar_chart()
        self.draw_legend()

    def draw_radar_chart(self):
        cx, cy = 200, 200
        radius = 150
        labels = list(self.data.keys())
        values = list(self.data.values())
        num_vars = len(labels)
        
        if num_vars < 3:
            self.canvas.create_text(cx, cy, text="Not enough data to chart", font=("Arial", 14))
            return

        angle_step = 2 * math.pi / num_vars
        
        # Draw Background (Web)
        for i in range(1, 6): # 5 rings
            r = radius * i / 5
            points = []
            for j in range(num_vars):
                angle = j * angle_step - math.pi / 2 # Start from top
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                points.extend([x, y])
            self.canvas.create_polygon(points, outline="#e0e0e0", fill="", width=1)

        # Draw Axes
        for j in range(num_vars):
            angle = j * angle_step - math.pi / 2
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            self.canvas.create_line(cx, cy, x, y, fill="#e0e0e0")
            
            # Draw Labels
            lx = cx + (radius + 20) * math.cos(angle)
            ly = cy + (radius + 20) * math.sin(angle)
            self.canvas.create_text(lx, ly, text=labels[j], font=("Arial", 10, "bold"))

        # Draw Data Polygon
        data_points = []
        for j, val in enumerate(values):
            # Val is 0-10 usually
            normalized = min(val / 10.0, 1.0) 
            r = radius * normalized
            angle = j * angle_step - math.pi / 2
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            data_points.extend([x, y])
            
            # Draw point
            self.canvas.create_oval(x-3, y-3, x+3, y+3, fill="#4CAF50", outline="")

        if len(data_points) >= 4:
            self.canvas.create_polygon(data_points, outline="#4CAF50", fill="#4CAF50", width=2, stipple="gray25")

    def draw_legend(self):
        lbl = tk.Label(self, text="Scale: 0 - 10 (AI Score)", bg="#f0f0f0", font=("Arial", 9, "italic"))
        lbl.pack(side=tk.BOTTOM, pady=10)
