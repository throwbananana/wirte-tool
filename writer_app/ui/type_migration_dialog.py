"""
Type migration dialog - handles project type switching with data migration options.

When a user switches project types, this dialog:
1. Shows which data modules will be affected
2. Lets the user choose how to handle incompatible data
3. Provides clear information about what will happen
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Dict, Any

from writer_app.core.typed_data import (
    get_cleanup_info,
    get_new_modules,
    get_module_schema,
    DataModule
)
from writer_app.core.project_types import ProjectTypeManager


class TypeMigrationDialog(tk.Toplevel):
    """
    Dialog for handling project type changes with data migration options.

    Shows the user:
    - Modules that will become unused (with data counts)
    - New modules that will be added
    - Options: Archive (keep), Delete, or Cancel
    """

    def __init__(
        self,
        parent,
        old_type: str,
        new_type: str,
        project_data: Dict,
        on_confirm: callable = None
    ):
        """
        Initialize the type migration dialog.

        Args:
            parent: Parent window
            old_type: Current project type
            new_type: Target project type
            project_data: Current project data dictionary
            on_confirm: Callback when user confirms, receives (action: str)
                       action is "archive", "delete", or None for cancel
        """
        super().__init__(parent)
        self.old_type = old_type
        self.new_type = new_type
        self.project_data = project_data
        self.on_confirm = on_confirm
        self.result: Optional[str] = None

        # Get type display names
        old_info = ProjectTypeManager.get_type_info(old_type)
        new_info = ProjectTypeManager.get_type_info(new_type)
        self.old_name = old_info.get("name", old_type)
        self.new_name = new_info.get("name", new_type)

        # Get affected modules
        self.cleanup_info = get_cleanup_info(old_type, new_type, project_data)
        self.new_modules = get_new_modules(old_type, new_type)

        self._setup_ui()
        self._center_dialog()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        """Build the dialog UI."""
        self.title("切换项目类型")
        self.resizable(False, False)

        # Main container with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_label = ttk.Label(
            main_frame,
            text=f"从「{self.old_name}」切换到「{self.new_name}」",
            font=("", 12, "bold")
        )
        header_label.pack(anchor=tk.W, pady=(0, 15))

        # Affected data section (if any)
        if self.cleanup_info:
            self._build_affected_section(main_frame)

        # New modules section (if any)
        if self.new_modules:
            self._build_new_modules_section(main_frame)

        # No changes section
        if not self.cleanup_info and not self.new_modules:
            no_change_label = ttk.Label(
                main_frame,
                text="此切换不会影响任何现有数据。",
                foreground="green"
            )
            no_change_label.pack(anchor=tk.W, pady=10)

        # Action selection (only if there's data to handle)
        if self.cleanup_info:
            self._build_action_selection(main_frame)

        # Buttons
        self._build_buttons(main_frame)

    def _build_affected_section(self, parent):
        """Build the section showing affected data modules."""
        section_frame = ttk.LabelFrame(parent, text="将不再使用的数据模块", padding="10")
        section_frame.pack(fill=tk.X, pady=(0, 15))

        # Warning icon and text
        warning_frame = ttk.Frame(section_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 10))

        warning_label = ttk.Label(
            warning_frame,
            text="以下数据模块在新项目类型中不被使用：",
            foreground="#b8860b"
        )
        warning_label.pack(anchor=tk.W)

        # List affected modules
        for info in self.cleanup_info:
            item_frame = ttk.Frame(section_frame)
            item_frame.pack(fill=tk.X, pady=2)

            # Module name and description
            name_label = ttk.Label(
                item_frame,
                text=f"  {info['description']}",
                font=("", 10)
            )
            name_label.pack(side=tk.LEFT)

            # Data count
            if info['item_count'] > 0:
                count_label = ttk.Label(
                    item_frame,
                    text=f"({info['item_count']} 条数据)",
                    foreground="red"
                )
                count_label.pack(side=tk.LEFT, padx=(10, 0))

    def _build_new_modules_section(self, parent):
        """Build the section showing new modules that will be added."""
        section_frame = ttk.LabelFrame(parent, text="将新增的数据模块", padding="10")
        section_frame.pack(fill=tk.X, pady=(0, 15))

        info_label = ttk.Label(
            section_frame,
            text="以下功能模块将被启用：",
            foreground="green"
        )
        info_label.pack(anchor=tk.W, pady=(0, 5))

        for module in self.new_modules:
            schema = get_module_schema(module)
            if schema:
                module_label = ttk.Label(
                    section_frame,
                    text=f"  + {schema.description}",
                    font=("", 10)
                )
                module_label.pack(anchor=tk.W, pady=1)

    def _build_action_selection(self, parent):
        """Build the action selection radio buttons."""
        action_frame = ttk.LabelFrame(parent, text="如何处理不再使用的数据？", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 15))

        self.action_var = tk.StringVar(value="archive")

        # Archive option (recommended)
        archive_radio = ttk.Radiobutton(
            action_frame,
            text="归档保留（推荐）",
            variable=self.action_var,
            value="archive"
        )
        archive_radio.pack(anchor=tk.W)

        archive_desc = ttk.Label(
            action_frame,
            text="    数据将被归档，切换回原类型时可恢复",
            foreground="gray",
            font=("", 9)
        )
        archive_desc.pack(anchor=tk.W, pady=(0, 8))

        # Delete option
        delete_radio = ttk.Radiobutton(
            action_frame,
            text="永久删除",
            variable=self.action_var,
            value="delete"
        )
        delete_radio.pack(anchor=tk.W)

        delete_desc = ttk.Label(
            action_frame,
            text="    数据将被永久删除，无法恢复",
            foreground="red",
            font=("", 9)
        )
        delete_desc.pack(anchor=tk.W)

    def _build_buttons(self, parent):
        """Build the dialog buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="取消",
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Confirm button
        confirm_text = "确认切换" if self.cleanup_info else "切换"
        confirm_btn = ttk.Button(
            button_frame,
            text=confirm_text,
            command=self._on_confirm
        )
        confirm_btn.pack(side=tk.RIGHT)

    def _center_dialog(self):
        """Center the dialog on its parent window."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()

        # Get parent position
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2

        self.geometry(f"+{x}+{y}")

    def _on_confirm(self):
        """Handle confirm button click."""
        if self.cleanup_info:
            self.result = self.action_var.get()
        else:
            self.result = "none"  # No cleanup needed

        if self.on_confirm:
            self.on_confirm(self.result)

        self.destroy()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        if self.on_confirm:
            self.on_confirm(None)
        self.destroy()

    def show(self) -> Optional[str]:
        """
        Show the dialog and wait for user response.

        Returns:
            "archive", "delete", "none", or None if cancelled
        """
        self.wait_window()
        return self.result


def show_type_migration_dialog(
    parent,
    old_type: str,
    new_type: str,
    project_data: Dict
) -> Optional[str]:
    """
    Convenience function to show the type migration dialog.

    Args:
        parent: Parent window
        old_type: Current project type
        new_type: Target project type
        project_data: Current project data

    Returns:
        "archive", "delete", "none", or None if cancelled
    """
    # Check if migration is needed
    cleanup_info = get_cleanup_info(old_type, new_type, project_data)
    new_modules = get_new_modules(old_type, new_type)

    # If no changes needed, return immediately
    if not cleanup_info and not new_modules:
        return "none"

    # Show dialog
    dialog = TypeMigrationDialog(parent, old_type, new_type, project_data)
    return dialog.show()


class QuickTypeSwitchDialog(tk.Toplevel):
    """
    A simpler dialog for quick type switching when there's no data to migrate.
    Just confirms the switch with a brief summary of changes.
    """

    def __init__(self, parent, old_type: str, new_type: str):
        super().__init__(parent)
        self.old_type = old_type
        self.new_type = new_type
        self.result = False

        old_info = ProjectTypeManager.get_type_info(old_type)
        new_info = ProjectTypeManager.get_type_info(new_type)

        self.title("切换项目类型")
        self.resizable(False, False)

        # Main content
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Message
        msg = f"确定要从「{old_info.get('name', old_type)}」切换到「{new_info.get('name', new_type)}」吗？"
        msg_label = ttk.Label(main_frame, text=msg, wraplength=300)
        msg_label.pack(pady=(0, 10))

        # Description of new type
        desc_label = ttk.Label(
            main_frame,
            text=new_info.get('description', ''),
            foreground="gray",
            wraplength=300
        )
        desc_label.pack(pady=(0, 15))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="取消", command=self._cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(btn_frame, text="确认", command=self._confirm).pack(side=tk.RIGHT)

        # Center and modal
        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()

    def show(self) -> bool:
        self.wait_window()
        return self.result
