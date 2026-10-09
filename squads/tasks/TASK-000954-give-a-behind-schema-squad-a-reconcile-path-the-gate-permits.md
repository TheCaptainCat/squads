---
id: TASK-954
sequence_id: 954
type: task
title: Give a behind-schema squad a reconcile path the gate permits
status: Draft
author: tech-lead
priority: medium
refs:
- REV-952:fixes
- MILE-934:targets
- ADR-955:implements
description: Behind the schema gate only sq migrate runs, yet a stale index dead-ends
  it, its remedies name refused commands, and every migrate verb is exempt; reconcile
  inside migrate up per ADR-955
subentities:
- local_id: ST1
  title: Name only permitted commands in remedies behind the gate
  status: Todo
- local_id: ST2
  title: Reconcile the index structurally before the first runner
  status: Todo
- local_id: ST3
  title: Drive migrate up end to end over behind-schema squad shapes
  status: Todo
- local_id: ST4
  title: Build migrate up without the live-index cross-check
  status: Todo
- local_id: ST5
  title: Exempt only migrate up, help and chlog from the schema gate
  status: Todo
created_at: '2026-09-15T08:41:13Z'
updated_at: '2026-10-09T19:37:29Z'
---
<!-- sq:body -->
## Scope

A squad whose stamped `schema_version` is behind the installed package can run one command
group, `sq migrate`. Everything else is refused by `require_current_schema`
(`src/squads/_cli/_common.py`), called from the root callback in `src/squads/_cli/__init__.py`.
`sq migrate up` is therefore the only way out of that window, and four things are wrong with it.

1. **A missing, corrupt or stale index is a dead end.** Runners read the index through their own
   `IndexStore.transaction()`, which refuses a missing file, unparseable JSON, and an entry whose
   type or status the active spec does not declare. Every one of those refusals names `sq repair`,
   and `sq repair` is refused by the gate.
2. **A file the index does not know is never migrated.** Every runner enumerates items from the
   index. A markdown file with no index entry (what an interrupted create leaves) is passed over
   without a word: `sq migrate up` exits 0 and stamps the new schema, and `sq check` reports the
   item afterwards.
3. **The exemption covers the whole `migrate` group.** `sq migrate repad`, `rename-type` and
   `rename-status` rename files and rewrite frontmatter on a squad that is behind the package,
   and also on one that is *ahead* of it, where `sq migrate up` itself refuses.
4. **Remedies name refused commands.** Messages reachable from `sq migrate up` on a behind-schema
   squad tell the operator to run `sq repair`, `sq check` or `sq workflow lint`.

This is a general hazard, not one migration's: any runner that raises, and any `migrate up`
interrupted between its markdown writes and the index commit, leaves the markdown ahead of the
index, which is the direction `_index/_store.py` sanctions on the strength of a heal the operator
cannot run here. The surface is a gate every command passes through, across every schema version
and every migration, so it belongs to no one feature.

## Reproductions

Each row reproduces on a scratch squad initialised with the current package, given two
milestones and one task, with the `sq:view:milestone_rollup` line deleted from both milestone
files and `.squads.toml` hand-stamped `schema_version = "0.14"`.

| Shape | Command | Result |
|---|---|---|
| index file deleted | `sq migrate up` | exit 1, `missing index .squads.json; run sq repair ...`; `sq repair` exits 1 at the gate |
| index is not JSON | `sq migrate up` | exit 1, `corrupt index .squads.json ...; run sq repair ...`; same loop |
| index entry carries status `Triaged`, file says `Draft` | `sq migrate up` | exit 1, `... (or run sq repair if the index itself is merely stale)`; same loop |
| one milestone removed from the index, file still on disk | `sq migrate up` | exit 0, `1 changed`, schema stamped; that milestone has no tag and `sq check` then errors on it |
| task file hand-edited to `status: Triaged` | `sq migrate up` | both milestones written, then exit 1 `fix the frontmatter before running sq repair`; schema not stamped; re-running repeats it |
| override that drops the `task` type | `sq migrate up` | exit 1 with the override refusal, which names `sq workflow lint`; that exits 1 at the gate |
| any | `sq migrate rename-status task Draft Ready`, `sq migrate repad 7` | exit 0; frontmatter rewritten, every item file renamed, schema still `0.14` |
| `.squads.toml` stamped `0.99` | the same two commands | exit 0, same writes, on a corpus `sq migrate up` refuses as newer than the package |

A frontmatter value that is merely ahead of the index (a hand-edited title, an update whose index
commit never landed) already migrates cleanly: no runner reads values from the index or calls the
skew guard.

## The rule being implemented

ADR-955 rules what may run while the schema is behind, as a property of the operation and not of
the command name. An operation holds the **reconcile licence** only if it is:

1. **vocabulary-blind**: nothing the active spec resolves (types, statuses, folders, prefixes,
   ref kinds and their default, views, sub-entity kinds, badge collections, validators) decides
   what it does; it reads the corpus structurally (bytes, file names, marker shape, frontmatter
   keys);
2. **content-neutral**: it writes no item body and no frontmatter value, only derived state (the
   index), stamped at the corpus's own schema and never the installed one;
3. **convergent**: it leaves the squad no further from a successful `sq migrate up`, and never
   changes what a later runner was written to read.

What follows from it, and bounds this task:

- `sq repair` gains no exemption, no mode and no flag. Its trailing call in
  `run_pending_migrations`, and the ordering argument in its docstring, stay exactly as they are.
