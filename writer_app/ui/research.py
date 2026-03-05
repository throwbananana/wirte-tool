import tkinter as tk
from tkinter import ttk
import webbrowser
from writer_app.ui.components.empty_state_panel import EmptyStatePanel, EmptyStateConfig

class ResearchPanel(ttk.Frame):
    def __init__(self, parent, project_manager, theme_manager):
        super().__init__(parent)
        self.project_manager = project_manager
        self.theme_manager = theme_manager
        self.controller = None
        self.root = parent.winfo_toplevel()
        self.current_item_uid = None
        self._empty_state_visible = False

        self.setup_ui()
        self.theme_manager.add_listener(self.apply_theme)

    def set_controller(self, controller):
        self.controller = controller
        self.refresh_list()

    def setup_ui(self):
        # Top Bar: URL Fetcher
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="URL:").pack(side=tk.LEFT, padx=2)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(top_frame, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.url_entry.bind("<Return>", lambda e: self.fetch_url())
        
        ttk.Button(top_frame, text="获取内容", command=self.fetch_url).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="手动新建", command=self.create_new).pack(side=tk.LEFT, padx=2)
        
        self.status_lbl = ttk.Label(top_frame, text="", foreground="#666")
        self.status_lbl.pack(side=tk.LEFT, padx=5)

        # Main Content: Paned Window
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: List
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)
        
        list_toolbar = ttk.Frame(left_frame)
        list_toolbar.pack(fill=tk.X)
        ttk.Label(list_toolbar, text="已存资料:").pack(side=tk.LEFT)
        ttk.Button(list_toolbar, text="刷新", command=self.refresh_list).pack(side=tk.RIGHT)
        
        self.item_listbox = tk.Listbox(left_frame, selectmode=tk.SINGLE)
        list_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.item_listbox.yview)
        self.item_listbox.configure(yscrollcommand=list_scroll.set)
        
        self.item_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.item_listbox.bind("<<ListboxSelect>>", self.on_select)
        
        # Right: Detail Editor
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)
        
        detail_toolbar = ttk.Frame(right_frame)
        detail_toolbar.pack(fill=tk.X, pady=2)
        
        ttk.Label(detail_toolbar, text="标题:").pack(side=tk.LEFT)
        self.title_var = tk.StringVar()
        ttk.Entry(detail_toolbar, textvariable=self.title_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Label(detail_toolbar, text="来源:").pack(side=tk.LEFT)
        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(detail_toolbar, textvariable=self.source_var)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.source_entry.bind("<Double-1>", self.open_source)
        
        self.content_text = tk.Text(right_frame, wrap=tk.WORD, font=("Microsoft YaHei", 10))
        text_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=text_scroll.set)
        
        self.content_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y, in_=self.content_text)
        
        bottom_bar = ttk.Frame(right_frame)
        bottom_bar.pack(fill=tk.X, pady=5)
        
        ttk.Label(bottom_bar, text="标签:").pack(side=tk.LEFT)
        self.tags_var = tk.StringVar()
        ttk.Entry(bottom_bar, textvariable=self.tags_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(bottom_bar, text="保存修改", command=self.save_current).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_bar, text="删除", command=self.delete_current).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_bar, text="添加到百科", command=self.add_to_wiki).pack(side=tk.RIGHT, padx=5)

        # Empty state panel
        config = EmptyStateConfig.RESEARCH
        self._empty_state = EmptyStatePanel(
            self,
            self.theme_manager,
            icon=config["icon"],
            title=config["title"],
            description=config["description"],
            action_text=config["action_text"],
            action_callback=self._on_empty_state_action
        )

    def _on_empty_state_action(self):
        """Handle empty state action button click."""
        self.create_new()

    def _show_empty_state(self, show: bool):
        """Show or hide the empty state panel."""
        if show and not self._empty_state_visible:
            self.paned.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self._empty_state_visible = True
        elif not show and self._empty_state_visible:
            self._empty_state.pack_forget()
            self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self._empty_state_visible = False

    def fetch_url(self):
        url = self.url_var.get().strip()
        if not url: return
        if self.controller:
            self.controller.fetch_url(url)

    def update_status(self, msg, busy=False):
        self.status_lbl.config(text=msg)
        if busy:
            self.config(cursor="watch")
        else:
            self.config(cursor="")

    def on_fetch_success(self, title, text, url):
        self.update_status("获取成功", False)
        self.create_new_with_data(title, text, url)

    def on_fetch_error(self, error_msg):
        self.update_status(f"错误: {error_msg}", False)

    def create_new(self):
        self.create_new_with_data("新资料", "", "")

    def create_new_with_data(self, title, content, url):
        # Create directly via controller
        self.controller.add_item(title, content, url, [])
        # Select the new item (it's inserted at 0)
        self.item_listbox.selection_clear(0, tk.END)
        self.item_listbox.selection_set(0)
        self.on_select(None)

    def refresh_list(self):
        self.item_listbox.delete(0, tk.END)
        items = self.project_manager.get_research_items()

        # Show empty state if no items
        if not items:
            self._show_empty_state(True)
            return
        self._show_empty_state(False)

        for item in items:
            self.item_listbox.insert(tk.END, item.get("title", "No Title"))

        # Restore selection if possible
        if self.current_item_uid:
            for i, item in enumerate(items):
                if item.get("uid") == self.current_item_uid:
                    self.item_listbox.selection_set(i)
                    break

    def on_select(self, event):
        sel = self.item_listbox.curselection()
        if not sel: 
            self.current_item_uid = None
            return
            
        items = self.project_manager.get_research_items()
        idx = sel[0]
        if idx < len(items):
            item = items[idx]
            self.current_item_uid = item.get("uid")
            
            self.title_var.set(item.get("title", ""))
            self.source_var.set(item.get("source_url", ""))
            self.tags_var.set(", ".join(item.get("tags", [])))
            self.content_text.delete("1.0", tk.END)
            self.content_text.insert("1.0", item.get("content", ""))

    def save_current(self):
        if not self.current_item_uid: return
        
        updated = {
            "title": self.title_var.get(),
            "source_url": self.source_var.get(),
            "content": self.content_text.get("1.0", tk.END).strip(),
            "tags": [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
        }
        self.controller.update_item(self.current_item_uid, updated)
        self.update_status("已保存")

    def delete_current(self):
        if not self.current_item_uid: return
        self.controller.delete_item(self.current_item_uid)
        self.current_item_uid = None
        self.title_var.set("")
        self.source_var.set("")
        self.content_text.delete("1.0", tk.END)

    def add_to_wiki(self):
        if not self.current_item_uid: return
        items = self.project_manager.get_research_items()
        item = next((i for i in items if i["uid"] == self.current_item_uid), None)
        if item:
            self.controller.add_to_wiki(item)

    def open_source(self, event):
        url = self.source_var.get()
        if url:
            webbrowser.open(url)

    def apply_theme(self):
        theme = self.theme_manager
        bg = theme.get_color("editor_bg")
        fg = theme.get_color("editor_fg")
        self.content_text.configure(bg=bg, fg=fg, insertbackground=fg)
        self.item_listbox.configure(bg=bg, fg=fg)
