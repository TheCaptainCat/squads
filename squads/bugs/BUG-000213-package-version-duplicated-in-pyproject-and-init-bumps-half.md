---
id: BUG-213
sequence_id: 213
type: bug
title: Package version duplicated in pyproject and __init__ (bumps half-apply)
status: Verified
author: op-pierre
created_at: '2026-06-25T13:34:04Z'
updated_at: '2026-07-19T19:05:18Z'
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
- [2026-07-07T13:07:37Z] Hugo Ops:
  - Fixed: src/squads/__init__.py now derives __version__ = importlib.metadata.version("squads") at import time; removed the hardcoded 0.6.0 literal, so pyproject.toml [project].version is the single source of truth. Verified squads.__version__ == importlib.metadata.version('squads') and 'sq --version' report 0.7.0 after 'uv sync'; the schema-mismatch guard (_cli/_common.py::require_current_schema) reads the same symbol unchanged.
  - Landed as part of the 0.7.0 release prep working tree (pyproject bumped 0.6.0->0.7.0, uv.lock refreshed, sq sync rolled squads_version, CHANGELOG 0.7.0 section written).
  - Side effect discovered: scripts/gen_template_manifest.py text-parses __init__.py for the version and now misreads it — filed as BUG-324, not fixed this pass per release-prep scope; the 0.7.0 manifest entry itself was produced correctly via a manual one-off workaround (see BUG-324 body).
- [2026-07-07T13:11:23Z] Hugo Ops:
  - Follow-up resolved: the coordinator lifted the release-prep guardrail for this one case and had BUG-324 folded into this fix rather than deferred. scripts/gen_template_manifest.py::_current_version() now reads pyproject.toml's [project].version via tomllib instead of text-scanning this file's old __version__ literal, so the generator and the CI manifest-freshness gate are consistent with the single-sourced version again. BUG-324 is Fixed.
- [2026-07-19T19:05:18Z] Mara Tester:
  - src/squads/__init__.py derives __version__ via importlib.metadata.version("squads"), no hardcoded literal remains; confirmed squads.__version__ == importlib.metadata.version('squads') == pyproject's 0.9.0 live.
<!-- sq:discussion:end -->
