---
id: TASK-1004
sequence_id: 1004
type: task
title: Put the author's slug in comment headers and migrate the corpus
status: InProgress
parent: FEAT-980
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-979:implements
- TASK-954:depends-on
description: One header grammar and parser, author_slug in JSON, reserved role slugs,
  and the 0.16 migration step with the comment-header rewrite as its first contribution
subentities:
- local_id: ST1
  title: Write and parse one header grammar that names the slug
  status: Todo
  story: US1
- local_id: ST2
  title: Add author_slug to discussion JSON; show name then slug
  status: Todo
  story: US4
- local_id: ST3
  title: Refuse reserved role slugs and pin slug permanence
  status: Todo
  story: US2
- local_id: ST4
  title: Create the 0.16 migration step as a list of contributions
  status: Todo
  story: US3
- local_id: ST5
  title: 'Migrate legacy headers: resolve all, refuse loudly, rewrite'
  status: Todo
  story: US3
- local_id: ST6
  title: Freeze a 0.15 squad with discussions; prove the run end to end
  status: Todo
  story: US3
- local_id: ST7
  title: Dry-run the header planning pass on a copy of this squad
  status: Todo
  story: US3
created_at: '2026-10-12T06:46:55Z'
updated_at: '2026-10-15T21:43:32Z'
---
<!-- sq:body -->
## Scope

A comment header names its author by display name only, and the slug typed with `--as` is thrown
away at write time. This task puts the slug in the header (ADR-979), makes one parser read it
everywhere, and migrates every existing header once:

- the header grammar ``- [<timestamp>] `<slug>` <name>:``, one writer and one column-0 pattern
  shared by every reader (decisions 2 and 3);
- `author_slug` on every discussion entry in `--json`, and the slug beside the name in the human
  renders (decision 5);
- the reserved role slugs, and a test that attacks every path that could write a different slug
  to an existing roster entry (decisions 1 and 6);
- the release's one 0.15 to 0.16 migration step, which this task creates, and its first
  contribution: the comment-header rewrite, which resolves every legacy name across the whole
  corpus before it writes anything (decision 4).

It covers stories 1 to 4 of FEAT-980, the Python half of story 4 included. The VS Code half of
story 4 and story 5 (documentation) are separate tasks, because their owners differ.

There is no dual-read parser. The writer, the reader and the migration land together: a build
with the new reader and no migration cannot read an existing squad's comments, and a build with
the migration and the old reader cannot read a migrated one.

## Before the first edit

- **TASK-954 is merged.** `run_pending_migrations` hands every runner one `MigrationContext`
  (paths, the resolved spec and playbook), reconciles the index before the first runner, checks
  the corpus against the vocabulary before any runner writes, and refuses rather than stamps past
  a file it cannot index. This task adds a runner behind all of that. Write it against the
  contract in `_migrations/_context.py`, `_migrations/_registry.py` and ADR-955 as amended (A1
  to A11), not against line numbers.
- **The working version reads 0.15.0 and stays there.** Do not bump it and do not wait for a
  bump. "Building at the released version" below says what follows.
- **This task changes no bundled file** (the templates under `_rendering/templates/`,
  `_specs/workflow.toml`, `_specs/roles.toml`, `_specs/playbook.toml`). If a change to one turns
  out to be needed, stop and report it before making it.
- Not built in parallel with the verb parity work of FEAT-977: its comment verbs write this
  grammar and its update verbs must never take a slug.

## Subtasks, in build order

**The grammar, live.**

- **ST1, one header grammar: writer, shared parser, search scan** (US1).
- **ST2, `author_slug` in the discussion JSON and in the human renders** (US4).
- **ST3, reserved role slugs, and slug permanence on every write path** (US2).

**The migration.**

- **ST4, the 0.16 migration step, built as a list of contributions** (US3).
- **ST5, the comment-header contribution: resolve all, refuse loudly, rewrite** (US3).
- **ST6, a frozen 0.15 squad with discussions, and the run end to end** (US3).
- **ST7, dry-run of the planning pass on a copy of this repository's squad** (US3).

One developer, one pass: ST1, ST2 and ST5 share the header pattern and its tests, and ST4 to ST7
are one runner. The tree is reviewable after ST3 and at the end. Between those two points a
squad written by the released tool cannot be read by this build, which is expected on the
branch and is why the task ships as one increment.

## Rules this task fixes where the decision is silent

Each is a rule to build.

- **Human renders show `Name (slug)`**, and the slug once when the name equals it (`squads`).
  The same helper serves `comments`, `show --comments`, `--raw` and the TUI.
- **The writer refuses a slug outside the grammar** (`[a-z0-9][a-z0-9-]*`) with a `SquadsError`
  before anything is written. The bulk importer reaches the writer with a string the roster
  never validated.
- **Header-shaped** means a column-0 line, inside a discussion region, matching the legacy
  pattern ``^- \[([^\]]+)\] (.+?):$``. Any other column-0 line there is left alone.
- **The migration finds discussion regions by their markers**: the `discussion` tag and every
  tag ending in `:discussion`, in every item file the reconciled index lists, roster files
  included, whether or not the frontmatter still lists the sub-entity.
- **The migration writes no frontmatter.** `updated_at` and `modified_session` are untouched:
  the whole-file diff of a migrated file is its header lines and nothing else.
- **The migration keeps the name's bytes.** The rewritten header carries the legacy name as it
  was written, which is the snapshot decision 3 describes.
- **Roster names are read from each roster file's own frontmatter**, not from index entries,
  which can trail the files while a chain of runners is in flight.
- **A legacy name that is only an entry's slug** (never its display name) matches no entry, as
  the decision is written.
- **A discussion region that is opened and never closed** is a failure of its own, because a
  legacy header left behind after the stamp is read by nothing afterwards.
- **A refusal names no command the gate refuses** (ADR-955, A7). The commands that change the
  roster are in the `MANUAL` text, which says they are run with the release the squad is stamped
  for.

## The migration step

**One step for the release.**

- `_models/_schema.py`: `SCHEMA_VERSION = "0.16"`.
- A new module, `_migrations/_v0_15_to_v0_16.py`, and one entry appended to `MIGRATIONS` in
  `_migrations/_registry.py`: `version="0.16.0"`, `from_schema="0.15"`, `to_schema="0.16"`,
  `summary` and `manual` read from the module, `run` the module's `migrate`, which speaks the
  `MigrationContext` to `MigrationOutcome` contract natively (no wrapper).
- The runner declares nothing for the vocabulary check before the first runner: it renames or
  retires no type, status, prefix, folder or badge code.

**The runner is a list of contributions.** Each contribution has four parts:

- a **planning function**, read-only, which takes the run's context and returns a plan: the
  failures it found (each one printable line), the report lines for a run that completes, and
  whatever its own writer needs;
- an optional **writing function**, which takes the context and that plan, writes, and returns
  the number of files it changed. It re-reads each file it changes, so two contributions can
  change one file;
