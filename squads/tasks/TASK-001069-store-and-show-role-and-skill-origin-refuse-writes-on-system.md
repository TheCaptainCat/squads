---
id: TASK-1069
sequence_id: 1069
type: task
title: Store and show role and skill origin, refuse writes on system ones
status: Done
parent: FEAT-976
author: tech-lead
priority: high
refs:
- TASK-990:depends-on
description: One origin rule, stored as a pinned attribute, stamped at creation and
  by a 0.16 contribution, shown everywhere; system writes refused via the body classification
subentities:
- local_id: ST1
  title: Define one origin rule for roles and skills
  status: Done
  story: US1
- local_id: ST2
  title: Declare and pin the origin attribute, report bad values in check
  status: Done
  story: US1
- local_id: ST3
  title: Stamp origin on every creation path
  status: Done
  story: US1
- local_id: ST4
  title: Show origin on every role and skill surface
  status: Done
  story: US1
- local_id: ST5
  title: Stamp existing squads through a 0.16 contribution
  status: Done
  story: US2
- local_id: ST6
  title: Refuse content writes on system roles and skills
  status: Done
  story: US3
created_at: '2026-10-16T19:20:35Z'
updated_at: '2026-10-16T22:48:08Z'
---
<!-- sq:body -->
## Scope

Whether a role or skill is `system` (bundled or spec-generated) or `project` (authored by the
project) is answered by one rule and shown under one name, `origin`, on every surface. Today
three rules disagree: `sq skill show` prints `kind:` from the body-refusal classification,
`sq skill show --json` prints `system` from `is_system_skill` (bundled-blind), and
`sq role catalog` prints `bundled`/`project` from slug-in-bundled-set. Every content-changing
write on a system role or skill is refused through the classification the body refusal already
uses.

Covers FEAT-976 stories 1 to 3. Out of scope: verbs new to roster entities (FEAT-977), making
system skills editable, a role's model (BUG-1065), documentation (the tech writer, from this
task's handoff).

## The rule (one function, used by every writer and reader)

