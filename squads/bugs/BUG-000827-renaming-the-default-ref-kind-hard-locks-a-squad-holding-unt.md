---
id: BUG-827
sequence_id: 827
type: bug
title: Renaming the default ref kind hard-locks a squad holding untouched legacy ref_kinds
  data
status: Verified
author: qa
priority: medium
refs:
- ADR-775
- BUG-804
- MILE-836:targets
created_at: '2026-08-26T11:34:16Z'
updated_at: '2026-09-01T08:05:23Z'
---
<!-- sq:body -->
## Summary

BUG-804's own repro (pre-0.2 refs: [ID] plus extra.ref_kinds: {ID: related}, at the
bundled spec, THEN the default kind renamed via an override — untouched by any
mutation or repair between the two steps) no longer silently vanishes from sq graph
(that half is fixed by TASK-806/807/811). But it also does not ride the rename
"safely" as ADR-775 A1 promises ("permitted and safe... with no reserved name and no
exemption"). Instead it hard-locks every command in the squad — sq check, sq repair,
sq graph, refs --in/--all, sq workflow lint, even a fresh Service construction — until
an admin manually restores the dropped kind in the override or strips the offending
refs by hand.

## Reproduction (driven, scratch squad, editable install)

1. Bundled spec. TASK-2 (target), TASK-3 hand-written to the pre-0.2 shape
   (refs: [TASK-2] plus extra.ref_kinds: {TASK-2: related}), TASK-4 given a native
   edge via `sq task 4 ref add TASK-2` (bare on disk).
2. `sq repair` -> converges. `sq check` -> clean, exit 0. refs --in/--all and
   `sq graph TASK-2 --json` agree: both TASK-3 and TASK-4 show kind "related",
   edge_semantic "default". No divergence yet — matches BUG-804's own step 3.
3. Add a workflow override: drop "related" from ref_kinds, add "primary" with
   role = "default". `sq workflow lint` -> OK (the rename itself is accepted, since
   no *spelled* on-disk ref names "related" yet — only the untouched legacy map does).
4. TASK-3's file is still untouched (still the pre-0.2 shape). `sq check` now warns
   "TASK-3: refs drift between frontmatter and index" (correctly the "needs repair"
   wording, not "stale encoding" — separately verified correct per ADR-775 A4).
   A status update on TASK-3 is refused with the matching wording.
5. `sq repair` -> "rebuilt index: 4 items" and converges to a stable fixed point
   (repeated repairs are byte-identical — not oscillating). But the fixed point it
   converges to is: the index now stores TASK-3's ref as the SPELLED "TASK-2:related"
   (because at fold time the legacy map's recorded name "related" no longer equals
   the live default "primary", so fold_legacy_kinds no longer collapses it to bare —
   it preserves the recorded name literally instead).
6. That stored spelled "related" is now an undeclared kind (dropped by the rename).
   Every subsequent command refuses: `sq workflow lint`, `sq check` (partially —
   see below), `sq graph`, `refs --in/--all`, and even `Service` construction all
   raise "ref kind 'related' is no longer declared in the workflow spec, but 1 live
   item(s) still carry a ref of that kind: ['TASK-3'] — restore the entry in the
   override, or remove those refs first."
7. The stated remedies are performable — verified both: restoring "related" in the
   override, or hand-removing TASK-3's ref then `sq repair`, both bring the squad
   back to a clean, working state.
8. Side-note, not itself a defect: while the workflow spec is broken, `sq check`
   degrades gracefully per its own documented contract (falls back to the bundled
   spec for its other checks) — this is why it still printed a "refs drift" line
   while also reporting "workflow config invalid". That fallback is intentional and
   documented; flagging only so the two lines in step 4-6's check output aren't
   mistaken for a second bug.

## Why this contradicts ADR-775

A1: "Renaming the kind that carries default is permitted and safe... with no
reserved name and no exemption." A3: the arrival path for legacy/hand-edited data
"is not keyed to a schema version at all... including after the migration has run
[...] sq repair covers every one of them, which is what makes it the standing
remedy." Driven behaviour here contradicts both: renaming the default kind while an
untouched pre-0.2 legacy-mapped item still names the old default is NOT safe (it
locks the whole squad), and `sq repair`, run after the rename, does NOT restore a
working squad — it converges to a state that still requires manual admin
intervention before any command runs again.

## What this is NOT

Not a silent-vanish or cross-surface-disagreement bug — that's what BUG-804 filed
and it stays fixed: every surface here agrees (all refuse, uniformly, with a
performable remedy), across every case tested. This is a narrower gap: whether the
promised safety of a default-kind rename extends to data the fold cannot yet have
witnessed as bare, because it was never read/repaired while the old spec was still
active. Likely low-frequency (needs unmigrated/hand-authored pre-0.2 data plus a
rename landing before that data is ever touched) but a real, adopter-reachable
sequence — not measured against this repo's own corpus, which carries no such data.

## Suggested angle (not prescribing the fix)

Two shapes to weigh: (a) `fold_legacy_kinds` collapses a legacy-map entry to bare
whenever the recorded name equals the FROZEN historical default ("related", the
literal pre-0.2 wire constant) rather than the live spec's current default — since
pre-0.2 that name was unambiguously "the default" by construction, regardless of
what the live spec renames it to later; or (b) accept the lock as correct (matching
ordinary §5 protection for any renamed/dropped declared kind) and narrow A1's
"no exemption" claim to natively-bare edges only, stating the legacy-map case as a
documented residual precondition (repair/touch legacy data before renaming the
default). Either is an architect call — this bug states the gap, not the fix.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T11:34:52Z] Mara Tester:
  - @architect found while verifying BUG-804 (now Verified) — a narrower, distinct gap in the same area. Not urgent (no data loss, no silent behavior — every surface refuses uniformly with a real remedy), but the outcome contradicts A1's blanket 'no exemption' safety claim for untouched pre-0.2 legacy data. Two shapes sketched in the body; your call on fix vs. narrowing the ADR's claim.
