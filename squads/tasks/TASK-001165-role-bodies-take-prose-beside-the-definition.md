---
id: TASK-1165
sequence_id: 1165
type: task
title: Role bodies take prose beside the definition
status: Done
author: tech-lead
priority: medium
refs:
- MILE-1051:targets
- ADR-880:implements
- ADR-1151:implements
- TASK-1153:depends-on
description: 'ADR-880 §8 and ADR-1151 §11: role body write on every role, empty responsibilities
  render nothing'
subentities:
- local_id: ST1
  title: Admit body writes on every role
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Render no section for empty responsibilities
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Document role body prose and list keys
  status: Done
  assignee: tech-writer
created_at: '2026-10-26T13:05:15Z'
updated_at: '2026-10-26T16:13:11Z'
---
<!-- sq:body -->
## Goal

Every role's body takes authored prose beside its `role_definition` view, and a role with no responsibilities renders no Responsibilities section. `sq role <slug> body` (replace and `--append`) writes on catalog, template and item-defined roles alike, through the same view-tag placement routine as every other document; the definition renders first and the prose follows; the agent reads the prose through `sq role <slug> show` only.

Read before starting a subtask, each body below cites the rule and does not restate it:

- `sq decision 880 show --full --comments`: §6 (re-placement, `--force` meaning), §8 (role bodies), §9 (convergence sweep), and op-pierre's rulings of 2026-10-26 (comments `6f7cbfe`, `a6fcc89`, `9e1671d`).
- `sq decision 1151 show --full --comments`: §11 (list keys through `--file`, an empty list renders nothing).
- `sq decision 776 show --full --comments`: §5 (a role body may hold authored prose beside its tag).

## Parent

No open feature owns roles or views work in 0.17: the closest, FEAT-1054 (prose in roster bodies) and FEAT-976 (system roles and skills), are Done in the 0.16 milestone. As with TASK-1153, this task targets MILE-1051 with no parent.

## What does not change

- System and per-item-type skill bodies still refuse replace and append, `--force` or not.
- The role metadata update gate and the view verbs on a role host (`view disable` refused, `view add` admits only `role_definition`).
- `sq check` gains no rule; prose in place of a role's tag stays unreported (REV-1047 F8 ruling).
- No migration: no stored shape changes, and a tag-only region is the same bytes under `top` and `bottom`.
- The `.claude/agents/<slug>.md` pointer, the `CLAUDE.md`/`AGENTS.md` roster and the `sq role <slug> show --json` card never carry the prose.

## Sequencing

ST1 and ST2 are independent and share no file except possibly test helpers; one python-dev does both, ST1 first. ST3 (tech-writer) runs once ST1 and ST2 are in, against the shipped behaviour. This task depends on TASK-1153, which reshapes `sq role add`/`update` and the role bases that ST2 tests against.

## Gates

`uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the touched test paths plus `tests/meta`, and `sq check` clean. The main loop runs the full suite.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1165 add-subtask "<title>"`; track with `sq task 1165 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Admit body writes on every role

<!-- sq:subtask:ST1:body -->
Admit `sq role <slug> body` (replace and `--append`) on every role, catalog, template and item-defined, through the existing §6 placement routine; skills keep their refusal. Rule: ADR-880 §6 and §8.

## Where

- `src/squads/_services/_items.py::_reject_unwritable_body`: ask `_refuse_classified_roster_write` for skills only (`item.type == ROSTER_SKILL`); a role falls through to the ordinary path. The project-declared roster-type refusal below it is unchanged. Do not change `_refuse_classified_roster_write` itself: the metadata update and the view verbs still ask it for roles and skills.
- The bulk importer's body op (`_services/_import.py`, the pre-pass at the `_reject_unwritable_body` call and the apply pass through `_body_mutate`) inherits the change through the shared predicate; no second check.
- `src/squads/_specs/workflow.toml` `[views.role_definition]`: add `position = "top"`, and rewrite the "Seeded:" comment, which still says the role write path refuses replace and append.
- Docstrings that state the old rule: `set_body`, `_reject_unwritable_body`, `_refuse_classified_roster_write` (its body-write mention), and `_cli/_role.py::_role_empty_body_hint` ("`body` is refused while the role's view is declared"). Keep each to one or two sentences stating the present rule.
- Confirm by test, not by reading, that `pristine_body` makes a tag-only role body count as unwritten for each role kind, so the first replace needs no `--force`.

## Behaviour

- The prose input passes `reject_markers`; the tags are stripped and re-placed; an absent `role_definition` tag is re-inserted enabled at the top; a disabled one keeps its state.
- `--force` is consent to overwrite prose only. A replace over a tag-only body needs none; a replace over written prose is refused by `reject_body_overwrite` without it; an append never needs it.
- `body -m ""` is a replace: over written prose it needs `--force` like any replace, and it leaves the tag alone in the region.
- The convergence sweep (`_converge_body_tag`), `sq sync` and `sq repair` leave a role region holding prose untouched.

## Test table

Write one table-driven test over role kind × write shape at the service level, plus a CLI smoke test for each verb shape on one kind. Role kinds: a catalog role (`tech-lead`), a template role (a developer from `[templates.dev]`), and an item-defined role (`sq role add` with flags). Every row asserts the resulting `sq:body` region byte for byte, and that a refused write leaves the file byte-identical.

| Starting body | Write | Expected |
|---|---|---|
| tag only | replace, no `--force` | admitted; tag first, one blank line, prose |
| tag only | append, no `--force` | admitted; same bytes as the replace row |
| tag + prose | replace, no `--force` | refused, the overwrite message, nothing written |
| tag + prose | replace, `--force` | admitted; prose replaced, tag first |
| tag + prose | append, no `--force` | admitted; new prose after the existing prose |
| tag + prose | `-m ""`, `--force` | admitted; region holds the tag alone |
| tag + prose | `-m ""`, no `--force` | refused, nothing written |
| prose only, tag hand-removed | append | admitted; tag re-inserted enabled at the top, prose kept |
| prose only, tag hand-removed | replace, `--force` | admitted; tag re-inserted enabled at the top |
| prose then tag (tag hand-placed at the bottom) | append | admitted; tag relocated to the top, prose order kept |
| disabled tag + prose (hand edit) | append | admitted; tag stays disabled, at the top |
| tag + prose | replace `--force` carrying the placed tag unchanged (the `show --json` round trip) | admitted; tag kept once, at the top |
| tag + prose | replace carrying an unplaced or differently-stated view tag | refused, naming the view verbs |

Plus:

- The importer's `body` event: the replace, append and force rows above on one role kind give the same bytes as the verb.
- A role not on the roster: `body` still refused with `activate it first`.
- Skills unchanged: replace, append and replace `--force` on `squads`, `greeting`, `sq-memory` and one `sq-<type>` skill are still refused, through the verb and the importer; a custom skill still writes.
- Read surfaces, after writing a distinctive prose line on each role kind: `sq role <slug> show` prints the definition (its H1 first) then the prose; `sq show ROLE-<n> --json` carries the prose and the tag in `body`; the `sq role <slug> show --json` card, the `.claude/agents/<slug>.md` pointer (after `sq sync` and after `sq role <slug> regen`), and the `CLAUDE.md` and `AGENTS.md` managed sections do not contain the prose line.
- `sq sync` and `sq repair` leave the role file byte-identical; `sq check` is clean.

Existing tests asserting the role body refusal (among them `tests/cli/test_content_writes_on_a_generated_role_or_skill_are_refused_cli.py` and `tests/service/test_bulk_import_body_op_shares_the_required_view_refusal.py`) flip their role rows to the admitted behaviour and keep their skill rows. Name new test files by behaviour, no ticket ids.

## Docs and CHANGELOG

Handled in ST3; leave a comment on this subtask listing every user-visible message whose text changed.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-26T15:20:06Z] `python-dev` Elias Python:
  - Done: every role kind takes body replace/append; the tag stays on top (position = "top"); skills still refused. Changed user-visible text: a role body write no longer errors with the "renders through its declared ... tag" refusal (skills keep it); the --file help of `role add` and `role <slug> update`.
  - Tests: service table (3 kinds x 12 write shapes), CLI smoke, importer rows, read surfaces, sync/repair/check; mutation-checked (guard, position, force).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Render no section for empty responsibilities

<!-- sq:subtask:ST2:body -->
A role with an empty responsibilities list renders no Responsibilities section and no placeholder, for every base kind; the `--file` help of `sq role add` and `sq role <slug> update` names the list keys. Rule: ADR-1151 §11.

## Where

- `src/squads/_rendering/templates/views/role_definition.md.j2`: wrap the `## Responsibilities` heading and its list in `{% if source.responsibilities %}`, and remove the `- _TODO: list responsibilities._` branch. The output for a non-empty list stays byte-identical.
- Agreements: checked, no placeholder. The `## Working agreements` section always renders because its fixed text is always present, and an empty agreements list already adds no line; leave it unchanged.
- `src/squads/_cli/_common.py`: `ROLE_DEFINITION_FILE_HELP` (used by `role add --file`) and `ROLE_DELTA_FILE_HELP` (used by `role update --file`) name `responsibilities` and `agreements` as list keys set only through `--file`; the delta help says `["$(*self)", "…"]` appends and `[]` clears. Keep each help to one sentence or two.
- Template bookkeeping: regenerate with `scripts/gen_template_manifest.py` and, if the content store keys the new hash, `scripts/seed_content_store.py`; diff the manifest and confirm only the 0.17.0 entry changed. `tests/meta/test_override_manifest_and_stamp_freshness.py` must pass.
- Goldens: update only the rendered role definitions whose responsibilities list is empty (`tests/goldens/workflow_views.json` and any golden role rendering that shows the placeholder); a golden whose list is non-empty must not change.

