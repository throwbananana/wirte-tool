import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import subprocess
from datetime import datetime
from writer_app.controllers.base_controller import BaseController
from writer_app.core.thread_pool import get_ai_thread_pool
from writer_app.ui.editor import ScriptEditor
from writer_app.ui.dialogs import CharacterDialog
from writer_app.ui.components.personality_radar import PersonalityRadar
from writer_app.ui.tags import TagSelectorDialog
from writer_app.core.commands import (
    AddCharacterCommand, DeleteCharacterCommand, EditCharacterCommand,
    AddSceneCommand, DeleteSceneCommand, EditSceneCommand, EditSceneContentCommand
)
from writer_app.core.analysis import AnalysisUtils
from writer_app.core.tts import TTSManager
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.ui.help_dialog import create_module_help_button

from writer_app.ui.flowchart_view import StoryFlowCanvas
from writer_app.core.resource_loader import ResourceLoader

PERSONALITY_FIELDS = [
    ("openness", "开放性"),
    ("conscientiousness", "尽责性"),
    ("extraversion", "外向性"),
    ("agreeableness", "宜人性"),
    ("neuroticism", "神经质"),
]

class ScriptController(BaseController):
    def __init__(self, parent, project_manager, command_executor, theme_manager, ai_client, config_manager, on_wiki_click=None, ai_controller=None, ambiance_player=None):
        super().__init__(parent, project_manager, command_executor, theme_manager)
        self.ai_client = ai_client
        self.resource_loader = ResourceLoader()
        self.config_manager = config_manager
        self.on_wiki_click = on_wiki_click
        self.ai_controller = ai_controller
        self.ambiance_player = ambiance_player
        self.tts_manager = TTSManager()
        self.ai_logic_btn = None
        self.ai_motivation_btn = None
        self.ai_tension_btn = None
        self.script_btn_box = None
        
        # Variables
        self.char_name_var = tk.StringVar()
        self.char_tags_display_var = tk.StringVar(value="未设置")
        self.scene_name_var = tk.StringVar()
        self.scene_location_var = tk.StringVar()
        self.scene_time_var = tk.StringVar()
        self.scene_image_var = tk.StringVar()
        self.scene_bgm_var = tk.StringVar() # For Galgame
        self.scene_outline_ref_var = tk.StringVar()
        self.scene_tags_display_var = tk.StringVar(value="未设置")
        self.script_title_var = tk.StringVar(value="未命名剧本")
        self.script_ai_status_var = tk.StringVar(value="使用大纲生成剧本")
        self.scene_tag_filter_var = tk.StringVar(value="全部")
        
        self.current_scene_idx = None
        self.scene_index_map = []
        self.current_scene_tags = []
        self.current_char_tags = []
        self.scene_tag_filter = None
        self.script_ai_generating = False
        self.is_reading = False
        
        self.setup_ui()
        self._add_theme_listener(self.apply_theme)
        self.set_ai_mode_enabled(self.config_manager.is_ai_enabled())
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅事件总线以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.SCENE_ADDED, self._on_scene_changed)
        self._subscribe_event(Events.SCENE_UPDATED, self._on_scene_changed)
        self._subscribe_event(Events.SCENE_DELETED, self._on_scene_changed)
        self._subscribe_event(Events.CHARACTER_ADDED, self._on_character_changed)
        self._subscribe_event(Events.CHARACTER_UPDATED, self._on_character_changed)
        self._subscribe_event(Events.CHARACTER_DELETED, self._on_character_changed)
        self._subscribe_event(Events.PROJECT_LOADED, self._on_project_loaded)
        self._subscribe_event(Events.TAGS_UPDATED, self._on_tags_changed)

    def _on_scene_changed(self, event_type=None, **kwargs):
        """响应场景变化事件"""
        self.refresh_scene_list()

    def _on_character_changed(self, event_type=None, **kwargs):
        """响应角色变化事件"""
        self.refresh_character_list()

    def _on_project_loaded(self, event_type=None, **kwargs):
        """响应项目加载事件"""
        self.refresh()

    def _on_tags_changed(self, event_type=None, **kwargs):
        """响应标签变化事件"""
        self.refresh_scene_list()

    def setup_ui(self):
        self.script_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        self.script_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.char_frame_ui = ttk.LabelFrame(self.script_paned, text="角色管理")
        self.script_paned.add(self.char_frame_ui, weight=1)
        self.setup_character_panel(self.char_frame_ui)
        
        self.scene_frame_ui = ttk.LabelFrame(self.script_paned, text="场景列表")
        self.script_paned.add(self.scene_frame_ui, weight=1)
        self.setup_scene_panel(self.scene_frame_ui)
        
        editor_frame = ttk.LabelFrame(self.script_paned, text="剧本编辑器")
        self.script_paned.add(editor_frame, weight=3)
        self.setup_script_editor(editor_frame)

    def setup_character_panel(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="+ 添加", command=self.add_character).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="编辑", command=self.edit_character).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self.delete_character).pack(side=tk.LEFT, padx=2)

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.char_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        char_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_listbox.yview)
        self.char_listbox.configure(yscrollcommand=char_scroll.set)
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        char_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        detail_frame = ttk.LabelFrame(parent, text="角色详情")
        detail_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(detail_frame, text="姓名:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(detail_frame, textvariable=self.char_name_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(detail_frame, text="描述:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=2)
        self.char_desc_text = tk.Text(detail_frame, height=4, width=25, wrap=tk.WORD)
        self.char_desc_text.grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(detail_frame, text="标签:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        tag_row = ttk.Frame(detail_frame)
        tag_row.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(tag_row, textvariable=self.char_tags_display_var, foreground="#555").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(tag_row, text="选择标签", command=self.open_character_tag_selector).pack(side=tk.LEFT, padx=3)

        personality_frame = ttk.LabelFrame(parent, text="性格五维")
        personality_frame.pack(fill=tk.X, padx=5, pady=5)

        self.personality_chart = PersonalityRadar(personality_frame, size=160)
        self.personality_chart.pack(side=tk.LEFT, padx=5, pady=5)

        personality_btns = ttk.Frame(personality_frame)
        personality_btns.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(personality_btns, text="AI识别", command=self.ai_fill_personality).pack(fill=tk.X, pady=2)
        ttk.Button(personality_btns, text="编辑", command=self.edit_personality).pack(fill=tk.X, pady=2)
        self._refresh_personality_chart(None)

        scenes_frame = ttk.LabelFrame(parent, text="出现的场景")
        scenes_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.char_scene_listbox = tk.Listbox(scenes_frame, selectmode=tk.SINGLE)
        self.char_scene_listbox.pack(fill=tk.BOTH, expand=True)
        self.char_scene_listbox.bind("<Double-1>", lambda e: self.jump_to_scene_from_char())

        self.char_listbox.bind("<<ListboxSelect>>", self.on_character_select)
        self.char_listbox.bind("<Double-1>", lambda e: self.edit_character())

    def setup_scene_panel(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="+ 添加场景", command=self.add_scene).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self.delete_scene).pack(side=tk.LEFT, padx=2)
        ttk.Label(toolbar, text="标签过滤:").pack(side=tk.LEFT, padx=(10,2))
        self.scene_tag_filter_combo = ttk.Combobox(toolbar, textvariable=self.scene_tag_filter_var, width=12, state="readonly")
        self.scene_tag_filter_combo.pack(side=tk.LEFT, padx=2)
        self.scene_tag_filter_combo.bind("<<ComboboxSelected>>", self.on_scene_tag_filter_change)
        
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.scene_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        scene_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.scene_listbox.yview)
        self.scene_listbox.configure(yscrollcommand=scene_scroll.set)
        self.scene_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scene_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        detail_frame = ttk.LabelFrame(parent, text="场景信息")
        detail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(detail_frame, text="场景名:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(detail_frame, textvariable=self.scene_name_var).grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(detail_frame, text="地点:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(detail_frame, textvariable=self.scene_location_var).grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(detail_frame, text="时间:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(detail_frame, textvariable=self.scene_time_var).grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(detail_frame, text="场景图片:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        img_box = ttk.Frame(detail_frame)
        img_box.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        ttk.Entry(img_box, textvariable=self.scene_image_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(img_box, text="...", width=3, command=self.browse_scene_image).pack(side=tk.LEFT, padx=2)

        # Galgame Specifics
        if self.project_manager.get_project_type() == "Galgame":
            ttk.Label(detail_frame, text="BGM:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
            bgm_box = ttk.Frame(detail_frame)
            bgm_box.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
            ttk.Entry(bgm_box, textvariable=self.scene_bgm_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(bgm_box, text="...", width=3, command=self.browse_scene_bgm).pack(side=tk.LEFT, padx=2)
            
            ttk.Label(detail_frame, text="分支选项:").grid(row=6, column=0, sticky=tk.NW, padx=5, pady=2)
            choice_frame = ttk.Frame(detail_frame)
            choice_frame.grid(row=6, column=1, sticky="ew", padx=5, pady=2)
            self.choices_listbox = tk.Listbox(choice_frame, height=3)
            self.choices_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.choices_listbox.bind("<Double-1>", lambda e: self.edit_choice())
            c_btn_frame = ttk.Frame(choice_frame)
            c_btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
            ttk.Button(c_btn_frame, text="+", width=3, command=self.add_choice).pack()
            ttk.Button(c_btn_frame, text="-", width=3, command=self.delete_choice).pack()
            
            ttk.Button(detail_frame, text="查看剧情流向图", command=self.open_flowchart).grid(row=8, column=0, columnspan=2, pady=5)
        
        ttk.Label(detail_frame, text="关联角色:").grid(row=5, column=0, sticky=tk.NW, padx=5, pady=2)
        self.scene_characters_listbox = tk.Listbox(detail_frame, selectmode=tk.MULTIPLE, height=5, exportselection=False)
        self.scene_characters_listbox.grid(row=5, column=1, sticky="ew", padx=5, pady=2)

        ttk.Button(detail_frame, text="保存场景信息", command=self.save_scene_info).grid(row=7, column=0, columnspan=2, pady=5)

        self.scene_listbox.bind("<<ListboxSelect>>", self.on_scene_select)
        self.scene_listbox.bind("<Double-1>", lambda e: self.load_scene_to_editor())

    def setup_script_editor(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(toolbar, text="剧本标题:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(toolbar, textvariable=self.script_title_var, width=30).pack(side=tk.LEFT, padx=5)
        
        btn_box = ttk.Frame(toolbar)
        btn_box.pack(side=tk.RIGHT)
        self.script_btn_box = btn_box
        ttk.Button(btn_box, text="保存场景内容", command=self.save_scene_content).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="📸 存快照", command=self.save_scene_snapshot).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="📜 历史", command=self.view_scene_history).pack(side=tk.LEFT, padx=2)
        
        # TTS Controls
        self.tts_read_btn = ttk.Button(btn_box, text="🔊 朗读", command=self.read_scene_aloud)
        self.tts_read_btn.pack(side=tk.LEFT, padx=2)
        self.tts_stop_btn = ttk.Button(btn_box, text="⏹ 停止", command=self.stop_reading, state=tk.DISABLED)
        self.tts_stop_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="⚙ TTS设置", command=self.open_tts_settings).pack(side=tk.LEFT, padx=2)
        
        if self.ai_controller:
            ttk.Button(btn_box, text="逻辑检查", command=self.check_logic).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_box, text="动机分析", command=self.analyze_motivation).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_box, text="张力检测", command=self.detect_tension).pack(side=tk.LEFT, padx=2)

        # 帮助按钮
        help_btn = create_module_help_button(btn_box, "script", self._show_full_help)
        help_btn.pack(side=tk.LEFT, padx=4)

        editor_container = ttk.Frame(parent)
        editor_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.script_editor = ScriptEditor(
            editor_container, 
            project_manager=self.project_manager,
            on_ai_continue=self.ai_continue_script,
            on_ai_rewrite=self.ai_rewrite_script,
            on_wiki_click=self.on_wiki_click,
            on_content_change=None # Could link to productivity
        )
        editor_scroll = ttk.Scrollbar(editor_container, orient=tk.VERTICAL, command=self.script_editor.yview)
        self.script_editor.configure(yscrollcommand=editor_scroll.set)
        self.script_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        editor_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def check_logic(self):
        if not self.ai_controller: return
        # Collect full context for deep logic check
        context = []
        
        # 1. Outline
        context.append("【项目大纲】")
        context.append(json.dumps(self.project_manager.get_outline(), ensure_ascii=False))
        
        # 2. Characters & Wiki
        context.append("\n【设定与百科】")
        for char in self.project_manager.get_characters():
            context.append(f"- 角色: {char.get('name')} | 描述: {char.get('description')}")
        for entry in self.project_manager.get_world_entries():
            context.append(f"- {entry.get('category')}: {entry.get('name')} | 内容: {entry.get('content')}")
            
        # 3. Script
        context.append("\n【剧本内容】")
        script = self.project_manager.get_script()
        context.append(f"标题: {script.get('title', '')}")
        for s in self.project_manager.get_scenes():
            context.append(f"\n场景: {s.get('name')}")
            context.append(f"地点: {s.get('location')} | 时间: {s.get('time')}")
            context.append(s.get('content', ''))
        
        full_context_text = "\n".join(context)
        self.ai_controller.check_logic_consistency(full_context_text)

    def analyze_motivation(self):
        """分析当前场景中角色的动机。"""
        if not self.ai_controller: return
        content = self.script_editor.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("提示", "场景内容为空，无法分析。")
            return
            
        scene_name = self.scene_name_var.get()
        # 获取相关角色设定
        chars_info = []
        for i in self.scene_characters_listbox.curselection():
            char_name = self.scene_characters_listbox.get(i)
            char = next((c for c in self.project_manager.get_characters() if c["name"] == char_name), None)
            if char:
                chars_info.append(f"- {char_name}: {char.get('description', '')}")
        
        prompt = f"请分析场景「{scene_name}」中各角色的动机和心理状态。\n角色背景：\n" + "\n".join(chars_info) + f"\n\n剧本内容：\n{content}"
        self.ai_controller.diagnose_outline(prompt) # Re-using diagnose_outline which shows a dialog

    def detect_tension(self):
        """检测当前场景的戏剧冲突张力。"""
        if not self.ai_controller: return
        content = self.script_editor.get("1.0", tk.END).strip()
        if not content: return
        
        prompt = f"请评估以下剧本片段的戏剧张力和冲突等级（1-10分），并给出改进建议：\n\n{content}"
        self.ai_controller.diagnose_outline(prompt)

    def _show_full_help(self, topic_id: str = None):
        """显示完整帮助对话框"""
        from writer_app.ui.help_dialog import show_help_dialog
        show_help_dialog(self.parent.winfo_toplevel(), topic_id or "script")

    def refresh(self):
        self.refresh_character_list()
        self.refresh_scene_list()
        self.script_title_var.set(self.project_manager.get_script().get("title", "未命名剧本"))
        # Refresh current editor if needed
        if self.current_scene_idx is not None:
            scene_data = self.project_manager.get_scenes()
            if 0 <= self.current_scene_idx < len(scene_data):
                current_scene = scene_data[self.current_scene_idx]
                editor_content = self.script_editor.get("1.0", tk.END).strip()
                if editor_content != current_scene.get("content", ""):
                    self.script_editor.delete("1.0", tk.END)
                    self.script_editor.insert("1.0", current_scene.get("content", ""))

    def apply_theme(self):
        theme = self.theme_manager
        self.script_editor.apply_theme(theme)
        
        # Apply Editor Font
        if self.config_manager:
            font_family = self.config_manager.get("editor_font", "Consolas")
            font_size = self.config_manager.get("editor_font_size", 12)
            self.script_editor.configure(font=(font_family, font_size))
        
        bg = theme.get_color("editor_bg")
        fg = theme.get_color("editor_fg")
        
        # Apply to listboxes and texts
        widgets = [self.char_listbox, self.scene_listbox, self.char_scene_listbox, 
                   self.scene_characters_listbox, self.char_desc_text]
        for w in widgets:
            w.configure(bg=bg, fg=fg, selectbackground=theme.get_color("accent"))

        if hasattr(self, "personality_chart"):
            self.personality_chart.configure(bg=bg)

    def _cache_ai_buttons(self):
        if not self.script_btn_box:
            return
        targets = {
            "逻辑检查": "ai_logic_btn",
            "动机分析": "ai_motivation_btn",
            "张力检测": "ai_tension_btn"
        }
        for child in self.script_btn_box.winfo_children():
            try:
                text = child.cget("text")
            except Exception:
                continue
            for key, attr in targets.items():
                if key in text:
                    setattr(self, attr, child)

    def set_ai_mode_enabled(self, enabled: bool):
        self._cache_ai_buttons()
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in [self.ai_logic_btn, self.ai_motivation_btn, self.ai_tension_btn]:
            if btn:
                btn.config(state=state)
        if hasattr(self, "script_editor"):
            self.script_editor.set_ai_mode_enabled(enabled)

    # --- Actions ---
    # Simplified versions of main.py logic
    def refresh_character_list(self):
        self.char_listbox.delete(0, tk.END)
        for char in self.project_manager.get_characters():
            self.char_listbox.insert(tk.END, char.get("name", "未命名"))
        self.refresh_scene_characters_options()

    def refresh_scene_list(self):
        self.scene_listbox.delete(0, tk.END)
        scenes = self.project_manager.get_scenes()
        tag_filter = self.scene_tag_filter
        self.scene_index_map = []
        for i, scene in enumerate(scenes):
            if tag_filter and tag_filter not in scene.get("tags", []):
                continue
            name = scene.get('name', '未命名')
            self.scene_listbox.insert(tk.END, f"{i+1}. {name}")
            self.scene_index_map.append(i)
        
        # Update filter combo
        tags = ["全部"] + [t.get("name") for t in self.project_manager.get_tags_config()]
        self.scene_tag_filter_combo["values"] = tags

    def refresh_scene_characters_options(self):
        current_selection = list(self.scene_characters_listbox.curselection())
        self.scene_characters_listbox.delete(0, tk.END)
        for char in self.project_manager.get_characters():
            self.scene_characters_listbox.insert(tk.END, char.get("name", ""))
        for idx in current_selection:
            if idx < self.scene_characters_listbox.size():
                self.scene_characters_listbox.selection_set(idx)

    def on_scene_tag_filter_change(self, event=None):
        val = self.scene_tag_filter_var.get()
        self.scene_tag_filter = None if val == "全部" else val
        self.refresh_scene_list()

    def add_character(self):
        name = simpledialog.askstring("添加角色", "姓名:", parent=self.parent)
        if name:
            character_data = {"name": name, "description": "", "image_path": "", "tags": []}
            command = AddCharacterCommand(self.project_manager, character_data, "添加角色")
            self.command_executor(command)

    def edit_character(self):
        sel = self.char_listbox.curselection()
        if not sel: return
        idx = sel[0]
        old_char_data = self.project_manager.get_characters()[idx]
        
        template = self.config_manager.get("character_template", [])
        dialog = CharacterDialog(self.parent.winfo_toplevel(), "编辑角色", old_char_data, template=template)
        if dialog.result:
            new_char_data = dialog.result
            new_char_data["tags"] = list(self.current_char_tags or old_char_data.get("tags", []))
            if old_char_data != new_char_data:
                command = EditCharacterCommand(self.project_manager, idx, old_char_data, new_char_data, "编辑角色")
                self.command_executor(cmd)

    def delete_character(self):
        sel = self.char_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if messagebox.askyesno("确认删除", "确定要删除该角色吗?"):
            char_data_to_delete = self.project_manager.get_characters()[idx]
            command = DeleteCharacterCommand(self.project_manager, idx, char_data_to_delete, "删除角色")
            self.command_executor(command)

    def on_character_select(self, e):
        sel = self.char_listbox.curselection()
        if sel:
            char = self.project_manager.get_characters()[sel[0]]
            self.char_name_var.set(char.get("name", ""))
            self.char_desc_text.delete("1.0", tk.END)
            self.char_desc_text.insert("1.0", char.get("description", ""))
            self.current_char_tags = list(char.get("tags", []))
            self.char_tags_display_var.set(", ".join(self.current_char_tags) if self.current_char_tags else "未设置")
            self.refresh_char_scene_list(char.get("name", ""))
            self._refresh_personality_chart(char)
        else:
            self.refresh_char_scene_list("")
            self.current_char_tags = []
            self.char_tags_display_var.set("未设置")
            self._refresh_personality_chart(None)

    def refresh_char_scene_list(self, char_name):
        self.char_scene_listbox.delete(0, tk.END)
        scenes = self.project_manager.get_scenes()
        for idx, scene in enumerate(scenes):
            if char_name and char_name in scene.get("characters", []):
                self.char_scene_listbox.insert(tk.END, f"{idx+1}. {scene.get('name', '')}")

    def jump_to_scene_from_char(self):
        sel = self.char_scene_listbox.curselection()
        if not sel: return
        label = self.char_scene_listbox.get(sel[0])
        try:
            idx = int(label.split(".")[0]) - 1
        except (ValueError, IndexError):
            return
        
        if 0 <= idx < len(self.project_manager.get_scenes()):
            # Select in scene list
            self.scene_tag_filter_var.set("全部")
            self.on_scene_tag_filter_change()
            self.scene_listbox.selection_clear(0, tk.END)
            self.scene_listbox.selection_set(idx)
            self.scene_listbox.event_generate("<<ListboxSelect>>")
            self.load_scene_to_editor()

    def open_character_tag_selector(self):
        sel = self.char_listbox.curselection()
        if not sel: return
        idx = sel[0]
        char = self.project_manager.get_characters()[idx]
        dialog = TagSelectorDialog(self.parent.winfo_toplevel(), self.project_manager, char.get("tags", []))
        if dialog.result is not None:
            new_char = dict(char)
            new_char["tags"] = dialog.result
            cmd = EditCharacterCommand(self.project_manager, idx, char, new_char, "设置角色标签")
            self.command_executor(cmd)
            self.current_char_tags = dialog.result
            self.char_tags_display_var.set(", ".join(self.current_char_tags) if self.current_char_tags else "未设置")

    def _refresh_personality_chart(self, char):
        if not hasattr(self, "personality_chart"):
            return

        values = {}
        if char:
            data = char.get("personality", {}) or {}
            for key, label in PERSONALITY_FIELDS:
                raw = data.get(key, 5)
                try:
                    val = float(raw)
                except (TypeError, ValueError):
                    val = 5.0
                if 0 <= val <= 1:
                    val *= 10
                values[label] = max(0.0, min(10.0, val))
        else:
            for _, label in PERSONALITY_FIELDS:
                values[label] = 5

        self.personality_chart.set_values(values)

    def edit_personality(self):
        sel = self.char_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择角色")
            return

        idx = sel[0]
        char = self.project_manager.get_characters()[idx]
        current = char.get("personality", {}) or {}
        dlg = PersonalityEditDialog(self.parent.winfo_toplevel(), current)
        if dlg.result:
            new_char = dict(char)
            new_char["personality"] = dlg.result
            cmd = EditCharacterCommand(self.project_manager, idx, char, new_char, "编辑角色性格")
            self.command_executor(cmd)
            self._refresh_personality_chart(new_char)

    def ai_fill_personality(self):
        sel = self.char_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择角色")
            return

        if not self.ai_controller:
            messagebox.showinfo("提示", "当前未启用 AI 模式")
            return

        idx = sel[0]
        char = self.project_manager.get_characters()[idx]
        char_name = char.get("name", "")
        char_desc = char.get("description", "")

        scenes = self.project_manager.get_scenes_with_character(char_name)
        scene_texts = []
        for _, scene in scenes[:5]:
            content = scene.get("content", "")
            if content:
                scene_texts.append(content[:800])

        def _apply(result):
            new_char = dict(char)
            new_char["personality"] = result
            cmd = EditCharacterCommand(self.project_manager, idx, char, new_char, "AI识别角色性格")
            self.command_executor(cmd)
            self._refresh_personality_chart(new_char)

        self.ai_controller.analyze_character_personality(
            char_name=char_name,
            char_desc=char_desc,
            scene_texts=scene_texts,
            on_success=_apply
        )

    def add_scene(self):
        name = simpledialog.askstring("添加场景", "场景名:", parent=self.parent)
        if name:
            scene_data = {
                "name": name,
                "location": "", "time": "", "image_path": "", "content": "",
                "characters": [], "tags": [], "outline_ref": "", "outline_ref_id": "", "outline_ref_path": ""
            }
            command = AddSceneCommand(self.project_manager, scene_data, "添加场景")
            self.command_executor(command)

    def delete_scene(self):
        idx = self._get_selected_scene_index()
        if idx is None: return
        if messagebox.askyesno("确认删除", "确定要删除该场景吗?"):
            scene_data_to_delete = self.project_manager.get_scenes()[idx]
            command = DeleteSceneCommand(self.project_manager, idx, scene_data_to_delete, "删除场景")
            self.command_executor(command)
            if self.current_scene_idx == idx:
                self.current_scene_idx = None
                self.script_editor.delete("1.0", tk.END)

    def _get_selected_scene_index(self):
        sel = self.scene_listbox.curselection()
        if not sel: return None
        idx = sel[0]
        if self.scene_index_map and idx < len(self.scene_index_map):
            return self.scene_index_map[idx]
        return idx

    def on_scene_select(self, e):
        scene_idx = self._get_selected_scene_index()
        if scene_idx is not None:
            scene = self.project_manager.get_scenes()[scene_idx]
            self.scene_name_var.set(scene.get("name", ""))
            self.scene_location_var.set(scene.get("location", ""))
            self.scene_time_var.set(scene.get("time", ""))
            self.scene_image_var.set(scene.get("image_path", ""))
            self.scene_bgm_var.set(scene.get("bgm_path", ""))
            
            # Load choices for Galgame
            if hasattr(self, "choices_listbox"):
                self.refresh_choices_list(scene)

            # Preselect characters
            self.scene_characters_listbox.selection_clear(0, tk.END)
            scene_chars = set(scene.get("characters", []))
            for idx, char in enumerate(self.project_manager.get_characters()):
                if char.get("name") in scene_chars:
                    self.scene_characters_listbox.selection_set(idx)
        else:
            self.scene_name_var.set("")
            self.scene_location_var.set("")
            self.scene_time_var.set("")
            self.scene_characters_listbox.selection_clear(0, tk.END)

    def load_scene_to_editor(self):
        scene_idx = self._get_selected_scene_index()
        if scene_idx is None: return
        
        if self.current_scene_idx is not None:
            self.save_scene_content()
        
        scene = self.project_manager.get_scenes()[scene_idx]
        self.script_editor.delete("1.0", tk.END)
        self.script_editor.insert("1.0", scene.get("content", ""))
        self.script_editor.highlight_all()
        self.current_scene_idx = scene_idx
        
        # Preload Assets (Galgame)
        if self.project_manager.get_project_type() == "Galgame":
            self._preload_scene_assets(scene_idx)

        # Trigger Smart Ambience
        if self.ambiance_player and self.ambiance_player.enabled:
            context = f"{scene.get('location', '')} {scene.get('time', '')} {' '.join(scene.get('tags', []))}"
            self.ambiance_player.play_smart(context)

    def _preload_scene_assets(self, scene_idx):
        scenes = self.project_manager.get_scenes()
        if not (0 <= scene_idx < len(scenes)): return
        
        to_preload = []
        
        # 1. Current Scene Assets
        current = scenes[scene_idx]
        if current.get("image_path"): to_preload.append(current["image_path"])
        if current.get("bgm_path"): to_preload.append(current["bgm_path"])
        
        # 2. Next Scenes (via choices)
        # Find scenes referenced by choices
        scene_map = {s.get("name"): s for s in scenes}
        for choice in current.get("choices", []):
            tgt_name = choice.get("target_scene")
            if tgt_name and tgt_name in scene_map:
                s = scene_map[tgt_name]
                if s.get("image_path"): to_preload.append(s["image_path"])
                if s.get("bgm_path"): to_preload.append(s["bgm_path"])
        
        self.resource_loader.preload(to_preload)

    def save_scene_info(self):
        idx = self._get_selected_scene_index()
        if idx is None: return
        old_scene_data = self.project_manager.get_scenes()[idx]
        selected_chars = [self.scene_characters_listbox.get(i) for i in self.scene_characters_listbox.curselection()]

        new_scene_data = dict(old_scene_data)
        new_scene_data.update({
            "name": self.scene_name_var.get().strip(),
            "location": self.scene_location_var.get().strip(),
            "time": self.scene_time_var.get().strip(),
            "image_path": self.scene_image_var.get().strip(),
            "bgm_path": self.scene_bgm_var.get().strip() if hasattr(self, "scene_bgm_var") else "",
            "characters": selected_chars,
        })
        
        # Wiki Location Image Check (Optimization)
        loc = new_scene_data["location"]
        if loc and not new_scene_data["image_path"]:
            # Search Wiki
            entries = self.project_manager.get_world_entries()
            found_img = None
            for e in entries:
                if e.get("category") == "地点" and e.get("name") == loc and e.get("image_path"):
                    found_img = e["image_path"]
                    break
            
            if found_img:
                if messagebox.askyesno("关联资源", f"检测到地点 '{loc}' 在百科中有设定图。\n是否应用该图片作为场景背景？"):
                    new_scene_data["image_path"] = found_img
                    self.scene_image_var.set(found_img)

        # Save choices if Galgame
        if hasattr(self, "choices_listbox"):
            # We don't edit choices here, we edit them via the listbox buttons directly updating project data? 
            # Or we store them in a temp list? 
            # Ideally, add/delete buttons should modify the SCENE data directly or a temp list.
            # To keep it simple, let's assume choices are managed by the buttons and this SAVE button 
            # syncs the other fields. BUT, if we modify choices via buttons, we need to be careful.
            # Let's make the buttons modify the scene data directly using commands.
            pass
        
        if old_scene_data != new_scene_data:
            command = EditSceneCommand(self.project_manager, idx, old_scene_data, new_scene_data, "保存场景信息")
            self.command_executor(command)
            # Sync to timeline
            self._sync_scene_to_timeline(idx, new_scene_data)

    def _sync_scene_to_timeline(self, scene_idx, scene_data):
        """Update any linked timeline events when scene info changes."""
        truth_events = self.project_manager.project_data.get("timelines", {}).get("truth_events", [])
        scene_uid = scene_data.get("uid", "")
        for event in truth_events:
            if event.get("linked_scene_uid") == scene_uid or (
                not event.get("linked_scene_uid") and event.get("linked_scene_index") == scene_idx
            ):
                old_data = dict(event)
                new_data = dict(event)
                # Sync basic fields if they match or were empty
                new_data["name"] = scene_data.get("name")
                new_data["location"] = scene_data.get("location")
                if scene_uid:
                    new_data["linked_scene_uid"] = scene_uid
                new_data.pop("linked_scene_index", None)
                
                # Try to parse and sync timestamp if format matches YYYY-MM-DD HH:MM
                time_str = scene_data.get("time", "")
                parsed_ts = AnalysisUtils.parse_date(time_str)
                if parsed_ts:
                    # Keep original HH:MM if present in event but missing in parsed_ts
                    if ":" not in parsed_ts and ":" in event.get("timestamp", ""):
                        time_part = event.get("timestamp").split(" ")[1] if " " in event.get("timestamp") else "00:00"
                        new_data["timestamp"] = f"{parsed_ts} {time_part}"
                    else:
                        new_data["timestamp"] = parsed_ts
                
                if old_data != new_data:
                    from writer_app.core.commands import EditTimelineEventCommand
                    cmd = EditTimelineEventCommand(self.project_manager, "truth", event.get("uid"), old_data, new_data, "同步场景更改至时间轴")
                    self.command_executor(cmd)

    def save_scene_content(self):
        if self.current_scene_idx is None: return
        
        scenes = self.project_manager.get_scenes()
        if not (0 <= self.current_scene_idx < len(scenes)): return
        
        old_content = scenes[self.current_scene_idx].get("content", "")
        new_content = self.script_editor.get("1.0", tk.END).strip()
        
        if old_content != new_content:
            command = EditSceneContentCommand(self.project_manager, self.current_scene_idx, old_content, new_content, "编辑场景内容")
            self.command_executor(command)
            
            # Check Status Automaton
            self._check_status_update(self.current_scene_idx, new_content)

            # Auto-extract chars
            char_matches = AnalysisUtils.extract_characters(new_content, self.project_manager.get_characters())
            if char_matches:
                current_chars = set(scenes[self.current_scene_idx].get("characters", []))
                added = set(char_matches) - current_chars
                if added:
                    updated_chars = list(current_chars.union(added))
                    scene = scenes[self.current_scene_idx]
                    new_scene = dict(scene)
                    new_scene["characters"] = updated_chars
                    cmd = EditSceneCommand(self.project_manager, self.current_scene_idx, scene, new_scene, "自动提取角色")
                    self.command_executor(cmd)
                    self.refresh_scene_characters_options()
                    # Check for faction conflicts after adding chars
                    self._check_faction_conflicts(updated_chars)

    def _check_faction_conflicts(self, char_names):
        """Check if characters from opposing factions are present."""
        if not char_names or len(char_names) < 2: return
        
        # 1. Map chars to factions (how? manually or via wiki?)
        # We need a way to link char to faction. 
        # For now, let's assume char description or tags contains faction name.
        # OR we can add a 'faction' field to character data.
        # Let's search wiki entries for faction names in char tags/desc.
        
        factions = self.project_manager.get_factions() # List of {uid, name}
        if not factions: return
        
        char_faction_map = {}
        for cname in char_names:
            # Find char obj
            char = next((c for c in self.project_manager.get_characters() if c["name"] == cname), None)
            if not char: continue
            
            # Check tags or description for faction name
            for f in factions:
                if f["name"] in char.get("tags", []) or f["name"] in char.get("description", ""):
                    char_faction_map[cname] = f["uid"]
                    break
        
        if len(char_faction_map) < 2: return
        
        matrix = self.project_manager.get_faction_matrix()
        
        # Check pairs
        conflict_msg = []
        checked = set()
        
        for c1, f1 in char_faction_map.items():
            for c2, f2 in char_faction_map.items():
                if c1 == c2 or (c1, c2) in checked or (c2, c1) in checked: continue
                
                # Check relation
                val = matrix.get(f1, {}).get(f2, 0)
                if val < -50: # Hostile threshold
                    fname1 = next(f["name"] for f in factions if f["uid"] == f1)
                    fname2 = next(f["name"] for f in factions if f["uid"] == f2)
                    conflict_msg.append(f"{c1}({fname1}) vs {c2}({fname2}): 关系恶劣 ({val})")
                
                checked.add((c1, c2))
                
        if conflict_msg:
            # Show non-intrusive alert? Or status bar?
            # Flash status bar for now
            msg = "⚠️ 势力冲突警报: " + " | ".join(conflict_msg)
            if hasattr(self.parent.winfo_toplevel(), "status_var"):
                self.parent.winfo_toplevel().status_var.set(msg)

    def _check_status_update(self, scene_idx, content):
        scenes = self.project_manager.get_scenes()
        scene = scenes[scene_idx]
        status = scene.get("status")
        cols = self.project_manager.get_kanban_columns()
        
        word_count = len(content.strip())
        new_status = None
        
        # Simple Rules
        if not status or status == cols[0]: # e.g. "构思"
            if word_count > 50 and len(cols) > 1:
                new_status = cols[1] # "初稿"
        elif status == cols[1] and len(cols) > 2: # e.g. "初稿"
            if word_count > 1000:
                new_status = cols[2] # "润色"
                
        if new_status:
            new_scene = dict(scene)
            new_scene["status"] = new_status
            cmd = EditSceneCommand(self.project_manager, scene_idx, scene, new_scene, f"自动更新状态至 {new_status}")
            self.command_executor(cmd)

    def save_scene_snapshot(self):
        if self.current_scene_idx is None: return
        scene = self.project_manager.get_scenes()[self.current_scene_idx]
        note = simpledialog.askstring("存快照", "版本备注 (可选):", parent=self.parent)
        if note is None: return # Cancelled
        
        content = self.script_editor.get("1.0", tk.END).strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if "snapshots" not in scene: scene["snapshots"] = []
        scene["snapshots"].append({
            "timestamp": timestamp,
            "content": content,
            "note": note or "手动保存"
        })
        self.project_manager.mark_modified()
        messagebox.showinfo("成功", f"快照 '{timestamp}' 已保存")

    def view_scene_history(self):
        if self.current_scene_idx is None: return
        scene = self.project_manager.get_scenes()[self.current_scene_idx]
        snapshots = scene.get("snapshots", [])
        if not snapshots:
            messagebox.showinfo("历史", "该场景暂无历史快照。")
            return
            
        # Dialog to pick snapshot
        dlg = tk.Toplevel(self.parent)
        dlg.title("场景历史版本")
        dlg.geometry("400x300")
        
        listbox = tk.Listbox(dlg)
        listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        for s in reversed(snapshots):
            listbox.insert(tk.END, f"{s['timestamp']} - {s['note']}")
            
        def restore():
            sel = listbox.curselection()
            if not sel: return
            idx = len(snapshots) - 1 - sel[0]
            snap = snapshots[idx]
            if messagebox.askyesno("确认恢复", f"恢复到版本 {snap['timestamp']}？当前未保存内容将丢失。"):
                self.script_editor.delete("1.0", tk.END)
                self.script_editor.insert("1.0", snap["content"])
                self.save_scene_content()
                dlg.destroy()
                
        ttk.Button(dlg, text="恢复选中版本", command=restore).pack(pady=5)

    def read_scene_aloud(self):
        content = self.script_editor.get("1.0", tk.END).strip()
        if not content: return
        
        self.is_reading = True
        self.tts_read_btn.configure(state=tk.DISABLED)
        self.tts_stop_btn.configure(state=tk.NORMAL)
        
        self.tts_manager.speak(content, on_finish=self._on_tts_finished)

    def stop_reading(self):
        self.tts_manager.stop()
        self._on_tts_finished()

    def _on_tts_finished(self):
        self.is_reading = False
        if hasattr(self, "tts_read_btn"):
            self.tts_read_btn.configure(state=tk.NORMAL)
        if hasattr(self, "tts_stop_btn"):
            self.tts_stop_btn.configure(state=tk.DISABLED)

    def open_tts_settings(self):
        dlg = tk.Toplevel(self.parent)
        dlg.title("TTS 设置")
        dlg.geometry("400x250")
        
        ttk.Label(dlg, text="语速 (Rate):").pack(pady=5)
        rate_var = tk.IntVar(value=self.tts_manager.get_rate())
        rate_scale = ttk.Scale(dlg, from_=50, to=300, variable=rate_var, orient=tk.HORIZONTAL)
        rate_scale.pack(fill=tk.X, padx=20)
        
        ttk.Label(dlg, text="语音 (Voice):").pack(pady=5)
        voices = self.tts_manager.get_voices()
        voice_names = [v.name for v in voices]
        voice_var = tk.StringVar()
        
        # Try to match current voice if possible (not implemented in getter but we can default)
        if voices: voice_var.set(voice_names[0])
        
        voice_combo = ttk.Combobox(dlg, textvariable=voice_var, values=voice_names, state="readonly")
        voice_combo.pack(pady=5)
        
        def save():
            self.tts_manager.set_rate(rate_var.get())
            if voices:
                idx = voice_combo.current()
                if idx >= 0:
                    self.tts_manager.set_voice(voices[idx].id)
            dlg.destroy()
            
        def test():
            self.tts_manager.set_rate(rate_var.get())
            if voices:
                idx = voice_combo.current()
                if idx >= 0:
                    self.tts_manager.set_voice(voices[idx].id)
            self.tts_manager.speak("这是一个测试语音。 This is a test voice.")
            
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="试听", command=test).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="确定", command=save).pack(side=tk.LEFT, padx=5)

    def ai_continue_script(self, context_text):
        if not self.config_manager.is_ai_enabled():
            messagebox.showinfo("提示", "当前为非AI模式，AI续写不可用。")
            return
        if not self.config_manager.get("lm_api_url") or not self.config_manager.get("lm_api_model"):
            messagebox.showwarning("AI配置缺失", "请先在设置中配置AI API地址和模型名称。" )
            return
            
        if self.script_ai_generating:
            return

        self.script_ai_generating = True
        self.script_editor.config(cursor="watch")
        
        # Gather Context
        scene_info = ""
        if self.current_scene_idx is not None:
            scene = self.project_manager.get_scenes()[self.current_scene_idx]
            scene_info = f"场景: {scene.get('name')}\n地点: {scene.get('location')}\n时间: {scene.get('time')}\n"
            
        chars = self.project_manager.get_characters()
        char_info = "登场角色:\n" + "\n".join([f"- {c.get('name')}: {c.get('description')}" for c in chars])
        
        base_prompt = self.config_manager.get("prompt_continue_script", "你是一个专业的编剧助手。请根据提供的上下文续写剧本。")
        system_prompt = f"""{base_prompt}
项目类型: {self.project_manager.get_project_type()}
{scene_info}
{char_info}

请遵循标准剧本格式：
1. 场景标题使用 ### 开头 (或 ### 场景名)
2. 角色名后加冒号 (如 Name: )
3. 动作描写清晰简洁。
请只输出续写的内容，不要包含解释性语言。"""

        user_prompt = f"上文:\n{context_text}\n\n请续写:"
        
        def run_ai():
            return self.ai_client.call_lm_studio_with_prompts(
                self.config_manager.get("lm_api_url"),
                self.config_manager.get("lm_api_model"),
                self.config_manager.get("lm_api_key"),
                system_prompt,
                user_prompt
            )

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="script_continue",
            fn=run_ai,
            on_success=self._on_ai_success,
            on_error=lambda e: self._on_ai_error(str(e)),
            tk_root=self.parent
        )

    def _on_ai_success(self, content):
        self.script_ai_generating = False
        self.script_editor.config(cursor="")
        if content:
            self.script_editor.insert(tk.INSERT, " " + content)
            self.script_editor.see(tk.INSERT)
            self.save_scene_content() # Auto save

    def _on_ai_error(self, error_msg):
        self.script_ai_generating = False
        self.script_editor.config(cursor="")
        messagebox.showerror("AI生成失败", error_msg)

    def ai_rewrite_script(self, original_text, style, callback):
        if not self.config_manager.is_ai_enabled():
            messagebox.showinfo("提示", "当前为非AI模式，AI重写不可用。")
            callback(original_text)
            return
        if not self.config_manager.get("lm_api_url") or not self.config_manager.get("lm_api_model"):
            messagebox.showwarning("AI配置缺失", "请先在设置中配置AI API地址和模型名称。" )
            callback(original_text) # Restore
            return

        base_prompt = self.config_manager.get("prompt_rewrite_script", "你是一个专业的剧本润色助手。请将用户提供的文本重写为'{style}'风格。")
        sys_prompt = f"{base_prompt} 保持原意，仅调整语气和修辞。不要输出任何解释，直接输出重写后的文本。"
        
        def run_ai():
            return self.ai_client.call_lm_studio_with_prompts(
                self.config_manager.get("lm_api_url"),
                self.config_manager.get("lm_api_model"),
                self.config_manager.get("lm_api_key"),
                sys_prompt,
                original_text
            )

        def on_success(res):
            callback(res if res else original_text)

        def on_error(e):
            messagebox.showerror("AI Error", str(e))
            callback(original_text)

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="script_rewrite",
            fn=run_ai,
            on_success=on_success,
            on_error=on_error,
            tk_root=self.parent
        )

    def open_scene_tag_selector(self):
        pass # Simplified for controller
        
    def browse_scene_image(self):
        # LightNovel Smart Suggestion
        if self.project_manager.get_project_type() == "LightNovel":
            self._smart_browse_image()
            return

        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp")],
            title="选择场景背景图"
        )
        if path:
            self.scene_image_var.set(path)

    def _smart_browse_image(self):
        # Dialog to choose between File or Character Sprites
        dlg = tk.Toplevel(self.parent)
        dlg.title("选择插画/背景")
        dlg.geometry("400x300")
        
        selected_path = [None]
        
        def pick_file():
            path = filedialog.askopenfilename(
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp")],
                title="选择文件"
            )
            if path:
                selected_path[0] = path
                dlg.destroy()
        
        ttk.Button(dlg, text="📂 浏览本地文件...", command=pick_file).pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(dlg, text="-- 或从关联角色中选择 --").pack(pady=5)
        
        list_frame = ttk.Frame(dlg)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        lb = tk.Listbox(list_frame)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=lb.yview)
        lb.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Gather chars in current scene
        scene_idx = self._get_selected_scene_index()
        candidates = []
        if scene_idx is not None:
            scene = self.project_manager.get_scenes()[scene_idx]
            scene_chars = scene.get("characters", [])
            all_chars = self.project_manager.get_characters()
            
            for c_name in scene_chars:
                char_data = next((c for c in all_chars if c["name"] == c_name), None)
                if char_data and char_data.get("image_path"):
                    candidates.append((c_name, char_data["image_path"]))
                    lb.insert(tk.END, f"👤 {c_name} (立绘)")
        
        if not candidates:
            lb.insert(tk.END, "(当前场景无带立绘的角色)")
            lb.configure(state=tk.DISABLED)
            
        def on_select(e):
            sel = lb.curselection()
            if not sel or not candidates: return
            idx = sel[0]
            if idx < len(candidates):
                selected_path[0] = candidates[idx][1]
                dlg.destroy()
                
        lb.bind("<Double-1>", on_select)
        ttk.Button(dlg, text="确定选择", command=lambda: on_select(None)).pack(pady=5)
        
        self.parent.wait_window(dlg)
        if selected_path[0]:
            self.scene_image_var.set(selected_path[0])

    def browse_scene_bgm(self):
        path = filedialog.askopenfilename(
            filetypes=[("Audio", "*.mp3;*.wav;*.ogg;*.flac")],
            title="选择背景音乐"
        )
        if path:
            self.scene_bgm_var.set(path)

    def add_choice(self):
        idx = self._get_selected_scene_index()
        if idx is None: return
        
        # 1. Ask for text
        text = simpledialog.askstring("添加选项", "选项文本:")
        if not text: return
        
        # 2. Ask for target scene (simple list selection dialog)
        scenes = self.project_manager.get_scenes()
        scene_names = [f"{i+1}. {s.get('name', '未命名')}" for i, s in enumerate(scenes)]
        
        target_dlg = tk.Toplevel(self.parent)
        target_dlg.title("选项设置")
        
        # Target
        target_var = tk.StringVar()
        ttk.Label(target_dlg, text="跳转至:").pack(pady=5)
        combo = ttk.Combobox(target_dlg, textvariable=target_var, values=scene_names, state="readonly")
        combo.pack(padx=10, pady=5)
        
        # Condition
        ttk.Label(target_dlg, text="出现条件 (逻辑):").pack(pady=5)
        cond_entry = ttk.Entry(target_dlg, width=30)
        cond_entry.pack(padx=10, pady=2)
        ttk.Label(target_dlg, text="条件描述 (自然语言，如'需高好感'):").pack(pady=0)
        cond_desc_entry = ttk.Entry(target_dlg, width=30)
        cond_desc_entry.pack(padx=10, pady=5)
        
        # Effects
        ttk.Label(target_dlg, text="选择后效果 (逻辑):").pack(pady=5)
        effect_text = tk.Text(target_dlg, height=3, width=30)
        effect_text.pack(padx=10, pady=2)
        ttk.Label(target_dlg, text="效果描述 (自然语言，如'好感上升'):").pack(pady=0)
        eff_desc_entry = ttk.Entry(target_dlg, width=30)
        eff_desc_entry.pack(padx=10, pady=5)
        
        result = {"target": "", "condition": "", "effects": [], "cond_desc": "", "eff_desc": ""}
        
        def on_ok():
            if combo.current() >= 0:
                result["target"] = scenes[combo.current()].get("name")
            result["condition"] = cond_entry.get().strip()
            result["cond_desc"] = cond_desc_entry.get().strip()
            result["eff_desc"] = eff_desc_entry.get().strip()
            
            effects_raw = effect_text.get("1.0", tk.END).strip()
            if effects_raw:
                result["effects"] = [line.strip() for line in effects_raw.split("\n") if line.strip()]
            target_dlg.destroy()
            
        ttk.Button(target_dlg, text="确定", command=on_ok).pack(pady=10)
        self.parent.wait_window(target_dlg)
        
        scene = self.project_manager.get_scenes()[idx]
        new_scene = dict(scene)
        choices = list(scene.get("choices", []))
        
        new_choice = {
            "text": text,
            "target_scene": result["target"],
            "condition": result["condition"],
            "effects": result["effects"],
            "condition_desc": result["cond_desc"],
            "effect_desc": result["eff_desc"]
        }
        
        choices.append(new_choice)
        new_scene["choices"] = choices
        
        cmd = EditSceneCommand(self.project_manager, idx, scene, new_scene, "添加选项")
        self.command_executor(cmd)
        
        self.refresh_choices_list(new_scene)

    def edit_choice(self):
        idx = self._get_selected_scene_index()
        if idx is None: return
        
        sel = self.choices_listbox.curselection()
        if not sel: return
        choice_idx = sel[0]
        
        scene = self.project_manager.get_scenes()[idx]
        choices = scene.get("choices", [])
        if not (0 <= choice_idx < len(choices)): return
        
        old_choice = choices[choice_idx]
        
        # Ask for text
        text = simpledialog.askstring("编辑选项", "选项文本:", initialvalue=old_choice.get("text", ""))
        if not text: return
        
        # Ask for target and logic
        scenes = self.project_manager.get_scenes()
        scene_names = [f"{i+1}. {s.get('name', '未命名')}" for i, s in enumerate(scenes)]
        
        target_dlg = tk.Toplevel(self.parent)
        target_dlg.title("选项设置")
        
        # Target
        target_var = tk.StringVar()
        current_target = old_choice.get("target_scene", "")
        current_idx = -1
        if current_target:
            for i, s in enumerate(scenes):
                if s.get("name") == current_target:
                    current_idx = i
                    break
        
        ttk.Label(target_dlg, text="跳转至:").pack(pady=5)
        combo = ttk.Combobox(target_dlg, textvariable=target_var, values=scene_names, state="readonly")
        combo.pack(padx=10, pady=5)
        if current_idx >= 0:
            combo.current(current_idx)
            
        # Condition
        ttk.Label(target_dlg, text="出现条件 (逻辑):").pack(pady=5)
        cond_entry = ttk.Entry(target_dlg, width=30)
        cond_entry.pack(padx=10, pady=2)
        cond_entry.insert(0, old_choice.get("condition", ""))
        
        ttk.Label(target_dlg, text="条件描述 (自然语言):").pack(pady=0)
        cond_desc_entry = ttk.Entry(target_dlg, width=30)
        cond_desc_entry.pack(padx=10, pady=5)
        cond_desc_entry.insert(0, old_choice.get("condition_desc", ""))
        
        # Effects
        ttk.Label(target_dlg, text="选择后效果 (逻辑):").pack(pady=5)
        effect_text = tk.Text(target_dlg, height=3, width=30)
        effect_text.pack(padx=10, pady=2)
        if old_choice.get("effects"):
            effect_text.insert("1.0", "\n".join(old_choice.get("effects", [])))
            
        ttk.Label(target_dlg, text="效果描述 (自然语言):").pack(pady=0)
        eff_desc_entry = ttk.Entry(target_dlg, width=30)
        eff_desc_entry.pack(padx=10, pady=5)
        eff_desc_entry.insert(0, old_choice.get("effect_desc", ""))
            
        result = {"target": current_target, "condition": "", "effects": [], "cond_desc": "", "eff_desc": ""}
        
        def on_ok():
            if combo.current() >= 0:
                result["target"] = scenes[combo.current()].get("name")
            result["condition"] = cond_entry.get().strip()
            result["cond_desc"] = cond_desc_entry.get().strip()
            result["eff_desc"] = eff_desc_entry.get().strip()
            
            effects_raw = effect_text.get("1.0", tk.END).strip()
            if effects_raw:
                result["effects"] = [line.strip() for line in effects_raw.split("\n") if line.strip()]
            target_dlg.destroy()
            
        ttk.Button(target_dlg, text="确定", command=on_ok).pack(pady=10)
        self.parent.wait_window(target_dlg)
        
        new_choice = {
            "text": text,
            "target_scene": result["target"],
            "condition": result["condition"],
            "effects": result["effects"],
            "condition_desc": result["cond_desc"],
            "effect_desc": result["eff_desc"]
        }
        
        new_scene = dict(scene)
        new_choices = list(choices)
        new_choices[choice_idx] = new_choice
        new_scene["choices"] = new_choices
        
        cmd = EditSceneCommand(self.project_manager, idx, scene, new_scene, "编辑选项")
        self.command_executor(cmd)
        self.refresh_choices_list(new_scene)

    def refresh_choices_list(self, scene_data):
        if not hasattr(self, "choices_listbox"): return
        self.choices_listbox.delete(0, tk.END)
        for c in scene_data.get("choices", []):
            target = c.get("target_scene", "")
            
            # Prioritize descriptions, hide raw logic
            if c.get("condition_desc"):
                cond = f" [需: {c.get('condition_desc')}]"
            elif c.get("condition"):
                cond = " [有条件]" # Hide raw code
            else:
                cond = ""
                
            if c.get("effect_desc"):
                eff = f" [则: {c.get('effect_desc')}]"
            elif c.get("effects"):
                eff = " [有效果]" # Hide raw code
            else:
                eff = ""
                
            display = f"{c.get('text', '选项')} -> {target if target else '(无)'}{cond}{eff}"
            self.choices_listbox.insert(tk.END, display)

    def delete_choice(self):
        idx = self._get_selected_scene_index()
        if idx is None: return
        
        sel = self.choices_listbox.curselection()
        if not sel: return
        choice_idx = sel[0]
        
        scene = self.project_manager.get_scenes()[idx]
        new_scene = dict(scene)
        choices = list(scene.get("choices", []))
        
        if 0 <= choice_idx < len(choices):
            del choices[choice_idx]
            new_scene["choices"] = choices
            cmd = EditSceneCommand(self.project_manager, idx, scene, new_scene, "删除选项")
            self.command_executor(cmd)
            self.choices_listbox.delete(choice_idx)

    def open_flowchart(self):
        win = tk.Toplevel(self.parent)
        win.title("剧情流向图 - Story Flow (右键拖拽连接节点)")
        win.geometry("800x600")
        
        canvas = StoryFlowCanvas(
            win, 
            self.project_manager, 
            on_jump_to_scene=self.jump_to_scene_from_flowchart,
            on_add_connection=self.add_connection_from_flowchart
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.refresh()

    def jump_to_scene_from_flowchart(self, idx):
        # Callback to select scene in main list
        if hasattr(self, "scene_listbox"):
            self.scene_listbox.selection_clear(0, tk.END)
            self.scene_listbox.selection_set(idx)
            self.scene_listbox.event_generate("<<ListboxSelect>>")
            self.scene_listbox.see(idx)
            self.load_scene_to_editor()

    def add_connection_from_flowchart(self, src_name, tgt_name):
        scenes = self.project_manager.get_scenes()
        src_idx = -1
        for i, s in enumerate(scenes):
            if s.get("name") == src_name:
                src_idx = i
                break
        
        if src_idx < 0: return

        # Prompt for text
        text = simpledialog.askstring("创建分支", f"从 '{src_name}' 跳转到 '{tgt_name}' 的选项文本:", initialvalue=f"前往 {tgt_name}")
        if not text: return

        scene = scenes[src_idx]
        new_scene = dict(scene)
        choices = list(scene.get("choices", []))
        choices.append({"text": text, "target_scene": tgt_name})
        new_scene["choices"] = choices
        
        cmd = EditSceneCommand(self.project_manager, src_idx, scene, new_scene, f"添加分支: {src_name}->{tgt_name}")
        self.command_executor(cmd)
        
        # Refresh if this scene is selected
        if self.current_scene_idx == src_idx:
            self.refresh_choices_list(new_scene)


class PersonalityEditDialog(simpledialog.Dialog):
    """编辑角色性格五维值"""

    def __init__(self, parent, values):
        self.values = values or {}
        self.result = None
        self._vars = {}
        super().__init__(parent, title="编辑性格")

    def body(self, master):
        for row, (key, label) in enumerate(PERSONALITY_FIELDS):
            ttk.Label(master, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
            
            var = tk.DoubleVar(value=float(self.values.get(key, 5)))
            
            # Slider
            scale = ttk.Scale(master, from_=0, to=10, variable=var, orient=tk.HORIZONTAL, length=150)
            scale.grid(row=row, column=1, padx=5, pady=4)
            
            # Descriptive Label (Low/High) instead of number
            desc_lbl = ttk.Label(master, text="中等", width=6, foreground="#666")
            desc_lbl.grid(row=row, column=2, padx=5)
            
            def update_desc(v, lbl=desc_lbl):
                try:
                    val = float(v)
                    if val < 3: txt = "低"
                    elif val > 7: txt = "高"
                    else: txt = "中等"
                    lbl.config(text=txt)
                except: pass
                
            scale.configure(command=update_desc)
            update_desc(var.get()) # Init
            
            self._vars[key] = var

        master.columnconfigure(1, weight=1)
        return master

    def apply(self):
        result = {}
        for key, var in self._vars.items():
            result[key] = var.get()
        self.result = result
