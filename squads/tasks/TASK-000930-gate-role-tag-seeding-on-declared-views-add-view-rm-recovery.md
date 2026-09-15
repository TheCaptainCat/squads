---
id: TASK-930
sequence_id: 930
type: task
title: Gate role tag seeding on declared views, add view rm recovery
status: Done
parent: FEAT-906
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
- REV-926:addresses
subentities:
- local_id: ST1
  title: Gate _create_core's role tag seed on spec.views (F12)
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: Add sq role <slug> view add|rm <name>
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST3
  title: Add sq skill <slug> view add|rm <name>
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST4
  title: Fix sq role show's empty-body hint under a dropped view (F16)
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST5
  title: Fix sq skill show's empty-body hint under a dropped view (F16)
  status: Done
  assignee: python-dev
  story: US2
created_at: '2026-09-08T13:52:16Z'
updated_at: '2026-09-10T09:40:27Z'
---
<!-- sq:body -->
## Scope

Fixes REV-926 F12 and F16, and closes F5's remaining gap: the sanctioned recovery ADR-880's
second amendment names (`view rm`) is missing from the two addressing groups that need it most.

### F12 — `_create_core` still seeds a role's placement tag unconditionally

`ServiceCore._create_core` (`src/squads/_services/_base.py`, the `if item_type == ROSTER_ROLE:`
block) writes `sq:view:role_definition` into a new role's `sq:body` with no
`ROLE_DEFINITION_VIEW_NAME in self.spec.views` check — the same one-line condition
`MaintenanceMixin._repair_body_tag` already applies (`_services/_maintenance.py`, the three
`self.spec.views` gates added for F5). Under a spec that has dropped `role_definition`,
`sq role activate <slug>` mints a fresh dangling tag — a fresh `sq check` error — every time.

Fix: gate the block on the same condition the repair-time classifier uses. No new helper
required beyond importing what F5's fix already added; reuse the check verbatim so the two
writers can never drift apart again (this is the same "two writers must agree" debt F7/F12
already trace).

**Acceptance, driven exactly as the reviewer reproduced it:** on a synced squad whose
`.overrides/workflow.toml` drops `role_definition` via `[selected].views`, `sq role activate`
on a fresh role adds **no** `sq check` finding — before the fix, each activation adds one;
after, the count stays flat across repeated activations. Also confirm the untouched path is
unchanged: with `role_definition` declared, a newly activated role's body still carries the
tag exactly as before.

### The recovery: `view add`/`view rm` on `sq role` and `sq skill`

F5's gate (already Verified) correctly stops *re-seeding* a dangling tag, but a role or system
skill whose body already carries one — from before this fix, or from any future spec edit that
drops a view out from under an already-tagged item — has no command that can clear it. There is
no `view` verb on either addressing group (`sq role <slug>`: show/regen/rm/status/set-default;
`sq skill <slug>`: show/regen/rm/status), no `body` verb (role) or a `body` verb that refuses
the write (skill, for a system slug), and hand-editing the `.md` file is against this project's
own convention. ADR-880's second amendment names `view rm` explicitly as "the recovery path for
precisely this state" and rules it deliberately ungated for that reason. Roster items are the
one item family whose addressing group never exposed it.

This is a mechanical CLI-wiring task, not new design: `ServiceCore.insert_view`/`remove_view`
(`_services/_views.py`) are already item-type-agnostic — they take a bare `item_id` and do the
same marker-safe edit for any item. `_cli/_items.py::_cmd_view` is the exact pattern to mirror
(a two-command `view` sub-Typer calling the same two service methods) — copy its shape into
`_cli/_role.py` and `_cli/_skill.py`'s own Typer apps, addressed through each group's existing
slug/ID/number resolution (`resolve_agent_addr`), not through `_cli/_items.py`'s generic
per-type group.

Land it as `sq role <slug|id|n> view add|rm <name>` and `sq skill <slug|id|n> view add|rm <name>`
— same verb names, same output shape, same idempotent/no-op semantics as the generic group.

### F16 — the empty-body hint names `sq sync` where the F5 gate makes it a no-op

Under a dropped view, F5's gate correctly leaves a role's or system skill's body empty and
untagged — the accepted quiet state, per ADR-880's problem-2 ruling. `_cli/_role.py`'s empty
hint is a single hardcoded string; `_cli/_skill.py`'s already distinguishes "type dropped"
(`orphaned_skill_item_type`) from "not synced yet" but has no third branch for "the *view* this
body would render is not declared" (as opposed to the *item type* a skill documents being
undeclared — two different conditions, only one of which the skill hint currently names).

