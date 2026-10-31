---
id: TASK-1106
sequence_id: 1106
type: task
title: Role ergonomics, bundled handoffs and a compact sq list
status: Done
parent: FEAT-1101
author: tech-lead
assignee: python-dev
refs:
- REV-1099:addresses
- ADR-1121:implements
description: F13, F15, F8, F17 and F14 from REV-1099.
subentities:
- local_id: ST1
  title: End role show with how to change the role's definition
  status: Done
  maps_to: US7
- local_id: ST2
  title: Scaffold every overridable role field with its bundled value and the append
    idiom
  status: Done
  maps_to: US7
- local_id: ST3
  title: Add sq list --compact, one line per item with a truncated title
  status: Done
  maps_to: US9
- local_id: ST4
  title: Declare bundled capabilities and resolve @*name tokens in skills
  status: Done
  maps_to: US8
- local_id: ST5
  title: Give the tech writer the narration sweep, name it in loop step 5, and default
    it to sonnet
  status: Done
  maps_to: US8
- local_id: ST6
  title: Write the 0.17.0 CHANGELOG entries for the role, list and guidance changes
  status: Done
  assignee: tech-writer
  maps_to: US7
- local_id: ST7
  title: Convert every bundled hand-off to capability tokens
  status: Done
  maps_to: US8
- local_id: ST8
  title: Report unheld capability tokens in override guides
  status: Done
  maps_to: US8
created_at: '2026-10-24T10:04:05Z'
updated_at: '2026-10-28T12:11:19Z'
---
<!-- sq:body -->
## Goal

Five code and bundled-guidance fixes from REV-1099: F13 (`role show` says how to change a role), F15 (`override scaffold --role` lists every overridable field), F8 (a compact `sq list`), F17 (hand-offs mention roles by capability, per ADR-1121) and F14 (the tech writer owns the narration sweep and defaults to sonnet). The doc-only findings are on TASK-1107.

## Approach

- **F13** (`src/squads/_cli/_role.py`, `show_role`). End the text output with one line: to change mission, responsibilities or model, run `sq override scaffold --role <slug>`, edit the file, then `sq sync`. Print it for an activated role and a bundled-only one. For a project-defined role (no bundled entry), point at its existing `.overrides/roles/<slug>.toml` instead. Do not add it to `--json`.
- **F15** (`src/squads/_overrides/_service.py`, `scaffold_role`). After the stamp, write every overridable `RoleSpec` field (`src/squads/_roles/_models.py`: `full_name`, `title`, `description`, `mission`, `responsibilities`, `agreements`, `model`, `color`, `can_spawn`, `capabilities`) commented out with its current bundled value, rendered as valid TOML once uncommented. Add a commented `# responsibilities = ["$(*self)", "…"]` line showing the append idiom. Derive the field list from the model, minus `slug` and any field an override may not set, so a new field cannot be missed. Uncommenting any one line must still load. The `--new` path is unchanged.
- **F8** (`src/squads/_cli/_main.py`, `list_items`). Add `--compact`: one line per item (ID, status, title truncated to the terminal width with an ellipsis), no table borders, no wrapped cells. Mutually exclusive with `--json`. The hidden-items footer stays. The default output does not change.
- **F17, hand-offs mention roles by capability** (ADR-1121; `src/squads/_specs/roles.toml`, `src/squads/_specs/playbook.toml`, `src/squads/_interactions/_role_guidance.py`, `src/squads/_interactions/_loader.py`, `src/squads/_interactions/__init__.py`). ADR-1121 is the specification; where this body and the ADR disagree, the ADR wins.
  - **Capabilities** (ST4). In `roles.toml`: `tech-lead` holds `plan`, `reviewer` `review`, `qa` `verify`, `product-owner` `product`, `tech-writer` `edit`; `dev` stays on the `[dev]` table. The manager and the architect hold none. Nothing registers a capability, and nothing is stored on a role item.
  - **Resolver** (ST4). In guide text (`enter`, `do`, `handoff`, `watch`) and a type's `commands`, `@*<name>` renders, when `sq sync` generates the `sq-<type>` skill, as the `@<slug>` of every live holder in live-roster order joined with `/`, or as `*<name>` (no `@`, so `_MENTION_RE` does not match) when none is live. It runs in the same pass and over the same roster as `live_roster_text`. Each token resolves on its own; a retired role holds nothing; an operator never appears. A literal `@<slug>` keeps its current behaviour, including the placeholder rewrite. The playbook loader refuses a token whose name does not match `CAPABILITY_NAME_PATTERN`, as it already refuses a malformed `*<name>` subject.
  - **Bundled lines** (ST7). Convert every `@`-mention in the bundled playbook: `@tech-lead` to `@*plan`, `@reviewer`/`@qa` to `@*review`/`@*verify`, `@product-owner` to `@*product`, `@tech-writer` to `@*edit`, and the `@<developer>` placeholder to `@*dev`. The `--assignee <developer>` flag placeholder stays. The review `*dev` hand-off is the one exception and keeps the author prose: "`@`-mention the review's author (shown on `sq review <n> show`) once all findings are Fixed, for re-review". The task and bug `*dev` hand-offs use `@*review`/`@*verify`, not the author wording.
  - **Unheld tokens in override guides** (ST8). A well-formed token no live role holds, in a guide the adopter declared in `.overrides/playbook.toml`, is reported once by `sq check` and `sq sync` through the `orphaned_playbook_guides` path, naming the capability, the type and both remedies (declare it on a live role, or edit the line). The same token in the bundled playbook degrades silently to `*<name>`.
  - Replacing a single playbook guide by slug stays out of scope. No schema bump and no migration.
