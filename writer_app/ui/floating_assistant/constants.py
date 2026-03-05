"""
悬浮写作助手 - 常量定义模块
包含名字库、写作提示、成就、食物等静态数据
"""
import json
from pathlib import Path
from typing import Dict, List, Any
from writer_app.core.icon_manager import IconManager

# Helper to get icon
def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

# 角色基本信息
ASSISTANT_NAME = "神本朝奈"

# ============================================================
# 名字库数据
# ============================================================

# 中文姓氏
CHINESE_SURNAMES = [
    "李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
    "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧",
    "程", "曹", "袁", "邓", "许", "傅", "沈", "曾", "彭", "吕",
    "苏", "卢", "蒋", "蔡", "贾", "丁", "魏", "薛", "叶", "阎",
    "余", "潘", "杜", "戴", "夏", "钟", "汪", "田", "任", "姜",
    "范", "方", "石", "姚", "谭", "廖", "邹", "熊", "金", "陆",
    "郝", "孔", "白", "崔", "康", "毛", "邱", "秦", "江", "史",
    "顾", "侯", "邵", "孟", "龙", "万", "段", "漕", "钱", "汤",
    "尹", "黎", "易", "常", "武", "乔", "贺", "赖", "龚", "文"
]

# 中文名（男性倾向）
CHINESE_NAMES_MALE = [
    "伟", "强", "磊", "军", "勇", "杰", "涛", "明", "超", "华",
    "浩", "然", "宇", "轩", "辰", "睿", "博", "文", "志", "俊",
    "鹏", "飞", "龙", "天", "逸", "晨", "阳", "旭", "泽", "昊",
    "霖", "皓", "瑞", "宸", "铭", "航", "毅", "恒", "峰", "嘉",
    "晟", "煜", "彦", "翰", "墨", "言", "风", "霆", "寒", "萧"
]

# 中文名（女性倾向）
CHINESE_NAMES_FEMALE = [
    "芳", "娟", "敏", "静", "丽", "艳", "燕", "红", "玲", "霞",
    "雪", "萍", "婷", "梅", "琳", "露", "洁", "莹", "蕾", "薇",
    "妍", "瑶", "琪", "璇", "诗", "梦", "欣", "怡", "涵", "雅",
    "晴", "柔", "蓉", "颖", "珊", "倩", "悦", "菲", "瑾", "萱",
    "婉", "清", "韵", "澜", "黛", "凝", "舒", "灵", "若", "曦"
]

# 英文名
ENGLISH_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark",
    "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George",
    "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob",
    "Alexander", "Benjamin", "Nicholas", "Samuel", "Henry", "Oliver", "Leo",
    "Ethan", "Lucas", "Mason", "Logan", "Jack", "Aiden", "Owen", "Dylan"
]

ENGLISH_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Kimberly", "Emily", "Donna", "Michelle", "Dorothy", "Carol",
    "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura",
    "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
    "Harper", "Evelyn", "Abigail", "Ella", "Scarlett", "Grace", "Chloe", "Luna"
]

ENGLISH_SURNAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
    "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera"
]

# 日式名字
JAPANESE_SURNAMES = [
    "佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤",
    "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "林", "斎藤", "清水",
    "山崎", "森", "池田", "橋本", "阿部", "石川", "山下", "中島", "石井", "小川",
    "前田", "岡田", "長谷川", "藤田", "後藤", "近藤", "村上", "遠藤", "青木", "坂本"
]

JAPANESE_NAMES_MALE = [
    "太郎", "一郎", "健太", "翔太", "大輝", "拓海", "蓮", "悠真", "陽翔", "樹",
    "颯太", "蒼", "陸", "悠", "翼", "海斗", "翔", "颯", "大和", "陽太",
    "隼人", "瑛太", "優斗", "駿", "晴", "遼", "奏", "匠", "航", "歩"
]

JAPANESE_NAMES_FEMALE = [
    "花子", "愛", "美咲", "桜", "結衣", "葵", "陽菜", "凛", "さくら", "芽依",
    "莉子", "結菜", "楓", "琴音", "美月", "心春", "咲良", "杏", "彩葉", "真央",
    "結愛", "美優", "心結", "詩織", "菜々子", "陽向", "優花", "紗良", "美桜", "心音"
]

