import json
import os
import random
import logging
from tkinter import filedialog
from writer_app.core.commands import (
    AddSceneCommand, EditSceneCommand, AddNodeCommand,
    AddCharacterCommand, AddWikiEntryCommand,
    EditSceneContentCommand, EditCharacterCommand,
    AddTimelineEventCommand, AddLinkCommand,
    AddEvidenceNodeCommand, AddEvidenceLinkCommand
)
from writer_app.core.analysis import AnalysisUtils
from writer_app.core.ai_tools import AIToolRegistry, ToolResult
from writer_app.core.thread_pool import get_ai_thread_pool
from writer_app.core.exceptions import AIConfigError
from writer_app.core.ai_prompts import get_genre_config, build_project_context, GenrePromptConfig

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

class AIController:
    """
    AI控制器 - 管理所有AI相关的异步操作。

    使用线程池来限制并发任务数量，提供任务取消和错误处理机制。
    """

    def __init__(self, main_app):
        self.app = main_app
        self.project_manager = main_app.project_manager
        self.ai_client = main_app.ai_client
        self.root = main_app.root

        # 获取线程池
        self.pool = get_ai_thread_pool()

        # 确保AI工具已加载
        AIToolRegistry._ensure_initialized()

        # 题材配置缓存
        self._genre_config: GenrePromptConfig = None
        self._update_genre_config()

    def get_api_config(self):
        url = self.app.lm_api_url.get().strip()
        model = self.app.lm_api_model.get().strip()
        key = self.app.lm_api_key.get().strip()
        return url, model, key

    # --- Genre-Aware Configuration ---

    def _update_genre_config(self):
        """Update the genre configuration based on current project type."""
        project_type = self._get_project_type()
        self._genre_config = get_genre_config(project_type)
        logger.debug(f"Updated genre config to: {project_type}")

    def _get_project_type(self) -> str:
        """Get the current project type."""
        if self.project_manager:
            meta = self.project_manager.get_project_data().get("meta", {})
            return meta.get("type", "General")
        return "General"

    def get_genre_config(self) -> GenrePromptConfig:
        """Get the current genre configuration."""
        if self._genre_config is None:
            self._update_genre_config()
        return self._genre_config

    def _get_genre_aware_system_prompt(self, base_prompt: str) -> str:
        """
        Build a genre-aware system prompt.

        Combines the base prompt with genre-specific context and guidelines.
        """
        config = self.get_genre_config()
        context = build_project_context(self.project_manager)
        merged_prompt = base_prompt or ""
        if context:
            merged_prompt = f"{merged_prompt}\n\n{context}".strip()
        return config.get_full_system_prompt(merged_prompt)

    def get_genre_specialized_tools(self) -> list:
        """Get the list of specialized tools for the current genre."""
        config = self.get_genre_config()
        return config.specialized_tools

    def get_genre_analysis_dimensions(self) -> list:
        """Get the analysis dimensions for the current genre."""
        config = self.get_genre_config()
        return config.analysis_dimensions

    def get_genre_diagnostic_focus(self) -> list:
        """Get the diagnostic focus areas for the current genre."""
        config = self.get_genre_config()
        return config.diagnostic_focus

    def on_project_loaded(self):
        """Called when a project is loaded. Updates genre configuration."""
        self._update_genre_config()

    def on_project_config_changed(self):
        """Called when project config changes (type/tags/modules)."""
        self._update_genre_config()

    def _ensure_ai_enabled(self) -> bool:
        if hasattr(self.app, "is_ai_mode_enabled") and not self.app.is_ai_mode_enabled():
            self.app.messagebox.showinfo("提示", "当前为非AI模式，已禁用AI功能。")
            return False
        return True

    def _is_ai_mode_active(self) -> bool:
        if hasattr(self.app, "is_ai_mode_enabled"):
            return bool(self.app.is_ai_mode_enabled())
        return True

    def _run_if_ai_enabled(self, callback):
        if self._is_ai_mode_active():
            callback()

    # --- Agentic Chat Handler ---

    def handle_chat_response(self, response_text, callback):
        """
        Parses the AI response for tool calls (JSON).
        If found, executes the corresponding command via AIToolRegistry.
        Always calls callback with the text to display.
        """
        try:
            if not self._is_ai_mode_active():
                self.root.after(0, lambda: callback(response_text + "\n\n[系统] AI模式已关闭，结果已忽略。"))
                return

            data = self.ai_client.extract_json_from_text(response_text)
            if not data or "tool" not in data:
                # No tool call found, just display text
                self.root.after(0, lambda: callback(response_text))
                return

            tool = data.get("tool")
            params = data.get("params", {})

            # 使用AI工具注册表执行工具
            result = AIToolRegistry.execute(
                tool,
                self.project_manager,
                self.app._execute_command,
                params
            )

            # 处理特殊工具的副作用（如UI导航、计时器）
            if result.success and result.data:
                self._handle_tool_side_effects(tool, result.data)

            # Append status to response
            final_text = response_text
            if result.success:
                final_text += f"\n\n[系统] {result.message}"
            else:
                final_text += f"\n\n[系统] 操作失败或部分忽略: {result.message}"

            self.root.after(0, lambda: callback(final_text))

        except Exception as e:
            print(f"Agent execution error: {e}")
            self.root.after(0, lambda: callback(response_text + f"\n\n[系统] 执行出错: {str(e)}"))

    def _handle_tool_side_effects(self, tool: str, data: dict) -> None:
        """处理工具执行的副作用（如UI导航、计时器等）。"""
        if tool == "navigate_to" and "tab_key" in data:
            self.root.after(0, lambda: self._navigate_ui(data.get("original_target", "outline")))

        elif tool == "start_timer" and "duration" in data:
            duration = data.get("duration", 25)
            self.root.after(0, lambda: self._start_pomodoro(duration))

        elif tool == "stop_timer":
            self.root.after(0, lambda: self._stop_pomodoro())

    def _generate_placeholder_image(self, path, text, color, size):
        try:
            img = Image.new('RGB', size, color=color)
            d = ImageDraw.Draw(img)
            # Draw border
            d.rectangle([0, 0, size[0]-1, size[1]-1], outline=(255, 255, 255), width=5)
            # Draw text (centered rough calculation)
            d.text((size[0]/2, size[1]/2), text, fill=(255, 255, 255), anchor="mm", font_size=40)
            img.save(path)
        except Exception as e:
            print(f"Image gen failed: {e}")

    # --- Extended Tool Helpers ---

    def _start_pomodoro(self, duration):
        if hasattr(self.app, "pomodoro_controller"):
            # Set custom time? The controller uses config.
            # We can temporarily override or just start current mode.
            # Assuming standard 'work' mode for now.
            self.app.pomodoro_controller.set_mode("work")
            self.app.pomodoro_controller.start()

    def _stop_pomodoro(self):
        if hasattr(self.app, "pomodoro_controller"):
            self.app.pomodoro_controller.pause()

    def _get_project_stats_summary(self):
        script = self.project_manager.get_script()
        scenes = script.get("scenes", [])
        chars = script.get("characters", [])
        total_words = sum(len(s.get("content", "")) for s in scenes)
        
        return (f"- 总字数: {total_words}\n"
                f"- 场景数: {len(scenes)}\n"
                f"- 角色数: {len(chars)}")

    def _navigate_ui(self, target):
        # target: outline, script, timeline, kanban, etc.
        tabs = getattr(self.app, "tabs", {})
        target_map = {
            "大纲": "outline", "outline": "outline",
            "剧本": "script", "script": "script",
            "人物": "relationship", "relationship": "relationship",
            "关系": "relationship",
            "线索": "evidence_board", "evidence": "evidence_board",
            "时间轴": "timeline", "timeline": "timeline",
            "统计": "analytics", "analytics": "analytics",
            "看板": "kanban", "kanban": "kanban",
            "日历": "calendar", "calendar": "calendar",
            "百科": "wiki", "wiki": "wiki"
        }
        
        key = target_map.get(target.lower(), target)
        if key in tabs:
            self.app.notebook.select(tabs[key])

    def _find_evidence_uid_by_name(self, name):
        # Search existing nodes in relationship/evidence data
        rels = self.project_manager.get_relationships()
        
        # Check custom nodes
        for node in rels.get("nodes", []):
            if node.get("name") == name:
                return node.get("uid")
                
        # Check characters
        for char in self.project_manager.get_characters():
            if char.get("name") == name:
                return char.get("uid") or char.get("name") # Fallback to name if UID missing
                
        return None

    # --- Outline Generation ---

    def generate_outline(self, script_text):
        """使用AI从剧本文本生成大纲。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        self.app._set_ai_generation_state(True, "生成思维导图...")

        def task():
            sys_p = self.app.config_manager.get("prompt_generate_outline", "你是剧本助手，将剧本转为层级思维导图JSON(name, content, children)。要求按幕/章节组织，每个章节作为父节点，章节下的场景/事件作为子节点。")
            user_p = f"剧本:\n{script_text}"
            res = self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, user_p)
            data = self.ai_client.extract_json_from_text(res)
            if not data:
                raise ValueError("无效JSON")
            norm = self.app._normalize_outline_node(data, "AI生成")
            if not norm:
                raise ValueError("结构错误")
            return norm

        self.pool.submit(
            task_id="outline_generation",
            fn=task,
            on_success=lambda result: self.root.after(0, lambda: self.app._apply_ai_outline(result)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("错误", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app._set_ai_generation_state(False, "就绪")),
            tk_root=self.root
        )

    # --- Diagnosis ---

    def diagnose_outline(self, outline_text):
        """诊断大纲的结构和逻辑（题材感知版）。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        self.app._set_ai_generation_state(True, "诊断中...")

        def task():
            # 获取题材专属诊断维度
            config = self.get_genre_config()
            focus_areas = config.diagnostic_focus

            base_prompt = self.app.config_manager.get(
                "prompt_diagnose_outline",
                "你是剧本顾问，请诊断大纲的结构、逻辑、角色、节奏，输出Markdown报告。"
            )

            # 构建题材感知的系统提示
            if focus_areas:
                focus_str = "、".join(focus_areas)
                enhanced_prompt = f"{base_prompt}\n\n针对当前题材，请特别关注：{focus_str}"
            else:
                enhanced_prompt = base_prompt

            sys_p = self._get_genre_aware_system_prompt(enhanced_prompt)
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, outline_text)

        def on_success(res):
            from writer_app.ui.dialogs import DiagnosisResultDialog
            if not self._is_ai_mode_active():
                return
            DiagnosisResultDialog(self.root, res)

        self.pool.submit(
            task_id="diagnose_outline",
            fn=task,
            on_success=lambda res: self.root.after(0, lambda: on_success(res)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("错误", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app._set_ai_generation_state(False, "就绪")),
            tk_root=self.root
        )

    # --- Outline Helper (Node Completion) ---

    def start_outline_helper(self, mode, node, outline_text, hint, opts=None):
        """使用AI补全大纲节点。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        self.app._set_outline_helper_state(True, "AI运行中...")
        target_node = node  # 保存引用

        def task():
            if mode == "complete_all":
                sys_p = self.app.config_manager.get("prompt_generate_outline", "你是剧本助手，补全大纲JSON(name,content,children)，不改变结构。")
                user_p = f"补全大纲:\n{outline_text}\n提示:{hint}"
                res = self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, user_p)
                data = self.ai_client.extract_json_from_text(res)
                if not data:
                    raise ValueError("无效JSON")
                norm = self.app._normalize_outline_node(data, "项目大纲")
                if not norm:
                    raise ValueError("结构错误")
                return ("complete_all", norm)
            else:
                node_copy = json.loads(json.dumps(target_node))
                sys_p = self.app.config_manager.get("prompt_generate_outline", "你是剧本助手，补全节点JSON(name,content,children)。")
                user_p = f"补全节点:\n{json.dumps(node_copy, ensure_ascii=False)}\n大纲背景:{outline_text}\n提示:{hint}\nMode:{mode}"
                if opts:
                    user_p += f"\nOpts:{opts}"
                res = self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, user_p)
                data = self.ai_client.extract_json_from_text(res)
                if not data:
                    raise ValueError("无效JSON")
                norm = self.app._normalize_outline_node(data, node_copy.get("name"))
                if not norm:
                    raise ValueError("结构错误")
                return ("node", norm)

        def on_success(result):
            result_type, norm = result
            if result_type == "complete_all":
                self.app._apply_ai_outline(norm)
            else:
                self.app._apply_ai_node_result(target_node, norm, mode)

        self.pool.submit(
            task_id="outline_helper",
            fn=task,
            on_success=lambda res: self.root.after(0, lambda: on_success(res)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("错误", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app._set_outline_helper_state(False)),
            tk_root=self.root
        )

    # --- Scene Generation ---

    def generate_scene_from_node(self, node, outline_path):
        """从大纲节点生成场景。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请先在左侧配置AI接口URL和模型名称")
            return

        name = node.get("name", "未命名")
        content = node.get("content", "")
        outline_uid = node.get("uid", "")

        self.app._set_script_ai_state(True, f"正在为节点 '{name}' 生成场景...")

        def task():
            sys_p = self.app.config_manager.get("prompt_continue_script", "你是专业的编剧助手。请根据提供的场景标题和梗概，撰写一段标准的剧本场景内容（包含场景标题、动作描述、角色对话）。")
            user_p = f"场景标题：{name}\n场景梗概/上下文：{content}\n\n请直接输出剧本内容，不要包含额外的解释。"
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, user_p)

        self.pool.submit(
            task_id="scene_from_node",
            fn=task,
            on_success=lambda res: self.root.after(0, lambda: self.app._add_generated_scene(name, res, outline_uid, outline_path)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("生成失败", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app._set_script_ai_state(False, "就绪")),
            tk_root=self.root
        )

    # --- Script Generation ---

    def generate_script_from_outline(self, outline_text):
        """从大纲生成完整剧本。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        self.app._set_script_ai_state(True, "生成剧本...")

        def task():
            sys_p = self.app.config_manager.get("prompt_continue_script", "你是编剧，将大纲转为剧本JSON(title,characters,scenes)。")
            res = self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, outline_text)
            data = self.ai_client.extract_json_from_text(res)
            if not data:
                raise ValueError("无效JSON")
            norm = self.app._normalize_script_data(data)
            if not norm:
                raise ValueError("结构错误")
            return norm

        self.pool.submit(
            task_id="script_from_outline",
            fn=task,
            on_success=lambda result: self.root.after(0, lambda: self.app._apply_ai_script(result)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("错误", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app._set_script_ai_state(False, "就绪")),
            tk_root=self.root
        )

    # --- Script Continue ---

    def continue_script(self, context):
        """AI续写剧本内容。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请先在左侧配置AI接口URL和模型名称")
            return

        self.app.status_var.set("AI正在续写...")

        def task():
            sys_p = self.app.config_manager.get("prompt_continue_script", "你是专业的编剧助手。请根据给定的上文，续写接下来的剧本内容（对话或动作描述）。请保持格式和风格一致。直接输出续写内容。")
            user_p = f"剧本上文：\n{context}\n\n请续写："
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, user_p)

        self.pool.submit(
            task_id="continue_script",
            fn=task,
            on_success=lambda res: self.root.after(0, lambda: self.app._insert_ai_text(res)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("续写失败", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app.status_var.set("续写完成")),
            tk_root=self.root
        )

    def check_logic_consistency(self, script_text):
        """检查剧本逻辑一致性。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        self.app.status_var.set("正在进行逻辑检查...")

        def task():
            sys_p = self.app.config_manager.get("prompt_diagnose_outline", "你是专业的剧本逻辑审校。请检查剧本中的逻辑漏洞、时间线冲突、角色行为不一致等问题。输出Markdown格式的检查报告。")
            # 如果文本过长，只发送前50000字符
            user_p = f"剧本内容:\n{script_text[:50000]}"
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, user_p)

        def on_success(res):
            from writer_app.ui.dialogs import DiagnosisResultDialog
            if not self._is_ai_mode_active():
                return
            DiagnosisResultDialog(self.root, res, title="逻辑检查报告")

        self.pool.submit(
            task_id="logic_check",
            fn=task,
            on_success=lambda res: self.root.after(0, lambda: on_success(res)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("错误", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app.status_var.set("逻辑检查完成")),
            tk_root=self.root
        )

    def rewrite_style(self, text, style, callback):
        """用指定风格重写文本。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        style_prompts = {
            "humorous": "用幽默、风趣、带有反讽的风格重写这段内容。",
            "dark": "用严肃、黑暗、压抑的风格重写这段内容。",
            "concise": "用简洁有力、海明威式的风格重写这段内容，去除冗余修饰。",
            "detailed": "用细腻、感性、充满细节描写（视觉、听觉、嗅觉）的风格重写这段内容。",
            "casual": "用口语化、接地气、自然的对话风格重写这段内容。"
        }
        target_style = style_prompts.get(style, f"用 {style} 风格重写这段内容。")

        def task():
            sys_p = "你是专业的创意写作助手。"
            user_p = f"原文：\n{text}\n\n要求：{target_style}\n\n请直接输出重写后的内容："
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, user_p)

        self.pool.submit(
            task_id="rewrite_style",
            fn=task,
            on_success=lambda res: self.root.after(0, lambda: callback(res)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("重写失败", str(e))),
            tk_root=self.root
        )

    # --- Analysis ---

    def analyze_script(self, type_, script_text):
        """执行剧本分析。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        def task():
            sys_p = f"你是剧本顾问，请进行{type_}，输出Markdown。"
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, script_text)

        def on_success(res):
            from writer_app.ui.dialogs import DiagnosisResultDialog
            if not self._is_ai_mode_active():
                return
            DiagnosisResultDialog(self.root, res)

        self.pool.submit(
            task_id="analyze_script",
            fn=task,
            on_success=lambda res: self.root.after(0, lambda: on_success(res)),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("错误", str(e))),
            tk_root=self.root
        )

    def analyze_scene_pacing(self, scenes, callback):
        """
        批量分析场景的节奏和情绪。
        scenes: list of dicts {idx, name, content}
        callback: func(results) -> results is dict {idx: {pacing, valence}}
        """
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        self.app.status_var.set("正在分析故事曲线...")

        def task():
            # 准备批量分析提示
            prompt = "请分析以下剧本场景的【节奏强度 (Pacing)】(1-10分，1为平静，10为极度紧张) 和 【情绪正负值 (Valence)】(-5到+5，-5为极度悲伤/绝望，+5为极度快乐/胜利)。\n\n"
            for s in scenes:
                content_snippet = s['content'][:500].replace("\n", " ")
                prompt += f"场景ID {s['idx']} ({s['name']}): {content_snippet}\n\n"

            prompt += "请严格以JSON格式输出，格式为：\n"
            prompt += '{\n  "results": [\n    {"id": 0, "pacing": 5, "valence": 2},\n    ...\n  ]\n}'

            res = self.ai_client.call_lm_studio_with_prompts(url, model, key, "你是专业的剧本分析师。", prompt)
            data = self.ai_client.extract_json_from_text(res)

            results = {}
            if data and "results" in data:
                for item in data["results"]:
                    idx = item.get("id")
                    if idx is not None:
                        results[idx] = {
                            "pacing": item.get("pacing", 5),
                            "valence": item.get("valence", 0)
                        }
            return results

        self.pool.submit(
            task_id="pacing_analysis",
            fn=task,
            on_success=lambda results: self.root.after(0, lambda: self._run_if_ai_enabled(lambda: callback(results))),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("分析失败", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app.status_var.set("分析完成")),
            tk_root=self.root
        )

    def analyze_character_personality(self, char_name: str, char_desc: str, scene_texts: list, on_success):
        """分析角色性格五维并回传字典结果。"""
        if not self._ensure_ai_enabled():
            return
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        self.app.status_var.set(f"AI正在分析角色性格: {char_name}")

        def _normalize(data):
            mapping = {
                "openness": "openness",
                "conscientiousness": "conscientiousness",
                "extraversion": "extraversion",
                "agreeableness": "agreeableness",
                "neuroticism": "neuroticism",
                "开放性": "openness",
                "尽责性": "conscientiousness",
                "外向性": "extraversion",
                "宜人性": "agreeableness",
                "神经质": "neuroticism",
                "情绪稳定性": "neuroticism",
            }
            result = {}
            for key_in, key_out in mapping.items():
                if key_in in data:
                    try:
                        val = float(data.get(key_in))
                    except (TypeError, ValueError):
                        continue
                    if 0 <= val <= 1:
                        val *= 10
                    result[key_out] = max(0.0, min(10.0, val))

            # Fill missing with neutral values
            for key_out in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
                result.setdefault(key_out, 5.0)
            return result

        def task():
            sys_p = "你是角色心理分析师。请根据给定的角色设定与剧情片段，评估角色性格五维（0-10分）。"
            snippets = "\n".join(scene_texts) if scene_texts else "（暂无剧情片段）"
            user_p = (
                f"角色名: {char_name}\n"
                f"角色描述: {char_desc}\n"
                f"剧情片段:\n{snippets}\n\n"
                "请严格返回 JSON，格式为：\n"
                "{\n"
                '  "openness": 5,\n'
                '  "conscientiousness": 5,\n'
                '  "extraversion": 5,\n'
                '  "agreeableness": 5,\n'
                '  "neuroticism": 5\n'
                "}"
            )
            res = self.ai_client.call_lm_studio_with_prompts(url, model, key, sys_p, user_p)
            data = self.ai_client.extract_json_from_text(res)
            if not data:
                raise ValueError("无效JSON")
            return _normalize(data)

        self.pool.submit(
            task_id=f"personality_{char_name}",
            fn=task,
            on_success=lambda result: self.root.after(0, lambda: self._run_if_ai_enabled(lambda: on_success(result))),
            on_error=lambda e: self.root.after(0, lambda: self.app.messagebox.showerror("分析失败", str(e))),
            on_complete=lambda: self.root.after(0, lambda: self.app.status_var.set("就绪")),
            tk_root=self.root
        )

    # --- 任务管理 ---

    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务。"""
        return self.pool.cancel(task_id)

    def cancel_all_tasks(self) -> int:
        """取消所有AI任务。"""
        return self.pool.cancel_all()

    def is_task_running(self, task_id: str) -> bool:
        """检查任务是否正在运行。"""
        return self.pool.is_running(task_id)

    def get_active_task_count(self) -> int:
        """获取活跃任务数量。"""
        return self.pool.get_active_count()

    def cleanup(self):
        """清理资源，取消所有待处理任务。"""
        cancelled = self.cancel_all_tasks()
        if cancelled > 0:
            logger.info(f"AI控制器清理: 取消了 {cancelled} 个任务")
