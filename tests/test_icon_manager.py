import unittest
from unittest import mock

from writer_app.core.icon_manager import IconManager


class TestIconManager(unittest.TestCase):
    def tearDown(self):
        IconManager._instance = None

    def test_regular_font_falls_back_to_filled_font(self):
        IconManager._instance = None

        with mock.patch.object(IconManager, "_load_resources", autospec=True):
            manager = IconManager()

        manager.loaded_fonts = {"FluentSystemIcons-Filled.ttf"}

        self.assertEqual(manager.get_font(size=14, style="regular"), ("FluentSystemIcons-Filled", 14))

    def test_missing_icon_fonts_fall_back_to_system_font(self):
        IconManager._instance = None

        with mock.patch.object(IconManager, "_load_resources", autospec=True):
            manager = IconManager()

        manager.loaded_fonts = set()

        self.assertEqual(manager.get_font(size=12, style="filled"), ("Segoe UI Symbol", 12))
