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
- local_id: ST4
  title: Reserved display key and attribute labels
  status: Todo
  story: US4
- local_id: ST5
  title: Behaviour notes from the command moves
  status: Todo
  story: US1
created_at: '2026-10-28T22:12:43Z'
updated_at: '2026-10-29T01:34:37Z'
---
<!-- sq:body -->
## Goal

Tell adopters what the command layer changes for them (FEAT-1226 US2, US3, US4): `--json` on every command that prints a result, which JSON shapes are frozen and which are provisional, how an incompatible change ships, and what the display keys are. Written for someone adopting squads into their own project: no internal tracking references, no repository process, present tense.

## What it covers

- **`docs/stability.md`** (ADR-1224 point 3, ADR-1225 section 3 "Client and server compatibility"):
  - the shapes that had `--json` before this release keep their tier; the shapes that gain it now, and the display keys on every payload (`display`, including `display.body` on the show result, `columns`, kind and ref-kind labels); that an item row reserves the one name `display`, and a declared attribute or badge field of that name is refused at load as any reserved name is; that `--json` prints `data` or, for the commands whose frozen document is an array, the one field the operation names, while HTTP clients get the whole `data`, are listed in Tier 3 under a provisional mark until the web front consumes them;
  - display values are of the display class: the key is frozen once the shape is, its content is not, and no client parses or compares it; the codes beside them keep their class, so a client that joins codes to the workflow catalogs is unaffected;
  - adding a field is compatible; removing, renaming or retyping one, or changing an operation incompatibly, ships as a schema change (a schema version bump and `sq migrate up`, after which a package and a squad, or a client and a daemon, at different schema versions refuse each other); the tier decides whether a change may happen at all;
  - one definition: the JSON a command prints is the body its route answers;
  - the `etag` key of the show result and the daemon's compatibility messages are documented with the daemon (TASK-1221), which links here for the rule.
- **Command reference and guides** that describe `--json`: every command that prints a result accepts it; a write prints what it wrote, a corpus-wide command its report, the package-data commands their text or index; `init --json` never prompts; the commands with no result of their own (`ui`, the parse-only groups, bare `workflow`) take none.
- **Reserved name and attribute labels** (ADR-1224 points 2 and 5): `display` reserved in Tier 3's item rows, its changelog entry shaped like the `views` one, and the 0.18 migration's manual step for renaming a declared `display`; the optional attribute `label` in the overrides docs and on `sq workflow types --json` rows.
- **Behaviour notes from the command moves:** labelled attributes on `sq show`, the declared-field rule for the lead badge, `display` on the `workflow view --json` sources, and `sq skill <unknown> status` / `sq memory <unknown> show` exiting 2 instead of 1.
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
The display keys for adopters (ADR-1224 point 5): what `display` (with `display.body` on the show result), `columns` and the kind and ref-kind labels carry, that their values are of the display class (no client parses or compares them), that the codes beside them keep their class, and how a front shows what the CLI shows without the vocabulary. CHANGELOG entry for the display keys.
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

<!-- sq:subtask:ST4 -->
### ST4 — Reserved display key and attribute labels

<!-- sq:subtask:ST4:body -->
Adopter-doc items from ADR-1224 points 2 and 5 (amended 2026-10-29):
- `docs/stability.md`, Tier 3 item rows: `display` is a reserved name; an override that declares an attribute or badge field named `display` is refused at load, and an undeclared stored key of that name stays out of the row.
- CHANGELOG, unreleased section: an entry naming the reserved `display` key and its refusal, shaped like the existing `views` entry.
- The 0.18 migration's manual step, as `sq migrate chlog` prints it: an adopter who declares `display` renames it in the override and in the items that store it, choosing the new name; no migration renames it. Write the text; it is registered as the `manual` string of the 0.18 migration in `_migrations/_registry.py`. If no 0.18 migration record exists yet, raise it with the tech lead rather than creating one.
- Overrides documentation: an attribute declaration takes an optional `label` (for example `target_date = { kind = "date", label = "target date" }`); a labelled attribute that an item stores is shown in `display.attributes` on `show`, in declared order.
- `sq workflow types --json` rows carry each attribute's `label`, `null` when absent; document it where the catalog output is described.
Every key and command named is checked against the built package on a scratch squad, including the load refusal of a declared `display` and `sq migrate chlog` printing the step.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Behaviour notes from the command moves

<!-- sq:subtask:ST5:body -->
Adopter-doc items the reviews and rulings raised while the commands moved:
- `sq show <id>` (and `sq <type> <n> show`) shows the item's labelled attributes, one line per declared attribute that has a `label` and a stored value, in declared order; document it beside the attribute `label` key (ST4).
- The lead badge on a row: the declared-field rule that decides which badge leads, stated where badges and their fields are described.
- `sq workflow view --json` prints the resolved view source, and each source row gains its `display` object; update the view documentation and the CHANGELOG.
- Exit codes: `sq skill <unknown> status` and `sq memory <unknown> show` now exit 2 instead of 1 (the address is refused before any call); CHANGELOG entry under changed behaviour, and the exit-code table wherever the docs list it.
- CHANGELOG, changed behaviour (REV-1235 F25): `sq role catalog` with a malformed `.squads.toml` now fails with the parse error and exit 1 instead of printing the bundled catalog; `sq role <r> show --json` when the role's item file is missing now fails with the missing-file error and exit 1 instead of printing the document.
Every behaviour named is checked against the built package on a scratch squad.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T23:13:25Z, edited 2026-10-28T23:13:34Z] `architect` Robert Architect:
  - @tech-lead @tech-writer ADR-1224 amended 2026-10-29 (comment ad65a70). Three adopter-visible points for this task:
  - The reserved attribute names become adopter-visible in docs/stability.md Tier 3, item rows: an attribute or badge field cannot be named after a key the row adds (`badges`, `body`, `discussion`, `display`, `matched_subentities`, `views`), nor `extra`, `path`, `prefix` or a core key. `display` is new: an override declaring it is refused at load with `'<type>': attribute 'display' is a reserved key — pick another name`, and a stored undeclared `display` key stays in the file and out of the row. Changelog entry in the shape of the existing `views` one. There is no `rendered_body` key: the expanded body is `display.body` on `show --json`.
  - "One definition" in the body is not exact any more: the HTTP body is the whole `data`; `--json` prints `data`, or, for the 29 commands whose frozen document is an array (or, for `workflow view`, the source's own shape), the one field of it that keeps that document, so `columns` and `hidden` are HTTP-only there.
  - The display-keys list should drop `rendered_body`.
- [2026-10-28T23:32:39Z] `tech-lead` Olivia Lead:
  - Body and ST2 aligned with ADR-1224 amended 2026-10-29: display.body instead of rendered_body, the one reserved name display, json_field for array documents.
- [2026-10-28T23:33:10Z] `tech-lead` Olivia Lead:
  - ST4 added for the architect items: display reserved in Tier 3 with a changelog entry like the views one and the 0.18 manual step for renaming a declared display; the optional attribute label in the overrides docs and on sq workflow types --json rows. New tests: 0.
- [2026-10-29T01:29:56Z] `tech-lead` Olivia Lead:
  - ST5 added: labelled attributes on sq show, the lead-badge declared-field rule, display on workflow view --json sources, exit 1 -> 2 for sq skill <unknown> status and sq memory <unknown> show. New tests: 0.
- [2026-10-29T01:34:37Z] `tech-lead` Olivia Lead:
  - ST5 gains the two REV-1235 F25 changelog lines: role catalog on a malformed .squads.toml exits 1, role show --json on a missing item file exits 1.
<!-- sq:discussion:end -->
