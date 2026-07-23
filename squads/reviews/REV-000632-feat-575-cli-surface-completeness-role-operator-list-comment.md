---
id: REV-632
sequence_id: 632
type: review
title: FEAT-575 CLI surface completeness — role/operator list, comments, guarded sub-entity
  remove
status: Approved
author: reviewer
refs:
- FEAT-575:addresses
subentities:
- local_id: F1
  title: stability.md frozen-surface bullet lists non-existent 'skill list -t skill'
  status: Verified
  severity: low
- local_id: F2
  title: role list --json emits derived 'active' alongside 'status'
  status: Verified
  severity: low
created_at: '2026-07-23T08:34:44Z'
updated_at: '2026-07-23T08:40:44Z'
---
<!-- sq:body -->
Independent review of FEAT-575 (TASK-623/624/625/626/627) scoped to the uncommitted src/tests/docs diff. Verifies: guarded sub-entity remove (marker-safe span excision, atomic refusal, dangling-story guard, freed-local-id policy), the store._log reflog reach-in, role/operator/comments --json contract fidelity against the show-family, and the renamed address-verb test's fallthrough coverage.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 632 add-finding "…" --severity medium`; track with `sq review 632 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Verified |  | stability.md frozen-surface bullet lists non-existent 'skill list -t skill' |
| F2 | 🟢 low | Verified |  | role list --json emits derived 'active' alongside 'status' |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — stability.md frozen-surface bullet lists non-existent 'skill list -t skill'

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
docs/stability.md, frozen-surface bullet (touched by this diff): 'The catalog and roster viewers: role catalog, role list, operator list, skill list -t skill (all with --json)'. 'skill list -t skill' is not a real command — a carryover from the removed standalone-list text. It contradicts the adjacent new prose in the same file ('sq skill list has no dedicated verb; use sq list -t skill'). Correct form is 'list -t skill'. Low, but notable given the feature-family's docs-accuracy theme.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-23T08:38:35Z] Elias Python:
  - Fixed: docs/stability.md's frozen-surface bullet no longer claims a standalone 'skill list -t skill' command — reworded to point at the generic 'list -t skill' (already covered by the Commands bullet above), consistent with the adjacent prose.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — role list --json emits derived 'active' alongside 'status'

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
sq role list --json (src/squads/_cli/_role.py) emits both 'status' and 'active', where active = (status == 'Active') — fully derivable. Now pinned in tests/goldens/role_list.json, so it becomes frozen contract. Roles can be Draft/Active/Archived so active is a genuine convenience (is-in-live-roster) rather than a pure binary of status, but it is still redundant with what a consumer can derive. Flagging per the project's don't-emit-what-you-can-derive lean; keep it consciously or drop it before the golden freezes. Non-blocking.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-23T08:38:36Z] Elias Python:
  - Fixed: dropped the derived 'active' field from 'sq role list --json' (src/squads/_cli/_role.py) — status is now the sole source, un-restated. Regenerated tests/goldens/role_list.json and updated tests/cli/test_role_list_command_cli.py's shape assertion. Table's active/inactive marker column (display-only) is unchanged.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T08:35:27Z] Paul Reviewer:
  - RECOMMENDED VERDICT: Approve (two LOW nits, non-blocking; distinct-party status set by the manager).
  - GATE: green — pyright 0 errors, ruff check clean, ruff format clean (363 files). Targeted pytest over the touched service/CLI/sections/golden tests + tests/meta: 130 passed.
  - LEAD #1 (remove correctness): CORRECT. remove_section(text, 'kind:local_id') excises exactly the block's open→matching-:end span; the nested :head/:body/:discussion regions carry distinct :head:end/:body:end/:discussion:end tokens, so text.find(close) can't mis-match them (verified against block.md.j2, which wraps them all between the block's own open/close and owns the leading blank line remove_section absorbs). Sibling blocks + their markers and the roll-up :summary stay intact (re-rendered via ensure_summary). Refusal is atomic — the dangling-story guard and _find raise before any mutation/write, so file+index+reflog are untouched (test asserts both sides intact). The story→subtask guard is correctly scoped to kind=='story' via _dependent_subtasks over db.children. Freed-local-id policy reasoned soundly in the docstring and can't collide: the guard blocks removing a story that still has mapped subtasks, so a reissued highest id never inherits a stale mapping; reflog is history-only (not replayed to rebuild state). Test coverage is thorough (siblings, summary, frontmatter, refusal, reflog, both gap and reissue cases).
  - LEAD #3 (store._log): ESTABLISHED pattern, not new debt. remove_block uses the identical self.store._log(...) # pyright: ignore[reportPrivateUsage] that every other mutation uses (6 existing sites in this same file plus _items/_refs/_collab/_base/_rename/_retype/_maintenance). No new suppression introduced — consistent, fine.
  - LEAD #4 (--json fidelity): FAITHFUL. comments --json {author, ts, body} is byte-identical to show --json's discussion[] (both _cli/_common.py:563-565 and _items.py:286 use cmt.author/cmt.timestamp/cmt.body via split_discussion). operator list matches operator show fields. Goldens contain only the intended additions. The renamed test_roster_type_address_verbs.py keeps the skill-list fallthrough assertion intact and correctly flips role/operator list to real-verb tests.
  - Conventions: clean — no ticket IDs in source (the FEAT-000002/TASK-3 in the remove CLI test are synthetic IDs generated in the test's own tmp squad, asserted on CLI output — legitimate), no new 'meta' usages (the two hits are pre-existing: a historical :meta marker in a docstring and an untouched local var), no bare type aliases, no </content> leakage, SquadsError-family raised, e() escaping present on console output, no SCHEMA_VERSION bump. Two LOW findings: F1 (stability.md 'skill list -t skill' non-command) and F2 (role list --json derived 'active' redundancy). @manager for verdict.
- [2026-07-23T08:40:42Z] Catherine Manager:
  - Manager verification: F1 stability.md now internally consistent (phantom 'skill list -t skill' gone, skills listed via 'list -t skill'); F2 derived 'active' dropped from role list --json (golden fields: full_name/id/slug/status/title), display marker kept. Full suite green. Leads all confirmed (remove path marker-safe + atomic, store._log established, --json faithful). Approving.
<!-- sq:discussion:end -->
