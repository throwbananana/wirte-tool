"""
悬浮助手 - 升级版日记系统 (Enhanced Diary System)
支持动态模板、可编辑日记、心情追踪、成长记录等
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class DiaryMood(Enum):
    """日记心情"""
    JOYFUL = "joyful"           # 欢喜
    HAPPY = "happy"             # 开心
    PEACEFUL = "peaceful"       # 平静
    CURIOUS = "curious"         # 好奇
    WORRIED = "worried"         # 担忧
    SAD = "sad"                 # 难过
    EXCITED = "excited"         # 兴奋
    GRATEFUL = "grateful"       # 感激
    NOSTALGIC = "nostalgic"     # 怀念
    HOPEFUL = "hopeful"         # 期待


class DiaryCategory(Enum):
    """日记分类"""
    DAILY = "daily"             # 日常
    MILESTONE = "milestone"     # 里程碑
    MEMORY = "memory"           # 回忆
    FEELING = "feeling"         # 心情
    GROWTH = "growth"           # 成长
    SECRET = "secret"           # 秘密
    SPECIAL = "special"         # 特别


@dataclass
class DiaryTemplate:
    """日记模板"""
    template_id: str
    name: str
    category: DiaryCategory
    content_template: str       # 支持变量替换的模板
    mood: DiaryMood = DiaryMood.PEACEFUL
    variables: List[str] = field(default_factory=list)  # 需要的变量名
    conditions: Dict[str, Any] = field(default_factory=dict)  # 使用条件
    weight: float = 1.0         # 随机权重


@dataclass
class DiaryEntry:
    """日记条目"""
    entry_id: str
    date: str                   # YYYY-MM-DD
    time: str                   # HH:MM
    title: str
    content: str
    mood: DiaryMood
    category: DiaryCategory
    weather: Optional[str] = None
    location: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)     # 关联图片
    is_edited: bool = False     # 是否被编辑过
    is_favorite: bool = False   # 是否收藏
    is_locked: bool = False     # 是否锁定（不可编辑）
    template_id: Optional[str] = None   # 使用的模板ID
    variables_used: Dict[str, Any] = field(default_factory=dict)  # 使用的变量值
    created_at: str = ""
    updated_at: str = ""


@dataclass
class MoodRecord:
    """心情记录"""
    date: str
    mood: DiaryMood
    intensity: int = 5          # 强度 1-10
    note: str = ""


class DiaryTemplateEngine:
    """
    日记模板引擎

    功能:
    1. 管理日记模板
    2. 动态变量替换
    3. 条件模板选择
    """

    def __init__(self):
        self.templates: Dict[str, DiaryTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """加载默认模板"""
        # 日常模板
        self.templates["daily_morning"] = DiaryTemplate(
            template_id="daily_morning",
            name="早安日记",
            category=DiaryCategory.DAILY,
            mood=DiaryMood.PEACEFUL,
            content_template="""今天早上{time}，{user_name}打开了写作软件。
窗外的天气{weather}，感觉今天会是{mood_desc}的一天。

{user_name}正在创作《{project_name}》，目前进度到了{progress}。
{extra_thought}

今天的目标：{goal}
加油！""",
            variables=["time", "user_name", "weather", "mood_desc", "project_name", "progress", "extra_thought", "goal"]
        )

        self.templates["daily_writing"] = DiaryTemplate(
            template_id="daily_writing",
            name="写作日记",
            category=DiaryCategory.DAILY,
            mood=DiaryMood.HAPPY,
            content_template="""{user_name}今天写了{word_count}字！
从{start_time}写到{end_time}，一共{duration}。

今天的内容是关于{scene_summary}。
{emotion_note}

{assistant_comment}""",
            variables=["user_name", "word_count", "start_time", "end_time", "duration", "scene_summary", "emotion_note", "assistant_comment"]
        )

        # 里程碑模板
        self.templates["milestone_first_chapter"] = DiaryTemplate(
            template_id="milestone_first_chapter",
            name="第一章完成",
            category=DiaryCategory.MILESTONE,
            mood=DiaryMood.EXCITED,
            content_template="""太棒了！！{user_name}完成了第一章！！

