import tkinter as tk
from tkinter import ttk, messagebox

from writer_app.core.commands import (
    AddFlatDraftEntryCommand,
    EditFlatDraftEntryCommand,
    DeleteFlatDraftEntryCommand,
    ConvertFlatDraftToOutlineCommand,
)


KIND_OPTIONS = [
    ("narrative", "平铺叙事"),
    ("twist_encounter", "转折-遭遇"),
    ("twist_chance", "转折-偶然事件"),
    ("twist_choice", "转折-抉择处"),
    ("foreshadow_pos", "正铺垫"),
    ("foreshadow_neg", "反铺垫"),
]

KIND_LABELS = {key: label for key, label in KIND_OPTIONS}


class FlatDraftEntryDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_kind=None, initial_text=""):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="类型:").grid(row=0, column=0, sticky=tk.W)
        self.kind_var = tk.StringVar(value=initial_kind or KIND_OPTIONS[0][1])
        self.kind_combo = ttk.Combobox(
            frame,
            textvariable=self.kind_var,
            values=[label for _, label in KIND_OPTIONS],
            state="readonly",
            width=18,
        )
        self.kind_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(frame, text="内容:").grid(row=1, column=0, sticky=tk.NW, pady=(10, 0))
        self.text = tk.Text(frame, width=50, height=8, wrap=tk.WORD)
        self.text.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(10, 0))
        self.text.insert("1.0", initial_text or "")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_confirm).pack(side=tk.RIGHT)

        frame.columnconfigure(1, weight=1)

        self.text.focus_set()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_confirm(self):
        label = self.kind_var.get().strip()
        text = self.text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请填写内容。", parent=self)
            return
        kind_key = None
        for key, value in KIND_OPTIONS:
            if value == label:
                kind_key = key
                break
        self.result = {"kind": kind_key or "narrative", "label": label, "text": text}
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


