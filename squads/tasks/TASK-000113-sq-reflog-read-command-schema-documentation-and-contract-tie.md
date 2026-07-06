---
id: TASK-113
sequence_id: 113
type: task
title: sq reflog read command + schema documentation and contract tiering
status: Done
parent: FEAT-24
author: tech-lead
priority: medium
refs:
- FEAT-15
description: sq reflog read/filter command with --json passthrough, golden tests,
  and the documented/versioned line schema feeding the stability contract.
subentities:
- local_id: ST1
  title: 'sq reflog read command: tail by default, filter by --item/--actor/--op/--since,
    with --json passthrough'
  status: Done
  story: US1
- local_id: ST2
  title: 'Reflog back-compat: absent/truncated file never an error'
  status: Done
  story: US2
- local_id: ST3
  title: Version and document the line schema; golden-test the --json shape and state
    its stability tier in the contract doc
  status: Done
  story: US3
created_at: '2026-06-15T08:20:49Z'
updated_at: '2026-07-06T15:18:06Z'
---
<!-- sq:body -->
## Goal

The read side of the reflog: a `sq reflog` command that tails and filters the operation log, a
versioned + documented line schema, and its stability tier stated in the contract doc. Depends on
TASK-112 (which produces the lines).

## sq reflog command

A new read command alongside `inbox`/`blocked`/`search` in `src/squads/_cli/_main.py`:
- tail by default (most recent N lines);
- filters: `--item` (by target ID), `--actor`, `--op`, `--since` (ISO via `_clock.parse_iso`);
- `--json` passthrough — the line shape is emitted verbatim, joining FEAT-15's frozen
  machine-readable surface (same `console.print_json` idiom as the other read commands).

Service method (e.g. on `_maintenance` or a small reflog read mixin) reads + filters the JSONL;
reads never go through `store.transaction()` (read-only, no lock needed, mirrors `load()`).

## Back-compat (US2 acceptance)

- A squad with no `.reflog.jsonl` behaves identically to today — `sq reflog` on such a squad
  prints empty/“no history”, never errors.
- The reflog is **never** consulted for state: the index stays rebuildable from frontmatter alone
  (`sq repair` unaffected). A missing or truncated reflog is never an error anywhere.
- Add a test for the no-reflog squad and a truncated/partial-last-line squad.

## Schema versioning + contract (US3 acceptance)

- The JSONL line carries a schema version field; document the schema (field names, types, op
  vocabulary, delta format) — likely under `docs/` next to the FEAT-13 stability doc.
- Golden-test the `--json` shape (the project already uses golden files for the frozen surface).
- State the reflog line's stability tier in the contract doc (FEAT-13): which fields are
  promised stable through 1.0 vs. additive. **This is the contract decision the ADR must settle**
  (see deferral note below).

## Files to touch

- `src/squads/_cli/_main.py` — the `sq reflog` command (+ help, `--json`).
- `src/squads/_services/_maintenance.py` (or a new small read mixin + `_service.py` compose) —
  read/filter logic.
- `src/squads/_services/_results.py` — a `ReflogEntry`/result dataclass if needed for `--json`.
- `src/squads/_index/_reflog.py` (from TASK-112) — reuse the line model for parsing.
- `docs/` — schema documentation; cross-link from the stability contract.
- Golden-file test fixtures + a CLI smoke test.

## Acceptance

