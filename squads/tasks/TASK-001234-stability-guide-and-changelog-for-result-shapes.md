---
id: TASK-1234
sequence_id: 1234
type: task
title: Stability guide and changelog for result shapes
status: Ready
parent: FEAT-1226
author: tech-lead
priority: medium
refs:
- ADR-1224:implements
- TASK-1232:depends-on
- TASK-1233:depends-on
description: Frozen and provisional JSON shapes, the schema-change rule, display keys
  and --json on every command, for adopters
subentities:
- local_id: ST1
  title: 'Stability guide: tiers, provisional shapes, schema rule'
  status: Todo
  story: US3
- local_id: ST2
  title: Display keys for adopters
  status: Todo
  story: US4
- local_id: ST3
  title: JSON output on every command, in docs and changelog
  status: Todo
  story: US2
created_at: '2026-10-28T22:12:43Z'
updated_at: '2026-10-28T22:28:30Z'
---
<!-- sq:body -->
## Goal

Tell adopters what the command layer changes for them (FEAT-1226 US2, US3, US4): `--json` on every command that prints a result, which JSON shapes are frozen and which are provisional, how an incompatible change ships, and what the display keys are. Written for someone adopting squads into their own project: no internal tracking references, no repository process, present tense.

## What it covers

- **`docs/stability.md`** (ADR-1224 point 3, ADR-1225 section 3 "Client and server compatibility"):
  - the shapes that had `--json` before this release keep their tier; the shapes that gain it now, and the display keys on every payload (`display`, `columns`, `rendered_body`, kind and ref-kind labels), are listed in Tier 3 under a provisional mark until the web front consumes them;
  - display values are of the display class: the key is frozen once the shape is, its content is not, and no client parses or compares it; the codes beside them keep their class, so a client that joins codes to the workflow catalogs is unaffected;
  - adding a field is compatible; removing, renaming or retyping one, or changing an operation incompatibly, ships as a schema change (a schema version bump and `sq migrate up`, after which a package and a squad, or a client and a daemon, at different schema versions refuse each other); the tier decides whether a change may happen at all;
  - one definition: the JSON a command prints is the body its route answers;
  - the `etag` key of the show result and the daemon's compatibility messages are documented with the daemon (TASK-1221), which links here for the rule.
- **Command reference and guides** that describe `--json`: every command that prints a result accepts it; a write prints what it wrote, a corpus-wide command its report, the package-data commands their text or index; `init --json` never prompts; the commands with no result of their own (`ui`, the parse-only groups, bare `workflow`) take none.
- **CHANGELOG**, unreleased section: one entry for `--json` on every command, one for the display keys, one for the compatibility rule. Entries may be added as each command group lands; this task owns their final wording.

## Acceptance

- FEAT-1226 acceptance, last bullet: the adopter documentation lists frozen and provisional shapes and states that an incompatible change ships as a schema change.
- FEAT-1226 US3, last bullet; US2 and US4 as documented behaviour.
- Every command, flag and key named exists in the shipped code: check each against the implementation, not the ADR.

## Test approach

- Run every documented command and `--json` example against a scratch squad outside this repository with the built package, and record what was run in a comment.
- `tests/meta/test_documented_commands_resolve_against_cli.py` stays green. New tests: 0.
- Depends on TASK-1232 and TASK-1233, so every shape is final when it is listed.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1234 add-subtask "<title>"`; track with `sq task 1234 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Stability guide: tiers, provisional shapes, schema rule

<!-- sq:subtask:ST1:body -->
`docs/stability.md`: the shapes that had `--json` before this release keep their tier; the shapes that gain it now and the display keys on every payload are listed in Tier 3 under a provisional mark until the web front consumes them; adding a field is compatible, an incompatible change ships as a schema change (schema version bump, `sq migrate up`, client and daemon at different schema versions refusing each other), and the tier decides whether it may happen at all; one definition for the CLI's JSON and the route's body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Display keys for adopters

<!-- sq:subtask:ST2:body -->
The display keys for adopters (ADR-1224 point 5): what `display`, `columns`, `rendered_body` and the kind and ref-kind labels carry, that their values are of the display class (no client parses or compares them), that the codes beside them keep their class, and how a front shows what the CLI shows without the vocabulary. CHANGELOG entry for the display keys.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — JSON output on every command, in docs and changelog

<!-- sq:subtask:ST3:body -->
Command reference and guides: every command that prints a result accepts `--json`; a write prints what it wrote, a corpus-wide command its report, the package-data commands their text or index; `init --json` never prompts; `ui`, the parse-only groups and bare `workflow` take none. CHANGELOG unreleased section: entries for `--json` on every command and for the compatibility rule. Every command and flag named is run against a scratch squad with the built package.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
