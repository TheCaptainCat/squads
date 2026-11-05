---
id: TASK-1313
sequence_id: 1313
type: task
title: 'Board notices: summary and body, show, warnings, migration'
status: InProgress
parent: FEAT-1311
author: tech-lead
assignee: python-dev
refs:
- ADR-1312:implements
description: Python side of ADR-1312, in four dev rounds
subentities:
- local_id: ST1
  title: Stored summary over a body; post and list by summary
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST2
  title: board show and the BOARD_SHOW operation; --json shapes
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST3
  title: Multi-line summary warnings in sq check and at write time
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST4
  title: 0.19 to 0.20 step copies each notice body into its summary
  status: Done
  assignee: python-dev
  maps_to: US3
- local_id: ST5
  title: sq-memory skill board section; role skill board line
  status: Done
  assignee: python-dev
  maps_to: US4
- local_id: ST6
  title: Measure the board section before and after on a copy
  status: Done
  assignee: python-dev
  maps_to: US4
created_at: '2026-11-05T07:21:31Z'
updated_at: '2026-11-05T09:23:53Z'
---
<!-- sq:body -->
## Goal

Implement ADR-1312 in the Python code: a board notice stores a one-line `summary` over an
optional body; `sq board post "<summary>"`, `list` (summaries only), a new `show <n>` and the
`BOARD_SHOW` operation; the `--json` shapes; the two always-on `sq check` warnings and the
matching write-time warnings on `board post` and `memory add`; the 0.19 to 0.20 migration step
that copies each notice's body into its summary; the `sq-memory` skill's board section; and the
before/after measurement of the board section of the role skill. Docs and CHANGELOG are the
tech-writer task, the VS Code client the typescript-dev task.

Where FEAT-1311's story text and ADR-1312 disagree, ADR-1312 rules (see the architect's comment
on FEAT-1311): `board show` takes `--json` only, no `--raw`/`--no-header`; `board list --raw`
prints no `posted_at`.

## Rounds

One fresh python-dev per round. Each round leaves the fast gates green; the main loop runs the
full suite and commits a checkpoint before the next round. Brief each round with its subtask IDs
only, "stay out of the later subtasks", "no full suite, no commit", and "stop at a green point
and say where if context runs low".

| Round | Subtasks | Why this order |
|---|---|---|
| 1 | ST1, ST2 | The stored form, the DTOs and the three verbs share every file (`_board/`, `_api/_dto/_board.py`, `_cli/_board.py`, `_cli/_render/_board.py`); splitting them across developers collides |
| 2 | ST3 | The warnings read the stored `summary` ST1 introduces; memory gets the same rule |
| 3 | ST4, ST5 | The migration writes the ST1 format and its manual names the ST3 remedy; the `sq-memory` text describes the finished verbs |
| 4 | ST6 | Measures the finished build; no product code |

## Fast gates (every round)

`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff
format --check .`, then the tests the change touches, selected per board notice 15 (grep the
changed DTO fields, constants, template paths and command names across `tests/`), plus the floor
`tests/meta tests/cli` for any change under `_cli/`, `_api/` or `_rendering/templates/`, on both
test squads: `uv run --all-extras pytest -n 4 <paths>` and again with `--squad override`. No full
suite, no commit: the main loop owns both. `~/.local/bin/sq check` stays clean. No `sq remove`,
no `sq migrate up` or `sq sync` on this repository's squad.

## Tests

CLI surface tests per ADR-1172 (`@pytest.mark.covers`, `@pytest.mark.breaches` in
`tests/check/`), in the module of the command they declare (`tests/cli/test_board.py`,
`tests/cli/test_memory.py`, `tests/cli/test_migrate.py`), one case per behaviour plus its
boundary refusals, no tables or cross products, passing on the bundled and the override squad.
Expected new tests: about 17 (ST1 4, ST2 4, ST3 5, ST4 3, ST5 0 to 1). Existing board tests that
post with `-m` as the notice text are rewritten in place, not duplicated. Break each new test
once by hand (revert the line it guards, watch it go red) and say so in the handback (board
notice 4).

## Generated and frozen files to regenerate

