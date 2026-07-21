---
id: REV-542
sequence_id: 542
type: review
title: Review of BUG-539 CommonMark render fix
status: Approved
author: reviewer
refs:
- BUG-539
subentities:
- local_id: F1
  title: Pre-existing sentinel char in body is not neutralized before extraction
  status: Fixed
  severity: low
- local_id: F2
  title: 'Test gaps: multi-span index, escaping inside code span, digit-adjacency,
    table/heading'
  status: Fixed
  severity: low
created_at: '2026-07-21T20:20:14Z'
updated_at: '2026-07-21T20:24:26Z'
---
<!-- sq:body -->
Independent code review of the uncommitted BUG-539 fix (base = HEAD): `clients/vscode/src/domain/markdown.ts` + `test/markdown.test.ts`.

## Scope reviewed
The code-span-precedence fix: `extractCodeSpans`/`restoreCodeSpans` carve single-backtick code spans out of the raw line into a U+E000-delimited `<sentinel>index<sentinel>` placeholder before the emphasis/link regex runs, then stitch them back as pre-escaped `<code>` HTML. Code removed from the combined `INLINE_TOKEN` alternation.

## Assessment
The approach is correct and a genuine improvement over the old alternation (which could only break ties at the same start index). Adversarial checks pass:

- Precedence: `**`a*b`**`, `*a `b*c` d*`, bare `` `x*y` ``, `` `[a](b)` `` all render with code binding tighter than emphasis/links, per CommonMark.
- Digit-adjacency / id / mention collisions: neutralized by the double-sided sentinel delimiter — a strength of the design.
- Escaping: code content is escaped exactly once in `extractCodeSpans`; the placeholder (sentinels + digits) is inert through `escapeHtml`/linkify; restore inserts renderer-generated HTML that is not re-scanned. No double-unescape, no XSS via the round-trip.
- Emphasis/link/item-id/mention/safe-scheme paths: unchanged and un-regressed. Bonus: code spans nested inside bold now render (old code left them literal).
- Per-call span-index scoping (table cell / heading / list item) is correct.

Gates verified green: vitest 45/45 in `clients/vscode`.

Two low-severity items only (see findings): the pre-existing-sentinel assumption is closed by comment but not by code (one-line lossless strip would make it unconditional), and a handful of edge tests would pin the scheme (escaping-inside-span, multi-span index, digit-adjacency, table/heading, underscore variant).

Verdict: approve-with-nits. No changes required to land; both findings are optional hardening.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 542 add-finding "…" --severity medium`; track with `sq review 542 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | Pre-existing sentinel char in body is not neutralized before extraction |
| F2 | 🟢 low | Fixed |  | Test gaps: multi-span index, escaping inside code span, digit-adjacency, table/heading |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Pre-existing sentinel char in body is not neutralized before extraction

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The placeholder scheme is `<index>` delimited by U+E000 on both sides. `extractCodeSpans` never strips or neutralizes a U+E000 that already exists in the raw body before substituting code spans, and `escapeHtml` does not touch that char. Two consequences:

- No code spans on the line: `restoreCodeSpans` early-returns (`spans.length === 0`), so a stray sentinel passes through verbatim into the emitted HTML — an invisible PUA glyph.
- A body containing the literal `<sentinel>N<sentinel>` sequence AND at least one real code span: the restore regex matches the user's literal sequence too and replaces it with `spans[N]` (or deletes it via `?? ''` when N is out of range). The user's own text is silently swapped for a duplicated code span or removed.

Not a security hole: the substituted value is always `<code>${escapeHtml(code)}</code>` the renderer itself generated, so no raw-HTML/XSS injection is possible through the round-trip — worst case is display corruption of pathological input. A markdown body containing U+E000 is astronomically unlikely, so the dev's "real bodies can't contain it" assumption is reasonable.

But the defense is a one-liner and makes the guarantee unconditional: strip incoming sentinels first, e.g. `raw.replaceAll(CODE_SPAN_PLACEHOLDER, '')` at the top of `extractCodeSpans` (dropping a PUA char with no legitimate body meaning is lossless). Severity low precisely because it is non-exploitable and near-impossible to hit — flagged so the assumption is closed in code, not just in a comment.

Positive note: the double-delimiter design is otherwise sound. Because the index is bracketed by a sentinel on both sides, the "placeholder index adjacent to a prose digit" concern (e.g. `` `x`5 ``) does NOT bite — the trailing sentinel terminates `\d+` before the prose digit, and neither ITEM_ID_PATTERN nor MENTION_PATTERN can match a sentinel-led run.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Test gaps: multi-span index, escaping inside code span, digit-adjacency, table/heading

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The 5 new tests pin the reported repro and guard plain emphasis, which is good. But they miss the edges that make the placeholder scheme trustworthy — add:

- Escaping inside a code span (the security-relevant lock): assert `renderMarkdownToHtml('`<b>&"`')` yields `<code>&lt;b&gt;&amp;&quot;</code>`. This is the test that pins "content escaped exactly once, no raw-HTML injection through the round-trip" — currently the escape path inside `extractCodeSpans` has no direct coverage.
- Multiple code spans on one line: `` `a` and `b` `` → `<code>a</code> and <code>b</code>`, to pin the index/ordering scheme (the one thing the placeholder round-trip could get wrong).
- Code span immediately followed by a prose digit: `` a `x`5 b `` → `a <code>x</code>5 b`, to lock the double-delimiter property against future single-delimiter "simplification".
- Code span inside a table cell and inside a heading, to pin that each `renderInline` call scopes its own spans index (per-call reset) rather than sharing state.
- Underscore emphasis wrapping a code span with an underscore inside (`` __`a_b`__ ``) — only the `*` variant is exercised; `_` is a separate INLINE_TOKEN alternative.

All are nits: the implementation handles every one of these correctly (verified by reading), so these are coverage/regression-guard additions, not defect proof. No missing behavior, only missing pins.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
