import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import logging

from writer_app.core.models import ProjectManager
from writer_app.core.config import ConfigManager
from writer_app.core.theme import ThemeManager
from writer_app.ui.galgame_assets import GalgameAssetsController
from writer_app.ui.editors.event_editor import EventEditorPanel
from writer_app.utils.logging_utils import setup_logging
from writer_app.core.icon_manager import IconManager
from writer_app.core.font_manager import get_font_manager
from writer_app.ui.components.toast import show_toast

logger = logging.getLogger(__name__)

class AssetEditorApp:
    """独立资源编辑器 (Standalone Asset Editor)"""

    def __init__(self, root):
        self.root = root
        self.root.title("资源管理器 - Asset Editor")
        
        self.data_dir = Path(__file__).parent.parent / "writer_data"
        self.data_dir.mkdir(exist_ok=True)
        setup_logging(self.data_dir)
        
        # Init Managers
        try:
            get_font_manager().load_local_fonts()
        except: pass
        self.icon_mgr = IconManager()
        
        self.config_manager = ConfigManager()
        self.theme_manager = ThemeManager(self.config_manager.get("theme", "Light"))
        self.project_manager = ProjectManager()
        
        # Window setup
        geometry = self.config_manager.get("asset_editor_geometry", "1000x700")
        self.root.geometry(geometry)
        
        self.setup_menu()
        self.setup_ui()
        
        # Auto-load last project if possible
        last_file = self.config_manager.get("last_opened_file")
        if last_file and Path(last_file).exists():
            try:
                self.project_manager.load_project(last_file)
                self.refresh()
                self.root.title(f"资源管理器 - {Path(last_file).name}")

                # Load associated events file
                events_file = self._get_project_events_file(Path(last_file))
                self._create_event_editor(events_file)

                # Update status bar
                self.file_label.configure(text=Path(last_file).name)
                self._update_status("已加载上次项目")
            except Exception as e:
                logger.error(f"Auto-load failed: {e}")

        self.apply_theme()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开项目...", command=self.open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="保存项目", command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing, accelerator="Alt+F4")

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="切换主题", command=self.toggle_theme, accelerator="Ctrl+T")
        view_menu.add_separator()
        view_menu.add_command(label="资源管理", command=lambda: self.notebook.select(0), accelerator="Ctrl+1")
        view_menu.add_command(label="事件编辑", command=lambda: self.notebook.select(1), accelerator="Ctrl+2")

        # Bind keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self.open_project())
        self.root.bind("<Control-s>", lambda e: self.save_project())
        self.root.bind("<Control-t>", lambda e: self.toggle_theme())
        self.root.bind("<Control-Key-1>", lambda e: self.notebook.select(0))
        self.root.bind("<Control-Key-2>", lambda e: self.notebook.select(1))

    def setup_ui(self):
        # Main Container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Status bar at bottom
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

        self.status_label = ttk.Label(self.status_frame, text="就绪", foreground="#666666")
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.file_label = ttk.Label(self.status_frame, text="未打开项目", foreground="#999999")
        self.file_label.pack(side=tk.RIGHT, padx=5)

        self.modified_label = ttk.Label(self.status_frame, text="", foreground="#D32F2F")
        self.modified_label.pack(side=tk.RIGHT, padx=5)

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Asset Editor
        self.asset_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.asset_frame, text="资源管理")

        self.asset_controller = GalgameAssetsController(
            self.asset_frame,
            self.project_manager,
            execute_command=None
        )

        # Event Editor (initially with default events file, will update on project load)
        self.event_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.event_frame, text="事件编辑")
        self._create_event_editor()
        
    def _create_event_editor(self, events_file: Path = None):
        """Create or recreate the event editor panel."""
        # Clear existing
        for widget in self.event_frame.winfo_children():
            widget.destroy()

        # Get events file path
        if events_file is None:
            events_file = self.data_dir / "school_events.json"

        self.events_file = events_file
        self.event_editor = EventEditorPanel(
            self.event_frame,
            file_path=events_file,
            on_modified=self._on_events_modified,
            mode="file",
        )
        self.event_editor.pack(fill=tk.BOTH, expand=True)

    def _on_events_modified(self):
        """Handle events modification."""
        self.modified_label.configure(text="● 有未保存的更改")

    def _get_project_events_file(self, project_path: Path) -> Path:
        """Get the events file associated with a project."""
        # Events file is stored alongside project with _events.json suffix
        # e.g., MyProject.writerproj -> MyProject_events.json
        return project_path.with_suffix("").with_name(project_path.stem + "_events.json")

    def _update_status(self, text: str):
        """Update status bar text."""
        self.status_label.configure(text=text)

    def open_project(self):
        path = filedialog.askopenfilename(defaultextension=".writerproj", filetypes=[("Writer Project", "*.writerproj")])
        if path:
            if self.project_manager.modified:
                if not messagebox.askyesno("未保存", "当前更改未保存，是否继续？"):
                    return
            self.project_manager.load_project(path)
            self.refresh()
            self.root.title(f"资源管理器 - {Path(path).name}")

            # Load associated events file
            events_file = self._get_project_events_file(Path(path))
            self._create_event_editor(events_file)

            # Update status
            self.file_label.configure(text=Path(path).name)
            self.modified_label.configure(text="")
            self._update_status(f"已加载项目: {Path(path).name}")

            # Update config to sync with main app
            self.config_manager.set("last_opened_file", path)
            self.config_manager.save()

    def save_project(self):
        if self.project_manager.current_file:
            self.project_manager.save_project()
            self.modified_label.configure(text="")
            self._update_status("项目已保存")
            show_toast(self.root, "项目已保存", toast_type="success", duration=1500)
        else:
            show_toast(self.root, "请先打开一个项目", toast_type="warning", duration=2000)

    def refresh(self):
        self.asset_controller.refresh()
        if hasattr(self, 'event_editor'):
            self.event_editor.refresh()

    def toggle_theme(self):
        self.theme_manager.toggle_theme()
        self.apply_theme()

    def apply_theme(self):
        theme = self.theme_manager
        style = ttk.Style(self.root)
        try:
            style.theme_use('clam')
        except: pass
        
        bg = theme.get_color("bg_secondary")
        fg = theme.get_color("fg_primary")
        
        self.root.configure(bg=bg)
        style.configure(".", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("TButton", background=bg, foreground=fg)
        
        # Refresh controller UI
        # AssetController doesn't have `apply_theme` method exposed but uses standard widgets.
        # We might need to manually trigger refresh or if widgets listen to style changes.
        # Re-creating might be cleanest for theme switch if simple style update isn't enough.
        # But standard ttk widgets update with style.
        pass

    def on_closing(self):
        if self.project_manager.modified:
            if messagebox.askyesno("保存", "项目有未保存的更改，是否保存？"):
                self.save_project()
        
        self.config_manager.set("asset_editor_geometry", self.root.geometry())
        self.config_manager.save()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AssetEditorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
