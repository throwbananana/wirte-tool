# Outline Views Package
# 大纲可视化视图模块

from .base_view import BaseOutlineView
from .horizontal_tree import HorizontalTreeView
from .vertical_tree import VerticalTreeView
from .radial_view import RadialView
from .table_view import TableView
from .fishbone_view import FishboneView
from .flat_draft_view import FlatDraftView

# 视图类型映射
VIEW_TYPES = {
    "horizontal": HorizontalTreeView,
    "vertical": VerticalTreeView,
    "radial": RadialView,
    "table": TableView,
    "fishbone": FishboneView,
    "flat_draft": FlatDraftView,
}

VIEW_TYPE_NAMES = {
    "horizontal": "水平思维导图",
    "vertical": "垂直树形图",
    "radial": "放射发散图",
    "table": "大纲表格",
    "fishbone": "鱼骨图 (因果分析)",
    "flat_draft": "平铺叙事草稿",
}

__all__ = [
    'BaseOutlineView',
    'HorizontalTreeView',
    'VerticalTreeView',
    'RadialView',
    'TableView',
    'FishboneView',
    'FlatDraftView',
    'VIEW_TYPES',
    'VIEW_TYPE_NAMES',
]
