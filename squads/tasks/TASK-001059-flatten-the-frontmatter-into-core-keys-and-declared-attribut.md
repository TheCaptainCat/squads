---
id: TASK-1059
sequence_id: 1059
type: task
title: Flatten the frontmatter into core keys and declared attributes
status: InProgress
parent: FEAT-1016
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1007:implements
- BUG-1049:fixes
description: Item.attributes, the attributes grammar, the write invariant, the flattening
  merged with operator-identity in the 0.16 step, and the chosen-name fix
subentities:
- local_id: ST1
  title: 'Model: one attribute mapping, slug as a core key, AttributeKey and the accessor'
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: 'Spec: the attributes grammar, pinned roster attributes and the refused names'
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST3
  title: 'Validation: attribute kinds in sq check, --set and import; opt-in undeclared
    check'
  status: Done
  assignee: python-dev
  story: US3
- local_id: ST4
  title: 'Write invariant: the write-path by key-shape table and its falsification'
  status: Done
  assignee: python-dev
  story: US4
- local_id: ST5
  title: 'One meaning per name: skill description, operator title, tech'
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST6
  title: The flat-frontmatter contribution of the 0.16 step, absorbing operator-identity
  status: Done
  assignee: python-dev
  story: US6
- local_id: ST7
  title: Run the 0.16 step on a scratch copy of this repository's squad
  status: Done
  assignee: python-dev
  story: US6
- local_id: ST8
  title: Flat --json rows, workflow attributes and flat render contexts
  status: Done
  assignee: python-dev
  story: US7
- local_id: ST9
  title: 'VS Code skew canary: flat rows and type attributes'
  status: Todo
  assignee: typescript-dev
  story: US7
- local_id: ST10
  title: Docs and changelog for the flat frontmatter
  status: Todo
  assignee: tech-writer
  story: US8
created_at: '2026-10-16T13:05:35Z'
updated_at: '2026-10-16T14:56:46Z'
---
<!-- sq:body -->
## Scope

Implements ADR-1007 (frontmatter is flat: core keys plus spec-declared attributes) for FEAT-1016.
The decision is the spec and the feature's stories are the acceptance; each subtask cites the
story it maps to and adds what the build must also hold. One developer pass: the model, spec,
validation, writer, migration and render changes share files and cannot be split across devs
without collisions.

## The 0.15 to 0.16 step

The flattening is a contribution of the existing 0.15 to 0.16 step in
`src/squads/_migrations/_v0_15_to_v0_16.py`, not a new step and not a schema bump. It plugs into
`CONTRIBUTIONS` like `comment-headers`, so the step still plans every contribution first, refuses
with one combined list when any contribution fails, and writes nothing on a refusal.

**`operator-identity` is merged into it.** That contribution fills `extra.slug` and
`extra.full_name` on an operator the older importer wrote without them. In the flat shape both
targets disappear: `slug` is a core key written on every roster item, and `full_name` is folded
into `title`. So the flattening contribution owns operators end to end, and `operator-identity`
is removed from `CONTRIBUTIONS`, its `MANUAL` section and its `POSTCONDITIONS` row. For a 0.15
operator, one run gives:

| 0.15 operator file | after one run |
|---|---|
| `extra.slug` and `extra.full_name` equal to `title` | top-level `slug`, same `title`, no `extra` |
| `extra.full_name` differs from `title` | `title` takes the `full_name` value, the file is reported |
| importer shape: no `extra.slug`, no `extra.full_name` | top-level `slug` from the file name, `title` unchanged |

**Order.** Every planner reads the files as they are before any write, so the order of the
writers does not change how a header resolves: the header planner keeps keying an operator by its
`extra.full_name`, or by its slug when it has none (ADR-979 A6 as built). The writers run
`comment-headers` (discussion lines only) then `flat-frontmatter` (the frontmatter block only).
Each writer re-reads its file at write time, so the two compose on one file. After the run an
operator's `title` holds the name its `extra.full_name` held, which keeps the dated ADR-979 note
true.

