import threading
from datetime import datetime

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False


class TrayManager:
    """System tray manager (optional; requires pystray + Pillow)."""

    def __init__(self, root, on_show, on_hide, on_exit):
        self.root = root
        self.on_show = on_show
        self.on_hide = on_hide
        self.on_exit = on_exit
        self._icon = None
        self._events = []
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        return HAS_PYSTRAY

    def set_events(self, events):
        with self._lock:
            self._events = list(events or [])
        if self._icon:
            self._icon.menu = self._build_menu()

    def ensure_started(self) -> bool:
        if not HAS_PYSTRAY:
            return False
        if self._icon:
            return True

        image = self._create_default_icon()
        self._icon = pystray.Icon("writer_tool", image, "写作助手", self._build_menu())
        self._icon.run_detached()
        return True

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def _create_default_icon(self):
        size = 64
        image = Image.new("RGBA", (size, size), (30, 136, 229, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((6, 6, size - 6, size - 6), outline=(255, 255, 255, 255), width=3)
        draw.text((size // 2, size // 2), "W", fill=(255, 255, 255, 255), anchor="mm")
        return image

    def _toggle_window(self, icon=None, item=None):
        def _action():
            try:
                if self.root.state() == "withdrawn" or not self.root.winfo_viewable():
                    self.on_show()
                else:
                    self.on_hide()
            except Exception:
                self.on_show()

        self.root.after(0, _action)

    def _exit(self, icon=None, item=None):
        self.root.after(0, self.on_exit)

    def _build_menu(self):
        items = [
            pystray.MenuItem("显示/隐藏", self._toggle_window),
            pystray.Menu.SEPARATOR,
        ]

        events_menu = self._build_events_menu()
        items.append(pystray.MenuItem("日期事件", events_menu))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("退出", self._exit))
        return pystray.Menu(*items)

    def _build_events_menu(self):
        events = self._get_sorted_events()
        if not events:
            return pystray.Menu(pystray.MenuItem("暂无事件", None, enabled=False))

        menu_items = []
        for evt in events[:8]:
            label = f"{evt.get('date', '')} - {evt.get('title', '')}".strip(" -")
            menu_items.append(pystray.MenuItem(label or "未命名事件", None, enabled=False))
        return pystray.Menu(*menu_items)

    def _get_sorted_events(self):
        with self._lock:
            events = list(self._events)

        def _parse_date(value):
            try:
                return datetime.strptime(value, "%Y-%m-%d")
            except Exception:
                return datetime.max

        return sorted(events, key=lambda e: _parse_date(e.get("date", "")))
