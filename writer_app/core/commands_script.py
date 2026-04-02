import json

from writer_app.core.commands_base import Command
from writer_app.core.event_bus import Events, get_event_bus


class AddCharacterCommand(Command):
    def __init__(self, project_manager, character_data, description="添加角色"):
        super().__init__(description)
        self.project_manager = project_manager
        self.character_data = json.loads(json.dumps(character_data))
        self.added_char_index = -1

    def execute(self):
        characters = self.project_manager.get_characters()
        characters.append(self.character_data)
        self.added_char_index = len(characters) - 1
        
        # Sync to Wiki
        char_name = self.character_data.get("name", "")
        if char_name:
            self.project_manager.sync_to_wiki(char_name, "人物", "add", content=self.character_data.get("description", ""))
            
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.CHARACTER_ADDED, char_index=self.added_char_index, char_name=char_name)
        return True

    def undo(self):
        characters = self.project_manager.get_characters()
        if 0 <= self.added_char_index < len(characters) and id(characters[self.added_char_index]) == id(self.character_data): # Compare object IDs
            del characters[self.added_char_index]
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.CHARACTER_DELETED, char_index=self.added_char_index)
            return True
        return False

class DeleteCharacterCommand(Command):
    def __init__(self, project_manager, character_index, character_data, description="删除角色"):
        super().__init__(description)
        self.project_manager = project_manager
        self.character_index = character_index
        self.deleted_character_data = json.loads(json.dumps(character_data))

    def execute(self):
        characters = self.project_manager.get_characters()
        if 0 <= self.character_index < len(characters):
            # Command should operate on a copy of data, not modify directly in init
            # The character is removed by index. This command should not store
            # a reference to the actual object if execute is called multiple times (redo)
            # Just verify index and remove
            char_name = characters[self.character_index].get("name", "")
            
            del characters[self.character_index]

            # Sync to Wiki (Mark as deleted)
            if char_name:
                self.project_manager.sync_to_wiki(char_name, "人物", "delete")

            self.project_manager.mark_modified()
            get_event_bus().publish(Events.CHARACTER_DELETED, char_index=self.character_index, char_name=char_name)
            return True
        return False

    def undo(self):
        characters = self.project_manager.get_characters()
        characters.insert(self.character_index, self.deleted_character_data)
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.CHARACTER_ADDED, char_index=self.character_index)
        return True

class EditCharacterCommand(Command):
    def __init__(self, project_manager, character_index, old_data, new_data, description="编辑角色"):
        super().__init__(description)
        self.project_manager = project_manager
        self.character_index = character_index
        self.old_data = json.loads(json.dumps(old_data))
        self.new_data = json.loads(json.dumps(new_data))
        self._changed_scenes = {}
        self._changed_relationship_links = []
        self._changed_relationship_layout = None
        self._changed_faction_members = []

    def execute(self):
        characters = self.project_manager.get_characters()
        if 0 <= self.character_index < len(characters):
            self._changed_scenes = {}
            self._changed_relationship_links = []
            self._changed_relationship_layout = None
            self._changed_faction_members = []
            old_name = self.old_data.get("name")
            new_name = self.new_data.get("name")
            characters[self.character_index].update(self.new_data) # Update in place

            # Propagate rename to scenes' character references
            if old_name and new_name and old_name != new_name:
                scenes = self.project_manager.get_scenes()
                for idx, scene in enumerate(scenes):
                    if old_name in scene.get("characters", []):
                        self._changed_scenes[idx] = list(scene.get("characters", []))
                        scene["characters"] = [
                            (new_name if n == old_name else n) for n in scene.get("characters", [])
                        ]

                # Update relationship links and layout
                rels = self.project_manager.get_relationships()
                for i, link in enumerate(rels.get("relationship_links", [])):
                    src = link.get("source")
                    tgt = link.get("target")
                    if src == old_name or tgt == old_name:
                        self._changed_relationship_links.append((i, src, tgt))
                        if src == old_name:
                            link["source"] = new_name
                        if tgt == old_name:
                            link["target"] = new_name

                layout = rels.get("character_layout", {})
                if old_name in layout:
                    self._changed_relationship_layout = (old_name, layout.get(old_name))
                    layout[new_name] = layout.pop(old_name)

                # Update faction members
                factions = self.project_manager.get_factions()
                for f_idx, faction in enumerate(factions):
                    members = faction.get("members", [])
                    for m_idx, member in enumerate(members):
                        if member.get("char_name") == old_name:
                            self._changed_faction_members.append((f_idx, m_idx, old_name))
                            member["char_name"] = new_name
            
            # Sync to Wiki
            if old_name and new_name:
                self.project_manager.sync_to_wiki(
                    new_name, "人物", "update", 
                    content=self.new_data.get("description", ""), 
                    old_name=old_name
                )
                
            self.project_manager.mark_modified()
            get_event_bus().publish(
                Events.CHARACTER_UPDATED,
                char_index=self.character_index,
                char_name=new_name,
                old_name=old_name
            )
            return True
        return False

    def undo(self):
        characters = self.project_manager.get_characters()
        if 0 <= self.character_index < len(characters):
            characters[self.character_index].update(self.old_data) # Revert to old
            if self._changed_scenes:
                scenes = self.project_manager.get_scenes()
                for idx, old_list in self._changed_scenes.items():
                    if 0 <= idx < len(scenes):
                        scenes[idx]["characters"] = old_list
            if self._changed_relationship_links:
                rels = self.project_manager.get_relationships()
                for i, src, tgt in self._changed_relationship_links:
                    if 0 <= i < len(rels.get("relationship_links", [])):
                        rels["relationship_links"][i]["source"] = src
                        rels["relationship_links"][i]["target"] = tgt
            if self._changed_relationship_layout:
                old_name, pos = self._changed_relationship_layout
                rels = self.project_manager.get_relationships()
                layout = rels.get("character_layout", {})
                for key in list(layout.keys()):
                    if key == self.new_data.get("name"):
                        layout.pop(key, None)
                layout[old_name] = pos
            if self._changed_faction_members:
                factions = self.project_manager.get_factions()
                for f_idx, m_idx, old_name in self._changed_faction_members:
                    if 0 <= f_idx < len(factions):
                        members = factions[f_idx].get("members", [])
                        if 0 <= m_idx < len(members):
                            members[m_idx]["char_name"] = old_name
            self.project_manager.mark_modified()
            get_event_bus().publish(
                Events.CHARACTER_UPDATED,
                char_index=self.character_index,
                char_name=self.old_data.get("name", ""),
                old_name=self.new_data.get("name", "")
            )
            return True
        return False

