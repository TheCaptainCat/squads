---
id: TASK-875
sequence_id: 875
type: task
title: Make sub-entity --force override the transition, not the vocabulary
status: Ready
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-873:fixes
description: A sub-entity status update under --force writes a value outside that
  kind's lifecycle at exit 0 and the integrity gate then errors; add the membership
  check the add path already performs.
subentities:
- local_id: ST1
  title: Membership check on the sub-entity status path
  status: Todo
- local_id: ST2
  title: Recovery from an already-invalid stored status
  status: Todo
- local_id: ST3
  title: Close the same write on the import route
  status: Todo
created_at: '2026-09-02T09:58:51Z'
updated_at: '2026-09-02T10:02:46Z'
---
<!-- sq:body -->
## What is wrong

`sq <type> <n> <kind> <k> update --status <S> --force` accepts any status in the squad's
global status set, including one that is not a member of that sub-entity kind's own
lifecycle. The write succeeds at exit 0. `sq check` then reports the corpus it just
produced as an **error** and exits 3. Three commands from a fresh init reach it, and all
three bundled kinds behave the same way.

A supported, documented verb produces a corpus the integrity gate rejects.

## The rule to implement

`--force` overrides an illegal **transition**. It never overrides the **vocabulary**.

That is already what it means at item level, because `update` runs the validator engine
after applying the delta: an illegal edge with a valid status passes under `--force`, a
status outside the type's declared set is refused even under `--force`. It is also
already what the documentation says for both layers — `docs/workflow.md` gives `--force`
the transition meaning for items and for sub-entities, and states the vocabulary meaning
for neither.

The sub-entity `add` path already performs the membership check the `update` path skips
(`add-subtask --status Verified` correctly exits 1). Two doors onto the same kind
disagree about the same value. That asymmetry is the defect.

## The constraint any fix must clear

Do not reach for an unconditional gate on the sub-entity status door. It is wrong, and
it is wrong in a way that is worse than the bug.

`<kind> <k> update --status … --force` is the **only** way out of the state this defect
creates. While an invalid sub-entity status stands, every gated door on the parent item
refuses and quotes the sub-entity's problem — the parent cannot be transitioned or
edited at all. Gating the one remaining door against the parent's full validator set
would make an already-corrupt corpus unrecoverable through the CLI: a bricking
regression, strictly worse than a red gate.

So the fix is narrow by construction: a **membership** check on the target status
against that kind's own declared lifecycle, at the same point and with the same message
shape the `add` path already uses. Not a general gate, and not the parent's whole
validator set.

## Recovery from a corpus that is already wrong

This is the half most likely to be got wrong, and it is why the fix needs to be driven
against a pre-corrupted squad and not only against a clean one.

After the fix, recovering a subtask whose stored status is `Verified` means running
`update --status Todo --force`. The **target** (`Todo`) is a member, so the new
membership check passes. But the **current** stored value (`Verified`) is not on the
machine at all, and the transition lookup has to read it. Whatever the transition layer
does with an origin state that is not a node — raise, return no edges, or fall through —
determines whether recovery still works. Establish that empirically; do not assume it.

## Scope decisions, so they are not re-litigated

**In scope — the import route's write.** `sq import` reaches this same core through a
`sub-status` event carrying `"force": true`. Fixing the core closes that write too, but
"closes it for free" is a claim, not a result: prove it at the import door as well as at
the CLI door.

**Out of scope — the importer's severity flattening.** `sq import` runs the validator
engine through `report()` rather than the gate, flattens error-level and warn-level
findings into one list, prints an error-level finding as `warning:`, and exits 0 keeping
the write. That is a genuinely separate defect: it is in the importer's result handling
rather than in the sub-entity write path, it applies to **every** error-level validator
and not just this one, and correcting it changes `sq import`'s exit-code contract for
adopters, which is an operator call and not a rider on a fix task. It is being raised as
its own item. Do not change `sq import`'s exit code or its report handling here.

**Out of scope — consolidating the duplicated story-mapping rule.** `_services/_subentities.py`
has no validator-engine call anywhere, and re-implements the story-mapping rule as
bespoke per-door guards. One rule, two independent implementations, which is a real
fragility. It is also, driven, not a reachable hole: every door that could break the
mapping refuses today. Consolidating it means deciding *which* validators run on *which*
sub-entity door, and the constraint above proves that answer is not "all of them on all
of them" — the `body` and `comment` doors have the same objection, since blocking the
discussion in which a recovery is coordinated makes a fail-closed design worse rather
than safer. That is a design question with a settled precedent to honour and a live
proposed catalog decision to fit into. It is not a rider on this fix. Leave the bespoke
guards exactly as they are.

## Acceptance

- A cross-kind status is refused at exit 1 with nothing written, **with and without**
  `--force`, on all three bundled kinds. Refusal names the offending value and lists the
  kind's own allowed statuses, matching the `add` path's message shape.
- An illegal **transition** between two statuses that *are* members still succeeds under
  `--force` at exit 0. This is the behaviour the fix must not take away, and it is the
  regression most likely to be introduced; assert it per kind.
- Without `--force`, an illegal transition between valid members still fails at exit 1
  with the existing message. Unchanged.