Fix: give both hints a branch for "the relevant view name is not declared in `self.spec.views`"
(role: `ROLE_DEFINITION_VIEW_NAME`; system skill: `SYSTEM_SKILL_VIEW_NAMES[slug]`; per-item-type
skill: `ITEM_SKILL_VIEW_NAME`) that says so plainly and does **not** point at `sq sync` — the
one command proven not to help there. Once `view rm` (above) exists, the message can name it as
the way to accept the state: an already-tagged body says "this tag names a dropped view, run
`view rm <name>` to clear it"; an untagged body under a dropped view says the view isn't
declared and there's nothing to run.

**Acceptance:** under a dropped `role_definition`/system-skill/per-type-skill view, the empty
hint text no longer says "run `sq sync`". Under a *declared* view with a genuine sync-pending
state, the hint is unchanged from today.

## Testing

Falsify every new and changed test both directions (revert the fix, confirm red; restore,
confirm green) and report both.

Test selection: grep each changed name (`ROLE_DEFINITION_VIEW_NAME`, `insert_view`,
`remove_view`, `_create_core`, the two hint strings, `orphaned_skill_item_type`) across
`tests/`, plus the unconditional floor — `tests/meta`, `tests/integration`, `tests/cli` — since
this touches `_cli/`. Note the board's line-wrap warning: a zero-hit grep on any of these names
is not trustworthy on its own; scan with internal whitespace collapsed and validate the search
against a known positive (a pre-fix build, or the string as it appears today) before trusting a
zero.

No docstring or comment claiming test coverage that doesn't exist, and none asserting a property
nothing in the code enforces.

## Refs

Implements ADR-880 (the second amendment's `view rm` ruling and the third-writer gap F7/F12
name). Addresses REV-926 F12 and F16.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 930 add-subtask "<title>"`; track with `sq task 930 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Gate _create_core's role tag seed on spec.views (F12)

<!-- sq:subtask:ST1:body -->
Add the same 'ROLE_DEFINITION_VIEW_NAME in self.spec.views' condition MaintenanceMixin._repair_body_tag already uses to _create_core's 'if item_type == ROSTER_ROLE:' block in _services/_base.py. Drive the reviewer's exact repro: drop role_definition via [selected].views, then repeatedly sq role activate — no new sq check finding, before or after this fix's regression control.

Done. Gated the same replace_section call on ROLE_DEFINITION_VIEW_NAME in self.spec.views — declared -> tag as before; dropped -> overwrites the template's static tag with empty body (the third writer, role.md.j2, needed no separate change since this call overwrites it unconditionally). Driven: repeated sq role activate under a dropped view adds no new sq check findings.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add sq role <slug> view add|rm <name>

<!-- sq:subtask:ST2:body -->
Mirror _cli/_items.py::_cmd_view's shape into _cli/_role.py's own Typer app, calling the existing item-type-agnostic svc.insert_view/remove_view. Address through the group's own slug/ID/number resolution, not the generic per-type group.

Done. Driven end to end including view rm clearing an already-tagged corpus body left by pre-fix _create_core (sq check error -> clean).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Add sq skill <slug> view add|rm <name>

<!-- sq:subtask:ST3:body -->
Same pattern as the role subtask, in _cli/_skill.py. Covers system skills and per-item-type skills alike — svc.insert_view/remove_view take a bare item_id and don't distinguish.

Done. Same pattern, driven the same way.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Fix sq role show's empty-body hint under a dropped view (F16)

<!-- sq:subtask:ST4:body -->
Branch on ROLE_DEFINITION_VIEW_NAME in self.spec.views before falling back to the 'run sq sync' hint; a dropped view gets a message naming the state plainly (and, once the view-verb subtask lands, the view rm remedy for an already-tagged body).

Done. Declared+pending-sync path unchanged; dropped-view path names the view and points at view rm instead of sq sync.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Fix sq skill show's empty-body hint under a dropped view (F16)

<!-- sq:subtask:ST5:body -->
Extend the existing dropped_type branch with a sibling check for the relevant view name (SYSTEM_SKILL_VIEW_NAMES[slug] or ITEM_SKILL_VIEW_NAME) not being in self.spec.views — distinct from orphaned_skill_item_type's 'type dropped' case, which already has its own message.

