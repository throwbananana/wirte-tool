import unittest

from writer_app.core.commands import (
    AddRelationshipEventCommand,
    EditLinkCommand,
)
from writer_app.core.history_manager import CommandHistory
from writer_app.core.models import ProjectManager


class TestRelationshipCommands(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()
        self.history = CommandHistory()
        rels = self.pm.get_relationships()
        rels["relationship_links"] = [
            {"source": "Alice", "target": "Bob", "label": "旧关系", "event_uids": [], "event_frame_ids": []}
        ]
        rels["relationship_events"] = []

    def test_edit_link_command_can_undo(self):
        rels = self.pm.get_relationships()
        cmd = EditLinkCommand(self.pm, 0, {"label": "新关系", "color": "#ff0000"})

        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual(rels["relationship_links"][0]["label"], "新关系")
        self.assertEqual(rels["relationship_links"][0]["color"], "#ff0000")

        self.assertTrue(self.history.undo())
        self.assertEqual(rels["relationship_links"][0]["label"], "旧关系")
        self.assertNotIn("color", rels["relationship_links"][0])

    def test_add_relationship_event_command_undo_restores_link_lists(self):
        rels = self.pm.get_relationships()
        cmd = AddRelationshipEventCommand(
            self.pm,
            0,
            {"chapter_title": "第一章", "content": "关系推进"},
        )

        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual(len(rels["relationship_events"]), 1)
        self.assertEqual(len(rels["relationship_links"][0]["event_uids"]), 1)
        self.assertEqual(len(rels["relationship_links"][0]["event_frame_ids"]), 1)

        self.assertTrue(self.history.undo())
        self.assertEqual(rels["relationship_events"], [])
        self.assertEqual(rels["relationship_links"][0]["event_uids"], [])
        self.assertEqual(rels["relationship_links"][0]["event_frame_ids"], [])


if __name__ == "__main__":
    unittest.main()
