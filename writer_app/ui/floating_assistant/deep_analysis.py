"""
悬浮助手 - 深度分析引擎 (Deep Analysis Engine)
提供写作风格分析、情感曲线、节奏分析、角色弧光等高级分析功能
"""
import re
import time
import json
import math
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum


class AnalysisLevel(Enum):
    """分析深度级别"""
    QUICK = "quick"       # 快速分析（基础指标）
    STANDARD = "standard" # 标准分析（常规深度）
    DEEP = "deep"         # 深度分析（全面分析）


@dataclass
class WritingStyleProfile:
    """写作风格档案"""
    # 基础指标
    avg_sentence_length: float = 0.0
    avg_paragraph_length: float = 0.0
    dialogue_ratio: float = 0.0
    description_ratio: float = 0.0
    action_ratio: float = 0.0

    # 词汇指标
    vocabulary_richness: float = 0.0  # 词汇丰富度 (unique words / total words)
    adjective_density: float = 0.0    # 形容词密度
    adverb_density: float = 0.0       # 副词密度
    verb_diversity: float = 0.0       # 动词多样性

    # 句式指标
    simple_sentence_ratio: float = 0.0  # 简单句比例
    complex_sentence_ratio: float = 0.0  # 复杂句比例
    question_ratio: float = 0.0         # 疑问句比例
    exclamation_ratio: float = 0.0      # 感叹句比例

    # 风格标签
    style_tags: List[str] = field(default_factory=list)


@dataclass
class EmotionalBeat:
    """情感节拍"""
    scene_index: int
    scene_name: str
    emotional_valence: float  # -1 到 1，负面到正面
    emotional_intensity: float  # 0 到 1，强度
    dominant_emotion: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class PacingAnalysis:
    """节奏分析结果"""
    avg_scene_length: float
    scene_length_variance: float
    transition_speed: str  # slow, medium, fast, erratic
    time_span_coverage: str  # compressed, normal, extended
    pacing_issues: List[str] = field(default_factory=list)


@dataclass
class CharacterArc:
    """角色弧光"""
    character_name: str
    arc_type: str  # positive, negative, flat, complex
    key_moments: List[Dict] = field(default_factory=list)
    presence_ratio: float = 0.0
    relationship_changes: List[Dict] = field(default_factory=list)
    growth_indicators: List[str] = field(default_factory=list)


@dataclass
class StructureAnalysis:
    """结构分析结果"""
    act_structure: str  # three-act, five-act, episodic, etc.
    plot_points: List[Dict] = field(default_factory=list)
    subplot_count: int = 0
    foreshadowing_items: List[Dict] = field(default_factory=list)
    unclosed_threads: List[str] = field(default_factory=list)


# 情感关键词词典
EMOTION_KEYWORDS = {
    "joy": ["开心", "高兴", "快乐", "欢喜", "兴奋", "愉快", "欣喜", "喜悦", "幸福", "甜蜜", "笑", "微笑"],
    "sadness": ["悲伤", "难过", "伤心", "哭", "泪", "痛苦", "绝望", "沮丧", "忧郁", "心碎", "失落", "孤独"],
    "anger": ["愤怒", "生气", "恼火", "暴怒", "怒", "吼", "咆哮", "愤恨", "气愤", "激动", "怨恨"],
    "fear": ["害怕", "恐惧", "恐慌", "惊恐", "担心", "忧虑", "紧张", "颤抖", "惊吓", "战栗", "不安"],
    "surprise": ["惊讶", "震惊", "意外", "惊奇", "吃惊", "愕然", "错愕", "目瞪口呆", "难以置信"],
    "disgust": ["厌恶", "反感", "恶心", "讨厌", "鄙视", "唾弃", "憎恶"],
    "anticipation": ["期待", "盼望", "渴望", "希望", "憧憬", "向往", "等待"],
    "trust": ["信任", "相信", "依赖", "信赖", "托付", "安心", "放心"],
    "tension": ["紧张", "压力", "焦虑", "窒息", "压抑", "沉重", "凝重", "肃杀"],
    "romance": ["爱", "喜欢", "心动", "脸红", "害羞", "暧昧", "温柔", "亲吻", "拥抱", "甜蜜"]
}

