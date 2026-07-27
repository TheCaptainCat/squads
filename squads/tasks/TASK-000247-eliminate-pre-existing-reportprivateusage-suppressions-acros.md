---
id: TASK-247
sequence_id: 247
type: task
title: Eliminate pre-existing reportPrivateUsage suppressions across service mixins
status: Draft
author: tech-lead
priority: low
refs:
- TASK-666:depends-on
- TASK-664:depends-on
description: 'Tech-debt: replace 29 cross-module private reach-ins in src/ with public
  APIs/accessors'
subentities:
- local_id: ST1
  title: Public store logging API and its 23 call sites
  status: Todo
- local_id: ST2
  title: Roster accessor, shared type-change helpers, full-ID predicate
  status: Todo
- local_id: ST3
  title: Prove the suppressions are gone and hold the gate
  status: Todo
created_at: '2026-06-30T08:51:11Z'
updated_at: '2026-07-27T15:12:11Z'
---
<!-- sq:body -->
Decision (Pierre, 2026-06-30): we stop suppressing pyright's `reportPrivateUsage`. Modules stay
private (leading-underscore), but cross-module code must not reach into another module's private
names behind a `# pyright: ignore`. Where an inner name is genuinely needed across a boundary,
make it public or expose a public accessor.

FEAT-209's own suppressions (Group A: `_active_spec` reach-ins, `_BUNDLED_SPEC`,
`Workflow._from_machine`) were already cleaned in that feature via
`active_spec()`/`bundled_spec()`/`Workflow.from_machine`. This task covers the pre-existing
Group B, unrelated to that feature.

This is a **visibility** change, not a de-privatisation: every module keeps its leading
underscore. What changes is which *names inside* those modules are part of their surface.

# Inventory

Derive the working list from `grep -rn "reportPrivateUsage" src/` at implementation time, not from
this body — the list recorded when this task was filed has already gone stale in both directions
(`discussion._status_badge`, `discussion._SUMMARY_COLS` and `common._active_dir` were cleaned by
the request-context work; two new reach-ins appeared in `_services/_rename.py`).

As it stands: **29 suppressions in `src/squads/`, four concerns.**

| # | Concern | Sites |
|---|---|---|
| 1 | `self.store._log(...)` from the service mixins | 23 (`_items` 6, `_subentities` 6, `_refs` 3, `_maintenance` 3, `_rename` 2, `_base` 1, `_collab` 1, `_retype` 1) |
| 2 | `svc._role_item` / `_skill_item` / `_operator_item` from `_cli/_common.py` | 3 |
| 3 | `_apply_type_change` / `_resync_edges` imported from `_retype` by `_rename` | 2 |
| 4 | `_is_full_id_shape` imported from `_cli/_common` by `_cli/_role` | 1 |

# 1. The store logging API

**`IndexStore.log(op: str, target: str, delta: dict[str, Any]) -> None`** — the existing `_log`,
made public, same signature, same behaviour. It buffers one reflog entry on the active
transaction context, snapshotting the ambient actor/clock/session at *buffer* time.

**No open transaction: it stays a silent no-op.** Not an oversight preserved out of inertia —
three reasons, in order of weight:

1. ADR-663 §4 makes silence load-bearing. The ambient context is task-local and store-scoped, and
   the logging entry point must **ignore** a context belonging to a different store. If `log()`
   raised on "no context for me", then a `log()` call on store B while store A holds an open
   transaction would raise instead of being ignored — turning a benign two-squads-in-one-process
   situation into a crash. Silence is the specified behaviour of that guard, so the public method
   inherits it.
2. Raising would manufacture the skew ADR-663 §1 forbids. Most callers write the markdown
   *before* they log (`_set_status_core` updates frontmatter, then logs). An exception from the
   logging call would abort the transaction after a durable markdown write and before the index
   commit — creating a real inconsistency to report a bookkeeping mistake.
3. The reflog is already under a never-raise contract on the other side of the commit: the store
   swallows a failed append and degrades to a warning. A pre-commit logging call that raises
   would contradict that stance within the same subsystem.

What replaces the raise as a safety net: the reflog assertions that already cover the mutation
cores. A core that forgets to log shows up as a missing `sq reflog` line, not as a silent
correctness bug.

**Provisional by design.** ADR-663 §4 records a promotion trigger: the first time the transaction
API is revised for fan-out/batch mutation or for the server, the handle becomes an explicit
parameter and the ambient binding is deleted — at which point this becomes `txn.log(...)`. Say so
in the docstring, and keep the surface minimal so that migration stays cheap: no overloads, no
return value for callers to depend on, no extra keyword arguments. Public visibility here is not a
commitment to `store.log()` as the permanent shape.

