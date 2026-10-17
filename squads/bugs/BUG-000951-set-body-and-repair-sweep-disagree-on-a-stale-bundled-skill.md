---
id: BUG-951
sequence_id: 951
type: bug
title: set_body and repair sweep disagree on a stale bundled skill slug
status: Verified
author: qa
severity: low
refs:
- ADR-880
- FEAT-948
- MILE-934:targets
created_at: '2026-09-15T08:00:38Z'
updated_at: '2026-10-09T19:20:59Z'
---
<!-- sq:body -->
## Problem

Two different membership tests decide "is this SKILL slug template-owned", for the same slug,
and they disagree on a stale bundled slug — leaving a `sq:body` region no command can write and
no sweep can converge.

Found by the architect while ruling ADR-880's fifth amendment; this bug records it as a tracked
defect rather than leaving it as decision-record prose.

## Read — the two tests and where they diverge

`_services/_items.py::set_body` (the body-write closure, shared by the single-item body command
and the bulk importer) refuses a skill body write when:

```python
if is_system_skill(slug, self.spec):
    raise SquadsError(f"{item_id} is a system skill; its definition is template-owned …")
```

`is_system_skill` (`_interactions/__init__.py`) is **deliberately bundled-blind** — by its own
docstring: it returns true for every slug in `bundled_skill_slugs()`, which is built from
`managed_item_types()` (the fixed, historical bundled-type list) with **no `spec` parameter at
all**, so it does not consult which types the active spec currently declares.

The repair sweep's classification, `_services/_maintenance.py::_repair_body_tag`, asks a
different question for the same slug:

```python
if item_type_for_skill_slug(slug, self.spec) is not None:
    return ITEM_SKILL_VIEW_NAME
# else: left alone — "one level earlier", per the method's own docstring
```

`item_type_for_skill_slug` (`_interactions/__init__.py`) loops over `spec.items.items()` and
returns `None` the moment the slug's type is **not currently declared** — the opposite of
bundled-blind.

So for a slug like `sq-bug` whose type (`bug`) has been dropped from the active spec via a
workflow override:

- `is_system_skill("sq-bug", spec)` → **True** (bundled-blind: `bug` is historically bundled,
  spec-drop doesn't matter) → `set_body` refuses any write, replace or append.
- `item_type_for_skill_slug("sq-bug", spec)` → **None** (spec-aware: `bug` isn't declared right
  now) → `_repair_body_tag` returns `None` → the sweep leaves the region exactly as it found it,
  never seeding or converging a placement tag.

A region simultaneously "refused by every write path" and "skipped by the one sweep that
converges write-refused regions" is a document neither a command nor `sq repair` can ever bring
to a consistent state — a defect class this project has already named in the ADR: "a region no
command can write and no sweep can converge."

## Confirmed on the record, not just derived here

Read `sq decision 880 show --full --comments`, Robert Architect's fifth amendment
(2026-09-15T07:20:35Z), which states this precisely as an already-identified defect while ruling
an unrelated, broader question (moving required-view enforcement to a per-view flag):

> `set_body` asks `is_system_skill` while the sweep asks `item_type_for_skill_slug` — two
> membership tests for one question, disagreeing on exactly the stale bundled slug: `sq-bug`
> with `bug` dropped is refused by the write path and never reached by the sweep. A region no
> command can write and no sweep can converge.

This bug is filed to track that defect as work, not to relitigate the ADR's ruling.

## Scope note — narrower than it first looks

The same amendment notes the disagreement is narrower than "any custom-typed skill": a
**project-declared** custom type's stale skill (e.g. `sq-widget` after `widget` is dropped) does
*not* hit this — `custom_skill_slugs(spec)` (the other half of `is_system_skill`'s union) does
consult the live spec, so `is_system_skill` correctly stops calling it template-owned once its
type is gone, and `set_body` would allow the author to reclaim it. The disagreement is specific
to a **historically-bundled** type's slug, because only `bundled_skill_slugs()` is
unconditionally spec-blind by design.

## Relationship to FEAT-948 — do not duplicate its scope here

FEAT-948 ("Required views: a declared, enforced document invariant", Draft, implements ADR-880)
retires `set_body`'s hardcoded per-item-type-skill refusal into a general, declared `required`
rule whose host-set is derived from "the existing creation-template seeding lookup and the
roster writer's own tag classification" — i.e. the same derivation `_repair_body_tag` already
uses. Once FEAT-948 lands, the write path and the sweep read the *same* host classification, and
this specific disagreement closes as a side effect of that unification; no separate code change
is anticipated for it beyond what FEAT-948 already scopes.

This bug still warrants its own record for two reasons: FEAT-948 is Draft (not yet built) and the
defect is live in the current codebase today; and a bug is the right place to track the *observed
defect* independently of which feature happens to resolve it, in case FEAT-948's scope changes
before it lands. Filing this only to note the relationship and avoid re-describing FEAT-948's
fix here — no new remediation scope proposed beyond what's already in that feature.

## Expected vs actual

- **Expected:** `set_body`'s refusal and `_repair_body_tag`'s convergence classification agree on
  which SKILL slugs are template-owned, for any given active spec.
- **Actual:** they use two independently-defined membership tests (one spec-blind, one
  spec-aware) that disagree on a stale bundled slug, producing a body region simultaneously
  unwritable and unconvergeable.

## Severity

Judged **low**. It requires a specific, uncommon precondition (a historically-bundled item type
dropped from the active spec via workflow override while a stale `SKILL` item for its
`sq-<type>` skill still exists in the corpus) and has no data-loss or crash consequence — the
affected region stays exactly as-is, readable, and the item's generated output is already
withdrawn elsewhere (`orphaned_skill_item_type`/`is_live_roster_entry`), so nothing user-facing
regresses today. It is worth tracking rather than leaving as decision-record prose because it is
a genuine, confirmed inconsistency between two supposedly-equivalent membership tests, and its
remedy is already scoped (via FEAT-948) rather than open-ended.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T08:13:00Z] `manager` Catherine Manager:
  - Left untargeted deliberately: TASK-942 removes this defect as a side effect of routing the write
    path and the repair sweep through one host classification, so it closes when that work lands
    (fixes ref added). Targeting it separately would double-count scope already written.
- [2026-10-09T19:20:40Z] `qa` Mara Tester:
  - QA verification: the defect no longer reproduces at HEAD 9a00ddb4. The fix is TASK-942 (carries `fixes` to this bug), shipped in v0.15.0. Both sites now classify through `roster_body_view_name`, and the stale-slug case is pinned by `tests/service/test_admitted_roster_shapes_survive_convergence.py::test_a_stale_bundled_sq_bug_after_its_type_is_dropped_round_trip`; that file ran once here: 3 passed, 0 FAILED.
    
    Driven (not read) with the dev build `.venv/bin/sq` in a scratch squad under the QA scratchpad (`sq init --roles all`, then a workflow override with `[selected].items` omitting `bug`; later also `guide`). Exit codes read from the bare command.
    
    | Shape | Result | Exit |
    |---|---|---|
    | Control, `bug` declared: `skill sq-bug body` replace | refused: "renders through its declared sq:view:item_skill tag ... --force does not lift this" | 1 |
    | `bug` dropped: `sq-bug` replace (no force, then --force) | body set, `item_skill` tag kept at bottom | 0, 0 |
    | `bug` dropped: `sq-bug` append | body appended | 0 |
    | `sq repair` x2 after those writes | file sha256 identical, same output both runs | 0, 0 |
    | `sq check` | no error rows; only the by-design "type 'bug' is no longer declared" warning on SKILL-10, same as the pre-write baseline | 0 |
    | `sq sync` after the writes | stale skill file byte-identical | 0 |
    | Stale `sq-bug` with the tag hand-stripped (tagless region): repair, then replace, then append | repair leaves it identical; both writes succeed, no tag seeded | 0, 0, 0 |
    | Second dropped bundled type, `sq-guide`: replace, append, repair x2, check | writes ok, repair identical, check no errors | 0 each |
    | Declared per-type `sq-task`: replace, append | refused | 1, 1 |
    | Always-on `squads`, `sq-memory`, `greeting`: replace and append each | refused, files unchanged | 1 (x6) |
    | Author-defined skill (`sq skill add qa-custom`): replace, append | succeed | 0, 0 |
    | Importer `body` event on stale `SKILL-10`: replace (force), append; dry-run and apply | accepted | 0 (all four) |
    | Importer on declared `SKILL-19` (`sq-task`): dry-run and apply | refused with the same message as the CLI | 1, 1 |
    | Importer `body` event on author-defined `SKILL-21` | applied | 0 |
    
    Leftover seen, as described: for the stale `sq-bug`, `sq skill sq-bug show` prints `kind: custom (authored)` while `show --json` prints `"system": true`. Not filed; FEAT-976 retires both derivations.
    
    Not covered: a project-declared type's stale skill (`sq-widget`) was not driven by me, only via the pinned test (it passes); `sq migrate`; a hand-renamed skill file whose slug differs from its filename; the TUI and VS Code surfaces.
- [2026-10-09T19:20:59Z] `qa` Mara Tester:
  - Moved Open to InProgress to Fixed to Verified (the lifecycle has no Open-to-Verified edge); fix is TASK-942, verification above.
<!-- sq:discussion:end -->
