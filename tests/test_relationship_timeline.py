import unittest
from unittest.mock import MagicMock
from writer_app.core.models import ProjectManager

class TestRelationshipTimeline(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager()
        self.pm.new_project()

    def test_snapshot_management(self):
        # 1. Add some initial links
        rels = self.pm.get_relationships()
        rels["relationship_links"] = [{"source": "A", "target": "B", "label": "Friend"}]
        
        # 2. Add Snapshot 1
        idx1 = self.pm.add_relationship_snapshot("Start")
        self.assertEqual(idx1, 0)
        
        # 3. Change links
        rels["relationship_links"] = [{"source": "A", "target": "B", "label": "Enemy"}]
        
        # 4. Add Snapshot 2
        idx2 = self.pm.add_relationship_snapshot("End")
        self.assertEqual(idx2, 1)
        
        # 5. Verify Snapshots
        snapshots = self.pm.get_relationship_snapshots()
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0]["links"][0]["label"], "Friend")
        self.assertEqual(snapshots[1]["links"][0]["label"], "Enemy")
        
        # 6. Delete Snapshot
        self.pm.delete_relationship_snapshot(0)
        snapshots = self.pm.get_relationship_snapshots()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["name"], "End")

if __name__ == '__main__':
    unittest.main()
