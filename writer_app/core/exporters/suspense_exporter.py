"""
Suspense Enhanced Markdown Exporter - Export suspense projects with additional analysis.

Provides enhanced Markdown export for suspense/mystery projects including:
- Truth vs. Narrative timeline comparison table
- Evidence/clue checklist
- Logic validation results
- Unresolved plot threads

Usage:
    from writer_app.core.exporters.suspense_exporter import SuspenseMarkdownExporter

    SuspenseMarkdownExporter.export(project_data, "/path/to/output.md")
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from writer_app.core.exporter import ExportFormat, MarkdownExporter


class SuspenseMarkdownExporter(ExportFormat):
    """Enhanced Markdown exporter for suspense/mystery projects."""

    key = "suspense_markdown"
    name = "悬疑增强 Markdown"
    extension = ".md"
    description = "包含时间线对比、线索清单和逻辑分析的增强 Markdown 导出"
    supported_types = ["Suspense"]
    priority_for_types = {"Suspense": 100}

    @classmethod
    def export(cls, project_data: Dict, file_path: str, **kwargs) -> bool:
        """
        Export suspense project with enhanced analysis.

        Args:
            project_data: Project data dict
            file_path: Output file path
            **kwargs:
                include_timeline: Include timeline comparison (default: True)
                include_evidence: Include evidence checklist (default: True)
                include_logic_check: Include logic validation (default: True)
                include_script: Include main script content (default: True)
                include_outline: Include outline (default: True)

        Returns:
            bool: True if successful
        """
        include_timeline = kwargs.get("include_timeline", True)
        include_evidence = kwargs.get("include_evidence", True)
        include_logic_check = kwargs.get("include_logic_check", True)
        include_script = kwargs.get("include_script", True)
        include_outline = kwargs.get("include_outline", True)

        lines = []
        script = project_data.get("script", {})
        title = script.get("title", "Untitled")

        # Title and metadata
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"> 项目类型: 悬疑/推理")
        lines.append("")

        # Table of Contents
        lines.append("## 目录")
        lines.append("")
        toc_items = []
        if include_timeline:
            toc_items.append("- [时间线对比](#时间线对比)")
        if include_evidence:
            toc_items.append("- [线索清单](#线索清单)")
        if include_logic_check:
            toc_items.append("- [逻辑分析](#逻辑分析)")
        if include_script:
            toc_items.append("- [正文内容](#正文内容)")
        if include_outline:
            toc_items.append("- [大纲结构](#大纲结构)")
        lines.extend(toc_items)
        lines.append("")
        lines.append("---")
        lines.append("")

        # Timeline Comparison Section
        if include_timeline:
            cls._add_timeline_section(lines, project_data)

        # Evidence Checklist Section
        if include_evidence:
            cls._add_evidence_section(lines, project_data)

        # Logic Check Section
        if include_logic_check:
            cls._add_logic_check_section(lines, project_data)

        # Main Script Content
        if include_script:
            cls._add_script_section(lines, project_data)

        # Outline
        if include_outline:
            cls._add_outline_section(lines, project_data)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    @classmethod
    def _add_timeline_section(cls, lines: List[str], project_data: Dict):
        """Add truth vs. narrative timeline comparison section."""
        lines.append("## 时间线对比")
        lines.append("")
        lines.append("真相时间线与叙述时间线的对比分析。")
        lines.append("")

        timelines = project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])
        lie_events = timelines.get("lie_events", [])

        if not truth_events and not lie_events:
            lines.append("*暂无时间线数据*")
            lines.append("")
        else:
            # Create comparison table
            lines.append("### 真相时间线")
            lines.append("")
            if truth_events:
                lines.append("| 时间 | 事件 | 涉及角色 | 地点 |")
                lines.append("|------|------|----------|------|")
                for event in sorted(truth_events, key=lambda x: x.get("time", "")):
                    time = event.get("time", "")
                    desc = event.get("description", "")
                    characters = ", ".join(event.get("characters", []))
                    location = event.get("location", "")
                    lines.append(f"| {time} | {desc} | {characters} | {location} |")
            else:
                lines.append("*暂无真相时间线事件*")
            lines.append("")

            lines.append("### 叙述时间线（读者视角）")
            lines.append("")
            if lie_events:
                lines.append("| 时间 | 事件 | 涉及角色 | 信息来源 |")
                lines.append("|------|------|----------|----------|")
                for event in sorted(lie_events, key=lambda x: x.get("time", "")):
                    time = event.get("time", "")
                    desc = event.get("description", "")
                    characters = ", ".join(event.get("characters", []))
                    source = event.get("source", "")
                    lines.append(f"| {time} | {desc} | {characters} | {source} |")
            else:
                lines.append("*暂无叙述时间线事件*")
            lines.append("")

            # Timeline discrepancies
            cls._add_timeline_discrepancies(lines, truth_events, lie_events)

        lines.append("---")
        lines.append("")

    @classmethod
    def _add_timeline_discrepancies(cls, lines: List[str], truth_events: List, lie_events: List):
        """Analyze discrepancies between truth and narrative timelines."""
        lines.append("### 时间线差异分析")
        lines.append("")

        truth_times = {e.get("time"): e for e in truth_events if e.get("time")}
        lie_times = {e.get("time"): e for e in lie_events if e.get("time")}

        discrepancies = []

        # Find events in truth but not in narrative
        for time, event in truth_times.items():
            if time not in lie_times:
                discrepancies.append({
                    "type": "hidden",
                    "time": time,
                    "description": event.get("description", ""),
                    "note": "真相事件未在叙述中出现"
                })

        # Find events in narrative but not in truth (fabricated)
        for time, event in lie_times.items():
            if time not in truth_times:
                discrepancies.append({
                    "type": "fabricated",
                    "time": time,
                    "description": event.get("description", ""),
                    "note": "叙述事件在真相中不存在"
                })

        # Find same-time events with different descriptions
        for time in set(truth_times.keys()) & set(lie_times.keys()):
            truth_desc = truth_times[time].get("description", "")
            lie_desc = lie_times[time].get("description", "")
            if truth_desc != lie_desc:
                discrepancies.append({
                    "type": "modified",
                    "time": time,
                    "truth": truth_desc,
                    "narrative": lie_desc,
                    "note": "同一时间事件描述存在差异"
                })

        if discrepancies:
            lines.append("| 类型 | 时间 | 说明 |")
            lines.append("|------|------|------|")
            for d in discrepancies:
                type_str = {"hidden": "🔒 隐藏", "fabricated": "✨ 虚构", "modified": "📝 篡改"}.get(d["type"], d["type"])
                note = d.get("note", "")
                if d["type"] == "modified":
                    note = f"真相: {d['truth']} → 叙述: {d['narrative']}"
                else:
                    note = d.get("description", "") + f" ({d.get('note', '')})"
                lines.append(f"| {type_str} | {d['time']} | {note} |")
        else:
            lines.append("*未发现时间线差异*")

        lines.append("")

    @classmethod
    def _add_evidence_section(cls, lines: List[str], project_data: Dict):
        """Add evidence/clue checklist section."""
        lines.append("## 线索清单")
        lines.append("")

        # Get evidence data from relationships or dedicated evidence structure
        relationships = project_data.get("relationships", {})
        evidence_nodes = [n for n in relationships.get("nodes", []) if n.get("type") == "evidence"]

        # Also check for evidence_data if exists
        evidence_data = project_data.get("evidence_data", {})
        evidence_items = evidence_data.get("items", [])

        if not evidence_nodes and not evidence_items:
            lines.append("*暂无线索数据*")
            lines.append("")
        else:
            # Combine evidence from both sources
            all_evidence = []

            for node in evidence_nodes:
                all_evidence.append({
                    "name": node.get("name", ""),
                    "description": node.get("description", ""),
                    "revealed": node.get("revealed", False),
                    "scene": node.get("scene_ref", ""),
                    "importance": node.get("importance", "normal")
                })

            for item in evidence_items:
                all_evidence.append({
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                    "revealed": item.get("is_revealed", False),
                    "scene": item.get("reveal_scene", ""),
                    "importance": item.get("importance", "normal")
                })

            # Group by revealed status
            revealed = [e for e in all_evidence if e.get("revealed")]
            hidden = [e for e in all_evidence if not e.get("revealed")]

            lines.append("### 已揭示线索")
            lines.append("")
            if revealed:
                for e in revealed:
                    importance_icon = {"critical": "🔴", "high": "🟠", "normal": "🟢", "low": "⚪"}.get(e["importance"], "🟢")
                    lines.append(f"- {importance_icon} **{e['name']}**")
                    if e.get("description"):
                        lines.append(f"  - {e['description']}")
                    if e.get("scene"):
                        lines.append(f"  - 揭示场景: {e['scene']}")
            else:
                lines.append("*暂无已揭示线索*")
            lines.append("")

            lines.append("### 待揭示线索")
            lines.append("")
            if hidden:
                for e in hidden:
                    importance_icon = {"critical": "🔴", "high": "🟠", "normal": "🟢", "low": "⚪"}.get(e["importance"], "🟢")
                    lines.append(f"- {importance_icon} **{e['name']}** *(待揭示)*")
                    if e.get("description"):
                        lines.append(f"  - {e['description']}")
            else:
                lines.append("*所有线索已揭示*")
            lines.append("")

            # Evidence summary
            lines.append("### 线索统计")
            lines.append("")
            total = len(all_evidence)
            revealed_count = len(revealed)
            lines.append(f"- 总线索数: {total}")
            lines.append(f"- 已揭示: {revealed_count}")
            lines.append(f"- 待揭示: {total - revealed_count}")
            if total > 0:
                lines.append(f"- 揭示率: {revealed_count / total * 100:.1f}%")
            lines.append("")

        lines.append("---")
        lines.append("")

    @classmethod
    def _add_logic_check_section(cls, lines: List[str], project_data: Dict):
        """Add logic validation section."""
        lines.append("## 逻辑分析")
        lines.append("")

        issues = []

        # Check 1: Timeline consistency
        cls._check_timeline_consistency(project_data, issues)

        # Check 2: Character alibi coverage
        cls._check_alibi_coverage(project_data, issues)

        # Check 3: Unresolved plot threads
        cls._check_unresolved_threads(project_data, issues)

        # Check 4: Evidence placement
        cls._check_evidence_placement(project_data, issues)

        if issues:
            # Group by severity
            critical = [i for i in issues if i.get("severity") == "critical"]
            warnings = [i for i in issues if i.get("severity") == "warning"]
            info = [i for i in issues if i.get("severity") == "info"]

            if critical:
                lines.append("### ❌ 严重问题")
                lines.append("")
                for issue in critical:
                    lines.append(f"- **{issue['title']}**")
                    lines.append(f"  - {issue['description']}")
                    if issue.get("suggestion"):
                        lines.append(f"  - 💡 建议: {issue['suggestion']}")
                lines.append("")

            if warnings:
                lines.append("### ⚠️ 警告")
                lines.append("")
                for issue in warnings:
                    lines.append(f"- **{issue['title']}**")
                    lines.append(f"  - {issue['description']}")
                    if issue.get("suggestion"):
                        lines.append(f"  - 💡 建议: {issue['suggestion']}")
                lines.append("")

            if info:
                lines.append("### ℹ️ 提示")
                lines.append("")
                for issue in info:
                    lines.append(f"- {issue['title']}: {issue['description']}")
                lines.append("")
        else:
            lines.append("✅ 未发现逻辑问题")
            lines.append("")

        lines.append("---")
        lines.append("")

    @classmethod
    def _check_timeline_consistency(cls, project_data: Dict, issues: List):
        """Check for timeline consistency issues."""
        timelines = project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])

        if not truth_events:
            return

        # Check for overlapping events with same character
        char_events = {}
        for event in truth_events:
            for char in event.get("characters", []):
                if char not in char_events:
                    char_events[char] = []
                char_events[char].append(event)

        for char, events in char_events.items():
            times = [e.get("time") for e in events if e.get("time")]
            if len(times) != len(set(times)):
                issues.append({
                    "severity": "warning",
                    "title": f"角色时间冲突: {char}",
                    "description": f"{char} 在同一时间出现在多个事件中",
                    "suggestion": "检查该角色的时间线是否合理"
                })

    @classmethod
    def _check_alibi_coverage(cls, project_data: Dict, issues: List):
        """Check if key characters have alibi coverage."""
        script = project_data.get("script", {})
        characters = script.get("characters", [])
        timelines = project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])

        # Find characters marked as suspects
        suspects = [c for c in characters if c.get("is_suspect") or "嫌疑" in c.get("tags", [])]

        if not suspects or not truth_events:
            return

        # Check if suspects have events during critical times
        for suspect in suspects:
            name = suspect.get("name", "")
            suspect_events = [e for e in truth_events if name in e.get("characters", [])]

            if len(suspect_events) == 0:
                issues.append({
                    "severity": "info",
                    "title": f"缺少不在场证明: {name}",
                    "description": f"嫌疑人 {name} 在真相时间线中没有事件记录",
                    "suggestion": "考虑为该角色添加不在场证明或活动轨迹"
                })

    @classmethod
    def _check_unresolved_threads(cls, project_data: Dict, issues: List):
        """Check for unresolved plot threads."""
        # Check for foreshadowing without payoff
        script = project_data.get("script", {})
        scenes = script.get("scenes", [])

        # Look for common suspense keywords that might indicate unresolved threads
        foreshadowing_keywords = ["之后再说", "稍后", "暂且不提", "留个悬念", "TODO", "待定"]

        for i, scene in enumerate(scenes):
            content = scene.get("content", "")
            notes = scene.get("notes", "")

            for keyword in foreshadowing_keywords:
                if keyword in content or keyword in notes:
                    issues.append({
                        "severity": "info",
                        "title": f"可能的未完成线索: 场景 {i + 1}",
                        "description": f"在 \"{scene.get('name', '')}\" 中发现标记 \"{keyword}\"",
                        "suggestion": "确认该线索是否已在后续场景中解决"
                    })

    @classmethod
    def _check_evidence_placement(cls, project_data: Dict, issues: List):
        """Check evidence placement and revelation order."""
        relationships = project_data.get("relationships", {})
        evidence_nodes = [n for n in relationships.get("nodes", []) if n.get("type") == "evidence"]

        critical_evidence = [e for e in evidence_nodes if e.get("importance") == "critical"]

        for evidence in critical_evidence:
            if not evidence.get("revealed") and not evidence.get("scene_ref"):
                issues.append({
                    "severity": "warning",
                    "title": f"关键线索未安排: {evidence.get('name', '')}",
                    "description": "该关键线索尚未安排揭示场景",
                    "suggestion": "为该关键线索选择合适的揭示时机"
                })

    @classmethod
    def _add_script_section(cls, lines: List[str], project_data: Dict):
        """Add main script content section."""
        lines.append("## 正文内容")
        lines.append("")

        script = project_data.get("script", {})
        scenes = script.get("scenes", [])

        # Characters overview
        chars = script.get("characters", [])
        if chars:
            lines.append("### 登场人物")
            lines.append("")
            for c in chars:
                name = c.get("name", "")
                desc = c.get("description", "")
                tags = c.get("tags", [])
                tag_str = f" `{'` `'.join(tags)}`" if tags else ""
                lines.append(f"- **{name}**{tag_str}: {desc}")
            lines.append("")

        # Scenes
        if scenes:
            lines.append("### 场景列表")
            lines.append("")
            for i, s in enumerate(scenes):
                lines.append(f"#### {i + 1}. {s.get('name', 'Untitled')}")
                lines.append(f"**地点**: {s.get('location', '')} | **时间**: {s.get('time', '')}")
                lines.append("")

                content = s.get("content", "")
                for line in content.split('\n'):
                    line = line.strip()
                    if not line:
                        lines.append("")
                        continue
                    # Format dialogue
                    match = re.match(r"^([^\s：:]+)[：:]\s*(.*)$", line)
                    if match:
                        name = match.group(1)
                        dialogue = match.group(2)
                        lines.append(f"**{name}**: {dialogue}")
                    else:
                        lines.append(line)

                lines.append("")
                lines.append("---")
                lines.append("")

        lines.append("")

    @classmethod
    def _add_outline_section(cls, lines: List[str], project_data: Dict):
        """Add outline structure section."""
        lines.append("## 大纲结构")
        lines.append("")

        outline = project_data.get("outline", {})
        if outline:
            cls._recursive_outline(outline, 0, lines)
        else:
            lines.append("*暂无大纲*")

        lines.append("")

    @classmethod
    def _recursive_outline(cls, node: Dict, level: int, lines: List[str]):
        """Recursively add outline nodes."""
        prefix = "#" * (level + 3) if level < 4 else "-" * (level - 3 + 1)
        name = node.get("name", "Untitled")
        lines.append(f"{prefix} {name}")

        if node.get("content"):
            lines.append(f"{node.get('content')}")
            lines.append("")

        for child in node.get("children", []):
            cls._recursive_outline(child, level + 1, lines)

    @classmethod
    def get_type_specific_options(cls, project_type: str) -> Dict[str, Any]:
        """Get Suspense-specific export options."""
        return {
            "include_timeline": True,
            "include_evidence": True,
            "include_logic_check": True,
            "include_script": True,
            "include_outline": True,
            "analysis_depth": ["basic", "detailed", "comprehensive"]
        }
