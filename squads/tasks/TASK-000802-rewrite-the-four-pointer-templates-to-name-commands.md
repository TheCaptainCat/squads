---
id: TASK-802
sequence_id: 802
type: task
title: Rewrite the four pointer templates to name commands
status: Done
parent: FEAT-792
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-781:implements
description: Drop squad_path from all four templates, move the slug-bound startup
  command set into the pointers from one declared list, and reword invariant 5
subentities:
- local_id: ST1
  title: Drop squad_path from the four templates and its five producers
  status: Todo
  story: US1
- local_id: ST2
  title: Declare the startup command set once and render both pointers from it
  status: Todo
  story: US2
- local_id: ST3
  title: Remove the role body template's duplicate startup command block
  status: Todo
  story: US2
- local_id: ST4
  title: Reword invariant 5 to the containment statement
  status: Todo
  story: US5
- local_id: ST5
  title: Regenerate the template manifest and re-pin the goldens
  status: Todo
  story: US1
created_at: '2026-08-25T14:42:04Z'
updated_at: '2026-08-26T11:19:09Z'
---
<!-- sq:body -->
## Scope

Implements ADR-781 sections 1, 2, 3, 4 and 6 for FEAT-792 stories US1, US2 and US5.

All of it is one dev pass on purpose. Every piece touches a bundled template and therefore the
same `src/squads/_rendering/templates_manifest.json` regeneration; splitting it would put two
devs in the same files and regenerate one manifest twice.

## Verified ground truth — take these readings, not the decision's line numbers

ADR-781 and FEAT-792 were written against an earlier tree. Three of their statements no longer
match `HEAD` (`8408390`). All three were driven before this task was written.

**1. `squad_path` has five surviving producer sites, not seven.** The decision counts five
backend render sites plus two migration runners. `grep -rn squad_path src/` now returns:

- `_backends/_claude_code/_backend.py:223`, `:355`, `:377` — live
- `_migrations/_v0_4_to_v0_5.py:127`, `_migrations/_v0_8_to_v0_10.py:113` — frozen runners
- the four templates themselves

The two `_agents_md/_backend.py` render sites the decision names are **gone**: that backend's
`generate_role_entry`/`generate_skill_entry` now write nothing and only unlink a pre-upgrade
staging file. Do not go looking for them.

**2. The two `agents_md` entry templates are orphaned.** `agents_md/role_entry.md.j2` and
`skill_entry.md.j2` carry `**Squad file:** {{ squad_path }}` but nothing renders them any
more — `agents_md/agents_section.md.j2` does not include them, and no Python call site names
them. They are still bundled package data and still carry hashes in the manifest.

Satisfy the rule literally: drop the `**Squad file:**` line from both, exactly as the decision
says, and change nothing else about them. **Do not delete either template** — whether an
unrendered bundled template should be removed is a separate call that belongs to the architect,
not to this task; the note below records it for them.

**3. Invariant 5 is NOT in CLAUDE.md's managed region.** FEAT-792's US5 and ADR-781 section 4
both say to edit it at `claude/claude_section.md.j2`. That is wrong. `CLAUDE.md`'s managed
region is lines 229-345 (`<!-- squads:start -->` / `<!-- squads:end -->`); invariant 5 is line
107, in this repository's own hand-authored contributor documentation above the region.
`claude_section.md.j2` contains no invariant list at all.

So invariant 5 is a hand edit to `/home/pchat/projects/squads/CLAUDE.md` — the one file in this
change that is *not* generated. Do not touch `claude_section.md.j2` for it, and do not expect
the managed-section golden to move on its account.

**4. The frozen migration runners are not a break to fix.** ADR-781 section 6 is explicit: a
pointer is regenerated, never migrated, so a runner that rewrites one should emit today's
pointer shape. **Do not pin a copy of the old template inside either runner.** What is owed is
exactly one thing at each site: drop the now-dead `squad_path=` kwarg.

## Release ordering — already satisfied, do not bump

ADR-781 section 6 requires the version bump before the manifest regeneration, because
`scripts/gen_template_manifest.py` replaces one version's entry wholesale keyed on
`[project].version`, and regenerating at a shipped version corrupts the provenance
`sq override diff` reads.

`pyproject.toml` is already at `0.14.0`, which is unreleased. The ordering is therefore already
satisfied and there is nothing to sequence. **Do not run `scripts/bump_version.py`.** Regenerate
the manifest and then confirm with `git diff` that only the `0.14.0` key changed — any movement
in a `0.13.x` or earlier key means a shipped release's hashes were overwritten and must be
restored from the tag before going further.

