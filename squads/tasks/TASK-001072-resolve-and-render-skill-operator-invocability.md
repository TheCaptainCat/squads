---
id: TASK-1072
sequence_id: 1072
type: task
title: Resolve and render skill operator invocability
status: Ready
parent: FEAT-966
author: tech-lead
refs:
- TASK-1069:depends-on
- ADR-983:implements
- TASK-1070:depends-on
description: 'A declared default per bundled skill, a squad''s stored choice set by
  the CLI, rendered as user-invocable: false by the Claude Code backend'
subentities:
- local_id: ST1
  title: Declare each bundled skill's default and resolve operator_invocable in one
    place
  status: Todo
  story: US1
- local_id: ST2
  title: 'Render user-invocable: false from all three Claude Code pointer sites'
  status: Todo
  story: US2
- local_id: ST3
  title: Add --operator-invocable yes/no/default to sq skill add and update
  status: Todo
  story: US3
- local_id: ST4
  title: Show the resolved value and whether the squad set it
  status: Todo
  story: US6
- local_id: ST5
  title: Keep the AGENTS.md backend silent about operator_invocable
  status: Todo
  story: US4
- local_id: ST6
  title: 'Prove the upgrade path: drift before sq sync, clean after'
  status: Todo
  story: US5
- local_id: ST7
  title: Observe a hidden skill preloading into a subagent on a real host
  status: Todo
  assignee: qa
  story: US2
created_at: '2026-10-16T19:55:32Z'
updated_at: '2026-10-17T03:11:06Z'
---
<!-- sq:body -->
## Scope

Deliver FEAT-966 as ADR-983 rules it, on the flat frontmatter of ADR-1007. Covers stories 1 to 6.

- `operator_invocable` is an attribute of a skill. A bundled skill's default is declared in its
  bundled definition in `_interactions`, beside its description and view name: one value for each
  of `squads`, `sq-memory` and `greeting`, one shared by every `sq-<type>` skill. All `false`. A
  skill with no bundled definition (every author-defined skill) defaults to invocable.
- A squad's own value is the top-level `operator_invocable` key, a declared `bool` attribute on
  `skill` (`settable = false`), pinned. Only `sq skill add` and `sq skill <addr> update` write it,
  through `--operator-invocable <yes|no|default>`.
- One resolver in the engine: the stored value when it is a YAML boolean, else the declared
  default. It also answers whether the value is the squad's own. Backends receive the resolved
  value and never re-derive it.
- Claude Code: `pointer_skill.md.j2` emits `user-invocable: false` when the value is false and
  nothing when true. `disable-model-invocation` is never written. The host key is spelled only in
  that template.
- AGENTS.md: writes and warns nothing, and says in its own definition that it has no place for
  the value.

Binding rulings, not reopened: op-pierre on FEAT-966, 2026-09-28 (every bundled skill not
invocable, `greeting` included; every author-defined skill invocable, `releasing-squads`
included); op-pierre on ADR-983, 2026-10-09 (an attribute of the skill, not derived from origin; a
bundled default in the definition, a squad's value in frontmatter; the revision accepted with one
shared per-type default, a stored choice that never follows a release, and the three-valued
option); ADR-1007 (top-level key, declared in the spec). `origin` is not read anywhere here.

Implementation hazard named by the architect: the generic `--set` coercion
(`_models/_metadata.py::coerce`) turns unrecognised text into `false`. The option is parsed on
its own and refuses anything but `yes`, `no`, `default`.

## New state, and why

One optional stored key per skill, written only by a verb, because the squad's choice must
survive a release that changes a default (ADR-983 clause 3). The default is code, never copied
onto an item. No index field beyond the attribute mapping, no spec key, no override surface.

## Migration

None. Nothing is stamped on any skill, and an absent key means the declared default. Between the
upgrade and the first `sq sync`, `sq check` warns that each system skill pointer drifted; the sync
clears it (ST6). No contribution to `_migrations/_v0_15_to_v0_16.py` and no POSTCONDITIONS row.

## Order and dependencies

