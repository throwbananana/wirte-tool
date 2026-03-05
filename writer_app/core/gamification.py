import json
import os
from pathlib import Path
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

class GamificationManager:
    """
    Manages User Level, XP, Points, and Achievements.
    """
    
    LEVEL_TITLES = [
        (1, "萌新作家"),
        (5, "签约写手"),
        (10, "全勤标兵"),
        (20, "精品作者"),
        (30, "大神作家"),
        (50, "白金大神"),
        (100, "文坛巨擘")
    ]

    ACHIEVEMENTS_DEF = [
        {"id": "first_blood", "name": "初出茅庐", "desc": "第一次开始写作 (输入文字)", "xp": 50, "icon": get_icon("leaf_one", "🌱")},
        {"id": "word_master_1k", "name": "千字积累", "desc": "总字数达到 1,000 字", "xp": 100, "icon": get_icon("document_text", "📝")},
        {"id": "word_master_10k", "name": "万字更新", "desc": "总字数达到 10,000 字", "xp": 500, "icon": get_icon("library", "📚")},
        {"id": "pomodoro_5", "name": "专注时刻", "desc": "完成 5 个番茄钟", "xp": 150, "icon": get_icon("clock", "⏰")},
        {"id": "submission_high", "name": "潜力新作", "desc": "获得一次 80 分以上的投稿评价", "xp": 300, "icon": get_icon("star", "🌟")},
        {"id": "level_5", "name": "签约达成", "desc": "等级达到 5 级", "xp": 200, "icon": get_icon("edit", "✒️")},
        {"id": "night_owl", "name": "深夜码字", "desc": "在凌晨 0-4 点进行写作", "xp": 100, "icon": get_icon("weather_moon", "🦉")},
        # 专注模式成就
        {"id": "focus_first", "name": "初入心流", "desc": "第一次使用专注模式写作超过10分钟", "xp": 80, "icon": get_icon("target", "🎯")},
        {"id": "focus_hour", "name": "专注一小时", "desc": "单次专注写作超过60分钟", "xp": 200, "icon": get_icon("timer", "⏳")},
        {"id": "focus_master", "name": "专注大师", "desc": "累计专注写作时间超过10小时", "xp": 500, "icon": get_icon("brain_circuit", "🧘")},
        {"id": "zen_explorer", "name": "沉浸探索", "desc": "使用沉浸模式写作超过30分钟", "xp": 150, "icon": get_icon("weather_moon", "🌙")},
        {"id": "focus_streak_3", "name": "连续专注", "desc": "连续3天使用专注模式", "xp": 200, "icon": get_icon("fire", "🔥")},
    ]


    def __init__(self, data_dir):
        self.data_file = Path(data_dir) / "user_stats.json"
        self.listeners = []
        self._load_data()

    def _load_data(self):
        default_data = {
            "level": 1,
            "xp": 0,
            "points": 0,  # Currency for buying skins/items (future)
            "total_words_tracked": 0,
            "pomodoros_completed": 0,
            "submissions_made": 0,
            "highest_submission_score": 0,
            "achievements": [], # List of unlocked achievement IDs
            "history": [], # Log of gains
            "daily_activity": {}, # "YYYY-MM-DD": word_count
            # 专注模式统计
            "focus_sessions": 0,          # 专注会话次数
            "focus_time_minutes": 0,      # 累计专注时间（分钟）
            "zen_time_minutes": 0,        # 累计禅模式时间（分钟）
            "longest_focus_minutes": 0,   # 最长单次专注时间
            "focus_streak_days": 0,       # 连续专注天数
            "last_focus_date": "",        # 上次专注日期
            "daily_focus": {}             # "YYYY-MM-DD": focus_minutes
        }
        
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                    # Merge defaults
                    for k, v in default_data.items():
                        if k not in self.data:
                            self.data[k] = v
            except (json.JSONDecodeError, IOError, KeyError) as e:
                print(f"Warning: Failed to load gamification data: {e}")
                self.data = default_data
        else:
            self.data = default_data

    def save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Failed to save gamification data: {e}")

    def add_listener(self, callback):
        """Callback(event_type, data)"""
        self.listeners.append(callback)

    def _notify(self, event_type, message=None):
        for cb in self.listeners:
            cb(event_type, {"level": self.data["level"], "xp": self.data["xp"], "points": self.data["points"], "msg": message})

    def get_stats(self):
        return self.data
    
    def get_achievements_status(self):
        """Return list of {def, unlocked(bool), date}"""
        status = []
        unlocked_set = set(self.data.get("achievements", []))
        for ach in self.ACHIEVEMENTS_DEF:
            status.append({
                "id": ach["id"],
                "name": ach["name"],
                "desc": ach["desc"],
                "icon": ach["icon"],
                "xp_reward": ach["xp"],
                "unlocked": ach["id"] in unlocked_set
            })
        return status

    def check_achievements(self, trigger_type, value=None):
        unlocked_ids = set(self.data.get("achievements", []))
        new_unlocks = []

        # Helper to unlock
        def unlock(aid):
            if aid not in unlocked_ids:
                unlocked_ids.add(aid)
                self.data["achievements"].append(aid)
                # Find def
                defi = next((a for a in self.ACHIEVEMENTS_DEF if a["id"] == aid), None)
                if defi:
                    self.add_xp(defi["xp"], f"成就解锁: {defi['name']}")
                    new_unlocks.append(defi)

        # Logic
        if trigger_type == "word_count":
            if self.data["total_words_tracked"] > 0:
                unlock("first_blood")
            if self.data["total_words_tracked"] >= 1000:
                unlock("word_master_1k")
            if self.data["total_words_tracked"] >= 10000:
                unlock("word_master_10k")
                
            # Night owl check
            import datetime
            now_hour = datetime.datetime.now().hour
            if 0 <= now_hour < 4:
                unlock("night_owl")

        elif trigger_type == "pomodoro":
            if self.data["pomodoros_completed"] >= 5:
                unlock("pomodoro_5")
        
        elif trigger_type == "submission":
            if value and value >= 80:
                unlock("submission_high")
        
        elif trigger_type == "level":
            if self.data["level"] >= 5:
                unlock("level_5")

        elif trigger_type == "focus":
            # value = {"minutes": int, "is_zen": bool}
            if value:
                minutes = value.get("minutes", 0)
                is_zen = value.get("is_zen", False)

                # 初入心流：首次专注超过10分钟
                if minutes >= 10:
                    unlock("focus_first")

                # 专注一小时：单次超过60分钟
                if minutes >= 60:
                    unlock("focus_hour")

                # 专注大师：累计超过10小时（600分钟）
                if self.data.get("focus_time_minutes", 0) >= 600:
                    unlock("focus_master")

                # 沉浸探索：禅模式超过30分钟
                if is_zen and minutes >= 30:
                    unlock("zen_explorer")

                # 连续专注：连续3天
                if self.data.get("focus_streak_days", 0) >= 3:
                    unlock("focus_streak_3")

        if new_unlocks:
            self.save()
            # Notify for each (or summary)
            for u in new_unlocks:
                self._notify("achievement", f"🏆 解锁成就: {u['name']}")

    def get_current_title(self):
        lvl = self.data["level"]
        current = "文字爱好者"
        for req_lvl, title in self.LEVEL_TITLES:
            if lvl >= req_lvl:
                current = title
            else:
                break
        return current

    def get_next_level_xp(self):
        # Formula: Level^2 * 100
        return self.data["level"] ** 2 * 100

    def add_xp(self, amount, source=""):
        self.data["xp"] += amount
        self.data["points"] += amount # 1 XP = 1 Point usually
        
        # Log
        self.data["history"].append({
            "source": source,
            "amount": amount,
            "timestamp": str(os.path.getmtime(self.data_file) if self.data_file.exists() else 0)
        })
        
        # Check Level Up
        leveled_up = False
        while self.data["xp"] >= self.get_next_level_xp():
            self.data["xp"] -= self.get_next_level_xp()
            self.data["level"] += 1
            leveled_up = True
        
        self.save()
        
        if leveled_up:
            self._notify("levelup", f"恭喜升级！当前等级: Lv.{self.data['level']} {self.get_current_title()}")
            self.check_achievements("level") # Check level based achievements
        else:
            self._notify("gain", f"+{amount} 积分 ({source})")

    def record_pomodoro(self):
        self.data["pomodoros_completed"] += 1
        self.add_xp(50, "完成番茄钟")
        self.check_achievements("pomodoro")

    def record_words(self, count):
        # Prevent spamming: only call this for chunks (e.g. +100 words)
        if count > 0:
            import datetime
            today = datetime.date.today().isoformat()
            if "daily_activity" not in self.data:
                self.data["daily_activity"] = {}
            
            self.data["daily_activity"][today] = self.data["daily_activity"].get(today, 0) + count
            
            points = int(count / 10) # 10 words = 1 point
            if points > 0:
                self.data["total_words_tracked"] += count
                self.add_xp(points, f"码字 {count}")
                self.check_achievements("word_count")

    def record_submission(self, score, feedback_summary):
        self.data["submissions_made"] += 1
        if score > self.data["highest_submission_score"]:
            self.data["highest_submission_score"] = score

        # Formula: Base 100 + Score * 5
        reward = 100 + (score * 5)
        self.add_xp(reward, f"投稿评级: {score}分")
        self.check_achievements("submission", score)

    def record_focus_session(self, duration_seconds: float, is_zen_mode: bool = False):
        """
        记录专注会话

        Args:
            duration_seconds: 专注时长（秒）
            is_zen_mode: 是否为禅模式（沉浸模式）
        """
        import datetime

        if duration_seconds < 60:  # 少于1分钟不计入
            return

        minutes = int(duration_seconds / 60)
        today = datetime.date.today().isoformat()

        # 更新统计数据
        self.data["focus_sessions"] += 1
        self.data["focus_time_minutes"] += minutes

        if is_zen_mode:
            self.data["zen_time_minutes"] += minutes

        # 更新最长单次专注时间
        if minutes > self.data.get("longest_focus_minutes", 0):
            self.data["longest_focus_minutes"] = minutes

        # 更新每日专注数据
        if "daily_focus" not in self.data:
            self.data["daily_focus"] = {}
        self.data["daily_focus"][today] = self.data["daily_focus"].get(today, 0) + minutes

        # 更新连续专注天数
        last_date = self.data.get("last_focus_date", "")
        if last_date:
            try:
                last = datetime.date.fromisoformat(last_date)
                diff = (datetime.date.today() - last).days
                if diff == 1:
                    # 连续
                    self.data["focus_streak_days"] += 1
                elif diff > 1:
                    # 断了
                    self.data["focus_streak_days"] = 1
                # diff == 0 表示今天已经记录过，不变
            except ValueError:
                self.data["focus_streak_days"] = 1
        else:
            self.data["focus_streak_days"] = 1

        self.data["last_focus_date"] = today

        # 计算积分：每5分钟专注=10积分
        xp_gain = (minutes // 5) * 10
        if xp_gain > 0:
            mode_name = "沉浸模式" if is_zen_mode else "专注模式"
            self.add_xp(xp_gain, f"{mode_name}写作 {minutes}分钟")

        # 检查成就
        self.check_achievements("focus", {"minutes": minutes, "is_zen": is_zen_mode})

        self.save()
        self._notify("focus", f"专注写作 {minutes} 分钟，获得 {xp_gain} 积分")

    def get_focus_stats(self):
        """获取专注模式统计数据"""
        return {
            "sessions": self.data.get("focus_sessions", 0),
            "total_minutes": self.data.get("focus_time_minutes", 0),
            "zen_minutes": self.data.get("zen_time_minutes", 0),
            "longest_minutes": self.data.get("longest_focus_minutes", 0),
            "streak_days": self.data.get("focus_streak_days", 0),
            "daily_focus": self.data.get("daily_focus", {})
        }