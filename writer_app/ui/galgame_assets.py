"""
Universal Asset Manager - 管理各类资源

支持所有项目类型:
- Galgame: 立绘、背景、CG、UI素材
- 悬疑: 证据照片、地点照片、参考资料
- 其他: 根据项目类型动态配置

使用 AssetTypeRegistry 获取资产类型信息。
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
import shutil
import uuid
import os

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 导入资产类型注册表
try:
    from writer_app.core.resource_loader import AssetTypeRegistry
except ImportError:
    from core.resource_loader import AssetTypeRegistry


class AssetThumbnail(ttk.Frame):
    """单个资源缩略图卡片"""
    def __init__(self, parent, asset_data, on_select, on_delete, on_edit, thumbnail_size=100):
        super().__init__(parent, relief="raised", borderwidth=1)
        self.asset_data = asset_data
        self.on_select = on_select
        self.on_delete = on_delete
        self.on_edit = on_edit
        self.thumbnail_size = thumbnail_size
        self.selected = False

        self._setup_ui()

    def _setup_ui(self):
        # Thumbnail area
        self.thumb_canvas = tk.Canvas(self, width=self.thumbnail_size, height=self.thumbnail_size, bg="#2a2a2a", highlightthickness=0)
        self.thumb_canvas.pack(padx=5, pady=5)

        # Load and display thumbnail
        self._load_thumbnail()

        # Name label
        name = self.asset_data.get("name", "未命名")
        if len(name) > 12:
            name = name[:10] + "..."
        self.name_lbl = ttk.Label(self, text=name, width=14, anchor="center")
        self.name_lbl.pack(pady=(0, 2))

        # Type label - 使用 AssetTypeRegistry 获取显示名称
        asset_type = self.asset_data.get("type", "unknown")
        type_text = AssetTypeRegistry.get_display_name(asset_type)
        ttk.Label(self, text=f"[{type_text}]", foreground="#888").pack()

        # Bind events
        self.bind("<Button-1>", self._on_click)
        self.thumb_canvas.bind("<Button-1>", self._on_click)
        self.name_lbl.bind("<Button-1>", self._on_click)
        self.bind("<Double-1>", self._on_double_click)
        self.thumb_canvas.bind("<Double-1>", self._on_double_click)

        # Right-click menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="在场景中使用", command=lambda: self._use_in_scene(self.asset_data))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="编辑信息", command=lambda: self.on_edit(self.asset_data))
        self.context_menu.add_command(label="删除", command=lambda: self.on_delete(self.asset_data))
        self.bind("<Button-3>", self._show_context_menu)
        self.thumb_canvas.bind("<Button-3>", self._show_context_menu)

    def _use_in_scene(self, asset):
        """将资源载入到场景中使用。"""
        asset_type = asset.get("type", "reference")
        asset_name = asset.get("name", "未命名")
        asset_path = asset.get("path", "")
        character = asset.get("character", "")
        expression = asset.get("expression", "")

        # 根据资产类型生成引用代码
        if asset_type == "sprite":
            if character and expression:
                ref_code = f'show {character} {expression}'
            elif character:
                ref_code = f'show {character}'
            else:
                ref_code = f'show {asset_name}'
        elif asset_type == "background":
            ref_code = f'scene {asset_name}'
        elif asset_type == "cg":
            ref_code = f'show cg {asset_name}'
        elif asset_type == "ui":
            ref_code = f'[UI: {asset_name}]'
        elif asset_type in ("evidence", "clue", "location_photo"):
            ref_code = f'[证据: {asset_name}]'
        else:
            ref_code = f'[资源: {asset_name}]'

        if asset_path:
            full_ref = f'{ref_code}  # {asset_path}'
        else:
            full_ref = ref_code

        # 通过 EventBus 发布事件
        try:
            from writer_app.core.event_bus import get_event_bus
            bus = get_event_bus()
            bus.publish("asset_insert_requested",
                        asset_uid=asset.get("uid"),
                        asset_type=asset_type,
                        asset_name=asset_name,
                        ref_code=ref_code,
                        full_ref=full_ref,
                        asset_path=asset_path)
        except Exception:
            pass

        # 复制到剪贴板
        try:
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(full_ref)
            messagebox.showinfo("已复制", f"资源引用已复制到剪贴板:\n{ref_code}")
        except tk.TclError:
            pass

    def _load_thumbnail(self):
        path = self.asset_data.get("path", "")
        asset_type = self.asset_data.get("type", "unknown")

        # 检查是否为图片类型
        type_info = AssetTypeRegistry.get(asset_type)
        is_image = type_info and type_info.category == "image"

        if HAS_PIL and path and os.path.exists(path) and is_image:
            try:
                img = Image.open(path)
                img.thumbnail((self.thumbnail_size - 10, self.thumbnail_size - 10))
                self.photo = ImageTk.PhotoImage(img)
                self.thumb_canvas.create_image(
                    self.thumbnail_size // 2,
                    self.thumbnail_size // 2,
                    image=self.photo,
                    anchor="center"
                )
            except Exception:
                self._draw_placeholder()
        else:
            self._draw_placeholder()

    def _draw_placeholder(self):
        asset_type = self.asset_data.get("type", "unknown")
        # 使用 AssetTypeRegistry 获取颜色和图标
        color = AssetTypeRegistry.get_color(asset_type)
        icon = AssetTypeRegistry.get_icon(asset_type)

        self.thumb_canvas.create_rectangle(10, 10, self.thumbnail_size-10, self.thumbnail_size-10, fill=color, outline="#888")
        self.thumb_canvas.create_text(self.thumbnail_size//2, self.thumbnail_size//2, text=icon, font=("Arial", 24))

    def _on_click(self, event):
        self.on_select(self.asset_data)

    def _on_double_click(self, event):
        self.on_edit(self.asset_data)

    def _show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def set_selected(self, selected):
        self.selected = selected
        if selected:
            self.configure(relief="solid", borderwidth=2)
        else:
            self.configure(relief="raised", borderwidth=1)


class AssetManagerPanel(ttk.Frame):
    """
    通用资源网格视图面板

    根据项目类型动态显示可用的资产类型筛选器。
    """
    def __init__(self, parent, project_manager, on_asset_select):
        super().__init__(parent)
        self.project_manager = project_manager
        self.on_asset_select = on_asset_select
        self.asset_widgets = []
        self.current_filter = "all"
        self.selected_asset = None
        self.filter_buttons = []

        self._setup_ui()

    def _get_available_asset_types(self):
        """获取当前项目类型支持的资产类型。"""
        return self.project_manager.get_asset_types()

    def _setup_ui(self):
        # Filter bar
        self.filter_frame = ttk.Frame(self)
        self.filter_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.filter_frame, text="筛选:").pack(side=tk.LEFT)

        self.filter_var = tk.StringVar(value="all")

        # 动态创建筛选按钮
        self._rebuild_filter_buttons()

        # Scrollable grid
        self.canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        # 设置可滚动网格
        self._setup_scrollable_grid()

    def _rebuild_filter_buttons(self):
        """根据项目类型重建筛选按钮。"""
        # 清除旧按钮
        for btn in self.filter_buttons:
            btn.destroy()
        self.filter_buttons = []

        # 添加"全部"按钮
        all_btn = ttk.Radiobutton(
            self.filter_frame, text="全部", value="all",
            variable=self.filter_var, command=self.refresh
        )
        all_btn.pack(side=tk.LEFT, padx=5)
        self.filter_buttons.append(all_btn)

        # 根据项目类型添加资产类型按钮
        asset_types = self._get_available_asset_types()
        for type_key in asset_types:
            display_name = AssetTypeRegistry.get_display_name(type_key)
            btn = ttk.Radiobutton(
                self.filter_frame, text=display_name, value=type_key,
                variable=self.filter_var, command=self.refresh
            )
            btn.pack(side=tk.LEFT, padx=5)
            self.filter_buttons.append(btn)

    def _setup_scrollable_grid(self):
        """设置可滚动网格（在_setup_ui中调用）。"""
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def refresh(self):
        """刷新资源列表（项目类型可能已更改）。"""
        # 重建筛选按钮（如果项目类型改变）
        self._rebuild_filter_buttons()

        # Clear existing widgets
        for widget in self.asset_widgets:
            widget.destroy()
        self.asset_widgets = []

        # 确保 scrollable_frame 存在
        if not hasattr(self, 'scrollable_frame') or not self.scrollable_frame.winfo_exists():
            self._setup_scrollable_grid()

        # Get assets - 使用通用的 assets 存储
        assets = self.project_manager.get_galgame_assets()
        filter_type = self.filter_var.get()

        # 筛选：确保筛选值在可用类型中
        available_types = self._get_available_asset_types()
        if filter_type != "all" and filter_type in available_types:
            assets = [a for a in assets if a.get("type") == filter_type]
        elif filter_type != "all":
            # 筛选值无效，重置为全部
            self.filter_var.set("all")

        if not assets:
            lbl = ttk.Label(self.scrollable_frame, text="暂无资源，点击上方按钮添加", foreground="#888")
            lbl.grid(row=0, column=0, padx=20, pady=40)
            self.asset_widgets.append(lbl)
            return

        # Layout in grid (4 columns)
        cols = 4
        for i, asset in enumerate(assets):
            row = i // cols
            col = i % cols

            thumb = AssetThumbnail(
                self.scrollable_frame,
                asset,
                on_select=self._on_select,
                on_delete=self._on_delete,
                on_edit=self._on_edit
            )
            thumb.grid(row=row, column=col, padx=5, pady=5)
            self.asset_widgets.append(thumb)

            if self.selected_asset and asset.get("uid") == self.selected_asset.get("uid"):
                thumb.set_selected(True)

    def _on_select(self, asset):
        self.selected_asset = asset
        for widget in self.asset_widgets:
            if isinstance(widget, AssetThumbnail):
                widget.set_selected(widget.asset_data.get("uid") == asset.get("uid"))
        self.on_asset_select(asset)

    def _on_delete(self, asset):
        if messagebox.askyesno("确认删除", f"确定要删除资源 '{asset.get('name', '未命名')}' 吗？"):
            self.project_manager.delete_galgame_asset(asset.get("uid"))
            self.refresh()

    def _on_edit(self, asset):
        EditAssetDialog(self.winfo_toplevel(), asset, self.project_manager, self.refresh)


# 兼容旧代码的别名
GalgameAssetsPanel = AssetManagerPanel


class AssetDetailPanel(ttk.LabelFrame):
    """资源详情面板 - 显示并编辑选中资源的详细信息。"""
    def __init__(self, parent, project_manager):
        super().__init__(parent, text="资源详情")
        self.project_manager = project_manager
        self.current_asset = None

        self._setup_ui()

    def _get_available_asset_types(self):
        """获取当前项目类型支持的资产类型。"""
        return self.project_manager.get_asset_types()

    def _get_type_display_values(self):
        """获取资产类型的显示值列表（用于下拉框）。"""
        types = self._get_available_asset_types()
        # 返回 (显示名称, 键) 的列表
        return [(AssetTypeRegistry.get_display_name(t), t) for t in types]

    def _setup_ui(self):
        # Preview
        self.preview_canvas = tk.Canvas(self, width=200, height=200, bg="#2a2a2a", highlightthickness=0)
        self.preview_canvas.pack(padx=10, pady=10)

        # Info fields
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, padx=10)

        ttk.Label(info_frame, text="名称:").grid(row=0, column=0, sticky="w", pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(info_frame, textvariable=self.name_var, width=25)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(info_frame, text="类型:").grid(row=1, column=0, sticky="w", pady=2)
        self.type_var = tk.StringVar()
        # 使用动态获取的资产类型
        type_values = self._get_available_asset_types()
        self.type_combo = ttk.Combobox(info_frame, textvariable=self.type_var, values=type_values, state="readonly", width=23)
        self.type_combo.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(info_frame, text="角色:").grid(row=2, column=0, sticky="w", pady=2)
        self.char_var = tk.StringVar()
        self.char_combo = ttk.Combobox(info_frame, textvariable=self.char_var, width=23)
        self.char_combo.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(info_frame, text="表情:").grid(row=3, column=0, sticky="w", pady=2)
        self.expr_var = tk.StringVar()
        self.expr_entry = ttk.Entry(info_frame, textvariable=self.expr_var, width=25)
        self.expr_entry.grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(info_frame, text="路径:").grid(row=4, column=0, sticky="w", pady=2)
        self.path_var = tk.StringVar()
        path_frame = ttk.Frame(info_frame)
        path_frame.grid(row=4, column=1, sticky="ew", pady=2)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=18)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="...", width=3, command=self._browse_path).pack(side=tk.RIGHT)

        ttk.Label(info_frame, text="标签:").grid(row=5, column=0, sticky="w", pady=2)
        self.tags_var = tk.StringVar()
        self.tags_entry = ttk.Entry(info_frame, textvariable=self.tags_var, width=25)
        self.tags_entry.grid(row=5, column=1, sticky="ew", pady=2)

        info_frame.columnconfigure(1, weight=1)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="保存修改", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="在场景中使用", command=self._use_in_scene).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, foreground="#888").pack(anchor="w", padx=10, pady=(0, 8))

        self._update_character_list()

    def _update_character_list(self):
        chars = self.project_manager.get_characters()
        char_names = ["(无)"] + [c.get("name", "") for c in chars]
        self.char_combo["values"] = char_names

    def show_asset(self, asset):
        self.current_asset = asset
        if hasattr(self, "status_var"):
            self.status_var.set("")
        self._update_character_list()

        if not asset:
            self.preview_canvas.delete("all")
            self.name_var.set("")
            self.type_var.set("")
            self.char_var.set("(无)")
            self.expr_var.set("")
            self.path_var.set("")
            self.tags_var.set("")
            return

        self.name_var.set(asset.get("name", ""))
        self.type_var.set(asset.get("type", "sprite"))
        self.char_var.set(asset.get("character", "(无)"))
        self.expr_var.set(asset.get("expression", ""))
        self.path_var.set(asset.get("path", ""))
        self.tags_var.set(", ".join(asset.get("tags", [])))

        self._load_preview(asset.get("path", ""))

    def _load_preview(self, path):
        self.preview_canvas.delete("all")

        if HAS_PIL and path and os.path.exists(path):
            try:
                img = Image.open(path)
                img.thumbnail((190, 190))
                self.preview_photo = ImageTk.PhotoImage(img)
                self.preview_canvas.create_image(100, 100, image=self.preview_photo, anchor="center")
            except (IOError, OSError, Exception) as e:
                self.preview_canvas.create_text(100, 100, text="预览失败", fill="#888")
        else:
            self.preview_canvas.create_text(100, 100, text="无预览" if not path else "需要 PIL 库", fill="#888")

    def _browse_path(self):
        path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.gif"), ("所有文件", "*.*")]
        )
        if path:
            self.path_var.set(path)
            self._load_preview(path)

    def _save(self):
        if not self.current_asset:
            return

        uid = self.current_asset.get("uid")
        updated = {
            "uid": uid,
            "name": self.name_var.get().strip(),
            "type": self.type_var.get(),
            "character": self.char_var.get() if self.char_var.get() != "(无)" else "",
            "expression": self.expr_var.get().strip(),
            "path": self.path_var.get().strip(),
            "tags": [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
        }

        self.project_manager.update_galgame_asset(uid, updated)
        messagebox.showinfo("成功", "资源信息已保存")

    def _set_status(self, text, duration_ms=3000):
        if not hasattr(self, "status_var"):
            return
        self.status_var.set(text)
        if duration_ms:
            self.after(duration_ms, lambda: self.status_var.set(""))

    def _use_in_scene(self):
        """
        将当前资产插入到场景编辑器中。

        生成对应格式的资源引用代码，通过 EventBus 请求插入。
        若未打开编辑器则回退复制到剪贴板。
        """
        if not self.current_asset:
            messagebox.showwarning("提示", "请先选择一个资源")
            return

        asset = self.current_asset
        asset_type = asset.get("type", "reference")
        asset_name = asset.get("name", "未命名")
        asset_path = asset.get("path", "")
        character = asset.get("character", "")
        expression = asset.get("expression", "")

        # 根据资产类型生成不同的引用代码
        if asset_type == "sprite":
            # 立绘：生成 Ren'Py 风格的显示命令
            if character and expression:
                ref_code = f'show {character} {expression}'
            elif character:
                ref_code = f'show {character}'
            else:
                ref_code = f'show {asset_name}'
        elif asset_type == "background":
            # 背景：生成场景切换命令
            ref_code = f'scene {asset_name}'
        elif asset_type == "cg":
            # CG：生成显示命令
            ref_code = f'show cg {asset_name}'
        elif asset_type == "ui":
            # UI素材：生成图片显示
            ref_code = f'[UI: {asset_name}]'
        elif asset_type in ("evidence", "clue", "location_photo"):
            # 证据/线索：生成标记
            ref_code = f'[证据: {asset_name}]'
        else:
            # 通用引用
            ref_code = f'[资源: {asset_name}]'

        # 添加路径注释
        if asset_path:
            full_ref = f'{ref_code}  # {asset_path}'
        else:
            full_ref = ref_code

        # 通过 EventBus 发布事件，通知场景编辑器可以插入资源引用
        try:
            from writer_app.core.event_bus import get_event_bus
            bus = get_event_bus()
            bus.publish("asset_insert_requested",
                        asset_uid=asset.get("uid"),
                        asset_type=asset_type,
                        asset_name=asset_name,
                        ref_code=ref_code,
                        full_ref=full_ref,
                        asset_path=asset_path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"发布资产插入事件失败: {e}")
        script_editor = None
        root = self.winfo_toplevel()
        if root:
            script_controller = getattr(root, "script_controller", None)
            script_editor = getattr(script_controller, "script_editor", None)

        if script_editor:
            self._set_status(f"已插入资源: {asset_name}")
            if hasattr(root, "status_var"):
                root.status_var.set(f"已插入资源: {asset_name}")
            return

        # 回退到剪贴板
        try:
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(full_ref)
        except tk.TclError:
            pass
        self._set_status("已复制到剪贴板，可在剧本中粘贴")


class LoadExistingResourcesDialog:
    """载入已有资源对话框 - 扫描项目中的资源并导入。"""

    def __init__(self, parent, project_manager, on_import_complete):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("载入已有资源")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.project_manager = project_manager
        self.on_import_complete = on_import_complete
        self.found_resources = []
        self.selected_items = set()

        self._setup_ui()

    def _setup_ui(self):
        # 顶部说明
        header_frame = ttk.Frame(self.dialog)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(
            header_frame,
            text="扫描并载入项目中已有的资源文件",
            font=("Microsoft YaHei UI", 11, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header_frame,
            text="支持：悬浮助手图像、事件配置、项目目录图片等",
            foreground="#666"
        ).pack(anchor="w")

        # 扫描选项
        options_frame = ttk.LabelFrame(self.dialog, text="扫描源")
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        self.scan_vars = {}
        scan_options = [
            ("assistant_images", "悬浮助手图像 (表情/立绘)"),
            ("event_files", "事件配置文件 (JSON)"),
            ("wiki_images", "百科图片 (wiki_images)"),
            ("project_images", "项目目录图片"),
            ("data_dir", "数据目录 (writer_data)"),
        ]

        for i, (key, label) in enumerate(scan_options):
            var = tk.BooleanVar(value=True)
            self.scan_vars[key] = var
            ttk.Checkbutton(options_frame, text=label, variable=var).grid(
                row=i // 2, column=i % 2, sticky="w", padx=10, pady=2
            )

        # 扫描按钮
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="开始扫描", command=self._scan_resources).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="全选", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="取消全选", command=self._deselect_all).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="点击「开始扫描」查找资源")
        ttk.Label(btn_frame, textvariable=self.status_var, foreground="#888").pack(side=tk.RIGHT, padx=5)

        # 结果列表
        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建 Treeview
        columns = ("name", "type", "path", "source")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("name", text="名称")
        self.tree.heading("type", text="类型")
        self.tree.heading("path", text="路径")
        self.tree.heading("source", text="来源")

        self.tree.column("name", width=120)
        self.tree.column("type", width=80)
        self.tree.column("path", width=250)
        self.tree.column("source", width=100)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部按钮
        bottom_frame = ttk.Frame(self.dialog)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(bottom_frame, text="导入选中", command=self._import_selected).pack(side=tk.RIGHT, padx=2)
        ttk.Button(bottom_frame, text="取消", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=2)

    def _get_data_dir(self):
        """获取 writer_data 目录。"""
        # 尝试从项目文件获取
        if self.project_manager.current_file:
            project_dir = Path(self.project_manager.current_file).parent
            data_dir = project_dir / "writer_data"
            if data_dir.exists():
                return data_dir

        # 尝试从脚本目录获取
        try:
            script_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = script_dir / "writer_data"
            if data_dir.exists():
                return data_dir
        except:
            pass

        return None

    def _get_assistant_images_dir(self):
        """获取悬浮助手图像目录。"""
        try:
            script_dir = Path(__file__).resolve().parent
            # 检查多个可能的位置
            candidates = [
                script_dir / "floating_assistant" / "images",
                script_dir / "floating_assistant" / "resources",
                script_dir / "floating_assistant" / "assets",
                script_dir.parent / "resources" / "assistant",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
        except:
            pass
        return None

    def _scan_resources(self):
        """扫描资源。"""
        self.found_resources = []
        self.tree.delete(*self.tree.get_children())

        data_dir = self._get_data_dir()
        valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

        # 扫描悬浮助手图像
        if self.scan_vars.get("assistant_images", tk.BooleanVar()).get():
            assistant_dir = self._get_assistant_images_dir()
            if assistant_dir:
                self._scan_directory(assistant_dir, "sprite", "悬浮助手", valid_exts)

        # 扫描事件配置文件
        if self.scan_vars.get("event_files", tk.BooleanVar()).get():
            if data_dir:
                for json_file in data_dir.glob("*.json"):
                    if "event" in json_file.stem.lower() or json_file.stem == "school_events":
                        self._add_resource({
                            "name": json_file.stem,
                            "type": "reference",
                            "path": str(json_file),
                            "source": "事件配置",
                            "tags": ["事件", "配置"]
                        })

        # 扫描百科图片
        if self.scan_vars.get("wiki_images", tk.BooleanVar()).get():
            if data_dir:
                wiki_dir = data_dir / "wiki_images"
                if wiki_dir.exists():
                    self._scan_directory(wiki_dir, "reference", "百科图片", valid_exts)

        # 扫描项目目录图片
        if self.scan_vars.get("project_images", tk.BooleanVar()).get():
            if self.project_manager.current_file:
                project_dir = Path(self.project_manager.current_file).parent
                # 扫描项目目录下的 images, assets, resources 文件夹
                for subdir_name in ["images", "assets", "resources", "sprites", "backgrounds", "cg"]:
                    subdir = project_dir / subdir_name
                    if subdir.exists():
                        asset_type = "sprite" if subdir_name in ("sprites", "characters") else \
                                    "background" if subdir_name == "backgrounds" else \
                                    "cg" if subdir_name == "cg" else "reference"
                        self._scan_directory(subdir, asset_type, f"项目/{subdir_name}", valid_exts)

        # 扫描数据目录
        if self.scan_vars.get("data_dir", tk.BooleanVar()).get():
            if data_dir:
                # 只扫描根目录的图片，不递归
                for file in data_dir.iterdir():
                    if file.is_file() and file.suffix.lower() in valid_exts:
                        self._add_resource({
                            "name": file.stem,
                            "type": "reference",
                            "path": str(file),
                            "source": "数据目录",
                            "tags": []
                        })

        # 过滤已存在的资源
        existing_paths = {a.get("path", "") for a in self.project_manager.get_galgame_assets()}
        self.found_resources = [r for r in self.found_resources if r["path"] not in existing_paths]

        # 更新列表
        for res in self.found_resources:
            self.tree.insert("", tk.END, values=(
                res["name"],
                AssetTypeRegistry.get_display_name(res["type"]),
                res["path"][:50] + "..." if len(res["path"]) > 50 else res["path"],
                res["source"]
            ))

        self.status_var.set(f"找到 {len(self.found_resources)} 个新资源")

    def _scan_directory(self, directory: Path, asset_type: str, source: str, valid_exts: set):
        """扫描目录中的图像文件。"""
        if not directory.exists():
            return

        for file in directory.rglob("*"):
            if file.is_file() and file.suffix.lower() in valid_exts:
                # 尝试从文件名推断类型
                name_lower = file.stem.lower()
                detected_type = asset_type

                if any(kw in name_lower for kw in ["bg", "background", "scene"]):
                    detected_type = "background"
                elif any(kw in name_lower for kw in ["sprite", "char", "立绘"]):
                    detected_type = "sprite"
                elif any(kw in name_lower for kw in ["cg", "event"]):
                    detected_type = "cg"
                elif any(kw in name_lower for kw in ["ui", "button", "icon"]):
                    detected_type = "ui"

                self._add_resource({
                    "name": file.stem,
                    "type": detected_type,
                    "path": str(file),
                    "source": source,
                    "tags": []
                })

    def _add_resource(self, resource: dict):
        """添加资源到列表。"""
        self.found_resources.append(resource)

    def _select_all(self):
        """全选。"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def _deselect_all(self):
        """取消全选。"""
        self.tree.selection_remove(*self.tree.get_children())

    def _import_selected(self):
        """导入选中的资源。"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要导入的资源")
            return

        count = 0
        items = list(self.tree.get_children())

        for item in selected:
            idx = items.index(item)
            if idx < len(self.found_resources):
                res = self.found_resources[idx]
                asset = {
                    "uid": str(uuid.uuid4()),
                    "name": res["name"],
                    "type": res["type"],
                    "path": res["path"],
                    "character": "",
                    "expression": "",
                    "tags": res.get("tags", [])
                }
                self.project_manager.add_galgame_asset(asset)
                count += 1

        messagebox.showinfo("导入完成", f"已导入 {count} 个资源")
        self.on_import_complete()
        self.dialog.destroy()


class EditAssetDialog:
    """编辑资源对话框 - 使用动态资产类型。"""
    def __init__(self, parent, asset, project_manager, on_save):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑资源")
        self.dialog.geometry("400x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.asset = asset
        self.project_manager = project_manager
        self.on_save = on_save

        self._setup_ui()

    def _get_available_asset_types(self):
        """获取当前项目类型支持的资产类型。"""
        return self.project_manager.get_asset_types()

    def _setup_ui(self):
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="名称:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_var = tk.StringVar(value=self.asset.get("name", ""))
        ttk.Entry(frame, textvariable=self.name_var, width=30).grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="类型:").grid(row=1, column=0, sticky="w", pady=5)
        # 使用动态获取的资产类型
        asset_types = self._get_available_asset_types()
        current_type = self.asset.get("type", asset_types[0] if asset_types else "reference")
        self.type_var = tk.StringVar(value=current_type)
        ttk.Combobox(frame, textvariable=self.type_var, values=asset_types, state="readonly", width=28).grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="关联角色:").grid(row=2, column=0, sticky="w", pady=5)
        chars = ["(无)"] + [c.get("name", "") for c in self.project_manager.get_characters()]
        self.char_var = tk.StringVar(value=self.asset.get("character", "(无)"))
        ttk.Combobox(frame, textvariable=self.char_var, values=chars, width=28).grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="表情/姿势:").grid(row=3, column=0, sticky="w", pady=5)
        self.expr_var = tk.StringVar(value=self.asset.get("expression", ""))
        ttk.Entry(frame, textvariable=self.expr_var, width=30).grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="文件路径:").grid(row=4, column=0, sticky="w", pady=5)
        path_frame = ttk.Frame(frame)
        path_frame.grid(row=4, column=1, sticky="ew", pady=5)
        self.path_var = tk.StringVar(value=self.asset.get("path", ""))
        ttk.Entry(path_frame, textvariable=self.path_var, width=22).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览", command=self._browse).pack(side=tk.RIGHT)

        ttk.Label(frame, text="标签 (逗号分隔):").grid(row=5, column=0, sticky="w", pady=5)
        self.tags_var = tk.StringVar(value=", ".join(self.asset.get("tags", [])))
        ttk.Entry(frame, textvariable=self.tags_var, width=30).grid(row=5, column=1, sticky="ew", pady=5)

        frame.columnconfigure(1, weight=1)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.gif"), ("所有文件", "*.*")]
        )
        if path:
            self.path_var.set(path)

    def _save(self):
        uid = self.asset.get("uid")
        updated = {
            "uid": uid,
            "name": self.name_var.get().strip() or "未命名",
            "type": self.type_var.get(),
            "character": self.char_var.get() if self.char_var.get() != "(无)" else "",
            "expression": self.expr_var.get().strip(),
            "path": self.path_var.get().strip(),
            "tags": [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
        }

        self.project_manager.update_galgame_asset(uid, updated)
        self.on_save()
        self.dialog.destroy()


class AssetManagerController:
    """
    通用资源管理控制器

    根据项目类型动态显示可用的资产类型按钮。
    """
    def __init__(self, parent, project_manager, execute_command=None):
        self.parent = parent
        self.project_manager = project_manager
        self.execute_command = execute_command
        self.add_buttons = []  # 存储动态创建的添加按钮

        self._setup_ui()

    def _get_available_asset_types(self):
        """获取当前项目类型支持的资产类型。"""
        return self.project_manager.get_asset_types()

    def _setup_ui(self):
        # Main paned window
        paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Asset grid
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)

        # Toolbar
        self.toolbar = ttk.Frame(left_frame)
        self.toolbar.pack(fill=tk.X, pady=5)

        # 动态创建添加按钮
        self._rebuild_add_buttons()

        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(self.toolbar, text="载入已有资源", command=self._load_existing_resources).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="批量导入", command=self._batch_import).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=2)

        # Asset panel - 使用通用的 AssetManagerPanel
        self.asset_panel = AssetManagerPanel(left_frame, self.project_manager, self._on_asset_select)
        self.asset_panel.pack(fill=tk.BOTH, expand=True)

        # Right: Detail panel
        self.detail_panel = AssetDetailPanel(paned, self.project_manager)
        paned.add(self.detail_panel, weight=1)

        # Initial refresh
        self.refresh()

    def _rebuild_add_buttons(self):
        """根据项目类型重建添加按钮。"""
        # 清除旧按钮
        for btn in self.add_buttons:
            btn.destroy()
        self.add_buttons = []

        # 根据项目类型添加按钮
        asset_types = self._get_available_asset_types()
        for type_key in asset_types:
            display_name = AssetTypeRegistry.get_display_name(type_key)
            btn = ttk.Button(
                self.toolbar,
                text=f"+ {display_name}",
                command=lambda t=type_key: self._add_asset(t)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.add_buttons.append(btn)

    def _add_asset(self, asset_type):
        """添加新资源。"""
        display_name = AssetTypeRegistry.get_display_name(asset_type)
        file_filter = AssetTypeRegistry.get_file_filter(asset_type)

        path = filedialog.askopenfilename(
            title=f"选择{display_name}文件",
            filetypes=file_filter
        )
        if not path:
            return

        name = Path(path).stem

        asset = {
            "uid": str(uuid.uuid4()),
            "name": name,
            "type": asset_type,
            "path": path,
            "character": "",
            "expression": "",
            "tags": []
        }

        self.project_manager.add_galgame_asset(asset)
        self.refresh()

    def _load_existing_resources(self):
        """打开载入已有资源对话框。"""
        LoadExistingResourcesDialog(
            self.parent.winfo_toplevel(),
            self.project_manager,
            self.refresh
        )

    def _batch_import(self):
        """批量导入资源。"""
        folder = filedialog.askdirectory(title="选择包含文件的文件夹")
        if not folder:
            return

        # 使用动态资产类型
        asset_types = self._get_available_asset_types()
        type_options = "\n".join([f"- {t}: {AssetTypeRegistry.get_display_name(t)}" for t in asset_types])
        default_type = asset_types[0] if asset_types else "reference"

        asset_type = simpledialog.askstring(
            "资源类型",
            f"这批文件的类型是什么？\n\n可选类型：\n{type_options}\n\n请输入类型代码:",
            initialvalue=default_type
        )
        if not asset_type or asset_type not in asset_types:
            asset_type = default_type

        # 获取该类型支持的扩展名
        type_info = AssetTypeRegistry.get(asset_type)
        valid_exts = type_info.file_extensions if type_info else [".png", ".jpg", ".jpeg", ".webp", ".gif"]

        count = 0
        for file in Path(folder).iterdir():
            if file.suffix.lower() in valid_exts:
                asset = {
                    "uid": str(uuid.uuid4()),
                    "name": file.stem,
                    "type": asset_type,
                    "path": str(file),
                    "character": "",
                    "expression": "",
                    "tags": []
                }
                self.project_manager.add_galgame_asset(asset)
                count += 1

        messagebox.showinfo("导入完成", f"已导入 {count} 个资源")
        self.refresh()

    def _on_asset_select(self, asset):
        self.detail_panel.show_asset(asset)

    def refresh(self):
        """刷新资源列表（项目类型可能已更改）。"""
        # 重建添加按钮（如果项目类型改变）
        self._rebuild_add_buttons()
        # 刷新资源面板
        self.asset_panel.refresh()
        # 更新详情面板的类型下拉框
        if hasattr(self.detail_panel, 'type_combo'):
            self.detail_panel.type_combo['values'] = self._get_available_asset_types()

    def pack(self, **kwargs):
        self.parent.pack(**kwargs)


# 兼容旧代码的别名
GalgameAssetsController = AssetManagerController
