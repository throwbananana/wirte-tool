import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class RelationshipTimelinePanel(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.snapshots = []
        self.current_idx = -1 # -1 means Live (or len(snapshots))
        self.frames = []
        self.frame_map = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        # Layout:
        # [Prev] [Slider ----------------] [Next] [Add]
        #        [ Label: Snapshot Name ]
        
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, expand=True)
        
        self.btn_prev = ttk.Button(top_frame, text="<", width=3, command=self.go_prev)
        self.btn_prev.pack(side=tk.LEFT)
        
        self.slider_var = tk.DoubleVar()
        self.slider = ttk.Scale(top_frame, variable=self.slider_var, orient=tk.HORIZONTAL, command=self.on_slider_move)
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.btn_next = ttk.Button(top_frame, text=">", width=3, command=self.go_next)
        self.btn_next.pack(side=tk.LEFT)
        
        ttk.Separator(top_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.btn_add = ttk.Button(top_frame, text="+", width=3, command=self.controller.save_snapshot)
        self.btn_add.pack(side=tk.LEFT)
        
        self.btn_del = ttk.Button(top_frame, text="-", width=3, command=self.controller.delete_snapshot)
        self.btn_del.pack(side=tk.LEFT)
        
        self.lbl_info_var = tk.StringVar(value="当前状态 (Live)")
        self.lbl_info = ttk.Label(self, textvariable=self.lbl_info_var, font=("Arial", 9, "bold"), anchor="center")
        self.lbl_info.pack(fill=tk.X, pady=(2, 0))
        
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, pady=(4, 0))

        ttk.Label(mode_frame, text="视图:").pack(side=tk.LEFT)
        self.view_mode_var = tk.StringVar(value="snapshot")
        ttk.Radiobutton(
            mode_frame,
            text="快照",
            variable=self.view_mode_var,
            value="snapshot",
            command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Radiobutton(
            mode_frame,
            text="事件帧",
            variable=self.view_mode_var,
            value="frame",
            command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(mode_frame, text="帧:").pack(side=tk.LEFT, padx=(10, 2))
        self.frame_var = tk.StringVar(value="当前状态 (Live)")
        self.frame_combo = ttk.Combobox(mode_frame, textvariable=self.frame_var, state="readonly", width=30)
        self.frame_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.frame_combo.bind("<<ComboboxSelected>>", self._on_frame_selected)
        
        # Context menu for rename
        self.lbl_info.bind("<Button-3>", self.on_label_right_click)
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="重命名节点...", command=self.rename_current)

    def update_data(self, snapshots, current_idx):
        self.snapshots = snapshots
        # Map: 0..N-1 are snapshots. N is Live.
        max_val = len(snapshots)
        self.slider.configure(to=max_val, from_=0)
        
        # Determine internal index vs slider value
        # current_idx: -1 is Live. In slider terms, that's max_val.
        # current_idx: 0..N-1. In slider terms, that's 0..N-1.
        
        if current_idx == -1:
            slider_val = max_val
        else:
            slider_val = current_idx
            
        self.slider_var.set(slider_val)
        self.update_label(slider_val)
        self._sync_mode_controls()

    def update_frames(self, frames, current_frame_id, mode):
        self.frames = frames or []
        self.frame_map = {}

        values = ["当前状态 (Live)"]
        for idx, frame in enumerate(self.frames):
            title = frame.get("title", "未命名帧")
            display = f"{idx + 1}. {title}"
            values.append(display)
            self.frame_map[display] = frame.get("frame_id")

        self.frame_combo["values"] = values
        if mode:
            self.view_mode_var.set(mode)

        display = "当前状态 (Live)"
        if current_frame_id:
            for key, frame_id in self.frame_map.items():
                if frame_id == current_frame_id:
                    display = key
                    break
        self.frame_var.set(display)
        self._sync_mode_controls()
        self.update_frame_label()

    def on_slider_move(self, value):
        val = int(round(float(value)))
        if val != self.get_current_slider_val():
            self.controller.switch_to_snapshot_by_slider(val)
            self.update_label(val)

    def get_current_slider_val(self):
        # Convert internal controller index to slider value
        if self.controller.current_snapshot_idx == -1:
            return len(self.snapshots)
        return self.controller.current_snapshot_idx

    def update_label(self, val):
        val = int(round(val))
        if val >= len(self.snapshots):
            self.lbl_info_var.set("🔴 当前状态 (Live)")
            self.btn_del.configure(state=tk.DISABLED)
        else:
            name = self.snapshots[val].get("name", "未命名")
            self.lbl_info_var.set(f"⚫ [{val+1}/{len(self.snapshots)}] {name}")
            self.btn_del.configure(state=tk.NORMAL)

    def go_prev(self):
        val = int(round(self.slider_var.get()))
        if val > 0:
            self.slider_var.set(val - 1)
            self.on_slider_move(val - 1)

    def update_frame_label(self):
        if self.view_mode_var.get() != "frame":
            return
        display = self.frame_var.get() or "当前状态 (Live)"
        self.lbl_info_var.set(f"?? {display}")
        self.btn_del.configure(state=tk.DISABLED)

    def go_next(self):
        val = int(round(self.slider_var.get()))
        max_val = len(self.snapshots)
        if val < max_val:
            self.slider_var.set(val + 1)
            self.on_slider_move(val + 1)

    def on_label_right_click(self, event):
        val = int(round(self.slider_var.get()))
        if val < len(self.snapshots):
            self.context_menu.post(event.x_root, event.y_root)

    def rename_current(self):
        val = int(round(self.slider_var.get()))
        if val < len(self.snapshots):
            self.controller.rename_snapshot(val)

    def _on_mode_change(self):
        mode = self.view_mode_var.get()
        self.controller.set_timeline_mode(mode)
        self._sync_mode_controls()
        self.update_frame_label()

    def _on_frame_selected(self, event=None):
        display = self.frame_var.get()
        frame_id = self.frame_map.get(display, "")
        self.controller.switch_to_frame(frame_id)
        self.update_frame_label()

    def _sync_mode_controls(self):
        is_frame = self.view_mode_var.get() == "frame"
        state_snap = tk.DISABLED if is_frame else tk.NORMAL
        self.btn_prev.configure(state=state_snap)
        self.btn_next.configure(state=state_snap)
        self.slider.configure(state=state_snap)
        self.btn_add.configure(state=state_snap)
        self.btn_del.configure(state=state_snap)
        self.frame_combo.configure(state="readonly" if is_frame else tk.DISABLED)
