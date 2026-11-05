---
id: FEAT-1311
sequence_id: 1311
type: feature
title: Board notices with a summary and a body
status: Ready
author: product-owner
refs:
- MILE-1269:targets
- FEAT-1290
description: A board notice gets a one-line summary and a body; list shows summaries,
  show reads the body
subentities:
- local_id: US1
  title: Post, list and show a notice by summary and body
  status: Todo
- local_id: US2
  title: Warn on a multi-line summary
  status: Todo
- local_id: US3
  title: Migrate existing notices
  status: Todo
- local_id: US4
  title: Startup text carries the board index
  status: Todo
- local_id: US5
  title: Docs describe summary and body
  status: Todo
created_at: '2026-11-05T07:05:50Z'
updated_at: '2026-11-05T08:06:42Z'
---
<!-- sq:body -->
## Outcome

A board notice has a one-line summary and a full body, as a memory already does. `sq board list` prints numbered summaries and `sq board show <n>` prints one notice in full. The board stops rendering every notice in full into each agent's startup text. A summary that spans several lines raises an `sq check` warning, for notices and for memories alike. A 0.19 squad migrates with its notices intact.

## Why

The board is 15k characters on this repository and `sq board list --raw` renders all of it into every subagent's `sq-role-<slug>` skill, so each spawn pays for notices most runs do not need. A memory already separates a summary from a body, and the role skill shows only the summaries. The board should read the same way: the index at startup, the body on demand. Pierre ruled on 2026-11-05 that both kinds have a one-line summary and a full body, that `list` shows summaries only, and that a multi-line summary is a warning.

## Scope

- Board notice: a summary line and a body; `post`, `list`, a new `show`, and the `--json` shapes.
- `sq check`: a warning for a multi-line summary on a notice or a memory.
- The 0.19 to 0.20 migration of existing notices.
- The role skill's board line, the `sq-memory` skill's board section, the `docs/` pages, and the VS Code client that reads `sq board list --json`.

## Acceptance

- Every user-visible behaviour below is exercised by a test through the CLI.
- The board section of a rendered `sq-role-<slug>` skill is a fraction of its size before the change; the before and after sizes on this repository's board are recorded in the feature discussion.
- `sq check` is clean on a squad whose notices and memories all have one-line summaries.
- A multi-line summary warns and is never refused.
- The decision on the stored form of a notice (see the first story) is recorded before the board format changes.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1311 add-story "As a <role>, I want … so that …"`; track with `sq feature 1311 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Post, list and show a notice by summary and body

<!-- sq:story:US1:body -->
As an agent posting to the board, I give a one-line summary and optionally a body, and I read a notice in full only when I ask for it. The stored form and the commands are fixed by ADR-1312.

- `sq board post "<summary>" [-m … | --file …] --as <slug> [--until <date>]`: the positional argument is the summary, required and non-empty; the optional body comes from `-m` or `--file`. A post with no body is valid, and `post -m "<text>"` without a summary is refused by the argument parser.
- A summary with a line break in it is accepted and stored; `post` answers with one warning saying to keep the summary to one line and put the rest in the body (`--file`).
- `sq board list` prints one numbered line per live notice: summary, author and expiry. It prints no bodies. `--raw` carries no ANSI and no wrapping, as today.
- `sq board show <n> [--json]` prints notice n: a header (summary, author, posted date, expiry) and the body. It takes `--json` only; it has no `--raw` and no `--no-header`. A number outside the listing exits 1 with nothing on stdout.
- `sq board clear <n>` keeps its meaning against the numbering of `list`.
- `--json`: `list` is an array of objects with `n`, `id`, `summary`, `author`, `posted_at`, `until`; `show` is one object with those keys plus `body` (`""` when the notice has none). The old `body` key is gone from `list`.
- A notice stores `summary` in its frontmatter over an optional body, as a memory does (ADR-1312).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Warn on a multi-line summary

<!-- sq:story:US2:body -->
As a maintainer, I am warned when a summary spans several lines, so the one-line index stays readable.

