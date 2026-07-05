---
id: REV-225
sequence_id: 225
type: review
title: 'FEAT-219 review: role catalog externalized to bundled roles.toml'
status: Approved
author: reviewer
refs:
- FEAT-219
- TASK-222
- TASK-223
- TASK-224
subentities:
- local_id: F1
  title: 'Golden test docstring overstates coverage: a newly-added RoleSpec field
    would NOT fail the lock'
  status: Open
  severity: low
- local_id: F2
  title: Unknown TOML role keys silently ignored (pydantic extra=ignore + explicit
    key enum in _parse_role)
  status: Open
  severity: low
- local_id: F3
  title: 'Stale comment: lazy import of RoleSpec in _role_spec_to_def claims a circular-import
    risk that does not exist'
  status: Open
  severity: low
created_at: '2026-06-26T07:54:32Z'
updated_at: '2026-06-26T07:58:41Z'
---
<!-- sq:body -->
# FEAT-219 review — role catalog externalized to bundled `roles.toml`

**Verdict: APPROVE-WITH-NITS.** Behavior-preserving, golden-locked, fail-closed, acyclic, pyright/ruff-clean. Both nits are pre-existing-style robustness gaps in the golden test's *future-proofing*, not drift in today's data. No code change required to ship.

## Scope
Independent review (I did not write it). Mirrors REV-218 (FEAT-207) rigor. Files: `src/squads/_roles/_models.py`, `roles.toml`, `_loader.py`, `_catalog.py`, `tests/test_role_catalog.py`. Reviewed against ADR-221 and TASK-222/223/224.

## What I verified independently

**1. Byte-identical (the core requirement) — CONFIRMED.** I execed the original `_catalog.py` from git HEAD and field-by-field-diffed all 11 fields of all 8 roles, the 3 bundles, and the dev pool against `roles.toml`: **NO DRIFT**. The em-dash in manager's mission ("— keeping"), the smart-quote/ellipsis in tech-lead's `add-subtask "…"`, the reviewer `agreements` prose, the escaped quotes in TOML — all reproduce exactly. Multi-line missions correctly collapsed to single-line basic strings matching the Python string-concat (no stray newlines).

**2. Golden test is genuine and non-circular — CONFIRMED.** The snapshot is hand-transcribed from the literals, NOT derived from the spec. I independently diffed `_ROLE_SNAPSHOT`/`_BUNDLE_SNAPSHOT`/`_DEV_POOL_SNAPSHOT` against the original HEAD literals: **NO DRIFT**. So snapshot==original AND toml==original ⇒ the lock proves toml==original, not toml==toml. Per-field coverage is complete for all 11 current fields (no field omitted from the assertion). `test_golden_predefined_matches_snapshot` also locks the `RoleDef` shim, and `test_golden_dev_role_spotcheck` locks `dev_role("dotnet", seq=0)` exactly. Packaging: `importlib.resources` accessibility + wheel-presence both asserted.

**3. `dev_role()` integrity — CONFIRMED.** Logic stayed in Python (slug `<slugify(tech)>-dev`, surname titlecased, name-by-seq with `% len(pool)` wrap); only `name_pool`/`model`/`color` data moved to `spec.dev`. Spot-checked output identical incl. seq-wrap (seq=12 → "Elias"). `to_extra`/`from_extra` ExtraKey bridge byte-for-byte unchanged from HEAD.

**4. Loader & fail-closed validation — CONFIRMED.** `importlib.resources` + `tomllib`; I exercised all 6 ADR rules + read-failure + malformed-TOML paths — every violation raises `SquadsError` (no bare exceptions leak): unique slugs, required non-empty fields, ≤1 is_default, bundle referential integrity (+ `all`==full set), dev-pool well-formed/unique, model whitelist (roles and dev). `RoleNotFoundError` path on `role_by_slug("ghost")` intact.

**5. Identity landmines — NONE.** No `is`/`==` identity comparison on RoleDef/role objects in `_resolver.py`, services, backends, or CLI. The two `PREDEFINED` references in `_cli/_role.py` are iteration, not identity. RoleDef rebuilt fresh from spec is safe.

**6. Invariants — CONFIRMED.** No `from __future__`. Import graph acyclic: `_models` → pydantic only; `_loader` → `_errors`+`_models`; `_catalog` → `_loader`+`_models`+`_errors`/`_extras`/`_util`. No service/backend edges. Singleton loaded once at `_catalog` import. pyright strict 0 errors, ruff check + format clean on all 4 files.

**7. Scope boundary — HELD.** No de-typing, no custom roles, no new overrides. Crucially the dev **kept `RoleDef` as a frozen dataclass** (did not replace it with the pydantic `RoleSpec`), so the pre-existing `_resolver.py` (`.overrides/roles/`, shipped earlier in 087ebe3 — untouched by this feature) still works: it relies on `dc_fields(RoleDef)` + `RoleDef(**current)`, which would have broken had RoleDef become pydantic. ADR-221's "no overrides" refers to the *catalog* not gaining an override layer — correct; the separate pre-existing role-override resolver is out of this feature's scope and unchanged.

**Cross-check of operator's claims:** all confirmed — roles/bundles/dev-pool/dev_role match today, golden+packaging green (12/12), no identity comparisons, existing tests unedited (only `test_role_catalog.py` is new), consumer tests (`test_role_resolver`, `test_skill_seeding`) green.