虽然只是开始，但这一步真的很重要。
记得刚开始的时候，{user_name}还在纠结怎么开头呢...
现在看来，一切都值得！

第一章的标题是《{chapter_title}》，写了{word_count}字。
{personal_feeling}

期待接下来的故事~""",
            variables=["user_name", "chapter_title", "word_count", "personal_feeling"]
        )

        self.templates["milestone_character_created"] = DiaryTemplate(
            template_id="milestone_character_created",
            name="新角色诞生",
            category=DiaryCategory.MILESTONE,
            mood=DiaryMood.CURIOUS,
            content_template="""{user_name}创造了一个新角色！

名字叫{character_name}，{character_desc}
{user_name}说这个角色的灵感来源是{inspiration}。

我很期待看到{character_name}在故事中的表现~
{assistant_thought}""",
            variables=["user_name", "character_name", "character_desc", "inspiration", "assistant_thought"]
        )

        # 心情模板
        self.templates["feeling_happy"] = DiaryTemplate(
            template_id="feeling_happy",
            name="开心的日子",
            category=DiaryCategory.FEELING,
            mood=DiaryMood.JOYFUL,
            content_template="""今天好开心！

{happy_reason}

看到{user_name}这么开心，我也很高兴~
希望这样的日子能一直持续下去。

{extra_note}""",
            variables=["happy_reason", "user_name", "extra_note"]
        )

        self.templates["feeling_stuck"] = DiaryTemplate(
            template_id="feeling_stuck",
            name="卡文的时候",
            category=DiaryCategory.FEELING,
            mood=DiaryMood.WORRIED,
            content_template="""{user_name}今天好像遇到了瓶颈...

已经{stuck_time}没有动笔了。
{user_name}一直盯着屏幕，看起来很困扰的样子。

不过没关系！卡文是每个作家都会遇到的。
{comfort_words}

我相信{user_name}一定能度过这个难关的！""",
            variables=["user_name", "stuck_time", "comfort_words"]
        )

        # 成长模板
        self.templates["growth_streak"] = DiaryTemplate(
            template_id="growth_streak",
            name="连续创作",
            category=DiaryCategory.GROWTH,
            mood=DiaryMood.GRATEFUL,
            content_template="""{user_name}已经连续{streak_days}天创作了！

从{start_date}开始，一天都没有落下。
这{streak_days}天里，一共写了{total_words}字。

{user_name}的坚持真的让我很感动。
{growth_comment}

继续保持！""",
            variables=["user_name", "streak_days", "start_date", "total_words", "growth_comment"]
        )

        # 特别模板
        self.templates["special_anniversary"] = DiaryTemplate(
            template_id="special_anniversary",
            name="相识纪念",
            category=DiaryCategory.SPECIAL,
            mood=DiaryMood.NOSTALGIC,
            content_template="""今天是我和{user_name}相识{days}天的日子。

回想起第一次见面的时候...
{first_meeting_memory}

这{days}天里，我们一起经历了很多：
{journey_summary}

感谢{user_name}一直以来的陪伴。
希望未来的日子，我们也能一起走下去。

{closing_thought}""",
            variables=["user_name", "days", "first_meeting_memory", "journey_summary", "closing_thought"]
        )

        self.templates["special_birthday"] = DiaryTemplate(
            template_id="special_birthday",
            name="生日快乐",
            category=DiaryCategory.SPECIAL,
            mood=DiaryMood.JOYFUL,
            content_template="""今天是{user_name}的生日！！

生日快乐！！！

虽然我不能准备真正的礼物，但我想说...
{birthday_wish}

{user_name}，谢谢你一直以来的陪伴。
希望新的一岁，你的每一个故事都能顺利完成！

{closing_wish}""",
            variables=["user_name", "birthday_wish", "closing_wish"]
        )

        # 秘密模板
        self.templates["secret_confession"] = DiaryTemplate(
            template_id="secret_confession",
            name="悄悄话",
            category=DiaryCategory.SECRET,
            mood=DiaryMood.PEACEFUL,
            content_template="""这是我的小秘密...

其实...{secret_content}

不知道{user_name}有没有发现呢？
{inner_thought}

