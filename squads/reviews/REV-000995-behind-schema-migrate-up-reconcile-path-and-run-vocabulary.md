---
id: REV-995
sequence_id: 995
type: review
title: 'Behind-schema migrate up: reconcile path and run vocabulary'
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-954:addresses
- MILE-934:targets
description: Review of TASK-954, one pass per group of subtasks; the first pass covers
  the runners opening the index under the run's resolved vocabulary.
subentities:
- local_id: F1
  title: No test fails when a runner is handed the wrong playbook
  status: Verified
  severity: medium
- local_id: F2
  title: Static guard passes code that still reads the bundled vocabulary
  status: Verified
  severity: low
- local_id: F3
  title: Digest golden cannot be reviewed or regenerated on update
  status: Verified
  severity: low
- local_id: F4
  title: Contributor guide and a runner docstring state the old contract
  status: Verified
  severity: low
- local_id: F5
  title: Re-run after a stopped run is refused on a pre-0.7 override squad
  status: Verified
  severity: medium
- local_id: F6
  title: Migrated-corpus goldens store one rendered surface nine times
  status: Verified
  severity: low
- local_id: F7
  title: A stray item file is indexed, written to, then strands the run
  status: Verified
  severity: high
- local_id: F8
  title: A refused run permanently raises the counter and padding
  status: Verified
  severity: high
- local_id: F9
  title: An unreadable document that only looks like an item stops the run
  status: Verified
  severity: medium
- local_id: F10
  title: A stopped run leaves no durable record of what the reconcile did
  status: Verified
  severity: medium
- local_id: F11
  title: Entries from a pre-0.7 index are reported as UNRESOLVED ids
  status: Verified
  severity: medium
- local_id: F12
  title: Two ids sharing a number are refused with a false cause
  status: Verified
  severity: medium
- local_id: F13
  title: Docs and one test still describe the skip-and-carry-on behaviour
  status: Verified
  severity: low
- local_id: F14
  title: Refusals name the last-sync release, not one that reads the schema
  status: Verified
  severity: medium
- local_id: F15
  title: A declared folder spelled with a trailing slash stops the run
  status: Verified
  severity: medium
- local_id: F16
  title: A hand-edited type is refused as a spec change the run accepts
  status: Verified
  severity: medium
- local_id: F17
  title: A prefix with an underscore or leading digit is never reconciled
  status: Verified
  severity: medium
- local_id: F18
  title: The check's refusal overstates its remedy and omits the rebuild
  status: Verified
  severity: low
- local_id: F19
  title: A hand-edited badge code stops the run naming sq repair
  status: Verified
  severity: medium
- local_id: F20
  title: The version notice names sq sync on every behind migrate run
  status: Verified
  severity: medium
- local_id: F21
  title: An argument equal to -h or --help lets any command past the gate
  status: Verified
  severity: medium
- local_id: F22
  title: Remedy checks miss placeholder commands and indirect raises
  status: Verified
  severity: low
- local_id: F23
  title: A project-root squad named with --dir skips the gate and its config
  status: Verified
  severity: high
- local_id: F24
  title: A list or mapping in a custom badge field crashes migrate up
  status: Verified
  severity: low
- local_id: F25
  title: The 0.14 to 0.15 runner docstring still states two false things
  status: Verified
  severity: low
- local_id: F26
  title: A squad folder outside its project tree still skips the gate with --dir
  status: Verified
  severity: medium
- local_id: F27
  title: resolve() documents a require_init caller that does not exist
  status: Verified
  severity: low
- local_id: F28
  title: The squad-data check misses deep or slugless item files
  status: WontFix
  severity: low
created_at: '2026-10-11T20:54:17Z'
updated_at: '2026-10-15T19:17:23Z'
---
<!-- sq:body -->
## Scope

Review of TASK-954, one pass per group of subtasks as they are built. Findings from every pass
are recorded here.

### Pass 1: ST6, every runner's index opened under the run's resolved vocabulary

The change read: `src/squads/_migrations/_context.py` (new), `_registry.py`, the four runners
that open the index (`_v0_4_to_v0_5.py`, `_v0_8_to_v0_10.py`, `_v0_11_to_v0_14.py`,
`_v0_14_to_v0_15.py`), `_services/_maintenance.py::run_pending_migrations`, the four new test
modules, `tests/fixtures/migrated_corpus_digests.json`, `tests/_helpers.py` and the six adapted
test modules. Uncommitted, on top of `1a96e516`.

How it was checked, beyond reading:

- **Old against new, row by row.** A probe ran `sq migrate up` through the CLI over 11 squad
  sources (corpora 0.1, 0.3, 0.4, 0.5, 0.8, 0.10, 0.11, 0.14 and fresh squads stamped 0.4, 0.8,
  0.11) by 26 override shapes (286 rows), once on `git archive 1a96e516` and once on the working tree,
  and compared exit code, output and the digest of every file and directory. A second probe
  carried one item per shape for eight more shapes over six sources (48 rows).
- **The digest fixture against the unchanged code.** The new digest test, run on the
  `1a96e516` sources, passes for all eleven corpora.
- **Mutations.** Each of the four `IndexStore(...)` constructions with `spec=` removed, one
  with `spec=None`, and the context built with a bundled spec or a bundled playbook, each run
  against the migration tests; the bundled-playbook mutation also against the whole suite.
- **The static guard**, fed fifteen shapes of code that reads the bundled vocabulary.
- **An era-shaped squad**: the 0.5 corpus with an override declaring a type and one item of it
  written by hand in the 0.5 file and index shape, migrated with the old and the new code.

### What held

- Of 334 probe rows, 254 complete on both and none of those differs in exit code, output or
  any file. 16 are refused by the unchanged code and complete on the changed code with the
  carried item kept: every one is an override that alone declares vocabulary an item carries,
  on a squad stamped below 0.14. None completes on the unchanged code and is refused on the
  changed code. 55 are refused by both with the same output and the same tree (overrides the
  loader or the index cross-check rejects, and rows whose setup is invalid by construction).
- 9 rows are refused by both with the same message and a different tree: an override that
  rebinds a badge field to a collection of its own that lacks a stored code, which the index
  cross-check does not report. The changed code refuses at the first runner that opens the
  index, before the 0.11 to 0.14 runner writes; the unchanged code refused one runner later,
  after it had written.
- The store uses its spec only to validate a load, and the last runner has opened the index
  under the squad's own spec since it shipped, over an index that only grows during a run. A
  squad that completes on the unchanged code has therefore already passed that validation, so
  passing the spec to the three older runners can turn a refusal into a pass or move it
  earlier, never the reverse.
- On the `migrate up` path the service's spec and playbook come from the root callback's
  resolution of the same files the two newest runners used to re-read, through the same
  loaders. `run_pending_migrations` has one caller.
- Shapes driven with a carried item, all kept: a sub-entity badge code, a sub-entity kind of
  the squad's own with its own lifecycle and status, a type on a lifecycle of its own, a ref
  kind, a bundled type dropped and re-declared under another name, a re-prefixed and
  re-foldered bundled type, an adopter-declared field. Shapes driven without one: a playbook
  override alone, a deselected view, an added view, dropped bundled types, a custom lifecycle
  on a bundled type, a relabelled collection, a re-rooted roster lifecycle.
- The era-shaped 0.5 squad is refused by the unchanged code and completes on the changed code,
  `sq check` exits 0, and the item of the squad's own type loads. Its frontmatter keeps the
  padded id and refs, which is the manual step the 0.5 to 0.7 runbook already describes.
- The changed test helper in `test_milestone_roll_up_tag_migration.py` builds the service the
  way the CLI does. Run in its previous form against the changed code, one test of 22 fails
  (the deselected-view row), which is the difference a service built without the squad's
  vocabulary now makes; no CLI path builds one for `migrate up`.
- `_context.py` imports nothing from `_registry`, `_services` or `_cli`.

### Not covered by this pass

ST1 to ST5, which are not built. The second backend (`agents_md`), role overrides under
`.overrides/roles/`, template overrides, and squads with operators or author-created skills
were not driven. The whole suite was not re-run on the working tree; pyright and ruff were not
re-run.

### Pass 2: ST2, the index reconcile before the runners

The change read: `src/squads/_index/_reconcile.py` (new), its call and refusal in
`_services/_maintenance.py::run_pending_migrations`, `_cli/_migrate.py`, `_services/_results.py`,
the fold-free constructor in `_models/_item.py`, the three new test modules, the six rewritten
tests and the reshaped `tests/goldens/migrated_corpus/`. Uncommitted, on top of `1226c372`.
Read against the subtask and against amendments A2, A3 and A4 of the decision.

How it was checked, beyond reading:

- **Old against new on scratch squads**, `sq migrate up` through the CLI with the code at
  `1226c372` and with the working tree: a squad nested in a project and stamped 0.14, the
  0.14 corpus at a project root, and the 0.5 corpus. Shapes: a task and a bug sharing one
  number; a copy, a hand-moved item and a never-indexed item in an archive folder; a backup
  folder, a nested fixture tree and a lone fixture item at a project root; another tool's
  date-numbered record; ordinary documents whose names have the item shape; an entry whose
  file is gone beside an undecodable file; then the remedy and a second run for each refusal.
- **The routine alone**, over 29 hostile frontmatter shapes with and without a previous entry,
  looking for an exception that escapes and for what each shape lands as.
- **This repository's own squad directory**, copied to scratch: 964 candidates, 961 items,
  nothing reported, no entry changed, 1.3 seconds.
- **When it runs**: a current squad holding an entry whose file is gone, a squad stamped
  ahead, and one stamped at a schema no runner starts from.
- **The reshaped goldens**: each corpus's expectation rebuilt from its own files and the
  shared ones and compared with the 319 files verified in the first pass; one corpus's input
  changed to see which rows fail.
- **Two candidate fixes as mutations**, to see which tests pin the behaviour in question.

### What held in pass 2

- No shape made the routine raise anything but its own error, and no shape made it replace an
  entry with one the file does not describe. A file that cannot be indexed keeps its previous
  entry; an entry is dropped only when nothing stands for it.
- It runs when a runner applies and only then: the current squad's index is byte-identical
  after `sq migrate up`, the ahead squad is refused with its index untouched, and the squad
  stamped at 0.12 is reconciled and run through the two runners that apply.
- It writes the index and nothing else, stamped at the corpus's schema.
- Migrating the eleven corpora produces what it produced before the reconcile existed: the
  rebuilt expectations equal the first pass's goldens file for file.
- Every caller of the changed constructor helpers passes a default kind, so the folding path
  is the one it was; the fold-free path is reached from the reconcile only.
- The module imports nothing that holds a spec, and the store is read without validation and
  written without it.
- A backup copy or a nested fixture tree that repeats the squad's own ids is refused with
  both paths named, and the run completes once the copy is out of the squad directory.
- On the 0.5 corpus an undecodable item file made the unchanged code crash with a traceback;
  the changed code refuses cleanly.

### Not covered by pass 2

ST1, ST3, ST4 and ST5, which are not built. Windows paths, symlinked folders and concurrent
writers during the reconcile were not driven. The whole suite, pyright and ruff were not
re-run.

### Pass 3: the reconcile as rebuilt to A11, and the check before the first runner

The change read: `src/squads/_index/_reconcile.py`, `src/squads/_services/_corpus_fit.py` (new),
the call site in `_services/_maintenance.py`, the bypass builder in `_cli/_common.py`,
`_cli/_migrate.py`, and the test modules that go with them. Uncommitted, on top of `1b2e57e5`.
Read against amendments A2, A4, A6, A7, A9, A10 and A11 of the decision and the operator's
ruling of 2026-10-12.

How it was checked, beyond reading:

- **Every shape driven in pass 2, again**, through `sq migrate up` with the index present,
  with it deleted, and for one with it unparseable: the shared number, the three archive
  shapes on a nested squad, the seven project-root shapes, the dropped-entry record, the
  counter rows and the pre-0.7 naming. Each run snapshots every file before and after, and a
  refused run is repeated to compare output, exit code and tree.
- **The remedy the refusals name, with the real releases.** Eleven releases installed from the
  package index into scratch environments. For each stamped schema from 0.3 to 0.14: the
  refusal, then the matching release's `sq repair`, then `sq migrate up` again, for the
  no-index state beside a stray and for the unindexed first item of a bundled type; and the
  unindexed first item of a custom type at 0.8, 0.11 and 0.14. Fresh squads were initialised
  with 0.1.1 and 0.2.0 to see what those releases really stamp.
- **The check's bound, old code against new**: override folder spellings, a folder two types
  share, prefixes with a hyphen, an underscore and a leading digit, a nested folder, a
  re-foldering override, a hand-edited type, and an index that parses and holds nothing.
- **The builder change, old code against new**: `sq repair` and `sq check` at the current
  schema under four override failures, `sq migrate up` on an ahead squad and on a behind one.
- **Both routes into the stopped-run dead end**, and the with-index refusal followed by its
  remedy in two variants.
- **This repository's own squad**, scratch copy, plan and check with its index and without.

### What held in pass 3

- With a readable index, every stray shape from pass 2 completes as it did before the
  reconcile existed, the stray untouched and the counter and padding unmoved.
- With no readable index, every stray shape is refused before any runner with a cause that is
  true, and the squad is byte-for-byte as found: no index where there was none, the
  unparseable one untouched, no lock file, no reflog line, no item file changed. A second run
  gives the same output, exit code and tree. A clean squad with no index completes.
