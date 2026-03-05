from dataclasses import dataclass


@dataclass(frozen=True)
class ScaleMetrics:
    total_words: int
    scene_count: int
    outline_nodes: int


@dataclass(frozen=True)
class ScaleRecommendation:
    target_length: str
    reasons: list
    metrics: ScaleMetrics


SHORT_TO_LONG_WORDS_PRIMARY = 30000
SHORT_TO_LONG_WORDS = 20000
SHORT_TO_LONG_SCENES = 20
SHORT_TO_LONG_NODES = 50
SHORT_TO_LONG_MIN_SCORE = 2


def _count_outline_nodes(outline: dict) -> int:
    if not outline:
        return 0
    count = 0
    stack = list(outline.get("children", []))
    while stack:
        node = stack.pop()
        count += 1
        stack.extend(node.get("children", []))
    return count


def get_scale_metrics(project_data: dict) -> ScaleMetrics:
    script = project_data.get("script", {})
    scenes = script.get("scenes", [])
    total_words = 0
    for scene in scenes:
        total_words += len(scene.get("content", "").strip())

    outline_nodes = _count_outline_nodes(project_data.get("outline", {}))

    return ScaleMetrics(
        total_words=total_words,
        scene_count=len(scenes),
        outline_nodes=outline_nodes
    )


def recommend_scale(current_length: str, metrics: ScaleMetrics) -> ScaleRecommendation:
    if current_length != "Short":
        return None

    reasons = []
    score = 0

    if metrics.total_words >= SHORT_TO_LONG_WORDS_PRIMARY:
        reasons.append(f"字数已达 {metrics.total_words}")
        score = SHORT_TO_LONG_MIN_SCORE
    else:
        if metrics.total_words >= SHORT_TO_LONG_WORDS:
            reasons.append(f"字数 {metrics.total_words}")
            score += 1
        if metrics.scene_count >= SHORT_TO_LONG_SCENES:
            reasons.append(f"场景 {metrics.scene_count}")
            score += 1
        if metrics.outline_nodes >= SHORT_TO_LONG_NODES:
            reasons.append(f"大纲节点 {metrics.outline_nodes}")
            score += 1

    if score >= SHORT_TO_LONG_MIN_SCORE:
        return ScaleRecommendation(
            target_length="Long",
            reasons=reasons,
            metrics=metrics
        )

    return None
