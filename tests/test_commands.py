import unittest
from writer_app.core.models import ProjectManager
from writer_app.core.history_manager import CommandHistory
from writer_app.core.commands import AddNodeCommand, DeleteNodesCommand, EditNodeCommand

class TestCommands(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()
        self.history = CommandHistory()

    def test_add_node_command(self):
        root = self.pm.get_outline()
        # Ensure root UID
        root_uid = root.get("uid")
        
        new_node_data = {"name": "Test Node", "children": []}
        
        cmd = AddNodeCommand(self.pm, root_uid, new_node_data)
        
        # Execute
        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual(len(root["children"]), 1)
        self.assertEqual(root["children"][0]["name"], "Test Node")
        self.assertIsNotNone(root["children"][0].get("uid"))
        
        # Undo
        self.assertTrue(self.history.undo())
        self.assertEqual(len(root["children"]), 0)
        
        # Redo
        self.assertTrue(self.history.redo())
        self.assertEqual(len(root["children"]), 1)
        self.assertEqual(root["children"][0]["name"], "Test Node")

    def test_delete_nodes_command(self):
        root = self.pm.get_outline()
        child1 = {"name": "C1", "children": [], "uid": "c1"}
        child2 = {"name": "C2", "children": [], "uid": "c2"}
        root["children"] = [child1, child2]
        
        cmd = DeleteNodesCommand(self.pm, ["c1"])
        
        # Execute
        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual(len(root["children"]), 1)
        self.assertEqual(root["children"][0]["name"], "C2")
        
        # Undo
        self.assertTrue(self.history.undo())
        self.assertEqual(len(root["children"]), 2)
        self.assertEqual(root["children"][0]["name"], "C1")

    def test_delete_nodes_command_redo(self):
        root = self.pm.get_outline()
        child1 = {"name": "C1", "children": [], "uid": "c1"}
        child2 = {"name": "C2", "children": [], "uid": "c2"}
        child3 = {"name": "C3", "children": [], "uid": "c3"}
        root["children"] = [child1, child2, child3]

        cmd = DeleteNodesCommand(self.pm, ["c2"])

        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual([c["name"] for c in root["children"]], ["C1", "C3"])

        self.assertTrue(self.history.undo())
        self.assertEqual([c["name"] for c in root["children"]], ["C1", "C2", "C3"])

        self.assertTrue(self.history.redo())
        self.assertEqual([c["name"] for c in root["children"]], ["C1", "C3"])

    def test_edit_node_command(self):
        root = self.pm.get_outline()
        child = {"name": "Original", "content": "Old", "children": [], "uid": "c_edit"}
        root["children"].append(child)
        
        cmd = EditNodeCommand(self.pm, "c_edit", "Original", "New Name", "Old", "New Content")
        
        # Execute
        self.history.execute_command(cmd)
        self.assertEqual(child["name"], "New Name")
        self.assertEqual(child["content"], "New Content")
        
        # Undo
        self.history.undo()
        self.assertEqual(child["name"], "Original")
        self.assertEqual(child["content"], "Old")

    def test_add_node_command_insert_index_and_redo(self):
        root = self.pm.get_outline()
        root["children"] = [
            {"name": "A", "children": [], "uid": "A"},
            {"name": "B", "children": [], "uid": "B"},
            {"name": "C", "children": [], "uid": "C"},
        ]

        cmd = AddNodeCommand(self.pm, root.get("uid"), {"name": "NEW", "children": []}, insert_index=1)
        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual([c["name"] for c in root["children"]], ["A", "NEW", "B", "C"])

        self.assertTrue(self.history.undo())
        self.assertEqual([c["name"] for c in root["children"]], ["A", "B", "C"])

        self.assertTrue(self.history.redo())
        self.assertEqual([c["name"] for c in root["children"]], ["A", "NEW", "B", "C"])

if __name__ == '__main__':
    unittest.main()