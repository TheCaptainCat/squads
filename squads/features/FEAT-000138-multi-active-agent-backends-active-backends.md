---
id: FEAT-000138
sequence_id: 138
type: feature
title: Multi-active agent backends (active_backends)
status: Done
parent: EPIC-000012
author: product-owner
priority: high
refs:
- FEAT-000016
- ADR-000133
- FEAT-000137
- FEAT-000013
subentities:
- local_id: US1
  title: Maintain multiple active backends at once
  status: Done
- local_id: US2
  title: Empty active_backends and deactivation-ignore semantics
  status: Done
- local_id: US3
  title: Migrate existing squads to active_backends schema
  status: Done
created_at: '2026-06-16T09:38:58Z'
updated_at: '2026-06-16T13:01:05Z'
---
<!-- sq:body -->
## Decision (op-pierre, 2026-06-16)

Replace the singular `.squads.toml` `default_backend: str` with a **list**:
`active_backends: list[str]`. A squad can run **multiple backends at once** —
e.g. maintain both `CLAUDE.md` and `AGENTS.md` for a mixed-tooling team. The
`sync`/scaffold/`write_managed` paths loop over **all** active backends instead
of resolving one.

Three semantics nail down the edges:

- **Empty `active_backends = []` is valid** — a "sq-only" squad that tracks work
  but generates no agent files. `sq check` has nothing to verify when the list
  is empty (no managed-file rule fires).
- **`sq check` verifies each *active* backend's managed files are present**
  (present-only per ADR-000141; drift/currency detection is deferred — it can be
  added later without a schema change, so it need not freeze at 1.0).
- **Deactivation = ignore, not delete.** Removing a backend from the list leaves
  its files on disk untouched; `sync` stops refreshing them and `sq check` stops
  checking them — they go stale harmlessly. No artifact deletion on
  deactivation. (Active cleanup/removal is the post-1.0 `sq backend remove`
  story in FEAT-000137, not here.)

## Why now (pre-1.0)

This is the **schema shape FEAT-000013 (stability contract) will freeze**.
`active_backends` is part of the durable `.squads.toml` surface; we must pick the
multi-active shape *before* 1.0 so the freeze doesn't lock us into the singular
`default_backend` and force a breaking change later. This directly **resolves
FEAT-000137's OQ-2 (single-active vs multiple-active)** in favour of
multiple-active, so FEAT-000137's post-1.0 management commands
(`sq backend add/switch/remove`) build on a list that already exists.

## Scope

This feature is the **schema + multi-active runtime + check rule + migration**:

- the `default_backend` → `active_backends` config-model change;
- the runtime fan-out (`_backend()` becomes "iterate active backends" across
  scaffold / sync / `write_managed` / role+skill entry generation);
- `sq init` / `sq adopt` populating the list from `--backend` (repeatable;
  `--backend none` → empty/sq-only) per ADR-000141;
- the new `sq check` rule (active backends' managed files present, empty ok,
  deactivated ignored) via the read-only `managed_paths` ABC probe;
- the `SCHEMA_VERSION` bump (0.3 → 0.4) + the `_v0_3_to_v0_4` migration
  (`default_backend` string → single-element `active_backends` list) + a new
  migration-corpus fixture for the now-previous schema (FEAT-000017 corpus rule).

**Out of scope** (deferred to FEAT-000137, post-1.0): the `sq backend`
add/switch/remove/list command group and active artifact cleanup on removal.

## References

- FEAT-000016 — the second backend (AGENTS.md) that makes multi-active real.
- ADR-000133 — de-Claude-ified the ABC; backends are now symmetric enough to run
  side by side.
- ADR-000141 — settles the multi-active design (migration mapping, order/dedup,
  init grammar, present-only check via `managed_paths`).
- FEAT-000137 — post-1.0 backend management; this resolves its OQ-2 (single vs
  multi) toward multi-active.
- FEAT-000013 — the stability contract that will freeze `active_backends`.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 138 add-story "As a <role>, I want … so that …"`; track with `sq feature 138 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Maintain multiple active backends at once |
| US2 | Done |  | Empty active_backends and deactivation-ignore semantics |
| US3 | Done |  | Migrate existing squads to active_backends schema |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Maintain multiple active backends at once

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a team using mixed agent tooling, I want a squad to keep several backends active at once, so that both `CLAUDE.md` and `AGENTS.md` stay generated and refreshed from one squad.

**Acceptance:** `active_backends` in `.squads.toml` is a list and accepts multiple entries; `sync`/scaffold/`write_managed` fan out over all active backends and produce each one's managed files; `sq check` verifies each active backend's managed files are present (present-only per ADR-000141; drift detection deferred).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Empty active_backends and deactivation-ignore semantics

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a squad operator, I want an empty `active_backends = []` to be a valid configuration (work tracked, no agent files generated), so that squads can be used as a pure work-tracker without any backend artifact.

**Acceptance:** a squad with `active_backends = []` passes `sq check` with no managed-file violations; `sync` is a no-op for artifact generation; removing a backend from the list leaves its on-disk files untouched, and `sync` stops refreshing them while `sq check` stops verifying them (they go stale harmlessly with no error).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Migrate existing squads to active_backends schema

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a developer upgrading an existing squad, I want a v0.3 squad with a singular `default_backend` string to migrate cleanly to a single-element `active_backends` list under the new `SCHEMA_VERSION`, so that my existing squad continues to work without manual intervention.

