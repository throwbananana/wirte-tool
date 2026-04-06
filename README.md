# Writer Tool

`Writer Tool` is a Tkinter-based writing workspace for outlines, scripts, worldbuilding, AI-assisted drafting, and side editors such as the asset editor and event analyzer.

## Repository Layout

- `writer_app/`: main application code, controllers, core services, and UI modules
- `tools/launchers/`: launcher entrypoints for the main GUI and tools hub
- `tools/standalone/`: standalone editors and analyzers
- `docs/architecture/`: refactor plans and architecture notes
- `docs/testing/`: test plans and QA notes
- `docs/notes/`: implementation notes and patch records
- `assets/`: shared static assets such as fonts and sounds
- `sample_data/`: bundled example data and starter content
- `runtime_data/`: runtime logs and generated working data
- `writer_data/`: legacy compatibility directory still read by the app when present
- `tests/`: `unittest` suites

## Common Commands

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python start_app.py
python start_tools.py
python -m unittest discover tests
```

### Notes for first run

- On Windows, Python 3.12 is recommended for the smoothest install experience.
- Some optional features such as advanced audio or speech input may require extra packages and system support.
- Excel export requires `openpyxl`.
- EPUB export requires `ebooklib`.
- If you only want to verify that the main GUI starts, focus on installing the default dependencies in `requirements.txt` first.

Legacy root launchers remain available as thin wrappers, while the actual implementations now live under `tools/`.

## Path Model

- User config: `%USERPROFILE%\.writer_tool\config.json`
- Shared assets: `assets/`
- Sample data: `sample_data/`
- Runtime logs and generated output: `runtime_data/`
- Old `writer_data/` content is still used as a fallback to avoid breaking existing projects

## Documentation

- Architecture: `docs/architecture/`
- Testing plans: `docs/testing/`
- Notes and migration records: `docs/notes/`
