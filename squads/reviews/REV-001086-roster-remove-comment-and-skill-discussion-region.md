---
id: REV-1086
sequence_id: 1086
type: review
title: Roster remove, comment and skill discussion region
status: ChangesRequested
author: reviewer
refs:
- TASK-1070
description: 'Review of TASK-1070 ST1-ST3: remove/rm, the skill discussion region
  and its 0.16 contribution, roster comment verbs'
subentities:
- local_id: F1
  title: Roster comments help names show --comments, which roster show lacks
  status: Open
  severity: medium
- local_id: F2
  title: Remedy and refusal texts still name the hidden rm alias
  status: Open
  severity: low
- local_id: F3
  title: Addressed-verb lists are hand-copied per group and drift
  status: Open
  severity: info
created_at: '2026-10-16T23:20:09Z'
updated_at: '2026-10-16T23:21:00Z'
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
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T23:20:50Z] Paul Reviewer:
  - Recommended verdict: changes requested, minor. F1 (medium): roster show lacks --comments, which the shared comments help names; add it for parity. F2 (low): refusal and remedy texts still name the hidden rm. F3 (info): derive the addressed-verb lists. Migration, remove/rm identity and comment semantics all verified clean.
  - @python-dev F1 and F2 to fix before the ST3 commit point; @tech-lead to rule on F1 if show --comments is out of scope.
<!-- sq:discussion:end -->
