import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class HistoryBrowserDialog(tk.Toplevel):
    """Dialog for browsing and navigating command history."""

    def __init__(self, parent, command_history, on_navigate=None):
        super().__init__(parent)
        self.title("操作历史")
        self.geometry("500x400")
        self.transient(parent)

        self.command_history = command_history
        self.on_navigate = on_navigate

        self._setup_ui()
        self._refresh_list()

        # Register listener for history changes
        self.command_history.add_listener(self._on_history_changed)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """Setup the dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Info label
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.stats_label = ttk.Label(info_frame, text="")
        self.stats_label.pack(side=tk.LEFT)

        # Treeview for history list
        columns = ("index", "description", "time", "status")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("index", text="#")
        self.tree.heading("description", text="操作描述")
        self.tree.heading("time", text="时间")
        self.tree.heading("status", text="状态")

        self.tree.column("index", width=40, anchor="center")
        self.tree.column("description", width=250)
        self.tree.column("time", width=100, anchor="center")
        self.tree.column("status", width=60, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        self.goto_btn = ttk.Button(btn_frame, text="跳转到此状态", command=self._goto_selected)
        self.goto_btn.pack(side=tk.LEFT, padx=5)

        self.undo_btn = ttk.Button(btn_frame, text="撤销 (Ctrl+Z)", command=self._do_undo)
        self.undo_btn.pack(side=tk.LEFT, padx=5)

        self.redo_btn = ttk.Button(btn_frame, text="重做 (Ctrl+Y)", command=self._do_redo)
        self.redo_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="关闭", command=self._on_close).pack(side=tk.RIGHT, padx=5)

        # Double-click to go to state
        self.tree.bind("<Double-1>", lambda e: self._goto_selected())

        # Update button states
        self._update_buttons()

    def _refresh_list(self):
        """Refresh the history list."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get history
        history = self.command_history.get_history_list(include_redo=True)
        current_index = len(self.command_history.undo_stack) - 1

        # Insert items
        for i, (description, timestamp, is_undone) in enumerate(history):
            time_str = timestamp.strftime("%H:%M:%S") if timestamp else "-"
            status = "已撤销" if is_undone else "已执行"

            # Determine if this is current state
            tags = ()
            if not is_undone and i == current_index:
                tags = ("current",)
            elif is_undone:
                tags = ("undone",)

            self.tree.insert("", tk.END, values=(i + 1, description, time_str, status), tags=tags)

        # Configure tags for styling
        self.tree.tag_configure("current", background="#E3F2FD")
        self.tree.tag_configure("undone", foreground="#999999")

        # Update stats
        stats = self.command_history.get_stats()
        self.stats_label.config(
            text=f"可撤销: {stats['undo_count']} | 可重做: {stats['redo_count']}"
        )

        self._update_buttons()

    def _update_buttons(self):
        """Update button states."""
        self.undo_btn.config(state=tk.NORMAL if self.command_history.can_undo() else tk.DISABLED)
        self.redo_btn.config(state=tk.NORMAL if self.command_history.can_redo() else tk.DISABLED)

        # Enable goto button only if item selected
        selection = self.tree.selection()
        self.goto_btn.config(state=tk.NORMAL if selection else tk.DISABLED)

    def _goto_selected(self):
        """Navigate to the selected history state."""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        target_index = int(item["values"][0]) - 1  # Convert to 0-based

        current_index = len(self.command_history.undo_stack) - 1

        if target_index == current_index:
            return  # Already at this state

        if target_index < current_index:
            # Need to undo
            count = self.command_history.undo_to_index(target_index + 1)
            if count > 0 and self.on_navigate:
                self.on_navigate()
        else:
            # Need to redo
            count = self.command_history.redo_to_index(target_index)
            if count > 0 and self.on_navigate:
                self.on_navigate()

        self._refresh_list()

    def _do_undo(self):
        """Perform undo."""
        if self.command_history.undo():
            if self.on_navigate:
                self.on_navigate()
            self._refresh_list()

    def _do_redo(self):
        """Perform redo."""
        if self.command_history.redo():
            if self.on_navigate:
                self.on_navigate()
            self._refresh_list()

    def _on_history_changed(self):
        """Handle history change event."""
        if self.winfo_exists():
            self._refresh_list()

    def _on_close(self):
        """Clean up and close dialog."""
        self.command_history.remove_listener(self._on_history_changed)
        self.destroy()


class BackupBrowserDialog(tk.Toplevel):
    """Dialog for browsing and restoring backups."""

    def __init__(self, parent, backup_manager, on_restore=None):
        super().__init__(parent)
        self.title("备份管理")
        self.geometry("600x400")
        self.transient(parent)

        self.backup_manager = backup_manager
        self.on_restore = on_restore

        self._setup_ui()
        self._refresh_list()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """Setup the dialog UI."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Info
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text=f"备份目录: {self.backup_manager.get_backup_dir()}").pack(side=tk.LEFT)

        # Treeview
        columns = ("filename", "date", "size")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("filename", text="文件名")
        self.tree.heading("date", text="备份时间")
        self.tree.heading("size", text="大小")

        self.tree.column("filename", width=250)
        self.tree.column("date", width=150, anchor="center")
        self.tree.column("size", width=80, anchor="e")

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="刷新", command=self._refresh_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="立即备份", command=self._create_backup).pack(side=tk.LEFT, padx=5)

        self.restore_btn = ttk.Button(btn_frame, text="恢复此备份", command=self._restore_selected)
        self.restore_btn.pack(side=tk.LEFT, padx=5)

        self.delete_btn = ttk.Button(btn_frame, text="删除", command=self._delete_selected)
        self.delete_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT, padx=5)

        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_buttons())
        self._update_buttons()

    def _refresh_list(self):
        """Refresh backup list."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        backups = self.backup_manager.list_backups()

        for path, mtime, size in backups:
            size_str = f"{size / 1024:.1f} KB"
            date_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
            self.tree.insert("", tk.END, values=(path.name, date_str, size_str), tags=(str(path),))

        self._update_buttons()

    def _update_buttons(self):
        """Update button states."""
        has_selection = bool(self.tree.selection())
        self.restore_btn.config(state=tk.NORMAL if has_selection else tk.DISABLED)
        self.delete_btn.config(state=tk.NORMAL if has_selection else tk.DISABLED)

    def _get_selected_path(self):
        """Get path of selected backup."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            return item["tags"][0] if item["tags"] else None
        return None

    def _create_backup(self):
        """Create a new backup."""
        path = self.backup_manager.perform_backup(force=True)
        if path:
            messagebox.showinfo("成功", f"已创建备份:\n{path}")
            self._refresh_list()
        else:
            messagebox.showerror("失败", "备份创建失败")

    def _restore_selected(self):
        """Restore selected backup."""
        path = self._get_selected_path()
        if not path:
            return

        if messagebox.askyesno("确认", "确定要恢复此备份吗？\n当前未保存的更改将丢失。"):
            if self.backup_manager.restore_backup(path):
                messagebox.showinfo("成功", "备份已恢复")
                if self.on_restore:
                    self.on_restore()
                self.destroy()
            else:
                messagebox.showerror("失败", "备份恢复失败")

    def _delete_selected(self):
        """Delete selected backup."""
        path = self._get_selected_path()
        if not path:
            return

        if messagebox.askyesno("确认", "确定要删除此备份吗？"):
            if self.backup_manager.delete_backup(path):
                self._refresh_list()
            else:
                messagebox.showerror("失败", "删除失败")
