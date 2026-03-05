"""
测试数据验证器模块。
"""
import unittest

from writer_app.core.validators import (
    Validator,
    CharacterValidator,
    SceneValidator,
    OutlineNodeValidator,
    WikiEntryValidator,
    TimelineEventValidator,
    ProjectValidator
)
from writer_app.core.exceptions import (
    ValidationError,
    RequiredFieldError,
    DuplicateError,
    InvalidFormatError
)


class TestBaseValidator(unittest.TestCase):
    """测试基础验证器。"""

    def test_required_with_value(self):
        """测试必填字段有值。"""
        result = Validator.required("test", "field")
        self.assertEqual(result, "test")

    def test_required_with_none(self):
        """测试必填字段为 None。"""
        with self.assertRaises(RequiredFieldError) as ctx:
            Validator.required(None, "名称")
        self.assertEqual(ctx.exception.field, "名称")

    def test_required_with_empty_string(self):
        """测试必填字段为空字符串。"""
        with self.assertRaises(RequiredFieldError):
            Validator.required("   ", "名称")

    def test_max_length_valid(self):
        """测试最大长度验证通过。"""
        result = Validator.max_length("test", 10, "field")
        self.assertEqual(result, "test")

    def test_max_length_exceeded(self):
        """测试超过最大长度。"""
        with self.assertRaises(ValidationError) as ctx:
            Validator.max_length("very long text", 5, "field")
        self.assertIn("不能超过", str(ctx.exception))

    def test_min_length_valid(self):
        """测试最小长度验证通过。"""
        result = Validator.min_length("test", 2, "field")
        self.assertEqual(result, "test")

    def test_min_length_too_short(self):
        """测试长度不足。"""
        with self.assertRaises(ValidationError) as ctx:
            Validator.min_length("ab", 5, "field")
        self.assertIn("不能少于", str(ctx.exception))

    def test_in_range_valid(self):
        """测试范围验证通过。"""
        result = Validator.in_range(50, 0, 100, "value")
        self.assertEqual(result, 50)

    def test_in_range_out_of_bounds(self):
        """测试超出范围。"""
        with self.assertRaises(ValidationError):
            Validator.in_range(150, 0, 100, "value")

    def test_matches_pattern_valid(self):
        """测试正则匹配通过。"""
        result = Validator.matches_pattern("abc123", r"^[a-z]+\d+$", "code")
        self.assertEqual(result, "abc123")

    def test_matches_pattern_invalid(self):
        """测试正则匹配失败。"""
        with self.assertRaises(InvalidFormatError):
            Validator.matches_pattern("123abc", r"^[a-z]+\d+$", "code")

    def test_ensure_uid(self):
        """测试确保 UID 存在。"""
        data = {"name": "test"}
        result = Validator.ensure_uid(data)
        self.assertIn("uid", result)
        self.assertTrue(len(result["uid"]) > 0)

    def test_ensure_uid_preserves_existing(self):
        """测试保留现有 UID。"""
        data = {"name": "test", "uid": "existing_uid"}
        result = Validator.ensure_uid(data)
        self.assertEqual(result["uid"], "existing_uid")

    def test_strip_string(self):
        """测试去除空白。"""
        result = Validator.strip_string("  test  ")
        self.assertEqual(result, "test")


class TestCharacterValidator(unittest.TestCase):
    """测试角色验证器。"""

    def test_validate_valid_character(self):
        """测试验证有效角色。"""
        data = {"name": "张三", "description": "主角"}
        result = CharacterValidator.validate(data)

        self.assertEqual(result["name"], "张三")
        self.assertEqual(result["description"], "主角")
        self.assertIn("uid", result)

    def test_validate_missing_name(self):
        """测试缺少名称。"""
        with self.assertRaises(RequiredFieldError):
            CharacterValidator.validate({"description": "test"})

    def test_validate_duplicate_name(self):
        """测试重复名称。"""
        existing = ["张三", "李四"]
        with self.assertRaises(DuplicateError):
            CharacterValidator.validate({"name": "张三"}, existing_names=existing)

    def test_validate_name_too_long(self):
        """测试名称过长。"""
        long_name = "a" * 150
        with self.assertRaises(ValidationError):
            CharacterValidator.validate({"name": long_name})

    def test_validate_preserves_custom_fields(self):
        """测试保留自定义字段。"""
        data = {"name": "测试", "custom_field": "value"}
        result = CharacterValidator.validate(data)
        self.assertEqual(result["custom_field"], "value")


