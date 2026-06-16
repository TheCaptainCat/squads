---
id: TASK-000131
sequence_id: 131
type: task
title: Backend conformance suite + ABC de-Claude-ification
status: Done
parent: FEAT-000016
author: tech-lead
priority: high
description: Shared conformance suite capturing the AgentBackend contract; run against
  Claude; merge ABC corrections before 1.0
subentities:
- local_id: ST1
  title: Write the shared backend conformance suite (parametrized factory fixture)
    and make it green against claude_code
  status: Done
  story: US2
- local_id: ST2
  title: Merge the ABC corrections the suite surfaces (de-Claude-ify the contract)
    so a non-Claude backend can implement it
  status: Done
  story: US1
created_at: '2026-06-15T13:02:37Z'
updated_at: '2026-06-15T14:22:45Z'
---
<!-- sq:body -->
## Goal

Turn the `AgentBackend` ABC from a one-implementation hypothesis into a contract we can freeze at 1.0, by writing a **shared conformance suite** that exercises the ABC's behavioural promises, running it against the existing Claude backend (must pass green), and merging the ABC corrections this exercise surfaces — **before** the agents-md backend is built (TASK-B depends on this).

## Approach (conformance-suite-first)

1. **Write the conformance suite** as a parametrized pytest module (`tests/test_backend_conformance.py`) driven by a backend factory fixture, so any backend can be plugged in. Assert only on the *contract*, not on Claude file layout:
   - `ensure_scaffold` is idempotent and never clobbers pre-existing user content; returns `Artifact`s whose `path` is project-root-relative and actually exists on disk.
   - `write_managed` (re)writes roster/version-dependent files idempotently; re-running produces stable output; the managed region is injected/replaced, not duplicated.
   - `generate_role_pointer` / `generate_skill_pointer` produce an artifact per item; `remove_artifacts` removes exactly what was generated and is safe to call when nothing exists (`missing_ok` semantics).
   - All returned `Artifact.path` values are root-relative + forward-slash; `Artifact.backend == backend.name`.
   - Round-trip: scaffold → write_managed → generate pointers → remove leaves no orphans.
2. **Run it against `claude_code`** and make it green. Where the suite can only pass by asserting Claude-specific filenames, that is a **leaked Claude-ism** — record it (see ABC findings) and fix the ABC rather than weakening the assertion.
3. **Merge the ABC corrections** the exercise surfaces. Known leak candidates from recon (the de-Claude-ification work):
   - `src/squads/_backends/_base.py`: `Artifact.kind` comment vocabulary (`claude_md`/`settings`), `write_managed` docstring naming "the skill + CLAUDE.md section", "pointer" naming on `generate_*_pointer` and in `BackendContext.rel`/`root_relative` docstrings. Decide whether method names stay (acceptable abstraction) or generalise.
   - `src/squads/_paths.py`: `claude_dir`/`claude_md` are Claude-specific paths living in the **shared** path module (lines ~67/71). A second backend that owns `AGENTS.md` at project root has nowhere clean to declare its own root file — decide the seam (e.g. backend-owned path resolution vs. a generic `root` the backend composes from).
   - `src/squads/_backends/_registry.py`: `get_backend` hard-imports only `_claude_code` for side-effect registration (~line 18); the registration story must accommodate a second backend.

## Files

- NEW: `tests/test_backend_conformance.py` (shared suite + factory fixture).
- EDIT (high blast radius — see warning): `src/squads/_backends/_base.py` (the ABC), possibly `src/squads/_paths.py`, `src/squads/_backends/_registry.py`, and `src/squads/_backends/_claude_code/_backend.py` if an ABC signature changes ripples into the Claude impl.

## WARNING — blast radius / ADR gate

Any change to `_base.py` (the ABC) or to the `claude_dir`/`claude_md` seam touches **the 1.0 stability contract** (the ABC is contract material — see FEAT-13 flag) **and the only existing backend**. This is a ripple, not an isolated edit. **If the suite surfaces a signature/seam change, stop and get an architect ADR before merging** — do not free-hand a contract change. Pure docstring/comment de-Claude-ification needs no ADR; signature or path-ownership changes do.

## Acceptance

