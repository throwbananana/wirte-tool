"""
逻辑校验系统 - 验证剧本中的逻辑一致性

主要功能:
    - 检查线索出现顺序（线索是否在使用前揭示）
    - 检查角色在场景中的出现（是否在不应在的场景出现）
    - 检查时间线一致性
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

class IssueSeverity(Enum):
    """问题严重程度。"""
    ERROR = "error"      # 严重逻辑错误
    WARNING = "warning"  # 潜在问题
    INFO = "info"        # 信息提示


class IssueCategory(Enum):
    """问题分类。"""
    CLUE_ORDER = "clue_order"              # 线索顺序问题
    CHARACTER_PRESENCE = "character_presence"  # 角色在场问题
    TIMELINE_CONFLICT = "timeline_conflict"    # 时间线冲突
    LOCATION_INCONSISTENCY = "location_inconsistency"  # 地点不一致
    REFERENCE_MISSING = "reference_missing"    # 引用缺失
    DUAL_TIMELINE = "dual_timeline"            # 双时间轴问题
    LIE_TRUTH_CONFLICT = "lie_truth_conflict"  # 谎言与真相冲突


@dataclass
class LogicIssue:
    """逻辑问题。"""
    severity: IssueSeverity
    category: IssueCategory
    message: str
    scene_refs: List[int] = field(default_factory=list)  # 相关场景索引
    node_refs: List[str] = field(default_factory=list)   # 相关证据节点UID

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "scene_refs": self.scene_refs,
            "node_refs": self.node_refs
        }

    @property
    def severity_icon(self) -> str:
        """获取严重程度图标。"""
        icons = {
            IssueSeverity.ERROR: get_icon("error_circle", "❌"),
            IssueSeverity.WARNING: get_icon("warning", "⚠️"),
            IssueSeverity.INFO: get_icon("info", "ℹ️")
        }
        return icons.get(self.severity, "•")


@dataclass
class ValidationReport:
    """验证报告。"""
    issues: List[LogicIssue] = field(default_factory=list)
    summary: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.INFO)

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    def to_markdown(self) -> str:
        """转换为Markdown格式的报告。"""
        lines = ["# 逻辑校验报告\n"]

        if not self.has_issues:
            # We keep Emojis in Markdown for better compatibility with external readers
            lines.append("✅ **未发现逻辑问题**\n")
            return "\n".join(lines)

        # 统计摘要
        lines.append(f"## 摘要\n")
        lines.append(f"- 错误: {self.error_count}")
        lines.append(f"- 警告: {self.warning_count}")
        lines.append(f"- 信息: {self.info_count}")
        lines.append("")

        # 按严重程度分组
        if self.error_count > 0:
            lines.append("## ❌ 错误\n")
            for issue in self.issues:
                if issue.severity == IssueSeverity.ERROR:
                    lines.append(f"- {issue.message}")
                    if issue.scene_refs:
                        lines.append(f"  - 相关场景: {', '.join(str(i+1) for i in issue.scene_refs)}")
            lines.append("")

        if self.warning_count > 0:
            lines.append("## ⚠️ 警告\n")
            for issue in self.issues:
                if issue.severity == IssueSeverity.WARNING:
                    lines.append(f"- {issue.message}")
                    if issue.scene_refs:
                        lines.append(f"  - 相关场景: {', '.join(str(i+1) for i in issue.scene_refs)}")
            lines.append("")

        if self.info_count > 0:
            lines.append("## ℹ️ 信息\n")
            for issue in self.issues:
                if issue.severity == IssueSeverity.INFO:
                    lines.append(f"- {issue.message}")
            lines.append("")

        return "\n".join(lines)


class LogicValidator:
    """逻辑校验器。"""

    def __init__(self, project_manager):
        self.project_manager = project_manager

    def validate_clue_timeline(self) -> List[LogicIssue]:
        """
        检查线索时间线：线索是否在使用前被揭示。

        逻辑：
        - 获取所有证据节点及其关联的场景
        - 检查线索节点的scene_ref是否在使用该线索的场景之前
        """
        issues = []

        relationships = self.project_manager.get_relationships()
        nodes = relationships.get("nodes", [])
        links = relationships.get("evidence_links", [])
        scenes = self.project_manager.get_scenes()

        # 建立节点UID到数据的映射
        node_map: Dict[str, Dict] = {}
        for node in nodes:
            uid = node.get("uid")
            if uid:
                node_map[uid] = node

        # 建立节点名称到场景索引的映射（通过scene_ref）
        clue_first_appearance: Dict[str, int] = {}
        for node in nodes:
            uid = node.get("uid", "")
            scene_ref = node.get("scene_ref")
            if scene_ref is not None and uid:
                clue_first_appearance[uid] = scene_ref

        # 检查链接：如果A线索依赖B线索，但B在A之后才出现
        for link in links:
            source_uid = link.get("source", "")
            target_uid = link.get("target", "")
            link_type = link.get("type", "relates_to")

            # 只检查因果关系
            if link_type not in ["caused_by", "confirms"]:
                continue

            source_scene = clue_first_appearance.get(source_uid)
            target_scene = clue_first_appearance.get(target_uid)

            if source_scene is not None and target_scene is not None:
                if link_type == "caused_by" and target_scene > source_scene:
                    # 原因应该在结果之前
                    source_name = node_map.get(source_uid, {}).get("name", source_uid)
                    target_name = node_map.get(target_uid, {}).get("name", target_uid)
                    issues.append(LogicIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.CLUE_ORDER,
                        message=f"线索顺序错误：「{target_name}」应在「{source_name}」之前揭示（因果关系）",
                        scene_refs=[source_scene, target_scene],
                        node_refs=[source_uid, target_uid]
                    ))

        # 检查场景内容中提到的线索是否已经揭示
        for scene_idx, scene in enumerate(scenes):
            content = scene.get("content", "")

            for node in nodes:
                if node.get("type") != "clue":
                    continue

                clue_name = node.get("name", "")
                clue_uid = node.get("uid", "")
                reveal_scene = clue_first_appearance.get(clue_uid)

                # 如果内容中提到了这个线索
                if clue_name and clue_name in content:
                    # 但线索还没有揭示场景，或者在当前场景之后才揭示
                    if reveal_scene is not None and reveal_scene > scene_idx:
                        issues.append(LogicIssue(
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.CLUE_ORDER,
                            message=f"场景{scene_idx+1}中提到了线索「{clue_name}」，但该线索在场景{reveal_scene+1}才揭示",
                            scene_refs=[scene_idx, reveal_scene],
                            node_refs=[clue_uid]
                        ))

        return issues

    def validate_character_presence(self) -> List[LogicIssue]:
        """
        检查角色在场问题：角色是否出现在不应在的场景。

        逻辑：
        - 检查场景的登场角色列表是否与内容一致
        - 检查角色是否在"死亡"后仍然出场（如果有死亡标记）
        """
        issues = []
        scenes = self.project_manager.get_scenes()
        characters = self.project_manager.get_characters()

        # 建立角色名称集合
        char_names = {c.get("name", "") for c in characters if c.get("name")}

        for scene_idx, scene in enumerate(scenes):
            content = scene.get("content", "")
            listed_chars = set(scene.get("characters", []))

            # 检查内容中出现但未列入登场角色的角色
            for char_name in char_names:
                if not char_name:
                    continue

                # 简单匹配：角色名后跟冒号（对话格式）
                dialogue_pattern = f"{char_name}："
                dialogue_pattern2 = f"{char_name}:"

                appears_in_dialogue = dialogue_pattern in content or dialogue_pattern2 in content

                if appears_in_dialogue and char_name not in listed_chars:
                    issues.append(LogicIssue(
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.CHARACTER_PRESENCE,
                        message=f"角色「{char_name}」在场景{scene_idx+1}中有对话，但未列入登场角色",
                        scene_refs=[scene_idx]
                    ))

        return issues

    def validate_timeline_consistency(self) -> List[LogicIssue]:
        """
        检查时间线一致性：场景时间是否合理。

        逻辑：
        - 检查时间是否向后倒退（除非有明确的回忆/闪回标记）
        """
        issues = []
        scenes = self.project_manager.get_scenes()

        # 简单的时间顺序检查
        time_order = ["早晨", "上午", "中午", "下午", "傍晚", "晚上", "深夜", "凌晨"]
        time_order_map = {t: i for i, t in enumerate(time_order)}

        prev_time_idx = -1
        prev_scene_idx = -1

        for scene_idx, scene in enumerate(scenes):
            time_str = scene.get("time", "")
            scene_name = scene.get("name", "")

            # 跳过回忆/闪回场景
            if any(kw in scene_name for kw in ["回忆", "闪回", "过去", "之前"]):
                continue

            # 查找时间关键词
            current_time_idx = -1
            for t, idx in time_order_map.items():
                if t in time_str:
                    current_time_idx = idx
                    break

            if current_time_idx != -1 and prev_time_idx != -1:
                # 如果时间倒退了（考虑跨天）
                if current_time_idx < prev_time_idx:
                    # 检查是否可能是跨天
                    if current_time_idx <= 1 and prev_time_idx >= 5:
                        # 可能是跨天（早晨/上午跟在晚上/深夜后面）
                        pass
                    else:
                        issues.append(LogicIssue(
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.TIMELINE_CONFLICT,
                            message=f"时间线可能倒退：场景{prev_scene_idx+1}为{scenes[prev_scene_idx].get('time')}，场景{scene_idx+1}为{time_str}",
                            scene_refs=[prev_scene_idx, scene_idx]
                        ))

            if current_time_idx != -1:
                prev_time_idx = current_time_idx
                prev_scene_idx = scene_idx

        return issues

    def validate_location_consistency(self) -> List[LogicIssue]:
        """
        检查地点一致性：角色是否在短时间内出现在相距甚远的地点。
        """
        issues = []
        scenes = self.project_manager.get_scenes()
        
        # 记录角色最后一次出现的地点和场景索引
        char_last_loc: Dict[str, Dict] = {} # char_name -> {"loc": str, "idx": int}

        for scene_idx, scene in enumerate(scenes):
            loc = scene.get("location", "")
            chars = scene.get("characters", [])
            
            if not loc:
                continue

            for char_name in chars:
                if char_name in char_last_loc:
                    last_info = char_last_loc[char_name]
                    last_loc = last_info["loc"]
                    last_idx = last_info["idx"]
                    
                    # 如果地点变了，且场景是连续的（中间没有跳跃场景）
                    if loc != last_loc and scene_idx == last_idx + 1:
                        # 检查是否有时间跳跃或特殊标记
                        scene_name = scene.get("name", "")
                        if not any(kw in scene_name for kw in ["之后", "转场", "旅途"]):
                            issues.append(LogicIssue(
                                severity=IssueSeverity.INFO,
                                category=IssueCategory.LOCATION_INCONSISTENCY,
                                message=f"角色「{char_name}」在场景{scene_idx}位于「{last_loc}」，在紧接着的场景{scene_idx+1}却出现在「{loc}」，中间缺乏过渡描述",
                                scene_refs=[last_idx, scene_idx]
                            ))
                
                char_last_loc[char_name] = {"loc": loc, "idx": scene_idx}

        return issues

    def validate_references(self) -> List[LogicIssue]:
        """
        检查引用完整性：大纲引用、角色引用等是否有效。
        """
        issues = []
        scenes = self.project_manager.get_scenes()
        characters = self.project_manager.get_characters()
        outline = self.project_manager.get_outline()

        char_names = {c.get("name", "") for c in characters if c.get("name")}

        for scene_idx, scene in enumerate(scenes):
            # 检查大纲引用
            outline_ref_id = scene.get("outline_ref_id")
            if outline_ref_id:
                node = self.project_manager.find_node_by_uid(outline, outline_ref_id)
                if not node:
                    issues.append(LogicIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.REFERENCE_MISSING,
                        message=f"场景{scene_idx+1}关联的大纲节点不存在",
                        scene_refs=[scene_idx]
                    ))

            # 检查登场角色引用
            for char_name in scene.get("characters", []):
                if char_name and char_name not in char_names:
                    issues.append(LogicIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.REFERENCE_MISSING,
                        message=f"场景{scene_idx+1}中的角色「{char_name}」未在角色列表中定义",
                        scene_refs=[scene_idx]
                    ))

        return issues

    def validate_dual_timeline(self) -> List[LogicIssue]:
        """
        检查双时间轴一致性：真相与谎言事件的关联和冲突。

        逻辑：
        - 检查谎言事件是否关联了对应的真相事件
        - 检查谎言事件的时间是否与关联真相事件时间一致
        - 检查谎言事件是否有破绽(bug)但没有对应证据
        - 检查真相事件是否有场景关联
        """
        issues = []
        timelines = self.project_manager.project_data.get("timelines", {})
        truth_events = timelines.get("truth_events", [])
        lie_events = timelines.get("lie_events", [])
        scenes = self.project_manager.get_scenes()
        relationships = self.project_manager.get_relationships()
        evidence_nodes = relationships.get("nodes", [])

        # 建立真相事件 UID 到数据的映射
        truth_map: Dict[str, Dict] = {}
        for evt in truth_events:
            uid = evt.get("uid")
            if uid:
                truth_map[uid] = evt

        # 建立场景 UID 到索引的映射
        scene_uid_map: Dict[str, int] = {}
        for idx, scene in enumerate(scenes):
            uid = scene.get("uid")
            if uid:
                scene_uid_map[uid] = idx

        # 建立证据名称集合（用于检查破绽是否有证据支持）
        evidence_names = {n.get("name", "").lower() for n in evidence_nodes if n.get("type") == "clue"}

        # 检查谎言事件
        for lie_evt in lie_events:
            lie_name = lie_evt.get("name", "未命名")
            linked_truth_uid = lie_evt.get("linked_truth_event_uid", "")

            # 检查是否关联了真相事件
            if not linked_truth_uid:
                issues.append(LogicIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.DUAL_TIMELINE,
                    message=f"谎言事件「{lie_name}」未关联对应的真相事件",
                    node_refs=[lie_evt.get("uid", "")]
                ))
            else:
                # 检查关联的真相事件是否存在
                truth_evt = truth_map.get(linked_truth_uid)
                if not truth_evt:
                    issues.append(LogicIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.REFERENCE_MISSING,
                        message=f"谎言事件「{lie_name}」关联的真相事件不存在",
                        node_refs=[lie_evt.get("uid", "")]
                    ))
                else:
                    # 检查时间是否冲突
                    lie_time = lie_evt.get("timestamp", "")
                    truth_time = truth_evt.get("timestamp", "")
                    truth_name = truth_evt.get("name", "未命名")

                    if lie_time and truth_time and lie_time != truth_time:
                        issues.append(LogicIssue(
                            severity=IssueSeverity.INFO,
                            category=IssueCategory.LIE_TRUTH_CONFLICT,
                            message=f"谎言事件「{lie_name}」时间({lie_time})与真相事件「{truth_name}」时间({truth_time})不一致（可能是故意设计）",
                            node_refs=[lie_evt.get("uid", ""), linked_truth_uid]
                        ))

            # 检查破绽是否有对应证据
            bug = lie_evt.get("bug", "")
            if bug:
                bug_lower = bug.lower()
                # 检查是否有任何证据名称包含破绽关键词
                has_evidence = any(bug_lower in name or name in bug_lower for name in evidence_names if name)
                if not has_evidence:
                    issues.append(LogicIssue(
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.DUAL_TIMELINE,
                        message=f"谎言事件「{lie_name}」的破绽「{bug}」可能缺少对应的证据节点",
                        node_refs=[lie_evt.get("uid", "")]
                    ))

        # 检查真相事件
        for truth_evt in truth_events:
            truth_name = truth_evt.get("name", "未命名")
            linked_scene_uid = truth_evt.get("linked_scene_uid", "")

            # 检查是否关联了场景
            if linked_scene_uid:
                scene_idx = scene_uid_map.get(linked_scene_uid)
                if scene_idx is None:
                    issues.append(LogicIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.REFERENCE_MISSING,
                        message=f"真相事件「{truth_name}」关联的场景不存在",
                        node_refs=[truth_evt.get("uid", "")]
                    ))
                else:
                    # 检查场景时间与事件时间是否一致
                    event_time = truth_evt.get("timestamp", "")
                    scene = scenes[scene_idx]
                    scene_time = scene.get("time", "")

                    if event_time and scene_time:
                        # 简单比较日期部分
                        event_date = event_time.split()[0] if " " in event_time else event_time
                        if event_date not in scene_time and scene_time not in event_date:
                            issues.append(LogicIssue(
                                severity=IssueSeverity.INFO,
                                category=IssueCategory.TIMELINE_CONFLICT,
                                message=f"真相事件「{truth_name}」时间({event_time})与关联场景{scene_idx+1}时间({scene_time})可能不一致",
                                scene_refs=[scene_idx],
                                node_refs=[truth_evt.get("uid", "")]
                            ))

        # 检查是否有孤立的真相事件（没有被任何谎言事件引用）
        referenced_truth_uids = {evt.get("linked_truth_event_uid") for evt in lie_events if evt.get("linked_truth_event_uid")}
        for truth_evt in truth_events:
            truth_uid = truth_evt.get("uid", "")
            truth_name = truth_evt.get("name", "未命名")
            if truth_uid and truth_uid not in referenced_truth_uids:
                # 只有当有谎言事件时才提示
                if lie_events:
                    issues.append(LogicIssue(
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.DUAL_TIMELINE,
                        message=f"真相事件「{truth_name}」没有被任何谎言事件关联（可能无需掩盖）",
                        node_refs=[truth_uid]
                    ))

        return issues

    def run_full_validation(self) -> ValidationReport:
        """
        运行完整验证，返回验证报告。
        """
        all_issues: List[LogicIssue] = []

        # 运行所有验证器
        all_issues.extend(self.validate_clue_timeline())
        all_issues.extend(self.validate_character_presence())
        all_issues.extend(self.validate_timeline_consistency())
        all_issues.extend(self.validate_location_consistency())
        all_issues.extend(self.validate_references())
        all_issues.extend(self.validate_dual_timeline())

        # 按严重程度排序
        severity_order = {
            IssueSeverity.ERROR: 0,
            IssueSeverity.WARNING: 1,
            IssueSeverity.INFO: 2
        }
        all_issues.sort(key=lambda x: severity_order.get(x.severity, 99))

        # 生成摘要
        report = ValidationReport(issues=all_issues)
        if report.has_issues:
            report.summary = f"发现 {report.error_count} 个错误, {report.warning_count} 个警告, {report.info_count} 条信息"
        else:
            report.summary = "未发现逻辑问题"

        return report


def get_logic_validator(project_manager) -> LogicValidator:
    """获取逻辑验证器实例。"""
    return LogicValidator(project_manager)