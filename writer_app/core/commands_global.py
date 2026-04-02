import json

from writer_app.core.commands_base import Command
from writer_app.core.event_bus import Events, get_event_bus


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
