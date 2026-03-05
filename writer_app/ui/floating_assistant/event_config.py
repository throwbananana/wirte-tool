"""
事件系统配置加载模块
"""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

# 默认配置数据
DEFAULT_CONFIG = {
    "event_state_default": {
        "unlocked_events": [],
        "module_usage": {},
        "time_marks": {},
        "event_log": [],
        "created_types": [],
        "created_themes": [],
    },
    "event_to_module": {
        "outline_changed": "outline",
        "outline_node_added": "outline",
        "scene_added": "script",
        "scene_updated": "script",
        "scene_deleted": "script",
        "character_added": "characters",
        "character_updated": "characters",
        "character_deleted": "characters",
        "wiki_entry_added": "wiki",
        "wiki_entry_updated": "wiki",
        "wiki_entry_deleted": "wiki",
        "relationship_link_added": "relationship",
        "relationship_link_deleted": "relationship",
        "relationships_updated": "relationship",
        "timeline_event_added": "timeline",
        "timeline_event_updated": "timeline",
        "timeline_event_deleted": "timeline",
        "evidence_node_added": "evidence",
        "evidence_link_added": "evidence",
        "clue_added": "evidence",
        "kanban_task_added": "kanban",
        "kanban_task_updated": "kanban",
        "kanban_task_moved": "kanban",
        "idea_added": "idea",
        "research_added": "research",
        "galgame_asset_added": "assets",
        "asset_added": "assets",
        "asset_updated": "assets",
        "asset_deleted": "assets",
        "faction_added": "faction",
        "faction_relation_changed": "faction",
        "training_completed": "training",
    },
    "creation_event_types": [
        "scene_added",
        "scene_updated",
        "outline_changed",
        "idea_added",
        "research_added",
        "timeline_event_added",
        "kanban_task_added",
    ],
    "theme_event_types": [
        "scene_added",
        "scene_updated",
        "outline_changed",
        "idea_added",
        "research_added",
    ],
    "theme_ignore_prefixes": ["Beat:"],
    "type_photo_states": {
        "General": "writing",
        "Suspense": "thinking",
        "Horror": "startled",
        "Thriller": "worried",
        "Romance": "love",
        "Epic": "knight",
        "Fantasy": "witch",
        "SciFi": "curious",
        "Poetry": "reading",
        "LightNovel": "excited",
        "Galgame": "playing",
        "Fanfic": "happy",
        "*": "writing",
    },
    "module_milestones": [
        {
            "id": "module_newbie",
            "threshold": 4,
            "achievement": "module_newbie",
            "message": "🎯 新手入门：你已经熟悉多个模块啦！",
        },
        {
            "id": "module_explorer",
            "threshold": 8,
            "achievement": "module_explorer",
            "message": "🧭 模块探索者：工具箱越来越全面了。",
        },
        {
            "id": "module_master",
            "threshold": 50,
            "achievement": "module_master",
            "message": "🏆 模块大师：你对工具的使用已经炉火纯青！",
            "type": "usage_count"
        }
    ],
    "type_milestones": [
        {
            "id": "type_explorer",
            "threshold": 2,
            "achievement": "type_explorer",
            "message": "已尝试多种项目类型，题材探索进度+1！",
        },
        {
            "id": "type_collector",
            "threshold": 4,
            "achievement": "type_collector",
            "message": "题材触角越来越广，继续保持~",
        },
        {
            "id": "type_master",
            "threshold": 6,
            "achievement": "type_master",
            "message": "多类型创作达成，题材跨度很厉害！",
        },
    ],
    "theme_milestones": [
        {
            "id": "theme_explorer",
            "threshold": 3,
            "achievement": "theme_explorer",
            "message": "主题标签开始丰富起来了~",
        },
        {
            "id": "theme_collector",
            "threshold": 6,
            "achievement": "theme_collector",
            "message": "主题收集进展顺利，继续探索新题材吧！",
        },
        {
            "id": "theme_master",
            "threshold": 10,
            "achievement": "theme_master",
            "message": "主题版图已展开，创作类型更上一层！",
        },
    ],
    "time_events": [
        {
            "id": "time_early_bird",
            "period": "morning",
            "achievement": "early_bird",
            "message": "🌅 清晨创作打卡成功！",
            "cooldown": "daily",
        },
        {
            "id": "time_night_owl",
            "period": "midnight",
            "achievement": "night_owl",
            "message": "🌙 深夜还在创作，真是夜猫子~",
            "cooldown": "daily",
        },
    ],
    "achievement_photo_rewards": {
        "module_newbie": {
            "General": "happy",
            "Suspense": "thinking",
            "Romance": "love",
            "Epic": "fantasy",
            "SciFi": "curious",
            "Poetry": "writing",
            "LightNovel": "excited",
            "Galgame": "playing",
            "*": "happy",
            "_message": "📸 相册新增一张纪念照片。",
        },
        "module_explorer": {
            "*": "celebrating",
            "_message": "📸 探索里程碑已记录到相册。",
        },
        "type_explorer": {
            "*": "curious",
            "_message": "题材探索留影已入册。",
        },
        "type_collector": {
            "*": "writing",
            "_message": "题材旅程留影已入册。",
        },
        "type_master": {
            "*": "celebrating",
            "_message": "题材大师留影已入册。",
        },
        "theme_explorer": {
            "*": "thinking",
            "_message": "主题探索留影已入册。",
        },
        "theme_collector": {
            "*": "excited",
            "_message": "主题收集留影已入册。",
        },
        "theme_master": {
            "*": "celebrating",
            "_message": "主题开拓留影已入册。",
        },
        "early_bird": {
            "*": "morning",
            "_message": "📸 清晨留影已入册。",
        },
        "night_owl": {
            "*": "midnight",
            "_message": "📸 深夜留影已入册。",
        },
        "birthday": {
            "*": "celebrating",
            "_message": "📸 这一刻值得珍藏，生日照片已存入相册。",
        },
        "anniversary": {
            "*": "trust",
            "_message": "📸 周年纪念照片已存入相册。",
        },
    }
}

def get_default_config_path(config_manager=None) -> str:
    """获取默认配置文件路径"""
    if config_manager and hasattr(config_manager, "config_dir"):
        return os.path.join(config_manager.config_dir, "event_rules.json")
    
    # 回退到用户主目录
    return os.path.join(str(Path.home()), ".writer_tool", "event_rules.json")

def load_event_config(config_path: str) -> Dict[str, Any]:
    """加载事件配置，如果文件不存在则返回空字典（使用代码中的默认值）"""
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading event config: {e}")
        return {}

def save_event_config(config_path: str, config: Dict[str, Any]):
    """保存事件配置"""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving event config: {e}")

# Alias for backward compatibility
DEFAULT_EVENT_CONFIG = DEFAULT_CONFIG