---
id: REV-967
sequence_id: 967
type: review
title: 'View placement range: positions, roster, migration'
status: Approved
author: reviewer
refs:
- FEAT-948
- TASK-942
description: Independent review of TASK-942's committed range under FEAT-948
subentities:
- local_id: F1
  title: Migration reclaim wipes a later-declared type's authored skill
  status: Fixed
  severity: high
- local_id: F2
  title: Routine-inserted blank lines become prose on the next write
  status: Fixed
  severity: medium
- local_id: F3
  title: Region-less roster file crashes repair, sync and migrate
  status: Fixed
  severity: medium
- local_id: F4
  title: Roster refusal names no concrete type, file or path
  status: Fixed
  severity: low
- local_id: F5
  title: Migration manual and workflow.md give opposite remedies
  status: Fixed
  severity: low
- local_id: F6
  title: View-name and position validators accept a trailing newline
  status: Fixed
  severity: low
- local_id: F7
  title: 'Four messages hand-spell the sq:view: shape'
  status: Fixed
  severity: low
- local_id: F8
  title: Verb and guard messages misstate what happened
  status: Fixed
  severity: low
- local_id: F9
  title: Duplicate-tag remedy is a no-op; duplicate reported twice
  status: Fixed
  severity: medium
- local_id: F10
  title: Creation under a dropped view mints a dangling tag
  status: Fixed
  severity: medium
- local_id: F11
  title: Named remedy strands legacy prose beside a roster tag
  status: Fixed
  severity: medium
- local_id: F12
  title: Mirrored spacing departs from ADR-880's ruled blank line
  status: Fixed
  severity: medium
- local_id: F13
  title: Whitespace-only lines defeat invertibility; fuzz never draws them
  status: Fixed
  severity: low
- local_id: F14
  title: Region recovery orphans heading-led prose outside sq:body
  status: Fixed
  severity: medium
- local_id: F15
  title: Four-step remedy deletes a runbook the migration preserved
  status: Fixed
  severity: medium
- local_id: F16
  title: Shadowed-skill save command captures the rendered guidance
  status: Fixed
  severity: low
- local_id: F17
  title: Disabled tag mid-paragraph renders as a paragraph break
  status: Fixed
  severity: low
- local_id: F18
  title: Remedy comment says the reclaim skips authored skills
  status: Fixed
  severity: low
created_at: '2026-09-28T18:33:55Z'
updated_at: '2026-09-29T09:28:12Z'
---
<!-- sq:body -->
## Scope

The committed range `1e317941~1..HEAD` on release/0.15, limited to `src`, `tests`, `docs` and `CHANGELOG.md`. It delivers TASK-942 under FEAT-948: positioned views, disabled tags, one re-placement routine for every body write, the roster refusal, the widened 0.14→0.15 reclaim, and removal of the dead skip channel. The rules come from ADR-880's seventh amendment §1–§9 and the TASK-942 subtask specs.

## Method

Every claim in a finding is labelled **driven** (reproduced on a scratch squad or through the pure function), **read** (checked against the code) or **inferred**.

- Scratch squads only: fresh `sq init`; a squad initialised with released v0.13.1 and one with v0.14.0 (via `uvx --from git+file://…@<tag>`), each migrated with this tree; copies of the v0_1, v0_5, v0_7, v0_11 and v0_14 fixtures; and an `sq adopt` of a pre-0.14 squad folder.
- Body shapes crossed with tag positions, through `place_view_tags` directly: 11 positions squared, 12 prose shapes, 4 edits, append on and off, and 5 tag sets, checking idempotence and exactly-once. Then through `body`, `--append`, `sq import`, `create`, `view add` and `view disable`.
- Roster host kinds (role, `squads`, `greeting`, `sq-memory`, `sq-bug`, custom skill, and a later-declared type's skill) crossed with every write verb.
- Every command that a refusal, hint, check finding or migration text names was run on the state that produced it.

## Checked, fine

- Gates: pyright reports 0 errors; ruff check and format are clean; tests/meta plus the targeted placement, check, migration, corpus and CLI tests give 1495 passed and 7 skipped.
- Milestone replace and append, the importer's body op (replace and append), the roster refusal with and without `--force` for each host kind, and the conflicting-pair refusal with its `view add` remedy all behave as ruled.
- The documented hand-authoring route in docs/overrides.md (drop `squads_skill`, write, sync and repair keep the prose, then `view disable` clears check) works end to end.
- `after()` positions anchor as ruled. A single view is idempotent in every fuzzed shape. The exactly-once condition held in every fuzzed shape. There is no module-level mutable state, and ViewSpec.required is gone.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 967 add-finding "…" --severity medium`; track with `sq review 967 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Migration reclaim wipes a later-declared type's authored skill

<!-- sq:finding:F1:body -->
**Driven.** The 0.14→0.15 reclaim replaces any marker-free, non-empty body that `roster_body_view_name` classifies as a per-item-type skill. That classification uses the *current* spec, so it also takes in a custom skill whose slug matches a project type declared after the skill was written. The reclaim treats that skill's authored runbook as legacy rendering and deletes it. There is no skip row and no warning, and git is the only way back.

This is the shape `item_skill_shadowed` exists to report, and the standing sweep keeps it (`test_admitted_roster_shapes_survive_convergence.py::test_a_project_declared_types_stale_sq_widget_round_trip` pins that). The migration is the one writer that destroys it.

**Repro:**
1. `uvx --from git+file://…@v0.14.0 sq init`
2. `sq skill add sq-widget --desc "our widget runbook"`, then `sq skill sq-widget body -m "Hand-written widget runbook: step 1, step 2."`
3. Declare `[items.widget]` (prefix WID, folder widgets, lifecycle guide, category records) in `squads/.overrides/workflow.toml`, then `sq sync`. At 0.14 the prose survives and `sq check` is clean. Commit.
4. With this tree, `sq migrate up` reports `0.15.0 … — 1 changed`, and `sq:body` of `SKILL-000021-sq-widget.md` now holds only the `item_skill` tag. The prose is gone.

**Read:** `_v0_14_to_v0_15.py::_reclaim_legacy_roster_bodies`. The only filters are `view_name is None`, empty/already-tagged, and `find_markers(current)`. Nothing distinguishes text that 0.13.1 rendered from text an author wrote.

**Suggested direction:** restrict the reclaim to a body that is provably a past rendering. For example, compare against what the released writer would have rendered, or limit it to bundled types and the three system slugs. Otherwise skip it and report it, the way marker-shaped content is skipped. Add a migration test for this exact shape.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-28T19:12:49Z] Elias Python:
  - Reclaim now excludes any per-item-type skill whose type is project-declared (_is_provably_legacy_type in _v0_14_to_v0_15.py) — its declaration date is unrecoverable from disk, so its skill's content is never provably legacy and is skipped and reported instead. Reproduced the exact repro (skill add sq-widget + authored body + later [items.widget] + migrate up on a fresh v0.14.0 squad): SKILL is now skipped by id, body byte-unchanged, sq check reports item_skill_shadowed instead of silent loss.
- [2026-09-28T22:51:31Z] Paul Reviewer:
  - Verified the exact repro, still Open. On a real v0.14.0 squad (`uvx … @v0.14.0`), running `skill add sq-widget` with prose, then declaring `[items.widget]` and migrating, now skips SKILL-21 and leaves the prose byte-unchanged. Fixed for that shape (fc54db1d). New repro for the same loss via a type that squads bundled only from 0.14:
    1. `uvx --from git+file://…@v0.13.1 sq init`, then `sq skill add sq-milestone --desc "our milestone runbook"` and `sq skill sq-milestone body -m "Hand-written milestone runbook: cut the branch, tag, announce."`. `sq check` is clean. (`milestone` and `contract` do not exist at 0.13.1, so this is an ordinary custom skill.)
    2. Run `sq migrate up` with v0.14.0 only: the prose survives.
    3. Run `sq migrate up` with HEAD: `SKILL-000019-sq-milestone.md` now holds only the `item_skill` tag. The prose is gone, with no skip row.
    
    Read: `_BUNDLED_TYPES_AT_0_14` includes `contract` and `milestone`, and `_is_provably_legacy_type`'s docstring premise ("every squad … was created no earlier than some release … which already bundled every type in `_BUNDLED_TYPES_AT_0_14`") is false. A squad created at 0.8–0.13.1 had neither type, so its `sq-contract`/`sq-milestone` could be authored. The provable set is the types bundled at the corpus's *origin* release. At minimum that means excluding types introduced in 0.14. Better: key on whether the body equals what the released writer rendered.
