from typing import Dict, List


WIKI_TEMPLATES: Dict[str, List[str]] = {
    "通用": ["人物", "地点", "物品", "势力", "设定", "其他"],
    "悬疑": ["人物", "证据", "地点", "时间点", "动机", "其他"],
    "言情": ["人物", "地点", "回忆", "约定", "情感节点", "其他"],
    "科幻": ["人物", "地点", "科技", "势力", "星球", "飞船", "设定", "其他"],
    "奇幻": ["人物", "地点", "种族", "魔法", "势力", "历史", "设定", "其他"],
    "武侠": ["人物", "门派", "功法", "兵器", "江湖势力", "恩怨", "地点", "其他"],
    "历史": ["人物", "朝代", "事件", "地理", "制度", "史料", "其他"],
    "校园": ["人物", "地点", "社团", "课程", "事件", "回忆", "其他"],
}


def get_template_names() -> List[str]:
    return list(WIKI_TEMPLATES.keys())


def get_template_categories(name: str) -> List[str]:
    return list(WIKI_TEMPLATES.get(name, []))


def merge_categories(base: List[str], extra: List[str]) -> List[str]:
    merged = list(base or [])
    for item in extra or []:
        if item not in merged:
            merged.append(item)
    return merged
