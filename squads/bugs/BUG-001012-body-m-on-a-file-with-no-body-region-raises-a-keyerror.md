---
id: BUG-1012
sequence_id: 1012
type: bug
title: body -m on a file with no body region raises a KeyError
status: Fixed
author: qa
refs:
- REV-1010
description: Raw traceback instead of a SquadsError when the body region is missing
created_at: '2026-10-15T19:27:55Z'
updated_at: '2026-10-15T20:33:21Z'
---
<!-- sq:body -->
## Reproduction

Driven in a fresh scratch squad on sq 0.15.0 (`sq init --backend none --default-names`).

1. `sq create task "t" --author tech-lead`
2. Delete the body marker region (the sq:body open and close tags and everything between) from the task `.md` file.
3. `sq task 9 body -m "new prose"`

## Expected

A `SquadsError` message (clean one-line error, exit 1) saying the item has no body region.

## Actual

A rich traceback ending in `KeyError: "section 'body' not found"`, raised at `_sections.replace_section`, exit 1. `sq check` does not report the missing region either.

## Versions affected

Reproduced on 0.15.0. The code path predates the 0.16 work in REV-1010; it is not caused by it.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
