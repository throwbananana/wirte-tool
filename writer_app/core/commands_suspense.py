"""
悬疑相关命令 - 为保持向后兼容性重新导出

注意: 所有时间轴命令已统一到 commands.py 中
此文件仅为保持旧代码导入兼容性，新代码请直接从 commands.py 导入
"""

# 从 commands.py 重新导出时间轴命令（保持向后兼容）
from writer_app.core.commands import (
    AddTimelineEventCommand,
    EditTimelineEventCommand,
    DeleteTimelineEventCommand
)

# 为使用旧参数名的代码提供适配器
class AddTimelineEventCommandLegacy:
    """
    旧版兼容适配器 - 将 timeline_type 参数转换为 track_type

    旧用法: AddTimelineEventCommand(pm, "truth_events", data)
    新用法: AddTimelineEventCommand(pm, "truth", data, desc)
    """
    def __new__(cls, project_manager, timeline_type, event_data, description=None):
        # 转换参数名
        track_type = "truth" if timeline_type == "truth_events" else "lie"
        desc = description or f"添加{'真相' if track_type == 'truth' else '谎言'}事件"
        return AddTimelineEventCommand(project_manager, track_type, event_data, desc)


# 导出所有命令
__all__ = [
    'AddTimelineEventCommand',
    'EditTimelineEventCommand',
    'DeleteTimelineEventCommand',
    'AddTimelineEventCommandLegacy'
]