# 奇幻/武侠名字元素
FANTASY_PREFIXES = [
    "苍", "玄", "紫", "青", "赤", "白", "黑", "金", "银", "碧",
    "幽", "冥", "灵", "神", "魔", "妖", "仙", "圣", "暗", "光"
]
FANTASY_ELEMENTS = [
    "龙", "凤", "麟", "虎", "鹤", "狼", "鹰", "蛇", "雷", "风",
    "火", "水", "冰", "雪", "云", "月", "星", "剑", "刃", "影"
]
FANTASY_SUFFIXES = [
    "天", "尘", "羽", "心", "魂", "血", "骨", "眼", "手", "歌",
    "舞", "笑", "泪", "痕", "殇", "无极", "千秋", "万里", "九霄", "三生"
]

# ============================================================
# 写作提示卡
# ============================================================

WRITING_PROMPTS = [
    # 场景类
    "描写一个雨夜的街角咖啡店",
    "写一段黄昏时分的海边对话",
    "描绘一个被遗忘的旧书店",
    "写一个发生在电梯里的偶遇",
    "描写深夜便利店里的故事",
    "写一段发生在医院走廊的对话",
    "描绘一个热闹的夜市场景",
    "写一个空无一人的游乐场",
    "描写一座古老的钟楼",
    "写一个隐藏在城市角落的秘密花园",

    # 情感类
    "写一段关于等待的内心独白",
    "描写重逢时的复杂情绪",
    "写一封永远不会寄出的信",
    "描写告别时说不出口的话",
    "写一段关于遗憾的回忆",
    "描写暗恋者的心理活动",
    "写一个关于原谅的故事",
    "描写失去后的领悟",
    "写一段关于成长的感悟",
    "描写久别重逢后的陌生感",

    # 人物类
    "写一个有秘密的老人",
    "描写一个假装坚强的人",
    "写一个性格反差巨大的角色",
    "描写一个说谎成性的人的内心",
    "写一个总是微笑的悲伤者",
    "描写一个外表冷漠内心温暖的人",
    "写一个正在改变的反派",
    "描写一个平凡人的英雄时刻",
    "写一个失去记忆的人",
    "描写一个守护秘密的孩子",

    # 对话类
    "写一段充满潜台词的对话",
    "写两个陌生人在车站的交谈",
    "写一段父子/母女间的和解对话",
    "写一段通过电话进行的争吵",
    "写两个老朋友多年后的对话",
    "写一段师徒之间的教诲",
    "写一段情侣间的误会对话",
    "写一段充满暗示的商业谈判",
    "写两个对手之间的尊重对话",
    "写一段跨越时空的对话",

    # 开头类
    "用一个意外开始你的故事",
    "从一封神秘的信开始",
    "用一个梦境作为开头",
    "从一件丢失的物品开始",
    "用一个谎言开始你的故事",
    "从一次失败开始讲述",
    "用一个声音作为故事的开端",
    "从一个承诺开始",
    "用一个预言开启故事",
    "从一张旧照片开始",

    # 挑战类
    "用100字讲述一个完整的故事",
    "只用对话推进一个场景",
    "不使用'说'字写一段对话",
    "用第二人称写一段内心独白",
    "用五感描写一个场景",
    "倒叙讲述一个故事",
    "用书信体讲述一段关系",
    "用意识流写一段心理活动",
    "用极简主义风格写一个故事",
    "用多视角讲述同一事件",
]

# 闲聊话题（无AI模式）
IDLE_CHAT_TOPICS = [
    "今天写了多少字呢？记得适当休息哦~",
    "有没有遇到卡文的地方？试试换个角度思考",
    "主人的故事进展得怎么样了？",
    "要不要来抽一张写作提示卡？",
    "灵感枯竭的话，出去散散步也不错呢",
    "记得保存文件！Ctrl+S！",
    "今天的天气适合写什么类型的故事呢？",
    "角色们在你的脑海里说了什么有趣的话吗？",
    "有没有为难以命名的角色而苦恼？试试起名工具~",
    "写累了就休息一下，我会一直在这里的",
    "要来玩个小游戏放松一下吗？",
    "突然想到：你最喜欢自己笔下的哪个角色？",
    "有没有哪个情节让你自己都感动了？",
    "今天有没有什么有趣的灵感闪过？",
    "记得喝水！创作也要照顾好身体~",
    "写作时听音乐会更有灵感吗？",
    "最近有看什么好书吗？分享给我听听~",
    "今天的目标字数完成了吗？",
    "有没有想过给故事画个插图？",
    "主人最近的写作状态怎么样？"
]

