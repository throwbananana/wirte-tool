"""
思维导图Canvas - 向后兼容模块
此模块保留用于向后兼容，实际实现已移至 outline_views.horizontal_tree
"""
from writer_app.ui.outline_views.horizontal_tree import HorizontalTreeView

# 保持向后兼容：MindMapCanvas 现在是 HorizontalTreeView 的别名
MindMapCanvas = HorizontalTreeView

__all__ = ['MindMapCanvas', 'HorizontalTreeView']
