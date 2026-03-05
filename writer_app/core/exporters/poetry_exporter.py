"""
Poetry Image Exporter - Export poetry scenes as styled image cards.

Provides beautiful image export for poetry projects with various style options.

Usage:
    from writer_app.core.exporters.poetry_exporter import PoetryImageExporter

    PoetryImageExporter.export(project_data, "/path/to/output", style="classical")
"""

import os
from typing import Dict, List, Optional, Any, Tuple
from writer_app.core.exporter import ExportFormat

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


class PoetryStyle:
    """Predefined poetry image styles."""

    CLASSICAL = {
        "name": "classical",
        "display_name": "古典风格",
        "background_color": (245, 235, 220),  # 古宣纸色
        "text_color": (50, 40, 30),
        "accent_color": (139, 69, 19),  # 棕色点缀
        "font_name": "SimSun",  # 宋体
        "title_font_size": 48,
        "body_font_size": 32,
        "line_spacing": 1.8,
        "padding": (80, 100),
        "border": True,
        "border_color": (139, 69, 19),
        "border_width": 3,
        "seal_enabled": True,  # 印章效果
    }

    MODERN = {
        "name": "modern",
        "display_name": "现代简约",
        "background_color": (255, 255, 255),
        "text_color": (40, 40, 40),
        "accent_color": (100, 100, 100),
        "font_name": "Microsoft YaHei",
        "title_font_size": 42,
        "body_font_size": 28,
        "line_spacing": 2.0,
        "padding": (60, 80),
        "border": False,
        "border_color": (200, 200, 200),
        "border_width": 1,
        "seal_enabled": False,
    }

    MINIMALIST = {
        "name": "minimalist",
        "display_name": "极简主义",
        "background_color": (250, 250, 250),
        "text_color": (30, 30, 30),
        "accent_color": (150, 150, 150),
        "font_name": "Microsoft YaHei Light",
        "title_font_size": 36,
        "body_font_size": 24,
        "line_spacing": 2.5,
        "padding": (100, 120),
        "border": False,
        "border_color": (220, 220, 220),
        "border_width": 0,
        "seal_enabled": False,
    }

    DARK = {
        "name": "dark",
        "display_name": "暗色主题",
        "background_color": (30, 30, 35),
        "text_color": (230, 230, 230),
        "accent_color": (180, 150, 100),
        "font_name": "Microsoft YaHei",
        "title_font_size": 42,
        "body_font_size": 28,
        "line_spacing": 2.0,
        "padding": (60, 80),
        "border": True,
        "border_color": (80, 80, 90),
        "border_width": 2,
        "seal_enabled": False,
    }

    STYLES = {
        "classical": CLASSICAL,
        "modern": MODERN,
        "minimalist": MINIMALIST,
        "dark": DARK,
    }

    @classmethod
    def get_style(cls, name: str) -> Dict:
        return cls.STYLES.get(name, cls.CLASSICAL)