class AddCharacterEventCommand(Command):
    def __init__(self, project_manager, char_name, event_data, description="添加人物事件"):
        super().__init__(description)
        self.project_manager = project_manager
        self.char_name = char_name
        self.event_data = json.loads(json.dumps(event_data))
        self.added_event_uid = None
        self.added_event_index = -1

    def execute(self):
        char = self.project_manager.get_character_by_name(self.char_name)
        if not char:
            return False
        events = char.setdefault("events", [])
        if "uid" not in self.event_data or not self.event_data["uid"]:
            self.event_data["uid"] = self.project_manager._gen_uid()
        events.append(self.event_data)
        self.added_event_uid = self.event_data["uid"]
        self.added_event_index = len(events) - 1
        self.project_manager.mark_modified("script")
        get_event_bus().publish(Events.CHARACTER_UPDATED, char_name=self.char_name)
        return True

    def undo(self):
        char = self.project_manager.get_character_by_name(self.char_name)
        if not char:
            return False
        events = char.get("events", [])
        removed = False
        if 0 <= self.added_event_index < len(events):
            if events[self.added_event_index].get("uid") == self.added_event_uid:
                del events[self.added_event_index]
                removed = True
        if not removed and self.added_event_uid:
            original_len = len(events)
            events[:] = [e for e in events if e.get("uid") != self.added_event_uid]
            removed = len(events) < original_len
        if removed:
            self.project_manager.mark_modified("script")
            get_event_bus().publish(Events.CHARACTER_UPDATED, char_name=self.char_name)
            return True
        return False

class EditCharacterEventCommand(Command):
    def __init__(self, project_manager, char_name, event_index, old_data, new_data, description="编辑人物事件"):
        super().__init__(description)
        self.project_manager = project_manager
        self.char_name = char_name
        self.event_index = event_index
        self.old_data = json.loads(json.dumps(old_data))
        self.new_data = json.loads(json.dumps(new_data))

    def execute(self):
        char = self.project_manager.get_character_by_name(self.char_name)
        if not char:
            return False
        events = char.get("events", [])
        if 0 <= self.event_index < len(events):
            events[self.event_index].update(self.new_data)
            self.project_manager.mark_modified("script")
            get_event_bus().publish(Events.CHARACTER_UPDATED, char_name=self.char_name)
            return True
        return False

    def undo(self):
        char = self.project_manager.get_character_by_name(self.char_name)
        if not char:
            return False
        events = char.get("events", [])
        if 0 <= self.event_index < len(events):
            events[self.event_index] = self.old_data
            self.project_manager.mark_modified("script")
            get_event_bus().publish(Events.CHARACTER_UPDATED, char_name=self.char_name)
            return True
        return False

