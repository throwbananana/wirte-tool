"""预置的思维导图模板集合，用于不同题材的快速结构化。"""

import json


def _deepcopy(data):
    return json.loads(json.dumps(data))


# 保持插入顺序，方便菜单显示
OUTLINE_TEMPLATES = {
    "suspense_layers": {
        "name": "悬疑/推理三层图",
        "description": "分层拆分真相、谎言、叙事节奏，避免所有问题挤在一张平面图里。",
        "nodes": [
            {
                "name": "层1：上帝视角（The Truth）",
                "content": "写纯物理真相：发生了什么、为什么、有哪些意外变量。不要考虑欺骗读者。",
                "children": [
                    {"name": "真实动机（Why）", "content": "谁为什么要行动？真实的利益或威胁是什么。"},
                    {"name": "真实行动时间轴（What/When/Where）", "content": "按时间列出动作、地点、工具，保持自洽。"},
                    {"name": "意外变量（Chaos）", "content": "计划外事件：第三人闯入、天气突变、装备失效等。"},
                ],
            },
            {
                "name": "层2：嫌疑人视角（The Lie）",
                "content": "凶手/策划者希望世界看到的剧本，用谎言包住真相。",
                "children": [
                    {"name": "表面动机/借口（Excuse）", "content": "他们对外的说辞，用来掩盖真实动机。"},
                    {"name": "信息差/隐藏点（Gap）", "content": "刻意遮蔽的关系、物品或时间点。"},
                    {"name": "破绽与证据（Bug）", "content": "谎言与真相的碰撞点，读者/侦探可抓到的证据。"},
                ],
            },
            {
                "name": "层3：侦探/读者视角（The Story）",
                "content": "叙事节奏层：先误导，再反转，逐步揭露真相。",
                "children": [
                    {"name": "切入点（Hook）", "content": "读者首先看到的画面/证词，让好奇心被勾住。"},
                    {"name": "误导（Red Herring）", "content": "优先抛出的假线索，引导错误方向。"},
                    {"name": "反转与揭示（Twist）", "content": "在哪个节点戳破谎言？用什么证据完成反转。"},
                ],
            },
        ],
    },
    "emotional_arc": {
        "name": "情感脉络弧线",
        "description": "适合情感/成长故事，用波峰波谷标记情绪旅程和代价。",
        "nodes": [
            {
                "name": "情感弧线基线",
                "content": "人物关系的起点：彼此的缺口、渴望与禁忌。",
                "children": [
                    {"name": "缺口/伤口", "content": "角色内在的伤与需求，决定情感走向。"},
                    {"name": "关系现状", "content": "当下的默契/隔阂，观众进场时的温度。"},
                ],
            },
            {"name": "触发事件", "content": "让情绪开始波动的外部/内部诱因。"},
            {"name": "情绪波峰", "content": "高光或短暂幸福，人物许下承诺或幻想。"},
            {"name": "情绪波谷", "content": "冲突、误会或失落，明确代价与退路。"},
            {"name": "修复/决裂选择", "content": "角色主动选择，付出代价（道歉、牺牲、放手）。"},
            {"name": "余韵与成长", "content": "情感余波后的新坐标：彼此的改变、主题命题句。"},
        ],
    },
    "poetry_palette": {
        "name": "诗歌意象板",
        "description": "为诗歌或抒情片段准备意象、声韵与结构的素材盘。",
        "nodes": [
            {"name": "主题与情绪色调", "content": "一句话写清核心意图与情绪（清冷/炽热/孤寂等）。"},
            {
                "name": "意象池",
                "content": "收集可循环使用的意象，保持色彩和质地的一致或刻意冲突。",
                "children": [
                    {"name": "自然/季节意象", "content": "雨、雾、秋叶、潮汐等。"},
                    {"name": "器物/材料", "content": "玻璃、铁锈、纸张、光纤、烟味。"},
                    {"name": "动作/体感", "content": "颤抖、坠落、呼吸、回声。"},
                ],
            },
            {"name": "声音与节奏", "content": "押韵策略、节奏型、重音/停顿安排。"},
            {"name": "结构与转折", "content": "分节/叠句/转折段，何处翻面或留白。"},
            {"name": "钩子与余味", "content": "意外的比喻或结尾回声，让情绪延迟消散。"},
        ],
    },
    "three_act": {
        "name": "经典三幕式",
        "description": "好莱坞经典叙事结构，通用性最强，适合绝大多数故事。",
        "nodes": [
            {
                "name": "第一幕：铺垫 (Act I)",
                "content": "建立世界观、介绍人物、确立基调。",
                "children": [
                    {"name": "现状 (Status Quo)", "content": "主角的日常生活和未被满足的渴望。"},
                    {"name": "激励事件 (Inciting Incident)", "content": "打破平衡的事件，故事真正开始。"},
                    {"name": "情节点一 (Plot Point 1)", "content": "主角决定踏上旅程，离开舒适区，不可逆转的时刻。"},
                ],
            },
            {
                "name": "第二幕：对抗 (Act II)",
                "content": "冲突升级，主角面临试炼、盟友与敌人。",
                "children": [
                    {"name": "试炼之路", "content": "一系列的挑战，主角学习新规则。"},
                    {"name": "中点 (Midpoint)", "content": "故事中间的重大转折，主角由被动变主动，或虚假的胜利/失败。"},
                    {"name": "一无所有时刻 (All Is Lost)", "content": "最低谷，看似彻底失败，必须面对内心最大的恐惧。"},
                ],
            },
            {
                "name": "第三幕：结局 (Act III)",
                "content": "高潮与新的平衡。",
                "children": [
                    {"name": "高潮 (Climax)", "content": "最后的决战，主角必须应用所学战胜反派/困难。"},
                    {"name": "结局 (Resolution)", "content": "故事结束，展示新的常态和主角的成长。"},
                ],
            },
        ],
    },
    "hero_journey": {
        "name": "冒险/英雄之旅",
        "description": "坎贝尔经典神话结构，适合奇幻、冒险、史诗题材。",
        "nodes": [
            {"name": "平凡世界", "content": "主角在舒适区的状态，展现其渴望与缺陷。"},
            {"name": "冒险召唤", "content": "打破平静的事件，必须做出选择。"},
            {"name": "拒斥召唤", "content": "主角因恐惧或犹豫最初拒绝冒险。"},
            {"name": "遇见导师", "content": "获得建议、宝物或心理准备。"},
            {"name": "跨越门槛", "content": "主角离开舒适区，进入未知世界，冒险正式开始。"},
            {"name": "试炼与盟友", "content": "在新世界探索，结识伙伴，遭遇小挫折，了解规则。"},
            {"name": "接近洞穴", "content": "为核心挑战做准备，计划实施。"},
            {"name": "核心危机 (Ordeal)", "content": "直面最大的恐惧或敌人，遭遇重创/假死。"},
            {"name": "获得奖赏", "content": "战胜危机后获得的宝物、知识或力量。"},
            {"name": "回归之路", "content": "带着战利品返回，遭遇最后的追逐或阻碍。"},
            {"name": "复活/觉醒", "content": "最终的决战，主角完成内在彻底蜕变，应用所学。"},
            {"name": "满载而归", "content": "回到平凡世界，用所得改变现状或惠及他人。"},
        ],
    },
    "comedy_structure": {
        "name": "喜剧/情景结构",
        "description": "建立在误会、错位与反差上的结构，适合轻小说、情景剧。",
        "nodes": [
            {"name": "常态与怪癖", "content": "角色性格中的怪癖、执念或荒谬的设定背景。"},
            {"name": "激励事件/目标", "content": "一个小谎言、误会，或一个看似简单实则荒唐的目标。"},
            {
                "name": "错误决策链",
                "content": "角色为了掩盖谎言或达成目标，做出越来越离谱的尝试。",
                "children": [
                    {"name": "滚雪球 (Escalation)", "content": "不仅没解决问题，反而引入了新麻烦，谎言越扯越大。"},
                    {"name": "猪队友/阻碍", "content": "好心办坏事的盟友或极其较真的对头。"},
                ],
            },
            {"name": "混乱高潮", "content": "所有线索纠缠在一起，多方势力汇聚，场面极度混乱尴尬。"},
            {"name": "意外和解/反转", "content": "通过意外事件或突然坦白解决问题，通常回到原点但有些许温情。"},
            {"name": "笑点回归 (The Tag)", "content": "最后的笑话或余韵，暗示角色本性难移，或者新的麻烦开始。"},
        ],
    },
}


def list_outline_templates():
    """返回模板元数据列表，用于菜单展示。"""
    return [
        {"key": key, "name": tpl["name"], "description": tpl.get("description", "")}
        for key, tpl in OUTLINE_TEMPLATES.items()
    ]


def get_outline_template_nodes(key):
    """获取模板节点的深拷贝列表。"""
    template = OUTLINE_TEMPLATES.get(key)
    if not template:
        return []
    return _deepcopy(template.get("nodes", []))


def get_outline_template_meta(key):
    """返回模板的名称与描述元数据。"""
    template = OUTLINE_TEMPLATES.get(key)
    if not template:
        return None
    return {
        "key": key,
        "name": template.get("name", key),
        "description": template.get("description", ""),
    }