## Test table

| Role | Responsibilities | Expected render (`sq role <slug> show`) |
|---|---|---|
| catalog role, bundled list | non-empty | section shown, unchanged bytes |
| catalog role, override sets `responsibilities = []` | empty | no `## Responsibilities` heading, no `_TODO` |
| template role (`[templates.dev]`), list set | non-empty | section shown |
| template role, override empties the list | empty | no heading, no `_TODO` |
| item-defined, `sq role add` with flags only | empty | no heading, no `_TODO` |
| item-defined, `sq role add --file` with a list | non-empty | section shown |
| item-defined, `update --file` with `[]` | empty | section disappears |
| item-defined, `update --file` with `["$(*self)", "x"]` | non-empty | section shown with the appended entry |

Every row also asserts: the Mission and Working agreements sections are present; no line of the rendered definition contains `_TODO`; with an empty agreements list the Working agreements section carries no empty bullet. Assert the heading's absence on the rendered text, not by template inspection.

Help: `sq role add --help` and `sq role <slug> update --help` name both `responsibilities` and `agreements` under `--file` (run through `CliRunner`, with `FORCE_COLOR` unset as the conftest does).

## Docs and CHANGELOG

Handled in ST3.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-26T13:06:21Z] `manager` Catherine Manager:
  - Scope add: apply the same rule to the Mission section — no _TODO placeholder in the generated view; an empty mission renders no section (op-pierre's ADR-880 Q4 ruling: no TODO in the generated view).
- [2026-10-26T15:20:09Z] `python-dev` Elias Python:
  - Done: role_definition view drops the Mission and Responsibilities sections when empty, no _TODO; non-empty bytes unchanged (checked against the old template). --file help names the list keys. Manifest and content store regenerated (only the 0.17.0 entry changed). CHANGELOG has two Changed lines for the writer to rework.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Document role body prose and list keys

<!-- sq:subtask:ST3:body -->
Bring the adopter docs and the 0.17.0 CHANGELOG in line with ST1 and ST2, against the behaviour as shipped. Rules: ADR-880 §8 and ADR-1151 §11.

## docs/roles.md

- The `body` bullet for a role (section "Updating and commenting on roles, skills and operators"): every role takes `body`, replace and `--append`; the tag survives every write; `--force` is consent to overwrite prose and an append never needs it; `body -m "" --force` clears the prose and keeps the tag. Drop the "once the project drops the view" path for roles.
- Where the prose shows: `sq role <slug> show` prints the definition, then the prose. It is not in the agent pointer, the `CLAUDE.md`/`AGENTS.md` roster or the `show --json` card; `sq show ROLE-<n> --json` carries it in `body`. Say what the prose is for (anything the definition has no key for), and that it overrides no definition field.
- The paragraph on role or operator prose and `sq check`: keep the accepted states, reworded for prose beside the tag.
- The `sq role add` / `update --file` passages: `responsibilities` and `agreements` are set only through `--file` (append with `["$(*self)", "…"]`, clear with `[]`), and an empty responsibilities list shows no Responsibilities section.
- The section "What a generated role or skill refuses": roles no longer refuse a body write; skills still do.

## docs/overrides.md

- § "Authoring a role or skill body by hand": a role needs no view drop to take prose any more; rewrite the section around skills, and keep the role case to a pointer to roles.md. Drop the `sq role qa body` / `view disable role_definition` example as the way to write a role body.
- Mention `position = "top"` where `[views.role_definition]` is described, if it is.

## Also check

- `docs/stability.md`, `docs/agents.md`, `README.md`: grep for any sentence that says a role body is refused or must be authored through an override, and fix it.
- The CLI help and messages ST1 lists in its comment.

## CHANGELOG (0.17.0)

One **Changed** entry: a role's body takes authored prose beside its generated definition, on every role, with the `--force`/append/clear rules and where the prose shows; no migration. One **Changed** entry: a role with no responsibilities shows no Responsibilities section instead of a `_TODO` placeholder, and the `--file` help names the list keys. Describe the tool, no ticket ids or build-process wording.

Read each touched paragraph against the shipped CLI on a scratch squad before writing it; do not describe behaviour from this body alone.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-26T15:56:14Z] `python-dev` Elias Python:
  - Operator-visible strings changed, for the writer:
  - 1. 'sq <role|skill|operator> <x> body --help': now says a role takes prose beside its generated definition; a system or per-type skill is refused even with --force; an operator body is never refused for it.
  - 2. Role refusal (view disable, view add of another view, metadata update on a role): the tail 'Drop the view from [selected] to author this directly instead...' is replaced by 'To add prose beside the definition, use sq role <slug> body. To replace the generated definition itself, drop the view from [selected], then clear its leftover tag with ...'. Skill refusal text unchanged. docs/roles.md:704 quotes the old tail.
  - 3. A role body carrying another view's tag: refused with 'Leave it out of the body: sq keeps a placed tag in place.' and no view-verb clause (those verbs are refused on a role).
  - 4. 'sq role add --file' and 'sq role <slug> update --file' help name responsibilities and agreements; update says ["$(*self)", "more"] appends, [] clears.
  - 5. Role body write no longer fails with the 'renders through its declared tag' refusal; skills still do.
  - 6. A role with no responsibilities shows no Responsibilities heading; Mission always renders (mission is required).
  - Docs still stale: F3, docs/migration.md:891-915 and docs/overrides.md:2066-2083 (a role needs 'body -m "" --force' alone to clear old text).
