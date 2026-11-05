---
id: TASK-1315
sequence_id: 1315
type: task
title: Docs and changelog for board summaries and bodies
status: Done
parent: FEAT-1311
author: tech-lead
assignee: tech-writer
refs:
- ADR-1312:implements
description: Docs pages and the 0.20.0 CHANGELOG for ADR-1312
created_at: '2026-11-05T07:21:32Z'
updated_at: '2026-11-05T08:10:32Z'
---
<!-- sq:body -->
## Goal

The adopter docs and the 0.20.0 CHANGELOG section describe the board as ADR-1312 makes it: a
notice is a one-line summary over an optional body, `sq board list` prints numbered summaries,
`sq board show <n>` prints one notice, the startup text carries the summaries only, a multi-line
summary of a notice or a memory warns in `sq check` and at write time, and the 0.19 to 0.20
migration copies each notice's text into its summary. FEAT-1311 US5. Start after the Python
task's round 3 is committed, and describe what the build does: run each command you document
against a scratch squad (`uv run sq -C <scratch>`), never against this repository's squad.

## Pages and what changes

- `docs/workflow.md` (around lines 131-132): `board list --raw` prints `n. <summary> — <author>[,
  until …]` and the closing line naming `sq board show <n>`; no full text, no date. Add `board
  show <n>` beside `list` and `clear`, and the post form `sq board post "<summary>" [-m … | --file
  …]`.
- `docs/agents.md` (step 6 and the `## Board` bullet near line 63): the board section is the
  index of summaries; an agent reads a notice with `sq board show <n>`.
- `docs/roles.md` (around lines 514-532): the board line renders summaries, author and expiry,
  not each notice's full text.
- `docs/internals.md` (around line 378): same correction.
- `docs/stability.md`: the `board list --json` row shape (`summary`, no `body`), the new `board
  show --json` object, `board post`'s positional summary, and the operation list that names the
  board verbs (around lines 1079, 1143, 1176, 1353).
- `docs/overrides.md`: two rows in the always-on validator table beside `display_config_valid`
  (around line 1315), `notice_summary_single_line` and `memory_summary_single_line`, level `warn`,
  each with what it flags.
- `docs/faq.md` (around lines 271-290): check the exit-code rows still read true for `board
  list`; `board show` exits 1 on a number outside the listing.
- `docs/migration.md`, "Upgrading to 0.20: the schema step": the board step (every notice's text
  becomes its summary, the body is kept, nothing is renamed), the `sq check` warning it leaves on
  each multi-line notice, and the rewrite it asks for (post again with a one-line summary and the
  rest as the body, then clear the old number).
- `docs/recipes.md` "Search the board": check it still works with summaries in `list`.
- `CHANGELOG.md`, the `[0.20.0]` section: one entry for the summary-and-body board (the breaking
  change: `sq board post -m "<text>"` without a summary is refused, and `body` leaves `board list
  --json`), one for the two warnings, and the migration's board step in the schema paragraph.

The docs and the `sq-memory` skill (ST5 of the Python task) say the same thing about a one-line
summary and the warning; read the rendered skill (`uv run sq -C <scratch> skill sq-memory show
--raw --no-header`) and match it.

## Rules

Present tense, no history, no internal references (no item IDs, no repo process). One place
states each rule; other pages link to it. No status prose. Run the narration test of board
notices 13 and 14 on every sentence you add.

## Gates

`~/.local/bin/sq check` clean; the docs guards: `uv run --all-extras pytest -n 4 tests/meta`
(the bundled-docs registry and the documented-command checks). No commit.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1315 add-subtask "<title>"`; track with `sq task 1315 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T08:10:32Z] `tech-writer` Theo Writer:
  - Docs and CHANGELOG done for the summary-over-body board, checked against the dev build on scratch squads under ~/.cache/sq-docs-board. A 0.19 squad was made with the released tool and migrated with the dev build. Not committed.
    
    - The rule has one home, `docs/workflow.md` § "Memories and board notices: a summary over a body", and the other pages link to it. It covers post, list, show, clear, the `<n>` error, the write-time warning, the check rules and the rewrite. The `--raw` list paragraph shows the new index.
    - Also edited:
      - `agents.md` and `roles.md`: step 6 and the board bullets.
      - `internals.md`: the role skill line.
      - `stability.md`: the `board list` and `board show` JSON shapes, plus a Tier 2 "The board commands" subsection.
      - `overrides.md`: two always-on rows. The count is now fourteen; the old "eleven" was already one short.
      - `faq.md`: the exit-1 example.
      - `migration.md` 0.20: the step bullet, the sample output, and the rewrite procedure (run end to end).
      - README: the command line and the role skill sentence.
      - CHANGELOG 0.20: a migration bullet, a Changed entry (breaking) and an Added entry (warnings).
    - `recipes.md` "Search the board" covers `sq search` over items, not notices. It is unchanged.
    - For the architect or tech lead: `sq board list --raw` and `sq memory <role> list --raw` print the entries they read and exit 4 when a file is unreadable. ADR-1294 §1 says nothing reaches stdout unless the whole list was read. The docs and CHANGELOG now describe the build. @architect, please confirm or file a bug.
    - I placed `board show --json` with the frozen shapes, because the VS Code client consumes it. Move it to provisional if that is not intended.
    - A multi-line memory summary in `memory list --raw` prints its second line unindented, unlike the board. That breaks the bullet's markdown. Minor.
    - Gates: `tests/meta -n 4`: 748 passed. `sq check` clean.
<!-- sq:discussion:end -->
