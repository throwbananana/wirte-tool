import tkinter as tk
from tkinter import messagebox
from writer_app.ui.components.zoomable_canvas import ZoomableCanvas
from writer_app.core.commands import MoveSceneCommand, EditSceneCommand
from writer_app.core.event_bus import get_event_bus, Events
import math
import logging

logger = logging.getLogger(__name__)


class CorkboardView(ZoomableCanvas):
    """
    Corkboard view for visualizing scenes as index cards.
    Supports Drag & Drop reordering.

    Features:
    - 场景以索引卡片形式展示
    - 支持拖放重排场景顺序
    - 双击跳转到场景编辑器
    - 卡片颜色反映场景状态
    - 与 EventBus 集成实现实时更新
    """
    def __init__(self, parent, project_manager, command_executor,
                 on_node_select=None, on_ai_suggest_branch=None,
                 on_generate_scene=None, on_set_tags=None,
                 on_jump_to_scene=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.project_manager = project_manager
        self.command_executor = command_executor

        # 回调函数
        self.on_node_select = on_node_select
        self.on_jump_to_scene = on_jump_to_scene
        
        # Card settings
        self.card_width = 200
        self.card_height = 140
        self.padding_x = 20
        self.padding_y = 20
        self.cols = 4 # Fixed columns for now, or auto-flow
        
        self.cards = {} # item_id -> scene_index
        self.scene_map = {} # scene_index -> item_ids (group)
        
        self.drag_data = {"item": None, "x": 0, "y": 0, "index": None}
        self.drop_target = None
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Double-1>", self.on_double_click)
        self.bind("<Configure>", self.on_resize)
        
        # Compatibility/Interface attributes expected by OutlineViewManager
        self.root_node = None  # Not strictly used for flat scene list, but good for interface
        self.selected_node_ids = set()
        self.node_items = {}
        self.tag_filter = None
        self.theme_manager = None
        self.scene_counts = {}  # 场景计数映射

        # 订阅事件
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅 EventBus 事件"""
        bus = get_event_bus()
        bus.subscribe(Events.SCENE_ADDED, self._on_scene_event)
        bus.subscribe(Events.SCENE_UPDATED, self._on_scene_event)
        bus.subscribe(Events.SCENE_DELETED, self._on_scene_event)
        bus.subscribe(Events.SCENE_MOVED, self._on_scene_event)

    def _on_scene_event(self, event_type, **kwargs):
        """处理场景相关事件"""
        try:
            self.after(10, self.refresh)
        except tk.TclError:
            pass  # Widget 已销毁 

    def set_data(self, root_node):
        """Interface method, but we pull scenes directly."""
        self.refresh()

    def set_scene_counts(self, counts):
        """设置场景计数映射：outline_uid -> count"""
        self.scene_counts = counts or {}

    def set_tag_filter(self, tags):
        self.tag_filter = tags
        self.refresh()
        
    def apply_theme(self, theme_manager):
        self.theme_manager = theme_manager
        if theme_manager.current_theme == "Dark":
            self.configure(bg="#2D2D2D")
        else:
            self.configure(bg="#F0E68C") # Khaki/Cork color
        self.refresh()

    def refresh(self):
        self.delete("all")
        self.cards.clear()
        self.scene_map.clear()
        
        scenes = self.project_manager.get_scenes()
        if not scenes:
            self.create_text(self.winfo_width()/2, self.winfo_height()/2, 
                             text="No Scenes Created", font=("Arial", 14), fill="#555")
            return

        # Calculate grid
        w = self.winfo_width()
        if w < 100: w = 800
        
        # Dynamic columns based on width
        eff_width = self.card_width + self.padding_x
        cols = max(1, int((w - self.padding_x) / eff_width))
        self.cols = cols
        
        current_y = self.padding_y
        current_x = self.padding_x
        
        for i, scene in enumerate(scenes):
            # Check filter (optional implementation)
            # if self.tag_filter and ... 
            
            # Draw Card
            self._draw_card(i, scene, current_x, current_y)
            
            current_x += eff_width
            if (i + 1) % cols == 0:
                current_x = self.padding_x
                current_y += self.card_height + self.padding_y
                
        self.configure(scrollregion=self.bbox("all"))

    def _draw_card(self, index, scene, x, y):
        """Draw a single index card."""
        w, h = self.card_width, self.card_height
        
        # Shadow
        self.create_rectangle(x+3, y+3, x+w+3, y+h+3, fill="rgba(0,0,0,0.2)", outline="", tags="card_bg")
        
        # Card Body
        bg_color = "white"
        status = scene.get("status", "")
        if status == "定稿":
            bg_color = "#E8F5E9" # Green tint
        elif status == "初稿":
            bg_color = "#E3F2FD" # Blue tint
            
        card_id = self.create_rectangle(x, y, x+w, y+h, fill=bg_color, outline="#888", width=1, tags=("card", f"scene_{index}"))
        
        # Pin
        self.create_oval(x+w/2-5, y+5, x+w/2+5, y+15, fill="red", outline="#333", tags=("card", f"scene_{index}"))
        
        # Title
        title = scene.get("name", f"Scene {index+1}")
        if len(title) > 20: title = title[:18] + "..."
        self.create_text(x+10, y+30, text=title, anchor="w", font=("Arial", 10, "bold"), width=w-20, tags=("card", f"scene_{index}"))
        
        # Synopsis/Content Preview
        content = scene.get("content", "")
        preview = content[:80].replace("\n", " ") + "..." if len(content) > 80 else content
        self.create_text(x+10, y+55, text=preview, anchor="nw", font=("Arial", 8), width=w-20, fill="#555", tags=("card", f"scene_{index}"))
        
        # Metadata
        meta = f"Chars: {len(scene.get('characters', []))} | Loc: {scene.get('location', '-')}"
        self.create_text(x+10, y+h-15, text=meta, anchor="w", font=("Arial", 7), fill="#888", tags=("card", f"scene_{index}"))
        
        self.cards[card_id] = index
        self.scene_map[index] = [card_id] # simplified, tracking mainly bg

    def on_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        item = self.find_closest(x, y)[0]
        tags = self.gettags(item)
        
        scene_idx = None
        for tag in tags:
            if tag.startswith("scene_"):
                scene_idx = int(tag.split("_")[1])
                break
        
        if scene_idx is not None:
            self.drag_data["index"] = scene_idx
            self.drag_data["x"] = x
            self.drag_data["y"] = y
            self.drag_data["start_item_pos"] = self.coords(item) # approximation
            # Lift all items related to this scene?
            # Ideally, we move the visual representation.
            # For simplicity, we just drag a ghost rect.
            self.drag_data["ghost"] = self.create_rectangle(x, y, x+self.card_width, y+self.card_height, 
                                                            fill="", outline="blue", width=2, dash=(4,4))

    def on_drag(self, event):
        if self.drag_data["index"] is None:
            return
            
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        dx = x - self.drag_data["x"]
        dy = y - self.drag_data["y"]
        
        self.move(self.drag_data["ghost"], dx, dy)
        self.drag_data["x"] = x
        self.drag_data["y"] = y
        
        # Highlight drop target
        # Calculate grid index based on x, y
        col = int((x - self.padding_x) / (self.card_width + self.padding_x))
        row = int((y - self.padding_y) / (self.card_height + self.padding_y))
        
        target_idx = row * self.cols + col
        scenes = self.project_manager.get_scenes()
        if 0 <= target_idx < len(scenes):
            self.drop_target = target_idx
        else:
            self.drop_target = None

    def on_release(self, event):
        if self.drag_data.get("ghost"):
            self.delete(self.drag_data["ghost"])
            
        if self.drag_data["index"] is not None and self.drop_target is not None:
            if self.drag_data["index"] != self.drop_target:
                # Reorder
                from_idx = self.drag_data["index"]
                to_idx = self.drop_target
                
                cmd = MoveSceneCommand(self.project_manager, from_idx, to_idx)
                if self.command_executor(cmd):
                    self.refresh()
        
        self.drag_data = {"item": None, "x": 0, "y": 0, "index": None}
        self.drop_target = None

    def on_double_click(self, event):
        """
        双击卡片跳转到场景编辑器。
        """
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        items = self.find_overlapping(x - 5, y - 5, x + 5, y + 5)

        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith("scene_"):
                    try:
                        idx = int(tag.split("_")[1])
                        logger.debug(f"Double clicked scene {idx}")

                        # 使用回调跳转到场景
                        if self.on_jump_to_scene:
                            self.on_jump_to_scene(idx)
                        else:
                            # 发布事件作为备用
                            bus = get_event_bus()
                            bus.publish("scene_jump_requested", scene_idx=idx)
                            messagebox.showinfo("场景详情", f"跳转到场景 {idx + 1}")
                        return
                    except (ValueError, IndexError) as e:
                        logger.warning(f"解析场景索引失败: {tag}, 错误: {e}")

    def on_resize(self, event):
        self.refresh()

    def select_node(self, node_id, add=False):
        """
        选中与指定大纲节点关联的场景卡片。

        Args:
            node_id: 大纲节点的 UID
            add: 是否添加到现有选择（多选模式）
        """
        if not add:
            self.deselect_all()

        # 根据 outline_ref_id 找到关联的场景
        scenes = self.project_manager.get_scenes()
        for idx, scene in enumerate(scenes):
            if scene.get("outline_ref_id") == node_id:
                self.selected_node_ids.add(node_id)
                self._highlight_card(idx, True)

                # 滚动到可见区域
                if idx in self.scene_map:
                    card_items = self.scene_map[idx]
                    if card_items:
                        bbox = self.bbox(card_items[0])
                        if bbox:
                            self.see(bbox[0], bbox[1])

    def deselect_all(self):
        """取消所有选中的卡片"""
        # 移除所有高亮
        for idx in list(self.scene_map.keys()):
            self._highlight_card(idx, False)
        self.selected_node_ids.clear()

    def _highlight_card(self, scene_idx, highlight):
        """
        高亮或取消高亮指定索引的卡片。

        Args:
            scene_idx: 场景索引
            highlight: True 高亮，False 取消高亮
        """
        if scene_idx not in self.scene_map:
            return

        card_items = self.scene_map[scene_idx]
        if not card_items:
            return

        card_id = card_items[0]  # 主卡片矩形
        try:
            if highlight:
                self.itemconfig(card_id, outline="#2196F3", width=3)
            else:
                self.itemconfig(card_id, outline="#888", width=1)
        except tk.TclError as e:
            logger.warning(f"高亮卡片时出错: {e}")

    def see(self, x, y):
        """滚动画布使指定坐标可见"""
        try:
            # 获取当前可见区域
            x1, y1, x2, y2 = self.bbox("all") or (0, 0, 0, 0)
            canvas_width = self.winfo_width()
            canvas_height = self.winfo_height()

            # 计算滚动位置
            if x2 > canvas_width:
                scroll_x = max(0, min(1, (x - canvas_width / 2) / x2))
                self.xview_moveto(scroll_x)

            if y2 > canvas_height:
                scroll_y = max(0, min(1, (y - canvas_height / 2) / y2))
                self.yview_moveto(scroll_y)
        except tk.TclError:
            pass

    def destroy(self):
        """清理资源"""
        # 取消事件订阅
        try:
            bus = get_event_bus()
            bus.unsubscribe(Events.SCENE_ADDED, self._on_scene_event)
            bus.unsubscribe(Events.SCENE_UPDATED, self._on_scene_event)
            bus.unsubscribe(Events.SCENE_DELETED, self._on_scene_event)
            bus.unsubscribe(Events.SCENE_MOVED, self._on_scene_event)
        except Exception as e:
            logger.warning(f"取消事件订阅时出错: {e}")

        super().destroy()
