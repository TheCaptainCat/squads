---
id: TASK-1071
sequence_id: 1071
type: task
title: Add pronouns to roles and operators
status: Done
parent: FEAT-961
author: tech-lead
refs:
- TASK-990:depends-on
- TASK-1069:depends-on
- ADR-981:implements
- TASK-1070:depends-on
- TASK-1079:depends-on
description: Declared pronouns attribute, a resolved roster default, roster --json,
  generated files, a typed display table and the VS Code setting
subentities:
- local_id: ST1
  title: Declare and pin the pronouns attribute, with one shape rule and a check
  status: Done
  story: US1
- local_id: ST2
  title: Set and clear pronouns through the creation and update verbs
  status: Done
  story: US1
- local_id: ST3
  title: Resolve a declared roster default from the role catalog document
  status: Done
  story: US2
- local_id: ST4
  title: Carry resolved pronouns in the four roster --json payloads
  status: Done
  story: US3
- local_id: ST5
  title: Render pronouns in the generated roster section and identity pointer
  status: Done
  story: US4
- local_id: ST6
  title: Add the typed display table to .squads.toml
  status: Done
  story: US5
- local_id: ST7
  title: Print Name (pronouns) dimmed in human CLI output and sq ui
  status: Done
  story: US4
- local_id: ST8
  title: Show pronouns in the VS Code client behind its own setting
  status: Done
  assignee: typescript-dev
  story: US4
created_at: '2026-10-16T19:53:59Z'
updated_at: '2026-10-17T03:14:22Z'
---
<!-- sq:body -->
## Scope

Deliver FEAT-961 as ADR-981 rules it, on the flat frontmatter of ADR-1007. Covers stories 1 to 5.

- `pronouns` is a declared attribute of `role` and `operator` (`[items.<type>.attributes]` in
  `_specs/workflow.toml`, `kind = "str"`, `settable = false`: only a verb that names it writes it),
  pinned in `PINNED_ROSTER_ATTRIBUTES` for both types, since the engine renders it into host files.
- One shape rule, one function: one line, trimmed, 1 to 40 characters, no control character, no sq
  marker tag. The verbs, the `[defaults]` loader, the typed accessor and `sq check` all call it.
- A role's pronouns resolve in `resolve_role_for_item`: its own value, else `[defaults].pronouns`
  from the role catalog document, else unset. An operator's: its own value, else unset. The
  resolved value is never written to an item.
- The four roster `--json` viewers carry `pronouns` (resolved, string or null, always present).
- Generated agent-facing files (roster section of `CLAUDE.md`/`AGENTS.md`, the agent's identity
  pointer) always carry pronouns.
- `[display]` in `.squads.toml`: typed, closed, one boolean `pronouns`, default true; it changes
  only human CLI output and `sq ui`.
- The VS Code client joins slugs to the roster viewers and has its own setting (ST8).

Binding rulings, not reopened: ADR-981 as accepted by op-pierre on 2026-10-09 (display on by
default, a declared default rather than stamped values, a typed table rather than a settings
system); op-pierre on FEAT-961, 2026-09-24 (generated agent-facing files always carry pronouns);
ADR-1007 as accepted on 2026-10-15 (top-level key, declared in the spec).

Not in this task: a `sq init` pronouns flag. ADR-981 allows one as shorthand but does not require
it; declaring `[defaults]` in the override and running `sq sync` is the one path, at init and
later. A flag can be added without changing anything here. Also out: a bulk-apply verb, a
`sq config` verb, a per-user file, pronoun-aware grammar, any change to name generation.

## New state, and why

One stored key (`pronouns` on role and operator items), one key in the role catalog document's
top-level space (`defaults`), one typed table in `.squads.toml` (`[display]`). Each is the
decision itself. No index field beyond the attribute mapping, no precedence ladder beyond
own-else-default, nothing stamped.

## Migration