class PoetryImageExporter(ExportFormat):
    """Export poetry scenes as beautiful image cards."""

    key = "poetry_image"
    name = "诗歌图卡"
    extension = ".png"
    description = "将诗歌导出为精美的图卡图片"
    supported_types = ["Poetry"]
    priority_for_types = {"Poetry": 100}

    @classmethod
    def export(cls, project_data: Dict, file_path: str, **kwargs) -> bool:
        """
        Export poetry scenes as image cards.

        Args:
            project_data: Project data dict
            file_path: Output file path or directory
            **kwargs:
                style: Style name ("classical", "modern", "minimalist", "dark")
                single_file: If True, create one image per scene
                include_title: Include scene title in image
                width: Image width (default: 800)
                height: Image height (default: auto)

        Returns:
            bool: True if successful
        """
        if not HAS_PILLOW:
            raise ImportError("需要安装 Pillow 库才能导出诗歌图卡: pip install Pillow")

        style_name = kwargs.get("style", "classical")
        style = PoetryStyle.get_style(style_name)
        single_file = kwargs.get("single_file", True)
        include_title = kwargs.get("include_title", True)
        width = kwargs.get("width", 800)

        script = project_data.get("script", {})
        scenes = script.get("scenes", [])

        if not scenes:
            raise ValueError("没有可导出的诗歌内容")

        # Determine output mode
        if single_file:
            # Export each scene as a separate image
            output_dir = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            for i, scene in enumerate(scenes):
                scene_name = scene.get("name", f"poem_{i+1}")
                safe_name = "".join(c for c in scene_name if c.isalnum() or c in "_ -")[:50]
                img_path = os.path.join(output_dir, f"{safe_name}.png")

                cls._export_scene_as_image(scene, img_path, style, include_title, width)
        else:
            # Combine all scenes into one image
            cls._export_all_scenes_as_image(scenes, file_path, style, include_title, width)

        return True

    @classmethod
    def _export_scene_as_image(
        cls,
        scene: Dict,
        file_path: str,
        style: Dict,
        include_title: bool,
        width: int
    ):
        """Export a single scene as an image."""
        content = scene.get("content", "")
        title = scene.get("name", "") if include_title else ""

        lines = [line.strip() for line in content.split("\n") if line.strip()]

        # Calculate dimensions
        padding_x, padding_y = style["padding"]
        line_height = int(style["body_font_size"] * style["line_spacing"])
        title_height = style["title_font_size"] + 40 if title else 0

        content_height = len(lines) * line_height
        height = content_height + title_height + padding_y * 2 + 60

        # Create image
        img = Image.new("RGB", (width, height), style["background_color"])
        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            title_font = ImageFont.truetype(style["font_name"], style["title_font_size"])
            body_font = ImageFont.truetype(style["font_name"], style["body_font_size"])
        except:
            # Fallback to default font
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        # Draw border
        if style["border"]:
            border_w = style["border_width"]
            draw.rectangle(
                [border_w, border_w, width - border_w - 1, height - border_w - 1],
                outline=style["border_color"],
                width=border_w
            )

        y = padding_y

        # Draw title
        if title:
            # Center title
            bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = bbox[2] - bbox[0]
            x = (width - title_width) // 2
            draw.text((x, y), title, font=title_font, fill=style["accent_color"])
            y += title_height

        # Draw content lines (centered)
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=body_font)
            line_width = bbox[2] - bbox[0]
            x = (width - line_width) // 2
            draw.text((x, y), line, font=body_font, fill=style["text_color"])
            y += line_height

        # Add seal effect for classical style
        if style.get("seal_enabled"):
            cls._add_seal(draw, width, height, style)

        img.save(file_path, "PNG", quality=95)

    @classmethod
    def _export_all_scenes_as_image(
        cls,
        scenes: List[Dict],
        file_path: str,
        style: Dict,
        include_title: bool,
        width: int
    ):
        """Export all scenes as a single long image."""
        padding_x, padding_y = style["padding"]
        line_height = int(style["body_font_size"] * style["line_spacing"])
        title_height = style["title_font_size"] + 40

        # Calculate total height
        total_height = padding_y * 2

        scene_data = []
        for scene in scenes:
            content = scene.get("content", "")
            title = scene.get("name", "") if include_title else ""
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            scene_height = len(lines) * line_height
            if title:
                scene_height += title_height

            scene_data.append({
                "title": title,
                "lines": lines,
                "height": scene_height
            })

            total_height += scene_height + 60  # Scene separator

        # Create image
        img = Image.new("RGB", (width, total_height), style["background_color"])
        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            title_font = ImageFont.truetype(style["font_name"], style["title_font_size"])
            body_font = ImageFont.truetype(style["font_name"], style["body_font_size"])
        except:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        # Draw border
        if style["border"]:
            border_w = style["border_width"]
            draw.rectangle(
                [border_w, border_w, width - border_w - 1, total_height - border_w - 1],
                outline=style["border_color"],
                width=border_w
            )

        y = padding_y

        for data in scene_data:
            # Draw title
            if data["title"]:
                bbox = draw.textbbox((0, 0), data["title"], font=title_font)
                title_width = bbox[2] - bbox[0]
                x = (width - title_width) // 2
                draw.text((x, y), data["title"], font=title_font, fill=style["accent_color"])
                y += title_height

            # Draw content lines
            for line in data["lines"]:
                bbox = draw.textbbox((0, 0), line, font=body_font)
                line_width = bbox[2] - bbox[0]
                x = (width - line_width) // 2
                draw.text((x, y), line, font=body_font, fill=style["text_color"])
                y += line_height

            # Scene separator
            y += 60

        img.save(file_path, "PNG", quality=95)

    @classmethod
    def _add_seal(cls, draw: 'ImageDraw', width: int, height: int, style: Dict):
        """Add a decorative seal in the corner."""
        seal_size = 60
        seal_color = (180, 50, 50)  # Red seal color

        # Position: bottom right corner
        x = width - 80
        y = height - 100

        # Draw simple square seal
        draw.rectangle(
            [x, y, x + seal_size, y + seal_size],
            outline=seal_color,
            width=2
        )

        # Draw diagonal lines inside
        draw.line([x + 10, y + 10, x + seal_size - 10, y + seal_size - 10], fill=seal_color, width=2)
        draw.line([x + seal_size - 10, y + 10, x + 10, y + seal_size - 10], fill=seal_color, width=2)

    @classmethod
    def get_type_specific_options(cls, project_type: str) -> Dict[str, Any]:
        """Get Poetry-specific export options."""
        return {
            "styles": list(PoetryStyle.STYLES.keys()),
            "default_style": "classical",
            "supports_single_file": True,
            "supports_batch": True
        }
