---
id: TASK-43
sequence_id: 43
type: task
title: Validate slug arguments across mine/inbox and slug-accepting surfaces (BUG-000021)
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-21:fixes
subentities:
- local_id: ST1
  title: Add resolve_slug_or_raise helper to _cli/_common.py
  status: Done
- local_id: ST2
  title: Make sq mine require slug argument
  status: Done
- local_id: ST3
  title: Validate slug on inbox, workload, comment --as, update --assignee/--author
  status: Done
- local_id: ST4
  title: Add service-level and CLI smoke tests
  status: Done
created_at: '2026-06-11T12:14:52Z'
updated_at: '2026-07-06T15:17:38Z'
---
<!-- sq:body -->
## Goal

Validate slug arguments so an unknown or typo'd slug is a clean error, not a silent empty result. Agents drive their loop off `sq mine` / `sq inbox`; a bad slug currently reports an empty workload and work goes stale with no error.

## What to change

1. **Shared "resolve slug or raise" helper** — one place that validates a slug against the roster (registered agents **and** operators, `op-…`) and raises a `SquadsError` (exit 1) naming the valid slugs / pointing at `sq operator list`. Coordinate with FEAT-19's item-ID resolver pattern (same shape, same home — see the coordination comment on this task). Likely lives near `_cli/_common.py` parsers or a service-level roster lookup (`_services/_roster.py` / `_base.ServiceCore` already has roster access).
2. **Require the slug on `sq mine`** — bare `sq mine` must not silently default to `manager`; the invoking shell implies no agent identity. Make the slug required.
3. **Audit every slug-accepting surface** and route them all through the helper — at least: `sq mine`, `sq inbox`, `sq workload` filters, `comment --as`, `update --assignee`, and `--author` outside create. Validation already exists for `--author` on create and `sq check` warns on unregistered authors/assignees, so this closes an inconsistency, not a design choice.

## Notes / invariants

- Operators (`op-…`) are valid slugs alongside agent roles — the helper validates against both.
- Use `SquadsError`; let `@handle_errors` render it.
- CLI lives in `_cli/`; keep the import graph acyclic.

## Acceptance

- Service-level tests: the resolver raises on an unknown slug, accepts a registered agent and an operator slug.
- CLI smoke tests: `sq mine unknown` and `sq inbox unknown` exit 1 with a helpful message; bare `sq mine` errors (slug required); a valid agent/operator slug still works on every audited surface.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 43 add-subtask "<title>"`; track with `sq task 43 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add resolve_slug_or_raise helper to _cli/_common.py |  |
| ST2 | Done |  | Make sq mine require slug argument |  |
| ST3 | Done |  | Validate slug on inbox, workload, comment --as, update --assignee/--author |  |
| ST4 | Done |  | Add service-level and CLI smoke tests |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add resolve_slug_or_raise helper to _cli/_common.py

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add a shared resolve_slug_or_raise helper (near _cli/_common.py parsers, taking the service for roster access) that validates a slug against the roster — registered agents and operators (op-…) — and raises SquadsError (exit 1) naming the valid slugs / pointing at sq operator list. Mirrors FEAT-19's item-ID resolver shape.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Make sq mine require slug argument

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Make the slug argument required on sq mine so a bare invocation no longer silently defaults to manager — the invoking shell implies no agent identity, so an omitted slug is an error rather than a misleading default workload.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Validate slug on inbox, workload, comment --as, update --assignee/--author

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Route every slug-accepting surface through resolve_slug_or_raise: sq inbox, sq workload filters, comment --as, update --assignee, and --author outside create. Closes the inconsistency where only create's --author was validated, so a typo'd slug is a clean error instead of a silent empty result.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Add service-level and CLI smoke tests

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Service-level tests (resolver raises on unknown slug, accepts a registered agent and an operator slug) plus CLI smoke tests (sq mine unknown / sq inbox unknown exit 1 with a helpful message; bare sq mine errors as slug-required; a valid agent/operator slug still works on every audited surface).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T12:15:55Z] Olivia Lead:
  - @python-dev coordination point: the 'resolve slug or raise' helper should mirror the item-ID resolver pattern decided in FEAT-19 — same shape, ideally same home in _cli/_common.py. Check FEAT-19's resolver before designing this one so we land one consistent validation idiom (item IDs + slugs), not two divergent ones.
  - Sequencing: this task is independent of TASK-42 (different code paths — slug validation in _cli vs the index store) but second in the queue behind it by priority.
- [2026-06-11T12:39:51Z] Elias Python:
  - Implemented resolve_slug_or_raise helper in src/squads/_cli/_common.py, mirroring the resolve_item_id pattern (same module, same shape). Validates against roster() + operators(); raises SquadsError naming valid slugs. 'operator' sentinel passes through for compat.
  - Applied the helper to: sq mine (slug now required, bare call errors), sq inbox, sq list --assignee, comment --as on items and sub-entities, update --assignee on items and all three sub-entity kinds (subtask/story/finding), update --author on items, add-subtask/add-story/add-finding --assignee.
  - Updated 3 existing tests that had stale expectations (test_subtask_assignee_cli error message, test_collab_commands_via_cli using unregistered qa slug, test_mine_cli using bare sq mine). Added tests/test_slug_validation.py with 26 new tests covering the helper and all audited CLI surfaces.
  - uv run pytest: 245 passed, 1 skipped. pyright on changed files: 0 errors. ruff check/format on changed files: clean. Pre-existing repo-wide F401 in _services/_items.py (11) and _cli/__init__.py (1) + _discussion.py format issue — all pre-date these changes (from TASK-42 working tree). @tech-lead ready for review.
- [2026-06-11T12:50:23Z] Olivia Lead:
  - Review PASS — Done. resolve_slug_or_raise in _cli/_common.py mirrors the FEAT-19 resolver shape; validates against roster() + operators(), preserves the legacy 'operator' anonymous sentinel, raises SquadsError naming valid slugs. Routed through every audited surface: mine, inbox, list --assignee, comment --as (item + sub-entity), update --assignee/--author, add-story/add-subtask/add-finding --assignee, update-story/subtask/finding --assignee.
  - Verified live: 'sq mine ghost' / 'sq inbox ghost' exit 1 with "unknown slug 'ghost'; valid slugs: manager"; valid 'sq mine manager' exits 0. Bare 'sq mine' now errors via required Typer Argument (exit 2, not 1 — standard Typer missing-required behavior, consistent with the rest of the CLI; brief intent 'must error' is met). 26 new tests in test_slug_validation.py + updated existing assertions. Clean gates.
- [2026-06-11T12:56:40Z] Pierre Chat:
  - Decision: bare 'sq mine' exiting 2 (Typer missing-required-argument) stays — consistency with the rest of the CLI wins over the exit-1 wording in the bug. No follow-up.
<!-- sq:discussion:end -->
