---
id: TASK-997
sequence_id: 997
type: task
title: Document the two checks that became catalog-only
status: Done
parent: FEAT-899
author: tech-lead
assignee: tech-writer
priority: low
refs:
- TASK-996:depends-on
description: 'Validators reference and release note: no_status_banner and subentity_title_max
  run only where a type selects them, with the line that restores each'
subentities:
- local_id: ST1
  title: Rewrite the validators reference for the two checks
  status: Done
  story: US4
- local_id: ST2
  title: Write the release note for the two checks
  status: Done
  story: US4
created_at: '2026-10-11T21:10:21Z'
updated_at: '2026-10-12T06:19:30Z'
---
<!-- sq:body -->
## Scope

Story 4 of FEAT-899: what an adopter needs to read when `no_status_banner` and
`subentity_title_max` stop running by default. The engine work is TASK-996; this task
describes what an adopter now sees and the line that brings each check back.

Owner: the tech writer. The developer's handoff comment on TASK-996 lists every
adopter-visible change with its exact text. That list is the input; each claim is still
checked against a scratch squad before it is written.

It is written against a build that contains TASK-996: in the validator worktree before its
merge, or in the main tree after it.

## Subtasks

- **ST1, the validators reference** in `docs/overrides.md`, and the passages that point at
  it.
- **ST2, the release note** in `CHANGELOG.md`.

ST1 first: the release note links to its section.

## What changed, for the reader

- A squad on the bundled spec no longer gets a warning for a body or summary that opens
  with a status banner, on any type.
- A squad on the bundled spec no longer gets a warning for a story, subtask or finding title
  over 120 characters, and `add-<kind>` no longer prints its title advisory.
- Both are still in the catalog. A type runs one when its own `validators` list names it:
  `no_status_banner`, and `subentity_title_max` (120) or `subentity_title_max:<n>`.
- Selection is per type. There is no squad-wide switch.
- An existing squad needs no migration: nothing on disk changes, and `sq migrate up` has
  nothing to do for this.

## Acceptance (whole task)

- Story 4: the validators section and the release note state that both checks are
  catalog-only, show the one-line selection that restores each, and say that an existing
  squad needs no migration.
- **Every command and every quoted message is run before it is written**, with a build that
  contains TASK-996, in a scratch squad nested under the session scratchpad (print the
  working directory before any writing command, chain with `&&`, never this repository's
  own squad). The handoff labels each claim as driven or read.
- **The reader test.** Following only the docs, in a fresh scratch squad: confirm a banner
  body and a 121-character story title report nothing; add the documented lines; confirm
  both are reported and the `add-story` advisory prints. Record the commands and exit codes.
- **A stale-claim sweep, table-driven.** For each retired statement, search every file under
  `docs/`, the README, `PYPI.md` and the unreleased section of the CHANGELOG, on
  whitespace-collapsed text, and validate each search on the previous wording first:
  - two checks are the only ones nothing bundled selects (`parent_present` and
    `ref_rule_target_present`), stated twice in `docs/overrides.md`;
  - a type that declares no parameter gets the bundled title threshold, with no mention of
    selecting the check;
  - any sentence that has `sq check` warning on a status banner or on a long sub-entity
    title without the type selecting it;
  - any example that shows the `add-<kind>` advisory on a type whose `validators` the
    example does not show.
  The handoff lists each statement, where it was, and what replaced it.
- Adopter docs carry no item references and no development-process content. Each sentence
  passes the stranger test: true and meaningful for a reader who never saw the change.

## Gates and working rules

- `uv run --all-extras pytest tests/meta` passes: the gate that documented commands resolve
  against the CLI, and the gate against stray item references in docs.
- `sq check` is clean before handback, run from the main checkout with the released tool:
  `cd /home/pchat/projects/squads && pwd && ~/.local/bin/sq check`. Board writes (subtask
  status, comments, the handoff) are made the same way, never from a worktree and never
  with the dev build. No board item is created from a worktree.
- No source or test file is edited. A doc claim that the build contradicts is reported on
  TASK-996 as a comment, not worked around in prose.
- The CHANGELOG entry is one self-contained bullet under the unreleased version's
  `### Changed`, so merging it with entries written in another tree is a pure addition.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 997 add-subtask "<title>"`; track with `sq task 997 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rewrite the validators reference for the two checks

<!-- sq:subtask:ST1:body -->
**Goal.** `docs/overrides.md` § "Validators" describes the set a type runs as it now is: the
status-banner check and the sub-entity title check are available and unselected, like
`parent_present` and `ref_rule_target_present`.

