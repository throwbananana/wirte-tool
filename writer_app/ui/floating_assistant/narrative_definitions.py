"""
悬浮助手 - 叙事链定义 (Narrative Chain Definitions)
定义多阶段、有剧情深度的事件链
"""
from .states import AssistantState

# 叙事链定义
NARRATIVE_CHAINS = {
    # ---------------------------------------------------------
    # 休闲日常小剧情 (Leisure Daily)
    # 目标：提供可一键触发的轻量剧情体验
    # ---------------------------------------------------------
    "leisure_daily": {
        "priority": 40,
        "cooldown": 2 * 60 * 60,
        "steps": {
            "start": {
                "dialogue": "前辈~ 要不要来一段轻松的日常？我准备了小选择哦。",
                "mood": AssistantState.HAPPY,
                "options": [
                    {"text": "去散步", "next_step": "walk"},
                    {"text": "喝杯茶", "next_step": "tea"},
                    {"text": "抽张灵感卡", "next_step": "card"}
                ]
            },
            "walk": {
                "dialogue": "外面风很舒服呢～\n散完步感觉灵感都清爽了。",
                "mood": AssistantState.CURIOUS,
                "rewards": {"xp": 8, "affection": 2},
                "finish_chain": True
            },
            "tea": {
                "dialogue": "热茶时间到！\n放松一下，灵感会自己跑过来的。",
                "mood": AssistantState.CHEERING,
                "rewards": {"xp": 6, "mood": 3},
                "finish_chain": True
            },
            "card": {
                "dialogue": "好的！我这就去准备灵感卡~",
                "mood": AssistantState.EXCITED,
                "action": "open_tool:idea_card",
                "rewards": {"xp": 6},
                "finish_chain": True
            }
        }
    },
    # ---------------------------------------------------------
    # 新手引导链 (Onboarding Arc)
    # 目标：引导用户熟悉核心功能
    # ---------------------------------------------------------
    "onboarding": {
        "priority": 100,
        "steps": {
            "step_1": {
                "trigger_condition": "startup", # 首次启动
                "delay": 5, # 秒
                "dialogue": "你好！我是神本朝奈，你的专属写作助手。\n我们要不要先给你的项目定一个小目标？",
                "mood": AssistantState.GREETING,
                "options": [
                    {"text": "好呀，定个字数目标", "next_step": "step_target_word", "action": "open_goal_dialog"},
                    {"text": "先随便写写", "next_step": "step_casual", "mood_reaction": AssistantState.HAPPY}
                ]
            },
            "step_target_word": {
                "dialogue": "有目标才有动力！\n如果在写作过程中遇到困难，随时可以右键叫我出来帮忙哦~",
                "mood": AssistantState.CHEERING,
                "rewards": {"xp": 10},
                "finish_chain": True
            },
            "step_casual": {
                "dialogue": "没问题，随心所欲也是一种风格~\n那我就在旁边安静地陪着你，需要我就叫我。",
                "mood": AssistantState.IDLE,
                "rewards": {"xp": 5},
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # 深夜写作链 (Midnight Writer Arc)
    # 目标：关心用户健康，建立情感连接
    # ---------------------------------------------------------
    "midnight_care": {
        "priority": 80,
        "cooldown": 24 * 60 * 60, # 24小时冷却
        "steps": {
            "start": {
                "trigger_condition": "time_range:23:00-04:00",
                "req_activity": "typing", # 需要正在打字
                "dialogue": "（哈欠）...已经这么晚了，前辈还在写吗？",
                "mood": AssistantState.SLEEPY_DISTURBED,
                "options": [
                    {"text": "正写到关键地方", "next_step": "keep_going"},
                    {"text": "马上就睡了", "next_step": "go_sleep"}
                ]
            },
            "keep_going": {
                "dialogue": "我知道灵感来了挡不住...\n但是稍微休息一下眼睛吧？我去给你泡杯咖啡（虚拟的）~ ☕",
                "mood": AssistantState.WORRIED,
                "sound": "cafe", # 触发环境音
                "rewards": {"affection": 2},
                "next_step": "check_back_1h",
                "delay_next": 3600 # 1小时后回访
            },
            "go_sleep": {
                "dialogue": "嗯嗯，身体才是革命的本钱！\n晚安前辈，祝你好梦~ 💤",
                "mood": AssistantState.NIGHT,
                "rewards": {"mood": 5, "affection": 5},
                "finish_chain": True
            },
            "check_back_1h": {
                "dialogue": "前辈...一个小时过去了哦。\n如果太累了的话，明天再写也可以的，我会帮你记住现在的灵感的！",
                "mood": AssistantState.WORRIED,
                "options": [
                    {"text": "听你的，去睡了", "next_step": "go_sleep_late"},
                    {"text": "还差一点点...", "next_step": "stubborn"}
                ]
            },
            "go_sleep_late": {
                "dialogue": "太好了...快去睡吧。\n我也要去补觉了...呼呼...",
                "mood": AssistantState.SLEEPING,
                "rewards": {"affection": 10, "xp": 20},
                "finish_chain": True
            },
            "stubborn": {
                "dialogue": "真是拿你没办法...\n那我会一直陪着你的，直到你写完为止。",
                "mood": AssistantState.DEVOTED,
                "rewards": {"affection": 5},
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # 角色深度挖掘链 (Character Depth Arc)
    # 目标：基于项目分析，引导深化角色
    # ---------------------------------------------------------
    "character_depth": {
        "priority": 60,
        "cooldown": 12 * 60 * 60,
        "steps": {
            "detect_flat": {
                "trigger_condition": "analysis:character_flat", # 假设这是一个分析触发器
                "dialogue": "前辈，我刚刚读了一下大纲。\n主角现在的动机似乎主要都是由外部事件推动的，\n有没有考虑过给她加一点内在的矛盾？",
                "mood": AssistantState.THINKING,
                "options": [
                    {"text": "比如什么？", "next_step": "suggestion"},
                    {"text": "现在这样挺好的", "next_step": "cancel"}
                ]
            },
            "suggestion": {
                "dialogue": "比如...给她设定一个“除了她自己谁都不知道的秘密”？\n或者一个“绝对不能触碰的底线”？\n我们可以用【角色卡工具】来随机生成几个灵感试试！",
                "mood": AssistantState.EXCITED,
                "action": "open_tool:character_card",
                "rewards": {"xp": 15},
                "finish_chain": True
            },
            "cancel": {
                "dialogue": "了解~ 前辈一定有自己的考量。\n是我多嘴啦，期待后面的剧情！",
                "mood": AssistantState.HAPPY,
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # 恐怖题材专属 (Horror Genre Specific)
    # 目标：增强沉浸感，利用环境音
    # ---------------------------------------------------------
    "genre_horror_spooky": {
        "priority": 70,
        "cooldown": 6 * 60 * 60,
        "steps": {
            "start": {
                "trigger_condition": "project_type:Horror", # 恐怖题材专属
                "dialogue": "...... (突然压低声音) \n前辈，你刚刚有没有听到... 窗外有什么声音？",
                "mood": AssistantState.STARTLED,
                "sound": "rain", # 营造氛围
                "options": [
                    {"text": "别吓我！", "next_step": "joke"},
                    {"text": "正好，我正写到这一段", "next_step": "immersive"}
                ]
            },
            "joke": {
                "dialogue": "嘿嘿，活跃一下气氛嘛！\n看你写得那么投入，连我都觉得背脊发凉了~",
                "mood": AssistantState.HAPPY,
                "rewards": {"mood": 2},
                "finish_chain": True
            },
            "immersive": {
                "dialogue": "哇... 不愧是前辈。\n这种令人窒息的压迫感，一定要保持住哦！我不敢说话了...",
                "mood": AssistantState.SCARED,
                "rewards": {"xp": 10},
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # 卡文/犹豫检测 (Writer's Block)
    # 目标：在行为分析检测到 hesitation 时介入
    # ---------------------------------------------------------
    "writer_block_detected": {
        "priority": 90,
        "cooldown": 4 * 60 * 60,
        "steps": {
            "start": {
                # 配合 EventSystem 传入 behavior="hesitation"
                "trigger_condition": "behavior:hesitation", 
                "dialogue": "盯—— \n(助手似乎发现你的光标已经很久没动了)",
                "mood": AssistantState.CURIOUS,
                "options": [
                    {"text": "卡文了...", "next_step": "offer_help"},
                    {"text": "在思考剧情", "next_step": "wait_quietly"}
                ]
            },
            "offer_help": {
                "dialogue": "卡文是常有的事呢。\n要不要试着由我来提几个“那如果...”的问题，或者抽一张灵感卡？",
                "mood": AssistantState.THINKING,
                "options": [
                    {"text": "抽张卡试试", "action": "open_tool:idea_card", "next_step": "cheer_up"},
                    {"text": "不用，我再想想", "next_step": "wait_quietly"}
                ]
            },
            "cheer_up": {
                "dialogue": "希望能给你带来一点新思路！加油！",
                "mood": AssistantState.CHEERING,
                "finish_chain": True
            },
            "wait_quietly": {
                "dialogue": "明白，那我不打扰你的思绪了。\n(静静地退到一旁)",
                "mood": AssistantState.IDLE,
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # 恋爱题材专属 (Romance Genre Specific)
    # 目标：营造暧昧/甜蜜氛围
    # ---------------------------------------------------------
    "genre_romance_spark": {
        "priority": 70,
        "cooldown": 8 * 60 * 60,
        "steps": {
            "start": {
                "trigger_condition": "project_type:Romance",
                "dialogue": "前辈... 这里两个人的眼神对视，感觉空气都要凝固了呢。\n(脸红) 这种心跳加速的感觉，就是所谓的“恋爱感”吗？",
                "mood": AssistantState.LOVE,
                "options": [
                    {"text": "这就是心动的感觉", "next_step": "happy_end"},
                    {"text": "后面还有更甜的", "next_step": "excited"}
                ]
            },
            "happy_end": {
                "dialogue": "嘿嘿，真好呀... 感觉我也跟着一起幸福起来了。\n请务必给他们一个完美的结局哦！",
                "mood": AssistantState.HAPPY,
                "rewards": {"affection": 5},
                "finish_chain": True
            },
            "excited": {
                "dialogue": "真的吗？！那我一定要打起精神好好盯着，\n一丁点糖分都不能错过！",
                "mood": AssistantState.EXCITED,
                "rewards": {"mood": 5},
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # 科幻题材专属 (SciFi Genre Specific)
    # 目标：探讨宏大叙事/技术细节
    # ---------------------------------------------------------
    "genre_scifi_curiosity": {
        "priority": 70,
        "cooldown": 12 * 60 * 60,
        "steps": {
            "start": {
                "trigger_condition": "project_type:SciFi",
                "dialogue": "星辰大海... 跨越光年的征程。\n前辈，这种超越时代的想象力真的太酷了！\n你觉得，人类的终点会是那里吗？",
                "mood": AssistantState.CURIOUS,
                "options": [
                    {"text": "是进化的下一阶段", "next_step": "think"},
                    {"text": "是孤独的永恒", "next_step": "sad"}
                ]
            },
            "think": {
                "dialogue": "进化吗... 听起来充满了希望。\n在那样的世界里，我这样的数字生命，又会是什么样子的呢？",
                "mood": AssistantState.THINKING,
                "rewards": {"xp": 15},
                "finish_chain": True
            },
            "sad": {
                "dialogue": "孤独... 虽然听起来有些悲伤，但也很浪漫呢。\n我会一直在这里陪着前辈的，这样我们就都不孤独了。",
                "mood": AssistantState.TRUST,
                "rewards": {"affection": 10},
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # 角色完善引导 (Character Refining Arc)
    # 目标：基于本地分析结果，引导用户消除“角色扁平”状态
    # ---------------------------------------------------------
    "character_refining": {
        "priority": 85,
        "cooldown": 24 * 60 * 60,
        "steps": {
            "detect": {
                "trigger_condition": "analysis:character_flat",
                "dialogue": "前辈，我稍微翻了下你给主角写的设定...\n感觉虽然外貌很清晰，但内心深处最渴望的东西似乎还有点模糊？",
                "mood": AssistantState.THINKING,
                "options": [
                    {"text": "有道理，怎么完善？", "next_step": "suggestion"},
                    {"text": "我打算在正文中体现", "next_step": "accept"}
                ]
            },
            "suggestion": {
                "dialogue": "我们可以试试“反差设定”！\n比如一个坚强的人其实很怕黑，或者一个冷酷的人私下里很喜欢猫？\n要不要打开【角色卡工具】找找灵感？",
                "mood": AssistantState.HAPPY,
                "action": "open_tool:character_card",
                "options": [
                    {"text": "好主意", "next_step": "done"},
                    {"text": "我直接改改大纲", "next_step": "done"}
                ]
            },
            "accept": {
                "dialogue": "原来如此，把悬念留在正文里也是高招呢！\n不愧是前辈，是我多虑啦~",
                "mood": AssistantState.HAPPY,
                "finish_chain": True
            },
            "done": {
                "dialogue": "太棒了！丰满的角色会让故事更有生命力。\n加油，我很期待看到更立体的他/她！",
                "mood": AssistantState.CHEERING,
                "rewards": {"xp": 20, "affection": 5},
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # 悬疑小说讨论 (Mystery Novel Discussion)
    # 触发源：学校事件 "mystery_novel_club"
    # ---------------------------------------------------------
    "mystery_discussion": {
        "priority": 50,
        "cooldown": 0, # 由事件强制触发，无视冷却
        "steps": {
            "start": {
                "delay": 5, # 事件结束后5秒触发
                "dialogue": "其实... 刚才说的那个诡计，我还是觉得有点在意。\n前辈，如果你是作者，你会怎么设计那个密室？",
                "mood": AssistantState.THINKING,
                "options": [
                    {"text": "利用视觉错位", "next_step": "visual_trick"},
                    {"text": "其实根本没有密室", "next_step": "psychological"}
                ]
            },
            "visual_trick": {
                "dialogue": "原来如此！利用镜子或者角度吗...\n哇，感觉前辈随口一说都比那本书精彩！\n(拿出小本本记下来)",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 10},
                "diary_id": "mystery_novel_club",
                "finish_chain": True
            },
            "psychological": {
                "dialogue": "叙述性诡计？！\n那是最高级的骗术了！\n前辈...你的脑洞好深不可测啊...",
                "mood": AssistantState.SHOCKED,
                "rewards": {"affection": 5},
                "diary_id": "mystery_novel_club",
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # NPC 剧情线：部长路线 (Rivalry Arc - Ren Path)
    # 触发源：在社团争论中支持部长
    # ---------------------------------------------------------
    "rivalry_support_ren": {
        "priority": 60,
        "cooldown": 0,
        "steps": {
            "start": {
                "delay": 1800, # 30分钟后触发（模拟回家路上的沉默）
                "dialogue": "......\n(助手看起来一直闷闷不乐，欲言又止)",
                "mood": AssistantState.SAD,
                "options": [
                    {"text": "还在在意刚才的事？", "next_step": "express_sadness"},
                    {"text": "部长的建议也有道理", "next_step": "argument"}
                ]
            },
            "express_sadness": {
                "dialogue": "虽然我知道前辈是对的...桐生学姐确实很有才华。\n但是...哪怕一次也好，我想被前辈无条件地站在这一边啊...",
                "mood": AssistantState.CRYING,
                "options": [
                    {"text": "下次一定", "next_step": "cold_end"},
                    {"text": "摸摸头安慰她", "next_step": "comfort"}
                ]
            },
            "argument": {
                "dialogue": "道理我都懂！\n可是...算了，前辈这个大笨蛋！\n(她转过身去，不想理你)",
                "mood": AssistantState.ANGRY,
                "finish_chain": True
            },
            "comfort": {
                "dialogue": "呜... 狡猾... \n被前辈这样摸头，就没法继续生气了啊...\n这次就原谅你了。",
                "mood": AssistantState.SHY,
                "rewards": {"affection": 3},
                "diary_id": "rivalry_support_ren",
                "finish_chain": True
            },
            "cold_end": {
                "dialogue": "......\n(只有沉默)",
                "mood": AssistantState.IDLE,
                "diary_id": "rivalry_support_ren",
                "finish_chain": True
            }
        }
    },

    # ---------------------------------------------------------
    # NPC 剧情线：助手路线 (Rivalry Arc - Assistant Path)
    # 触发源：在社团争论中支持助手
    # ---------------------------------------------------------
    "rivalry_support_assistant": {
        "priority": 60,
        "cooldown": 0,
        "steps": {
            "start": {
                "delay": 300, # 5分钟后触发
                "dialogue": "嘿嘿... \n刚才前辈怼部长的样子，真的超级帅气！\n我当时心跳都漏了一拍呢！",
                "mood": AssistantState.EXCITED,
                "options": [
                    {"text": "毕竟我是你这边的人", "next_step": "devotion"},
                    {"text": "单纯是看不惯她傲慢", "next_step": "tsundere"}
                ]
            },
            "devotion": {
                "dialogue": "「我这边的人」... \n这句话，我可以当做是某种承诺吗？\n我会一直记在心里的！",
                "mood": AssistantState.LOVE,
                "rewards": {"affection": 10},
                "diary_id": "rivalry_support_assistant",
                "finish_chain": True
            },
            "tsundere": {
                "dialogue": "又在掩饰了~\n前辈明明就是想保护我嘛。\n我都懂的！",
                "mood": AssistantState.HAPPY,
                "rewards": {"affection": 5},
                "diary_id": "rivalry_support_assistant",
                "finish_chain": True
            }
        }
    }
}
