import unittest

from writer_app.core.project_types import ProjectTypeManager


class TestProjectPresets(unittest.TestCase):
    def test_preset_merges_tags(self):
        preset = ProjectTypeManager.get_preset_config("SciFi", ["Suspense"], "Long")
        tools = set(preset.get("recommended_tools", []))
        self.assertIn("faction", tools)
        self.assertIn("evidence_board", tools)
        self.assertIn("dual_timeline", tools)

    def test_preset_respects_length_hidden(self):
        preset = ProjectTypeManager.get_preset_config("General", [], "Short")
        tools = set(preset.get("recommended_tools", []))
        self.assertNotIn("calendar", tools)
        self.assertNotIn("swimlanes", tools)

        suspense_preset = ProjectTypeManager.get_preset_config("Suspense", [], "Short")
        suspense_tools = set(suspense_preset.get("recommended_tools", []))
        self.assertIn("dual_timeline", suspense_tools)
        self.assertIn("evidence_board", suspense_tools)

    def test_preset_merges_wiki_categories(self):
        preset = ProjectTypeManager.get_preset_config("SciFi", ["Suspense"], "Long")
        categories = preset.get("wiki_categories", [])
        self.assertIn("科技", categories)
        self.assertIn("证据", categories)


if __name__ == "__main__":
    unittest.main()
