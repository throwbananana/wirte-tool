class ThemeManager:
    """Manages application themes (Light/Dark)."""
    
    THEMES = {
        "Light": {
            "bg_primary": "#FFFFFF",
            "bg_secondary": "#F0F0F0",
            "fg_primary": "#000000",
            "fg_secondary": "#555555",
            "accent": "#007BFF",
            "canvas_bg": "#FFFFFF",
            "border": "#CCCCCC",
            "highlight": "#BBDEFB",
            "success": "#28A745",
            "warning": "#FFC107",
            "error": "#DC3545",
            "editor_bg": "#FFFFFF",
            "editor_fg": "#000000",
            "editor_select_bg": "#0078D7",
            "editor_select_fg": "#FFFFFF",
            "mindmap_node_bg": "#E3F2FD",
            "mindmap_node_border": "#2196F3",
            "timeline_lane_bg": "#FAFAFA",
            "chat_user_fg": "#007BFF",
            "chat_ai_fg": "#28A745",
            "chat_system_fg": "#666666",
            # Editor specific
            "editor_scene_header_bg": "#E3F2FD",
            "editor_scene_header_fg": "#000000",
            "editor_char_name_fg": "#1565C0",
            "editor_paren_fg": "#757575",
            "editor_trans_fg": "#E65100",
            "editor_dimmed_fg": "#DDDDDD",
            "editor_wiki_fg": "#009688",
            "editor_wiki_deep_bg": "#F3E5F5",
            "editor_wiki_deep_fg": "#9C27B0",
            # Alibi Timeline specific
            "alibi_bg": "#FAFAFA",
            "alibi_header_bg": "#E0E0E0",
            "alibi_header_fg": "#333333",
            "alibi_grid": "#BDBDBD",
            "alibi_text": "#424242",
            "alibi_cell_bg": "#90CAF9",
            "alibi_cell_outline": "#42A5F5",
            "alibi_cell_text": "#1A237E",
            # TableView specific
            "table_level_0_bg": "#E3F2FD",
            "table_level_1_bg": "#E8F5E9",
            "table_level_2_bg": "#FFF3E0",
            "table_level_3_bg": "#FCE4EC",
            "table_level_4_bg": "#F3E5F5",
            "table_level_5_bg": "#E0F7FA",
            "table_has_content_fg": "#1565C0",
            "table_status_draft_fg": "#1976D2",
            "table_status_final_fg": "#2E7D32",
            # World Iceberg specific
            "iceberg_bg": "#E0F7FA",
            "iceberg_deep_bg": "#006064",
            "iceberg_shallow_bg": "#0097A7",
            "iceberg_surface_bg": "#4DD0E1",
            "iceberg_line": "#0277BD",
            "iceberg_text": "#FFFFFF",
            "iceberg_entry_bg": "#FFFFFF",
            "iceberg_entry_fg": "#000000",
            "iceberg_entry_outline": "#00838F",
            # Swimlane specific
            "swimlane_header_line": "#EEEEEE",
            "swimlane_block_fill": "#4DA3FF",
            "swimlane_block_text": "#FFFFFF",
            # BeatSheet specific
            "beat_slot_bg": "#F5F5F5",
            "beat_slot_outline": "#CCCCCC",
            "beat_header_fill": "#DDDDDD",
            "beat_header_outline": "#CCCCCC",
            "beat_card_bg": "#FFFFFF",
            "beat_card_outline": "#DDDDDD",
            "beat_card_text": "#000000",
            # Calendar specific
            "calendar_event_bg": "#E3F2FD",
            "calendar_event_fg": "#000000",
            # Guide/Onboarding specific
            "guide_overlay_bg": "#000000",
            "guide_highlight_border": "#2196F3",
            "guide_tooltip_bg": "#FFFDE7",
            "guide_tooltip_fg": "#333333",
            "guide_tooltip_title": "#1565C0",
            "guide_tooltip_border": "#FFC107",
            "empty_state_icon": "#9E9E9E",
            "empty_state_title": "#424242",
            "empty_state_desc": "#757575",
            # Sidebar specific
            "sidebar_bg": "#F5F5F5",
            "sidebar_fg": "#333333",
            "sidebar_workspace_header": "#E0E0E0",
            "sidebar_item_hover": "#E3F2FD",
            "sidebar_item_active": "#BBDEFB"
        },
        "Dark": {
            "bg_primary": "#2D2D2D",
            "bg_secondary": "#333333",
            "fg_primary": "#E0E0E0",
            "fg_secondary": "#AAAAAA",
            "accent": "#4DA3FF",
            "canvas_bg": "#1E1E1E",
            "border": "#444444",
            "highlight": "#3A3A3A",
            "success": "#5CB85C",
            "warning": "#F0AD4E",
            "error": "#D9534F",
            "editor_bg": "#1E1E1E",
            "editor_fg": "#D4D4D4",
            "editor_select_bg": "#264F78",
            "editor_select_fg": "#FFFFFF",
            "mindmap_node_bg": "#37474F",
            "mindmap_node_border": "#64B5F6",
            "timeline_lane_bg": "#252526",
            "chat_user_fg": "#4DA3FF",
            "chat_ai_fg": "#5CB85C",
            "chat_system_fg": "#888888",
            # Editor specific
            "editor_scene_header_bg": "#37474F",
            "editor_scene_header_fg": "#E0E0E0",
            "editor_char_name_fg": "#64B5F6",
            "editor_paren_fg": "#B0BEC5",
            "editor_trans_fg": "#FFB74D",
            "editor_dimmed_fg": "#555555",
            "editor_wiki_fg": "#4DB6AC",
            "editor_wiki_deep_bg": "#4A148C",
            "editor_wiki_deep_fg": "#CE93D8",
            # Alibi Timeline specific
            "alibi_bg": "#263238",
            "alibi_header_bg": "#37474F",
            "alibi_header_fg": "#ECEFF1",
            "alibi_grid": "#37474F",
            "alibi_text": "#CFD8DC",
            "alibi_cell_bg": "#546E7A",
            "alibi_cell_outline": "#78909C",
            "alibi_cell_text": "#FFFFFF",
            # TableView specific
            "table_level_0_bg": "#1E3A5F",
            "table_level_1_bg": "#1E4D2B",
            "table_level_2_bg": "#5D4037",
            "table_level_3_bg": "#4A1942",
            "table_level_4_bg": "#4A148C",
            "table_level_5_bg": "#006064",
            "table_has_content_fg": "#64B5F6",
            "table_status_draft_fg": "#90CAF9",
            "table_status_final_fg": "#A5D6A7",
            # World Iceberg specific
            "iceberg_bg": "#263238",
            "iceberg_deep_bg": "#00363A",
            "iceberg_shallow_bg": "#006064",
            "iceberg_surface_bg": "#00838F",
            "iceberg_line": "#4FC3F7",
            "iceberg_text": "#E0E0E0",
            "iceberg_entry_bg": "#37474F",
            "iceberg_entry_fg": "#ECEFF1",
            "iceberg_entry_outline": "#546E7A",
            # Swimlane specific
            "swimlane_header_line": "#444444",
            "swimlane_block_fill": "#1E88E5",
            "swimlane_block_text": "#FFFFFF",
            # BeatSheet specific
            "beat_slot_bg": "#2D2D2D",
            "beat_slot_outline": "#444444",
            "beat_header_fill": "#37474F",
            "beat_header_outline": "#444444",
            "beat_card_bg": "#424242",
            "beat_card_outline": "#555555",
            "beat_card_text": "#E0E0E0",
            # Calendar specific
            "calendar_event_bg": "#264F78",
            "calendar_event_fg": "#FFFFFF",
            # Guide/Onboarding specific
            "guide_overlay_bg": "#000000",
            "guide_highlight_border": "#64B5F6",
            "guide_tooltip_bg": "#424242",
            "guide_tooltip_fg": "#E0E0E0",
            "guide_tooltip_title": "#64B5F6",
            "guide_tooltip_border": "#757575",
            "empty_state_icon": "#757575",
            "empty_state_title": "#E0E0E0",
            "empty_state_desc": "#AAAAAA",
            # Sidebar specific
            "sidebar_bg": "#252526",
            "sidebar_fg": "#E0E0E0",
            "sidebar_workspace_header": "#333333",
            "sidebar_item_hover": "#3A3A3A",
            "sidebar_item_active": "#264F78"
        },
        "Custom": {
             # Default Custom values (copy of Light)
            "bg_primary": "#FFFFFF",
            "bg_secondary": "#F0F0F0",
            "fg_primary": "#000000",
            "fg_secondary": "#555555",
            "accent": "#007BFF",
            "canvas_bg": "#FFFFFF",
            "border": "#CCCCCC",
            "highlight": "#BBDEFB",
            "success": "#28A745",
            "warning": "#FFC107",
            "error": "#DC3545",
            "editor_bg": "#FFFFFF",
            "editor_fg": "#000000",
            "editor_select_bg": "#0078D7",
            "editor_select_fg": "#FFFFFF",
            "mindmap_node_bg": "#E3F2FD",
            "mindmap_node_border": "#2196F3",
            "timeline_lane_bg": "#FAFAFA",
            "chat_user_fg": "#007BFF",
            "chat_ai_fg": "#28A745",
            "chat_system_fg": "#666666",
            # Editor specific
            "editor_scene_header_bg": "#E3F2FD",
            "editor_scene_header_fg": "#000000",
            "editor_char_name_fg": "#1565C0",
            "editor_paren_fg": "#757575",
            "editor_trans_fg": "#E65100",
            "editor_dimmed_fg": "#DDDDDD",
            "editor_wiki_fg": "#009688",
            "editor_wiki_deep_bg": "#F3E5F5",
            "editor_wiki_deep_fg": "#9C27B0",
            # Alibi Timeline specific
            "alibi_bg": "#FAFAFA",
            "alibi_header_bg": "#E0E0E0",
            "alibi_header_fg": "#333333",
            "alibi_grid": "#BDBDBD",
            "alibi_text": "#424242",
            "alibi_cell_bg": "#90CAF9",
            "alibi_cell_outline": "#42A5F5",
            "alibi_cell_text": "#1A237E",
            # TableView specific
            "table_level_0_bg": "#E3F2FD",
            "table_level_1_bg": "#E8F5E9",
            "table_level_2_bg": "#FFF3E0",
            "table_level_3_bg": "#FCE4EC",
            "table_level_4_bg": "#F3E5F5",
            "table_level_5_bg": "#E0F7FA",
            "table_has_content_fg": "#1565C0",
            "table_status_draft_fg": "#1976D2",
            "table_status_final_fg": "#2E7D32",
            # World Iceberg specific
            "iceberg_bg": "#E0F7FA",
            "iceberg_deep_bg": "#006064",
            "iceberg_shallow_bg": "#0097A7",
            "iceberg_surface_bg": "#4DD0E1",
            "iceberg_line": "#0277BD",
            "iceberg_text": "#FFFFFF",
            "iceberg_entry_bg": "#FFFFFF",
            "iceberg_entry_fg": "#000000",
            "iceberg_entry_outline": "#00838F",
            # Swimlane specific
            "swimlane_header_line": "#EEEEEE",
            "swimlane_block_fill": "#4DA3FF",
            "swimlane_block_text": "#FFFFFF",
            # BeatSheet specific
            "beat_slot_bg": "#F5F5F5",
            "beat_slot_outline": "#CCCCCC",
            "beat_header_fill": "#DDDDDD",
            "beat_header_outline": "#CCCCCC",
            "beat_card_bg": "#FFFFFF",
            "beat_card_outline": "#DDDDDD",
            "beat_card_text": "#000000",
            # Calendar specific
            "calendar_event_bg": "#E3F2FD",
            "calendar_event_fg": "#000000",
            # Guide/Onboarding specific
            "guide_overlay_bg": "#000000",
            "guide_highlight_border": "#2196F3",
            "guide_tooltip_bg": "#FFFDE7",
            "guide_tooltip_fg": "#333333",
            "guide_tooltip_title": "#1565C0",
            "guide_tooltip_border": "#FFC107",
            "empty_state_icon": "#9E9E9E",
            "empty_state_title": "#424242",
            "empty_state_desc": "#757575",
            # Sidebar specific
            "sidebar_bg": "#F5F5F5",
            "sidebar_fg": "#333333",
            "sidebar_workspace_header": "#E0E0E0",
            "sidebar_item_hover": "#E3F2FD",
            "sidebar_item_active": "#BBDEFB"
        }
    }

    def __init__(self, current_theme="Light"):
        self.current_theme = current_theme
        self.background_image_path = None
        self.background_opacity = 1.0
        self._listeners = []

    def get_color(self, key):
        return self.THEMES.get(self.current_theme, self.THEMES["Light"]).get(key, "#FF00FF")
    
    def set_background_image(self, path):
        self.background_image_path = path
        self.notify_listeners()

    def set_background_opacity(self, opacity):
        self.background_opacity = float(opacity)
        self.notify_listeners()
    
    def set_custom_colors(self, colors):
        """Update Custom theme colors."""
        if "Custom" in self.THEMES:
            self.THEMES["Custom"].update(colors)
        self.notify_listeners()

    def toggle_theme(self):
        """切换主题 (Light -> Dark -> Custom -> Light)"""
        theme_order = ["Light", "Dark", "Custom"]
        try:
            idx = theme_order.index(self.current_theme)
            self.current_theme = theme_order[(idx + 1) % len(theme_order)]
        except ValueError:
            self.current_theme = "Light"
        self.notify_listeners()
        return self.current_theme

    def set_theme(self, theme_name):
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            self.notify_listeners()

    def add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def notify_listeners(self):
        for callback in self._listeners:
            callback()
