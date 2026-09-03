---
id: TASK-793
sequence_id: 793
type: task
title: State the read-side half of the sq-managed-files rule in guidance
status: Done
author: tech-lead
assignee: tech-writer
priority: high
refs:
- BUG-789:fixes
description: Add 'read item files through sq show, never open them directly' to every
  carrier of the sq-managed rule
subentities:
- local_id: ST1
  title: Add the read-side half to the four named bundled templates
  status: Done
- local_id: ST2
  title: Rule on the role body and the two generated pointers
  status: Done
- local_id: ST3
  title: Carry the read-side half into the adopter-facing docs
  status: Done
- local_id: ST4
  title: Regenerate the template manifest and the goldens it moves
  status: Done
created_at: '2026-08-24T20:29:47Z'
updated_at: '2026-08-25T13:50:31Z'
---
<!-- sq:body -->
## What is wrong

Every agent-facing carrier of the "the `.md` files are sq-managed" rule states it for
**writes only**. Each one tells an agent not to hand-edit the file; none of them tells the
agent that the file is not a valid **read** surface either. An agent that runs
`cat squads/tasks/TASK-000123-….md` to learn an item's state is doing something no
guidance forbids, and today it mostly works — which is exactly what makes it a habit.

BUG-789 names four carriers with line numbers. Three more carry the same write-only
rule in a shorter spelling. The adopter-facing documentation carries it too.

## What to do

Add the read-side half to the rule wherever it is stated: **item `.md` files are read
through `sq <type> <n> show` (`--full --comments` for the dossier), never opened
directly.** Keep it in the register the surrounding prose already uses — one clause on
the existing bullet, not a new section — and keep the four bundled templates consistent
with each other in wording, because an agent meets several of them in one session.

The reason belongs with the rule, briefly: the CLI resolves state the file does not
carry, so a direct read returns strictly less than the command.

## Out of scope, by operator ruling

The `file:` line in `sq … show`'s header panel (`src/squads/_cli/_common.py:531`) is
**out of scope and stays exactly as it is.** After ADR-776, a human resolving a merge
conflict is the only legitimate reader of the raw file, and that path is what they
need. Do not remove it, do not add a caveat to it, and do not treat BUG-789's
"aggravating factor" paragraph as licence to touch it.

BUG-789 also left an open question: could a check or gate catch an agent opening a file
instead of using the CLI? It cannot — that is a property of an agent's tool-use choice
outside any sq-tracked artifact, not a property of the squad's own files. This work is
documentation-only for that reason. `sq`'s runtime behaviour does not change; nothing
under `src/squads/` outside the template directory changes, and no new check rule ships.

## Why it cannot wait

BUG-789 `blocks` FEAT-694. FEAT-694 retires the materialised sub-entity summary and head
regions, which is what turns a direct file read from a bad habit into a **wrong answer**:
with the roll-up gone from the body, an agent reading the raw file sees no sub-entities
at all and can conclude an item has none. The guidance must land no later than FEAT-694.

## Release ordering — already satisfied

These are bundled templates, so editing them forces a template-manifest regeneration
(`scripts/gen_template_manifest.py` replaces one version's entry wholesale, keyed on
`[project].version`). ADR-781 section 6 states the ordering once for every
template-touching change in this release: **the version bump comes first, then the
regeneration**, because regenerating against a shipped release's version corrupts that
release's recorded hashes.

That gate is **already satisfied** — `pyproject.toml` is at `0.14.0` and 0.13.x is
shipped. Regenerate freely; do not re-derive this and do not run `scripts/bump_version.py`.

## Acceptance

- Every bundled carrier states the read-side half, in wording consistent across the four
  primary templates.
- The adopter-facing documentation carriers state it too, in adopter register (no sq item
  IDs, no repo/dev-process framing).
- `sq workflow`, `sq docs agents` and a fresh `sq init` in a scratch directory all surface
  the new text with no code change.
- The template manifest is regenerated and the goldens/guards that move with these
  templates are updated in the same change.
- `uv run --all-extras pytest` is green; `uv run --all-extras ruff check .` and
  `ruff format --check .` are clean.
- Nothing under `src/squads/` outside `_rendering/templates/` changes. No new command,
  generator, or check rule ships.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 793 add-subtask "<title>"`; track with `sq task 793 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add the read-side half to the four named bundled templates

