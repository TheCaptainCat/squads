---
id: BUG-1014
sequence_id: 1014
type: bug
title: Untouched scaffold reads as written once target_ref is set
status: Open
author: qa
refs:
- REV-1010
- TASK-1001
description: Body guard and body_written compare against a re-render, so a changed
  scaffold input hides the stub
created_at: '2026-10-15T19:36:06Z'
updated_at: '2026-10-15T19:36:06Z'
---
<!-- sq:body -->
## Reproduction

Driven in a fresh scratch squad on sq 0.15.0 (the overwrite-guard half).

1. `sq create review "r" --author reviewer` (no target_ref)
2. `sq review 9 update --set target_ref=zzz`
3. `sq review 9 body -m x`

## Expected

The body is still the untouched scaffold (`## Scope` and the placeholder line), so `body -m` replaces it.

## Actual

`error: REV-9 already has a body (3 lines); setting one would discard it`, listing the untouched scaffold lines, and "Nothing was written". The guard compares the stored body with the scaffold re-rendered from the item's current fields. Once target_ref is set, the re-render gains a Target line the stored body never had, so the scaffold no longer matches and reads as written.

The unwritten-body check (`body_written`) shares this comparison, so `sq check` goes silent on the same scaffold. That half was not run on 0.15.0; it rests on the 0.16 code reviewed in REV-1010 finding F6.

## Cause

Nothing records the scaffold inputs at creation (target_ref, or the type for the default template). Any template that interpolates a field that later changes has the same blind spot: the default item template names the type, so a retype hits it, and the review template reads target_ref.

## Versions affected

0.15.0 for the overwrite guard (reproduced); the guard predates 0.16. The unwritten-body report built on the same comparison is part of the 0.16 work.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
