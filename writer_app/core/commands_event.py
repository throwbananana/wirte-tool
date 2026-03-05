"""
Event Editor Commands - 事件编辑器的撤销/重做命令类

支持:
- AddEventCommand: 添加事件
- UpdateEventCommand: 更新事件
- DeleteEventCommand: 删除事件
- MoveEventCommand: 移动/重排序事件
- BatchEventCommand: 批量操作（复制粘贴多个）
"""

from __future__ import annotations

import json
from abc import ABC
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from writer_app.core.commands import Command

if TYPE_CHECKING:
    from writer_app.ui.editors.event_editor import EventEditorPanel


def _deep_copy(data: Any) -> Any:
    """Deep copy using JSON serialization."""
    return json.loads(json.dumps(data))


class EventCommand(Command):
    """Base class for event editor commands."""

    def __init__(self, editor: "EventEditorPanel", description: str = ""):
        super().__init__(description)
        self.editor = editor

    @property
    def events(self) -> List[Dict]:
        """Shortcut to editor's events list."""
        return self.editor.events


class AddEventCommand(EventCommand):
    """Add a new event to the list."""

    def __init__(
        self,
        editor: "EventEditorPanel",
        event_data: Dict,
        insert_index: Optional[int] = None,
        description: str = "添加事件",
    ):
        super().__init__(editor, description)
        self.event_data = _deep_copy(event_data)
        self.insert_index = insert_index
        self.added_index: int = -1

    def execute(self) -> bool:
        try:
            if self.insert_index is not None and 0 <= self.insert_index <= len(self.events):
                self.events.insert(self.insert_index, _deep_copy(self.event_data))
                self.added_index = self.insert_index
            else:
                self.events.append(_deep_copy(self.event_data))
                self.added_index = len(self.events) - 1
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        try:
            if 0 <= self.added_index < len(self.events):
                del self.events[self.added_index]
                return True
            return False
        except Exception:
            return False


class UpdateEventCommand(EventCommand):
    """Update an existing event's data."""

    def __init__(
        self,
        editor: "EventEditorPanel",
        event_index: int,
        old_data: Dict,
        new_data: Dict,
        description: str = "更新事件",
    ):
        super().__init__(editor, description)
        self.event_index = event_index
        self.old_data = _deep_copy(old_data)
        self.new_data = _deep_copy(new_data)

    def execute(self) -> bool:
        try:
            if 0 <= self.event_index < len(self.events):
                self.events[self.event_index] = _deep_copy(self.new_data)
                return True
            return False
        except Exception:
            return False

    def undo(self) -> bool:
        try:
            if 0 <= self.event_index < len(self.events):
                self.events[self.event_index] = _deep_copy(self.old_data)
                return True
            return False
        except Exception:
            return False


class DeleteEventCommand(EventCommand):
    """Delete an event from the list."""

    def __init__(
        self,
        editor: "EventEditorPanel",
        event_index: int,
        description: str = "删除事件",
    ):
        super().__init__(editor, description)
        self.event_index = event_index
        self.deleted_data: Optional[Dict] = None

    def execute(self) -> bool:
        try:
            if 0 <= self.event_index < len(self.events):
                self.deleted_data = _deep_copy(self.events[self.event_index])
                del self.events[self.event_index]
                return True
            return False
        except Exception:
            return False

    def undo(self) -> bool:
        try:
            if self.deleted_data is not None:
                self.events.insert(self.event_index, _deep_copy(self.deleted_data))
                return True
            return False
        except Exception:
            return False


class MoveEventCommand(EventCommand):
    """Move an event from one position to another (reorder)."""

    def __init__(
        self,
        editor: "EventEditorPanel",
        from_index: int,
        to_index: int,
        description: str = "移动事件",
    ):
        super().__init__(editor, description)
        self.from_index = from_index
        self.to_index = to_index

    def execute(self) -> bool:
        try:
            if not (0 <= self.from_index < len(self.events)):
                return False
            if not (0 <= self.to_index < len(self.events)):
                return False
            if self.from_index == self.to_index:
                return False

            event = self.events.pop(self.from_index)
            self.events.insert(self.to_index, event)
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        try:
            if not (0 <= self.to_index < len(self.events)):
                return False

            event = self.events.pop(self.to_index)
            self.events.insert(self.from_index, event)
            return True
        except Exception:
            return False


class BatchEventCommand(EventCommand):
    """Execute multiple event commands as a single undoable operation."""

    def __init__(
        self,
        editor: "EventEditorPanel",
        commands: List[EventCommand],
        description: str = "批量操作",
    ):
        super().__init__(editor, description)
        self.commands = commands
        self._executed_count = 0

    def execute(self) -> bool:
        try:
            self._executed_count = 0
            for cmd in self.commands:
                if cmd.execute():
                    self._executed_count += 1
                else:
                    # Rollback on failure
                    self._rollback()
                    return False
            return True
        except Exception:
            self._rollback()
            return False

    def undo(self) -> bool:
        try:
            # Undo in reverse order
            for cmd in reversed(self.commands[: self._executed_count]):
                cmd.undo()
            return True
        except Exception:
            return False

    def _rollback(self):
        """Rollback already executed commands on failure."""
        for i in range(self._executed_count - 1, -1, -1):
            self.commands[i].undo()
        self._executed_count = 0


class DuplicateEventCommand(EventCommand):
    """Duplicate an event with a new ID."""

    def __init__(
        self,
        editor: "EventEditorPanel",
        source_index: int,
        new_id_suffix: str = "_copy",
        description: str = "复制事件",
    ):
        super().__init__(editor, description)
        self.source_index = source_index
        self.new_id_suffix = new_id_suffix
        self.added_index: int = -1
        self.duplicated_data: Optional[Dict] = None

    def execute(self) -> bool:
        try:
            if not (0 <= self.source_index < len(self.events)):
                return False

            source = self.events[self.source_index]
            self.duplicated_data = _deep_copy(source)

            # Generate new ID
            old_id = self.duplicated_data.get("id", "event")
            new_id = old_id + self.new_id_suffix
            # Ensure uniqueness
            existing_ids = {e.get("id") for e in self.events}
            counter = 1
            while new_id in existing_ids:
                new_id = f"{old_id}{self.new_id_suffix}{counter}"
                counter += 1
            self.duplicated_data["id"] = new_id

            # Insert after source
            insert_pos = self.source_index + 1
            self.events.insert(insert_pos, self.duplicated_data)
            self.added_index = insert_pos
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        try:
            if 0 <= self.added_index < len(self.events):
                del self.events[self.added_index]
                return True
            return False
        except Exception:
            return False
