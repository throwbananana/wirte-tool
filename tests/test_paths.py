import tempfile
import unittest
from pathlib import Path

from writer_app.core.paths import AppPaths, get_app_paths


class AppPathsTests(unittest.TestCase):
    def _make_paths(self, root: Path) -> AppPaths:
        return AppPaths(
            repo_root=root,
            assets_dir=root / "assets",
            sample_data_dir=root / "sample_data",
            runtime_data_dir=root / "runtime_data",
            legacy_data_dir=root / "writer_data",
            docs_dir=root / "docs",
            tools_dir=root / "tools",
        )

    def test_ensure_layout_creates_expected_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._make_paths(Path(temp_dir))

            paths.ensure_layout()

            self.assertTrue(paths.assets_dir.is_dir())
            self.assertTrue(paths.sample_data_dir.is_dir())
            self.assertTrue(paths.runtime_data_dir.is_dir())
            self.assertTrue(paths.logs_dir().is_dir())
            self.assertTrue(paths.wiki_images_dir().is_dir())

    def test_find_data_file_prefers_runtime_then_sample_then_legacy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._make_paths(Path(temp_dir))
            paths.ensure_layout()

            sample_file = paths.sample_data_dir / "school_events.json"
            legacy_file = paths.legacy_data_dir / "school_events.json"
            runtime_file = paths.runtime_data_dir / "school_events.json"

            paths.legacy_data_dir.mkdir(parents=True, exist_ok=True)
            sample_file.write_text("sample", encoding="utf-8")
            legacy_file.write_text("legacy", encoding="utf-8")

            self.assertEqual(paths.find_data_file("school_events.json"), sample_file)

            runtime_file.write_text("runtime", encoding="utf-8")
            self.assertEqual(paths.find_data_file("school_events.json"), runtime_file)

    def test_find_asset_dir_prefers_existing_legacy_and_can_create_assets_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._make_paths(Path(temp_dir))
            paths.ensure_layout()

            legacy_sounds = paths.legacy_data_dir / "sounds"
            legacy_sounds.mkdir(parents=True, exist_ok=True)

            self.assertEqual(paths.find_asset_dir("sounds"), legacy_sounds)

            created_fonts = paths.find_asset_dir("fonts", create_in_assets=True)
            self.assertEqual(created_fonts, paths.assets_dir / "fonts")
            self.assertTrue(created_fonts.is_dir())


class CachedAppPathsTests(unittest.TestCase):
    def test_cached_paths_point_to_repository_root(self):
        get_app_paths.cache_clear()
        paths = get_app_paths()

        self.assertEqual(paths.repo_root, Path(__file__).resolve().parents[1])
        self.assertEqual(paths.docs_dir, paths.repo_root / "docs")
        self.assertEqual(paths.tools_dir, paths.repo_root / "tools")


if __name__ == "__main__":
    unittest.main()