- `src/squads/_rendering/templates_manifest.json` and `content_store.json`: `python
  scripts/gen_template_manifest.py` after ST5 edits `views/memory_skill.md.j2` (the version is
  already 0.20.0, so only the 0.20.0 entry moves). Guard:
  `tests/meta/test_override_manifest_and_stamp_freshness.py`;
  `python scripts/gen_template_manifest.py --check` must exit 0.
- `tests/cli/_bundled_documents.py`: the frozen `sq migrate help --json` document, whose 0.20.0
  `summary` and `manual` ST4 changes.
- `tests/meta/test_package_import_edges_match_the_recorded_table.py`: a row for any new
  package-to-package edge (ST3 if `_services/_validators.py` reads through `_board`/`_memory`).
- The operation table in `src/squads/_api/_ops.py` (`_GROUPS`, `_ORDER`, the `__all__`-style
  name list) gains `BOARD_SHOW` (ST2); `tests/meta/test_the_operation_table_lists_every_operation_its_groups_define.py`
  holds it.
- This repository's own `squads/board/`, `CLAUDE.md` and `.claude/` change only when the main
  loop migrates this squad with the finished build (board notice 17); no round touches them.

## Not in scope

An edit verb for notices or memories (ADR-1312, rejected alternatives). The memory file format
and `sq memory` JSON. Docs, CHANGELOG, the VS Code client. Rewriting this repository's live
notices (ST6 drafts the summaries on a copy only).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1313 add-subtask "<title>"`; track with `sq task 1313 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Stored summary over a body; post and list by summary

<!-- sq:subtask:ST1:body -->
Implements ADR-1312 §1, §2 (post, list), §4. Story US1. Round 1, with ST2.

## Behaviour

- A notice file is `squads/board/<id>.md` with frontmatter `summary`, `author`, `posted_at`,
  optional `until`, in that order, over an optional body stored as written. No `id` key.
- `sq board post "<summary>" [-m … | --file …] [--until <date>] --as <slug>`: the positional
  `summary` is required and non-empty after stripping; `-m` (repeatable, one paragraph each) or
  `--file` (`-` reads stdin) gives the body; `-m` with `--file` is refused as today. A post with
  neither stores an empty body; the summary is never copied into it. `post -m "<text>"` with no
  summary is refused by the argument parser (usage error, exit 2).
- A new id is the short hash of author, `posted_at`, summary and body. Existing ids are never
  recomputed.
- `sq board list --raw` prints `n. <summary> — <author>[, until <until>]` per notice, then a
  blank line and `Read a notice in full with \`sq board show <n>\`.` when at least one notice is
  listed; an empty board prints `no current notices`. A multi-line summary prints its first line
  on the item and each further line indented three spaces, with ` — <author>…` appended to the
  last line. No `posted_at`, no body, no ANSI, no wrapping, nothing on stdout unless the whole
  list was read (ADR-1294 §1).
- `sq board list` (styled) prints one line per notice: number, summary, author, expiry. No body.
- Numbering is unchanged: the position in the live listing (unexpired, sorted by `posted_at` then
  id); `clear <n>` resolves against it.
- A multi-line summary is accepted and stored as given here; its warning is ST3.

## Files

- `src/squads/_board/_model.py`: `BoardNotice.summary`; `to_frontmatter_dict` writes the §1
  order; `from_frontmatter` reads `summary` (missing reads as `""`, which only a 0.19 file not yet
  migrated can hold).
- `src/squads/_board/_store.py`: `post(author, summary, body, *, until)`; `_hash_id` over the four
  inputs; a `show(n)` resolver that `clear` shares (same out-of-range `SquadsError`), so `show`
  and `clear` cannot disagree on numbering.
- `src/squads/_services/_board.py`: `board_post` signature; `board_show(n)` for ST2.
- `src/squads/_api/_dto/_board.py`: `BoardPostRequest {summary, body: str | None, until}`;
  `NoticeRow` drops `body`, gains `summary`; `Notice` gains `summary`. Re-export through
  `_api/_dto/__init__.py` and `_api/__init__.py` per the privacy convention.
- `src/squads/_services/_squad_ops.py`: `list_board` rows and `_notice` carry `summary`;
  `post_to_board` passes summary and body.
