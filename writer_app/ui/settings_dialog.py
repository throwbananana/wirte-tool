import gzip
import json
import logging
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, simpledialog, font, messagebox
import re
from pathlib import Path
from urllib.parse import urlparse
from writer_app.core.font_manager import get_font_manager
from writer_app.core.thread_pool import get_ai_thread_pool


class SettingsDialog(tk.Toplevel):
    """应用通用设置（含悬浮助手设置）的集中对话框。"""

    logger = logging.getLogger(__name__)

    # 验证常量
    MIN_FONT_SIZE = 6
    MAX_FONT_SIZE = 72
    MIN_AVATAR_SIZE = 30
    MAX_AVATAR_SIZE = 500
    MIN_MARGIN = 5
    MAX_MARGIN = 100
    MIN_LINE_SPACING = 1.0
    MAX_LINE_SPACING = 5.0

    def __init__(self, parent, config_manager, initial_tab="general", ai_client=None):
        super().__init__(parent)
        self.title("设置")
        self.geometry("650x550")
        self.minsize(550, 450)
        self.result = None
        self.config_manager = config_manager
        self.ai_client = ai_client

        # -------- 变量初始化 --------
        self.v_lm_url = tk.StringVar(value=config_manager.get("lm_api_url", "http://localhost:1234/v1/chat/completions"))
        self.v_lm_model = tk.StringVar(value=config_manager.get("lm_api_model", "local-model"))
        self.v_lm_key = tk.StringVar(value=config_manager.get("lm_api_key", ""))
        self.v_test_status = tk.StringVar(value="")
        self.v_ai_mode = tk.BooleanVar(value=config_manager.get("ai_mode_enabled", True))
        self.v_guide_mode = tk.BooleanVar(value=config_manager.get("guide_mode_enabled", True))

        self.v_enable_idle = tk.BooleanVar(value=config_manager.get("enable_idle_chat", False))
        self.v_idle_interval = tk.StringVar(value=str(config_manager.get("idle_interval", 10)))
        self.v_start_expanded = tk.BooleanVar(value=config_manager.get("assistant_start_expanded", False))
        self.v_assistant_primary = tk.BooleanVar(value=config_manager.get("assistant_primary_mode", False))
        self.v_avatar_size = tk.IntVar(value=int(config_manager.get("assistant_avatar_size", 120)))
        self.v_alpha = tk.DoubleVar(value=float(config_manager.get("assistant_alpha", 0.95)))
        self.v_bg_remove_mode = tk.StringVar(value=config_manager.get("assistant_bg_remove_mode", "ai"))
        self.v_bg_remove_tolerance = tk.IntVar(value=config_manager.get("assistant_bg_remove_tolerance", 30))

        # Theme Variables
        self.v_theme = tk.StringVar(value=config_manager.get("theme", "Light"))
        self.v_bg_image = tk.StringVar(value=config_manager.get("background_image", ""))
        self.v_bg_opacity = tk.DoubleVar(value=config_manager.get("background_opacity", 1.0))
        self.custom_colors = config_manager.get("custom_theme_colors", {}).copy()

        # Font Variables
        ui_font_val = config_manager.get("ui_font", "Microsoft YaHei")
        if ui_font_val and ui_font_val.startswith("@"):
            ui_font_val = ui_font_val[1:]
        self.v_ui_font = tk.StringVar(value=ui_font_val)

        self.v_ui_font_size = tk.IntVar(value=config_manager.get("ui_font_size", 9))

        editor_font_val = config_manager.get("editor_font", "Consolas")
        if editor_font_val and editor_font_val.startswith("@"):
            editor_font_val = editor_font_val[1:]
        self.v_editor_font = tk.StringVar(value=editor_font_val)

        self.v_editor_font_size = tk.IntVar(value=config_manager.get("editor_font_size", 12))

        # Template Variables
        self.char_template = list(config_manager.get("character_template", []))

        # AI Prompts Variables
        self.v_prompt_continue = tk.StringVar(value=config_manager.get("prompt_continue_script", ""))
        self.v_prompt_rewrite = tk.StringVar(value=config_manager.get("prompt_rewrite_script", ""))
        self.v_prompt_diagnose = tk.StringVar(value=config_manager.get("prompt_diagnose_outline", ""))
        self.v_prompt_generate = tk.StringVar(value=config_manager.get("prompt_generate_outline", ""))

        # Export Variables
        self.v_export_margin = tk.IntVar(value=config_manager.get("export_pdf_margin", 20))
        self.v_export_spacing = tk.DoubleVar(value=config_manager.get("export_pdf_line_spacing", 1.5))
        
        export_font_val = config_manager.get("export_font_family", "Microsoft YaHei")
        if export_font_val and export_font_val.startswith("@"):
            export_font_val = export_font_val[1:]
        self.v_export_font = tk.StringVar(value=export_font_val)

        # Weather Variables
        self.v_weather_enabled = tk.BooleanVar(value=config_manager.get("weather_enabled", False))
        self.v_weather_api_key = tk.StringVar(value=config_manager.get("weather_api_key", ""))
        self.v_weather_api_host = tk.StringVar(value=config_manager.get("weather_api_host", ""))
        self.v_weather_location = tk.StringVar(value=config_manager.get("weather_location", "101010100"))
        self.v_weather_location_name = tk.StringVar(value=config_manager.get("weather_location_name", "北京"))
        self.v_weather_auto_ambiance = tk.BooleanVar(value=config_manager.get("weather_auto_ambiance", True))
        self.v_weather_show_in_scene = tk.BooleanVar(value=config_manager.get("weather_show_in_scene", True))
        self._weather_search_results = []

        # Taskbar/close behavior
        self.v_close_behavior = tk.StringVar(value=config_manager.get("close_behavior", "ask"))
        self.date_events = list(config_manager.get("taskbar_date_events", []))
        self.v_date_event_summary = tk.StringVar(value="")
        self._update_date_event_summary()

        # 验证错误列表
        self.validation_errors = []

        # -------- UI --------
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_general_tab(notebook)
        self._build_appearance_tab(notebook)
        self._build_templates_tab(notebook)
        self._build_prompts_tab(notebook)
        self._build_export_tab(notebook)
        self._build_assistant_tab(notebook)

        if initial_tab == "assistant":
            notebook.select(5)
        elif initial_tab == "appearance":
            notebook.select(1)
        elif initial_tab == "templates":
            notebook.select(2)
        elif initial_tab == "prompts":
            notebook.select(3)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="保存", command=self.save).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="重置为默认", command=self._reset_to_defaults).pack(side=tk.LEFT)

        self.bind("<Return>", lambda e: self.save())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # --- Validation Helpers ---
    def _validate_url(self, url: str) -> bool:
        """验证URL格式"""
        if not url:
            return False
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except Exception:
            return False

    def _validate_int_range(self, value, min_val, max_val, field_name) -> bool:
        """验证整数范围"""
        try:
            v = int(value)
            if v < min_val or v > max_val:
                self.validation_errors.append(f"{field_name} 必须在 {min_val}-{max_val} 之间")
                return False
            return True
        except (ValueError, TypeError):
            self.validation_errors.append(f"{field_name} 必须是有效的整数")
            return False

    def _validate_float_range(self, value, min_val, max_val, field_name) -> bool:
        """验证浮点数范围"""
        try:
            v = float(value)
            if v < min_val or v > max_val:
                self.validation_errors.append(f"{field_name} 必须在 {min_val}-{max_val} 之间")
                return False
            return True
        except (ValueError, TypeError):
            self.validation_errors.append(f"{field_name} 必须是有效的数字")
            return False

    def _create_validated_spinbox(self, parent, variable, from_, to, width=8, increment=1):
        """创建带验证的Spinbox"""
        spinbox = ttk.Spinbox(
            parent,
            from_=from_,
            to=to,
            textvariable=variable,
            width=width,
            increment=increment
        )
        return spinbox

    def _update_date_event_summary(self):
        count = len(self.date_events)
        if count:
            self.v_date_event_summary.set(f"已配置 {count} 条日期事件")
        else:
            self.v_date_event_summary.set("未配置日期事件")

    def _open_date_event_dialog(self):
        dlg = DateEventsDialog(self, self.date_events)
        self.wait_window(dlg)
        if dlg.result is not None:
            self.date_events = dlg.result
            self._update_date_event_summary()

    def _reset_to_defaults(self):
        """重置为默认值"""
        if not messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？", parent=self):
            return

        self.v_lm_url.set("http://localhost:1234/v1/chat/completions")
        self.v_lm_model.set("local-model")
        self.v_lm_key.set("")
        self.v_ai_mode.set(True)
        self.v_guide_mode.set(True)
        self.v_theme.set("Light")
        self.v_bg_image.set("")
        self.v_bg_opacity.set(1.0)
        self.v_ui_font.set("Microsoft YaHei")
        self.v_ui_font_size.set(9)
        self.v_editor_font.set("Consolas")
        self.v_editor_font_size.set(12)
        self.v_export_margin.set(20)
        self.v_export_spacing.set(1.5)
        self.v_avatar_size.set(120)
        self.v_alpha.set(0.95)
        self.v_enable_idle.set(False)
        self.v_idle_interval.set("10")
        self.v_start_expanded.set(False)
        self.v_assistant_primary.set(False)

        # Weather defaults
        self.v_weather_enabled.set(False)
        self.v_weather_api_key.set("")
        self.v_weather_api_host.set("")
        self.v_weather_location.set("101010100")
        self.v_weather_location_name.set("北京")
        self.v_weather_auto_ambiance.set(True)
        self.v_weather_show_in_scene.set(True)

        # Taskbar defaults
        self.v_close_behavior.set("ask")
        self.date_events = []
        self._update_date_event_summary()

        messagebox.showinfo("提示", "设置已重置为默认值", parent=self)

    # --- Tabs ---
    def _build_general_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="通用")

        ai_frame = ttk.LabelFrame(tab, text="AI 接口")
        ai_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # URL with validation indicator
        url_frame = ttk.Frame(ai_frame)
        url_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=2)

        ttk.Label(url_frame, text="接口 URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, textvariable=self.v_lm_url, width=45)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.url_status = ttk.Label(url_frame, text="", width=3)
        self.url_status.pack(side=tk.LEFT)

        # Validate URL on change
        self.v_lm_url.trace_add("write", self._on_url_change)
        self._on_url_change()  # Initial validation

        ttk.Label(ai_frame, text="模型名称:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        model_frame = ttk.Frame(ai_frame)
        model_frame.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        self.model_entry = ttk.Entry(model_frame, textvariable=self.v_lm_model, width=25)
        self.model_entry.pack(side=tk.LEFT)

        self.model_status = ttk.Label(model_frame, text="", width=3)
        self.model_status.pack(side=tk.LEFT, padx=5)

        self.v_lm_model.trace_add("write", self._on_model_change)
        self._on_model_change()

        ttk.Label(ai_frame, text="API Key (可选):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(ai_frame, textvariable=self.v_lm_key, width=35, show="*").grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        test_frame = ttk.Frame(ai_frame)
        test_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=(6, 2))
        self.btn_test = ttk.Button(test_frame, text="测试连接", command=self._test_ai_connection)
        self.btn_test.pack(side=tk.LEFT)
        ttk.Label(test_frame, textvariable=self.v_test_status, foreground="gray").pack(side=tk.LEFT, padx=8)

        ttk.Checkbutton(ai_frame, text="启用 AI 模式", variable=self.v_ai_mode).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(2, 4)
        )

        ttk.Checkbutton(ai_frame, text="启用助理模式引导 (启动时逐步说明功能)", variable=self.v_guide_mode).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0, 4)
        )

        # Hint label
        hint_label = ttk.Label(ai_frame, text="💡 提示: 使用 OpenAI 兼容的本地服务器 (如 LM Studio)", foreground="gray")
        hint_label.grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))

        ai_frame.columnconfigure(1, weight=1)

        taskbar_frame = ttk.LabelFrame(tab, text="任务栏/托盘")
        taskbar_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(taskbar_frame, text="关闭按钮行为:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        behavior_frame = ttk.Frame(taskbar_frame)
        behavior_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        ttk.Radiobutton(behavior_frame, text="首次询问", variable=self.v_close_behavior, value="ask").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(behavior_frame, text="最小化到托盘", variable=self.v_close_behavior, value="minimize").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(behavior_frame, text="直接退出", variable=self.v_close_behavior, value="exit").pack(side=tk.LEFT)

        ttk.Label(taskbar_frame, text="日期事件:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        event_row = ttk.Frame(taskbar_frame)
        event_row.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(event_row, textvariable=self.v_date_event_summary, foreground="gray").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(event_row, text="管理...", command=self._open_date_event_dialog).pack(side=tk.RIGHT)

        taskbar_frame.columnconfigure(1, weight=1)

        tools_frame = ttk.LabelFrame(tab, text="外置编辑器")
        tools_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            tools_frame,
            text="打开素材编辑器",
            command=lambda: self._launch_external_tool("start_asset_editor.py", "素材编辑器"),
        ).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(
            tools_frame,
            text="打开事件分析器",
            command=lambda: self._launch_external_tool("analyze_events.py", "事件分析器"),
        ).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(
            tools_frame,
            text="打开助手事件编辑器",
            command=lambda: self._launch_external_tool("start_assistant_event_editor.py", "助手事件编辑器"),
        ).pack(side=tk.LEFT, padx=5, pady=5)

    def _on_url_change(self, *args):
        """URL变化时验证"""
        url = self.v_lm_url.get().strip()
        if self._validate_url(url):
            self.url_status.config(text="✓", foreground="green")
        elif url:
            self.url_status.config(text="✗", foreground="red")
        else:
            self.url_status.config(text="")

    def _on_model_change(self, *args):
        """模型名称变化时验证"""
        model = self.v_lm_model.get().strip()
        if model:
            self.model_status.config(text="✓", foreground="green")
        else:
            self.model_status.config(text="✗", foreground="red")

    def _test_ai_connection(self):
        """Run a lightweight connectivity test without blocking the UI thread."""
        if not self.ai_client:
            messagebox.showwarning("提示", "当前会话未加载AI客户端，无法测试连接。", parent=self)
            return

        api_url = self.v_lm_url.get().strip()
        model = self.v_lm_model.get().strip()
        api_key = self.v_lm_key.get().strip()

        # Validate before testing
        if not self._validate_url(api_url):
            messagebox.showwarning("提示", "请输入有效的接口 URL (以 http:// 或 https:// 开头)。", parent=self)
            return

        if not model:
            messagebox.showwarning("提示", "请填写模型名称。", parent=self)
            return

        self.v_test_status.set("测试中...")
        self.btn_test.configure(state=tk.DISABLED)

        def worker():
            return self.ai_client.test_connection(api_url, model, api_key)

        def on_success(result):
            ok, msg = result
            self._finish_test(ok, msg)

        def on_error(e):
            self._finish_test(False, str(e))

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="settings_ai_test",
            fn=worker,
            on_success=on_success,
            on_error=on_error,
            tk_root=self
        )

    def _finish_test(self, ok: bool, msg: str):
        self.btn_test.configure(state=tk.NORMAL)
        self.v_test_status.set(msg)
        if ok:
            self.logger.info("AI connection test succeeded: %s", msg)
            messagebox.showinfo("连接成功", msg, parent=self)
        else:
            self.logger.warning("AI connection test failed: %s", msg)
            messagebox.showwarning("连接失败", msg, parent=self)

    def _launch_external_tool(self, script_name: str, tool_label: str) -> None:
        """Launch a bundled external tool script."""
        base_dir = Path(__file__).resolve().parents[2]
        script_path = base_dir / script_name
        if not script_path.exists():
            messagebox.showwarning("提示", f"未找到 {tool_label} 脚本: {script_path}", parent=self)
            return

        try:
            subprocess.Popen([sys.executable, str(script_path)], cwd=str(base_dir))
        except Exception as exc:
            messagebox.showerror("启动失败", f"{tool_label} 启动失败:\n{exc}", parent=self)

    def _build_templates_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="模板")

        lbl_frame = ttk.LabelFrame(tab, text="角色属性模板")
        lbl_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # List
        list_frame = ttk.Frame(lbl_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.template_listbox = tk.Listbox(list_frame, height=10)
        self.template_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.template_listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.template_listbox.config(yscrollcommand=scroll.set)

        self._refresh_template_list()

        # Buttons
        btn_box = ttk.Frame(lbl_frame)
        btn_box.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        ttk.Button(btn_box, text="添加属性", command=self._add_template_field).pack(fill=tk.X, pady=2)
        ttk.Button(btn_box, text="删除属性", command=self._del_template_field).pack(fill=tk.X, pady=2)
        ttk.Button(btn_box, text="上移", command=lambda: self._move_template(-1)).pack(fill=tk.X, pady=2)
        ttk.Button(btn_box, text="下移", command=lambda: self._move_template(1)).pack(fill=tk.X, pady=2)

    def _refresh_template_list(self):
        self.template_listbox.delete(0, tk.END)
        for field in self.char_template:
            self.template_listbox.insert(tk.END, f"{field['label']} ({field['key']}) - {field['type']}")

    def _add_template_field(self):
        key = simpledialog.askstring("新建属性", "属性ID (英文,如 age):", parent=self)
        if not key:
            return
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
            messagebox.showwarning("格式错误", "属性ID只能包含字母、数字和下划线，且不能以数字开头", parent=self)
            return

        # 检查重复
        for field in self.char_template:
            if field['key'] == key:
                messagebox.showwarning("重复", f"属性ID '{key}' 已存在", parent=self)
                return

        label = simpledialog.askstring("新建属性", "显示名称 (如 年龄):", parent=self) or key

        # Simple type selection dialog could be better, but defaulting to text for MVP
        ftype = "text"

        self.char_template.append({"key": key, "label": label, "type": ftype})
        self._refresh_template_list()

    def _del_template_field(self):
        sel = self.template_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if messagebox.askyesno("确认删除", f"确定要删除属性 '{self.char_template[idx]['label']}' 吗？", parent=self):
            del self.char_template[idx]
            self._refresh_template_list()

    def _move_template(self, direction):
        """移动模板属性顺序"""
        sel = self.template_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if 0 <= new_idx < len(self.char_template):
            self.char_template[idx], self.char_template[new_idx] = self.char_template[new_idx], self.char_template[idx]
            self._refresh_template_list()
            self.template_listbox.selection_set(new_idx)

    def _build_prompts_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="AI 指令")

        container = ttk.Frame(tab, padding=5)
        container.pack(fill=tk.BOTH, expand=True)

        prompts = [
            ("续写剧本 (System Prompt):", self.v_prompt_continue),
            ("润色重写 (System Prompt):", self.v_prompt_rewrite),
            ("大纲诊断 (System Prompt):", self.v_prompt_diagnose),
            ("大纲生成 (System Prompt):", self.v_prompt_generate)
        ]

        for i, (label, var) in enumerate(prompts):
            ttk.Label(container, text=label).pack(anchor=tk.W, pady=(5, 0))
            txt = tk.Text(container, height=4, wrap=tk.WORD, font=("Microsoft YaHei", 9))
            txt.pack(fill=tk.X, pady=(0, 5))
            txt.insert("1.0", var.get())
            # Save ref to read back on save
            setattr(self, f"txt_prompt_{i}", txt)

    def _build_export_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="导出设置")

        pdf_frame = ttk.LabelFrame(tab, text="PDF / 文档导出样式")
        pdf_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 页边距 - 带验证
        ttk.Label(pdf_frame, text="页边距 (mm):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        margin_frame = ttk.Frame(pdf_frame)
        margin_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        margin_spinbox = self._create_validated_spinbox(margin_frame, self.v_export_margin, self.MIN_MARGIN, self.MAX_MARGIN, width=8)
        margin_spinbox.pack(side=tk.LEFT)
        ttk.Label(margin_frame, text=f"({self.MIN_MARGIN}-{self.MAX_MARGIN})", foreground="gray").pack(side=tk.LEFT, padx=5)

        # 行间距 - 带验证
        ttk.Label(pdf_frame, text="行间距:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        spacing_frame = ttk.Frame(pdf_frame)
        spacing_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        spacing_spinbox = self._create_validated_spinbox(spacing_frame, self.v_export_spacing, self.MIN_LINE_SPACING, self.MAX_LINE_SPACING, width=8, increment=0.1)
        spacing_spinbox.pack(side=tk.LEFT)
        ttk.Label(spacing_frame, text=f"({self.MIN_LINE_SPACING}-{self.MAX_LINE_SPACING})", foreground="gray").pack(side=tk.LEFT, padx=5)

        ttk.Label(pdf_frame, text="导出字体:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        available_fonts = get_font_manager().get_available_families()
        ttk.Combobox(pdf_frame, textvariable=self.v_export_font, values=available_fonts, width=25, state="readonly").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

    def _build_appearance_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="外观")

        # Fonts
        font_frame = ttk.LabelFrame(tab, text="字体设置")
        font_frame.pack(fill=tk.X, padx=5, pady=5)

        available_fonts = get_font_manager().get_available_families()

        ttk.Label(font_frame, text="UI字体:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Combobox(font_frame, textvariable=self.v_ui_font, values=available_fonts, width=20, state="readonly").grid(row=0, column=1, padx=5, pady=2)

        ui_size_frame = ttk.Frame(font_frame)
        ui_size_frame.grid(row=0, column=2, padx=5, pady=2)
        self._create_validated_spinbox(ui_size_frame, self.v_ui_font_size, self.MIN_FONT_SIZE, self.MAX_FONT_SIZE, width=5).pack(side=tk.LEFT)
        ttk.Label(ui_size_frame, text="pt", foreground="gray").pack(side=tk.LEFT, padx=2)

        ttk.Label(font_frame, text="编辑器字体:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Combobox(font_frame, textvariable=self.v_editor_font, values=available_fonts, width=20, state="readonly").grid(row=1, column=1, padx=5, pady=2)

        editor_size_frame = ttk.Frame(font_frame)
        editor_size_frame.grid(row=1, column=2, padx=5, pady=2)
        self._create_validated_spinbox(editor_size_frame, self.v_editor_font_size, self.MIN_FONT_SIZE, self.MAX_FONT_SIZE, width=5).pack(side=tk.LEFT)
        ttk.Label(editor_size_frame, text="pt", foreground="gray").pack(side=tk.LEFT, padx=2)

        # Restore default fonts button
        ttk.Button(font_frame, text="恢复默认字体", command=self._restore_default_fonts).grid(row=2, column=0, columnspan=3, pady=(5, 2))

        # Theme Selection
        theme_frame = ttk.LabelFrame(tab, text="主题设置")
        theme_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(theme_frame, text="主题模式:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        theme_cb = ttk.Combobox(theme_frame, textvariable=self.v_theme, values=["Light", "Dark", "Custom"], state="readonly", width=10)
        theme_cb.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(theme_frame, text="背景图片:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        bg_entry = ttk.Entry(theme_frame, textvariable=self.v_bg_image, width=30)
        bg_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(theme_frame, text="浏览...", command=self._browse_bg_image).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(theme_frame, text="清除", command=lambda: self.v_bg_image.set("")).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(theme_frame, text="背景不透明度:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        opacity_frame = ttk.Frame(theme_frame)
        opacity_frame.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=5)

        self.opacity_scale = ttk.Scale(opacity_frame, from_=0.0, to=1.0, variable=self.v_bg_opacity, orient=tk.HORIZONTAL)
        self.opacity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.opacity_label = ttk.Label(opacity_frame, text=f"{self.v_bg_opacity.get():.0%}", width=5)
        self.opacity_label.pack(side=tk.LEFT, padx=5)
        self.opacity_scale.configure(command=lambda v: self.opacity_label.configure(text=f"{float(v):.0%}"))

        # Custom Colors
        self.custom_frame = ttk.LabelFrame(tab, text="自定义主题颜色 (仅 Custom 模式生效)")
        self.custom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # We'll allow picking a few key colors
        colors_to_pick = [
            ("bg_primary", "主背景色"),
            ("bg_secondary", "次背景色"),
            ("fg_primary", "主文本色"),
            ("accent", "强调色"),
            ("canvas_bg", "画布背景"),
            ("editor_bg", "编辑器背景"),
            ("editor_fg", "编辑器文本")
        ]

        for i, (key, label) in enumerate(colors_to_pick):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(self.custom_frame, text=label + ":").grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            # Preview Button
            btn = tk.Button(self.custom_frame, width=10, relief="flat", command=lambda k=key: self._pick_color(k))
            # Set initial color from current custom config or default
            current_col = self.custom_colors.get(key, "#FFFFFF")  # Fallback, likely overridden by update
            btn.configure(bg=current_col)
            btn.grid(row=row, column=col+1, sticky=tk.W, padx=5, pady=2)

            # Save reference to update it later
            setattr(self, f"btn_{key}", btn)

        theme_cb.bind("<<ComboboxSelected>>", self._on_theme_change)
        self._on_theme_change(None)  # Init state

    def _browse_bg_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")],
            parent=self
        )
        if path:
            self.v_bg_image.set(path)

    def _pick_color(self, key):
        current = self.custom_colors.get(key, "#FFFFFF")
        color = colorchooser.askcolor(initialcolor=current, title=f"选择颜色: {key}", parent=self)
        if color[1]:
            self.custom_colors[key] = color[1]
            btn = getattr(self, f"btn_{key}", None)
            if btn:
                btn.configure(bg=color[1])

    def _on_theme_change(self, event):
        state = tk.NORMAL if self.v_theme.get() == "Custom" else tk.DISABLED
        for child in self.custom_frame.winfo_children():
            try:
                child.configure(state=state)
            except:
                pass

    def _restore_default_fonts(self):
        """仅恢复字体设置为默认值"""
        if messagebox.askyesno("确认", "确定要恢复字体设置为默认值吗？", parent=self):
            self.v_ui_font.set("Microsoft YaHei")
            self.v_ui_font_size.set(9)
            self.v_editor_font.set("Consolas")
            self.v_editor_font_size.set(12)

    def _build_assistant_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="悬浮助手")

        mode_frame = ttk.LabelFrame(tab, text="模式")
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Checkbutton(
            mode_frame,
            text="以悬浮助手为主界面（启动后隐藏主窗）",
            variable=self.v_assistant_primary
        ).pack(anchor=tk.W, padx=5, pady=5)

        idle_frame = ttk.LabelFrame(tab, text="闲聊")
        idle_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Checkbutton(idle_frame, text="启用闲聊", variable=self.v_enable_idle).pack(anchor=tk.W, padx=5, pady=(5, 0))
        int_frame = ttk.Frame(idle_frame)
        int_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(int_frame, text="间隔(分):").pack(side=tk.LEFT)

        idle_spinbox = self._create_validated_spinbox(int_frame, tk.IntVar(value=int(self.v_idle_interval.get() or 10)), 1, 120, width=6)
        idle_spinbox.pack(side=tk.LEFT, padx=(4, 0))
        # Sync with string var
        idle_spinbox.configure(textvariable=self.v_idle_interval)

        ttk.Label(int_frame, text="(1-120)", foreground="gray").pack(side=tk.LEFT, padx=5)

        appearance = ttk.LabelFrame(tab, text="外观")
        appearance.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Checkbutton(appearance, text="启动时展开对话框", variable=self.v_start_expanded).pack(anchor=tk.W, padx=5, pady=(5, 0))

        size_frame = ttk.Frame(appearance)
        size_frame.pack(fill=tk.X, padx=5, pady=6)
        ttk.Label(size_frame, text="图像大小:").pack(side=tk.LEFT)
        size_scale = ttk.Scale(size_frame, from_=self.MIN_AVATAR_SIZE, to=self.MAX_AVATAR_SIZE, variable=self.v_avatar_size, orient=tk.HORIZONTAL)
        size_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.lbl_size = ttk.Label(size_frame, text=f"{self.v_avatar_size.get()}px", width=6)
        self.lbl_size.pack(side=tk.LEFT)
        size_scale.configure(command=lambda v: self.lbl_size.configure(text=f"{int(float(v))}px"))

        alpha_frame = ttk.Frame(appearance)
        alpha_frame.pack(fill=tk.X, padx=5, pady=6)
        ttk.Label(alpha_frame, text="透明度:").pack(side=tk.LEFT)
        alpha_scale = ttk.Scale(alpha_frame, from_=0.1, to=1.0, variable=self.v_alpha, orient=tk.HORIZONTAL)
        alpha_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.lbl_alpha = ttk.Label(alpha_frame, text=f"{self.v_alpha.get():.0%}", width=6)
        self.lbl_alpha.pack(side=tk.LEFT)
        alpha_scale.configure(command=lambda v: self.lbl_alpha.configure(text=f"{float(v):.0%}"))

        # Background Removal Settings
        bg_remove_frame = ttk.LabelFrame(tab, text="背景移除 (立绘图片)")
        bg_remove_frame.pack(fill=tk.X, padx=5, pady=5)

        mode_frame = ttk.Frame(bg_remove_frame)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(mode_frame, text="移除模式:").pack(side=tk.LEFT)

        mode_options = [
            ("AI智能 (适合照片)", "ai"),
            ("边缘填充 (适合漫画)", "floodfill"),
            ("不移除", "none")
        ]
        for i, (text, value) in enumerate(mode_options):
            ttk.Radiobutton(mode_frame, text=text, variable=self.v_bg_remove_mode,
                          value=value).pack(side=tk.LEFT, padx=(10 if i > 0 else 5, 0))

        tol_frame = ttk.Frame(bg_remove_frame)
        tol_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(tol_frame, text="白色容差:").pack(side=tk.LEFT)
        tol_scale = ttk.Scale(tol_frame, from_=10, to=80, variable=self.v_bg_remove_tolerance, orient=tk.HORIZONTAL)
        tol_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.lbl_tolerance = ttk.Label(tol_frame, text=f"{self.v_bg_remove_tolerance.get()}", width=4)
        self.lbl_tolerance.pack(side=tk.LEFT)
        tol_scale.configure(command=lambda v: self.lbl_tolerance.configure(text=f"{int(float(v))}"))

        hint_bg = ttk.Label(bg_remove_frame, text="提示: 黑白漫画人物建议使用「边缘填充」模式，可保护身体内的白色区域",
                          foreground="gray", font=("", 8))
        hint_bg.pack(anchor=tk.W, padx=5, pady=(0, 5))

        # Clear cache button
        cache_btn_frame = ttk.Frame(bg_remove_frame)
        cache_btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(cache_btn_frame, text="清除背景缓存", command=self._clear_avatar_cache).pack(side=tk.LEFT)
        ttk.Label(cache_btn_frame, text="(修改设置后需清除缓存才能生效)", foreground="gray", font=("", 8)).pack(side=tk.LEFT, padx=5)

        # Weather Settings Section
        weather_frame = ttk.LabelFrame(tab, text="天气同步 (和风天气 API)")
        weather_frame.pack(fill=tk.X, padx=5, pady=5)

        # Enable weather sync
        ttk.Checkbutton(weather_frame, text="启用天气同步", variable=self.v_weather_enabled).pack(anchor=tk.W, padx=5, pady=(5, 0))

        # API Host
        api_host_frame = ttk.Frame(weather_frame)
        api_host_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(api_host_frame, text="API Host:").pack(side=tk.LEFT)
        self.weather_host_entry = ttk.Entry(api_host_frame, textvariable=self.v_weather_api_host, width=35)
        self.weather_host_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

        # API Key
        api_key_frame = ttk.Frame(weather_frame)
        api_key_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(api_key_frame, text="API Key:").pack(side=tk.LEFT)
        self.weather_api_entry = ttk.Entry(api_key_frame, textvariable=self.v_weather_api_key, width=30, show="*")
        self.weather_api_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        ttk.Button(api_key_frame, text="测试", command=self._test_weather_api, width=6).pack(side=tk.LEFT, padx=(5, 0))

        # City search
        city_frame = ttk.Frame(weather_frame)
        city_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(city_frame, text="城市:").pack(side=tk.LEFT)
        self.city_search_entry = ttk.Entry(city_frame, width=15)
        self.city_search_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.city_search_entry.insert(0, self.v_weather_location_name.get())
        ttk.Button(city_frame, text="搜索", command=self._search_weather_city, width=6).pack(side=tk.LEFT, padx=(5, 0))

        # City result combobox
        self.city_result_combo = ttk.Combobox(city_frame, state="readonly", width=20)
        self.city_result_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.city_result_combo.bind("<<ComboboxSelected>>", self._on_city_selected)

        # Current selected city display
        current_city_frame = ttk.Frame(weather_frame)
        current_city_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Label(current_city_frame, text="当前城市:").pack(side=tk.LEFT)
        self.lbl_current_city = ttk.Label(current_city_frame, text=self.v_weather_location_name.get(), foreground="blue")
        self.lbl_current_city.pack(side=tk.LEFT, padx=(5, 0))
        self.lbl_city_id = ttk.Label(current_city_frame, text=f"(ID: {self.v_weather_location.get()})", foreground="gray")
        self.lbl_city_id.pack(side=tk.LEFT, padx=(5, 0))

        # Weather sync options
        options_frame = ttk.Frame(weather_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Checkbutton(options_frame, text="天气联动环境音", variable=self.v_weather_auto_ambiance).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Checkbutton(options_frame, text="场景生成显示真实天气", variable=self.v_weather_show_in_scene).pack(side=tk.LEFT)

        # Hint for getting API key
        hint_frame = ttk.Frame(weather_frame)
        hint_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Label(hint_frame, text="💡 注册: https://dev.qweather.com/ → 控制台-设置 获取 API Host 和 Key", foreground="gray").pack(anchor=tk.W)

    # --- Actions ---
    def save(self):
        """验证并保存设置"""
        self.validation_errors = []

        # Validate all fields
        api_url = self.v_lm_url.get().strip()
        model = self.v_lm_model.get().strip()

        if api_url and not self._validate_url(api_url):
            self.validation_errors.append("接口 URL 格式无效 (应以 http:// 或 https:// 开头)")

        if not model and self.v_ai_mode.get():
            self.validation_errors.append("启用 AI 模式时，模型名称不能为空")

        # Validate font sizes
        self._validate_int_range(self.v_ui_font_size.get(), self.MIN_FONT_SIZE, self.MAX_FONT_SIZE, "UI 字体大小")
        self._validate_int_range(self.v_editor_font_size.get(), self.MIN_FONT_SIZE, self.MAX_FONT_SIZE, "编辑器字体大小")

        # Validate export settings
        self._validate_int_range(self.v_export_margin.get(), self.MIN_MARGIN, self.MAX_MARGIN, "页边距")
        self._validate_float_range(self.v_export_spacing.get(), self.MIN_LINE_SPACING, self.MAX_LINE_SPACING, "行间距")

        # Validate avatar size
        self._validate_int_range(self.v_avatar_size.get(), self.MIN_AVATAR_SIZE, self.MAX_AVATAR_SIZE, "图像大小")

        # Validate idle interval
        try:
            idle_int = int(self.v_idle_interval.get())
            if idle_int < 1 or idle_int > 120:
                self.validation_errors.append("闲聊间隔必须在 1-120 分钟之间")
        except (ValueError, TypeError):
            idle_int = 10
            self.validation_errors.append("闲聊间隔必须是有效的整数")

        # Show errors if any
        if self.validation_errors:
            error_msg = "请修正以下问题:\n\n" + "\n".join(f"• {e}" for e in self.validation_errors)
            messagebox.showerror("验证错误", error_msg, parent=self)
            return

        # All validations passed, save
        self.result = {
            "lm_api_url": api_url,
            "lm_api_model": model,
            "lm_api_key": self.v_lm_key.get(),
            "ai_mode_enabled": self.v_ai_mode.get(),
            "guide_mode_enabled": self.v_guide_mode.get(),
            "theme": self.v_theme.get(),
            "background_image": self.v_bg_image.get().strip(),
            "background_opacity": self.v_bg_opacity.get(),
            "custom_theme_colors": self.custom_colors,
            "character_template": self.char_template,
            "ui_font": self.v_ui_font.get(),
            "ui_font_size": self.v_ui_font_size.get(),
            "editor_font": self.v_editor_font.get(),
            "editor_font_size": self.v_editor_font_size.get(),
            # AI Prompts
            "prompt_continue_script": self.txt_prompt_0.get("1.0", tk.END).strip(),
            "prompt_rewrite_script": self.txt_prompt_1.get("1.0", tk.END).strip(),
            "prompt_diagnose_outline": self.txt_prompt_2.get("1.0", tk.END).strip(),
            "prompt_generate_outline": self.txt_prompt_3.get("1.0", tk.END).strip(),
            # Export Settings
            "export_pdf_margin": self.v_export_margin.get(),
            "export_pdf_line_spacing": self.v_export_spacing.get(),
            "export_font_family": self.v_export_font.get(),
            "assistant_primary_mode": self.v_assistant_primary.get(),
            "assistant": {
                "enable_idle_chat": self.v_enable_idle.get(),
                "idle_interval": idle_int,
                "start_expanded": self.v_start_expanded.get(),
                "avatar_size": int(self.v_avatar_size.get()),
                "alpha": float(self.v_alpha.get()),
                "bg_remove_mode": self.v_bg_remove_mode.get(),
                "bg_remove_tolerance": int(self.v_bg_remove_tolerance.get())
            },
            # Weather Settings
            "weather_enabled": self.v_weather_enabled.get(),
            "weather_api_key": self.v_weather_api_key.get(),
            "weather_api_host": self.v_weather_api_host.get().strip(),
            "weather_location": self.v_weather_location.get(),
            "weather_location_name": self.v_weather_location_name.get(),
            "weather_auto_ambiance": self.v_weather_auto_ambiance.get(),
            "weather_show_in_scene": self.v_weather_show_in_scene.get(),
            "close_behavior": self.v_close_behavior.get(),
            "taskbar_date_events": self.date_events,
        }
        self.destroy()

    # --- Weather Helper Methods ---
    def _read_json_response(self, response):
        """读取并解析可能被压缩的 JSON 响应"""
        raw = response.read()
        if not raw:
            return {}

        encoding = ""
        if hasattr(response, "headers"):
            encoding = response.headers.get("Content-Encoding", "")
        if not encoding and hasattr(response, "getheader"):
            encoding = response.getheader("Content-Encoding", "")
        encoding = encoding.lower()

        if "gzip" in encoding or raw[:2] == b"\x1f\x8b":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")

        return json.loads(text)

    def _clear_avatar_cache(self):
        """清除头像背景缓存"""
        from pathlib import Path
        import shutil

        cache_dir = Path.home() / ".writer_tool" / "avatar_cache"
        if cache_dir.exists():
            try:
                count = 0
                for f in cache_dir.glob("*.png"):
                    f.unlink()
                    count += 1
                messagebox.showinfo("完成", f"已清除 {count} 个缓存文件。\n重新加载立绘后将使用新设置。", parent=self)
            except Exception as e:
                messagebox.showerror("错误", f"清除缓存失败: {e}", parent=self)
        else:
            messagebox.showinfo("提示", "没有找到缓存文件。", parent=self)

    def _test_weather_api(self):
        """测试和风天气 API 连接"""
        api_key = self.v_weather_api_key.get().strip()
        api_host = self.v_weather_api_host.get().strip()
        location = self.v_weather_location.get().strip()

        if not api_host:
            messagebox.showwarning("提示", "请先输入 API Host", parent=self)
            return

        if not api_key:
            messagebox.showwarning("提示", "请先输入 API Key", parent=self)
            return

        def worker():
            import urllib.request

            # 使用用户的 API Host 和请求头认证
            url = f"https://{api_host}/v7/weather/now?location={location}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "WriterTool/1.0")
            req.add_header("X-QW-Api-Key", api_key)

            with urllib.request.urlopen(req, timeout=10) as response:
                data = self._read_json_response(response)

            return data

        def on_success(data):
            if data.get("code") == "200":
                now = data.get("now", {})
                weather_text = now.get("text", "未知")
                temp = now.get("temp", "?")
                messagebox.showinfo(
                    "连接成功",
                    f"API 连接正常!\n\n当前天气: {weather_text}\n温度: {temp}°C",
                    parent=self
                )
            else:
                error_code = data.get("code", "未知")
                messagebox.showwarning(
                    "API 错误",
                    f"API 返回错误代码: {error_code}\n请检查 API Host 和 Key 是否正确",
                    parent=self
                )

        def on_error(e):
            messagebox.showerror(
                "连接失败",
                f"无法连接到和风天气 API:\n{str(e)}",
                parent=self
            )

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="settings_weather_test",
            fn=worker,
            on_success=on_success,
            on_error=on_error,
            tk_root=self
        )

    def _search_weather_city(self):
        """搜索城市"""
        api_key = self.v_weather_api_key.get().strip()
        api_host = self.v_weather_api_host.get().strip()
        query = self.city_search_entry.get().strip()

        if not api_host:
            messagebox.showwarning("提示", "请先输入 API Host", parent=self)
            return

        if not api_key:
            messagebox.showwarning("提示", "请先输入 API Key", parent=self)
            return

        if not query:
            messagebox.showwarning("提示", "请输入城市名称", parent=self)
            return

        def worker():
            import urllib.request
            import urllib.parse

            encoded_query = urllib.parse.quote(query)
            # 使用用户的 API Host 和请求头认证
            url = f"https://{api_host}/geo/v2/city/lookup?location={encoded_query}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "WriterTool/1.0")
            req.add_header("X-QW-Api-Key", api_key)

            with urllib.request.urlopen(req, timeout=10) as response:
                data = self._read_json_response(response)

            return data

        def on_success(data):
            if data.get("code") == "200":
                locations = data.get("location", [])
                if locations:
                    self._weather_search_results = locations
                    display_list = [f"{loc.get('name', '')} ({loc.get('adm1', '')}, {loc.get('country', '')})" for loc in locations]
                    self._update_city_results(display_list)
                else:
                    messagebox.showinfo("搜索结果", "未找到匹配的城市", parent=self)
            else:
                error_code = data.get("code", "未知")
                messagebox.showwarning("搜索失败", f"API 返回错误代码: {error_code}", parent=self)

        def on_error(e):
            messagebox.showerror("搜索失败", f"搜索城市失败:\n{str(e)}", parent=self)

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="settings_city_search",
            fn=worker,
            on_success=on_success,
            on_error=on_error,
            tk_root=self
        )

    def _update_city_results(self, display_list):
        """更新城市搜索结果下拉框"""
        self.city_result_combo["values"] = display_list
        if display_list:
            self.city_result_combo.current(0)
            self._on_city_selected(None)

    def _on_city_selected(self, event):
        """当选择城市时更新变量"""
        idx = self.city_result_combo.current()
        if idx >= 0 and idx < len(self._weather_search_results):
            loc = self._weather_search_results[idx]
            location_id = loc.get("id", "")
            location_name = loc.get("name", "")

            self.v_weather_location.set(location_id)
            self.v_weather_location_name.set(location_name)

            # Update display
            self.lbl_current_city.config(text=location_name)
            self.lbl_city_id.config(text=f"(ID: {location_id})")


class DateEventEditDialog(simpledialog.Dialog):
    """编辑日期事件对话框"""

    def __init__(self, parent, date_value="", title_value=""):
        self.date_value = date_value
        self.title_value = title_value
        self.result = None
        super().__init__(parent, title="日期事件")

    def body(self, master):
        ttk.Label(master, text="日期 (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.date_var = tk.StringVar(value=self.date_value)
        ttk.Entry(master, textvariable=self.date_var, width=18).grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(master, text="事件标题:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        self.title_var = tk.StringVar(value=self.title_value)
        ttk.Entry(master, textvariable=self.title_var, width=28).grid(row=1, column=1, padx=5, pady=4)

        master.columnconfigure(1, weight=1)
        return master

    def apply(self):
        self.result = {
            "date": self.date_var.get().strip(),
            "title": self.title_var.get().strip(),
        }


class DateEventsDialog(tk.Toplevel):
    """日期事件管理对话框"""

    def __init__(self, parent, events):
        super().__init__(parent)
        self.title("日期事件")
        self.geometry("420x320")
        self.transient(parent)
        self.grab_set()

        self.events = list(events or [])
        self.result = None

        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        list_frame = ttk.Frame(self, padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(list_frame, columns=("date", "title"), show="headings")
        self.tree.heading("date", text="日期")
        self.tree.heading("title", text="事件")
        self.tree.column("date", width=110, anchor="center")
        self.tree.column("title", width=260, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="添加", command=self._add_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="编辑", command=self._edit_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除", command=self._delete_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self._confirm).pack(side=tk.RIGHT, padx=5)

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, evt in enumerate(self.events):
            self.tree.insert("", tk.END, iid=str(idx), values=(evt.get("date", ""), evt.get("title", "")))

    def _add_event(self):
        dlg = DateEventEditDialog(self)
        if dlg.result:
            self.events.append(dlg.result)
            self._refresh_list()

    def _edit_event(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        evt = self.events[idx]
        dlg = DateEventEditDialog(self, evt.get("date", ""), evt.get("title", ""))
        if dlg.result:
            self.events[idx] = dlg.result
            self._refresh_list()

    def _delete_event(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.events):
            del self.events[idx]
            self._refresh_list()

    def _confirm(self):
        self.result = self.events
        self.destroy()