<!-- sq:subtask:ST1:body -->
The four carriers BUG-789 names. Each states the sq-managed rule for writes only;
each gains the read-side half.

- `src/squads/_rendering/templates/claude/claude_section.md.j2:161` — "Track all work
  with the `sq` CLI; the `.md` files are sq-managed — never edit them by hand."
  The bullet immediately below already says "Read with `sq <type> <n> show --full
  --comments`" but frames it as checking what you wrote; make it the only way to read.
- `src/squads/_rendering/templates/agents/squads_skill.md.j2:44` — "never hand-edit
  frontmatter or the `<!-- sq:* -->` markers, and don't type prose directly into a file.
  Every region is written through a command." Add the matching read clause.
- `src/squads/_rendering/templates/agents/item_skill.md.j2:51` — "The `.md` files are
  sq-managed — never edit them by hand." This one is a single closing paragraph rendered
  into every `sq-<type>` skill, so keep the addition to one clause.
- `src/squads/_rendering/templates/workflow.md.j2:74` — "never hand-edit them"; shared by
  the `squads` skill body and `sq workflow`.

Use the same phrasing in all four. An agent meets three or four of them in one session,
and four near-identical sentences that differ slightly read as four different rules.

State the reason once, briefly, where there is room (the CLAUDE.md section and the
`squads` skill are the two with room): the CLI resolves state the file does not carry,
so opening the file returns strictly less than the command.

Do not touch `src/squads/_cli/_common.py:531`.

Done when: all four templates carry the read-side half, consistently worded, and the
rendered output of each (`sq workflow`, a fresh `sq init`'s CLAUDE.md section, the
generated `squads` and `sq-<type>` skill bodies) shows it.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-08-25T13:41:48Z] Theo Writer:
  - All four carriers now state the read-side half in one shared clause: "read them through `sq <type> <n> show`, never by opening the file". The two with room (the CLAUDE.md managed section and the `squads` skill) also carry the reason once — the command resolves state the file does not carry, so a direct read returns strictly less than the command. `src/squads/_cli/_common.py` untouched.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rule on the role body and the two generated pointers

<!-- sq:subtask:ST2:body -->
Three more bundled templates carry the same rule in a shorter spelling and are not in
BUG-789's list:

- `src/squads/_rendering/templates/agents/role.md.j2:43` — "Track all work with the `sq`
  CLI; never alter the `<!-- sq:* -->` marker lines."
- `src/squads/_rendering/templates/claude/pointer_agent.md.j2:28-29` — same sentence.
- `src/squads/_rendering/templates/claude/pointer_skill.md.j2:10` — same sentence.

The role body has room and should carry the read-side half like the other four.

The two pointers are the judgment call. ADR-781 section 2a rules on what a pointer may
contain and orders its contents by priority "when space is contested" — identity, the
slug-bound startup command set, then the one command that renders the full definition. A
general read-surface rule is none of those three. Weigh that before adding a line, and if
the answer is that the pointers stay as they are, say so in a comment on this subtask
with the reasoning, so the next reader does not re-open it as an oversight.

Whichever way it goes, the pointers keep their existing "this pointer file itself is
regenerated by `sq sync`" stamp untouched — that is invariant 7 (a generated file says it
is generated), a different rule from this one, and it must not be conflated with it.

Done when: `role.md.j2` carries the read-side half, and the two pointers either carry it
or have a recorded decision explaining why they do not.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-08-25T13:42:11Z] Theo Writer:
  - Role body done: `agents/role.md.j2` now carries the same clause as the other four, worded identically ("The `.md` files are sq-managed — read them through `sq <type> <n> show`, never by opening the file.").
  - Decision on the two `.claude` pointers: they stay as they are. Three reasons, in order. (1) ADR-781 section 2a fixes what a pointer carries and orders it when space is contested — identity, the slug-bound startup command set, then the one command that renders the full definition. A general read-surface rule is none of the three, and adding it would be adding a fourth item ahead of nothing. (2) A pointer is not actually a carrier of this rule. Its existing sentence is about the `<!-- sq:* -->` marker lines, and the read-side rule reaches the same agent on the same first turn through the two surfaces the pointer routes it to — the role definition and the `CLAUDE.md` managed section — both of which now state it. (3) The pointer templates are about to be rewritten wholesale by the ADR-781 build work, so a line added here would be churn against an already-decided shape.
  - The pointers keep their "regenerated by `sq sync`" stamp untouched — that is invariant 7, a different rule, and nothing here touches it.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Carry the read-side half into the adopter-facing docs

<!-- sq:subtask:ST3:body -->
The adopter-facing documentation carries the same write-only rule and needs the same
addition. Carriers found:

- `docs/agents.md:56` — "Set the body with a command — never hand-edit the file."
- `docs/agents.md:84` — the "Never hand-edit a `.md` file" golden rule. The golden-rules
  list is the natural home for the read-side half as its own bullet.
- `docs/agents.md:91` — "The `.md` frontmatter is the source of truth."
- `docs/faq.md:39` — "No — the `.md` files are fully sq-managed."
- `docs/workflow.md:247` — "is sq-managed too — set it with …" (sub-entity bodies).
- `docs/tutorial.md:34` — "through `sq <type> <n> body` — never by hand-editing the file."
- `docs/migration.md:82` — the tool-owned/managed table row.

`docs/agents.md` is the home; the others get at most a clause, not a restatement. Not
every line above needs an edit — pick the ones where a reader is actually being told the
rule, and leave the incidental mentions alone.

Adopter register throughout: no sq item IDs, no references to this repository's own build
process, no mention of the internal reason the roll-up is moving. An adopter is being told
how to use the tool, not what changed in it.

Done when: `docs/agents.md` states the read-side half as a first-class rule, the other
docs carriers agree with it rather than contradicting it, and `sq docs agents` (offline,
packaged) surfaces the new text.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-08-25T13:42:24Z] Theo Writer:
  - Edited four of the seven doc carriers. `docs/agents.md` is the home: the golden-rules list gains "Never read a `.md` file directly either" as a first-class bullet next to the hand-edit rule, with the reason; loop step 3 gains a half-clause pointing at the same command.
  - Clause-only elsewhere: `docs/faq.md` ("Can I edit the markdown by hand?" now answers the read side too), `docs/workflow.md` (the sub-entity block — the on-disk block holds only prose, so opening the file shows strictly less than `show`), `docs/tutorial.md` (the scaffold/body pattern now states the read direction alongside the write one).
  - Left alone deliberately: the frontmatter-is-source-of-truth bullet in `docs/agents.md` (a restatement there would say the rule twice in one list) and the tool-owned/managed row in `docs/migration.md` (a tier table about what migrates, not a place a reader is being told the rule).
  - Adopter register throughout: no item IDs, no repository process, no mention of why the roll-up is moving.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Regenerate the template manifest and the goldens it moves

<!-- sq:subtask:ST4:body -->
The gate step that closes the change, run once after the template edits land.

Regenerate the template manifest:

    uv run python scripts/gen_template_manifest.py

The version-bump ordering ADR-781 section 6 requires is already satisfied —
`pyproject.toml` is at `0.14.0`, 0.13.x is shipped, so the generator writes a new
`0.14.0` key rather than overwriting a released one. Do not run
`scripts/bump_version.py`, and do not restore a prior manifest entry from a tag; that
recovery step belongs to a release cut, not to this change.

Guards and goldens that move with these templates, per ADR-781 section 6:

- `tests/unit/test_managed_section_and_cheatsheet_goldens.py` — pins the CLAUDE.md
  managed section, the AGENTS.md managed section, and the raw `sq workflow` cheatsheet
  byte-for-byte against a fixed roster. Goldens live in `tests/goldens/`
  (`claude_md_section.txt`, `agents_md_section.txt`, `workflow_cheatsheet.txt`,
  `workflow_cheatsheet_raw.txt`); refresh with `UPDATE_GOLDENS=1`.
- `tests/goldens/skill_body_sq-*.txt` — the seven generated item-skill bodies, moved by
  the `item_skill.md.j2` edit.
- `tests/integration/test_squads_skill_content_generation.py` and
  `tests/integration/test_item_skill_body_generation.py` — assert on generated skill text.
- `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` — the new wording
  must not name a bundled type, status or slug literal.
- `tests/meta/test_override_manifest_and_stamp_freshness.py` — fails loudly if a template
  changed without the generator being re-run; this is what proves the regeneration happened.
- `tests/cli/test_workflow_raw_markdown_golden.py` — the `sq workflow` raw output.

Regenerate the goldens, do not hand-edit them. Then read the diff: a golden refresh that
changes lines you did not intend to touch means a template edit went wider than planned.

Done when: the manifest carries a `0.14.0` entry covering the edited templates with no
prior version's entry altered, every guard above passes, and
`uv run --all-extras pytest` is green.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-08-25T13:42:34Z] Theo Writer:
  - Manifest regenerated at 0.14.0: a new key with 26 hashes, purely additive (28 insertions, 0 deletions) — no prior version entry altered. `scripts/bump_version.py` not run.
  - Goldens regenerated, not hand-edited: `claude_md_section.txt`, `agents_md_section.txt`, `workflow_cheatsheet.txt`, `workflow_cheatsheet_raw.txt` (UPDATE_GOLDENS=1) and the seven `skill_body_sq-*.txt` (via the pinned has-dev roster helper that test uses — that module has no UPDATE_GOLDENS path). Every changed line is the new clause and nothing else.
  - Two goldens outside this change were already failing on the branch tip before I touched anything: `override_list.json` and `override_diff.json` still carried a `0.13.1` override-base stamp after the version bump to 0.14.0. Refreshed them in the same pass so the suite is green; flagging it because it is not this task work.
  - Ran the affected set only, not the full suite: the two golden modules, `tests/meta/`, the two skill-generation integration modules and the two CLI golden modules — 244 passed. ruff check and ruff format --check clean.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-24T20:32:52Z] Olivia Lead:
  - Scoped from BUG-789 and moved to Ready: the bug names four bundled carriers, and the sweep found three more bundled (role body + the two pointers) plus seven doc lines, so this is one guidance surface, one owner, four subtasks.
  - Two operator/ADR rulings are written into the body rather than left to re-derive: the `file:` line in `sq … show` stays as-is (a human resolving a merge is its legitimate reader after ADR-776), and ADR-781 section 6's bump-before-regeneration gate is already satisfied at 0.14.0.
  - Priority high because BUG-789 blocks FEAT-694 — once the materialised roll-up retires, a direct file read stops being a bad habit and starts returning a wrong answer.
  - @tech-writer ready for dispatch.
- [2026-08-24T20:40:49Z] Catherine Manager:
  - Dispatch paused by the operator before any file was written; the task is InProgress but no work has landed yet. Resume from the task body as specified.
- [2026-08-25T13:42:58Z] Theo Writer:
  - Done and in review. The read-side half now ships in one shared clause — "read them through `sq <type> <n> show`, never by opening the file" — across all seven bundled carriers: the CLAUDE.md managed section, the `squads` skill, the generated `sq-<type>` skill body, the workflow cheatsheet (which is also what puts it into the AGENTS.md managed section) and the role body. The two with room carry the reason once: the command resolves state the file does not carry, so a direct read returns strictly less than the command.
  - Docs: `docs/agents.md` states it as a first-class golden rule; `docs/faq.md`, `docs/workflow.md` and `docs/tutorial.md` gain a clause each. `docs/migration.md` and the frontmatter bullet in `agents.md` left alone on purpose — see ST3.
  - The two `.claude` pointers stay as they are. Full reasoning on ST2; the short version is that ADR-781 section 2a orders a pointer contents by priority and a general read-surface rule is not in that set, the pointer routes the agent to two surfaces that now do state it, and the pointer templates are about to be rewritten wholesale anyway.
  - Out of scope and untouched as ruled: the `file:` line in the show header panel. No check rule, no command, no generator; nothing under `src/squads/` outside the template directory and the regenerated manifest.
  - Gates: manifest regenerated additively at 0.14.0, goldens regenerated (not hand-edited), 244 affected golden/meta/integration/CLI tests pass, ruff check and format clean, `sq check` clean. Full suite left to the coordinator. One incidental find recorded on ST4: two override goldens were already stale against the 0.14.0 version bump before this work and are refreshed here.
  - @tech-lead ready for review. BUG-789 left Open.
- [2026-08-25T13:50:31Z] Catherine Manager:
  - Verified before closing: manifest regeneration is purely additive (28 insertions, 0 deletions, the 0.13.1 entry untouched), the clause is present and identically worded in all five bundled templates and carried into the docs, full suite green at 3925 passed 0 failed, ruff clean.
<!-- sq:discussion:end -->
