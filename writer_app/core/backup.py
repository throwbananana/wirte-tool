import os
import json
import time
import threading
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages automatic backups of project data."""

    def __init__(self, project_manager, interval_minutes=5, max_backups=50, backup_dir=None):
        self.project_manager = project_manager
        self.interval_minutes = interval_minutes
        self.max_backups = max_backups
        self.running = False
        self.thread = None
        self._lock = threading.Lock()

        # Use user's home directory for backups by default
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            # Default to user's .writer_tool/backups directory
            user_home = Path.home()
            self.backup_dir = user_home / ".writer_tool" / "backups"

    def set_backup_dir(self, path):
        """Set custom backup directory."""
        self.backup_dir = Path(path)
        logger.info(f"Backup directory set to: {self.backup_dir}")

    def get_backup_dir(self):
        """Get current backup directory."""
        return self.backup_dir

    def start(self):
        """Start the auto-backup background thread."""
        if self.running:
            return

        self.running = True
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
            self.running = False
            return

        self.thread = threading.Thread(target=self._loop, daemon=True, name="BackupThread")
        self.thread.start()
        logger.info(f"Auto-backup started. Interval: {self.interval_minutes} min. Dir: {self.backup_dir}")

    def stop(self):
        """Stop the auto-backup thread."""
        self.running = False
        logger.info("Auto-backup stopped.")

    def _loop(self):
        """Background loop for periodic backups."""
        while self.running:
            time.sleep(self.interval_minutes * 60)
            if self.running and self.project_manager.current_file:
                self.perform_backup()

    def perform_backup(self, force=False):
        """
        Perform a backup of the current project state.

        Args:
            force: If True, backup even if project hasn't been modified
        """
        with self._lock:
            try:
                # Check if there's something to backup
                if not self.project_manager.current_file and not force:
                    return None

                # Ensure backup directory exists
                self.backup_dir.mkdir(parents=True, exist_ok=True)

                # Generate backup filename
                if self.project_manager.current_file:
                    current_path = Path(self.project_manager.current_file)
                    base_name = current_path.stem
                else:
                    base_name = "untitled"

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup_filename = f"{base_name}_{timestamp}.writerproj"
                backup_path = self.backup_dir / backup_filename

                # Serialize current memory state (includes unsaved changes)
                data = self.project_manager.project_data
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                logger.info(f"Backup created: {backup_path}")
                self._prune_old_backups()
                return backup_path

            except Exception as e:
                logger.error(f"Backup failed: {e}", exc_info=True)
                return None

    def _prune_old_backups(self):
        """Remove old backups exceeding max_backups limit."""
        try:
            # Get all backup files sorted by modification time (newest first)
            files = sorted(
                self.backup_dir.glob("*.writerproj"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            # Remove excess backups
            if len(files) > self.max_backups:
                for f in files[self.max_backups:]:
                    f.unlink()
                    logger.debug(f"Pruned old backup: {f}")

        except Exception as e:
            logger.warning(f"Backup pruning failed: {e}")

    def list_backups(self):
        """
        List all available backups.

        Returns:
            List of tuples: (backup_path, modification_time, size_bytes)
        """
        backups = []
        try:
            if not self.backup_dir.exists():
                return backups

            for f in self.backup_dir.glob("*.writerproj"):
                stat = f.stat()
                backups.append((
                    f,
                    datetime.fromtimestamp(stat.st_mtime),
                    stat.st_size
                ))

            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x[1], reverse=True)

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")

        return backups

    def restore_backup(self, backup_path):
        """
        Restore project from a backup file.

        Args:
            backup_path: Path to the backup file to restore

        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.project_manager.project_data = data
            self.project_manager.modified = True
            self.project_manager.notify_listeners()
            logger.info(f"Restored from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup: {e}", exc_info=True)
            return False

    def delete_backup(self, backup_path):
        """
        Delete a specific backup file.

        Args:
            backup_path: Path to the backup file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_path)
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"Deleted backup: {backup_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    def clear_all_backups(self):
        """Delete all backup files."""
        try:
            count = 0
            for f in self.backup_dir.glob("*.writerproj"):
                f.unlink()
                count += 1
            logger.info(f"Cleared {count} backups")
            return count

        except Exception as e:
            logger.error(f"Failed to clear backups: {e}")
            return 0
