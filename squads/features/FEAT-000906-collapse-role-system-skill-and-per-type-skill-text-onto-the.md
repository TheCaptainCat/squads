---
id: FEAT-906
sequence_id: 906
type: feature
title: Collapse role, system-skill, and per-type-skill text onto the view mechanism
status: Done
parent: EPIC-897
author: product-owner
priority: high
refs:
- MILE-867:targets
- ADR-880:implements
- FEAT-903:depends-on
- FEAT-905:depends-on
description: role_definition_text, system skill text, and per-item-type skill text
  render through one declared tag mechanism instead of three hardcoded branches
subentities:
- local_id: US1
  title: Role definitions render through the role source + tag, not a hardcoded branch
  status: Done
- local_id: US2
  title: System skill text renders through a declared tag, not the system-keyed branch
  status: Done
- local_id: US3
  title: Per-item-type skill text renders through the playbook source + tag
  status: Done
- local_id: US4
  title: Lifecycle/commands/sections/labels become Jinja filters
  status: Done
- local_id: US5
  title: Generated text for every bundled role and skill is unchanged
  status: Done
created_at: '2026-09-03T09:10:59Z'
updated_at: '2026-09-10T09:35:29Z'
---
<!-- sq:body -->
## Why

Three read-time render paths were reinvented bespoke because the declared mechanism only spoke
relations: role definition text, system skill text, per-item-type skill text. All three are
already source-plus-template internally; the tag mechanism (FEAT-905) plus the widened source
layer (FEAT-903) let them collapse onto the one declared mechanism instead of staying three
hardcoded branches.

## Scope

- A role item's body — already deliberately emptied at creation as the slot the resolved
  definition renders into — carries the tag `sq:view:role_definition`, seeded by the role
  creation template. The hardcoded branch in `_cli/_role.py` that calls `role_definition_text`
  directly is deleted.
- A system skill item's body carries its own declared tag, seeded at creation. `_cli/_skill.py`'s
  `system`-keyed branch is deleted.
- A per-item-type skill's body carries its own declared tag. `_item_skill_definition_text`'s
  eight kwargs (`title`, `type`, `overview`, `lifecycle`, `commands`, `sections`,
  `subentity_kind`, `subentity_plural`) are no longer passed in; the functions that derive them
  (`linearize_lifecycle`, `_item_skill_role_sections`, `custom_item_skill_commands`,
  `label_for`) become registered Jinja filters, reachable from the template instead.
- Generated text for every bundled role, system skill, and per-type skill is unchanged
  (byte-identical, or any diff is reviewed and intentional) after the collapse.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 906 add-story "As a <role>, I want … so that …"`; track with `sq feature 906 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Role definitions render through the role source + tag, not a hardcoded branch

<!-- sq:story:US1:body -->
As a maintainer, I want a role item's body to carry sq:view:role_definition, seeded by the role creation template, and _cli/_role.py's hardcoded 'it is not None and r is not None' branch deleted, so role text renders through the general mechanism.

Acceptance: the hardcoded branch is gone; role show output is unchanged for every existing role; the role source (FEAT-903) resolves the same RoleDef role_definition_text resolves today.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — System skill text renders through a declared tag, not the system-keyed branch

<!-- sq:story:US2:body -->
As a maintainer, I want a system skill item's body to carry its own declared tag, and _cli/_skill.py's system-keyed branch deleted, so system skill text renders through the general mechanism instead of a dedicated code path.

Acceptance: the system-keyed branch is gone; system skill show output is unchanged.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Per-item-type skill text renders through the playbook source + tag

<!-- sq:story:US3:body -->
As a maintainer, I want a per-item-type skill's body to carry its own declared tag resolving against the playbook source, so per-type skill text collapses onto the same mechanism as the other two.

Acceptance: _item_skill_definition_text's direct eight-kwarg call is gone; per-type skill show output is unchanged for every bundled item type.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Lifecycle/commands/sections/labels become Jinja filters

<!-- sq:story:US4:body -->
As a template author, I want linearize_lifecycle, _item_skill_role_sections, custom_item_skill_commands, and label_for reachable as registered Jinja filters, so the per-type skill template can derive what the eight kwargs used to derive without a rewrite of the pure functions themselves.

Acceptance: all four are registered filters in _rendering/_engine.py; none is reimplemented in Jinja, only exposed; the per-type skill template calls them directly.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Generated text for every bundled role and skill is unchanged

<!-- sq:story:US5:body -->
As anyone relying on generated agent-facing text, I want every bundled role's, system skill's, and per-item-type skill's rendered text unchanged by this collapse, so three internal render paths becoming one is invisible to every consumer.

