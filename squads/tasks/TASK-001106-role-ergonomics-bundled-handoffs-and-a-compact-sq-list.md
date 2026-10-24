---
id: TASK-1106
sequence_id: 1106
type: task
title: Role ergonomics, bundled handoffs and a compact sq list
status: Draft
parent: FEAT-1101
author: tech-lead
assignee: python-dev
refs:
- REV-1099:addresses
description: F13, F15, F8, F17 and F14 from REV-1099.
subentities:
- local_id: ST1
  title: End role show with how to change the role's definition
  status: Todo
  story: US7
- local_id: ST2
  title: Scaffold every overridable role field with its bundled value and the append
    idiom
  status: Todo
  story: US7
- local_id: ST3
  title: Add sq list --compact, one line per item with a truncated title
  status: Todo
  story: US9
- local_id: ST4
  title: Word the bundled review and bug handoffs by the item's author
  status: Todo
  story: US8
- local_id: ST5
  title: Give the tech writer the narration sweep, name it in loop step 5, and default
    it to sonnet
  status: Todo
  story: US8
- local_id: ST6
  title: Write the 0.17.0 CHANGELOG entries for the role, list and guidance changes
  status: Todo
  assignee: tech-writer
  story: US7
created_at: '2026-10-24T10:04:05Z'
updated_at: '2026-10-24T10:08:11Z'
---
<!-- sq:body -->
## Goal

Five code and bundled-guidance fixes from REV-1099: F13 (`role show` says how to change a role), F15 (`override scaffold --role` lists every overridable field), F8 (a compact `sq list`), F17 (handoffs address the author) and F14 (the tech writer owns the narration sweep and defaults to sonnet). The doc-only findings are on TASK-1107.

## Approach

- **F13** (`src/squads/_cli/_role.py`, `show_role`). End the text output with one line: to change mission, responsibilities or model, run `sq override scaffold --role <slug>`, edit the file, then `sq sync`. Print it for an activated role and a bundled-only one. For a project-defined role (no bundled entry), point at its existing `.overrides/roles/<slug>.toml` instead. Do not add it to `--json`.
- **F15** (`src/squads/_overrides/_service.py`, `scaffold_role`). After the stamp, write every overridable `RoleSpec` field (`src/squads/_roles/_models.py`: `full_name`, `title`, `description`, `mission`, `responsibilities`, `agreements`, `model`, `color`, `can_spawn`, `capabilities`) commented out with its current bundled value, rendered as valid TOML once uncommented. Add a commented `# responsibilities = ["$(*self)", "…"]` line showing the append idiom. Derive the field list from the model, minus `slug` and any field an override may not set, so a new field cannot be missed. Uncommenting any one line must still load. The `--new` path is unchanged.
- **F8** (`src/squads/_cli/_main.py`, `list_items`). Add `--compact`: one line per item (ID, status, title truncated to the terminal width with an ellipsis), no table borders, no wrapped cells. Mutually exclusive with `--json`. The hidden-items footer stays. The default output does not change.
- **F17** (`src/squads/_specs/playbook.toml`). Change only the wording of two `*dev` handoffs. The review guide: "`@`-mention the review's author (shown on `sq review <n> show`) once all findings are Fixed, for re-review". The bug guide: move the task to InReview and mention the bug's author. Check `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` and any guard on hardcoded handoff slugs. Replacing a single playbook guide by slug is out of scope.
- **F14** (`src/squads/_specs/roles.toml`, `src/squads/_rendering/templates/claude/claude_section.md.j2`, and the AGENTS.md section if it carries the loop).
  - Tech-writer responsibilities gain the process-narration sweep of delivered text before an increment closes.
  - The tech-writer `model` moves from `haiku` to `sonnet`.
  - Orchestration loop step 5 names the technical writer as the role that runs the sweep. Resolve the title from the roster, and fall back to the current wording when no tech-writer is live.
  - Edit the template, never the rendered CLAUDE.md.

## Tests

Service-level plus CLI smoke each. Run `tests/meta`, `tests/integration` and `tests/cli` (bundled specs and templates change). Falsify each test.

