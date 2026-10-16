---
id: TASK-1070
sequence_id: 1070
type: task
title: Give skills, roles and operators the item verbs
status: Ready
parent: FEAT-977
author: tech-lead
priority: high
refs:
- TASK-990:depends-on
- TASK-1069:depends-on
- ADR-979
description: update, comment, comments and remove (rm alias) on roster entities, through
  the TASK-1069 gate; skills gain a discussion region
subentities:
- local_id: ST1
  title: Register remove on skills, roles and operators, with rm as its alias
  status: Todo
  story: US3
- local_id: ST2
  title: Give every skill a discussion region, in the template and through a 0.16
    contribution
  status: Todo
  story: US2
- local_id: ST3
  title: Add comment and comments to skills, roles and operators
  status: Todo
  story: US2
- local_id: ST4
  title: Make the system-entry gate refuse update by field, with a declared exemption
    set
  status: Todo
  story: US4
- local_id: ST5
  title: Add update for display fields on skills, roles and operators
  status: Todo
  story: US1
- local_id: ST6
  title: Rewrite the docs passages that deny a roster update verb
  status: Todo
  assignee: tech-writer
  story: US3
created_at: '2026-10-16T19:52:27Z'
updated_at: '2026-10-16T22:48:25Z'
---
<!-- sq:body -->
## Scope

