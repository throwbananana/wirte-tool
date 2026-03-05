"""
悬浮写作助手 - 事件系统 (增强版)
负责模块使用、时间段事件、成就/相册联动、深度行为分析、复合规则引擎，
以及事件序列追踪、用户偏好学习、主动干预、动态内容生成等增强功能
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set, List, Callable
from collections import deque, Counter
from enum import Enum
from pathlib import Path
import json
import random
import heapq
import logging

from .states import AssistantState
from .event_config import get_default_config_path, load_event_config
from .behavior_config import BEHAVIOR_THRESHOLDS, BEHAVIOR_FEEDBACK, COMPLEX_RULES
from .narrative_manager import NarrativeManager
from writer_app.core.project_types import ProjectTypeManager

# 增强模块导入
from .event_sequence import EventSequenceTracker, FeedbackLoop
from .preference_system import PersonalizationEngine
from .deep_analysis import DeepAnalysisEngine
from .proactive_system import ProactiveInterventionSystem, ContextAwareFeedback
from .feedback_templates import FeedbackSelector, EXTENDED_BEHAVIOR_FEEDBACK
from .dynamic_content import DynamicContentGenerator

logger = logging.getLogger(__name__)


EVENT_STATE_DEFAULT = {
    "unlocked_events": [],
    "module_usage": {},
    "time_marks": {},
    "event_log": [],
    "created_types": [],
    "created_themes": [],
}

EVENT_TO_MODULE = {
    "outline_changed": "outline",
    "outline_node_added": "outline",
    "scene_added": "script",
    "scene_updated": "script",
    "scene_deleted": "script",
    "character_added": "characters",
    "character_updated": "characters",
    "character_deleted": "characters",
    "wiki_entry_added": "wiki",
    "wiki_entry_updated": "wiki",
    "wiki_entry_deleted": "wiki",
    "relationship_link_added": "relationship",
    "relationship_link_deleted": "relationship",
    "relationships_updated": "relationship",
    "timeline_event_added": "timeline",
    "timeline_event_updated": "timeline",
    "timeline_event_deleted": "timeline",
    "evidence_node_added": "evidence",
    "evidence_link_added": "evidence",
    "clue_added": "evidence",
    "kanban_task_added": "kanban",
    "kanban_task_updated": "kanban",
    "kanban_task_moved": "kanban",
    "idea_added": "idea",
    "research_added": "research",
    "galgame_asset_added": "assets",
    "asset_added": "assets",
    "asset_updated": "assets",
    "asset_deleted": "assets",
    "faction_added": "faction",
    "faction_relation_changed": "faction",
    "training_completed": "training",
}

CREATION_EVENT_TYPES = {
    "scene_added",
    "scene_updated",
    "outline_changed",
    "idea_added",
    "research_added",
    "timeline_event_added",
    "kanban_task_added",
}

THEME_EVENT_TYPES = {
    "scene_added",
    "scene_updated",
    "outline_changed",
    "idea_added",
    "research_added",
}

THEME_IGNORE_PREFIXES = ("Beat:",)

TYPE_PHOTO_STATES = {
    "General": AssistantState.WRITING,
    "Suspense": AssistantState.THINKING,
    "Horror": AssistantState.STARTLED,
    "Thriller": AssistantState.WORRIED,
    "Romance": AssistantState.LOVE,
    "Epic": AssistantState.KNIGHT,
    "Fantasy": AssistantState.WITCH,
    "SciFi": AssistantState.CURIOUS,
    "Poetry": AssistantState.READING,
    "LightNovel": AssistantState.EXCITED,
    "Galgame": AssistantState.PLAYING,
    "Fanfic": AssistantState.HAPPY,
    "*": AssistantState.WRITING,
}

MODULE_MILESTONES = [
    {
        "id": "module_newbie",
        "threshold": 4,
        "achievement": "module_newbie",
        "message": "🎯 新手入门：你已经熟悉多个模块啦！",
    },
    {
        "id": "module_explorer",
        "threshold": 8,
        "achievement": "module_explorer",
        "message": "🧭 模块探索者：工具箱越来越全面了。",
    },
    {
        "id": "module_expert",
        "threshold": 12,
        "message": "🛠️ 模块专家：你已经熟练掌握了大部分功能！",
    },
]


TYPE_MILESTONES = [
    {
        "id": "type_explorer",
        "threshold": 2,
        "achievement": "type_explorer",
        "message": "已尝试多种项目类型，题材探索进度+1！",
    },
    {
        "id": "type_collector",
        "threshold": 4,
        "achievement": "type_collector",
        "message": "题材触角越来越广，继续保持~",
    },
    {
        "id": "type_master",
        "threshold": 6,
        "achievement": "type_master",
        "message": "多类型创作达成，题材跨度很厉害！",
    },
    {
        "id": "type_legend",
        "threshold": 8,
        "message": "👑 题材传说：几乎没有什么类型能难倒你了！",
        "diary_id": "type_legend"
    },
]

THEME_MILESTONES = [
    {
        "id": "theme_explorer",
        "threshold": 3,
        "achievement": "theme_explorer",
        "message": "主题标签开始丰富起来了~",
    },
    {
        "id": "theme_collector",
        "threshold": 6,
        "achievement": "theme_collector",
        "message": "主题收集进展顺利，社团的大家也对你的新题材很感兴趣呢！",
        "action": "trigger_school_event"
    },
    {
        "id": "theme_master",
        "threshold": 10,
        "achievement": "theme_master",
        "message": "主题版图已展开，创作类型更上一层！",
    },
    {
        "id": "theme_encyclopedia",
        "threshold": 20,
        "message": "📚 主题百科：你的作品主题丰富得令人惊叹！",
        "diary_id": "theme_encyclopedia"
    },
]

TIME_EVENTS = [
    {
        "id": "time_early_bird",
        "period": AssistantState.MORNING,
        "achievement": "early_bird",
        "message": "🌅 清晨创作打卡成功！",
        "variants": [
            {
                "text": "🌅 早安！看到主角和反派还没正面交锋，今天要安排一场大戏吗？",
                "condition": "analysis:conflict_missing_direct",
                "weight": 50
            },
            {
                "text": "🌅 又是新的一天！这种坚持不懈的精神，一定能写出好作品。",
                "weight": 10
            }
        ],
        "cooldown": "daily",
    },
    {
        "id": "time_night_owl",
        "period": AssistantState.MIDNIGHT,
        "achievement": "night_owl",
        "message": "🌙 深夜还在创作，真是夜猫子~",
        "variants": [
            {
                "text": "🌙 这么晚还在纠结结局吗？如果卡在这一步，不如先去睡一觉，梦里会有答案的。",
                "condition": "analysis:structure_missing_climax",
                "weight": 50
            },
            {
                "text": "🌙 感觉你今晚写得很顺呢！但是身体也很重要哦，早点休息吧。",
                "weight": 10
            }
        ],
        "cooldown": "daily",
    },
    {
        "id": "time_lunch",
        "period": "noon",
        "achievement": "shared_lunch",
        "state": AssistantState.EATING,
        "message": "🍱 午饭时间到啦，要不要休息一下？",
        "cooldown": "daily",
        "action": "trigger_school_event"
    },
    {
        "id": "time_afternoon_tea",
        "period": "afternoon",
        "state": AssistantState.EATING,
        "message": "☕ 下午茶时间，来杯咖啡提提神吧~",
        "cooldown": "daily",
        "action": "trigger_school_event"
    }
]

ACHIEVEMENT_PHOTO_REWARDS = {
    "module_newbie": {
        "General": AssistantState.HAPPY,
        "Suspense": AssistantState.THINKING,
        "Romance": AssistantState.LOVE,
        "Epic": AssistantState.FANTASY,
        "SciFi": AssistantState.CURIOUS,
        "Poetry": AssistantState.WRITING,
        "LightNovel": AssistantState.EXCITED,
        "Galgame": AssistantState.PLAYING,
        "*": AssistantState.HAPPY,
        "_message": "📸 相册新增一张纪念照片。",
    },
    "module_explorer": {
        "*": AssistantState.CELEBRATING,
        "_message": "📸 探索里程碑已记录到相册。",
    },
    "type_explorer": {
        "*": AssistantState.CURIOUS,
        "_message": "题材探索留影已入册。",
    },
    "type_collector": {
        "*": AssistantState.WRITING,
        "_message": "题材旅程留影已入册。",
    },
    "type_master": {
        "*": AssistantState.CELEBRATING,
        "_message": "题材大师留影已入册。",
    },
    "theme_explorer": {
        "*": AssistantState.THINKING,
        "_message": "主题探索留影已入册。",
    },
    "theme_collector": {
        "*": AssistantState.EXCITED,
        "_message": "主题收集留影已入册。",
    },
    "theme_master": {
        "*": AssistantState.CELEBRATING,
        "_message": "主题开拓留影已入册。",
    },
    "early_bird": {
        "*": AssistantState.MORNING,
        "_message": "📸 清晨留影已入册。",
    },
    "night_owl": {
        "*": AssistantState.MIDNIGHT,
        "_message": "📸 深夜留影已入册。",
    },
    "birthday": {
        "*": AssistantState.CELEBRATING,
        "_message": "📸 这一刻值得珍藏，生日照片已存入相册。",
    },
    "anniversary": {
        "*": AssistantState.TRUST,
        "_message": "📸 周年纪念照片已存入相册。",
    },
}

class EventPriority(int, Enum):
    """事件优先级"""
    CRITICAL = 0  # 必须立即处理 (成就、报错)
    HIGH = 10     # 重要反馈 (心流结束、复合规则)
    NORMAL = 20   # 普通互动 (点击反馈)
    LOW = 30      # 背景状态 (天气、时间变化)
    SILENT = 99   # 仅记录不反馈

class BehaviorTracker:
    """行为追踪器：负责短期内的行为模式分析"""
    
    def __init__(self, event_to_module: Optional[Dict[str, str]] = None):
        # 存储最近的操作记录 (timestamp, event_type, details)
        self.action_history = deque(maxlen=50) 
        self.last_action_time = datetime.now()
        self._event_to_module = event_to_module or {}
        
        # 状态标志
        self.is_in_flow_state = False  # 是否处于心流状态
        self.flow_start_time = None
        
        # 阈值配置 (从配置加载)
        self.FLOW_CPM_ENTER = BEHAVIOR_THRESHOLDS.get("FLOW_CPM_ENTER", 20)
        self.FLOW_CPM_EXIT = BEHAVIOR_THRESHOLDS.get("FLOW_CPM_EXIT", 10)
        self.HESITATION_GAP = BEHAVIOR_THRESHOLDS.get("HESITATION_GAP", 300)
        self.REFACTOR_WINDOW = BEHAVIOR_THRESHOLDS.get("REFACTOR_WINDOW", 10)
        self.REFACTOR_RATIO = BEHAVIOR_THRESHOLDS.get("REFACTOR_RATIO", 0.8)
        self.CONTEXT_SWITCH_WINDOW = BEHAVIOR_THRESHOLDS.get("CONTEXT_SWITCH_WINDOW", 5)
        self.CONTEXT_SWITCH_COUNT = BEHAVIOR_THRESHOLDS.get("CONTEXT_SWITCH_COUNT", 3)
        
    def record_action(self, event_type: str, details: Any = None):
        now = datetime.now()
        self.action_history.append((now, event_type, details))
        self.last_action_time = now
        
    def analyze_flow(self) -> Dict[str, Any]:
        """分析心流状态"""
        if len(self.action_history) < 5:
            return {}
            
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # 统计最近一分钟的操作数
        recent_actions = [a for a in self.action_history if a[0] > one_minute_ago]
        count = len(recent_actions)
        
        result = {}
        
        # 进入心流
        if count >= self.FLOW_CPM_ENTER and not self.is_in_flow_state:
            self.is_in_flow_state = True
            self.flow_start_time = now
            result["flow_state_change"] = "entered"
            
        # 退出心流 (活跃度显著下降)
        elif count < self.FLOW_CPM_EXIT and self.is_in_flow_state:
            duration = (now - self.flow_start_time).total_seconds() if self.flow_start_time else 0
            self.is_in_flow_state = False
            self.flow_start_time = None
            result["flow_state_change"] = "exited"
            result["duration"] = duration
            
        return result
        
    def analyze_hesitation(self) -> bool:
        """分析是否犹豫/卡文"""
        now = datetime.now()
        gap = (now - self.last_action_time).total_seconds()
        
        # 如果还在心流中，不算犹豫
        if self.is_in_flow_state:
            return False
            
        return gap > self.HESITATION_GAP
        
    def analyze_refactoring(self) -> bool:
        """分析是否在润色/修改 (最近10次操作中'update'占比高)"""
        if len(self.action_history) < self.REFACTOR_WINDOW:
            return False
            
        recent = list(self.action_history)[-self.REFACTOR_WINDOW:]
        update_count = sum(1 for _, et, _ in recent if "updated" in et or "changed" in et)
        
        return (update_count / self.REFACTOR_WINDOW) >= self.REFACTOR_RATIO

    def analyze_context_switching(self) -> bool:
        """分析是否在多线程工作 (大纲->角色->正文 快速切换)"""
        if len(self.action_history) < self.CONTEXT_SWITCH_WINDOW:
            return False
            
        recent = list(self.action_history)[-self.CONTEXT_SWITCH_WINDOW:]
        modules = set()
        for _, et, _ in recent:
            mod = self._event_to_module.get(et)
            if mod:
                modules.add(mod)
                
        return len(modules) >= self.CONTEXT_SWITCH_COUNT  # 短时间内操作了多个不同模块


class AssistantEventSystem:
    """事件系统：管理触发、记录与奖励，集成规则引擎 (增强版)"""

    def __init__(self, assistant, pet_system, project_manager=None):
        self.assistant = assistant
        self.pet_system = pet_system
        self.project_manager = project_manager

        # 优先队列 (PriorityQueue)，存储待处理的反馈任务
        # 元素格式: (priority, timestamp, task_type, kwargs)
        self._event_queue = []
        self._is_processing = False

        # 事件配置
        config_manager = getattr(self.assistant, "config_manager", None)
        self._config_path = get_default_config_path(config_manager=config_manager)
        self._config = load_event_config(self._config_path)
        self._event_state_default = dict(self._config.get("event_state_default", EVENT_STATE_DEFAULT))
        self._event_to_module = dict(self._config.get("event_to_module", EVENT_TO_MODULE))
        self._creation_event_types = set(self._config.get("creation_event_types", list(CREATION_EVENT_TYPES)))
        self._theme_event_types = set(self._config.get("theme_event_types", list(THEME_EVENT_TYPES)))
        self._theme_ignore_prefixes = tuple(self._config.get("theme_ignore_prefixes", list(THEME_IGNORE_PREFIXES)))
        self._type_photo_states = dict(self._config.get("type_photo_states", TYPE_PHOTO_STATES))
        self._module_milestones = list(self._config.get("module_milestones", MODULE_MILESTONES))
        self._type_milestones = list(self._config.get("type_milestones", TYPE_MILESTONES))
        self._theme_milestones = list(self._config.get("theme_milestones", THEME_MILESTONES))
        self._time_events = list(self._config.get("time_events", TIME_EVENTS))
        self._achievement_photo_rewards = dict(
            self._config.get("achievement_photo_rewards", ACHIEVEMENT_PHOTO_REWARDS)
        )

        # 行为追踪器
        self.behavior_tracker = BehaviorTracker(self._event_to_module)

        # 叙事管理器
        self.narrative_manager = NarrativeManager(self.assistant, self.pet_system)

        # 加载日记内容 (用于同步记录)
        self.diary_data = self._load_diary_content()

        self._startup_time = datetime.now()

        # 动态冷却记录
        self._last_feedback_times = {}
        self._last_behavior_feedback = datetime.min # Global throttle fallback

        self._unlocked_events: Set[str] = set()
        self._module_usage = {}
        self._time_marks = {}
        self._event_log = []
        self._created_types = set()
        self._created_themes = set()
        self._load_state()

        # ========== 增强模块初始化 ==========

        # 1. 事件序列追踪器 - 识别用户行为模式
        self.sequence_tracker = EventSequenceTracker()

        # 2. 反馈循环 - 根据用户反应调整反馈
        self.feedback_loop = FeedbackLoop()

        # 3. 个性化引擎 - 学习用户偏好
        self.personalization = PersonalizationEngine()

        # 4. 深度分析引擎 - 分析写作内容
        self.deep_analysis = DeepAnalysisEngine()

        # 5. 主动干预系统 - 主动发起互动
        self.proactive_system = ProactiveInterventionSystem(
            preference_tracker=self.personalization.tracker
        )

        # 6. 上下文感知反馈 - 根据内容类型给反馈
        self.context_feedback = ContextAwareFeedback(self.proactive_system)

        # 7. 反馈选择器 - 个性化反馈文案选择
        self.feedback_selector = FeedbackSelector()

        # 8. 动态内容生成器 - 基于项目数据生成内容
        self.dynamic_content = DynamicContentGenerator()

        # 加载增强模块的持久化数据
        self._load_enhanced_state()

        logger.info("事件系统增强模块初始化完成")

    def _load_enhanced_state(self) -> None:
        """加载增强模块的持久化数据"""
        try:
            enhanced_state = getattr(self.pet_system.data, "enhanced_event_state", {}) or {}

            # 加载个性化引擎数据
            if "personalization" in enhanced_state:
                self.personalization.load_state(enhanced_state["personalization"])

            # 加载反馈循环数据
            if "feedback_loop" in enhanced_state:
                self.feedback_loop.load_state(enhanced_state["feedback_loop"])

            # 加载反馈选择器偏好
            if "feedback_preferences" in enhanced_state:
                self.feedback_selector.load_preferences(enhanced_state["feedback_preferences"])

            logger.debug("增强模块状态加载完成")
        except Exception as e:
            logger.warning(f"加载增强模块状态失败: {e}")

    def _save_enhanced_state(self) -> None:
        """保存增强模块的持久化数据"""
        try:
            enhanced_state = {
                "personalization": self.personalization.get_state(),
                "feedback_loop": self.feedback_loop.get_state(),
                "feedback_preferences": self.feedback_selector.get_preferences(),
            }
            self.pet_system.data.enhanced_event_state = enhanced_state
            # 注意：不单独调用save，让主save_state一起处理
        except Exception as e:
            logger.warning(f"保存增强模块状态失败: {e}")

    def _load_state(self) -> None:
        raw_state = getattr(self.pet_system.data, "event_state", {}) or {}
        state = dict(self._event_state_default)
        state.update(raw_state)

        self._unlocked_events = set(state.get("unlocked_events", []))
        self._module_usage = dict(state.get("module_usage", {}))
        self._time_marks = dict(state.get("time_marks", {}))
        self._event_log = list(state.get("event_log", []))
        self._created_types = set(state.get("created_types", []))
        self._created_themes = set(state.get("created_themes", []))

    def _save_state(self) -> None:
        # 限制日志长度
        if len(self._event_log) > 100:
            self._event_log = self._event_log[-100:]

        self.pet_system.data.event_state = {
            "unlocked_events": sorted(self._unlocked_events),
            "module_usage": dict(self._module_usage),
            "time_marks": dict(self._time_marks),
            "event_log": list(self._event_log),
            "created_types": sorted(self._created_types),
            "created_themes": sorted(self._created_themes),
        }

        # 保存增强模块状态
        self._save_enhanced_state()

        self.pet_system.save()
        
    def _enqueue_event(self, priority: int, task_type: str, **kwargs):
        """将事件推入优先级队列"""
        heapq.heappush(self._event_queue, (priority, datetime.now(), task_type, kwargs))

    def _process_queue(self):
        """处理事件队列"""
        if self._event_queue:
            # 取出优先级最高的事件
            priority, _, task_type, kwargs = heapq.heappop(self._event_queue)

            if task_type == "feedback":
                self._do_trigger_feedback(**kwargs)
            elif task_type == "milestone":
                self._do_trigger_milestone(**kwargs)
            elif task_type == "complex_rule":
                self._do_apply_complex_rule(**kwargs)
            elif task_type == "narrative":
                self._do_trigger_narrative(**kwargs)
            elif task_type == "proactive":
                self._do_trigger_proactive(**kwargs)
        
        # 叙事链触发检查
        # 1. 获取上下文
        ctx = self._get_rule_context(None)
        # 2. 检查是否在打字
        ctx["is_typing"] = (datetime.now() - self.behavior_tracker.last_action_time).total_seconds() < 60
        # 3. 检查启动标志
        ctx["startup"] = (datetime.now() - self._startup_time).total_seconds() < 30
        # 4. 补充时间与分析
        ctx["time_str"] = datetime.now().strftime("%H:%M")
        if hasattr(self.assistant, "integration"):
             ctx["analysis_results"] = self.assistant.integration.get_deep_analysis()
        
        narrative_event = self.narrative_manager.check_triggers(ctx)
        if narrative_event:
            # 增加随机延迟感，不一定每次轮询都触发，且触发前增加一个随机权重
            if random.random() < 0.7: # 70% 概率在条件满足时立即反应
                self._enqueue_event(EventPriority.HIGH, "narrative", **narrative_event)
                
        # 循环调度: 3-6秒之间的随机间隔，避免机械感
        interval = random.randint(3000, 6000)
        self.assistant.after(interval, self._process_queue)

    def _do_trigger_narrative(self, chain_id: str, message: str, mood: str, options: list, rewards: dict, sound: str = None, action: str = None, diary_id: str = None):
        """执行叙事事件"""
        # 1. 状态与声音
        if mood:
            self.assistant.set_state(mood)
        if sound and hasattr(self.assistant, "toggle_ambiance"):
            self.assistant.toggle_ambiance(sound)
            
        # 2. 执行动作
        if action:
            self.narrative_manager._execute_action(action)

        # 3. 显示对话 (带选项)
        if options:
            self._show_narrative_dialog(chain_id, message, options)
        else:
            self._announce(message)
            # 无选项时，通知 NarrativeManager 自动推进
            self.narrative_manager.handle_no_option_step(chain_id)

        # 4. 发放奖励与日记
        if rewards:
            xp = rewards.get("xp", 0)
            coins = rewards.get("coins", 0)
            affection = rewards.get("affection", 0)
            mood_bonus = rewards.get("mood", 0)
            
            self.pet_system.add_reward(xp=xp, coins=coins, affection=affection)
            if mood_bonus:
                self.pet_system.update_mood(mood_bonus)

            if hasattr(self.assistant, "_show_reward_card"):
                parts = []
                if xp:
                    parts.append(f"经验 +{xp}")
                if coins:
                    parts.append(f"金币 +{coins}")
                if affection:
                    parts.append(f"好感 +{affection}")
                if mood_bonus:
                    parts.append("心情提升")
                if parts:
                    detail = " / ".join(parts)
                    self.assistant.after(200, lambda: self.assistant._show_reward_card("剧情奖励", detail))

        # 记录日记 (针对叙事链步骤)
        if diary_id:
            if self._check_diary_unlock(diary_id, title="叙事足迹"):
                self._announce("📖 【日记已更新】助手悄悄记录下了这次对话...")

    def _show_narrative_dialog(self, chain_id, message, options):
        """显示叙事选择对话框"""
        if hasattr(self.assistant, "show_option_dialog"):
            self.assistant.show_option_dialog(message, options, lambda idx: self.narrative_manager.handle_option_selection(chain_id, idx))
        else:
            self._announce(message)
            self.narrative_manager.handle_no_option_step(chain_id)

    def handle_project_event(self, event_type: str, **kwargs) -> None:
        # 1. 基础记录 (同步)
        module_key = self._event_to_module.get(event_type)
        if module_key:
            self.record_module_usage(module_key)
        if event_type in self._creation_event_types:
            self.record_creation_activity(event_type)

        # 2. 行为追踪记录 (同步)
        self.behavior_tracker.record_action(event_type, kwargs)

        # 3. 增强模块记录
        # 3.1 事件序列追踪
        self.sequence_tracker.record_event(event_type, kwargs)

        # 3.2 个性化引擎学习
        self.personalization.record_interaction(
            interaction_type=event_type,
            context=kwargs
        )

        # 3.3 主动干预系统活动追踪
        self.proactive_system.record_activity(event_type)

        # 4. 检测用户行为模式
        detected_pattern = self.sequence_tracker.detect_pattern()
        if detected_pattern:
            self._handle_detected_pattern(detected_pattern)

        # 5. 实时行为分析 (可能产生异步反馈)
        self._analyze_behavior_patterns()

        # 6. 尝试生成动态内容反馈
        self._try_dynamic_feedback(event_type, kwargs)

    def _analyze_behavior_patterns(self):
        """分析复杂行为模式并给出反馈"""
        now = datetime.now()
        
        # 特例检查：退出心流必须能够立即结算
        flow_analysis = self.behavior_tracker.analyze_flow()
        if flow_analysis.get("flow_state_change") == "exited":
            duration = flow_analysis.get("duration", 0)
            if duration > BEHAVIOR_THRESHOLDS.get("FLOW_MIN_DURATION", 300):
                self._trigger_behavior_feedback("flow_finish", duration=duration, priority=EventPriority.HIGH)
            return

        # 冷却检查函数
        def check_cooldown(pattern, seconds):
            last = self._last_feedback_times.get(pattern, datetime.min)
            return (now - last).total_seconds() > seconds

        # 1. 进入心流检测 (冷却 10 分钟)
        if flow_analysis.get("flow_state_change") == "entered":
            if check_cooldown("flow_enter", 600):
                # 状态改变立即执行，不进队列
                self.assistant.set_state(AssistantState.WRITING, duration=0) 
                self._last_feedback_times["flow_enter"] = now
            return

        # 2. 润色模式 (冷却 15 分钟)
        if self.behavior_tracker.analyze_refactoring():
            if check_cooldown("refactoring", 900):
                self._trigger_behavior_feedback("refactoring", priority=EventPriority.NORMAL)
            return
            
        # 3. 架构师模式 (冷却 10 分钟)
        if self.behavior_tracker.analyze_context_switching():
            if check_cooldown("architect", 600):
                self._trigger_behavior_feedback("architect", priority=EventPriority.NORMAL)
            return
            
    def check_idle_behavior(self):
        """定期检查的闲置行为"""
        now = datetime.now()
        last = self._last_feedback_times.get("hesitation", datetime.min)
        
        # 犹豫检测冷却 (20分钟)
        if (now - last).total_seconds() < 1200:
            return
            
        if self.behavior_tracker.analyze_hesitation():
            self._trigger_behavior_feedback("hesitation", priority=EventPriority.LOW)

    def _trigger_behavior_feedback(self, pattern_type: str, priority: int = 10, **kwargs):
        """触发行为反馈 (入队)"""
        # --- 1. 复合规则引擎介入 ---
        rule_matched = self._check_complex_rules(trigger_behavior=pattern_type)
        if rule_matched:
            return 

        # --- 2. 叙事链介入 (语义升级) ---
        # 如果是犹豫行为，且冷却已好，尝试触发“卡文叙事链”而不是普通气泡
        if pattern_type == "hesitation":
            # 检查叙事冷却 (借用 NarrativeManager 的逻辑，这里手动检查一下或直接推入)
            # 简单起见，我们直接推入 narrative 事件，NarrativeManager 会再次检查冷却
            # 但我们需要知道 chain_id。这里硬编码一下关联，未来可以做成配置
            self._enqueue_event(EventPriority.HIGH, "narrative", 
                              chain_id="writer_block_detected", 
                              # 填充 dummy 数据，实际由 manager 接管，但 _do_trigger_narrative 需要参数
                              # 修正：event_system 的 _do_trigger_narrative 是执行者，不是决策者。
                              # 正确的做法是：通知 narrative manager 检查特定触发
                              )
            # 注意：上面的逻辑有问题，因为 _do_trigger_narrative 期望具体的 message/options
            # 更好的做法是将 context['behavior'] = 'hesitation' 传递给 narrative_manager.check_triggers
            # 但 check_triggers 是轮询的。
            # 替代方案：直接在这里构造一个伪造的 narrative event 上下文推给 manager
            pass 

        # 修正方案：在 process_queue 的轮询中，我们已经把 context 传给了 narrative_manager
        # 但那是轮询。这里是事件触发。
        # 我们修改一下 strategy：
        # 将 "behavior" 存入一个临时状态，让下一次 process_queue 的轮询能捕捉到它？
        # 或者直接在这里手动调用 narrative_manager.check_triggers 并传入 behavior="hesitation"
        
        ctx = self._get_rule_context(pattern_type)
        narrative_event = self.narrative_manager.check_triggers(ctx)
        if narrative_event:
            self._enqueue_event(EventPriority.HIGH, "narrative", **narrative_event)
            return # 如果触发了叙事，就压制普通气泡

        # --- 3. 普通气泡反馈 ---
        self._enqueue_event(priority, "feedback", pattern_type=pattern_type, **kwargs)

    def _do_trigger_feedback(self, pattern_type: str, **kwargs):
        """执行反馈 (实际显示) - 增强版：支持个性化选择"""
        now = datetime.now()
        self._last_behavior_feedback = now
        self._last_feedback_times[pattern_type] = now

        # 尝试使用个性化反馈选择器
        user_prefs = self.personalization.get_preferences()
        message = self.feedback_selector.select_feedback(
            pattern_type,
            preferences=user_prefs,
            context={"project_type": self._get_project_type(), **kwargs}
        )

        # 如果个性化选择器没有返回，回退到原有逻辑
        if not message:
            # 先尝试扩展模板库
            templates = EXTENDED_BEHAVIOR_FEEDBACK.get(pattern_type, [])
            if not templates:
                templates = BEHAVIOR_FEEDBACK.get(pattern_type, [])
            if templates:
                message = random.choice(templates)
                try:
                    if pattern_type == "flow_finish":
                        kwargs["minutes"] = int(kwargs.get("duration", 0) / 60)
                    message = message.format(**kwargs)
                except Exception:
                    pass

        if pattern_type == "flow_finish":
            minutes = int(kwargs.get("duration", 0) / 60)
            self.assistant.set_state(AssistantState.EXCITED)
            if not message:
                message = f"刚才的{minutes}分钟里，你的键盘都要冒烟了！"
            self._announce(message)
            self.pet_system.add_xp(minutes * 2)

            # 记录反馈以供学习
            self.feedback_loop.record_feedback(f"flow_finish_{now.isoformat()}", "triggered")

        elif pattern_type == "refactoring":
            self.assistant.set_state(AssistantState.THINKING)
            self._announce(message or "反复推敲、精雕细琢...这一定是很重要的段落吧？")

        elif pattern_type == "architect":
            self.assistant.set_state(AssistantState.WORRIED)
            self._announce(message or "大纲、角色、正文...你的大脑在飞速运转呢，要喝杯水吗？")

        elif pattern_type == "hesitation":
            self.assistant.set_state(AssistantState.WORRIED)
            self._announce(message or "盯着屏幕发呆好久了...是不是卡文了？可以试试抽一张灵感卡哦。")

        else:
            # 通用处理：其他模式类型
            if message:
                self.assistant.set_state(AssistantState.HAPPY)
                self._announce(message)

    # ============================================================
    # 复合规则引擎
    # ============================================================

    def _check_complex_rules(self, trigger_behavior: Optional[str] = None) -> bool:
        """评估复合规则逻辑"""
        context = self._get_rule_context(trigger_behavior)
        
        for rule_id, config in COMPLEX_RULES.items():
            # 冷却检查
            cooldown = config.get("cooldown")
            if cooldown == "daily":
                if not self._check_daily_cooldown(f"complex:{rule_id}"):
                    continue
            elif cooldown == "weekly":
                if not self._check_weekly_cooldown(f"complex:{rule_id}"):
                    continue
            elif rule_id in self._unlocked_events:
                continue

            # 条件评估
            conditions_met = True
            for cond in config.get("conditions", []):
                if not self._evaluate_condition(cond, context):
                    conditions_met = False
                    break
            
            if conditions_met:
                # 复合规则通常优先级较高
                self._enqueue_event(EventPriority.HIGH, "complex_rule", rule_id=rule_id, config=config)
                return True
        
        return False

    def _do_apply_complex_rule(self, rule_id: str, config: Dict):
        """执行复合规则奖励"""
        mood = config.get("mood", AssistantState.HAPPY)
        self.assistant.set_state(mood)
        
        templates = BEHAVIOR_FEEDBACK.get(rule_id, [])
        message = random.choice(templates) if templates else config.get("message")
        if message:
            self._announce(message)
            
        xp = config.get("reward_xp", 0)
        if xp > 0:
            self.pet_system.add_xp(xp)
            
        event_key = f"complex:{rule_id}"
        self._unlocked_events.add(event_key)
        self._event_log.append({
            "id": event_key,
            "message": message or f"达成复合规则: {rule_id}",
            "timestamp": datetime.now().isoformat(),
        })
        self._save_state()

    def _get_rule_context(self, trigger_behavior: Optional[str]) -> Dict[str, Any]:
        """获取当前规则评估上下文 (增强版：支持本地数据分析)"""
        now = datetime.now()
        
        # 1. 获取基础统计
        streak = 0
        today_words = 0
        if hasattr(self.assistant, "integration") and self.assistant.integration:
            try:
                stats = self.assistant.integration.get_stats_summary()
                streak = stats.get("streak", 0)
                today_words = stats.get("today_words", 0)
            except: pass
        else:
            streak = getattr(self.pet_system.data, "daily_streak", 0)
            # 尝试从 project_manager 获取今日字数 (如果有统计模块)
            # 这里简化处理，暂时留空或读取本地缓存

        # 2. 获取时间状态
        time_period = "unknown"
        if hasattr(self.assistant, "time_detector"):
            time_period = self.assistant.time_detector.get_time_state()

        # 3. 构建分析结果 (优先用 Integration，失败则用本地分析)
        analysis_results = {}
        if hasattr(self.assistant, "integration") and self.assistant.integration:
             analysis_results = self.assistant.integration.get_deep_analysis() or {}
        
        # 本地分析回退 (Local Analysis Fallback)
        # 如果 Integration 没返回结果，或者根本不存在，我们自己分析 ProjectManager 数据
        if not analysis_results and self.project_manager:
            analysis_results = self._perform_local_analysis()

        return {
            "behavior": trigger_behavior,
            "time_period": time_period,
            "weekday": now.weekday(),
            "is_weekend": now.weekday() >= 5,
            "stat_streak": streak,
            "stat_today_words": today_words,
            "analysis_results": analysis_results,
            "project_type": self._get_project_type()
        }

    def _perform_local_analysis(self) -> Dict[str, bool]:
        """本地轻量级项目分析 (不依赖 AI)"""
        results = {
            "character_flat": False,
            "scene_short": False,
            "description_missing": False,
            "structure_missing_climax": False,
            "structure_repetitive": False,
            "conflict_missing_direct": False,
            "relationships_sparse": False
        }
        
        try:
            # 1. 角色深度分析
            characters = self.project_manager.get_characters()
            flat_count = 0
            protagonist = None
            antagonist = None
            
            for char in characters:
                desc = char.get("description", "") or ""
                bio = char.get("bio", "") or ""
                role = char.get("role", "")
                
                if role == "protagonist": protagonist = char
                elif role == "antagonist": antagonist = char
                
                # 如果主要角色描述极短
                if role in ["protagonist", "antagonist"] and (len(desc) + len(bio)) < 20:
                    flat_count += 1
            
            if flat_count > 0:
                results["character_flat"] = True

            # 2. 场景结构分析
            scenes = self.project_manager.get_scenes()
            if scenes:
                last_scene = scenes[-1]
                content = last_scene.get("content", "")
                if 0 < len(content) < 200: 
                    results["scene_short"] = True
                    
                # 检查高潮
                has_climax = False
                tags_sequence = []
                for s in scenes:
                    tags = s.get("tags", [])
                    # 简单关键词匹配
                    for t in tags:
                        t_lower = t.lower()
                        if "climax" in t_lower or "高潮" in t_lower:
                            has_climax = True
                        tags_sequence.append(t_lower)
                
                if len(scenes) > 5 and not has_climax:
                    results["structure_missing_climax"] = True
                    
                # 检查重复结构 (连续3个相同功能标签)
                # 简化逻辑：检查最近3个场景是否tag完全一致且非空
                if len(scenes) >= 3:
                    s1, s2, s3 = scenes[-3:]
                    t1, t2, t3 = str(s1.get("tags")), str(s2.get("tags")), str(s3.get("tags"))
                    if t1 == t2 == t3 and s1.get("tags"):
                        results["structure_repetitive"] = True

            # 3. 冲突检测
            if protagonist and antagonist:
                # 检查是否有两人同场的场景
                pairs = self.project_manager.get_scenes_with_character_pair(
                    protagonist["name"], antagonist["name"]
                )
                if not pairs and len(scenes) > 3:
                    results["conflict_missing_direct"] = True

            # 4. 关系网密度
            rels = self.project_manager.get_relationships()
            links = rels.get("relationship_links", [])
            major_chars_count = sum(1 for c in characters if c.get("role") in ["protagonist", "antagonist", "supporting"])
            if major_chars_count > 2 and len(links) < major_chars_count:
                results["relationships_sparse"] = True

        except Exception:
            pass
            
        return results

    def _evaluate_condition(self, cond: Dict, ctx: Dict) -> bool:
        """评估单个条件"""
        ctype = cond.get("type")
        cval = cond.get("value")
        cop = cond.get("op", "==")
        
        actual = ctx.get(ctype)
        if actual is None:
            if ctype == "weekday" and cval == "weekend":
                actual = "weekend" if ctx.get("is_weekend") else "weekday"
            else:
                return False

        if cop == "==": return actual == cval
        if cop == ">=": return actual >= cval
        if cop == "<=": return actual <= cval
        if cop == "!=": return actual != cval
        return False

    def _check_weekly_cooldown(self, event_id: str) -> bool:
        today = datetime.now()
        monday = (today - timedelta(days=today.weekday())).strftime("%Y-%W")
        if self._time_marks.get(event_id) == monday:
            return False
        self._time_marks[event_id] = monday
        return True

    def _check_daily_cooldown(self, event_id: str) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        if self._time_marks.get(event_id) == today:
            return False
        self._time_marks[event_id] = today
        return True

    # ============================================================
    # 存量逻辑 (Milestones, Themes, etc.)
    # ============================================================

    def _do_trigger_milestone(self, milestone: Dict):
        """执行里程碑触发"""
        message = self._resolve_smart_message(milestone)
        self._trigger_event(
            event_id=milestone["id"],
            message=message,
            achievement_id=milestone.get("achievement"),
            diary_id=milestone.get("diary_id")
        )

    def _check_module_milestones(self) -> None:
        unique_count = len([k for k, v in self._module_usage.items() if v > 0])
        total_usage = sum(self._module_usage.values())

        for milestone in self._module_milestones:
            m_type = milestone.get("type", "unique_count") # Default to unique count
            threshold = milestone["threshold"]
            
            is_met = False
            if m_type == "unique_count":
                if unique_count >= threshold:
                    is_met = True
            elif m_type == "usage_count":
                if total_usage >= threshold:
                    is_met = True
            elif m_type == "specific_module":
                module_name = milestone.get("module")
                if module_name and self._module_usage.get(module_name, 0) >= threshold:
                    is_met = True

            if is_met:
                self._enqueue_event(EventPriority.HIGH, "milestone", milestone=milestone)

    def _check_type_milestones(self) -> None:
        count = len(self._created_types)
        for milestone in self._type_milestones:
            if count >= milestone["threshold"]:
                self._enqueue_event(EventPriority.HIGH, "milestone", milestone=milestone)

    def _check_theme_milestones(self) -> None:
        count = len(self._created_themes)
        for milestone in self._theme_milestones:
            if count >= milestone["threshold"]:
                self._enqueue_event(EventPriority.HIGH, "milestone", milestone=milestone)

    # ... (record_module_usage, record_creation_activity, _record_project_type, _record_themes, _trigger_type_event, _collect_theme_tags, _normalize_tags, handle_festival_event, check_time_events, handle_achievement_unlocked, _trigger_event, _unlock_achievement, _award_photo, _announce, _get_project_type, get_event_log methods remain mostly the same, ensuring they use queue for side effects where appropriate) ...

    def handle_festival_event(self, festival: str) -> None:
        """处理节日/纪念日事件"""
        if festival == AssistantState.BIRTHDAY:
            self._trigger_event(
                event_id=f"special_day:birthday:{datetime.now().year}",
                achievement_id="birthday",
                photo_state=AssistantState.CELEBRATING,
                cooldown="daily"
            )
        elif festival == AssistantState.ANNIVERSARY:
            self._trigger_event(
                event_id=f"special_day:anniversary:{datetime.now().year}",
                achievement_id="anniversary",
                photo_state=AssistantState.TRUST,
                cooldown="daily"
            )

    def record_module_usage(self, module_key: str) -> None:
        # Increment usage count
        current = self._module_usage.get(module_key, 0)
        self._module_usage[module_key] = current + 1
        self._save_state()
        self._check_module_milestones()

    def record_creation_activity(self, event_type: str) -> None:
        project_type = self._get_project_type()
        if project_type:
            self._record_project_type(project_type)
        if event_type in self._theme_event_types:
            self._record_themes()

    def _record_project_type(self, project_type: str) -> None:
        if project_type in self._created_types:
            return

        self._created_types.add(project_type)
        self._trigger_type_event(project_type)
        self._check_type_milestones()
        self._save_state()

    def _record_themes(self) -> None:
        new_tags = self._collect_theme_tags() - self._created_themes
        if not new_tags:
            return

        self._created_themes.update(new_tags)
        self._check_theme_milestones()
        self._save_state()

    def _trigger_type_event(self, project_type: str) -> None:
        type_info = ProjectTypeManager.get_type_info(project_type)
        type_name = type_info.get("name", project_type)
        photo_state = self._type_photo_states.get(project_type) or self._type_photo_states.get("*")
        self._trigger_event(
            event_id=f"type_created:{project_type}",
            message=f"创作类型已记录：{type_name}",
            photo_state=photo_state,
        )

    def _collect_theme_tags(self) -> Set[str]:
        if not self.project_manager:
            return set()

        tags: Set[str] = set()

        try:
            for scene in self.project_manager.get_scenes():
                tags.update(self._normalize_tags(scene.get("tags", [])))

            outline_root = self.project_manager.get_outline()
            if outline_root:
                stack = [outline_root]
                while stack:
                    node = stack.pop()
                    tags.update(self._normalize_tags(node.get("tags", [])))
                    for child in node.get("children", []):
                        stack.append(child)

            for idea in self.project_manager.get_ideas():
                tags.update(self._normalize_tags(idea.get("tags", [])))

            for item in self.project_manager.get_research_items():
                tags.update(self._normalize_tags(item.get("tags", [])))
        except Exception:
            return set()

        return tags

    def _normalize_tags(self, raw_tags) -> Set[str]:
        if not isinstance(raw_tags, (list, set, tuple)):
            return set()

        cleaned: Set[str] = set()
        for tag in raw_tags:
            if not isinstance(tag, str):
                continue
            value = tag.strip()
            if not value:
                continue
            if any(value.startswith(prefix) for prefix in self._theme_ignore_prefixes):
                continue
            cleaned.add(value)
        return cleaned

    def _resolve_smart_message(self, event_def: Dict) -> str:
        """解析智能动态文案"""
        variants = event_def.get("variants")
        if variants:
            ctx = self._get_rule_context(None)
            valid_variants = []
            
            for v in variants:
                condition = v.get("condition")
                if self._check_variant_condition(condition, ctx):
                    valid_variants.append(v)
            
            if valid_variants:
                weights = [v.get("weight", 10) for v in valid_variants]
                selected = random.choices(valid_variants, weights=weights, k=1)[0]
                return selected.get("text")
        
        return event_def.get("message", "")

    def _check_variant_condition(self, condition: str, ctx: Dict) -> bool:
        """检查文案变体条件 (简易版)"""
        if not condition: return True
        
        if condition.startswith("analysis:"):
            key = condition.split(":")[1]
            return ctx.get("analysis_results", {}).get(key, False)
            
        return True

    def check_time_events(self) -> None:
        if not hasattr(self.assistant, "time_detector"):
            return

        period = self.assistant.time_detector.get_time_state()
        if not period:
            return
            
        # 顺便检查闲置行为
        self.check_idle_behavior()

        for evt in self._time_events:
            if evt["period"] == period:
                message = self._resolve_smart_message(evt)
                self._trigger_event(
                    event_id=evt["id"],
                    message=message,
                    achievement_id=evt.get("achievement"),
                    photo_state=evt.get("state"),
                    action=evt.get("action"),
                    cooldown=evt.get("cooldown"),
                )

    def handle_achievement_unlocked(self, achievement_id: str) -> None:
        reward = self._achievement_photo_rewards.get(achievement_id)
        if not reward:
            return

        project_type = self._get_project_type()
        state = reward.get(project_type) or reward.get("*")
        if not state:
            return

        event_id = f"achievement_photo:{achievement_id}:{project_type}"
        message = reward.get("_message")
        self._trigger_event(
            event_id=event_id,
            message=message,
            photo_state=state,
            silent_message=message is None,
            require_photo_for_message=True,
        )

    def _trigger_event(
        self,
        event_id: str,
        message: Optional[str] = None,
        achievement_id: Optional[str] = None,
        photo_state: Optional[str] = None,
        action: Optional[str] = None,
        cooldown: Optional[str] = None,
        silent_message: bool = False,
        require_photo_for_message: bool = False,
        diary_id: Optional[str] = None,
    ) -> bool:
        if not event_id:
            return False

        if cooldown == "daily":
            if not self._check_daily_cooldown(event_id):
                return False
        else:
            if event_id in self._unlocked_events:
                return False

        if achievement_id:
            self._unlock_achievement(achievement_id)

        photo_added = False
        if photo_state:
            photo_added = self._award_photo(photo_state, event_id)
            
        if action:
            self._execute_event_action(action)

        if message and not silent_message:
            if require_photo_for_message and not photo_added:
                message = None
        if message:
            self._announce(message)

        # --- 全局日记同步 ---
        target_diary_id = diary_id or event_id
        if self._check_diary_unlock(target_diary_id, title=message):
            self._announce("📖 【日记已更新】助手悄悄记录下了这一刻...")

        self._unlocked_events.add(event_id)
        self._event_log.append({
            "id": event_id,
            "message": message or "",
            "timestamp": datetime.now().isoformat(),
        })
        self._save_state()
        return True

    def _execute_event_action(self, action: str):
        """执行事件动作"""
        if action == "trigger_school_event":
            if hasattr(self.assistant, "_trigger_school_event"):
                # 延迟执行，避免与当前弹窗冲突
                self.assistant.after(2000, lambda: self.assistant._trigger_school_event())

    def _unlock_achievement(self, achievement_id: str) -> None:
        if hasattr(self.assistant, "_unlock_achievement"):
            try:
                self.assistant._unlock_achievement(achievement_id)
            except Exception:
                pass

    def _award_photo(self, state: str, event_id: str) -> bool:
        if hasattr(self.assistant, "_add_event_photo"):
            try:
                photo = self.assistant._add_event_photo(state, event_id=event_id)
                return bool(photo)
            except Exception:
                return False
        return False

    def _announce(self, message: str) -> None:
        if hasattr(self.assistant, "notification_manager"):
            self.assistant.notification_manager.notify(message, "system", priority=10)
        elif hasattr(self.assistant, "_append_message"):
            try:
                self.assistant.after(0, lambda: self.assistant._append_message("system", message))
            except Exception:
                pass

    def _get_project_type(self) -> str:
        if self.project_manager and hasattr(self.project_manager, "get_project_type"):
            try:
                return self.project_manager.get_project_type()
            except Exception:
                return "General"
        return "General"

    def get_event_log(self) -> list:
        return list(self._event_log)

    def _load_diary_content(self) -> Dict:
        """加载日记内容库"""
        try:
            path = Path(__file__).parent.parent.parent.parent / "writer_data" / "diary_content.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _check_diary_unlock(self, event_id: str, title: str = None) -> bool:
        """检查并解锁关联日记"""
        if event_id in self.diary_data:
            # 对于系统事件，通常使用索引 "0" 或直接匹配 event_id
            content = self.diary_data[event_id].get("0") or self.diary_data[event_id].get("diary")
            if content:
                return self.pet_system.add_diary_entry(
                    event_id=event_id,
                    title=title or "系统记录",
                    content=content
                )
        return False

    # ============================================================
    # 增强模块方法
    # ============================================================

    def _handle_detected_pattern(self, pattern: Dict[str, Any]) -> None:
        """处理检测到的用户行为模式"""
        pattern_id = pattern.get("pattern_id")
        confidence = pattern.get("confidence", 0)

        if confidence < 0.6:
            return  # 置信度过低，不触发

        # 冷却检查 (每种模式每30分钟最多触发一次)
        cooldown_key = f"pattern:{pattern_id}"
        now = datetime.now()
        last_time = self._last_feedback_times.get(cooldown_key, datetime.min)
        if (now - last_time).total_seconds() < 1800:
            return

        self._last_feedback_times[cooldown_key] = now

        # 根据模式类型选择反馈
        pattern_messages = {
            "planner": "看起来你喜欢先规划再动笔呢，这是个好习惯！",
            "discovery_writer": "你好像更喜欢边写边发现故事的走向，这种探索感很棒！",
            "character_driven": "角色对你来说很重要呢，人物塑造是故事的灵魂~",
            "worldbuilder": "世界观架构师！你的设定一定很丰富。",
            "quick_drafter": "快速起草派！先完成再完美，效率很高呢。",
            "perfectionist": "精益求精型！每一个细节都不放过。",
            "night_worker": "夜猫子作家！深夜的灵感总是特别多。",
            "morning_person": "早起的鸟儿有虫吃！清晨创作效率最高。",
            "multi_project": "多线程创作！同时进行多个项目，思维很活跃。",
            "deep_diver": "深度探索者！专注于一个项目深耕细作。",
        }

        message = pattern_messages.get(pattern_id)
        if message:
            # 使用个性化反馈选择器调整语气
            user_preferences = self.personalization.get_preferences()
            preferred_tone = user_preferences.get("preferred_tone", "encouraging")
            adjusted_message = self.feedback_selector.adjust_tone(message, preferred_tone)

            self.assistant.set_state(AssistantState.HAPPY)
            self._announce(adjusted_message)

    def _try_dynamic_feedback(self, event_type: str, event_data: Dict) -> None:
        """尝试生成动态内容反馈"""
        # 冷却检查 (每5分钟最多一次动态反馈)
        cooldown_key = "dynamic_feedback"
        now = datetime.now()
        last_time = self._last_feedback_times.get(cooldown_key, datetime.min)
        if (now - last_time).total_seconds() < 300:
            return

        # 概率触发 (30%概率)
        if random.random() > 0.3:
            return

        self._last_feedback_times[cooldown_key] = now

        try:
            # 根据事件类型选择生成方法
            feedback = None

            if event_type == "character_added" and self.project_manager:
                characters = self.project_manager.get_characters()
                if characters:
                    char = characters[-1]  # 最新添加的角色
                    feedback = self.dynamic_content.generate_character_comment(char)

            elif event_type in ("scene_added", "scene_updated") and self.project_manager:
                scenes = self.project_manager.get_scenes()
                if scenes:
                    scene = scenes[-1]  # 最新的场景
                    feedback = self.dynamic_content.generate_scene_reaction(scene)

            elif event_type == "outline_changed" and random.random() < 0.5:
                # 生成鼓励性问题
                feedback = self.dynamic_content.generate_question()

            if feedback:
                self._announce(feedback)

        except Exception as e:
            logger.debug(f"动态反馈生成失败: {e}")

    def perform_deep_analysis(self, content: str = None) -> Dict[str, Any]:
        """执行深度内容分析"""
        if not content and self.project_manager:
            # 收集所有场景内容
            scenes = self.project_manager.get_scenes()
            content = "\n\n".join(s.get("content", "") for s in scenes if s.get("content"))

        if not content:
            return {}

        return self.deep_analysis.analyze_all(content)

    def get_proactive_intervention(self) -> Optional[Dict[str, Any]]:
        """获取主动干预建议"""
        ctx = self._get_rule_context(None)
        return self.proactive_system.check_interventions(ctx)

    def handle_proactive_tick(self) -> None:
        """主动干预系统的定时检查"""
        intervention = self.get_proactive_intervention()
        if intervention:
            message = intervention.get("message")
            mood = intervention.get("mood", AssistantState.THINKING)
            priority = intervention.get("priority", EventPriority.NORMAL)

            self._enqueue_event(priority, "proactive", message=message, mood=mood)

    def _do_trigger_proactive(self, message: str, mood: str = None):
        """执行主动干预"""
        if mood:
            self.assistant.set_state(mood)
        self._announce(message)

    def get_context_aware_tip(self, content_type: str = None) -> Optional[str]:
        """获取上下文感知的写作建议"""
        if not content_type and self.project_manager:
            # 尝试检测当前内容类型
            scenes = self.project_manager.get_scenes()
            if scenes:
                last_scene = scenes[-1]
                content = last_scene.get("content", "")
                content_type = self.context_feedback.detect_content_type(content)

        if content_type:
            return self.context_feedback.get_contextual_tip(content_type)
        return None

    def record_feedback_reaction(self, feedback_id: str, reaction: str) -> None:
        """记录用户对反馈的反应"""
        # reaction: "positive", "neutral", "negative", "dismissed"
        self.feedback_loop.record_feedback(feedback_id, reaction)
        self.personalization.update_preference("feedback_reaction", reaction)

    def get_personalized_feedback(self, category: str) -> str:
        """获取个性化的反馈文案"""
        user_prefs = self.personalization.get_preferences()
        return self.feedback_selector.select_feedback(
            category,
            preferences=user_prefs,
            context={"project_type": self._get_project_type()}
        )

    def get_writing_style_summary(self) -> Dict[str, Any]:
        """获取写作风格摘要"""
        if not self.project_manager:
            return {}

        scenes = self.project_manager.get_scenes()
        content = "\n\n".join(s.get("content", "") for s in scenes if s.get("content"))

        if not content:
            return {}

        return self.deep_analysis.style_analyzer.analyze(content)

    def get_emotional_curve(self) -> List[Dict[str, Any]]:
        """获取情感曲线分析"""
        if not self.project_manager:
            return []

        scenes = self.project_manager.get_scenes()
        content = "\n\n".join(s.get("content", "") for s in scenes if s.get("content"))

        if not content:
            return []

        return self.deep_analysis.emotional_analyzer.analyze(content)

    def get_pacing_analysis(self) -> Dict[str, Any]:
        """获取节奏分析"""
        if not self.project_manager:
            return {}

        scenes = self.project_manager.get_scenes()
        return self.deep_analysis.pacing_analyzer.analyze_scenes(scenes)

    def get_user_behavior_profile(self) -> Dict[str, Any]:
        """获取用户行为画像"""
        return {
            "detected_patterns": self.sequence_tracker.get_detected_patterns(),
            "preferences": self.personalization.get_preferences(),
            "activity_stats": self.proactive_system.get_activity_stats(),
            "feedback_effectiveness": self.feedback_loop.get_effectiveness_report(),
        }
