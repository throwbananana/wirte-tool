from typing import Any, Dict, List, Optional


class ProjectOutlineService:
    """Pure outline traversal and normalization helpers."""

    def __init__(self, project_manager):
        self.project_manager = project_manager

    def clean_temp_attrs_iterative(self, root: dict) -> None:
        if root is None:
            return

        stack = [root]
        while stack:
            node = stack.pop()
            node.pop("_collapsed", None)
            for child in node.get("children", []):
                stack.append(child)

    def ensure_outline_uids_iterative(self, root: dict) -> None:
        if root is None:
            return

        stack = [root]
        while stack:
            node = stack.pop()
            if "uid" not in node or not node["uid"]:
                node["uid"] = self.project_manager._gen_uid()
            for child in node.get("children", []):
                stack.append(child)

    def find_node_by_uid(self, root: dict, target_uid: str) -> Optional[dict]:
        if root is None or not target_uid:
            return None

        stack = [root]
        while stack:
            node = stack.pop()
            if node.get("uid") == target_uid:
                return node
            for child in node.get("children", []):
                stack.append(child)
        return None

    def find_parent_of_node_by_uid(self, root: dict, target_node_uid: str) -> Optional[dict]:
        if root is None or not target_node_uid:
            return None

        stack = [root]
        while stack:
            node = stack.pop()
            for child in node.get("children", []):
                if child.get("uid") == target_node_uid:
                    return node
                stack.append(child)
        return None

    def get_outline_path(self, target_uid: str, separator: str = " > ") -> str:
        if not target_uid:
            return ""

        root = self.project_manager.get_outline()
        if root is None:
            return ""

        stack = [(root, [])]
        while stack:
            node, path = stack.pop()
            current_path = path + [node.get("name", "")]
            if node.get("uid") == target_uid:
                return separator.join(current_path)

            for child in reversed(node.get("children", [])):
                stack.append((child, current_path))

        return ""


class ProjectSceneService:
    """Cross-links between scenes, outline nodes, and characters."""

    def __init__(self, project_manager):
        self.project_manager = project_manager

    def get_scenes_by_outline_uid(self, outline_uid: str) -> List[tuple[int, dict]]:
        result = []
        for index, scene in enumerate(self.project_manager.get_scenes()):
            if scene.get("outline_ref_id") == outline_uid:
                result.append((index, scene))
        return result

    def get_outline_node_for_scene(self, scene_index: int) -> Optional[dict]:
        scenes = self.project_manager.get_scenes()
        if 0 <= scene_index < len(scenes):
            outline_uid = scenes[scene_index].get("outline_ref_id")
            if outline_uid:
                return self.project_manager.find_node_by_uid(
                    self.project_manager.get_outline(),
                    outline_uid,
                )
        return None

    def get_outline_scene_links(self) -> Dict[str, List[int]]:
        links: Dict[str, List[int]] = {}
        for index, scene in enumerate(self.project_manager.get_scenes()):
            outline_uid = scene.get("outline_ref_id")
            if not outline_uid:
                continue
            links.setdefault(outline_uid, []).append(index)
        return links

    def link_scene_to_outline(self, scene_index: int, outline_uid: str) -> bool:
        scenes = self.project_manager.get_scenes()
        if not (0 <= scene_index < len(scenes)):
            return False

        outline_node = self.project_manager.find_node_by_uid(
            self.project_manager.get_outline(),
            outline_uid,
        )
        if not outline_node:
            return False

        scenes[scene_index]["outline_ref_id"] = outline_uid
        scenes[scene_index]["outline_ref_path"] = self.project_manager.get_outline_path(outline_uid)
        self.project_manager.mark_modified()
        return True

    def unlink_scene_from_outline(self, scene_index: int) -> bool:
        scenes = self.project_manager.get_scenes()
        if not (0 <= scene_index < len(scenes)):
            return False

        scenes[scene_index]["outline_ref_id"] = ""
        scenes[scene_index]["outline_ref_path"] = ""
        self.project_manager.mark_modified()
        return True

    def get_characters_in_scene(self, scene_index: int) -> List[str]:
        scenes = self.project_manager.get_scenes()
        if 0 <= scene_index < len(scenes):
            return scenes[scene_index].get("characters", [])
        return []

    def get_scenes_with_character(self, character_name: str) -> List[tuple[int, dict]]:
        result = []
        for index, scene in enumerate(self.project_manager.get_scenes()):
            if character_name in scene.get("characters", []):
                result.append((index, scene))
        return result

    def get_scenes_with_character_pair(self, char_a: str, char_b: str) -> List[tuple[int, dict]]:
        result = []
        for index, scene in enumerate(self.project_manager.get_scenes()):
            characters = scene.get("characters", [])
            if char_a in characters and char_b in characters:
                result.append((index, scene))
        return result

    def get_character_scene_matrix(self) -> Dict[str, List[int]]:
        matrix: Dict[str, List[int]] = {}
        for char in self.project_manager.get_characters():
            name = char.get("name")
            if name:
                matrix[name] = []

        for index, scene in enumerate(self.project_manager.get_scenes()):
            for char_name in scene.get("characters", []):
                if char_name in matrix:
                    matrix[char_name].append(index)

        return matrix

    def get_scenes_containing_text(self, query: str) -> List[tuple[int, dict]]:
        if not query:
            return []

        query_lower = query.lower()
        result = []
        for index, scene in enumerate(self.project_manager.get_scenes()):
            name = scene.get("name", "").lower()
            content = scene.get("content", "").lower()
            if query_lower in name or query_lower in content:
                result.append((index, scene))
        return result