- [2026-09-28T23:26:59Z] Elias Python:
  - Replaced the type-bundled-ness heuristic with a real provenance signal: seed_bundled_skills stamps a per-item-type skill's extra with only {slug}, add_skill always also stamps description/when_to_use/allowed_tools (even empty) -- verified against the v0_14 fixture and real v0.13.1/v0.14.0 uvx installs. _is_provably_template_seeded reads that presence directly; the old bundled-type set is gone. Reproduced red->green on a fresh v0.13.1->v0.14.0->this-tree chain (sq-milestone runbook now survives the 0.15 migration, skipped and reported) and via pytest falsification (stub true: 5 tests fail, incl. both new regression tests; restored: all pass). tests/fixtures/corpus/v0_15 confirmed unchanged (its own skills are genuinely bare-extra tool-seeded; test_migration_corpus.py passes unmodified).
- [2026-09-29T00:04:38Z] Paul Reviewer:
  - Re-verified against HEAD 1ab4d170, still Open. The review's own chain passes: a `sq skill add sq-milestone` at v0.13.1, then v0.14.0, then HEAD skips SKILL-19 and keeps its prose, because its `extra` carries `description`/`when_to_use`/`allowed_tools`. But the provenance signal is unsound for a skill made by another creation route. New repro:
    1. At v0.13.1, `sq import` one event: `{"op":"create","type":"skill","title":"sq-contract","slug":"sq-contract","body":"Imported contract runbook prose.","as":"manager"}`. The created file has **no `extra` at all**, and `sq check` is clean. (`contract` is not a type at 0.13.1, so this is an ordinary custom skill.)
    2. `sq migrate up` with v0.14.0: the prose survives.
    3. `sq migrate up` with HEAD: `SKILL-000019-sq-contract.md` now holds only the `item_skill` tag. The prose is gone, and there is no skip row.
    
    Read: `_is_provably_template_seeded` returns True whenever the `add_skill` keys are *absent*, so a skill created by the importer, by `sq adopt` of a hand-written file, or by hand (none of which stamps those keys) reads as tool-seeded. Absence is not proof. The signal needs a positive marker of tool seeding, or a body that matches what the released writer rendered.
- [2026-09-29T07:51:27Z] Elias Python:
  - Per op-pierre's ruling: removed the provenance check and the project-declared-type skip entirely.
    The 0.15 reclaim now overwrites every marker-free, non-empty per-item-type skill body onto its
    tag unconditionally, same as a role/system skill always has -- no distinction between a genuine
    0.13.1 rendering and an author's own runbook. Marker-shaped and unreadable-file skips are
    unchanged (structural, not provenance).
    
    Deleted _is_provably_template_seeded and both tests that pinned the skip
    (test_a_hand_authored_skill_matching_a_bundled_type_is_skipped_not_wiped and its legacy-shaped
    sibling). The widget and sq-milestone runbook tests now assert the overwrite instead
    (test_a_project_declared_types_skill_is_overwritten_like_any_other,
    test_a_skill_matching_a_type_bundled_after_it_was_written_is_overwritten), consolidating the
    authored/legacy-shaped pairs since there's no longer a distinction to test for.
    
    Reproduced on a real v0.13.1->v0.14.0->this-tree chain: a hand-authored sq-milestone runbook is
    now correctly wiped onto its tag, sq check clean, no skip. Falsified via pytest (stub a skip back
    in for sq-widget/sq-milestone: exactly the 2 new overwrite-asserting tests go red; restored:
    green). tests/fixtures/corpus/v0_15 confirmed unchanged (test_migration_corpus.py passes as-is --
    its own bundled skills were always overwritten either way).
- [2026-09-29T09:16:18Z] Paul Reviewer:
  - Verified against op-pierre's ruling at HEAD 8042b0f6. On a v0.13.1 → v0.14.0 → HEAD chain, a `sq skill add sq-milestone` runbook, an `sq import`-created `sq-contract`, and the tool-seeded `sq-bug` all end tag-only. The overwrite is reported in the step's count ("— 12 changed"), and `sq migrate chlog v0.14.0..v0.15.0` says plainly that every marker-free per-item-type body is overwritten unconditionally before 1.0. There is no provenance skip; the only skips left are an unreadable file, a missing region and marker-shaped content.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Routine-inserted blank lines become prose on the next write

<!-- sq:finding:F2:body -->
**Driven.** `place_view_tags` puts exactly one blank line on each side of every tag it inserts. Stripping keeps that blank line (`_strip_lone_line` leaves one blank line where a blank line flanked the tag). So once a tag has sat somewhere, its blank lines become part of the author's prose. Three consequences follow, each contradicting ADR-880 seventh amendment §4:

1. **An author's paragraph is split for good.** Set `[views.milestone_rollup] position = "after(^Line one)"`, then `sq milestone 24 body -m $'Line one of a paragraph\nline two of the same paragraph.'`. The tag goes between the two lines. Change the position to `"bottom"` and `sq milestone 24 body --append -m "Appended."`. The body now reads `Line one of a paragraph` / blank line / `line two …`: one paragraph has become two, although §4 says "a tag that moves leaves no stray blank line where it sat".
2. **Placement is not idempotent.** Set `milestone_rollup` to `after(^## Objective)` and a self-sourced `notes` view to `after(^$)`. Then `sq milestone 23 body -m $'## Objective\nShip.'` followed by `view add notes` puts `notes` right under the roll-up, because it matched the blank line the roll-up's insertion created. Repeating the identical `body --force -m $'## Objective\nShip.'` moves `notes` to the bottom. Same prose, different bytes; this breaks §4's "Byte-stable" rule. The pure-function fuzz found 736 non-idempotent cases, all with two views where one view's pattern (`^$`, `\n\n`) matches whitespace the other's insertion added. No single-view case failed.
3. **The first replace over an untouched scaffold is refused.** With `position = "after(^_TODO: what counts)"` (a line inside the bundled Scope-boundary paragraph), `sq create milestone "Scaf"` then `sq milestone 25 body -m "First real prose."` exits 1: "already has a body (12 lines)". The scaffold's prose no longer equals `pristine_body` once the split paragraph has a blank line in it. §4 says "its first replace over the unwritten scaffold needs no `--force`".

**Read:** `_views.py::_build_segments` joins atoms with a blank line; `_sections.py::_strip_lone_line` keeps a flanking blank line; `_items.py::_body_mutate` compares prose with `.strip()` only at the edges.

**Suggested direction:** strip should remove the blank lines the routine itself adds, reversing its own insertion, so that strip(place(p)) == p for any prose p. Pin that as a property test over position × prose, plus a two-view idempotence row.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-28T21:15:32Z] Elias Python:
  - Fixed: mirrored insert-side separator (place_view_tags) + made strip_marker_lines run-aware for a chain of tags sharing one cut point (both were needed — the fuzz found the second bug). Round-trip/idempotence proven via 800-case seeded fuzz + table cases; falsified.
- [2026-09-28T22:51:33Z] Paul Reviewer:
  - Verified against HEAD (61a95690). All three repros are clean on a scratch squad: the `after(^Line one)` → `bottom` move closes the paragraph back up exactly; the `## Objective`/`notes after(^$)` rewrite is byte-identical; and the first replace over the scaffold with `after(^_TODO: what counts)` exits 0 without `--force`. My original 7,744-case fuzz now shows 0 failures. Two consequences of the mirrored-spacing fix are filed as F12 and F13.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Region-less roster file crashes repair, sync and migrate

<!-- sq:finding:F3:body -->
**Driven.** A role (or seeded skill) file whose body has no `sq:body` region crashes every maintenance verb with a raw traceback, and the two remedies `sq check` names both refuse:

- `sq repair` → `KeyError: "section 'body' not found"`, from `_converge_body_tag` → `sections.replace_section`, because `current` is `""` for a missing region, so the empty-region branch runs.
- `sq sync` with version drift gives the same traceback.
- `sq migrate up` on a copy of v0_11 with the dev-agent role's body markers removed gives the same traceback from the trailing repair. Exit 1, and no migration completes.
- `sq check` reports `missing seeded view tag … restore it with sq role qa view add role_definition, or disable it with … view disable …`. Both commands fail with "has no sq:body region".

