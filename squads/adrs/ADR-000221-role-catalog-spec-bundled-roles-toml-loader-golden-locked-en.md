---
id: ADR-221
sequence_id: 221
type: decision
title: 'Role catalog spec: bundled roles.toml + loader, golden-locked, enums-intact
  era'
status: Accepted
author: architect
refs:
- FEAT-219:addresses
- ADR-214
- ADR-85
- ADR-696
created_at: '2026-06-26T07:33:23Z'
updated_at: '2026-08-03T08:44:26Z'
---
<!-- sq:body -->
## Context

Today the 8 bundled agent roles are hardcoded in `src/squads/_roles/_catalog.py` as frozen
`RoleDef` dataclass instances in the `PREDEFINED` tuple, alongside the `BUNDLES` selection map, the
`DEV_NAME_POOL`, and the `dev_role()` factory. Adding a bundled role, editing a responsibility, or
fixing a mission requires a Python source edit and a release.

`FEAT-000219` (FR) externalizes that catalog into a bundled `roles.toml`, loaded and validated at
runtime as a `RoleCatalogSpec` value object, with default behavior **byte-identical to today**
(golden-locked). This is the **same load-and-validate pattern** established for the workflow spec by
`FEAT-000207` / `ADR-000214`, and this ADR deliberately reuses that shape: a bundled-default TOML
shipped as package data, read via `importlib.resources` + stdlib `tomllib`, parsed into a
pyright-strict pydantic model, fail-closed validation raising `SquadsError`, and a frozen-snapshot
golden test as the regression gate.

FR is a prerequisite for `FEAT-000220` (playbook externalization), which references role slugs.

## Decision

### 1. The `RoleCatalogSpec` shape (loaded, validated value object)

`_catalog.py`'s `RoleDef` carries **more than slug/name/title/mission** — the spec must capture
every field or the golden lock fails. The full field set (read from source):

```
RoleSpec  (pydantic v2, replaces the RoleDef dataclass content)  # _roles/_models.py
    slug:             str
    full_name:        str
    title:            str
    description:      str          # one-liner for the Claude pointer frontmatter
    mission:          str
    responsibilities: list[str] = []
    agreements:       list[str] = []   # e.g. reviewer's "file findings as sub-entities" agreement
    model:            str | None = None   # sonnet | opus | haiku | inherit
    color:            str | None = None
    is_default:       bool = False        # exactly one role (manager) is the default
    can_spawn:        bool = False        # orchestrating roles only (manager, tech-lead)

RoleCatalogSpec
    roles:    list[RoleSpec]            # the 8 bundled roles, declaration order preserved
    bundles:  dict[str, list[str]]      # today's BUNDLES: all / core / minimal → slug lists
    dev:      DevPoolSpec

DevPoolSpec                            # the dev_role() inputs, externalized
    name_pool:    list[str]            # today's DEV_NAME_POOL (12 first names)
    model:        str = "sonnet"       # dev_role default model
    color:        str = "green"        # dev_role default color
    # the dev_role() *logic* (slug = "<tech>-dev", surname = tech.title(), name-by-seq) stays in
    # Python — only its DATA (pool, defaults) is externalized. See §3.
```

The `RoleDef.to_extra()` / `from_extra()` bridge to `ExtraKey` (the ROLE-item frontmatter mapping)
is **behavior that stays in Python** — it maps a loaded `RoleSpec` onto the `X.*` extra keys exactly
as today. The TOML defines role *content*; the extra-key serialization is unchanged.

### 2. Bundled TOML location & schema

Ships as package data at **`src/squads/_roles/roles.toml`** (now `src/squads/_specs/roles.toml`) —
consistent with
`FEAT-000207`'s `src/squads/_workflow/default_workflow.toml`, and swept into the wheel by the
existing `packages = ["src/squads"]` rule (verify in the build test, same as templates). Loaded via
`importlib.resources.files("squads._roles") / "roles.toml"` + `tomllib`.

Representative schema sketch (the default — reproduces `_catalog.py` exactly):