**Later contributors.** The contributions that follow (the `is_dev` removal, `origin`,
`pronouns`, `operator_invocable`) plan on flat keys. The flattening exposes its per-file
transform as a pure function over a frontmatter mapping, and a later planner reads each file
through it, so it plans against the shape its writer will find.

## A role's name: chosen or not (BUG-1049)

This task fixes BUG-1049. A role name chosen explicitly (`--name` at activation) stays. A name
never chosen follows the configuration layers: the bundled catalog, then `.overrides/roles.toml`,
then the per-slug `.overrides/roles/<slug>.toml`. Whether the name was chosen is the declared
role attribute `name_chosen` (`bool`, not settable through `--set`).

- ST2 declares `name_chosen` on `role` and pins it with the roster attributes.
- ST5 changes the resolution in `role_base_from_item` (ST1 only re-points its reads to flat keys)
  and sets `name_chosen` at every write seam.
- ST6 sets `name_chosen` on existing roles in the 0.16 step.
- ST10 updates the docs that state which name wins.

Acceptance:

- A role whose `name_chosen` is false takes its name from the configuration layers on every
  `sq sync`, `sq role <slug> show` and `sq check`: the most specific layer that sets `full_name`
  wins. The role's `title`, `sq list`, its `.claude/` pointer and the `CLAUDE.md`/`AGENTS.md`
  rosters follow, and the rename moves `updated_at` and is recorded in the reflog.
- A role whose `name_chosen` is true keeps its stored name under every layer, the per-slug file
  included.
- `sq role activate --name`, `sq init --name <slug>=<name>`, `[init.names]`, a name typed at the
  `sq init` prompt and `sq dev add --name` store `name_chosen = true`. Activation without a name,
  `--default-names`, an accepted prompt default and a pool-named developer store `false`.
- A developer role with `name_chosen` false takes a per-slug `full_name` when one is set, and
  keeps its stored pool name otherwise: the pool draw is never re-rolled.
- The BUG-1049 repro, run on a squad built by this release, shows `Rita Catalog` as the active
  architect's name after `sq sync`, and `sq check` stays clean.

## Order of work

ST1 and ST2 together (the model and the grammar depend on each other, `name_chosen` included), then ST3, ST5, ST8, ST6,
ST4 (its table has a row for the step), ST7, ST9, and ST10 for the tech writer last.

## Rules for every subtask

- Tests: one table per behaviour, covering every layer it crosses, not one table per layer.
- Comments, docstrings and docs state present truth: no history, no ticket IDs, no versions. The
  migration runner and its `MANUAL` may name the versions they migrate between.
- Never run bare `ls`.
- Board operations go through `~/.local/bin/sq`; the dev tree runs only against scratch squads
  under the session scratchpad.