- **Role:** `system` when its slug is in the bundled catalog (`roles.toml` as packaged, not the
  squad's resolved catalog) or the item carries the `tech` attribute (a templated developer);
  otherwise `project`. A per-slug override of a bundled role keeps `system`. A declared
  developer (a role file with the `dev` capability, no `tech`) is `project`.
- **Skill:** `system` exactly when `is_system_skill(slug, spec)` holds (bundled skill slugs plus
  the spec's generated `sq-<type>` slugs); otherwise `project`.
- Creation stamps, the migration and the catalog's rows for not-yet-activated roles all call
  this function. No second membership test is written anywhere.

## Stored state, and why

The feature asks for one stored attribute, `origin`, on role and skill items. That is the only
new state: no index field beyond the attribute mapping it already carries, no new collection, no
precedence ladder. Stored and derived agree at creation and after the migration; they can differ
only when a later spec or bundled catalog changes membership, and then the stored value (where it
came from) wins on every surface. Whether the field should be stored at all is raised on FEAT-976
for the manager; ST2, ST3 and ST5 are the subtasks that fall away if it is derived instead.

The refusal never reads the stored origin. It follows the body-refusal classification
(`views.roster_body_view_name`), so a system skill whose view the project dropped from
`[selected]` is writable and still shows `origin: system`. This is the one documented divergence.

## Order and dependency on TASK-990

Starts after TASK-990 is Done (depends-on). TASK-990 is in progress in the same tree and its
ST5 to ST11 edit the same files:

| file | TASK-990 | this task |
|---|---|---|
| `_specs/workflow.toml`, `_workflow/_models.py` (`PINNED_ROSTER_ATTRIBUTES`) | ST8 removes `is_dev` | ST2 adds `origin` |
| `_models/_attributes.py` | ST8 deletes `AttributeKey.IS_DEV` | ST2 adds `AttributeKey.ORIGIN` and its accessor |
| `_roles/_catalog.py`, `_roles/_projection.py` | ST2/ST6/ST8 (`RoleDef`, `RoleView`) | ST1/ST4 (catalog rows, `RoleView.origin`) |
| `_interactions/__init__.py`, `_interactions/_role_guidance.py` | ST5/ST6 | ST1 homes the rule beside `is_system_skill` |
| `_services/_roster.py` | ST8/ST10 (`add_dev`) | ST3 stamps in `activate_role`, `add_dev`, `add_skill` |
| `_services/_maintenance.py` | ST8 (`_retired_role_keys`, `_refresh_catalog_attributes`) | ST3 stamps the skills sync seeds |
| `_services/_validators.py` | ST5 (playbook `*<name>` check) | ST2 adds the closed-vocabulary rule |
| `_migrations/_v0_15_to_v0_16.py` `CONTRIBUTIONS` | ST8 appends after `flat-frontmatter` | ST5 appends after TASK-990's |
| `tests/cli/test_migrate_up_rewrites_comment_headers_cli.py` `POSTCONDITIONS` | ST8 adds its row | ST5 adds its row |
| `tests/fixtures/corpus/v0_15_developers/` | ST8 builds it | ST5 reuses it (rebuilt by its README if a shape is missing) |
| `_cli/_role.py` | ST4 (capabilities, done) | ST4 (origin column) |
| `templates_manifest.json` | regenerated per bundled change | regenerated with ST2 |

Build order: ST1, ST2, ST3, ST4 (commit point, reviewed), ST5, ST6 (commit point, reviewed).
ST6 does not depend on the stored field and may go first if the storage question is still open.

## Files touched

`src/squads/_interactions/__init__.py`, `_specs/workflow.toml`, `_workflow/_models.py`,
`_models/_attributes.py`, `_services/_validators.py`, `_services/_roster.py`,
`_services/_maintenance.py`, `_services/_service.py` (init), `_services/_items.py`
(`_reject_unwritable_body` and the shared gate), `_services/_import.py` (simulated ops),
`_roles/_projection.py`, `_roles/_catalog.py`, `_cli/_role.py`, `_cli/_skill.py`,
`_migrations/_v0_15_to_v0_16.py`, `_rendering/templates_manifest.json` and the content store;
tests under `tests/integration`, `tests/cli`, `tests/meta`; the migrated-corpus goldens and the
`v0_16` fixture, regenerated by their README rules.

## Acceptance (whole task)

- Every acceptance bullet of FEAT-976 US1 to US3 is pinned by a named test; the handoff maps
  bullet to test.
- **Table-driven shape tests**, not one test per branch. Two backbone tables:
  - *Origin by surface.* Rows (shapes): bundled role; bundled role with a per-slug override;
    retired bundled role; templated developer; declared developer; project role; project role
    whose slug ends in `-dev`; bundled skill (`squads`); generated `sq-<type>` skill; generated
    skill of a project-declared type; skill of a type the spec dropped; system skill whose view
    is dropped from `[selected]`; project skill (`sq skill add`). Columns (surfaces): file
    frontmatter; `sq role list` / `sq skill list`; `sq role show` / `sq skill show` text and
    `--json`; `sq list -t role|skill --json`; `sq role catalog` text and `--json`; the index
    after delete-then-`sq repair`. Invariant per row: every surface prints the same value as the
    file.
  - *Refusal by verb* (ST6): rows are the same shapes, columns are the write verbs.
    Invariant per row: refused iff classified, and label equals refusal on every row except the
    dropped-view row.
- **Pipeline invariants:** the rule and the stored value agree on every row of a fresh `sq init`
  plus each creation path; `sq sync` is a fixed point and never rewrites an existing `origin`;
  migrate then sync converges on what a fresh init writes for the same roster; the index is
  rebuildable from the files with identical values.
- **A falsified test per subtask:** break the change on purpose, watch the named test go red,
  restore. The handoff records what was broken and which test went red.
- A service-level test and a CLI smoke test per behaviour change; CLI tests assert the bare exit
  code and the printed text.
- Generated files diffed with the roster held constant (fresh init against migrate then sync):
  byte-identical, and the diff against 0.15 output shows only what a subtask names.

## Gates and working rules

TASK-990's "Gates and working rules" apply unchanged: pyright/ruff with `--all-extras`,
`~/.local/bin/sq check` clean, `tests/meta` on any module constant, bundled-byte, migration or
import-edge change; selection derived from the diff, the manager runs the full suite; one-or-two
sentence comments with no versions or ticket ids; no ticket ids in test file names; no edits to
`CHANGELOG.md`, `docs/` or the hand-written `CLAUDE.md`; probing only in a scratch squad under the
session scratchpad; the dev build never runs at the repository root. This repository's squad is
migrated by the operator at release preparation; the proof is made on a scratch copy.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1069 add-subtask "<title>"`; track with `sq task 1069 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Define one origin rule for roles and skills

<!-- sq:subtask:ST1:body -->
**Goal.** One function answers `system` or `project` for a role or skill item. Nothing calls it
yet except its tests; later subtasks make every writer and reader go through it.

**Approach**

- Home it beside `is_system_skill` in `src/squads/_interactions/__init__.py` (the module already
  imports from `_roles`). If the import-graph guard
  (`tests/meta/test_package_import_edges_match_the_recorded_table.py`) needs a new edge, it is a
  row in its diff; no `TYPE_CHECKING` workaround unless a cycle forces it.
- Role: slug in the bundled catalog's slugs (as packaged, never the squad's resolved catalog)
  or `attrs.tech(item)` is set gives `system`; otherwise `project`.
- Skill: `is_system_skill(slug, spec)` gives `system`; otherwise `project`.
- The vocabulary is two named constants (`system`, `project`), spelled once, in
  `_models/_attributes.py` next to the accessor ST2 adds.
- A second helper answers the same question for a catalog definition with no item (needed by
  `sq role catalog` in ST4): bundled entry or the `[dev]` template gives `system`, a
  project-declared entry `project`. Both helpers share the slug test; neither re-implements it.

**Tests**

- Table: the role and skill shapes of the task body's origin table, by the rule's inputs
  (slug, `tech`, spec). Each cell states the expected origin. Includes a workflow override that
  renames a type (the old `sq-<type>` stays `system`, as `is_system_skill` is bundled-blind) and
  a catalog override that declares a project role.

**Falsify.** Read the squad's resolved catalog instead of the bundled one: the
project-declared-role row goes red. Drop the `tech` branch: the templated-developer row goes red.
Restore each.

**Acceptance**

- `rg -n '_BUNDLED_SLUGS|in bundled_skill_slugs\(' src/squads/_cli` finds nothing new; the rule
  has one definition.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-16T21:29:56Z] Elias Python:
  - Done. origin rule in _interactions (role_origin, skill_origin, item_origin); constants ORIGIN_SYSTEM/PROJECT in _models/_attributes. Falsification, 11 new tests red in total across three breaks: dropping the tech branch 2 red, treating every slug as bundled 6 red, treating every skill as system 3 red (tests/unit/test_origin_rule_by_shape.py, 24 tests).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Declare and pin the origin attribute, report bad values in check