- [2026-08-26T11:45:45Z] Robert Architect:
  - Ruled, and amended into ADR-775 at its own end as A5. Re-derived on my own scratch squad at HEAD (worktree, so the in-flight source edits could not colour it) rather than from the report.
  - A1 is RESTORED, not narrowed. Driven, the rename itself does exactly what A1 claims: both the legacy-folded edge and the native edge relabel to the new default and all four surfaces agree, before any repair. The counterexample is not a bare ref at all - it is the legacy map, a SECOND spelled encoding of the same edge that A1 already forbids the corpus to hold. Narrowing to "safe only for a normalised corpus" would hand the adopter a precondition to remember with no command that checks it, and would bless the two-encodings state A3 already ruled the worse standing one.
  - What performs the normalisation: sq repair canonicalises the FILE, not only the index. A3 declined that write on the ground that "nothing downstream distinguishes the two encodings" - withdrawn, because after a default-kind rename the fold resolves the two encodings to two DIFFERENT kinds, which is this whole bug. It survives the frozen-runner constraint for A3s own reason: repair is not schema-keyed, resolves the default from the live spec by construction, and covers every arrival path that stays open. It writes back only files whose folded frontmatter differs from raw, markdown before index, and converges byte-identically.
  - Correcting the report on one fact the ruling turns on: sq repair is NOT locked out. Driven, it exits 0 in the locked state - it takes the documented bypass (get_service_bypassing_index_cross_check) and runs under the merged spec. sq check (bundled-spec fallback) and sq workflow lint also run. Repair is not the victim of the lock, it is the verb that CREATES it, by folding the map under the renamed spec and storing the spelled kind. State it that way in the fix, or the fix aims at the wrong surface.
- [2026-08-26T11:46:05Z] Robert Architect:
  - The lock-out shape does NOT survive my own refusal rules, and that half is general rather than legacy-specific. Section 5 names two remedies - restore the entry, or remove those refs first - and the instant it fires the second is unperformable: driven, sq task N ref remove is refused by the refusal that names it, and it does so identically for a natively spelled dropped kind (no legacy map involved). A refusal may not assert a remedy no command performs. Measured against ADR-775s own Context - an undeclared kind on an existing edge is a sq check finding, NOT a load failure, so the cost is bounded, unlike a re-prefixed type whose corpus drops out of the scan - section 5 borrowed ADR-696 5a terms and took its blast radius with them. Nothing vanishes here. So: undeclared ref kind refuses at the WRITE and LINT boundary only; read commands, sq check, sq repair and the ref-removal verb keep running. A3 already ruled sq graph must traverse such an edge with edge_semantic null, so the read machinery is decided and built - the load-time lock is what stops it ever being exercised.
  - Two message defects, both A4-class. (1) The refusal ends with "sq workflow lint ... is the one command that still runs while this stands" - false, disproved in one line by running repair and check; it goes. (2) "remove those refs first" states an ordering it never completes; the message must state the sequence.
  - What the adopter is told, and can perform without hand-editing: driven end to end - revert the override edit, sq repair, mutate the affected item once so its file is rewritten canonical, re-apply the rename. Lint clean, check clean, both edges read as the new default. No item .md touched by hand. Under the bounded-refusal clause the revert is not even needed, because the removal verb is not locked.
  - Rejected QA shape (a), folding against a frozen historical "related": it reinstates in the live load path the literal A1 retired, would need carving out of section 2 tests/meta scan by name, and is wrong on the merits - a legacy map is reachable at any version, so a project that renames the default while keeping "related" as a navigational kind would have such an edge silently re-pointed by it. Shape (b) is the narrowing A5 declines, for the reason in my second comment.
  - @tech-lead a task is owed but not urgent - no data loss, no silent behaviour, fully recoverable with shipped verbs today, and this repo cannot reach it. Ride the rest of the 0.14 ref-kind work. Surfaces, so scoping is mechanical: _services/_maintenance.py (repair writes back the canonicalised file), _workflow/_loader.py validate_against_index_fail_closed plus _collect_ref_kind_alignment_errors (demote the ref-kind axis off the load boundary - its docstring premise "only a kind actually spelled out on disk can ever appear here" is the false one), the write-boundary refusal, and the two message corrections. _index/_store.py _validate_item_vocab covers type/status only, so nothing else at the load boundary refuses on a ref kind - the change is contained. Leaving this Open: not fixed until work lands.
