"""
Event Analyzer - 事件逻辑分析器

功能:
- 检测循环引用 (A -> B -> C -> A)
- 检测死路径 (无法到达的分支)
- 检测孤立事件 (无前置且无后续)
- 检测缺失引用 (next_event_id 指向不存在的事件)
- 检测无效效果 (effect_type 无效)
- 生成事件流程图数据
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class AnalysisIssueType(Enum):
    """Issue types for event analysis."""
    MISSING_REFERENCE = "missing_ref"
    CYCLE_DETECTED = "cycle"
    DEAD_END = "dead_end"
    ORPHAN_EVENT = "orphan"
    INVALID_EFFECT = "invalid_effect"
    DUPLICATE_ID = "duplicate_id"
    MISSING_REQUIRED_FIELD = "missing_field"


class IssueSeverity(Enum):
    """Severity levels for issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class AnalysisIssue:
    """Represents a single analysis issue."""
    issue_type: AnalysisIssueType
    severity: IssueSeverity
    event_id: str
    message: str
    related_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "event_id": self.event_id,
            "message": self.message,
            "related_ids": self.related_ids,
        }


@dataclass
class AnalysisReport:
    """Complete analysis report."""
    total_events: int
    single_count: int
    conditional_chain_count: int
    immediate_chain_count: int
    repeatable_count: int
    issues: List[AnalysisIssue] = field(default_factory=list)
    event_graph: Dict[str, List[str]] = field(default_factory=dict)
    reverse_graph: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == IssueSeverity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    def to_text(self) -> str:
        """Generate text report."""
        lines = []
        lines.append(f"事件分析报告")
        lines.append("=" * 40)
        lines.append(f"总事件数: {self.total_events}")
        lines.append(f"单独事件: {self.single_count}")
        lines.append(f"条件链式事件: {self.conditional_chain_count}")
        lines.append(f"即时链式事件: {self.immediate_chain_count}")
        lines.append(f"可重复事件: {self.repeatable_count}")
        lines.append(f"一次性事件: {self.total_events - self.repeatable_count}")
        lines.append("")
        lines.append(f"发现问题: {len(self.issues)} (错误: {self.error_count}, 警告: {self.warning_count})")
        lines.append("-" * 40)

        if self.issues:
            for issue in self.issues:
                severity_icon = {"error": "[错误]", "warning": "[警告]", "info": "[信息]"}.get(
                    issue.severity.value, "[?]"
                )
                lines.append(f"{severity_icon} {issue.event_id}: {issue.message}")
        else:
            lines.append("未发现问题")

        return "\n".join(lines)


# Valid effect types based on the event system
VALID_EFFECT_TYPES = {
    "affection", "npc_affection", "mood", "npc_mood",
    "flag", "item", "achievement", "unlock_location",
    "time_advance", "event_completed",
}