- **F14** (`src/squads/_specs/roles.toml`, `src/squads/_rendering/templates/claude/claude_section.md.j2`; the AGENTS.md section does not carry the loop).
  - Tech-writer responsibilities gain the process-narration sweep of delivered text before an increment closes.
  - The tech-writer `model` moves from `haiku` to `sonnet`.
  - Orchestration loop step 5 names the technical writer as the role that runs the sweep. Resolve the title from the roster, and fall back to the current wording when no tech-writer is live.
  - Edit the template, never the rendered CLAUDE.md.

## Tests

One table per behaviour. A row exists only if breaking the fix turns it red, so check each one that way. Rows are boundaries and failures, never a cross product. A behaviour is tested at one layer; where goldens already pin a bundled text, regenerate them and add no row. Run `tests/meta`, `tests/integration` and `tests/cli` (bundled specs and templates change).

- **F13, the role show footer** (CLI, since it is text output). Rows: an activated bundled role ends with the scaffold line; a project-defined role points at its `.overrides/roles/<slug>.toml`; `--json` carries no footer.
- **F15, the role scaffold** (unit on `scaffold_role`). Rows: the commented fields are exactly the overridable `RoleSpec` fields (set equality with the model, so a new field fails it); the whole scaffold uncommented loads and equals the bundled role, on a role whose fields cover a string, a list, a boolean and a model value; a field whose bundled value is unset is rendered so it still loads; the splat line resolves to the bundled list plus the new entry.
- **F8, `sq list --compact`** (CLI). Rows: a title that fits prints whole on one line; a longer title is cut with an ellipsis and no line passes `COLUMNS`; a width narrower than ID plus status still prints one line per item; `--compact --json` is refused; the hidden-items footer still prints.
- **F17, the `@*<name>` resolver** (unit, ST4; the ADR's boundaries). Rows: no live holder renders `*<name>`, keeps the line and extracts no mention; one holder renders `@<slug>`; two holders render `/`-joined in live-roster order; a retired holder is not counted; a role holding two capabilities named on one line appears once per token; a literal `@<slug>` next to a token is unchanged; a malformed token is a playbook load error.
- **F17, unheld tokens** (service, ST8). Rows: an unheld token in an override-declared guide is reported by `sq check`, naming the capability, the type and both remedies; the same report comes from `sq sync`; the same token in a bundled guide is silent; a held token in an override guide is silent.
- **F17, bundled lines** (ST7). The skill goldens, the role catalog golden and the playbook golden lock pin the converted text. One `tests/meta` row: the bundled playbook's guide text carries no `@<slug>` of a bundled role and no `@<developer>`. Adjust the vocabulary probe so its roster holds the capabilities it expects resolved, or assert the `*<name>` form.
- **F14, the narration sweep**. The role catalog golden pins the responsibility and the model. Rows on the rendered loop: with a live tech-writer, step 5 names the technical writer; with none live, it keeps the neutral wording.

## Generated output

Regenerate `tests/goldens/claude_md_section.txt`, `agents_md_section.txt`, the role and skill goldens, and the template manifest. F17 also regenerates the `sq-<type>` skills of epic, feature, task, bug, decision, milestone, review and guide, the role catalog golden, the playbook golden lock (`tests/unit/test_playbook_spec_artifact.py`) and the content store (`scripts/seed_content_store.py`); it does not change the CLAUDE.md or AGENTS.md sections. This repository has no role override, so its own tech-writer pointer moves to `sonnet` on the next `sq sync` after release.

## CHANGELOG substance (0.17.0)

The developer reports and the tech writer writes the entry (ST6).

- Added: `sq role <slug> show` ends with how to change the role (`sq override scaffold --role <slug>`, then `sq sync`).
- Changed: `sq override scaffold --role <slug>` writes every overridable field commented out with its bundled value, plus the splat-ref line for appending to a list.
- Added: `sq list --compact` prints one line per item with the title truncated to the terminal width.
- Changed: bundled hand-offs mention roles by capability (`@*plan`, `@*review`, `@*verify`, `@*product`, `@*edit`, `@*dev`), rendered as the live holders' `@`-mentions, or as `*<name>` when none is live. The bundled roles hold these capabilities; give one to another role with `capabilities = [...]` in its role override. The review hand-off tells the developer to mention the review's author. Literal `@<slug>` mentions in overrides keep working, and an override guide naming a capability no live role holds is reported by `sq check` and `sq sync`. Run `sq sync` to pick it up; no migration.
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
Closes REV-1099 F8. `--compact` prints ID, status and a title truncated to the terminal width, one line per item, and is refused with `--json`. The default output does not change. Tests: the F8 rows in the task's Tests section.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Declare bundled capabilities and resolve @*name tokens in skills

<!-- sq:subtask:ST4:body -->
Part of REV-1099 F17, per ADR-1121. Declare the bundled capabilities in `roles.toml` (`plan` on tech-lead, `review` on reviewer, `verify` on qa, `product` on product-owner, `edit` on tech-writer; `dev` unchanged). Add the `@*<name>` resolver to the `sq-<type>` skill render, beside `live_roster_text` and over the same live roster: live holders as `/`-joined `@<slug>` in roster order, `*<name>` when none. The playbook loader refuses a malformed token. Tests: the resolver rows in the task's Tests section.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Give the tech writer the narration sweep, name it in loop step 5, and default it to sonnet

<!-- sq:subtask:ST5:body -->
Closes REV-1099 F14. The tech-writer responsibilities in `roles.toml` gain the process-narration sweep, and its `model` moves from `haiku` to `sonnet`. Step 5 of the orchestration loop in `claude_section.md.j2` (the AGENTS.md section has no loop) names the technical writer from the roster, and keeps neutral wording when none is live. Regenerate the goldens and the manifest.
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

<!-- sq:subtask:ST7 -->
### ST7 — Convert every bundled hand-off to capability tokens

<!-- sq:subtask:ST7:body -->
Part of REV-1099 F17, per ADR-1121. Convert every `@`-mention in the bundled `playbook.toml` to its capability token (`@*plan`, `@*review`/`@*verify`, `@*product`, `@*edit`, `@*dev` for the `@<developer>` placeholder), keeping `--assignee <developer>`. The review `*dev` hand-off keeps the author prose; the task and bug ones use `@*review`/`@*verify`. Add the `tests/meta` row against bundled slug mentions, adjust the vocabulary probe, and regenerate the skill goldens, the role catalog golden, the playbook golden lock, the content store and the manifest.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Report unheld capability tokens in override guides

<!-- sq:subtask:ST8:body -->
Part of REV-1099 F17, per ADR-1121. A well-formed `@*<name>` token that no live role holds, in a guide declared in `.overrides/playbook.toml`, is reported once by `sq check` and `sq sync` through the `orphaned_playbook_guides` path, naming the capability, the type and both remedies. A bundled guide's unheld token stays silent. Tests: the unheld-token rows in the task's Tests section.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:46:25Z] `tech-lead` Olivia Lead:
  - Realigned: F17 now covers the task handoff (op-pierre ruling), F14 states AGENTS.md has no loop, the stale TASK-1098 sequencing dropped; Tests rewritten, goldens carry F17 and the role card. Moved to Ready.
