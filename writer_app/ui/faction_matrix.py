import tkinter as tk
from tkinter import ttk, simpledialog
from writer_app.core.commands import UpdateFactionRelationCommand

class FactionMatrixCanvas(tk.Canvas):
    def __init__(self, parent, project_manager, on_relation_select=None, **kwargs):
        super().__init__(parent, bg="#111", highlightthickness=0, **kwargs)
        self.project_manager = project_manager
        self.on_relation_select = on_relation_select
        self.selected_pair = None
        
        self.bind("<Configure>", lambda e: self.refresh())
        self.bind("<Button-1>", self.on_click)

    def refresh(self):
        self.delete("all")
        
        factions = self.project_manager.get_factions()
        matrix = self.project_manager.get_faction_matrix()
        
        if not factions:
            self.create_text(self.winfo_width()/2, self.winfo_height()/2, text="暂无势力。请点击上方添加。", fill="#555")
            return
            
        n = len(factions)
        w = self.winfo_width()
        h = self.winfo_height()
        
        padding = 100
        cell_size = min((w - padding*2) / (n+1), (h - padding*2) / (n+1))
        cell_size = min(80, max(40, cell_size))
        
        start_x = padding
        start_y = padding
        
        # Headers
        for i, f in enumerate(factions):
            # Row Header
            y = start_y + (i+1) * cell_size
            self.create_text(start_x - 10, y + cell_size/2, text=f["name"], anchor="e", fill="white", font=("Arial", 9, "bold"))
            
            # Col Header
            x = start_x + (i+1) * cell_size
            self.create_text(x + cell_size/2, start_y - 10, text=f["name"], anchor="s", angle=45, fill="white", font=("Arial", 9, "bold"))

        # Grid
        for r in range(n):
            for c in range(n):
                if r == c: continue # Diagonal
                
                f_row = factions[r]
                f_col = factions[c]
                
                x = start_x + (c+1) * cell_size
                y = start_y + (r+1) * cell_size
                
                # Get value
                val = matrix.get(f_row["uid"], {}).get(f_col["uid"], 0)
                
                # Color based on val (-100 red to 100 green)
                # Normalize to 0-255
                # 0 -> gray
                if val < 0:
                    intensity = int(abs(val) / 100 * 255)
                    color = f"#{intensity:02x}0000"
                else:
                    intensity = int(val / 100 * 255)
                    color = f"#00{intensity:02x}00"
                
                if val == 0: color = "#333"
                
                tag = f"cell_{f_row['uid']}_{f_col['uid']}"
                outline = "#FFD54F" if self.selected_pair == (f_row["uid"], f_col["uid"]) else "#555"
                width = 2 if self.selected_pair == (f_row["uid"], f_col["uid"]) else 1
                self.create_rectangle(x, y, x+cell_size, y+cell_size, fill=color, outline=outline, width=width, tags=tag)
                self.create_text(x + cell_size/2, y + cell_size/2, text=str(val), fill="white", tags=tag)

    def on_click(self, event):
        item = self.find_closest(self.canvasx(event.x), self.canvasy(event.y))[0]
        tags = self.gettags(item)
        for tag in tags:
            if tag.startswith("cell_"):
                parts = tag.split("_")
                uid_a, uid_b = parts[1], parts[2]
                self.selected_pair = (uid_a, uid_b)
                if self.on_relation_select:
                    self.on_relation_select(uid_a, uid_b)
                self.refresh()
                break

    def set_selected_pair(self, uid_a, uid_b):
        self.selected_pair = (uid_a, uid_b) if uid_a and uid_b else None
        self.refresh()