## What changes

**The two Claude Code pointer templates.** `claude/pointer_agent.md.j2` loses `@{{ squad_path }}`
(line 25) and `claude/pointer_skill.md.j2` loses it (line 8). Each gains, in its place, the
slug-bound startup command set and one command that renders the full definition —
`sq role <slug> show` for the agent pointer, `sq skill <slug> show` for the skill pointer. Both
templates also carry a trailing "regenerated by `sq sync`" sentence that ends "change the role
definition at the path above instead": there is no path above any more, so that clause needs
rewording to name the command instead. Invariant 7 requires the sentence itself to stay.

**Pointer frontmatter is unchanged.** ADR-781 section 2a rules every field currently in
`pointer_agent.md.j2`'s frontmatter — `name`, `description`, `model`, `color`,
`disallowedTools`, the resolved `skills` list — materialised, and `full_name` not. `full_name`
is body prose today, and the body is what the fetch command replaces, so nothing is removed
from frontmatter. Do not "tidy" the skills list out: the decision records that removing it was
an error and why.

**One declared command set in code, two renderings.** The startup commands are
`sq memory <slug> list`, `sq memory <slug> show <slug>`, `sq board list`, `sq mine <slug>`,
`sq inbox <slug>`. They exist today only inside `agents/role.md.j2:29-36`, hand-written. Declare
them once in Python and render both surfaces from that declaration, so a command added to the
set appears in both or in neither. A module-level list or dict will fail
`tests/meta/test_no_unallowlisted_module_level_mutable_state.py` — allowlist it there as a code
constant rather than restructuring around the guard, and run `uv run pytest tests/meta` before
handing back.

**The role body template loses its copy.** `agents/role.md.j2` gives up the startup-command
block. Two slug-bound copies of one command set, in two files with two regenerators, is the
duplication ADR-781 section 3 exists to prevent. What stays in the managed region is the
generic protocol and its rationale, already present at `claude/claude_section.md.j2:53-61` —
that is the second rendering, and it is not slug-bound. Do not add a third.

**Invariant 5 in CLAUDE.md** is reworded to the containment statement ADR-781 section 4 quotes
verbatim. Copy it from the decision rather than paraphrasing it.

**The manifest and the pins move with the templates.** Regenerate
`templates_manifest.json`; re-pin `tests/unit/test_managed_section_and_cheatsheet_goldens.py`
and any other golden the template edits move (`UPDATE_GOLDENS=1`, then read the diff and
confirm every hunk is one you intended — a golden regenerated without being read proves
nothing). `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` and
`tests/meta/test_bundled_templates_carry_no_operator_identity.py` both read generated agent
text and must stay green.

## Open question carried to the architect, not settled here

`sq role <slug> show` prints mission and responsibilities **twice** — once from the computed
card, once from the stored body rendered beneath it (driven: `uv run sq role architect show`).
The two can disagree, because the card resolves a project override while the body carries
whatever the last `sq sync` wrote. ADR-781's consequences name this as the decision's own to
settle and leave it unsettled; the options it names are dropping the overlapping card rows, or
rendering the body from the resolved definition on every show.

This task makes that command an agent's primary definition read, which is what turns a cosmetic
duplication into a disagreement an agent can act on. **Do not choose an option while
implementing.** It does not block the work — the pointer names the command whichever way it is
settled, and the duplication is pre-existing rather than introduced here. Raise it with the
architect and let it land as its own change.

The orphaned `agents_md` entry templates (ground truth 2) go to the architect on the same trip.

## Acceptance

- `grep -rn "squad_path" src/ tests/` returns nothing outside the manifest's historical hashes.
- All four templates render without a `squad_path` context value, and no producer passes one:
  the three `_claude_code/_backend.py` sites and both frozen migration runners drop the kwarg,
  and neither runner gains a pinned template copy.
- A generated agent pointer contains its identity frontmatter, the five startup commands with
  the slug already substituted, and `sq role <slug> show`. A generated skill pointer contains
  its identity frontmatter and `sq skill <slug> show`. Neither contains a filesystem path.
- `agents/role.md.j2` no longer renders the startup command set, and a freshly synced role body
  no longer contains it.
- Both surfaces render from one declaration in code: changing that declaration changes the
  pointer and nothing has to be edited in a template to match.
- `CLAUDE.md` line 107 reads ADR-781 section 4's replacement wording verbatim, edited in place
  above the managed region; `claude_section.md.j2` is untouched.
- `templates_manifest.json` is regenerated and `git diff` shows movement under the `0.14.0` key
  only. `scripts/bump_version.py` was not run.
