from collections import deque
from datetime import datetime
import logging
from contextlib import contextmanager

from writer_app.core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class CommandHistory:
    """Manages command history for undo/redo operations."""

    def __init__(self, max_history=100):
        self.undo_stack = deque()
        self.redo_stack = deque()
        self.max_history = max_history
        self._listeners = []

    def add_listener(self, callback):
        """Add a listener for history changes."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        """Remove a history change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        """Notify all listeners of history change."""
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                logger.warning(f"History listener error: {e}")

    def execute_command(self, command, use_batch_events=True):
        """
        Execute a command and add it to history.

        Args:
            command: The command to execute
            use_batch_events: If True, batch events during command execution
                             and publish them all at once on success (default True)
        """
        bus = get_event_bus()

        # Start batch mode if requested
        if use_batch_events:
            bus.begin_batch()

        try:
            if command.execute():
                # Add timestamp to command for history browsing
                command._executed_at = datetime.now()
                self.undo_stack.append(command)
                if len(self.undo_stack) > self.max_history:
                    self.undo_stack.popleft()
                self.redo_stack.clear()
                self._notify_listeners()
                logger.debug(f"Executed command: {command.description}")

                # End batch and publish all collected events
                if use_batch_events:
                    bus.end_batch()
                return True
            else:
                # Command execution returned False
                if use_batch_events:
                    bus.cancel_batch()
                return False
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            # Cancel batch on exception
            if use_batch_events:
                bus.cancel_batch()
        return False

    def undo(self, use_batch_events=True):
        """Undo the last command."""
        if self.undo_stack:
            command = self.undo_stack.pop()
            bus = get_event_bus()

            if use_batch_events:
                bus.begin_batch()

            try:
                if command.undo():
                    self.redo_stack.append(command)
                    self._notify_listeners()
                    logger.debug(f"Undone command: {command.description}")
                    if use_batch_events:
                        bus.end_batch()
                    return True
                else:
                    # Put command back if undo returned False
                    self.undo_stack.append(command)
                    if use_batch_events:
                        bus.cancel_batch()
            except Exception as e:
                logger.error(f"Undo failed: {e}", exc_info=True)
                # Put command back if undo failed
                self.undo_stack.append(command)
                if use_batch_events:
                    bus.cancel_batch()
        return False

    def redo(self, use_batch_events=True):
        """Redo the last undone command."""
        if self.redo_stack:
            command = self.redo_stack.pop()
            bus = get_event_bus()

            if use_batch_events:
                bus.begin_batch()

            try:
                if command.execute():
                    self.undo_stack.append(command)
                    self._notify_listeners()
                    logger.debug(f"Redone command: {command.description}")
                    if use_batch_events:
                        bus.end_batch()
                    return True
                else:
                    # Put command back if redo returned False
                    self.redo_stack.append(command)
                    if use_batch_events:
                        bus.cancel_batch()
            except Exception as e:
                logger.error(f"Redo failed: {e}", exc_info=True)
                # Put command back if redo failed
                self.redo_stack.append(command)
                if use_batch_events:
                    bus.cancel_batch()
        return False

    def clear(self):
        """Clear all history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._notify_listeners()
        logger.debug("History cleared")

    def can_undo(self):
        """Check if undo is available."""
        return len(self.undo_stack) > 0

    def can_redo(self):
        """Check if redo is available."""
        return len(self.redo_stack) > 0

    def get_undo_description(self):
        """Get description of the command that would be undone."""
        if self.undo_stack:
            return self.undo_stack[-1].description
        return None

    def get_redo_description(self):
        """Get description of the command that would be redone."""
        if self.redo_stack:
            return self.redo_stack[-1].description
        return None

    def get_history_list(self, include_redo=True):
        """
        Get list of all commands in history for browsing.

        Returns:
            List of tuples: (description, timestamp, is_undone)
        """
        history = []

        # Undo stack (executed commands)
        for cmd in self.undo_stack:
            timestamp = getattr(cmd, '_executed_at', None)
            history.append((
                cmd.description,
                timestamp,
                False  # Not undone
            ))

        if include_redo:
            # Redo stack (undone commands)
            for cmd in reversed(list(self.redo_stack)):
                timestamp = getattr(cmd, '_executed_at', None)
                history.append((
                    cmd.description,
                    timestamp,
                    True  # Undone
                ))

        return history

    def undo_to_index(self, target_index):
        """
        Undo until reaching a specific point in history.

        Args:
            target_index: Index in the undo stack to reach (0 = oldest)

        Returns:
            Number of commands undone
        """
        current_index = len(self.undo_stack) - 1
        count = 0

        while current_index > target_index and self.undo_stack:
            if self.undo():
                count += 1
                current_index -= 1
            else:
                break

        return count

    def redo_to_index(self, target_index):
        """
        Redo until reaching a specific point in history.

        Args:
            target_index: Target index in undo stack

        Returns:
            Number of commands redone
        """
        count = 0

        while len(self.undo_stack) <= target_index and self.redo_stack:
            if self.redo():
                count += 1
            else:
                break

        return count

    def get_stats(self):
        """Get statistics about the history."""
        return {
            "undo_count": len(self.undo_stack),
            "redo_count": len(self.redo_stack),
            "max_history": self.max_history,
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo()
        }


class TransactionContext:
    """
    事务上下文管理器，用于批量操作。

    在事务期间，所有事件会被收集并在成功时统一发布，
    失败时取消所有待发布事件。

    用法:
        with TransactionContext():
            # 执行多个操作
            command_history.execute_command(cmd1, use_batch_events=False)
            command_history.execute_command(cmd2, use_batch_events=False)
            # 事务结束时自动发布所有事件

        # 或者处理异常:
        try:
            with TransactionContext():
                # 操作...
                raise ValueError("出错了")
        except ValueError:
            # 事件已被取消
            pass
    """

    def __init__(self):
        self._bus = None

    def __enter__(self):
        self._bus = get_event_bus()
        self._bus.begin_batch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # 没有异常，发布所有事件
            self._bus.end_batch()
        else:
            # 有异常，取消所有事件
            self._bus.cancel_batch()
        # 不抑制异常
        return False


@contextmanager
def transaction():
    """
    事务上下文管理器的函数形式。

    用法:
        with transaction():
            # 执行多个操作
            pass
    """
    bus = get_event_bus()
    bus.begin_batch()
    try:
        yield
        bus.end_batch()
    except Exception:
        bus.cancel_batch()
        raise
