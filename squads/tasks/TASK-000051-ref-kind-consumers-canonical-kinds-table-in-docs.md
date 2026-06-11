---
id: TASK-000051
sequence_id: 51
type: task
title: Ref-kind consumers + canonical kinds table in docs
status: Done
parent: FEAT-000035
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Single canonical eight-row kinds table in workflow.md.j2 (meaning/direction/consumer);
    ref add --kind help points at it
  status: Done
  story: US3
- local_id: ST2
  title: depends-on equivalence in sq blocked (A depends-on B == B blocks A; mixed
    usage works)
  status: Done
  story: US4
created_at: '2026-06-11T20:22:02Z'
updated_at: '2026-06-11T20:43:22Z'
---
<!-- sq:body -->
Wire the three new kinds into their consumers and ship the one canonical kinds table. Builds on TASK-000050 (the `VALID_REF_KINDS` constant must exist first). Per **ADR-000049**: closed vocabulary, no project-config lookup; `sq check`'s unknown-kind warning is a flat set-membership test; the docs table is the **contract wording**.

## Consumers
1. **`depends-on` ≡ `blocks` in `sq blocked`** — `src/squads/_services/_refs.py::blocked()` currently only matches `kind == "blocks"` ("A blocks B": B blocked while A open). Add the inverse: `A depends-on B` means **A is blocked by B** (edge stored on the dependent A, blocker is B). Mixed usage in one squad must work — an item blocked via either spelling shows once with its blocker(s). Mind the direction: `blocks` puts the blocker on the edge source; `depends-on` puts the dependent on the edge source.
2. **`sq check` unknown-kind warning** — `src/squads/_services/_maintenance.py` (the per-item loop ~line 250 that already emits dangling-ref warnings). For every ref whose kind is not in `VALID_REF_KINDS`, emit a `CheckIssue("warn", …)` naming the item and the offending edge (id + kind). **Warning, not error** — old files are data, not mistakes; no project-config exception path (ADR: stays a flat membership test).
3. **`sq check` Superseded-without-edge warning** — also in `_maintenance.py`: a decision with status `Superseded` that has **no incoming `supersedes` edge** gets a `CheckIssue("warn", …)`. Incoming = some other item's refs contain `"<this-id>:supersedes"`. (Inversion, like backrefs — never persist a backedge.)

## Docs — the canonical kinds table (US3, the contract)
- One table in `src/squads/_rendering/templates/workflow.md.j2` (shared by the `squads` skill and `sq workflow`). **Eight rows, no "add your own" footnote.** Each row: **kind**, **meaning**, **direction convention**, **consumer**.
  - Direction examples to state verbatim: `A blocks B` lives on A; `depends-on` lives on the dependent, with **`A depends-on B` ≡ `B blocks A`**; `supersedes` on the newer decision; `duplicates` on the later filing.
  - Consumers: `blocks`/`depends-on` → `sq blocked`; `fixes`/`addresses` → `sq check` task rules; `supersedes` → decision checks; `related`/`implements`/`duplicates` → navigation.
- **CLI help points at the table.** Update the `--kind` help on `ref add` (`_cli/_items.py`) — it currently lists only `related | blocks | implements | fixes | addresses` (stale, missing three). Make it enumerate the eight or point at `sq workflow`. Likewise the `create --ref` help if it implies a vocabulary.

## Boundary (do NOT do here)
The **stability-contract doc wording** ("vocabulary is closed in 1.0; unknown kinds rejected; extension reserved, additive & non-breaking") is **FEAT-000013's** to write — recorded on FEAT-000035. This task ships the *docs kinds table* and *help text* only, not the contract/stability doc.

## Acceptance
- `sq blocked` treats `A depends-on B` exactly as `B blocks A`; mixed usage in one squad works.
- `sq check` warns on unknown kinds in files (naming item + edge) and on Superseded decisions lacking an incoming `supersedes` edge — both warnings, exit code unaffected by warnings.
- `sq workflow` shows a single eight-row kinds table (meaning/direction/consumer); `ref add --kind` help references it / lists all eight.

## Tests
- Service: `blocked()` — `depends-on` edge produces the same blocked pairing as the equivalent `blocks`; a squad mixing both renders correctly.
- Check fixtures: a file with a junk kind → one warn naming item+edge; a Superseded decision with no incoming `supersedes` → one warn; the same decision *with* an incoming `supersedes` → no warn.
- CLI smoke: `sq workflow` output contains all eight kind names; `ref add --help` lists/points at them.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 51 add-subtask "<title>"`; track with `sq task 51 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Single canonical eight-row kinds table in workflow.md.j2 (meaning/direction/consumer); ref add --kind help points at it | US3 |
| ST2 | Done |  | depends-on equivalence in sq blocked (A depends-on B == B blocks A; mixed usage works) | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Single canonical eight-row kinds table in workflow.md.j2 (meaning/direction/consumer); ref add --kind help points at it

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a team member learning the system, I want one documented table of kinds with direction and consumers, so that I pick the right kind without archaeology across five docs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — depends-on equivalence in sq blocked (A depends-on B == B blocks A; mixed usage works)

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US4 — As a user drafting an item that needs another one first, I want to record depends-on from the item I'm editing, so that dependencies are authorable without touching the blocker
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
- [2026-06-11T20:39:38Z] Elias Python:
  - Implementation complete. All gates green (275 passed, 1 skipped; pyright 0 errors; ruff clean).
  - Changes: (1) `blocked()` in `_services/_refs.py` now consumes both `blocks` and `depends-on` — collects a set of blocker IDs per target, deduplicating items blocked via both edges. (2) `_maintenance.py _check_items` warns on unknown ref kinds (naming item + edge). (3) New `_check_decisions` static method warns when a Superseded decision has no incoming `supersedes` edge. (4) `workflow.md.j2` gains an eight-row kinds table (kind/meaning/direction/consumer). (5) `ref add --kind` help text points at `sq workflow`.
  - `sq sync` regenerated the squads skill — the table is now in `squads/agents/skills/squads.md`. The `sq workflow` command serves it directly from the template.
  - Actual squad: `sq check` reports two pre-existing `relates` (typo for `related`) edges on BUG-000022 and BUG-000025 — warnings, exit 0. These are data issues in existing items, not a regression from this task.
  - Ready for review. @reviewer
- [2026-06-11T20:43:22Z] Paul Reviewer:
  - Done via REV-000052 (Approved). depends-on/blocks equivalence, check warnings, and the eight-row kinds table verified live and by tests.
<!-- sq:discussion:end -->
