"""
悬浮写作助手 (Floating Writing Assistant) v5.1

一个桌宠风格的悬浮AI写作助手，支持：
- AI对话（流式输出、打字机效果）
- 无AI模式工具集（起名、提示卡、骰子、计时器等）
- 养成系统（好感度、心情、收集品、等级）
- 边缘吸附、快捷键、剪贴板监听
- 丰富立绘分支（60+状态：情绪、节日、季节、服装、场景）
- 分层立绘系统（多层叠加、表情组合、环境效果）
- 相册系统（标签管理、收藏集、稀有度、导出功能）
- 日记系统（动态模板、心情追踪、可编辑）
- 节日/季节自动检测和主题切换
- 小游戏（猜数字、成语接龙、故事接龙等）
- 语音输入/朗读（可选）
- 分支叙事引擎（多结局故事、CG解锁）
- 互动链系统（多种互动类型、关系发展）
- 成长轨迹（里程碑追踪、统计分析）

v5.1 新增 - 校园Galgame系统：
- NPC角色系统（多角色、好感度、关系发展阶段）
- 校园场景系统（教室、图书馆、社团等30+地点）
- 关系网络系统（NPC社交关系、社交圈）
- 时间周期系统（日程、天气、季节、特殊日期）
- 社交行动系统（对话、送礼、活动、浪漫互动）
- 剧情追踪系统（主线/支线/角色线、成就）
- 校园事件系统（智能事件触发、剧情联动）
"""

__version__ = "5.1.0"
__author__ = "Writer Tool Team"

# 导出核心类
from .states import (
    AssistantState,
    STATE_NAMES,
    STATE_EMOJIS,
    STATE_FALLBACKS,
    FestivalDetector,
    SeasonDetector,
    TimeDetector,
    LunarCalendar,
)

from .constants import (
    ACHIEVEMENTS,
    FOODS,
    WRITING_PROMPTS,
    IDLE_CHAT_TOPICS,
    EMOTION_KEYWORDS,
    AI_EMOTION_KEYWORDS,
    QUICK_PROMPTS_AI,
    QUICK_TOOLS,
    CHARACTER_TEMPLATES,
    SCENE_TEMPLATES,
)

from .pet_system import (
    PetSystem,
    PetData,
    MoodLevel,
)

from .tools import (
    NameGenerator,
    NameType,
    Gender,
    DiceRoller,
    PomodoroTimer,
    PromptCardDrawer,
    CharacterCardGenerator,
    SceneGenerator,
    WordCounter,
    FoodSelector,
)

from .ai_handler import (
    AIConfig,
    StreamingAIClient,
    ConversationHistory,
    ConversationMessage,
    EmotionDetector,
    ProjectContextBuilder,
    AIAssistantHandler,
)

from .games import (
    MiniGameManager,
    GuessNumberGame,
    RockPaperScissorsGame,
    WordChainGame,
    WordAssociationGame,
    StoryGame,
)

from .dialogs import (
    NameGeneratorDialog,
    TimerDialog,
    QuickNoteDialog,
    PromptCardDialog,
    CharacterCardDialog,
    SceneGeneratorDialog,
    GameDialog,
    AchievementDialog,
    CollectionDialog,
    FeedDialog,
    AffectionDialog,
    WardrobeDialog,
    AssistantSettingsDialog,
    AlbumDialog,
)

from .main import (
    FloatingAssistant,
    FloatingAssistantManager,
)

from .context_hotkeys import (
    EditorContext,
    ContextProvider,
    HotkeyBinding,
    HotkeyManager,
    ClipboardMonitor,
    ContextAwareAssistant,
)

from .voice import (
    VoiceInputState,
    VoiceRecognitionResult,
    SpeechRecognizer,
    TextToSpeech,
    VoiceAssistant,
    check_voice_dependencies,
    get_installation_guide,
)

from .integrations import (
    EventBusIntegration,
    GamificationIntegration,
    CommandExecutor,
    AIControllerBridge,
    StatsIntegration,
    AssistantIntegrationManager,
)

# 增强模块
from .event_sequence import (
    EventSequenceTracker,
    FeedbackLoop,
)

