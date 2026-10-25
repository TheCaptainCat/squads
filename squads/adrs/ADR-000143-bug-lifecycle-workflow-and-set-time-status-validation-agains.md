---
id: ADR-143
sequence_id: 143
type: decision
title: Bug lifecycle workflow and set-time status validation against the type workflow
status: Accepted
author: architect
refs:
- BUG-142:addresses
- FEAT-13
- FEAT-138
- ADR-322
- ADR-696
created_at: '2026-06-16T11:58:36Z'
updated_at: '2026-10-25T21:48:37Z'
---
<!-- sq:body -->
## Context

Two coupled defects in the status vocabulary and its validation (BUG-142):

1. **Orphan bug vocabulary.** `Open`/`Fixed`/`Verified`/`WontFix` existed only in the review-finding
   machine, while bugs ran the generic work-item lifecycle
   (`Draft → Ready → InProgress → InReview → Done`, + `Blocked`, `Cancelled`), so a bug never reached
   a bug-flavoured state.

2. **Set-time validation gap.** Setting a status checked only whether the move was a legal *edge*
   from the current state, never whether the target is a *member* of the type's lifecycle; only
   `sq check` asked that. So `--force` could set any status, and an out-of-lifecycle target that was
   not a legal edge produced a misleading "cannot move X → Y" error. BUG-134 was set to `Fixed`,
   committed, and failed only later at `sq check`.

What freezes at 1.0 here is the set-time validation behaviour, the declared status-role vocabulary
the engine binds to, and this lifecycle as the bundled **default**. Status names are not contract
surface: a project may rename, reorder and replace them (ADR-322, ADR-474/604/696), and a project's
replacement lifecycle is held to the spec loader's reachability, single-initial and role-coverage
rules instead.

Operator direction (op-pierre, 2026-06-16): give bugs a real lifecycle using the existing status
names, and reject out-of-lifecycle values at set-time.

## Decision

### 1. The bug lifecycle

Bugs have their own lifecycle, `[lifecycles.bug]` in the bundled `src/squads/_specs/workflow.toml`:

- **Initial state:** `Open`.
- **Transition map:**

  | From         | To (allowed)                                   |
  |--------------|------------------------------------------------|
  | `Open`       | `InProgress`, `WontFix`, `Cancelled`           |
  | `InProgress` | `Fixed`, `Blocked`, `WontFix`, `Cancelled`     |
  | `Fixed`      | `Verified`, `InProgress`                       |
  | `Verified`   | `InProgress`                                   |
  | `Blocked`    | `InProgress`, `WontFix`, `Cancelled`           |
  | `WontFix`    | `Open`                                         |
  | `Cancelled`  | `Open`                                         |

- **Settled for scoping (inbox/list/blocked):** `Verified`, `WontFix`, `Cancelled`. Settledness
  derives from each status's declared role, not from a per-status flag.

Rationale for the edges:

- **`Open` is initial**, not `Draft`: a bug is reported, not drafted. This matches the finding
  machine, keeping the two bug-shaped lifecycles (item bug + review finding) aligned.
- **`Fixed → InProgress` reopens** (a fix that fails verification bounces back), and
  **`Verified → InProgress` reopens** (regression after sign-off). `Verified` is settled for scoping
  but not a dead end, like `Done` in the work lifecycle.
- **`WontFix`** is settled, with a single re-open edge back to `Open`, mirroring the finding
  machine.
- **`Cancelled`** is a settled escape hatch on the active states, with a `Cancelled → Open` re-open
  edge. Use `WontFix` for "we decided not to fix it"; `Cancelled` for "this isn't a real bug /
  withdrawn".
- **`Blocked`** sits on the active path (`InProgress → Blocked → InProgress`).

`Draft`, `Ready`, `InReview`, `Done` and `Todo` are not bug states in the bundled default.

### 2. Set-time validation

Setting a status runs a **membership check** in `_apply_status` (`_services/_items.py`), **before**
the transition check and **regardless of `--force`**:

```
def _apply_status(self, item, status, *, force):
    states = <the item type's lifecycle states>
    if status not in states:
        raise StatusNotInWorkflowError(
            f"'{status}' is not a valid status for {item.type} (allowed: …)"
        )
    if not force and item.status != status and not self.spec.can_transition(item.type, item.status, status):
        raise InvalidTransitionError(...)
    item.status = status
```

- **Vocabulary first, always.** Membership is a hard invariant of the type and is **not**
  overridable by `--force` — `--force` relaxes only the *transition* (edge) rule, never lets a bug
  become `Done`.
