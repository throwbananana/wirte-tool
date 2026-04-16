import unittest

from writer_app.core.tone_outline import (
    DEFAULT_PLOT_SEGMENT_UID,
    analyze_merge_conflicts,
    build_line_summary,
    build_plot_summary,
    build_relation_summary,
    build_timeline_summary,
    duplicate_segment,
    ensure_tone_outline_defaults,
    merge_adjacent_segments,
    shift_segment,
    split_segment,
)


class TestToneOutline(unittest.TestCase):
    def test_migrates_legacy_line_nodes_into_segment_points(self):
        data = {
            "axis_nodes": [
                {"uid": "axis-1", "title": "开场", "description": ""},
                {"uid": "axis-2", "title": "冲突", "description": ""},
                {"uid": "axis-3", "title": "回落", "description": ""},
            ],
            "lines": [
                {
                    "uid": "plot-main",
                    "name": "情节线",
                    "line_type": "plot",
                    "nodes": [
                        {
                            "uid": "plot-point",
                            "axis_uid": "axis-2",
                            "amplitude": 20,
                            "curvature": 0.6,
                            "label": "转折",
                            "description": "",
                        }
                    ],
                },
                {
                    "uid": "hero-line",
                    "name": "主角线",
                    "line_type": "character",
                    "segments": [
                        {
                            "uid": "seg-1",
                            "start_axis_uid": "axis-1",
                            "end_axis_uid": "axis-3",
                        }
                    ],
                    "nodes": [
                        {
                            "uid": "hero-point",
                            "axis_uid": "axis-2",
                            "amplitude": 35,
                            "curvature": 0.8,
                            "label": "爆发",
                            "description": "",
                        }
                    ],
                },
            ],
        }

        normalized = ensure_tone_outline_defaults(data)

        self.assertEqual(normalized["lines"][0]["segments"][0]["uid"], DEFAULT_PLOT_SEGMENT_UID)
        self.assertEqual(normalized["lines"][0]["segments"][0]["points"][0]["label"], "转折")
        self.assertEqual(normalized["lines"][1]["segments"][0]["points"][0]["label"], "爆发")

    def test_line_summary_exposes_segment_curve_text(self):
        data = ensure_tone_outline_defaults(
            {
                "axis_nodes": [
                    {"uid": "axis-1", "title": "开场", "description": ""},
                    {"uid": "axis-2", "title": "终局", "description": ""},
                ],
                "lines": [
                    {
                        "uid": "plot-main",
                        "name": "情节线",
                        "line_type": "plot",
                        "segments": [
                            {
                                "uid": DEFAULT_PLOT_SEGMENT_UID,
                                "start_curve": 0.4,
                                "end_curve": 0.9,
                                "points": [],
                            }
                        ],
                    }
                ],
            }
        )

        summaries = build_line_summary(data)

        self.assertEqual(summaries[0]["segments"][0]["curve_text"], "0.40 / 0.90")

    def test_duplicate_split_and_merge_segment_helpers(self):
        data = ensure_tone_outline_defaults(
            {
                "axis_nodes": [
                    {"uid": "axis-1", "title": "开场", "description": ""},
                    {"uid": "axis-2", "title": "冲突", "description": ""},
                    {"uid": "axis-3", "title": "转折", "description": ""},
                    {"uid": "axis-4", "title": "终局", "description": ""},
                ],
                "lines": [
                    {
                        "uid": "hero-line",
                        "name": "主角线",
                        "line_type": "character",
                        "segments": [
                            {
                                "uid": "seg-1",
                                "start_axis_uid": "axis-1",
                                "end_axis_uid": "axis-4",
                                "start_curve": 0.3,
                                "end_curve": 0.9,
                                "points": [
                                    {
                                        "uid": "p-1",
                                        "axis_uid": "axis-2",
                                        "amplitude": 20,
                                        "curvature": 0.6,
                                        "label": "起势",
                                        "description": "",
                                    },
                                    {
                                        "uid": "p-2",
                                        "axis_uid": "axis-3",
                                        "amplitude": 50,
                                        "curvature": 0.8,
                                        "label": "爆发",
                                        "description": "",
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        )
        line = data["lines"][1]
        axis_index_map = {
            axis["uid"]: index
            for index, axis in enumerate(data["axis_nodes"])
        }

        duplicated_uid = duplicate_segment(line, "seg-1")
        self.assertTrue(duplicated_uid)
        self.assertEqual(len(line["segments"]), 2)
        self.assertNotEqual(line["segments"][1]["points"][0]["uid"], "p-1")

        line["segments"] = [line["segments"][0]]
        left_uid, right_uid = split_segment(
            line,
            "seg-1",
            "axis-3",
            axis_index_map,
        )
        self.assertTrue(left_uid)
        self.assertTrue(right_uid)
        self.assertEqual(len(line["segments"]), 2)
        self.assertEqual(line["segments"][0]["end_axis_uid"], "axis-3")
        self.assertEqual(line["segments"][1]["start_axis_uid"], "axis-3")

        merged_uid = merge_adjacent_segments(
            line,
            left_uid,
            right_uid,
            axis_index_map,
        )
        self.assertTrue(merged_uid)
        self.assertEqual(len(line["segments"]), 1)
        self.assertEqual(line["segments"][0]["start_axis_uid"], "axis-1")
        self.assertEqual(line["segments"][0]["end_axis_uid"], "axis-4")

    def test_merge_conflicts_can_prefer_second_segment(self):
        data = ensure_tone_outline_defaults(
            {
                "axis_nodes": [
                    {"uid": "axis-1", "title": "开场", "description": ""},
                    {"uid": "axis-2", "title": "冲突", "description": ""},
                    {"uid": "axis-3", "title": "终局", "description": ""},
                ],
                "lines": [
                    {
                        "uid": "hero-line",
                        "name": "主角线",
                        "line_type": "character",
                        "segments": [
                            {
                                "uid": "seg-1",
                                "start_axis_uid": "axis-1",
                                "end_axis_uid": "axis-2",
                                "points": [
                                    {
                                        "uid": "p-1",
                                        "axis_uid": "axis-2",
                                        "amplitude": 10,
                                        "curvature": 0.5,
                                        "label": "前段",
                                        "description": "",
                                    }
                                ],
                            },
                            {
                                "uid": "seg-2",
                                "start_axis_uid": "axis-2",
                                "end_axis_uid": "axis-3",
                                "points": [
                                    {
                                        "uid": "p-2",
                                        "axis_uid": "axis-2",
                                        "amplitude": 40,
                                        "curvature": 0.9,
                                        "label": "后段",
                                        "description": "",
                                    }
                                ],
                            },
                        ],
                    }
                ],
            }
        )
        line = data["lines"][1]
        axis_index_map = {
            axis["uid"]: index
            for index, axis in enumerate(data["axis_nodes"])
        }

        conflicts = analyze_merge_conflicts(line, "seg-1", "seg-2")
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["axis_uid"], "axis-2")

        merged_uid = merge_adjacent_segments(
            line,
            "seg-1",
            "seg-2",
            axis_index_map,
            conflict_strategy="second",
        )
        self.assertTrue(merged_uid)
        self.assertEqual(len(line["segments"]), 1)
        self.assertEqual(line["segments"][0]["points"][0]["label"], "后段")

    def test_shift_segment_moves_boundaries_and_points_together(self):
        data = ensure_tone_outline_defaults(
            {
                "axis_nodes": [
                    {"uid": "axis-1", "title": "开场", "description": ""},
                    {"uid": "axis-2", "title": "冲突", "description": ""},
                    {"uid": "axis-3", "title": "转折", "description": ""},
                    {"uid": "axis-4", "title": "终局", "description": ""},
                ],
                "lines": [
                    {
                        "uid": "hero-line",
                        "name": "主角线",
                        "line_type": "character",
                        "segments": [
                            {
                                "uid": "seg-1",
                                "start_axis_uid": "axis-1",
                                "end_axis_uid": "axis-3",
                                "points": [
                                    {
                                        "uid": "p-1",
                                        "axis_uid": "axis-2",
                                        "amplitude": 22,
                                        "curvature": 0.6,
                                        "label": "中段",
                                        "description": "",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )
        line = data["lines"][1]
        shifted = shift_segment(
            line,
            "seg-1",
            ["axis-1", "axis-2", "axis-3", "axis-4"],
            1,
        )

        self.assertTrue(shifted)
        self.assertEqual(line["segments"][0]["start_axis_uid"], "axis-2")
        self.assertEqual(line["segments"][0]["end_axis_uid"], "axis-4")
        self.assertEqual(line["segments"][0]["points"][0]["axis_uid"], "axis-3")

    def test_interactions_are_normalized_and_included_in_summaries(self):
        data = ensure_tone_outline_defaults(
            {
                "axis_nodes": [
                    {"uid": "axis-1", "title": "开场", "description": ""},
                    {"uid": "axis-2", "title": "对抗", "description": ""},
                ],
                "lines": [
                    {
                        "uid": "plot-main",
                        "name": "情节线",
                        "line_type": "plot",
                        "segments": [
                            {
                                "uid": DEFAULT_PLOT_SEGMENT_UID,
                                "points": [
                                    {
                                        "uid": "plot-point",
                                        "axis_uid": "axis-2",
                                        "amplitude": 30,
                                        "curvature": 0.5,
                                        "label": "压迫",
                                        "description": "",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "uid": "hero-line",
                        "name": "主角线",
                        "line_type": "character",
                        "segments": [
                            {
                                "uid": "hero-seg",
                                "start_axis_uid": "axis-1",
                                "end_axis_uid": "axis-2",
                                "points": [
                                    {
                                        "uid": "hero-point",
                                        "axis_uid": "axis-2",
                                        "amplitude": -20,
                                        "curvature": 0.8,
                                        "label": "受压",
                                        "description": "",
                                    }
                                ],
                            }
                        ],
                    },
                ],
                "interactions": [
                    {
                        "uid": "interaction-1",
                        "axis_uid": "axis-2",
                        "source_point_uid": "hero-point",
                        "target_line_uid": "plot-main",
                        "target_segment_uid": DEFAULT_PLOT_SEGMENT_UID,
                        "interaction_type": "solid_single",
                        "note": "主角主动压制情节线",
                    }
                ],
            }
        )

        self.assertEqual(len(data["interactions"]), 1)
        self.assertEqual(data["interactions"][0]["source_line_uid"], "hero-line")

        line_summaries = build_line_summary(data)
        hero_summary = next(item for item in line_summaries if item["uid"] == "hero-line")
        self.assertEqual(hero_summary["segments"][0]["interactions"][0]["type_text"], "实线单箭头")
        self.assertEqual(hero_summary["segments"][0]["interactions"][0]["note"], "主角主动压制情节线")

        timeline_summaries = build_timeline_summary(data)
        axis_summary = next(item for item in timeline_summaries if item["axis_uid"] == "axis-2")
        interaction_match = next(
            item for item in axis_summary["matches"]
            if item["line_name"] == "主角线 -> 情节线"
        )
        self.assertEqual(interaction_match["curvature"], "实线单箭头")
        self.assertEqual(interaction_match["description"], "主角主动压制情节线")

    def test_new_metadata_fields_are_normalized_and_exposed(self):
        data = ensure_tone_outline_defaults(
            {
                "axis_nodes": [
                    {"uid": "axis-1", "title": "开场", "description": ""},
                    {"uid": "axis-2", "title": "对抗", "description": ""},
                ],
                "lines": [
                    {
                        "uid": "plot-main",
                        "name": "情节线",
                        "line_type": "plot",
                        "visible": False,
                        "segments": [
                            {
                                "uid": DEFAULT_PLOT_SEGMENT_UID,
                                "title": "第一幕",
                                "description": "铺垫主冲突",
                                "note_type": "foreshadow",
                                "points": [
                                    {
                                        "uid": "plot-point",
                                        "axis_uid": "axis-2",
                                        "amplitude": 42,
                                        "curvature": 0.65,
                                        "label": "翻面",
                                        "description": "信息揭露",
                                        "node_type": "turning",
                                        "note_type": "plot",
                                        "tags": ["反转", "揭露"],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )

        plot_line = data["lines"][0]
        plot_segment = plot_line["segments"][0]
        plot_point = plot_segment["points"][0]
        self.assertFalse(plot_line["visible"])
        self.assertEqual(plot_segment["title"], "第一幕")
        self.assertEqual(plot_segment["note_type"], "foreshadow")
        self.assertEqual(plot_point["node_type"], "turning")
        self.assertEqual(plot_point["tags"], ["反转", "揭露"])

        line_summary = build_line_summary(data)[0]
        self.assertIn("已隐藏", line_summary["status_text"])
        self.assertEqual(line_summary["segments"][0]["segment_title"], "第一幕")
        self.assertEqual(line_summary["segments"][0]["segment_note_type"], "伏笔说明")

        timeline_summary = build_timeline_summary(data)
        axis_summary = next(item for item in timeline_summary if item["axis_uid"] == "axis-2")
        self.assertEqual(axis_summary["matches"][0]["state_text"], "转折节点")
        self.assertEqual(axis_summary["matches"][0]["tags"], ["反转", "揭露"])

    def test_plot_and_relation_summaries_group_matches(self):
        data = ensure_tone_outline_defaults(
            {
                "axis_nodes": [
                    {"uid": "axis-1", "title": "开场", "description": ""},
                    {"uid": "axis-2", "title": "碰撞", "description": "情节升温"},
                ],
                "lines": [
                    {
                        "uid": "plot-main",
                        "name": "情节线",
                        "line_type": "plot",
                        "segments": [
                            {
                                "uid": DEFAULT_PLOT_SEGMENT_UID,
                                "points": [
                                    {
                                        "uid": "plot-point",
                                        "axis_uid": "axis-2",
                                        "amplitude": 35,
                                        "curvature": 0.6,
                                        "label": "升级",
                                        "description": "正面冲突爆发",
                                        "node_type": "conflict",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "uid": "hero-line",
                        "name": "主角线",
                        "line_type": "character",
                        "segments": [
                            {
                                "uid": "hero-seg",
                                "start_axis_uid": "axis-1",
                                "end_axis_uid": "axis-2",
                                "points": [
                                    {
                                        "uid": "hero-point",
                                        "axis_uid": "axis-2",
                                        "amplitude": -25,
                                        "curvature": 0.8,
                                        "label": "受压",
                                        "description": "主角失势",
                                        "node_type": "conflict",
                                    }
                                ],
                            }
                        ],
                    },
                ],
                "interactions": [
                    {
                        "uid": "interaction-1",
                        "axis_uid": "axis-2",
                        "source_point_uid": "hero-point",
                        "target_line_uid": "plot-main",
                        "target_segment_uid": DEFAULT_PLOT_SEGMENT_UID,
                        "interaction_type": "solid_single",
                        "note": "主角被主线压制",
                    }
                ],
            }
        )

        plot_summary = build_plot_summary(data)
        axis_plot = next(item for item in plot_summary if item["axis_uid"] == "axis-2")
        self.assertEqual(axis_plot["plot_match"]["state_text"], "冲突节点")
        self.assertEqual(axis_plot["related_lines"][0]["line_name"], "主角线")
        self.assertEqual(axis_plot["relations"][0]["description"], "主角被主线压制")

        relation_summary = build_relation_summary(data)
        self.assertEqual(relation_summary[0]["axis_title"], "碰撞")
        self.assertEqual(relation_summary[0]["relation_label"], "实线单箭头")
        self.assertEqual(relation_summary[0]["target_line_name"], "情节线")


if __name__ == "__main__":
    unittest.main()
