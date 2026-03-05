"""
数据验证器 - 提供统一的数据验证功能

用法:
    from writer_app.core.validators import CharacterValidator, SceneValidator

    try:
        validated_data = CharacterValidator.validate(char_data)
    except ValidationError as e:
        print(f"验证失败: {e.field} - {e.message}")
"""

from typing import Any, Dict, List, Optional, Callable
import re
import uuid

from writer_app.core.exceptions import (
    ValidationError,
    RequiredFieldError,
    DuplicateError,
    InvalidFormatError
)


class Validator:
    """数据验证基类。"""

    @staticmethod
    def required(value: Any, field_name: str) -> Any:
        """
        验证必填字段。

        Args:
            value: 字段值
            field_name: 字段名称

        Raises:
            RequiredFieldError: 如果字段为空
        """
        if value is None:
            raise RequiredFieldError(field_name)
        if isinstance(value, str) and not value.strip():
            raise RequiredFieldError(field_name)
        return value

    @staticmethod
    def max_length(value: str, max_len: int, field_name: str) -> str:
        """
        验证最大长度。

        Args:
            value: 字段值
            max_len: 最大长度
            field_name: 字段名称

        Raises:
            ValidationError: 如果超过最大长度
        """
        if value and len(value) > max_len:
            raise ValidationError(f"长度不能超过 {max_len} 个字符", field=field_name)
        return value

    @staticmethod
    def min_length(value: str, min_len: int, field_name: str) -> str:
        """验证最小长度。"""
        if value and len(value) < min_len:
            raise ValidationError(f"长度不能少于 {min_len} 个字符", field=field_name)
        return value

    @staticmethod
    def in_range(value: int, min_val: int, max_val: int, field_name: str) -> int:
        """验证数值范围。"""
        if value < min_val or value > max_val:
            raise ValidationError(f"必须在 {min_val} 到 {max_val} 之间", field=field_name)
        return value

    @staticmethod
    def matches_pattern(value: str, pattern: str, field_name: str, message: str = None) -> str:
        """验证正则匹配。"""
        if value and not re.match(pattern, value):
            raise InvalidFormatError(
                message or f"格式不正确",
                field=field_name,
                expected_format=pattern
            )
        return value

    @staticmethod
    def ensure_uid(data: dict) -> dict:
        """确保数据有 UID。"""
        if not data.get("uid"):
            data["uid"] = uuid.uuid4().hex
        return data

    @staticmethod
    def ensure_list(data: dict, field: str) -> dict:
        """确保字段是列表。"""
        if field not in data or not isinstance(data[field], list):
            data[field] = []
        return data

    @staticmethod
    def ensure_dict(data: dict, field: str) -> dict:
        """确保字段是字典。"""
        if field not in data or not isinstance(data[field], dict):
            data[field] = {}
        return data

    @staticmethod
    def strip_string(value: str) -> str:
        """去除字符串首尾空白。"""
        return value.strip() if isinstance(value, str) else value


class CharacterValidator(Validator):
    """角色数据验证器。"""

    MAX_NAME_LENGTH = 100
    MAX_DESC_LENGTH = 10000

    @classmethod
    def validate(cls, data: dict, existing_names: List[str] = None) -> dict:
        """
        验证角色数据。

        Args:
            data: 角色数据字典
            existing_names: 已存在的角色名列表（用于检查重复）

        Returns:
            验证后的数据

        Raises:
            ValidationError: 验证失败
        """
        # 必填字段
        name = cls.strip_string(data.get("name", ""))
        cls.required(name, "角色名称")
        cls.max_length(name, cls.MAX_NAME_LENGTH, "角色名称")

        # 检查重复
        if existing_names and name in existing_names:
            raise DuplicateError(f"角色 '{name}' 已存在", field="name", existing_value=name)

        # 可选字段验证
        desc = data.get("description", "")
        if desc:
            cls.max_length(desc, cls.MAX_DESC_LENGTH, "角色描述")

        # 确保必要字段存在
        result = {
            "name": name,
            "description": desc,
            "tags": data.get("tags", []),
            "image_path": data.get("image_path", ""),
            "events": data.get("events", []),
            # 叙述者相关字段 (POV 系统)
            "is_narrator": data.get("is_narrator", False),
            "knowledge_scope": data.get("knowledge_scope", []),      # 角色知道的事件 UID 列表
            "narrator_voice_style": data.get("narrator_voice_style", ""),  # 叙述风格
            "perception_bias": data.get("perception_bias", {}),      # {角色UID: 偏见分数}
        }

        # 确保 is_narrator 是布尔值
        if not isinstance(result["is_narrator"], bool):
            result["is_narrator"] = bool(result["is_narrator"])

        # 确保 knowledge_scope 是列表
        if not isinstance(result["knowledge_scope"], list):
            result["knowledge_scope"] = []

        # 确保 perception_bias 是字典
        if not isinstance(result["perception_bias"], dict):
            result["perception_bias"] = {}

        # 确保有 UID
        if data.get("uid"):
            result["uid"] = data["uid"]
        else:
            result["uid"] = uuid.uuid4().hex

        # 保留其他自定义字段
        for key, value in data.items():
            if key not in result:
                result[key] = value

        return result


