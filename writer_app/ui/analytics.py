import tkinter as tk
from tkinter import ttk
import math

class AnalyticsPanel(ttk.Frame):
    def __init__(self, parent, project_manager, gamification_manager=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.gamification_manager = gamification_manager
        self.setup_ui()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="刷新数据", command=self.refresh).pack(side=tk.LEFT)

        # Content - Scrollable
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.canvas_ref = canvas

    def refresh(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        script = self.project_manager.get_script()
        scenes = script.get("scenes", [])
        chars = script.get("characters", [])
        
        # 1. Overview Cards
        overview_frame = ttk.Frame(self.scrollable_frame)
        overview_frame.pack(fill=tk.X, padx=10, pady=10)
        
        total_words = sum(len(s.get("content", "")) for s in scenes)
        avg_scene = total_words // len(scenes) if scenes else 0
        
        self._create_card(overview_frame, "总字数", str(total_words), "#E3F2FD").pack(side=tk.LEFT, padx=5)
        self._create_card(overview_frame, "场景数", str(len(scenes)), "#E8F5E9").pack(side=tk.LEFT, padx=5)
        self._create_card(overview_frame, "角色数", str(len(chars)), "#FFF3E0").pack(side=tk.LEFT, padx=5)
        self._create_card(overview_frame, "平均字数/场", str(avg_scene), "#F3E5F5").pack(side=tk.LEFT, padx=5)

        # 2. Heatmap (Activity)
        if self.gamification_manager:
            self._create_heatmap(self.scrollable_frame, "创作热力图 (Activity Heatmap)")

        # 3. Scene Length Chart
        self._create_bar_chart("场景字数分布", [s.get("name") for s in scenes], [len(s.get("content", "")) for s in scenes])

        # 4. Location Frequency (New)
        loc_counts = {}
        for s in scenes:
            loc = s.get("location", "Unknown")
            loc_counts[loc] = loc_counts.get(loc, 0) + 1
        sorted_locs = sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        self._create_bar_chart("Top 5 场景地点", [x[0] for x in sorted_locs], [x[1] for x in sorted_locs], color="#AB47BC")

        # 5. Character Stats (Radar + Freq)
        self._create_character_radar(chars, scenes)

    def _create_character_radar(self, chars, scenes):
        container = ttk.LabelFrame(self.scrollable_frame, text="角色五维属性 & 活跃度")
        container.pack(fill=tk.X, padx=10, pady=10)
        
        # Calculate stats
        char_stats = {}
        for char in chars:
            name = char.get("name")
            # Dimensions
            # 1. Mentions (Frequency)
            mentions = sum(s.get("content", "").count(name) for s in scenes)
            # 2. Appearance (Scenes present)
            appearance = sum(1 for s in scenes if name in s.get("characters", []))
            # 3. Relations (Links)
            rels = self.project_manager.get_relationships().get("relationship_links", [])
            links = sum(1 for r in rels if r["source"] == name or r["target"] == name)
            # 4. Dialogue (Approximation: lines starting with Name)
            dialogue = 0 # complex to parse without rigid format, skip or mock
            # 5. Scenes as POV (if POV field exists, else random mock for proto)
            
            char_stats[name] = {
                "Mentions": mentions,
                "Scenes": appearance,
                "Links": links
            }
            
        # Sort top 5 active
        sorted_chars = sorted(char_stats.items(), key=lambda x: x[1]["Mentions"], reverse=True)[:5]
        
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            import matplotlib
            import numpy as np

            # 配置中文字体支持，解决"口口"乱码问题
            matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'Arial Unicode MS', 'sans-serif']
            matplotlib.rcParams['axes.unicode_minus'] = False

            fig = Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111, polar=True)
            
            categories = ["提及", "场次", "关系", "深度", "潜力"]
            
            for name, stats in sorted_chars:
                # Normalize values roughly to 0-5 scale
                values = [
                    min(5, stats["Mentions"]/10), 
                    min(5, stats["Scenes"]/2), 
                    min(5, stats["Links"]/2), 
                    np.random.randint(1, 5), # Mock Depth
                    np.random.randint(1, 5)  # Mock Potential
                ]
                values += values[:1] # Close the loop
                
                angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
                angles += angles[:1]
                
                ax.plot(angles, values, linewidth=1, label=name)
                ax.fill(angles, values, alpha=0.1)
                
            ax.set_xticks(np.linspace(0, 2 * np.pi, len(categories), endpoint=False))
            ax.set_xticklabels(categories)
            ax.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1), prop={'size': 6})
            
            canvas = FigureCanvasTkAgg(fig, master=container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except ImportError:
            tk.Label(container, text="安装 matplotlib 以查看雷达图").pack()
            # Fallback to bar chart for Top Character
            if sorted_chars:
                self._create_bar_chart("角色提及频次 (Top 10)", [x[0] for x in sorted_chars], [x[1]["Mentions"] for x in sorted_chars], color="#FF7043")

    def _create_heatmap(self, parent, title):
        container = ttk.LabelFrame(parent, text=title)
        container.pack(fill=tk.X, padx=10, pady=10)
        
        # We need datetime
        from datetime import date, timedelta, datetime
        
        # Config
        cell_size = 12
        gap = 2
        weeks = 53
        days = 7
        width = weeks * (cell_size + gap) + 20
        height = days * (cell_size + gap) + 30
        
        canvas = tk.Canvas(container, width=width, height=height, bg="white", highlightthickness=0)
        canvas.pack(padx=10, pady=10)
        
        # Get data
        activity_data = self.gamification_manager.get_stats().get("daily_activity", {})
        
        # Calculate start date (1 year ago)
        today = date.today()
        # Find the Sunday of 52 weeks ago
        start_date = today - timedelta(weeks=52)
        # Adjust to previous Sunday
        start_date = start_date - timedelta(days=(start_date.weekday() + 1) % 7)
        
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        current_month_idx = -1
        
        for w in range(weeks):
            # Draw month label if changed
            check_date = start_date + timedelta(weeks=w)
            if check_date.month != current_month_idx:
                current_month_idx = check_date.month
                x_pos = w * (cell_size + gap)
                if x_pos + 30 < width:
                    canvas.create_text(x_pos + 10, height - 10, text=months[current_month_idx-1], font=("Arial", 8), fill="#666")

            for d in range(days):
                curr = start_date + timedelta(weeks=w, days=d)
                if curr > today: break
                
                date_str = curr.isoformat()
                count = activity_data.get(date_str, 0)
                
                # Color logic
                color = "#EBEDF0" # default gray
                if count > 0:
                    if count < 500: color = "#9BE9A8"
                    elif count < 1500: color = "#40C463"
                    elif count < 3000: color = "#30A14E"
                    else: color = "#216E39"
                
                x = w * (cell_size + gap)
                y = d * (cell_size + gap)
                
                rect_id = canvas.create_rectangle(x, y, x+cell_size, y+cell_size, fill=color, outline="")
                
                # Tooltip simulated binding (simplified)
                # In full version, use a Tooltip class
                
    def _create_card(self, parent, title, value, bg_color):
        frame = tk.Frame(parent, bg=bg_color, padx=15, pady=10, relief=tk.RAISED, borderwidth=1)
        tk.Label(frame, text=title, bg=bg_color, font=("Arial", 10)).pack()
        tk.Label(frame, text=value, bg=bg_color, font=("Arial", 16, "bold")).pack()
        return frame

    def _create_bar_chart(self, title, labels, values, color="#42A5F5"):
        container = ttk.LabelFrame(self.scrollable_frame, text=title)
        container.pack(fill=tk.X, padx=10, pady=10, expand=True)
        
        if not values:
            ttk.Label(container, text="无数据").pack(pady=20)
            return

        canvas_height = 200
        canvas_width = 700
        canvas = tk.Canvas(container, height=canvas_height, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Draw chart
        margin = 30
        bar_width = min(50, (canvas_width - 2 * margin) / len(values))
        max_val = max(values) if values else 1
        
        # Fixed imports
        from datetime import datetime
        
        for i, (label, val) in enumerate(zip(labels, values)):
            x0 = margin + i * bar_width + i * 10
            bar_h = (val / max_val) * (canvas_height - 2 * margin)
            y0 = canvas_height - margin - bar_h
            x1 = x0 + bar_width
            y1 = canvas_height - margin
            
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            
            # Value
            canvas.create_text((x0+x1)/2, y0-10, text=str(val), font=("Arial", 8))
            
            # Label
            lbl = label if len(label) < 8 else label[:6] + "."
            canvas.create_text((x0+x1)/2, y1+15, text=lbl, font=("Arial", 8), angle=0)
