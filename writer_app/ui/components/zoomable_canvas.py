import tkinter as tk
from tkinter import ttk

class ZoomableCanvas(tk.Canvas):
    """
    A Canvas subclass that supports zooming (Ctrl+Wheel) and panning (Right-drag or Middle-drag).
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Scaling state
        self.scale_factor = 1.0
        self.min_scale = 0.1
        self.max_scale = 5.0
        
        # Pan state
        self._pan_start_x = 0
        self._pan_start_y = 0
        
        # Bind events
        # Zoom: Ctrl + MouseWheel (Windows/Linux) or Command + MouseWheel (Mac)
        self.bind("<Control-MouseWheel>", self.on_zoom)
        # Linux might use Button-4 and Button-5
        self.bind("<Control-Button-4>", lambda e: self.on_zoom(e, 1))
        self.bind("<Control-Button-5>", lambda e: self.on_zoom(e, -1))
        
        # Pan: Right mouse button drag (Button-3) or Middle mouse (Button-2)
        # Choosing Button-3 (Right Click) for Pan might conflict with Context Menu.
        # Let's use Middle Button (Button-2) or Space+Drag logic if desired.
        # Standard: Middle Button or Space + Left Drag.
        # Let's support Middle Button (Button-2) for Pan.
        self.bind("<ButtonPress-2>", self.start_pan)
        self.bind("<B2-Motion>", self.do_pan)
        
        # Also support Alt+Drag or Space+Drag logic in subclasses if needed, 
        # but built-in Middle Drag is standard for CAD/Design tools.
        
    def on_zoom(self, event, direction=None):
        """Zoom in or out centered on mouse pointer."""
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        
        # Determine scroll direction
        if direction:
            delta = direction
        else:
            delta = 1 if event.delta > 0 else -1
            
        scale_multiplier = 1.1 if delta > 0 else 0.9
        
        new_scale = self.scale_factor * scale_multiplier
        if new_scale < self.min_scale or new_scale > self.max_scale:
            return
            
        self.scale_factor = new_scale
        
        # Rescale all objects
        self.scale("all", x, y, scale_multiplier, scale_multiplier)
        
        # Adjust scroll region
        self.configure(scrollregion=self.bbox("all"))
        
        # Trigger redraw if necessary (subclasses might want to redraw semantic zoom)
        # self.event_generate("<<ZoomChanged>>") 
        
    def start_pan(self, event):
        self.scan_mark(event.x, event.y)
        self._pan_start_x = event.x
        self._pan_start_y = event.y

    def do_pan(self, event):
        self.scan_dragto(event.x, event.y, gain=1)
