# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Writer Tool (写作助手) is a Python/Tkinter desktop application for writers that combines mind map outlining with structured script writing. It features local AI integration (LM Studio/OpenAI-compatible API) for content generation, analysis, and diagnostics.

**Data Format:** JSON-based project files (`.writerproj`)

## Quick Start

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install manually (Tkinter ships with Python)
pip install requests pillow pygame reportlab SpeechRecognition pyaudio pyttsx3

# Optional: for Word export
pip install python-docx

# Run the application
python start_app.py
# Or: python writer_app/main.py

# Specialized editors
python start_asset_editor.py              # Galgame asset manager
python start_assistant_event_editor.py    # Assistant event editor
python start_tools.py                     # Tool launcher

# Local AI: start LM Studio server (default http://localhost:1234/v1/chat/completions)
# before using AI-driven features
```

## Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run a single test file
python -m unittest tests.test_project_manager
python -m unittest tests.test_commands

# Run a specific test method
python -m unittest tests.test_commands.TestAddNodeCommand.test_add_node_execute

# Run tests with verbose output
python -m unittest discover tests -v
```

## Architecture

### Core Data Flow
- **`ProjectManager`** (`core/models.py`) is the single source of truth for all project data
- Observer pattern: UI components register listeners via `add_listener()` and react to `mark_modified()` calls
- **Command pattern** (`core/commands.py`) encapsulates all data mutations for undo/redo support
- All mutations route through `CommandHistory` (`core/history_manager.py`)
- **Event bus** (`core/event_bus.py`) provides pub/sub messaging between decoupled components
- **Module sync service** (`core/module_sync.py`) coordinates cross-module data consistency (timeline↔scene, timeline↔evidence)
- **UID-based node identification**: All outline nodes use persistent `uid` fields instead of Python object IDs for reliable undo/redo
- **Modular data system** (`core/typed_data.py`): Project types (Novel, Suspense, Galgame, etc.) determine which data modules are loaded—lean projects skip unused features