<!-- sq:subtask:ST2:body -->
**Goal.** `origin` is a declared, pinned attribute of the `role` and `skill` types, read through
one typed accessor, and `sq check` reports a missing or out-of-vocabulary value.

**Approach**

- `_specs/workflow.toml`: `origin = { kind = "str", required = true, settable = false }` under
  `[items.role.attributes]` and `[items.skill.attributes]`. `required` gives the missing-value
  report from the existing attribute validator; `settable = false` refuses `sq update --set`.
- `_workflow/_models.py`: `origin` joins `PINNED_ROSTER_ATTRIBUTES` for both types (kind `str`).
- `_models/_attributes.py`: `AttributeKey.ORIGIN` and an `origin(item)` accessor that returns
  the value only when it is one of the two constants, `None` otherwise (ADR-1007 decision 3: a
  wrong value reads as unset).
- `_services/_validators.py`: one rule in the default bundle, at `error`, reporting a stored
  `origin` outside the two values and naming the file. No other new rule.
- Regenerate the template manifest in the same commit (task body of TASK-990, "Bundled files and
  the manifest"), and the content store if a blob is left unreferenced.

**Tests**

- Table: stored value shape by surface. Shapes: `system`; `project`; absent; `System` (case);
  empty string; a list; `null`; an unknown word. Surfaces: `sq check` (exit code and message);
  the accessor; `sq update --set origin=project` (refused, exit 1); delete the index then
  `sq repair` (value round-trips verbatim, including the invalid ones, per ADR-1007 decision 5).
- Spec: a workflow override that drops `origin` from `role` is refused at load naming the key;
  `sq workflow types --json` lists `origin` among role and skill attributes.

**Falsify.** Remove the pin: the override row loads and goes red. Make the accessor return the
raw value: the `System` and unknown-word rows go red. Restore each.

**Acceptance**

- FEAT-976 US1: closed vocabulary of exactly two values; `sq repair` round-trips the field.
- `tests/meta` passes (mutable-state guard, manifest freshness).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-16T21:29:59Z] Elias Python:
  - Done. origin declared required + settable=false on role and skill, pinned, accessor attrs.origin, closed-vocabulary check inside attribute_valid (no new validator name). Falsification: pin removed 2 red, accessor returning the raw value 4 red, vocabulary check disabled 6 red (tests/service/test_a_stored_origin_is_judged_by_check_and_survives_repair.py, 64 tests; pinned rows added to the attribute-declaration CLI table).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Stamp origin on every creation path

