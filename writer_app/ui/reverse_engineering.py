import json
import logging
import os
import threading
import time
import uuid
import difflib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from writer_app.core.reverse_engineer import ReverseEngineeringManager, AnalysisContext
from writer_app.core.commands import (
    AddCharacterCommand,
    AddWikiEntryCommand,
    AddNodeCommand,
    AddLinkCommand,
    AddTimelineEventCommand,
    AddSceneCommand,
    EditSceneCommand
)
from writer_app.core.event_bus import get_event_bus, Events

logger = logging.getLogger(__name__)

class EditableResultTree(ttk.Frame):
    """
    A wrapper around Treeview that adds:
    1. Checkboxes (simulated via a column) for selection.
    2. Double-click to edit values.
    3. Storage of the raw data objects.
    """
    def __init__(self, parent, columns, data_keys):
        super().__init__(parent)
        self.columns = ["select"] + columns
        self.data_keys = data_keys # Maps column index to dict key (excluding select)
        self.items_data = {} # map item_id -> original data dict
        
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", selectmode="extended")
        
        # Setup "Select" column
        self.tree.heading("select", text="√")
        self.tree.column("select", width=40, anchor="center")
        
        width_map = {
            "Description": 220,
            "Content": 220,
            "Analysis": 240,
            "Summary": 240,
            "Action": 220,
            "Gap": 220,
            "Motive": 160,
            "Chaos": 160,
            "Bug": 160,
            "LinkedTruth": 180,
            "Chapter": 160
        }
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width_map.get(col, 120))

        y_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        x_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.tree.bind("<Double-1>", self.on_double_click)
        # Bind single click to toggle checkbox if clicking the first column
        self.tree.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#1": # The Select column
                item_id = self.tree.identify_row(event.y)
                if item_id:
                    self.toggle_check(item_id)
                    return "break" # Prevent default selection behavior if desired

    def toggle_check(self, item_id):
        current_val = self.tree.item(item_id, "values")[0]
        new_val = "[ ]" if "[x]" in current_val else "[x]"
        
        # Preserve other values
        values = list(self.tree.item(item_id, "values"))
        values[0] = new_val
        self.tree.item(item_id, values=values)
        
        # Update internal data selection state (optional, or just rely on tree state)
        if item_id in self.items_data:
            self.items_data[item_id]["_selected"] = (new_val == "[x]")

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        
        if not item_id or column_id == "#1": 
            return

        # Map column #N to index N-1 -> data_keys index
        col_idx = int(column_id.replace("#", "")) - 2 # -1 for 0-based, -1 for select col
        
        if 0 <= col_idx < len(self.data_keys):
            key = self.data_keys[col_idx]
            current_values = self.tree.item(item_id, "values")
            current_val = current_values[col_idx + 1] # +1 skip select
            
            new_val = simpledialog.askstring("Edit", f"Edit {key}:", initialvalue=current_val, parent=self)
            if new_val is not None:
                # Update Tree
                values = list(current_values)
                values[col_idx + 1] = new_val
                self.tree.item(item_id, values=values)
                
                # Update Data
                if item_id in self.items_data:
                    self.items_data[item_id][key] = new_val

    def add_item(self, data_dict):
        # Respect existing selection state if present, default to True
        is_selected = data_dict.get("_selected", True)
        values = ["[x]" if is_selected else "[ ]"]
        
        for key in self.data_keys:
            val = data_dict.get(key, "")
            # Handle list/special types for display
            if isinstance(val, list):
                val = ", ".join(val)
            values.append(str(val))
            
        item_id = self.tree.insert("", tk.END, values=values)
        data_dict["_selected"] = is_selected
        self.items_data[item_id] = data_dict

    def get_selected_items(self):
        selected = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            if values[0] == "[x]":
                selected.append(self.items_data[item_id])
        return selected

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.items_data = {}
        
    def select_all(self, state=True):
        val = "[x]" if state else "[ ]"
        for item_id in self.tree.get_children():
            values = list(self.tree.item(item_id, "values"))
            values[0] = val
            self.tree.item(item_id, values=values)
            if item_id in self.items_data:
                self.items_data[item_id]["_selected"] = state