Done. Third branch added; dropped-item-type precedence over dropped-view preserved and driven.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-08T14:18:48Z] Elias Python:
  - F12/F16 fixed, view add/rm exposed on both roster groups. Details:
    
    **Gate (F12) and all three writers.** `_create_core`'s `replace_section` call is now
    `markers.open_marker(...) if ROLE_DEFINITION_VIEW_NAME in self.spec.views else ""` — same
    condition as `_repair_body_tag`'s classifier. The template (`agents/role.md.j2`) — the third
    writer F7 named — needed no separate gate: it always writes the static tag, but `_create_core`
    unconditionally overwrites that same body region afterward, so gating that one call is
    authoritative regardless of what the template rendered. Verified by reading the render order,
    not assumed. Reviewer's exact repro driven: dropped `role_definition`, repeated `sq role
    activate` — finding count flat at 1 (was growing +1/activation pre-fix, confirmed by reverting
    and re-running). Untouched path (declared view) unchanged — tag seeded exactly as before,
    `sq check` clean.
    
    **`view add`/`view rm`** on `sq role <addr>` and `sq skill <addr>`, mirroring
    `_cli/_items.py::_cmd_view` over the existing `insert_view`/`remove_view`. Driven on both
    groups including the case that matters: a role/skill body already carrying a dangling tag from
    before a view was dropped — `view rm` clears it, `sq check` goes error -> clean, no automatic
    sweep involved (operator-invoked only, per doctrine). `view add` proven idempotent and refuses
    an undeclared name. Both groups' `--help`/docstring/epilog updated to list the verb.
    
    **F16.** Empty-body hint on `sq role show`/`sq skill show` now distinguishes: view declared +
    genuinely pending sync -> unchanged "run `sq sync`"; view undeclared -> names the view, says
    sync can't help, points at `view rm` as the remedy for a body that already carries the tag
    (general guidance, not a false claim about the item in front of it — its body is empty, so
    there's nothing to remove on THAT item). Dropped-item-type branch (existing, `sq-<type>`
    skills) still takes precedence when both conditions hold — driven with `sq-guide` under both
    `guide` and `item_skill` dropped. Two states distinguished, matches the acceptance list.
    
    **Falsification, both directions, all three new/changed test files** (12 CLI view-verb tests +
    8 CLI hint tests + 3 service tests): every test passes with the fix, reverting the relevant
    source file (`git stash` on `_base.py` or `_role.py`+`_skill.py`) reddens exactly the tests
    that exercise the reverted behavior, restoring turns them green again. Full detail + which
    tests reddened on which revert is in the sq comment below this one isn't needed — ran it live,
    reported in chat to Catherine.
    
    **Selection**: grep for `ROLE_DEFINITION_VIEW_NAME`, `insert_view`, `remove_view`,
    `SYSTEM_SKILL_VIEW_NAMES`, `ITEM_SKILL_VIEW_NAME`, `is_system_skill`,
    `item_type_for_skill_slug`, `_create_core` across tests/, union with the unconditional floor
    (tests/meta, tests/integration, tests/cli) plus the sibling F5 tests — 2117 passed, 7 skipped
    (slow, excluded by design). Zero-hit names (`orphaned_skill_item_type`) validated against a
    known positive via the scratchpad's whitespace-collapsed scanner before trusting the zero.
    
    **Gates**: pyright/ruff check/ruff format clean project-wide. One pre-existing E501 in
    `_services/_maintenance.py` from a concurrent edit outside my surface (not touched by me,
    verified via `git status`). `sq check` clean on this squad.
    
    **Coordinator note**: a stray ADR reference in two of my own comments was flagged mid-task and
    fixed (both source comments rewritten to state the property instead of citing the record); a
    stray ADR reference in a test docstring I'd just written was caught by the same gate and fixed
    before this handoff — `tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py`
    now passes clean.
    
    @tech-lead ready for review.
- [2026-09-08T14:18:56Z] Elias Python:
  - Correction to the falsification paragraph above (typo/garble): every test in the 3 new/changed test files was falsified directly — reverted the relevant source file, confirmed each affected test went red, restored, confirmed green. Details in this session's transcript, not a separate file.
<!-- sq:discussion:end -->
