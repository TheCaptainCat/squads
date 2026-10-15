---
id: BUG-1011
sequence_id: 1011
type: bug
title: sq console text drops a backslash before a bracket
status: Fixed
author: qa
refs:
- TASK-1001
description: e() is plain rich escape, so a \[ in user text prints without its backslash
created_at: '2026-10-15T19:27:50Z'
updated_at: '2026-10-15T20:33:19Z'
---
<!-- sq:body -->
## Reproduction

Driven in a fresh scratch squad on sq 0.15.0.

1. `sq create task "t" --author tech-lead` (no feature parent)
2. `sq task 9 add-subtask x --story '\[A-Z]+-\d+\]'`

Output: `error: TASK-9 has no feature parent; set one before mapping a subtask to [A-Z]+-\D+\]`

The backslash before `[A-Z]` is gone (the `\d` to `\D` change is the story id being upper-cased and is unrelated).

The same loss shows on the helper alone: `rich.markup.escape(r'\[A-Z]+-\d+\]')` returns the string unchanged, and `Console.print` of it renders `[A-Z]+-\d+\]`.

## Expected

The text prints exactly as given. `--json` output is exact for the same text.

## Actual

`e()` in `src/squads/_cli/_common.py` is plain `rich.markup.escape`. It leaves a `\[` that does not open a lowercase tag unescaped, and Rich then consumes the backslash as an escape on render. Any console path printing user text through `e()` loses it.

## Not reached through sq check

No `sq check` message on 0.15.0 echoes user text containing `[`, so the bug was reproduced through the error path above. It was found in the 0.16 work on TASK-1001, where a finding message holding the pattern `\[[A-Z]+-\d+\]` printed as `[[A-Z]+-\d+\]` in text mode.

## Versions affected

0.15.0 (reproduced).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