```toml
[bundles]
all     = ["manager", "architect", "tech-lead", "reviewer", "qa", "devops", "product-owner", "tech-writer"]
core    = ["manager", "architect", "tech-lead", "reviewer"]
minimal = ["manager"]

[dev]
model = "sonnet"
color = "green"
name_pool = ["Elias", "Ada", "Linus", "Grace", "Dennis", "Margaret",
             "Alan", "Barbara", "Ken", "Edsger", "Radia", "Donald"]

[[roles]]
slug = "manager"
full_name = "Catherine Manager"
title = "manager"
description = "Default agent: triages the operator's request and routes it to the right specialist."
mission = """
Be the operator's first point of contact and run the work loop: understand the intent, delegate to
the right specialists, integrate what they return, and drive each feature to done — keeping
everything tracked in squads.
"""
responsibilities = [
  "Triage incoming requests and clarify intent",
  "Delegate work to the right specialist agents and integrate their results",
  "Drive features through the loop (implement → review → fix) until done",
  "Keep the backlog and statuses honest",
  "Summarise progress for the operator",
]
model = "opus"
color = "cyan"
is_default = true
can_spawn = true

[[roles]]
slug = "reviewer"
full_name = "Paul Reviewer"
title = "code reviewer"
description = "Reviews code changes for correctness, clarity, and consistency."
mission = "Guard quality: review changes critically, request changes when needed, approve when sound."
responsibilities = ["Review diffs for correctness and clarity", "Drive code-review items to a verdict", "Flag risks and missing tests"]
agreements = [
  "File review findings as tracked sub-entities — `sq review <n> add-finding` with severity, statuses updated as they close — never as body prose; finding-scoped comments, statuses, and dossier panes all depend on the structure.",
]
model = "opus"
color = "red"
# … architect, tech-lead, qa, devops, product-owner, tech-writer follow the same shape
```

Multi-line missions use TOML basic-multiline strings; absent optional fields fall back to the
`RoleSpec` defaults (matching the dataclass defaults: empty `responsibilities`/`agreements`,
`model`/`color` None, `is_default`/`can_spawn` False).

### 3. Loader, validation, and consumer rewiring

- `load_role_catalog() -> RoleCatalogSpec` reads the bundled TOML via `importlib.resources` +
  `tomllib`, validates, and caches a module-level singleton (same lifecycle as `WorkflowSpec`).
- The existing `_catalog.py` public surface is preserved as **thin shims over the loaded spec** so
  consumers do not churn: `PREDEFINED` → `spec.roles`, `BUNDLES` → `spec.bundles`, `DEV_NAME_POOL` →
  `spec.dev.name_pool`, `role_by_slug()` / `resolve_roles()` read the spec, and `dev_role(...)`
  keeps its **logic in Python** (slug = `<slugify(tech)>-dev`, surname = tech titlecased,
  name-by-seq from the pool) but sources its `name_pool` / default `model` / `color` from
  `spec.dev`. The `RoleDef` dataclass either becomes the `RoleSpec` pydantic model directly, or a
  trivial adapter — `to_extra`/`from_extra` move onto/alongside it unchanged.
- **Fail-closed validation** in `load_role_catalog()` (raises `SquadsError`):
  1. **Unique slugs** across all roles.
  2. **Required fields present and non-empty** per role: `slug`, `full_name`, `title`,
     `description`, `mission`.
  3. **At most one `is_default = true`** (exactly one in the default catalog: manager).
  4. **`bundles` referential integrity:** every slug listed in any bundle is a defined role; the
     `all` bundle equals the full role set.
  5. **Dev pool well-formed:** `name_pool` is non-empty and unique; `model`/`color` are non-empty
     strings.
  6. **`model`, if set,** is one of the accepted values (`sonnet`/`opus`/`haiku`/`inherit`) — same
     constraint implied by today's code.
- A corrupt/invalid bundled catalog refuses to run, exactly like a corrupt index or an invalid
  workflow spec.

### 4. The golden-lock contract

A **frozen-snapshot test** asserts the loaded `RoleCatalogSpec` reproduces today's `_catalog.py`
exactly: all 8 roles with every field (slug, full_name, title, description, mission,
responsibilities, agreements, model, color, is_default, can_spawn), the three bundles and their
membership, and the dev pool (the 12 names + dev defaults). Build the snapshot directly from today's
`PREDEFINED` / `BUNDLES` / `DEV_NAME_POOL` and assert structural equality with the loaded spec, plus
a spot-check that `dev_role("dotnet", seq=0)` yields the identical `RoleDef` before and after. This
test is the regression gate that proves the externalization is behavior-preserving.

### 5. Relationship to FEAT-220 (playbook externalization)

Clean separation of ownership:
- **`roles.toml` (this feature) owns role DEFINITIONS** — who each role is and what it's for.
- **`playbook.toml` (FEAT-220) owns role INTERACTIONS** — which roles touch each item type, the
  per-type guidance, create-lanes — and it **references role slugs**.

