---
id: REV-1086
sequence_id: 1086
type: review
title: Roster remove, comment and skill discussion region
status: Approved
author: reviewer
refs:
- TASK-1070
description: 'Review of TASK-1070 ST1-ST3: remove/rm, the skill discussion region
  and its 0.16 contribution, roster comment verbs'
subentities:
- local_id: F1
  title: Roster comments help names show --comments, which roster show lacks
  status: Verified
  severity: medium
- local_id: F2
  title: Remedy and refusal texts still name the hidden rm alias
  status: Verified
  severity: low
- local_id: F3
  title: Addressed-verb lists are hand-copied per group and drift
  status: Verified
  severity: info
- local_id: F4
  title: Update with only --when-to-use leaves the scaffold stale, so the skill body
    counts as written
  status: Verified
  severity: medium
- local_id: F5
  title: A slug key on a generated role import names the role override; elsewhere
    it is not settable
  status: Verified
  severity: low
- local_id: F6
  title: Rescaffold address branch is unreachable for work items and misroutes operators
  status: Verified
  severity: info
- local_id: F7
  title: Renaming a dropped-view or dropped-type skill inserts template prose next
    to its tag
  status: Verified
  severity: low
created_at: '2026-10-16T23:20:09Z'
updated_at: '2026-10-25T19:38:38Z'
---
<!-- sq:body -->
## Scope

The uncommitted TASK-1070 ST1 to ST3 against c533014d:
- `remove` with `rm` as a hidden alias on skills, roles and operators;
- the skill discussion region (the backend seed, `sections.with_discussion_region`, and the `skill-discussion` contribution in the 0.15 to 0.16 migration);
- `comment`/`comments` on all three, through `register_comment_verbs`.

## Verified (dev build, scratch squads only)

- **remove and rm.** Six shapes (bundled, generated and project skill; system role; declared developer; operator), bare and with `--purge`. Each pair gave the same exit code, the same output and the same tree, except the `.reflog.jsonl` timestamp. The roster dependency gate still refuses (permanent floor, implied-by-type, scoped-to-role). Help lists `remove` and not `rm`.
- **Migration on a copy of this squad.** `migrate up` then `sync` then `check` is clean, and a second `migrate up` is a no-op. 12 of 14 skills gained the region; the 2 project skills already had one. Compared with a HEAD-build migration of the same copy, the only difference is the region lines in those 12 skill files, and `.squads.json` is identical.
- **Migration on the v0_15 fixture.** A CRLF skill keeps CRLF throughout, and a skill with no final newline gets the same bytes as a fresh file.
- **Fresh init.** All 13 skills and a newly added skill carry the region, and `sync` is a fixed point.
- **Comments.** Comments are allowed on system skills and roles and are never gated. Headers match the item format (backticked slug, then the name). `--json` carries `author_slug`. `@mention`s reach `sq inbox`; a retired role is excluded, which is terminal-status behaviour as for items. `--file` with backticks and a fence, CRLF input and stdin all work. A missing or unknown `--as` exits 1 and writes nothing, and a marker in a comment is refused.
- **Tests.** The four new test modules, the header-migration test, the corpus migration test, the existing rm tests and `tests/meta` ran under a scratch basetemp: 664 passed, 0 failed.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1086 add-finding "…" --severity medium`; track with `sq review 1086 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Roster comments help names show --comments, which roster show lacks

<!-- sq:finding:F1:body -->
The roster `comments` help, shared from `register_comment_verbs` in `_cli/_common.py`, says "`show --comments` renders the same discussion inline alongside the rest". That holds on a work item, but `sq skill|role|operator <x> show --comments` exits 2 with "No such option: --comments". So the help text is false on all three roster groups.

The task's ST3 test table also lists a `show --comments` column, and the dev flagged it as not done.

Probe: on a migrated copy of this squad (dev build, `-C`), run `sq skill squads show --comments`. It exits 2. `sq role qa show --full` exits 2 as well.

Recommendation: add `--comments` to the three roster `show` commands, which gives verb parity with items and makes the shared help true, and pin it in the comment table. If the team rules against it, the shared docstring has to stop naming `show --comments` on the roster subgroups.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T23:25:34Z] `python-dev` Elias Python:
  - Added --comments to the three roster show commands (text output); pinned in the comment table. Reverting the skill one: 8 tests red.
- [2026-10-16T23:54:26Z] `reviewer` Paul Reviewer:
  - Verified: role, skill and operator show take --comments and print the discussion.
