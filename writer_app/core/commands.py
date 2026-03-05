from abc import ABC, abstractmethod
import json
import uuid
from writer_app.core.event_bus import get_event_bus, Events

class Command(ABC):
    """Abstract base class for all commands that modify the project."""
    
    def __init__(self, description=""):
        self.description = description

    @abstractmethod
    def execute(self):
        """Execute the command and return True if successful, False otherwise."""
        pass

    @abstractmethod
    def undo(self):
        """Undo the command and return True if successful, False otherwise."""
        pass

    def __str__(self):
        return self.description


# --- Mind Map Node Commands ---

class AddNodeCommand(Command):
    def __init__(self, project_manager, parent_uid, new_node_data, description="添加节点", insert_index=None):
        super().__init__(description)
        self.project_manager = project_manager
        self.parent_uid = parent_uid
        self.new_node_data = json.loads(json.dumps(new_node_data)) # Deep copy
        self.insert_index = insert_index
        self.added_node_uid = None # Will store the actual UID after execute
        self.inserted_index = -1

    def execute(self):
        root_outline = self.project_manager.get_outline()
        parent_node_obj = self.project_manager.find_node_by_uid(root_outline, self.parent_uid)

        if not parent_node_obj:
            # Special case for adding the very first node to an empty outline
            if not root_outline.get("children") and root_outline.get("name") == "项目大纲":
                if self.parent_uid == root_outline.get("uid"):
                    parent_node_obj = root_outline
            else:
                return False # Parent not found
        
        if self.added_node_uid is None: # Prevent re-adding on redo
            if "children" not in parent_node_obj:
                parent_node_obj["children"] = []
            
            actual_new_node = json.loads(json.dumps(self.new_node_data)) # Create actual new node object
            # Ensure stable uid on new nodes
            if "uid" not in actual_new_node or not actual_new_node["uid"]:
                actual_new_node["uid"] = self.project_manager._gen_uid()
            
            self.added_node_uid = actual_new_node["uid"]
            children = parent_node_obj["children"]

            # Prefer stored index on redo, then requested insert_index, otherwise append
            if self.inserted_index >= 0:
                target_index = max(0, min(self.inserted_index, len(children)))
            elif self.insert_index is not None:
                target_index = max(0, min(self.insert_index, len(children)))
            else:
                target_index = len(children)

            children.insert(target_index, actual_new_node)
            self.inserted_index = target_index # Store insertion index
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.OUTLINE_NODE_ADDED, node_uid=self.added_node_uid)
            get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=self.added_node_uid)
            return True
        return False # Already executed or error

    def undo(self):
        root_outline = self.project_manager.get_outline()
        parent_node_obj = self.project_manager.find_node_by_uid(root_outline, self.parent_uid)

        if parent_node_obj and "children" in parent_node_obj:
            if self.added_node_uid is not None:
                # Find the object by its UID and remove it
                original_len = len(parent_node_obj["children"])
                parent_node_obj["children"][:] = [
                    node for node in parent_node_obj["children"] if node.get("uid") != self.added_node_uid
                ]
                if len(parent_node_obj["children"]) < original_len:
                    removed_uid = self.added_node_uid
                    self.project_manager.mark_modified()
                    if removed_uid:
                        get_event_bus().publish(Events.OUTLINE_NODE_DELETED, node_uids=[removed_uid])
                        get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=removed_uid)
                    self.added_node_uid = None # Mark as undone
                    return True
        return False


class DeleteNodesCommand(Command):
    def __init__(self, project_manager, node_uids_to_delete, description="删除节点"):
        super().__init__(description)
        self.project_manager = project_manager
        self.node_uids_to_delete = list(node_uids_to_delete)
        self.deleted_nodes_info = [] # Stores (parent_uid, index, node_data)
        self._executed_once = False
        self.deleted_uid_set = set()
        self._scene_outline_refs = {}

    def execute(self):
        root_outline = self.project_manager.get_outline()

        # Redo path: use stored index info
        if self._executed_once and self.deleted_nodes_info:
            removed_any = False
            for parent_uid, index, _ in sorted(self.deleted_nodes_info, key=lambda x: (x[0], x[1]), reverse=True):
                parent_node_obj = self.project_manager.find_node_by_uid(root_outline, parent_uid)
                if parent_node_obj and "children" in parent_node_obj and 0 <= index < len(parent_node_obj["children"]):
                    del parent_node_obj["children"][index]
                    removed_any = True
            if removed_any:
                self.project_manager.mark_modified()
                if self.deleted_uid_set:
                    get_event_bus().publish(
                        Events.OUTLINE_NODE_DELETED,
                        node_uids=list(self.deleted_uid_set)
                    )
                get_event_bus().publish(Events.OUTLINE_CHANGED)
                return True
            return False
        
        # Build a set of node UIDs to be deleted for efficient checking
        target_node_uids = set()
        self.deleted_uid_set = set()

        def _collect_uids(node_obj):
            uid = node_obj.get("uid")
            if uid:
                self.deleted_uid_set.add(uid)
            for child in node_obj.get("children", []):
                _collect_uids(child)

        for node_uid_to_del in self.node_uids_to_delete:
            found_node = self.project_manager.find_node_by_uid(root_outline, node_uid_to_del)
            if found_node and found_node is not root_outline: # Cannot delete root
                target_node_uids.add(found_node.get("uid"))
                _collect_uids(found_node)

        if not target_node_uids:
            return False # Nothing valid to delete

        # Capture outline references for undo
        self._scene_outline_refs = {}
        if self.deleted_uid_set:
            scenes = self.project_manager.get_scenes()
            for idx, scene in enumerate(scenes):
                outline_uid = scene.get("outline_ref_id", "")
                if outline_uid and outline_uid in self.deleted_uid_set:
                    self._scene_outline_refs[idx] = (
                        outline_uid,
                        scene.get("outline_ref_path", "")
                    )

        self.deleted_nodes_info.clear() # Clear any previous info on re-execution (redo)
        
        # Traverse the tree and prune branches that are in target_node_uids
        def _recursive_delete_and_record(current_node):
            if "children" in current_node:
                new_children_list = []
                # Iterate with index to capture position
                for i, child_obj in enumerate(current_node["children"]):
                    if child_obj.get("uid") in target_node_uids:
                        # Record deletion for undo
                        self.deleted_nodes_info.append((current_node.get("uid"), i, json.loads(json.dumps(child_obj))))
                    else:
                        new_children_list.append(child_obj)
                        _recursive_delete_and_record(child_obj) # Recurse into non-deleted children
                current_node["children"] = new_children_list

        _recursive_delete_and_record(root_outline)
        
        if self.deleted_nodes_info:
            self.project_manager.mark_modified()
            # Sort deleted info by parent_uid and then by index for consistent undo
            self.deleted_nodes_info.sort(key=lambda x: (x[0], x[1]))
            self._executed_once = True
            if self.deleted_uid_set:
                get_event_bus().publish(
                    Events.OUTLINE_NODE_DELETED,
                    node_uids=list(self.deleted_uid_set)
                )
            get_event_bus().publish(Events.OUTLINE_CHANGED)
            return True
        return False

    def undo(self):
        if not self.deleted_nodes_info:
            return False

        root_outline = self.project_manager.get_outline()
        
        # Re-insert nodes in index order to preserve original layout
        for parent_uid, index, node_data in sorted(self.deleted_nodes_info, key=lambda x: (x[0], x[1])):
            parent_node_obj = self.project_manager.find_node_by_uid(root_outline, parent_uid)
            if parent_node_obj and "children" in parent_node_obj:
                parent_node_obj["children"].insert(index, node_data)

        if self._scene_outline_refs:
            scenes = self.project_manager.get_scenes()
            for idx, (outline_uid, outline_path) in self._scene_outline_refs.items():
                if 0 <= idx < len(scenes):
                    scenes[idx]["outline_ref_id"] = outline_uid
                    scenes[idx]["outline_ref_path"] = (
                        outline_path or self.project_manager.get_outline_path(outline_uid)
                    )

        self.project_manager.mark_modified()
        if self.deleted_uid_set:
            get_event_bus().publish(
                Events.OUTLINE_NODE_ADDED,
                node_uids=list(self.deleted_uid_set)
            )
        get_event_bus().publish(Events.OUTLINE_CHANGED)
        return True


