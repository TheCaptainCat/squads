---
id: TASK-347
sequence_id: 347
type: task
title: Relocate badge-rendering helpers out of _discussion into _badges
status: InReview
author: tech-lead
assignee: python-dev
priority: low
refs:
- REV-346:addresses
description: Byte-identical move of badge/status-badge rendering helpers into a focused
  _badges module
created_at: '2026-07-09T14:56:25Z'
updated_at: '2026-07-09T15:10:55Z'
---
<!-- sq:body -->
Pure structural relocation (no behaviour change) addressing REV-346 finding F4. The badge/status-badge presentation helpers currently live in `src/squads/_discussion.py`, whose remit is comment/story/subtask prose formatting + @mention extraction. Badge rendering is presentation, not discussion — it belongs in its own module.

Scope: move `_status_badge`, `resolve_collection`, `badge_render` (and any tightly-coupled badge helper) out of `_discussion.py` into a new focused top-level `src/squads/_badges.py`. Repoint every caller — `_discussion`, `_cli/_common`, `_cli/_main`, `_cli/_items`, and any rendering-engine/template references. Keep the import graph acyclic.

Constraints: this must be a trivially-reviewable MOVE — identical function bodies, no logic edits, no golden regeneration. Any rationale comment that lands in the code stays ID-free (no ticket refs in source).

Acceptance: `_discussion.py` holds no badge-rendering functions (grep-verified); `_badges.py` owns them and all callers import from it; no golden change; `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; full suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 347 add-subtask "<title>"`; track with `sq task 347 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T15:06:58Z] Elias Python:
  - Moved _status_badge/resolve_collection/badge_render (+ _DEFAULT_BADGE) from _discussion.py into new src/squads/_badges.py, identical bodies. Repointed callers: _discussion.py (imports badges module, calls badges.X), _cli/_common.py, _cli/_main.py, _cli/_items.py. No _rendering engine/template reference existed (no-op there). Also repointed direct-call test files: test_discussion.py, test_rendering.py, test_status_display_characterization.py, test_custom_status_badges.py.
  - Gates: pyright/ruff check/ruff format clean; test_squad_ref_hygiene.py green; targeted discussion/badges/rendering/status/custom-badge-axis/graph/show-render/priority-views/tree/reflog-tree/golden-json/golden-rendered-output/bug-severity-migration suites green; no goldens changed. grep for def _status_badge|resolve_collection|badge_render in _discussion.py is empty.
- [2026-07-09T15:10:55Z] Elias Python:
  - Per coordinator: renamed _status_badge -> status_badge (no underscore, matches resolve_collection/badge_render) instead of suppressing reportUnusedFunction; the leading underscore was the real bug (module-private name used cross-module) not a pyright false-positive. Updated all call sites and removed every pyright-ignore I'd added. Re-verified: pyright 0 errors/0 new ignores, ruff check/format clean, test_squad_ref_hygiene.py green, targeted suites green, no golden change.
<!-- sq:discussion:end -->
