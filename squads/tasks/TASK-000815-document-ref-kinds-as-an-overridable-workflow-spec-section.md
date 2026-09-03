---
id: TASK-815
sequence_id: 815
type: task
title: Document ref_kinds as an overridable workflow-spec section
status: Done
parent: FEAT-790
author: tech-lead
assignee: tech-writer
priority: medium
refs:
- ADR-775:implements
- TASK-796:depends-on
- TASK-797:depends-on
- TASK-821:depends-on
description: Name ref_kinds in every override-section enumeration and give it a field
  reference in the override docs
subentities:
- local_id: ST1
  title: Name ref_kinds in every override-section enumeration
  status: Done
  assignee: tech-writer
  story: US1
- local_id: ST2
  title: Write the ref-kinds field reference in the override docs
  status: Done
  assignee: tech-writer
  story: US1
- local_id: ST3
  title: Complete the workflow.md override-format field reference
  status: Done
  assignee: tech-writer
  story: US1
- local_id: ST4
  title: Cover ref kinds in the drop-and-rename live-corpus prose
  status: Done
  assignee: tech-writer
  story: US1
- local_id: ST5
  title: Restore the duplicate-filing guidance in the docs, not the spec
  status: Done
  assignee: tech-writer
  story: US1
created_at: '2026-08-25T22:33:00Z'
updated_at: '2026-08-26T09:21:15Z'
---
<!-- sq:body -->
## Scope

FEAT-790 US1 — the documentation half of declaring `[ref_kinds]`.

`ref_kinds` is a member of `WORKFLOW_TOP_LEVEL_SECTIONS` (`_workflow/_loader.py:99-101`), so an
adopter may already declare a ref kind of their own, shadow a bundled one, or drop one they do not
use, from `.overrides/workflow.toml`. **No override documentation says so.** Every place the docs
enumerate the sections a workflow override may carry still lists the pre-`ref_kinds` set, so the
capability this feature exists to give an adopter cannot be discovered by reading the docs.

This is documentation debt from the section-declaring work, not a carrier of the retired
closed-vocabulary policy — which is why the contract-prose reissue correctly left it.

**Document only what the shipped engine does.** Every claim below was verified against the tree;
verify any further claim the same way before writing it. A doc that promises behaviour the engine
does not have is the failure mode this whole surface is being corrected for.

## The sites, all verified against the tree

### `docs/overrides.md`

- **`:199`** — the "Add" bullet of the three-things-you-can-do list: "new item types, statuses,
  lifecycles, badge collections, status roles".
- **`:222-223`** — the closed set of section names: "`[items.*]`, `[statuses.*]`, `[lifecycles.*]`,
  `[collections.*]`, `[subentity_kinds.*]` and `[roles.*]`, plus the single `[selected]` table".
- **`:229`** — a reproduced refusal, quoted as literal tool output. The engine now prints
  `['collections', 'items', 'lifecycles', 'ref_kinds', 'roles', 'selected', 'statuses',
  'subentity_kinds']` (the frozenset plus `selected`, sorted). Reproduce what the tool prints, not
  a hand-edited list — a quoted-output block that does not match the tool is worse than no block.
- **`:610-611`** — the `[selected]` accepted section keys: "`items`, `statuses`, `lifecycles`,
  `collections`, `subentity_kinds` and `roles`".
- **`:192` and `:194-196`** — the section heading and its opening paragraph, which enumerate what
  `.overrides/workflow.toml` governs ("item types, statuses, and badge collections") and so read as
  a closed list to anyone scanning for ref kinds.
- **`:238-467`** — the per-section field reference (Items, records-category types, Statuses,
  Lifecycles, Collections, Status roles). There is no ref-kinds subsection.
- **`:695-716`** — "What a drop or a rename actually changes". Its live-corpus note names only a
  type or a status; ref kinds joined that same check
  (`_workflow/_loader.py::_collect_ref_kind_alignment_errors`, with its own fix hint at `:1207`).