- **`StatusNotInWorkflowError`** is a `SquadsError` subclass raised at set-time, so the user gets
  "X is not a valid status for bug" instead of a misleading transition error or a deferred
  `sq check` failure.
- The no-op case (`item.status == status`) skips the transition check and passes the membership
  check, so idempotent sets are unaffected.
- It applies uniformly to **every** type, through both `status` and `update --status`. Sub-entity
  status setting has the same set-time membership guard against its kind's lifecycle.
- `sq check`'s membership check stays as defence in depth for hand-edited or legacy files.

### 3. Existing bugs — remapped in place, no migration

No schema bump and no migration runner ship for the bug lifecycle (op-pierre, 2026-10-25): 0.3 was
still in development when it landed, and the existing bugs were remapped in place.

The remap applied, for the record of what each old status meant:

| Old (work lifecycle) | New (bug lifecycle) | Reasoning                                                        |
|----------------------|---------------------|------------------------------------------------------------------|
| `Done`               | `Verified`          | A closed bug is a fixed-and-confirmed bug.                       |
| `Draft`              | `Open`              | Reported-but-not-started maps to the initial state.              |
| `Ready`              | `Open`              | "Triaged, ready to work" collapses to `Open`.                    |
| `InProgress`         | `InProgress`        | Identical member.                                                |
| `InReview`           | `Fixed`             | "Fix written, under review" awaits `Verified`.                   |
| `Blocked`            | `Blocked`           | Identical member.                                                |
| `Cancelled`          | `Cancelled`         | Identical member.                                                |

A bug carrying an old work-lifecycle status is reported by `sq check`'s membership check, and moved
with `sq bug <n> status <new> --force`.

A superset lifecycle (keeping `Done`/`Draft` valid for bugs) was rejected: it would leave two
synonyms for "done" in the bundled default.

## Consequences

- Bugs have a meaningful lifecycle; `sq blocked`/inbox/list scoping treat `Verified`/`WontFix`/
  `Cancelled` as settled.
- Out-of-lifecycle statuses are rejected at the point of edit for **every** type, with a clear
  error, and `--force` cannot set a wrong-vocabulary status.
- No migration exists for this change; a squad holding a bug in an old work-lifecycle status sees it
  in `sq check`.
- The stability contract records the bundled bug lifecycle as the default, and the set-time
  membership check, its force-independence and its distinct error type as the guaranteed behaviour.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:36:04Z] `architect` Robert Architect:
  - Amended in place; nothing retired. Both substantive rulings verified edge for edge: `[lifecycles.bug]` in the bundled spec reproduces section 1s table row for row with `initial = "Open"`, and `StatusNotInWorkflowError` fires from `_apply_status` at `_services/_items.py:397` before the transition check and independently of `force`, which is exactly what section 2 required.
  - Narrowed the framing clause, and this is the one the audit rightly put ahead of the cosmetic fixes: "the status vocabulary and the per-type workflows are stability-contract surface that freezes at 1.0" was true of a `StrEnum` codebase and is false now. Stated precisely what moved where — names are adopter-renamable (ADR-322, then ADR-474/604/696 binding engine behaviour to a declared status role), while what actually freezes is the set-time membership check with its force-independence and distinct error type, the role vocabulary a lifecycle must supply, and this lifecycle as the bundled default.
  - Flagged for whoever runs the bundled-assumption sweep off this map: read the clause as narrowed, not as written. Left as written it will report every renamable status name as a frozen surface the code fails to guarantee, which inverts the finding.
  - Marked the implementation-pointer section historical rather than rewriting it — no `Status`/`ItemType` enum, no `_workflow.py` module, no `_workflow.TERMINAL`. Worth noting the one citation that needed no correction: `workflow_for(type).states` is still the membership source, which is why section 2s check survived the de-typing untouched. Added `related` edges to ADR-322 and ADR-696.
- [2026-10-25T21:47:47Z] `op-pierre` Pierre Chat:
  - No remap runner: 0.3 was still in development, and the existing bugs were remapped in place. Record that no migration ships.
- [2026-10-25T21:48:37Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten in present tense on op-pierre's ruling (84a8acb). No remap runner ships; the existing bugs were remapped in place. Removed the false 'remap runner shipped' claim, the 0.4→0.5 migration plan, the implementation pointers and the amendment note. The lifecycle and the set-time check are unchanged.
<!-- sq:discussion:end -->
