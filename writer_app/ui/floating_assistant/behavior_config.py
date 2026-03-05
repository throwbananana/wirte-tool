"""
悬浮助手行为分析与反馈配置文件
"""

# 行为分析阈值
BEHAVIOR_THRESHOLDS = {
    # 心流检测
    "FLOW_CPM_ENTER": 20,       # 进入心流所需的每分钟操作数
    "FLOW_CPM_EXIT": 10,        # 退出心流的每分钟操作数阈值
    "FLOW_MIN_DURATION": 300,   # 心流结算的最短持续时间（秒）
    
    # 犹豫/卡文
    "HESITATION_GAP": 300,      # 无操作视为卡文的时间（秒）
    "IDLE_REMINDER_INTERVAL": 600, # 闲置提醒的最小间隔（秒）
    
    # 润色模式
    "REFACTOR_WINDOW": 10,      # 分析最近多少次操作
    "REFACTOR_RATIO": 0.8,      # 修改操作占比阈值
    
    # 架构师模式
    "CONTEXT_SWITCH_WINDOW": 5, # 分析最近多少次操作
    "CONTEXT_SWITCH_COUNT": 3,  # 涉及不同模块的数量
}

# 反馈文案模板 (支持随机选择)
BEHAVIOR_FEEDBACK = {
    "flow_finish": [
        "刚才的{minutes}分钟里，你的键盘都要冒烟了！这就是传说中的心流吗？",
        "好厉害！一口气专注了{minutes}分钟，这就是职业作家的气场吧！",
        "呼...刚才都不敢打扰你，{minutes}分钟的深度创作，辛苦啦！",
    ],
    "refactoring": [
        "反复推敲、精雕细琢...这一定是很重要的段落吧？",
        "修改是写作的灵魂。我也觉得这里还可以更完美！",
        "这种精益求精的态度，我很佩服哦。",
    ],
    "architect": [
        "大纲、角色、正文...你的大脑在飞速运转呢，要喝杯水吗？",
        "统筹全局的感觉很棒吧？不过也要注意脑力消耗哦。",
        "哇，感觉你在构建一个庞大的世界呢！",
    ],
    "hesitation": [
        "盯着屏幕发呆好久了...是不是卡文了？可以试试抽一张灵感卡哦。",
        "如果觉得累了，休息一下也没关系。欲速则不达嘛。",
        "唔...遇到瓶颈了吗？要不要和我聊聊思路？",
    ],
    "streak_7": [
        "连续7天创作达成！这种坚持太帅气了！",
        "一周全勤！你是最棒的！",
    ],
    "streak_30": [
        "一个月都在坚持创作，这是伟大的里程碑！",
        "连续30天的努力，我都看在眼里哦。",
    ],
    # 复合规则反馈
    "late_night_flow": [
        "夜深了，灵感却还在燃烧...要注意身体哦，我的大作家。",
        "虽然深夜效率很高，但也别忘了休息。我会一直陪着你的。",
    ],
    "weekend_warrior": [
        "周末还在这么努力地写作，这份热情一定能传达给读者的！",
        "难得的周末，把时间献给梦想的样子真迷人。",
    ],
    "high_yield_streak": [
        "不仅连续打卡，字数还这么多！你是在燃烧生命写作吗？",
        "太强了...连续的高产出，请收下我的膝盖！",
    ]
}

# 组合规则定义
# 结构: id: { conditions: [ {type, value, op} ], cooldown: "daily/weekly/once" }
# 支持的条件类型:
# - time_period: morning, afternoon, night, midnight
# - weekday: 0-6 (0=Mon, 6=Sun) or "weekend"
# - behavior: flow_finish, refactoring, etc.
# - stat_streak: int (连续天数)
# - stat_today_words: int (今日字数)
COMPLEX_RULES = {
    "late_night_flow": {
        "conditions": [
            {"type": "time_period", "value": "midnight", "op": "=="},
            {"type": "behavior", "value": "flow_finish", "op": "=="},
        ],
        "reward_xp": 50,
        "mood": "worried",
        "cooldown": "daily"
    },
    "weekend_warrior": {
        "conditions": [
            {"type": "weekday", "value": "weekend", "op": "=="},
            {"type": "stat_today_words", "value": 2000, "op": ">="},
        ],
        "reward_xp": 100,
        "mood": "cheering",
        "cooldown": "daily"
    },
    "high_yield_streak": {
        "conditions": [
            {"type": "stat_streak", "value": 3, "op": ">="},
            {"type": "stat_today_words", "value": 3000, "op": ">="},
        ],
        "reward_xp": 200,
        "mood": "excited",
        "cooldown": "weekly"
    },
    "early_bird_sprint": {
        "conditions": [
            {"type": "time_period", "value": "morning", "op": "=="},
            {"type": "behavior", "value": "flow_finish", "op": "=="},
            {"type": "stat_today_words", "value": 1000, "op": ">="},
        ],
        "reward_xp": 80,
        "mood": "morning",
        "cooldown": "daily",
        "message": "一日之计在于晨！早起写作的鸟儿有虫吃，效率真高！"
    },
    "marathoner": {
        "conditions": [
            {"type": "behavior", "value": "flow_finish", "op": "=="},
            {"type": "stat_today_words", "value": 5000, "op": ">="},
        ],
        "reward_xp": 300,
        "mood": "shocked",
        "cooldown": "daily",
        "message": "单日突破5000字？！这是人类的手速吗？请收下我的膝盖！"
    }
}
