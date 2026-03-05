from dataclasses import dataclass, field
from typing import Dict, List, Iterable, Optional

from writer_app.core.typed_data import DataModule


@dataclass(frozen=True)
class ModuleInfo:
    key: str
    name: str
    desc: str
    group: str = ""
    data_modules: List[DataModule] = field(default_factory=list)
    ai_hint: str = ""
    ui_visible: bool = True
    order: int = 0


MODULES: Dict[str, ModuleInfo] = {
    "outline": ModuleInfo(
        key="outline",
        name="思维导图/大纲",
        desc="核心结构化工具，组织章节与节点。",
        group="core",
        data_modules=[DataModule.OUTLINE],
        order=10
    ),
    "script": ModuleInfo(
        key="script",
        name="剧本写作",
        desc="场景写作与正文编辑。",
        group="core",
        data_modules=[DataModule.SCRIPT],
        order=20
    ),
    "char_events": ModuleInfo(
        key="char_events",
        name="人物事件",
        desc="记录人物关键事件与轨迹。",
        group="structure",
        data_modules=[DataModule.SCRIPT],
        order=30
    ),
    "story_curve": ModuleInfo(
        key="story_curve",
        name="故事曲线",
        desc="节奏与张力曲线的可视化。",
        group="structure",
        data_modules=[DataModule.SCRIPT],
        order=40
    ),
    "evidence_board": ModuleInfo(
        key="evidence_board",
        name="线索墙",
        desc="整理线索与证据的关系网络。",
        group="suspense",
        data_modules=[DataModule.EVIDENCE, DataModule.RELATIONSHIPS],
        ai_hint="已启用线索墙，请关注证据链、伏笔与逻辑闭环。",
        order=50
    ),
    "dual_timeline": ModuleInfo(
        key="dual_timeline",
        name="表里双轨图",
        desc="真相/叙述两条时间线对照。",
        group="suspense",
        data_modules=[DataModule.TIMELINES],
        ai_hint="已启用双轨时间线，请关注表里时间一致性。",
        order=60
    ),
    "timeline": ModuleInfo(
        key="timeline",
        name="时间轴",
        desc="编排事件顺序与时间线。",
        group="planning",
        data_modules=[DataModule.TIMELINES],
        ai_hint="已启用时间轴，请关注事件时间顺序与因果关系。",
        order=70
    ),
    "relationship": ModuleInfo(
        key="relationship",
        name="人物关系图",
        desc="可视化人物关系网络。",
        group="character",
        data_modules=[DataModule.RELATIONSHIPS],
        ai_hint="已启用人物关系图，请关注关系变化与冲突走向。",
        order=80
    ),
    "kanban": ModuleInfo(
        key="kanban",
        name="场次看板",
        desc="管理场次进度与状态。",
        group="planning",
        data_modules=[DataModule.SCRIPT],
        order=90
    ),
    "calendar": ModuleInfo(
        key="calendar",
        name="故事日历",
        desc="按日期查看事件分布。",
        group="planning",
        data_modules=[DataModule.SCRIPT],
        order=100
    ),
    "wiki": ModuleInfo(
        key="wiki",
        name="世界观百科",
        desc="整理设定、地点、人物与物品。",
        group="world",
        data_modules=[DataModule.WORLD],
        ai_hint="已启用世界观百科，请关注设定一致性与条目扩展。",
        order=110
    ),
    "analytics": ModuleInfo(
        key="analytics",
        name="数据统计",
        desc="项目指标与进度统计。",
        group="analysis",
        data_modules=[DataModule.SCRIPT],
        order=120
    ),
    "swimlanes": ModuleInfo(
        key="swimlanes",
        name="故事泳道",
        desc="多角色并行线索的可视化。",
        group="structure",
        data_modules=[DataModule.SCRIPT],
        order=130
    ),
    "research": ModuleInfo(
        key="research",
        name="资料搜集",
        desc="记录资料与来源。",
        group="assistant",
        data_modules=[DataModule.RESEARCH],
        order=140
    ),
    "reverse_engineering": ModuleInfo(
        key="reverse_engineering",
        name="反推导学习",
        desc="拆解文本结构与创作思路。",
        group="assistant",
        order=150
    ),
    "ideas": ModuleInfo(
        key="ideas",
        name="灵感箱",
        desc="收集与整理灵感条目。",
        group="assistant",
        data_modules=[DataModule.IDEAS],
        order=160
    ),
    "training": ModuleInfo(
        key="training",
        name="创意训练",
        desc="进行创意练习与挑战。",
        group="assistant",
        order=170
    ),
    "chat": ModuleInfo(
        key="chat",
        name="项目对话",
        desc="项目内对话与提示。",
        group="assistant",
        order=180
    ),
    "heartbeat": ModuleInfo(
        key="heartbeat",
        name="心动追踪",
        desc="记录情感节奏与关键节点。",
        group="romance",
        data_modules=[DataModule.HEARTBEAT],
        ai_hint="已启用心动追踪，请关注情感节奏与关系推进。",
        order=190
    ),
    "alibi": ModuleInfo(
        key="alibi",
        name="不在场证明",
        desc="时间与地点的逻辑核验。",
        group="suspense",
        data_modules=[DataModule.SCRIPT],
        ai_hint="已启用不在场证明，请关注时间地点一致性。",
        order=200
    ),
    "iceberg": ModuleInfo(
        key="iceberg",
        name="世界冰山",
        desc="世界观设定分层构建。",
        group="world",
        data_modules=[DataModule.WORLD],
        ai_hint="已启用世界冰山，请关注显性与隐性设定层级。",
        order=210
    ),
    "faction": ModuleInfo(
        key="faction",
        name="势力矩阵",
        desc="势力关系与阵营冲突。",
        group="world",
        data_modules=[DataModule.FACTIONS],
        ai_hint="已启用势力矩阵，请关注阵营关系与冲突升级。",
        order=220
    ),
    "variable": ModuleInfo(
        key="variable",
        name="变量管理",
        desc="分支变量与条件判定。",
        group="interactive",
        data_modules=[DataModule.VARIABLES],
        ai_hint="已启用变量管理，请关注分支条件与结果一致性。",
        order=230
    ),
    "flowchart": ModuleInfo(
        key="flowchart",
        name="剧情流向",
        desc="剧情分支与场景跳转。",
        group="interactive",
        data_modules=[DataModule.SCRIPT],
        ai_hint="已启用剧情流向，请关注分支结构与闭环。",
        order=240
    ),
    "galgame_assets": ModuleInfo(
        key="galgame_assets",
        name="资源管理",
        desc="立绘/背景/CG 等资产管理。",
        group="interactive",
        data_modules=[DataModule.GALGAME_ASSETS],
        ui_visible=False,
        order=250
    ),
}


def get_module_info(key: str) -> Optional[ModuleInfo]:
    return MODULES.get(key)


def get_all_modules() -> List[ModuleInfo]:
    return list(MODULES.values())


def get_visible_modules() -> List[ModuleInfo]:
    return [info for info in MODULES.values() if info.ui_visible]


def get_ordered_module_keys(visible_only: bool = False) -> List[str]:
    modules = get_visible_modules() if visible_only else get_all_modules()
    return [info.key for info in sorted(modules, key=lambda item: item.order)]


def get_module_display_name(key: str) -> str:
    info = get_module_info(key)
    return info.name if info else key


def get_module_ai_hints(keys: Iterable[str]) -> List[str]:
    hints = []
    for key in keys:
        info = get_module_info(key)
        if info and info.ai_hint:
            hints.append(info.ai_hint)
    return hints
