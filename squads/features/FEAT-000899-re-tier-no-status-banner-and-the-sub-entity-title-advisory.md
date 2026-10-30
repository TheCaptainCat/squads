---
id: FEAT-899
sequence_id: 899
type: feature
title: Re-tier no_status_banner and the sub-entity title advisory
status: Done
parent: EPIC-540
author: product-owner
refs:
- ADR-864:implements
- FEAT-898:depends-on
- MILE-934:targets
- FEAT-901
description: Move two always-on members to catalog-only, with this project selecting
  both in its own override
subentities:
- local_id: US1
  title: Move no_status_banner from floor to catalog-only
  status: Done
- local_id: US2
  title: Move the sub-entity title advisory from the work bundle to catalog-only
  status: Done
- local_id: US3
  title: This project selects both, at today's strength, by override
  status: Done
- local_id: US4
  title: As an adopter upgrading, I want the behaviour change documented
  status: Done
created_at: '2026-09-03T09:02:32Z'
updated_at: '2026-10-12T06:20:46Z'
priority: low
---
<!-- sq:body -->
## Why

Two members of the always-on check set fail the tiering test ADR-864 sets for the whole
catalog (*can a competent squad be in this state on purpose, indefinitely?*), and neither can be
subtracted by an adopter:

- **`no_status_banner`** sits in the floor (`COMMON_CORE`). This project's house convention
  (frontmatter is the source of status truth, no `STATUS:`/`## Status` prose) ships as a
  universal defect every squad inherits. A team whose ADR template has carried a `## Status`
  heading for a decade gets a permanent, un-subtractable warning.
- **`subentity_title_max`** sits in the `work` category bundle, not the floor. Its threshold is
  already a declared, per-type parameter (`subentity_title_max:<n>`, delivered by FEAT-898), but
  the member itself is bundled for every `work` type and the bundled default of 120 characters is
  a module constant every squad inherits when it names no number. A bundle cannot be subtracted
  from either, so relocating within bundles would not help.

Neither rule is wrong for *us*. Both stay fully enforced by this project's own spec once
re-tiered.

## Scope

- Remove `no_status_banner` from the floor and `subentity_title_max` from the `work` bundle, so
  both are catalog-only: effective for a type only when that type's `validators` list names it.
- The create-time title advisory that `add-<kind>` prints follows the same selection: a type that
  does not select `subentity_title_max` gets no advisory, and a type that does gets it at the
  number it selected.
- Keep the member's mechanism, message and default level unchanged. A bare
  `subentity_title_max` selection keeps resolving to the bundled default of 120.
- This project selects both on its own types, at today's effective strength, in a **project
  override** (`.overrides/workflow.toml`) -- not in the bundled spec, which ships to every adopter
  and would defeat the re-tiering. This project has no override file today, so this feature
  introduces one. Selection is per type: there is no squad-wide selection surface for per-item
  checks.

## Out of scope

Any change to the selection grammar itself, to a member's default level, or to the other
members of the floor and bundles.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 899 add-story "As a <role>, I want … so that …"`; track with `sq feature 899 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Move no_status_banner from floor to catalog-only

<!-- sq:story:US1:body -->
As an adopter whose document conventions carry a '## Status' heading or similar, I want no_status_banner off the floor and available as a catalog-only selection, so a house convention we don't share doesn't warn on every record I own.

Acceptance:
- no_status_banner is removed from COMMON_CORE (the floor); it is in no category bundle either (a bundle cannot be subtracted from, so relocating it into one would not fix this).
- On a squad whose spec selects nothing, an item whose body opens with a '## Status' heading or a 'STATUS:' line produces no finding from sq check.
- On the same squad, once a type's validators list names no_status_banner, that type's item with such a body produces the same finding, with the same message and level, as today; naming it with an @error level suffix still works.
- It remains a valid catalog member; an unknown-name refusal is not raised for it.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Move the sub-entity title advisory from the work bundle to catalog-only

<!-- sq:story:US2:body -->
As an adopter, I want the sub-entity title-length advisory off the bundle and available catalog-only with its own declared threshold, so I'm not stuck with squads' own number.

Acceptance:
- subentity_title_max is removed from the work category bundle; it is effective for a type only when that type's validators list names it.
- Naming it with a number (subentity_title_max:<n>) uses that number for sq check; naming it bare uses the bundled default of 120. The message and level are unchanged.
- On a type that does not select it, a story/subtask/finding title over 120 characters produces no finding from sq check and no title advisory from the add-<kind> verb.
- On a type that does select it, add-<kind> prints its create-time advisory at exactly the number sq check uses: a title one character over the threshold triggers both, a title at the threshold triggers neither.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — This project selects both, at today's strength, by override

<!-- sq:story:US3:body -->
As this project, I want both re-tiered members selected in our own override at their current effective strength, so re-tiering demotes neither rule for us -- it is the difference between a policy we hold and a defect we assert on every adopter's behalf.

Acceptance:
- The selection lives in this project's own .overrides/workflow.toml, not in the bundled spec; a fresh sq init of a new squad does not select either member.
- That override selects no_status_banner on every type that ran it before (every type in the bundled spec) and subentity_title_max:120 on every work-category type, and keeps each type's other bundled validators (replacing a type's validators list without the splat form drops them).
- A bare sq check on this repo reports the same issues before and after the change lands.
- sq workflow lint and sq override list run clean with the new override present.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an adopter upgrading, I want the behaviour change documented

