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
created_at: '2026-06-16T11:58:36Z'
updated_at: '2026-06-16T11:59:52Z'
---
<!-- sq:body -->
## Context

Two coupled defects in the status vocabulary / workflow validation (BUG-142):

1. **Orphan bug vocabulary.** The `Status` enum carries `Open`/`Fixed`/`Verified`/`WontFix`,
   but no item workflow uses them — they are wired only into the review-*finding* sub-entity
   machine (`_workflow._FINDING`). Bugs run the generic work-item machine `_WORK`
   (`Draft → Ready → InProgress → InReview → Done`, + `Blocked`, `Cancelled`), so a bug never
   reaches a bug-flavoured state.

2. **Set-time validation gap.** `set_status` / `update(status=…)` validate a target status only
   through `_apply_status` → `can_transition` (`_services/_items.py:113`). That check answers
   "is this a legal *edge* from the current state?" — it never asks "is this status even a
   *member* of this type's workflow?". The only membership check lives in `sq check`
   (`_services/_maintenance.py:500`, `item.status not in workflow_for(item.type).states`). Two
   holes follow: (a) `--force` bypasses `_apply_status` entirely, accepting any enum value; and
   (b) when an out-of-vocabulary value happens to *not* be a legal edge, the user sees an
   `InvalidTransitionError` ("cannot move X → Y") that misdescribes the real problem (Y is not a
   state of this workflow at all). Concretely: BUG-134 was set to `Fixed`, committed, and only
   failed later at `sq check`.

The status vocabulary and the per-type workflows are **stability-contract surface that freezes at
1.0** (FEAT-13). This is therefore a pre-1.0 decision and must be recorded there.

Operator direction (op-pierre, 2026-06-16): give bugs a real lifecycle using the existing enum
values, and tighten set-status to reject out-of-workflow values at set-time.

## Decision

### 1. Bug workflow (new `_BUG` machine in `_workflow.py`)

Bugs get their own `Workflow`, distinct from `_WORK`, reusing existing `Status` members only
(no enum additions):

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

- **Terminal set (for scoping — inbox/list/blocked):** `Verified`, `WontFix`, `Cancelled`. These
  are added to / already in `_workflow.TERMINAL` (`Verified` and `WontFix` are already members;
  `Cancelled` already is). No change to `TERMINAL` is required — all three are present.

Rationale for the specific edges:

- **`Open` is initial**, not `Draft`: a bug is reported, not drafted. Matches the existing
  `_FINDING` machine, keeping the two bug-shaped lifecycles (item bug + review finding) aligned.
- **`Fixed → InProgress` reopens** (a fix that fails verification bounces back), and
  **`Verified → InProgress` reopens** (regression after sign-off). `Verified` is therefore
  *terminal-for-scoping but not a dead end* — exactly like `Done` in `_WORK` and `Approved` in
  `_REVIEW` (the `TERMINAL` docstring already notes terminal ≠ no outgoing edges).
- **`WontFix` is terminal** with a single re-open edge back to `Open` (a closed-as-wontfix bug
  can be reconsidered), mirroring `_FINDING`'s `WontFix → Open`.