**Approach**

- The paragraph that names the checks nothing bundled selects lists four, not two, and says
  what each of the two new ones reports. The same statement near the end of the file ("Two
  checks ship unselected") is brought in line.
- One short worked example restores both on one type, and a sentence says selection is per
  type, so a squad that wants a check everywhere names it on each type.
- "A threshold is yours to set": a type gets the title check, at 120, by naming
  `subentity_title_max` bare, and at its own number with `subentity_title_max:<n>`. A type
  that does not name it gets neither the `sq check` finding nor the `add-<kind>` advisory.
  The sentence "Declare no parameter and the type gets the bundled default" is rewritten to
  say so.
- The array-replacement warning stays and gains the case a reader restoring a check will
  hit: `epic` and `skill` ship a `validators` list, so restoring a check on them uses the
  splat form; on a type that ships no list the splat is refused, with the message quoted.
- The examples that already select explicitly (`no_status_banner@error`,
  `subentity_title_max:40@error`, the repeat-selection refusals) are re-run and kept if
  their output is unchanged.
- `docs/workflow.md`: the `validators` entry in the item-type field list, and any passage
  found by the sweep, agree with the section.

**Tests**

- Every fenced command and quoted message in the changed passages is run in a scratch squad
  with a build that contains TASK-996; the handoff lists them with exit codes.
- The reader test of the task body.
- The stale-claim sweep of the task body over `docs/`, each search validated on the old
  wording.

**Falsify.** Take the worked example and remove its `validators` line: the outcome the
example states must stop holding in the scratch squad. If it still holds, the example was
not demonstrating the selection; rewrite it.

**Acceptance.** Story 4, for the override reference: both checks stated as catalog-only,
with the one-line selection that restores each.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Write the release note for the two checks

<!-- sq:subtask:ST2:body -->
**Goal.** An adopter reading the release notes before upgrading learns that two warnings
stop by default, how to get each back, and that nothing needs migrating.

**Approach**

- `CHANGELOG.md`, the unreleased version, `### Changed`: one bullet. It names both checks by
  what the reader sees (`sq check` no longer warns on a body or summary opening with a
  status banner; it no longer warns on a story, subtask or finding title over 120
  characters, and `add-<kind>` no longer prints the title advisory), gives the line that
  restores each in `.overrides/workflow.toml`, says selection is per type, says an existing
  squad needs no migration, and links to the validators section ST1 rewrote.
- The bullet states the reason in one clause an adopter recognises: both are conventions a
  team may not share, not defects.
- No entry under `docs/migration.md`: there is no migration step for this. If the sweep
  finds a sentence there that the change makes false, correct that sentence.
- The entry for the release that introduced the level and parameter grammar is released
  history and is not edited.

**Tests**

- The two restoring lines in the bullet are run in a scratch squad with a build that
  contains TASK-996, each from a squad where the warning is absent to one where it is
  reported. The handoff records the commands.
- The link target resolves to the heading ST1 left in place.
- The stale-claim sweep of the task body over the README, `PYPI.md` and the unreleased
  section of the CHANGELOG.

**Falsify.** In the scratch squad, remove one restoring line again: the warning the bullet
says it brings back must disappear. If it stays, the bullet describes a squad where the
check was never off; rewrite it.

**Acceptance.** Story 4, for the release notes: catalog-only stated, the one-line selection
for each, and no migration needed. No item id and no build-process wording in the entry.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-12T05:21:40Z] Catherine Manager:
  - Promoted and dispatched. The code is merged on release/0.16 at 4b23b04c (REV-998 Approved).
    
    From the review, to cover beside what the subtasks already list:
    
    - `docs/overrides.md`, validators section: "two checks are not selected for you anywhere in the bundled spec" is now four; "declare no parameter and the type gets the bundled default" must say a type that does not select the check runs nothing and a bare name gives 120; the sentence that neither the core nor a bundle can be subtracted from should note these two are in neither.
    - The hand-written part of `CLAUDE.md`: the `sq check` gate section and the rule on status prose in bodies should say both rules are this project's own selections in its workflow override, not defaults of the tool. Do not touch the generated region.
    - A list that replaces a type's bundled one without the splat form silently drops the bundled entries; `epic` and `skill` are the two bundled types that ship a list.