- [2026-10-25T19:38:38Z] `reviewer` Paul Reviewer:
  - Holds: `sq role qa show --comments` exits 0 and prints the discussion on 0.17; the option is on role, skill and operator show.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Remedy and refusal texts still name the hidden rm alias

<!-- sq:finding:F2:body -->
`rm` is now hidden from `--help`, but the user-facing text still sends people to it:

- `_services/_items.py` `_purge_required_message`: `remove` itself prints "To delete it for good, run `sq role ROLE-5 rm --purge`" (checked on role, skill and operator).
- `_services/_validators.py` lines 1439, 1448 and 1452: three `sq check` remedies end in `rm --purge`.
- `_migrations/_v0_15_to_v0_16.py` lines 749 and 758: the MANUAL steps say `rm --purge`. The 0.16 migration is unreleased, so this text can still change.
- `_cli/_common.py` `AddressDispatchGroup`: the docstring (`show|regen|rm`) and the default `_ADDR_VERBS` (`show|regen|rm|status`) are stale. Every subclass overrides the default, so it only misleads.

The alias still works, so nothing breaks, but every remedy names a command that help does not list. Name `remove` in all of them. `tests/service/test_remove_roster_item_requires_purge.py` pins the old text at lines 31 and 43.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T23:25:36Z] `python-dev` Elias Python:
  - remove is named in the purge message, the three sq check remedies, the 0.16 MANUAL steps and the dispatch-group docstring/default (the default is gone, see F3); pinned tests updated. Reverting the purge message: 24 tests red.
- [2026-10-16T23:54:27Z] `reviewer` Paul Reviewer:
  - Verified: no rm --purge is left under src, including the 0.16 MANUAL; refusal and check remedies name remove --purge.
- [2026-10-25T19:38:38Z] `reviewer` Paul Reviewer:
  - Holds: refusals and check remedies name `remove --purge`; the 0.16 MANUAL keeps `rm --purge` on purpose, as the 0.15 tool runs it (565c39fa).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Addressed-verb lists are hand-copied per group and drift

<!-- sq:finding:F3:body -->
Each roster group restates its addressed verbs by hand three times: `_ADDR_VERBS`, the epilog's "Address a ..." line, and the module grammar docstring. This change edited all nine copies (three groups x three places) and missed the base-class default (see F2). The ST4/ST5 `update` verb has to edit them all again.

Suggestion: derive `_ADDR_VERBS`, and the epilog's verb list, from the `_addr` subgroup's registered non-hidden commands, so a new verb or alias cannot drift from the missing-verb error. This is a cleanup, so it is not blocking.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T23:25:38Z] `python-dev` Elias Python:
  - The missing-verb error and each group help epilog now come from the registered non-hidden commands of the addressed subgroup (the three _ADDR_VERBS lists are deleted; epilogs take a {verbs} slot filled after registration). Hand list restored: 3 red; rm unhidden: 6 red. The module grammar docstrings stay hand-written.
- [2026-10-16T23:54:28Z] `reviewer` Paul Reviewer:
  - Verified: the epilog and the missing-verb error derive their verb list from the registered non-hidden commands, and update appears without a hand edit.
- [2026-10-25T19:38:38Z] `reviewer` Paul Reviewer:
  - Holds: `sq operator --help` builds its VERB list from the registered commands; `_ADDR_VERBS` is gone from src.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Update with only --when-to-use leaves the scaffold stale, so the skill body counts as written

<!-- sq:finding:F4:body -->
Body re-rendering happens only when the title or the description changes: `_update_model` passes `rescaffold=... and ("title" in delta or "description" in delta)`. But `templates/agents/skill.md.j2` also interpolates `item.when_to_use`, as a "## When to use" section.

So on a project skill whose body is still the seeded scaffold, `sq skill <x> update --when-to-use "..."` does not re-render the body. The old scaffold no longer equals the new pristine body, so the seeded template now counts as written, which the FEAT-1054 rule says an update must never cause.

Probe (fresh scratch squad, dev build):
1. Run `skill add my-skill --desc 'Old desc'`.
2. Run `skill my-skill update --when-to-use 'When shipping.'`. The body is unchanged.
3. Run `skill my-skill body -m 'Authored now.'`. It exits 1 with "already has a body (5 lines) ... pass --force".

Without step 2, step 3 succeeds. With `--title` added to step 2, the body re-renders and step 3 succeeds.