- **`Cancelled`** is kept as a terminal escape hatch on the active states (parity with `_WORK`),
  with a `Cancelled → Open` re-open edge (parity with `_WORK`'s `Cancelled → Draft`). Use
  `WontFix` for "we decided not to fix it"; `Cancelled` for "this isn't a real bug / withdrawn".
- **`Blocked`** sits on the active path (`InProgress → Blocked → InProgress`), parity with `_WORK`.

`Draft`, `Ready`, `InReview`, `Done`, `Todo` are **not** bug states.

### 2. Set-time validation (close the gap)

Add a **membership check** in `_apply_status`, evaluated **before** the transition check and
**regardless of `--force`**:

```
def _apply_status(self, item, status, *, force):
    states = workflow_for(item.type).states
    if status not in states:
        raise StatusNotInWorkflowError(
            f"{status.value!r} is not a valid status for {item.type.value} "
            f"(allowed: {', '.join(sorted(s.value for s in states))})"
        )
    if not force and item.status != status and not can_transition(...):
        raise InvalidTransitionError(...)
    item.status = status
```

Composition with the existing check:

- **Vocabulary first, always.** Membership is a hard invariant of the type and is **not**
  overridable by `--force` — `--force` only relaxes the *transition* (edge) rule, never lets a
  bug become `Done`. This is the precise fix for hole (a).
- **`StatusNotInWorkflowError`** is a new `SquadsError` subclass (so `@handle_errors` renders it
  cleanly, exit 1) raised at set-time. This is the fix for hole (b): the user gets "X is not a
  valid status for bug" instead of a misleading transition error or a deferred `sq check` failure.
- The no-op case (`item.status == status`) still skips the *transition* check but now still
  passes the *membership* check (it must, since the current status is by construction a member),
  so no behaviour regression for idempotent sets.
- Applies uniformly to **all** types via `set_status` and `update(status=…)` — both already route
  through `_apply_status`. Sub-entity status setting (`_subentities.py:279`) already validates
  against `subentity_workflow(kind).states` at `sq check`; for symmetry the same set-time
  membership guard SHOULD be added there against `subentity_workflow(kind).states`, but that is a
  minor follow-on, not load-bearing for this bug.
- `sq check`'s membership check (`_maintenance.py:500`) **stays** as the defence-in-depth /
  rebuild-time invariant. It now becomes "should never fire for new edits" but still guards
  hand-edited or legacy files.

### 3. Back-compat — the load-bearing part

Inventory of existing bugs on disk (2026-06-16): **all nine closed bugs are `Done`**
(BUG-11/21/22/25/30/56/80/120/134); BUG-142 is `Draft`. No bug is in
`Ready`/`InReview`/`Blocked`/`Cancelled`. So once `_BUG` no longer accepts `Done`/`Draft`, every
existing bug breaks `sq check`. We MUST remap stored statuses.

**Chosen approach: a one-shot migration** that rewrites bug-item frontmatter `status` from the
generic vocabulary to the bug vocabulary. We do **not** widen `_BUG` to a superset — a superset
would re-introduce the orphan-vocabulary problem (two synonyms for "done") and pollute the 1.0
stability contract. A clean, narrow workflow + a migration is the minimal honest design.

Remap (generic `_WORK` status → bug status), applied to `type: bug` items only:

| Old (`_WORK`) | New (`_BUG`) | Reasoning                                                        |
|---------------|--------------|------------------------------------------------------------------|
| `Done`        | `Verified`   | A closed bug is a fixed-and-confirmed bug; `Verified` is `_BUG`'s settled-success terminal. |
| `Draft`       | `Open`       | Reported-but-not-started maps to the initial state.              |
| `Ready`       | `Open`       | "Triaged, ready to work" collapses to `Open` (no `Ready` in `_BUG`). |
| `InProgress`  | `InProgress` | Identical member — unchanged.                                    |
| `InReview`    | `Fixed`      | "Fix written, under review" maps to `Fixed` (awaiting `Verified`). |
| `Blocked`     | `Blocked`    | Identical member — unchanged.                                    |
| `Cancelled`   | `Cancelled`  | Identical member — unchanged.                                    |

Only `Done → Verified` and `Draft → Open` actually occur in the current corpus; the rest are
specified for completeness and for the FEAT-17 frozen fixtures. The migration is idempotent: a
status already valid for `_BUG` is left untouched.

This rewrites **frontmatter** (source of truth) — the index is rebuilt from it by the runner's
trailing `repair`. Invariant 1 (frontmatter-as-truth) holds.

### 4. Schema bump and sequencing vs FEAT-138

A stored-status remap is a frontmatter shape change, so it needs a `SCHEMA_VERSION` bump and a
runner. FEAT-138 is **concurrently** bumping `0.3 → 0.4` (`default_backend → active_backends`);
its runner `_v0_3_to_v0_4.py` already exists and is registered.

Therefore this decision's migration is **`0.4 → 0.5`** and MUST sequence **after** FEAT-138 lands:

- `_models/_schema.py::SCHEMA_VERSION` → `"0.5"` (bumped only **after** FEAT-138's `0.4` is on
  `main`; do not collide on this file while FEAT-138 is in flight).
- New runner `_migrations/_v0_4_to_v0_5.py::migrate(paths) -> int` doing the §3 remap (fully
  automatic; `MANUAL = ""`), appended to `_registry.MIGRATIONS` as a `Migration(version="0.5.0",
  from_schema="0.4", to_schema="0.5", …)` **after** the `0.4.0` entry.
- Per the FEAT-17 standing rule, add a **`v0_5` corpus fixture** under
  `tests/fixtures/corpus/v0_5/` (a frozen squad with at least one `Done` bug) and register it in
  `tests/test_migration_corpus.py::_CORPUS_CASES` so the remap is exercised and proven to reach
  `sq check`-clean.

If FEAT-138 were to slip and **not** ship a schema bump, this would instead be `0.3 → 0.4`; but
the working tree already carries FEAT-138's `0.4`, so plan on `0.4 → 0.5`.

We considered avoiding a schema bump via a superset workflow (no stored remap) — **rejected**:
it leaves orphan/duplicate vocabulary in the frozen 1.0 contract. A narrow workflow + a one-shot
remap is preferred and is minimal.

## Consequences

- Bugs gain a meaningful lifecycle; `sq blocked`/inbox/list scoping treat `Verified`/`WontFix`/
  `Cancelled` as settled.
- Out-of-workflow statuses are rejected at the point of edit for **every** type, with a clear
  error, and `--force` can no longer smuggle a wrong-vocabulary status past validation.
- One-way data migration; existing bugs are re-stated per the table. IDs/bodies untouched.
- **FEAT-13 must record the final bug lifecycle** in the stability-contract doc (the
  `Open → InProgress → Fixed → Verified` map + terminals above) before the 1.0 freeze. Flagged
  here; @manager files the deferral comment during the loop (not filed by this ADR).
- Follow-on (minor): add the same set-time membership guard to sub-entity status setting in
  `_subentities.py` for symmetry.

## Implementation pointers (for @python-dev)

- `src/squads/_workflow.py`: add `_BUG`, point `WORKFLOWS[ItemType.BUG]` at it (was `_WORK`).
  Confirm `TERMINAL` already contains `Verified`/`WontFix`/`Cancelled` (it does) — no edit needed.
- `src/squads/_services/_items.py::_apply_status`: add the membership check (force-independent),
  before the transition check.
- `src/squads/_errors.py`: add `StatusNotInWorkflowError(SquadsError)`.
- Migration `_v0_4_to_v0_5.py` + registry entry + `SCHEMA_VERSION="0.5"` + `v0_5` corpus fixture —
  **only after FEAT-138's 0.4 is merged**.
- Tests: service + CLI smoke for (a) bug transitions along the new map, (b) set-time rejection of
  `Done` on a bug (and with `--force`), (c) corpus migration reaching `sq check`-clean.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