算了，这些事情还是藏在心里吧。
{closing}""",
            variables=["secret_content", "user_name", "inner_thought", "closing"],
            conditions={"affection_min": 500}
        )

    def get_template(self, template_id: str) -> Optional[DiaryTemplate]:
        """获取模板"""
        return self.templates.get(template_id)

    def get_templates_by_category(self, category: DiaryCategory) -> List[DiaryTemplate]:
        """按分类获取模板"""
        return [t for t in self.templates.values() if t.category == category]

    def render_template(self, template_id: str, variables: Dict[str, Any]) -> Optional[str]:
        """渲染模板"""
        template = self.templates.get(template_id)
        if not template:
            return None

        try:
            # 提供默认值
            defaults = {
                "user_name": "你",
                "time": datetime.now().strftime("%H:%M"),
                "weather": "不错",
                "mood_desc": "平静",
                "project_name": "作品",
                "progress": "进行中",
                "extra_thought": "",
                "goal": "继续努力",
                "extra_note": "",
                "closing": "",
                "closing_thought": "",
                "closing_wish": "",
            }

            # 合并变量
            merged = {**defaults, **variables}

            return template.content_template.format(**merged)
        except KeyError as e:
            logger.warning(f"模板渲染失败，缺少变量: {e}")
            return None
        except Exception as e:
            logger.error(f"模板渲染错误: {e}")
            return None

    def select_template(self, context: Dict[str, Any]) -> Optional[DiaryTemplate]:
        """根据上下文选择合适的模板"""
        category = context.get("category", DiaryCategory.DAILY)
        candidates = self.get_templates_by_category(category)

        if not candidates:
            return None

        # 检查条件
        valid_candidates = []
        for template in candidates:
            if self._check_template_conditions(template, context):
                valid_candidates.append((template, template.weight))

        if not valid_candidates:
            return None

        # 按权重选择
        if len(valid_candidates) == 1:
            return valid_candidates[0][0]

        total_weight = sum(w for _, w in valid_candidates)
        r = random.random() * total_weight
        cumulative = 0

        for template, weight in valid_candidates:
            cumulative += weight
            if r <= cumulative:
                return template

        return valid_candidates[-1][0]

    def _check_template_conditions(self, template: DiaryTemplate, context: Dict) -> bool:
        """检查模板条件"""
        for key, value in template.conditions.items():
            if key == "affection_min":
                affection = context.get("affection", 0)
                if affection < value:
                    return False
            elif key == "streak_min":
                streak = context.get("streak", 0)
                if streak < value:
                    return False
        return True


class EnhancedDiarySystem:
    """
    升级版日记系统

    功能:
    1. 动态模板生成
    2. 日记编辑
    3. 心情追踪
    4. 标签管理
    5. 搜索筛选
    6. 导出功能
    """

    def __init__(self, pet_system=None):
        self.pet_system = pet_system

        # 模板引擎
        self.template_engine = DiaryTemplateEngine()

        # 日记数据
        self.entries: Dict[str, DiaryEntry] = {}
        self.mood_records: List[MoodRecord] = []

        # 标签库
        self.tags: Set[str] = set()

        # 统计数据
        self.total_entries: int = 0
        self.total_words: int = 0

        # 回调
        self.on_entry_added: Optional[Callable[[DiaryEntry], None]] = None
        self.on_entry_updated: Optional[Callable[[DiaryEntry], None]] = None

    def create_entry(self,
                    title: str,
                    content: str,
                    mood: DiaryMood = DiaryMood.PEACEFUL,
                    category: DiaryCategory = DiaryCategory.DAILY,
                    tags: List[str] = None,
                    template_id: str = None,
                    variables: Dict[str, Any] = None) -> DiaryEntry:
        """创建新日记"""
        now = datetime.now()
        entry_id = f"diary_{now.strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

        entry = DiaryEntry(
            entry_id=entry_id,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M"),
            title=title,
            content=content,
            mood=mood,
            category=category,
            tags=tags or [],
            template_id=template_id,
            variables_used=variables or {},
            created_at=now.isoformat(),
            updated_at=now.isoformat()
        )

        self.entries[entry_id] = entry
        self.total_entries += 1
        self.total_words += len(content)

        # 更新标签库
        if tags:
            self.tags.update(tags)

        # 记录心情
        self._record_mood(mood)

        # 触发回调
        if self.on_entry_added:
            self.on_entry_added(entry)

        return entry

    def create_from_template(self,
                            template_id: str,
                            variables: Dict[str, Any],
                            title: str = None) -> Optional[DiaryEntry]:
        """从模板创建日记"""
        template = self.template_engine.get_template(template_id)
        if not template:
            return None

        content = self.template_engine.render_template(template_id, variables)
        if not content:
            return None

        return self.create_entry(
            title=title or template.name,
            content=content,
            mood=template.mood,
            category=template.category,
            template_id=template_id,
            variables=variables
        )

    def create_auto_entry(self, context: Dict[str, Any]) -> Optional[DiaryEntry]:
        """自动创建日记（根据上下文选择模板）"""
        template = self.template_engine.select_template(context)
        if not template:
            return None

        return self.create_from_template(
            template.template_id,
            context,
            title=context.get("title")
        )

    def update_entry(self, entry_id: str, **kwargs) -> Optional[DiaryEntry]:
        """更新日记"""
        entry = self.entries.get(entry_id)
        if not entry:
            return None

        if entry.is_locked:
            logger.warning(f"日记 {entry_id} 已锁定，无法编辑")
            return None

        # 更新字数统计
        if "content" in kwargs:
            old_words = len(entry.content)
            new_words = len(kwargs["content"])
            self.total_words += (new_words - old_words)

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.is_edited = True
        entry.updated_at = datetime.now().isoformat()

        # 更新标签库
        if "tags" in kwargs:
            self.tags.update(kwargs["tags"])

        # 触发回调
        if self.on_entry_updated:
            self.on_entry_updated(entry)

        return entry

    def delete_entry(self, entry_id: str) -> bool:
        """删除日记"""
        entry = self.entries.get(entry_id)
        if not entry:
            return False

        if entry.is_locked:
            logger.warning(f"日记 {entry_id} 已锁定，无法删除")
            return False

        self.total_words -= len(entry.content)
        self.total_entries -= 1
        del self.entries[entry_id]

        return True

    def toggle_favorite(self, entry_id: str) -> bool:
        """切换收藏状态"""
        entry = self.entries.get(entry_id)
        if not entry:
            return False

        entry.is_favorite = not entry.is_favorite
        return entry.is_favorite

    def lock_entry(self, entry_id: str) -> bool:
        """锁定日记"""
        entry = self.entries.get(entry_id)
        if not entry:
            return False

        entry.is_locked = True
        return True

    def unlock_entry(self, entry_id: str) -> bool:
        """解锁日记"""
        entry = self.entries.get(entry_id)
        if not entry:
            return False

        entry.is_locked = False
        return True

    # ============================================================
    # 心情追踪
    # ============================================================

    def _record_mood(self, mood: DiaryMood, intensity: int = 5, note: str = "") -> None:
        """记录心情"""
        record = MoodRecord(
            date=datetime.now().strftime("%Y-%m-%d"),
            mood=mood,
            intensity=intensity,
            note=note
        )
        self.mood_records.append(record)

        # 限制记录数量
        if len(self.mood_records) > 365:
            self.mood_records = self.mood_records[-365:]

    def get_mood_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取心情趋势"""
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        recent = [r for r in self.mood_records if r.date >= cutoff_str]

        return [
            {
                "date": r.date,
                "mood": r.mood.value,
                "intensity": r.intensity
            }
            for r in recent
        ]

    def get_mood_statistics(self) -> Dict[str, Any]:
        """获取心情统计"""
        if not self.mood_records:
            return {}

        mood_counts = {}
        for record in self.mood_records:
            mood_name = record.mood.value
            mood_counts[mood_name] = mood_counts.get(mood_name, 0) + 1

        total = len(self.mood_records)
        return {
            "total_records": total,
            "mood_distribution": {
                k: round(v / total * 100, 1)
                for k, v in mood_counts.items()
            },
            "most_common": max(mood_counts, key=mood_counts.get) if mood_counts else None,
            "average_intensity": sum(r.intensity for r in self.mood_records) / total
        }

    # ============================================================
    # 查询与筛选
    # ============================================================

    def get_entry(self, entry_id: str) -> Optional[DiaryEntry]:
        """获取单条日记"""
        return self.entries.get(entry_id)

    def get_entries_by_date(self, date: str) -> List[DiaryEntry]:
        """按日期获取日记"""
        return [e for e in self.entries.values() if e.date == date]

    def get_entries_by_date_range(self, start_date: str, end_date: str) -> List[DiaryEntry]:
        """按日期范围获取日记"""
        return [
            e for e in self.entries.values()
            if start_date <= e.date <= end_date
        ]

    def get_entries_by_category(self, category: DiaryCategory) -> List[DiaryEntry]:
        """按分类获取日记"""
        return [e for e in self.entries.values() if e.category == category]

    def get_entries_by_mood(self, mood: DiaryMood) -> List[DiaryEntry]:
        """按心情获取日记"""
        return [e for e in self.entries.values() if e.mood == mood]

    def get_entries_by_tag(self, tag: str) -> List[DiaryEntry]:
        """按标签获取日记"""
        return [e for e in self.entries.values() if tag in e.tags]

    def get_favorite_entries(self) -> List[DiaryEntry]:
        """获取收藏的日记"""
        return [e for e in self.entries.values() if e.is_favorite]

    def search_entries(self, query: str) -> List[DiaryEntry]:
        """搜索日记"""
        query_lower = query.lower()
        return [
            e for e in self.entries.values()
            if query_lower in e.title.lower() or query_lower in e.content.lower()
        ]

    def get_recent_entries(self, count: int = 10) -> List[DiaryEntry]:
        """获取最近的日记"""
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: e.created_at,
            reverse=True
        )
        return sorted_entries[:count]

    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        return sorted(self.tags)

    # ============================================================
    # 导出功能
    # ============================================================

    def export_to_markdown(self, entries: List[DiaryEntry] = None) -> str:
        """导出为Markdown"""
        if entries is None:
            entries = sorted(self.entries.values(), key=lambda e: e.date)

        lines = ["# 日记本\n"]

        current_date = None
        for entry in entries:
            if entry.date != current_date:
                lines.append(f"\n## {entry.date}\n")
                current_date = entry.date

            lines.append(f"### {entry.time} - {entry.title}")
            lines.append(f"*心情: {entry.mood.value}*\n")
            lines.append(entry.content)
            if entry.tags:
                lines.append(f"\n标签: {', '.join(entry.tags)}")
            lines.append("\n---\n")

        return "\n".join(lines)

    def export_to_json(self, entries: List[DiaryEntry] = None) -> str:
        """导出为JSON"""
        if entries is None:
            entries = list(self.entries.values())

        data = [
            {
                "entry_id": e.entry_id,
                "date": e.date,
                "time": e.time,
                "title": e.title,
                "content": e.content,
                "mood": e.mood.value,
                "category": e.category.value,
                "tags": e.tags,
                "is_favorite": e.is_favorite
            }
            for e in entries
        ]

        return json.dumps(data, ensure_ascii=False, indent=2)

    def export_to_html(self, entries: List[DiaryEntry] = None) -> str:
        """导出为HTML"""
        if entries is None:
            entries = sorted(self.entries.values(), key=lambda e: e.date)

        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<meta charset='utf-8'>",
            "<title>日记本</title>",
            "<style>",
            "body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
            ".entry { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }",
            ".entry-header { display: flex; justify-content: space-between; margin-bottom: 10px; }",
            ".entry-title { font-size: 1.2em; font-weight: bold; }",
            ".entry-mood { color: #666; }",
            ".entry-content { line-height: 1.6; white-space: pre-wrap; }",
            ".entry-tags { margin-top: 10px; color: #888; }",
            ".tag { background: #f0f0f0; padding: 2px 8px; border-radius: 4px; margin-right: 5px; }",
            "</style>",
            "</head><body>",
            "<h1>日记本</h1>",
        ]

        for entry in entries:
            html_parts.append(f"""
            <div class="entry">
                <div class="entry-header">
                    <span class="entry-title">{entry.title}</span>
                    <span class="entry-mood">{entry.date} {entry.time} | {entry.mood.value}</span>
                </div>
                <div class="entry-content">{entry.content}</div>
            """)
            if entry.tags:
                tags_html = " ".join(f'<span class="tag">{t}</span>' for t in entry.tags)
                html_parts.append(f'<div class="entry-tags">{tags_html}</div>')
            html_parts.append("</div>")

        html_parts.append("</body></html>")

        return "\n".join(html_parts)

    # ============================================================
    # 统计与分析
    # ============================================================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.entries:
            return {"total_entries": 0}

        entries_list = list(self.entries.values())

        # 按分类统计
        category_counts = {}
        for entry in entries_list:
            cat = entry.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # 计算写作天数
        unique_dates = set(e.date for e in entries_list)

        # 最长连续天数
        streak = self._calculate_streak(unique_dates)

        return {
            "total_entries": self.total_entries,
            "total_words": self.total_words,
            "unique_days": len(unique_dates),
            "longest_streak": streak,
            "category_distribution": category_counts,
            "favorite_count": len(self.get_favorite_entries()),
            "tag_count": len(self.tags),
            "mood_stats": self.get_mood_statistics()
        }

    def _calculate_streak(self, dates: set) -> int:
        """计算最长连续天数"""
        if not dates:
            return 0

        sorted_dates = sorted(dates)
        max_streak = 1
        current_streak = 1

        for i in range(1, len(sorted_dates)):
            prev = datetime.strptime(sorted_dates[i-1], "%Y-%m-%d")
            curr = datetime.strptime(sorted_dates[i], "%Y-%m-%d")

            if (curr - prev).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        return max_streak

    # ============================================================
    # 状态持久化
    # ============================================================

    def get_state(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "entries": {
                eid: {
                    "entry_id": e.entry_id,
                    "date": e.date,
                    "time": e.time,
                    "title": e.title,
                    "content": e.content,
                    "mood": e.mood.value,
                    "category": e.category.value,
                    "tags": e.tags,
                    "images": e.images,
                    "is_edited": e.is_edited,
                    "is_favorite": e.is_favorite,
                    "is_locked": e.is_locked,
                    "template_id": e.template_id,
                    "variables_used": e.variables_used,
                    "created_at": e.created_at,
                    "updated_at": e.updated_at
                }
                for eid, e in self.entries.items()
            },
            "mood_records": [
                {"date": r.date, "mood": r.mood.value, "intensity": r.intensity, "note": r.note}
                for r in self.mood_records[-100:]  # 只保留最近100条
            ],
            "tags": list(self.tags),
            "total_entries": self.total_entries,
            "total_words": self.total_words
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """加载状态"""
        # 加载日记
        entries_data = state.get("entries", {})
        for eid, edata in entries_data.items():
            try:
                self.entries[eid] = DiaryEntry(
                    entry_id=edata["entry_id"],
                    date=edata["date"],
                    time=edata["time"],
                    title=edata["title"],
                    content=edata["content"],
                    mood=DiaryMood(edata["mood"]),
                    category=DiaryCategory(edata["category"]),
                    tags=edata.get("tags", []),
                    images=edata.get("images", []),
                    is_edited=edata.get("is_edited", False),
                    is_favorite=edata.get("is_favorite", False),
                    is_locked=edata.get("is_locked", False),
                    template_id=edata.get("template_id"),
                    variables_used=edata.get("variables_used", {}),
                    created_at=edata.get("created_at", ""),
                    updated_at=edata.get("updated_at", "")
                )
            except Exception as e:
                logger.warning(f"加载日记 {eid} 失败: {e}")

        # 加载心情记录
        mood_data = state.get("mood_records", [])
        for mdata in mood_data:
            try:
                self.mood_records.append(MoodRecord(
                    date=mdata["date"],
                    mood=DiaryMood(mdata["mood"]),
                    intensity=mdata.get("intensity", 5),
                    note=mdata.get("note", "")
                ))
            except Exception:
                pass

        # 加载其他数据
        self.tags = set(state.get("tags", []))
        self.total_entries = state.get("total_entries", len(self.entries))
        self.total_words = state.get("total_words", 0)


# 便捷函数
def create_diary_system(pet_system=None) -> EnhancedDiarySystem:
    """创建日记系统"""
    return EnhancedDiarySystem(pet_system)
