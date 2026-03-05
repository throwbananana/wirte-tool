# -*- coding: utf-8 -*-
import logging
import os
import json
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import re
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AnalysisContext:
    """
    累积上下文：在分析长文本时保持跨章节的信息连贯性。

    用于解决长上下文问题：
    - 将已识别的角色/设定传递给后续分析
    - 维护滚动摘要供后续章节参考
    - 追踪关系演变
    """
    # 已识别的角色名称列表（用于后续章节识别）
    known_characters: List[str] = field(default_factory=list)

    # 已识别的设定/名词列表
    known_entities: List[str] = field(default_factory=list)

    # 滚动摘要：最近N个章节的剧情概要
    rolling_summary: str = ""

    # 章节摘要列表（用于生成滚动摘要）
    chapter_summaries: List[Dict[str, str]] = field(default_factory=list)

    # 最大滚动摘要长度（字符数）
    max_summary_length: int = 2000

    # 保留的最近章节数
    max_chapters_in_summary: int = 5

    def add_characters(self, names: List[str]):
        """添加新识别的角色名称。"""
        for name in names:
            name = name.strip()
            if name and name not in self.known_characters:
                self.known_characters.append(name)

    def add_entities(self, names: List[str]):
        """添加新识别的设定名词。"""
        for name in names:
            name = name.strip()
            if name and name not in self.known_entities:
                self.known_entities.append(name)

    def add_chapter_summary(self, chapter_title: str, summary: str):
        """添加章节摘要并更新滚动摘要。"""
        self.chapter_summaries.append({
            "title": chapter_title,
            "summary": summary
        })

        # 只保留最近N个章节
        if len(self.chapter_summaries) > self.max_chapters_in_summary:
            self.chapter_summaries = self.chapter_summaries[-self.max_chapters_in_summary:]

        # 更新滚动摘要
        self._update_rolling_summary()

    def _update_rolling_summary(self):
        """根据章节摘要列表生成滚动摘要。"""
        parts = []
        for cs in self.chapter_summaries:
            parts.append(f"【{cs['title']}】{cs['summary']}")

        combined = "\n".join(parts)

        # 如果超过最大长度，截取最近的部分
        if len(combined) > self.max_summary_length:
            combined = combined[-self.max_summary_length:]
            # 从第一个完整句子开始
            cut_candidates = [combined.find(p) for p in ("。", "！", "？", ".", "!", "?")]
            cut_candidates = [c for c in cut_candidates if 0 < c < 200]
            if cut_candidates:
                first_period = min(cut_candidates)
                combined = combined[first_period + 1:]

        self.rolling_summary = combined

    def get_context_prompt(self, analysis_type: str) -> str:
        """根据分析类型生成上下文提示词。"""
        parts = []

        # 添加已识别角色（对角色和关系分析特别重要）
        if self.known_characters and analysis_type in ("characters", "relationships", "outline", "timeline"):
            chars_str = "、".join(self.known_characters[:30])  # 限制数量
            parts.append(f"【已知角色】：{chars_str}")

        # 添加已识别设定（对wiki分析重要）
        if self.known_entities and analysis_type in ("wiki", "outline"):
            entities_str = "、".join(self.known_entities[:20])
            parts.append(f"【已知设定】：{entities_str}")

        # 添加滚动摘要（对所有分析都有帮助）
        if self.rolling_summary:
            parts.append(f"【前情提要】：\n{self.rolling_summary}")

        if parts:
            return "\n\n".join(parts) + "\n\n---\n\n"
        return ""

    def to_dict(self) -> Dict:
        """导出为字典（用于持久化）。"""
        return {
            "known_characters": self.known_characters,
            "known_entities": self.known_entities,
            "rolling_summary": self.rolling_summary,
            "chapter_summaries": self.chapter_summaries
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AnalysisContext":
        """从字典恢复（用于加载会话）。"""
        ctx = cls()
        ctx.known_characters = data.get("known_characters", [])
        ctx.known_entities = data.get("known_entities", [])
        ctx.rolling_summary = data.get("rolling_summary", "")
        ctx.chapter_summaries = data.get("chapter_summaries", [])
        return ctx

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.result.append(text)

    def get_text(self):
        return "\n".join(self.result)

class EpubReader:
    """Reads EPUB files using standard libraries only."""
    
    namespaces = {
        'u': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'opf': 'http://www.idpf.org/2007/opf',
        'ncx': 'http://www.daisy.org/z3986/2005/ncx/'
    }

    def __init__(self, file_path):
        self.file_path = file_path

    def read(self) -> str:
        """Extracts all text content from the EPUB in reading order."""
        if not zipfile.is_zipfile(self.file_path):
            raise ValueError("Invalid EPUB file (not a zip).")

        with zipfile.ZipFile(self.file_path, 'r') as z:
            root_path = self._find_rootfile(z)
            if not root_path:
                raise ValueError("Could not parse META-INF/container.xml")

            # 2. Parse the OPF file to get the spine
            opf_content = z.read(root_path)
            opf_string = opf_content.decode('utf-8', errors='ignore')
            opf_root = ET.fromstring(opf_string)

            manifest = self._parse_manifest(opf_root)
            spine = self._parse_spine(opf_root, manifest)
            if not spine:
                logger.warning("EPUB spine is empty, falling back to manifest order.")
                spine = list(manifest.values())

            # 3. Read content files in order
            full_text = []
            opf_dir = os.path.dirname(root_path)
            
            for href in spine:
                # Resolve path relative to OPF file
                file_path = os.path.join(opf_dir, href).replace('\\', '/')
                try:
                    content = z.read(file_path).decode('utf-8', errors='ignore')
                    parser = TextExtractor()
                    parser.feed(content)
                    text = parser.get_text()
                    if text:
                        full_text.append(f"--- Section: {href} ---")
                        full_text.append(text)
                except KeyError:
                    # Sometimes manifest paths are weird or absolute
                    logger.warning("Spine entry %s not found in EPUB archive.", file_path)
                except Exception as e:
                    logger.warning("Error reading %s: %s", file_path, e)

            if not full_text:
                logger.info("Falling back to scanning all HTML/XHTML files for text.")
                full_text = self._fallback_collect_html(z)

            if not full_text:
                raise ValueError("EPUB 内容为空或未能解析文本。")

            return "\n\n".join(full_text)

    def read_chapters(self) -> List[Dict[str, str]]:
        """Extracts text content grouped by chapters/sections."""
        if not zipfile.is_zipfile(self.file_path):
            raise ValueError("Invalid EPUB file (not a zip).")

        chapters = []
        with zipfile.ZipFile(self.file_path, 'r') as z:
            root_path = self._find_rootfile(z)
            if not root_path:
                fallback = "\n\n".join(self._fallback_collect_html(z))
                return [{"title": "Full Text", "content": fallback}] if fallback else []

            try:
                opf_content = z.read(root_path).decode('utf-8', errors='ignore')
                opf_root = ET.fromstring(opf_content)
            except Exception as exc:
                logger.warning("Failed to parse OPF file: %s", exc)
                fallback = "\n\n".join(self._fallback_collect_html(z))
                return [{"title": "Full Text", "content": fallback}] if fallback else []

            manifest = self._parse_manifest(opf_root)
            spine = self._parse_spine(opf_root, manifest)
            if not spine:
                spine = list(manifest.values())

            # 3. Read content
            opf_dir = os.path.dirname(root_path)
            for href in spine:
                file_path = os.path.join(opf_dir, href).replace('\\', '/')
                try:
                    content = z.read(file_path).decode('utf-8', errors='ignore')
                    parser = TextExtractor()
                    parser.feed(content)
                    text = parser.get_text()
                    if len(text) > 100: # Filter out very short sections (covers, toc)
                        chapters.append({
                            "title": href, # Use filename as title if no metadata
                            "content": text
                        })
                except Exception as exc:
                    logger.warning("Skipping chapter %s due to error: %s", file_path, exc)

        if not chapters:
            with zipfile.ZipFile(self.file_path, 'r') as fallback_zf:
                fallback = "\n\n".join(self._fallback_collect_html(fallback_zf))
            if fallback:
                return [{"title": "Full Text", "content": fallback}]
        return chapters

    def _find_rootfile(self, zf: zipfile.ZipFile) -> Optional[str]:
        try:
            container_xml = zf.read('META-INF/container.xml')
            root = ET.fromstring(container_xml)
            node = root.find('.//u:rootfile', self.namespaces) or root.find('.//{*}rootfile')
            if node is not None:
                return node.attrib.get('full-path')
        except Exception as exc:
            logger.warning("Could not parse container.xml: %s", exc)
        return None

    def _parse_manifest(self, opf_root: ET.Element) -> Dict[str, str]:
        ns = {'opf': 'http://www.idpf.org/2007/opf'}
        manifest: Dict[str, str] = {}
        for item in opf_root.findall('.//opf:item', ns) + opf_root.findall('.//{*}item'):
            item_id = item.attrib.get('id')
            href = item.attrib.get('href')
            if item_id and href and item_id not in manifest:
                manifest[item_id] = href
        return manifest

    def _parse_spine(self, opf_root: ET.Element, manifest: Dict[str, str]) -> List[str]:
        ns = {'opf': 'http://www.idpf.org/2007/opf'}
        spine = []
        for itemref in opf_root.findall('.//opf:itemref', ns) + opf_root.findall('.//{*}itemref'):
            idref = itemref.attrib.get('idref')
            if idref in manifest:
                spine.append(manifest[idref])
        return spine

    def _fallback_collect_html(self, zf: zipfile.ZipFile) -> List[str]:
        """Collect text from all HTML-like files if the manifest/spine cannot be parsed."""
        collected = []
        for name in sorted(zf.namelist()):
            if not name.lower().endswith((".xhtml", ".html", ".htm")):
                continue
            try:
                content = zf.read(name).decode('utf-8', errors='ignore')
                parser = TextExtractor()
                parser.feed(content)
                text = parser.get_text()
                if text:
                    collected.append(f"--- Section: {name} ---")
                    collected.append(text)
            except Exception as exc:
                logger.warning("Fallback reader skipped %s: %s", name, exc)
        return collected

class ReverseEngineeringManager:
    """Manages the analysis of texts to extract structured data."""

    # 章节标题检测正则表达式
    CHAPTER_PATTERNS = [
        r'^第[一二三四五六七八九十百千\d]+[章节卷部集回]',  # 第X章、第X节
        r'^Chapter\s+\d+',  # Chapter 1
        r'^CHAPTER\s+\d+',
        r'^卷[一二三四五六七八九十\d]+',  # 卷一
        r'^\d+[\.、]\s*\S+',  # 1. 标题 或 1、标题
        r'^【[^】]+】$',  # 【章节名】
        r'^━+\s*\S+\s*━+$',  # ━━ 章节名 ━━
    ]

    def __init__(self, ai_client, max_chunk_size: int = 6000, max_retries: int = 3):
        self.ai_client = ai_client
        self.max_chunk_size = max_chunk_size
        self.max_retries = max_retries
        self._compiled_patterns = [re.compile(p, re.MULTILINE) for p in self.CHAPTER_PATTERNS]
        # 增量分析：记录已分析的章节哈希值
        self._analyzed_hashes: Dict[str, Set[str]] = {}  # {analysis_type: set of content hashes}
        self._summary_cache: Dict[str, str] = {}

        # 容错：解析常见的容器键，兼容 LLM 输出变体
        self._container_keys = {
            "characters": ("characters", "character_list", "people", "persons", "items"),
            "wiki": (
                "wiki", "entries", "entry_list", "setting", "setting_list", "setting_elements",
                "setting_items", "setting_terms", "world_setting", "world_settings"
            ),
            "outline": ("outline", "events", "event_list", "storyline", "plot", "nodes"),
            "relationships": ("relations", "relationships", "relation_list", "links"),
            "summary": ("summary", "summaries"),
            "style": ("style", "styles")
        }

    @staticmethod
    def _first_present(item: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[Any]:
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return None

    def _extract_timeline_items(self, result: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        truth_items = []
        lie_items = []

        for key in ("truth_events", "truth", "truth_list"):
            value = result.get(key)
            if isinstance(value, list):
                truth_items.extend(value)

        for key in ("lie_events", "lie", "lie_list"):
            value = result.get(key)
            if isinstance(value, list):
                lie_items.extend(value)

        if truth_items or lie_items:
            items = []
            for item in truth_items:
                if isinstance(item, dict):
                    entry = dict(item)
                    entry.setdefault("type", "truth")
                    items.append(entry)
            for item in lie_items:
                if isinstance(item, dict):
                    entry = dict(item)
                    entry.setdefault("type", "lie")
                    items.append(entry)
            return items

        for key in ("timeline", "events", "event_list", "items"):
            value = result.get(key)
            if isinstance(value, list):
                return value

        return None

    def _extract_items_from_container(self, result: Dict[str, Any], analysis_type: str) -> Optional[List[Any]]:
        if analysis_type == "timeline":
            return self._extract_timeline_items(result)

        for key in self._container_keys.get(analysis_type, ()):
            value = result.get(key)
            if isinstance(value, list):
                return value
        return None

    def _looks_like_item(self, result: Dict[str, Any], analysis_type: str) -> bool:
        if analysis_type == "relationships":
            return bool(result.get("source") or result.get("target"))
        if analysis_type == "timeline":
            return bool(result.get("name") or result.get("action") or result.get("gap") or result.get("timestamp"))
        if analysis_type in ("summary", "style"):
            return bool(result.get("content") or result.get("analysis") or result.get("summary"))
        return bool(result.get("name") or result.get("title"))

    def _normalize_item(self, item: Dict[str, Any], analysis_type: str) -> Optional[Dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        normalized = dict(item)

        if analysis_type == "characters":
            name = normalized.get("name") or self._first_present(item, ("character", "person", "title"))
            if name:
                normalized["name"] = str(name).strip()
            role = normalized.get("role") or self._first_present(item, ("position", "identity", "role_name"))
            if role:
                normalized["role"] = str(role).strip()
            desc = normalized.get("description") or self._first_present(item, ("desc", "summary", "profile", "details"))
            if desc:
                normalized["description"] = str(desc).strip()
            tags = normalized.get("tags")
            if not tags:
                tag_val = self._first_present(item, ("tag", "tags"))
                if tag_val:
                    normalized["tags"] = tag_val if isinstance(tag_val, list) else [str(tag_val)]

        elif analysis_type == "wiki":
            name = normalized.get("name") or self._first_present(item, ("term", "entry", "title"))
            if name:
                normalized["name"] = str(name).strip()
            category = normalized.get("category") or self._first_present(item, ("type", "kind"))
            if category:
                normalized["category"] = str(category).strip()
            content = normalized.get("content") or self._first_present(item, ("description", "desc", "detail", "text"))
            if content:
                normalized["content"] = str(content).strip()

        elif analysis_type == "outline":
            name = normalized.get("name") or self._first_present(item, ("title", "event", "summary"))
            if name:
                normalized["name"] = str(name).strip()
            content = normalized.get("content") or self._first_present(item, ("description", "detail", "text"))
            if content:
                normalized["content"] = str(content).strip()
            chars = normalized.get("characters")
            if chars is None:
                alt_chars = self._first_present(item, ("roles", "people"))
                if isinstance(alt_chars, list):
                    normalized["characters"] = alt_chars

        elif analysis_type == "relationships":
            source = normalized.get("source") or self._first_present(item, ("from", "src"))
            if source:
                normalized["source"] = str(source).strip()
            target = normalized.get("target") or self._first_present(item, ("to", "dst"))
            if target:
                normalized["target"] = str(target).strip()
            target_type = normalized.get("target_type") or self._first_present(item, ("type", "targetType", "target_kind"))
            if target_type:
                normalized["target_type"] = str(target_type).strip()
            label = normalized.get("label") or self._first_present(item, ("relation", "relationship", "relation_type"))
            if label:
                normalized["label"] = str(label).strip()
            desc = normalized.get("description") or self._first_present(item, ("detail", "desc"))
            if desc:
                normalized["description"] = str(desc).strip()
            if not normalized.get("target_type"):
                normalized["target_type"] = "character"

        elif analysis_type == "timeline":
            event_type = normalized.get("type") or self._first_present(item, ("event_type", "track"))
            if event_type:
                normalized["type"] = str(event_type).strip().lower()
            if normalized.get("type") not in ("truth", "lie"):
                normalized["type"] = "truth"
            name = normalized.get("name") or self._first_present(item, ("event", "title", "event_name"))
            if name:
                normalized["name"] = str(name).strip()
            timestamp = normalized.get("timestamp") or self._first_present(item, ("time", "date", "datetime"))
            if timestamp:
                normalized["timestamp"] = str(timestamp).strip()
            location = normalized.get("location") or self._first_present(item, ("place", "where"))
            if location:
                normalized["location"] = str(location).strip()
            action = normalized.get("action") or self._first_present(item, ("event_detail", "detail", "description"))
            if action:
                normalized["action"] = str(action).strip()
            motive = normalized.get("motive") or self._first_present(item, ("reason", "cause"))
            if motive:
                normalized["motive"] = str(motive).strip()
            chaos = normalized.get("chaos") or self._first_present(item, ("unexpected", "complication"))
            if chaos:
                normalized["chaos"] = str(chaos).strip()
            gap = normalized.get("gap") or self._first_present(item, ("hidden", "cover", "omission"))
            if gap:
                normalized["gap"] = str(gap).strip()
            bug = normalized.get("bug") or self._first_present(item, ("flaw", "loophole"))
            if bug:
                normalized["bug"] = str(bug).strip()
            linked_truth_name = normalized.get("linked_truth_name") or self._first_present(
                item, ("linked_truth", "linked_truth_event", "linked_truth_event_name")
            )
            if linked_truth_name:
                normalized["linked_truth_name"] = str(linked_truth_name).strip()

            if not normalized.get("description"):
                normalized["description"] = normalized.get("action") or normalized.get("gap") or ""

            if not normalized.get("name"):
                fallback = normalized.get("action") or normalized.get("gap") or normalized.get("description")
                if fallback:
                    normalized["name"] = str(fallback).strip()[:30]

        elif analysis_type == "summary":
            content = normalized.get("content") or self._first_present(item, ("summary", "text"))
            if content:
                normalized["content"] = str(content).strip()
            name = normalized.get("name") or self._first_present(item, ("title",))
            if name:
                normalized["name"] = str(name).strip()

        elif analysis_type == "style":
            content = normalized.get("content") or self._first_present(item, ("analysis", "text"))
            if content:
                normalized["content"] = str(content).strip()
            if not normalized.get("name"):
                normalized["name"] = "写作风格"

        # Final validation: ensure required fields exist
        if analysis_type == "relationships":
            if not normalized.get("source") or not normalized.get("target"):
                return None
        elif analysis_type in ("summary", "style"):
            if not normalized.get("content"):
                return None
        else:
            if not normalized.get("name"):
                return None

        return normalized

    def _normalize_result(self, result: Any, analysis_type: str) -> Optional[List[Dict[str, Any]]]:
        if result is None:
            return None

        if isinstance(result, list):
            items = result
        elif isinstance(result, dict):
            items = self._extract_items_from_container(result, analysis_type)
            if items is None:
                if self._looks_like_item(result, analysis_type):
                    items = [result]
                else:
                    return None
        else:
            return None

        normalized_items = []
        for item in items:
            if isinstance(item, dict):
                normalized = self._normalize_item(item, analysis_type)
                if normalized:
                    normalized_items.append(normalized)
        if items and not normalized_items:
            return None
        return normalized_items

    # --- 增量分析支持 ---
    @staticmethod
    def _compute_hash(content: str) -> str:
        """计算内容的哈希值用于增量检测。"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]

    def get_incremental_units(
        self,
        processing_units: List[Dict[str, str]],
        analysis_type: str
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        将处理单元分为新增和已分析两部分。

        Returns:
            (new_units, skipped_units): 需要分析的新单元和可跳过的已分析单元
        """
        if analysis_type not in self._analyzed_hashes:
            self._analyzed_hashes[analysis_type] = set()

        analyzed_set = self._analyzed_hashes[analysis_type]
        new_units = []
        skipped_units = []

        for unit in processing_units:
            content_hash = self._compute_hash(unit["content"])
            unit["_hash"] = content_hash  # 记录哈希供后续使用

            if content_hash in analyzed_set:
                skipped_units.append(unit)
            else:
                new_units.append(unit)

        return new_units, skipped_units

    def mark_analyzed(self, content_hash: str, analysis_type: str):
        """标记某个内容已完成分析。"""
        if analysis_type not in self._analyzed_hashes:
            self._analyzed_hashes[analysis_type] = set()
        self._analyzed_hashes[analysis_type].add(content_hash)

    def clear_analysis_cache(self, analysis_type: Optional[str] = None):
        """清除分析缓存，强制重新分析。"""
        if analysis_type:
            self._analyzed_hashes.pop(analysis_type, None)
        else:
            self._analyzed_hashes.clear()

    def get_analysis_progress(self) -> Dict[str, int]:
        """获取各类型的已分析数量。"""
        return {k: len(v) for k, v in self._analyzed_hashes.items()}

    def export_analysis_state(self) -> Dict:
        """导出增量分析状态用于持久化。"""
        return {
            "analyzed_hashes": {k: list(v) for k, v in self._analyzed_hashes.items()},
            "summary_cache": self._summary_cache
        }

    def import_analysis_state(self, state: Dict):
        """导入增量分析状态。"""
        if "analyzed_hashes" in state:
            self._analyzed_hashes = {
                k: set(v) for k, v in state["analyzed_hashes"].items()
            }
        if "summary_cache" in state and isinstance(state["summary_cache"], dict):
            self._summary_cache = state["summary_cache"]

    def set_cached_summary(self, content_hash: str, summary: str):
        if content_hash and summary:
            self._summary_cache[content_hash] = summary

    def get_cached_summary(self, content_hash: str) -> str:
        return self._summary_cache.get(content_hash, "")

    def load_file(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.epub':
            reader = EpubReader(file_path)
            return reader.read()
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def load_file_structured(self, file_path: str) -> List[Dict[str, str]]:
        """Loads file as a list of chapters/sections with intelligent chapter detection."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.epub':
            reader = EpubReader(file_path)
            return reader.read_chapters()
        elif ext == '.txt':
            text = self.load_file(file_path)
            return self._split_txt_into_chapters(text)
        else:
            return []

    def _split_txt_into_chapters(self, text: str) -> List[Dict[str, str]]:
        """
        智能分割TXT文本为章节。
        支持多种章节格式：第X章、Chapter X、【章节名】等。
        """
        lines = text.split('\n')
        chapters = []
        current_title = "序章"
        current_content = []

        for line in lines:
            stripped = line.strip()
            is_chapter_title = False

            # 检测是否为章节标题
            for pattern in self._compiled_patterns:
                if pattern.match(stripped):
                    is_chapter_title = True
                    break

            if is_chapter_title and stripped:
                # 保存之前的章节（如果有内容）
                if current_content:
                    content_text = '\n'.join(current_content).strip()
                    if len(content_text) > 50:  # 过滤过短的内容
                        chapters.append({
                            "title": current_title,
                            "content": content_text
                        })

                # 开始新章节
                current_title = stripped
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个章节
        if current_content:
            content_text = '\n'.join(current_content).strip()
            if len(content_text) > 50:
                chapters.append({
                    "title": current_title,
                    "content": content_text
                })

        # 如果未检测到章节，返回整个文本
        if not chapters:
            return [{"title": "Full Text", "content": text}]

        return chapters

    def split_text(self, text: str, chunk_size=None) -> List[str]:
        """Splits text into chunks, respecting paragraph boundaries."""
        if chunk_size is None:
            chunk_size = self.max_chunk_size
        
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        current_chunk = []
        current_len = 0
        
        # Split by double newlines to keep paragraphs
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            if current_len + len(para) > chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            
            current_chunk.append(para)
            current_len += len(para)
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks

    def analyze_chunk(
        self,
        chunk: str,
        analysis_type: str,
        config: Dict,
        context: Optional[AnalysisContext] = None,
        request_timeout: Optional[int] = None
    ) -> Any:
        """
        Sends a chunk to AI for specific analysis with optional accumulated context.

        Args:
            chunk: Text content
            analysis_type: 'characters', 'outline', 'wiki', 'relationships', 'style', 'summary'
            config: API config dict (url, model, key)
            context: Optional AnalysisContext with known characters, entities, and rolling summary
            request_timeout: Optional per-request timeout in seconds
        """
        prompts = {
            "characters": {
                "system": "你是专业的文学分析师。请分析以下文本，提取其中出现的主要角色。",
                "user": (
                    "{context_prompt}"
                    "请阅读以下文本，提取所有出现的角色信息。\n"
                    "注意：如果上方有【已知角色】列表，请关注这些角色的新信息，同时也要发现新角色。\n"
                    "返回JSON格式列表，每个元素包含：\n"
                    "- name: 角色名字\n"
                    "- role: 角色定位（主角/配角/反派等）\n"
                    "- description: 外貌和性格特征描述\n"
                    "- tags: 相关的简短标签列表\n\n"
                    "文本内容：\n{text}"
                )
            },
            "outline": {
                "system": "你是专业的剧情分析师。请总结以下文本的关键情节。",
                "user": (
                    "{context_prompt}"
                    "请阅读以下文本，总结发生的关键事件。\n"
                    "注意：参考【前情提要】了解之前发生的事，关注新的情节发展。\n"
                    "返回JSON格式列表，每个元素包含：\n"
                    "- name: 事件标题（简短）\n"
                    "- content: 事件详情描述\n"
                    "- characters: 参与的角色名字列表（使用【已知角色】中的标准名称）\n\n"
                    "文本内容：\n{text}"
                )
            },
            "wiki": {
                "system": "你是世界观设定分析师。请分析文本中的设定名词。",
                "user": (
                    "{context_prompt}"
                    "请阅读以下文本，提取世界观设定（地点、组织、物品、魔法/技术系统）。\n"
                    "注意：如果上方有【已知设定】，关注这些设定的新细节，同时也要发现新设定。\n"
                    "返回JSON格式列表，每个元素包含：\n"
                    "- name: 名词\n"
                    "- category: 分类（地点/组织/物品/设定）\n"
                    "- content: 详细描述\n\n"
                    "文本内容：\n{text}"
                )
            },
            "timeline": {
                "system": "你是专业的刑侦时间轴分析师。请分析文本中的关键事件，区分客观事实（Truth）和主观陈述/谎言（Lie）。",
                "user": (
                    "{context_prompt}"
                    "请阅读以下文本，提取带有时间信息的关键事件。\n"
                    "注意：参考【前情提要】了解时间线上下文。\n"
                    "返回JSON格式列表，每个元素包含：\n\n"
                    "【真相事件 (type='truth')】：\n"
                    "- name: 事件名称（简短）\n"
                    "- type: 'truth'\n"
                    "- timestamp: 时间（格式: YYYY-MM-DD HH:MM，如不确定可用相对描述如 '案发当晚 20:00'）\n"
                    "- location: 地点\n"
                    "- action: 实际发生的行动/事件详情\n"
                    "- motive: 行动动机\n"
                    "- chaos: 意外/混乱因素（如有）\n\n"
                    "【谎言事件 (type='lie')】：\n"
                    "- name: 事件名称（简短）\n"
                    "- type: 'lie'\n"
                    "- timestamp: 宣称的时间\n"
                    "- motive: 撒谎的借口/理由\n"
                    "- gap: 实际隐瞒的内容（谎言掩盖了什么）\n"
                    "- bug: 破绽（如有明显漏洞）\n"
                    "- linked_truth_name: 关联的真相事件名称（如果能对应）\n\n"
                    "文本内容：\n{text}"
                )
            },
            "relationships": {
                "system": "你是人物关系及势力架构分析师。",
                "user": (
                    "{context_prompt}"
                    "请分析文本中角色之间、以及角色与组织/势力之间的关系。\n"
                    "注意：使用【已知角色】中的标准名称，关注关系的变化和演进。\n"
                    "返回JSON格式列表，每个元素包含：\n"
                    "- source: 主体名字（通常是角色）\n"
                    "- target: 客体名字（角色或组织名）\n"
                    "- target_type: 客体类型（'character' 或 'faction'）\n"
                    "- label: 关系描述（如：朋友、敌对、隶属、盟友）\n"
                    "- description: 关系详情\n\n"
                    "文本内容：\n{text}"
                )
            },
            "style": {
                "system": "你是文学评论家。请分析以下文本的写作风格。",
                "user": (
                    "请阅读以下文本，分析作者的文笔和写作风格。\n"
                    "返回JSON格式列表，包含一个汇总对象：\n"
                    "- name: '写作风格'\n"
                    "- content: 包含对用词、句式、修辞手法、叙事节奏和氛围营造的详细分析。\n\n"
                    "文本内容：\n{text}"
                )
            },
            "summary": {
                "system": "你是专业的小说编辑。请为以下文本撰写详细的【前情提要】总结。",
                "user": (
                    "{context_prompt}"
                    "请阅读以下文本，撰写一份详细的剧情回顾总结（前情提要），重点包含：\n"
                    "1. 关键事件的起因经过结果\n"
                    "2. 角色之间关系的变化\n"
                    "3. 重要的伏笔或信息\n\n"
                    "注意：如果有【前情提要】，你的总结应该衔接之前的内容，形成连贯叙述。\n"
                    "请返回JSON格式，包含一个对象：\n"
                    "- name: '剧情回顾'\n"
                    "- content: 详细的总结文本（500字以内），用于帮助AI理解之前的剧情。\n\n"
                    "文本内容：\n{text}"
                )
            },
            # 新增：内部使用的简短摘要生成（用于滚动上下文）
            "_internal_summary": {
                "system": "你是专业的编辑。请用简洁的语言总结以下章节的核心内容。",
                "user": (
                    "请用2-3句话总结以下文本的核心情节和关键信息，重点关注：\n"
                    "- 主要发生了什么事\n"
                    "- 哪些角色参与\n"
                    "- 有什么重要变化或发现\n\n"
                    "直接返回总结文本（不需要JSON格式）。\n\n"
                    "文本内容：\n{text}"
                )
            }
        }

        if analysis_type not in prompts:
            return None

        prompt_def = prompts[analysis_type]

        # 生成上下文提示
        context_prompt = ""
        if context and analysis_type != "style":  # style分析不需要上下文
            context_prompt = context.get_context_prompt(analysis_type)

        user_prompt = prompt_def["user"].format(
            text=chunk,
            context_prompt=context_prompt
        )

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response_text = self.ai_client.call_lm_studio_with_prompts(
                    api_url=config.get("api_url"),
                    model=config.get("model"),
                    api_key=config.get("api_key"),
                    system_prompt=prompt_def["system"],
                    user_prompt=user_prompt,
                    timeout=request_timeout
                )
                raw_result = self.ai_client.extract_json_from_text(response_text)
                if raw_result is not None:
                    normalized = self._normalize_result(raw_result, analysis_type)
                    if normalized is not None:
                        return normalized
                    last_error = "JSON schema not recognized"
                    if response_text:
                        logger.warning(
                            "JSON schema invalid for %s (attempt %d/%d). Response preview: %s",
                            analysis_type, attempt + 1, self.max_retries,
                            response_text[:200].replace('\n', ' ')
                        )
                else:
                    # JSON extraction failed
                    last_error = "JSON extraction returned None"
                    if response_text:
                        # Log first 200 chars for debugging
                        logger.warning(
                            "JSON extraction failed for %s (attempt %d/%d). Response preview: %s",
                            analysis_type, attempt + 1, self.max_retries,
                            response_text[:200].replace('\n', ' ')
                        )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "API error for %s (attempt %d/%d): %s",
                    analysis_type, attempt + 1, self.max_retries, last_error
                )

            # 指数退避重试（适用于异常和JSON解析失败）
            if attempt < self.max_retries - 1:
                wait_time = (2 ** attempt) * 0.5
                time.sleep(wait_time)

        logger.error("Analysis error (%s) after %d retries: %s", analysis_type, self.max_retries, last_error)
        return None

    def merge_results(self, all_results: List[Any], analysis_type: str) -> List[Any]:
        """
        Merges results from multiple chunks into a cohesive list.

        改进的合并策略：
        - 角色/设定：按名称去重，累加描述（多视角）
        - 关系：保留方向性（A→B 和 B→A 视为不同关系），相同方向的合并描述
        - 大纲/时间线：保留所有条目，按章节顺序
        """
        if not all_results:
            return []

        merged = {}
        ordered_keys = []  # 保持顺序

        for batch in all_results:
            if not isinstance(batch, list):
                continue
            for item in batch:
                if not isinstance(item, dict):
                    continue

                # 根据类型确定去重键
                key = self._get_merge_key(item, analysis_type)

                if not key:
                    continue

                if key not in merged:
                    merged[key] = item.copy()  # 使用副本避免修改原数据
                    merged[key]["_mentions"] = 1  # 记录出现次数
                    if analysis_type == "relationships":
                        chapter_titles = merged[key].get("chapter_titles")
                        if isinstance(chapter_titles, list):
                            if not merged[key].get("chapter_title") and chapter_titles:
                                merged[key]["chapter_title"] = chapter_titles[0]
                        else:
                            chapter_title = merged[key].get("chapter_title")
                            if chapter_title:
                                merged[key]["chapter_titles"] = [chapter_title]
                    ordered_keys.append(key)
                else:
                    existing = merged[key]
                    existing["_mentions"] = existing.get("_mentions", 1) + 1
                    self._merge_item_fields(existing, item, analysis_type)

        # 按出现顺序返回结果
        result = [merged[k] for k in ordered_keys]

        # 清理内部字段
        for item in result:
            item.pop("_mentions", None)

        return result

    def _get_merge_key(self, item: Dict, analysis_type: str) -> Optional[Tuple]:
        """根据分析类型生成合并键。"""
        if analysis_type == "relationships":
            # 保留方向性：(source, target, target_type) 作为键
            src = item.get("source", "").strip()
            tgt = item.get("target", "").strip()
            tgt_type = item.get("target_type", "character")
            if src and tgt:
                return (src, tgt, tgt_type)
        elif analysis_type in ("outline", "timeline"):
            # 大纲和时间线：使用名称+时间戳作为键（允许同名不同时间的事件）
            name = item.get("name", "").strip()
            timestamp = item.get("timestamp", "")
            if name:
                return (name, timestamp) if timestamp else (name, item.get("chapter_title", ""))
        else:
            # 角色、设定等：按名称去重
            name = item.get("name", "").strip()
            if name:
                return (name,)
        return None

    def _merge_item_fields(self, existing: Dict, new_item: Dict, analysis_type: str):
        """智能合并两个条目的字段。"""
        # 描述字段：累加不同的描述（多视角）
        desc_fields = ["description", "content", "action", "gap", "motive", "chaos", "bug"]
        for field in desc_fields:
            if field in new_item and new_item[field]:
                new_text = new_item[field].strip()
                if field not in existing or not existing[field]:
                    existing[field] = new_text
                elif new_text not in existing[field]:
                    # 累加新信息，避免重复
                    if len(existing[field]) + len(new_text) < 2000:  # 防止过长
                        existing[field] = f"{existing[field]}\n\n【补充】{new_text}"
                    elif len(new_text) > len(existing[field]):
                        # 如果新描述更长，替换
                        existing[field] = new_text

        # 标签字段：合并去重
        if "tags" in new_item and isinstance(new_item["tags"], list):
            if "tags" not in existing:
                existing["tags"] = []
            existing["tags"] = list(set(existing["tags"] + new_item["tags"]))

        # 角色列表字段：合并去重
        if "characters" in new_item and isinstance(new_item["characters"], list):
            if "characters" not in existing:
                existing["characters"] = []
            existing["characters"] = list(set(existing["characters"] + new_item["characters"]))

        # 关系特定：合并关系描述
        if analysis_type == "relationships":
            if "label" in new_item and new_item["label"]:
                new_label = new_item["label"].strip()
                if "label" not in existing or not existing["label"]:
                    existing["label"] = new_label
                elif new_label not in existing["label"]:
                    existing["label"] = f"{existing['label']}、{new_label}"
            chapter_titles = []
            existing_titles = existing.get("chapter_titles")
            if isinstance(existing_titles, list):
                chapter_titles.extend([t for t in existing_titles if t])
            elif existing.get("chapter_title"):
                chapter_titles.append(existing.get("chapter_title"))

            new_titles = new_item.get("chapter_titles")
            if isinstance(new_titles, list):
                for title in new_titles:
                    if title and title not in chapter_titles:
                        chapter_titles.append(title)
            elif new_item.get("chapter_title"):
                title = new_item.get("chapter_title")
                if title and title not in chapter_titles:
                    chapter_titles.append(title)

            if chapter_titles:
                existing["chapter_titles"] = chapter_titles
                if not existing.get("chapter_title"):
                    existing["chapter_title"] = chapter_titles[0]

    # --- 长上下文支持：滚动摘要与累积上下文 ---

    def generate_chapter_summary(
        self,
        chunk: str,
        chapter_title: str,
        config: Dict
    ) -> Optional[str]:
        """
        为单个章节生成简短摘要（用于滚动上下文）。

        Returns:
            简短的章节摘要文本，或 None（如果失败）
        """
        prompt_def = {
            "system": "你是专业的编辑。请用简洁的语言总结以下章节的核心内容。",
            "user": (
                f"章节标题：{chapter_title}\n\n"
                "请用2-3句话总结以下文本的核心情节和关键信息，重点关注：\n"
                "- 主要发生了什么事\n"
                "- 哪些角色参与\n"
                "- 有什么重要变化或发现\n\n"
                "直接返回总结文本（不需要JSON格式）。\n\n"
                f"文本内容：\n{chunk[:3000]}"  # 限制长度避免token超限
            )
        }

        try:
            response_text = self.ai_client.call_lm_studio_with_prompts(
                api_url=config.get("api_url"),
                model=config.get("model"),
                api_key=config.get("api_key"),
                system_prompt=prompt_def["system"],
                user_prompt=prompt_def["user"]
            )
            # 简短摘要不需要JSON解析，直接返回文本
            summary = response_text.strip() if response_text else None
            if summary:
                self.set_cached_summary(self._compute_hash(chunk), summary)
            return summary
        except Exception as e:
            print(f"Error generating chapter summary: {e}")
            return None

    def update_context_from_results(
        self,
        context: AnalysisContext,
        results: Dict[str, List[Any]],
        chapter_title: str,
        chapter_summary: Optional[str] = None
    ):
        """
        根据分析结果更新累积上下文。

        Args:
            context: 要更新的上下文对象
            results: 当前章节的分析结果 {analysis_type: [items]}
            chapter_title: 章节标题
            chapter_summary: 可选的章节摘要（如果没有则从results中提取）
        """
        # 1. 从角色分析结果中提取角色名
        if "characters" in results:
            char_results = results["characters"]
            if isinstance(char_results, list):
                for batch in char_results:
                    if isinstance(batch, list):
                        for item in batch:
                            if isinstance(item, dict) and "name" in item:
                                context.add_characters([item["name"]])
                    elif isinstance(batch, dict) and "name" in batch:
                        context.add_characters([batch["name"]])

        # 2. 从设定分析结果中提取设定名词
        if "wiki" in results:
            wiki_results = results["wiki"]
            if isinstance(wiki_results, list):
                for batch in wiki_results:
                    if isinstance(batch, list):
                        for item in batch:
                            if isinstance(item, dict) and "name" in item:
                                context.add_entities([item["name"]])
                    elif isinstance(batch, dict) and "name" in batch:
                        context.add_entities([batch["name"]])

        # 3. 从大纲结果中提取参与角色
        if "outline" in results:
            outline_results = results["outline"]
            if isinstance(outline_results, list):
                for batch in outline_results:
                    if isinstance(batch, list):
                        for item in batch:
                            if isinstance(item, dict) and "characters" in item:
                                chars = item["characters"]
                                if isinstance(chars, list):
                                    context.add_characters(chars)
                    elif isinstance(batch, dict) and "characters" in batch:
                        chars = batch["characters"]
                        if isinstance(chars, list):
                            context.add_characters(chars)

        # 3b. 从关系结果中提取角色（避免未勾选角色分析时遗漏）
        if "relationships" in results:
            rel_results = results["relationships"]
            if isinstance(rel_results, list):
                for batch in rel_results:
                    if isinstance(batch, list):
                        for item in batch:
                            if isinstance(item, dict):
                                src = item.get("source")
                                tgt = item.get("target")
                                tgt_type = item.get("target_type", "character")
                                if src:
                                    context.add_characters([src])
                                if tgt and str(tgt_type).lower() == "character":
                                    context.add_characters([tgt])
                    elif isinstance(batch, dict):
                        src = batch.get("source")
                        tgt = batch.get("target")
                        tgt_type = batch.get("target_type", "character")
                        if src:
                            context.add_characters([src])
                        if tgt and str(tgt_type).lower() == "character":
                            context.add_characters([tgt])

        # 4. 更新滚动摘要
        if chapter_summary:
            context.add_chapter_summary(chapter_title, chapter_summary)
        elif "summary" in results:
            # 尝试从summary结果中提取
            summary_results = results["summary"]
            if isinstance(summary_results, list) and summary_results:
                for batch in summary_results:
                    if isinstance(batch, list) and batch:
                        for item in batch:
                            if isinstance(item, dict) and "content" in item:
                                context.add_chapter_summary(chapter_title, item["content"][:500])
                                break
                    elif isinstance(batch, dict) and "content" in batch:
                        context.add_chapter_summary(chapter_title, batch["content"][:500])
                    break

    def create_analysis_context(self) -> AnalysisContext:
        """创建新的分析上下文。"""
        return AnalysisContext()

    def export_context(self, context: AnalysisContext) -> Dict:
        """导出上下文用于持久化。"""
        return context.to_dict()

    def import_context(self, data: Dict) -> AnalysisContext:
        """从字典导入上下文。"""
        return AnalysisContext.from_dict(data)
