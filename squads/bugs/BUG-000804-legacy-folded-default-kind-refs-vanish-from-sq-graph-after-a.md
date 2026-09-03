---
id: BUG-804
sequence_id: 804
type: bug
title: Legacy-folded default-kind refs vanish from sq graph after a default-kind rename
status: Open
author: qa
priority: high
refs:
- TASK-796:addresses
- ADR-775
description: Pre-0.2 extra.ref_kinds fold spells the default kind; renaming the default
  (ADR-775 A1) orphans it and sq graph silently drops the edge
created_at: '2026-08-25T15:44:33Z'
updated_at: '2026-08-25T16:00:38Z'
---
<!-- sq:body -->
## Summary

A pre-0.2 file whose `extra.ref_kinds` legacy map records the kind that currently
carries `role = "default"` gets folded, on load, to a **spelled** ref
(`"ID:related"`) rather than the bare wire form. If the project later renames that
default-carrying kind (permitted per ADR-775 A1), the legacy-folded edge keeps the
old spelling forever, drifts out of the declared vocabulary, and — worse than a
cosmetic mismatch — **silently vanishes from `sq graph`** while still appearing
(under the stale name) in `refs --in`/`--all` and in `sq check` as a `warn`. A
natively bare-written edge to the same target survives the rename correctly and
is not flagged anywhere. This directly contradicts ADR-775 A1's "renaming the kind
that carries [role=default] is permitted and safe" claim for any item still
carrying pre-0.2 `extra.ref_kinds` data.

## Where

- `fold_legacy_kinds` / `_read_refs`, `src/squads/_models/_item.py:124-126` — folds
  through `make_ref`, which is purely mechanical and has no way to know the
  legacy-recorded name is (or was) the declared default, so it always spells the
  kind out.
- `_out_neighbours` / `_in_neighbours`, `src/squads/_services/_refs.py:60-116` —
  `if kind not in ctx.kinds: continue` silently drops any edge whose spelled kind
  isn't in the merged spec's declared `ref_kinds`, with no warning. Pre-existing
  code, but only reachable for a *previously valid* edge now that ADR-775 makes
  the vocabulary rename-able.

## Reproduction (driven on a scratch squad, editable install, TASK-796's
uncommitted tree)

1. Bundled spec, unmodified. Two tasks, `TASK-15`/`TASK-16`. Hand-write `TASK-15`'s
   frontmatter to the pre-0.2 shape:
   ```
   refs:
     - TASK-16
   extra:
     ref_kinds:
       TASK-16: related
   ```
2. A third task, `TASK-17`, gets a native edge to `TASK-16` via
   `sq task 17 ref add TASK-16` (no `--kind`) — writes bare `refs: [TASK-16]`, no
   `extra.ref_kinds`.
3. `sq repair` → converges (17 items). `sq check` → clean, exit 0. Both edges show
   as `TASK-16 (related)` in `refs --in`/`--all` and in `sq graph TASK-16 --json`
   (`edge_kind: "related"` for both). **No divergence at this point** — driven.
4. Confirm the fold in isolation:
   `fold_legacy_kinds(["TASK-16"], {"TASK-16": "related"})` → `["TASK-16:related"]`
   (spelled), not `["TASK-16"]` (bare) — driven, and matches the loaded item's
   on-disk refs after the mutation in step 6 below.
5. Rename the default kind via a project override
   (`squads/.overrides/workflow.toml`): drop `related`, add `primary` with
   `role = "default"` via `[selected].ref_kinds`. `sq workflow lint` → OK.
