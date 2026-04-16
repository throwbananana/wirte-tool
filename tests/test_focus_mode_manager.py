import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from writer_app.ui.app_mode_manager import AppModeManager
from writer_app.ui.editor import ScriptEditor


class FakeEditor:
    def __init__(self, focus_mode=False, typewriter_mode=False, focus_level="line"):
        self.focus_mode = focus_mode
        self.typewriter_mode = typewriter_mode
        self._focus_level = focus_level
        self.pause_focus_session = Mock()
        self.resume_focus_session = Mock()
        self.focus_set = Mock()
        self.toggle_focus_mode = Mock(side_effect=self._set_focus_mode)
        self.toggle_typewriter_mode = Mock(side_effect=self._set_typewriter_mode)

    def _set_focus_mode(self, enabled, save_config=True, track_session=True):
        self.focus_mode = enabled

    def _set_typewriter_mode(self, enabled):
        self.typewriter_mode = enabled


class TestScriptEditorFocusMode(unittest.TestCase):
    def _make_editor_stub(self):
        editor = ScriptEditor.__new__(ScriptEditor)
        editor.focus_mode = False
        editor.typewriter_mode = False
        editor._focus_with_typewriter = True
        editor._focus_controls_typewriter = False
        editor._focus_session_paused = False
        editor._focus_level = ScriptEditor.FOCUS_LINE
        editor._destroyed = False
        editor.on_focus_mode_change = None
        editor.config_manager = None
        editor._apply_focus_effect = Mock()
        editor._clear_focus_effect = Mock()
        editor.get_focus_settings = Mock(return_value={"enabled": False})
        editor.toggle_typewriter_mode = Mock(side_effect=lambda enabled: setattr(editor, "typewriter_mode", enabled))
        editor._start_focus_session = Mock()
        editor._end_focus_session = Mock()
        return editor

    @patch("writer_app.ui.editor.get_event_bus")
    def test_toggle_focus_mode_restores_typewriter_when_focus_enabled_it(self, mock_get_event_bus):
        mock_get_event_bus.return_value = Mock()
        editor = self._make_editor_stub()

        ScriptEditor.toggle_focus_mode(editor, True)
        self.assertTrue(editor.typewriter_mode)
        self.assertTrue(editor._focus_controls_typewriter)

        ScriptEditor.toggle_focus_mode(editor, False)
        self.assertFalse(editor.typewriter_mode)
        self.assertFalse(editor._focus_controls_typewriter)
        editor._start_focus_session.assert_called_once()
        editor._end_focus_session.assert_called_once()

    def test_load_focus_config_tracks_enabled_state_for_startup_restore(self):
        editor = ScriptEditor.__new__(ScriptEditor)
        editor.config_manager = Mock()
        editor.config_manager.get_focus_mode_config.return_value = {
            "enabled": True,
            "level": ScriptEditor.FOCUS_PARAGRAPH,
            "context_lines": 5,
            "gradient": False,
            "highlight_current": False,
            "with_typewriter": False,
        }

        ScriptEditor._load_focus_config(editor)

        self.assertTrue(editor._focus_restore_on_init)
        self.assertEqual(editor._focus_level, ScriptEditor.FOCUS_PARAGRAPH)
        self.assertEqual(editor._focus_context_lines, 5)
        self.assertFalse(editor._focus_gradient)
        self.assertFalse(editor._focus_highlight_current)
        self.assertFalse(editor._focus_with_typewriter)

    def test_restore_initial_focus_mode_replays_saved_enabled_state(self):
        editor = ScriptEditor.__new__(ScriptEditor)
        editor._destroyed = False
        editor._focus_restore_on_init = True
        editor.focus_mode = False
        editor.toggle_focus_mode = Mock()

        ScriptEditor._restore_initial_focus_mode(editor)

        editor.toggle_focus_mode.assert_called_once_with(True, save_config=False)
        self.assertFalse(editor._focus_restore_on_init)


class TestAppModeManager(unittest.TestCase):
    def _make_app(self, editor, auto_focus_in_zen=True):
        script_controller = SimpleNamespace(
            script_editor=editor,
            enter_zen_mode=Mock(),
            exit_zen_mode=Mock(),
        )
        return SimpleNamespace(
            root=Mock(),
            script_controller=script_controller,
            is_zen_mode=False,
            pre_zen_geometry=None,
            notebook=Mock(),
            script_frame=object(),
            config_manager=Mock(),
            ambiance_player=Mock(),
            status_var=Mock(),
            menubar=Mock(),
            _orig_notebook_style="",
            _zen_style_created=False,
        )

    @patch("writer_app.ui.app_mode_manager.get_event_bus")
    def test_toggle_zen_mode_builds_aux_ui_and_uses_non_tracking_focus(self, mock_get_event_bus):
        mock_get_event_bus.return_value = Mock()
        editor = FakeEditor(focus_mode=False, typewriter_mode=False)
        app = self._make_app(editor)
        app.config_manager.get.return_value = True
        manager = AppModeManager(app)

        manager._zen_fade_transition = Mock()
        manager._apply_zen_notebook_style = Mock()
        manager._set_status_ui_visible = Mock()
        manager._hide_main_sidebar = Mock()
        manager._create_zen_exit_button = Mock()
        manager._create_zen_info_panel = Mock()
        manager._capture_pre_zen_state = Mock(
            return_value={
                "sidebar_visible": False,
                "typewriter_mode": False,
                "focus_mode": False,
                "main_paned_pack": None,
                "status_visible": True,
            }
        )

        manager.toggle_zen_mode()

        self.assertTrue(app.is_zen_mode)
        editor.toggle_typewriter_mode.assert_called_once_with(True)
        editor.toggle_focus_mode.assert_called_once_with(True, save_config=False, track_session=False)
        editor.pause_focus_session.assert_not_called()
        manager._create_zen_exit_button.assert_called_once()
        manager._create_zen_info_panel.assert_called_once()
        app.status_var.set.assert_called_with("沉浸模式: 已开启 | 按 F11 退出")

    def test_restore_pre_zen_editor_state_resumes_paused_focus_session(self):
        editor = FakeEditor(focus_mode=True, typewriter_mode=True)
        app = self._make_app(editor)
        manager = AppModeManager(app)
        manager._pre_zen_state = {"focus_mode": True, "typewriter_mode": False}

        manager._restore_pre_zen_editor_state(app.script_controller)

        editor.toggle_focus_mode.assert_not_called()
        editor.toggle_typewriter_mode.assert_called_once_with(False)
        editor.resume_focus_session.assert_called_once_with()

    def test_restore_pre_zen_editor_state_disables_zen_auto_focus_without_session_tracking(self):
        editor = FakeEditor(focus_mode=True, typewriter_mode=True)
        app = self._make_app(editor)
        manager = AppModeManager(app)
        manager._pre_zen_state = {"focus_mode": False, "typewriter_mode": False}

        manager._restore_pre_zen_editor_state(app.script_controller)

        editor.toggle_focus_mode.assert_called_once_with(False, save_config=False, track_session=False)
        editor.resume_focus_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
