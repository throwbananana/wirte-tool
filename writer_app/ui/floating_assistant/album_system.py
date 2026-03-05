"""
悬浮助手 - 升级版相册系统 (Enhanced Album System)
支持标签管理、收藏集、智能分类、导出功能等
"""
import random
import json
import io
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class PhotoCategory(Enum):
    """照片分类"""
    DAILY = "daily"             # 日常
    MILESTONE = "milestone"     # 里程碑
    FESTIVAL = "festival"       # 节日
    SPECIAL = "special"         # 特别时刻
    EXPRESSION = "expression"   # 表情收集
    OUTFIT = "outfit"           # 服装收集
    SCENE = "scene"             # 场景收集
    STORY = "story"             # 故事CG
    SECRET = "secret"           # 隐藏收集


class PhotoRarity(Enum):
    """照片稀有度"""
    COMMON = "common"           # 普通 (N)
    UNCOMMON = "uncommon"       # 不常见 (R)
    RARE = "rare"               # 稀有 (SR)
    EPIC = "epic"               # 史诗 (SSR)
    LEGENDARY = "legendary"     # 传说 (UR)


@dataclass
class PhotoTag:
    """照片标签"""
    tag_id: str
    name: str
    color: str = "#808080"      # 标签颜色
    icon: str = ""              # 标签图标
    count: int = 0              # 使用次数


@dataclass
class Photo:
    """照片条目"""
    photo_id: str
    name: str
    description: str = ""
    image_path: str = ""
    thumbnail_path: str = ""
    state_id: str = ""          # 关联的立绘状态
    category: PhotoCategory = PhotoCategory.DAILY
    rarity: PhotoRarity = PhotoRarity.COMMON
    tags: List[str] = field(default_factory=list)
    is_favorite: bool = False
    is_locked: bool = False     # 是否已解锁
    unlock_date: str = ""       # 解锁日期
    unlock_condition: str = ""  # 解锁条件描述
    view_count: int = 0         # 查看次数
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外信息


@dataclass
class Collection:
    """收藏集"""
    collection_id: str
    name: str
    description: str = ""
    cover_photo: str = ""       # 封面照片ID
    photos: List[str] = field(default_factory=list)  # 照片ID列表
    is_system: bool = False     # 是否系统收藏集
    created_at: str = ""
    updated_at: str = ""


@dataclass
class AlbumFilter:
    """相册筛选器"""
    categories: List[PhotoCategory] = field(default_factory=list)
    rarities: List[PhotoRarity] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    is_favorite: Optional[bool] = None
    is_locked: Optional[bool] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    keyword: str = ""


