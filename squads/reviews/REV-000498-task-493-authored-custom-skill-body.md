---
id: REV-498
sequence_id: 498
type: review
title: 'TASK-493: authored custom-skill body'
status: Approved
author: reviewer
refs:
- TASK-493:addresses
created_at: '2026-07-20T09:23:23Z'
updated_at: '2026-07-20T09:24:34Z'
---
<!-- sq:body -->
Independent review of the TASK-493 working-tree changes implementing ADR-492 Pillars 1 and 2 (authored/persisted custom-skill body + the derived system-vs-custom classifier). Scope reviewed: `src/squads/_services/_items.py` (set_body guard), `src/squads/_interactions/__init__.py` (is_system_skill), `src/squads/_cli/_skill.py` (body verb + show label), and the associated tests/golden. Board-data changes (squads/*.md, .squads.json) excluded by direction.

## Verdict: APPROVE — 0 findings

## Guard relaxation (highest priority) — correct
`set_body`'s branch reorders cleanly: `if item.type == META_SKILL` rejects only when `is_system_skill(slug, spec)`, else falls through and admits the custom skill; the `elif item_is_meta and != META_OPERATOR` keeps rejecting role (and any non-operator meta) as before; work items and operator still admitted. Verified every case (system→reject, custom→admit, role→reject, operator→admit, work→admit).
- Slug source is `item.extra.get(X.SLUG, item.slug)` — the same classifier input the `show` label uses, so gate and label never disagree; and it takes the active `self.spec`, so a renamed/dropped type re-derives.
- Slug-collision safety: `add_skill` already rejects a slug matching any existing skill item; and even if a custom skill somehow held a system slug, `is_system_skill` classifies it system and *denies* the body edit — a fail-safe (denial), never an accidental opening of a system skill.

## is_system_skill — correct, no layering violation
Pure `slug in (bundled_skill_slugs() ∪ custom_skill_slugs(spec))`; lives in `_interactions`, imports no index/store. Documented as derived-not-stored.

## body CLI verb — mirrors the item verb
Same `-m`/`--file`(`-`=stdin)/`--append` surface, routes to `svc.set_body`, uses the shared `resolve_body` (raises `SquadsError` on empty/both-sources). Console output carries no unescaped user content; the `show` label is a fixed literal, `--json` gains `system: bool` additively (golden updated).

## Scope discipline — clean
No `scopes` ref kind, no link-role/unlink-role verbs, no `SCHEMA_VERSION` bump — none of TASK-494/495/496 leaked. Diff touches exactly the 3 code files + 4 test files.

## Standards & tests — clean
pyright 0 errors, ruff check + format clean on the changed files. Service-level tests (meta-guard reject/custom-accept/append; the persistence test genuinely exercises set_body -> sync -> regen -> repair asserting the body unchanged after each, plus the fresh-no-body-renders-coherently case) AND a CLI smoke test (body verb author+append, show label text+json). A unit test pins the predicate's purity. All named by behavior, no ticket ids.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 498 add-finding "…" --severity medium`; track with `sq review 498 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T09:24:34Z] Paul Reviewer:
  - @manager APPROVE — 0 findings. Independent review of the TASK-493 working tree (set_body guard, is_system_skill, sq skill body verb + show label, tests/golden). Guard relaxation is correct and fail-safe; scope clean (no 494/495/496 leakage); pyright/ruff clean; service + CLI tests present, persistence test genuinely proves body survives sync/regen/repair. REV-498 Approved.
<!-- sq:discussion:end -->
