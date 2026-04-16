import copy
from typing import Any, Callable, Dict, List


DEFAULT_PLOT_LINE_UID = "plot-main"
DEFAULT_PLOT_SEGMENT_UID = "plot-main-segment"
DEFAULT_PLOT_LINE_COLOR = "#2563EB"
DEFAULT_SEGMENT_CURVE = 0.35
DEFAULT_INTERACTION_TYPE = "solid_single"
DEFAULT_NODE_TYPE = "normal"
DEFAULT_NOTE_TYPE = "plot"
INTERACTION_TYPE_LABELS = {
    "solid_single": "实线单箭头",
    "dashed_single": "虚线单箭头",
    "solid_opposed_double": "实线对立双箭头",
    "dashed_facing_double": "虚线相向双箭头",
    "solid_reverse_double": "实线相反双箭头",
    "dashed_reverse_double": "虚线相反双箭头",
}
INTERACTION_TYPE_TONES = {
    "solid_single": "压制",
    "dashed_single": "和解",
    "solid_opposed_double": "压制",
    "dashed_facing_double": "和解",
    "solid_reverse_double": "压制",
    "dashed_reverse_double": "和解",
}
CHARACTER_LINE_COLORS = [
    "#E11D48",
    "#059669",
    "#7C3AED",
    "#EA580C",
    "#0891B2",
    "#CA8A04",
]
NODE_TYPE_LABELS = {
    "normal": "普通节点",
    "climax": "高潮节点",
    "turning": "转折节点",
    "intro": "引入节点",
    "converge": "收束节点",
    "conflict": "冲突节点",
    "reconcile": "和解节点",
    "echo": "对应节点",
}
NOTE_TYPE_LABELS = {
    "plot": "情节说明",
    "character": "人物说明",
    "relationship": "关系说明",
    "foreshadow": "伏笔说明",
    "conclusion": "结论说明",
}


def _normalize_flag(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"0", "false", "no", "off", ""}:
            return False
        if lowered in {"1", "true", "yes", "on"}:
            return True
    if value is None:
        return default
    return bool(value)


def _normalize_choice(value: Any, options: Dict[str, str], default: str) -> str:
    normalized = str(value or "").strip()
    if normalized in options:
        return normalized
    return default


def _normalize_tags(value: Any) -> List[str]:
    if isinstance(value, str):
        raw_items = value.replace("，", ",").split(",")
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = []

    normalized: List[str] = []
    seen: set[str] = set()
    for item in raw_items:
        tag = str(item or "").strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized


def create_default_tone_outline() -> Dict[str, Any]:
    return {
        "version": 4,
        "axis_nodes": [],
        "interactions": [],
        "lines": [
            {
                "uid": DEFAULT_PLOT_LINE_UID,
                "name": "情节线",
                "line_type": "plot",
                "character_name": "",
                "color": DEFAULT_PLOT_LINE_COLOR,
                "visible": True,
                "segments": [
                    {
                        "uid": DEFAULT_PLOT_SEGMENT_UID,
                        "start_axis_uid": "",
                        "end_axis_uid": "",
                        "start_curve": DEFAULT_SEGMENT_CURVE,
                        "end_curve": DEFAULT_SEGMENT_CURVE,
                        "title": "",
                        "description": "",
                        "note_type": DEFAULT_NOTE_TYPE,
                        "points": [],
                    }
                ],
            }
        ],
    }


