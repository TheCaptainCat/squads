---
id: FEAT-000036
sequence_id: 36
type: feature
title: Type aliases in the CLI grammar
status: Ready
parent: EPIC-000012
author: product-owner
priority: medium
refs:
- FEAT-000013
description: Short and single-letter aliases for the item-type commands (sq feat /
  sq f, sq t, sq b, ...) — hidden from help clutter, documented once, frozen with
  the grammar
subentities:
- local_id: US1
  title: As a daily CLI user, I want sq f / sq t / sq b to work everywhere the full
    type word does, so that the commands I type all day are as short as they are unambiguous
  status: Todo
- local_id: US2
  title: As a newcomer reading help and docs, I want aliases out of the command list
    but documented in one table, so that discoverability doesn't cost clarity
  status: Todo
created_at: '2026-06-11T07:37:01Z'
updated_at: '2026-06-11T07:54:56Z'
---
<!-- sq:body -->
## Problem

The type commands are typed dozens of times a day — `sq feature 26 story 4 update --status …` —
and the type word is the longest, least informative part. There are no abbreviations: `sq feat`
is an error, `sq f` too. For a CLI whose primary users include humans working a backlog live,
that's friction with no payoff.

## Value

Muscle-memory speed: `sq t 35 show`, `sq f 26 story 4 body …`, `sq b 21 status InProgress`.
Aliases are additive (no existing invocation changes meaning), cheap to implement (the same
sub-app registered under hidden alias names), and — because the CLI grammar becomes SemVer-stable
at 1.0 — best chosen *now*, deliberately, rather than bolted on under freeze pressure later.

## Scope

- **Alias table** (canonical → aliases), one per type, no overloading:

  | type     | short | letter |
  |----------|-------|--------|
  | epic     | —     | `e`    |
  | feature  | `feat`| `f`    |
  | task     | —     | `t`    |
  | bug      | —     | `b`    |
  | decision | `dec` | `d`    |
  | review   | `rev` | `r`    |
  | guide    | —     | `g`    |

  Single letters are safe: command resolution is exact-match, so `b` doesn't collide with
  `blocked` nor `t` with `tree`. No aliases for non-type commands (out of scope — `sq blocked`
  stays as is).
- **Full verb-chain equivalence**: every alias accepts everything the canonical name does,
  including sub-entities (`sq f 26 story 4 show`).
- **Help stays clean**: aliases are hidden from the root command list; the canonical help mentions
  them once (epilog or the type command's help line), and the docs/workflow cheatsheet carries the
  table.
- **Output stays canonical**: errors, confirmations and `--json` always print the canonical type
  name and full IDs — aliases are input sugar, never output.
- **Contract**: the alias table joins the stability doc (FEAT-000013) as frozen grammar; adding
  aliases later is additive and allowed, removing or repurposing one is breaking and isn't.

## Acceptance

- Every alias routes to its type's full command tree; CLI test matrix samples each alias with at
  least one deep chain.
- Root `--help` shows only canonical names; the alias table appears in `sq docs workflow` and the
  type help text.
- All output (including errors) uses canonical names regardless of the alias used.
- The contract doc records the table and the add-only evolution rule.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 36 add-story "As a <role>, I want … so that …"`; track with `sq feature 36 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a daily CLI user, I want sq f / sq t / sq b to work everywhere the full type word does, so that the commands I type all day are as short as they are unambiguous |
| US2 | Todo |  | As a newcomer reading help and docs, I want aliases out of the command list but documented in one table, so that discoverability doesn't cost clarity |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a daily CLI user, I want sq f / sq t / sq b to work everywhere the full type word does, so that the commands I type all day are as short as they are unambiguous

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** sq f 26 story 4 show ≡ sq feature 26 story 4 show (and likewise e/t/b/d/r/g, feat/dec/rev) across every verb and sub-entity chain; outputs and errors always print canonical names.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a newcomer reading help and docs, I want aliases out of the command list but documented in one table, so that discoverability doesn't cost clarity

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** root --help lists only the seven canonical type commands; the alias table lives in sq docs workflow and each type's help; the stability contract records the table with its add-only rule.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