- F13: footer present for an activated bundled role, a bundled-only role and a project-defined role; absent from `--json`.
- F15: for every bundled role, the scaffold parses as TOML, lists every overridable field, and each line, uncommented alone, yields a spec equal to the bundled one. The splat line resolves to the bundled list plus the new entry.
- F8: table over title lengths × terminal widths (`COLUMNS`): one line per item, no line over the width, truncation marked; `--compact --json` refused; filters compose.
- F17: the generated `sq-review` and `sq-bug` skills carry the author wording and no `@reviewer`/`@qa` in those handoffs.
- F14: the role card shows the new responsibility and `sonnet`. CLAUDE.md step 5 names the technical writer with a live tech-writer and keeps the neutral wording without one.

## Generated output

Regenerate `tests/goldens/claude_md_section.txt`, `agents_md_section.txt`, the role and skill goldens, and the template manifest. TASK-1103 (F16) and TASK-1098 touch the same CLAUDE.md template, and TASK-1105 edits `playbook.toml`, so sequence the regenerations. This repository has no role override, so its own tech-writer pointer moves to `sonnet` on the next `sq sync` after release.

## CHANGELOG substance (0.17.0)

The developer reports and the tech writer writes the entry (ST6).

- Added: `sq role <slug> show` ends with how to change the role (`sq override scaffold --role <slug>`, then `sq sync`).
- Changed: `sq override scaffold --role <slug>` writes every overridable field commented out with its bundled value, plus the splat-ref line for appending to a list.
- Added: `sq list --compact` prints one line per item with the title truncated to the terminal width.
- Changed: bundled review and bug handoffs tell the developer to mention the item's author instead of a fixed `@reviewer`/`@qa`.
- Changed: the bundled technical writer owns the process-narration sweep (orchestration loop step 5 names it) and defaults to `sonnet`. Run `sq sync` to pick it up. An override that sets the model is unaffected.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1106 add-subtask "<title>"`; track with `sq task 1106 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — End role show with how to change the role's definition

<!-- sq:subtask:ST1:body -->
Closes REV-1099 F13. `sq role <slug> show` text output ends with one line: to change mission, responsibilities or model, `sq override scaffold --role <slug>` then `sq sync`. A project-defined role is pointed at its existing override file. Nothing is added to `--json`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Scaffold every overridable role field with its bundled value and the append idiom

<!-- sq:subtask:ST2:body -->
Closes REV-1099 F15. `sq override scaffold --role <slug>` writes each overridable `RoleSpec` field commented out with its bundled value, derived from the model, plus a commented `responsibilities = ["$(*self)", "…"]` line. Every line, uncommented alone, must load. Tested for every bundled role.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Add sq list --compact, one line per item with a truncated title

<!-- sq:subtask:ST3:body -->
Closes REV-1099 F8. `--compact` prints ID, status and a title truncated to the terminal width, one line per item, and is refused with `--json`. The default output does not change. Table over title lengths × `COLUMNS`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Word the bundled review and bug handoffs by the item's author

<!-- sq:subtask:ST4:body -->
Closes REV-1099 F17 (wording only). The `*dev` handoff on the review type mentions the review's author (shown on `show`) instead of `@reviewer`, and the bug handoff mentions the bug's author instead of `@reviewer`/`@qa`. Replacing a single guide by slug stays out of scope. Regenerate the skill goldens and the manifest.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Give the tech writer the narration sweep, name it in loop step 5, and default it to sonnet

<!-- sq:subtask:ST5:body -->
Closes REV-1099 F14. The tech-writer responsibilities in `roles.toml` gain the process-narration sweep, and its `model` moves from `haiku` to `sonnet`. Step 5 of the orchestration loop in `claude_section.md.j2` (and the AGENTS.md section if it carries the loop) names the technical writer from the roster, and keeps neutral wording when none is live. Regenerate the goldens and the manifest.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Write the 0.17.0 CHANGELOG entries for the role, list and guidance changes

<!-- sq:subtask:ST6:body -->
Covers REV-1099 F13, F15, F8, F17 and F14 in the CHANGELOG, from this task's CHANGELOG substance and the developer's handback. Mapped to US7 for the board; it covers US7 to US9.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
