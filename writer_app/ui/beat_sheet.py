import tkinter as tk
from tkinter import ttk, messagebox
import logging

from writer_app.core.commands import EditSceneCommand
from writer_app.ui.components.zoomable_canvas import ZoomableCanvas
from writer_app.core.event_bus import get_event_bus, Events

logger = logging.getLogger(__name__)


class BeatSheetView(ttk.Frame):
    """
    Beat Sheet View allowing mapping of scenes to specific beats.
    Implements a drag-and-drop interface.

    Features:
    - 支持 Save the Cat 等多种节拍表模板
    - 拖放场景到节拍槽位
    - 可视化展示场景与节拍的映射关系
    - 与 EventBus 集成实现实时更新
    """
    def __init__(self, parent, project_manager, command_executor, theme_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager

        # Standard Beats (Save the Cat style)
        self.beats = [
            ("Opening Image", "开篇画面", "介绍主角现状", 1),
            ("Theme Stated", "主题呈现", "暗示故事主题", 5),
            ("Setup", "铺垫", "展现主角生活和缺陷", 10),
            ("Catalyst", "催化剂", "打破平衡的事件", 12),
            ("Debate", "争辩", "主角犹豫是否行动", 25),
            ("Break into Two", "进入第二幕", "主角决定踏上旅程", 30),
            ("B Story", "B故事", "次要情节/感情线", 35),
            ("Fun and Games", "游戏时刻", "探索新世界/承诺前提", 55),
            ("Midpoint", "中点", "伪胜利或伪失败，赌注提高", 50),
            ("Bad Guys Close In", "反派逼近", "压力增加，困难重重", 75),
            ("All Is Lost", "一无所有", "遭受重大打击", 75),
            ("Dark Night of the Soul", "灵魂黑夜", "主角绝望反思", 85),
            ("Break into Three", "进入第三幕", "找到解决方案", 85),
            ("Finale", "结局", "决战，应用所学", 100),
            ("Final Image", "终场画面", "展示主角变化后的新常态", 100)
        ]

        # 接口兼容性属性
        self.tag_filter = None
        self.scene_counts = {}

        self.setup_ui()

        # 订阅事件（在 UI 设置完成后）
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅 EventBus 事件"""
        bus = get_event_bus()
        bus.subscribe(Events.SCENE_ADDED, self._on_scene_event)
        bus.subscribe(Events.SCENE_UPDATED, self._on_scene_event)
        bus.subscribe(Events.SCENE_DELETED, self._on_scene_event)
        bus.subscribe(Events.TAGS_UPDATED, self._on_scene_event)

    def _on_scene_event(self, event_type, **kwargs):
        """处理场景相关事件"""
        try:
            self.after(10, self.refresh)
        except tk.TclError:
            pass  # Widget 已销毁
        
    def setup_ui(self):
        # Layout: Left side = Unassigned Scenes List, Right side = Beat Sheet
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel: Scenes List
        self.left_frame = ttk.LabelFrame(self.paned, text="可用场景")
        self.paned.add(self.left_frame, weight=1)
        
        self.scene_list = tk.Listbox(self.left_frame, selectmode=tk.SINGLE, bg="#FAFAFA")
        self.scene_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.scene_list.bind("<Button-1>", self.on_scene_click)
        self.scene_list.bind("<B1-Motion>", self.on_scene_drag)
        self.scene_list.bind("<ButtonRelease-1>", self.on_scene_release)
        
        # Right Panel: Beat Sheet (Scrollable Canvas)
        self.right_frame = ttk.LabelFrame(self.paned, text="节拍表 (Beat Sheet)")
        self.paned.add(self.right_frame, weight=3)
        
        self.canvas = ZoomableCanvas(self.right_frame, bg="#FFFFFF")
        vsb = ttk.Scrollbar(self.right_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        self.drag_data = {"item": None, "scene_idx": None, "ghost": None}
        
        # Beat logic
        self.beat_slots = [] # list of dict {name, x, y, w, h, scenes[]}
        
        self.canvas.bind("<Configure>", self.refresh)

        # Interface compatibility for OutlineViewManager
        self.node_items = {}
        self.selected_node_ids = set()

    def set_data(self, root_node):
        """Interface method - BeatSheet doesn't use the outline tree directly but needs to accept it."""
        self.refresh()

    def set_scene_counts(self, counts):
        """
        设置场景计数（接口方法）。

        Args:
            counts: 场景计数字典 {outline_uid: count}
        """
        self.scene_counts = counts or {}
        # 可以在刷新时使用这些计数

    def set_tag_filter(self, tags):
        """
        设置标签过滤器。

        Args:
            tags: 要过滤的标签列表或集合
        """
        if not tags:
            self.tag_filter = None
        elif isinstance(tags, (list, set, tuple)):
            self.tag_filter = set(tags)
        else:
            self.tag_filter = {tags}
        self.refresh()

    def select_node(self, node_id, add=False):
        """
        选中与指定大纲节点关联的场景。

        Args:
            node_id: 大纲节点的 UID
            add: 是否添加到现有选择
        """
        if not add:
            self.deselect_all()

        # 根据 outline_ref_id 找到关联的场景
        scenes = self.project_manager.get_scenes()
        for idx, scene in enumerate(scenes):
            if scene.get("outline_ref_id") == node_id:
                self.selected_node_ids.add(node_id)
                # 在场景列表中高亮
                try:
                    self.scene_list.selection_set(idx)
                    self.scene_list.see(idx)
                except tk.TclError:
                    pass

    def deselect_all(self):
        """取消所有选中"""
        self.selected_node_ids.clear()
        try:
            self.scene_list.selection_clear(0, tk.END)
        except tk.TclError:
            pass

    def apply_theme(self, theme_manager):
        """Interface method."""
        self.theme_manager = theme_manager
        self.refresh()

    def refresh(self, event=None):
        self.canvas.delete("all")
        self.scene_list.delete(0, tk.END)
        self.beat_slots.clear()
        
        scenes = self.project_manager.get_scenes()
        if not scenes: return
        
        # 1. Populate Scene List (Unassigned or All?)
        # Let's show All, but highlight assigned ones differently? 
        # Or better: Show scenes that are NOT assigned to a specific beat property.
        # But we don't have a specific "beat" property in scene model yet.
        # We can reuse "tags" or add a new field. Let's assume we use a tag "Beat:Name".
        
        unassigned_indices = []
        beat_map = {b[0]: [] for b in self.beats} # Beat Name -> [scene objects]
        
        for i, scene in enumerate(scenes):
            assigned = False
            tags = scene.get("tags", [])
            for tag in tags:
                if tag.startswith("Beat:"):
                    beat_name = tag[5:]
                    if beat_name in beat_map:
                        beat_map[beat_name].append(scene)
                        assigned = True
                        break
            
            self.scene_list.insert(tk.END, f"{i+1}. {scene.get('name')}")
            if assigned:
                self.scene_list.itemconfig(tk.END, {'fg': '#888'}) # Gray out assigned
        
        # 2. Draw Beats
        w = self.canvas.winfo_width()
        if w < 100: w = 600
        
        slot_height = 120
        padding = 10
        current_y = padding
        
        for b_name, b_cn, b_desc, pct in self.beats:
            # Draw Slot
            bg_color = "#F5F5F5"
            if self.theme_manager and self.theme_manager.current_theme == "Dark":
                bg_color = "#333"
            
            # Header
            self.canvas.create_rectangle(10, current_y, w-10, current_y + 30, fill="#DDD", outline="#CCC")
            self.canvas.create_text(20, current_y + 15, text=f"{b_name} ({b_cn})", anchor="w", font=("Arial", 10, "bold"))
            self.canvas.create_text(w-20, current_y + 15, text=b_desc, anchor="e", font=("Arial", 9, "italic"), fill="#666")
            
            # Content Area
            content_h = max(80, len(beat_map[b_name]) * 30 + 20)
            self.canvas.create_rectangle(10, current_y + 30, w-10, current_y + 30 + content_h, fill=bg_color, outline="#CCC", tags=f"slot_{b_name}")
            
            # Store slot info for drop detection
            self.beat_slots.append({
                "name": b_name,
                "y": current_y + 30,
                "h": content_h,
                "x": 10,
                "w": w-20
            })
            
            # Draw assigned scenes
            scene_y = current_y + 40
            for s in beat_map[b_name]:
                self.canvas.create_rectangle(20, scene_y, w-20, scene_y+25, fill="white", outline="#DDD")
                self.canvas.create_text(30, scene_y+12, text=s.get("name"), anchor="w", font=("Arial", 9))
                scene_y += 30
            
            current_y += 30 + content_h + padding
            
        self.canvas.configure(scrollregion=(0, 0, w, current_y))

    def on_scene_click(self, event):
        idx = self.scene_list.nearest(event.y)
        if idx >= 0:
            self.drag_data["scene_idx"] = idx
            
    def on_scene_drag(self, event):
        if self.drag_data["scene_idx"] is None: return
        
        # Create ghost if not exists
        if not self.drag_data["ghost"]:
            # We need a Toplevel or just a label following mouse?
            # Canvas drag is easier if within canvas, but we are dragging from Listbox to Canvas.
            # Cross-widget drag is tricky in Tkinter without DND lib.
            # Simpler: Just rely on mouse release logic, changing cursor.
            self.configure(cursor="hand2")
            
    def on_scene_release(self, event):
        self.configure(cursor="")
        if self.drag_data["scene_idx"] is None: return
        
        # Check where we dropped relative to canvas
        # Coordinates need to be mapped to canvas
        
        # Global mouse pos
        x_root, y_root = event.x_root, event.y_root
        
        # Canvas pos
        c_x = x_root - self.canvas.winfo_rootx()
        c_y = y_root - self.canvas.winfo_rooty()
        
        # Account for scroll
        c_y = self.canvas.canvasy(c_y)
        
        # Check slots
        dropped_beat = None
        for slot in self.beat_slots:
            if slot["y"] <= c_y <= slot["y"] + slot["h"]:
                dropped_beat = slot["name"]
                break
        
        if dropped_beat:
            self._assign_scene_to_beat(self.drag_data["scene_idx"], dropped_beat)
            
        self.drag_data["scene_idx"] = None

    def _assign_scene_to_beat(self, scene_idx, beat_name):
        scenes = self.project_manager.get_scenes()
        if 0 <= scene_idx < len(scenes):
            scene = scenes[scene_idx]
            tags = scene.get("tags", [])
            
            # Remove existing beat tags
            new_tags = [t for t in tags if not t.startswith("Beat:")]
            new_tags.append(f"Beat:{beat_name}")
            
            # Update
            if set(new_tags) != set(tags):
                new_data = dict(scene)
                new_data["tags"] = new_tags
                cmd = EditSceneCommand(self.project_manager, scene_idx, scene, new_data, f"Assign Beat {beat_name}")
                self.command_executor(cmd)
                self.refresh()