Considered and rejected: `log_op()` as the name. `log()` mirrors `_TransactionCtx.log`, which it
delegates to, and the symmetry is worth more than the extra syllable.

**This adds no ambient state.** ADR-534 §1 forbids module-level mutable state and prefers explicit
threading below the CLI edge; ADR-663 §4 sanctions one task-local binding here as the interim,
with the trigger above. Renaming `_log` to `log` neither adds a global nor changes what the method
reads. Nothing in this task touches the state question — that is TASK-666's, and this waits for it.

# 2. Roster lookups from the CLI

`_cli/_common.py::resolve_agent_addr` builds a dict of three bound private methods to dispatch
slug lookup by roster type. The dict-of-privates *is* the smell.

**Collapse all three into one public accessor:
`Service.roster_item(item_type: str, slug: str) -> Item | None`.** The three privates differ only
in the type constant they filter on, so one method parameterised by type removes the duplicated
index scan *and* the dispatch dict at the call site — `resolve_agent_addr` already has
`item_type` in hand.

Preserve one real difference the collapse must not flatten: `_skill_item` resolves the slug as
`extra.get(X.SLUG, it.slug)` — falling back to the item's own slug — while the role and operator
lookups use `extra.get(X.SLUG)` with no fallback. Keep that per-type behaviour rather than
picking one.

Update the six internal callers in `_services/` (`_roster.py` ×4, `_base.py` ×2) to the public
method and delete the three privates, rather than leaving thin delegating wrappers — two names for
one lookup is what this task exists to reduce.

Rejected: moving `resolve_agent_addr` into the service. It composes CLI-flavoured error messages
and feeds the address-dispatch group; it belongs at the CLI edge. One public accessor is the
smaller and more honest change.

# 3. The shared type-change helpers

`_services/_rename.py` imports `_apply_type_change` and `_resync_edges` from `_services/_retype.py`
— the per-item type-change core and the edge resync, shared by the retype and bulk-rename paths.

**Promote both in place: `apply_type_change`, `resync_edges`.** They are genuinely shared logic
with two legitimate callers, and their home in `_retype.py` is where the retype path put them
first.

Rejected for now: extracting them into a shared `_services/_typechange.py`. It is the better home
in the abstract, but a move is a structural refactor with no forcing reason today, and this task's
job is removing reach-ins. Worth revisiting when a third caller appears.

# 4. The full-ID predicate

`_cli/_role.py` imports `_is_full_id_shape` from `_cli/_common.py`. It is a pure two-line
predicate on a token, and `_common.py` already publishes helpers of exactly this kind
(`resolve_slug_or_raise`, `set_active_dir`, `e`).

**Promote to `is_full_id_shape`.** No accessor, no move.

# Scope: `src/` only, and what to do about the tests

The ~90 `reportPrivateUsage` suppressions under `tests/` are **out of scope**, and not because
they are tedious: a test that pins a module's internal behaviour is deliberate whitebox coverage,
not a design defect, and the largest block of them (`tests/tui/`) reaches into **Textual's**
private widget attributes — third-party names no API design in this repo can promote. Sweeping
them would either delete real coverage or replace it with worse assertions.

So the policy this task should land is a split, not a blanket: **`src/` may not reach into another
module's privates, enforced; `tests/` may.** The mechanism already exists in `pyproject.toml` —
the `[[tool.pyright.executionEnvironments]]` block rooted at `tests` that silences strict's
unknown-type family for the same "tests are different" reason. Add `reportPrivateUsage = "none"`
there, and the per-line ignore comments under `tests/` become redundant; removing them in the same
pass is worthwhile so nobody reads them as a live gate signal, but it is not what makes pyright
clean.

**This part needs sign-off before it lands** — it changes the shape of the gate, and a blanket-off
for tests could be read as walking back the original decision. If it is not ratified, the fallback
needs no design: scope the task to `src/` and leave the test-side comments exactly as they are.
Pyright ends clean either way; only the tidiness differs. Do not block on this — implement the four
concerns above first.

# Constraints

- Module privacy stays: no module loses its leading underscore. Only names inside them become
  public.
- No module-level mutable state, no process-global singletons (ADR-534 §1). Nothing here needs
  new state; if a step seems to, stop — that is a design change, not this task.
