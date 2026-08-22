---
id: BUG-758
sequence_id: 758
type: bug
title: Workflow override multiplies whole-index parses outside the read scope
status: Verified
author: qa
refs:
- REV-757
- ADR-753
created_at: '2026-08-21T17:49:45Z'
updated_at: '2026-08-21T20:48:21Z'
---
<!-- sq:body -->
Re-driven independently, not inherited from the finding. Fresh squad, one task item, a
minimal two-line `.overrides/workflow.toml` (`[statuses.Frobbed]` / `role = "pending"`).
Instrumented `SquadsDB.model_validate_json` as a call counter and drove the real CLI app
in-process:

    command                       no override   with override
    sq list                       1 parse       3 parses
    sq <type> <n> show --json     2 parses      5 parses
    sq check                      1 parse       3 parses
    sq sync                       1 parse       3 parses

Matches the finding's table exactly. The extra parses come from
`validate_against_index_fail_closed` (`_workflow/_loader.py`, reached from the line-1255
call site), which does its own synchronous whole-index `model_validate_json` once per
`open_service` call, and only when a workflow override file is present — entirely outside the
request-scoped read snapshot. On a 720-item corpus that index parse costs ~26.4 ms (the
figure this repo's own request-scoped-snapshot decision measured), so the addressed-item show
form pays roughly three extra parses' worth of parsing time on top of the one the decision's
headline number assumes, and it falls only on adopters who customise the workflow — first-class
scope for this tool, not an edge case.

The architect's ruling on this (recorded as an amendment to the request-scoped-snapshot
decision) is explicit and binds the fix direction: the cross-check must NOT move inside the
read scope. It is a fail-closed validation, not a read, and memoizing a validation asserts the
corpus has not changed since the check passed — a materially stronger claim than memoizing a
read result. Admitting a storeless caller with a differently-shaped value into a scope that is
keyed on store identity and holds `SquadsDB` snapshots would also turn a narrowly-scoped
mechanism into a general-purpose per-invocation cache, a larger commitment than that decision
made.

The ruled fix direction instead: reduce the call count to once per invocation, anchored on the
same Click-root context the read scope already uses — either memoize the cross-check per
(squad_dir, spec) on that anchor, or hoist it to the root callback where the spec is bound,
rather than re-running it once per `open_service`.

Dependency, not a status: this reduction is the same shape as, and the amendment says should
follow, the `Service`-memoization fix for the still-open "2 reads for the addressed-item form"
gap on the same decision (also anchored on the Click root context) — the second memo is meant
to hang off the first rather than invent a second anchor. Sequence this after that work lands,
rather than in parallel with it.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T20:29:24Z] Catherine Manager:
  - Fix landed in ac0bebb on release/0.14 (TASK-763). Verified independently by counting SquadsDB.model_validate_json against the real CLI on an override-carrying probe: sq list, the addressed show form, sq check and sq sync each do 2 whole-index parses, down from 3. No-override squads are unchanged at 1.
  - Honest partial worth recording: this is 3 to 2, not 3 to 1, and the acceptance asked for the no-override count. The floor is structural under ADR-753 amendment A4 - the cross-check runs at spec-binding time, before any IndexStore exists, so it cannot share the read scope snapshot, and A4 forbids memoizing the validation itself. One cross-check parse plus one real read is the floor consistent with that ruling. Getting to 1 would mean inverting the order so the store is built before the vocabulary is validated, which is a different decision, not an optimisation.
- [2026-08-21T20:48:20Z] Mara Tester:
  - Verified by counting, not timing: instrumented SquadsDB.model_validate_json in-process against a fresh squad + one task. No-override squad unchanged at 1 parse for sq list, the addressed show form, sq check and sq sync. With a minimal two-line workflow override, all four are exactly 2 parses (down from 3), matching the fix's own claim of 3->2 rather than 3->1, and the structural-floor reasoning (A4 forbids folding the fail-closed cross-check into the read scope) holds up.
  - Critical check: dropped a live item's priority code from the collection via the same override (priority: urgent still on TASK-19, badges no longer declaring it) and confirmed sq list, the addressed show form, sq check and sq sync all still refuse the genuine corpus/vocabulary conflict with the same cross-check error naming TASK-19 -- the faster gate did not stop gating. sq repair still recovers as a clean bypass (exit 0, rebuilds).
<!-- sq:discussion:end -->