Fix: re-render on every roster update. `_rescaffolded_body` already leaves a written body alone, so the delta condition only adds a way to miss a field. Add a `--when-to-use`-only row to the body re-render test.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T23:58:32Z] `python-dev` Elias Python:
  - Every roster update now re-renders an unwritten scaffold body, so --when-to-use alone keeps it unwritten (new --title/--desc/--when-to-use row; the old delta condition: 1 red).
- [2026-10-17T00:02:33Z] `reviewer` Paul Reviewer:
  - Reopened. `--when-to-use` alone now re-renders a project skill's scaffold, and `body -m` then succeeds, so the reported case is fixed. But re-rendering on every roster update created a regression on generated skills.
    
    A system or generated skill's seeded body is only its view tag, while `pristine_body` renders the generic `skill.md.j2` scaffold for it. `body_is_unwritten` treats the tag-only body as unwritten, so `_rescaffolded_body` inserts the scaffold prose (title heading, description, "## Instructions") in front of the view tag.
    
    The gate allows the updates that trigger this on these skills: labels, assignee, parent and project attributes, through `sq import`.
    
    Probe (fresh squad, dev build):
    - `{"op":"update","target":"SKILL-20","as":"manager","add_labels":["z"]}` on `squads` adds "# squads / <description> / ## Instructions" above the sq:view:squads_skill tag.
    - `assignee: qa` on `sq-task` does the same.
    - `sq skill squads show` renders the injected prose, and `sq check` stays clean.
    - Roles and operators were unaffected in the probe.
    
    The targeted tests (683) pass, so no test pins the body bytes after a metadata-only update on a generated skill.
    
    Suggested fix: skip re-rendering for an entry whose body is classified (`views.roster_body_view_name`, already read by the gate), or re-render only when the pristine body actually changes between *base* and *item*. Add a body-bytes column for the label, assignee and project-attribute rows of the generated-host table.
- [2026-10-17T00:07:47Z] `python-dev` Elias Python:
  - The re-render skips a body that renders through a view (the gate classifier, via one shared helper, so there is still one caller) and skips any update that leaves the scaffold unchanged. New rows: generated, dropped-view and dropped-type skills x label, assignee and project-attribute import leave the body byte-identical (6 red without the unchanged-scaffold check). The classifier check alone turns nothing red: a classified skill refuses title and description before the re-render, and a role scaffold reads neither.
- [2026-10-17T00:11:29Z] `reviewer` Paul Reviewer:
  - Verified: label, assignee and project-attribute imports leave the squads, sq-task, greeting (dropped view) and sq-guide (dropped type) bodies byte-identical; a project skill --when-to-use update re-renders and body -m then succeeds. The rename residual on dropped-view/type skills is filed as F7.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — A slug key on a generated role import names the role override; elsewhere it is not settable

<!-- sq:finding:F5:body -->
On an import update, the gate builds its set of gated fields from the `RoleDef` field names, and that set includes `slug`. So `fields: {slug: x}` on a generated role is refused with "its content already has one validated authoring surface: `.overrides/roles.toml`". That message suggests the slug can be authored in the role document, but it cannot: an override's slug must equal its file name. The same event on a skill or operator says "'slug' is not a settable field".

An unknown key now gets "not a settable field" on a role, as on a skill, an operator or a work item, and that part is consistent.

Suggestion: leave identity keys (`slug`) out of the role-supplied set, so a slug change gets the same "not settable" answer on every roster type.

Separately, `require_update_fields` prints "pass at least one of --title" on a role or an operator. With a single option, "pass --title" reads better.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T23:58:34Z] `python-dev` Elias Python:
  - slug is left out of the role-supplied gated set, so importing it answers not a settable field on every roster type (4 red when restored); a single-option update now says pass --title (6 red when restored).
- [2026-10-17T00:02:34Z] `reviewer` Paul Reviewer:
  - Verified: slug set/unset gives not a settable field on role, skill and operator; single-option update says pass --title.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Rescaffold address branch is unreachable for work items and misroutes operators

<!-- sq:finding:F6:body -->
`_rescaffolded_body` in `_services/_base.py` picks its address with `slug if item.type in (ROSTER_ROLE, ROSTER_SKILL) else number_for_id(item.id)`. Its only caller sets `rescaffold` for roster types only, so the work-item branch is unreachable. An operator, which is a roster entry addressed by slug, falls into the number branch.

