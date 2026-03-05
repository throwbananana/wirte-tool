import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog, ttk
try:
    from PIL import Image, ImageTk, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
import math
import random
import os
import tempfile
import time

from writer_app.core.commands import (
    UpdateCharLayoutCommand,
    AddLinkCommand,
    DeleteLinkCommand,
    EditLinkCommand,
    EditCharacterCommand,
    AddRelationshipEventCommand,
    UpdateRelationshipEventCommand,
    DeleteRelationshipEventCommand,
)
from writer_app.ui.dialogs import CharacterDialog
from writer_app.ui.components.zoomable_canvas import ZoomableCanvas
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.ui.components.empty_state_panel import EmptyStatePanel, EmptyStateConfig

class RelationshipMapCanvas(ZoomableCanvas):
    def __init__(self, parent, project_manager, command_executor, theme_manager=None, config_manager=None, on_jump_to_scene=None, on_jump_to_outline=None, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager
        self.config_manager = config_manager
        self.on_jump_to_scene = on_jump_to_scene
        self.on_jump_to_outline = on_jump_to_outline  # Callback to jump to outline node
        self.tag_filter = None
        
        self.node_radius = 40
        self.node_items = {} # name -> {x, y, type}
        
        # Dragging
        self.drag_data = {"item": None, "x": 0, "y": 0, "char_name": None}
        self.linking_data = {"active": False, "source": None, "line": None}
        
        # Images cache: name -> {"path": str, "photo": ImageTk.PhotoImage}
        self.images = {}
        
        # Force Layout
        self.force_layout_active = False
        self.velocity = {} # name -> {vx, vy}
        self.snapshot_links = None # Override links for time travel
        self._transform_offset = [0.0, 0.0]
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<Double-1>", self.on_double_click)

        # Tooltip window
        self._tooltip = None

        # Empty state panel
        self._empty_state_visible = False
        config = EmptyStateConfig.RELATIONSHIP
        self._empty_state = EmptyStatePanel(
            self,
            self.theme_manager,
            icon=config["icon"],
            title=config["title"],
            description=config["description"],
            action_text=config["action_text"],
            action_callback=self._on_empty_state_action
        )
        self._empty_state_window = None

        # Apply theme
        self._apply_theme()
        if self.theme_manager:
            self.theme_manager.add_listener(self._on_theme_change)

        # 订阅事件总线
        self._subscribe_events()

    def _on_theme_change(self):
        self._apply_theme()
        self.refresh()

    def _apply_theme(self):
        if self.theme_manager:
            bg = self.theme_manager.get_color("canvas_bg")
        else:
            bg = "#F0F0F0"
        self.configure(bg=bg)

    def _get_theme_colors(self):
        if self.theme_manager:
            return {
                "node_bg": self.theme_manager.get_color("canvas_bg"),
                "node_outline": self.theme_manager.get_color("fg_secondary"),
                "text": self.theme_manager.get_color("fg_primary"),
                "faction_fill": self.theme_manager.get_color("mindmap_node_bg"), # Reuse suitable color
                "faction_outline": self.theme_manager.get_color("mindmap_node_border"),
            }
        else:
            return {
                "node_bg": "#F0F0F0",
                "node_outline": "#333",
                "text": "#000",
                "faction_fill": "#FFF3E0",
                "faction_outline": "#FF8800"
            }

    def _on_empty_state_action(self):
        """Handle empty state action button click - open character dialog."""
        # Trigger add character through right-click menu logic
        messagebox.showinfo("提示", "请在剧本写作面板添加角色，或右键点击画布添加角色节点。")

    def _show_empty_state(self, show: bool):
        """Show or hide the empty state panel."""
        if show and not self._empty_state_visible:
            w = self.winfo_width()
            h = self.winfo_height()
            if w < 100:
                w = 800
            if h < 100:
                h = 600
            self._empty_state_window = self.create_window(
                w // 2, h // 2,
                window=self._empty_state,
                width=w - 40,
                height=h - 40,
                anchor=tk.CENTER,
                tags="empty_state"
            )
            self._empty_state_visible = True
        elif not show and self._empty_state_visible:
            if self._empty_state_window:
                self.delete("empty_state")
                self._empty_state_window = None
            self._empty_state_visible = False
            
    def _subscribe_events(self):
        """订阅相关事件"""
        bus = get_event_bus()
        bus.subscribe(Events.RELATIONSHIPS_UPDATED, self._on_relationships_changed)
        bus.subscribe(Events.RELATIONSHIP_LINK_ADDED, self._on_relationships_changed)
        bus.subscribe(Events.RELATIONSHIP_LINK_DELETED, self._on_relationships_changed)
        bus.subscribe(Events.CHARACTER_ADDED, self._on_character_changed)
        bus.subscribe(Events.CHARACTER_UPDATED, self._on_character_changed)
        bus.subscribe(Events.CHARACTER_DELETED, self._on_character_changed)
        bus.subscribe(Events.PROJECT_LOADED, self._on_project_loaded)

    def _on_relationships_changed(self, event_type, **kwargs):
        """关系变更时刷新"""
        self.refresh()

    def _on_character_changed(self, event_type, **kwargs):
        """角色变更时刷新"""
        self.refresh()

    def _on_project_loaded(self, event_type, **kwargs):
        """项目加载时刷新"""
        self.images.clear()  # 清除图片缓存
        self.refresh()

    def _show_link_tooltip(self, event, label, outline_ref_name):
        """显示连线的工具提示，包含大纲引用信息"""
        if self._tooltip:
            self._tooltip.destroy()
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        frame = tk.Frame(self._tooltip, bg="#FFFACD", relief=tk.SOLID, bd=1)
        frame.pack()

        tk.Label(frame, text=f"关系: {label}", bg="#FFFACD", font=("Arial", 9)).pack(anchor="w", padx=4, pady=2)
        tk.Label(frame, text=f"📖 事件: {outline_ref_name}", bg="#FFFACD", font=("Arial", 9, "bold"), fg="#B8860B").pack(anchor="w", padx=4, pady=2)

    def _hide_link_tooltip(self, event=None):
        """隐藏工具提示"""
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    def on_zoom(self, event, direction=None):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        prev_scale = self.scale_factor

        super().on_zoom(event, direction)

        if self.scale_factor == prev_scale:
            return
        multiplier = self.scale_factor / prev_scale
        tx, ty = self._transform_offset
        self._transform_offset = [
            tx * multiplier + (1 - multiplier) * x,
            ty * multiplier + (1 - multiplier) * y
        ]

    def _canvas_to_logical(self, x, y):
        tx, ty = self._transform_offset
        if self.scale_factor == 0:
            return 0, 0
        return (x - tx) / self.scale_factor, (y - ty) / self.scale_factor

    def set_snapshot_links(self, links):
        """Set override links from a snapshot. Pass None to revert to live data."""
        self.snapshot_links = links
        self.refresh()

    def _get_active_links(self):
        if self.snapshot_links is not None:
            return self.snapshot_links
        rels = self.project_manager.get_relationships()
        return rels.get("relationship_links", [])

    def refresh(self):
        self.delete("all")
        self.node_items.clear()

        chars = self.project_manager.get_characters()
        factions = self.project_manager.get_factions()

        # Show empty state if no characters and no factions
        if not chars and not factions:
            self._show_empty_state(True)
            return
        self._show_empty_state(False)

        rels = self.project_manager.get_relationships()
        layout = rels.get("character_layout", {})
        if not layout and rels.get("layout"):
            layout = dict(rels.get("layout", {}))
            rels["character_layout"] = layout
        
        # Use snapshot links if available, otherwise live links
        links = self._get_active_links()
        
        char_tags = {c["name"]: c.get("tags", []) for c in chars}
        char_names = {c["name"] for c in chars}
        faction_names = {f.get("name") for f in factions if f.get("name")}
        
        # 1. Ensure all characters have a position (auto-layout if new)
        existing_names = char_names.union(faction_names)

        # Smart auto-layout for new nodes: avoid overlap with existing nodes
        new_nodes = [name for name in existing_names if name not in layout]
        if new_nodes:
            center_x, center_y = self.winfo_width()/2 or 400, self.winfo_height()/2 or 300

            # Calculate adaptive radius based on total node count
            total_nodes = len(existing_names)
            min_spacing = self.node_radius * 3  # Minimum distance between node centers
            base_radius = max(200, total_nodes * min_spacing / (2 * math.pi))

            # Collect existing positions for collision detection
            existing_positions = [(layout[n][0], layout[n][1]) for n in layout if n in existing_names]

            for i, name in enumerate(new_nodes):
                # Try to find a non-overlapping position
                placed = False
                for radius_mult in [1.0, 1.5, 2.0, 2.5]:  # Try increasing radii
                    radius = base_radius * radius_mult
                    angle_step = 2 * math.pi / (len(new_nodes) or 1)
                    angle = i * angle_step

                    # Add random offset to avoid perfect alignment
                    angle += random.uniform(-0.2, 0.2)

                    candidate_x = center_x + radius * math.cos(angle)
                    candidate_y = center_y + radius * math.sin(angle)

                    # Check collision with existing nodes
                    collision = False
                    for ex, ey in existing_positions:
                        dist = math.sqrt((candidate_x - ex)**2 + (candidate_y - ey)**2)
                        if dist < min_spacing:
                            collision = True
                            break

                    if not collision:
                        layout[name] = [candidate_x, candidate_y]
                        existing_positions.append((candidate_x, candidate_y))
                        placed = True
                        break

                # Fallback: place with offset if all attempts fail
                if not placed:
                    offset = random.uniform(50, 150)
                    layout[name] = [
                        center_x + offset * random.choice([-1, 1]),
                        center_y + offset * random.choice([-1, 1])
                    ]
                    existing_positions.append((layout[name][0], layout[name][1]))
        
        # 2. Draw Links
        for i, link in enumerate(links):
            src, tgt = link["source"], link["target"]
            if self.tag_filter:
                if src in char_names and self.tag_filter not in char_tags.get(src, []):
                    continue
                if tgt in char_names and self.tag_filter not in char_tags.get(tgt, []):
                    continue
            label = link.get("label", "")
            color = link.get("color", "#666666")  # Use color from data
            outline_ref_uid = link.get("outline_ref_uid")  # Outline reference
            if src in layout and tgt in layout:
                self._draw_link(src, tgt, label, layout, i, color, outline_ref_uid)
        
        # 3. Draw Nodes
        for char in chars:
            name = char["name"]
            if self.tag_filter and self.tag_filter not in char.get("tags", []):
                continue
            if name in layout:
                pos = layout[name]
                self._draw_node(name, pos[0], pos[1], char.get("image_path"))

        for faction in factions:
            name = faction.get("name", "")
            if not name:
                continue
            if name in layout:
                pos = layout[name]
                self._draw_faction_node(name, pos[0], pos[1])
        
        # Apply scaling if needed (from ZoomableCanvas state)
        self.scale("all", 0, 0, self.scale_factor, self.scale_factor)
        if self._transform_offset != [0.0, 0.0]:
            self.move("all", self._transform_offset[0], self._transform_offset[1])
        self.configure(scrollregion=self.bbox("all"))

    def _draw_node(self, name, x, y, img_path):
        colors = self._get_theme_colors()
        
        # Draw circle
        r = self.node_radius
        tag = f"node_{name}"

        # Base circle to preserve node UI even when image fails
        base_fill = colors["node_bg"]
        self.create_oval(x - r, y - r, x + r, y + r, fill=base_fill, outline="", tags=(tag, "node"))

        # Image
        if img_path and HAS_PIL:
            cached = self.images.get(name)
            if not cached or cached.get("path") != img_path:
                loaded = self._load_circular_image(img_path, r)
                if loaded:
                    self.images[name] = {"path": img_path, "photo": loaded}
                else:
                    self.images[name] = {"path": img_path, "photo": None}

            img_data = self.images.get(name)
            if img_data and img_data.get("photo"):
                self.create_image(x, y, image=img_data["photo"], tags=(tag, "node"))
        else:
            # Clear cached image when image path removed
            if name in self.images:
                self.images.pop(name, None)

        # Border
        self.create_oval(x - r, y - r, x + r, y + r, outline=colors["node_outline"], width=2, tags=(tag, "node"))

        # Text Label
        self.create_text(x, y + r + 15, text=name, font=("Arial", 10, "bold"), fill=colors["text"], tags=(tag, "label"))

        self.node_items[name] = {"x": x, "y": y, "type": "character"}

    def _load_circular_image(self, img_path, radius):
        """Load and crop image into a circle for relationship nodes."""
        try:
            pil_img = Image.open(img_path)
            pil_img = pil_img.convert("RGBA")
            pil_img = pil_img.resize((radius * 2, radius * 2), Image.Resampling.LANCZOS)

            # Create circular mask
            mask = Image.new("L", (radius * 2, radius * 2), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)

            output = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
            output.paste(pil_img, (0, 0), mask)

            return ImageTk.PhotoImage(output)
        except Exception as e:
            print(f"Failed to load image for path {img_path}: {e}")
            return None

    def _draw_faction_node(self, name, x, y):
        colors = self._get_theme_colors()
        r = self.node_radius + 5
        tag = f"node_{name}"
        fill = colors["faction_fill"]
        outline = colors["faction_outline"]

        self.create_oval(x-r, y-r, x+r, y+r, outline=outline, width=2, fill=fill, tags=(tag, "node", "faction"))
        self.create_text(x, y + r + 15, text=name, font=("Arial", 10, "bold"), fill=colors["text"], tags=(tag, "label"))

        self.node_items[name] = {"x": x, "y": y, "type": "faction"}

    def _draw_link(self, src, tgt, label, layout, index, color="#666666", outline_ref_uid=None):
        x1, y1 = layout[src]
        x2, y2 = layout[tgt]

        # Calculate arrow end point (stop at radius)
        angle = math.atan2(y2-y1, x2-x1)
        r = self.node_radius + 5

        end_x = x2 - r * math.cos(angle)
        end_y = y2 - r * math.sin(angle)

        start_x = x1 + r * math.cos(angle)
        start_y = y1 + r * math.sin(angle)

        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2

        tag = f"link_{index}"

        # Draw line with different style if has outline reference
        line_width = 3 if outline_ref_uid else 2
        self.create_line(start_x, start_y, end_x, end_y, arrow=tk.LAST, fill=color, width=line_width, tags=(tag, "link"))

        # Draw label
        self.create_text(mid_x, mid_y - 10, text=label, fill=color, font=("Arial", 9), tags=(tag, "link_label"))

        # Draw outline reference indicator (small book icon or marker)
        if outline_ref_uid:
            # Get outline node name for tooltip
            outline = self.project_manager.get_outline()
            ref_node = self.project_manager.find_node_by_uid(outline, outline_ref_uid)
            ref_name = ref_node.get("name", "未知事件") if ref_node else "引用已删除"

            # Draw a small indicator (diamond shape) near the label
            indicator_x = mid_x + 8
            indicator_y = mid_y - 10
            size = 6
            self.create_polygon(
                indicator_x, indicator_y - size,
                indicator_x + size, indicator_y,
                indicator_x, indicator_y + size,
                indicator_x - size, indicator_y,
                fill="#FFD700", outline="#B8860B", width=1,
                tags=(tag, "link_indicator", f"outline_ref_{outline_ref_uid}")
            )
            # Store reference info for tooltip
            self.tag_bind(f"link_{index}", "<Enter>", lambda e, n=ref_name, l=label: self._show_link_tooltip(e, l, n))
            self.tag_bind(f"link_{index}", "<Leave>", self._hide_link_tooltip)

    def start_force_layout(self):
        if not self.force_layout_active:
            self.force_layout_active = True
            # Initialize velocity
            self.velocity = {name: {"vx": 0, "vy": 0} for name in self.node_items}
            self._step_force_layout()

    def stop_force_layout(self):
        self.force_layout_active = False

    def is_force_layout_running(self):
        return self.force_layout_active

    def _step_force_layout(self):
        if not self.force_layout_active:
            return

        # Parameters - tuned for better separation
        k = 180  # Ideal spring length (increased for more spacing)
        repulsion = 800000  # Repulsion strength (increased to prevent overlap)
        center_attraction = 0.03  # Reduced to allow more spreading
        damping = 0.85
        dt = 0.1
        min_distance = self.node_radius * 2.5  # Minimum allowed distance between nodes

        rels = self.project_manager.get_relationships()
        layout = rels.get("character_layout", {})
        if not layout and rels.get("layout"):
            layout = dict(rels.get("layout", {}))
            rels["character_layout"] = layout
        links = self._get_active_links()
        
        nodes = list(self.node_items.keys())
        width = self.winfo_width()
        height = self.winfo_height()
        if self.scale_factor:
            width = width / self.scale_factor
            height = height / self.scale_factor
        center_x, center_y = width / 2, height / 2

        # 1. Repulsion (Coulomb's Law) with minimum distance enforcement
        forces = {n: {"fx": 0, "fy": 0} for n in nodes}

        for i, n1 in enumerate(nodes):
            for n2 in nodes[i+1:]:
                if n1 not in layout or n2 not in layout: continue
                x1, y1 = layout[n1]
                x2, y2 = layout[n2]
                dx = x1 - x2
                dy = y1 - y2
                dist_sq = dx*dx + dy*dy
                if dist_sq < 0.1: dist_sq = 0.1
                dist = math.sqrt(dist_sq)

                # Base repulsion force
                f = repulsion / dist_sq

                # Extra strong repulsion when nodes are too close (overlap prevention)
                if dist < min_distance:
                    overlap_factor = (min_distance - dist) / min_distance
                    f *= (1 + overlap_factor * 5)  # Boost repulsion significantly

                fx = f * dx / dist
                fy = f * dy / dist

                forces[n1]["fx"] += fx
                forces[n1]["fy"] += fy
                forces[n2]["fx"] -= fx
                forces[n2]["fy"] -= fy

        # 2. Attraction (Hooke's Law) for links
        for link in links:
            src, tgt = link["source"], link["target"]
            if src in layout and tgt in layout:
                x1, y1 = layout[src]
                x2, y2 = layout[tgt]
                dx = x2 - x1
                dy = y2 - y1
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 0.1: dist = 0.1
                
                # Attraction towards target
                f = (dist - k) * 1.0 # Spring constant
                fx = f * dx / dist
                fy = f * dy / dist
                
                if src in forces:
                    forces[src]["fx"] += fx
                    forces[src]["fy"] += fy
                if tgt in forces:
                    forces[tgt]["fx"] -= fx
                    forces[tgt]["fy"] -= fy

        # 3. Center Gravity & Update
        for n in nodes:
            if n not in layout: continue
            x, y = layout[n]
            # Pull to center
            forces[n]["fx"] += (center_x - x) * center_attraction
            forces[n]["fy"] += (center_y - y) * center_attraction
            
            # Update Velocity
            if n not in self.velocity: self.velocity[n] = {"vx": 0, "vy": 0}
            self.velocity[n]["vx"] = (self.velocity[n]["vx"] + forces[n]["fx"] * dt) * damping
            self.velocity[n]["vy"] = (self.velocity[n]["vy"] + forces[n]["fy"] * dt) * damping
            
            # Update Position
            layout[n][0] += self.velocity[n]["vx"] * dt
            layout[n][1] += self.velocity[n]["vy"] * dt
            
            # Boundary constraint with adequate padding for node + label
            padding = self.node_radius + 30  # Account for node radius and label
            layout[n][0] = max(padding, min(width - padding, layout[n][0]))
            layout[n][1] = max(padding, min(height - padding - 20, layout[n][1]))  # Extra bottom space for label

        # Optimized update instead of full refresh
        self._update_positions(layout, links)
        self.after(30, self._step_force_layout)

    def _update_positions(self, layout, links):
        """Update coordinates of existing items without full redraw."""
        # 1. Update Nodes
        for name, data in self.node_items.items():
            if name in layout:
                # Get new logical coords
                lx, ly = layout[name]
                
                # Apply zoom + translation
                tx, ty = self._transform_offset
                sx = lx * self.scale_factor + tx
                sy = ly * self.scale_factor + ty
                
                # Update cache (logical coords)
                data["x"] = lx
                data["y"] = ly
                
                # Move visual items
                # We used tags: node_{name} for circle/image, and label_{name} ? 
                # Wait, in _draw_node I used tags=(tag, "node") and (tag, "label")
                # tag is f"node_{name}" for both.
                # So calculating delta is hard if we don't know previous visual center from canvas.
                # Easiest way with Canvas is absolute coords.
                
                base_radius = self.node_radius + 5 if data.get("type") == "faction" else self.node_radius
                r = base_radius * self.scale_factor
                
                # Circle/Image
                # Canvas.coords for image: x, y
                # Canvas.coords for oval: x1, y1, x2, y2
                
                # Find items with tag
                items = self.find_withtag(f"node_{name}")
                for item in items:
                    itype = self.type(item)
                    if itype == "image":
                        self.coords(item, sx, sy)
                    elif itype == "oval":
                        self.coords(item, sx-r, sy-r, sx+r, sy+r)
                    elif itype == "text":
                        # Text offset was y + r + 15 (unscaled)
                        # Scaled offset:
                        off = (base_radius + 15) * self.scale_factor
                        self.coords(item, sx, sy + off)

        # 2. Update Links
        for i, link in enumerate(links):
            src, tgt = link["source"], link["target"]
            if src in layout and tgt in layout:
                # Coords
                x1, y1 = layout[src]
                x2, y2 = layout[tgt]
                
                tx, ty = self._transform_offset
                sx1, sy1 = x1 * self.scale_factor + tx, y1 * self.scale_factor + ty
                sx2, sy2 = x2 * self.scale_factor + tx, y2 * self.scale_factor + ty
                
                # Recalculate arrow points
                angle = math.atan2(sy2-sy1, sx2-sx1)
                r = (self.node_radius + 5) * self.scale_factor
                
                end_x = sx2 - r * math.cos(angle)
                end_y = sy2 - r * math.sin(angle)
                
                start_x = sx1 + r * math.cos(angle)
                start_y = sy1 + r * math.sin(angle)
                
                mid_x = (start_x + end_x) / 2
                mid_y = (start_y + end_y) / 2
                
                # Update Line
                tag = f"link_{i}"
                line = self.find_withtag(tag)
                # Filter to line and text
                for item in line:
                    if self.type(item) == "line":
                        self.coords(item, start_x, start_y, end_x, end_y)
                    elif self.type(item) == "text":
                        self.coords(item, mid_x, mid_y - 10 * self.scale_factor)

    def export_to_image(self):
        """导出当前画布为图片"""
        if not HAS_PIL:
            messagebox.showerror("错误", "未安装 PIL (Pillow) 库，无法导出图片。\n请运行 pip install pillow")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            title="导出关系图"
        )
        
        if not file_path:
            return
            
        try:
            bbox = self.bbox("all")
            if not bbox:
                messagebox.showwarning("提示", "画布为空，无法导出")
                return
                
            x1, y1, x2, y2 = bbox
            padding = 20
            x1 -= padding
            y1 -= padding
            x2 += padding
            y2 += padding
            
            width = x2 - x1
            height = y2 - y1
            
            ps_data = self.postscript(colormode='color', x=x1, y=y1, width=width, height=height)
            
            if ps_data:
                with tempfile.NamedTemporaryFile(suffix='.ps', delete=False) as tmp_ps:
                    tmp_ps.write(ps_data.encode('utf-8'))
                    tmp_ps_path = tmp_ps.name
                
                try:
                    img = Image.open(tmp_ps_path)
                    img.save(file_path, "PNG")
                    messagebox.showinfo("成功", f"图片已导出至:\n{file_path}")
                finally:
                    if os.path.exists(tmp_ps_path):
                        os.unlink(tmp_ps_path)
            else:
                messagebox.showerror("错误", "生成 PostScript 数据失败")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出图片时发生错误:\n{str(e)}")

    def on_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        closest = self.find_closest(x, y)
        if not closest:
            return
        item = closest[0]
        tags = self.gettags(item)
        
        self.drag_data["char_name"] = None
        for tag in tags:
            if tag.startswith("node_"):
                self.drag_data["char_name"] = tag[5:]
                self.drag_data["start_x"] = x
                self.drag_data["start_y"] = y
                break

    def on_drag(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        
        if self.linking_data["active"]:
            self.coords(self.linking_data["line"], self.linking_data["start_x"], self.linking_data["start_y"], x, y)
            return

        name = self.drag_data["char_name"]
        if name:
            # Calculate displacement
            dx = x - self.drag_data["start_x"]
            dy = y - self.drag_data["start_y"]
            
            # Move the node visually
            self.move(f"node_{name}", dx, dy)
            
            # Update start position for next delta
            self.drag_data["start_x"] = x
            self.drag_data["start_y"] = y
            
            # Update internal cache
            if name in self.node_items:
                self.node_items[name]["x"] += dx / self.scale_factor
                self.node_items[name]["y"] += dy / self.scale_factor
                
            # Note: Links will snap to new position on release/refresh

    def on_release(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)

        if self.linking_data["active"]:
            # Check if dropped on a node
            target_name = self._get_node_at(x, y)
            if target_name and target_name != self.linking_data["source"]:
                # Ask for label, type and outline reference
                outline_nodes = self._get_outline_nodes_flat()
                dlg = LinkDialog(self.winfo_toplevel(), self.linking_data["source"], target_name, outline_nodes=outline_nodes)
                if dlg.result:
                    label, color, outline_ref_uid = dlg.result
                    link_data = {
                        "source": self.linking_data["source"],
                        "target": target_name,
                        "label": label,
                        "color": color
                    }
                    if outline_ref_uid:
                        link_data["outline_ref_uid"] = outline_ref_uid
                    src_type = self.node_items.get(self.linking_data["source"], {}).get("type")
                    tgt_type = self.node_items.get(target_name, {}).get("type")
                    if src_type == "faction":
                        link_data["source_type"] = "faction"
                    if tgt_type == "faction":
                        link_data["target_type"] = "faction"
                    cmd = AddLinkCommand(self.project_manager, link_data)
                    self.command_executor(cmd)

            self.delete(self.linking_data["line"])
            self.linking_data["active"] = False
            self.refresh()
            return

        name = self.drag_data["char_name"]
        if name:
            log_x = self.node_items[name]["x"]
            log_y = self.node_items[name]["y"]
            
            cmd = UpdateCharLayoutCommand(self.project_manager, name, [log_x, log_y])
            self.command_executor(cmd)
            self.refresh()
            self.drag_data["char_name"] = None

    def _get_outline_nodes_flat(self):
        """获取大纲节点的扁平列表，用于下拉选择"""
        outline = self.project_manager.get_outline()
        nodes = []

        def _traverse(node, depth=0):
            if node.get("uid") and node.get("name"):
                prefix = "  " * depth
                nodes.append({
                    "uid": node["uid"],
                    "name": node["name"],
                    "display": f"{prefix}{node['name']}"
                })
            for child in node.get("children", []):
                _traverse(child, depth + 1)

        _traverse(outline)
        return nodes

    def on_right_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        name = self._get_node_at(x, y)

        menu = tk.Menu(self, tearoff=0)
        read_only = self.snapshot_links is not None
        if name:
            if read_only:
                menu.add_command(label="快照模式（只读）", state=tk.DISABLED)
            else:
                menu.add_command(label=f"连线从 {name}...", command=lambda: self._start_link(name, x, y))
            node_type = self.node_items.get(name, {}).get("type", "character")
            if node_type == "character":
                if not read_only:
                    menu.add_command(label="编辑角色", command=lambda: self._edit_char_by_name(name))
                menu.add_separator()
                menu.add_command(label="查看关联场景", command=lambda: self._show_linked_scenes(name))

        # Check links
        link_idx = self._get_link_at(x, y)
        if link_idx is not None:
            links = self._get_active_links()
            link = links[link_idx] if 0 <= link_idx < len(links) else None

            menu.add_command(label="查看互动场景", command=lambda: self._show_link_interactions(link_idx))

            if not read_only:
                menu.add_command(label="编辑连线...", command=lambda: self._edit_link(link_idx))
                menu.add_command(label="删除连线", command=lambda: self._delete_link(link_idx))
                menu.add_command(label="添加关系事件...", command=lambda: self._add_link_event(link_idx))
            menu.add_command(label="事件列表...", command=lambda: self._show_link_event_list(link_idx))

            # Jump to outline reference if available
            if link and link.get("outline_ref_uid"):
                menu.add_separator()
                outline = self.project_manager.get_outline()
                ref_node = self.project_manager.find_node_by_uid(outline, link["outline_ref_uid"])
                ref_name = ref_node.get("name", "未知") if ref_node else "已删除"
                menu.add_command(
                    label=f"📖 跳转到事件: {ref_name}",
                    command=lambda uid=link["outline_ref_uid"]: self._jump_to_outline(uid)
                )

        menu.post(event.x_root, event.y_root)

    def _edit_link(self, link_idx):
        """编辑连线属性"""
        links = self._get_active_links()
        if not (0 <= link_idx < len(links)):
            return

        link = links[link_idx]
        outline_nodes = self._get_outline_nodes_flat()

        dlg = LinkDialog(
            self.winfo_toplevel(),
            link["source"],
            link["target"],
            outline_nodes=outline_nodes,
            existing_data=link  # Pass existing data for editing
        )

        if dlg.result:
            label, color, outline_ref_uid = dlg.result
            new_data = {
                "label": label,
                "color": color,
                "outline_ref_uid": outline_ref_uid if outline_ref_uid else None
            }
            # Remove None values
            new_data = {k: v for k, v in new_data.items() if v is not None}
            if not outline_ref_uid and "outline_ref_uid" in link:
                # Explicitly remove if cleared
                new_data["outline_ref_uid"] = None

            cmd = EditLinkCommand(self.project_manager, link_idx, new_data)
            self.command_executor(cmd)
            self.refresh()

    def _add_link_event(self, link_idx):
        """为关系连线添加事件记录"""
        links = self._get_active_links()
        if not (0 <= link_idx < len(links)):
            return

        link = links[link_idx]
        outline_nodes = self._get_outline_nodes_flat()

        dlg = RelationEventDialog(
            self.winfo_toplevel(),
            link.get("source", ""),
            link.get("target", ""),
            outline_nodes=outline_nodes,
            existing_data=link
        )
        if dlg.result:
            event_data = dlg.result
            cmd = AddRelationshipEventCommand(self.project_manager, link_idx, event_data)
            self.command_executor(cmd)
            self.refresh()

    def _get_link_events(self, link):
        rels = self.project_manager.get_relationships()
        events = rels.get("relationship_events", [])
        if not events:
            return []
        uids = set(link.get("event_uids", []))
        if uids:
            return [e for e in events if e.get("uid") in uids]

        source = link.get("source")
        target = link.get("target")
        label = link.get("label", "")
        target_type = link.get("target_type", "character")
        return [
            e for e in events
            if e.get("source") == source
            and e.get("target") == target
            and e.get("target_type", "character") == target_type
            and e.get("label", "") == label
        ]

    def _show_link_event_list(self, link_idx):
        links = self._get_active_links()
        if not (0 <= link_idx < len(links)):
            return
        link = links[link_idx]
        events = self._get_link_events(link)
        read_only = self.snapshot_links is not None
        dlg = RelationshipEventListDialog(
            self.winfo_toplevel(),
            self.project_manager,
            self.command_executor,
            link_idx,
            link,
            events,
            self._get_outline_nodes_flat(),
            read_only=read_only
        )
        self.wait_window(dlg)
        if dlg.changed:
            self.refresh()

    def _jump_to_outline(self, uid):
        """跳转到大纲节点"""
        if self.on_jump_to_outline:
            self.on_jump_to_outline(uid)
        else:
            messagebox.showinfo("提示", "无法跳转到大纲节点，请从大纲视图中查看。")

    def _show_link_interactions(self, link_idx):
        if not self.on_jump_to_scene:
            messagebox.showinfo("提示", "无法跳转到场景。")
            return
            
        links = self._get_active_links()
        if not (0 <= link_idx < len(links)): return
        
        link = links[link_idx]
        src, tgt = link["source"], link["target"]

        if self.node_items.get(src, {}).get("type") == "faction" or self.node_items.get(tgt, {}).get("type") == "faction":
            messagebox.showinfo("提示", "势力连线暂无场景检索。")
            return
        
        scenes = self.project_manager.get_scenes_with_character_pair(src, tgt)
        if not scenes:
            messagebox.showinfo("提示", f"未找到 {src} 和 {tgt} 同时出现的场景。")
            return
            
        dlg = tk.Toplevel(self)
        dlg.title(f"{src} & {tgt} 的互动场景")
        dlg.geometry("300x400")
        
        lb = tk.Listbox(dlg)
        lb.pack(fill=tk.BOTH, expand=True)
        
        for idx, s in scenes:
            lb.insert(tk.END, f"{idx+1}. {s.get('name')}")
            
        def jump(event):
            sel = lb.curselection()
            if sel:
                idx = scenes[sel[0]][0]
                self.on_jump_to_scene(idx)
                # dlg.destroy() # Optional: keep open to jump around
                
        lb.bind("<Double-1>", jump)

    def _show_linked_scenes(self, char_name):
        if not self.on_jump_to_scene:
            messagebox.showinfo("提示", "无法跳转到场景。")
            return
            
        scenes = self.project_manager.get_scenes_with_character(char_name)
        if not scenes:
            messagebox.showinfo("提示", f"角色 {char_name} 未在任何场景中出现。")
            return
            
        # If multiple, show dialog? For now, list dialog or jump to first?
        # Let's show a simple list dialog to pick
        
        dlg = tk.Toplevel(self)
        dlg.title(f"{char_name} 的场景")
        dlg.geometry("300x400")
        
        lb = tk.Listbox(dlg)
        lb.pack(fill=tk.BOTH, expand=True)
        
        for idx, s in scenes:
            lb.insert(tk.END, f"{idx+1}. {s.get('name')}")
            
        def jump(event):
            sel = lb.curselection()
            if sel:
                idx = scenes[sel[0]][0]
                self.on_jump_to_scene(idx)
                dlg.destroy()
                
        lb.bind("<Double-1>", jump)

    def on_double_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        name = self._get_node_at(x, y)
        if name and self.node_items.get(name, {}).get("type") == "character":
            self._edit_char_by_name(name)

    def set_tag_filter(self, tag_name):
        """Filter characters by tag (None for all)."""
        self.tag_filter = tag_name or None
        self.refresh()

    def _edit_char_by_name(self, name):
        # Find character data
        chars = self.project_manager.get_characters()
        char_data = next((c for c in chars if c["name"] == name), None)
        if char_data:
            # Find index
            idx = chars.index(char_data)
            
            # Fetch template if available
            template = []
            if self.config_manager:
                template = self.config_manager.get("character_template", [])
                
            dlg = CharacterDialog(self.winfo_toplevel(), "编辑角色", character=char_data, template=template)
            if dlg.result:
                new_data = dict(char_data)
                new_data.update(dlg.result) # Preserve existing tags/other fields
                cmd = EditCharacterCommand(self.project_manager, idx, char_data, new_data)
                self.command_executor(cmd)

    def _get_node_at(self, x, y):
        # Simple distance check
        lx, ly = self._canvas_to_logical(x, y)
        for name, data in self.node_items.items():
            dx = lx - data["x"]
            dy = ly - data["y"]
            radius = self.node_radius + 5 if data.get("type") == "faction" else self.node_radius
            if dx*dx + dy*dy < radius**2:
                return name
        return None

    def _get_link_at(self, x, y):
        closest = self.find_closest(x, y, halo=5)
        if not closest:
            return None
        item = closest[0]
        tags = self.gettags(item)
        for tag in tags:
            if tag.startswith("link_") and not tag.endswith("_label"):
                try:
                    return int(tag[5:])
                except (ValueError, IndexError):
                    pass  # 无效的链接索引格式，继续检查其他标签
        return None

    def _start_link(self, name, x, y):
        if self.snapshot_links is not None:
            messagebox.showinfo("提示", "快照模式下暂不支持编辑连线。")
            return
        self.linking_data["active"] = True
        self.linking_data["source"] = name
        self.linking_data["start_x"] = x
        self.linking_data["start_y"] = y
        self.linking_data["line"] = self.create_line(x, y, x, y, dash=(4, 2), width=2)

    def _delete_link(self, index):
        if self.snapshot_links is not None:
            messagebox.showinfo("提示", "快照模式下暂不支持删除连线。")
            return
        if messagebox.askyesno("删除", "删除此关系?"):
            self.command_executor(DeleteLinkCommand(self.project_manager, index))
            self.refresh()

class LinkDialog(simpledialog.Dialog):
    """添加/编辑关系连线对话框，支持大纲事件引用"""

    COLOR_OPTIONS = [
        ("普通", "#666666"),
        ("喜爱", "#E91E63"),
        ("憎恨", "#F44336"),
        ("盟友", "#4CAF50"),
        ("亲属", "#2196F3"),
        ("敌对", "#9C27B0"),
        ("合作", "#00BCD4"),
    ]

    def __init__(self, parent, src, tgt, outline_nodes=None, existing_data=None):
        self.src = src
        self.tgt = tgt
        self.outline_nodes = outline_nodes or []
        self.existing_data = existing_data  # For editing existing link
        self.outline_uid_map = {}  # display -> uid
        super().__init__(parent, title="编辑关系" if existing_data else "添加关系")

    def body(self, master):
        # Header
        tk.Label(master, text=f"{self.src} → {self.tgt}", font=("Arial", 10, "bold")).grid(row=0, columnspan=2, pady=(0, 10))

        # Label/Description
        tk.Label(master, text="关系描述:").grid(row=1, column=0, sticky="w")
        self.e1 = tk.Entry(master, width=30)
        self.e1.grid(row=1, column=1, sticky="ew", padx=5)

        # Color/Type
        tk.Label(master, text="关系类型:").grid(row=2, column=0, sticky="w")
        color_display = [f"{name} ({color})" for name, color in self.COLOR_OPTIONS]
        self.cb = ttk.Combobox(master, state="readonly", values=color_display, width=28)
        self.cb.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        self.cb.current(0)

        # Outline Reference
        tk.Label(master, text="📖 起因事件:").grid(row=3, column=0, sticky="w")
        outline_display = ["(无)"] + [n["display"] for n in self.outline_nodes]
        self.outline_uid_map = {n["display"]: n["uid"] for n in self.outline_nodes}
        self.outline_cb = ttk.Combobox(master, state="readonly", values=outline_display, width=28)
        self.outline_cb.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        self.outline_cb.current(0)

        # Help text
        tk.Label(
            master,
            text="选择导致此关系变化的大纲事件（可选）",
            font=("Arial", 8),
            fg="#888"
        ).grid(row=4, columnspan=2, pady=(0, 5))

        # Pre-fill if editing existing link
        if self.existing_data:
            self.e1.insert(0, self.existing_data.get("label", ""))

            # Set color
            existing_color = self.existing_data.get("color", "#666666")
            for i, (name, color) in enumerate(self.COLOR_OPTIONS):
                if color == existing_color:
                    self.cb.current(i)
                    break

            # Set outline reference
            existing_ref = self.existing_data.get("outline_ref_uid")
            if existing_ref:
                for i, node in enumerate(self.outline_nodes):
                    if node["uid"] == existing_ref:
                        self.outline_cb.current(i + 1)  # +1 because of "(无)"
                        break

        master.columnconfigure(1, weight=1)
        return self.e1

    def apply(self):
        label = self.e1.get().strip()
        if not label:
            label = "相关"  # Default label

        # Parse color from combobox "Name (Color)"
        val = self.cb.get()
        color = val.split("(")[-1].strip(")")

        # Get outline reference UID
        outline_selection = self.outline_cb.get()
        outline_ref_uid = self.outline_uid_map.get(outline_selection) if outline_selection != "(无)" else None

        self.result = (label, color, outline_ref_uid)


class RelationEventDialog(simpledialog.Dialog):
    """关系事件录入对话框"""

    def __init__(self, parent, src, tgt, outline_nodes=None, existing_data=None, event_data=None):
        self.src = src
        self.tgt = tgt
        self.outline_nodes = outline_nodes or []
        self.existing_data = existing_data or {}
        self.event_data = event_data or {}
        self.outline_uid_map = {}
        self.result = None
        title = "编辑关系事件" if self.event_data else "添加关系事件"
        super().__init__(parent, title=title)

    def body(self, master):
        tk.Label(master, text=f"{self.src} ↔ {self.tgt}", font=("Arial", 10, "bold")).grid(row=0, columnspan=2, pady=(0, 10))

        tk.Label(master, text="章节/帧标题:").grid(row=1, column=0, sticky="w")
        self.e_chapter = tk.Entry(master, width=30)
        self.e_chapter.grid(row=1, column=1, sticky="ew", padx=5)

        tk.Label(master, text="事件描述:").grid(row=2, column=0, sticky="w")
        self.e_desc = tk.Entry(master, width=30)
        self.e_desc.grid(row=2, column=1, sticky="ew", padx=5)

        tk.Label(master, text="关联大纲事件:").grid(row=3, column=0, sticky="w")
        outline_display = ["(无)"] + [n["display"] for n in self.outline_nodes]
        self.outline_uid_map = {n["display"]: n["uid"] for n in self.outline_nodes}
        self.outline_cb = ttk.Combobox(master, state="readonly", values=outline_display, width=28)
        self.outline_cb.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        self.outline_cb.current(0)

        hint = "用于事件帧分组（可填章节名或时间点）"
        tk.Label(master, text=hint, font=("Arial", 8), fg="#888").grid(row=4, columnspan=2, pady=(0, 5))

        default_desc = self.event_data.get("description") or self.existing_data.get("label", "关系变化")
        self.e_desc.insert(0, default_desc)
        if self.event_data.get("chapter_title"):
            self.e_chapter.insert(0, self.event_data.get("chapter_title"))
        existing_ref = self.event_data.get("outline_ref_uid")
        if existing_ref:
            for i, node in enumerate(self.outline_nodes):
                if node["uid"] == existing_ref:
                    self.outline_cb.current(i + 1)
                    break

        master.columnconfigure(1, weight=1)
        return self.e_chapter

    def apply(self):
        chapter_title = self.e_chapter.get().strip()
        description = self.e_desc.get().strip() or "关系变化"
        outline_selection = self.outline_cb.get()
        outline_ref_uid = self.outline_uid_map.get(outline_selection) if outline_selection != "(无)" else None

        self.result = {
            "source": self.src,
            "target": self.tgt,
            "target_type": self.existing_data.get("target_type", "character"),
            "label": self.existing_data.get("label", ""),
            "description": description,
            "chapter_title": chapter_title,
            "created_at": self.event_data.get("created_at", time.time()),
            "origin": self.event_data.get("origin", "manual")
        }
        if outline_ref_uid:
            self.result["outline_ref_uid"] = outline_ref_uid
        if self.event_data.get("uid"):
            self.result["uid"] = self.event_data.get("uid")


class RelationshipEventListDialog(tk.Toplevel):
    """关系事件列表（查看/编辑/删除）"""

    def __init__(self, parent, project_manager, command_executor, link_idx, link, events, outline_nodes, read_only=False):
        super().__init__(parent)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.link_idx = link_idx
        self.link = link
        self.events = list(events)
        self.outline_nodes = outline_nodes
        self.read_only = read_only
        self.changed = False

        self.title("关系事件列表")
        self.geometry("820x360")
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        top = tk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=6)
        tk.Label(top, text=f"{self.link.get('source')} ↔ {self.link.get('target')}").pack(side=tk.LEFT)

        btns = tk.Frame(self)
        btns.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.btn_add = ttk.Button(btns, text="添加", command=self._add_event)
        self.btn_edit = ttk.Button(btns, text="编辑", command=self._edit_event)
        self.btn_del = ttk.Button(btns, text="删除", command=self._delete_event)
        self.btn_close = ttk.Button(btns, text="关闭", command=self.destroy)

        self.btn_add.pack(side=tk.LEFT, padx=4)
        self.btn_edit.pack(side=tk.LEFT, padx=4)
        self.btn_del.pack(side=tk.LEFT, padx=4)
        self.btn_close.pack(side=tk.RIGHT, padx=4)

        if self.read_only:
            self.btn_add.configure(state=tk.DISABLED)
            self.btn_edit.configure(state=tk.DISABLED)
            self.btn_del.configure(state=tk.DISABLED)

        columns = ("time", "chapter", "description", "outline", "source", "target", "relation", "origin", "frame_id")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.heading("time", text="时间")
        self.tree.heading("chapter", text="章节/帧")
        self.tree.heading("description", text="描述")
        self.tree.heading("outline", text="大纲事件")
        self.tree.heading("source", text="来源角色")
        self.tree.heading("target", text="目标角色")
        self.tree.heading("relation", text="关系")
        self.tree.heading("origin", text="来源")
        self.tree.heading("frame_id", text="帧ID")

        self.tree.column("time", width=130, anchor="w")
        self.tree.column("chapter", width=140, anchor="w")
        self.tree.column("description", width=200, anchor="w")
        self.tree.column("outline", width=140, anchor="w")
        self.tree.column("source", width=90, anchor="w")
        self.tree.column("target", width=90, anchor="w")
        self.tree.column("relation", width=120, anchor="w")
        self.tree.column("origin", width=90, anchor="w")
        self.tree.column("frame_id", width=140, anchor="w")

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for ev in self.events:
            created_at = ev.get("created_at", 0)
            ts = ""
            try:
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(created_at))
            except Exception:
                ts = ""
            outline_name = ""
            outline_uid = ev.get("outline_ref_uid")
            if outline_uid:
                outline = self.project_manager.get_outline()
                ref_node = self.project_manager.find_node_by_uid(outline, outline_uid)
                outline_name = ref_node.get("name", "未知") if ref_node else "已删除"
            relation_label = ev.get("label", "")
            values = (
                ts,
                ev.get("chapter_title", ""),
                ev.get("description", ""),
                outline_name,
                ev.get("source", ""),
                ev.get("target", ""),
                relation_label,
                ev.get("origin", ""),
                ev.get("frame_id", "")
            )
            self.tree.insert("", tk.END, iid=ev.get("uid", ""), values=values)

    def _get_selected_event(self):
        sel = self.tree.selection()
        if not sel:
            return None
        uid = sel[0]
        for ev in self.events:
            if ev.get("uid") == uid:
                return ev
        return None

    def _add_event(self):
        dlg = RelationEventDialog(
            self,
            self.link.get("source", ""),
            self.link.get("target", ""),
            outline_nodes=self.outline_nodes,
            existing_data=self.link
        )
        if dlg.result:
            cmd = AddRelationshipEventCommand(self.project_manager, self.link_idx, dlg.result)
            if self.command_executor(cmd):
                self.events = self._reload_events()
                self.changed = True
                self._refresh_list()

    def _edit_event(self):
        ev = self._get_selected_event()
        if not ev:
            messagebox.showinfo("提示", "请先选择一条事件。")
            return
        dlg = RelationEventDialog(
            self,
            self.link.get("source", ""),
            self.link.get("target", ""),
            outline_nodes=self.outline_nodes,
            existing_data=self.link,
            event_data=ev
        )
        if dlg.result:
            cmd = UpdateRelationshipEventCommand(self.project_manager, self.link_idx, ev.get("uid"), dlg.result)
            if self.command_executor(cmd):
                self.events = self._reload_events()
                self.changed = True
                self._refresh_list()

    def _delete_event(self):
        ev = self._get_selected_event()
        if not ev:
            messagebox.showinfo("提示", "请先选择一条事件。")
            return
        if not messagebox.askyesno("删除事件", "确定删除该关系事件吗？"):
            return
        cmd = DeleteRelationshipEventCommand(self.project_manager, self.link_idx, ev.get("uid"))
        if self.command_executor(cmd):
            self.events = self._reload_events()
            self.changed = True
            self._refresh_list()

    def _reload_events(self):
        rels = self.project_manager.get_relationships()
        events = rels.get("relationship_events", [])
        link = rels.get("relationship_links", [])[self.link_idx]
        uids = set(link.get("event_uids", []))
        if uids:
            return [e for e in events if e.get("uid") in uids]
        return [
            e for e in events
            if e.get("source") == link.get("source")
            and e.get("target") == link.get("target")
            and e.get("target_type", "character") == link.get("target_type", "character")
            and e.get("label", "") == link.get("label", "")
        ]
