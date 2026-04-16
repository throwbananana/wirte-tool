import json

from writer_app.core.commands_base import Command
from writer_app.core.tone_outline import ensure_tone_outline_defaults


class UpdateToneOutlineCommand(Command):
    """Replace the tone-outline module data with undo support."""

    def __init__(self, project_manager, old_data, new_data, description="更新基调大纲"):
        super().__init__(description)
        self.project_manager = project_manager
        self.old_data = json.loads(json.dumps(old_data or {}))
        self.new_data = json.loads(json.dumps(new_data or {}))

    def execute(self):
        normalized = ensure_tone_outline_defaults(
            self.new_data,
            uid_generator=self.project_manager._gen_uid,
        )
        self.project_manager.project_data["tone_outline"] = normalized
        self.project_manager.mark_modified("tone_outline")
        return True

    def undo(self):
        normalized = ensure_tone_outline_defaults(
            self.old_data,
            uid_generator=self.project_manager._gen_uid,
        )
        self.project_manager.project_data["tone_outline"] = normalized
        self.project_manager.mark_modified("tone_outline")
        return True
