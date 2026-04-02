import unittest

from writer_app.core.module_policy import get_required_modules_for_tools
from writer_app.core.typed_data import DataModule, get_required_modules


class TestModulePolicy(unittest.TestCase):
    def test_required_modules_follow_enabled_tools(self):
        modules = get_required_modules_for_tools(["timeline", "relationship", "evidence_board"])
        self.assertIn(DataModule.OUTLINE, modules)
        self.assertIn(DataModule.SCRIPT, modules)
        self.assertIn(DataModule.TIMELINES, modules)
        self.assertIn(DataModule.RELATIONSHIPS, modules)
        self.assertIn(DataModule.EVIDENCE, modules)

    def test_project_type_modules_are_derived_from_tool_presets(self):
        suspense_modules = get_required_modules("Suspense")
        self.assertIn(DataModule.EVIDENCE, suspense_modules)
        self.assertIn(DataModule.TIMELINES, suspense_modules)
        self.assertNotIn(DataModule.FACTIONS, suspense_modules)

        poetry_modules = get_required_modules("Poetry")
        self.assertIn(DataModule.OUTLINE, poetry_modules)
        self.assertIn(DataModule.SCRIPT, poetry_modules)
        self.assertIn(DataModule.TAGS, poetry_modules)
        self.assertIn(DataModule.RESEARCH, poetry_modules)
        self.assertIn(DataModule.IDEAS, poetry_modules)
        self.assertIn(DataModule.GALGAME_ASSETS, poetry_modules)
        self.assertNotIn(DataModule.TIMELINES, poetry_modules)


if __name__ == "__main__":
    unittest.main()