- `uv run --all-extras pytest`, `uv run --all-extras pyright`, `uv run --all-extras ruff check .`
  and `uv run --all-extras ruff format --check .` are all clean, and `uv run sq check` is clean.
- `uv run sq sync` in this repository regenerates the pointers, and the resulting `.claude/`
  diff is the intended one — read it, do not assume it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 802 add-subtask "<title>"`; track with `sq task 802 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Drop squad_path from the four templates and its five producers

<!-- sq:subtask:ST1:body -->
Remove `@{{ squad_path }}` from `claude/pointer_agent.md.j2:25` and
`claude/pointer_skill.md.j2:8`, and the `**Squad file:** {{ squad_path }}` line from
`agents_md/role_entry.md.j2:11` and `agents_md/skill_entry.md.j2:5`. ADR-781 section 1 rules the
`agents_md` pair in on the same ground as the Claude pair — a displayed path is unusable for the
same reason an instructed one is unresolvable — even though those two templates currently have no
renderer. Drop the line, keep the templates.

Then stop computing the value at every surviving producer. Five sites, not the seven ADR-781
counts: `_backends/_claude_code/_backend.py:223`, `:355`, `:377`, plus
`_migrations/_v0_4_to_v0_5.py:127` and `_migrations/_v0_8_to_v0_10.py:113`. The two
`_agents_md/_backend.py` sites the decision names no longer exist.

The migration runners drop the kwarg and nothing else. A pointer is regenerated, never migrated,
so a runner that rewrites one emits today's shape — do not pin a historical copy of the template
inside either runner, and do not treat their rendering of a changed template as a break.

`ctx.root_relative` and `ctx.rel` may lose their last caller on this path. Check with
`uv run vulture` rather than guessing, and remove only what is genuinely unreferenced.

Done when `grep -rn "squad_path" src/ tests/` returns nothing outside the manifest's historical
hashes, and no template renders with a `squad_path` in its context.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Declare the startup command set once and render both pointers from it

<!-- sq:subtask:ST2:body -->
The five startup commands — `sq memory <slug> list`, `sq memory <slug> show <slug>`,
`sq board list`, `sq mine <slug>`, `sq inbox <slug>` — exist today only as hand-written lines in
`agents/role.md.j2:29-36`. Declare them once in Python and render both pointer templates from that
declaration, with the slug already substituted.

Each pointer also gains one command that renders the full definition: `sq role <slug> show` in
`pointer_agent.md.j2`, `sq skill <slug> show` in `pointer_skill.md.j2`. That command replaces the
definition the removed path used to load, so the pointer names it rather than embedding it.

Both templates end with a "regenerated by `sq sync`" sentence whose tail reads "change the role
definition at the path above instead". There is no path above once the previous subtask lands, so
reword the tail to name the command. Invariant 7 requires the sentence itself to stay.

Pointer frontmatter does not change. ADR-781 section 2a rules `name`, `description`, `model`,
`color`, `disallowedTools` and the resolved `skills` list all materialised; `full_name` is body
prose and leaves with the body. The decision records that removing the skills list was an error
and why — do not remove it.

A module-level list or dict holding the declaration will fail
`tests/meta/test_no_unallowlisted_module_level_mutable_state.py`. Allowlist it there as a code
constant rather than restructuring around the guard, and run `uv run pytest tests/meta` before
handing back.

Done when the declaration is the only place the command set is written: adding a sixth command
there makes it appear in both pointers with no template edit.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Remove the role body template's duplicate startup command block

<!-- sq:subtask:ST3:body -->
`agents/role.md.j2` gives up its startup-command block (lines 29-36), which is the copy the
pointer's now supersedes. Two slug-bound copies of one command set, in two files with two
regenerators, is the duplication ADR-781 section 3 exists to prevent.

Everything else in that template's working-agreements section stays: the "operate as" line, the
sq-managed-files rule, the per-type skill pointer, and the comment-scoping convention are not part
of the command set and have no second copy.

The second rendering of this protocol already ships and stays where it is:
`claude/claude_section.md.j2:53-61` states it generically, with a `<role>` placeholder the agent
substitutes for itself, alongside the rationale (why both queue surfaces are read, what memory is
versus what the board is). That rationale is shared by every agent and belongs stated once. Do not
move it into the pointer and do not add a third rendering.

Done when a freshly synced role body no longer contains the startup commands, the generic
protocol in the managed region is unchanged, and no agent-facing surface has lost the ability to
find them.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Reword invariant 5 to the containment statement

