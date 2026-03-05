"""
POV/Perspective management utilities.

Manages POV-related operations across the project including:
- POV character tracking
- Narrative voice management
- Perspective conflict detection
- Knowledge timeline construction
- Reliability scoring

Usage:
    from writer_app.core.pov_manager import POVManager

    pov = POVManager(project_manager)
    scenes = pov.get_scenes_by_pov("char_uid_123")
    conflicts = pov.detect_perspective_conflicts()
"""
from typing import List, Dict, Tuple, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class NarrativeVoice(Enum):
    """Narrative voice/perspective types."""
    FIRST = "first"                    # 第一人称 "我"
    SECOND = "second"                  # 第二人称 "你"
    THIRD_LIMITED = "third_limited"    # 第三人称限制视角
    THIRD_OMNISCIENT = "third_omniscient"  # 第三人称全知视角

    @classmethod
    def get_display_name(cls, voice: str) -> str:
        """Get display name for a narrative voice."""
        names = {
            "first": "第一人称",
            "second": "第二人称",
            "third_limited": "第三人称（限制视角）",
            "third_omniscient": "第三人称（全知视角）"
        }
        return names.get(voice, voice)

    @classmethod
    def get_description(cls, voice: str) -> str:
        """Get description for a narrative voice."""
        descriptions = {
            "first": "使用「我」叙述，读者只能知道叙述者所见所感",
            "second": "使用「你」叙述，读者被置于角色位置",
            "third_limited": "使用「他/她」叙述，但限于一个角色的视角",
            "third_omniscient": "全知视角，可以描述任何角色的内心"
        }
        return descriptions.get(voice, "")


@dataclass
class PerspectiveConflict:
    """Represents a detected perspective conflict."""
    scene_index: int
    scene_uid: str
    scene_name: str
    conflict_type: str
    description: str
    severity: str  # "error", "warning", "info"


@dataclass
class KnowledgeEvent:
    """Represents a knowledge acquisition event for a character."""
    scene_index: int
    scene_uid: str
    learned_info: str
    source: str  # "direct", "told", "observed", "inferred"