- Gate before handoff: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`, the tests the diff selects, and a clean
  `~/.local/bin/sq check`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1059 add-subtask "<title>"`; track with `sq task 1059 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Model: one attribute mapping, slug as a core key, AttributeKey and the accessor

<!-- sq:subtask:ST1:body -->
ADR-1007 decisions 1, 2, 3 (accessors) and 6; acceptance is US1.

- `Item.extra` is replaced by `Item.attributes: dict[str, Any]`, holding every non-core key,
  declared or not. `slug` is a core key: written for every roster-category item and for any other
  item whose file carried it; read from frontmatter when present, from the file name otherwise.
- `ExtraKey` becomes `AttributeKey` in `_models/_attributes.py`, read through one item accessor
  (`item.attribute(AttributeKey.MODEL)`); typed roster accessors wrap it and read a value of the
  wrong kind as unset. Every `item.extra` reader moves to `item.slug`, the accessor or a typed
  accessor; `stored_slug` collapses into `item.slug`.
- The model reads no `extra`: `_read_extra`, `_extra_mapping` and the `ref_kinds`/`severity`
  folds move under `_migrations/` as a compat reader, used only by the runners that need it. A
  hand-pasted `extra:` in a current file is an unknown attribute named `extra`, kept.
- The index carries the whole attribute mapping; `sq repair` rebuilds it from the files.
- A guard test in `tests/meta` fails when any reader indexes the attribute mapping by a string
  literal; falsify it by adding one such read.
- `role_base_from_item` and `dev_base_from_item` read the flat keys. The name precedence change
  is ST5's.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions; never run bare `ls`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-16T14:56:18Z] Elias Python:
  - Falsification: one literal-keyed attribute read planted in src turned the tree scan red (1 of 11 tests); restored, green.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Spec: the attributes grammar, pinned roster attributes and the refused names

<!-- sq:subtask:ST2:body -->
ADR-1007 decisions 3 and 4; acceptance is US2.

- `[items.<type>.attributes]` declares `kind` (`str`, `list`, `bool`, `date`), `required`
  (default false) and `settable` (default true). The bundled `workflow.toml` declares attributes
  on guide, milestone, review, role and skill; `_models/_metadata.py`'s per-type tables and the
  closed `_GENERIC_FIELDS` catalog are gone, and no Python table lists a type's keys.
- `sq update --set` writes any settable declared attribute with kind validation, on any type an
  adopter declares one for. Custom badge fields are stored top-level under their code.
- The bundled `role` type declares `name_chosen` (`bool`, not required, `settable = false`):
  whether the role's name was chosen explicitly. It is one of the pinned roster attributes below.
- The loader pins the roster attributes the engine materialises (one table beside the other
  roster minimum semantics): a resolved spec whose role or skill type lacks one, or declares it
  with another kind, is refused naming the key and the remedy. An override may add attributes to
  a roster type.
- The loader refuses an attribute or badge code that is a core key, a duplicate on the type, a
  `--json`-added name (`badges`, `body`, `discussion`, `matched_subentities`), `path`, `prefix`
  or `extra`, naming the key.
- `extra_fields` in any override is refused at load, naming `attributes` and the equivalent
  table. There is no alias and the old key is never read.
- One table for the refusals: rows are the refused shapes above, each asserting exit 1, the named
  key, and that nothing was written.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions; never run bare `ls`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-16T14:56:19Z] Elias Python:
  - Falsification: with the attribute-name/pinned checks and the extra_fields refusal disabled, 24 of 28 refusal rows went red; restored, 28 green.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Validation: attribute kinds in sq check, --set and import; opt-in undeclared check

<!-- sq:subtask:ST3:body -->
ADR-1007 decisions 5 and 11; acceptance is US3.

- Load refuses only a core key of the wrong type, naming the file. A declared attribute of the
  wrong kind never makes an item unreadable.
- `sq check` reports at error an attribute whose stored value fails its declared kind and a
  missing required attribute; the value stays as written and the typed accessor reads it as
  unset.
- `sq update --set` and `sq import` refuse an invalid value before writing; nothing is written.
- `frontmatter_key_undeclared` is a catalog-only validator at warn: off by default, silent unless
  a project selects it, never rewrites. With it selected, an attribute no declaration on the
  item's type names is reported. Unknown keys are kept silently when it is not selected.
- One table: rows are value shapes (wrong kind per kind, missing required, undeclared typo), with
  columns for load, `sq check` with and without the opt-in, `--set` and import, each asserting
  the report or refusal and that the file is byte-identical afterwards.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions; never run bare `ls`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-16T14:56:20Z] Elias Python:
  - Falsification: attribute_valid returning nothing, the undeclared check returning nothing, and bool coercion accepting anything turned 7 of 18 rows red (5+1+1); restored, 18 green.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Write invariant: the write-path by key-shape table and its falsification

<!-- sq:subtask:ST4:body -->
ADR-1007 decision 7; acceptance is US4, whose table is the test.

- The writer serialises the core keys plus the whole attribute mapping and never consults the
  spec. The `sq sync` sweep removes only the closed named set of retired role keys, re-pointed at
  top-level names. `ensure_no_skew` compares round-tripped frontmatter with unknown keys on both
  sides, its retired-key exemptions re-pointed at top-level names.
- One table-driven test: rows are the write paths US4 lists, the 0.15 to 0.16 step included;
  columns are the eight key shapes it lists. Each cell asserts the key is in the file with an
  equal value, in `--json` (a `--json`-only name stays in the file and out of the row) and in the
  rebuilt index.
- One control per row targets the key (`--set`, and an import unset) and shows the write changes
  it, so no row passes on a path that never runs.
- Falsify: make the writer drop undeclared keys, show the undeclared and removed-from-override
  columns go red, restore, show green. Report both runs.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions; never run bare `ls`.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-16T14:56:21Z] Elias Python:
  - Falsification: a writer that drops undeclared keys turned 60 of 122 cells red (never-declared, nested, list, null, json-only x 12 paths); also dropping the override-removed key turned 72 red incl. the removed-from-override column 12/15; restored, 122 green. Paths that do not use the writer (renumber, runner) stay green by design.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — One meaning per name: skill description, operator title, tech

<!-- sq:subtask:ST5:body -->
ADR-1007 decision 8; acceptance is US5.

- A skill's `description` is its summary. `sq skill add` no longer writes a second copy, and the
  Claude Code backend reads `description` then `title`. A test edits a skill's description and
  shows the pointer carries the new text.
- No item stores `full_name`. `sq operator add` writes the name to `title` only, and every
  operator surface (CLI, `operator.md.j2`, card) reads `title`. The roster card payloads keep
  their `full_name` key, valued from `title`, so the cards are unchanged.
- `tech` has a separate declaration on `guide` and on `role`, same kind.
- The role catalog's job-title key in `roles.toml` is untouched.
- Role name resolution (BUG-1049), with the acceptance in the task body: `role_base_from_item`
  carries the stored name into the merge base only when `name_chosen` is true, and then a
  layer's `full_name` never replaces it. When false, the base takes the catalog's name, so
  `roles.toml` and then the per-slug file apply over it. `dev_base_from_item` keeps the stored
  name as the base either way; with `name_chosen` false a per-slug `full_name` applies over it.
  A role item with no `name_chosen` reads as false.
- Every write seam sets `name_chosen` as the task body lists. The roles.toml scaffold comment and
  the docstrings in `_roles/_resolver.py` state the rule.
- One table: rows are `name_chosen` true and false, crossed with the layer that sets
  `full_name` (the bundled catalog only, `roles.toml`, the per-slug file, both override files),
  for a bundled role and for a developer role. Columns are `sq role <slug> show`, the role's
  `title` in its file, its `.claude/` pointer, the `CLAUDE.md` roster and `sq list --json`, each
  after one `sq sync` and again after a second sync, which writes nothing. Expected: false takes
  the most specific layer's name (a developer with no per-slug name keeps its pool name), true
  keeps the stored name in every cell, and `sq check` is clean in every row.
- The BUG-1049 repro, driven on a scratch squad built by the dev tree, shows `Rita Catalog`.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions; never run bare `ls`.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-16T14:56:22Z] Elias Python:
  - Falsification: removing the name pin turned 5 rows red (chosen x layers); freezing the stored name as the bundled base turned 2 red; pointer reading title instead of description turned 1 red. Restored, green. Precedence follows the operator's corrected comment (bundled, roles.toml, per-slug, chosen name last), which is also ST5's body.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — The flat-frontmatter contribution of the 0.16 step, absorbing operator-identity

<!-- sq:subtask:ST6:body -->
ADR-1007 decision 9; acceptance is US6. The design is in the task body under "The 0.15 to 0.16
step".

- A `flat-frontmatter` contribution is added to `CONTRIBUTIONS` after `comment-headers`, with its
  `MANUAL` section, its summary clause and a `POSTCONDITIONS` row in
  `tests/cli/test_migrate_up_rewrites_comment_headers_cli.py`: no item file carries `extra`,
  every roster file carries a top-level `slug`, no operator file carries `full_name`.
- `operator-identity` is removed: its contribution, `MANUAL` section, `POSTCONDITIONS` row and
  tests. The three operator rows of the task body's table are one table-driven test of the step.
- The per-file transform lifts each `extra` key with its value unchanged, with the exceptions
  ADR-1007 decision 9 lists, removes the stray top-level `path:` on system skills, and removes
  `extra`. It is a pure function over a frontmatter mapping, so a later contribution plans
  through it.
- Planning reads only pre-write files, and the pre-flight failures (`extra` not a mapping, a
  lifted key colliding with a different top-level value, a roster `extra.slug` differing from its
  file name) join the header failures in one refusal that writes nothing.
- The writer re-reads each file and replaces only its frontmatter, emitting keys in the model
  writer's order, so a load then write of a migrated file gives the same bytes. A file with no
  `extra` and nothing to remove is byte-identical after the run.
- Every role file gets `name_chosen`, decided from the files as they are before the run: a bundled
  role whose stored name equals the bundled catalog's `full_name` for its slug at migration time
  is unchosen (`false`), and any other name is chosen (`true`). A developer role whose name is a
  first name from the resolved dev pool followed by its tech surname is unchosen, any other is
  chosen. A project-defined role, which has no catalog name, is `false`: its per-slug file is its
  only name source. A role file that already carries `name_chosen` keeps it. The
  `POSTCONDITIONS` row also asserts every role file carries `name_chosen`, and one table-driven
  test covers these rows.
- The `MANUAL` states the rule, says that an unchosen role now follows `roles.toml` and its
  per-slug file on the next `sq sync`, and gives the remedy for keeping a name: set it as
  `full_name` in `.overrides/roles/<slug>.toml`.
- The report gives files flattened, keys lifted per key, skill descriptions dropped, `path:` keys
  removed, the files whose operator `title` changed, and the roles marked chosen and unchosen.
- The `MANUAL` passages that assume the nested shape are rewritten for it: the duplicate-name
  remedy (for an operator the name typed for the run becomes its permanent `title`, so the remedy
  says how to restore it afterwards), the operator matching rule (stated as what the earlier
  release wrote, and that the run makes it the `title`), and any statement that an operator
  without `op-` is only reported. The remedy is driven on a scratch squad end to end.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions (the runner and its `MANUAL` may name the versions they migrate between); never run
bare `ls`.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-10-16T14:56:23Z] Elias Python:
  - Falsification: keeping retired role keys 1 red; name_chosen always false 3 red; operator title not taken 3 red; no writer-order 13 red. Restored, 36 green.
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Run the 0.16 step on a scratch copy of this repository's squad

<!-- sq:subtask:ST7:body -->
Acceptance is US6's run on a copy of this repository's squad.

- Copy `squads/` and `.squads.toml` from the repository into a new project folder under the
  session scratchpad, never inside the repository, `git init` it and commit the copy.
- Before migrating, confirm the copy is the squad that resolves:
  `uv run --project /home/pchat/projects/squads sq -C <copy> check` names the copy. Chain every
  command with `&&`, so a failed `cd` never runs a command against the live squad. The live squad
  is never migrated, repaired or written by this subtask.
- Run `uv run --project /home/pchat/projects/squads sq -C <copy> migrate up` and report its
  counts: headers rewritten, files flattened, keys lifted per key, skill descriptions dropped,
  `path:` keys removed, operators retitled, roles marked chosen and unchosen.
- Show with `git diff` in the copy that every changed line is a comment header line or a
  frontmatter line of the named changes, and that no other frontmatter key moved or changed.
- After the run every item loads, `sq check` is clean, and a census of the copy's frontmatter
  shows no `extra` key left.
- Afterwards, `git status` in the repository shows no change under `squads/`.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions; never run bare `ls`.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-10-16T14:56:25Z] Elias Python:
  - Dry run on a copy under scratchpad t1059 (own git repo, resolve() confirmed the copy): 27 files flattened, 23 keys lifted (allowed_tools 2, is_default 10, is_dev 2, model 2, tags 1, target_date 1, tech 3, when_to_use 2), 2 skill descriptions dropped, 9 path keys removed, 0 operators retitled, 0 roles chosen / 10 never named; 4159 headers in 906 files. 1025 item files, 0 with extra, every roster file has slug; sq sync then sq check clean; second run a no-op; repo git status squads unchanged. Only frontmatter movement beyond the named changes: created_at/updated_at moved after description in the 9 system skill files (writer order).
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Flat --json rows, workflow attributes and flat render contexts

<!-- sq:subtask:ST8:body -->
ADR-1007 decision 10, Python side; acceptance is US7's first three bullets.

- A generic item row (`list`, `show`, `create`, `mine` with `--json`) is the core keys, each
  stored attribute flat at the top level, and the keys the command adds. An unknown key named
  like an added key stays in the file and is left out of the row.
- `sq workflow --json` type entries gain `attributes`: name to `{kind, required, settable}`.
  Roster card payloads are unchanged.
- Render contexts expose the flat item; the `extra` variable is gone. The bundled role, skill,
  operator and review templates read flat keys, and a golden comparison shows they render
  identically for a migrated corpus.
- Regenerate the template manifest and the goldens this changes, and run `tests/meta`,
  `tests/integration` and `tests/cli` in full.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions; never run bare `ls`.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
- [2026-10-16T14:56:26Z] Elias Python:
  - Falsification: rows without attributes 7 red; added-key names unprotected 2 red; no flat render item 3 red. Restored, green. Goldens (list, show, mine, workflow_types, migrated corpora) and the v0_16 fixture regenerated; manifest regenerated.
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — VS Code skew canary: flat rows and type attributes

<!-- sq:subtask:ST9:body -->
ADR-1007 decision 10, client side; acceptance is US7's last bullet.

- `clients/vscode/test/canary/skewCanary.test.ts` drops `extra` from `LIST_ROW_KEYS`, asserts
  the exact core set plus, for every other row key, membership in that type's `attributes` from
  `sq workflow --json`, and adds `attributes` to `TYPE_ENTRY_KEYS`.
- No client source changes: the client reads no `extra` key.
- Falsify: add a stray key to a row the canary reads and show it fails, then restore it.

Rules: one table per behaviour across layers; present-truth comments with no history, ticket IDs
or versions; never run bare `ls`.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Docs and changelog for the flat frontmatter

<!-- sq:subtask:ST10:body -->
ADR-1007 Consequences; acceptance is US8's docs and changelog bullets.

- Refresh `docs/overrides.md` (the `extra` passage, the full-name passage, the `attributes`
  grammar, the `extra_fields` refusal), `docs/roles.md`, `docs/internals.md`,
  `docs/adoption.md`, `docs/faq.md`, and `docs/stability.md` (flat frontmatter and the
  `attributes` grammar named as contract).
- Which name a role takes: the `roles.toml` precedence paragraph and "Which name wins" in
  `docs/overrides.md`, the role-name passage of `docs/stability.md` and `docs/roles.md`, stated as
  the chosen/unchosen rule, with the 0.16 step's marking of existing roles in `docs/migration.md`.
- `docs/migration.md`: a 0.16 upgrade note on the flat frontmatter, the `extra_fields` break, the
  `--json` row change and the `extra.<key>` to `<key>` template change; the schema-change rules
  that still name `extra:`; the sample run output; the operator-identity section replaced by the
  operator rows of the flattening; and the three passages that assume the nested shape (the
  duplicate-name remedy, the operator matching rule, any line saying an operator without `op-` is
  only reported), matched to the step's `MANUAL` as built.
- `CHANGELOG.md`: one entry per adopter-visible break in the unreleased section, one fix entry
  for an unchosen role name following `roles.toml`, and the operator-identity text removed (the
  clause saying an imported operator gets `slug` and `full_name` under `extra:`, and its report
  line), since the flattening's operator rows replace it.
- Read each changed passage against a driven run of the step on a scratch squad, not against the
  code. Docs describe the result: no ticket IDs, no versions beyond the release they document, no
  development-process content.

Rules: present-truth prose with no history; never run bare `ls`.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T13:06:28Z] Olivia Lead:
  - 2026-10-16: authored from FEAT-1016 and ADR-1007. The flattening is a contribution of the existing 0.15 to 0.16 step and absorbs operator-identity; planners read pre-write files, so header resolution (ADR-979 A6 as built) does not depend on writer order.
  - BUG-1049 is not included: its expected behaviour is an open choice assigned to the architect. ST1 and ST5 keep role_base_from_item precedence unchanged so the bug fix lands on flat keys once ruled.
  - Left Draft; promoted at dispatch.
- [2026-10-16T13:08:47Z] Pierre Chat:
  - 2026-10-16: (1) merge the operator-identity contribution into the flat-frontmatter one and drop its MANUAL, CHANGELOG and doc text; (2) ST9 goes to typescript-dev.
- [2026-10-16T13:11:36Z] Olivia Lead:
  - 2026-10-16: amended per op-pierre rulings. BUG-1049 folded in: name_chosen declared in ST2, resolution in ST5 (ST1 re-points reads only), 0.16 marking in ST6 (stored name equal to the bundled catalog name = unchosen, else chosen; pool-shaped dev name = unchosen), docs and CHANGELOG in ST10. Ref added (fixes).
  - Reading of "a chosen name stays": a per-slug full_name no longer renames a chosen role. @op-pierre correct me if the per-slug file should still win.
  - Moved Draft to Ready; dispatch waits on FEAT-1016 Ready.
- [2026-10-16T13:21:23Z] Pierre Chat:
  - 2026-10-16: role name precedence, lowest to highest: bundled catalog, roles.toml, the chosen name (--name at activation, name_chosen), the per-slug override file. A per-slug full_name still renames a chosen role; the chosen name only protects against catalog and roles.toml changes. This supersedes the ST5 reading that a chosen name ignores the per-slug file.
- [2026-10-16T13:22:49Z] Pierre Chat:
  - 2026-10-16: correction to the earlier precedence comment. Role name precedence, lowest to highest: bundled catalog, roles.toml, the per-slug override file, the chosen name. A chosen name (set by activate --name, or by sq role <slug> update once FEAT-977 lands; stored with name_chosen) is never changed by configuration; it is renamed only through update. Configuration supplies the default name of a role never named. This is the reading ST5 already carries.
- [2026-10-16T14:56:45Z] Elias Python:
  - @tech-writer material for ST10, exact user-visible text as built (driven on scratch squads; the step's MANUAL is `sq migrate chlog v0.15.0..v0.16.0`, section "The frontmatter is flat").
    
    Report lines of `sq migrate up` (after the comment-header line):
    - `N file(s) flattened; K key(s) lifted (key n, key n, ...); D skill description(s) dropped; P `path:` key(s) removed`
    - `N operator title(s) set from the stored full name` followed by one `  operators/OP-...md` line per operator
    - `N role(s) marked as named explicitly, M as never named`
    - step summary: "Item frontmatter is flat: the extra block is lifted to top-level keys, and every role records whether its name was chosen."
    
    Refusals (exit 1, nothing written, joined with header problems under one "N problem(s) found."):
    - `<file>: extra is not a mapping`
    - `<file>: extra.<key> and the top-level <key> hold different values`
    - `<file>: extra.slug 'x' differs from the file name's slug 'y'`
    Remedy note: "Correct each file by hand (a stray `extra:` that is not a mapping, a key that exists both under `extra:` and at the top level with different values, a role or operator whose `extra.slug` differs from its file name), then run `sq migrate up` again".
    
    Duplicate-name remedy as driven end to end: give the other entry a distinct name for the run (`title:` for a role, `full_name:` under `extra:` for an operator); the run keeps a role's title and makes the operator's full_name its `title:`; afterwards edit the `title:` line back and run `sq repair`.
    
    Operator rows: extra.slug + extra.full_name equal to title -> top-level slug, same title, no extra; full_name differs -> title takes it, file listed; importer shape (no extra.slug/full_name) -> slug from the file name, title unchanged.
    
    Role name rule: precedence lowest to highest: bundled catalog, roles.toml, per-slug .overrides/roles/<slug>.toml, then a chosen name (`sq role activate --name`, `sq dev add --name`, `sq init --name`/[init.names]/typed prompt), which no layer changes. A role never named takes the most specific layer's name on every sync; a developer never named keeps its pool name unless the per-slug file sets one. The 0.16 step marks existing roles: bundled role whose name equals the bundled catalog's -> never named, else chosen; developer whose name is a first name of the resolved pool + its tech -> never named, else chosen; project-defined role -> never named. Remedy to keep a name for a role marked never named: set it as `full_name` in `.overrides/roles/<slug>.toml`. roles.toml scaffold comment states the rule.
    
    Other user-visible changes: `extra_fields` in an override is refused at load ("'extra_fields' is not a declared key ... replace it with `[items.<type>.attributes]` and one `<name> = { kind = "str" }` line per key (kind is str, list, bool or date)"); attributes grammar kind/required/settable; roster attributes pinned (role: is_default, is_dev, model, name_chosen, tech; skill: allowed_tools, model, when_to_use), refusal text "roster type 'role' must declare attribute 'x' with kind 'k' — add `x = { kind = "k" }` under [items.role.attributes]"; refused attribute names: core keys, badges/body/discussion/matched_subentities, path, prefix, extra, a badge code on the same type. `sq check` error `attribute 'x': expected a list of strings, got ...` / `missing required attribute 'x'`; opt-in validator `frontmatter_key_undeclared` (warn) `frontmatter key 'x' is not declared on <type>`; `--set` refuses a bad value ("'weight' expects true or false; got 'heavy'", "'d' expects an ISO date (YYYY-MM-DD); got ..."), bool coercion is now strict. `--json` item rows (list, show, create, mine): attributes flat at top level, no `extra`; a name equal to a row field or an added key (badges, body, discussion, matched_subentities) stays in the file, out of the row. `sq workflow types --json` entries gain `attributes` ({name: {kind, required, settable}}). Templates: `item.<key>` replaces `extra.<key>`; `extra` variable gone. Operators: name is `title` only (no full_name); a skill's description is its only summary. Unknown frontmatter keys are kept on every write (hand-added keys, keys of a removed declaration, stray fixture keys such as schema_version/id_padding on old skills).
- [2026-10-16T14:56:46Z] Elias Python:
  - ST1-ST8 built in the main tree (uncommitted). Gates green: pyright 0, ruff check/format clean, sq check clean; meta+integration+cli in full plus every test the diff selects: 10408 passed. I did not run the whole suite. Notes for review: (1) ST5 follows the operator's corrected comment (config layers bundled, roles.toml, per-slug; a chosen name is last and no layer changes it). (2) The 0.16 step writes keys in the model writer's order, so 9 system-skill files in this squad also move created_at/updated_at after description, the only frontmatter movement beyond the named changes. (3) is_dev is pinned and declared on role until its removal lands. (4) Because TASK-1001 also edits VALIDATOR_NAMES/DEFAULT_VALIDATOR_LEVEL/UNGUARDED_VALIDATOR_NAMES and the effective-set tests, expect a merge there (mine add attribute_valid to COMMON_CORE and frontmatter_key_undeclared as catalog-only). @manager
<!-- sq:discussion:end -->
