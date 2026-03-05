import tkinter as tk
from tkinter import ttk
import random
from tkinter import messagebox
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.core.thread_pool import get_ai_thread_pool

class NameGeneratorDialog(tk.Toplevel):
    def __init__(self, parent, ai_client, theme_manager, config_manager=None):
        super().__init__(parent)
        self.title("起名助手")
        self.geometry("500x400")
        self.ai_client = ai_client
        self.theme_manager = theme_manager
        self.config_manager = config_manager
        
        self.setup_ui()
        self.apply_theme()
        self.set_ai_mode_enabled(self._is_ai_enabled())
        self._ai_mode_handler = self._on_ai_mode_changed
        get_event_bus().subscribe(Events.AI_MODE_CHANGED, self._ai_mode_handler)

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Rule Based Section ---
        rule_frame = ttk.LabelFrame(main_frame, text="随机生成 (规则库)")
        rule_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.type_var = tk.StringVar(value="chinese")
        types = [("中文名", "chinese"), ("英文名", "english"), ("日文名", "japanese")]
        for lbl, val in types:
            ttk.Radiobutton(rule_frame, text=lbl, variable=self.type_var, value=val).pack(side=tk.LEFT, padx=5, pady=5)
            
        ttk.Button(rule_frame, text="生成", command=self.generate_rule_based).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # --- AI Section ---
        ai_frame = ttk.LabelFrame(main_frame, text="AI 灵感生成")
        ai_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(ai_frame, text="描述需求 (如: '维多利亚风格的贵族女性'):").pack(anchor=tk.W, padx=5, pady=2)
        self.prompt_entry = ttk.Entry(ai_frame)
        self.prompt_entry.pack(fill=tk.X, padx=5, pady=2)
        
        self.ai_btn = ttk.Button(ai_frame, text="AI 生成", command=self.generate_ai_based)
        self.ai_btn.pack(anchor=tk.E, padx=5, pady=5)
        
        # --- Result Section ---
        res_frame = ttk.LabelFrame(main_frame, text="生成结果 (点击复制)")
        res_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_list = tk.Listbox(res_frame)
        self.result_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scr = ttk.Scrollbar(res_frame, orient=tk.VERTICAL, command=self.result_list.yview)
        self.result_list.configure(yscrollcommand=scr.set)
        scr.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_list.bind("<<ListboxSelect>>", self.on_select)

    def generate_rule_based(self):
        t = self.type_var.get()
        names = []
        if t == "chinese":
            surnames = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许"
            chars = "明国华建文平志伟东海强晓生光林小爱"
            for _ in range(10):
                names.append(random.choice(surnames) + random.choice(chars) + (random.choice(chars) if random.random() > 0.5 else ""))
        elif t == "english":
            firsts = ["James", "John", "Robert", "Michael", "William", "David", "Mary", "Patricia", "Jennifer", "Linda"]
            lasts = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
            for _ in range(10):
                names.append(f"{random.choice(firsts)} {random.choice(lasts)}")
        elif t == "japanese":
            surnames = ["佐藤", "铃木", "高桥", "田中", "渡边", "伊藤", "山本"]
            names_j = ["春树", "直子", "健太", "美咲", "大翔", "阳菜"]
            for _ in range(10):
                names.append(random.choice(surnames) + random.choice(names_j))
        
        self.result_list.delete(0, tk.END)
        for n in names:
            self.result_list.insert(tk.END, n)

    def generate_ai_based(self):
        if not self._is_ai_enabled():
            messagebox.showinfo("提示", "当前为非AI模式，AI生成不可用。")
            return
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            return

        self.ai_btn.config(state="disabled", text="生成中...")

        def _run():
            sys_prompt = "You are a creative naming assistant. Generate 10 names based on the user's description. Return ONLY the names, one per line. No numbering."
            res = self.ai_client.chat_completion(
                system_prompt=sys_prompt,
                user_prompt=prompt,
                temperature=0.9
            )
            return res

        def on_success(res):
            if res:
                lines = [l.strip().strip("-").strip() for l in res.split("\n") if l.strip()]
                self.result_list.delete(0, tk.END)
                for l in lines:
                    self.result_list.insert(tk.END, l)
            self.ai_btn.config(state="normal", text="AI 生成")

        def on_error(e):
            self.ai_btn.config(state="normal", text="AI 生成")

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="name_generator_ai",
            fn=_run,
            on_success=on_success,
            on_error=on_error,
            tk_root=self
        )

    def on_select(self, event):
        sel = self.result_list.curselection()
        if sel:
            txt = self.result_list.get(sel[0])
            self.clipboard_clear()
            self.clipboard_append(txt)
            self.title(f"已复制: {txt}")

    def apply_theme(self):
        # Apply theme colors
        pass

    def _is_ai_enabled(self):
        if self.config_manager:
            return self.config_manager.is_ai_enabled()
        return True

    def set_ai_mode_enabled(self, enabled: bool):
        if not enabled:
            self.ai_btn.config(state="disabled")
        else:
            self.ai_btn.config(state="normal")

    def _on_ai_mode_changed(self, _event_type=None, **kwargs):
        enabled = kwargs.get("enabled", True)
        self.set_ai_mode_enabled(enabled)

    def destroy(self):
        if hasattr(self, "_ai_mode_handler") and self._ai_mode_handler:
            get_event_bus().unsubscribe(Events.AI_MODE_CHANGED, self._ai_mode_handler)
        super().destroy()