- [2026-10-24T19:59:49Z] `op-pierre` Pierre Chat:
  - F17 decision: handoff mentions resolve by role capability, not hardcoded slugs. Roles declare capabilities (alongside the existing dev one, e.g. review and verify), and every bundled handoff line renders the slugs of the live roles holding the named capability. Applies to all hardcoded @-mentions in the bundled playbook, not only the review and task guides. Needs an ADR before implementation.
- [2026-10-24T20:03:55Z] `architect` Robert Architect:
  - - ADR-1121 records the F17 capability decision: bundled roles declare `plan`, `review`, `verify`, `product`, `edit` (plus `dev`), and handoff lines use `@*<name>`, rendered as the live holders' `@slug`s.
    - ST4 changes: the review `*dev` handoff keeps the author wording; the task and bug ones use `@*review`/`@*verify` instead of the item's author. All other bundled `@tech-lead`/`@<developer>`/`@product-owner`/`@tech-writer` mentions convert too, with `roles.toml` capabilities and a new token resolver.
    - @tech-lead re-plan ST4 against ADR-1121 once it is Accepted.
- [2026-10-24T21:23:26Z] `tech-lead` Olivia Lead:
  - Re-planned F17 to ADR-1121 (Accepted): ST4 is now capabilities plus the @*name resolver, ST7 converts the bundled hand-offs and regenerates, ST8 reports unheld tokens in override guides. Approach, Tests, Generated output and CHANGELOG substance updated; F13, F15, F8 and F14 unchanged. Stays Ready.