None. Nothing is stored before this feature, an absent `pronouns` means unset, an absent
`[display]` means defaults and an absent `[defaults]` means no default (ADR-981, Consequences). No
contribution to `_migrations/_v0_15_to_v0_16.py` and no POSTCONDITIONS row.

## Order and dependencies

Starts after TASK-990 and TASK-1069 are Done, and after FEAT-977's task delivers the `update` verbs
on roles and operators (depends-on refs). TASK-990's body already says it is not built in parallel
with this feature.

| file | TASK-990 | TASK-1069 | this task |
|---|---|---|---|
| `_specs/workflow.toml`, `_workflow/_models.py` (`PINNED_ROSTER_ATTRIBUTES`) | ST8 removes `is_dev` | ST2 adds `origin` | ST1 adds `pronouns` on role and operator |
| `_models/_attributes.py` | ST8 | ST2 | ST1 `AttributeKey.PRONOUNS` and accessor |
| `_roles/_loader.py`, `_roles/_models.py` (closed top-level key space) | ST2 adds `capabilities` | | ST3 adds `defaults` |
| `_roles/_resolver.py`, `_roles/_catalog.py` (`RoleDef`) | ST2, ST6, ST8 | ST1 | ST3 |
| `_roles/_projection.py` (`RoleView`, `OperatorView`) | ST4, ST6 | ST4 | ST4 |
| `_services/_roster.py` | ST8, ST10 | ST3 | ST2 |
| `_services/_validators.py`, `_workflow/_models.py` catalogs | ST5 | ST2 | ST1, ST6 |
| `_cli/_role.py`, `_cli/_dev.py`, `_cli/_operator.py` | ST4, ST10 | ST4 | ST2, ST4, ST7 |
| `_services/_items.py` (system-entry write gate) | | ST6 | ST2 (pronouns exempt) |
| templates (roster section, identity pointer) + manifest | ST7 | ST2 | ST5 |

FEAT-966's task touches the same pin table and attribute module; whichever lands second rebases
and regenerates the manifest. FEAT-902's task introduces the always-on/selectable squad-global
partition; ST6's new always-on member joins it (see ST6).

## Files

`_specs/workflow.toml`, `_workflow/_models.py`, `_models/_attributes.py`, `_models/_config.py`,
`_roles/_loader.py`, `_roles/_models.py`, `_roles/_resolver.py`, `_roles/_catalog.py`,
`_roles/_projection.py`, `_services/_roster.py`, `_services/_items.py`, `_services/_validators.py`,
`_cli/_role.py`, `_cli/_dev.py`, `_cli/_operator.py`, `_cli/_common.py`, `_tui/` (name rendering),
templates `claude/claude_section.md.j2`, `agents_md/agents_section.md.j2` and the role pointer
template, `templates_manifest.json` and the content store; `clients/vscode/` (ST8). Tests under
`tests/integration`, `tests/cli`, `tests/meta`, `tests/tui`; goldens regenerated by their README
rules.

## Acceptance (whole task)

- Every acceptance bullet of FEAT-961 US1 to US5 is pinned by a named test; the handoff maps
  bullet to test.
- **Table-driven shape tests**, two backbone tables:
  - *Value shape by entry point.* Rows: `they/them`; 1 char; 40 chars; 41 chars; surrounding
    whitespace; empty; whitespace only; embedded newline; tab; other control char; an sq marker
    tag; square brackets (`[x]`); non-ASCII (`elle/iel`). Columns: `sq role activate`,
    `sq dev add`, `sq operator add`, role `update`, operator `update`, `[defaults].pronouns` in
    the override, a hand-edited stored value. Per cell: exit code, what is stored (absent, or the
    trimmed value), what `sq check` reports, what the renderers show.
  - *Resolution by surface.* Rows: bundled role with own value; bundled role, no value, default
    declared; templated developer; declared developer; project role; operator with own value;
    operator, no value, default declared; any of these with an invalid stored value. Columns:
    `sq role list --json`, `sq role <addr> show --json`, `sq operator list --json`,
    `sq operator <addr> show --json`, human show/list with `[display] pronouns` true and false,
    `CLAUDE.md` roster, `AGENTS.md` roster, identity pointer, the item file after `sq sync`.
