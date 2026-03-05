import math
import random
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import uuid

from writer_app.core.commands import (
    AddEvidenceLinkCommand,
    AddEvidenceNodeCommand,
    DeleteEvidenceLinkCommand,
    DeleteEvidenceNodeCommand,
    EditEvidenceLinkCommand,
    EditEvidenceNodeCommand,
    UpdateEvidenceNodeLayoutCommand,
)
from writer_app.core.event_bus import get_event_bus, Events

class EvidenceNodeDialog(tk.Toplevel):
    def __init__(self, parent, node_data=None, scenes=None):
        super().__init__(parent)
        self.title("线索节点详情")
        self.geometry("400x380")
        self.result = None
        self.node_data = node_data or {"type": "clue", "name": "", "description": "", "scene_ref": None}
        self.scenes = scenes or []

        self.setup_ui()
        self.transient(parent)
        self.grab_set()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="名称:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.name_var = tk.StringVar(value=self.node_data.get("name", ""))
        ttk.Entry(main_frame, textvariable=self.name_var).pack(fill=tk.X, pady=(0, 10))

        ttk.Label(main_frame, text="类型:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.type_var = ttk.Combobox(main_frame, values=["clue", "character", "location", "event", "question"], state="readonly")
        self.type_var.set(self.node_data.get("type", "clue"))
        self.type_var.pack(fill=tk.X, pady=(0, 10))

        # 场景关联（用于逻辑校验）
        ttk.Label(main_frame, text="揭示场景 (逻辑校验用):", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        scene_options = ["(无)"] + [f"{i+1}. {s.get('name', '未命名')}" for i, s in enumerate(self.scenes)]
        self.scene_var = ttk.Combobox(main_frame, values=scene_options, state="readonly")

        # 设置当前值
        current_scene_ref = self.node_data.get("scene_ref")
        if current_scene_ref is not None and 0 <= current_scene_ref < len(self.scenes):
            self.scene_var.current(current_scene_ref + 1)  # +1 因为第一项是"(无)"
        else:
            self.scene_var.current(0)
        self.scene_var.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(main_frame, text="描述:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.desc_text = tk.Text(main_frame, height=4, font=("", 9))
        self.desc_text.insert("1.0", self.node_data.get("description", ""))
        self.desc_text.pack(fill=tk.X, expand=True)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="保存", command=self.on_save).pack(side=tk.RIGHT)

    def on_save(self):
        # 解析场景引用
        scene_ref = None
        scene_idx = self.scene_var.current()
        if scene_idx > 0:  # 0是"(无)"
            scene_ref = scene_idx - 1

        self.result = {
            "name": self.name_var.get().strip(),
            "type": self.type_var.get(),
            "description": self.desc_text.get("1.0", tk.END).strip(),
            "uid": self.node_data.get("uid"),  # Preserve UID
            "scene_ref": scene_ref
        }
        self.destroy()

class EvidenceLinkDialog(tk.Toplevel):
    def __init__(self, parent, link_data=None):
        super().__init__(parent)
        self.title("线索链接详情")
        self.geometry("300x150")
        self.result = None
        self.link_data = link_data or {"label": "", "type": "relates_to"}

        self.setup_ui()
        self.transient(parent)
        self.grab_set()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="标签:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.label_var = tk.StringVar(value=self.link_data.get("label", ""))
        ttk.Entry(main_frame, textvariable=self.label_var).pack(fill=tk.X, pady=(0, 10))

        ttk.Label(main_frame, text="类型:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.type_var = ttk.Combobox(main_frame, values=["relates_to", "suspects", "confirms", "contradicts", "caused_by"], state="readonly")
        self.type_var.set(self.link_data.get("type", "relates_to"))
        self.type_var.pack(fill=tk.X)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="保存", command=self.on_save).pack(side=tk.RIGHT)

    def on_save(self):
        self.result = {
            "label": self.label_var.get().strip(),
            "type": self.type_var.get(),
        }
        self.destroy()


from writer_app.core.analysis import AnalysisUtils
from writer_app.core.logic_validator import get_logic_validator
from writer_app.ui.dialogs import ValidationResultDialog
from writer_app.ui.components.empty_state_panel import EmptyStatePanel, EmptyStateConfig


class EvidencePropertiesPanel(ttk.LabelFrame):
    def __init__(self, parent, project_manager, command_executor, on_navigate_to_scene=None):
        super().__init__(parent, text="属性面板")
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.on_navigate_to_scene = on_navigate_to_scene

        self._selected_type = None
        self._selected_node_uid = None
        self._selected_link_index = None
        self._node_editable = False
        self._suspend_updates = False
        self._node_update_job = None
        self._link_update_job = None

        self._build_ui()

    def _build_ui(self):
        self.empty_label = ttk.Label(self, text="选择线索节点或连线以编辑", foreground="#777")
        self.empty_label.pack(anchor="center", pady=20)

        self.node_frame = ttk.Frame(self)
        ttk.Label(self.node_frame, text="节点属性", font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 8))

        node_form = ttk.Frame(self.node_frame)
        node_form.pack(fill=tk.X, padx=10)

        ttk.Label(node_form, text="名称:").grid(row=0, column=0, sticky="w", pady=2)
        self.node_name_var = tk.StringVar()
        self.node_name_entry = ttk.Entry(node_form, textvariable=self.node_name_var)
        self.node_name_entry.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(node_form, text="类型:").grid(row=1, column=0, sticky="w", pady=2)
        self.node_type_var = tk.StringVar()
        self.node_type_combo = ttk.Combobox(
            node_form,
            textvariable=self.node_type_var,
            values=["clue", "character", "location", "event", "question"],
            state="readonly"
        )
        self.node_type_combo.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(node_form, text="揭示场景:").grid(row=2, column=0, sticky="w", pady=2)
        self.node_scene_var = tk.StringVar()
        self.node_scene_combo = ttk.Combobox(node_form, textvariable=self.node_scene_var, state="readonly")
        self.node_scene_combo.grid(row=2, column=1, sticky="ew", pady=2)

        node_form.columnconfigure(1, weight=1)

        ttk.Label(self.node_frame, text="描述:").pack(anchor="w", padx=10, pady=(8, 2))
        self.node_desc_text = tk.Text(self.node_frame, height=6, font=("", 9))
        self.node_desc_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        self.node_note_var = tk.StringVar(value="")
        self.node_note_label = ttk.Label(self.node_frame, textvariable=self.node_note_var, foreground="#666")
        self.node_note_label.pack(anchor="w", padx=10, pady=(0, 6))

        node_btn_frame = ttk.Frame(self.node_frame)
        node_btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.node_jump_btn = ttk.Button(node_btn_frame, text="跳转到场景", command=self._jump_to_scene, state="disabled")
        self.node_jump_btn.pack(side=tk.LEFT)
        self.node_delete_btn = ttk.Button(node_btn_frame, text="删除节点", command=self._delete_node)
        self.node_delete_btn.pack(side=tk.RIGHT)

        self.link_frame = ttk.Frame(self)
        ttk.Label(self.link_frame, text="连线属性", font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 8))

        link_form = ttk.Frame(self.link_frame)
        link_form.pack(fill=tk.X, padx=10)

        ttk.Label(link_form, text="起点:").grid(row=0, column=0, sticky="w", pady=2)
        self.link_source_var = tk.StringVar()
        ttk.Label(link_form, textvariable=self.link_source_var, foreground="#555").grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(link_form, text="终点:").grid(row=1, column=0, sticky="w", pady=2)
        self.link_target_var = tk.StringVar()
        ttk.Label(link_form, textvariable=self.link_target_var, foreground="#555").grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(link_form, text="标签:").grid(row=2, column=0, sticky="w", pady=2)
        self.link_label_var = tk.StringVar()
        self.link_label_entry = ttk.Entry(link_form, textvariable=self.link_label_var)
        self.link_label_entry.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(link_form, text="类型:").grid(row=3, column=0, sticky="w", pady=2)
        self.link_type_var = tk.StringVar()
        self.link_type_combo = ttk.Combobox(
            link_form,
            textvariable=self.link_type_var,
            values=["relates_to", "suspects", "confirms", "contradicts", "caused_by"],
            state="readonly"
        )
        self.link_type_combo.grid(row=3, column=1, sticky="ew", pady=2)

        link_form.columnconfigure(1, weight=1)

        link_btn_frame = ttk.Frame(self.link_frame)
        link_btn_frame.pack(fill=tk.X, padx=10, pady=(10, 10))
        self.link_delete_btn = ttk.Button(link_btn_frame, text="删除连线", command=self._delete_link)
        self.link_delete_btn.pack(side=tk.RIGHT)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, foreground="#888").pack(anchor="w", padx=10, pady=(0, 8))

        self._bind_events()

    def _bind_events(self):
        self.node_name_var.trace_add("write", lambda *args: self._schedule_node_apply())
        self.node_name_entry.bind("<FocusOut>", self._apply_node_changes)
        self.node_name_entry.bind("<Return>", self._apply_node_changes)

        self.node_type_combo.bind("<<ComboboxSelected>>", self._apply_node_changes)
        self.node_scene_combo.bind("<<ComboboxSelected>>", self._apply_node_changes)
        self.node_desc_text.bind("<KeyRelease>", lambda event: self._schedule_node_apply())
        self.node_desc_text.bind("<FocusOut>", self._apply_node_changes)

        self.link_label_var.trace_add("write", lambda *args: self._schedule_link_apply())
        self.link_label_entry.bind("<FocusOut>", self._apply_link_changes)
        self.link_label_entry.bind("<Return>", self._apply_link_changes)
        self.link_type_combo.bind("<<ComboboxSelected>>", self._apply_link_changes)

    def set_selection(self, selection):
        self._cancel_pending_jobs()
        self._suspend_updates = True
        self._selected_type = None
        self._selected_node_uid = None
        self._selected_link_index = None

        if selection is None:
            self._show_empty()
            self._suspend_updates = False
            return

        sel_type = selection.get("type")
        focus = selection.get("focus", False)
        if sel_type == "node":
            self._show_node(selection.get("uid"), focus)
        elif sel_type == "link":
            self._show_link(selection.get("index"), focus)
        else:
            self._show_empty()

        self._suspend_updates = False

    def _show_empty(self):
        self._selected_type = None
        self._selected_node_uid = None
        self._selected_link_index = None
        self._node_editable = False
        self.node_frame.pack_forget()
        self.link_frame.pack_forget()
        self.empty_label.pack(anchor="center", pady=20)
        self.status_var.set("")

    def _show_node(self, node_uid, focus):
        node = self._get_node_by_uid(node_uid)
        self._selected_type = "node"
        self._selected_node_uid = node_uid
        self._selected_link_index = None
        self.empty_label.pack_forget()
        self.link_frame.pack_forget()
        self.node_frame.pack(fill=tk.BOTH, expand=True)

        self._refresh_scene_options()

        if not node:
            self._node_editable = False
            self.node_name_var.set("")
            self.node_type_var.set("")
            self.node_scene_var.set("(无)")
            self._set_desc_text("")
            self.node_note_var.set("角色节点不可在此编辑，请到角色管理中修改。")
            self._set_node_editable(False)
            self.node_jump_btn.configure(state="disabled")
            self.node_delete_btn.configure(state="disabled")
            return

        self._node_editable = node.get("type") != "character"
        self.node_name_var.set(node.get("name", ""))
        self.node_type_var.set(node.get("type", "clue"))

        scene_ref = node.get("scene_ref")
        if scene_ref is not None and 0 <= scene_ref < len(self._scene_options):
            self.node_scene_combo.current(scene_ref + 1)
        else:
            self.node_scene_combo.current(0)

        self._set_desc_text(node.get("description", ""))

        if self._node_editable:
            self.node_note_var.set("")
        else:
            self.node_note_var.set("角色节点不可在此编辑，请到角色管理中修改。")

        self._set_node_editable(self._node_editable)
        self.node_delete_btn.configure(state="normal" if self._node_editable else "disabled")
        self._update_jump_button(scene_ref)

        if focus and self._node_editable:
            self.node_name_entry.focus_set()

    def _show_link(self, link_index, focus):
        link = self._get_link_by_index(link_index)
        self._selected_type = "link"
        self._selected_node_uid = None
        self._selected_link_index = link_index
        self.empty_label.pack_forget()
        self.node_frame.pack_forget()
        self.link_frame.pack(fill=tk.BOTH, expand=True)

        if not link:
            self.link_source_var.set("")
            self.link_target_var.set("")
            self.link_label_var.set("")
            self.link_type_var.set("")
            return

        src_name = self._resolve_node_name(link.get("source"))
        tgt_name = self._resolve_node_name(link.get("target"))
        self.link_source_var.set(src_name)
        self.link_target_var.set(tgt_name)
        self.link_label_var.set(link.get("label", ""))
        self.link_type_var.set(link.get("type", "relates_to"))

        if focus:
            self.link_label_entry.focus_set()

    def _set_node_editable(self, editable):
        state = "normal" if editable else "disabled"
        combo_state = "readonly" if editable else "disabled"
        self.node_name_entry.configure(state=state)
        self.node_type_combo.configure(state=combo_state)
        self.node_scene_combo.configure(state=combo_state)
        self.node_desc_text.configure(state=state)

    def _set_desc_text(self, value):
        self.node_desc_text.configure(state="normal")
        self.node_desc_text.delete("1.0", tk.END)
        self.node_desc_text.insert("1.0", value or "")
        self.node_desc_text.configure(state="normal" if self._node_editable else "disabled")

    def _refresh_scene_options(self):
        scenes = self.project_manager.get_scenes()
        self._scene_options = scenes
        scene_options = ["(无)"] + [f"{i+1}. {s.get('name', '未命名')}" for i, s in enumerate(scenes)]
        self.node_scene_combo["values"] = scene_options

    def _update_jump_button(self, scene_ref):
        if self.on_navigate_to_scene and scene_ref is not None:
            self.node_jump_btn.configure(state="normal")
        else:
            self.node_jump_btn.configure(state="disabled")

    def _jump_to_scene(self):
        if not self.on_navigate_to_scene:
            return
        node = self._get_node_by_uid(self._selected_node_uid)
        if not node:
            return
        scene_ref = node.get("scene_ref")
        if scene_ref is not None:
            self.on_navigate_to_scene(scene_ref)

    def _delete_node(self):
        if not self._selected_node_uid:
            return
        if not messagebox.askyesno("确认", "确定删除此节点？"):
            return
        cmd = DeleteEvidenceNodeCommand(self.project_manager, self._selected_node_uid)
        self._execute_command(cmd)
        self.set_selection(None)

    def _delete_link(self):
        if self._selected_link_index is None:
            return
        if not messagebox.askyesno("确认", "确定删除此连线？"):
            return
        cmd = DeleteEvidenceLinkCommand(self.project_manager, self._selected_link_index)
        self._execute_command(cmd)
        self.set_selection(None)

    def _schedule_node_apply(self, delay_ms=500):
        if self._suspend_updates or not self._node_editable:
            return
        if self._node_update_job:
            self.after_cancel(self._node_update_job)
        self._node_update_job = self.after(delay_ms, self._apply_node_changes)

    def _schedule_link_apply(self, delay_ms=500):
        if self._suspend_updates:
            return
        if self._link_update_job:
            self.after_cancel(self._link_update_job)
        self._link_update_job = self.after(delay_ms, self._apply_link_changes)

    def _apply_node_changes(self, event=None):
        if self._suspend_updates or not self._node_editable:
            return
        node = self._get_node_by_uid(self._selected_node_uid)
        if not node:
            return
        scene_idx = self.node_scene_combo.current()
        scene_ref = scene_idx - 1 if scene_idx > 0 else None
        new_data = {
            "uid": node.get("uid"),
            "name": self.node_name_var.get().strip(),
            "type": self.node_type_var.get(),
            "description": self.node_desc_text.get("1.0", tk.END).strip(),
            "scene_ref": scene_ref
        }
        if node.get("is_placeholder"):
            new_data["is_placeholder"] = False
        if not self._node_has_changes(node, new_data):
            return
        cmd = EditEvidenceNodeCommand(self.project_manager, node.get("uid"), dict(node), new_data)
        self._execute_command(cmd)
        self._set_status("节点已更新")
        self._update_jump_button(scene_ref)

    def _apply_link_changes(self, event=None):
        if self._suspend_updates:
            return
        link = self._get_link_by_index(self._selected_link_index)
        if not link:
            return
        new_label = self.link_label_var.get().strip()
        new_type = self.link_type_var.get()
        if new_label == link.get("label", "") and new_type == link.get("type", ""):
            return
        cmd = EditEvidenceLinkCommand(
            self.project_manager,
            self._selected_link_index,
            {"label": new_label, "type": new_type}
        )
        self._execute_command(cmd)
        self._set_status("连线已更新")

    def _execute_command(self, cmd):
        if self.command_executor:
            self.command_executor(cmd)
        else:
            cmd.execute()

    def _get_node_by_uid(self, uid):
        if not uid:
            return None
        rels = self.project_manager.get_relationships()
        for node in rels.get("nodes", []):
            if node.get("uid") == uid:
                return node
        for char in self.project_manager.get_characters():
            char_uid = char.get("uid") or char.get("name")
            if char_uid == uid:
                return {
                    "uid": char_uid,
                    "name": char.get("name", ""),
                    "type": "character",
                    "description": char.get("description", ""),
                    "scene_ref": None
                }
        return None

    def _get_link_by_index(self, idx):
        if idx is None:
            return None
        rels = self.project_manager.get_relationships()
        links = rels.get("evidence_links", [])
        if 0 <= idx < len(links):
            return links[idx]
        return None

    def _node_has_changes(self, node, new_data):
        fields = ("name", "type", "description", "scene_ref")
        for field in fields:
            if node.get(field) != new_data.get(field):
                return True
        if node.get("is_placeholder") and not new_data.get("is_placeholder"):
            return True
        return False

    def _resolve_node_name(self, uid):
        if not uid:
            return ""
        for node in self.project_manager.get_relationships().get("nodes", []):
            if node.get("uid") == uid:
                return node.get("name", uid)
        for char in self.project_manager.get_characters():
            char_uid = char.get("uid") or char.get("name")
            if char_uid == uid:
                return char.get("name", uid)
        return uid

    def _set_status(self, text, duration_ms=2500):
        self.status_var.set(text)
        if duration_ms:
            self.after(duration_ms, lambda: self.status_var.set(""))

    def _cancel_pending_jobs(self):
        if self._node_update_job:
            self.after_cancel(self._node_update_job)
            self._node_update_job = None
        if self._link_update_job:
            self.after_cancel(self._link_update_job)
            self._link_update_job = None