from .preference_system import (
    UserPreferenceTracker,
    AdaptiveContentSelector,
    PersonalizationEngine,
)

from .deep_analysis import (
    WritingStyleAnalyzer,
    EmotionalCurveAnalyzer,
    PacingAnalyzer,
    CharacterArcAnalyzer,
    StructureAnalyzer,
    DeepAnalysisEngine,
)

from .proactive_system import (
    ActivityTracker,
    ContextAnalyzer,
    ProactiveInterventionSystem,
    ContextAwareFeedback,
)

from .feedback_templates import (
    EXTENDED_BEHAVIOR_FEEDBACK,
    TONE_TEMPLATES,
    FeedbackSelector,
)

from .dynamic_content import (
    DynamicContentGenerator,
)

from .enhanced_integration import (
    EnhancedIntegrationManager,
    create_enhanced_integration,
)

# v5.0 升级模块 - 分层立绘系统
from .layered_image import (
    LayerType,
    BlendMode,
    LayerDefinition,
    CompositeDefinition,
    ExpressionSet,
    PoseDefinition,
    LayeredImageManager,
    FrameAnimationPlayer,
    IdleAnimationController,
)

# v5.0 升级模块 - 环境效果
from .environment_effects import (
    TimeOfDay,
    Weather,
    Season,
    MoodTone,
    LightingConfig,
    ParticleConfig,
    EnvironmentState,
    EnvironmentEffectsRenderer,
    DynamicLightingController,
    SpecialEffectsLibrary,
    create_environment_renderer,
    apply_quick_effect,
)

# v5.0 升级模块 - 互动链系统
from .interaction_chain import (
    InteractionType,
    InteractionResult,
    RelationshipPhase,
    InteractionOption,
    InteractionNode,
    InteractionChain,
    InteractionHistory,
    InteractionChainManager,
    DailyCycleManager,
    create_interaction_system,
)

# v5.0 升级模块 - 分支叙事引擎
from .branching_narrative import (
    StoryRoute,
    EndingType,
    ConditionType,
    StoryCondition,
    StoryEffect,
    DialogLine,
    StoryChoice,
    StoryNode,
    StoryChapter,
    StoryEnding,
    CGEntry,
    BranchingNarrativeEngine,
    create_narrative_engine,
)

# v5.0 升级模块 - 日记系统
from .diary_system import (
    DiaryMood,
    DiaryCategory,
    DiaryTemplate,
    DiaryEntry,
    MoodRecord,
    DiaryTemplateEngine,
    EnhancedDiarySystem,
    create_diary_system,
)

# v5.0 升级模块 - 相册系统
from .album_system import (
    PhotoCategory,
    PhotoRarity,
    PhotoTag,
    Photo,
    Collection,
    AlbumFilter,
    EnhancedAlbumSystem,
    create_album_system,
)

# v5.0 升级模块 - 成长轨迹
from .growth_timeline import (
    EventType,
    EventImportance,
    TimelineEvent,
    GrowthStats,
    GrowthTimeline,
    create_growth_timeline,
)

# v5.1 升级模块 - NPC系统
from .npc_system import (
    NPCRole,
    NPCRelationPhase,
    NPCCharacter,
    NPCRelationData,
    NPCManager,
    create_npc_system,
)

# v5.1 升级模块 - 校园场景系统
from .campus_locations import (
    LocationCategory,
    LocationStatus,
    CampusLocation,
    CampusLocationManager,
    create_location_manager,
)

# v5.1 升级模块 - 关系网络系统
from .relationship_network import (
    RelationType,
    RelationStrength,
    SocialCircleType,
    NPCRelationship,
    SocialCircle,
    RelationshipNetworkManager,
    create_relationship_network,
)

# v5.1 升级模块 - 时间周期系统
from .time_cycle import (
    TimePeriod,
    DayOfWeek,
    GameTime,
    SpecialDate,
    TimeCycleManager,
    create_time_cycle,
)

# v5.1 升级模块 - 社交行动系统
from .social_actions import (
    ActionCategory,
    ActionResult,
    SocialAction,
    SocialActionManager,
    create_social_action_manager,
)