- **Pipeline invariants:** `sq sync` is a fixed point and never writes or removes `pronouns`;
  adding then removing `[defaults]` plus `sq sync` returns every file byte-identical to before;
  `--json`, exit codes, stored data and generated files are identical with `[display] pronouns`
  true and false; the index rebuilt by `sq repair` carries the same values.
- An upgraded squad with no declaration shows no new output on any surface (golden diff with the
  roster held constant).
- A falsified test per subtask: break the change, watch the named test go red, restore. The
  handoff records what was broken and which test went red.
- The handoff lists, for the tech writer: the new options, the `[defaults]` and `[display]`
  tables, the limit that an agent cannot have no pronouns under a declared default, and the
  stability-doc entries ADR-981 names.

## Gates and working rules

TASK-990's "Gates and working rules" apply unchanged: pyright/ruff with `--all-extras`,
`~/.local/bin/sq check` clean, `tests/meta` on any module constant, bundled-byte or import-edge
change; test selection derived from the diff, the manager runs the full suite; one-or-two sentence
comments with no versions or ticket ids; no ticket ids in test file names; no edits to
`CHANGELOG.md`, `docs/` or the hand-written `CLAUDE.md`; probing only in a scratch squad under the
session scratchpad, never at the repository root.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1071 add-subtask "<title>"`; track with `sq task 1071 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare and pin the pronouns attribute, with one shape rule and a check

<!-- sq:subtask:ST1:body -->
**Goal.** `pronouns` is a declared, pinned attribute of `role` and `operator`, read through one typed accessor, and `sq check` reports a stored value that fails the shape rule.

**Approach**

- `_specs/workflow.toml`: `pronouns = { kind = "str", settable = false }` under `[items.role.attributes]` and `[items.operator.attributes]`. `settable = false` keeps `sq update --set` off it.
- `_workflow/_models.py`: `pronouns` joins `PINNED_ROSTER_ATTRIBUTES` for role and for operator (kind `str`), with an operator entry added to the table.
- `_models/_attributes.py`: `AttributeKey.PRONOUNS`; one pure `pronouns_problem(raw) -> str | None` holding the shape rule (one line, trimmed, 1 to 40 characters, no control character, no sq marker tag via the existing marker check); a `pronouns(item)` accessor that returns the trimmed value only when it passes, `None` otherwise.
- `_services/_validators.py`: one per-item member, `pronouns_valid`, at `error`, in the `roster` category bundle, reporting a stored value that fails the rule and naming the item. It checks only types that declare the attribute. No other new rule.
- Regenerate the template manifest in the same commit.

**Tests**

- Table: stored shape by surface. Shapes: the value-shape rows of the task body plus `null`, a list and an integer. Surfaces: `sq check` (exit and message), the accessor, `sq update --set pronouns=x` (refused), delete the index then `sq repair` (round-trips verbatim, ADR-1007 decision 5).
- Spec: an override dropping `pronouns` from `role` or `operator` is refused at load naming the key; `sq workflow types --json` lists it on both types.

**Falsify.** Remove the operator pin: the override row loads. Make the accessor skip the rule: the 41-char and newline rows render. Restore each.

**Acceptance.** FEAT-961 US1: the shape rule and the hand-edited-value report. `tests/meta` passes.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-17T02:38:24Z] `python-dev` Elias Python:
  - Done. Pronouns declared and pinned on role and operator (workflow.toml, PINNED_ROSTER_ATTRIBUTES); one shape rule and accessor in src/squads/_pronouns.py; pronouns_valid in the roster bundle (judges the stored text, so it reports at sq check and sits the write gate out). Falsified: dropping the operator pin 1 test red; accessor skipping the rule 25 red; validator off 14 red; limit 40 to 400 7 red.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Set and clear pronouns through the creation and update verbs