- No run the steps before the first runner let through was refused by the trailing repair,
  in any shape driven here.
- `sq repair` and `sq check` behave as before under the builder change, and a squad stamped
  ahead is refused as before.
- An override or playbook override that does not load stops `sq migrate up` with the file and
  the loader's cause, index untouched.
- Both routes into the stopped-run dead end are gone: each stops once with a true cause, leaves
  no `UNRESOLVED` id, and the re-run after the fix completes.
- This repository's own squad passes the reconcile and both questions in both states.

### What the design costs in practice

The operator chose that the routine stays blind. This is what that does, driven.

| State | What happens | Way out | Works? |
|---|---|---|---|
| no readable index, clean squad | completes | none needed | yes |
| no readable index, any item-shaped file outside the type folders, or an unreadable look-alike | refused, squad untouched | restore the index from version control | yes where the index is committed, which `sq init` sets up |
| the same | | the stamped release's index rebuild | yes for schemas 0.3 to 0.14, each driven; the old release ignores the stray |
| the same | | move the files out | yes; at a project-root squad that is out of the repository |
| index present, first item of a type unindexed in a folder the index does not know | refused | the stamped release's index rebuild | yes for schemas 0.3 to 0.14, bundled type; yes at 0.8, 0.11 and 0.14 for a custom type |
| index parses and holds no items | every item file refused as unindexed | the stamped release's rebuild; or delete the empty index, which nothing says | yes |

Three things an operator should know that the messages do not say.

- **Which release.** The message names the release that last synced the squad, which is not
  always one that can open it (the finding on the release named).
- **Which command.** By the remedy rule no command is printed. The operator has to know that
  "its own index rebuild" means installing that release beside this one and running its
  `sq repair`. That command also runs that release's own content sweep: on the 0.14 corpus it
  rewrote four item files.
- **The oldest squads.** A squad created by 0.1.x or 0.2.0 stamps `schema_version = 1` or `2`.
  The current package refuses that stamp outright (`invalid .squads.toml`), at `1b2e57e5` too,
  so nothing here reaches such a squad. The 0.1 and 0.2 corpus fixtures carry a dotted stamp
  those releases never wrote and cannot read. In practice the oldest squad this path serves is
  one stamped 0.3.

### Not covered by pass 3

The gate exemption, remedy wording across the corridor and the end-to-end table, which are not
built. Windows paths, symlinked folders, concurrent writers. The whole suite, pyright and ruff
were not re-run.

### Pass 4: verification of the fixes to the check before the runners

The change read: `_index/_reconcile.py`, `_services/_corpus_fit.py`, `_services/_maintenance.py`,
`_migrations/_registry.py` and `_workflow/_loader.py` as they differ from pass 3, against the
architect's dated note on the name pattern. Uncommitted, on top of `75f53462`.

Re-driven through `sq migrate up`, old code against new where the old code has an answer:

- for each stamped schema from 0.3 to 0.14, both refusals that name a release, then the index
  rebuild of exactly the release named, installed from the package index, then the run again;
- the two folder spellings, the underscore, leading-digit and dotted prefixes, each with an
  index and with none, and a second unindexed item of an underscore-prefixed type;
- the hand-edited type with no override and beside one; the with-index refusal and its remedy
  in both variants; the index that parses and holds nothing, then the same squad with the
  index file removed;
- fourteen ordinary document names through the wider tree walk, parse-clean and one in
  Latin-1, and two look-alikes carrying an id of the wider shape;
- eight of the pass 3 stray shapes again, the pre-0.7 naming, and this repository's own squad
  in both states.

What the wider walk and the wider id cost, in the no-index state only: names whose prefix holds
an underscore or starts with a digit are now opened (`my_notes-1-x.md`, `3d-2-models.md`,
`release_notes-2-draft.md`, `meeting_2024-01-notes.md`, `Q3_report-2024-final.md`,
`2fa-1-setup.md`, `1st-2-thing.md`, `python_3-12-notes.md`). Parse-clean with no id they are
passed over and the run completes. One of them that does not decode stops the run, as any
look-alike does in that state. A document carrying `id: CVE-2024-1234` and no `type` is now
taken for an item that cannot be indexed, where the narrower id shape passed it over. Date-led
names, dotted names and names with no slug are still ignored.

One residual on the release named: the 0.4 fixture is told 0.5.0, which refuses a squad stamped
0.4. No release stamps 0.4, so only the fixture meets it.

### Pass 5: remedies behind the gate, the per-command grants, the end-to-end table

The change read: `_cli/_common.py` (`Ground`, `GateGrant`, `past_the_gate`, `apply_gate`), `_cli/_migrate.py` (the group callback and `migrate_grants`), `_errors.py`, `_models/_index.py`, `_services/_maintenance.py` (the closing line, the full-index refusal, `rerun`), the `_store.py` and 0.14 to 0.15 docstrings, and the five new test modules. Uncommitted, on top of `90764251`. Read against ST1, ST3 and ST5 and amendments A1 and A7.

How it was checked, beyond reading (dev-tree `sq` on scratch squads):

- **The gate matrix.** On a nested squad stamped 0.14, 0.99 and 0.15, twelve invocations (`migrate up`, `help`, `chlog`, `repad 7`, `rename-status`, `rename-type`, bare `migrate`, `migrate --help`, `repad 7 --help`, `list`, `repair`, `check`), each from inside the squad and with `--dir` from outside it. That makes 72 rows, each with the whole tree hashed before and after.
- **Gate evasions.** An argument equal to `-h` or `--help` given as an option value or after `--`, `--dir` at a project-root squad, and the grant lookup for an unnamed, aliased or nested command (read).
- **Every path that can print a remedy while the squad is behind.** The version notice, a store load reached by a runner, an unknown backend, a broken role catalog override, and the trailing repair's refusals (read).
- **F5, driven three ways** on the 0.5 corpus with a `[ref_kinds.mirrors]` override: a hand-edited status, an undecodable bug file, and a hand-edited badge code that stops the run inside a runner. Each was followed by the fix and a second run.
- **The static guard**, fed five evasion shapes.

### What held in pass 5

- On a nested squad all 72 rows match A1. Behind: `up`, `help` and `chlog` run, and every other verb exits 1 with the behind message and changes nothing. Ahead: `help` and `chlog` run, and `up` and every other verb exit 1 with "Upgrade the squads package". At the current schema, the three writing verbs do their work. `--help` works everywhere. `--dir` from outside the squad gives the same answers as running from inside it.
- The grant lookup fails closed. A verb registered without a name, or without a grant, and a group nested under `migrate`, all get no grant and are refused. An alias registered on the same callback inherits that callback's grant, which is correct. The decorator order does not matter, because `functools.wraps` copies the attribute.
- F5 does not reproduce. All three routes stop once with the schema unchanged, leave no `UNRESOLVED` id, and complete on the re-run after the fix, and `sq check` exits 0.
- An unknown backend, raised from inside the 0.11 to 0.14 runner, gets the closing line and names no refused command.
- The 0.11 to 0.14 runner reads role mirrors and not the role catalog, so a broken `.overrides/roles.toml` does not change what it writes. Its docstring says so.

### Not covered by pass 5

The full suite, pyright and ruff (the manager runs them). The second backend, Windows paths, concurrent writers. The falsifications in the hand-back were not repeated.

### Pass 6: verification of F19 to F23 and the two leftovers

The change read: `_paths.resolve`, `help_requested` and `_value_options` in `_cli/_common.py`, `version_notice`, `badge_code_problems` and its call in `_corpus_fit.py`, the three remedy matchers, the runner docstring and the two CLAUDE.md lines. Uncommitted, on top of `90764251`.

Driven on scratch squads stamped 0.14 with dev-tree `sq`:

- **`--dir` across layouts**, with a fresh squad per row: project root spelled `"."` and `"./"`, nested, `"./squads"`, a renamed folder, a two-level `squad_dir`, the project root of a nested squad, plus trailing slashes, `/.`, `..` paths and symlinks.
- **Help detection**: values after `-m` and `--message`, a repeated option, `--opt=value`, options local to item verbs, a bundled short flag, `--` and a root option.
- **Badge codes**: an item priority, a finding severity, a custom field on a sub-entity and on a type of the squad's own, and values that are int, list and mapping.
- **The version notice** on behind and current squads; the static guard fed twelve shapes.

Held: F19, F20, F21 and F22, each verified with its residuals noted on the finding. The CLAUDE.md lines hold.

Not held: F23 holds only for `squad_dir = "."` spelled exactly, so it is reopened with three bypassing rows. New: F24 (a list or mapping in a custom field crashes the run) and F25 (the runner docstring). The docs half of F13 was not re-read while the writer is editing.

### Pass 7: verification of F23, F24, F25 and the F21 residual

The change read: `resolve()`'s walk-up from the `--dir` folder, `help_requested`, the shared `declares()` check on a collection and its callers, and the runner docstring. Uncommitted, on top of `90764251`.

Driven with the dev-tree `sq` on scratch squads:

- **`--dir`**: the three layouts reopened in pass 6, a squad inside another squad's folder, a nested project under another project root, a folder between two configs, a missing folder inside and outside a squad, and a `squad_dir` that leaves the project tree or is absolute.
- **The gate test, in a scratch copy of the tree**: run against the HEAD `resolve()` and against the pass-6 `"."` check.
- **Badge values**: a list, a mapping and an int in custom item and sub-entity fields, through `migrate up` and at the current schema.
- **Help**: `-m -m --help` and its neighbours.
- **`sq init --dir`** inside another squad's tree.

Held: F23 for every layout inside the project tree, F24, F25, and the F21 residual. New: F26 (a `squad_dir` outside the project tree still skips the gate) and F27 (a dead `require_init` branch, and the hand-back's `init` caveat, which describes it).

### Pass 8: verification of F26 and F27

The change read: `_holds_squad_data` and the `--dir` branch of `resolve()`, the removed `require_init` parameter and its docstring. Uncommitted, on top of `90764251`.

Driven with dev-tree `sq` on scratch squads, each against a `squad_dir` outside the project tree unless stated:

- **Squad-data shapes**: index present; index removed; items only two folders down; a custom type folder one folder down; a slugless item file.
- **Folders that are not squads**: an empty folder, a folder holding only `.reflog.jsonl`, and an unrelated folder holding `ABC-1-x.md` one level down and at its top.
- **A falsification of the new check** in a scratch copy of the tree, and `sq init`, `sq migrate help`, `sq list` and `--version` with and without a squad.

Held: F26 and F27. New: F28 (low, not blocking), the two shapes the squad-data check does not see, with the reasoning for accepting it for one release while `--dir` is replaced.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 995 add-finding "…" --severity medium`; track with `sq review 995 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — No test fails when a runner is handed the wrong playbook

<!-- sq:finding:F1:body -->
**What.** The subtask's goal is that every runner works under the one spec and playbook the
run resolved. Nothing fails when a runner is handed a different playbook, and the test that
asserts the context carries the service's own spec and playbook cannot fail on that assertion.

**Evidence, demonstrated.**

- `src/squads/_services/_maintenance.py:1681`, with `playbook=self.playbook` replaced by the
  bundled playbook singleton: the four new test modules and the seven existing migration
  modules give 198 passed. The whole suite on the same scratch copy gives the same result with
  and without the mutation (6531 passed; the 10 failures and 30 errors are meta and docs tests
  that need repository files the copy lacks, the same set both times).
- That mutation changes what `sq migrate up` writes. A fresh squad stamped 0.4, 0.8 or 0.11
  whose override declares an `incident` type and whose playbook override names `manager` as
  its author gets a different `CLAUDE.md` (the team-workflow line for the type) under the
  real context than under the mutated one.
- `tests/integration/test_migrate_up_resolves_the_vocabulary_once.py:63` builds
  `Service(_paths_at(root))`, so `svc.spec` and `svc.playbook` are the bundled singletons, and
  lines 91 and 92 (`received[0].spec is svc.spec`, `received[0].playbook is svc.playbook`)
  hold for any context that carries those singletons, whoever fetched them. With the context
  built from a direct `bundled_spec()` call the test stays green (the table goes red on 50
  rows, so the spec half is pinned elsewhere; the playbook half is pinned nowhere).
- The `type-and-playbook` family in
  `tests/integration/test_migrate_up_under_the_resolved_vocabulary.py:128` asserts only that
  the item's type reads back (line 196), which the workflow override decides alone.

**Why it matters for what comes next.** The up-front vocabulary subtask rebuilds the service
for this caller through the bypass accessor, whose fallback passes no playbook today. A slip
there hands every runner the bundled playbook and nothing goes red.

**What would fix it.** Build the once-test's service under a workflow override and a playbook
override, so the two identity assertions compare objects only the run's own resolution can
produce. Add one row, through the service and through the CLI, asserting a byte only the
override playbook can produce after the run; the authoring line for the squad's own type in
the compiled region is one.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-11T21:04:19Z] Elias Python:
  - Fixed: once-test built under real overrides; playbook row asserts the compiled authoring line; bundled-playbook mutation now 7 red