class SceneValidator(Validator):
    """场景数据验证器。"""

    MAX_NAME_LENGTH = 200
    MAX_LOCATION_LENGTH = 200
    MAX_CONTENT_LENGTH = 100000

    # POV 叙述人称选项
    VALID_NARRATIVE_VOICES = [
        "first",            # 第一人称
        "second",           # 第二人称
        "third_limited",    # 第三人称限制视角
        "third_omniscient"  # 第三人称全知视角
    ]

    @classmethod
    def validate(cls, data: dict) -> dict:
        """验证场景数据。"""
        # 必填字段
        name = cls.strip_string(data.get("name", ""))
        cls.required(name, "场景名称")
        cls.max_length(name, cls.MAX_NAME_LENGTH, "场景名称")

        # 可选字段验证
        location = data.get("location", "")
        if location:
            cls.max_length(location, cls.MAX_LOCATION_LENGTH, "地点")

        content = data.get("content", "")
        if content:
            cls.max_length(content, cls.MAX_CONTENT_LENGTH, "场景内容")

        # 验证 tension 范围
        tension = data.get("tension", 50)
        if isinstance(tension, (int, float)):
            tension = int(cls.in_range(int(tension), 0, 100, "张力值"))
        else:
            tension = 50

        # 验证 POV 叙述人称
        narrative_voice = data.get("narrative_voice", "third_limited")
        if narrative_voice not in cls.VALID_NARRATIVE_VOICES:
            narrative_voice = "third_limited"

        # 验证叙述者可靠度 (0.0 - 1.0)
        narrator_reliability = data.get("narrator_reliability", 1.0)
        if isinstance(narrator_reliability, (int, float)):
            narrator_reliability = max(0.0, min(1.0, float(narrator_reliability)))
        else:
            narrator_reliability = 1.0

        result = {
            "name": name,
            "location": location,
            "time": data.get("time", ""),
            "content": content,
            "characters": data.get("characters", []),
            "tags": data.get("tags", []),
            "tension": tension,
            "outline_ref_id": data.get("outline_ref_id", ""),
            "outline_ref_path": data.get("outline_ref_path", ""),
            "snapshots": data.get("snapshots", []),
            # POV 相关字段
            "pov_character": data.get("pov_character", ""),  # 视角角色 UID
            "narrative_voice": narrative_voice,              # 叙述人称
            "narrator_reliability": narrator_reliability,    # 叙述者可靠度
            "pov_notes": data.get("pov_notes", ""),         # 视角限制说明
        }

        # 确保有 UID
        if data.get("uid"):
            result["uid"] = data["uid"]
        else:
            result["uid"] = uuid.uuid4().hex

        return result


class OutlineNodeValidator(Validator):
    """大纲节点验证器。"""

    MAX_NAME_LENGTH = 500
    MAX_CONTENT_LENGTH = 50000

    @classmethod
    def validate(cls, data: dict) -> dict:
        """验证大纲节点数据。"""
        # 必填字段
        name = cls.strip_string(data.get("name", ""))
        cls.required(name, "节点名称")
        cls.max_length(name, cls.MAX_NAME_LENGTH, "节点名称")

        # 可选字段
        content = data.get("content", "")
        if content:
            cls.max_length(content, cls.MAX_CONTENT_LENGTH, "节点内容")

        result = {
            "name": name,
            "content": content,
            "children": data.get("children", []),
            "tags": data.get("tags", []),
        }

        # 确保有 UID
        if data.get("uid"):
            result["uid"] = data["uid"]
        else:
            result["uid"] = uuid.uuid4().hex

        # 递归验证子节点
        validated_children = []
        for child in result["children"]:
            if isinstance(child, dict):
                validated_children.append(cls.validate(child))
        result["children"] = validated_children

        return result


