import tkinter as tk
from tkinter import ttk

class AchievementsDialog(tk.Toplevel):
    def __init__(self, parent, gamification_manager):
        super().__init__(parent)
        self.title("我的成就 (My Achievements)")
        self.geometry("600x500")
        self.gamification_manager = gamification_manager
        
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.bind_mouse_wheel(self.canvas)
        self.bind_mouse_wheel(self.scrollable_frame)

        self._populate()

    def bind_mouse_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")

    def _populate(self):
        status = self.gamification_manager.get_achievements_status()
        
        # Grid layout: 2 columns
        row = 0
        col = 0
        
        for item in status:
            self._create_card(item, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

    def _create_card(self, item, row, col):
        frame = tk.Frame(self.scrollable_frame, relief="groove", borderwidth=1, padx=10, pady=10, bg="#f9f9f9" if item['unlocked'] else "#eeeeee")
        frame.grid(row=row, column=col, sticky="ew", padx=10, pady=10, ipadx=5)
        
        # Icon
        icon_lbl = tk.Label(frame, text=item["icon"], font=("Segoe UI Emoji", 24), bg=frame["bg"])
        if not item["unlocked"]:
            icon_lbl.config(fg="#999")
        icon_lbl.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        
        # Name
        name_fg = "#000" if item["unlocked"] else "#777"
        tk.Label(frame, text=item["name"], font=("Arial", 12, "bold"), fg=name_fg, bg=frame["bg"]).grid(row=0, column=1, sticky="w")
        
        # Desc
        desc_fg = "#555" if item["unlocked"] else "#999"
        tk.Label(frame, text=item["desc"], font=("Arial", 10), fg=desc_fg, bg=frame["bg"], wraplength=180, justify="left").grid(row=1, column=1, sticky="w")
        
        # Reward
        reward_fg = "#d9534f" if item["unlocked"] else "#aaa"
        tk.Label(frame, text=f"+{item['xp_reward']} XP", font=("Arial", 9, "bold"), fg=reward_fg, bg=frame["bg"]).grid(row=2, column=1, sticky="e")