class EditNodeCommand(Command):
    def __init__(self, project_manager, node_uid, old_name, new_name, old_content, new_content, description="编辑节点"):
        super().__init__(description)
        self.project_manager = project_manager
        self.node_uid = node_uid
        self.old_name = old_name
        self.new_name = new_name
        self.old_content = old_content
        self.new_content = new_content

    def execute(self):
        root_outline = self.project_manager.get_outline()
        target_node_obj = self.project_manager.find_node_by_uid(root_outline, self.node_uid)
        if target_node_obj:
            target_node_obj["name"] = self.new_name
            target_node_obj["content"] = self.new_content
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=self.node_uid)
            return True
        return False

    def undo(self):
        root_outline = self.project_manager.get_outline()
        target_node_obj = self.project_manager.find_node_by_uid(root_outline, self.node_uid)
        if target_node_obj:
            target_node_obj["name"] = self.old_name
            target_node_obj["content"] = self.old_content
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=self.node_uid)
            return True
        return False


class MoveNodeCommand(Command):
    def __init__(self, project_manager, node_uid, new_parent_uid, index=None, description="移动节点"):
        super().__init__(description)
        self.project_manager = project_manager
        self.node_uid = node_uid
        self.new_parent_uid = new_parent_uid
        self.new_index = index
        
        self.old_parent_uid = None
        self.old_index = -1

    def execute(self):
        root = self.project_manager.get_outline()
        node_obj = self.project_manager.find_node_by_uid(root, self.node_uid)
        new_parent_obj = self.project_manager.find_node_by_uid(root, self.new_parent_uid)
        
        if not node_obj or not new_parent_obj:
            return False
            
        # Check for cycles
        if self._is_descendant(node_obj, new_parent_obj):
            return False

        old_parent_obj = self.project_manager.find_parent_of_node_by_uid(root, self.node_uid)
        if not old_parent_obj:
            return False # Cannot move root

        if "children" in old_parent_obj:
            try:
                self.old_index = old_parent_obj["children"].index(node_obj)
                self.old_parent_uid = old_parent_obj.get("uid")
                
                target_index = self.new_index
                if self.new_index is None:
                    target_index = len(new_parent_obj.get("children", []))
                    if old_parent_obj is new_parent_obj:
                         target_index -= 1

                # Remove from old
                old_parent_obj["children"].remove(node_obj)
                
                # Add to new
                if "children" not in new_parent_obj:
                    new_parent_obj["children"] = []
                
                if old_parent_obj is new_parent_obj and target_index is not None:
                     if target_index > self.old_index:
                         target_index -= 1

                if target_index is not None and 0 <= target_index <= len(new_parent_obj["children"]):
                    new_parent_obj["children"].insert(target_index, node_obj)
                else:
                    new_parent_obj["children"].append(node_obj)
                
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.OUTLINE_NODE_MOVED, node_uid=self.node_uid)
                get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=self.node_uid)
                return True
            except ValueError:
                pass
        return False

    def undo(self):
        if self.old_parent_uid is None: return False
        
        root = self.project_manager.get_outline()
        node_obj = self.project_manager.find_node_by_uid(root, self.node_uid)
        old_parent_obj = self.project_manager.find_node_by_uid(root, self.old_parent_uid)
        current_parent_obj = self.project_manager.find_node_by_uid(root, self.new_parent_uid)

        if node_obj and old_parent_obj and current_parent_obj:
            if "children" in current_parent_obj and node_obj in current_parent_obj["children"]:
                current_parent_obj["children"].remove(node_obj)
                old_parent_obj["children"].insert(self.old_index, node_obj)
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.OUTLINE_NODE_MOVED, node_uid=self.node_uid)
                get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=self.node_uid)
                return True
        return False

    def _is_descendant(self, node, potential_descendant):
        if node is potential_descendant: return True
        for child in node.get("children", []):
            if self._is_descendant(child, potential_descendant):
                return True
        return False

# --- Flat Draft Commands ---

