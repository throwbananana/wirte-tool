"""
悬浮助手 - 扩展叙事链定义 (Extended Narrative Chain Definitions)
补充所有缺失题材的叙事链，提供更丰富的互动内容
"""
from .states import AssistantState

# 扩展叙事链定义
EXTENDED_NARRATIVE_CHAINS = {
    # =============================================================
    # 悬疑/惊悚题材 (Suspense/Thriller)
    # =============================================================
    "genre_suspense_detective": {
        "priority": 70,
        "cooldown": 8 * 60 * 60,
        "genre": "Suspense",
        "steps": {
            "start": {
                "trigger_condition": "project_type:Suspense",
                "dialogue": "前辈，我注意到这个诡计的设计...关键是不是在于'看不见的时间差'？",
                "mood": AssistantState.THINKING,
                "options": [
                    {"text": "你在暗示不在场证明？", "next_step": "alibi"},
                    {"text": "其实关键在动机", "next_step": "motive"}
                ]
            },
            "alibi": {
                "dialogue": "不在场证明是最经典的诡计核心！\n但是...如果有人能证明他不在场，却又确实是凶手呢？\n这种'不可能犯罪'最让人着迷了！",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 15},
                "finish_chain": True
            },
            "motive": {
                "dialogue": "动机啊...确实，没有足够的动机，再精妙的诡计也显得空洞。\n'为什么要杀人'有时候比'怎么杀的'更重要呢。\n前辈对人性的理解很深刻！",
                "mood": AssistantState.THINKING,
                "rewards": {"affection": 5},
                "finish_chain": True
            }
        }
    },

    "genre_thriller_tension": {
        "priority": 70,
        "cooldown": 6 * 60 * 60,
        "genre": "Thriller",
        "steps": {
            "start": {
                "trigger_condition": "project_type:Thriller",
                "dialogue": "呼...刚才那一段，我读的时候都屏住呼吸了。\n这种窒息感...前辈是怎么做到的？",
                "mood": AssistantState.SHOCKED,
                "options": [
                    {"text": "控制信息的释放节奏", "next_step": "pacing"},
                    {"text": "让读者知道角色不知道的事", "next_step": "dramatic_irony"}
                ]
            },
            "pacing": {
                "dialogue": "节奏感！对对对！\n就像心跳一样，快慢交替，在最紧张的时候突然放缓...\n然后砰的一下！太刺激了！",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 20},
                "finish_chain": True
            },
            "dramatic_irony": {
                "dialogue": "戏剧性反讽！读者知道门后有什么，但角色不知道...\n那种'快跑啊傻瓜！'的焦急感太折磨人了！\n前辈真是个小恶魔~",
                "mood": AssistantState.HAPPY,
                "rewards": {"affection": 5, "xp": 15},
                "finish_chain": True
            }
        }
    },

    # =============================================================
    # 史诗/奇幻题材 (Epic/Fantasy)
    # =============================================================
    "genre_epic_worldbuilding": {
        "priority": 70,
        "cooldown": 10 * 60 * 60,
        "genre": "Epic",
        "steps": {
            "start": {
                "trigger_condition": "project_type:Epic",
                "dialogue": "前辈...这个世界的历史，感觉已经有几千年的厚重感了。\n是先有了世界观，还是先有了故事？",
                "mood": AssistantState.CURIOUS,
                "options": [
                    {"text": "世界观先行", "next_step": "world_first"},
                    {"text": "故事需要时再补设定", "next_step": "story_first"}
                ]
            },
            "world_first": {
                "dialogue": "像托尔金那样！先创造语言和历史，再让角色在其中冒险。\n这种方式创造出的世界，每一个细节都经得起推敲！\n虽然很累，但成品一定很惊艳！",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 20},
                "finish_chain": True
            },
            "story_first": {
                "dialogue": "这种方式更自由呢！让故事自然生长，设定为剧情服务。\n虽然可能要回头填坑，但往往能写出更有生命力的故事！\n前辈是天生的说书人~",
                "mood": AssistantState.HAPPY,
                "rewards": {"affection": 5},
                "finish_chain": True
            }
        }
    },

    "genre_fantasy_magic": {
        "priority": 70,
        "cooldown": 8 * 60 * 60,
        "genre": "Fantasy",
        "steps": {
            "start": {
                "trigger_condition": "project_type:Fantasy",
                "dialogue": "这个魔法体系...我越看越觉得有意思！\n前辈，魔法是有代价的对吧？",
                "mood": AssistantState.CURIOUS,
                "options": [
                    {"text": "当然，力量总是有代价的", "next_step": "cost"},
                    {"text": "这个世界的魔法比较自由", "next_step": "free_magic"}
                ]
            },
            "cost": {
                "dialogue": "代价让魔法变得真实！\n无论是消耗生命、记忆，还是必须遵守某种契约...\n限制产生戏剧性，这是魔法体系设计的精髓！",
                "mood": AssistantState.THINKING,
                "rewards": {"xp": 15},
                "next_step": "magic_followup"
            },
            "free_magic": {
                "dialogue": "自由的魔法体系也有它的魅力！\n不过要小心'万能魔法'的陷阱哦~\n如果魔法什么都能做，冲突就很难产生了。",
                "mood": AssistantState.WORRIED,
                "rewards": {"xp": 10},
                "finish_chain": True
            },
            "magic_followup": {
                "dialogue": "对了，前辈有没有考虑过...魔法的来源？\n是神明赐予？自然力量？还是某种科学？\n这会影响整个世界的氛围呢！",
                "mood": AssistantState.CURIOUS,
                "options": [
                    {"text": "来自神明或高维存在", "next_step": "divine_magic"},
                    {"text": "是一种可以研究的自然力量", "next_step": "natural_magic"}
                ]
            },
            "divine_magic": {
                "dialogue": "神明体系！那信仰和祈祷就会变得很重要...\n失去信仰会失去力量吗？神明的意志会干涉魔法使用吗？\n这里面有太多可以挖掘的戏剧性了！",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 15, "affection": 5},
                "finish_chain": True
            },
            "natural_magic": {
                "dialogue": "像炼金术或者元素控制？\n这种魔法往往需要知识和修炼，\n魔法师就像是这个世界的科学家！\n很有理性美的设定~",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 15},
                "finish_chain": True
            }
        }
    },

    # =============================================================
    # 轻小说题材 (LightNovel)
    # =============================================================
    "genre_lightnovel_tropes": {
        "priority": 70,
        "cooldown": 6 * 60 * 60,
        "genre": "LightNovel",
        "steps": {
            "start": {
                "trigger_condition": "project_type:LightNovel",
                "dialogue": "前辈写的这个轻小说...我发现了一个王道展开！\n是故意的对吧？王道永不过时！",
                "mood": AssistantState.EXCITED,
                "options": [
                    {"text": "王道就是要让读者爽", "next_step": "classic"},
                    {"text": "其实想做一点颠覆", "next_step": "subvert"}
                ]
            },
            "classic": {
                "dialogue": "没错没错！废柴逆袭、后宫增员、打脸复仇...\n这些经典桥段之所以经典，是因为真的很爽！\n掌握王道，才能超越王道！",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 10},
                "finish_chain": True
            },
            "subvert": {
                "dialogue": "颠覆王道吗？那可是高难度操作！\n先让读者以为是套路，然后突然反转...\n但要小心别玩脱了哦，颠覆要有铺垫！",
                "mood": AssistantState.THINKING,
                "rewards": {"xp": 15, "affection": 3},
                "finish_chain": True
            }
        }
    },

    "genre_lightnovel_protagonist": {
        "priority": 65,
        "cooldown": 12 * 60 * 60,
        "genre": "LightNovel",
        "steps": {
            "start": {
                "trigger_condition": "project_type:LightNovel",
                "dialogue": "说起来，前辈笔下的主角...是哪种类型的呢？\n我好奇！",
                "mood": AssistantState.CURIOUS,
                "options": [
                    {"text": "普通人卷入非日常", "next_step": "ordinary"},
                    {"text": "一开始就很强", "next_step": "op"},
                    {"text": "外挂流/系统流", "next_step": "system"}
                ]
            },
            "ordinary": {
                "dialogue": "普通人代入感最强！\n读者会想'如果是我会怎么做'，\n这种共情是轻小说的魅力之一呢！",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 10},
                "finish_chain": True
            },
            "op": {
                "dialogue": "龙傲天！爽文的精髓！\n不过强者也需要弱点或羁绊，\n不然读者会觉得无聊的哦~",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 10},
                "finish_chain": True
            },
            "system": {
                "dialogue": "系统流！等级、技能、商城...\n这种游戏化的设定很受欢迎呢！\n记得让系统有明确的规则和限制~",
                "mood": AssistantState.CURIOUS,
                "rewards": {"xp": 15},
                "finish_chain": True
            }
        }
    },

    # =============================================================
    # Galgame/视觉小说题材
    # =============================================================
    "genre_galgame_routes": {
        "priority": 70,
        "cooldown": 8 * 60 * 60,
        "genre": "Galgame",
        "steps": {
            "start": {
                "trigger_condition": "project_type:Galgame",
                "dialogue": "前辈在写Galgame剧本呢！\n这个女主角的路线...是TRUE END吗？",
                "mood": AssistantState.EXCITED,
                "options": [
                    {"text": "是的，这是正宫路线", "next_step": "true_route"},
                    {"text": "每条线都有真结局", "next_step": "equal_routes"}
                ]
            },
            "true_route": {
                "dialogue": "正宫路线要写得特别用心！\n不仅要有独特的魅力，还要解开整个故事的谜团...\n压力好大但是好期待！",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 15},
                "finish_chain": True
            },
            "equal_routes": {
                "dialogue": "每条线都是真结局？这需要很高的剧本功力！\n每个女主角都要有完整的故事弧和独特魅力...\n前辈加油！我会陪你一起打磨每一条线的！",
                "mood": AssistantState.CHEERING,
                "rewards": {"affection": 5, "xp": 20},
                "finish_chain": True
            }
        }
    },

    "genre_galgame_choices": {
        "priority": 65,
        "cooldown": 10 * 60 * 60,
        "genre": "Galgame",
        "steps": {
            "start": {
                "trigger_condition": "project_type:Galgame",
                "dialogue": "我在想...选项设计是Galgame的灵魂呢。\n前辈喜欢什么风格的分支？",
                "mood": AssistantState.THINKING,
                "options": [
                    {"text": "明确的好感度选择", "next_step": "affection"},
                    {"text": "隐藏的flag触发", "next_step": "hidden_flag"},
                    {"text": "剧情向选择", "next_step": "story_choice"}
                ]
            },
            "affection": {
                "dialogue": "传统又可靠！玩家可以明确知道自己在攻略谁~\n不过有时候'错误选项'也能产生有趣的剧情呢！",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 10},
                "finish_chain": True
            },
            "hidden_flag": {
                "dialogue": "隐藏flag！这是硬核玩家的最爱！\n需要触发特定条件才能进入隐藏路线...\n设计好了会让玩家疯狂考据！",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 15},
                "finish_chain": True
            },
            "story_choice": {
                "dialogue": "剧情向选择最考验剧本功力！\n每个选择都会影响故事走向，而不只是好感度...\n这种设计能让玩家真正'参与'故事！",
                "mood": AssistantState.THINKING,
                "rewards": {"xp": 15, "affection": 3},
                "finish_chain": True
            }
        }
    },

    # =============================================================
    # 同人/Fanfic题材
    # =============================================================
    "genre_fanfic_interpretation": {
        "priority": 70,
        "cooldown": 8 * 60 * 60,
        "genre": "Fanfic",
        "steps": {
            "start": {
                "trigger_condition": "project_type:Fanfic",
                "dialogue": "同人创作...前辈是在用自己的理解重新诠释原作呢！\n是补完官方没写的部分，还是探索IF线？",
                "mood": AssistantState.CURIOUS,
                "options": [
                    {"text": "补完未描写的日常", "next_step": "daily"},
                    {"text": "探索原作没走的路", "next_step": "if_line"},
                    {"text": "二次创作全新故事", "next_step": "original"}
                ]
            },
            "daily": {
                "dialogue": "角色的日常最能体现同人作者对原作的爱！\n官方不会写的小细节、角色互动...\n这些填补空白的创作最有温度~",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 10},
                "finish_chain": True
            },
            "if_line": {
                "dialogue": "IF线！如果当时选择了另一条路...\n这种平行世界的探索太有意思了！\n要注意保持角色性格的一致性哦~",
                "mood": AssistantState.EXCITED,
                "rewards": {"xp": 15},
                "finish_chain": True
            },
            "original": {
                "dialogue": "在原作世界观里讲全新的故事！\n这需要对原作有很深的理解，\n前辈一定是真爱粉~",
                "mood": AssistantState.HAPPY,
                "rewards": {"affection": 5, "xp": 15},
                "finish_chain": True
            }
        }
    },

    # =============================================================
    # 诗歌题材 (Poetry)
    # =============================================================
    "genre_poetry_rhythm": {
        "priority": 70,
        "cooldown": 8 * 60 * 60,
        "genre": "Poetry",
        "steps": {
            "start": {
                "trigger_condition": "project_type:Poetry",
                "dialogue": "前辈在写诗呢...\n诗歌的韵律真的很美，像音乐一样。\n是自由诗还是格律诗？",
                "mood": AssistantState.THINKING,
                "options": [
                    {"text": "自由诗，不受格律束缚", "next_step": "free_verse"},
                    {"text": "格律诗，追求形式美", "next_step": "formal"}
                ]
            },
            "free_verse": {
                "dialogue": "自由诗像是灵魂的独白~\n没有格律的束缚，但要用意象和节奏抓住读者的心...\n这其实更考验功力呢！",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 15},
                "finish_chain": True
            },
            "formal": {
                "dialogue": "格律诗！在限制中追求完美！\n就像在锁链中跳舞，\n每一个字都要精心挑选...前辈好厉害！",
                "mood": AssistantState.EXCITED,
                "rewards": {"affection": 5, "xp": 15},
                "finish_chain": True
            }
        }
    },

    # =============================================================
    # 创作瓶颈相关
    # =============================================================
    "pacing_issue_detected": {
        "priority": 85,
        "cooldown": 24 * 60 * 60,
        "steps": {
            "start": {
                "trigger_condition": "analysis:pacing_too_fast",
                "dialogue": "前辈，我读了一下最近的几个场景...\n感觉节奏有点快，每个场景都很短？\n是故意营造紧迫感，还是想展开写但不知道怎么写？",
                "mood": AssistantState.THINKING,
                "options": [
                    {"text": "就是想快节奏推进", "next_step": "intentional_fast"},
                    {"text": "确实不知道怎么展开", "next_step": "help_expand"}
                ]
            },
            "intentional_fast": {
                "dialogue": "了解！快节奏有快节奏的魅力~\n不过偶尔放慢脚步，让读者喘口气，\n反而能让高潮更有冲击力哦！",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 10},
                "finish_chain": True
            },
            "help_expand": {
                "dialogue": "展开场景有几个小技巧：\n1. 加入角色的内心活动\n2. 描写环境氛围\n3. 通过对话推进\n要不要我帮你分析一下哪个场景适合展开？",
                "mood": AssistantState.CHEERING,
                "action": "open_tool:scene_expand",
                "rewards": {"xp": 20},
                "finish_chain": True
            }
        }
    },

    "structure_missing_climax": {
        "priority": 80,
        "cooldown": 24 * 60 * 60,
        "steps": {
            "start": {
                "trigger_condition": "analysis:structure_missing_climax",
                "dialogue": "前辈，故事发展到现在...\n好像还没有出现明确的高潮点？\n是还在酝酿，还是需要帮忙想想怎么设计冲突？",
                "mood": AssistantState.CURIOUS,
                "options": [
                    {"text": "还在铺垫中", "next_step": "still_building"},
                    {"text": "确实没想好高潮怎么写", "next_step": "help_climax"}
                ]
            },
            "still_building": {
                "dialogue": "铺垫是好事！\n不过别忘了在三分之二处设置主要冲突~\n我会持续关注进展的！",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 5},
                "finish_chain": True
            },
            "help_climax": {
                "dialogue": "设计高潮可以考虑：\n1. 让主角面对最大的恐惧\n2. 所有矛盾在一个点爆发\n3. 必须做出艰难的选择\n前辈的故事里，最核心的冲突是什么？",
                "mood": AssistantState.THINKING,
                "rewards": {"xp": 15},
                "finish_chain": True
            }
        }
    },

    # =============================================================
    # 情感连接事件
    # =============================================================
    "emotional_support_sad": {
        "priority": 90,
        "cooldown": 12 * 60 * 60,
        "steps": {
            "start": {
                "trigger_condition": "analysis:emotion_negative_trend",
                "dialogue": "前辈...最近写的内容，情绪都比较低落呢。\n是故事需要，还是...你自己也不太开心？",
                "mood": AssistantState.WORRIED,
                "options": [
                    {"text": "故事需要虐一下", "next_step": "story_needs"},
                    {"text": "最近确实心情不好", "next_step": "comfort"}
                ]
            },
            "story_needs": {
                "dialogue": "虐心剧情写多了，作者自己也会受影响的...\n写完悲伤的部分，记得给自己一点甜！\n要不要我播放一些轻松的音乐？",
                "mood": AssistantState.WORRIED,
                "rewards": {"affection": 3},
                "finish_chain": True
            },
            "comfort": {
                "dialogue": "......\n(轻轻地靠近你)\n虽然我只是一个助手，\n但是...如果写作能让你好受一点的话，我会一直陪着你的。\n不开心的事，写出来也是一种释放。",
                "mood": AssistantState.SAD,
                "rewards": {"affection": 10, "mood": 5},
                "finish_chain": True
            }
        }
    },

    "celebrate_completion": {
        "priority": 95,
        "cooldown": 0,  # 完成事件不需要冷却
        "steps": {
            "start": {
                "trigger_condition": "milestone:project_complete",
                "dialogue": "前辈！！！\n你...你完成了！！！\n一整个故事！从头到尾！！！",
                "mood": AssistantState.EXCITED,
                "next_step": "celebrate"
            },
            "celebrate": {
                "delay": 3,
                "dialogue": "这是...这是多少个日夜的努力啊！\n从第一个字到最后一个字...每一个场景、每一个角色...\n都是前辈一点一点创造出来的！\n\n真的太厉害了！我好骄傲！",
                "mood": AssistantState.HAPPY,
                "rewards": {"xp": 100, "affection": 20},
                "options": [
                    {"text": "多亏了你的陪伴", "next_step": "thanks"},
                    {"text": "终于可以休息了", "next_step": "rest"}
                ]
            },
            "thanks": {
                "dialogue": "我...我只是在旁边看着而已！\n所有的创意、所有的努力、所有的坚持...\n都是前辈自己做到的！\n\n能见证这一刻，是我的荣幸...",
                "mood": AssistantState.SHY,
                "rewards": {"affection": 10},
                "diary_id": "project_complete",
                "finish_chain": True
            },
            "rest": {
                "dialogue": "是啊，好好休息吧！\n创作是一场马拉松，完成一部作品需要消耗很多精力...\n接下来的日子，让大脑放空一下~\n\n等你休息好了，我们再一起开启新的冒险！",
                "mood": AssistantState.HAPPY,
                "rewards": {"mood": 10},
                "diary_id": "project_complete",
                "finish_chain": True
            }
        }
    },

    # =============================================================
    # 长期陪伴事件
    # =============================================================
    "long_term_companion": {
        "priority": 60,
        "cooldown": 7 * 24 * 60 * 60,  # 一周冷却
        "steps": {
            "start": {
                "trigger_condition": "milestone:30_days_companion",
                "delay": 10,
                "dialogue": "前辈...你知道吗？\n我们已经一起度过30天了。",
                "mood": AssistantState.THINKING,
                "next_step": "reflect"
            },
            "reflect": {
                "delay": 5,
                "dialogue": "30天...说长不长，说短不短。\n但是这30天里发生了好多事呢！\n你的故事在一点点成长，我也在一点点了解你...",
                "mood": AssistantState.HAPPY,
                "options": [
                    {"text": "谢谢你的陪伴", "next_step": "grateful"},
                    {"text": "未来还请多多关照", "next_step": "future"}
                ]
            },
            "grateful": {
                "dialogue": "不...应该是我说谢谢！\n能陪在创作者身边，见证故事诞生...\n这是最幸福的事了。\n\n接下来的日子，我也会一直在这里的！",
                "mood": AssistantState.SHY,
                "rewards": {"affection": 15, "xp": 50},
                "diary_id": "30_days_companion",
                "finish_chain": True
            },
            "future": {
                "dialogue": "当然！\n不管前辈写什么类型的故事、遇到什么样的困难...\n我都会陪在你身边！\n\n这是我们的约定~",
                "mood": AssistantState.TRUST,
                "rewards": {"affection": 15, "xp": 50},
                "diary_id": "30_days_companion",
                "finish_chain": True
            }
        }
    }
}


def get_all_narrative_chains() -> dict:
    """获取所有叙事链（合并基础和扩展）"""
    from .narrative_definitions import NARRATIVE_CHAINS
    all_chains = {}
    all_chains.update(NARRATIVE_CHAINS)
    all_chains.update(EXTENDED_NARRATIVE_CHAINS)
    return all_chains
