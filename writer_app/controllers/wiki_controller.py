import json
import os
import re
import shutil
import uuid
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog

from PIL import Image, ImageTk

from writer_app.controllers.base_controller import BaseController
from writer_app.core.thread_pool import get_ai_thread_pool
from writer_app.core.commands import (
    AddWikiEntryCommand,
    DeleteWikiEntryCommand,
    EditWikiEntryCommand,
)
from writer_app.core.tts import TTSManager
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.ui.help_dialog import create_module_help_button


class WikiController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager, ai_client, config_manager, on_jump_to_scene=None):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.ai_client = ai_client
        self.config_manager = config_manager
        self.on_jump_to_scene = on_jump_to_scene

        self.wiki_name_var = tk.StringVar()
        self.wiki_category_var = tk.StringVar()
        self.image_path_var = tk.StringVar()

        # 从ProjectManager获取动态分类
        self.wiki_categories = self.project_manager.get_wiki_categories()
        self.image_preview_label = None
        self.current_image_obj = None
        self.wiki_tree = None
        self.wiki_content_text = None
        self.ai_gen_btn = None
        self.consistency_check_btn = None
        self.category_combobox = None  # 保存引用以便更新

        self.setup_ui()
        self._add_theme_listener(self.apply_theme)
        self.refresh()
        self.set_ai_mode_enabled(self.config_manager.is_ai_enabled())
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅事件总线以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.WIKI_ENTRY_ADDED, self._on_wiki_changed)
        self._subscribe_event(Events.WIKI_ENTRY_UPDATED, self._on_wiki_changed)
        self._subscribe_event(Events.WIKI_ENTRY_DELETED, self._on_wiki_changed)
        self._subscribe_event(Events.PROJECT_LOADED, self._on_project_loaded)
        self._subscribe_event(Events.CHARACTER_ADDED, self._on_character_changed)
        self._subscribe_event(Events.CHARACTER_UPDATED, self._on_character_changed)
        self._subscribe_event(Events.CHARACTER_DELETED, self._on_character_changed)

    def _on_wiki_changed(self, event_type=None, **kwargs):
        """响应Wiki条目变化事件"""
        self.refresh()

    def _on_project_loaded(self, event_type=None, **kwargs):
        """响应项目加载事件"""
        self.wiki_categories = self.project_manager.get_wiki_categories()
        if self.category_combobox:
            self.category_combobox['values'] = self.wiki_categories
        self.refresh()

    def _on_character_changed(self, event_type=None, **kwargs):
        """响应角色变化事件 - 角色可能同步到Wiki"""
        self.refresh()

    def setup_ui(self):
        paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Left: Tree List ---
        list_frame = ttk.LabelFrame(paned, text="条目列表")
        paned.add(list_frame, weight=1)

        toolbar = ttk.Frame(list_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="+ 添加条目", command=self.add_wiki_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除条目", command=self.delete_wiki_entry).pack(side=tk.LEFT, padx=2)
        
        # New Button for Consistency Check
        self.consistency_check_btn = ttk.Button(toolbar, text="🔍 设定冲突检查", command=self.check_consistency)
        self.consistency_check_btn.pack(side=tk.LEFT, padx=2)

        # 帮助按钮
        help_btn = create_module_help_button(toolbar, "wiki", self._show_full_help)
        help_btn.pack(side=tk.RIGHT, padx=4)

        self.wiki_tree = ttk.Treeview(list_frame, selectmode="browse", show="tree")
        self.wiki_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        wiki_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.wiki_tree.yview)
        wiki_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.wiki_tree.configure(yscrollcommand=wiki_scroll.set)
        self.wiki_tree.bind("<<TreeviewSelect>>", self.on_wiki_select)

        # --- Right: Details ---
        detail_frame = ttk.LabelFrame(paned, text="条目详情")
        paned.add(detail_frame, weight=3)

        # -- Top Input Area --
        input_frame = ttk.Frame(detail_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(input_frame, text="名称:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(input_frame, textvariable=self.wiki_name_var).grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(input_frame, text="分类:").grid(row=0, column=2, sticky=tk.W)
        self.category_combobox = ttk.Combobox(input_frame, textvariable=self.wiki_category_var, values=self.wiki_categories, state="readonly")
        self.category_combobox.grid(row=0, column=3, sticky="ew", padx=5)

        btn_box = ttk.Frame(input_frame)
        btn_box.grid(row=0, column=4, padx=5)
        ttk.Button(btn_box, text="保存条目", command=self.save_wiki_entry).pack(side=tk.LEFT, padx=2)
        self.ai_gen_btn = ttk.Button(btn_box, text="💡 AI启发", command=self.ai_generate_entry)
        self.ai_gen_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="🔊 朗读", command=self.read_entry).pack(side=tk.LEFT, padx=2)

        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)

        # -- Image Area --
        img_frame = ttk.LabelFrame(detail_frame, text="图片")
        img_frame.pack(fill=tk.X, padx=5, pady=5)

        btn_frame = ttk.Frame(img_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(btn_frame, text="选择图片", command=self.select_image).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清除图片", command=self.clear_image).pack(fill=tk.X, pady=2)

        self.image_preview_label = ttk.Label(img_frame, text="无图片")
        self.image_preview_label.pack(side=tk.LEFT, padx=10, pady=5)

        # -- Related Scenes --
        related_frame = ttk.LabelFrame(detail_frame, text="关联引用 (双击跳转)")
        related_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.related_scenes_listbox = tk.Listbox(related_frame, height=4)
        self.related_scenes_listbox.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.related_scenes_listbox.bind("<Double-1>", self._jump_to_related_scene)

        # -- Content Area --
        self.wiki_content_text = tk.Text(detail_frame, wrap=tk.WORD, font=("Microsoft YaHei", 10))
        content_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.wiki_content_text.yview)
        self.wiki_content_text.configure(yscrollcommand=content_scroll.set)
        self.wiki_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        content_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Hyperlink config
        self.wiki_content_text.tag_config("hyperlink", foreground="blue", underline=True)
        self.wiki_content_text.tag_bind("hyperlink", "<Button-1>", self.on_text_click)
        self.wiki_content_text.bind("<KeyRelease>", self.on_text_edit)

    def on_text_edit(self, event):
        """Re-highlight on edit (with simple debounce or just run it)."""
        # For performance, maybe don't run on every keystroke, but for now it's fine for small texts
        self.highlight_keywords()

    def highlight_keywords(self):
        """Scan text and highlight names of other wiki entries."""
        if not self.wiki_content_text: return
        
        # Remove old tags
        self.wiki_content_text.tag_remove("hyperlink", "1.0", tk.END)
        
        content = self.wiki_content_text.get("1.0", tk.END)
        if not content.strip(): return
        
        entries = self.project_manager.get_world_entries()
        current_name = self.wiki_name_var.get()
        
        # Build a regex of all entry names (sorted by length descending to match longest first)
        names = [e["name"] for e in entries if e["name"] and e["name"] != current_name]
        names.sort(key=len, reverse=True)
        
        if not names: return
        
        # Simple keyword matching
        for name in names:
            start_idx = "1.0"
            while True:
                idx = self.wiki_content_text.search(name, start_idx, stopindex=tk.END)
                if not idx:
                    break
                
                end_idx = f"{idx}+{len(name)}c"
                self.wiki_content_text.tag_add("hyperlink", idx, end_idx)
                start_idx = end_idx

    def on_text_click(self, event):
        """Handle click on hyperlink tag."""
        try:
            index = self.wiki_content_text.index(f"@{event.x},{event.y}")
            tags = self.wiki_content_text.tag_names(index)
            if "hyperlink" in tags:
                # Find which word was clicked
                # We need to find the range of the tag at this index
                tag_ranges = self.wiki_content_text.tag_ranges("hyperlink")
                for i in range(0, len(tag_ranges), 2):
                    start = tag_ranges[i]
                    end = tag_ranges[i+1]
                    if self.wiki_content_text.compare(start, "<=", index) and self.wiki_content_text.compare(index, "<", end):
                        text = self.wiki_content_text.get(start, end)
                        self.select_entry_by_name(text)
                        break
        except Exception:
            pass

    def read_entry(self):
        content = self.wiki_content_text.get("1.0", tk.END).strip()
        if content:
            TTSManager().speak(content)
        else:
            messagebox.showinfo("提示", "没有内容可朗读")

    def check_consistency(self):
        """Check for conflicts between wiki and script using AI."""
        if not self.config_manager.is_ai_enabled():
            messagebox.showinfo("提示", "当前为非AI模式，设定冲突检查不可用。")
            return
        if not self.config_manager.get("lm_api_url") or not self.config_manager.get("lm_api_model"):
            messagebox.showwarning("提示", "请先在设置中配置 AI 接口。" )
            return

        # 1. Gather Data
        wiki_entries = self.project_manager.get_world_entries()
        if not wiki_entries:
            messagebox.showinfo("提示", "暂无世界观条目。" )
            return
            
        script_scenes = self.project_manager.get_scenes()
        if not script_scenes:
            messagebox.showinfo("提示", "暂无剧本场景。" )
            return

        # Prepare context (Summarize to save tokens)
        wiki_text = "【世界观设定/Wiki】\n"
        for entry in wiki_entries:
            wiki_text += f"- {entry.get('name')} ({entry.get('category')}): {entry.get('content')[:200]}\n"
            
        script_text = "【剧本内容摘要】\n"
        for i, scene in enumerate(script_scenes[:20]): # Limit to first 20 scenes or summarize
            script_text += f"场景 {i+1} {scene.get('name')}: {scene.get('content')[:300]}...\n"
            
        prompt = f"""请分析以下【世界观设定】和【剧本内容】，找出其中可能存在的冲突或不一致之处（例如角色性格、外貌描述、物品功能、地点方位等）。
        
{wiki_text}

{script_text}

请列出你发现的冲突点，如果没发现明显冲突，请说明“未发现明显冲突”。"""

        self.consistency_check_btn.state(["disabled"])
        self.parent.config(cursor="watch")

        def run():
            return self.ai_client.call_lm_studio(
                self.config_manager.get("lm_api_url"),
                self.config_manager.get("lm_api_model"),
                self.config_manager.get("lm_api_key", ""),
                prompt
            )

        def on_success(res):
            self._show_consistency_result(res)

        def on_error(e):
            messagebox.showerror("错误", f"AI 分析失败: {e}")

        def on_complete():
            self.consistency_check_btn.state(["!disabled"])
            self.parent.config(cursor="")

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="wiki_consistency_check",
            fn=run,
            on_success=on_success,
            on_error=on_error,
            on_complete=on_complete,
            tk_root=self.parent
        )

    def _show_consistency_result(self, result):
        if not result: return
        
        dlg = tk.Toplevel(self.parent)
        dlg.title("设定冲突检查结果")
        dlg.geometry("600x500")
        
        text_area = tk.Text(dlg, wrap=tk.WORD, font=("Microsoft YaHei", 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_area.insert("1.0", result)
        text_area.config(state=tk.DISABLED)
        
        ttk.Button(dlg, text="关闭", command=dlg.destroy).pack(pady=5)

    def ai_generate_entry(self):
        if not self.config_manager.is_ai_enabled():
            messagebox.showinfo("提示", "当前为非AI模式，AI启发不可用。")
            return
        url = self.config_manager.get("lm_api_url")
        model = self.config_manager.get("lm_api_model")
        if not url or not model:
            messagebox.showwarning("提示", "请先在设置中配置 AI 接口。" )
            return

        category = self.wiki_category_var.get() or "设定"
        name = self.wiki_name_var.get().strip()

        prompt = f"请为我的剧本生成一个【{category}】设定。"
        if name:
            prompt += f"名称叫作：{name}。"
        else:
            prompt += "请随机生成一个富有创意的名称。"
        prompt += "\n要求：输出格式为 JSON，包含 'name' 和 'description' 两个字段。描述请控制在 200 字以内，风格契合剧本创作。"

        self.ai_gen_btn.state(["disabled"])
        self.parent.config(cursor="watch")

        def run():
            res = self.ai_client.call_lm_studio(url, model, self.config_manager.get("lm_api_key", ""), prompt)
            match = re.search(r"\{.*\}", res, re.DOTALL)
            data = None
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    data = None
            if data is None:
                data = {"description": res}
            return data

        def on_success(data):
            self._apply_ai_result(data)

        def on_error(e):
            messagebox.showerror("错误", f"AI 生成失败: {e}")

        def on_complete():
            self.ai_gen_btn.state(["!disabled"])
            self.parent.config(cursor="")

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="wiki_ai_generate",
            fn=run,
            on_success=on_success,
            on_error=on_error,
            on_complete=on_complete,
            tk_root=self.parent
        )

    def _apply_ai_result(self, data):
        if data.get("name"):
            self.wiki_name_var.set(data["name"])
        if data.get("description"):
            self.wiki_content_text.delete("1.0", tk.END)
            self.wiki_content_text.insert("1.0", data["description"])
        messagebox.showinfo("成功", "AI 设定生成完成！记得点击保存。" )

    def refresh(self):
        # 更新分类列表（可能因项目类型变化）
        self.wiki_categories = self.project_manager.get_wiki_categories()
        if self.category_combobox:
            self.category_combobox['values'] = self.wiki_categories

        selected_idx = None
        sel = self.wiki_tree.selection()
        if sel:
            values = self.wiki_tree.item(sel[0], "values")
            if values:
                selected_idx = int(values[0])

        for item in self.wiki_tree.get_children():
            self.wiki_tree.delete(item)

        category_nodes = {}
        for cat in self.wiki_categories:
            node_id = self.wiki_tree.insert("", "end", text=cat, open=True)
            category_nodes[cat] = node_id

        category_nodes["其他"] = category_nodes.get("其他") or self.wiki_tree.insert("", "end", text="其他", open=True)

        entries = self.project_manager.get_world_entries()
        select_item_id = None
        for idx, entry in enumerate(entries):
            name = entry.get("name", "未命名")
            cat = entry.get("category", "其他")
            parent_node = category_nodes.get(cat)
            if not parent_node:
                parent_node = self.wiki_tree.insert("", "end", text=cat, open=True)
                category_nodes[cat] = parent_node
            item_id = self.wiki_tree.insert(parent_node, "end", text=name, values=(idx,), tags=("item",))
            if selected_idx is not None and idx == selected_idx:
                select_item_id = item_id

        if select_item_id:
            self.wiki_tree.selection_set(select_item_id)
            self.wiki_tree.see(select_item_id)
        else:
            self._clear_details()

    def apply_theme(self):
        theme = self.theme_manager
        bg = theme.get_color("editor_bg")
        fg = theme.get_color("editor_fg")
        self.wiki_content_text.configure(bg=bg, fg=fg, insertbackground=fg)
        self.wiki_tree.tag_configure("item", foreground="black")

    def set_ai_mode_enabled(self, enabled: bool):
        if enabled:
            if self.ai_gen_btn:
                self.ai_gen_btn.pack(side=tk.LEFT, padx=2)
            if self.consistency_check_btn:
                self.consistency_check_btn.pack(side=tk.LEFT, padx=2)
        else:
            if self.ai_gen_btn:
                self.ai_gen_btn.pack_forget()
            if self.consistency_check_btn:
                self.consistency_check_btn.pack_forget()

    def add_wiki_entry(self):
        name = simpledialog.askstring("添加条目", "名称:", parent=self.parent)
        if not name:
            return
        data = {"name": name.strip(), "category": "其他", "content": "", "image_path": ""}
        command = AddWikiEntryCommand(self.project_manager, data)
        self.command_executor(command)
        self.refresh()

    def delete_wiki_entry(self):
        sel_item = self.wiki_tree.selection()
        if not sel_item:
            return
        item_values = self.wiki_tree.item(sel_item[0], "values")
        if not item_values:
            return
        idx = int(item_values[0])
        if messagebox.askyesno("确认", "删除此条目?"):
            data = self.project_manager.get_world_entries()[idx]
            command = DeleteWikiEntryCommand(self.project_manager, idx, data)
            self.command_executor(command)
            self.refresh()
            self._clear_details()

    def on_wiki_select(self, event):
        sel_item = self.wiki_tree.selection()
        if not sel_item:
            return
        item_values = self.wiki_tree.item(sel_item[0], "values")
        if not item_values:
            self._clear_details()
            return

        idx = int(item_values[0])
        entries = self.project_manager.get_world_entries()
        if not (0 <= idx < len(entries)):
            self._clear_details()
            return

        entry = entries[idx]
        self.wiki_name_var.set(entry.get("name", ""))
        self.wiki_category_var.set(entry.get("category", "其他"))
        self.wiki_content_text.delete("1.0", tk.END)
        self.wiki_content_text.insert("1.0", entry.get("content", ""))
        self.highlight_keywords() # Apply highlighting
        img_path = entry.get("image_path", "")
        self.image_path_var.set(img_path)
        self._load_image_preview(img_path)
        
        # Update related references (Scenes & Other Wiki Entries)
        self._refresh_references(entry.get("name", ""))

    def _refresh_references(self, name):
        """Find scenes and other wiki entries that mention this entry."""
        self.related_scenes_listbox.delete(0, tk.END)
        if not name:
            return
            
        # 1. Search Scenes
        matches = self.project_manager.get_scenes_containing_text(name)
        for idx, scene in matches:
            self.related_scenes_listbox.insert(tk.END, f"[剧本] {idx+1}. {scene.get('name', '')}")

        # 2. Search Other Wiki Entries
        all_entries = self.project_manager.get_world_entries()
        for idx, entry in enumerate(all_entries):
            if entry.get("name") == name: continue # Skip self
            
            content = entry.get("content", "")
            if name in content:
                 self.related_scenes_listbox.insert(tk.END, f"[设定] {entry.get('name', '')}")

    def _jump_to_related_scene(self, event):
        if not self.on_jump_to_scene:
            return
            
        sel = self.related_scenes_listbox.curselection()
        if not sel:
            return
            
        text = self.related_scenes_listbox.get(sel[0])
        
        # Handle jump based on type
        if text.startswith("[剧本]"):
            try:
                # Format: "[剧本] Index. Name"
                # Split by ". " to get "Index"
                part1 = text.split(". ")[0] # "[剧本] 1"
                idx = int(part1.split("] ")[1]) - 1
                self.on_jump_to_scene(idx)
            except Exception:
                pass
        elif text.startswith("[设定]"):
            # Format: "[设定] EntryName"
            entry_name = text.split("] ")[1]
            self.select_entry_by_name(entry_name)

    def _clear_details(self):
        self.wiki_name_var.set("")
        self.wiki_category_var.set("")
        self.wiki_content_text.delete("1.0", tk.END)
        self.image_path_var.set("")
        if self.image_preview_label:
            self.image_preview_label.configure(image="", text="无图片")
        self.current_image_obj = None

    def select_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if not path:
            return

        storage_dir = os.path.join(os.getcwd(), "writer_data", "wiki_images")
        os.makedirs(storage_dir, exist_ok=True)

        ext = os.path.splitext(path)[1]
        new_filename = f"{uuid.uuid4().hex}{ext}"
        new_path = os.path.join(storage_dir, new_filename)

        try:
            shutil.copy2(path, new_path)
            rel_path = os.path.join("writer_data", "wiki_images", new_filename)
            self.image_path_var.set(rel_path)
            self._load_image_preview(rel_path)
        except Exception as e:
            messagebox.showerror("错误", f"保存图片失败: {e}")

    def clear_image(self):
        self.image_path_var.set("")
        if self.image_preview_label:
            self.image_preview_label.configure(image="", text="无图片")
        self.current_image_obj = None

    def _load_image_preview(self, path):
        if not path or not os.path.exists(path):
            if self.image_preview_label:
                self.image_preview_label.configure(image="", text="无图片")
            self.current_image_obj = None
            return

        try:
            pil_img = Image.open(path)
            pil_img.thumbnail((150, 150))
            tk_img = ImageTk.PhotoImage(pil_img)
            self.image_preview_label.configure(image=tk_img, text="")
            self.current_image_obj = tk_img
        except Exception:
            if self.image_preview_label:
                self.image_preview_label.configure(image="", text="图片加载失败")
            self.current_image_obj = None

    def save_wiki_entry(self):
        sel_item = self.wiki_tree.selection()
        if not sel_item:
            return messagebox.showwarning("提示", "请选择需要保存的条目。" )

        item_values = self.wiki_tree.item(sel_item[0], "values")
        if not item_values:
            return messagebox.showwarning("提示", "请选择具体条目而不是分类。" )

        idx = int(item_values[0])
        entries = self.project_manager.get_world_entries()
        if not (0 <= idx < len(entries)):
            return messagebox.showerror("错误", "未找到对应条目。" )

        old_data = entries[idx]
        new_data = {
            "name": self.wiki_name_var.get().strip() or "未命名",
            "category": self.wiki_category_var.get() or "其他",
            "content": self.wiki_content_text.get("1.0", tk.END).strip(),
            "image_path": self.image_path_var.get().strip(),
        }
        command = EditWikiEntryCommand(self.project_manager, idx, old_data, new_data)
        self.command_executor(command)
        self.refresh()

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "wiki")

    def select_entry_by_name(self, name):
        """Find and select a wiki entry by name."""
        for item_id in self.wiki_tree.get_children():
            # Check children of category nodes
            for child_id in self.wiki_tree.get_children(item_id):
                if self.wiki_tree.item(child_id, "text") == name:
                    self.wiki_tree.selection_set(child_id)
                    self.wiki_tree.see(child_id)
                    self.on_wiki_select(None)
                    return True
        return False