class AddFlatDraftEntryCommand(Command):
    def __init__(self, project_manager, entry_data, insert_index=None, description="添加平铺叙事"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_data = json.loads(json.dumps(entry_data))
        self.insert_index = insert_index
        self.added_uid = None
        self.inserted_index = -1

    def execute(self):
        entries = self.project_manager.get_flat_draft_entries()
        if self.added_uid is None:
            actual_entry = json.loads(json.dumps(self.entry_data))
            if not actual_entry.get("uid"):
                actual_entry["uid"] = self.project_manager._gen_uid()
            self.added_uid = actual_entry["uid"]
            if self.inserted_index >= 0:
                target_index = max(0, min(self.inserted_index, len(entries)))
            elif self.insert_index is not None:
                target_index = max(0, min(self.insert_index, len(entries)))
            else:
                target_index = len(entries)
            entries.insert(target_index, actual_entry)
            self.inserted_index = target_index
            self.project_manager.mark_modified("outline")
            get_event_bus().publish(Events.OUTLINE_CHANGED, flat_draft_uid=self.added_uid)
            return True
        return False

    def undo(self):
        entries = self.project_manager.get_flat_draft_entries()
        if self.added_uid is None:
            return False
        original_len = len(entries)
        entries[:] = [entry for entry in entries if entry.get("uid") != self.added_uid]
        if len(entries) < original_len:
            removed_uid = self.added_uid
            self.added_uid = None
            self.project_manager.mark_modified("outline")
            get_event_bus().publish(Events.OUTLINE_CHANGED, flat_draft_uid=removed_uid)
            return True
        return False


class EditFlatDraftEntryCommand(Command):
    def __init__(self, project_manager, entry_uid, new_entry_data, description="编辑平铺叙事"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_uid = entry_uid
        self.new_entry_data = json.loads(json.dumps(new_entry_data))
        self.old_entry_data = None

    def execute(self):
        entries = self.project_manager.get_flat_draft_entries()
        for idx, entry in enumerate(entries):
            if entry.get("uid") == self.entry_uid:
                if self.old_entry_data is None:
                    self.old_entry_data = json.loads(json.dumps(entry))
                updated_entry = json.loads(json.dumps(self.new_entry_data))
                updated_entry["uid"] = self.entry_uid
                entries[idx] = updated_entry
                self.project_manager.mark_modified("outline")
                get_event_bus().publish(Events.OUTLINE_CHANGED, flat_draft_uid=self.entry_uid)
                return True
        return False

    def undo(self):
        if self.old_entry_data is None:
            return False
        entries = self.project_manager.get_flat_draft_entries()
        for idx, entry in enumerate(entries):
            if entry.get("uid") == self.entry_uid:
                entries[idx] = json.loads(json.dumps(self.old_entry_data))
                self.project_manager.mark_modified("outline")
                get_event_bus().publish(Events.OUTLINE_CHANGED, flat_draft_uid=self.entry_uid)
                return True
        return False


class DeleteFlatDraftEntryCommand(Command):
    def __init__(self, project_manager, entry_uid, description="删除平铺叙事"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_uid = entry_uid
        self.deleted_entry = None
        self.deleted_index = None

    def execute(self):
        entries = self.project_manager.get_flat_draft_entries()
        for idx, entry in enumerate(entries):
            if entry.get("uid") == self.entry_uid:
                self.deleted_entry = json.loads(json.dumps(entry))
                self.deleted_index = idx
                del entries[idx]
                self.project_manager.mark_modified("outline")
                get_event_bus().publish(Events.OUTLINE_CHANGED, flat_draft_uid=self.entry_uid)
                return True
        return False

    def undo(self):
        if self.deleted_entry is None or self.deleted_index is None:
            return False
        entries = self.project_manager.get_flat_draft_entries()
        insert_index = max(0, min(self.deleted_index, len(entries)))
        entries.insert(insert_index, json.loads(json.dumps(self.deleted_entry)))
        self.project_manager.mark_modified("outline")
        get_event_bus().publish(Events.OUTLINE_CHANGED, flat_draft_uid=self.entry_uid)
        return True


class ConvertFlatDraftToOutlineCommand(Command):
    def __init__(self, project_manager, entries, description="平铺叙事转换为大纲"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entries = json.loads(json.dumps(entries))
        self._nodes = None
        self._inserted_uids = []
        self._inserted_indices = []

    def execute(self):
        outline = self.project_manager.get_outline()
        children = outline.setdefault("children", [])
        if self._nodes is None:
            self._nodes = []
            kind_labels = {
                "narrative": "平铺叙事",
                "twist_encounter": "转折-遭遇",
                "twist_chance": "转折-偶然事件",
                "twist_choice": "转折-抉择处",
                "foreshadow_pos": "正铺垫",
                "foreshadow_neg": "反铺垫",
            }
            for entry in self.entries:
                label = entry.get("label") or kind_labels.get(entry.get("kind", ""), entry.get("kind", ""))
                name = entry.get("name") or ""
                if not name:
                    text = entry.get("text", "").strip()
                    name = text.splitlines()[0] if text else "未命名"
                prefix = f"[{label}]" if label else ""
                node = {
                    "name": f"{prefix} {name}".strip(),
                    "content": entry.get("text", ""),
                    "uid": self.project_manager._gen_uid(),
                    "children": []
                }
                self._nodes.append(node)
        if not self._nodes:
            return False
        start_index = len(children)
        for offset, node in enumerate(self._nodes):
            insert_index = start_index + offset
            children.insert(insert_index, json.loads(json.dumps(node)))
            self._inserted_indices.append(insert_index)
            self._inserted_uids.append(node["uid"])
            get_event_bus().publish(Events.OUTLINE_NODE_ADDED, node_uid=node["uid"])
        self.project_manager.mark_modified("outline")
        get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=self._inserted_uids[-1] if self._inserted_uids else None)
        return True

    def undo(self):
        if not self._inserted_uids:
            return False
        outline = self.project_manager.get_outline()
        children = outline.get("children", [])
        removed = []
        for uid in self._inserted_uids:
            for idx, node in enumerate(list(children)):
                if node.get("uid") == uid:
                    removed.append(uid)
                    del children[idx]
                    break
        if removed:
            self.project_manager.mark_modified("outline")
            get_event_bus().publish(Events.OUTLINE_NODE_DELETED, node_uids=removed)
            get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=removed[-1])
            return True
        return False

# --- Script Commands ---

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

class AddWikiEntryCommand(Command):
    def __init__(self, project_manager, entry_data, description="添加世界观条目"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_data = json.loads(json.dumps(entry_data))
        self.added_index = -1

    def execute(self):
        entries = self.project_manager.get_world_entries()
        entries.append(self.entry_data)
        self.added_index = len(entries) - 1
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.WIKI_ENTRY_ADDED, entry_idx=self.added_index)
        return True

    def undo(self):
        entries = self.project_manager.get_world_entries()
        if 0 <= self.added_index < len(entries):
            del entries[self.added_index]
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.WIKI_ENTRY_DELETED, entry_idx=self.added_index)
            return True
        return False

class DeleteWikiEntryCommand(Command):
    def __init__(self, project_manager, entry_index, entry_data, description="删除世界观条目"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_index = entry_index
        self.deleted_data = json.loads(json.dumps(entry_data))

    def execute(self):
        entries = self.project_manager.get_world_entries()
        if 0 <= self.entry_index < len(entries):
            del entries[self.entry_index]
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.WIKI_ENTRY_DELETED, entry_idx=self.entry_index)
            return True
        return False

    def undo(self):
        entries = self.project_manager.get_world_entries()
        entries.insert(self.entry_index, self.deleted_data)
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.WIKI_ENTRY_ADDED, entry_idx=self.entry_index)
        return True

class EditWikiEntryCommand(Command):
    def __init__(self, project_manager, entry_index, old_data, new_data, description="编辑世界观条目"):
        super().__init__(description)
        self.project_manager = project_manager
        self.entry_index = entry_index
        self.old_data = json.loads(json.dumps(old_data))
        self.new_data = json.loads(json.dumps(new_data))

    def execute(self):
        entries = self.project_manager.get_world_entries()
        if 0 <= self.entry_index < len(entries):
            entries[self.entry_index].update(self.new_data)
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.WIKI_ENTRY_UPDATED, entry_idx=self.entry_index)
            return True
        return False

    def undo(self):
        entries = self.project_manager.get_world_entries()
        if 0 <= self.entry_index < len(entries):
            entries[self.entry_index].update(self.old_data)
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.WIKI_ENTRY_UPDATED, entry_idx=self.entry_index)
            return True
        return False

