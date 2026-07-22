---
id: BUG-563
sequence_id: 563
type: bug
title: Search snippet windowing can truncate the matched term out
status: Verified
author: qa
severity: medium
refs:
- FEAT-537
- REV-562
created_at: '2026-07-21T23:53:46Z'
updated_at: '2026-07-22T08:00:30Z'
---
<!-- sq:body -->
`sq search`'s snippet windowing (`_windowed_snippet` in `src/squads/_services/_collab.py`,
`_SNIPPET_WIDTH=160`) builds the snippet by joining up to 3 raw lines around the match and then
hard-truncating from column 0 (`text[:159].rstrip()+'…'`). It does not window *around* the match
offset, so a hit whose matched line is long — or is preceded by a long neighbor line — can have the
matched term itself fall past column 160 and get truncated out of the snippet the engine returns.

Any consumer that renders or filters on the snippet then shows (or, worse, silently drops) a hit
without its matched text visible anywhere: `sq search --json` still reports the item as a match,
but the snippet no longer proves why. This affects the CLI/TUI search display and, most visibly,
the VS Code extension's search QuickPick (FEAT-537): the QuickPick widens its always-on fuzzy
filter with `matchOnDetail` specifically so a body-only hit survives via its snippet (see REV-562
F1) — when the snippet doesn't contain the term, VS Code's filter drops the row entirely and the
user sees fewer results than `sq search` actually matched, with no indication anything was hidden.

**Reproduced** (throwaway squad, `sq search --json`): an item titled "Checkout validation
intermittently fails" (title does NOT contain the query term) with a body paragraph containing one
long line — a ~150-char run of filler text followed by " the user hits unicornberry during
checkout validation." — matching only in the body. `sq search unicornberry --json` returns the hit
(`region: "body"`), but its `snippet` is truncated at the 160-char cap before reaching
"unicornberry":

```
"snippet": "The error occurs after xxxxxxxxxxx...xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx…"
```

— the matched word "unicornberry" never appears in the returned snippet, even though the item is
a genuine, correctly-matched hit.

**Suggested fix direction:** window `_windowed_snippet` around the match column offset within the
line (e.g. centered on the needle's index, not starting from column 0), so the truncated snippet
always retains the matched text regardless of how far into a long line it sits.

**Severity:** medium — result completeness/trust issue across every snippet-based consumer (CLI
output readability, TUI search, and the VS Code QuickPick where it causes silent, undetectable
result drops), not a crash and not data loss.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T07:56:59Z] Elias Python:
  - Fixed: _windowed_snippet (src/squads/_services/_collab.py) now windows around the first match offset instead of column 0 (needle threaded through _hit_for_line/search); short/near-start lines unchanged. Tests added in tests/service/test_search_and_workload_views.py (start/past-cap/near-end/multi-match/short-line). pyright/ruff clean, targeted pytest (29 tests) green.
- [2026-07-22T08:00:30Z] Catherine Manager:
  - Verified: full suite green incl. 5 new regression tests (match past col 160 now present in snippet with left ellipsis); logic reviewed; end-to-end smoke confirmed 'sq search' returns the matched term in the snippet for a deep-in-line match. Server-side fix — TUI and extension inherit it.
<!-- sq:discussion:end -->