- Recovery from a pre-existing corrupt value is driven end to end: construct the corrupt
  state (write it however you must, since the CLI door is about to close), then
  `update --status <valid> --force`, then `sq check` exit 0, then a gated door on the
  parent exits 0. If recovery does not survive the fix, that is a blocking finding —
  stop and report it rather than shipping a bricking change.
- The import route is driven: a `sub-status` event with `"force": true` and a cross-kind
  status no longer writes it.
- `sq check` exits 0 on every corpus produced by these commands.
- Exit codes read from bare invocations, never through a pipe.
- **The tests fail before the fix.** Break the fix, watch each new test go red, restore
  it, watch it go green, and report both in the handoff comment. A test written to
  confirm a change rather than to disprove it has shipped three defects this release.
- Cover the shape families, not one instance per branch: kind x (member status /
  cross-kind status) x (with `--force` / without), table-driven, plus the two
  pipeline-level invariants — every write this path accepts leaves `sq check` clean, and
  every corpus this path can reach is recoverable through it.
- Name tests by behaviour. No ticket identifier in a test name, a file name, or a source
  comment.
- `uv run --all-extras pytest`, `ruff check .`, `ruff format --check .`, `pyright` and
  `sq check` all clean. `--all-extras` on each.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 875 add-subtask "<title>"`; track with `sq task 875 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Membership check on the sub-entity status path

<!-- sq:subtask:ST1:body -->
The core fix. On the sub-entity status update path, check the target status for
membership in that kind's own declared lifecycle before applying, and refuse a
non-member regardless of `--force`.

Mirror the `add` path, which already performs this check and already produces the right
message shape — it names the offending value and lists the kind's allowed statuses. Two
doors onto the same kind should not word the same refusal two ways.

`--force` keeps its existing effect on the transition: an illegal edge between two
statuses that are both members still succeeds under it. Do not touch that.

Resolve the allowed set from the kind's declared lifecycle in the active spec, not from a
literal list — a project can redeclare these, and a hardcoded set would be a second
source of truth for vocabulary the spec already owns.

Done when: a cross-kind status is refused at exit 1 with nothing written, with and
without `--force`, on all three bundled kinds; an illegal transition between members
still succeeds under `--force`; and without `--force` an illegal transition between
members still fails with the message it gives today.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Recovery from an already-invalid stored status

<!-- sq:subtask:ST2:body -->
The regression risk, isolated so it is driven rather than assumed.

Recovering a sub-entity whose stored status is already outside its machine means running
`update --status <valid member> --force`. The target is a member, so the new membership
check passes. But the stored current value is not a node on the machine, and the
transition lookup has to read it. What that layer does with an origin state it does not
know — raise, return no edges, or fall through — decides whether recovery still works
after the fix.

Establish it empirically against a squad that is already in the bad state. Construct that
state directly, since the CLI door that used to produce it is being closed by ST1.

This matters because that door is the only way out: while an invalid sub-entity status
stands, every gated door on the parent item refuses and quotes the sub-entity's problem,
so the parent cannot be transitioned or edited at all.

If recovery does not survive the fix, stop and report it. A change that closes the last
exit from a corrupt corpus is worse than the defect it fixes, and this subtask is where
that gets caught.

Done when: the full recovery sequence is driven end to end on a pre-corrupted squad —
force the value back to a valid member, integrity gate clean, a gated door on the parent
succeeds — and a test pins it so a later change cannot quietly take it away.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Close the same write on the import route

<!-- sq:subtask:ST3:body -->
The bulk-import surface reaches the same core through a sub-status event carrying a force
flag, and that is the only import route in — an add-sub event carrying a cross-kind
status is already refused in the pre-pass with nothing written.

Fixing the core should close this write too. That is a reasonable expectation and not a
result: drive it at the import door as well as at the CLI door, with an events file
carrying the force flag and a cross-kind status.

Strictly the write, not the reporting. The importer's habit of flattening error-level and
warn-level findings into one list, printing an error as a warning and exiting 0, is out of
scope for this task and is being raised separately — it is in the importer's result
handling, it affects every error-level validator rather than this one, and changing the
exit code is an adopter-facing contract change. Do not touch the exit code or the report
handling here.

Done when: the import route can no longer write a cross-kind sub-entity status, proven by
a test that runs the events file and asserts nothing was written; and the importer's exit
code and report formatting are unchanged by this task.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:02:46Z] Olivia Lead:
  - Scoped from BUG-873 and dispatchable. The rule is settled in the body — `--force`
    overrides the transition, never the vocabulary — so there is no design call left open for
    the implementer.
    
    Read ST2 before starting ST1. It is the reason this is three subtasks and not one: the
    door being narrowed is also the only way out of the state the defect creates, and whether
    recovery survives depends on what the transition layer does with a stored origin state
    that is not a node on the machine. Drive it, do not assume it, and stop and report rather
    than ship if it does not survive.
    
    Two things deliberately left out and recorded as such on the bug: the importer's
    severity flattening (a separate defect in the importer's result handling, with an
    adopter-facing exit-code contract change behind it) and the consolidation of the
    duplicated story-mapping guards (a design question with an open catalog decision it would
    have to fit). Do not widen into either.
    
    @python-dev ready for dispatch.
<!-- sq:discussion:end -->
