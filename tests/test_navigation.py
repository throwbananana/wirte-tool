import unittest
from writer_app.core.models import ProjectManager


class TestBidirectionalNavigation(unittest.TestCase):
    """Tests for bidirectional outline-scene navigation."""

    def setUp(self):
        self.pm = ProjectManager()
        # Setup test data
        self._setup_test_data()

    def _setup_test_data(self):
        """Create test outline and scenes."""
        # Create outline structure
        outline = self.pm.get_outline()
        outline["uid"] = "root_uid"
        outline["children"] = [
            {"name": "Chapter 1", "uid": "ch1_uid", "children": [
                {"name": "Scene 1.1", "uid": "s11_uid", "children": []},
                {"name": "Scene 1.2", "uid": "s12_uid", "children": []}
            ]},
            {"name": "Chapter 2", "uid": "ch2_uid", "children": []}
        ]

        # Create scenes linked to outline
        scenes = self.pm.get_scenes()
        scenes.extend([
            {"name": "Scene A", "outline_ref_id": "s11_uid", "characters": ["Alice", "Bob"]},
            {"name": "Scene B", "outline_ref_id": "s11_uid", "characters": ["Bob"]},
            {"name": "Scene C", "outline_ref_id": "ch2_uid", "characters": ["Alice"]},
            {"name": "Scene D", "outline_ref_id": "", "characters": []}
        ])

        # Create characters
        chars = self.pm.get_characters()
        chars.extend([
            {"name": "Alice", "description": "Protagonist"},
            {"name": "Bob", "description": "Supporting"}
        ])

    def test_get_scenes_by_outline_uid(self):
        """Test getting scenes linked to an outline node."""
        # s11_uid should have 2 scenes
        scenes = self.pm.get_scenes_by_outline_uid("s11_uid")
        self.assertEqual(len(scenes), 2)
        self.assertEqual(scenes[0][1]["name"], "Scene A")
        self.assertEqual(scenes[1][1]["name"], "Scene B")

        # ch2_uid should have 1 scene
        scenes = self.pm.get_scenes_by_outline_uid("ch2_uid")
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0][1]["name"], "Scene C")

        # Non-existent uid should return empty
        scenes = self.pm.get_scenes_by_outline_uid("nonexistent")
        self.assertEqual(len(scenes), 0)

    def test_get_outline_node_for_scene(self):
        """Test getting outline node for a scene."""
        # Scene 0 should link to s11_uid
        node = self.pm.get_outline_node_for_scene(0)
        self.assertIsNotNone(node)
        self.assertEqual(node["uid"], "s11_uid")
        self.assertEqual(node["name"], "Scene 1.1")

        # Scene 3 has no link
        node = self.pm.get_outline_node_for_scene(3)
        self.assertIsNone(node)

        # Invalid index
        node = self.pm.get_outline_node_for_scene(99)
        self.assertIsNone(node)

    def test_get_outline_scene_links(self):
        """Test getting all outline-scene links."""
        links = self.pm.get_outline_scene_links()

        self.assertIn("s11_uid", links)
        self.assertEqual(links["s11_uid"], [0, 1])

        self.assertIn("ch2_uid", links)
        self.assertEqual(links["ch2_uid"], [2])

    def test_link_scene_to_outline(self):
        """Test linking a scene to an outline node."""
        # Link scene 3 to ch1_uid
        result = self.pm.link_scene_to_outline(3, "ch1_uid")
        self.assertTrue(result)

        scenes = self.pm.get_scenes()
        self.assertEqual(scenes[3]["outline_ref_id"], "ch1_uid")

        # Linking to non-existent outline should fail
        result = self.pm.link_scene_to_outline(0, "nonexistent")
        self.assertFalse(result)

    def test_unlink_scene_from_outline(self):
        """Test unlinking a scene from outline."""
        result = self.pm.unlink_scene_from_outline(0)
        self.assertTrue(result)

        scenes = self.pm.get_scenes()
        self.assertEqual(scenes[0]["outline_ref_id"], "")

    def test_get_outline_path(self):
        """Test getting path string for outline node."""
        # Path to Scene 1.1
        path = self.pm.get_outline_path("s11_uid")
        self.assertEqual(path, "项目大纲 > Chapter 1 > Scene 1.1")

        # Path to Chapter 2
        path = self.pm.get_outline_path("ch2_uid")
        self.assertEqual(path, "项目大纲 > Chapter 2")

        # Non-existent
        path = self.pm.get_outline_path("nonexistent")
        self.assertEqual(path, "")

    def test_get_characters_in_scene(self):
        """Test getting characters in a scene."""
        chars = self.pm.get_characters_in_scene(0)
        self.assertEqual(chars, ["Alice", "Bob"])

        chars = self.pm.get_characters_in_scene(3)
        self.assertEqual(chars, [])

    def test_get_scenes_with_character(self):
        """Test getting scenes where a character appears."""
        scenes = self.pm.get_scenes_with_character("Alice")
        self.assertEqual(len(scenes), 2)
        self.assertEqual(scenes[0][0], 0)  # Scene A
        self.assertEqual(scenes[1][0], 2)  # Scene C

        scenes = self.pm.get_scenes_with_character("Bob")
        self.assertEqual(len(scenes), 2)

        scenes = self.pm.get_scenes_with_character("NonExistent")
        self.assertEqual(len(scenes), 0)

    def test_get_character_scene_matrix(self):
        """Test character-scene matrix."""
        matrix = self.pm.get_character_scene_matrix()

        self.assertIn("Alice", matrix)
        self.assertIn("Bob", matrix)

        self.assertEqual(matrix["Alice"], [0, 2])
        self.assertEqual(matrix["Bob"], [0, 1])


class TestOutlineNodeSearch(unittest.TestCase):
    """Tests for outline node search methods."""

    def setUp(self):
        self.pm = ProjectManager()
        outline = self.pm.get_outline()
        outline["uid"] = "root"
        outline["children"] = [
            {"name": "A", "uid": "a", "children": [
                {"name": "A1", "uid": "a1", "children": []},
                {"name": "A2", "uid": "a2", "children": []}
            ]},
            {"name": "B", "uid": "b", "children": []}
        ]

    def test_find_node_by_uid(self):
        """Test finding nodes by UID."""
        root = self.pm.get_outline()

        # Find root
        node = self.pm.find_node_by_uid(root, "root")
        self.assertEqual(node["name"], "项目大纲")

        # Find nested node
        node = self.pm.find_node_by_uid(root, "a1")
        self.assertEqual(node["name"], "A1")

        # Not found
        node = self.pm.find_node_by_uid(root, "nonexistent")
        self.assertIsNone(node)

    def test_find_parent_of_node_by_uid(self):
        """Test finding parent of a node."""
        root = self.pm.get_outline()

        # Parent of A1 should be A
        parent = self.pm.find_parent_of_node_by_uid(root, "a1")
        self.assertEqual(parent["uid"], "a")

        # Parent of root should be None
        parent = self.pm.find_parent_of_node_by_uid(root, "root")
        self.assertIsNone(parent)


if __name__ == '__main__':
    unittest.main()
