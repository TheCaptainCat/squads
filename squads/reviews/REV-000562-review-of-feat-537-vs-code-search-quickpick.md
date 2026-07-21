---
id: REV-562
sequence_id: 562
type: review
title: Review of FEAT-537 VS Code search QuickPick
status: Approved
author: reviewer
refs:
- FEAT-537
subentities:
- local_id: F1
  title: VS Code built-in filter can silently hide legitimate sq search hits
  status: WontFix
  severity: medium
- local_id: F2
  title: Displayed row order is VS Code fuzzy-score order, not sq search's returned
    rank
  status: Verified
  severity: low
- local_id: F3
  title: Enter mid-debounce can open a stale highlighted result instead of submitting
    the refined query
  status: Verified
  severity: low
created_at: '2026-07-21T23:45:49Z'
updated_at: '2026-07-21T23:57:05Z'
---
<!-- sq:body -->
Independent read-only review of FEAT-537 (VS Code full-text search QuickPick): TASK-558 adapter+guard, TASK-559 QuickPick/states, TASK-560 type/status narrowing, TASK-561 open-in-reader. Reviewer did not author the code. Extension gates reported green (typecheck/lint/format, vitest 359).

Verdict: approve-with-nits. The client implementation is correct and idiomatic — last-query-wins, submit/debounce, single-valued pass-through filters, reuse of ItemPreviewManager.openFromTree, and a robust shape guard all check out. One Medium correctness gap (F1) sits at the VS Code widget layer and its clean fix lives server-side (out of this read-only feature's scope), so it should be tracked as a follow-up bug rather than block the client code. F2/F3 are Low.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 562 add-finding "…" --severity medium`; track with `sq review 562 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | WontFix |  | VS Code built-in filter can silently hide legitimate sq search hits |
| F2 | 🟢 low | Verified |  | Displayed row order is VS Code fuzzy-score order, not sq search's returned rank |
| F3 | 🟢 low | Verified |  | Enter mid-debounce can open a stale highlighted result instead of submitting the refined query |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — VS Code built-in filter can silently hide legitimate sq search hits

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**What.** searchQuickPick.ts enables matchOnDescription/matchOnDetail to widen VS Code's always-on QuickPick filter so a server hit whose *title* doesn't contain the query still survives on its snippet. The module comment claims this is safe because "every hit's detail always carries the matched snippet (which does contain the query)". That invariant does not hold.

**Why it breaks.** sq's engine matches a single case-insensitive contiguous needle (`needle = text.strip().lower()`, _services/_collab.py). For title/description/discussion hits the snippet does contain the needle. But body/other-region hits use `_windowed_snippet`, which joins up to 3 lines with ' / ' and caps the result at _SNIPPET_WIDTH=160 chars (`text[:159].rstrip()+'…'`). The matched line sits in the MIDDLE of the window, so a long preceding line — or a single long matched line with the match near its end — pushes the needle past the 160 cap and truncates it out of the snippet.

**Failure scenario.** Search 'authenticate'. An item matches only in a body paragraph that is one long line with 'authenticate' at column ~180 (or preceded by a ~120-char line). sq returns the hit; its detail snippet is truncated before 'authenticate'. The row's label (id+title) and description (type·status) don't contain 'authenticate' either, so VS Code's fuzzy filter drops the row. The user sees fewer results than `sq search authenticate` returns, with no indication — violating the acceptance criterion 'lists matching items … sq search returned'.

**Remedy.** The clean fix is server-side and out of this read-only feature's scope: window `_windowed_snippet` around the match offset so the needle always survives the 160-char cap. Client-side there is no supported way to disable the QuickPick filter, so the mitigation as written is the best available at this layer — but it is incompletely sound. Recommend tracking a follow-up bug against the search engine's snippet windowing; the feature can ship with this documented.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Displayed row order is VS Code fuzzy-score order, not sq search's returned rank

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**What.** searchResults.ts documents 'Rows are rendered in the exact order sq search --json returned them — no client-side re-ranking'. End-to-end that invariant is not upheld: with matchOnDescription/matchOnDetail on, VS Code sorts the surviving items by its own fuzzy match score against the current value, so the user sees results in relevance-to-query order, not sq's returned rank.

**Impact.** No results are dropped — this is ordering only — but the module's stated 'no re-ranking' guarantee and the feature's 'no client-side re-matching/post-filtering' posture are technically not held at the widget layer. Low: it's inherent to the QuickPick widget (same root constraint as F1) and the mapping code itself is faithful. Recommend softening the doc comment to acknowledge the widget re-orders, so the promise matches reality.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Enter mid-debounce can open a stale highlighted result instead of submitting the refined query

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**What.** onDidAccept disambiguates via decideAccept(quickPick.selectedItems[0]): a selected row → open; nothing selected → debounce-bypass submit. This is correct in the common case. The sharp edge: after results render, the first row is auto-active; if the user then types a refinement, the OLD results stay displayed until the new result arrives (items are only replaced in applyOutcome). If a stale row still fuzzy-matches the new value it remains selectedItems[0].

**Failure scenario.** Type 'login', results show (first row active). Refine to 'logout' and press Enter within the 300ms debounce before the new search returns. If a stale 'login' row still matches 'logout' fuzzily, decideAccept returns 'open' and the extension opens that stale item instead of submitting the 'logout' query. No data loss; a wrong-item navigation only. Low. Optional mitigation: clear quickPick.items (or drop selection) on value change before the new results land, so Enter mid-typing falls through to submit.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T23:49:57Z] Ada Typescript:
  - F2 fixed: softened domain/searchResults.ts's doc comment to state sq's returned order is what this mapping passes through, not a guarantee about the rendered order (VS Code's matchOnDescription/matchOnDetail may still re-sort surviving rows).
  - F3 fixed: onDidChangeValue now clears quickPick.items before searchRunner.typed(...), so a stale highlighted row can never survive into a mid-debounce Enter; decideAccept falls through to submit instead. Extended test/searchAccept.test.ts for the post-clear (empty items) case.
  - Gates re-run in clients/vscode: typecheck/lint --max-warnings 0/format:check/vitest all green (23 files, 360 tests). F1 tracked separately (server-side).
- [2026-07-21T23:56:21Z] Catherine Manager:
  - F2/F3 fixed by Ada (doc comment softened; items cleared on value change so a stale row can't be accepted mid-debounce) and Verified. F1 (server-side snippet windowing) is out of FEAT-537's read-only client scope — tracked as BUG-563 for a fix in _services/_collab.py (window around the match offset). Approving.
<!-- sq:discussion:end -->