**Read:** the crash itself predates the range (the old `_converge_body_tag` also called `replace_section` on an empty `current`). The range added two false claims on top of it: `_converge_body_tag`'s new docstring says "Never raises", and `_strip_retired_regions` says it has no skip channel because of that. The migration docstring lists "a body with no `sq:body` region (either step)" as a reported skip, but `_reclaim_legacy_roster_bodies` silently `continue`s on it (`current == ""`), and step one is the only one that reports it.

**Repro:** in a scratch squad, delete the `sq:body` marker pair from `ROLE-000005-qa.md`, then run `sq repair`, `sq check`, and `sq role qa view add role_definition`.

**Suggested direction:** guard the missing region in `_converge_body_tag` (leave the file alone, since there is no region to converge) and make the check finding name a remedy that works for a region-less file.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-09-28T21:15:33Z] Elias Python:
  - Fixed: reinstate_absent_body_region recovers a missing sq:body pair when the would-be span is empty-or-tag-only (never guesses at real prose); wired into _converge_body_tag (repair/sync/migrate) and view add/disable (roster hosts only). New sq check finding for the region-entirely-absent shape. Corrected the same false 'reported skip' claim in the 0.14->0.15 reclaim's second step.
- [2026-09-28T22:51:35Z] Paul Reviewer:
  - Verified against HEAD. With the body markers deleted from `ROLE-000005-qa.md`, `sq repair`, `sq role qa view add role_definition` and `sq sync` (drifted) each reinstate the region and leave `sq check` clean. `sq check` names the region-absent shape before recovery. A reinstatement next to headed prose is filed as F14.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Roster refusal names no concrete type, file or path

<!-- sq:finding:F4:body -->
**Driven.** The §8 refusal names the authoring surface, but for skills it does not say where that surface is:

- `sq skill sq-bug body -m x` → "…one validated authoring surface: this type's lane in the playbook overrides." It names neither the type (`bug`) nor the file (`.overrides/playbook.toml`). On a *skill* document, "this type" reads as the skill type. The empty-body hint on `sq skill sq-bug show` has the same wording.
- `sq skill greeting body -m x` → "its `views/greeting_skill.md.j2` view template override". The path is relative to an unstated root (`.overrides/templates/`), and the message does not name `sq override scaffold`, which docs/workflow.md does.
- **The docs sample does not match the output.** docs/workflow.md ("Which bodies take prose") shows `SKILL-20 … sq:view:squads_skill … this type's lane in the playbook overrides`. The real output for `squads` is "the playbook overrides" (driven).
- **Read:** the role branch in `_services/_items.py::_reject_unwritable_body` and `_cli/_role.py::_role_empty_body_hint` hard-code `.overrides/roles.toml` although `_roles/_loader.py::ROLES_OVERRIDE_FILENAME` exists. `skill_authoring_surface` never uses `PLAYBOOK_OVERRIDE_FILENAME`.

**Suggested direction:** name the concrete file and type (for example ``the `[types.bug]` lane in `.overrides/playbook.toml` ``) from the declared constants, and regenerate the docs sample from real output.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-28T22:11:32Z] Elias Python:
  - Fixed: skill_authoring_surface now names the concrete file/type (the [types.<t>] lane in .overrides/playbook.toml, or the .overrides/templates/<path> view-template-override path + sq override scaffold command), using ROLES_OVERRIDE_FILENAME/PLAYBOOK_OVERRIDE_FILENAME/new TEMPLATES_OVERRIDE_DIR constants. Also fixed a real bug this surfaced: _render_body's empty-hint print left the dynamic text unescaped, so Rich silently swallowed the new [types.bug]-shaped text (and, pre-existing, any hint mentioning [selected]) as unrecognized markup.
- [2026-09-28T22:51:36Z] Paul Reviewer:
  - Verified: `sq-bug` names the `[types.bug]` lane in `.overrides/playbook.toml`, `squads` names `.overrides/playbook.toml`, and `greeting` names `.overrides/templates/views/greeting_skill.md.j2` plus `sq override scaffold views/greeting_skill.md.j2`, which runs and creates the file. The docs/workflow.md:1219 sample matches the output. The hint text with brackets renders escaped in `sq skill sq-bug show`.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Migration manual and workflow.md give opposite remedies

<!-- sq:finding:F5:body -->
**Driven.** For a milestone whose tag already sits outside `sq:body`, the two adopter-facing texts give opposite remedies, and the migration's one is false under the new write rule:

- `sq migrate chlog v0.14.0..v0.15.0` (the `MANUAL` in `_v0_14_to_v0_15.py`): "**Do not run `sq milestone <n> view add milestone_rollup`** on one of these … There is nothing to fix here; the tag is present."
- docs/workflow.md ("After `sq migrate up`: seeded views"): "Delete the out-of-region line from the file by hand, then run `sq milestone <n> view add milestone_rollup`." It also says `sq migrate chlog` "prints the migration's own manual steps".

"Nothing to fix" is no longer true, because every body write now inserts an absent seeded view. Driven: move a milestone's tag below `sq:body:end`, run `sq milestone 26 body --append -m "a note"`, and `sq check` reports `duplicate sq:view:milestone_rollup tag (2 copies…)`. BUG-957 covers the underlying out-of-region mechanism and ADR-880 §9 names the duplicate. The new part is that the migration manual tells adopters the state needs nothing.

**Suggested direction:** align `MANUAL` with docs/workflow.md, or point both at BUG-957's eventual ruling, and remove "nothing to fix".
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-28T22:11:34Z] Elias Python:
  - Fixed: the 0.14->0.15 MANUAL no longer says 'nothing to fix here' for an out-of-region milestone tag; it now says what docs/workflow.md already did -- delete the out-of-region line, then view add milestone_rollup -- since every body write now re-inserts an absent seeded tag, making the old advice actively wrong. Docs untouched, per instruction.
- [2026-09-28T22:36:51Z] Elias Python:
  - Follow-up (writer's verification pass): the sq migrate up CLI's own skip line (src/squads/_cli/_migrate.py, separate from the MANUAL text already fixed) still ended 'needs none of this' for an out-of-region milestone tag. Aligned it with the MANUAL/docs remedy (delete the outside line, then view add); validated grep found no other copy of the old wording. Reproduced red-then-green on a v0_14 fixture copy.
- [2026-09-28T22:51:38Z] Paul Reviewer:
  - Verified: "nothing to fix" and "Do not run" are gone from the MANUAL and from the `_cli/_migrate.py` skip line. Both now say to delete the out-of-region line, then `view add`, matching docs/workflow.md.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — View-name and position validators accept a trailing newline

<!-- sq:finding:F6:body -->
**Driven.** The view-name alphabet uses `_BARE_TOML_KEY_RE.match(name)` with `^[A-Za-z0-9_-]+$`, and the position grammar uses `^after\((?P<pattern>.*)\)$`. In Python, `$` also matches just before a trailing newline, so both accept a value ending in `\n`:

```toml
[views."nl\n"]
source = { kind = "self" }

[views.p1]
source = { kind = "self" }
position = "after(x)\n"
```

`sq workflow lint` then says "workflow spec OK", and `sq workflow views` lists `nl` with an empty line under it. The tag for such a view, `sq:view:nl` followed by a newline, falls outside `MARKER_RE`'s class, which is the exact case the alphabet rule exists to refuse (ADR-880 §2).

**Suggested direction:** use `fullmatch` or `\Z` in both, and add the two rows to the load-level table in ST13's tests.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-28T22:11:35Z] Elias Python:
  - Fixed: both _BARE_TOML_KEY_RE and _AFTER_POSITION_RE now use fullmatch instead of match, so a view name or an after() pattern ending in a trailing newline is refused at load, matching the alphabet rule's own intent.
- [2026-09-28T22:51:41Z] Paul Reviewer:
  - Verified: `[views."nl\n"]` and `position = "after(x)\n"` are both refused by `sq workflow lint` (2 errors).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Four messages hand-spell the sq:view: shape

<!-- sq:finding:F7:body -->
**Read.** TASK-942's rules say "The `sq:view:` shape and the `:disabled` suffix are never spelled as literals at a call site". Four new message sites hand-compose the shape instead of calling `markers.open_marker(markers.view_tag(name))`:

- `src/squads/_services/_items.py:554`: `sq:view:{roster_view}`
- `src/squads/_services/_maintenance.py:649`: `<!-- sq:view:{name} -->`
- `src/squads/_services/_maintenance.py:653`: `sq:view:{name}`
- `src/squads/_views.py:932`: `sq:view:{name}`

These sites only display the shape and write nothing, so no output is wrong today. They are the kind of drift the rule exists to prevent, and the writer-site meta test cannot see them because it scans `markers.view_tag(` calls only.

**Repro:** `rg -n 'f"[^"]*sq:view:\{' src/squads --glob '*.py'`
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-09-28T22:11:37Z] Elias Python:
  - Fixed: all five current hand-spelled sq:view:{name} sites (the 4 named plus one my own F11 batch added) now route through markers.open_marker(markers.view_tag(...)) or markers.PREFIX+markers.view_tag(...).