- a **section of `MANUAL`**;
- a **clause of the summary line**.

`migrate()` opens one index transaction under the run's spec, awaits every contribution's
planning function, and only then looks at the failures. If any contribution reported one, it
raises a single `SquadsError` that lists them all and nothing has been written. Otherwise it
runs the writing functions in order and returns one `MigrationOutcome` whose count is the sum
and whose report is the concatenation. `MANUAL` and the summary are assembled from the
contributions when the module is imported.

**The report channel.** `MigrationOutcome` gains `report: tuple[str, ...] = ()`, so no released
runner changes; `MigrationRun` carries it per step and `sq migrate up` prints each line under
the step's own line, escaped and soft-wrapped.

**How a later contributor amends it.** The developer-role retirement (TASK-990) and the origin
work (FEAT-976) each append one contribution to the module's tuple and add one row to the
runner's test table. They add no module, no registry entry and no schema bump, and they do not
edit `migrate()`, `MigrationOutcome`, `MigrationRun` or `_cli/_migrate.py`. The runner's test
module is written so that a contribution added to the tuple is picked up by the "every
contribution in one `sq migrate up`" assertion without editing it.

**What `sq migrate` shows.**

- `sq migrate help` gains the row `v0.16.0 | v0.15→v0.16 | <summary> | yes`.
- `sq migrate chlog v0.15.0..v0.16.0` prints the heading
  `## v0.16.0 — manual steps (schema v0.15→v0.16)` and then `MANUAL`: a short preamble saying the
  step checks every part before it writes any file, then one section per contribution. With
  only this task's contribution that is the comment-header section ST5 specifies.
- A completed `sq migrate up` prints the step line with its changed count, this contribution's
  report line (headers rewritten, files changed, headers that already carried a slug), and
  `manual steps remain — read them with sq migrate chlog v0.15.0..v0.16.0`.

**How the contribution uses the run's context.** `ctx.paths` gives the squad directory, the
index and lock paths and the stamped schema; `ctx.spec` is the `spec=` of the one `IndexStore`
the runner opens; `ctx.playbook` is unused by this contribution. The runner resolves no spec
and no playbook of its own and imports none of the names the static guard bans.

## Building at the released version

The package reads 0.15.0 while this task raises the schema to 0.16.

- **No bundled file changes, so the manifest is not involved.** The bundled templates and the
  three spec documents are byte-identical to the 0.15.0 tag before this task and stay so (read:
  no template or spec document mentions the header grammar). Do not run
  `scripts/gen_template_manifest.py` in write mode, `scripts/seed_content_store.py` or
  `scripts/bump_version.py`, and do not edit `templates_manifest.json` or `content_store.json`.
- **The manifest freshness tests keep passing.**
  `tests/meta/test_override_manifest_and_stamp_freshness.py` compares the manifest's entry for
  the running version with the bundled bytes; neither moves. Run `tests/meta` after ST1 and at
  the end. A freshness failure there means a bundled file changed: stop and report it, and do
  not edit, skip or mark the guard.
- **The registry entry names release 0.16.0 while the package reads 0.15.0.** `sq migrate up`,
  `help` and `chlog` take releases from the registry, never from the running version (read:
  `_manual_chlog_span` and `migrate_chlog` in `_cli/_migrate.py`). No test may tie the two.
- **No assertion is tied to the running package version.** A test that means "the current
  schema" imports `SCHEMA_VERSION`; a test that means this step names `"0.16"`; none reads
  `__version__` to decide what a migration, a schema or a message should be. Existing tests
  that pin `"0.15"` or `v0.15.0` as the current schema or the newest release are found by
  grepping the string across `tests/` and each is classified in the handoff: means "current"
  (moved to `SCHEMA_VERSION` or the registry's last entry) or means the 0.15 step (kept).
- **A squad this build creates is stamped schema 0.16 with `squads_version` 0.15.0.** No release
  produces that pair. The released tool refuses such a squad as ahead of it, which is correct.
- **Scratch squads for probes.** A squad the released tool initialised is behind this build
  from ST4 on: the build runs nothing on it but `sq migrate up`. That is the upgrade path the
  task proves, so upgrade fixtures and probes start from a squad the released tool
  (`~/.local/bin/sq`) wrote.

**Moved to release preparation**, and not part of this task's acceptance:

- the version bump to 0.16.0, which the operator makes once this task has landed;
- this repository's own squad being migrated, once, by the operator, after TASK-990 and
  FEAT-976 have added their contributions;
- regenerating the `v0_16` corpus fixture after the last contribution lands.

## This repository's own squad

- The developer never runs `sq migrate`, `sq repair` or `sq sync` on this repository's squad,
  with any build. From ST4 on the dev build run at the repository root refuses every command
  but `sq migrate up`, and that one would migrate the live board: do not run the dev build
  there at all. Board updates for this task go through `~/.local/bin/sq`.
- The proof that this squad migrates is ST7, on a `git archive` copy under the session
  scratchpad.

## Tests (whole task)

- **Table-driven over header shapes**, one parametrised table shared by ST1 (parse and write)
  and ST5 (migrate): each bundled role, a developer role and an operator; a retired role and a
  retired operator; the two reserved names (`Operator`, `squads`); an author whose entry was
  renamed since; names with a colon, a backtick, an accent and trailing text after a colon; a
  top-level discussion and a story's, a subtask's and a finding's; a header-shaped line with a
  bad timestamp; a header-like line that is not a header (indented, or with no closing colon);
  a header already in the new grammar; a comment whose bullets contain a line that looks like a
  header; an item body that contains one.
- **Each failure kind with no file written**, by position: top-level and each sub-entity kind,
  first, middle and last comment, one file and several. Hash every item file and
  `.squads.toml` before and after.
- **Pipeline invariants**: bullets byte-identical; the whole-file diff is header lines only;
  comment-level equivalence (same count, timestamps, names and bodies before and after, under
  the legacy parse and the live one); idempotence; convergence after an interrupted write pass;
  no roster entry's slug, stored slug or file name changes; every corpus fixture still migrates
  and passes `sq check`.
- **A service-level test and a CLI smoke test for every behaviour change.** CLI tests assert
  the bare exit code and the printed text, never an exit code read through a pipe.
- **Goldens are reviewable and stored once where shared.** The migrated-corpus goldens are
  regenerated only through `UPDATE_GOLDENS=1` on their own module, and their diff is reviewed
  as the change: the handoff says what the diff contains and why each part is expected.
- **A falsified test per subtask.** Break the change on purpose, watch the named test go red,
  restore it, watch it go green. The handoff records, per subtask, what was broken and the
  tests that went red.

## Acceptance (whole task)

- Each subtask's own acceptance holds, and every acceptance clause of stories 1 to 4 (Python
  half) is pinned by a named test. The handoff maps clause to test.
