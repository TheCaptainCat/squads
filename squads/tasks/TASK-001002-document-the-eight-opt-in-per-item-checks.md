---
id: TASK-1002
sequence_id: 1002
type: task
title: Document the eight opt-in per-item checks
status: Done
parent: FEAT-901
author: tech-lead
assignee: tech-writer
priority: low
refs:
- TASK-1001:depends-on
- TASK-997:depends-on
description: 'Story 10: validators reference, release note and roles reference for
  the eight checks a type may select and the blocked flag one of them reads'
subentities:
- local_id: ST1
  title: Add the eight checks to the validators reference
  status: Done
  story: US10
- local_id: ST2
  title: Write the release note for the eight checks
  status: Done
  story: US10
- local_id: ST3
  title: Document the blocked flag and the role catalog's sixth key
  status: Done
  story: US10
created_at: '2026-10-12T05:46:28Z'
updated_at: '2026-10-16T22:50:28Z'
---
<!-- sq:body -->
## Scope

Story 10 of FEAT-901: what an adopter needs to read to use the eight opt-in per-item checks,
and the status-role flag one of them reads. The engine work is TASK-1001.

Owner: the tech writer. The developer's handoff comments on TASK-1001 (one for each part of
that task) list every adopter-visible fact with its exact text. Those lists are the input;
each claim is still checked against a scratch squad before it is written.

It is written against a build that contains all of TASK-1001, the `blocked` flag included.
The validators section of `docs/overrides.md` already describes `no_status_banner` and
`subentity_title_max` as checks a type selects; this builds on that text.

## Subtasks

- **ST1, the validators reference** in `docs/overrides.md`, and the passages that point at
  it.
- **ST2, the release note** in `CHANGELOG.md`.
- **ST3, the roles reference and the stability table**: the `blocked` flag beside `live` and
  `settled`, and the sixth key of `sq workflow roles --json` in `docs/stability.md`.

ST1 first: the release note links to its section. ST3 before ST1's entry for
`blocked_has_blocker`, which points at it.

## What the reader must be able to do

- Find the eight checks, what each reports and for which team it is meant, and the one line
  that selects each on a type.
- Know that none is selected by the bundled spec: a squad that names none sees no new
  finding, and nothing needs migrating.
- Know that the eight apply to `work` and `records` types only, and read each load-time
  refusal of a selection that cannot fire, with its exact text: any of the eight on a roster
  type; `ref_rule_target_typed` with no ref rule that declares a target; `assignee_present`
  with no status of a live role in the type's lifecycle; `blocked_has_blocker` with no status
  of a blocked-flag role in the lifecycle, or with no dependency-role ref kind.
- Write the two parameters correctly: `item_title_max:<n>` needs its number;
  `external_id_not_in_title:<regex>` needs a pattern that compiles, written in a TOML literal
  string, with no `@` in it. Each refusal is shown with its real message.
- Know what `@error` does for each check: six of them then refuse a create or an update, and
  the handoff's door table says which verb is refused and which verb is the way out; two
  (`body_written`, `settled_requires_discussion`) only change the exit code of `sq check`.
- **Read the warning about `external_id_not_in_title`, as the build behaves:** nothing
  bounds a match; the pattern runs on every `sq check`, and on a gated write of an item only
  when its type selects the check at `@error`, where the write holds the index lock while
  the pattern runs; a pattern that backtracks can therefore hang `sq check`, and at `@error`
  the write. A check selected at `warn` is not evaluated on a write.
- Know that active, settled and blocked are what a status's role declares (`live`, `settled`,
  `blocked`), never a role name or a status name, and what a squad that declares its own
  roles must add before it can select `blocked_has_blocker`.
- Know the limit the handoff reports for `body_written`: when it no longer recognises a
  scaffold.

## Acceptance (whole task)

- Story 10, all seven bullets, and nothing the build does not do. Where a story bullet and
  the build differ, the docs follow the build and the handoff says where.
- **Every command and every quoted message is run before it is written**, with a build that
  contains TASK-1001, in a scratch squad nested under the session scratchpad (print the
  working directory before any writing command, chain with `&&`, never this repository's own
  squad). The handoff labels each claim as driven or read.