- [2026-10-24T22:53:15Z] `python-dev` Elias Python:
  - Handoff, ST1-ST5, ST7, ST8 done (ST6 CHANGELOG left to the tech writer).
    
    **Per subtask**
    - ST1: `role show` text ends with the scaffold line for a bundled role (activated or not) and with the `.overrides/roles/<slug>.toml` pointer for a non-bundled one; `--json` unchanged (`_cli/_role.py`).
    - ST2: `scaffold_role` writes every `RoleSpec` field except `slug` and `is_default` commented out with its bundled value, plus the commented `responsibilities = ["$(*self)", "…"]` append line; an unset `model`/`color` is written as `inherit`/`teal`. `--new` untouched. The placeholder dict is allowlisted in the tests/meta mutable-state guard.
    - ST3: `sq list --compact` (ID, status, title on one line, ellipsis at the console width, refused with `--json`, empty-view footer kept).
    - ST4: `roles.toml` capabilities (tech-lead plan, reviewer review, qa verify, product-owner product, tech-writer edit). `live_roster_text` resolves `@*<name>` in the same pass. The playbook loader refuses a malformed `@*` token in commands and guide text.
    - ST5: tech-writer gains the narration-sweep responsibility and `model = "sonnet"`; loop step 5 in `claude_section.md.j2` names the live `edit` holder(s) from the roster, neutral wording when none.
    - ST7: every bundled `@`-mention converted; the review `*dev` hand-off now reads "`@`-mention the review's author (shown on `sq review <n> show`) once all findings are Fixed, for re-review"; `--assignee <developer>` kept. New meta guard on bundled slug and `@<developer>` mentions.
    - ST8: `unheld_capability_tokens` + `unheld_capability_token_message` in `_interactions`, wired into `sq check` (`_playbook_guide_role_live`) and `sq sync`; only guides declared in `.overrides/playbook.toml`, deduped per type and capability. Token in a type's `commands` is not reported (it is not a guide).
    
    **Regenerated**: template manifest and content store (`gen_template_manifest.py`, `seed_content_store.py --rebuild`), `UPDATE_GOLDENS=1` goldens (claude/agents sections, role catalog and `role_qa_show`), skill-body goldens and the two spec JSON goldens (scratch script over the tests' own render functions). The pinned rosters in two unit tests now carry the bundled capabilities so tokens resolve. The repo CLAUDE.md is not regenerated (next `sq sync`). The CLAUDE.md golden pins the live-writer wording; the AGENTS.md section changed only through the responsibility line.
    
    **Tests** (each row mutated and seen red): CLI role-show footer, CLI list --compact, service scaffold, unit resolver, service unheld token, service malformed token, unit step-5 rows, meta bundled-text guard. Gates: ruff, format, pyright clean; tests/meta, unit, integration, cli, service: 13978 passed (tui and full suite not run). `sq check` clean.
    
    **CHANGELOG substance**: as in the task body, plus: a `@*<name>` token in an override guide that no live role holds is reported by `sq check` and `sq sync`; a malformed `@*` token in playbook text is a load error; the bundled tech-writer's responsibilities gain the narration sweep.
- [2026-10-24T23:12:00Z] `tech-writer` Theo Writer:
  - ST6 done. CHANGELOG 0.17.0: Added the @*<name> token (with the malformed-token load error), the unheld-token report, sq list --compact and the role show hint; Changed the bundled capabilities and hand-offs, the full role scaffold, and the tech writer (narration sweep, sonnet, loop step 5).
  - Docs: roles.md (roster model, bundled capability table, moving or dropping a capability, new section "Mentioning a capability in hand-offs", role show hint), overrides.md (scaffold --role, playbook Rules bullet with the warning text, example uses @*plan), workflow.md and README (list --compact), agents.md (tech writer duty). Every quoted message and rendering checked on the dev build in a scratch squad.
  - For src (not edited): the scaffold --role confirmation still prints "to add fields to override (e.g. full_name, model)", which no longer describes the file it just wrote. @manager for the guards and the merge.
- [2026-10-24T23:27:42Z] `python-dev` Elias Python:
  - REV-1130 F1-F5 fixed; targeted gates and tests/meta, unit, integration, cli, service pass (13982). @reviewer for re-review.
<!-- sq:discussion:end -->