# 动作/叙述/对话识别模式
DIALOGUE_PATTERN = re.compile(r'[""「」『』【】].*?[""「」『』【】]|".*?"|「.*?」')
ACTION_KEYWORDS = ["走", "跑", "跳", "打", "拿", "放", "看", "听", "说", "喊", "转身", "站", "坐", "躺"]
DESCRIPTION_KEYWORDS = ["如同", "仿佛", "像", "般", "似", "宛如", "犹如", "恍若"]


class WritingStyleAnalyzer:
    """写作风格分析器"""

    def __init__(self):
        self.cache: Dict[str, WritingStyleProfile] = {}
        self.cache_time: Dict[str, float] = {}
        self.cache_ttl = 300  # 5分钟缓存

    def analyze(self, text: str, cache_key: Optional[str] = None) -> WritingStyleProfile:
        """
        分析文本的写作风格

        Args:
            text: 待分析文本
            cache_key: 缓存键

        Returns:
            写作风格档案
        """
        # 检查缓存
        if cache_key and cache_key in self.cache:
            if time.time() - self.cache_time.get(cache_key, 0) < self.cache_ttl:
                return self.cache[cache_key]

        profile = WritingStyleProfile()

        if not text or len(text) < 50:
            return profile

        # 分割句子和段落
        sentences = self._split_sentences(text)
        paragraphs = text.split("\n\n")

        if not sentences:
            return profile

        # 基础指标
        profile.avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
        profile.avg_paragraph_length = sum(len(p) for p in paragraphs) / max(1, len(paragraphs))

        # 对话/叙述/动作比例
        dialogue_chars = sum(len(m.group()) for m in DIALOGUE_PATTERN.finditer(text))
        total_chars = len(text)

        profile.dialogue_ratio = dialogue_chars / total_chars if total_chars > 0 else 0

        action_count = sum(text.count(kw) for kw in ACTION_KEYWORDS)
        desc_count = sum(text.count(kw) for kw in DESCRIPTION_KEYWORDS)
        total_keywords = action_count + desc_count + 1

        profile.action_ratio = action_count / total_keywords
        profile.description_ratio = desc_count / total_keywords

        # 词汇指标
        words = list(self._tokenize(text))
        if words:
            unique_words = set(words)
            profile.vocabulary_richness = len(unique_words) / len(words)

        # 句式指标
        question_count = sum(1 for s in sentences if s.endswith("？") or s.endswith("?"))
        exclamation_count = sum(1 for s in sentences if s.endswith("！") or s.endswith("!"))

        profile.question_ratio = question_count / len(sentences)
        profile.exclamation_ratio = exclamation_count / len(sentences)

        # 简单句/复杂句
        short_sentences = sum(1 for s in sentences if len(s) < 20)
        long_sentences = sum(1 for s in sentences if len(s) > 50)

        profile.simple_sentence_ratio = short_sentences / len(sentences)
        profile.complex_sentence_ratio = long_sentences / len(sentences)

        # 生成风格标签
        profile.style_tags = self._generate_style_tags(profile)

        # 缓存结果
        if cache_key:
            self.cache[cache_key] = profile
            self.cache_time[cache_key] = time.time()

        return profile

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 简单的句子分割
        sentences = re.split(r'[。！？.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _tokenize(self, text: str) -> List[str]:
        """简单分词（基于字符和标点）"""
        # 简单实现：按标点和空白分割
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
        return tokens

    def _generate_style_tags(self, profile: WritingStyleProfile) -> List[str]:
        """生成风格标签"""
        tags = []

        # 对话风格
        if profile.dialogue_ratio > 0.5:
            tags.append("对话驱动型")
        elif profile.dialogue_ratio < 0.2:
            tags.append("叙述主导型")

        # 句子风格
        if profile.avg_sentence_length > 40:
            tags.append("长句优美型")
        elif profile.avg_sentence_length < 15:
            tags.append("简洁利落型")

        # 词汇风格
        if profile.vocabulary_richness > 0.7:
            tags.append("词汇丰富型")
        elif profile.vocabulary_richness < 0.4:
            tags.append("朴素直白型")

        # 情感表达
        if profile.exclamation_ratio > 0.2:
            tags.append("情感充沛型")
        if profile.question_ratio > 0.15:
            tags.append("悬念设置型")

        # 动作/描写
        if profile.action_ratio > 0.6:
            tags.append("动作导向型")
        if profile.description_ratio > 0.4:
            tags.append("细腻描写型")

        return tags


class EmotionalCurveAnalyzer:
    """情感曲线分析器"""

    def __init__(self):
        self.emotion_weights = {
            "joy": 0.8, "trust": 0.5, "anticipation": 0.3, "romance": 0.7,
            "sadness": -0.7, "fear": -0.5, "anger": -0.6, "disgust": -0.8,
            "surprise": 0.1, "tension": -0.3
        }

    def analyze_scenes(self, scenes: List[Dict]) -> List[EmotionalBeat]:
        """
        分析场景序列的情感曲线

        Args:
            scenes: 场景列表，每个包含 name, content 等字段

        Returns:
            情感节拍列表
        """
        beats = []

        for i, scene in enumerate(scenes):
            content = scene.get("content", "")
            name = scene.get("name", f"场景{i+1}")

            if not content:
                continue

            beat = self._analyze_scene_emotion(i, name, content)
            beats.append(beat)

        return beats

    def _analyze_scene_emotion(self, index: int, name: str, content: str) -> EmotionalBeat:
        """分析单个场景的情感"""
        emotion_scores: Dict[str, int] = defaultdict(int)
        keywords_found: List[str] = []

        # 统计情感关键词
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for kw in keywords:
                count = content.count(kw)
                if count > 0:
                    emotion_scores[emotion] += count
                    keywords_found.append(kw)

        # 计算情感效价和强度
        total_score = sum(emotion_scores.values())
        if total_score == 0:
            return EmotionalBeat(
                scene_index=index,
                scene_name=name,
                emotional_valence=0.0,
                emotional_intensity=0.0,
                dominant_emotion="neutral",
                keywords=[]
            )

        # 加权情感效价
        valence = sum(
            self.emotion_weights.get(emotion, 0) * count / total_score
            for emotion, count in emotion_scores.items()
        )

        # 情感强度（关键词密度）
        intensity = min(1.0, total_score / (len(content) / 100 + 1))

        # 主导情感
        dominant = max(emotion_scores.items(), key=lambda x: x[1])[0] if emotion_scores else "neutral"

        return EmotionalBeat(
            scene_index=index,
            scene_name=name,
            emotional_valence=valence,
            emotional_intensity=intensity,
            dominant_emotion=dominant,
            keywords=keywords_found[:10]
        )

    def get_curve_summary(self, beats: List[EmotionalBeat]) -> Dict[str, Any]:
        """获取情感曲线摘要"""
        if not beats:
            return {"status": "no_data"}

        valences = [b.emotional_valence for b in beats]
        intensities = [b.emotional_intensity for b in beats]

        # 计算统计指标
        avg_valence = sum(valences) / len(valences)
        valence_variance = sum((v - avg_valence) ** 2 for v in valences) / len(valences)
        avg_intensity = sum(intensities) / len(intensities)

        # 识别高潮点
        climax_indices = [
            i for i, b in enumerate(beats)
            if b.emotional_intensity > 0.7 or abs(b.emotional_valence) > 0.6
        ]

        # 情感变化趋势
        if len(valences) >= 3:
            first_third = sum(valences[:len(valences)//3]) / (len(valences)//3 or 1)
            last_third = sum(valences[-len(valences)//3:]) / (len(valences)//3 or 1)
            trend = "ascending" if last_third > first_third + 0.2 else \
                   "descending" if last_third < first_third - 0.2 else "stable"
        else:
            trend = "insufficient_data"

        return {
            "avg_valence": avg_valence,
            "valence_variance": valence_variance,
            "avg_intensity": avg_intensity,
            "climax_count": len(climax_indices),
            "climax_positions": climax_indices,
            "trend": trend,
            "is_flat": valence_variance < 0.1,
            "is_turbulent": valence_variance > 0.5,
        }

    def detect_issues(self, beats: List[EmotionalBeat]) -> List[str]:
        """检测情感曲线问题"""
        issues = []
        summary = self.get_curve_summary(beats)

        if summary.get("is_flat"):
            issues.append("情感曲线过于平淡，缺乏波动，考虑增加冲突或情感转折")

        if summary.get("climax_count", 0) == 0 and len(beats) > 5:
            issues.append("未检测到明显的情感高潮点，故事可能缺乏张力")

        if len(beats) > 10 and summary.get("climax_count", 0) > len(beats) * 0.4:
            issues.append("高潮点过多，可能导致读者疲劳，建议适当放缓节奏")

        # 检查连续相同情感
        if len(beats) >= 5:
            for i in range(len(beats) - 4):
                window = beats[i:i+5]
                if all(b.dominant_emotion == window[0].dominant_emotion for b in window):
                    issues.append(f"场景{i+1}到{i+5}情感单一，考虑增加变化")
                    break

        return issues


class PacingAnalyzer:
    """节奏分析器"""

    def analyze(self, scenes: List[Dict]) -> PacingAnalysis:
        """分析故事节奏"""
        if not scenes:
            return PacingAnalysis(
                avg_scene_length=0,
                scene_length_variance=0,
                transition_speed="unknown",
                time_span_coverage="unknown"
            )

        lengths = [len(scene.get("content", "")) for scene in scenes]

        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)

        # 判断过渡速度
        short_scenes = sum(1 for l in lengths if l < 200)
        long_scenes = sum(1 for l in lengths if l > 2000)

        if short_scenes > len(lengths) * 0.6:
            transition_speed = "fast"
        elif long_scenes > len(lengths) * 0.4:
            transition_speed = "slow"
        elif variance > 500000:  # 高方差
            transition_speed = "erratic"
        else:
            transition_speed = "medium"

        # 时间跨度（基于场景时间标签）
        time_span = self._analyze_time_span(scenes)

        # 检测问题
        issues = self._detect_pacing_issues(lengths, transition_speed)

        return PacingAnalysis(
            avg_scene_length=avg_length,
            scene_length_variance=variance,
            transition_speed=transition_speed,
            time_span_coverage=time_span,
            pacing_issues=issues
        )

    def _analyze_time_span(self, scenes: List[Dict]) -> str:
        """分析时间跨度覆盖"""
        time_markers = []
        time_keywords = {
            "instant": ["同时", "此刻", "瞬间", "立刻"],
            "short": ["几分钟", "片刻", "一会儿", "稍后"],
            "medium": ["几小时", "当天", "那天", "傍晚", "晚上", "清晨"],
            "long": ["第二天", "几天后", "一周", "几周"],
            "extended": ["一个月", "几个月", "一年", "多年"]
        }

        for scene in scenes:
            content = scene.get("content", "") + scene.get("time", "")
            for span_type, keywords in time_keywords.items():
                if any(kw in content for kw in keywords):
                    time_markers.append(span_type)
                    break

        if not time_markers:
            return "unknown"

        # 根据标记分布判断
        marker_counts = Counter(time_markers)
        most_common = marker_counts.most_common(1)[0][0]

        if most_common in ["instant", "short"]:
            return "compressed"
        elif most_common in ["extended"]:
            return "extended"
        else:
            return "normal"

    def _detect_pacing_issues(self, lengths: List[int], speed: str) -> List[str]:
        """检测节奏问题"""
        issues = []

        if speed == "fast":
            issues.append("整体节奏偏快，场景普遍较短，可能导致读者难以沉浸")

        if speed == "slow":
            issues.append("整体节奏偏慢，场景普遍较长，可能导致读者失去耐心")

        if speed == "erratic":
            issues.append("场景长度差异过大，节奏不稳定，考虑调整场景划分")

        # 检查开头和结尾
        if lengths and lengths[0] > 3000:
            issues.append("开场场景过长，可能影响读者代入感")

        if len(lengths) > 3 and all(l < 300 for l in lengths[-3:]):
            issues.append("结尾三个场景都很短，可能显得仓促")

        return issues


class CharacterArcAnalyzer:
    """角色弧光分析器"""

    def analyze(self, characters: List[Dict], scenes: List[Dict],
               relationships: Optional[List[Dict]] = None) -> List[CharacterArc]:
        """分析角色弧光"""
        arcs = []

        for char in characters:
            char_name = char.get("name", "")
            if not char_name:
                continue

            arc = self._analyze_character_arc(char_name, char, scenes, relationships or [])
            arcs.append(arc)

        return arcs

    def _analyze_character_arc(self, name: str, char_data: Dict,
                               scenes: List[Dict], relationships: List[Dict]) -> CharacterArc:
        """分析单个角色的弧光"""
        # 计算出场比例
        appearances = 0
        key_moments = []

        for i, scene in enumerate(scenes):
            scene_chars = scene.get("characters", [])
            content = scene.get("content", "")

            if name in scene_chars or name in content:
                appearances += 1

                # 检测关键时刻
                if self._is_key_moment(name, content):
                    key_moments.append({
                        "scene_index": i,
                        "scene_name": scene.get("name", ""),
                        "type": self._detect_moment_type(content)
                    })

        presence_ratio = appearances / len(scenes) if scenes else 0

        # 判断弧光类型
        arc_type = self._determine_arc_type(char_data, key_moments, scenes)

        # 分析关系变化
        relationship_changes = self._analyze_relationship_changes(name, relationships)

        # 成长指标
        growth_indicators = self._detect_growth_indicators(name, scenes)

        return CharacterArc(
            character_name=name,
            arc_type=arc_type,
            key_moments=key_moments,
            presence_ratio=presence_ratio,
            relationship_changes=relationship_changes,
            growth_indicators=growth_indicators
        )

    def _is_key_moment(self, char_name: str, content: str) -> bool:
        """判断是否是角色的关键时刻"""
        key_indicators = [
            "决定", "选择", "终于", "第一次", "意识到", "明白了",
            "改变", "放弃", "坚持", "勇敢", "面对", "承认",
            "秘密", "真相", "转折", "突破"
        ]
        return any(kw in content for kw in key_indicators)

    def _detect_moment_type(self, content: str) -> str:
        """检测关键时刻类型"""
        if any(kw in content for kw in ["决定", "选择", "放弃"]):
            return "decision"
        if any(kw in content for kw in ["真相", "秘密", "发现"]):
            return "revelation"
        if any(kw in content for kw in ["改变", "成长", "明白"]):
            return "growth"
        if any(kw in content for kw in ["冲突", "对抗", "争吵"]):
            return "conflict"
        return "general"

    def _determine_arc_type(self, char_data: Dict, key_moments: List[Dict],
                           scenes: List[Dict]) -> str:
        """判断弧光类型"""
        if len(key_moments) < 2:
            return "flat"

        moment_types = [m["type"] for m in key_moments]

        if moment_types.count("growth") >= 2:
            return "positive"
        if moment_types.count("conflict") > moment_types.count("growth"):
            return "negative"
        if len(set(moment_types)) >= 3:
            return "complex"

        return "flat"

    def _analyze_relationship_changes(self, char_name: str,
                                      relationships: List[Dict]) -> List[Dict]:
        """分析关系变化"""
        changes = []
        for rel in relationships:
            if char_name in [rel.get("from"), rel.get("to")]:
                changes.append({
                    "partner": rel.get("to") if rel.get("from") == char_name else rel.get("from"),
                    "relation_type": rel.get("type", "unknown"),
                    "label": rel.get("label", "")
                })
        return changes

    def _detect_growth_indicators(self, char_name: str, scenes: List[Dict]) -> List[str]:
        """检测成长指标"""
        indicators = []
        growth_keywords = {
            "courage": ["勇敢", "勇气", "鼓起", "面对"],
            "wisdom": ["明白", "理解", "领悟", "懂得"],
            "trust": ["相信", "信任", "依靠", "托付"],
            "acceptance": ["接受", "承认", "放下", "释然"],
            "independence": ["独立", "自己", "不再依赖", "成长"]
        }

        for scene in scenes:
            content = scene.get("content", "")
            if char_name not in content:
                continue

            for indicator, keywords in growth_keywords.items():
                if any(kw in content for kw in keywords):
                    if indicator not in indicators:
                        indicators.append(indicator)

        return indicators


class StructureAnalyzer:
    """结构分析器"""

    def analyze(self, scenes: List[Dict], outline: Optional[Dict] = None) -> StructureAnalysis:
        """分析故事结构"""
        analysis = StructureAnalysis()

        if not scenes:
            return analysis

        # 分析幕结构
        analysis.act_structure = self._detect_act_structure(scenes)

        # 识别情节点
        analysis.plot_points = self._identify_plot_points(scenes)

        # 统计支线
        analysis.subplot_count = self._count_subplots(scenes, outline)

        # 检测伏笔
        analysis.foreshadowing_items = self._detect_foreshadowing(scenes)

        # 检测未闭合的线索
        analysis.unclosed_threads = self._find_unclosed_threads(scenes)

        return analysis

    def _detect_act_structure(self, scenes: List[Dict]) -> str:
        """检测幕结构"""
        n = len(scenes)

        if n < 5:
            return "minimal"

        # 基于场景内容分析结构
        # 简化处理：根据场景数量和关键词判断

        setup_keywords = ["开始", "第一次", "来到", "出发", "认识"]
        climax_keywords = ["高潮", "决战", "对决", "真相", "揭露", "爆发"]
        resolution_keywords = ["结束", "最后", "终于", "从此", "再见"]

        setup_count = sum(1 for s in scenes[:n//3]
                        if any(kw in s.get("content", "") for kw in setup_keywords))
        climax_count = sum(1 for s in scenes[n//3:2*n//3]
                         if any(kw in s.get("content", "") for kw in climax_keywords))
        resolution_count = sum(1 for s in scenes[2*n//3:]
                              if any(kw in s.get("content", "") for kw in resolution_keywords))

        if setup_count > 0 and climax_count > 0 and resolution_count > 0:
            return "three-act"
        elif n > 20:
            return "episodic"
        else:
            return "linear"

    def _identify_plot_points(self, scenes: List[Dict]) -> List[Dict]:
        """识别情节点"""
        plot_points = []

        plot_keywords = {
            "inciting_incident": ["突然", "意外", "发现", "打破"],
            "first_plot_point": ["决定", "踏上", "开始", "必须"],
            "midpoint": ["真相", "转变", "意识到"],
            "second_plot_point": ["危机", "绝望", "最后的", "唯一的"],
            "climax": ["决战", "对决", "最终", "高潮"],
            "resolution": ["结束", "从此", "终于", "再见"]
        }

        for i, scene in enumerate(scenes):
            content = scene.get("content", "")
            for point_type, keywords in plot_keywords.items():
                if any(kw in content for kw in keywords):
                    plot_points.append({
                        "type": point_type,
                        "scene_index": i,
                        "scene_name": scene.get("name", "")
                    })
                    break

        return plot_points

    def _count_subplots(self, scenes: List[Dict], outline: Optional[Dict]) -> int:
        """统计支线数量"""
        if outline:
            # 从大纲中统计
            children = outline.get("children", [])
            return max(0, len(children) - 1)  # 假设第一个是主线

        # 简单估算：基于场景分组
        return 0

    def _detect_foreshadowing(self, scenes: List[Dict]) -> List[Dict]:
        """检测伏笔"""
        foreshadowing_patterns = [
            r"(?:后来|之后|将来|日后).*?(?:才|就|便)",
            r"(?:殊不知|却不知|谁能想到)",
            r"(?:这是.*?第一次|这将是.*?最后)",
            r"(?:如果.*?知道.*?的话)"
        ]

        items = []
        for i, scene in enumerate(scenes):
            content = scene.get("content", "")
            for pattern in foreshadowing_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    items.append({
                        "scene_index": i,
                        "scene_name": scene.get("name", ""),
                        "hint": match[:50]
                    })

        return items

    def _find_unclosed_threads(self, scenes: List[Dict]) -> List[str]:
        """查找未闭合的线索"""
        threads = []

        # 检测悬念设置但未回收
        suspense_keywords = ["之谜", "秘密", "真相", "谜团", "未解"]
        resolution_keywords = ["原来", "终于明白", "真相是", "谜底"]

        for scene in scenes[:-3]:  # 不检查最后几个场景
            content = scene.get("content", "")
            for kw in suspense_keywords:
                if kw in content:
                    # 检查后续是否有解答
                    resolved = False
                    for later_scene in scenes[scenes.index(scene)+1:]:
                        later_content = later_scene.get("content", "")
                        if any(rkw in later_content for rkw in resolution_keywords):
                            resolved = True
                            break

                    if not resolved:
                        threads.append(f"场景「{scene.get('name', '')}」中的{kw}可能未被回收")

        return threads[:5]  # 限制数量


class DeepAnalysisEngine:
    """深度分析引擎：整合所有分析功能"""

    def __init__(self, data_dir: Optional[str] = None):
        self.style_analyzer = WritingStyleAnalyzer()
        self.emotion_analyzer = EmotionalCurveAnalyzer()
        self.pacing_analyzer = PacingAnalyzer()
        self.character_analyzer = CharacterArcAnalyzer()
        self.structure_analyzer = StructureAnalyzer()

        self.data_dir = Path(data_dir) if data_dir else None
        self._cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl = 300  # 5分钟

    def analyze(self, project_data: Dict,
               level: AnalysisLevel = AnalysisLevel.STANDARD) -> Dict[str, Any]:
        """
        执行全面分析

        Args:
            project_data: 项目数据
            level: 分析深度级别

        Returns:
            分析结果字典
        """
        # 检查缓存
        cache_key = f"{hash(json.dumps(project_data, sort_keys=True, default=str))}"
        if self._cache.get("key") == cache_key and time.time() - self._cache_time < self._cache_ttl:
            return self._cache.get("result", {})

        result = {}
        script = project_data.get("script", {})
        scenes = script.get("scenes", [])
        characters = script.get("characters", [])
        relationships = project_data.get("relationships", {})
        outline = project_data.get("outline", {})

        # 合并所有场景内容用于风格分析
        all_text = "\n\n".join(s.get("content", "") for s in scenes)

        # 快速分析（始终执行）
        result["style"] = self.style_analyzer.analyze(all_text)

        if level in [AnalysisLevel.STANDARD, AnalysisLevel.DEEP]:
            # 情感曲线
            result["emotional_beats"] = self.emotion_analyzer.analyze_scenes(scenes)
            result["emotional_summary"] = self.emotion_analyzer.get_curve_summary(result["emotional_beats"])
            result["emotional_issues"] = self.emotion_analyzer.detect_issues(result["emotional_beats"])

            # 节奏分析
            result["pacing"] = self.pacing_analyzer.analyze(scenes)

        if level == AnalysisLevel.DEEP:
            # 角色弧光
            rel_links = relationships.get("links", [])
            result["character_arcs"] = self.character_analyzer.analyze(characters, scenes, rel_links)

            # 结构分析
            result["structure"] = self.structure_analyzer.analyze(scenes, outline)

        # 生成综合问题列表
        result["all_issues"] = self._compile_issues(result)

        # 生成改进建议
        result["suggestions"] = self._generate_suggestions(result)

        # 缓存结果
        self._cache = {"key": cache_key, "result": result}
        self._cache_time = time.time()

        return result

    def _compile_issues(self, analysis: Dict) -> List[Dict]:
        """汇总所有问题"""
        issues = []

        # 情感问题
        for issue in analysis.get("emotional_issues", []):
            issues.append({"category": "emotion", "message": issue, "severity": "medium"})

        # 节奏问题
        pacing = analysis.get("pacing")
        if pacing:
            for issue in pacing.pacing_issues:
                issues.append({"category": "pacing", "message": issue, "severity": "medium"})

        # 结构问题
        structure = analysis.get("structure")
        if structure:
            for thread in structure.unclosed_threads:
                issues.append({"category": "structure", "message": thread, "severity": "low"})

        # 角色问题
        for arc in analysis.get("character_arcs", []):
            if arc.arc_type == "flat" and arc.presence_ratio > 0.3:
                issues.append({
                    "category": "character",
                    "message": f"角色「{arc.character_name}」出场较多但缺乏明显成长弧线",
                    "severity": "medium"
                })

        return issues

    def _generate_suggestions(self, analysis: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于风格的建议
        style = analysis.get("style")
        if style:
            if style.dialogue_ratio < 0.15:
                suggestions.append("对话比例较低，可以考虑增加角色对话来推进剧情")
            if style.vocabulary_richness < 0.4:
                suggestions.append("词汇重复率较高，可以尝试使用同义词替换")
            if style.avg_sentence_length > 50:
                suggestions.append("句子普遍较长，适当分割可以提高可读性")

        # 基于情感的建议
        emotional_summary = analysis.get("emotional_summary", {})
        if emotional_summary.get("is_flat"):
            suggestions.append("情感曲线较为平淡，考虑在关键节点增加冲突或情感爆发")

        # 基于节奏的建议
        pacing = analysis.get("pacing")
        if pacing and pacing.transition_speed == "erratic":
            suggestions.append("场景节奏不够稳定，建议统一调整场景长度分布")

        # 基于结构的建议
        structure = analysis.get("structure")
        if structure and len(structure.unclosed_threads) > 2:
            suggestions.append("存在多个未回收的伏笔，注意在后续章节中进行呼应")

        return suggestions[:5]  # 限制建议数量

    def get_quick_insights(self, project_data: Dict) -> List[str]:
        """获取快速洞察（用于实时反馈）"""
        insights = []

        result = self.analyze(project_data, AnalysisLevel.QUICK)
        style = result.get("style")

        if style:
            insights.extend(style.style_tags[:3])

        return insights
