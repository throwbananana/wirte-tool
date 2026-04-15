# Release Checklist

## Before Tagging

- Confirm `README.md` matches the actual startup, install, and feature status.
- Review `CHANGELOG.md` and summarize user-facing changes only.
- Verify archived notes in `docs/notes/archive/` do not need to remain in the root directory.

## Validation

- Run `python -m unittest discover tests`
- Complete every item in `docs/testing/RELEASE_BLOCKERS.md`
- Review `docs/testing/BETA_VALIDATION.md` and decide which Beta items remain explicitly out of scope for the release

## Packaging

- Create a fresh virtual environment and run `pip install .`
- Verify the package entry points resolve:
  - `writer-tool`
  - `writer-tool-tools`
  - `writer-tool-assets`
  - `writer-tool-assistant-events`
  - `writer-tool-event-analyzer`
- Produce release artifacts only after tests and install validation pass

## Release Notes

- State the supported Python range and Windows-first scope
- Call out Beta modules clearly instead of implying full product parity
- Link the changelog, release blockers, and any packaged downloads