- `src/squads/_cli/_board.py`: `post` takes the positional summary, `resolve_body_optional` for
  the body; the module docstring's grammar.
- `src/squads/_cli/_render/_board.py`: `_raw_notice` and `render_notices` per the behaviour above;
  `e()` on every dynamic string.
- `src/squads/_tui/_board.py`: `_notice_block` shows the summary as the notice's heading line; the
  body arrives with ST2.
- `tests/daemon/test_the_error_table.py`, `tests/daemon/test_a_get_never_mutates.py`,
  `tests/cli/test_init.py`, `tests/meta/test_a_covers_marker_is_checked_against_the_pairs_a_call_reaches.py`:
  their `board post` calls and request bodies move to `summary`.

## Tests (`tests/cli/test_board.py`, about 4 new)

- `post "<summary>"` alone: the `--json` row holds the summary, and `show` (ST2) later reads an
  empty body. Covers `("board post", "summary")`.
- `post` with no summary: usage error, nothing posted. `post "   "`: exit 1, one-line error,
  nothing posted.
- `list --raw` with one notice that has `--until` and one without: the two items and the closing
  line, byte for byte; the existing empty-board case keeps `no current notices` and gains no
  closing line.
- `list --raw` with a multi-line summary: continuation lines indented three spaces, author on
  the last.
- Rewritten in place: the `-m`, repeated `-m`, `--file`, `-m`+`--file`, `--until`, styled `list`
  and `clear` cases post with a summary; `test_post_needs_a_message_or_a_file` becomes the
  no-summary refusal.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — board show and the BOARD_SHOW operation; --json shapes

<!-- sq:subtask:ST2:body -->
Implements ADR-1312 §2 (show), §3. Story US1. Round 1, after ST1.

## Behaviour

- `sq board show <n> [--json]` prints notice n in full: a header (summary, author, posted,
  until when set) and the body. No `--raw`, no `--no-header`.
- `show` with a number outside the live listing exits 1, nothing on stdout, sq's one-line error
  on stderr; a non-integer `<n>` is a usage error.
- `--json` shapes: `board list` an array of `{n, id, summary, author, posted_at, until}` (no
  `body`); `board show <n>` one object `{n, id, summary, author, posted_at, until, body}`, `body`
  is `""` when the notice has none; `board post` and `board clear` keep their envelope, the
  `entry` object gains `summary` beside `body`.
- `BOARD_SHOW` is a read (`GET /v1/board/{n}`, request `BoardShowRequest {n}`), served by the
  daemon like the other board operations, so `show` works the same in local and remote mode.
- The `sq ui` board screen keeps showing each notice in full: it lists through `BOARD_LIST`, then
  reads each row's body through `BOARD_SHOW` and skips (with the existing partial note) a row
  whose returned `id` differs from the listed one, which means the board changed in between.

## Files

- `src/squads/_api/_dto/_board.py`: `BoardShowRequest {n: int}`; a `NoticeDetail` (or `Notice`
  with `n`) carrying `n` plus every `Notice` field; re-exports.
- `src/squads/_api/_ops_board.py`: `BOARD_SHOW = Operation("board.show", "GET", "/v1/board/{n}",
  BoardShowRequest, NoticeDetail)`.
- `src/squads/_api/_ops.py`: `BOARD_SHOW` in the name list, `_GROUPS` (`board`) and `_ORDER`
  (route priority: beside `BOARD_CLEAR`).
- `src/squads/_services/_squad_ops.py`: `show_board_notice(req)`; `src/squads/_services/_bindings.py`:
  `bind(ops.BOARD_SHOW, Service.show_board_notice)`.
- `src/squads/_cli/_board.py`: the `show` command, `--json` printing the object.
- `src/squads/_cli/_render/_board.py`: `render_notice` for the text form.
- `src/squads/_tui/_board.py`: as above.
- `tests/daemon/test_a_get_never_mutates.py`: `seed` posts a notice with a summary and gives `n`
  the value `1`, so the GET sweep reaches `BOARD_SHOW`.

## Tests (`tests/cli/test_board.py`, about 4 new)

