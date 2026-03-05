import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from datetime import datetime

class TruthEventDialog(tk.Toplevel):
    """Dialog to edit detailed Truth Event properties for Layer 1."""
    def __init__(self, parent, event_data=None):
        super().__init__(parent)
        self.title("真相事件详情 (Layer 1: The Truth)")
        self.geometry("500x550")
        self.result = None
        self.event_data = event_data or {}
        
        self.setup_ui()
        self.transient(parent)
        self.grab_set()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. Basic Info
        ttk.Label(main_frame, text="事件名称:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.name_var = tk.StringVar(value=self.event_data.get("name", ""))
        ttk.Entry(main_frame, textvariable=self.name_var).pack(fill=tk.X, pady=(0, 10))
        
        # 2. Absolute Time
        ttk.Label(main_frame, text="绝对时间 (YYYY-MM-DD HH:MM):", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.time_var = tk.StringVar(value=self.event_data.get("timestamp", ""))
        ttk.Entry(main_frame, textvariable=self.time_var).pack(fill=tk.X, pady=(0, 10))
        
        # 3. The Truth Fields
        grp = ttk.LabelFrame(main_frame, text="物理事实 (The Truth)", padding=10)
        grp.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Motive
        ttk.Label(grp, text="真实动机 (Why):", foreground="#d9534f").grid(row=0, column=0, sticky=tk.NW, pady=2)
        self.motive_text = tk.Text(grp, height=3, width=40, font=("", 9))
        self.motive_text.insert("1.0", self.event_data.get("motive", ""))
        self.motive_text.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        # Action
        ttk.Label(grp, text="真实行动 (What):", foreground="#0275d8").grid(row=1, column=0, sticky=tk.NW, pady=2)
        self.action_text = tk.Text(grp, height=3, width=40, font=("", 9))
        self.action_text.insert("1.0", self.event_data.get("action", ""))
        self.action_text.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        # Chaos
        ttk.Label(grp, text="意外变量 (Chaos):", foreground="#f0ad4e").grid(row=2, column=0, sticky=tk.NW, pady=2)
        self.chaos_text = tk.Text(grp, height=3, width=40, font=("", 9))
        self.chaos_text.insert("1.0", self.event_data.get("chaos", ""))
        self.chaos_text.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        
        grp.columnconfigure(1, weight=1)
        
        # 4. Location
        ttk.Label(main_frame, text="真实地点:").pack(anchor=tk.W, pady=(10, 2))
        self.loc_var = tk.StringVar(value=self.event_data.get("location", ""))
        ttk.Entry(main_frame, textvariable=self.loc_var).pack(fill=tk.X)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="保存", command=self.on_save).pack(side=tk.RIGHT)

    def on_save(self):
        self.result = {
            "name": self.name_var.get().strip(),
            "timestamp": self.time_var.get().strip(),
            "motive": self.motive_text.get("1.0", tk.END).strip(),
            "action": self.action_text.get("1.0", tk.END).strip(),
            "chaos": self.chaos_text.get("1.0", tk.END).strip(),
            "location": self.loc_var.get().strip(),
            "uid": self.event_data.get("uid") or None, # Preserve UID or let caller gen
            "linked_scene_uid": self.event_data.get("linked_scene_uid")
        }
        self.destroy()

class LieEventDialog(tk.Toplevel):
    """Dialog to edit detailed Lie Event properties for Layer 2."""
    def __init__(self, parent, event_data=None):
        super().__init__(parent)
        self.title("谎言事件详情 (Layer 2: The Lie)")
        self.geometry("500x600")
        self.result = None
        self.event_data = event_data or {}
        
        self.setup_ui()
        self.transient(parent)
        self.grab_set()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. Basic Info
        ttk.Label(main_frame, text="事件名称:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.name_var = tk.StringVar(value=self.event_data.get("name", ""))
        ttk.Entry(main_frame, textvariable=self.name_var).pack(fill=tk.X, pady=(0, 10))
        
        # 2. Fabricated Time
        ttk.Label(main_frame, text="对外宣称时间 (YYYY-MM-DD HH:MM):", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.time_var = tk.StringVar(value=self.event_data.get("timestamp", ""))
        ttk.Entry(main_frame, textvariable=self.time_var).pack(fill=tk.X, pady=(0, 10))
        
        # 3. The Lie Fields
        grp = ttk.LabelFrame(main_frame, text="嫌疑人诡计 (The Lie)", padding=10)
        grp.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Surface Motive
        ttk.Label(grp, text="表面动机/借口 (Excuse):", foreground="#007BFF").grid(row=0, column=0, sticky=tk.NW, pady=2)
        self.motive_text = tk.Text(grp, height=3, width=40, font=("", 9))
        self.motive_text.insert("1.0", self.event_data.get("motive", ""))
        self.motive_text.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        # Information Gap
        ttk.Label(grp, text="信息差/隐瞒内容 (Gap):", foreground="#f0ad4e").grid(row=1, column=0, sticky=tk.NW, pady=2)
        self.gap_text = tk.Text(grp, height=3, width=40, font=("", 9))
        self.gap_text.insert("1.0", self.event_data.get("gap", ""))
        self.gap_text.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        # Flaw/Bug
        ttk.Label(grp, text="破绽/与真相的矛盾 (Flaw/Bug):", foreground="#d9534f").grid(row=2, column=0, sticky=tk.NW, pady=2)
        self.bug_text = tk.Text(grp, height=3, width=40, font=("", 9))
        self.bug_text.insert("1.0", self.event_data.get("bug", ""))
        self.bug_text.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        
        grp.columnconfigure(1, weight=1)

        # 4. Linked Truth Event (for conflict detection)
        ttk.Label(main_frame, text="关联的真相事件UID (可选):").pack(anchor=tk.W, pady=(10, 2))
        self.linked_truth_var = tk.StringVar(value=self.event_data.get("linked_truth_event_uid", ""))
        ttk.Entry(main_frame, textvariable=self.linked_truth_var).pack(fill=tk.X)
        ttk.Label(main_frame, text="可从真相线上右键事件获取UID", font=("", 8), foreground="gray").pack(anchor=tk.W)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="保存", command=self.on_save).pack(side=tk.RIGHT)

    def on_save(self):
        self.result = {
            "name": self.name_var.get().strip(),
            "timestamp": self.time_var.get().strip(),
            "motive": self.motive_text.get("1.0", tk.END).strip(),
            "gap": self.gap_text.get("1.0", tk.END).strip(),
            "bug": self.bug_text.get("1.0", tk.END).strip(),
            "uid": self.event_data.get("uid") or None,
            "linked_truth_event_uid": self.linked_truth_var.get().strip() or None
        }
        self.destroy()
