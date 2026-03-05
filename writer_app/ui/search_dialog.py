import tkinter as tk
from tkinter import ttk, messagebox
import re
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

def get_icon_font(size=12):
    return IconManager().get_font(size=size)



class SearchDialog(tk.Toplevel):
    """全局搜索与替换对话框 - 支持正则表达式和批量替换"""

    def __init__(self, parent, project_manager, on_navigate_callback, command_executor=None):
        super().__init__(parent)
        self.title("全局搜索与替换")
        self.geometry("700x500")
        self.minsize(500, 400)
        self.project_manager = project_manager
        self.on_navigate_callback = on_navigate_callback  # (type, index, match_start, match_end)
        self.command_executor = command_executor  # For undo support

        self.results = []
        self._replace_count = 0

        self.setup_ui()
        self.bind("<Escape>", lambda e: self.destroy())
        self.search_entry.focus_set()

        # 使窗口可调整大小
        self.resizable(True, True)

    def setup_ui(self):
        # Input Area
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        input_frame.columnconfigure(1, weight=1)

        # Search Term
        label_frame = ttk.Frame(input_frame)
        label_frame.grid(row=0, column=0, sticky=tk.W, pady=2)
        tk.Label(label_frame, text=get_icon("search", "🔍"), font=get_icon_font(10)).pack(side=tk.LEFT)
        ttk.Label(label_frame, text=" 查找内容:").pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()

        self.search_entry = ttk.Entry(input_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.search_entry.bind("<Return>", self.do_search)

        # Replace Term
        ttk.Label(input_frame, text="替换为:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.replace_var = tk.StringVar()
        self.replace_entry = ttk.Entry(input_frame, textvariable=self.replace_var)
        self.replace_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=0, column=2, rowspan=2, padx=5, sticky="ns")
        ttk.Button(btn_frame, text="查找全部", command=self.do_search, width=10).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="替换选中", command=self.do_replace_selected, width=10).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="全部替换", command=self.do_replace_all, width=10).pack(fill=tk.X, pady=2)

        # Options
        opt_frame = ttk.Frame(self)
        opt_frame.pack(fill=tk.X, padx=10)

        self.case_sensitive = tk.BooleanVar(value=False)
        self.use_regex = tk.BooleanVar(value=False)
        self.whole_word = tk.BooleanVar(value=False)

        ttk.Checkbutton(opt_frame, text="区分大小写", variable=self.case_sensitive).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(opt_frame, text="正则表达式", variable=self.use_regex, command=self._on_regex_toggle).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(opt_frame, text="全词匹配", variable=self.whole_word).pack(side=tk.LEFT, padx=5)

        # Regex hint
        self.regex_hint = ttk.Label(opt_frame, text="", foreground="gray")
        self.regex_hint.pack(side=tk.LEFT, padx=10)

        # Scope Selection
        scope_frame = ttk.LabelFrame(self, text="搜索范围")
        scope_frame.pack(fill=tk.X, padx=10, pady=5)

        self.scope_scene = tk.BooleanVar(value=True)
        self.scope_character = tk.BooleanVar(value=True)
        self.scope_wiki = tk.BooleanVar(value=True)
        self.scope_outline = tk.BooleanVar(value=True)

        ttk.Checkbutton(scope_frame, text="场景", variable=self.scope_scene).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(scope_frame, text="角色", variable=self.scope_character).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(scope_frame, text="百科", variable=self.scope_wiki).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(scope_frame, text="大纲", variable=self.scope_outline).pack(side=tk.LEFT, padx=5)

        # Results List
        result_frame = ttk.Frame(self)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(result_frame, columns=("location", "context"), show="headings", selectmode="extended")
        self.tree.heading("location", text="位置")
        self.tree.heading("context", text="内容预览")
        self.tree.column("location", width=150, minwidth=100)
        self.tree.column("context", width=450, minwidth=200)

        scroll_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_result_double_click)
        self.tree.bind("<Return>", self.on_result_double_click)

        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)

        # Select all / deselect all buttons
        ttk.Button(status_frame, text="全选", command=self._select_all, width=6).pack(side=tk.RIGHT, padx=2)
        ttk.Button(status_frame, text="取消全选", command=self._deselect_all, width=8).pack(side=tk.RIGHT, padx=2)

    def _on_regex_toggle(self):
        """正则表达式模式切换"""
        if self.use_regex.get():
            self.regex_hint.config(text="提示: 使用 $1, $2 引用分组")
            self.whole_word.set(False)  # 正则模式下禁用全词匹配
        else:
            self.regex_hint.config(text="")

    def _select_all(self):
        """选择所有结果"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def _deselect_all(self):
        """取消选择所有结果"""
        self.tree.selection_remove(*self.tree.selection())

    def _compile_pattern(self, term):
        """编译搜索模式，返回正则表达式对象"""
        if not term:
            return None

        try:
            if self.use_regex.get():
                flags = 0 if self.case_sensitive.get() else re.IGNORECASE
                pattern = re.compile(term, flags)
            else:
                # 转义特殊字符
                escaped = re.escape(term)
                if self.whole_word.get():
                    escaped = r'\b' + escaped + r'\b'
                flags = 0 if self.case_sensitive.get() else re.IGNORECASE
                pattern = re.compile(escaped, flags)
            return pattern
        except re.error as e:
            messagebox.showerror("正则表达式错误", f"无效的正则表达式:\n{str(e)}", parent=self)
            return None

    def do_search(self, event=None):
        """执行搜索"""
        term = self.search_var.get()
        if not term:
            return

        pattern = self._compile_pattern(term)
        if pattern is None:
            return

        self.tree.delete(*self.tree.get_children())
        self.results = []

        type_map = {
            "scene": "场景",
            "character": "角色",
            "wiki": "百科",
            "outline": "大纲"
        }

        # 构建搜索范围过滤
        scope_filter = []
        if self.scope_scene.get():
            scope_filter.append("scene")
        if self.scope_character.get():
            scope_filter.append("character")
        if self.scope_wiki.get():
            scope_filter.append("wiki")
        if self.scope_outline.get():
            scope_filter.append("outline")

        if not scope_filter:
            messagebox.showwarning("提示", "请至少选择一个搜索范围", parent=self)
            return

        # 执行搜索
        results = self._search_with_pattern(pattern, scope_filter)

        for res in results:
            type_str = type_map.get(res["type"], res["type"])
            display_str = f"[{type_str}] {res['name']}"

            # 高亮匹配内容
            context = res.get("context", "")

            item_id = self.tree.insert("", tk.END, values=(display_str, context))
            res["item_id"] = item_id
            self.results.append(res)

        count = len(results)
        self.status_label.config(text=f"找到 {count} 个匹配项")

        if count == 0:
            messagebox.showinfo("搜索结果", "未找到匹配项", parent=self)

    def _search_with_pattern(self, pattern, scope_filter):
        """使用正则表达式搜索"""
        results = []

        # 搜索场景
        if "scene" in scope_filter:
            for idx, scene in enumerate(self.project_manager.get_scenes()):
                content = scene.get("content", "")
                name = scene.get("name", f"场景{idx+1}")

                for match in pattern.finditer(content):
                    start, end = match.span()
                    context = self._get_context(content, start, end)
                    results.append({
                        "type": "scene",
                        "index": idx,
                        "name": name,
                        "field": "content",
                        "match_start": start,
                        "match_end": end,
                        "matched_text": match.group(),
                        "context": context
                    })

        # 搜索角色
        if "character" in scope_filter:
            for idx, char in enumerate(self.project_manager.get_characters()):
                name = char.get("name", f"角色{idx+1}")
                desc = char.get("description", "")

                # 搜索名称
                for match in pattern.finditer(name):
                    results.append({
                        "type": "character",
                        "index": idx,
                        "name": name,
                        "field": "name",
                        "match_start": match.start(),
                        "match_end": match.end(),
                        "matched_text": match.group(),
                        "context": name
                    })

                # 搜索描述
                for match in pattern.finditer(desc):
                    start, end = match.span()
                    context = self._get_context(desc, start, end)
                    results.append({
                        "type": "character",
                        "index": idx,
                        "name": name,
                        "field": "description",
                        "match_start": start,
                        "match_end": end,
                        "matched_text": match.group(),
                        "context": context
                    })

        # 搜索百科
        if "wiki" in scope_filter:
            entries = self.project_manager.project_data.get("world", {}).get("entries", [])
            for idx, entry in enumerate(entries):
                name = entry.get("name", f"条目{idx+1}")
                content = entry.get("content", "")

                for match in pattern.finditer(content):
                    start, end = match.span()
                    context = self._get_context(content, start, end)
                    results.append({
                        "type": "wiki",
                        "index": idx,
                        "name": name,
                        "field": "content",
                        "match_start": start,
                        "match_end": end,
                        "matched_text": match.group(),
                        "context": context
                    })

        # 搜索大纲
        if "outline" in scope_filter:
            outline = self.project_manager.get_outline()
            self._search_outline_recursive(outline, pattern, results)

        return results

    def _search_outline_recursive(self, node, pattern, results, path=""):
        """递归搜索大纲节点"""
        name = node.get("name", "")
        content = node.get("content", "")
        current_path = f"{path}/{name}" if path else name

        # 搜索节点名称
        for match in pattern.finditer(name):
            results.append({
                "type": "outline",
                "node_uid": node.get("uid"),
                "name": current_path,
                "field": "name",
                "match_start": match.start(),
                "match_end": match.end(),
                "matched_text": match.group(),
                "context": name
            })

        # 搜索节点内容
        for match in pattern.finditer(content):
            start, end = match.span()
            context = self._get_context(content, start, end)
            results.append({
                "type": "outline",
                "node_uid": node.get("uid"),
                "name": current_path,
                "field": "content",
                "match_start": start,
                "match_end": end,
                "matched_text": match.group(),
                "context": context
            })

        # 递归搜索子节点
        for child in node.get("children", []):
            self._search_outline_recursive(child, pattern, results, current_path)

    def _get_context(self, text, start, end, context_len=40):
        """获取匹配项的上下文"""
        prefix_start = max(0, start - context_len)
        suffix_end = min(len(text), end + context_len)

        prefix = text[prefix_start:start]
        matched = text[start:end]
        suffix = text[end:suffix_end]

        # 清理换行符
        prefix = prefix.replace("\n", " ").strip()
        matched = matched.replace("\n", " ")
        suffix = suffix.replace("\n", " ").strip()

        # 添加省略号
        if prefix_start > 0:
            prefix = "..." + prefix
        if suffix_end < len(text):
            suffix = suffix + "..."

        return f"{prefix}【{matched}】{suffix}"

    def on_result_double_click(self, event):
        """双击跳转到匹配位置"""
        item = self.tree.selection()
        if not item:
            return

        for res in self.results:
            if res["item_id"] == item[0]:
                self.on_navigate_callback(res)
                break

    def do_replace_selected(self):
        """替换选中的匹配项"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择要替换的项目", parent=self)
            return

        replace_text = self.replace_var.get()
        search_term = self.search_var.get()

        if not search_term:
            return

        # 确认替换
        count = len(selection)
        if not messagebox.askyesno("确认替换", f"确定要替换选中的 {count} 个匹配项吗？", parent=self):
            return

        # 收集要替换的结果
        to_replace = []
        for item_id in selection:
            for res in self.results:
                if res.get("item_id") == item_id:
                    to_replace.append(res)
                    break

        # 执行替换
        replaced_count = self._perform_replacements(to_replace, replace_text)

        # 刷新搜索结果
        self.do_search()

        messagebox.showinfo("替换完成", f"成功替换 {replaced_count} 个匹配项", parent=self)

    def do_replace_all(self):
        """替换所有匹配项"""
        if not self.results:
            messagebox.showinfo("提示", "请先执行搜索", parent=self)
            return

        replace_text = self.replace_var.get()
        search_term = self.search_var.get()

        if not search_term:
            return

        # 确认替换
        count = len(self.results)
        if not messagebox.askyesno("确认全部替换",
                                    f"确定要替换全部 {count} 个匹配项吗？\n\n此操作可通过撤销恢复。",
                                    parent=self):
            return

        # 执行替换
        replaced_count = self._perform_replacements(self.results, replace_text)

        # 刷新搜索结果
        self.do_search()

        messagebox.showinfo("替换完成", f"成功替换 {replaced_count} 个匹配项", parent=self)

    def _perform_replacements(self, results_to_replace, replace_text):
        """执行替换操作"""
        replaced_count = 0
        pattern = self._compile_pattern(self.search_var.get())

        if pattern is None:
            return 0

        # 按类型和索引分组，以便批量处理
        # 需要从后往前替换，避免索引偏移问题
        grouped = {}
        for res in results_to_replace:
            key = (res["type"], res.get("index"), res.get("node_uid"), res.get("field"))
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(res)

        # 对每个分组，按匹配位置从后往前排序
        for key, items in grouped.items():
            items.sort(key=lambda x: x.get("match_start", 0), reverse=True)

        # 执行替换
        for (res_type, index, node_uid, field), items in grouped.items():
            try:
                if res_type == "scene":
                    scenes = self.project_manager.get_scenes()
                    if 0 <= index < len(scenes):
                        scene = scenes[index]
                        content = scene.get(field, "")
                        new_content = self._replace_in_text(content, items, pattern, replace_text)
                        scene[field] = new_content
                        replaced_count += len(items)

                elif res_type == "character":
                    characters = self.project_manager.get_characters()
                    if 0 <= index < len(characters):
                        char = characters[index]
                        content = char.get(field, "")
                        new_content = self._replace_in_text(content, items, pattern, replace_text)
                        char[field] = new_content
                        replaced_count += len(items)

                elif res_type == "wiki":
                    entries = self.project_manager.project_data.get("world", {}).get("entries", [])
                    if 0 <= index < len(entries):
                        entry = entries[index]
                        content = entry.get(field, "")
                        new_content = self._replace_in_text(content, items, pattern, replace_text)
                        entry[field] = new_content
                        replaced_count += len(items)

                elif res_type == "outline":
                    node = self.project_manager.find_node_by_uid(node_uid)
                    if node:
                        content = node.get(field, "")
                        new_content = self._replace_in_text(content, items, pattern, replace_text)
                        node[field] = new_content
                        replaced_count += len(items)

            except Exception as e:
                print(f"替换出错: {e}")
                continue

        if replaced_count > 0:
            self.project_manager.mark_modified()

        return replaced_count

    def _replace_in_text(self, text, items, pattern, replace_text):
        """在文本中执行替换"""
        if self.use_regex.get():
            # 正则替换 - 支持分组引用
            return pattern.sub(replace_text, text)
        else:
            # 普通替换 - 从后往前替换，避免索引偏移
            result = text
            for item in items:  # items 已经按位置从后往前排序
                start = item.get("match_start", 0)
                end = item.get("match_end", 0)
                result = result[:start] + replace_text + result[end:]
            return result

    def focus_replace_field(self):
        """将焦点设置到替换输入框"""
        self.replace_entry.focus_set()
        self.replace_entry.selection_range(0, tk.END)