class FlatDraftView(tk.Canvas):
    def __init__(self, parent, project_manager, command_executor,
                 on_node_select=None, on_ai_suggest_branch=None,
                 on_generate_scene=None, on_set_tags=None,
                 on_jump_to_scene=None, **kwargs):
        super().__init__(parent, bg="#FFFFFF", highlightthickness=0, **kwargs)
        self.project_manager = project_manager
        self.command_executor = command_executor

        self._selected_uid = None
        self._tree_item_to_uid = {}
        self.current_theme_manager = None

        self._build_ui()
        self._bind_events()
        self.refresh()

    def _build_ui(self):
        self.container = ttk.Frame(self)
        self.window_id = self.create_window(0, 0, window=self.container, anchor="nw")

        header = ttk.Frame(self.container)
        header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(header, text="平铺叙事草稿").pack(side=tk.LEFT)
        ttk.Button(header, text="还原为大纲", command=self._convert_to_outline).pack(side=tk.RIGHT)

        self.tree_frame = ttk.Frame(self.container)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("type",)
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, selectmode="browse")
        self.tree.heading("#0", text="内容")
        self.tree.heading("type", text="类型")
        self.tree.column("#0", width=520, minwidth=240, stretch=True)
        self.tree.column("type", width=140, minwidth=120, stretch=False)

        y_scroll = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(self.tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        self.context_menu = tk.Menu(self, tearoff=0)
        self._build_context_menu()

        self.bind("<Configure>", self._on_resize)

    def _bind_events(self):
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Delete>", lambda _event: self.delete_selected_node())

    def _build_context_menu(self):
        add_menu = tk.Menu(self.context_menu, tearoff=0)
        for key, label in KIND_OPTIONS:
            add_menu.add_command(label=label, command=lambda k=key: self._add_entry(kind=k))
        self.context_menu.add_cascade(label="新增条目", menu=add_menu)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="编辑", command=self._edit_selected)
        self.context_menu.add_command(label="删除", command=self.delete_selected_node)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="还原为大纲", command=self._convert_to_outline)

    def _on_resize(self, event):
        self.itemconfigure(self.window_id, width=event.width, height=event.height)
        self.configure(scrollregion=self.bbox("all"))

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        self._selected_uid = selection[0] if selection else None

    def _on_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self._selected_uid = row_id
        else:
            self.tree.selection_remove(self.tree.selection())
            self._selected_uid = None
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _on_double_click(self, _event):
        if self._selected_uid:
            self._edit_selected()

    def _get_entries(self):
        return self.project_manager.get_flat_draft_entries()

    def _find_entry(self, uid):
        for entry in self._get_entries():
            if entry.get("uid") == uid:
                return entry
        return None

    def _add_entry(self, kind="narrative", insert_after_uid=None):
        dialog = FlatDraftEntryDialog(
            self.winfo_toplevel(),
            "新增条目",
            initial_kind=KIND_LABELS.get(kind, KIND_OPTIONS[0][1]),
        )
        self.wait_window(dialog)
        if not dialog.result:
            return

        entry = dialog.result
        insert_index = None
        if insert_after_uid:
            entries = self._get_entries()
            for idx, item in enumerate(entries):
                if item.get("uid") == insert_after_uid:
                    insert_index = idx + 1
                    break

        cmd = AddFlatDraftEntryCommand(self.project_manager, entry, insert_index=insert_index)
        if self.command_executor(cmd):
            self.refresh()

    def _edit_selected(self):
        if not self._selected_uid:
            messagebox.showinfo("提示", "请先选择条目。", parent=self.winfo_toplevel())
            return
        entry = self._find_entry(self._selected_uid)
        if not entry:
            return
        dialog = FlatDraftEntryDialog(
            self.winfo_toplevel(),
            "编辑条目",
            initial_kind=entry.get("label") or KIND_LABELS.get(entry.get("kind"), KIND_OPTIONS[0][1]),
            initial_text=entry.get("text", ""),
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        cmd = EditFlatDraftEntryCommand(self.project_manager, self._selected_uid, dialog.result)
        if self.command_executor(cmd):
            self.refresh()

    def _convert_to_outline(self):
        entries = self._get_entries()
        if not entries:
            messagebox.showinfo("提示", "当前没有可转换的条目。", parent=self.winfo_toplevel())
            return
        if not messagebox.askyesno("确认转换", "将条目追加为大纲节点？", parent=self.winfo_toplevel()):
            return
        cmd = ConvertFlatDraftToOutlineCommand(self.project_manager, entries)
        if self.command_executor(cmd):
            self.refresh()

    def add_child_to_selected(self):
        self._add_entry(insert_after_uid=self._selected_uid)

    def add_sibling_to_selected(self):
        self._add_entry(insert_after_uid=self._selected_uid)

    def delete_selected_node(self):
        if not self._selected_uid:
            return
        if not messagebox.askyesno("确认删除", "确定删除该条目？", parent=self.winfo_toplevel()):
            return
        cmd = DeleteFlatDraftEntryCommand(self.project_manager, self._selected_uid)
        if self.command_executor(cmd):
            self.refresh()

    def set_data(self, root_node):
        self.root_node = root_node

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._tree_item_to_uid.clear()
        entries = self._get_entries()
        updated = False
        for entry in entries:
            uid = entry.get("uid") or self.project_manager._gen_uid()
            if entry.get("uid") != uid:
                entry["uid"] = uid
                updated = True
            label = entry.get("label") or KIND_LABELS.get(entry.get("kind"), "平铺叙事")
            preview = self._build_preview(entry.get("text", ""))
            self.tree.insert("", tk.END, iid=uid, text=preview, values=(label,))
            self._tree_item_to_uid[uid] = uid
        if updated:
            self.project_manager.mark_modified("outline")
        self.configure(scrollregion=self.bbox("all"))

    def _build_preview(self, text, max_len=60):
        text = (text or "").strip()
        if not text:
            return "（空）"
        first_line = text.splitlines()[0].strip()
        if len(first_line) > max_len:
            return first_line[:max_len - 3] + "..."
        return first_line

    def set_scene_counts(self, counts):
        pass

    def expand_selected(self):
        pass

    def set_tag_filter(self, tags):
        pass

    def set_ai_mode_enabled(self, enabled: bool):
        pass

    def apply_theme(self, theme_manager):
        self.current_theme_manager = theme_manager
        style = ttk.Style()
        bg_primary = theme_manager.get_color("bg_primary")
        fg_primary = theme_manager.get_color("fg_primary")
        select_bg = theme_manager.get_color("editor_select_bg")
        style.configure(
            "Treeview",
            background=bg_primary,
            foreground=fg_primary,
            fieldbackground=bg_primary,
        )
        style.map("Treeview", background=[("selected", select_bg)])

    def destroy(self):
        if hasattr(self, "container"):
            self.container.destroy()
        super().destroy()