### `docs/workflow.md` — which `docs/overrides.md:236` calls the complete field reference

- **`:378-379`** — "standard TOML with four sections: `[items.*]`, `[statuses.*]`,
  `[lifecycles.*]`, and `[collections.*]`". This was already wrong before the feature (it omits
  `subentity_kinds` and `roles`) and is wrong again now. There are seven.
- **`:574-576`** — "The override may add a new item type, status, lifecycle, collection or status
  role".
- **`:381-570`** — the field-reference subsections. No ref-kinds one.

## What a ref-kind field reference has to state

- The entry is `[ref_kinds.<kind>]`, keyed by the kind as it is spelled on disk in a
  `"ID:kind"` ref. Fields: `label`, `hint`, `role`, and `direction` where the role is
  `dependency`.
- `role` is the semantic the engine binds to, never the spelling: `default` (what a bare
  `ref add <id>` with no `--kind` resolves to), `dependency` with
  `direction = "blocker" | "dependent"` (feeds `sq blocked`), `preload` (the skill-to-role
  resolver), `supersession` (`sq check`'s supersedes rule). **A kind that declares no `role` is
  navigational, and that is what an adopter-declared kind gets by default** — which is the whole
  point for an adopter and should be the worked example.
- The floor a merged spec must satisfy: exactly one kind carries `preload`; at most one per
  `dependency` direction; a kind name may not contain `:` and must be a bare TOML key. Zero
  `dependency` and zero `supersession` kinds are legal.
- Dropping or renaming a kind that live refs still carry is refused, with the offending item IDs
  listed and two remedies — restore the entry, or remove the edges first.
- `sq workflow ref-kinds` is how an adopter reads back what their merged spec declares.

## Out of scope

- **`sq override scaffold workflow`'s commented example.** It covers lifecycles, statuses and items
  only — it never covered collections, `subentity_kinds` or `roles` either, so omitting ref kinds
  there is existing scope, not new debt. Do not widen it here.
- **The contract prose** in `docs/stability.md`, the cheatsheet template and `README.md` — a
  separate piece of work, already reissued.
- **The wording of the bundled `targets` hint** — that text is spec data in
  `_specs/workflow.toml`, not documentation, and is being corrected separately.
- **`subentity_kinds`' own missing field reference.** Real, pre-existing, and not this feature's
  debt. Note it, do not fix it here.

## Acceptance

- Every enumeration listed above names `ref_kinds`, and the `docs/workflow.md:378` count is
  correct rather than restated wrong.
- The quoted refusal output at `docs/overrides.md:229` is byte-identical to what the engine
  prints — reproduced from a run, not hand-assembled.
- `docs/overrides.md` and `docs/workflow.md` each carry a ref-kinds field reference covering
  `label`, `hint`, `role` and `direction`, the four semantic roles, the navigational default, the
  floor, and the live-corpus refusal on drop or rename.
- An adopter reading only the override documentation can declare a navigational kind of their own,
  and can tell what would happen if they renamed a bundled one.
- Every behavioural claim in the new prose was verified against the shipped engine; none describes
  a capability that does not ship.
- No build-process narration, no sq item ID, no status or lifecycle prose in the delivered text.
- `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 815 add-subtask "<title>"`; track with `sq task 815 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | tech-writer | Name ref_kinds in every override-section enumeration | US1 |
| ST2 | Done | tech-writer | Write the ref-kinds field reference in the override docs | US1 |
| ST3 | Done | tech-writer | Complete the workflow.md override-format field reference | US1 |
| ST4 | Done | tech-writer | Cover ref kinds in the drop-and-rename live-corpus prose | US1 |
| ST5 | Done | tech-writer | Restore the duplicate-filing guidance in the docs, not the spec | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Name ref_kinds in every override-section enumeration

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Name `ref_kinds` everywhere the docs enumerate the sections a workflow override may carry, so the
closed set the reader is shown matches `WORKFLOW_TOP_LEVEL_SECTIONS`.

The enumerations, each verified in the tree:

- `docs/overrides.md:199` — the "Add" bullet ("new item types, statuses, lifecycles, badge
  collections, status roles").
- `docs/overrides.md:222-223` — the closed set of section names.
- `docs/overrides.md:229` — the quoted refusal output. Reproduce this from an actual run: the
  engine prints the frozenset plus `selected`, sorted, which is now
  `['collections', 'items', 'lifecycles', 'ref_kinds', 'roles', 'selected', 'statuses',
  'subentity_kinds']`. A quoted output block that does not match the tool is worse than none.
- `docs/overrides.md:610-611` — the accepted `[selected]` section keys.
- `docs/overrides.md:192` and `:194-196` — the section heading and its opening paragraph, which
  read as a closed list of what the file governs.
- `docs/workflow.md:378-379` — "standard TOML with four sections". Already wrong before this
  feature (it omits `subentity_kinds` and `roles`); there are seven. Correct the count and the
  list rather than restating it wrong with one more entry.
- `docs/workflow.md:574-576` — "may add a new item type, status, lifecycle, collection or status
  role".

Done when a reader who searches any of these lists for ref kinds finds them, and the quoted
refusal matches the engine byte for byte.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Write the ref-kinds field reference in the override docs

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add a ref-kinds subsection to the per-section field reference in `docs/overrides.md` (the run of
`####` subsections at `:238-467`: Items, records-category types, Statuses, Lifecycles, Collections,
Status roles), in the register those subsections already use — a worked TOML block, then the field
rules.