### Module Structure
```
writer_app/
├── main.py              # Main controller, wires all components, handles Tkinter tabs
├── core/
│   ├── models.py        # ProjectManager: data state, load/save, UID-based node traversal
│   ├── commands.py      # Command classes for undo/redo (all use UID-based lookups)
│   ├── commands_suspense.py # Commands for suspense/mystery features
│   ├── history_manager.py # CommandHistory: undo/redo stack management
│   ├── event_bus.py     # EventBus: pub/sub messaging between components
│   ├── config.py        # ConfigManager: user settings persistence
│   ├── backup.py        # BackupManager: autosave functionality
│   ├── exporter.py      # Export to Markdown, HTML, FDX, DOCX, Fountain, Ren'Py, CSV
│   ├── theme.py         # ThemeManager: dark/light theme support
│   ├── analysis.py      # AnalysisUtils: text analysis helpers
│   ├── audio.py         # AmbiancePlayer: ambient sound/white noise playback
│   ├── tts.py           # TextToSpeech: pyttsx3 wrapper for reading text aloud
│   ├── gamification.py  # XP/achievements system for writing motivation
│   ├── logic_validator.py # Story logic validation and consistency checks
│   ├── outline_templates.py # Pre-built story structure templates
│   ├── project_types.py # Project type definitions (novel, screenplay, etc.)
│   ├── resource_loader.py # Asset loading and management
│   ├── module_sync.py   # ModuleSyncService: cross-module event coordination
│   ├── controller_registry.py # ControllerRegistry: unified controller lifecycle management
│   ├── typed_data.py    # Modular data schemas per project type (DataModule enum, TYPE_MODULE_MAP)
│   ├── module_registry.py # Module availability tracking
│   ├── thread_pool.py   # AI thread pool for non-blocking API calls
│   ├── exceptions.py    # Custom exception classes (ProjectLoadError, etc.)
│   ├── validators.py    # Data structure validation (CharacterValidator, SceneValidator)
│   ├── reverse_engineer.py  # Reverse engineering story logic
│   ├── stats_manager.py # Writing statistics tracking
│   ├── training.py      # AI training features
│   ├── training_challenges.py # Writing challenge definitions
│   ├── training_history.py # Training session history
│   └── ai_tools/        # Structured AI tool definitions for function calling
│       ├── creation_tools.py   # Create characters, scenes, outline nodes
│       ├── editing_tools.py    # Modify existing content
│       ├── navigation_tools.py # Navigate project structure
│       ├── timeline_tools.py   # Timeline event operations
│       ├── evidence_tools.py   # Evidence/clue management
│       ├── asset_tools.py      # Asset management
│       ├── analysis_tools.py   # Content analysis
│       ├── batch_tools.py      # Bulk operations
│       ├── validation_tools.py # Story validation
│       └── query_tools.py      # Data queries
├── ui/
│   ├── editor.py        # ScriptEditor: syntax-highlighted script editing
│   ├── mindmap.py       # MindMap canvas for outline visualization
│   ├── relationship_map.py # Character relationship visualization
│   ├── evidence_board.py   # Evidence/clue board for mystery writing
│   ├── dual_timeline.py # Truth vs. narrative timeline for mysteries
│   ├── alibi_timeline.py # Character alibi tracking
│   ├── timeline.py      # TimelinePanel: scene timeline view
│   ├── kanban.py        # KanbanBoard: scene management board
│   ├── swimlanes.py     # SwimlaneView: character/location swimlanes
│   ├── calendar_view.py # CalendarView: story calendar
│   ├── chat_panel.py    # ChatPanel: project-context AI chat
│   ├── floating_assistant.py # Floating AI assistant overlay
│   ├── analytics.py     # AnalyticsPanel: data visualization
│   ├── beat_sheet.py    # Beat sheet editor (Save the Cat, etc.)
│   ├── story_curve.py   # Visual story tension/arc editor
│   ├── flowchart_view.py # Scene flow visualization
│   ├── galgame_assets.py # Visual novel asset management
│   ├── sprint_dialog.py # Writing sprint (timed writing sessions)
│   ├── history_browser.py # Undo/redo history visualization
│   ├── dialogs.py       # CharacterDialog, DiagnosisResultDialog
│   ├── dialogs_suspense.py # Suspense/mystery specific dialogs
│   ├── tags.py          # TagManagerDialog, TagSelectorDialog
│   ├── search_dialog.py # Global search/replace
│   ├── research.py      # ResearchPanel: research notes management
│   ├── idea_panel.py    # IdeaPanel: idea capture
│   ├── training_panel.py # TrainingPanel: AI writing training
│   ├── world_iceberg.py # WorldIcebergController: world-building iceberg view
│   ├── faction_matrix.py # Faction relationship matrix
│   ├── heartbeat_tracker.py # Story pacing/tension tracker
│   ├── outline_view_manager.py # Manages different outline view modes
│   ├── outline_views/   # Alternative outline visualizations (radial, fishbone, corkboard, etc.)
│   └── components/      # Reusable UI components (zoomable_canvas, etc.)
├── controllers/
│   ├── base_controller.py    # BaseController: abstract base with error handling
│   ├── mindmap_controller.py # Coordinates mindmap UI and data
│   ├── script_controller.py  # Script editing operations
│   ├── ai_controller.py      # AI generation and tool calling
│   ├── chat_controller.py    # Project chat interactions
│   ├── relationship_controller.py # Character relationship management
│   ├── dual_timeline_controller.py # Truth/narrative timeline logic
│   ├── wiki_controller.py    # World-building wiki management
│   ├── flowchart_controller.py
│   ├── kanban_controller.py
│   ├── calendar_controller.py
│   ├── timeline_controller.py
│   ├── pomodoro_controller.py # Pomodoro timer integration
│   ├── idea_controller.py    # Idea capture management
│   ├── research_controller.py # Research notes management
│   ├── training_controller.py # AI training session management
│   └── analytics_controller.py
└── utils/
    ├── ai_client.py     # AIClient: LM Studio/OpenAI API wrapper with JSON extraction
    └── logging_utils.py # Logging configuration and setup
```

