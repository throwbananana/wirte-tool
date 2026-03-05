import unittest

from writer_app.core.models import ProjectManager
from writer_app.core.project_types import ProjectTypeManager


class TestProjectTools(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()

    def test_new_project_sets_enabled_tools(self):
        self.pm.new_project("General")
        tools = self.pm.project_data.get("meta", {}).get("enabled_tools")
        self.assertIsInstance(tools, list)
        expected = ProjectTypeManager.get_default_tools_list("General", "Long")
        self.assertEqual(tools, expected)

    def test_get_enabled_tools_falls_back_to_default(self):
        self.pm.new_project("General")
        self.pm.project_data.get("meta", {}).pop("enabled_tools", None)
        tools = self.pm.get_enabled_tools()
        expected = ProjectTypeManager.get_default_tools("General", "Long")
        self.assertEqual(tools, expected)

    def test_set_enabled_tools_ensures_required_and_modules(self):
        self.pm.new_project("Poetry")
        self.pm.set_enabled_tools(["timeline", "relationship", "evidence_board"])
        enabled = self.pm.get_enabled_tools()
        self.assertIn("outline", enabled)
        self.assertIn("script", enabled)
        self.assertIn("timelines", self.pm.project_data)
        self.assertIn("relationships", self.pm.project_data)
        self.assertIn("evidence_data", self.pm.project_data)


if __name__ == "__main__":
    unittest.main()