class EvidenceBoardContainer(ttk.Frame):
    """证据板容器，包含工具栏和画布"""

    def __init__(self, parent, project_manager, command_executor, theme_manager, on_navigate_to_scene=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager
        self.on_navigate_to_scene = on_navigate_to_scene

        self._setup_ui()

    def _setup_ui(self):
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(paned)
        right_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=4)
        paned.add(right_frame, weight=1)

        # 工具栏
        toolbar = ttk.Frame(left_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="逻辑校验", command=self._run_logic_validation).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="添加线索", command=self._add_node_from_toolbar).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # 布局控制
        ttk.Button(toolbar, text="网格布局", command=lambda: self.canvas.auto_layout("grid")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="力导向布局", command=lambda: self.canvas.auto_layout("force")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="重置视图", command=self.canvas.reset_view).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Label(toolbar, text="提示: 滚轮缩放 | 中键平移 | 右键菜单").pack(side=tk.LEFT)

        # 画布
        self.canvas = EvidenceBoard(
            left_frame,
            self.project_manager,
            self.command_executor,
            self.theme_manager
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 属性面板
        self.properties_panel = EvidencePropertiesPanel(
            right_frame,
            self.project_manager,
            self.command_executor,
            on_navigate_to_scene=self.on_navigate_to_scene
        )
        self.properties_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.set_selection_callback(self.properties_panel.set_selection)

        # Empty state panel
        config = EmptyStateConfig.EVIDENCE
        self._empty_state = EmptyStatePanel(
            left_frame,
            self.theme_manager,
            icon=config["icon"],
            title=config["title"],
            description=config["description"],
            action_text=config["action_text"],
            action_callback=self._add_node_from_toolbar
        )
        self._empty_state_visible = False

    def _show_empty_state(self, show: bool):
        """Show or hide the empty state panel."""
        if show and not self._empty_state_visible:
            self.canvas.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True)
            self._empty_state_visible = True
        elif not show and self._empty_state_visible:
            self._empty_state.pack_forget()
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self._empty_state_visible = False

    def _run_logic_validation(self):
        """运行逻辑校验"""
        validator = get_logic_validator(self.project_manager)
        report = validator.run_full_validation()

        ValidationResultDialog(
            self.winfo_toplevel(),
            report,
            on_navigate_to_scene=self.on_navigate_to_scene
        )

    def _add_node_from_toolbar(self):
        """从工具栏添加节点"""
        # 在画布中心添加节点
        canvas_width = self.canvas.winfo_width() or 800
        canvas_height = self.canvas.winfo_height() or 600
        x = canvas_width // 2 + random.randint(-100, 100)
        y = canvas_height // 2 + random.randint(-100, 100)
        self.canvas.add_node_dialog(x, y)

    def refresh(self):
        """刷新证据板"""
        # Check for empty state
        nodes = self.project_manager.get_evidence_nodes()
        if not nodes:
            self._show_empty_state(True)
            return
        self._show_empty_state(False)
        self.canvas.refresh()

    def apply_theme(self):
        self.canvas.apply_theme()