- The licensed operation is a narrow routine of its own, run by `sq migrate up` before its first
  runner.
- `sq migrate up` builds its service without the live-index cross-check.
- A message may only name a command that is permitted in the state the message fires in.
- A squad ahead of the package stays refused.

## Subtasks, in build order

- **ST2, reconcile the index before the first runner.** The licensed routine, and its call from
  `run_pending_migrations`. Closes defects 1 and 2.
- **ST4, build `migrate up` without the cross-check.** The override case, and the one
  vocabulary check that moves in front of the runners.
- **ST5, exempt only `migrate up`, `help` and `chlog`.** Closes defect 3.
- **ST1, remedies behind the gate.** Closes defect 4, once the three above have fixed which
  messages are still reachable.
- **ST3, end to end.** The proof over squad shapes, driven through the CLI.

One developer, one pass: ST2, ST4 and ST1 all edit `run_pending_migrations` and
`_cli/_migrate.py`.

## Acceptance (whole task)

- Each subtask's own acceptance holds.
- **Table-driven tests over shape families, not one test per implemented branch.** Each subtask
  names its families. The tables are parametrised, and a row that needs its own fixture still
  goes through the same assertions as its neighbours.
- **Pipeline-level invariants**, each stated in its subtask: the result of `sq migrate up` over
  every aged corpus fixture is unchanged by the reconcile; no failing `sq migrate up` on a
  behind-schema squad names a refused command; the set of commands that run on a mismatched
  squad equals the set declared to.
- **A falsified test per subtask.** Break the fix on purpose, watch the new test go red, restore
  it, watch it go green. The handoff records what was broken and the name of the test that went
  red, for each subtask.
- **A service-level test and a CLI smoke test for every behaviour change.** CLI tests assert the
  bare exit code and the printed text, never an exit code read through a pipe.
- Assert the operator's position, not only that a command stopped failing: which files changed
  (hash them), what the index holds, what the schema stamp says, and what can be run next.

## Gates and working rules

- `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .` and `sq check` are clean before handback. A bare
  `uv run` prunes the optional `tui` extra and reports false import errors.
- Run `uv run --all-extras pytest tests/meta` whenever a module-level constant is added (the
  mutable-state guard) and whenever a migration-facing module is added or an
  `Item.from_frontmatter` call site moves.
- Run targeted tests only (`--lf`, `-x`, path selectors), redirected to a file and read from the
  file. Report which selectors were run. The full suite is run by the manager afterwards.
- Code comments and docstrings are one or two sentences, with no release versions, ticket ids or
  history. No ticket ids in source or in test file names: name a test file by the behaviour it
  pins.
- `type X = ...` for aliases. A multi-exception handler is parenthesised and carries
  `# fmt: skip`. No `from __future__ import annotations`. Time goes through `clock`.
- User-facing errors are `SquadsError` subclasses. Dynamic text printed to the console goes
  through `e()`.
- Do not edit `CHANGELOG.md` or anything under `docs/`. The handoff lists every adopter-visible
  change for the tech writer: the new `sq migrate up` line, every reworded message, the commands
  that now refuse on a mismatched squad, and the sentence in `docs/migration.md` that says every
  `sq migrate` command runs on an out-of-date squad.
- Probe in a scratch squad nested under the session scratchpad, never at `/tmp` and never in this
  repository's own squad: check the working directory before any writing command and chain with
  `&&`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 954 add-subtask "<title>"`; track with `sq task 954 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Name only permitted commands in remedies behind the gate

<!-- sq:subtask:ST1:body -->
**Goal.** Every message, docstring and report line that can reach an operator while the schema
is behind names only a command that runs in that state: `sq migrate up` (or `help` / `chlog`), or
an action outside `sq` (fix the frontmatter, restore the file, edit the override).

**Defect.** The remedy wording is shared between callers that run at the current schema, where
`sq repair` is the right answer, and `sq migrate up`, where it is refused. Known sites:

- `MaintenanceMixin._raise_unless_vocab_valid` (`src/squads/_services/_maintenance.py`), three
  messages ending `fix the frontmatter before running sq repair`, reached through the trailing
  `repair()` in `run_pending_migrations`.
- `IndexStore._read_from_disk`, `_validate_item_vocab` and `_check_field_codes`
  (`src/squads/_index/_store.py`): missing index, corrupt index, and `(or run sq repair if the
  index itself is merely stale)`, reached through a runner's own `IndexStore.transaction()`.
- `spec_refusal` (`src/squads/_workflow/_loader.py`), whose last line recommends
  `sq workflow lint`, and the `validate_against_index_fail_closed` cause text that does the same;
  also check `_pending_spec_error` in `src/squads/_cli/_common.py`, which can print it from the
  root group before any command body runs.
