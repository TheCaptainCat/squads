---
id: FEAT-271
sequence_id: 271
type: feature
title: 'CLI grammar: verb-first addressing (sq show ID, sq update ID)'
status: Draft
parent: EPIC-38
author: product-owner
refs:
- FEAT-13
- REV-265
subentities:
- local_id: US1
  title: As a user, I address any item by ID alone without specifying its type
  status: Todo
- local_id: US2
  title: As a user, custom types work with the same verb-first commands as built-in
    types
  status: Todo
created_at: '2026-07-01T09:41:35Z'
updated_at: '2026-07-02T13:07:21Z'
---
<!-- sq:body -->
## Problem

Today's CLI grammar is type-first: every command begins with the item type as a sub-app selector — `sq task 35 show`, `sq feature 12 story 1 update`, `sq bug 7 comment`. Built-in types are wired as Typer sub-apps by `build_item_app`; custom types land through a lazy-dispatch `_CustomTypeGroup` that registers `sq <custom-type>` at parse-time and wraps get_command in a bare `except Exception` to swallow registration errors (flagged as REV-265 F5).

At small scale, type-first is intuitive: `sq task 35 show` reads naturally. At larger scale — especially once custom types are in play — it creates structural friction:

- Users must know (or look up) an item's type before issuing any command. The ID alone — `TASK-000035` — already contains the type. The grammar asks for information the user is giving twice.
- Every new custom type requires registering a new sub-app, perpetuating the `_CustomTypeGroup` machinery and its error-masking. There is no escape hatch.
- Skills, the playbook, the `sq workflow` cheatsheet, and all docs hardcode `sq <type> <n> <verb>` — each new type multiplies the surface that must be kept in sync.
- The pre-1.0 moment is the cheapest time to change this. Every custom-type surface built on type-first raises the cost of a later migration.

## Proposal

Global verb-first commands that resolve the item type from the ID prefix at dispatch time:

```
sq show TASK-35
sq update FEAT-12 --status InProgress
sq comment BUG-7 --as reviewer -m "…"
sq body TASK-35 -m "…"
sq ref add TASK-35 BUG-7 --kind fixes
```

`sq create <type>` stays verb-first — it already is, and creation is the one case where no existing ID is available to resolve from.

Sub-entity addressing needs a verb-first spelling too (e.g. `sq show FEAT-12 story 1`, or an ID-like form — the exact sub-entity grammar is an open design question left for the ADR).

## Why now, on the generic base

EPIC-206 makes `Item` fully generic (type is `str`, prefix and folder come from the spec). Once that lands, the type is mechanically recoverable from any ID prefix — dispatch does not need a per-type sub-app. The entire `_CustomTypeGroup` lazy-dispatch machinery (and the `except Exception` masking in REV-265 F5) can be retired rather than carried forward. Without this change, the custom-type surface builds on a grammar that is already showing structural debt.

## Blast radius (scope, not solution)

This feature records the intent. The following are open decisions, not specifications:

- **Grammar supersession:** verb-first supersedes the FEAT-13 command-grammar stability freeze. That freeze must be formally lifted (a new ADR) before implementation begins.
- **Back-compat strategy:** hard flip on the next major version, or a deprecation window keeping type-first as hidden aliases? The answer determines migration burden for existing users and scripts.
- **Sub-entity addressing:** `sq feature 12 story 1 update` needs a verb-first form. The exact spelling (positional args, a sub-ID scheme, or a `--sub` flag) is unresolved.
- **Docs and skills:** every managed skill (`sq-task`, `sq-feature`, …), the playbook, the `sq workflow` cheatsheet, and the shipped docs pages all encode type-first examples. The update sweep is large.
- **Alias table:** the existing single-letter aliases (`sq t 35 show`, `sq f 12 show`) share the type-first structure. Their fate under verb-first needs a decision.

## Non-goals / Deferred

The ADRs that decide the target grammar, formally supersede FEAT-13, and resolve the back-compat/deprecation strategy are **not part of this feature**. They will be authored by the architect when this feature is scheduled. This item is the backlog placeholder that captures intent and rationale so the decision context travels with the work.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 271 add-story "As a <role>, I want … so that …"`; track with `sq feature 271 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a user, I address any item by ID alone without specifying its type |
| US2 | Todo |  | As a user, custom types work with the same verb-first commands as built-in types |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a user, I address any item by ID alone without specifying its type

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
The user types 'sq show TASK-35' or 'sq comment BUG-7 --as reviewer -m ...' without having to know or repeat the item's type. The ID prefix carries the type; the CLI resolves it automatically at dispatch time.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a user, custom types work with the same verb-first commands as built-in types

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Once a custom type is registered in the workflow spec, 'sq show INC-3', 'sq update INC-3 --status Mitigating', and 'sq comment INC-3 --as on-call -m ...' all work without any additional CLI wiring. There is no '_CustomTypeGroup' registration step visible to the user, and no sub-app to maintain per type.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T09:42:41Z] Nina Product:
  - Drafted for the record at the tail of EPIC-206 (after FEAT-210/211/212), unscheduled.
  - Intent: retire type-first CLI grammar in favor of global verb-first dispatch keyed on the ID prefix. Captures the rationale, blast radius, and the open back-compat question so the context travels with the work.
  - ADRs not authored here — Robert Architect will draft them (grammar target, supersession of FEAT-013 stability freeze, back-compat/deprecation strategy) when op-pierre greenlights scheduling.
  - @manager: this item is in Draft, unscheduled. No tasks, no ADRs, no devs yet — per op-pierre.
- [2026-07-02T13:07:21Z] Catherine Manager:
  - Re-parented from EPIC-206 to EPIC-38 (CLI frontend) per op-pierre: verb-first addressing is a CLI-grammar refactor, a different axis from EPIC-206's config-driven-workflow mission (which is now fully delivered). Same scope-line reasoning as the FEAT-212→EPIC-280 split (ADR-274). Still refs FEAT-013 (grammar stability contract) + REV-265 (custom-type dispatch).
<!-- sq:discussion:end -->
