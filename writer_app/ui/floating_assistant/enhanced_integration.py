"""
悬浮写作助手 - 增强版集成管理器
统一协调所有增强模块，提供简化的对外接口
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
import logging
import random

from .states import AssistantState

logger = logging.getLogger(__name__)


class EnhancedIntegrationManager:
    """
    增强版集成管理器

    职责：
    1. 统一管理所有增强模块的生命周期
    2. 协调模块间的数据流动
    3. 提供简化的对外API
    4. 处理模块间的优先级和冲突
    """

    def __init__(self, event_system):
        """
        初始化集成管理器

        Args:
            event_system: AssistantEventSystem 实例
        """
        self.event_system = event_system
        self.assistant = event_system.assistant
        self.project_manager = event_system.project_manager

        # 模块引用 (从 event_system 获取)
        self.sequence_tracker = event_system.sequence_tracker
        self.personalization = event_system.personalization
        self.deep_analysis = event_system.deep_analysis
        self.proactive_system = event_system.proactive_system
        self.context_feedback = event_system.context_feedback
        self.feedback_selector = event_system.feedback_selector
        self.dynamic_content = event_system.dynamic_content
        self.feedback_loop = event_system.feedback_loop

        # 状态追踪
        self._last_analysis_time = datetime.min
        self._cached_analysis = {}
        self._analysis_cache_ttl = 300  # 5分钟缓存

        # 回调注册
        self._callbacks: Dict[str, List[Callable]] = {
            "pattern_detected": [],
            "intervention_triggered": [],
            "analysis_completed": [],
            "feedback_generated": [],
        }

        logger.info("增强版集成管理器初始化完成")

    # ============================================================
    # 对外统一API
    # ============================================================

    def get_smart_response(self, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        获取智能响应 - 综合所有模块给出最佳响应

        Args:
            context: 当前上下文信息

        Returns:
            包含 message, mood, priority, source 的响应字典
        """
        context = context or {}
        candidates = []

        # 1. 检查主动干预
        intervention = self.proactive_system.check_interventions(context)
        if intervention:
            candidates.append({
                "message": intervention.get("message"),
                "mood": intervention.get("mood", AssistantState.THINKING),
                "priority": intervention.get("priority", 20),
                "source": "proactive",
            })

        # 2. 检查行为模式
        pattern = self.sequence_tracker.detect_pattern()
        if pattern and pattern.get("confidence", 0) > 0.7:
            pattern_msg = self._get_pattern_message(pattern)
            if pattern_msg:
                candidates.append({
                    "message": pattern_msg,
                    "mood": AssistantState.HAPPY,
                    "priority": 30,
                    "source": "pattern",
                })

        # 3. 检查上下文感知提示
        if self.project_manager:
            scenes = self.project_manager.get_scenes()
            if scenes:
                last_scene = scenes[-1]
                content = last_scene.get("content", "")
                content_type = self.context_feedback.detect_content_type(content)
                if content_type:
                    tip = self.context_feedback.get_contextual_tip(content_type)
                    if tip:
                        candidates.append({
                            "message": tip,
                            "mood": AssistantState.THINKING,
                            "priority": 40,
                            "source": "context",
                        })

        # 4. 动态内容生成
        if random.random() < 0.3 and self.project_manager:
            dynamic = self._generate_dynamic_content()
            if dynamic:
                candidates.append({
                    "message": dynamic,
                    "mood": AssistantState.CURIOUS,
                    "priority": 50,
                    "source": "dynamic",
                })

        # 选择优先级最高的响应
        if candidates:
            candidates.sort(key=lambda x: x["priority"])
            return candidates[0]

        return None

    def get_comprehensive_analysis(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取综合分析结果

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            包含所有分析维度的结果字典
        """
        now = datetime.now()

        # 检查缓存
        if not force_refresh:
            cache_age = (now - self._last_analysis_time).total_seconds()
            if cache_age < self._analysis_cache_ttl and self._cached_analysis:
                return self._cached_analysis

        # 执行分析
        result = {
            "timestamp": now.isoformat(),
            "writing_style": {},
            "emotional_curve": [],
            "pacing": {},
            "structure": {},
            "user_profile": {},
        }

        try:
            # 写作风格分析
            result["writing_style"] = self.event_system.get_writing_style_summary()

            # 情感曲线分析
            result["emotional_curve"] = self.event_system.get_emotional_curve()

            # 节奏分析
            result["pacing"] = self.event_system.get_pacing_analysis()

            # 用户行为画像
            result["user_profile"] = self.event_system.get_user_behavior_profile()

            # 结构分析
            if self.project_manager:
                scenes = self.project_manager.get_scenes()
                content = "\n\n".join(s.get("content", "") for s in scenes if s.get("content"))
                if content:
                    result["structure"] = self.deep_analysis.structure_analyzer.analyze(content)

            # 更新缓存
            self._cached_analysis = result
            self._last_analysis_time = now

            # 触发回调
            self._trigger_callback("analysis_completed", result)

        except Exception as e:
            logger.error(f"综合分析失败: {e}")

        return result

    def get_personalized_suggestion(self, category: str = None) -> str:
        """
        获取个性化建议

        Args:
            category: 建议类别 (可选)

        Returns:
            个性化的建议文案
        """
        user_prefs = self.personalization.get_preferences()
        project_type = self.event_system._get_project_type()

        context = {
            "project_type": project_type,
            "time_of_day": self._get_time_period(),
            "user_style": user_prefs.get("writing_style", "unknown"),
        }

        if category:
            return self.feedback_selector.select_feedback(category, user_prefs, context)

        # 自动选择类别
        categories = ["encouragement", "tip", "question"]
        category = random.choice(categories)
        return self.feedback_selector.select_feedback(category, user_prefs, context)

    def record_user_interaction(self, interaction_type: str, data: Dict = None) -> None:
        """
        记录用户交互

        Args:
            interaction_type: 交互类型
            data: 交互数据
        """
        data = data or {}

        # 记录到序列追踪器
        self.sequence_tracker.record_event(interaction_type, data)

        # 记录到个性化引擎
        self.personalization.record_interaction(interaction_type, data)

        # 记录到主动干预系统
        self.proactive_system.record_activity(interaction_type)

    def record_feedback_reaction(self, feedback_id: str, reaction: str) -> None:
        """
        记录用户对反馈的反应

        Args:
            feedback_id: 反馈ID
            reaction: 反应类型 (positive/neutral/negative/dismissed)
        """
        self.feedback_loop.record_feedback(feedback_id, reaction)
        self.personalization.update_preference("feedback_reaction", reaction)

        # 如果是负面反应，调整反馈频率
        if reaction == "negative" or reaction == "dismissed":
            current_freq = self.personalization.get_preference("feedback_frequency", 1.0)
            self.personalization.update_preference("feedback_frequency", max(0.3, current_freq - 0.1))
        elif reaction == "positive":
            current_freq = self.personalization.get_preference("feedback_frequency", 1.0)
            self.personalization.update_preference("feedback_frequency", min(1.5, current_freq + 0.05))

    # ============================================================
    # 回调管理
    # ============================================================

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """注册回调函数"""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)

    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """注销回调函数"""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)

    def _trigger_callback(self, event_type: str, data: Any) -> None:
        """触发回调"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")

    # ============================================================
    # 辅助方法
    # ============================================================

    def _get_pattern_message(self, pattern: Dict) -> Optional[str]:
        """获取模式对应的消息"""
        pattern_id = pattern.get("pattern_id")
        messages = {
            "planner": "我注意到你喜欢先规划后执行，这种方法论很棒！",
            "discovery_writer": "边写边探索的方式很有意思，故事会带给你惊喜的！",
            "character_driven": "角色是你故事的核心呢，人物塑造得很用心！",
            "worldbuilder": "世界观设定很丰富，这个世界会很精彩的！",
            "quick_drafter": "快速成稿的节奏很好，先完成再完美！",
            "perfectionist": "精益求精的态度值得敬佩，每一个细节都很重要~",
        }
        return messages.get(pattern_id)

    def _generate_dynamic_content(self) -> Optional[str]:
        """生成动态内容"""
        if not self.project_manager:
            return None

        try:
            # 随机选择生成类型
            gen_type = random.choice(["character", "scene", "question", "encouragement"])

            if gen_type == "character":
                characters = self.project_manager.get_characters()
                if characters:
                    char = random.choice(characters)
                    return self.dynamic_content.generate_character_comment(char)

            elif gen_type == "scene":
                scenes = self.project_manager.get_scenes()
                if scenes:
                    scene = scenes[-1]
                    return self.dynamic_content.generate_scene_reaction(scene)

            elif gen_type == "question":
                return self.dynamic_content.generate_question()

            elif gen_type == "encouragement":
                context = {"time_of_day": self._get_time_period()}
                return self.dynamic_content.generate_encouragement(context)

        except Exception as e:
            logger.debug(f"动态内容生成失败: {e}")

        return None

    def _get_time_period(self) -> str:
        """获取当前时间段"""
        hour = datetime.now().hour
        if 5 <= hour < 9:
            return "early_morning"
        elif 9 <= hour < 12:
            return "morning"
        elif 12 <= hour < 14:
            return "noon"
        elif 14 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"

    # ============================================================
    # 报告生成
    # ============================================================

    def generate_session_report(self) -> Dict[str, Any]:
        """
        生成会话报告

        Returns:
            包含本次会话统计的报告
        """
        analysis = self.get_comprehensive_analysis()
        profile = analysis.get("user_profile", {})

        return {
            "session_summary": {
                "patterns_detected": profile.get("detected_patterns", []),
                "activity_stats": profile.get("activity_stats", {}),
                "feedback_effectiveness": profile.get("feedback_effectiveness", {}),
            },
            "writing_insights": {
                "style": analysis.get("writing_style", {}),
                "emotional_flow": self._summarize_emotional_curve(analysis.get("emotional_curve", [])),
                "pacing": analysis.get("pacing", {}),
            },
            "recommendations": self._generate_recommendations(analysis),
        }

    def _summarize_emotional_curve(self, curve: List) -> Dict[str, Any]:
        """总结情感曲线"""
        if not curve:
            return {"status": "insufficient_data"}

        # 计算平均情感值
        avg_valence = sum(p.get("valence", 0) for p in curve) / len(curve) if curve else 0
        avg_intensity = sum(p.get("intensity", 0) for p in curve) / len(curve) if curve else 0

        # 检测高潮点
        peaks = [p for p in curve if p.get("intensity", 0) > 0.7]

        return {
            "average_valence": round(avg_valence, 2),
            "average_intensity": round(avg_intensity, 2),
            "peak_count": len(peaks),
            "trend": "rising" if curve and curve[-1].get("intensity", 0) > curve[0].get("intensity", 0) else "falling",
        }

    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成推荐建议"""
        recommendations = []

        # 基于写作风格
        style = analysis.get("writing_style", {})
        if style.get("dialogue_ratio", 0) < 0.2:
            recommendations.append("考虑增加一些对话，让场景更加生动")
        if style.get("avg_sentence_length", 0) > 30:
            recommendations.append("有些句子可能过长，适当断句会更易读")

        # 基于节奏
        pacing = analysis.get("pacing", {})
        issues = pacing.get("issues", [])
        for issue in issues[:2]:  # 最多显示2个节奏问题
            recommendations.append(issue.get("suggestion", ""))

        # 基于情感曲线
        emotional = self._summarize_emotional_curve(analysis.get("emotional_curve", []))
        if emotional.get("peak_count", 0) == 0:
            recommendations.append("故事节奏比较平稳，可以考虑添加一些情感高潮点")

        return [r for r in recommendations if r]  # 过滤空字符串

    # ============================================================
    # 模块状态
    # ============================================================

    def get_module_status(self) -> Dict[str, Any]:
        """获取所有模块的状态"""
        return {
            "sequence_tracker": {
                "events_recorded": len(self.sequence_tracker.event_history) if hasattr(self.sequence_tracker, 'event_history') else 0,
                "patterns_detected": len(self.sequence_tracker.get_detected_patterns()) if hasattr(self.sequence_tracker, 'get_detected_patterns') else 0,
            },
            "personalization": {
                "preferences_count": len(self.personalization.get_preferences()) if hasattr(self.personalization, 'get_preferences') else 0,
            },
            "deep_analysis": {
                "last_analysis": self._last_analysis_time.isoformat() if self._last_analysis_time != datetime.min else None,
                "cache_valid": (datetime.now() - self._last_analysis_time).total_seconds() < self._analysis_cache_ttl,
            },
            "proactive_system": {
                "active": True,
            },
            "feedback_loop": {
                "feedback_count": len(self.feedback_loop.feedback_history) if hasattr(self.feedback_loop, 'feedback_history') else 0,
            },
        }


def create_enhanced_integration(event_system) -> EnhancedIntegrationManager:
    """
    工厂函数：创建增强集成管理器

    Args:
        event_system: AssistantEventSystem 实例

    Returns:
        EnhancedIntegrationManager 实例
    """
    return EnhancedIntegrationManager(event_system)