class WikiEntryValidator(Validator):
    """百科条目验证器。"""

    MAX_NAME_LENGTH = 200
    MAX_CONTENT_LENGTH = 100000

    @classmethod
    def validate(cls, data: dict, existing_names: List[str] = None) -> dict:
        """验证百科条目数据。"""
        # 必填字段
        name = cls.strip_string(data.get("name", ""))
        cls.required(name, "条目名称")
        cls.max_length(name, cls.MAX_NAME_LENGTH, "条目名称")

        # 检查重复
        if existing_names and name in existing_names:
            raise DuplicateError(f"条目 '{name}' 已存在", field="name", existing_value=name)

        # 类别
        category = data.get("category", "其他")
        cls.required(category, "分类")

        result = {
            "name": name,
            "category": category,
            "content": data.get("content", ""),
            "image_path": data.get("image_path", ""),
            "tags": data.get("tags", []),
        }

        # 确保有 UID
        if data.get("uid"):
            result["uid"] = data["uid"]
        else:
            result["uid"] = uuid.uuid4().hex

        return result


class TimelineEventValidator(Validator):
    """时间轴事件验证器。"""

    @classmethod
    def validate(cls, data: dict, event_type: str = "truth") -> dict:
        """
        验证时间轴事件数据。

        Args:
            data: 事件数据
            event_type: 事件类型 ("truth" 或 "lie")
        """
        name = cls.strip_string(data.get("name", ""))
        cls.required(name, "事件名称")

        result = {
            "name": name,
            "timestamp": data.get("timestamp", ""),
            "location": data.get("location", ""),
        }

        if event_type == "truth":
            result.update({
                "motive": data.get("motive", ""),
                "action": data.get("action", ""),
                "chaos": data.get("chaos", ""),
                "linked_scene_uid": data.get("linked_scene_uid", ""),
            })
        else:  # lie
            result.update({
                "motive": data.get("motive", ""),
                "gap": data.get("gap", ""),
                "bug": data.get("bug", ""),
                "linked_truth_event_uid": data.get("linked_truth_event_uid", ""),
            })

        # 确保有 UID
        if data.get("uid"):
            result["uid"] = data["uid"]
        else:
            result["uid"] = uuid.uuid4().hex

        return result


