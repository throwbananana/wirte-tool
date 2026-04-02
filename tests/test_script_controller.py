import unittest
import sys
from unittest.mock import Mock, patch

sys.modules.setdefault("pyttsx3", Mock())

from writer_app.controllers.script_controller import ScriptController


class TestScriptController(unittest.TestCase):
    @patch("writer_app.controllers.script_controller.CharacterDialog")
    def test_edit_character_executes_command(self, mock_dialog_cls):
        controller = ScriptController.__new__(ScriptController)
        controller.parent = Mock()
        controller.parent.winfo_toplevel.return_value = Mock()
        controller.char_listbox = Mock()
        controller.char_listbox.curselection.return_value = (0,)
        controller.project_manager = Mock()
        controller.project_manager.get_characters.return_value = [
            {"name": "旧角色", "description": "旧描述", "tags": ["旧标签"]}
        ]
        controller.config_manager = Mock()
        controller.config_manager.get.return_value = []
        controller.current_char_tags = ["新标签"]
        controller.command_executor = Mock()

        dialog = Mock()
        dialog.result = {"name": "新角色", "description": "新描述"}
        mock_dialog_cls.return_value = dialog

        controller.edit_character()

        controller.command_executor.assert_called_once()
        command = controller.command_executor.call_args.args[0]
        self.assertEqual(command.new_data["name"], "新角色")
        self.assertEqual(command.new_data["tags"], ["新标签"])


if __name__ == "__main__":
    unittest.main()
