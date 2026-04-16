"""
Sidebar Navigation Component for Writer Tool.

Replaces horizontal tab notebook with a collapsible vertical sidebar
organized into workspaces.
"""
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class SidebarItem:
    """Represents a single item in a workspace."""
    key: str           # e.g., "outline"
    icon: str          # e.g., "🗺️"
    label: str         # e.g., "思维导图/大纲"
    frame: Optional[ttk.Frame] = None  # Reference to content frame


@dataclass
class WorkspaceConfig:
    """Configuration for a workspace section."""
    key: str           # e.g., "writing"
    icon: str          # e.g., "📝"
    label: str         # e.g., "写作"
    items: List[SidebarItem]


class WorkspaceSection(ttk.Frame):
    """A collapsible workspace section containing sidebar items."""

    EXPANDED_ITEMS_PADX = (16, 0)
    COLLAPSED_ITEMS_PADX = (2, 0)
    EXPANDED_ITEM_PADDING = (8, 4)
    COLLAPSED_ITEM_PADDING = (2, 4)
    EXPANDED_HEADER_PADX = 4
    COLLAPSED_HEADER_PADX = 0
    EXPANDED_INDICATOR_PADX = (4, 0)

    def __init__(self, parent, key: str, icon: str, label: str,
                 items: List[SidebarItem], on_item_select: Callable,
                 theme_manager=None, collapsed_mode: bool = False):
        super().__init__(parent)
        self.key = key
        self.icon = icon
        self.label = label
        self.items = {item.key: item for item in items}
        self.item_order = [item.key for item in items]
        self.on_item_select = on_item_select
        self.theme_manager = theme_manager
        self.collapsed_mode = collapsed_mode
        self.expanded = True
        self.active_item: Optional[str] = None

        self.item_buttons: Dict[str, ttk.Label] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Build the workspace section UI."""
        # Header (clickable to expand/collapse)
        self.header_frame = ttk.Frame(self, cursor="hand2")
        self.header_frame.pack(fill=tk.X, pady=(0, 2))

        # Expand/collapse indicator
        self.expand_indicator = ttk.Label(
            self.header_frame,
            text="▼" if self.expanded else "▶",
            width=2,
            cursor="hand2"
        )
        self.expand_indicator.pack(side=tk.LEFT, padx=self.EXPANDED_INDICATOR_PADX)

        # Workspace icon and label
        self.header_label = ttk.Label(
            self.header_frame,
            text=self._get_header_text(self.collapsed_mode),
            font=("Microsoft YaHei", 10, "bold"),
            cursor="hand2"
        )
        self.header_label.pack(
            side=tk.LEFT,
            padx=self._get_header_padx(self.collapsed_mode),
            fill=tk.X,
            expand=True,
        )

        # Bind click events to all header elements
        for widget in (self.header_frame, self.expand_indicator, self.header_label):
            widget.bind("<Button-1>", self._toggle_expand)
            widget.bind("<Enter>", self._on_header_hover_enter)
            widget.bind("<Leave>", self._on_header_hover_leave)

        # Items container
        self.items_frame = ttk.Frame(self)
        self.items_frame.pack(fill=tk.X, padx=self._get_items_frame_padx(self.collapsed_mode))

        # Create item buttons
        self._create_item_buttons()
        self._apply_collapsed_layout(self.collapsed_mode)

    def _get_header_text(self, collapsed: bool) -> str:
        return self.icon if collapsed else f"{self.icon} {self.label}"

    def _get_header_padx(self, collapsed: bool) -> int:
        return self.COLLAPSED_HEADER_PADX if collapsed else self.EXPANDED_HEADER_PADX

    def _get_items_frame_padx(self, collapsed: bool):
        return self.COLLAPSED_ITEMS_PADX if collapsed else self.EXPANDED_ITEMS_PADX

    def _get_item_text(self, item: SidebarItem, collapsed: bool) -> str:
        return item.icon if collapsed else f"  {item.icon} {item.label}"

    def _get_item_padding(self, collapsed: bool):
        return self.COLLAPSED_ITEM_PADDING if collapsed else self.EXPANDED_ITEM_PADDING

    def _get_item_anchor(self, collapsed: bool) -> str:
        return "center" if collapsed else "w"

    def _apply_collapsed_layout(self, collapsed: bool):
        if collapsed:
            if self.expand_indicator.winfo_manager() == "pack":
                self.expand_indicator.pack_forget()
            self.header_label.pack_configure(padx=self._get_header_padx(True))
            self.header_label.configure(anchor="center")
        else:
            if self.expand_indicator.winfo_manager() != "pack":
                self.expand_indicator.pack(
                    side=tk.LEFT,
                    padx=self.EXPANDED_INDICATOR_PADX,
                    before=self.header_label,
                )
            self.header_label.pack_configure(padx=self._get_header_padx(False))
            self.header_label.configure(anchor="w")

    def _on_header_hover_enter(self, event=None):
        """Handle header hover enter."""
        if self.theme_manager:
            self.header_frame.configure(style="SidebarHeaderHover.TFrame")

    def _on_header_hover_leave(self, event=None):
        """Handle header hover leave."""
        self.header_frame.configure(style="SidebarHeader.TFrame")

    def _create_item_buttons(self):
        """Create buttons for each item in the workspace."""
        for key in self.item_order:
            item = self.items[key]

            item_frame = ttk.Frame(self.items_frame)
            item_frame.pack(fill=tk.X, pady=1)

            btn = ttk.Label(
                item_frame,
                text=self._get_item_text(item, self.collapsed_mode),
                cursor="hand2",
                padding=self._get_item_padding(self.collapsed_mode),
                anchor=self._get_item_anchor(self.collapsed_mode),
            )
            btn.pack(fill=tk.X)
            btn.bind("<Button-1>", lambda e, k=key: self._on_item_click(k))
            btn.bind("<Enter>", lambda e, b=btn: self._on_hover_enter(b))
            btn.bind("<Leave>", lambda e, b=btn: self._on_hover_leave(b))

            self.item_buttons[key] = btn

    def _toggle_expand(self, event=None):
        """Toggle the expanded/collapsed state of this workspace."""
        self.expanded = not self.expanded
        self.expand_indicator.config(text="▼" if self.expanded else "▶")

        if self.expanded:
            self.items_frame.pack(fill=tk.X, padx=self._get_items_frame_padx(self.collapsed_mode))
        else:
            self.items_frame.pack_forget()

    def _on_item_click(self, item_key: str):
        """Handle item click."""
        self.on_item_select(self.key, item_key)

    def _on_hover_enter(self, btn: ttk.Label):
        """Handle mouse hover enter."""
        if self.theme_manager:
            btn.configure(background=self.theme_manager.get_color("sidebar_item_hover"))

    def _on_hover_leave(self, btn: ttk.Label):
        """Handle mouse hover leave."""
        # Reset to active or normal state
        item_key = None
        for k, b in self.item_buttons.items():
            if b == btn:
                item_key = k
                break

        if item_key == self.active_item and self.theme_manager:
            btn.configure(background=self.theme_manager.get_color("sidebar_item_active"))
        else:
            btn.configure(background="")

    def set_active_item(self, item_key: Optional[str]):
        """Set the active item in this workspace."""
        old_active = self.active_item
        self.active_item = item_key

        # Reset old active button
        if old_active and old_active in self.item_buttons:
            self.item_buttons[old_active].configure(background="")

        # Highlight new active button
        if item_key and item_key in self.item_buttons and self.theme_manager:
            self.item_buttons[item_key].configure(
                background=self.theme_manager.get_color("sidebar_item_active")
            )

    def expand(self):
        """Expand this workspace section."""
        if not self.expanded:
            self._toggle_expand()

    def collapse(self):
        """Collapse this workspace section."""
        if self.expanded:
            self._toggle_expand()

    def set_collapsed_mode(self, collapsed: bool):
        """Switch between hidden-strip and expanded mode."""
        if self.collapsed_mode == collapsed:
            return

        self.collapsed_mode = collapsed

        self._apply_collapsed_layout(collapsed)
        self.header_label.config(text=self._get_header_text(collapsed))
        if self.expanded:
            self.items_frame.pack_configure(padx=self._get_items_frame_padx(collapsed))

        # Update item buttons
        for key in self.item_order:
            item = self.items[key]
            btn = self.item_buttons.get(key)
            if btn:
                btn.config(
                    text=self._get_item_text(item, collapsed),
                    padding=self._get_item_padding(collapsed),
                    anchor=self._get_item_anchor(collapsed),
                )

    def apply_theme(self):
        """Apply theme colors to this workspace section."""
        if not self.theme_manager:
            return

        bg = self.theme_manager.get_color("sidebar_bg")
        fg = self.theme_manager.get_color("sidebar_fg")
        header_bg = self.theme_manager.get_color("sidebar_workspace_header")

        self.configure(style="Sidebar.TFrame")
        self.header_frame.configure(style="SidebarHeader.TFrame")
        self.items_frame.configure(style="Sidebar.TFrame")

        # Update active item highlight
        if self.active_item and self.active_item in self.item_buttons:
            self.item_buttons[self.active_item].configure(
                background=self.theme_manager.get_color("sidebar_item_active")
            )


class SidebarPanel(ttk.Frame):
    """
    The main sidebar navigation panel.

    Contains multiple workspace sections that can be expanded/collapsed.
    Supports a hidden-strip collapsed state and a full expanded state.
    """

    # Workspace definitions
    WORKSPACE_DEFINITIONS = [
        WorkspaceConfig(
            key="writing",
            icon="📝",
            label="写作",
            items=[
                SidebarItem("outline", "🗺️", "思维导图/大纲"),
                SidebarItem("script", "📜", "剧本写作"),
                SidebarItem("char_events", "👥", "人物事件"),
                SidebarItem("ideas", "💡", "灵感箱"),
            ]
        ),
        WorkspaceConfig(
            key="visualization",
            icon="📊",
            label="可视化",
            items=[
                SidebarItem("relationship", "🔗", "人物关系图"),
                SidebarItem("timeline", "⏱️", "时间轴"),
                SidebarItem("story_curve", "📈", "故事曲线"),
                SidebarItem("swimlanes", "🏊", "故事泳道"),
                SidebarItem("kanban", "📋", "场次看板"),
                SidebarItem("calendar", "📅", "故事日历"),
                SidebarItem("flowchart", "🕸️", "剧情流向"),
            ]
        ),
        WorkspaceConfig(
            key="worldbuilding",
            icon="🌍",
            label="世界观",
            items=[
                SidebarItem("wiki", "📚", "世界观百科"),
                SidebarItem("iceberg", "🏔️", "世界冰山"),
                SidebarItem("faction", "⚔️", "势力矩阵"),
                SidebarItem("research", "📖", "资料搜集"),
            ]
        ),
        WorkspaceConfig(
            key="mystery",
            icon="🔍",
            label="推理/悬疑",
            items=[
                SidebarItem("evidence_board", "🧩", "线索墙"),
                SidebarItem("dual_timeline", "⚖️", "表里双轨图"),
                SidebarItem("alibi", "🕵️", "不在场证明"),
                SidebarItem("heartbeat", "💗", "心动追踪"),
            ]
        ),
        WorkspaceConfig(
            key="tools",
            icon="⚙️",
            label="工具",
            items=[
                SidebarItem("variable", "🔢", "变量管理"),
                SidebarItem("analytics", "📊", "数据统计"),
                SidebarItem("reverse_engineering", "🔬", "反推导学习"),
                SidebarItem("training", "🎯", "创意训练"),
                SidebarItem("chat", "💬", "项目对话"),
            ]
        ),
    ]

    COLLAPSED_WIDTH = 36
    EXPANDED_WIDTH = 200
    COLLAPSED_CANVAS_PADDING = 2
    EXPANDED_CANVAS_PADDING = 20
    COLLAPSED_BUTTON_PADX = 0
    EXPANDED_BUTTON_PADX = 4
    COLLAPSED_TOOLBOX_PADX = 0
    EXPANDED_TOOLBOX_PADX = 8

    def _get_canvas_width(self, collapsed: bool) -> int:
        base_width = self.COLLAPSED_WIDTH if collapsed else self.EXPANDED_WIDTH
        canvas_padding = self.COLLAPSED_CANVAS_PADDING if collapsed else self.EXPANDED_CANVAS_PADDING
        return base_width - canvas_padding

    def _get_toolbox_text(self, collapsed: bool) -> str:
        return "➕" if collapsed else "➕ 工具箱"

    def _get_toggle_button_text(self, collapsed: bool) -> str:
        return "»" if collapsed else "≡"

    def _apply_panel_layout(self):
        if self.collapsed:
            self.top_bar.pack_configure(pady=(4, 2))
            self.title_label.pack_forget()
            self.collapse_btn.configure(width=2, text=self._get_toggle_button_text(True))
            self.collapse_btn.pack_configure(padx=self.COLLAPSED_BUTTON_PADX)
            if self.canvas.winfo_manager() == "pack":
                self.canvas.pack_forget()
            if self.toolbox_frame.winfo_manager() == "pack":
                self.toolbox_frame.pack_forget()
            if self.scrollbar.winfo_manager() == "pack":
                self.scrollbar.pack_forget()
        else:
            self.top_bar.pack_configure(pady=(4, 8))
            if self.title_label.winfo_manager() != "pack":
                self.title_label.pack(side=tk.LEFT, padx=8)
            self.collapse_btn.configure(width=3, text=self._get_toggle_button_text(False))
            self.collapse_btn.pack_configure(padx=self.EXPANDED_BUTTON_PADX)
            if self.canvas.winfo_manager() != "pack":
                self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            if self.scrollbar.winfo_manager() != "pack":
                self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.toolbox_btn.config(text=self._get_toolbox_text(False))
            self.toolbox_btn.pack_configure(padx=self.EXPANDED_TOOLBOX_PADX)
            if self.toolbox_frame.winfo_manager() != "pack":
                self.toolbox_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=4)

    def __init__(self, parent, theme_manager, on_item_select: Callable[[str, str], None],
                 config_manager=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.on_item_select = on_item_select
        self.config_manager = config_manager

        self.collapsed = False
        self.workspaces: Dict[str, WorkspaceSection] = {}
        self.current_workspace: Optional[str] = None
        self.current_item: Optional[str] = None

        # Map item keys to their workspace
        self.item_to_workspace: Dict[str, str] = {}

        self._setup_ui()
        self._restore_state()

    def _setup_ui(self):
        """Build the sidebar UI."""
        self.configure(width=self.EXPANDED_WIDTH)
        self.pack_propagate(False)

        # Top bar with collapse toggle
        self.top_bar = ttk.Frame(self)
        self.top_bar.pack(fill=tk.X, pady=(4, 8))

        self.collapse_btn = ttk.Button(
            self.top_bar,
            text=self._get_toggle_button_text(False),
            width=3,
            command=self.toggle_collapse
        )
        self.collapse_btn.pack(side=tk.LEFT, padx=self.EXPANDED_BUTTON_PADX)

        self.title_label = ttk.Label(
            self.top_bar,
            text="导航",
            font=("Microsoft YaHei", 11, "bold")
        )
        self.title_label.pack(side=tk.LEFT, padx=8)

        # Scrollable container for workspaces
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mouse wheel
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # Create workspace sections
        self._create_workspaces()

        # Toolbox button at bottom
        self.toolbox_frame = ttk.Frame(self)
        self.toolbox_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=4)

        self.toolbox_btn = ttk.Button(
            self.toolbox_frame,
            text=self._get_toolbox_text(False),
            command=lambda: self.on_item_select("toolbox", "toolbox")
        )
        self.toolbox_btn.pack(fill=tk.X, padx=self.EXPANDED_TOOLBOX_PADX, pady=4)

    def _create_workspaces(self):
        """Create workspace sections from definitions."""
        for ws_config in self.WORKSPACE_DEFINITIONS:
            # Build item-to-workspace mapping
            for item in ws_config.items:
                self.item_to_workspace[item.key] = ws_config.key

            section = WorkspaceSection(
                self.scrollable_frame,
                ws_config.key,
                ws_config.icon,
                ws_config.label,
                ws_config.items,
                self._on_workspace_item_select,
                self.theme_manager,
                self.collapsed
            )
            section.pack(fill=tk.X, pady=(0, 4))
            self.workspaces[ws_config.key] = section

    def _on_workspace_item_select(self, workspace_key: str, item_key: str):
        """Handle item selection from a workspace."""
        # Update active state
        if self.current_workspace and self.current_workspace != workspace_key:
            # Clear active state in previous workspace
            prev_ws = self.workspaces.get(self.current_workspace)
            if prev_ws:
                prev_ws.set_active_item(None)

        self.current_workspace = workspace_key
        self.current_item = item_key

        # Set active state in current workspace
        ws = self.workspaces.get(workspace_key)
        if ws:
            ws.set_active_item(item_key)

        # Save state
        self._save_state()

        # Notify callback
        self.on_item_select(workspace_key, item_key)

    def _bind_mousewheel(self, event):
        """Bind mouse wheel for scrolling."""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        """Unbind mouse wheel."""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll."""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    def toggle_collapse(self):
        """Toggle between hidden-strip and expanded mode."""
        self.collapsed = not self.collapsed
        new_width = self.COLLAPSED_WIDTH if self.collapsed else self.EXPANDED_WIDTH

        self._apply_panel_layout()

        # Update all workspaces
        for ws in self.workspaces.values():
            ws.set_collapsed_mode(self.collapsed)

        # Update width - need to configure and force geometry update
        self.configure(width=new_width)
        self.update_idletasks()

        # Force PanedWindow to update sash position if we're in a PanedWindow
        parent = self.master
        if isinstance(parent, ttk.PanedWindow):
            try:
                # Set sash position based on new width
                parent.sashpos(0, new_width)
            except tk.TclError:
                pass

        # Update canvas window width
        self._update_canvas_width()

        self._save_state()

    def _update_canvas_width(self):
        """Update canvas window width to match sidebar width."""
        self.canvas.itemconfigure(self.canvas_window, width=self._get_canvas_width(self.collapsed))

    def select_item(self, workspace_key: str, item_key: str):
        """Programmatically select an item."""
        self._on_workspace_item_select(workspace_key, item_key)

    def select_item_by_key(self, item_key: str):
        """Select an item by its key, auto-detecting workspace."""
        workspace_key = self.item_to_workspace.get(item_key)
        if workspace_key:
            self.select_item(workspace_key, item_key)

    def get_selected(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the currently selected workspace and item."""
        return self.current_workspace, self.current_item

    def register_item_frame(self, item_key: str, frame: ttk.Frame):
        """Register a frame reference for an item."""
        workspace_key = self.item_to_workspace.get(item_key)
        if workspace_key:
            ws = self.workspaces.get(workspace_key)
            if ws and item_key in ws.items:
                ws.items[item_key].frame = frame

    def get_enabled_items(self, enabled_tools: set) -> Dict[str, List[str]]:
        """Get items that should be visible based on enabled tools."""
        result = {}
        for ws_key, ws in self.workspaces.items():
            enabled = [k for k in ws.item_order if k in enabled_tools]
            if enabled:
                result[ws_key] = enabled
        return result

    def _save_state(self):
        """Save sidebar state to config."""
        if self.config_manager:
            self.config_manager.set("sidebar_collapsed", self.collapsed)
            self.config_manager.set("sidebar_active_workspace", self.current_workspace)
            self.config_manager.set("sidebar_active_item", self.current_item)
            self.config_manager.save()

    def _restore_state(self):
        """Restore sidebar state from config."""
        if not self.config_manager:
            return

        collapsed = self.config_manager.get("sidebar_collapsed", False)
        if collapsed:
            self.toggle_collapse()

        workspace = self.config_manager.get("sidebar_active_workspace")
        item = self.config_manager.get("sidebar_active_item")

        if workspace and item:
            self.current_workspace = workspace
            self.current_item = item

            ws = self.workspaces.get(workspace)
            if ws:
                ws.set_active_item(item)
        else:
            # Set default selection if none saved
            self.current_workspace = "writing"
            self.current_item = "outline"
            if "writing" in self.workspaces:
                self.workspaces["writing"].set_active_item("outline")

    def apply_theme(self):
        """Apply theme colors to the sidebar."""
        if not self.theme_manager:
            return

        style = ttk.Style()

        bg = self.theme_manager.get_color("sidebar_bg")
        fg = self.theme_manager.get_color("sidebar_fg")
        header_bg = self.theme_manager.get_color("sidebar_workspace_header")

        hover_bg = self.theme_manager.get_color("sidebar_item_hover")

        # Configure custom styles
        style.configure("Sidebar.TFrame", background=bg)
        style.configure("SidebarHeader.TFrame", background=header_bg)
        style.configure("SidebarHeaderHover.TFrame", background=hover_bg)
        style.configure("Sidebar.TLabel", background=bg, foreground=fg)
        style.configure("SidebarHeader.TLabel", background=header_bg, foreground=fg)

        # Apply to canvas
        self.canvas.configure(bg=bg)

        # Apply to all workspaces
        for ws in self.workspaces.values():
            ws.apply_theme()

    def update_visibility(self, enabled_tools: set):
        """Update which items are visible based on enabled tools."""
        for ws_key, ws in self.workspaces.items():
            visible_count = 0
            for item_key in ws.item_order:
                btn = ws.item_buttons.get(item_key)
                if btn:
                    if item_key in enabled_tools:
                        btn.master.pack(fill=tk.X, pady=1)
                        visible_count += 1
                    else:
                        btn.master.pack_forget()

            # Hide entire workspace if no visible items
            if visible_count == 0:
                ws.pack_forget()
            else:
                ws.pack(fill=tk.X, pady=(0, 4))
