"""
悬浮写作助手 - 养成系统模块
管理好感度、心情、成就、收藏品以及分层奖励体系
"""
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .constants import ACHIEVEMENTS, FOODS
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)


class MoodLevel(Enum):
    """心情等级"""
    GREAT = 5      # 极好
    GOOD = 4       # 好
    NORMAL = 3     # 一般
    BAD = 2        # 差
    TERRIBLE = 1   # 极差


# 每日任务配置
DAILY_TASKS = [
    {"id": "greet", "label": "打个招呼", "target": 1},
    {"id": "feed", "label": "投喂一次", "target": 1},
    {"id": "game", "label": "玩一局小游戏", "target": 1},
]

DAILY_TASK_REWARD = {
    "xp": 20,
    "coins": 15,
    "affection": 2,
}


@dataclass
class PetData:
    """养成数据结构"""
    # --- 基础数值 ---
    affection: int = 0                      # 好感度 (长期)
    mood: int = 100                         # 心情值 (0-100, 短期)
    mood_level: MoodLevel = MoodLevel.GOOD  # 心情等级
    total_xp: int = 0                       # 总经验值 (长期成长)
    level: int = 1                          # 等级 (成长阶段)
    coins: int = 0                          # 金币 (中短期货币) - NEW
    
    # --- 行为统计 ---
    feed_count: int = 0                     # 喂食次数
    name_gen_count: int = 0                 # 起名次数
    prompt_count: int = 0                   # 抽卡次数
    timer_count: int = 0                    # 完成计时次数
    timer_streak: int = 0                   # 连续完成计时次数
    total_chats: int = 0                    # 总对话次数
    game_wins: int = 0                      # 游戏胜利次数
    consecutive_sixes: int = 0              # 骰子连续6次数
    
    # --- 收集与解锁 ---
    collected_foods: Set[str] = field(default_factory=set)  # 收集的食物
    unlocked_achievements: Set[str] = field(default_factory=set)  # 已解锁成就
    inventory: Dict[str, int] = field(default_factory=dict) # 背包 {item_id: count} - NEW
    unlocked_skins: Set[str] = field(default_factory=set)   # 已解锁皮肤 - NEW
    
    # --- 时间记录 ---
    created_at: str = ""                    # 创建时间
    last_interaction: str = ""              # 最后互动时间
    daily_streak: int = 0                   # 连续使用天数
    last_daily_check: str = ""              # 最后签到日期
    last_mood_decay: str = ""               # 最后心情衰减结算时间

    # --- 每日任务 ---
    daily_task_date: str = ""               # 今日任务日期
    daily_task_progress: Dict[str, int] = field(default_factory=dict)
    daily_task_claimed: bool = False

    # --- 复杂状态 ---
    album_photos: List[Dict] = field(default_factory=list)  # 相册照片
    event_state: Dict[str, Any] = field(default_factory=dict)  # 事件系统状态
    completed_events: Set[str] = field(default_factory=set)  # 已完成的事件ID
    event_history: List[Dict] = field(default_factory=list)  # 事件历史记录
    diary_entries: List[Dict] = field(default_factory=list)  # 日记记录
    npc_relations: Dict[str, int] = field(default_factory=dict)  # NPC关系网

    def to_dict(self) -> Dict:
        """转换为字典（用于保存）"""
        return {
            "affection": self.affection,
            "mood": self.mood,
            "total_xp": self.total_xp,
            "level": self.level,
            "coins": self.coins,
            "feed_count": self.feed_count,
            "name_gen_count": self.name_gen_count,
            "prompt_count": self.prompt_count,
            "timer_count": self.timer_count,
            "timer_streak": self.timer_streak,
            "collected_foods": list(self.collected_foods),
            "achievements": list(self.unlocked_achievements),
            "inventory": self.inventory,
            "unlocked_skins": list(self.unlocked_skins),
            "total_chats": self.total_chats,
            "created_at": self.created_at,
            "last_interaction": self.last_interaction,
            "daily_streak": self.daily_streak,
            "last_daily_check": self.last_daily_check,
            "last_mood_decay": self.last_mood_decay,
            "daily_task_date": self.daily_task_date,
            "daily_task_progress": self.daily_task_progress,
            "daily_task_claimed": self.daily_task_claimed,
            "album_photos": self.album_photos,
            "event_state": self.event_state,
            "completed_events": list(self.completed_events),
            "event_history": self.event_history,
            "diary_entries": self.diary_entries,
            "npc_relations": self.npc_relations,
            "game_wins": self.game_wins,
            "consecutive_sixes": self.consecutive_sixes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PetData":
        """从字典创建"""
        pet = cls()
        # 基础数值
        pet.affection = data.get("affection", 0)
        pet.mood = data.get("mood", 100)
        pet.total_xp = data.get("total_xp", 0)
        pet.level = data.get("level", 1)
        pet.coins = data.get("coins", 0)
        
        # 统计
        pet.feed_count = data.get("feed_count", 0)
        pet.name_gen_count = data.get("name_gen_count", 0)
        pet.prompt_count = data.get("prompt_count", 0)
        pet.timer_count = data.get("timer_count", 0)
        pet.timer_streak = data.get("timer_streak", 0)
        pet.total_chats = data.get("total_chats", 0)
        pet.game_wins = data.get("game_wins", 0)
        pet.consecutive_sixes = data.get("consecutive_sixes", 0)
        
        # 收集
        pet.collected_foods = set(data.get("collected_foods", []))
        pet.unlocked_achievements = set(data.get("achievements", []))
        pet.inventory = data.get("inventory", {})
        pet.unlocked_skins = set(data.get("unlocked_skins", []))
        
        # 时间
        pet.created_at = data.get("created_at", datetime.now().isoformat())
        pet.last_interaction = data.get("last_interaction", "")
        pet.daily_streak = data.get("daily_streak", 0)
        pet.last_daily_check = data.get("last_daily_check", "")
        pet.last_mood_decay = data.get("last_mood_decay", "")
        pet.daily_task_date = data.get("daily_task_date", "")
        pet.daily_task_progress = data.get("daily_task_progress", {})
        pet.daily_task_claimed = data.get("daily_task_claimed", False)
        
        # 复杂状态
        pet.album_photos = data.get("album_photos", [])
        pet.event_state = data.get("event_state", {})
        pet.completed_events = set(data.get("completed_events", []))
        pet.event_history = data.get("event_history", [])
        pet.diary_entries = data.get("diary_entries", [])
        pet.npc_relations = data.get("npc_relations", {})
        
        pet._update_mood_level()
        return pet

    def _update_mood_level(self):
        """更新心情等级"""
        if self.mood >= 80:
            self.mood_level = MoodLevel.GREAT
        elif self.mood >= 60:
            self.mood_level = MoodLevel.GOOD
        elif self.mood >= 40:
            self.mood_level = MoodLevel.NORMAL
        elif self.mood >= 20:
            self.mood_level = MoodLevel.BAD
        else:
            self.mood_level = MoodLevel.TERRIBLE


class PetSystem:
    """养成系统管理器"""

    # 等级经验需求 (指数增长)
    LEVEL_XP = {
        1: 0, 2: 100, 3: 250, 4: 500, 5: 800,
        6: 1200, 7: 1700, 8: 2300, 9: 3000, 10: 4000,
        11: 5000, 12: 6500, 13: 8000, 14: 10000, 15: 12500,
    }

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.data = self._load_data()
        self._achievement_callbacks: List[Callable[[str], None]] = []
        self._level_up_callbacks: List[Callable[[int], None]] = []

    def _load_data(self) -> PetData:
        """从配置加载数据"""
        saved = self.config_manager.get("pet_system", {})
        if saved:
            return PetData.from_dict(saved)
        # 新建数据
        data = PetData()
        data.created_at = datetime.now().isoformat()
        return data

    def save(self):
        """保存数据"""
        self.config_manager.set("pet_system", self.data.to_dict())
        self.config_manager.save()

    def on_achievement(self, callback: Callable[[str], None]):
        """注册成就解锁回调"""
        self._achievement_callbacks.append(callback)

    def on_level_up(self, callback: Callable[[int], None]):
        """注册升级回调"""
        self._level_up_callbacks.append(callback)

    # ========================================
    # 奖励系统 (核心升级)
    # ========================================

    def add_reward(self, xp: int = 0, coins: int = 0, affection: int = 0, items: Dict[str, int] = None):
        """
        发放复合奖励
        """
        rewards_log = []
        
        if xp > 0:
            leveled_up = self.add_xp(xp)
            rewards_log.append(f"经验 +{xp}")
            if leveled_up:
                rewards_log.append(f"升级! Lv.{self.data.level}")
                
        if coins > 0:
            self.data.coins += coins
            rewards_log.append(f"金币 +{coins}")
            
        if affection > 0:
            self.add_affection(affection)
            rewards_log.append(f"好感 +{affection}")
            
        if items:
            for item_id, count in items.items():
                current = self.data.inventory.get(item_id, 0)
                self.data.inventory[item_id] = current + count
                rewards_log.append(f"获得道具: {item_id} x{count}")
                
        self.save()
        return rewards_log

    def add_xp(self, amount: int) -> bool:
        """增加经验值并检查升级"""
        self.data.total_xp += amount
        old_level = self.data.level

        # 计算新等级
        for level, required in sorted(self.LEVEL_XP.items(), reverse=True):
            if self.data.total_xp >= required:
                self.data.level = level
                break

        leveled_up = self.data.level > old_level

        if leveled_up:
            # 触发升级回调
            for callback in self._level_up_callbacks:
                try:
                    callback(self.data.level)
                except Exception:
                    pass
            # 升级奖励：少量金币
            self.data.coins += 50 

        return leveled_up

    # ========================================
    # 好感度系统
    # ========================================

    def add_affection(self, amount: int) -> List[str]:
        """增加好感度"""
        old_affection = self.data.affection
        self.data.affection = min(self.data.affection + amount, 9999)

        # 检查好感度成就
        unlocked = []
        thresholds = [
            (50, "affection_50"),
            (100, "affection_100"),
            (200, "affection_200"),
            (500, "affection_500"),
        ]
        for threshold, ach_id in thresholds:
            if old_affection < threshold <= self.data.affection:
                if self.unlock_achievement(ach_id):
                    unlocked.append(ach_id)

        self.save()
        return unlocked

    def add_diary_entry(self, event_id: str, title: str, content: str, choice_index: int = 0) -> bool:
        """
        向助手日记本写入新条目
        :return: bool 是否成功写入(去重后)
        """
        # 去重检查
        existing = next((d for d in self.data.diary_entries 
                       if d["event_id"] == event_id and d["choice_index"] == choice_index), None)
        if existing:
            return False
            
        diary_entry = {
            "event_id": event_id,
            "event_title": title,
            "choice_index": choice_index,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "is_new": True 
        }
        self.data.diary_entries.insert(0, diary_entry)
        
        # 限制日记数量
        if len(self.data.diary_entries) > 50:
            self.data.diary_entries = self.data.diary_entries[:50]
            
        self.save()
        return True

    def get_affection_level(self) -> str:
        """获取好感度等级名称"""
        aff = self.data.affection
        if aff < 30:
            return "初见"
        elif aff < 60:
            return "友好"
        elif aff < 100:
            return "亲密"
        elif aff < 200:
            return "挚友"
        elif aff < 500:
            return "羁绊"
        else:
            return "灵魂伴侣"

    def get_affection_bonus_state(self, base_state: str) -> str:
        """根据好感度获取增强状态"""
        from .states import AssistantState

        if self.data.affection >= 200:
            upgrades = {
                AssistantState.HAPPY: AssistantState.DEVOTED,
                AssistantState.LOVE: AssistantState.DEVOTED,
                AssistantState.SHY: AssistantState.BLUSH,
            }
            return upgrades.get(base_state, base_state)
        elif self.data.affection >= 100:
            upgrades = {
                AssistantState.HAPPY: AssistantState.TRUST,
                AssistantState.SHY: AssistantState.BLUSH,
            }
            return upgrades.get(base_state, base_state)
        elif self.data.affection >= 50:
            upgrades = {
                AssistantState.SHY: AssistantState.BLUSH,
                AssistantState.LOVE: AssistantState.BLUSH,
            }
            return upgrades.get(base_state, base_state)
        return base_state

    # ========================================
    # 心情系统
    # ========================================

    def update_mood(self, delta: int):
        """更新心情值"""
        self.data.mood = max(0, min(100, self.data.mood + delta))
        self.data._update_mood_level()
        self.save()

    def decay_mood(self):
        """心情自然衰减（长时间不互动）"""
        if not self.data.last_interaction:
            return

        reference_time = self.data.last_mood_decay or self.data.last_interaction
        try:
            last = datetime.fromisoformat(reference_time)
            now = datetime.now()
            hours_passed = (now - last).total_seconds() / 3600

            if hours_passed >= 1:
                decay = min(int(hours_passed), 20)
                if decay > 0:
                    self.data.mood = max(20, self.data.mood - decay)
                    self.data._update_mood_level()
                    
                    # 记录这次衰减的时间点，保留分钟级的进度
                    new_time = last + timedelta(hours=decay)
                    self.data.last_mood_decay = new_time.isoformat()
                    self.save()
        except Exception:
            pass

    def get_mood_emoji(self) -> str:
        """获取心情对应的图标 (Fluent UI)"""
        level = self.data.mood_level
        return {
            MoodLevel.GREAT: get_icon("presence_available", "😁"),
            MoodLevel.GOOD: get_icon("presence_available", "😊"),
            MoodLevel.NORMAL: get_icon("presence_away", "😐"),
            MoodLevel.BAD: get_icon("presence_dnd", "😞"),
            MoodLevel.TERRIBLE: get_icon("presence_blocked", "😭"),
        }.get(level, get_icon("presence_away", "😐"))

    def get_mood_name(self) -> str:
        """获取心情名称"""
        level = self.data.mood_level
        return {
            MoodLevel.GREAT: "极好",
            MoodLevel.GOOD: "开心",
            MoodLevel.NORMAL: "平静",
            MoodLevel.BAD: "低落",
            MoodLevel.TERRIBLE: "极差",
        }.get(level, "平静")


    def get_mood_state(self) -> str:
        """获取心情对应的状态"""
        from .states import AssistantState

        level = self.data.mood_level
        return {
            MoodLevel.GREAT: AssistantState.EXCITED,
            MoodLevel.GOOD: AssistantState.HAPPY,
            MoodLevel.NORMAL: AssistantState.IDLE,
            MoodLevel.BAD: AssistantState.SAD,
            MoodLevel.TERRIBLE: AssistantState.WORRIED,
        }.get(level, AssistantState.IDLE)

    # ========================================
    # 成就系统
    # ========================================

    def unlock_achievement(self, achievement_id: str) -> bool:
        """解锁成就"""
        if achievement_id in self.data.unlocked_achievements:
            return False

        if achievement_id not in ACHIEVEMENTS:
            return False

        self.data.unlocked_achievements.add(achievement_id)

        # 获得奖励 (混合)
        ach_data = ACHIEVEMENTS[achievement_id]
        xp = ach_data.get("xp", 10)
        self.add_xp(xp)
        
        # 成就解锁奖励金币
        self.data.coins += 20

        self.save()

        # 触发回调
        for callback in self._achievement_callbacks:
            try:
                callback(achievement_id)
            except Exception:
                pass

        return True

    def get_achievement_progress(self) -> Dict[str, Any]:
        """获取成就进度"""
        unlocked = len(self.data.unlocked_achievements)
        total = len(ACHIEVEMENTS)
        return {
            "unlocked": unlocked,
            "total": total,
            "percentage": (unlocked / total * 100) if total > 0 else 0,
            "unlocked_list": list(self.data.unlocked_achievements),
        }

    def check_and_unlock_achievements(self) -> List[str]:
        """检查并解锁所有符合条件的成就"""
        unlocked = []

        # 对话成就
        if self.data.total_chats >= 1:
            if self.unlock_achievement("first_chat"):
                unlocked.append("first_chat")
        if self.data.total_chats >= 100:
            if self.unlock_achievement("chat_100"):
                unlocked.append("chat_100")
        if self.data.total_chats >= 500:
            if self.unlock_achievement("chat_500"):
                unlocked.append("chat_500")

        # 喂食成就
        if self.data.feed_count >= 10:
            if self.unlock_achievement("feed_10"):
                unlocked.append("feed_10")
        if self.data.feed_count >= 50:
            if self.unlock_achievement("feed_50"):
                unlocked.append("feed_50")
        if self.data.feed_count >= 100:
            if self.unlock_achievement("feed_100"):
                unlocked.append("feed_100")

        # 工具成就
        if self.data.name_gen_count >= 10:
            if self.unlock_achievement("name_gen_10"):
                unlocked.append("name_gen_10")
        if self.data.name_gen_count >= 50:
            if self.unlock_achievement("name_gen_50"):
                unlocked.append("name_gen_50")
        if self.data.prompt_count >= 20:
            if self.unlock_achievement("prompt_20"):
                unlocked.append("prompt_20")
        if self.data.prompt_count >= 100:
            if self.unlock_achievement("prompt_100"):
                unlocked.append("prompt_100")

        # 计时器成就
        if self.data.timer_count >= 10:
            if self.unlock_achievement("timer_10"):
                unlocked.append("timer_10")
        if self.data.timer_streak >= 3:
            if self.unlock_achievement("timer_streak"):
                unlocked.append("timer_streak")

        # 收集成就
        if len(self.data.collected_foods) >= len(FOODS):
            if self.unlock_achievement("collect_all_food"):
                unlocked.append("collect_all_food")

        # 连续使用成就
        if self.data.daily_streak >= 7:
            if self.unlock_achievement("daily_streak_7"):
                unlocked.append("daily_streak_7")
        if self.data.daily_streak >= 30:
            if self.unlock_achievement("daily_streak_30"):
                unlocked.append("daily_streak_30")

        # 游戏成就
        if self.data.game_wins >= 10:
            if self.unlock_achievement("game_winner"):
                unlocked.append("game_winner")

        return unlocked

    # ========================================
    # 每日签到
    # ========================================

    def check_daily(self) -> Dict[str, Any]:
        """
        检查每日签到

        Returns:
            {
                "is_new_day": bool,
                "streak_continued": bool,
                "streak": int,
                "bonus_affection": int,
                "bonus_mood": int,
                "bonus_coins": int,  # NEW
            }
        """
        today = datetime.now().strftime("%Y-%m-%d")
        result = {
            "is_new_day": False,
            "streak_continued": False,
            "streak": self.data.daily_streak,
            "bonus_affection": 0,
            "bonus_mood": 0,
            "bonus_coins": 0,
        }

        if self.data.last_daily_check == today:
            return result

        result["is_new_day"] = True

        # 检查是否连续
        if self.data.last_daily_check:
            try:
                last_date = datetime.strptime(self.data.last_daily_check, "%Y-%m-%d")
                today_date = datetime.strptime(today, "%Y-%m-%d")
                diff = (today_date - last_date).days

                if diff == 1:
                    self.data.daily_streak += 1
                    result["streak_continued"] = True
                elif diff > 1:
                    self.data.daily_streak = 1
            except Exception:
                self.data.daily_streak = 1
        else:
            self.data.daily_streak = 1

        result["streak"] = self.data.daily_streak

        # 计算奖励 (引入阶梯式奖励)
        base_affection = 5
        base_coins = 10
        streak_bonus = min(self.data.daily_streak, 7)  # 最多7天额外奖励
        
        result["bonus_affection"] = base_affection + streak_bonus
        result["bonus_mood"] = 5 + streak_bonus
        result["bonus_coins"] = base_coins + (streak_bonus * 5) # 签到金币奖励

        # 应用奖励
        self.add_reward(
            affection=result["bonus_affection"],
            coins=result["bonus_coins"]
        )
        self.update_mood(result["bonus_mood"])

        self.data.last_daily_check = today
        self.save()

        # 检查连续签到成就
        self.check_and_unlock_achievements()

        return result

    # ========================================
    # 每日任务
    # ========================================

    def _ensure_daily_task_state(self):
        """确保每日任务状态为当天"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.data.daily_task_date != today:
            self.data.daily_task_date = today
            self.data.daily_task_progress = {}
            self.data.daily_task_claimed = False
            self.save()

    def get_daily_task_status(self) -> Dict[str, Any]:
        """获取每日任务状态"""
        self._ensure_daily_task_state()
        progress = self.data.daily_task_progress or {}

        tasks = []
        for task in DAILY_TASKS:
            target = int(task.get("target", 1))
            current = int(progress.get(task["id"], 0))
            tasks.append({
                "id": task["id"],
                "label": task.get("label", task["id"]),
                "target": target,
                "progress": current,
                "completed": current >= target,
            })

        all_completed = all(t["completed"] for t in tasks) if tasks else False
        return {
            "date": self.data.daily_task_date,
            "tasks": tasks,
            "all_completed": all_completed,
            "claimed": self.data.daily_task_claimed,
            "reward": dict(DAILY_TASK_REWARD),
        }

    def record_daily_task(self, task_id: str, count: int = 1):
        """记录每日任务进度"""
        self._ensure_daily_task_state()
        valid_ids = {t["id"] for t in DAILY_TASKS}
        if task_id not in valid_ids:
            return

        current = int(self.data.daily_task_progress.get(task_id, 0))
        self.data.daily_task_progress[task_id] = current + max(1, int(count))
        self.save()

    def claim_daily_task_reward(self) -> List[str]:
        """领取每日任务奖励"""
        status = self.get_daily_task_status()
        if not status["all_completed"] or status["claimed"]:
            return []

        self.data.daily_task_claimed = True
        rewards_log = self.add_reward(**DAILY_TASK_REWARD)
        return rewards_log

    # ========================================
    # 互动记录
    # ========================================

    def record_interaction(self):
        """记录互动时间"""
        self.data.last_interaction = datetime.now().isoformat()
        self.save()

    def record_chat(self) -> List[str]:
        """记录对话"""
        self.data.total_chats += 1
        # 少量 XP 奖励
        self.add_xp(1)
        self.record_interaction()
        self.record_daily_task("greet")
        return self.check_and_unlock_achievements()

    def record_feed(self, food_id: str) -> Dict[str, Any]:
        """记录喂食"""
        food = FOODS.get(food_id)
        if not food:
            return {"error": "未知食物"}

        is_new = food_id not in self.data.collected_foods
        self.data.collected_foods.add(food_id)
        self.data.feed_count += 1

        affection = food.get("affection", 5)
        mood_boost = food.get("mood_boost", 3)
        xp_gain = food.get("xp", 5) # 喂食也有经验

        self.add_reward(affection=affection, xp=xp_gain)
        self.update_mood(mood_boost)
        self.record_daily_task("feed")
        self.record_interaction()

        achievements = self.check_and_unlock_achievements()

        return {
            "food": food,
            "is_new": is_new,
            "affection_gained": affection,
            "mood_gained": mood_boost,
            "achievements": achievements,
        }

    def record_game_play(self):
        """记录游戏开始"""
        self.record_daily_task("game")

    def record_name_gen(self):
        """记录起名使用"""
        self.data.name_gen_count += 1
        self.add_affection(1)
        self.record_interaction()
        self.check_and_unlock_achievements()

    def record_prompt_draw(self):
        """记录提示卡抽取"""
        self.data.prompt_count += 1
        self.add_affection(1)
        self.record_interaction()
        self.check_and_unlock_achievements()

    def record_timer_complete(self) -> List[str]:
        """记录计时器完成"""
        self.data.timer_count += 1
        self.data.timer_streak += 1
        
        # 计时器奖励金币和经验
        self.add_reward(affection=5, xp=20, coins=10)
        self.update_mood(10)
        self.record_interaction()

        # 首次完成成就
        if self.data.timer_count == 1:
            self.unlock_achievement("timer_complete")

        return self.check_and_unlock_achievements()

    def reset_timer_streak(self):
        """重置计时器连击"""
        self.data.timer_streak = 0
        self.save()

    def record_dice_roll(self, result: int) -> bool:
        """记录骰子投掷"""
        if result == 6:
            self.data.consecutive_sixes += 1
            if self.data.consecutive_sixes >= 3:
                return self.unlock_achievement("dice_lucky")
        else:
            self.data.consecutive_sixes = 0

        self.add_affection(1)
        self.record_interaction()
        self.save()
        return False

    def record_game_win(self):
        """记录游戏胜利"""
        self.data.game_wins += 1
        # 游戏胜利奖励
        self.add_reward(affection=3, xp=15, coins=5)
        self.update_mood(5)
        self.record_interaction()
        self.check_and_unlock_achievements()

    # ========================================
    # 统计信息
    # ========================================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            created = datetime.fromisoformat(self.data.created_at)
            days = (datetime.now() - created).days
        except Exception:
            days = 0

        return {
            "affection": self.data.affection,
            "affection_level": self.get_affection_level(),
            "mood": self.data.mood,
            "mood_level": self.data.mood_level.name,
            "mood_emoji": self.get_mood_emoji(),
            "level": self.data.level,
            "xp": self.data.total_xp,
            "coins": self.data.coins, # NEW
            "days_together": days,
            "total_chats": self.data.total_chats,
            "feed_count": self.data.feed_count,
            "daily_streak": self.data.daily_streak,
            "foods_collected": len(self.data.collected_foods),
            "foods_total": len(FOODS),
            "achievements_unlocked": len(self.data.unlocked_achievements),
            "achievements_total": len(ACHIEVEMENTS),
        }

    def reset(self):
        """重置所有养成数据"""
        self.data = PetData()
        self.data.created_at = datetime.now().isoformat()
        self.save()