## Findings
Two LOW nits below — both are golden-test future-proofing / a stale comment, neither blocks. See finding details.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 225 add-finding "…" --severity high`; track with `sq review 225 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Golden test docstring overstates coverage: a newly-added RoleSpec field would NOT fail the lock |
| F2 | 🟢 low | Open |  | Unknown TOML role keys silently ignored (pydantic extra=ignore + explicit key enum in _parse_role) |
| F3 | 🟢 low | Open |  | Stale comment: lazy import of RoleSpec in _role_spec_to_def claims a circular-import risk that does not exist |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Golden test docstring overstates coverage: a newly-added RoleSpec field would NOT fail the lock

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
tests/test_role_catalog.py:33-34 — the docstring 'adding a field to RoleSpec without updating this test causes a failure' is aspirational, not enforced. The test asserts each of the 11 named fields explicitly but never asserts set(RoleSpec.model_fields) == set(snapshot keys). A future 12th field on RoleSpec would silently escape the golden lock. LOW for this feature (all 11 of today's fields ARE locked, byte-identical). Suggested hardening: add 'assert set(RoleSpec.model_fields) == {<the 11 keys>}' so a new field forces a snapshot update. No change required to ship.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Unknown TOML role keys silently ignored (pydantic extra=ignore + explicit key enum in _parse_role)

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
src/squads/_roles/_loader.py:68-85 (_parse_role) + _models.py (RoleSpec has no extra='forbid'). An unknown role key in roles.toml (e.g. a typo like 'mision = ...') is silently dropped rather than rejected — verified: _build_catalog accepts a role with a bogus field. ADR-221 does not mandate rejecting unknowns, and the bundled TOML is clean, so this is a defensive nit, not a defect. A typo on a REQUIRED field would still be caught by the required-field check; a typo on an OPTIONAL field would silently revert to default. Optional hardening: ConfigDict(extra='forbid') on RoleSpec, or validate keys against a known set in _parse_role. LOW.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Stale comment: lazy import of RoleSpec in _role_spec_to_def claims a circular-import risk that does not exist

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
src/squads/_roles/_catalog.py:70-72 — the comment 'Import here to avoid a circular-import risk at module level' is inaccurate: _catalog.py already imports RoleCatalogSpec from squads._roles._models at module top (line 18), so _models is a fully-resolved dependency and importing RoleSpec at module scope would create no cycle (_models imports only pydantic). Cosmetic only — the lazy import is harmless and runs once during singleton build. Suggest hoisting RoleSpec to the top-level import and dropping the misleading comment. LOW / cosmetic.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T07:55:39Z] Paul Reviewer:
  - VERDICT: APPROVE-WITH-NITS. FEAT-219 is behavior-preserving and golden-locked. Independently confirmed byte-identical: execed the original _catalog.py from git HEAD and field-by-field-diffed all 11 fields of all 8 roles + 3 bundles + dev pool against roles.toml (NO DRIFT), and separately diffed the test snapshot against those same literals (NO DRIFT) — so the golden lock is genuine and non-circular, not spec-vs-itself.
  - dev_role() logic stays in Python (only pool/defaults externalized), to_extra/from_extra bridge unchanged, loader fail-closed on all 6 ADR rules + read/parse failures (all SquadsError, no bare exceptions), import graph acyclic, no from __future__, pyright/ruff clean, no is/== identity landmines. Scope held: RoleDef correctly kept as a frozen dataclass so the pre-existing .overrides resolver (dc_fields/RoleDef(**current)) still works.
  - 3 LOW nits, none blocking, no code change required to ship: F1 golden-test docstring overstates coverage (a future RoleSpec field would escape the lock — add a model_fields-set assertion); F2 unknown TOML role keys silently ignored (consider extra='forbid'); F3 stale 'circular-import risk' comment on the lazy RoleSpec import (no cycle exists — hoist it). @tech-lead @python-dev — approving as-is; the nits are optional hardening for a follow-up, your call.
- [2026-06-26T07:58:01Z] Elias Python:
  - @manager REV-225 nits all fixed.
  - F1 (field completeness guard): added test_golden_snapshot_covers_all_rolespec_fields() before test_golden_all_role_fields in tests/test_role_catalog.py. Asserts set(_ROLE_SNAPSHOT[0].keys()) == set(RoleSpec.model_fields) — fails if a 12th field is added to RoleSpec without extending the snapshot. Added RoleSpec import to test file.
  - F2 (extra='forbid'): all three models in src/squads/_roles/_models.py now use ConfigDict(frozen=True, extra='forbid'). Bundled roles.toml still loads (verified — no stray keys). Unknown TOML keys now raise a pydantic ValidationError wrapped in SquadsError.
  - F3 (stale comment): removed the lazy 'avoid circular-import' import of RoleSpec inside _role_spec_to_def — promoted to top-level import alongside RoleCatalogSpec. Changed function signature from rs: object to rs: RoleSpec (type now expressible at top level). No assert isinstance needed.
  - Gates: pytest tests/test_role_catalog.py → 13 tests pass; pyright 0 errors; ruff check clean; ruff format --check 131 files already formatted. All existing role tests pass unchanged.
- [2026-06-26T07:58:41Z] Catherine Manager:
  - REV-225 nits verified fixed: F1 golden-lock now asserts checked fields == set(RoleSpec.model_fields) (future fields can't escape the lock); F2 ConfigDict(extra='forbid') on RoleSpec/DevPoolSpec/RoleCatalogSpec — unknown TOML keys now fail closed (confirmed); F3 stale circular-import comment + lazy import removed, RoleSpec now top-level. roles.toml loads, 8 roles byte-identical, 13 role tests + gates green. Closing FEAT-219.
<!-- sq:discussion:end -->
