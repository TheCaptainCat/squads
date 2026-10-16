---
id: BUG-1003
sequence_id: 1003
type: bug
title: ref_rule_target_present never accepts an edge of the default kind
status: Open
author: qa
priority: low
refs:
- MILE-1051:targets
created_at: '2026-10-12T05:51:11Z'
updated_at: '2026-10-16T12:24:12Z'
---
<!-- sq:body -->
## Reproduction

Released 0.15.0 tool, fresh squad (`sq init --default-names`) with this `squads/.overrides/workflow.toml` (`sq workflow lint` exits 0). `related` is the bundled default ref kind; `addresses` is the control.

```toml
# squads:override-base:0.15.0
[items.feature]
ref_rules = [{ kind = "related", target = "milestone" }]
validators = ["ref_rule_target_present:milestone"]

[items.bug]
ref_rules = [{ kind = "addresses", target = "milestone" }]
validators = ["ref_rule_target_present:milestone"]
```

One milestone (`MILE-<m>`), three features and three bugs, each moved to its delivered status (`Done` for a feature, `Verified` for a bug) with `update --status ... --force`. Edges added as follows:

```
sq feature <a> ref add MILE-<m>                    # bare, default kind
sq feature <b> ref add MILE-<m> --kind related     # default kind spelled out
sq feature <c>                                      # no edge
sq bug <d> ref add MILE-<m>                        # bare (not the rule's kind)
sq bug <e> ref add MILE-<m> --kind addresses       # the rule's kind
sq bug <f>                                          # no edge
```

Each `ref add` confirms the kind: `FEAT-<a> → MILE-<m> (related)`, `FEAT-<b> → MILE-<m> (related)`. In the item files both features store the same entry, `MILE-<m>`, with no `:related` suffix: a spelled-out default kind is stored bare.

`sq check` (exit 0, warnings only):

```
warn FEAT-<a>: settled with no related ref to a milestone — its functional contract slice may be stale
warn FEAT-<b>: settled with no related ref to a milestone — its functional contract slice may be stale
warn FEAT-<c>: settled with no related ref to a milestone — its functional contract slice may be stale
warn BUG-<d>: settled with no addresses ref to a milestone — its functional contract slice may be stale
warn BUG-<f>: settled with no addresses ref to a milestone — its functional contract slice may be stale
```

## Expected versus actual

Expected: FEAT-<a> and FEAT-<b> carry exactly the edge the rule asks for (`related` to a milestone) and are not reported, like BUG-<e> which carries the rule's kind.

Actual: all three features are reported, including the two that carry the edge. A rule declared on the default kind can never be satisfied, by either way of adding the edge, so the warning cannot be cleared.

The control behaves correctly: BUG-<e> (rule on a non-default kind, edge of that kind) is not reported, and BUG-<d> (edge of another kind) and BUG-<f> (no edge) are.

## Cause

`_ref_rule_target_present` in `src/squads/_services/_validators.py` takes each ref's kind from `split_ref`, which returns no kind for a bare ref, and tests `(kind, target_type)` against the pairs built from the rules' declared kinds. A bare ref carries no kind there, so it matches no rule whose kind is the default one. Resolving a missing kind to the spec's default kind before the comparison is one way to fix it; the choice is open.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
