---
id: BUG-896
sequence_id: 896
type: bug
title: Skew canary asserts an exact key set on one surface, a superset on two
status: Open
author: qa
priority: low
severity: low
refs:
- BUG-879
- MILE-867:targets
created_at: '2026-09-03T07:08:33Z'
updated_at: '2026-09-03T07:08:59Z'
---
<!-- sq:body -->
## Summary

**Driven.** The VS Code client's skew canary now asserts an exact key set for `sq tree --json`
nodes, and still asserts a superset (`expect.arrayContaining`) for `sq graph --json` nodes and
`sq list --json` rows. A superset assertion is green on an added key and on a removed one, so on
those two surfaces the one test built to notice sq/client drift cannot notice it.

The asymmetry is between surfaces, not a doubt about the approach: the tree half is proven to catch
both directions, including against a real stale `sq` on PATH.

## The two surfaces still on a superset

**Read**, `clients/vscode/test/canary/skewCanary.test.ts`:

- `sq graph --json` nodes — `arrayContaining(['id', 'type', 'status', 'priority', 'assignee',
  'edge_kind', 'direction', 'seen', 'children'])`
- `sq list --json` rows — `arrayContaining(['id', 'labels', 'refs', 'path', 'created_at',
  'updated_at', 'badges'])`

The same file's `sq workflow types --json` entry assertion and the badge/collection assertions below
it are the same shape; they are named here for completeness rather than as the subject, since the
tree/graph/list trio is what the client's structural views join on.

## What a superset cannot see

**Driven**, running both assertion shapes over identical inputs through the client's own matcher
(`@vitest/expect`'s `ArrayContaining` + `equals`, the exact semantics
`expect(...).toEqual(expect.arrayContaining(...))` compiles to):

| node under test | superset assertion | exact assertion |
| --- | --- | --- |
| carries an EXTRA unmodelled key (`path_only`) | green | **red** |
| MISSING a modelled key (a stale `sq` on PATH) | green | **red** |
| exactly the modelled key set | green | green |

Green on all three. Blind in both directions, which is the property this class of bug was filed
against in the first place.

## The tree half is proven, so the fix is known-good

**Driven**, on the surface that was tightened:

- `npm run test:canary` against `sq 0.14.0`: 23/23 green.
- the same command against the stale `sq 0.12.1` on PATH: the tree case goes red inside
  `assertExactTreeNodeKeys` with `- "anchor"` in the diff — a real missing-key catch against a real
  older binary, not a synthetic one.
- the four key-set self-tests run without `sq` present at all and pass, asserting both directions by
  construction.

So this is not "should we do it this way" — it is the same one-line change, not yet applied to two
sibling surfaces. `assertExactTreeNodeKeys` is already generic over the key list it is handed; each
surface needs a named key set and a call.

## Why it is worth tracking rather than leaving

**Read.** The client's interfaces are deliberately hand-trimmed and its runtime guards ignore
unknown keys rather than rejecting them — a documented, deliberate policy. That policy is what makes
the canary the *only* place a new `sq` field can be noticed at all: nothing else in the client will
ever complain. A superset assertion on a surface with that policy is not a weak test, it is an
absent one.

The worked example is on the record: the cycle-anchor flag rode the wire into a client that ignored
it, and every gate stayed green. Nothing says `graph` or `list` cannot grow a field the same way.

## Expected vs actual

- **Expected:** the drift test detects drift on every surface the client joins on.
- **Actual:** it detects drift on one of them, and reports green through it on the other two.

## Not claimed

- No unmodelled field exists on either surface today — **driven**: the canary is 23/23 green
  against `sq 0.14.0`, so today's key sets match the client's model exactly. This is latent, not a
  live miss.
- Not proposing which keys belong in each set beyond what the current assertions already list; that
  should be read off live output at the time of the change, not transcribed from here.

## Severity

Judged **low**.

Not lower: it is a gate that cannot fail on the condition it exists to detect, on two of the three
structural surfaces the client depends on; the remedy is known, proven on the third surface, and
small; and the client's ignore-unknown-keys policy means no other test or runtime check will ever
cover for it.

Not higher: nothing is wrong today and the canary is green against the current `sq` for the right
reason rather than by accident; it cannot corrupt anything or affect shipped behaviour; and the
failure it would miss is a rendering/feature gap on a client surface, recoverable by reading the
terminal, rather than a data or correctness fault.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
