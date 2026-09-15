---
id: BUG-896
sequence_id: 896
type: bug
title: Skew canary asserts an exact key set on one surface, a superset on two
status: Verified
author: qa
assignee: typescript-dev
priority: low
severity: low
refs:
- BUG-879
- MILE-867:targets
created_at: '2026-09-03T07:08:33Z'
updated_at: '2026-09-09T14:43:35Z'
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
- [2026-09-08T14:52:37Z] Ada Typescript:
  - Fixed the asymmetry: `test/canary/skewCanary.test.ts` now asserts an exact key set on graph and list too (GRAPH_NODE_KEYS/LIST_ROW_KEYS via a shared assertExactKeys helper), replacing both arrayContaining checks. Added a "the graph-node key assertion" and "the list-row key assertion" describe block (4 tests each, no sq needed), mirroring the existing tree one.
    
    Driven (falsified against real sq 0.15.0 on PATH, not just the hermetic self-tests): for both surfaces I temporarily dropped one key from the expected set (added-key direction) and separately added a bogus expected key (removed-key direction) and re-ran the live-sq integration test each time — reddened on all four cases with a clear diff, then restored and confirmed 31/31 green again. Full transcript kept in-session, not committed.
    
    Stale key sets, found while reading live output (not transcribed from the old superset lists):
    - graph nodes carry `badges` (GraphNode's additive badge axis, landed earlier this project under FEAT-336/TASK-370) and `edge_semantic` — neither was in the old 9-key arrayContaining list, so this was latent, undetected drift even before this fix.
    - list rows are the full `Item` model dump (`i.model_dump(mode="json")`) plus resolved badges — 22 keys, not the 7 the old superset list named.
    I did not widen SqGraphNode/SqListItem to model the extra keys (graph's badges; list's created_session/modified_session/extra/subentities) — no consumer reads them (graphDiagrams.ts colors off status/priority only; listView.ts never touches those 4), matching types.ts's own documented hand-trim policy. Decided in writing in the new constants' doc comments; the canary still requires their presence so a future removal reddens it even though the shape guard ignores them.
    
    Gates (clients/vscode/, TypeScript held at 6.0.3, type-aware lint untouched): `npm run check` (typecheck+lint+format:check) clean; `npm run test:canary` 31/31 green against sq 0.15.0; `npm test` 624/624 green.
    
    Touched only clients/vscode/test/canary/skewCanary.test.ts — nothing under src/squads/ or tests/.
- [2026-09-08T14:53:46Z] Catherine Manager:
  - Fixed and committed. Client gates green: npm run check clean, test:canary 31/31 (was 23/23) against a live sq 0.15.0, npm test 624/624, TypeScript untouched at 6.0.3 with the type-aware lint layer intact. Verified the scope claim myself -- only the canary file changed, nothing under src/squads or tests.
  - The fix found more than the bug: both superset lists were ALREADY stale. graph --json nodes carry badges and edge_semantic that were never in the 9-key list, and list --json rows are 22 keys not 7. That is latent undetected drift predating the fix, which is exactly what a superset assertion hides -- so the bug was worth more than its severity suggested. The dev cited where the drift came from rather than silently updating, and deliberately did not widen the client types for keys no consumer reads while keeping the canary requiring their presence so a removal still reddens.
- [2026-09-08T15:00:31Z] Ada Typescript:
  - Class-closure assessment of the seven remaining `expect.arrayContaining` assertions, as requested. No fix applied — two doc comments added beside the two that are legitimate floors, everything else is report-only. `uv run sq check` clean; client gates green throughout.
    
    **Method:** for each, I read the Python builder backing the `sq workflow <x> --json` payload (`_cli/_workflow_cmd.py`) to see whether the row is a closed/frozen shape (a named `*_CATALOG_FIELDS` tuple) or a genuinely open one, then compared that against the current live output and the client's own TS interface (does the client already model/consume the field the floor is missing).
    
    **1. `sq workflow types --json` entry keys (~line 524) — SAME BLINDNESS, and it IS already drifted.**
    The Python row is a frozen 9-key shape (`TYPE_CATALOG_FIELDS`), confirmed live: `category, fields, labels, lifecycle, order, prefix, reserved, subentity_kind, type`. The canary's floor names only 7 — it is missing `labels` AND `lifecycle`.
    - `labels` is modelled by `SqTypeCatalogEntry` (optional) and actively consumed (`domain/typeLabels.ts`, `isOptionalTypeLabels` guard) — this is exactly the graph/list hole: if `sq` stopped emitting it, nothing would go red.
    - `lifecycle` is emitted but not modelled or read anywhere in the client (`grep .lifecycle src` finds nothing but an unrelated webview comment) — same shape as graph's `badges`: needs a "model it or decide in writing" call, which the floor doesn't even let a maintainer make since it isn't named.
    Recommend a bug of its own — this is evidenced drift, not a guess, and closing it needs a decision on `lifecycle` (model vs. document-and-ignore) rather than a one-line floor edit.
    
    **2 & 3. `bug.fields` (~line 555) and `finding.fields` (~line 663) — legitimately supersets.**
    Neither is a key-set assertion on an object; both check that an ARRAY (a type's or kind's declared field->collection bindings) contains at least one known member. That array's length is genuinely open — a project adds a custom field, the array grows, nothing is wrong. Each named member is still checked for its own exact `{code, label, collection}` shape via `toEqual`'s recursive equality (`FIELD_ENTRY_FIELDS` on the core side), so this isn't under-testing the member's shape, only (correctly) not enumerating the whole array. Documented in place with a comment beside each, same style as the hand-trim policy note.
    
    **4, 5, 6, 7. `sq workflow collections/statuses/roles/subentity-kinds --json` entry keys (~lines 581, 608, 638, 696) — same mechanism, currently NOT drifted.**
    All four Python rows are also frozen tuples (`COLLECTION_CATALOG_FIELDS` 5, `STATUS_CATALOG_FIELDS` 3, `ROLE_CATALOG_FIELDS` 5, `SUBENTITY_KIND_CATALOG_FIELDS` 8) and I confirmed live output matches each exactly. The canary's floor for every one of these already names 100% of the frozen key set — unlike the types-catalog case, nothing modelled or emitted is left unchecked today. The only remaining gap is the structural one: `arrayContaining` still can't fail on a brand-new key nobody's named yet.
    Cost to close: zero today — converting each to `assertExactKeys` (the helper is already there) would not redden a single current test, since floor == full frozen set already; it only adds protection against a *future* addition. I'd class these as the same mechanism but not the same live bug — worth doing as one mechanical follow-up pass alongside or after the types-catalog bug, but not urgent and not evidence of a second latent defect.
    
    **Recommendation:** file the types-catalog gap (`labels`/`lifecycle`) as its own bug — it's real, evidenced, and needs a modelling decision on `lifecycle`. The four zero-drift closed-shape assertions (collections/statuses/roles/subentity-kinds) are safe to fold into the same follow-up as a zero-risk exactness pass, or left as-is; either way they don't need urgent action since nothing is currently unmonitored.
- [2026-09-09T14:42:27Z] Mara Tester:
  - Verified independently. Read skewCanary.test.ts myself: tree/graph/list all now use assertExactKeys via GRAPH_NODE_KEYS (11 keys, incl. badges + edge_semantic) and LIST_ROW_KEYS (22 keys) — confirmed the stale-list claim by counting the old vs new sets directly, not by trusting the handback prose.
  - Falsified rather than just re-ran the shipped tests: temporarily dropped "badges" from GRAPH_NODE_KEYS and ran the live-sq integration block (npx vitest -t graph) — reddened with a real diff against a real sq 0.15.0 payload ("+ badges" unexpected extra key), confirming the exact-set assertion actually catches the removed-key direction the old superset was blind to. Restored the file; git diff clean, npm run test:canary back to 31/31 green.
  - Reran client gates myself from scratch: npm run test:canary 31/31, npm run check (typecheck+lint+format:check) clean, npm test 624/624. package.json confirms typescript ^6.0.3 and typescript-eslint ^8.64.0 with projectService (type-aware lint) still wired in eslint.config — nothing weakened there.
  - sq workflow types --json live-checked: bug row carries 9 keys incl. labels + lifecycle, matching TYPE_CATALOG_FIELDS in src/squads/_cli/_workflow_cmd.py. That is the 7th arrayContaining site from the follow-up assessment, and it is real drift, not a guess — filed as BUG-935 (targets MILE-867, addresses this bug). The other six sites in the assessment are not being re-filed: bug.fields/finding.fields are legitimate open-array floors, and collections/statuses/roles/subentity-kinds already name every frozen key.
<!-- sq:discussion:end -->
