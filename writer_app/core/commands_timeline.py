import json

from writer_app.core.commands_base import Command
from writer_app.core.event_bus import Events, get_event_bus


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
