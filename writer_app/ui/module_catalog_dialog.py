import tkinter as tk
from tkinter import ttk

from writer_app.core.module_registry import get_all_modules
from writer_app.core.project_types import ProjectTypeManager
from writer_app.core.module_usage import get_module_usage_counts


GROUP_LABELS = {
    "core": "核心",
    "structure": "结构",
    "planning": "规划",
    "character": "角色",
    "world": "世界观",
    "analysis": "分析",
    "assistant": "助手",
    "suspense": "悬疑",
    "romance": "言情",
    "interactive": "互动",
}


class ModuleCatalogDialog:
    def __init__(self, parent, project_manager):
        self.project_manager = project_manager
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("模块工具箱")
        self.dialog.geometry("760x640")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.required_tools = ProjectTypeManager.get_required_tools()
        self.module_catalog = sorted(get_all_modules(), key=lambda item: item.order)
        self.module_info_map = {info.key: info for info in self.module_catalog}
        self.module_recommendations = ProjectTypeManager.get_module_recommendation_map()
        self.module_usage = get_module_usage_counts(project_manager.get_project_data())
        self.current_tools = set(project_manager.get_enabled_tools())
        self.tool_vars = {}
        self.module_rows = {}

        self.search_var = tk.StringVar(value="")
        self.group_var = tk.StringVar(value="全部")
        self.show_hidden_var = tk.BooleanVar(value=False)
        self.recommended_only_var = tk.BooleanVar(value=False)

        self._setup_ui()

        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text="在当前项目中自由开启/关闭模块，关闭仅隐藏入口，数据仍保留。",
            foreground="#666"
        ).pack(anchor=tk.W)

        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(12, 8))

        ttk.Label(filter_frame, text="搜索:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 12))
        self.search_var.trace_add("write", lambda *args: self._filter_modules())

        ttk.Label(filter_frame, text="分组:").pack(side=tk.LEFT)
        group_combo = ttk.Combobox(filter_frame, textvariable=self.group_var, state="readonly", width=10)
        group_combo["values"] = self._get_group_labels()
        group_combo.current(0)
        group_combo.pack(side=tk.LEFT, padx=(6, 12))
        group_combo.bind("<<ComboboxSelected>>", lambda event: self._filter_modules())

        ttk.Checkbutton(
            filter_frame,
            text="显示隐藏模块",
            variable=self.show_hidden_var,
            command=self._filter_modules
        ).pack(side=tk.LEFT)
        ttk.Checkbutton(
            filter_frame,
            text="仅显示推荐",
            variable=self.recommended_only_var,
            command=self._filter_modules
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.summary_label = ttk.Label(main_frame, text="", foreground="#666")
        self.summary_label.pack(anchor=tk.W, pady=(0, 8))

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner.bind("<Configure>", _on_configure)

        for info in self.module_catalog:
            row = ttk.Frame(inner)
            var = tk.BooleanVar(value=info.key in self.current_tools)
            self.tool_vars[info.key] = var

            cb = ttk.Checkbutton(
                row,
                text=info.name,
                variable=var,
                command=self._update_summary
            )
            cb.pack(side=tk.LEFT)

            usage = self.module_usage.get(info.key, 0)
            usage_text = f"已有数据 {usage}" if usage else "暂无数据"
            badge_text = self._format_type_badges(self.module_recommendations.get(info.key, []))
            meta_parts = [info.desc]
            if badge_text:
                meta_parts.append(badge_text)
            meta_parts.append(usage_text)
            if not info.ui_visible:
                meta_parts.append("外部工具")
            meta_text = " | ".join(meta_parts)
            ttk.Label(row, text=meta_text, foreground="#666").pack(side=tk.LEFT, padx=(8, 0))

            if info.key in self.required_tools:
                cb.state(["disabled"])
                var.set(True)

            row.pack(fill=tk.X, pady=2)
            self.module_rows[info.key] = row

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(12, 0))

        ttk.Button(btn_frame, text="全部启用", command=self._enable_all_modules).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="关闭", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="应用", command=self._apply).pack(side=tk.RIGHT, padx=5)

        self._update_summary()
        self._filter_modules()

    def _get_group_labels(self):
        groups = sorted({info.group for info in self.module_catalog if info.group})
        labels = ["全部"]
        labels.extend([GROUP_LABELS.get(group, group) for group in groups])
        return labels

    def _get_selected_group_key(self):
        label = self.group_var.get()
        if label == "全部":
            return None
        for key, value in GROUP_LABELS.items():
            if value == label:
                return key
        return label

    def _format_type_badges(self, type_keys):
        labels = []
        for key in type_keys:
            info = ProjectTypeManager.get_type_info(key)
            name = info.get("name", key)
            short = name.split("/")[0].strip() if name else key
            labels.append(f"{short}推荐")
        if len(labels) > 3:
            labels = labels[:3] + ["等"]
        return "、".join(labels)

    def _get_recommended_module_keys(self):
        selected_types = set(self.project_manager.get_genre_tags() or [])
        selected_types.add(self.project_manager.get_project_type())
        recommended = set()
        for module_key, type_keys in self.module_recommendations.items():
            if selected_types.intersection(type_keys):
                recommended.add(module_key)
        return recommended

    def _filter_modules(self):
        query = self.search_var.get().strip().lower()
        group_key = self._get_selected_group_key()
        show_hidden = self.show_hidden_var.get()
        recommended_only = self.recommended_only_var.get()
        recommended_keys = self._get_recommended_module_keys() if recommended_only else set()

        for key, row in self.module_rows.items():
            info = self.module_info_map.get(key)
            if not info:
                continue
            if not show_hidden and not info.ui_visible:
                row.pack_forget()
                continue
            if group_key and info.group != group_key:
                row.pack_forget()
                continue
            if recommended_only and key not in recommended_keys:
                row.pack_forget()
                continue
            name = info.name.lower()
            desc = info.desc.lower()
            matched = not query or query in name or query in desc
            if matched:
                row.pack(fill=tk.X, pady=2)
            else:
                row.pack_forget()

    def _get_selected_tools(self):
        selected = []
        for tool_key, var in self.tool_vars.items():
            if var.get():
                selected.append(tool_key)
        for tool_key in self.current_tools:
            if tool_key not in self.tool_vars:
                selected.append(tool_key)
        for tool_key in self.required_tools:
            if tool_key not in selected:
                selected.append(tool_key)
        return selected

    def _update_summary(self):
        enabled = len([k for k, v in self.tool_vars.items() if v.get()])
        total = len(self.tool_vars)
        self.summary_label.config(text=f"已启用 {enabled} / {total} 个模块")

    def _enable_all_modules(self):
        for tool_key, var in self.tool_vars.items():
            var.set(True)
        self._update_summary()

    def _apply(self):
        selected_tools = self._get_selected_tools()
        if set(selected_tools) != set(self.current_tools):
            self.project_manager.set_enabled_tools(selected_tools)
            self.current_tools = set(selected_tools)
            self._update_summary()
