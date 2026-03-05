# Writer Tool (写作助手)

This project is a Python/Tkinter desktop application designed to assist writers with outlining, scriptwriting, and world-building. It features a dual-timeline system, mind map outlining, character relationship mapping, and local AI integration.

## Project Overview

*   **Name:** Writer Tool (写作助手)
*   **Type:** Desktop Application (GUI)
*   **Tech Stack:**
    *   **Language:** Python 3.x
    *   **GUI Framework:** Tkinter (native Python GUI)
    *   **Data Persistence:** JSON-based project files (`.writerproj`)
    *   **AI Integration:** Local AI (LM Studio) or OpenAI-compatible APIs
*   **Key Features:**
    *   Mind Map Outlining
    *   Script/Screenplay Editor with Syntax Highlighting
    *   Dual Timeline (Truth vs. Narrative)
    *   Character Relationship Map
    *   Evidence Board (for mystery/detective stories)
    *   AI-powered content generation and analysis
    *   Local Autosave and Backup

## Building and Running

### Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Key dependencies include:
*   `requests` (API calls)
*   `pillow` (Image handling)
*   `pygame` (Audio playback)
*   `pystray` (System tray icon)
*   `reportlab` (PDF export)
*   `SpeechRecognition`, `pyaudio` (Voice input)
*   `pyttsx3` (Text-to-speech)

### Running the Application

To start the application:

```bash
python start_app.py
```
Or directly via the package:
```bash
python writer_app/main.py
```

### Running Tests

The project uses Python's built-in `unittest` framework.

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_commands
```

## Architecture

The application follows a modular architecture separating data, logic, and UI.

### Core Components (`writer_app/core/`)

*   **`ProjectManager` (`models.py`):** The single source of truth for all project data. Manages loading, saving, and node traversal.
*   **`CommandHistory` (`history_manager.py`):** Implements the Command Pattern to handle Undo/Redo operations.
*   **`EventBus` (`event_bus.py`):** A Pub/Sub system allowing decoupled components to communicate (e.g., UI updates when data changes).
*   **`ConfigManager` (`config.py`):** Manages user preferences, persisting them to `~/.writer_tool/config.json`.
*   **`AIClient` (`utils/ai_client.py`):** A wrapper for AI API calls, handling connection to local LLMs (default: `localhost:1234`).

### UI Components (`writer_app/ui/`)

*   The UI is built with Tkinter and organized into modular views (tabs/panels).
*   **`main.py`:** The main entry point `WriterTool` class which assembles the UI.
*   **Views:** `ScriptEditor`, `MindMap`, `TimelinePanel`, `RelationshipMapCanvas`, etc.

### Data Flow

1.  **User Action:** User interacts with UI (e.g., adds a scene).
2.  **Command:** A specific `Command` subclass (e.g., `AddSceneCommand`) is instantiated.
3.  **Execution:** `CommandHistory` executes the command.
4.  **Model Update:** The command modifies data in `ProjectManager`.
5.  **Event:** `ProjectManager` triggers an event via `EventBus`.
6.  **UI Refresh:** Subscribers (UI components) receive the event and update their display.

## Development Conventions

*   **Command Pattern:** **All** state changes must be encapsulated in `Command` classes (in `core/commands.py`). Do not modify `ProjectManager` data directly from the UI.
*   **UIDs:** Nodes (scenes, characters, etc.) are referenced by unique `uid` strings, not by object reference, ensuring robust serialization and undo/redo.
*   **Event-Driven:** Use `EventBus` to notify other parts of the system about changes. Define new event types in `EventBus.Events`.
*   **Error Handling:** Use `BaseController.handle_error()` in controllers to manage exceptions and show user feedback.
*   **Logging:** Use the project's logging utility (`utils/logging_utils.py`). Logs are stored in `writer_data/writer_tool.log`.

## Configuration

User configuration is stored in `config.json` located in the user's home directory (`~/.writer_tool/`). This includes AI API settings, theme preferences, and window geometry.