<!-- sq:story:US4:body -->
As an adopter upgrading, I want the behaviour change described, so I know the two warnings stop by default and how to get them back.

Acceptance (authored by the tech writer): the override reference's validators section and the release notes state that no_status_banner and subentity_title_max are catalog-only, show the one-line selection that restores each, and say that an existing squad needs no migration. Adopter-facing text carries no item IDs and no build-process narration.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T15:35:10Z] `product-owner` Nina Product:
  - 2026-10-09 readiness pass: checked against ADR-864 and the engine as it stands. Corrected stale premise (subentity_title_max sits in the work bundle, not the floor; its threshold is already a declared param from FEAT-898); the create-time advisory now follows selection; own-spec selection moved from the bundled spec to a project override (no override file exists today); rewrote acceptance; added US4 (docs). Moved to Ready.
- [2026-10-09T17:04:03Z] `op-pierre` Pierre Chat:
  - 2026-10-09: yes, this project's own validator selections go in a project override (squads/.overrides/workflow.toml), the first one in this repo. Same answer for FEAT-901.
- [2026-10-12T05:32:17Z] `qa` Mara Tester:
  - QA of stories 1 to 3, driven as an adopter with the dev build (HEAD 4b23b04c plus uncommitted tree) against the released 0.15.0 tool, in scratch squads and in a scratch COPY of this repository's squads/, .squads.toml, .claude and CLAUDE.md. Nothing was run against the repository's own squad except board writes with the released tool. Exit codes read from the bare command.
    
    - US1 (verified): fresh `sq init` squad selects nothing. Seven types (feature, bug, decision, guide, epic, milestone, contract) x body shapes `## Status`, `### Status`, `STATUS:`, `**Status:**`, plus a `STATUS:` description, a mid-body mention and no body: released tool 35 findings, dev build 0 (exit 0). Naming `no_status_banner` bare on all seven: `sq check --json` byte-identical to the released tool and to the released baseline. `no_status_banner@error` on bug: error level, exit 3, same as released. `no_status_banner:5` refused at load (takes no param), exit 3, `sq workflow lint` exit 1; an unknown name is refused too; the bare name is accepted.
    - US2 (verified): unselected, lengths 119/120/121 on add-story, add-subtask and add-finding: no advisory and no finding. Selected bare (120), with `:80` (79/80/81, and 121), `:80@error`, bare `@error`: the advisory appears exactly at threshold+1 and never at or under it, and `sq check` reports exactly those titles with the same threshold in the message. `@error` gives check exit 3; add-<kind> still exits 0 (the dev build and the released tool agree on that, driven on a squad selecting `subentity_title_max:80@error`). `add-story --json` carries `title_advisory` only when selected (key absent when unselected).
    - US3 (verified): on the copy of this repository, `sq check --json` is identical between the dev build and the released tool, both as copied (0 findings) and after planting offenders with the released tool (banners on epic, feature, bug, decision, guide, task; 121-char titles on a story, a subtask and a finding; a 120-char story title stays quiet): 9 findings, byte-identical, and identical to the released tool on the same copy with `.overrides/` removed. With the override removed the dev build reports 0. `sq workflow lint` exit 0, `sq override list` exit 0 (state `current`). `create epic --parent FEAT-...` and `--parent EPIC-...` are still refused with the dev build and the released tool (exit 1). `sq sync` on the copy writes the same files as the released tool and is a no-op the second time.
    - Upgrade path (verified): a squad built with the released tool carrying 10 banner and 3 title findings: the dev build reports "no issues" (exit 0). `sq sync` changes nothing; `sq repair` rewrites only the index order and appends one reflog line, identical to what the released tool does, and a second `repair` and `sync` change only the reflog. Adding the repository's override file brings all 13 findings back, `sq check --json` byte-identical to the released tool's.
    - Observation (not filed, for @manager to judge): `sq import` prints its warnings in a different order when both checks are selected. The set is identical (sorted outputs equal); for the same item, the dev build prints "US1 body is unwritten" before "body opens with a status/lifecycle banner", where the released tool prints the banner first. The order follows the type's effective validator list, which now appends the selected names after the bundle. `sq check` output is unaffected (it sorts). Reproduction: scratch squad with this repository's override, import a feature with a `## Status` body and an add-story of 121 characters, diff against the released tool.
    - Not covered: roster types (role, skill, operator) banner path on the board (no verb sets their description), `[categories]` level overrides, TUI and VS Code, story 4 (documentation) left as is.
- [2026-10-12T05:32:22Z] `qa` Mara Tester:
  - Correction to the QA comment above: the upgrade-path squad carried 8 banner and 3 title findings (11 in all, not 10 and 13).
- [2026-10-12T06:20:42Z] `manager` Catherine Manager:
  - Closing under the operator's standing delegation for reviewed, verified, non-visual work: all four stories Done, TASK-996 and TASK-997 Done, REV-998 Approved at 4b23b04c, QA verified stories 1 to 3 against the merged build and the released tool, docs and changelog committed. BUG-999 (import warning order) is the one side effect found, tracked on its own.
<!-- sq:discussion:end -->
