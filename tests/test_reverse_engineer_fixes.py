import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest

from writer_app.core.reverse_engineer import ReverseEngineeringManager, AnalysisContext


class DummyAIClient:
    def call_lm_studio_with_prompts(self, **kwargs):
        return '[{"name": "林舟", "role": "主角", "description": "", "tags": []}]'

    def extract_json_from_text(self, text):
        import json
        return json.loads(text)


class ReverseEngineerFixTests(unittest.TestCase):
    def setUp(self):
        self.manager = ReverseEngineeringManager(DummyAIClient())

    def test_cache_key_changes_when_model_changes(self):
        content = "same content"
        key_a = self.manager.get_analysis_cache_key(
            content,
            "timeline",
            config={"model": "model-a", "api_url": "http://localhost:1234"},
            context_enabled=True,
        )
        key_b = self.manager.get_analysis_cache_key(
            content,
            "timeline",
            config={"model": "model-b", "api_url": "http://localhost:1234"},
            context_enabled=True,
        )
        self.assertNotEqual(key_a, key_b)

    def test_timeline_merge_keeps_truth_and_lie_separate(self):
        merged = self.manager.merge_results(
            [[
                {"type": "truth", "name": "宴会开始", "timestamp": "20:00", "action": "真相线"},
                {"type": "lie", "name": "宴会开始", "timestamp": "20:00", "gap": "谎言线"},
            ]],
            "timeline",
        )
        self.assertEqual(len(merged), 2)
        self.assertEqual({item["type"] for item in merged}, {"truth", "lie"})


    def test_analyze_chunk_accepts_cancel_event(self):
        import threading

        result = self.manager.analyze_chunk(
            "林舟走进房间。",
            "characters",
            {"model": "model-a", "api_url": "http://localhost:1234", "api_key": ""},
            cancel_event=threading.Event(),
        )
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["name"], "林舟")

    def test_relationship_faction_enters_known_entities(self):
        context = AnalysisContext()
        self.manager.update_context_from_results(
            context,
            {
                "relationships": [[
                    {"source": "林舟", "target": "白塔会", "target_type": "faction"}
                ]]
            },
            "第1章",
        )
        self.assertIn("林舟", context.known_characters)
        self.assertIn("白塔会", context.known_entities)

    def test_summary_context_strips_think_blocks_and_caches_compact_text(self):
        raw_summary = "<think>这里是模型推理过程，不应进入上下文。</think>\n林舟发现白塔会的密信。"
        context = AnalysisContext()

        context.add_chapter_summary("第1章", raw_summary)
        self.manager.set_cached_summary("summary-key", raw_summary)

        self.assertIn("林舟发现白塔会的密信", context.rolling_summary)
        self.assertNotIn("<think>", context.rolling_summary)
        self.assertNotIn("模型推理过程", context.rolling_summary)
        self.assertEqual(self.manager.get_cached_summary("summary-key"), "林舟发现白塔会的密信。")

    def test_import_context_rebuilds_sanitized_rolling_summary(self):
        context = AnalysisContext.from_dict({
            "known_characters": ["林舟"],
            "known_entities": ["白塔会"],
            "rolling_summary": "旧的污染摘要",
            "chapter_summaries": [
                {
                    "title": "第1章",
                    "summary": "<think>冗长分析</think>\n林舟第一次进入白塔。"
                }
            ]
        })

        self.assertIn("林舟第一次进入白塔", context.rolling_summary)
        self.assertNotIn("旧的污染摘要", context.rolling_summary)
        self.assertNotIn("冗长分析", context.rolling_summary)

    def test_context_prompt_compacts_names_and_includes_recent_relationship_entities(self):
        context = AnalysisContext()
        context.add_characters([f"角色{i}" for i in range(1, 41)])
        context.add_entities(["白塔会", "旧城区"])

        prompt = context.get_context_prompt("relationships")

        self.assertIn("【已知角色】", prompt)
        self.assertIn("角色1", prompt)
        self.assertIn("角色40", prompt)
        self.assertIn("省略", prompt)
        self.assertIn("【已知设定】", prompt)
        self.assertIn("白塔会", prompt)

    def test_analyze_chunk_still_runs_when_retry_count_is_zero(self):
        self.manager.max_retries = 0

        result = self.manager.analyze_chunk(
            "林舟走进房间。",
            "characters",
            {"model": "model-a", "api_url": "http://localhost:1234", "api_key": ""},
        )

        self.assertEqual(result[0]["name"], "林舟")

    def test_all_reverse_analysis_types_normalize_expected_shapes(self):
        cases = {
            "characters": [{"name": "林舟", "description": "主角"}],
            "outline": [{"name": "进入白塔", "content": "林舟进入白塔。", "characters": ["林舟"]}],
            "wiki": [{"name": "白塔会", "category": "组织", "content": "地下势力"}],
            "relationships": [{"source": "林舟", "target": "白塔会", "target_type": "faction"}],
            "timeline": {
                "truth_events": [{"name": "进入白塔", "timestamp": "夜晚", "action": "林舟潜入"}],
                "lie_events": [{"name": "留在家中", "timestamp": "夜晚", "gap": "掩盖潜入"}],
            },
            "style": {"analysis": "冷峻、短句密集。"},
            "summary": {"summary": "林舟发现白塔会的线索。"},
        }

        for analysis_type, payload in cases.items():
            with self.subTest(analysis_type=analysis_type):
                normalized = self.manager._normalize_result(payload, analysis_type)
                self.assertIsInstance(normalized, list)
                self.assertGreater(len(normalized), 0)

    def test_incremental_result_cache_survives_skip_without_mutating_source(self):
        content_hash = "abc123"
        result = [{"name": "林舟", "chapter_title": "第1章"}]

        self.manager.set_cached_analysis_result(content_hash, "characters", result)
        cached = self.manager.get_cached_analysis_result(content_hash, "characters")
        cached[0]["name"] = "已修改"

        self.assertEqual(result[0]["name"], "林舟")
        self.assertEqual(self.manager.get_cached_analysis_result(content_hash, "characters")[0]["name"], "林舟")
        self.assertNotIn("chapter_title", self.manager.get_cached_analysis_result(content_hash, "characters")[0])


if __name__ == "__main__":
    unittest.main()
