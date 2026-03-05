"""
悬浮助手头像视图组件 (Avatar View Component)
负责头像的显示、动画、拖拽和交互
"""
import tkinter as tk
import os
import time
from typing import Dict, Any, Optional

try:
    from PIL import Image, ImageTk, ImageSequence
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

import hashlib
from collections import deque
from pathlib import Path

from ..states import AssistantState, STATE_EMOJIS, STATE_FALLBACKS
from ..theme import ThemeManager
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

def get_icon_font(size=12):
    return IconManager().get_font(size=size)

class AvatarView(tk.Frame):
    def __init__(self, parent, assistant):
        self.theme = ThemeManager.get_theme()
        super().__init__(parent, bg=assistant.transparent_color)
        self.assistant = assistant
        self.pet_system = assistant.pet_system
        self.icon_mgr = IconManager()
        
        # 拖拽状态
        self._drag_data = {"x": 0, "y": 0, "start_time": 0, "start_x": 0, "start_y": 0}
        
        # 图片缓存
        self.avatar_images: Dict[str, Any] = {}
        self.current_avatar_image = None
        self.avatar_ratio = 1.0
        self.avatar_render_size = (0, 0)
        
        self._setup_ui()
        self._bind_events()
        
    def _setup_ui(self):
        # 头像标签
        self.avatar_label = tk.Label(
            self,
            text=get_icon("bot", "🤖"),
            font=get_icon_font(48),
            bg=self.assistant.transparent_color,
            fg=self.theme.TEXT_PRIMARY,
            cursor="hand2"
        )
        self.avatar_label.pack(anchor=tk.CENTER)

        # 状态栏
        self.status_bar = tk.Frame(self, bg=self.assistant.transparent_color)
        self.status_bar.pack(anchor=tk.CENTER)

        # 状态提示标签（计时等）
        self.status_label = tk.Label(
            self.status_bar,
            text="",
            font=(self.theme.FONT_FAMILY, 8),
            bg=self.assistant.transparent_color,
            fg=self.theme.TEXT_SECONDARY
        )
        self.status_label.pack(side=tk.LEFT, padx=2)

        # 等级标签
        level = self.pet_system.data.level
        self.level_label = tk.Label(
            self.status_bar,
            text=f"Lv.{level}",
            font=(self.theme.FONT_FAMILY, 8),
            bg=self.assistant.transparent_color,
            fg=self.theme.COLOR_WARNING # 金色
        )
        self.level_label.pack(side=tk.LEFT, padx=2)

        # 心情标签
        mood_emoji = self.pet_system.get_mood_emoji()
        self.mood_label = tk.Label(
            self.status_bar,
            text=mood_emoji,
            font=get_icon_font(10), # Try using icon font for emoji fallback too
            bg=self.assistant.transparent_color
        )
        self.mood_label.pack(side=tk.LEFT, padx=2)


    def apply_theme(self):
        """应用当前主题"""
        self.theme = ThemeManager.get_theme()
        
        # 更新背景色
        self.configure(bg=self.assistant.transparent_color)
        self.status_bar.configure(bg=self.assistant.transparent_color)
        
        self.avatar_label.configure(
            bg=self.assistant.transparent_color,
            fg=self.theme.TEXT_PRIMARY
        )
        
        self.status_label.configure(
            bg=self.assistant.transparent_color,
            fg=self.theme.TEXT_SECONDARY
        )
        
        self.level_label.configure(
            bg=self.assistant.transparent_color,
            fg=self.theme.COLOR_WARNING
        )
        
        self.mood_label.configure(bg=self.assistant.transparent_color)

    def _bind_events(self):
        self.avatar_label.bind("<Button-1>", self._start_drag)
        self.avatar_label.bind("<B1-Motion>", self._on_drag)
        self.avatar_label.bind("<ButtonRelease-1>", self._on_drag_release)
        self.avatar_label.bind("<Double-1>", self.assistant._toggle_expand)
        self.avatar_label.bind("<Button-3>", self.assistant._show_context_menu)
        self.avatar_label.bind("<Control-MouseWheel>", self._on_avatar_zoom)

    def load_images(self):
        """加载立绘图片"""
        if not HAS_PIL:
            return

        self.avatar_images.clear()
        
        # 计算尺寸
        base_size = self.assistant.avatar_size
        self._update_avatar_ratio()
        target_size = self.avatar_render_size if self.avatar_render_size != (0, 0) else (base_size, base_size)

        skin_data = self.assistant.skins.get(self.assistant.current_skin, {})
        
        for state_key, path in skin_data.items():
            if path and os.path.exists(path):
                try:
                    img = self._load_image(path, target_size)
                    if img:
                        self.avatar_images[state_key] = img
                except Exception:
                    pass
        
        # 更新显示
        self.update_avatar()

    def update_avatar(self):
        """更新头像显示"""
        state = self.assistant.state

        # 尝试获取当前状态的图片，失败则使用回退链
        img_data = self.avatar_images.get(state)

        if not img_data and state in STATE_FALLBACKS:
            for fallback in STATE_FALLBACKS[state]:
                img_data = self.avatar_images.get(fallback)
                if img_data:
                    break

        if img_data:
            if img_data["type"] == "static":
                self.avatar_label.configure(image=img_data["image"], text="")
                self.current_avatar_image = img_data["image"]
            elif img_data["type"] == "gif":
                self._animate_gif(img_data)
        else:
            # 使用emoji
            emoji = STATE_EMOJIS.get(state, "🤖")
            self.avatar_label.configure(image="", text=emoji)
            
        # 更新心情标签
        mood_emoji = self.pet_system.get_mood_emoji()
        self.mood_label.configure(text=mood_emoji)

    def update_status(self, text):
        self.status_label.configure(text=text)

    def update_level(self, level):
        self.level_label.configure(text=f"Lv.{level}")

    def _animate_gif(self, img_data: Dict, frame_idx: int = 0):
        """播放GIF动画"""
        # 如果状态改变了，停止动画
        state = self.assistant.state
        # 简单检查：如果当前显示的不是这个GIF，就不继续
        # 但这里比较难判断，因为img_data是局部变量
        # 我们可以检查 assistant.state 是否还对应这个图片
        
        frames = img_data["frames"]
        durations = img_data["durations"]

        if frame_idx >= len(frames):
            frame_idx = 0

        self.avatar_label.configure(image=frames[frame_idx], text="")
        self.current_avatar_image = frames[frame_idx]

        # 继续播放
        delay = durations[frame_idx] if frame_idx < len(durations) else 100
        self.after(delay, lambda: self._animate_gif(img_data, frame_idx + 1))

    def _get_cache_dir(self) -> Path:
        """获取背景移除缓存目录"""
        cache_dir = Path.home() / ".writer_tool" / "avatar_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _get_cached_path(self, original_path: str, mode: str = "ai") -> Optional[Path]:
        """获取缓存的透明背景图片路径"""
        if not original_path or not os.path.exists(original_path):
            return None

        # 生成缓存文件名 (基于原始路径的hash和模式)
        path_hash = hashlib.md5(original_path.encode()).hexdigest()[:16]
        original_mtime = os.path.getmtime(original_path)
        cache_name = f"{path_hash}_{mode}_{int(original_mtime)}.png"
        return self._get_cache_dir() / cache_name

    def _remove_background(self, pil_img: Image.Image, original_path: str) -> Image.Image:
        """
        移除图片背景，支持多种模式

        背景移除模式 (通过配置 assistant_bg_remove_mode 设置):
        - "ai": 使用 rembg AI模型（适合真实照片）
        - "floodfill": 使用边缘填充法（适合黑白漫画、线稿）
        - "none": 不移除背景

        对于黑白漫画人物，推荐使用 "floodfill" 模式，
        可以保护人物身体内部的白色区域（眼白、高光等）。
        """
        # 获取背景移除模式设置
        mode = "ai"  # 默认使用AI模式
        try:
            if hasattr(self.assistant, 'app') and self.assistant.app:
                mode = self.assistant.app.config_manager.get("assistant_bg_remove_mode", "ai")
            elif hasattr(self.assistant, 'config_manager') and self.assistant.config_manager:
                mode = self.assistant.config_manager.get("assistant_bg_remove_mode", "ai")
        except Exception:
            pass

        # 如果模式为 none，直接返回
        if mode == "none":
            return pil_img.convert("RGBA") if pil_img.mode != "RGBA" else pil_img

        # 检查是否已经有透明通道且不完全不透明
        if pil_img.mode == "RGBA":
            alpha = pil_img.split()[3]
            extrema = alpha.getextrema()
            if extrema != (255, 255):
                # 已经有透明区域，不需要处理
                return pil_img

        # 检查缓存 (缓存文件名包含模式)
        cache_path = self._get_cached_path(original_path, mode)
        if cache_path and cache_path.exists():
            try:
                cached_img = Image.open(cache_path)
                return cached_img.convert("RGBA")
            except Exception:
                pass

        result = None

        if mode == "floodfill":
            # 使用边缘填充法（适合黑白漫画）
            try:
                # 获取容差设置
                tolerance = 30
                try:
                    if hasattr(self.assistant, 'app') and self.assistant.app:
                        tolerance = self.assistant.app.config_manager.get("assistant_bg_remove_tolerance", 30)
                    elif hasattr(self.assistant, 'config_manager') and self.assistant.config_manager:
                        tolerance = self.assistant.config_manager.get("assistant_bg_remove_tolerance", 30)
                except Exception:
                    pass

                result = self._remove_white_background_floodfill(pil_img.copy(), tolerance=tolerance)
            except Exception:
                result = pil_img.convert("RGBA") if pil_img.mode != "RGBA" else pil_img

        elif mode == "ai" and HAS_REMBG:
            # 使用 rembg AI 移除背景
            try:
                result = rembg_remove(pil_img)
            except Exception:
                result = pil_img.convert("RGBA") if pil_img.mode != "RGBA" else pil_img
        else:
            # 无法处理，返回原图
            result = pil_img.convert("RGBA") if pil_img.mode != "RGBA" else pil_img

        # 保存到缓存
        if cache_path and result:
            try:
                result.save(cache_path, "PNG")
            except Exception:
                pass

        return result

    def _remove_white_background_floodfill(self, pil_img: Image.Image,
                                           tolerance: int = 30,
                                           edge_tolerance: int = 15) -> Image.Image:
        """
        使用边缘填充法移除白色背景（适合黑白漫画人物）

        从图像四边开始填充，只移除与边缘连通的白色/浅色区域，
        保护人物身体内部的白色区域（如眼白、高光、白色衣服等）。

        Args:
            pil_img: PIL图像
            tolerance: 主体白色判定容差 (0-255)，越大越容易被识别为白色
            edge_tolerance: 边缘检测容差，用于保护边缘附近的像素
        """
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")

        width, height = pil_img.size
        pixels = pil_img.load()

        # 创建访问标记
        visited = [[False] * height for _ in range(width)]

        def is_light_pixel(pixel, tol=tolerance):
            """判断是否为浅色像素（可能是背景）"""
            r, g, b = pixel[:3]
            # 检查是否接近白色
            if r >= 255 - tol and g >= 255 - tol and b >= 255 - tol:
                return True
            # 检查是否为浅灰色（常见于扫描的漫画背景）
            avg = (r + g + b) / 3
            if avg >= 240 - tol and abs(r - g) < 10 and abs(g - b) < 10:
                return True
            return False

        def flood_fill_from_edges():
            """从四边开始填充"""
            queue = deque()

            # 添加四边的起点
            for x in range(width):
                if is_light_pixel(pixels[x, 0]):
                    queue.append((x, 0))
                if is_light_pixel(pixels[x, height - 1]):
                    queue.append((x, height - 1))
            for y in range(height):
                if is_light_pixel(pixels[0, y]):
                    queue.append((0, y))
                if is_light_pixel(pixels[width - 1, y]):
                    queue.append((width - 1, y))

            while queue:
                x, y = queue.popleft()

                if x < 0 or x >= width or y < 0 or y >= height:
                    continue
                if visited[x][y]:
                    continue

                visited[x][y] = True

                if is_light_pixel(pixels[x, y]):
                    # 设置为透明
                    pixels[x, y] = (255, 255, 255, 0)

                    # 添加相邻像素到队列（8方向）
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                                   (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height and not visited[nx][ny]:
                            queue.append((nx, ny))

        flood_fill_from_edges()

        # 边缘平滑处理：对于边缘像素，如果周围大部分是透明的，也设为半透明
        for x in range(width):
            for y in range(height):
                if pixels[x, y][3] == 0:  # 已经透明
                    continue

                # 检查周围8个像素
                transparent_count = 0
                total = 0
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            total += 1
                            if pixels[nx, ny][3] == 0:
                                transparent_count += 1

                # 如果周围超过60%是透明的，且当前像素是浅色，则设为半透明
                if total > 0 and transparent_count / total > 0.6:
                    r, g, b, a = pixels[x, y]
                    if is_light_pixel((r, g, b), edge_tolerance):
                        # 设置半透明，实现抗锯齿效果
                        new_alpha = int(255 * (1 - transparent_count / total))
                        pixels[x, y] = (r, g, b, new_alpha)

        return pil_img

    def _load_image(self, path: str, target_size: tuple) -> Optional[Dict]:
        """加载并处理图片（自动移除背景）"""
        if not HAS_PIL:
            return None

        try:
            ext = os.path.splitext(path)[1].lower()

            if ext == ".gif":
                # GIF动画
                pil_img = Image.open(path)
                frames = []
                durations = []

                try:
                    while True:
                        frame = pil_img.copy()
                        if frame.mode != "RGBA":
                            frame = frame.convert("RGBA")
                        frame = self._resize_image_keep_ratio(frame, target_size)
                        frames.append(ImageTk.PhotoImage(frame))
                        durations.append(pil_img.info.get('duration', 100))
                        pil_img.seek(pil_img.tell() + 1)
                except EOFError:
                    pass

                if frames:
                    return {"type": "gif", "frames": frames, "durations": durations}
            else:
                # 静态图片 - 自动移除背景
                pil_img = Image.open(path)
                pil_img = self._remove_background(pil_img, path)
                pil_img = self._resize_image_keep_ratio(pil_img, target_size)
                return {"type": "static", "image": ImageTk.PhotoImage(pil_img)}
        except Exception:
            return None

    def _resize_image_keep_ratio(self, pil_img, target_size: tuple):
        """按比例缩放并居中到目标画布，透明区域填充为窗口透明色"""
        target_w, target_h = target_size
        src_w, src_h = pil_img.size
        if src_w <= 0 or src_h <= 0:
            return pil_img.resize(target_size, Image.Resampling.LANCZOS)

        scale = min(target_w / src_w, target_h / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))

        resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        if resized.mode != "RGBA":
            resized = resized.convert("RGBA")

        # 使用窗口透明色 #000001 作为背景，这样 Windows 的 transparentcolor 能正确处理
        # (0, 0, 1) 对应 #000001
        transparent_key_rgb = (0, 0, 1)
        canvas = Image.new("RGBA", target_size, (*transparent_key_rgb, 255))

        # 把图片贴到画布上，保留图片的透明通道
        offset = ((target_w - new_w) // 2, (target_h - new_h) // 2)
        canvas.paste(resized, offset, resized)  # 使用 resized 作为 mask 保留透明度

        # 把所有透明/半透明像素替换为透明色
        data = canvas.getdata()
        new_data = []
        for pixel in data:
            if pixel[3] < 128:  # 透明或半透明像素
                new_data.append((*transparent_key_rgb, 255))
            else:
                new_data.append(pixel)
        canvas.putdata(new_data)

        return canvas

    def _get_avatar_ratio(self) -> float:
        """获取当前皮肤的宽高比"""
        if not HAS_PIL:
            return 1.0

        skin_data = self.assistant.skins.get(self.assistant.current_skin, {})
        if not skin_data:
            return 1.0

        preferred_states = [
            AssistantState.IDLE,
            AssistantState.HAPPY,
            AssistantState.THINKING,
            AssistantState.SUCCESS,
            AssistantState.WRITING,
        ]
        for state in preferred_states:
            ratio = self._read_image_ratio(skin_data.get(state, ""))
            if ratio:
                return ratio

        for path in skin_data.values():
            ratio = self._read_image_ratio(path)
            if ratio:
                return ratio

        return 1.0

    def _read_image_ratio(self, path: str) -> Optional[float]:
        if not path or not os.path.exists(path):
            return None
        try:
            with Image.open(path) as img:
                width, height = img.size
            if width > 0 and height > 0:
                return width / height
        except Exception:
            return None
        return None

    def _calculate_avatar_render_size(self, base_size: int) -> tuple:
        """根据宽高比计算渲染尺寸（以高度为基准）"""
        ratio = self.avatar_ratio if self.avatar_ratio else 1.0
        width = max(1, int(base_size * ratio))
        return (width, base_size)

    def _update_avatar_ratio(self):
        """更新当前皮肤的宽高比缓存"""
        self.avatar_ratio = self._get_avatar_ratio()
        self.avatar_render_size = self._calculate_avatar_render_size(self.assistant.avatar_size)

    def _start_drag(self, event):
        """开始拖拽"""
        self.assistant._refresh_activity()
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["start_time"] = time.time()
        self._drag_data["start_x"] = event.x
        self._drag_data["start_y"] = event.y
        self.assistant.edge_snapped = False

    def _on_drag(self, event):
        """拖拽中"""
        self.assistant._refresh_activity()
        x = self.assistant.winfo_x() - self._drag_data["x"] + event.x
        y = self.assistant.winfo_y() - self._drag_data["y"] + event.y
        self.assistant.geometry(f"+{x}+{y}")

    def _on_drag_release(self, event):
        """拖拽释放"""
        # 检测是否为点击
        dx = abs(event.x - self._drag_data["start_x"])
        dy = abs(event.y - self._drag_data["start_y"])
        elapsed = time.time() - self._drag_data["start_time"]

        if dx < 10 and dy < 10 and elapsed < 0.3:
            self.assistant._on_avatar_click()
            return

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = self.assistant.winfo_x()
        y = self.assistant.winfo_y()
        w = self.assistant.winfo_width()
        h = self.assistant.winfo_height()

        snap_distance = 20

        # 边缘吸附
        if x < snap_distance:
            x = 0
            self.assistant.edge_snapped = True
            self.assistant.snap_side = "left"
        elif x + w > screen_width - snap_distance:
            x = screen_width - w
            self.assistant.edge_snapped = True
            self.assistant.snap_side = "right"

        if y < snap_distance:
            y = 0
        elif y + h > screen_height - snap_distance:
            y = screen_height - h

        self.assistant.geometry(f"+{x}+{y}")

    def _clamp_avatar_size(self, size: int) -> int:
        """限制头像尺寸范围"""
        return max(30, min(500, size))

    def _on_avatar_zoom(self, event):
        """按住 Ctrl 滚轮调整头像大小"""
        step = 10 if event.delta > 0 else -10
        new_size = self.assistant.avatar_size + step
        self.assistant._apply_avatar_size(new_size, save=True)