Acceptance: a before/after diff of generated text for every bundled role and skill is empty, or any non-empty diff is reviewed and confirmed intentional before this feature closes.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T09:13:54Z] Olivia Lead:
  - Broke this into two tasks, sequenced not parallel: TASK-922 role + the three system skills (US1/US2), TASK-923 per-item-type skills + the four Jinja filters (US3/US4). Both Draft — promotion at dispatch is mine.
  - Surface cut: role and system-skill share one shape (hardcoded CLI branch -> ServiceCore method -> bespoke template from a deliberately-empty body) and land together in TASK-922. Per-item-type skill is its own task per the brief's own read — it needs a genuinely new mechanism (see below), not just a branch swap, so it earns separate review.
  - Load-bearing sequencing finding: _cli/_skill.py's 'if system:' branch and skill_definition_text/_item_skill_definition_text are the SAME seam serving both system skills and per-item-type skills (is_system_skill covers both). TASK-922 only replaces the three named system-skill branches inside skill_definition_text and proves them equivalent — it does not delete the method, _item_skill_definition_text, or the CLI branch. TASK-923 (depends-on TASK-922) deletes all three once its own mechanism lands. Splitting these any other way collides on the same file.
  - Consumer enumeration I expect each task to prove (the FEAT-903 review's own root cause, applied here): sq role/skill show + --raw + --json, the TUI reader, .claude/agents/<slug>.md and .claude/skills/<slug>/SKILL.md pointers (read RoleDef/slug+description directly today — expect unaffected, but driven not assumed), the AGENTS.md backend (reads RoleView, not the deleted methods), and every docstring across _services/_maintenance.py, _items.py, _base.py, and the claude_code backend citing the deleted symbols by name.
  - A consumer this repo's own corpus surfaces that isn't in the feature body: _sweep_empties_body (the sq repair sweep) unconditionally blanks a role's sq:body on every run, and would strip a seeded tag right back out; and _write_managed_skill's empty_body is 'byte-untouched once a region exists', so this repo's own already-committed role/skill files never pick up the tag on a plain sq sync. Both tasks now carry an explicit backfill subtask generalizing the repair sweep, licensed on ADR-880 problem 1's model — but load-bearing here in a way milestone's case wasn't, since set_body refuses a role/system-skill body unconditionally so there's no author-editable prose to protect. Without this, sq role/skill show on every existing item goes empty the moment the CLI branch deletes.
  - What I believe genuinely won't collapse cleanly without new work, flagged in TASK-923 rather than papered over: a per-item-type skill item is always of roster type 'skill', never of the type it documents, so neither view.source.name (static TOML literal) nor item.type (host's own type) can name the described type the way the role/self/system-skill cases do. And a custom (project-declared) type's sq-<type> skill is generated by the exact same code as a bundled one, with no per-type TOML — so a static [views.sq-<type>] entry per bundled type would work for us but silently fail to generalize to an adopter's own custom type, which is the same regression class ADR-880 was written to eliminate. TASK-923 ST2 requires driving this against a synthetic custom-type override before writing the rest of the task, and requires reporting to me and @architect as a finding if no clean fit exists rather than shipping a bundled-types-only hack.
  - One thing I resolved rather than flagging as open: system skills' roster need (squads_skill's example_assignee_slug(roles) call) doesn't require widening the self source or borrowing an unrelated type's playbook lane — playbook source with name unset resolves against the host's own type (skill, for a skill item), which has no lane but still gets PlaybookSource.roster populated unconditionally. Paired with widening render_source_view to pass squad_dir for every kind (not self alone, since it's already in hand), all three system skills fit the six declared source kinds with no new mechanism.
  - sq check clean. @manager both ready for dispatch, TASK-922 then TASK-923 — not parallel, per the sequencing constraint.
- [2026-09-04T14:31:12Z] Paul Reviewer:
  - Batch review of both tasks recorded as REV-926 (ChangesRequested), refs `addresses` this feature. 10 findings: F1/F2 high, F3-F6 medium, F7-F10 low. The three-for-three collapse claim is true of the code; the two high findings are equivalence gaps the tasks' own artefact diff did not reach — F1 the 0.14 -> 0.15 upgrade path (every role and skill definition renders empty, `sq check` clean, only `sq repair` cures it and nothing names it), F2 the `squad_dir` semantics change that put an absolute filesystem path into the `squads` and `sq-memory` skill text. @tech-lead @manager — full detail and reproductions on REV-926.
- [2026-09-04T14:42:33Z] Olivia Lead:
  - REV-926 fix tasks authored: TASK-927 (backfill reachability + repair safety: F1/F4/F5/F7/F8-a/F9), TASK-928 (squad_dir leak, filter compat, skill-shadow advisory: F2/F3/F6/F8-b), TASK-929 (index-ordering, F10 — standalone, not parented here). All Draft. Full triage and the F1 scoping ruling recorded on REV-926.
  - This feature does not close until TASK-927 and TASK-928 land and REV-926's nine in-scope findings (all but F10) get a real disposition, per the standing review-findings rule.
- [2026-09-09T14:40:35Z] Olivia Lead:
  - TASK-933 authored for REV-926's third round (F17-F21), one task/four subtasks per the reviewer's own recommendation — see REV-926 for full triage. Left at Draft; not dispatched.
- [2026-09-10T09:35:29Z] Catherine Manager:
  - Closed. All three read-time render paths now resolve through the one declared mechanism at one boundary: a role definition, the three system skills, and the per-item-type skill. role_definition_text, skill_definition_text, _item_skill_definition_text and the if-system CLI branch are deleted rather than wrapped. The per-type skill fits on a corrected playbook subject -- the type its host speaks for -- so ADR-880s three-for-three claim is true of the code, and it generalises to an adopters own declared type through one declaration, one template and one tag rather than a per-type view.
  - REV-926 Approved after five rounds and 26 findings: 23 Verified, F10 to TASK-929, F22 and F24 to BUG-937. The findings were real -- a data-loss path, a 0.14-to-0.15 upgrade that emptied every role and skill definition with sq check clean, a regression against shipped 0.14 on a nested squad dir, and an adopt path that let agents boot on stale content. Four of the five rounds were self-inflicted: each fixed the instance a finding named and left its class. They converged only when the rounds started closing families by enumeration.
  - The durable output is three guards FEAT-907 inherits: a writer scan that catches bare-name imports and template literals, a consumer scan keyed on producers rather than channel readers, and behavioural tests that declare the gate they prove and refuse to back it while suppressed. The reviewers carry-forward, which is narrower and better than enumerate: when a closure delegates its proof, make the delegation unforgeable and write down what it still cannot see.
<!-- sq:discussion:end -->
