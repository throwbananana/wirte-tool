import unittest
import json
import os
from writer_app.core.models import ProjectManager

class TestProjectManager(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()

    def test_new_project(self):
        self.pm.new_project()
        outline = self.pm.get_outline()
        self.assertEqual(outline["name"], "项目大纲")
        self.assertEqual(len(outline["children"]), 0)
        self.assertFalse(self.pm.modified)

    def test_find_node_by_uid(self):
        root = self.pm.get_outline()
        # Ensure root has uid (ProjectManager creates it, but just in case)
        if "uid" not in root: root["uid"] = "root_uid"
        
        child = {"name": "Child", "children": [], "uid": "child_uid"}
        root["children"].append(child)
        
        found = self.pm.find_node_by_uid(root, "child_uid")
        self.assertEqual(found, child)
        
        found_root = self.pm.find_node_by_uid(root, root["uid"])
        self.assertEqual(found_root, root)
        
        self.assertIsNone(self.pm.find_node_by_uid(root, "non_existent"))

    def test_find_parent_of_node_by_uid(self):
        root = self.pm.get_outline()
        if "uid" not in root: root["uid"] = "root_uid"
        
        child = {"name": "Child", "children": [], "uid": "child_uid"}
        root["children"].append(child)
        
        parent = self.pm.find_parent_of_node_by_uid(root, "child_uid")
        self.assertEqual(parent, root)
        
        self.assertIsNone(self.pm.find_parent_of_node_by_uid(root, "root_uid"))

    def test_mark_modified(self):
        self.assertFalse(self.pm.modified)
        self.pm.mark_modified()
        self.assertTrue(self.pm.modified)

if __name__ == '__main__':
    unittest.main()