- [2026-10-12T05:35:54Z] Theo Writer:
  - Docs and release note written for the two catalog-only checks; ST1 and ST2 Done. Nothing committed. @manager
    
    **Changed:** `docs/overrides.md` (validators section, six passages), `docs/workflow.md` (the `validators` field entry), `CHANGELOG.md` (one bullet under 0.16.0 `### Changed`). `tests/meta`: 345 passed. No file under `src/` or `tests/` touched.
    
    **Not done: `CLAUDE.md`.** My session rules do not let an agent's message authorise a change to `CLAUDE.md`, so I left it untouched and propose the text for the operator to approve:
    - status-prose rule, appended: "A rule of this project, not a default of the tool: `squads/.overrides/workflow.toml` selects `no_status_banner` on every type."
    - `sq check` gate section, appended: "The title rule and the status-banner rule are this project's own selections, made in `squads/.overrides/workflow.toml` (`subentity_title_max:120`, `no_status_banner`), not defaults of the tool."
    
    **Retired statements and what replaced them** (each search validated on the HEAD text first, whitespace-collapsed, over `docs/`, README, PYPI.md and the unreleased changelog section):
    - "Two checks are not selected for you anywhere in the bundled spec" (`docs/overrides.md`): now four, as a list, with what each of the two new ones reports.
    - "Two checks ship unselected" (`docs/overrides.md`, hard-stop table notes): now four, named.
    - "Declare no parameter and the type gets the bundled default": now "Name the check with no parameter and the threshold is 120. A type that does not name the check at all has no threshold".
    - "neither the cross-cutting core nor a category bundle can be subtracted from": kept, plus "The four checks nothing bundled selects are in neither".
    - "refuses a plain retitle of the item" (`subentity_title_max:40@error`): replaced by what was driven, see below.
    - The array-replacement example used `subentity_body_written`, which the `work` bundle already gives an epic; it now restores `no_status_banner`, names `epic` and `skill` as the two types that ship a list, and quotes the refusal of a splat on `task`.
    - No sentence anywhere had `sq check` warning on a banner or a long title unselected; no example shows the advisory without its `validators` line. README and PYPI.md mention neither check.
    
    **Driven** (dev build, scratch squads under the session scratchpad, bare exit codes; scripts and logs in `writer-997/`):
    - Bundled spec, banner bodies (`## Status`, `STATUS:`, `**Status:**`), a banner summary and 121-character story and subtask titles: `sq check` "no issues", exit 0; `add-story` prints no advisory.
    - `[items.feature] validators = ["no_status_banner", "subentity_title_max"]`: both warnings, exit 0; `add-story` at 121 prints the advisory, at 120 nothing. Line removed: clean again, no advisory. Tasks and decisions carrying the same content are not reported.
    - Bare name gives 120; `subentity_title_max:40` reports a 49-character subtask title at check and at `add-subtask`.
    - Banner detection: first line only; a mid-body `## Status` is silent; one finding per item, body first, summary otherwise.
    - `no_status_banner@error`: `sq check` exit 3; the body write that adds the banner, a retitle and a status transition all exit 0.
    - `subentity_title_max:40@error`: `sq check` exit 3; the task's retitle, summary change and status transition exit 1 with the finding; `add-subtask` with an over-long title and a subtask retitle past the number both exit 0.
    - `epic` list replaced without the splat: lint OK, epic accepts a parent. With `"$(*items.epic.validators)"`: parent refused again. Same splat on `skill` loads. On `task`: "dangling splat path 'items.task.validators' has no counterpart in the bundled base", lint exit 1.
    - A `records` type hosting `finding`: refused with no `validators`; loads with `subentity_title_max` alone and then reports at 120 with the advisory; with another sub-entity check only, neither.
    - A type hosting no kind (`bug`, `decision`) may name the title check and reports nothing.
    - Every refusal message already quoted in the section (repeat, level-only repeat, two numbers, `:0`, `@warn:40`, unknown name): text unchanged.
    - Released 0.15.0 in a scratch squad warns on both by default, which is the "before" of the release note.
    
    **Read, not driven:** the membership of the core and the bundles (`COMMON_CORE`, `CATEGORY_BUNDLES`); that only `epic` and `skill` ship a list (bundled `workflow.toml`); the banner pattern's case-insensitivity beyond the spellings driven; "no file in the squad is touched".
    
    **Found on the way, not part of this change:** at `@error` the title check does not refuse the sub-entity write that makes a title too long, only the host item's next edit. The docs now say so; whether it is intended is a question for the tech lead.
- [2026-10-12T06:19:24Z] Catherine Manager:
  - The two CLAUDE.md sentences were added by the manager on the operator's explicit approval of 2026-10-12, since the writer's session rules do not let an agent's brief authorise an edit to that file. Committed with the docs; closing.
<!-- sq:discussion:end -->