<!-- sq:subtask:ST3:body -->
**Goal.** Every path that creates a role or skill item stamps `origin` from the ST1 rule. No
path rewrites an existing value.

**Approach**

- Creation paths: `sq init` (`_services/_service.py`), the skill seeding in `sq sync`
  (`_services/_maintenance.py`, the `create` of `ROSTER_SKILL` items), `activate_role`,
  `add_dev` and `add_skill` (`_services/_roster.py`), and `sq import` when it creates a role or
  skill. Each passes `origin` in the `attributes` it already builds, computed by the ST1 rule;
  none hard-codes `system` or `project`.
- `sq sync` stamps only what it creates. It never changes an existing `origin` and never fills a
  missing one: a missing value is `sq check`'s report (ST2) and the migration's job (ST5).
- The sync retired-key sweep and `_refresh_catalog_attributes` must keep `origin`: it is
  declared on `role`, so `_retired_role_keys` already keeps it. Pin that with a row, add no code.

**Tests**

- Table: creation path by shape. Paths: `sq init --roles all`; `sq sync` after a workflow
  override adds a type (its `sq-<type>` skill); `sq role activate` of a bundled role and of a
  project-declared role; `sq dev add --tech rust`; activating a declared developer;
  `sq skill add`; `sq import` of a role and a skill. Columns: the stored value, the ST1 rule's
  value, `sq check` result. Invariant: stored equals rule on every row.
- Fixed point: run `sq sync` twice after each row; the second run changes no file (hash the
  tree). A hand-edited `origin: project` on a bundled role survives `sq sync` and `sq repair`.

**Falsify.** Stamp a constant `system` in `activate_role`: the project-declared-role row goes
red. Let `sq sync` backfill a missing value: the fixed-point row with a hand-removed value goes
red. Restore each.

**Acceptance**

