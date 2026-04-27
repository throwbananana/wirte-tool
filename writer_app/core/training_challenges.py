import json
import logging
from typing import List, Dict
import random
from datetime import datetime

from writer_app.core.training import MODES, DAILY_MODE_POOLS, DAILY_QUEST_MODES

logger = logging.getLogger(__name__)

# 定义结构化课程
DEFAULT_CHALLENGES = [
    # --- 赛道1：描写精通 ---
    {
        "id": "c_desc_01",
        "category": "描写精通",
        "title": "第一阶段：静物描写",
        "description": "详细描写你桌上的一件简单物品。聚焦质感、光线和岁月痕迹。",
        "mode": "show_dont_tell",
        "rubric_mode": "show_dont_tell",
        "topic": "日常物品",
        "required_topic": "日常物品",
        "level": "级别1（具象词汇）",
        "min_score": 20,
        "next_challenge": "c_desc_02",
        "unlocked": True,
        "completed": False
    },
    {
        "id": "c_desc_02",
        "category": "描写精通",
        "title": "第二阶段：动态与混沌",
        "description": "描写一个繁忙的街角或拥挤的市场。捕捉动感和能量，但不失焦点。",
        "mode": "keywords",
        "rubric_mode": "sensory",
        "topic": "都市喧嚣",
        "required_keywords": ["人群", "噪声", "气味"],
        "level": "级别2（动作/抽象）",
        "min_score": 22,
        "next_challenge": "c_desc_03",
        "unlocked": False,
        "completed": False
    },
    {
        "id": "c_desc_03",
        "category": "描写精通",
        "title": "第三阶段：盲人观察者",
        "description": "只用声音和气味描写一场雷暴。禁用任何视觉词汇。",
        "mode": "sensory",
        "rubric_mode": "sensory",
        "topic": "雷暴",
        "sensory_constraint": "禁用视觉（只能用听觉/嗅觉）",
        "allow_random_sensory": False,
        "level": "级别3（复杂主题）",
        "min_score": 24,
        "next_challenge": "c_desc_04",
        "unlocked": False,
        "completed": False
    },
    {
        "id": "c_desc_04",
        "category": "描写精通",
        "title": "第四阶段：情感氛围",
        "description": "描写一个让读者感到「孤独」的房间，但不能使用「孤独」或「悲伤」这些词。",
        "mode": "show_dont_tell",
        "rubric_mode": "show_dont_tell",
        "topic": "空房间",
        "prompt_note": "禁用词：孤独、悲伤。请用物件、空间和动作让读者自行感到情绪。",
        "level": "级别3（复杂主题）",
        "min_score": 25,
        "next_challenge": None,
        "unlocked": False,
        "completed": False
    },

    # --- 赛道2：对话道场 ---
    {
        "id": "c_dial_01",
        "category": "对话道场",
        "title": "第一阶段：争论",
        "description": "写一段两个角色就琐事争论的对话。聚焦自然的对话流。",
        "mode": "character_voice",
        "rubric_mode": "character_voice",
        "topic": "晚餐分歧",
        "level": "级别1（具象词汇）",
        "min_score": 20,
        "next_challenge": "c_dial_02",
        "unlocked": True,
        "completed": False
    },
    {
        "id": "c_dial_02",
        "category": "对话道场",
        "title": "第二阶段：潜台词与谎言",
        "description": "两个角色在谈论天气，但实际上他们正在分手。使用潜台词。",
        "mode": "dialogue_subtext",
        "rubric_mode": "dialogue_subtext",
        "topic": "分手潜台词",
        "required_topic": "谈论天气，实际分手",
        "level": "级别2（动作/抽象）",
        "min_score": 23,
        "next_challenge": "c_dial_03",
        "unlocked": False,
        "completed": False
    },
    {
        "id": "c_dial_03",
        "category": "对话道场",
        "title": "第三阶段：高压审讯",
        "description": "一个侦探审讯一个比他更聪明的嫌疑人。运用权力动态。",
        "mode": "dialogue_subtext",
        "rubric_mode": "dialogue_subtext",
        "topic": "审讯",
        "required_topic": "侦探审讯更聪明的嫌疑人",
        "level": "级别3（复杂主题）",
        "min_score": 25,
        "next_challenge": None,
        "unlocked": False,
        "completed": False
    },

    # --- 赛道3：动作与节奏 ---
    {
        "id": "c_act_01",
        "category": "动作与节奏",
        "title": "第一阶段：追逐",
        "description": "写一个短暂的徒步追逐场景。聚焦动词和短句来加快节奏。",
        "mode": "keywords",
        "rubric_mode": "continuation",
        "topic": "巷道追逐",
        "required_keywords": ["奔跑", "转角", "喘息"],
        "level": "级别2（动作/抽象）",
        "min_score": 21,
        "next_challenge": "c_act_02",
        "unlocked": True,
        "completed": False
    },
    {
        "id": "c_act_02",
        "category": "动作与节奏",
        "title": "第二阶段：慢动作",
        "description": "用极致的慢动作描写一场车祸或爆炸。将一秒钟拉长为一个段落。",
        "mode": "show_dont_tell",
        "rubric_mode": "show_dont_tell",
        "topic": "冲击瞬间",
        "level": "级别3（复杂主题）",
        "min_score": 24,
        "next_challenge": None,
        "unlocked": False,
        "completed": False
    },

    # --- 赛道4：创意训练 ---
    {
        "id": "c_creative_01",
        "category": "创意训练",
        "title": "第一阶段：点子喷泉",
        "description": "同一主题下写出10个截然不同的创意设定。",
        "mode": "brainstorm",
        "rubric_mode": "brainstorm",
        "topic": "被遗弃的主题公园",
        "level": "级别2（动作/抽象）",
        "min_score": 20,
        "next_challenge": "c_creative_02",
        "unlocked": True,
        "completed": False
    },
    {
        "id": "c_creative_02",
        "category": "创意训练",
        "title": "第二阶段：关键词变奏",
        "description": "基于关键词写一段包含转折的短段落，确保每个关键词都有作用。",
        "mode": "keywords",
        "rubric_mode": "keywords",
        "topic": "被遗弃的主题公园",
        "required_keywords": ["摩天轮", "售票亭", "广播"],
        "level": "级别2（动作/抽象）",
        "min_score": 22,
        "next_challenge": None,
        "unlocked": False,
        "completed": False
    },

    # --- 赛道5：风格模仿 ---
    {
        "id": "c_style_01",
        "category": "风格模仿",
        "title": "第一阶段：海明威的冰山",
        "description": "写一对情侣在等火车的场景。使用简短、简洁的句子。",
        "mode": "style",
        "rubric_mode": "style",
        "topic": "等待火车",
        "required_style": "海明威风格（极简主义、冰山理论）",
        "allow_random_style": False,
        "level": "级别2（动作/抽象）",
        "min_score": 22,
        "next_challenge": "c_style_02",
        "unlocked": True,
        "completed": False
    },
    {
        "id": "c_style_02",
        "category": "风格模仿",
        "title": "第二阶段：黑色电影氛围",
        "description": "一个侦探在雨夜走进他的办公室。使用愤世嫉俗的语调和黑暗意象。",
        "mode": "style",
        "rubric_mode": "style",
        "topic": "侦探办公室",
        "required_style": "黑色电影风格（愤世嫉俗、黑暗、氛围感）",
        "allow_random_style": False,
        "level": "级别2（动作/抽象）",
        "min_score": 23,
        "next_challenge": "c_style_03",
        "unlocked": False,
        "completed": False
    },
    {
        "id": "c_style_03",
        "category": "风格模仿",
        "title": "第三阶段：洛夫克拉夫特式恐怖",
        "description": "描写在洞穴中发现的一件古老神器。使用繁复、古旧的语言，强调恐惧感。",
        "mode": "style",
        "rubric_mode": "style",
        "topic": "禁忌神像",
        "required_style": "洛夫克拉夫特风格（宇宙恐怖、繁复、古老）",
        "allow_random_style": False,
        "level": "级别3（复杂主题）",
        "min_score": 25,
        "next_challenge": None,
        "unlocked": False,
        "completed": False
    },

    # --- 赛道6：类型研究 ---
    {
        "id": "c_genre_01",
        "category": "类型研究",
        "title": "第一阶段：赛博朋克霓虹",
        "description": "描写一个未来主义的街头市场。聚焦「高科技、低生活」。",
        "mode": "style",
        "rubric_mode": "style",
        "topic": "夜城市场",
        "required_style": "赛博朋克风格（高科技、低生活、霓虹灯）",
        "allow_random_style": False,
        "level": "级别2（动作/抽象）",
        "min_score": 22,
        "next_challenge": "c_genre_02",
        "unlocked": True,
        "completed": False
    },
    {
        "id": "c_genre_02",
        "category": "类型研究",
        "title": "第二阶段：武侠对决",
        "description": "两个剑客在竹林相遇。聚焦氛围、风声和内功。",
        "mode": "sensory",
        "rubric_mode": "sensory",
        "topic": "竹林决斗",
        "sensory_constraint": "聚焦声音、触觉与气息，减少直白视觉铺陈",
        "allow_random_sensory": False,
        "level": "级别2（动作/抽象）",
        "min_score": 23,
        "next_challenge": None,
        "unlocked": False,
        "completed": False
    }
]


