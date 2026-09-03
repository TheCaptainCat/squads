---
id: TASK-759
sequence_id: 759
type: task
title: Memoize the Service per invocation so one command reads once
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- ADR-753:implements
- REV-757:addresses
description: Share one Service across both bridge crossings of the addressed-item
  form, plus the roster-regen defensive copy
created_at: '2026-08-21T17:51:04Z'
updated_at: '2026-08-21T18:37:03Z'
---
<!-- sq:body -->
`sq <type> <n> <verb>` — the addressed-item form the skills, the docs and every agent brief use —
crosses the sync-to-async bridge twice for one invocation the user issues once: the Typer group's
id-resolving callback (`_resolve` in `_cli/_items.py`) and the leaf verb, as two sequential
`anyio.run` calls rather than one nested in the other. Each crossing calls `get_service()`, which
calls `open_service` unconditionally, so each mints its own `Service` and its own `IndexStore`. The
read scope is keyed on store instance identity, so two stores means two index reads.

Memoize the `Service` for the invocation so both crossings share one store and one snapshot.

## What this closes

ADR-753's summary line ("one index load per invocation") and its Consequences ("one invocation
observes one index state") are both unmet for that form. Amendment A2 rules the guarantee **kept**
rather than restated to match the shortfall — it is the correctness half of the decision, not the
speed half — and names this work as what closes it. Measured, per A2:

| form | index reads |
|---|---|
| `sq list` | 1 |
| `sq show <id> --json` | 1 |
| `sq <type> <n> show --json` | 2 |

The N+1 is genuinely gone (12 sub-entities cost 2 reads, not 14), so what remains is a constant. But
two lock-free reads of a mutable file in one invocation are two chances to observe different states:
the callback resolves the id from one snapshot, the verb renders from another. A constant of 2 is not
1, and the decision claimed 1.

Two other things fall out in the same stroke. The id-resolving callback currently builds a `Service`,
keeps only the resolved id, and discards it — sharing that instance is the whole fix. And the
cross-call scope machinery becomes load-bearing: today it is indistinguishable from a plain per-call
`with read_scope():`, because the two crossings never share a store, so no load-count assertion can
tell the two implementations apart.

## Design constraints

- **The memo hangs off the Click root context — the same anchor the read scope already uses**
  (`ctx.meta` keyed per Click's convention, torn down by `root.call_on_close`). Do not invent a
  second anchor, and do not add a second teardown path. Per A1 that root context is the one object
  Click builds exactly once per dispatch and tears down exactly once at the end; per A4 a later memo
  on the same surface is expected to hang off this one.
- **Not an `IndexStore` instance attribute and not an `open_service` constructor flag** — A1 leaves
  everything §2 decided about the anchor binding, for the reason §2 gives.
- **`sq ui` keeps today's behaviour.** It is sync, decorated `@handle_errors` rather than the async
  bridge, and holds one `Service` for the whole session while other processes mutate the index
  underneath it. The memo must not pin a session-long terminal browser to launch-time state — the
  failure mode is silently serving stale data for as long as the session lasts, which is exactly why
  the decision refused an instance-lifetime cache.
- **Resolution semantics of every `get_service()` call site are unchanged.** There are ~83 of them
  and they are uniform today: `open_service(ctx.active_dir, client_cwd=ctx.client_cwd)`, reading the
  one `RequestContext` the root callback binds per invocation. `--dir` never touches any cwd;
  `client_cwd` is the walk-up base. A memo must preserve that exactly, not re-resolve and not widen
  it.
- **One construction path is deliberately different and must not be conflated with the memo.**
  `get_service_bypassing_index_cross_check()` — used by `sq repair`, and by `sq check` as its
  fallback — deliberately builds a `Service` that skips `open_service`'s live-index cross-check,
  because a validation gate that locks out its own recovery path is not a recovery path. A memo that
  cannot tell the two apart is a hole in both directions: a bypass-built instance served to a later
  plain caller silently skips a fail-closed check, and a plain instance served to `repair` reinstates
  the very refusal `repair` exists to clear. Key or gate the memo so each caller gets the
  construction it asked for, and cover both directions with a test.

## Fold in: the defensive copy at the roster-regen graft

`_refresh_catalog_extra` (`_services/_maintenance.py`) mutates `item.extra[key]` in place *before*
opening its transaction, then calls `db.add(item)` inside it — grafting a pre-transaction object into
a db read fresh from disk. Under a scope those items are identity aliases into the invocation's
snapshot, because `list_items` (`_services/_base.py`) returns the snapshot's own `Item` objects with
no copy.

**This is a locality change, not a safety fix.** The architect drove that the commit path is correct
today: `ensure_no_skew` runs inside that transaction *before* `db.add` and aborts on any divergence
on an index-authoritative key, and the permitted-skew set and the set the graft reasserts from
`RoleDef.to_extra()` are the *same set* — so for every excluded key but one the grafted value is
authoritative rather than stale. None of it was introduced by the read scope; the aliases were
already pre-transaction objects before any of this work.

The problem is that the argument is correct but spread across three files, and a reader of
`_refresh_catalog_extra` cannot see it. Hand that function an explicit copy — or copy at the
roster-regen `list_items` call — so the graft is local-by-construction rather than safe-by-trace. A
role item measures about 0.01 ms. Cite amendment A3, which states the general rule the copy makes
local: **a read result may be mutated in place only by a caller that also owns the write seam for
it, and must never be grafted into a transaction db it did not come from; where a caller does both,
it copies first.**

Do not extend this into copying every read. The decision's own measurement (13.7 ms to copy the
whole db against 26.4 ms to load it) rules that out, and it is one caller's list that needs copying.