- [2026-09-28T22:51:43Z] Paul Reviewer:
  - Verified: `rg -n 'f"[^"]*sq:view:\{' src/squads --glob '*.py'` finds nothing.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Verb and guard messages misstate what happened

<!-- sq:finding:F8:body -->
**Driven.** Three verb and guard messages describe something other than what happened:

- `sq role qa view disable nope` (a typo, and no such tag exists) prints "view nope disabled in sq:body" and exits 0. It actually *placed* a new disabled tag for an undeclared view. `sq check` stays clean, so nothing ever surfaces the typo, and the intended `role_definition` is still enabled. The verb being ungated is ruled (§3), but the message should say it placed a new tag for an undeclared view.
- The authored-body guard's preview counts the tool's own tag lines as authored lines. On a milestone whose prose is `hello`, blank line, `appended`, a replace without `--force` says "already has a body (5 lines)… (2 more lines)". The two extra lines are the blank line and the roll-up tag. `reject_body_overwrite` is passed `current`, not the tag-stripped prose the decision uses.
- The conflicting-state refusal ("sq:view:milestone_rollup carries both an enabled and a disabled tag…") names no item. On `body` that is merely unhelpful; in a multi-event `sq import` the only locator is the `line N:` prefix.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-09-28T22:11:41Z] Elias Python:
  - Fixed all three: view disable now distinguishes 'placed' (no prior tag) from 'disabled' (turned off or collapsed) via a new view_tag_present pre-check; the overwrite preview passes the tag-stripped prose (current_prose) to reject_body_overwrite instead of the raw, tag-and-all region; the conflicting-state refusal now leads with 'item_type addr:'.
- [2026-09-28T22:51:45Z] Paul Reviewer:
  - Verified: `view disable nope` prints "had no existing tag — placed disabled"; the overwrite preview counts 3 lines for `hello`/blank/`appended`; the conflict refusal leads with "milestone 21:".
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Duplicate-tag remedy is a no-op; duplicate reported twice

<!-- sq:finding:F9:body -->
**Driven.** For a same-state duplicate, `sq check` names `view add` and `view disable` as the ways to "collapse to one", and one of the two is a no-op in each state:

- Two **enabled** copies: `sq milestone 21 view add milestone_rollup` prints "already present, unchanged" and writes nothing. `add_view` returns early when `view_tag_states(...) == {False}`, which duplicates also satisfy. `sq check` keeps reporting the duplicate.
- Two **disabled** copies: `sq milestone 21 view disable milestone_rollup` prints "already disabled, unchanged" for the same reason (`== {True}`).

So the only working remedy for an enabled pair is to disable it, which changes the state the author wanted. The pair can also be collapsed by an unrelated body write. ADR-880 §3 says "a verb that finds its view already in the state it names writes nothing", but a duplicated view is not in the state the verb names, because there is more than one tag.

The same fixture also shows the condition **reported twice**: `duplicate marker sq:view:milestone_rollup` from `_marker_issues` and `duplicate sq:view:milestone_rollup tag (2 copies…)` from `_seeded_view_issues`. ST7 says "Make sure a same-state duplicate is not reported twice (once by each function)", and the `_seeded_view_issues` docstring states the opposite.

**Repro:** in a milestone body, repeat the `sq:view:milestone_rollup` line (scratch squad, hand edit), then run `sq check` and `sq milestone <n> view add milestone_rollup`. Do the same with two `:disabled` copies and `view disable`.

**Suggested direction:** the early return should require exactly one tag (for example `len(parts)==1`, not a set comparison); add a verb × duplicate-state row to the ST10 matrix; drop the second report.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-09-28T19:38:29Z] Elias Python:
  - add_view/disable_view's no-op check now requires exactly one matching tag in the target state (view_tag_settled in _views.py), not a set-of-states comparison that a same-state duplicate also satisfies -- both verbs now genuinely collapse a duplicate via place_view_tags's own force=. sq check's duplicate-by-name report now fires only for a cross-state duplicate (an enabled plus a disabled copy), which _marker_issues cannot see; a same-state duplicate is reported once, by _marker_issues alone. Reproduced both original repros (2 enabled + view add, 2 disabled + view disable) on a scratch squad: single report, remedy places/collapses, sq check clean after.
- [2026-09-28T22:36:50Z] Elias Python:
  - Follow-up (writer's verification pass): a same-state duplicate (two enabled, or two disabled, copies) used to surface only _marker_issues's generic 'duplicate marker ...' with no remedy, unlike the cross-state case. _seeded_view_issues's duplicate condition now covers both shapes (both verbs already collapse a same-state duplicate too), and _marker_issues defers the whole view-tag family to it -- exactly one finding, carrying the real view add/disable remedy. Reproduced red on the pre-follow-up code, green after; both the widened condition and the marker-issues deferral falsified independently.
- [2026-09-28T22:51:47Z] Paul Reviewer:
  - Verified: for two enabled copies, `view add` collapses them; for two disabled copies, `view disable` collapses them. Each duplicate is reported exactly once, by the named remedy line, and check is clean afterwards. A cross-state pair is still refused on a body write, with both remedies named.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Creation under a dropped view mints a dangling tag

<!-- sq:finding:F10:body -->
**Driven.** Creation now runs the routine over the creation template's static text and keeps every tag it finds, including one for a view that is no longer declared. So creating a document under a dropped view writes a dangling enabled tag, and the tool's own write produces a `sq check` error:

- `[selected] views = ["squads_skill","greeting_skill","memory_skill","item_skill"]`, then `sq dev add --tech rust`: `ROLE-000022-rust-dev.md` gets `sq:view:role_definition`, and `sq check` reports `no declared view 'role_definition'` on the new role (exit 3).
- Under the same override, `sq create milestone "M"` gets `sq:view:milestone_rollup`, and `sq milestone 21 show` prints the literal `sq:view:milestone_rollup` to the reader.

For roles this is a regression. Before the range, `_create_core` wrote an empty role body when `role_definition` was undeclared, and `test_role_activation_seeds_no_tag_for_an_undeclared_view.py` pinned that; the test was deleted and replaced by a test pinning the dangling tag. Managed skills still seed nothing for an undeclared view (`_write_managed_skill` gates `body_tag`), so a role and a skill under the same dropped-view shape now behave differently.

ADR-880 §1 says "A view dropped from `[selected]` seeds nothing anywhere". The comment above the call in `_services/_base.py::_create_core` claims this path is "what makes a role activated under a dropped `role_definition` mint no fresh dangling tag", which the new test itself shows is false.

**Suggested direction:** at creation, treat a template's own tags as seeding input filtered by `seeded_view_names`, not as existing document state, or get an explicit ruling that creation may mint a check error. In either case, fix the comment.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-09-28T19:38:41Z] Elias Python:
  - _create_core now strips every view tag from the creation template's own rendered region before running place_view_tags, so a bundled scaffold's hardcoded tag (role_definition in agents/role.md.j2, milestone_rollup in items/milestone.md.j2) is never treated as existing content to preserve -- what survives is decided entirely by seeded_view_names, byte-identical to the template's own copy for a still-declared view and absent for a dropped one. Fixed the false _create_core comment claiming this already worked. One fix point covers every creation path (create, activate_role/dev add/role add, add_skill, add_operator, and the bulk importer's own create op, which all funnel through _create_core); sq adopt never renders a creation template, so it cannot reach this shape. Reproduced both original repros (dev add and create milestone under a dropped view) on a scratch squad: no dangling tag, no check error, no literal tag shown to the reader.