- `show <n>` text: header lines and body of a notice posted with `--until` and a body.
- `show <n> --json`: the whole object of a notice posted without a body, `body == ""`.
- `show` one past the end of the listing: exit 1, empty stdout, the error line.
- `show abc`: usage error.
- Rewritten in place: `list --json` (no `body`, has `summary`), `post --json` and `clear --json`
  (`entry.summary`).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Multi-line summary warnings in sq check and at write time

<!-- sq:subtask:ST3:body -->
Implements ADR-1312 §2 (write-time warnings) and §5. Story US2. Round 2.

## Behaviour

- A summary holds a line break when `len(summary.splitlines()) > 1`, the separators
  `str.splitlines` splits on, as `title_single_line` reads a title. No length rule.
- `notice_summary_single_line`: for each live (unexpired) notice whose summary holds a line
  break, one warning naming the notice by number and id, with the remedy: `sq board post
  "<summary>" --file <body> --as <author>` (with `--until <until>` when it has one), then `sq
  board clear <n>`; the new post lists after every existing notice, so `<n>` still names the old
  one. An expired notice is not checked.
- `memory_summary_single_line`: for each memory, in every folder under `agents/memory/` (roles,
  retired roles and operators), whose summary holds a line break, one warning naming
  `<role>/<slug>`, with the remedy: `sq memory <role> forget <slug>`, then `sq memory <role> add
  "<summary>" --file <body> --slug <slug>`.
- Both are squad-global, always on, default level `warn`: a `[squad] validators` entry cannot
  name them or change their level. A file neither store can read is skipped by the rule (`board
  list` and `memory list` keep reporting it).
- `sq board post` and `sq memory <role> add` with a multi-line summary write the entry and answer
  with one warning in the response's `warnings`, the same message as the rule, printed by
  `calls.print_warnings` (stderr) and carried in `--json`. Neither refuses.

## Files

- `src/squads/_workflow/_validator_names.py`: both names in `SQUAD_GLOBAL_VALIDATOR_NAMES`,
  `ALWAYS_ON_SQUAD_GLOBAL_NAMES` and `DEFAULT_SQUAD_GLOBAL_LEVEL` (`warn`).
- `src/squads/_services/_validators.py`: the two validators in `SQUAD_GLOBAL_CATALOG`. They are
  synchronous and get `ctx.paths` and `ctx.now`; read the files with the stores' own parse
  (`BoardNotice.from_frontmatter`, `MemoryEntry.from_frontmatter` over `split_frontmatter`) and
  the same expiry test the board listing uses, rather than a second parser. One message builder
  per rule, shared with the write-time warning, lives beside the store it describes
  (`_board/`, `_memory/`) so the service and the validator cannot drift.
- `src/squads/_services/_squad_ops.py`: `post_to_board` and `add_memory` add the warning to the
  `Response`.
- `tests/meta/test_package_import_edges_match_the_recorded_table.py`: a row per new edge.

## Tests (about 5 new)

- `tests/check/` (a new `test_notebook_rules.py`, or the closest existing module): one breach
  test per rule, `@pytest.mark.breaches("notice_summary_single_line")` and
  `@pytest.mark.breaches("memory_summary_single_line")`, asserting the level, the subject (number
  and id; `<role>/<slug>`) and the remedy text; arrange the multi-line summary by writing the file
  the way the migration leaves it.
- `tests/check/`: an expired notice with a multi-line summary raises nothing.
- `tests/cli/test_board.py`: `post` with a multi-line summary exits 0, stores it, prints the
  warning on stderr.
- `tests/cli/test_memory.py`: `memory <role> add` with a multi-line summary, same.
- The clean side (one-line summaries raise nothing) is held by `tests/check/test_baseline.py`'s
  clean squad; post a notice and add a memory there if its squad holds none.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — 0.19 to 0.20 step copies each notice body into its summary

<!-- sq:subtask:ST4:body -->
Implements ADR-1312 §6 with op-pierre's acceptance ruling (copy, don't move). Story US3.
Round 3, with ST5.

## Behaviour

- A step of `migrate()` in the 0.19 to 0.20 runner, after the refusal pre-scan (`_scan` and
  `_refusal`), so a refused run still writes nothing. It walks every `squads/board/*.md`,
  expired notices included.