class EnhancedAlbumSystem:
    """
    升级版相册系统

    功能:
    1. 照片管理与收集
    2. 标签系统
    3. 收藏集功能
    4. 稀有度系统
    5. 智能分类
    6. 导出功能
    7. 统计分析
    """

    def __init__(self, assets_dir: str = None):
        self.assets_dir = Path(assets_dir) if assets_dir else None

        # 照片库
        self.photos: Dict[str, Photo] = {}

        # 标签库
        self.tags: Dict[str, PhotoTag] = {}

        # 收藏集
        self.collections: Dict[str, Collection] = {}

        # 统计数据
        self.total_photos: int = 0
        self.unlocked_count: int = 0

        # 回调
        self.on_photo_unlocked: Optional[Callable[[Photo], None]] = None
        self.on_collection_updated: Optional[Callable[[Collection], None]] = None

        # 初始化默认内容
        self._init_default_tags()
        self._init_system_collections()
        self._init_default_photos()

    def _init_default_tags(self):
        """初始化默认标签"""
        default_tags = [
            ("happy", "开心", "#FFD700"),
            ("sad", "难过", "#87CEEB"),
            ("excited", "兴奋", "#FF6347"),
            ("peaceful", "平静", "#98FB98"),
            ("special", "特别", "#FF69B4"),
            ("milestone", "里程碑", "#9370DB"),
            ("festival", "节日", "#FF4500"),
            ("daily", "日常", "#808080"),
            ("morning", "早晨", "#FFA07A"),
            ("night", "夜晚", "#483D8B"),
            ("writing", "创作中", "#20B2AA"),
            ("celebration", "庆祝", "#FFD700"),
        ]

        for tag_id, name, color in default_tags:
            self.tags[tag_id] = PhotoTag(
                tag_id=tag_id,
                name=name,
                color=color
            )

    def _init_system_collections(self):
        """初始化系统收藏集"""
        system_collections = [
            ("favorites", "我的收藏", "收藏的特别照片"),
            ("expressions", "表情图鉴", "收集的各种表情"),
            ("outfits", "服装图鉴", "收集的各种服装"),
            ("festivals", "节日回忆", "节日的特别照片"),
            ("milestones", "成长记录", "重要里程碑的记录"),
            ("story_cg", "故事回忆", "故事中解锁的CG"),
        ]

        for coll_id, name, desc in system_collections:
            self.collections[coll_id] = Collection(
                collection_id=coll_id,
                name=name,
                description=desc,
                is_system=True,
                created_at=datetime.now().isoformat()
            )

    def _init_default_photos(self):
        """初始化默认照片（立绘收集）"""
        # 表情收集
        expressions = [
            ("expr_happy", "开心", "happy", PhotoRarity.COMMON),
            ("expr_sad", "难过", "sad", PhotoRarity.COMMON),
            ("expr_angry", "生气", "angry", PhotoRarity.UNCOMMON),
            ("expr_surprised", "惊讶", "surprised", PhotoRarity.UNCOMMON),
            ("expr_shy", "害羞", "shy", PhotoRarity.RARE),
            ("expr_love", "心动", "love", PhotoRarity.RARE),
            ("expr_excited", "兴奋", "excited", PhotoRarity.UNCOMMON),
            ("expr_sleepy", "困倦", "sleepy", PhotoRarity.UNCOMMON),
            ("expr_thinking", "思考", "thinking", PhotoRarity.COMMON),
            ("expr_smug", "得意", "smug", PhotoRarity.RARE),
            ("expr_crying", "哭泣", "crying", PhotoRarity.EPIC),
            ("expr_blushing", "脸红", "blushing", PhotoRarity.RARE),
        ]

        for photo_id, name, state, rarity in expressions:
            self.photos[photo_id] = Photo(
                photo_id=photo_id,
                name=name,
                description=f"收集的{name}表情",
                state_id=state,
                category=PhotoCategory.EXPRESSION,
                rarity=rarity,
                tags=["expression"],
                is_locked=True,
                unlock_condition="在特定情境下触发"
            )

        # 节日照片
        festivals = [
            ("fest_newyear", "新年快乐", "newyear", PhotoRarity.RARE),
            ("fest_valentine", "情人节", "valentine", PhotoRarity.EPIC),
            ("fest_spring", "春节", "spring_festival", PhotoRarity.RARE),
            ("fest_christmas", "圣诞节", "christmas", PhotoRarity.RARE),
            ("fest_halloween", "万圣节", "halloween", PhotoRarity.RARE),
            ("fest_birthday", "生日快乐", "birthday", PhotoRarity.EPIC),
            ("fest_anniversary", "周年纪念", "anniversary", PhotoRarity.LEGENDARY),
        ]

        for photo_id, name, state, rarity in festivals:
            self.photos[photo_id] = Photo(
                photo_id=photo_id,
                name=name,
                description=f"{name}的特别照片",
                state_id=state,
                category=PhotoCategory.FESTIVAL,
                rarity=rarity,
                tags=["festival", "special"],
                is_locked=True,
                unlock_condition="在相应节日时解锁"
            )

        # 里程碑照片
        milestones = [
            ("mile_first_meet", "初次相遇", "first_meeting", PhotoRarity.COMMON),
            ("mile_first_chapter", "第一章完成", "milestone", PhotoRarity.UNCOMMON),
            ("mile_10k_words", "万字达成", "celebrating", PhotoRarity.UNCOMMON),
            ("mile_50k_words", "五万字达成", "celebrating", PhotoRarity.RARE),
            ("mile_100k_words", "十万字达成", "celebrating", PhotoRarity.EPIC),
            ("mile_first_finish", "首作完成", "proud", PhotoRarity.EPIC),
            ("mile_100_days", "百日纪念", "happy", PhotoRarity.RARE),
            ("mile_affection_max", "羁绊之证", "love", PhotoRarity.LEGENDARY),
        ]

        for photo_id, name, state, rarity in milestones:
            self.photos[photo_id] = Photo(
                photo_id=photo_id,
                name=name,
                description=f"达成{name}时的纪念照片",
                state_id=state,
                category=PhotoCategory.MILESTONE,
                rarity=rarity,
                tags=["milestone"],
                is_locked=True
            )

        self.total_photos = len(self.photos)

    # ============================================================
    # 照片管理
    # ============================================================

    def add_photo(self, photo: Photo) -> bool:
        """添加照片"""
        if photo.photo_id in self.photos:
            return False

        self.photos[photo.photo_id] = photo
        self.total_photos += 1

        # 更新标签计数
        for tag_id in photo.tags:
            if tag_id in self.tags:
                self.tags[tag_id].count += 1

        return True

    def unlock_photo(self, photo_id: str, metadata: Dict = None) -> Optional[Photo]:
        """解锁照片"""
        photo = self.photos.get(photo_id)
        if not photo:
            logger.warning(f"照片不存在: {photo_id}")
            return None

        if not photo.is_locked:
            logger.info(f"照片已解锁: {photo_id}")
            return photo

        photo.is_locked = False
        photo.unlock_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        if metadata:
            photo.metadata.update(metadata)

        self.unlocked_count += 1

        # 自动添加到相应收藏集
        self._auto_categorize(photo)

        # 触发回调
        if self.on_photo_unlocked:
            self.on_photo_unlocked(photo)

        return photo

    def get_photo(self, photo_id: str) -> Optional[Photo]:
        """获取照片"""
        photo = self.photos.get(photo_id)
        if photo:
            photo.view_count += 1
        return photo

    def toggle_favorite(self, photo_id: str) -> bool:
        """切换收藏状态"""
        photo = self.photos.get(photo_id)
        if not photo:
            return False

        photo.is_favorite = not photo.is_favorite

        # 更新收藏集
        favorites = self.collections.get("favorites")
        if favorites:
            if photo.is_favorite:
                if photo_id not in favorites.photos:
                    favorites.photos.append(photo_id)
            else:
                if photo_id in favorites.photos:
                    favorites.photos.remove(photo_id)

        return photo.is_favorite

    def add_tag_to_photo(self, photo_id: str, tag_id: str) -> bool:
        """给照片添加标签"""
        photo = self.photos.get(photo_id)
        if not photo:
            return False

        if tag_id not in photo.tags:
            photo.tags.append(tag_id)
            if tag_id in self.tags:
                self.tags[tag_id].count += 1

        return True

    def remove_tag_from_photo(self, photo_id: str, tag_id: str) -> bool:
        """移除照片标签"""
        photo = self.photos.get(photo_id)
        if not photo:
            return False

        if tag_id in photo.tags:
            photo.tags.remove(tag_id)
            if tag_id in self.tags:
                self.tags[tag_id].count -= 1

        return True

    def _auto_categorize(self, photo: Photo) -> None:
        """自动分类到收藏集"""
        category_mapping = {
            PhotoCategory.EXPRESSION: "expressions",
            PhotoCategory.OUTFIT: "outfits",
            PhotoCategory.FESTIVAL: "festivals",
            PhotoCategory.MILESTONE: "milestones",
            PhotoCategory.STORY: "story_cg",
        }

        collection_id = category_mapping.get(photo.category)
        if collection_id and collection_id in self.collections:
            collection = self.collections[collection_id]
            if photo.photo_id not in collection.photos:
                collection.photos.append(photo.photo_id)

    # ============================================================
    # 标签管理
    # ============================================================

    def create_tag(self, name: str, color: str = "#808080") -> PhotoTag:
        """创建标签"""
        tag_id = f"tag_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}"
        tag = PhotoTag(
            tag_id=tag_id,
            name=name,
            color=color
        )
        self.tags[tag_id] = tag
        return tag

    def update_tag(self, tag_id: str, name: str = None, color: str = None) -> Optional[PhotoTag]:
        """更新标签"""
        tag = self.tags.get(tag_id)
        if not tag:
            return None

        if name:
            tag.name = name
        if color:
            tag.color = color

        return tag

    def delete_tag(self, tag_id: str) -> bool:
        """删除标签"""
        if tag_id not in self.tags:
            return False

        # 从所有照片中移除该标签
        for photo in self.photos.values():
            if tag_id in photo.tags:
                photo.tags.remove(tag_id)

        del self.tags[tag_id]
        return True

    def get_all_tags(self) -> List[PhotoTag]:
        """获取所有标签"""
        return sorted(self.tags.values(), key=lambda t: t.count, reverse=True)

    def get_popular_tags(self, count: int = 10) -> List[PhotoTag]:
        """获取热门标签"""
        return self.get_all_tags()[:count]

    # ============================================================
    # 收藏集管理
    # ============================================================

    def create_collection(self, name: str, description: str = "") -> Collection:
        """创建收藏集"""
        coll_id = f"coll_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100, 999)}"
        collection = Collection(
            collection_id=coll_id,
            name=name,
            description=description,
            is_system=False,
            created_at=datetime.now().isoformat()
        )
        self.collections[coll_id] = collection
        return collection

    def update_collection(self, collection_id: str, **kwargs) -> Optional[Collection]:
        """更新收藏集"""
        collection = self.collections.get(collection_id)
        if not collection:
            return None

        if collection.is_system and "name" in kwargs:
            # 系统收藏集不能改名
            del kwargs["name"]

        for key, value in kwargs.items():
            if hasattr(collection, key):
                setattr(collection, key, value)

        collection.updated_at = datetime.now().isoformat()

        if self.on_collection_updated:
            self.on_collection_updated(collection)

        return collection

    def delete_collection(self, collection_id: str) -> bool:
        """删除收藏集"""
        collection = self.collections.get(collection_id)
        if not collection:
            return False

        if collection.is_system:
            logger.warning("系统收藏集不能删除")
            return False

        del self.collections[collection_id]
        return True

    def add_photo_to_collection(self, collection_id: str, photo_id: str) -> bool:
        """添加照片到收藏集"""
        collection = self.collections.get(collection_id)
        if not collection:
            return False

        if photo_id not in self.photos:
            return False

        if photo_id not in collection.photos:
            collection.photos.append(photo_id)
            collection.updated_at = datetime.now().isoformat()

        return True

    def remove_photo_from_collection(self, collection_id: str, photo_id: str) -> bool:
        """从收藏集移除照片"""
        collection = self.collections.get(collection_id)
        if not collection:
            return False

        if photo_id in collection.photos:
            collection.photos.remove(photo_id)
            collection.updated_at = datetime.now().isoformat()

        return True

    def get_collection(self, collection_id: str) -> Optional[Collection]:
        """获取收藏集"""
        return self.collections.get(collection_id)

    def get_collection_photos(self, collection_id: str) -> List[Photo]:
        """获取收藏集中的照片"""
        collection = self.collections.get(collection_id)
        if not collection:
            return []

        return [
            self.photos[pid]
            for pid in collection.photos
            if pid in self.photos
        ]

    def get_user_collections(self) -> List[Collection]:
        """获取用户创建的收藏集"""
        return [c for c in self.collections.values() if not c.is_system]

    def get_system_collections(self) -> List[Collection]:
        """获取系统收藏集"""
        return [c for c in self.collections.values() if c.is_system]

    # ============================================================
    # 查询与筛选
    # ============================================================

    def filter_photos(self, filter_obj: AlbumFilter) -> List[Photo]:
        """筛选照片"""
        results = []

        for photo in self.photos.values():
            # 分类筛选
            if filter_obj.categories and photo.category not in filter_obj.categories:
                continue

            # 稀有度筛选
            if filter_obj.rarities and photo.rarity not in filter_obj.rarities:
                continue

            # 标签筛选
            if filter_obj.tags:
                if not any(tag in photo.tags for tag in filter_obj.tags):
                    continue

            # 收藏筛选
            if filter_obj.is_favorite is not None:
                if photo.is_favorite != filter_obj.is_favorite:
                    continue

            # 解锁状态筛选
            if filter_obj.is_locked is not None:
                if photo.is_locked != filter_obj.is_locked:
                    continue

            # 日期筛选
            if filter_obj.date_from and photo.unlock_date:
                if photo.unlock_date < filter_obj.date_from:
                    continue
            if filter_obj.date_to and photo.unlock_date:
                if photo.unlock_date > filter_obj.date_to:
                    continue

            # 关键词搜索
            if filter_obj.keyword:
                keyword = filter_obj.keyword.lower()
                if keyword not in photo.name.lower() and keyword not in photo.description.lower():
                    continue

            results.append(photo)

        return results

    def get_unlocked_photos(self) -> List[Photo]:
        """获取已解锁的照片"""
        return [p for p in self.photos.values() if not p.is_locked]

    def get_locked_photos(self) -> List[Photo]:
        """获取未解锁的照片"""
        return [p for p in self.photos.values() if p.is_locked]

    def get_favorite_photos(self) -> List[Photo]:
        """获取收藏的照片"""
        return [p for p in self.photos.values() if p.is_favorite and not p.is_locked]

    def get_photos_by_category(self, category: PhotoCategory) -> List[Photo]:
        """按分类获取照片"""
        return [p for p in self.photos.values() if p.category == category]

    def get_photos_by_rarity(self, rarity: PhotoRarity) -> List[Photo]:
        """按稀有度获取照片"""
        return [p for p in self.photos.values() if p.rarity == rarity]

    def get_photos_by_tag(self, tag_id: str) -> List[Photo]:
        """按标签获取照片"""
        return [p for p in self.photos.values() if tag_id in p.tags]

    def get_recent_photos(self, count: int = 10) -> List[Photo]:
        """获取最近解锁的照片"""
        unlocked = [p for p in self.photos.values() if not p.is_locked and p.unlock_date]
        sorted_photos = sorted(unlocked, key=lambda p: p.unlock_date, reverse=True)
        return sorted_photos[:count]

    def search_photos(self, query: str) -> List[Photo]:
        """搜索照片"""
        query_lower = query.lower()
        return [
            p for p in self.photos.values()
            if query_lower in p.name.lower() or query_lower in p.description.lower()
        ]

    # ============================================================
    # 统计与分析
    # ============================================================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        unlocked = self.get_unlocked_photos()

        # 按分类统计
        category_stats = {}
        for cat in PhotoCategory:
            total = len([p for p in self.photos.values() if p.category == cat])
            unlocked_count = len([p for p in unlocked if p.category == cat])
            category_stats[cat.value] = {
                "total": total,
                "unlocked": unlocked_count,
                "progress": round(unlocked_count / total * 100, 1) if total > 0 else 0
            }

        # 按稀有度统计
        rarity_stats = {}
        for rarity in PhotoRarity:
            total = len([p for p in self.photos.values() if p.rarity == rarity])
            unlocked_count = len([p for p in unlocked if p.rarity == rarity])
            rarity_stats[rarity.value] = {
                "total": total,
                "unlocked": unlocked_count,
                "progress": round(unlocked_count / total * 100, 1) if total > 0 else 0
            }

        return {
            "total_photos": self.total_photos,
            "unlocked_count": len(unlocked),
            "completion_rate": round(len(unlocked) / self.total_photos * 100, 1) if self.total_photos > 0 else 0,
            "favorite_count": len(self.get_favorite_photos()),
            "collection_count": len(self.collections),
            "tag_count": len(self.tags),
            "category_stats": category_stats,
            "rarity_stats": rarity_stats
        }

    def get_completion_progress(self) -> Dict[str, float]:
        """获取各类别完成进度"""
        progress = {}

        for cat in PhotoCategory:
            total = len([p for p in self.photos.values() if p.category == cat])
            unlocked = len([p for p in self.photos.values() if p.category == cat and not p.is_locked])
            progress[cat.value] = round(unlocked / total * 100, 1) if total > 0 else 0

        return progress

    # ============================================================
    # 导出功能
    # ============================================================

    def export_to_json(self, photos: List[Photo] = None) -> str:
        """导出为JSON"""
        if photos is None:
            photos = self.get_unlocked_photos()

        data = [
            {
                "photo_id": p.photo_id,
                "name": p.name,
                "description": p.description,
                "category": p.category.value,
                "rarity": p.rarity.value,
                "tags": p.tags,
                "unlock_date": p.unlock_date,
                "is_favorite": p.is_favorite
            }
            for p in photos
        ]

        return json.dumps(data, ensure_ascii=False, indent=2)

    def export_to_html_gallery(self, photos: List[Photo] = None) -> str:
        """导出为HTML图鉴"""
        if photos is None:
            photos = self.get_unlocked_photos()

        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<meta charset='utf-8'>",
            "<title>相册图鉴</title>",
            "<style>",
            "body { font-family: sans-serif; background: #f5f5f5; padding: 20px; }",
            ".gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }",
            ".photo-card { background: white; border-radius: 8px; padding: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }",
            ".photo-image { width: 100%; aspect-ratio: 1; background: #eee; border-radius: 4px; display: flex; align-items: center; justify-content: center; }",
            ".photo-name { font-weight: bold; margin-top: 10px; }",
            ".photo-desc { color: #666; font-size: 0.9em; margin-top: 5px; }",
            ".photo-tags { margin-top: 10px; }",
            ".tag { display: inline-block; background: #e0e0e0; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; margin-right: 5px; }",
            f".rarity-{PhotoRarity.COMMON.value} {{ border-left: 3px solid #808080; }}",
            f".rarity-{PhotoRarity.UNCOMMON.value} {{ border-left: 3px solid #1E90FF; }}",
            f".rarity-{PhotoRarity.RARE.value} {{ border-left: 3px solid #9370DB; }}",
            f".rarity-{PhotoRarity.EPIC.value} {{ border-left: 3px solid #FFD700; }}",
            f".rarity-{PhotoRarity.LEGENDARY.value} {{ border-left: 3px solid #FF6347; }}",
            ".favorite { position: absolute; top: 5px; right: 5px; color: #ff4444; }",
            "</style>",
            "</head><body>",
            "<h1>相册图鉴</h1>",
            f"<p>收集进度: {len(photos)}/{self.total_photos}</p>",
            "<div class='gallery'>",
        ]

        for photo in photos:
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in photo.tags[:3])
            favorite_icon = "&#9829;" if photo.is_favorite else ""

            html_parts.append(f"""
            <div class="photo-card rarity-{photo.rarity.value}">
                <div class="photo-image" style="position:relative;">
                    {photo.state_id}
                    <span class="favorite">{favorite_icon}</span>
                </div>
                <div class="photo-name">{photo.name}</div>
                <div class="photo-desc">{photo.description[:50]}...</div>
                <div class="photo-tags">{tags_html}</div>
            </div>
            """)

        html_parts.append("</div></body></html>")

        return "\n".join(html_parts)

    def export_collection_as_zip(self, collection_id: str, output_path: str = None) -> Optional[bytes]:
        """导出收藏集为ZIP"""
        collection = self.collections.get(collection_id)
        if not collection:
            return None

        photos = self.get_collection_photos(collection_id)
        if not photos:
            return None

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加元数据
            metadata = {
                "collection_name": collection.name,
                "description": collection.description,
                "photo_count": len(photos),
                "export_date": datetime.now().isoformat()
            }
            zipf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))

            # 添加照片列表
            photos_data = [
                {
                    "name": p.name,
                    "description": p.description,
                    "rarity": p.rarity.value,
                    "unlock_date": p.unlock_date
                }
                for p in photos
            ]
            zipf.writestr("photos.json", json.dumps(photos_data, ensure_ascii=False, indent=2))

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    # ============================================================
    # 状态持久化
    # ============================================================

    def get_state(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "photos": {
                pid: {
                    "photo_id": p.photo_id,
                    "name": p.name,
                    "description": p.description,
                    "image_path": p.image_path,
                    "state_id": p.state_id,
                    "category": p.category.value,
                    "rarity": p.rarity.value,
                    "tags": p.tags,
                    "is_favorite": p.is_favorite,
                    "is_locked": p.is_locked,
                    "unlock_date": p.unlock_date,
                    "unlock_condition": p.unlock_condition,
                    "view_count": p.view_count,
                    "created_at": p.created_at,
                    "metadata": p.metadata
                }
                for pid, p in self.photos.items()
            },
            "tags": {
                tid: {
                    "tag_id": t.tag_id,
                    "name": t.name,
                    "color": t.color,
                    "count": t.count
                }
                for tid, t in self.tags.items()
            },
            "collections": {
                cid: {
                    "collection_id": c.collection_id,
                    "name": c.name,
                    "description": c.description,
                    "cover_photo": c.cover_photo,
                    "photos": c.photos,
                    "is_system": c.is_system,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at
                }
                for cid, c in self.collections.items()
            },
            "total_photos": self.total_photos,
            "unlocked_count": self.unlocked_count
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """加载状态"""
        # 加载照片
        photos_data = state.get("photos", {})
        for pid, pdata in photos_data.items():
            try:
                self.photos[pid] = Photo(
                    photo_id=pdata["photo_id"],
                    name=pdata["name"],
                    description=pdata.get("description", ""),
                    image_path=pdata.get("image_path", ""),
                    state_id=pdata.get("state_id", ""),
                    category=PhotoCategory(pdata["category"]),
                    rarity=PhotoRarity(pdata["rarity"]),
                    tags=pdata.get("tags", []),
                    is_favorite=pdata.get("is_favorite", False),
                    is_locked=pdata.get("is_locked", True),
                    unlock_date=pdata.get("unlock_date", ""),
                    unlock_condition=pdata.get("unlock_condition", ""),
                    view_count=pdata.get("view_count", 0),
                    created_at=pdata.get("created_at", ""),
                    metadata=pdata.get("metadata", {})
                )
            except Exception as e:
                logger.warning(f"加载照片 {pid} 失败: {e}")

        # 加载标签
        tags_data = state.get("tags", {})
        for tid, tdata in tags_data.items():
            self.tags[tid] = PhotoTag(
                tag_id=tdata["tag_id"],
                name=tdata["name"],
                color=tdata.get("color", "#808080"),
                count=tdata.get("count", 0)
            )

        # 加载收藏集
        collections_data = state.get("collections", {})
        for cid, cdata in collections_data.items():
            self.collections[cid] = Collection(
                collection_id=cdata["collection_id"],
                name=cdata["name"],
                description=cdata.get("description", ""),
                cover_photo=cdata.get("cover_photo", ""),
                photos=cdata.get("photos", []),
                is_system=cdata.get("is_system", False),
                created_at=cdata.get("created_at", ""),
                updated_at=cdata.get("updated_at", "")
            )

        self.total_photos = state.get("total_photos", len(self.photos))
        self.unlocked_count = state.get("unlocked_count", 0)


# 便捷函数
def create_album_system(assets_dir: str = None) -> EnhancedAlbumSystem:
    """创建相册系统"""
    return EnhancedAlbumSystem(assets_dir)
