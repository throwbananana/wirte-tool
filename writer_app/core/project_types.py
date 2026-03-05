import re
from typing import Dict, Any

from writer_app.core.config import ConfigManager


class ProjectTypeManager:
    """
    Manages project genres (Suspense, Romance, etc.) AND lengths (Long, Short).
    """

    CUSTOM_TYPE_KEY = "Custom"

    # 默认百科分类
    DEFAULT_WIKI_CATEGORIES = ["人物", "地点", "物品", "势力", "设定", "其他"]

    TYPES = {
        "General": {
            "name": "通用/小说",
            "description": "标准写作模式，启用所有基础功能。",
            "hint": "可作为通用模板，工具可在下方自由增减。",
            "tools": ["outline", "script", "char_events", "story_curve", "kanban", "calendar", "timeline", "relationship", "wiki", "analytics"],
            "specialized_modules": ["galgame_assets"],
            "default_tab": "outline",
            "wiki_categories": ["人物", "地点", "物品", "势力", "设定", "其他"],
            "asset_types": ["reference", "character_image"]
        },
        "Custom": {
            "name": "自定义/其他",
            "description": "自定义题材名称，默认配置等同通用模式，可在下方自由调整模块。",
            "hint": "可作为临时方案，推荐保存为自定义类型以便复用。",
            "tools": ["outline", "script", "char_events", "story_curve", "kanban", "calendar", "timeline", "relationship", "wiki", "analytics"],
            "specialized_modules": ["galgame_assets"],
            "default_tab": "outline",
            "wiki_categories": ["人物", "地点", "物品", "势力", "设定", "其他"],
            "asset_types": ["reference", "character_image"]
        },
        "Suspense": {
            "name": "悬疑/推理",
            "description": "侧重线索管理、双重时间线（真相 vs 叙述）。",
            "hint": "推荐线索墙与双轨时间线，像管理案件一样推理。",
            "tools": ["outline", "script", "char_events", "story_curve", "evidence_board", "dual_timeline", "kanban", "wiki"],
            "specialized_modules": ["alibi", "galgame_assets"],
            "default_tab": "evidence_board",
            "wiki_categories": ["人物", "证据", "地点", "时间点", "动机", "其他"],
            "asset_types": ["evidence_photo", "location_photo", "reference"]
        },
        "Romance": {
            "name": "恋爱/言情",
            "description": "侧重人物关系动态、情感曲线。",
            "hint": "推荐人物关系图与情感节奏工具。",
            "tools": ["outline", "script", "char_events", "story_curve", "relationship", "timeline", "calendar"],
            "specialized_modules": ["heartbeat", "galgame_assets"],
            "default_tab": "relationship",
            "wiki_categories": ["人物", "地点", "物品", "回忆", "约定", "其他"],
            "asset_types": ["reference", "mood_board", "character_image"]
        },
        "Epic": {
            "name": "奇幻/史诗",
            "description": "侧重多线叙事、宏大世界观。",
            "hint": "推荐故事泳道与百科，适合多线叙事。",
            "tools": ["outline", "script", "char_events", "story_curve", "swimlanes", "wiki", "calendar"],
            "specialized_modules": ["iceberg", "galgame_assets"],
            "default_tab": "swimlanes",
            "wiki_categories": ["人物", "地点", "物品", "势力", "魔法/科技", "历史", "种族", "设定", "其他"],
            "asset_types": ["reference", "map", "character_image"]
        },
        "SciFi": {
            "name": "科幻/赛博",
            "description": "侧重势力阵营、科技设定、政治角力。",
            "hint": "推荐势力矩阵与科技设定分类。",
            "tools": ["outline", "script", "char_events", "story_curve", "kanban", "wiki", "relationship"],
            "specialized_modules": ["faction", "galgame_assets"],
            "default_tab": "wiki",
            "wiki_categories": ["人物", "地点", "科技", "势力", "星球", "飞船", "设定", "其他"],
            "asset_types": ["reference", "tech_diagram", "character_image"]
        },
        "Poetry": {
            "name": "诗歌/散文",
            "description": "极简模式，专注文字韵律。",
            "hint": "极简起步，如需设定可开启百科与关系图。",
            "tools": ["script", "char_events", "story_curve", "zen_mode"],
            "specialized_modules": ["galgame_assets"],
            "default_tab": "script",
            "wiki_categories": ["意象", "典故", "风格", "其他"],
            "asset_types": ["reference"]
        },
        "LightNovel": {
            "name": "轻小说",
            "description": "二次元风格，侧重插画管理、人设详细设定。",
            "hint": "适合插画与人设管理。",
            "tools": ["outline", "script", "char_events", "story_curve", "wiki", "relationship", "kanban"],
            "specialized_modules": ["galgame_assets"],
            "default_tab": "script",
            "wiki_categories": ["人物", "地点", "物品", "势力", "技能", "种族", "设定", "其他"],
            "asset_types": ["illustration", "character_image", "reference"]
        },
        "Galgame": {
            "name": "Galgame/文字冒险",
            "description": "侧重剧情分支、立绘背景搭配、选项管理。",
            "hint": "建议配合变量管理与剧情流向梳理分支。",
            "tools": ["outline", "script", "char_events", "story_curve", "relationship", "wiki", "variable", "flowchart"],
            "specialized_modules": ["galgame_assets"],
            "default_tab": "outline",
            "wiki_categories": ["人物", "地点", "物品", "事件", "结局", "CG", "其他"],
            "asset_types": ["sprite", "background", "cg", "ui"]
        }
    }
    
    LENGTHS = {
        "Long": {
            "name": "长篇连载",
            "daily_goal": 3000,
            "complexity": "high", # Show all configured tools
            "desc": "适合几十万字的长篇，启用所有结构化管理工具。",
            "hint": "可开启全部结构化工具。"
        },
        "Short": {
            "name": "短篇故事",
            "daily_goal": 1000,
            "complexity": "low", # Hide complex timelines/world building if not essential
            "desc": "适合短篇创作，界面更简洁，隐藏不必要的高级视图。",
            "hint": "只影响推荐复杂度，可在下方手动开启高级工具。",
            "hidden_tools": ["swimlanes", "dual_timeline", "calendar"] # Override tools to hide even if type has them
        }
    }

    REQUIRED_TOOLS = ["outline", "script"]
    GLOBAL_DEFAULT_TOOLS = ["ideas", "research", "training", "reverse_engineering", "chat"]
    CUSTOM_TYPES_KEY = "custom_project_types"
    CUSTOM_TYPE_PREFIX = "Custom_"

    TAG_PRESETS = {
        # Optional tag presets can override or extend type defaults
        "Suspense": {
            "ai_hints": ["关注伏笔、线索与逻辑闭环。"]
        },
        "Romance": {
            "ai_hints": ["关注情感推进与角色化学反应。"]
        },
        "SciFi": {
            "ai_hints": ["关注科技设定与势力冲突。"]
        },
        "Epic": {
            "ai_hints": ["关注世界观一致性与多线叙事。"]
        },
        "Galgame": {
            "ai_hints": ["关注分支条件与结局可达性。"]
        },
    }

    # 项目类型对应的默认大纲视图
    # horizontal: 水平思维导图（默认）
    # vertical: 垂直树形图
    # radial: 放射发散图
    # table: 大纲表格
    OUTLINE_VIEW_DEFAULTS = {
        "General": "horizontal",
        "Custom": "horizontal",
        "Suspense": "horizontal",
        "Romance": "radial",      # 恋爱类适合展示人物关系的发散图
        "Epic": "table",          # 史诗类适合表格概览管理多线叙事
        "Poetry": "radial",       # 诗歌类适合发散思维
        "LightNovel": "horizontal",
        "Galgame": "horizontal",
    }

    @staticmethod
    def _get_config_manager():
        if not hasattr(ProjectTypeManager, "_config_manager"):
            ProjectTypeManager._config_manager = ConfigManager()
        return ProjectTypeManager._config_manager

    @staticmethod
    def get_custom_types() -> Dict[str, Dict[str, Any]]:
        config = ProjectTypeManager._get_config_manager()
        custom = config.get(ProjectTypeManager.CUSTOM_TYPES_KEY, {})
        if not isinstance(custom, dict):
            return {}
        return {k: v for k, v in custom.items() if isinstance(v, dict)}

    @staticmethod
    def is_custom_type(type_key: str) -> bool:
        return type_key in ProjectTypeManager.get_custom_types()

    @staticmethod
    def find_custom_type_key_by_name(name: str) -> str:
        for key, info in ProjectTypeManager.get_custom_types().items():
            if info.get("name") == name:
                return key
        return ""

    @staticmethod
    def _make_custom_type_key(name: str, existing: Dict[str, Dict[str, Any]]) -> str:
        base = re.sub(r"[^A-Za-z0-9]+", "_", name or "").strip("_")
        if not base:
            base = "Custom"
        key = f"{ProjectTypeManager.CUSTOM_TYPE_PREFIX}{base}"
        if key not in existing:
            return key
        counter = 2
        while f"{key}_{counter}" in existing:
            counter += 1
        return f"{key}_{counter}"

    @staticmethod
    def save_custom_type(type_key: str, info: Dict[str, Any]) -> None:
        custom = ProjectTypeManager.get_custom_types()
        custom[type_key] = dict(info)
        config = ProjectTypeManager._get_config_manager()
        config.set(ProjectTypeManager.CUSTOM_TYPES_KEY, custom)
        config.save()

    @staticmethod
    def create_custom_type(name: str, info: Dict[str, Any]) -> str:
        custom = ProjectTypeManager.get_custom_types()
        type_key = ProjectTypeManager._make_custom_type_key(name, custom)
        payload = dict(info)
        payload["name"] = name
        ProjectTypeManager.save_custom_type(type_key, payload)
        return type_key

    @staticmethod
    def delete_custom_type(type_key: str) -> None:
        custom = ProjectTypeManager.get_custom_types()
        if type_key in custom:
            del custom[type_key]
            config = ProjectTypeManager._get_config_manager()
            config.set(ProjectTypeManager.CUSTOM_TYPES_KEY, custom)
            config.save()

    @staticmethod
    def get_builtin_types():
        return list(ProjectTypeManager.TYPES.keys())

    @staticmethod
    def get_available_types():
        available = list(ProjectTypeManager.TYPES.keys())
        available.extend(ProjectTypeManager.get_custom_types().keys())
        return available
        
    @staticmethod
    def get_available_lengths():
        return list(ProjectTypeManager.LENGTHS.keys())

    @staticmethod
    def get_type_info(type_key):
        if type_key in ProjectTypeManager.TYPES:
            return ProjectTypeManager.TYPES[type_key]
        custom = ProjectTypeManager.get_custom_types().get(type_key)
        if custom:
            base_key = custom.get("base_type", "General")
            base_info = ProjectTypeManager.TYPES.get(base_key, ProjectTypeManager.TYPES["General"])
            merged = dict(base_info)
            merged.update(custom)
            merged.setdefault("name", custom.get("name", type_key))
            merged["base_type"] = base_key
            merged["is_custom"] = True
            return merged
        return ProjectTypeManager.TYPES["General"]
        
    @staticmethod
    def get_length_info(length_key):
        return ProjectTypeManager.LENGTHS.get(length_key, ProjectTypeManager.LENGTHS["Long"])

    @staticmethod
    def get_required_tools():
        return set(ProjectTypeManager.REQUIRED_TOOLS)

    @staticmethod
    def get_available_tags():
        tag_keys = set(ProjectTypeManager.TAG_PRESETS.keys())
        tag_keys.update(ProjectTypeManager.TYPES.keys())
        tag_keys.discard("General")
        tag_keys.discard(ProjectTypeManager.CUSTOM_TYPE_KEY)
        return sorted(tag_keys)

    @staticmethod
    def get_tag_info(tag_key):
        base = ProjectTypeManager.TYPES.get(tag_key, {})
        tag_info = ProjectTypeManager.TAG_PRESETS.get(tag_key, {})
        if not base:
            return tag_info
        merged = dict(base)
        merged.update(tag_info)
        return merged

    @staticmethod
    def _extend_unique(target, items):
        for item in items:
            if item not in target:
                target.append(item)

    @staticmethod
    def _merge_categories(base, extra):
        merged = list(base)
        for cat in extra:
            if cat not in merged:
                merged.append(cat)
        return merged

    @staticmethod
    def get_type_display_name(type_key, custom_name=None):
        info = ProjectTypeManager.get_type_info(type_key)
        if type_key == ProjectTypeManager.CUSTOM_TYPE_KEY and custom_name:
            return custom_name
        return info.get("name", type_key)

    @staticmethod
    def get_recommended_tools_for_type(type_key):
        info = ProjectTypeManager.get_type_info(type_key)
        tools = []
        ProjectTypeManager._extend_unique(tools, info.get("tools", []))
        ProjectTypeManager._extend_unique(tools, info.get("specialized_modules", []))
        return tools

    @staticmethod
    def get_recommended_tools_for_selection(type_key, tags=None):
        tools = []
        ProjectTypeManager._extend_unique(
            tools, ProjectTypeManager.get_recommended_tools_for_type(type_key)
        )

        for tag in tags or []:
            tag_info = ProjectTypeManager.TYPES.get(tag)
            if tag_info:
                ProjectTypeManager._extend_unique(
                    tools, ProjectTypeManager.get_recommended_tools_for_type(tag)
                )
            extra = ProjectTypeManager.TAG_PRESETS.get(tag, {})
            ProjectTypeManager._extend_unique(tools, extra.get("tools", []))
            ProjectTypeManager._extend_unique(tools, extra.get("specialized_modules", []))

        return tools

    @staticmethod
    def get_module_recommendation_map():
        base = set(ProjectTypeManager.get_recommended_tools_for_type("General"))
        base.update(ProjectTypeManager.REQUIRED_TOOLS)
        base.update(ProjectTypeManager.GLOBAL_DEFAULT_TOOLS)

        recommendations = {}
        for type_key, info in ProjectTypeManager.TYPES.items():
            if type_key in ("General", ProjectTypeManager.CUSTOM_TYPE_KEY):
                continue
            tools = set(ProjectTypeManager.get_recommended_tools_for_type(type_key))
            tools = tools - base
            highlight = info.get("highlight_tools", [])
            if highlight:
                tools.update(highlight)
            for tool in tools:
                recommendations.setdefault(tool, []).append(type_key)

        return recommendations

    @staticmethod
    def get_preset_config(type_key, tags=None, length_key="Long"):
        tags = [t for t in (tags or []) if t]
        type_info = ProjectTypeManager.get_type_info(type_key)

        tools = []
        ProjectTypeManager._extend_unique(tools, type_info.get("tools", []))
        ProjectTypeManager._extend_unique(tools, type_info.get("specialized_modules", []))

        wiki_categories = list(type_info.get("wiki_categories", ProjectTypeManager.DEFAULT_WIKI_CATEGORIES))
        ai_hints = list(type_info.get("ai_hints", []))

        for tag in tags:
            tag_info = ProjectTypeManager.get_tag_info(tag)
            ProjectTypeManager._extend_unique(tools, tag_info.get("tools", []))
            ProjectTypeManager._extend_unique(tools, tag_info.get("specialized_modules", []))
            if tag_info.get("wiki_categories"):
                wiki_categories = ProjectTypeManager._merge_categories(wiki_categories, tag_info.get("wiki_categories", []))
            if tag_info.get("ai_hints"):
                ProjectTypeManager._extend_unique(ai_hints, tag_info.get("ai_hints", []))

        ProjectTypeManager._extend_unique(tools, ProjectTypeManager.GLOBAL_DEFAULT_TOOLS)
        ProjectTypeManager._extend_unique(tools, ProjectTypeManager.REQUIRED_TOOLS)

        length_info = ProjectTypeManager.get_length_info(length_key)
        hidden = set(length_info.get("hidden_tools", []))
        default_tab = type_info.get("default_tab")

        final_tools = []
        for tool in tools:
            if tool in hidden:
                if tool in ProjectTypeManager.REQUIRED_TOOLS:
                    final_tools.append(tool)
                elif tool == default_tab:
                    final_tools.append(tool)
                elif (type_key == "Suspense" or "Suspense" in tags) and tool in ["evidence_board", "dual_timeline"]:
                    final_tools.append(tool)
                else:
                    continue
            else:
                final_tools.append(tool)

        for tool in ProjectTypeManager.REQUIRED_TOOLS:
            if tool not in final_tools:
                final_tools.insert(0, tool)

        return {
            "recommended_tools": final_tools,
            "wiki_categories": wiki_categories,
            "outline_view": ProjectTypeManager.get_default_outline_view(type_key),
            "ai_hints": ai_hints,
        }

    @staticmethod
    def get_default_tools(type_key, length_key="Long", tags=None):
        preset = ProjectTypeManager.get_preset_config(type_key, tags, length_key)
        return set(preset.get("recommended_tools", []))

    @staticmethod
    def get_default_tools_list(type_key, length_key="Long", tags=None):
        from writer_app.core.module_registry import get_ordered_module_keys
        default_tools = ProjectTypeManager.get_default_tools(type_key, length_key, tags)
        ordered = []

        for tool in get_ordered_module_keys(visible_only=False):
            if tool in default_tools:
                ordered.append(tool)

        for tool in sorted(default_tools):
            if tool not in ordered:
                ordered.append(tool)

        return ordered

    @staticmethod
    def get_enabled_tools(type_key, length_key="Long"):
        return ProjectTypeManager.get_default_tools(type_key, length_key)


    @staticmethod
    def get_default_tab_key(type_key):
        info = ProjectTypeManager.get_type_info(type_key)
        return info.get("default_tab", "outline")

    @staticmethod
    def get_default_outline_view(type_key):
        """获取项目类型对应的默认大纲视图"""
        info = ProjectTypeManager.get_type_info(type_key)
        outline_view = info.get("outline_view")
        if outline_view:
            return outline_view
        base_key = info.get("base_type")
        if base_key:
            return ProjectTypeManager.OUTLINE_VIEW_DEFAULTS.get(base_key, "horizontal")
        return ProjectTypeManager.OUTLINE_VIEW_DEFAULTS.get(type_key, "horizontal")

    @staticmethod
    def get_specialized_modules(type_key):
        """Get list of specialized module keys for the project type."""
        info = ProjectTypeManager.get_type_info(type_key)
        return info.get("specialized_modules", [])

    @staticmethod
    def get_wiki_categories(type_key):
        """获取项目类型对应的百科分类列表。"""
        info = ProjectTypeManager.get_type_info(type_key)
        return info.get("wiki_categories", ProjectTypeManager.DEFAULT_WIKI_CATEGORIES)

    @staticmethod
    def get_asset_types(type_key):
        """获取项目类型对应的资源类型列表。"""
        info = ProjectTypeManager.get_type_info(type_key)
        return info.get("asset_types", ["reference"])
