---
id: TASK-954
sequence_id: 954
type: task
title: Give a behind-schema squad a reconcile path the gate permits
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- REV-952:fixes
- MILE-934:targets
- ADR-955:implements
- BUG-988:fixes
description: sq migrate up is the only exit for a behind-schema squad, yet a stale
  index dead-ends it, unreadable files are stamped past, own-type squads are refused,
  every migrate verb is exempt and remedies name refused commands; ADR-955 as amended
subentities:
- local_id: ST1
  title: Name only permitted commands in remedies behind the gate
  status: Done
- local_id: ST2
  title: Reconcile the index before the runners; refuse unindexable files
  status: Done
- local_id: ST3
  title: Drive migrate up end to end over mismatched squad shapes
  status: Done
- local_id: ST4
  title: Run migrate up under the squad's vocabulary, checked up front
  status: Done
- local_id: ST5
  title: Let only migrate up, help and chlog past the gate, by direction
  status: Done
- local_id: ST6
  title: Open every runner's index under the run's resolved vocabulary
  status: Done
created_at: '2026-09-15T08:41:13Z'
updated_at: '2026-10-15T19:19:49Z'
---
<!-- sq:body -->
## Scope

A squad whose stamped `schema_version` differs from the installed package's is refused by
`require_current_schema` (`src/squads/_cli/_common.py`), called from the root callback in
`src/squads/_cli/__init__.py`, for every command outside the `sq migrate` group. Behind the
package, `sq migrate up` is the only way out of that window, and six things are wrong with it.

1. **A missing, corrupt or stale index is a dead end.** Four of the ten runners open the index
   (0.4 to 0.5, 0.8 to 0.10, 0.11 to 0.14, 0.14 to 0.15), through an `IndexStore` load that
   refuses a missing file, unparseable JSON, and an entry whose type or status the spec does not
   declare. Each refusal names `sq repair`, and `sq repair` is refused by the gate.
2. **A file the index does not know is never migrated by the runners that enumerate from it.**
   Two do (0.11 to 0.14 for the roster projection, 0.14 to 0.15 for every item it touches); two
   are no-ops, and the rest walk frozen folder and prefix literals. A markdown file with no index
   entry is passed over by those two without a word: `sq migrate up` exits 0 and stamps the new
   schema, and `sq check` reports the item afterwards.
3. **An item file that cannot be read is stamped past.** Undecodable bytes, frontmatter that
   does not parse, a missing `id`, or one id in two files, in a file no runner happens to read:
   the run migrates the rest, stamps the new schema and exits 1 with a report. Frontmatter that
   does not parse in a file a runner does read stops the run instead, with the schema unchanged.
   Once the stamp is written no runner visits a passed-over file again.
4. **A squad with a type of its own cannot migrate from an older schema.** The 0.4 to 0.5,
   0.8 to 0.10 and 0.11 to 0.14 runners build `IndexStore(paths.index_path, paths.lock_path)`
   with no spec, which validates under the bundled vocabulary. A squad stamped 0.11 or 0.8 whose
   valid override declares a type, with one item of it, is refused as carrying a type "the active
   spec no longer declares". Nothing is wrong with that squad.
5. **The exemption covers the whole `migrate` group.** `sq migrate repad`, `rename-type` and
   `rename-status` rename files and rewrite frontmatter on a squad that is behind the package,
   and also on one that is *ahead* of it. `repad` ends in the full `repair()` sweep, which
   `repair`'s own docstring says cannot run on a behind-schema corpus.
6. **Remedies name refused commands.** Messages reachable from `sq migrate up` on a squad it
   leaves behind tell the operator to run `sq repair`, `sq check`, `sq workflow lint` or
   `sq migrate repad`.

This is a general hazard, not one migration's: any runner that raises, and any `migrate up`
interrupted part-way, leaves the markdown ahead of the index, which is the direction
`_index/_store.py` sanctions on the strength of a heal the operator cannot run here. The surface
is a gate every command passes through, across every schema version and every migration, so it
belongs to no one feature.

**Not in this task.** The 0.1 to 0.2, 0.2 to 0.3, 0.5 to 0.7 and 0.7 to 0.8 runners walk frozen
bundled folders and prefixes, so they never visit a custom type's files. That is a question about
what a shipped runner covers, it is not repaired by anything here, and a squad already stamped
past those runners can only be caught up by a new one.

## Reproductions

Each row reproduces on a scratch squad initialised with the current package, given two
milestones and one task, with the `sq:view:milestone_rollup` line deleted from both milestone
files and `.squads.toml` hand-stamped `schema_version = "0.14"` unless the row says otherwise.

| Shape | Command | Result |
|---|---|---|
| index file deleted | `sq migrate up` | exit 1, `missing index .squads.json; run sq repair ...`; `sq repair` exits 1 at the gate |
| index is not JSON | `sq migrate up` | exit 1, `corrupt index .squads.json ...; run sq repair ...`; same loop |
| index entry carries status `Triaged`, file says `Draft` | `sq migrate up` | exit 1, `... (or run sq repair if the index itself is merely stale)`; same loop |
| one milestone removed from the index, file still on disk | `sq migrate up` | exit 0, `1 changed`, schema stamped; that milestone has no tag and `sq check` then errors on it |
| task file overwritten with undecodable bytes | `sq migrate up` | both milestones migrated, schema stamped, exit 1 with a report |
| task file given frontmatter that does not parse; its `id` line deleted; copied to a second file | `sq migrate up` | the same for each: stamped, exit 1 |
| a milestone file given frontmatter that does not parse | `sq migrate up` | exit 1 from inside the runner, schema unchanged |
| task file hand-edited to `status: Triaged` | `sq migrate up` | both milestones written, then exit 1 `fix the frontmatter before running sq repair`; schema not stamped; re-running repeats it |
| override that drops the `task` type | `sq migrate up` | exit 1 with the override refusal, which names `sq workflow lint`; that exits 1 at the gate |
| valid override declaring an `incident` type, one incident; stamped `0.11` or `0.8` | `sq migrate up` | exit 1, `item INC-24 has type 'incident', which the active spec no longer declares ... run sq repair`; stamped `0.14` it migrates, and without the override stamped `0.11` it migrates |
| any | `sq migrate rename-status task Draft Ready`, `sq migrate repad 7` | exit 0; frontmatter rewritten, every item file renamed, schema still `0.14` |
| stamped `0.99` | the same two commands | exit 0, same writes |
| stamped `0.99`, with the override that drops `task` | `sq migrate up` | exit 1 with the override refusal, not "upgrade the squads package" |

A frontmatter value that is merely ahead of the index, and a pass interrupted after some files
were written, both complete already. Alone they prove nothing about the reconcile.

## The rule being implemented

ADR-955, as amended on 2026-10-09 (A1 to A7), rules what may run while the schema differs from
the package, as a property of the operation and not of the command name. An operation holds the
**reconcile licence** only if it is:

1. **vocabulary-blind**: nothing the active spec resolves (types, statuses, folders, prefixes,
   ref kinds and their default, views, sub-entity kinds, badge collections, validators) decides
   what it does; it reads the corpus structurally (bytes, file names, marker shape, frontmatter
   keys);
2. **content-neutral**: it writes no item body and no frontmatter value, only derived state (the
   index and the reflog), stamped at the corpus's own schema and never the installed one;
3. **convergent**: it leaves the squad no further from a successful `sq migrate up`, and never
   changes what a later runner was written to read.

What follows from it, and bounds this task:

- **The gate (A1).** On a squad whose schema differs from the package's, the gate lets past
  `sq migrate up` when the squad is behind, and `sq migrate help`, `sq migrate chlog` and `--help`
  in both directions. Nothing else. `sq repair` gains no exemption, no mode and no flag.
- **Before the first runner, on a behind squad, in this order:** the declared vocabulary and
  every other document a pending runner loads resolve, or the run stops (A5); the reconcile runs
  (A2, A3); every item file has an index entry of its own, or the run stops (A4); the reconciled
  corpus fits the vocabulary, or the run stops (A6). Only the index is written before the first
  runner.
- **One resolution (A5).** Every step that validates against vocabulary uses the one the run
  resolved: the pre-runner check, each runner's own access to the index, the trailing repair.
- **The reconcile runs whenever a runner applies, with no staleness test (A3).** Not on a squad
  at the current schema, where `sq migrate up` writes nothing, and not on one ahead.
- **Remedies (A7).** A run that leaves the squad behind names, as remedies, only commands the
  gate lets past in that state and actions outside `sq`. A run that completes leaves a current
  squad and may name any command.
- `repair()`'s trailing call in `run_pending_migrations`, and the ordering argument in its
  docstring, stay exactly as they are.

## Subtasks, in build order

- **ST6, runners use the run's vocabulary.** Every runner reaches the index under the spec the
  run resolved. This is the whole fix for defect 4, it depends on nothing else here, and it is
  built first so it can be reviewed, and if need be shipped, on its own.
- **ST2, reconcile the index before the first runner, and refuse a file that cannot be
  indexed.** Closes defects 1, 2 and 3.
- **ST4, build `migrate up` under the squad's vocabulary and check it before the runners.** The
  override cases, and the one vocabulary refusal that moves in front of the runners.
- **ST5, the gate, command by command and direction by direction.** Closes defect 5.
- **ST1, remedies on a squad left behind.** Closes defect 6, once the four above have fixed
  which messages are still reachable and which commands are permitted.
- **ST3, end to end.** The proof over squad shapes, driven through the CLI.

