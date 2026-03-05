import math
import tkinter as tk
from .base_view import BaseOutlineView
from writer_app.ui.components.zoomable_canvas import ZoomableCanvas

class FishboneView(BaseOutlineView, ZoomableCanvas):
    """
    Fishbone Diagram (Ishikawa Diagram) View
    Ideal for Suspense/Mystery plots to visualize Cause & Effect.
    Layout:
    - Root node is the "Head" (Right side).
    - Main branches are the "Ribs" (Angled).
    - Sub-branches are horizontal off the ribs.
    """

    def __init__(self, parent, project_manager, command_executor, **kwargs):
        BaseOutlineView.__init__(self, parent, project_manager, command_executor, **kwargs)
        ZoomableCanvas.__init__(self, parent, **kwargs)

        self.spine_y = 300
        self.head_x = 800
        self.tail_x = 100
        
        # Override node radius/size for this view if needed, or use default
        self.node_radius = 25 # Smaller nodes for fishbone

        # Bind events
        self._bind_events()

    def _bind_events(self):
        """Bind mouse and keyboard events"""
        self.bind("<Button-1>", self.on_click)
        self.bind("<Double-1>", self.on_double_click)
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<MouseWheel>", self.on_mousewheel)

    def on_click(self, event):
        """Handle click selection"""
        self.focus_set()
        self._close_edit_entry()
        self._hide_tooltip()
        
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        
        node_id = self._get_node_at(x, y)
        if node_id:
            self.select_node(node_id)
        else:
            self.deselect_all()

    def on_double_click(self, event):
        """Handle double click to edit"""
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        node_id = self._get_node_at(x, y)
        if node_id:
            self.select_node(node_id)
            self._start_edit(node_id)

    def on_right_click(self, event):
        """Handle right click context menu"""
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        node_id = self._get_node_at(x, y)
        if node_id and node_id not in self.selected_node_ids:
            self.select_node(node_id)
        
        self._update_status_menu()
        self._apply_ai_menu_state()
        self.context_menu.post(event.x_root, event.y_root)

    def on_mousewheel(self, event):
        """Handle scrolling and zooming"""
        if event.state & 0x0004: # Control key
             self.on_zoom(event)
        else:
             self.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh(self):
        """Refresh the canvas"""
        super().refresh()
        if not self.root_node:
            return

        # Calculate layout
        # Use center of current view or default
        center_y = max(300, self.winfo_height() / 2)
        center_x = max(400, self.winfo_width() / 2) # Not strictly used by _calculate_layout logic but passed
        
        positions = self._calculate_layout(self.root_node, center_x, center_y)
        
        if not positions:
            return
            
        # Draw connections first
        self._draw_connections(self.root_node, positions)
        
        # Draw nodes
        self._draw_nodes(self.root_node, positions, 0)
        
        # Update scroll region
        bbox = self.bbox("all")
        if bbox:
            padding = 50
            self.configure(scrollregion=(bbox[0] - padding, bbox[1] - padding,
                                         bbox[2] + padding, bbox[3] + padding))

    def _calculate_layout(self, root_node, center_x, center_y):
        """
        Calculate positions for Fishbone layout.
        Root = Head (Right)
        Level 1 Children = Main Ribs (Alternating Top/Bottom)
        Level 2 Children = Sub-ribs (Horizontal attached to Ribs)
        """
        positions = {}
        if not root_node: return positions

        # 1. Place Head (Root)
        # We use a fixed canvas size logic or dynamic based on children
        # Let's start with a dynamic width
        
        children = root_node.get("children", [])
        num_ribs = len(children)
        
        # Spacing
        rib_spacing = 150
        spine_length = max(600, num_ribs * rib_spacing + 200)
        
        # Center in canvas (start somewhat left)
        start_x = 100
        end_x = start_x + spine_length
        spine_y = center_y
        
        # Root Position (Head)
        positions[root_node.get("uid")] = [end_x, spine_y]
        
        # 2. Place Ribs (Level 1)
        # They are placed along the spine, starting from right to left or left to right?
        # Usually Cause -> Effect (Head is Effect). So Ribs are causes leading to head.
        # We place them from left to right along the spine.
        
        for i, child in enumerate(children):
            # Position along spine
            # Distribute them. 
            # If we want them pointing to the head, they should angle towards the right.
            
            # x position on spine
            rib_x = start_x + i * rib_spacing
            
            # Alternate Top/Bottom
            is_top = (i % 2 == 0)
            
            # Rib Length
            rib_len = 200
            angle = math.radians(135 if is_top else 225) # Pointing left-ish? 
            # Fishbone ribs usually angle *towards* the head (right).
            # So if top, angle is approx 135 (Top-Left) or 45 (Top-Right)?
            # If line goes FROM spine TO rib-end:
            #   Rib end is Top-Left relative to spine point? No, usually ribs feed INTO spine.
            #   Visual:  \  /
            #             -----
            #            /  \
            # Let's put Rib End points away from spine.
            # Top rib: Ends at Top-Left relative to connection point on spine.
            # Connection point on spine: (rib_x, spine_y)
            
            rib_angle = math.radians(240) if is_top else math.radians(120) 
            # 240 is Bottom-Left? 0 is Right, 90 Down, 180 Left, 270 Up.
            # Tkinter coords: y increases downwards.
            # 0 = Right, 90 = Down, 180 = Left, 270 = Up.
            # Top Rib: Needs to go UP (-y). Angled Left. So between 180 and 270. -> 225.
            # Bottom Rib: Needs to go DOWN (+y). Angled Left. So between 90 and 180. -> 135.
            
            rib_angle = math.radians(225) if is_top else math.radians(135)
            
            # Node Position (End of Rib)
            node_x = rib_x + rib_len * math.cos(rib_angle)
            node_y = spine_y + rib_len * math.sin(rib_angle)
            
            positions[child.get("uid")] = [node_x, node_y]
            
            # Store connection point on spine for drawing
            child["_fishbone_connect"] = [rib_x, spine_y]
            
            # 3. Place Sub-Ribs (Level 2) - Horizontal lines off the Rib
            sub_children = child.get("children", [])
            for j, sub in enumerate(sub_children):
                # Place along the rib line
                dist = 50 + j * 40
                sub_base_x = node_x - dist * math.cos(rib_angle) # Backtrack towards spine? No, start from node or spine?
                # Actually, standard fishbone has sub-causes branching horizontally.
                # Let's simplify: Vertical or Horizontal offsets from the Rib Node.
                
                # Let's put them horizontally to the left of the rib node
                sub_x = node_x - 100
                sub_y = node_y + (j * 30 * (1 if is_top else -1)) # Stack downwards for top rib?
                
                positions[sub.get("uid")] = [sub_x, sub_y]
                
                # Recurse? Fishbone usually flat 2-3 levels.
                # Level 3: just stack below/above level 2
                for k, deep in enumerate(sub.get("children", [])):
                    positions[deep.get("uid")] = [sub_x - 20, sub_y + (k+1)*20]

        return positions

    def _draw_connections(self, node, positions):
        uid = node.get("uid")
        if uid not in positions: return
        
        x, y = positions[uid]
        
        # Root special drawing: Draw Spine
        if node == self.root_node:
            # Draw Spine Line from Start to Head
            # We need start_x. Based on children count.
            children = node.get("children", [])
            if children:
                last_child = children[-1] # Actually the one furthest left is index 0 in my loop logic?
                # Loop used start_x + i*spacing. So last child is furthest RIGHT (closest to head).
                # First child (index 0) is furthest LEFT.
                first_child = children[0]
                if "_fishbone_connect" in first_child:
                    start_x = first_child["_fishbone_connect"][0] - 50
                    self.create_line(start_x, y, x, y, width=4, fill="#333", arrow=tk.LAST)
        
        # Draw connection to children
        for child in node.get("children", []):
            cid = child.get("uid")
            if cid in positions:
                cx, cy = positions[cid]
                
                if node == self.root_node:
                    # Rib connection: Node -> Spine Point
                    if "_fishbone_connect" in child:
                        sx, sy = child["_fishbone_connect"]
                        self.create_line(cx, cy, sx, sy, width=2, fill="#555")
                else:
                    # Normal Parent -> Child
                    self.create_line(x, y, cx, cy, width=1, fill="#777")
                
                self._draw_connections(child, positions)

    def _draw_nodes(self, node, positions, level):
        uid = node.get("uid")
        if uid in positions:
            x, y = positions[uid]
            # Custom shape for Root (Head)
            if node == self.root_node:
                # Draw Triangle or Box
                self.create_polygon(x, y-30, x+40, y, x, y+30, fill="#E3F2FD", outline="#1565C0", width=2, tags=(f"node_{uid}", "node"))
                self.create_text(x+10, y, text=node.get("name"), font=("Arial", 12, "bold"), tags=(f"label_{uid}", "label"))
            else:
                super()._draw_single_node(node, x, y, level)
            
        for child in node.get("children", []):
            self._draw_nodes(child, positions, level+1)