What it has to state:

- The entry is `[ref_kinds.<kind>]`, keyed by the kind exactly as it is spelled on disk inside a
  `"ID:kind"` ref. Fields: `label`, `hint`, `role`, and `direction` where the role is `dependency`.
- `role` is the semantic the engine binds to, never the spelling. `default` is what a bare
  `ref add <id>` resolves to; `dependency` with `direction = "blocker" | "dependent"` feeds
  `sq blocked`; `preload` drives the skill-to-role resolver; `supersession` drives `sq check`'s
  supersedes rule.
- A kind that declares no `role` is navigational — and that is what an adopter-declared kind gets
  by default. Make that the worked example, because it is the case an adopter actually reaches for.
- The floor a merged spec must satisfy: exactly one kind carries `preload`; at most one kind per
  `dependency` direction; a kind name may not contain `:` and must be a bare TOML key. Zero
  `dependency` kinds and zero `supersession` kinds are both legal.
- `sq workflow ref-kinds` is how an adopter reads back what their merged spec declares.

Verify each of these against the shipped engine before writing it — `_workflow/_models.py`'s
`ref_kinds_with_role` / `preload_ref_kind` / `dependency_ref_kind` are the behaviour, and
`_workflow/_loader.py::_parse_ref_kind` is the accepted field set.

Done when an adopter can declare a navigational kind of their own from this subsection alone.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Complete the workflow.md override-format field reference

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Give `docs/workflow.md` the same treatment, because `docs/overrides.md:236` sends the reader there
for the complete field reference and it currently has no ref-kinds entry at all.

- `:376-379` — the "Override format" preamble undercounts the sections. Correct it.
- `:381-570` — the field-reference subsections (Lifecycles, Statuses, Status roles, Item types,
  records-category types, Collections). Add the ref-kinds one, at the depth this file uses, without
  duplicating `docs/overrides.md` wholesale — cross-link the way the neighbouring subsections do
  rather than maintaining two copies of the same field table.
- `:572-593` — "What the override may and may not change". Its add-list omits ref kinds, and its
  refusal list names only a type or status drop that strands live items; a ref kind drop or rename
  now behaves the same way.

Note in passing, do not fix here: `subentity_kinds` has no field reference in either file. That is
real and pre-existing debt, and it is not this feature's.

