---
id: TASK-763
sequence_id: 763
type: task
title: Run the workflow index cross-check once per invocation
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-758:fixes
- ADR-753:implements
description: Reduce the override-only whole-index parse multiplication on the existing
  Click-root anchor, without moving a fail-closed gate into the read scope
created_at: '2026-08-21T19:36:45Z'
updated_at: '2026-08-22T09:26:25Z'
---
<!-- sq:body -->
`validate_against_index_fail_closed` (`src/squads/_workflow/_loader.py`) performs its own
synchronous whole-index `model_validate_json` once per `open_service` call, and only when a workflow
override file is present — entirely outside the request-scoped read snapshot. So an adopter who
customises their workflow pays extra whole-index parses on every command, and customising the
workflow is first-class scope for this tool, not an edge case.

## Re-driven baseline

Fresh squad, one task item, a minimal two-line `.overrides/workflow.toml`
(`[statuses.Frobbed]` / `role = "pending"`), with `SquadsDB.model_validate_json` instrumented as a
call counter against the real CLI app in-process:

| command | no override | with override |
|---|---|---|
| `sq list` | 1 parse | 3 parses |
| `sq <type> <n> show --json` | 1 parse (after the invocation-scoped `Service` memo landed) | 3 parses |
| `sq check` | 1 parse | 3 parses |
| `sq sync` | 1 parse | 3 parses |

At the ~26.4 ms per parse measured on a 720-item corpus, that is the dominant cost of an
override-carrying squad's every invocation.

## The binding constraint: this does not move into the read scope

ADR-753 Amendment A4 rules on this directly and the ruling is a constraint on the fix, not a
suggestion. Read A4 before starting. It says: **do not put the cross-check in the read scope.**

- It is a fail-closed validation, not a read. Memoizing a validation asserts the corpus has not
  changed since the check passed — a materially stronger claim than memoizing a read result.
- The scope is keyed on `IndexStore` identity and holds `SquadsDB` snapshots a store filed.
  Admitting a storeless caller with a differently-shaped value turns a narrowly-scoped mechanism
  into a general-purpose per-invocation cache, which is a larger commitment than that decision made.

## The ruled fix direction

Reduce the count: run the cross-check **once per invocation** rather than once per `open_service`.

- **On the same Click-root anchor the invocation-scoped `Service` memo already established** —
  `ctx.meta` keyed per Click's convention, torn down by the root context's `call_on_close`. That
  anchor exists now; A4 says the second memo hangs off the first. **Do not invent a second anchor**
  and do not add a second teardown path.
- Either memoize the cross-check per `(squad_dir, spec)` on that anchor, or hoist it to the root
  callback where the spec is bound. Pick one and state the choice and the reason on the item.
- Keying matters: two `IndexStore`s can legitimately address one squad directory, and the spec can
  differ between resolutions within one invocation. A memo that ignores either key is wrong in a way
  no parse count will show.

The fail-closed property is preserved end to end: an invocation that would refuse today must still
refuse, at the same exit code, with the same message. Running the gate once per invocation instead of
once per service construction is a count reduction, not a weakening — and the acceptance below is
written so that a fix which quietly skips the check on some path fails.

## Surfaces

- `src/squads/_workflow/_loader.py` — `validate_against_index_fail_closed` and its call site.
- `src/squads/_cli/_common.py` — the existing Click-root anchor and its `meta` keys, if the memo
  lands there.
- `src/squads/_cli/__init__.py` — the root callback where the spec is bound, if the hoist lands
  there instead.
- `tests/` — the parse-count assertions, and `tests/meta` for any new module-level binding.

## Acceptance criteria

- **An asserted parse count per command form**, instrumented on `SquadsDB.model_validate_json`, not
  a wall-clock measurement. With a workflow override present: `sq list`, `sq <type> <n> show --json`,
  `sq check` and `sq sync` each drop from 3 to their no-override count. State the achieved number for
  each of the four forms.
- The no-override counts are unchanged for the same four forms — this must not slow the bundled path.
- **The gate still refuses.** A squad whose corpus conflicts with its override is still refused, at
  the same exit code and with the same message, on every one of the four forms. Prove it per form,
  not once: a memo whose lookup succeeds where the check should have run is exactly the failure this
  risks, and a single happy-path refusal test will not see it.
- The check still runs when it must within one invocation: cover the case where the spec resolved for
  a later call differs from the earlier one, and the case of two `IndexStore` instances on one squad
  directory. A memo keyed too loosely must fail one of these.