# ============================================================
# 成就系统
# ============================================================

ACHIEVEMENTS = {
    # 基础成就
    "first_chat": {"name": "初次相遇", "desc": f"第一次和{ASSISTANT_NAME}对话", "icon": get_icon("chat", "🎉"), "xp": 10},
    "chat_100": {"name": "话痨", "desc": "累计对话100次", "icon": get_icon("chat_bubbles", "💬"), "xp": 50},
    "chat_500": {"name": "知心好友", "desc": "累计对话500次", "icon": get_icon("heart", "💕"), "xp": 100},

    # 喂食成就
    "feed_10": {"name": "小小投喂者", "desc": "累计喂食10次", "icon": get_icon("food_cookie", "🍪"), "xp": 20},
    "feed_50": {"name": "资深饲养员", "desc": "累计喂食50次", "icon": get_icon("food_cake", "🍰"), "xp": 50},
    "feed_100": {"name": "美食大师", "desc": "累计喂食100次", "icon": get_icon("food_pizza", "👨‍🍳"), "xp": 100},

    # 工具成就
    "name_gen_10": {"name": "起名达人", "desc": "使用起名工具10次", "icon": get_icon("rename", "📝"), "xp": 20},
    "name_gen_50": {"name": "命名大师", "desc": "使用起名工具50次", "icon": get_icon("edit", "✒️"), "xp": 50},
    "prompt_20": {"name": "灵感收集者", "desc": "抽取20张提示卡", "icon": get_icon("lightbulb", "💡"), "xp": 30},
    "prompt_100": {"name": "灵感宝库", "desc": "抽取100张提示卡", "icon": get_icon("star", "🌟"), "xp": 80},
    "dice_lucky": {"name": "幸运儿", "desc": "骰子连续3次掷出6", "icon": get_icon("games", "🎲"), "xp": 50},
    "module_newbie": {"name": "新手入门", "desc": "熟悉4个以上模块", "icon": get_icon("book_open", "??"), "xp": 30},
    "module_explorer": {"name": "模块探索者", "desc": "体验8个以上模块", "icon": get_icon("library", "??"), "xp": 60},
    "type_explorer": {"name": "题材初探", "desc": "尝试2种不同的项目类型", "icon": get_icon("compass", "??"), "xp": 30},
    "type_collector": {"name": "题材旅人", "desc": "尝试4种不同的项目类型", "icon": get_icon("map", "??"), "xp": 60},
    "type_master": {"name": "题材全开", "desc": "尝试6种不同的项目类型", "icon": get_icon("trophy", "??"), "xp": 120},
    "theme_explorer": {"name": "主题采风", "desc": "使用3个以上创作标签", "icon": get_icon("tag", "??"), "xp": 20},
    "theme_collector": {"name": "主题收集者", "desc": "使用6个以上创作标签", "icon": get_icon("collections", "??"), "xp": 50},
    "theme_master": {"name": "主题开拓者", "desc": "使用10个以上创作标签", "icon": get_icon("flag", "??"), "xp": 100},

    # 计时器成就
    "timer_complete": {"name": "专注达人", "desc": "完成一次番茄钟", "icon": get_icon("timer", "🍅"), "xp": 15},
    "timer_10": {"name": "时间管理者", "desc": "完成10次番茄钟", "icon": get_icon("clock", "⏰"), "xp": 50},
    "timer_streak": {"name": "专注大师", "desc": "连续完成3个番茄钟", "icon": get_icon("fire", "🔥"), "xp": 80},

    # 好感度成就
    "affection_50": {"name": "初见好感", "desc": "关系变得更熟悉", "icon": get_icon("heart", "💕"), "xp": 30},
    "affection_100": {"name": "亲密伙伴", "desc": "关系愈发亲近", "icon": get_icon("heart_circle", "❤️"), "xp": 50},
    "affection_200": {"name": "挚友", "desc": "关系更加深厚", "icon": get_icon("heart_pulse", "💖"), "xp": 80},
    "affection_500": {"name": "灵魂伴侣", "desc": "关系亲密无间", "icon": get_icon("heart", "💞"), "xp": 150},

    # 收集成就
    "collect_all_food": {"name": "美食收藏家", "desc": "收集所有食物", "icon": get_icon("trophy", "🏆"), "xp": 100},

    # 时间成就
    "night_owl": {"name": "夜猫子", "desc": "凌晨2点还在写作", "icon": get_icon("weather_moon", "🦉"), "xp": 20},
    "early_bird": {"name": "早起鸟", "desc": "早上6点就开始写作", "icon": get_icon("weather_sunny", "🐦"), "xp": 20},
    "weekend_writer": {"name": "周末作家", "desc": "周末连续写作2小时", "icon": get_icon("calendar_work_week", "📚"), "xp": 30},

    # 相册成就
    "first_photo": {"name": "初次留影", "desc": f"第一次拍摄{ASSISTANT_NAME}立绘", "icon": get_icon("camera", "📸"), "xp": 10},
    "photo_collector": {"name": "摄影爱好者", "desc": "收集10张照片", "icon": get_icon("image_copy", "📷"), "xp": 30},
    "diverse_collector": {"name": "多样收藏家", "desc": "收集10种不同状态的照片", "icon": get_icon("color", "🎨"), "xp": 50},
    "master_collector": {"name": "终极收藏家", "desc": "收集20种不同状态的照片", "icon": get_icon("crown", "👑"), "xp": 100},
    "festival_master": {"name": "节日达人", "desc": "收集所有节日立绘", "icon": get_icon("gift", "🎊"), "xp": 80},
    "costume_master": {"name": "换装达人", "desc": "收集所有服装立绘", "icon": get_icon("t_shirt", "👗"), "xp": 80},
    "season_master": {"name": "四季收藏", "desc": "收集所有季节立绘", "icon": get_icon("weather_rain", "🌈"), "xp": 60},

    # 写作相关成就
    "word_1000": {"name": "千字作者", "desc": "项目字数达到1000", "icon": get_icon("document_text", "📖"), "xp": 20},
    "word_10000": {"name": "万字作家", "desc": "项目字数达到10000", "icon": get_icon("library", "📚"), "xp": 50},
    "word_50000": {"name": "长篇作者", "desc": "项目字数达到50000", "icon": get_icon("book", "📕"), "xp": 100},

    # 连续使用成就
    "daily_streak_7": {"name": "一周坚持", "desc": f"连续7天使用{ASSISTANT_NAME}", "icon": get_icon("calendar_week", "🗓️"), "xp": 50},
    "daily_streak_30": {"name": "月度坚持", "desc": f"连续30天使用{ASSISTANT_NAME}", "icon": get_icon("calendar_month", "📅"), "xp": 150},

    # 小游戏成就
    "game_winner": {"name": "游戏高手", "desc": "在小游戏中获胜10次", "icon": get_icon("games", "🎮"), "xp": 40},

    # 学校事件成就
    "shared_lunch": {"name": "午餐时光", "desc": f"和{ASSISTANT_NAME}分享午餐", "icon": get_icon("food_bowl", "🍱"), "xp": 30},

    # 传说食物成就
    "legendary_food": {"name": "珍馐美味", "desc": "喂食传说级食物", "icon": get_icon("star", "🌟"), "xp": 100},

    # 节日与纪念日成就
    "birthday": {"name": "生日快乐", "desc": f"在5月9日和{ASSISTANT_NAME}一起庆祝生日", "icon": get_icon("food_cake", "🎂"), "xp": 100},
    "anniversary": {"name": "相识周年", "desc": "纪念建立连接的一周年", "icon": get_icon("gift", "💍"), "xp": 200},
}

