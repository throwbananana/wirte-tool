import json

from writer_app.core.commands_base import Command
from writer_app.core.event_bus import Events, get_event_bus


class AddWikiEntryCommand(Command):
    def __init__(self, project_manager, entry_data, description="添加世界观条目"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_data = json.loads(json.dumps(entry_data))
        self.added_index = -1

    def execute(self):
        entries = self.project_manager.get_world_entries()
        entries.append(self.entry_data)
        self.added_index = len(entries) - 1
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.WIKI_ENTRY_ADDED, entry_idx=self.added_index)
        return True

    def undo(self):
        entries = self.project_manager.get_world_entries()
        if 0 <= self.added_index < len(entries):
            del entries[self.added_index]
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.WIKI_ENTRY_DELETED, entry_idx=self.added_index)
            return True
        return False

class DeleteWikiEntryCommand(Command):
    def __init__(self, project_manager, entry_index, entry_data, description="删除世界观条目"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_index = entry_index
        self.deleted_data = json.loads(json.dumps(entry_data))

    def execute(self):
        entries = self.project_manager.get_world_entries()
        if 0 <= self.entry_index < len(entries):
            del entries[self.entry_index]
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.WIKI_ENTRY_DELETED, entry_idx=self.entry_index)
            return True
        return False

    def undo(self):
        entries = self.project_manager.get_world_entries()
        entries.insert(self.entry_index, self.deleted_data)
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.WIKI_ENTRY_ADDED, entry_idx=self.entry_index)
        return True

class EditWikiEntryCommand(Command):
    def __init__(self, project_manager, entry_index, old_data, new_data, description="编辑世界观条目"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_index = entry_index
        self.old_data = json.loads(json.dumps(old_data))
        self.new_data = json.loads(json.dumps(new_data))

    def execute(self):
        entries = self.project_manager.get_world_entries()
        if 0 <= self.entry_index < len(entries):
            entries[self.entry_index].update(self.new_data)
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.WIKI_ENTRY_UPDATED, entry_idx=self.entry_index)
            return True
        return False

    def undo(self):
        entries = self.project_manager.get_world_entries()
        if 0 <= self.entry_index < len(entries):
            entries[self.entry_index].update(self.old_data)
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.WIKI_ENTRY_UPDATED, entry_idx=self.entry_index)
            return True
        return False

# --- Relationship Commands ---