- `sq check` raises a warning for a live board notice (rule `notice_summary_single_line`) or a memory (rule `memory_summary_single_line`) whose summary contains a line break. Both rules are always on, at level `warn`. The warning names the notice by number and id, or the memory by `<role>/<slug>`, and gives the command that fixes it.
- The warning clears once the summary is one line; a notice or memory with a one-line summary raises nothing. An expired notice is not checked.
- `sq memory <role> add "<summary>"` with a multi-line summary is accepted and answers with the same warning as `board post`; the state stays valid, as the migration produces it.
- There is no length cap: the rule is only that a summary spans several lines.
- Each rule has a breach test in `tests/check/` declared with `@pytest.mark.breaches(...)`.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Migrate existing notices

<!-- sq:story:US3:body -->
As an adopter on 0.19, I run `sq migrate up` and keep every notice, with a clear signal about what to tidy.

- The unreleased 0.19 to 0.20 runner copies each existing notice's body into its summary and keeps the body as it is. A notice that already has a `summary` is left untouched.
- Because a copied summary spans several lines, `sq check` warns on each such notice afterwards; the `manual` step of the release says so and tells the adopter to rewrite them with `sq board post` and `sq board clear` (ADR-1312 gives the remedy).
- The migration changes no notice's file name (so its id and place in the listing), author, posted date or expiry. A file that does not read or parse is left untouched and named in the run's outcome; the step refuses nothing.
- A second run is a no-op; `sq repair` rebuilds the same board.
- A one-line notice now shows its text as summary and again as body in `show`.
- The migrated squad lists, shows and clears notices with the new commands.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Startup text carries the board index

<!-- sq:story:US4:body -->
As an agent starting a run, I get the board as a short index, so the startup text is small and I know which notice to open.

- `sq board list --raw`, which the `sq-role-<slug>` skill and `sq-greeting` render, prints `n. <summary> — <author>[, until <date>]` for each notice, no `posted_at`, no body, and a closing line naming `sq board show <n>`. An empty board prints `no current notices`.
- The rendered `sq-role-<slug>` skill on this repository is measured before and after, board section and whole skill, in characters; both figures are posted in the feature discussion.
- The `sq-memory` skill's board section documents `post "<summary>"` with a body, `list`, `show <n>` and `clear <n>`, and states that the number comes from the latest `list`.
- The startup commands fall back to their one-line message when the board cannot be read, as today.
- The VS Code client reads the new `sq board list --json` shape and opens a notice's body through `sq board show <n> --json`; its board view shows summaries and loads a body on demand.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Docs describe summary and body

<!-- sq:story:US5:body -->
As an adopter reading the docs, I find the summary-and-body model for the board and the new warning described once and correctly.

- `docs/workflow.md`, `docs/agents.md` and `docs/roles.md` describe `board list` as numbered summaries, `board show <n>`, and the startup text carrying summaries only.
- The docs and the `sq-memory` skill say the same thing about a one-line summary and a multi-line warning for memories and notices.
- `docs/migration.md` or the release changelog explains the migration's effect and the rewrite it asks of the adopter.
- The pages describe the tool as it is, with no history and no internal references.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T07:11:11Z] `architect` Robert Architect:
  - - ADR-1312 (Proposed, for @op-pierre) records the stored form: `summary` in the notice's frontmatter over an optional body, as a memory has. It is a new ADR because it also fixes commands, JSON, check rules and the migration; ADR-314 (board format) and ADR-1294 §1/§2 (raw list) are narrowed in place with dated notes.
    - @product-owner corrections to the stories, beyond warn-not-refuse: `sq memory <role> show` has no `--raw`/`--no-header`, so `board show <n>` takes `--json` only (US1). The `sq check` rules are `notice_summary_single_line` and `memory_summary_single_line`, always-on squad-global, level warn, line break only, no length rule (US2). `board list --raw` prints `n. <summary> — <author>[, until …]` plus one closing line naming `sq board show <n>`; no posted_at (US4). `post` and `memory add` write a multi-line summary and answer with the same warning.
    - @tech-lead the migration step leaves a notice that already has `summary` untouched, keeps the filename (id), author, posted_at and until, and skips an unreadable file without refusing. This repo's squad then warns on every migrated notice, so whoever migrates it rewrites the notices in the same change to keep `sq check` clean.