- FEAT-976 US1, the creation-stamp bullet.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-16T21:30:03Z] Elias Python:
  - Done. One stamp in ServiceCore._create_model (covers init, activate, dev add, skill add, import, role/skill creates) plus the three Item constructions in the skill seeding/restore code in _maintenance. Falsification: constant system stamp 4 red, skill-seed stamp dropped 8 red, sync backfilling origin 5 red (tests/integration/test_every_creation_path_stamps_the_origin_the_rule_gives.py, 20 tests).
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Show origin on every role and skill surface

<!-- sq:subtask:ST4:body -->
**Goal.** Every role and skill surface prints `origin` and nothing else for that question. The
two divergent derivations in the CLI are deleted.

**Approach**

- `_cli/_skill.py`: `show` replaces the `kind:` line with `origin:` read from the stored
  attribute; `show --json` carries `origin` and drops `system`. `sq skill list` gains an Origin
  column. `is_system_skill` stays where it decides seeding and reclaim; the CLI no longer calls
  it for a label.
- `_cli/_role.py`: `role list` and `role show` (text and `--json`) gain `origin`, read from the
  item through `RoleView.origin` (`_roles/_projection.py`, copied from the item's attribute in
  `ServiceCore._role_view`). `role catalog` prints `system` where it printed `bundled`, reads the
  stored value for an activated role and the ST1 catalog helper for a definition with no item,
  and lists developer roles (templated items and declared role files). `_BUNDLED_SLUGS` goes.
  The docstring claim that the column tells apart a project-overridden bundled role is deleted.
- `sq list -t role|skill --json` already carries every stored attribute flat (ADR-1007); pin it,
  add no code.
- A missing or invalid stored value prints as empty text and is omitted from `--json`; `sq
  check` (ST2) is where it is reported. No fallback to the rule on read.

**Tests**

- The task body's origin-by-surface table, every row and column, as one parametrised module.
- An overridden bundled role asserts `system` on every surface.
- `role catalog --json` golden: `bundled` gone, `system` present, developer rows present.

**Falsify.** Make `skill show` read `is_system_skill` again: the dropped-type and project-type
rows disagree with the file and go red. Make the catalog read slug-in-bundled-set: the templated
developer row goes red. Restore each.

**Acceptance**

- FEAT-976 US1, the surface bullets: same value under the name `origin` everywhere; the `kind`
  line and the bundled-blind `system` flag are gone (`rg -n '"system":|kind_label' src/squads/_cli`
  finds nothing, checked against the commit before).
- The handoff lists each changed payload key and column for the tech writer.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-16T21:30:06Z] Elias Python:
  - Done. origin on role list/show (text+json), skill show (text+json), role catalog (system replaces bundled; templated and declared developers listed), the kind line and bundled-blind system flag removed. Falsification: skill show re-derived from the body classification 2 red, skill json back to the bundled-blind rule 2 red, catalog from slug-in-bundle 2 red (tests/cli/test_origin_is_printed_identically_on_every_role_and_skill_surface.py, 6 tests x shapes x surfaces, fresh and after delete+repair).
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Stamp existing squads through a 0.16 contribution

<!-- sq:subtask:ST5:body -->
**Goal.** `sq migrate up` stamps `origin` on every existing role and skill that lacks it, as one
contribution to the release's 0.15 to 0.16 step, with no schema bump of its own.

**Approach**

- One `Contribution` appended to `CONTRIBUTIONS` in `_migrations/_v0_15_to_v0_16.py`, after
  TASK-990's. Nothing else in the step is edited: not `migrate()`, `run_contributions`, the
  registry, `SCHEMA_VERSION`, `flatten_frontmatter` or its frozen key set, `_cli/_migrate.py`.
