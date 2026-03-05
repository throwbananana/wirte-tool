import unittest

from writer_app.core.commands import (
    AddEvidenceLinkCommand,
    AddEvidenceNodeCommand,
    DeleteEvidenceLinkCommand,
    EditEvidenceNodeCommand,
    UpdateEvidenceNodeLayoutCommand,
)
from writer_app.core.history_manager import CommandHistory
from writer_app.core.models import ProjectManager


class TestEvidenceCommands(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()
        self.history = CommandHistory()

    def test_add_evidence_node_command(self):
        node_data = {"name": "Clue A", "type": "clue", "description": "test"}
        cmd = AddEvidenceNodeCommand(self.pm, node_data, [100, 200])

        self.assertTrue(self.history.execute_command(cmd))
        rels = self.pm.get_relationships()
        self.assertEqual(len(rels["nodes"]), 1)
        added_uid = rels["nodes"][0]["uid"]
        self.assertEqual(rels["evidence_layout"][added_uid], [100, 200])

        self.assertTrue(self.history.undo())
        rels = self.pm.get_relationships()
        self.assertEqual(len(rels["nodes"]), 0)
        self.assertNotIn(added_uid, rels.get("evidence_layout", {}))

        self.assertTrue(self.history.redo())
        rels = self.pm.get_relationships()
        self.assertEqual(rels["nodes"][0]["uid"], added_uid)
        self.assertEqual(rels["evidence_layout"][added_uid], [100, 200])

    def test_edit_evidence_node_command(self):
        rels = self.pm.get_relationships()
        rels["nodes"].append({"uid": "n1", "name": "old", "description": "desc", "type": "clue"})
        rels["evidence_layout"]["n1"] = [0, 0]

        old_data = dict(rels["nodes"][0])
        new_data = {"name": "new", "description": "updated"}

        cmd = EditEvidenceNodeCommand(self.pm, "n1", old_data, new_data)
        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual(rels["nodes"][0]["name"], "new")
        self.assertEqual(rels["nodes"][0]["description"], "updated")

        self.assertTrue(self.history.undo())
        self.assertEqual(rels["nodes"][0]["name"], "old")
        self.assertEqual(rels["nodes"][0]["description"], "desc")

    def test_update_layout_and_links(self):
        rels = self.pm.get_relationships()
        rels["evidence_layout"]["n2"] = [10, 10]

        layout_cmd = UpdateEvidenceNodeLayoutCommand(self.pm, "n2", [50, 60])
        self.assertTrue(self.history.execute_command(layout_cmd))
        self.assertEqual(rels["evidence_layout"]["n2"], [50, 60])
        self.assertTrue(self.history.undo())
        self.assertEqual(rels["evidence_layout"]["n2"], [10, 10])

        link_data = {"source": "n2", "target": "n3", "label": "tests", "type": "relates_to"}
        add_link_cmd = AddEvidenceLinkCommand(self.pm, link_data)
        self.assertTrue(self.history.execute_command(add_link_cmd))
        self.assertEqual(len(rels["evidence_links"]), 1)
        self.assertEqual(rels["evidence_links"][0]["label"], "tests")

        delete_cmd = DeleteEvidenceLinkCommand(self.pm, 0)
        self.assertTrue(self.history.execute_command(delete_cmd))
        self.assertEqual(len(rels["evidence_links"]), 0)

        self.assertTrue(self.history.undo())
        self.assertEqual(len(rels["evidence_links"]), 1)
        self.assertEqual(rels["evidence_links"][0]["label"], "tests")


if __name__ == "__main__":
    unittest.main()