class DeleteCharacterEventCommand(Command):
    def __init__(self, project_manager, char_name, event_index, description="删除人物事件"):
        super().__init__(description)
        self.project_manager = project_manager
        self.char_name = char_name
        self.event_index = event_index
        self.deleted_event = None
        self.deleted_index = -1

    def execute(self):
        char = self.project_manager.get_character_by_name(self.char_name)
        if not char:
            return False
        events = char.get("events", [])
        if 0 <= self.event_index < len(events):
            self.deleted_event = json.loads(json.dumps(events[self.event_index]))
            self.deleted_index = self.event_index
            del events[self.event_index]
            self.project_manager.mark_modified("script")
            get_event_bus().publish(Events.CHARACTER_UPDATED, char_name=self.char_name)
            return True
        return False

    def undo(self):
        if self.deleted_event is None:
            return False
        char = self.project_manager.get_character_by_name(self.char_name)
        if not char:
            return False
        events = char.setdefault("events", [])
        insert_index = self.deleted_index
        if insert_index < 0 or insert_index > len(events):
            insert_index = len(events)
        events.insert(insert_index, self.deleted_event)
        self.project_manager.mark_modified("script")
        get_event_bus().publish(Events.CHARACTER_UPDATED, char_name=self.char_name)
        return True

class AddSceneCommand(Command):
    def __init__(self, project_manager, scene_data, description="添加场景"):
        super().__init__(description)
        self.project_manager = project_manager
        self.scene_data = json.loads(json.dumps(scene_data))
        self.added_scene_index = -1
        self.added_scene_uid = ""

    def execute(self):
        scenes = self.project_manager.get_scenes()
        # 确保场景有 UID
        if "uid" not in self.scene_data:
            self.scene_data["uid"] = self.project_manager._gen_uid()
        self.added_scene_uid = self.scene_data["uid"]
        scenes.append(self.scene_data)
        self.added_scene_index = len(scenes) - 1
        self.project_manager.mark_modified()
        get_event_bus().publish(
            Events.SCENE_ADDED,
            scene_idx=self.added_scene_index,
            scene_uid=self.added_scene_uid,
            scene_name=self.scene_data.get("name", "")
        )
        return True

    def undo(self):
        scenes = self.project_manager.get_scenes()
        if 0 <= self.added_scene_index < len(scenes) and id(scenes[self.added_scene_index]) == id(self.scene_data):
            del scenes[self.added_scene_index]
            self.project_manager.mark_modified()
            get_event_bus().publish(
                Events.SCENE_DELETED,
                scene_idx=self.added_scene_index,
                scene_uid=self.added_scene_uid
            )
            return True
        return False

class DeleteSceneCommand(Command):
    def __init__(self, project_manager, scene_index, scene_data, description="删除场景"):
        super().__init__(description)
        self.project_manager = project_manager
        self.scene_index = scene_index
        self.deleted_scene_data = json.loads(json.dumps(scene_data))
        self.deleted_scene_uid = scene_data.get("uid", "")

    def execute(self):
        scenes = self.project_manager.get_scenes()
        if 0 <= self.scene_index < len(scenes):
            del scenes[self.scene_index]
            self.project_manager.mark_modified()
            get_event_bus().publish(
                Events.SCENE_DELETED,
                scene_idx=self.scene_index,
                scene_uid=self.deleted_scene_uid
            )
            return True
        return False

    def undo(self):
        scenes = self.project_manager.get_scenes()
        scenes.insert(self.scene_index, self.deleted_scene_data)
        self.project_manager.mark_modified()
        get_event_bus().publish(
            Events.SCENE_ADDED,
            scene_idx=self.scene_index,
            scene_uid=self.deleted_scene_uid
        )
        return True

class EditSceneCommand(Command):
    def __init__(self, project_manager, scene_index, old_data, new_data, description="编辑场景"):
        super().__init__(description)
        self.project_manager = project_manager
        self.scene_index = scene_index
        self.old_data = json.loads(json.dumps(old_data))
        self.new_data = json.loads(json.dumps(new_data))
        self.scene_uid = new_data.get("uid", old_data.get("uid", ""))

    def execute(self):
        scenes = self.project_manager.get_scenes()
        if 0 <= self.scene_index < len(scenes):
            scenes[self.scene_index] = self.new_data
            self.project_manager.mark_modified()
            get_event_bus().publish(
                Events.SCENE_UPDATED,
                scene_idx=self.scene_index,
                scene_uid=self.scene_uid
            )
            return True
        return False

    def undo(self):
        scenes = self.project_manager.get_scenes()
        if 0 <= self.scene_index < len(scenes):
            scenes[self.scene_index] = self.old_data
            self.project_manager.mark_modified()
            get_event_bus().publish(
                Events.SCENE_UPDATED,
                scene_idx=self.scene_index,
                scene_uid=self.scene_uid
            )
            return True
        return False