def clone_tone_outline(data: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(data or create_default_tone_outline())


def build_axis_nodes_from_scenes(
    scenes: List[Dict[str, Any]],
    uid_generator: Callable[[], str],
) -> List[Dict[str, Any]]:
    axis_nodes = []
    for index, scene in enumerate(scenes):
        title = (scene.get("name") or f"场景 {index + 1}").strip()
        description = (scene.get("content") or "").strip()
        if len(description) > 90:
            description = description[:87] + "..."
        axis_nodes.append(
            {
                "uid": uid_generator(),
                "title": title,
                "description": description,
            }
        )
    return axis_nodes


def get_next_tone_line_color(lines: List[Dict[str, Any]]) -> str:
    used = {
        (line or {}).get("color")
        for line in (lines or [])
        if (line or {}).get("line_type") == "character"
    }
    for color in CHARACTER_LINE_COLORS:
        if color not in used:
            return color
    return CHARACTER_LINE_COLORS[len(used) % len(CHARACTER_LINE_COLORS)]


def get_axis_index_map(data: Dict[str, Any]) -> Dict[str, int]:
    return {
        axis.get("uid"): index
        for index, axis in enumerate((data or {}).get("axis_nodes", []))
        if axis.get("uid")
    }


def _axis_range_text(axis_map: Dict[str, Dict[str, Any]], start_uid: str, end_uid: str) -> str:
    start_name = axis_map.get(start_uid, {}).get("title", "未设置")
    if not end_uid:
        return f"{start_name} -> 进行中"
    end_name = axis_map.get(end_uid, {}).get("title", "未设置")
    return f"{start_name} -> {end_name}"


def _normalize_curve(value: Any, default: float = DEFAULT_SEGMENT_CURVE) -> float:
    try:
        return max(0.1, min(1.5, float(value)))
    except (TypeError, ValueError):
        return default


def _normalize_point(
    node: Dict[str, Any],
    uid_prefix: str,
    point_index: int,
    axis_index_map: Dict[str, int],
    seen_point_uids: set[str],
    uid_generator: Callable[[], str] | None,
) -> Dict[str, Any] | None:
    if not isinstance(node, dict):
        return None
    axis_uid = node.get("axis_uid")
    if axis_uid not in axis_index_map:
        return None
    point_uid = node.get("uid") or (
        uid_generator() if uid_generator else f"{uid_prefix}-point-{point_index + 1}"
    )
    if point_uid in seen_point_uids:
        point_uid = uid_generator() if uid_generator else f"{point_uid}-{point_index + 1}"
    seen_point_uids.add(point_uid)
    amplitude = node.get("amplitude", 0)
    curvature = node.get("curvature", 0.45)
    try:
        amplitude = max(-100.0, min(100.0, float(amplitude)))
    except (TypeError, ValueError):
        amplitude = 0.0
    try:
        curvature = max(0.1, min(1.5, float(curvature)))
    except (TypeError, ValueError):
        curvature = 0.45
    return {
        "uid": point_uid,
        "axis_uid": axis_uid,
        "amplitude": amplitude,
        "curvature": curvature,
        "label": node.get("label") or "",
        "description": node.get("description") or "",
        "node_type": _normalize_choice(
            node.get("node_type"),
            NODE_TYPE_LABELS,
            DEFAULT_NODE_TYPE,
        ),
        "note_type": _normalize_choice(
            node.get("note_type"),
            NOTE_TYPE_LABELS,
            DEFAULT_NOTE_TYPE,
        ),
        "tags": _normalize_tags(node.get("tags")),
    }


def _sort_points(points: List[Dict[str, Any]], axis_index_map: Dict[str, int]) -> None:
    points.sort(key=lambda item: axis_index_map.get(item.get("axis_uid"), 0))


def _normalize_point_list(
    raw_points: Any,
    uid_prefix: str,
    axis_index_map: Dict[str, int],
    uid_generator: Callable[[], str] | None,
) -> List[Dict[str, Any]]:
    if not isinstance(raw_points, list):
        raw_points = []

    normalized = []
    seen_point_uids: set[str] = set()
    seen_axes: set[str] = set()
    for point_index, node in enumerate(raw_points):
        normalized_point = _normalize_point(
            node,
            uid_prefix,
            point_index,
            axis_index_map,
            seen_point_uids,
            uid_generator,
        )
        if not normalized_point:
            continue
        axis_uid = normalized_point.get("axis_uid")
        if axis_uid in seen_axes:
            continue
        seen_axes.add(axis_uid)
        normalized.append(normalized_point)
    _sort_points(normalized, axis_index_map)
    return normalized


def axis_in_segment(
    axis_uid: str,
    segment: Dict[str, Any],
    axis_index_map: Dict[str, int],
    last_axis_uid: str = "",
) -> bool:
    if axis_uid not in axis_index_map:
        return False
    start_uid = segment.get("start_axis_uid")
    if start_uid not in axis_index_map:
        return False
    end_uid = segment.get("end_axis_uid") or last_axis_uid
    if end_uid not in axis_index_map:
        end_uid = last_axis_uid
    if end_uid not in axis_index_map:
        return False
    start_idx = axis_index_map[start_uid]
    end_idx = axis_index_map[end_uid]
    if end_idx < start_idx:
        start_idx, end_idx = end_idx, start_idx
    current_idx = axis_index_map[axis_uid]
    return start_idx <= current_idx <= end_idx


def _assign_legacy_points_to_segments(
    segments: List[Dict[str, Any]],
    legacy_points: List[Dict[str, Any]],
    axis_index_map: Dict[str, int],
    last_axis_uid: str,
) -> None:
    for point in legacy_points:
        axis_uid = point.get("axis_uid")
        for segment in segments:
            if not axis_in_segment(axis_uid, segment, axis_index_map, last_axis_uid=last_axis_uid):
                continue
            existing_axes = {item.get("axis_uid") for item in segment.get("points", [])}
            if axis_uid not in existing_axes:
                segment.setdefault("points", []).append(point)
                _sort_points(segment["points"], axis_index_map)
            break


def _normalize_plot_segments(
    line: Dict[str, Any],
    axis_index_map: Dict[str, int],
    uid_generator: Callable[[], str] | None,
) -> List[Dict[str, Any]]:
    raw_segments = line.get("segments")
    if not isinstance(raw_segments, list):
        raw_segments = []

    raw_points = []
    first_segment = {}
    for segment in raw_segments:
        if not isinstance(segment, dict):
            continue
        if not first_segment:
            first_segment = segment
        raw_points.extend(segment.get("points", []))
    raw_points.extend(line.get("nodes", []))
    points = _normalize_point_list(
        raw_points,
        DEFAULT_PLOT_SEGMENT_UID,
        axis_index_map,
        uid_generator,
    )
    return [
        {
            "uid": DEFAULT_PLOT_SEGMENT_UID,
            "start_axis_uid": "",
            "end_axis_uid": "",
            "start_curve": _normalize_curve(first_segment.get("start_curve")),
            "end_curve": _normalize_curve(first_segment.get("end_curve")),
            "title": first_segment.get("title") or "",
            "description": first_segment.get("description") or "",
            "note_type": _normalize_choice(
                first_segment.get("note_type"),
                NOTE_TYPE_LABELS,
                DEFAULT_NOTE_TYPE,
            ),
            "points": points,
        }
    ]


def _normalize_character_segments(
    line: Dict[str, Any],
    uid: str,
    axis_index_map: Dict[str, int],
    uid_generator: Callable[[], str] | None,
    last_axis_uid: str,
) -> List[Dict[str, Any]]:
    raw_segments = line.get("segments")
    if not isinstance(raw_segments, list):
        raw_segments = []

    legacy_start = line.get("start_axis_uid")
    legacy_end = line.get("end_axis_uid")
    if not raw_segments and legacy_start in axis_index_map:
        raw_segments = [
            {
                "uid": line.get("segment_uid") or "",
                "start_axis_uid": legacy_start,
                "end_axis_uid": legacy_end or "",
                "start_curve": DEFAULT_SEGMENT_CURVE,
                "end_curve": DEFAULT_SEGMENT_CURVE,
                "points": [],
            }
        ]

    normalized = []
    seen_segment_uids = set()
    for seg_index, segment in enumerate(raw_segments):
        if not isinstance(segment, dict):
            continue
        start_uid = segment.get("start_axis_uid")
        if start_uid not in axis_index_map:
            continue
        end_uid = segment.get("end_axis_uid") or ""
        if end_uid and end_uid not in axis_index_map:
            end_uid = ""
        if end_uid and axis_index_map[end_uid] < axis_index_map[start_uid]:
            start_uid, end_uid = end_uid, start_uid

        segment_uid = segment.get("uid") or (
            uid_generator() if uid_generator else f"{uid}-segment-{seg_index + 1}"
        )
        if segment_uid in seen_segment_uids:
            segment_uid = uid_generator() if uid_generator else f"{segment_uid}-{seg_index + 1}"
        seen_segment_uids.add(segment_uid)

        points = _normalize_point_list(
            segment.get("points", []),
            segment_uid,
            axis_index_map,
            uid_generator,
        )
        points = [
            point
            for point in points
            if axis_in_segment(
                point.get("axis_uid"),
                {"start_axis_uid": start_uid, "end_axis_uid": end_uid},
                axis_index_map,
                last_axis_uid=last_axis_uid,
            )
        ]

        normalized.append(
            {
                "uid": segment_uid,
                "start_axis_uid": start_uid,
                "end_axis_uid": end_uid,
                "start_curve": _normalize_curve(segment.get("start_curve")),
                "end_curve": _normalize_curve(segment.get("end_curve")),
                "title": segment.get("title") or "",
                "description": segment.get("description") or "",
                "note_type": _normalize_choice(
                    segment.get("note_type"),
                    NOTE_TYPE_LABELS,
                    DEFAULT_NOTE_TYPE,
                ),
                "points": points,
            }
        )

    normalized.sort(
        key=lambda seg: (
            axis_index_map.get(seg.get("start_axis_uid"), 10**6),
            axis_index_map.get(seg.get("end_axis_uid"), 10**6)
            if seg.get("end_axis_uid")
            else 10**6,
        )
    )

    legacy_points = _normalize_point_list(
        line.get("nodes", []),
        uid,
        axis_index_map,
        uid_generator,
    )
    if normalized and legacy_points:
        _assign_legacy_points_to_segments(
            normalized,
            legacy_points,
            axis_index_map,
            last_axis_uid,
        )

    return normalized


def get_display_segments(data: Dict[str, Any], line: Dict[str, Any]) -> List[Dict[str, Any]]:
    axis_nodes = data.get("axis_nodes", [])
    axis_index_map = get_axis_index_map(data)
    if not axis_nodes:
        return []

    if line.get("line_type") == "plot":
        raw_segment = (line.get("segments") or [{}])[0]
        points = [
            point
            for point in raw_segment.get("points", [])
            if point.get("axis_uid") in axis_index_map
        ]
        _sort_points(points, axis_index_map)
        return [
            {
                "uid": raw_segment.get("uid") or DEFAULT_PLOT_SEGMENT_UID,
                "start_axis_uid": axis_nodes[0]["uid"],
                "end_axis_uid": axis_nodes[-1]["uid"],
                "start_curve": _normalize_curve(raw_segment.get("start_curve")),
                "end_curve": _normalize_curve(raw_segment.get("end_curve")),
                "title": raw_segment.get("title") or "",
                "description": raw_segment.get("description") or "",
                "note_type": _normalize_choice(
                    raw_segment.get("note_type"),
                    NOTE_TYPE_LABELS,
                    DEFAULT_NOTE_TYPE,
                ),
                "points": points,
            }
        ]

    display_segments = []
    for segment in line.get("segments", []):
        start_uid = segment.get("start_axis_uid")
        if start_uid not in axis_index_map:
            continue
        display_segments.append(
            {
                "uid": segment.get("uid"),
                "start_axis_uid": start_uid,
                "end_axis_uid": segment.get("end_axis_uid") or "",
                "start_curve": _normalize_curve(segment.get("start_curve")),
                "end_curve": _normalize_curve(segment.get("end_curve")),
                "title": segment.get("title") or "",
                "description": segment.get("description") or "",
                "note_type": _normalize_choice(
                    segment.get("note_type"),
                    NOTE_TYPE_LABELS,
                    DEFAULT_NOTE_TYPE,
                ),
                "points": [
                    point
                    for point in segment.get("points", [])
                    if point.get("axis_uid") in axis_index_map
                ],
            }
        )
    return display_segments


def get_open_segment(line: Dict[str, Any]) -> Dict[str, Any] | None:
    if line.get("line_type") != "character":
        return None
    for segment in reversed(line.get("segments", [])):
        if not segment.get("end_axis_uid"):
            return segment
    return None


def is_character_line_potential(line: Dict[str, Any]) -> bool:
    return line.get("line_type") == "character" and get_open_segment(line) is None


def line_covers_axis(data: Dict[str, Any], line: Dict[str, Any], axis_uid: str) -> bool:
    axis_nodes = data.get("axis_nodes", [])
    if not axis_nodes:
        return False
    axis_index_map = get_axis_index_map(data)
    last_axis_uid = axis_nodes[-1]["uid"]
    for segment in get_display_segments(data, line):
        if axis_in_segment(axis_uid, segment, axis_index_map, last_axis_uid=last_axis_uid):
            return True
    return False


def iter_line_points(line: Dict[str, Any]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for segment in line.get("segments", []):
        for point in segment.get("points", []):
            points.append(point)
    return points


def get_interaction_label(interaction_type: str) -> str:
    return INTERACTION_TYPE_LABELS.get(interaction_type, INTERACTION_TYPE_LABELS[DEFAULT_INTERACTION_TYPE])


def get_interaction_tone(interaction_type: str) -> str:
    return INTERACTION_TYPE_TONES.get(interaction_type, INTERACTION_TYPE_TONES[DEFAULT_INTERACTION_TYPE])


def get_node_type_label(node_type: str) -> str:
    return NODE_TYPE_LABELS.get(node_type, NODE_TYPE_LABELS[DEFAULT_NODE_TYPE])


def get_note_type_label(note_type: str) -> str:
    return NOTE_TYPE_LABELS.get(note_type, NOTE_TYPE_LABELS[DEFAULT_NOTE_TYPE])


def iter_tone_interactions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list((data or {}).get("interactions", []) or [])


def _iter_point_contexts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    contexts: List[Dict[str, Any]] = []
    for line in data.get("lines", []):
        for segment in line.get("segments", []):
            for point in segment.get("points", []):
                contexts.append(
                    {
                        "line_uid": line.get("uid", ""),
                        "line_name": line.get("name") or "未命名线",
                        "segment_uid": segment.get("uid", ""),
                        "point_uid": point.get("uid", ""),
                        "axis_uid": point.get("axis_uid", ""),
                        "point": point,
                    }
                )
    return contexts


def _build_segment_lookup(data: Dict[str, Any]) -> Dict[tuple[str, str], Dict[str, Any]]:
    lookup: Dict[tuple[str, str], Dict[str, Any]] = {}
    for line in data.get("lines", []):
        for segment in get_display_segments(data, line):
            segment_uid = segment.get("uid")
            line_uid = line.get("uid")
            if not line_uid or not segment_uid:
                continue
            lookup[(line_uid, segment_uid)] = segment
    return lookup


def _normalize_interactions(
    raw_interactions: Any,
    data: Dict[str, Any],
    uid_generator: Callable[[], str] | None,
) -> List[Dict[str, Any]]:
    if not isinstance(raw_interactions, list):
        raw_interactions = []
    axis_index_map = get_axis_index_map(data)
    last_axis_uid = data.get("axis_nodes", [])[-1]["uid"] if data.get("axis_nodes") else ""
    point_lookup = {
        context["point_uid"]: context
        for context in _iter_point_contexts(data)
        if context.get("point_uid")
    }
    segment_lookup = _build_segment_lookup(data)
    seen_uids: set[str] = set()
    normalized: List[Dict[str, Any]] = []

    for index, interaction in enumerate(raw_interactions):
        if not isinstance(interaction, dict):
            continue
        source_point_uid = interaction.get("source_point_uid") or interaction.get("from_point_uid") or ""
        source_context = point_lookup.get(source_point_uid)
        if not source_context:
            continue
        axis_uid = interaction.get("axis_uid") or source_context.get("axis_uid") or ""
        if axis_uid not in axis_index_map or axis_uid != source_context.get("axis_uid"):
            continue
        target_line_uid = interaction.get("target_line_uid") or interaction.get("to_line_uid") or ""
        target_segment_uid = interaction.get("target_segment_uid") or interaction.get("to_segment_uid") or ""
        target_segment = segment_lookup.get((target_line_uid, target_segment_uid))
        if not target_segment:
            continue
        if not axis_in_segment(
            axis_uid,
            target_segment,
            axis_index_map,
            last_axis_uid=last_axis_uid,
        ):
            continue
        if (
            source_context.get("line_uid") == target_line_uid
            and source_context.get("segment_uid") == target_segment_uid
        ):
            continue

        interaction_uid = interaction.get("uid") or (
            uid_generator() if uid_generator else f"tone-interaction-{index + 1}"
        )
        if interaction_uid in seen_uids:
            interaction_uid = uid_generator() if uid_generator else f"{interaction_uid}-{index + 1}"
        seen_uids.add(interaction_uid)

        interaction_type = interaction.get("interaction_type") or interaction.get("type") or DEFAULT_INTERACTION_TYPE
        if interaction_type not in INTERACTION_TYPE_LABELS:
            interaction_type = DEFAULT_INTERACTION_TYPE

        normalized.append(
            {
                "uid": interaction_uid,
                "axis_uid": axis_uid,
                "source_line_uid": source_context.get("line_uid", ""),
                "source_segment_uid": source_context.get("segment_uid", ""),
                "source_point_uid": source_point_uid,
                "target_line_uid": target_line_uid,
                "target_segment_uid": target_segment_uid,
                "interaction_type": interaction_type,
                "note": interaction.get("note") or "",
            }
        )
    return normalized


def _clone_segment_point(
    point: Dict[str, Any],
    segment_uid: str,
    uid_generator: Callable[[], str] | None,
    suffix: str,
) -> Dict[str, Any]:
    cloned = copy.deepcopy(point)
    cloned["uid"] = (
        uid_generator()
        if uid_generator
        else f"{segment_uid}-point-{suffix}"
    )
    return cloned


def duplicate_segment(
    line: Dict[str, Any],
    segment_uid: str,
    uid_generator: Callable[[], str] | None = None,
) -> str:
    segments = line.get("segments", [])
    for index, segment in enumerate(segments):
        if segment.get("uid") != segment_uid:
            continue
        new_uid = uid_generator() if uid_generator else f"{segment_uid}-copy"
        copied_points = []
        for point_index, point in enumerate(segment.get("points", []), start=1):
            copied_points.append(
                _clone_segment_point(point, new_uid, uid_generator, str(point_index))
            )
        copied_segment = {
            "uid": new_uid,
            "start_axis_uid": segment.get("start_axis_uid", ""),
            "end_axis_uid": segment.get("end_axis_uid", ""),
            "start_curve": _normalize_curve(segment.get("start_curve")),
            "end_curve": _normalize_curve(segment.get("end_curve")),
            "title": segment.get("title") or "",
            "description": segment.get("description") or "",
            "note_type": _normalize_choice(
                segment.get("note_type"),
                NOTE_TYPE_LABELS,
                DEFAULT_NOTE_TYPE,
            ),
            "points": copied_points,
        }
        segments.insert(index + 1, copied_segment)
        return new_uid
    return ""


def analyze_merge_conflicts(
    line: Dict[str, Any],
    first_segment_uid: str,
    second_segment_uid: str,
) -> List[Dict[str, Any]]:
    segments = line.get("segments", [])
    first_segment = None
    second_segment = None
    for segment in segments:
        if segment.get("uid") == first_segment_uid:
            first_segment = segment
        if segment.get("uid") == second_segment_uid:
            second_segment = segment
    if not first_segment or not second_segment:
        return []

    first_points = {
        point.get("axis_uid"): point
        for point in first_segment.get("points", [])
        if point.get("axis_uid")
    }
    second_points = {
        point.get("axis_uid"): point
        for point in second_segment.get("points", [])
        if point.get("axis_uid")
    }

    conflicts = []
    shared_axes = sorted(set(first_points).intersection(second_points))
    for axis_uid in shared_axes:
        first_point = first_points[axis_uid]
        second_point = second_points[axis_uid]
        first_signature = (
            round(float(first_point.get("amplitude", 0)), 3),
            round(float(first_point.get("curvature", 0.45)), 3),
            first_point.get("label") or "",
            first_point.get("description") or "",
            _normalize_choice(first_point.get("node_type"), NODE_TYPE_LABELS, DEFAULT_NODE_TYPE),
            _normalize_choice(first_point.get("note_type"), NOTE_TYPE_LABELS, DEFAULT_NOTE_TYPE),
            tuple(_normalize_tags(first_point.get("tags"))),
        )
        second_signature = (
            round(float(second_point.get("amplitude", 0)), 3),
            round(float(second_point.get("curvature", 0.45)), 3),
            second_point.get("label") or "",
            second_point.get("description") or "",
            _normalize_choice(second_point.get("node_type"), NODE_TYPE_LABELS, DEFAULT_NODE_TYPE),
            _normalize_choice(second_point.get("note_type"), NOTE_TYPE_LABELS, DEFAULT_NOTE_TYPE),
            tuple(_normalize_tags(second_point.get("tags"))),
        )
        if first_signature == second_signature:
            continue
        conflicts.append(
            {
                "axis_uid": axis_uid,
                "first_point": copy.deepcopy(first_point),
                "second_point": copy.deepcopy(second_point),
            }
        )
    return conflicts


def split_segment(
    line: Dict[str, Any],
    segment_uid: str,
    split_axis_uid: str,
    axis_index_map: Dict[str, int],
    uid_generator: Callable[[], str] | None = None,
    last_axis_uid: str = "",
) -> tuple[str, str]:
    segments = line.get("segments", [])
    for index, segment in enumerate(segments):
        if segment.get("uid") != segment_uid:
            continue
        start_uid = segment.get("start_axis_uid", "")
        end_uid = segment.get("end_axis_uid") or last_axis_uid
        if (
            split_axis_uid not in axis_index_map
            or start_uid not in axis_index_map
            or end_uid not in axis_index_map
        ):
            return ("", "")
        split_index = axis_index_map[split_axis_uid]
        start_index = axis_index_map[start_uid]
        end_index = axis_index_map[end_uid]
        if split_index <= start_index or split_index >= end_index:
            return ("", "")

        left_uid = uid_generator() if uid_generator else f"{segment_uid}-left"
        right_uid = uid_generator() if uid_generator else f"{segment_uid}-right"
        join_curve = (
            _normalize_curve(segment.get("start_curve"))
            + _normalize_curve(segment.get("end_curve"))
        ) / 2.0

        left_points = []
        right_points = []
        shared_points = []
        for point_index, point in enumerate(segment.get("points", []), start=1):
            point_axis_uid = point.get("axis_uid")
            point_axis_index = axis_index_map.get(point_axis_uid, -1)
            if point_axis_index < split_index:
                left_points.append(_clone_segment_point(point, left_uid, uid_generator, f"l{point_index}"))
            elif point_axis_index > split_index:
                right_points.append(_clone_segment_point(point, right_uid, uid_generator, f"r{point_index}"))
            else:
                shared_points.append(point)
        for point_index, point in enumerate(shared_points, start=1):
            left_points.append(_clone_segment_point(point, left_uid, uid_generator, f"ls{point_index}"))
            right_points.append(_clone_segment_point(point, right_uid, uid_generator, f"rs{point_index}"))

        left_segment = {
            "uid": left_uid,
            "start_axis_uid": start_uid,
            "end_axis_uid": split_axis_uid,
            "start_curve": _normalize_curve(segment.get("start_curve")),
            "end_curve": join_curve,
            "title": segment.get("title") or "",
            "description": segment.get("description") or "",
            "note_type": _normalize_choice(
                segment.get("note_type"),
                NOTE_TYPE_LABELS,
                DEFAULT_NOTE_TYPE,
            ),
            "points": left_points,
        }
        right_segment = {
            "uid": right_uid,
            "start_axis_uid": split_axis_uid,
            "end_axis_uid": segment.get("end_axis_uid", ""),
            "start_curve": join_curve,
            "end_curve": _normalize_curve(segment.get("end_curve")),
            "title": segment.get("title") or "",
            "description": segment.get("description") or "",
            "note_type": _normalize_choice(
                segment.get("note_type"),
                NOTE_TYPE_LABELS,
                DEFAULT_NOTE_TYPE,
            ),
            "points": right_points,
        }
        _sort_points(left_segment["points"], axis_index_map)
        _sort_points(right_segment["points"], axis_index_map)
        segments[index:index + 1] = [left_segment, right_segment]
        return (left_uid, right_uid)
    return ("", "")


def shift_segment(
    line: Dict[str, Any],
    segment_uid: str,
    axis_uids: List[str],
    delta: int,
    uid_generator: Callable[[], str] | None = None,
) -> bool:
    if not delta:
        return False
    axis_index_map = {axis_uid: index for index, axis_uid in enumerate(axis_uids)}
    segments = line.get("segments", [])
    for segment in segments:
        if segment.get("uid") != segment_uid:
            continue
        start_uid = segment.get("start_axis_uid")
        end_uid = segment.get("end_axis_uid") or ""
        if (
            start_uid not in axis_index_map
            or not end_uid
            or end_uid not in axis_index_map
        ):
            return False
        new_start_index = axis_index_map[start_uid] + delta
        new_end_index = axis_index_map[end_uid] + delta
        if (
            new_start_index < 0
            or new_end_index >= len(axis_uids)
            or new_start_index >= len(axis_uids)
            or new_end_index < 0
        ):
            return False

        point_map = {
            axis_uid: axis_uids[axis_index_map[axis_uid] + delta]
            for axis_uid in [
                point.get("axis_uid")
                for point in segment.get("points", [])
                if point.get("axis_uid") in axis_index_map
            ]
        }

        segment["start_axis_uid"] = axis_uids[new_start_index]
        segment["end_axis_uid"] = axis_uids[new_end_index]
        for point_index, point in enumerate(segment.get("points", []), start=1):
            old_axis_uid = point.get("axis_uid")
            if old_axis_uid not in point_map:
                continue
            point["axis_uid"] = point_map[old_axis_uid]
            if not point.get("uid"):
                point["uid"] = (
                    uid_generator()
                    if uid_generator
                    else f"{segment_uid}-shift-{point_index}"
                )
        _sort_points(segment.get("points", []), axis_index_map)
        return True
    return False


def merge_adjacent_segments(
    line: Dict[str, Any],
    first_segment_uid: str,
    second_segment_uid: str,
    axis_index_map: Dict[str, int],
    uid_generator: Callable[[], str] | None = None,
    conflict_strategy: str = "first",
) -> str:
    segments = line.get("segments", [])
    first_index = -1
    second_index = -1
    for index, segment in enumerate(segments):
        if segment.get("uid") == first_segment_uid:
            first_index = index
        if segment.get("uid") == second_segment_uid:
            second_index = index
    if first_index < 0 or second_index < 0 or abs(first_index - second_index) != 1:
        return ""
    if second_index < first_index:
        first_index, second_index = second_index, first_index
    first_segment = segments[first_index]
    second_segment = segments[second_index]
    merged_uid = uid_generator() if uid_generator else f"{first_segment_uid}-merged"

    conflict_strategy = "second" if conflict_strategy == "second" else "first"
    merged_points_by_axis: Dict[str, Dict[str, Any]] = {}

    for point_index, point in enumerate(first_segment.get("points", []), start=1):
        axis_uid = point.get("axis_uid")
        if not axis_uid:
            continue
        merged_points_by_axis[axis_uid] = _clone_segment_point(
            point,
            merged_uid,
            uid_generator,
            f"m1-{point_index}",
        )
    for point_index, point in enumerate(second_segment.get("points", []), start=1):
        axis_uid = point.get("axis_uid")
        if not axis_uid:
            continue
        if axis_uid not in merged_points_by_axis:
            merged_points_by_axis[axis_uid] = _clone_segment_point(
                point,
                merged_uid,
                uid_generator,
                f"m2-{point_index}",
            )
            continue
        if conflict_strategy == "second":
            merged_points_by_axis[axis_uid] = _clone_segment_point(
                point,
                merged_uid,
                uid_generator,
                f"m2-{point_index}",
            )

    merged_points = list(merged_points_by_axis.values())
    _sort_points(merged_points, axis_index_map)

    merged_segment = {
        "uid": merged_uid,
        "start_axis_uid": first_segment.get("start_axis_uid", ""),
        "end_axis_uid": second_segment.get("end_axis_uid", ""),
        "start_curve": _normalize_curve(first_segment.get("start_curve")),
        "end_curve": _normalize_curve(second_segment.get("end_curve")),
        "title": first_segment.get("title") or second_segment.get("title") or "",
        "description": first_segment.get("description") or second_segment.get("description") or "",
        "note_type": _normalize_choice(
            first_segment.get("note_type") or second_segment.get("note_type"),
            NOTE_TYPE_LABELS,
            DEFAULT_NOTE_TYPE,
        ),
        "points": merged_points,
    }
    segments[first_index:second_index + 1] = [merged_segment]
    return merged_uid


def ensure_tone_outline_defaults(
    data: Dict[str, Any],
    uid_generator: Callable[[], str] | None = None,
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = create_default_tone_outline()

    data["version"] = max(4, int(data.get("version", 0) or 0))
    axis_nodes = data.setdefault("axis_nodes", [])
    interactions = data.setdefault("interactions", [])
    lines = data.setdefault("lines", [])

    if not isinstance(axis_nodes, list):
        axis_nodes = []
        data["axis_nodes"] = axis_nodes
    if not isinstance(interactions, list):
        interactions = []
        data["interactions"] = interactions
    if not isinstance(lines, list):
        lines = []
        data["lines"] = lines

    normalized_axes: List[Dict[str, Any]] = []
    seen_axis_uids = set()
    for index, axis in enumerate(axis_nodes):
        if not isinstance(axis, dict):
            continue
        uid = axis.get("uid") or (
            uid_generator() if uid_generator else f"axis-{index + 1}"
        )
        if uid in seen_axis_uids:
            uid = uid_generator() if uid_generator else f"{uid}-{index + 1}"
        seen_axis_uids.add(uid)
        normalized_axes.append(
            {
                "uid": uid,
                "title": (axis.get("title") or axis.get("name") or f"节点 {index + 1}").strip(),
                "description": axis.get("description") or "",
            }
        )
    data["axis_nodes"] = normalized_axes

    axis_index_map = get_axis_index_map(data)
    last_axis_uid = normalized_axes[-1]["uid"] if normalized_axes else ""
    normalized_lines: List[Dict[str, Any]] = []
    plot_line = None

    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            continue
        line_type = "plot" if line.get("line_type") == "plot" else "character"
        uid = line.get("uid") or (
            DEFAULT_PLOT_LINE_UID
            if line_type == "plot" and plot_line is None
            else uid_generator()
            if uid_generator
            else f"tone-line-{index + 1}"
        )
        if line_type == "plot":
            uid = DEFAULT_PLOT_LINE_UID

        color = line.get("color") or (
            DEFAULT_PLOT_LINE_COLOR
            if line_type == "plot"
            else get_next_tone_line_color(normalized_lines)
        )

        if line_type == "plot":
            segments = _normalize_plot_segments(line, axis_index_map, uid_generator)
        else:
            segments = _normalize_character_segments(
                line,
                uid,
                axis_index_map,
                uid_generator,
                last_axis_uid,
            )

        normalized_line = {
            "uid": uid,
            "name": (
                line.get("name")
                or ("情节线" if line_type == "plot" else f"人物线 {index + 1}")
            ).strip(),
            "line_type": line_type,
            "character_name": (
                (line.get("character_name") or "").strip()
                if line_type == "character"
                else ""
            ),
            "color": color,
            "visible": _normalize_flag(line.get("visible"), default=True),
            "segments": segments,
        }

        if line_type == "plot" and plot_line is None:
            plot_line = normalized_line
        else:
            normalized_lines.append(normalized_line)

    if plot_line is None:
        plot_line = create_default_tone_outline()["lines"][0]

    data["lines"] = [plot_line, *normalized_lines]
    data["interactions"] = _normalize_interactions(interactions, data, uid_generator)
    return data


def build_line_summary(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = ensure_tone_outline_defaults(clone_tone_outline(data))
    axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
    line_map = {line.get("uid"): line for line in data.get("lines", [])}
    axis_index_map = get_axis_index_map(data)
    last_axis_uid = data.get("axis_nodes", [])[-1]["uid"] if data.get("axis_nodes") else ""
    interactions_by_source: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for interaction in data.get("interactions", []):
        source_key = (
            interaction.get("source_line_uid", ""),
            interaction.get("source_segment_uid", ""),
        )
        target_line = line_map.get(interaction.get("target_line_uid"), {})
        interactions_by_source.setdefault(source_key, []).append(
            {
                "uid": interaction.get("uid", ""),
                "axis_uid": interaction.get("axis_uid", ""),
                "axis_title": axis_map.get(interaction.get("axis_uid"), {}).get("title", "未命名节点"),
                "state_text": get_interaction_tone(interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE)),
                "type_text": get_interaction_label(interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE)),
                "target_line_name": target_line.get("name") or "未命名线",
                "note": interaction.get("note") or "",
            }
        )
    summaries = []

    for line in data.get("lines", []):
        status_text = "主轴情节线"
        if line.get("line_type") == "character":
            status_text = "潜在线" if is_character_line_potential(line) else "活动线"
        if not _normalize_flag(line.get("visible"), default=True):
            status_text = f"{status_text} / 已隐藏"

        segment_summaries = []
        display_segments = get_display_segments(data, line)
        if not display_segments and line.get("line_type") == "character":
            segment_summaries.append(
                {
                    "uid": "",
                    "range_text": "未引入，保存在潜在栏",
                    "state_text": "潜在",
                    "curve_text": "",
                    "segment_note": "",
                    "segment_title": "",
                    "segment_note_type": "",
                    "items": [],
                }
            )

        for segment_index, segment in enumerate(display_segments):
            range_text = _axis_range_text(
                axis_map,
                segment.get("start_axis_uid"),
                segment.get("end_axis_uid"),
            )
            if line.get("line_type") == "plot":
                state_text = "全程"
            else:
                state_text = "进行中" if not segment.get("end_axis_uid") else f"第{segment_index + 1}段"
            items = []
            for point in segment.get("points", []):
                if not axis_in_segment(
                    point.get("axis_uid"),
                    segment,
                    axis_index_map,
                    last_axis_uid=last_axis_uid,
                ):
                    continue
                axis = axis_map.get(point.get("axis_uid"), {})
                items.append(
                    {
                        "axis_uid": point.get("axis_uid"),
                        "axis_title": axis.get("title", "未命名节点"),
                        "strength": round(abs(float(point.get("amplitude", 0))), 1),
                        "amplitude": round(float(point.get("amplitude", 0)), 1),
                        "curvature": round(float(point.get("curvature", 0.45)), 2),
                        "label": point.get("label") or "",
                        "description": point.get("description") or "",
                    }
                )
            items.sort(key=lambda item: axis_index_map.get(item.get("axis_uid"), 0))
            segment_summaries.append(
                {
                    "uid": segment.get("uid"),
                    "range_text": range_text,
                    "state_text": state_text,
                    "curve_text": f"{segment.get('start_curve', DEFAULT_SEGMENT_CURVE):.2f} / {segment.get('end_curve', DEFAULT_SEGMENT_CURVE):.2f}",
                    "segment_note": segment.get("description") or "",
                    "segment_title": segment.get("title") or "",
                    "segment_note_type": get_note_type_label(
                        segment.get("note_type", DEFAULT_NOTE_TYPE)
                    ),
                    "items": items,
                    "interactions": interactions_by_source.get(
                        (line.get("uid", ""), segment.get("uid", "")),
                        [],
                    ),
                }
            )

        summaries.append(
            {
                "uid": line.get("uid"),
                "name": line.get("name") or "未命名线",
                "line_type": line.get("line_type") or "character",
                "character_name": line.get("character_name") or "",
                "status_text": status_text,
                "segments": segment_summaries,
            }
        )
    return summaries


def build_timeline_summary(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = ensure_tone_outline_defaults(clone_tone_outline(data))
    axis_nodes = data.get("axis_nodes", [])
    line_map = {line.get("uid"): line for line in data.get("lines", [])}
    axis_index_map = get_axis_index_map(data)
    last_axis_uid = axis_nodes[-1]["uid"] if axis_nodes else ""
    summaries = []

    for axis in axis_nodes:
        matches = []
        for line in data.get("lines", []):
            display_segments = get_display_segments(data, line)
            for segment_index, segment in enumerate(display_segments):
                explicit_points = [
                    point
                    for point in segment.get("points", [])
                    if point.get("axis_uid") == axis.get("uid")
                ]
                if explicit_points:
                    for point in explicit_points:
                        matches.append(
                            {
                                "line_uid": line.get("uid"),
                                "line_name": line.get("name") or "未命名线",
                                "line_type": line.get("line_type") or "character",
                                "state_text": get_node_type_label(
                                    point.get("node_type", DEFAULT_NODE_TYPE)
                                ),
                                "strength": round(abs(float(point.get("amplitude", 0))), 1),
                                "amplitude": round(float(point.get("amplitude", 0)), 1),
                                "curvature": round(float(point.get("curvature", 0.45)), 2),
                                "label": point.get("label") or "",
                                "description": point.get("description") or "",
                                "node_type": point.get("node_type", DEFAULT_NODE_TYPE),
                                "note_type": get_note_type_label(
                                    point.get("note_type", DEFAULT_NOTE_TYPE)
                                ),
                                "tags": list(point.get("tags", [])),
                                "segment_title": segment.get("title") or "",
                            }
                        )
                elif axis_in_segment(
                    axis.get("uid"),
                    segment,
                    axis_index_map,
                    last_axis_uid=last_axis_uid,
                ):
                    matches.append(
                        {
                            "line_uid": line.get("uid"),
                            "line_name": line.get("name") or "未命名线",
                            "line_type": line.get("line_type") or "character",
                            "state_text": "在线" if line.get("line_type") == "plot" else f"第{segment_index + 1}段在线",
                            "strength": "",
                            "amplitude": "",
                            "curvature": "",
                            "label": "",
                            "description": "该线段覆盖当前时间节点",
                        }
                    )
        for interaction in data.get("interactions", []):
            if interaction.get("axis_uid") != axis.get("uid"):
                continue
            source_line = line_map.get(interaction.get("source_line_uid"), {})
            target_line = line_map.get(interaction.get("target_line_uid"), {})
            matches.append(
                {
                    "line_uid": interaction.get("source_line_uid", ""),
                    "line_name": f"{source_line.get('name') or '未命名线'} -> {target_line.get('name') or '未命名线'}",
                    "line_type": source_line.get("line_type") or "character",
                    "state_text": get_interaction_tone(interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE)),
                    "strength": "",
                    "amplitude": "",
                    "curvature": get_interaction_label(interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE)),
                    "label": "",
                    "description": interaction.get("note") or "同轴节点作用箭头",
                }
            )
        matches.sort(
            key=lambda item: (
                0 if item["line_type"] == "plot" else 1,
                0 if "节点" in item["state_text"] else 1,
                item["line_name"],
            )
        )
        summaries.append(
            {
                "axis_uid": axis.get("uid"),
                "axis_title": axis.get("title") or "未命名节点",
                "axis_description": axis.get("description") or "",
                "matches": matches,
            }
        )
    return summaries


def build_plot_summary(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    timeline_items = build_timeline_summary(data)
    plot_summary: List[Dict[str, Any]] = []
    for axis in timeline_items:
        plot_match = next(
            (
                match for match in axis.get("matches", [])
                if match.get("line_type") == "plot"
            ),
            None,
        )
        related_lines = [
            match for match in axis.get("matches", [])
            if match.get("line_type") != "plot" and "->" not in match.get("line_name", "")
        ]
        relations = [
            match for match in axis.get("matches", [])
            if "->" in match.get("line_name", "")
        ]
        plot_summary.append(
            {
                "axis_uid": axis.get("axis_uid", ""),
                "axis_title": axis.get("axis_title", "未命名节点"),
                "axis_description": axis.get("axis_description", ""),
                "plot_match": plot_match,
                "related_lines": related_lines,
                "relations": relations,
            }
        )
    return plot_summary


def build_relation_summary(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = ensure_tone_outline_defaults(clone_tone_outline(data))
    axis_map = {axis.get("uid"): axis for axis in data.get("axis_nodes", [])}
    line_map = {line.get("uid"): line for line in data.get("lines", [])}

    summaries: List[Dict[str, Any]] = []
    for interaction in data.get("interactions", []):
        source_line = line_map.get(interaction.get("source_line_uid"), {})
        target_line = line_map.get(interaction.get("target_line_uid"), {})
        summaries.append(
            {
                "uid": interaction.get("uid", ""),
                "axis_uid": interaction.get("axis_uid", ""),
                "axis_title": axis_map.get(interaction.get("axis_uid"), {}).get("title", "未命名节点"),
                "source_line_name": source_line.get("name") or "未命名线",
                "target_line_name": target_line.get("name") or "未命名线",
                "relation_type": get_interaction_tone(
                    interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE)
                ),
                "relation_label": get_interaction_label(
                    interaction.get("interaction_type", DEFAULT_INTERACTION_TYPE)
                ),
                "note": interaction.get("note") or "",
            }
        )
    summaries.sort(key=lambda item: (item.get("axis_title", ""), item.get("source_line_name", ""), item.get("target_line_name", "")))
    return summaries