- *Planning function* (read-only): the role and skill items from the reconciled index; each
  file's frontmatter passed through `flatten_frontmatter` (planning runs before the flattening
  writer), then the ST1 rule applied with the run's `ctx.spec` and the bundled catalog. A file
  that already carries an `origin` key, whatever its value, is skipped (an invalid value is
  `sq check`'s report, ST2). The plan carries no failure. No second file reader, no `extra`
  parsing.
- *Writing function*: sets top-level `origin` on each planned file through the frontmatter
  writer, changing no other key. Runs after the flattening writer, so it writes flat files.
- *Report*: counts of `system` and `project` stamps, per type.
- *MANUAL section and summary clause*: every role and skill now records where it came from;
  bundled and spec-generated ones and templated developers are `system`, the rest `project`; an
  overridden bundled role stays `system`; a value is never changed once set. The tech writer
  tightens the wording through a comment on this task.
- If the runner guard
  (`tests/meta/test_migration_runners_use_the_runs_resolved_vocabulary.py`) refuses the bundled
  catalog read, report it; add no exemption and do not widen `MigrationContext`.
- `POSTCONDITIONS` row in `tests/cli/test_migrate_up_rewrites_comment_headers_cli.py`: every
  role and skill file carries `origin` in `{system, project}`.

**Tests**

- Table: corpus shape by step, on TASK-990's `tests/fixtures/corpus/v0_15_developers/`. Shapes
  needed: a project-authored skill; a bundled role with a per-slug override; a templated
  developer; a declared developer; a retired bundled role; a generated `sq-<type>` skill. If the
  fixture lacks one, rebuild it with the released tool by its README commands with the shape
  added (never hand-edit) and regenerate its goldens. Steps: `sq migrate up`; a second
  `sq migrate up`; delete the index then `sq repair`. Columns: files changed (hashed), `origin`
  per item in file and index, report lines, exit code.
- Invariants: the second run changes no file; no key other than `origin` changes; migrate then
  `sq sync` produces the same frontmatter as a fresh init for the same roster; `sq check` clean.
- `v0_16` fixture and migrated-corpus goldens regenerated by their README rule; the expected
  diff (an `origin` line on each role and skill) is confirmed line by line in the handoff.
- `sq migrate chlog v0.15.0..v0.16.0` prints this section once, after TASK-990's.
- A scratch copy of this repository's squad: `migrate up`, `sync`, `check`; record the counts
  and that `sq check` is clean. Never the live squad.

**Falsify.** Stamp every role `system`: the declared-developer row goes red. Overwrite an
existing value: the second-run invariant goes red. Remove the `POSTCONDITIONS` row: the
contribution test fails naming it. Restore each.

**Acceptance**

- FEAT-976 US2, all bullets; FEAT-986 story 4's every-contribution bullet gains this row.
- The diff under `src/squads/_migrations/` is the appended contribution and nothing else.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Refuse content writes on system roles and skills

<!-- sq:subtask:ST6:body -->
**Goal.** Every content-changing write on a system role or skill is refused with exit 1 and an
error naming the real authoring surface, through the classification the body refusal already
uses. `comment` and `comments` stay allowed.

**Approach**

- Extract the roster-view question in `ItemsMixin._reject_unwritable_body`
  (`_services/_items.py`) into one gate that names the item, the verb and the authoring surface
  (the playbook via `views.skill_authoring_surface` for a skill, the role override for a role).
  Body replace and append keep calling it; every other content-changing service entry point on a
  role or skill calls the same gate: `update` (title, description, `--set`), `view` enable and
  disable on a classified host, `rm`, `status`, and the `sq import` simulation
  (`_services/_import.py`). `--force` does not lift it. FEAT-977's new verbs call it as they land.
- The gate reads `views.roster_body_view_name`, never the stored `origin`, so a skill whose view
  is dropped from `[selected]` leaves the classification and is writable.
- The existing refusal on project-declared roles (definition in the role override file) is
  unchanged.
- `status` and `rm` are listed by FEAT-976 US3; `sq role <slug> status Archived` and
  `sq skill <slug> status Archived` are today the documented way to retire a bundled role or
  skill. The rows for those two verbs follow the ruling recorded on FEAT-976 before dispatch.

**Tests**

- Table: verb by shape. Verbs: `update --title`, `update --desc`, `update --set`, `body`,
  `body --append`, `view enable`, `view disable`, `rm`, `status`, `comment`, `comments`, an
  import body op and an import field op; each with and without `--force` where the flag exists.
  Shapes: the role and skill rows of the task body's origin table. Each cell: exit code, error
  text naming the surface, and the file hash unchanged on refusal.
- Invariant: refused iff `roster_body_view_name` names a view; label (`origin`) equals refusal
  on every row except the dropped-view row, which is writable and shows `system`.
- Meta test: `roster_body_view_name` is called from `_services/` only inside the gate (and from
  `_views.py`); no second membership test.

**Falsify.** Make the gate read the stored `origin`: the dropped-view row goes red. Let
`--force` bypass it on `update`: the force column goes red. Call the classifier directly from
one verb: the meta test goes red. Restore each.

**Acceptance**

- FEAT-976 US3, all bullets.
- The handoff lists every new error message and exit code for the tech writer.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T19:21:18Z] Olivia Lead:
  - Broken down into ST1-ST6. Starts after TASK-990 (shared files listed in the body). Two open questions on FEAT-976 for @manager: stored vs derived origin (ST2/ST3/ST5 drop if derived), and whether status/rm count as content writes (ST6).
