"""
悬浮助手 - 主动干预系统 (Proactive Intervention System)
不仅响应事件，还能主动发起互动，提供上下文感知的反馈
"""
import time
import random
import re
from collections import deque
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path


class InterventionType(Enum):
    """干预类型"""
    GENTLE_REMINDER = "gentle_reminder"  # 温和提醒
    ENCOURAGEMENT = "encouragement"      # 鼓励
    SUGGESTION = "suggestion"            # 建议
    MILESTONE = "milestone"              # 里程碑庆祝
    HEALTH_CHECK = "health_check"        # 健康关怀
    CREATIVE_PROMPT = "creative_prompt"  # 创意提示
    ANALYSIS_INSIGHT = "analysis_insight"  # 分析洞察
    CONTEXT_TIP = "context_tip"          # 上下文提示


class InterventionPriority(Enum):
    """干预优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class InterventionOpportunity:
    """干预机会"""
    intervention_type: InterventionType
    priority: InterventionPriority
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    action: Optional[str] = None  # 可选的动作标识
    expires_at: float = 0.0  # 过期时间


@dataclass
class ActivitySnapshot:
    """活动快照"""
    timestamp: float
    event_count: int
    word_count: int
    active_module: str
    last_edit_time: float
    is_typing: bool = False


# 干预消息模板
INTERVENTION_MESSAGES = {
    # 温和提醒
    "idle_gentle": [
        "盯着屏幕发呆好久了...要不要休息一下？",
        "（小声）前辈，有在思考剧情吗？需要帮忙吗？",
        "如果卡住了，出去走走也许会有灵感哦~",
        "我在这里陪着你，不着急~",
    ],
    "idle_long": [
        "已经很久没动了呢...是遇到什么困难了吗？",
        "要不要试试抽一张灵感卡？",
        "如果累了就休息一下吧，我会守着你的进度的~",
    ],

    # 鼓励
    "writing_momentum": [
        "写得真顺啊！保持这个节奏！",
        "键盘都要冒烟了！这就是传说中的心流吗？",
        "太棒了，这种状态要珍惜！",
    ],
    "small_progress": [
        "虽然只写了一点点，但也是进步！",
        "千里之行，始于足下~",
        "每一个字都是前进的一步！",
    ],

    # 里程碑
    "word_count_500": [
        "恭喜！今天已经写了500字了！",
        "500字达成！继续加油~",
    ],
    "word_count_1000": [
        "1000字里程碑！你太厉害了！",
        "破千了！这个效率我都佩服！",
    ],
    "word_count_2000": [
        "2000字！今天的产出真不错！",
        "这产量...前辈是在燃烧生命写作吗？",
    ],
    "word_count_5000": [
        "5000字？！请收下我的膝盖！",
        "日产五千字...这是神仙级别的产出！",
    ],

    # 健康关怀
    "late_night": [
        "已经很晚了哦，注意休息~",
        "夜深了，眼睛会累的，休息一下吧",
        "虽然灵感来了挡不住，但身体也很重要！",
    ],
    "long_session": [
        "已经连续写了好久了，该休息一下眼睛了~",
        "适当休息效率更高哦~",
        "站起来活动一下吧，我等你回来~",
    ],
    "eye_break": [
        "看看窗外，让眼睛休息一下吧~",
        "20-20-20法则：每20分钟看20英尺外20秒！",
    ],

    # 创意提示
    "stuck_suggestion": [
        "试试从另一个角色的视角重新想想这个场景？",
        "如果时间线往前或往后移一点会怎样？",
        "这个场景最坏的结果是什么？最好的呢？",
        "角色最不想发生的事情是什么？让它发生！",
    ],
    "scene_start": [
        "新场景开始了！要从哪里切入呢？",
        "考虑一下这个场景的核心冲突是什么？",
    ],

    # 分析洞察
    "dialogue_heavy": [
        "这一段对话挺多的，要不要加点动作描写？",
        "对话很精彩！适当加点表情和动作会更生动~",
    ],
    "description_heavy": [
        "描写很细腻！也可以让角色动起来哦~",
        "环境铺垫很棒，是时候推进剧情了？",
    ],
    "emotion_flat": [
        "这一段情绪比较平，可以考虑加点波动？",
        "稳扎稳打挺好的，不过适当的冲突会更抓人~",
    ],
}

# 上下文感知提示
CONTEXT_TIPS = {
    "dialogue": [
        "写对话时，记得用动作和表情来增强表现力",
        "避免\"说\"字过多，可以用\"问\"\"喊\"\"低语\"等替换",
        "对话中的停顿和省略也是一种表达",
    ],
    "action": [
        "动作场景要注意节奏感，短句会更有力",
        "动作描写可以结合角色的心理活动",
        "记得照顾空间感，让读者知道角色在哪",
    ],
    "description": [
        "描写时可以调动多种感官：视觉、听觉、触觉...",
        "环境描写也可以反映角色的心情",
        "适当留白，给读者想象的空间",
    ],
    "emotion": [
        "展示而非叙述：用行为暗示情感比直接说更有力",
        "矛盾的情感往往更真实动人",
        "情感转变需要铺垫，不宜太突兀",
    ],
    "suspense": [
        "悬疑场景注意信息的释放节奏",
        "线索要公平地呈现给读者",
        "转折前的平静会让转折更有冲击力",
    ],
    "romance": [
        "甜蜜场景注意把握分寸",
        "暧昧的张力来自于\"差一点\"",
        "日常小细节往往比大场面更动人",
    ],
}


class ActivityTracker:
    """活动追踪器"""

    def __init__(self, window_size: int = 100):
        self.snapshots: deque = deque(maxlen=window_size)
        self.session_start = time.time()
        self.last_activity_time = time.time()
        self.total_words_session = 0
        self.last_word_count = 0

        # 编辑状态
        self.current_content: str = ""
        self.edit_history: deque = deque(maxlen=50)  # 最近的编辑

    def record_activity(self, event_type: str, word_count: int = 0,
                       module: str = "unknown", content: str = ""):
        """记录活动"""
        now = time.time()

        # 更新编辑历史
        if content and content != self.current_content:
            self.edit_history.append({
                "timestamp": now,
                "old_length": len(self.current_content),
                "new_length": len(content),
                "delta": len(content) - len(self.current_content)
            })
            self.current_content = content

        # 计算字数变化
        if word_count > self.last_word_count:
            self.total_words_session += word_count - self.last_word_count
        self.last_word_count = word_count

        snapshot = ActivitySnapshot(
            timestamp=now,
            event_count=len(self.snapshots) + 1,
            word_count=word_count,
            active_module=module,
            last_edit_time=now,
            is_typing=self._is_typing()
        )
        self.snapshots.append(snapshot)
        self.last_activity_time = now

    def _is_typing(self) -> bool:
        """判断是否正在打字"""
        if len(self.edit_history) < 2:
            return False

        recent = list(self.edit_history)[-5:]
        if not recent:
            return False

        # 最近5次编辑的时间跨度
        time_span = recent[-1]["timestamp"] - recent[0]["timestamp"]
        if time_span < 30:  # 30秒内有多次编辑
            return True

        return False

    def get_idle_duration(self) -> float:
        """获取空闲时长（秒）"""
        return time.time() - self.last_activity_time

    def get_session_duration(self) -> float:
        """获取会话时长（秒）"""
        return time.time() - self.session_start

    def get_recent_activity_rate(self, window_seconds: float = 300) -> float:
        """获取最近的活动率（每分钟事件数）"""
        now = time.time()
        cutoff = now - window_seconds

        recent = [s for s in self.snapshots if s.timestamp > cutoff]
        if not recent:
            return 0.0

        return len(recent) / (window_seconds / 60)

    def detect_revision_loop(self) -> bool:
        """检测是否在反复修改同一段"""
        if len(self.edit_history) < 10:
            return False

        recent = list(self.edit_history)[-10:]

        # 检查是否有多次小幅度的增删
        small_edits = sum(1 for e in recent if abs(e["delta"]) < 20)
        if small_edits > 7:
            return True

        # 检查是否在来回增删
        deltas = [e["delta"] for e in recent]
        sign_changes = sum(1 for i in range(1, len(deltas))
                         if deltas[i] * deltas[i-1] < 0)
        if sign_changes > 5:
            return True

        return False

    def get_writing_momentum(self) -> str:
        """获取写作势头"""
        if len(self.edit_history) < 5:
            return "starting"

        recent = list(self.edit_history)[-10:]
        total_delta = sum(e["delta"] for e in recent)
        time_span = recent[-1]["timestamp"] - recent[0]["timestamp"]

        if time_span == 0:
            return "burst"

        wpm = (total_delta / time_span) * 60  # 每分钟字数

        if wpm > 60:
            return "blazing"
        elif wpm > 30:
            return "flowing"
        elif wpm > 10:
            return "steady"
        elif wpm > 0:
            return "slow"
        else:
            return "stuck"


class ContextAnalyzer:
    """上下文分析器"""

    def __init__(self):
        self.current_context: Dict[str, Any] = {}

    def analyze_current_content(self, content: str,
                               cursor_position: int = -1) -> Dict[str, Any]:
        """
        分析当前编辑内容的上下文

        Args:
            content: 当前内容
            cursor_position: 光标位置 (-1 表示末尾)

        Returns:
            上下文信息
        """
        if cursor_position < 0:
            cursor_position = len(content)

        context = {
            "total_length": len(content),
            "cursor_position": cursor_position,
            "content_type": "unknown",
            "recent_text": "",
            "suggestions": []
        }

        if not content:
            return context

        # 获取光标附近的文本
        start = max(0, cursor_position - 200)
        end = min(len(content), cursor_position + 100)
        context["recent_text"] = content[start:end]

        # 分析内容类型
        context["content_type"] = self._detect_content_type(context["recent_text"])

        # 获取相关提示
        context["suggestions"] = self._get_context_suggestions(context["content_type"])

        self.current_context = context
        return context

    def _detect_content_type(self, text: str) -> str:
        """检测内容类型"""
        if not text:
            return "unknown"

        # 对话检测
        dialogue_pattern = re.compile(r'[""「」『』]|说|问|道')
        if len(dialogue_pattern.findall(text)) > 2:
            return "dialogue"

        # 动作检测
        action_keywords = ["走", "跑", "跳", "打", "拿", "转身", "站", "坐"]
        if sum(text.count(kw) for kw in action_keywords) > 3:
            return "action"

        # 描写检测
        desc_keywords = ["如同", "仿佛", "像", "般", "是", "有"]
        if sum(text.count(kw) for kw in desc_keywords) > 3:
            return "description"

        # 情感检测
        emotion_keywords = ["心", "感", "想", "觉得", "认为"]
        if sum(text.count(kw) for kw in emotion_keywords) > 2:
            return "emotion"

        return "narrative"

    def _get_context_suggestions(self, content_type: str) -> List[str]:
        """获取上下文相关建议"""
        tips = CONTEXT_TIPS.get(content_type, [])
        if tips:
            return random.sample(tips, min(2, len(tips)))
        return []

    def detect_genre_context(self, content: str, project_type: str,
                             genre_tags: Optional[List[str]] = None,
                             enabled_tools: Optional[List[str]] = None) -> str:
        """检测题材相关上下文"""
        tags = set(genre_tags or [])
        tools = set(enabled_tools or [])

        suspense_enabled = (
            "Suspense" in tags
            or "Horror" in tags
            or "evidence_board" in tools
            or "dual_timeline" in tools
            or "alibi" in tools
        )
        romance_enabled = "Romance" in tags or "heartbeat" in tools

        if suspense_enabled:
            if any(kw in content for kw in ["线索", "证据", "真相", "谜"]):
                return "suspense"
        if romance_enabled:
            if any(kw in content for kw in ["心跳", "脸红", "目光", "微笑"]):
                return "romance"

        return "general"


class ProactiveInterventionSystem:
    """主动干预系统"""

    def __init__(self, preference_tracker=None, data_dir: Optional[str] = None):
        self.activity_tracker = ActivityTracker()
        self.context_analyzer = ContextAnalyzer()
        self.preference_tracker = preference_tracker

        # 干预队列
        self.pending_interventions: List[InterventionOpportunity] = []

        # 冷却时间
        self.cooldowns: Dict[str, float] = {}
        self.last_intervention_time = 0.0

        # 配置
        self.min_intervention_gap = 300  # 最少5分钟间隔
        self.idle_threshold = 180  # 3分钟无活动视为空闲
        self.long_session_threshold = 3600  # 1小时为长会话

        # 里程碑追踪
        self.achieved_milestones: set = set()

    def check_opportunities(self, context: Dict[str, Any] = None) -> Optional[InterventionOpportunity]:
        """
        检查干预机会

        Args:
            context: 当前上下文

        Returns:
            如果有合适的干预机会，返回干预对象
        """
        context = context or {}
        now = time.time()

        # 检查冷却
        if now - self.last_intervention_time < self.min_intervention_gap:
            # 只允许高优先级干预
            return self._get_high_priority_intervention()

        opportunities = []

        # 1. 空闲检测
        idle_duration = self.activity_tracker.get_idle_duration()
        if idle_duration > self.idle_threshold:
            opp = self._check_idle_intervention(idle_duration)
            if opp:
                opportunities.append(opp)

        # 2. 健康关怀
        health_opp = self._check_health_intervention()
        if health_opp:
            opportunities.append(health_opp)

        # 3. 里程碑检测
        milestone_opp = self._check_milestone_intervention()
        if milestone_opp:
            opportunities.append(milestone_opp)

        # 4. 写作势头反馈
        momentum_opp = self._check_momentum_intervention()
        if momentum_opp:
            opportunities.append(momentum_opp)

        # 5. 修改循环检测
        if self.activity_tracker.detect_revision_loop():
            opp = self._create_intervention(
                InterventionType.SUGGESTION,
                InterventionPriority.MEDIUM,
                random.choice(INTERVENTION_MESSAGES["stuck_suggestion"]),
                context={"reason": "revision_loop"}
            )
            opportunities.append(opp)

        # 6. 上下文提示
        content_context = context.get("current_content_context", {})
        if content_context.get("suggestions"):
            for suggestion in content_context["suggestions"][:1]:
                opp = self._create_intervention(
                    InterventionType.CONTEXT_TIP,
                    InterventionPriority.LOW,
                    suggestion,
                    context=content_context
                )
                opportunities.append(opp)

        # 选择最佳干预
        return self._select_best_intervention(opportunities)

    def _check_idle_intervention(self, idle_duration: float) -> Optional[InterventionOpportunity]:
        """检查空闲干预"""
        if self._is_cooled_down("idle"):
            return None

        if idle_duration > 600:  # 10分钟
            messages = INTERVENTION_MESSAGES["idle_long"]
        else:
            messages = INTERVENTION_MESSAGES["idle_gentle"]

        return self._create_intervention(
            InterventionType.GENTLE_REMINDER,
            InterventionPriority.LOW,
            random.choice(messages),
            context={"idle_duration": idle_duration}
        )

    def _check_health_intervention(self) -> Optional[InterventionOpportunity]:
        """检查健康干预"""
        now = datetime.now()

        # 深夜检查
        if 23 <= now.hour or now.hour <= 4:
            if not self._is_cooled_down("late_night", 7200):  # 2小时冷却
                return self._create_intervention(
                    InterventionType.HEALTH_CHECK,
                    InterventionPriority.MEDIUM,
                    random.choice(INTERVENTION_MESSAGES["late_night"]),
                    context={"hour": now.hour}
                )

        # 长时间会话检查
        session_duration = self.activity_tracker.get_session_duration()
        if session_duration > self.long_session_threshold:
            if not self._is_cooled_down("long_session", 1800):  # 30分钟冷却
                return self._create_intervention(
                    InterventionType.HEALTH_CHECK,
                    InterventionPriority.MEDIUM,
                    random.choice(INTERVENTION_MESSAGES["long_session"]),
                    context={"session_duration": session_duration}
                )

        return None

    def _check_milestone_intervention(self) -> Optional[InterventionOpportunity]:
        """检查里程碑干预"""
        words = self.activity_tracker.total_words_session

        milestones = [
            (5000, "word_count_5000"),
            (2000, "word_count_2000"),
            (1000, "word_count_1000"),
            (500, "word_count_500"),
        ]

        for threshold, key in milestones:
            if words >= threshold and key not in self.achieved_milestones:
                self.achieved_milestones.add(key)
                return self._create_intervention(
                    InterventionType.MILESTONE,
                    InterventionPriority.HIGH,
                    random.choice(INTERVENTION_MESSAGES[key]),
                    context={"words": words, "milestone": key}
                )

        return None

    def _check_momentum_intervention(self) -> Optional[InterventionOpportunity]:
        """检查势头干预"""
        momentum = self.activity_tracker.get_writing_momentum()

        if momentum in ["blazing", "flowing"]:
            if not self._is_cooled_down("momentum", 900):  # 15分钟冷却
                return self._create_intervention(
                    InterventionType.ENCOURAGEMENT,
                    InterventionPriority.LOW,
                    random.choice(INTERVENTION_MESSAGES["writing_momentum"]),
                    context={"momentum": momentum}
                )

        return None

    def _create_intervention(self, itype: InterventionType,
                            priority: InterventionPriority,
                            message: str,
                            context: Dict = None,
                            action: str = None) -> InterventionOpportunity:
        """创建干预对象"""
        return InterventionOpportunity(
            intervention_type=itype,
            priority=priority,
            message=message,
            context=context or {},
            action=action,
            expires_at=time.time() + 300  # 5分钟后过期
        )

    def _select_best_intervention(self,
                                  opportunities: List[InterventionOpportunity]
                                  ) -> Optional[InterventionOpportunity]:
        """选择最佳干预"""
        if not opportunities:
            return None

        # 过滤过期的
        now = time.time()
        valid = [o for o in opportunities if o.expires_at > now]

        if not valid:
            return None

        # 按优先级排序
        valid.sort(key=lambda x: x.priority.value, reverse=True)

        # 考虑用户偏好
        if self.preference_tracker:
            prefs = self.preference_tracker.preferences
            if prefs.likes_proactive < 0.3:
                # 用户不喜欢主动干预，只选择高优先级
                valid = [o for o in valid if o.priority.value >= InterventionPriority.HIGH.value]

        selected = valid[0] if valid else None

        if selected:
            self.last_intervention_time = now
            # 设置冷却
            type_key = selected.intervention_type.value
            self.cooldowns[type_key] = now

        return selected

    def _get_high_priority_intervention(self) -> Optional[InterventionOpportunity]:
        """获取高优先级干预（用于冷却期间）"""
        valid = [o for o in self.pending_interventions
                if o.priority.value >= InterventionPriority.HIGH.value
                and o.expires_at > time.time()]

        if valid:
            return valid[0]
        return None

    def _is_cooled_down(self, key: str, cooldown: float = 600) -> bool:
        """检查是否在冷却中"""
        last_time = self.cooldowns.get(key, 0)
        return time.time() - last_time < cooldown

    def record_activity(self, event_type: str, word_count: int = 0,
                       module: str = "unknown", content: str = ""):
        """记录活动"""
        self.activity_tracker.record_activity(event_type, word_count, module, content)

    def get_context_tip(self, content: str, cursor_position: int = -1) -> Optional[str]:
        """获取上下文提示"""
        context = self.context_analyzer.analyze_current_content(content, cursor_position)
        tips = context.get("suggestions", [])
        return tips[0] if tips else None

    def reset_session(self):
        """重置会话"""
        self.activity_tracker = ActivityTracker()
        self.achieved_milestones.clear()


class ContextAwareFeedback:
    """上下文感知反馈系统"""

    def __init__(self, proactive_system: ProactiveInterventionSystem):
        self.proactive = proactive_system
        self.context_analyzer = ContextAnalyzer()

    def get_contextual_feedback(self, content: str, project_type: str = "General",
                                cursor_position: int = -1,
                                genre_tags: Optional[List[str]] = None,
                                enabled_tools: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        获取基于当前编辑上下文的反馈

        Args:
            content: 当前内容
            project_type: 项目类型
            cursor_position: 光标位置

        Returns:
            反馈信息或 None
        """
        if not content or len(content) < 50:
            return None

        context = self.context_analyzer.analyze_current_content(content, cursor_position)
        content_type = context.get("content_type", "unknown")

        # 获取题材相关上下文
        genre_context = self.context_analyzer.detect_genre_context(
            content,
            project_type,
            genre_tags=genre_tags,
            enabled_tools=enabled_tools
        )

        # 组合反馈
        feedback = {
            "content_type": content_type,
            "genre_context": genre_context,
            "tips": [],
            "warnings": []
        }

        # 添加类型特定提示
        tips = CONTEXT_TIPS.get(content_type, [])
        if tips:
            feedback["tips"].append(random.choice(tips))

        # 添加题材特定提示
        genre_tips = CONTEXT_TIPS.get(genre_context, [])
        if genre_tips and genre_context != "general":
            feedback["tips"].append(random.choice(genre_tips))

        # 检测潜在问题
        warnings = self._detect_issues(content, content_type)
        feedback["warnings"] = warnings

        return feedback if feedback["tips"] or feedback["warnings"] else None

    def _detect_issues(self, content: str, content_type: str) -> List[str]:
        """检测内容问题"""
        warnings = []

        # 检测对话标点问题
        if content_type == "dialogue":
            if content.count('"') % 2 != 0:
                warnings.append("对话引号可能未闭合")
            if content.count("“") != content.count("”") or content.count("「") != content.count("」"):
                warnings.append("中文引号可能未闭合")

        # 检测重复词
        words = content[-200:].split()
        if len(words) > 10:
            from collections import Counter
            word_counts = Counter(words)
            for word, count in word_counts.most_common(3):
                if count > 5 and len(word) > 1:
                    warnings.append(f"「{word}」在最近内容中出现较多")

        return warnings[:2]  # 限制警告数量

    def get_genre_specific_prompt(self, project_type: str) -> Optional[str]:
        """获取题材特定的创意提示"""
        prompts = {
            "Suspense": [
                "悬疑的关键是公平地给读者线索",
                "每个角色都可能有隐藏的动机",
                "时间线是推理的关键",
            ],
            "Horror": [
                "恐惧来自于未知和等待",
                "日常中的异常最令人不安",
                "心理恐惧比血腥更持久",
            ],
            "Romance": [
                "让角色慢慢靠近，欲擒故纵",
                "小细节比大场面更动人",
                "误会要适度，沟通也是浪漫",
            ],
            "Fantasy": [
                "魔法要有代价，能力要有限制",
                "世界观要自洽",
                "平凡人在奇幻世界中的反应更有代入感",
            ],
            "SciFi": [
                "科技改变的是生活方式，不变的是人性",
                "硬科幻需要逻辑自洽",
                "未来世界也需要日常细节",
            ],
        }

        genre_prompts = prompts.get(project_type, [])
        return random.choice(genre_prompts) if genre_prompts else None
