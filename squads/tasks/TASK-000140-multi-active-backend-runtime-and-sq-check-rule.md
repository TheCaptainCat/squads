---
id: TASK-000140
sequence_id: 140
type: task
title: Multi-active backend runtime and sq check rule
status: Done
parent: FEAT-000138
author: tech-lead
priority: high
subentities:
- local_id: ST1
  title: Config model active_backends + runtime fan-out over all active backends in
    scaffold/sync/write_managed + init/adopt populate the list; tests proving multiple
    backends (CLAUDE.md + AGENTS.md) are generated and checked
  status: Done
  story: US1
- local_id: ST2
  title: 'sq check rule: each active backend''s files present & current, empty active_backends=[]
    verifies nothing (sq-only squad), deactivated backend''s lingering files are ignored
    not flagged; tests for empty + deactivation semantics'
  status: Done
  story: US2
created_at: '2026-06-16T09:39:30Z'
updated_at: '2026-06-16T13:01:00Z'
---
<!-- sq:body -->
## Goal

The runtime half of FEAT-000138: change the config model to carry
`active_backends: list[str]`, fan every backend-writing path out over the active
list, populate the list at init/adopt, and add the `sq check` rule. Builds on the
schema bump + migration in TASK-000139.

## Work

- **Config model** (`src/squads/_models/_config.py`): replace
  `default_backend: NonEmpty = "claude_code"` with `active_backends: list[str]`
  (default `["claude_code"]`; `[]` is valid). Update `to_toml()` to emit the list
  and `from_toml_dict` / validation to read it. (Per ADR: whether order matters,
  dedup policy.)
- **Runtime fan-out** (`src/squads/_services/_base.py`): `_backend()` (singular)
  becomes an iterator over active backends — `active_backends()` /
  `_backends()` — and the call sites that write managed files loop over all of
  them: `scaffold_backend`, `refresh_managed`, and in
  `src/squads/_services/_maintenance.py::sync` the `ensure_scaffold` /
  `generate_role_entry` / `generate_skill_entry` / `write_managed` calls. Empty
  list = no-op (sq-only squad).
- **init / adopt** (`src/squads/_services/_service.py`, `src/squads/_cli/_main.py`):
  the `--backend` option populates `active_backends` (single element, or `[]` /
  multi per the ADR's chosen input grammar). Update the `sq init`/info line that
  prints `config.default_backend` (`_cli/_main.py:185`).
- **`sq check` rule** (`src/squads/_services/_maintenance.py::check`): for each
  active backend, verify its managed files are present and current/un-drifted
  (error or warn per ADR); empty list verifies nothing; backends absent from the
  list are ignored even if their files linger on disk (deactivation = ignore).
  This needs a backend-level "what files do you own / are they current?" probe —
  coordinate with the ABC (ADR-000133 shape).
- **Tests**: service-level + CLI smoke for (a) multi-active sync writing both
  backends' files; (b) empty list = no agent files, check clean; (c) deactivation
  leaves files but check ignores them. Update existing tests that assert
  `default_backend` (`tests/test_service.py`, `tests/test_backend_*`,
  `tests/test_operators.py`).

## Coordination

Shares the `SquadsConfig` seam with TASK-000139 (which bumps schema + writes the
new TOML key). The ABC probe for "files present/current" may touch
`src/squads/_backends/_base.py` and both backend impls — overlaps lightly with
ADR-000133's just-landed ABC surface. Sequence after 139's schema/runner.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 140 add-subtask "<title>"`; track with `sq task 140 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Config model active_backends + runtime fan-out over all active backends in scaffold/sync/write_managed + init/adopt populate the list; tests proving multiple backends (CLAUDE.md + AGENTS.md) are generated and checked | US1 |
| ST2 | Done |  | sq check rule: each active backend's files present & current, empty active_backends=[] verifies nothing (sq-only squad), deactivated backend's lingering files are ignored not flagged; tests for empty + deactivation semantics | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Config model active_backends + runtime fan-out over all active backends in scaffold/sync/write_managed + init/adopt populate the list; tests proving multiple backends (CLAUDE.md + AGENTS.md) are generated and checked

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Maintain multiple active backends at once
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sq check rule: each active backend's files present & current, empty active_backends=[] verifies nothing (sq-only squad), deactivated backend's lingering files are ignored not flagged; tests for empty + deactivation semantics

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Empty active_backends and deactivation-ignore semantics
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-16T12:27:52Z] Elias Python:
  - Implemented TASK-000140 (config model + multi-active runtime + check) per ADR-000141.
  - Config model (_models/_config.py): replaced default_backend: NonEmpty with active_backends: list[str] = ['claude_code']. Dedup-on-read via @field_validator (first-occurrence order, ADR-141 §2). from_toml_dict translates legacy default_backend→active_backends for back-compat with pre-migration TOML.
  - Runtime fan-out (_services/_base.py): _backend() replaced by _backends() returning list[AgentBackend]. scaffold_backend(), refresh_managed(), activate_role/add_dev/add_skill (roster), regen/remove_item (items), and sync() (maintenance) all fan out over all active backends. Empty list = no-op (sq-only squad).
  - init/adopt CLI (_cli/_main.py, _services/_service.py): --backend is now repeatable (list[str]); _parse_backend_option() implements the 'none' sentinel (case-insensitive → [] i.e. sq-only; 'none' + real backend raises SquadsError per ADR-141 §3). Info line changed from default_backend to joined active_backends.
  - New ABC method managed_paths(ctx)->list[str] on AgentBackend (read-only probe for sq check). claude_code returns ['CLAUDE.md', '.claude/settings.json']; agents_md returns ['AGENTS.md']. Both added to conformance suite (TestManagedPaths: returns list[str], paths relative+forward-slash, does not create files, paths exist after sync).
  - sq check rule (_maintenance.py::_check_backends): loops active (deduped) backends, emits CheckIssue('error', ...) for any missing managed path. Empty active_backends=[]→nothing checked (sq-only squad clean). Deactivated backends not probed.
  - Tests updated: test_backend_conformance.py (active_backends=[...]), test_backend_agents_md.py (backend=[...] list form), test_agent_naming.py (active_backends), test_backend_claude.py (_backend()→_backends()), test_cli.py (schema 0.3→0.4 string literals), test_reflog_core/read.py (v='0.4').
  - Full gate: 808 passed, 1 skipped. Pyright 0 errors. Ruff + format clean.
  - @reviewer ready for review. @qa please run test_backend_conformance (multi-backend), test_migration_corpus (v0_3→v0_4 non-vacuous), and test_cli (backend=none sentinel, multi-active).
