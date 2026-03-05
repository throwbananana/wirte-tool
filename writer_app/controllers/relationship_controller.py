import tkinter as tk
from tkinter import ttk, messagebox
from writer_app.controllers.base_controller import BaseController
from writer_app.ui.relationship_map import RelationshipMapCanvas
from writer_app.ui.relationship_timeline import RelationshipTimelinePanel
from writer_app.ui.help_dialog import create_module_help_button

class RelationshipController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager, config_manager, on_jump_to_scene=None, on_jump_to_outline=None):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.config_manager = config_manager
        self.on_jump_to_scene = on_jump_to_scene
        self.on_jump_to_outline = on_jump_to_outline  # Callback to jump to outline node
        self.relationship_tag_filter_var = tk.StringVar(value="全部")
        self.layout_btn_var = tk.StringVar(value="开始自动布局")
        self.current_snapshot_idx = -1  # -1 means current/live state
        self.timeline_mode = "snapshot"
        self.current_frame_id = ""

        self.setup_ui()
        self.theme_manager.add_listener(self.apply_theme)

    def setup_ui(self):
        # Main Layout
        content_frame = ttk.Frame(self.parent)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top Toolbar
        toolbar = ttk.Frame(content_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="刷新布局", command=self.refresh).pack(side=tk.LEFT, padx=5)
        self.layout_btn = ttk.Button(toolbar, textvariable=self.layout_btn_var, command=self.toggle_layout)
        self.layout_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="导出图片", command=self.export_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="自动生成", command=self.auto_generate).pack(side=tk.LEFT, padx=5)

        ttk.Label(toolbar, text="|").pack(side=tk.LEFT, padx=5)
        
        # Tag Filter
        ttk.Label(toolbar, text="标签过滤:").pack(side=tk.LEFT, padx=2)
        self.relationship_tag_combo = ttk.Combobox(toolbar, textvariable=self.relationship_tag_filter_var, width=12, state="readonly")
        self.relationship_tag_combo.pack(side=tk.LEFT)
        self.relationship_tag_combo.bind("<<ComboboxSelected>>", self.on_tag_filter_change)

        # 帮助按钮
        help_btn = create_module_help_button(toolbar, "relationship", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        self.rel_tag_legend = ttk.Frame(toolbar)
        self.rel_tag_legend.pack(side=tk.RIGHT, padx=4)
        
        # Canvas
        self.view = RelationshipMapCanvas(
            content_frame,
            project_manager=self.project_manager,
            command_executor=self.command_executor,
            theme_manager=self.theme_manager,
            config_manager=self.config_manager,
            on_jump_to_scene=self.on_jump_to_scene,
            on_jump_to_outline=self.on_jump_to_outline
        )
        self.view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bottom Timeline
        self.timeline_panel = RelationshipTimelinePanel(content_frame, self)
        self.timeline_panel.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)

    def save_snapshot(self):
        name = tk.simpledialog.askstring("保存快照", "请输入时间点名称 (e.g. 第一章结束):", parent=self.parent)
        if not name: return
        
        self.project_manager.add_relationship_snapshot(name)
        # Switch to the new snapshot (which is the last one)
        snapshots = self.project_manager.get_relationship_snapshots()
        self.current_snapshot_idx = len(snapshots) - 1
        self.refresh()
        messagebox.showinfo("成功", f"已保存快照: {name}")

    def delete_snapshot(self):
        if self.current_snapshot_idx == -1: return
        
        snapshots = self.project_manager.get_relationship_snapshots()
        if 0 <= self.current_snapshot_idx < len(snapshots):
            name = snapshots[self.current_snapshot_idx].get("name")
            if messagebox.askyesno("删除快照", f"确定要删除快照 '{name}' 吗？"):
                self.project_manager.delete_relationship_snapshot(self.current_snapshot_idx)
                self.current_snapshot_idx = -1 # Reset to Live
                self.refresh()

    def rename_snapshot(self, idx):
        snapshots = self.project_manager.get_relationship_snapshots()
        if 0 <= idx < len(snapshots):
            old_name = snapshots[idx].get("name")
            new_name = tk.simpledialog.askstring("重命名", f"重命名 '{old_name}' 为:", initialvalue=old_name, parent=self.parent)
            if new_name:
                self.project_manager.update_relationship_snapshot(idx, name=new_name)
                self.refresh()

    def switch_to_snapshot_by_slider(self, val):
        if self.timeline_mode != "snapshot":
            return
        snapshots = self.project_manager.get_relationship_snapshots()
        max_val = len(snapshots)
        
        if val >= max_val:
            # Live Mode
            self.current_snapshot_idx = -1
            self.view.set_snapshot_links(None)
        else:
            # Snapshot Mode
            self.current_snapshot_idx = val
            self.view.set_snapshot_links(snapshots[val]["links"])
        
        self.view.refresh()

    def set_timeline_mode(self, mode):
        if mode not in ("snapshot", "frame"):
            return
        self.timeline_mode = mode
        if mode == "snapshot":
            current_val = self.timeline_panel.get_current_slider_val()
            self.switch_to_snapshot_by_slider(current_val)
        else:
            self.switch_to_frame(self.current_frame_id)

    def _collect_frame_items(self):
        rels = self.project_manager.get_relationships()
        events = rels.get("relationship_events", [])
        frames = {}
        for ev in events:
            frame_id = ev.get("frame_id")
            if not frame_id:
                continue
            created_at = ev.get("created_at", 0)
            title = ev.get("chapter_title") or ev.get("frame_title") or "未命名帧"
            existing = frames.get(frame_id)
            if existing:
                if not existing.get("title") and title:
                    existing["title"] = title
                if created_at and (not existing.get("created_at") or created_at < existing["created_at"]):
                    existing["created_at"] = created_at
            else:
                frames[frame_id] = {
                    "frame_id": frame_id,
                    "title": title,
                    "created_at": created_at,
                }
        return sorted(frames.values(), key=lambda f: (f.get("created_at", 0), f.get("title", "")))

    def _get_frame_links(self, frame_id):
        rels = self.project_manager.get_relationships()
        links = rels.get("relationship_links", [])
        if not frame_id:
            return links

        events = rels.get("relationship_events", [])
        event_keys = set()
        for ev in events:
            if ev.get("frame_id") == frame_id:
                event_keys.add((
                    ev.get("source"),
                    ev.get("target"),
                    ev.get("target_type", "character"),
                    ev.get("label", "")
                ))

        filtered = []
        for link in links:
            frame_ids = link.get("event_frame_ids", [])
            if isinstance(frame_ids, list) and frame_id in frame_ids:
                filtered.append(link)
                continue
            key = (
                link.get("source"),
                link.get("target"),
                link.get("target_type", "character"),
                link.get("label", "")
            )
            if key in event_keys:
                filtered.append(link)
        return filtered

    def switch_to_frame(self, frame_id):
        if self.timeline_mode != "frame":
            return
        self.current_frame_id = frame_id or ""
        if not self.current_frame_id:
            self.view.set_snapshot_links(None)
        else:
            self.view.set_snapshot_links(self._get_frame_links(self.current_frame_id))
        self.view.refresh()

    def auto_generate(self):
        count = self.project_manager.auto_generate_relationships()
        if count > 0:
            messagebox.showinfo("成功", f"自动生成了 {count} 条关系连线。")
            self.refresh()
        else:
            messagebox.showinfo("提示", "未发现新的共现关系 (需两个角色出现在同一场景)。")

    def toggle_layout(self):
        if self.view.is_force_layout_running():
            self.view.stop_force_layout()
            self.layout_btn_var.set("开始自动布局")
        else:
            self.view.start_force_layout()
            self.layout_btn_var.set("停止自动布局")

    def export_image(self):
        if hasattr(self.view, 'export_to_image'):
            self.view.export_to_image()
        else:
            messagebox.showinfo("提示", "当前视图不支持导出图片")

    def refresh(self):
        snapshots = self.project_manager.get_relationship_snapshots()
        frames = self._collect_frame_items()
        self.timeline_panel.update_data(snapshots, self.current_snapshot_idx)
        self.timeline_panel.update_frames(frames, self.current_frame_id, self.timeline_mode)
        
        # Update combo values
        tags = ["全部"] + [t.get("name") for t in self.project_manager.get_tags_config()]
        self.relationship_tag_combo["values"] = tags
        
        self.view.set_tag_filter(None if self.relationship_tag_filter_var.get() == "全部" else self.relationship_tag_filter_var.get())
        if self.timeline_mode == "frame":
            self.switch_to_frame(self.current_frame_id)
        else:
            self.view.refresh()
        self._render_legend()

    def apply_theme(self):
        bg = self.theme_manager.get_color("canvas_bg")
        self.view.configure(bg=bg)
        self.view.refresh()

    def on_tag_filter_change(self, event=None):
        self.refresh()

    def _render_legend(self):
        for w in self.rel_tag_legend.winfo_children():
            w.destroy()
        tag_configs = self.project_manager.get_tags_config()
        if not tag_configs:
            ttk.Label(self.rel_tag_legend, text="无标签", foreground="#666").pack(side=tk.LEFT)
            return
        
        active_tag = self.relationship_tag_filter_var.get()
        for t in tag_configs[:8]:
            color = t.get("color", "#ccc")
            name = t.get("name", "")
            is_active = (name == active_tag)
            btn = tk.Button(
                self.rel_tag_legend,
                text=" ",
                relief=tk.SUNKEN if is_active else tk.FLAT,
                bd=2 if is_active else 0,
                bg=color,
                width=2,
                command=lambda n=name: self._on_legend_click(n)
            )
            btn.pack(side=tk.LEFT, padx=2)
            lbl = tk.Label(self.rel_tag_legend, text=name, font=("Arial", 9, "bold" if is_active else "normal"))
            lbl.bind("<Button-1>", lambda e, n=name: self._on_legend_click(n))
            lbl.pack(side=tk.LEFT, padx=(0,6))

    def _on_legend_click(self, name):
        if self.relationship_tag_filter_var.get() == name:
            self.relationship_tag_filter_var.set("全部")
        else:
            self.relationship_tag_filter_var.set(name)
        self.refresh()

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "relationship")
