---
id: FEAT-000019
sequence_id: 19
type: feature
title: 'Uniform item addressing: every command accepts both ID and number'
status: Done
parent: EPIC-000012
author: product-owner
priority: high
description: Every ID-accepting surface (verbs, tree, --parent, ref add, search args)
  understands both the full ID (FEAT-000013) and the bare number (13), with one shared
  resolver
subentities:
- local_id: US1
  title: As a CLI user, I want to name an item by full ID or bare number in any command,
    so that one habit works everywhere
  status: Done
- local_id: US2
  title: As a user copy-pasting an ID from a comment or tree, I want it accepted by
    every command including tree, --parent and ref add, so that handoffs never need
    manual reformatting
  status: Done
- local_id: US3
  title: As a user who typos the type, I want sq to tell me 13 is a feature instead
    of silently obeying, so that I never act on the wrong item
  status: Done
created_at: '2026-06-10T12:56:45Z'
updated_at: '2026-06-11T14:41:09Z'
---
<!-- sq:body -->
## Problem

Commands disagree on how an item is named. The item verbs take the bare sequence number
(`sq task 35 show`), while `sq tree`, `--parent`, and `sq <type> <n> ref add` demand the full
formatted ID (`FEAT-000013`) — `sq tree 13` is an error today. Worse, the looseness cuts the other
way too: `sq task 13 show` happily displays **FEAT**-000013 without flagging that 13 isn't a task.
Users have to remember per-command which form to use, and copy-pasted IDs don't work everywhere.

## Value

One rule everywhere: **anywhere an item can be named, both forms work** — the full ID and the bare
number (numbers are globally unique, so the bare form is never ambiguous). Muscle memory and
copy-paste both succeed on every command. Settling this before 1.0 matters because the stability
contract (FEAT-000013) will document the CLI grammar as SemVer-stable — the addressing rule should
be written down once, as a deliberate decision, not frozen as today's accidental patchwork.

## Scope

- **Inventory** every ID-accepting surface: item verbs, `sq tree`, `--parent`, `ref add`,
  `sq search`-adjacent args, sub-entity addressing — anything that names an item.
- **One shared resolver** used by all of them, accepting `FEAT-000013` and `13` alike.
- **Type mismatch is an error** *(decided — op-pierre, 2026-06-10)*: when the named item exists
  but isn't of the addressed type, every command fails with a pointer to the right type
  (e.g. `13 is FEAT-000013 (feature), not a task`) instead of silently obeying. Same rule for a
  full ID whose prefix contradicts the command (`sq task … ref add` stays kind-agnostic; this is
  about the `sq <type> <n>` addressing).
- Document the addressing rule in the stability contract (link to FEAT-000013).

Accepting more forms is additive (no existing invocation breaks), which is why this is medium
rather than high — but note the mismatch-error decision **tightens** current behaviour (commands
that silently obeyed will start failing), so it must land before the grammar freezes, not after.

## Acceptance

- Every command that names an item accepts both the full ID and the bare number; covered by tests
  across the inventory.
- Addressing an existing item through the wrong type errors, consistently everywhere, naming the
  actual item and type; covered by tests.
- The addressing rule has a single implementation (shared resolver) and is documented in the
  stability contract.