# ============================================================
# 食物数据
# ============================================================

FOODS = {
    # 普通食物
    "cookie": {"name": "曲奇", "icon": get_icon("food_cookie", "🍪"), "affection": 5, "rarity": "common", "mood_boost": 3},
    "cake": {"name": "蛋糕", "icon": get_icon("food_cake", "🍰"), "affection": 10, "rarity": "common", "mood_boost": 5},
    "candy": {"name": "糖果", "icon": get_icon("food_candy", "🍬"), "affection": 3, "rarity": "common", "mood_boost": 2},
    "chocolate": {"name": "巧克力", "icon": get_icon("food_chocolate", "🍫"), "affection": 8, "rarity": "common", "mood_boost": 6},
    "donut": {"name": "甜甜圈", "icon": get_icon("food_donut", "🍩"), "affection": 7, "rarity": "common", "mood_boost": 4},
    "icecream": {"name": "冰淇淋", "icon": get_icon("food_icecream", "🍦"), "affection": 6, "rarity": "common", "mood_boost": 5},
    "coffee": {"name": "咖啡", "icon": get_icon("drink_coffee", "☕"), "affection": 5, "rarity": "common", "mood_boost": 3},
    "tea": {"name": "奶茶", "icon": get_icon("drink_tea", "🧋"), "affection": 6, "rarity": "common", "mood_boost": 4},
    "bread": {"name": "面包", "icon": get_icon("food_bread", "🍞"), "affection": 4, "rarity": "common", "mood_boost": 2},
    "apple": {"name": "苹果", "icon": get_icon("food_apple", "🍎"), "affection": 4, "rarity": "common", "mood_boost": 3},

    # 稀有食物
    "pizza": {"name": "披萨", "icon": get_icon("food_pizza", "🍕"), "affection": 12, "rarity": "rare", "mood_boost": 8},
    "sushi": {"name": "寿司", "icon": get_icon("food_sushi", "🍣"), "affection": 15, "rarity": "rare", "mood_boost": 10},
    "burger": {"name": "汉堡", "icon": get_icon("food_burger", "🍔"), "affection": 10, "rarity": "rare", "mood_boost": 7},
    "ramen": {"name": "拉面", "icon": get_icon("food_bowl", "🍜"), "affection": 12, "rarity": "rare", "mood_boost": 9},
    "steak": {"name": "牛排", "icon": get_icon("food_steak", "🥩"), "affection": 18, "rarity": "rare", "mood_boost": 12},
    "pasta": {"name": "意面", "icon": get_icon("food_spaghetti", "🍝"), "affection": 14, "rarity": "rare", "mood_boost": 10},
    "takoyaki": {"name": "章鱼烧", "icon": get_icon("food", "🐙"), "affection": 13, "rarity": "rare", "mood_boost": 9},

    # 传说食物
    "golden_apple": {"name": "金苹果", "icon": get_icon("food_apple", "🍎"), "affection": 30, "rarity": "legendary", "mood_boost": 20},
    "star_candy": {"name": "星星糖", "icon": get_icon("star", "⭐"), "affection": 25, "rarity": "legendary", "mood_boost": 18},
    "rainbow_cake": {"name": "彩虹蛋糕", "icon": get_icon("food_cake", "🌈"), "affection": 50, "rarity": "legendary", "mood_boost": 30},
    "moon_cake": {"name": "仙月饼", "icon": get_icon("food_cake", "🥮"), "affection": 35, "rarity": "legendary", "mood_boost": 25},
    "dragon_fruit": {"name": "龙之果", "icon": get_icon("food_apple", "🐲"), "affection": 40, "rarity": "legendary", "mood_boost": 28},
}