# --- Relationship Commands ---

class UpdateCharLayoutCommand(Command):
    def __init__(self, project_manager, char_name, new_pos, old_pos=None):
        super().__init__("更新角色位置")
        self.project_manager = project_manager
        self.char_name = char_name
        self.new_pos = new_pos
        self.old_pos = old_pos

    def execute(self):
        rels = self.project_manager.get_relationships()
        if "character_layout" not in rels:
            rels["character_layout"] = dict(rels.get("layout", {}))
        if self.old_pos is None:
            self.old_pos = rels["character_layout"].get(self.char_name)
        rels["character_layout"][self.char_name] = self.new_pos
        self.project_manager.mark_modified("relationships")
        # 发布布局更新事件
        get_event_bus().publish(Events.RELATIONSHIPS_UPDATED,
                                char_name=self.char_name,
                                layout_type="character")
        return True

    def undo(self):
        rels = self.project_manager.get_relationships()
        if self.old_pos is None:
            if self.char_name in rels.get("character_layout", {}):
                del rels["character_layout"][self.char_name]
        else:
            rels["character_layout"][self.char_name] = self.old_pos
        self.project_manager.mark_modified("relationships")
        # 发布布局更新事件
        get_event_bus().publish(Events.RELATIONSHIPS_UPDATED,
                                char_name=self.char_name,
                                layout_type="character")
        return True

class AddLinkCommand(Command):
    def __init__(self, project_manager, link_data):
        super().__init__("添加关系连线")
        self.project_manager = project_manager
        self.link_data = link_data
        self.added_index = -1

    def execute(self):
        rels = self.project_manager.get_relationships()
        if "relationship_links" not in rels:
            rels["relationship_links"] = []
        rels["relationship_links"].append(self.link_data)
        self.added_index = len(rels["relationship_links"]) - 1
        self.project_manager.mark_modified("relationships")
        get_event_bus().publish(Events.RELATIONSHIP_LINK_ADDED, link_index=self.added_index)
        get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.added_index)
        return True

    def undo(self):
        rels = self.project_manager.get_relationships()
        if 0 <= self.added_index < len(rels.get("relationship_links", [])):
            del rels["relationship_links"][self.added_index]
            self.project_manager.mark_modified("relationships")
            get_event_bus().publish(Events.RELATIONSHIP_LINK_DELETED, link_index=self.added_index)
            get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.added_index)
            return True
        return False

class DeleteLinkCommand(Command):
    def __init__(self, project_manager, index):
        super().__init__("删除关系连线")
        self.project_manager = project_manager
        self.index = index
        self.deleted_data = None

    def execute(self):
        rels = self.project_manager.get_relationships()
        if "relationship_links" in rels and 0 <= self.index < len(rels["relationship_links"]):
            self.deleted_data = rels["relationship_links"][self.index]
            del rels["relationship_links"][self.index]
            self.project_manager.mark_modified("relationships")
            get_event_bus().publish(Events.RELATIONSHIP_LINK_DELETED, link_index=self.index)
            get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.index)
            return True
        return False

    def undo(self):
        rels = self.project_manager.get_relationships()
        if self.deleted_data:
            rels.setdefault("relationship_links", [])
            rels["relationship_links"].insert(self.index, self.deleted_data)
            self.project_manager.mark_modified("relationships")
            get_event_bus().publish(Events.RELATIONSHIP_LINK_ADDED, link_index=self.index)
            get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.index)
            return True
        return False


class EditLinkCommand(Command):
    """编辑关系连线（修改标签、颜色、大纲引用等）"""
    def __init__(self, project_manager, index, new_link_data):
        super().__init__("编辑关系连线")
        self.project_manager = project_manager
        self.index = index
        self.new_link_data = new_link_data
        self.old_link_data = None

    def execute(self):
        rels = self.project_manager.get_relationships()
        links = rels.get("relationship_links", [])
        if 0 <= self.index < len(links):
            self.old_link_data = dict(links[self.index])  # Save old data for undo
            links[self.index].update(self.new_link_data)
            self.project_manager.mark_modified("relationships")
            get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.index)
            return True
        return False


class AddRelationshipEventCommand(Command):
    """添加关系事件并关联到关系连线"""
    def __init__(self, project_manager, link_index, event_data):
        super().__init__("添加关系事件")
        self.project_manager = project_manager
        self.link_index = link_index
        self.event_data = json.loads(json.dumps(event_data))
        self.added_event_uid = ""
        self.added_frame_id = ""

    def execute(self):
        rels = self.project_manager.get_relationships()
        links = rels.get("relationship_links", [])
        if not (0 <= self.link_index < len(links)):
            return False

        link = links[self.link_index]
        events = rels.setdefault("relationship_events", [])

        if not self.event_data.get("uid"):
            self.event_data["uid"] = self.project_manager._gen_uid()
        self.added_event_uid = self.event_data["uid"]

        chapter_title = self.event_data.get("chapter_title", "")
        frame_id = self.event_data.get("frame_id")
        if not frame_id:
            for ev in events:
                if ev.get("chapter_title") == chapter_title and ev.get("frame_id"):
                    frame_id = ev.get("frame_id")
                    break
        if not frame_id:
            frame_id = self.project_manager._gen_uid()
        self.event_data["frame_id"] = frame_id
        self.added_frame_id = frame_id

        events.append(self.event_data)

        link.setdefault("event_uids", [])
        if self.added_event_uid not in link["event_uids"]:
            link["event_uids"].append(self.added_event_uid)

        link.setdefault("event_frame_ids", [])
        if self.added_frame_id not in link["event_frame_ids"]:
            link["event_frame_ids"].append(self.added_frame_id)

        self.project_manager.mark_modified("relationships")
        get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.link_index)
        return True

    def undo(self):
        rels = self.project_manager.get_relationships()
        events = rels.get("relationship_events", [])
        links = rels.get("relationship_links", [])
        if not (0 <= self.link_index < len(links)):
            return False

        if self.added_event_uid:
            rels["relationship_events"] = [e for e in events if e.get("uid") != self.added_event_uid]
            link = links[self.link_index]
            if "event_uids" in link and self.added_event_uid in link["event_uids"]:
                link["event_uids"].remove(self.added_event_uid)
            if "event_frame_ids" in link and self.added_frame_id in link["event_frame_ids"]:
                link["event_frame_ids"].remove(self.added_frame_id)

            self.project_manager.mark_modified("relationships")
            get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.link_index)
            return True
        return False

    def undo(self):
        if self.old_link_data is None:
            return False
        rels = self.project_manager.get_relationships()
        links = rels.get("relationship_links", [])
        if 0 <= self.index < len(links):
            links[self.index] = self.old_link_data
            self.project_manager.mark_modified("relationships")
            get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.index)
            return True
        return False