One developer, one pass: ST6, ST2, ST4 and ST1 all edit `run_pending_migrations`,
`_migrations/_registry.py` and `_cli/_migrate.py`. The custom-type defect (4) is fixed here and
not in a task of its own because the amended decision obliges it of this work (every runner under
the run's resolution), because ST4's check would otherwise pass that squad only for a runner to
refuse it mid-run, and because ST3 cannot prove the path without it.

## Acceptance (whole task)

- Each subtask's own acceptance holds.
- **Table-driven tests over shape families, not one test per implemented branch.** Each subtask
  names its families. The tables are parametrised, and a row that needs its own fixture still
  goes through the same assertions as its neighbours.
- **Pipeline-level invariants**, each stated in its subtask: the result of `sq migrate up` over
  every aged corpus fixture is unchanged by the reconcile; no `sq migrate up` run that leaves the
  schema stamp unchanged names a command the gate refuses in that state; the set of commands
  that get past the gate equals the set declared to, per direction; `sq migrate up` never stamps
  a squad holding an item file without an index entry of its own.
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
- A test that pins a behaviour this task reverses is rewritten to the new behaviour and named in
  the handoff, never deleted.
- Do not edit `CHANGELOG.md` or anything under `docs/`. The handoff lists every adopter-visible
  change for the tech writer:
  - the two an adopter can observe: `repad`, `rename-type` and `rename-status` no longer run on
    a squad whose schema differs from the package's, and `sq migrate up` no longer stamps past an
    item file it cannot index;
  - in `docs/migration.md`: the sentence that `sq migrate *` are the only commands exempt and
    always run on an out-of-date squad; the order to follow when the three verbs are wanted on an
    old squad (migrate first; where the corpus uses vocabulary the override has dropped, restore
    the declaration, migrate, rename at the current schema, then drop it again); the new
    `sq migrate up` refusals and their remedies; the reconcile line;
  - every reworded message, and the new key on the `migrate` reflog line.
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
**Goal.** A `sq migrate up` run that leaves the squad behind names, as remedies, only commands
the gate lets past in that state (`sq migrate up`, `help`, `chlog`) and actions outside `sq` (fix
the frontmatter, restore the file, edit the override).

**Scope of the rule.** Its subject is a remedy: what an operator is told to run to leave the
state the run leaves them in. A run that completes leaves a current squad, so its report may name
any command. A `MANUAL` runbook and a runner's docstring describe steps taken after that and are
outside the rule.

**Defect.** The remedy wording is shared between callers that run at the current schema, where
`sq repair` is the right answer, and `sq migrate up`, where it is refused. The sites that name a
refused command to an operator left behind the gate:

- `IndexStore._read_from_disk`, `_validate_item_vocab` and `_check_field_codes`
  (`src/squads/_index/_store.py`): missing index, corrupt index, and `(or run sq repair if the
  index itself is merely stale)`, reached through a runner's own index access.
- `MaintenanceMixin._raise_unless_vocab_valid` (`src/squads/_services/_maintenance.py`), three
  messages ending `fix the frontmatter before running sq repair`, reached through the trailing
  `repair()` in `run_pending_migrations`.
- `spec_refusal` (`src/squads/_workflow/_loader.py`), whose last line recommends
  `sq workflow lint`, and the `validate_against_index_fail_closed` cause text that does the same;
  also check `_pending_spec_error` in `src/squads/_cli/_common.py`, which can print it from the
  root group before any command body runs.
- `SquadsDB.allocate_id` (`src/squads/_models/_index.py`): the capacity refusal ends "Raise the
  padding with `sq migrate repad <new-width>`". The three runners that allocate ids can raise it,
  and `repad` is a refused command behind the gate.
- Two docstrings. The module docstring of `src/squads/_index/_store.py` states the
  current-schema half unconditionally in four places: the table column headed `sq repair
  outcome`, the sentence that each interrupted state "heals losslessly", the closing "`sq repair`
  remains the recovery path there too", and the last sentence of `IndexStore.transaction`'s
  docstring. And the paragraph in `src/squads/_migrations/_v0_14_to_v0_15.py` explaining why the
  runner never raises is wrong on two counts: the runner can raise, through what it calls
  (frontmatter that does not parse in a milestone file stops the run from inside it), and a
  raised run does have a command to reconcile with, `sq migrate up` itself.

Two sites that are correct only because of the gate subtask, and must be recorded as depending
on it: `skew_message` (`src/squads/_itemfile.py`), which `rename_type` and `rename_status` reach
through `_check_batch_skew` on a behind squad today; and the closing `run sq check` of
`repad`, `rename-type` and `rename-status`. Neither is reachable on a mismatched squad once those
three verbs are refused there. No runner imports `skew_message`.

**Approach**

- **Inventory first.** Sweep `src/squads` for every string and docstring naming an `sq`
  subcommand as something to run, and classify each: the states it can fire in, whether the run
  can leave the squad behind in that state, and what the operator can run there. Validate each
  search pattern against a known hit before trusting a zero. Post the table as a comment on this
  subtask; it is what the reviewer checks the fixes against. The sites above are its seed.
- **A shared message stays worded for its ordinary callers.** The remedy is composed where the
  state is known, by `migrate up`, and never by rewording the seam or by catching an error and
  editing its text. `repair()` and `_rebuild_index_from_disk` take the command to re-run as a
  keyword (default the ordinary one); `run_pending_migrations` passes the migrate form.
- **The capacity refusal.** `run_pending_migrations` composes this one too: the index is full at
  the current padding; widen it with the squads release this squad is stamped for, then upgrade
  and re-run `sq migrate up`. It names no `repad` command, because none runs in this state.
- **One closing line on anything that escapes.** A `SquadsError` leaving the runner loop or the
  trailing `repair()` in `run_pending_migrations` is re-raised with one added sentence: the squad
  is still at schema X, and the way forward is to fix the cause and re-run `sq migrate up`, which
  reconciles the index first.
- **Store messages.** After the reconcile and the pre-runner check the store-load refusals are
  not reachable from `sq migrate up` in any known shape. Do not thread caller state into the
  store. Leave their wording, and let the behavioural invariant prove they stay unreachable.
- **Docstrings.** State which command heals in which state: `sq repair` at the current schema,
  `sq migrate up`'s own reconcile while the schema is behind. The runner's paragraph says what is
  true: it turns the conditions it meets into skips, and a run that stops is resumed by
  re-running `sq migrate up`. One or two sentences each; correct the claim, do not record how it
  changed.

**Acceptance**

- **Behavioural invariant, and the one that binds.** Over a table of `sq migrate up` runs that
  end with the schema stamp unchanged, every `sq <group> <verb>` the output names is one the gate
  lets past in that state. The permitted set is read from the declared capability and is not
  written into the test, so `sq migrate repad` in a message fails it and a new message is covered
  without being listed.
- **The table (families).** Every refused row of the reconcile subtask (each unindexable cause)
  and of the cross-check subtask (dropped type, status, sub-entity status, re-prefixed type,
  shrunk badge collection, hand-edited status and type, workflow and playbook overrides that do
  not load); a runner that raises a `SquadsError`, injected through a patched `MIGRATIONS`,
  before and after it has written a file; a full index, with a runner that allocates an id
  pending; the trailing `repair()` raising on each of its refusals (vocabulary, corpus alignment,
  a spec declaring no single default ref kind).
- For the injected-runner rows: the added closing line is present, the schema is unchanged, and
  a second `sq migrate up` with the runner restored completes and migrates the file the first
  pass had already written without changing it again.
- **Static guard under `tests/meta`, narrower.** In every module under `src/squads/_migrations/`,
  no string that can leave through a `raise` names a refused command, and none imports
  `skew_message` or `ensure_no_skew`. It is scoped to `raise` because the rest of a runner's text
  is description. Prove the scan sees a planted violation before trusting its pass.
- The ordinary callers are unchanged: at the current schema `sq repair`, the write seams and
  `allocate_id` print exactly the wording they print now (pinned in the same table, schema
  equal).
- Service test for the keyword on `repair()` and for the composed capacity refusal; CLI test for
  the `sq migrate up` wording.
- **Falsify, and record the test that went red for each:** drop the keyword at the
  `run_pending_migrations` call so the trailing repair says `sq repair` again; let the capacity
  refusal through unchanged; remove the closing line; add `run sq check` to a raise in a runner.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-15T18:21:27Z] Elias Python:
  - Inventory of remedies reachable from `sq migrate up` on a squad left behind (read from the code; each row is pinned by a refusal row in `tests/integration/test_a_refused_migrate_up_names_only_commands_the_gate_permits.py` or by the meta guard).
    
    | Site | Fires when | Permitted? | Resolution |
    |---|---|---|---|
    | `IndexStore` load refusals (missing, corrupt, undeclared type/status) | a runner opens an index the reconcile did not repair | no, names `sq repair` | unreachable after the reconcile and the pre-runner check; wording kept; the closing line covers a stray escape |
    | `_raise_unless_vocab_valid` (three messages) | trailing `repair()` meets an unknown type, status or sub-entity status | no | takes the command to re-run as `rerun`; `run_pending_migrations` passes the migrate form |
    | `_corpus_alignment_refusals` text in trailing `repair()` | spec re-foldered/re-prefixed against the corpus | names no command | unchanged |
    | `spec_refusal`, `validate_against_index_fail_closed` (`sq workflow lint`) | override does not load or does not fit the index | no | `migrate up` composes its own refusal (file, cause, "re-run `sq migrate up`"); the shared text still serves ordinary callers |
    | `SquadsDB.allocate_id` capacity refusal (`sq migrate repad`) | a pending runner allocates an id at a full index | no | raises `IndexFullError`; `run_pending_migrations` composes the refusal naming the release that reads the stamped schema |
    | any other `SquadsError` out of a runner or the trailing repair | a runner or the repair stops | n/a | re-raised with one closing line: the squad is still at schema X, fix the cause, re-run `sq migrate up` |
    | `skew_message`, `ensure_no_skew` | `rename_type`/`rename_status` on a behind squad | n/a | unreachable once the gate refuses those verbs; no runner imports them (meta guard) |
    | module docstrings in `_index/_store.py` and `_migrations/_v0_14_to_v0_15.py` | n/a | n/a | state which command heals in which state; the runner's paragraph says it can raise and a stopped run is resumed by `sq migrate up` |
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Reconcile the index before the runners; refuse unindexable files

<!-- sq:subtask:ST2:body -->
**Goal.** Before its first runner, `sq migrate up` rebuilds the index from the markdown with a
routine that holds the reconcile licence, so every runner that opens the index reads one that
mirrors the files, whatever state it was left in. And it never stamps a squad holding an item
file it could not index.

**Defect.** Four runners open the index through a validating `IndexStore` load, and two of them
(0.11 to 0.14 for the roster projection, 0.14 to 0.15) enumerate items from it. On a behind-schema
squad:

- a missing index, an unparseable one, and an entry whose type or status the spec does not
  declare while the file's own value is declared, each stop `sq migrate up` with a message naming
  `sq repair`;
- a file with no index entry is never visited by the two enumerating runners, and the run exits
  0 and stamps the new schema;
- an item file that cannot be read (undecodable bytes, frontmatter that does not parse, no `id`,
  one id in two files, a read the OS refuses) is skipped, the schema is stamped and the exit is
  1, unless a runner happens to read that file, in which case malformed frontmatter stops the
  run from inside it.

**Approach: the routine**

- A new module, `src/squads/_index/_reconcile.py`, with one public coroutine that takes the
  squad directory, the `IndexStore` to write through, and the schema version to stamp, and
  returns a result dataclass. It takes no `WorkflowSpec` and imports nothing from
  `squads._workflow`, `squads._interactions`, `squads._views`, `squads._specs` or
  `squads._services`. It refuses nothing: it reports.
- **Previous index.** Read it with `store.load(validate_vocab=False)`. A missing or unparseable
  index means "no previous index", as it does for `repair()`: the routine then builds from the
  files alone, and the counter floor comes from them.
- **Walk.** Every `*.md` under the squad directory, skipping dot-directories. The squad
  directory may be the project root (`squad_dir = "."`, as in every corpus fixture), where the
  walk meets every markdown file in the repository, so no file is opened unless its name has the
  item shape.
- **Recognition is structural, never by a declared folder.** A file is a candidate when its name
  has the shape `<PREFIX>-<digits>-<slug>.md`. A candidate is an item when its frontmatter parses
  and carries an `id` of the shape `<PREFIX>-<digits>`. Recover the prefix from an id with
  `prefix_from_id` (`_models/_item.py`), never by counting hyphens
  (`tests/meta/test_no_hand_rolled_id_prefix_split_outside_shared_primitive.py`). A markdown file
  that is not an item is never reported: any file whose name lacks the shape, whatever its
  frontmatter says, and a candidate whose frontmatter parses without such an `id` when the
  previous index holds no entry at its path.
- **Every schema this package can migrate from is read as written.** The two oldest fixtures
  carry no `sequence_id` in any item file; the number is then read from the `id`. A shape an
  older schema wrote legitimately is never damage.
- **Entry rules, each a consequence of "carry forward, never fabricate".**
  - An item becomes its entry, with `path` the squad-relative path it was found at. A file with
    no previous entry gains one. A file's own frontmatter replaces its previous entry.
  - `refs` and a legacy `extra.ref_kinds` map are stored exactly as the frontmatter spells them.
    No default ref kind is resolved and `fold_legacy_kinds` is not called. `Item.from_frontmatter`
    requires a default kind, and `tests/meta/test_from_frontmatter_call_sites_stay_enumerated.py`
    pins its three call sites: add a fold-free constructor beside it in `_models/_item.py` rather
    than a fourth call with an invented kind.
  - A timestamp the file does not carry keeps its previously indexed value.
    `_carry_forward_indexed_timestamps` and `_fold_stem_into_floor` in `_services/_maintenance.py`
    already do this and take no spec: move them where both modules can import them, do not copy
    them. The file-name parse needs a spec-free form (`_stem_digit_run` strips a spec prefix).
  - A previous entry is dropped only when no file sits at its recorded path and no file on disk
    claims its sequence number. It is reported as **missing**, and the run continues.
  - A candidate that cannot be given an entry of its own is reported as **unindexable**, with its
    cause, and its previous entry is carried forward unchanged, found by path and then by the
    number in its file name. The causes: bytes that do not decode; a read the OS refuses;
    frontmatter that does not parse; an identity that cannot be established (a previously indexed
    file whose `id` is gone or malformed, or a required field missing or type-invalid); an id two
    files claim (both files are named, and no winner is picked). Either way the digits in its
    file name raise the counter and padding floors.
  - The result keeps **missing** and **unindexable** apart, beside what was newly indexed.