- After a completed `sq migrate up`, no item file holds a legacy header inside a discussion
  region, and every comment read back through `comments --json` carries an `author_slug`.
- One header pattern in the live tree: `rg -n 'HEADER_RE' src/squads` finds it defined once, in
  `_discussion.py`, and the frozen copies in `_migrations/_v0_15_to_v0_16.py`, and nowhere
  else. Validate the search on the commit before, where it must find the old pattern.
- The handoff lists every adopter-visible change for the tech writer: the grammar, each
  changed render, `author_slug` and where it appears, each new refusal with its text and exit
  code, the corrected search attribution, the migration's report, failure report and `MANUAL`.

## Gates and working rules

- `uv run --all-extras pyright`, `uv run --all-extras ruff check . --exclude .claude/worktrees`,
  `uv run --all-extras ruff format --check . --exclude .claude/worktrees` and
  `~/.local/bin/sq check` are clean before handback. A bare `uv run` prunes the optional `tui`
  extra and reports false import errors.
- `uv run --all-extras pytest tests/meta` whenever a module-level constant is added (the
  mutable-state guard), when the migration module is added, and when a call site of
  `Item.from_frontmatter` or a frontmatter writer moves.
- **A wide run before handing back.** Iterate with path selectors, `-x` and `--lf`. Before the
  handoff run, once, in the foreground, redirected to a file under the scratchpad and read from
  the file: `uv run --all-extras pytest tests/meta tests/unit tests/service tests/integration tests/cli`,
  with no `-k` and no `--lf`. Report the summary line and the count of `FAILED` lines. Do not
  add `-q`. The manager runs the full suite afterwards.
- Comments and docstrings are one or two sentences, with no release versions, ticket ids or
  history. The migration runner is the one place a version may appear.
- No ticket ids in source or in test names: name a test file by the behaviour it pins.
- `type X = ...` for aliases. A multi-exception handler is parenthesised and carries
  `# fmt: skip`. No `from __future__ import annotations`. Time goes through `clock`.
- No new module-level mutable state: constants are tuples, frozensets or compiled patterns.
- User-facing errors are `SquadsError` subclasses. Dynamic text printed to the console goes
  through `e()`.
- A test that pins a behaviour this task reverses is rewritten to the new behaviour and named
  in the handoff, never deleted.
- Do not edit `CHANGELOG.md` or anything under `docs/`: they go through the tech writer.
- **Probes.** Any probe script starts with `set -euo pipefail`, an absolute `cd` into its
  scratch folder under the session scratchpad, and an exit if `pwd` is under
  `/home/pchat/projects/squads`. Chain writing commands with `&&`. Never probe at `/tmp` itself
  and never in this repository's own squad. Do not silence a probe's setup errors.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1004 add-subtask "<title>"`; track with `sq task 1004 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Write and parse one header grammar that names the slug

<!-- sq:subtask:ST1:body -->
**Goal.** Every comment sq writes opens with ``- [<timestamp>] `<slug>` <name>:``, and every
reader recognises a header with the same column-0 pattern (ADR-979, decisions 2 and 3).