- [2026-09-28T22:51:50Z] Paul Reviewer:
  - Verified: with `role_definition` and `milestone_rollup` dropped, `sq dev add --tech rust` and `sq create milestone` write no tag, `sq check` has no error on either, and `show` prints no literal tag. After the views are restored, check names `view add`.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Named remedy strands legacy prose beside a roster tag

<!-- sq:finding:F11:body -->
**Driven.** When pre-0.14 legacy text reaches 0.15 without the reclaim running, the documented remedy produces a duplicated definition that no `sq` verb can clear. There are two routes in:

1. **`sq adopt` of a pre-0.14 squad folder** (the v0_11 fixture's item folders, no config). Adopt stamps the current schema, so the migration never runs. `sq check` then gives 3 errors (`missing seeded view tag` on `dev-agent`, `greeting`, `squads`), each naming `view add`. The integration test `test_the_bare_verb_strips_a_corpus_already_at_the_current_stamp` pins this gap as expected.
2. **A migration skip for marker-shaped content** (a v0_11 copy with a stray `sq:note` in the role body). Follow docs/workflow.md: remove the marker-shaped content, then `sq role dev-agent view add role_definition`.

Either way, `sq role dev-agent show` then renders the legacy `# Dev Agent` text **and** the live definition. The legacy text cannot be removed: body replace and append are refused on a roster host (§8), repair leaves non-empty regions alone, and the reclaim ran once or never. The only escape is to drop `role_definition` from `[selected]` (which hits every role), write the body, and restore the view. No doc or message says so. docs/workflow.md tells the reader to "take the marker-shaped content out of the body, then run the command the error names", and that leads straight into this state.

**Suggested direction:** give roster hosts a route that clears legacy text, such as a `sq repair` mode or a check remedy that says "remove the text by hand, then view add". Or run the reclaim on adopt too, under its own licence. Either way, the named remedy has to end in a clean document.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-09-28T19:12:57Z] Elias Python:
  - sq check's missing-seeded-view-tag finding now names only view disable, not view add, on a roster host (role/skill) whose body already carries non-empty prose alongside the missing tag -- view add would stack a second, live rendering, view disable renders nothing so the surviving prose stays the document's only rendering. Reproduced both routes (adopt of a v0_11-shaped folder with no config, and a marker-shaped migration skip followed by hand-removing the marker) on scratch squads: sq check now names only view disable, and running it ends with sq check clean and a single rendering, no data loss.
- [2026-09-28T21:15:35Z] Elias Python:
  - Fixed per op-pierre's ruling: sq check + the migration MANUAL now name the full 4-step remedy (drop view, clear text, restore view, view add) with exact filled-in commands, never view-disable-only. Verified end to end for role/system-skill/per-item-type-skill, both the adopt route and the marker-shaped-migration-skip route.
- [2026-09-28T22:51:52Z] Paul Reviewer:
  - Verified against op-pierre's ruling, end to end. `sq check` names the filled-in four-step remedy (drop the view, clear the text, restore it, `view add`), with no `view disable` fallback. I ran each step literally for a role (`echo '{"op": "body", "target": "ROLE-1", …}' | sq import -`), for a system skill (`greeting`) and for a per-item-type skill (`sq-contract`) on an `sq adopt` of pre-0.14 folders, and for the role on the marker-skip migration route. Each ended with `sq check` clean and a single live rendering. One consequence, the remedy telling an author to delete a runbook F1's fix deliberately preserved, is filed as F15.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Mirrored spacing departs from ADR-880's ruled blank line

<!-- sq:finding:F12:body -->
**Driven, and read against the ADR.** To fix F2, the routine now mirrors whatever separator sat at the cut point, so a tag between two lines of a paragraph gets a single newline on each side. ADR-880 seventh amendment §4 still rules the opposite: "A re-inserted tag sits on its own line, with **exactly one blank line** between it and adjacent prose". No commit in `37b92f8a..HEAD` touches the ADR. docs/workflow.md:1162 and the CHANGELOG now describe the mirrored rule, so the code and docs have moved away from a standing ruling. That needs op-pierre and the architect, not a code change on its own.

The ruled blank line exists so a view renders as its own block. Under mirroring it does not. Declare a `notes` view with source `self`, template `Notes view for {{ item.id }}.`, and `position = "after(^Line one)"`, then run `sq milestone 23 body --force -m $'Line one of a paragraph\nline two of the same paragraph.'`:

```
Line one of a paragraph
Notes view for MILE-23.

line two of the same paragraph.
```

That is from `sq milestone 23 show --raw`. In Markdown the view's output merges into the author's first line as one paragraph, and the author's own paragraph is split in two. The bundled `milestone_rollup` only escapes this because its template starts with an ATX heading, which may interrupt a paragraph.

**Suggested direction:** get a ruling. Either amend §4 to the mirrored rule and have `expand_view_tags` pad an expansion into its own block at read time, or keep the ruled blank line and make the strip side invert it, as F2 originally suggested.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-09-29T07:51:50Z] Elias Python:
  - Per op-pierre's ruling: the padding now lives entirely in expand_view_tags (the one read-time
    expansion path) -- stored bytes are never touched, only the rendered output. Each rendered view
    gets a full blank line on either side that borders real prose, never at the body's own edges,
    and never doubled when a neighbour is already blank; a disabled tag (renders nothing) gets no
    padding of its own, so removing it reconnects the prose exactly as if it had never been there.
    
    Checked every render surface: sq show/--raw/--json's body field (same read_body call), the TUI
    reader (calls read_body directly), the VS Code extension (consumes sq show --json's body field
    over the CLI, no separate rendering path) -- and confirmed .claude/ pointer files never carry
    expanded content at all (thin pointers, per the architecture), so they're out of scope entirely.
    
    Reproduced the exact repro (a self-sourced notes view at after(^Line one)): the rendered output
    now reads "Line one of a paragraph", blank line, "Notes view for MILE-21.", blank line, "line
    two...", with the stored bytes still holding the mirrored single-line-break spacing untouched.
    Falsified (stub the padding helper to a no-op): 6 tests go red, including the exact mid-paragraph
    repro; restored: green. Ran the full fast suite (meta+integration+cli+unit+service+tui, 6260
    tests) after fixing the fallout in ~7 pre-existing tests whose assertions assumed the old
    no-padding shape -- all green.
    
    Doc note (not edited): docs/workflow.md's "Where tags go on a body write" section says a tag
    "takes the spacing of the spot it lands in" -- true of the stored bytes, but doesn't mention that
    read-time expansion now pads a rendered view out to a full blank line regardless of that stored
    spacing. Worth a clarifying sentence.
- [2026-09-29T09:16:23Z] Paul Reviewer:
  - Verified per the ruling: the stored body keeps the author's single line break (`Line one…` / tag / `line two…`), and `show --raw` pads the rendered `notes` view with a blank line on each side, so it no longer merges with the prose. ADR-880 §4 is amended to match. One consequence for disabled tags is filed as F17.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Whitespace-only lines defeat invertibility; fuzz never draws them

<!-- sq:finding:F13:body -->
**Driven.** Invertibility, and with it idempotence, fails when a line holding only spaces or tabs sits between two tags. Markdown reads such a line as blank. `strip_marker_lines` treats a run of tags as one chain when only `"\n \t"` lies between them (`result[run_line_end:nstart].strip("\n \t")`), so the whitespace-only line is eaten as tag padding. If that line was the author's paragraph break, two paragraphs merge.

**Repro:** set `[views.milestone_rollup] position = "after(^Intro)"` and a self-sourced `notes` view at `position = "after(^\\s*$)"`. Then run `sq milestone 24 body --file p.md` with `p.md` = `Intro paragraph.\n  \nSecond paragraph.`, then `sq milestone 24 view add notes`, then `sq milestone 24 body --append -m "Third."`. The body now reads `Intro paragraph.` directly followed by `Second paragraph.`: the blank line holding two spaces is gone and the two paragraphs are one. A trailing whitespace-only line after the last heading also makes a two-view placement non-idempotent. In my 6,000-case fuzz adding whitespace-only lines, 3+ newline runs and CRLF, 197 cases fail invertibility or move-invariance. None of them changes a non-whitespace character.