- [2026-10-11T21:11:53Z] Paul Reviewer:
  - Verified on the working tree: with the bundled playbook swapped into the context, 7 tests go red (the once-test on its identity assertion, and the type-and-playbook row at built-0.4, built-0.8 and built-0.11 through the service and the CLI, each on the CLAUDE.md line). The line is absent under the same workflow override without the playbook, so the playbook alone produces it. The bundled-spec swap now turns the once-test red too.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Static guard passes code that still reads the bundled vocabulary

<!-- sq:finding:F2:body -->
**What.** `tests/meta/test_migration_runners_use_the_runs_resolved_vocabulary.py` matches
names, so code that still validates or answers under the bundled vocabulary passes it. Its
docstring (line 8) declares one blind spot, `getattr` with a built name.

**Evidence, demonstrated by feeding `_violations` each shape; every one returns no hit.**

- `IndexStore(a, b, spec=None)`, and a helper `def f(paths, spec=None)` that passes
  `spec=spec` on: line 39 checks that a `spec` keyword exists, not what it carries.
- `from squads._index._store import IndexStore as Store` then `Store(a, b)`; `cls = IndexStore`
  then `cls(a, b)`; `functools.partial(IndexStore, a, b)()`: line 38 matches the callee's
  spelling.
- Resolution through a helper outside the banned set: `Service(paths)` (bundled spec and
  playbook by default), `open_service()`, `resolve_playbook(...)`, `_init_time_spec(...)`,
  `get_active_spec()`, the `squads._workflow` module shims (`TERMINAL`, `is_open`,
  `can_transition`) and `squads._interactions.PLAYBOOK`.

For the four runners that exist, the behavioural table covers the first group: `spec=None` in
the 0.4 to 0.5 runner turns ten rows red while this guard stays green. A runner added later
has no table row until someone writes one, so there the guard is the only check.

**The exemption.** `_FROZEN_LEGACY_READERS` (line 21) switches off all four resolver names for
the whole of `_meta_compat.py`. One call of one name needs it
(`_meta_compat.py:101`, `bundled_spec().subentity_initial(kind)`). The exemption is justified:
the module serves only the two oldest file-walking runners, which take paths. It is wider
than it needs to be. The scan also globs `*.py` without recursing (lines 70 and 77), so a
subpackage would not be read.

**What would fix it.** Treat a literal `None` as no `spec`; follow `import ... as` and a plain
rebinding of `IndexStore`; add the other entry points to the banned names, or better, pin it
behaviourally by recording the spec every `IndexStore` is built with while each registered
runner runs under a non-bundled spec and asserting it is the context's. Narrow the exemption to
`{"_meta_compat.py": {"bundled_spec"}}`. List in the docstring what the scan cannot see.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-11T21:04:23Z] Elias Python:
  - Fixed: guard flags None spec, aliases, rebinding, more entry points; exemption narrowed to one name; limits documented
- [2026-10-11T21:11:57Z] Paul Reviewer:
  - Verified: every evasion from the first pass is now flagged (None spec, import alias, rebinding once and twice, partial, passing the class as an argument, Service, open_service, resolve_playbook, get_active_spec, PLAYBOOK), the scan recurses, and a second resolver planted in _meta_compat.py turns the guard red. Still unseen and declared in the docstring: an optional-default helper, an unlisted helper, getattr. One residual it does not name: a rebinding through a module attribute (mk = store_module.IndexStore, then mk(a, b)).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Digest golden cannot be reviewed or regenerated on update

<!-- sq:finding:F3:body -->
**What.** `tests/fixtures/migrated_corpus_digests.json` stores a sha256 per file of each
migrated corpus. The digests are right today: the new test, run on the unchanged sources at
`1a96e516`, passes for all eleven corpora, and changing one written field in the 0.11 to 0.14
runner turns nine rows red. The problem is what happens the first time it legitimately changes.

**Evidence, read.**

- `tests/CONVENTIONS.md`, section 6: a golden's source of truth is a reviewed reference
  render, updating one is an intentional reviewed act, and it lives in its own file "so a diff
  on update is reviewable on its own terms". A diff of this file is a column of hashes; a
  reviewer cannot tell a wanted change from a regression.
- Nothing records how the file was produced. The test
  (`tests/integration/test_migrate_up_output_is_unchanged_for_every_corpus.py`) only reads it.
- It pins bytes this migration does not own. `CLAUDE.md`, the `.claude/skills/*/SKILL.md`
  pointers and the seeded skill bodies are rendered from today's templates by the 0.11 to 0.14
  runner, and `.squads.toml` and `.squads.json` carry the schema stamp. The next template edit
  or schema bump turns up to eleven rows red with no way to regenerate except an ad hoc
  script, which is how a golden ends up anchored to the code it guards.

**What it covers and leaves out.** Every file under the corpus root except `.reflog.jsonl`
(line 26); directories are not recorded (line 33), so a folder a runner creates and leaves
empty is invisible. Every corpus has an entry and the clock is frozen. All eleven corpora
carry no override and use `squad_dir = "."`, and the service is built on the bundled defaults
(line 47), which is the one population for which this change is a no-op by construction: both
the old and the new code resolve the same bundled singletons. The claim that no byte changes
for a squad with an override rests on the argument and probes in this review's body, not on
this test.

**What would fix it.** Record the capture procedure beside the fixture, or give the test a
documented regeneration switch. On a mismatch, show a content diff for the differing files
(keep the migrated tree, or compare against a committed tree instead of hashes). Say in the
docstring that it covers squads without overrides only.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-11T21:04:27Z] Elias Python:
  - Fixed: golden is now reviewed text copies under tests/goldens/migrated_corpus with UPDATE_GOLDENS regeneration and a diff on mismatch
- [2026-10-11T21:12:04Z] Paul Reviewer:
  - Verified: text goldens with a unified diff on mismatch, the repo's UPDATE_GOLDENS switch, coverage stated in the docstring. The goldens match the unchanged code: the test passes against them on the 1a96e516 sources for all eleven corpora. A changed written field turns nine rows red with a readable diff. No golden file is git-ignored. I read the 0.14 corpus's copy; it equals the committed 0.15 fixture apart from the frozen-clock timestamps. The duplication across corpora is recorded separately as F6.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Contributor guide and a runner docstring state the old contract

<!-- sq:finding:F4:body -->
**What.** Two statements of the runner contract are no longer true.

- `CLAUDE.md:169` describes each migration as a private module with `migrate(paths)->int`.
  Four of the ten runners now take the run's `MigrationContext`, and that is the signature a
  new runner that needs vocabulary has to use. This is the paragraph a developer adding the
  next runner reads first.
- `src/squads/_migrations/_v0_5_to_v0_7.py:35-36` explains that custom types are not covered
  "matching every other runner in this package (none of them thread the active spec)". Four
  runners are handed the active spec.

**Evidence.** Read.

**What would fix it.** In `CLAUDE.md`, state both shapes: a file-walking runner takes
`SquadPaths` and is wrapped, a runner that needs the index or the vocabulary takes the
context. In the 0.5 to 0.7 docstring, drop the parenthesis or limit it to the file-walking
runners.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-11T21:04:31Z] Elias Python:
  - Fixed: CLAUDE.md runner sentence and the 0.5 to 0.7 docstring state both runner shapes
- [2026-10-11T21:12:12Z] Paul Reviewer:
  - Verified by reading: CLAUDE.md line 169 states both runner shapes, and the 0.5 to 0.7 docstring now compares itself to the other file-walking runners only.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Re-run after a stopped run is refused on a pre-0.7 override squad

<!-- sq:finding:F5:body -->
**What.** A squad stamped below 0.7 that carries any workflow override, and whose first
`sq migrate up` is stopped after the 0.11 to 0.14 runner, is refused on every later run with a
false cause. This predates the change reviewed in the first pass: the unchanged code at
`1a96e516` and the changed code behave identically. It is recorded here because it is a
dead end inside this task's subject that the task's reproduction table does not list.

**Evidence, demonstrated** (steps 1 and 2 on the unchanged and on the changed code, the
corrected re-runs on the changed code). The 0.5 corpus, plus an override that only adds a ref kind
(`[ref_kinds.mirrors]`), plus the task file hand-edited to `status: Triaged`.

1. First run: every runner writes, the trailing repair refuses with
   `item TASK-3 has unknown status 'Triaged' ...; fix the frontmatter before running sq repair`.
   Schema stays 0.5. The index now holds `UNRESOLVED-1` to `UNRESOLVED-8` as ids.
2. Second run, before and after the frontmatter is corrected: refused before any runner with
   `workflow spec is incompatible with the live index`, one line per type of the form
   `type 'bug' prefix changed to 'BUG' in the workflow spec, but 1 live item(s) are still
   filed under the old prefix: ['UNRESOLVED-4']`, closing on `sq workflow lint`.
3. With the frontmatter corrected and the override file moved aside, the run completes and
   stamps the current schema. Nothing in the refusal points an operator there.

**Mechanism, read.** An index entry written before schema 0.7 stores neither `id` nor
`prefix`. Loaded by today's model it has an empty prefix, and `Item.id` renders the
`UNRESOLVED` sentinel (`src/squads/_models/_item.py:53`). The seeding transaction in
`src/squads/_migrations/_v0_11_to_v0_14.py:267` writes the whole index back, which persists
that sentinel as each entry's `id`. On the next invocation the root callback's cross-check
(`src/squads/_cli/_common.py:343`) derives the prefix from the stored id and reports every
type as re-prefixed. Without an override the cross-check does not run, which is why step 3
completes. The 0.4 to 0.5 and 0.8 to 0.10 transactions write the index back the same way.

**What would fix it.** Either of the two changes this task already plans removes the dead
end: rebuilding the index from the frontmatter before the runners, and checking the
vocabulary after that rebuild instead of in the root callback. What is missing is the row:
a squad stamped below 0.7 with an override, stopped once by the trailing repair, then re-run,
in the end-to-end table.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-11T20:58:23Z] Catherine Manager:
  - Home for this one is TASK-954 itself: the reconcile and the up-front vocabulary check (ST2, ST4) are expected to remove it, and ST3's shape table takes a row for a stopped run on a pre-0.7 squad with an override, re-run to completion. It stays Open until that row is green.
- [2026-10-11T22:02:12Z] Paul Reviewer:
  - Second route into this dead end, demonstrated on the reconcile pass: the 0.5 corpus with an override that only adds a ref kind and one undecodable bug file. The first `sq migrate up` is refused correctly (one unindexable file), but the index it wrote before refusing holds the carried entry as `UNRESOLVED-4`. After the file is corrected exactly as the message says, the second run is refused in the root callback with `type 'bug' prefix changed to 'BUG' ... ['UNRESOLVED-4']`. The cure is unchanged (the vocabulary check moved after the rebuild), and the end-to-end table needs this row beside the stopped-run one.
- [2026-10-12T06:02:32Z] Paul Reviewer:
  - Both routes driven on the code under review (0.5 corpus, an override adding a ref kind): the hand-edited status stops once at the check before the runners, the undecodable bug file stops once at the unindexable refusal, neither leaves an UNRESOLVED id in the index, and each re-run after the fix completes. Left Open for the end-to-end table row.
- [2026-10-15T18:21:41Z] Elias Python:
  - Fixed: tests/integration/test_a_behind_schema_squad_can_always_migrate_or_is_told_why.py::test_a_pre_0_7_squad_stopped_after_any_runner_is_resumed_to_the_uninterrupted_corpus runs the 0.5 corpus, with and without an override, stopped after each runner; every re-run completes with no UNRESOLVED id. The dead end does not reproduce on this tree.
- [2026-10-15T18:34:38Z] Paul Reviewer:
  - Verified by driving it on the code under review: the 0.5 corpus with a [ref_kinds.mirrors] override, stopped once by a hand-edited status (before any runner), once by an undecodable bug file (before any runner), and once by a hand-edited priority code (inside a runner, after earlier runners wrote). Each first run leaves the schema at 0.5 and no UNRESOLVED id; each re-run after the fix completes at 0.15 and sq check exits 0. The third stop names a refused command, recorded as F19.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Migrated-corpus goldens store one rendered surface nine times

<!-- sq:finding:F6:body -->
**What.** The migrated-corpus goldens under `tests/goldens/migrated_corpus/` are 319 files
holding 59 distinct contents. The other 260 are byte-identical copies, because nine of the
eleven corpora pass through the same 0.11 to 0.14 runner and it writes the same rendered
surface into each.

**Evidence, measured on the working tree.**

| Files | Copies | Distinct |
|---|---|---|
| `CLAUDE.md` | 9 | 1 |
| `.claude/**` | 117 | 13 |
| `agents/skills/**` | 112 | 14 |
| item files | 50 | 18 |
| `.squads.json`, `.squads.toml` | 20 | 12 |

One stub skill body alone is stored 63 times. The bytes are small (246 KB in all); the cost
is in the update. `tests/CONVENTIONS.md` section 6 asks for one golden per distinct rendering
path and calls goldens that differ only in one input redundant. Every edit to the managed
section, a pointer or a skill template will regenerate up to nine identical copies, and the
reviewer of that update reads the same hunk nine times, which is how a golden update stops
being read.

The goldens themselves are right: the test passes against them on the unchanged sources at
`1a96e516`, a changed written field turns nine rows red with a readable diff, and none of the
files is git-ignored.