- No private→public import re-aliasing (`import X as _X`) to paper over a rename. Use the plain
  public name at every call site.
- Rename the prose too: docstrings that mention `store._log()` (in `_items.py`, `_retype.py`,
  `_subentities.py`) must name the public method, or the docs point at a name that no longer
  exists.
- One focused pass, one dev. Sequenced behind the durability work: TASK-666 replaces the attribute
  `_log` reads, and TASK-664 is concurrently rewriting the write calls in six of the eight modules
  this touches. Starting earlier means doing it twice or fighting merge conflicts.
- Gate: `uv run --all-extras pyright` at 0 errors / 0 warnings with the `src/` suppressions
  **removed, not relocated**, plus `ruff check .`, `ruff format --check .`, and the suite.

# Acceptance

- `grep -rn "reportPrivateUsage" src/` returns nothing.
- Pyright is 0/0 under `--all-extras`, and the rule is still at strict's error level for `src`.
- No behaviour change anywhere: the reflog output, the address resolution results, and the
  retype/rename paths are byte-identical before and after. This is a rename-and-promote pass; a
  diff that changes what a command does has gone wrong.
- `IndexStore.log()` documents its no-open-transaction contract and its provisional status.
- `Service.roster_item()` is the single lookup, with the per-type slug-fallback difference intact.
- `uv run sq check` clean; the suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 247 add-subtask "<title>"`; track with `sq task 247 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Public store logging API and its 23 call sites |  |
| ST2 | Todo |  | Roster accessor, shared type-change helpers, full-ID predicate |  |
| ST3 | Todo |  | Prove the suppressions are gone and hold the gate |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Public store logging API and its 23 call sites

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Make the store's reflog buffering public and convert its 23 callers.

`IndexStore._log` becomes `IndexStore.log`, same signature
(`op: str, target: str, delta: dict[str, Any]) -> None`), same behaviour. Its docstring gains two
things it does not say today: that calling it with no open transaction (or with an ambient context
belonging to a *different* store) is a deliberate silent no-op, with the reason; and that the
method is provisional — when the transaction API is next revised for fan-out or the server, the
handle becomes explicit and this becomes `txn.log(...)`.

Convert every call site: `_items` (6), `_subentities` (6), `_refs` (3), `_maintenance` (3),
`_rename` (2), `_base` (1), `_collab` (1), `_retype` (1). Each loses its trailing
`# pyright: ignore[reportPrivateUsage]` — removed, not moved to a file-level suppression.

Rename the prose too: docstrings in `_items.py`, `_retype.py` and `_subentities.py` refer to
`store._log()` in text. A doc pointing at a deleted name is worse than no doc.

Do not change the buffer-time snapshot behaviour. A single transaction can buffer several ops under
different ambient actor/clock bindings (the bulk importer rebinds per event inside one open
transaction), so each entry keeps its own ts/actor/session snapshot taken when it was buffered.

Acceptance:
- No `_log` name remains on `IndexStore`, and no call site carries a suppression.
- Reflog output is byte-identical before and after, for a single mutation and for a bulk import:
  same ops, same order, same timestamps, same actor/session lineage.
- A `log()` call outside any transaction is still a no-op and still raises nothing, covered by a
  test that says so deliberately rather than leaving it implied.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Roster accessor, shared type-change helpers, full-ID predicate

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The other three concerns — six suppressions, all mechanical once the shape is decided.

**Roster lookups.** Add `Service.roster_item(item_type: str, slug: str) -> Item | None` as the
single implementation, delete `_role_item` / `_skill_item` / `_operator_item`, and update the six
internal callers (`_services/_roster.py` ×4, `_services/_base.py` ×2). In
`_cli/_common.py::resolve_agent_addr`, the `_SLUG_LOOKUP` dict of bound private methods disappears
entirely — it already has `item_type` in hand, so it calls the accessor directly.