<!-- sq:subtask:ST2:body -->
**Goal.** Pronouns are set on creation and changed or cleared afterwards by a verb that names them, on bundled roles too; a sync never touches them; the role documents refuse a `pronouns` key and name the verb.

**Approach**

- `--pronouns <text>` on `sq role activate`, `sq dev add`, `sq operator add`, and on the role and operator `update` verbs FEAT-977's task delivers. Input passes `pronouns_problem` before any write; a refusal is exit 1 with a message and nothing stored.
- Blank (empty or whitespace only): on `update` it removes the key; on creation it stores nothing.
- `_services/_items.py`: the system-entry write gate (TASK-1069 ST6) lets `--pronouns` through on a system role, on the same footing as a comment; every other content-changing option stays refused.
- A changed value refreshes the managed region and that role's entry on every active backend.
- `_roles/_loader.py`: a `pronouns` key in a `[[roles]]` entry or a per-slug role file is refused with a message naming `sq role <addr> update --pronouns` (today `RoleSpec`'s `extra="forbid"` refuses it without naming the verb).
- `_services/_maintenance.py`: confirm the retired-key sweep and the catalog-attribute refresh never touch `pronouns`.

**Tests**

- Table: verb by shape. Verbs: the five above. Shapes: the value-shape rows. Per cell: exit code, message, frontmatter after (absent or trimmed value), file hash unchanged on refusal.
- Bundled role (`architect`): `update --pronouns` succeeds, `update --title` in the same squad is still refused.
- `sq sync` after a set leaves the value; `sq sync` on a role carrying an invalid hand-edited value leaves it as written.
- Role override with `pronouns` in `[[roles]]` and in a per-slug file: refused, message names the verb.

**Falsify.** Let the gate refuse `--pronouns` on a system role: the bundled-role row goes red. Store the untrimmed input: the whitespace row goes red. Restore each.

**Acceptance.** FEAT-961 US1, every bullet except the shape-report bullet owned by ST1.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-17T02:38:26Z] `python-dev` Elias Python:
  - Done. --pronouns on role activate, dev add, operator add and the role and operator update verbs; update carries it through the one transaction (no gate trip on a system role, so it works on bundled roles); a role document pronouns key is refused naming the verb; activate of a live role with --pronouns is refused naming update. Falsified: gate refusing pronouns on a system role 14 red; storing the untrimmed input 5 red; role-document refusal removed 2 red.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Resolve a declared roster default from the role catalog document

<!-- sq:subtask:ST3:body -->
**Goal.** The role catalog document accepts `[defaults]` with `pronouns`, and a role's pronouns resolve in one seam as own value, else default, else unset. Operators never take the default.

**Approach**

- `_roles/_loader.py`: `defaults` joins `ROLES_TOP_LEVEL_KEYS`; not a `[selected]` section. `_roles/_models.py`: a closed `DefaultsSpec` (`extra="forbid"`) with one optional `pronouns`, checked by `pronouns_problem` at load; an invalid value is refused at load and reported by `sq check` the way any invalid override is.
- `_roles/_resolver.py`: `resolve_role_for_item` computes the resolved pronouns; `RoleDef` carries it. Nothing below the resolver reads the attribute or the default directly. An operator's pronouns come from its own accessor only.
- The bundled `roles.toml` does not change bytes, and an existing catalog override reports no drift. ADR-981 marks the drift path as inferred: drive it in a scratch squad (scaffold the override with the old build, then `sq override` status on the new one) and record the result.

**Tests**

- Table: role shape by default state. Shapes: bundled, templated developer, declared developer, project role, operator. States: no default; default `they/them`; default plus own value `she/her`; default removed after a sync. Columns: resolved value, item frontmatter (never gains the key), roster `--json`.
- Override load: `[defaults]` with 41 chars, a newline, an unknown key beside `pronouns`: each refused naming the entry.
- Bundled bytes: `roles.toml` hash unchanged; existing override reports no drift.

**Falsify.** Apply the default to operators: the operator row goes red. Write the resolved value back on sync: the frontmatter column goes red. Restore each.

