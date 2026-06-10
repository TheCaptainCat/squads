---
id: FEAT-000019
sequence_id: 19
type: feature
title: 'Uniform item addressing: every command accepts both ID and number'
status: Ready
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
  status: Todo
- local_id: US2
  title: As a user copy-pasting an ID from a comment or tree, I want it accepted by
    every command including tree, --parent and ref add, so that handoffs never need
    manual reformatting
  status: Todo
- local_id: US3
  title: As a user who typos the type, I want sq to tell me 13 is a feature instead
    of silently obeying, so that I never act on the wrong item
  status: Todo
created_at: '2026-06-10T12:56:45Z'
updated_at: '2026-06-11T07:54:54Z'
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
| US1 | Todo |  | As a CLI user, I want to name an item by full ID or bare number in any command, so that one habit works everywhere |
| US2 | Todo |  | As a user copy-pasting an ID from a comment or tree, I want it accepted by every command including tree, --parent and ref add, so that handoffs never need manual reformatting |
| US3 | Todo |  | As a user who typos the type, I want sq to tell me 13 is a feature instead of silently obeying, so that I never act on the wrong item |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a CLI user, I want to name an item by full ID or bare number in any command, so that one habit works everywhere

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
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
**Status:** ⚪ Todo
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
**Status:** ⚪ Todo
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
<!-- sq:discussion:end -->
