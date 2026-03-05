"""
逻辑校验器单元测试
"""

import unittest
from writer_app.core.models import ProjectManager
from writer_app.core.logic_validator import (
    LogicValidator, ValidationReport, LogicIssue,
    IssueSeverity, IssueCategory, get_logic_validator
)


class TestLogicValidator(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()
        self.validator = LogicValidator(self.pm)

    def test_validator_creation(self):
        """测试创建验证器。"""
        validator = get_logic_validator(self.pm)
        self.assertIsInstance(validator, LogicValidator)

    def test_empty_project_no_issues(self):
        """测试空项目没有问题。"""
        report = self.validator.run_full_validation()
        # 空项目应该没有严重错误
        self.assertEqual(report.error_count, 0)

    def test_clue_timeline_validation(self):
        """测试线索时间线验证。"""
        # 设置测试数据：两个场景，线索在后一个场景揭示但在前一个场景被提到
        scenes = self.pm.get_scenes()
        scenes.append({
            "name": "场景1",
            "content": "发现了一把匕首",
            "characters": [],
            "time": "上午"
        })
        scenes.append({
            "name": "场景2",
            "content": "检验匕首",
            "characters": [],
            "time": "下午"
        })

        # 设置证据节点
        relationships = self.pm.get_relationships()
        relationships["nodes"] = [
            {
                "uid": "clue1",
                "name": "匕首",
                "type": "clue",
                "scene_ref": 1  # 在场景2才揭示
            }
        ]

        issues = self.validator.validate_clue_timeline()
        # 应该检测到线索在场景1提到但在场景2才揭示
        # 注意：这取决于内容匹配逻辑

    def test_character_presence_validation(self):
        """测试角色在场验证。"""
        # 添加角色
        characters = self.pm.get_characters()
        characters.append({"name": "张三", "description": "主角"})

        # 添加场景，内容中有张三对话但未列入登场角色
        scenes = self.pm.get_scenes()
        scenes.append({
            "name": "场景1",
            "content": "张三：你好啊！",
            "characters": [],  # 未列入登场角色
            "time": "上午"
        })

        issues = self.validator.validate_character_presence()
        # 应该有一个INFO级别的问题
        self.assertTrue(len(issues) >= 1)
        self.assertTrue(any(
            i.category == IssueCategory.CHARACTER_PRESENCE
            for i in issues
        ))

    def test_timeline_consistency_validation(self):
        """测试时间线一致性验证。"""
        scenes = self.pm.get_scenes()
        scenes.append({"name": "场景1", "time": "下午", "content": ""})
        scenes.append({"name": "场景2", "time": "上午", "content": ""})  # 时间倒退

        issues = self.validator.validate_timeline_consistency()
        # 应该检测到时间倒退
        time_issues = [i for i in issues if i.category == IssueCategory.TIMELINE_CONFLICT]
        self.assertTrue(len(time_issues) >= 1)

    def test_flashback_scene_ignored(self):
        """测试回忆场景被忽略。"""
        scenes = self.pm.get_scenes()
        scenes.append({"name": "场景1", "time": "下午", "content": ""})
        scenes.append({"name": "回忆场景", "time": "上午", "content": ""})  # 回忆场景

        issues = self.validator.validate_timeline_consistency()
        # 回忆场景的时间倒退应该被忽略
        time_issues = [i for i in issues if i.category == IssueCategory.TIMELINE_CONFLICT]
        self.assertEqual(len(time_issues), 0)

    def test_reference_validation(self):
        """测试引用完整性验证。"""
        scenes = self.pm.get_scenes()
        scenes.append({
            "name": "场景1",
            "characters": ["不存在的角色"],
            "content": "",
            "outline_ref_id": "nonexistent_uid"
        })

        issues = self.validator.validate_references()
        # 应该检测到角色引用和大纲引用问题
        self.assertTrue(len(issues) >= 1)

    def test_full_validation_report(self):
        """测试完整验证报告。"""
        report = self.validator.run_full_validation()

        self.assertIsInstance(report, ValidationReport)
        self.assertIsInstance(report.error_count, int)
        self.assertIsInstance(report.warning_count, int)
        self.assertIsInstance(report.info_count, int)

    def test_report_to_markdown(self):
        """测试报告转换为Markdown。"""
        report = ValidationReport(issues=[
            LogicIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.CLUE_ORDER,
                message="测试错误",
                scene_refs=[0, 1]
            )
        ])

        markdown = report.to_markdown()
        self.assertIn("逻辑校验报告", markdown)
        self.assertIn("测试错误", markdown)
        self.assertIn("错误", markdown)


class TestLogicIssue(unittest.TestCase):
    def test_issue_creation(self):
        """测试创建LogicIssue。"""
        issue = LogicIssue(
            severity=IssueSeverity.WARNING,
            category=IssueCategory.CHARACTER_PRESENCE,
            message="测试警告",
            scene_refs=[0],
            node_refs=["uid1"]
        )

        self.assertEqual(issue.severity, IssueSeverity.WARNING)
        self.assertEqual(issue.category, IssueCategory.CHARACTER_PRESENCE)
        self.assertEqual(issue.message, "测试警告")

    def test_issue_to_dict(self):
        """测试LogicIssue转换为字典。"""
        issue = LogicIssue(
            severity=IssueSeverity.ERROR,
            category=IssueCategory.CLUE_ORDER,
            message="测试",
            scene_refs=[1, 2]
        )

        d = issue.to_dict()

        self.assertEqual(d["severity"], "error")
        self.assertEqual(d["category"], "clue_order")
        self.assertEqual(d["message"], "测试")
        self.assertEqual(d["scene_refs"], [1, 2])

    def test_severity_icon(self):
        """测试严重程度图标。"""
        error = LogicIssue(IssueSeverity.ERROR, IssueCategory.CLUE_ORDER, "")
        warning = LogicIssue(IssueSeverity.WARNING, IssueCategory.CLUE_ORDER, "")
        info = LogicIssue(IssueSeverity.INFO, IssueCategory.CLUE_ORDER, "")

        self.assertIn("❌", error.severity_icon)
        self.assertIn("⚠", warning.severity_icon)
        self.assertIn("ℹ", info.severity_icon)


class TestValidationReport(unittest.TestCase):
    def test_empty_report(self):
        """测试空报告。"""
        report = ValidationReport()

        self.assertFalse(report.has_issues)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.warning_count, 0)
        self.assertEqual(report.info_count, 0)

    def test_report_counts(self):
        """测试报告计数。"""
        report = ValidationReport(issues=[
            LogicIssue(IssueSeverity.ERROR, IssueCategory.CLUE_ORDER, "E1"),
            LogicIssue(IssueSeverity.ERROR, IssueCategory.CLUE_ORDER, "E2"),
            LogicIssue(IssueSeverity.WARNING, IssueCategory.TIMELINE_CONFLICT, "W1"),
            LogicIssue(IssueSeverity.INFO, IssueCategory.CHARACTER_PRESENCE, "I1"),
        ])

        self.assertTrue(report.has_issues)
        self.assertEqual(report.error_count, 2)
        self.assertEqual(report.warning_count, 1)
        self.assertEqual(report.info_count, 1)


if __name__ == "__main__":
    unittest.main()
