---
id: TASK-709
sequence_id: 709
type: task
title: Document retirement's withdrawal, refusal and --unlink for adopters
status: Done
parent: FEAT-691
author: tech-lead
priority: high
refs:
- REV-706:addresses
- TASK-707:depends-on
- TASK-708:depends-on
description: The two missing 0.13.0 changelog entries, the corrected sq check entry,
  and the roster docs lines
subentities:
- local_id: ST1
  title: Add the withdrawal entry under action required
  status: Done
  story: US4
- local_id: ST2
  title: Add the refusal and --unlink entry under Added
  status: Done
  story: US5
- local_id: ST3
  title: Correct the sq check entry's withdrawn condition
  status: Done
  story: US6
- local_id: ST4
  title: Cover all three roster types in the roles doc
  status: Done
  story: US3
- local_id: ST5
  title: Reconcile the workflow diagram with its own table
  status: Done
created_at: '2026-07-31T09:36:40Z'
updated_at: '2026-07-31T12:41:32Z'
---
<!-- sq:body -->
## Context

The `## [0.13.0]` changelog section documents the roster `status` verb, the `live` status-role
flag, the `sq check` reporter and the bundled `Draft` drop. It documents neither of the two
largest behavioural changes an adopter will meet: that retiring a role or skill now **deletes**
its generated backend files, and that a retirement can be **refused**, with `--unlink` as the one
way to satisfy the refusal.

Both omissions are named as adopter costs in ADR-697's own consequences: "Retirement now deletes
generated files. It is reversible … but an adopter who had come to rely on a generated file being
there will find it gone", and "the config-integrity refusal can block a legitimate-looking action
… the operator has to do two steps where they expected one." Documenting the guard's *reporter*
while omitting the guard itself leaves someone reading the 0.13.0 notes with no reason to expect
either the deletion or the refusal.

`--unlink` appears nowhere outside `sq role|skill|operator <addr> status --help`: `grep -rn unlink
CHANGELOG.md README.md docs/` returns only the pre-existing `link-role`/`unlink-role` hits and one
unrelated 0.x line. `docs/roles.md` gained `sq role <id> status Archived [--force]` and the
operator equivalent, but no skill line, no mention that the transition can be refused, and no
`--unlink`.

The misleading half of the existing entry — the claim that the verb works "the same way the
work-item `status` verb does, `--force` included" — is already corrected in place, because it was
wrong regardless of anything pending. What remains is what is missing.

## What to write

- **`### Changed — action required`: retirement withdraws generated backend config.** Moving a
  role or skill out of a live status deletes its generated per-entry file and rewrites every
  compiled region that named it; reactivating puts it back in full. It belongs in the
  action-required tier because a file an adopter had come to rely on disappears. Say plainly that
  it is reversible and how.
- **`### Added`: a retirement can be refused, and `--unlink` satisfies it.** Two conditions
  refuse: retiring the last live role while an agent backend is active, and retiring a skill a
  live role still preloads. Say what the refusal gives the reader — the specific condition, the
  dependent entities, and a remedy when one exists — and that where no remedy exists the message
  says so instead of inventing one. `--unlink` severs the stored role-scoping edges that
  constitute the dependency and then the ordinary check runs and passes on its own merits; it
  never suppresses a refusal, and a still-refused transition changes nothing. `--force` overrides
  the lifecycle's own transition edge only.
- **Correct the existing `sq check` entry.** It lists three flagged conditions, one of them "the
  default-carrying role not live". That condition is withdrawn — retiring the role that carries
  the default designation is legitimate, and the generated config now omits the default-role line
  rather than naming a role that is not there. The entry must list the conditions that remain,
  and the withdrawal itself is worth a line of its own: an adopter can lose that routing guidance
  from their generated config, and until a designation verb exists, reactivation is the way back.
- **`docs/roles.md`.** A `status` line for `skill` alongside the ones `role` and `operator` got;
  the fact that the transition can be refused; and `--unlink`.
- **`docs/workflow.md`.** Its ASCII diagram still labels the row `role · skill` while the table
  directly beneath it correctly says `role / skill / operator`.

## Constraints

These surfaces are read by adopters of the tool, so they describe the tool. No sq item IDs, no
decision or review references, no repo-process content, and no wording that narrates how any of
it was built. Match the voice of the entries already in the section: what changed, what it costs
the reader, what to type.

## Out of scope

Every code change under `src/`. The `--force` claim, already corrected. A designation verb for
the default role, which does not exist yet — the changelog may say what an adopter can do today,
never what is planned.

## Acceptance

- `grep -rn unlink CHANGELOG.md docs/` names the flag in both the changelog entry and
  `docs/roles.md`.
- The 0.13.0 section carries a withdrawal entry under `### Changed — action required` and a
  refusal-plus-`--unlink` entry under `### Added`.
- The `sq check` entry no longer lists the withdrawn default-role condition, and the withdrawal
  is stated as its own change with the recovery path named.