class EventAnalyzer:
    """Comprehensive event logic analyzer."""

    def __init__(self, events: List[Dict]):
        self.events = events
        self._id_map: Dict[str, Dict] = {}
        self._build_id_map()
        self.graph: Dict[str, List[str]] = {}
        self.reverse_graph: Dict[str, List[str]] = {}
        self._build_graphs()

    def _build_id_map(self):
        """Build event ID to event object map."""
        self._id_map = {}
        for event in self.events:
            event_id = event.get("id") or event.get("event_id")
            if event_id:
                self._id_map[event_id] = event

    def _build_graphs(self):
        """Build directed graph from events."""
        self.graph = {eid: [] for eid in self._id_map}
        self.reverse_graph = {eid: [] for eid in self._id_map}

        for event_id, event in self._id_map.items():
            # Get outgoing edges from choices
            for choice in event.get("choices", []):
                next_id = choice.get("next_event_id")
                if next_id:
                    self.graph[event_id].append(next_id)
                    if next_id in self.reverse_graph:
                        self.reverse_graph[next_id].append(event_id)

            # Get outgoing edges from prerequisites (reverse direction)
            for prereq in event.get("prerequisites", []):
                if prereq in self.graph:
                    self.graph[prereq].append(event_id)
                    self.reverse_graph[event_id].append(prereq)

    def analyze(self) -> AnalysisReport:
        """Run all analysis checks and return report."""
        issues: List[AnalysisIssue] = []

        # Run all checks
        issues.extend(self._check_duplicate_ids())
        issues.extend(self._check_missing_references())
        issues.extend(self._detect_cycles())
        issues.extend(self._find_dead_ends())
        issues.extend(self._find_orphans())
        issues.extend(self._validate_effects())
        issues.extend(self._check_required_fields())

        # Count event types
        single_count = 0
        conditional_chain_count = 0
        immediate_chain_count = 0
        repeatable_count = 0

        for event in self.events:
            prereqs = event.get("prerequisites", [])
            has_next = any(c.get("next_event_id") for c in event.get("choices", []))

            if prereqs:
                conditional_chain_count += 1
            elif has_next:
                immediate_chain_count += 1
            else:
                single_count += 1

            if event.get("repeatable", True):
                repeatable_count += 1

        return AnalysisReport(
            total_events=len(self.events),
            single_count=single_count,
            conditional_chain_count=conditional_chain_count,
            immediate_chain_count=immediate_chain_count,
            repeatable_count=repeatable_count,
            issues=issues,
            event_graph=self.graph,
            reverse_graph=self.reverse_graph,
        )

    def _check_duplicate_ids(self) -> List[AnalysisIssue]:
        """Check for duplicate event IDs."""
        issues = []
        seen_ids: Dict[str, int] = {}

        for i, event in enumerate(self.events):
            event_id = event.get("id") or event.get("event_id") or f"index_{i}"
            if event_id in seen_ids:
                issues.append(AnalysisIssue(
                    issue_type=AnalysisIssueType.DUPLICATE_ID,
                    severity=IssueSeverity.ERROR,
                    event_id=event_id,
                    message=f"重复的事件ID: '{event_id}' (首次出现在索引 {seen_ids[event_id]})",
                    related_ids=[event_id],
                ))
            else:
                seen_ids[event_id] = i

        return issues

    def _check_missing_references(self) -> List[AnalysisIssue]:
        """Check for references to non-existent events."""
        issues = []

        for event_id, event in self._id_map.items():
            # Check next_event_id in choices
            for i, choice in enumerate(event.get("choices", [])):
                next_id = choice.get("next_event_id")
                if next_id and next_id not in self._id_map:
                    issues.append(AnalysisIssue(
                        issue_type=AnalysisIssueType.MISSING_REFERENCE,
                        severity=IssueSeverity.ERROR,
                        event_id=event_id,
                        message=f"选项 {i+1} 引用了不存在的事件: '{next_id}'",
                        related_ids=[next_id],
                    ))

            # Check prerequisites
            for prereq in event.get("prerequisites", []):
                if prereq not in self._id_map:
                    issues.append(AnalysisIssue(
                        issue_type=AnalysisIssueType.MISSING_REFERENCE,
                        severity=IssueSeverity.ERROR,
                        event_id=event_id,
                        message=f"前置条件引用了不存在的事件: '{prereq}'",
                        related_ids=[prereq],
                    ))

        return issues

    def _detect_cycles(self) -> List[AnalysisIssue]:
        """Detect cycles using DFS with three-color marking."""
        issues = []
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {eid: WHITE for eid in self._id_map}
        found_cycles: Set[frozenset] = set()

        def dfs(node: str, path: List[str]):
            if node not in color:
                return  # Node doesn't exist

            if color[node] == GRAY:
                # Cycle found
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycle_set = frozenset(cycle)

                # Avoid duplicate cycle reports
                if cycle_set not in found_cycles:
                    found_cycles.add(cycle_set)
                    issues.append(AnalysisIssue(
                        issue_type=AnalysisIssueType.CYCLE_DETECTED,
                        severity=IssueSeverity.ERROR,
                        event_id=node,
                        message=f"检测到事件循环: {' -> '.join(cycle)}",
                        related_ids=cycle,
                    ))
                return

            if color[node] == BLACK:
                return  # Already processed

            color[node] = GRAY
            for neighbor in self.graph.get(node, []):
                dfs(neighbor, path + [node])
            color[node] = BLACK

        for event_id in self._id_map:
            if color[event_id] == WHITE:
                dfs(event_id, [])

        return issues

    def _find_dead_ends(self) -> List[AnalysisIssue]:
        """Find events that lead nowhere (no choices, not end events)."""
        issues = []

        for event_id, event in self._id_map.items():
            choices = event.get("choices", [])

            # If event has no choices and is not explicitly marked as terminal
            if not choices:
                # Check if this is a terminal event (no outgoing edges expected)
                if not event.get("is_terminal", False):
                    # Check if any other events reference this as prerequisite
                    has_dependents = bool(self.graph.get(event_id, []))
                    if not has_dependents:
                        issues.append(AnalysisIssue(
                            issue_type=AnalysisIssueType.DEAD_END,
                            severity=IssueSeverity.WARNING,
                            event_id=event_id,
                            message="事件没有选项且没有后续事件 (可能是死路径)",
                        ))

        return issues

    def _find_orphans(self) -> List[AnalysisIssue]:
        """Find events that cannot be reached (no predecessors except start events)."""
        issues = []

        # Events with no incoming edges and no way to trigger
        for event_id, event in self._id_map.items():
            incoming = self.reverse_graph.get(event_id, [])
            prereqs = event.get("prerequisites", [])
            conditions = event.get("conditions", [])

            # If no incoming edges and no prerequisites and no trigger conditions
            if not incoming and not prereqs and not conditions:
                # Check if it's a start/random event (these are OK to be orphans)
                event_type = event.get("type", event.get("event_type", "random"))
                if event_type not in ("random", "scheduled", "story", "special"):
                    issues.append(AnalysisIssue(
                        issue_type=AnalysisIssueType.ORPHAN_EVENT,
                        severity=IssueSeverity.INFO,
                        event_id=event_id,
                        message="事件没有前置条件，可能无法触发 (孤立事件)",
                    ))

        return issues

    def _validate_effects(self) -> List[AnalysisIssue]:
        """Validate effect types in choices."""
        issues = []

        for event_id, event in self._id_map.items():
            for i, choice in enumerate(event.get("choices", [])):
                for j, effect in enumerate(choice.get("effects", [])):
                    effect_type = effect.get("effect_type", effect.get("type"))
                    if effect_type and effect_type not in VALID_EFFECT_TYPES:
                        issues.append(AnalysisIssue(
                            issue_type=AnalysisIssueType.INVALID_EFFECT,
                            severity=IssueSeverity.WARNING,
                            event_id=event_id,
                            message=f"选项 {i+1} 效果 {j+1} 使用了未知的效果类型: '{effect_type}'",
                        ))

        return issues

    def _check_required_fields(self) -> List[AnalysisIssue]:
        """Check for missing required fields."""
        issues = []
        required_fields = ["id", "title"]

        for i, event in enumerate(self.events):
            event_id = event.get("id") or event.get("event_id") or f"index_{i}"

            for field_name in required_fields:
                if not event.get(field_name):
                    # Allow event_id as alternative to id
                    if field_name == "id" and event.get("event_id"):
                        continue
                    issues.append(AnalysisIssue(
                        issue_type=AnalysisIssueType.MISSING_REQUIRED_FIELD,
                        severity=IssueSeverity.WARNING,
                        event_id=event_id,
                        message=f"缺少必填字段: '{field_name}'",
                    ))

        return issues

    def get_event_chain(self, start_id: str, max_depth: int = 10) -> List[str]:
        """Get the chain of events starting from a given event."""
        chain = []
        visited = set()
        current = start_id

        while current and current not in visited and len(chain) < max_depth:
            if current not in self._id_map:
                break
            chain.append(current)
            visited.add(current)

            # Get first next_event_id from choices
            event = self._id_map[current]
            next_id = None
            for choice in event.get("choices", []):
                if choice.get("next_event_id"):
                    next_id = choice.get("next_event_id")
                    break
            current = next_id

        return chain