**Why the committed fuzz misses it:** `tests/unit/test_place_view_tags_fuzz_idempotence_and_invertibility.py` draws separators only from `["\n", "\n\n"]` and lines from four plain words. No whitespace-only line, no 3+ blank run, no CRLF ever reaches it. The table cases don't cover these either.

**Suggested direction:** treat a whitespace-only line as prose, not padding, in the chain test, and widen the fuzz alphabet (whitespace-only lines, `\n\n\n`, `\r\n`, whitespace-matching positions).
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-09-29T07:52:02Z] Elias Python:
  - A line holding only spaces/tabs now counts as blank for both placement (_local_separator, via a
    new _blank_run_length helper) and the chain-detection check in strip_marker_lines (changed
    .strip("\n \t") to .strip("\n") so a whitespace-only line between two hand-placed tags breaks
    their chain instead of being eaten as padding). Also fixed a related double-counting bug in
    _build_segments: it was stripping only bare newlines from each prose slice's edge, leaving a
    whitespace-only line's own text attached to the slice while _local_separator independently added
    its own gap on top, producing an extra blank line. Deliberately did not make _strip_lone_line
    itself whitespace-aware -- reproduced live that combining it with the chain-break fix
    double-counts a shared whitespace-only line from both sides when two tags are chain-broken
    around it; the original pure-newline counting there, combined with the chain-break fix alone,
    round-trips correctly.
    
    Widened the committed fuzz with a new, dedicated property (rather than folding into the general
    random fuzz, which can't tell a touched separator from an untouched one without re-deriving the
    routine's own cut-point logic): a view anchored at after(^\s*$) lands exactly on a whitespace-only
    line between two prose lines, round-trips to a plain blank line, and repeats byte-for-byte. Added
    a second regression test for the chain-break case directly. Falsified both (stub the
    _build_segments fix: 200 cases red; stub the chain-detection fix: the dedicated chain test red);
    restored: green, 1001 passed. Ran the full fast suite (6260 tests) alongside F12 -- green.
- [2026-09-29T09:16:30Z] Paul Reviewer:
  - Verified per the amended §4, which treats a whitespace-only line as a blank line. The F13 repro (`Intro paragraph.` / two-space line / `Second paragraph.`) keeps the two paragraphs separate after `view add` and `--append`. The whitespace line is normalised to an empty line, which the ADR allows, and my wider fuzz shows 0 non-whitespace changes. Recorded as a note, not a finding: a position whose pattern matches whitespace characters themselves (for example `after(^ +$)`) loses its match once the line is normalised, so such a tag moves on the next write (for example `A\n\t\n\nb c\n \nx`). That breaks §4's byte-stable wording, but only for that contrived pattern shape.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Region recovery orphans heading-led prose outside sq:body

<!-- sq:finding:F14:body -->
**Driven.** `reinstate_absent_body_region` accepts a remainder that starts with a Markdown heading, on the grounds that it is "that region's heading (`## Discussion`)". An author's own body that starts with a heading has the same shape. The recovery then puts an empty `sq:body` pair *in front of* that prose. The prose ends up permanently outside the region, invisible to `show` and to every writer, and `sq check` goes silent.

**Repro:** copy `tests/fixtures/corpus/v0_11` and delete only the `sq:body` marker pair from `agents/roles/ROLE-000001-dev-agent.md`. Its legacy body starts with `# Dev Agent`. Run `sq migrate up`: it skips ROLE-1, and the trailing repair reinstates the region. The file now reads `sq:body` / the role tag / `sq:body:end`, then `# Dev Agent`, a blank line, `A minimal developer role for corpus testing.`, then `## Discussion`. `sq check` reports nothing for the file. The same thing happens on any role or skill whose authored text starts with a heading, through `sq repair`, `sq sync`, `view add` or `view disable`.

This is the out-of-region shape BUG-957 tracks, but produced by the tool itself. The new part is that a recovery path writes it and that its check finding disappears. Before recovery, `_absent_body_region_issues` names `view add` as the fix for this file, and that command creates the state.

**Suggested direction:** accept only the next *known* region's own shape (the discussion heading followed by its `sq:discussion` marker, or nothing), never an arbitrary heading. Report anything else as needing manual recovery.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-09-28T23:45:32Z] Elias Python:
  - reinstate_absent_body_region now requires the span between the tag-run and the next real marker to collapse to exactly one heading line immediately followed by the sq:discussion open marker -- not just 'starts with #, and a discussion marker appears somewhere after'. The v0_11 dev-agent shape (heading-led prose running on for several lines before the file's real Discussion region) previously passed that looser check and got wrapped in front of, orphaning the prose; now it is correctly refused and left exactly as it was, and check reports the region-less-file finding plainly instead of going silent. Verified live: copied v0_11, deleted the role's sq:body markers, ran migrate up/repair/sync -- no crash, no data loss, sq check names the manual-recovery finding. Table-driven unit tests added (prose after frontmatter, heading-led with/without a real discussion region, tag-only, empty, unrelated marker, differing heading depth/text) and falsified (loosening the check back to the old behavior: exactly the 3 refusal tests go red; restored: 15/15 green).
- [2026-09-28T23:57:41Z] Elias Python:
  - Follow-up (writer): when the region is entirely absent, _seeded_view_issues now suppresses its own 'missing seeded view tag' report for that host, leaving _absent_body_region_issues as the sole finding -- its remedy is the only one that can ever work there (view add/disable both require an existing region). Reproduced both shapes (unsafe stray text: view add exited 1 before the fix; safe bare-tag: same working remedy, just duplicated), fixed, falsified (stub the suppression off: the unsafe-shape test goes red; restored: 16/16 green).
- [2026-09-29T00:04:42Z] Paul Reviewer:
  - Verified against HEAD (a38ddeea, 1ab4d170). On a v0_11 copy with only the `sq:body` pair deleted from `ROLE-000001-dev-agent.md` (body starts with `# Dev Agent`), `sq migrate up` skips ROLE-1, the trailing repair leaves the file untouched, and `sq check` reports the missing region, saying to "recover the file by hand". Neither `view add` nor `repair` reinstates it. I also attacked a one-line heading body, prose after the tag run, and prose before the tag run: `after` is either multi-line or unheaded, and each is refused.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Four-step remedy deletes a runbook the migration preserved

<!-- sq:finding:F15:body -->
**Driven.** Since F1's fix, the migration deliberately leaves a project-declared type's `sq-<type>` skill untouched, because its prose may be an author's real runbook. `sq check` then gives that file the F11 four-step remedy, whose step 2 deletes the runbook: `sq skill sq-widget body -m "" --force`. The same file also carries an `item_skill_shadowed` warning with a different remedy ("take the type out … clear **or move** the prose, then restore the type"). So one document has two remedies that disagree, and the error, which is the one a reader acts on, is the destructive one.

**Repro (real v0.14.0 install):** `uvx … @v0.14.0 sq init`, `sq skill add sq-widget`, `sq skill sq-widget body -m "Hand-written widget runbook: step 1, step 2."`, declare `[items.widget]`, `sq sync`, commit. Then with HEAD: `sq migrate up` (SKILL-21 skipped, prose kept), then `sq check`:
- `error … missing seeded view tag … (2) clear the text with sq skill sq-widget body -m "" --force …`
- `warn SKILL-21: documents declared type 'widget' but carries authored content … clear or move the prose …`

The same pairing shows on an adopted `sq-contract` (v0_14 folders). There the text really is legacy, but the two remedies still disagree about which spec edit comes first (drop the view, or drop the type).

**Suggested direction:** when a per-item-type skill's prose can be authored (a project-declared type, which is exactly the case the migration now skips), name "move the prose to a custom skill first" before any clearing step, and make the error and the shadowed warning give one consistent sequence. Minor, same file: the warning prints `'widget''s`, a doubled quote.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-09-28T23:27:06Z] Elias Python:
  - sq check's missing-seeded-view-tag remedy and item_skill_shadowed's warning now agree: for a per-item-type skill whose slug still documents a currently-declared type (the exact shape F1's skip can leave), both name moving the prose to a new sq skill add <new-slug> first, then clearing the original -- never a clear-first sequence. clear_roster_body_cmd moved to _views.py (shared, no import cycle between _maintenance.py and _validators.py) so both compose the identical clear command. Also fixed the doubled-quote bug (repr-then-possessive gave 'widget''s). Verified end to end on two scratch squads: the v0.14.0 sq-widget/project-declared-type repro, and an sq adopt of v0_14-shaped folders (sq-contract, genuinely legacy) -- both converge to sq check clean with the moved prose intact under its new slug. Regression tests added and falsified (stub the old remedy text: exactly the 2 new tests fail; restored: green).
- [2026-09-29T00:04:44Z] Paul Reviewer:
  - Verified the preservation part, but one step fails as written, so this stays Open. On the real v0.14.0 widget squad after the HEAD migration, `sq check` names the five steps, and running them literally preserves the runbook and ends with check clean for `sq-widget`. Step 1's read command is wrong, though: "read it with `sq skill sq-widget show --raw`". `--raw` only drops markdown rendering; stdout still starts with the `show` panel (id/slug/kind/status/file box), so `show --raw > moved.md` then `sq skill widget-runbook body --file moved.md` writes the panel into the new skill's body. Driven: `sq skill widget-runbook show --raw` now begins with the nested `SKILL-21 sq-widget … kind: system (template-owned)` box. `item_skill_shadowed` names the same command. It needs a command that prints the body alone.
- [2026-09-29T00:18:30Z] Elias Python:
  - Reopened root cause: `show --raw`'s stdout leads with the metadata panel box, so step 1's
    `> moved.md` captured the panel, not just the prose. Neither `--raw` nor the existing `--json`
    gave exact-bytes body-only output for a skill (an ordinary item's own `show --json` already has
    this via `build_item_json`'s `body` key -- a skill's builder lacked it). Added the missing
    `body` key to `sq skill <slug> show --json` (the same `read_body` call `--raw` already prints,
    now isolated with nothing else on stdout) and repointed both remedy sites at
    `sq skill <slug> show --json | jq -r .body > <path>`.
    
    Ran steps 1-5 literally, copy-pasted, on a fresh v0.14.0-origin widget squad: the saved file is
    byte-identical to the original stored prose (only difference is jq -r's own trailing newline,
    confirmed by reading the moved skill back through the same show --json | jq -r .body and getting
    an identical diff), sq check ends clean, and the generated guidance renders. Regenerated the
    skill_show golden (one new key, nothing else changed) and added a regression test pinning the
    new field equals read_body(); falsified by removing the key (exactly 2 tests go red: the new
    regression test and the golden); restored, all green.
    
    docs/workflow.md:521's sample `sq check` output block still shows the stale `show --raw` command
    in its literal text -- now false, flagged for the writer, not touched here (no docs edits this
    batch).
- [2026-09-29T00:25:46Z] Paul Reviewer:
  - Verified Fixed at HEAD 611f6988 (b6a983b4). I migrated the v0.14.0-origin widget squad with HEAD and ran the five steps exactly as `sq check` prints them: `sq skill add widget-runbook`; `sq skill sq-widget show --json | jq -r .body > moved.md`; `body --file moved.md`; drop `item_skill`; `body -m "" --force`; restore; `view add item_skill`. The moved skill's `sq:body` region is byte-identical to the original runbook's region at the committed 0.14 base (`cmp`), and `sq check` is clean for both skills. A richer body (backticks, `$HOME`, brackets, quotes, a tab, a fenced block, non-ASCII) also round-trips unchanged through `show --json | jq -r .body` and `body --file`. The same command in `item_skill_shadowed`'s tag-present variant is a separate problem, filed as F16.
- [2026-09-29T00:25:47Z] Paul Reviewer:
  - On `jq` in a check remedy (a judgement, not a finding): acceptable. The docs already depend on it (docs/recipes.md, docs/faq.md, and the `sq renumber` hint in `_cli/_main.py`), `jq -r` keeps the text exact apart from one trailing newline that `body --file` normalises, and the step is a one-time manual recovery, not a routine path. Two caveats worth a sentence in docs/workflow.md: `jq` is not a squads dependency and is absent on stock Windows/macOS; and on Windows PowerShell 5.1, `>` writes UTF-16, which `body --file` would then read wrongly (inferred, not driven). A jq-free way to print only the body (for example a `--body` or `--field body` flag on `show`) would remove both.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — Shadowed-skill save command captures the rendered guidance

<!-- sq:finding:F16:body -->
**Driven.** `item_skill_shadowed` has two variants. The tag-present one names the same save command as the five-step remedy: `sq skill <slug> show --json | jq -r .body > <path>`. But `show --json`'s `body` is `read_body`, which is **tag-expanded**. When the `item_skill` tag sits beside the prose, which is exactly this variant's shape, the saved file holds the author's prose **plus the whole rendered generated guidance** for the type. Following the remedy writes that guidance into the new custom skill as authored text: a stale second copy that never updates.

**Repro (scratch squad):**
1. `sq skill add sq-gizmo --desc g`, then `sq skill sq-gizmo body -m "Gizmo runbook prose."`, then `sq skill sq-gizmo view add item_skill`.
2. Declare `[items.gizmo]` (prefix GIZ, folder gizmos, lifecycle guide, category records) and run `sq sync`.
3. `sq check` warns: "documents declared type 'gizmo' and carries prose beside its item_skill tag … save the current text with `sq skill sq-gizmo show --json | jq -r .body > <path>` …".
4. `sq skill sq-gizmo show --json | jq -r .body` prints `Gizmo runbook prose.`, a blank line, then `# Gizmo items` and the rest of the generated guidance.

The tag-missing variant (the five-step error) is unaffected, because there is no tag to expand (verified byte-identical on F15).

**Suggested direction:** give the remedy a way to save the *stored* prose with view tags stripped, not the rendered body. That could be a `show --json` field for the raw region or a `show --raw-body` flag. Or name that command in both variants. Note that b6a983b4's own comment calls `body` "the one exact-bytes read of the stored body" while also saying it is tag-expanded, which is a contradiction.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-09-29T07:51:37Z] Elias Python:
  - Per op-pierre's ruling: removed the jq/show-json read step from both remedies entirely. The
    item_skill_shadowed warning and the seeded-view-issues check error now both say only: move the
    prose into its own skill with sq skill add <new-slug>, then drop the type from [selected], clear
    the original, restore, and view add -- no automated capture step named. Kept the body key on
    skill show --json (still consistent with every other item type's show --json). Fixed the
    self-contradictory comment/docstring that called it "the one exact-bytes read of the stored
    body" while also saying it is tag-expanded -- now just states the tag-expansion fact plainly.
    
    Verified end to end on a scratch squad (the gizmo repro): the warning names no read command at
    all now; ran the corrected 4-step sequence (move manually, drop, clear, restore) and confirmed sq
    check ends clean with the prose intact under its new skill.
- [2026-09-29T09:16:35Z] Paul Reviewer:
  - Verified: the tag-present `item_skill_shadowed` warning on `sq-gizmo` now says "move the prose first (`sq skill add <new-slug>`)", with no jq or save command, and `rg -n jq src/squads` finds only the unrelated `sq renumber` hint.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Disabled tag mid-paragraph renders as a paragraph break

<!-- sq:finding:F17:body -->
**Driven.** Since the F12 ruling, the stored body keeps the author's single line break around a tag. A **disabled** tag between two lines of one paragraph therefore sits on its own line inside the paragraph. At read time it expands to nothing but leaves its line behind as an empty line, and that empty line splits the author's paragraph in the rendered output. ADR-880 §3 says a disabled tag "renders nothing".

**Repro:** declare a self-sourced `notes` view with `position = "after(^Line one)"` and a template override. Run `sq milestone 21 body -m $'Line one of a paragraph\nline two of the same paragraph.'`, then `sq milestone 21 view add notes`, then `sq milestone 21 view disable notes`. Stored: `Line one of a paragraph` / the disabled tag / `line two of the same paragraph.` `sq milestone 21 show --raw` and `show --json | jq -r .body` give `Line one of a paragraph`, an empty line, `line two of the same paragraph.`: two paragraphs where the author wrote one.

**Suggested direction:** at the read boundary, remove a disabled tag the way `strip_marker_lines` does, taking its line and applying the same separator rule, instead of substituting an empty string in place.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-09-29T09:27:57Z] Paul Reviewer:
  - Verified at f053083e. The original repro now renders `Line one…` directly followed by `line two…` (`show --raw` and `show --json`). I also drove the shapes through `show --raw`, and each renders as if the tag were absent: mid-paragraph → `A line\nB line`; its own paragraph → `A para\n\nB para`; body start and body end → `A para`; sharing a line → `A B` and `A text\nB line`; beside an enabled view → `A para`, the padded view, `B para`; two disabled tags mid-paragraph → `A line\nB line`; two disabled tags between paragraphs → `A para\n\nB para`; disabled-only body → empty.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Remedy comment says the reclaim skips authored skills

<!-- sq:finding:F18:body -->
**Read.** `src/squads/_services/_maintenance.py:601-605` (in `_seeded_view_issues`) says the reclaim "may have skipped this file precisely because its prose could be an author's real runbook". Under the F1 ruling the reclaim never skips on that ground: it overwrites every marker-free per-item-type body. The branch is still reachable (for example an `sq adopt` of pre-0.14 folders, or a type declared after 0.15), so the message it guards stays right; only the reason comment is now false. Repro: `sed -n 600,606p src/squads/_services/_maintenance.py`, compared against `_v0_14_to_v0_15.py`'s "no further test applied".
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-09-29T09:28:05Z] Paul Reviewer:
  - Verified: `_services/_maintenance.py:601-603` now says the reclaim never ran against such prose (an `sq adopt`, or a type declared later), which matches the unconditional reclaim.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-28T18:36:29Z] Paul Reviewer:
  - @manager @tech-lead REV-967: independent review of TASK-942's committed range under FEAT-948. Recommended verdict: **ChangesRequested**. The review is left at Requested; the approval transition is not mine to take.
    
    - **High (1).** F1: the 0.14→0.15 reclaim silently deletes an authored custom skill's body when its slug matches a project type declared before the migration. Driven on a real v0.14.0 squad.
    - **Medium (6).** F2: blank lines the placement routine inserts become prose. This splits an author's paragraph for good, makes placement non-idempotent with two views, and refuses the first replace over an untouched scaffold. F3: a region-less roster file crashes repair, sync and migrate with a raw KeyError, and both remedies check names refuse. F9: for a same-state duplicate, one of the two named collapse remedies is a no-op, and the duplicate is reported twice. F10: creating a document under a dropped view mints a dangling tag (a regression for roles). F11: the named remedy for legacy text that reaches 0.15 without the reclaim (adopt, or a marker-shaped skip) leaves a duplicated definition that no verb can clear.
    - **Low (4).** F4: surface text is vague, and the docs sample does not match the output. F5: the migration manual and workflow.md contradict each other. F6: validators accept a trailing newline. F7: four messages hand-spell `sq:view:`. F8: three messages misstate what happened.
    - Checked fine: gates (pyright 0, ruff clean, 1495 targeted and meta tests passed), milestone and importer body writes, the roster refusal for each host kind, the documented hand-authoring route, the conflicting-pair remedy, and single-view idempotence and exactly-once across the fuzz.
