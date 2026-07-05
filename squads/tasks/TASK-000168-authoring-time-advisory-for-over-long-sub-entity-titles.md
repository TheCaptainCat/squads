---
id: TASK-168
sequence_id: 168
type: task
title: Authoring-time advisory for over-long sub-entity titles
status: Done
parent: FEAT-166
author: tech-lead
refs:
- ADR-167
subentities:
- local_id: ST1
  title: Add TITLE_ADVISORY_MAX=120 constant in _interactions.py
  status: Done
  story: US1
- local_id: ST2
  title: Carry title advisory on add-finding/add-subtask/add-story service results
  status: Done
  story: US1
- local_id: ST3
  title: Render advisory + reflog entry at the CLI edge for the three add-* commands
  status: Done
  story: US1
created_at: '2026-06-23T08:37:42Z'
updated_at: '2026-06-23T09:29:24Z'
---
<!-- sq:body -->
Add an advisory warning when a sub-entity title supplied to add-finding / add-subtask / add-story exceeds the threshold. Implements US1.

## Design (per ADR-167)
- Define a single module-level constant in _interactions.py — TITLE_ADVISORY_MAX = 120 (sits alongside CREATE_LANES). NOT .squads.toml-configurable.
- The check is advisory / warn-and-proceed: the sub-entity is created, the command exits 0, the warning is surfaced by the CLI. Mirror the CreateResult.lane_warning pattern from FEAT-122 / ADR-163 — carry the warning back on the service result, render it at the CLI edge.
- Fires at all three add-* entry points: add-finding, add-subtask, add-story. Titles at or below 120 produce no warning.
- Body presence is NEVER gated — only the long title triggers the advisory.

## Warning copy (pinned in ADR-167)
Advisory register, names the fix with real IDs, does not scold. Example:
    Title is 213 chars — a sub-entity title is a one-line handle, not the description. Put the detail in the body:
      sq review 165 finding F1 body -m "…"
The length and the body-set command must reflect the actual item/kind/index.

## Acceptance criteria
- add-finding / add-subtask / add-story with a title >120 chars prints the advisory warning, still creates the sub-entity, exits 0.
- The warning names the over-long title length and points to the correct sq <type> <n> <kind> <k> body -m … command for that sub-entity.
- Titles ≤120 chars produce no warning.
- The advisory is recorded in the reflog alongside the create event (as lane_warning is).
- No new mandatory arguments; no exit-code change.

## Tests
- Service-level test: result carries the advisory above threshold, none at/below.
- CLI smoke test for each of the three add-* commands (warning shown, exit 0, sub-entity created).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 168 add-subtask "<title>"`; track with `sq task 168 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add TITLE_ADVISORY_MAX=120 constant in _interactions.py | US1 |
| ST2 | Done |  | Carry title advisory on add-finding/add-subtask/add-story service results | US1 |
| ST3 | Done |  | Render advisory + reflog entry at the CLI edge for the three add-* commands | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add TITLE_ADVISORY_MAX=120 constant in _interactions.py

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an agent author, I want a warning when I give a sub-entity a long title
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Define TITLE_ADVISORY_MAX = 120 as a single module-level constant in _interactions.py, alongside CREATE_LANES. This is the one source of truth for the threshold (also consumed by TASK-169). Not .squads.toml-configurable per ADR-167.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Carry title advisory on add-finding/add-subtask/add-story service results

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an agent author, I want a warning when I give a sub-entity a long title
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
In the service layer for add-finding / add-subtask / add-story, compute an advisory message when the supplied title length exceeds TITLE_ADVISORY_MAX and attach it to the result object — mirroring CreateResult.lane_warning (FEAT-122 / ADR-163). The sub-entity is still created. Message is the pinned ADR copy: states the char count, that the title is a one-line handle, and the exact 'sq <type> <n> <kind> <k> body -m …' command for this sub-entity.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Render advisory + reflog entry at the CLI edge for the three add-* commands

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an agent author, I want a warning when I give a sub-entity a long title
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
At the CLI edge, render the advisory (if present) for each of the three add-* commands and record it in the reflog alongside the create event, the way lane_warning is surfaced. Command exits 0. Add CLI smoke tests: title >120 shows the warning and still creates + exits 0; title ≤120 is silent.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T09:11:01Z] Elias Python:
  - Implemented TASK-168 (authoring-time advisory for over-long sub-entity titles). All three subtasks done.
  - **Files changed:**
  - - `src/squads/_interactions.py` — ST1: added `TITLE_ADVISORY_MAX = 120` constant alongside `CREATE_LANES`; also fixed two pre-existing E501 violations in the playbook text.
  - - `src/squads/_services/_results.py` — ST2: added `title_advisory: str | None = None` field to `BlockResult`.
  - - `src/squads/_services/_subentities.py` — ST2: imported `TITLE_ADVISORY_MAX`, added advisory check in `_add_block` (fires when `len(title) > 120`), carries warning on `BlockResult`, records `title_advisory` dict in reflog delta.
  - - `src/squads/_cli/_common.py` — ST3: updated `print_block` to render the advisory (escaped via `e()`) on the human path and include it in `--json` output. Exit 0 always.
  - - `tests/test_title_advisory.py` — 38 new tests: constant sanity (2), service level covering all three add-* verbs + reflog + wording (26), CLI smoke tests for all three verbs + JSON + boundary (12 — including at/below-threshold silence and --json).
  - **Gate results:** pyright: 0 errors. ruff check: clean. ruff format: clean. pytest: 1009 passed, 1 skipped (pre-existing skip).
  - **Behaviour:** title length > 120 → advisory on result and in reflog; title length <= 120 → silent. Sub-entity always created; command exits 0. Warning names the char count and the exact `sq <type> <n> <kind> <k> body -m "…"` command.
- [2026-06-23T09:29:24Z] Paul Reviewer:
  - Reviewed under REV-172 — APPROVED, no findings.
  - Independently verified against ADR-167: threshold is the single TITLE_ADVISORY_MAX=120 constant (strict > comparison, silent at 120, fires at 121); advisory/warn-and-proceed across all three add-* verbs via the shared _add_block; body presence never gated; service stays silent and the warning rides on BlockResult.title_advisory, rendered only at the CLI edge (escaped via e(), present in --json); reflog delta records the advisory only when it fires; copy is honest (no enforce/guarantee/secur/forbid) and names the char count + the exact body command.
  - Ran tests/test_title_advisory.py (38 pass) and a live end-to-end check at 120/121 chars on add-finding — behaviour matches the ADR. @manager
<!-- sq:discussion:end -->
