"""
Sidebar Controller for Writer Tool.

Manages sidebar navigation state and coordinates between
the sidebar panel and the content area.
"""
import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Dict, Callable

from writer_app.controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class SidebarController:
    """
    Controller for the sidebar navigation.

    Manages the relationship between sidebar items and their corresponding
    content frames, handles navigation events, and persists state.
    """

    def __init__(self, sidebar, notebook, config_manager, on_item_changed: Optional[Callable] = None):
        """
        Initialize the sidebar controller.

        Args:
            sidebar: The SidebarPanel instance
            notebook: The ttk.Notebook containing content frames
            config_manager: ConfigManager for state persistence
            on_item_changed: Optional callback when active item changes
        """
        self.sidebar = sidebar
        self.notebook = notebook
        self.config_manager = config_manager
        self.on_item_changed = on_item_changed

        self.current_workspace: Optional[str] = None
        self.current_item: Optional[str] = None

        # Map item keys to notebook frame indices
        self.item_to_index: Dict[str, int] = {}

        self.logger = logging.getLogger(self.__class__.__name__)

    def setup_ui(self):
        """Initialize UI bindings."""
        pass

    def refresh(self):
        """Refresh the sidebar state."""
        pass

    def register_tab(self, item_key: str, frame: ttk.Frame):
        """
        Register a notebook tab/frame with an item key.

        Args:
            item_key: The sidebar item key (e.g., "outline")
            frame: The content frame
        """
        try:
            # Find the index of this frame in the notebook
            tabs = self.notebook.tabs()
            for i, tab in enumerate(tabs):
                if str(frame) == tab:
                    self.item_to_index[item_key] = i
                    break

            # Also register with sidebar for frame reference
            self.sidebar.register_item_frame(item_key, frame)

            self.logger.debug(f"Registered tab: {item_key}")
        except Exception as e:
            self.logger.error(f"Failed to register tab {item_key}: {e}")

    def on_item_selected(self, workspace: str, item: str):
        """
        Handle sidebar item selection.

        Args:
            workspace: The workspace key (e.g., "writing")
            item: The item key (e.g., "outline")
        """
        if item == "toolbox":
            # Special case: toolbox opens module catalog
            self.logger.debug("Toolbox selected - handled externally")
            return

        # Update internal state
        self.current_workspace = workspace
        self.current_item = item

        # Switch notebook tab
        self.show_content(item)

        # Save state
        self.save_state()

        # Notify callback
        if self.on_item_changed:
            try:
                self.on_item_changed(workspace, item)
            except Exception as e:
                self.logger.error(f"Error in item_changed callback: {e}")

    def show_content(self, item_key: str):
        """
        Show the content frame for the given item.

        Args:
            item_key: The sidebar item key
        """
        if item_key not in self.item_to_index:
            self.logger.warning(f"Unknown item key: {item_key}")
            return

        try:
            index = self.item_to_index[item_key]
            self.notebook.select(index)
            self.logger.debug(f"Switched to content: {item_key}")
        except tk.TclError as e:
            self.logger.error(f"Failed to select tab {item_key}: {e}")

    def save_state(self):
        """Persist current navigation state."""
        if self.config_manager:
            self.config_manager.set("sidebar_active_workspace", self.current_workspace)
            self.config_manager.set("sidebar_active_item", self.current_item)
            self.config_manager.save()

    def restore_state(self):
        """Restore navigation state from config."""
        if not self.config_manager:
            return

        workspace = self.config_manager.get("sidebar_active_workspace")
        item = self.config_manager.get("sidebar_active_item")

        if workspace and item:
            self.current_workspace = workspace
            self.current_item = item

            # Update sidebar selection
            self.sidebar.select_item(workspace, item)

            # Update notebook
            self.show_content(item)

    def select_by_frame(self, frame: ttk.Frame) -> bool:
        """
        Select the sidebar item corresponding to a frame.

        Args:
            frame: The content frame

        Returns:
            True if found and selected, False otherwise
        """
        frame_str = str(frame)
        for item_key, index in self.item_to_index.items():
            tabs = self.notebook.tabs()
            if index < len(tabs) and tabs[index] == frame_str:
                workspace = self.sidebar.item_to_workspace.get(item_key)
                if workspace:
                    self.sidebar.select_item(workspace, item_key)
                    self.current_workspace = workspace
                    self.current_item = item_key
                    return True
        return False

    def get_current(self):
        """Get current workspace and item."""
        return self.current_workspace, self.current_item

    def navigate_to(self, item_key: str):
        """
        Navigate to an item by its key.

        Args:
            item_key: The sidebar item key
        """
        workspace = self.sidebar.item_to_workspace.get(item_key)
        if workspace:
            self.on_item_selected(workspace, item_key)
        else:
            self.logger.warning(f"Cannot navigate to unknown item: {item_key}")

    def apply_theme(self):
        """Apply theme to sidebar."""
        if self.sidebar:
            self.sidebar.apply_theme()

    def update_enabled_tools(self, enabled_tools: set):
        """
        Update sidebar visibility based on enabled tools.

        Args:
            enabled_tools: Set of enabled tool keys
        """
        if self.sidebar:
            self.sidebar.update_visibility(enabled_tools)

            # If current item is no longer visible, select first available
            if self.current_item and self.current_item not in enabled_tools:
                for ws_key, ws in self.sidebar.workspaces.items():
                    for item_key in ws.item_order:
                        if item_key in enabled_tools:
                            self.on_item_selected(ws_key, item_key)
                            return
