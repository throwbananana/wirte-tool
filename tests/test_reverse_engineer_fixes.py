import unittest

from writer_app.core.reverse_engineer import ReverseEngineeringManager, AnalysisContext


class DummyAIClient:
    def call_lm_studio_with_prompts(self, **kwargs):
        return '{"characters": []}'

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


if __name__ == "__main__":
    unittest.main()
