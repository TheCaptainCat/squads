---
id: TASK-634
sequence_id: 634
type: task
title: Orphan-pointer warning on init/adopt
status: Draft
parent: FEAT-576
author: tech-lead
description: WARN-only listing of pre-existing .claude agent pointers + skill files
  this run did not generate; never delete (crosses backend ownership boundary).
created_at: '2026-07-23T13:29:34Z'
updated_at: '2026-07-23T13:32:43Z'
---
<!-- sq:body -->
On `init`/`adopt`, warn about pre-existing `.claude` agent-pointer files and skill files that this run did not generate/manage — candidate orphans. WARN-only: never delete them (deleting crosses the backend's ownership boundary — squads owns only what it generates).

## The problem (from the field report)

When `adopt` meets a `.claude` corpus authored outside squads, a slug match silently overwrites (e.g. a hand-written `architect.md` pointer is replaced) while a non-matching file (`lead.md`, `ux-ui-dev.md`, a stray `.index.md`) is left with no signal at all. `adopt` is documented "non-destructive" but that claim does not extend to this collision case. This task makes both cases visible.

## Scope

- After a run's backend scaffolding/managed writes complete, compare the `.claude` agent-pointer and skill files present on disk against the set this run actually generated/manages, and emit a WARNING listing the leftovers as **candidate orphans** — the adopter reconciles them by hand.
- WARN only. Do not delete, move, or rewrite any file the run did not generate. This is the whole point: squads must not reach across the ownership boundary and remove operator-authored `.claude` content.
- Do this through the backend, not by reaching into `.claude/` from the service. The `AgentBackend` ABC already returns the artifacts it writes (`Artifact` list from `write_managed`/`ensure_scaffold`) and exposes `managed_paths(ctx)` — use "what the backend generated/manages this run" as the authoritative set, and let the backend enumerate the on-disk agent-pointer/skill files so the check stays backend-owned (invariant #6: don't reach into `.claude/` outside a backend). If a small new backend method is the clean way to enumerate candidate orphans, add it to the ABC so every backend participates.
- Surface the warnings on the `init`/`adopt` result so the CLI prints them; keep the service returning structured data and the CLI doing the rendering.

## Where it plugs in
- `_services/_service.py::init`/`adopt` (they call `scaffold_backend()` + `refresh_managed()`), `_services/_base.py::scaffold_backend`/`refresh_managed`.
- `_backends/_base.py` (the ABC + `BackendContext`), `_backends/_claude_code/_backend.py` (the pointer/skill writers already know their own paths: `.claude/skills/<name>/…`, agent pointers).

## Conventions (must hold)
- No status/lifecycle prose. Category is "roster", never "meta". No ticket/sq IDs in source or test names. PEP-695 `type` aliases. `SquadsError` family (this is a warning, not an error — do not abort the run). Escape console output via `_cli._common.e()` (file paths contain no markup usually, but paths with brackets would break Rich — wrap them).
- Invariant #5/#6: `.claude/` files are pointers, and nothing outside a backend touches them.

## Testing / gates
- Gates: `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`.
- If you add ANY module-level constant, run `tests/meta` (mutable-state guard).
- Service-level test: seed a `.claude` tree with both a slug-matching pointer and non-matching pointer/skill files before `adopt`, assert the warning lists exactly the candidate orphans and that NO pre-existing file was deleted. CLI smoke test: the warning is printed on `init`/`adopt`.
- `uv run sq check` clean before finishing.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 634 add-subtask "<title>"`; track with `sq task 634 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
