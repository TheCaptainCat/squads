---
id: BUG-1042
sequence_id: 1042
type: bug
title: Help on a behind-schema squad resolves addresses on stale index
status: Open
author: qa
priority: low
refs:
- REV-1033
- MILE-1051:targets
created_at: '2026-10-16T09:01:36Z'
updated_at: '2026-10-16T12:24:19Z'
---
<!-- sq:body -->
## Repro

Behind-schema squad: created with the released 0.15.0 (`sq init --roles all`, schema 0.15), then driven with the dev build (expects 0.16):

```
$ sq -C d list
error: this squad is at schema v0.15; squads ... expects v0.16. Run sq migrate up ...   (exit 1)   <- gate works
$ sq -C d task 1 show
error: this squad is at schema v0.15; ...                                              (exit 1)
$ sq -C d task 1 comment -m -m --help
error: 1 is ROLE-1 (role), not a task                                                  (exit 1)
$ sq -C d task 1 comment --help
error: 1 is ROLE-1 (role), not a task                                                  (exit 1)
```

## Expected

Either help prints and exits 0 (the gate's stated rule is "help only"), or the schema-mismatch error is shown. It must not resolve an address against a squad of the wrong schema and print an unrelated error.

## Cause

The root gate exempts `--help`, so the request reaches the type-group callback, which resolves `N` against the stale index and raises. Harmless (read-only) but it contradicts the gate rule and gives a misleading message on exactly the squads that need the migrate hint. Fix: skip address resolution when help is requested, or keep the gate for the resolver.

Found in the docs audit (REV-1033 body, "Code observation").
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