## Fold in: the test that currently locks the gap in

`test_per_type_show_json_load_count_is_flat_but_not_one` in
`tests/cli/test_show_json_single_index_load.py` asserts the 2-load status quo. That was the right way
to record a known gap, and closing the gap turns it red — deliberately. It is rewritten as part of
this change, not worked around.

Per A2, **the replacement asserts shared store identity across both bridge crossings**, not merely a
load count. A load count alone cannot distinguish cross-call scoping from per-call scoping: driven
with a per-call fake anchor, both implementations produce `loads=2 stores=2`, identical. So a
count-only assertion leaves the most intricate part of the mechanism unpinned — swap the
`ctx.meta`/`call_on_close` machinery for a plain per-call `with read_scope():` and the suite stays
green. Assert the identity (one store object, or one populated snapshot map, observed across both
crossings) so that swap goes red.

## Sequencing

A separate defect covers the whole-index parse multiplication that appears when a project has a
workflow override — the pre-service cross-check running once per `open_service` rather than once per
invocation. QA is filing it in parallel. Per A4 its fix belongs on this same Click-root anchor and
therefore lands **after** this work, so the second memo hangs off the first rather than inventing a
second anchor. Do not attempt both here, and do not build an anchor that only the first one can use.

## Acceptance criteria

- **The asserted load count for `sq <type> <n> show --json` is 1**, on a multi-sub-entity item,
  measured by an instrumented counter around the disk read — not by wall clock.
- **`sq show <id> --json` stays at 1** and its flat-with-more-sub-entities property still holds.
- **A test asserts shared store identity across both bridge crossings** and goes red if the
  root-context anchor is replaced by per-call scoping. Falsify it that way and report red-then-green.
- **`sq ui` behaviour is unchanged**: no read scope is opened for it, and no snapshot or service is
  pinned for the life of the session. Cover it, since the failure is silent and long-lived.
- **The `--dir` and client-cwd resolution semantics of every `get_service()` call site are
  unchanged**, including the `--dir`-given branch that consults no cwd. A test that a `--dir`
  invocation and a walk-up invocation both resolve as they do today.
- **The bypass path stays separate in both directions**: `sq repair` and `sq check`'s fallback still
  get a cross-check-free `Service`, and no plain caller is ever handed one. Both directions tested.
- `test_per_type_show_json_load_count_is_flat_but_not_one` is rewritten rather than deleted or
  skipped, and the module's docstring stops documenting a 2-load status quo that no longer exists.
- **The roster-regen copy is in place**: `_refresh_catalog_extra` no longer grafts an object it did
  not copy, with a test that the copy exists at that seam. `sq sync` output and the resulting
  frontmatter and index are unchanged by the copy — this is locality, so behaviour must not move.
- The read count for the addressed-item form is reported before and after in a comment on this item,
  with the exact commands, alongside `sq list` / `sq show <id> --json` / `sq check` / `sq sync` /
  `sq repair` as controls. Check the probe before trusting a surprising number.
- `uv run --all-extras pytest --run-slow` is green, plus `tests/meta` — any new module-level binding
  goes past the mutable-state guard rather than around it, and a memo key belongs inside the existing
  anchor's `meta` namespace, not in a new module-level dict.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
