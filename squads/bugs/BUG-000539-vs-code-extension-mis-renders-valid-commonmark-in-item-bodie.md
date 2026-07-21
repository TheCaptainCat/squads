---
id: BUG-539
sequence_id: 539
type: bug
title: VS Code extension mis-renders valid CommonMark in item bodies
status: Open
author: op-pierre
priority: medium
refs:
- BUG-535
description: 'Extension body renderer mangles valid CommonMark: bold-wrapped inline
  code and a ''*'' inside a code span break out, unbalance emphasis, and the code
  span runs on.'
created_at: '2026-07-21T15:24:45Z'
updated_at: '2026-07-21T15:25:10Z'
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
<!-- sq:discussion:end -->
