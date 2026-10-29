---
id: FEAT-1226
sequence_id: 1226
type: feature
title: Every command answers in JSON, one shape for CLI and API
status: InProgress
parent: EPIC-29
author: product-owner
priority: high
refs:
- MILE-1152:targets
- ADR-1224:depends-on
- ADR-1225
- FEAT-1140
description: Each command calls one operation and renders its result; --json on every
  command that prints one, and the same shape served by the API
subentities:
- local_id: US1
  title: Output unchanged as each command moves onto its operation
  status: InProgress
- local_id: US2
  title: JSON output on every command that prints a result
  status: InProgress
- local_id: US3
  title: One result shape for the CLI and the API
  status: InProgress
- local_id: US4
  title: Results carry their own display
  status: InProgress
- local_id: US5
  title: The terminal UI reads through the same API
  status: InProgress
- local_id: US6
  title: Local commands are no slower than in 0.17.0
  status: Todo
created_at: '2026-10-28T22:00:08Z'
updated_at: '2026-10-29T07:12:29Z'
---
<!-- sq:body -->
## Problem

Half of the CLI's commands print only human text: an agent or a script that wants a write's result, a roster entry or a repair report has to parse prose. The JSON the other half prints is assembled in the CLI, separately for each command, and the daemon's routes (FEAT-1140) need the same results as typed JSON bodies. Two definitions of one result would drift. And what the CLI displays (labels, badges, column headers, names) is worked out on the client from the vocabulary, so a browser front would have to hold the vocabulary to show anything.

## What an adopter gets

- `--json` on every command that prints a result, not only on the reads that have it today.
- One definition per result: the JSON a command prints is exactly the body its route answers, so a script written against the CLI and a front written against the API read the same shape.
- Results that carry their own display: labels, rendered badges, column headers, display names and the rendered body travel with the data, so a client that holds no vocabulary shows what the CLI shows.
- The terminal UI reading the squad through the same API as the CLI.
- No change to what a command prints today: the same human output, the same JSON keys, the same exit codes and error text.

## Scope

- Every command of the CLI moved onto one operation that returns its result; a command parses, validates what the vocabulary alone decides, makes its call, and renders the result.
- `--json` added to the 55 commands that print a result and lack it.
- Display content (labels, badges, columns, names, rendered body, the working-language notice) carried in every result, as additive keys.
- The terminal UI on the same API, in local mode and as a daemon client (FEAT-1140 holds its remote behaviour).
- The compatibility rule for result shapes, and their documentation in the stability guide.

The command-layer design is decided in ADR-1224; this feature states the outcomes. It comes first in the release: the daemon's routes are generated from the operations it creates.

## Non-goals

- The routes themselves, remote mode and the daemon (FEAT-1140).
- New commands or new options other than `--json`.
- Freezing the shapes that had no `--json` before this release: they stay provisional until the web front consumes them (MILE-868).
- Pagination of listings and search results.

## Acceptance criteria

- Every command's human output, `--json` output, exit code and error text is unchanged, apart from keys added to JSON documents.
- Every command that prints a result accepts `--json` and prints its result as one JSON document; a write prints what it wrote, a corpus-wide operation its report.
- The JSON a command prints is the `data` of its route's answer, for every command.
- Every item, tree node, graph node, search hit and sub-entity in a result carries its display labels and badges, and every listing its columns.
- The terminal UI shows the same screens as before, reading through the same API as the CLI.
- The adopter documentation lists which JSON shapes are frozen and which are provisional, and states that an incompatible change to a shape ships as a schema change.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1226 add-story "As a <role>, I want … so that …"`; track with `sq feature 1226 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Output unchanged as each command moves onto its operation

<!-- sq:story:US1:body -->
As an adopter, agent or script author, every command I already use prints the same thing after its move onto one operation, so nothing I rely on breaks.

Done when:
- Each command parses its arguments, refuses what the vocabulary alone decides (an unknown type, status or badge code, conflicting flags) with exit 2 and today's text, makes one call, and renders the result it gets back. The one exception is `comment remove` without `--yes`, which shows the comments it is about to remove, asks, and then removes exactly the comments shown.
- Whether an addressed item exists, whether a slug is on the roster, and the duplicate-id warning are answered by the operation, with the message local mode prints today.
- Human output, `--json` documents, exit codes (1 for an error, 2 for usage, 3 for findings in `check` and `import`, 4 for a partial read) and error text are unchanged, apart from keys added to JSON documents (US4).
- A partial read still prints its result, then the `omitted` line on stderr, and exits 4; warnings print on stderr in human mode.
- The surface test suite passes unchanged as each group of commands moves.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — JSON output on every command that prints a result

