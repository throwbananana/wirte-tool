import tkinter as tk
import re
from typing import List, Tuple, Callable

from writer_app.core.event_bus import get_event_bus, Events


class ScriptEditor(tk.Text):
    """Enhanced script editor with focus mode, syntax highlighting, and AI integration."""

    # Focus mode level constants
    FOCUS_LINE = "line"
    FOCUS_SENTENCE = "sentence"
    FOCUS_PARAGRAPH = "paragraph"
    FOCUS_DIALOGUE = "dialogue"

    def __init__(self, parent, project_manager=None, on_ai_continue=None, on_ai_rewrite=None,
                 on_content_change=None, command_executor=None, on_wiki_click=None,
                 config_manager=None, on_focus_mode_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.project_manager = project_manager

        # Lifecycle tracking for cleanup
        self._destroyed = False
        self._event_subscriptions: List[Tuple[str, Callable]] = []
        self._project_listeners: List[Callable] = []
        self.on_ai_continue = on_ai_continue
        self.on_ai_rewrite = on_ai_rewrite
        self.on_content_change = on_content_change
        self.command_executor = command_executor  # For executing commands with undo support
        self.on_wiki_click = on_wiki_click
        self.config_manager = config_manager
        self.on_focus_mode_change = on_focus_mode_change  # Callback when focus mode changes

        self.typewriter_mode = False
        self.focus_mode = False
        self.context_menu_target_text = ""

        # Focus mode settings
        self._focus_level = self.FOCUS_LINE
        self._focus_context_lines = 3
        self._focus_gradient = True
        self._focus_highlight_current = True
        self._focus_with_typewriter = True
        self._current_theme = "Light"

        # Focus mode debounce
        self._focus_update_job = None
        self._focus_update_delay_ms = 50

        # Autocomplete state
        self.autocomplete_popup = None
        self.autocomplete_candidates = []
        self.autocomplete_selected = 0
        self._autocomplete_trigger_chars = [":", "：", "【", "["]

        # Wiki term cache for performance
        self._wiki_terms_cache = []
        self._wiki_cache_dirty = True
        self._tooltip_popup = None
        self._tooltip_job = None
        self._last_hover_term = None

        # Highlight debounce
        self._highlight_job = None
        self._highlight_delay_ms = 100
        self._content_change_job = None
        self._content_change_delay_ms = 1200

        # Load focus mode config if available
        self._load_focus_config()

        # Default font
        if "font" not in kwargs:
            self.configure(font=("Microsoft YaHei", 11))

        self.bind("<KeyRelease>", self.on_key_release)
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<Button-1>", self.on_click_cursor_move)
        self.bind("<Button-3>", self._show_context_menu)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<Leave>", self._hide_wiki_tooltip)

        self._configure_tags()
        self._setup_context_menu()

        # Register listener for wiki updates if project_manager available
        if self.project_manager:
            self._add_project_listener(self._on_project_data_changed)

        # 订阅事件总线
        self._subscribe_events()

    def _add_project_listener(self, handler: Callable) -> None:
        """添加项目监听器并追踪以便清理"""
        if self.project_manager:
            self.project_manager.add_listener(handler)
            self._project_listeners.append(handler)

    def _subscribe_event(self, event_type: str, handler: Callable) -> None:
        """订阅事件并追踪以便清理"""
        bus = get_event_bus()
        bus.subscribe(event_type, handler)
        self._event_subscriptions.append((event_type, handler))

    def _subscribe_events(self):
        """订阅相关事件（使用追踪方法以便清理）"""
        self._subscribe_event(Events.SCENE_UPDATED, self._on_scene_updated)
        self._subscribe_event(Events.CHARACTER_UPDATED, self._on_character_updated)
        self._subscribe_event(Events.WIKI_ENTRY_UPDATED, self._on_wiki_updated)
        self._subscribe_event(Events.WIKI_ENTRY_ADDED, self._on_wiki_updated)
        self._subscribe_event(Events.WIKI_ENTRY_DELETED, self._on_wiki_updated)

    def destroy(self):
        """清理资源并销毁控件"""
        self._destroyed = True

        # 取消所有 pending after() 任务
        if self._highlight_job:
            try:
                self.after_cancel(self._highlight_job)
            except Exception:
                pass
            self._highlight_job = None

        if self._content_change_job:
            try:
                self.after_cancel(self._content_change_job)
            except Exception:
                pass
            self._content_change_job = None

        if self._tooltip_job:
            try:
                self.after_cancel(self._tooltip_job)
            except Exception:
                pass
            self._tooltip_job = None

        if self._focus_update_job:
            try:
                self.after_cancel(self._focus_update_job)
            except Exception:
                pass
            self._focus_update_job = None

        # 取消订阅 EventBus
        bus = get_event_bus()
        for event_type, handler in self._event_subscriptions:
            try:
                bus.unsubscribe(event_type, handler)
            except Exception:
                pass
        self._event_subscriptions.clear()

        # 移除项目监听器
        if self.project_manager:
            for handler in self._project_listeners:
                try:
                    self.project_manager.remove_listener(handler)
                except Exception:
                    pass
        self._project_listeners.clear()

        # 关闭工具提示
        self._hide_wiki_tooltip()

        super().destroy()

    def _on_scene_updated(self, event_type, **kwargs):
        """场景更新时触发高亮刷新"""
        self._wiki_cache_dirty = True
        self._debounce_highlight()

    def _on_character_updated(self, event_type, **kwargs):
        """角色更新时刷新高亮（角色名称可能变化）"""
        self._wiki_cache_dirty = True
        self._debounce_highlight()

    def _on_wiki_updated(self, event_type, **kwargs):
        """百科更新时刷新高亮"""
        self._wiki_cache_dirty = True
        self._debounce_highlight()

    def _debounce_highlight(self):
        """防抖高亮刷新"""
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(self._highlight_delay_ms, self._do_highlight)

    def _on_project_data_changed(self, event_type="all"):
        """Invalidate wiki cache when project data changes."""
        self._wiki_cache_dirty = True

    def _get_wiki_terms(self):
        """Get wiki terms (world entries + characters) with caching."""
        if self._wiki_cache_dirty or not self._wiki_terms_cache:
            if self.project_manager:
                # Get world entries with depth info
                self._wiki_terms_cache = []
                
                for e in self.project_manager.get_world_entries():
                    if e.get("name"):
                        self._wiki_terms_cache.append({
                            "term": e["name"],
                            "type": "entry",
                            "depth": e.get("iceberg_depth", "surface"),
                            "data": e
                        })
                
                # Get characters
                for c in self.project_manager.get_characters():
                    if c.get("name"):
                        self._wiki_terms_cache.append({
                            "term": c["name"],
                            "type": "character",
                            "depth": "surface", # Characters default to surface unless specified
                            "data": c
                        })
            else:
                self._wiki_terms_cache = []
            self._wiki_cache_dirty = False
        return self._wiki_terms_cache

    def _on_mouse_move(self, event):
        """Check if hovering over a wiki term to show tooltip."""
        idx = self.index(f"@{event.x},{event.y}")
        tags = self.tag_names(idx)
        
        if "wiki_term" in tags:
            # Find the term
            start, end = self.tag_prevrange("wiki_term", idx + " + 1 chars")
            if start and end:
                term = self.get(start, end)
                if term != self._last_hover_term:
                    self._hide_wiki_tooltip()
                    self._last_hover_term = term
                    # Debounce tooltip showing
                    if self._tooltip_job:
                        self.after_cancel(self._tooltip_job)
                    self._tooltip_job = self.after(500, lambda: self._show_wiki_tooltip(event.x_root, event.y_root, term))
                return
        
        # Not over a wiki term
        self._hide_wiki_tooltip()
        self._last_hover_term = None

    def _show_wiki_tooltip(self, x, y, term):
        """Show a small tooltip with wiki content."""
        if not self.project_manager: return
        
        # Find content
        content = ""
        category = ""
        
        # Check world entries
        for e in self.project_manager.get_world_entries():
            if e.get("name") == term:
                content = e.get("content", "")
                category = e.get("category", "词条")
                break
        
        # Check characters if not found
        if not content:
            for c in self.project_manager.get_characters():
                if c.get("name") == term:
                    content = c.get("description", "")
                    category = "角色"
                    break
                    
        if not content and not category: return
        
        # Create tooltip
        self._tooltip_popup = tk.Toplevel(self)
        self._tooltip_popup.wm_overrideredirect(True)
        self._tooltip_popup.wm_attributes("-topmost", True)
        self._tooltip_popup.configure(bg="#FFF9C4", highlightbackground="#FBC02D", highlightthickness=1)
        
        container = tk.Frame(self._tooltip_popup, bg="#FFF9C4", padx=5, pady=5)
        container.pack()
        
        tk.Label(container, text=f"[{category}] {term}", font=("Microsoft YaHei", 9, "bold"), 
                 bg="#FFF9C4", fg="#5D4037").pack(anchor="w")
        
        # Truncate content for preview
        preview_text = content[:200] + ("..." if len(content) > 200 else "")
        tk.Label(container, text=preview_text, font=("Microsoft YaHei", 9), 
                 bg="#FFF9C4", fg="#333", justify="left", wraplength=300).pack(anchor="w")
        
        tk.Label(container, text="点击跳转至详情", font=("Microsoft YaHei", 8, "italic"), 
                 bg="#FFF9C4", fg="#757575").pack(anchor="e", pady=(5,0))
        
        # Position it slightly offset from cursor
        self._tooltip_popup.geometry(f"+{x + 15}+{y + 15}")

    def _hide_wiki_tooltip(self, event=None):
        """Hide the wiki tooltip."""
        if self._tooltip_job:
            self.after_cancel(self._tooltip_job)
            self._tooltip_job = None
            
        if self._tooltip_popup:
            try:
                self._tooltip_popup.destroy()
            except tk.TclError:
                pass
            self._tooltip_popup = None

    def invalidate_wiki_cache(self):
        """Public method to invalidate wiki cache."""
        self._wiki_cache_dirty = True

    def _load_focus_config(self):
        """Load focus mode configuration from config manager."""
        if self.config_manager:
            config = self.config_manager.get_focus_mode_config()
            self._focus_level = config.get("level", self.FOCUS_LINE)
            self._focus_context_lines = config.get("context_lines", 3)
            self._focus_gradient = config.get("gradient", True)
            self._focus_highlight_current = config.get("highlight_current", True)
            self._focus_with_typewriter = config.get("with_typewriter", True)

    def save_focus_config(self):
        """Save current focus mode settings to config."""
        if self.config_manager:
            self.config_manager.set_focus_mode_config({
                "enabled": self.focus_mode,
                "level": self._focus_level,
                "context_lines": self._focus_context_lines,
                "gradient": self._focus_gradient,
                "highlight_current": self._focus_highlight_current,
                "with_typewriter": self._focus_with_typewriter
            })
            self.config_manager.save()

    def toggle_typewriter_mode(self, enabled):
        self.typewriter_mode = enabled
        if enabled:
            self.yview_pickplace("insert")

        # 发布事件
        bus = get_event_bus()
        bus.publish(Events.TYPEWRITER_MODE_CHANGED, enabled=enabled)

    def toggle_focus_mode(self, enabled, save_config=True):
        """Toggle focus mode on/off with full feature support."""
        was_enabled = self.focus_mode
        self.focus_mode = enabled

        if enabled:
            # Auto-enable typewriter mode if configured
            if self._focus_with_typewriter and not self.typewriter_mode:
                self.toggle_typewriter_mode(True)
            self._apply_focus_effect()
            # 记录专注会话开始时间
            if not was_enabled:
                import time
                self._focus_session_start = time.time()
        else:
            self._clear_focus_effect()
            # 记录专注会话结束并发布统计
            if was_enabled and hasattr(self, '_focus_session_start'):
                import time
                duration = time.time() - self._focus_session_start
                bus = get_event_bus()
                bus.publish(Events.FOCUS_SESSION_ENDED,
                            duration=duration,
                            level=self._focus_level)
                del self._focus_session_start

        # 发布专注模式变化事件
        bus = get_event_bus()
        bus.publish(Events.FOCUS_MODE_CHANGED,
                    enabled=enabled,
                    level=self._focus_level,
                    settings=self.get_focus_settings())

        # 发布会话开始事件
        if enabled and not was_enabled:
            bus.publish(Events.FOCUS_SESSION_STARTED, level=self._focus_level)

        # Notify listeners
        if self.on_focus_mode_change:
            self.on_focus_mode_change(enabled)

        # Save config if requested
        if save_config and self.config_manager:
            self.config_manager.set("focus_mode_enabled", enabled)
            self.config_manager.save()

    def set_focus_level(self, level):
        """Set focus granularity level: line, sentence, paragraph, or dialogue."""
        if level in (self.FOCUS_LINE, self.FOCUS_SENTENCE, self.FOCUS_PARAGRAPH, self.FOCUS_DIALOGUE):
            old_level = self._focus_level
            self._focus_level = level
            if self.focus_mode:
                self._apply_focus_effect()
            self.save_focus_config()

            # 发布专注级别变化事件
            if old_level != level:
                bus = get_event_bus()
                bus.publish(Events.FOCUS_LEVEL_CHANGED,
                            old_level=old_level,
                            new_level=level)

    @property
    def focus_level(self):
        """Get current focus level."""
        return self._focus_level

    def set_focus_context_lines(self, lines):
        """Set number of context lines to show around focus area."""
        self._focus_context_lines = max(0, min(10, lines))
        if self.focus_mode:
            self._apply_focus_effect()
        self.save_focus_config()

    def set_focus_gradient(self, enabled):
        """Enable/disable gradient dimming effect."""
        self._focus_gradient = enabled
        if self.focus_mode:
            self._apply_focus_effect()
        self.save_focus_config()

    def set_focus_highlight_current(self, enabled):
        """Enable/disable current line/area highlighting."""
        self._focus_highlight_current = enabled
        if self.focus_mode:
            self._apply_focus_effect()
        self.save_focus_config()

    def get_focus_settings(self):
        """Get current focus mode settings."""
        return {
            "enabled": self.focus_mode,
            "level": self._focus_level,
            "context_lines": self._focus_context_lines,
            "gradient": self._focus_gradient,
            "highlight_current": self._focus_highlight_current,
            "with_typewriter": self._focus_with_typewriter
        }

    def on_click_cursor_move(self, event):
        self._hide_autocomplete()
        if self.typewriter_mode:
            self.after_idle(lambda: self.yview_pickplace("insert"))
        if self.focus_mode:
            self._schedule_focus_update()

    def _on_focus_out(self, event):
        self._hide_autocomplete()

    def _setup_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self._ai_mode_enabled = True # Default to enabled

    def set_ai_mode_enabled(self, enabled: bool):
        self._ai_mode_enabled = bool(enabled)

    def _show_context_menu(self, event):
        self.focus_set()
        self._hide_autocomplete()

        # Dynamically rebuild the menu to hide invalid items in non-AI mode
        self.context_menu.delete(0, tk.END)
        self.context_menu.add_command(label="剪切", command=lambda: self.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="复制", command=lambda: self.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="粘贴", command=lambda: self.event_generate("<<Paste>>"))
        self.context_menu.add_separator()

        if self._ai_mode_enabled:
            self.context_menu.add_command(label="AI 续写 (根据光标前内容)", command=self._trigger_ai_continue)
            
            rewrite_menu = tk.Menu(self.context_menu, tearoff=0)
            styles = [("更幽默", "humorous"), ("更严肃/黑暗", "dark"), ("更简洁", "concise"), ("更丰富/细节", "detailed"), ("更口语化", "casual")]
            for label, style in styles:
                rewrite_menu.add_command(label=label, command=lambda s=style: self._trigger_ai_rewrite(s))
            self.context_menu.add_cascade(label="AI 重写选中内容...", menu=rewrite_menu)
            self.context_menu.add_separator()

        self.context_menu.add_command(label="添加到角色列表", command=self._add_to_characters)
        self.context_menu.add_command(label="添加到世界观百科", command=self._add_to_wiki)

        # Check selection for smart actions
        try:
            sel_start = self.index("sel.first")
            sel_end = self.index("sel.last")
            self.context_menu_target_text = self.get(sel_start, sel_end).strip()
        except tk.TclError:
            self.context_menu_target_text = ""

        self.context_menu.post(event.x_root, event.y_root)

    def _trigger_ai_continue(self):
        if self.on_ai_continue:
            # Get context: Up to 1000 chars before cursor
            context = self.get("insert - 1000 chars", "insert")
            self.on_ai_continue(context)

    def _trigger_ai_rewrite(self, style):
        if not self.on_ai_rewrite: return
        try:
            sel_text = self.get("sel.first", "sel.last")
            if not sel_text.strip(): return
            
            # Replace selection with placeholder
            self.delete("sel.first", "sel.last")
            insert_idx = self.index("insert")
            self.insert(insert_idx, "[AI正在重写...]")
            
            def callback(new_text):
                # Find placeholder and replace
                search_res = self.search("[AI正在重写...]", "1.0", tk.END)
                if search_res:
                    end_res = f"{search_res} + {len('[AI正在重写...]')} chars"
                    self.delete(search_res, end_res)
                    self.insert(search_res, new_text)
            
            self.on_ai_rewrite(sel_text, style, callback)
            
        except tk.TclError:
            pass # No selection

    def _add_to_characters(self):
        """Add selected text as a new character."""
        name = self.context_menu_target_text
        if not name:
            return

        if not self.project_manager:
            return

        # Check if exists
        chars = self.project_manager.get_characters()
        if any(c["name"] == name for c in chars):
            tk.messagebox.showinfo("提示", f"角色 '{name}' 已存在")
            return

        # Use command executor if available for undo support
        if self.command_executor:
            from writer_app.core.commands import AddCharacterCommand
            cmd = AddCharacterCommand(
                self.project_manager,
                {"name": name, "description": "从剧本提取", "tags": []},
                f"添加角色: {name}"
            )
            self.command_executor(cmd)
            tk.messagebox.showinfo("成功", f"已添加角色: {name}")
        else:
            # Fallback: direct modification (no undo support)
            chars.append({"name": name, "description": "从剧本提取", "tags": []})
            self.project_manager.mark_modified()
            tk.messagebox.showinfo("成功", f"已添加角色: {name} (无撤销支持)")

    def _add_to_wiki(self):
        """Add selected text as a new wiki entry."""
        name = self.context_menu_target_text
        if not name:
            return

        if not self.project_manager:
            return

        # Check if exists
        entries = self.project_manager.get_world_entries()
        if any(e["name"] == name for e in entries):
            tk.messagebox.showinfo("提示", f"词条 '{name}' 已存在")
            return

        # Use command executor if available
        if self.command_executor:
            from writer_app.core.commands import AddWikiEntryCommand
            cmd = AddWikiEntryCommand(
                self.project_manager,
                {"name": name, "category": "其他", "content": ""},
                f"添加词条: {name}"
            )
            self.command_executor(cmd)
            self._wiki_cache_dirty = True
            tk.messagebox.showinfo("成功", f"已添加词条: {name}")
        else:
            entries.append({"name": name, "category": "其他", "content": ""})
            self.project_manager.mark_modified()
            self._wiki_cache_dirty = True
            tk.messagebox.showinfo("成功", f"已添加词条: {name} (无撤销支持)")

    def _configure_tags(self):
        # Default styles (Light)
        self.tag_config("scene_header", background="#E3F2FD", font=("Microsoft YaHei", 11, "bold"))
        self.tag_config("character_name", foreground="#1565C0", font=("Microsoft YaHei", 11, "bold"))
        self.tag_config("parenthetical", foreground="#757575", font=("Microsoft YaHei", 10, "italic"))
        self.tag_config("transition", foreground="#E65100", justify="right", font=("Microsoft YaHei", 10, "bold"))
        self.tag_config("dimmed", foreground="#AAAAAA")
        self.tag_config("wiki_term", underline=True, foreground="#009688")
        self.tag_config("wiki_deep", underline=True, foreground="#9C27B0", background="#F3E5F5") # Purple for deep/secret
        self.tag_bind("wiki_term", "<Button-1>", self._on_wiki_term_click)
        self.tag_bind("wiki_term", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("wiki_term", "<Leave>", lambda e: self.config(cursor=""))
        self.tag_config("search_highlight", background="yellow", foreground="black")

        # Focus mode tags (Light theme default)
        self._configure_focus_tags("Light")

    def _configure_focus_tags(self, theme_name):
        """Configure focus mode tag colors based on theme."""
        self._current_theme = theme_name

        # Get colors from config if available
        if self.config_manager:
            config = self.config_manager.get_focus_mode_config()
            if theme_name == "Dark":
                highlight_bg = config.get("highlight_color_dark", "#37474F")
                dim_color = config.get("dim_color_dark", "#555555")
            else:
                highlight_bg = config.get("highlight_color_light", "#FFFDE7")
                dim_color = config.get("dim_color_light", "#CCCCCC")
        else:
            if theme_name == "Dark":
                highlight_bg = "#37474F"
                dim_color = "#555555"
            else:
                highlight_bg = "#FFFDE7"
                dim_color = "#CCCCCC"

        # Current focus area highlight
        self.tag_config("focus_current", background=highlight_bg)

        # Full dim color (most distant)
        self.tag_config("focus_dim", foreground=dim_color)

        # Gradient dim levels (1 = closest to focus, 5 = furthest)
        if theme_name == "Dark":
            gradient_colors = ["#9E9E9E", "#7A7A7A", "#666666", "#5A5A5A", "#555555"]
        else:
            gradient_colors = ["#666666", "#888888", "#AAAAAA", "#BBBBBB", "#CCCCCC"]

        for i, color in enumerate(gradient_colors, 1):
            self.tag_config(f"focus_dim_{i}", foreground=color)

        # Ensure focus tags have higher priority than other tags
        self.tag_raise("focus_current")
        self.tag_raise("focus_dim")
        for i in range(1, 6):
            self.tag_raise(f"focus_dim_{i}")

    def _on_wiki_term_click(self, event):
        """Handle click on a wiki term."""
        if not self.on_wiki_click:
            return
            
        # Find which term was clicked
        idx = self.index(f"@{event.x},{event.y}")
        tags = self.tag_names(idx)
        if "wiki_term" in tags:
            # Get the full word range
            start, end = self.tag_prevrange("wiki_term", idx + " + 1 chars")
            if start and end:
                term = self.get(start, end)
                self.on_wiki_click(term)
                return "break" # Prevent cursor movement if desired

    def apply_theme(self, theme_manager):
        theme_name = theme_manager.current_theme
        bg = theme_manager.get_color("editor_bg")
        fg = theme_manager.get_color("editor_fg")
        select_bg = theme_manager.get_color("editor_select_bg")
        select_fg = theme_manager.get_color("editor_select_fg")

        self.configure(bg=bg, fg=fg, insertbackground=fg, selectbackground=select_bg, selectforeground=select_fg)

        # Use centralized theme keys
        self.tag_config("scene_header", 
                       background=theme_manager.get_color("editor_scene_header_bg"),
                       foreground=theme_manager.get_color("editor_scene_header_fg"))
        
        self.tag_config("character_name", foreground=theme_manager.get_color("editor_char_name_fg"))
        self.tag_config("parenthetical", foreground=theme_manager.get_color("editor_paren_fg"))
        self.tag_config("transition", foreground=theme_manager.get_color("editor_trans_fg"))
        self.tag_config("dimmed", foreground=theme_manager.get_color("editor_dimmed_fg"))
        
        self.tag_config("wiki_term", underline=True, foreground=theme_manager.get_color("editor_wiki_fg"))
        self.tag_config("wiki_deep", underline=True, 
                       foreground=theme_manager.get_color("editor_wiki_deep_fg"),
                       background=theme_manager.get_color("editor_wiki_deep_bg"))

        # Update focus mode tags for theme
        self._configure_focus_tags(theme_name)

        # Reapply focus effect if active
        if self.focus_mode:
            self._apply_focus_effect()

    # --- Autocomplete ---

    def _get_character_names(self):
        """Get list of character names for autocomplete."""
        if self.project_manager:
            return [c["name"] for c in self.project_manager.get_characters() if c.get("name")]
        return []

    def on_key_press(self, event):
        """Handle key press for autocomplete navigation and smart quotes."""
        if self.autocomplete_popup and self.autocomplete_popup.winfo_exists():
            if event.keysym == "Down":
                self._autocomplete_move(1)
                return "break"
            elif event.keysym == "Up":
                self._autocomplete_move(-1)
                return "break"
            elif event.keysym in ("Return", "Tab"):
                self._autocomplete_select()
                return "break"
            elif event.keysym == "Escape":
                self._hide_autocomplete()
                return "break"
        
        # Smart Quotes
        if event.char in ['"', "'"]:
            return self._insert_smart_quote(event.char)

    def _insert_smart_quote(self, char):
        """Insert curly quotes based on context."""
        # Get character before cursor
        try:
            prev_char = self.get("insert - 1 chars", "insert")
        except tk.TclError:
            prev_char = ""
        
        to_insert = char
        if char == '"':
            # Open quote if start of line or preceded by space/bracket
            if not prev_char or prev_char in " \n\t([{（【":
                to_insert = "“"
            else:
                to_insert = "”"
        elif char == "'":
            if not prev_char or prev_char in " \n\t([{（【":
                to_insert = "‘"
            else:
                to_insert = "’"
        
        self.insert("insert", to_insert)
        return "break"

    def on_key_release(self, event=None):
        # Check for autocomplete trigger
        if event and event.char in self._autocomplete_trigger_chars:
            self._show_autocomplete()
        elif event and event.keysym in ("BackSpace", "Delete"):
            self._hide_autocomplete()
        elif event and event.char.isalnum():
            # Update autocomplete filter if popup is visible
            if self.autocomplete_popup and self.autocomplete_popup.winfo_exists():
                self._update_autocomplete_filter()

        # Debounced highlight
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(self._highlight_delay_ms, self._do_highlight)

        if self.on_content_change:
            self.on_content_change()

        self._schedule_content_change_event()

    def _schedule_content_change_event(self):
        if self._content_change_job:
            self.after_cancel(self._content_change_job)
        self._content_change_job = self.after(
            self._content_change_delay_ms,
            self._publish_content_change_event
        )

    def _publish_content_change_event(self):
        self._content_change_job = None
        try:
            content = self.get("1.0", "end-1c")
        except tk.TclError:
            return
        word_count = len(content.strip())
        snippet = content[-400:] if len(content) > 400 else content
        bus = get_event_bus()
        bus.publish(
            Events.EDITOR_CONTENT_CHANGED,
            word_count=word_count,
            text_snippet=snippet
        )

        if self.typewriter_mode:
            self.yview_pickplace("insert")
        if self.focus_mode:
            self._schedule_focus_update()

    def _do_highlight(self):
        """Perform actual highlighting (debounced)."""
        self._highlight_job = None
        self._highlight_visible()

    def _show_autocomplete(self):
        """Show autocomplete popup based on trigger character."""
        line = self.get("insert linestart", "insert")
        if not line: return
        
        trigger = line[-1]
        
        if trigger in (":", "："):
            candidates = self._get_character_names()
        elif trigger in ("[", "【"):
            candidates = self._get_wiki_terms()
        else:
            return

        if not candidates:
            return

        self.autocomplete_candidates = sorted(candidates)
        self.autocomplete_selected = 0

        # Get cursor position
        try:
            bbox = self.bbox("insert")
            if not bbox:
                return
            x, y, _, h = bbox
        except tk.TclError:
            return

        # Create popup
        self._hide_autocomplete()
        self.autocomplete_popup = tk.Toplevel(self)
        self.autocomplete_popup.wm_overrideredirect(True)
        self.autocomplete_popup.wm_attributes("-topmost", True)

        # Create listbox first to get dimensions
        list_height = min(6, len(self.autocomplete_candidates))
        self.autocomplete_listbox = tk.Listbox(
            self.autocomplete_popup,
            font=("Microsoft YaHei", 10),
            selectmode=tk.SINGLE,
            height=list_height,
            width=25,
            exportselection=False
        )
        self.autocomplete_listbox.pack()

        for cand in self.autocomplete_candidates:
            self.autocomplete_listbox.insert(tk.END, cand)

        self.autocomplete_listbox.selection_set(0)
        self.autocomplete_listbox.bind("<Double-1>", lambda e: self._autocomplete_select())

        # Update to get actual size
        self.autocomplete_popup.update_idletasks()
        popup_width = self.autocomplete_popup.winfo_reqwidth()
        popup_height = self.autocomplete_popup.winfo_reqheight()

        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate initial position
        root_x = self.winfo_rootx() + x
        root_y = self.winfo_rooty() + y + h

        # Boundary checking - horizontal
        if root_x + popup_width > screen_width:
            root_x = screen_width - popup_width - 10

        # Boundary checking - vertical
        # If popup would go below screen, show it above the cursor
        if root_y + popup_height > screen_height:
            root_y = self.winfo_rooty() + y - popup_height

        # Ensure not negative
        root_x = max(0, root_x)
        root_y = max(0, root_y)

        self.autocomplete_popup.geometry(f"+{root_x}+{root_y}")

    def _update_autocomplete_filter(self):
        """Filter autocomplete based on typed text."""
        if not self.autocomplete_popup or not self.autocomplete_popup.winfo_exists():
            return

        # Get text after the trigger character
        line = self.get("insert linestart", "insert")
        trigger_pos = max(line.rfind(":"), line.rfind("："), line.rfind("【"), line.rfind("["))
        if trigger_pos == -1:
            self._hide_autocomplete()
            return

        trigger = line[trigger_pos]
        filter_text = line[trigger_pos + 1:].strip().lower()

        if trigger in (":", "："):
            all_candidates = self._get_character_names()
        else:
            all_candidates = self._get_wiki_terms()
            
        filtered = [c for c in all_candidates if filter_text in c.lower()]

        if not filtered:
            self._hide_autocomplete()
            return

        self.autocomplete_candidates = sorted(filtered)
        self.autocomplete_listbox.delete(0, tk.END)
        for cand in self.autocomplete_candidates:
            self.autocomplete_listbox.insert(tk.END, cand)
        self.autocomplete_listbox.selection_set(0)
        self.autocomplete_selected = 0

    def _autocomplete_select(self):
        """Insert selected autocomplete item."""
        if not self.autocomplete_candidates:
            self._hide_autocomplete()
            return

        selected = self.autocomplete_candidates[self.autocomplete_selected]

        # Delete any partial text after trigger
        line = self.get("insert linestart", "insert")
        trigger_pos = max(line.rfind(":"), line.rfind("："), line.rfind("【"), line.rfind("["))
        if trigger_pos != -1:
            trigger = line[trigger_pos]
            # Calculate how many chars to delete
            partial_len = len(line) - trigger_pos - 1
            if partial_len > 0:
                self.delete(f"insert - {partial_len} chars", "insert")

        # Insert selected name
        self.insert("insert", selected)
        
        # If it was a bracket trigger, maybe add closing bracket
        line_after = self.get("insert linestart", "insert")
        if "[" in line_after or "【" in line_after:
            # Check if there is already a closing bracket
            after_cursor = self.get("insert", "insert + 1 chars")
            if after_cursor not in ("]", "】"):
                self.insert("insert", "]" if "[" in line_after else "】")
                
        self._hide_autocomplete()

    def _hide_autocomplete(self):
        """Hide autocomplete popup."""
        if self.autocomplete_popup:
            try:
                self.autocomplete_popup.destroy()
            except tk.TclError:
                pass
            self.autocomplete_popup = None

    # --- Focus Mode Effects ---

    def _schedule_focus_update(self):
        """Schedule a debounced focus effect update."""
        if self._focus_update_job:
            self.after_cancel(self._focus_update_job)
        self._focus_update_job = self.after(self._focus_update_delay_ms, self._apply_focus_effect)

    def _apply_focus_effect(self):
        """Apply focus mode visual effects based on current settings."""
        self._focus_update_job = None
        if not self.focus_mode:
            return

        # Clear previous focus effects
        self._clear_focus_tags()

        # Get focus range based on level
        focus_start, focus_end = self._get_focus_range()

        # Apply current line/area highlight
        if self._focus_highlight_current:
            self._apply_current_highlight(focus_start, focus_end)

        # Apply dimming with optional gradient
        if self._focus_gradient:
            self._apply_gradient_dim(focus_start, focus_end)
        else:
            self._apply_simple_dim(focus_start, focus_end)

    def _clear_focus_effect(self):
        """Clear all focus mode visual effects."""
        self._clear_focus_tags()

    def _clear_focus_tags(self):
        """Remove all focus-related tags."""
        tags_to_clear = [
            "focus_current", "focus_dim",
            "focus_dim_1", "focus_dim_2", "focus_dim_3",
            "focus_dim_4", "focus_dim_5"
        ]
        for tag in tags_to_clear:
            self.tag_remove(tag, "1.0", tk.END)

    def _get_focus_range(self):
        """Get the start and end indices of the current focus area based on level."""
        cursor_idx = self.index("insert")

        if self._focus_level == self.FOCUS_LINE:
            return self.index("insert linestart"), self.index("insert lineend + 1 chars")

        elif self._focus_level == self.FOCUS_SENTENCE:
            return self._get_sentence_range(cursor_idx)

        elif self._focus_level == self.FOCUS_PARAGRAPH:
            return self._get_paragraph_range(cursor_idx)

        elif self._focus_level == self.FOCUS_DIALOGUE:
            return self._get_dialogue_range(cursor_idx)

        return self.index("insert linestart"), self.index("insert lineend + 1 chars")

    def _get_sentence_range(self, cursor_idx):
        """Find the sentence containing the cursor."""
        # Get surrounding text
        line_start = self.index(f"{cursor_idx} linestart")
        line_end = self.index(f"{cursor_idx} lineend")
        line_text = self.get(line_start, line_end)

        # Find cursor position in line
        cursor_col = int(cursor_idx.split('.')[1])

        # Chinese and English sentence endings
        sentence_ends = ['。', '！', '？', '.', '!', '?', '；', ';']

        # Find sentence start (search backward)
        sent_start = 0
        for i in range(cursor_col - 1, -1, -1):
            if i < len(line_text) and line_text[i] in sentence_ends:
                sent_start = i + 1
                break

        # Find sentence end (search forward)
        sent_end = len(line_text)
        for i in range(cursor_col, len(line_text)):
            if line_text[i] in sentence_ends:
                sent_end = i + 1
                break

        start = f"{line_start} + {sent_start} chars"
        end = f"{line_start} + {sent_end} chars"
        return self.index(start), self.index(end)

    def _get_paragraph_range(self, cursor_idx):
        """Find the paragraph containing the cursor (text between blank lines)."""
        # Search backward for paragraph start
        current_line = int(cursor_idx.split('.')[0])
        para_start_line = current_line

        for line_num in range(current_line - 1, 0, -1):
            line_text = self.get(f"{line_num}.0", f"{line_num}.end")
            if not line_text.strip():
                para_start_line = line_num + 1
                break
            para_start_line = line_num

        # Search forward for paragraph end
        total_lines = int(self.index("end").split('.')[0])
        para_end_line = current_line

        for line_num in range(current_line + 1, total_lines + 1):
            line_text = self.get(f"{line_num}.0", f"{line_num}.end")
            if not line_text.strip():
                para_end_line = line_num - 1
                break
            para_end_line = line_num

        return self.index(f"{para_start_line}.0"), self.index(f"{para_end_line}.end + 1 chars")

    def _get_dialogue_range(self, cursor_idx):
        """Find the dialogue block (character name + dialogue) containing the cursor."""
        current_line = int(cursor_idx.split('.')[0])
        line_text = self.get(f"{current_line}.0", f"{current_line}.end")

        # Check if current line has dialogue marker
        has_dialogue_marker = "：" in line_text or ":" in line_text

        # Search backward for dialogue start
        dialogue_start_line = current_line
        for line_num in range(current_line, 0, -1):
            text = self.get(f"{line_num}.0", f"{line_num}.end")
            if "：" in text or ":" in text:
                dialogue_start_line = line_num
                break
            if not text.strip():
                dialogue_start_line = line_num + 1
                break

        # Search forward for dialogue end (next dialogue or blank line)
        total_lines = int(self.index("end").split('.')[0])
        dialogue_end_line = current_line

        found_start = False
        for line_num in range(dialogue_start_line, total_lines + 1):
            text = self.get(f"{line_num}.0", f"{line_num}.end")
            if ("：" in text or ":" in text) and found_start:
                dialogue_end_line = line_num - 1
                break
            if "：" in text or ":" in text:
                found_start = True
            if not text.strip() and found_start:
                dialogue_end_line = line_num - 1
                break
            dialogue_end_line = line_num

        return self.index(f"{dialogue_start_line}.0"), self.index(f"{dialogue_end_line}.end + 1 chars")

    def _apply_current_highlight(self, focus_start, focus_end):
        """Apply background highlight to the current focus area."""
        self.tag_add("focus_current", focus_start, focus_end)

    def _apply_simple_dim(self, focus_start, focus_end):
        """Apply simple (non-gradient) dimming to non-focus areas."""
        # Dim everything before focus
        if self.compare(focus_start, ">", "1.0"):
            self.tag_add("focus_dim", "1.0", focus_start)

        # Dim everything after focus
        if self.compare(focus_end, "<", "end"):
            self.tag_add("focus_dim", focus_end, "end")

    def _apply_gradient_dim(self, focus_start, focus_end):
        """Apply gradient dimming effect with context lines."""
        context = self._focus_context_lines
        focus_start_line = int(focus_start.split('.')[0])
        focus_end_line = int(focus_end.split('.')[0])
        total_lines = int(self.index("end").split('.')[0])

        # Apply gradient before focus area
        for i in range(1, context + 1):
            grad_line = focus_start_line - i
            if grad_line >= 1:
                dim_level = min(i, 5)  # Max 5 gradient levels
                self.tag_add(f"focus_dim_{dim_level}", f"{grad_line}.0", f"{grad_line}.end + 1 chars")

        # Fully dim everything before gradient area
        first_grad_line = max(1, focus_start_line - context)
        if first_grad_line > 1:
            self.tag_add("focus_dim", "1.0", f"{first_grad_line}.0")

        # Apply gradient after focus area
        for i in range(1, context + 1):
            grad_line = focus_end_line + i
            if grad_line <= total_lines:
                dim_level = min(i, 5)
                self.tag_add(f"focus_dim_{dim_level}", f"{grad_line}.0", f"{grad_line}.end + 1 chars")

        # Fully dim everything after gradient area
        last_grad_line = min(total_lines, focus_end_line + context)
        if last_grad_line < total_lines:
            self.tag_add("focus_dim", f"{last_grad_line + 1}.0", "end")

    # --- Highlighting ---

    def get_word_count(self):
        text = self.get("1.0", tk.END)
        clean = re.sub(r'\s+', '', text)
        return len(clean)

    def highlight_all(self):
        self._highlight_range("1.0", tk.END)

    def _highlight_visible(self):
        """Highlight only visible area for better performance."""
        try:
            # Get visible range
            first_visible = self.index("@0,0")
            last_visible = self.index(f"@0,{self.winfo_height()}")
            # Add some buffer lines
            first_line = max(1, int(first_visible.split(".")[0]) - 5)
            last_line = int(last_visible.split(".")[0]) + 5
            self._highlight_range(f"{first_line}.0", f"{last_line}.end")
        except (tk.TclError, ValueError, IndexError):
            self.highlight_all()

    def _highlight_range(self, start, end):
        # Remove existing tags
        for tag in ["scene_header", "character_name", "parenthetical", "transition", "wiki_term"]:
            self.tag_remove(tag, start, end)

        text = self.get(start, end)
        if not text:
            return

        current_idx = self.index(start)
        end_idx = self.index(end)

        # Get cached wiki terms
        wiki_data = self._get_wiki_terms()

        while self.compare(current_idx, "<", end_idx):
            line_end = self.index(f"{current_idx} lineend")
            line_text = self.get(current_idx, line_end)
            stripped = line_text.strip()

            if stripped:
                # Scene Header
                if stripped.startswith("###") or stripped.startswith("【场景】") or \
                   stripped.startswith("INT.") or stripped.startswith("EXT."):
                    self.tag_add("scene_header", current_idx, line_end)

                # Transition
                elif stripped.startswith("——") or stripped.endswith("TO:"):
                    self.tag_add("transition", current_idx, line_end)

                # Parenthetical
                elif (stripped.startswith("(") and stripped.endswith(")")) or \
                     (stripped.startswith("（") and stripped.endswith("）")):
                    self.tag_add("parenthetical", current_idx, line_end)

                # Character Name (Name: Dialogue)
                elif "：" in stripped or ":" in stripped:
                    sep = "：" if "：" in stripped else ":"
                    parts = stripped.split(sep, 1)
                    name_candidate = parts[0].strip()

                    if len(name_candidate) < 20 and not name_candidate.startswith("###"):
                        sep_idx = line_text.find(sep)
                        if sep_idx != -1:
                            tag_end = f"{current_idx} + {sep_idx + 1} chars"
                            self.tag_add("character_name", current_idx, tag_end)

                # Wiki Terms - optimized with early exit
                if wiki_data:
                    line_lower = line_text.lower()
                    for item in wiki_data:
                        term = item["term"]
                        depth = item.get("depth", "surface")
                        term_lower = term.lower()
                        
                        if term_lower not in line_lower:
                            continue
                            
                        start_match = 0
                        while True:
                            idx = line_text.lower().find(term_lower, start_match)
                            if idx == -1:
                                break
                            term_start = f"{current_idx} + {idx} chars"
                            term_end = f"{current_idx} + {idx + len(term)} chars"
                            
                            # Apply generic wiki tag
                            self.tag_add("wiki_term", term_start, term_end)
                            
                            # Apply specific depth tag if deep
                            if depth == "deep":
                                self.tag_add("wiki_deep", term_start, term_end)
                                
                            start_match = idx + len(term)

            current_idx = self.index(f"{current_idx} + 1 lines linestart")
