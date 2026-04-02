import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from writer_app.app.workspace_builder import WorkspaceBuilder


class TestWorkspaceBuilder(unittest.TestCase):
    def test_build_tabs_uses_registered_builders_in_enabled_tool_order(self):
        app = SimpleNamespace()
        builder = WorkspaceBuilder(app)
        calls = []

        def build_outline(current_builder):
            calls.append(("outline", current_builder.app))

        def build_chat(current_builder):
            calls.append(("chat", current_builder.app))

        with patch.dict(
            "writer_app.app.workspace_builder.TAB_BUILDERS",
            {"chat": build_chat, "outline": build_outline},
            clear=True,
        ):
            builder._build_tabs(["chat", "missing", "outline"])

        self.assertEqual(calls, [("chat", app), ("outline", app)])

    @patch("writer_app.app.workspace_builder.ProjectTypeManager.get_default_tab_key")
    @patch("writer_app.app.workspace_builder.SidebarController")
    def test_setup_sidebar_registers_tabs_and_selects_default_tab(
        self,
        mock_sidebar_controller_cls,
        mock_get_default_tab_key,
    ):
        frame_outline = object()
        frame_script = object()
        notebook = Mock()
        notebook.select = Mock(side_effect=[None, "selected-script"])
        sidebar = Mock()
        sidebar_controller = Mock()
        mock_sidebar_controller_cls.return_value = sidebar_controller
        mock_get_default_tab_key.return_value = "script"

        app = SimpleNamespace(
            sidebar=sidebar,
            notebook=notebook,
            config_manager=Mock(),
            tabs={"outline": frame_outline, "script": frame_script},
            _on_sidebar_item_changed=Mock(),
            _toolbox_tab=None,
            _last_real_tab=None,
        )
        builder = WorkspaceBuilder(app)

        builder._setup_sidebar(["outline", "script"], "novel")

        mock_sidebar_controller_cls.assert_called_once_with(
            sidebar,
            notebook,
            app.config_manager,
            on_item_changed=app._on_sidebar_item_changed,
        )
        sidebar_controller.register_tab.assert_any_call("outline", frame_outline)
        sidebar_controller.register_tab.assert_any_call("script", frame_script)
        sidebar.update_visibility.assert_called_once_with(["outline", "script"])
        sidebar.select_item_by_key.assert_called_once_with("script")
        notebook.select.assert_any_call(frame_script)
        self.assertEqual(app._last_real_tab, "selected-script")

    @patch("writer_app.app.workspace_builder.ProjectTypeManager.get_length_info")
    def test_update_project_badge_sets_type_and_length_text(self, mock_get_length_info):
        mock_get_length_info.return_value = {"name": "长篇"}
        type_label = Mock()
        app = SimpleNamespace(
            project_manager=SimpleNamespace(
                get_project_type_display_name=Mock(return_value="悬疑小说")
            ),
            type_lbl=type_label,
        )
        builder = WorkspaceBuilder(app)

        builder._update_project_badge("mystery", "long")

        type_label.config.assert_called_once_with(text="[悬疑小说 | 长篇]")


if __name__ == "__main__":
    unittest.main()