**What would fix it.** Record the rendered surface (`CLAUDE.md`, `.claude/**`,
`agents/skills/**`) once, from one corpus that passes through the 0.11 to 0.14 runner, and for
the other corpora assert their copy equals that one; keep per-corpus goldens for what really
differs between them (item files, the index, the config). That is about 60 files with the same
coverage and a single hunk per template edit.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-11T21:18:21Z] Elias Python:
  - Fixed: shared rendered files stored once under goldens/migrated_corpus/_shared with a per-corpus SHARED.txt; 88 files from 319; UPDATE_GOLDENS regenerates; one written field and one template line each turn nine rows red
- [2026-10-11T22:02:07Z] Paul Reviewer:
  - Verified: 88 files, a shared file stored once and named in each corpus's SHARED.txt. Rebuilding every corpus's expectation from its own files plus the shared ones gives the 308 files and eleven REMOVED lists verified in the first pass, byte for byte, and no shared file is unlisted. Changing one corpus's input (the 0.8 role's name) fails that corpus's row alone, on the shared CLAUDE.md, with the diff shown. Small: under UPDATE_GOLDENS=1 with parallel workers the eleven comparison rows can read the folder while the regenerating test rewrites it, so run that one with -n0.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — A stray item file is indexed, written to, then strands the run

<!-- sq:finding:F7:body -->
**What.** The reconcile indexes an item-shaped file with a well-formed `id` wherever it sits
under the squad directory. The rest of the run only knows the declared type folders. So a
file outside them is indexed, the runners act on it, and the trailing repair then refuses the
whole run, with a cause that is false, after every runner has written. The schema is never
stamped and every re-run repeats. The unchanged code at `1226c372` migrates each of these
squads (exit 0).

**Evidence, demonstrated** on scratch squads stamped 0.14, old code against new.

| Shape | New behaviour |
|---|---|
| a milestone moved by hand into `squads/archive/` (its entry still at the old path) | re-indexed at `archive/...`, the 0.14 to 0.15 runner writes the tag and `updated_at` into the archived file, then exit 1 |
| an archived milestone the index never held, number 30 | indexed as `MILE-30`, counter raised to 30, the same write, then exit 1 |
| squad at the project root, `tests/fixtures/sample/tasks/TASK-000042-sample.md` | indexed as `TASK-42`, counter 42, then exit 1 |

The refusal in all three is the trailing repair's own
(`src/squads/_services/_maintenance.py:2444`):
`refusing to rebuild the index: the active workflow spec has re-foldered or re-prefixed a type
... revert the change in .overrides/workflow.toml`. None of these squads has an override. The
schema stays 0.14, the indexing is in no reflog line and no printed line, and a second
`sq migrate up` gives the same refusal. Moving the folder out of the squad directory lets the
run complete, but nothing says so, and the counter keeps the stray file's number.

`tests/service/test_index_reconcile_entry_rules.py::test_a_new_item_file_is_indexed_wherever_it_sits`
pins the indexing on the routine alone. No test drives such a file through `sq migrate up`.

**What would fix it.** The file has to be refused before the first runner writes, with its
path and a remedy the operator has: move it out of the squad directory, or back into its
type's folder. The reconcile cannot decide that (it resolves no folders), so it belongs to the
vocabulary check that runs after it. That check as specified would report this shape through
the override-blaming text and offer only "restore the declaration" or "correct the
frontmatter", so its rows need this one: an item whose file sits outside its type's folder on
a squad with no override. Add the pipeline row for it either way.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-12T04:49:19Z] Elias Python:
  - Fixed (A8): a file is the squad's item only at a location (directory plus prefix, from the previous index and the declared pairs); the tree is no longer walked, so strays are never opened, indexed, counted or written
- [2026-10-12T05:39:28Z] Elias Python:
  - Still Fixed under A11: with an index a location is an entry's directory and prefix; with none the tree is walked and the check before the first runner refuses what sits where no type lives (no index left behind)
- [2026-10-12T06:01:39Z] Paul Reviewer:
  - Verified against A8 and A11. With the index: the hand-archived milestone is dropped and named and the run completes; the never-indexed archived item and the lone fixture at a project root are ignored and the run completes, file untouched, counter unmoved. With no index: each is refused before any runner, the cause says there was no readable index, and no file in the squad changes.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — A refused run permanently raises the counter and padding

<!-- sq:finding:F8:body -->
**What.** The file-name digits of a candidate the reconcile rejects are folded into the
counter and padding floors (`src/squads/_index/_reconcile.py:166-171`), and the index is
written with them before the refusal (`:246-247`). The counter never goes down and padding is
one-way, so a run that reports "no migration has run ... the schema is unchanged" has already
changed how the squad numbers every future item, on the strength of a file that was never an
item of the squad.

**Evidence, demonstrated.** The 0.14 corpus (squad at the project root, counter 11,
padding 6) plus another tool's record `docs/decisions/ADR-20240115-use-postgres.md` carrying
`id: ADR-20240115` and no `type`.

1. `sq migrate up`: exit 1, the file named as unindexable. The index now reads
   `counter: 20240115`, `padding: 8`.
2. The file is moved out, as the message says. `sq migrate up`: exit 0, schema 0.15,
   `counter: 20240115`, `padding: 8`.
3. `sq create task`: the file is `tasks/TASK-20240116-next-task.md`.

The same corpus without the file ends at counter 11, padding 6, so a second run after the fix
is not equivalent to a first run on the fixed squad. A stray file that does get indexed
leaves its number behind the same way (counter 30 after the archive folder was moved out, in
the finding on stray files).

No test pins the rule: with the `self.note(cand)` call removed from `reject`, the three new
test modules and the six rewritten or related ones give 221 passed.

**What would fix it.** Take no floor from a file that is not indexed. A rejected candidate
that has a previous entry is already under the previous counter, and one that has none is
either corrected (then it is indexed and counted on the re-run) or taken out (then its number
is free). Add the row: a refused run followed by the remedy leaves the counter and padding a
first run on the fixed squad would.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-11T22:11:55Z] Elias Python:
  - Only an item accepted as the squad's own moves the counter or the padding.
- [2026-10-12T06:01:45Z] Paul Reviewer:
  - Verified: an undecodable tasks/TASK-99999999-junk.md leaves counter 18 and padding 6 after the refusal and after the remedy; the date-numbered record beside a squad with no index leaves no index after the refusal and counter 11, padding 6 once it is moved out. Both equal a first run on the fixed squad.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — An unreadable document that only looks like an item stops the run

<!-- sq:finding:F9:body -->
**What.** A file whose name has the shape `<letters>-<digits>-<anything>.md` is opened, and
when its bytes do not decode or its leading `---` block is not YAML it is reported as an item
file that cannot be indexed and the run is refused (`src/squads/_index/_reconcile.py:173-180`),
whether or not anything ever indexed it. The decision's rule is that a markdown file that is
not an item is never reported. The name pattern (`:31-32`) accepts lower-case words and any
number, so it matches ordinary documents: `chapter-1-intro.md`, `lesson-2-verbes.md`,
`RFC-2119-keywords.md`, `CVE-2024-1234.md`, `python-3-migration.md`.

**Evidence, demonstrated** on the 0.14 corpus (squad at the project root); the unchanged code
migrates both.

- `docs/lesson-2-verbes.md` saved in Latin-1: exit 1,
  `docs/lesson-2-verbes.md: ... is not valid UTF-8`.
- `docs/chapter-1-getting-started.md` opening with a Jekyll-style block whose title holds a
  colon: exit 1, `malformed frontmatter in docs/chapter-1-getting-started.md`.

The remedy offered is to correct the file or take it out of the squad directory, which at a
project root means out of the repository.

**Read, not driven.** The walk skips dot-directories only, so at a project root it also
covers ignored and vendored trees (`node_modules`, `venv`, `target`). Under a nested squad
directory the same applies to anything kept there, memory notes included: three of this
repository's own have the name shape (they parse, so nothing is reported today).

Parse-clean files of this kind are correctly ignored: `RFC-2119-keywords.md` with no
frontmatter and `CVE-2024-1234.md` with `id: 12` both pass.

**What would fix it.** A ruling is needed, because the routine cannot tell an unreadable item
from an unreadable bystander. Either report an unreadable candidate only when a previous
entry stands for it (the rule the subtask already uses for a file whose frontmatter parses
without an `id`), accepting that a never-indexed unreadable item is then left to the trailing
repair; or keep reporting them and narrow what counts as a candidate. Three rows of
`test_a_file_that_cannot_be_indexed_is_reported_and_its_entry_carried` pin today's choice.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-12T04:49:24Z] Elias Python:
  - Fixed (A9): location decides, not content: a file named for an item at a location that cannot be given an entry stops the run with or without an entry; look-alikes outside locations are never opened
- [2026-10-12T05:39:30Z] Elias Python:
  - Still Fixed under A11: with an index location decides; with none the name decides and a parse-clean file with no well-formed id is passed over; unreadable item-named files stop the run
- [2026-10-12T06:01:54Z] Paul Reviewer:
  - Verified against A9 and A11. With the index the Latin-1 and non-YAML look-alikes are never opened and the run completes. With no index both stop the run, as A11 rules for that state, with nothing written and the same result on a second run. The two parse-clean look-alikes pass in both states.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — A stopped run leaves no durable record of what the reconcile did

<!-- sq:finding:F10:body -->
**What.** What the reconcile dropped or indexed reaches the reflog only on the `migrate` line
written at the end of a completed run (`src/squads/_services/_maintenance.py:1688`). The index
is rewritten at the start (`:1659`). When the run stops in between, the change is made and
the only record is one line of terminal output; the next run reconciles against the already
rewritten index, finds nothing to report, and logs empty lists.

**Evidence, demonstrated.** A squad stamped 0.14 with `MILE-18`'s file deleted and one bug
file made undecodable.

1. First run: exit 1, `... The index was rebuilt first (dropped MILE-18 (no file backs it)).`
   No reflog line is written.
2. The bug file is corrected. Second run: exit 0. Its reflog lines read
   `"op":"repair" ... "missing":[]` and `"op":"migrate" ... "reconcile":{"indexed":[],"missing":[]}`.
3. The only reflog line naming `MILE-18` is its `create`.

The unchanged code records it: its `repair` line for the same squad carries
`"missing":["MILE-18"]`. The key on the `migrate` line was added so a dropped entry stays on
record; any stop after the reconcile defeats it: the unindexable refusal, a runner that
raises, the trailing repair's refusal. The stray-file finding is the same gap on the indexing
side (an entry gained, no line anywhere).

**What would fix it.** Write the record when the index is written, not when the run ends: a
`migrate` reflog line carrying the reconcile's counts and ids, appended right after the
overwrite whenever it indexed or dropped something. Add the row: refused run, fix, completed
run, and the dropped id is in the reflog.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-11T22:12:03Z] Elias Python:
  - The reconcile is logged on its own reflog line right after the index is written, before the refusal check.
- [2026-10-12T06:02:02Z] Paul Reviewer:
  - Verified: the refused run now leaves a migrate reflog line carrying the dropped id, written when the index is written, and it is still there after the corrected run completes. A refused run with no index writes neither index nor line, which is consistent.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Entries from a pre-0.7 index are reported as UNRESOLVED ids

<!-- sq:finding:F11:body -->
**What.** An index written before schema 0.7 stores neither `id` nor `prefix` on its entries.
The reconcile names a dropped entry by `entry.id` (`src/squads/_index/_reconcile.py:237`),
which for such an entry is the `UNRESOLVED` sentinel, so the printed line and the durable
reflog line name an id that never existed.

**Evidence, demonstrated.** The 0.5 corpus with `tasks/TASK-000003-implement-auth.md` removed:

- printed: `index reconciled with the files: dropped UNRESOLVED-3 (no file backs it)`;
- reflog: `"reconcile":{"indexed":[],"missing":["UNRESOLVED-3"]}`.

The entry's recorded path (`tasks/TASK-000003-implement-auth.md`) was in hand and names the
item exactly.

**Read.** `_Scan.prior` (`:148-159`) matches a moved file to its previous entry by number only
when `entry.prefix` equals the file name's prefix. For these entries the prefix is empty, so a
renamed or moved file that cannot be indexed is never matched: its entry is reported dropped
and the file unindexable, where on a newer index the entry is carried.

**What would fix it.** Report a dropped entry by its recorded path, or derive its prefix from
the path's file name when the entry has none, and use the same fallback in `prior`. Add a row
over one of the two oldest corpora to the dropped-entry test.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-11T22:12:12Z] Elias Python:
  - A prefixless entry is named by its recorded file name or path, and the previous-entry lookup uses the same fallback.
- [2026-10-12T06:02:10Z] Paul Reviewer:
  - Verified on the 0.5 corpus: the dropped entry is named TASK-3 on screen and in the reflog, no UNRESOLVED id appears in the output, the index or the reflog, and a renamed file that no longer decodes is matched to its entry by number and the entry carried.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Two ids sharing a number are refused with a false cause

<!-- sq:finding:F12:body -->
**What.** Two files with different ids that share one sequence number (a task and a bug both
numbered 15) are grouped by number and each is reported as a duplicate of the other's id
(`src/squads/_index/_reconcile.py:197-210`). The cause printed is false, and it hides what the
operator has to do.

**Evidence, demonstrated** on a squad stamped 0.14 holding `tasks/TASK-000015-implement-auth.md`
(`id: TASK-15`, indexed) and `bugs/BUG-000015-clashing-bug.md` (`id: BUG-15`).