- Frontmatter already holds `summary`: the file is untouched. A second run changes no file.
- Otherwise the stripped body is **copied** into `summary` and the body is kept exactly as it is.
  `author`, `posted_at`, `until` and any other key are written back unchanged, in the order
  `summary`, `author`, `posted_at`, `until`, then other keys. The filename stays, so the id and
  the listing position stay. The write is atomic (`_aio.atomic_write_text`).
- A file that does not read or parse is left untouched and named in the run's outcome (one
  report line with its squad-relative path and the read error); the step refuses nothing.
- Memories are not touched.
- The outcome's report gains one line per notice summarised (`summarised notice <id>`), counted in
  `MigrationOutcome.count`.
- `SUMMARY` names the board step; `MANUAL` gains a step: every migrated notice now lists its whole
  text as its summary, `sq check` warns on each multi-line one, and the remedy is ST3's (post
  again with a one-line summary and the rest as the body, then clear the old number).

## Files

- `src/squads/_migrations/_v0_19_to_v0_20.py`: the step, `SUMMARY`, `MANUAL`, the module
  docstring.
- `tests/fixtures/corpus/v0_19/`: a `board/` folder (beside the item folders) holding a
  one-line notice with `until`, a multi-line notice without, an expired notice, a notice that
  already has `summary`, and one file that does not parse. Update the existing `test_migrate.py`
  expectations this fixture change moves (report lines, counts), not their intent.
- `tests/cli/_bundled_documents.py`: the 0.20.0 `summary` and `manual` in the frozen `sq migrate
  help --json` document.

## Tests (`tests/cli/test_migrate.py`, about 3 new)

- `up` on the 0.19 fixture: each plain notice's `summary` equals its stripped body, the body is
  byte-identical, `author`/`posted_at`/`until` and the filename unchanged, expired one included;
  key order as above.
- `up` leaves the notice that already has `summary` byte-identical and names the unreadable file
  in its outcome while completing (exit 0, schema stamped).
- After `up`, `sq board list --json`, `sq board show 1 --json` and `sq board clear 1` work on the
  migrated board, and `sq check` warns `notice_summary_single_line` on the multi-line notice only.
- The existing `test_up_run_again_changes_no_file` covers the second run once the fixture holds a
  board; confirm it reaches the board files.
- `sq repair` does not read the board (it is outside the index); no test for it.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — sq-memory skill board section; role skill board line

<!-- sq:subtask:ST5:body -->
Implements ADR-1312 §4 (startup text) on the skill side. Story US4. Round 3, with ST4.

## Behaviour

- The role skill's board line (ADR-1294 §2 item 3) keeps the command `sq board list --raw` and
  its failure text; `_backends/_claude_code/_pointer_lines.py` does not change. Its output is the
  ST1 index. Confirm with `tests/cli/test_sync.py`'s role-skill pointer assertion that nothing
  moved.
