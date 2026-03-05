from writer_app.controllers.base_controller import BaseController
# Import specific views
from writer_app.ui.outline_views.horizontal_tree import HorizontalTreeView
from writer_app.ui.outline_views.vertical_tree import VerticalTreeView
from writer_app.ui.outline_views.radial_view import RadialView
from writer_app.ui.outline_views.table_view import TableView
from writer_app.ui.outline_views.flat_draft_view import FlatDraftView
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from writer_app.ui.tags import TagSelectorDialog, SetNodeTagsCommand
from writer_app.ui.dialogs import DiagnosisResultDialog, ValidationResultDialog
from writer_app.core.logic_validator import get_logic_validator
from writer_app.core.commands import AddNodeCommand, DeleteNodesCommand, EditNodeCommand
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.core.project_types import ProjectTypeManager
from writer_app.controllers.ai_controller import AIController
from writer_app.ui.help_dialog import create_module_help_button
import threading
import json

class MindMapController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager, ai_client, config_manager, ai_controller):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.ai_client = ai_client
        self.config_manager = config_manager
        
        self.mindmap_tag_filters = set()
        self.ai_generating = False
        self.outline_helper_running = False
        
        self.current_selected_node = None
        
        # Variables for UI binding
        self.lm_api_url = tk.StringVar(value=self.config_manager.get("lm_api_url", "http://localhost:1234/v1/chat/completions"))
        self.lm_api_model = tk.StringVar(value=self.config_manager.get("lm_api_model", "local-model"))
        self.lm_api_key = tk.StringVar(value=self.config_manager.get("lm_api_key", ""))
        self.ai_status_var = tk.StringVar(value="使用本地 LM Studio 分析剧本并生成思维导图")
        self.outline_helper_status_var = tk.StringVar(value="选择节点后可用AI补全内容或生成子节点")
        self.outline_helper_hint_var = tk.StringVar(value="")
        self._ai_status_default = self.ai_status_var.get()
        self._outline_helper_status_default = self.outline_helper_status_var.get()
        self.mindmap_tag_filter_label_var = tk.StringVar(value="全部标签")
        self.node_title_var = tk.StringVar()
        
        self.ai_controller = ai_controller

        # View Mode
        self.view_mode_var = tk.StringVar(value="水平树状图")
        self._view_style_labels = {
            "horizontal": "水平树状图",
            "vertical": "垂直树状图",
            "radial": "放射发散图",
            "table": "大纲表格",
            "flat_draft": "平铺叙事草稿",
        }
        self._view_label_to_style = {v: k for k, v in self._view_style_labels.items()}
        try:
            preferred_style = self.project_manager.get_outline_template_style()
            if not preferred_style or preferred_style == "default":
                preferred_style = ProjectTypeManager.get_default_outline_view(
                    self.project_manager.get_project_type()
                )
            if preferred_style not in self._view_style_labels:
                preferred_style = ProjectTypeManager.get_default_outline_view(
                    self.project_manager.get_project_type()
                )
            preferred_label = self._view_style_labels.get(preferred_style)
            if preferred_label:
                self.view_mode_var.set(preferred_label)
        except Exception:
            pass
        self.canvas_container = None # Container for the canvas
        
        self.setup_ui()
        self._add_theme_listener(self.apply_theme)
        self.set_ai_mode_enabled(self.config_manager.is_ai_enabled())
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅事件总线以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.OUTLINE_NODE_ADDED, self._on_outline_changed)
        self._subscribe_event(Events.OUTLINE_NODE_DELETED, self._on_outline_changed)
        self._subscribe_event(Events.OUTLINE_NODE_MOVED, self._on_outline_changed)
        self._subscribe_event(Events.OUTLINE_CHANGED, self._on_outline_changed)
        self._subscribe_event(Events.SCENE_ADDED, self._on_scene_changed)
        self._subscribe_event(Events.SCENE_DELETED, self._on_scene_changed)
        self._subscribe_event(Events.PROJECT_LOADED, self._on_project_loaded)
        self._subscribe_event(Events.TAGS_UPDATED, self._on_tags_changed)

    def _on_outline_changed(self, event_type=None, **kwargs):
        """响应大纲变化事件"""
        self.refresh()

    def _on_scene_changed(self, event_type=None, **kwargs):
        """响应场景变化事件 - 更新场景计数"""
        self.refresh()

    def _on_project_loaded(self, event_type=None, **kwargs):
        """响应项目加载事件"""
        self.refresh()

    def _on_tags_changed(self, event_type=None, **kwargs):
        """响应标签变化事件"""
        self.refresh()

    def setup_ui(self):
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_panel = ttk.Frame(main_paned)
        main_paned.add(left_panel, weight=4)

        # Toolbar
        toolbar = ttk.Frame(left_panel)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # View Mode Selector
        ttk.Label(toolbar, text="视图:").pack(side=tk.LEFT, padx=(2, 2))
        view_combo = ttk.Combobox(
            toolbar,
            textvariable=self.view_mode_var,
            values=["水平树状图", "垂直树状图", "放射发散图", "大纲表格", "平铺叙事草稿"],
            state="readonly",
            width=14
        )
        view_combo.pack(side=tk.LEFT, padx=2)
        view_combo.bind("<<ComboboxSelected>>", self.change_view_mode)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(toolbar, text="+ 子节点", command=self.add_child_node).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="+ 同级", command=self.add_sibling_node).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self.delete_node).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="展开全部", command=self.expand_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="折叠全部", command=self.collapse_all).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=2)
        
        # Export Button
        ttk.Button(toolbar, text="导出图片", command=self.export_image).pack(side=tk.LEFT, padx=2)
        
        # Logic Check Button
        ttk.Button(toolbar, text="逻辑检查", command=self.run_logic_check).pack(side=tk.LEFT, padx=2)

        # 帮助按钮
        help_btn = create_module_help_button(toolbar, "outline", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        ttk.Label(toolbar, text="括号内=场景数", foreground="#666666").pack(side=tk.RIGHT, padx=4)

        # AI Frame
        ai_frame = ttk.LabelFrame(left_panel, text="AI生成思维导图 (本地 LM Studio)")
        ai_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(ai_frame, text="接口URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(ai_frame, textvariable=self.lm_api_url, width=45).grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        self.ai_generate_btn = ttk.Button(ai_frame, text="AI生成思维导图", command=self.generate_outline_with_ai)
        self.ai_generate_btn.grid(row=0, column=2, rowspan=2, sticky="ns", padx=6, pady=4)
        self.ai_diagnose_btn = ttk.Button(ai_frame, text="大纲诊断", command=self.diagnose_outline_with_ai)
        self.ai_diagnose_btn.grid(row=2, column=2, rowspan=1, sticky="ns", padx=6, pady=4)

        ttk.Label(ai_frame, text="模型:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(ai_frame, textvariable=self.lm_api_model, width=20).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(ai_frame, text="API Key(可选):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(ai_frame, textvariable=self.lm_api_key, width=30, show="*").grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(ai_frame, textvariable=self.ai_status_var, foreground="#666666").grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(0, 4))
        ai_frame.columnconfigure(1, weight=1)

        # Canvas Frame
        canvas_frame = ttk.LabelFrame(left_panel, text="思维导图 (双击编辑 | 右键菜单 | 点击+添加子节点)")
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Legend/Filter
        legend_frame = ttk.Frame(canvas_frame)
        legend_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(legend_frame, text="标签过滤:").pack(side=tk.LEFT)
        ttk.Button(legend_frame, textvariable=self.mindmap_tag_filter_label_var, command=self.open_mindmap_filter_selector, width=16).pack(side=tk.LEFT, padx=(2, 10))
        ttk.Label(legend_frame, text="标签:").pack(side=tk.LEFT)
        self.mindmap_tag_legend = ttk.Frame(legend_frame)
        self.mindmap_tag_legend.pack(side=tk.LEFT, padx=4)

        # Container for the Canvas (to easily swap views)
        self.canvas_container = ttk.Frame(canvas_frame)
        self.canvas_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize default view
        self.change_view_mode()

        # Right Panel (Node Details)
        right_panel = ttk.LabelFrame(main_paned, text="节点详情")
        main_paned.add(right_panel, weight=1)
        detail_frame = ttk.Frame(right_panel)
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Label(detail_frame, text="标题:").pack(anchor=tk.W)
        self.node_title_entry = ttk.Entry(detail_frame, textvariable=self.node_title_var)
        self.node_title_entry.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(detail_frame, text="内容/备注:").pack(anchor=tk.W)
        content_frame = ttk.Frame(detail_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        self.node_content_text = tk.Text(content_frame, wrap=tk.WORD, height=15)
        content_scroll = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.node_content_text.yview)
        self.node_content_text.configure(yscrollcommand=content_scroll.set)
        self.node_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(detail_frame, text="保存节点详情", command=self.save_node_details).pack(pady=10, fill=tk.X)

        # AI Outline Helper Frame
        ai_outline_frame = ttk.LabelFrame(detail_frame, text="AI补全/扩展节点")
        ai_outline_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(ai_outline_frame, text="补全提示(可选):").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Entry(ai_outline_frame, textvariable=self.outline_helper_hint_var).grid(row=0, column=1, columnspan=2, sticky="ew", padx=4, pady=2)
        self.node_ai_complete_btn = ttk.Button(ai_outline_frame, text="补全当前节点内容", command=self.ai_complete_current_node)
        self.node_ai_complete_btn.grid(row=1, column=0, sticky="ew", padx=4, pady=2)
        self.node_ai_children_btn = ttk.Button(ai_outline_frame, text="生成子节点建议", command=self.ai_suggest_children_for_node)
        self.node_ai_children_btn.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        self.full_outline_ai_btn = ttk.Button(ai_outline_frame, text="补全整份大纲", command=self.ai_complete_whole_outline)
        self.full_outline_ai_btn.grid(row=1, column=2, sticky="ew", padx=4, pady=2)
        ttk.Label(ai_outline_frame, textvariable=self.outline_helper_status_var, foreground="#666666").grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=4, pady=(2, 4))
        ai_outline_frame.columnconfigure(1, weight=1)
        ai_outline_frame.columnconfigure(2, weight=1)

    def _init_canvas_view(self, view_class):
        """Initialize or replace the canvas view"""
        if hasattr(self, 'mindmap_canvas'):
            self.mindmap_canvas.destroy()
            
        # Clean up scrollbars if any
        for widget in self.canvas_container.winfo_children():
            widget.destroy()
            
        self.mindmap_canvas = view_class(
            self.canvas_container,
            project_manager=self.project_manager,
            command_executor=self.command_executor,
            on_node_select=self.on_mindmap_select,
            on_ai_suggest_branch=self.ai_request_branch_suggestion,
            on_generate_scene=self.generate_scene_from_node_with_ai,
            on_set_tags=self.open_node_tag_selector
        )
        self.view = self.mindmap_canvas
        if hasattr(self.mindmap_canvas, "set_ai_mode_enabled"):
            self.mindmap_canvas.set_ai_mode_enabled(self.config_manager.is_ai_enabled())
        
        h_scroll = ttk.Scrollbar(self.canvas_container, orient=tk.HORIZONTAL, command=self.mindmap_canvas.xview)
        v_scroll = ttk.Scrollbar(self.canvas_container, orient=tk.VERTICAL, command=self.mindmap_canvas.yview)
        self.mindmap_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        self.mindmap_canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        self.canvas_container.grid_columnconfigure(0, weight=1)
        self.canvas_container.grid_rowconfigure(0, weight=1)
        
        # Apply current theme if available
        if hasattr(self, 'theme_manager'):
            self.apply_theme()

    def change_view_mode(self, event=None):
        mode = self.view_mode_var.get()
        if mode == "水平树状图":
            self._init_canvas_view(HorizontalTreeView)
        elif mode == "垂直树状图":
            self._init_canvas_view(VerticalTreeView)
        elif mode == "放射发散图":
            self._init_canvas_view(RadialView)
        elif mode == "大纲表格":
            self._init_canvas_view(TableView)
        elif mode == "平铺叙事草稿":
            self._init_canvas_view(FlatDraftView)
        style_key = self._view_label_to_style.get(mode)
        if style_key and event is not None and self.project_manager.get_outline_template_style() != style_key:
            self.project_manager.set_outline_template_style(style_key)
        self.refresh()

    def export_image(self):
        if hasattr(self.mindmap_canvas, 'export_to_image'):
            self.mindmap_canvas.export_to_image()
        else:
            messagebox.showinfo("提示", "当前视图不支持导出图片")

    def run_logic_check(self):
        validator = get_logic_validator(self.project_manager)
        report = validator.run_full_validation()
        # Note: We need a way to navigate back to script tab from here if double clicked.
        # But for now, we just show the report.
        ValidationResultDialog(self.parent.winfo_toplevel(), report)

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "outline")

    def refresh(self):
        # Refresh Logic
        valid_names = {t.get("name") for t in self.project_manager.get_tags_config()}
        self.mindmap_tag_filters = {t for t in self.mindmap_tag_filters if t in valid_names}
        self._update_mindmap_filter_label()
        
        # Build scene counts logic here or helper
        # Logic from main.py:
        counts = {}
        outline_root = self.project_manager.get_outline()
        
        # Recursive path map builder - we can duplicate the helper or keep it in util
        # Let's simple reimplement for isolation
        def _build_path_map(node, prefix=""):
            if not node: return {}
            name = node.get("name", "")
            current_path = f"{prefix} / {name}" if prefix else name
            mapping = {current_path: node.get("uid", "")}
            for child in node.get("children", []):
                mapping.update(_build_path_map(child, current_path))
            return mapping
            
        path_map = _build_path_map(outline_root)
        for scene in self.project_manager.get_scenes():
            uid = scene.get("outline_ref_id", "")
            if not uid:
                path = scene.get("outline_ref_path", "") or scene.get("outline_ref", "")
                uid = path_map.get(path, "")
            if uid:
                counts[uid] = counts.get(uid, 0) + 1
        
        self.mindmap_canvas.set_scene_counts(counts)
        self.mindmap_canvas.set_data(self.project_manager.get_outline())
        self.mindmap_canvas.set_tag_filter(self.mindmap_tag_filters if self.mindmap_tag_filters else None)
        self.mindmap_canvas.refresh()
        self._render_mindmap_tag_legend()

    def set_ai_mode_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in [
            getattr(self, "ai_generate_btn", None),
            getattr(self, "ai_diagnose_btn", None),
            getattr(self, "node_ai_complete_btn", None),
            getattr(self, "node_ai_children_btn", None),
            getattr(self, "full_outline_ai_btn", None)
        ]:
            if btn:
                btn.config(state=state)
        if not enabled:
            self.ai_status_var.set("非AI模式已关闭AI功能")
            self.outline_helper_status_var.set("非AI模式下不可用")
        else:
            self.ai_status_var.set(self._ai_status_default)
            self.outline_helper_status_var.set(self._outline_helper_status_default)
        if hasattr(self, "mindmap_canvas") and hasattr(self.mindmap_canvas, "set_ai_mode_enabled"):
            self.mindmap_canvas.set_ai_mode_enabled(enabled)

    def apply_theme(self):
        if hasattr(self.mindmap_canvas, "apply_theme"):
            self.mindmap_canvas.apply_theme(self.theme_manager)
        
        # Update text area manually
        theme = self.theme_manager
        bg = theme.get_color("editor_bg")
        fg = theme.get_color("editor_fg")
        if hasattr(self, 'node_content_text') and self.node_content_text:
            self.node_content_text.configure(bg=bg, fg=fg, insertbackground=fg)

    # --- Interaction Handlers ---
    
    def on_mindmap_select(self, node):
        self.current_selected_node = node
        self.node_title_var.set(node.get("name", ""))
        self.node_content_text.delete("1.0", tk.END)
        self.node_content_text.insert("1.0", node.get("content", ""))

    def save_node_details(self):
        if not self.current_selected_node:
            messagebox.showwarning("提示", "请先选择一个节点")
            return
        
        old_name = self.current_selected_node.get("name", "")
        old_content = self.current_selected_node.get("content", "")
        new_name = self.node_title_var.get().strip()
        new_content = self.node_content_text.get("1.0", tk.END).strip()

        if old_name != new_name or old_content != new_content:
            command = EditNodeCommand(
                self.project_manager,
                self.current_selected_node.get("uid"),
                old_name, new_name,
                old_content, new_content,
                "编辑节点详情"
            )
            self.command_executor(command)
            self.refresh()

    def open_mindmap_filter_selector(self):
        dialog = TagSelectorDialog(self.parent, self.project_manager, list(self.mindmap_tag_filters))
        if dialog.result is not None:
            self.mindmap_tag_filters = set(dialog.result)
            self.refresh()

    def on_mindmap_tag_click(self, tag_name):
        if tag_name in self.mindmap_tag_filters:
            self.mindmap_tag_filters.remove(tag_name)
        else:
            self.mindmap_tag_filters.add(tag_name)
        self.refresh()

    def _render_mindmap_tag_legend(self):
        for w in self.mindmap_tag_legend.winfo_children():
            w.destroy()
        tag_configs = self.project_manager.get_tags_config()
        if not tag_configs:
            ttk.Label(self.mindmap_tag_legend, text="无标签", foreground="#666").pack(side=tk.LEFT)
            return
        
        # Helper to build legend buttons
        for t in tag_configs[:8]:
            color = t.get("color", "#ccc")
            name = t.get("name", "")
            is_active = name in self.mindmap_tag_filters
            btn = tk.Button(
                self.mindmap_tag_legend,
                text=" ",
                relief=tk.SUNKEN if is_active else tk.FLAT,
                bd=2 if is_active else 0,
                highlightthickness=0,
                command=lambda n=name: self.on_mindmap_tag_click(n)
            )
            btn.configure(width=2, bg=color, activebackground=color)
            btn.pack(side=tk.LEFT, padx=2)
            lbl = tk.Label(self.mindmap_tag_legend, text=name, fg="#222" if is_active else "#555", cursor="hand2", font=("Arial", 9, "bold" if is_active else "normal"))
            lbl.bind("<Button-1>", lambda e, n=name: self.on_mindmap_tag_click(n))
            lbl.pack(side=tk.LEFT, padx=(0,6))

    def _update_mindmap_filter_label(self):
        if not self.mindmap_tag_filters:
            self.mindmap_tag_filter_label_var.set("全部标签")
        else:
            sorted_tags = sorted(self.mindmap_tag_filters)
            text = "，".join(sorted_tags)
            if len(text) > 16:
                text = text[:15] + "..."
            self.mindmap_tag_filter_label_var.set(f"已选: {text}")

    def add_child_node(self):
        self.mindmap_canvas.add_child_to_selected()

    def add_sibling_node(self):
        self.mindmap_canvas.add_sibling_to_selected()

    def delete_node(self):
        self.mindmap_canvas.delete_selected_node()

    def expand_all(self):
        self.mindmap_canvas.expand_selected() # Wait, we need global expand? 
        # The canvas only expands selected.
        # Global expand needs recursive data update.
        # Refactor: Controller handles global logic.
        def _set_collapse_all(node, collapsed):
            node["_collapsed"] = collapsed
            for child in node.get("children", []):
                _set_collapse_all(child, collapsed)
        
        _set_collapse_all(self.project_manager.get_outline(), False)
        self.refresh()

    def collapse_all(self):
        outline = self.project_manager.get_outline()
        # Helper reuse?
        def _set_collapse_all(node, collapsed):
            node["_collapsed"] = collapsed
            for child in node.get("children", []):
                _set_collapse_all(child, collapsed)
        _set_collapse_all(outline, True)
        outline["_collapsed"] = False # Root always open
        self.refresh()

    def open_node_tag_selector(self, node):
        dialog = TagSelectorDialog(self.parent, self.project_manager, node.get("tags", []))
        if dialog.result is not None:
            cmd = SetNodeTagsCommand(self.project_manager, node, dialog.result)
            self.command_executor(cmd)

    # --- AI Proxies ---
    
    def generate_outline_with_ai(self):
        self.ai_controller.generate_outline(self._collect_script_text())

    def diagnose_outline_with_ai(self):
        self.ai_controller.diagnose_outline(self._collect_outline_text_for_ai())

    def ai_complete_current_node(self):
        self.ai_controller.start_outline_helper("complete_node", self.current_selected_node, self._collect_outline_text_for_ai(), self.outline_helper_hint_var.get())

    def ai_suggest_children_for_node(self):
        self.ai_controller.start_outline_helper("children_only", self.current_selected_node, self._collect_outline_text_for_ai(), self.outline_helper_hint_var.get())

    def ai_complete_whole_outline(self):
        self.ai_controller.start_outline_helper("complete_all", None, self._collect_outline_text_for_ai(), self.outline_helper_hint_var.get())

    def ai_request_branch_suggestion(self, node):
        self.ai_controller.start_outline_helper("children_only", node, self._collect_outline_text_for_ai(), "", {"count":3})

    def generate_scene_from_node_with_ai(self, node):
        self.ai_controller.generate_scene_from_node(node, self._get_outline_path(node))

    def _collect_script_text(self):
        # We need access to script content. ProjectManager has it.
        lines = []
        script = self.project_manager.get_script()
        lines.append(f"Title: {script.get('title', '')}")
        for scene in script.get("scenes", []):
            lines.append(f"Scene: {scene.get('name', '')}")
            lines.append(scene.get('content', '')[:200] + "...")
        return "\n".join(lines)

    def _collect_outline_text_for_ai(self):
        return json.dumps(self.project_manager.get_outline())

    def _get_outline_path(self, node):
        if not node: return ""
        path = []
        current = node
        while current:
            path.append(current.get("name", ""))
            parent = self.project_manager.find_parent_of_node_by_uid(self.project_manager.get_outline(), current.get("uid"))
            current = parent
        return " / ".join(reversed(path))
