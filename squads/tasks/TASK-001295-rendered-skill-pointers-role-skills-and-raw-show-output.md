---
id: TASK-1295
sequence_id: 1295
type: task
title: Rendered skill pointers, role skills and raw show output
status: InProgress
parent: FEAT-1290
author: tech-lead
assignee: python-dev
refs:
- ADR-1294:implements
description: Python side of ADR-1294, in seven dev rounds
subentities:
- local_id: ST1
  title: show --raw prints a YAML header; --no-header prints the body alone
  status: Done
  assignee: python-dev
  maps_to: US7
- local_id: ST2
  title: A view that fails to render leaves one line naming the command
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST3
  title: The role_playbook view in every role body
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST4
  title: Pointers render their body; one sq-role-<slug> skill per role
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST5
  title: Retire the per-type sq-<type> skills from the code
  status: Done
  assignee: python-dev
  maps_to: US3
- local_id: ST6
  title: Rename to sq-how-to and sq-greeting; trim the base skills
  status: Done
  assignee: python-dev
  maps_to: US3
- local_id: ST7
  title: sq-greeting states the startup steps; CLAUDE.md directs to it
  status: Done
  assignee: python-dev
  maps_to: US6
- local_id: ST8
  title: AGENTS.md compiles role bodies and the shared startup steps
  status: Done
  assignee: python-dev
  maps_to: US8
- local_id: ST9
  title: 0.19 to 0.20 migration retires per-type skills and renames two
  status: Done
  assignee: python-dev
  maps_to: US4
- local_id: ST10
  title: memory list and board list gain --raw
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST11
  title: Raw header lists the panel's rows
  status: Done
  assignee: python-dev
  maps_to: US7
created_at: '2026-11-04T21:46:20Z'
updated_at: '2026-11-05T01:28:59Z'
---
<!-- sq:body -->
## Goal

Implement ADR-1294 in the Python code: `show --raw` with the panel's rows as its header and `--no-header`, the `role_playbook` view, rendered skill pointers with a never-failing `!` line, one `sq-role-<slug>` skill per role, the retirement of the per-type `sq-<type>` skills, the `sq-how-to`/`sq-greeting` names and trims, the main-session startup through `sq-greeting`, the AGENTS.md role bodies, and the 0.19 to 0.20 migration. Docs and CHANGELOG are not in this task (the tech-writer task), nor is the VS Code preview (the typescript-dev task) or the measurement (the qa task).

## Rounds

One fresh python-dev per round, one to two subtasks each. Each round leaves the fast gates green; the main loop runs the full suite and commits a checkpoint before the next round. Brief each round with its subtask IDs only and "stay out of the later subtasks".

| Round | Subtasks | Why this order |
|---|---|---|
| 1 | ST1, ST2 | Every pointer renders with `--raw --no-header`; nothing else can be built or tested before it |
| 2 | ST11, then ST3 | The raw header becomes the panel's rows (op-pierre's ruling of 2026-11-04), then the role body the role skill renders |
| 3 | ST10, then ST4 | Plain memory and board lists, then pointer format, role skill, agent pointer, preload list |
| 4 | ST5 | Rip out the per-type skills once nothing preloads them |
| 5 | ST6 | Renames and trims of the base skills and the role definition text |
| 6 | ST7, ST8 | `sq-greeting`, the managed `CLAUDE.md` section, and AGENTS.md share one startup partial |
| 7 | ST9 | The migration and `sq init`, over the finished shape |

ST11 replaces ST1's YAML header; ST10 needs ST1 and ST11 (the same raw contract); ST4 needs ST1, ST3 and ST10; ST5 needs ST4; ST7 needs ST6; ST9 needs everything before it.

## Fast gates (every round)

`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`, then the tests the change touches, selected per board notice 15: grep the changed template paths, view names, constants and DTO fields across `tests/`, plus the floor `tests/meta tests/cli` for any change under `_specs/`, `_rendering/templates/` or `_cli/`. Use `-n 4`. No full suite, no commit: the main loop owns both. `~/.local/bin/sq check` stays clean.

## Tests

CLI surface tests per ADR-1172 (`@pytest.mark.covers`), one case per behaviour plus its boundary refusals, no tables or cross products. Expected new tests per subtask are stated in each subtask; about 45 in all. Break each new test once by hand (revert the line it guards, watch it go red) and say so in the handback (board notice 4).

## Generated and frozen files to regenerate

