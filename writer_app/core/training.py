import json
import random
import logging
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from writer_app.core.analysis import TextMetrics

logger = logging.getLogger(__name__)

MODES = {
    # 逻辑训练
    "continuation": "续写挑战",
    "editing": "编辑训练营",

    # 创意训练
    "keywords": "关键词联想",
    "brainstorm": "头脑风暴",

    # 描写训练
    "sensory": "感官描写",
    "show_dont_tell": "展示而非讲述",

    # 情感训练
    "style": "风格模仿",
    "emotion_infusion": "情感注入",

    # 对话训练
    "dialogue_subtext": "潜台词训练",
    "character_voice": "角色腔调",

    # 人物训练
    "character_persona": "人设生成",
    "character_arc": "人物弧光"
}

MODE_CATEGORIES = {
    "逻辑训练": ["continuation", "editing"],
    "创意训练": ["keywords", "brainstorm"],
    "描写训练": ["sensory", "show_dont_tell"],
    "情感训练": ["style", "emotion_infusion"],
    "对话训练": ["dialogue_subtext", "character_voice"],
    "人物训练": ["character_persona", "character_arc"]
}

STYLES = [
    "海明威风格（极简主义、冰山理论）",
    "鲁迅风格（犀利、社会批判）",
    "古龙风格（短句、诗意、武侠）",
    "黑色电影风格（愤世嫉俗、黑暗、氛围感）",
    "哥特恐怖风格（诡异、浪漫、颓废）",
    "魔幻现实主义（日常与魔幻交织）",
    "赛博朋克风格（高科技、低生活、霓虹灯）",
    "武侠风格（江湖义气、侠骨柔情）",
    "卡夫卡风格（荒诞、官僚主义、超现实）",
    "简·奥斯汀风格（机智、社会讽刺、爱情）",
    "洛夫克拉夫特风格（宇宙恐怖、繁复、古老）",
    "意识流风格（伍尔夫、乔伊斯）",
    "硬汉派侦探风格（雷蒙德·钱德勒）",
    "高奇幻风格（托尔金、世界构建）",
    "蒸汽朋克风格（维多利亚科技、蒸汽动力）",
    "反乌托邦风格（压迫社会、生存挣扎）",
    "太空歌剧风格（星际旅行、宏大叙事）",
    "童话风格（奇幻、寓意、简洁）",
    "垮掉派风格（凯鲁亚克、即兴、爵士感）",
    "南方哥特风格（奥康纳、怪诞、乡村）"
]

SENSORY_CONSTRAINTS = [
    "禁用视觉（只能用听觉/嗅觉）",
    "禁用听觉（只能用视觉/触觉）",
    "聚焦味觉与质感",
    "聚焦温度与动感",
    "只用嗅觉（嗅觉轰炸）",
    "用声音词汇描述寂静",
    "用视觉词汇描述黑暗",
    "聚焦内在身体感受（内感受）"
]

EMOTIONS = [
    "喜悦/狂喜", "悲伤/绝望", "愤怒/暴怒", "恐惧/惊骇",
    "厌恶", "惊讶/震惊", "期待/焦虑", "信任/崇拜"
]

# 历史记录默认保留数量
DEFAULT_HISTORY_LIMIT = 50

# 每日任务通过分数
DAILY_QUEST_PASS_SCORE = 15