- `docs/roles.md` carries the skill `status` line, the refusability, and `--unlink`; every command
  spelling in the new text is verified by running it, not inferred from `--help` text alone.
- `docs/workflow.md`'s diagram row and the table beneath it agree.
- No sq/decision/review ID, no repo-process content, and no build-process narration anywhere in
  the new text.
- `uv run sq check` clean.

## Tests

None of this is code. The verification is running each command spelling that appears in the new
text against a throwaway squad and confirming the described behaviour, then re-reading the
section end to end as an adopter who has not followed any of the work.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 709 add-subtask "<title>"`; track with `sq task 709 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add the withdrawal entry under action required

<!-- sq:subtask:ST1:body -->
Retiring a role or skill deletes its generated per-entry file and rewrites every compiled region that named it. It belongs in the action-required tier because a file an adopter had come to rely on disappears; say plainly that it is reversible and how.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add the refusal and --unlink entry under Added

<!-- sq:subtask:ST2:body -->
Two conditions refuse a retirement: the last live role while an agent backend is active, and a skill a live role still preloads. Say what the refusal gives the reader, that where no remedy exists the message says so rather than inventing one, and that the severing flag satisfies the check rather than suppressing it. --force covers the lifecycle edge only.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Correct the sq check entry's withdrawn condition

<!-- sq:subtask:ST3:body -->
The existing entry lists three flagged conditions, one of them the default-carrying role not being live. That condition is withdrawn: retiring the designated role is legitimate and the generated config omits the default-role line instead of naming a role that is not there. List what remains, and give the withdrawal its own line with the recovery path named.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Cover all three roster types in the roles doc

<!-- sq:subtask:ST4:body -->
The roles doc gained a status line for role and for operator but not for skill, and mentions neither that the transition can be refused nor the severing flag. Add all three, verifying each command spelling by running it rather than inferring it from help text.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Reconcile the workflow diagram with its own table

<!-- sq:subtask:ST5:body -->
The ASCII diagram labels the roster row as role and skill while the table directly beneath it correctly says role, skill and operator. Make the two agree.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T11:18:46Z] Theo Writer:
  - Docs landed for the retirement behaviour. CHANGELOG 0.13.0: a Changed—action-required entry for retirement withdrawing the entry from generated backend config (reversible, reactivation restores it in full, no sq sync) plus its own entry for the default-role line being lost when the designated role is retired; an Added entry for the refusal plus --unlink; and the sq check entry corrected from three flagged conditions to the two that remain.
  - docs/roles.md gained a Managing skills section (the skill address verbs, incl. body/link-role/unlink-role/status) and a Retiring a roster entry section covering withdrawal, reactivation, the two refusal conditions, --force's scope, --unlink, the no-remedy cases and the sq check reporter. --unlink now appears on the role/skill/operator status lines. docs/workflow.md's diagram row is reconciled with its table (roster entries: role · skill · operator) and carries the roster-specific lifecycle rule. README's roster grammar block gained set-default and --unlink; docs/stability.md gained set-default/link-role to the item-first block, a status-flags paragraph, and a note under the generated-files tier that a roster entry's generated files track its status.
  - Reconciled rather than duplicated: the set-default changelog entry and docs/roles.md paragraph were already written — I kept both and only fixed the set-default entry's false history (it implied the default-role line could be lost before this release). Also corrected README's 'sq status validates transitions' to 'sq <type> <n> status <S>' — sq status is not a command.
  - Two things the tool contradicted in the brief. (1) The recovery path for a lost default-role line is 'sq role <addr> set-default', not 'until a designation verb exists, reactivation is the way back' — the verb shipped, and the warning sq prints already names it; I wrote what the tool does. (2) The skill refusal has three shapes, not one: a stored scoping edge (--unlink or unlink-role), a skill every live role preloads unconditionally (no remedy), and a skill implied by a declared item type (no remedy today). Documented as one condition with the remedy varying, which is how it reads to an adopter.
  - One thing I could not write as adopter-facing prose, flagged for whoever owns the code: 'sq role|skill|operator <addr> status --help' describes --unlink as severing 'the config-integrity clauses' severable edges'. That is internal vocabulary in a user-facing help string. Out of scope for this task (src/ was excluded) but it is the one place an adopter still meets it. @tech-lead
  - Verified by driving the CLI on five throwaway squads outside this repo, never against this squad's data: per-entry withdrawal and full reactivation (scoped custom skills included) across both claude_code and agents_md; compiled-region rewrites in CLAUDE.md, AGENTS.md and the generated sq-<type> skills; the operator roster line; both refusals; --force failing to override either; --unlink severing and reporting, then the ordinary check passing; --unlink refusing a non-retiring transition; --unlink reporting nothing severable on a role/operator; reactivation not restoring a severed scoping; set-default moving, clearing, refusing a non-live target and reporting a no-op; the default-role retirement warning; sq check reporting both conditions at exit 3; and the gate staying delta-scoped in an already-invalid squad. sq check clean, tests/meta + tests/cli/test_docs_cli.py green (66 passed).
<!-- sq:discussion:end -->