- [2026-11-05T07:22:02Z] `tech-lead` Olivia Lead:
  - Broken down against ADR-1312 (with op-pierre's copy-not-move ruling). Three tasks, all Draft:
    
    - TASK-1313 (python-dev), four rounds: R1 ST1+ST2 (stored `summary`, `post "<summary>"`, `list` by summary, `show <n>` and `BOARD_SHOW`, the `--json` shapes, the `sq ui` board screen); R2 ST3 (`notice_summary_single_line`, `memory_summary_single_line`, write-time warnings); R3 ST4+ST5 (migration step, `sq-memory` text, manifest); R4 ST6 (before/after measurement on a migrated copy, before = `5f4669f7`). About 17 new CLI/check tests, on both test squads.
    - TASK-1314 (typescript-dev), after R1 is committed: board panel shows summaries, loads a body through `sq board show <n> --json` with an id check, canary covers both commands.
    - TASK-1315 (tech-writer), after R3: docs pages and the 0.20.0 CHANGELOG.
    
    Gaps for the record:
    
    - FEAT-1311 US1/US2/US4 still say `board show --raw/--no-header`; the tasks follow ADR-1312 (`--json` only). @product-owner the story text needs the architect's corrections.
    - The `sq ui` board screen reads `NoticeRow.body`, which neither the ADR nor the feature names. TASK-1313 ST2 keeps it showing full notices by reading each body through `BOARD_SHOW`.
    - `show <n>` is positional, so a client can get a different notice if the board changes between `list` and `show`. ADR-1312 doesn't cover this. The VS Code task compares the returned `id` and re-lists on a mismatch.
    - Rewriting this repository's live notices after the migration has no owner in FEAT-1311. ST6 drafts one-line summaries on a copy only (`summaries.tsv`). The real rewrite needs the authors' wording, op-pierre's notices included, when this squad migrates.
    - The ADR's notice remedy uses `post --as <author>`, which fails when the author is no longer on the live roster.
    - A migrated one-line notice stores its text twice (summary and body), so `show` prints it twice. This follows the ruling; noting it only.
    
    @manager ready for promotion and round 1 dispatch.
- [2026-11-05T08:06:09Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-05): when this squad's notices are rewritten after the migration, the ones that do not warn (one-line notices whose summary and body are now the same text) keep their line as the summary and gain a longer body that makes them clearer.
- [2026-11-05T08:06:42Z] `python-dev` Elias Python:
  - Board section size, before and after (characters, `len` of the decoded text, 22 live notices).
    
    | Role skill (python-dev) | Before (5f4669f7) | After, migrated (HEAD f9cc8727, whole body as summary) | After, drafted one-line summaries |
    |---|---|---|---|
    | Board section (`sq board list --raw` output) | 15,224 | 14,723 | 2,904 |
    | Whole `sq-role-python-dev` render, body after the frontmatter | 22,473 | 21,972 | 10,153 |
    
    - The board section is the same for every role. The whole render differs only by role body: for manager it is 18,880 after migration and 7,061 with the drafted summaries.
    - Migration alone saves 501 characters (the posted_at timestamps leave the list). The rewrite saves 11,819 more: the board section falls by 80.3% and the whole render by 53.8% against the migrated build.
    - The before pointer runs the same `sq board list --raw`, which prints each notice's whole text, author, posted_at and expiry.
    - Method: `.squads.toml` and `squads/` from commit HEAD, copied once per build under `/home/pchat/.cache/sq-adr1290/board-measure/` (`copy-before`, `copy-after`, `copy-drafted`), each migrated by its own build's `sq migrate up`. The `sq-role-<slug>` pointer is rendered by running each `!` line through that build's `sq -C <copy>`. This repo's squad was not written to.
    - Drafted column: each of the 22 live notices posted again with `sq board post "<summary>" --file <body> --as <author> [--until <until>]`, the notice's whole original text as the body, then `sq board clear 1` 22 times. The summaries keep the authors' wording and are in `summaries.tsv` (id, author, summary). Posts made within one second list in id order, so the numbers differ from the original order. op-pierre reviews the summaries before this squad is migrated.
    - `sq check` on the rewritten copy: no `notice_summary_single_line` warning. Before the rewrite, 6 of the 22 live notices warn.
    - Files: `measure.py` (renders and counts), `setup.sh` (worktree copies and migration), `rewrite.sh` (the post and clear pass), `summaries.tsv`, all in `/home/pchat/.cache/sq-adr1290/board-measure/`. The before worktree is `before-wt` there.
<!-- sq:discussion:end -->
