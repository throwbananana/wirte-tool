import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from typing import List, Optional
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

def get_icon_font(size=12):
    return IconManager().get_font(size=size)



class ValidationResultDialog(tk.Toplevel):
    """逻辑校验结果对话框"""

    def __init__(self, parent, report, on_navigate_to_scene=None):
        """
        Args:
            parent: 父窗口
            report: ValidationReport对象
            on_navigate_to_scene: 点击场景引用时的回调函数 (scene_idx) -> None
        """
        super().__init__(parent)
        self.title("逻辑校验报告")
        self.geometry("700x500")
        self.report = report
        self.on_navigate_to_scene = on_navigate_to_scene

        self.transient(parent)
        self.grab_set()

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 摘要区域
        summary_frame = ttk.LabelFrame(main_frame, text="摘要", padding=10)
        summary_frame.pack(fill=tk.X, pady=(0, 10))

        if self.report.has_issues:
            summary_text = f"发现 {self.report.error_count} 个错误, {self.report.warning_count} 个警告, {self.report.info_count} 条信息"
            summary_color = "red" if self.report.error_count > 0 else ("orange" if self.report.warning_count > 0 else "blue")
            summary_icon = get_icon("error_circle", "❌") if self.report.error_count > 0 else get_icon("warning", "⚠️")
        else:
            summary_text = "未发现逻辑问题"
            summary_color = "green"
            summary_icon = get_icon("checkmark_circle", "✅")

        summary_lbl_frame = ttk.Frame(summary_frame)
        summary_lbl_frame.pack(anchor=tk.W)
        
        tk.Label(summary_lbl_frame, text=summary_icon, font=get_icon_font(12), fg=summary_color).pack(side=tk.LEFT)
        summary_label = ttk.Label(summary_lbl_frame, text=f" {summary_text}", font=("", 11, "bold"))
        summary_label.pack(side=tk.LEFT)


        # 问题列表区域
        list_frame = ttk.LabelFrame(main_frame, text="问题详情", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview for issues
        columns = ("severity", "category", "message")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        self.tree.heading("severity", text="严重程度")
        self.tree.heading("category", text="分类")
        self.tree.heading("message", text="描述")

        self.tree.column("severity", width=80, anchor=tk.CENTER)
        self.tree.column("category", width=100, anchor=tk.CENTER)
        self.tree.column("message", width=450)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 填充数据
        self._populate_issues()

        # 双击跳转
        self.tree.bind("<Double-1>", self._on_item_double_click)

        # 详情区域
        detail_frame = ttk.LabelFrame(main_frame, text="选中问题详情", padding=10)
        detail_frame.pack(fill=tk.X, pady=(0, 10))

        self.detail_label = ttk.Label(detail_frame, text="双击问题可跳转到相关场景", wraplength=650)
        self.detail_label.pack(anchor=tk.W)

        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="复制报告", command=self._copy_report).pack(side=tk.RIGHT, padx=10)

    def _populate_issues(self):
        """填充问题列表"""
        severity_icons = {
            "error": get_icon("error_circle", "❌"), 
            "warning": get_icon("warning", "⚠️"), 
            "info": get_icon("info", "ℹ️")
        }
        # To support icons in Treeview, we might need to set the font for the severity column or the whole tree.
        # Let's set it for the whole tree for now if we want icons to show.
        self.tree.configure(font=("Segoe UI", 9)) # Segoe UI has good emoji/icon support on Windows
        
        category_names = {
            "clue_order": "线索顺序",
            "character_presence": "角色在场",
            "timeline_conflict": "时间线冲突",
            "location_inconsistency": "地点不一致",
            "reference_missing": "引用缺失"
        }

        for i, issue in enumerate(self.report.issues):
            severity_icon = severity_icons.get(issue.severity.value, "•")
            category_name = category_names.get(issue.category.value, issue.category.value)

            self.tree.insert("", tk.END, iid=str(i), values=(
                f"{severity_icon} {issue.severity.value.upper()}",
                category_name,
                issue.message
            ))


    def _on_item_double_click(self, event):
        """双击跳转到相关场景"""
        selection = self.tree.selection()
        if not selection:
            return

        issue_idx = int(selection[0])
        if 0 <= issue_idx < len(self.report.issues):
            issue = self.report.issues[issue_idx]

            # 更新详情
            detail_text = f"场景引用: {', '.join(str(s+1) for s in issue.scene_refs) if issue.scene_refs else '无'}\n"
            detail_text += f"节点引用: {', '.join(issue.node_refs) if issue.node_refs else '无'}"
            self.detail_label.configure(text=detail_text)

            # 跳转到第一个相关场景
            if issue.scene_refs and self.on_navigate_to_scene:
                self.on_navigate_to_scene(issue.scene_refs[0])

    def _copy_report(self):
        """复制报告到剪贴板"""
        report_md = self.report.to_markdown()
        self.clipboard_clear()
        self.clipboard_append(report_md)
        messagebox.showinfo("提示", "报告已复制到剪贴板")


