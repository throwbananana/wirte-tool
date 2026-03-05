"""
大纲视图管理器
OutlineViewManager - 管理大纲可视化视图的切换和生命周期
"""
import tkinter as tk
from typing import Optional, Dict, Callable, Any


class OutlineViewManager:
    """
    大纲视图管理器
    负责管理不同大纲视图的切换、数据同步和生命周期
    """

    # 视图类型映射
    VIEW_TYPES = {
        "horizontal": "水平思维导图",
        "vertical": "垂直树形图",
        "radial": "放射发散图",
        "table": "大纲表格",
        "corkboard": "卡片板视图",
        "grid": "电子表格视图",
        "beats": "节拍表视图",
        "fishbone": "鱼骨图 (因果分析)",
        "flat_draft": "平铺叙事草稿",
    }

    # 视图类型到类的映射（延迟加载）
    _view_classes = {}

    def __init__(self, parent: tk.Widget, project_manager, command_executor: Callable,
                 on_node_select: Callable = None, on_ai_suggest_branch: Callable = None,
                 on_generate_scene: Callable = None, on_set_tags: Callable = None):
        """
        初始化视图管理器

        Args:
            parent: 父容器widget
            project_manager: 项目管理器实例
            command_executor: 命令执行函数
            on_node_select: 节点选中回调
            on_ai_suggest_branch: AI建议分支回调
            on_generate_scene: 生成场景回调
            on_set_tags: 设置标签回调
        """
        self.parent = parent
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.on_node_select = on_node_select
        self.on_ai_suggest_branch = on_ai_suggest_branch
        self.on_generate_scene = on_generate_scene
        self.on_set_tags = on_set_tags

        # 当前视图
        self.current_view = None
        self.current_view_type = None

        # 主题管理器
        self.theme_manager = None

        # 滚动条
        self.h_scrollbar = None
        self.v_scrollbar = None

        # 视图容器
        self.view_frame = tk.Frame(parent)
        self.view_frame.pack(fill=tk.BOTH, expand=True)

        # 创建滚动条
        self._setup_scrollbars()

    def _setup_scrollbars(self):
        """设置滚动条"""
        self.h_scrollbar = tk.Scrollbar(self.view_frame, orient=tk.HORIZONTAL)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.v_scrollbar = tk.Scrollbar(self.view_frame, orient=tk.VERTICAL)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    @classmethod
    def _get_view_class(cls, view_type: str):
        """
        获取视图类（延迟加载）

        Args:
            view_type: 视图类型标识符

        Returns:
            视图类
        """
        if view_type not in cls._view_classes:
            if view_type == "horizontal":
                from writer_app.ui.outline_views.horizontal_tree import HorizontalTreeView
                cls._view_classes["horizontal"] = HorizontalTreeView
            elif view_type == "vertical":
                from writer_app.ui.outline_views.vertical_tree import VerticalTreeView
                cls._view_classes["vertical"] = VerticalTreeView
            elif view_type == "radial":
                from writer_app.ui.outline_views.radial_view import RadialView
                cls._view_classes["radial"] = RadialView
            elif view_type == "table":
                from writer_app.ui.outline_views.table_view import TableView
                cls._view_classes["table"] = TableView
            elif view_type == "corkboard":
                from writer_app.ui.outline_views.corkboard_view import CorkboardView
                cls._view_classes["corkboard"] = CorkboardView
            elif view_type == "grid":
                from writer_app.ui.outline_views.grid_view import GridView
                cls._view_classes["grid"] = GridView
            elif view_type == "beats":
                from writer_app.ui.beat_sheet import BeatSheetView
                cls._view_classes["beats"] = BeatSheetView
            elif view_type == "fishbone":
                from writer_app.ui.outline_views.fishbone_view import FishboneView
                cls._view_classes["fishbone"] = FishboneView
            elif view_type == "flat_draft":
                from writer_app.ui.outline_views.flat_draft_view import FlatDraftView
                cls._view_classes["flat_draft"] = FlatDraftView
            else:
                raise ValueError(f"Unknown view type: {view_type}")

        return cls._view_classes[view_type]

    def switch_view(self, view_type: str) -> bool:
        """
        切换到指定视图类型

        Args:
            view_type: 视图类型标识符 (horizontal, vertical, radial, table)

        Returns:
            是否切换成功
        """
        if view_type == self.current_view_type:
            return True

        if view_type not in self.VIEW_TYPES:
            return False

        # 保存当前状态
        selected_ids = set()
        root_node = None
        scene_counts = {}
        tag_filter = None

        if self.current_view:
            selected_ids = set(self.current_view.selected_node_ids)
            root_node = self.current_view.root_node
            scene_counts = getattr(self.current_view, 'scene_counts', {})
            tag_filter = getattr(self.current_view, 'tag_filter', None)
            self.current_view.destroy()

        # 获取视图类并创建新视图
        try:
            view_class = self._get_view_class(view_type)
        except (ImportError, ValueError) as e:
            print(f"Failed to load view class for {view_type}: {e}")
            return False

        self.current_view = view_class(
            self.view_frame,
            self.project_manager,
            self.command_executor,
            on_node_select=self.on_node_select,
            on_ai_suggest_branch=self.on_ai_suggest_branch,
            on_generate_scene=self.on_generate_scene,
            on_set_tags=self.on_set_tags,
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set
        )
        self.current_view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 配置滚动条
        self.h_scrollbar.config(command=self.current_view.xview)
        self.v_scrollbar.config(command=self.current_view.yview)

        # 应用主题
        if self.theme_manager:
            self.current_view.apply_theme(self.theme_manager)

        # 恢复数据
        if root_node:
            self.current_view.set_scene_counts(scene_counts)
            self.current_view.set_tag_filter(tag_filter)
            self.current_view.set_data(root_node)

            # 恢复选中状态
            for node_id in selected_ids:
                if node_id in self.current_view.node_items:
                    self.current_view.select_node(node_id, add=True)

        self.current_view_type = view_type
        return True

    def get_current_view(self):
        """获取当前视图"""
        return self.current_view

    def get_current_view_type(self) -> Optional[str]:
        """获取当前视图类型"""
        return self.current_view_type

    def get_view_type_name(self, view_type: str) -> str:
        """获取视图类型的显示名称"""
        return self.VIEW_TYPES.get(view_type, view_type)

    def get_available_view_types(self) -> Dict[str, str]:
        """获取所有可用的视图类型"""
        return self.VIEW_TYPES.copy()

    def set_data(self, root_node):
        """设置数据"""
        if self.current_view:
            self.current_view.set_data(root_node)

    def refresh(self):
        """刷新当前视图"""
        if self.current_view:
            self.current_view.refresh()

    def set_scene_counts(self, counts: Dict[str, int]):
        """设置场景计数"""
        if self.current_view:
            self.current_view.set_scene_counts(counts)

    def set_tag_filter(self, tags):
        """设置标签过滤"""
        if self.current_view:
            self.current_view.set_tag_filter(tags)

    def apply_theme(self, theme_manager):
        """应用主题"""
        self.theme_manager = theme_manager
        if self.current_view:
            self.current_view.apply_theme(theme_manager)

    def select_node(self, node_id: str, add: bool = False):
        """选中节点"""
        if self.current_view:
            self.current_view.select_node(node_id, add)

    def deselect_all(self):
        """取消所有选中"""
        if self.current_view:
            self.current_view.deselect_all()

    @property
    def selected_node_ids(self):
        """获取选中的节点ID集合"""
        if self.current_view:
            return self.current_view.selected_node_ids
        return set()

    @property
    def node_items(self):
        """获取节点项目映射"""
        if self.current_view:
            return self.current_view.node_items
        return {}

    def destroy(self):
        """销毁管理器及其视图"""
        if self.current_view:
            self.current_view.destroy()
        self.view_frame.destroy()
