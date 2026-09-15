---
id: BUG-935
sequence_id: 935
type: bug
title: Skew canary type-catalog floor omits labels and lifecycle keys
status: Open
author: qa
priority: low
severity: low
refs:
- BUG-896:addresses
- MILE-934:targets
created_at: '2026-09-09T14:41:36Z'
updated_at: '2026-09-09T14:46:23Z'
---
<!-- sq:body -->
## Summary

**Driven.** The VS Code skew canary's `sq workflow types --json` entry-key assertion
(`clients/vscode/test/canary/skewCanary.test.ts`, the `sq workflow types --json` describe
block) checks `Object.keys(entry)` against `expect.arrayContaining([...])` naming 7 keys:
`type`, `order`, `prefix`, `reserved`, `category`, `fields`, `subentity_kind`. The live,
frozen Python shape (`TYPE_CATALOG_FIELDS` in `src/squads/_cli/_workflow_cmd.py`) has **9**
keys — it also includes `labels` and `lifecycle`. Both are missing from the floor.

This is the same blindness class BUG-896 fixed for `sq graph --json` and `sq list --json`
(a superset assertion cannot fail on a removed key), on a surface BUG-896 didn't touch, and
here it is not only latent-class but **already drifted**: `labels` is a real, modelled,
actively-consumed field the floor does not protect at all.

## Reproduction

1. `sq workflow types --json` on a live squad — confirmed keys on the `bug` row:
   `type, order, prefix, reserved, category, subentity_kind, lifecycle, fields, labels` (9).
2. `clients/vscode/src/types.ts`'s `SqTypeCatalogEntry` interface models `labels` (optional,
   `SqTypeLabels`) and it is consumed by `domain/typeLabels.ts` (`entry.labels !== undefined`
   gate, falls back to the raw type string when absent) — a live, load-bearing client field.
3. The canary's floor list (`skewCanary.test.ts`, `sq workflow types --json` block) omits
   `labels`. Drop `labels` from the live payload today and the canary stays green while the
   client silently degrades every type's display label to its raw name — the exact failure
   mode `arrayContaining` was already shown to hide (BUG-896).

## `lifecycle` — a narrower, second gap

`lifecycle` is also emitted, also missing from the floor, but **not** modelled or read
anywhere in the client (`grep -n '\.lifecycle' clients/vscode/src` — no hits; the only
`lifecycle` match outside `types.ts` is `itemPreviewManager.ts`'s unrelated "WebviewPanel
lifecycle" comment).

Unlike `labels`, this one already has a written decision: `types.ts`'s `SqTypeCatalogEntry`
doc comment states `lifecycle` is "deliberately unmodelled … nothing in this release
publishes those [state-machine] catalogs, so it is a grouping key … with no catalog to
resolve against. Modelling it would invite a resolver for a target that does not exist."
That call predates this bug (landed in "Made the VS Code client read the spec it already
fetches").

What's still open is not *whether* to model it — that's settled — but whether the canary
should **protect the decision**: `GRAPH_NODE_KEYS`/`LIST_ROW_KEYS` both already carry
unmodelled-but-required keys (`badges`, `edge_semantic`, `created_session`, …) specifically
so their removal still reddens the canary even though the client ignores them. `lifecycle`
gets no such protection today — if `sq` stopped emitting it, nothing would notice, and the
`types.ts` doc comment describing it would go silently stale.

## Expected vs actual

- **Expected:** the type-catalog canary floor names every key the frozen `TYPE_CATALOG_FIELDS`
  shape carries, so a removed key reddens it — same guarantee BUG-896 gave graph/list.
- **Actual:** it names 7 of 9. `labels` (modelled, consumed) has zero protection; `lifecycle`
  (deliberately unmodelled, documented) has zero protection either, unlike its sibling
  unmodelled-but-guarded keys on the other two surfaces.

## Not claimed

- Not proposing the fix mechanics — converting to `assertExactKeys`/a named
  `TYPE_ENTRY_KEYS` constant is the established pattern (BUG-896) and should drop out cleanly
  for `labels`. Closing `lifecycle` needs one written call: **fold it into the exact set as an
  unmodelled-but-required key (protect the existing decision, mirroring `badges`/
  `edge_semantic`)**, or record explicitly that it stays unguarded. That call is what makes
  this more than a one-line floor update.
- Not re-filing the other six `arrayContaining` sites Ada Typescript's assessment on BUG-896
  already closed out: `bug.fields`/`finding.fields` are legitimate open-array floors (each
  member still checked exactly), and collections/statuses/roles/subentity-kinds are frozen
  shapes whose floors already name every key today — zero live risk, a mechanical follow-up
  at most.

## Severity

Judged **low**, matching BUG-896: nothing is broken today (the canary is 31/31 green against
current `sq`), the remedy is small and already proven on three sibling surfaces, and the
failure it would miss is a client display degrade (a stale label, an undetected doc comment)
rather than data loss or a wrong exit code. Not lower: `labels` is a currently-consumed field
with zero canary protection, which is a step past BUG-896's fully-latent graph/list findings.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-09T14:42:32Z] Mara Tester:
  - @tech-lead for triage. Driven and evidenced (not a guess) — same blindness class as BUG-896, on a surface it did not touch. labels is the sharper of the two: modelled + actively consumed by domain/typeLabels.ts with zero canary protection today. lifecycle needs one written call before closing: fold into the exact key set as an unmodelled-but-required key (protecting the existing "deliberately unmodelled" decision already on record in types.ts, mirroring badges/edge_semantic), or explicitly decide it stays unguarded.
<!-- sq:discussion:end -->
