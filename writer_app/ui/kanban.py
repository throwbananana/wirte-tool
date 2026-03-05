import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from writer_app.core.accessibility import StatusIndicators
from writer_app.ui.components.empty_state_panel import EmptyStatePanel, EmptyStateConfig

class KanbanBoard(ttk.Frame):
    def __init__(self, parent, project_manager, command_executor, theme_manager):
        super().__init__(parent)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager
        
        self.columns = self.project_manager.get_kanban_columns()
        self.column_widgets = {}
        self.cards = {} # scene_index -> widget
        self.drag_data = {"item": None, "source_col": None, "scene_idx": None}
        
        self.filter_var = tk.StringVar()
        self.filter_var.trace("w", self.on_filter_change)
        
        self.setup_ui()
        
        # Listen for theme changes
        self.theme_manager.add_listener(self.apply_theme)

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(toolbar, text="过滤:").pack(side=tk.LEFT, padx=2)
        ttk.Entry(toolbar, textvariable=self.filter_var).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="设置状态列", command=self.configure_columns).pack(side=tk.RIGHT, padx=5)

        self.board_frame = ttk.Frame(self)
        self.board_frame.pack(fill=tk.BOTH, expand=True)

        # Empty state panel
        config = EmptyStateConfig.KANBAN
        self._empty_state = EmptyStatePanel(
            self,
            self.theme_manager,
            icon=config["icon"],
            title=config["title"],
            description=config["description"],
            action_text=config["action_text"],
            action_callback=self._on_empty_state_action
        )
        self._empty_state_visible = False

        self._build_columns()

    def _on_empty_state_action(self):
        """Handle empty state action button click."""
        messagebox.showinfo("提示", "请在剧本写作中添加场景，场景会自动显示在看板上。")

    def _show_empty_state(self, show: bool):
        """Show or hide the empty state panel."""
        if show and not self._empty_state_visible:
            self.board_frame.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True)
            self._empty_state_visible = True
        elif not show and self._empty_state_visible:
            self._empty_state.pack_forget()
            self.board_frame.pack(fill=tk.BOTH, expand=True)
            self._empty_state_visible = False

    def _build_columns(self):
        for widget in self.board_frame.winfo_children():
            widget.destroy()
        self.column_widgets = {}

        # Configure Grid
        for i in range(len(self.columns)):
            self.board_frame.columnconfigure(i, weight=1, uniform="col")
        self.board_frame.rowconfigure(0, weight=1)
        
        # Create Columns with accessibility icons
        for i, col_name in enumerate(self.columns):
            # Add status icon to column header for accessibility
            indicator = StatusIndicators.get_kanban_indicator(col_name)
            
            frame = ttk.LabelFrame(self.board_frame, padding=5)
            frame.grid(row=0, column=i, sticky="nsew", padx=5, pady=5)
            
            # Use labelwidget for custom font support in title
            # Note: labelwidget must be a child of the frame's parent (self.board_frame)
            title_widget = tk.Frame(self.board_frame)
            tk.Label(title_widget, text=indicator['icon'], font=indicator.get("font", ("Arial", 10))).pack(side="left")
            tk.Label(title_widget, text=f" {col_name}").pack(side="left")
            frame.configure(labelwidget=title_widget)
            
            # Scrollable area
            canvas = tk.Canvas(frame, highlightthickness=0)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags="inner")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Make inner frame wide enough
            frame.bind("<Configure>", lambda e, c=canvas, w=scrollable_frame: c.itemconfig("inner", width=e.width))

            self.column_widgets[col_name] = {
                "frame": scrollable_frame,
                "canvas": canvas
            }

    def configure_columns(self):
        current = ",".join(self.columns)
        new_cols_str = simpledialog.askstring("设置看板列", "请输入列名，用逗号分隔:", initialvalue=current, parent=self)
        if new_cols_str:
            new_cols = [c.strip() for c in new_cols_str.split(",") if c.strip()]
            if new_cols:
                self.project_manager.set_kanban_columns(new_cols)
                # self.refresh() will be triggered by listener or manual call

    def on_filter_change(self, *args):
        self.refresh()

    def refresh(self):
        # Check if columns changed
        current_cols = self.project_manager.get_kanban_columns()
        if current_cols != self.columns:
            self.columns = current_cols
            self._build_columns()

        # Clear existing cards
        for col in self.column_widgets.values():
            for widget in col["frame"].winfo_children():
                widget.destroy()
        self.cards.clear()

        filter_text = self.filter_var.get().lower()
        scenes = self.project_manager.get_scenes()

        # Show empty state if no scenes
        if not scenes:
            self._show_empty_state(True)
            return
        self._show_empty_state(False)

        for idx, scene in enumerate(scenes):
            # Apply Filter
            if filter_text:
                if filter_text not in scene.get("name", "").lower() and \
                   filter_text not in scene.get("content", "").lower():
                    continue

            status = scene.get("status", self.columns[0] if self.columns else "")
            if status not in self.columns and self.columns:
                status = self.columns[0] # Default to first column if status invalid
            
            if status and status in self.column_widgets:
                parent = self.column_widgets[status]["frame"]
                self._create_card(parent, idx, scene)
            
        self.apply_theme()

    def _create_card(self, parent, idx, scene):
        card = tk.Frame(parent, bd=1, relief="raised", padx=5, pady=5, cursor="hand2")
        card.pack(fill="x", pady=2)

        # Header row with status icon and title
        header_frame = tk.Frame(card)
        header_frame.pack(fill="x")

        # Status icon for accessibility (not just color)
        status = scene.get("status", "")
        indicator = StatusIndicators.get_kanban_indicator(status)
        status_label = tk.Label(header_frame, text=indicator['icon'], font=indicator.get("font", ("Arial", 10)))
        status_label.pack(side="left", padx=(0, 5))

        title = scene.get("name", "未命名")
        tk.Label(header_frame, text=title, font=("Microsoft YaHei", 10, "bold"), anchor="w").pack(side="left", fill="x", expand=True)

        desc = scene.get("content", "").strip()[:30].replace("\n", " ")
        if desc:
            tk.Label(card, text=desc, font=("Microsoft YaHei", 8), fg="gray", anchor="w").pack(fill="x")

        # Footer row with tags and word count
        footer_frame = tk.Frame(card)
        footer_frame.pack(fill="x")

        # Tags indicator with count text for accessibility
        tags = scene.get("tags", [])
        if tags:
            tag_text = f"[{len(tags)}]" if len(tags) > 3 else " ".join(f"#{t}" for t in tags[:3])
            tk.Label(footer_frame, text=tag_text, fg="orange", font=("Arial", 8), anchor="w").pack(side="left")

        # Word count indicator
        word_count = len(scene.get("content", ""))
        if word_count > 0:
            wc_text = f"{word_count}字"
            tk.Label(footer_frame, text=wc_text, fg="gray", font=("Arial", 8), anchor="e").pack(side="right")

        # Drag events
        card.bind("<Button-1>", lambda e, i=idx: self._on_drag_start(e, i))
        card.bind("<B1-Motion>", self._on_drag_motion)
        card.bind("<ButtonRelease-1>", self._on_drag_stop)
        
        self.cards[idx] = card

    def _on_drag_start(self, event, idx):
        self.drag_data["scene_idx"] = idx
        self.drag_data["item"] = event.widget
        # Find source column? Not strictly needed if we just check drop target
        
        # Create drag visual (toplevel)
        self.drag_win = tk.Toplevel(self)
        self.drag_win.overrideredirect(True)
        self.drag_win.attributes("-alpha", 0.6)
        
        l = tk.Label(self.drag_win, text=self.project_manager.get_scenes()[idx].get("name"), bg="yellow")
        l.pack()
        
        x, y = event.x_root, event.y_root
        self.drag_win.geometry(f"{x}+{y}")

    def _on_drag_motion(self, event):
        if self.drag_win:
            x, y = event.x_root, event.y_root
            self.drag_win.geometry(f"{x+10}+{y+10}")

    def _on_drag_stop(self, event):
        if self.drag_win:
            self.drag_win.destroy()
            self.drag_win = None
            
        # Determine drop column
        x_root = event.x_root
        target_col = None
        
        for col_name, widgets in self.column_widgets.items():
            frame = widgets["canvas"] # Use canvas as it spans the area
            fx = frame.winfo_rootx()
            fw = frame.winfo_width()
            if fx <= x_root <= fx + fw:
                target_col = col_name
                break
        
        if target_col:
            self._move_scene(self.drag_data["scene_idx"], target_col)
            
        self.drag_data = {"item": None, "source_col": None, "scene_idx": None}

    def _move_scene(self, idx, new_status):
        from writer_app.core.commands import EditSceneCommand
        
        scene = self.project_manager.get_scenes()[idx]
        if scene.get("status") == new_status:
            return
            
        new_scene = dict(scene)
        new_scene["status"] = new_status
        
        cmd = EditSceneCommand(self.project_manager, idx, scene, new_scene, f"移动场景至 {new_status}")
        self.command_executor(cmd)
        # Refresh is triggered by listener in main

    def apply_theme(self):
        theme = self.theme_manager.current_theme
        bg = self.theme_manager.get_color("bg_secondary")
        card_bg = "#FFFFFF" if theme == "Light" else "#444444"
        fg = self.theme_manager.get_color("fg_primary")
        
        self.configure(style="TFrame") # Rely on global style, or manually config if standard Frame
        
        # Configure columns
        for col in self.column_widgets.values():
            col["canvas"].configure(bg=bg)
            col["frame"].configure(style="TFrame") # or specific color if needed
            
        # Configure cards
        for card in self.cards.values():
            card.configure(bg=card_bg)
            for child in card.winfo_children():
                if isinstance(child, tk.Label):
                    if child.cget("text").startswith("●"):
                        continue
                    child.configure(bg=card_bg, fg=fg)