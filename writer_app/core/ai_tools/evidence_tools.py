"""
证据工具 - 用于添加线索和连接线索

包含工具:
    - add_clue: 添加线索/证据节点
    - connect_clues: 连接两个线索节点
"""

from typing import Dict, Any, Callable, Optional
import random
from . import AITool, ToolResult, ToolParameter, AIToolRegistry

from writer_app.core.commands import (
    AddEvidenceNodeCommand,
    AddEvidenceLinkCommand
)


class AddClueTool(AITool):
    """添加线索/证据节点工具。"""

    name = "add_clue"
    description = "在证据板上添加新的线索节点。支持类型：clue（线索）、character（人物）、location（地点）、event（事件）、question（疑问）。"
    parameters = [
        ToolParameter("name", "线索名称", "string", required=True),
        ToolParameter("description", "线索描述", "string", required=False, default=""),
        ToolParameter("type", "节点类型：clue/character/location/event/question", "string", required=False, default="clue"),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        name = params.get("name", "")
        desc = params.get("description", "")
        ctype = params.get("type", "clue")

        if not name:
            return ToolResult.error("线索名称不能为空")

        # 验证类型
        valid_types = ["clue", "character", "location", "event", "question"]
        if ctype not in valid_types:
            ctype = "clue"

        node_data = {
            "name": name,
            "description": desc,
            "type": ctype
        }

        # 随机位置
        pos = [random.randint(100, 500), random.randint(100, 400)]

        cmd = AddEvidenceNodeCommand(project_manager, node_data, pos)
        success = command_executor(cmd)

        if success:
            return ToolResult.success(f"已添加{ctype}节点: {name}")
        else:
            return ToolResult.error("添加线索失败")


class ConnectCluesTool(AITool):
    """连接两个线索节点工具。"""

    name = "connect_clues"
    description = "在证据板上连接两个已有的线索节点。支持连接类型：relates_to（相关）、suspects（怀疑）、confirms（确认）、contradicts（矛盾）、caused_by（因果）。"
    parameters = [
        ToolParameter("source", "起点节点名称", "string", required=True),
        ToolParameter("target", "终点节点名称", "string", required=True),
        ToolParameter("label", "连接标签/描述", "string", required=False, default=""),
        ToolParameter("link_type", "连接类型：relates_to/suspects/confirms/contradicts/caused_by", "string", required=False, default="relates_to"),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        src_name = params.get("source", "")
        tgt_name = params.get("target", "")
        label = params.get("label", "")
        link_type = params.get("link_type", "relates_to")

        if not src_name or not tgt_name:
            return ToolResult.error("必须指定起点和终点节点")

        # 验证连接类型
        valid_types = ["relates_to", "suspects", "confirms", "contradicts", "caused_by"]
        if link_type not in valid_types:
            link_type = "relates_to"

        # 查找节点UID
        src_uid = self._find_evidence_uid_by_name(project_manager, src_name)
        tgt_uid = self._find_evidence_uid_by_name(project_manager, tgt_name)

        if not src_uid:
            return ToolResult.error(f"找不到起点节点: {src_name}")
        if not tgt_uid:
            return ToolResult.error(f"找不到终点节点: {tgt_name}")

        link_data = {
            "source": src_uid,
            "target": tgt_uid,
            "label": label,
            "type": link_type
        }

        cmd = AddEvidenceLinkCommand(project_manager, link_data)
        success = command_executor(cmd)

        if success:
            return ToolResult.success(f"已连接线索: {src_name} -> {tgt_name}")
        else:
            return ToolResult.error("连接线索失败")

    def _find_evidence_uid_by_name(self, project_manager, name: str) -> Optional[str]:
        """通过名称查找证据节点UID。"""
        rels = project_manager.get_relationships()

        # 检查自定义节点
        for node in rels.get("nodes", []):
            if node.get("name") == name:
                return node.get("uid")

        # 检查角色（角色也可以作为证据板节点）
        for char in project_manager.get_characters():
            if char.get("name") == name:
                return char.get("uid") or char.get("name")

        return None


def register_tools(registry: 'AIToolRegistry') -> None:
    """注册所有证据工具。"""
    registry.register(AddClueTool())
    registry.register(ConnectCluesTool())
