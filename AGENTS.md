# Repository Guidelines

## Project Structure & Module Organization
- `writer_app/main.py`: GUI entry point that wires controllers and Tkinter tabs; extend this instead of legacy entrypoints (e.g., `writer_tool.pyw` if present).
- `writer_app/core/`: domain logic such as `models.py`, command/undo history, backups, exporters, and config.
- `writer_app/ui/`: view layer (mind map, relationship map, chat panel, editor, timeline, dialogs).
- `writer_app/utils/`: helpers like `ai_client.py`, logging, tray integration.
- `tests/`: `unittest` suites (`test_*.py`).
- `writer_data/`: runtime assets, exports, and logs; do not treat as source.
- `build/`, `dist/`: packaged outputs.

## Build, Test, and Development Commands
- `python -m venv .venv && .\.venv\Scripts\activate`: create/activate a local env (Windows).
- `pip install -r requirements.txt`: install full dependencies (minimal runtime is `pip install requests`).
- `python start_app.py`: launch the main GUI (same as `python writer_app/main.py`).
- `python start_asset_editor.py` / `python start_assistant_event_editor.py`: open specialized editors.
- `python -m unittest discover tests`: run the test suite.

## Coding Style & Naming Conventions
- Python 3, PEP 8, 4-space indents; `snake_case` for functions, `PascalCase` for classes, `UPPER_SNAKE` for constants.
- Keep UI text bilingual as-is; avoid hardcoded paths; use `Path` and project-relative locations.
- Route state changes through the command pattern (`Command` + `CommandHistory`), not direct mutations.
- Add docstrings only when behavior is non-obvious, especially for canvas interactions in `writer_app/ui/`.

## Testing Guidelines
- Use `unittest` with `test_*.py`; follow arrange/act/assert.
- For new commands, add undo/redo coverage.
- For UI logic, factor non-GUI helpers so tests avoid Tkinter event loops.

## Commit & Pull Request Guidelines
- This checkout has no `.git` history, so follow concise, present-tense messages; use Conventional Commits (`feat:`, `fix:`, `chore:`) when in doubt.
- PRs should describe user-facing changes, list affected modules (`core`, `ui`, `utils`), include test commands run, and attach screenshots/gifs for UI changes (mind map, relationship map, chat panel).

## Security & Configuration Tips
- User config lives at `%USERPROFILE%\.writer_tool\config.json`; never commit or hardcode keys.
- AI calls target local LM Studio by default (`http://localhost:1234/v1/chat/completions`); use env vars + `ConfigManager` for remote endpoints.
- Export outputs under `writer_data/` or a user-selected directory to avoid clobbering sources.