### Key Classes

| Class | Responsibility |
|-------|----------------|
| `ProjectManager` | Manages project data, file I/O, UID-based node traversal (`find_node_by_uid`, `find_parent_of_node_by_uid`) |
| `CommandHistory` | Maintains undo/redo stacks, executes commands |
| `Command` (ABC) | Base class for all mutations; subclasses implement `execute()` and `undo()` |
| `EventBus` | Pub/sub messaging for decoupled component communication |
| `ControllerRegistry` | Unified controller management with group-based refresh (`refresh_group("scene")`) |
| `BaseController` | Abstract controller base with centralized error handling and logging |
| `AIClient` | Calls OpenAI-compatible endpoints, extracts JSON with trailing comma fix |
| `ScriptEditor` | Text widget with syntax highlighting, typewriter mode, focus mode |
| `LogicValidator` | Validates story consistency (timeline, character appearances, plot holes) |
| `ModuleSyncService` | Singleton that coordinates timeline↔scene and timeline↔evidence sync |

### Project Data Structure
```json
{
  "meta": {
    "type": "General",
    "length": "Long",
    "outline_template_style": "default",
    "created_at": "",
    "version": "1.0",
    "kanban_columns": ["构思", "初稿", "润色", "定稿"]
  },
  "outline": { "name": "...", "content": "...", "children": [], "uid": "..." },
  "script": {
    "title": "...",
    "characters": [{ "name": "", "description": "", "tags": [] }],
    "scenes": [{ "name": "", "location": "", "time": "", "content": "", "characters": [], "tags": [], "outline_ref_id": "" }]
  },
  "world": { "entries": [{ "name": "", "category": "", "content": "" }] },
  "relationships": {
    "layout": {},
    "character_layout": {},
    "evidence_layout": {},
    "relationship_links": [],
    "evidence_links": [],
    "links": [],
    "nodes": [],
    "snapshots": []
  },
  "factions": { "groups": [], "matrix": {} },
  "research": [],
  "ideas": [],
  "timelines": {
    "truth_events": [],
    "lie_events": []
  },
  "tags": [{ "name": "", "color": "" }]
}
```

## Adding New Features

### New Command Type
1. Create a class in `core/commands.py` inheriting from `Command`
2. Use `project_manager.find_node_by_uid()` for node lookups (not object IDs)
3. Implement `execute()` and `undo()` methods
4. Call via `_execute_command()` in `main.py` or controller

### New UI Tab
1. Create view class in `ui/`
2. Create controller in `controllers/` extending `BaseController`
3. Implement `setup_ui()` and `refresh()` methods
4. Add tab frame in `WriterTool.setup_ui()` in `main.py`
5. Register controller with `ControllerRegistry` and specify refresh groups
6. Subscribe to relevant events via `EventBus` for data updates

### New Export Format
1. Add static method to `Exporter` class in `core/exporter.py`
2. Add menu item in `WriterTool.setup_menu()` calling the export method

### New AI Tool
1. Add tool definition in appropriate file under `core/ai_tools/` (creation, editing, navigation, etc.)
2. Register in `core/ai_tools/__init__.py`
3. Implement handler in `controllers/ai_controller.py`

## AI Integration

The app connects to **local LM Studio** by default (OpenAI-compatible API):
- Default endpoint: `http://localhost:1234/v1/chat/completions`
- Configure via GUI: Outline tab → "AI生成思维导图" panel
- **AI Tools**: Structured function-calling tools in `core/ai_tools/` for creation, editing, navigation, timeline, and evidence operations

### Thread Pool for Non-blocking AI Calls
```python
from writer_app.core.thread_pool import get_ai_thread_pool

pool = get_ai_thread_pool()
pool.submit(ai_task_function, callback=on_complete, error_callback=on_error)

# Shutdown on app exit
from writer_app.core.thread_pool import shutdown_thread_pool
shutdown_thread_pool()
```