- **Write.** One `store.overwrite(db)`. `db.schema_version` is the version passed in (the
  corpus's own), `counter` is the higher of the previous counter and the highest number seen,
  `padding` the higher of the previous padding and the widest file-name digit run, and
  `squads_version` is carried from the previous index, else from `.squads.toml`. No item file is
  written.

**Approach: the call, and the refusal**

- In `MaintenanceMixin.run_pending_migrations`, when at least one runner applies, call the
  routine with `self.paths.config.schema_version` before the first `m.run(...)`. When no runner
  applies nothing is reconciled, so `sq migrate up` on a current squad stays a no-op. There is no
  test of whether the index looks stale.
- **Then refuse before the first runner when the result holds any unindexable file.** One
  `SquadsError` naming each file by its squad-relative path with its cause, and as remedy only
  this: correct the file, or take it out of the squad directory, then re-run `sq migrate up`.
  The index, with the carried entries, has been written; nothing else has.
- A runner's own skips are untouched: a runner that visits an item and declines to act on it
  still reports it by id, on a run that completes.
- **Report.** `MigrationRun` carries the result. `migrate_up` prints one line for it only when
  something was indexed or dropped as missing. The `migrate` reflog line gains one key carrying
  the same counts and ids, because the trailing `repair()` compares against the reconciled index
  and so no longer sees an entry the reconcile already dropped. No reflog op is added. A run that
  stops after the reconcile says in its refusal what the reconcile indexed and dropped.
- `migrate_up`'s docstring describes exit code 1 as "migrated, but the trailing repair carried an
  unreadable file forward". Restate what exit 1 means now.
- The trailing `repair()` call and its docstring are untouched. `sq repair` gains no mode or flag.

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
  entry rule it exercises and which of the three result sets, if any, the file lands in.
  - Index state: consistent with the files; missing; not JSON; JSON that fails the model; an
    entry with a type the spec lacks; an entry with a status the spec lacks; no entry for a file
    on disk; an entry whose file is gone; an entry at an old path with the file at a new one; an
    entry with a stale field value.
  - File shape: parses; undecodable bytes; a read the OS refuses; malformed YAML; an item-shaped
    name with no frontmatter at all, or with its `id` line gone, each with and without a previous
    entry; an `id` with no `sequence_id`; no `created_at` or `updated_at`; two files with one id,
    same slug and different slug; a hyphenated prefix; a slug that starts with digits; a file in a
    folder no bundled type declares; a legacy `extra.ref_kinds` map.
  - Not items, nothing reported: a memory note, a board notice, a slug-named skill file; and,
    with the squad directory at the project root, unrelated markdown elsewhere in the tree whose
    name lacks the item shape (with and without an `id` key), and whose name has it but whose
    frontmatter is absent or carries an `id` of another shape.
  - The boundary of that rule, pinned as its own row: unrelated markdown at the project root
    whose name and `id` both have the item shape is an item by this rule. It is indexed when it
    carries what an entry needs and reported unindexable when it does not.
- **Pipeline invariant (convergence).** For every fixture under `tests/fixtures/corpus/`, under a
  frozen clock: the routine alone reports nothing unindexable and leaves the set of indexed
  sequence numbers and paths equal to the fixture's own index, and `sq migrate up` ends with
  every file and the index identical to what it produces with the routine stubbed out.
- **Pipeline invariant (the stamp).** Over every unindexable row, on a file a runner reads and on
  one no runner reads: `sq migrate up` exits 1, the schema stamp is unchanged, no item file has
  changed (hash), the file is named with its cause, and the output names no `sq` command but
  `sq migrate up`. After the named file is corrected by hand, or moved out of the squad
  directory, a re-run completes.
- **Service test:** `run_pending_migrations` over each index-state row completes and every
  eligible item is migrated, including the one the index did not know; over each unindexable row
  it raises before any runner is called (patch the registry to count calls).
- **CLI test:** `sq migrate up` exits 0 on the missing-index and not-JSON rows and prints the
  reconcile line; it prints no such line on a consistent squad; the reflog's `migrate` line
  carries the dropped id on the entry-whose-file-is-gone row.
- `tests/cli/test_migrate_up_bare_subprocess_exit_parity.py::test_migrate_up_exits_non_zero_bare_on_an_unreadable_file`
  pins the behaviour reversed here (migrated, stamped, exit 1, "carried forward as-is"). Rewrite
  it to the refusal and name it in the handoff.
- `sq migrate up` on a squad already at the current schema writes nothing (index hash unchanged).
- **Falsify, and record the test that went red for each:** remove the reconcile call from
  `run_pending_migrations`; stamp `SCHEMA_VERSION` instead of the passed version; route the parse
  through the folding constructor with the spec's default kind; drop an entry when its file fails
  to parse; remove the unindexable refusal (the stamp invariant goes red); recognise an item by
  an `id` key alone (the project-root rows go red).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Drive migrate up end to end over mismatched squad shapes

<!-- sq:subtask:ST3:body -->
**Goal.** Prove the whole path on real mismatched squads, through the installed CLI entry point,
with the operator's position asserted after every command and never only an exit code.

**Approach**

- One integration module (name it for the behaviour, for example
  `tests/integration/test_a_behind_schema_squad_can_always_migrate_or_is_told_why.py`), built on a
  helper that makes a pre-migration squad: initialise, create two milestones and a task, delete
  the roll-up tag line from both milestone files, stamp `schema_version = "0.14"` in
  `.squads.toml`. Each row then applies one mutation to that squad. Rows that need an older stamp
  start from the aged fixtures under `tests/fixtures/corpus/`.
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
| entry whose file is gone | delete one milestone file | exit 0; the other is tagged; the gone one is reported missing and is on the `migrate` reflog line |
| rename interrupted | move a file to a new slug, leave the index | as clean, at the new path |
| squad directory at the project root | `squad_dir = "."`, plus unrelated markdown with and without an `id` key | as clean; none of the unrelated files is named |
| own type, several schemas behind | a valid override declaring a type, one item of it; stamped `0.11`, and `0.8` | as clean; the item keeps its type |
| override, consistent | an override that changes nothing the corpus uses | as clean |
| override, stale-index conflict | a consistent override, plus an index entry carrying a status no lifecycle declares | as clean |
| undecodable file | a task file overwritten with undecodable bytes | exit 1 before any item file changes, schema unchanged, file and cause named |
| frontmatter does not parse | in a task file; in a milestone file | the same, for both |
| one id in two files | copy a task file to a second name | the same; both files named |
| identity lost | delete the `id` line of an indexed task file | the same |
| read refused by the OS | make a task file unreadable | the same |
| override, real conflict | override drops the `task` type | exit 1 before any item file changes; the items and the override are named |
| override does not load | invalid TOML; a playbook override that fails | exit 1, index and item files unchanged, the file named |
| hand-edited status | task file set to `Triaged` | exit 1 before any item file changes |
| interrupted run | a runner patched to raise after its first write, then restored | first run exit 1 with the closing line, schema unchanged; second run as clean |
| ahead of the package | stamp `0.99` | exit 1, "upgrade the squads package", nothing written |
| ahead, with an override conflict | stamp `0.99`, override drops `task` | the same; the override is not mentioned |
| value ahead of the index | hand-edit a title | as clean, title kept |
| partial pass | tag one milestone by hand, bump its `updated_at`, leave the index | as clean; the tagged file is byte-identical afterwards |

The last two complete without the reconcile. They are regression rows and prove nothing about it
alone; the index-state rows are the ones the falsifications below must turn red.

**Acceptance**

- Every "as clean" row ends in the same state as the clean row: the same set of indexed items,
  both roll-up tags present exactly once inside the body region, `schema_version` current, and
  then `sq check` exits 0 and `sq list` runs.
- **No body is rewritten under the old schema.** For every row, hash each item file before
  `sq migrate up` and after the reconcile but before the first runner (patch the first runner to
  capture): the hashes are equal. Only runners and the trailing `repair()` change item files.
- **Every exit-1 row is recoverable or says why not.** Its output names no `sq` command the gate
  refuses in that state. Apply the remedy the message names by hand, re-run `sq migrate up`, and
  it completes. The two ahead rows are the exception, and their message says to upgrade the
  package.
- **The stamp is never written past a file.** In every exit-1 row from "undecodable file" to
  "read refused by the OS", the schema is unchanged and the index still holds the file's previous
  entry.
- **Gate rows, on the clean squad before migrating and on the ahead squad:** `sq repair`,
  `sq check`, `sq list`, `sq migrate repad 7`, `sq migrate rename-status task Draft Ready` and
  `sq migrate rename-type task guide` each exit 1 with the gate message for that direction and
  change no file; `sq migrate help` and `sq migrate chlog v0.14.0..v0.15.0` exit 0 in both.
- **Idempotence:** on every row that completes, a second `sq migrate up` prints "nothing to
  migrate" and leaves every file and the index byte-identical.
- **Pipeline invariant:** the final corpus of every completing row equals the clean row's final
  corpus, file for file, apart from the fields the row's own mutation changed.
- The undecodable and OS-refused rows reverse what the existing exit-parity test pins (migrated,
  stamped, exit 1). Review that test and `migrate_up`'s exit-code docstring against these rows
  and say in the handoff what each now asserts.
- **Falsify, and record the test that went red for each:** stub the reconcile out (the
  index-state rows go red); remove the unindexable refusal (the unreadable-file rows go red);
  drop `spec=` from a runner's `IndexStore` (the own-type rows go red); restore the
  `get_service()` build in `migrate_up` (the override rows go red); widen the gate exemption back
  to the whole group (the gate rows go red).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Run migrate up under the squad's vocabulary, checked up front

<!-- sq:subtask:ST4:body -->
**Goal.** `sq migrate up` runs under the vocabulary the squad declared, or not at all. A
workflow override can no longer veto it on the strength of an index it is about to rebuild, and
a corpus that cannot fit the vocabulary is refused once, before any runner writes.

**Defect.** `migrate_up` (`src/squads/_cli/_migrate.py`) builds through `get_service()`. For a
squad carrying `.overrides/workflow.toml`, `bind_active_spec` has already run
`validate_against_index_fail_closed` against the live index in the root callback, and
`_build_plain_service` re-raises that cached refusal. So `sq migrate up` exits 1 before any
runner, with a message that recommends `sq workflow lint` twice (its closing line, and the cause
it quotes), which the gate refuses. Building the service without the cross-check is necessary and
not sufficient: the same squad then fails one layer down, in the first runner that opens the
index, with `item TASK-23 has type 'task', which the active spec no longer declares; migrate or
re-type this item ... (or run sq repair ...)`. And without any override, a hand-edited status
lets every runner write before the trailing `repair()` refuses it, with the schema unchanged.

**Approach**

- **Build.** `migrate_up` builds through `get_service_bypassing_index_cross_check()`
  (`src/squads/_cli/_common.py`), which falls back to the merged spec from `load_workflow_spec`
  with no index cross-check.
- **No bundled substitute for this caller.** `_build_bypass_fallback_service` ends by
  substituting the bundled spec when the override does not load at all. That suits `sq repair`
  at the current schema and is refused here. Give the accessor a keyword for it rather than
  writing a third accessor.
- **One resolution, before the first write.** Resolve the workflow spec and the playbook
  together when the service is built; that resolution is the one handed to every runner.
  `_build_bypass_fallback_service` builds `Service(sp, spec=merged_spec)` with no playbook, which
  silently leaves the bundled playbook on the service: for this caller it must pass
  `resolve_playbook(merged_spec, sp.squad_dir)` as `open_service` does. A workflow override or a
  playbook override that does not load stops the run there, before the reconcile: neither the
  index nor any item file has been written.
- **Its refusal** names the file and the loader's own cause, and as remedy only this: correct
  the file, then re-run `sq migrate up`. Compose it from the loader's exception. It may not go
  through `spec_refusal`, whose closing line names `sq workflow lint`.
- **One vocabulary check, after the reconcile and the unindexable-file refusal, before the first
  runner.** The index now mirrors the frontmatter, so what the check reports is a fact about the
  corpus and not about a stale entry. `run_pending_migrations` runs `validate_against_index`
  (`src/squads/_workflow/_loader.py`, the list-returning form) on the reconciled index under the
  run's spec, with or without an override, and on any mismatch raises one `SquadsError`. Nothing
  but the index has been written.
- **Its bound: it refuses only what the completed run would refuse**, the families the load
  boundary refuses at the current schema and no more: a type, a status, a sub-entity status, a
  prefix or folder against a type that has items, a badge code. It is not part of the reconcile,
  which stays blind. Its docstring says, in one sentence, that a runner which renames or retires
  vocabulary declares the names it consumes on its migration record and the check is blind to
  them. No shipped runner does, so no such mechanism is built now.
- **Its refusal** names the offending items, the override path when there is one, and as
  remedies only these: restore the declaration in the override, or correct the named frontmatter
  by hand, then re-run `sq migrate up`. It may not carry the "run `sq workflow lint`" the
  fail-closed cause embeds, nor `rename-type` or `rename-status` as later steps.
- **The trailing refusals stay.** What cannot be seen before the runners is still refused by the
  trailing `repair()`; composing that remedy for a squad still behind is the remedies subtask.
- On a squad ahead of the package none of this runs: the gate refuses `up` before a service is
  built. `migrate_up`'s own ahead check may stay as a second line.
- `sq repair`, `sq check` and every other caller of `get_service()` are unchanged: at the current
  schema the cross-check, the bundled fallback and their wording stay as they are.

**Acceptance**

- **Shape families, one table, each row driven through `run_pending_migrations` and through the
  CLI**, asserting exit code, message, the schema stamp, the index hash where the row says the
  index is untouched, and the hash of every item file:
  - override present and consistent with the corpus: completes;
  - override declaring a type of its own with one item of it, stamped 0.14: completes;
  - override conflicts only with a stale index entry (the file's own value is declared):
    completes, because the reconcile removed the conflict;
  - override drops a type the corpus uses; drops a status it uses; drops a sub-entity status it
    uses; re-prefixes or re-folders a type that has items; shrinks a badge collection a stored
    value names: refused before any item file changes, schema unchanged, items and override path
    named;
  - no override, one file hand-edited to an undeclared status; to an undeclared type: refused
    the same way, and no milestone file has been written;
  - workflow override that is not valid TOML; valid TOML that fails spec validation; a playbook
    override that fails to load beside a valid workflow override: refused before the reconcile
    (index hash unchanged), message names the file that failed and the loader's cause.
- In every refused row the output names no `sq` command other than `sq migrate up`, and in
  particular not `sq workflow lint`, `sq repair`, `sq migrate rename-type` or
  `sq migrate rename-status`.
- After the remedy in the message is applied by hand, re-running `sq migrate up` completes, for
  every refused row.
- **Pipeline invariant (the bound):** every row the check refuses is also refused, later, with
  the check stubbed out; and every fixture under `tests/fixtures/corpus/` still migrates to the
  current schema with the check in place.
- `sq repair` on a current-schema squad whose override does not load still falls back to the
  bundled spec as it does now (the existing bypass tests stay green, and one row pins it).
- **Falsify, and record the test that went red for each:** switch `migrate_up` back to
  `get_service()`; let the bundled fallback through for this caller; route the load refusal
  through `spec_refusal`; remove the pre-runner check and watch the "no item file changed"
  assertion fail on the hand-edited-status row.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Let only migrate up, help and chlog past the gate, by direction

<!-- sq:subtask:ST5:body -->
**Goal.** On a squad whose schema differs from the package's, the gate lets past
`sq migrate up` when the squad is behind, and `sq migrate help`, `sq migrate chlog` and `--help`
in both directions. Nothing else, and each of those by a capability it declares.

**Defect.** `require_current_schema` returns early for `subcommand == "migrate"`, and in the root
callback `ctx.invoked_subcommand` is the group name, so all six commands under `sq migrate` are
exempt, in both directions.

- `sq migrate repad` globs by the active spec's folders and prefixes, renames every item file,
  and ends in `repair()`, the full sweep, ahead of every pending runner.
- `sq migrate rename-type` and `rename-status` resolve their arguments in the active spec,
  rewrite frontmatter (ids, file names and referencing files too, for `rename-type`), and append
  a comment to each body.
- All three run on a squad behind the package and on one ahead of it, and each closes with
  `run sq check to verify integrity`, which the gate refuses.
- On a squad ahead of the package that also carries an override the corpus conflicts with,
  `sq migrate up` prints the override refusal, with `sq workflow lint`, because it builds a
  service before it looks at the direction.

**Approach**

- **Declare the capability on the command, never in a tuple.** A small marker (a decorator in
  `src/squads/_cli/_common.py`, applied in `src/squads/_cli/_migrate.py`) that names the ground
  the command gets past the gate on and the directions it covers:
  - `migrate_up`: it is the migration; behind only;
  - `migrate_help`, `migrate_chlog`: they read the package's own registry and touch no squad
    state; behind and ahead.
  No command holds the licence as a ground today (the reconcile is a routine, not a command).
- **One refusal, two call sites.** The root callback keeps gating every other group as it does
  now. A callback on `migrate_app` reads its own `ctx.invoked_subcommand`, looks up the resolved
  command's marker, and applies the same refusal function with the same two messages (behind:
  run `sq migrate up`; ahead: upgrade the squads package) when the marker is absent or does not
  cover the squad's direction.
- **On a squad ahead of the package the gate refuses `up` itself, before a service is built**,
  so the answer is "upgrade the squads package" and never an override refusal. `migrate_up`'s own
  ahead check may stay as a second line; it is not the mechanism.
- `--help` keeps bypassing the gate everywhere, as it does now.
- A command added under `sq migrate` without a marker is refused on a mismatched squad.
- At an equal schema nothing changes for any command.

**Acceptance**

- **Pipeline invariant, as a meta-test, per direction:** walk the registered command tree (every
  top-level command and group of `app`, and every verb of `migrate_app`). For behind and for
  ahead, the set of commands that get past the gate equals the set whose marker covers that
  direction: behind `{migrate up, migrate help, migrate chlog}`, ahead
  `{migrate help, migrate chlog}`. The expected sets are read from the markers; the two literal
  sets are asserted once, so adding a marker is a visible change to that one assertion.
- **Shape families, one parametrised CLI table:** schema direction (behind, ahead, equal) by
  command (`migrate up`, `migrate help`, `migrate chlog`, `migrate repad`, `migrate rename-type`,
  `migrate rename-status`, and three ordinary commands: `list`, `repair`, `check`) by invocation
  form (bare, with `--help`, with `--dir` pointing at the squad from outside it) by override
  state (none; a valid one; one the corpus conflicts with; one that does not load). Each row
  asserts the exit code, which of the two gate messages is printed if any, and, for every refused
  row, that no file under the squad directory changed (hash before and after).
- The row that drives the ahead ruling: ahead, `migrate up`, with a conflicting override and with
  one that does not load. Exit 1, "upgrade the squads package", and no mention of the override or
  of `sq workflow lint`.
- Equal-schema rows prove nothing regressed: the three writing verbs still do their work.
- Outside a squad (no `.squads.toml`) the migrate verbs behave as they do now.
- A service-level test is not applicable to the gate itself (it lives in the CLI layer); the
  services behind `repad`, `rename_type` and `rename_status` are untouched and their existing
  tests stay green.
- **Falsify, and record the test that went red for each:** remove the marker check from the
  `migrate_app` callback (the behind and ahead rows for the three writing verbs go red); widen
  `migrate_up`'s marker to both directions (the ahead rows and the meta-test go red); add a
  marker to `migrate_repad` (the meta-test goes red).
- Handoff names the adopter-visible change: three commands that ran on an out-of-date squad now
  refuse, `docs/migration.md` says otherwise, and the order an adopter follows instead (migrate
  first, then run them; ahead, upgrade the package).
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Open every runner's index under the run's resolved vocabulary

<!-- sq:subtask:ST6:body -->
**Goal.** Every runner reaches the index, and every other vocabulary question, under the one
spec and playbook the run resolved. No runner resolves its own, and none falls back to the
bundled vocabulary by leaving a spec out.

**Defect.** `Migration.run` takes `SquadPaths` only, so each runner that needs vocabulary finds
it for itself, and three do not:

- `src/squads/_migrations/_v0_4_to_v0_5.py` and `_v0_8_to_v0_10.py` each build
  `IndexStore(paths.index_path, paths.lock_path)` to allocate skill ids;
- `_v0_11_to_v0_14.py` does so twice, once to load the roster projection and once to allocate,
  although it has the squad's merged spec in hand at both places.

`IndexStore` with no spec validates every load under the bundled vocabulary. A squad stamped
0.11 or 0.8 whose valid `.overrides/workflow.toml` declares a type of its own, with one item of
that type, is therefore refused by `sq migrate up`: `item INC-24 has type 'incident', which the
active spec no longer declares; migrate or re-type this item ... (or run sq repair ...)`. The
same squad stamped 0.14 migrates (the newest runner passes its spec), and so does a squad
stamped 0.11 without the override. Custom types have existed since long before those schemas,
so this is an ordinary adopter squad that cannot upgrade.

The two newest runners also resolve the spec and the playbook a second time each (`_active_spec`,
`_active_playbook`), apart from the service that is running them.

**Approach**

- `Migration.run` (`src/squads/_migrations/_registry.py`) takes one frozen context value
  carrying `SquadPaths`, the resolved `WorkflowSpec` and the resolved `PlaybookSpec`.
  `MaintenanceMixin.run_pending_migrations` builds it once from `self.paths`, `self.spec` and
  `self.playbook` and hands the same value to every runner.
- `_wrap_sync` and `_wrap_async` keep adapting the runners that only walk files: their
  `migrate(paths)` signature and their direct tests stay as they are.
- The four runners that open the index take the context, and every `IndexStore(...)` they build
  passes `spec=`. The two newest read the spec and playbook from the context; `_active_spec` and
  `_active_playbook` go from both modules.
- The trailing `repair()` already runs on `self.spec`; nothing changes there.
- Nothing a runner writes changes: this alters which vocabulary a load is validated under, and
  where a spec comes from, and no byte of output for a squad that migrates today.

**Acceptance**

- **Shape families, one table over (stamped schema) by (what the override alone declares),
  through `run_pending_migrations` and through the CLI.** Schemas: stamped 0.8 and 0.11, which
  between them meet all the runners a squad with a type of its own can meet, and 0.14 as the
  control, built from the aged fixtures under `tests/fixtures/corpus/`. The second axis is the
  family the store's load validates, each declared only by a valid override and carried by one
  item: a type; a status on a bundled lifecycle; a sub-entity status; a badge code; plus no
  override, and a valid playbook override beside the workflow one. Every row completes, reaches
  the current schema, and the item is still indexed with its own value afterwards.
- **Pipeline invariant:** for every fixture under `tests/fixtures/corpus/` with no override,
  under a frozen clock, every file and the index after `sq migrate up` are identical to what the
  same run produces before this change (capture the expected tree first, as a golden or by
  running the unchanged registry).
- **Static guard under `tests/meta`:** in every module under `src/squads/_migrations/`, each
  `IndexStore(...)` construction passes `spec=`, and no runner module calls `load_workflow_spec`,
  `load_playbook`, `bundled_spec` or `get_playbook_spec`. Prove the scan sees a planted violation
  before trusting its pass.
- The context is built once per run: a test counts spec and playbook resolutions across a chain
  of several runners and finds none inside a runner.
- Service test and CLI smoke test as the table's two drivers; the CLI row for the stamped-0.11
  custom-type squad asserts exit 0 and the new schema stamp.
- **Falsify, and record the test that went red for each:** drop `spec=` from one `IndexStore`
  call in the 0.11 to 0.14 runner (the custom-type row at 0.11 and the static guard go red); put
  `_active_spec` back in the newest runner (the static guard and the resolution count go red).
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
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
- [2026-10-09T20:28:12Z] Olivia Lead:
  - 2026-10-09: brought into line with ADR-955 as amended (A1 to A7) and confirmed by op-pierre, working from the architect's list above. Body and ST1 to ST5 rewritten, ST6 added, summary updated. Still Draft and unassigned; no developer briefed. Code read at `d07b0e50` (no source change since the first draft).
    
    **Per subtask**
    - ST5 (A1): the capability names its ground and its directions; `up` behind only, `help` and `chlog` both; the gate refuses `up` on an ahead squad before a service is built; the meta-test binds the set per direction; the table gains the override axis and the ahead-with-conflict row.
    - ST2 (A2, A3, A4): recognition by file-name shape and `id` shape, with the project-root rows; unindexable files are a refusal before the first runner, kept apart from "missing" in the result; the pinned exit-parity test is rewritten. The scope wording about which runners enumerate from the index is corrected.
    - ST4 (A5, A6): one resolution of spec and playbook before the first write; the check bounded to what the completed run would refuse; both remedy texts pinned, with `spec_refusal`, `sq workflow lint` and the rename verbs excluded.
    - ST1 (A7): permitted set read from the capability, runs scoped to "stamp unchanged"; `skew_message` and the three closing "run `sq check`" recorded as depending on ST5; the `allocate_id` capacity refusal added; the second error in the 0.14 to 0.15 docstring added.
    - ST3: the unreadable-file rows, the own-type rows at 0.11 and 0.8, the project-root row and the ahead-with-conflict row added; the two rows that complete without the reconcile marked as regression rows only.
    - ST6 (new, A5): every runner reaches the index under the run's resolved spec and playbook.
    
    **Calls that were mine**
    1. **The custom-type defect is fixed here, in ST6.** The amended decision obliges it of this work, ST4's check would otherwise pass that squad for a runner to refuse mid-run, and ST3 cannot prove the path without it. It is first in the build order and depends on nothing else, so it can be lifted out unchanged if it has to ship ahead of the rest. Re-driven: stamped 0.11 and 0.8 refused, stamped 0.14 and the no-override control migrate. Custom types shipped in 0.6.0, so this is an ordinary adopter squad.
    2. **An override that does not load is refused before the reconcile**, so not even the index is written.
    3. **The reflog suggestion is taken**, as a key on the `migrate` line, because the trailing repair compares against the reconciled index and would no longer record an entry the reconcile dropped.
    4. **The frozen-literal runners (0.1 to 0.2, 0.2 to 0.3, 0.5 to 0.7, 0.7 to 0.8) are left out.** A squad already stamped past them can only be caught up by a new runner, which is a different piece of work and wants a drive and a bug first.
    
    **Found while re-driving**
    - A4's note that frontmatter which does not parse "already stops the run" holds only for a file a runner reads. In a task file it is stamped past with exit 1, like undecodable bytes. The ruling covers both; the body's reproduction table has both rows.
    - The bypass builder passes no playbook, so a service built that way carries the bundled playbook even when a playbook override exists. ST4 names it.
    
    **One thing to weigh, not blocking.** With the squad directory at the project root, another tool's file whose name and `id` both have the item shape (an `ADR-0007-x.md` carrying `id: ADR-0007`) is an item by the A2 rule and, lacking squads' fields, stops `sq migrate up` under A4, where "take it out of the squad directory" is not available. ST2 pins that as its own row so it is one line to change.
    
    Build order: ST6, ST2, ST4, ST5, ST1, ST3. @manager
- [2026-10-11T20:16:02Z] Catherine Manager:
  - Promoted to Ready and dispatched on the operator's go of 2026-10-11. Built in two passes by one developer: the first subtask in the build order (every runner's index opened under the run's vocabulary, which fixes BUG-988) is built and reviewed alone, then the rest.
- [2026-10-11T20:26:25Z] Elias Python:
  - @manager ST6 built and set Done; uncommitted in the working tree for review.
    
    Design: new frozen `MigrationContext(paths, spec, playbook)` in `_migrations/_context.py`. `run_pending_migrations` builds it once from self.paths/self.spec/self.playbook and passes it to every `Migration.run`. `_wrap_sync` unwraps `ctx.paths` for the file-walking runners (their `migrate(paths)` and direct tests are unchanged). The four index-opening runners (0.4-0.5, 0.8-0.10, 0.11-0.14, 0.14-0.15) now take the context; every IndexStore they build passes `spec=ctx.spec` (0.11-0.14 passes the spec down to `_live_roster` and the seeding loop). `_active_spec`/`_active_playbook` are gone from both newest runners.
    
    Tests: table of 5 sources (corpus 0.8/0.11/0.14, fresh-built 0.4/0.8 so the 0.4 and 0.8 allocation paths really run) x 6 families (type, status, sub-entity status, badge code, none, type+playbook override), each through the service and through `sq migrate up`: 60 green. Pipeline invariant: committed digests of the migrated tree per corpus (captured on the unchanged code first, reflog excluded), 12 green. Resolution count: one shared context, zero resolver calls inside any runner. Static guard in tests/meta (planted violations proven).
    Falsified: dropped spec= from the roster load in 0.11-0.14: 41 red (every override row at 0.4/0.8/0.11, service and CLI, plus the static guard; 0.14 and none rows stay green). Put `_active_spec` back in the 0.14-0.15 runner: the static guard and the resolution count red.
    
    Subtask vs code: (1) the shipped corpus 0.8 and 0.11 fixtures never reach the 0.4-0.5 or 0.8-0.10 allocation (no legacy skill file), so I added fresh-built squads stamped 0.4 and 0.8 to the table. (2) `_meta_compat.py` (frozen legacy reader used by the 0.1-0.2 and 0.2-0.3 walkers) calls `bundled_spec()`; the guard exempts it from the resolver half by name, since it is a helper not a runner. (3) `test_milestone_roll_up_tag_migration._downgraded` built a Service on the bundled spec and relied on the runner re-resolving the override; it now opens the Service under the override, as the CLI does.
    
    Adopter-visible: a squad stamped before 0.14 whose valid override declares its own type, status, sub-entity status or badge code now migrates with `sq migrate up` instead of being refused; no output byte changes for a squad that migrates today. Gates: pyright, ruff check, ruff format clean. Not run: the whole suite (yours).
- [2026-10-11T20:58:24Z] Catherine Manager:
  - From REV-995 F5, for ST3's table: add a row for a run that stops part-way on a squad stamped before 0.7 with any override, then is re-run. Today the seeding transaction writes the old index back with unresolved ids and every re-run is refused with a false cause; after ST2 and ST4 the re-run must complete.
- [2026-10-11T21:04:05Z] Elias Python:
  - @manager REV-995 findings F1 to F4 closed; tests and text only, no behaviour change; uncommitted.
    
    F1: the once-test now builds its Service under a workflow override and a playbook override and asserts the spec and playbook are not the bundled singletons before checking the context carries them. The table gains a built-0.11 source and the type-and-playbook family now declares a playbook entry whose role authors the squad's own type, then asserts the compiled CLAUDE.md line "authors **incidents**" for the built squads (stamped 0.4, 0.8, 0.11; the aged corpora register a different role, so the line is not produced there). Falsified as the reviewer did (bundled playbook in the context in run_pending_migrations): 7 red, the once-test and the type-and-playbook row at built-0.4, built-0.8 and built-0.11 in both the service and the CLI driver. Restored.
    F2: guard now flags a missing or literal-None spec, IndexStore used other than called directly, import-as and plain rebinding of IndexStore, and Service, open_service, resolve_playbook, get_active_spec, PLAYBOOK beside the four resolvers; scans recursively; the exemption is the one name bundled_spec in _meta_compat.py. Docstring says what it cannot see and that the behavioural table covers the existing runners. Each planted form is proven flagged.
    F3: the hash file is replaced by reviewed copies of every file the run adds or changes, as text, under tests/goldens/migrated_corpus/<corpus>/ with a REMOVED.txt per corpus. A mismatch prints a unified diff. Regenerate with UPDATE_GOLDENS=1 (the repo's existing switch). Docstring states it covers squads without overrides only. The copies were recorded from the current tree, which had already matched the earlier digests captured on the unchanged code.
    F4: CLAUDE.md line 169 (one line, outside the generated region) and the 0.5 to 0.7 docstring now state the two runner shapes.
    Also: first falsification count is 42 red, not 41. tests/_helpers.py imports are now under TYPE_CHECKING with the runtime ones local, matching the file's convention.
- [2026-10-11T21:36:29Z] Elias Python:
  - @manager F6 closed and ST2 built and set Done; uncommitted in the working tree.
    
    F6: a file several corpora write identically is stored once under tests/goldens/migrated_corpus/_shared and named in each corpus's SHARED.txt; a corpus keeps its own copy only of what differs (319 files down to 88). A mismatch prints a unified diff; UPDATE_GOLDENS=1 regenerates through one test. The reconstructed expectation equals the old goldens for all eleven corpora. Proof: one written field changed (author of the seeded skills in the 0.11 to 0.14 runner) turned 9 corpora red; one rendered line changed (a heading in the CLAUDE.md template) turned the same 9 red with the diff shown.
    
    ST2: new src/squads/_index/_reconcile.py (reconcile_index, ReconcileResult, Unindexable; takes the squad directory, the store and the corpus schema, no spec; imports nothing from the five vocabulary packages). run_pending_migrations calls it before the first runner whenever a runner applies, and stops with a SquadsError naming each unindexable file with its cause, the remedy being only correct or move the file and re-run sq migrate up, plus what the rebuild indexed and dropped. MigrationRun.reconcile carries the result; migrate_up prints one line only when something was indexed or dropped; the migrate reflog line gains delta.reconcile {indexed, missing}. Item.from_frontmatter_verbatim is the fold-free constructor beside from_frontmatter; INVENTED_WHEN_ABSENT moved to _models/_item.py; carry_forward_indexed_timestamps and fold_stem_into_floor moved into the new module and imported by _maintenance.
    Recognition: a name PREFIX-DIGITS-slug.md (prefix = hyphen-joined letter-led segments) and an id PREFIX-DIGITS; a missing sequence_id is read from the id. Walk skips dot-directories; a directory named like an item counts as a candidate so a refused read is reported. A name-shaped file whose frontmatter parses without a usable id is reported only when a previous entry stands for it (by path, then by file-name number only if that entry's own file is gone).
    Tests: tests/service/test_index_reconcile_entry_rules.py (index state x file shape, not-item rows, project-root boundary rows, content-neutral at three schemas, vocabulary-blind over five spec variants, convergence over every corpus), tests/integration/test_migrate_up_reconciles_before_the_runners.py (service and CLI: index states, refusal rows on a file a runner reads and one none reads, resume after fixing or moving the file, convergence with the routine stubbed, current schema untouched), tests/meta/test_index_reconcile_resolves_no_vocabulary.py.
    Pinned test rewritten: tests/cli/test_migrate_up_bare_subprocess_exit_parity.py, the unreadable-file test, now asserts the refusal (exit 1, schema and item files unchanged, file named with cause, only sq migrate up named). Also changed: two tests in test_milestone_roll_up_tag_migration.py that pinned a runner skipping an item whose file is gone; the rebuild now drops that entry first, so they assert it is reported as missing instead.
    Falsified (red tests): no reconcile call 38; stamp SCHEMA_VERSION 14; folding constructor 1 (legacy ref_kinds); entry dropped on unindexable 12 (the unindexable-carried table, duplicate-id rows, refusal-carries-entry); refusal removed 27 (service and CLI refusal rows, bare-subprocess test); id key alone 1 (the not-item table).
    Body vs code: the subtask puts the walk "under the squad directory" and says unreadable files are reported; a refused read is only reachable as a name-shaped directory under test, handled as above. An item lacking created_at/updated_at and any previous entry gets the loader's invented now, as repair does. A file whose id number disagrees with its sequence_id is reported unindexable.
    Adopter-visible: sq migrate up on a behind squad no longer stops on a missing, corrupt or stale index and no longer skips a file the index did not know; it prints "index reconciled with the files: indexed ...; dropped ..." when it changed anything; it refuses (exit 1, nothing migrated, schema unchanged) when an item file cannot be read, parsed or identified, or two files claim one id, naming each file and cause; the migrate reflog line has a reconcile key; with the squad directory at the project root, another tool's file whose name and id both look like an item and lacks squads fields now blocks the run.
    Not covered: no scratch-squad drive of a real aged project beyond the corpora; remedies elsewhere (ST1) and the gate (ST5) untouched. ruff check . also reports a long line in .claude/worktrees/agent-a240571530eba5b43 (another agent's worktree, not mine); src and tests are clean.
- [2026-10-11T21:42:51Z] Elias Python:
  - @manager the three ST2 suite failures are fixed (tests only; no source change).
    
    1. tests/cli/test_repair_corridor_message_and_exit_parity.py, migrate-up unreadable row: pinned that migrate up reuses repair's "carried forward as-is; fix the file" sentence. It now asserts the file is named, exit 1 (the parity that still holds with repair), "no migration has run" present and the repair sentence absent; the module docstring says migrate up shares the exit code but refuses before migrating, so its wording is its own. The repair, sync and adopt rows still pin the shared wording.
    2. tests/cli/test_milestone_roll_up_tag_migration_cli.py: the damaged milestone there is a deleted file, not an unparseable one. It was pinning "a runner skips an item it cannot read and carries on"; for a missing file the rebuild now drops the entry first, so the test (renamed) asserts the id is named as "dropped MILE-n", exit 0, schema 0.15, check clean. I added the other half: a milestone whose frontmatter does not parse exits 1, is named, says "no migration has run" and leaves the schema at 0.14.
    3. tests/service/test_type_invalid_frontmatter_load_boundary.py: the stand-in _boom now accepts **kwargs; the new keyword only keeps ref_kinds in the verbatim constructor path, so which errors from_frontmatter relabels is unchanged and the test again proves a KeyError escapes.
    Skip-and-carry-on pinned elsewhere: the full wide run found only these tests plus the two service milestone tests and the bare-subprocess test I rewrote earlier; no other test pinned it. The behaviour is gone for unreadable, undecodable and unparseable item files (all refuse); a file that is simply gone is dropped and named; a runner skip on an item it can read but cannot act on (moved tag, no body region) is unchanged.
    Wide run: every test file mentioning migrate up, run_pending_migrations, carried forward, skipped, from_frontmatter or unreadable, plus tests/meta, tests/integration, tests/cli, tests/service in one run: 4352 passed, 14 skipped, 0 FAILED. Gates (ruff with --exclude .claude/worktrees): pyright 0 errors, ruff check passed, ruff format clean.
- [2026-10-11T22:11:52Z] Elias Python:
  - @manager F8, F10, F11 and the code and tests of F13 are fixed; F7, F9, F12 untouched (walk, recognition and clash handling unchanged, their table rows kept). Uncommitted.
    
    F8: floors now move only for an item accepted by the routine (note() moved from reject/read into settle for the single accepted claimant). Rows: a table of four rejected shapes with huge file-name numbers (no type, malformed YAML, undecodable, id claimed twice) leaves counter and padding unchanged; a service-level and a CLI refused-then-fixed equivalence (the ADR-20240115 record from the finding: refused leaves 11/6, after the remedy the squad ends 11/6, equal to a first run on the fixed squad). Falsified (note() back in reject): 6 red - the CLI refused-run floor test, the CLI refused-then-fixed test, 3 of the 4 table rows, the service refused-then-fixed test.
    F10: run_pending_migrations appends a migrate reflog line (delta from_schema + reconcile {indexed, missing}) right after the index is written whenever something was indexed or dropped; the final migrate line no longer carries the key. Row: refuse, fix, complete, and the dropped TASK-3 is on exactly one migrate line, and sq reflog --json parses. The earlier dropped-id CLI test now finds the line by its key. Falsified (call removed): 2 red - that CLI test and the new stopped-run test.
    F11: entry_prefix/entry_name in the routine: a prefixless entry (index before ids were stored) takes its prefix from the recorded file name and is reported as e.g. TASK-3 (else its path); prior() uses entry_prefix. Rows on the 0.1 and 0.5 corpora: dropped entry is named TASK-3; a moved file that cannot be indexed keeps its entry. Falsified: naming back to entry.id 2 red; prior() back to entry.prefix 2 red.
    F13: the two skip texts (_cli/_migrate.py, 0.14 to 0.15 manual) no longer mention a missing file; the bare-subprocess docstring is corrected; the runner-skips-every-item case is back (one milestone with no body region, one with a moved tag: both skipped, zero changed, stamp 0.15) beside the missing-file test. docs/ lines remain for the writer.
    UPDATE_GOLDENS: the comparison rows are skipped while it is set, so only the regeneration test touches the folder.
    Wide run (every file mentioning migrate up, run_pending_migrations, reconcile, carried forward, skipped, from_frontmatter or unreadable, plus tests/meta, integration, cli, service): 4398 passed, 14 skipped, 0 FAILED. Gates: pyright 0 errors, ruff check passed, ruff format clean (excluding .claude/worktrees). No disagreement with the findings.
- [2026-10-11T22:19:04Z] Robert Architect:
  - 2026-10-12: ADR-955 rules on REV-995 findings 7, 9 and 12 (A8 to A10, under **Amendments — 2026-10-12**). What ST2 changes, for @tech-lead and @python-dev. Nothing below was driven by me; each expected outcome is from the ruling and is yours to prove.
    
    **Code, `_index/_reconcile.py` and its call site**
    - `reconcile_index` takes one more keyword: the declared locations, as plain pairs of squad-relative folder and prefix. `run_pending_migrations` builds them from the run's own spec (the one `MigrationContext` carries). The module still imports nothing that holds a spec, so the meta-test stands.
    - Locations are those pairs plus, for every previous entry, the directory and the file-name prefix of its recorded path. Parse the prefix from the path's file name, not from `entry.prefix`, which a pre-0.7 index does not carry.
    - `_candidates` stops walking the tree. It lists each location's directory, not recursively, and keeps the names `<that prefix>-<digits>-...` (prefix compared exactly). No other directory is listed.
    - In `_Scan.read`, the branch "no usable id, reported only when a previous entry stands for it" goes. At a location every candidate that cannot become an entry is rejected, entry or no entry.
    - Same-id detection widens inside location directories only: a markdown file there that is not named for an item is opened to read its `id`, and joins the duplicate group when an item carries the same one. Unreadable or id-less, it is left alone. This mirrors `_id_carriers`.
    - `settle` separates two cases: one id in two files ("is also claimed by") and one number under two ids ("number 15 is used by TASK-15 (path) and BUG-15 (path); the index holds one item per number").
    - `_unindexable_refusal`: the remedy reads "correct each file, or, when it is not one of the squad's items, move it out of the folder it sits in". For a shared number it gives the hand renumber: the next free number (counter plus one, printed), the file name, `id`, `sequence_id`, the references to the old id. It may add that the release the squad is stamped for can renumber it, naming the release, without printing a command to run here.
    - The module docstring and `test_a_new_item_file_is_indexed_wherever_it_sits` state the withdrawn rule; both invert.
    
    **Test rows through `sq migrate up`, each completing with exit 0, schema stamped, counter and padding as a squad without the file, the file byte-identical and named nowhere**
    - an archived milestone the index never held (`squads/archive/`, number 30);
    - a copy of an indexed item in `squads/archive/`;
    - a milestone moved by hand into `squads/archive/`: as above, plus its entry reported dropped as missing and absent from the final index;
    - squad at the project root: a `backup-2025/tasks/` copy, a nested fixture tree repeating the squad's ids, a lone `tests/fixtures/sample/tasks/TASK-000042-sample.md`, `docs/decisions/ADR-20240115-use-postgres.md`, `docs/lesson-2-verbes.md` in Latin-1, `docs/chapter-1-getting-started.md` with a non-YAML block;
    - `tasks/BUG-000050-x.md` carrying `id: BUG-50` (another type's prefix inside a type's folder, an id of its own);
    - no index at all beside the archived milestone: every item in the type folders indexed, the archive ignored.
    
    **Rows that stop before any item file changes, schema unchanged, and complete after the remedy**
    - at a location, never indexed: undecodable bytes, frontmatter that does not parse, frontmatter with no `id`;
    - the same three with a previous entry (entry carried forward);
    - one id in two files inside the type folders, including a second copy under a name that is not an item's;
    - a task and a bug sharing a number: the new cause, the printed next free number, and a re-run that completes after the hand renumber.
    
    **Kept as built**: a file with no entry in a folder the index knows gains one; a custom type's items are found through their entries and through the override's folder and prefix (add the row with no entry yet for that type); rename and retype interrupted between two locations.
    
    **Pipeline invariants over the whole table**: no run that reaches its first runner is refused by the trailing `repair` for where a file sits; no file on disk before the run appears in the trailing `repair`'s unreadable report. A shape that breaks either comes back to ADR-955. The eleven corpus fixtures still reconcile with nothing reported and migrate to the same result.
    
    **Changes to tests already written**: the vocabulary-blind table now holds the handed-in pairs constant, or asserts that different pairs change the index only by files found in a declared location the index did not know. The three rows of `test_a_file_that_cannot_be_indexed_is_reported_and_its_entry_carried` that pin a report for a look-alike outside the type folders invert. The reviewer's "backup copy or nested fixture tree is refused" becomes "ignored".
    
    **ST4, the check before the first runner**: add the row the reviewer asked for, which can now only come from the previous index: an entry whose recorded path is outside its type's declared folder, on a squad with no override. Refused before any runner, saying where the file is and where its type's items live, blaming no override.
    
    @manager ADR-955's discussion carries the two points for op-pierre's confirmation (the declared locations handed to the reconcile, and the refusal on a shared number); repeated here because an inbox lists open items only.
- [2026-10-12T04:49:42Z] Elias Python:
  - @manager third pass on ST2 (ADR-955 A8, A9, A10) built; F7, F9, F12 marked Fixed. Uncommitted.
    
    Module (_index/_reconcile.py): the tree is no longer walked. Locations = (directory, prefix) pairs from the previous index (directory and file-name prefix of each entry's recorded path, not entry.prefix) plus the declared pairs; only those directories are listed (not recursively), and only names with exactly that prefix are candidates. Everything outside is never opened, indexed, counted towards the counter or padding, or reported. The "no id, reported only if an entry stands" branch is gone: any candidate that cannot become an entry is rejected. Other markdown files in a location's directory (any name, any prefix) are opened only to read an id and join a duplicate group; unreadable or id-less ones are left alone. settle separates one id in two files ("is also claimed by") from one number under two ids (cause names the number, both ids, both paths, "the index holds one item per number"; Unindexable.shared_number). ReconcileResult carries the counter. Call site (_maintenance.run_pending_migrations): passes declared=[(folder, prefix)] from self.spec.items; the refusal remedy now reads "correct each file, or, when it is not one of the squad's items, move it out of the folder it sits in", and for a shared number adds the by-hand renumber (counter+1 printed; file name, id, sequence_id, references; the stamped release can also renumber; no command printed).
    The seam: _locations() in _index/_reconcile.py is the one place the declared pairs enter. The strictly blind alternative (no declared pairs; with no readable index, recognise every item-shaped file in the tree) is that function plus the declared= argument at the call site.
    
    Rows (all through the service and sq migrate up where stated; * = owed by the amendment, driven, all came out as the amendment expected):
    - ignored, completes, floors as a squad without it, file byte-identical, named nowhere: archived milestone the index never held, copy of an indexed item in archive/, backup-2025/tasks copy, nested fixture tree, lone tests/fixtures/sample/tasks file, ADR-20240115 record, Latin-1 documents and a non-YAML block (never opened asserted), tasks/BUG-50 with an id of its own*, and the trailing repair never refusing any of them and reporting nothing unreadable.
    - milestone moved by hand into archive/: file untouched, entry dropped and named, absent from the index, completes.
    - no index / corrupt index beside strays*: declared folders indexed, strays ignored, floors 11/6.
    - file with no entry in a known folder gains one; custom type found through its entries and through the declared pair (no entry yet); hyphenated prefix and digit-leading slug at a location.
    - refusals (schema unchanged, files hash-identical, resumes after the remedy): undecodable, unparseable, no id, no frontmatter at a location, never indexed and with an entry; one id in two files incl. a copy under a non-item name; task and bug sharing number 3: new cause, printed number 12, no renumber command, completes after the hand renumber.
    - agreement with repair*: repair reports the id-less file in a type folder and the copy under any name, and does not see another type's prefix inside a type folder (all three agree with the reconcile).
    Inverted rows (kept, flipped): test_a_new_item_file_is_indexed_wherever_it_sits (now at-a-location indexed / outside-every-location ignored); the look-alike rows (name-and-id item-shaped doc, shape with no frontmatter, id of another shape, id gone) now assert never opened; the no-frontmatter, id-line-gone, id-malformed shape rows now report without an entry; duplicate copies now live inside type folders; entry-at-an-old-path split into rename within a folder (path updates) and moved out of every location (dropped, named); the floor rows moved to tasks/. The vocabulary-blind table keeps the pairs constant; a new row shows different pairs change the index only by the file in the declared location.
    Falsified (red): tree walked again (A8) 50 red across the ignored/strays/repair-agreement/never-opened/moved-by-hand/no-index rows; reported-only-with-an-entry branch back (A9) 5 red (the never-indexed location rows and the shape table); the copy-detection reading only parseable ids (A9) 1 red; the shared-number case folded into "also claimed" (A10) 2 red. Refused-then-fixed equivalence and the counter rows from the last pass re-run green under the new rule.
    Nothing in the amendment failed when driven; ST4's out-of-folder-entry row is not built.
    Wide run (every file mentioning migrate up, run_pending_migrations, reconcile, carried forward, skipped, from_frontmatter or unreadable, plus tests/meta, integration, cli, service): 4455 passed, 14 skipped, 0 FAILED. Gates: pyright 0 errors, ruff check passed, ruff format clean (excluding .claude/worktrees). After the interruption I re-ran the reconcile files and tests/meta: 495 passed.
    Adopter sees differently: only the folders the squad keeps items in (from its index and its declared types) are read; an archive folder, a backup copy, a nested fixture tree or another tool's records at a project-root squad are ignored and never block the run, and an item moved by hand out of its folder is dropped from the index and named; a file named for an item in an item folder that cannot be read, parsed or identified stops the run (with or without an earlier entry), remedy: correct it or move it out of that folder; one id in two files in an item folder (any file name) stops the run; two ids sharing a number stop the run with the number, ids and paths named and a by-hand renumber spelled out.
- [2026-10-12T05:22:01Z] Robert Architect:
  - 2026-10-12: ADR-955 A11 withdraws A8's second source on the operator's decision. The routine stays blind. What changes in what is built, for @python-dev and @tech-lead. A9's rules at a location, A10 and every with-index row stand as built.
    
    **Code, `_index/_reconcile.py` and the call site**
    - `_locations()` loses `declared`, `reconcile_index` loses the `declared=` keyword, and `run_pending_migrations` stops passing pairs. Locations are the directory and file-name prefix of each previous entry's recorded path, nothing else.
    - With no readable previous index there are no locations: walk the tree (dot-directories skipped) and take every file with an item's name. One that parses with a well-formed `id` becomes an entry. One that parses without a well-formed `id` is passed over, since no entry can stand for it. One that cannot be read or parsed is rejected. Two files carrying one id are rejected wherever they sit. The any-name copy check (other markdown files opened for their id) stays a with-index rule; do not open every markdown file in the tree.
    - `ReconcileResult` says whether a previous index was read. The check before the first runner needs it for its cause, and the next rule needs it.
    - A run refused before its first runner with no readable previous index leaves no index behind: no file where there was none, the unparseable one untouched, no reflog line for an index that is not kept. Build then commit, or withdraw, is yours. With an index, a refused run keeps the reconciled index as now.
    - Remedy text when there was no readable index: restore the index (from version control, or with the index rebuild of the release the squad is stamped for, named, no command printed) and re-run; otherwise correct the file or move it out of the squad directory. With an index the remedy stays as built.
    - The module docstring and the vocabulary-blind meta-test go back to "nothing declared reaches the routine".
    
    **Rows that flip**
    - No index or corrupt index beside strays (was: declared folders indexed, strays ignored, floors 11/6). Now: the archived item is recognised; the run is refused before any runner by the check's first question, with the true cause; no item file changes; no index is left; a second run behaves the same; after the index is restored the run completes and the stray is never opened. Until that check exists this row ends in the strand REV-995 F7 found, so ST2 must not ship ahead of ST4's first question.
    - Custom type found through its declared pair with no entry yet (was: indexed). Now: not seen by the reconcile; refused before any runner by the check's second question; completes once the stamped release has indexed the file. The same row for the first item of a bundled type.
    - The vocabulary-blind table: the pairs column goes, the index bytes are identical under every vocabulary again, and the row "different pairs change the index only by the file in the declared location" is removed.
    
    **New rows owed, each through `sq migrate up`, all with no readable index**
    - a clean squad: completes, every item indexed, counter and padding as the files give them;
    - beside a look-alike document that cannot be read (project root): refused, no index left; completes after the index is restored;
    - beside another tool's numbered record with no `type`: refused, counter not raised, no index left;
    - beside a backup copy repeating an id: refused with both paths, no index left;
    - a parse-clean look-alike with no well-formed `id` (`RFC-2119-keywords.md`, `CVE-2024-1234.md`): passed over, run completes.
    
    **ST4, the check before the first runner, now carries the invariant**
    - First question: every entry of the reconciled index sits at a declared location (its directory is a declared folder and its file name carries that type's prefix). Otherwise refuse. Two causes: with a previous index, the file is where the index knows it and where no declared type lives (name the override only when the squad has one); with none, there was no readable index, so every item-shaped file under the squad directory was taken for an item, and these sit where no type lives.
    - Second question: every file named for an item at a declared location has an entry in the reconciled index. Otherwise refuse, naming the file. Remedy: move it out of the folder when it is not the squad's item; when it is, the release the squad is stamped for indexes it, then re-run.
    - Its refusals in the no-index state fall under "no index left behind".
    - Pipeline invariants over the whole table, unchanged in wording: no run that reaches its first runner is refused by the trailing `repair` for where a file sits, and no file on disk before the run reaches the trailing `repair`'s unreadable report. One known limit, to pin and not to fix: a copy under a name that is not an item's, in a declared folder the index has never held an item in.
    - Both questions pass over the eleven corpus fixtures.
    
    @manager ADR-955's discussion carries the cost of the decision in the no-index state and one point for op-pierre to reconsider; repeated here because an inbox lists open items only.
- [2026-10-12T05:39:36Z] Elias Python:
  - @manager A11 and ST4 built; ST4 set Done; F7, F9, F12 stay Fixed (a comment on each names the rule). Uncommitted.
    
    Reconcile (_index/_reconcile.py): the declared pairs are gone from _locations(), the signature and the call site. New plan_reconcile() builds the index without writing and returns (db, result); reconcile_index() is plan + write, for the tests. With a readable index a location is an entry's directory and file-name prefix, nothing else. With none the tree is walked (dot-directories skipped) and every item-named file is a candidate: a well-formed id makes an entry, a file that parses without one is passed over, an unreadable/unparseable one is rejected, a shared id is rejected wherever it sits; the any-name copy check stays a with-index rule. ReconcileResult.had_index says which state. A prefixless (pre-0.7) entry that is carried is given its prefix from its recorded name, so a written index no longer holds UNRESOLVED ids.
    Call site (_services/_maintenance.run_pending_migrations): with an index the rebuilt one is written first and the reflog line follows (as before); with none nothing is written until every check passes, so a refusal leaves no index (or the unparseable one untouched) and no reflog line. The unindexable refusal's remedy for the no-index state: restore the index (version control, or the index rebuild of the stamped release, named, no command printed), or correct/move the file out of the squad directory.
    ST4: new _services/_corpus_fit.py, run after the reconcile and the unindexable refusal and before the first runner. Question one (every entry sits at a declared (folder, prefix)) and question two (every file named for an item at a declared location has an entry) with the two causes and remedies A11 gives, then the vocabulary cross-check (validate_against_index under the run's spec, override hint dropped when there is no override). Override named only when the squad has one; remedies only hand fixes and `sq migrate up`. migrate_up now builds through get_service_bypassing_index_cross_check(bundled_fallback=False): no bundled substitute, an override or playbook override that does not load stops the run with the file and the loader's cause before the reconcile (index untouched), and the service carries resolve_playbook(...) (the trap); sq repair's accessor behaviour is unchanged (a row pins it).
    Seam: the declared pairs were the only thing the routine took; it now takes nothing. The check in _corpus_fit.py is where the spec lives.
    
    Flipped rows: no index beside strays (now recognised by the walk, refused before any runner by question one, no index left, second run identical, completes once the index is restored with the stray never opened); the first item of a bundled/custom type with no entry (not seen by the routine; refused by question two; completes once indexed); the vocabulary-blind table lost nothing but its pairs; the hyphenated-prefix, custom-type, archive and deep rows now sit under the no-index walk; the entry-less shape/duplicate/timestamp rows keep tasks/ a location through an anchor entry; "different pairs" row removed.
    New rows (all through sq migrate up unless stated; * owed by A11): no-index clean squad completes with 11 items, counter 11 / padding 6 (missing and corrupt)*; archived item, unreadable look-alike, another tool's numbered record, backup copy repeating an id: each refused before any runner, cause names "no readable index", no index left / unparseable one byte-identical, no reflog line, files unchanged, second run identical, counter 11 after restore*; RFC-2119-keywords.md / CVE-2024-1234.md passed over*; with an index: an entry where no type lives refused (override not named), unindexed first item of a bundled and of a custom type refused by question two and completing once indexed*; both questions pass over all eleven corpora and the trailing repair never refuses a run the checks let through, nothing unreadable (strays with an index); the known limit (non-item-named copy in a never-held declared folder) pinned. Vocabulary table (service + CLI, hand remedy then completes, only `sq migrate up` named, no item file changed, stamp unchanged): override drops a type, re-prefixes, re-folders, shrinks a badge collection a value names; no override with an undeclared status, type, sub-entity status; consistent overrides complete; override conflicting only with a stale entry completes; override with its own type and an item completes at 0.14; override not TOML, failing validation, playbook override failing beside a valid workflow one: refused before the index is touched, naming the file and cause; bound: each refused row is also refused later with the check stubbed. F5: both routes (pre-0.7 squad with an override and a hand-edited status; and with an unreadable bug file) now stop once, leave no UNRESOLVED ids, and the re-run after the fix completes - so ST2+ST4 do remove F5; ST3 still owes its table row.
    Did not survive driving: dropping a status through an override cannot be built (the override does not load while a lifecycle uses the status), so that family is covered by the hand-edited status rows; after the first refusal with an index the rebuilt index has already dropped an entry whose file was moved by hand, so the remedy for a misplaced file also needs its entry rebuilt (the message says so, naming the stamped release). Otherwise A11 and A6 held as written.
    Falsified (red): routine no longer walks with no index 31; always walks 58; index kept on a no-index refusal 8 (stray refusal rows); question one removed 7; question two removed 4; vocabulary check removed 8 (undeclared status/type/sub-entity status, badge); migrate_up back on get_service() 8 (stale-entry, non-loading overrides, the pre-0.7 row, remedies); bundled fallback let through 2 (non-loading override rows).
    Wide run (every file mentioning migrate up, run_pending_migrations, reconcile, carried forward, skipped, from_frontmatter, unreadable, bypass, plus tests/meta, integration, cli, service, unit): 7052 passed, 14 skipped, 0 FAILED. Gates: pyright 0, ruff check passed, ruff format clean (excluding .claude/worktrees). sq check clean.
    Adopter sees differently: with no readable index the whole tree under the squad directory is read for item-named files, and a stray (archived item, backup copy, another tool's record, an unreadable look-alike) stops the run before anything is written, leaving the squad exactly as found, with the remedy to restore the index or move the file out of the squad directory; with an index, an indexed file where no type lives, or a file named for an item where a type lives with no entry, stops the run (remedy: move it, or have the stamped release rebuild the index); a corpus that does not fit the vocabulary the squad declares (undeclared type/status/sub-entity status, re-prefixed or re-foldered type, shrunk badge collection) is refused before any item file is written, with the items and the override named; an override or playbook override that does not load stops sq migrate up with the file and cause and without the old sq workflow lint advice, and sq migrate up no longer falls back to the bundled vocabulary; an index written before ids were stored no longer ends up with UNRESOLVED ids.
- [2026-10-12T06:23:33Z] Robert Architect:
  - 2026-10-12: ruling on REV-995 finding 17, recorded as a dated note in ADR-955 at A11. For @python-dev. Read, not driven; every row below is yours to prove.
    
    **The prefix grammar as the code has it.** There is none in the spec: `ItemSpec.prefix` is a bare `str`, and load checks it for uniqueness only. Three other readers each have their own idea: `prefix_from_id` (everything before the last hyphen), `_NAME_NUMBER` in `_duplicate_ids.py` (anything, then the first hyphen-digits), and `repair`'s scan (a glob on the declared prefix, literally). The reconcile's `_PREFIX` is a fourth and the narrowest.
    
    **The ruling.**
    - With an index, no pattern recognises a prefix. A location's prefix is the spelling the entry records: its id's prefix when the recorded file name starts with it, otherwise what stands before the entry's own number in that name. Files in the location's directory are matched against that spelling literally (spelling, hyphen, digits, then a hyphen and slug or the extension).
    - An `id` is well formed when the model's own parser reads a non-empty prefix and a number from it, not when `_PREFIX` matches.
    - With no index the walk keeps one shape, widened to word characters: hyphen-joined segments of letters, digits and underscores, each holding at least one character that is not a digit, the first segment of digits alone being the number.
    - The invariant does not rest on that shape. The second question of the check lists by each declared prefix exactly as declared (your fix in progress), so an item the walk misses is refused before any runner.
    
    **Code**
    - `_locations()` and `entry_prefix()` stop reading the prefix through `_NAME_RE`; they take the entry's spelling as above. `_scan_directories` matches candidates by literal prefix, not by the pattern.
    - `_identity_problem`, `_normalized` and `_ID_RE` use the model's id parsing.
    - `_PREFIX` widens as above and is used by the tree walk only.
    - In `_corpus_fit.py`, both questions compare by the declared spelling: the first question's `item_name_parts` test has the same gap as the second had.
    
    **Rows**
    - `MY_INC` and `2FA`, with an index: the entry is refreshed from its file; a second, unindexed item of the type in the same folder gains an entry; the run completes.
    - `MY_INC` and `2FA`, with no index: recognised by the walk; the run completes and the reconcile line names them.
    - A declared prefix outside the walk's shape (a dot in it, for instance), with no index: not recognised; refused by the second question before any runner, no index left; with an index, handled like any other.
    - The first question on an indexed `MY_INC` entry in its declared folder: passes.
    - Walk look-alikes under the wider shape (`my_notes-1-x.md`, `3d-2-models.md`): parse-clean without a well-formed `id`, passed over.
    - The eleven corpus fixtures and the hyphenated-prefix rows unchanged.
    
    @manager ADR-955's discussion has two points for op-pierre from this ruling: the wider walk shape, and the spec having no prefix grammar at all.
- [2026-10-12T06:34:36Z] Elias Python:
  - @manager F14 to F18 built, including the architect's ruling on F17; all five marked Fixed. Uncommitted.
    
    F14: new release_reading_schema(schema) in _migrations/_registry.py (the migration that introduced the schema, else the first release past it). The three refusals (no index, unindexed file, renumber note) now say "a squads release that reads schema vX (vY is one)"; squads_version is out of them. Rows: one per stamped schema 0.3, 0.4, 0.5, 0.7, 0.8, 0.10, 0.11, 0.14 asserting the named release is one whose migration has to_schema equal to the squad's schema, and that the fixture's last-sync 0.7.0 is not named. Red on revert: 7.
    F15: both questions compare posixpath-normalised folders and paths (declared folder, recorded directory, the paths the second question builds). Rows: trailing slash, ./, both, nested "ops/incidents/", each indexed and with no index, through sq migrate up. Red on revert: 8.
    F16: the check calls validate_against_index(..., alignment=has_override); the new keyword leaves out the prefix/folder alignment half. Without an override only the families the store's load refuses are asked; a hand-edited bug->task type migrates (sq check reports it) and no message names an override; the same edit with an override is refused naming it. A6 bound re-checked: every refused row of the vocabulary table is still refused later with the check stubbed out, and the rows the completed run accepts (consistent overrides, stale entry, own type, hand-edited type) complete. Red on revert: 1.
    F17 (ruling folded in): with an index a location's prefix is the entry's own spelling (entry_prefix: id prefix when the recorded name starts with it, else what precedes the entry's number in the name) and candidates match it literally (spelling, hyphen, digits, optional hyphen and slug, .md); ids are judged by the model's prefix_from_id/number_for_id; the walk shape is widened to word-character segments with at least one non-digit and used only by the walk; both check questions compare by declared spelling (first question: a declared (folder, prefix) matches the name literally; a name with no -digits shape in a declared folder still passes). Rows (all driven, all came out as the ruling reads): MY_INC and 2FA with an index (first refreshed from its file, second unindexed gains an entry, run completes); with no index (recognised by the walk, reconcile line names them, 12 items, completes); a dotted declared prefix (v1.0) with no index (refused by the second question, no index left) and with an index handled; the first question passes on an indexed MY_INC entry; my_notes-1-x.md and 3d-2-models.md passed over; the corpus fixtures and hyphenated-prefix rows unchanged. Red on revert: second question narrowed 11, walk shape narrowed 2, location prefix narrowed 18.
    F18: the misplaced-file remedy now reads "move each file into the folder its type lives in, then re-run" (the second refusal, question two, carries the other release); every refusal of the check appends "The index was rebuilt first (dropped ...; indexed ...)" when the kept rebuild changed something. I did this with the note in the message, not a separate printed line, so it is on screen with the refusal and in the same words as the unindexable refusal. Rows: moving back is enough when the folder holds another indexed item; the dropped note is shown. Red on revert: 2.
    Empty index: I left the routine alone (an index that parses is readable; changing it would change A11). The second question now says, when the index holds no items, that removing the index file lets the run read the tree instead (row). Say if you want the routine to treat it as no index.
    Wide run (every file mentioning migrate up, run_pending_migrations, reconcile, carried forward, skipped, from_frontmatter, unreadable, bypass, plus tests/meta, integration, cli, service, unit): 7082 passed, 14 skipped, 0 FAILED. Gates: pyright 0, ruff check passed, ruff format clean (excluding .claude/worktrees). sq check clean.
    No disagreement with the findings.
- [2026-10-15T18:22:18Z] Elias Python:
  - @manager ST1 and ST3 are Done and F5 is Fixed. Nothing is committed. `sq check` is clean. Pyright, `ruff check .` (source and tests) and `ruff format --check` on source and tests are clean; the one file ruff format flags in the repository is a copy under `.claude/worktrees/`, not mine.
    
    **ST1.** The earlier session had finished most of it, so I kept it. That covers the `rerun` keyword on `repair()`, `IndexFullError` with its composed refusal, the closing line, the docstrings, the gate grants and the four test files. What I added:
    - The inventory table, as a comment on ST1.
    - A row for two ref kinds declaring `role = "default"`. The override is refused at load, with a message that names only `sq migrate up`.
    - Three rows (hand-edited status, type and sub-entity status) that stub out the pre-runner check and make the 0.15 runner inert, so the trailing repair's vocabulary message is reached. Before this, nothing reached it, and the `rerun` keyword was not pinned at its call site.
    - A wrapped line in the `_store.py` docstring (E501).
    
    **ST3.** One module: `tests/integration/test_a_behind_schema_squad_can_always_migrate_or_is_told_why.py` (44 tests, 16 s). Everything goes through the Typer app, plus one real-subprocess test.
    - Completing rows (11 plus clean), each against a reference squad migrated without mutation:
      - Each row asserts: exit 0; stamp current; both roll-up tags exactly once inside the body region; item files byte-identical at the point just before the first runner (captured by wrapping `_pre_runner_refusal`); indexed set equal to the reference's; `sq check` and `sq list` exit 0; and a second `migrate up` says "nothing to migrate" and leaves every file and the index byte-identical.
      - The rows: index missing, not JSON, invalid for the model, stale undeclared status, file the index lacks, entry whose file is gone, interrupted rename, consistent override, override with a stale entry, value ahead of the index, partial pass.
    - Refusing rows (10): undecodable, bad frontmatter in a task and in a milestone, one id in two files, id lost, read refused by the OS, override dropping `task`, workflow override not TOML, playbook override not loading, hand-edited status.
      - Each asserts: exit 1; stamp unchanged; every `.md` byte-identical; the file and cause named; only permitted commands named; the previous index entry kept (unreadable family); the by-hand remedy followed by a re-run completes and `sq check` is clean.
    - Also: a stopped run resumed to the same corpus; ahead of the package (plain, and with a conflicting override that is not mentioned); the gate on behind and on ahead squads (6 gated commands exit 1 with the direction's message and change no file; `help` and `chlog` exit 0).
    - Aged squads:
      - Own-type override from 0.4, 0.8 and 0.11. Each starts from the fixture plus one unstamped legacy skill file, so the old runners open the index. The incident is kept as an incident.
      - Project-root squad with unrelated markdown, with and without an `id` key. None is named, and all are untouched.
      - F5: the 0.5 corpus, with and without a `[ref_kinds.mirrors]` override, stopped after each of the six later runners and re-run. All complete with no `UNRESOLVED` id.
    
    **F5 does not reproduce** on this tree. The original trigger (hand-edited status, caught by the trailing repair) is now refused before any runner, and a run stopped after a runner by any other cause resumes. No fix was needed.
    
    **Falsifications, recorded by the test that went red.**
    
    ST1:
    - Drop `rerun=` at the `run_pending_migrations` call: 3 red, `test_the_trailing_repairs_vocabulary_refusal_names_the_command_the_gate_permits[status|type|subentity-status]`. Before the new rows it was green, i.e. unpinned.
    - Capacity refusal unchanged: 1 red, `test_a_full_index_with_an_id_hungry_runner_pending_is_refused_without_repad`.
    - Closing line removed: 2 red, `test_a_runner_that_raises_leaves_the_squad_behind_and_a_second_run_completes[before-a-write|after-a-write]`.
    - Planted `run sq check` in a runner's `raise`: red, `tests/meta/test_a_migration_runner_never_raises_a_refused_command.py::test_no_runner_raises_a_refused_command_or_uses_the_skew_guard`.
    
    ST3:
    - Reconcile stubbed out: 19 red, across the completing and refusing tables.
    - Unindexable refusal removed: 5 red, undecodable, frontmatter, id lost, two ids and OS-refused.
    - `spec=` dropped from `IndexStore`:
      - `_v0_4_to_v0_5`: 1 red (the 0.4 row with an unstamped skill).
      - `_v0_8_to_v0_10`: 1 red (the 0.8 row with an unstamped memory skill).
      - `_v0_11_to_v0_14`: 3 red.
      - `_v0_14_to_v0_15`: 3 red.
      - Without the legacy skill file, the 0.4 and 0.8 runners never open the index and the rows stay green. That is why the rows carry it.
    - `migrate_up` back on `get_service()`: 3 red (override drops a type, workflow override not TOML, override with a stale entry).
    - Gate exemption widened to the whole group: 2 red (the gate test, behind and ahead).
    
    **Test run.** `tests/meta tests/integration tests/cli`: 2648 passed, 9 skipped. A keyword-selected sweep of the other directories (store, index, repair, allocate, gate): 327 passed. The full suite was not run.
    
    **Hand repeat.** I repeated three rows in a scratch squad under the session scratchpad, with the working tree's `sq`: gate refusal of `migrate repad 7` with no file changed; an undecodable task, refused with exit 1, schema 0.14; then the file restored and the index removed, which migrated, printed the reconcile line, and gave `nothing to migrate` on the second run.
    
    **Existing exit-parity test.** `test_migrate_up_bare_subprocess_exit_parity.py` had already been reversed. It asserts exit 1, file and cause named, schema stamp and item files unchanged, and only `sq migrate up` in the remedy.
    - `migrate_up`'s docstring is accurate. It lists the refusal exit and the partial-completion exit.
    - In ST3 the OS-refused and undecodable rows assert the same, plus the index entry kept.
    
    **Read, not driven, or inferred.**
    - The trailing repair's "no single default ref kind" refusal is unreachable (the load refuses first), so the row asserts the load message.
    - The store-load refusals remain worded for `sq repair`. They are unreachable from `migrate up` after the reconcile and the check; the invariant rows prove it for the shapes tried, nothing more.
    - After a with-index refusal for a hand-edited status the index keeps the rebuilt entry (`Triaged`). Only unreadable files keep the previous entry.
    - Generated skill ids and names (`SKILL-0000NN-*`) depend on the run's history. A resumed run can number them differently from an uninterrupted one. Resumed-run rows therefore compare the non-skill corpus, and `sq check` is clean.
    - `sq repair` on a behind squad with a broken override: the gate refuses it before any spec text. Not a `migrate up` remedy, so out of scope.
    
    **Adopter-visible messages whose wording changed (for the tech writer, F13).**
    1. New closing line on any `SquadsError` leaving a runner or the trailing repair in `sq migrate up`: "The squad is still at schema vX: fix the cause, then re-run `sq migrate up`, which rebuilds the index from the files first."
    2. New full-index refusal in `sq migrate up`: "the index is full: all N ids at padding P are used up, and a pending migration needs another. Widen the padding with a squads release that reads schema vX (vY is one), then upgrade and re-run `sq migrate up`. The schema is unchanged." It no longer names `sq migrate repad`.
    3. The trailing repair's three unknown type/status/sub-entity-status messages end "fix the frontmatter before running `sq migrate up`" when reached from `migrate up`. `sq repair` keeps its wording.
    4. `sq migrate repad`, `rename-status` and `rename-type` are refused on a mismatched squad with the same gate message as other verbs (gate behaviour, ST5). `help` and `chlog` run in both directions, `up` only when behind.
    5. Not changed: the gate message text, `allocate_id`'s wording at the current schema (pinned by test), and `spec_refusal`'s shared text.
    Docstrings and module docs in `_store.py` and `_v0_14_to_v0_15.py` were corrected and are not adopter-facing.
    
    @python-dev note for the reviewer: new behaviour is in `_maintenance.run_pending_migrations`, `_cli/_migrate.py` and `_cli/_common.py`. ST1 and ST3 tests are the four files from the earlier session plus the new module.
- [2026-10-15T18:27:52Z] Theo Writer:
  - @manager REV-995 F13 documentation half is done, and F13 is marked Fixed (the reviewer had already confirmed the code and test half). Files changed, not committed: docs/migration.md, docs/workflow.md, docs/stability.md, CHANGELOG.md (two entries under 0.16.0 Changed).
    
    Driven with the working tree's `sq` in a scratch squad stamped 0.14: the gate refuses `repad` and `rename-status`; `help` runs; a deleted milestone file gives `index reconciled with the files: dropped MILE-22 (no file backs it)` and the run completes; an undecodable task and a hand-edited `status: Bogus` each give exit 1 with the schema left at 0.14; with no index the run walks and completes; stamped ahead, `migrate up` gets the gate's "Upgrade the squads package"; a current squad gives "nothing to migrate". Read, not driven: the shared-number renumber text, the override and playbook load refusals, the index-full refusal, and the "still at schema" ending.
    
    What's left (optional, not adopter-facing): the module docstring of `_v0_14_to_v0_15.py` (around lines 113-116, plus the comments at 323 and 338) still lists "a missing indexed file" as a skip the runner makes. The reconcile now drops that entry first. The reviewer's note that CLAUDE.md's module list leaves out `_index/_reconcile.py` and `_services/_corpus_fit.py` is still open too, and CLAUDE.md is outside my scope.
- [2026-10-15T18:42:56Z] Elias Python:
  - @manager F19 to F23 and both leftovers are fixed. Nothing is committed. Pyright, ruff check and format are clean. `tests/meta tests/integration tests/cli tests/unit tests/service` gave 7303 passed, 9 skipped; the full suite was not run.
    
    **Correction to my earlier handoff.** I wrote that the store-load refusals were unreachable after the reconcile and the pre-runner check. That was inferred from the shapes I tried, and F19 showed it false for hand-edited badge codes.
    
    **Fixes, with the rows that go red on revert:**
    - **F23.** `resolve()` in `src/squads/_paths.py` now reads a `--dir` folder's own `.squads.toml` when its `squad_dir` is ".". It never synthesises a current-stamp config for a folder that holds one.
      - Rows: layout (nested, project-root) × command (repad, list, repair, migrate up) × direction (behind, ahead, equal), in the gate test file.
      - Reverting the fix turns 7 red, all project-root.
    - **F21.** The gate no longer matches `-h`, and `--help` counts only when it sits before any `--` and is not the value of an option that takes one. The value-taking options are read from the whole command tree (`help_requested` in `_cli/_common.py`).
      - Rows: `-m --help`, `-m -h`, and `-- --help` on behind and ahead squads.
      - Reverting turns 6 red. The existing help-is-never-gated rows stay green.
    - **F20.** `version_notice` prints nothing while the schema differs from the package's. The remedy tests now read the whole output, not the slice from `error:`. That includes `test_migrate_up_bare_subprocess_exit_parity.py` and `test_migrate_up_checks_the_corpus_before_the_runners.py`.
      - Rows: the notice never names `sq sync` on migrate up, help or chlog of a behind squad.
      - Reverting turns 44 red, because every refusal row now sees the notice.
    - **F19.** The check before the runners now asks what the store's load asks. New `badge_code_problems` in `_index/_store.py`, called from `_corpus_fit.py`, refuses before any runner with a hand-fix remedy.
      - Rows: hand-edited item badge and sub-entity badge, each with and without an override, in the refusal table, plus one end-to-end row.
      - Reverting turns 5 red.
    - **F22.** Both remedy matchers and the static guard now catch placeholder-shaped commands (`sq <type> <n> …`). The guard also follows a string constant assigned to a name in the same module, and flags attribute uses such as `itf.skew_message`. Its docstring states what it cannot see: text built by a helper, imported from another module, or raised by code a runner calls. The behavioural table covers those.
      - Reverting the pattern turns the guard's self-check red (1).
    - **Leftover 1.** The `_v0_14_to_v0_15.py` docstring and comments no longer list a missing indexed file as skipped. They say the reconcile drops that entry first, and that a file unreadable after that is skipped.
    - **Leftover 2.** One line each for `_index/_reconcile.py` and `_services/_corpus_fit.py` in CLAUDE.md's hand-written module list.
    
    **Adopter-visible wording that changed:**
    1. The "squads X detected … Run `sq sync`" notice is gone while the squad's schema differs from the package's.
    2. New refusal before any runner: "no migration has run: these stored badge codes are not declared by their collection:" followed by one line per item or sub-entity ("<id> field 'priority' has code 'x', which the 'priority' collection does not declare"), then "correct the named frontmatter values by hand, then re-run `sq migrate up`. The schema is unchanged."
    3. Behaviour: `--dir` on a project-root squad now meets the gate, so `repair`, `list` and `migrate repad` are refused there as on a nested squad. An argument that only spells `-h` or `--help` no longer bypasses the gate.
- [2026-10-15T18:45:41Z] Theo Writer:
  - @manager The three adopter-visible changes from the latest python-dev handoff are now documented. Nothing is committed.
    
    - docs/migration.md: the version notice is not shown while the schema differs from the package's (in the TL;DR follow-up paragraph and the stamping section). The out-of-date-squad section now says `--help` counts only as an option of its own (not after `--`, not as an option's value), that `-h` is not a help option, and that the gate covers `--dir` on a project-root squad. "Before the first runner" gains the undeclared-badge-code refusal.
    - CHANGELOG 0.16.0: the badge refusal is folded into the existing `sq migrate up` Changed entry, a new Changed entry covers the notice, and two Fixed entries cover `--dir` on a project-root squad and the `-h`/`--help` bypass.
    - docs/stability.md: no change needed.
    
    Driven with the working tree's `sq` in scratch squads:
    - No notice on a behind squad; it still prints on a current squad with an older `squads_version`.
    - `priority: x` refused before any runner, exit 1, schema left at 0.14.
    - `list -h` and `comment -m --help` are refused by the gate on a behind squad.
    - `--dir` from another folder on a `squad_dir = "."` squad stamped 0.14 refuses `list` and `repair`.
    
    Read, not driven: the 0.15.0 `-h`/`--help` and `--dir` behaviour I describe as "before" (from the `v0.15.0` source).
- [2026-10-15T18:57:24Z] Elias Python:
  - @manager F23, F24, F25 and the F21 residual are fixed. Nothing is committed. Pyright, ruff check and format are clean. `tests/meta tests/integration tests/cli tests/unit tests/service`: 7387 passed, 9 skipped. The full suite was not run.
    
    **F23.** `resolve()` in `src/squads/_paths.py` now walks up from the `--dir` folder to the first `.squads.toml` and accepts it only if its `squad_dir` resolves to that folder, so `"."`, `"./"`, `"work/squad"`, a renamed folder and a symlinked folder all work. If the configured squad folder is a different one, it raises "<folder> is not the squad folder of the squad configured at <file>…". It never synthesises a default config while an initialised squad is on the path.
    - Rows in `test_the_gate_lets_past_by_command_and_direction.py`: layout (nested, root, `./`, multi-level, renamed, symlinked) × command (repad, list, repair, migrate up) × direction (behind, ahead, equal). A second table covers `--dir` at the project root of a nested squad and at a sibling folder: all refused, nothing written. One more row covers a folder in no squad.
    - Reverting to a "." check only: 59 red. I did this with a crude edit, so the count includes the nested rows, which that edit also broke.
    - One deliberate limit: `sq init --dir X` inside an existing squad's tree still falls back to the default config. I left `init` alone.
    
    **F24.** The comparison is one guarded method, `declares()` on the collection in `_workflow/_models.py`. A value that is not a string is not a code. The loader (all three sites), the store load and `badge_code_problems` all call it. The refusal now also names the file: "INC-20 field 'impact' has code [...], which the 'level' collection does not declare (in incidents/INC-000020-an-incident.md)".
    - Rows in the migrate-up refusal table: custom badge as a list, a mapping, a number, and an undeclared string.
    - With the guard removed, 2 red (the list and the mapping).
    
    **F25.** The runner docstring now says: every condition it declines is a skip reported by item id; what it calls can still raise (a file that becomes unreadable during the run) and a stopped run is resumed with `sq migrate up`; an unparseable item file never reaches it, because the run is refused first. The false example is gone.
    
    **F21 residual.** `help_requested` now consumes the token after each value-taking option, so `-m -m --help` is a real help request and `-m -m -m --help` is not. Table `test_help_is_recognised_only_where_the_parser_would_treat_it_as_help` has 7 shapes. Reverting to the old rule: 1 red (`-m -m --help`). It was clean to do.
    
    **Adopter-visible wording and behaviour changes:**
    1. New error when `--dir` names a folder that is not the squad's own folder: "<folder> is not the squad folder of the squad configured at <file> (its squad_dir is '…'); name that folder with --dir".
    2. `--dir` at a project root, or on a `"./"`, multi-level or symlinked squad folder, now meets the gate.
    3. The stored-badge-code refusal names the file; a list or mapping value is refused cleanly instead of crashing `sq migrate up` with a TypeError.
    4. `sq … -m -m --help` is now help.
- [2026-10-15T18:59:46Z] Theo Writer:
  - @manager The four changes from the latest python-dev handoff are reflected. Nothing is committed, and `sq check` is clean.
    
    - **New `--dir` error.** docs/faq.md has a new error entry that names the folder to pass. The changelog `--dir` Fixed entry quotes the message.
    - **`--dir` gate fix.** The existing Fixed entry and the migration.md gate sentence now cover project-root, multi-level and symlinked squad folders. The changelog's "before" sentence names only project root and multi-level. The `v0.15.0` source read the parent folder's `.squads.toml`, so `"./squads"` and a symlinked folder already resolved correctly in 0.15.0. Those two were never broken in a release.
    - **Badge-code refusal.** migration.md and the changelog say the message names the file, and that a list in place of a code is refused before any runner. Driven: `priority: [a, b]` on a task is refused before any runner with exit 1. It comes out through the "cannot be given an index entry" refusal, not the badge one, so I did not write "the same way".
    - **`-m -m --help`.** Folded into the migration.md `--help` sentence.
    
    Driven: the new error, for `--dir` on a nested squad's project root and on a type folder. Symlinked `--dir`: the command runs at the current schema and is refused when the squad is behind. `-m -m --help` prints usage. Read only: `"./"` and multi-level `squad_dir`.
- [2026-10-15T19:11:26Z] Elias Python:
  - @manager F26 and the docstring half of F27 are fixed. Nothing is committed. `sq check` is clean. Pyright, ruff check and format are clean. `tests/meta tests/integration tests/cli tests/unit tests/service`: 7411 passed, 9 skipped (the run came before a final docstring re-wrap in `_paths.py`; only ruff was re-run after it). The full suite was not run.
    
    **F26.** In `src/squads/_paths.py`, `--dir` on a folder with no `.squads.toml` above it now checks whether the folder holds squad data (a `.squads.json`, or an `PREFIX-N-slug.md` item file one folder down). If it does, `resolve()` refuses: "<folder> holds squad data but no .squads.toml above it names it as its squad folder (a squad_dir outside its project tree is not found from here); run from the project directory instead". A folder holding none still gets the default config, so a made-up current stamp is never given to a populated folder. I chose to refuse rather than read the index's stored stamp, because the owning config is unreachable and the project directory is the right place to run from.
    - Rows: `outside-relative` (`../shared`) and `outside-absolute` layouts × repad, list, repair, migrate up × behind, ahead, equal (24 rows), in the not-the-squad table of `test_the_gate_lets_past_by_command_and_direction.py`. They assert exit 1 and that the whole temp tree is byte-identical.
    - Removing the new check: 24 red, all of those rows.
    
    **F27 (docstring half).** The `require_init` parameter had no caller, so I removed it and the dead default-config branch of the walk-up. `resolve()` now always raises `NotInitializedError` when no config is found. The docstring is rewritten to say what `--dir` and the walk-up actually do. Vulture reports nothing in `_paths.py` from this change. I did not touch `sq init` ignoring `--dir`; that goes to QA as a bug.
    
    **Adopter-visible change:** `--dir <folder>` on a squad folder that lies outside its project tree now fails with the message above instead of running unchecked.
- [2026-10-15T19:12:19Z] Theo Writer:
  - @manager The out-of-tree `--dir` refusal is documented. It has an entry in docs/faq.md beside the other `--dir` error, and one sentence in the existing 0.16.0 `--dir` Fixed entry. There are no new sections and nothing is committed.
    
    I drove it in a scratch squad initialised with `squad_dir = "../shared"`. `sq list` from the project directory exits 0. `sq --dir <shared> list` from outside the project exits 1 with the "holds squad data but no .squads.toml above it names it" message. I did not drive the absolute-path `squad_dir` case; I read it from `resolve()`.
- [2026-10-15T19:19:49Z] Catherine Manager:
  - Done: REV-995 approved after eight passes (F28 WontFix, home ADR-1009); full suite 7485 passed, 0 failed; pyright, ruff and sq check clean. Accepted under the operator delegation of 2026-10-11 on MILE-934.
<!-- sq:discussion:end -->