class TestSceneValidator(unittest.TestCase):
    """测试场景验证器。"""

    def test_validate_valid_scene(self):
        """测试验证有效场景。"""
        data = {
            "name": "第一幕",
            "location": "咖啡厅",
            "content": "场景内容"
        }
        result = SceneValidator.validate(data)

        self.assertEqual(result["name"], "第一幕")
        self.assertEqual(result["location"], "咖啡厅")
        self.assertIn("uid", result)

    def test_validate_missing_name(self):
        """测试缺少名称。"""
        with self.assertRaises(RequiredFieldError):
            SceneValidator.validate({"content": "test"})

    def test_validate_tension_in_range(self):
        """测试张力值范围。"""
        data = {"name": "场景", "tension": 80}
        result = SceneValidator.validate(data)
        self.assertEqual(result["tension"], 80)

    def test_validate_tension_out_of_range(self):
        """测试张力值超出范围。"""
        with self.assertRaises(ValidationError):
            SceneValidator.validate({"name": "场景", "tension": 150})

    def test_validate_default_tension(self):
        """测试默认张力值。"""
        data = {"name": "场景"}
        result = SceneValidator.validate(data)
        self.assertEqual(result["tension"], 50)


class TestOutlineNodeValidator(unittest.TestCase):
    """测试大纲节点验证器。"""

    def test_validate_valid_node(self):
        """测试验证有效节点。"""
        data = {"name": "第一章", "content": "章节内容"}
        result = OutlineNodeValidator.validate(data)

        self.assertEqual(result["name"], "第一章")
        self.assertIn("uid", result)

    def test_validate_with_children(self):
        """测试带子节点的验证。"""
        data = {
            "name": "根节点",
            "children": [
                {"name": "子节点1"},
                {"name": "子节点2"}
            ]
        }
        result = OutlineNodeValidator.validate(data)

        self.assertEqual(len(result["children"]), 2)
        self.assertIn("uid", result["children"][0])
        self.assertIn("uid", result["children"][1])


class TestWikiEntryValidator(unittest.TestCase):
    """测试百科条目验证器。"""

    def test_validate_valid_entry(self):
        """测试验证有效条目。"""
        data = {"name": "魔法", "category": "设定"}
        result = WikiEntryValidator.validate(data)

        self.assertEqual(result["name"], "魔法")
        self.assertEqual(result["category"], "设定")

    def test_validate_duplicate_name(self):
        """测试重复名称。"""
        existing = ["魔法", "科技"]
        with self.assertRaises(DuplicateError):
            WikiEntryValidator.validate(
                {"name": "魔法", "category": "设定"},
                existing_names=existing
            )


class TestTimelineEventValidator(unittest.TestCase):
    """测试时间轴事件验证器。"""

    def test_validate_truth_event(self):
        """测试验证真相事件。"""
        data = {
            "name": "案发",
            "timestamp": "2024-01-01",
            "motive": "复仇"
        }
        result = TimelineEventValidator.validate(data, event_type="truth")

        self.assertEqual(result["name"], "案发")
        self.assertIn("motive", result)
        self.assertIn("action", result)

    def test_validate_lie_event(self):
        """测试验证谎言事件。"""
        data = {
            "name": "假证词",
            "timestamp": "2024-01-02"
        }
        result = TimelineEventValidator.validate(data, event_type="lie")

        self.assertEqual(result["name"], "假证词")
        self.assertIn("gap", result)
        self.assertIn("bug", result)


class TestProjectValidator(unittest.TestCase):
    """测试项目验证器。"""

    def test_validate_structure_valid(self):
        """测试验证有效项目结构。"""
        data = {
            "outline": {"name": "大纲"},
            "script": {"characters": [], "scenes": []}
        }
        errors = ProjectValidator.validate_structure(data)
        self.assertEqual(errors, [])

    def test_validate_structure_missing_outline(self):
        """测试缺少大纲。"""
        data = {"script": {"characters": [], "scenes": []}}
        errors = ProjectValidator.validate_structure(data)
        self.assertTrue(any("outline" in e for e in errors))

    def test_validate_structure_missing_script(self):
        """测试缺少剧本。"""
        data = {"outline": {"name": "大纲"}}
        errors = ProjectValidator.validate_structure(data)
        self.assertTrue(any("script" in e for e in errors))

    def test_migrate_adds_missing_fields(self):
        """测试迁移添加缺失字段。"""
        data = {
            "outline": {"name": "大纲"},
            "script": {"characters": [], "scenes": []}
        }
        result = ProjectValidator.migrate(data)

        self.assertIn("meta", result)
        self.assertIn("world", result)
        self.assertIn("relationships", result)
        self.assertIn("tags", result)
        self.assertIn("timelines", result)

    def test_migrate_preserves_existing_data(self):
        """测试迁移保留现有数据。"""
        data = {
            "outline": {"name": "大纲"},
            "script": {"characters": [], "scenes": []},
            "tags": [{"name": "重要", "color": "#ff0000"}]
        }
        result = ProjectValidator.migrate(data)

        self.assertEqual(len(result["tags"]), 1)
        self.assertEqual(result["tags"][0]["name"], "重要")


if __name__ == "__main__":
    unittest.main()