- [2026-10-16T19:31:31Z] Catherine Manager:
  - Rulings recorded on FEAT-976: origin stored (ST2/ST3/ST5 stand); status and rm allowed on system entries, ST6 refuses update, body and view edits only. Dispatch after TASK-990 closes.
- [2026-10-16T19:53:50Z] Olivia Lead:
  - ST6: role title (the name) must pass the system-role gate, or the documented bundled-role rename via sq import update breaks. Question and recommendation on FEAT-977 for @manager; TASK-1070 ST4 makes the gate field-level with a declared exemption set.
- [2026-10-16T19:54:19Z] Catherine Manager:
  - @tech-lead ST6: the role name (title) is exempt from the system-role refusal, per the 2026-10-16 stored-name ruling; see FEAT-977.
- [2026-10-16T21:30:34Z] Elias Python:
  - ST1-ST4 done, checkpoint. Adopter-visible changes for the tech writer:
    - Frontmatter of every role and skill carries origin: system or project (required, not settable by update --set; sq check reports a missing value or one outside the two words).
    - sq skill show: the kind line becomes an origin line; show --json carries origin and no longer carries system.
    - sq role list and sq role show (text and --json) gain origin; sq role list gains an Origin column.
    - sq role catalog: the value bundled becomes system; the column is stored origin for activated roles. Activated developers (templated and declared) now get catalog rows even when the catalog document does not declare them.
    - sq list -t role|skill --json already carries the stored origin flat.
    Deviations from the task text, for review:
    - sq skill list does not exist (new roster verbs are FEAT-977), so no Origin column was added there.
    - RoleView.origin was not added: nothing would read it (the CLI reads the item).
    - The closed-vocabulary rule lives inside attribute_valid (error level) rather than as a new validator name, so no new entry in the validator catalogs.
    - Stamping happens once in ServiceCore._create_model plus the three skill Item constructions in _maintenance, not per call site.
    Expected red until ST5: tests that migrate a corpus and then run sq check (migration corpus, resume-after-runner, developer-marker and comment-header CLI tests), because migrated files do not yet carry origin.
- [2026-10-16T21:31:13Z] Elias Python:
  - ST6 ruling from the coordinator (citing the 2026-10-09 op-pierre ruling on FEAT-976: origin is provenance, the refusal follows whether the body is generated): the refusal follows the existing body classification. A role's body is a generated view, so a role is refused whatever its origin. The label-equals-refusal invariant applies to skills only; for roles the invariant is refused iff the body is generated, and the title stays exempt.