class POVManager:
    """Manages POV-related operations across the project."""

    def __init__(self, project_manager):
        """
        Initialize the POV manager.

        Args:
            project_manager: The ProjectManager instance
        """
        self.pm = project_manager

    def get_scenes_by_pov(self, character_uid: str) -> List[Tuple[int, dict]]:
        """
        Get all scenes from a specific character's POV.

        Args:
            character_uid: UID of the POV character

        Returns:
            List of (scene_index, scene_data) tuples
        """
        result = []
        for i, scene in enumerate(self.pm.get_scenes()):
            if scene.get("pov_character") == character_uid:
                result.append((i, scene))
        return result

    def get_pov_characters(self) -> List[dict]:
        """
        Get all characters used as POV narrators.

        Returns:
            List of character dicts that have been used as POV
        """
        # Collect UIDs of characters used as POV
        pov_uids: Set[str] = set()
        for scene in self.pm.get_scenes():
            pov_char = scene.get("pov_character")
            if pov_char:
                pov_uids.add(pov_char)

        # Also include characters explicitly marked as narrators
        for char in self.pm.get_characters():
            if char.get("is_narrator"):
                pov_uids.add(char.get("uid", ""))

        # Get full character data
        result = []
        for char in self.pm.get_characters():
            if char.get("uid") in pov_uids:
                result.append(char)

        return result

    def get_narrator_characters(self) -> List[dict]:
        """
        Get all characters marked as potential narrators.

        Returns:
            List of character dicts marked as is_narrator=True
        """
        return [c for c in self.pm.get_characters() if c.get("is_narrator")]

    def get_scenes_without_pov(self) -> List[Tuple[int, dict]]:
        """
        Get all scenes that don't have a POV character assigned.

        Returns:
            List of (scene_index, scene_data) tuples
        """
        result = []
        for i, scene in enumerate(self.pm.get_scenes()):
            if not scene.get("pov_character"):
                result.append((i, scene))
        return result

    def get_pov_statistics(self) -> Dict[str, Any]:
        """
        Get POV usage statistics.

        Returns:
            Dict with POV statistics:
            {
                "total_scenes": int,
                "scenes_with_pov": int,
                "scenes_without_pov": int,
                "pov_distribution": {char_uid: count},
                "voice_distribution": {voice: count},
                "avg_reliability": float
            }
        """
        scenes = self.pm.get_scenes()
        total = len(scenes)
        with_pov = 0
        pov_dist: Dict[str, int] = {}
        voice_dist: Dict[str, int] = {}
        reliability_sum = 0.0

        for scene in scenes:
            pov = scene.get("pov_character")
            voice = scene.get("narrative_voice", "third_limited")
            reliability = scene.get("narrator_reliability", 1.0)

            reliability_sum += reliability
            voice_dist[voice] = voice_dist.get(voice, 0) + 1

            if pov:
                with_pov += 1
                pov_dist[pov] = pov_dist.get(pov, 0) + 1

        return {
            "total_scenes": total,
            "scenes_with_pov": with_pov,
            "scenes_without_pov": total - with_pov,
            "pov_distribution": pov_dist,
            "voice_distribution": voice_dist,
            "avg_reliability": reliability_sum / total if total > 0 else 1.0
        }

    def detect_perspective_conflicts(self) -> List[PerspectiveConflict]:
        """
        Detect logical conflicts in POV across all scenes.

        Checks for:
        - Third-person limited describing non-POV character's thoughts
        - First-person describing events the narrator couldn't witness
        - Inconsistent knowledge state (character knows something before learning)
        - Unreliable narrator contradictions

        Returns:
            List of PerspectiveConflict objects
        """
        conflicts: List[PerspectiveConflict] = []
        scenes = self.pm.get_scenes()
        characters = {c.get("uid"): c for c in self.pm.get_characters()}

        for i, scene in enumerate(scenes):
            pov_uid = scene.get("pov_character")
            voice = scene.get("narrative_voice", "third_limited")
            content = scene.get("content", "")
            scene_chars = scene.get("characters", [])

            if not pov_uid:
                continue

            pov_char = characters.get(pov_uid)
            if not pov_char:
                continue

            pov_name = pov_char.get("name", "")

            # Check 1: Limited voice describing other characters' internal states
            if voice in ("first", "third_limited"):
                for char_name in scene_chars:
                    if char_name == pov_name:
                        continue

                    # Look for internal state indicators
                    internal_patterns = [
                        f"{char_name}想着",
                        f"{char_name}心想",
                        f"{char_name}感到",
                        f"{char_name}意识到",
                        f"{char_name}知道",
                        f"{char_name}的内心",
                    ]

                    for pattern in internal_patterns:
                        if pattern in content:
                            conflicts.append(PerspectiveConflict(
                                scene_index=i,
                                scene_uid=scene.get("uid", ""),
                                scene_name=scene.get("name", ""),
                                conflict_type="internal_state_violation",
                                description=f"限制视角下描述了「{char_name}」的内心状态",
                                severity="warning"
                            ))
                            break

            # Check 2: First person but POV character not in scene
            if voice == "first" and pov_name not in scene_chars:
                conflicts.append(PerspectiveConflict(
                    scene_index=i,
                    scene_uid=scene.get("uid", ""),
                    scene_name=scene.get("name", ""),
                    conflict_type="narrator_absent",
                    description=f"第一人称叙述者「{pov_name}」未出现在场景中",
                    severity="error"
                ))

            # Check 3: Very low reliability with factual statements
            reliability = scene.get("narrator_reliability", 1.0)
            if reliability < 0.5:
                # Low reliability narrator making absolute statements
                absolute_patterns = ["一定是", "肯定是", "绝对是", "确实是", "毫无疑问"]
                for pattern in absolute_patterns:
                    if pattern in content:
                        conflicts.append(PerspectiveConflict(
                            scene_index=i,
                            scene_uid=scene.get("uid", ""),
                            scene_name=scene.get("name", ""),
                            conflict_type="unreliable_certainty",
                            description=f"不可靠叙述者使用了确定性表达「{pattern}」",
                            severity="info"
                        ))
                        break

        return conflicts

    def get_knowledge_timeline(self, character_uid: str) -> List[KnowledgeEvent]:
        """
        Build timeline of what a character learns and when.

        Args:
            character_uid: UID of the character to track

        Returns:
            List of KnowledgeEvent objects in scene order
        """
        # This is a simplified implementation
        # A full implementation would analyze scene content for information reveals
        events: List[KnowledgeEvent] = []

        character = None
        for c in self.pm.get_characters():
            if c.get("uid") == character_uid:
                character = c
                break

        if not character:
            return events

        char_name = character.get("name", "")
        knowledge_scope = character.get("knowledge_scope", [])

        # Track scenes where character appears
        for i, scene in enumerate(self.pm.get_scenes()):
            if char_name not in scene.get("characters", []):
                continue

            # Character is present - they learn what happens in this scene
            events.append(KnowledgeEvent(
                scene_index=i,
                scene_uid=scene.get("uid", ""),
                learned_info=f"场景 {scene.get('name', '')} 中的事件",
                source="direct"
            ))

        return events

    def calculate_reliability_score(self, scene_index: int) -> float:
        """
        Calculate effective reliability based on multiple factors.

        Args:
            scene_index: Index of the scene

        Returns:
            Effective reliability score (0.0 - 1.0)
        """
        scenes = self.pm.get_scenes()
        if scene_index < 0 or scene_index >= len(scenes):
            return 1.0

        scene = scenes[scene_index]
        base_reliability = scene.get("narrator_reliability", 1.0)

        # Get POV character
        pov_uid = scene.get("pov_character")
        if not pov_uid:
            return base_reliability

        # Find character
        pov_char = None
        for c in self.pm.get_characters():
            if c.get("uid") == pov_uid:
                pov_char = c
                break

        if not pov_char:
            return base_reliability

        # Factor in perception bias
        perception_bias = pov_char.get("perception_bias", {})
        scene_chars = scene.get("characters", [])

        # If characters with high bias are present, reduce reliability
        bias_penalty = 0.0
        for char_uid, bias in perception_bias.items():
            # Find character name from UID
            for c in self.pm.get_characters():
                if c.get("uid") == char_uid and c.get("name") in scene_chars:
                    # Bias score: -100 to +100, high absolute value = less reliable
                    bias_penalty += abs(bias) / 100 * 0.1

        effective_reliability = max(0.0, base_reliability - bias_penalty)
        return effective_reliability

    def get_pov_transitions(self) -> List[Dict[str, Any]]:
        """
        Get list of POV transitions between scenes.

        Returns:
            List of transition dicts:
            {
                "from_scene_index": int,
                "to_scene_index": int,
                "from_pov": str (character UID),
                "to_pov": str (character UID),
                "from_voice": str,
                "to_voice": str
            }
        """
        transitions = []
        scenes = self.pm.get_scenes()

        prev_pov = None
        prev_voice = None
        prev_index = -1

        for i, scene in enumerate(scenes):
            pov = scene.get("pov_character")
            voice = scene.get("narrative_voice")

            if prev_pov is not None and (pov != prev_pov or voice != prev_voice):
                transitions.append({
                    "from_scene_index": prev_index,
                    "to_scene_index": i,
                    "from_pov": prev_pov,
                    "to_pov": pov,
                    "from_voice": prev_voice,
                    "to_voice": voice
                })

            prev_pov = pov
            prev_voice = voice
            prev_index = i

        return transitions

    def suggest_pov_for_scene(self, scene_index: int) -> Optional[str]:
        """
        Suggest a POV character for a scene based on context.

        Args:
            scene_index: Index of the scene

        Returns:
            Suggested character UID or None
        """
        scenes = self.pm.get_scenes()
        if scene_index < 0 or scene_index >= len(scenes):
            return None

        scene = scenes[scene_index]
        scene_chars = scene.get("characters", [])

        if not scene_chars:
            return None

        # Get character with most narrative focus (most scenes as POV nearby)
        char_pov_counts: Dict[str, int] = {}

        # Look at surrounding scenes
        window = 3
        for i in range(max(0, scene_index - window), min(len(scenes), scene_index + window + 1)):
            if i == scene_index:
                continue
            pov = scenes[i].get("pov_character")
            if pov:
                char_pov_counts[pov] = char_pov_counts.get(pov, 0) + 1

        # Map character UIDs to names
        char_uid_map = {c.get("name"): c.get("uid") for c in self.pm.get_characters()}

        # Find the best match among scene characters
        best_uid = None
        best_count = 0

        for char_name in scene_chars:
            char_uid = char_uid_map.get(char_name)
            if char_uid:
                count = char_pov_counts.get(char_uid, 0)
                if count > best_count:
                    best_count = count
                    best_uid = char_uid

        # If no nearby POV found, suggest the first character
        if not best_uid and scene_chars:
            best_uid = char_uid_map.get(scene_chars[0])

        return best_uid

    def get_character_pov_summary(self, character_uid: str) -> Dict[str, Any]:
        """
        Get a summary of POV usage for a specific character.

        Args:
            character_uid: UID of the character

        Returns:
            Summary dict with POV statistics for this character
        """
        scenes = self.get_scenes_by_pov(character_uid)
        total_words = 0
        voice_counts: Dict[str, int] = {}
        reliability_sum = 0.0

        for _, scene in scenes:
            content = scene.get("content", "")
            total_words += len(content)

            voice = scene.get("narrative_voice", "third_limited")
            voice_counts[voice] = voice_counts.get(voice, 0) + 1

            reliability_sum += scene.get("narrator_reliability", 1.0)

        scene_count = len(scenes)

        return {
            "scene_count": scene_count,
            "total_words": total_words,
            "voice_distribution": voice_counts,
            "avg_reliability": reliability_sum / scene_count if scene_count > 0 else 1.0
        }
