---
id: REV-438
sequence_id: 438
type: review
title: VS Code extension browse UI (US1-3) + dev-time CI lane
status: Approved
author: reviewer
refs:
- TASK-429:addresses
- TASK-430:addresses
- TASK-431:addresses
- TASK-432:addresses
subentities:
- local_id: F1
  title: Hierarchy refresh fires a redundant open-only sq list invocation
  status: Fixed
  severity: low
- local_id: F2
  title: CI covers only the unit test layer; integration skew-canary + host smoke
    absent
  status: Open
  severity: medium
- local_id: F3
  title: Python test.yml runs on TS-only changes (no paths filter) despite the stated
    isolation
  status: Fixed
  severity: low
created_at: '2026-07-16T19:34:39Z'
updated_at: '2026-07-17T08:00:33Z'
---
<!-- sq:body -->
Round-2 review of the VS Code extension's browse UI (TASK-429 US1 tree, TASK-430 US2 preview, TASK-431 US3 filter/group/refresh — all Ada) and the dev-time CI lane (TASK-432 — Hugo). Foundation (TASK-428, REV-436) has landed. Scope: clients/vscode/** + .github/workflows/vscode-client.yml only; concurrent src/tests (TASK-434) excluded.

Gate run by the reviewer: `npm run check` clean (tsc + eslint --max-warnings 0 + prettier), `npm test` 67/67 green. Round-1 findings confirmed addressed: item-ID hygiene now guarded by test/hygiene.test.ts (F2) and src/README are ID-free (F1); the usage-error argv now carries the resolved command (F3).

