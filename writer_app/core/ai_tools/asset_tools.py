"""
资源工具 - 用于创建资源占位符

包含工具:
    - create_asset_placeholder: 创建资源占位图
"""

from typing import Dict, Any, Callable
import random
import os
from pathlib import Path
from . import AITool, ToolResult, ToolParameter, AIToolRegistry

from writer_app.core.commands import (
    EditSceneCommand,
    EditCharacterCommand
)

# 尝试导入Pillow
try:
    from PIL import Image, ImageDraw
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


class CreateAssetPlaceholderTool(AITool):
    """创建资源占位图工具。"""

    name = "create_asset_placeholder"
    description = "为角色或场景生成占位图片。需要安装Pillow库。"
    parameters = [
        ToolParameter("type", "资源类型：character（角色立绘）或background（背景图）", "string", required=True),
        ToolParameter("target_name", "目标名称（角色名或场景名）", "string", required=True),
    ]

    def execute(
        self,
        project_manager,
        command_executor: Callable,
        params: Dict[str, Any]
    ) -> ToolResult:
        if not HAS_PILLOW:
            return ToolResult.error("无法生成图片: 未安装 Pillow 库。请运行: pip install Pillow")

        target_type = params.get("type", "character")
        target_name = params.get("target_name", "")

        if not target_name:
            return ToolResult.error("必须指定目标名称")

        # 验证类型
        if target_type not in ["character", "background"]:
            target_type = "character"

        # 生成随机颜色
        color = (
            random.randint(50, 200),
            random.randint(50, 200),
            random.randint(50, 200)
        )

        # 确定图片尺寸
        if target_type == "character":
            size = (400, 600)
        else:
            size = (800, 450)

        # 创建资源目录
        assets_dir = Path(os.getcwd()) / "writer_data" / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        filename = f"{target_name}_{target_type}_{random.randint(1000, 9999)}.png"
        filepath = assets_dir / filename

        # 生成图片
        try:
            self._generate_placeholder_image(str(filepath), target_name, color, size)
        except Exception as e:
            return ToolResult.error(f"生成图片失败: {e}")

        # 绑定到数据
        if target_type == "character":
            chars = project_manager.get_characters()
            found = False

            for i, c in enumerate(chars):
                if c.get("name") == target_name:
                    old_data = c.copy()
                    new_data = c.copy()
                    new_data["image_path"] = str(filepath)

                    cmd = EditCharacterCommand(
                        project_manager, i, old_data, new_data, "AI生成立绘"
                    )
                    success = command_executor(cmd)

                    if success:
                        found = True
                        return ToolResult.success(
                            f"已生成并绑定立绘到角色: {target_name}",
                            data={"path": str(filepath)}
                        )
                    break

            if not found:
                return ToolResult.success(
                    f"已生成图片但找不到角色: {target_name}",
                    data={"path": str(filepath)}
                )

        elif target_type == "background":
            scenes = project_manager.get_scenes()
            found = False

            for i, s in enumerate(scenes):
                if s.get("name") == target_name:
                    old_data = s.copy()
                    new_data = s.copy()
                    new_data["image_path"] = str(filepath)

                    cmd = EditSceneCommand(
                        project_manager, i, old_data, new_data, "AI生成背景"
                    )
                    success = command_executor(cmd)

                    if success:
                        found = True
                        return ToolResult.success(
                            f"已生成并绑定背景到场景: {target_name}",
                            data={"path": str(filepath)}
                        )
                    break

            if not found:
                return ToolResult.success(
                    f"已生成图片但找不到场景: {target_name}",
                    data={"path": str(filepath)}
                )

        return ToolResult.success(
            f"已生成占位图: {filename}",
            data={"path": str(filepath)}
        )

    def _generate_placeholder_image(
        self,
        path: str,
        text: str,
        color: tuple,
        size: tuple
    ) -> None:
        """生成占位图片。"""
        img = Image.new('RGB', size, color=color)
        d = ImageDraw.Draw(img)

        # 绘制边框
        d.rectangle(
            [0, 0, size[0] - 1, size[1] - 1],
            outline=(255, 255, 255),
            width=5
        )

        # 绘制文字（居中）
        display_text = text[0] if text else "?"
        try:
            # 尝试使用较大字体
            d.text(
                (size[0] / 2, size[1] / 2),
                display_text,
                fill=(255, 255, 255),
                anchor="mm",
                font_size=60
            )
        except TypeError:
            # 旧版Pillow不支持font_size参数
            d.text(
                (size[0] / 2, size[1] / 2),
                display_text,
                fill=(255, 255, 255),
                anchor="mm"
            )

        img.save(path)


def register_tools(registry: 'AIToolRegistry') -> None:
    """注册所有资源工具。"""
    registry.register(CreateAssetPlaceholderTool())
