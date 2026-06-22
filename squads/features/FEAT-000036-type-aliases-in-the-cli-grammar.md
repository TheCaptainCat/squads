---
id: FEAT-000036
sequence_id: 36
type: feature
title: Type aliases in the CLI grammar
status: Done
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
  title: Short type aliases (sq f/t/b) work everywhere the full word does
  status: Done
- local_id: US2
  title: Aliases hidden from help but documented in one table
  status: Done
created_at: '2026-06-11T07:37:01Z'
updated_at: '2026-06-23T09:59:04Z'
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
| US1 | Done |  | Short type aliases (sq f/t/b) work everywhere the full word does |
| US2 | Done |  | Aliases hidden from help but documented in one table |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Short type aliases (sq f/t/b) work everywhere the full word does

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a daily CLI user, I want sq f / sq t / sq b to work everywhere the full type word does, so that the commands I type all day are as short as they are unambiguous.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Aliases hidden from help but documented in one table

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a newcomer reading help and docs, I want aliases out of the command list but documented in one table, so that discoverability doesn't cost clarity.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T07:43:38Z] Olivia Lead:
  - Broke FEAT-000036 into two tasks. TASK-000107 (US1) — alias routing/equivalence: a single canonical ALIASES map next to WORK_TYPES, each type sub-app re-registered under its hidden alias names in _cli/__init__.py (the proven hidden=True _addr pattern), plus a CLI test matrix proving deep-chain equivalence and canonical output/errors.
  - TASK-000108 (US2) — help cleanliness + docs + contract: hide aliases from root --help, mention the table once (epilog or type help), render it from the same ALIASES map into the workflow cheatsheet with the add-only evolution rule, and tie into FEAT-000013 for docs/stability.md (refd as related; FEAT-13 still owns creating that file).
  - Single source of truth for the table = the ALIASES map TASK-107 introduces; TASK-108 consumes it so routing and docs can't drift. @python-dev TASK-000107 is ready to start (TASK-000108 builds on its ALIASES map, so take 107 first).
- [2026-06-15T08:07:51Z] Mara Tester:
  - QA verification of FEAT-000036 — overall PASS with one minor clarification needed.
  - **AC1 (alias equivalence):** PASS. All aliases (e, f/feat, t, b, d/dec, r/rev, g) route to the full command tree including deep verb + sub-entity chains. Empirically sampled: feature story show (f/feat), task subtask show/update (t), review finding show (r/rev), decision status mutation (d/dec), bug comment (b), task ref add (t), epic show (e). Identical output to canonical in all cases. 23 automated tests in tests/test_aliases.py all pass.
  - **AC2 (canonical output):** PASS. --json output uses canonical type name (feature/task/bug/decision/review/guide/epic) and full canonical ID (FEAT-/TASK-/BUG-/ADR-/REV-/GUIDE-/EPIC-) for all 7 types via all aliases. Error messages also use canonical IDs.
  - **AC3 (help cleanliness):** PASS. Root --help shows only 7 canonical type commands; aliases are hidden. Root --help epilog mentions aliases and points to sq workflow. sq workflow renders the alias table dynamically from TYPE_ALIASES (Jinja2 context, no hardcoding), with the add-only evolution rule and FEAT-000013 reference.
  - **AC4 (collision safety):** PASS. b/t/r/d do not shadow blocked/tree/repair/docs. Exact-match resolution verified empirically and in automated tests.
  - **AC5 (contract doc):** PASS. Add-only rule recorded in sq workflow output with FEAT-000013 tie-in. docs/stability.md correctly deferred to FEAT-000013.
  - **Clarification needed:** Feature AC says 'alias table appears in sq docs workflow'. The implementation puts it in sq workflow (the terminal command) and the root --help epilog, not in docs/workflow.md (read by sq docs workflow). TASK-000108's task-level AC says 'sq workflow output and each type's help (or the root epilog)' — which IS satisfied. The discrepancy is in the feature-level wording. @tech-lead — please confirm whether docs/workflow.md should be updated, or accept the current wording as equivalent.
  - **Gate:** uv run pytest — 602 passed, 1 skipped. pyright 0 errors. ruff clean.
- [2026-06-15T08:10:19Z] Theo Writer:
  - Closed the docs gap: added the 'Type-command aliases' section to docs/workflow.md.
  - The section includes the full alias table, equivalence note (full verb-chain and sub-entity support), output canonicalization rule, and the add-only evolution rule with FEAT-000013 tie-in.
  - Verified: sq docs workflow now displays the new section; all tests pass (602 passed, 1 skipped).
  - @qa ready for re-verification that the feature-level acceptance 'alias table appears in sq docs workflow' is now satisfied.
<!-- sq:discussion:end -->
