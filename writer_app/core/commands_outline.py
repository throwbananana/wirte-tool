import json

from writer_app.core.commands_base import Command
from writer_app.core.event_bus import Events, get_event_bus


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