### JSON Extraction
`AIClient` handles markdown code blocks and trailing commas in AI responses automatically.

## Event Bus Usage

Use `Events` constants for type safety when publishing/subscribing:

```python
from writer_app.core.event_bus import get_event_bus, Events

bus = get_event_bus()

# Subscribe
bus.subscribe(Events.SCENE_UPDATED, lambda evt, **kw: print(kw.get('scene_uid')))

# Publish
bus.publish(Events.SCENE_UPDATED, scene_uid="abc123")

# Batch mode (for bulk operations)
bus.begin_batch()
# ... multiple publishes ...
bus.end_batch()  # deduplicates and dispatches
```

Key event types: `SCENE_*`, `CHARACTER_*`, `OUTLINE_*`, `TIMELINE_*`, `EVIDENCE_*`, `KANBAN_*`, `PROJECT_LOADED`, `PROJECT_SAVED`

## Controller Registry

Use `ControllerRegistry` for managing controllers and targeted refreshes:

```python
from writer_app.core.controller_registry import ControllerRegistry, RefreshGroups

# Register controller with refresh groups
registry.register("timeline", timeline_controller,
                  refresh_groups=[RefreshGroups.SCENE, RefreshGroups.TIMELINE])

# Refresh only controllers in a specific group (more efficient than refresh_all)
registry.refresh_group(RefreshGroups.SCENE)
```

**RefreshGroups constants:**
- `SCENE`, `CHARACTER`, `OUTLINE`, `WIKI`, `TIMELINE`
- `RELATIONSHIP`, `KANBAN`, `EVIDENCE`, `ASSET`, `ANALYTICS`, `ALL`

## Logging

Logs are written to `writer_data/writer_tool.log`. Configure logging level in code:

```python
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

## Exception Handling

Use custom exceptions from `core/exceptions.py`:

```python
from writer_app.core.exceptions import (
    ProjectLoadError,
    ProjectSaveError,
    ProjectValidationError,
    ValidationError,
    RequiredFieldError,
    DuplicateError
)

# In controllers, use BaseController.handle_error()
class MyController(BaseController):
    def some_action(self):
        try:
            # ... action logic
        except Exception as e:
            self.handle_error(e, "操作失败")
```

## Data Validation

Use validators from `core/validators.py` for data integrity:

```python
from writer_app.core.validators import CharacterValidator, SceneValidator

try:
    validated = CharacterValidator.validate(char_data)
except ValidationError as e:
    print(f"验证失败: {e.field} - {e.message}")
```

## Code Conventions

- PEP 8 style, 4-space indentation
- Classes: `PascalCase`, functions/methods: `snake_case`
- UI text is bilingual (Chinese primary, some English)
- Use `Path` from pathlib for file operations
- All data mutations must go through Command objects
- Use UID (not object ID) for node identification in commands
- Use `BaseController.handle_error()` for error handling in controllers
- Test new commands with `unittest` in `tests/`

## Configuration

User config stored at: `%USERPROFILE%\.writer_tool\config.json`

Includes:
- `lm_api_url`, `lm_api_model`, `lm_api_key` - AI settings
- `window_geometry` - Window size/position
- `last_opened_file` - Auto-restore on startup
- `theme` - Light/Dark

## Export Formats

| Format | Method | Dependencies |
|--------|--------|--------------|
| Markdown | `export_to_markdown()` | None |
| HTML (Print) | `export_to_html_print()` | None |
| Fountain | `export_to_fountain()` | None |
| Final Draft | `export_to_fdx()` | None |
| Word | `export_to_docx()` | python-docx |
| PDF | `export_to_pdf()` | reportlab |
| Ren'Py | `export_to_renpy()` | None |
| CSV | `export_to_csv()` | None |
| Character Sides | `export_character_sides()` | None |

## Commit Guidelines

- Use Conventional Commit prefixes: `feat:`, `fix:`, `chore:`, `test:`
- Never commit API keys or user config files
- Run `python -m unittest discover tests` before committing
