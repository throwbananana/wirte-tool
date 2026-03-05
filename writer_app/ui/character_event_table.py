import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from writer_app.core.commands import (
    AddCharacterEventCommand,
    DeleteCharacterEventCommand,
    EditCharacterEventCommand,
)

class CharacterEventTable(ttk.Frame):
    def __init__(self, parent, project_manager, theme_manager, command_executor=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.theme_manager = theme_manager
        self.command_executor = command_executor
        self.current_char = None
        self._is_destroyed = False
        
        self.setup_ui()
        self.project_manager.add_listener(self.refresh)

    def setup_ui(self):
        # Layout: Split PanedWindow
        # Left: Character List
        # Right: Event Table
        
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- Left Side ---
        left_frame = ttk.LabelFrame(paned, text="人物列表")
        paned.add(left_frame, weight=1)
        
        self.char_list = tk.Listbox(left_frame, width=20)
        self.char_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.char_list.bind("<<ListboxSelect>>", self.on_char_select)
        
        # --- Right Side ---
        right_frame = ttk.LabelFrame(paned, text="人物事件履历")
        paned.add(right_frame, weight=3)
        
        # Toolbar
        toolbar = ttk.Frame(right_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(toolbar, text="添加事件", command=self.add_event).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="编辑", command=self.edit_event).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self.delete_event).pack(side=tk.LEFT, padx=2)
        
        # Table
        cols = ("time", "summary", "type")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings")
        self.tree.heading("time", text="时间/阶段")
        self.tree.column("time", width=100)
        self.tree.heading("summary", text="事件内容")
        self.tree.column("summary", width=400)
        self.tree.heading("type", text="类型")
        self.tree.column("type", width=80)
        
        vsb = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh(self, event_type="all"):
        if self._is_destroyed or not self.winfo_exists():
            return
        if not hasattr(self, "char_list") or not self.char_list.winfo_exists():
            return

        # Refresh char list
        current_sel = self.char_list.curselection()
        
        self.char_list.delete(0, tk.END)
        chars = self.project_manager.get_characters()
        for c in chars:
            self.char_list.insert(tk.END, c.get("name", "未命名"))
            
        if self.current_char:
            # Try to restore selection
            names = [c["name"] for c in chars]
            if self.current_char in names:
                idx = names.index(self.current_char)
                self.char_list.selection_set(idx)
                self.load_events(self.current_char)
            else:
                self.current_char = None
                self.clear_table()

    def destroy(self):
        """移除监听并销毁"""
        if not self._is_destroyed:
            self._is_destroyed = True
            if self.project_manager:
                try:
                    self.project_manager.remove_listener(self.refresh)
                except Exception:
                    pass
        super().destroy()

    def on_char_select(self, event):
        sel = self.char_list.curselection()
        if sel:
            name = self.char_list.get(sel[0])
            self.current_char = name
            self.load_events(name)

    def load_events(self, char_name):
        self.clear_table()
        events = self.project_manager.get_character_events(char_name)
        for e in events:
            self.tree.insert("", tk.END, values=(
                e.get("time", ""),
                e.get("summary", ""),
                e.get("type", "普通")
            ), tags=(e.get("uid"),)) # Store UID in tags? No, items have IIDs

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def add_event(self):
        if not self.current_char: return
        
        dlg = EventDialog(self.winfo_toplevel())
        if dlg.result:
            data = dlg.result
            if self.command_executor:
                cmd = AddCharacterEventCommand(self.project_manager, self.current_char, data)
                if self.command_executor(cmd):
                    self.load_events(self.current_char)
            else:
                self.project_manager.add_character_event(self.current_char, data)
                self.load_events(self.current_char)

    def edit_event(self):
        sel = self.tree.selection()
        if not sel: return
        # Need to find the event object. 
        # Tree doesn't store data directly.
        # We assume order matches or we need UID mapping.
        # Simple approach: find by index
        idx = self.tree.index(sel[0])
        events = self.project_manager.get_character_events(self.current_char)
        if 0 <= idx < len(events):
            event_data = events[idx]
            dlg = EventDialog(self.winfo_toplevel(), event_data)
            if dlg.result:
                if self.command_executor:
                    cmd = EditCharacterEventCommand(
                        self.project_manager,
                        self.current_char,
                        idx,
                        event_data,
                        dlg.result
                    )
                    if self.command_executor(cmd):
                        self.load_events(self.current_char)
                else:
                    events[idx].update(dlg.result)
                    self.project_manager.mark_modified("script")
                    self.load_events(self.current_char)

    def delete_event(self):
        sel = self.tree.selection()
        if not sel: return
        if messagebox.askyesno("Confirm", "Delete this event?"):
            idx = self.tree.index(sel[0])
            events = self.project_manager.get_character_events(self.current_char)
            if 0 <= idx < len(events):
                if self.command_executor:
                    cmd = DeleteCharacterEventCommand(self.project_manager, self.current_char, idx)
                    if self.command_executor(cmd):
                        self.load_events(self.current_char)
                else:
                    del events[idx]
                    self.project_manager.mark_modified("script")
                    self.load_events(self.current_char)

class EventDialog(simpledialog.Dialog):
    def __init__(self, parent, initial_data=None):
        self.initial_data = initial_data or {}
        super().__init__(parent, title="人物事件")

    def body(self, master):
        tk.Label(master, text="时间/阶段:").grid(row=0, column=0, sticky="e")
        self.e_time = tk.Entry(master, width=30)
        self.e_time.grid(row=0, column=1, padx=5, pady=2)
        self.e_time.insert(0, self.initial_data.get("time", ""))

        tk.Label(master, text="事件内容:").grid(row=1, column=0, sticky="ne")
        self.e_summary = tk.Text(master, width=30, height=5)
        self.e_summary.grid(row=1, column=1, padx=5, pady=2)
        self.e_summary.insert("1.0", self.initial_data.get("summary", ""))

        tk.Label(master, text="类型:").grid(row=2, column=0, sticky="e")
        self.cb_type = ttk.Combobox(master, values=["普通", "转折点", "背景故事", "高光时刻", "伏笔"], state="readonly")
        self.cb_type.grid(row=2, column=1, padx=5, pady=2)
        self.cb_type.set(self.initial_data.get("type", "普通"))

        return self.e_time

    def apply(self):
        self.result = {
            "time": self.e_time.get(),
            "summary": self.e_summary.get("1.0", tk.END).strip(),
            "type": self.cb_type.get()
        }
