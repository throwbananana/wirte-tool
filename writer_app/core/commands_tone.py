import json

from writer_app.core.commands_base import Command
from writer_app.core.tone_outline import ensure_tone_outline_defaults


class UpdateToneOutlineCommand(Command):
    """Replace the tone-outline module data with undo support."""

    def __init__(
        self,
        project_manager,
        old_data,
        new_data,
        description="更新基调大纲",
        before_selection=None,
        after_selection=None,
        selection_restorer=None,
    ):
        super().__init__(description)
        self.project_manager = project_manager
        self.old_data = json.loads(json.dumps(old_data or {}))
        self.new_data = json.loads(json.dumps(new_data or {}))
        self.before_selection = json.loads(json.dumps(before_selection or {}))
        self.after_selection = json.loads(json.dumps(after_selection or {}))
        self.selection_restorer = selection_restorer

    def _restore_selection(self, snapshot):
        if self.selection_restorer:
            self.selection_restorer(snapshot)

    def execute(self):
        normalized = ensure_tone_outline_defaults(
            self.new_data,
            uid_generator=self.project_manager._gen_uid,
        )
        self.project_manager.project_data["tone_outline"] = normalized
        self._restore_selection(self.after_selection)
        self.project_manager.mark_modified("tone_outline")
        return True

    def undo(self):
        normalized = ensure_tone_outline_defaults(
            self.old_data,
            uid_generator=self.project_manager._gen_uid,
        )
        self.project_manager.project_data["tone_outline"] = normalized
        self._restore_selection(self.before_selection)
        self.project_manager.mark_modified("tone_outline")
        return True
