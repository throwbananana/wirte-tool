import logging
import tkinter as tk
from tkinter import messagebox, Toplevel, ttk, scrolledtext
from writer_app.core.training import TrainingManager, MODES, DAILY_QUEST_PASS_SCORE

# 上下文截断限制（用于AI对话）
CONTEXT_TRUNCATE_LIMIT = 1000
from writer_app.core.training_history import TrainingHistoryManager
from writer_app.core.training_challenges import ChallengeManager
from writer_app.core.stats_manager import StatsManager
from writer_app.ui.word_bank_editor import WordBankEditor
from writer_app.ui.stats_visualizer import StatsVisualizer
from writer_app.core.thread_pool import get_ai_thread_pool
from writer_app.core.event_bus import get_event_bus, Events
from typing import List, Tuple, Callable, Any
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class TrainingController:
    def __init__(self, view, project_manager, theme_manager, ai_client, config_manager, gamification_manager=None):
        self.view = view
        self.project_manager = project_manager
        self.theme_manager = theme_manager
        self.ai_client = ai_client
        self.config_manager = config_manager
        self.gamification_manager = gamification_manager

        # Lifecycle tracking (手动实现，因为不继承 BaseController)
        self._destroyed = False
        self._event_subscriptions: List[Tuple[str, Callable]] = []
        self._theme_listeners: List[Callable] = []
        self._gamification_listeners: List[Tuple[Any, Callable]] = []

        # 数据管理器的路径解析
        from pathlib import Path
        data_dir = Path(__file__).parent.parent.parent / "writer_data"

        self.manager = TrainingManager(data_dir)
        self.history_manager = TrainingHistoryManager(data_dir)
        self.challenge_manager = ChallengeManager(data_dir)
        self.stats_manager = StatsManager(self.history_manager)

        self.pool = get_ai_thread_pool()

        # 状态跟踪
        self.current_exercise_data = {}
        self.current_mode = "keywords"
        self.current_level = "级别1"
        self.active_challenge_id = None
        self.challenge_prompt_text = None
        self._gamification_listener_added = False
        self._request_counter = 0
        self._active_prompt_request_id = None
        self._active_analysis_request_id = None
        self._active_daily_quest_request_id = None
        self._loading_challenge = False

        # set_controller 会触发 UI 回调（例如 on_mode_changed），因此放在状态初始化之后。
        self.view.set_controller(self)

        self._add_theme_listener(self.view.apply_theme)
        self.set_ai_mode_enabled(self.config_manager.is_ai_enabled())
        self._subscribe_events()

    def _subscribe_event(self, event_type: str, handler: Callable) -> None:
        """订阅事件并追踪以便清理"""
        bus = get_event_bus()
        bus.subscribe(event_type, handler)
        self._event_subscriptions.append((event_type, handler))

    def _add_theme_listener(self, handler: Callable) -> None:
        """添加主题监听器并追踪以便清理"""
        if self.theme_manager:
            self.theme_manager.add_listener(handler)
            self._theme_listeners.append(handler)

    def _add_gamification_listener(self, manager: Any, handler: Callable) -> None:
        """添加游戏化管理器监听器并追踪以便清理"""
        if manager:
            manager.add_listener(handler)
            self._gamification_listeners.append((manager, handler))

    def cleanup(self) -> None:
        """清理所有追踪的资源"""
        self._destroyed = True

        # 取消订阅 EventBus
        bus = get_event_bus()
        for event_type, handler in self._event_subscriptions:
            try:
                bus.unsubscribe(event_type, handler)
            except Exception:
                pass
        self._event_subscriptions.clear()

        # 移除主题监听器
        if self.theme_manager:
            for handler in self._theme_listeners:
                try:
                    self.theme_manager.remove_listener(handler)
                except Exception:
                    pass
        self._theme_listeners.clear()

        # 移除游戏化管理器监听器
        for manager, handler in self._gamification_listeners:
            try:
                if hasattr(manager, 'remove_listener'):
                    manager.remove_listener(handler)
            except Exception:
                pass
        self._gamification_listeners.clear()

        logger.debug("TrainingController cleanup completed")

    def _subscribe_events(self):
        """订阅事件总线（使用追踪方法以便清理）"""
        self._subscribe_event(Events.PROJECT_LOADED, self._on_project_loaded)

    def _on_project_loaded(self, event_type=None, **kwargs):
        """响应项目加载事件"""
        self.refresh()

    def _next_request_id(self):
        self._request_counter += 1
        return self._request_counter

    def on_mode_changed(self) -> None:
        """Clear stale exercise state when the user changes mode manually."""
        if self._loading_challenge:
            return

        # Cancel pending prompt tasks when possible and invalidate callbacks.
        self.pool.cancel("setup_generation")
        self.pool.cancel("keyword_generation")
        self._active_prompt_request_id = self._next_request_id()

        self.current_mode = self.view.get_selected_mode_key()
        self.current_exercise_data = {}
        self.active_challenge_id = None
        self.challenge_prompt_text = None

    def _is_request_active(self, request_type, request_id):
        if request_type == "prompt":
            return request_id == self._active_prompt_request_id
        if request_type == "analysis":
            return request_id == self._active_analysis_request_id
        if request_type == "daily_quest":
            return request_id == self._active_daily_quest_request_id
        return True

    def refresh(self):
        """刷新视图"""
        if hasattr(self.view, 'refresh'):
            self.view.refresh()

        if self.gamification_manager:
            if not self._gamification_listener_added:
                self._add_gamification_listener(self.gamification_manager, self._on_gamification_update)
                self._gamification_listener_added = True
            self._update_gamification_view()

    def _on_gamification_update(self, event_type, data):
        self.view.after(0, lambda: self._update_gamification_view(data))

    def _update_gamification_view(self, data=None):
        if not self.gamification_manager:
            return
        if not data:
            data = self.gamification_manager.get_stats()

        lvl = data.get("level", 1)
        xp = data.get("xp", 0)
        next_xp = self.gamification_manager.get_next_level_xp()
        title = self.gamification_manager.get_current_title()

        self.view.update_gamification_ui(lvl, title, xp, next_xp)

    def get_levels(self):
        return self.manager.get_levels()

    def get_tags(self):
        return self.manager.get_all_tags()

    def get_challenges(self):
        return self.challenge_manager.get_all_challenges()

    def load_challenge(self, challenge_id):
        challenge = self.challenge_manager.get_challenge(challenge_id)
        if not challenge:
            return

        if not challenge["unlocked"]:
            messagebox.showwarning("已锁定", "请先完成前置挑战以解锁此项！")
            return

        self.active_challenge_id = challenge_id

        # Prevent programmatic mode changes from clearing challenge state.
        self._loading_challenge = True
        try:
            if hasattr(self.view, "select_mode_by_key"):
                self.view.select_mode_by_key(challenge["mode"])
            else:
                self.view.mode_var.set(self.manager.get_modes().get(challenge["mode"]))
            self.view.level_var.set(challenge["level"])
            self.view.topic_var.set(challenge["topic"])
        finally:
            self._loading_challenge = False

        self.current_mode = challenge["mode"]
        self.current_level = challenge["level"]
        self.current_exercise_data = {
            "mode": challenge["mode"],
            "level": challenge["level"],
            "topic": challenge["topic"],
            "challenge_id": challenge_id
        }

        prompt_text = f"🔥 挑战：{challenge['title']}\n{challenge['description']}\n\n目标分数：{challenge['min_score']}"
        self.challenge_prompt_text = prompt_text
        self.view.update_prompt_display(prompt_text)
        self.generate_prompt(is_challenge=True)

    def load_daily_quest(self):
        quest = self.challenge_manager.get_daily_quest()
        if not quest:
            return

        if quest["completed"]:
            messagebox.showinfo("每日任务", "你今天已经完成了每日任务！")
            return

        if self._is_ai_enabled() and quest.get("generated_by") != "ai":
            self._generate_ai_daily_quest(quest)
            return

        self._apply_daily_quest(quest)

    def _apply_daily_quest(self, quest):
        if not quest:
            return

        self.active_challenge_id = "daily"
        # Prevent programmatic mode changes from clearing quest state.
        self._loading_challenge = True
        try:
            if hasattr(self.view, "select_mode_by_key"):
                self.view.select_mode_by_key(quest["mode"])
            else:
                self.view.mode_var.set(self.manager.get_modes().get(quest["mode"]))
            self.view.level_var.set(quest["level"])
            self.view.topic_var.set(quest["topic"])
        finally:
            self._loading_challenge = False

        self.current_mode = quest["mode"]
        self.current_level = quest["level"]
        self.current_exercise_data = {
            "mode": quest["mode"],
            "level": quest["level"],
            "topic": quest["topic"],
            "challenge_id": "daily"
        }

        prompt_text = f"🌟 每日任务：{quest['title']}\n{quest['description']}"
        self.challenge_prompt_text = prompt_text
        self.view.update_prompt_display(prompt_text)
        self.generate_prompt(is_challenge=True)

    def _generate_ai_daily_quest(self, fallback_quest):
        self._active_daily_quest_request_id = self._next_request_id()
        request_id = self._active_daily_quest_request_id
        today = datetime.now().strftime("%Y-%m-%d")

        self.view.update_prompt_display("正在生成每日任务...")

        url, model, key = self._get_ai_config()

        def run_generation():
            prompt = self.manager.get_daily_quest_prompt()
            resp = self.ai_client.call_lm_studio_with_prompts(url, model, key, "Planner", prompt)
            data = self.ai_client.extract_json_from_text(resp)
            quest = self._normalize_ai_daily_quest(data, today)
            if not quest:
                raise ValueError("AI 未返回有效的每日任务数据")
            return quest

        def on_success(quest):
            if not self._is_request_active("daily_quest", request_id):
                return
            self.challenge_manager.set_daily_quest(quest)
            self._apply_daily_quest(quest)

        def on_error(_err):
            if not self._is_request_active("daily_quest", request_id):
                return
            self._apply_daily_quest(fallback_quest)

        self.pool.cancel("daily_quest_generation")
        self.pool.submit(
            "daily_quest_generation",
            run_generation,
            on_success=on_success,
            on_error=on_error,
            tk_root=self.view
        )

    def _normalize_ai_daily_quest(self, data, date_str):
        if not isinstance(data, dict):
            return None

        allowed_modes = ["keywords", "brainstorm", "style", "sensory", "show_dont_tell", "editing"]
        mode = data.get("mode")
        if mode not in allowed_modes:
            return None

        topic = (data.get("topic") or "").strip()
        if not topic:
            return None

        level = data.get("level") or "级别2（动作/抽象）"
        if level not in self.manager.get_levels():
            level = "级别2（动作/抽象）"

        title = (data.get("title") or f"每日任务：{topic}").strip()
        description = (data.get("description") or f"完成一个「{MODES.get(mode, mode)}」练习，主题是「{topic}」。").strip()

        return {
            "date": date_str,
            "title": title,
            "description": description,
            "mode": mode,
            "topic": topic,
            "level": level,
            "completed": False,
            "generated_by": "ai"
        }

    def _submit_ai_task(self, task_id, func, *args, success_callback=None, error_callback=None, request_type=None, request_id=None):
        """提交AI任务的辅助方法，包含标准错误处理和UI清理。"""

        def on_success(result):
            if request_id is not None and not self._is_request_active(request_type, request_id):
                return
            if success_callback:
                success_callback(result)

        def on_error(e):
            if request_id is not None and not self._is_request_active(request_type, request_id):
                return
            self.view.show_feedback(f"错误：{e}")
            # 如果是setup任务也更新提示显示
            if "setup" in task_id:
                self.view.update_prompt_display(f"生成失败：{e}")
            if error_callback:
                error_callback(e)

        def on_complete():
            if request_id is not None and not self._is_request_active(request_type, request_id):
                return
            self.view.set_analyzing(False)
            self.view.generate_btn.config(state="normal")

        self.pool.submit(
            task_id,
            func,
            *args,
            on_success=on_success,
            on_error=on_error,
            on_complete=on_complete,
            tk_root=self.view
        )

    def generate_prompt(self, is_challenge=False):
        self._active_prompt_request_id = self._next_request_id()
        request_id = self._active_prompt_request_id
        mode_key = self.view.get_selected_mode_key()
        level = self.view.level_var.get()
        topic = self.view.topic_var.get().strip()
        selected_tag = self.view.tag_var.get().strip()

        if not is_challenge:
            self.active_challenge_id = None
            self.challenge_prompt_text = None

        self.current_mode = mode_key
        self.current_level = level
        self.current_exercise_data = {
            "mode": mode_key,
            "level": level,
            "topic": topic,
            "tag": selected_tag,
            "challenge_id": self.active_challenge_id
        }

        if not is_challenge:
            self.view.update_prompt_display("正在生成题目...")

        self.view.generate_btn.config(state="disabled")

        if mode_key == "keywords":
            if self._is_ai_enabled():
                self._handle_keywords_generation(topic, level, selected_tag, is_challenge, request_id)
            else:
                self._fallback_to_local(level, selected_tag)
                self.view.after(0, lambda: self.view.generate_btn.config(state="normal"))
        elif mode_key == "style":
            style = self.manager.get_random_style()
            self.current_exercise_data["style"] = style
            display = f"目标风格：{style}\n主题：{topic or selected_tag or '自选'}"
            prefix = self._get_challenge_prefix() if is_challenge else None
            if prefix:
                display = f"{prefix}\n\n{display}"
            self.view.update_prompt_display(display)
            self.view.generate_btn.config(state="normal")
        elif mode_key == "sensory":
            constraint = self.manager.get_random_sensory_constraint()
            self.current_exercise_data["constraint"] = constraint
            display = f"感官限制：{constraint}\n主题：{topic or selected_tag or '自选'}"
            prefix = self._get_challenge_prefix() if is_challenge else None
            if prefix:
                display = f"{prefix}\n\n{display}"
            self.view.update_prompt_display(display)
            self.view.generate_btn.config(state="normal")
        elif mode_key == "emotion_infusion":
            emotion = self.manager.get_random_emotion()
            self.current_exercise_data["emotion"] = emotion
            display = f"目标情感：{emotion}\n主题：{topic or selected_tag or '自选'}"
            prefix = self._get_challenge_prefix() if is_challenge else None
            if prefix:
                display = f"{prefix}\n\n{display}"
            self.view.update_prompt_display(display)
            self.view.generate_btn.config(state="normal")
        elif mode_key == "character_persona":
            archetype = self.manager.get_random_archetype()
            self.current_exercise_data["archetype"] = archetype
            display = f"角色原型/特质：{archetype}\n主题：{topic or selected_tag or '自选'}\n\n任务：创建详细的角色档案（姓名、年龄、背景、目标、缺陷）。"
            prefix = self._get_challenge_prefix() if is_challenge else None
            if prefix:
                display = f"{prefix}\n\n{display}"
            self.view.update_prompt_display(display)
            self.view.generate_btn.config(state="normal")
        elif mode_key == "character_arc":
            event = self.manager.get_random_event()
            self.current_exercise_data["event"] = event
            display = f"突发事件：{event}\n主题：{topic or selected_tag or '自选'}\n\n任务：写出角色反应和解释反应的隐藏伏笔。"
            prefix = self._get_challenge_prefix() if is_challenge else None
            if prefix:
                display = f"{prefix}\n\n{display}"
            self.view.update_prompt_display(display)
            self.view.generate_btn.config(state="normal")
        else:
            eff_topic = topic if topic else (f"类型：{selected_tag}" if selected_tag else "")
            if not self._is_ai_enabled():
                display = self._build_non_ai_prompt(mode_key, eff_topic)
                prefix = self._get_challenge_prefix() if is_challenge else None
                if prefix:
                    display = f"{prefix}\n\n{display}"
                self.view.update_prompt_display(display)
                self.view.generate_btn.config(state="normal")
            else:
                url, model, key = self._get_ai_config()

                # 线程中运行的逻辑
                def run_setup():
                    prompt = self.manager.get_setup_prompt(mode_key, eff_topic)
                    resp = self.ai_client.call_lm_studio_with_prompts(url, model, key, "Assistant", prompt)
                    return resp.strip().strip('"')

                # 更新UI的回调
                def on_setup_done(resp):
                    if not self._is_request_active("prompt", request_id):
                        return
                    display = resp
                    if mode_key == "show_dont_tell":
                        self.current_exercise_data["telling"] = resp
                        display = f"请将这句「直白叙述」改写为「展示」：\n\n{resp}"
                        self.view.set_content(resp)
                    elif mode_key == "editing":
                        self.current_exercise_data["telling"] = resp
                        display = f"请修复以下文本：\n\n{resp}"
                        self.view.set_content(resp)
                    elif mode_key == "emotion_infusion":
                        self.current_exercise_data["telling"] = resp
                        display = f"请为这个句子注入情感：\n\n{resp}"
                        self.view.set_content(resp)
                    elif mode_key == "character_persona":
                        self.current_exercise_data["archetype"] = resp
                        display = f"基于以下设定创建角色：\n\n{resp}\n\n包括：姓名、年龄、背景、目标、缺陷。"
                    elif mode_key == "character_arc":
                        self.current_exercise_data["event"] = resp
                        display = f"事件：{resp}\n\n写出反应 + 伏笔。"

                    if is_challenge:
                        prefix = self._get_challenge_prefix()
                        if prefix:
                            display = f"{prefix}\n\n{display}"
                    self.view.update_prompt_display(display)

                self._submit_ai_task(
                    "setup_generation",
                    run_setup,
                    success_callback=on_setup_done,
                    request_type="prompt",
                    request_id=request_id
                )

    def _handle_keywords_generation(self, topic, level, tag, is_challenge, request_id):
        ai_topic = topic
        if tag:
            ai_topic += f"（类型/标签：{tag}）" if ai_topic else f"类型：{tag}"

        url, model, key = self._get_ai_config()

        def run_keywords():
            prompt = self.manager.get_word_generation_prompt(ai_topic, level)
            resp = self.ai_client.call_lm_studio_with_prompts(url, model, key, "Assistant", prompt)
            return self.ai_client.extract_json_from_text(resp)

        def on_keywords_done(words):
            if not self._is_request_active("prompt", request_id):
                return
            if words and isinstance(words, list):
                self.current_exercise_data["words"] = words
                display = f"关键词（AI生成）：{', '.join(words)}"
                prefix = self._get_challenge_prefix() if is_challenge else None
                if prefix:
                    display = f"{prefix}\n\n{display}"
                self.view.update_prompt_display(display)
            else:
                self._fallback_to_local(level, tag)

        def on_keywords_error(_err):
            if not self._is_request_active("prompt", request_id):
                return
            self._fallback_to_local(level, tag)

        self._submit_ai_task(
            "keyword_generation",
            run_keywords,
            success_callback=on_keywords_done,
            error_callback=on_keywords_error,
            request_type="prompt",
            request_id=request_id
        )

    def analyze_content(self):
        content = self.view.get_content()
        if not content:
            self.view.show_feedback("请先写点内容！")
            return
        if not self.current_exercise_data:
            self.view.show_feedback("请先生成题目。")
            return

        self.view.set_analyzing(True)
        self._active_analysis_request_id = self._next_request_id()
        request_id = self._active_analysis_request_id

        # AI与本地分支
        if self._is_ai_enabled():
            url, model, key = self._get_ai_config()

            def run_analysis():
                prompt = self.manager.get_analysis_prompt(self.current_mode, self.current_exercise_data, content)
                return self.ai_client.call_lm_studio_with_prompts(url, model, key, "Coach", prompt)

            self._submit_ai_task(
                "analysis",
                run_analysis,
                success_callback=lambda resp: self._on_analysis_done(resp, request_id=request_id),
                request_type="analysis",
                request_id=request_id
            )
        else:
            # 本地离线分析
            # 模拟短暂延迟以改善用户体验
            self.view.after(500, lambda: self._run_offline_analysis(content, request_id))

    def _run_offline_analysis(self, content, request_id):
        response = self.manager.evaluate_offline(self.current_mode, self.current_exercise_data, content)
        self._on_analysis_done(response, request_id=request_id)

    def _normalize_scores(self, data):
        if not isinstance(data, dict):
            return {}
        scores = data.get("scores") if isinstance(data.get("scores"), dict) else data

        def get_int(*keys):
            for key in keys:
                if key in scores:
                    try:
                        return int(scores[key])
                    except (TypeError, ValueError):
                        continue
            return None

        score_1 = get_int("score_1", "Score 1", "评分1", "评分 1")
        score_2 = get_int("score_2", "Score 2", "评分2", "评分 2")
        score_3 = get_int("score_3", "Score 3", "评分3", "评分 3")
        total = get_int("total", "Total Score", "总分", "总分数")

        if total is None and all(isinstance(v, int) for v in [score_1, score_2, score_3]):
            total = score_1 + score_2 + score_3

        labels = {}
        if isinstance(scores.get("labels"), dict):
            labels.update(scores.get("labels", {}))
        for idx in (1, 2, 3):
            for key in (f"label_{idx}", f"label{idx}"):
                if key in scores:
                    labels[f"score_{idx}"] = scores.get(key)

        return {
            "score_1": score_1 or 0,
            "score_2": score_2 or 0,
            "score_3": score_3 or 0,
            "total": total or 0,
            "labels": labels
        }

    def _parse_scores_from_text(self, response_text):
        scores = {}
        score_matches = re.findall(
            r"(评分\s*\d|Score \d|总分|Total Score|创意|结构|词汇|风格|专注|冲击力|逻辑|流畅|节奏|贴合度|深度|氛围|生动|篇幅|Creativity|Structure|Vocabulary|Style|Focus|Impact|Logic|Flow|Pacing|Adherence|Depth|Atmosphere|Vividness|Volume)[\s:：]*(\d+)",
            response_text, re.IGNORECASE)
        for k, v in score_matches:
            scores[k.strip()] = int(v)
        return self._normalize_scores(scores)

    def _on_analysis_done(self, response, request_id=None):
        if request_id is not None and not self._is_request_active("analysis", request_id):
            return

        scores = {}
        feedback_text = ""
        display_text = ""

        if isinstance(response, dict):
            scores = self._normalize_scores(response)
            feedback_text = response.get("feedback") or response.get("text") or response.get("analysis") or ""
            display_text = feedback_text
        elif isinstance(response, str):
            extracted = self.ai_client.extract_json_from_text(response)
            if isinstance(extracted, dict):
                scores = self._normalize_scores(extracted)
                feedback_text = extracted.get("feedback") or extracted.get("text") or ""
                display_text = feedback_text or response
            else:
                scores = self._parse_scores_from_text(response)
                display_text = response
        else:
            display_text = str(response)

        if not display_text:
            display_text = "评分完成，但未返回详细点评。"

        self.history_manager.add_session(
            self.current_mode,
            self.current_exercise_data,
            self.view.get_content(),
            display_text,
            scores
        )

        # 记录字数
        content = self.view.get_content()
        if self.gamification_manager:
            self.gamification_manager.record_words(len(content))

        total = scores.get("total", 0)
        reward_msg = ""
        if self.gamification_manager and total > 0:
            xp = total * 5
            self.gamification_manager.gain_experience(xp, f"完成{self.current_mode}训练")
            reward_msg = f"\n\n💎 获得 {xp} 经验值！"

        completion_msg = ""
        if self.active_challenge_id == "daily":
            if total >= DAILY_QUEST_PASS_SCORE:
                if self.challenge_manager.complete_daily_quest():
                    completion_msg = "\n\n🌟 每日任务完成！（+50 额外经验）"
                    if self.gamification_manager:
                        self.gamification_manager.gain_experience(50, "每日任务奖励")
                    self.active_challenge_id = None
            else:
                completion_msg = f"\n\n❌ 每日任务分数不足（需要 {DAILY_QUEST_PASS_SCORE} 分）。"
        if self.active_challenge_id and self.active_challenge_id != "daily":
            success, msg = self.challenge_manager.complete_challenge(self.active_challenge_id, total)
            if success:
                completion_msg = f"\n\n🎉 {msg}"
                self.active_challenge_id = None
            else:
                completion_msg = f"\n\n❌ 挑战失败：{msg}"

        # 发布事件给浮动助手
        get_event_bus().publish("training_completed", mode=self.current_mode, score=total)

        self.view.show_feedback(display_text + reward_msg + completion_msg)
        self.view.set_analyzing(False)
        self.view.generate_btn.config(state="normal")

    def ai_rewrite(self):
        if not self._require_ai("AI改写"):
            return
        content = self.view.get_content()
        if not content:
            return
        self.view.set_analyzing(True)
        url, model, key = self._get_ai_config()

        def run_rewrite():
            prompt = self.manager.get_rewrite_prompt(self.current_mode, self.current_exercise_data, content)
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, "Expert", prompt)

        def on_rewrite_done(response):
            current_feedback = self.view.feedback_area.get("1.0", "end").strip()
            self.view.show_feedback(f"{current_feedback}\n\n=== AI 改写完成 ===\n（请查看弹出窗口进行详细对比）")
            self.view.show_diff_dialog(content, response)

        self._submit_ai_task("rewrite", run_rewrite, success_callback=on_rewrite_done)

    def ai_polish(self):
        if not self._require_ai("AI润色"):
            return
        content = self.view.get_content()
        if not content:
            return
        self.view.set_analyzing(True)
        url, model, key = self._get_ai_config()

        def run_polish():
            prompt = self.manager.get_polish_prompt(content)
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, "Editor", prompt)

        def on_polish_done(response):
            current_feedback = self.view.feedback_area.get("1.0", "end").strip()
            self.view.show_feedback(f"{current_feedback}\n\n=== 润色建议 ===\n{response}")

        self._submit_ai_task("polish", run_polish, success_callback=on_polish_done)

    def ask_coach(self, question):
        if not self._require_ai("AI教练对话"):
            return
        current_feedback = self.view.feedback_area.get("1.0", "end").strip()
        if not current_feedback:
            messagebox.showinfo("提示", "请先提交作品进行分析。")
            return
        self.view.set_analyzing(True)
        url, model, key = self._get_ai_config()

        def run_chat():
            prompt = f"之前的分析：\n{current_feedback[:CONTEXT_TRUNCATE_LIMIT]}...\n\n学员问题：{question}\n请提供帮助性回答。"
            return self.ai_client.call_lm_studio_with_prompts(url, model, key, "Coach", prompt)

        def on_chat_done(response):
            self.view.show_feedback(f"{current_feedback}\n\n👤 你：{question}\n🤖 教练：{response}")

        self._submit_ai_task("coach_chat", run_chat, success_callback=on_chat_done)

    def _fallback_to_local(self, level, tag):
        tags = [tag] if tag else []
        words = self.manager.get_words(level, 5, tags=tags)
        note = ""
        if not words and tag:
            words = self.manager.get_words(level, 5, tags=[])
            note = f"（标签「{tag}」没有匹配词汇，已使用全量词库）\n"
        self.current_exercise_data["words"] = words
        display = f"{note}关键词（本地生成）：{', '.join(words)}"
        prefix = self._get_challenge_prefix()
        if prefix:
            display = f"{prefix}\n\n{display}"
        self.view.after(0, lambda: self.view.update_prompt_display(display))

    def show_history(self):
        history = self.history_manager.get_history()
        win = Toplevel(self.view)
        win.title("训练历史")
        win.geometry("600x450")

        listbox = tk.Listbox(win, font=("Consolas", 10))
        listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(win, orient="vertical", command=listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scroll.set)

        for sess in history:
            date = sess.get("date_str", "未知")
            mode = sess.get("mode", "通用")
            scores = sess.get("scores", {})
            score = scores.get("total") or scores.get("Total Score") or scores.get("总分") or "?"
            listbox.insert(tk.END, f"[{date}] {mode.upper()}（得分：{score}）")

        listbox.bind("<Double-Button-1>", lambda e: self._show_session_detail(listbox, history))

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="清空所有历史", command=lambda: self._clear_history_ui(win)).pack(side=tk.LEFT)

    def _clear_history_ui(self, win):
        if messagebox.askyesno("确认", "确定要删除所有历史记录吗？"):
            self.history_manager.clear_history()
            win.destroy()
            messagebox.showinfo("成功", "历史记录已清空。")

    def _show_session_detail(self, listbox, history):
        idx = listbox.curselection()
        if not idx:
            return
        data = history[idx[0]]
        detail_win = Toplevel(listbox)
        detail_win.title("会话详情")
        detail_win.geometry("500x500")
        txt = scrolledtext.ScrolledText(detail_win, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True)
        info = f"日期：{data.get('date_str')}\n模式：{data.get('mode')}\n题目：{data.get('prompt_data')}\n---\n内容：\n{data.get('content')}\n---\n反馈：\n{data.get('analysis_text')}"
        txt.insert("1.0", info)
        txt.config(state="disabled")

    def open_editor(self):
        WordBankEditor(self.view, self.manager)

    def show_stats(self):
        radar = self.stats_manager.get_radar_data()
        StatsVisualizer(self.view, radar)

    def _get_ai_config(self):
        url = self.config_manager.get("lm_api_url", "http://localhost:1234/v1/chat/completions")
        model = self.config_manager.get("lm_api_model", "local-model")
        key = self.config_manager.get("lm_api_key", "")
        return url, model, key

    def _is_ai_enabled(self):
        return self.config_manager.is_ai_enabled()

    def _require_ai(self, label):
        if self._is_ai_enabled():
            return True
        messagebox.showinfo("提示", f"当前为非AI模式，{label}不可用。")
        return False

    def _build_non_ai_prompt(self, mode, topic):
        base_topic = topic or "自选主题"
        starter = self.manager.get_offline_starter(mode)

        if mode == "continuation":
            self.current_exercise_data["starter"] = starter
            prompt = f"续写练习：请接续以下开头进行创作。\n\n【开头】\n{starter}"
        elif mode == "show_dont_tell":
            self.current_exercise_data["telling"] = starter
            prompt = f"表现性写作：请将以下直白陈述改写为更具画面感的描述。\n\n【原句】\n{starter}"
        elif mode == "editing":
            self.current_exercise_data["telling"] = starter
            prompt = f"文本修订：请润色与精简以下片段。\n\n【原文】\n{starter}"
        elif mode == "brainstorm":
            prompt = f"头脑风暴：请列出与「{base_topic}」相关的10个创意点子（每条独立一行）。"
        elif mode == "dialogue_subtext":
            prompt = f"潜台词训练：{starter}\n\n请编写一段对话，体现上述潜台词。"
        elif mode == "character_voice":
            prompt = f"角色腔调：请设计两个性格迥异的角色，围绕「{base_topic}」展开对话，体现各自的说话风格。"
        elif mode == "character_persona":
            prompt = f"人设生成：请基于原型「{self.manager.get_random_archetype()}」和主题「{base_topic}」创作一个完整的人物小传（姓名、年龄、背景、目标、弱点）。"
        elif mode == "character_arc":
            prompt = f"人物弧光：突发事件「{self.manager.get_random_event()}」。请描写人物反应，并补充一段隐藏铺垫（前史）来解释该反应。"
        else:
            prompt = f"写作练习：请围绕「{base_topic}」进行创作。"
        return prompt

    def _get_challenge_prefix(self):
        if self.active_challenge_id and self.challenge_prompt_text:
            return self.challenge_prompt_text
        return None

    def set_ai_mode_enabled(self, enabled: bool):
        if hasattr(self.view, "set_ai_mode_enabled"):
            self.view.set_ai_mode_enabled(enabled)

    def save_to_ideas(self, content):
        if not content:
            messagebox.showwarning("提示", "内容为空，无法保存。")
            return

        try:
            # 添加关于练习的元数据
            source_info = f"\n\n[来自创作训练: {MODES.get(self.current_mode, self.current_mode)} | {self.current_exercise_data.get('topic', '无主题')}]"
            full_content = content + source_info

            self.project_manager.add_idea(full_content)
            messagebox.showinfo("成功", "已保存到灵感库！")
        except Exception as e:
            logger.error(f"保存灵感失败: {e}")
            messagebox.showerror("错误", f"保存失败: {e}")
