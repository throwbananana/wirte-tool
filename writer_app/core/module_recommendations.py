from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class ModuleRule:
    module_key: str
    keywords: List[str]
    reason: str
    priority: int = 50


@dataclass(frozen=True)
class ModuleRecommendation:
    module_key: str
    reason: str
    matched_keywords: List[str]


RULES: List[ModuleRule] = [
    ModuleRule(
        module_key="evidence_board",
        keywords=["线索", "证据", "案发", "凶手", "嫌疑", "推理", "侦探", "尸体", "死者", "谜团"],
        reason="文本包含推理线索关键词",
        priority=10
    ),
    ModuleRule(
        module_key="dual_timeline",
        keywords=["真相", "叙述", "时间线", "倒叙", "回忆"],
        reason="出现双时间线/叙事错位提示",
        priority=20
    ),
    ModuleRule(
        module_key="alibi",
        keywords=["不在场", "案发时间", "案发地点", "时间地点"],
        reason="出现不在场与时间地点核验提示",
        priority=25
    ),
    ModuleRule(
        module_key="heartbeat",
        keywords=["心动", "心跳", "告白", "吻", "暧昧", "恋爱", "牵手", "拥抱"],
        reason="文本包含情感推进关键词",
        priority=15
    ),
    ModuleRule(
        module_key="relationship",
        keywords=["关系", "羁绊", "恩怨", "师徒", "亲子", "搭档", "对立"],
        reason="文本包含人物关系关键词",
        priority=30
    ),
    ModuleRule(
        module_key="faction",
        keywords=["势力", "阵营", "组织", "帮派", "联盟", "政权", "权力", "争夺"],
        reason="文本包含势力对抗关键词",
        priority=18
    ),
    ModuleRule(
        module_key="iceberg",
        keywords=["设定", "世界观", "传说", "历史", "种族", "魔法", "科技"],
        reason="文本包含世界观设定关键词",
        priority=40
    ),
    ModuleRule(
        module_key="timeline",
        keywords=["时间", "日期", "日历", "某年", "某月", "某日"],
        reason="文本包含时间组织关键词",
        priority=35
    ),
    ModuleRule(
        module_key="flowchart",
        keywords=["分支", "选项", "路线", "结局", "True End", "Bad End", "多结局"],
        reason="文本包含分支叙事关键词",
        priority=28
    ),
    ModuleRule(
        module_key="variable",
        keywords=["变量", "flag", "数值", "条件", "好感度"],
        reason="文本包含条件变量关键词",
        priority=32
    ),
    ModuleRule(
        module_key="swimlanes",
        keywords=["多线", "并行", "视角切换"],
        reason="文本包含多线叙事关键词",
        priority=45
    ),
]


def recommend_modules(
    text: str,
    enabled_tools: Iterable[str],
    max_results: int = 1
) -> List[ModuleRecommendation]:
    text = text or ""
    enabled = set(enabled_tools or [])
    recommendations: List[ModuleRecommendation] = []

    for rule in sorted(RULES, key=lambda item: item.priority):
        if rule.module_key in enabled:
            continue
        matched = [kw for kw in rule.keywords if kw in text]
        if matched:
            recommendations.append(
                ModuleRecommendation(
                    module_key=rule.module_key,
                    reason=rule.reason,
                    matched_keywords=matched[:3]
                )
            )
        if len(recommendations) >= max_results:
            break

    return recommendations