- `sq reflog` reads and filters by `--item/--actor/--op/--since`; tail default.
- `--json` shape documented and golden-tested.
- No-reflog and truncated-reflog squads behave identically (no error).
- Line schema versioned + documented; stability tier stated in the contract doc.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 113 add-subtask "<title>"`; track with `sq task 113 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | sq reflog read command: tail by default, filter by --item/--actor/--op/--since, with --json passthrough | US1 |
| ST2 | Done |  | Reflog back-compat: absent/truncated file never an error | US2 |
| ST3 | Done |  | Version and document the line schema; golden-test the --json shape and state its stability tier in the contract doc | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq reflog read command: tail by default, filter by --item/--actor/--op/--since, with --json passthrough

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an operator, I want a chronological log of every mutation with its actor, so that I can review what the agents did without having been in their conversations
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers the sq reflog read command alongside inbox/blocked/search: tail-by-default of the operation log with --item/--actor/--op/--since filters (ISO via _clock.parse_iso) and a --json passthrough emitting the line shape verbatim. Backed by a read-only service method that reads+filters the JSONL without store.transaction() (mirrors load()).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Reflog back-compat: absent/truncated file never an error

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a team member investigating an anomaly, I want removals, retypes and forced transitions explainable from the squad directory alone, so that a gap or surprise reads as history, not corruption
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Back-compat: a squad with no reflog file behaves identically; reflog never consulted for state, missing/truncated never an error.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Version and document the line schema; golden-test the --json shape and state its stability tier in the contract doc

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a tool builder, I want the reflog as stable, documented JSONL, so that I can build dashboards and automation on the operation stream
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Covers versioning and documenting the reflog line schema (field names, types, op vocabulary, delta format) under docs/ next to the stability doc, golden-testing the --json shape, and stating the line's stability tier in the FEAT-13 contract doc (which fields are promised stable through 1.0 vs additive).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T09:51:38Z] Elias Python:
  - TASK-113 complete. Delivered: sq reflog command in _cli/_main.py with --item/--actor/--op/--since/--tail/--json filters; read_reflog() method on MaintenanceMixin in _services/_maintenance.py; ReflogEntry dataclass in _services/_results.py. Back-compat (US2): missing or truncated .reflog.jsonl never errors, empty result returned. Schema (US3): .reflog.jsonl versioned at v=0.3 (SCHEMA_VERSION), schema documented in docs/workflow.md under 'Operation reflog' section; golden-file test at tests/goldens/reflog_shape.json confirms field set and schema version; 20 new tests in tests/test_reflog_read.py. Gate: 697 passed 1 skipped, pyright 0 errors, ruff clean. Builds on TASK-112 (InReview). @reviewer please review the read command, filter semantics, and --json shape. @qa please verify back-compat (no-reflog squad) and filter correctness in tests/test_reflog_read.py.
- [2026-06-15T09:59:12Z] Paul Reviewer:
  - Reviewed in REV-118 — APPROVED. Read side honors ADR-117 §2 reader contract: read_lines tolerates missing file → [], trailing partial line → silently skipped, interior malformed line → warn+skip, never raises. sq reflog tails (default 50, --tail 0 = all) and filters by --item/--actor/--op/--since (AND-ed), --json emits the ReflogEntry array. Schema is versioned (v='0.3' from line one), documented in docs/workflow.md with the field table + op vocabulary + the additive-delta stability note deferring the freeze to FEAT-13, and matches the golden tests/goldens/reflog_shape.json. @architect @python-dev
- [2026-06-15T10:15:16Z] Paul Reviewer:
  - Independent re-review REV-119 (supersedes REV-118). VERDICT: APPROVED.
  - Read side verified: sq reflog tails (--tail, 0=all) and AND-filters --item/--actor/--op/--since; --json emits the ReflogEntry shape and is golden-tested; --since invalid exits 1. Reader tolerance per ADR-117 §2 confirmed empirically — a trailing partial line is skipped silently, interior bad lines warn-skip, a missing reflog returns empty (back-compat). Schema documented in docs/workflow.md with the field table, op vocabulary, durability/ordering notes, and the stability tier deferred to FEAT-13.
  - Note F-findings on REV-119: the golden stores a structural descriptor rather than a byte-exact output (defensible given dynamic ts/IDs) — not raised as a blocker. 5 low findings total, none blocking. Gate green.
- [2026-06-15T10:16:08Z] Mara Tester:
  - INDEPENDENT QA VERIFICATION of TASK-113 — PASS on all acceptance criteria.
  - PASS sq reflog read command: tails by default (--tail 50), all filters work — --item (exact target match), --actor (exact actor match), --op (exact op match), --since (ISO-8601 >= comparison), AND-semantics across filters. --tail 0 returns all. Verified empirically.
  - PASS --json shape: 6 fields (v/ts/actor/op/target/delta) present and correctly typed. Matches goldens/reflog_shape.json. Schema version is 0.3.
  - PASS back-compat: squad with no .reflog.jsonl → sq reflog exits 0 with 'no reflog entries'. All mutating commands work identically without reflog. Missing reflog is never an error anywhere.
  - PASS reader tolerance: truncated trailing line (no terminating newline) skipped silently with no stderr output. Interior unparseable line warns to stderr but returns all remaining entries.
  - PASS not-a-source-of-truth: corrupt/missing reflog has zero effect on sq repair (rebuilds from .md), sq check (exits 0), or any command. Repair does not read .reflog.jsonl — confirmed by code reading and by corrupting the file then running repair successfully.
  - PASS schema documented in docs/workflow.md with field table, op vocabulary, and durability notes. Stability tier for delta fields deferred to FEAT-13 (documented as such).
<!-- sq:discussion:end -->