**Acceptance.** FEAT-961 US2, every bullet except the documentation line (writer, from the handoff).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-17T02:38:28Z] `python-dev` Elias Python:
  - Done. [defaults] pronouns in the role catalog document (closed DefaultsSpec, same shape rule, trimmed at load); resolve_pronouns in the resolver is own value else default; RoleDef.pronouns is set by resolve_role_for_item only, never stored. Bundled roles.toml bytes unchanged. Falsified: default applied to operators 3 red; resolved default written back on sync 8 red.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Carry resolved pronouns in the four roster --json payloads

<!-- sq:subtask:ST4:body -->
**Goal.** `sq role list`, `sq role <addr> show`, `sq operator list` and `sq operator <addr> show` carry a top-level `pronouns` key beside `full_name` in `--json`: the resolved value, a string or null, always present.

**Approach**

- `_roles/_projection.py`: `RoleView` and `OperatorView` gain `pronouns`, filled from the resolved role and the operator accessor.
- `_cli/_role.py`, `_cli/_operator.py`: emit the key in each of the four payloads.
- Nothing is added to item rows, `discussion[]` entries or comment headers. The generic item JSON carries the stored attribute flat only when stored (ADR-1007 decision 10) and is not the contract surface.

**Tests**

- Table: payload by role shape, using the resolution rows of the task body. Per cell: key present, value equals the resolved value, `null` when unset.
- Exact key-set assertions on each of the four payloads (not a superset check), so a missing or extra key goes red.
- Item rows and `discussion[]` of `sq show --json` on an item authored by a role with pronouns: no `pronouns` key.
- Same output with `[display] pronouns` true and false.

**Falsify.** Omit the key when unset: the null rows go red. Emit the stored value instead of the resolved one: the default-declared row goes red. Restore each.

**Acceptance.** FEAT-961 US3, all bullets.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-17T02:38:30Z] `python-dev` Elias Python:
  - Done. RoleView and OperatorView carry pronouns; the four roster --json payloads emit the resolved value beside full_name, always present, exact key sets pinned; item rows and discussion entries gain nothing. Falsified: key omitted when unset 2 red; stored value emitted instead of resolved 2 red.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Render pronouns in the generated roster section and identity pointer

<!-- sq:subtask:ST5:body -->
**Goal.** The roster section of `CLAUDE.md` and `AGENTS.md` and an agent's own identity pointer carry the resolved pronouns, whatever `[display]` says, and `sq sync` picks up a changed value or default.

**Approach**

- Templates `claude/claude_section.md.j2`, `agents_md/agents_section.md.j2` and the role pointer template render `Name (pronouns)` from `RoleView`/`OperatorView`; a name with none renders exactly as today.
- No `[display]` input reaches a backend render.
- Regenerate the manifest, the content store, the managed-section golden and the migrated-corpus goldens by their README rules.

**Tests**

- Table: generated file by roster shape. Files: `CLAUDE.md` section, `AGENTS.md` section, a role pointer. Shapes: no pronouns anywhere; own value; default declared; operator with value; `[display] pronouns = false`. Per cell: exact rendered line.
- Golden with the roster held constant: a squad with no pronouns renders byte-identical to before.
- `sq check` is clean after `sq sync` for every row (no drift loop between writer and check render).

**Falsify.** Gate the template on `[display]`: the display-false row goes red. Restore.

**Acceptance.** FEAT-961 US4, the generated-files bullet; Scope, generated agent-facing files.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-17T03:04:20Z] `python-dev` Elias Python:
  - Done. CLAUDE.md and AGENTS.md roster lines and the role pointer render the name then the pronouns whatever [display] says; templates read the key tolerantly (missing key means none); manifest and store regenerated, goldens unchanged for a squad with none. Falsified: gating the roster on [display] 1 red; pointer without pronouns 3 red.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Add the typed display table to .squads.toml

