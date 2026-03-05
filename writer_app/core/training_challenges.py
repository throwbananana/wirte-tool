import json
import logging
from typing import List, Dict
import random
from datetime import datetime

from writer_app.core.training import MODES

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
        "topic": "日常物品",
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
        "topic": "都市喧嚣",
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
        "topic": "雷暴",
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
        "topic": "空房间",
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
        "mode": "continuation",
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
        "mode": "continuation",
        "topic": "分手潜台词",
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
        "mode": "continuation",
        "topic": "审讯",
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
        "topic": "巷道追逐",
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
        "topic": "被遗弃的主题公园",
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
        "topic": "等待火车",
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
        "topic": "侦探办公室",
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
        "topic": "禁忌神像",
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
        "mode": "keywords",
        "topic": "夜城市场",
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
        "mode": "keywords",
        "topic": "竹林决斗",
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
                entry = dict(default)
                # Preserve progress and any tuned difficulty.
                entry["unlocked"] = existing.get("unlocked", default["unlocked"])
                entry["completed"] = existing.get("completed", default["completed"])
                entry["min_score"] = existing.get("min_score", default["min_score"])
                merged.append(entry)
            else:
                merged.append(dict(default))

        # Keep custom challenges that are not part of the defaults.
        for cid, existing in loaded_by_id.items():
            if cid not in default_by_id:
                merged.append(existing)

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
                self.challenges = DEFAULT_CHALLENGES
        else:
            self.challenges = DEFAULT_CHALLENGES
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
        # 从可用池中随机挑选
        modes = ["keywords", "brainstorm", "style", "sensory", "show_dont_tell", "editing"]
        mode = random.choice(modes)
        topics = ["失落之城", "赛博朋克咖啡馆", "初雪", "破碎的时钟", "午夜列车"]
        topic = random.choice(topics)
        mode_name = MODES.get(mode, mode)

        self.daily_quest = {
            "date": date_str,
            "title": f"每日任务：{topic}",
            "description": f"完成一个「{mode_name}」练习，主题是「{topic}」。",
            "mode": mode,
            "topic": topic,
            "level": "级别2（动作/抽象）",  # 默认每日难度
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