class TrainingManager:
    def __init__(self, data_dir: Path = None):
        self.word_bank_data = {}
        if data_dir:
            self.load_word_bank(data_dir / "word_bank.json")
        else:
            # 测试环境的回退加载
            try:
                p = Path(__file__).parent.parent.parent / "writer_data" / "word_bank.json"
                if p.exists():
                    self.load_word_bank(p)
            except Exception as e:
                logger.warning(f"无法加载词库: {e}")

    def load_word_bank(self, path: Path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.word_bank_data = json.load(f)
        except Exception as e:
            logger.error(f"加载词库失败: {e}")

    def get_levels(self) -> List[str]:
        return ["级别1（具象词汇）", "级别2（动作/抽象）", "级别3（复杂主题）"]

    def get_modes(self) -> Dict[str, str]:
        return MODES

    def get_categories(self) -> Dict[str, List[str]]:
        return MODE_CATEGORIES

    def get_all_tags(self) -> List[str]:
        """收集词库中所有唯一标签。"""
        tags = set()
        if not self.word_bank_data: return []

        def collect(data):
            if isinstance(data, dict):
                for k, v in data.items():
                    if k == "tags" and isinstance(v, list):
                        tags.update(v)
                    else:
                        collect(v)
            elif isinstance(data, list):
                for item in data:
                    collect(item)

        collect(self.word_bank_data)
        return sorted(list(tags))

    @staticmethod
    def _infer_level_index(level: str) -> int:
        """Infer a numeric level index (1-3) from localized level labels."""
        if not level:
            return 1

        # Prefer explicit digits when present (handles "Level 2", "级别2", etc.).
        match = re.search(r"([123])", str(level))
        if match:
            return int(match.group(1))

        level_lower = str(level).lower()
        if "level 1" in level_lower or "级别1" in level_lower:
            return 1
        if "level 2" in level_lower or "级别2" in level_lower:
            return 2
        return 3

    def get_words(self, level: str, count: int = 3, tags: List[str] = None) -> List[str]:
        """根据级别和可选标签获取随机词汇。"""
        if not self.word_bank_data:
            logger.warning("词库数据未加载，请检查 word_bank.json 文件是否存在")
            return ["词库未加载，请检查配置"]

        def format_item(item):
            if isinstance(item, dict):
                cn = item.get("cn") or item.get("zh") or ""
                en = item.get("en") or ""
                if cn and en:
                    return f"{cn}（{en}）"
                return cn or en
            if isinstance(item, str):
                return item
            return None

        pool = []

        # 根据级别收集候选词汇
        candidates = []
        level_idx = self._infer_level_index(level)
        if level_idx == 1:
            candidates.extend(self.word_bank_data.get("nouns", {}).get("concrete", []))
        elif level_idx == 2:
            candidates.extend(self.word_bank_data.get("nouns", {}).get("concrete", []))
            candidates.extend(self.word_bank_data.get("nouns", {}).get("abstract", []))
            candidates.extend(self.word_bank_data.get("verbs", []))
        else:  # 级别3
            candidates.extend(self.word_bank_data.get("adjectives", []))
            candidates.extend(self.word_bank_data.get("nouns", {}).get("abstract", []))
            candidates.extend(self.word_bank_data.get("verbs", []))

        # 2. 按标签筛选
        if tags and len(tags) > 0:
            filtered = []
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                item_tags = item.get("tags", [])
                if any(t in item_tags for t in tags):
                    filtered.append(item)

            if filtered:
                pool = filtered
            else:
                # Signal "no tag match" to the caller instead of silently
                # falling back to all candidates.
                logger.info("标签筛选未命中: %s", tags)
                return []
        else:
            pool = candidates

        if not pool: return []

        selected = random.sample(pool, min(count, len(pool)))
        formatted = [format_item(item) for item in selected]
        return [item for item in formatted if item]

    def get_template_prompt(self) -> str:
        templates = self.word_bank_data.get("templates", [])
        if not templates: return ""

        tmpl = random.choice(templates)
        structure = tmpl["structure"]

        parts = []
        for part_type in structure:
            if "." in part_type:
                cat, sub = part_type.split(".")
                options = self.word_bank_data.get(cat, {}).get(sub, [])
            else:
                options = self.word_bank_data.get(part_type, [])

            if options:
                item = random.choice(options)
                if isinstance(item, dict):
                    cn = item.get("cn") or item.get("zh") or ""
                    en = item.get("en") or ""
                    if cn and en:
                        parts.append(f"{cn}（{en}）")
                    else:
                        parts.append(cn or en)
                elif isinstance(item, str):
                    parts.append(item)

        return f"模板【{tmpl['desc']}】：" + " + ".join(parts)

    def get_random_style(self) -> str:
        return random.choice(STYLES)

    def get_random_sensory_constraint(self) -> str:
        return random.choice(SENSORY_CONSTRAINTS)

    def get_random_emotion(self) -> str:
        return random.choice(EMOTIONS)

    def get_random_archetype(self) -> str:
        archetypes = self.word_bank_data.get("archetypes", ["英雄（默认）"])
        return random.choice(archetypes)

    def get_random_event(self) -> str:
        events = self.word_bank_data.get("incidental_events", ["一只猫出现了（默认）"])
        return random.choice(events)

    # --- AI提示词生成逻辑 ---
    def get_setup_prompt(self, mode: str, topic: str = "") -> str:
        if mode == "continuation":
            return (
                f"请生成一个与「{topic or '悬疑'}」相关的引人入胜的故事开头（1-2句）。"
                f"应该是一个悬念或有趣的情境，适合作为写作提示。"
                f"只返回故事开头文本，使用简体中文。"
            )
        elif mode == "show_dont_tell":
            return (
                f"请生成一个与「{topic or '情感'}」相关的平淡「讲述」句子（如「他很生气」）。"
                f"用户的目标是用「展示而非讲述」的手法改写它。"
                f"只返回平淡的句子，使用简体中文。"
            )
        elif mode == "editing":
            return (
                f"请生成一个关于「{topic or '追逐场景'}」的短段落，该段落存在明显的写作问题"
                f"（如被动语态过多、副词滥用、对话生硬、或直白叙述）。"
                f"不要明说是什么问题，让用户自己识别并修复。"
                f"只返回有问题的段落，使用简体中文。"
            )
        elif mode == "brainstorm":
            return (
                f"请围绕「{topic or '科幻'}」列出10个创意写作点子或「如果……会怎样」的设定。"
                f"要求：\n"
                f"1. 每条独立一行（可编号），简体中文。\n"
                f"2. 只返回点子列表，不要解释。\n"
                f"3. 点子之间尽量差异化。"
            )
        elif mode == "emotion_infusion":
            return (
                f"请生成一个关于「{topic or '雨天'}」的中性、陈述性句子。"
                f"用户需要改写这个句子来注入特定情感（如喜悦、绝望）。"
                f"只返回中性句子，使用简体中文。"
            )
        elif mode == "dialogue_subtext":
            return (
                f"请生成一个两人对话场景，角色A想从角色B那里「{topic or '借钱'}」，但不能直接开口。"
                f"简要描述情境和隐藏的目的。"
                f"只返回场景描述，使用简体中文。"
            )
        elif mode == "character_voice":
            return (
                f"请生成两个性格迥异角色的简要描述（如老教授和街头混混），"
                f"他们在讨论「{topic or '人生的意义'}」。"
                f"只返回角色描述，使用简体中文。"
            )
        elif mode == "character_persona":
            return (
                f"请根据「{topic or '赛博朋克黑客'}」生成一个创意角色原型或核心特质组合。"
                f"用户需要将其扩展为完整的角色档案（姓名、年龄、背景故事、目标、缺陷）。"
                f"只返回原型/特质描述，使用简体中文。"
            )
        elif mode == "character_arc":
            return (
                f"请生成一个与「{topic or '雨天'}」相关的突发事件。"
                f"用户需要写出角色的反应，以及一个解释该反应的隐藏前史细节（伏笔）。"
                f"只返回事件描述，使用简体中文。"
            )
        return ""

    def get_word_generation_prompt(self, topic: str, level: str, count: int = 5) -> str:
        context = f"与主题「{topic}」相关" if topic else "完全随机、富有创意且彼此不同"

        return (
            f"你是一个创意写作助手。我需要{count}个具体、生动的关键词，{context}。\n"
            f"难度/风格：{level}\n\n"
            f"要求：\n"
            f"1. 只返回一个原始JSON数组，包含简体中文字符串，如 [\"词语1\", \"词语2\"]\n"
            f"2. 不要包含任何解释或JSON外的markdown格式。\n"
            f"3. 确保词语各不相同且能激发想象。"
        )

    def get_daily_quest_prompt(self) -> str:
        modes = ["keywords", "brainstorm", "style", "sensory", "show_dont_tell", "editing"]
        levels = self.get_levels()
        mode_hint = " | ".join(modes)
        level_hint = " | ".join(levels)
        return (
            f"你是写作训练任务生成器。请输出一个严格 JSON 对象，字段包括：\n"
            f"{{\"mode\": \"{mode_hint}\", \"topic\": \"主题\", \"level\": \"{level_hint}\", "
            f"\"title\": \"不超过12字\", \"description\": \"不超过40字\"}}\n"
            f"要求：\n"
            f"1. mode 必须从列表中选择。\n"
            f"2. topic 用简体中文短语（2-8字）。\n"
            f"3. title 以「每日任务：」开头更好。\n"
            f"4. description 描述该练习，不要包含 JSON 外文本。\n"
            f"5. 只返回 JSON 对象，不要包含 Markdown。"
        )

    def get_analysis_prompt(self, mode: str, exercise_data: Dict, content: str) -> str:
        level = exercise_data.get("level", "级别1")
        if "级别1" in level:
            persona = "鼓励型导师（侧重积极方面）"
            strictness = "宽松"
        elif "级别2" in level:
            persona = "专业编辑（客观、结构性）"
            strictness = "中等"
        else:
            persona = "严苛文学评论家（字斟句酌）"
            strictness = "严格"

        base_criteria = (
            f"分析提交作品。\n角色：{persona}\n严格程度：{strictness}\n"
            f"模式：{MODES.get(mode, mode)}\n背景：{exercise_data}\n"
            f"内容：\n'''\n{content}\n'''\n\n"
        )

        specific = ""
        if mode == "keywords":
            words = exercise_data.get("words", [])
            specific = f"评估关键词使用：{words}"
        elif mode == "style":
            specific = f"评估风格匹配度：{exercise_data.get('style')}"
        elif mode == "continuation":
            specific = "评估与开头的衔接流畅度。"
        elif mode == "sensory":
            specific = f"评估感官限制的遵守：{exercise_data.get('constraint')}"
        elif mode == "show_dont_tell":
            specific = "评估画面感vs直白叙述。"
        elif mode == "editing":
            bad_text = exercise_data.get("telling", "")
            specific = (
                f"原始有问题文本：「{bad_text}」。\n"
                f"识别原文的问题（被动语态？副词过多？）。\n"
                f"评估学员是否在保持原意的前提下修复了问题。"
            )
        elif mode == "brainstorm":
            specific = "评估创意的创造性、多样性和独特性。"
        elif mode == "emotion_infusion":
            target_emotion = exercise_data.get("emotion", "指定情感")
            specific = f"评估文本传达情感的效果：{target_emotion}。"
        elif mode == "dialogue_subtext":
            specific = "评估潜台词的运用。角色是否在不直接表述的情况下传达了隐藏目的？"
        elif mode == "character_voice":
            specific = "评估角色声音的区分度。仅通过对话风格能否辨别说话者？"
        elif mode == "character_persona":
            specific = (
                "评估角色人设。是否多维立体？"
                f"角色是否有清晰的目标、缺陷和一致的声音？"
                f"背景故事是否合理解释了当前特质？"
            )
        elif mode == "character_arc":
            specific = (
                "评估人物弧光练习。用户是否提供了可信的反应？"
                f"伏笔是否有效解释了反应并增加了深度？"
                f"过去事件与当前反应之间的联系是否合理？"
            )

        return (
            f"{base_criteria}{specific}\n"
            f"请用简体中文进行评分与点评，但只返回严格 JSON 对象，不要包含多余文本或 Markdown。\n"
            f"JSON 格式要求：\n"
            f"{{\n"
            f"  \"score_1\": 0-10,\n"
            f"  \"score_2\": 0-10,\n"
            f"  \"score_3\": 0-10,\n"
            f"  \"total\": 0-30,\n"
            f"  \"label_1\": \"评分1说明\",\n"
            f"  \"label_2\": \"评分2说明\",\n"
            f"  \"label_3\": \"评分3说明\",\n"
            f"  \"feedback\": \"不超过100字的点评与建议\"\n"
            f"}}\n"
            f"要求：total 应等于三个分数之和。"
        )

    def get_rewrite_prompt(self, mode: str, exercise_data: Dict, user_content: str) -> str:
        return (
            f"专家作者改写。\n模式：{mode}\n背景：{exercise_data}\n"
            f"用户作品：\n{user_content}\n\n"
            f"请用简体中文写一个专家级版本。"
        )

    def get_polish_prompt(self, user_content: str) -> str:
        return (
            f"你是一位专业编辑。请润色以下文本。\n"
            f"提供3-5条具体、可操作的改进建议（如「将此被动动词改为主动」、「加强此描写」），使用简体中文。\n"
            f"然后，提供一个稍加润色的版本，使用简体中文。\n\n"
            f"待润色文本：\n'''\n{user_content}\n'''"
        )

    def evaluate_offline(self, mode: str, exercise_data: Dict, content: str) -> Dict[str, Any]:
        return LocalTrainingScorer.evaluate(mode, exercise_data, content)

    def get_offline_starter(self, mode: str) -> str:
        """为离线模式提供静态开头。"""
        if mode == "show_dont_tell":
            options = [
                "他很生气。",
                "房间很乱。",
                "她感到悲伤。",
                "那是寒冷的一天。",
                "食物很难吃。",
                "他是个有钱人。",
                "花园很美。"
            ]
            return random.choice(options)
        elif mode == "editing":
            options = [
                "有很多人正在那条非常繁忙的街道上行走着。",
                "他非常非常快速地跑向了商店。",
                "太阳正在落下，看起来非常非常美丽。",
                "她对他说，「我不去了，」她说道。",
                "众所周知的事实是，他是一个喜欢吃食物的人。"
            ]
            return random.choice(options)
        elif mode == "continuation":
            options = [
                "午夜时分，电话响了。",
                "她打开盒子，倒吸一口凉气。",
                "门从外面被锁住了。",
                "那本该是平凡的周二。",
                "他在口袋里发现了一把不属于他的钥匙。"
            ]
            return random.choice(options)
        elif mode == "emotion_infusion":
            options = [
                "他走进了房间。",
                "外面正在下雨。",
                "信放在桌上。",
                "她在等公交车。"
            ]
            return random.choice(options)
        elif mode == "dialogue_subtext":
            options = [
                "A想让B离开，但碍于礼貌不好直说。",
                "A怀疑B在撒谎，但假装相信。",
                "A爱慕B，却表现得很冷淡。"
            ]
            return random.choice(options)
        return ""


class LocalTrainingScorer:
    """当AI不可用时提供算法评分和反馈。"""

    @staticmethod
    def evaluate(mode: str, exercise_data: Dict, content: str) -> Dict[str, Any]:
        def estimate_idea_count(text: str) -> int:
            if not text:
                return 0

            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

            # Numbered/bulleted lines are the most reliable brainstorm structure.
            numbered = [
                ln for ln in lines
                if re.match(r"^(\d{1,2}[\.\、\)]|[（(]\d{1,2}[)）])", ln)
            ]
            bullets = [ln for ln in lines if re.match(r"^[-*•]", ln)]
            if numbered or bullets:
                return len(numbered) + len(bullets)

            # One idea per line.
            if len(lines) >= 2:
                return len(lines)

            # Inline numbering such as "1、... 2、..."
            inline_nums = re.findall(r"(?:^|\D)\d{1,2}[、\.)]", text)
            if len(inline_nums) >= 2:
                return len(inline_nums)

            # Fallback: split by semicolons
            parts = [p.strip() for p in re.split(r"[；;]", text) if p.strip()]
            if len(parts) >= 2:
                return len(parts)

            return 1

        words = TextMetrics.count_words(content)
        sentences = TextMetrics.count_sentences(content)
        avg_len = TextMetrics.get_avg_sentence_length(content)
        unique_terms = TextMetrics.count_unique_terms(content)

        # 基础分数计算（0-10分制）
        # 1. 篇幅分（超过200字得满分10分）
        volume_score = min(10, words / 20)

        # 2. 复杂度分（词汇丰富度）
        vocab_ratio = unique_terms / words if words > 0 else 0
        complexity_score = min(10, vocab_ratio * 15)

        # 3. 结构分（句子多样性）
        # 理想平均句长约15-20字
        # 如果平均<5（太短）或>40（太长），扣分
        structure_score = 10 - min(10, abs(avg_len - 15) / 2)

        # 模式特定调整
        mode_feedback = []
        bonus_points = 0

        if mode == "keywords":
            target_words = exercise_data.get("words", [])
            hit_count = 0
            content_lower = content.lower()
            for w in target_words:
                # 基本检查：移除括号内的英文
                clean_w = w.split('（')[0].split('(')[0].strip().lower()
                if clean_w in content_lower:
                    hit_count += 1

            hit_rate = hit_count / len(target_words) if target_words else 0
            bonus_points = hit_rate * 5  # 最多5分加成
            mode_feedback.append(f"关键词使用：{hit_count}/{len(target_words)}")
            if hit_count == len(target_words):
                mode_feedback.append("关键词整合完美！")

        elif mode == "show_dont_tell":
            telling = exercise_data.get("telling", "")
            if len(content) > len(telling) * 2:
                bonus_points = 2
                mode_feedback.append("扩写良好！你添加了大量细节。")
            elif len(content) < len(telling):
                mode_feedback.append("警告：你的改写比原文更短。是否添加了足够的感官细节？")
            sensory_hits = sum(1 for w in ["光", "影", "风", "声", "气味", "香", "苦", "凉", "热", "触", "粗糙", "柔软"] if w in content)
            if sensory_hits >= 2:
                bonus_points += 1
                mode_feedback.append("感官描写较丰富。")

        elif mode == "editing":
            original = exercise_data.get("telling", "")
            if len(content) < len(original):
                bonus_points = 3
                mode_feedback.append("精简文本做得好。")
            else:
                mode_feedback.append("提示：尝试更加精炼。")
            if original:
                adverbs = ["非常", "十分", "极其", "很", "有点"]
                original_hits = sum(original.count(w) for w in adverbs)
                new_hits = sum(content.count(w) for w in adverbs)
                if new_hits < original_hits:
                    bonus_points += 1
                    mode_feedback.append("冗余修饰语有所减少。")

        elif mode == "emotion_infusion":
            emotion = exercise_data.get("emotion", "")
            if emotion and any(token in content for token in emotion.split("/")):
                bonus_points += 2
                mode_feedback.append("目标情感有明显呈现。")

        elif mode == "brainstorm":
            idea_count = estimate_idea_count(content)
            volume_score = min(10, idea_count)

            vocab_ratio = unique_terms / words if words > 0 else 0
            complexity_score = min(10, vocab_ratio * 18)

            if idea_count >= 10:
                structure_score = 9
                bonus_points += 2
            elif idea_count >= 8:
                structure_score = 8
                bonus_points += 1
            elif idea_count >= 5:
                structure_score = 6
            elif idea_count >= 3:
                structure_score = 4
            else:
                structure_score = 2

            mode_feedback.append(f"点子数量：{idea_count}")
            if idea_count < 5:
                mode_feedback.append("点子偏少，建议扩展到8-10个以提升多样性。")
            if vocab_ratio < 0.25 and words > 20:
                mode_feedback.append("用词重复偏多，尝试扩大意象范围。")

        elif mode in ("dialogue_subtext", "character_voice"):
            dialogue_lines = [line for line in content.splitlines() if "：" in line]
            if len(dialogue_lines) >= 2:
                bonus_points += 2
                mode_feedback.append("对话形式清晰。")
            speakers = set(line.split("：")[0].strip() for line in dialogue_lines if "：" in line)
            if len(speakers) >= 2:
                bonus_points += 1
                mode_feedback.append("角色声音区分较明显。")

        elif mode == "character_persona":
            needed = ["姓名", "年龄", "背景", "目标", "缺陷"]
            hit = sum(1 for item in needed if item in content)
            if hit >= 3:
                bonus_points += 2
                mode_feedback.append("角色档案结构完整度较高。")

        elif mode == "character_arc":
            cues = ["伏笔", "过去", "前史", "曾经", "原因"]
            if any(cue in content for cue in cues):
                bonus_points += 2
                mode_feedback.append("伏笔/前史线索较明确。")

        total_raw = (volume_score + complexity_score + structure_score + bonus_points)
        # 归一化到大约30分
        final_score = min(30, int(total_raw))

        labels_by_mode = {
            "keywords": ("关键词运用", "词汇丰富度", "结构与流畅"),
            "brainstorm": ("点子数量", "多样性", "表达清晰"),
            "style": ("风格贴合", "词汇控制", "结构与节奏"),
            "continuation": ("衔接度", "情节推进", "创意"),
            "show_dont_tell": ("画面感", "细节密度", "表达流畅"),
            "editing": ("精简度", "可读性", "表达准确"),
            "sensory": ("感官投入", "描写层次", "节奏"),
            "emotion_infusion": ("情感传达", "语言强度", "连贯性"),
            "dialogue_subtext": ("潜台词", "对白自然度", "节奏"),
            "character_voice": ("角色区分", "对白一致性", "表现力"),
            "character_persona": ("人物立体度", "设定完整度", "一致性"),
            "character_arc": ("反应可信度", "伏笔合理性", "层次")
        }
        label_1, label_2, label_3 = labels_by_mode.get(mode, ("创意", "表达", "结构"))

        # 生成报告
        feedback = [
            f"=== 离线分析报告 ===",
            f"模式：{MODES.get(mode, mode)}",
            f"字数：{words}",
            f"平均句长：{avg_len:.1f}",
            "",
            "--- 评分（估算）---",
            f"{label_1}：{int(volume_score)}/10",
            f"{label_2}：{int(complexity_score)}/10",
            f"{label_3}：{int(structure_score)}/10",
            f"加分：{int(bonus_points)}",
            f"总分：{final_score}/30",
            "",
            "--- 反馈 ---"
        ]

        if mode != "brainstorm":
            if words < 50:
                feedback.append("- 考虑多写一些以充分展开主题。")
            if avg_len > 30:
                feedback.append("- 你的句子较长，注意避免病句。")
            elif avg_len < 5:
                feedback.append("- 你的句子非常短促，尝试组合一些想法。")

        feedback.extend(mode_feedback)
        feedback.append("\n（注：这是基础离线分析。启用AI可获得深度点评。）")

        scores = {
            "score_1": int(volume_score),
            "score_2": int(complexity_score),
            "score_3": int(structure_score),
            "total": final_score,
            "labels": {
                "score_1": label_1,
                "score_2": label_2,
                "score_3": label_3
            }
        }

        return {
            "scores": scores,
            "feedback": "\n".join(feedback)
        }