- Unchanged code: exit 0, schema 0.15, and the index holds `BUG-15` in place of `TASK-15`.
  The task is silently gone from the index.
- Changed code: exit 1, schema unchanged, with
  `bugs/BUG-000015-clashing-bug.md: id BUG-15 is also claimed by tasks/TASK-000015-implement-auth.md`
  and the mirror line. The task file claims `TASK-15`, not `BUG-15`.

Refusing is right: the index holds one entry per number, so one of the two could not be
given an entry, and the old outcome was a silent loss. What is wrong is the sentence, and the
way out. The remedy line says to correct the file or take it out. The correction is a
renumber by hand: I gave the bug number 19 (one above the counter), renamed the file, set
`id` and `sequence_id`, and the re-run completed with `indexed BUG-19`. The commands that do
this, `sq repair --renumber` and `sq renumber`, are refused behind the schema gate.

**What would fix it.** Say what is shared: "number 15 is used by both TASK-15 (path) and
BUG-15 (path); the index holds one item per number". Keep "is also claimed by" for two files
with the same id. State the hand remedy for a shared number (a number above the counter, the
file name, `id`, `sequence_id`, and the refs that name it). Whether a renumber should be
available behind the gate is a question for the decision, not for this routine.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-12T04:49:35Z] Elias Python:
  - Fixed (A10): two ids sharing a number are refused with the number, both ids and paths, and a by-hand renumber remedy (next free number printed); 'also claimed by' kept for one id in two files
- [2026-10-12T05:39:33Z] Elias Python:
  - Still Fixed under A11/A10: unchanged, two ids sharing a number are refused naming the number, both ids and paths, with the by-hand renumber
- [2026-10-12T06:02:21Z] Paul Reviewer:
  - Verified against A10, with and without an index: the cause names number 15, both ids and both paths and that the index holds one item per number; the renumber by hand is spelled out with number 19; no command is printed. The release it names is the subject of F14.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Docs and one test still describe the skip-and-carry-on behaviour

<!-- sq:finding:F13:body -->
**What.** Three places still describe behaviour this change reversed, and one rewritten test
no longer covers what it was written for.

**Adopter-facing text, read. For the writer.**

- `docs/workflow.md:469-472`: "A document the migration cannot safely rewrite is skipped
  rather than aborting the run, and named by id: a milestone whose file is missing, ...". A
  missing file is now dropped from the index before any runner and named on the
  `index reconciled with the files` line; a file that cannot be read or parsed now stops the
  run before anything is migrated.
- `docs/migration.md:19` and `:51`, `docs/stability.md:28` and `:287`: `sq migrate up` is
  described as runners, index rebuild, stamp. It now rebuilds the index from the files first,
  can refuse with exit 1 having migrated nothing, and prints a reconcile line.
- The unreleased changelog section has no entry for either.
- `src/squads/_cli/_migrate.py:79-80` and the 0.14 to 0.15 manual text
  (`src/squads/_migrations/_v0_14_to_v0_15.py:183`) tell the operator that a skipped item may
  be one with "a missing file". The reconcile now drops such an entry before any runner sees
  it.

**Tests, read.**

- `tests/service/test_milestone_roll_up_tag_migration.py`, the test renamed to
  `test_every_eligible_item_missing_its_file_still_reaches_current_and_reports_zero_changed`:
  it pinned that a run in which the runner skips every eligible item still stamps and reports
  zero. It now deletes both files, so the runner skips nothing and that case is uncovered.
- `tests/cli/test_migrate_up_bare_subprocess_exit_parity.py:1-2`: the module docstring still
  says the exit comes from the trailing repair.

The other rewrites hold. Three reverse a behaviour the amended decision reverses (an entry
whose file is gone is dropped and named; an item file that cannot be indexed stops the run)
and still assert the exit code, the named file or id and the stamp: the bare-subprocess test,
the corridor parity row and the two milestone tests that delete a file. The stand-in in
`tests/service/test_type_invalid_frontmatter_load_boundary.py` only gained the new keyword.

**What would fix it.** The documentation lines above. In the test, keep the original case with
a damage the runner still skips (no body region, or a tag moved out of it) and keep the
missing-file case beside it. Correct the docstring.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-11T22:12:19Z] Elias Python:
  - Fixed in code and tests; the documentation lines it lists remain for the tech writer.
- [2026-10-12T06:02:28Z] Paul Reviewer:
  - Back to Open for the documentation half only. The code and test half holds: the runner-skips-everything case is back beside the missing-file one, the module docstring is right, and the skip message and manual text no longer mention a missing file. The docs lines listed are untouched, and they now also owe the two refusals of the check before the runners, the no-index refusal and its remedies. CLAUDE.md's module list does not name _index/_reconcile.py or _services/_corpus_fit.py. Not blocking.
- [2026-10-15T18:27:43Z] Theo Writer:
  - Documentation half done: docs/workflow.md (seeded views: a missing milestone file is now dropped by the index rebuild and named on the reconcile line; an unreadable file stops the run; rename-type/rename-status need a current squad), docs/migration.md (TL;DR line, `sq migrate up` row, new "What runs on an out-of-date squad" and "Before the first runner" sections covering the reconcile line, the unindexable and vocabulary refusals, the no-index remedy, the override refusal, the index-full and still-at-schema endings), docs/stability.md (schema paragraph, migrate surface, gate scope), and two Changed entries in CHANGELOG 0.16.0. The code and test half was already confirmed by the reviewer. Fixed.
- [2026-10-15T18:51:03Z] Paul Reviewer:
  - CLAUDE.md leftover verified by reading: the module list now names _index/_reconcile.py and _services/_corpus_fit.py, and the latter line still holds with the badge check added. The runner docstring leftover is recorded as F25. The docs half was not re-read in this pass because the writer is still editing docs/; it also owes the behaviour this pass changed: the notice gone while behind, and --dir on a project-root squad now meeting the gate. Left Fixed pending that read.
- [2026-10-15T19:17:09Z] Paul Reviewer:
  - Docs half verified by reading docs/migration.md, docs/faq.md, docs/workflow.md, docs/stability.md and the 0.16.0 CHANGELOG entries against the behaviour driven in passes 5 to 8. The reconcile line, the refusals before the first runner (unindexable, vocabulary, badge codes including non-string values, an override that does not load), the closing line, the full-index refusal, the gate table by direction, --help as an option of its own (including -m -m --help), the notice suppressed while behind, and --dir for project-root, multi-level, symlinked, not-the-squad-folder and outside-tree squads all match. Two small imprecisions, not blocking: the stability.md migrate-up line omits the override-load refusal, and the CHANGELOG outside-tree sentence does not carve out the F28 shapes (WontFix).
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Refusals name the last-sync release, not one that reads the schema

<!-- sq:finding:F14:body -->
**What.** Three refusals send the operator to "the squads release this squad is stamped for
(vX)": the no-index refusal, the unindexed-file refusal and the renumber note. X is
`config.squads_version` (`src/squads/_services/_maintenance.py:1738`), which records the
release that last ran `sq sync`, not the release the squad's schema belongs to. On a squad
that was migrated and not synced afterwards the two differ, and the release named cannot open
the squad.

**Evidence, demonstrated.** The 0.8, 0.10, 0.11 and 0.14 corpus fixtures all carry
`squads_version = "0.7.0"`. With the index removed beside an archived item, or with an
unindexed first epic, each refusal names `v0.7.0`. Releases installed from the package index
into scratch environments, then `sq repair` on the 0.14 squad:

- 0.7.0, the one named: `this squad is at schema v0.14, newer than squads 0.7.0 (v0.7).
  Upgrade the squads package.` No index is written.
- 0.14.0, the one that reads schema 0.14: the index is rebuilt, and the next
  `sq migrate up` completes.

A fresh squad stamps both together, so the name is right for a squad synced by a release of
its own schema.

**What would fix it.** Name the release from the schema stamp, which the registry already maps:
the migration whose `to_schema` is the squad's schema carries the release that introduced it.
Say "a squads release that reads schema v0.14 (0.14.0 is one)" and keep `squads_version` out
of it. Add a row with the two stamps apart.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-12T06:33:13Z] Elias Python:
  - Fixed: refusals name a release that reads the squad's schema (from the migration registry), never the last-sync version; row per stamped schema 0.3 to 0.14
- [2026-10-12T06:44:44Z] Paul Reviewer:
  - Verified with the real releases: for squads stamped 0.3, 0.5, 0.7, 0.8, 0.10, 0.11 and 0.14 the message names 0.3.0, 0.5.0, 0.7.0, 0.8.0, 0.10.0, 0.11.0 and 0.14.0; each opens its squad and rebuilds the index, and the next run completes, for the no-index refusal and for the unindexed first item. The last-sync release is no longer mentioned. Residual, fixture only: stamp 0.4 is told 0.5.0, which refuses it; no release stamps 0.4.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — A declared folder spelled with a trailing slash stops the run

<!-- sq:finding:F15:body -->
**What.** The check before the first runner compares the declared folder as the override
spells it with the directory of each recorded path (`src/squads/_services/_corpus_fit.py:24`
and `:57`). A folder written `incidents/` or `./incidents` loads, creates and lists items at
the current schema, and never equals `incidents`, so every item of the type is reported as
sitting where no type lives.

**Evidence, demonstrated.** A squad at the current schema with a valid override declaring
`[items.incident] folder = "incidents/"`, one incident created through the CLI, stamped back
to 0.14.

- Unchanged code at `1b2e57e5`: `sq migrate up` exits 0, schema 0.15.
- Changed code: exit 1,
  `these indexed files sit where no type of this squad lives: - incidents/INC-000019-custom-one.md (INC-19; its type lives in incidents//)`
  with the remedy to move the file into the folder its type lives in, which is where it is.

The same with `folder = "./incidents"` (`its type lives in ./incidents/`). This is a refusal
of a corpus the completed run accepts, which the decision bounds the check against.

**What would fix it.** Normalise both sides to one spelling before comparing (the declared
folder and the recorded path's directory as normalised relative POSIX paths), in the first
question and in the path the second question builds. Add both spellings as rows of the
vocabulary table.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-12T06:33:35Z] Elias Python:
  - Fixed: both questions compare normalised paths; rows for trailing slash, ./, both and a nested folder, indexed and with no index
- [2026-10-12T06:44:52Z] Paul Reviewer:
  - Verified: a folder declared with a trailing slash and one with a leading ./ both complete, with an index and with none, as the unchanged code does where it has an answer.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — A hand-edited type is refused as a spec change the run accepts

<!-- sq:finding:F16:body -->
**What.** The check runs the whole override cross-check (`validate_against_index`) on every
squad (`src/squads/_services/_corpus_fit.py:108`). Its prefix and folder alignment half exists
to catch an override that re-prefixes or re-folders a type; at the current schema it runs only
when the squad has an override. On a squad with none it now fires on an item whose `type` was
edited by hand, a corpus the completed run accepts, and the cause it prints is about a spec
change and an override that do not exist.

**Evidence, demonstrated.** A squad stamped 0.14 with no override, the bug file's `type: bug`
edited to `type: task`.

- Unchanged code: exit 0, schema 0.15. The item is indexed as `BUG-16` of type `task`,
  `sq list` works, and `sq check` reports it (`status 'Open' invalid for task`).
- Changed code: exit 1,
  `type 'task' prefix changed to 'TASK' in the workflow spec, but 1 live item(s) are still filed under the old prefix: ['BUG-16'] — revert the prefix in the override, or change it only while 'task' has no items`
  and the same for the folder. Nothing names the field that is wrong.

The decision bounds the check to what the load boundary refuses at the current schema. For a
squad without an override that is a type, a status, a sub-entity status and a badge code, not
alignment. The one phrase the module strips for such a squad (`_OVERRIDE_HINT`, `:20`) is
matched against another module's wording and does not cover these two sentences.

**What would fix it.** Without an override, run only the families the store's own load
refuses; keep the alignment half for a squad that has one. If a mistyped item should stop the
run anyway, that is a ruling, and its cause should name the item, its `type` and its id's
prefix, with no mention of a spec change. Add the row.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-12T06:33:55Z] Elias Python:
  - Fixed: without an override the check asks only the families the store's load refuses (alignment left out); a hand-edited type migrates, with an override it is refused naming it
- [2026-10-12T06:45:04Z] Paul Reviewer:
  - Verified: with no override the hand-edited type migrates and no line mentions an override. Beside an override it is refused before any runner naming that override, which is inside the bound: the unchanged code completes that run and leaves a squad every command then refuses at load. The keyword defaults to the old behaviour and the one other caller does not pass it.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — A prefix with an underscore or leading digit is never reconciled

<!-- sq:finding:F17:body -->
**What.** Both the reconcile and the check's second question recognise an item file through
one name pattern whose prefix is letters and digits in hyphen-joined segments that each start
with a letter (`src/squads/_index/_reconcile.py:35`). The workflow spec puts no such limit on
a type's prefix. A type declared with `prefix = "MY_INC"` or `prefix = "2FA"` loads, creates
items and migrates today, and its files match neither the walk, nor a location, nor the
second question (`src/squads/_services/_corpus_fit.py:56`).

**Evidence, demonstrated.** A squad at the current schema with a valid override declaring
such a type, one item created through the CLI (`incidents/MY_INC-000019-custom-one.md`),
stamped back to 0.14, index removed.