# ============================================================
# 情绪关键词
# ============================================================

EMOTION_KEYWORDS = {
    "happy": ["开心", "高兴", "快乐", "棒", "太好了", "哈哈", "嘻嘻", "耶", "好耶",
              "感谢", "谢谢", "爱你", "喜欢", "赞", "厉害", "完美", "nice", "great", "good",
              "wonderful", "amazing", "awesome", "excellent"],
    "sad": ["难过", "伤心", "悲伤", "郁闷", "失落", "唉", "呜呜", "哭", "泪", "惨",
            "糟糕", "倒霉", "不好", "失败", "放弃", "累了", "算了", "沮丧", "心痛"],
    "excited": ["太棒了", "激动", "兴奋", "期待", "迫不及待", "终于", "成功了",
                "冲", "加油", "干劲", "燃", "爆", "狂喜", "wow", "yay"],
    "shy": ["害羞", "不好意思", "羞", "脸红", "嘿嘿", "emmm", "这个嘛", "人家",
            "羞涩", "腼腆"],
    "angry": ["生气", "愤怒", "烦", "讨厌", "可恶", "气死", "离谱", "过分", "啊啊啊",
              "恼火", "怒", "火大"],
    "surprised": ["惊讶", "天哪", "什么", "居然", "竟然", "没想到", "意外", "wow",
                  "卧槽", "我靠", "厉害了", "震惊", "不敢相信", "天呐"],
    "curious": ["好奇", "为什么", "怎么", "是什么", "告诉我", "想知道", "求问",
                "请问", "疑问", "不懂", "解释", "想了解"],
    "love": ["爱", "❤", "心", "喜欢你", "最喜欢", "宝贝", "亲爱的", "超爱", "mua",
             "爱死了", "心动", "喜欢"],
    "worried": ["担心", "焦虑", "紧张", "害怕", "怎么办", "完了", "慌", "不安", "忧虑",
                "恐惧", "担忧"]
}