<!-- sq:story:US2:body -->
As an agent or script author, I add `--json` to any command that prints a result and get that result as one JSON document, so I never parse human text.

Done when:
- The 55 commands that print a result and lack `--json` accept it: the item writes (comment add, update, status, body, retype, ref add and rm, view add and disable, sub-entity update and body), the role, skill, operator and dev verbs, board and memory writes, override scaffold and update, `sync`, `workflow show`, `workflow lint`, `docs`, `migrate help`, `migrate chlog`, `repair`, `renumber`, the `migrate` operations, `init` and `adopt`.
- A write prints the resource it wrote (an item row, a sub-entity, a roster row); a corpus-wide operation prints its report; the package-data commands print their text or index as data.
- `--json` never puts a prompt on stdout: `init --json` asks for no role names and keeps the defaults.
- Given with a comment verb that carries its own flag (`edit`, `remove`, `show`), `--json` on the comment group is a usage error.
- The commands that print no result of their own (the parse-only groups, `sq ui`, the bare `workflow` group) take no `--json`.
- The `daemon` commands that print a result carry `--json` from the start.
- Each new flag has a surface test that asserts its whole document.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — One result shape for the CLI and the API

<!-- sq:story:US3:body -->
As a script or front author, the JSON a command prints and the body its route answers are one shape with one definition, and I know which shapes may still change.

Done when:
- For every command, `--json` prints exactly the `data` of the answer its route gives, with no CLI-side assembly.
- Adding a field is a compatible change. Removing, renaming or retyping one, or changing an operation incompatibly, ships as a schema change: a schema version bump with its migration, after which a package and a squad, or a client and a daemon, at different schema versions refuse each other until `sq migrate up` or an upgrade.
- Which shapes may change at all is the stability guide's call: the shapes that had `--json` before this release keep their tier, and the new ones, with the display keys of US4, are listed as provisional until the web front consumes them.
- The stability guide states all of this for adopters.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Results carry their own display

<!-- sq:story:US4:body -->
As a front author, a result tells me how to display itself, so my client shows what the CLI shows without holding the workflow vocabulary.

Done when:
- Every item, tree node, graph node, search hit and sub-entity in a result carries its type label, its rendered status badge, each declared badge field with its label and rendered badge, and the assignee's display name.
- Every table or listing carries its ordered columns and their headers; sub-entity kinds carry their plural and heading, and refs and graph edges their kind's label.
- An item's result carries its body with view tags expanded beside the stored body, and a view's output comes rendered through the squad's own templates.
- Role and operator names come with pronouns applied or left out according to the squad's `[display]` setting, and the working-language notice comes as a warning.
- The CLI's renderer and the terminal UI display only what the result carries and never read the vocabulary or the squad's configuration.
- The codes beside the display keys keep their meaning, so a client that joins codes to the workflow catalogs is unaffected.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — The terminal UI reads through the same API

<!-- sq:story:US5:body -->
As an operator, the terminal UI (`sq ui`) shows the same screens as before, and reads the squad through the same API as every other command.

Done when:
- Browsing the tree, the reader, the memory reader, search, the board and the filter screen show what they show today, with labels, badges and display names taken from the results.
- In local mode the terminal UI reads the squad directly through the same calls as the CLI; each screen load is one call.
- The terminal UI holds no copy of the vocabulary: its filter choices come from the workflow catalogs the API serves.
- Its behaviour against a daemon (remote mode, retirement, a daemon that went away) is FEAT-1140's.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Local commands are no slower than in 0.17.0

<!-- sq:story:US6:body -->
As an adopter in local mode, the commands I run most are no slower after this release than in 0.17.0.

Done when:
- `sq <type> <n> show`, `sq list` and `sq tree`, each as the median of 31 runs interleaved with the released 0.17.0 against the same squad on the reference host, take no longer than they do in 0.17.0.
- The measurement is a script under `scripts/` that anyone can rerun, and its numbers are recorded with the release.
- The remote client budget is FEAT-1140's, not this story's.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T22:06:03Z] `product-owner` Nina Product:
  - Created 2026-10-28 for ADR-1224 (the command layer), separate from FEAT-1140 because it is visible in local mode on its own, comes first in the release (op-pierre, MILE-1152, 2026-10-28) and gives the refactor's tasks their own parent. Same epic (EPIC-29), targets MILE-1152.
    - Stories: US1 output unchanged, US2 JSON output on the 55 commands, US3 one result shape and its compatibility rule, US4 results carry their own display, US5 the TUI on the same API (its daemon behaviour is FEAT-1140 US13).
    - Left Draft. @tech-lead break into tasks per ADR-1224's increments.