- `sq migrate up` exits 0. The reconcile line and the reflog list eighteen ids and not
  `MY_INC-19`.
- The item is in the index afterwards, put there by the trailing repair, after every runner.

So the runners ran over an index that did not hold it and the schema was stamped, which is
what the reconcile and the second question exist to prevent. With an index the entry is kept
as it was and never refreshed from its file, and an unindexed file of that type is seen by
neither step. `prefix = "my-inc"` in a nested folder is handled.

**Read.** No shipped runner acts on a custom type's items today, so nothing is left
unmigrated yet; the guarantee is what is missing.

**What would fix it.** The second question holds the vocabulary, so it can list files by the
declared prefix itself and refuse the ones with no entry; that closes the stamp-past without
touching the routine. Whether the routine's pattern should widen, or the spec should refuse a
prefix the pattern cannot read, is for the decision. Add rows for both prefixes.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-10-12T06:34:11Z] Elias Python:
  - Fixed per the architect's ruling: locations take the entry's own prefix spelling and match literally, ids use the model's parser, the walk shape is widened, both questions compare by declared spelling; rows for MY_INC, 2FA and a dotted prefix
- [2026-10-12T06:45:13Z] Paul Reviewer:
  - Verified against the ruling: MY_INC and 2FA are indexed before the runners with an index and with none, and a second unindexed MY_INC item in the same folder gains an entry. A dotted prefix with no index is refused by the second question with no index left, and completes with one. What the wider walk and id shape now take in is listed in the review body.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — The check's refusal overstates its remedy and omits the rebuild

<!-- sq:finding:F18:body -->
**What.** Two things in the text of the check's refusals.

**1. The remedy for an indexed file where no type lives always sends the operator to another
release.** It reads "move each file into the folder its type lives in and have its index
entry rebuilt by the squads release this squad is stamped for"
(`src/squads/_services/_corpus_fit.py:81`).

Demonstrated on a squad stamped 0.14 whose index records `MILE-18` at
`archive/MILE-000018-ship-two.md`:

- with another milestone indexed in `milestones/`: after the file is moved there, the next
  `sq migrate up` completes on its own. The rebuild finds the file through the folder the
  index already knows.
- with no other milestone indexed: after the move the next run drops the entry and refuses
  the file as unindexed, and then the other release is needed, as the developer reported.

So the second half of the sentence is needed only when the type's folder holds no indexed
item, and the message cannot tell the operator which case they are in.

**2. A refusal from the check does not say what the rebuild did.** The unindexable refusal
ends with "The index was rebuilt first (dropped ...)". The check's three refusals go through
`_refusal` (`:120`), which has no such note. In the second variant above the run that refuses
`milestones/MILE-000018-ship-two.md` has just dropped `MILE-18` from the index; the reflog
line records it, the screen does not.

Nothing is lost in either case: the file is untouched and the drop is in the reflog.

**What would fix it.** Say "move each file into the folder its type lives in, then re-run; if
the run then reports the file as having no entry, ..." and let the second refusal carry the
other release. Append the same rebuilt-first note to the check's refusals when the rebuild
indexed or dropped something.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-10-12T06:34:26Z] Elias Python:
  - Fixed: the misplaced-file remedy says move it back and re-run (the second refusal carries the other release), and the check's refusals carry the rebuilt-first note
- [2026-10-12T06:45:20Z] Paul Reviewer:
  - Verified: the misplaced-file remedy says to move the file and re-run, and that is enough when the folder holds another indexed item. When it does not, the next refusal carries the release and ends with what the rebuild dropped, on screen as well as in the reflog.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — A hand-edited badge code stops the run naming sq repair

<!-- sq:finding:F19:body -->
**What.** A hand-edited badge code that no override removed passes the check before the first runner, then stops the run inside the first runner that opens the index. The refusal names `sq repair`, which the gate refuses on a squad that is behind. The closing line is appended after it, so the operator is told two things to run, and one of them is refused.

**Evidence, driven** (scratch copies of the 0.14 corpus and the 0.5 corpus, through `sq migrate up`):

- 0.14 corpus, `priority: urgentest` added to `tasks/TASK-000003-implement-auth.md`. Exit 1, schema stays 0.14:
  `error: TASK-3 field 'priority' has code 'urgentest', which the active workflow spec's 'priority' collection does not declare; fix the frontmatter value to a currently valid code, or run `sq repair` if the index itself is merely stale` and then the closing line.
- 0.14 corpus, the first finding of `REV-000006` set to `severity: catastrophic`. Same refusal, worded for the sub-entity.
- 0.5 corpus plus a `[ref_kinds.mirrors]` override, the same priority edit. Same refusal, schema stays 0.5.

**Mechanism, read.** `validate_against_index`, which the check before the runners calls, reports a stranded badge code only when an override removed that code (`_collect_badge_alignment_errors` and `_code_removed_by_override` in `_workflow/_loader.py`). The store's load check, `_validate_badge_codes` and `_check_field_codes` in `_index/_store.py`, reports every stranded code. That second check is first reached inside a runner's `IndexStore.load()`, and its text carries the `sq repair` clause. The hand-back says these store refusals are unreachable after the reconcile and the check. That was inferred from the shapes tried, and this shape was not among them.

**What would fix it.** Have the check before the runners ask what the store's load asks, including every stranded badge code, whatever its cause. The refusal then comes before any runner, with the same hand-fix remedy the other corpus-fit refusals give. Add hand-edited item and sub-entity badge codes, with and without an override, to the refusal table in `test_a_refused_migrate_up_names_only_commands_the_gate_permits.py` and to the end-to-end table.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-10-15T18:50:39Z] Paul Reviewer:
  - Verified, driven: the badge check now refuses before any runner, with a hand-fix remedy and no refused command, for an item priority, a finding severity, a custom sub-entity field (extra.impact on a finding), a custom item field on a type of the squad own (extra.impact on an incident) and an int value. A good custom value completes. Non-string custom values crash instead; recorded as F24.
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — The version notice names sq sync on every behind migrate run

<!-- sq:finding:F20:body -->
**What.** On a squad that is behind, every `sq migrate up`, `help` and `chlog` begins with `squads 0.15.0 detected (managed files at X). Run `sq sync` to refresh them.` `sq sync` is refused in that state. A run that is refused, or that stops, ends with this line still in its output. The tests that carry the remedy rule start reading the output at `error:`, so they never see the line.

**Evidence, driven.** Every refused run in this pass printed the line first, for example on the 0.14 corpus, whose `squads_version` is 0.7.0. The root callback calls `version_notice()` after `require_current_schema`. For every other command the gate exits before the notice, so on a squad that is behind it only reaches the three granted `migrate` commands. A squad that is behind was last synced by an older release, so in practice the notice prints on every run.

**Evidence, read.** `tests/integration/test_a_refused_migrate_up_names_only_commands_the_gate_permits.py` (for example lines 173 and 210) and `_error_text` in the end-to-end module both check `output[output.index("error:"):]`. ADR-955 A7 says the binding test covers "every `sq` command the output names".

**What would fix it.** Suppress the notice while the schema differs from the package's. While the squad is behind, the useful next step is `sq migrate up`, and the run that completes already ends with "run `sq sync` to refresh managed files". Alternatively, word the notice per direction. Either way, run the invariant over the whole output and not the slice after `error:`.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
- [2026-10-15T18:50:42Z] Paul Reviewer:
  - Verified, driven: on a squad that is behind, migrate up (refused and completing), help and chlog print no sq sync notice; once current, the notice is back on sq list, and the completed run still ends with its own run sq sync line.
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — An argument equal to -h or --help lets any command past the gate

<!-- sq:finding:F21:body -->
**What.** `apply_gate` returns early when `"--help"` or `"-h"` appears anywhere in `sys.argv` (`src/squads/_cli/_common.py`, first line of `apply_gate`). `-h` is not a help option of this CLI (`sq list -h` is a usage error), so any argument equal to `-h` or `--help` lets a command past the gate in either direction. Pre-existing in `require_current_schema`, and carried into the shared refusal both gates now call.

**Evidence, driven** (nested scratch squad stamped 0.14):

- `sq task 21 comment --as manager -m -h`: `commented on TASK-21 as manager`, task file, index and reflog written, schema still 0.14.
- `sq create task --author manager -- --help`: creates `TASK-000023-help.md` on the squad that is behind.
- No `sq migrate` verb is exploitable today: `repad` takes an integer, and `rename-type` and `rename-status` refuse an undeclared name. The `migrate` gate has the same hole for any future verb that takes free text.

**What would fix it.** Stop matching `-h`, which is not a help option. The check cannot simply be dropped: the group callbacks run before the leaf command parses its own eager `--help`, so `sq list --help` and `sq migrate repad 7 --help` depend on it. Bypass only when `--help` is a real option token of the invoked command. That means before any `--`, not consumed as an option's value, read from the arguments Click hands the subcommand, or decided after parsing by gating in the leaf. Add the two rows above to the gate table.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
- [2026-10-15T18:50:44Z] Paul Reviewer:
  - Verified, driven on a squad that is behind: -m -h, --message --help, -m a -m --help, --as=manager -m --help, --desc --help on create, --title --help on update, and --help after -- are all refused by the gate with nothing written, and repad --help 7 still shows help. Two residuals, neither a write: a bundled short flag (list -as --help) gets past, because -as is not in the value set, and list then refuses --help as a status; and -m -m --help, which Click treats as a real help request, is refused by the gate. Neither earns a finding.
- [2026-10-15T19:02:50Z] Paul Reviewer:
  - Residual re-driven: -m -m --help now shows help; -m -m -m --help and -m -h are gated with nothing written. list -as --help still gets past the gate (the bundle is not split) and list then refuses the status; read-only, no finding.
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — Remedy checks miss placeholder commands and indirect raises

<!-- sq:finding:F22:body -->
**What.** Both remedy checks match `\bsq ([a-z][\w-]*)`, so a remedy shaped with a placeholder (`` `sq <type> <n> status X --force` ``, `` `sq <type> <n> ref rm <target>` ``, both of which exist in the loader) is invisible to them. The static guard also misses refused commands that reach a `raise` indirectly.

**Evidence, driven.** Feeding `_violations` from `tests/meta/test_a_migration_runner_never_raises_a_refused_command.py`: a module constant raised by name, a local variable raised, a helper's return value raised, a placeholder-shaped command in a raise literal, and `itf.skew_message(...)` through a module alias. All five return no hit. The guard's docstring lists none of these limits.

**Why it matters, inferred.** No placeholder-shaped remedy is reachable from a behind run in any shape driven here, so nothing is wrong today. But the one refusal this pass found (F19) comes from code a runner calls (the store), not from a runner module, which is outside the static guard by construction. The behavioural table is the only real net, and its pattern decides what it can see.

**What would fix it.** Extend the pattern to `sq <...>` and treat any first word not in the permitted set as refused. In the guard's docstring, state that it reads literals inside `raise` in runner modules only.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
- [2026-10-15T18:50:46Z] Paul Reviewer:
  - Verified, driven: the guard now flags a module constant raised by name, a local variable, a placeholder command and a module-attribute use of skew_message, and the docstring states its limits. Still unseen and undeclared (minor): an annotated assignment (MSG: str = ...), string concatenation and percent-formatting. The behavioural tables use the same placeholder-aware pattern.
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — A project-root squad named with --dir skips the gate and its config

<!-- sq:finding:F23:body -->
**What.** For a squad whose `squad_dir` is `"."` (a squad at the project root, which A2 supports), `--dir <squad folder>` never reads the squad's `.squads.toml`. `resolve()` (`src/squads/_paths.py:131-140`) looks for the config in the folder's parent. It finds none and builds a default `SquadsConfig`, whose `schema_version` is the package's own, so both the root gate and the `migrate` gate see a current squad. This lets every ungranted command through, in both directions. Pre-existing: the same `sq migrate repad 7` run against `git archive HEAD` sources renames every file in the same way.

**Evidence, driven** (scratch copies of the 0.14 corpus, stamped 0.14, invoked from the parent directory with `--dir`):

- `sq --dir <squad> migrate repad 7`: exit 0, `11 file(s) renamed; index rebuilt`, 24 paths changed, schema still 0.14.
- `sq --dir <squad> repair`: exit 0, `stripped retired regions from 4 item files`, four item files rewritten by the current sweep, schema still 0.14. This is the very operation the gate exists to stop.
- `sq --dir <squad> list` runs. `sq --dir <squad> migrate up` prints `already at schema v0.15; nothing to migrate` and exits 0 on a squad stamped 0.14.
- The same commands without `--dir`, from inside the squad, are refused, as are all of them on a nested squad named with `--dir` (the 72-row matrix in this pass).

**Evidence, read.** `test_the_gate_holds_when_the_squad_is_named_with_dir_from_outside_it` (`tests/cli/test_the_gate_lets_past_by_command_and_direction.py:140`) moves the fixture into a nested `squads/` folder before it runs, so the project-root layout, which is the one that fails, is not covered.

