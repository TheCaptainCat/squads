---
id: BUG-535
sequence_id: 535
type: bug
title: sq ui crashes rendering dynamic content that contains bracket markup
status: Verified
author: op-pierre
priority: high
refs:
- FEAT-526
- FEAT-513
- FEAT-514
description: MarkupError on search hits (and latent in tree/reader) — rich escape
  not honored by Textual's markup parser
created_at: '2026-07-21T13:20:08Z'
updated_at: '2026-07-21T14:14:19Z'
---
<!-- sq:body -->
**Repro.** Open `sq ui`, open the search page, run a query that matches item bodies/discussion. It crashes immediately with `MarkupError: closing tag '[/dim]' does not match any open tag` while rendering the result rows.

**Root cause.** The TUI builds Rich-style markup strings (`[bold]…[/bold] [dim]…[/dim]`) for Textual `Static` widgets and escapes the dynamic parts with `rich.markup.escape`. But `Static` renders through **Textual's** content-markup parser, which does not honor Rich's `\[` escaping — so any dynamic value containing a bracket sequence (search snippets from bodies/discussion are full of them) slips a stray `[/dim]` past and crashes the layout.

**Systemic, not just search.** Same pattern in `_search.py` (hit header + snippets), `_reader.py` (glance assignee, discussion comments), and `_tree.py` (item titles). Search hit it first only because snippet text is the most bracket-heavy; a title or comment containing `[…]` would crash the tree/reader too.

**Fix direction.** Stop concatenating dynamic content into markup strings rendered by Textual. Use a Textual-safe construction — Textual `Content`/`Content.from_markup` with placeholder substitution (placeholders aren't re-parsed as markup), or Textual's own escape — across every Static-markup surface in the TUI. Add a Pilot regression test per surface (search snippet, discussion comment, tree title) using content that contains literal `[/dim]`/bracket sequences.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T13:45:06Z] Elias Python:
  - Fixed across all 3 named surfaces (+ the search no-results line, same pattern). Root cause was more specific than 'Rich escape not honored': rich.markup.escape only escapes '[' when followed by [a-z#/@] (calibrated to Rich's own tag grammar), so a bracket sequence starting with an uppercase letter or digit (e.g. a discussion timestamp '[2026-...]', or a title mentioning '[Note]') passes through unescaped, and Textual's Content parser (broader/different tag recognition than Rich's) can then silently swallow it or, in the right arrangement, raise 'closing tag ... does not match any open tag'.
  - Fix: stopped concatenating dynamic content into markup strings entirely. _search.py/_reader.py now build Textual textual.content.Content via Content.from_markup(template, **vars) -- the template's own tags parse as markup, substituted values are inserted verbatim and never re-parsed (verified directly against the installed Textual: a value containing a literal '[/dim]' renders as plain text). _tree.py's item-title label now builds a rich.text.Text via Text.assemble() with styled spans -- no markup parsing at all, for either parser. Confirmed unaffected: the Markdown body widget (raw commonmark, not Content markup) and the sub-entities Table (a genuine Rich renderable, rendered via Rich's own protocol, already safe with rich.markup.escape).
  - Verified: 4 new Pilot tests (test_bracket_content_renders_safely.py) -- tree title, discussion comment, glance assignee, search snippet -- each with content containing '[/dim]' + an uppercase-bracketed '[Note]' (the shape rich.markup.escape misses); confirmed against the old e()-based functions that this exact content was silently corrupted (bracketed word dropped) before the fix, preserved intact after. Full tests/tui/ (34) + whole-repo pyright/ruff clean.
- [2026-07-21T14:14:18Z] Pierre Chat:
  - Verified in live sq ui testing.
<!-- sq:discussion:end -->