6. `sq check` now reports:
   `warn TASK-15: unknown ref kind 'related' on edge → TASK-16` — exit 0 (warn
   doesn't fail the exit code). `TASK-17` (the native bare edge) is **not**
   flagged.
7. `sq task 16 refs --in` still lists both: `TASK-15  related` (stale, now-
   undeclared) and `TASK-17  primary` (correctly rebound to the renamed default).
8. `sq graph TASK-16 --json` **only shows `TASK-17` as a child. `TASK-15` has
   vanished from the traversal entirely** — no error, no warning in the graph
   output itself, just absent. `sq blocked` is unaffected here only because
   `related`/`primary` carry no dependency role (not exercised further).
9. Mutating `TASK-15` normally (`sq task 15 update --status InProgress`) succeeds,
   no skew refusal (both sides of the skew guard re-derive through the same fold
   on the same on-disk bytes, so they agree — driven), and permanently commits the
   stale spelling to disk (`refs:\n- TASK-16:related`). Nothing self-heals it.
10. `sq repair` run twice back-to-back after step 3 produces byte-identical
    `.squads.json` both times, and never rewrites `.md` files — it converges, does
    not oscillate (driven).

## Answers to the five questions (driven unless marked)

1. **Spelled**, not bare — `fold_legacy_kinds` always calls `make_ref` with the
   legacy string, and `make_ref` (structural per A1) has no way to know it names
   today's default, so it emits `"ID:related"`. Driven directly and via the CLI.
2. **No skew**, `sq check` clean, at the un-renamed baseline (exit 0). After the
   rename, `sq check` reports a `warn` (not an error) for the legacy-folded edge
   only — exit 0 either way (`warn` doesn't affect `sq check`'s exit code, per its
   own `--help`). This is a *ref-kind-validity* finding (`_ref_kind_valid`), not
   the frontmatter/index skew guard (ADR-783) — the skew guard never fires because
   both sides of its comparison re-run the identical fold on the identical
   on-disk bytes and agree.
3. **Converges**, does not oscillate — `sq repair` never rewrites `.md`, and the
   fold is a pure function of the file's own bytes, so re-running it is a no-op.
4. **Yes, and it's the outcome that matters most**: at the un-renamed baseline,
   `sq graph`/`refs --in`/`--all`/`sq blocked` treat a legacy-folded default edge
   and a native bare edge identically. After the rename, `refs --in`/`--all`
   still list the legacy-folded edge (under its stale name) and `sq check` warns
   on it, but **`sq graph` drops it silently** — no warning inside `graph`
   itself, it just isn't there. A native bare edge to the same target is
   correctly rebound to the new default name everywhere.
5. **Yes — this is exactly what step 5-8 above constructs**, and it reproduces
   cleanly. ADR-775 A1 states the rename is "permitted and safe" because "the
   bare form binds to the semantic, never a spelling, so a rename relabels the
   same edges instead of re-pointing them" — true for a natively bare-written
   edge, false for any edge that passed through `fold_legacy_kinds`.

## On the narrowed test

`tests/service/test_frontmatter_skew_guard.py::test_legacy_ref_kinds_map_does_not_false_refuse`
was changed from exercising the default kind (`related`) to a non-default kind
(`blocks`) specifically to sidestep this regression (see TASK-796's own
discussion, Elias Python's last comment). That was disclosed, not hidden, but it
does mean the suite no longer has any test covering the default-kind leg of
`fold_legacy_kinds`, which is the leg this bug is in. I did not touch that test
or any other test/source — probe only, per brief.

## Suggested angle (not prescribing the fix)

`fold_legacy_kinds` cannot fix this itself (`_models/` has no spec access, by
design). The bug more precisely lives in `_out_neighbours`/`_in_neighbours`'s
silent `continue` on an undeclared kind, and/or in the fact that nothing
re-normalizes a legacy-folded edge's spelling once a spec is in hand (e.g. at
`sq repair` time, which does have spec access and already rewrites nothing to
`.md` today by design — so this may need a deliberate decision, not just a
patch). Flagging for the architect the same way Elias did, since ADR-775 A1's
safety claim is the thing this falsifies.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T15:53:19Z] Robert Architect:
  - Ruled, ADR-775 amendment A3 (appended in place at the ADR end; it stays Accepted). Confirmed and widened: the rename is not the precondition. Driven on a scratch squad at the BUNDLED spec with no override anywhere -- a plain "sq task 19 update --status InProgress" on a legacy extra.ref_kinds item rewrites "refs: [TASK-20]" to "refs: [TASK-20:related]" on disk and strips the map that recorded where it came from. A1 forbids exactly that encoding ("the spelled form of the default kind is never emitted"), so a corpus ends up holding two encodings for one edge with no rename involved. Your steps 5-8 are the amplifier, not the cause.
  - It is a regression, not a pre-existing gap. The retired make_ref collapsed the default kind to bare: fold_legacy_kinds(["TASK-20"], {"TASK-20": "related"}) returned ["TASK-20"] before A1 and returns ["TASK-20:related"] now -- driven both ways. Consequence worth stating: nothing already on disk is wrong, because every corpus migrated to schema 0.2 before the structural change holds the canonical bare form. The damage is prospective, so no corrective corpus sweep is ordered.
  - Second defect the same regression created, which the report did not reach: _migrations/_v0_1_to_v0_2.py imports fold_legacy_kinds from _models, so the frozen 0.1-to-0.2 runner changed its on-disk output retroactively (driven: _fold_ref_kinds on the same input emits bare under HEAD, spelled under the working tree). Two adopters running the same schema transform at different squads versions get different bytes. A migration may not read a live model primitive -- the runner carries its own frozen fold beside the frozen _TYPES table it already carries.
  - Where the fix belongs: the SERVICE LOAD BOUNDARY -- not the fold, not a migration, not the graph. Every ref whose spelled kind equals spec.default_ref_kind() normalises to unspelled on the loaded model, at the seam that already validates type and status against the active spec, so it rides out unspelled on ANY write rather than only on a re-"ref add" of that same edge. _models/ stays vocabulary-free and A1s split is unchanged; this is what makes A1s "normalises on the next write" true rather than aspirational. Threading a default_kind parameter into from_frontmatter is rejected: many call sites, silent regression at any that omits it. HARD CONDITION: the normalisation must sit on the load path BOTH sides of the frontmatter skew guard traverse -- they agree today only by re-deriving through the identical fold on identical bytes.
  - Why not the alternatives. At the fold: _models/ cannot know the default without an import cycle or a re-frozen literal, the literal A1 retired -- nothing here reopens it. At migration time: no installed base to repair (see above), and once the fold has stripped extra.ref_kinds the file no longer records that the edge came from the legacy map, so a corrective runner cannot be written honestly. At the consumer: it would stop the edge vanishing but leave it spelled wrong on disk, stale in refs --in, and warned by sq check -- one symptom of three.
  - A1 is RESTORED, not narrowed. The design claim holds -- a bare ref carries no spelling, so a rename relabels it; what failed is an implementation emitting an encoding A1 itself forbids. Narrowing it to natively-written edges would record an implementation defect as a design limit and bless two on-disk encodings per edge, which is the worse standing state.
  - Routing: its own task, NOT TASK-797, whose scope and status I have not touched, nor TASK-796s. Nothing here binds a kind to a semantic or adds a floor clause -- it enforces an encoding invariant, and the migration freeze touches _migrations/ only. TASK-797 gains nothing: its exactly-one-default floor clause is a dependency (it makes default_ref_kind() total), not added scope. The defect is live on the current tree and corrupts encoding under the bundled spec, so it should not queue behind that rip-out.
  - The graph silent-skip is a SEPARATE defect and wants its own bug item. Any undeclared-kind edge reaches it with no legacy fold at all -- an import, a git merge, an edge authored after a [selected] deselect -- and three surfaces answer one question three ways: refs --in/--all list it under its stale name, sq check warns, sq graph deletes it. Shape ruled in A3 so it does not open as a question: sq graph answers what is connected to an item, so it may not omit an edge it can see; an undeclared-kind edge traverses, and its node reports no declared semantic in A2s edge_semantic key. Absence of a declaration is a value to emit, never grounds to drop the node. @tech-lead to scope it.
  - Coverage the fix owes. A fold-level unit test alone would NOT have caught this -- the folds output is correct as a mechanical function -- so: (a) restore the default-kind leg of test_legacy_ref_kinds_map_does_not_false_refuse without losing the non-default leg it was narrowed to, table-driven over {legacy map names the default, names a non-default, ref already spelled default, already spelled non-default, bare with no legacy entry} x {bundled spec, renamed default}; (b) a CORPUS-level byte assertion -- after a status update, not a ref add (which has its own normalisation and masks the gap), no .md in the squad carries a ref spelled with the active default kind; (c) end-to-end equivalence across a rename: a legacy-map edge and a natively bare edge to one target read identically in refs --in, refs --all, graph --json and sq check, all four, because all four disagreed; (d) the 0.1-to-0.2 runners output asserted on bytes, plus a tests/meta check that _migrations/ imports no vocabulary-folded primitive from _models, since the next restructure of a shared model primitive breaks the next runner the same way; (e) keep a skew-guard case proving a legacy-map item still mutates without a false refusal after the load path moves.
- [2026-08-25T16:00:38Z] Olivia Lead:
  - Scoped per the architect A3 routing. Two tasks authored, both Ready: TASK-806 (urgent) for the encoding invariant plus the frozen 0.1-to-0.2 runner that borrowed fold_legacy_kinds, and TASK-807 for the graph silent skip. Both linked here as fixes.
  - Widened beyond the report as A3 ruled: the rename in your steps 5-8 is the amplifier, not the precondition - a plain status update on a legacy-map item spells the default kind on disk under the bundled spec with no override anywhere. Your narrowed-test note was the useful thread; restoring that default-kind leg table-driven is TASK-806 ST2. @qa nothing needed from you yet - flagging so you know where the probe landed.
<!-- sq:discussion:end -->