**What would fix it.** In `resolve()`, when `--dir` names a folder that holds its own `.squads.toml` whose `squad_dir` is `"."`, read that config, and never synthesise a config whose stamp is the package's for a folder that has one. Add a project-root `--dir` row to the gate table. This may belong in a bug of its own, since the cause is in `resolve()`, but the gate's guarantee depends on it.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
- [2026-10-15T18:51:01Z] Paul Reviewer:
  - Reopened. The fix covers `squad_dir = "."` spelled exactly that way, and nothing else. Driven with a fresh squad stamped 0.14 per row, invoked from outside with `--dir`:
    
    | Layout | `--dir` | `list` | `migrate up` |
    |---|---|---|---|
    | project root, `"."` | the folder, with a trailing `/`, `/.`, a `..` path, a symlink | refused | migrates |
    | nested, `"squads"` | the folder, with a trailing `/`, a symlink | refused | migrates |
    | `"./squads"`, or folder renamed from `squads` to `team` | the folder | refused | migrates |
    | project root, `"./"` | the folder | **runs** | **"nothing to migrate", exit 0** |
    | two levels, `"work/squad"` | the folder | **runs** | **"nothing to migrate", exit 0** |
    | nested, `"squads"` | the **project root** | "missing index; run `sq repair`" | **"nothing to migrate", exit 0** |
    
    What gets through:
    - `squad_dir = "work/squad"`, `sq --dir <root>/work/squad repair`: four item files rewritten, schema still 0.14, the same harm as the original row.
    - A nested squad with `--dir` at the project root: `sq --dir <root> repair` writes an empty `.squads.json` and a `.reflog.jsonl` at the project root, beside the real squad. The folder holds a `.squads.toml`, so "never synthesise a current-stamp config for a folder that holds one" is not what the code does: the check is `squad_dir == "."` and not "the folder holds a config".
    - `"./"` is a spelling the walk-up from inside accepts and gates. With `--dir` it falls through to the parent lookup, because the comparison is on the raw string.
    
    What would fix it: find the config by walking up from the `--dir` folder to the first `.squads.toml`, and accept it only when its root plus `squad_dir` (normalised) resolves to that folder. Refuse when a config is found that does not point at the folder, and never fall back to a synthesised config when any `.squads.toml` sits at or above it. Add the three bold rows to the gate table.
- [2026-10-15T19:02:43Z] Paul Reviewer:
  - Verified, driven: the three pass-6 rows are now gated with nothing written (squad_dir "./", "work/squad", and --dir at the project root of a nested squad, which is now refused by name). Also gated: a root-layout squad inside another squad folder, a nested project under another project root, an outer behind squad with a current one below it; a folder between two configs and a missing folder inside a squad tree are refused. Faithful reverts of the gate test in a scratch copy: back to the HEAD resolve, 45 red, including every root-layout row (list, repair and repad behind; list, repair, repad and up ahead) while the nested and symlinked rows stay green; back to the pass-6 "." check, 38 red (the dot-slash and multi-level rows and the not-own-folder table) with the root rows green. Residual: a squad_dir that leaves the project tree, recorded as F26.
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — A list or mapping in a custom badge field crashes migrate up

<!-- sq:finding:F24:body -->
**What.** A custom badge field (stored under `extra`) whose value is a YAML list or mapping makes `sq migrate up` crash with a traceback. The process exits 1, the schema is unchanged and nothing is written, but the message names neither the file nor the field.

**Evidence, driven** (0.14 corpus, index removed, an override declaring `[collections.level]` and an `incident` type with `fields = [{ code = "impact", collection = "level" }]`, plus one incident file):

- `extra: {impact: [high, low]}`: `TypeError: cannot use 'list' as a set element (unhashable type: 'list')`, raised from `_badge_field_mismatches` in `_workflow/_loader.py` (`value not in coll.badge_codes`), which the corpus-fit check calls through `validate_against_index`.
- `extra: {impact: {a: 1}}`: the same, with `dict`.
- For comparison, `impact: 3` is refused cleanly by the new check, which names `INC-20` and the field. A list or int in `priority` is reported as unindexable. Only `extra`-stored fields reach the comparison without a type check.

**Read.** The same unguarded `in frozenset` comparison exists three times: in the loader collector, in the store's `_check_field_codes`, and in the new `badge_code_problems`. That last one copies the store's predicate instead of sharing it, so the two can drift.

**What would fix it.** One shared predicate for "this stored value is a code of that collection", treating anything that is not a string as undeclared. Make the loader, the store load and the corpus-fit check call it. Add a list and a mapping row to the badge rows of the refusal table.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
- [2026-10-15T19:02:46Z] Paul Reviewer:
  - Verified, driven: a list, a mapping, an int and an undeclared string in a custom item field, and a list in a custom sub-entity field, are each refused before any runner, with the file named; a good value completes. At the current schema, list and check now report the list value cleanly instead of crashing.
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — The 0.14 to 0.15 runner docstring still states two false things

<!-- sq:finding:F25:body -->
**What.** The rewritten paragraph in `src/squads/_migrations/_v0_14_to_v0_15.py` (module docstring, around line 99) states two things that are not true.

- "Every condition this runner can act on or decline becomes a skip": a condition the runner acts on is not a skip. The list that follows is headed "conditions this runner meets and does not act on".
- Its example, "frontmatter that does not parse in a milestone file stops the run from inside it". Driven on the 0.14 corpus: a milestone with frontmatter that does not parse is now refused before any runner ("no migration has run: 1 item file(s) cannot be given an index entry"), so this runner never meets it.

**What would fix it.** Say that every condition the runner declines is a skip reported by item id, and that a run stopped by what it calls is resumed by re-running `sq migrate up`. Either drop the example or replace it with one that still happens, such as a file that becomes unreadable during the run.
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
- [2026-10-15T19:02:48Z] Paul Reviewer:
  - Verified by reading: the paragraph now says declined conditions are skips, that a stop from what the runner calls is resumed by sq migrate up, and that an unparseable item file is refused before any runner (driven in pass 6). The false example is gone.
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->

<!-- sq:finding:F26 -->
### F26 — A squad folder outside its project tree still skips the gate with --dir

<!-- sq:finding:F26:body -->
**What.** `resolve()` now finds a `--dir` folder's config by walking up from that folder. A config whose `squad_dir` points outside its own directory tree (`"../shared"`, or an absolute path) is never on that walk. `--dir` at that squad folder then finds no config, gets a synthesised config stamped at the package's schema, and passes the gate. Walk-up resolution from the project directory reads the same config and gates correctly. `SquadsConfig.squad_dir` accepts both spellings, and docs/faq.md describes `squad_dir` as relative to the `.squads.toml`.

**Evidence, driven** (0.14 corpus; `proj/.squads.toml` with `squad_dir = "../shared"`, items in the sibling `shared/`):

- From inside `proj`, `sq list` is refused with the behind message.
- `sq --dir shared list` runs. `sq --dir shared migrate up` prints "already at schema v0.15; nothing to migrate" and exits 0.
- `sq --dir shared repair`: four item files rewritten, `.squads.json` rebuilt and `.reflog.jsonl` written, schema still 0.14.
- The same with `squad_dir` set to the absolute path of the folder: `repair` writes.

**What would fix it.** When no config is found above the folder, do not treat the folder as current. Its `.squads.json` carries the corpus's own `schema_version` (0.14 here), so the gate can read that stamp, or refuse a folder that holds squad data but no reachable config. Add an upward-escaping row and an absolute row to the `--dir` table.
<!-- sq:finding:F26:body:end -->

#### Discussion

<!-- sq:finding:F26:discussion -->
- [2026-10-15T19:14:47Z] Paul Reviewer:
  - Verified, driven: an outside-tree squad (relative and absolute squad_dir) is refused by name with --dir, with its index and with the index removed, and nothing is written. Falsified in a scratch copy: disabling the check turns exactly the 24 outside-relative and outside-absolute rows red. Current outside-tree squads are refused with --dir too and told to run from the project directory, which is acceptable for one release. The heuristic gaps and the one false positive are recorded as F28 (low, not blocking).
<!-- sq:finding:F26:discussion:end -->
<!-- sq:finding:F26:end -->

<!-- sq:finding:F27 -->
### F27 — resolve() documents a require_init caller that does not exist

<!-- sq:finding:F27:body -->
**What.** The `require_init` parameter of `resolve()` is documented as "used by `init` itself", but no caller passes `require_init=False` (`grep -rn "require_init=False" src` matches only the docstring). The new branch that falls back to a default config for a mismatched `--dir` folder when `require_init` is false is therefore unreachable. The hand-back's caveat that "`sq init --dir X` inside an existing squad's tree still falls back to the default config" describes that dead branch, not something `init` does.

**What `sq init --dir X` really does, driven.** `init` never reads `--dir`: it initialises the current directory (`Path.cwd()` in `_cli/_main.py` and `_services/_service.py`). Run from a scratch directory with `--dir` at a folder inside another squad, it printed "squads initialized" and wrote `.squads.toml`, `CLAUDE.md`, `.claude/` and `squads/` into the working directory. The squad named by `--dir` was untouched. That predates this change and has nothing to do with the gate, but an operator who passes `--dir` gets a squad where they did not ask for one. It is better raised as a bug of its own than fixed here.

**What would fix it.** Drop the parameter, or make `init` use it. Correct the docstring. Leave `init`'s handling of `--dir` to a separate bug.
<!-- sq:finding:F27:body:end -->

#### Discussion

<!-- sq:finding:F27:discussion -->
- [2026-10-15T19:14:51Z] Paul Reviewer:
  - Verified: require_init is gone from src, tests and the VS Code client (grep clean), the dead default-config branch is removed and the docstring describes what --dir and the walk-up do. Driven: sq init in a fresh directory succeeds and the squad lists; outside a squad, migrate help exits 0, list gives the run-sq-init error, and --version works. sq init ignoring --dir is tracked by BUG-1008.
<!-- sq:finding:F27:discussion:end -->
<!-- sq:finding:F27:end -->

<!-- sq:finding:F28 -->
### F28 — The squad-data check misses deep or slugless item files

<!-- sq:finding:F28:body -->
**What.** `_holds_squad_data` (`src/squads/_paths.py`) decides that a folder with no `.squads.toml` above it is a squad's own when it has a `.squads.json`, or a file matching `*/[A-Za-z]*-[0-9]*-*.md` one folder down. A squad folder outside its project tree, with no index, whose item files all sit deeper than one folder, have no slug, or have a prefix that does not start with a letter, does not match. `--dir` there still gets a made-up current config and passes the gate.

**Evidence, driven** (a `proj/.squads.toml` stamped 0.14 with `squad_dir = "../shared"`, no `shared/.squads.json`):

- An override type `incident` with `folder = "work/incidents"` and one item there: `sq --dir shared repair` exits 0 and writes `.squads.json` (stamped 0.15) and `.reflog.jsonl`, running the current repair over a corpus stamped 0.14. A later `sq migrate up` from `proj` still completes, with INC-1 indexed. No item file was rewritten in this corpus, but this is the route by which pass 6 saw four files rewritten.
- One slugless item, `tasks/TASK-000001.md`: the same, `repair` writes the index.
- Matched as intended: a squad folder with its index, the same folder with the index removed, and a custom type folder one level down are all refused with nothing written. An empty folder and a folder holding only `.reflog.jsonl` get the default config, and `list` exits 1 with nothing written.
- False positive: an unrelated folder with `docs/ABC-1-x.md` is refused as "holds squad data". This only changes which error is printed, since such a folder had no index to list anyway.

**Why it is not blocking.** It needs three conditions together: a `squad_dir` outside the project tree, no index on disk (the index is committed by default), and no item file one folder down that matches the pattern. `--dir` is being replaced by `-C` under an ADR in drafting, so this check only has to hold for one release.

**What would fix it, if it stays.** Match the item-file shape the reconcile already uses (any depth, slug optional, the wider prefix), or treat any `*.md` with an `id:` frontmatter key under the folder as squad data.
<!-- sq:finding:F28:body:end -->

#### Discussion

<!-- sq:finding:F28:discussion -->
- [2026-10-15T19:15:41Z] Catherine Manager:
  - WontFix: temporary heuristic, needs three rare conditions at once; --dir is being replaced by a git-style -C (operator ruling of 2026-10-15 on MILE-934), whose ADR removes this code path.
- [2026-10-15T19:17:11Z] Catherine Manager:
  - WontFix for this release (decision relayed by the manager): --dir is being replaced by a git-style -C, and the ADR in drafting for it is the home for this gap.
- [2026-10-15T19:17:22Z] Paul Reviewer:
  - Note: the previous comment was posted by the reviewer under the manager slug to record the manager WontFix decision as relayed in the pass-9 brief; I set the status.
<!-- sq:finding:F28:discussion:end -->
<!-- sq:finding:F28:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-11T20:56:45Z] Paul Reviewer:
  - @manager first pass done, ST6 only. Verdict: ChangesRequested on one test gap; no defect found in the source change.
    
    - **The source change holds.** Old code against new over 334 rows of squad source by override shape: 254 complete on both with no byte, output or exit-code difference; 16 refused before now complete with the item kept; none goes the other way. The digests reproduce on the unchanged code at 1a96e516. The claim that no byte changes for a squad that migrates today is sound, including for squads with overrides, which the digest test does not represent.
    - **F1 (medium) should land before the up-front vocabulary subtask.** Handing every runner the bundled playbook leaves the whole suite green while changing CLAUDE.md for a squad with a playbook override, and the once-test's identity assertions cannot fail. That subtask rebuilds the service for this caller, through an accessor that passes no playbook today. @python-dev
    - **F2, F3, F4 (low)** can ride with the task: the static guard's blind spots and wide exemption, the hash-only golden, two stale statements of the runner contract.
    - **F5 (medium) is not this subtask's.** It predates the change and is closed by the reconcile and the relocated vocabulary check; it needs a row in the end-to-end table. @tech-lead
    - The changed helper in the milestone roll-up test is faithful: it builds the service as the CLI does. A service built without the squad's vocabulary now migrates under the bundled one where the two newest runners used to re-read the override; no CLI path builds one for migrate up today, and the up-front vocabulary subtask has to keep it that way.
    - Not filed, small: tests/_helpers.py gains the module's first top-level squads imports where every other helper imports locally. No changelog entry for the adopter-visible fix yet.
    - Not covered: the agents_md backend, role and template overrides, squads with operators or custom skills. The whole suite, pyright and ruff were not re-run here.
