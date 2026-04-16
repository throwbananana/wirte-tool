import unittest

from writer_app.core.commands import (
    AddFactionCommand,
    AddFactionMemberCommand,
    AddRelationshipEventCommand,
    AddRelationshipSnapshotCommand,
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

    def test_add_relationship_snapshot_command_supports_undo(self):
        rels = self.pm.get_relationships()
        cmd = AddRelationshipSnapshotCommand(
            self.pm,
            {"name": "关键帧 1", "links": [{"source": "Alice", "target": "Bob"}], "timestamp": 1.0},
        )

        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual(len(rels.get("snapshots", [])), 1)
        self.assertEqual(rels["snapshots"][0]["name"], "关键帧 1")

        self.assertTrue(self.history.undo())
        self.assertEqual(rels.get("snapshots", []), [])

    def test_add_faction_member_command_is_idempotent_and_undoable(self):
        faction_uid = self.pm.add_faction("白塔会")
        factions = self.pm.get_factions()
        cmd = AddFactionMemberCommand(
            self.pm,
            faction_uid,
            {"char_uid": "char-1", "char_name": "Alice", "role": "成员"},
        )

        self.assertTrue(self.history.execute_command(cmd))
        self.assertEqual(len(factions[0].get("members", [])), 1)

        duplicate_cmd = AddFactionMemberCommand(
            self.pm,
            faction_uid,
            {"char_uid": "char-1", "char_name": "Alice", "role": "成员"},
        )
        self.assertTrue(self.history.execute_command(duplicate_cmd))
        self.assertEqual(len(factions[0].get("members", [])), 1)

        self.assertTrue(self.history.undo())
        self.assertEqual(len(factions[0].get("members", [])), 1)

        self.assertTrue(self.history.undo())
        self.assertEqual(factions[0].get("members", []), [])

    def test_add_faction_command_creates_and_undoes_wiki_entry(self):
        world_entries = self.pm.get_world_entries()
        cmd = AddFactionCommand(self.pm, "白塔会")

        self.assertTrue(self.history.execute_command(cmd))
        factions = self.pm.get_factions()
        self.assertEqual(len(factions), 1)
        self.assertEqual(factions[0]["name"], "白塔会")
        self.assertTrue(any(entry.get("name") == "白塔会" and entry.get("faction_uid") == cmd.added_uid for entry in world_entries))

        self.assertTrue(self.history.undo())
        self.assertEqual(self.pm.get_factions(), [])
        self.assertFalse(any(entry.get("faction_uid") == cmd.added_uid for entry in world_entries))


if __name__ == "__main__":
    unittest.main()