class ReverseEngineeringView(ttk.Frame):
    def __init__(self, parent, project_manager, ai_client, theme_manager, config_manager=None, command_executor=None, on_navigate=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.ai_client = ai_client
        self.theme_manager = theme_manager
        self.config_manager = config_manager
        self.command_executor = command_executor
        self.on_navigate = on_navigate
        self.manager = ReverseEngineeringManager(ai_client)
        
        self.loaded_text = ""
        # Storing data in the trees themselves now
        self.is_analyzing = False
        self.stop_event = threading.Event()
        self.ai_mode_enabled = True
        self._linkage_defaults = {}
        self._auto_link_default = False
        self._last_linkage_report = None
        if self.config_manager:
            self._linkage_defaults = self.config_manager.get("reverse_engineering_linkage_defaults", {}) or {}
            self._auto_link_default = bool(self.config_manager.get("reverse_engineering_auto_link", False))
        
        self.setup_ui()
        self.set_ai_mode_enabled(self.config_manager.get("ai_mode_enabled", True) if self.config_manager else True)

    def setup_ui(self):
        # 1. Top Bar: File Loading
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="反推导学习模块 - 导入文本/电子书进行AI分析").pack(side=tk.LEFT)
        
        self.file_path_var = tk.StringVar()
        entry = ttk.Entry(top_frame, textvariable=self.file_path_var, width=50)
        entry.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(top_frame, text="浏览...", command=self.browse_file).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="加载文本", command=self.load_text).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="从剪贴板导入", command=self.load_text_from_clipboard).pack(side=tk.LEFT, padx=5)

        # 2. Main Content: Split Pane
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left Panel: Controls
        left_frame = ttk.LabelFrame(paned, text="分析选项", padding=10)
        paned.add(left_frame, weight=1)
        
        self.vars = {
            "characters": tk.BooleanVar(value=True),
            "outline": tk.BooleanVar(value=True),
            "timeline": tk.BooleanVar(value=False),
            "wiki": tk.BooleanVar(value=True),
            "relationships": tk.BooleanVar(value=False),
            "style": tk.BooleanVar(value=False),
            "summary": tk.BooleanVar(value=False)
        }
        
        ttk.Checkbutton(left_frame, text="提取角色 (Characters)", variable=self.vars["characters"]).pack(anchor="w", pady=2)
        ttk.Checkbutton(left_frame, text="提取大纲 (Outline)", variable=self.vars["outline"]).pack(anchor="w", pady=2)
        ttk.Checkbutton(left_frame, text="提取双线时间轴 (Dual Timeline)", variable=self.vars["timeline"]).pack(anchor="w", pady=2)
        ttk.Checkbutton(left_frame, text="提取设定 (Wiki)", variable=self.vars["wiki"]).pack(anchor="w", pady=2)
        ttk.Checkbutton(left_frame, text="提取关系/势力 (Relationships)", variable=self.vars["relationships"]).pack(anchor="w", pady=2)
        ttk.Checkbutton(left_frame, text="分析文笔 (Style)", variable=self.vars["style"]).pack(anchor="w", pady=2)
        ttk.Checkbutton(left_frame, text="剧情回顾 (Summary)", variable=self.vars["summary"]).pack(anchor="w", pady=2)
        
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # 增量分析选项
        self.incremental_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            left_frame,
            text="增量分析（跳过已分析章节）",
            variable=self.incremental_var
        ).pack(anchor="w", pady=2)

        # 长上下文选项（核心改进）
        self.context_var = tk.BooleanVar(value=True)
        context_check = ttk.Checkbutton(
            left_frame,
            text="长上下文模式（推荐）",
            variable=self.context_var
        )
        context_check.pack(anchor="w", pady=2)

        # 添加提示标签
        context_hint = ttk.Label(
            left_frame,
            text="  ↳ 累积角色/设定/摘要，提高跨章节识别",
            font=("", 8),
            foreground="gray"
        )
        context_hint.pack(anchor="w")

        self.request_timeout_var = tk.IntVar(
            value=self.config_manager.get("reverse_engineering_request_timeout", 120) if self.config_manager else 120
        )
        timeout_frame = ttk.Frame(left_frame)
        timeout_frame.pack(fill=tk.X, pady=2)
        ttk.Label(timeout_frame, text="请求超时(秒)").pack(side=tk.LEFT)
        ttk.Entry(timeout_frame, textvariable=self.request_timeout_var, width=6).pack(side=tk.LEFT, padx=5)

        self.retry_var = tk.IntVar(
            value=self.config_manager.get("reverse_engineering_max_retries", self.manager.max_retries)
            if self.config_manager else self.manager.max_retries
        )
        retry_frame = ttk.Frame(left_frame)
        retry_frame.pack(fill=tk.X, pady=2)
        ttk.Label(retry_frame, text="重试次数").pack(side=tk.LEFT)
        ttk.Entry(retry_frame, textvariable=self.retry_var, width=6).pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(left_frame, text="开始AI分析", command=self.start_analysis, state=tk.DISABLED)
        self.start_btn.pack(fill=tk.X, pady=5)

        self.stop_btn = ttk.Button(left_frame, text="停止", command=self.stop_analysis, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=5)

        # 分析进度标签
        self.progress_label = ttk.Label(left_frame, text="", font=("", 8))
        self.progress_label.pack(anchor="w")

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(left_frame, text="操作:").pack(anchor="w")

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="全选", command=lambda: self.toggle_all_selection(True)).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="全不选", command=lambda: self.toggle_all_selection(False)).pack(side=tk.LEFT, expand=True, fill=tk.X)

        ttk.Button(left_frame, text="应用选定结果到项目", command=self.apply_results).pack(fill=tk.X, pady=5)

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        linkage_frame = ttk.LabelFrame(left_frame, text="模块联动", padding=5)
        linkage_frame.pack(fill=tk.X, pady=5)
        self.auto_link_var = tk.BooleanVar(value=self._auto_link_default)
        ttk.Checkbutton(
            linkage_frame,
            text="自动联动（使用上次设置）",
            variable=self.auto_link_var,
            command=self._save_auto_link_setting
        ).pack(anchor="w")
        ttk.Button(linkage_frame, text="联动向导", command=self.open_linkage_wizard).pack(fill=tk.X, pady=2)
        ttk.Button(linkage_frame, text="联动复核", command=self.open_linkage_review).pack(fill=tk.X, pady=2)

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Session Management
        session_frame = ttk.LabelFrame(left_frame, text="分析会话", padding=5)
        session_frame.pack(fill=tk.X, pady=5)
        ttk.Button(session_frame, text="保存当前分析结果", command=self.save_session).pack(fill=tk.X, pady=2)
        ttk.Button(session_frame, text="加载上次分析结果", command=self.load_session).pack(fill=tk.X, pady=2)
        ttk.Button(session_frame, text="清除分析缓存", command=self.clear_analysis_cache).pack(fill=tk.X, pady=2)

        # Right Panel: Results Preview
        right_frame = ttk.LabelFrame(paned, text="分析结果预览 (双击修改，勾选确认)", padding=10)
        paned.add(right_frame, weight=3)
        
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.result_trees = {}
        
        self.create_result_tab("角色", "characters", ["Name", "Role", "Description"], ["name", "role", "description"])
        self.create_result_tab("大纲", "outline", ["Title", "Content"], ["name", "content"])
        self.create_result_tab(
            "双线时间轴",
            "timeline",
            ["Type", "Time", "Name", "Location", "Action", "Motive", "Chaos", "Gap", "Bug", "LinkedTruth", "Chapter"],
            ["type", "timestamp", "name", "location", "action", "motive", "chaos", "gap", "bug", "linked_truth_name", "chapter_title"]
        )
        self.create_result_tab("设定", "wiki", ["Name", "Category", "Content"], ["name", "category", "content"])
        self.create_result_tab(
            "关系",
            "relationships",
            ["Source", "Target", "Type", "Relation", "Description", "Chapter"],
            ["source", "target", "target_type", "label", "description", "chapter_title"]
        )
        self.create_result_tab("文笔", "style", ["Type", "Analysis"], ["name", "content"])
        self.create_result_tab("回顾", "summary", ["Section", "Summary"], ["chapter_title", "content"])

        # Bottom: Log & Progress
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, side=tk.TOP)
        
        self.log_text = tk.Text(bottom_frame, height=5, font=("Consolas", 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.X, side=tk.BOTTOM)

    def create_result_tab(self, title, key, col_names, data_keys):
        # Wrapper frame for the notebook tab
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        
        # Instantiate our custom Tree
        tree_widget = EditableResultTree(frame, col_names, data_keys)
        tree_widget.pack(fill=tk.BOTH, expand=True)
        
        self.result_trees[key] = tree_widget

    def toggle_all_selection(self, state):
        current_tab_idx = self.notebook.index(self.notebook.select())
        # The notebook tabs are in creation order. 
        # self.result_trees is a dict, order might vary in py<3.7 but we inserted in order.
        # Safer to map index to keys.
        keys = ["characters", "outline", "timeline", "wiki", "relationships", "style", "summary"]
        if 0 <= current_tab_idx < len(keys):
            key = keys[current_tab_idx]
            if key in self.result_trees:
                self.result_trees[key].select_all(state)

    def log(self, message):
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_progress(self, value):
        self.after(0, self.progress_var.set, value)

    def _save_auto_link_setting(self):
        if self.config_manager:
            self.config_manager.set("reverse_engineering_auto_link", bool(self.auto_link_var.get()))
            self.config_manager.save()

    def _serialize_linkage_defaults(self, vars_dict):
        defaults = {}
        for key, value in vars_dict.items():
            if hasattr(value, "get"):
                defaults[key] = bool(value.get())
            else:
                defaults[key] = bool(value)
        return defaults

    def _save_linkage_defaults(self, defaults):
        self._linkage_defaults = dict(defaults or {})
        if self.config_manager is not None:
            self.config_manager.set("reverse_engineering_linkage_defaults", self._linkage_defaults)
            self.config_manager.save()

    def _get_linkage_defaults(self):
        return dict(self._linkage_defaults or {})

    def open_linkage_wizard(self):
        sel_outline = self.result_trees["outline"].get_selected_items()
        sel_timeline = self.result_trees["timeline"].get_selected_items()
        if not sel_outline and not sel_timeline:
            messagebox.showinfo("提示", "请先选择大纲或时间轴条目。")
            return
        self._show_module_linkage_wizard(sel_outline, sel_timeline, defaults=self._get_linkage_defaults())

    def open_linkage_review(self):
        report = self._collect_linkage_issues()
        if report.get("unlinked_truth_count", 0) == 0 and report.get("unlinked_lie_count", 0) == 0:
            messagebox.showinfo("联动复核", "当前没有未关联项。")
            return
        self._show_linkage_review_dialog(report)

    def _build_relationship_keyframes(self, imported_links, min_changes):
        rels = self.project_manager.get_relationships()
        if "snapshots" not in rels:
            rels["snapshots"] = []

        def _iter_chapter_titles(link):
            titles = link.get("chapter_titles")
            if isinstance(titles, list):
                return [t for t in titles if t]
            chapter_title = link.get("chapter_title")
            if chapter_title:
                return [chapter_title]
            return []

        chapter_sequence = getattr(self, "_last_chapter_sequence", []) or []
        seen_chapters = {c for c in chapter_sequence}
        for link in imported_links:
            for chapter_title in _iter_chapter_titles(link):
                if chapter_title and chapter_title not in seen_chapters:
                    chapter_sequence.append(chapter_title)
                    seen_chapters.add(chapter_title)

        outline_by_chapter = {}
        sel_outline = self.result_trees["outline"].get_selected_items()
        for item in sel_outline:
            chap = item.get("chapter_title")
            name = item.get("name")
            if not chap or not name:
                continue
            outline_by_chapter.setdefault(chap, []).append(name)

        links_by_chapter = {}
        for link in imported_links:
            chapters = _iter_chapter_titles(link)
            if not chapters:
                continue
            for chap in chapters:
                links_by_chapter.setdefault(chap, []).append(link)

        cumulative = {}
        last_snapshot_idx = -1
        snapshot_count = 0

        for idx, chap in enumerate(chapter_sequence):
            changed = 0
            for link in links_by_chapter.get(chap, []):
                key = (link.get("source"), link.get("target"), link.get("target_type", "character"))
                if key not in cumulative:
                    cumulative[key] = link
                    changed += 1

            if changed >= min_changes:
                start_idx = last_snapshot_idx + 1
                end_idx = idx
                chapter_span = end_idx - start_idx + 1

                outline_names = []
                for c in chapter_sequence[start_idx:end_idx + 1]:
                    outline_names.extend(outline_by_chapter.get(c, []))
                unique_outline = []
                for name in outline_names:
                    if name not in unique_outline:
                        unique_outline.append(name)

                outline_label = "无"
                if unique_outline:
                    outline_label = " / ".join(unique_outline[:3])
                    if len(unique_outline) > 3:
                        outline_label += " ..."

                snap_name = f"章节 {start_idx + 1}-{end_idx + 1}（{chapter_span}章）| 大纲: {outline_label}"
                rels["snapshots"].append({
                    "name": snap_name,
                    "links": list(cumulative.values()),
                    "timestamp": time.time()
                })
                last_snapshot_idx = idx
                snapshot_count += 1

        if snapshot_count:
            self.project_manager.mark_modified("relationships")
            messagebox.showinfo("关系快照", f"已生成 {snapshot_count} 个关键帧快照。")
        else:
            messagebox.showinfo("关系快照", "未达到关键帧阈值，未生成快照。")

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("E-books & Text", "*.epub *.txt"), ("All Files", "*.*")])
        if file_path:
            self.file_path_var.set(file_path)
            self.load_text()

    def load_text(self):
        path = self.file_path_var.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "File not found.")
            return

        try:
            self.log(f"Loading {path}...")
            self.loaded_text = self.manager.load_file(path)
            if not self.loaded_text:
                self.log("加载结果为空，请确认文件内容是否有效。")
                messagebox.showwarning("Empty", "文件内容为空，无法开始分析。")
                self.start_btn.configure(state=tk.DISABLED)
                return

            self.log(f"Loaded {len(self.loaded_text)} characters.")
            if self.ai_mode_enabled:
                self.start_btn.configure(state=tk.NORMAL)
        except Exception as e:
            self.log(f"Error loading file: {e}")
            logger.exception("Failed to load file for reverse engineering: %s", path)
            messagebox.showerror("Error", str(e))

    def load_text_from_clipboard(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Empty", "剪贴板为空，无法导入。")
            return

        if not text or not text.strip():
            messagebox.showwarning("Empty", "剪贴板内容为空，无法导入。")
            return

        self.loaded_text = text
        self.file_path_var.set("【剪贴板】")
        self.log(f"Loaded {len(self.loaded_text)} characters from clipboard.")
        if self.ai_mode_enabled:
            self.start_btn.configure(state=tk.NORMAL)

    def start_analysis(self):
        if not self.ai_mode_enabled:
            messagebox.showinfo("提示", "当前为非AI模式，AI分析不可用。")
            return
        if not self.loaded_text:
            return

        ai_config = self._get_ai_config()
        if not ai_config.get("api_url") or not ai_config.get("model"):
            self.log("AI 配置缺失，请先在设置中填写接口 URL 和模型。")
            messagebox.showwarning("Config", "Please configure AI settings (URL and Model) in Settings first.")
            return
        ai_config.setdefault("api_key", "")

        logger.info("Starting reverse engineering analysis for %s", self.file_path_var.get())

        self._apply_runtime_settings()

        self.is_analyzing = True
        self.stop_event.clear()
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # Clear previous results
        for key in self.result_trees:
            self.result_trees[key].clear()

        thread = threading.Thread(target=self._run_analysis, args=(ai_config,))
        thread.daemon = True
        thread.start()

    def stop_analysis(self):
        self.stop_event.set()
        self.is_analyzing = False
        self.log("Stopping analysis...")

    def _get_ai_config(self):
        if self.config_manager and hasattr(self.config_manager, "get_ai_config"):
            return self.config_manager.get_ai_config()
        return {}

    def _apply_runtime_settings(self):
        try:
            timeout_val = int(self.request_timeout_var.get())
        except Exception:
            timeout_val = 120
        if timeout_val < 10:
            timeout_val = 10

        try:
            retries_val = int(self.retry_var.get())
        except Exception:
            retries_val = self.manager.max_retries
        if retries_val < 0:
            retries_val = 0

        self._analysis_request_timeout = timeout_val
        self.manager.max_retries = retries_val

        if self.config_manager:
            self.config_manager.set("reverse_engineering_request_timeout", timeout_val)
            self.config_manager.set("reverse_engineering_max_retries", retries_val)
            self.config_manager.save()

    def set_ai_mode_enabled(self, enabled: bool):
        self.ai_mode_enabled = bool(enabled)
        if not self.ai_mode_enabled:
            self.start_btn.pack_forget()
            self.stop_btn.pack_forget()
            # Also hide incremental and context options
            self.progress_label.config(text="非AI模式下不可用")
        else:
            # Re-pack in order
            self.start_btn.pack(fill=tk.X, pady=5)
            self.stop_btn.pack(fill=tk.X, pady=5)
            self.progress_label.config(text="")
            if self.loaded_text:
                self.start_btn.configure(state=tk.NORMAL)

    def _execute_command(self, command):
        if self.command_executor:
            return self.command_executor(command)
        return command.execute()

    def _run_analysis(self, ai_config):
        """
        改进的分析流程：支持长上下文累积。

        核心改进：
        1. 按章节顺序处理（而非按分析类型分组）
        2. 每个章节处理后更新累积上下文（已知角色、设定、滚动摘要）
        3. 将上下文传递给后续章节的分析，提高跨章节的识别准确性
        """
        # 1. 加载并分割文本
        path = self.file_path_var.get()
        structured_chapters = self.manager.load_file_structured(path)

        if len(structured_chapters) == 1 and structured_chapters[0]["title"] == "Full Text":
            raw_chunks = self.manager.split_text(structured_chapters[0]["content"])
            processing_units = [{"title": f"Chunk {i+1}", "content": c} for i, c in enumerate(raw_chunks)]
        else:
            processing_units = []
            for chap in structured_chapters:
                sub_chunks = self.manager.split_text(chap["content"])
                for i, sub in enumerate(sub_chunks):
                    title = chap["title"]
                    if len(sub_chunks) > 1:
                        title += f" ({i+1})"
                    processing_units.append({"title": title, "content": sub})
        self._last_chapter_sequence = [u["title"] for u in processing_units]

        # 获取选中的分析类型
        selected_types = [k for k, v in self.vars.items() if v.get()]
        use_incremental = self.incremental_var.get()
        use_context = self.context_var.get()  # 是否使用长上下文

        if not selected_types:
            self.log("Warning: No analysis options selected.")
            self.is_analyzing = False
            self.after(0, lambda: self.start_btn.configure(state=tk.NORMAL))
            self.after(0, lambda: self.stop_btn.configure(state=tk.DISABLED))
            return

        # 2. 创建累积上下文（如果启用）
        context = self.manager.create_analysis_context() if use_context else None

        # 尝试从已保存的会话恢复上下文
        if use_context and hasattr(self, '_saved_context') and self._saved_context:
            context = self.manager.import_context(self._saved_context)
            self.log(f"Restored context: {len(context.known_characters)} characters, "
                    f"{len(context.known_entities)} entities")

        # 3. 计算总任务数（按章节 x 分析类型）
        total_units = len(processing_units) * len(selected_types)
        if use_context:
            # 额外的摘要生成任务
            total_units += len(processing_units)

        self.log(f"Processing {len(processing_units)} chapters × {len(selected_types)} analysis types")
        if use_context:
            self.log("Long context mode enabled: accumulating characters, entities, and summaries")

        current_step = 0
        global_results_buffer = {k: [] for k in self.vars}
        skipped_count = 0

        # 4. 按章节顺序处理（核心改进）
        for unit_idx, unit in enumerate(processing_units):
            if self.stop_event.is_set():
                break

            unit_title = unit["title"]
            unit_content = unit["content"]
            content_hash = self.manager._compute_hash(unit_content)

            self.log(f"\n=== Chapter {unit_idx + 1}/{len(processing_units)}: {unit_title} ===")

            # 显示当前上下文状态
            if use_context and context:
                ctx_info = f"Context: {len(context.known_characters)} chars, {len(context.known_entities)} entities"
                self.log(f"  {ctx_info}")

            chapter_results = {}  # 本章节的分析结果

            # 4a. 对当前章节执行所有选中的分析类型
            any_analysis_done = False
            for analysis_type in selected_types:
                if self.stop_event.is_set():
                    break

                # 增量检查
                if use_incremental:
                    if analysis_type not in self.manager._analyzed_hashes:
                        self.manager._analyzed_hashes[analysis_type] = set()
                    if content_hash in self.manager._analyzed_hashes[analysis_type]:
                        skipped_count += 1
                        current_step += 1
                        progress = (current_step / total_units) * 100
                        self._set_progress(progress)
                        continue

                self.log(f"  [{analysis_type}] Analyzing...")

                try:
                    # 使用累积上下文进行分析
                    result = self.manager.analyze_chunk(
                        unit_content,
                        analysis_type,
                        ai_config,
                        context=context,  # 传递累积上下文
                        request_timeout=getattr(self, "_analysis_request_timeout", None)
                    )

                    if result is not None:
                        for r in result:
                            r["chapter_title"] = unit_title
                        global_results_buffer[analysis_type].append(result)
                        chapter_results[analysis_type] = result

                        item_count = len(result)
                        if item_count:
                            self.log(f"    ✓ Found {item_count} items")
                        else:
                            self.log("    ⚠ No items found")

                        # 标记为已分析
                        self.manager.mark_analyzed(content_hash, analysis_type)
                        any_analysis_done = True
                    else:
                        self.log("    ✗ No valid JSON output")

                except Exception as e:
                    self.log(f"    ✗ Error: {e}")

                current_step += 1
                progress = (current_step / total_units) * 100
                self._set_progress(progress)

            if self.stop_event.is_set():
                break

            # 4b. 更新累积上下文（基于本章节的分析结果）
            if use_context and context:
                chapter_summary = self.manager.get_cached_summary(content_hash)
                if any_analysis_done and not chapter_summary:
                    self.log("  [context] Generating chapter summary...")
                    chapter_summary = self.manager.generate_chapter_summary(
                        unit_content, unit_title, ai_config
                    )
                    if chapter_summary:
                        self.log(f"    ? Summary: {chapter_summary[:80]}...")

                if not chapter_summary and "summary" in chapter_results:
                    summary_items = chapter_results.get("summary", [])
                    if isinstance(summary_items, list) and summary_items:
                        first = summary_items[0]
                        if isinstance(first, dict):
                            chapter_summary = (first.get("content") or "")[:500].strip()
                        elif isinstance(first, list) and first:
                            item = first[0]
                            if isinstance(item, dict):
                                chapter_summary = (item.get("content") or "")[:500].strip()

                if chapter_summary:
                    self.manager.set_cached_summary(content_hash, chapter_summary)

                context_results = chapter_results
                if "summary" in chapter_results:
                    context_results = dict(chapter_results)
                    context_results.pop("summary", None)

                if chapter_summary or context_results:
                    self.manager.update_context_from_results(
                        context, context_results, unit_title, chapter_summary
                    )

                current_step += 1
                progress = (current_step / total_units) * 100
                self._set_progress(progress)

            # 更新进度标签
            self.after(0, self._update_progress_label)

        # 5. 保存上下文供后续使用
        if use_context and context:
            self._saved_context = self.manager.export_context(context)
            self.log(f"\nContext saved: {len(context.known_characters)} characters, "
                    f"{len(context.known_entities)} entities, "
                    f"{len(context.chapter_summaries)} chapter summaries")

        if skipped_count > 0:
            self.log(f"Skipped {skipped_count} already-analyzed sections (incremental mode)")

        # 6. 合并结果
        self.log("\nMerging global results...")

        for key in global_results_buffer:
            if not self.vars[key].get():
                continue

            if key in ["summary", "style"]:
                flat_list = []
                for batch in global_results_buffer[key]:
                    flat_list.extend(batch)
                merged_data = flat_list
            else:
                merged_data = self.manager.merge_results(global_results_buffer[key], key)

            # Update UI on main thread
            self.after(0, self._update_tree, key, merged_data)

        self.is_analyzing = False
        self.after(0, lambda: self.start_btn.configure(state=tk.NORMAL))
        self.after(0, lambda: self.stop_btn.configure(state=tk.DISABLED))
        self.log("\n=== Analysis Complete ===")

    def _update_tree(self, key, data):
        tree = self.result_trees[key]
        tree.clear()
        for item in data:
            tree.add_item(item)

    def apply_results(self):
        """Injects selected analyzed data into the current project."""
        if not messagebox.askyesno("Confirm", "Import checked items to project?"):
            return

        count = 0
        
        # 1. Characters
        sel_chars = self.result_trees["characters"].get_selected_items()
        if sel_chars:
            current_chars = self.project_manager.get_characters()
            existing_names = {c["name"] for c in current_chars}
            
            for char in sel_chars:
                name = char.get("name", "").strip()
                if not name or name in existing_names:
                    continue
                new_char = {
                    "name": name,
                    "description": char.get("description", ""),
                    "tags": char.get("tags", []),
                    "role": char.get("role", "")
                }
                if self._execute_command(AddCharacterCommand(self.project_manager, new_char, "反推导导入角色")):
                    existing_names.add(name)
                    count += 1

        # 2. Wiki
        sel_wiki = self.result_trees["wiki"].get_selected_items()
        if sel_wiki:
            current_entries = self.project_manager.get_world_entries()
            existing_entries = {e["name"] for e in current_entries}
            
            for entry in sel_wiki:
                name = entry.get("name", "").strip()
                if not name or name in existing_entries:
                    continue
                new_entry = {
                    "name": name,
                    "category": entry.get("category", "未分类"),
                    "content": entry.get("content", ""),
                    "iceberg_depth": "surface",
                    "image_path": ""
                }
                if self._execute_command(AddWikiEntryCommand(self.project_manager, new_entry, "反推导导入设定")):
                    existing_entries.add(name)
                    count += 1

        # 3. Outline
        sel_outline = self.result_trees["outline"].get_selected_items()
        if sel_outline:
            mount_to_chars = messagebox.askyesno("Outline", "Detect characters in events and add to Character Timeline?")

            root = self.project_manager.get_outline()
            new_branch = {
                "name": "反推导分析 - 大纲",
                "uid": self.project_manager._gen_uid(),
                "children": []
            }

            # 按章节分组，保持原始顺序
            chapter_order = []  # 记录章节出现顺序
            chapters_dict = {}  # 章节名 -> 事件列表

            for item in sel_outline:
                chapter = item.get("chapter_title", "未分类章节")
                if chapter not in chapters_dict:
                    chapter_order.append(chapter)
                    chapters_dict[chapter] = []
                chapters_dict[chapter].append(item)

            # 按章节顺序创建层级结构
            for chapter_title in chapter_order:
                events = chapters_dict[chapter_title]

                # 创建章节节点
                chapter_node = {
                    "name": chapter_title,
                    "content": f"包含 {len(events)} 个事件",
                    "uid": self.project_manager._gen_uid(),
                    "children": []
                }

                # 添加章节下的事件节点
                for item in events:
                    event_node = {
                        "name": item.get("name", "Event"),
                        "content": item.get("content", ""),
                        "uid": self.project_manager._gen_uid(),
                        "children": []
                    }
                    chapter_node["children"].append(event_node)

                    if mount_to_chars:
                        chars = item.get("characters", [])
                        if not isinstance(chars, list):
                            chars = []

                        # 如果AI没有返回characters字段，尝试从事件内容中匹配已有角色名
                        if not chars:
                            event_text = f"{item.get('name', '')} {item.get('content', '')}"
                            existing_chars = self.project_manager.get_characters()
                            for char in existing_chars:
                                char_name = char.get("name", "")
                                if char_name and char_name in event_text:
                                    chars.append(char_name)

                        for c_name in chars:
                            event_data = {
                                "time": f"{chapter_title}",
                                "summary": f"{item.get('name')}: {item.get('content')}",
                                "type": "剧情事件",
                                "source": "Reverse Engineering"
                            }
                            self.project_manager.add_character_event(c_name, event_data)

                new_branch["children"].append(chapter_node)

            if self._execute_command(AddNodeCommand(self.project_manager, root.get("uid"), new_branch, "反推导导入大纲")):
                count += 1
            
        # 4. Dual Timeline (使用 Command 模式)
        sel_timeline = self.result_trees["timeline"].get_selected_items()
        if sel_timeline:
            # 首先导入所有真相事件并记录名称到UID的映射
            truth_name_to_uid = {}
            added_events = 0
            def _normalize_truth_key(name):
                return "".join(str(name).split()).lower()

            # 第一轮：导入真相事件
            for item in sel_timeline:
                event_type = item.get("type", "truth").lower()
                if event_type != "truth":
                    continue

                event_data = {
                    "name": item.get("name", "未命名事件"),
                    "timestamp": item.get("timestamp", ""),
                    "location": item.get("location", ""),
                    "action": item.get("action", item.get("description", "")),
                    "motive": item.get("motive", ""),
                    "chaos": item.get("chaos", ""),
                    "linked_scene_uid": ""  # 使用 UID 而非索引
                }

                cmd = AddTimelineEventCommand(
                    self.project_manager,
                    "truth",
                    event_data,
                    "反推导导入真相事件"
                )
                if self._execute_command(cmd):
                    truth_name_to_uid[_normalize_truth_key(event_data["name"])] = cmd.added_uid
                    added_events += 1

            # 第二轮：导入谎言事件并尝试关联真相事件
            for item in sel_timeline:
                event_type = item.get("type", "truth").lower()
                if event_type != "lie":
                    continue

                # 尝试查找关联的真相事件
                linked_truth_name = item.get("linked_truth_name", "")
                linked_truth_key = _normalize_truth_key(linked_truth_name)
                linked_truth_uid = truth_name_to_uid.get(linked_truth_key, "")
                if not linked_truth_uid and linked_truth_key:
                    matches = {
                        uid for key, uid in truth_name_to_uid.items()
                        if linked_truth_key in key or key in linked_truth_key
                    }
                    if len(matches) == 1:
                        linked_truth_uid = matches.pop()

                event_data = {
                    "name": item.get("name", "未命名谎言"),
                    "timestamp": item.get("timestamp", ""),
                    "motive": item.get("motive", "反推导提取"),
                    "gap": item.get("gap", item.get("description", "")),
                    "bug": item.get("bug", ""),
                    "linked_truth_event_uid": linked_truth_uid
                }

                cmd = AddTimelineEventCommand(
                    self.project_manager,
                    "lie",
                    event_data,
                    "反推导导入谎言事件"
                )
                if self._execute_command(cmd):
                    added_events += 1

            count += added_events

        # 5. Relationships & Factions (完善整合)
        sel_rels = self.result_trees["relationships"].get_selected_items()
        if sel_rels:
            factions = self.project_manager.get_factions()
            faction_names = {f["name"]: f["uid"] for f in factions}
            rels = self.project_manager.get_relationships()
            rels.setdefault("relationship_events", [])
            relationship_events = rels["relationship_events"]

            # 确保角色有UID（用于势力矩阵关联）
            characters = self.project_manager.get_characters()
            char_name_to_uid = {}
            existing_char_names = set()
            renamed_char_uids = {}
            for char in characters:
                if "uid" not in char or not char["uid"]:
                    new_uid = self.project_manager._gen_uid()
                    renamed_char_uids[char["name"]] = new_uid
                    char["uid"] = new_uid
                char_name_to_uid[char["name"]] = char["uid"]
                existing_char_names.add(char["name"])

            def ensure_character(name):
                if not name or name in existing_char_names:
                    return
                new_char = {
                    "name": name,
                    "uid": self.project_manager._gen_uid(),
                    "description": "",
                    "tags": ["反推导"],
                    "role": ""
                }
                if self._execute_command(AddCharacterCommand(self.project_manager, new_char, "反推导关系补充角色")):
                    existing_char_names.add(name)
                    char_name_to_uid[name] = new_char["uid"]

            imported_links = []
            events_added = False
            frame_ids = {}
            batch_frame_id = self.project_manager._gen_uid()

            def _build_snapshot_link(base_link, source_link):
                snapshot_link = dict(base_link)
                chapter_titles = source_link.get("chapter_titles")
                if isinstance(chapter_titles, list) and chapter_titles:
                    snapshot_link["chapter_titles"] = list(chapter_titles)
                chapter_title = source_link.get("chapter_title")
                if chapter_title:
                    snapshot_link["chapter_title"] = chapter_title
                return snapshot_link

            def _iter_chapter_titles(source_link):
                chapter_titles = source_link.get("chapter_titles")
                if isinstance(chapter_titles, list) and chapter_titles:
                    return [t for t in chapter_titles if t]
                chapter_title = source_link.get("chapter_title")
                if chapter_title:
                    return [chapter_title]
                return []

            def _get_frame_id(chapter_title):
                if not chapter_title:
                    return batch_frame_id
                if chapter_title not in frame_ids:
                    frame_ids[chapter_title] = self.project_manager._gen_uid()
                return frame_ids[chapter_title]

            def _append_events_for_link(new_link, source_link, target_type):
                nonlocal events_added
                event_uids = []
                frame_id_list = []
                chapters = _iter_chapter_titles(source_link)
                if not chapters:
                    chapters = [""]

                for chapter_title in chapters:
                    frame_id = _get_frame_id(chapter_title)
                    event = {
                        "uid": self.project_manager._gen_uid(),
                        "source": new_link.get("source", ""),
                        "target": new_link.get("target", ""),
                        "target_type": target_type,
                        "label": new_link.get("label", ""),
                        "description": new_link.get("description", ""),
                        "chapter_title": chapter_title,
                        "frame_id": frame_id,
                        "created_at": time.time(),
                        "origin": "reverse_engineering"
                    }
                    outline_ref_uid = source_link.get("outline_ref_uid")
                    if outline_ref_uid:
                        event["outline_ref_uid"] = outline_ref_uid
                    relationship_events.append(event)
                    event_uids.append(event["uid"])
                    if frame_id and frame_id not in frame_id_list:
                        frame_id_list.append(frame_id)

                if event_uids:
                    new_link["event_uids"] = event_uids
                if frame_id_list:
                    new_link["event_frame_ids"] = frame_id_list
                events_added = True

            for link in sel_rels:
                src = link.get("source", "").strip()
                tgt = link.get("target", "").strip()
                tgt_type = (link.get("target_type", "character") or "character").strip().lower()
                if tgt_type not in ("character", "faction"):
                    tgt_type = "character"
                label = link.get("label", "")
                description = link.get("description", "")

                if not src or not tgt:
                    continue

                ensure_character(src)

                if tgt_type == "faction":
                    # 1. 创建势力（如果不存在）
                    if tgt not in faction_names:
                        new_uid = self.project_manager.add_faction(tgt)
                        faction_names[tgt] = new_uid

                    faction_uid = faction_names[tgt]

                    # 2. 添加可视化关系链接
                    new_link = {
                        "source": src,
                        "target": tgt,
                        "label": f"{label} (势力)",
                        "color": "#FF8800",
                        "description": description,
                        "target_type": "faction"
                    }
                    if self._execute_command(AddLinkCommand(self.project_manager, new_link)):
                        _append_events_for_link(new_link, link, "faction")
                        imported_links.append(_build_snapshot_link(new_link, link))

                    # 3. 更新势力成员信息
                    # 查找角色并关联到势力
                    if src in char_name_to_uid:
                        char_uid = char_name_to_uid[src]
                        # 更新势力的成员列表（存储在势力的描述或专用字段中）
                        for faction in factions:
                            if faction["uid"] == faction_uid:
                                if "members" not in faction:
                                    faction["members"] = []
                                member_entry = {
                                    "char_uid": char_uid,
                                    "char_name": src,
                                    "role": label
                                }
                                # 避免重复添加
                                existing_uids = [m.get("char_uid") for m in faction["members"]]
                                if char_uid not in existing_uids:
                                    faction["members"].append(member_entry)
                                break
                        self.project_manager.mark_modified("factions")

                    # 4. 同步到Wiki
                    self.project_manager.sync_to_wiki(
                        tgt, "势力", "update",
                        content=f"成员：{src}（{label}）\n{description}"
                    )

                else:
                    ensure_character(tgt)
                    # 普通角色关系
                    new_link = {
                        "source": src,
                        "target": tgt,
                        "label": label,
                        "color": "#666666",
                        "description": description,
                        "target_type": "character"
                    }
                    if self._execute_command(AddLinkCommand(self.project_manager, new_link)):
                        _append_events_for_link(new_link, link, "character")
                        imported_links.append(_build_snapshot_link(new_link, link))

            self.project_manager.mark_modified("script")  # 因为更新了角色UID
            if events_added:
                self.project_manager.mark_modified("relationships")
            count += len(sel_rels)

            if imported_links:
                # 默认自动生成关键帧快照（提高可发现性）
                auto_generate = messagebox.askyesno(
                    "关系快照",
                    f"检测到 {len(imported_links)} 条关系。\n是否根据章节自动生成关键帧快照？\n（推荐：便于查看关系演变）"
                )
                if auto_generate:
                    min_changes = simpledialog.askinteger(
                        "关键帧阈值",
                        "每章节累积多少条新关系时生成快照？\n（建议：1-3条，可捕捉更多变化点）",
                        initialvalue=1,
                        minvalue=1
                    )
                    if min_changes:
                        self._build_relationship_keyframes(imported_links, min_changes)
                else:
                    # 即使不生成多帧，也创建一个"全部关系"快照
                    rels = self.project_manager.get_relationships()
                    if "snapshots" not in rels:
                        rels["snapshots"] = []
                    rels["snapshots"].append({
                        "name": "反推导导入 - 完整关系图",
                        "links": imported_links,
                        "timestamp": time.time()
                    })
                    self.project_manager.mark_modified("relationships")

            if renamed_char_uids:
                rels = self.project_manager.get_relationships()
                layout = rels.get("evidence_layout", {})
                updated_layout = {}
                for key, pos in layout.items():
                    if key in renamed_char_uids:
                        updated_layout[renamed_char_uids[key]] = pos
                    else:
                        updated_layout[key] = pos
                rels["evidence_layout"] = updated_layout

                ev_links = rels.get("evidence_links", [])
                for link in ev_links:
                    src = link.get("source")
                    tgt = link.get("target")
                    if src in renamed_char_uids:
                        link["source"] = renamed_char_uids[src]
                    if tgt in renamed_char_uids:
                        link["target"] = renamed_char_uids[tgt]

                self.project_manager.mark_modified("evidence")

        # 6. Style
        sel_style = self.result_trees["style"].get_selected_items()
        if sel_style:
            style_texts = [item.get('content', '') for item in sel_style]
            
            # Save Idea
            for txt in style_texts:
                self.project_manager.add_idea(f"【文笔分析】\n{txt}", tags=["反推导", "文笔"])
            
            # Update Preset
            full_style = "\n".join(style_texts)
            if "ai_context" not in self.project_manager.project_data["meta"]:
                self.project_manager.project_data["meta"]["ai_context"] = {}
            
            # Append or Replace? Let's Append to not lose previous manual edits if any, or just overwrite?
            # Preset implies "The current style". Overwrite is probably expected for "Apply".
            self.project_manager.project_data["meta"]["ai_context"]["style_preset"] = full_style
            
            self.project_manager.mark_modified("ideas")
            self.project_manager.mark_modified("meta")
            count += 1

        # 7. Summary
        sel_summary = self.result_trees["summary"].get_selected_items()
        if sel_summary:
            full_recap = "\n\n".join([f"### {s.get('chapter_title')}\n{s.get('content')}" for s in sel_summary])
            
            if "ai_context" not in self.project_manager.project_data["meta"]:
                self.project_manager.project_data["meta"]["ai_context"] = {}
            
            self.project_manager.project_data["meta"]["ai_context"]["summary_recap"] = full_recap
            self.project_manager.mark_modified("meta")
            self.project_manager.add_idea(f"【剧情前情提要】\n{full_recap}", tags=["反推导", "回顾"])
            count += 1

        # 8. 模块联动向导 - 询问是否生成场景和建立关联
        if count > 0:
            self._post_import_linkage(sel_outline, sel_timeline)
        else:
            messagebox.showinfo("Success", f"Successfully imported {count} items.")

    def _post_import_linkage(self, sel_outline, sel_timeline):
        if self.auto_link_var.get():
            defaults = self._get_linkage_defaults()
            if not defaults:
                self._show_module_linkage_wizard(sel_outline, sel_timeline, defaults=defaults, force_remember=True)
                return

            try:
                result_count = self._execute_module_linkage(defaults, sel_outline, sel_timeline, None)
                self._maybe_show_linkage_issues()
                messagebox.showinfo("模块联动", f"已自动联动，处理 {result_count} 项。")
            except Exception as exc:
                logger.error("自动联动失败: %s", exc, exc_info=True)
                messagebox.showerror("模块联动", f"自动联动失败: {exc}")
        else:
            self._show_module_linkage_wizard(sel_outline, sel_timeline, defaults=self._get_linkage_defaults())

    def _show_module_linkage_wizard(self, sel_outline, sel_timeline, defaults=None, force_remember=False):
        """显示模块联动向导对话框，帮助用户完成数据关联。"""
        wizard = tk.Toplevel(self.winfo_toplevel())
        wizard.title("模块联动向导")
        wizard.geometry("550x480")
        wizard.transient(self.winfo_toplevel())
        wizard.grab_set()

        # 变量
        defaults = defaults or {}
        vars_dict = {
            "generate_scenes_from_outline": tk.BooleanVar(
                value=defaults.get("generate_scenes_from_outline", bool(sel_outline))
            ),
            "generate_scenes_from_timeline": tk.BooleanVar(
                value=defaults.get("generate_scenes_from_timeline", False)
            ),
            "link_timeline_to_scenes": tk.BooleanVar(
                value=defaults.get("link_timeline_to_scenes", bool(sel_timeline))
            ),
            "analyze_story_curve": tk.BooleanVar(
                value=defaults.get("analyze_story_curve", True)
            ),
            "extract_calendar_dates": tk.BooleanVar(
                value=defaults.get("extract_calendar_dates", True)
            ),
            "sync_char_events_to_timeline": tk.BooleanVar(
                value=defaults.get("sync_char_events_to_timeline", True)
            ),
        }

        # 标题
        ttk.Label(wizard, text="模块联动设置", font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(wizard, text="选择要执行的联动操作，激活更多模块功能：", foreground="gray").pack()

        # 选项框架
        options_frame = ttk.LabelFrame(wizard, text="可用操作", padding=10)
        options_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # 场景生成选项
        scene_frame = ttk.LabelFrame(options_frame, text="📝 场景生成", padding=5)
        scene_frame.pack(fill=tk.X, pady=5)

        cb1 = ttk.Checkbutton(scene_frame, text="从大纲事件生成场景",
                              variable=vars_dict["generate_scenes_from_outline"])
        cb1.pack(anchor="w")
        ttk.Label(scene_frame, text="   将每个大纲事件节点转换为独立场景", foreground="gray", font=("Arial", 9)).pack(anchor="w")

        cb2 = ttk.Checkbutton(scene_frame, text="从时间轴事件生成场景",
                              variable=vars_dict["generate_scenes_from_timeline"])
        cb2.pack(anchor="w")
        ttk.Label(scene_frame, text="   将每个真相事件转换为场景（适合推理类）", foreground="gray", font=("Arial", 9)).pack(anchor="w")

        # 关联选项
        link_frame = ttk.LabelFrame(options_frame, text="🔗 数据关联", padding=5)
        link_frame.pack(fill=tk.X, pady=5)

        cb3 = ttk.Checkbutton(link_frame, text="自动关联时间轴与场景",
                              variable=vars_dict["link_timeline_to_scenes"])
        cb3.pack(anchor="w")
        ttk.Label(link_frame, text="   根据名称/时间匹配建立双向关联", foreground="gray", font=("Arial", 9)).pack(anchor="w")

        cb4 = ttk.Checkbutton(link_frame, text="同步角色事件到时间轴",
                              variable=vars_dict["sync_char_events_to_timeline"])
        cb4.pack(anchor="w")
        ttk.Label(link_frame, text="   将角色个人事件同步到全局时间轴", foreground="gray", font=("Arial", 9)).pack(anchor="w")

        # 分析选项
        analysis_frame = ttk.LabelFrame(options_frame, text="📊 数据分析", padding=5)
        analysis_frame.pack(fill=tk.X, pady=5)

        cb5 = ttk.Checkbutton(analysis_frame, text="分析故事曲线数据",
                              variable=vars_dict["analyze_story_curve"])
        cb5.pack(anchor="w")
        ttk.Label(analysis_frame, text="   为场景生成 tension/pacing 值，激活故事曲线视图", foreground="gray", font=("Arial", 9)).pack(anchor="w")

        cb6 = ttk.Checkbutton(analysis_frame, text="提取日历时间信息",
                              variable=vars_dict["extract_calendar_dates"])
        cb6.pack(anchor="w")
        ttk.Label(analysis_frame, text="   从场景内容中提取日期，激活日历视图", foreground="gray", font=("Arial", 9)).pack(anchor="w")

        # 进度标签
        progress_var = tk.StringVar(value="")
        progress_label = ttk.Label(wizard, textvariable=progress_var, foreground="blue")
        progress_label.pack(pady=5)

        remember_var = tk.BooleanVar(value=force_remember or bool(defaults))
        ttk.Checkbutton(
            wizard,
            text="记住这组联动设置",
            variable=remember_var
        ).pack()

        # 按钮
        btn_frame = ttk.Frame(wizard)
        btn_frame.pack(pady=10)

        def execute_linkage():
            wizard.config(cursor="watch")
            progress_var.set("正在执行模块联动...")
            wizard.update()

            try:
                result_count = self._execute_module_linkage(vars_dict, sel_outline, sel_timeline, progress_var)
                if remember_var.get():
                    self._save_linkage_defaults(self._serialize_linkage_defaults(vars_dict))
                self._maybe_show_linkage_issues()
                progress_var.set(f"完成！共处理 {result_count} 项")
                wizard.after(1500, wizard.destroy)
            except Exception as e:
                logger.error(f"模块联动失败: {e}", exc_info=True)
                progress_var.set(f"错误: {e}")
                wizard.config(cursor="")

        def skip_linkage():
            wizard.destroy()
            messagebox.showinfo("提示", "已跳过模块联动。\n您可以稍后在各模块中手动建立关联。")

        ttk.Button(btn_frame, text="执行联动", command=execute_linkage).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="跳过", command=skip_linkage).pack(side=tk.LEFT, padx=10)

    def _get_linkage_option(self, vars_dict, key):
        value = vars_dict.get(key)
        if hasattr(value, "get"):
            return bool(value.get())
        return bool(value)

    def _set_linkage_status(self, progress_var, text):
        if progress_var is None:
            return
        progress_var.set(text)
        self.winfo_toplevel().update()

    def _execute_module_linkage(self, vars_dict, sel_outline, sel_timeline, progress_var):
        """执行模块联动操作。"""
        result_count = 0
        generated_scene_uids = []  # 记录生成的场景UID用于后续关联
        report = {
            "scenes_from_outline": 0,
            "scenes_from_timeline": 0,
            "linked_timeline": 0,
            "synced_char_events": 0,
            "story_curve": 0,
            "calendar_dates": 0
        }

        # 1. 从大纲生成场景
        if self._get_linkage_option(vars_dict, "generate_scenes_from_outline") and sel_outline:
            self._set_linkage_status(progress_var, "正在从大纲生成场景...")

            scene_order = 0
            for item in sel_outline:
                chapter = item.get("chapter_title", "")
                scene_data = {
                    "name": item.get("name", "未命名场景"),
                    "location": item.get("location", ""),
                    "time": chapter,  # 使用章节名作为时间标识
                    "content": item.get("content", ""),
                    "characters": item.get("characters", []) if isinstance(item.get("characters"), list) else [],
                    "tags": ["反推导生成"],
                    "outline_ref_id": "",  # 将在后续关联
                    "tension": 50,  # 默认张力值
                    "kanban_status": "构思",
                    "order": scene_order
                }

                cmd = AddSceneCommand(self.project_manager, scene_data, "从大纲生成场景")
                if self._execute_command(cmd):
                    generated_scene_uids.append(cmd.added_scene_uid)
                    result_count += 1
                    scene_order += 1
                    report["scenes_from_outline"] += 1

        # 2. 从时间轴生成场景
        if self._get_linkage_option(vars_dict, "generate_scenes_from_timeline") and sel_timeline:
            self._set_linkage_status(progress_var, "正在从时间轴生成场景...")

            scene_order = len(generated_scene_uids)
            for item in sel_timeline:
                if item.get("type", "").lower() != "truth":
                    continue

                scene_data = {
                    "name": item.get("name", "未命名场景"),
                    "location": item.get("location", ""),
                    "time": item.get("timestamp", ""),
                    "content": item.get("action", item.get("description", "")),
                    "characters": [],
                    "tags": ["反推导生成", "时间轴事件"],
                    "tension": 50,
                    "kanban_status": "构思",
                    "order": scene_order
                }

                cmd = AddSceneCommand(self.project_manager, scene_data, "从时间轴生成场景")
                if self._execute_command(cmd):
                    generated_scene_uids.append(cmd.added_scene_uid)
                    result_count += 1
                    scene_order += 1
                    report["scenes_from_timeline"] += 1

        # 3. 自动关联时间轴与场景
        if self._get_linkage_option(vars_dict, "link_timeline_to_scenes"):
            self._set_linkage_status(progress_var, "正在关联时间轴与场景...")

            linked = self._auto_link_timeline_to_scenes()
            result_count += linked
            report["linked_timeline"] = linked

        # 4. 同步角色事件到时间轴
        if self._get_linkage_option(vars_dict, "sync_char_events_to_timeline"):
            self._set_linkage_status(progress_var, "正在同步角色事件...")

            synced = self._sync_character_events_to_timeline()
            result_count += synced
            report["synced_char_events"] = synced

        # 5. 分析故事曲线数据
        if self._get_linkage_option(vars_dict, "analyze_story_curve"):
            self._set_linkage_status(progress_var, "正在分析故事曲线...")

            analyzed = self._analyze_story_curve_data()
            result_count += analyzed
            report["story_curve"] = analyzed

        # 6. 提取日历时间
        if self._get_linkage_option(vars_dict, "extract_calendar_dates"):
            self._set_linkage_status(progress_var, "正在提取日历时间...")

            extracted = self._extract_calendar_dates()
            result_count += extracted
            report["calendar_dates"] = extracted

        report.update(self._collect_linkage_issues())
        report["total"] = result_count
        self._last_linkage_report = report
        return result_count

    def _auto_link_timeline_to_scenes(self):
        """自动关联时间轴事件与场景（基于名称匹配）。"""
        linked_count = 0

        timelines = self.project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])
        scenes = self.project_manager.get_scenes()

        if not truth_events or not scenes:
            return 0

        # 建立场景名称到UID的映射
        scene_name_to_uid = {}
        for scene in scenes:
            name = scene.get("name", "").strip().lower()
            if name:
                scene_name_to_uid[name] = scene.get("uid", "")

        # 尝试匹配
        for evt in truth_events:
            if evt.get("linked_scene_uid"):
                continue  # 已关联

            evt_name = evt.get("name", "").strip().lower()

            # 精确匹配
            if evt_name in scene_name_to_uid:
                evt["linked_scene_uid"] = scene_name_to_uid[evt_name]
                linked_count += 1
                continue

            # 模糊匹配（事件名包含在场景名中，或反之）
            for scene_name, scene_uid in scene_name_to_uid.items():
                if evt_name in scene_name or scene_name in evt_name:
                    evt["linked_scene_uid"] = scene_uid
                    linked_count += 1
                    break

        if linked_count > 0:
            self.project_manager.mark_modified("timelines")
            get_event_bus().publish(Events.TIMELINE_UPDATED, source="reverse_engineering")

        return linked_count

    @staticmethod
    def _normalize_match_key(text):
        return "".join(str(text or "").split()).lower()

    def _find_best_match(self, name, candidates):
        base = self._normalize_match_key(name)
        best_score = 0.0
        best_name = ""
        best_uid = ""
        if not base:
            return best_name, best_uid, best_score

        for cand_name, cand_uid in candidates:
            cand_key = self._normalize_match_key(cand_name)
            if not cand_key:
                continue
            score = difflib.SequenceMatcher(None, base, cand_key).ratio()
            if score > best_score:
                best_score = score
                best_name = cand_name
                best_uid = cand_uid
        return best_name, best_uid, best_score

    def _build_linkage_candidates(self):
        timelines = self.project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", []) or []
        lie_events = timelines.get("lie_events", []) or []
        scenes = self.project_manager.get_scenes()

        scene_candidates = [(s.get("name", ""), s.get("uid", "")) for s in scenes]
        truth_candidates = [(e.get("name", ""), e.get("uid", "")) for e in truth_events]

        unlinked_truth = [e for e in truth_events if not e.get("linked_scene_uid")]
        unlinked_lie = [e for e in lie_events if not e.get("linked_truth_event_uid")]

        return unlinked_truth, unlinked_lie, scene_candidates, truth_candidates

    def _suggest_linkage_items(self, items, candidates, threshold=0.5):
        suggestions = []
        for item in items:
            name = item.get("name", "")
            best_name, best_uid, score = self._find_best_match(name, candidates)
            if score < threshold:
                best_name = ""
                best_uid = ""
                score = 0.0
            suggestions.append({
                "name": name,
                "target_name": best_name,
                "target_uid": best_uid,
                "score": score
            })
        return suggestions

    def _auto_resolve_linkage_issues(self, threshold=0.72):
        resolved_truth = 0
        resolved_lie = 0

        unlinked_truth, unlinked_lie, scene_candidates, truth_candidates = self._build_linkage_candidates()

        for evt in unlinked_truth:
            best_name, best_uid, score = self._find_best_match(evt.get("name", ""), scene_candidates)
            if score >= threshold and best_uid:
                evt["linked_scene_uid"] = best_uid
                resolved_truth += 1

        for evt in unlinked_lie:
            best_name, best_uid, score = self._find_best_match(evt.get("name", ""), truth_candidates)
            if score >= threshold and best_uid:
                evt["linked_truth_event_uid"] = best_uid
                resolved_lie += 1

        if resolved_truth or resolved_lie:
            self.project_manager.mark_modified("timelines")
            get_event_bus().publish(Events.TIMELINE_UPDATED, source="reverse_engineering")

        return resolved_truth, resolved_lie

    def _show_linkage_review_dialog(self, report):
        dialog = tk.Toplevel(self.winfo_toplevel())
        dialog.title("联动复核")
        dialog.geometry("720x420")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="未关联项复核", font=("Arial", 12, "bold")).pack(pady=8)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        unlinked_truth, unlinked_lie, scene_candidates, truth_candidates = self._build_linkage_candidates()
        truth_suggestions = self._suggest_linkage_items(unlinked_truth, scene_candidates)
        lie_suggestions = self._suggest_linkage_items(unlinked_lie, truth_candidates)

        def _build_tab(title, suggestions, target_label):
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=title)

            tree = ttk.Treeview(frame, columns=("name", "target", "score"), show="headings")
            tree.heading("name", text="事件")
            tree.heading("target", text=f"推荐{target_label}")
            tree.heading("score", text="相似度")
            tree.column("name", width=260)
            tree.column("target", width=260)
            tree.column("score", width=80, anchor="center")

            y_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=y_scroll.set)
            tree.grid(row=0, column=0, sticky="nsew")
            y_scroll.grid(row=0, column=1, sticky="ns")
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)

            for item in suggestions:
                score_text = f"{item['score']:.2f}" if item["score"] else ""
                tree.insert("", tk.END, values=(item["name"], item["target_name"], score_text))

            return frame

        _build_tab("真相事件 → 场景", truth_suggestions, "场景")
        _build_tab("谎言事件 → 真相", lie_suggestions, "真相事件")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=8)

        def _run_auto_fix():
            resolved_truth, resolved_lie = self._auto_resolve_linkage_issues()
            updated_report = self._collect_linkage_issues()
            self._last_linkage_report = updated_report
            messagebox.showinfo(
                "智能补齐",
                f"自动关联完成：真相→场景 {resolved_truth} 项，谎言→真相 {resolved_lie} 项。"
            )
            if updated_report.get("unlinked_truth_count", 0) == 0 and updated_report.get("unlinked_lie_count", 0) == 0:
                dialog.destroy()
            else:
                dialog.destroy()
                self._show_linkage_review_dialog(updated_report)

        def _navigate_timeline():
            if self.on_navigate:
                self.on_navigate("timeline")
            dialog.destroy()

        ttk.Button(btn_frame, text="智能补齐", command=_run_auto_fix).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="跳转时间轴", command=_navigate_timeline).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=6)

    def _collect_linkage_issues(self):
        timelines = self.project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", []) or []
        lie_events = timelines.get("lie_events", []) or []

        unlinked_truth = [e for e in truth_events if not e.get("linked_scene_uid")]
        unlinked_lie = [e for e in lie_events if not e.get("linked_truth_event_uid")]

        return {
            "unlinked_truth_count": len(unlinked_truth),
            "unlinked_lie_count": len(unlinked_lie),
            "unlinked_truth_names": [e.get("name", "") for e in unlinked_truth],
            "unlinked_lie_names": [e.get("name", "") for e in unlinked_lie],
        }

    def _maybe_show_linkage_issues(self):
        report = getattr(self, "_last_linkage_report", None)
        if not report:
            return

        truth_count = report.get("unlinked_truth_count", 0)
        lie_count = report.get("unlinked_lie_count", 0)
        if truth_count == 0 and lie_count == 0:
            return

        def _format_names(names):
            names = [n for n in names if n]
            preview = names[:5]
            suffix = " ..." if len(names) > 5 else ""
            return "、".join(preview) + suffix if preview else "（无）"

        truth_names = _format_names(report.get("unlinked_truth_names", []))
        lie_names = _format_names(report.get("unlinked_lie_names", []))

        message = (
            "联动完成，但仍有未关联项：\n"
            f"- 未关联场景的真相事件: {truth_count} 个\n"
            f"  示例: {truth_names}\n"
            f"- 未关联真相的谎言事件: {lie_count} 个\n"
            f"  示例: {lie_names}\n\n"
            "是否打开联动复核进行补齐？"
        )
        if messagebox.askyesno("联动提示", message):
            self._show_linkage_review_dialog(report)

    def _sync_character_events_to_timeline(self):
        """同步角色个人事件到全局时间轴。"""
        synced_count = 0

        characters = self.project_manager.get_characters()
        timelines = self.project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])

        # 收集已有事件名称避免重复
        existing_names = {e.get("name", "") for e in truth_events}

        for char in characters:
            char_name = char.get("name", "")
            events = char.get("events", [])

            for evt in events:
                evt_summary = evt.get("summary", "")
                evt_name = f"{char_name}: {evt_summary[:30]}"

                if evt_name in existing_names:
                    continue

                # 创建时间轴事件
                timeline_evt = {
                    "uid": self.project_manager._gen_uid(),
                    "name": evt_name,
                    "timestamp": evt.get("time", ""),
                    "location": "",
                    "action": evt_summary,
                    "motive": "",
                    "chaos": "",
                    "linked_scene_uid": "",
                    "source": "角色事件同步"
                }

                truth_events.append(timeline_evt)
                existing_names.add(evt_name)
                synced_count += 1

        if synced_count > 0:
            self.project_manager.mark_modified("timelines")

        return synced_count

    def _analyze_story_curve_data(self):
        """为场景分析故事曲线数据（tension, pacing, valence）。"""
        scenes = self.project_manager.get_scenes()
        if not scenes:
            return 0

        analyzed_count = 0
        total_scenes = len(scenes)

        for idx, scene in enumerate(scenes):
            # 如果已有有效值则跳过
            if scene.get("tension") and scene.get("tension") != 50:
                continue

            content = scene.get("content", "")
            name = scene.get("name", "")

            # 基于位置的默认张力曲线（三幕式结构）
            position_ratio = idx / max(total_scenes - 1, 1)

            if position_ratio < 0.25:
                # 第一幕：铺垫，张力逐渐上升
                base_tension = 20 + int(position_ratio * 4 * 30)
            elif position_ratio < 0.5:
                # 第二幕前半：冲突升级
                base_tension = 50 + int((position_ratio - 0.25) * 4 * 20)
            elif position_ratio < 0.75:
                # 第二幕后半：中点后下降再上升
                mid_pos = (position_ratio - 0.5) * 4
                base_tension = 70 - int(mid_pos * 20) + int(mid_pos * mid_pos * 30)
            else:
                # 第三幕：高潮
                base_tension = 60 + int((position_ratio - 0.75) * 4 * 35)

            # 根据内容关键词微调
            tension_keywords = {
                "高": ["死", "杀", "战", "爆炸", "危", "紧急", "最后", "决战", "真相"],
                "中": ["发现", "冲突", "争", "质问", "揭", "秘密", "追"],
                "低": ["日常", "闲聊", "散步", "休息", "平静", "回忆"]
            }

            text_to_check = name + content
            adjustment = 0

            for keyword in tension_keywords["高"]:
                if keyword in text_to_check:
                    adjustment += 10
                    break

            for keyword in tension_keywords["低"]:
                if keyword in text_to_check:
                    adjustment -= 10
                    break

            final_tension = max(5, min(100, base_tension + adjustment))

            # 简单的 pacing 估算（基于内容长度）
            content_length = len(content)
            if content_length < 200:
                pacing = 7  # 快节奏
            elif content_length < 500:
                pacing = 5  # 中等
            else:
                pacing = 3  # 慢节奏

            # 更新场景
            scene["tension"] = final_tension
            scene["ai_pacing"] = pacing
            scene["ai_valence"] = 0  # 中性
            analyzed_count += 1

        if analyzed_count > 0:
            self.project_manager.mark_modified("script")

        return analyzed_count

    def _extract_calendar_dates(self):
        """从场景内容中提取日期信息。"""
        import re

        scenes = self.project_manager.get_scenes()
        if not scenes:
            return 0

        extracted_count = 0

        # 日期模式
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})月(\d{1,2})日',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            r'(第[一二三四五六七八九十]+天)',
            r'(星期[一二三四五六日天])',
            r'(周[一二三四五六日])',
            r'(早上|上午|中午|下午|傍晚|晚上|深夜|凌晨)',
        ]

        for scene in scenes:
            if scene.get("time") and len(scene.get("time", "")) > 3:
                continue  # 已有时间信息

            content = scene.get("content", "")
            name = scene.get("name", "")
            text = name + " " + content[:500]  # 检查前500字符

            found_dates = []
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    if isinstance(matches[0], tuple):
                        found_dates.append("-".join(matches[0]))
                    else:
                        found_dates.append(matches[0])

            if found_dates:
                # 合并找到的日期信息
                scene["time"] = " ".join(found_dates[:2])  # 最多取两个
                extracted_count += 1

        if extracted_count > 0:
            self.project_manager.mark_modified("script")

        return extracted_count

    def _update_progress_label(self):
        """更新进度标签显示已分析数量。"""
        progress = self.manager.get_analysis_progress()
        if progress:
            text = " | ".join([f"{k}: {v}" for k, v in progress.items()])
            self.progress_label.config(text=f"已分析: {text}")
        else:
            self.progress_label.config(text="")

    def clear_analysis_cache(self):
        """清除分析缓存和累积上下文，允许重新分析所有内容。"""
        if messagebox.askyesno("确认", "确定要清除分析缓存和累积上下文吗？\n这将允许重新分析所有章节。"):
            self.manager.clear_analysis_cache()
            self._saved_context = None  # 清除累积上下文
            self._update_progress_label()
            self.log("Analysis cache and context cleared. All sections will be re-analyzed.")

    def save_session(self):
        """Save all current analysis results (including selection state, incremental state, and context) to a JSON file."""
        if not any(tree.items_data for tree in self.result_trees.values()):
            messagebox.showwarning("Empty", "No analysis data to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            title="Save Analysis Session"
        )
        if not file_path:
            return

        session_data = {
            "version": "3.0",  # 新版本格式（包含长上下文）
            "results": {},
            "incremental_state": self.manager.export_analysis_state(),
            "source_file": self.file_path_var.get(),
            "context": getattr(self, '_saved_context', None)  # 保存累积上下文
        }

        for key, tree in self.result_trees.items():
            session_data["results"][key] = list(tree.items_data.values())

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            # 显示保存的上下文信息
            ctx = session_data.get("context")
            if ctx:
                ctx_info = (f"Context: {len(ctx.get('known_characters', []))} characters, "
                           f"{len(ctx.get('known_entities', []))} entities")
                messagebox.showinfo("Saved", f"Session saved successfully.\n{ctx_info}")
            else:
                messagebox.showinfo("Saved", "Session saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save session: {e}")

    def load_session(self):
        """Load analysis results from a JSON file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json")],
            title="Load Analysis Session"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            version = session_data.get("version", "1.0")
            ctx_info = ""

            # 支持多个版本格式
            if version in ("2.0", "3.0"):
                # 新格式
                results = session_data.get("results", {})
                incremental_state = session_data.get("incremental_state", {})
                source_file = session_data.get("source_file", "")

                # 恢复增量分析状态
                if incremental_state:
                    self.manager.import_analysis_state(incremental_state)
                    self._update_progress_label()

                # 恢复源文件路径
                if source_file:
                    self.file_path_var.set(source_file)

                # 恢复累积上下文（v3.0新增）
                if version == "3.0":
                    context_data = session_data.get("context")
                    if context_data:
                        self._saved_context = context_data
                        ctx_info = (f"\nContext restored: "
                                   f"{len(context_data.get('known_characters', []))} characters, "
                                   f"{len(context_data.get('known_entities', []))} entities")
                        self.log(f"Loaded context: {ctx_info}")
            else:
                # 旧格式兼容
                results = session_data

            # 恢复UI结果
            for key, data_list in results.items():
                if key in self.result_trees:
                    self.result_trees[key].clear()
                    for item in data_list:
                        self.result_trees[key].add_item(item)

            messagebox.showinfo("Loaded", f"Session loaded successfully.{ctx_info}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load session: {e}")