# AI响应情绪识别关键词
AI_EMOTION_KEYWORDS = {
    "happy": ["很高兴", "开心", "恭喜", "太棒了", "不错", "很好", "赞", "祝贺"],
    "cheering": ["加油", "相信你", "一定可以", "继续努力", "坚持", "fighting", "支持你"],
    "curious": ["有趣", "想了解", "好奇", "这个问题", "让我想想"],
    "success": ["完成", "搞定", "成功", "解决了", "好了", "做到了"],
    "worried": ["注意", "小心", "建议", "可能需要", "担心", "需要注意"],
    "love": ["喜欢", "感谢", "感动", "温暖", "谢谢"]
}

# ============================================================
# 快捷提示词
# ============================================================

QUICK_PROMPTS_AI = [
    ("润色", "请帮我润色以下文字，使其更加流畅优美："),
    ("续写", "请根据以下内容继续创作："),
    ("扩写", "请帮我扩展以下段落，增加更多细节："),
    ("缩写", "请帮我精简以下内容，保留核心信息："),
    ("改写", "请用不同的方式重新表达以下内容："),
    ("起名", "请为以下场景/角色起几个合适的名字："),
    ("对话", "请帮我写一段对话，场景是："),
    ("描写", "请帮我写一段描写："),
    ("分析", "请帮我分析以下文字的优缺点："),
    ("建议", "请针对以下内容给出写作建议："),
]

# 无AI模式的快捷工具
QUICK_TOOLS = [
    ("起名", "name_generator"),
    ("提示卡", "prompt_card"),
    ("骰子", "dice"),
    ("计时", "timer"),
    ("统计", "word_count"),
    ("笔记", "quick_note"),
    ("角色卡", "character_card"),
    ("场景", "scene_generator"),
    ("环境音", "ambiance"),
    ("打字音", "typewriter"),
]

# ============================================================
# 角色模板
# ============================================================

CHARACTER_TEMPLATES = {
    "protagonist": {
        "name": "主角模板",
        "fields": ["姓名", "年龄", "性别", "外貌", "性格", "背景", "目标", "弱点", "特长"]
    },
    "antagonist": {
        "name": "反派模板",
        "fields": ["姓名", "年龄", "性别", "外貌", "性格", "动机", "手段", "弱点", "与主角关系"]
    },
    "supporting": {
        "name": "配角模板",
        "fields": ["姓名", "年龄", "性别", "外貌", "性格", "与主角关系", "作用"]
    },
    "fantasy": {
        "name": "奇幻角色模板",
        "fields": ["姓名", "种族", "年龄", "外貌", "能力", "性格", "背景", "阵营"]
    }
}

# 场景模板
SCENE_TEMPLATES = {
    "indoor": ["咖啡馆", "图书馆", "教室", "办公室", "卧室", "餐厅", "医院", "车站", "电梯", "地下室"],
    "outdoor": ["公园", "海滩", "森林", "山顶", "街道", "广场", "屋顶", "桥上", "湖边", "花园"],
    "fantasy": ["古堡", "魔法塔", "地下城", "浮空岛", "神殿", "龙巢", "精灵森林", "矮人矿洞"],
    "scifi": ["宇宙飞船", "空间站", "殖民地", "实验室", "虚拟世界", "废墟城市", "地下避难所"]
}

# ============================================================
# 辅助函数
# ============================================================

def load_custom_prompts(config_dir: Path) -> List[str]:
    """从配置目录加载自定义写作提示"""
    custom_file = config_dir / "custom_prompts.json"
    if custom_file.exists():
        try:
            with open(custom_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_custom_prompts(config_dir: Path, prompts: List[str]) -> bool:
    """保存自定义写作提示"""
    custom_file = config_dir / "custom_prompts.json"
    try:
        with open(custom_file, "w", encoding="utf-8") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def get_all_prompts(config_dir: Path = None) -> List[str]:
    """获取所有写作提示（内置+自定义）"""
    prompts = WRITING_PROMPTS.copy()
    if config_dir:
        prompts.extend(load_custom_prompts(config_dir))
    return prompts