<!-- sq:subtask:ST6:body -->
**Goal.** `.squads.toml` accepts a typed, closed `[display]` table with one boolean, `pronouns`, default true. A bad key or value never stops a command; `sq check` names it.

**Approach**

- `_models/_config.py`: a `DisplaySettings` model with `pronouns: bool = True`, a field on `SquadsConfig`. Parsed tolerantly (a before-validator): an unknown key or a non-boolean value falls back to the default and is recorded as a problem on the loaded config, never raised. A quoted `"false"` is not a boolean.
- `to_toml` emits `[display]` only when a value differs from its default, so a file with no table, or with defaults only, is rewritten byte-identically by the version and schema stamps.
- `sq check`: one always-on squad-global member, `display_config_valid`, at `warn`, reporting each recorded problem by key. If FEAT-902's task has landed, it is declared in the always-on tier and the default-level table; otherwise that task adds it there.
- Renderers receive the settings from `SquadPaths.config`, as an argument. No module-level cache.

**Tests**

- Table: file content by surface. Contents: no table; `pronouns = true`; `pronouns = false`; `pronouns = "false"`; `pronouns = 1`; an unknown key; `[display]` as a non-table value. Surfaces: any command's exit code; the resolved setting; `sq check` output; the file after a version stamp and a schema stamp (byte-compare).
- No `sq config` verb exists.

**Falsify.** Raise on an unknown key: the unknown-key row stops a command. Emit the table when it holds defaults: the stamp byte-compare goes red. Restore each.

**Acceptance.** FEAT-961 US5, all bullets.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-10-17T03:04:22Z] `python-dev` Elias Python:
  - Done. DisplaySettings with tolerant parse, display_config_valid always-on at warn, stamp keeps the table verbatim, no config verb. Tests over 11 file contents x exit, setting, check output, stamped bytes. Falsified: rebuilding the table on stamp 9 red; accepting display_problems from the file 1 red.
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Print Name (pronouns) dimmed in human CLI output and sq ui

<!-- sq:subtask:ST7:body -->
**Goal.** With `[display] pronouns` true, a role or operator name with pronouns prints as `Name (pronouns)` in the CLI's human output and `sq ui`, the parenthesis dimmed; otherwise the name prints as today.

**Approach**

- One pure formatter producing the Rich renderable, taking the name, the resolved pronouns and the display setting. Every human surface that prints a role or operator name calls it; slug surfaces (assignee columns) do not. Placement follows the import-edge table; record a new edge there if one is needed.
- The pronouns text is escaped like any content string (`_cli._common.e()`).
- `sq ui` gets the setting from the threaded config.

**Tests**

- Table: surface by case. Surfaces: `sq role list`, `sq role <addr> show`, `sq operator list`, `sq operator <addr> show`, each other human surface that prints a name (enumerate them by grep on the name accessors in the handoff), and the `sq ui` roster view. Cases: pronouns set with display true; set with display false; unset; value containing `[x]`. Per cell: exact text, no empty parentheses, no trailing space, dim style on the parenthesis.
- An assignee column is unchanged in every case.

**Falsify.** Skip escaping: the `[x]` row goes red. Print `Name ()` when unset: the unset row goes red. Restore each.

**Acceptance.** FEAT-961 US4, all bullets except the generated-files bullet (ST5) and the VS Code bullets (ST8).
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-10-17T03:04:25Z] `python-dev` Elias Python:
  - Done. One formatter (_pronouns.named) used by role list/show, operator list/show, dev list, the creation messages and the sq ui tree; slug columns untouched; sq role catalog and comment headers deliberately do not carry pronouns. Falsified: Name () for unset 1 red; no dim 3 red; no escaping 10 red; tree ignores setting 1 red; operator table ignores setting 1 red.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Show pronouns in the VS Code client behind its own setting

<!-- sq:subtask:ST8:body -->
**Goal.** The VS Code client shows pronouns after a name by default, following a setting of its own, by joining a slug to the roster `--json` viewers.

**Approach**