class UpdateRelationshipEventCommand(Command):
    """编辑关系事件并更新帧关联"""
    def __init__(self, project_manager, link_index, event_uid, new_data):
        super().__init__("编辑关系事件")
        self.project_manager = project_manager
        self.link_index = link_index
        self.event_uid = event_uid
        self.new_data = json.loads(json.dumps(new_data))
        self.old_data = None
        self.old_frame_id = ""
        self.new_frame_id = ""

    def _find_event(self, events):
        for idx, ev in enumerate(events):
            if ev.get("uid") == self.event_uid:
                return idx, ev
        return -1, None

    def _find_frame_id_for_chapter(self, events, chapter_title):
        if not chapter_title:
            return ""
        for ev in events:
            if ev.get("chapter_title") == chapter_title and ev.get("frame_id"):
                return ev.get("frame_id")
        return ""

    def _link_has_frame(self, events, link, frame_id):
        if not frame_id:
            return False
        uids = set(link.get("event_uids", []))
        for ev in events:
            if ev.get("uid") in uids and ev.get("frame_id") == frame_id:
                return True
        return False

    def execute(self):
        rels = self.project_manager.get_relationships()
        events = rels.get("relationship_events", [])
        links = rels.get("relationship_links", [])
        if not (0 <= self.link_index < len(links)):
            return False

        ev_idx, ev = self._find_event(events)
        if ev_idx < 0 or ev is None:
            return False

        self.old_data = dict(ev)
        self.old_frame_id = ev.get("frame_id", "")

        chapter_title = self.new_data.get("chapter_title", ev.get("chapter_title", ""))
        new_frame_id = self.new_data.get("frame_id") or ev.get("frame_id")
        if chapter_title != ev.get("chapter_title", ""):
            new_frame_id = self._find_frame_id_for_chapter(events, chapter_title)
            if not new_frame_id:
                new_frame_id = self.project_manager._gen_uid()

        if new_frame_id:
            self.new_data["frame_id"] = new_frame_id
        if chapter_title is not None:
            self.new_data["chapter_title"] = chapter_title

        events[ev_idx].update(self.new_data)
        self.new_frame_id = events[ev_idx].get("frame_id", "")

        link = links[self.link_index]
        link.setdefault("event_uids", [])
        if self.event_uid not in link["event_uids"]:
            link["event_uids"].append(self.event_uid)

        link.setdefault("event_frame_ids", [])
        if self.new_frame_id and self.new_frame_id not in link["event_frame_ids"]:
            link["event_frame_ids"].append(self.new_frame_id)
        if self.old_frame_id and self.old_frame_id != self.new_frame_id:
            if self.old_frame_id in link.get("event_frame_ids", []) and not self._link_has_frame(events, link, self.old_frame_id):
                link["event_frame_ids"].remove(self.old_frame_id)

        self.project_manager.mark_modified("relationships")
        get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.link_index)
        return True

    def undo(self):
        if not self.old_data:
            return False
        rels = self.project_manager.get_relationships()
        events = rels.get("relationship_events", [])
        links = rels.get("relationship_links", [])
        if not (0 <= self.link_index < len(links)):
            return False

        ev_idx, _ = self._find_event(events)
        if ev_idx < 0:
            return False
        events[ev_idx] = self.old_data

        link = links[self.link_index]
        link.setdefault("event_uids", [])
        if self.event_uid not in link["event_uids"]:
            link["event_uids"].append(self.event_uid)
        link.setdefault("event_frame_ids", [])
        old_frame_id = self.old_data.get("frame_id", "")
        if old_frame_id and old_frame_id not in link["event_frame_ids"]:
            link["event_frame_ids"].append(old_frame_id)
        if self.new_frame_id and self.new_frame_id != old_frame_id:
            if self.new_frame_id in link.get("event_frame_ids", []) and not self._link_has_frame(events, link, self.new_frame_id):
                link["event_frame_ids"].remove(self.new_frame_id)

        self.project_manager.mark_modified("relationships")
        get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.link_index)
        return True


class DeleteRelationshipEventCommand(Command):
    """删除关系事件并更新帧关联"""
    def __init__(self, project_manager, link_index, event_uid):
        super().__init__("删除关系事件")
        self.project_manager = project_manager
        self.link_index = link_index
        self.event_uid = event_uid
        self.deleted_event = None
        self.deleted_index = -1

    def _link_has_frame(self, events, link, frame_id):
        if not frame_id:
            return False
        uids = set(link.get("event_uids", []))
        for ev in events:
            if ev.get("uid") in uids and ev.get("frame_id") == frame_id:
                return True
        return False

    def execute(self):
        rels = self.project_manager.get_relationships()
        events = rels.get("relationship_events", [])
        links = rels.get("relationship_links", [])
        if not (0 <= self.link_index < len(links)):
            return False

        for idx, ev in enumerate(events):
            if ev.get("uid") == self.event_uid:
                self.deleted_event = ev
                self.deleted_index = idx
                break
        if self.deleted_event is None:
            return False

        del events[self.deleted_index]
        link = links[self.link_index]
        if "event_uids" in link and self.event_uid in link["event_uids"]:
            link["event_uids"].remove(self.event_uid)
        frame_id = self.deleted_event.get("frame_id", "")
        if frame_id and frame_id in link.get("event_frame_ids", []) and not self._link_has_frame(events, link, frame_id):
            link["event_frame_ids"].remove(frame_id)

        self.project_manager.mark_modified("relationships")
        get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.link_index)
        return True

    def undo(self):
        if self.deleted_event is None:
            return False
        rels = self.project_manager.get_relationships()
        events = rels.get("relationship_events", [])
        links = rels.get("relationship_links", [])
        if not (0 <= self.link_index < len(links)):
            return False

        insert_index = self.deleted_index
        if insert_index < 0 or insert_index > len(events):
            insert_index = len(events)
        events.insert(insert_index, self.deleted_event)

        link = links[self.link_index]
        link.setdefault("event_uids", [])
        if self.event_uid not in link["event_uids"]:
            link["event_uids"].append(self.event_uid)
        frame_id = self.deleted_event.get("frame_id", "")
        if frame_id:
            link.setdefault("event_frame_ids", [])
            if frame_id not in link["event_frame_ids"]:
                link["event_frame_ids"].append(frame_id)

        self.project_manager.mark_modified("relationships")
        get_event_bus().publish(Events.RELATIONSHIP_UPDATED, link_index=self.link_index)
        return True

# --- Evidence Board Commands ---

