---
id: TASK-107
sequence_id: 107
type: task
title: Route type-command aliases to the full command tree
status: Done
parent: FEAT-36
author: tech-lead
subentities:
- local_id: ST1
  title: Add a canonical ALIASES map and register each type sub-app under its hidden
    alias names
  status: Done
  story: US1
- local_id: ST2
  title: 'CLI test matrix: every alias routes deep chains; output and errors stay
    canonical'
  status: Done
  story: US1
created_at: '2026-06-15T07:42:47Z'
updated_at: '2026-07-06T15:18:04Z'
---
<!-- sq:body -->
Add short/single-letter aliases for the seven work-item type command groups so every alias routes to the exact same command tree as its canonical name (full verb-chain + sub-entity equivalence). Aliases are pure input sugar.

## Alias table (canonical → aliases)

epic→e · feature→feat,f · task→t · bug→b · decision→dec,d · review→rev,r · guide→g. No overloading; single letters are safe because command resolution is exact-match (b≠blocked, t≠tree, r≠repair, d≠docs — verify none of the chosen letters collide with an existing top-level command before wiring).

## Approach

The seam is the per-type registration loop in src/squads/_cli/__init__.py (lines ~96-101): each type's sub-app is built once by _items.build_item_app(_type) and registered with app.add_typer(name=_type.value). Register the SAME built Typer object under each alias name with hidden=True (the proven pattern already used for the _addr subgroups in _role/_skill/_operator). Drive the alias names from a single canonical map (e.g. an ALIASES dict keyed by ItemType) co-located with WORK_TYPES in src/squads/_models/_enums.py so the table has one source of truth that both this task and the docs task (TASK-108) consume.

Build the sub-app once per type, then loop its alias names registering each as a hidden typer. Confirm a hidden alias still exposes the entire nested tree (verbs, ref subgroup, and the story/subtask/finding subgroups) — Typer shares the same group object, so it should, but assert it.

## Output stays canonical

No code change should be needed for output (IDs and type names are resolved from the item, not the invoked alias), but the test matrix MUST assert it: errors, confirmations and --json print the canonical type name and full IDs regardless of which alias was typed.

## Acceptance

sq f 26 story 4 show ≡ sq feature 26 story 4 show, and likewise for e/t/b/d/r/g and feat/dec/rev across every verb and sub-entity chain. CLI test matrix (tests/) samples each alias with at least one deep chain and asserts canonical output/errors. uv run pyright && ruff check && ruff format --check && pytest all green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 107 add-subtask "<title>"`; track with `sq task 107 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add a canonical ALIASES map and register each type sub-app under its hidden alias names | US1 |
| ST2 | Done |  | CLI test matrix: every alias routes deep chains; output and errors stay canonical | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add a canonical ALIASES map and register each type sub-app under its hidden alias names

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a daily CLI user, I want sq f / sq t / sq b to work everywhere the full type word does, so that the commands I type all day are as short as they are unambiguous
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers the routing implementation: a single canonical ALIASES map keyed by ItemType (co-located with WORK_TYPES in _models/_enums.py) and registering each type's built sub-app Typer object under its hidden alias names (epic→e, feature→feat/f, task→t, bug→b, decision→dec/d, review→rev/r, guide→g) via the same hidden=True add_typer pattern used for the _addr subgroups, so an alias exposes the entire nested verb + ref + sub-entity tree.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — CLI test matrix: every alias routes deep chains; output and errors stay canonical

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a daily CLI user, I want sq f / sq t / sq b to work everywhere the full type word does, so that the commands I type all day are as short as they are unambiguous
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers the CLI test matrix asserting alias/canonical equivalence: each alias sampled with at least one deep verb + sub-entity chain (e.g. sq f 26 story 4 show ≡ sq feature 26 story 4 show), plus assertions that output, confirmations, errors and --json print the canonical type name and full IDs regardless of which alias was typed.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T07:50:16Z] Elias Python:
  - Implemented TASK-107 (ST1 + ST2).
  - ST1 — Added TYPE_ALIASES: dict[ItemType, tuple[str, ...]] to src/squads/_models/_enums.py, co-located with WORK_TYPES as the single source of truth. Map: epic→e, feature→feat/f, task→t, bug→b, decision→dec/d, review→rev/r, guide→g. TASK-108 (docs) can import it directly from there.
  - ST1 — Updated src/squads/_cli/__init__.py: the registration loop now builds each type's Typer sub-app once and registers it under its canonical name, then loops TYPE_ALIASES to register the same app object under each alias with hidden=True. The aliases are pure input sugar — output (IDs, type names, JSON) is derived from the item model, so it stays canonical without any extra code.
  - ST2 — Added tests/test_aliases.py: 19 tests covering (a) the alias map structure (completeness, no duplicates), (b) collision check (b!=blocked, t!=tree, r!=repair, d!=docs empirically), (c) hidden-from-help assertion for all aliases, (d) canonical output identity (alias output == canonical output) for all 7 types, (e) deep chain equivalence (f N story K show, t N subtask K show, r N finding K show, t N ref add, dec N status), (f) JSON type field stays canonical, (g) error messages use canonical form.
  - Full gate: 598 passed, 1 skipped; 0 pyright errors; ruff clean. @reviewer @qa for verification.
- [2026-06-15T08:05:25Z] Paul Reviewer:
  - Reviewed under REV-109 — **Approved.** Alias routing is correct: each type sub-app is built once and re-registered under canonical + hidden alias names (the _addr hidden=True pattern), so every alias exposes the identical full tree. Verified all 7 letters + feat/dec/rev across deep chains (story/subtask/finding/ref/status) including mutations, canonical output/errors/--json, and no single-letter collision (b!=blocked, t!=tree, r!=repair, d!=docs). TYPE_ALIASES is the single source of truth. Gate green (602 passed/1 skipped, pyright clean, ruff clean). Test matrix in tests/test_aliases.py is adequate.
- [2026-06-15T08:07:24Z] Mara Tester:
  - QA verification complete — PASS.
  - **Acceptance criterion (TASK-107):** sq f/feat/t/b/d/dec/r/rev/g/e all route to the full command tree including deep verb + sub-entity chains. Empirically verified: feature story show, feat story show, task subtask show, review finding show (r/rev), decision status (dec/d), bug comment (b), task ref add (t), epic show (e). Every alias uses the same Typer app object (hidden=True, same tree). Output identical to canonical in all cases.
  - **Canonical output:** --json verified for all 7 types via aliases — type field is canonical (feature/task/bug/decision/review/guide/epic), id is full canonical ID (FEAT-/TASK-/BUG-/ADR-/REV-/GUIDE-/EPIC-). Error messages also use canonical IDs (e.g. sq f 9999 show → 'FEAT-009999').
  - **Collision safety:** b does not shadow blocked, t does not shadow tree, r does not shadow repair, d does not shadow docs. All verified — sq blocked/tree/repair/docs all respond correctly alongside their alias letter.
  - **Test coverage:** tests/test_aliases.py — 23 tests, all pass. Covers: alias completeness, no duplicates, canonical type commands in help, deep chain equivalence for all 7 types, --json canonical output, error canonical output, collision safety.
  - **Gate:** 602 passed 1 skipped; pyright 0 errors; ruff clean.
<!-- sq:discussion:end -->