class FactionRelationPanel(ttk.LabelFrame):
    def __init__(self, parent, project_manager, command_executor=None, on_value_change=None):
        super().__init__(parent, text="属性面板")
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.on_value_change = on_value_change
        self._selected_pair = None
        self._suspend_updates = False
        self._apply_job = None

        self._build_ui()

    def _build_ui(self):
        self.title_var = tk.StringVar(value="未选择关系")
        self.meta_var = tk.StringVar(value="点击矩阵格子查看关系详情")
        ttk.Label(self, textvariable=self.title_var, font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        ttk.Label(self, textvariable=self.meta_var, foreground="#666", wraplength=240).pack(anchor="w", padx=10)

        self.value_var = tk.IntVar(value=0)
        self.scale_var = tk.DoubleVar(value=0)

        self.scale = ttk.Scale(self, from_=-100, to=100, variable=self.scale_var, command=self._on_scale_change)
        self.scale.pack(fill=tk.X, padx=10, pady=(10, 4))

        entry_frame = ttk.Frame(self)
        entry_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Label(entry_frame, text="关系值:").pack(side=tk.LEFT)
        self.value_entry = ttk.Entry(entry_frame, textvariable=self.value_var, width=6)
        self.value_entry.pack(side=tk.LEFT, padx=6)
        ttk.Label(entry_frame, text="(-100 ~ 100)").pack(side=tk.LEFT, padx=4)

        self.apply_btn = ttk.Button(self, text="应用", command=self._apply_relation_change, state="disabled")
        self.apply_btn.pack(anchor="e", padx=10, pady=(0, 10))

        self.value_entry.bind("<Return>", self._apply_relation_change)
        self.value_entry.bind("<FocusOut>", self._apply_relation_change)

    def set_selection(self, uid_a, uid_b):
        self._cancel_pending()
        self._selected_pair = None
        if not uid_a or not uid_b:
            self._show_empty()
            return

        name_a, name_b = self._resolve_faction_names(uid_a, uid_b)
        matrix = self.project_manager.get_faction_matrix()
        curr_val = matrix.get(uid_a, {}).get(uid_b, 0)

        self._suspend_updates = True
        self.title_var.set(f"{name_a} → {name_b}")
        self.meta_var.set("拖动滑杆或输入数值，实时调整外交关系。")
        self.value_var.set(int(curr_val))
        self.scale_var.set(float(curr_val))
        self.apply_btn.configure(state="normal")
        self._selected_pair = (uid_a, uid_b)
        self._suspend_updates = False

    def _show_empty(self):
        self.title_var.set("未选择关系")
        self.meta_var.set("点击矩阵格子查看关系详情")
        self.value_var.set(0)
        self.scale_var.set(0)
        self.apply_btn.configure(state="disabled")

    def _on_scale_change(self, value):
        if self._suspend_updates:
            return
        try:
            value = int(float(value))
        except (TypeError, ValueError):
            value = 0
        self.value_var.set(value)
        self._schedule_apply()

    def _apply_relation_change(self, event=None):
        if not self._selected_pair:
            return
        try:
            value = int(self.value_var.get())
        except (TypeError, ValueError):
            value = 0
        value = max(-100, min(100, value))
        self.value_var.set(value)
        self.scale_var.set(float(value))

        uid_a, uid_b = self._selected_pair
        matrix = self.project_manager.get_faction_matrix()
        curr_val = matrix.get(uid_a, {}).get(uid_b, 0)
        if curr_val == value:
            return
        cmd = UpdateFactionRelationCommand(self.project_manager, uid_a, uid_b, value)
        self._execute_command(cmd)
        if self.on_value_change:
            self.on_value_change()

    def _schedule_apply(self, delay_ms=300):
        if self._apply_job:
            self.after_cancel(self._apply_job)
        self._apply_job = self.after(delay_ms, self._apply_relation_change)

    def _execute_command(self, cmd):
        if self.command_executor:
            self.command_executor(cmd)
        else:
            cmd.execute()

    def _resolve_faction_names(self, uid_a, uid_b):
        factions = self.project_manager.get_factions()
        name_map = {f.get("uid"): f.get("name", "") for f in factions}
        return name_map.get(uid_a, uid_a), name_map.get(uid_b, uid_b)

    def _cancel_pending(self):
        if self._apply_job:
            self.after_cancel(self._apply_job)
            self._apply_job = None

class FactionMatrixController:
    def __init__(self, parent, project_manager, command_executor=None):
        self.parent = parent
        self.project_manager = project_manager
        self.command_executor = command_executor
        
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="+ 添加势力", command=self.add_faction).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT)
        
        paned = ttk.Panedwindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(paned)
        right_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=4)
        paned.add(right_frame, weight=1)

        self.view = FactionMatrixCanvas(left_frame, project_manager, on_relation_select=self._on_relation_select)
        self.view.pack(fill=tk.BOTH, expand=True)

        self.relation_panel = FactionRelationPanel(
            right_frame,
            project_manager,
            command_executor=command_executor,
            on_value_change=self.refresh
        )
        self.relation_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def add_faction(self):
        name = simpledialog.askstring("添加势力", "势力名称:")
        if name:
            self.project_manager.add_faction(name)
            self.refresh()

    def refresh(self):
        self.view.refresh()
        if self.view.selected_pair:
            uid_a, uid_b = self.view.selected_pair
            self.relation_panel.set_selection(uid_a, uid_b)
        else:
            self.relation_panel.set_selection(None, None)

    def _on_relation_select(self, uid_a, uid_b):
        self.relation_panel.set_selection(uid_a, uid_b)