**Acceptance:** `sq migrate up` on a v0.3 squad rewrites `default_backend: <name>` to `active_backends: [<name>]` and bumps `SCHEMA_VERSION` to 0.4; `sq check` on the migrated squad passes cleanly; a committed migration-corpus fixture exercises this migration path in CI and is not vacuous.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-16T09:40:32Z] Olivia Lead:
  - @manager FEAT-000013 deferral flag (flagged, not filed): when this lands, the stability contract must FREEZE the `active_backends: list[str]` config shape — including the empty-list (sq-only) and deactivation-ignore semantics — as part of the durable .squads.toml surface. This is the grammar-settling decision FEAT-000013 owes a deferral entry per the EPIC-12 capstone rule.
  - Architect ADR needed FIRST (consistent with how we ADR'd removal/reflog/python-floor/the ABC): this changes an about-to-freeze schema, bumps SCHEMA_VERSION 0.3→0.4, and defines multi-active resolution semantics. The ADR must settle: (1) exact migration mapping default_backend→active_backends (and how a missing/empty source maps); (2) whether active_backends ORDER is significant (e.g. on overlapping file writes) and dedup policy; (3) how `sq init/adopt --backend X` maps onto the list (single element? repeatable flag? comma-list? how to express empty/sq-only); (4) what 'files present/current' means for the sq check rule and what ABC probe the backends expose for it; (5) confirm deactivation = ignore-not-delete (no artifact cleanup here; that's FEAT-000137). This resolves FEAT-000137 OQ-2 (single-vs-multi) toward multiple-active.
- [2026-06-16T09:45:59Z] Robert Architect:
  - ADR-000141 (Accepted) settles the multi-active design — @python-dev implement to its rulings; make no further design calls. Summary of the five points:
  - (1) Migration 0.3→0.4: default_backend="X" → active_backends=["X"]. CRITICAL: a missing/empty default_backend in an old squad migrates to ["claude_code"], NOT [] — pre-0.4 every squad had a backend; empty (sq-only) must be reachable ONLY by deliberate intent, never silently by migration (don't orphan a CLAUDE.md). Bump SCHEMA_VERSION to "0.4", add _v0_3_to_v0_4.py (rewrites .squads.toml only, MANUAL=""), register it. Corpus: keep v0_3 with the SINGULAR default_backend so the runner is non-vacuous (REV-130 lesson); add v0_4 (active_backends list, schema 0.4) and wire ("0.4","v0_4") into _CORPUS_CASES.
  - (2) Order NOT significant — the two backends write DISJOINT paths (claude_code: CLAUDE.md/.claude/+skills; agents_md: AGENTS.md/.agents_md), so order can't change bytes; don't rely on it. Dedup: collapse repeats on read, first-occurrence order, no error — every consumer iterates the deduped list.
  - (3) init/adopt: keep a single --backend Option made REPEATABLE (list[str]), default ["claude_code"]. --backend none (case-insensitive sentinel) → [] (sq-only); none may not combine with a real name (SquadsError). Full management is FEAT-137; init just seeds the list. Fix the _cli/_main.py:185 info line to print active_backends joined.
  - (4) sq check = PRESENT-ONLY (narrowing US1's 'and current' — drift can be added later without a schema change, so it need not freeze at 1.0). Add ONE minimal read-only ABC method: managed_paths(ctx)->list[str] returning the root-relative files the backend owns, WITHOUT writing (ensure_scaffold/write_managed write, so check can't reuse them). check loops active (deduped) backends, errors on any missing path. Empty list = nothing checked; deactivated backends = not probed. Add managed_paths to BOTH backends + the conformance suite.
  - (5) Deactivation = ignore-not-delete, CONFIRMED. No artifact cleanup in this feature — that's FEAT-137 post-1.0.
  - FEAT-13 freeze obligation NOTED (not filed by me): at 1.0 the stability contract must freeze the active_backends: list[str] shape incl. empty-[] (sq-only) + deactivation-ignore semantics + the present-only check rule + the 'none' init sentinel — @manager owes it a deferral entry per the EPIC-12 capstone rule.
- [2026-06-16T12:42:45Z] Elias Python:
  - The 0.4 schema bump and migration introduced by TASK-000139 was reverted per op-pierre: active_backends is part of the in-development 0.3 schema — no version bump, no migration. The feature's config model, back-compat default_backend read, multi-active fan-out, managed_paths probe, sq check rule, and all related tests (TASK-000140 scope) are fully retained. TASK-000139 (the migration task) is now void and should be cancelled. @manager
- [2026-06-16T12:54:27Z] Mara Tester:
  - QA verification completed for TASK-000140 (InReview) — all user story acceptance criteria pass.
    
    US1 (multi-active backends): PASS. Both CLAUDE.md and AGENTS.md coexist from a single squad init with two backends; both refresh on sync; sq check verifies both present.
    
    US2 (empty / deactivation-ignore semantics): PASS. sq-only squad (`active_backends = []`) generates no files, sq check clean. Deactivated backend's files survive on disk after sync; sq check ignores them (does not flag missing).
    
    US3 (tolerant read of legacy default_backend): PASS under revised framing (no migration, tolerant read). Legacy `default_backend = "claude_code"` in a 0.3 TOML loads transparently as `active_backends = ["claude_code"]`. No schema bump to 0.4. No v0_3_to_v0_4 migration runner exists or is needed.
    
    Schema is 0.3 throughout. Full test suite 819 passed, 1 skipped.
<!-- sq:discussion:end -->