- [2026-10-28T22:27:01Z] `tech-lead` Olivia Lead:
  - Broken into tasks per ADR-1224 point 8 (2026-10-28), all Draft and unassigned; owner python-dev except TASK-1234 (tech-writer).
    - TASK-1227, the foundation plus show, list and status as the reference. It also removes the seeded-request code (ADR-1225 section 9), because nothing calls it and it sits in the files this task reshapes. 1 new case, 4 guards.
    - TASK-1228, item reads. Depends on 1227. 0 new cases.
    - TASK-1229, item writes. Depends on 1227 and 1228, because write responses reuse the read rows. 11 new cases.
    - TASK-1230, roster. Depends on 1227. 24 new cases.
    - TASK-1231, board, memory, workflow, overrides, reflog, check, sync and the package-data commands. Depends on 1227. 12 new cases.
    - TASK-1232, corpus-wide commands and squad creation, then deletion of get_service, the CLI gates and the JSON builders. Depends on 1228-1231. 8 new cases.
    - TASK-1233, the terminal UI on the Api, local mode. Depends on 1228, 1230 and 1231. 0 tests, guard extended, the operator checks it by eye.
    - TASK-1234, the stability guide and changelog (US3). Depends on 1232 and 1233.
    - Parallel after 1227: 1228, 1230, 1231 and TASK-1218. Then 1229 after 1228, then 1232 and 1233 side by side. Collisions are kept down by per-resource DTO and renderer modules, per-group sections in the op and binding tables, one-line pending-list rows, and no deletion of shared `_common.py` helpers before 1232.
    - `status --json` lands in 1227, not with the other item writes, because ADR-1224's own rule puts a flag with the move. Total new --json cases: 1 + 10 + 24 + 12 + 8 = 55, plus 1 usage-error refusal.
    - Every whole-document --json expectation of a moved command gains the display keys; review should check those test edits only add keys.
    - Open, each with a recommendation in its task: the roster comment route (1229), where the package-data DTOs are built (1231), and TUI test coverage (1233). @architect on the first two.
- [2026-10-28T22:28:35Z] `manager` Catherine Manager:
  - Dispatch 2026-10-28 (overnight drive delegated by op-pierre): TASK-1227 to python-dev; FEAT-1226 and US1-US4 InProgress with it. TASK-1228, 1230, 1232, 1233, 1234 Ready. TASK-1229 and 1231 stay Draft until the architect settles the tech lead's open points 1-3 (roster comment route, package-data DTOs, write ETag header).
- [2026-10-28T23:59:08Z] `manager` Catherine Manager:
  - Dispatch 2026-10-29: TASK-1228, 1230 and 1231 in parallel to three python-devs, each in its own git worktree, following TASK-1227's collision conventions. The daemon (TASK-1218) waits for the refactor, per op-pierre's order on MILE-1152.
- [2026-10-29T01:04:41Z] `manager` Catherine Manager:
  - 2026-10-29: TASK-1228, 1230 and 1231 integrated on release/0.18 (42ac2937, 9733ec0c, 98b14245; full suite 1607 passed). TASK-1229 dispatched (depends on 1228). Reviews of 1230 and 1231 start now; REV-1235 F13/F15 go back to the 1228 dev, F14 to the architect.
- [2026-10-29T06:57:37Z] `op-pierre` Pierre Chat:
  - 2026-10-29: tolerant view rendering. When a view tag in a body fails to render (e.g. a broken override template), the command still succeeds: the tag stays as written in display.body and a warning names the view and the error. sq check keeps reporting the broken template. Applies to show, role show and every surface that expands view tags, --json and the API included.
- [2026-10-29T07:10:53Z] `op-pierre` Pierre Chat:
  - 2026-10-29: the refactor does not close slower than 0.17.0 in local mode. Measured today: show/list/tree 20-30 % slower (e.g. task show 1088 -> 1304 ms median). Add a local-mode performance pass to this feature, with the criterion: 0.18 local is not slower than 0.17.0 on show, list and tree (median of 31 runs). The remote client budget stays with TASK-1219.
- [2026-10-29T07:12:29Z] `product-owner` Nina Product:
  - Added US6, local commands no slower than 0.17.0 (show, list, tree; median of 31 interleaved runs on the reference host; script under scripts/), per op-pierre 2026-10-29.
<!-- sq:discussion:end -->
