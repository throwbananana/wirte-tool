import json

from writer_app.core.commands_base import Command
from writer_app.core.event_bus import Events, get_event_bus


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