Starts after TASK-1069 is Done (its ST6 builds the system-entry write gate this option is exempt
from, and it edits the same skill files) and after FEAT-977's task delivers `sq skill <addr>
update` (depends-on refs).

| file | TASK-990 | TASK-1069 | this task |
|---|---|---|---|
| `_interactions/__init__.py` (`SKILL_DESCRIPTIONS`, `SYSTEM_SKILL_VIEW_NAMES`, `is_system_skill`) | ST5, ST6 | ST1 homes the origin rule here | ST1 declares the defaults here |
| `_specs/workflow.toml`, `_workflow/_models.py` (`PINNED_ROSTER_ATTRIBUTES`) | ST8 | ST2 | ST1 |
| `_models/_attributes.py` | ST8 | ST2 | ST1 |
| `_services/_roster.py` (`add_skill`) | ST8, ST10 | ST3 | ST3 |
| `_services/_items.py` (write gate) | | ST6 | ST3 (exemption) |
| `_cli/_skill.py` | | ST4 | ST3, ST4 |
| `_backends/_claude_code/_backend.py`, `pointer_skill.md.j2` | | | ST2 |
| `_backends/_agents_md/_backend.py` | | | ST5 |
| manifest, content store | regenerated | regenerated | regenerated |

FEAT-961's task touches the same pin table and attribute module; whichever lands second rebases
and regenerates the manifest. The two do not otherwise wait on each other.

## Files

`_interactions/__init__.py`, `_specs/workflow.toml`, `_workflow/_models.py`,
`_models/_attributes.py`, `_services/_roster.py`, `_services/_items.py`, `_services/_maintenance.py`
(the sync path that hands resolved values to the managed writer), `_cli/_skill.py`,
`_backends/_claude_code/_backend.py`, `_rendering/templates/claude/pointer_skill.md.j2`,
`_backends/_agents_md/_backend.py`, `templates_manifest.json` and the content store. Tests under
`tests/integration`, `tests/cli`, `tests/meta`; goldens regenerated by their README rules.

## Acceptance (whole task)

- Every acceptance bullet of FEAT-966 US1 to US6 is pinned by a named test; the handoff maps
  bullet to test.
- **Table-driven shape tests**, one backbone table, *skill shape by surface.* Rows: `squads`;
  `sq-memory`; `greeting`; a bundled `sq-<type>` skill; the `sq-<type>` skill of a
  project-declared type; an author-defined skill; an author-defined skill named `sq-onboarding`;
  each of those with stored `true`, stored `false`, a stored value equal to its default, a
  non-boolean stored value (`"no"`, `1`, a list). Columns: the SKILL.md pointer from the managed
  writer, from the item entry and from the pure render `sq check` compares; `sq check` drift; `sq
  skill <addr> show` text; `--json` `operator_invocable` and `operator_invocable_set`; the item
  frontmatter; the index after delete-then-`sq repair`; `AGENTS.md`.
- **Pipeline invariants:** `sq init` then `sq sync` writes no `operator_invocable` key anywhere;
  `sq sync` is a fixed point and never changes a stored value; the three render sites agree on
  every row (no drift on any of them before and after a set); `AGENTS.md` is byte-identical with
  and without stored values; changing a bundled default moves exactly the skills with no stored
  value.
- A falsified test per subtask: break the change, watch the named test go red, restore. The
  handoff records what was broken and which test went red.
- The handoff gives the tech writer the release-note facts of US5 (bundled `/name` stops running
  after the first sync; a later default change reaches unstored skills on the next sync).

## Gates and working rules

TASK-990's "Gates and working rules" apply unchanged: pyright/ruff with `--all-extras`,
`~/.local/bin/sq check` clean, `tests/meta` on any module constant, bundled-byte or import-edge
change; test selection derived from the diff, the manager runs the full suite; one-or-two sentence
comments with no versions or ticket ids; no ticket ids in test file names; no edits to
`CHANGELOG.md`, `docs/` or the hand-written `CLAUDE.md`; probing only in a scratch squad under the
session scratchpad, never at the repository root.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1072 add-subtask "<title>"`; track with `sq task 1072 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare each bundled skill's default and resolve operator_invocable in one place

<!-- sq:subtask:ST1:body -->
**Goal.** Each bundled skill declares its default beside its description, a guard holds the declaration closed, the squad's key is a declared pinned attribute, and one resolver answers both the value and whether it is the squad's own.

**Approach**

- `_interactions/__init__.py`: a declaration of the default for each always-on skill and one for the per-type family, next to `SKILL_DESCRIPTIONS`, `SYSTEM_SKILL_VIEW_NAMES` and `ITEM_SKILL_VIEW_NAME`. All `false`. An import-time assert closes it against the always-on set.
- "Has a bundled definition" is the test that already decides whether the engine supplies the description (`is_system_skill`). No second membership test; the slug's spelling plays no other part; `origin` is not read.
- `_specs/workflow.toml`: `operator_invocable = { kind = "bool", settable = false }` under `[items.skill.attributes]`; pinned in `PINNED_ROSTER_ATTRIBUTES`. `_models/_attributes.py`: `AttributeKey.OPERATOR_INVOCABLE` and a strict accessor that returns a value only for a real boolean.
- One resolver `(slug, item or None, spec) -> (value, is_set)`: the stored boolean when present, else the declared default, else `True` for a skill with no bundled definition. With no item (before indexing) it returns the declared default and `is_set = False`.

**Tests**

- Table: the skill shape rows of the task body by resolver output (value, is_set).
- Guard: adding an always-on skill without a declared default fails at import.
- Spec: an override dropping the attribute from `skill` is refused at load naming the key.

**Falsify.** Resolve from the `sq-` prefix: the `sq-onboarding` row goes red. Accept a stored `"no"` as false: the non-boolean row goes red. Restore each.

**Acceptance.** FEAT-966 US1, all bullets except the pointer bullet (ST2).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Render user-invocable: false from all three Claude Code pointer sites

<!-- sq:subtask:ST2:body -->
**Goal.** The Claude Code skill pointer carries `user-invocable: false` exactly when the resolved value is false, and the three render sites agree so `sq check` never reports a drift loop.

**Approach**

- `pointer_skill.md.j2`: one conditional line. The only place the host key is spelled.
- `_write_managed_skill` (item-less, init and sync) is handed resolved values by the service, the way `skill_paths` and `role_skills` already reach it. `generate_skill_entry` and `render_skill_entry` resolve from the item through the engine resolver. No backend reads the stored key or the declared default.
- The `AgentBackend` ABC gains no abstract method.
- `disable-model-invocation` is never written; a role's `skills:` preload list is unchanged.

**Tests**

- Table: render site by skill shape. Sites: managed writer, item entry, pure render. Shapes: the task body rows. Per cell: the exact frontmatter; `sq check` reports no drift for any site, before and after a stored value is set.
- First write of `sq init` (no items yet): every bundled pointer carries the line; an author-defined skill added later does not.
- Grep guard: `user-invocable` appears in `src/` only in the template (validated against a known positive first).
- Role pointer `skills:` lists are byte-identical to before.

**Falsify.** Resolve differently in the managed writer (ignore the stored value): the drift column goes red after a set. Restore.

**Acceptance.** FEAT-966 US2, every bullet except the real-host preload bullet (ST7); US1 pointer bullet.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Add --operator-invocable yes/no/default to sq skill add and update

<!-- sq:subtask:ST3:body -->
**Goal.** `sq skill add` and `sq skill <addr> update` take `--operator-invocable <yes|no|default>`: yes and no store the value even when equal to the default, default removes it, absent changes nothing, anything else is refused.

**Approach**

- `_cli/_skill.py`: a dedicated three-valued parser, not the generic `--set` coercion. Any other text: exit 1, nothing written.
- `_services/_roster.py` (`add_skill`) and the skill update service: store or remove the top-level key; regenerate that skill's entry on every active backend.
- `_services/_items.py`: the system-entry write gate lets this option through on a system skill; it is the only update option a system skill accepts. Every other option stays refused.
- Init, sync, seeding and migrations never write the key: assert it in the code paths, not only in tests.

**Tests**

- Table: verb by value by shape. Verbs: `add`, `update`. Values: `yes`, `no`, `default`, omitted, `Yes`, `false`, `""`. Shapes: bundled skill, `sq-<type>` skill, author-defined skill. Per cell: exit code, frontmatter key after, pointer line after, file hash unchanged on refusal.
- System skill: `update --operator-invocable yes` succeeds; `update --title x` is still refused.
- The stored value survives `sq sync`, and deleting the index plus `sq repair`.
- Release behaviour: patch a bundled default in the test; a skill with a stored value keeps it, one with none follows after `sq sync`.

**Falsify.** Route the option through the generic coercion: the `Yes` and `""` rows store false. Drop a value equal to the default: the equal-to-default row goes red. Restore each.

**Acceptance.** FEAT-966 US3, all bullets.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Show the resolved value and whether the squad set it

<!-- sq:subtask:ST4:body -->
**Goal.** `sq skill <addr> show` prints the resolved value and whether it is the squad's own; its `--json` carries `operator_invocable` and `operator_invocable_set` on every row.

**Approach**

- `_cli/_skill.py`: one line in the text view (value plus "set by this squad" or "declared default"); two keys in the `--json` payload, from the engine resolver.
- Any other `--json` surface that publishes a skill's own fields gets the same two keys; list them in the handoff.

**Tests**

- Table: skill shape by output. Rows: the task body rows. Columns: text line; `operator_invocable`; `operator_invocable_set`.
- A skill whose stored value equals its default shows set true; after `--operator-invocable default`, set false and the same value.
- Exact key-set assertion on the payload.

**Falsify.** Derive `_set` from value differing from the default: the equal-to-default row goes red. Restore.

**Acceptance.** FEAT-966 US6, all bullets.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Keep the AGENTS.md backend silent about operator_invocable

<!-- sq:subtask:ST5:body -->
**Goal.** The AGENTS.md backend is unaffected: nothing written, nothing warned, and its own definition says it has no place for the value.

**Approach**

- `_backends/_agents_md/_backend.py`: one sentence beside its existing statements about the model, colour and preload list. No code path reads the value.

**Tests**

- Regression: a squad regenerated under the AGENTS.md backend produces a byte-identical `AGENTS.md` with and without a stored value on a skill, and with both backends active.
- No warning or log line mentions the value.
- A test backend written against the existing ABC needs no change.

**Falsify.** Emit a line for a hidden skill: the byte-identical test goes red. Restore.

**Acceptance.** FEAT-966 US4, all bullets.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Prove the upgrade path: drift before sq sync, clean after

<!-- sq:subtask:ST6:body -->
**Goal.** An existing squad receives the new pointer line through `sq sync` alone: before it, `sq check` warns of drift on each system skill pointer without changing the exit code; after it, `sq check` is clean.

**Approach**

- No code beyond ST2. This subtask proves the upgrade path and updates the fixtures that freeze generated pointers.
- Use a 0.15 corpus fixture (or a scratch squad initialised by the released tool under the session scratchpad), migrated by the build under test.

**Tests**

- Upgrade path: migrate, then `sq check` (exit code unchanged, one drift warning per system skill pointer, none for authored skills), then `sq sync`, then `sq check` clean.
- Migrated-corpus goldens and any golden that freezes a SKILL.md pointer are regenerated by their README rules; the diff shows only the new line.

**Falsify.** Skip the line in the pure render only: the post-sync check stays dirty. Restore.

**Acceptance.** FEAT-966 US5, the first two bullets; the release-note bullet goes to the writer from the task handoff.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Observe a hidden skill preloading into a subagent on a real host

<!-- sq:subtask:ST7:body -->
**Goal.** See once on a real Claude Code host that a skill marked `user-invocable: false` still preloads into a subagent whose `skills:` list names it. ADR-983 infers this from the host documentation; the default does not ship until it is observed.

**Method**

- In a scratch project under the session scratchpad, initialised by the build under test after ST2: hand-add a unique sentinel line to one bundled skill's `SKILL.md` pointer (what the host preloads is that file), confirm the pointer carries `user-invocable: false`, and define an agent whose `skills:` list names it.
- Run the host non-interactively (`~/.local/bin/claude -p`) asking that agent to quote the sentinel without reading any file. Record the command, the host version and the output on this subtask.
- Control: the same run with `disable-model-invocation: true` hand-added to the pointer should fail to preload, proving the probe can tell the cases apart.

**Acceptance.** FEAT-966 US2 last bullet: the observation is recorded. If the skill does not preload, stop and raise it to @manager before the task closes. Owner: qa; the operator if the host cannot be driven from an agent shell.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T19:58:48Z] Olivia Lead:
  - Broken down into ST1-ST7. No migration contribution (nothing stamped; drift warning until the first sq sync, pinned in ST6). Depends on TASK-1069 (write gate exemption, same skill files) and the FEAT-977 sq skill update verb. ST7 (qa) observes preload on a real host before the default ships. @manager
<!-- sq:discussion:end -->
