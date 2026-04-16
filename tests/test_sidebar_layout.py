import unittest

from writer_app.ui.sidebar import SidebarItem, SidebarPanel, WorkspaceSection


class _FakeWidget:
    def __init__(self, manager="pack"):
        self.manager = manager
        self.config_calls = []
        self.pack_calls = []
        self.pack_configure_calls = []

    def configure(self, **kwargs):
        self.config_calls.append(kwargs)

    config = configure

    def pack(self, **kwargs):
        self.manager = "pack"
        self.pack_calls.append(kwargs)

    def pack_forget(self):
        self.manager = ""

    def pack_configure(self, **kwargs):
        self.pack_configure_calls.append(kwargs)

    def winfo_manager(self):
        return self.manager


class TestWorkspaceSectionLayout(unittest.TestCase):
    def test_workspace_section_compact_spacing_and_text(self):
        section = WorkspaceSection.__new__(WorkspaceSection)
        section.icon = "📝"
        section.label = "写作"
        item = SidebarItem("outline", "🗺️", "思维导图/大纲")

        self.assertEqual(section._get_header_text(True), "📝")
        self.assertEqual(section._get_header_text(False), "📝 写作")
        self.assertEqual(section._get_items_frame_padx(True), WorkspaceSection.COLLAPSED_ITEMS_PADX)
        self.assertEqual(section._get_item_padding(True), WorkspaceSection.COLLAPSED_ITEM_PADDING)
        self.assertEqual(section._get_item_anchor(True), "center")
        self.assertEqual(section._get_item_text(item, True), "🗺️")
        self.assertEqual(section._get_item_text(item, False), "  🗺️ 思维导图/大纲")


class TestSidebarPanelLayout(unittest.TestCase):
    def test_collapsed_panel_uses_tighter_width_and_hidden_strip_labels(self):
        panel = SidebarPanel.__new__(SidebarPanel)

        self.assertEqual(panel._get_canvas_width(True), SidebarPanel.COLLAPSED_WIDTH - SidebarPanel.COLLAPSED_CANVAS_PADDING)
        self.assertEqual(panel._get_canvas_width(False), SidebarPanel.EXPANDED_WIDTH - SidebarPanel.EXPANDED_CANVAS_PADDING)
        self.assertEqual(panel._get_toolbox_text(True), "➕")
        self.assertEqual(panel._get_toolbox_text(False), "➕ 工具箱")
        self.assertEqual(panel._get_toggle_button_text(True), "»")
        self.assertEqual(panel._get_toggle_button_text(False), "≡")

    def test_apply_panel_layout_hides_canvas_and_toolbox_in_collapsed_mode(self):
        panel = SidebarPanel.__new__(SidebarPanel)
        panel.collapsed = True
        panel.top_bar = _FakeWidget()
        panel.title_label = _FakeWidget()
        panel.collapse_btn = _FakeWidget()
        panel.canvas = _FakeWidget()
        panel.toolbox_frame = _FakeWidget()
        panel.scrollbar = _FakeWidget()
        panel.toolbox_btn = _FakeWidget()

        panel._apply_panel_layout()

        self.assertEqual(panel.canvas.winfo_manager(), "")
        self.assertEqual(panel.toolbox_frame.winfo_manager(), "")
        self.assertEqual(panel.scrollbar.winfo_manager(), "")
        self.assertIn({"width": 2, "text": "»"}, panel.collapse_btn.config_calls)

    def test_apply_panel_layout_restores_canvas_and_toolbox_in_expanded_mode(self):
        panel = SidebarPanel.__new__(SidebarPanel)
        panel.collapsed = False
        panel.top_bar = _FakeWidget()
        panel.title_label = _FakeWidget(manager="")
        panel.collapse_btn = _FakeWidget()
        panel.canvas = _FakeWidget(manager="")
        panel.toolbox_frame = _FakeWidget(manager="")
        panel.scrollbar = _FakeWidget(manager="")
        panel.toolbox_btn = _FakeWidget()

        panel._apply_panel_layout()

        self.assertEqual(panel.canvas.winfo_manager(), "pack")
        self.assertEqual(panel.toolbox_frame.winfo_manager(), "pack")
        self.assertEqual(panel.scrollbar.winfo_manager(), "pack")
        self.assertIn({"width": 3, "text": "≡"}, panel.collapse_btn.config_calls)


if __name__ == "__main__":
    unittest.main()
