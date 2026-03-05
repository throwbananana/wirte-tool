import unittest
from writer_app.core.theme import ThemeManager

class TestThemeManager(unittest.TestCase):
    def setUp(self):
        self.theme_manager = ThemeManager()

    def test_themes_exist(self):
        self.assertIn("Light", self.theme_manager.THEMES)
        self.assertIn("Dark", self.theme_manager.THEMES)

    def test_get_color(self):
        self.theme_manager.set_theme("Light")
        self.assertEqual(self.theme_manager.get_color("bg_primary"), "#FFFFFF")
        
        self.theme_manager.set_theme("Dark")
        self.assertEqual(self.theme_manager.get_color("bg_primary"), "#2D2D2D")

    def test_new_editor_keys(self):
        """Verify new editor keys exist in all themes."""
        required_keys = [
            "editor_scene_header_bg", "editor_scene_header_fg",
            "editor_char_name_fg", "editor_paren_fg",
            "editor_trans_fg", "editor_dimmed_fg",
            "editor_wiki_fg", "editor_wiki_deep_bg", "editor_wiki_deep_fg"
        ]
        
        for theme_name in ["Light", "Dark"]:
            theme = self.theme_manager.THEMES[theme_name]
            for key in required_keys:
                self.assertIn(key, theme, f"Key '{key}' missing in {theme_name} theme")

    def test_new_alibi_keys(self):
        """Verify new alibi timeline keys exist in all themes."""
        required_keys = [
            "alibi_bg", "alibi_header_bg", "alibi_header_fg",
            "alibi_grid", "alibi_text", 
            "alibi_cell_bg", "alibi_cell_outline", "alibi_cell_text"
        ]
        
        for theme_name in ["Light", "Dark"]:
            theme = self.theme_manager.THEMES[theme_name]
            for key in required_keys:
                self.assertIn(key, theme, f"Key '{key}' missing in {theme_name} theme")

    def test_new_table_keys(self):
        """Verify new table view keys exist in all themes."""
        required_keys = [
            "table_level_0_bg", "table_level_5_bg",
            "table_has_content_fg", "table_status_draft_fg", "table_status_final_fg"
        ]
        
        for theme_name in ["Light", "Dark"]:
            theme = self.theme_manager.THEMES[theme_name]
            for key in required_keys:
                self.assertIn(key, theme, f"Key '{key}' missing in {theme_name} theme")

    def test_new_iceberg_keys(self):
        """Verify new world iceberg keys exist in all themes."""
        required_keys = [
            "iceberg_bg", "iceberg_deep_bg", "iceberg_surface_bg",
            "iceberg_line", "iceberg_text",
            "iceberg_entry_bg", "iceberg_entry_fg", "iceberg_entry_outline"
        ]
        
        for theme_name in ["Light", "Dark"]:
            theme = self.theme_manager.THEMES[theme_name]
            for key in required_keys:
                self.assertIn(key, theme, f"Key '{key}' missing in {theme_name} theme")

    def test_new_swimlane_keys(self):
        """Verify new swimlane keys exist in all themes."""
        required_keys = [
            "swimlane_header_line", "swimlane_block_fill", "swimlane_block_text"
        ]
        for theme_name in ["Light", "Dark"]:
            theme = self.theme_manager.THEMES[theme_name]
            for key in required_keys:
                self.assertIn(key, theme, f"Key '{key}' missing in {theme_name} theme")

    def test_new_beatsheet_keys(self):
        """Verify new beatsheet keys exist in all themes."""
        required_keys = [
            "beat_slot_bg", "beat_slot_outline",
            "beat_header_fill", "beat_header_outline",
            "beat_card_bg", "beat_card_outline", "beat_card_text"
        ]
        for theme_name in ["Light", "Dark"]:
            theme = self.theme_manager.THEMES[theme_name]
            for key in required_keys:
                self.assertIn(key, theme, f"Key '{key}' missing in {theme_name} theme")

    def test_new_calendar_keys(self):
        """Verify new calendar keys exist in all themes."""
        required_keys = [
            "calendar_event_bg", "calendar_event_fg"
        ]
        for theme_name in ["Light", "Dark"]:
            theme = self.theme_manager.THEMES[theme_name]
            for key in required_keys:
                self.assertIn(key, theme, f"Key '{key}' missing in {theme_name} theme")

if __name__ == "__main__":
    unittest.main()
