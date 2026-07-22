---
id: REV-580
sequence_id: 580
type: review
title: 'Review of FEAT-567 Phase A: category axis + validator engine'
status: Approved
author: reviewer
refs:
- FEAT-567
subentities:
- local_id: F1
  title: category_bundles mutable-dict default param is a latent aliasing footgun
  status: Verified
  severity: low
- local_id: F2
  title: CHANGELOG 0.12.0 heading has no date unlike prior releases
  status: WontFix
  severity: low
created_at: '2026-07-22T10:20:15Z'
updated_at: '2026-07-22T10:25:28Z'
---
<!-- sq:body -->
Independent review of FEAT-567 Phase A (TASK-577/578/579): the `category` axis replacing `is_meta`, the loader compat shim, and the no-op validator-dispatch engine scaffold. Read-only; I did not author the code.

## Verdict: Approved — byte-identical guarantee holds

No behaviour change found. The engine is a genuine no-op in both call sites; the accessor/category migration is an exact equivalent of the old `is_meta` logic; gates all green; full suite green; `sq check` clean.

## Byte-identical: confirmed sound by construction

- `MaintenanceMixin.check()` appends `ValidatorEngine(spec).report(index, on_disk)` after every existing `_check_*`. `report()` iterates items → `effective_validator_names(category)` = `COMMON_CORE(()) + CATEGORY_BUNDLES[cat](()) = ()`, so no catalog lookups; `SQUAD_GLOBAL_CATALOG` empty → returns `[]`. Appending `[]` cannot alter output or ordering. The `_check_*` methods are untouched and remain the sole source of output.
- create (`ServiceCore._create`) and update (`ItemsMixin.update`) call `ValidatorEngine(spec).gate(item, db)`; `gate()` runs the item's per-item set (empty) → no issues → returns `None`. No-op across all three categories (test proves role/task/decision all resolve to an empty set).

## Category migration: exact equivalence

- `item_is_roster(t) := category=="roster"` and `work_types() := category!="roster"` are exact re-expressions of the old `is_meta`/`not is_meta`. `default_workflow.toml` maps roster to exactly the three types that carried `is_meta=true` (role/skill/operator), so both accessors return identical sets. All ~15 consumer sites (services, CLI, backend, interactions, TUI, 3 Jinja templates) switched to `item_is_roster` / `category != "roster"` — pure renames, same booleans. `sq workflow types` `reserved` field is `category=="roster"`, identical values.
- TOML category assignments correct per ADR-541: work = epic/feature/task/bug/review; records = decision/guide; roster = role/skill/operator.
- Reserved-vocab floor correctly migrated: `META_TYPES` members must declare `category=="roster"`.

## Compat shim (`_pop_legacy_is_meta`): correct

Pops `is_meta` from a *copy* before `model_validate`, so `extra="forbid"` stays intact for every other unknown key. `false`/absent → `category` defaults to `"work"`; `true` on a non-roster type → clean `SquadsError`. Applied on BOTH the bundled item loop and the override parser. Loader tests cover all three branches + the "other unknown key still hard-fails" case. `category` is threaded through `{**data}` → `model_validate` in both paths (verified — this is the crux of the whole change and it is correct).

## Engine scaffold matches the design pins

Lives in `_services/` (D1). `ItemSpec` carries bare `category`, resolution at call time (D2). `Validator`/`SquadGlobalValidator` protocols over `ValidatorContext`; closed catalogs as CODE constants; `report()`/`gate()` shapes match D1/D2/D3; squad-global validators run in report only, never in gate (test-proven). AST-guard allowlist entry added (`CATALOG`/`SQUAD_GLOBAL_CATALOG`/`CATEGORY_BUNDLES`); meta-test green. `COMMON_CORE`/`OnDiskMap` are a tuple/type-alias so not flagged.

## Version / manifest / goldens

pyproject `0.11.1`→`0.12.0`. Manifest: the `0.11.1` entry is byte-identical to HEAD; a fresh `0.12.0` entry is appended whose 26 hashes all match the current template files (verified by recomputation) — no manifest corruption. Golden fixtures regenerated version-string-only (`0.11.1`→`0.12.0` in the override-base stamp), no other drift.

## "meta" directive

No `meta` reintroduced in production code beyond the unavoidable `is_meta` legacy-key handling in the shim (its whole job) and the pre-existing `META_TYPES` constant — the `META_*`/`item_is_meta`→`item_is_roster` rename and `work_types()` rework are correctly deferred to FEAT-573 (op-pierre's recorded scope). ADR/CHANGELOG prose documenting the transition legitimately keeps the old name.

Gates: `pyright` 0 errors, `ruff check`/`format` clean, full `pytest` green (0 failures), `sq check` clean (exit 0).

Findings below are Low nits only — neither is a behaviour change and neither blocks the merge.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 580 add-finding "…" --severity medium`; track with `sq review 580 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Verified |  | category_bundles mutable-dict default param is a latent aliasing footgun |
| F2 | 🟢 low | WontFix |  | CHANGELOG 0.12.0 heading has no date unlike prior releases |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — category_bundles mutable-dict default param is a latent aliasing footgun

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
effective_validator_names(category_bundles=CATEGORY_BUNDLES) binds a module-level mutable dict as a default parameter value. Harmless today (the function only reads it and CATEGORY_BUNDLES is a documented never-mutated CODE constant), so no behaviour impact — but if a future edit ever mutates the parameter in-place (e.g. setdefault) it would silently corrupt the shared catalog for all callers. Optional hardening: type the param as a Mapping, or default to None and fall back inside. Not blocking.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — CHANGELOG 0.12.0 heading has no date unlike prior releases

<!-- sq:finding:F2:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The 0.12.0 CHANGELOG entry drops '## [Unreleased]' to '## [0.12.0]' with no ' - <date>' suffix, unlike '## [0.11.1] - 2026-07-21'. Not a code issue; flagging so the release owner adds the date at publish (or confirms the date is intentionally deferred until Pierre publishes). Failure mode: a released changelog reads inconsistently / looks half-cut.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T10:25:28Z] Catherine Manager:
  - F1 (mutable-default param) hardened to a None sentinel, behavior identical, byte-identical confirmed. F2 (undated [0.12.0] heading) is by-design — the working heading stays undated until Pierre cuts the release. Approving.
<!-- sq:discussion:end -->
