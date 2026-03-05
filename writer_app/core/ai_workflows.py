"""
AI Workflow Manager - Event-driven automatic AI task execution.

Provides automated AI workflows triggered by project events, with genre-specific
configurations for different project types.

Usage:
    from writer_app.core.ai_workflows import AIWorkflowManager, get_workflow_manager

    # Get singleton instance
    manager = get_workflow_manager()

    # Initialize with project manager
    manager.initialize(project_manager, ai_controller)

    # Workflows are automatically triggered by events
"""

from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
from queue import Queue

from writer_app.core.event_bus import get_event_bus, Events

logger = logging.getLogger(__name__)


class WorkflowTrigger(Enum):
    """Events that can trigger workflows."""
    ON_SCENE_ADDED = "on_scene_added"
    ON_SCENE_UPDATED = "on_scene_updated"
    ON_SCENE_DELETED = "on_scene_deleted"
    ON_CHARACTER_ADDED = "on_character_added"
    ON_CHARACTER_UPDATED = "on_character_updated"
    ON_CHOICE_ADDED = "on_choice_added"
    ON_TIMELINE_CHANGED = "on_timeline_changed"
    ON_EVIDENCE_ADDED = "on_evidence_added"
    ON_SAVE = "on_save"
    ON_PROJECT_LOADED = "on_project_loaded"
    ON_EXPORT = "on_export"


class WorkflowPriority(Enum):
    """Priority levels for workflow execution."""
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class WorkflowTask:
    """Represents a single workflow task."""
    name: str
    description: str
    tool_name: str
    tool_params: Dict[str, Any] = field(default_factory=dict)
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    run_async: bool = True
    notify_on_complete: bool = False
    notify_on_error: bool = True


@dataclass
class WorkflowDefinition:
    """Defines a workflow that can be triggered."""
    name: str
    trigger: WorkflowTrigger
    tasks: List[WorkflowTask]
    genre_filter: Optional[List[str]] = None  # Only run for these genres
    condition: Optional[Callable[[Dict], bool]] = None  # Custom condition
    enabled: bool = True


# Genre-specific workflow configurations
GENRE_WORKFLOWS: Dict[str, List[WorkflowDefinition]] = {
    "Suspense": [
        WorkflowDefinition(
            name="validate_timeline_on_scene_add",
            trigger=WorkflowTrigger.ON_SCENE_ADDED,
            tasks=[
                WorkflowTask(
                    name="analyze_timeline_gaps",
                    description="检查时间线一致性",
                    tool_name="analyze_timeline_gaps",
                    priority=WorkflowPriority.NORMAL,
                    notify_on_error=True
                )
            ],
            genre_filter=["Suspense"]
        ),
        WorkflowDefinition(
            name="check_unresolved_clues",
            trigger=WorkflowTrigger.ON_SAVE,
            tasks=[
                WorkflowTask(
                    name="check_clue_placement",
                    description="检查未解决的线索",
                    tool_name="check_clue_placement",
                    priority=WorkflowPriority.LOW,
                    run_async=True
                )
            ],
            genre_filter=["Suspense"]
        ),
        WorkflowDefinition(
            name="detect_plot_holes_on_save",
            trigger=WorkflowTrigger.ON_SAVE,
            tasks=[
                WorkflowTask(
                    name="detect_plot_holes",
                    description="检测情节漏洞",
                    tool_name="detect_plot_holes",
                    priority=WorkflowPriority.LOW,
                    run_async=True
                )
            ],
            genre_filter=["Suspense"]
        )
    ],

    "Romance": [
        WorkflowDefinition(
            name="analyze_emotional_arc_on_save",
            trigger=WorkflowTrigger.ON_SAVE,
            tasks=[
                WorkflowTask(
                    name="analyze_emotional_arc",
                    description="分析情感弧线",
                    tool_name="analyze_emotional_arc",
                    priority=WorkflowPriority.LOW,
                    run_async=True
                )
            ],
            genre_filter=["Romance"]
        ),
        WorkflowDefinition(
            name="track_relationship_on_scene_update",
            trigger=WorkflowTrigger.ON_SCENE_UPDATED,
            tasks=[
                WorkflowTask(
                    name="track_relationships",
                    description="追踪感情线进展",
                    tool_name="track_relationship_progress",
                    priority=WorkflowPriority.BACKGROUND
                )
            ],
            genre_filter=["Romance"],
            enabled=False  # Disabled by default - can be enabled
        )
    ],

    "Galgame": [
        WorkflowDefinition(
            name="validate_branching_on_choice_add",
            trigger=WorkflowTrigger.ON_CHOICE_ADDED,
            tasks=[
                WorkflowTask(
                    name="validate_branching",
                    description="验证分支逻辑",
                    tool_name="validate_branching",
                    priority=WorkflowPriority.NORMAL
                )
            ],
            genre_filter=["Galgame", "LightNovel"]
        ),
        WorkflowDefinition(
            name="trace_variables_on_save",
            trigger=WorkflowTrigger.ON_SAVE,
            tasks=[
                WorkflowTask(
                    name="trace_variable_usage",
                    description="追踪变量使用",
                    tool_name="trace_variable_usage",
                    priority=WorkflowPriority.LOW
                )
            ],
            genre_filter=["Galgame"]
        ),
        WorkflowDefinition(
            name="check_endings_on_export",
            trigger=WorkflowTrigger.ON_EXPORT,
            tasks=[
                WorkflowTask(
                    name="check_ending_reachability",
                    description="检查结局可达性",
                    tool_name="check_ending_reachability",
                    priority=WorkflowPriority.NORMAL,
                    notify_on_complete=True
                )
            ],
            genre_filter=["Galgame"]
        )
    ],

    "General": [
        # Workflows that apply to all genres
        WorkflowDefinition(
            name="analyze_pacing_on_save",
            trigger=WorkflowTrigger.ON_SAVE,
            tasks=[
                WorkflowTask(
                    name="analyze_pacing",
                    description="分析节奏",
                    tool_name="analyze_pacing",
                    priority=WorkflowPriority.BACKGROUND,
                    run_async=True
                )
            ],
            genre_filter=None,  # All genres
            enabled=False  # Disabled by default
        )
    ]
}