- **The reader test.** Following only the docs, in a fresh scratch squad: confirm that an
  over-long title, an unwritten body and an item with no summary report nothing; add the
  documented lines; confirm each is reported; add one of the eight to a roster type and
  confirm the documented refusal. Record the commands and exit codes.
- **A stale-claim sweep, table-driven.** For each retired statement, search every file under
  `docs/`, the README, `PYPI.md` and the unreleased section of the CHANGELOG, on
  whitespace-collapsed text, and validate each search on the previous wording first:
  - any count or list of the checks that nothing bundled selects;
  - any sentence saying item titles, item bodies or summaries are not checked;
  - any statement of which checks take a parameter, or of which stay out of the create/update
    gate, or that every selected check runs on a write;
  - any list of the keys of a status role or of a `sq workflow roles --json` row.
  The handoff lists each statement, where it was, and what replaced it.
- Adopter docs carry no item references and no development-process content. Each sentence
  passes the stranger test: true and meaningful for a reader who never saw the change.

## Gates and working rules

- `uv run --all-extras pytest tests/meta` passes: the gate that documented commands resolve
  against the CLI, and the gate against stray item references in docs.
- `sq check` is clean before handback, run from the main checkout with the released tool:
  `cd /home/pchat/projects/squads && pwd && ~/.local/bin/sq check`. Board writes (subtask
  status, comments, the handoff) are made the same way, never from a worktree and never with
  the dev build. No board item is created from a worktree.
- No source or test file is edited. A doc claim that the build contradicts is reported on
  TASK-1001 as a comment, not worked around in prose.
- The CHANGELOG entry is self-contained under the unreleased version's `### Added`, so
  merging it with entries written in another tree is a pure addition.
- This repository's own selection of two of the checks is not described as made: it is a
  step of release preparation, and `CLAUDE.md` is not edited for it here.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1002 add-subtask "<title>"`; track with `sq task 1002 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add the eight checks to the validators reference

<!-- sq:subtask:ST1:body -->
**Goal.** `docs/overrides.md` § "Validators" lists the eight checks among the ones a type
may select, with what each reports, its entry form, its default level, what `@error` does for
it, what clears a finding, and when selecting it is refused.

**Approach**

- One entry per check, in the order an adopter would look for them: the two about titles
  (`item_title_max:<n>`, `external_id_not_in_title:<regex>`), the two about content
  (`body_written`, `description_present`), the two about status (`assignee_present`,
  `settled_requires_discussion`), the two about refs (`blocked_has_blocker`,
  `ref_rule_target_typed`). Each entry says who the check is for, in one clause, as the
  feature's stories do.
- The passage that names the checks nothing bundled selects is brought in line, wherever it
  occurs in the file.
- **Where the eight apply.** They apply to `work` and `records` types and never to `role`,
  `skill` or `operator` items; naming one on a roster type is refused, with the message
  quoted.
- **A selection that cannot fire is refused.** One passage lists the three other cases with
  their exact text, and says how to make each selectable: a ref rule with a target; a status
  of a live role in the lifecycle; a status of a blocked-flag role in the lifecycle and a
  dependency-role ref kind.
- The parameter passage gains the two parameterised checks: the number is required for
  `item_title_max`; the pattern is required for `external_id_not_in_title`, is a regular
  expression searched for anywhere in the title, and is written in a TOML literal string.
  Each refusal the handoff lists is shown with its message, the reserved `@` included.
- **The warning for `external_id_not_in_title`**, as the task body words it and as the build
  behaves: nothing bounds a match, where the pattern runs, and what a pattern that backtracks
  can hang.
- One passage on levels states which of the eight refuse a write at `@error`, with the verb
  that is refused and the verb that is the way out, which two never refuse a write, and that
  a check selected at `warn` is not evaluated on a write.
- The three status checks say what they read: the `live`, `settled` and `blocked` flags of
  the status's role, with a pointer to the roles reference (ST3).
- One worked example selects `item_title_max:120` and `body_written` on a type, using the
  splat form on a type that ships a list.