class AddEvidenceNodeCommand(Command):
    def __init__(self, project_manager, node_data, initial_pos):
        super().__init__("添加线索节点")
        self.project_manager = project_manager
        self.node_data = node_data
        self.initial_pos = initial_pos
        self.added_uid = None

    def execute(self):
        rels = self.project_manager.get_relationships()
        if "nodes" not in rels:
            rels["nodes"] = []
        if "evidence_layout" not in rels:
            rels["evidence_layout"] = dict(rels.get("layout", {}))

        if "uid" not in self.node_data or not self.node_data["uid"]:
            self.node_data["uid"] = str(uuid.uuid4())

        rels["nodes"].append(self.node_data)
        rels["evidence_layout"][self.node_data["uid"]] = self.initial_pos
        self.added_uid = self.node_data["uid"]
        self.project_manager.mark_modified("evidence")
        get_event_bus().publish(Events.EVIDENCE_NODE_ADDED, node_uid=self.added_uid)
        get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.added_uid)
        return True

    def undo(self):
        rels = self.project_manager.get_relationships()
        if self.added_uid:
            rels["nodes"] = [n for n in rels["nodes"] if n.get("uid") != self.added_uid]
            if self.added_uid in rels.get("evidence_layout", {}):
                del rels["evidence_layout"][self.added_uid]
            # Also remove any links associated with this node
            rels["evidence_links"] = [
                link for link in rels.get("evidence_links", [])
                if link.get("source") != self.added_uid and link.get("target") != self.added_uid
            ]
            self.project_manager.mark_modified("evidence")
            get_event_bus().publish(Events.EVIDENCE_NODE_DELETED, node_uid=self.added_uid)
            get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.added_uid)
            return True
        return False


class EditEvidenceNodeCommand(Command):
    def __init__(self, project_manager, node_uid, old_data, new_data):
        super().__init__("编辑线索节点")
        self.project_manager = project_manager
        self.node_uid = node_uid
        self.old_data = old_data  # Full old data dict
        self.new_data = new_data  # Full new data dict

    def execute(self):
        rels = self.project_manager.get_relationships()
        nodes = rels.get("nodes", [])
        for i, node in enumerate(nodes):
            if node.get("uid") == self.node_uid:
                nodes[i].update(self.new_data)
                self.project_manager.mark_modified("evidence")
                get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.node_uid)
                return True
        return False

    def undo(self):
        rels = self.project_manager.get_relationships()
        nodes = rels.get("nodes", [])
        for i, node in enumerate(nodes):
            if node.get("uid") == self.node_uid:
                nodes[i].update(self.old_data)
                self.project_manager.mark_modified("evidence")
                get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.node_uid)
                return True
        return False


class DeleteEvidenceNodeCommand(Command):
    def __init__(self, project_manager, node_uid):
        super().__init__("删除线索节点")
        self.project_manager = project_manager
        self.node_uid = node_uid
        self.deleted_node = None
        self.deleted_index = -1
        self.deleted_layout = None
        self.deleted_links = []

    def execute(self):
        rels = self.project_manager.get_relationships()
        nodes = rels.get("nodes", [])
        for i, node in enumerate(nodes):
            if node.get("uid") == self.node_uid:
                self.deleted_node = json.loads(json.dumps(node))
                self.deleted_index = i
                del nodes[i]
                break
        if self.deleted_node is None:
            return False

        layout = rels.get("evidence_layout", {})
        if self.node_uid in layout:
            self.deleted_layout = layout.pop(self.node_uid)

        links = rels.get("evidence_links", [])
        remaining_links = []
        self.deleted_links = []
        for i, link in enumerate(links):
            if link.get("source") == self.node_uid or link.get("target") == self.node_uid:
                self.deleted_links.append((i, json.loads(json.dumps(link))))
            else:
                remaining_links.append(link)
        rels["evidence_links"] = remaining_links

        self.project_manager.mark_modified("evidence")
        get_event_bus().publish(Events.EVIDENCE_NODE_DELETED, node_uid=self.node_uid)
        get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.node_uid)
        return True

    def undo(self):
        if self.deleted_node is None:
            return False

        rels = self.project_manager.get_relationships()
        nodes = rels.get("nodes", [])
        insert_index = self.deleted_index
        if insert_index < 0 or insert_index > len(nodes):
            insert_index = len(nodes)
        nodes.insert(insert_index, self.deleted_node)

        if "evidence_layout" not in rels:
            rels["evidence_layout"] = dict(rels.get("layout", {}))
        if self.deleted_layout is not None:
            rels["evidence_layout"][self.node_uid] = self.deleted_layout

        if self.deleted_links:
            rels.setdefault("evidence_links", [])
            for index, link in sorted(self.deleted_links, key=lambda item: item[0]):
                insert_idx = max(0, min(index, len(rels["evidence_links"])))
                rels["evidence_links"].insert(insert_idx, link)

        self.project_manager.mark_modified("evidence")
        get_event_bus().publish(Events.EVIDENCE_NODE_ADDED, node_uid=self.node_uid)
        get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.node_uid)
        return True


class UpdateEvidenceNodeLayoutCommand(Command):
    def __init__(self, project_manager, node_uid, new_pos, old_pos=None):
        super().__init__("更新线索节点位置")
        self.project_manager = project_manager
        self.node_uid = node_uid
        self.new_pos = new_pos
        self.old_pos = old_pos  # Store current for undo

    def execute(self):
        rels = self.project_manager.get_relationships()
        if "evidence_layout" not in rels:
            rels["evidence_layout"] = dict(rels.get("layout", {}))
        if self.node_uid not in rels["evidence_layout"]:
            self.old_pos = None  # No old position to restore
        else:
            self.old_pos = rels["evidence_layout"][self.node_uid]

        rels["evidence_layout"][self.node_uid] = self.new_pos
        self.project_manager.mark_modified("evidence")
        get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.node_uid)
        return True

    def undo(self):
        rels = self.project_manager.get_relationships()
        if self.node_uid in rels.get("evidence_layout", {}) and self.old_pos is not None:
            rels["evidence_layout"][self.node_uid] = self.old_pos
            self.project_manager.mark_modified("evidence")
            get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.node_uid)
            return True
        if self.node_uid in rels.get("evidence_layout", {}) and self.old_pos is None:  # Was new, remove
            del rels["evidence_layout"][self.node_uid]
            self.project_manager.mark_modified("evidence")
            get_event_bus().publish(Events.EVIDENCE_UPDATED, node_uid=self.node_uid)
            return True
        return False