class DiagnosisResultDialog(tk.Toplevel):
    """诊断结果展示对话框"""

    def __init__(self, parent, text_content):
        super().__init__(parent)
        self.title("大纲诊断报告")
        self.geometry("800x600")
        
        # 文本显示区域
        text_frame = ttk.Frame(self, padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Microsoft YaHei", 11))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget.insert("1.0", text_content)
        self.text_widget.configure(state="disabled")  # 只读
        
        # 底部按钮
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="复制全部", command=self.copy_all).pack(side=tk.RIGHT, padx=10)

    def copy_all(self):
        """复制内容到剪贴板"""
        self.clipboard_clear()
        self.clipboard_append(self.text_widget.get("1.0", tk.END))
        messagebox.showinfo("提示", "已复制到剪贴板")


class CharacterDialog(tk.Toplevel):
    """角色编辑对话框"""

    def __init__(self, parent, title, character=None, template=None):
        super().__init__(parent)
        from tkinter import filedialog  # Import inside to avoid circular dependency if any
        self.filedialog = filedialog
        self.title(title)
        self.result = None
        self.character = character or {"name": "", "description": "", "image_path": ""}
        self.template = template or []
        # template example: [{"key": "age", "label": "年龄", "type": "text"}, {"key": "role", "label": "定位", "type": "combo", "values": ["主角", "配角"]}]

        self.geometry("500x600")
        self.transient(parent)
        self.grab_set()

        self.custom_fields_vars = {}
        self.setup_ui()
        self.wait_window()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable area for dynamic fields
        canvas = tk.Canvas(main_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # --- Core Fields ---
        ttk.Label(scrollable_frame, text="角色姓名 (必填):").pack(anchor=tk.W, pady=(0, 2))
        self.name_var = tk.StringVar(value=self.character.get("name", ""))
        ttk.Entry(scrollable_frame, textvariable=self.name_var).pack(fill=tk.X, pady=(0, 10))

        ttk.Label(scrollable_frame, text="角色图片:").pack(anchor=tk.W, pady=(0, 2))
        img_frame = ttk.Frame(scrollable_frame)
        img_frame.pack(fill=tk.X, pady=(0, 10))
        self.image_path_var = tk.StringVar(value=self.character.get("image_path", ""))
        ttk.Entry(img_frame, textvariable=self.image_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(img_frame, text="浏览...", command=self.browse_image).pack(side=tk.LEFT, padx=5)

        ttk.Label(scrollable_frame, text="基础描述:").pack(anchor=tk.W, pady=(0, 2))
        self.desc_text = tk.Text(scrollable_frame, height=5, wrap=tk.WORD)
        self.desc_text.pack(fill=tk.X, pady=(0, 10))
        self.desc_text.insert("1.0", self.character.get("description", ""))

        # --- Dynamic Template Fields ---
        if self.template:
            ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
            ttk.Label(scrollable_frame, text="自定义属性", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
            
            custom_data = self.character.get("custom_data", {})
            
            for field in self.template:
                key = field.get("key")
                label = field.get("label", key)
                ftype = field.get("type", "text")
                val = custom_data.get(key, field.get("default", ""))
                
                container = ttk.Frame(scrollable_frame)
                container.pack(fill=tk.X, pady=2)
                ttk.Label(container, text=f"{label}:").pack(anchor=tk.W)
                
                if ftype == "combo":
                    var = tk.StringVar(value=val)
                    cb = ttk.Combobox(container, textvariable=var, values=field.get("values", []))
                    cb.pack(fill=tk.X)
                    self.custom_fields_vars[key] = var
                else:
                    var = tk.StringVar(value=val)
                    ttk.Entry(container, textvariable=var).pack(fill=tk.X)
                    self.custom_fields_vars[key] = var

        # --- Buttons (Outside scroll area usually, but for simplicity inside or below) ---
        # Actually better to have buttons fixed at bottom.
        # Let's move buttons to self (Dialog window) bottom.
        
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(btn_frame, text="确定", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.on_cancel).pack(side=tk.RIGHT)

    def browse_image(self):
        path = self.filedialog.askopenfilename(
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp")]
        )
        if path:
            self.image_path_var.set(path)

    def on_ok(self):
        custom_data = {}
        for key, var in self.custom_fields_vars.items():
            custom_data[key] = var.get().strip()
            
        self.result = {
            "name": self.name_var.get().strip(),
            "description": self.desc_text.get("1.0", tk.END).strip(),
            "image_path": self.image_path_var.get().strip(),
            "custom_data": custom_data
        }
        self.destroy()

    def on_cancel(self):
        self.destroy()


class FocusModeSettingsDialog(tk.Toplevel):
    """专注模式设置对话框"""

    def __init__(self, parent, script_editor, config_manager):
        """
        Args:
            parent: 父窗口
            script_editor: ScriptEditor实例
            config_manager: ConfigManager实例
        """
        super().__init__(parent)
        self.title("专注模式设置")
        self.geometry("450x550")
        self.script_editor = script_editor
        self.config_manager = config_manager

        self.transient(parent)
        self.grab_set()

        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 聚焦级别 ---
        level_frame = ttk.LabelFrame(main_frame, text="聚焦级别", padding=10)
        level_frame.pack(fill=tk.X, pady=(0, 10))

        self.level_var = tk.StringVar(value="line")
        levels = [
            ("行 (Line)", "line", "聚焦当前行"),
            ("句子 (Sentence)", "sentence", "聚焦当前句子"),
            ("段落 (Paragraph)", "paragraph", "聚焦当前段落"),
            ("对话 (Dialogue)", "dialogue", "聚焦当前对话块")
        ]
        for text, value, desc in levels:
            rb_frame = ttk.Frame(level_frame)
            rb_frame.pack(fill=tk.X, pady=2)
            ttk.Radiobutton(rb_frame, text=text, value=value, variable=self.level_var).pack(side=tk.LEFT)
            ttk.Label(rb_frame, text=f"  - {desc}", foreground="#666").pack(side=tk.LEFT)

        # --- 上下文行数 ---
        context_frame = ttk.LabelFrame(main_frame, text="上下文设置", padding=10)
        context_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(context_frame, text="上下文行数 (显示聚焦区域周围的行数):").pack(anchor=tk.W)

        context_slider_frame = ttk.Frame(context_frame)
        context_slider_frame.pack(fill=tk.X, pady=5)

        self.context_var = tk.IntVar(value=3)
        self.context_label = ttk.Label(context_slider_frame, text="3 行")
        self.context_label.pack(side=tk.RIGHT)

        self.context_scale = ttk.Scale(
            context_slider_frame, from_=0, to=10, orient=tk.HORIZONTAL,
            variable=self.context_var, command=self._on_context_change
        )
        self.context_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # --- 视觉效果 ---
        effect_frame = ttk.LabelFrame(main_frame, text="视觉效果", padding=10)
        effect_frame.pack(fill=tk.X, pady=(0, 10))

        self.gradient_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            effect_frame, text="启用渐变淡化效果",
            variable=self.gradient_var
        ).pack(anchor=tk.W, pady=2)
        ttk.Label(effect_frame, text="  上下文行渐变淡化,更柔和的视觉过渡", foreground="#666").pack(anchor=tk.W)

        self.highlight_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            effect_frame, text="高亮当前聚焦区域背景",
            variable=self.highlight_var
        ).pack(anchor=tk.W, pady=(10, 2))
        ttk.Label(effect_frame, text="  为当前行/句子/段落添加背景色", foreground="#666").pack(anchor=tk.W)

        # --- 联动设置 ---
        link_frame = ttk.LabelFrame(main_frame, text="联动设置", padding=10)
        link_frame.pack(fill=tk.X, pady=(0, 10))

        self.typewriter_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            link_frame, text="专注模式自动启用打字机模式",
            variable=self.typewriter_var
        ).pack(anchor=tk.W, pady=2)

        self.zen_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            link_frame, text="沉浸模式自动启用专注模式",
            variable=self.zen_var
        ).pack(anchor=tk.W, pady=2)

        self.sprint_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            link_frame, text="写作冲刺自动启用专注模式",
            variable=self.sprint_var
        ).pack(anchor=tk.W, pady=2)

        # --- 颜色设置 ---
        color_frame = ttk.LabelFrame(main_frame, text="颜色设置", padding=10)
        color_frame.pack(fill=tk.X, pady=(0, 10))

        # 颜色选择器 - 创建带预览的颜色按钮
        self.color_buttons = {}

        # Light theme colors
        light_row = ttk.Frame(color_frame)
        light_row.pack(fill=tk.X, pady=5)
        ttk.Label(light_row, text="浅色主题:", width=10).pack(side=tk.LEFT)

        ttk.Label(light_row, text="高亮背景").pack(side=tk.LEFT, padx=(10, 2))
        self.highlight_light_var = tk.StringVar(value="#FFFDE7")
        self.color_buttons["highlight_light"] = self._create_color_button(
            light_row, self.highlight_light_var, "选择高亮背景色 (浅色主题)")

        ttk.Label(light_row, text="淡化颜色").pack(side=tk.LEFT, padx=(15, 2))
        self.dim_light_var = tk.StringVar(value="#CCCCCC")
        self.color_buttons["dim_light"] = self._create_color_button(
            light_row, self.dim_light_var, "选择淡化颜色 (浅色主题)")

        # Dark theme colors
        dark_row = ttk.Frame(color_frame)
        dark_row.pack(fill=tk.X, pady=5)
        ttk.Label(dark_row, text="深色主题:", width=10).pack(side=tk.LEFT)

        ttk.Label(dark_row, text="高亮背景").pack(side=tk.LEFT, padx=(10, 2))
        self.highlight_dark_var = tk.StringVar(value="#37474F")
        self.color_buttons["highlight_dark"] = self._create_color_button(
            dark_row, self.highlight_dark_var, "选择高亮背景色 (深色主题)")

        ttk.Label(dark_row, text="淡化颜色").pack(side=tk.LEFT, padx=(15, 2))
        self.dim_dark_var = tk.StringVar(value="#555555")
        self.color_buttons["dim_dark"] = self._create_color_button(
            dark_row, self.dim_dark_var, "选择淡化颜色 (深色主题)")

        # --- 按钮 ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="恢复默认", command=self.reset_defaults).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="应用", command=self.apply_settings).pack(side=tk.RIGHT)

    def _on_context_change(self, value):
        """Update context label when slider changes."""
        lines = int(float(value))
        self.context_label.configure(text=f"{lines} 行")

    def _create_color_button(self, parent, color_var, title):
        """创建带颜色预览的选择按钮"""
        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT, padx=2)

        # 颜色预览画布
        preview = tk.Canvas(frame, width=24, height=24, highlightthickness=1,
                            highlightbackground="#999", cursor="hand2")
        preview.pack(side=tk.LEFT)

        # 初始化颜色
        try:
            preview.configure(bg=color_var.get())
        except tk.TclError:
            preview.configure(bg="#FFFFFF")

        # 颜色值显示
        entry = ttk.Entry(frame, textvariable=color_var, width=8)
        entry.pack(side=tk.LEFT, padx=(2, 0))

        def choose_color(event=None):
            current = color_var.get()
            try:
                result = colorchooser.askcolor(
                    initialcolor=current,
                    title=title,
                    parent=self
                )
                if result[1]:
                    color_var.set(result[1])
                    preview.configure(bg=result[1])
            except Exception:
                pass

        def on_entry_change(*args):
            try:
                preview.configure(bg=color_var.get())
            except tk.TclError:
                pass

        # 绑定事件
        preview.bind("<Button-1>", choose_color)
        color_var.trace_add("write", on_entry_change)

        return {"preview": preview, "entry": entry, "choose": choose_color}

    def load_current_settings(self):
        """Load current settings from editor and config."""
        settings = self.script_editor.get_focus_settings()

        self.level_var.set(settings.get("level", "line"))
        self.context_var.set(settings.get("context_lines", 3))
        self._on_context_change(settings.get("context_lines", 3))
        self.gradient_var.set(settings.get("gradient", True))
        self.highlight_var.set(settings.get("highlight_current", True))
        self.typewriter_var.set(settings.get("with_typewriter", True))

        # Load from config
        if self.config_manager:
            config = self.config_manager.get_focus_mode_config()
            self.zen_var.set(config.get("auto_in_zen", True))
            self.sprint_var.set(config.get("auto_in_sprint", True))
            self.highlight_light_var.set(config.get("highlight_color_light", "#FFFDE7"))
            self.highlight_dark_var.set(config.get("highlight_color_dark", "#37474F"))
            self.dim_light_var.set(config.get("dim_color_light", "#CCCCCC"))
            self.dim_dark_var.set(config.get("dim_color_dark", "#555555"))

    def apply_settings(self):
        """Apply settings to editor and save to config."""
        # Apply to editor
        self.script_editor._focus_level = self.level_var.get()
        self.script_editor._focus_context_lines = self.context_var.get()
        self.script_editor._focus_gradient = self.gradient_var.get()
        self.script_editor._focus_highlight_current = self.highlight_var.get()
        self.script_editor._focus_with_typewriter = self.typewriter_var.get()

        # Save to config
        if self.config_manager:
            self.config_manager.set("focus_mode_level", self.level_var.get())
            self.config_manager.set("focus_mode_context_lines", self.context_var.get())
            self.config_manager.set("focus_mode_gradient", self.gradient_var.get())
            self.config_manager.set("focus_mode_highlight_current", self.highlight_var.get())
            self.config_manager.set("focus_mode_with_typewriter", self.typewriter_var.get())
            self.config_manager.set("focus_mode_auto_in_zen", self.zen_var.get())
            self.config_manager.set("focus_mode_auto_in_sprint", self.sprint_var.get())
            self.config_manager.set("focus_mode_highlight_color_light", self.highlight_light_var.get())
            self.config_manager.set("focus_mode_highlight_color_dark", self.highlight_dark_var.get())
            self.config_manager.set("focus_mode_dim_color_light", self.dim_light_var.get())
            self.config_manager.set("focus_mode_dim_color_dark", self.dim_dark_var.get())
            self.config_manager.save()

        # Reconfigure editor tags with new colors
        self.script_editor._configure_focus_tags(self.script_editor._current_theme)

        # Reapply focus effect if active
        if self.script_editor.focus_mode:
            self.script_editor._apply_focus_effect()

        messagebox.showinfo("成功", "专注模式设置已保存", parent=self)
        self.destroy()

    def reset_defaults(self):
        """Reset all settings to defaults."""
        self.level_var.set("line")
        self.context_var.set(3)
        self._on_context_change(3)
        self.gradient_var.set(True)
        self.highlight_var.set(True)
        self.typewriter_var.set(True)
        self.zen_var.set(True)
        self.sprint_var.set(True)

        # 重置颜色（通过trace自动更新预览）
        self.highlight_light_var.set("#FFFDE7")
        self.highlight_dark_var.set("#37474F")
        self.dim_light_var.set("#CCCCCC")
        self.dim_dark_var.set("#555555")

        # 手动更新颜色预览确保同步
        self._update_color_previews()

    def _update_color_previews(self):
        """更新所有颜色预览"""
        color_map = {
            "highlight_light": self.highlight_light_var,
            "dim_light": self.dim_light_var,
            "highlight_dark": self.highlight_dark_var,
            "dim_dark": self.dim_dark_var,
        }
        for key, var in color_map.items():
            if key in self.color_buttons:
                try:
                    self.color_buttons[key]["preview"].configure(bg=var.get())
                except tk.TclError:
                    pass