- [2026-10-16T21:43:57Z] Elias Python:
  - ST5 done. Contribution "origin" appended last to the 0.15 to 0.16 step (the diff under _migrations is that one contribution, its MANUAL section and its CONTRIBUTIONS entry); POSTCONDITIONS row added.
    Falsification, new or changed tests red when reverted: stamping every role system 4 red; overwriting a stored origin 1 red; removing the POSTCONDITIONS row 1 red (the contribution test names it).
    Tests: tests/cli/test_migrate_up_stamps_the_origin_of_every_role_and_skill_cli.py (developer fixture shapes by migrate / second migrate / delete index + repair; a stripped fresh-init squad migrates to byte-identical files, then sync is a fixed point and check is clean; chlog prints the section once, after the developer section).
    Fixtures: tests/fixtures/corpus/v0_16 regenerated by the real migrate up on a copy of v0_15 (clock pinned); the diff is 5 origin lines plus the matching index attributes. The migrated_corpus goldens were regenerated with UPDATE_GOLDENS=1; the diff is only added origin lines and their JSON commas. Existing partial-chain tests (4.5 and 8.10 runners only) now ignore the missing-origin error since the 0.16 step has not run; the hand-built current-stamp corpus helper stores origin.
    Dry run on a copy of this repository's squad (scratch copy, dev build, -C): migrate up wrote 4363 comment headers in 927 files, flattened 27 files, stamped 10 roles system, 12 skills system, 2 skills project; sync ok; sq check clean; second migrate up changes nothing (hashes stable).
- [2026-10-16T22:19:55Z] Elias Python:
  - ST6 done. One shared gate, ServiceCore._refuse_classified_roster_write (in _base.py), built on views.roster_body_view_name, the classification the body refusal already used; the body refusal now calls it too. It is called from: body replace and append (and the importer's body simulation), the metadata update (_update_model, which the importer's update simulation and apply share), and view disable. --force never reaches it.
    Rules as built: a role is refused whenever its body is generated (every role), title exempt; a skill is refused exactly when classified, so a skill whose view or type the project dropped is writable and still shows origin system. status, rm, comment stay open; status passed through update keeps its own existing refusal message.
    Deviation to review: view add is NOT refused. Every check remedy and the four-step legacy-body remedy ends in view add on a role or generated skill (restoring a missing or absent seeded tag), so refusing it leaves those states unrecoverable; view disable is the edit that hides generated content and is refused. One line to flip (add the gate call to add_view). The check remedy text that names view disable for an absent-region role/skill now points at a refused verb on a classified host.
    Falsification (new table, 86 tests): gate reading the stored origin 21 red; force bypassing the body gate 2 red; view disable using its own classifier call 1 red (no-second-membership-test meta check); update gate removed 12 red.
    Error text: "<ID>'s body renders through its declared sq:view:<name> tag, and its content already has one validated authoring surface: <surface>. <An update|A view edit|A replace|Append> is refused - --force does not lift this. Drop the view from [selected] to author this directly instead." Exit 1.
    Existing tests changed because role updates by description/--set/view disable are now refused: skew guard, drifted-sync, selection-table banner planting (role description set at creation), slug-fixed import tests, view add/disable CLI and service tests, retirement update seam, generic extra field. One test removed: interrupting a developer's --set model (the write is no longer reachable).
    Not changed, for the tech writer: sq role/skill have no update verb; update is reachable through sq import. Adopter-visible: update (except a role's title), body, view disable refused on role and generated-skill hosts; sq role catalog lists every activated role the document does not declare.
- [2026-10-16T22:43:59Z] Elias Python:
  - F4-F7 fixed. Also: the origin stamp is now written inside the flatten write for files that flatten rewrites (the write-once-per-transaction rule from the merged work flagged the double write on the v0_15 corpus in the -C migrate tests); the origin writer only handles files flatten leaves alone.
- [2026-10-16T22:48:08Z] Catherine Manager:
  - Done: REV-1082 approved; ca5866bd; full suite 12136 passed, 0 failed.
<!-- sq:discussion:end -->
