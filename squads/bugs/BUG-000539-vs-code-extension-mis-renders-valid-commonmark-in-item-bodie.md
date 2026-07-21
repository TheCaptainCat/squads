---
id: BUG-539
sequence_id: 539
type: bug
title: VS Code extension mis-renders valid CommonMark in item bodies
status: Fixed
author: op-pierre
assignee: typescript-dev
priority: medium
refs:
- BUG-535
description: 'Extension body renderer mangles valid CommonMark: bold-wrapped inline
  code and a ''*'' inside a code span break out, unbalance emphasis, and the code
  span runs on.'
created_at: '2026-07-21T15:24:45Z'
updated_at: '2026-07-21T20:24:26Z'
---
<!-- sq:body -->
## Summary

The VS Code extension's item-body renderer mangles **valid CommonMark**. Two symptoms
seen together on one line: an inline code span wrapped in bold, where the code contains an
asterisk, loses the asterisk, unbalances the surrounding `**`, and — because the code span
never closes — renders the rest of the body as a code block.

## Repro

1. Give any item a body line such as (valid CommonMark — code spans bind tighter than
   emphasis, so this is well-formed):

   ```
   - **`$(*path)` splat-refs** — a safe, eval-free path-reference splice
   ```
2. Open that item in the VS Code extension's reader/preview.

## Expected

Renders as bold **`$(*path)` splat-refs — …**, with `$(*path)` shown literally as inline
code (the `*` is inside the code span, so it is not an emphasis marker).

## Actual

The leading `**` collapses to a single `*`, the `*` inside `$(*path)` is consumed as an
emphasis token (shown as `$(path)`), the inline code span never terminates, and the
remainder of the body renders as a run-on code block.

## Impact

Display-only (frontmatter, markers, and stored body are intact), but item bodies routinely
contain `` ` ``, `*`, and `[]`, so this corrupts the rendering of ordinary content. Same
family as the TUI bracket-rendering defect (see related).

## Likely area

The extension's markdown rendering path (item preview/reader). Root cause smells like a
non-CommonMark tokenizer that resolves emphasis before code spans, rather than tokenizing
code spans first. Fix should route body rendering through a CommonMark-compliant renderer.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T20:08:57Z] Catherine Manager:
  - Dispatched to @typescript-dev. Root cause: the hand-rolled inline tokenizer (clients/vscode/src/domain/markdown.ts, INLINE_TOKEN) tokenizes emphasis without giving code spans precedence — the `**...**` and `*...*` alternatives exclude '*' in their content, so a code span containing '*' inside bold matches as single-* emphasis instead. CommonMark rule violated: code spans bind tighter than emphasis.
- [2026-07-21T20:14:16Z] Ada Typescript:
  - Fixed: renderInline in clients/vscode/src/domain/markdown.ts now extracts code spans (extractCodeSpans/restoreCodeSpans) into an opaque placeholder before running the emphasis/link regex, giving code-span precedence over emphasis per CommonMark, then restores them as <code> HTML — no library added. Added 4 regression tests in clients/vscode/test/markdown.test.ts (bold-wrapped code span with *, bare code span with *, unpaired trailing backtick, plain bold/italic still working). Gates green in clients/vscode: typecheck, lint (0 warnings), format:check, vitest (321/321 incl. new tests).
- [2026-07-21T20:24:26Z] Ada Typescript:
  - Addressed REV-542 F1/F2: extractCodeSpans now strips any pre-existing U+E000 sentinel from raw before extraction (unconditional guarantee, one-liner + comment). Added 6 pin tests: underscore-emphasis wrapping a code span, escaping-inside-code-span (locks no-double-unescape/no-XSS), multi-span ordering, placeholder/digit-adjacency, code span in a table cell, code span in a heading (per-call index scoping). Gates green in clients/vscode: typecheck, lint --max-warnings 0, format:check, vitest 327/327 (was 321, +6).
<!-- sq:discussion:end -->
