import unittest
import tempfile
import shutil
from pathlib import Path
from writer_app.core.models import ProjectManager
from writer_app.core.backup import BackupManager


class TestBackupManager(unittest.TestCase):
    """Tests for BackupManager."""

    def setUp(self):
        self.pm = ProjectManager()
        self.temp_dir = tempfile.mkdtemp()
        self.backup_manager = BackupManager(
            self.pm,
            interval_minutes=1,
            max_backups=5,
            backup_dir=self.temp_dir
        )
        # Set up a fake current file
        self.pm.current_file = str(Path(self.temp_dir) / "test_project.writerproj")

    def tearDown(self):
        self.backup_manager.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_perform_backup(self):
        """Test creating a backup."""
        # Add some data
        self.pm.get_characters().append({"name": "Test Character"})

        path = self.backup_manager.perform_backup(force=True)

        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertTrue(path.suffix == ".writerproj")

    def test_list_backups(self):
        """Test listing backups."""
        # Create multiple backups
        self.backup_manager.perform_backup(force=True)
        self.backup_manager.perform_backup(force=True)

        backups = self.backup_manager.list_backups()

        self.assertEqual(len(backups), 2)
        # Should be sorted newest first
        self.assertGreaterEqual(backups[0][1], backups[1][1])

    def test_restore_backup(self):
        """Test restoring from a backup."""
        # Add initial data
        self.pm.get_characters().append({"name": "Original"})

        # Create backup
        backup_path = self.backup_manager.perform_backup(force=True)

        # Modify data
        self.pm.get_characters().clear()
        self.pm.get_characters().append({"name": "Modified"})

        # Restore
        result = self.backup_manager.restore_backup(backup_path)

        self.assertTrue(result)
        self.assertEqual(len(self.pm.get_characters()), 1)
        self.assertEqual(self.pm.get_characters()[0]["name"], "Original")

    def test_delete_backup(self):
        """Test deleting a backup."""
        path = self.backup_manager.perform_backup(force=True)
        self.assertTrue(path.exists())

        result = self.backup_manager.delete_backup(path)

        self.assertTrue(result)
        self.assertFalse(path.exists())

    def test_clear_all_backups(self):
        """Test clearing all backups."""
        # Create multiple backups
        for _ in range(3):
            self.backup_manager.perform_backup(force=True)

        count = self.backup_manager.clear_all_backups()

        self.assertEqual(count, 3)
        self.assertEqual(len(self.backup_manager.list_backups()), 0)

    def test_max_backups_pruning(self):
        """Test that old backups are pruned."""
        # Create more backups than max
        for i in range(7):
            self.pm.project_data["meta"]["version"] = str(i)
            self.backup_manager.perform_backup(force=True)

        backups = self.backup_manager.list_backups()

        # Should only have max_backups
        self.assertLessEqual(len(backups), 5)

    def test_backup_dir_creation(self):
        """Test that backup directory is created if it doesn't exist."""
        new_dir = Path(self.temp_dir) / "new_backup_dir"
        self.backup_manager.set_backup_dir(new_dir)

        # Perform backup - should create directory
        self.backup_manager.perform_backup(force=True)

        self.assertTrue(new_dir.exists())

    def test_get_backup_dir(self):
        """Test getting backup directory."""
        custom_dir = Path(self.temp_dir) / "custom"
        self.backup_manager.set_backup_dir(custom_dir)

        self.assertEqual(self.backup_manager.get_backup_dir(), custom_dir)

    def test_restore_nonexistent_backup(self):
        """Test restoring from a non-existent backup."""
        result = self.backup_manager.restore_backup("/nonexistent/path.writerproj")
        self.assertFalse(result)

    def test_delete_nonexistent_backup(self):
        """Test deleting a non-existent backup."""
        result = self.backup_manager.delete_backup("/nonexistent/path.writerproj")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