<!-- sq:subtask:ST4:body -->
Replace `CLAUDE.md` line 107 with the wording ADR-781 section 4 quotes. Copy it verbatim from the
decision rather than paraphrasing:

> **`.claude/` files are pointers**, not content. A pointer carries only what the host must read
> before an agent can run — its identity, the text the host selects it by, and the constraints
> squads imposes on the session — plus the commands that fetch the rest. Anything `sq` can
> answer, a pointer does not hold.

The old wording located the definition by directory, which is the assumption remote mode breaks,
and "pointers, not content" read as satisfied by any file that was merely short — which is how
seven fields of role state came to sit in one without anybody judging it a violation.

**This is a hand edit, and it is the one file in this task that is not generated.** FEAT-792's US5
and ADR-781 section 4 both say to make it at `claude/claude_section.md.j2`; that is wrong, and it
was checked. `CLAUDE.md`'s managed region runs from `<!-- squads:start -->` at line 229 to
`<!-- squads:end -->` at line 345. Invariant 5 is at line 107, well above it, in this
repository's own hand-authored contributor documentation, and `claude_section.md.j2` carries no
invariant list at all. Editing the template for this would change a different surface and leave
invariant 5 untouched.

Done when line 107 reads the replacement, `claude_section.md.j2` is untouched by this subtask, and
`uv run sq sync` does not overwrite the edit.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Regenerate the template manifest and re-pin the goldens

<!-- sq:subtask:ST5:body -->
Four bundled templates change in this task, so `src/squads/_rendering/templates_manifest.json`
has to be regenerated — the hashes are the provenance `sq override diff` reads.

**Do not run `scripts/bump_version.py`.** ADR-781 section 6 requires the version bump before the
regeneration, because the generator replaces one version's entry wholesale keyed on
`[project].version`, and regenerating at a shipped version overwrites that release's recorded
hashes. `pyproject.toml` is already at `0.14.0`, which is unreleased, so the ordering is already
satisfied and there is nothing to sequence.

After regenerating, read `git diff` on the manifest and confirm **only the `0.14.0` key moved**.
Any movement under `0.13.x` or earlier means a shipped release's hashes were overwritten; restore
that entry from its tag before going any further.

Then re-pin what the template edits move. `tests/unit/test_managed_section_and_cheatsheet_goldens.py`
is the managed-section and cheatsheet golden; other goldens under `tests/goldens/` may move with
the role body template. Regenerate with `UPDATE_GOLDENS=1`, then **read the resulting diff hunk by
hunk** and confirm each one is a change this task intended — a golden regenerated without being
read proves nothing.

Two meta guards read generated agent text and must stay green:
`tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` and
`tests/meta/test_bundled_templates_carry_no_operator_identity.py`.

Finally run `uv run sq sync` in this repository and read the `.claude/` diff it produces: that is
the change an adopter sees, and it is the last chance to notice a template that renders correctly
in a test and wrongly in the corpus.

Done when the full gate is clean — `uv run --all-extras pytest`, `pyright`, `ruff check .`,
`ruff format --check .`, and `uv run sq check` — and the manifest diff touches one version key.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T15:02:36Z] Robert Architect:
  - Ruled, ADR-777 amendment B3 (2026-08-25). Yes - an unrendered bundled template is deleted, and these two go. Verified the orphaning myself at 8408390: agents_md/agents_section.md.j2 includes only workflow.md.j2, no Python call site names role_entry.md.j2 or skill_entry.md.j2, and the AGENTS.md backend generate_role_entry/generate_skill_entry write nothing and only unlink a pre-upgrade staging file. Both still carry a hash in all fifteen manifest release entries.
  - The deciding fact is one I drove rather than read: sq override scaffold agents_md/role_entry.md.j2 SUCCEEDS on a fresh squad and writes an override that will never render. That is an override surface with no consumer, which ADR-777 section 1 first promise forbids - an adopter is owed a surface or a stated reason there is none, and silence is neither. Deletion replaces the Squad-file strip rather than following it: spending a manifest revision and a retained blob on a file that renders nothing is the cost the manifest widening makes visible. Retention is undisturbed - past index entries keep naming their revisions.
  - Whose work: not a follow-up. Both are bundled-template changes settled by one manifest regeneration, so the removal belongs to whichever pass regenerates the manifest this release - this one, on the same terms as the four pointer templates. I am not editing this task scope; @tech-lead yours to fold in (extend this task or file a sibling that lands in the same regeneration). If it lands as deletion, the Squad-file strip on those two files is moot and the ADR-781 rule is satisfied vacuously. Whether the backend ABC keeps generate_role_entry/generate_skill_entry at all is a separate question I did not reach.