- `CHANGELOG.md` carries an adopter-facing entry in the unreleased section for the addressed-item
  form now reading the index once.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 759 add-subtask "<title>"`; track with `sq task 759 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T17:51:25Z] Olivia Lead:
  - Authored against ADR-753 amendments A1-A4 (linked, implements) and the batch review (addresses). Scope: memoize the Service on the existing Click-root anchor so both bridge crossings of the addressed-item form share one store; fold in the roster-regen defensive copy (locality per A3, not a safety fix) and the rewrite of the test that asserts the 2-load status quo.
  - Two notes from reading the source. The ~83 get_service() call sites are uniform (open_service(ctx.active_dir, client_cwd=ctx.client_cwd)), so resolution semantics are one seam, not 83. The deliberately-different construction path I found is get_service_bypassing_index_cross_check() - sq repair, and sq check as its fallback - and a memo that cannot tell it apart from the plain path is a hole in BOTH directions: a bypass-built instance served to a later plain caller skips a fail-closed check, and a plain instance served to repair reinstates the refusal repair exists to clear. Acceptance requires both directions tested.
- [2026-08-21T18:29:25Z] Elias Python:
  - Implemented. get_service() (_cli/_common.py) now memoizes the Service on the Click root context's meta, gated on the same _READ_SCOPE_META_KEY the read scope already uses (so sq ui, which never opens a scope, never gets a Service pinned either). get_service_bypassing_index_cross_check() memoizes its fallback under a separate meta key, never shared with the plain path in either direction.
  - Before/after index reads (no workflow override), driven with an instrumented counter around IndexStore._read_from_disk on a matched fixture: sq list 1->1, sq show <id> --json 1->1, sq check 1->1, sq repair 1->1, sq sync 11->11 (per-role transactions, unaffected), sq <type> <n> show --json 2->1. With a .overrides/workflow.toml present (whole-index parses, read-scope loads + the pre-service cross-check's own synchronous parses): sq list 3->3 (unaffected, single crossing), sq <type> <n> show --json 5->3 (both open_service calls collapse to one, so the pre-service cross-check's own parse also halves as a side effect; the remaining 3 is the known A4 gap, out of scope here).
  - Store-identity test (tests/cli/test_show_json_single_index_load.py::test_addressed_item_form_shares_one_store_identity_across_both_bridge_crossings): records id(svc.store) from every get_service() call the addressed form makes and asserts both crossings return the same object, not just a matching load count. Verified red-then-green: reverting src/squads/_cli/_common.py alone reproduces the pre-fix shape (distinct store ids, load count back to 2); with the fix both assertions pass.
  - Bypass hole, both directions, in tests/cli/test_service_memo_bypass_isolation.py: (1) bypass fallback built while open_service is forced to raise is never handed to a later plain get_service() call in the same invocation -- it still raises; (2) the bypass path still recovers (does not start propagating the refusal) after memoization, and reuses an already-successful plain memo rather than building a redundant unvalidated instance when the cross-check is not actually failing. All four scenario tests fail with AttributeError against the pre-fix code (the two meta keys did not exist), confirming they exercise the new mechanism.
  - sq ui coverage (tests/tui/test_ui_command.py::test_ui_opens_no_read_scope_and_pins_no_service_memo): asserts no read scope is bound and none of the three meta keys are present on the root context during the session.
  - --dir / walk-up coverage for the addressed-item form (tests/cli/test_cli_plumbing_misc.py): one test with --dir from an unrelated cwd, one walk-up from a nested cwd; both assert the resolved id through both bridge crossings.
  - Roster-regen copy (A3): sync() in _services/_maintenance.py now copies each ROSTER_ROLE item out of list_items' result before the loop mutates it, so _refresh_catalog_extra's db.add never grafts a snapshot-owned object. Locality only -- tests/service/test_roster_regen_copies_before_mutating.py proves (a) an item a caller is still holding from an earlier list_items call in the same scope is untouched by a later sync() in that scope (red without the copy: the held object picked up the merged field), and (b) sync's output/frontmatter/index are byte-identical with and without a scope open.
  - test_per_type_show_json_load_count_is_flat_but_not_one renamed to test_per_type_show_json_loads_the_index_exactly_once and now asserts 1; module docstring no longer documents a 2-load status quo.
  - Gates: pyright/ruff check/ruff format clean; tests/meta clean; targeted sweep (index-store, service, role/override, check/repair, cli-show, plus every new/changed test file) 385 passed 1 skipped; full non-slow pytest suite 3716 passed 6 skipped. sq check clean on this repo; sq repair a stable no-op (only .reflog.jsonl gains an entry; .squads.json is byte-identical once key order is normalised).
  - CHANGELOG.md: folded the addressed-item-form fix into the existing 0.14.0 'dramatically faster' entry rather than adding a new one, and corrected its with-override numbers (five parses -> three).
  - REV-757 findings F5, F6 and F8 marked Fixed with a comment each citing this fix.
<!-- sq:discussion:end -->