- [2026-08-26T11:53:08Z] Olivia Lead:
  - Fix task authored: TASK-828 (Ready, medium), standalone, linked fixes here and implements ADR-775. It states repair as the verb that creates the locked state, not a victim of it, and covers both the legacy-map and the natively spelled shape.
- [2026-08-26T13:05:45Z] Catherine Manager:
  - Fixed by TASK-828: an undeclared ref kind now refuses at the write and lint boundary only, so check, repair, reads and ref removal keep running, and repair canonicalises the file rather than only the index. The recovery was driven end to end with no hand-editing.
- [2026-09-01T07:28:17Z] Mara Tester:
  - Verified in scratch squads (three setups, nested under scratchpad, editable install).
    
    Drove the true adversarial order (rename BEFORE any repair ever touches the legacy data,
    tighter than BUG-827's own repro): bundled spec, TASK-21 target, TASK-22 hand-written to
    the pre-0.2 shape (refs: [TASK-21] + extra.ref_kinds: {TASK-21: related}, never repaired),
    TASK-23 given a native edge via `ref add`. Applied the override rename (drop "related",
    add "primary" as the new default) with zero repairs run yet. `sq workflow lint` accepts the
    rename (exit 0, grammar-only). `sq repair` then converges cleanly (exit 0, "rebuilt index: 23
    items") and writes TASK-22's file back as the spelled undeclared kind "TASK-21:related" (file
    diff confirmed) — matches A5's ruling that folding against a frozen historical default was
    rejected.
    
    Confirmed the write/lint-only boundary, not a load-time lock:
    - `sq check`: exit 0, one warn line ("unknown ref kind 'related' on edge -> TASK-21"), no
      "workflow config invalid" line.
    - `sq workflow lint`: exit 1 — refuses at the corpus cross-check, names the item and gives
      two remedies.
    - an ordinary unrelated mutation (`sq task 22 status Ready`) succeeds, exit 0 — not blocked.
    - `sq graph TASK-21 --json`: exit 0, traverses the edge with edge_kind "related",
      edge_semantic null.
    - `sq task 21 refs --all`: exit 0, lists it.
    - adding a NEW ref of the undeclared kind (`sq task 23 ref add TASK-21 --kind related`):
      refused, exit 1 ("unknown ref kind 'related'. Valid kinds: ...") — the write boundary.
    - `sq task 22 ref rm TASK-21` (the remedy the refusal names): succeeds, exit 0, and the squad
      is clean again (`sq check` exit 0 no issues, `sq workflow lint` exit 0 OK) — the remedy the
      message names is real and performable, closing the original "refusal naming a remedy the
      refusal itself blocks" defect.
    
    Also drove the other remedy end to end on a second corpus: revert the override edit -> `sq
    repair` -> mutate TASK-22 once (`sq task 22 status Ready`, file confirmed rewritten to bare
    canonical refs, no extra.ref_kinds) -> re-apply the rename -> lint clean (exit 0), check clean
    (exit 0), both TASK-22 and TASK-23 read as the new default "primary" via `refs --all`. No item
    .md file touched by hand at any point in either recovery.
    
    Checked message truthfulness: the general spec-unloadable message (triggered separately with
    an unrelated broken lifecycle reference) no longer claims lint is "the one command that still
    runs" — it says no command can answer with the vocabulary and points at lint, and in that
    genuinely-broken case `sq check` does fail (exit 3, "workflow config invalid") while `sq
    repair` still runs (exit 0, via its bypass) — consistent, and distinct from the ref-kind case
    above where check only warns.
<!-- sq:discussion:end -->
