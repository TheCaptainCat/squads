---
id: BUG-272
sequence_id: 272
type: bug
title: sq-bug skill + playbook advertise the wrong bug lifecycle string
status: Verified
author: python-dev
created_at: '2026-07-01T14:10:44Z'
updated_at: '2026-07-01T19:44:27Z'
---
<!-- sq:body -->
## Symptom

The shipped `sq-bug` managed skill and `_interactions/playbook.toml` advertise the bug lifecycle as:

`Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)`

That is the **generic task/epic/feature string, copy-pasted** — it is not the bug lifecycle. An agent reading the `sq-bug` skill is told bugs move through `Draft/Ready/InReview/Done`, none of which are valid bug states.

## Actual machine (authoritative — ADR-143, `default_workflow.toml [lifecycles.bug]`)

The bug machine linearizes to:

`Open → InProgress → Fixed → Verified (+ WontFix, Cancelled, Blocked)`

`Open`, `Fixed`, `Verified`, `WontFix` are the real bug states. So the advertised string is simply wrong; the state machine has always been correct.

## Root cause

`playbook.toml`'s `bug` `lifecycle = "…"` string was copy-pasted from the generic work-item string and never updated to the bug machine. Because the lifecycle string was hand-maintained separately from the machine, the two drifted with nothing checking them against each other.

## How it was found

Surfaced during TASK-269 (F3): wiring `linearize_lifecycle(machine_for(type))` into the `sq workflow` cheatsheet compared each built-in type's machine-derived lifecycle against its PLAYBOOK string and caught the mismatch (the manager guardrail that stopped the dev from silently reconciling).

## Fix

Correct the `bug` lifecycle string in `playbook.toml` to match the machine's canonical linearized form, and regenerate the `sq-bug` skill body golden deliberately (it is currently advertising a falsehood). **No state-machine change** — the machine is authoritative and correct. Being fixed as part of TASK-269's F3 reconciliation (which also makes `linearize_lifecycle` emit side-states in the canonical order so epic/feature/task/decision strings stay byte-identical).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T14:37:52Z] Elias Python:
  - Fixed in TASK-269 F3 reconciliation. Corrected playbook.toml bug lifecycle string from the copy-pasted generic work-item string to the machine-canonical form (Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled)). Also updated the sq-bug skill golden and test_playbook.py snapshot. F3's linearize_lifecycle wiring into the workflow cheatsheet now makes the state machine the authoritative source, preventing future drift. No state-machine change.
<!-- sq:discussion:end -->