Keep the per-type difference: skill lookup resolves the slug as `extra.get(X.SLUG, it.slug)` (with
the item's own slug as fallback), role and operator use `extra.get(X.SLUG)` with none. Collapsing to
one method must not flatten that.

**Shared type-change helpers.** Promote `_apply_type_change` → `apply_type_change` and
`_resync_edges` → `resync_edges` in `_services/_retype.py`, and update `_services/_rename.py`'s
import to the public names. Leave them in `_retype.py`; do not move them to a new module.

**Full-ID predicate.** Promote `_is_full_id_shape` → `is_full_id_shape` in `_cli/_common.py` and
update the `_cli/_role.py` import plus the in-module caller.

None of these is a re-alias: use the plain public name at every call site, never
`import is_full_id_shape as _is_full_id_shape`.

Acceptance:
- All six suppressions gone, none relocated to a file-level or config-level waiver.
- Address resolution behaviour is unchanged for every input shape — full ID, bare number, and slug,
  across role, skill and operator, including a skill whose slug lives only in `item.slug`.
- The retype and bulk-rename paths produce identical results to before.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Prove the suppressions are gone and hold the gate

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Land the gate policy so the reach-ins cannot come back, and confirm the removal is real.

Verify first: `grep -rn "reportPrivateUsage" src/` returns nothing, and
`uv run --all-extras pyright` is 0 errors / 0 warnings with the rule still at strict's error level
for `src`. A suppression moved to a file header or a config waiver instead of deleted does not
count — that is the one outcome this task is defined against.

Then the `tests/` policy, which needs ratification before it lands (see the task body). If approved:
add `reportPrivateUsage = "none"` to the existing `[[tool.pyright.executionEnvironments]]` block
rooted at `tests` in `pyproject.toml` — the same block that already silences strict's unknown-type
family for tests — with a one-line comment giving the reason: a test pinning internal behaviour is
deliberate whitebox coverage, and `tests/tui/` reaches into Textual's own private widget attributes,
which no API design in this repo can promote. Then drop the now-redundant per-line ignore comments
under `tests/`, so nobody reads them as a live gate signal.

If it is not ratified, do nothing here beyond the verification above and leave the test-side
comments exactly as they are. Pyright is clean either way — this step changes tidiness, not
correctness. Do not hold the other two subtasks on it.

Acceptance:
- `grep -rn "reportPrivateUsage" src/` is empty and pyright is 0/0.
- The `src` gate still reports a new cross-module private reach-in as an error — demonstrate it once
  (add a reach-in locally, see pyright fail, revert), rather than assuming it.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the file
  rather than re-running to reslice output.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T15:03:14Z] Catherine Manager:
  - Embarked with the ADR-663 fix round (Pierre). Sequenced after TASK-666: the dominant Group B site (store._log from the mixins) reads _current_ctx, which TASK-666 replaces with a task-local ContextVar — the public logging API must be designed against that shape, not the attribute being deleted. Tech-lead designs the surface now; implementation follows 666.
- [2026-07-27T15:09:00Z] Olivia Lead:
  - Public surface designed in the body. Store API: `IndexStore.log(op, target, delta)` — same signature as `_log`, and the no-open-transaction case stays a **silent no-op**, deliberately. ADR-663 §4 requires the logging entry point to ignore a foreign store's context, and raising there would also abort a transaction after a durable markdown write (the §1 skew) to report a bookkeeping mistake. Docstring records it as provisional: it becomes `txn.log()` at §4's promotion trigger.
  - Other three concerns: one public `Service.roster_item(item_type, slug)` replaces the three private roster lookups and kills the CLI's dict-of-bound-privates (keep the skill-only `extra.get(X.SLUG, it.slug)` fallback); promote `apply_type_change`/`resync_edges` in place in `_retype.py` rather than extracting a shared module; promote `is_full_id_shape` in `_cli/_common.py`.
  - Two corrections to the filed scope: the site list was stale both ways (`_status_badge`/`_SUMMARY_COLS`/`_active_dir` already cleaned by the request-context work; two new reach-ins in `_services/_rename.py`), so it is 29 suppressions not ~20 — derive the list from a fresh grep. And added `depends-on TASK-664`: Elias is rewriting write call sites in six of the eight modules this touches.
  - One part needs your sign-off, flagged in the body as non-blocking: scoping the ~90 `tests/` suppressions out via `reportPrivateUsage = "none"` on the existing tests execution environment. Rationale is whitebox coverage + `tests/tui/` reaching into Textual's own privates, which we cannot promote. Fallback if unratified: scope to `src/`, leave the test comments alone — pyright is clean either way. @manager
- [2026-07-27T15:12:11Z] Pierre Chat:
  - Signed off: set reportPrivateUsage = "none" on the tests execution environment and delete the ~90 suppression comments. Not a walk-back of the 2026-06-30 decision — that rule targets cross-module private reach-ins in src/; a test pinning internals is deliberate whitebox coverage, and the tests/tui/ block reaches into Textual's privates, which no API design here can promote.
<!-- sq:discussion:end -->