- `docs/workflow.md`: any passage the sweep finds agrees with the section.

**Tests**

- Every fenced command and quoted message in the changed passages is run in a scratch squad
  with a build that contains TASK-1001; the handoff lists them with exit codes.
- The reader test of the task body.
- The stale-claim sweep of the task body over `docs/`, each search validated on the old
  wording.

**Falsify.** Take the worked example and remove its `validators` line: the outcome the
example states must stop holding in the scratch squad. If it still holds, the example was not
demonstrating the selection; rewrite it.

**Acceptance.** Story 10, bullets one to six: an adopter can select each of the eight from
the section alone, and every refusal, every `@error` behaviour and the warning it states was
driven.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Write the release note for the eight checks

<!-- sq:subtask:ST2:body -->
**Goal.** An adopter reading the release notes learns that eight opt-in checks exist, that
none runs unless a type names it, that a status role can now declare that it means blocked,
and where to read how.

**Approach**

- `CHANGELOG.md`, the unreleased version, `### Added`: one bullet for the checks. It names
  the eight by what each reports, says each is selected per `work` or `records` type in
  `.overrides/workflow.toml` and is off until then, gives one selecting line as the example,
  and links to the validators section ST1 wrote.
- It says an existing squad needs no migration and sees no new finding.
- One bullet for the flag: a status role accepts `blocked`, the bundled `blocked` role
  declares it, and `sq workflow roles --json` rows gain the key, additively. It says what a
  squad that declares its own roles does to use `blocked_has_blocker`.
- What the developer's handoff reports as changed for an existing squad goes under
  `### Fixed` or `### Changed`, each as what the adopter sees: a rule on the default ref kind
  is now satisfied by an edge of that kind; `subentity_title_max` refuses a parameter it used
  to fail on; a check selected at `warn` is no longer evaluated on a write.
- No entry under `docs/migration.md`: there is no migration step for this.

**Tests**

- The selecting line in the bullet is run in a scratch squad with a build that contains
  TASK-1001, from a squad where the finding is absent to one where it is reported. The
  handoff records the commands.
- The link target resolves to the heading ST1 left in place.
- The stale-claim sweep of the task body over the README, `PYPI.md` and the unreleased
  section of the CHANGELOG.

**Falsify.** In the scratch squad, remove the selecting line again: the finding the bullet
says it turns on must disappear. If it stays, the bullet describes a squad where the check
was never off; rewrite it.

**Acceptance.** The release note states the eight checks as opt-in, shows one selection,
states the flag and the catalog key, and says no migration is needed. No item id and no
build-process wording in the entry.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Document the blocked flag and the role catalog's sixth key

<!-- sq:subtask:ST3:body -->
**Goal.** The roles reference documents the `blocked` flag beside `live` and `settled`, and
`docs/stability.md` lists the new key of `sq workflow roles --json`.

**Approach**

- The status-roles reference (the role catalog passages of `docs/overrides.md` and
  `docs/workflow.md`): `blocked` is a boolean a role declares, default false; the bundled
  `blocked` role declares it and no other bundled role does; it says the role's statuses mean
  the item is waiting on something else. It is read by `blocked_has_blocker` and by nothing
  else: `sq blocked` and the `blocked` key of `sq tree --json` come from dependency edges.
- **A squad that declares its own roles** has no blocked role until one of them declares the
  flag. The passage shows the one line to add, and the refusal `blocked_has_blocker` gives
  until a status of the type's lifecycle carries such a role, with its exact text.
- A non-boolean value is refused; the message is quoted.
- `docs/stability.md`: the row for `sq workflow roles --json` gains `blocked` as its sixth
  field, and any sentence beside the table that states the row's fields agrees.
- The example output of `sq workflow roles`, wherever the docs show it, has the column.

**Tests**

- `sq workflow roles` and `sq workflow roles --json` are run on a fresh scratch squad and on
  one whose override declares a flagged role of its own; every quoted line is from those
  runs.
- The own-roles passage is followed literally in a scratch squad: select
  `blocked_has_blocker`, read the refusal, add the documented line, and the spec loads.
- The stale-claim sweep of the task body for any list of a role's keys or of the catalog
  row's keys.

