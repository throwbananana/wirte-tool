"""
悬浮助手右键菜单 (Context Menu)
"""
import tkinter as tk
from .constants import QUICK_PROMPTS_AI, QUICK_TOOLS
from .theme import ThemeManager

class AssistantContextMenu:
    """管理悬浮助手的右键菜单"""

    def __init__(self, assistant):
        self.assistant = assistant

    def show(self, event):
        """显示右键菜单"""
        theme = ThemeManager.get_theme()
        menu = tk.Menu(self.assistant, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)

        # 检查选中文本
        selected_text = self.assistant.get_selected_text()
        if selected_text:
            # 选中文本操作置顶
            context_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
            context_menu.add_command(label="✨ 扩写选中内容", command=self.assistant.send_selected_for_expansion)
            context_menu.add_command(label="💎 润色选中内容", command=self.assistant.send_selected_for_polish)
            context_menu.add_command(label="📝 续写选中内容", command=self.assistant.send_selected_for_continue)
            context_menu.add_separator()
            context_menu.add_command(label="📋 插入到输入框", command=self.assistant._insert_context)
            
            menu.add_cascade(label="📋 选中内容操作", menu=context_menu)
            menu.add_separator()

        # AI/工具模式
        if self.assistant.ai_mode_enabled:
            ai_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
            for i, (name, _) in enumerate(QUICK_PROMPTS_AI):
                ai_menu.add_command(label=name, command=lambda idx=i: self.assistant._use_ai_prompt(idx))
            menu.add_cascade(label="✨ AI功能", menu=ai_menu)
        else:
            tools_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
            for name, tool_id in QUICK_TOOLS:
                tools_menu.add_command(label=name, command=lambda tid=tool_id: self.assistant._use_tool(tid))
            menu.add_cascade(label="🔧 写作工具", menu=tools_menu)

        menu.add_separator()

        # 小游戏
        games_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
        games_menu.add_command(label="🎯 猜数字", command=lambda: self.assistant._start_game("guess_number"))
        games_menu.add_command(label="✊ 石头剪刀布", command=lambda: self.assistant._start_game("rps"))
        games_menu.add_command(label="🔤 成语接龙", command=lambda: self.assistant._start_game("word_chain"))
        games_menu.add_command(label="💭 词语联想", command=lambda: self.assistant._start_game("word_association"))
        games_menu.add_command(label="📖 故事接龙", command=lambda: self.assistant._start_game("story"))
        menu.add_cascade(label="🎮 小游戏", menu=games_menu)

        menu.add_separator()

        # 互动
        interact_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
        interact_menu.add_command(label="🍪 喂食", command=self.assistant._feed_assistant)
        interact_menu.add_command(label="👋 打招呼", command=self.assistant._greet_assistant)
        interact_menu.add_command(label="🏆 成就", command=self.assistant._show_achievements)
        interact_menu.add_command(label="📦 收藏", command=self.assistant._show_collection)
        interact_menu.add_command(label="📜 事件历史", command=self.assistant._show_event_history)
        menu.add_cascade(label="💫 互动", menu=interact_menu)

        menu.add_separator()

        # 相册
        album_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
        album_menu.add_command(label="📸 拍照留念", command=self.assistant._capture_current)
        album_menu.add_command(label="📷 查看相册", command=self.assistant._open_album)
        album_menu.add_command(label="🖼️ 收藏统计", command=self.assistant._show_album_stats)
        menu.add_cascade(label="📸 相册", menu=album_menu)

        # 语音功能
        if self.assistant.voice_assistant.is_available:
            voice_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
            voice_menu.add_command(label="🎤 语音输入", command=self.assistant._toggle_voice_input)
            if self.assistant.voice_assistant.has_tts:
                voice_menu.add_command(label="🔊 朗读对话", command=lambda: self.assistant._read_last_response())
                voice_menu.add_command(label="⏹️ 停止朗读", command=self.assistant._stop_reading)
                auto_text = "✓ 自动朗读" if self.assistant.auto_speak else "○ 自动朗读"
                voice_menu.add_command(label=auto_text, command=self.assistant._toggle_auto_speak)
            menu.add_cascade(label="🎙️ 语音", menu=voice_menu)
        else:
            menu.add_command(label="🎙️ 语音(未安装)", command=self.assistant._show_voice_install_guide)

        # 上下文功能
        context_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
        context_menu.add_command(label="📋 插入选中文本", command=self.assistant._insert_context)
        context_menu.add_command(label="📊 显示上下文信息", command=self.assistant._show_context_info)
        context_menu.add_separator()
        context_menu.add_command(label="✨ 扩写选中内容", command=self.assistant.send_selected_for_expansion)
        context_menu.add_command(label="💎 润色选中内容", command=self.assistant.send_selected_for_polish)
        context_menu.add_command(label="📝 续写选中内容", command=self.assistant.send_selected_for_continue)
        menu.add_cascade(label="📋 上下文", menu=context_menu)

        menu.add_separator()

        # 快速创建（联动项目数据）
        create_menu = tk.Menu(menu, tearoff=0, bg=theme.BG_SECONDARY, fg=theme.TEXT_PRIMARY)
        create_menu.add_command(label="👥 添加角色", command=self.assistant.quick_add_character)
        create_menu.add_command(label="📝 添加场景", command=self.assistant.quick_add_scene)
        create_menu.add_command(label="💡 记录灵感", command=self.assistant.quick_add_idea)
        create_menu.add_command(label="📚 添加研究", command=self.assistant.quick_add_research)
        create_menu.add_separator()
        create_menu.add_command(label="📊 项目统计", command=self.assistant.show_stats_panel)
        menu.add_cascade(label="➕ 快速创建", menu=create_menu)

        # 5. 系统设置
        menu.add_separator()
        from .constants import ASSISTANT_NAME
        menu.add_command(label=f"👗 {ASSISTANT_NAME}的衣橱", command=self.assistant._open_wardrobe)
        menu.add_command(label=f"⚙️ {ASSISTANT_NAME}设置", command=self.assistant._open_settings)
        menu.add_command(label="🗑️ 清空对话", command=self.assistant._clear_conversation)
        menu.add_command(label="🪟 切换主界面显示", command=self.assistant._toggle_main_window)
        menu.add_command(label="🚪 退出程序", command=self.assistant._exit_application)

        menu.add_separator()
        menu.add_command(label="❌ 隐藏", command=self.assistant._on_close)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
