import tkinter as tk
import math


class PersonalityRadar(tk.Canvas):
    """Five-dimension personality radar chart (0-10 scale)."""

    def __init__(self, parent, size=160, labels=None, **kwargs):
        super().__init__(parent, width=size, height=size, highlightthickness=0, **kwargs)
        self.size = size
        self.center = size // 2
        self.radius = size // 2 - 12
        self.labels = labels or ["开放性", "尽责性", "外向性", "宜人性", "神经质"]
        self.values = {label: 5 for label in self.labels}
        self.colors = {
            "line": "#4CAF50",
            "fill": "#C8E6C9",
            "axis": "#999999",
            "text": "#666666",
        }

    def set_values(self, values):
        for label in self.labels:
            self.values[label] = float(values.get(label, 5))
        self._draw()

    def set_colors(self, **colors):
        self.colors.update(colors)
        self._draw()

    def _draw(self):
        self.delete("all")
        n = len(self.labels)
        if n < 3:
            return

        angles = [math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

        for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
            points = []
            for angle in angles:
                x = self.center + self.radius * r * math.cos(angle)
                y = self.center - self.radius * r * math.sin(angle)
                points.extend([x, y])
            self.create_line(*points, fill=self.colors["axis"], width=1, smooth=True)

        for angle, label in zip(angles, self.labels):
            x = self.center + self.radius * math.cos(angle)
            y = self.center - self.radius * math.sin(angle)
            self.create_line(self.center, self.center, x, y, fill=self.colors["axis"], width=1)

            lx = self.center + (self.radius + 12) * math.cos(angle)
            ly = self.center - (self.radius + 12) * math.sin(angle)
            self.create_text(lx, ly, text=label, font=("Microsoft YaHei", 8), fill=self.colors["text"])

        data_points = []
        for angle, label in zip(angles, self.labels):
            value = max(0.0, min(10.0, float(self.values.get(label, 5))))
            r = (value / 10.0) * self.radius
            x = self.center + r * math.cos(angle)
            y = self.center - r * math.sin(angle)
            data_points.extend([x, y])

        if len(data_points) >= 6:
            self.create_polygon(*data_points, fill=self.colors["fill"], outline=self.colors["line"], width=2)
            for i in range(0, len(data_points), 2):
                self.create_oval(
                    data_points[i] - 2,
                    data_points[i + 1] - 2,
                    data_points[i] + 2,
                    data_points[i + 1] + 2,
                    fill=self.colors["line"],
                    outline="",
                )