class EditSceneContentCommand(Command):
    def __init__(self, project_manager, scene_index, old_content, new_content, description="编辑场景内容"):
        super().__init__(description)
        self.project_manager = project_manager
        self.scene_index = scene_index
        self.old_content = old_content
        self.new_content = new_content

    def execute(self):
        scenes = self.project_manager.get_scenes()
        if 0 <= self.scene_index < len(scenes):
            scenes[self.scene_index]["content"] = self.new_content
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.SCENE_UPDATED, scene_idx=self.scene_index)
            return True
        return False

    def undo(self):
        scenes = self.project_manager.get_scenes()
        if 0 <= self.scene_index < len(scenes):
            scenes[self.scene_index]["content"] = self.old_content
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.SCENE_UPDATED, scene_idx=self.scene_index)
            return True
        return False

class MoveSceneCommand(Command):
    def __init__(self, project_manager, from_index, to_index, description="移动场景"):
        super().__init__(description)
        self.project_manager = project_manager
        self.from_index = from_index
        self.to_index = to_index

    def execute(self):
        scenes = self.project_manager.get_scenes()
        if 0 <= self.from_index < len(scenes) and 0 <= self.to_index <= len(scenes):
            item = scenes.pop(self.from_index)
            # Adjust insert index if moving forward
            # When popping from 2 and inserting at 5:
            # List shrinks. Insert at 5-1=4? No, python insert handles it if we pop first.
            # But if to_index > from_index, the index shifts down by 1 after pop.
            # actually insert(i, x) inserts before i.

            # Simple approach: standard list pop/insert
            target_idx = self.to_index
            if target_idx > self.from_index:
                target_idx -= 1

            scenes.insert(target_idx, item)
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.SCENE_MOVED, from_idx=self.from_index, to_idx=target_idx)
            return True
        return False

    def undo(self):
        scenes = self.project_manager.get_scenes()
        # To undo, we move back from the *new* position (target_idx) to from_index
        # Calculate where it ended up
        current_idx = self.to_index
        if current_idx > self.from_index:
            current_idx -= 1

        if 0 <= current_idx < len(scenes):
            item = scenes.pop(current_idx)
            scenes.insert(self.from_index, item)
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.SCENE_MOVED, from_idx=current_idx, to_idx=self.from_index)
            return True
        return False

# --- Wiki Commands ---

class SetScenePOVCommand(Command):
    """Set POV character and narrative voice for a scene."""

    def __init__(
        self,
        project_manager,
        scene_uid: str,
        pov_character: str,
        narrative_voice: str = "third_limited",
        narrator_reliability: float = 1.0,
        pov_notes: str = "",
        description="设置场景视角"
    ):
        super().__init__(description)
        self.project_manager = project_manager
        self.scene_uid = scene_uid
        self.new_pov = pov_character
        self.new_voice = narrative_voice
        self.new_reliability = narrator_reliability
        self.new_notes = pov_notes

        # Will be set during execute
        self.old_pov = ""
        self.old_voice = "third_limited"
        self.old_reliability = 1.0
        self.old_notes = ""

    def execute(self):
        scenes = self.project_manager.get_scenes()
        for scene in scenes:
            if scene.get("uid") == self.scene_uid:
                # Save old values
                self.old_pov = scene.get("pov_character", "")
                self.old_voice = scene.get("narrative_voice", "third_limited")
                self.old_reliability = scene.get("narrator_reliability", 1.0)
                self.old_notes = scene.get("pov_notes", "")

                # Set new values
                scene["pov_character"] = self.new_pov
                scene["narrative_voice"] = self.new_voice
                scene["narrator_reliability"] = self.new_reliability
                scene["pov_notes"] = self.new_notes

                self.project_manager.mark_modified()
                get_event_bus().publish(
                    Events.SCENE_UPDATED,
                    scene_uid=self.scene_uid,
                    update_type="pov"
                )
                return True
        return False

    def undo(self):
        scenes = self.project_manager.get_scenes()
        for scene in scenes:
            if scene.get("uid") == self.scene_uid:
                scene["pov_character"] = self.old_pov
                scene["narrative_voice"] = self.old_voice
                scene["narrator_reliability"] = self.old_reliability
                scene["pov_notes"] = self.old_notes

                self.project_manager.mark_modified()
                get_event_bus().publish(
                    Events.SCENE_UPDATED,
                    scene_uid=self.scene_uid,
                    update_type="pov"
                )
                return True
        return False

