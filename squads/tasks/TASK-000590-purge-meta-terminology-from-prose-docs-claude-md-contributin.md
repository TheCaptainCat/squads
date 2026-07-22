---
id: TASK-590
sequence_id: 590
type: task
title: Purge 'meta' terminology from prose, docs, CLAUDE.md, CONTRIBUTING
status: Done
parent: FEAT-573
author: tech-lead
assignee: python-dev
refs:
- TASK-589:depends-on
created_at: '2026-07-22T12:18:10Z'
updated_at: '2026-07-22T12:54:10Z'
---
<!-- sq:body -->
## Scope

Terminology purge, last of the FEAT-573 wave (runs after the constant rename + consumer audit so
docstrings reference the final `ROSTER_*` / reworked-accessor names). Purge "meta" / "meta-type" /
"meta-types" / "non-meta" from comments, docstrings, `docs/`, and `CLAUDE.md`, replacing with
"roster" / "roster category" / "roster type". Ground with
`grep -rin "meta-type\|meta type\|non-meta\|\bmeta\b"`.

### Purge these (roster-type concept)

- `src/squads/_workflow/_models.py` — module docstring + `ROSTER_TYPES` comments ("the three
  meta-types", "a meta-type must be…"), `_validate` error strings ("spec missing required
  meta-types", "meta-type X must declare category = 'roster'"), the "non-meta work item" comment
  (~line 253), the sub-entity-kind docstring (~line 288).
- `src/squads/_interactions/_loader.py` — "meta type", "which are meta", "non-meta work type",
  the `_WORK_TYPES`/`_META_TYPES` historical mentions.
- `src/squads/_models/_metadata.py` — "reserved meta-types" (x3).
- `_services/_retype.py`, `_services/_rename.py`, `_cli/_items.py`, `_cli/_create.py`,
  `_cli/_migrate.py`, `_services/_base.py`, `_services/_items.py`, `_workflow/__init__.py`
  docstrings ("non-meta work type", "reserved meta-type", "meta-types with their own", etc.).
- `docs/internals.md:214` — "the three meta-types (`role`/`skill`/`operator`, `is_meta=True`)" ->
  roster wording + `category = "roster"`.
- `docs/workflow.md:461` — "non-meta work types" -> "work types".
- `CLAUDE.md` — any "meta"/"meta-type" roster-concept prose (NOT the `:meta` region line at ~56).

### Add convention line

Add a one-line naming convention to `CONTRIBUTING.md`: no "meta" for the roster-type concept —
use "roster" / "roster category".

### Do NOT touch (different `meta` concept, or historical ADR text)

- Legacy body-stored sub-entity `:meta` marker regions: `_migrations/_meta_compat.py`,
  the `:meta` lines in `docs/migration.md`, `docs/internals.md:204`, `CLAUDE.md:56`,
  `_v0_2_to_v0_3.py`'s "no legacy meta to lift".
- The local `meta` display variable in `_cli/_common.py`.
- The literal deprecated spec key `"is_meta"` and its loader shim (a real adopter-facing key).
- Accepted ADR bodies documenting the `is_meta`->`category` transition (ADR-541 etc.) — historical
  text may keep the old name in that context; do not rewrite accepted ADR history.

## Constraints

- Comments/docstrings/docs only — zero functional diff, byte-identical runtime behaviour for the
  bundled spec. Error-message string edits are user-facing wording only (same conditions raised).
- No status/lifecycle prose introduced into any body.
- No ticket IDs in source/test names.

## Gates (dev must run)

The `tui` extra MUST be installed or pyright reports ~304 false textual errors and `tests/tui`
breaks. Run all gates with `uv run --all-extras`:

`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 590 add-subtask "<title>"`; track with `sq task 590 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T12:45:39Z] Elias Python:
  - Purged 'meta'/'meta-type(s)'/'non-meta' roster-concept prose from src/tests comments+docstrings, docs/internals.md + docs/workflow.md, and CLAUDE.md; also updated the two error strings this touched (test_rename.py/test_workflow_reserved_vocab.py assertions updated to match). Added the naming convention to CONTRIBUTING.md, and fixed CLAUDE.md's stale gate command to --all-extras per your note.
  - Left ADR bodies, :meta region concept (_meta_compat.py, migrations, docs mentions, _cli/_common.py's local meta var), tests/meta/ layer naming, and the is_meta literal/shim untouched.
  - 3 .j2 templates changed (comment-only) -> regenerated templates_manifest.json for v0.12.0 (only those 3 entries). sq check byte-identical; full suite green.
<!-- sq:discussion:end -->
