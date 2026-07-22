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
