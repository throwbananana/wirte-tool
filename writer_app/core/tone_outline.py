import copy
from typing import Any, Callable, Dict, List


DEFAULT_PLOT_LINE_UID = "plot-main"
DEFAULT_PLOT_LINE_COLOR = "#2563EB"
CHARACTER_LINE_COLORS = [
    "#E11D48",
    "#059669",
    "#7C3AED",
    "#EA580C",
    "#0891B2",
    "#CA8A04",
]


def create_default_tone_outline() -> Dict[str, Any]:
    return {
        "version": 2,
        "axis_nodes": [],
        "lines": [
            {
                "uid": DEFAULT_PLOT_LINE_UID,
                "name": "情节线",
                "line_type": "plot",
                "character_name": "",
                "color": DEFAULT_PLOT_LINE_COLOR,
                "segments": [],
                "nodes": [],
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
    }


def _normalize_character_segments(
    line: Dict[str, Any],
    uid: str,
    axis_index_map: Dict[str, int],
    uid_generator: Callable[[], str] | None,
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
        normalized.append(
            {
                "uid": segment_uid,
                "start_axis_uid": start_uid,
                "end_axis_uid": end_uid,
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
    return normalized


def get_display_segments(data: Dict[str, Any], line: Dict[str, Any]) -> List[Dict[str, Any]]:
    axis_nodes = data.get("axis_nodes", [])
    axis_index_map = get_axis_index_map(data)
    if not axis_nodes:
        return []
    if line.get("line_type") == "plot":
        return [
            {
                "uid": "plot-virtual",
                "start_axis_uid": axis_nodes[0]["uid"],
                "end_axis_uid": axis_nodes[-1]["uid"],
            }
        ]
    return [segment for segment in line.get("segments", []) if segment.get("start_axis_uid") in axis_index_map]


def get_open_segment(line: Dict[str, Any]) -> Dict[str, Any] | None:
    if line.get("line_type") != "character":
        return None
    for segment in reversed(line.get("segments", [])):
        if not segment.get("end_axis_uid"):
            return segment
    return None


def is_character_line_potential(line: Dict[str, Any]) -> bool:
    return line.get("line_type") == "character" and get_open_segment(line) is None


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


def ensure_tone_outline_defaults(
    data: Dict[str, Any],
    uid_generator: Callable[[], str] | None = None,
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = create_default_tone_outline()

    data.setdefault("version", 2)
    axis_nodes = data.setdefault("axis_nodes", [])
    lines = data.setdefault("lines", [])

    if not isinstance(axis_nodes, list):
        axis_nodes = []
        data["axis_nodes"] = axis_nodes
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

        seen_point_uids = set()
        nodes = line.get("nodes") if isinstance(line.get("nodes"), list) else []
        normalized_nodes = []
        for point_index, node in enumerate(nodes):
            normalized_point = _normalize_point(
                node,
                uid,
                point_index,
                axis_index_map,
                seen_point_uids,
                uid_generator,
            )
            if normalized_point:
                normalized_nodes.append(normalized_point)
        normalized_nodes.sort(key=lambda item: axis_index_map.get(item.get("axis_uid"), 0))

        segments: List[Dict[str, Any]]
        if line_type == "plot":
            segments = []
        else:
            segments = _normalize_character_segments(line, uid, axis_index_map, uid_generator)

        if line_type == "character" and segments:
            last_axis_uid = normalized_axes[-1]["uid"] if normalized_axes else ""
            normalized_nodes = [
                node
                for node in normalized_nodes
                if any(
                    axis_in_segment(
                        node.get("axis_uid"),
                        segment,
                        axis_index_map,
                        last_axis_uid=last_axis_uid,
                    )
                    for segment in segments
                )
            ]

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
            "segments": segments,
            "nodes": normalized_nodes,
        }

        if line_type == "plot" and plot_line is None:
            plot_line = normalized_line
        else:
            normalized_lines.append(normalized_line)

    if plot_line is None:
        plot_line = create_default_tone_outline()["lines"][0]

    data["lines"] = [plot_line, *normalized_lines]
    return data


def build_line_summary(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = ensure_tone_outline_defaults(clone_tone_outline(data))
    axis_map = {axis["uid"]: axis for axis in data.get("axis_nodes", [])}
    axis_index_map = get_axis_index_map(data)
    summaries = []

    for line in data.get("lines", []):
        status_text = "主轴情节线"
        if line.get("line_type") == "character":
            status_text = "潜在线" if is_character_line_potential(line) else "活动线"

        segment_summaries = []
        display_segments = get_display_segments(data, line)
        if not display_segments and line.get("line_type") == "character":
            segment_summaries.append(
                {
                    "uid": "",
                    "range_text": "未引入，保存在潜在栏",
                    "state_text": "潜在",
                    "items": [],
                }
            )

        for segment_index, segment in enumerate(display_segments):
            range_text = _axis_range_text(
                axis_map,
                segment.get("start_axis_uid"),
                segment.get("end_axis_uid"),
            )
            state_text = "进行中" if not segment.get("end_axis_uid") else f"第{segment_index + 1}段"
            items = []
            for node in line.get("nodes", []):
                if not axis_in_segment(
                    node.get("axis_uid"),
                    segment,
                    axis_index_map,
                    last_axis_uid=data.get("axis_nodes", [])[-1]["uid"] if data.get("axis_nodes") else "",
                ):
                    continue
                axis = axis_map.get(node.get("axis_uid"), {})
                items.append(
                    {
                        "axis_uid": node.get("axis_uid"),
                        "axis_title": axis.get("title", "未命名节点"),
                        "strength": round(abs(float(node.get("amplitude", 0))), 1),
                        "amplitude": round(float(node.get("amplitude", 0)), 1),
                        "curvature": round(float(node.get("curvature", 0.45)), 2),
                        "label": node.get("label") or "",
                        "description": node.get("description") or "",
                    }
                )
            items.sort(key=lambda item: axis_index_map.get(item.get("axis_uid"), 0))
            segment_summaries.append(
                {
                    "uid": segment.get("uid"),
                    "range_text": range_text,
                    "state_text": state_text,
                    "items": items,
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
    summaries = []

    for axis in axis_nodes:
        matches = []
        for line in data.get("lines", []):
            explicit_nodes = [
                node for node in line.get("nodes", [])
                if node.get("axis_uid") == axis.get("uid")
            ]
            if explicit_nodes:
                for node in explicit_nodes:
                    matches.append(
                        {
                            "line_uid": line.get("uid"),
                            "line_name": line.get("name") or "未命名线",
                            "line_type": line.get("line_type") or "character",
                            "state_text": "节点",
                            "strength": round(abs(float(node.get("amplitude", 0))), 1),
                            "amplitude": round(float(node.get("amplitude", 0)), 1),
                            "curvature": round(float(node.get("curvature", 0.45)), 2),
                            "label": node.get("label") or "",
                            "description": node.get("description") or "",
                        }
                    )
            elif line_covers_axis(data, line, axis.get("uid")):
                matches.append(
                    {
                        "line_uid": line.get("uid"),
                        "line_name": line.get("name") or "未命名线",
                        "line_type": line.get("line_type") or "character",
                        "state_text": "在线",
                        "strength": "",
                        "amplitude": "",
                        "curvature": "",
                        "label": "",
                        "description": "该线段覆盖当前时间节点",
                    }
                )
        matches.sort(
            key=lambda item: (
                0 if item["line_type"] == "plot" else 1,
                0 if item["state_text"] == "节点" else 1,
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
