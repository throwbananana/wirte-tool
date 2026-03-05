import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from writer_app.core.project_types import ProjectTypeManager
from writer_app.core.module_registry import (
    get_visible_modules,
    get_module_display_name,
    get_ordered_module_keys
)
from writer_app.core.wiki_templates import (
    get_template_names,
    get_template_categories,
    merge_categories
)

class ProjectSettingsDialog:
    def __init__(self, parent, current_type, current_length, current_tags, current_tools, current_wiki_categories, on_confirm):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("项目设置")
        self.dialog.geometry("680x620")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.on_confirm = on_confirm
        self.result = None
        self.current_type = current_type
        self.current_length = current_length
        self.current_tags = list(current_tags or [])
        self.current_wiki_categories = list(current_wiki_categories or [])
        self.current_tools = set(
            current_tools
            or ProjectTypeManager.get_default_tools(current_type, current_length, self.current_tags)
        )
        self.required_tools = ProjectTypeManager.get_required_tools()
        self.module_catalog = sorted(get_visible_modules(), key=lambda item: item.order)
        self.module_info_map = {info.key: info for info in self.module_catalog}
        self.module_recommendations = ProjectTypeManager.get_module_recommendation_map()
        self.tool_vars = {}
        self.tag_vars = {}
        self.module_rows = {}
        self.module_meta_labels = {}
        self.custom_wiki_categories = None
        self.type_display_map = {}
        self.type_key_display_map = {}
        
        self.type_var = tk.StringVar()
        self.length_var = tk.StringVar(value=current_length)
        self.sync_wiki_var = tk.BooleanVar(value=False)
        self.auto_apply_var = tk.BooleanVar(value=False)
        self.advanced_var = tk.BooleanVar(value=False)
        self.module_search_var = tk.StringVar(value="")
        self.recommended_only_var = tk.BooleanVar(value=False)
        self.wiki_template_var = tk.StringVar(value="")
        self._auto_apply_before_advanced = self.auto_apply_var.get()
        self._last_selected_type = current_type
        self._last_selected_length = current_length
        
        self._setup_ui()
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        preset_frame = ttk.LabelFrame(main_frame, text="预设与标签")
        preset_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(preset_frame, text="主类型 (Preset)", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(
            preset_frame,
            text="主类型决定默认布局与推荐模块，可在下方自由调整。",
            foreground="#666"
        ).pack(anchor=tk.W, pady=(0, 6))

        type_frame = ttk.Frame(preset_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))

        self.type_combo = ttk.Combobox(type_frame, textvariable=self.type_var, state="readonly")
        self._refresh_type_values(selected_key=self.current_type)
        self.type_combo.pack(fill=tk.X)
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_change)

        self.type_desc_label = ttk.Label(preset_frame, text="", wraplength=600, foreground="#666")
        self.type_desc_label.pack(fill=tk.X, pady=(0, 4))
        self.type_hint_label = ttk.Label(preset_frame, text="", wraplength=600, foreground="#666")
        self.type_hint_label.pack(fill=tk.X, pady=(0, 8))

        custom_type_frame = ttk.Frame(preset_frame)
        custom_type_frame.pack(fill=tk.X, pady=(0, 10))
        self.save_custom_btn = ttk.Button(
            custom_type_frame,
            text="保存为自定义类型",
            command=self._save_custom_type
        )
        self.save_custom_btn.pack(side=tk.LEFT)
        self.delete_custom_btn = ttk.Button(
            custom_type_frame,
            text="删除自定义类型",
            command=self._delete_custom_type
        )
        self.delete_custom_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.custom_type_hint_label = ttk.Label(
            preset_frame,
            text="自定义类型会保存到本机配置中，并以当前主类型为基底。",
            foreground="#666"
        )
        self.custom_type_hint_label.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(preset_frame, text="项目篇幅 (Scale)", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(
            preset_frame,
            text="篇幅影响推荐复杂度，工具可随时手动开启。",
            foreground="#666"
        ).pack(anchor=tk.W, pady=(0, 6))

        length_frame = ttk.Frame(preset_frame)
        length_frame.pack(fill=tk.X, pady=(0, 10))

        self.length_combo = ttk.Combobox(length_frame, textvariable=self.length_var, state="readonly")
        available_lengths = ProjectTypeManager.get_available_lengths()
        length_values = [f"{l} - {ProjectTypeManager.get_length_info(l)['name']}" for l in available_lengths]
        self.length_combo["values"] = length_values

        current_length_idx = 0
        if self.length_var.get() in available_lengths:
            current_length_idx = available_lengths.index(self.length_var.get())
        self.length_combo.current(current_length_idx)
        self.length_combo.pack(fill=tk.X)
        self.length_combo.bind("<<ComboboxSelected>>", self._on_length_change)

        self.length_desc_label = ttk.Label(preset_frame, text="", wraplength=600, foreground="#666")
        self.length_desc_label.pack(fill=tk.X, pady=(0, 4))
        self.length_hint_label = ttk.Label(preset_frame, text="", wraplength=600, foreground="#666")
        self.length_hint_label.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            preset_frame,
            text="辅助标签用于补充推荐工具，不改变主类型布局。",
            foreground="#666"
        ).pack(anchor=tk.W, pady=(0, 6))
        tags_frame = ttk.LabelFrame(preset_frame, text="辅助标签 (Secondary)")
        tags_frame.pack(fill=tk.X, pady=(0, 10))
        tags = ProjectTypeManager.get_available_tags()
        if not tags:
            ttk.Label(tags_frame, text="暂无可用标签。", foreground="#666").pack(anchor=tk.W, pady=4)
        else:
            for idx, tag in enumerate(tags):
                tag_label = ProjectTypeManager.get_type_info(tag).get("name", tag)
                var = tk.BooleanVar(value=tag in self.current_tags)
                self.tag_vars[tag] = var
                cb = ttk.Checkbutton(tags_frame, text=tag_label, variable=var, command=self._on_preset_inputs_change)
                row = idx // 3
                col = idx % 3
                cb.grid(row=row, column=col, sticky=tk.W, padx=(0, 12), pady=2)

        preset_action_frame = ttk.Frame(preset_frame)
        preset_action_frame.pack(fill=tk.X, pady=(6, 0))
        self.auto_apply_check = ttk.Checkbutton(
            preset_action_frame,
            text="自动应用预设",
            variable=self.auto_apply_var,
            command=self._on_auto_apply_toggle
        )
        self.auto_apply_check.pack(side=tk.LEFT)
        ttk.Checkbutton(
            preset_action_frame,
            text="同步百科分类",
            variable=self.sync_wiki_var
        ).pack(side=tk.LEFT, padx=(8, 0))
        self.apply_preset_btn = ttk.Button(
            preset_action_frame,
            text="应用预设",
            command=self._apply_preset
        )
        self.apply_preset_btn.pack(side=tk.RIGHT)

        wiki_template_frame = ttk.LabelFrame(preset_frame, text="百科模板")
        wiki_template_frame.pack(fill=tk.X, pady=(8, 0))

        template_names = get_template_names()
        template_combo = ttk.Combobox(
            wiki_template_frame,
            textvariable=self.wiki_template_var,
            state="readonly"
        )
        template_combo["values"] = template_names
        if template_names:
            template_combo.current(0)
        template_combo.pack(fill=tk.X, pady=(4, 6))

        template_btn_frame = ttk.Frame(wiki_template_frame)
        template_btn_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(
            template_btn_frame,
            text="追加分类",
            command=lambda: self._apply_wiki_template(mode="merge")
        ).pack(side=tk.LEFT)
        ttk.Button(
            template_btn_frame,
            text="替换分类",
            command=lambda: self._apply_wiki_template(mode="replace")
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.preset_preview_label = ttk.Label(preset_frame, text="", wraplength=600, foreground="#666")
        self.preset_preview_label.pack(fill=tk.X, pady=(6, 0))

        # Module Customization
        modules_frame = ttk.LabelFrame(main_frame, text="功能模块自定义")
        modules_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        ttk.Label(
            modules_frame,
            text="可按需开启/关闭模块，禁用仅隐藏入口。",
            foreground="#666"
        ).pack(anchor=tk.W, pady=(0, 6))
        self.advanced_check = ttk.Checkbutton(
            modules_frame,
            text="高级模式：启用全部模块（可再手动关闭）",
            variable=self.advanced_var,
            command=self._on_advanced_toggle
        )
        self.advanced_check.pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(
            modules_frame,
            text="标记为「悬疑推荐/言情推荐」等标签的模块为题材推荐，可自由调整。",
            foreground="#666"
        ).pack(anchor=tk.W, pady=(0, 6))

        search_frame = ttk.Frame(modules_frame)
        search_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(search_frame, text="搜索模块:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_frame, textvariable=self.module_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        self.module_search_var.trace_add("write", lambda *args: self._filter_modules())
        ttk.Checkbutton(
            search_frame,
            text="仅显示推荐",
            variable=self.recommended_only_var,
            command=self._filter_modules
        ).pack(side=tk.LEFT, padx=(8, 0))

        list_frame = ttk.Frame(modules_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(list_frame, highlightthickness=0, height=220)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner.bind("<Configure>", _on_configure)

        for info in sorted(self.module_catalog, key=lambda item: item.order):
            row = ttk.Frame(inner)
            var = tk.BooleanVar(value=info.key in self.current_tools)
            self.tool_vars[info.key] = var
            cb = ttk.Checkbutton(
                row,
                text=info.name,
                variable=var,
                command=self._on_tool_toggle
            )
            cb.pack(side=tk.LEFT)
            meta_label = ttk.Label(row, text=info.desc, foreground="#666")
            meta_label.pack(side=tk.LEFT, padx=(8, 0))
            self.module_meta_labels[info.key] = meta_label

            if info.key in self.required_tools:
                cb.state(["disabled"])
                var.set(True)

            row.pack(fill=tk.X, pady=2)
            self.module_rows[info.key] = row

        # Change Preview
        preview_frame = ttk.LabelFrame(main_frame, text="视图变化预告")
        preview_frame.pack(fill=tk.X, pady=(0, 12))
        self.preview_label = ttk.Label(preview_frame, text="", wraplength=600, foreground="#666", justify=tk.LEFT)
        self.preview_label.pack(fill=tk.X, padx=8, pady=6)

        # Warning
        ttk.Label(
            main_frame,
            text="注意：关闭模块仅隐藏入口，数据仍保留，可随时重新开启。",
            foreground="orange",
            wraplength=600
        ).pack(fill=tk.X, pady=(10, 20))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="确定", command=self._confirm).pack(side=tk.RIGHT, padx=5)

        self._update_descriptions()
        self._update_apply_button_state()

    def _get_selected_type_key(self):
        val = self.type_var.get()
        if val in self.type_display_map:
            return self.type_display_map[val]
        return val

    def _get_selected_length_key(self):
        val = self.length_combo.get()
        if " - " in val:
            return val.split(" - ")[0]
        return val

    def _refresh_type_values(self, selected_key=None):
        available_types = ProjectTypeManager.get_available_types()
        values = []
        self.type_display_map.clear()
        self.type_key_display_map.clear()

        for key in available_types:
            info = ProjectTypeManager.get_type_info(key)
            name = info.get("name", key)
            label = f"{name} (自定义)" if ProjectTypeManager.is_custom_type(key) else name
            if label in self.type_display_map:
                label = f"{label} [{key}]"
            values.append(label)
            self.type_display_map[label] = key
            self.type_key_display_map[key] = label

        self.type_combo["values"] = values
        if selected_key is None:
            selected_key = self.current_type

        display = self.type_key_display_map.get(selected_key)
        if display:
            self.type_combo.set(display)
        elif values:
            self.type_combo.set(values[0])

    def _on_type_change(self, event):
        previous = self._last_selected_type
        self._on_preset_inputs_change()
        current = self._get_selected_type_key()
        if current != previous:
            self._maybe_prompt_apply_preset("类型")
            self._last_selected_type = current

    def _on_length_change(self, event):
        previous = self._last_selected_length
        self._on_preset_inputs_change()
        current = self._get_selected_length_key()
        if current != previous:
            self._maybe_prompt_apply_preset("篇幅")
            self._last_selected_length = current

    def _on_preset_inputs_change(self):
        if self.advanced_var.get():
            self._update_descriptions()
            return
        if self.auto_apply_var.get():
            self._apply_preset(update_preview=False)
        self._update_descriptions()

    def _on_auto_apply_toggle(self):
        if self.advanced_var.get():
            self._update_apply_button_state()
            return
        if self.auto_apply_var.get():
            self._apply_preset(update_preview=False)
        self._update_apply_button_state()
        self._update_descriptions()

    def _maybe_prompt_apply_preset(self, label: str):
        if self.advanced_var.get() or self.auto_apply_var.get():
            return
        t_key = self._get_selected_type_key()
        l_key = self._get_selected_length_key()
        tags = self._get_selected_tags()
        preset = ProjectTypeManager.get_preset_config(t_key, tags, l_key)
        recommended = set(preset.get("recommended_tools", []))
        selected = set(self._get_selected_tools())
        if recommended == selected:
            return
        message = f"已切换{label}，是否应用推荐模块？"
        if messagebox.askyesno("应用预设", message, parent=self.dialog):
            self._apply_preset(update_preview=False)
            self._update_preview()

    def _are_all_tools_selected(self):
        for tool_key, var in self.tool_vars.items():
            if tool_key in self.required_tools:
                continue
            if not var.get():
                return False
        return True

    def _set_all_tools(self, enabled: bool):
        for tool_key, var in self.tool_vars.items():
            if tool_key in self.required_tools:
                var.set(True)
            else:
                var.set(enabled)

    def _on_advanced_toggle(self):
        if self.advanced_var.get():
            self._auto_apply_before_advanced = self.auto_apply_var.get()
            self.auto_apply_var.set(False)
            self.auto_apply_check.state(["disabled"])
            self._set_all_tools(True)
            self._update_apply_button_state()
            self._update_descriptions()
            return

        self.auto_apply_check.state(["!disabled"])
        self.auto_apply_var.set(self._auto_apply_before_advanced)
        self._update_apply_button_state()
        if self.auto_apply_var.get():
            self._apply_preset(update_preview=False)
        self._update_descriptions()

    def _update_apply_button_state(self):
        if self.advanced_var.get() or self.auto_apply_var.get():
            self.apply_preset_btn.state(["disabled"])
        else:
            self.apply_preset_btn.state(["!disabled"])

    def _on_tool_toggle(self):
        if self.advanced_var.get() and not self._are_all_tools_selected():
            self.advanced_var.set(False)
            self.auto_apply_check.state(["!disabled"])
            self._update_apply_button_state()
        self._update_preview()

    def _apply_preset(self, update_preview=True):
        t_key = self._get_selected_type_key()
        l_key = self._get_selected_length_key()
        tags = self._get_selected_tags()
        preset = ProjectTypeManager.get_preset_config(t_key, tags, l_key)
        recommended_tools = set(preset.get("recommended_tools", []))
        for tool_key, var in self.tool_vars.items():
            if tool_key in self.required_tools:
                var.set(True)
            else:
                var.set(tool_key in recommended_tools)
        self.custom_wiki_categories = None
        self._update_preset_preview()
        if update_preview:
            self._update_preview()

    def _update_descriptions(self):
        t_key = self._get_selected_type_key()
        l_key = self._get_selected_length_key()
        
        t_info = ProjectTypeManager.get_type_info(t_key)
        l_info = ProjectTypeManager.get_length_info(l_key)
        
        if t_info:
            self.type_desc_label.config(text=t_info.get("description", ""))
            self.type_hint_label.config(text=t_info.get("hint", ""))
        
        if l_info:
            self.length_desc_label.config(text=l_info.get("desc", ""))
            self.length_hint_label.config(text=l_info.get("hint", ""))

        self._update_preset_preview()
        self._update_module_badges()
        self._filter_modules()
        self._refresh_custom_type_actions()
        self._update_preview()

    def _get_selected_tags(self):
        tags = []
        for tag_key, var in self.tag_vars.items():
            if var.get():
                tags.append(tag_key)
        return tags

    def _get_selected_tools(self):
        selected = []
        for tool_key, var in self.tool_vars.items():
            if var.get():
                selected.append(tool_key)
        for tool_key in self.current_tools:
            if tool_key not in self.tool_vars:
                selected.append(tool_key)
        return selected

    def _get_recommended_module_keys(self):
        selected_types = set(self._get_selected_tags())
        selected_types.add(self._get_selected_type_key())
        recommended = set()
        for module_key, type_keys in self.module_recommendations.items():
            if selected_types.intersection(type_keys):
                if module_key in self.module_info_map:
                    recommended.add(module_key)
        return recommended

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

    def _update_module_badges(self):
        for tool_key, label in self.module_meta_labels.items():
            info = self.module_info_map.get(tool_key)
            if not info:
                continue
            type_keys = self.module_recommendations.get(tool_key, [])
            badge_text = self._format_type_badges(type_keys) if type_keys else ""
            if badge_text:
                label.config(text=f"{info.desc} | {badge_text}")
            else:
                label.config(text=info.desc)

    def _refresh_custom_type_actions(self):
        t_key = self._get_selected_type_key()
        if ProjectTypeManager.is_custom_type(t_key):
            self.save_custom_btn.config(text="更新自定义类型")
            self.delete_custom_btn.state(["!disabled"])
        else:
            self.save_custom_btn.config(text="保存为自定义类型")
            self.delete_custom_btn.state(["disabled"])

    def _update_preview(self):
        current_tools = set(self.current_tools)
        selected_tools = set(self._get_selected_tools())
        ordered_keys = [info.key for info in sorted(self.module_catalog, key=lambda item: item.order)]
        show_tools = [t for t in ordered_keys if t in (selected_tools - current_tools)]
        hide_tools = [t for t in ordered_keys if t in (current_tools - selected_tools)]

        def _fmt(tools):
            return "、".join([get_module_display_name(t) for t in tools]) if tools else "无"

        if show_tools or hide_tools:
            preview_text = f"将显示: {_fmt(show_tools)}\n将隐藏: {_fmt(hide_tools)}"
        else:
            preview_text = "功能布局保持不变。"
        self.preview_label.config(text=preview_text)

    def _update_preset_preview(self):
        t_key = self._get_selected_type_key()
        l_key = self._get_selected_length_key()
        tags = self._get_selected_tags()
        preset = ProjectTypeManager.get_preset_config(t_key, tags, l_key)
        categories = self.custom_wiki_categories or preset.get("wiki_categories", [])
        tag_names = [ProjectTypeManager.get_type_info(tag).get("name", tag) for tag in tags]
        tag_text = "、".join(tag_names) if tag_names else "无"
        cat_text = "、".join(categories) if categories else "无"
        self.preset_preview_label.config(text=f"辅助标签: {tag_text}\n推荐百科分类: {cat_text}")

    def _build_custom_type_payload(self, name: str, description: str):
        t_key = self._get_selected_type_key()
        base_key = t_key
        if ProjectTypeManager.is_custom_type(t_key):
            base_key = ProjectTypeManager.get_type_info(t_key).get("base_type", t_key)

        preset = ProjectTypeManager.get_preset_config(
            t_key,
            self._get_selected_tags(),
            self._get_selected_length_key()
        )
        if self.custom_wiki_categories is not None:
            wiki_categories = self.custom_wiki_categories
        elif self.current_wiki_categories:
            wiki_categories = self.current_wiki_categories
        else:
            wiki_categories = preset.get("wiki_categories", [])

        selected_tools = self._get_selected_tools()
        ordered = [key for key in get_ordered_module_keys(visible_only=False) if key in selected_tools]
        default_tab = ordered[0] if ordered else "outline"

        return {
            "name": name,
            "description": description or "",
            "hint": "自定义类型，可自由组合模块。",
            "tools": list(selected_tools),
            "specialized_modules": [],
            "default_tab": default_tab,
            "wiki_categories": wiki_categories,
            "base_type": base_key
        }

    def _save_custom_type(self):
        t_key = self._get_selected_type_key()
        t_info = ProjectTypeManager.get_type_info(t_key)
        default_name = t_info.get("name", t_key)
        name = simpledialog.askstring(
            "保存自定义类型",
            "类型名称:",
            initialvalue=default_name,
            parent=self.dialog
        )
        name = (name or "").strip()
        if not name:
            return
        description = simpledialog.askstring(
            "保存自定义类型",
            "一句话描述 (可选):",
            initialvalue=t_info.get("description", ""),
            parent=self.dialog
        )
        if description is None:
            description = ""

        payload = self._build_custom_type_payload(name, description)
        if ProjectTypeManager.is_custom_type(t_key):
            target_key = t_key
            ProjectTypeManager.save_custom_type(target_key, payload)
        else:
            existing_key = ProjectTypeManager.find_custom_type_key_by_name(name)
            if existing_key:
                if not messagebox.askyesno(
                    "覆盖自定义类型",
                    f"已存在同名自定义类型“{name}”，是否覆盖？",
                    parent=self.dialog
                ):
                    return
                target_key = existing_key
                ProjectTypeManager.save_custom_type(target_key, payload)
            else:
                target_key = ProjectTypeManager.create_custom_type(name, payload)

        self._refresh_type_values(selected_key=target_key)
        self._update_descriptions()
        messagebox.showinfo("保存成功", f"已保存为自定义类型：{name}", parent=self.dialog)

    def _delete_custom_type(self):
        t_key = self._get_selected_type_key()
        if not ProjectTypeManager.is_custom_type(t_key):
            return
        info = ProjectTypeManager.get_type_info(t_key)
        name = info.get("name", t_key)
        if not messagebox.askyesno(
            "删除自定义类型",
            f"确定删除自定义类型“{name}”吗？",
            parent=self.dialog
        ):
            return
        base_key = info.get("base_type", "General")
        ProjectTypeManager.delete_custom_type(t_key)
        self._refresh_type_values(selected_key=base_key)
        self._update_descriptions()

    def _apply_wiki_template(self, mode="merge"):
        template_name = self.wiki_template_var.get()
        if not template_name:
            return
        template_categories = get_template_categories(template_name)
        base_categories = self.custom_wiki_categories or self.current_wiki_categories
        if not base_categories:
            base_categories = ProjectTypeManager.get_preset_config(
                self._get_selected_type_key(),
                self._get_selected_tags(),
                self._get_selected_length_key()
            ).get("wiki_categories", [])
        if mode == "replace":
            new_categories = list(template_categories)
        else:
            new_categories = merge_categories(base_categories, template_categories)
        self.custom_wiki_categories = new_categories
        self.sync_wiki_var.set(False)
        self._update_preset_preview()

    def _filter_modules(self):
        query = self.module_search_var.get().strip().lower()
        recommended_only = self.recommended_only_var.get()
        recommended_keys = self._get_recommended_module_keys() if recommended_only else set()
        for key, row in self.module_rows.items():
            info = self.module_info_map.get(key)
            if not info:
                continue
            name = info.name.lower()
            desc = info.desc.lower()
            matched = not query or query in name or query in desc
            if matched and (not recommended_only or key in recommended_keys):
                row.pack(fill=tk.X, pady=2)
            else:
                row.pack_forget()

    def _confirm(self):
        t_key = self._get_selected_type_key()
        l_key = self._get_selected_length_key()
        selected_tools = self._get_selected_tools()
        selected_tags = self._get_selected_tags()
        preset = ProjectTypeManager.get_preset_config(t_key, selected_tags, l_key)
        if self.custom_wiki_categories is not None:
            wiki_categories = self.custom_wiki_categories
        else:
            wiki_categories = preset.get("wiki_categories", []) if self.sync_wiki_var.get() else None
        
        if self.on_confirm:
            self.on_confirm(t_key, l_key, selected_tags, selected_tools, wiki_categories)
            
        self.dialog.destroy()