- `clients/vscode/`: read `pronouns` from `sq role list --json` and `sq operator list --json`; render `Name (pronouns)` wherever the client shows a role or operator name, de-emphasised. Slug displays do not change.
- A new setting in `package.json`, default on, beside `squads.typeIcons`. `.squads.toml` is not read for it.
- The skew canary's floor accepts the new key on those payloads.

**Tests**

- Unit table: name rendering by case (set, unset, setting off).
- Canary: the roster payload key sets include `pronouns`.
- Changing `[display]` in `.squads.toml` changes nothing in the client; changing the VS Code setting changes nothing in the CLI.

**Falsify.** Hard-wire the setting on: the setting-off row goes red. Restore.

**Acceptance.** FEAT-961 US4, the two VS Code bullets. Owner: typescript-dev, after ST4 lands. Visual check on a dev host is the operator's.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T19:58:47Z] `tech-lead` Olivia Lead:
  - Broken down into ST1-ST8 (ST8 is typescript-dev, VS Code). No migration contribution: nothing stored before, absent keys mean unset/defaults. Depends on TASK-990, TASK-1069 and the FEAT-977 update verbs; shared files tabled in the body.
  - Choices within ADR-981: no sq init pronouns flag (ADR allows, does not require; declaring [defaults] plus sq sync is the one path); pronouns pinned on operator as well as role (rendered into host files); sq check reports via a roster-bundle member pronouns_valid and an always-on squad-global display_config_valid. @manager to confirm or overrule before dispatch.
- [2026-10-17T03:04:42Z] `python-dev` Elias Python:
  - For @typescript-dev (ST8), facts from the Python side:
    - Payload keys: `sq role list --json` rows, `sq role <addr> show --json`, `sq operator list --json` rows and `sq operator <addr> show --json` each carry a top-level `pronouns`, placed right after `full_name`: the resolved string, or `null`; always present.
    - Role value is own value, else the squad's declared roster default, else null; an operator is own value, else null. Join by `slug` (roles `architect`, operators `op-alex`); do not read pronouns from item rows or discussion entries, which carry none.
    - Render `Name (pronouns)` with the parenthesis de-emphasised; show only the name when `pronouns` is null; never print empty parentheses. Pronouns are plain text up to 40 characters.
    - The setting is the client's own (default on, beside `squads.typeIcons`). Do not read `[display]` in `.squads.toml`; the payloads are identical whatever it says.
    - Skew canary: the exact key sets are role list row: id, slug, full_name, pronouns, title, is_default, capabilities, status, origin; role show: slug, id, activated, origin, full_name, pronouns, title, mission, model, is_default, can_spawn, capabilities, create_lane, responsibilities, skills; operator list row: id, slug, full_name, pronouns, status; operator show: id, slug, full_name, pronouns, status, path.
    - Python-side reference for the human form: `squads._pronouns.named`.
