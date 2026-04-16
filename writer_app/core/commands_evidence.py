import json
import uuid

from writer_app.core.commands_base import Command
from writer_app.core.event_bus import Events, get_event_bus


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


class RemapEvidenceReferencesCommand(Command):
    """批量迁移 evidence_layout / evidence_links 中的节点引用。"""

    def __init__(self, project_manager, uid_map):
        super().__init__("迁移线索板引用")
        self.project_manager = project_manager
        self.uid_map = dict(uid_map or {})
        self.old_layout = None
        self.old_links = None

    def execute(self):
        if not self.uid_map:
            return False

        rels = self.project_manager.get_relationships()
        layout = rels.get("evidence_layout", {})
        links = rels.get("evidence_links", [])

        self.old_layout = json.loads(json.dumps(layout))
        self.old_links = json.loads(json.dumps(links))

        changed = False
        new_layout = {}
        for key, pos in layout.items():
            mapped_key = self.uid_map.get(key, key)
            if mapped_key != key:
                changed = True
            if mapped_key not in new_layout:
                new_layout[mapped_key] = pos

        new_links = []
        for link in links:
            new_link = json.loads(json.dumps(link))
            source = new_link.get("source")
            target = new_link.get("target")
            mapped_source = self.uid_map.get(source, source)
            mapped_target = self.uid_map.get(target, target)
            if mapped_source != source or mapped_target != target:
                changed = True
            new_link["source"] = mapped_source
            new_link["target"] = mapped_target
            new_links.append(new_link)

        if not changed:
            return False

        rels["evidence_layout"] = new_layout
        rels["evidence_links"] = new_links
        self.project_manager.mark_modified("evidence")
        get_event_bus().publish(Events.EVIDENCE_LAYOUT_UPDATED)
        get_event_bus().publish(Events.EVIDENCE_UPDATED)
        return True

    def undo(self):
        if self.old_layout is None or self.old_links is None:
            return False

        rels = self.project_manager.get_relationships()
        rels["evidence_layout"] = json.loads(json.dumps(self.old_layout))
        rels["evidence_links"] = json.loads(json.dumps(self.old_links))
        self.project_manager.mark_modified("evidence")
        get_event_bus().publish(Events.EVIDENCE_LAYOUT_UPDATED)
        get_event_bus().publish(Events.EVIDENCE_UPDATED)
        return True


# --- Faction Commands ---