class BatchSetPOVCommand(Command):
    """Set POV for multiple scenes at once."""

    def __init__(
        self,
        project_manager,
        scene_uids: list,
        pov_character: str,
        narrative_voice: str = None,
        description="批量设置场景视角"
    ):
        super().__init__(description)
        self.project_manager = project_manager
        self.scene_uids = scene_uids
        self.new_pov = pov_character
        self.new_voice = narrative_voice  # If None, don't change voice

        # Will store old values during execute
        self.old_values = {}  # {scene_uid: {pov_character, narrative_voice}}

    def execute(self):
        scenes = self.project_manager.get_scenes()
        changed = False

        for scene in scenes:
            uid = scene.get("uid")
            if uid in self.scene_uids:
                # Save old values
                self.old_values[uid] = {
                    "pov_character": scene.get("pov_character", ""),
                    "narrative_voice": scene.get("narrative_voice", "third_limited")
                }

                # Set new values
                scene["pov_character"] = self.new_pov
                if self.new_voice is not None:
                    scene["narrative_voice"] = self.new_voice

                changed = True

        if changed:
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.SCENE_UPDATED, update_type="batch_pov")

        return changed

    def undo(self):
        scenes = self.project_manager.get_scenes()
        changed = False

        for scene in scenes:
            uid = scene.get("uid")
            if uid in self.old_values:
                old = self.old_values[uid]
                scene["pov_character"] = old["pov_character"]
                scene["narrative_voice"] = old["narrative_voice"]
                changed = True

        if changed:
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.SCENE_UPDATED, update_type="batch_pov")

        return changed

class UpdateNarratorReliabilityCommand(Command):
    """Update narrator reliability score for a scene."""

    def __init__(
        self,
        project_manager,
        scene_uid: str,
        new_reliability: float,
        description="更新叙述者可靠度"
    ):
        super().__init__(description)
        self.project_manager = project_manager
        self.scene_uid = scene_uid
        self.new_reliability = max(0.0, min(1.0, new_reliability))
        self.old_reliability = 1.0

    def execute(self):
        scenes = self.project_manager.get_scenes()
        for scene in scenes:
            if scene.get("uid") == self.scene_uid:
                self.old_reliability = scene.get("narrator_reliability", 1.0)
                scene["narrator_reliability"] = self.new_reliability

                self.project_manager.mark_modified()
                get_event_bus().publish(
                    Events.SCENE_UPDATED,
                    scene_uid=self.scene_uid,
                    update_type="reliability"
                )
                return True
        return False

    def undo(self):
        scenes = self.project_manager.get_scenes()
        for scene in scenes:
            if scene.get("uid") == self.scene_uid:
                scene["narrator_reliability"] = self.old_reliability

                self.project_manager.mark_modified()
                get_event_bus().publish(
                    Events.SCENE_UPDATED,
                    scene_uid=self.scene_uid,
                    update_type="reliability"
                )
                return True
        return False

class SetCharacterNarratorCommand(Command):
    """Mark a character as a potential narrator."""

    def __init__(
        self,
        project_manager,
        character_uid: str,
        is_narrator: bool,
        narrator_voice_style: str = "",
        description="设置角色叙述者属性"
    ):
        super().__init__(description)
        self.project_manager = project_manager
        self.character_uid = character_uid
        self.new_is_narrator = is_narrator
        self.new_voice_style = narrator_voice_style

        self.old_is_narrator = False
        self.old_voice_style = ""

    def execute(self):
        characters = self.project_manager.get_characters()
        for char in characters:
            if char.get("uid") == self.character_uid:
                self.old_is_narrator = char.get("is_narrator", False)
                self.old_voice_style = char.get("narrator_voice_style", "")

                char["is_narrator"] = self.new_is_narrator
                char["narrator_voice_style"] = self.new_voice_style

                self.project_manager.mark_modified()
                get_event_bus().publish(
                    Events.CHARACTER_UPDATED,
                    character_uid=self.character_uid
                )
                return True
        return False

    def undo(self):
        characters = self.project_manager.get_characters()
        for char in characters:
            if char.get("uid") == self.character_uid:
                char["is_narrator"] = self.old_is_narrator
                char["narrator_voice_style"] = self.old_voice_style

                self.project_manager.mark_modified()
                get_event_bus().publish(
                    Events.CHARACTER_UPDATED,
                    character_uid=self.character_uid
                )
                return True
        return False
