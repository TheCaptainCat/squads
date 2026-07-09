---
id: TASK-339
sequence_id: 339
type: task
title: Lead vocab-validation errors with the dropped-type cause, not sq repair
status: Done
author: tech-lead
assignee: python-dev
refs:
- ADR-322
- FEAT-281
created_at: '2026-07-08T16:13:06Z'
updated_at: '2026-07-09T19:24:18Z'
---
<!-- sq:body -->
## What this fixes

`_validate_item_vocab` in `src/squads/_index/_store.py` (~lines 76–93) fails
closed at `IndexStore.load()` on any item whose `type`, `status`, or
sub-entity `status` isn't in the active spec. That guard is correct and stays
exactly as-is — this task only rewrites its three error **messages**.

The messages currently misdiagnose. They uniquely blame index staleness and
point at `sq repair`. But when the real cause is a dropped / renamed /
re-prefixed still-populated type or status, `sq repair` rebuilds the index
*from the frontmatter* — which still carries the vanished vocabulary — so it
re-fails and sends the user in a circle. This is the now-primary cause under
the droppability contract (dropping a populated type is forbidden; a populated
drop/rename must go through a migration or re-type first).

## Scope (message strings only)

Rewrite the three `_validate_item_vocab` messages (unknown type, unknown
status, unknown sub-entity status) to **lead with the real cause**: the active
spec no longer declares this type/status → migrate or re-type its items first.
Demote the `sq repair` advice to a **secondary clause** for the genuinely
corrupt/stale-index case.

No behaviour change, no signature change, no source touched beyond these three
strings. Purely technical, low risk.

## Wording decision (from Robert's ruling on ADR-322)

Two options for the remediation citation:
- **Ideal (deferred):** cite FEAT-281's concrete re-type / migrate command
  surface. That command does not exist yet, so citing it now would ship a
  stale pointer.
- **Interim (ship now):** a citation-**free** honesty fix — name the
  drop/rename cause first and stop uniquely blaming `sq repair`, without
  pointing at a not-yet-built command.

Recommendation: ship the interim citation-free fix now. It's message-strings
only and immediately stops routing people into the repair loop. When FEAT-281
lands its re-type/migrate command, tighten the wording to cite it.

## Sequencing

`_store.py` is currently churning under TASK-338 (derive-prefix-from-id).
Dispatch this **after TASK-338 lands** to avoid an edit collision.

## Acceptance

- All three messages (unknown type, unknown status, unknown sub-entity status)
  name the dropped/renamed-spec cause **first**, with the `sq repair`
  stale-index advice demoted to a secondary clause.
- A test loads a squad whose spec has dropped a still-populated type and
  asserts the raised `SquadsError` message content leads with the real cause
  (not `sq repair`).
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean;
  full suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 339 add-subtask "<title>"`; track with `sq task 339 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T16:13:51Z] Olivia Lead:
  - Authored as an interim honesty-fix follow-up to Robert's droppability ruling on ADR-322. Targeting the 0.8 wave. Purely technical, message-strings-only, low risk — no change to the fail-closed guard itself.
  - Dispatch AFTER TASK-338 lands: _store.py is churning under 338 (derive-prefix-from-id), so touching these strings now would collide. Left standalone (no feature parent) since it doesn't implement FEAT-281; refs ADR-322 (the contract) and FEAT-281 (whose future re-type/migrate command the eventual final wording should cite) as related context.
- [2026-07-09T14:59:50Z] Elias Python:
  - Reworded the three _validate_item_vocab messages (unknown type/status, sub-entity status) to lead with the spec-drop/rename cause first, demoting sq repair to a parenthetical secondary clause; citation-free per Robert's interim ruling. Added a load() test with a spec missing a still-populated type, asserting the real-cause text precedes 'sq repair'. Updated the 3 existing IndexStore.load() message-match tests (repair()-path tests untouched, different message owner in _maintenance.py). pyright/ruff/format clean; hygiene + load_boundary_vocab targeted suites green.
- [2026-07-09T19:23:33Z] Paul Reviewer:
  - APPROVE — reviewer verification (independent).
  - All three _validate_item_vocab messages in src/squads/_index/_store.py (unknown type L109-113, status L114-119, sub-entity status L123-128) now lead with the real cause ('…which the active spec no longer declares; migrate or re-type this item before it can load again') and demote sq repair to a secondary parenthetical ('…or run sq repair if the index itself is merely stale').
  - Fail-closed guard behavior UNCHANGED: each branch still raises SquadsError at IndexStore.load(); only the message strings changed. Confirmed against the load-boundary suite.
  - Citation-free: no unbuilt command cited in source ('migrate or re-type' is generic prose, not a command surface); no squad IDs in the source strings (test_squad_ref_hygiene green). The task's FEAT-281 ref is sq linkage, not a source citation — fine.
  - test_load_error_leads_with_dropped_type_cause_not_sq_repair asserts message.index('no longer declares') < message.index('sq repair') on a genuine dropped-type spec (not corruption) — the right regression lock. Gates green (pyright/ruff/format); targeted + hygiene suites pass (215).
  - One LOW/non-blocking nit (out of scope for this task, pre-existing): tests/test_load_boundary_vocab.py:239 docstring still reads 'raw ValueError from _discussion._status_badge downstream' — that helper now lives at squads._badges.status_badge. Stale prose only, no code impact; sweep opportunistically.
<!-- sq:discussion:end -->