- `src/squads/_rendering/templates_manifest.json` and `content_store.json`: `python scripts/gen_template_manifest.py` after every round that adds, removes or edits a template (rounds 2 to 6; the version is already 0.20.0, so only the 0.20.0 entry moves). Update the template count in that script's docstring when templates are added or removed. Guard: `tests/meta/test_override_manifest_and_stamp_freshness.py`.
- `src/squads/_rendering/templates/claude/claude_section.md.j2`: the source of every squad's managed `CLAUDE.md` section, this repository's included. Edit it, never the rendered `CLAUDE.md`.
- `tests/cli/_bundled_documents.py`: the frozen `sq workflow views --json` document (ST3 adds `role_playbook`, ST5 removes `item_skill`, ST7 may change `greeting_skill`'s source) and the frozen `sq migrate help --json` document (ST9 changes the 0.20.0 summary and manual).
- There is no managed-section golden file in the rebuilt suite; the section is held by `tests/cli/test_sync.py`, `test_init.py` and `test_adopt.py` assertions, which ST6 and ST7 update.
- This repository's own `CLAUDE.md`, `.claude/` and `squads/` change only when the main loop migrates this squad with the finished build (board notice 17); no round runs `sq sync` or `sq migrate up` on it.

## Not in scope

`sq <type> <n> comment <hash> show --raw` keeps its current output. Docs, CHANGELOG, the VS Code client.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1295 add-subtask "<title>"`; track with `sq task 1295 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — show --raw prints a YAML header; --no-header prints the body alone

<!-- sq:subtask:ST1:body -->
Implements ADR-1294 §1, "Raw output". Story US7.

## Behaviour

- `--raw` on every `show`: `sq <type> <n> show`, `sq show <id>`, `sq role <slug> show`, `sq skill <slug> show`, `sq operator <slug> show`. Output is plain markdown: no panel, no ANSI, no Rich markup, no wrapping, no emoji badge glyph, whatever `FORCE_COLOR`, `NO_COLOR`, `TERM`, `COLUMNS` or the tty say, in local mode and through the daemon.
- The header is the item's frontmatter as a YAML front-matter block (`---` / YAML / `---`), keys in stored order, without `subentities`. It replaces `_raw_metadata` in `_cli/_render/_items.py`. The `# <id> — <title>` heading follows it (see Heading below).
- `--full` and `--comments` render raw too; sub-entity state is plain text (status and field values by label, no badge glyph).
- `--no-header` is valid only with `--raw` and prints the body alone, every view tag expanded. Without `--raw` it is refused with one line and a non-zero exit.
- The render is built whole, then written once: nothing on stdout unless it all succeeded. On failure (item, squad or schema not resolved) exit non-zero with sq's one-line error on stderr.
- `--body` is not added.

## Files

- `_cli/_common.py`: `raw_option` help text; a `no_header_option`; the refusal of `--no-header` without `--raw` as a parse-time `SquadsError`.
- `_cli/_items.py`, `_cli/_main.py`, `_cli/_role.py`, `_cli/_skill.py`, `_cli/_operator.py`: the option on each `show`.
- `_cli/_render/_items.py`, `_cli/_render/_roster.py`: one raw renderer for items and roster entries (no panel on role, skill or operator).
- `_api/_dto/`: the frontmatter the header prints. Project it in `_services/_item_dto.py` (or the roster DTO module) as a JSON-native mapping on the show DTOs; the renderer only serialises it. Renderers stay off `_workflow`/`_config`/`_services` (meta guard).
- The shim's option tables, if `--no-header` needs an entry there (the `tests/meta` guard on the shim tables says).

## Heading

Under `--raw` the `# <id> — <title>` heading stays after the YAML block: header, blank line, heading, blank line, body. `--no-header` drops both (ADR-1294 amendment; manager's ruling on this task).

## Tests (about 8, `tests/cli/test_show.py`, `test_role.py`, `test_skill.py`, `test_operator.py`)

- item `show --raw`: the header parses as YAML, equals the stored frontmatter without `subentities`; no ESC byte with `FORCE_COLOR=3` and `COLUMNS=40` set (a long line is not wrapped).
- `show --raw --no-header` prints exactly the body with a view tag expanded (a milestone with its roll-up).
- `show --raw --full --comments`: sub-entity state as plain text, no badge glyph.
- `--no-header` without `--raw`: one-line refusal, non-zero exit, empty stdout.
- an unknown item under `--raw`: non-zero exit, empty stdout, one stderr line.
- `role`, `skill` and `operator show --raw --no-header`: body only, no panel (one case each, or one parametrised over the three roster types if the covers marker allows it).
- one case through the daemon's command endpoint: no ESC byte with `FORCE_COLOR=3`.

Covers markers: (`show`, `--raw`), (`show`, `--no-header`), and the same pair on `role show`, `skill show`, `operator show` and the per-type `show`.

## Not in this subtask

`--raw` on `sq memory <slug> list` and `sq board list` is ST10, in round 3.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — A view that fails to render leaves one line naming the command

<!-- sq:subtask:ST2:body -->
Implements ADR-1294 §1, "Partial failure stays inside the text". Story US1.

## Behaviour

- A view whose source, transform or template fails at read time renders, in place of its tag, one line saying the view could not be rendered and naming the command that shows why: `sq workflow view <name> <id>`. The rest of the body renders, and the command exits 0.
- One behaviour for every body read (`show` styled and raw, `--json`'s body, the AGENTS.md compile later): the line replaces today's literal tag. The per-view warning on stderr stays.
- A transform failure, which raises today, takes the same path.
- An undeclared or inapplicable tag (an override dropped the view, a source that does not apply to the host) stays as it is today: that is a squad's configuration, not a failure.
- Only a failure to resolve the item, the squad or the schema fails the command.

## Files

- `_view_tags.py` (`expand_view_tags`, the `failed` handling and the transform call).
- `_views.py` only if the line's wording belongs beside `render_resolved_source_or_raise`.
- The line's text in one place.

## Tests (about 2)

- a body holding a view whose template override raises: `show --raw --no-header` exits 0, prints the line naming `sq workflow view <name> <id>` and the prose around it.
- a view whose transform raises: same, through `show` (styled) to hold the one-behaviour rule.

Any existing test that pins the literal-tag-on-failure behaviour changes with it; grep `shown as written` and `its tag is shown` across `tests/`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — The role_playbook view in every role body

<!-- sq:subtask:ST3:body -->
Implements ADR-1294 §2, "The role body" and "Backfill". Story US2.

## Behaviour

- A new bundled view, `role_playbook`, seeded in every role body after `role_definition`. For each item type in the role's playbook, in the order `item_types_for_role` gives: the type's label as a heading, its overview, its lifecycle line, and this role's own Enter, Do, Hand off and Watch for section, with live-roster substitution (`live_roster_text`, capability tokens). A guide addressed to a capability (`*<name>`) the role holds is its own section. No other role's section, no Commands block. A role whose playbook names no type renders nothing.
- `sq role <slug> show` (styled and `--raw`) prints the definition, then the playbook sections. Never memory or board.
- An adopter's prose in the role body stays where it is, beside the tags; `sq role <slug> body` replace and append keep both tags in place.
- `sq role <slug> view disable role_playbook` turns it off for one role, through the existing view engine.
- `sq repair`'s body-tag sweep places `role_playbook` on a role body that lacks it entirely, after `role_definition`; a disabled tag is present and left alone.
- `sq check`'s existing rule for a seeded view a host has lost covers `role_playbook` with no new rule.

## Design

Declare `[views.role_playbook]` in `_specs/workflow.toml` with `source = { kind = "playbook" }`; for a role host the source resolves no lane (`_playbook_subject` gives the role type) but carries the roster and the merged playbook, which is all the template needs. A Jinja filter in `_rendering/_engine.py` (backed by a function in `_interactions/_role_guidance.py`) turns the host role, roster, playbook and spec into the ordered sections, reusing `item_types_for_role`, `addresses` and `live_roster_text`. No new source kind. If this shape does not hold, stop and say why before adding a source kind (that is a spec-grammar change).

## Files

- `_specs/workflow.toml` (`[views.role_playbook]`, its comment block beside `role_definition`).
- `_rendering/templates/views/role_playbook.md.j2` (new).
- `_rendering/templates/agents/role.md.j2` (seed the second tag).
- `_views.py`: `roster_body_view_name` returns one name today; a role is seeded with two. Make the role case give both (`seeded_view_names`, `ROLE_DEFINITION_VIEW_NAME` beside a `ROLE_PLAYBOOK_VIEW_NAME`), and keep every consumer (`_services/_roster_dto.py`, `_services/_validators.py`, `ServiceCore._create_core`'s reassertion, `MaintenanceMixin._repair_body_tag`) agreeing.
- `_interactions/_role_guidance.py`, `_rendering/_engine.py` (the filter).

## Tests (about 5, `tests/cli/test_role.py`, `test_repair.py`)

- `role tech-lead show --raw --no-header` holds its own section for the task type and no other role's section for that type, and its definition first.
- a role with no playbook type (a project role added with `sq role add`) shows its definition only.
- `role <slug> view disable role_playbook` hides the sections; `repair` leaves the disabled tag.
- `repair` places the tag on a role body that lacks it, after `role_definition`.
- an adopter's prose written with `role <slug> body` survives and sits beside the rendered sections.

Regenerate the template manifest; add `role_playbook` to the frozen views document in `tests/cli/_bundled_documents.py`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Pointers render their body; one sq-role-<slug> skill per role

<!-- sq:subtask:ST4:body -->
Implements ADR-1294 §1 (the pointer, the command, the grant, invariant 7, drift), §2 (name, no skill item, what it renders, lifecycle, collisions) and §3. Story US2.

## Behaviour

- **Skill pointer** (`claude/pointer_skill.md.j2`), exactly the §1 shape: a YAML comment on the frontmatter's first line stating `sq sync` regenerates the file; `name`, `description`, `user-invocable: false` as ADR-983 resolves it, `allowed-tools: Bash(sq skill <slug> show --raw --no-header)`; one body line `` !`sq skill <slug> show --raw --no-header || echo 'squads could not render the <slug> skill; run: sq skill <slug> show'` ``. No guidance lines, no HTML comment.
- **Role skill pointer**, new, `.claude/skills/sq-role-<slug>/SKILL.md`, one per live role, `user-invocable: false`, model invocation left on. Three `!` lines, each with its own `|| echo` fallback naming its command: `sq role <slug> show --raw --no-header`, `sq memory <slug> list --raw`, `sq board list --raw` (the last two from ST10). `allowed-tools` names exactly those three, as a YAML list (the form the architect drove on the host). No `SKILL` item behind it.
- **Agent pointer** (`claude/pointer_agent.md.j2`): the YAML comment first line; identity line; the two startup commands `sq mine <slug>` and `sq inbox <slug>` (`_STARTUP_COMMAND_TEMPLATES`); no definition, memory or board command; no guidance lines. Preload list: `sq-role-<slug>`, then the base how-to skill, then `sq-memory`, then any custom skill a `preload` ref adds. No greeting skill, no per-type skill.
- **Echo text**: single-quoted ASCII with no `$`, backtick, `!`, glob character or brace; a slug is `[a-z0-9-]`. Hold it with a check in code (a slug outside that set is refused before render), not only by convention.
- **Lifecycle**: `generate_role_entry` writes the agent pointer and the role skill pointer; `remove_artifacts` on a role removes both; reactivation writes both. `managed_entry_paths` declares the role skill pointer of every live role; `candidate_orphans` reports a `.claude/skills/sq-role-<slug>/` whose role is not live and never reports a live role's.
- **Drift**: `sq check` compares the role skill pointer with a fresh render, as it does the agent pointer. The backend ABC gains the render question for it (or the role entry render returns both files); the AGENTS.md backend answers `None`.
- **Collisions**: `sq skill add sq-role-<s>` is refused when `<s>` is a role item's slug, any status; `sq role add` and `sq role activate` are refused when `sq-role-<slug>` is an existing skill item. One-line `SquadsError` each.
- `skills_for_role` (`_interactions/_role_guidance.py`) returns the new preload list; `_services/_roster_projection.py`'s `resolve_role_skills` keeps adding `preload`-ref skills after it.

## Files

`_backends/_claude_code/_backend.py`, `_backends/_base.py`, `_backends/_agents_md/_backend.py` (the `None` answer), `_rendering/templates/claude/pointer_skill.md.j2`, `pointer_agent.md.j2`, a new `pointer_role_skill.md.j2` (or one skill template taking a list of commands, whichever stays simpler), `_interactions/_role_guidance.py`, `_interactions/_skills.py` (the role skill name function and its slug check), `_services/_roster_projection.py`, `_services/_validators.py` (drift), the roster create/activate services for the collisions, `_services/_config_integrity.py` (a preload entry `sq-role-<slug>` has no skill item and is never reported missing).


## Tests (about 7, `tests/cli/test_sync.py`, `test_role.py`, `test_skill.py`, `test_check.py`)

- after `sync`, a skill pointer is exactly the §1 shape (frontmatter parses as YAML with the comment line first; one `!` line; `allowed-tools` names only its command).
- the role skill pointer exists per live role with the three lines and the three-entry grant as a YAML list; the agent pointer's preload list starts with it and names no per-type or greeting skill; the agent pointer names `sq mine` and `sq inbox` only.
- a `!` line run under `bash -c` and `zsh -c` with `sq` absent from `PATH` exits 0 and prints the echo line (skip zsh when not installed).
- `role <slug> retire` removes both pointers; `role <slug> activate` writes both.
- `check` reports a hand-edited role skill pointer as drifted and is clean after `sync`.
- `skill add sq-role-tech-lead` refused; `role add`/`activate` of a slug whose `sq-role-<slug>` skill exists refused.

Update `tests/meta` guards that pin the pointer text or the startup command set (grep `_STARTUP_COMMAND_TEMPLATES`, `Load your full role definition`, `This pointer file itself` across `tests/`). Regenerate the template manifest.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Retire the per-type sq-<type> skills from the code

<!-- sq:subtask:ST5:body -->
Implements ADR-1294's consequence "The `item_skill` view, the per-type writer, `ITEM_SKILL_OPERATOR_INVOCABLE` and the `custom_item_skill_*` helpers retire", and ADR-983 §2 as narrowed. Story US3.

## Behaviour

- `sq init` and `sq sync` write no `sq-<type>` skill, pointer or body, for a bundled type or a project type alike. The `item_skill` view and its template are gone from the bundled spec.
- A squad that still holds per-type skill items (one not yet migrated) is the migration's business (ST9); this subtask removes the code that writes and checks them and must not leave a path that crashes on one. A leftover `sq-<type>` skill item reads as an ordinary project skill.
- No delivered text names an `sq-<type>` skill: grep the templates and the bundled playbook text.

## Remove

- `_backends/_claude_code/_backend.py`: `_write_item_skills` and its call.
- `_interactions/_skills.py`: `item_skill_name`, `custom_item_skill_name`, `custom_item_skill_description`, `custom_item_skill_commands`, `ITEM_SKILL_OPERATOR_INVOCABLE`, `item_type_for_skill_slug`, and the per-type arms of `skill_description`, `is_system_skill`, `custom_skill_slugs`, `active_skill_slugs`, `orphaned_skill_item_type`, `declared_operator_invocable`. Keep what the three base skills need.
- `_views.py`: `ITEM_SKILL_VIEW_NAME`, the per-type arm of `roster_body_view_name` and `_playbook_subject`'s skill inversion, the per-type arm of `skill_authoring_surface`.
- `_specs/workflow.toml`: `[views.item_skill]`. `_rendering/templates/views/item_skill.md.j2`. `_rendering/_engine.py`: filters only it used (`item_skill_role_sections` stays if `role_playbook` uses it, `custom_item_skill_commands` goes).
- `_services/_maintenance.py`: `seed_custom_skills` and the per-type arms of the seeding and `_repair_body_tag`; `_services/_roster_dto.py`, `_services/_validators.py` (the per-type skill body check near the `ITEM_SKILL_VIEW_NAME` use), `_services/_config_integrity.py` (the type-implied dependency kind of `preloaded_skill`), `_services/_retirement.py`.
- `_interactions/__init__.py` re-exports that lose their last `src` user (the import-edge meta guard holds the init to the exact surface).

Use `uv run vulture` once at the end to catch a helper left with no caller.

## Tests (about 2 new, many removed or changed)

- `init` writes no `sq-<type>` pointer or skill item, for a bundled and a project type.
- `check` stays clean on a fresh squad with a project type (no type-implied preload finding).

Remove or rewrite the breach test of any `sq check` rule this deletes (`tests/check/`, the `breaches` marker guard fails on a stale one); update `tests/meta/test_every_skill_seeding_entry_point_seeds_bundled_and_custom.py`, `test_every_cli_command_is_named_in_agent_guidance.py` (its body set loses the per-type bodies: a command named only in a lane's Commands block may now be named nowhere; report each such command in the handback rather than widening the guard's body set on your own), `test_generated_agent_text_names_no_bundled_vocabulary.py`, and the frozen views document in `tests/cli/_bundled_documents.py`. Regenerate the template manifest and its docstring count.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Rename to sq-how-to and sq-greeting; trim the base skills

<!-- sq:subtask:ST6:body -->
Implements ADR-1294 §5 and §2 "Role definition text". Story US3.

## Behaviour

- The base skills are named `sq-how-to` (formerly `squads`) and `sq-greeting` (formerly `greeting`); `sq-memory` keeps its name. `SQUADS_SKILL` and `GREETING_SKILL` in `_interactions/_skills.py` take the new slugs; `ensure_scaffold` creates `.claude/skills/sq-how-to`; descriptions say what each is for, and `sq-greeting`'s says it is for the main session only. The view names `squads_skill` and `greeting_skill` do not change.
- `role_definition.md.j2` loses the line sending the agent to its `sq-<type>` skill and the "Live with the operator" instruction to follow `greeting`; it names no command for reading the agent's own role; its references to the `squads` skill name `sq-how-to`.
- Every delivered mention of the `squads` skill says `sq-how-to`: `claude_section.md.j2` (opening paragraph, orchestration loop), `role_definition.md.j2`, the bundled playbook text, `workflow.md.j2`.
- The trims below, under the rule: a section stays only when every agent needs it on every run and no other startup text (the role skill, the managed `CLAUDE.md` section, `sq-greeting`, `sq-memory`) carries it. `sq-how-to` ends with one line per moved topic: the `sq docs` name and when to read it.

## Proposed trims (the reviewer checks them against US3)

`sq-how-to` (`views/squads_skill.md.j2`):
- Drop the opening paragraph: the managed `CLAUDE.md` section opens with the same text.
- Golden rules: keep, minus the `sq-<type>` bullet and the "Need detail? `sq docs`" bullet (the closing topic lines replace it).
- Drop the working-language include: the `CLAUDE.md` section carries "Working language".
- Keep the comment-scoping bullet and its table (every agent comments, and the role definition points to it); move the rest of "Working directly with the operator" behind `sq docs agents` (the role definition's "Live with the operator" keeps the principle). Drop the operators paragraph: the `CLAUDE.md` "Operators" section carries it.
- Move "Finding things across the board" behind `sq docs recipes` (its "Prioritize, find, and focus" recipe).
- Drop the `workflow.md.j2` include (team workflow, aliases, lifecycles): the `CLAUDE.md` "Team workflow" section and the role skill's lifecycle lines carry what an agent needs; the rest is `sq workflow` and `sq docs workflow`.
- Keep "Common commands".
- Closing lines, one per moved topic: `sq docs agents` (working live with the operator), `sq docs recipes` (searching the board, prioritising), `sq docs workflow` (lifecycles, aliases, sub-entities), `sq workflow` (this squad's own vocabulary).

`sq-memory` (`views/memory_skill.md.j2`):
- Drop "Check it at the start of a run" and the board's "Run `sq board list` at the start of a run" sentence: the role skill renders both and `sq-greeting` runs them.
- Fold "The summary-vs-body split" into the command surface as two lines.
- Keep one fact per memory, pruning, the memory-vs-board boundary, the board notice guidance and both command blocks.

`sq-greeting` is rewritten whole in ST7.

Moving a topic does not write docs: the named docs already cover these topics; the tech-writer task checks each closing line against its doc and fills a gap.

## Files

`_interactions/_skills.py`, `_backends/_claude_code/_backend.py` (`ensure_scaffold`), `_rendering/templates/views/squads_skill.md.j2`, `memory_skill.md.j2`, `role_definition.md.j2`, `claude/claude_section.md.j2`, `workflow.md.j2` if it names the skill, `_specs/playbook.toml` text, every `src` mention of the old slugs (grep `"squads"` and `"greeting"` as slugs, not the package name).

## Tests (about 3)

- `init` creates skills `sq-how-to`, `sq-greeting`, `sq-memory` and no `squads` or `greeting` skill or pointer.
- `skill sq-how-to show --raw --no-header` names no `sq-<type>` skill and ends with the `sq docs` topic lines.
- `role <slug> show --raw --no-header` names no `sq-<type>` skill, no `greeting` skill and no `sq role <slug> show`.

Update the fixtures and meta guards that name `squads`/`greeting` as skill slugs (`tests/meta/test_the_squad_fixtures_hold_what_they_promise.py`, `test_every_cli_command_is_named_in_agent_guidance.py`, the managed-section assertions in `tests/cli/test_sync.py`, `test_init.py`, `test_adopt.py`). Regenerate the template manifest.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — sq-greeting states the startup steps; CLAUDE.md directs to it

<!-- sq:subtask:ST7:body -->
Implements ADR-1294 §4. Story US6.

## Behaviour

- **`CLAUDE.md` section** (`claude/claude_section.md.j2`): one mandatory instruction, placed early: before its first reply the main session invokes `sq-greeting` and completes every step it gives; a subagent never does. The "Impersonation on greeting" and "Start of a run" parts and the greeting paragraph under "Operators" leave the section. Roster, operators list, working language, orchestration loop (naming `sq-how-to`), team workflow and working-with-squads stay.
- **`sq-greeting` body** (`views/greeting_skill.md.j2`), the startup sequence as numbered, imperative, mandatory steps, in this order:
  1. Identify the operator: the logged-in user or `git config user.name`, checked against `sq list -t operator --all`; registered, retired and not-registered cases as today; register only on a yes; ask when unsure, never guess.
  2. Adopt the role: the agent the operator greets by name or function, matched to a live role's slug; otherwise the squad's default role, named with full name and slug; a squad with no default gets one line naming `sq role set-default`, then asks which role to adopt. A greeting that matches no live role means asking. A human introducing themselves is the operator, not a role.
  3. Read the role: `sq role <slug> show --raw --no-header`.
  4. `sq mine <slug>`. 5. `sq inbox <slug>`. 6. `sq board list --raw`.
  7. `sq memory <slug> list --raw`, then `sq memory <slug> show <entry>` for each entry the request touches.
  8. Greet, with today's tone guidance (match register, say who you are, one short read of the project), trimmed of anything the steps now cover ("Get your bearings" goes).
- The steps are text; the render runs none of them. The render reads only the skill's own body and the default role, so it is the same for every session of a squad. `sq-greeting` takes no argument.
- Steps 1 to 7 come from one template partial (for example `templates/startup_steps.md.j2`) that ST8's AGENTS.md section includes too, so the two hosts state one sequence.
- **`settings.json`** (`claude/settings.json.j2`): `Skill(sq-greeting)` and `Skill(sq-how-to)` join the allow rules `_merge_settings` merges beside `Bash(sq:*)`.

## Design

`greeting_skill` is a `self` source today and needs the default role. Switch its declaration to the `playbook` kind (the shape `squads_skill` already has: the source carries the live roster), and resolve the default from `RoleView.is_default` in the template. No new context variable outside the view engine.

## Files

`_rendering/templates/claude/claude_section.md.j2`, `views/greeting_skill.md.j2`, the new partial, `claude/settings.json.j2`, `_specs/workflow.toml` (`[views.greeting_skill]` source and comment), `_backends/_claude_code/_backend.py` if the section's context changes.

## Tests (about 4)

- `sync`: the managed section holds the one `sq-greeting` instruction and no "Impersonation on greeting" or "Start of a run" heading.
- `skill sq-greeting show --raw --no-header`: the eight steps in order, steps 3, 6 and 7 with `--raw`, the default role's full name and slug; after `role set-default` to another role, that role.
- a squad with no default role: the step names `sq role set-default`.
- `sync` merges `Skill(sq-greeting)` and `Skill(sq-how-to)` into an existing `settings.json` and keeps the adopter's own rules.

Update the frozen views document if `greeting_skill`'s source changes. Regenerate the template manifest.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — AGENTS.md compiles role bodies and the shared startup steps

<!-- sq:subtask:ST8:body -->
Implements ADR-1294 §7. Story US8.

## Behaviour

- The AGENTS.md "Role definitions" section compiles each live role's body exactly as `sq role <slug> show --raw --no-header` prints it: definition, playbook sections and the squad's own prose. It replaces today's mission/responsibilities summary.
- The memory index and the board are not compiled.
- The "Start of a run" part states the startup steps from the partial ST7 created, with the same commands (`sq role <slug> show --raw --no-header`, `sq mine`, `sq inbox`, `sq board list --raw`, `sq memory <slug> list --raw`) and the same imperative, mandatory wording. AGENTS.md has no skill to direct a session to, so the steps stay inline.
- A role body that fails to render compiles as ST2's one line, and the file is still written.

## Design

Backends do not import `_services` or `_index`. The service layer renders each live role's body (the same expansion `role show` uses) and hands the backend a slug-to-text mapping on `BackendContext`, filled where `refresh_managed` fills `skill_paths`. The Claude Code backend ignores it.

## Files

`_backends/_agents_md/_backend.py`, `_backends/_agents_md/_managed.py`, `_backends/_base.py` (`BackendContext`), `_rendering/templates/agents_md/agents_section.md.j2`, `_services/_roster_projection.py`.

## Tests (about 2)

- `sync` with the AGENTS.md backend: each role's section equals that role's `role <slug> show --raw --no-header` output, an adopter's prose included; no memory or board text.
- the AGENTS.md "Start of a run" steps and the `sq-greeting` steps 1 to 7 are the same text (one rendered from the shared partial, compared).

Regenerate the template manifest.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — 0.19 to 0.20 migration retires per-type skills and renames two

<!-- sq:subtask:ST9:body -->
Implements ADR-1294 §6. Story US4.

## Behaviour

In the unreleased `_migrations/_v0_19_to_v0_20.py` runner (board notice 17), after its existing scan:

- **Plan before writing.** Collect every per-type skill item (identify it as 0.19 recorded it, not by the run's spec, so a dropped type's stale skill is included: a skill item other than `squads`, `greeting` and `sq-memory` that carries the `item_skill` view tag or whose slug is `sq-<t>` with the author equal to the slug; confirm against `tests/fixtures/corpus/v0_19`), every skill item named `sq-role-<s>` for a role `<s>`, and every skill item named `sq-greeting` or `sq-how-to`.
- **Refuse the whole run**, listing each skill and what it holds, writing nothing, when: a per-type skill carries prose in its `sq:body` beyond its view tag, a discussion comment, or a ref from another item; an `sq-role-<s>` skill item exists; a project skill already holds `sq-greeting` or `sq-how-to`. Fold these into the runner's existing `EntriesRefused` list so one run reports every case.
- **Then**: rename the `greeting` skill to `sq-greeting` and `squads` to `sq-how-to` (slug, title, file name; item ID and refs unchanged; precedent: the 0.8 to 0.10 runner's `sq-memory` rename); remove each per-type skill item; place the `role_playbook` tag on every role body (if `sq migrate up`'s closing repair already does it through ST3's backfill, rely on that and test it, do not write it twice).
- **Backend refresh**, as `sq sync`: remove the per-type, `greeting` and `squads` pointer directories from `.claude/skills/` (only those names; never a project skill's directory), write the `sq-greeting`, `sq-how-to` and role skill pointers, rewrite every agent pointer, the managed `CLAUDE.md` section and the `settings.json` allow rules. Check whether `migrate up` already ends with this refresh; today's `sync` only reports orphans, so the removal is new code.
- **`MANUAL`**: move each listed skill's content first (into the role body of the role it addressed, a project skill, or the playbook override) and re-point refs; rename a project skill holding `sq-greeting` or `sq-how-to`; a stored `operator_invocable` choice on a retired skill is not carried over; the squad's own prose naming `greeting` or `squads` is not rewritten; commit `.claude/` after the run. `SUMMARY` updated to match.
- After the adopter moves that content and runs `sq migrate up` again, it completes.
- **`sq init`**: creates `sq-how-to`, `sq-greeting`, `sq-memory`, seeds every role body with `role_definition` and `role_playbook`, writes one role skill pointer per activated role and no per-type skill (most of this lands in earlier rounds; this subtask holds the test).

The runner uses the run's resolved vocabulary and imports no vocabulary-folded primitive (two `tests/meta` guards). It never raises a refused command (another guard).

This repository's own squad was checked on 2026-11-04 against the hard stops: its nine per-type skills hold only their view tag, no comment and no inbound ref (TASK-313 mentions one file name in prose, not a ref), and no skill holds `sq-greeting`, `sq-how-to` or `sq-role-*`.

## Files

`_migrations/_v0_19_to_v0_20.py`, the service code the refresh reuses, `tests/fixtures/corpus/v0_19` (add a per-type skill with prose only inside a test's copy, never in the shared fixture unless every consumer agrees).

## Tests (about 8, `tests/cli/test_migrate.py`, `test_init.py`)

- one refusal per hard stop (body prose, comment, inbound ref, `sq-role-<s>` skill item, project `sq-greeting`/`sq-how-to`): names the skill, exit non-zero, files and schema stamp unchanged. Five cases, or fewer if one run listing several cases holds the "lists every case" rule.
- a clean 0.19 squad: renamed skills keep their IDs and inbound refs, per-type items and pointers gone, role bodies carry `role_playbook`, role skill pointers written, `settings.json` holds both `Skill(...)` rules.
- a refused run that is fixed by hand completes on the second run.
- `init`: the three skills, both role-body tags, one role skill pointer per activated role, no per-type skill.

Update the frozen `sq migrate help --json` document in `tests/cli/_bundled_documents.py` (0.20.0 summary and manual).
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — memory list and board list gain --raw

<!-- sq:subtask:ST10:body -->
Implements ADR-1294's amendment of 2026-11-04 (§1, §2, §4): `sq memory <slug> list` and `sq board list` gain `--raw` under the `show --raw` contract. Story US2. Round 3, before ST4, which renders both in the role skill.

## Behaviour

- `sq memory <slug> list --raw`: one markdown bullet per entry, its slug and its summary (for example ``- `slug`: summary``), in the order `list` gives today. An empty index prints one plain line saying the role has no memory, and exits 0.
- `sq board list --raw`: one numbered item per current notice, its ordinal matching `sq board clear <n>`, with the notice's full content, its author, its timestamp and its expiry when it has one. No notices prints one plain line saying so, and exits 0.
- Same contract as ST1's `show --raw`: plain markdown, no ANSI, no Rich markup, no wrapping, no glyph, whatever `FORCE_COLOR`, `NO_COLOR`, `TERM`, `COLUMNS` or the tty say, in local mode and through the daemon; the whole render is built and written once; on failure (unknown role, squad or schema not resolved) nothing on stdout, non-zero exit, one line on stderr.
- Without `--raw`, both commands print what they print today.

## Files

`_cli/_memory.py` (`list_memories`), `_cli/_board.py` (`list_notices`), `_cli/_render/_memory.py`, `_cli/_render/_board.py`, reusing ST1's `raw_option` and its single-write helper. If a field the raw board line needs (author, timestamp, expiry) is missing from the `NoticeList` DTO, add it in `_api/_dto/` and project it in the service; renderers stay off `_workflow`/`_config`/`_services`.

## Tests (about 4, `tests/cli/test_memory.py`, `tests/cli/test_board.py`)

- `memory <slug> list --raw` with `FORCE_COLOR=3` and `COLUMNS=40`: one bullet per entry, no ESC byte, a long summary not wrapped.
- `memory <slug> list --raw` for a role with no memory: the one line, exit 0.
- `board list --raw`: numbered items with content, author, timestamp and expiry, no ESC byte; ordinals match `board clear`.
- `board list --raw` with no notice: the one line, exit 0.

Covers markers: (`memory list`, `--raw`), (`board list`, `--raw`).
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->

<!-- sq:subtask:ST11 -->
### ST11 — Raw header lists the panel's rows

<!-- sq:subtask:ST11:body -->
Implements ADR-1294 §1, "Raw output", as amended by op-pierre's ruling of 2026-11-04 (comment c30d364 on ADR-1294), which replaces the YAML header. Story US7. Round 2, before ST3.

Supersedes the header part of ST1: ST1 stays Done for `--raw`, `--no-header`, the single write and the refusals; its YAML header, the `frontmatter` field and `header_fields` are replaced here.

## Behaviour

- Under `--raw` the header is the rows the styled `show` panel prints, in the panel's order and with its labels, as a markdown list: one `- **<label>:** <value>` line per row.
- Values are plain text: a badge prints its value with no glyph (the `badges` mapping's value, not `display.badges[...].badge`), refs print as `ID (kind)` (`ID` alone with no kind), lists comma-joined as the panel joins them, no Rich markup.
- The session rows are left out: the author row's `@ <session>` suffix and the `last-modified session` row.
- Items: the `# <id> — <title>` heading comes first and carries the panel's ID row and title row; the list follows without them and adds a `- **type:** <type>` row first, so the type is not lost. Shape: heading, blank line, list, blank line, body (the shape before the YAML header, and the one op-pierre approved).
- Role, skill and operator shows have no H1 under `--raw`. The panel's unlabelled first row (a role's name and slug, a skill's `ID title`, an operator's name) prints as a plain first bullet (`- <text>`, no bold label), then the labelled rows. Shape: list, blank line, body.
- `--no-header` still prints the body alone. `--full` and `--comments` stay plain markdown as ST1 left them.
- A role with no active item prints its rows, then the activate line ST1 prints; with `--no-header`, the line alone.

## Design

One function per show builds the labelled rows from the DTO, as `(label, value)` pairs; the styled panel formats them with `[bold]` and `e()`, and `--raw` writes them as bullets. Where the panel shows a styled value the raw form cannot (a badge glyph, the session suffix), the builder takes a flag or returns both forms; pick whichever keeps one list of rows and one place deciding their order. The rows cannot drift because there is one list.

- Items: `_panel_rows` in `_cli/_render/_items.py` becomes the builder; `render_show` and `_render_raw` both call it.
- Roster: the rows `render_role_show`, `render_skill_show` and `render_operator_show` in `_cli/_render/_roster.py` build inline today; each becomes a builder both paths use, under the same rule (labels as the panel, plain values, no session rows, the unlabelled first row as a plain bullet).

## Remove

- The `frontmatter` field on `ItemShow`, `RoleShow`, `SkillShow`, `OperatorShow` (`_api/_dto/`), its projections in `_services/_item_ops.py` and `_services/_roster_ops.py`, and `header_fields` in `_services/_item_dto.py`.
- `"frontmatter"` from `ROW_ADDED_KEYS` (`_models/_attributes.py`).
- `front_matter` and the YAML path in `_cli/_render/_raw.py`; `raw_head` takes the rows instead of a mapping.
- `--json` no longer carries `frontmatter`: reverse the expectations round 1 added in `tests/cli/test_show.py`, `test_item_verbs.py`, `test_workflow.py`, `test_role.py`, `test_skill.py`, `test_operator.py`, and drop `raw_forms`'s YAML parse in `tests/cli/_roster.py` (grep `frontmatter` and `yaml` across `tests/cli/`).

## Files

`_cli/_render/_items.py`, `_cli/_render/_roster.py`, `_cli/_render/_raw.py`, `_api/_dto/_items.py`, `_roles.py`, `_skills.py`, `_operators.py`, `_services/_item_dto.py`, `_services/_item_ops.py`, `_services/_roster_ops.py`, `_models/_attributes.py`. Renderers stay off `_workflow`/`_config`/`_services` (meta guard); everything the rows need is already on the DTOs.

## Tests (about 4)

Rewrite round 1's header tests rather than adding beside them (`test_show.py::test_raw_prints_plain_text_instead_of_the_rendered_panel`, the `test_item_verbs.py` raw header tests, and the `show --raw` test in `test_role.py`, `test_skill.py`, `test_operator.py`):

- item `show --raw` with `FORCE_COLOR=3` and `COLUMNS=40`: the H1 first, then `type` and the panel's labelled rows in order without the ID and title rows (compare against the styled panel's text, so drift fails), the badge value without glyph, refs as `ID (kind)`, no ESC byte.
- an item with a created and a modified session: neither session appears under `--raw`, both appear in the styled panel.
- role, skill and operator `show --raw`: no H1, the unlabelled first row as a plain bullet, then their panel's labelled rows, then the body; `--no-header` prints the body alone (one case per type, or one helper the three share).
- `show --json` carries no `frontmatter` key (one item, one roster type).

Break each new or rewritten test once by hand (revert the line it guards, watch it go red) and say so in the handback.
<!-- sq:subtask:ST11:body:end -->

#### Discussion

<!-- sq:subtask:ST11:discussion -->
<!-- sq:subtask:ST11:discussion:end -->
<!-- sq:subtask:ST11:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T21:48:08Z] `manager` Catherine Manager:
  - Open point on ST1 settled: under --raw the H1 '# <id> — <title>' stays, after the YAML block (header, blank line, heading, blank line, body); --no-header drops both. Gaps 2 and 3 (plain output of the memory and board lines; the three-command grant) go to the architect before round 3.
- [2026-11-04T21:53:24Z] `tech-lead` Olivia Lead:
  - Brought in line with the ADR-1294 amendment of 2026-11-04: ST1 drops its open point (the heading stays after the YAML block) and moves memory/board raw output out of its note; new ST10 gives `memory list` and `board list` a `--raw` flag in round 3, before ST4; ST4 renders both with `--raw` and writes the grant as a YAML list; ST7/ST8 steps use `--raw`. ST1/ST2 scope and status unchanged. TASK-1296 updated for the ADR-427 narrowing. @manager
- [2026-11-04T22:11:03Z] `python-dev` Elias Python:
  - Round 1 (ST1, ST2) done, both Done. Not committed.
    
    - Source: new `_cli/_render/_raw.py` (YAML header, heading, one-write printer); `show` renderers for items, roles, skills, operators go through it. `--raw`/`--no-header` on every `show`; `--no-header` without `--raw` is refused up front (`common.require_raw_for_no_header`). A `frontmatter` field (JSON-native, without `subentities`) is projected by `header_fields` in `_item_dto.py` onto `ItemShow`, `RoleShow`, `SkillShow`, `OperatorShow`; `frontmatter` joins `ROW_ADDED_KEYS`. It also appears in `--json`. Roster entries print header then body with no synthetic H1 (the body carries its own); items keep `# <id> — <title>` after the header.
    - ST2: `expand_view_tags` replaces a view whose source, transform or template fails with `view_failure_line` (in `_views.py`); the stderr warning stays; `view_data` (the `--json` views map) now omits a failed view instead of raising.
    - Tests: 12 added (8 in test_item_verbs, 1 in test_show, 1 each in test_role, test_skill, test_operator) plus the pinned JSON/raw expectations updated. Each new test broken once by reverting its guarded line.
    - Gates: pyright 0 errors; ruff check and format clean; `tests/meta tests/cli tests/check tests/daemon tests/regressions -n 4`: 2182 passed, 2 skipped; new files also pass with `--api-mode remote` (350 passed).
    - `sq check`: clean.
- [2026-11-04T22:34:22Z, edited 2026-11-04T22:35:21Z] `tech-lead` Olivia Lead:
  - Added ST11 (US7) for op-pierre's panel-row --raw header ruling (c30d364 on ADR-1294); round 2 is now ST11 then ST3. ST11 supersedes ST1's YAML header and removes frontmatter/header_fields from the DTOs and --json; ST1 stays Done. Items: H1 first (ID and title rows), then a type row and the labelled rows; roster: the unlabelled first row as a plain bullet. TASK-1296 cut to the bullet-label pattern, fixture and canary. @manager
- [2026-11-04T23:07:48Z] `python-dev` Elias Python:
  - - Round 2 (ST11, ST3) done, both Done. Not committed. @manager
    
    **ST11.** One row builder per show, used by the styled panel and `--raw`: new `_cli/_render/_rows.py` (`Row`, `panel_text`, `raw_lines`); `_items.py` and `_roster.py` build their rows once. Items: heading, then `- **type:**` and the panel's rows without id/title, no glyphs, refs `ID (kind)`, session rows left out. Role, skill, operator: no H1, plain first bullet, then labelled rows. A role with no active item prints its rows then the activate line. Removed: `frontmatter` on the four show DTOs, `header_fields`, its `ROW_ADDED_KEYS` entry, `front_matter`/the YAML path; round 1's `--json` expectations reverted.
    
    **ST3.** `[views.role_playbook]` (source playbook, position top, declared after `role_definition`); `views/role_playbook.md.j2`; filter `role_playbook_sections` (`_interactions/_role_guidance.py`). `_views.py`: `ROLE_PLAYBOOK_VIEW_NAME`, `roster_companion_view_names`; `seeded_view_names` gives a role both. The view verbs now allow `role_playbook` on a role (`add`/`disable`); `role_definition` stays refused. Repair places the tag when the body has `role_definition` and no playbook tag in any state (disabled left alone, prose kept). `sq check` reports a lost tag through the existing rule (checked by hand, no new test). `migrate up` now adds the tag to role bodies through that repair (three migrate tests updated).
    Side change in `_view_tags.expand_view_tags`: a view that renders empty leaves no blank gap (a role with no playbook type shows its definition only).
    Manifest and content store regenerated and rebuilt (orphan dropped); script docstring says 31 templates. The override test squad's `[selected] views` gains `role_playbook`.
    
    **Gates.** pyright 0 errors; ruff check and format clean; `tests/meta tests/cli tests/check tests/daemon tests/regressions -n 4`: 2192 passed, 2 skipped. `--squad override tests/cli`: none of the failures are in files I own except round 1's: `test_item_verbs` `test_show_raw_no_header_prints_the_body_alone_with_its_views_expanded` and `test_show_raw_full_comments_prints_sub_entity_state_as_plain_text`, and `test_show` `test_no_header_prints_the_body_alone_under_raw_and_is_refused_without_it` (failed before this round too; they use the bundled milestone or its words); the `test_source*` modules fail as known. `sq check` clean.
    
    **Mutation checks (each reverted).** ST11: modified-session row shown under raw, badge glyph back, bold first bullet, wrapping on, activate-line rows dropped: each turned its test red. ST3: companion placement off, disable allowance off, other roles' guides in, empty-view gap back, capability heading removed, companions emptied: each turned its test red. The "role with no playbook type" test alone stays green when the gap returns (print trims trailing blanks); the `show --json` body test in `test_add_creates_a_role_that_defines_itself` catches it.
- [2026-11-04T23:33:28Z] `python-dev` Elias Python:
  - Round 3 (override-squad fix, ST10, ST4) done; ST10 and ST4 Done. Not committed. @manager
    
    **Override fix.** The three round 1 tests now reach their hosts through the profile: the no-header body test compares against the item's `--json` body, the full/comments test builds its heading from `P.kind` and `P.kind_initial`, and the never-coloured raw test uses the reference item (the `bundled_only` mark is gone). The milestone views-expanded check stays as its own `bundled_only` test, since the override squad has no item type with a view.
    
    **ST10.** `--raw` on `memory <slug> list` (bullet per entry, ``- `slug`: summary``; empty gives "no memories for <role>") and `board list` (numbered item with full text, then "- author, time[, until X]" line; empty gives "no current notices"). Both go through `print_raw`. No DTO change was needed. The `raw_option` help text no longer says "YAML header".
    
    **ST4.** Pointers per ADR-1294 section 1: regeneration comment first, `allowed-tools` as a YAML list, one `!` line with `|| echo`. New `_backends/_claude_code/_pointer_lines.py` (`PointerLine`, refuses a slug outside the grammar and echo text outside a safe character set). Role skill `sq-role-<slug>` with three lines, written and removed with the agent pointer. Agent pointer names only `sq mine`/`sq inbox`. `skills_for_role` = `sq-role-<slug>`, `squads`, `sq-memory` (no greeting, no per-type; `squads` is renamed in ST6). `managed_entry_paths` declares the role skill pointer. `candidate_orphans` exempts live roles' skills (the service now fills `live_role_slugs`). Drift: new non-abstract `AgentBackend.render_role_skill_entries` (default `{}`); `backend_entry_drift` compares it. Collisions refused in `_create_role` and `add_skill`.
    
    **Gates.** pyright 0 errors; ruff check and format clean. `tests/meta tests/cli tests/check tests/daemon tests/regressions -n 4`: 2210 passed, 2 skipped. `--squad override tests/cli -n 4`: 142 failed, 881 passed, 178 skipped, 118 errors; all of them are in `test_source*`. `sq check` clean.
    
    **Mutations (each reverted, each turned its test red).** raw no-header off; soft_wrap off (item raw, memory raw); empty memory text; stdout before the error; board ordinal fixed at 1 (the first test of it was too weak, rewritten with three notices); board expiry dropped; empty board text; board only first line; pointer comment line removed; board line removed from the role skill; `sq board list` added back to the agent pointer; `|| echo` dropped (bash/zsh test); role skill removal on retire; role skill write skipped; both collision checks; companion drift check; orphan exemption; live slugs in the orphan context.
    
    **Not verified in-process:** that Claude Code actually runs the `!` lines and the YAML-list grant (host behaviour). The shell tests only prove each line exits 0 with `sq` absent under bash and zsh.
- [2026-11-05T00:28:16Z] `python-dev` Elias Python:
  - - Round 4 (ST5) done; ST5 Done. Not committed. @manager
    
    **Removed.** The `sq-<type>` writer in the Claude Code backend, `seed_custom_skills`, the `item_skill` view and template, `ITEM_SKILL_VIEW_NAME`, the per-type arms of `_interactions/_skills.py` and `_views.py` (`_playbook_subject` is now the host's own type), the `item_skill_role_sections` and `custom_item_skill_commands` filters, the orphaned-skill arms in check, sync, projection and the roster DTOs, the type-implied kind of `preloaded_skill`, and two `sq check` rules: `skill_type_declared` and the `item_skill_shadowed` validator (also out of `[items.skill] validators` and the validator name tables). A leftover `sq-<type>` skill item is now an ordinary project skill: sync, show and retire work on it (driven in a scratch squad). Its `sq:view:item_skill` tag is an undeclared view, so `sq check` reports `view_target_resolves` on it until ST9 removes the item.
    
    **Tidied signatures.** `skills_for_role(role)`; `resolve_operator_invocable(slug, item)`; `skill_origin(slug)`, `item_origin(item)`, `is_system_skill(slug)`; `skill_row(item)`; `skill_view_name(slug)`; `skill_authoring_surface(view, spec, playbook)`; `managed_skill_slugs()`; `retirement.enforce` and `check_all` lose `playbook`. Five `_interactions` re-exports with no `src` user left the init. Vulture: no new finding against HEAD.
    
    **Texts.** No delivered text names an `sq-<type>` skill now. I removed the `sq-<type>` line from `role_definition.md.j2` and the golden-rule bullet from `squads_skill.md.j2` (both are on ST6's list; ST6 can skip them). The orphaned-guide and unheld-capability messages say "generated role playbook". Manifest and content store regenerated and rebuilt (one orphan blob dropped); script docstring says 30 templates; frozen views document loses `item_skill`.
    
    **Tests.** New: `test_init_writes_no_skill_for_a_bundled_or_a_project_type`, `test_a_fresh_squad_with_a_project_type_checks_clean` (test_init). Removed: the two `item_skill_shadowed` and the `skill_type_declared` breach tests. Changed: the seeding meta guard (renamed `..._seeds_the_managed_skills`, one seed call), the command-naming guard (per-type bodies out, `_MIN_CARRIERS` 4), the rule-pin table, the override fixture (`item_skill` out of `[selected]`), the `view add/disable` JSON tests (use `squads_skill`), views listing, spec digest, role-body text, the 0.14 to 0.20 `migrate up --json` expectation, and the override squad's item numbers (initiative 5, job 6, record 7; fewer skills seeded) across test_check, test_create, test_import, test_init, test_item_verbs, test_list, test_migrate, test_root_options, test_subentity_verbs, test_tree.
    
    **Gates.** pyright 0 errors; ruff check and format clean. `tests/meta tests/cli tests/check tests/daemon tests/regressions -n 4`: 2209 passed, 2 skipped (log st5-gate-default2.log). `--squad override tests/cli -n 4`: 1024 passed, 179 skipped, 0 failed, 0 errors. `sq check` clean.
    
    **Mutations (each reverted).** Seeding guard: dropped `seed_bundled_skills` from `adopt`, red. Command guard: `_MIN_CARRIERS` raised, red. Init test: backend writes `sq-<type>` pointers for every type, red. The check-clean test stayed green under that mutation and under one that also seeded `sq-task`/`sq-note` items: nothing the check does flags them, so that test holds only "init then check is clean" and the init test carries the guard.
    
    **Commands left unnamed in agent guidance:** none. `test_every_cli_command_is_named_in_agent_guidance.py` passes with the per-type bodies removed and no change to its exemptions.
    
    **For you.** (1) Behaviour change in old migrations: the 0.11 to 0.14 runner no longer seeds `sq-contract`/`sq-milestone` skill items, the 0.14 to 0.15 reclaim no longer touches per-type skill bodies, and 0.15 to 0.16 stamps them `origin: project`. Fixture `v0_14` run: changed 4 (was 6), origin report "2 system, 2 project". (2) Docs still describe the per-type skills and the two removed rules: docs/overrides.md (1242, 1431), docs/workflow.md (1228, 1309), docs/adoption.md (334), docs/README.md (70), docs/faq.md (110): tech-writer task. (3) The 0.19 corpus fixture has no per-type skills; ST9 builds its own case.
- [2026-11-05T00:30:41Z] `manager` Catherine Manager:
  - - Round 4 (ST5) committed. Decisions on the handback's open points:
      - Older migration runners: accepted. The 0.11→0.14 runner no longer seeds `sq-contract`/`sq-milestone`, and 0.15→0.16 stamps a per-type skill `origin: project`; only intermediate notices change, the end state is ST9's. ST9 must recognise a per-type skill by its `sq-<type>` slug whatever its origin, so a squad migrated from 0.14 still has them removed.
      - ST9 adds its own corpus fixture case with per-type skills, since the `v0_19` fixture has none.
      - The docs naming per-type skills and the two removed check rules (`docs/overrides.md`, `docs/workflow.md`, `docs/adoption.md`, `docs/README.md`, `docs/faq.md`) go to the tech-writer task, TASK-1298.
- [2026-11-05T00:47:49Z] `python-dev` Elias Python:
  - - Round 5 (ST6) done; ST6 Done. Not committed. @manager
    
      **Renames.** `SQUADS_SKILL` is `sq-how-to`, `GREETING_SKILL` is `sq-greeting`; `ensure_scaffold` creates `.claude/skills/sq-how-to`; the three descriptions say what each is for (`sq-greeting`: main session only, never a subagent). View names unchanged. Slugs in `_cli/_skill.py` epilog, `workflow.toml` comment, `playbook.toml` text (`sq-how-to` skill's comment-scoping), `role_definition.md.j2`, and the skill name only in `claude_section.md.j2` (opening, greeting paragraph, both orchestration-loop sentences). `bundled_skill_slugs` now sorts sq-greeting, sq-how-to, sq-memory (the memory and how-to ordinals swap).
    
      **Role definition.** The "follow `greeting`, then the `squads` section" instruction is gone; "Live with the operator" keeps the principle and points to `sq docs agents`. No command to read its own role, no `sq-<type>` text.
    
      **Trims and where each moved section lives.**
      - sq-how-to opening paragraph, working-language include, operators paragraph: dropped, the managed CLAUDE.md section carries them (opening, Working language, Operators). No docs topic needed.
      - "Working directly with the operator" (anchor to an item, keep status honest, hand back, stay in lane): `sq docs agents`. Partly held (The loop covers create, status, comment, hand off); the live-work anchoring and stay-in-lane advice is not a section there. Gap for TASK-1298.
      - "Finding things across the board" (search scope, `--type/--status`, hit regions, `--json`): `sq docs recipes` ("Prioritize, find, and focus") holds only `sq search "lockout"`; `sq search --help` holds the narrowing and `--json`. Gap for TASK-1298 (region forms are in `sq docs stability`).
      - workflow.md.j2 include (team workflow, aliases, lifecycles, sub-entities): `sq docs workflow` holds all of it (Team workflow, Type-command aliases, Status lifecycles, Sub-entities); `sq workflow` prints the squad's own cheatsheet.
      - sq-memory "Check it at the start of a run" and the board's "run `sq board list` at the start": dropped, the role skill renders both and sq-greeting runs them. The summary-vs-body split became a 3-line paragraph under the command block.
      - sq-greeting: "Get your bearings" dropped (ST7 rewrites the rest). Closing lines in sq-how-to: `sq docs agents`, `sq docs recipes`, `sq docs workflow`, `sq workflow`.
      - `workflow.md.j2` still said "Each role has skills for the item types it manages (e.g. sq-task...)". ST5 missed it; replaced by a sentence about the role's definition.
    
      **Guard widened (your call).** `test_every_cli_command_is_named_in_agent_guidance` failed for graph, import, override, reflog, renumber, repair: they were named only in the workflow cheatsheet that sq-how-to included. The closing line now sends agents to `sq workflow`, so I added the `workflow.md.j2` render as a fifth carrier (`_MIN_CARRIERS` 5). Revert it if you prefer to name those commands elsewhere.
    
      **Older runners (please check for ST9).** The rename changed what two old runners see. 0.14 to 0.15 reclaimed skill bodies by current slug, so a legacy `squads`/`greeting` skill would no longer get its view tag; 0.15 to 0.16 stamped them origin project. I added a legacy-slug mapping in each (`_current_skill_slug`, `_RENAMED_SYSTEM_SKILLS`) so the v0_14 fixture run is unchanged (changed 4, 2 system, 2 project). The 0.4 to 0.5 runner seeds `bundled_skill_slugs()`, so a pre-0.5 squad now gets `sq-how-to`/`sq-greeting` items directly: ST9 must not refuse those as "a project skill already holds the name" when their origin is system.
    
      **Tests.** Updated slugs in test_skill, test_role, test_sync, test_init, test_workflow, the daemon tests, the fixtures guard and the options test. New: `test_the_sq_how_to_skill_names_no_per_type_skill_and_ends_with_its_docs_topics`, `test_show_raw_names_the_sq_how_to_skill_and_no_other_skill_or_role_read`; the init test `test_init_writes_no_skill_for_a_bundled_or_a_project_type` carries the "no squads/greeting skill or pointer" case. Manifest and store regenerated and rebuilt (4 orphan blobs dropped). `_bundled_documents.py` untouched (its two `squads`/`greeting` mentions are old migration text; ST9 owns the 0.20 entry).
    
      **Gates.** pyright 0 errors; ruff check and format clean. `tests/meta tests/cli tests/check tests/daemon tests/regressions -n 4`: 2211 passed, 2 skipped (st6-gate3.log). `--squad override tests/cli -n 4`: 1026 passed, 179 skipped, 0 failed, 0 errors. `sq check` clean.
    
      **Mutations (each reverted, each red).** role definition back to `squads`; a `sq role manager show` line added to it; last closing line deleted; an `sq-task` line added to sq-how-to; scaffold dir back to `squads`; the 0.14 to 0.15 mapping removed; the 0.15 to 0.16 mapping removed; the new workflow carrier pointed at another template (guard red).
- [2026-11-05T00:50:03Z] `manager` Catherine Manager:
  - - Round 5 (ST6) committed. Decisions on the handback's points:
      - The command-naming guard counts the `workflow.md.j2` render as a carrier: accepted. `sq-how-to` sends every agent to `sq workflow`, which prints that cheatsheet, so the commands it names reach agents.
      - The legacy-slug mappings in the 0.14→0.15 and 0.15→0.16 runners: accepted.
      - For ST9: a squad migrated from before 0.5 is seeded `sq-how-to` and `sq-greeting` directly (system origin) and has no `squads`/`greeting` item. The rename skips what is already in place, and the "a project skill holds the name" stop fires only on a skill whose origin is project.
- [2026-11-05T01:05:52Z] `python-dev` Elias Python:
  - - Round 6 (ST7, ST8) done; both Done. Not committed. @manager
    
      **ST7.** New partial `templates/startup_steps.md.j2` holds steps 1 to 7 (takes `default_role_full_name`/`default_role_slug`, `spec`, `squad_dir`). `views/greeting_skill.md.j2` is rewritten whole: intro, partial, step 8 (greet, tone guidance trimmed), example. `[views.greeting_skill]` is now a `playbook` source; the template reads the default role from `source.roster`. The managed CLAUDE.md section keeps one bold instruction right after the opening paragraph; the Impersonation, Start of a run and greeting paragraphs are gone. `settings.json.j2` adds `Skill(sq-greeting)` and `Skill(sq-how-to)` (the existing merge keeps the adopter's rules). The `sq-greeting` description is reworded for the new steps.
      **ST8.** `BackendContext.role_bodies` (slug to the text `role show --raw --no-header` prints, trailing newlines stripped). `ServiceCore.role_bodies()` fills it in `refresh_managed`, `project_transition` and `sync`; `read_body`/`_stored_body`/`read_stored_body` moved from `ItemsMixin` to `ServiceCore` so the core can call them. AGENTS.md "Role definitions" compiles the bodies as-is; "Start of a run" includes the same partial plus a short step 8. Memory and board are not compiled.
      **Gates.** pyright 0; ruff check and format clean; `tests/meta tests/cli tests/check tests/daemon tests/regressions -n 4`: 2218 passed, 2 skipped (st78-gate2.log; two line-length fixes after it, re-ran meta + init/sync/skill: 876 passed). `--squad override tests/cli -n 4`: 1033 passed, 179 skipped, 0 failed, 0 errors. Manifest and content store regenerated and rebuilt (3 blobs dropped); script docstring says 31 templates. `sq check` clean.
      **Tests.** New: 3 in test_skill (eight steps in order, default role named and moved, no-default line), 2 in test_sync (one instruction and removed headings, allow-rule merge), 2 in test_init (AGENTS.md role bodies equal `role show` output with adopter prose and no memory/board; steps equal sq-greeting's). Changed: test_role set-default, test_workflow (views listing, view json now on `memory_skill`, new spec digest), the skill refusal text, the command-naming guard, the RoleView guard (the section no longer renders mission/responsibilities), frozen views document.
      **Mutations (each red, reverted).** instruction line, `Skill(sq-greeting)` rule, `--raw` on step 6, step 8 renumbered, default name hardcoded, no-default sentence, `{{ r.body }}` dropped, partial replaced by inline text, memory text appended to a body.
      **Notes.** (1) `sq skill sq-greeting body`/`view` refusals now name `.overrides/playbook.toml` as the authoring surface, as for `sq-how-to`, because the surface follows the source kind. (2) The 0.11 to 0.14 runner builds a `BackendContext` without role bodies: an agents_md squad migrated through it gets no role bodies in AGENTS.md until the next `sq sync`; ST9 can pass them or rely on its refresh. (3) Step 1 reads the operator with `--raw --no-header`. (4) `RoleView.mission`/`responsibilities` are still carried (view source) though AGENTS.md no longer renders them.
- [2026-11-05T01:08:16Z] `manager` Catherine Manager:
  - - Round 6 (ST7, ST8) committed. Notes on the handback:
      - Step 1 reads the operator with `show --raw --no-header`: accepted, consistent with the other steps.
      - The reworded `sq-greeting` description and the playbook authoring surface for `greeting_skill`: accepted.
      - For ST9: the 0.11→0.14 runner builds a `BackendContext` without role bodies; ST9's closing backend refresh writes AGENTS.md with them, so rely on that refresh and test an `agents_md` squad through the chain.
      - `RoleView.mission` and `responsibilities` are no longer rendered by any backend; the reviewer judges at review whether they go.
- [2026-11-05T01:26:37Z] `python-dev` Elias Python:
  - - Round 7 (ST9) done; ST9 Done. Not committed. @manager
    
    **Runner** (`_v0_19_to_v0_20.py`). Scans first, writes nothing on refusal; all cases fold into the existing list. Refuses: a per-type skill with body prose, a comment or an inbound ref; an `sq-role-<s>` skill item; a project skill holding `sq-greeting`/`sq-how-to` (also a system one that sits beside the legacy skill it would replace). A per-type skill is found by the `item_skill` tag or `sq-<x>` slug with author == slug, whatever its origin or type. A system `sq-how-to`/`sq-greeting` with no legacy twin is left alone (pre-0.5 squads). Then: removes the per-type items, their pointer directories (through the backend `remove_artifacts`, only those slugs) and index rows; renames `greeting`/`squads` (slug, title, author, description, file name; id and refs unchanged). MANUAL items 5 to 7 and SUMMARY updated; frozen `migrate help --json` document regenerated.
    **Closing refresh.** `Migration.refreshes_backend` (set on 0.20); `run_pending_migrations` calls `sync()` after the repair when a step asks. It writes pointers, role skills, CLAUDE.md, settings.json and the AGENTS.md role bodies. The role_playbook tag comes from the repair's backfill, not the runner.
    **Decision for you.** A squad migrated from before 0.15 keeps the rendered guidance as prose in its per-type skill bodies (ST5 stopped the 0.14 to 0.15 reclaim touching them), so the prose stop would refuse every such squad. The runner therefore ignores body prose when the on-disk schema is below 0.15 (generated text); comments and refs still refuse. Revert if you prefer the strict reading.
    **Tests.** New fixture `corpus/v0_19_skills` (a real 0.19 init plus a project skill). test_migrate: retires and renames (ids, refs, pointers, settings, CLAUDE.md, check clean); one run listing five refusals, nothing written; completes after the fix; removes by slug whatever origin or type; leaves already-named base skills; agents_md squad gets role bodies. test_init: both role-body tags and both Skill rules. Updated: the 0.14 chain json test (0.20 entry: 4 changed), the clean 0.19 test (also `.gitignore` from the refresh), `_bundled_documents.py`.
    **Gates.** pyright 0, ruff check and format clean. `tests/meta tests/cli tests/check tests/daemon tests/regressions -n 4`: 2225 passed, 2 skipped. `--squad override tests/cli -n 4`: 1040 passed, 179 skipped, 0 failed, 0 errors. `sq check` clean.
    **Mutations (each red, reverted).** pointer drop; backref hold; rendered-body cutoff; slug recognition; name-holder rule; refresh flag; role_playbook placement; settings rule; refusal always on.
    **Dry run** on a copy in ~/.cache/sq-mig-dry: no hard stop fires. Removed SKILL-193..199, 834, 835; renamed SKILL-192 and 200; 10 role bodies gained role_playbook. `.claude/skills`: launch-dev-host, releasing-squads, sq-greeting, sq-how-to, sq-memory, 10 sq-role-*; 9 per-type dirs and greeting/squads gone; 10 agent pointers rewritten; CLAUDE.md -30/+5 lines; settings.json has both Skill rules. `sq check` on the copy: 2 errors (ADR-1274 and REV-1281: a comment quotes an `sq:attrs` line, which 0.20 reads as a malformed attribute line), plus the stale-override warning and one unknown-source-author warning on ADR-1274. These are in the content, not the migration; fix those comments or accept before the real run.
    **Notes.** The `migrate up` footer still says "run `sq sync`" (harmless, now redundant for this step). CHANGELOG entry not written.
- [2026-11-05T01:28:59Z] `manager` Catherine Manager:
  - - Round 7 (ST9) committed. Decisions:
      - Body prose of a per-type skill on a squad below schema 0.15 is generated text and does not refuse the run: accepted. Comments and inbound refs still refuse.
      - This repository's own squad is not migrated by the manager: `sq migrate up` here is the operator's call (it moves the board past the released 0.19 tool). The after-measurement and QA run on migrated copies until op-pierre gives the go.
      - Before that run: the comments on ADR-1274 and REV-1281 that quote an `sq:attrs` line are read by 0.20 as malformed attribute lines; the reviewer judges whether that is a parser defect rather than a corpus fix.
<!-- sq:discussion:end -->