class ChallengeManager:
    """管理阶段性训练挑战和每日任务的生命周期。"""

    def __init__(self, data_dir):
        self.file_path = data_dir / "training_challenges.json"
        self.quest_file_path = data_dir / "daily_quest.json"
        self.challenges = []
        self.daily_quest = None
        self.load()
        self.load_daily_quest()

    def _normalize_challenge_entry(self, entry: Dict) -> Dict:
        if not isinstance(entry, dict):
            return {}
        normalized = dict(entry)
        mode = normalized.get("mode") or "keywords"
        if mode not in MODES:
            mode = "keywords"
        normalized["mode"] = mode
        rubric_mode = normalized.get("rubric_mode") or mode
        normalized["rubric_mode"] = rubric_mode if rubric_mode in MODES else mode
        normalized.setdefault("required_topic", normalized.get("topic", ""))
        normalized.setdefault("required_keywords", [])
        normalized.setdefault("required_style", "")
        normalized.setdefault("sensory_constraint", "")
        normalized.setdefault("allow_random_style", not bool(normalized.get("required_style")))
        normalized.setdefault("allow_random_sensory", not bool(normalized.get("sensory_constraint")))
        normalized.setdefault("prompt_note", "")
        return normalized

    def _migrate_challenges(self, loaded) -> tuple[list, bool]:
        """
        Merge loaded challenges with DEFAULT_CHALLENGES.

        This normalizes localized text while preserving user progress states
        and keeps any custom challenges that are not part of the defaults.
        """
        if not isinstance(loaded, list):
            return [dict(c) for c in DEFAULT_CHALLENGES], True

        default_by_id = {c["id"]: c for c in DEFAULT_CHALLENGES}
        loaded_by_id = {
            c.get("id"): c for c in loaded
            if isinstance(c, dict) and c.get("id")
        }

        merged = []
        for default in DEFAULT_CHALLENGES:
            existing = loaded_by_id.get(default["id"])
            if existing:
                entry = self._normalize_challenge_entry(default)
                # Preserve progress and any tuned difficulty.
                entry["unlocked"] = existing.get("unlocked", default["unlocked"])
                entry["completed"] = existing.get("completed", default["completed"])
                entry["min_score"] = existing.get("min_score", default["min_score"])
                merged.append(entry)
            else:
                merged.append(self._normalize_challenge_entry(default))

        # Keep custom challenges that are not part of the defaults.
        for cid, existing in loaded_by_id.items():
            if cid not in default_by_id:
                merged.append(self._normalize_challenge_entry(existing))

        return merged, merged != loaded

    def load(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                self.challenges, changed = self._migrate_challenges(loaded)
                if changed:
                    logger.info("训练挑战数据已迁移为最新结构")
                    self.save()
            except Exception as e:
                logger.warning(f"加载挑战数据失败，使用默认数据: {e}")
                self.challenges = [self._normalize_challenge_entry(c) for c in DEFAULT_CHALLENGES]
        else:
            self.challenges = [self._normalize_challenge_entry(c) for c in DEFAULT_CHALLENGES]
            self.save()

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.challenges, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存挑战数据失败: {e}")

    def get_all_challenges(self):
        return self.challenges

    def get_challenge(self, challenge_id):
        for c in self.challenges:
            if c["id"] == challenge_id:
                return c
        return None

    def complete_challenge(self, challenge_id, score):
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return False, "未找到挑战"

        if score >= challenge["min_score"]:
            challenge["completed"] = True
            msg = f"挑战完成！（得分 {score}/{challenge['min_score']}）"

            if challenge["next_challenge"]:
                next_c = self.get_challenge(challenge["next_challenge"])
                if next_c:
                    next_c["unlocked"] = True
                    msg += f"\n已解锁：{next_c['title']}"

            self.save()
            return True, msg
        else:
            return False, f"得分 {score} 不足，需要 {challenge['min_score']} 分才能通过。"

    # --- 每日任务逻辑 ---

    def load_daily_quest(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.quest_file_path.exists():
            try:
                with open(self.quest_file_path, 'r', encoding='utf-8') as f:
                    quest = json.load(f)
                    if quest.get("date") == today:
                        mode = quest.get("mode")
                        if mode not in DAILY_QUEST_MODES:
                            quest["mode"] = "keywords"
                            mode = "keywords"
                        quest["rubric_mode"] = quest.get("rubric_mode") or mode
                        if "generated_by" not in quest:
                            quest["generated_by"] = "local"
                            self.daily_quest = quest
                            self.save_daily_quest()
                        else:
                            self.daily_quest = quest
                        return
            except Exception as e:
                logger.warning(f"加载每日任务失败: {e}")

        self.generate_new_daily_quest(today)

    def generate_new_daily_quest(self, date_str):
        # 从分层训练池中随机挑选，避免每日任务长期停留在基础模式。
        stage = random.choice(list(DAILY_MODE_POOLS.keys()))
        modes = DAILY_MODE_POOLS[stage]
        mode = random.choice(modes)
        topics = ["失落之城", "赛博朋克咖啡馆", "初雪", "破碎的时钟", "午夜列车", "迟到的告白", "旧书店重逢"]
        topic = random.choice(topics)
        mode_name = MODES.get(mode, mode)
        level_by_stage = {
            "beginner": "级别1（具象词汇）",
            "intermediate": "级别2（动作/抽象）",
            "advanced": "级别3（复杂主题）",
        }

        self.daily_quest = {
            "date": date_str,
            "title": f"每日任务：{topic}",
            "description": f"完成一个「{mode_name}」练习，主题是「{topic}」。",
            "mode": mode,
            "rubric_mode": mode,
            "topic": topic,
            "level": level_by_stage.get(stage, "级别2（动作/抽象）"),
            "stage": stage,
            "completed": False,
            "generated_by": "local"
        }
        self.save_daily_quest()

    def save_daily_quest(self):
        try:
            with open(self.quest_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.daily_quest, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存每日任务失败: {e}")

    def set_daily_quest(self, quest: Dict) -> None:
        """Replace current daily quest and persist it."""
        if not isinstance(quest, dict):
            return
        mode = quest.get("mode")
        if mode not in DAILY_QUEST_MODES:
            mode = "keywords"
        quest["mode"] = mode
        rubric_mode = quest.get("rubric_mode") or mode
        quest["rubric_mode"] = rubric_mode if rubric_mode in MODES else mode
        self.daily_quest = quest
        self.save_daily_quest()

    def get_daily_quest(self):
        # 如果应用运行时日期变化则刷新
        today = datetime.now().strftime("%Y-%m-%d")
        if self.daily_quest.get("date") != today:
            self.generate_new_daily_quest(today)
        return self.daily_quest

    def complete_daily_quest(self):
        if self.daily_quest and not self.daily_quest["completed"]:
            self.daily_quest["completed"] = True
            self.save_daily_quest()
            return True
        return False