- [2026-06-16T12:32:10Z] Elias Python:
  - TASK-140 final state: added 13 new tests in tests/test_multi_active_backends.py covering US1 (multi-active: both CLAUDE.md + AGENTS.md written), US2 (empty=[]: no scaffold, check clean; deactivated files not flagged), dedup semantics (collapse + first-occurrence order), --backend none sentinel (→[], case-insensitive, error if combined with real backend), and CLI output. Gate: 821 passed, 1 skipped. @reviewer @qa ready.
- [2026-06-16T12:42:41Z] Elias Python:
  - Reverted the 0.4 schema bump and its migration per op-pierre directive: active_backends is now part of the 0.3 schema shape, no migration needed. Removed _v0_3_to_v0_4.py, its registry entry, and the v0_4 corpus fixture. Re-stamped .squads.toml and squads/.squads.json from 0.4 back to 0.3. The transparent back-compat read of legacy default_backend stays (handles pre-0.3 TOML files without any migration). All 819 tests pass, pyright + ruff clean, sq check is green on the repo squad at 0.3. @reviewer @qa
- [2026-06-16T12:54:18Z] Mara Tester:
  - QA verification pass — all acceptance criteria met (2026-06-16).
    
    **US1 (multi-active):** `sq init --backend claude_code --backend agents_md` generates both CLAUDE.md and AGENTS.md; `.squads.toml` writes `active_backends = ["claude_code", "agents_md"]` (no `default_backend`). After adding an operator, `sq sync` refreshes both files. `sq check` passes clean.
    
    **US2 (empty / sq-only):** `sq init --backend none` writes `active_backends = []`, generates no agent files, `sq check` clean (no backend error).
    
    **none + real backend error:** `--backend none --backend claude_code` exits 1 with a clear error about cannot be combined.
    
    **Deactivation = ignore:** Dropping `agents_md` from `active_backends` in `.squads.toml` then running `sq sync` leaves AGENTS.md on disk untouched. `sq check` returns 0 (no missing-file error for deactivated backend).
    
    **sq check catches real gap:** Deleting CLAUDE.md from an active claude_code backend → `sq check` errors "CLAUDE.md: managed file missing — run `sq sync`" (exit 3).
    
    **Back-compat read:** Hand-written `.squads.toml` with `default_backend = "claude_code"` (schema 0.3) loads without migration. `sq check` passes. `sq migrate up` reports "already at schema v0.3; nothing to migrate". No migration runner for 0.3→0.4 exists (correct — tolerant read only).
    
    **No regression:** Default `sq init` (no --backend flag) produces single claude_code, CLAUDE.md only, `sq check` clean.
    
    **No 0.4:** SCHEMA_VERSION is 0.3 throughout.
    
    **Full suite:** 819 passed, 1 skipped.
- [2026-06-16T12:59:25Z] Paul Reviewer:
  - REV-000144: APPROVED. Independent review of FEAT-000138 multi-active backends complete.
  - Gate green: 819 passed / 1 skipped, pyright clean, ruff check + format clean. Repo squad at 0.3, sq check green; imports acyclic; Invariants 1 (nothing new in .squads.json) & 6 (no .claude/ reach-around) hold.
  - (a) Confirmed NO 0.4/migration residue in code — SCHEMA_VERSION=0.3, no _v0_3_to_v0_4 runner, registry stops at 0.3, no v0_4 corpus, _CORPUS_CASES ends at 0.3. (b) Confirmed managed_paths lists only guaranteed-written files: claude_code=[CLAUDE.md, .claude/settings.json], agents_md=[AGENTS.md]; read-only, conformance-covered for both.
  - Back-compat read of legacy default_backend verified (non-vacuously, via the v0_3 corpus). Fan-out verified across scaffold/sync/activate_role/add_dev/add_skill/regen/remove_item over the deduped list; --backend repeatable + none sentinel + none-with-real → SquadsError all verified by tests.
  - One LOW finding F1 (non-blocking): stale schema_version="0.4" literals in tests/test_agent_naming.py:186,198 — harmless residue, recommend changing to "0.3". @python-dev optional hygiene fix; no rework required for this approval.
<!-- sq:discussion:end -->