**Falsify.** In the scratch squad, take the documented line back out: the refusal must
return. If the spec still loads, the passage is describing a squad that kept the bundled
role; rewrite it for one that did not.

**Acceptance.** Story 10, bullet seven. The stability table and the build agree on the six
keys, in order.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-12T05:48:44Z] Olivia Lead:
  - 2026-10-12: drafted with TASK-1001, which carries the breakdown note. Draft and unassigned; it starts after TASK-1001 is built and TASK-997 has landed.
- [2026-10-12T06:48:33Z] Olivia Lead:
  - 2026-10-12: brought in line with story 10. ST1 and ST2 now map to it, ST3 added for the roles reference and the stability table. It needs all of TASK-1001, the blocked flag included, so it starts after that task's second part. TASK-997 is Done and its text is the base.
- [2026-10-16T22:49:32Z] Theo Writer:
  - Docs written, not committed. Build used: an archive of HEAD e56f7a18 (0.16.0), run as `uv run --project <export> sq -C <scratch squad>`, scratch squads under the session scratchpad. @manager
    
    - **ST1, docs/overrides.md § Validators.** "The work-policy checks" is rewritten: one entry per check in the order titles, content, status, refs, each with who it is for, what it reports and what clears it; the existing feature example kept; the other four messages; a worked example (`item_title_max:120` + `body_written` on feature and on epic with the splat); the `body_written` limit; where the eight apply with the roster refusal; the four cannot-fire refusals; both parameters with every refusal (missing, non-positive, compile error, empty match, compile warning, `@`, the TOML basic-string backslash error); the pattern warning; a per-check `@error` table with the refused verb and the way out; and "a check selected at `warn` is not evaluated on a write", also added under the gate paragraph.
    - **ST2, CHANGELOG `## [0.16.0]`.** Added: the eight checks; the `blocked` flag and the sixth catalog key. Changed: `warn` checks are not evaluated on a write. Fixed: a default-kind ref rule satisfied by a bare edge; `subentity_title_max:²` refused by name.
    - **ST3.** `blocked` bullet, table column, own-roles passage (refusal, the line to add, the loading override) and catalog output in overrides.md § Status roles; the same bullet and column in docs/workflow.md; `blocked` added to the stability.md row and the sentence beside it.
    - **Driven** (exit codes in brackets): unselected squad with a 144-char title, unwritten body and no summary prints no issues [0]; the documented lines report each [0]; one of the eight on `role` is refused by lint [1] and by `sq list` [1]. Every quoted message and refusal was produced by a run. Worked example falsified: without the lines, no issues; without the splat, `epic update --parent` is accepted [0], with it refused [1]. Door table: every refusal and every way out [1]/[0]; body_written and settled at error: transition accepted, `sq check` [3]; import pre-pass refusal [1], import with a body_written error finding [3]. Pattern warning: `(a+)+$` at warn, create returns in 0.8 s while `sq check` and an import hang (killed at the timeout, [124]); at `@error` the create hangs [124]. NFC count, `\x40`, `(?i)`, alternation, `foo@warn`, repeat refusal, bundled accept/refuse cells, and `blocked = "yes"` / `1` refusals all driven. BUG-1003 compared with the released 0.15.0 (reported) and the export (silent).
    - **Read, not driven:** the write holds the index lock while the pattern runs; the review-target case of the body_written limit.
    - **Stale-claim sweep** (whitespace-collapsed, each pattern checked first on the old wording): "The other five take part in the write gate" was wrong, six do, and the passage is replaced; the four-key role lists (workflow.md cheatsheet line and "four attributes", the stability.md row and the sentence beside it, both bundled-role tables) now carry `blocked`. Nothing found in README, PYPI.md or the unreleased CHANGELOG.
    - **Where the docs follow the build, not the handoff:** "clearing [the assignee] refused" cannot be driven through the CLI. `update --assignee ""` prints "updated" and leaves the assignee unchanged, and no other verb clears one. The table lists only the move to a live status. @qa that no-op may need a bug.
    - Not run, per my brief: `pytest tests/meta`.
<!-- sq:discussion:end -->