class AddEvidenceLinkCommand(Command):
    def __init__(self, project_manager, link_data):
        super().__init__("添加线索链接")
        self.project_manager = project_manager
        self.link_data = link_data  # {source, target, label, type}
        self.added_idx = -1

    def execute(self):
        rels = self.project_manager.get_relationships()
        if "evidence_links" not in rels:
            rels["evidence_links"] = []
        rels["evidence_links"].append(self.link_data)
        self.added_idx = len(rels["evidence_links"]) - 1
        self.project_manager.mark_modified("evidence")
        get_event_bus().publish(Events.EVIDENCE_LINK_ADDED, link_index=self.added_idx)
        get_event_bus().publish(Events.EVIDENCE_UPDATED, link_index=self.added_idx)
        return True

    def undo(self):
        rels = self.project_manager.get_relationships()
        if 0 <= self.added_idx < len(rels.get("evidence_links", [])):
            del rels["evidence_links"][self.added_idx]
            self.project_manager.mark_modified("evidence")
            get_event_bus().publish(Events.EVIDENCE_UPDATED, link_index=self.added_idx)
            return True
        return False


class EditEvidenceLinkCommand(Command):
    def __init__(self, project_manager, link_index, new_link_data):
        super().__init__("编辑线索链接")
        self.project_manager = project_manager
        self.link_index = link_index
        self.new_link_data = new_link_data
        self.old_link_data = None

    def execute(self):
        rels = self.project_manager.get_relationships()
        links = rels.get("evidence_links", [])
        if 0 <= self.link_index < len(links):
            self.old_link_data = json.loads(json.dumps(links[self.link_index]))
            links[self.link_index].update(self.new_link_data)
            self.project_manager.mark_modified("evidence")
            get_event_bus().publish(Events.EVIDENCE_UPDATED, link_index=self.link_index)
            return True
        return False

    def undo(self):
        if self.old_link_data is None:
            return False
        rels = self.project_manager.get_relationships()
        links = rels.get("evidence_links", [])
        if 0 <= self.link_index < len(links):
            links[self.link_index] = self.old_link_data
            self.project_manager.mark_modified("evidence")
            get_event_bus().publish(Events.EVIDENCE_UPDATED, link_index=self.link_index)
            return True
        return False


class DeleteEvidenceLinkCommand(Command):
    def __init__(self, project_manager, link_index):
        super().__init__("删除线索链接")
        self.project_manager = project_manager
        self.link_index = link_index
        self.deleted_data = None

    def execute(self):
        rels = self.project_manager.get_relationships()
        if "evidence_links" in rels and 0 <= self.link_index < len(rels["evidence_links"]):
            self.deleted_data = rels["evidence_links"][self.link_index]
            del rels["evidence_links"][self.link_index]
            self.project_manager.mark_modified("evidence")
            get_event_bus().publish(Events.EVIDENCE_UPDATED, link_index=self.link_index)
            return True
        return False

    def undo(self):
        rels = self.project_manager.get_relationships()
        if self.deleted_data:
            rels.setdefault("evidence_links", [])
            rels["evidence_links"].insert(self.link_index, self.deleted_data)
            self.project_manager.mark_modified("evidence")
            get_event_bus().publish(Events.EVIDENCE_UPDATED, link_index=self.link_index)
            return True
        return False


# --- Faction Commands ---

class UpdateFactionRelationCommand(Command):
    def __init__(self, project_manager, uid_a, uid_b, value):
        super().__init__("更新势力关系")
        self.project_manager = project_manager
        self.uid_a = uid_a
        self.uid_b = uid_b
        self.value = int(value)
        self._old_a = 0
        self._old_b = 0
        self._had_a = False
        self._had_b = False

    def execute(self):
        matrix = self.project_manager.get_faction_matrix()
        self._had_a = self.uid_a in matrix and self.uid_b in matrix.get(self.uid_a, {})
        self._had_b = self.uid_b in matrix and self.uid_a in matrix.get(self.uid_b, {})
        self._old_a = matrix.get(self.uid_a, {}).get(self.uid_b, 0)
        self._old_b = matrix.get(self.uid_b, {}).get(self.uid_a, 0)

        if self.uid_a not in matrix:
            matrix[self.uid_a] = {}
        if self.uid_b not in matrix:
            matrix[self.uid_b] = {}

        matrix[self.uid_a][self.uid_b] = self.value
        matrix[self.uid_b][self.uid_a] = self.value

        self.project_manager.mark_modified("factions")
        get_event_bus().publish(Events.FACTION_RELATION_CHANGED, uid_a=self.uid_a, uid_b=self.uid_b, value=self.value)
        return True

    def undo(self):
        matrix = self.project_manager.get_faction_matrix()
        if self._had_a:
            matrix.setdefault(self.uid_a, {})[self.uid_b] = self._old_a
        else:
            if self.uid_a in matrix:
                matrix[self.uid_a].pop(self.uid_b, None)
                if not matrix[self.uid_a]:
                    matrix.pop(self.uid_a, None)

        if self._had_b:
            matrix.setdefault(self.uid_b, {})[self.uid_a] = self._old_b
        else:
            if self.uid_b in matrix:
                matrix[self.uid_b].pop(self.uid_a, None)
                if not matrix[self.uid_b]:
                    matrix.pop(self.uid_b, None)

        self.project_manager.mark_modified("factions")
        get_event_bus().publish(Events.FACTION_RELATION_CHANGED, uid_a=self.uid_a, uid_b=self.uid_b, value=self._old_a)
        return True


# --- Global Operations ---

class GlobalRenameCommand(Command):
    def __init__(self, project_manager, old_text, new_text, description="全局替换"):
        super().__init__(description)
        self.project_manager = project_manager
        self.old_text = old_text
        self.new_text = new_text
        self.changes = [] # List of (obj, key, old_val)

    def execute(self):
        self.changes.clear()
        if not self.old_text: return False

        # 1. Outline
        self._process_outline(self.project_manager.get_outline())

        # 2. Scenes
        for scene in self.project_manager.get_scenes():
            self._replace_in_dict(scene, "name")
            self._replace_in_dict(scene, "content")
            # Note: Not replacing in snapshots to preserve history integrity

        # 3. Characters
        for char in self.project_manager.get_characters():
            self._replace_in_dict(char, "name")
            self._replace_in_dict(char, "description")
            # Also replace in tags? Maybe.

        # 4. Wiki
        for entry in self.project_manager.get_world_entries():
            self._replace_in_dict(entry, "name")
            self._replace_in_dict(entry, "content")
            self._replace_in_dict(entry, "category")

        # 5. Ideas
        for idea in self.project_manager.get_ideas():
            self._replace_in_dict(idea, "content")

        if self.changes:
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.OUTLINE_CHANGED)
            return True
        return False

    def undo(self):
        for obj, key, old_val in reversed(self.changes):
            obj[key] = old_val
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.OUTLINE_CHANGED)
        return True

    def _process_outline(self, node):
        if not node: return
        self._replace_in_dict(node, "name")
        self._replace_in_dict(node, "content")
        for child in node.get("children", []):
            self._process_outline(child)

    def _replace_in_dict(self, obj, key):
        if key in obj and isinstance(obj[key], str) and self.old_text in obj[key]:
            self.changes.append((obj, key, obj[key]))
            obj[key] = obj[key].replace(self.old_text, self.new_text)