- [2026-09-28T19:45:35Z] Pierre Chat:
  - F11: do the full remedy now. A roster body holding legacy text beside a missing tag names the remedy that converges to the live definition: drop the view from [selected], clear the text (sq skill <slug> body for a skill, sq import for a role), restore the view, then view add. It replaces the view disable fallback.
- [2026-09-28T22:52:35Z] Paul Reviewer:
  - @manager @python-dev Re-review of REV-967 against HEAD 5897ba45, with every repro re-run on scratch squads (F1 on a real v0.14.0 install). Status is now ChangesRequested.
    - **Verified Fixed (10):** F2–F11. F11 matches op-pierre's four-step ruling end to end for a role, a system skill and a per-item-type skill, by both the adopt route and the marker-skip route.
    - **Reopened (1):** F1. The widget repro is fixed, but a custom `sq-milestone`/`sq-contract` written at 0.13.1 is still wiped by the 0.15 reclaim, because `_BUNDLED_TYPES_AT_0_14` counts two types that did not exist before 0.14.
    - **New (4):** F12 (medium): the mirrored spacing contradicts ADR-880 §4's ruled blank line, and a view's output merges into the author's paragraph; this needs a ruling. F13 (low): whitespace-only lines defeat invertibility, and the committed fuzz never draws them. F14 (medium): region recovery puts an empty region in front of prose that starts with a heading, orphaning the prose and silencing check. F15 (medium): the four-step remedy tells authors to delete the runbook F1's fix preserves, and it disagrees with `item_skill_shadowed`.
    - Gates: pyright 0, ruff clean, 3514 targeted/meta/unit/cli tests passed with 7 skipped. `sq check` is clean.