- [2026-10-11T21:12:39Z] Paul Reviewer:
  - @manager F1 to F4 verified against the working tree; the first subtask is clear to commit and build on.
    
    - **F1** Verified: the bundled-playbook swap now turns 7 tests red, each on the intended assertion.
    - **F2** Verified: every earlier evasion is flagged; what a static scan cannot see is declared.
    - **F3** Verified: text goldens, regenerable and reviewable, and they match the unchanged code at 1a96e516.
    - **F4** Verified by reading.
    - **F6** (low, new, not blocking): 260 of the 319 golden files are byte-identical copies of one rendered surface. About 60 files would give the same coverage. @python-dev, with the rest of the task.
    - **F5** stays Open for the later subtasks.
    - Source is unchanged since the first pass apart from one docstring, so the old-against-new comparison there still stands.
    - Status left at ChangesRequested: F5 and F6 are open and the task is unfinished, and the lifecycle has no state for a pass that is clear with more to come.
- [2026-10-11T22:02:39Z] Paul Reviewer:
  - @manager second pass done: the goldens fix is verified, the index reconcile is not clear to commit or to build on. ChangesRequested.
    
    - **F6** Verified.
    - **F7 (high)** an item-shaped file outside the type folders (an archived item, a lone fixture) is indexed, the runners write to it, then the trailing repair refuses the run with a cause that blames an override the squad does not have. Never stamped, every re-run the same. Old code migrated these squads.
    - **F8 (high)** a refused run leaves the counter and padding raised for good by a file that was never an item: counter 20240115, padding 8, next task TASK-20240116, after the remedy was followed. No test pins the rule that causes it.
    - **F9 (medium)** an ordinary document whose name merely has the shape stops the run when it is not UTF-8 or opens with a block that is not YAML. The decision says a file that is not an item is never reported.
    - **F10 (medium)** a dropped or newly indexed entry is recorded in the reflog only if the same run completes; a refused run then a fixed one leaves no trace. Old code recorded the drop.
    - **F11 (medium)** on a pre-0.7 index the dropped entry is named UNRESOLVED-3, on screen and in the reflog.
    - **F12 (medium)** a task and a bug sharing a number are refused (right: old code silently lost one from the index) but each is called a duplicate of the other's id, and the commands that renumber are behind the gate. A hand renumber gets through.
    - **F13 (low)** docs and one rewritten test still describe skip-and-carry-on. @tech-writer for the docs lines listed there.
    - **F5** stays Open and now has a second route, noted on it.
    
    Who decides what: F8, F10 and F11 are code fixes for @python-dev. F7, F9 and F12 need a ruling first, since each is the decision's recognition rule meeting something it did not consider (@architect, @tech-lead): where a stray item file is refused and with what remedy, whether an unreadable bystander is reported, and whether a renumber is reachable behind the gate. F7 also changes what the up-front vocabulary check has to say, so it should be settled before that subtask is built.
    
    What held is in the review body: carry-forward under 29 hostile shapes, when it runs, content-neutrality, convergence over the eleven corpora, this repository's own squad (964 candidates, nothing reported).
- [2026-10-11T22:12:22Z] Catherine Manager:
  - The four status changes and comments above dated 2026-10-12 were entered by the manager from the developer's hand-back: the board index was missing when he tried to record them (a probe script had deleted it; restored and rebuilt since).
- [2026-10-12T06:02:57Z] Paul Reviewer:
  - @manager third pass done. The design as ruled holds when driven; four defects in the check before the runners and its messages keep this pass from being clear to commit. ChangesRequested.
    
    - **Verified:** F7, F8, F9, F10, F11, F12, each re-driven against the outcome the amendments give. **F5** stays Open for the end-to-end row; both routes are gone. **F13** back to Open for its documentation half only (@tech-writer; the list has grown with A11).
    - **F14 (medium)** the release the refusals name is the one that last synced the squad. On the 0.8 to 0.14 fixtures that is 0.7.0, which refuses those squads as newer than itself. The right release works: driven for every schema from 0.3 to 0.14.
    - **F15 (medium)** an override folder written with a trailing slash or a leading ./ loads and works every day, and the check refuses every item of that type. Old code migrates it.
    - **F16 (medium)** on a squad with no override the check runs the override's alignment test and refuses a hand-edited type as a spec change, naming an override that does not exist. Old code migrates it and sq check reports it.
    - **F17 (medium)** a type whose prefix has an underscore or starts with a digit is seen by neither the reconcile nor the check's second question; with no index its item is indexed only by the trailing repair, after the runners.
    - **F18 (low)** the misplaced-file remedy always sends the operator to another release, though moving the file is enough when the folder already holds an indexed item; and the check's refusals do not say what the rebuild dropped.
    
    F14, F15, F16 and F18 are small code fixes for @python-dev. F17 has a small fix (the second question lists files by the declared prefix) and a question behind it for @architect: widen the pattern, or refuse such a prefix at load.
    
    **The invariant** held in every shape driven: no run the steps before the first runner let through was refused by the trailing repair for where a file sits. The bound the other way does not hold yet (F15, F16: the check refuses what the completed run accepts).
    
    **The design's cost**, for op-pierre, is in the review body as a table. In short: every refusal it introduces has a way out that works when driven, for squads stamped 0.3 to 0.14; restoring the index from version control is the easy one; the release route works but the message names the wrong release when sync lagged, cannot name the command, and that command runs the old release's own content sweep. A squad created by 0.1.x or 0.2.0 is refused by the current package on its integer schema stamp before any of this, at HEAD too, so the oldest squad this path serves is stamped 0.3.
    
    The developer's second report is right and narrower than stated: after a with-index refusal, moving the file back is enough unless it was the only indexed item of its type. Nothing is lost and the drop is in the reflog; the screen does not show it (F18).
- [2026-10-12T06:45:42Z] Paul Reviewer:
  - @manager fourth pass done: F14 to F18 verified, nothing new filed. The reconcile and the check before the runners are clear to commit, and clear to build the remaining three subtasks on.
    
    - **F14** the release named now opens the squad: driven with the real releases for every schema a release stamps, 0.3 to 0.14, for both refusals that name one.
    - **F15** both folder spellings complete, with an index and with none.
    - **F16** a hand-edited type migrates when there is no override, and is refused naming the override when there is one, which is what the load boundary does at the current schema. The loader's other caller is unchanged.
    - **F17** underscore and leading-digit prefixes are indexed before the runners in both states; a dotted prefix with no index is refused with no index left.
    - **F18** the remedy and the rebuilt-first note read as they should.
    - **The empty index:** the added sentence is enough. Removing the index file then lets the run complete, driven. It does not name the file, and a squad with strays will then meet the no-index refusal, which explains itself.
    
    Two things for op-pierre from the ruling on the name pattern, neither a defect. In the no-index state the tree walk now opens names whose prefix has an underscore or starts with a digit, and an id is whatever the model's parser reads, so a document carrying an id such as CVE-2024-1234 with no type now stops the run where it used to be passed over. Both leave the squad untouched and have the same ways out; the list is in the review body.
    
    Still open: **F5** until the end-to-end table has its row, **F13** for its documentation half (@tech-writer). The review stays at ChangesRequested for those.
- [2026-10-15T18:34:58Z] Paul Reviewer:
  - @manager Pass 5 (ST1, ST3, F5) is recorded in the body. The review stays ChangesRequested.
  - Held: on a nested squad, the 72-row gate matrix (migrate verbs and ordinary commands, behind/ahead/current, run from inside and with --dir) matches A1 exactly, and the grant lookup fails closed. F5 is Verified: driven three ways, including a real stop inside a runner, and each re-run completes with no UNRESOLVED id.
  - New: F23 (high, pre-existing): with --dir, a project-root squad never has its .squads.toml read, so it passes as current. repad and repair then rewrite a behind corpus, and migrate up says nothing to migrate. The gate test sidesteps this by nesting the fixture.
  - F19 (medium): a hand-edited badge code passes the check before the runners and stops inside a runner with a message naming sq repair. The claim that store refusals are unreachable does not hold for this shape.
  - F20 (medium): the version notice names sq sync on every behind migrate run, and the invariant tests only read the output from error: onward. F21 (medium, pre-existing): an argument equal to -h or --help, e.g. comment -m -h, gets any command past the gate. F22 (low): the remedy checks cannot see placeholder commands or indirect raises.
  - F21 and F23 are gate mechanism defects outside ST1/ST3 as briefed. They may want a bug of their own, but the gate guarantee depends on them. F13 stays Open for the docs half.
- [2026-10-15T18:51:19Z] Paul Reviewer:
  - @manager Pass 6 is recorded in the body. The review stays ChangesRequested.
  - Verified: F19 (item, sub-entity and custom badge fields refused before any runner), F20 (no sq sync notice while behind), F21 (every value, repeated and option=value shape gated; only a read-only bundled-flag residual), F22 (guard and matchers; minor residual shapes noted). The CLAUDE.md module lines hold.
  - Reopened F23 (high): the fix matches the literal string ".". With squad_dir "./" or "work/squad", --dir still skips the gate (repair rewrote four item files on a 0.14 squad, and migrate up says nothing to migrate). With --dir at the project root of a nested squad, repair writes a stray index at the project root.
  - New: F24 (low): a list or mapping in a custom badge field crashes migrate up with a traceback; the in-frozenset check is copied three times. F25 (low): the runner docstring still says an unparseable milestone stops the run from inside it, but it is now refused before any runner.
  - F13 stays Fixed pending a read of the docs once the writer is done; the docs also owe the F20 and F23 behaviour changes.
- [2026-10-15T19:03:05Z] Paul Reviewer:
  - @manager Pass 7 is recorded in the body. The review stays ChangesRequested on one new medium.
  - Verified: F23 (all three pass-6 layouts gated; nested-in-another-squad, between-two-configs and missing-folder shapes refused). Faithful reverts: back to the HEAD resolve, 45 red, including every root-layout row, with nested and symlinked rows green; back to the pass-6 "." check, 38 red, with the root rows green. F24 (list, mapping and int custom values refused with the file named, no crash at any schema). F25 (docstring true). F21 residual (-m -m --help is help again).
  - New: F26 (medium): a squad_dir that leaves the project tree ("../shared" or absolute) is never on the walk-up from the --dir folder, so --dir there still synthesises a current config; repair rewrote four item files on a 0.14 squad. The index carries the corpus stamp the gate could read.
  - New: F27 (low): no caller passes require_init=False, so the init fallback the dev left is dead code, not a defect of init --dir. Separately, sq init ignores --dir entirely and initialises the working directory (it wrote a squad into my scratch cwd). That predates this work; better as a bug for QA than a fix here.
- [2026-10-15T19:15:11Z] Paul Reviewer:
  - @manager Pass 8: REV-995 is Approved, at your direction; no high or medium finding is open.
  - Verified: F26 (outside-tree squads refused with --dir, with the index and with it removed, nothing written; disabling the check turns exactly the 24 outside rows red) and F27 (require_init gone from src, tests and the client; init, migrate help, list and --version behave as before).
  - New, F28 (low, Open): the squad-data check misses a squad with no index whose item files are all two folders deep or slugless, so --dir there still runs repair under a made-up current stamp. It needs three rare conditions together, and --dir is being replaced by -C, so it is acceptable for one release. It needs your disposition: WontFix with the -C ADR as its home, or a widened pattern.
  - Still to do: F13 stays Fixed until the docs half is read once the writer is done; it also owes the F20, F23 and F26 behaviour changes.
- [2026-10-15T19:17:23Z] Paul Reviewer:
  - @manager Docs and narration check is done; REV-995 stays Approved. F13 is Verified (docs and CHANGELOG match the built behaviour through F27; two small imprecisions are noted on F13). F28 is WontFix, with the -C ADR as its home.
  - Narration sweep over the added lines of git diff (src, tests, docs, CHANGELOG, CLAUDE.md) and the five untracked test modules: no pass, round or phase language, no reviewer or finding references, and no ticket IDs in code or test names (the only ID-shaped strings are fixture file names). No release versions in comments outside the migration runner; the 0.14 strings in tests are fixture stamps.
  - Three minor hits for routing. src/squads/_cli/_common.py:1482: "No command does today" is a time-bound claim that will go stale. src/squads/_paths.py:134: "(the CLI edge, today; a future server handler)", the same, in pre-existing text rewrapped in this diff. tests/cli/test_the_gate_lets_past_by_command_and_direction.py:5: "--help is never gated" is no longer accurate, since --help only skips the gate as an option of its own.
<!-- sq:discussion:end -->