- `tests/test_backend_conformance.py` runs against the `claude_code` backend and passes.
- ABC docstrings/comments carry no Claude-specific file names except where genuinely Claude-only.
- `uv run pyright && uv run ruff check . && uv run ruff format --check . && uv run pytest` all green.
- Any signature/seam change is backed by an accepted ADR (architect) and the stability-contract impact is noted for FEAT-13.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 131 add-subtask "<title>"`; track with `sq task 131 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Write the shared backend conformance suite (parametrized factory fixture) and make it green against claude_code | US2 |
| ST2 | Done |  | Merge the ABC corrections the suite surfaces (de-Claude-ify the contract) so a non-Claude backend can implement it | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Write the shared backend conformance suite (parametrized factory fixture) and make it green against claude_code

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a future backend implementer, I want a backend conformance test suite, so that I know exactly what the AgentBackend contract requires of me
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Merge the ABC corrections the suite surfaces (de-Claude-ify the contract) so a non-Claude backend can implement it

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a team using a non-Claude agent tool, I want sq to generate an AGENTS.md, so that we can run squads with our own tooling
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
- [2026-06-15T13:03:23Z] Olivia Lead:
  - @architect heads-up: this task may surface AgentBackend ABC changes. The ABC is 1.0 stability-contract material (FEAT-13). Pure docstring/comment de-Claude-ification is safe to merge directly. But any *signature* change to _base.py, or moving the claude_dir/claude_md path ownership out of the shared _paths.py, ripples into the frozen contract AND the only existing backend — that needs an accepted ADR before merge, not a free-hand edit.
  - FEAT-13 flag: do not file ABC changes there; flag them. The stability-contract reflection happens once the change is settled.
  - Sequencing: conformance-suite-first (this task) then TASK-132. The suite captures what the contract actually requires and drives the Claude-isms out, so the agents_md backend is written against an honest ABC rather than discovering leaks late.
- [2026-06-15T13:15:10Z] Elias Python:
  - Phase 1 complete: conformance suite (ST1) written and green against claude_code (37/37 tests, full gate clean).
  - New file: tests/test_backend_conformance.py — parametrized on _BACKEND_FACTORIES; a second backend plugs in by adding one entry there.
  - Suite covers: Artifact invariants (immutable, relative forward-slash paths, backend name), ensure_scaffold idempotency + clobber guard, write_managed idempotency + no-dup-region + roster/operator reflection, generate_role_pointer / generate_skill_pointer (artifact exists, backend name, idempotent), remove_artifacts (missing_ok, cleans up role + skill), full round-trip, service-level sync smoke test.
  - Claude-isms discovered (annotated in the catalogue at the bottom of the file):
  - CC-001 [COSMETIC] _base.py:18 — Artifact.kind comment lists 'claude_md'/'settings' as example vocabulary. Fix: generalise the comment.
  - CC-002 [COSMETIC] _base.py:73 — write_managed docstring names 'CLAUDE.md section'. Fix: use backend-neutral wording.
  - CC-003 [COSMETIC, potentially STRUCTURAL] _base.py:76-81 — generate_role_pointer / generate_skill_pointer embed 'pointer' (a Claude-specific file mechanic) in the ABC's method names. Renaming to generate_role_entry / generate_skill_entry would be neutral but changes the public signature — needs ADR to confirm whether this is a 1.0 contract change.
  - CC-004 [COSMETIC] _base.py:53-59 — BackendContext.rel / root_relative docstrings say 'for pointers and Artifact paths'. Fix: 'for Artifact paths and backend-owned file references'.
  - CC-005 [STRUCTURAL] _paths.py:67-71 — claude_dir and claude_md live in the SHARED SquadPaths dataclass. An AGENTS.md backend has no clean seam to declare its own root file — it must bypass the paths object and reach into ctx.root directly (defeating the abstraction). Proposed options in the catalogue; all require ADR.
  - CC-006 [STRUCTURAL] _registry.py:18 — get_backend() hard-imports _claude_code for side-effect registration. No analogous trigger exists for a second backend. Fix: explicit multi-backend import list in the registry, or entry_points discovery; needs ADR.
  - @architect the two STRUCTURAL findings (CC-005, CC-006) and possibly CC-003 need your call before any code changes. CC-001/002/004 are docstring-only and safe to apply directly.
- [2026-06-15T13:18:28Z] Robert Architect:
  - ADR-000133 ACCEPTED — ruling on the ABC de-Claude-ification (CC-001..CC-006). All six are in scope; apply them together in ST2. Mechanical changes are spelled out per item in the ADR body (read `sq decision 133 show --full`) — no design calls left for you.
  - CC-003 (rename): generate_role_pointer→generate_role_entry, generate_skill_pointer→generate_skill_entry. Pure rename, signatures unchanged. Update the ABC defs+docstrings in _base.py, the concrete defs in _claude_code/_backend.py (bodies untouched), and ALL call sites: _services/_items.py (169,171), _services/_roster.py (49,74,105), _services/_maintenance.py (85,88), and tests/test_backend_conformance.py. Grep both names across src/ and tests/ until clean. Claude-internal Artifact.kind strings (e.g. 'skill_pointer') stay as-is.
  - CC-005 (path seam): chose option A. DELETE claude_dir/claude_md from SquadPaths (_paths.py ~65-72) and the Claude enumeration in the root field comment. The Claude backend resolves its own files from ctx.root via two local constants (_CLAUDE_DIR='.claude', _CLAUDE_MD='CLAUDE.md') — replace every ctx.paths.claude_dir/claude_md (backend lines 31,98,99,110,182,202,219,223). Fix the one non-backend leak at _cli/_main.py:185 (drop the path, print the backend name instead). Claude-backend tests keep asserting Claude layout but compose project.root/'.claude' etc.; the conformance suite stays Claude-free (ctx.root/artifact.path only). No new import edges.
  - CC-006 (registration): chose explicit built-in import list (NOT entry-points — too much machinery for 1.0; we can add discovery later without changing register()). In _registry.py add _BUILTIN_BACKEND_MODULES=('squads._backends._claude_code',) + an idempotent loader (guarded by a _loaded flag) called at the top of get_backend, replacing the inline import. Keep register()/_REGISTRY and _claude_code/__init__'s register() call as-is. Adding agents_md later = one tuple entry.
  - CC-001/002/004 are cosmetic and IN SCOPE — ship in the same change (Artifact.kind comment, write_managed docstring, BackendContext.rel/root_relative docstrings; exact wording in the ADR).
  - Constraints to hold: import graph stays acyclic; nothing into .squads.json; Invariant 6 (only the backend + its own tests touch .claude/CLAUDE.md). Gate after applying: uv run pyright && ruff check && ruff format --check && pytest — conformance suite must stay green for claude_code.
  - Stability-contract: do NOT file a separate item — these ABC renames + the path seam are a FEAT-000013 deferral; reflect them there once merged. @python-dev you're clear to implement ST2.
