# Writer Tool

`Writer Tool` is a Windows-first Tkinter writing workspace for outlines, scenes, scripts, worldbuilding, export workflows, and AI-assisted side tools.

## Quick Start

### Full local setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python start_app.py
```

### Package install

```powershell
pip install .
writer-tool
```

### Test the current mainline

```powershell
python -m unittest discover tests
```

## What Works Now

| Area | Status | Notes |
| --- | --- | --- |
| Project open/save/edit loop | Stable | Core writing workflow, command history, and data services are part of the mainline. |
| Main GUI and tool launchers | Stable | Main app, tools hub, asset editor, and event analyzer all have dedicated launch paths. |
| Core export chain | Stable | The repository ships with multiple export targets and regression coverage in `tests/`. |
| Architecture and module split | Stable | `core`, `controllers`, `ui`, and launcher modules are already separated for maintenance. |
| Relationship map / advanced outline interactions | Beta | Useful, but still tracked under targeted validation instead of release-blocking coverage. |
| Project chat / RAG / floating assistant features | Beta | Environment-dependent and still need clearer user-facing validation boundaries. |
| Audio, TTS, and speech-adjacent features | Beta | Optional system support and extra packages may be required depending on the feature set. |

## Entry Points

- Main app: `python start_app.py` or `writer-tool`
- Tools hub: `python start_tools.py` or `writer-tool-tools`
- Asset editor: `python start_asset_editor.py` or `writer-tool-assets`
- Assistant event editor: `python start_assistant_event_editor.py` or `writer-tool-assistant-events`
- Event analyzer: `python analyze_events.py` or `writer-tool-event-analyzer`
- Windows helper scripts: `tools/windows/`

## Platform Notes

- Primary target: Windows desktop
- Supported Python range in package metadata: `>=3.10`
- Release validation now targets Python `3.10` to `3.12` in CI
- Default AI endpoint: local LM Studio at `http://localhost:1234/v1/chat/completions`
- User config path: `%USERPROFILE%\.writer_tool\config.json`
- `writer_data/` is still read for backward compatibility and bundled fallback assets

## Known Limits

- Public screenshots and GIF demos are still pending before a wider release push.
- Some advanced modules are intentionally treated as Beta until they complete the checklist in `docs/testing/BETA_VALIDATION.md`.
- Audio and speech features depend on optional packages and local machine capabilities.

## Project Layout

- `writer_app/`: application code, controllers, core services, and Tkinter UI
- `tools/launchers/`: launcher entrypoints used by the root wrappers
- `tools/standalone/`: standalone editors and analysis tools
- `tools/windows/`: Windows batch launch helpers
- `docs/architecture/`: architecture notes and refactor records
- `docs/testing/`: release blockers, beta validation, and focused QA plans
- `docs/notes/`: implementation notes, patch notes, and archived review artifacts
- `assets/`: repository-owned static assets
- `sample_data/`: sample content
- `runtime_data/`: generated local runtime output
- `tests/`: `unittest` suites

## Testing And Release Readiness

- Release blockers: `docs/testing/RELEASE_BLOCKERS.md`
- Beta validation backlog: `docs/testing/BETA_VALIDATION.md`
- Release checklist: `RELEASE_CHECKLIST.md`
- Changelog: `CHANGELOG.md`
- CI: `.github/workflows/ci.yml`

## Documentation

- Architecture notes: `docs/architecture/`
- Testing plans: `docs/testing/`
- Implementation and patch notes: `docs/notes/`

## Roadmap

- Finish public release assets: screenshots, release notes, packaged downloads
- Continue Beta verification for relationship tooling, project chat, and advanced assistant workflows
- Harden Windows packaging and wheel-based install validation