class ConvertIdeaToNodeCommand(Command):
    def __init__(self, project_manager, idea_uid, parent_node_uid, description="灵感转节点"):
        super().__init__(description)
        self.project_manager = project_manager
        self.idea_uid = idea_uid
        self.parent_node_uid = parent_node_uid
        
        self.deleted_idea = None
        self.added_node_uid = None
        self.idea_index = -1

    def execute(self):
        # 1. Find and remove Idea
        ideas = self.project_manager.get_ideas()
        idea_to_move = None
        for i, idea in enumerate(ideas):
            if idea.get("uid") == self.idea_uid:
                idea_to_move = idea
                self.idea_index = i
                break
        
        if not idea_to_move:
            return False

        # 2. Add Node
        root = self.project_manager.get_outline()
        parent = self.project_manager.find_node_by_uid(root, self.parent_node_uid)
        if not parent:
            return False

        self.deleted_idea = json.loads(json.dumps(idea_to_move)) # Backup
        del ideas[self.idea_index] # Remove idea

        new_node = {
            "uid": self.project_manager._gen_uid(),
            "name": idea_to_move.get("content", "")[:20], # Use first 20 chars as title
            "content": idea_to_move.get("content", ""),
            "children": [],
            "tags": idea_to_move.get("tags", [])
        }
        
        if "children" not in parent:
            parent["children"] = []
        
        parent["children"].append(new_node)
        self.added_node_uid = new_node["uid"]
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=self.added_node_uid)
        get_event_bus().publish(Events.IDEA_DELETED, idea_uid=self.idea_uid)
        get_event_bus().publish(Events.IDEAS_UPDATED)
        return True

    def undo(self):
        # 1. Remove added node
        if self.added_node_uid:
            root = self.project_manager.get_outline()
            parent = self.project_manager.find_parent_of_node_by_uid(root, self.added_node_uid)
            if parent:
                parent["children"] = [c for c in parent["children"] if c["uid"] != self.added_node_uid]

        # 2. Restore idea
            if self.deleted_idea and self.idea_index >= 0:
                ideas = self.project_manager.get_ideas()
                ideas.insert(self.idea_index, self.deleted_idea)

                self.project_manager.mark_modified()
                get_event_bus().publish(Events.OUTLINE_CHANGED, node_uid=self.added_node_uid)
                get_event_bus().publish(Events.IDEA_ADDED, idea_uid=self.idea_uid)
                get_event_bus().publish(Events.IDEAS_UPDATED)
                return True

# --- Timeline Commands ---

class AddTimelineEventCommand(Command):
    def __init__(self, project_manager, track_type, event_data, description="添加时间轴事件"):
        super().__init__(description)
        self.project_manager = project_manager
        self.track_type = track_type  # "truth" or "lie"
        self.event_data = json.loads(json.dumps(event_data))
        self.added_uid = None

    def execute(self):
        timelines = self.project_manager.project_data.get("timelines", {})
        if not timelines:
            self.project_manager.project_data["timelines"] = {"truth_events": [], "lie_events": []}
            timelines = self.project_manager.project_data["timelines"]

        target_list_key = "truth_events" if self.track_type == "truth" else "lie_events"
        if target_list_key not in timelines:
            timelines[target_list_key] = []

        if "uid" not in self.event_data:
            self.event_data["uid"] = self.project_manager._gen_uid()

        timelines[target_list_key].append(self.event_data)
        self.added_uid = self.event_data["uid"]
        self.project_manager.mark_modified()
        get_event_bus().publish(Events.TIMELINE_EVENT_ADDED, event_uid=self.added_uid, track_type=self.track_type)
        return True

    def undo(self):
        timelines = self.project_manager.project_data.get("timelines", {})
        target_list_key = "truth_events" if self.track_type == "truth" else "lie_events"

        if self.added_uid:
            original_len = len(timelines.get(target_list_key, []))
            timelines[target_list_key] = [e for e in timelines.get(target_list_key, []) if e.get("uid") != self.added_uid]
            if len(timelines[target_list_key]) < original_len:
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.TIMELINE_EVENT_DELETED, event_uid=self.added_uid, track_type=self.track_type)
                return True
        return False

class DeleteTimelineEventCommand(Command):
    def __init__(self, project_manager, track_type, event_uid, description="删除时间轴事件"):
        super().__init__(description)
        self.project_manager = project_manager
        self.track_type = track_type
        self.event_uid = event_uid
        self.deleted_data = None
        self.deleted_index = -1

    def execute(self):
        timelines = self.project_manager.project_data.get("timelines", {})
        target_list_key = "truth_events" if self.track_type == "truth" else "lie_events"
        events = timelines.get(target_list_key, [])

        for i, e in enumerate(events):
            if e.get("uid") == self.event_uid:
                self.deleted_data = json.loads(json.dumps(e))
                self.deleted_index = i
                del events[i]
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.TIMELINE_EVENT_DELETED, event_uid=self.event_uid, track_type=self.track_type)
                return True
        return False

    def undo(self):
        timelines = self.project_manager.project_data.get("timelines", {})
        target_list_key = "truth_events" if self.track_type == "truth" else "lie_events"

        if self.deleted_data and self.deleted_index >= 0:
            if target_list_key not in timelines:
                timelines[target_list_key] = []
            timelines[target_list_key].insert(self.deleted_index, self.deleted_data)
            self.project_manager.mark_modified()
            get_event_bus().publish(Events.TIMELINE_EVENT_ADDED, event_uid=self.event_uid, track_type=self.track_type)
            return True
        return False

class EditTimelineEventCommand(Command):
    def __init__(self, project_manager, track_type, event_uid, old_data, new_data, description="编辑时间轴事件"):
        super().__init__(description)
        self.project_manager = project_manager
        self.track_type = track_type
        self.event_uid = event_uid
        self.old_data = json.loads(json.dumps(old_data))
        self.new_data = json.loads(json.dumps(new_data))

    def execute(self):
        timelines = self.project_manager.project_data.get("timelines", {})
        target_list_key = "truth_events" if self.track_type == "truth" else "lie_events"
        events = timelines.get(target_list_key, [])

        for e in events:
            if e.get("uid") == self.event_uid:
                e.clear()
                e.update(self.new_data)
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.TIMELINE_EVENT_UPDATED, event_uid=self.event_uid, track_type=self.track_type)
                return True
        return False

    def undo(self):
        timelines = self.project_manager.project_data.get("timelines", {})
        target_list_key = "truth_events" if self.track_type == "truth" else "lie_events"
        events = timelines.get(target_list_key, [])

        for e in events:
            if e.get("uid") == self.event_uid:
                e.clear()
                e.update(self.old_data)
                self.project_manager.mark_modified()
                get_event_bus().publish(Events.TIMELINE_EVENT_UPDATED, event_uid=self.event_uid, track_type=self.track_type)
                return True
        return False


# ========================================
# POV Commands
# ========================================

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
