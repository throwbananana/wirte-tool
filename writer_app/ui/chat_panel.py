import tkinter as tk
from tkinter import ttk
from writer_app.core.thread_pool import get_ai_thread_pool


class ChatPanel(ttk.Frame):
    PROJECT_OPTIONS = [
        ("项目概览", "overview"),
        ("角色列表", "characters"),
        ("场景列表", "scenes"),
        ("大纲概览", "outline"),
        ("项目统计", "stats"),
        ("下一步建议", "next_steps")
    ]
    ROLEPLAY_OPTIONS = [
        ("打招呼", "greet"),
        ("询问近况", "status"),
        ("询问目标", "goal"),
        ("道别", "bye")
    ]

    def __init__(self, parent, ai_client, context_provider, config_provider, project_manager, ai_controller=None, ai_mode_provider=None):
        super().__init__(parent)
        self.ai_client = ai_client
        self.context_provider = context_provider # Function that returns full project text
        self.config_provider = config_provider # Function that returns (url, model, key)
        self.project_manager = project_manager # Need project manager to get characters
        self.ai_controller = ai_controller
        self.ai_mode_provider = ai_mode_provider
        self.ai_mode_enabled = True
        self._ai_mode_initialized = False
        
        self.setup_ui()
        self.is_generating = False
        self.set_ai_mode_enabled(self._is_ai_enabled())

    def setup_ui(self):
        # Mode Selection
        mode_frame = ttk.Frame(self)
        mode_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mode_frame, text="模式:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="project") # project or roleplay
        
        ttk.Radiobutton(mode_frame, text="项目助手", variable=self.mode_var, value="project", command=self.on_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="角色扮演", variable=self.mode_var, value="roleplay", command=self.on_mode_change).pack(side=tk.LEFT, padx=5)
        
        self.char_select_frame = ttk.Frame(mode_frame)
        ttk.Label(self.char_select_frame, text="选择角色:").pack(side=tk.LEFT)
        self.roleplay_char_var = tk.StringVar()
        self.char_combo = ttk.Combobox(self.char_select_frame, textvariable=self.roleplay_char_var, state="readonly", width=15)
        self.char_combo.pack(side=tk.LEFT, padx=5)
        # Bind combobox dropdown to refresh
        self.char_combo.bind("<Button-1>", self.refresh_char_list)

        # Chat History
        self.history_text = tk.Text(self, wrap=tk.WORD, font=("Microsoft YaHei", 10), state="disabled")
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.history_text.yview)
        self.history_text.configure(yscrollcommand=scroll.set)
        
        self.history_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, in_=self.history_text)
        
        self._append_system_msg("欢迎使用项目对话功能！您可以询问关于大纲、剧本或设定的任何问题。")

        # Input Area
        input_frame = ttk.Frame(self)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.input_text = tk.Text(input_frame, height=3, wrap=tk.WORD, font=("Microsoft YaHei", 10))
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_text.bind("<Control-Return>", lambda e: self.send_message())
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        self.send_btn = ttk.Button(btn_frame, text="发送", command=self.send_message)
        self.send_btn.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))
        
        ttk.Button(btn_frame, text="清空", command=self.clear_history).pack(side=tk.BOTTOM, fill=tk.X)

        # Non-AI Option Chat
        self.option_frame = ttk.Frame(self)
        ttk.Label(self.option_frame, text="选项对话:").pack(side=tk.LEFT)
        self.option_var = tk.StringVar()
        self.option_combo = ttk.Combobox(self.option_frame, textvariable=self.option_var, state="readonly", width=20)
        self.option_combo.pack(side=tk.LEFT, padx=5)
        self.option_send_btn = ttk.Button(self.option_frame, text="发送选项", command=self.send_option_message)
        self.option_send_btn.pack(side=tk.LEFT)
        self.option_frame.pack_forget()

    def _is_ai_enabled(self):
        if self.ai_mode_provider:
            try:
                return bool(self.ai_mode_provider())
            except Exception:
                return True
        return True

    def set_ai_mode_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if self._ai_mode_initialized and self.ai_mode_enabled == enabled:
            return
        previous = self.ai_mode_enabled
        self.ai_mode_enabled = enabled
        self._ai_mode_initialized = True

        if enabled:
            self.option_frame.pack_forget()
            self._set_input_state(True)
            self.send_btn.state(["!disabled"])
            if previous is False:
                self._append_system_msg("已切换到 AI 模式，可自由提问。")
        else:
            self._update_option_values()
            self.option_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
            self._set_input_state(False)
            self.send_btn.state(["disabled"])
            if previous is True:
                self._append_system_msg("已切换到非AI模式，请使用选项对话。")

    def _set_input_state(self, enabled: bool):
        self.input_text.configure(state=tk.NORMAL)
        if not enabled:
            self.input_text.delete("1.0", tk.END)
            self.input_text.configure(state=tk.DISABLED)
        else:
            self.input_text.configure(state=tk.NORMAL)

    def on_mode_change(self):
        if self.mode_var.get() == "roleplay":
            self.char_select_frame.pack(side=tk.LEFT, padx=5)
            self.refresh_char_list()
            self._append_system_msg("切换到角色扮演模式。请选择一个角色开始对话。")
        else:
            self.char_select_frame.pack_forget()
            self._append_system_msg("切换到项目助手模式。")
        if not self.ai_mode_enabled:
            self._update_option_values()

    def refresh_char_list(self, event=None):
        chars = self.project_manager.get_characters()
        names = [c.get("name") for c in chars]
        self.char_combo["values"] = names
        if names and not self.roleplay_char_var.get():
            self.char_combo.current(0)

    def send_message(self):
        if not self._is_ai_enabled():
            self.send_option_message()
            return
        if self.is_generating: return
        
        query = self.input_text.get("1.0", tk.END).strip()
        if not query: return
        
        self.input_text.delete("1.0", tk.END)
        self._append_user_msg(query)
        
        url, model, key = self.config_provider()
        if not url or not model:
            self._append_system_msg("错误: 请先在左侧配置AI接口URL和模型名称")
            return

        mode = self.mode_var.get()
        
        if mode == "project":
            context = self.context_provider()
            
            agent_instructions = """
你是一个专业的剧本助手，可以回答问题，也可以操作项目数据。
你可以使用以下JSON工具（请用代码块 ```json 包裹）：

--- 创建工具 ---
1. 创建节点 (create_node):
   params: { "name": "标题", "content": "内容", "parent_uid": "父节点ID(可选)" }
2. 添加角色 (add_character):
   params: { "name": "姓名", "age": "年龄", "role": "角色定位", "description": "描述" }
3. 添加场景 (add_scene):
   params: { "name": "场景标题", "content": "梗概" }
4. 添加百科 (add_wiki_entry):
   params: { "name": "条目名", "category": "分类", "content": "内容" }
5. 添加任务 (add_kanban_task):
   params: { "text": "任务内容", "column": "状态列(To Do/Doing/Done)" }
6. 添加时间轴事件 (add_timeline_event):
   params: { "date": "YYYY-MM-DD", "content": "事件描述" }
7. 添加灵感 (add_idea):
   params: { "content": "灵感内容" }
8. 添加关系 (add_relationship):
   params: { "source": "角色A", "target": "角色B", "relation": "关系名" }
9. 添加线索 (add_clue):
   params: { "name": "线索名", "type": "clue/event/question", "description": "描述" }
10. 连接线索 (connect_clues):
    params: { "source": "线索A", "target": "线索B", "label": "关系描述" }

--- 编辑工具 ---
11. 修改场景内容 (update_scene_content):
    params: { "scene_name": "精确的场景标题", "content": "新的剧本内容" }
    用于重写场景或更新对话。
12. 更新角色 (update_character):
    params: { "name": "精确的角色姓名", "description": "新描述", "tags": ["标签"] }
    用于更新角色设定。

--- 辅助工具 ---
13. 生成资源占位符 (create_asset_placeholder):
    params: { "type": "character"|"background", "target_name": "角色名或场景名" }
14. 启动番茄钟 (start_timer):
    params: { "duration": 25 }
15. 停止番茄钟 (stop_timer):
    params: {}
16. 获取项目统计 (get_stats):
    params: {}
17. 跳转界面 (navigate_to):
    params: { "target": "大纲/剧本/线索/统计/看板/日历" }

如果用户要求创建或修改内容，请务必输出对应的JSON工具调用。仅输出JSON即可执行操作。
"""
            sys_prompt = f"{agent_instructions}\n请根据提供的项目上下文回答用户的问题。如果问题与项目无关，请礼貌拒绝。"
            user_prompt = f"项目上下文:\n{context}\n\n用户问题: {query}"
        else: # Roleplay
            char_name = self.roleplay_char_var.get()
            if not char_name:
                self._append_system_msg("请先选择一个角色！")
                return
            
            chars = self.project_manager.get_characters()
            char_data = next((c for c in chars if c.get("name") == char_name), None)
            
            if not char_data:
                self._append_system_msg("角色数据未找到。")
                return

            desc = char_data.get("description", "无描述")
            tags = ", ".join(char_data.get("tags", []))
            
            sys_prompt = f"""你现在是剧本中的角色 "{char_name}"。
你的设定如下:
描述: {desc}
标签/特征: {tags}

请完全沉浸在角色中，用这个角色的语气、口癖和思维方式回答我的问题。不要跳出角色，不要说你是AI。
"""
            user_prompt = query
        
        self.is_generating = True
        self.send_btn.state(["disabled"])

        def run_chat():
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_prompt, user_prompt)

        def on_success(response):
            if self.ai_controller and self.mode_var.get() == "project":
                self.ai_controller.handle_chat_response(response, self._append_ai_msg)
            else:
                self._append_ai_msg(response)
            self._reset_state()

        def on_error(e):
            self._append_system_msg(f"请求失败: {str(e)}")
            self._reset_state()

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="chat_panel_send",
            fn=run_chat,
            on_success=on_success,
            on_error=on_error,
            tk_root=self
        )

    def send_option_message(self):
        if self.is_generating:
            return

        mode = self.mode_var.get()
        if mode == "roleplay" and not self.roleplay_char_var.get():
            self._append_system_msg("请先选择一个角色！")
            return

        label = self.option_var.get()
        if not label:
            self._update_option_values()
            label = self.option_var.get()
        if not label:
            self._append_system_msg("暂无可用选项。")
            return

        self._append_user_msg(label)
        response = self._build_option_response(label, mode)
        self._append_ai_msg(response)

    def _update_option_values(self):
        options = self.PROJECT_OPTIONS if self.mode_var.get() == "project" else self.ROLEPLAY_OPTIONS
        labels = [label for label, _ in options]
        self.option_combo["values"] = labels
        if labels:
            self.option_var.set(labels[0])

    def _build_option_response(self, label, mode):
        options = self.PROJECT_OPTIONS if mode == "project" else self.ROLEPLAY_OPTIONS
        option_map = {k: v for k, v in options}
        key = option_map.get(label)
        if not key:
            return "暂未识别该选项。"
        if mode == "project":
            return self._build_project_option_response(key)
        return self._build_roleplay_option_response(key)

    def _build_project_option_response(self, key):
        outline = self.project_manager.get_outline() or {}
        top_nodes = outline.get("children", []) or []
        scenes = self.project_manager.get_scenes()
        chars = self.project_manager.get_characters()
        title = outline.get("name", "项目大纲")
        word_count = sum(len(s.get("content", "")) for s in scenes)

        if key == "overview":
            return (
                f"项目概览：\n"
                f"- 标题: {title}\n"
                f"- 类型: {self.project_manager.get_project_type_display_name()}\n"
                f"- 场景数: {len(scenes)}\n"
                f"- 角色数: {len(chars)}\n"
                f"- 一级大纲: {len(top_nodes)}\n"
                f"- 字数(粗略): {word_count}"
            )

        if key == "characters":
            if not chars:
                return "当前项目暂无角色。"
            names = [c.get("name", "未命名") for c in chars[:30]]
            suffix = "..." if len(chars) > 30 else ""
            return "角色列表：\n" + "\n".join(f"- {name}" for name in names) + suffix

        if key == "scenes":
            if not scenes:
                return "当前项目暂无场景。"
            names = [s.get("name", "未命名") for s in scenes[:20]]
            suffix = "..." if len(scenes) > 20 else ""
            return "场景列表：\n" + "\n".join(f"- {name}" for name in names) + suffix

        if key == "outline":
            if not top_nodes:
                return "当前大纲暂无一级节点。"
            names = [n.get("name", "未命名") for n in top_nodes[:20]]
            suffix = "..." if len(top_nodes) > 20 else ""
            return "大纲概览：\n" + "\n".join(f"- {name}" for name in names) + suffix

        if key == "stats":
            return (
                f"项目统计：\n"
                f"- 场景数: {len(scenes)}\n"
                f"- 角色数: {len(chars)}\n"
                f"- 一级大纲: {len(top_nodes)}\n"
                f"- 字数(粗略): {word_count}"
            )

        if key == "next_steps":
            suggestions = []
            if not top_nodes:
                suggestions.append("先补充大纲的一级节点。")
            if not chars:
                suggestions.append("完善主要角色设定。")
            if not scenes:
                suggestions.append("新增至少一个关键场景。")
            if not suggestions:
                suggestions.append("继续细化场景内容或检查逻辑一致性。")
            return "建议下一步：\n" + "\n".join(f"- {item}" for item in suggestions)

        return "暂未配置该选项的回复。"

    def _build_roleplay_option_response(self, key):
        char_name = self.roleplay_char_var.get() or "角色"
        char_data = next((c for c in self.project_manager.get_characters() if c.get("name") == char_name), {})
        desc = (char_data.get("description") or "").strip()
        tags = ", ".join(char_data.get("tags", []))
        short_desc = desc[:60] + ("..." if len(desc) > 60 else "")

        if key == "greet":
            base = f"你好，我是 {char_name}。"
            if short_desc:
                base += f"{short_desc}"
            return base

        if key == "status":
            extra = f"目前我在忙着处理一些事情。"
            if tags:
                extra = f"我最近在做与「{tags}」相关的事情。"
            return extra

        if key == "goal":
            if desc:
                return f"我的目标很明确：{short_desc}"
            return "我暂时不方便透露太多，但我有必须完成的目标。"

        if key == "bye":
            return "先到这里吧，我们下次再聊。"

        return "……"

    def _reset_state(self):
        self.is_generating = False
        self.send_btn.state(["!disabled"])

    def _append_user_msg(self, text):
        self.history_text.configure(state="normal")
        self.history_text.insert(tk.END, f"\n我: {text}\n", "user")
        self.history_text.tag_config("user", foreground="#007BFF", font=("Microsoft YaHei", 10, "bold"))
        self.history_text.see(tk.END)
        self.history_text.configure(state="disabled")

    def _append_ai_msg(self, text):
        name = "助手"
        color = "#28A745"
        if self.mode_var.get() == "roleplay":
            name = self.roleplay_char_var.get() or "角色"
            color = "#E05090" # Different color for roleplay

        self.history_text.configure(state="normal")
        self.history_text.insert(tk.END, f"\n{name}: {text}\n", "ai")
        self.history_text.tag_config("ai", foreground=color)
        self.history_text.see(tk.END)
        self.history_text.configure(state="disabled")

    def _append_system_msg(self, text):
        self.history_text.configure(state="normal")
        self.history_text.insert(tk.END, f"\n系统: {text}\n", "system")
        self.history_text.tag_config("system", foreground="#666666", font=("Microsoft YaHei", 9, "italic"))
        self.history_text.see(tk.END)
        self.history_text.configure(state="disabled")

    def clear_history(self):
        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", tk.END)
        self._append_system_msg("对话已清空")
        self.history_text.configure(state="disabled")