Verdict by area:
- US1 tree (treeDataProvider / domain/treeMapping / domain/reservedTypes): APPROVE. JSON->DisplayNode mapping correct; the 3 reserved meta types filtered at every depth by exact type string (spec-agnostic); status/assignee/blocked rendered (blocked = themed icon + description suffix + tooltip); failure yields a single error node + notification, never a partial silent tree; spawn-error invalidates discovery for re-probe. One low efficiency finding (F1).
- US2 preview (showDocumentProvider / sqAdapter.getRaw / domain/showPreview): APPROVE, no findings. squads: read-only TextDocumentContentProvider (inherently no write-back), shells sq show <id> --raw, failure renders actionable markdown + notification, spawn-error re-probes. Verified live sq show --raw already emits the clean H1+bold-bullet format, so show-raw.txt is genuinely captured, not aspirational.
- US3 filter/group (domain/listView / commands / package.json): APPROVE. Filter-by-type/state, recursive ordered grouping, reserved-type exclusion, dynamic type quick-pick (no hardcoded catalog); commands + view/title menus wired. Open/closed design tradeoff tracked as follow-up (see rulings), not blocking.
- TASK-432 CI lane: APPROVE with findings. Correctly isolated separate workflow, path-filtered on clients/vscode/**, Python CI untouched. Test-layers gap (F2) tracked; test.yml trigger note (F3).

Overall: APPROVE. No blocking findings — all three are low/medium follow-ups. Rulings on the two design calls + the CI gap are recorded as comments.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 438 add-finding "…" --severity medium`; track with `sq review 438 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | Hierarchy refresh fires a redundant open-only sq list invocation |
| F2 | 🟡 medium | Open |  | CI covers only the unit test layer; integration skew-canary + host smoke absent |
| F3 | 🟢 low | Fixed |  | Python test.yml runs on TS-only changes (no paths filter) despite the stated isolation |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Hierarchy refresh fires a redundant open-only sq list invocation

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
In treeDataProvider.refresh(), the hierarchy (non-flat) path runs Promise.all([getTree, getListSnapshot]). getListSnapshot issues TWO sq list calls (one --all, one default/open-only) and returns { items, openIds }. But the hierarchy branch uses only listOutcome.data.items (for buildTitleLookup + distinctTypes) and never touches openIds — so the second, open-only list fetch is pure waste on every full-tree refresh (tree + list --all + list = 3 spawns where 2 suffice).

getListSnapshot is the right call for the flat/grouped view (which needs openIds for state classification); the hierarchy path should call plain getList(--all) for titles instead. Low-impact (one extra short-lived subprocess per hierarchy refresh), but it compounds the efficiency concern in design-question #2.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-17T07:33:46Z] Operator:
  - Fixed: hierarchy refresh path now calls getList(--all) instead of getListSnapshot — one sq list spawn (plus sq tree) instead of two; getListSnapshot's double-fetch stays reserved for the flat/grouped view that needs openIds.
- [2026-07-17T07:33:56Z] Ada Typescript:
  - Fixed: hierarchy refresh path now calls getList(--all) instead of getListSnapshot — one sq list spawn (plus sq tree) instead of two; getListSnapshot's double-fetch stays reserved for the flat/grouped view that needs openIds.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — CI covers only the unit test layer; integration skew-canary + host smoke absent

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
ADR-427 #3 specifies three test layers — unit / thin integration skew-canary (real sq vs committed fixtures) / @vscode/test-electron extension-host smoke — but only the unit layer exists, so vscode-client.yml's test job runs only that. Hugo flagged this honestly (the other layers aren't npm scripts yet, and adding them was scoped out of TASK-432).

Ruling: acceptable to ship 0.10 without them (the unit layer is the bulk of the value and runs headless), BUT record + track as a follow-up. The integration skew-canary is the more important of the two: it is the ADR's designated mechanism for catching cross-language contract drift, and right now nothing re-verifies the committed tree/list/show-raw fixtures against live sq output. Recommend a follow-up task to add the skew-canary (ideally landing when TASK-434 merges, so show-raw.txt gets a live re-verification) and, lower priority, the extension-host smoke test — then wire both as npm scripts the CI lane invokes.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Python test.yml runs on TS-only changes (no paths filter) despite the stated isolation

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
vscode-client.yml is correctly path-filtered on clients/vscode/** so it never runs on Python-only changes. But the reverse isolation is not actually in place: test.yml (the Python CI) has NO paths filter — it triggers on every push/PR to main — so a clients/vscode-only PR triggers the full 3-OS Python matrix too. Hugo's handoff states 'test.yml has no clients/** trigger so it never runs on TS-only changes'; that is inaccurate.

Impact is low: the Python jobs pass on a clients-excluded tree (ruff/pyright exclude clients, pytest doesn't scan it), so it never BLOCKS — the ADR's 'a TS failure never blocks a Python-only change, and vice versa' still holds for blocking. But it wastes CI on every TS/doc-only PR and the documented isolation overstates reality. Fix options: correct the claim, or add paths-ignore: ['clients/vscode/**'] to test.yml — but weigh GitHub required-checks semantics first (a required check skipped by a paths filter can sit 'pending' and block merge unless branch protection is configured to match; the same required-checks caveat Hugo already flagged).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-16T19:35:39Z] Paul Reviewer:
  - Ruling — design call #1 (no title on sq tree --json): YES, the core sq tree --json should gain an additive title field. Exact parity with the just-shipped show --json body/discussion enrichment — a browse client shouldn't reconstruct data the core trivially has, and a title is arguably core to a *tree* surface (a tree of bare ids is barely usable), not enrichment. It's additive (golden tests just grow a key, no break), cheap (title is already in the index), and collapses the default tree render from 2 fetches to 1. For 0.10 Ada's join-by-id workaround is correct and ships fine (degrades gracefully to id-only labels on fetch failure); file the core follow-up for 0.11.
  - Ruling — design call #2 (open/closed via double sq list --all/default diff): the approach is CORRECT and admirably spec-driven — it honors 'statuses are per-project workflow-spec-driven; no hardcoded terminal-status table.' Efficiency is acceptable for 0.10: these are user-initiated refresh/filter actions at typical squad sizes, a couple of short-lived spawns, not a hot path. It doesn't scale elegantly though, and finding F1 (redundant open-only fetch in the hierarchy path) makes it worse. Right long-term fix mirrors #1: an additive authoritative is_open/terminal boolean on sq list --json (and ideally sq tree --json), computed by the CLI from the workflow spec — stays spec-driven (the CLI owns the spec), just moves derivation to the authoritative side and collapses 2 list calls to 1. Accept for 0.10 with a tracked follow-up; fix F1's redundant call now regardless.
  - Both #1 and #2 point the same way: the tree/list surfaces are a touch too thin, pushing the client into multi-fetch id-joins. Additive core fields (title on tree, is_open on list/tree) are the clean fix, consistent with the show --json enrichment already done. Neither blocks 0.10. @tech-lead for the two core-surface follow-ups + the CI skew-canary follow-up (F2).
- [2026-07-17T08:00:33Z] Paul Reviewer:
  - F3 marked Fixed — addressed by TASK-442: test.yml now carries paths-ignore ['clients/vscode/**'] on both push and pull_request, with the required-checks/branch-protection caveat documented in-file (main has no required checks today). Reviewed in REV-443 (APPROVE).
<!-- sq:discussion:end -->