- Error messages for unknown items mention both accepted forms.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 19 add-story "As a <role>, I want … so that …"`; track with `sq feature 19 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As a CLI user, I want to name an item by full ID or bare number in any command, so that one habit works everywhere |
| US2 | Done |  | As a user copy-pasting an ID from a comment or tree, I want it accepted by every command including tree, --parent and ref add, so that handoffs never need manual reformatting |
| US3 | Done |  | As a user who typos the type, I want sq to tell me 13 is a feature instead of silently obeying, so that I never act on the wrong item |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a CLI user, I want to name an item by full ID or bare number in any command, so that one habit works everywhere

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** the inventory of ID-accepting surfaces is complete and each accepts both forms via the shared resolver; a test matrix covers every surface with both forms.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a user copy-pasting an ID from a comment or tree, I want it accepted by every command including tree, --parent and ref add, so that handoffs never need manual reformatting

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** `sq tree 13`, `--parent 12` and `sq task <n> ref add 19` work with bare numbers, and all verbs work with full IDs; unknown-item errors mention both accepted forms.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a user who typos the type, I want sq to tell me 13 is a feature instead of silently obeying, so that I never act on the wrong item

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** addressing an existing item through the wrong type errors, naming the actual item and type (`13 is FEAT-000013 (feature), not a task`); behaviour is identical across all commands and covered by tests. (Decided by op-pierre: error, never silently obey.)
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-10T13:00:06Z] Pierre Chat:
  - Decision: when the addressed type doesn't match the item (e.g. `sq task 13` but 13 is a feature), error and point to the right type — never silently act on it.
- [2026-06-11T14:00:49Z] Olivia Lead:
  - Broke FEAT-000019 into two sequenced tasks, both high, assigned @python-dev (Elias).
  - TASK-000046 (foundation): shared item-address resolver in _cli/_common.py — typed resolve verifies the resolved item's ACTUAL type against the live DB (closes the sq task 13 → FEAT-000013 silent-obey hole, _index.py:57 _seq ignores type), plus a type-less resolve for the sweep. Maps US1 (both forms) + US3 (type-mismatch error).
  - TASK-000047 (adoption sweep, blocked by 046): route every raw surface through the resolver — create --parent/--ref, update --parent, ref add/rm, tree root, list --parent, role/skill/operator targets, subtask --story; uniform both-forms error wording. ref add stays kind-agnostic; --parent resolves then defers to parent_allowed. Maps US2 (copy-paste everywhere) + US3 (wording).
  - TASK-000046 blocks TASK-000047. Stability-contract documentation acceptance is deferred to FEAT-000013 (rule recorded here, ref kept). Seed test: test_resolve_item_id in tests/test_cli.py:232.
- [2026-06-11T14:41:09Z] Mara Tester:
  - QA sign-off: FEAT-000019 verified hands-on in a scratch squad (tmp dir, sq init, items of type epic/feature/task/bug/decision/operator/role/skill).
  - US1 (both forms everywhere) — PASS. Verified: sq <type> N show (bare+full), sq tree (bare+full), create --parent (bare+full), update --parent (bare+full), create --ref (bare+full+bare:kind+full:kind), ref add (bare+full+bare:kind+full:kind), ref rm (bare+full), sq list --parent (bare+full), sq role regen (bare+full), sq skill show (bare+full), sq operator rm (bare+full), subtask --story US1 and --story 1 — all accepted both forms.
  - US2 (copy-paste) — PASS. IDs as rendered in sq tree (FEAT-000010, TASK-000011, EPIC-000009) fed directly into show, tree, --parent, ref add — all accepted unchanged.
  - US3 (type mismatch) — PASS. Wrong-type bare number and wrong-prefix full ID both produce 'X is ID (type), not a/an type'. Consistent wording across both input forms for the same item (F1 fix verified). Vowel-initial article correct: 'not an epic' (sq epic 11 show on a task), 'not an operator' (sq operator rm 11 on a task) — both bare and full-ID forms (F4 fix verified).
  - Unknown-item wording (F2 fix) — PASS. Typed surfaces: 'no item with number 99 (use TASK-000099 or bare 99)' — both bare and full-ID forms give identical message. Type-less surfaces (sq tree): 'no item with number 99 (use a full ID like TYPE-000099 or bare 99)' — both bare and full-ID forms give identical message.
  - pytest: 258 passed, 1 skipped — green. sq check: no issues.
  - Note: the fourth acceptance criterion — documenting the addressing rule in the stability contract — is deferred to FEAT-000013 by design. The ref FEAT-000013 already links from this feature. No gap in this delivery.
<!-- sq:discussion:end -->