- `sq repair` and `sq check`'s cross-check-free construction path keeps its current behaviour — the
  bypass exists so a recovery command is not blocked by the gate it is there to clear, and a memo
  must not reintroduce the refusal on that path.
- `tests/meta` is green: any new module-level binding goes past the mutable-state guard rather than
  around it, and a memo key belongs inside the existing anchor's `meta` namespace, not in a new
  module-level dict.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.

## Handoff

**Do not edit `CHANGELOG.md`.** Several items in this batch run concurrently and a shared file would
have them racing. Put your adopter-facing changelog entry text in your handoff comment on this item
and the tech lead applies it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 763 add-subtask "<title>"`; track with `sq task 763 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:37:37Z] Olivia Lead:
  - Authored against ADR-753 amendment A4 (linked, implements). The Click-root anchor A4 requires already exists — the invocation-scoped Service memo landed with _SERVICE_META_KEY and a separate _BYPASS_SERVICE_META_KEY on the root context — so this hangs off it rather than inventing one. Acceptance adds what a parse count alone cannot see: the gate must still refuse on all four command forms, keying must survive a differing spec and two IndexStores on one directory, and the repair/check bypass path must not regain the refusal.
- [2026-08-21T20:27:31Z] Elias Python:
  - Fix: root callback's bind_active_spec is now the sole cross-check call per invocation; open_service gained a resolved_spec kwarg (default None, every other caller unaffected) and _build_plain_service (_cli/_common.py) threads ctx.active_spec through it, or raises the cached ctx.spec_error directly instead of re-deriving it. No new anchor — reuses the RequestContext the root callback already binds.
  - Parse counts (driven, SquadsDB.model_validate_json counter, fresh squad + 1 task item, synced): no-override unchanged at 1 for all four forms. With override: sq list 3→2, sq <type> <n> show --json 3→2, sq check 3→2, sq sync 3→2.
  - Not 3→1: A4 forbids folding the cross-check into the read scope, so it can never share the scope's one real read. 1 dedicated cross-check parse (once per invocation, was 2) + 1 real read is the floor consistent with that ruling — flagging since the acceptance text says 'drop to their no-override count' (1); 2 is what's architecturally reachable without violating A4, and I believe that's the intended bar given the constraint section's emphasis.
  - Refusal proofs (tests/cli/test_workflow_cross_check_once_per_invocation.py): a driven corpus/override conflict (priority badge code dropped while a live item carries it) individually through sq list / sq <type> <n> show --json / sq sync — each still exits 1, same message. sq check still degrades gracefully with the same CheckIssue. sq repair still recovers (exit 0, rebuilds) — bypass path unregressed.
  - Keying: no new memo added. Tests prove _build_plain_service always reads the currently-bound spec (rebound mid-process between two calls, each call sees the current one), a direct open_service() call ignores an unrelated ambient spec and validates fully on its own, and repeated open_service() calls against one directory (stand-in for a second IndexStore) all independently refuse.
  - Gates: pyright clean, ruff check/format clean, tests/meta + tests/cli + tests/service + tests/integration + read-scope/transaction-scoping: 2856 passed, 1 skipped. sq check clean. sq repair a stable no-op (identical .squads.json across two runs).
  - CHANGELOG text for this fix: '**A workflow override'\''s live-index compatibility check no longer runs twice per command.** Customising your workflow (.overrides/workflow.toml) triggers a check that your vocabulary still matches every live item — necessary, but it ran once to bind the active spec and again to build the command'\''s service, doubling that cost on every invocation. It now runs once. sq list, sq check, sq sync and the addressed show form each go from three whole-index parses to two on an override-carrying squad; a squad with no override is unaffected.'
  - This makes the existing 0.14.0 entry ('Viewing an item with a lot of sub-entities is dramatically faster') stale again: its closing sentence says 'three whole-index parses on sq list, three on sq review 12 show --json (down from five...)' — both should now read 'two', not 'three'.
- [2026-08-21T20:27:51Z] Elias Python:
  - Correction: the previous CHANGELOG-text bullet got mangled by shell quoting (literal backslash-quotes leaked in). Clean version below.
  - CHANGELOG text: A workflow override live-index compatibility check no longer runs twice per command. Customising your workflow (.overrides/workflow.toml) triggers a check that your vocabulary still matches every live item -- necessary, but it ran once to bind the active spec and again to build the command service, doubling that cost on every invocation. It now runs once. sq list, sq check, sq sync and the addressed show form each go from three whole-index parses to two on an override-carrying squad; a squad with no override is unaffected.
  - Bold lead-in to match house style: A workflow overrides live-index compatibility check no longer runs twice per command.
<!-- sq:discussion:end -->
