import unittest
from writer_app.core.history_manager import CommandHistory
from writer_app.core.commands import Command


class MockCommand(Command):
    """Mock command for testing."""

    def __init__(self, description="mock", should_succeed=True):
        super().__init__(description)
        self.should_succeed = should_succeed
        self.execute_count = 0
        self.undo_count = 0

    def execute(self):
        self.execute_count += 1
        return self.should_succeed

    def undo(self):
        self.undo_count += 1
        return self.should_succeed


class TestCommandHistory(unittest.TestCase):
    """Tests for CommandHistory."""

    def setUp(self):
        self.history = CommandHistory(max_history=10)

    def test_execute_command(self):
        """Test executing a command."""
        cmd = MockCommand("test")
        result = self.history.execute_command(cmd)

        self.assertTrue(result)
        self.assertEqual(cmd.execute_count, 1)
        self.assertTrue(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

    def test_execute_failing_command(self):
        """Test executing a failing command."""
        cmd = MockCommand("fail", should_succeed=False)
        result = self.history.execute_command(cmd)

        self.assertFalse(result)
        self.assertFalse(self.history.can_undo())

    def test_undo(self):
        """Test undo operation."""
        cmd = MockCommand("test")
        self.history.execute_command(cmd)

        result = self.history.undo()
        self.assertTrue(result)
        self.assertEqual(cmd.undo_count, 1)
        self.assertFalse(self.history.can_undo())
        self.assertTrue(self.history.can_redo())

    def test_redo(self):
        """Test redo operation."""
        cmd = MockCommand("test")
        self.history.execute_command(cmd)
        self.history.undo()

        result = self.history.redo()
        self.assertTrue(result)
        self.assertEqual(cmd.execute_count, 2)
        self.assertTrue(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

    def test_redo_clears_on_new_command(self):
        """Test that redo stack clears when new command is executed."""
        cmd1 = MockCommand("cmd1")
        cmd2 = MockCommand("cmd2")

        self.history.execute_command(cmd1)
        self.history.undo()
        self.assertTrue(self.history.can_redo())

        self.history.execute_command(cmd2)
        self.assertFalse(self.history.can_redo())

    def test_max_history(self):
        """Test that max history is enforced."""
        for i in range(15):
            cmd = MockCommand(f"cmd{i}")
            self.history.execute_command(cmd)

        # Should only have 10 commands
        self.assertEqual(len(self.history.undo_stack), 10)

    def test_get_descriptions(self):
        """Test getting command descriptions."""
        cmd1 = MockCommand("first")
        cmd2 = MockCommand("second")

        self.history.execute_command(cmd1)
        self.history.execute_command(cmd2)

        self.assertEqual(self.history.get_undo_description(), "second")
        self.assertIsNone(self.history.get_redo_description())

        self.history.undo()
        self.assertEqual(self.history.get_undo_description(), "first")
        self.assertEqual(self.history.get_redo_description(), "second")

    def test_get_history_list(self):
        """Test getting history list for browsing."""
        cmd1 = MockCommand("cmd1")
        cmd2 = MockCommand("cmd2")
        cmd3 = MockCommand("cmd3")

        self.history.execute_command(cmd1)
        self.history.execute_command(cmd2)
        self.history.execute_command(cmd3)
        self.history.undo()

        history = self.history.get_history_list()

        self.assertEqual(len(history), 3)
        # First two are executed
        self.assertEqual(history[0][0], "cmd1")
        self.assertFalse(history[0][2])  # Not undone
        self.assertEqual(history[1][0], "cmd2")
        self.assertFalse(history[1][2])
        # Third is undone
        self.assertEqual(history[2][0], "cmd3")
        self.assertTrue(history[2][2])  # Is undone

    def test_undo_to_index(self):
        """Test undoing to a specific index."""
        for i in range(5):
            self.history.execute_command(MockCommand(f"cmd{i}"))

        # Undo to index 2 (should undo cmd4, cmd3)
        count = self.history.undo_to_index(2)
        self.assertEqual(count, 2)
        self.assertEqual(len(self.history.undo_stack), 3)

    def test_redo_to_index(self):
        """Test redoing to a specific index."""
        for i in range(5):
            self.history.execute_command(MockCommand(f"cmd{i}"))

        # Undo all
        for _ in range(5):
            self.history.undo()

        # Redo to index 2
        count = self.history.redo_to_index(2)
        self.assertEqual(count, 3)
        self.assertEqual(len(self.history.undo_stack), 3)

    def test_clear(self):
        """Test clearing history."""
        self.history.execute_command(MockCommand("test"))
        self.history.clear()

        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

    def test_get_stats(self):
        """Test getting history statistics."""
        cmd1 = MockCommand("cmd1")
        cmd2 = MockCommand("cmd2")

        self.history.execute_command(cmd1)
        self.history.execute_command(cmd2)
        self.history.undo()

        stats = self.history.get_stats()

        self.assertEqual(stats["undo_count"], 1)
        self.assertEqual(stats["redo_count"], 1)
        self.assertEqual(stats["max_history"], 10)
        self.assertTrue(stats["can_undo"])
        self.assertTrue(stats["can_redo"])

    def test_listener_notification(self):
        """Test that listeners are notified on changes."""
        notifications = []

        def listener():
            notifications.append(True)

        self.history.add_listener(listener)

        cmd = MockCommand("test")
        self.history.execute_command(cmd)
        self.assertEqual(len(notifications), 1)

        self.history.undo()
        self.assertEqual(len(notifications), 2)

        self.history.redo()
        self.assertEqual(len(notifications), 3)

        self.history.clear()
        self.assertEqual(len(notifications), 4)

    def test_remove_listener(self):
        """Test removing a listener."""
        notifications = []

        def listener():
            notifications.append(True)

        self.history.add_listener(listener)
        self.history.execute_command(MockCommand("test"))
        self.assertEqual(len(notifications), 1)

        self.history.remove_listener(listener)
        self.history.execute_command(MockCommand("test2"))
        self.assertEqual(len(notifications), 1)  # No new notification


if __name__ == '__main__':
    unittest.main()