class WorkflowResult:
    """Result of workflow execution."""

    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.success = True
        self.task_results: Dict[str, Any] = {}
        self.errors: List[str] = []

    def add_task_result(self, task_name: str, result: Any):
        self.task_results[task_name] = result

    def add_error(self, error: str):
        self.errors.append(error)
        self.success = False


class AIWorkflowManager:
    """
    Manages event-driven AI workflows.

    Subscribes to project events and triggers appropriate AI tasks
    based on the project type and workflow configuration.
    """

    _instance: Optional['AIWorkflowManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._project_manager = None
        self._ai_controller = None
        self._event_bus = get_event_bus()
        self._enabled = True
        self._workflow_queue: Queue = Queue()
        self._active_workflows: Set[str] = set()

        # Custom workflow registry
        self._custom_workflows: List[WorkflowDefinition] = []

        # Callback for workflow results
        self._on_workflow_complete: Optional[Callable[[WorkflowResult], None]] = None

        # Track disabled workflows
        self._disabled_workflows: Set[str] = set()

        logger.info("AIWorkflowManager initialized")

    def initialize(
        self,
        project_manager,
        ai_controller=None,
        on_workflow_complete: Callable[[WorkflowResult], None] = None
    ):
        """
        Initialize the workflow manager with project context.

        Args:
            project_manager: ProjectManager instance
            ai_controller: AIController instance (optional)
            on_workflow_complete: Callback for workflow results
        """
        self._project_manager = project_manager
        self._ai_controller = ai_controller
        self._on_workflow_complete = on_workflow_complete

        # Subscribe to events
        self._subscribe_to_events()

        logger.info("AIWorkflowManager initialized with project context")

    def _subscribe_to_events(self):
        """Subscribe to relevant project events."""
        # Map event bus events to workflow triggers
        event_trigger_map = {
            Events.SCENE_ADDED: WorkflowTrigger.ON_SCENE_ADDED,
            Events.SCENE_UPDATED: WorkflowTrigger.ON_SCENE_UPDATED,
            Events.SCENE_DELETED: WorkflowTrigger.ON_SCENE_DELETED,
            Events.CHARACTER_ADDED: WorkflowTrigger.ON_CHARACTER_ADDED,
            Events.CHARACTER_UPDATED: WorkflowTrigger.ON_CHARACTER_UPDATED,
            Events.TIMELINE_CHANGED: WorkflowTrigger.ON_TIMELINE_CHANGED,
            Events.EVIDENCE_ADDED: WorkflowTrigger.ON_EVIDENCE_ADDED,
            Events.PROJECT_SAVED: WorkflowTrigger.ON_SAVE,
            Events.PROJECT_LOADED: WorkflowTrigger.ON_PROJECT_LOADED,
        }

        for event, trigger in event_trigger_map.items():
            self._event_bus.subscribe(
                event,
                lambda e, trigger=trigger, **kwargs: self._on_event(trigger, kwargs)
            )

    def _on_event(self, trigger: WorkflowTrigger, event_data: Dict[str, Any]):
        """Handle an event and trigger appropriate workflows."""
        if not self._enabled:
            return

        active_genres = self._get_active_genres()
        workflows = self._get_workflows_for_trigger(trigger, active_genres)

        for workflow in workflows:
            if self._should_run_workflow(workflow, event_data):
                self._queue_workflow(workflow, event_data)

    def _get_project_type(self) -> str:
        """Get the current project type."""
        if self._project_manager:
            meta = self._project_manager.get_project_data().get("meta", {})
            return meta.get("type", "General")
        return "General"

    def _get_active_genres(self) -> List[str]:
        """Get the active genre list (primary type + secondary tags)."""
        if not self._project_manager:
            return ["General"]

        meta = self._project_manager.get_project_data().get("meta", {})
        genres = []
        primary = meta.get("type", "General")
        if primary:
            genres.append(primary)

        for tag in meta.get("genre_tags", []) or []:
            if tag and tag not in genres:
                genres.append(tag)

        return genres or ["General"]

    def _get_workflows_for_trigger(
        self,
        trigger: WorkflowTrigger,
        active_genres: List[str]
    ) -> List[WorkflowDefinition]:
        """Get all workflows for a trigger and active genres."""
        workflows = []
        added = set()

        # Get genre-specific workflows
        for genre in active_genres or []:
            for wf in GENRE_WORKFLOWS.get(genre, []):
                if wf.trigger == trigger and wf.enabled:
                    if wf.name not in self._disabled_workflows:
                        if wf.name not in added:
                            workflows.append(wf)
                            added.add(wf.name)

        # Get general workflows (apply to all genres)
        for wf in GENRE_WORKFLOWS.get("General", []):
            if wf.trigger == trigger and wf.enabled:
                if wf.genre_filter is None or any(g in wf.genre_filter for g in active_genres or []):
                    if wf.name not in self._disabled_workflows:
                        if wf.name not in added:
                            workflows.append(wf)
                            added.add(wf.name)

        # Add custom workflows
        for wf in self._custom_workflows:
            if wf.trigger == trigger and wf.enabled:
                if wf.genre_filter is None or any(g in wf.genre_filter for g in active_genres or []):
                    if wf.name not in self._disabled_workflows:
                        if wf.name not in added:
                            workflows.append(wf)
                            added.add(wf.name)

        return workflows

    def _should_run_workflow(
        self,
        workflow: WorkflowDefinition,
        event_data: Dict[str, Any]
    ) -> bool:
        """Check if a workflow should run based on conditions."""
        # Check if already running
        if workflow.name in self._active_workflows:
            return False

        # Check custom condition
        if workflow.condition and not workflow.condition(event_data):
            return False

        return True

    def _queue_workflow(self, workflow: WorkflowDefinition, event_data: Dict[str, Any]):
        """Queue a workflow for execution."""
        self._active_workflows.add(workflow.name)

        # Execute asynchronously
        import threading
        thread = threading.Thread(
            target=self._execute_workflow,
            args=(workflow, event_data)
        )
        thread.daemon = True
        thread.start()

    def _execute_workflow(
        self,
        workflow: WorkflowDefinition,
        event_data: Dict[str, Any]
    ):
        """Execute a workflow."""
        result = WorkflowResult(workflow.name)

        try:
            logger.debug(f"Executing workflow: {workflow.name}")

            for task in workflow.tasks:
                task_result = self._execute_task(task, event_data)
                result.add_task_result(task.name, task_result)

                if task_result and not task_result.get("success", True):
                    if task.notify_on_error:
                        result.add_error(task_result.get("message", "Unknown error"))

            logger.debug(f"Workflow completed: {workflow.name}")

        except Exception as e:
            logger.error(f"Workflow error [{workflow.name}]: {e}", exc_info=True)
            result.add_error(str(e))

        finally:
            self._active_workflows.discard(workflow.name)

            if self._on_workflow_complete:
                self._on_workflow_complete(result)

    def _execute_task(
        self,
        task: WorkflowTask,
        event_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute a single workflow task."""
        if not self._ai_controller:
            logger.warning(f"No AI controller available for task: {task.name}")
            return None

        try:
            # Prepare parameters
            params = {**task.tool_params}

            # Add event data to params if needed
            if "scene_uid" in event_data:
                params.setdefault("scene_uid", event_data["scene_uid"])
            if "character_uid" in event_data:
                params.setdefault("character_uid", event_data["character_uid"])

            # Execute tool through AI controller
            from writer_app.core.ai_tools import AIToolRegistry

            result = AIToolRegistry.execute(
                task.tool_name,
                self._project_manager,
                lambda cmd: cmd.execute(),  # Simple command executor
                params
            )

            return result.to_dict() if result else None

        except Exception as e:
            logger.error(f"Task execution error [{task.name}]: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # --- Public API ---

    def enable(self):
        """Enable workflow execution."""
        self._enabled = True

    def disable(self):
        """Disable workflow execution."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if workflows are enabled."""
        return self._enabled

    def disable_workflow(self, workflow_name: str):
        """Disable a specific workflow."""
        self._disabled_workflows.add(workflow_name)

    def enable_workflow(self, workflow_name: str):
        """Enable a specific workflow."""
        self._disabled_workflows.discard(workflow_name)

    def register_workflow(self, workflow: WorkflowDefinition):
        """Register a custom workflow."""
        self._custom_workflows.append(workflow)

    def unregister_workflow(self, workflow_name: str):
        """Unregister a custom workflow."""
        self._custom_workflows = [
            wf for wf in self._custom_workflows if wf.name != workflow_name
        ]

    def get_available_workflows(self) -> List[Dict[str, Any]]:
        """Get list of available workflows for current project context."""
        active_genres = self._get_active_genres()
        workflows = []
        added = set()

        # Genre-specific workflows
        for genre in active_genres or []:
            for wf in GENRE_WORKFLOWS.get(genre, []):
                if wf.name in added:
                    continue
                workflows.append({
                    "name": wf.name,
                    "trigger": wf.trigger.value,
                    "enabled": wf.name not in self._disabled_workflows and wf.enabled,
                    "tasks": [t.name for t in wf.tasks],
                    "genre": genre
                })
                added.add(wf.name)

        # General workflows
        for wf in GENRE_WORKFLOWS.get("General", []):
            if wf.genre_filter is None or any(g in wf.genre_filter for g in active_genres or []):
                if wf.name in added:
                    continue
                workflows.append({
                    "name": wf.name,
                    "trigger": wf.trigger.value,
                    "enabled": wf.name not in self._disabled_workflows and wf.enabled,
                    "tasks": [t.name for t in wf.tasks],
                    "genre": "General"
                })
                added.add(wf.name)

        # Custom workflows
        for wf in self._custom_workflows:
            if wf.genre_filter is None or any(g in wf.genre_filter for g in active_genres or []):
                if wf.name in added:
                    continue
                workflows.append({
                    "name": wf.name,
                    "trigger": wf.trigger.value,
                    "enabled": wf.name not in self._disabled_workflows,
                    "tasks": [t.name for t in wf.tasks],
                    "genre": "Custom"
                })
                added.add(wf.name)

        return workflows

    def trigger_workflow_manually(self, workflow_name: str) -> Optional[WorkflowResult]:
        """Manually trigger a workflow by name."""
        active_genres = self._get_active_genres()

        # Find the workflow
        workflow = None

        for genre in active_genres or []:
            for wf in GENRE_WORKFLOWS.get(genre, []):
                if wf.name == workflow_name:
                    workflow = wf
                    break
            if workflow:
                break

        if not workflow:
            for wf in GENRE_WORKFLOWS.get("General", []):
                if wf.name == workflow_name:
                    workflow = wf
                    break

        if not workflow:
            for wf in self._custom_workflows:
                if wf.name == workflow_name:
                    workflow = wf
                    break

        if workflow:
            self._queue_workflow(workflow, {})
            return WorkflowResult(workflow_name)

        return None


# Singleton accessor
_workflow_manager: Optional[AIWorkflowManager] = None


def get_workflow_manager() -> AIWorkflowManager:
    """Get the singleton workflow manager instance."""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = AIWorkflowManager()
    return _workflow_manager