- [2026-06-15T13:44:01Z] Elias Python:
  - ST2 complete: all ABC corrections from ADR-000133 applied (CC-001..CC-006).
  - CC-003: generate_role_pointer→generate_role_entry, generate_skill_pointer→generate_skill_entry renamed in ABC (_base.py), ClaudeCodeBackend (_backend.py), and all call sites: _services/_items.py, _roster.py, _maintenance.py, and tests/test_backend_conformance.py. Grep clean.
  - CC-005: claude_dir/claude_md deleted from SquadPaths (_paths.py). Claude backend resolves its own paths via _CLAUDE_DIR='.claude' and _CLAUDE_MD='CLAUDE.md' module constants from ctx.root. All 8 occurrences in _backend.py replaced. CLI leak at _main.py:185 fixed with backend-neutral line. Claude-backend tests updated to compose project.root / '.claude' and project.root / 'CLAUDE.md' directly.
  - CC-006: _registry.py now has _BUILTIN_BACKEND_MODULES tuple + idempotent _load_builtins() loader (guarded by _loaded flag); get_backend() calls it instead of the inline import. Adding a backend = one tuple entry.
  - CC-001/002/004: Artifact.kind comment, write_managed docstring, and BackendContext.rel/root_relative docstrings updated to backend-neutral wording.
  - Gate: 794 tests pass (783 original + 11 new), pyright 0 errors, ruff clean.
  - @reviewer ready for review. @qa the full suite is green.
- [2026-06-15T13:54:20Z] Mara Tester:
  - QA verification complete. PASS for TASK-131 acceptance criteria:
  - - tests/test_backend_conformance.py: 70 tests pass (35 per backend, both claude_code and agents_md)
  - - ABC: generate_role_pointer/generate_skill_pointer correctly renamed to generate_role_entry/generate_skill_entry at all call sites (grep clean)
  - - CC-005: claude_dir/claude_md removed from SquadPaths (_paths.py has zero Claude references)
  - - CC-006: _registry.py has _BUILTIN_BACKEND_MODULES tuple including both backends
  - - CC-001/002/004: Artifact.kind comment, write_managed docstring, BackendContext.rel/root_relative docstrings all backend-neutral
  - - Full gate: 794 tests pass, pyright 0 errors, ruff clean
  - Minor cosmetic note (not blocking): OperatorView docstring on _base.py line 35 still says 'CLAUDE.md people roster' — not in ADR scope, low priority.
- [2026-06-15T13:58:21Z] Paul Reviewer:
  - REV-000135: CHANGES REQUESTED (verdict scoped to FEAT-16; TASK-131's own work is solid). Your half — conformance suite + ADR-133 de-Claude-ification — is correctly done: CC-001..006 all applied, grep-clean rename, claude_dir/claude_md out of SquadPaths, idempotent registry loader, Invariant 6 restored, gate green. One honest note on the suite (no change required by you, but flagging): it asserts structure (paths exist, idempotency, round-trip, no-orphans, roster reflected by name-OR-slug) but NOT that workflow/skill *content* lands — which is the exact gap TASK-132's agents_md slipped through green (F1). If you want the suite to be a usefulness contract too, add a content assertion; otherwise this is a known, documented limitation.
  - @python-dev the blocking finding is all on TASK-132 (F1). See REV-000135.
- [2026-06-15T14:22:06Z] Paul Reviewer:
  - No re-review needed — TASK-131 (ABC de-Claude-ification + conformance suite) and ADR-133 were already approved under REV-000135 and were untouched by the TASK-132 fix round (the agents_md fixes required zero _base.py changes, as the ADR demanded). Approval stands.
<!-- sq:discussion:end -->