# v5.1 升级模块 - 剧情追踪系统
from .story_tracker import (
    StoryLineType,
    StoryNodeType,
    StoryLine,
    StoryNode,
    Achievement,
    StoryTracker,
    create_story_tracker,
)

# v5.1 升级模块 - 校园事件系统 (升级版)
from .school_events import (
    SchoolEvent,
    SchoolEventChoice,
    SchoolEventManager,
    create_event_manager,
)

from .stats_widgets import (
    MiniRadarChart,
    ProgressBar,
    MiniHeatmap,
    StatsCard,
    MiniStatsPanel,
    QuickActionsPanel,
)

from .dialogs import (
    QuickInputDialog,
    QuickCharacterDialog,
    QuickSceneDialog,
    QuickIdeaDialog,
    QuickResearchDialog,
)

__all__ = [
    # 版本
    "__version__",

    # 状态
    "AssistantState",
    "STATE_NAMES",
    "STATE_EMOJIS",
    "STATE_FALLBACKS",
    "FestivalDetector",
    "SeasonDetector",
    "TimeDetector",
    "LunarCalendar",

    # 常量
    "ACHIEVEMENTS",
    "FOODS",
    "WRITING_PROMPTS",
    "IDLE_CHAT_TOPICS",
    "EMOTION_KEYWORDS",
    "AI_EMOTION_KEYWORDS",
    "QUICK_PROMPTS_AI",
    "QUICK_TOOLS",
    "CHARACTER_TEMPLATES",
    "SCENE_TEMPLATES",

    # 养成系统
    "PetSystem",
    "PetData",
    "MoodLevel",

    # 工具
    "NameGenerator",
    "NameType",
    "Gender",
    "DiceRoller",
    "PomodoroTimer",
    "PromptCardDrawer",
    "CharacterCardGenerator",
    "SceneGenerator",
    "WordCounter",
    "FoodSelector",

    # AI
    "AIConfig",
    "StreamingAIClient",
    "ConversationHistory",
    "ConversationMessage",
    "EmotionDetector",
    "ProjectContextBuilder",
    "AIAssistantHandler",

    # 游戏
    "MiniGameManager",
    "GuessNumberGame",
    "RockPaperScissorsGame",
    "WordChainGame",
    "WordAssociationGame",
    "StoryGame",

    # 对话框
    "NameGeneratorDialog",
    "TimerDialog",
    "QuickNoteDialog",
    "PromptCardDialog",
    "CharacterCardDialog",
    "SceneGeneratorDialog",
    "GameDialog",
    "AchievementDialog",
    "CollectionDialog",
    "FeedDialog",
    "AffectionDialog",
    "WardrobeDialog",
    "AssistantSettingsDialog",
    "AlbumDialog",

    # 主类
    "FloatingAssistant",
    "FloatingAssistantManager",

    # 上下文和快捷键
    "EditorContext",
    "ContextProvider",
    "HotkeyBinding",
    "HotkeyManager",
    "ClipboardMonitor",
    "ContextAwareAssistant",

    # 语音功能
    "VoiceInputState",
    "VoiceRecognitionResult",
    "SpeechRecognizer",
    "TextToSpeech",
    "VoiceAssistant",
    "check_voice_dependencies",
    "get_installation_guide",

    # 集成模块
    "EventBusIntegration",
    "GamificationIntegration",
    "CommandExecutor",
    "AIControllerBridge",
    "StatsIntegration",
    "AssistantIntegrationManager",

    # 统计组件
    "MiniRadarChart",
    "ProgressBar",
    "MiniHeatmap",
    "StatsCard",
    "MiniStatsPanel",
    "QuickActionsPanel",

    # 快速输入对话框
    "QuickInputDialog",
    "QuickCharacterDialog",
    "QuickSceneDialog",
    "QuickIdeaDialog",
    "QuickResearchDialog",

    # 增强模块 - 事件序列
    "EventSequenceTracker",
    "FeedbackLoop",

    # 增强模块 - 个性化
    "UserPreferenceTracker",
    "AdaptiveContentSelector",
    "PersonalizationEngine",

    # 增强模块 - 深度分析
    "WritingStyleAnalyzer",
    "EmotionalCurveAnalyzer",
    "PacingAnalyzer",
    "CharacterArcAnalyzer",
    "StructureAnalyzer",
    "DeepAnalysisEngine",

    # 增强模块 - 主动干预
    "ActivityTracker",
    "ContextAnalyzer",
    "ProactiveInterventionSystem",
    "ContextAwareFeedback",

    # 增强模块 - 反馈模板
    "EXTENDED_BEHAVIOR_FEEDBACK",
    "TONE_TEMPLATES",
    "FeedbackSelector",

    # 增强模块 - 动态内容
    "DynamicContentGenerator",

    # 增强模块 - 集成管理器
    "EnhancedIntegrationManager",
    "create_enhanced_integration",

    # v5.0 升级 - 分层立绘系统
    "LayerType",
    "BlendMode",
    "LayerDefinition",
    "CompositeDefinition",
    "ExpressionSet",
    "PoseDefinition",
    "LayeredImageManager",
    "FrameAnimationPlayer",
    "IdleAnimationController",

    # v5.0 升级 - 环境效果
    "TimeOfDay",
    "Weather",
    "Season",
    "MoodTone",
    "LightingConfig",
    "ParticleConfig",
    "EnvironmentState",
    "EnvironmentEffectsRenderer",
    "DynamicLightingController",
    "SpecialEffectsLibrary",
    "create_environment_renderer",
    "apply_quick_effect",

    # v5.0 升级 - 互动链系统
    "InteractionType",
    "InteractionResult",
    "RelationshipPhase",
    "InteractionOption",
    "InteractionNode",
    "InteractionChain",
    "InteractionHistory",
    "InteractionChainManager",
    "DailyCycleManager",
    "create_interaction_system",

    # v5.0 升级 - 分支叙事引擎
    "StoryRoute",
    "EndingType",
    "ConditionType",
    "StoryCondition",
    "StoryEffect",
    "DialogLine",
    "StoryChoice",
    "StoryNode",
    "StoryChapter",
    "StoryEnding",
    "CGEntry",
    "BranchingNarrativeEngine",
    "create_narrative_engine",

    # v5.0 升级 - 日记系统
    "DiaryMood",
    "DiaryCategory",
    "DiaryTemplate",
    "DiaryEntry",
    "MoodRecord",
    "DiaryTemplateEngine",
    "EnhancedDiarySystem",
    "create_diary_system",

    # v5.0 升级 - 相册系统
    "PhotoCategory",
    "PhotoRarity",
    "PhotoTag",
    "Photo",
    "Collection",
    "AlbumFilter",
    "EnhancedAlbumSystem",
    "create_album_system",

    # v5.0 升级 - 成长轨迹
    "EventType",
    "EventImportance",
    "TimelineEvent",
    "GrowthStats",
    "GrowthTimeline",
    "create_growth_timeline",

    # v5.1 升级 - 校园Galgame系统
    # NPC系统
    "NPCRole",
    "NPCRelationPhase",
    "NPCCharacter",
    "NPCRelationData",
    "NPCManager",
    "create_npc_system",

    # 校园场景系统
    "LocationCategory",
    "LocationStatus",
    "CampusLocation",
    "CampusLocationManager",
    "create_location_manager",

    # 关系网络系统
    "RelationType",
    "RelationStrength",
    "SocialCircleType",
    "NPCRelationship",
    "SocialCircle",
    "RelationshipNetworkManager",
    "create_relationship_network",

    # 时间周期系统
    "TimePeriod",
    "DayOfWeek",
    "GameTime",
    "SpecialDate",
    "TimeCycleManager",
    "create_time_cycle",

    # 社交行动系统
    "ActionCategory",
    "ActionResult",
    "SocialAction",
    "SocialActionManager",
    "create_social_action_manager",

    # 剧情追踪系统
    "StoryLineType",
    "StoryNodeType",
    "StoryLine",
    "StoryNode",
    "Achievement",
    "StoryTracker",
    "create_story_tracker",

    # 校园事件系统 (升级版)
    "SchoolEvent",
    "SchoolEventChoice",
    "SchoolEventManager",
    "create_event_manager",
]
