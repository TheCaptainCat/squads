---
id: BUG-1037
sequence_id: 1037
type: bug
title: add-story/subtask/finding hint prints a nonexistent command
status: Cancelled
author: qa
priority: medium
refs:
- REV-1032
- BUG-1000
created_at: '2026-10-16T09:01:07Z'
updated_at: '2026-10-16T12:24:02Z'
---
<!-- sq:body -->
## Repro

Dev build (release/0.16), fresh `sq init --roles all` scratch squad:

```
$ sq create feature --author product-owner "F one"      # FEAT-21
$ sq feature 21 add-story "Story one"
added US1 to FEAT-21
  set its body:  sq story body FEAT-21 US1 -m "…"  (or --file body.md / --file -)
$ sq story body FEAT-21 US1 -m x
No such command 'story'.   (exit 2)
$ sq task 22 add-subtask "sub one"
added ST1 to TASK-22
  set its body:  sq subtask body TASK-22 ST1 -m "…"
```

The review `add-finding` hint comes from the same line and has the same shape (`sq finding body REV-n Fn`).

## Expected

The printed command runs as shown. The real form is item-first: `sq feature 21 story 1 body -m "…"`, `sq task 22 subtask 1 body -m "…"`, `sq review N finding N body -m "…"` (confirmed with `sq feature N story N body --help`).

## Cause

`src/squads/_cli/_common.py` ~611 builds `sq {kind} body {parent_id} {res.local_id}`, the pre-item-grammar form. It should build `sq {parent_type} {n} {kind} {k} body`. The hint is also what an agent copies right after scaffolding, so it sends them to a failing command every time.

Found in the docs audit (REV-1032 asides).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T12:24:01Z] Catherine Manager:
  - Duplicate of BUG-1000 (same defect: the add-<kind> body hint names a command that does not exist). Cancelled; the fix lives on BUG-1000, which covers add-story, add-subtask and add-finding.
<!-- sq:discussion:end -->