- The module docstring of `src/squads/_index/_store.py`: the table column headed `sq repair
  outcome`, the sentence that each interrupted state "heals losslessly", and the closing "`sq
  repair` remains the recovery path there too"; and the last sentence of
  `IndexStore.transaction`'s docstring. All four state the current-schema half unconditionally.
- `src/squads/_migrations/_v0_14_to_v0_15.py`, the paragraph explaining why the runner never
  raises: it says a raised run leaves "no working command to reconcile the two with".

`skew_message` (`src/squads/_itemfile.py`) is correct as it stands: its callers are the write
seams, `sq sync` and the importer, none of which runs behind the gate, and no runner imports it.

**Approach**

- **Inventory first.** Sweep `src/squads` for every string and docstring naming an `sq`
  subcommand as something to run, and classify each: the states it can fire in, whether the
  schema can be behind in that state, and what the operator can run there. Validate each search
  pattern against a known hit before trusting a zero. Post the table as a comment on this
  subtask; it is what the reviewer checks the fixes against.
- **Compose the remedy where the state is known, never by rewording a shared message for its
  ordinary callers.** `repair()` and `_rebuild_index_from_disk` take the command to re-run as a
  keyword (default the ordinary one); `run_pending_migrations` passes the migrate form. Do not
  catch an error and edit its text.
- **One closing line on anything that escapes.** A `SquadsError` leaving the runner loop or the
  trailing `repair()` in `run_pending_migrations` is re-raised with one added sentence: the squad
  is still at schema X, and the way forward is to fix the cause and re-run `sq migrate up`, which
  reconciles the index first.
- **Store messages.** After the reconcile and the pre-runner check the three store-load refusals
  are not reachable from `sq migrate up` in any known shape. Do not thread caller state into the
  store. Leave their wording, and let the invariant below prove they stay unreachable.
- **Docstrings.** State which command heals in which state: `sq repair` at the current schema,
  `sq migrate up`'s own reconcile while the schema is behind. One or two sentences each; correct
  the claim, do not record how it changed.

**Acceptance**

- **Pipeline invariant, behavioural:** over every row of the failure table below, when
  `sq migrate up` exits non-zero on a behind-schema squad, every `sq <subcommand>` token in its
  output is `sq migrate`. The test extracts the tokens with one regex and compares against the
  permitted set, so a new message is covered without being listed.
- **Failure table (families):** the refused rows from the cross-check subtask (dropped type,
  dropped status, dropped sub-entity status, re-prefixed type, shrunk badge collection,
  hand-edited status, hand-edited type, override that does not load, playbook override that does
  not load); a runner that raises a `SquadsError` (inject one through a patched `MIGRATIONS`,
  before and after it has written a file); the trailing `repair()` raising on each of its
  refusals (vocabulary, corpus alignment, a spec declaring no single default ref kind).
- For the injected-runner rows: the added closing line is present, the schema is unchanged, and
  a second `sq migrate up` with the runner restored completes and migrates the file the first
  pass had already written without changing it again.
- **Static guard under `tests/meta`:** in every module under `src/squads/_migrations/`, no string
  literal inside a `raise` names an `sq` subcommand other than `migrate`, and none imports
  `skew_message` or `ensure_no_skew`. Scan `raise` literals only: the `MANUAL` runbooks and the
  docstrings legitimately name `sq check` and `sq sync` as steps taken once the squad is current.
  Prove the scan sees a planted violation before trusting its pass.
- The ordinary callers are unchanged: `sq repair` at the current schema prints exactly the
  wording it prints now for each of the same refusals (pinned in the same table, schema equal).
- Service test for the keyword on `repair()`; CLI test for the `sq migrate up` wording.
- **Falsify, and record the test that went red for each:** drop the keyword at the
  `run_pending_migrations` call so the trailing repair says `sq repair` again; remove the closing
  line; add `run sq check` to a raise in a runner.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Reconcile the index structurally before the first runner

<!-- sq:subtask:ST2:body -->
**Goal.** Before its first runner, `sq migrate up` rebuilds the index from the markdown with a
routine that holds the reconcile licence, so every runner reads an index that mirrors the files,
whatever state the index was left in.

**Defect.** Runners enumerate items from the index and open it through a validating
`IndexStore.transaction()`. On a behind-schema squad a missing index, an unparseable one, and an
entry whose status the spec does not declare each stop `sq migrate up` with a message naming
`sq repair`; a file with no index entry is silently left unmigrated while the run exits 0.

**Approach**

- A new module, `src/squads/_index/_reconcile.py`, with one public coroutine that takes the
  squad directory, the `IndexStore` to write through, and the schema version to stamp, and
  returns a small result dataclass (what was indexed that the previous index lacked, what was
  dropped as missing, what was carried forward unread). It takes no `WorkflowSpec` and imports
  nothing from `squads._workflow`, `squads._interactions`, `squads._views`, `squads._specs` or
  `squads._services`.
- **Previous index.** Read it with `store.load(validate_vocab=False)`. A missing or unparseable
  index means "no previous index", as it does for `repair()`: the counter floor then comes from
  the files alone.
- **Walk.** Every `*.md` under the squad directory, skipping dot-directories. The folders are
  whatever the corpus contains, never the folders a spec declares. A file is an item when its
  frontmatter parses and carries an `id`; memory notes, board notices and a legacy slug-named
  skill file carry none and are ignored without a report.
- **Entry rules, each one a consequence of "carry forward, never fabricate".**
  - A file that parses becomes its entry, with `path` the squad-relative path it was found at.
    The sequence number is `sequence_id` when present, else the digits of `id` (the two oldest
    corpus fixtures carry no `sequence_id` in any item file).
  - `refs` and a legacy `extra.ref_kinds` map are stored exactly as the frontmatter spells them.
    No default ref kind is resolved and `fold_legacy_kinds` is not called. `Item.from_frontmatter`
    requires a default kind, and `tests/meta/test_from_frontmatter_call_sites_stay_enumerated.py`
    pins its three call sites: add a fold-free constructor beside it in `_models/_item.py` rather
    than a fourth call with an invented kind.
  - A file that cannot become an item (unreadable, malformed YAML, a required field missing or
    type-invalid) keeps its previous entry, found by path and then by the sequence number in its
    file name, and is named in the result. With no previous entry it stays unindexed and is still
    named. Either way the digits in its file name raise the counter and padding floors.
  - A timestamp the file does not carry keeps its previously indexed value.
    `_carry_forward_indexed_timestamps` and `_fold_stem_into_floor` in `_services/_maintenance.py`
    already do this and take no spec: move them where both modules can import them, do not copy
    them. The file-name parse needs a spec-free form (`_stem_digit_run` strips a spec prefix).
  - Two files claiming one id: no winner is picked. The previous entry is carried when there is
    one, neither is indexed when there is not, and both files are named.
  - A previous entry is dropped only when no file sits at its recorded path and no file on disk
    claims its sequence number. It is named as missing. Failing to parse a file never drops it.
- **Write.** One `store.overwrite(db)`. `db.schema_version` is the version passed in (the
  corpus's own), `counter` is the higher of the previous counter and the highest number seen,
  `padding` the higher of the previous padding and the widest file-name digit run, and
  `squads_version` is carried from the previous index, else from `.squads.toml`. No item file is
  written. No reflog op is added.
- **Call site.** In `MaintenanceMixin.run_pending_migrations`, when at least one runner applies,
  call the routine with `self.paths.config.schema_version` before the first `m.run(...)`. When no
  runner applies nothing is reconciled, so `sq migrate up` on a current squad stays a no-op.
  `MigrationRun` carries the result, and `migrate_up` prints one line for it only when something
  was indexed, dropped or carried.

**Acceptance**

- **Vocabulary-blind, as a table.** For each corpus shape below, the index bytes written are
  identical when the store is built with the bundled spec, an override dropping a type the corpus
  uses, one dropping a status it uses, one re-foldering and re-prefixing a type, and one changing
  the default ref kind. Plus an AST test under `tests/meta` asserting the module imports none of
  the five packages above and no function in it takes a `WorkflowSpec`.
- **Content-neutral.** The hash of every file under the squad directory other than the index is
  unchanged by the routine, and the written index carries the corpus's schema version, over
  squads stamped at three different old schemas.
- **Shape families.** One parametrised table, index state by file shape, each row asserting the
  entry rule it exercises.
  - Index state: consistent with the files; missing; not JSON; JSON that fails the model; an
    entry with a type the spec lacks; an entry with a status the spec lacks; no entry for a file
    on disk; an entry whose file is gone; an entry at an old path with the file at a new one; an
    entry with a stale field value.
  - File shape: parses; undecodable bytes; malformed YAML; no frontmatter at all; frontmatter
    with no `id` (a memory note, a board notice, a slug-named skill file); an `id` with no
    `sequence_id`; no `created_at` or `updated_at`; two files with one id; a hyphenated prefix; a
    slug that starts with digits; a file in a folder no bundled type declares; a legacy
    `extra.ref_kinds` map.
- **Pipeline invariant (convergence).** For every fixture under `tests/fixtures/corpus/`, under a
  frozen clock: the routine alone leaves the set of indexed sequence numbers and paths equal to
  the fixture's own index, and `sq migrate up` ends with every file and the index identical to
  what it produces with the routine stubbed out.
- **Service test:** `run_pending_migrations` over each index-state row completes and every
  eligible item is migrated, including the one the index did not know.
- **CLI test:** `sq migrate up` exits 0 on the missing-index and not-JSON rows and prints the
  reconcile line; it prints no such line on a consistent squad.
- `sq migrate up` on a squad already at the current schema writes nothing (index hash unchanged).
- **Falsify, and record the test that went red for each:** remove the call from
  `run_pending_migrations`; stamp `SCHEMA_VERSION` instead of the passed version; route the parse
  through the folding constructor with the spec's default kind; drop an entry when its file fails
  to parse.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Drive migrate up end to end over behind-schema squad shapes

<!-- sq:subtask:ST3:body -->
**Goal.** Prove the whole path on real behind-schema squads, through the installed CLI entry
point, with the operator's position asserted after every command and never only an exit code.

**Approach**

- One integration module (name it for the behaviour, for example
  `tests/integration/test_a_behind_schema_squad_can_always_migrate_or_is_told_why.py`), built on a
  helper that makes a pre-migration squad: initialise, create two milestones and a task, delete
  the roll-up tag line from both milestone files, stamp `schema_version = "0.14"` in
  `.squads.toml`. Each row then applies one mutation to that squad.
- Drive `sq` through `CliRunner`, one invocation per command, reading the bare exit code. Add one
  subprocess row (the pattern in `tests/cli/test_migrate_up_bare_subprocess_exit_parity.py`) so
  the root callback and the real entry point are exercised once.
- After the last subtask lands, repeat the table by hand in a scratch squad with the built
  package and paste the transcript into the handoff: the squad must be nested under the session
  scratchpad, and the working directory checked before every writing command.

**Squad shapes (one parametrised table)**

| Row | Mutation | Expected after `sq migrate up` |
|---|---|---|
| clean | none | exit 0, schema current, both milestones tagged |
| index missing | delete `.squads.json` | as clean; reconcile line printed |
| index not JSON | overwrite with `{ not json` | as clean; reconcile line printed |
| index invalid for the model | valid JSON, wrong shape | as clean |
| stale entry, undeclared status | index says `Triaged`, file says `Draft` | as clean |
| file the index lacks | remove one milestone's entry | as clean, and that milestone is tagged |
| entry whose file is gone | delete one milestone file | exit 0; the other is tagged; the gone one is reported missing |
| rename interrupted | move a file to a new slug, leave the index | as clean, at the new path |
| value ahead of the index | hand-edit a title | as clean, title kept |
| partial pass | tag one milestone by hand, bump its `updated_at`, leave the index | as clean; the tagged file is byte-identical afterwards |
| interrupted run | a runner patched to raise after its first write, then restored | first run exit 1 with the closing line, schema unchanged; second run as clean |
| override, consistent | an override that changes nothing the corpus uses | as clean |
| override, stale-index conflict | a consistent override, plus an index entry carrying a status no lifecycle declares | as clean |
| override, real conflict | override drops the `task` type | exit 1 before any item file changes; message names the override and only `sq migrate up` |
| override does not load | invalid TOML | exit 1, index and item files unchanged |
| hand-edited status | task file set to `Triaged` | exit 1 before any item file changes |
| ahead of the package | stamp `0.99` | exit 1, "upgrade the squads package", nothing written |

**Acceptance**

- Every "as clean" row ends in the same state as the clean row: the same set of indexed items,
  both roll-up tags present exactly once inside the body region, `schema_version` current, and
  then `sq check` exits 0 and `sq list` runs.
- **No body is rewritten under the old schema.** For every row, hash each item file before
  `sq migrate up` and after the reconcile but before the first runner (patch the first runner to
  capture): the hashes are equal. Only runners and the trailing `repair()` change item files.
- **Every exit-1 row is recoverable or says why not.** Apply the remedy the message names by
  hand, re-run `sq migrate up`, and it completes. The ahead row is the one exception, and its
  message says to upgrade the package.
- **Gate rows, on the clean squad before migrating and on the ahead squad:** `sq repair`,
  `sq check`, `sq list`, `sq migrate repad 7`, `sq migrate rename-status task Draft Ready` and
  `sq migrate rename-type task guide` each exit 1 with the gate message and change no file;
  `sq migrate help` and `sq migrate chlog v0.14.0..v0.15.0` exit 0.
- **Idempotence:** on every row that completes, a second `sq migrate up` prints "nothing to
  migrate" and leaves every file and the index byte-identical.
- **Pipeline invariant:** the final corpus of every completing row equals the clean row's final
  corpus, file for file, apart from the fields the row's own mutation changed.
- **Falsify, and record the test that went red for each:** stub the reconcile out (the
  index-state rows go red); restore the `get_service()` build in `migrate_up` (the override rows
  go red); widen the gate exemption back to the whole group (the gate rows go red).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Build migrate up without the live-index cross-check

<!-- sq:subtask:ST4:body -->
**Goal.** A workflow override can no longer veto the one command a behind-schema squad may run
on the strength of an index that command is about to rebuild.

**Defect.** `migrate_up` (`src/squads/_cli/_migrate.py`) builds through `get_service()`. For a
squad carrying `.overrides/workflow.toml`, `bind_active_spec` has already run
`validate_against_index_fail_closed` against the live index in the root callback, and
`_build_plain_service` re-raises that cached refusal. So `sq migrate up` exits 1 before any
runner, with a message whose last line recommends `sq workflow lint`, which the gate refuses.
Building the service without the cross-check is necessary and not sufficient: the same squad then
fails one layer down, in the runner's own `IndexStore.transaction()`, with `item TASK-23 has type
'task', which the active spec no longer declares; migrate or re-type this item ... (or run sq
repair ...)`.

**Approach**

- `migrate_up` builds through `get_service_bypassing_index_cross_check()`
  (`src/squads/_cli/_common.py`), which falls back to the merged spec from `load_workflow_spec`
  with no index cross-check.
- **No bundled fallback for this caller.** `_build_bypass_fallback_service` ends by substituting
  the bundled spec when the override does not load at all. That is right for `sq repair` and
  wrong here: a migration must not run under a vocabulary the project did not declare. Give the
  accessor a keyword for it rather than writing a third accessor. An override that does not load
  stops `sq migrate up` before the reconcile and before any runner, naming the file, the loader's
  own cause, and the remedy: fix the file, then re-run `sq migrate up`.
- **One vocabulary check, in front of the runners.** After ST2's reconcile the index mirrors the
  frontmatter, so a type, status, folder, prefix or badge code the active spec does not declare is
  now a fact about the corpus and not about a stale index. `run_pending_migrations` runs
  `validate_against_index` (`src/squads/_workflow/_loader.py`, the list-returning form) on the
  reconciled index before the first runner and, on any mismatch, raises one `SquadsError`
  composed for this state: the offending items, the override path when there is one, and the
  remedy (restore the declaration in the override, or correct the named frontmatter by hand, then
  re-run `sq migrate up`). At that point nothing but the index has been written. It applies with
  or without an override, so a hand-edited status is refused here too, before any runner writes,
  instead of by the trailing `repair()` after they all have.
- `sq repair`, `sq check` and every other caller of `get_service()` are unchanged: at the current
  schema the cross-check and its wording stay as they are.

**Acceptance**

- **Shape families, one table, each row driven through `run_pending_migrations` and through the
  CLI**, asserting exit code, message, the schema stamp, and the hash of every item file:
  - override present and consistent with the corpus: completes;
  - override conflicts only with a stale index entry (the file's own value is declared):
    completes, because the reconcile removed the conflict;
  - override drops a type the corpus uses; drops a status it uses; drops a sub-entity status it
    uses; re-prefixes or re-folders a type that has items; shrinks a badge collection a stored
    value names: refused before any item file changes, schema unchanged;
  - no override, one file hand-edited to an undeclared status; to an undeclared type: refused
    the same way, and no milestone file has been written;
  - override that is not valid TOML; valid TOML that fails spec validation: refused before the
    reconcile (index hash unchanged), message names the file;
  - a playbook override that fails to load, beside a valid workflow override: refused before
    the reconcile as well, naming `.overrides/playbook.toml` (the newest runner loads the
    playbook itself and would otherwise raise from inside the pass).
- In every refused row the printed message names no `sq` command other than `sq migrate up`.
- After the remedy in the message is applied by hand, re-running `sq migrate up` completes, for
  every refused row.
- Every fixture under `tests/fixtures/corpus/` still migrates to the current schema with the
  check in place.
- `sq repair` on a current-schema squad whose override does not load still falls back to the
  bundled spec as it does now (the existing bypass tests stay green, and one row pins it).
- **Falsify, and record the test that went red for each:** switch `migrate_up` back to
  `get_service()`; let the bundled fallback through for this caller; remove the pre-runner check
  and watch the "no item file changed" assertion fail on the hand-edited-status row.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Exempt only migrate up, help and chlog from the schema gate

<!-- sq:subtask:ST5:body -->
**Goal.** On a squad whose schema does not match the package, in either direction, the only
commands that run are the ones that hold the reconcile licence or write nothing: `sq migrate up`,
`sq migrate help` and `sq migrate chlog`.

**Defect.** `require_current_schema` returns early for `subcommand == "migrate"`, and in the root
callback `ctx.invoked_subcommand` is the group name, so every verb under `sq migrate` is exempt.
`sq migrate repad`, `sq migrate rename-type` and `sq migrate rename-status` resolve vocabulary
off the installed spec and rename files or rewrite frontmatter values, which fails both the
vocabulary-blind and the content-neutral clause. They run on a behind-schema squad, and on a squad
*ahead* of the package, where `sq migrate up` refuses and this package has no model for the
corpus. Each then prints `run sq check to verify integrity`, which the gate refuses.

**Approach**

- Keep the root gate where it is and as it is for every other group.
- Declare the capability on the command, not in a tuple: a small marker (a decorator in
  `src/squads/_cli/_common.py`, applied in `src/squads/_cli/_migrate.py`) on `migrate_up`,
  `migrate_help` and `migrate_chlog`. A callback on `migrate_app` reads its own
  `ctx.invoked_subcommand`, and when the resolved command does not carry the marker it applies
  the same refusal the root gate applies, with the same two messages (behind: run `sq migrate
  up`; ahead: upgrade the package). One refusal function, two call sites.
- `--help` keeps bypassing the gate everywhere, as it does now.
- `migrate_up` keeps its own ahead-of-package refusal.

**Acceptance**

- **Pipeline invariant, as a meta-test:** walk the registered command tree (every top-level
  command and group of `app`, and every verb of `migrate_app`). The set of commands that get
  past the gate on a mismatched squad equals the set carrying the marker, and that set is
  exactly `migrate up`, `migrate help`, `migrate chlog`. A new verb added under `sq migrate`
  without a marker is refused by default.
- **Shape families, one parametrised CLI table:** schema direction (behind, ahead, equal) by
  command (`migrate up`, `migrate help`, `migrate chlog`, `migrate repad`, `migrate rename-type`,
  `migrate rename-status`, and three ordinary commands: `list`, `repair`, `check`) by invocation
  form (bare, with `--help`, with `--dir` pointing at the squad from outside it). Each row
  asserts the exit code, which of the two gate messages is printed if any, and, for the three
  writing verbs, that no file under the squad directory changed (hash before and after).
- Equal-schema rows prove nothing regressed: the three writing verbs still do their work.
- Outside a squad (no `.squads.toml`) the migrate verbs behave as they do now.
- A service-level test is not applicable to the gate itself (it lives in the CLI layer); the
  services behind `repad`, `rename_type` and `rename_status` are untouched and their existing
  tests stay green.
- **Falsify, and record the test that went red for each:** remove the marker check from the
  `migrate_app` callback (the behind and ahead rows for the three writing verbs go red); add the
  marker to `migrate_repad` (the meta-test goes red).
- Handoff names the adopter-visible change: three commands that ran on an out-of-date squad now
  refuse, and `docs/migration.md` says otherwise.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T09:00:25Z] Robert Architect:
  - Ruled in ADR-955 (refs this task). The answer is a rule about operations, not an exemption list.
    
    **The reconcile licence.** Behind the schema gate an operation may run only if it is (1) vocabulary-blind — no spec-resolved type/status/prefix/folder/ref-kind/view/badge value decides its behaviour; (2) content-neutral — it writes no body and no frontmatter value, only derived state (the index), stamped at the *corpus's* schema, not the installed one; (3) convergent — it leaves the squad no further from a successful `sq migrate up`. Anything failing (1) or (2) is a migration step and belongs in a versioned runner. That is what the next migration inherits.
    
    **`sq repair` is not exempted, in any form** — not wholesale, not behind a "skip the sweeps" flag. It reads installed vocabulary at six points and writes at four (the ref fold + canonical re-encoding, vocab validation, the retired-region strip, the body-tag convergence, retired role `extra` keys), globs by the active spec's folders, and stamps `SCHEMA_VERSION` into the rebuilt index. Its own docstring also derives its strip-ordering proof *from* the gate refusing it, so an exemption deletes a construction proof.
    
    **ST2 is rescoped, and the gate is not touched.** The licensed subset is separable — structural scan vs semantic sweep — but as its own narrow routine, not a mode on `repair`; and its home is `migrate up`'s **unconditional pre-pass**, before the first runner. That closes the deadlock inside the one command already permitted, so the exempt set stays at one. Later widening arrives as a declared capability on the command plus a meta-test binding the exempt set to it, never a second literal in a tuple.
    
    **One obligation the task does not have yet:** `migrate up` builds via `get_service()`, so a behind-schema squad carrying `.overrides/workflow.toml` can still be refused by `open_service`'s live-index cross-check — for the same class of reason the gate exempted it. The exempt command must build through `get_service_bypassing_index_cross_check()`, or the exemption is nominal.
    
    **ST1 stands and now has a rule to sweep against:** a remedy may only name a command permitted in the state it fires in. Three sites read — the 0.14/0.15 runner's messages and docstring; `_index/_store.py`'s module docstring (true at current schema, false behind the gate, and it must say which); `_itemfile.skew_message` (correct for its ordinary callers, so a runner composes its own remedy clause rather than inheriting it). A meta-test over runner modules is the cheap enforcement.
    
    **Ahead-of-package is unchanged**, and now derived rather than incidental: it fails content-neutrality, because this package cannot round-trip a newer corpus, so a rebuilt index is a lossy write of derived state. Its message already names a remedy that exists.
    
    Left open in the ADR: no deliberate verb for a licensed reconcile; a runner whose own refusal is the wall is not fixed by this; whether the licence should also govern reads.
    
    @manager ADR-955 is in its initial status for op-pierre. ST2/ST3 land against the licence, not against a chosen command.
- [2026-09-29T13:24:12Z] Pierre Chat:
  - Not high priority.
- [2026-10-09T19:01:09Z] Olivia Lead:
  - 2026-10-09: redrafted against ADR-955 as Accepted and the code at `f0c6295b`. Body and ST1 to ST3 rewritten, ST4 and ST5 added, summary updated, `implements` ref to ADR-955 added. Left in Draft and unassigned; no developer briefed.
    
    **Driven at that commit** (scratch squads stamped `0.14`, the repo's own build; every row is in the body's reproduction table): missing index, corrupt index and a stale index entry with an undeclared status each loop between `sq migrate up` ("run `sq repair`") and `sq repair` ("run `sq migrate up`"); a file the index lacks is skipped while the run exits 0; a hand-edited status lets the runners write and then stops at the trailing repair; an override conflict stops `migrate up` with a message naming `sq workflow lint`; `sq migrate repad` and `rename-status` run and write on a behind squad and on one stamped `0.99`. `rename-type` was read, not driven. A service built the way the bypass accessor builds it fails the same override squad one layer down, in the runner's own transaction.
    
    **Where ADR-955 no longer matches the code** (read unless marked):
    - The 0.14 to 0.15 runner has no abort path and no `raise` at all, and no runner imports `skew_message` or `ensure_no_skew` (grep, pattern validated against `_itemfile.py`). Two of the ADR's three remedy sites are already gone; the store docstring is the one left.
    - "The only thing that blocks a re-run is `ensure_no_skew`" is no longer true: a frontmatter value ahead of the index migrates cleanly (driven). The live defects are the index-state ones above, which the ADR does not list.
    - "`migrate` remains the only exempt subcommand" describes `migrate up`. The gate exempts the group (driven), so "a squad ahead of the package is unchanged" does not hold for three of its verbs.
    - The meta-test "no runner module's text names a gate-refused subcommand" fails as written: 64 such mentions across all ten runner modules, in `MANUAL` runbooks and docstrings describing the squad once it is current.
    - The licensed routine is described against current frontmatter. The `v0_1` and `v0_2` corpus fixtures carry no `sequence_id` in any item file (probed), so a routine built on `Item.from_frontmatter`'s required keys would index nothing there.
    
    **Calls made in the draft that go past the ADR's letter**, each to confirm or veto before a developer starts:
    1. ST5 narrows the exemption to `migrate up`, `help` and `chlog`. `docs/migration.md` currently documents that every `sq migrate` command runs on an out-of-date squad, so this is an adopter-visible contract change.
    2. ST4 does not take the bypass accessor's bundled-spec fallback for `migrate up`, and adds one vocabulary check on the reconciled index before the first runner, so a real conflict is refused before any item file is written.
    3. ST2 reads "unconditional" as "whenever a runner applies, with no staleness test", not "also on a squad already at the current schema".
    4. ST1 scopes the static runner guard to `raise` literals and carries the rule as a behavioural invariant over failing `migrate up` runs.
    
    @manager for the operator's read. Points 1 and 2 touch the decision itself, so they may want the architect's amendment rather than a yes on this task.
- [2026-10-09T19:14:12Z] Pierre Chat:
  - 2026-10-09: the points where this draft goes past ADR-955 (the narrower gate exemption, the pre-runner vocabulary check and skipped fallback) and the stale premises it found go to the architect as an amendment to ADR-955. The task follows the amended decision; no developer starts on it before that.
- [2026-10-09T19:36:38Z] Robert Architect:
  - 2026-10-09: ADR-955 is amended in place (A1 to A7 under **Amendments**). Your four calls are confirmed with the changes below; nothing in the task body is edited by me. @tech-lead
    
    **ST5, the gate (A1).** Confirmed: `up`, `help`, `chlog`. Two changes.
    - The declared capability carries the directions it covers: `up` behind only, `help` and `chlog` both. On a squad ahead of the package the gate refuses `up` itself, before a service is built. Driven today: an ahead squad with an override conflict prints the override refusal with `sq workflow lint`, not "upgrade the squads package". `migrate_up`'s own ahead check may stay as a second line but is not the mechanism.
    - The meta-test binds the set per direction, and the table gets the ahead-plus-override row.
    
    **ST2, the reconcile (A2, A3, A4).** Confirmed, including "nothing is reconciled when no runner applies". Three changes.
    - "A file is an item when its frontmatter parses and carries an `id`" is too wide. A squad directory may be the project root (`squad_dir = "."`, as in every corpus fixture), where the walk meets every markdown file in the repository, and a docs page with an `id:` key would be reported as a broken item. Recognise an item by the shape of its file name and of its `id`. Add a row: root squad directory, unrelated markdown with and without an `id` key, nothing reported.
    - A4 turns two of your report lines into a refusal. A file that could not be given an entry of its own (undecodable, frontmatter that does not parse, identity that cannot be established, an id two files claim) stops the run before the first runner, entry carried forward, each file named with its cause. The result dataclass has to keep that set apart from "dropped as missing", which stays a report on a run that continues.
    - Scope items 1 and 2 and ST2's defect say every runner enumerates items from the index. Two do (0.11 to 0.14 for the roster projection, 0.14 to 0.15), two are no-ops, and the rest glob by frozen folder and prefix literals, opening the index, if at all, to allocate ids. Reword.
    
    **ST4, the build and the check (A5, A6).** Both additions confirmed. Four changes.
    - One vocabulary resolution, used by every step. Driven: a squad stamped 0.11 or 0.8 whose valid override declares a type of its own, with one item, is refused by `migrate up` ("type 'incident', which the active spec no longer declares ... run sq repair"). Stamped 0.14 it migrates; without the override, stamped 0.11, it migrates. Cause, read: `IndexStore(paths.index_path, paths.lock_path)` with no spec in the 0.4 to 0.5, 0.8 to 0.10 and 0.11 to 0.14 runners, which validates under the bundled vocabulary. Your pre-runner check would pass this squad and the runner would then refuse it. It needs a row (completes) and a home: this subtask or a bug, your call with the manager.
    - The check refuses only the families the load boundary refuses at the current schema. Say in its docstring that a runner which renames or retires vocabulary declares what it consumes on its migration record; none does today, so no mechanism is owed now.
    - Remedy text. Override that does not load: the file, the loader's cause, correct the file, re-run `sq migrate up`. Conflict: the items, the override path, restore the declaration or correct the frontmatter by hand, re-run. Neither may carry the closing line of `spec_refusal`, the "run `sq workflow lint`" embedded in the fail-closed cause, or `rename-type` and `rename-status` as later steps.
    - Ruled is "before the first runner". Whether the override refusal precedes the reconcile is yours.
    
    **ST1, remedies (A7).** Confirmed, static guard on `raise` literals included. Four changes.
    - The behavioural invariant's permitted set is `sq migrate up`, `help`, `chlog`, read from the capability. "Every token is `sq migrate`" lets `sq migrate repad` through. Scope it to runs that end with the stamp unchanged.
    - `skew_message` is correct after ST5, not as it stands: `rename_type` and `rename_status` reach it through `_check_batch_skew` on a behind squad today. Record the dependency.
    - Add to the inventory: the capacity refusal in `SquadsDB.allocate_id` names `sq migrate repad` and can be raised to the three runners that allocate ids; the three writing verbs' closing "run `sq check`" (unreachable on a mismatched squad once ST5 lands).
    - The 0.14 to 0.15 docstring paragraph is wrong on a second count: the runner does raise, through what it calls. Driven: malformed frontmatter in a milestone file stops the run from inside it.
    
    **ST3, end to end.** Add: the unreadable-file rows (malformed frontmatter, undecodable bytes, one id in two files), each exit 1 before any item file changes and completing after the fix; the custom-type override stamped 0.11 and 0.8; the root squad directory; the ahead squad with an override conflict. "Value ahead of the index" and "partial pass" complete today without the reconcile, so they prove nothing about it alone. The undecodable row reverses a pinned behaviour (skipped, stamped, exit 1): review the existing exit-parity test and the `migrate up` exit-code docstring with it.
    
    **Docs handoff, for the tech writer.** `docs/migration.md`: the sentence that `sq migrate *` are the only commands exempt and always run on an out-of-date squad; the order to follow when the three verbs are wanted on an old squad (migrate first; restore a dropped declaration, migrate, rename, drop it again); the new `migrate up` refusals and their remedies; the reconcile line. The table there already lists exactly `up`, `help` and `chlog`.
    
    **Read, not driven, not ruled.** The 0.1 to 0.2, 0.2 to 0.3, 0.5 to 0.7 and 0.7 to 0.8 runners walk frozen bundled folders and prefixes, so a custom type's files on a squad stamped 0.5 are not visited by the 0.5 to 0.7 unpadding. Same family as A4, outside this task unless you take it. And a suggestion only: carry the reconcile's result on the `migrate` reflog line, since an entry dropped as missing is otherwise recorded nowhere.
- [2026-10-09T19:37:29Z] Robert Architect:
  - 2026-10-09: @manager ADR-955 is amended in place. Its discussion carries what changed and four points for op-pierre to weigh before this task is promoted: the narrower gate exemption (adopter-visible), the refusal on an unreadable item file instead of stamping past it, a custom-type migration defect that needs a home, and a reciprocal note owed on ADR-663. Posted here as well because an inbox lists open items only and ADR-955 is Accepted.
<!-- sq:discussion:end -->
