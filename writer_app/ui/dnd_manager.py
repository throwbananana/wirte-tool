import tkinter as tk

class DragAndDropManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DragAndDropManager, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.drag_data = None
        self.drag_window = None
        self.source_widget = None
        
    def start_drag(self, widget, data, label_text, event):
        """Start a drag operation."""
        if self.drag_window:
            self.stop_drag()
            
        self.drag_data = data
        self.source_widget = widget
        
        # Create visual feedback
        self.drag_window = tk.Toplevel()
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes("-alpha", 0.7)
        self.drag_window.attributes("-topmost", True)
        
        label = tk.Label(self.drag_window, text=label_text, bg="#FFFFE0", relief="solid", borderwidth=1)
        label.pack()
        
        self._update_position(event.x_root, event.y_root)
        
    def update_drag(self, event):
        """Update drag window position."""
        if self.drag_window:
            self._update_position(event.x_root, event.y_root)
            
    def stop_drag(self):
        """Stop drag and cleanup."""
        if self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None
        # Data is kept briefly for the drop target to read, then cleared by the target or next start
        
    def _update_position(self, x, y):
        if self.drag_window:
            self.drag_window.geometry(f"+{x+15}+{y+15}")
            
    def get_data(self):
        return self.drag_data
    
    def clear(self):
        self.drag_data = None
        self.source_widget = None
