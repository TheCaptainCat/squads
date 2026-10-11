---
id: TASK-991
sequence_id: 991
type: task
title: Document capabilities, declared developers and the 0.16 upgrade
status: Draft
parent: FEAT-986
author: tech-lead
assignee: tech-writer
priority: medium
refs:
- TASK-990:depends-on
- ADR-984:implements
description: Adopter docs, stability refresh and CHANGELOG for capabilities, sq dev
  add --slug, the [dev] template and the two upgrade changes with no automatic fix
subentities:
- local_id: ST1
  title: Document capabilities and developers in roles and overrides
  status: Todo
  story: US10
- local_id: ST2
  title: Write the 0.16 upgrade section and the changelog entries
  status: Todo
  story: US10
- local_id: ST3
  title: Refresh stability.md, internals, agents and the README
  status: Todo
  story: US10
created_at: '2026-10-09T20:28:03Z'
updated_at: '2026-10-09T20:39:47Z'
---
<!-- sq:body -->
## Scope

Story 10 of FEAT-986: the adopter documentation for capabilities, declared developers,
`sq dev add --slug`, the `[dev]` template, and the two upgrade changes that have no automatic
fix. The engine work is TASK-990; this task describes what an adopter now does differently.

Owner: the tech writer. The developer's handoff comment on TASK-990 lists every
adopter-visible change with its exact text (keys, flags, messages, exit codes, changed
generated sentences, the migration's report and manual text). That list is the input; each
claim is still checked against a scratch squad before it is written.

## Subtasks

- **ST1, `docs/roles.md` and `docs/overrides.md`.** The reference for the new vocabulary.
- **ST2, the upgrade section and the CHANGELOG.** What changes on upgrade, with a worked
  example for each change that has no automatic fix.
- **ST3, `docs/stability.md` and the documents that follow.** The contract refresh, then
  `docs/internals.md`, `docs/agents.md` and the README.

ST1 first: ST2 and ST3 link to its sections.

## Acceptance (whole task)

- Story 10, all bullets, each subtask covering the ones it names.
- **Every command and every quoted message is run before it is written**, with the dev build
  in a scratch squad nested under the session scratchpad (print the working directory before
  any writing command, chain with `&&`, never this repository's own squad). The handoff
  labels each claim as driven or read.
- **The reader test.** Following only the docs, in a fresh scratch squad, declare a developer
  role in a role file and a second capability with a playbook guide addressing it; `sq check`
  is clean and the pointer of each role lists the skill. Record the commands run.
- **A stale-claim sweep, table-driven.** For each retired statement (the slug is always
  `<tech>-dev`; the `*dev` sentinel matches any `<tech>-dev` role; a developer's definition
  is refreshed from the bundled catalog; an override may be written before its developer is
  added; a name is picked for a `<tech>-dev` slug with no role yet), search every file under
  `docs/`, the README and the CHANGELOG's unreleased section, on whitespace-collapsed text,
  and validate each search on the previous wording first. The handoff lists each statement,
  where it was, and what replaced it.
- Adopter docs carry no item references and no development-process content. Each sentence
  passes the stranger test: true and meaningful for a reader who never saw the change.
- Example slugs that are ordinary legal slugs (`python-dev`) may stay as examples. What goes
  is any sentence that states the suffix as a rule.

## Gates and working rules

- `uv run --all-extras pytest tests/meta` passes: the gate that documented commands resolve
  against the CLI, and the gate against stray item references in docs.
- `sq check` is clean before handback.
- No source or test file is edited. A doc claim that the build contradicts is reported on
  TASK-990 as a comment, not worked around in prose.
- `docs/migration.md` describes the 0.16 step as one step. FEAT-976 and FEAT-980 add their
  own paragraphs to the same section when they land; write this one so it can be extended.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 991 add-subtask "<title>"`; track with `sq task 991 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Document capabilities and developers in roles and overrides

<!-- sq:subtask:ST1:body -->
**Goal.** `docs/roles.md` and `docs/overrides.md` describe roles as they now work: a role
declares capabilities, the playbook addresses a capability, and a developer is a role that
holds one.

**Approach**

- `docs/roles.md`: the developer section (around the `sq dev add` examples) stops stating
  that the slug is always `<tech>-dev`. It documents `capabilities` on a role, the two ways
  to have a developer (templated with `sq dev add`, declared in a role file), that both are
  treated alike, `sq dev add --slug` and a second developer for one tech, and that
  `sq dev list` lists both kinds. The "Custom non-dev roles" heading loses the distinction
  it draws.
- `docs/overrides.md`: the per-slug role file section and the catalog document section gain
  the `capabilities` key and the `[dev]` template (model, colour, name pool, capabilities,
  and that existing developers pick up a change on `sq sync`, with what a stored model
  means). The playbook section replaces "the `*dev` sentinel" with the `*<name>` subject,
  including a project capability over two roles. The passage that says to write an override
  first and run `sq dev add` afterwards is rewritten for what now happens.
- One worked example each: declare a developer role; declare a second capability and
  address it.

**Tests**

- Every fenced command in the changed sections is run in a scratch squad; the handoff lists
  them with their exit codes.
- The stale-claim sweep of the task body, restricted to these two files, with each search
  validated on the old wording.

**Falsify.** Take one worked example and remove the `capabilities` line from the role file
it shows: the example's stated outcome must stop holding in the scratch squad. If it still
holds, the example was not demonstrating the feature; rewrite it.

**Acceptance.** Story 10, first bullet, and its last (the reader test of the task body).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Write the 0.16 upgrade section and the changelog entries

<!-- sq:subtask:ST2:body -->
**Goal.** An adopter upgrading to 0.16 learns, before running anything, the two changes that
have no automatic fix, and what the migration prints.

**Approach**

- `docs/migration.md`, the section for the 0.16 step, with a worked example for each:
  - a custom role whose slug ends in `-dev` must declare `capabilities = ["dev"]` to keep the
    developer guidance: what `sq migrate up` reports, the line to add, `sq sync`, and how to
    confirm it;
  - an override file written before its developer is added is now reported by `sq check`,
    and `sq role <slug> show` no longer previews a developer that does not exist: the
    message, and the two ways out (`sq dev add`, or remove the file).
- The same section states that an existing developer picks up a project `[dev]` override on
  the next `sq sync`, and that stamped catalog, playbook and role overrides report "may be
  stale" after the upgrade, with the two commands that clear it.
- `CHANGELOG.md`, unreleased section: Added (capabilities, `*<name>`, `sq dev add --slug`,
  the `--json` key), Changed (the two upgrade changes, generated text naming roster slugs,
  `sq dev list`), Fixed (the `[dev]` override reverted by `sq sync`), in the house style of
  the entries already there. No item references.

**Tests**

- Each worked example is driven end to end on a squad initialised by the previous release
  and upgraded with the dev build. The quoted report line and messages are copied from that
  run, not from the handoff.
- Table for the changelog: one row per adopter-visible change in the developer's handoff,
  with the entry that covers it or the reason it has none. No row is left blank.

**Falsify.** For the first example, skip the documented fix and confirm the stated symptom
appears (the pointer loses the developer skills). For the second, confirm `sq check` reports
the file before the fix and is clean after each of the two ways out.

**Acceptance.** Story 10, third and fourth bullets, and the CHANGELOG part of the second.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Refresh stability.md, internals, agents and the README

<!-- sq:subtask:ST3:body -->
**Goal.** `docs/stability.md` states the new contract, and the remaining documents stop
describing the old one.

**Approach**

- `docs/stability.md`: Tier 1 gains the `capabilities` key of the role document and of
  `[dev]`, and the `*<name>` subject of a playbook guide (the playbook override is not
  described there today). Tier 3 gains `capabilities` on `sq role catalog`, `sq role list`,
  `sq role <addr> show` and the `roster[]` rows of the `playbook` view payload, as an
  additive key that is always an array. The CLI tier gains `sq dev add --slug` and the two
  exit-1 paths. State that an older package refuses a document carrying the new key.
- `docs/internals.md`, `docs/agents.md` and the README: every passage that explains
  developers by the suffix, the `*dev` sentinel or the stored marker is brought in line.
- ADR-984 is the source for what is promised. A promise the decision does not make is not
  added here.

**Tests**

- Each `--json` claim is checked against real output from a scratch squad: the key is
  present and is a list for a bundled role, a templated developer and a declared one.
- The stale-claim sweep of the task body over these four files and over everything under
  `docs/` not covered by ST1 and ST2.

**Falsify.** Pick two statements added to `docs/stability.md` and try to break each in the
scratch squad (a role with no capabilities: is the key still present; an override naming
`*dev` written for the previous release: does it still load). Record both results.

**Acceptance.** Story 10, second bullet (except the CHANGELOG, which is ST2's) and the
fourth.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T20:39:47Z] Olivia Lead:
  - 2026-10-09: authored for story 10 of FEAT-986; assigned to the tech writer and left in Draft. Its input is the developer's handoff list on TASK-990, so it starts after that task is reviewed. Dispatch note for @manager: this is adopter-facing contract text (the stability refresh, the upgrade section), which has needed a stronger model than the writer's default before.
<!-- sq:discussion:end -->