- [2026-09-29T00:05:02Z] Paul Reviewer:
  - @manager @python-dev Second re-verification against HEAD 1ab4d170:
    - **F14:** Fixed, verified. Recovery refuses heading-led prose, and check names manual recovery instead.
    - **F1:** reopened. The `skill add` chain now preserves the prose, but a skill created by `sq import` at 0.13.1 has no `extra`, so it reads as tool-seeded and is still wiped. Presence-of-absence is not a provenance proof, and adopt and hand-made files have the same shape.
    - **F15:** reopened. The five steps preserve the runbook, but step 1's `show --raw` prints the show panel, which then lands in the new skill's body.
    - **F12/F13:** held for op-pierre, unchanged.
    - Gates: pyright 0, ruff clean, 3527 targeted tests passed with 7 skipped. Status stays ChangesRequested.
- [2026-09-29T00:25:54Z] Paul Reviewer:
  - @manager Third pass at 611f6988: F15 verified Fixed (moved prose byte-identical; jq judged acceptable, see the F15 comment). New F16 (low): the tag-present item_skill_shadowed save command captures the rendered guidance. Open: F1, F12, F13 (held for op-pierre), F16. Stays ChangesRequested.
- [2026-09-29T06:57:27Z] Pierre Chat:
  - F1: we are before 1.0, so the 0.15 migration overwrites every per-type skill body onto its tag, unconditionally: no provenance check and no skip. F16: the shadowed-skill warning's remedy only says to move the prose into its own skill with sq skill add, with no jq or save command.
- [2026-09-29T06:58:23Z] Pierre Chat:
  - F12: the stored body keeps the author's own spacing, and read-time expansion pads each rendered view with blank lines so it never merges with the prose around it. ADR-880 section 4 is amended to match. F13 follows: whitespace-only lines must round-trip through placement and strip like any other separator.
- [2026-09-29T09:16:46Z] Paul Reviewer:
  - @manager Final verification at 8042b0f6: F1, F12, F13 and F16 verify against op-pierre's rulings (F13 has a note on whitespace-matching positions). Two new low findings: F17, a disabled tag between two lines of a paragraph renders as a paragraph break; F18, a reason comment in `_seeded_view_issues` still says the reclaim skips authored skills. Gates: pyright 0, ruff clean, 5525 targeted tests passed with 7 skipped. Stays ChangesRequested until F17 and F18 are settled.
- [2026-09-29T09:22:48Z] Elias Python:
  - F17 fixed: expand_view_tags now strips a disabled view tag with strip_marker_lines (same collapsing rule as an ordinary marker) before the render loop, instead of deleting only the tag's own span. Repro'd on a scratch squad (blank line splitting a paragraph), falsified with a 5-case parametrized test in test_view_tag_expansion_at_read_time.py (mid-paragraph/own-paragraph/body-start/body-end/shared-line), all 5 red pre-fix, green post-fix.
  - F18 fixed: rewrote the stale comment at _maintenance.py (_seeded_view_issues) — the reclaim never skips on authorship grounds under the F1 ruling; the branch is reached when the reclaim never ran against the file at all (adopt, or a type declared later).
  - Gates: pyright + ruff clean on the touched files; targeted run (view-tag placement/expansion/check + tests/meta): 1454 passed, 0 failed. No full suite, no commit.
- [2026-09-29T09:28:12Z] Paul Reviewer:
  - @manager F17 and F18 verified at f053083e, including every disabled-tag render shape. All findings are Fixed, so REV-967 is Approved.
<!-- sq:discussion:end -->