Done when the file overrides.md calls the complete field reference is complete for ref kinds, and
its own section count and add-list are true.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Cover ref kinds in the drop-and-rename live-corpus prose

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Cover ref kinds in the prose that explains what a drop or a rename actually does to a live squad.

`docs/overrides.md:695-716` ("What a drop or a rename actually changes") states the live-corpus
rule for a type or a status only. Ref kinds joined that same cross-check: a kind the merged spec
drops or renames while live refs still carry it is refused, with the offending item IDs listed
(`_workflow/_loader.py::_collect_ref_kind_alignment_errors`; the fix hint it attaches is at
`:1207-1209`). A kind no edge uses may be dropped or renamed freely.

Read the refusal and its fix hint out of the engine and state the remedies it actually names —
restore the entry, or remove the edges first. Do not invent a third remedy: no verb rewrites a
corpus's ref kinds, and a documented remedy no command performs is a defect.

Say the freely-droppable case out loud. It is the one an adopter is actually in — choosing their
vocabulary when they adopt squads, before any edge carries the kind they are dropping.

Done when the drop-and-rename prose treats ref kinds alongside types and statuses, and every
remedy it offers is one a command performs.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Restore the duplicate-filing guidance in the docs, not the spec

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
The generated cheatsheet used to tell an author what to *do* with a duplicate. The pre-generation
row read:

    | `duplicates` | A (a later filing) duplicates B (the original); A is usually closed as
    {{ dropped or "dropped" }} | ... |

and it now reads `A (a later filing) duplicates B (the original)`. The clause was
template-supplied and spec-resolved (`spec.first_dropped_status(...)`, still live at
`workflow_static.md.j2:60`); it went when the Meaning column became the declared `hint` verbatim.
It is the only place the cheatsheet said what to do with a duplicate, and the cheatsheet is also the
body of the `squads` skill every agent in an adopting squad reads, so it is gone from the
agent-facing copy too. Two comparable clauses survived that rewrite; this third one was not noticed.

**The generated table does not get it back.** The derived line under the table resolves every name
it prints from a declared semantic role — `default`, `dependency`, `supersession` — never from a
kind's name, and there is no duplication role. Putting the clause in the declared `hint` would
hardcode a status name an adopter may have renamed or dropped, which is the same defect TASK-816 is
removing from the `targets` hint in this release. Inventing a `duplication` role to key it off would
declare a semantic the engine binds nothing to, which is a change to the ref-kind contract and an
architect's call, not a documentation one.

So it belongs where bundled kinds may be described by name because the bundled set is the subject:
the ref-kinds field reference this task is already creating.

State it there as guidance about the bundled `duplicates` kind — a later filing that duplicates an
existing one is normally closed as `Cancelled` rather than removed, with the `duplicates` edge left
on the later filing so the original stays reachable. Say plainly that this is a convention about
what to do, not an engine binding: nothing in the tool enforces it, which is why it is not in the
kind's declared semantics.

Constraints: name `Cancelled` only as this squad's bundled status, not as a universal, since an
adopter may have renamed or dropped it. No forward reference to a mechanism that does not ship. Do
not restore the clause to the cheatsheet template or to `_specs/workflow.toml`.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T22:35:58Z] Olivia Lead:
  - Parented to FEAT-790 and mapped to US1: this is the documentation half of declaring the section, not a carrier of the retired closed-vocabulary policy — which is why the contract-prose reissue correctly left it. Beyond the four enumerations in docs/overrides.md, docs/workflow.md (which overrides.md calls the complete field reference) has no ref-kinds entry at all and undercounts the sections at :378.