- [2026-10-26T16:11:16Z] `tech-writer` Theo Writer:
  - Done: docs/roles.md (body bullet for every role with --force/append/clear rules and an example; where the prose shows and what it is for; --file sets responsibilities and agreements, [] clears, empty list shows no section; refuses section and its quoted message updated to the shipped text), overrides.md (authoring section around skills, role pointer; role_definition declares position "top"), migration.md (one command for a role), workflow.md, agents.md and internals.md one-line fixes. stability.md and README needed nothing.
  - CHANGELOG 0.17.0: the two Changed entries rewritten for adopters. Every command and message driven on a scratch squad with the dev build. Doc guards and tests/meta pass at -n 4. Not committed. @manager
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T13:05:49Z] `tech-lead` Olivia Lead:
  - Broken down into three subtasks: ST1 admits body writes on every role (python-dev), ST2 drops the empty Responsibilities section and names the list keys in the --file help (python-dev), ST3 updates docs/roles.md, docs/overrides.md and the CHANGELOG (tech-writer). Agreements carry no placeholder, so ST2 leaves them unchanged. No open 0.17 feature fits, so the task targets MILE-1051 with no parent and depends on TASK-1153. Ready for dispatch. @manager
- [2026-10-26T15:20:27Z] `python-dev` Elias Python:
  - ST1 and ST2 done; ST3 (writer) is next. Not committed. I ran each tests/ directory at -n 4, all green.
- [2026-10-26T15:42:33Z] `reviewer` Paul Reviewer:
  - Reviewed 633c735a in REV-1170: behaviour sound, six findings on stale operator-facing text (F1 body --help still says a role body is refused, pinned by a test; F2 the role refusal tail still says drop the view to author the body). @manager @python-dev
- [2026-10-26T16:13:11Z] `manager` Catherine Manager:
  - ST1–ST3 delivered (633c735a, c466f309, c3231f49); REV-1170 Approved, all six findings Verified; full suite 15752 passed; CI green on all three OS. Accepted under the operator's delegation.
<!-- sq:discussion:end -->
