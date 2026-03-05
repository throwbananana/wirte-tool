"""
悬浮助手 - 分层立绘系统 (Layered Image System)
采用传统CG和立绘方式，支持多层叠加、表情组合、配饰切换
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import io
import logging

logger = logging.getLogger(__name__)


class LayerType(Enum):
    """图层类型"""
    BACKGROUND = "background"      # 背景层 (场景)
    BASE = "base"                  # 基础身体层
    CLOTHING = "clothing"          # 服装层
    EXPRESSION = "expression"      # 表情层 (面部)
    ACCESSORY = "accessory"        # 配饰层
    EFFECT = "effect"              # 特效层 (光晕等)
    OVERLAY = "overlay"            # 覆盖层 (滤镜效果)


class BlendMode(Enum):
    """混合模式"""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    ADD = "add"


@dataclass
class LayerDefinition:
    """图层定义"""
    layer_id: str
    layer_type: LayerType
    image_path: str
    z_order: int = 0                    # 渲染顺序 (越大越靠前)
    offset_x: int = 0                   # X偏移
    offset_y: int = 0                   # Y偏移
    opacity: float = 1.0                # 透明度 (0-1)
    blend_mode: BlendMode = BlendMode.NORMAL
    visible: bool = True
    tint_color: Optional[Tuple[int, int, int]] = None  # 着色
    tint_strength: float = 0.0          # 着色强度

    # 条件显示
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompositeDefinition:
    """组合立绘定义"""
    composite_id: str
    name: str
    layers: List[str]                   # 图层ID列表
    base_size: Tuple[int, int] = (512, 768)  # 基础尺寸


@dataclass
class ExpressionSet:
    """表情组"""
    expression_id: str
    name: str
    # 各部位的图层ID
    eyes: Optional[str] = None          # 眼睛
    eyebrows: Optional[str] = None      # 眉毛
    mouth: Optional[str] = None         # 嘴巴
    blush: Optional[str] = None         # 腮红
    tears: Optional[str] = None         # 眼泪
    sweat: Optional[str] = None         # 汗滴
    effect: Optional[str] = None        # 表情特效


@dataclass
class PoseDefinition:
    """姿态定义"""
    pose_id: str
    name: str
    base_layer: str                     # 基础身体图层
    compatible_expressions: List[str]   # 兼容的表情组
    compatible_clothing: List[str]      # 兼容的服装


class LayeredImageManager:
    """
    分层立绘管理器

    功能：
    1. 管理多层图像资源
    2. 实时组合渲染
    3. 表情/服装/配饰切换
    4. 缓存优化
    """

    def __init__(self, assets_dir: str = None):
        self.assets_dir = Path(assets_dir) if assets_dir else None

        # 图层库
        self.layers: Dict[str, LayerDefinition] = {}

        # 组合定义库
        self.composites: Dict[str, CompositeDefinition] = {}

        # 表情组库
        self.expressions: Dict[str, ExpressionSet] = {}

        # 姿态库
        self.poses: Dict[str, PoseDefinition] = {}

        # 当前状态
        self.current_pose: Optional[str] = None
        self.current_expression: Optional[str] = None
        self.current_clothing: List[str] = []
        self.current_accessories: List[str] = []

        # 图像缓存
        self._image_cache: Dict[str, Image.Image] = {}
        self._composite_cache: Dict[str, Image.Image] = {}
        self._cache_max_size = 50

        # 加载配置
        self._load_definitions()

    def _load_definitions(self):
        """加载图层定义"""
        if not self.assets_dir:
            self._load_default_definitions()
            return

        config_file = self.assets_dir / "layered_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self._parse_config(config)
            except Exception as e:
                logger.warning(f"加载分层配置失败: {e}")
                self._load_default_definitions()
        else:
            self._load_default_definitions()

    def _load_default_definitions(self):
        """加载默认定义"""
        # 基础姿态
        self.poses = {
            "standing": PoseDefinition(
                pose_id="standing",
                name="站立",
                base_layer="base_standing",
                compatible_expressions=["neutral", "happy", "sad", "angry", "surprised", "shy"],
                compatible_clothing=["casual", "formal", "pajamas"]
            ),
            "sitting": PoseDefinition(
                pose_id="sitting",
                name="坐姿",
                base_layer="base_sitting",
                compatible_expressions=["neutral", "happy", "thinking", "reading"],
                compatible_clothing=["casual", "pajamas"]
            ),
        }

        # 基础表情
        self.expressions = {
            "neutral": ExpressionSet("neutral", "平静", eyes="eyes_normal", mouth="mouth_normal"),
            "happy": ExpressionSet("happy", "开心", eyes="eyes_happy", mouth="mouth_smile", blush="blush_light"),
            "sad": ExpressionSet("sad", "难过", eyes="eyes_sad", mouth="mouth_sad", tears="tears_light"),
            "angry": ExpressionSet("angry", "生气", eyes="eyes_angry", eyebrows="brows_angry", mouth="mouth_angry"),
            "surprised": ExpressionSet("surprised", "惊讶", eyes="eyes_wide", mouth="mouth_open"),
            "shy": ExpressionSet("shy", "害羞", eyes="eyes_shy", mouth="mouth_small", blush="blush_heavy"),
            "thinking": ExpressionSet("thinking", "思考", eyes="eyes_thinking", mouth="mouth_normal"),
            "sleepy": ExpressionSet("sleepy", "困倦", eyes="eyes_sleepy", mouth="mouth_yawn"),
            "love": ExpressionSet("love", "心动", eyes="eyes_heart", mouth="mouth_smile", blush="blush_heavy", effect="hearts"),
            "excited": ExpressionSet("excited", "兴奋", eyes="eyes_sparkle", mouth="mouth_big_smile", effect="sparkles"),
        }

    def _parse_config(self, config: Dict):
        """解析配置文件"""
        # 解析图层
        for layer_data in config.get("layers", []):
            layer = LayerDefinition(
                layer_id=layer_data["id"],
                layer_type=LayerType(layer_data.get("type", "base")),
                image_path=layer_data["path"],
                z_order=layer_data.get("z_order", 0),
                offset_x=layer_data.get("offset_x", 0),
                offset_y=layer_data.get("offset_y", 0),
                opacity=layer_data.get("opacity", 1.0),
                blend_mode=BlendMode(layer_data.get("blend_mode", "normal")),
                visible=layer_data.get("visible", True),
                conditions=layer_data.get("conditions", {})
            )
            self.layers[layer.layer_id] = layer

        # 解析表情组
        for expr_data in config.get("expressions", []):
            expr = ExpressionSet(
                expression_id=expr_data["id"],
                name=expr_data["name"],
                eyes=expr_data.get("eyes"),
                eyebrows=expr_data.get("eyebrows"),
                mouth=expr_data.get("mouth"),
                blush=expr_data.get("blush"),
                tears=expr_data.get("tears"),
                sweat=expr_data.get("sweat"),
                effect=expr_data.get("effect")
            )
            self.expressions[expr.expression_id] = expr

        # 解析姿态
        for pose_data in config.get("poses", []):
            pose = PoseDefinition(
                pose_id=pose_data["id"],
                name=pose_data["name"],
                base_layer=pose_data["base_layer"],
                compatible_expressions=pose_data.get("compatible_expressions", []),
                compatible_clothing=pose_data.get("compatible_clothing", [])
            )
            self.poses[pose.pose_id] = pose

    def _load_image(self, path: str) -> Optional[Image.Image]:
        """加载图像（带缓存）"""
        if path in self._image_cache:
            return self._image_cache[path].copy()

        full_path = self.assets_dir / path if self.assets_dir else Path(path)
        if not full_path.exists():
            logger.debug(f"图像不存在: {full_path}")
            return None

        try:
            img = Image.open(full_path).convert("RGBA")

            # 缓存管理
            if len(self._image_cache) >= self._cache_max_size:
                # 移除最早的缓存
                oldest = next(iter(self._image_cache))
                del self._image_cache[oldest]

            self._image_cache[path] = img.copy()
            return img

        except Exception as e:
            logger.error(f"加载图像失败 {path}: {e}")
            return None

    def set_pose(self, pose_id: str) -> bool:
        """设置姿态"""
        if pose_id not in self.poses:
            logger.warning(f"未知姿态: {pose_id}")
            return False

        self.current_pose = pose_id
        self._invalidate_cache()
        return True

    def set_expression(self, expression_id: str) -> bool:
        """设置表情"""
        if expression_id not in self.expressions:
            logger.warning(f"未知表情: {expression_id}")
            return False

        # 检查兼容性
        if self.current_pose:
            pose = self.poses.get(self.current_pose)
            if pose and expression_id not in pose.compatible_expressions:
                logger.warning(f"表情 {expression_id} 与姿态 {self.current_pose} 不兼容")
                # 不阻止，只警告

        self.current_expression = expression_id
        self._invalidate_cache()
        return True

    def set_clothing(self, clothing_ids: List[str]):
        """设置服装"""
        self.current_clothing = clothing_ids
        self._invalidate_cache()

    def add_accessory(self, accessory_id: str):
        """添加配饰"""
        if accessory_id not in self.current_accessories:
            self.current_accessories.append(accessory_id)
            self._invalidate_cache()

    def remove_accessory(self, accessory_id: str):
        """移除配饰"""
        if accessory_id in self.current_accessories:
            self.current_accessories.remove(accessory_id)
            self._invalidate_cache()

    def _invalidate_cache(self):
        """使组合缓存失效"""
        self._composite_cache.clear()

    def compose(self, context: Dict[str, Any] = None) -> Optional[Image.Image]:
        """
        组合渲染当前立绘

        Args:
            context: 渲染上下文 (用于条件图层)

        Returns:
            合成后的 PIL Image
        """
        context = context or {}

        # 生成缓存键
        cache_key = self._get_cache_key()
        if cache_key in self._composite_cache:
            return self._composite_cache[cache_key].copy()

        # 收集所有需要渲染的图层
        layers_to_render = self._collect_layers(context)

        if not layers_to_render:
            return None

        # 按z_order排序
        layers_to_render.sort(key=lambda x: x.z_order)

        # 创建画布
        base_size = (512, 768)  # 默认尺寸
        canvas = Image.new("RGBA", base_size, (0, 0, 0, 0))

        # 逐层渲染
        for layer in layers_to_render:
            layer_img = self._load_image(layer.image_path)
            if layer_img is None:
                continue

            # 应用变换
            layer_img = self._apply_transforms(layer_img, layer)

            # 混合到画布
            canvas = self._blend_layer(canvas, layer_img, layer)

        # 缓存结果
        self._composite_cache[cache_key] = canvas.copy()

        return canvas

    def _collect_layers(self, context: Dict) -> List[LayerDefinition]:
        """收集需要渲染的图层"""
        layers = []

        # 1. 基础姿态层
        if self.current_pose:
            pose = self.poses.get(self.current_pose)
            if pose:
                base_layer = self.layers.get(pose.base_layer)
                if base_layer:
                    layers.append(base_layer)

        # 2. 服装层
        for clothing_id in self.current_clothing:
            clothing_layer = self.layers.get(clothing_id)
            if clothing_layer:
                layers.append(clothing_layer)

        # 3. 表情层
        if self.current_expression:
            expr = self.expressions.get(self.current_expression)
            if expr:
                for part in [expr.eyes, expr.eyebrows, expr.mouth, expr.blush, expr.tears, expr.sweat, expr.effect]:
                    if part:
                        part_layer = self.layers.get(part)
                        if part_layer:
                            layers.append(part_layer)

        # 4. 配饰层
        for accessory_id in self.current_accessories:
            accessory_layer = self.layers.get(accessory_id)
            if accessory_layer:
                layers.append(accessory_layer)

        # 5. 检查条件图层
        for layer in list(layers):
            if layer.conditions and not self._check_conditions(layer.conditions, context):
                layers.remove(layer)

        return layers

    def _check_conditions(self, conditions: Dict, context: Dict) -> bool:
        """检查图层条件"""
        for key, value in conditions.items():
            if key == "time_of_day":
                current_time = context.get("time_of_day", "day")
                if current_time != value:
                    return False
            elif key == "affection_min":
                affection = context.get("affection", 0)
                if affection < value:
                    return False
            elif key == "weather":
                weather = context.get("weather", "clear")
                if weather != value:
                    return False
        return True

    def _apply_transforms(self, img: Image.Image, layer: LayerDefinition) -> Image.Image:
        """应用图层变换"""
        # 透明度
        if layer.opacity < 1.0:
            alpha = img.split()[3]
            alpha = alpha.point(lambda x: int(x * layer.opacity))
            img.putalpha(alpha)

        # 着色
        if layer.tint_color and layer.tint_strength > 0:
            img = self._apply_tint(img, layer.tint_color, layer.tint_strength)

        return img

    def _apply_tint(self, img: Image.Image, color: Tuple[int, int, int], strength: float) -> Image.Image:
        """应用着色"""
        # 创建着色层
        tint_layer = Image.new("RGBA", img.size, (*color, int(255 * strength)))

        # 混合
        result = Image.new("RGBA", img.size)
        result.paste(img, (0, 0))
        result = Image.alpha_composite(result, tint_layer)

        # 保持原透明度
        alpha = img.split()[3]
        result.putalpha(alpha)

        return result

    def _blend_layer(self, canvas: Image.Image, layer_img: Image.Image,
                     layer: LayerDefinition) -> Image.Image:
        """混合图层"""
        # 应用偏移
        x, y = layer.offset_x, layer.offset_y

        # 确保图层尺寸匹配
        if layer_img.size != canvas.size:
            # 创建临时画布
            temp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            temp.paste(layer_img, (x, y))
            layer_img = temp
            x, y = 0, 0

        # 根据混合模式处理
        if layer.blend_mode == BlendMode.NORMAL:
            canvas = Image.alpha_composite(canvas, layer_img)
        elif layer.blend_mode == BlendMode.MULTIPLY:
            canvas = self._blend_multiply(canvas, layer_img)
        elif layer.blend_mode == BlendMode.SCREEN:
            canvas = self._blend_screen(canvas, layer_img)
        elif layer.blend_mode == BlendMode.OVERLAY:
            canvas = self._blend_overlay(canvas, layer_img)
        elif layer.blend_mode == BlendMode.ADD:
            canvas = self._blend_add(canvas, layer_img)
        else:
            canvas = Image.alpha_composite(canvas, layer_img)

        return canvas

    def _blend_multiply(self, base: Image.Image, layer: Image.Image) -> Image.Image:
        """正片叠底混合"""
        result = Image.new("RGBA", base.size)
        for x in range(base.width):
            for y in range(base.height):
                bp = base.getpixel((x, y))
                lp = layer.getpixel((x, y))
                r = (bp[0] * lp[0]) // 255
                g = (bp[1] * lp[1]) // 255
                b = (bp[2] * lp[2]) // 255
                a = max(bp[3], lp[3])
                result.putpixel((x, y), (r, g, b, a))
        return result

    def _blend_screen(self, base: Image.Image, layer: Image.Image) -> Image.Image:
        """滤色混合"""
        result = Image.new("RGBA", base.size)
        for x in range(base.width):
            for y in range(base.height):
                bp = base.getpixel((x, y))
                lp = layer.getpixel((x, y))
                r = 255 - ((255 - bp[0]) * (255 - lp[0])) // 255
                g = 255 - ((255 - bp[1]) * (255 - lp[1])) // 255
                b = 255 - ((255 - bp[2]) * (255 - lp[2])) // 255
                a = max(bp[3], lp[3])
                result.putpixel((x, y), (r, g, b, a))
        return result

    def _blend_overlay(self, base: Image.Image, layer: Image.Image) -> Image.Image:
        """叠加混合"""
        result = Image.new("RGBA", base.size)
        for x in range(base.width):
            for y in range(base.height):
                bp = base.getpixel((x, y))
                lp = layer.getpixel((x, y))
                r = self._overlay_channel(bp[0], lp[0])
                g = self._overlay_channel(bp[1], lp[1])
                b = self._overlay_channel(bp[2], lp[2])
                a = max(bp[3], lp[3])
                result.putpixel((x, y), (r, g, b, a))
        return result

    def _overlay_channel(self, base: int, layer: int) -> int:
        """叠加混合单通道"""
        if base < 128:
            return (2 * base * layer) // 255
        else:
            return 255 - (2 * (255 - base) * (255 - layer)) // 255

    def _blend_add(self, base: Image.Image, layer: Image.Image) -> Image.Image:
        """相加混合"""
        result = Image.new("RGBA", base.size)
        for x in range(base.width):
            for y in range(base.height):
                bp = base.getpixel((x, y))
                lp = layer.getpixel((x, y))
                r = min(255, bp[0] + lp[0])
                g = min(255, bp[1] + lp[1])
                b = min(255, bp[2] + lp[2])
                a = max(bp[3], lp[3])
                result.putpixel((x, y), (r, g, b, a))
        return result

    def _get_cache_key(self) -> str:
        """生成缓存键"""
        parts = [
            f"pose:{self.current_pose}",
            f"expr:{self.current_expression}",
            f"cloth:{','.join(sorted(self.current_clothing))}",
            f"acc:{','.join(sorted(self.current_accessories))}"
        ]
        return "|".join(parts)

    def get_available_expressions(self) -> List[Dict[str, str]]:
        """获取可用表情列表"""
        result = []
        for expr_id, expr in self.expressions.items():
            # 检查与当前姿态的兼容性
            compatible = True
            if self.current_pose:
                pose = self.poses.get(self.current_pose)
                if pose and expr_id not in pose.compatible_expressions:
                    compatible = False

            result.append({
                "id": expr_id,
                "name": expr.name,
                "compatible": compatible
            })
        return result

    def get_available_poses(self) -> List[Dict[str, str]]:
        """获取可用姿态列表"""
        return [
            {"id": pose_id, "name": pose.name}
            for pose_id, pose in self.poses.items()
        ]

    def export_to_bytes(self, format: str = "PNG") -> Optional[bytes]:
        """导出当前组合为字节"""
        img = self.compose()
        if img is None:
            return None

        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return buffer.getvalue()

    def save_composite(self, output_path: str, format: str = "PNG"):
        """保存当前组合到文件"""
        img = self.compose()
        if img:
            img.save(output_path, format=format)


class FrameAnimationPlayer:
    """
    帧动画播放器

    用于播放传统帧序列动画（呼吸、眨眼等）
    """

    def __init__(self, layered_manager: LayeredImageManager):
        self.manager = layered_manager

        # 动画定义
        self.animations: Dict[str, List[Dict]] = {}

        # 当前播放状态
        self.current_animation: Optional[str] = None
        self.current_frame: int = 0
        self.is_playing: bool = False
        self.loop: bool = False

        # 回调
        self.on_frame_change: Optional[Callable[[int], None]] = None
        self.on_animation_complete: Optional[Callable[[], None]] = None

        # 加载默认动画
        self._load_default_animations()

    def _load_default_animations(self):
        """加载默认动画定义"""
        # 眨眼动画
        self.animations["blink"] = [
            {"expression": "neutral", "duration": 100},
            {"eyes": "eyes_half", "duration": 50},
            {"eyes": "eyes_closed", "duration": 100},
            {"eyes": "eyes_half", "duration": 50},
            {"expression": "neutral", "duration": 100},
        ]

        # 呼吸动画 (通过微调偏移模拟)
        self.animations["breathing"] = [
            {"offset_y": 0, "duration": 800},
            {"offset_y": -2, "duration": 800},
            {"offset_y": 0, "duration": 800},
            {"offset_y": 2, "duration": 800},
        ]

        # 点头动画
        self.animations["nod"] = [
            {"offset_y": 0, "duration": 150},
            {"offset_y": 5, "duration": 100},
            {"offset_y": 0, "duration": 150},
        ]

        # 摇头动画
        self.animations["shake"] = [
            {"offset_x": 0, "duration": 100},
            {"offset_x": -3, "duration": 100},
            {"offset_x": 3, "duration": 100},
            {"offset_x": -3, "duration": 100},
            {"offset_x": 0, "duration": 100},
        ]

    def define_animation(self, name: str, frames: List[Dict]):
        """定义新动画"""
        self.animations[name] = frames

    def play(self, animation_name: str, loop: bool = False) -> bool:
        """播放动画"""
        if animation_name not in self.animations:
            logger.warning(f"未知动画: {animation_name}")
            return False

        self.current_animation = animation_name
        self.current_frame = 0
        self.loop = loop
        self.is_playing = True

        return True

    def stop(self):
        """停止动画"""
        self.is_playing = False
        self.current_animation = None
        self.current_frame = 0

    def get_current_frame_data(self) -> Optional[Dict]:
        """获取当前帧数据"""
        if not self.current_animation or not self.is_playing:
            return None

        frames = self.animations.get(self.current_animation, [])
        if not frames or self.current_frame >= len(frames):
            return None

        return frames[self.current_frame]

    def advance_frame(self) -> bool:
        """推进到下一帧"""
        if not self.current_animation or not self.is_playing:
            return False

        frames = self.animations.get(self.current_animation, [])
        self.current_frame += 1

        if self.on_frame_change:
            self.on_frame_change(self.current_frame)

        if self.current_frame >= len(frames):
            if self.loop:
                self.current_frame = 0
            else:
                self.is_playing = False
                if self.on_animation_complete:
                    self.on_animation_complete()
                return False

        return True

    def get_frame_duration(self) -> int:
        """获取当前帧持续时间(毫秒)"""
        frame_data = self.get_current_frame_data()
        if frame_data:
            return frame_data.get("duration", 100)
        return 100


class IdleAnimationController:
    """
    待机动画控制器

    自动播放随机的待机动画（眨眼、呼吸等）
    """

    def __init__(self, animation_player: FrameAnimationPlayer):
        self.player = animation_player
        self.is_active = False

        # 待机动画配置
        self.idle_animations = {
            "blink": {
                "weight": 30,           # 权重（越高越频繁）
                "min_interval": 2000,   # 最小间隔(毫秒)
                "max_interval": 6000,   # 最大间隔
            },
            "breathing": {
                "weight": 10,
                "min_interval": 0,      # 呼吸持续循环
                "max_interval": 0,
                "loop": True
            }
        }

        self._last_animation_time: Dict[str, float] = {}
        self._breathing_active = False

    def start(self):
        """启动待机动画"""
        self.is_active = True
        # 启动呼吸动画
        self._start_breathing()

    def stop(self):
        """停止待机动画"""
        self.is_active = False
        self.player.stop()

    def _start_breathing(self):
        """启动呼吸动画"""
        if "breathing" in self.idle_animations:
            self.player.play("breathing", loop=True)
            self._breathing_active = True

    def tick(self, current_time: float):
        """定时检查是否需要播放动画"""
        if not self.is_active:
            return

        import random

        # 检查眨眼等随机动画
        for anim_name, config in self.idle_animations.items():
            if config.get("loop"):
                continue  # 跳过循环动画

            last_time = self._last_animation_time.get(anim_name, 0)
            min_interval = config.get("min_interval", 2000) / 1000.0
            max_interval = config.get("max_interval", 6000) / 1000.0

            if current_time - last_time > min_interval:
                # 随机决定是否播放
                interval = random.uniform(min_interval, max_interval)
                if current_time - last_time > interval:
                    if random.random() < 0.3:  # 30%概率
                        self.player.play(anim_name, loop=False)
                        self._last_animation_time[anim_name] = current_time