class EvidenceBoard(tk.Canvas):
    def __init__(self, parent, project_manager, command_executor, theme_manager, on_selection_change=None):
        super().__init__(parent, bg="#333333", highlightthickness=0)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager
        self.on_selection_change = on_selection_change

        self.nodes = {}  # uid -> {x,y, name, type, description}
        self.node_widgets = {}  # uid -> canvas_item_ids
        self.link_widgets = {}  # (src_uid, tgt_uid) -> canvas_item_ids
        self.clue_status_map = {}  # uid -> status
        self.selected_node_uid = None
        self.selected_link_index = None
        self._selection_focus = False
        self._refresh_job = None
        self._refresh_delay_ms = 60
        self._pending_full_refresh = False
        self._force_full_refresh = False
        self._pending_node_uids = set()
        self._pending_link_refresh = False
        self._pending_clue_recalc = False
        self._link_count = 0
        self._layout_running = False
        self._layout_status_id = None
        self._layout_token = 0
        self._seeding_placeholders = False
        self._script_text_cache = ""
        self._script_text_dirty = True

        self.drag_data = {"node_uid": None, "start_x": 0, "start_y": 0, "dragging": False}
        self.linking_data = {"active": False, "source_uid": None, "line_id": None}

        # 视图控制
        self._scale = 1.0
        self._pan_offset = [0, 0]
        self._last_size = (0, 0)
        self._resize_pending = False

        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag_motion)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<Double-1>", self.on_double_click)
        self.bind("<Motion>", self.on_hover)
        self.bind("<Leave>", self._hide_tooltip)

        # 响应式布局
        self.bind("<Configure>", self._on_configure)

        # 滚轮缩放
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self._on_mousewheel_linux(e, 1))
        self.bind("<Button-5>", lambda e: self._on_mousewheel_linux(e, -1))

        # 中键平移
        self.bind("<Button-2>", self._start_pan)
        self.bind("<B2-Motion>", self._do_pan)

        self.theme_manager.add_listener(self.apply_theme)
        self.apply_theme()

        # 订阅事件总线
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅相关事件"""
        bus = get_event_bus()
        bus.subscribe(Events.EVIDENCE_UPDATED, self._on_evidence_changed)
        bus.subscribe(Events.EVIDENCE_NODE_ADDED, self._on_evidence_changed)
        bus.subscribe(Events.EVIDENCE_NODE_DELETED, self._on_evidence_changed)
        bus.subscribe(Events.EVIDENCE_LINK_ADDED, self._on_evidence_changed)
        bus.subscribe(Events.CLUE_ADDED, self._on_clue_changed)
        bus.subscribe(Events.CLUE_UPDATED, self._on_clue_changed)
        bus.subscribe(Events.CLUE_DELETED, self._on_clue_changed)
        bus.subscribe(Events.SCENE_UPDATED, self._on_scene_changed)
        bus.subscribe(Events.SCENE_ADDED, self._on_scene_changed)
        bus.subscribe(Events.SCENE_DELETED, self._on_scene_changed)
        bus.subscribe(Events.CHARACTER_ADDED, self._on_character_changed)
        bus.subscribe(Events.CHARACTER_UPDATED, self._on_character_changed)
        bus.subscribe(Events.CHARACTER_DELETED, self._on_character_changed)
        bus.subscribe(Events.PROJECT_LOADED, self._on_project_loaded)

    def set_selection_callback(self, callback):
        self.on_selection_change = callback

    def _notify_selection(self):
        if not self.on_selection_change:
            return
        selection = None
        if self.selected_node_uid:
            selection = {"type": "node", "uid": self.selected_node_uid, "focus": self._selection_focus}
        elif self.selected_link_index is not None:
            selection = {"type": "link", "index": self.selected_link_index, "focus": self._selection_focus}
        self._selection_focus = False
        self.on_selection_change(selection)

    def _set_selection(self, node_uid=None, link_index=None, focus=False):
        if node_uid == self.selected_node_uid and link_index == self.selected_link_index:
            if focus:
                self._selection_focus = True
                self._notify_selection()
            return

        if self.selected_node_uid:
            self._apply_node_selection(self.selected_node_uid, False)
        if self.selected_link_index is not None:
            self._apply_link_selection(self.selected_link_index, False)

        self.selected_node_uid = node_uid
        self.selected_link_index = link_index
        self._selection_focus = focus

        if self.selected_node_uid:
            self._apply_node_selection(self.selected_node_uid, True)
        if self.selected_link_index is not None:
            self._apply_link_selection(self.selected_link_index, True)

        self._notify_selection()

    def _clear_selection(self):
        self._set_selection(None, None)

    def _apply_selection_styles(self):
        if self.selected_node_uid:
            self._apply_node_selection(self.selected_node_uid, True)
        if self.selected_link_index is not None:
            self._apply_link_selection(self.selected_link_index, True)

    def _sync_selection(self, rels=None):
        if self.selected_node_uid and self.selected_node_uid not in self.nodes:
            self._clear_selection()
            return
        if self.selected_link_index is not None:
            rels = rels or self.project_manager.get_relationships()
            links = rels.get("evidence_links", [])
            if not (0 <= self.selected_link_index < len(links)):
                self._clear_selection()
                return
        self._apply_selection_styles()

    def _apply_node_selection(self, uid, selected):
        item_ids = self.node_widgets.get(uid)
        node_data = self.nodes.get(uid)
        if not item_ids or len(item_ids) < 2 or not node_data:
            return
        rect_id = item_ids[1]
        outline_color, dash_style = self._get_node_outline(node_data)
        if selected:
            outline_color = self.theme_manager.get_color("accent")
            width = 3
        else:
            width = 2
        self.itemconfigure(rect_id, outline=outline_color, width=width, dash=dash_style)

    def _apply_link_selection(self, link_index, selected):
        item_ids = self.link_widgets.get(link_index)
        if not item_ids or len(item_ids) < 2:
            return
        line_id, text_id = item_ids
        width = 3 if selected else 2
        font = ("Arial", 8, "bold") if selected else ("Arial", 8, "italic")
        self.itemconfigure(line_id, width=width)
        self.itemconfigure(text_id, font=font)

    def _on_evidence_changed(self, event_type, **kwargs):
        """证据变更时刷新"""
        if self._seeding_placeholders:
            return
        node_uid = kwargs.get("node_uid")
        link_index = kwargs.get("link_index")
        if event_type == Events.EVIDENCE_NODE_DELETED and node_uid:
            self._remove_node(node_uid)
            self._schedule_refresh(refresh_links=True)
            return
        if node_uid:
            self._schedule_refresh(node_uids=[node_uid], refresh_links=True)
            return
        if link_index is not None:
            self._schedule_refresh(refresh_links=True)
            return
        self._schedule_refresh(full=True)

    def _on_clue_changed(self, event_type, **kwargs):
        """线索变更时刷新"""
        self._script_text_dirty = True
        self._schedule_refresh(recalc_clues=True)

    def _on_scene_changed(self, event_type, **kwargs):
        """场景内容变化时，仅更新线索状态。"""
        self._script_text_dirty = True
        self._schedule_refresh(recalc_clues=True)

    def _on_character_changed(self, event_type, **kwargs):
        """角色变化影响证据板节点，需要全量刷新。"""
        self._schedule_refresh(full=True)

    def _on_project_loaded(self, event_type, **kwargs):
        """项目加载时刷新"""
        self._script_text_dirty = True
        self._schedule_refresh(full=True)

    def _on_configure(self, event):
        """窗口大小改变时的响应式布局调整"""
        new_size = (event.width, event.height)
        if new_size == self._last_size:
            return

        # 防止频繁刷新
        if self._resize_pending:
            return

        old_width, old_height = self._last_size
        self._last_size = new_size

        # 首次配置时不调整
        if old_width == 0 or old_height == 0:
            return

        # 标记正在调整
        self._resize_pending = True
        self.after(100, self._do_resize_adjustment)

    def _do_resize_adjustment(self):
        """延迟执行的窗口调整"""
        self._resize_pending = False
        # 简单地重新绘制以适应新尺寸
        self._schedule_refresh(full=True, force=True)

    def _on_mousewheel(self, event):
        """鼠标滚轮缩放"""
        # Windows
        if event.delta > 0:
            self._zoom(1.1, event.x, event.y)
        elif event.delta < 0:
            self._zoom(0.9, event.x, event.y)

    def _on_mousewheel_linux(self, event, direction):
        """Linux鼠标滚轮"""
        if direction > 0:
            self._zoom(1.1, event.x, event.y)
        else:
            self._zoom(0.9, event.x, event.y)

    def _zoom(self, factor, x, y):
        """以指定点为中心缩放"""
        new_scale = self._scale * factor
        # 限制缩放范围
        if new_scale < 0.3 or new_scale > 3.0:
            return

        self._scale = new_scale
        self.scale("all", x, y, factor, factor)
        self._pan_offset[0] *= factor
        self._pan_offset[1] *= factor

    def _start_pan(self, event):
        """开始平移"""
        self._pan_start = (event.x, event.y)

    def _do_pan(self, event):
        """执行平移"""
        if hasattr(self, '_pan_start'):
            dx = event.x - self._pan_start[0]
            dy = event.y - self._pan_start[1]
            self.move("all", dx, dy)
            self._pan_offset[0] += dx
            self._pan_offset[1] += dy
            self._pan_start = (event.x, event.y)

    def auto_layout(self, layout_type="grid"):
        """
        自动排列所有节点

        Args:
            layout_type: "grid" 网格布局, "force" 力导向布局
        """
        if not self.nodes:
            self._full_refresh()
            if not self.nodes:
                return

        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600

        # 计算边距
        margin = 80
        usable_width = canvas_width - 2 * margin
        usable_height = canvas_height - 2 * margin

        node_uids = list(self.nodes.keys())
        count = len(node_uids)

        if layout_type == "grid":
            # 网格布局
            cols = max(1, int(math.sqrt(count * usable_width / usable_height)))
            rows = math.ceil(count / cols)

            cell_width = usable_width / cols
            cell_height = usable_height / max(1, rows)

            new_layout = {}
            for i, uid in enumerate(node_uids):
                col = i % cols
                row = i // cols
                x = margin + cell_width * (col + 0.5)
                y = margin + cell_height * (row + 0.5)
                new_layout[uid] = [x, y]

            rels, layout = self._get_relationship_layout()
            layout.update(new_layout)
            rels["evidence_layout"] = layout
            self.project_manager.mark_modified("evidence")
            self._schedule_refresh(node_uids=list(new_layout.keys()), refresh_links=True)
            return

        if layout_type == "force":
            self._start_force_layout(node_uids, usable_width, usable_height, margin)
            return

        return

    def _set_layout_status(self, text):
        if text:
            if self._layout_status_id:
                self.itemconfigure(self._layout_status_id, text=text)
            else:
                self._layout_status_id = self.create_text(
                    20, 20,
                    text=text,
                    anchor="nw",
                    fill="#CCCCCC",
                    font=("Arial", 10, "bold"),
                    tags="layout_status"
                )
                self.tag_raise(self._layout_status_id)
        elif self._layout_status_id:
            self.delete(self._layout_status_id)
            self._layout_status_id = None

    def _start_force_layout(self, node_uids, width, height, margin, iterations=50):
        self._layout_token += 1
        token = self._layout_token
        self._layout_running = True
        self._set_layout_status("正在计算布局...")

        rels, layout = self._get_relationship_layout()
        positions = {}
        for uid in node_uids:
            if uid in layout:
                positions[uid] = list(layout[uid])
            else:
                positions[uid] = [
                    margin + random.random() * width,
                    margin + random.random() * height
                ]

        self._force_layout_state = {
            "token": token,
            "node_uids": node_uids,
            "positions": positions,
            "links": rels.get("evidence_links", []),
            "width": width,
            "height": height,
            "margin": margin,
            "iterations": iterations,
            "current_iter": 0
        }
        self._run_force_layout_step(token)

    def _run_force_layout_step(self, token):
        state = getattr(self, "_force_layout_state", None)
        if not state or token != state.get("token"):
            return

        steps_per_tick = 4
        for _ in range(steps_per_tick):
            self._apply_force_iteration(
                state["node_uids"],
                state["positions"],
                state["links"],
                state["width"],
                state["height"],
                state["margin"]
            )
            state["current_iter"] += 1
            if state["current_iter"] >= state["iterations"]:
                break

        for uid, pos in state["positions"].items():
            node_data = self.nodes.get(uid)
            if node_data:
                self._draw_or_update_node(pos[0], pos[1], node_data)

        rels, layout = self._get_relationship_layout()
        self._refresh_links(layout, rels, positions_override=state["positions"], force_rebuild=False)

        if state["current_iter"] >= state["iterations"]:
            self._finish_force_layout(token)
            return

        self.after(16, lambda: self._run_force_layout_step(token))

    def _finish_force_layout(self, token):
        state = getattr(self, "_force_layout_state", None)
        if not state or token != state.get("token"):
            return

        self._layout_running = False
        self._set_layout_status("")

        rels, layout = self._get_relationship_layout()
        layout.update(state["positions"])
        rels["evidence_layout"] = layout
        self.project_manager.mark_modified("evidence")
        self._schedule_refresh(node_uids=list(state["positions"].keys()), refresh_links=True)

        self._force_layout_state = None

    def _apply_force_iteration(self, node_uids, positions, links, width, height, margin):
        forces = {uid: [0.0, 0.0] for uid in node_uids}

        for i, uid1 in enumerate(node_uids):
            for uid2 in node_uids[i+1:]:
                dx = positions[uid1][0] - positions[uid2][0]
                dy = positions[uid1][1] - positions[uid2][1]
                dist = max(1, math.sqrt(dx * dx + dy * dy))

                repulsion = 10000 / (dist * dist)
                fx = repulsion * dx / dist
                fy = repulsion * dy / dist

                forces[uid1][0] += fx
                forces[uid1][1] += fy
                forces[uid2][0] -= fx
                forces[uid2][1] -= fy

        for link in links:
            src = link.get("source")
            tgt = link.get("target")
            if src in positions and tgt in positions:
                dx = positions[tgt][0] - positions[src][0]
                dy = positions[tgt][1] - positions[src][1]
                dist = max(1, math.sqrt(dx * dx + dy * dy))

                attraction = dist * 0.01
                fx = attraction * dx / dist
                fy = attraction * dy / dist

                forces[src][0] += fx
                forces[src][1] += fy
                forces[tgt][0] -= fx
                forces[tgt][1] -= fy

        for uid in node_uids:
            positions[uid][0] += forces[uid][0] * 0.1
            positions[uid][1] += forces[uid][1] * 0.1

            positions[uid][0] = max(margin, min(margin + width, positions[uid][0]))
            positions[uid][1] = max(margin, min(margin + height, positions[uid][1]))

    def reset_view(self):
        """重置视图（缩放和平移）"""
        # 重置缩放
        if self._scale != 1.0:
            factor = 1.0 / self._scale
            self.scale("all", 0, 0, factor, factor)
            self._scale = 1.0
        if self._pan_offset != [0, 0]:
            self.move("all", -self._pan_offset[0], -self._pan_offset[1])
            self._pan_offset = [0, 0]

    def apply_theme(self):
        bg = self.theme_manager.get_color("canvas_bg")
        self.configure(bg=bg)
        self._schedule_refresh(full=True, force=True)

    def refresh(self):
        if self._pending_node_uids or self._pending_link_refresh or self._pending_clue_recalc:
            return
        self._schedule_refresh(full=True)

    def _schedule_refresh(self, full=False, node_uids=None, refresh_links=False, recalc_clues=False, force=False):
        if full:
            self._pending_full_refresh = True
            if force:
                self._force_full_refresh = True
        if node_uids:
            self._pending_node_uids.update(node_uids)
        if refresh_links:
            self._pending_link_refresh = True
        if recalc_clues:
            self._pending_clue_recalc = True

        if self._refresh_job:
            return
        self._refresh_job = self.after(self._refresh_delay_ms, self._apply_pending_refresh)

    def _apply_pending_refresh(self):
        self._refresh_job = None

        if self._pending_full_refresh and not self._force_full_refresh:
            if self._pending_node_uids or self._pending_link_refresh or self._pending_clue_recalc:
                self._pending_full_refresh = False

        if self._pending_full_refresh:
            self._pending_full_refresh = False
            self._force_full_refresh = False
            self._pending_node_uids.clear()
            self._pending_link_refresh = False
            self._pending_clue_recalc = False
            self._full_refresh()
            return

        rels, layout = self._get_relationship_layout()
        changed_node_uids = set(self._pending_node_uids)
        self._pending_node_uids.clear()

        if self._pending_clue_recalc:
            self._pending_clue_recalc = False
            self._rebuild_clue_status()

        for uid in changed_node_uids:
            self._update_node_from_model(uid, rels, layout)

        if self._pending_link_refresh:
            self._pending_link_refresh = False
            self._refresh_links(layout, rels, node_uids=changed_node_uids)

        self._sync_selection(rels)

    def _full_refresh(self):
        self.delete("all")
        self.nodes.clear()
        self.node_widgets.clear()
        self.link_widgets.clear()
        self.clue_status_map.clear()
        self._layout_status_id = None
        
        # Analyze script for clue usage
        self._ensure_suspense_placeholders()
        all_script_text = self._get_script_text()
        rels, layout = self._get_relationship_layout()
        
        # Merge characters from script into nodes (as read-only for now)
        for char in self.project_manager.get_characters():
            char_uid = char.get("uid") or char["name"] # Fallback if no UID
            if char_uid not in layout: # Auto-layout if new
                layout[char_uid] = [random.randint(100, 700), random.randint(100, 500)]
            self.nodes[char_uid] = {"uid": char_uid, "name": char["name"], "type": "character", "description": char.get("description", "")}
        
        # Add custom evidence nodes
        for node in rels.get("nodes", []):
            if "uid" not in node: node["uid"] = str(uuid.uuid4()) # Ensure UID
            if node["uid"] not in layout:
                layout[node["uid"]] = [random.randint(100, 700), random.randint(100, 500)]
            self.nodes[node["uid"]] = node
            
            # Check clue status
            if node.get("type") == "clue":
                status = AnalysisUtils.check_clue_status(node.get("name"), all_script_text)
                self.clue_status_map[node["uid"]] = status
            
        # Draw links first
        for i, link in enumerate(rels.get("evidence_links", [])):
            src_uid = link["source"]
            tgt_uid = link["target"]
            if src_uid in self.nodes and tgt_uid in self.nodes:
                self._draw_link(src_uid, tgt_uid, link.get("label", ""), link.get("type", "relates_to"), layout, i)

        # Draw nodes
        for uid, node in self.nodes.items():
            if uid in layout:
                x, y = layout[uid]
                self._draw_node(x, y, node)

        rels["evidence_layout"] = layout # Save new layout
        self._link_count = len(rels.get("evidence_links", []))

        if self._scale != 1.0:
            self.scale("all", 0, 0, self._scale, self._scale)
        if self._pan_offset != [0, 0]:
            self.move("all", self._pan_offset[0], self._pan_offset[1])

        self._sync_selection(rels)

    def _get_relationship_layout(self):
        rels = self.project_manager.get_relationships()
        layout = rels.get("evidence_layout", {})
        if not layout and rels.get("layout"):
            layout = dict(rels.get("layout", {}))
            rels["evidence_layout"] = layout
        return rels, layout

    def _get_script_text(self):
        if self._script_text_dirty:
            scenes = self.project_manager.get_scenes()
            self._script_text_cache = "\n".join([s.get("content", "") for s in scenes])
            self._script_text_dirty = False
        return self._script_text_cache

    def _rebuild_clue_status(self):
        self.clue_status_map.clear()
        all_script_text = self._get_script_text()
        for uid, node in self.nodes.items():
            if node.get("type") == "clue":
                status = AnalysisUtils.check_clue_status(node.get("name"), all_script_text)
                self.clue_status_map[uid] = status
                self._update_pin_color(uid, node)

    def _ensure_suspense_placeholders(self):
        if self._seeding_placeholders:
            return
        if self.project_manager.get_project_type() != "Suspense":
            return
        meta = self.project_manager.project_data.setdefault("meta", {})
        if meta.get("evidence_seeded"):
            return

        rels = self.project_manager.get_relationships()
        if rels.get("nodes") or rels.get("evidence_links"):
            meta["evidence_seeded"] = True
            return
        if self.project_manager.get_scenes() or self.project_manager.get_characters():
            meta["evidence_seeded"] = True
            return

        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600
        cx = canvas_width // 2
        cy = canvas_height // 2
        offset_x = min(220, canvas_width // 4)
        offset_y = min(160, canvas_height // 4)

        placeholders = [
            {"name": "死者", "type": "question", "description": "点击替换", "scene_ref": None, "is_placeholder": True},
            {"name": "现场", "type": "question", "description": "点击替换", "scene_ref": None, "is_placeholder": True},
            {"name": "第一发现人", "type": "question", "description": "点击替换", "scene_ref": None, "is_placeholder": True},
        ]
        positions = [
            [cx - offset_x, cy - offset_y],
            [cx + offset_x, cy - offset_y],
            [cx, cy + offset_y],
        ]

        self._seeding_placeholders = True
        for node, pos in zip(placeholders, positions):
            node["uid"] = str(uuid.uuid4())
            cmd = AddEvidenceNodeCommand(self.project_manager, node, pos)
            if self.command_executor:
                self.command_executor(cmd)
            else:
                cmd.execute()
        meta["evidence_seeded"] = True
        self._seeding_placeholders = False

    def _update_node_from_model(self, uid, rels, layout):
        node_data = None
        for char in self.project_manager.get_characters():
            char_uid = char.get("uid") or char.get("name")
            if char_uid == uid:
                node_data = {
                    "uid": char_uid,
                    "name": char.get("name", ""),
                    "type": "character",
                    "description": char.get("description", "")
                }
                break

        if node_data is None:
            for node in rels.get("nodes", []):
                if node.get("uid") == uid:
                    node_data = node
                    break

        if not node_data:
            return

        if uid not in layout:
            layout[uid] = [random.randint(100, 700), random.randint(100, 500)]
        self.nodes[uid] = node_data

        if node_data.get("type") == "clue":
            status = AnalysisUtils.check_clue_status(node_data.get("name"), self._get_script_text())
            self.clue_status_map[uid] = status
        else:
            self.clue_status_map.pop(uid, None)

        x, y = layout[uid]
        self._draw_or_update_node(x, y, node_data)

    def _draw_or_update_node(self, x, y, node_data):
        uid = node_data["uid"]
        if uid not in self.node_widgets:
            self._draw_node(x, y, node_data)
            return
        self._update_node_geometry(x, y, node_data)

    def _update_node_geometry(self, x, y, node_data):
        uid = node_data["uid"]
        item_ids = self.node_widgets.get(uid)
        if not item_ids or len(item_ids) < 5:
            self._draw_node(x, y, node_data)
            return

        shadow_id, rect_id, pin_id, text_id, type_id = item_ids[:5]
        w, h = 120, 70

        self.coords(shadow_id, x - w / 2 + 4, y - h / 2 + 4, x + w / 2 + 4, y + h / 2 + 4)
        self.coords(rect_id, x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        self.coords(pin_id, x - 5, y - h / 2 - 5, x + 5, y - h / 2 + 5)
        self.coords(text_id, x, y - 10)
        self.coords(type_id, x, y + 20)

        bg_card = self.theme_manager.get_color("bg_secondary")
        fg_text = self.theme_manager.get_color("fg_primary")
        ntype = node_data.get("type", "clue")
        is_placeholder = bool(node_data.get("is_placeholder"))
        name_font = ("Arial", 10, "italic") if is_placeholder else ("Arial", 10, "bold")
        type_font = ("Arial", 7, "italic") if is_placeholder else ("Arial", 7)
        type_label = "点击替换" if is_placeholder else ntype.upper()
        outline_color, dash_style = self._get_node_outline(node_data)
        if uid == self.selected_node_uid:
            outline_color = self.theme_manager.get_color("accent")
            width = 3
        else:
            width = 2

        self.itemconfigure(rect_id, fill=bg_card, outline=outline_color, width=width, dash=dash_style)
        self.itemconfigure(text_id, text=node_data.get("name", ""), font=name_font, fill=fg_text)
        self.itemconfigure(type_id, text=type_label, font=type_font, fill=outline_color)
        self._update_pin_color(uid, node_data)
        self.tag_raise(f"node_{uid}")

    def _update_pin_color(self, uid, node_data):
        item_ids = self.node_widgets.get(uid)
        if not item_ids or len(item_ids) < 3:
            return
        pin_id = item_ids[2]
        self.itemconfigure(pin_id, fill=self._get_pin_color(uid, node_data))

    def _remove_node(self, uid):
        for item_id in self.node_widgets.get(uid, []):
            self.delete(item_id)
        self.node_widgets.pop(uid, None)
        self.nodes.pop(uid, None)
        self.clue_status_map.pop(uid, None)
        if uid == self.selected_node_uid:
            self._clear_selection()

    def _refresh_links(self, layout, rels, node_uids=None, positions_override=None, force_rebuild=False):
        links = rels.get("evidence_links", [])
        if not links:
            for ids in self.link_widgets.values():
                for item_id in ids:
                    self.delete(item_id)
            self.link_widgets.clear()
            self._link_count = 0
            return

        if force_rebuild or self._link_count != len(links) or not self.link_widgets:
            link_layout = positions_override or layout
            for ids in self.link_widgets.values():
                for item_id in ids:
                    self.delete(item_id)
            self.link_widgets.clear()
            for i, link in enumerate(links):
                src_uid = link.get("source")
                tgt_uid = link.get("target")
                if src_uid in link_layout and tgt_uid in link_layout:
                    self._draw_link(src_uid, tgt_uid, link.get("label", ""), link.get("type", "relates_to"), link_layout, i)
            self._link_count = len(links)
            return

        node_uids = set(node_uids or [])
        for i, link in enumerate(links):
            if node_uids and link.get("source") not in node_uids and link.get("target") not in node_uids:
                continue
            self._update_link_widget(i, link, layout, positions_override=positions_override)

    def _update_link_widget(self, link_index, link, layout, positions_override=None, use_canvas=False):
        src_uid = link.get("source")
        tgt_uid = link.get("target")

        if use_canvas:
            src_pos = self._get_node_center_from_canvas(src_uid)
            tgt_pos = self._get_node_center_from_canvas(tgt_uid)
        elif positions_override is not None:
            src_pos = positions_override.get(src_uid)
            tgt_pos = positions_override.get(tgt_uid)
        else:
            src_pos = layout.get(src_uid)
            tgt_pos = layout.get(tgt_uid)

        if not src_pos or not tgt_pos:
            return

        sx, sy, tx, ty = self._calculate_link_endpoints(src_pos, tgt_pos)
        color = self._get_link_color(link.get("type", "relates_to"))
        label = link.get("label", "")

        if link_index not in self.link_widgets:
            link_layout = positions_override or layout
            self._draw_link(src_uid, tgt_uid, label, link.get("type", "relates_to"), link_layout, link_index)
            return

        line_id, text_id = self.link_widgets[link_index]
        self.coords(line_id, sx, sy, tx, ty)
        self.coords(text_id, (sx + tx) / 2, (sy + ty) / 2 - 10)
        selected = link_index == self.selected_link_index
        line_width = 3 if selected else 2
        text_font = ("Arial", 8, "bold") if selected else ("Arial", 8, "italic")
        self.itemconfigure(line_id, fill=color, width=line_width)
        self.itemconfigure(text_id, text=label, fill=color, font=text_font)

    def _calculate_link_endpoints(self, src_pos, tgt_pos):
        x1, y1 = src_pos
        x2, y2 = tgt_pos
        angle = math.atan2(y2 - y1, x2 - x1)
        r = 60
        sx = x1 + r * math.cos(angle)
        sy = y1 + r * math.sin(angle)
        tx = x2 - r * math.cos(angle)
        ty = y2 - r * math.sin(angle)
        return sx, sy, tx, ty

    def _update_links_for_node(self, node_uid, use_canvas=False, positions_override=None):
        rels, layout = self._get_relationship_layout()
        links = rels.get("evidence_links", [])
        for i, link in enumerate(links):
            if link.get("source") == node_uid or link.get("target") == node_uid:
                self._update_link_widget(i, link, layout, positions_override=positions_override, use_canvas=use_canvas)

    def _get_node_center_from_canvas(self, uid):
        item_ids = self.node_widgets.get(uid)
        if not item_ids or len(item_ids) < 2:
            return None
        rect_id = item_ids[1]
        x1, y1, x2, y2 = self.coords(rect_id)
        return [(x1 + x2) / 2, (y1 + y2) / 2]

    def _get_pin_color(self, uid, node_data):
        if node_data.get("type") == "clue":
            status = self.clue_status_map.get(uid, "unused")
            if status == "resolved":
                return "#4CAF50"
            if status == "mentioned":
                return "#FFC107"
            return "#F44336"
        return "gray"

    def _get_link_color(self, link_type):
        link_color_map = {
            "relates_to": "gray",
            "suspects": "orange",
            "confirms": "green",
            "contradicts": "red",
            "caused_by": "purple"
        }
        return link_color_map.get(link_type, "gray")

    def _get_node_outline(self, node_data):
        fg_text = self.theme_manager.get_color("fg_primary")
        color_map = {
            "character": self.theme_manager.get_color("accent"),
            "clue": self.theme_manager.get_color("highlight"),
            "location": "#5CB85C",
            "event": "#F0AD4E",
            "question": "#D9534F",
        }
        ntype = node_data.get("type", "clue")
        outline_color = color_map.get(ntype, fg_text)
        dash_style = (4, 2) if node_data.get("is_placeholder") else ()
        return outline_color, dash_style

    def _draw_node(self, x, y, node_data):
        uid = node_data["uid"]
        name = node_data.get("name", "")
        ntype = node_data.get("type", "clue")
        
        # Card style adapted to theme
        bg_card = self.theme_manager.get_color("bg_secondary")
        fg_text = self.theme_manager.get_color("fg_primary")
        
        is_placeholder = bool(node_data.get("is_placeholder"))
        name_font = ("Arial", 10, "italic") if is_placeholder else ("Arial", 10, "bold")
        type_font = ("Arial", 7, "italic") if is_placeholder else ("Arial", 7)
        type_label = "点击替换" if is_placeholder else ntype.upper()
        outline_color, dash_style = self._get_node_outline(node_data)
        if uid == self.selected_node_uid:
            outline_color = self.theme_manager.get_color("accent")
            outline_width = 3
        else:
            outline_width = 2
        
        w, h = 120, 70
        
        item_ids = []
        
        # Shadow
        item_ids.append(self.create_rectangle(x-w/2+4, y-h/2+4, x+w/2+4, y+h/2+4, fill="#000000", outline="", tags=f"node_shadow_{uid}"))
        # Card body
        rect_id = self.create_rectangle(
            x-w/2, y-h/2, x+w/2, y+h/2,
            fill=bg_card, outline=outline_color, width=outline_width, dash=dash_style,
            tags=(f"node_{uid}", "node_rect")
        )
        item_ids.append(rect_id)
        
        # Pin
        pin_color = self._get_pin_color(uid, node_data)
        item_ids.append(self.create_oval(
            x-5, y-h/2-5, x+5, y-h/2+5,
            fill=pin_color, outline="black", tags=f"node_{uid}"
        ))
        
        # Text
        text_id = self.create_text(
            x, y-10,
            text=name, width=w-10, font=name_font, fill=fg_text,
            tags=(f"node_{uid}", "node_label")
        )
        item_ids.append(text_id)
        
        # Type label
        item_ids.append(self.create_text(
            x, y+20,
            text=type_label, font=type_font, fill=outline_color,
            tags=f"node_{uid}"
        ))

        self.node_widgets[uid] = item_ids

    def _draw_link(self, src_uid, tgt_uid, label, ltype, layout, link_index):
        src_pos = layout.get(src_uid)
        tgt_pos = layout.get(tgt_uid)
        if not src_pos or not tgt_pos:
            return

        sx, sy, tx, ty = self._calculate_link_endpoints(src_pos, tgt_pos)
        color = self._get_link_color(ltype)

        selected = link_index == self.selected_link_index
        line_width = 3 if selected else 2
        text_font = ("Arial", 8, "bold") if selected else ("Arial", 8, "italic")

        line_id = self.create_line(sx, sy, tx, ty, fill=color, width=line_width, arrow=tk.LAST, tags=(f"link_{link_index}", "link_line"))
        text_id = self.create_text((sx+tx)/2, (sy+ty)/2 - 10, text=label, fill=color, font=text_font, tags=(f"link_{link_index}", "link_label"))
        
        self.link_widgets[link_index] = [line_id, text_id]

    def get_node_uid_at(self, x_canvas, y_canvas):
        items = self.find_closest(x_canvas, y_canvas, halo=5)
        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith("node_") and not tag.startswith("node_shadow_"):
                    return tag[5:] # Return UID
        return None

    def get_link_index_at(self, x_canvas, y_canvas):
        items = self.find_closest(x_canvas, y_canvas, halo=5)
        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith("link_"):
                    try:
                        return int(tag[5:])
                    except ValueError:
                        continue
        return None

    def on_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        node_uid = self.get_node_uid_at(x, y)
        link_index = None
        if not node_uid:
            link_index = self.get_link_index_at(x, y)
        
        if node_uid:
            self.drag_data["node_uid"] = node_uid
            self.drag_data["start_x"] = x
            self.drag_data["start_y"] = y
            self.drag_data["dragging"] = False

        self._set_selection(node_uid=node_uid, link_index=link_index)
        
        if self.linking_data["active"]:
            self.linking_data["active"] = False
            self.delete(self.linking_data["line_id"])
            if node_uid and node_uid != self.linking_data["source_uid"]:
                self._create_link(self.linking_data["source_uid"], node_uid)
            self.linking_data = {"active": False, "source_uid": None, "line_id": None}
            
    def on_drag_motion(self, event):
        if self.linking_data["active"]:
            x, y = self.canvasx(event.x), self.canvasy(event.y)
            self.coords(self.linking_data["line_id"], self.linking_data["start_x"], self.linking_data["start_y"], x, y)
            return

        if self.drag_data["node_uid"]:
            dx = self.canvasx(event.x) - self.drag_data["start_x"]
            dy = self.canvasy(event.y) - self.drag_data["start_y"]
            
            if not self.drag_data["dragging"] and (abs(dx) > 5 or abs(dy) > 5):
                self.drag_data["dragging"] = True
            
            if self.drag_data["dragging"]:
                self.move(f"node_{self.drag_data['node_uid']}", dx, dy)
                self.move(f"node_shadow_{self.drag_data['node_uid']}", dx, dy) # Move shadow too
                self.drag_data["start_x"] = self.canvasx(event.x)
                self.drag_data["start_y"] = self.canvasy(event.y)
                self._update_links_for_node(self.drag_data["node_uid"], use_canvas=True)

    def on_release(self, event):
        was_dragging = self.drag_data.get("dragging")
        released_uid = self.drag_data.get("node_uid") if was_dragging else None
        if self.drag_data["node_uid"] and self.drag_data["dragging"]:
            x, y = self.canvasx(event.x), self.canvasy(event.y)
            
            # Recalculate node center after drag
            item_ids = self.node_widgets.get(self.drag_data["node_uid"])
            if item_ids:
                rect_id = item_ids[1] # The rect element
                x1, y1, x2, y2 = self.coords(rect_id)
                new_cx, new_cy = (x1+x2)/2, (y1+y2)/2
                
                # Update layout data in ProjectManager
                self.command_executor(UpdateEvidenceNodeLayoutCommand(
                    self.project_manager, 
                    self.drag_data["node_uid"], 
                    [new_cx, new_cy]
                ))
        self.drag_data = {"node_uid": None, "start_x": 0, "start_y": 0, "dragging": False}
        if released_uid:
            self._schedule_refresh(node_uids=[released_uid], refresh_links=True)

    def on_right_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        node_uid = self.get_node_uid_at(x, y)
        link_idx = None
        if not node_uid:
            link_idx = self.get_link_index_at(x, y)
        self._set_selection(node_uid=node_uid, link_index=link_idx)
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="添加新线索节点", command=lambda: self.add_node_dialog(x, y))
        menu.add_separator()
        
        if node_uid:
            node_data = self.nodes.get(node_uid)
            if node_data and node_data["type"] != "character": # Allow editing custom nodes
                menu.add_command(label="编辑节点", command=lambda uid=node_uid: self._set_selection(node_uid=uid, link_index=None, focus=True))
                menu.add_command(label="删除节点", command=lambda: self.delete_node(node_uid))
                menu.add_separator()
            
            menu.add_command(label="连线从此节点...", command=lambda: self._start_linking(node_uid, x, y))
            
        if link_idx is not None:
            menu.add_command(label="编辑连线", command=lambda idx=link_idx: self._set_selection(node_uid=None, link_index=idx, focus=True))
            menu.add_command(label="删除连线", command=lambda idx=link_idx: self.delete_link(idx))
        
        self.context_menu = menu
        self.context_menu.post(event.x_root, event.y_root)

    def on_double_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        node_uid = self.get_node_uid_at(x, y)
        if node_uid:
            node_data = self.nodes.get(node_uid)
            if node_data and node_data["type"] != "character": # Allow editing custom nodes
                self._set_selection(node_uid=node_uid, link_index=None, focus=True)
        
    def on_hover(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        node_uid = self.get_node_uid_at(x, y)
        
        if node_uid and node_uid in self.nodes:
            node_data = self.nodes[node_uid]
            tooltip_text = f"【{node_data.get('name')}】\n类型: {node_data.get('type')}\n描述: {node_data.get('description', '-')}"
            self._show_tooltip(event.x_root, event.y_root, tooltip_text)
        else:
            self._hide_tooltip()

    def _show_tooltip(self, x, y, text):
        if not hasattr(self, 'hover_tooltip_win') or not self.hover_tooltip_win:
            self.hover_tooltip_win = tk.Toplevel(self)
            self.hover_tooltip_win.wm_overrideredirect(True)
            self.hover_tooltip_win.wm_attributes("-topmost", True)
            self.hover_tooltip_label = tk.Label(self.hover_tooltip_win, bg="#FFFFDD", fg="black", justify=tk.LEFT, relief="solid", bd=1, wraplength=250)
            self.hover_tooltip_label.pack()
        
        bg = "#FFFFDD"
        fg = "black"
        if self.theme_manager.current_theme == "Dark":
            bg = "#333333"
            fg = "#FFFFFF"
        self.hover_tooltip_label.configure(text=text, bg=bg, fg=fg)
        self.hover_tooltip_win.geometry(f"+{x+15}+{y+15}")

    def _hide_tooltip(self, event=None):
        if hasattr(self, 'hover_tooltip_win') and self.hover_tooltip_win:
            self.hover_tooltip_win.destroy()
            self.hover_tooltip_win = None

    def _start_linking(self, source_uid, x, y):
        self.linking_data["active"] = True
        self.linking_data["source_uid"] = source_uid
        self.linking_data["start_x"] = x
        self.linking_data["start_y"] = y
        self.linking_data["line_id"] = self.create_line(x, y, x, y, dash=(4, 2), width=2, fill="gray")

    def _create_link(self, source_uid, target_uid):
        dialog = EvidenceLinkDialog(self.winfo_toplevel())
        self.wait_window(dialog)
        if dialog.result:
            link_data = {
                "source": source_uid,
                "target": target_uid,
                "label": dialog.result.get("label", ""),
                "type": dialog.result.get("type", "relates_to")
            }
            self.command_executor(AddEvidenceLinkCommand(self.project_manager, link_data))

    def edit_link_dialog(self, link_index):
        rels = self.project_manager.get_relationships()
        links = rels.get("evidence_links", [])
        if 0 <= link_index < len(links):
            old_link = links[link_index]
            dialog = EvidenceLinkDialog(self.winfo_toplevel(), old_link)
            self.wait_window(dialog)
            if dialog.result:
                old_label = old_link["label"]
                old_type = old_link["type"]
                new_label = dialog.result["label"]
                new_type = dialog.result["type"]
                if old_label != new_label or old_type != new_type:
                    new_data = {
                        "label": new_label,
                        "type": new_type
                    }
                    self.command_executor(EditEvidenceLinkCommand(
                        self.project_manager,
                        link_index,
                        new_data
                    ))

    def delete_link(self, link_index):
        if messagebox.askyesno("确认", "确定删除此链接？"):
            self.command_executor(DeleteEvidenceLinkCommand(self.project_manager, link_index))
            if self.selected_link_index == link_index:
                self._clear_selection()

    def add_node_dialog(self, x, y):
        scenes = self.project_manager.get_scenes()
        dialog = EvidenceNodeDialog(self.winfo_toplevel(), scenes=scenes)
        self.wait_window(dialog)
        if dialog.result:
            node_data = dialog.result
            self.command_executor(AddEvidenceNodeCommand(self.project_manager, node_data, [self.canvasx(x), self.canvasy(y)]))

    def edit_node_dialog(self, node_data):
        scenes = self.project_manager.get_scenes()
        dlg = EvidenceNodeDialog(self.winfo_toplevel(), node_data, scenes=scenes)
        self.wait_window(dlg)
        if dlg.result:
            new_data = dlg.result
            if node_data.get("is_placeholder"):
                new_data["is_placeholder"] = False
            if new_data != node_data:
                self.command_executor(EditEvidenceNodeCommand(self.project_manager, node_data["uid"], node_data, new_data))

    def delete_node(self, node_uid):
        if messagebox.askyesno("确认", "确定删除此节点？"):
            rels = self.project_manager.get_relationships()
            nodes = rels.get("nodes", [])
            node_to_delete = next((n for n in nodes if n.get("uid") == node_uid), None)
            if node_to_delete:
                self.command_executor(DeleteEvidenceNodeCommand(self.project_manager, node_uid))
                if self.selected_node_uid == node_uid:
                    self._clear_selection()
            else: # Must be a character from script. For now, characters are not deletable from here
                messagebox.showinfo("提示", "角色节点请在剧本面板的角色管理中删除。")
