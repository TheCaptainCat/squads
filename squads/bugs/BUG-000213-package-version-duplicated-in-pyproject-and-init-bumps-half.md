---
id: BUG-000213
sequence_id: 213
type: bug
title: Package version duplicated in pyproject and __init__ (bumps half-apply)
status: Open
author: op-pierre
created_at: '2026-06-25T13:34:04Z'
updated_at: '2026-06-25T13:34:22Z'
---
<!-- sq:body -->
## Defect
The package version is hard-coded in TWO places that can drift:
- `pyproject.toml` `[project].version`
- `src/squads/__init__.py` `__version__` (re-exported; drives `sq --version` and the schema-mismatch guard message in `_cli/_common.py::require_current_schema`).

During the 0.5 cut, `__version__` and `SCHEMA_VERSION` were bumped to 0.5 but `pyproject.toml` was left at 0.4.1. Consequences observed: `uv sync` saw no version change and skipped reinstalling; the global `uv tool` `sq` stayed 0.4.1 and refused to read the now-0.5 squad ("this squad is at schema v0.5, newer than squads 0.4.1"). The bump half-applied.

## Preferred fix (operator's call)
Make `pyproject.toml` the single source of truth and DERIVE the module version from installed metadata:
```python
from importlib.metadata import version
__version__ = version("squads")
```
So a future release bumps `pyproject` only, and `__version__` / `sq --version` / the schema guard follow automatically — they can't drift.

## Acceptance
- `squads.__version__ == importlib.metadata.version('squads')`; no second hard-coded version literal remains in the source.
- Bumping `pyproject.toml` version alone is reflected by `sq --version` and the schema-guard message after a reinstall.
- `uv run pyright && ruff && pytest` green.

Discovered live by op-pierre while debugging why `sq graph` failed after the 0.5 dogfood migration.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