- [2026-10-17T03:04:43Z] `python-dev` Elias Python:
  - For @tech-writer, adopter facts for pronouns:
    - Set at creation: `--pronouns <text>` on `sq role activate`, `sq dev add`, `sq operator add`. Change or clear later: `sq role <addr> update --pronouns <text>` and `sq operator <addr> update --pronouns <text>`; a blank value clears. It works on bundled roles. `sq init` has no pronouns flag. `--set pronouns=...` is refused and names the verb. `sq role activate <live role> --pronouns` is refused and names `update`.
    - Value rule: trimmed, one line, 1 to 40 characters counted after NFC normalisation, no control character, no invisible formatting character (bidi overrides, zero-width marks), no sq marker tag. A blank is never stored. A hand-edited value that fails the rule is reported by `sq check` (pronouns_valid, error, on roles and operators) and read as unset.
    - Roster default: `[defaults]` with `pronouns` in `.overrides/roles.toml`, same value rule, refused at load when invalid; applies to roles only, never operators, never written onto an item; declare it then run `sq sync`; remove it and sync to return roles with no value of their own to unset. Limit: a role cannot have no pronouns under a declared default. A `pronouns` key in a `[[roles]]` entry or a per-slug role file is refused and names the verb. The bundled catalog declares none.
    - `--json`: `pronouns` on the four roster viewers (resolved, string or null, always present); nothing on item rows, discussion entries or comment headers.
    - `[display]` in `.squads.toml`: typed, closed, one boolean `pronouns`, default true; it only changes human CLI output and `sq ui` (Name (pronouns), parenthesis dimmed); `--json`, exit codes, stored data and generated files are identical either way. An unknown key or non-boolean value (a quoted "false" is not a boolean) never stops a command, the default applies and `sq check` warns (display_config_valid, always on, cannot be named in [squad] validators). A version or schema stamp writes the `[display]` table back exactly as written. No `sq config` verb, per-user file or environment override. No migration and no schema bump.
    - Generated `CLAUDE.md`/`AGENTS.md` roster lines and the agent's own pointer always carry the pronouns, whatever `[display]` says; `sq sync` picks up changes.
    - Stability doc entries (ADR-981): the `pronouns` frontmatter key on role and operator items, the `[display]` table and its `pronouns` key, `defaults` in the role catalog document's top-level keys, `pronouns` on four roster --json shapes; refresh docs/roles.md and docs/overrides.md. A squad that declares a default needs this release for everyone sharing it.
- [2026-10-17T03:09:48Z] `typescript-dev` Ada Typescript:
  - ST8 done. Gates in clients/vscode: tsc, eslint --max-warnings 0, prettier --check clean; vitest 729 pass; canary (SQ_CANARY_CMD="uv run sq") 85 pass, incl. new role/operator list key-set check. Falsified: hard-wiring the setting on turned 3 tests red; restored.
  - Shown: the Roster view leaf gets a dim "(pronouns)" before the status (description slot), and the role @mention hover reads "Name (pronouns) (slug)". Setting squads.showPronouns, default on; .squads.toml is not read. Unset or older sq: no parentheses.
  - Dev host check: set pronouns with sq role <slug> update --pronouns and sq operator add --pronouns, refresh the Roster, toggle squads.showPronouns (view refreshes on change), hover an @role mention in a preview.
- [2026-10-17T03:14:00Z] `tech-writer` Theo Writer:
  - Pronouns docs written, not committed. Probed on an export of HEAD 1dba72da. This task has no docs subtask, so this comment is the handoff. @manager
    
    - docs/roles.md: new section "Pronouns" covering the verbs (set, clear, the live-role activate refusal, the `--set` and import refusal), the value rule and its errors, `pronouns_valid`, the `[defaults]` roster default, where pronouns show and never show, `[display]` with `display_config_valid`, and the VS Code `squads.showPronouns` setting.
    - docs/overrides.md: the `[defaults]` paragraph in the roles.toml section, and `display_config_valid` in the always-on squad-wide table (now seven). docs/stability.md: a "Display settings in `.squads.toml`" subsection and `pronouns` on the four roster viewers. README: the `--pronouns` options. CHANGELOG: an Added entry, and the `[squad]` entry's always-on list now includes `display_config_valid`.
    - Driven: every verb and refusal; the 41-character and bidi refusals; trimming; the blank clear; the default after sync (resolved in --json, not stored); the per-role key refusal; generated CLAUDE.md lines and the pointer; `[display] pronouns = false` (human output off, --json unchanged); the unknown-key and quoted-false warnings; the check error on a hand-edited value; no pronouns in a comment header; `display_config_valid` refused in `[squad]`.
    - Read, not driven: the VS Code view and setting, `sq ui`, and a stamp keeping `[display]` byte for byte. Note: `sq list -t role --json` item rows carry the stored `pronouns` key like any attribute (not the resolved default); the docs say so.
- [2026-10-17T03:14:22Z] `manager` Catherine Manager:
  - Done: REV-1089 approved (F5 folded into BUG-1090); Python 2deeb34d, VS Code 1dba72da; full suite 13557 passed, 0 failed; docs committed.
<!-- sq:discussion:end -->