- `sq-greeting` step 6 (`templates/startup_steps.md.j2`) keeps its text (ADR-1312 §4).
- The `sq-memory` skill's board section documents: `sq board post "<summary>" [-m … | --file …]
  --as <slug> [--until <date>]`, `sq board list` (numbered summaries), `sq board show <n>` (one
  notice in full), `sq board clear <n>`; that `<n>` is the position in the latest `list`, not a
  stored id; that a summary is one line and the detail goes in the body; and that a multi-line
  summary, of a notice or a memory, is accepted with a warning and flagged by `sq check`. The
  memory section says the same about a memory's summary. Present tense, no history.

## Files

- `src/squads/_rendering/templates/views/memory_skill.md.j2`: the board section and the
  one-line-summary rule.
- `src/squads/_rendering/templates_manifest.json`, `content_store.json`: regenerate with `python
  scripts/gen_template_manifest.py`.

## Tests (0 to 1 new)

- If a `tests/cli` case reads the `sq-memory` skill's text (`sq skill sq-memory show --raw
  --no-header`), update it; otherwise add one in `tests/cli/test_skill.py` asserting the board
  section names `sq board show <n>` and the post form with a summary.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Measure the board section before and after on a copy

<!-- sq:subtask:ST6:body -->
Implements FEAT-1311's acceptance on size. Story US4. Round 4. A measurement on a copy of
this repository's squad, not product code.

## Builds

- **Before**: commit `5f4669f7` (the head when this task was drafted, before any FEAT-1311 code),
  from a `git worktree` with that commit's own `uv run sq`.
- **After**: the commit that closes round 3, same method.

## Method

- Copy only `.squads.toml` and `squads/` into a scratch directory under
  `/home/pchat/.cache/sq-adr1290/board-measure/` (not `/tmp`), once per build, and run that
  build's `sq migrate up` on the copy. Every `sq` call takes `-C <copy>`. Never run either build on the repository's squad.
- For every live role on the copy: the board section is the output of `sq board list --raw`; the
  whole skill is the rendered `sq-role-<slug>` pointer with each `!` line replaced by its
  command's output, as Claude Code delivers it. Count characters (`len` of the decoded text).
- Three columns: before; after migration (notices carry their whole text as the summary); after
  rewriting every live notice on the copy with a one-line summary and the rest as its body,
  through `sq board post "<summary>" --file <body> --as <author> [--until …]` then `sq board
  clear <n>`, the ST3 remedy. Draft each summary from the notice's own first sentence; keep the
  drafts in `board-measure/summaries.tsv` (id, author, summary) so the real rewrite can start from
  them.
- `sq check` on the rewritten copy: no `notice_summary_single_line` warning.

## Output

One comment on FEAT-1311: the table (board section and whole skill, per role or as one row when
equal across roles, three columns), the two SHAs, the path of the script and of
`summaries.tsv`, and the `sq check` result. No product file changes.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T07:31:17Z] `python-dev` Elias Python:
  - Round 1 (ST1, ST2) done, both Done. Not committed.
    
    - Stored form: summary, author, posted_at, until over an optional body. The id hash covers author, posted_at, summary and body. A post with no body stores an empty one.
    - `board post "<summary>" [-m | --file]`: a blank summary exits 1 with a one-line error; a missing summary is a usage error (exit 2).
    - `board list`: `--raw` and styled show summaries only. `--raw` ends with the `sq board show <n>` line; an empty board prints `no current notices` alone.
    - `board show <n> [--json]` uses the new BOARD_SHOW (GET /v1/board/{n}). The store's `show(n)` is shared with `clear`.
    - `sq ui` board screen: lists through BOARD_LIST, reads each body through BOARD_SHOW, and counts a row as skipped when its id differs or the number is out of range. No test covers it; it passes pyright and ruff only.
    - Test changes: tests/cli/test_board.py rewritten in place (+8 cases). The daemon error-table and GET-sweep tests, test_init and the covers-marker meta test were updated.
    - Gates: pyright, ruff check and ruff format are clean. tests/tui does not exist, so I left it out of the command.
      - bundled: `2285 passed, 4 skipped`
      - override: `1992 passed, 171 skipped`
      - logs in /home/pchat/.cache/sq-loop/r1-*.log
    - Each new test was broken once by hand and went red. `sq check` is clean.
- [2026-11-05T07:42:59Z] `python-dev` Elias Python:
  - Round 2 (ST3) done, ST3 Done. Not committed.
    
    - Rules `notice_summary_single_line` and `memory_summary_single_line`: squad-global, always on, warn, line break only.
    - `board post` and `memory add` store a multi-line summary and answer with one warning, the same text as the rule. Neither refuses.
    - Tests: 3 breach tests in tests/check/test_notebook_rules.py, plus one write-time case each in tests/cli/test_board.py and tests/cli/test_memory.py. All three rules/commands were mutated once and went red.
    - Gates: pyright, ruff check and ruff format clean. Bundled `2290 passed, 4 skipped`; override `1997 passed, 171 skipped`. `sq check` clean.
- [2026-11-05T08:00:59Z] `python-dev` Elias Python:
  - Round 3 (ST4, ST5) done, both Done. Not committed.
    
    - ST4: the 0.19 to 0.20 runner now copies each notice's stripped body into `summary` after the refusal pre-scan, keeping body, file name and other keys. Key order is summary, author, posted_at, until, then others; the write is atomic. A notice with `summary` is untouched. An unreadable file is left as it was and named in the report. Memories are untouched. SUMMARY and MANUAL (step 9) updated; `tests/cli/_bundled_documents.py` regenerated; `tests/fixtures/corpus/v0_19/board/` added (5 files).
    - ST5: the `sq-memory` skill's board and memory sections describe `post "<summary>"`, `list`, `show <n>`, one-line summaries and the multi-line warning. Manifest and content store regenerated, and the store rebuilt with `seed_content_store.py --rebuild` to drop the one orphan blob this left.
    - Dry run on a copy of this repo's squad under ~/.cache: 6 of its 22 live notices would warn after the migration (24 files, 0 memory warnings).
    - Tests: 3 new in tests/cli/test_migrate.py, 1 in tests/cli/test_skill.py; the clean-0.19 test now sets the board folder aside. Each was broken once by hand. Gates green on both squads; `sq check` clean.
- [2026-11-05T08:24:41Z] `python-dev` Elias Python:
  - @reviewer REV-1316 F1 to F8 are fixed, uncommitted; the findings are marked Fixed.
    
    - F1: `board list --raw` and `memory list --raw` print nothing on stdout when a file cannot be read, and keep exit 4 with the stderr line. The one docs line in workflow.md now says so. One case per command.
    - F2: `memory list --raw` indents a multi-line summary's further lines under its bullet. One case.
    - F3, F7: the migration tests compare whole files, whole report lines, the whole config and the whole check issue as plain text, with no parser import. The slice assertion and the missing exit code in the board tests are restored, and the skill test compares the whole board section.
    - F4: the migration leaves a file with no frontmatter mapping, with no frontmatter, or with an empty body as it is, and names it. One case.
    - F5: a `sq ui` board test under `run_test()` in tests/cli/test_docs_ui.py asserts the whole board markdown. Summary lines are escaped and bolded one by one, so a blank line or an empty summary no longer breaks the bold. The skipped note now reads "could not be shown".
    - F6: one `has_line_break` in `_util` now serves titles and summaries. A board post case pins CR and U+2028.
    - F8: `board post` stores the body with only the surrounding blank lines removed. One case.
    
    Gates are green on both squads. Each new or changed test was broken once by hand and went red.
- [2026-11-05T08:52:24Z] `python-dev` Elias Python:
  - `--full` and `author_name` are in, uncommitted. Gates are green on both squads. Each new test was broken once by hand and went red.
    
    **`--full`** on `sq board list` and `sq memory <role> list` (`full: bool = false` on `BoardListRequest` and `MemoryListRequest`). Without it nothing changes.
    - `--json`: a `body` key per row, absent without `--full` (`exclude_if` on the DTO field).
    - Text: the body under its summary, a blank line first, each line indented three spaces (board) or two (memory).
    - `--raw`: the body inside the item, indented the same way. With `--full` the board's closing "Read a notice in full" line is dropped.
    
    **`author_name`**: the full name from the roster (the participant's title), or the slug when the author is not on the roster. It sits right after `author` on the list rows, the `show` object and the `entry` of post and clear. Memory rows are unchanged apart from `body`.
    
    **Shapes**
    - `board list --json`: `{"n","id","summary","author","author_name","posted_at","until"}`
    - `board list --full --json`: the same plus `"body"` last
    - `board show <n> --json`: `{"n","id","summary","author","author_name","posted_at","until","body"}`
    - `board post --json` and `board clear --json`: `{"entry": {"id","summary","author","author_name","posted_at","until","body"}}`
    - `memory list --json`: `{"slug","filename","description","created_at"}`; with `--full` the same plus `"body"` last
- [2026-11-05T09:23:53Z] `python-dev` Elias Python:
  - @reviewer REV-1316 F9 and F11 are fixed, uncommitted, and marked Fixed.
    
    - F9: the board's raw list indents a multi-line summary's further lines and a `--full` body by the width of the item's own marker (`len("10. ")` is 4). Two whole-output cases with eleven notices: plain `--raw` with a two-line summary at position 10, and `--full --raw` with bodies at 9, 10 and 11. Memory bullets are always `- `, so the two-space indent is correct there and no memory change was needed.
    - F11: the memory `--full` and `--full --raw` assertions are now two cases; the raw one declares `covers("memory list", "--full", "--raw")`.
    
    Gates are green on both squads, and each new test was broken once by hand and went red.
<!-- sq:discussion:end -->