The boundary implies a **referential-integrity contract**: FEAT-220's playbook validation must
cross-check every slug it references against this `RoleCatalogSpec` (and the `*dev` sentinel), and
fail closed on an unknown slug. **FEAT-220 depends on FEAT-219** for that reason — the catalog
must load first so the playbook has a slug authority to validate against. This ADR establishes the
catalog as that authority; it does not define the playbook schema (that is FEAT-220's ADR).

## Scope boundary (what FR does NOT do)

- **Enums-intact era.** This is role-*content* externalization only. It introduces **no custom item
  types, no de-typing, no `str` widening** (F2/FEAT-208) and **no project overrides** (F3) — there
  is no `.squads.toml`/`.overrides/` role-catalog override here; the catalog is bundled-only.
  *Narrowed 2026-08-03: bundled-only is no longer true. `.overrides/roles/<slug>.toml` is a live
  override kind and `resolve_role(slug, squad_dir)` does project-override-then-bundled resolution,
  merging field-wise (ADR-85, ADR-696 §4). Everything else in this boundary holds, and the catalog's
  bundled content is still the base every override merges onto. See the amendment note.*
- **Roles are not item types**, so the reserved-vocabulary / prefix-folder invariants of the
  workflow spec do **not** apply to this catalog — it touches only the role domain. (Roles *do*
  surface as `ROLE` items via `to_extra`, but that ItemType and its workflow are untouched.)
- **`dev_role()` logic stays in Python** — only its data (name pool, defaults) is externalized.
  Letting projects define custom roles is a future concern, out of scope here.
- **No backend/renderer change.** How roles are written to `.claude`/AGENTS.md is unchanged; only
  the source of the role data moves from a Python literal to a bundled TOML.

## Consequences

- **Positive:** role content becomes one auditable, editable artifact; adding/editing a bundled role
  no longer needs a Python edit (US1); the golden lock guarantees no behavioral drift (US2); the
  pattern is identical to `ADR-000214`, so the team already knows it; the catalog becomes the slug
  authority FEAT-220 validates against.
- **Cost:** a TOML round-trip + singleton load (negligible, cached); the shim layer over
  `_catalog.py` during the transition.
- **Risk:** low — behavior-preserving and golden-locked, with no model or type-system changes. The
  only subtlety is faithfully encoding multi-line missions and the reviewer `agreements` prose in
  TOML, which the golden test catches if wrong.

## Amendment note

**2026-08-03 — bundled-only was overtaken, and `RoleSpec` now names two different models.** The
mechanical rulings are verified in force: `load_role_catalog` in `_roles/_loader.py`, the catalog
singleton, the `PREDEFINED` shim still consumed by the CLI, `DEV_NAME_POOL` retained, and §5's
referential-integrity contract holding — the role catalog is the playbook's slug authority.

- **The scope boundary's "the catalog is bundled-only" is reversed in fact.** Project role overrides
  ship: `.overrides/roles/<slug>.toml` is scaffolded by `sq override scaffold --role`, and role
  resolution goes project-override-then-bundled with a field-wise merge. This was never a contested
  ruling — the boundary was a statement of that release's scope, and ADR-85 is the decision that
  crossed it — but the sentence reads as a standing prohibition, so it is narrowed in place.
- **The path is `src/squads/_specs/roles.toml`**, beside `workflow.toml` and `playbook.toml`.
- **`RoleSpec` is ambiguous now, and this is the correction most likely to save a reader real time.**
  There are two models with that name: the **agent-role** catalog entry this decision defines, in
  `_roles/_models.py`, and the **status-role** catalog entry ADR-474/696 defines, in
  `_workflow/_models.py`. A reader following this decision greps and lands in the wrong file, on a model
  about status colour and settledness. The declaration above is annotated with its module for that
  reason. Nothing behavioural diverges; the collision is purely one of names, and it is worth noting
  that neither decision was wrong to pick it — "role" is doing two honest jobs in this codebase.

`related` edges added to ADR-85 and ADR-696.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:44:26Z] Robert Architect:
  - Amended in place; nothing retired. Mechanical rulings verified in force: `load_role_catalog`, the catalog singleton, the `PREDEFINED` shim still consumed by the CLI, `DEV_NAME_POOL` retained, and section 5s referential-integrity contract holding with the role catalog as the playbooks slug authority.
  - Narrowed the scope boundarys "the catalog is bundled-only", which is reversed in fact — `.overrides/roles/<slug>.toml` ships and `resolve_role(slug, squad_dir)` does project-override-then-bundled with a field-wise merge. This was never a contested ruling; the boundary stated that releases scope and ADR-85 is what crossed it, but the sentence reads as a standing prohibition. Path corrected to `src/squads/_specs/roles.toml`.
  - Annotated the `RoleSpec` declaration with its module, which is the correction most likely to save a reader real time: there are now two models with that name — the agent-role entry this decision defines in `_roles/_models.py`, and the status-role entry ADR-474/696 defines in `_workflow/_models.py`. A reader following this decision greps and lands on a model about status colour and settledness. Nothing behavioural diverges, and neither decision was wrong to pick the name — "role" is doing two honest jobs in this codebase.
<!-- sq:discussion:end -->