Skills, roles and operators gain the item verbs they lack, under the item names: `update`,
`comment`, `comments` and `remove`, with `rm` kept as an alias of `remove`. Covers FEAT-977 US1
to US4. Out of scope: the pronouns value and the `--operator-invocable` option themselves (the
pronouns and skill invocability features add them, each as one option plus one row in this
task's exemption table), a role's definition fields (they come from the role catalog and its
overrides on every read), and any slug change.

## Rulings this task carries (binding, not reopened)

- **A slug is permanent** (ADR-979 decisions 1 and 6). No `update` takes a slug option or moves
  a file; `_rename` in `_services/_items.py` already keeps a roster item's slug and path.
  `tests/cli/test_a_roster_slug_is_fixed_at_creation_cli.py` stays green unchanged.
- **A role's stored name is its name** (op-pierre, 2026-10-16, on BUG-1049 and TASK-1059). It
  is set at creation, never changed by a configuration change, and renamed only through
  `sq role <slug> update --title`. `--title` is the role's name, as it is an item's title.
- **`status`, `rm` and `comment` stay allowed on system roles and skills; only `update`, `body`
  and view edits are refused** (op-pierre, 2026-10-16, on FEAT-976). `remove` is `rm` under the
  item verb name, so it is allowed on system entries too. FEAT-977 US3 and US4 still list
  `remove` as refused; that text predates the ruling and the product owner is asked to amend it.
- **Comments are allowed on system skills and roles** (op-pierre, 2026-09-29, on FEAT-977).
- **The refusal is TASK-1069's gate**, reading the body-refusal classification
  (`views.roster_body_view_name`), never the stored `origin`. This task calls that gate from
  every new content-changing verb and writes no membership test of its own. `--force` never
  lifts it.
- **`update` edits display fields only** (ADR-979 decision 6). No roster `update` takes `--set`.

## The verb set after this task

| entity | update options | comment, comments | remove (rm alias) | refused on a system entry |
|---|---|---|---|---|
| skill | `--title`, `--desc`, `--when-to-use` | yes | `--purge`, as `rm` today | every update option (named surface: the playbook) |
| role | `--title` (the name) | yes | `--purge`, as `rm` today | none of today's options (the name is identity); see the role-name question on FEAT-977 |
| operator | `--title` (the display name) | yes | `--purge`, as `rm` today | operators are never system |

`remove` is the existing `rm` command registered under the item name; `rm` is the same command,
hidden from `--help`. Same flags, same messages, same exit codes.

## Order and shared files

Depends on TASK-990 and TASK-1069 (itself after TASK-990). Build order:
TASK-990, then TASK-1069 through its ST6 gate, then this task. Shared files:

| file | TASK-990 | TASK-1069 | this task |
|---|---|---|---|
| `_cli/_role.py` | ST4, ST8 to ST11 | ST4 origin column | ST1 remove, ST3 comment verbs, ST5 update |
| `_cli/_common.py` | create lane on the role card | none | ST1, ST3 shared registration helpers beside `register_status_verb` |
| `_services/_roster.py` | ST8, ST10 (`add_dev`) | ST3 stamps | none (reads only) |
| `_services/_items.py` | none | ST6 the gate in `_reject_unwritable_body` | ST4 exemption set, ST5 calls |
| `_cli/_skill.py`, `_cli/_operator.py` | none | ST4 origin on skill show | ST1, ST3, ST5 |
| `_migrations/_v0_15_to_v0_16.py` `CONTRIBUTIONS` | ST8 appends | ST5 appends | ST2 appends after TASK-1069's |
| `templates/agents/skill.md.j2`, `templates_manifest.json` | regenerated per bundled change | regenerated with ST2 | ST2 adds the discussion region |

## Files touched

`src/squads/_cli/_common.py`, `_cli/_skill.py`, `_cli/_role.py`, `_cli/_operator.py`,
`_services/_items.py` (the gate's exemption set only), `_rendering/templates/agents/skill.md.j2`,
`_migrations/_v0_15_to_v0_16.py`, `_rendering/templates_manifest.json` and the content store;
tests under `tests/cli`, `tests/integration`, `tests/meta`; the migrated-corpus goldens and the
`v0_16` fixture regenerated by their README rules. Docs and CHANGELOG are ST6, the tech writer's.

## Acceptance (whole task)

- Every acceptance bullet of FEAT-977 US1 to US4 is pinned by a named test, except the pronouns
  and `--operator-invocable` bullets, which the features that add those options pin by adding a
  row to the tables below. The handoff maps bullet to test.
- **Table-driven shape tests**, one parametrised module per backbone table, not one test per
  branch:
  - *Verb by shape.* Rows (shapes): bundled skill (`squads`); generated `sq-<type>` skill;
    system skill whose view is dropped from `[selected]`; project skill; bundled role; bundled
    role with a per-slug override; templated developer; declared developer; project role;
    retired (Archived) role; operator; retired operator. Columns (verbs): `update --title`,
    `update --desc`, `update --when-to-use`, `update` with an exempt option combined with a
    refused one, `comment`, `comments`, `comments --json`, `remove` without `--purge`,
    `remove --purge`, `rm --purge`, `status Archived`; each with `--force` where the flag
    exists. Each cell: bare exit code, printed text (the named surface on refusal), file hash
    unchanged on refusal, `~/.local/bin/sq check`-equivalent clean afterwards.
  - *Identity by update.* Rows: each entity's `update` with each display option and with no
    option. Columns: slug, file name, id, `.claude/` pointer directory before and after (all
    equal); the changed display value in the file, in `show` and `show --json`, and in the
    regenerated pointer or managed `CLAUDE.md` roster line.
- **Pipeline invariants:** delete the index then `sq repair` gives the same values after every
  verb; `sq sync` after an `update` is a fixed point (second run changes no file); `rm` and
  `remove` produce byte-identical trees from the same start.
- **A falsified test per subtask:** break the change on purpose, watch the named test go red,
  restore; the handoff records what was broken and which test went red.
- A service-level test and a CLI smoke test per behaviour change; CLI tests assert the bare exit
  code and the printed text.

## Gates and working rules

TASK-990's "Gates and working rules" apply unchanged: pyright and ruff with `--all-extras`,
`~/.local/bin/sq check` clean, `tests/meta` on any module constant, bundled-byte, migration or
import-edge change; test selection derived from the diff, the manager runs the full suite;
one-or-two sentence comments with no versions or ticket ids; no ticket ids in test file names;
no edits to `CHANGELOG.md`, `docs/` or the hand-written `CLAUDE.md` outside ST6; probing only in
a scratch squad under the session scratchpad.

## Subtask order

ST1 (independent), ST2 then ST3 (commit point, reviewed), ST4 then ST5 (commit point, reviewed), ST6 last, from the ST5 handoff. ST4 and ST5 wait for TASK-1069 ST6.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1070 add-subtask "<title>"`; track with `sq task 1070 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Register remove on skills, roles and operators, with rm as its alias

<!-- sq:subtask:ST1:body -->
**Goal.** `remove` exists on skills, roles and operators and is the command `rm` is today; `rm`
stays as a hidden alias of the same command.

**Approach**

- One shared helper in `_cli/_common.py`, beside `register_status_verb`, registers the delete
  verb on an addressed roster subgroup under `remove` and, hidden, under `rm`. It drives
  `Service.remove_item(item_id, purge=...)` exactly as the three `rm` commands do now, prints
  the same lines and the same warnings, and takes the per-module `id_from_ctx` and an optional
  post-step (the operator's `refresh_managed`).
- Delete the three copies (`skill_rm`, `role_rm`, `operator_rm`) and call the helper.
- No gate call: `rm` stays allowed on system roles and skills (op-pierre, 2026-10-16, on
  FEAT-976), so `remove` is too.

**Tests**

- Table: shape (the task body's rows) by verb (`remove`, `rm`; each with and without
  `--purge`). Each cell: bare exit code, printed text, resulting tree hash. Invariant: `remove`
  and `rm` give byte-identical trees and identical output from the same start.
- `--help` of each subgroup lists `remove` and not `rm`.

**Falsify.** Register `rm` without `--purge`: the purge-refusal column goes red for `rm`. Drop the
operator post-step: the managed `CLAUDE.md` row for the operator goes red. Restore each.

**Acceptance**

- FEAT-977 US1 bullet 3 and the US3 alias bullet.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Give every skill a discussion region, in the template and through a 0.16 contribution

<!-- sq:subtask:ST2:body -->
**Goal.** Every skill file carries a top-level discussion region, as role and operator files
already do, so `comment` has a region to append to on every roster entity.

**Approach**

- `templates/agents/skill.md.j2` gains the `## Discussion` heading and the empty
  `sq:discussion` region after `sq:body`, as `templates/agents/role.md.j2` has. Regenerate the
  template manifest in the same commit.
- Existing squads: one `Contribution` appended to `CONTRIBUTIONS` in
  `_migrations/_v0_15_to_v0_16.py`, after TASK-1069's. Planning (read-only) lists the skill
  files that lack the region; writing appends the heading and empty region after the body
  region's end marker, byte-preserving everything else and keeping the file's line endings;
  a file that already has the region is skipped. Nothing else in the step is edited.
- MANUAL section and summary clause: every skill now has a discussion, so skills take comments
  like roles and operators. The tech writer tightens the wording through a comment.
- `POSTCONDITIONS` row in `tests/cli/test_migrate_up_rewrites_comment_headers_cli.py`: every
  skill file carries the region.
- No lazy creation in `_comment_core`: the region is scaffolded, never conjured on first write.

**Tests**

- Table: corpus shape by step. Shapes: a bundled skill, a generated `sq-<type>` skill, a project
  skill with an authored body, a skill that already has a region, a CRLF file. Steps:
  `sq migrate up`; a second `sq migrate up`; delete the index then `sq repair`. Columns: files
  changed (hashed), bytes outside the new region unchanged, report lines, exit code.
- Fresh `sq init` and `sq skill add` write the region; migrate then `sq sync` equals a fresh init
  for the same roster (roster held constant).
- `v0_16` fixture and migrated-corpus goldens regenerated by their README rules; the expected
  diff (the region on each skill) confirmed line by line in the handoff.

**Falsify.** Append the region when one exists: the already-has-region row and the second-run
invariant go red. Normalise line endings: the CRLF row goes red. Restore each.

**Acceptance**

- `sq skill <x> comment` has a region on every skill of a migrated and of a fresh squad.
- The diff under `src/squads/_migrations/` is the appended contribution and nothing else.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Add comment and comments to skills, roles and operators

<!-- sq:subtask:ST3:body -->
**Goal.** `comment` and `comments` work on skills, roles and operators with the item semantics:
required `--as`, the ADR-979 header grammar with the permanent slug, `@mentions` reaching
`sq inbox`, `comments --json` carrying `author_slug`.

**Approach**

- Two shared helpers in `_cli/_common.py` register `comment` and `comments` on an addressed
  roster subgroup. They call the same service entry points as `_cmd_comment` and
  `_cmd_comments` in `_cli/_items.py` (`resolve_actor_or_raise`, `Service.comment`,
  `Service.comments`, `print_comments`, `comment_json`); factor the shared body out of
  `_cli/_items.py` rather than copying it.
- No gate call: a comment never touches generated content (op-pierre, 2026-09-29), allowed on
  system skills and roles.
- Role addressing keeps `_require_id` (a bundled-only slug asks to activate first).

**Tests**

- Table: shape by verb (`comment -m`, `comment --file`, `comments`, `comments --json`,
  `show --comments`). Each cell: exit code, the stored header matching the ADR-979 column-0
  pattern with the author's slug, `author_slug` in JSON, the body bytes outside the discussion
  region unchanged.
- An `@mention` in a comment on a system skill, a system role and an operator appears in
  `sq inbox <slug>`; a comment without `--as` exits 1 and writes nothing.

**Falsify.** Route the roster `comment` through the gate: the system skill and system role rows
go red. Write the header without the slug: the header-pattern column goes red. Restore each.

**Acceptance**

- FEAT-977 US2, and the US4 bullet that comment and comments succeed on a system skill and a
  system role.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Make the system-entry gate refuse update by field, with a declared exemption set

<!-- sq:subtask:ST4:body -->
**Goal.** TASK-1069's gate refuses a content-changing `update` on a system role or skill field by
field, and lets through the fields that are operator-set identity rather than generated content.

**Approach**

- The gate (TASK-1069 ST6, `_services/_items.py`) receives the set of fields an `update`
  changes. It refuses when any of them is outside the entity type's exemption set, and names
  the real authoring surface (the playbook for a skill, the role override for a role). One
  declared constant, keyed by roster type, holds the exemption sets; the meta guard on module
  constants allowlists it.
- The sets this task ships: role `{title}` (the name, per the role-name ruling, pending the
  question raised on FEAT-977); skill `{}`. The pronouns feature adds `pronouns` to role and
  operator; the skill invocability feature adds `operator_invocable` to skill. Each is a one-row
  change plus a row in this subtask's table.
- A combined call (an exempt field with a refused one) is refused whole; nothing is written.
- The classification stays `views.roster_body_view_name`; this subtask adds no membership test.

**Tests**

- Table: field by shape. Fields: each display field of each entity, alone and paired with
  every other. Shapes: the task body's role and skill rows. Each cell: refused iff the shape is
  classified and a field is outside the exemption set; on refusal the file hash is unchanged and
  the message names the surface; `--force` changes no cell.
- Meta: the exemption sets are the declared constant and nothing else; no second call site of
  `roster_body_view_name` under `_services/` outside the gate (extends TASK-1069's guard).

**Falsify.** Exempt every field: the skill `--desc` row goes red. Check only the first changed
field: the combined-call column goes red. Let `--force` skip the gate: the force column goes red.
Restore each.

**Acceptance**

- FEAT-977 US4: each content-changing `update` option hits the single classification; the
  exemption is exactly the declared set and nothing broader; `--force` does not lift it.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Add update for display fields on skills, roles and operators

<!-- sq:subtask:ST5:body -->
**Goal.** `update` exists on skills, roles and operators and edits display fields only: skill
title, description and when-to-use; role name; operator display name. No slug changes, no
`--set`, no slug option.

**Approach**

- `_cli/_skill.py`: `update --title --desc --when-to-use`, calling `Service.update` (title,
  description, and `when_to_use` through the declared attribute path, not a string index). The
  existing post-update `regen` rewrites the pointer with the new description.
- `_cli/_role.py`: `update --title`, the role's stored name. After the write, refresh the
  managed region and the role's pointers so generated files carry the new name.
- `_cli/_operator.py`: `update --title`, the display name, then `refresh_managed` (the managed
  `CLAUDE.md` operator roster).
- Every one goes through the ST4 gate with the set of fields it changes. An `update` with no
  option exits 1 with a message listing the options; nothing is written.
- No option named `--slug` on any of them;
  `tests/cli/test_a_roster_slug_is_fixed_at_creation_cli.py` stays unchanged and green.

**Tests**

- The task body's identity-by-update table, every row and column, as one parametrised module.
- A role renamed by `update --title` keeps the new name through `sq sync` and a change to
  `.overrides/roles/<slug>.toml` `full_name` (the stored name is the name).
- Skill `update` on a system skill exits 1 naming the playbook; on a project skill it succeeds
  and the pointer description changes.

**Falsify.** Let the role update take the work-item rename path: the file-name column goes red.
Skip the post-update managed refresh for operators: the `CLAUDE.md` column goes red. Restore
each.

**Acceptance**

- FEAT-977 US1 bullets 1 and 2, US3 bullets 2 and 3 (as amended by the 2026-10-16 ruling).
- The handoff lists every new option, message and exit code for the tech writer.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Rewrite the docs passages that deny a roster update verb

<!-- sq:subtask:ST6:body -->
**Goal.** Adopter docs and the CHANGELOG describe the new roster verbs and no longer say roles,
skills and operators have no `update` verb or send renames through `sq import`.

**Approach (tech writer, from the ST5 handoff)**

- Rewrite every passage that says there is no roster `update` verb or points to `sq import` for
  a rename or a display edit. Known today: `docs/overrides.md` near lines 449, 2246 and 2493,
  and `CHANGELOG.md` line 39 (the role-rename instruction). Find the rest with
  `rg -n -i 'no .?update.? verb|sq import' docs CHANGELOG.md README.md` and read each hit.
- Add the 0.16 CHANGELOG entry for `update`, `comment`, `comments` and `remove` on roster
  entities, `rm` as an alias, and the skill discussion region added by the migration.
- `docs/stability.md`: the roster verb names under the CLI surface tier, if listed there.
- Present truth only: no "no longer", no history outside the CHANGELOG.

**Acceptance**

- The `rg` above returns no passage that denies the verb or routes a rename through `sq import`;
  each remaining `sq import` hit is about bulk import.
- Every command shown in the rewritten passages was run in a scratch squad and its output
  matches the text.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T21:17:00Z] Catherine Manager:
  - ST5 addition (FEAT-1054 decision, 2026-10-16): update re-renders a body that is still unwritten, so a rename never makes the seeded template count as written. No stored flag.
<!-- sq:discussion:end -->