- [2026-08-26T09:05:14Z] Theo Writer:
  - Documented [ref_kinds] across both override documents. docs/overrides.md: the section heading and its opening paragraph now name ref kinds; the "Add" bullet, the closed top-level section list and the [selected] accepted-key list all carry ref_kinds; and the quoted unknown-top-level-key refusal was re-run against the tool and replaced with what it actually prints (it names the running version now, so a note points the reader at their own sq workflow lint rather than the list on the page).
  - New "Ref kinds: the labelled edges between items" subsection in docs/overrides.md, in the register the other field-reference subsections use: a worked navigational kind an adopter declares in three lines, the label/hint/role/direction fields, a table of the four semantic roles and what each binds, the floor (exactly one default, exactly one preload, at most one per dependency direction, any number of supersession including zero, bare-TOML-key names), and the drop/rename refusals with the two remedies the engine actually names. Every refusal quoted was reproduced from a driven run, not hand-assembled: the unknown-kind message, the preload-floor error, the live-corpus refusal, and the ref-rule referential refusal you meet when you drop a kind a type rule still names.
  - docs/workflow.md: the "Override format" preamble said four sections and now says seven and lists them (it had been omitting subentity_kinds and roles since before this work); the may-and-may-not-change add-list gains ref kinds and its refusal list gains the ref-kind drop/rename hard stop; and a new "Ref kinds" subsection carries the bundled set as a table with each kind s meaning and role, plus a cross-link to the full field reference rather than a second copy of it.
  - The duplicates guidance is restored there as a convention nothing enforces: a later filing that duplicates an existing item is normally closed rather than deleted - at Cancelled under the bundled lifecycles, or whatever your own spec calls its equivalent dropped state - with the duplicates edge left on the later filing so the original stays reachable. Stated explicitly as a working convention rather than an engine binding, and Cancelled is named as the bundled status rather than as a universal.
  - Left alone deliberately: the sq override scaffold workflow commented example, and subentity_kinds own missing field reference. The workflow.md preamble now says in one line that sub-entity kinds are declarable but not documented there, and points at sq workflow subentity-kinds --json for the shape - that is a signpost, not the missing reference.
  - Gates: ruff check and ruff format --check clean; sq check clean; tests/meta 255 passed with 3 pre-existing failures all in the concurrent manifest/scripts work (test_override_manifest_and_stamp_freshness x2 and the F-shaped docstring hit in that same file), none in docs. The docs full-text ticket-reference scan passes - it caught illustrative TASK-/BUG- ids in my first draft, so the examples now use <type>/<n>/<id> placeholders and an INC- id from the file own incident example. Targeted doc/cheatsheet modules: 36 passed. Full suite left to the main loop. @tech-lead ready for review.
- [2026-08-26T09:19:08Z] Theo Writer:
  - Correction applied: both lines describing the targets kind promised the declared-view mechanism, which does not ship. I took that wording from the bundled hint, which has since been corrected for the same reason; my two lines were the last adopter-facing text still carrying it, and they contradicted the generated table a reader meets next to them.
  - docs/workflow.md ref-kinds table row now reads: "A targets B - a navigational membership edge with no engine binding; its meaning is whatever reads it". That is byte-identical to the corrected bundled hint, so the hand-authored table and the generated cheatsheet row now say the same thing, both under a Navigation consumer.
  - docs/overrides.md now reads: targets "is the plainest case of all: squads binds nothing to it whatsoever. It ships as a general membership edge - this item belongs to that one - and its meaning is whatever reads it: your own conventions, your own tooling, or a person following the link." No future tense, no reserved-for, no until-X-lands.
  - Swept the rest of docs/ and README for the same claim shape - declared view, derived view, milestone, reserved for a future, once X lands: those two lines were the only hits, and both are now gone. The only other targets mention in docs/ is a splat-ref example ref_rules entry, which promises no mechanism. While sweeping I also dropped a "not yet documented here" from the workflow.md override-format preamble - it was about documentation rather than a capability, but it read as a promise; it now says the section has no field reference for sub-entity kinds and points at sq workflow subentity-kinds --json.
  - Gates after the correction: tests/meta 258 passed (the three failures I reported earlier were the concurrent manifest work and are now green), doc and cheatsheet modules 36 passed, 294 total across both selections; ruff check and format clean; sq check clean. Full suite still left to the main loop; nothing committed. @tech-lead
<!-- sq:discussion:end -->