Use `item.slug` for every roster type and drop the branch. The function is roster-only, and its docstring could say so.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T23:58:36Z] `python-dev` Elias Python:
  - _rescaffolded_body addresses by slug with no branch; no observable difference exists for roster types, so reverting it turns 0 tests red.
- [2026-10-17T00:02:36Z] `reviewer` Paul Reviewer:
  - Verified: _rescaffolded_body addresses by item.slug for every roster type; the branch is gone.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Renaming a dropped-view or dropped-type skill inserts template prose next to its tag

<!-- sq:finding:F7:body -->
`_rescaffolded_body` now skips classified bodies and updates that leave the scaffold unchanged. A title change on a skill whose view or type is dropped from `[selected]` still re-renders, and its seeded body is only a tag.

The tag-only body counts as unwritten, so the generic `skill.md.j2` prose (the title heading, the description, "## Instructions") is inserted in front of the tag. The user never wrote that prose.

Probe (fresh squad, override dropping the guide type and the greeting view, greeting tag disabled):
1. Import `{"op":"update","target":"<id>","title":"Renamed"}` on `greeting` and on `sq-guide`. Both bodies gain the scaffold prose. Label, assignee and project-attribute imports leave both bodies byte-identical.
2. Restore `guide` in `[selected]` and run `sync`. `sq check` now warns that SKILL-15 "carries prose beside its item_skill tag", with a four-step remedy (move the prose, drop the type, clear the body with `--force`, restore the type). That leaves the adopter cleaning up prose the tool wrote.

Suggested fix: do not re-render a body that holds a view tag, enabled or disabled, and no prose. Its seeded shape is the tag alone, not the generic template. Equivalently, re-render only when the region is byte-equal to the old pristine body. Add rows for these two shapes to the re-render test.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-17T00:13:53Z] `python-dev` Elias Python:
  - A body holding only a view tag (enabled or disabled) is not re-rendered. New rows: a title import on a dropped-view skill and on a dropped-type skill leaves the body byte-identical (2 red without the check); the project-skill title row still re-renders.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T23:20:50Z] `reviewer` Paul Reviewer:
  - Recommended verdict: changes requested, minor. F1 (medium): roster show lacks --comments, which the shared comments help names; add it for parity. F2 (low): refusal and remedy texts still name the hidden rm. F3 (info): derive the addressed-verb lists. Migration, remove/rm identity and comment semantics all verified clean.
  - @python-dev F1 and F2 to fix before the ST3 commit point; @tech-lead to rule on F1 if show --comments is out of scope.
- [2026-10-16T23:54:38Z] `reviewer` Paul Reviewer:
  - ST4/ST5 re-review. F1-F3 verified Fixed. Verified clean: the gate (a project attribute stays writable through import; labels, parent and unknown keys are untouched by it; a combined call is refused; a system skill title, description or when-to-use is refused naming the playbook; every live role title passes), update options with no slug change, no-option exit 1 with nothing written, written bodies kept, retired role and skill updates leave pointers absent, live rename refreshes the pointer and CLAUDE.md, and sync is a fixed point. Targeted tests: 1077 passed; ruff and pyright clean.
  - New: F4 (medium) update --when-to-use alone leaves the scaffold stale; F5 (low) slug-on-role message and the single-option "at least one of" wording; F6 (info) unreachable rescaffold address branch. Review stays ChangesRequested on F4. @python-dev F4 to fix, F5/F6 your call.
- [2026-10-17T00:02:36Z] `reviewer` Paul Reviewer:
  - F5, F6 Verified. F4 reopened: re-rendering on every roster update injects skill.md.j2 scaffold prose into a generated skill body on a label, assignee or project-attribute import (repro on the finding). Review stays ChangesRequested. @python-dev F4.
- [2026-10-17T00:11:38Z] `reviewer` Paul Reviewer:
  - F1-F6 Verified. New F7 (low): renaming a dropped-view or dropped-type skill inserts skill.md.j2 prose next to its tag, and restoring the type then trips a sq check warning. Recommendation: Approved once F7 is fixed or given a disposition; the fix is one condition in _rescaffolded_body plus two table rows. @python-dev F7.
- [2026-10-17T00:17:36Z] `manager` Catherine Manager:
  - Approved: F1-F6 verified by the reviewer; F7 fixed with two falsified rows; full suite 12346 passed, 0 failed.
<!-- sq:discussion:end -->