class ProjectSearchService:
    """Higher-level analytical queries spanning multiple modules."""

    def __init__(self, project_manager):
        self.project_manager = project_manager

    def auto_generate_relationships(self, threshold: int = 1) -> int:
        matrix = {}

        for scene in self.project_manager.get_scenes():
            characters = sorted(set(scene.get("characters", [])))
            for index in range(len(characters)):
                for peer_index in range(index + 1, len(characters)):
                    pair = (characters[index], characters[peer_index])
                    matrix[pair] = matrix.get(pair, 0) + 1

        relationships = self.project_manager.get_relationships()
        existing_links = set()
        for link in relationships.get("relationship_links", []):
            pair = tuple(sorted([link["source"], link["target"]]))
            existing_links.add(pair)

        added_count = 0
        for pair, count in matrix.items():
            if count < threshold or pair in existing_links:
                continue

            relationships["relationship_links"].append(
                {
                    "source": pair[0],
                    "target": pair[1],
                    "label": f"共现 {count} 次",
                    "color": "#666666",
                }
            )
            existing_links.add(pair)
            added_count += 1

        if added_count > 0:
            self.project_manager.mark_modified("relationships")

        return added_count

    def search_all(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        if not query:
            return []

        results = []
        normalized_query = query if case_sensitive else query.lower()

        def check(text: str) -> bool:
            source = text if case_sensitive else text.lower()
            return normalized_query in source

        def get_context(content: str) -> str:
            haystack = content if case_sensitive else content.lower()
            index = haystack.find(normalized_query)
            start = max(0, index - 10)
            end = min(len(content), index + 20)
            return content[start:end].replace("\n", " ") + "..."

        for index, scene in enumerate(self.project_manager.get_scenes()):
            name = scene.get("name", "")
            content = scene.get("content", "")
            if check(name):
                results.append(
                    {
                        "type": "scene",
                        "index": index,
                        "name": name,
                        "context": "(标题匹配)",
                        "match_field": "name",
                    }
                )
            elif check(content):
                results.append(
                    {
                        "type": "scene",
                        "index": index,
                        "name": name,
                        "context": get_context(content),
                        "match_field": "content",
                    }
                )

        for index, char in enumerate(self.project_manager.get_characters()):
            name = char.get("name", "")
            description = char.get("description", "")
            if check(name):
                results.append(
                    {
                        "type": "character",
                        "index": index,
                        "name": name,
                        "context": "(姓名匹配)",
                        "match_field": "name",
                    }
                )
            elif check(description):
                results.append(
                    {
                        "type": "character",
                        "index": index,
                        "name": name,
                        "context": description[:30] + "...",
                        "match_field": "description",
                    }
                )

        for index, entry in enumerate(self.project_manager.get_world_entries()):
            name = entry.get("name", "")
            content = entry.get("content", "")
            if check(name):
                results.append(
                    {
                        "type": "wiki",
                        "index": index,
                        "name": name,
                        "context": "(词条名匹配)",
                        "match_field": "name",
                    }
                )
            elif check(content):
                results.append(
                    {
                        "type": "wiki",
                        "index": index,
                        "name": name,
                        "context": get_context(content),
                        "match_field": "content",
                    }
                )

        root = self.project_manager.get_outline()
        if root:
            stack = [root]
            while stack:
                node = stack.pop()
                uid = node.get("uid")
                name = node.get("name", "")
                content = node.get("content", "")

                if check(name):
                    results.append(
                        {
                            "type": "outline",
                            "index": uid,
                            "name": name,
                            "context": "(节点名匹配)",
                            "match_field": "name",
                        }
                    )
                elif check(content):
                    results.append(
                        {
                            "type": "outline",
                            "index": uid,
                            "name": name,
                            "context": get_context(content),
                            "match_field": "content",
                        }
                    )

                for child in node.get("children", []):
                    stack.append(child)

        return results