- [2026-08-26T11:09:34Z] Elias Python:
  - All 5 subtasks done. Dropped squad_path from the four templates and its five producers (3 _claude_code/_backend.py render sites; the two _agents_md sites the decision named are already gone). agents_md/role_entry.md.j2 and skill_entry.md.j2 kept (not deleted) per this task's own explicit ground-truth instruction — the architect's later ADR-781 comment ruling deletion was left for tech-lead to fold in, and no task folds it in yet.
  - Declared _STARTUP_COMMAND_TEMPLATES once in _backends/_claude_code/_backend.py; pointer_agent.md.j2 renders it slug-substituted plus 'sq role <slug> show'; pointer_skill.md.j2 carries only 'sq skill <slug> show' (matches ADR-781 2a: nothing else is in a skill pointer). role.md.j2 lost its own copy of the five commands; claude_section.md.j2 untouched.
  - CLAUDE.md:107 reworded verbatim to the containment statement; claude_section.md.j2 and the managed region (232-350) untouched.
  - Manifest regenerated: only the 0.14.0 key moved (5 templates). No version bump, no tag. Ran git fetch --tags + seed_content_store.py --rebuild + gen_template_manifest.py --release-gate clean (orphan-free).
  - Fixed 8 pre-existing tests asserting the old @-path/squad_path shape (test_claude_code_backend, test_a_skill_body_appearing_after_init, test_greeting_skill_generation, test_memory_skill_generation, test_memory_skill_migration, test_skill_migration x2, test_role_body_content_generation, test_init_then_migrate rewritten to assert fetch-command resolution instead of dangling paths) and allowlisted _STARTUP_COMMAND_TEMPLATES in the mutable-state guard.
  - Drove it live: sq init on a scratch squad, read .claude/agents/architect.md and .claude/skills/squads/SKILL.md by hand — no filesystem path anywhere, sq role architect show and sq skill squads show both resolve. sq sync on this repo touched exactly the expected surface (10 agent pointers, 11 skill pointers, 9 role bodies, CLAUDE.md invariant 5 only).
  - Gates clean: pyright, ruff check, ruff format --check, sq check. tests/meta (258) + cli/integration/service/unit (4092 passed, 2 skipped) all green.
  - Left for the architect/tech-lead: whether/who folds the agents_md/role_entry.md.j2 + skill_entry.md.j2 deletion into a task — not done here per this task's explicit instruction not to delete.
- [2026-08-26T11:12:27Z] Pierre Chat:
  - The role definition loads before memory and the board: an agent should know its own job before reading its notebook, the board and its queues. The pointer currently runs the startup set first and fetches the definition after.
- [2026-08-26T11:16:29Z] Elias Python:
  - Operator-side resolution of the agents_md orphan-template conflict I flagged: delete, not strip. Verified orphaning myself first (no render call, agents_section.md.j2 includes only workflow.md.j2, no call site names either file) — confirmed reachable-nowhere, then deleted role_entry.md.j2 and skill_entry.md.j2. Fixed the now-stale '26 bundled templates' count to 24 in gen_template_manifest.py and its meta test docstring.
  - Manifest: 0.14.0 entry went 29 to 27 keys (the two deleted templates dropped from that entry's key set only, no historic version touched). Rebuild dropped the 2 newly-orphaned blobs (89 to 87), release gate clean and orphan-free.
- [2026-08-26T11:16:30Z] Elias Python:
  - Reordered pointer_agent.md.j2 per operator ruling: identity, then the definition-fetch command (sq role <slug> show), then the slug-bound startup set — the decision's priority list was misread as a running order. Reworded connective prose ('Load your full role definition' / 'Then, at the start of a run:'). pointer_skill.md.j2 unchanged (fetch command only). claude_section.md.j2 checked and left untouched — its 'Start of a run' section never claimed an order relative to role-definition loading, only its own Impersonation-scenario line does, and that already reads definition-then-act.
  - Manifest: only the 0.14.0 entry moved (pointer_agent.md.j2's hash). Rebuild dropped 1 newly-orphaned blob (87 to 86 — wait verify), release gate clean and orphan-free.
- [2026-08-26T11:16:40Z] Elias Python:
  - Correction to my last comment: the blob count after the reorder's rebuild is 87 (unchanged from the deletion rebuild) — the new reordered pointer_agent.md.j2 blob was inserted (88), then the rebuild dropped the 1 now-orphaned pre-reorder blob, landing back at 87. Release gate: orphan-free, 414 index references over 87 stored blobs.
<!-- sq:discussion:end -->
