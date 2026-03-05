import tkinter as tk
from tkinter import ttk
from writer_app.ui.dnd_manager import DragAndDropManager
from writer_app.core.tts import TTSManager
from writer_app.ui.components.empty_state_panel import EmptyStatePanel, EmptyStateConfig

class IdeaPanel(ttk.Frame):
    def __init__(self, parent, project_manager, theme_manager):
        super().__init__(parent)
        self.project_manager = project_manager
        self.theme_manager = theme_manager
        
        self.add_command = None
        self.delete_command = None
        self.copy_command = None
        
        self.dnd_manager = DragAndDropManager()
        self.drag_start_pos = None
        
        self.setup_ui()

    def setup_ui(self):
        # Input Area
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self.on_add)
        
        add_btn = ttk.Button(input_frame, text="添加灵感", command=self.on_add)
        add_btn.pack(side=tk.LEFT)

        # List Area
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        self.tree = ttk.Treeview(list_frame, columns=("content",), show="", selectmode="browse")
        self.tree.column("content", anchor=tk.W)
        
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Drag bindings
        self.tree.bind("<Button-1>", self.on_press)
        self.tree.bind("<B1-Motion>", self.on_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_release)
        
        # Status
        self.status_lbl = ttk.Label(self, text="拖拽可生成大纲节点", foreground="gray")
        self.status_lbl.pack(anchor=tk.W, padx=5, pady=(0, 5))

        # Empty state panel
        config = EmptyStateConfig.IDEAS
        self._empty_state = EmptyStatePanel(
            list_frame,
            self.theme_manager,
            icon=config["icon"],
            title=config["title"],
            description=config["description"],
            action_text=None,  # Use input field instead
            action_callback=None
        )
        self._empty_state_visible = False

    def _show_empty_state(self, show: bool):
        """Show or hide the empty state panel."""
        if show and not self._empty_state_visible:
            self.tree.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True)
            self._empty_state_visible = True
        elif not show and self._empty_state_visible:
            self._empty_state.pack_forget()
            self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self._empty_state_visible = False

    def set_add_command(self, cmd):
        self.add_command = cmd

    def set_delete_command(self, cmd):
        self.delete_command = cmd
        
    def set_copy_command(self, cmd):
        self.copy_command = cmd

    def on_add(self, event=None):
        content = self.input_entry.get()
        if self.add_command and content:
            self.add_command(content)
            self.input_entry.delete(0, tk.END)

    def display_ideas(self, ideas):
        self.tree.delete(*self.tree.get_children())

        # Show empty state if no ideas
        if not ideas:
            self._show_empty_state(True)
            return
        self._show_empty_state(False)

        for idea in ideas:
            text = idea.get("content", "")
            uid = idea.get("uid")
            self.tree.insert("", tk.END, iid=uid, values=(text,))

    def on_double_click(self, event):
        item = self.tree.selection()
        if item and self.copy_command:
            content = self.tree.item(item[0], "values")[0]
            self.copy_command(content)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item: return
        self.tree.selection_set(item)
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="朗读", command=lambda: self.read_idea(item))
        menu.add_command(label="复制", command=lambda: self.on_double_click(None))
        menu.add_command(label="删除", command=lambda: self.delete_command(item) if self.delete_command else None)
        menu.post(event.x_root, event.y_root)

    def read_idea(self, item):
        content = self.tree.item(item, "values")[0]
        if content:
            TTSManager().speak(content)

    def show_message(self, msg):
        self.status_lbl.config(text=msg)
        self.after(2000, lambda: self.status_lbl.config(text="拖拽可生成大纲节点"))

    # --- DnD Handlers ---
    def on_press(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.drag_start_pos = (event.x, event.y)
        else:
            self.drag_start_pos = None

    def on_motion(self, event):
        if not self.drag_start_pos: return
        
        dx = abs(event.x - self.drag_start_pos[0])
        dy = abs(event.y - self.drag_start_pos[1])
        
        if dx > 5 or dy > 5: # Threshold
            item = self.tree.selection()[0]
            content = self.tree.item(item, "values")[0]
            uid = item
            
            data = {"type": "idea", "uid": uid, "content": content}
            
            # Start drag using manager
            self.dnd_manager.start_drag(self.tree, data, content[:15] + "...", event)
            self.drag_start_pos = None # Reset so we don't restart repeatedly

        self.dnd_manager.update_drag(event)

    def on_release(self, event):
        self.drag_start_pos = None
        self.dnd_manager.stop_drag()