class ProjectValidator(Validator):
    """项目数据验证器。"""

    @classmethod
    def validate_structure(cls, data: dict) -> List[str]:
        """
        验证项目数据结构完整性。

        Returns:
            错误消息列表（空列表表示验证通过）
        """
        errors = []

        # 检查必要的顶级字段
        required_fields = ["outline", "script"]
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必要字段: {field}")

        # 检查 outline 结构
        outline = data.get("outline", {})
        if not isinstance(outline, dict):
            errors.append("outline 必须是字典类型")
        elif not outline.get("name"):
            errors.append("outline 缺少 name 字段")

        # 检查 script 结构
        script = data.get("script", {})
        if not isinstance(script, dict):
            errors.append("script 必须是字典类型")
        else:
            if "characters" not in script:
                errors.append("script 缺少 characters 字段")
            if "scenes" not in script:
                errors.append("script 缺少 scenes 字段")

        return errors

    @classmethod
    def migrate(cls, data: dict) -> dict:
        """
        迁移旧版本项目数据到新版本。

        Args:
            data: 项目数据

        Returns:
            迁移后的数据
        """
        # 确保 meta 存在
        if "meta" not in data:
            data["meta"] = {}

        meta = data["meta"]
        meta.setdefault("type", "General")
        meta.setdefault("length", "Long")
        meta.setdefault("outline_template_style", "default")
        meta.setdefault("created_at", "")
        meta.setdefault("version", "1.0")
        meta.setdefault("kanban_columns", ["构思", "初稿", "润色", "定稿"])
        meta.setdefault("genre_tags", [])
        if "enabled_tools" not in meta or "custom_wiki_categories" not in meta:
            from writer_app.core.project_types import ProjectTypeManager
            preset = ProjectTypeManager.get_preset_config(
                meta.get("type", "General"),
                meta.get("genre_tags", []),
                meta.get("length", "Long")
            )
            meta.setdefault(
                "enabled_tools",
                ProjectTypeManager.get_default_tools_list(
                    meta.get("type", "General"),
                    meta.get("length", "Long"),
                    meta.get("genre_tags", [])
                )
            )
            meta.setdefault("custom_wiki_categories", preset.get("wiki_categories", []))

        # 确保 outline 存在并补齐 UID（便于路径映射）
        if "outline" not in data:
            data["outline"] = {"name": "项目大纲", "children": [], "uid": uuid.uuid4().hex}
        else:
            root = data.get("outline", {})
            stack = [root]
            while stack:
                node = stack.pop()
                if not node.get("uid"):
                    node["uid"] = uuid.uuid4().hex
                for child in node.get("children", []):
                    stack.append(child)

        # 确保 world 存在
        if "world" not in data:
            data["world"] = {"entries": []}

        # 确保 relationships 存在
        if "relationships" not in data:
            data["relationships"] = {
                "layout": {},
                "character_layout": {},
                "evidence_layout": {},
                "relationship_links": [],
                "evidence_links": [],
                "links": [],
                "nodes": [],
                "snapshots": [],
                "relationship_events": []
            }
        else:
            data["relationships"].setdefault("nodes", [])
            data["relationships"].setdefault("snapshots", [])
            data["relationships"].setdefault("character_layout", {})
            data["relationships"].setdefault("evidence_layout", {})
            data["relationships"].setdefault("relationship_links", [])
            data["relationships"].setdefault("evidence_links", [])
            data["relationships"].setdefault("links", [])
            data["relationships"].setdefault("relationship_events", [])

            # Legacy migration: split shared links into relationship/evidence buckets
            legacy_links = data["relationships"].get("links", [])
            if legacy_links and (not data["relationships"].get("relationship_links") and not data["relationships"].get("evidence_links")):
                evidence_types = {"relates_to", "suspects", "confirms", "contradicts", "caused_by"}
                rel_links = []
                ev_links = []
                for link in legacy_links:
                    if isinstance(link, dict) and link.get("type") in evidence_types:
                        ev_links.append(link)
                    else:
                        rel_links.append(link)
                data["relationships"]["relationship_links"] = rel_links
                data["relationships"]["evidence_links"] = ev_links

        # 确保 tags 存在
        if "tags" not in data:
            data["tags"] = []

        # 确保 timelines 存在
        if "timelines" not in data:
            data["timelines"] = {"truth_events": [], "lie_events": []}
        else:
            data["timelines"].setdefault("truth_events", [])
            data["timelines"].setdefault("lie_events", [])

        # 确保 research 和 ideas 存在
        if "research" not in data:
            data["research"] = []
        if "ideas" not in data:
            data["ideas"] = []

        # 确保 factions 存在
        if "factions" not in data:
            data["factions"] = {"groups": [], "matrix": {}}

        # 迁移场景数据
        scenes = data.get("script", {}).get("scenes", [])
        for scene in scenes:
            scene.setdefault("characters", [])
            scene.setdefault("tags", [])
            scene.setdefault("snapshots", [])
            scene.setdefault("tension", 50)
            scene.setdefault("outline_ref", "")
            scene.setdefault("outline_ref_id", "")
            scene.setdefault("outline_ref_path", scene.get("outline_ref", ""))
            # POV 字段迁移
            scene.setdefault("pov_character", "")
            scene.setdefault("narrative_voice", "third_limited")
            scene.setdefault("narrator_reliability", 1.0)
            scene.setdefault("pov_notes", "")
            if not scene.get("uid"):
                scene["uid"] = uuid.uuid4().hex

        # 尝试从路径恢复 outline_ref_id
        outline_root = data.get("outline", {})
        def build_path_map(root, separator):
            mapping = {}
            stack = [(root, [])]
            while stack:
                node, path = stack.pop()
                current = path + [node.get("name", "")]
                uid = node.get("uid")
                if uid:
                    mapping[separator.join([p for p in current if p])] = uid
                for child in node.get("children", []):
                    stack.append((child, current))
            return mapping

        path_map_slash = build_path_map(outline_root, " / ")
        path_map_arrow = build_path_map(outline_root, " > ")

        for scene in scenes:
            if scene.get("outline_ref_id"):
                continue
            raw_path = scene.get("outline_ref_path") or scene.get("outline_ref")
            if not raw_path:
                continue
            uid = path_map_slash.get(raw_path) or path_map_arrow.get(raw_path)
            if uid:
                scene["outline_ref_id"] = uid
                scene["outline_ref_path"] = " / ".join(raw_path.split(" > "))

        # 迁移时间轴事件（linked_scene_index -> linked_scene_uid）
        truth_events = data.get("timelines", {}).get("truth_events", [])
        for evt in truth_events:
            if evt.get("linked_scene_uid"):
                evt.pop("linked_scene_index", None)
                continue
            idx = evt.get("linked_scene_index")
            if isinstance(idx, int) and 0 <= idx < len(scenes):
                evt["linked_scene_uid"] = scenes[idx].get("uid", "")
            evt.pop("linked_scene_index", None)

        # 迁移角色数据
        for char in data.get("script", {}).get("characters", []):
            char.setdefault("tags", [])
            char.setdefault("image_path", "")
            char.setdefault("events", [])
            # 叙述者相关字段迁移 (POV 系统)
            char.setdefault("is_narrator", False)
            char.setdefault("knowledge_scope", [])
            char.setdefault("narrator_voice_style", "")
            char.setdefault("perception_bias", {})
            if not char.get("uid"):
                char["uid"] = uuid.uuid4().hex

        return data