**Today (read).** `format_comment` in `_discussion.py` writes `- [<timestamp>] <name>:` and
`_COMMENT_HEADER_RE` reads it back for `split_discussion` and `match_comment_header`.
`_scan_comment_headers` in `_services/_collab.py` strips each line before matching, so an
indented `- [x] Done:` inside a comment counts as a header for search attribution and not for
`comments`. Writers: `CollabMixin._comment_core` (the `comment` verb, the sub-entity `comment`
verb, the bulk importer's `_apply_comment`), the two system entries in `_services/_rename.py`
and the one in `_services/_retype.py`, all three written as `squads`.

**Approach**

- `_discussion.py`
  - One compiled pattern, the decision's, anchored at column 0:
    ``^- \[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] `([a-z0-9][a-z0-9-]*)` (.+):$``. The legacy
    pattern leaves the live tree.
  - `format_comment` takes the timestamp, the slug, the name and the messages. It collapses any
    line break in the name to one space, falls back to the slug when the name is empty, and
    refuses a slug outside the grammar with a `SquadsError` that names it. The bullets are
    written exactly as today.
  - `Comment` gains `author_slug`; `author` keeps the display name.
  - `split_discussion` and `match_comment_header` use the one pattern on the line as it is, with
    no stripping. `match_comment_header` returns the timestamp, the slug and the name.
- `_services/_collab.py`
  - `_comment_core` passes `as_slug` and the name `_author_of` resolves, unchanged in how it
    resolves: a role's title, an operator's full name, `Operator` for the `operator` sentinel,
    the slug when nothing resolves.
  - `_scan_comment_headers` hands each line to the matcher unstripped. Search and inbox output
    keeps its text: the snippet stays `[<ts>] <name>: <line>` and the location stays
    `(<name>, <ts>)`.
- `_services/_rename.py`, `_services/_retype.py`: the system entries are written with slug
  `squads` and name `squads`.
- The reserved participant slugs `operator` and `squads` are spelled once, in one module that
  the writers and ST3's refusal both import.

**Tests**

- The header-shape table of the task body, parse and write halves: for each row, what
  `format_comment` writes, and what `split_discussion` and `match_comment_header` read back
  (timestamp, slug, name, body). Rows that must not parse as a header: an indented checkbox
  (`  - [x] Done:`), a column-0 line with no closing colon, a legacy header, a header whose slug
  holds an uppercase letter or an underscore, a header whose timestamp has no `Z`.
- Names: with a colon, with a backtick, with an accent, with a line break (collapsed), empty
  (the slug), ending in a colon.
- A round trip per writer, through the service and through the CLI: the `comment` verb on an
  item and on a story, a subtask and a finding; `sq migrate rename-type`,
  `sq migrate rename-status` and `sq <type> <n> retype` (slug `squads`); a bulk import with a
  comment event. Each asserts the stored header line and what `comments --json` returns.
- The importer with an actor outside the slug grammar: establish first what it does today
  (drive it on the commit before), then pin that no comment is written with such a slug and
  that the import reports it without applying part of the file.
- The two parsers agree: one region holding an indented header-shaped line gives the same
  comment count from `split_discussion` and from the search region scan, and a search hit on a
  line after it is attributed to the right comment ordinal.
- Search and inbox `--json` are byte-identical to the commit before for a squad with no
  indented header-shaped line.

**Falsify.** Put `.strip()` back in `_scan_comment_headers`: the parser-agreement test goes red.
Make the pattern's name group lazy (`.+?`): the "name ending in a colon" row goes red. Drop the
slug refusal: the importer row goes red. Restore each.

**Acceptance**

- Story 1, every clause except the human renders, which are ST2.
- Adopter-visible, for the handoff: the grammar, the slug refusal and its text, and the
  corrected search attribution for an indented header-shaped line.

Gates and working rules: the task body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add author_slug to discussion JSON; show name then slug

<!-- sq:subtask:ST2:body -->
**Goal.** A tool reading a discussion gets the author's slug as its own key, and a person
reading one sees the slug beside the name (ADR-979, decision 5).

**Today (read).** Three sites build a discussion entry as `{author, ts, body}`:
`build_item_json` and `build_subentity_json` in `_cli/_common.py` (`show --json` for an item
and for each sub-entity) and the `comments` verb in `_cli/_items.py` (`comments --json`). Four
sites print an author: `_render_comments_plain` and `_render_comments_styled`, the styled
sub-entity panes in `_print_full_panes`, the `--raw` discussion section, all in
`_cli/_common.py`, and `_discussion_view` in `_tui/_reader.py`.

**Approach**

- One function builds a discussion entry for JSON, used by the three sites: it adds
  `author_slug` after `author`. `author` keeps the display name; `ts` and `body` are unchanged.
- One function gives the author's display form for the human renders, used by every site
  above: `Name (slug)`, and the slug once when the name equals it. Styled output escapes it
  with `e()`; plain output prints it raw, as today.
- Search and inbox JSON are not touched: their snippets are display text and keep the name.

**Tests**

- `show --json` for an item with a top-level comment and a comment on a story, a subtask and a
  finding, and `comments --json`: every entry carries `author`, `author_slug`, `ts`, `body`,
  `author` is the name and `author_slug` the slug, for a role, an operator, the `operator`
  sentinel and a `squads` system entry.
- `show --json` stays byte-identical across `--raw`, `--comments` and `--full`.
- `search --json` and `inbox --json` for the same squad carry no `author_slug` and are
  byte-identical to the commit before.
- The show goldens (`feature_show.json`, `task_show.json`, `subtask_st1_show.json`,
  `item_show_raw.txt`) change by the new key and the new author form only. Review the golden
  diff as the change and say so in the handoff.
- Each human render, as a table of render by author shape: plain `comments`, styled `comments`,
  `show --comments`, `show --full --comments` (sub-entity panes), `show --raw --comments`, and
  the TUI reader's discussion tab. A name carrying `[x]` does not break the styled render.

**Falsify.** Build one of the three JSON sites by hand again without the key: the entry-shape
test for that surface goes red. Print `cmt.author` alone in the `--raw` section: its row of the
render table and the raw golden go red. Restore each.

**Acceptance**

- Story 4, every clause on the Python side. The VS Code clause is the client task's.
- Story 1's last clause: human renders show the name, then the slug.
- Adopter-visible, for the handoff: `author_slug` and the three places it appears, and each
  changed render with a before and after line.

Gates and working rules: the task body.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Refuse reserved role slugs and pin slug permanence

<!-- sq:subtask:ST3:body -->
**Goal.** The slug of a roster entry is fixed at creation and nothing writes a different one
afterwards, and no role can take a slug reserved for another kind of author (ADR-979,
decisions 1 and 6; ADR-971 on the stored slug as identity).

**Today (read, not driven).**

- Role creation has two entry points in `_services/_roster.py`, `activate_role` (bundled and
  project roles, `sq init` and `sq adopt` through it) and `add_dev`, and the bulk importer can
  create roster entries. Neither refuses `operator`, `squads` or a slug starting with `op-`:
  a project role file named `squads.toml` activates, and `sq dev add --tech op` yields `op-dev`.
- `_roles/_resolver.py::_apply_override` already refuses a per-slug override whose `slug` key
  differs from its file name, with a message naming the file.
- `sq <type> <n> retype`, `sq migrate rename-type` and `sq migrate rename-status` already
  refuse roster types.
- The work-item retitle path (`_rename` in `_services/_items.py`) re-derives `item.slug` from
  the new title and moves the file. Whether any caller can reach it with a roster item, the
  bulk importer's `update` event included, is the first thing to establish.
- No verb under `sq role`, `sq dev`, `sq skill` or `sq operator` takes a `--slug` option except
  `sq operator add`.

**Approach**

- One refusal at the seam every role creation passes through, so the importer and any later
  entry point are covered without their own check: slug `operator`, slug `squads`, and any
  slug starting with `op-`. The message names the slug, says which rule it broke (reserved for
  the anonymous author, for system entries, for operators) and that a role needs another slug.
  Nothing is written: no item, no index entry, no generated file.
- The reserved slugs and the operator prefix are spelled once, in the module ST1 introduces.
- `sq operator add` is not changed here: the decision reserves the names against roles.
- For every other path the work is a test that attacks it. Where an attack succeeds in
  writing a different slug to an existing entry, that is a defect of this subtask: fix it at
  the path and keep the test.

**Tests: one table, path by roster type** (role, developer role, skill, operator, where the
path applies). For each cell, assert the entry's `extra.slug`, its `item.slug`, its file name
and its index entry are byte-identical before and after, or that the command is refused with
exit 1 and nothing written.

- Creation refusals: `sq role activate` on a project role file named `operator.toml`,
  `squads.toml` and `op-anna.toml`; a catalog-document entry with each slug; `sq dev add --tech op`;
  a bulk import that creates a role with each. Control: `sq role activate` on an ordinary
  project role still succeeds, and so does `sq operator add --slug op-anna`.
- Override documents: a per-slug file whose `slug` key differs from its file name is refused
  and the message names the file; a catalog override that stops declaring an entry leaves the
  item created from it with its slug and file name.
- Update paths: every `update`-shaped verb and the bulk importer's `update` event, given a new
  title, name or description on a roster entry: display fields change, the slug does not.
- No slug option: walk the live Typer command table and assert that no command under the
  roster groups declares a `--slug` option, apart from an allowlist of creation verbs
  (`operator add`). The walk reads the app, so a verb added later is covered without editing
  the test.
- Retype and rename: each of the three commands on each roster type is refused.
- Repair and sync: for a role, a skill and an operator whose stored slug is not what the title
  would derive, and for one whose file name was changed by hand, run `sq repair`, then delete
  the index and run `sq repair` again, then `sq sync`: no slug is derived or written.
- Migration: over every corpus fixture, no roster entry's slug, stored slug or file name
  differs before and after `sq migrate up`.
- **Not guarded, by ruling.** A slug freed by `rm --purge` is taken by a new entity although a
  comment written earlier names it: creation succeeds, and the earlier header then reads as
  the new entity's. The test asserts the success and carries one sentence saying the reuse is
  accepted, so the check is not added later as a fix.

**Falsify.** Remove the refusal: the creation rows go red. Add a `--slug` option to one roster
verb in a test-local copy of the walk's input: the option test goes red. Let repair write a
slug derived from the title in a scratch edit: the repair row goes red. Restore each.

**Acceptance**

- Story 2, every clause, each mapped to a row of the table in the handoff.
- Adopter-visible, for the handoff: the three refusals with their text and exit code.

Gates and working rules: the task body.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Create the 0.16 migration step as a list of contributions

<!-- sq:subtask:ST4:body -->
**Goal.** The release's one 0.15 to 0.16 step exists: the schema constant, the runner module,
its registry entry, and the shape that lets each later contributor add a contribution and
nothing else. This subtask builds the shell and proves it with stand-in contributions; ST5
adds the first real one.

**Approach**

- `_models/_schema.py`: `SCHEMA_VERSION = "0.16"`.
- `_migrations/_v0_15_to_v0_16.py`, as the task body's "The migration step" settles it:
  - a frozen plan value: `failures` (printable lines), `report` (printable lines), and room
    for what the contribution's own writer needs;
  - a frozen contribution value: a name, the planning function, the optional writing function,
    its `MANUAL` section and its summary clause;
  - the module's contributions as a tuple, and `MANUAL` and the summary assembled from it;
  - one function that runs a given sequence of contributions (every plan, then the failure
    check, then every writer), and `migrate(ctx)`, which calls it with the module's tuple
    inside one `IndexStore(..., spec=ctx.spec)` transaction. Taking the sequence as an argument
    is what lets the tests drive the order with stand-ins.
  - How the plan reaches its writer under strict typing (a generic contribution, or a narrowed
    base plan) is the developer's choice, with no `Any`, no `cast` and no ignore comment.
- The failure raised when any plan reports one: a single `SquadsError`, the failures grouped by
  contribution in tuple order, one per line, then a count, then that nothing was written and
  the schema is unchanged. No string that can leave through this `raise` names a command the
  gate refuses on a behind squad; it may name `sq migrate up`.
- `_migrations/_outcome.py`: `MigrationOutcome.report: tuple[str, ...] = ()`.
  `_services/_results.py`: `MigrationRun` carries the report per step, keyed like `changed`.
  `run_pending_migrations` fills it. `_cli/_migrate.py` prints each line, indented under the
  step's line, through `e()` and with `soft_wrap=True`.
- `_migrations/_registry.py`: the import and the one entry (`version="0.16.0"`,
  `from_schema="0.15"`, `to_schema="0.16"`), with `summary` and `manual` read from the module.
  The module docstring's "adding a step" sentence gains what a contribution is.
- The schema bump reaches every test and fixture that pins the current schema. Derive the list
  by grepping `0.15` and `v0_15` across `tests/` and classify each hit as the task body's
  "Building at the released version" says. Known from reading: `tests/unit/test_migration_registry.py`
  (the highest-target test already reads `SCHEMA_VERSION`), `tests/cli/test_migrate_up_chlog_span_covers_applied.py`
  (a literal `v0.15.0` upper bound, to be read from the registry), and
  `tests/integration/test_migration_corpus.py` (the case list; ST6 adds the new rows).

**Tests** (the runner's test module, named by behaviour)

- **Order, with stand-in contributions**: three stand-ins that record each call. Every planning
  function is awaited before any writing function; writers run in tuple order; a contribution
  with no writer is planned and never written; counts are summed and report lines concatenated
  in order.
- **Refusal, by position**: a failure from the first, the middle and the last stand-in, and
  from two at once. No writer is called in any of them, the error lists every failure of every
  contribution with the count, and the transaction commits nothing.
- **Assembly**: `MANUAL` holds each contribution's section once, in order, under the preamble;
  the summary holds each clause; the registry's 0.16 entry reads both from the module.
- **The registry**: exactly one entry targets `0.16`, it is the last, and its target equals
  `SCHEMA_VERSION`.
- **Every contribution in one run**: a parametrised assertion over the module's own tuple, so a
  contribution appended later is covered without editing the test. For each, one
  `sq migrate up` on a corpus that needs it leaves that contribution's postcondition true.
  ST5 supplies the first row and its postcondition.
- **An appended contribution, through the command**: with a stand-in appended to the module's
  tuple for the test, one `sq migrate up` on a 0.15 squad runs both contributions in order,
  prints both reports, and stamps 0.16.
- **CLI**: `sq migrate help` shows the 0.16.0 row; `sq migrate chlog v0.15.0..v0.16.0` prints
  the heading and `MANUAL`; `sq migrate up` on a 0.15 squad prints the step line, the report
  lines and the chlog hint with the span `v0.15.0..v0.16.0`, exit 0; a second run prints
  "already at schema" and writes nothing. No assertion reads the package version.
- **Static guards** under `tests/meta` pass with the new module: the runner opens its
  `IndexStore` with `spec=`, resolves no spec or playbook, imports no wire-encoding primitive
  from `_models`, and no string that leaves through a `raise` names a refused command
  (ADR-955, A7).

**Falsify.** Run each writer straight after its own plan: the order test and the middle-failure
refusal row go red. Drop `report` from what `run_pending_migrations` carries: the CLI report
row goes red. Point the registry entry's `manual` at an empty string: the chlog row and the
chlog hint go red. Restore each.

**Acceptance**

- Story 3's schema clause: the schema version becomes 0.16, through one registry entry. Its
  closing clauses too: on a 0.15 squad `sq migrate up` runs this step alone, exits 0 and stamps
  0.16; a squad already at 0.16 reports nothing to migrate; a second contribution appended to
  the step runs with the first in one `sq migrate up`.
- A later contributor's whole change to the migration is one contribution appended to the
  tuple and one row in the test table. Check it by reading the diff a stand-in would need.
- `tests/meta` passes, the manifest freshness tests included.
- Adopter-visible, for the handoff: the new step in `sq migrate help`, the chlog span, and the
  report lines under a step.

Gates and working rules: the task body.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Migrate legacy headers: resolve all, refuse loudly, rewrite

<!-- sq:subtask:ST5:body -->
**Goal.** One `sq migrate up` rewrites every legacy comment header in the squad into the new
grammar, or rewrites none and says exactly why (ADR-979, decision 4). This is the first
contribution to the runner ST4 builds.

**The contribution, in `_migrations/_v0_15_to_v0_16.py`**

Frozen in the module, as every runner freezes what it reads and writes: the legacy pattern
(``^- \[([^\]]+)\] (.+?):$``), the new pattern, the timestamp grammar, and the one function that
composes a new header line. The runner imports the marker tag constants and `_sections`, and
nothing from `_discussion`.

*Planning function (reads only).*

1. **The roster.** List the role and operator items from the index the run reconciled, live and
   retired alike, and read each one's display name and slug from its own file's frontmatter: a
   role by `title`, an operator by `extra.full_name`, falling back to its `title`; the slug is
   `extra.slug`, falling back to the item's `slug`. Add the two reserved names: `Operator` to
   `operator`, `squads` to `squads`. The result maps each name to the set of distinct slugs
   that hold it.
2. **The scan.** For every item file the index lists, find each discussion region by its
   marker tag (`discussion`, and every tag ending in `:discussion`) and look at its column-0
   lines only. A line in the new grammar is counted as already migrated. A line matching the
   legacy pattern is a legacy header. Every other line is left alone, and nothing outside a
   discussion region is looked at.
3. **Resolution**, for each legacy header, with its file line number:
   - the bracket text is not a timestamp in the grammar: a failure;
   - the name maps to no slug: a failure;
   - the name maps to two or more slugs: a failure, listing them sorted;
   - otherwise the header resolves to its one slug.
   A discussion region that is opened and never closed is a failure too.
4. **The plan**: the failures, the name-to-slug map, the files that hold a legacy header, and
   the report line (headers to rewrite, files, headers already migrated).

*Failure lines*, one per header, path relative to the squad directory:

~~~
tasks/TASK-000012-add-login.md:41: 'Hugo Ops' matches no roster entry
tasks/TASK-000012-add-login.md:57: 'Sam Lee' matches 2 entries: op-sam, qa
bugs/BUG-000007-crash.md:33: '2026-06-07 10:00' is not a timestamp sq writes
reviews/REV-000009-auth.md:88: discussion region `finding:F2:discussion` is not closed
~~~

After the last line and the count, one line per distinct failing name with the number of
headers that carry it, so a name on a thousand headers is read once. Then the remedy sentence,
which names no command the gate refuses: correct the roster with the squads release this squad
is stamped for (the message names that release, as the refusals of TASK-954 do), or correct
the line by hand, then run `sq migrate up` again; `sq migrate chlog` has the steps. When the
squad was stamped below 0.15, the message adds that the earlier steps of this run have already
been applied and that running again is safe.

*Writing function.* For each file in the plan, re-read it, and in each discussion region
replace each legacy header line with the composed new one: same timestamp, the resolved slug,
the name's bytes as they were. The edit goes through `_sections` and the file is written with
the item-file writer. No frontmatter key changes. Returns the number of files written.

**The `MANUAL` section.** The facts below are acceptance; the wording is the tech writer's to
tighten, through a comment on this task.

~~~markdown
### Comment headers name the author's slug

Every comment header changes from `- [<timestamp>] <name>:` to
`` - [<timestamp>] `<slug>` <name>: ``. `sq migrate up` rewrites the header line of every
comment, in each item's discussion and in each story's, subtask's and finding's, and nothing
else: a comment's own lines stay byte for byte and no frontmatter changes. It reports how many
headers it rewrote and in how many files. Review the diff before you commit it.

The slug is found from the name. Each name is looked up among the squad's roles and operators,
retired ones included, and the two names sq writes itself (`Operator` and `squads`). Every name
is resolved before any file is written. If one cannot be, nothing is written, the schema is
unchanged and the command exits 1 with one line per header, then a count, then one line per
distinct name:

    tasks/TASK-000012-add-login.md:41: 'Hugo Ops' matches no roster entry
    tasks/TASK-000012-add-login.md:57: 'Sam Lee' matches 2 entries: op-sam, qa
    bugs/BUG-000007-crash.md:33: '2026-06-07 10:00' is not a timestamp sq writes

What to do for each, before running `sq migrate up` again:

- **A name that matches no entry.** The role or operator that wrote those comments is no
  longer in the squad. Add it back under that name. A retired entry counts, so it does not have
  to be live. If the entry is still there under a newer name, both names cannot resolve at
  once: replace the older name in those header lines by hand.
- **A name that matches several entries.** Two entries share a display name. Give one of them a
  distinct name for the run. It can be changed back afterwards.
- **A timestamp sq does not write.** The line starts at the left margin inside a discussion
  and looks like a header. If it is text that was pasted there, indent it under its comment.
  If it is a header, correct its timestamp to the form `2026-06-07T10:00:00Z`.

Changes to the roster are made with the squads release your squad is stamped for: until the
migration completes, this release runs nothing on the squad but `sq migrate up`,
`sq migrate help` and `sq migrate chlog`. A squad stamped below 0.15 is first brought to 0.15
with the 0.15.0 release. There is no option that maps a name to a slug by hand.

A header already in the new form is left as it is, so the command can be run again safely.
~~~

**Tests**

- **The header-shape table of the task body, migrate half.** For each row: the stored line
  after the run, or the failure line, and that every other byte of the file is unchanged. Rows
  beyond the task body's list: a live role and a retired role holding the same title under two
  slugs (two entries); a role and an operator sharing a name (two entries); two items holding
  one slug under one name (one entry, resolves); an operator with no `extra.full_name` (its
  title); a role titled `Operator` (two entries, with the reserved one); a legacy name equal to
  an entry's slug and not to its name (no entry); a name with trailing text after a colon; a
  file with migrated and legacy headers mixed; a discussion on a role file; an empty
  discussion; a region opened and never closed.
- **Each failure kind, by position, with nothing written**: top-level discussion and each
  sub-entity kind's; first, middle and last comment; one file, several files, and one failing
  header among many files of resolvable ones. Every item file and `.squads.toml` hash
  identically before and after, the schema stamp is unchanged, the exit code is 1, and the
  error carries every failure line, the count and the per-name lines. A second run gives the
  same output. After the remedy the run completes.
- **Every failure in one report**: a corpus holding all kinds at once reports all of them in
  one run, never the first only.
- **Bullets byte-identical**: for each migrated file, the lines that differ are exactly the
  header lines, the line count is unchanged, and the frontmatter block is byte-identical. Run
  over comments holding a fenced code block, blank continuation lines, a nested list, an
  indented line that looks like a header, and a file with CRLF line endings.
- **Comment-level equivalence**: for every discussion region, the legacy parse before and the
  live `split_discussion` after give the same number of comments with the same timestamps,
  names and bodies, and each `author_slug` is the resolved slug. This is also what ties the
  runner's frozen patterns to the live parser.
- **Idempotence and convergence**: a migrated squad stamped back to 0.15 and migrated again
  writes no file; a write pass interrupted after some files (the writer made to raise on the
  n-th), then run again, ends in the same tree as an uninterrupted run.
- **A squad stamped below 0.15**: an aged corpus fixture copied to a temporary directory, with
  a legacy comment appended to the copy, migrates through the whole chain in one run. With an
  unresolvable name instead: exit 1, no header rewritten, the stamp unchanged, the message
  says the earlier steps were applied, and a second run behaves the same.
- **The message names no refused command**: the behavioural table of TASK-954 over runs that
  end with the stamp unchanged gains this refusal as a row.
- **Two contributions on one file**: a stand-in contribution that also edits a file this one
  rewrites; both edits are present after the run.

**Falsify, and record the red tests.** Write each file as soon as it is planned: the
"one failing header among many" row goes red. Resolve a two-entry name to the first slug: the
two-entry rows go red. Compose the header from the entry's current title instead of the legacy
name's bytes: the byte-identity and equivalence tests go red on the accent row. Bump
`updated_at` in the writer: the frontmatter invariant goes red. Scan the whole file instead of
the discussion regions: the "item body holding a header-looking line" row goes red. Restore
each.

**Acceptance**

- Story 3, every clause. The runbook clause is met by the `MANUAL` section above.
- There is no option, flag, environment variable or file that maps a name to a slug.
- Adopter-visible, for the handoff: the report line, the failure report in full, the `MANUAL`
  text, and that the migration bumps no `updated_at`.

Gates and working rules: the task body.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Freeze a 0.15 squad with discussions; prove the run end to end

<!-- sq:subtask:ST6:body -->
**Goal.** The header migration is proven on a squad a released tool really wrote, through the
real `sq migrate up`, and the corpus fixtures cover the new schema. The frozen fixtures under
`tests/fixtures/corpus/` hold no comment at all today (read: every discussion region in them is
empty), so without this subtask no fixture exercises the rewrite.

**Approach**

- **A 0.15 squad with discussions, `tests/fixtures/corpus/v0_15_discussions/`.** Produced by
  the released tool (`~/.local/bin/sq`, 0.15.0) in a scratch squad under the session
  scratchpad, laid out like the other fixtures, the clock pinned with `--at` on the corpus's
  own convention, and committed exactly as the tool wrote it minus the reflog. It is never
  hand-edited: every legacy header in it is one the released writer produced. It holds:
  - a comment from each bundled role it activates, from a developer role and from an operator
    whose name carries an accent;
  - a comment written `--as operator` (the `Operator` literal) and a system entry from a
    retype or a status rename (the `squads` literal);
  - comments on a story, a subtask and a finding, and on the top-level discussion of each item
    type;
  - a role and an operator that commented and were then retired with their `status` verb;
  - a comment with several `-m`, one with a fenced code block holding a line that looks like a
    header, and an item whose body quotes a header line.
  The commands that built it go in the fixture README, as the other rows do, so it can be
  rebuilt.
- **The new current-schema fixture, `tests/fixtures/corpus/v0_16/`**, by the README's standing
  rule: the real `sq migrate up` of this build against a scratch copy of the frozen `v0_15`,
  clock pinned, committed as written minus the reflog. Its README row says it is regenerated
  when a contribution is added to the 0.16 step.
- `tests/integration/test_migration_corpus.py`: `_CORPUS_CASES` gains
  `("0.15", "v0_15_discussions")` and `("0.16", "v0_16")`.
- **Migrated-corpus goldens.** Regenerate with `UPDATE_GOLDENS=1` on
  `tests/integration/test_migrate_up_output_is_unchanged_for_every_corpus.py` only. Expected
  diff, to confirm line by line in the handoff: the schema stamp in each corpus's
  `.squads.toml` copy; a new directory for each new corpus; and for `v0_15_discussions` the
  header lines of its item files. A file several corpora write identically stays stored once
  under `_shared/`. Any other change is a finding to explain before it is committed.
- Scratch work follows the probe rules of the task body. The dev build is run from its
  virtual environment by absolute path, with the scratch squad as the working directory, never
  from the repository root.

**Tests**

- Every corpus case, old and new, reaches the current schema and passes `sq check`, through
  the service and through the CLI (the existing parametrised tests, with the new rows).
- On `v0_15_discussions`, through the CLI: exit 0; the report line's header and file counts
  equal an independent count of the fixture's legacy headers; every comment read back with
  `comments --json` and `show --json` (item and sub-entity) carries the expected `author_slug`,
  the retired role's and the two reserved slugs included; `sq check` is clean; the diff of
  every item file is header lines only.
- The contribution table of ST4 gains this contribution's row, driven on this fixture: after
  one `sq migrate up` no item file holds a legacy header inside a discussion region.
- The same fixture with one roster file's title changed in the temporary copy: exit 1, the
  failure report names every header of that author, no file differs from the copy, and the
  stamp reads 0.15.
- Search and inbox on the migrated fixture return the same hits, regions and snippets as the
  released tool returned on the unmigrated one. Capture the released tool's output when
  building the fixture and commit it beside the fixture as the reference.

**Falsify.** Skip sub-entity regions in the scan: the read-back test goes red on the story,
subtask and finding comments, and the "no legacy header left" row goes red. Leave retired
entries out of the roster: the fixture run exits 1. Restore each.

**Acceptance**

- Story 3: the scan covers top-level and every sub-entity discussion, live and retired entries
  and both reserved names, on a corpus no test wrote by hand.
- The handoff lists the fixture's build commands, the golden diff with each part explained,
  and the released tool's version used.

Gates and working rules: the task body.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Dry-run the header planning pass on a copy of this squad

<!-- sq:subtask:ST7:body -->
**Goal.** Before release preparation the operator knows exactly which header names in this
repository's own squad resolve to nothing or to several entries, and so which remedies the
live migration needs. The live squad is never touched: this runs on a copy.

**Deliverable.** One comment on this subtask, complete enough to act on without re-running
anything:

1. the commit the copy was taken from, and the dev build's commit;
2. the totals: item files scanned, discussion regions, legacy headers, headers already in the
   new grammar;
3. **the complete list of names that do not resolve**, one line per name: the name, the
   failure kind (no entry, or the entries it matches), the number of headers and the number of
   files that carry it, and two example `file:line`. Then every bad-timestamp and
   unclosed-region line in full. An empty list is stated as empty, with the totals as its
   evidence;
4. every name that does resolve, with its slug and header count, so the mapping can be read
   and challenged;
5. for each failing name, the remedy the `MANUAL` text prescribes and whether the released
   tool can perform it;
6. if the list is empty, or after applying the remedies to the copy with the released tool:
   the result of the full `sq migrate up` on the copy (exit code, printed lines, files
   changed), that the diff is header lines only, and the dev build's `sq check` on the copy.

**Approach**

- The copy: `git -C /home/pchat/projects/squads archive <commit> squads .squads.toml .claude CLAUDE.md`,
  unpacked into a new, empty directory under the session scratchpad. `git archive` reads the
  repository and changes nothing in it. Never copy the working tree in place, and never point
  a command at the repository's own `squads/` folder.
- Every command runs from a script that starts with `set -euo pipefail`, an absolute `cd` into
  the copy, and an exit if `pwd` is under `/home/pchat/projects/squads`. The dev build is
  called by the absolute path of its virtual-environment entry point, with the copy as the
  working directory, so the squad it resolves is the copy's. Print `pwd` and the resolved
  squad directory before the first command that can write.
- **First the planning pass alone**, which writes nothing: call the contribution's planning
  function on the copy's context from a short script kept in the scratchpad, and print its
  failures and report. Hash the copy before and after to show it wrote nothing.
- **Then the whole run**, only on the copy: `sq migrate up`. If it refuses, the refusal's
  text is part of the deliverable; apply the remedies to the copy with the released tool,
  record them, and run again.
- For the diff, make the copy its own throwaway git repository before migrating, and read the
  diff there.
- The copy is deleted when the comment is written, so no scratch squad is left for a later
  command to resolve by walking up from a directory beneath it.

**Checks on the result**

- The totals are confirmed by an independent count that does not use the runner: a search of
  the copy for column-0 header-shaped lines, validated first on a file known to hold some.
  Where the two counts differ, the difference is explained (lines outside a discussion region
  are the expected one).
- The list of names is compared with the copy's role and operator items, retired ones
  included, read from their files.

**Acceptance**

- The comment holds the six parts above, each labelled as driven or read.
- No file under `/home/pchat/projects/squads/squads` changed: `git -C /home/pchat/projects/squads status --short squads .squads.toml`
  shows the same lines before and after the subtask, and the handoff quotes both.
- The item count of the live squad is unchanged, read with the released tool.

Gates and working rules: the task body.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-12T06:50:36Z] Olivia Lead:
  - 2026-10-12: authored from FEAT-980 and ADR-979 under the build order of this date (MILE-934): this task creates the 0.16 migration step and TASK-990 and FEAT-976 add to it. Left in Draft, nothing promoted, no developer briefed. Three tasks: this one (stories 1 to 4, Python), TASK-1005 (story 4, VS Code client, typescript-dev) and TASK-1006 (story 5, tech-writer). Everything below is read, not driven, unless marked. @manager
    
    **To confirm with the architect before a developer starts.** Each is built as stated in the body under "Rules this task fixes where the decision is silent"; say if one is wrong.
    
    1. **The remedy against the gate.** ADR-979 decision 4 gives as remedies "add or reactivate the missing entry" and "give one of the colliding entries a distinct display name". On a squad behind the package both are commands the gate refuses (ADR-955 A1, A7). Built: the refusal names no refused command and sends the adopter to the release the squad is stamped for; `MANUAL` says so. Note that 0.15.0 has no verb that changes a display name (the per-entry verbs of `sq role` and `sq operator` are show, regen, rm, status, set-default and view; update verbs arrive with FEAT-977), so "a distinct display name" is a hand edit of frontmatter for an adopter.
    2. **A squad stamped below 0.15.** The earlier runners have written by the time this step's planning refuses, so "nothing is written" holds for this step, not for the run. Built: the message says the earlier steps were applied and that a re-run is safe; the remedy is to bring the squad to 0.15 with 0.15.0, fix the roster there, then upgrade. The alternative is a planning hook on the `Migration` record that the run calls for every pending step before the first runner; it needs the 0.16 planning to read every older corpus shape, and is not built.
    3. **A renamed author.** An entry whose earlier name is on old headers and whose current name is on newer ones cannot be resolved by any state of the roster: one failure writes nothing, so there is no two-pass. The only remedy is to replace the older name in those header lines by hand. `MANUAL` says that. The decision's premise is that names never changed.
    4. **A legacy name that is only a slug.** The writer falls back to the slug when nothing resolves, and I found no roster validation of a bulk import's actor in `_services/_import.py`. Such a header "matches no roster entry" as the decision is written; the remedy is an operator added under that name. ST1 drives the importer first.
    5. **Three additions to the decision's failure report**: a discussion region opened and never closed is a fourth failure kind; one line per distinct failing name follows the count; a bad timestamp gets the text `'<bracket text>' is not a timestamp sq writes` and a hand remedy.
    6. **Operators and the reserved slugs.** The decision reserves `operator`, `squads` and `op-` against roles only. `sq operator add --slug squads` is left as it is. Should it be refused?
    7. **No `updated_at` bump.** The migration writes header lines only and no frontmatter, unlike the 0.14 to 0.15 runner, so a thousand items do not all read as modified on migration day.
    8. **Render form** `Name (slug)`, and **the writer refuses a slug outside the grammar**.
    
    **For op-pierre, through the manager.**
    
    - One task reviewed after ST3 and at the end, or two tasks split there. It is one because the reader, the writer and the migration cannot ship apart.
    - TASK-1005 shows the slug in the preview, which story 4 does not ask for (it asks for the optional field). It is a visual change; drop the render if it is not wanted.
    - The `v0_16` corpus fixture is created here and regenerated by each later contributor to the step.
    - TASK-1006 edits `docs/`, which ships in the wheel but is not in the template manifest. By that reading it is not held by "nothing that changes a bundled file is built before the bump".
    - Once this task lands, the dev build run at the repository root refuses everything but `sq migrate up`, and that command would migrate the live board. A board notice to that effect would cover the validator worktree as well.
    
    **This repository's squad, a first read by search, not the planning pass.** Over `squads/**/*.md` at the working tree of this date: about 3,700 column-0 header-shaped lines, twelve distinct names. Eleven equal the title of a live role or the full name of the one operator; the twelfth is `Operator` (16 lines). No role or operator item is retired, no header-shaped line has a timestamp outside the grammar, and no name maps to two entries. That matches the survey in ADR-979's context. So ST7 is expected to return an empty list; it stays as the proof, since the search read whole files and not discussion regions. Two lines already in the new grammar are the examples in ADR-979's body, outside any discussion region, and are not touched.
    
    **Sentences elsewhere that the new order makes wrong** (not edited, they are not this task's): TASK-990's "Migration and schema" section and ST8 still create the runner; TASK-991's last working rule says FEAT-976 and FEAT-980 add their paragraphs to a migration section it creates, where TASK-1006 now creates it. FEAT-980 itself has no sentence saying another feature creates the runner.
    
    **What TASK-990 and FEAT-976 inherit.** One contribution appended to the tuple in `_migrations/_v0_15_to_v0_16.py` and one row in the runner's test table. The report channel TASK-990's ST8 planned to add (`MigrationOutcome.report`, `MigrationRun`, the printed lines) is built here.
- [2026-10-12T06:54:13Z] Catherine Manager:
  - 2026-10-12, manager's calls on the tech lead's four questions for the operator. Three are mine and are flagged to the operator as such; one is his.
    
    - **One task, two review points.** TASK-1004 stays one task; the reviewer passes after ST3 and at the end. The writer, the reader and the migration cannot ship apart.
    - **The `v0_16` fixture** is created here and regenerated by each later contributor (TASK-990, FEAT-976). Accepted.
    - **TASK-1006 is not held behind the version bump.** The manifest script hashes the templates and the three spec documents only (read: `scripts/gen_template_manifest.py`), so a change under `docs/` moves no manifest entry.
    - **Open, for the operator:** TASK-1005 shows the slug in the VS Code preview, which story 4 does not ask for. TASK-1005 is not promoted until he answers.
    
    The eight design questions are with @architect; TASK-1004 is not promoted until they are ruled and TASK-954 has landed.
- [2026-10-15T21:43:32Z] Catherine Manager:
  - Dispatched to @python-dev: ST1-ST3 first, then the review checkpoint, then ST4-ST7 (manager call of 2026-10-12). -C (FEAT-1015) has landed; scratch probes use -C.
<!-- sq:discussion:end -->
