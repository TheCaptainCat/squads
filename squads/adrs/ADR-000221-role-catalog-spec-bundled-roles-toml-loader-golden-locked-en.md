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
- ADR-1007
created_at: '2026-06-26T07:33:23Z'
updated_at: '2026-10-25T21:36:55Z'
---
<!-- sq:body -->
## Context

The bundled agent roles — their definitions, the bundle selection map, and the developer name pool
and defaults — are data, not code. `FEAT-000219` externalizes that catalog into a bundled
`roles.toml`, loaded and validated at runtime as a `RoleCatalogSpec` value object, with default
behavior identical to the Python literals it replaced (golden-locked). Adding a bundled role or
editing a responsibility is a TOML edit, not a Python edit.

This reuses the load-and-validate pattern of the workflow spec (ADR-214): a bundled-default TOML
shipped as package data, read via `importlib.resources` + stdlib `tomllib`, parsed into a
pyright-strict pydantic model, fail-closed validation raising `SquadsError`, and a frozen-snapshot
golden test as the regression gate. The catalog is the slug authority the playbook (ADR-226)
validates against.

## Decision

### 1. The `RoleCatalogSpec` shape (loaded, validated value object)

The agent-role models live in `_roles/_models.py` (not to be confused with the status-role
`RoleSpec` of `_workflow/_models.py`, ADR-474/696):

```
RoleSpec                         # one agent role's catalog entry
    slug:             str
    full_name:        str
    title:            str
    description:      str          # one-liner for the agent pointer frontmatter
    mission:          str
    responsibilities: list[str] = []
    agreements:       list[str] = []   # e.g. reviewer's "file findings as sub-entities" agreement
    model:            str | None = None   # sonnet | opus | haiku | inherit
    color:            str | None = None
    is_default:       bool = False        # at most one role is the default
    can_spawn:        bool = False        # orchestrating roles only (ADR-155)
    capabilities:     list[str] = []      # what a playbook `*<capability>` guide addresses (ADR-984)

RoleCatalogSpec
    roles:    list[RoleSpec]            # declaration order preserved
    bundles:  dict[str, list[str]]      # all / core / minimal → slug lists
    dev:      DevPoolSpec
    defaults: DefaultsSpec              # roster-wide values a role resolves when it holds none

DevPoolSpec                            # the developer factory's inputs
    name_pool:    list[str]
    model:        str = "sonnet"
    color:        str = "green"
    capabilities: list[str] = []       # held by every templated developer
```

The TOML defines role *content*. How a resolved definition is stored on a ROLE item is the item
model's business: a role item's frontmatter is flat — `slug` (core) plus the declared role
attributes such as `is_default`, `model` and `tech`, read through `AttributeKey` (ADR-1007) — and
its name is its `title` (ADR-766).

### 2. Bundled TOML location & schema

Ships as package data at **`src/squads/_specs/roles.toml`**, beside `workflow.toml` and
`playbook.toml`, swept into the wheel with the other package data (verified in the build test).

Representative schema sketch:

```toml
[bundles]
all     = ["manager", "architect", "tech-lead", "reviewer", "qa", "devops", "product-owner", "tech-writer"]
core    = ["manager", "architect", "tech-lead", "reviewer"]
minimal = ["manager"]

[dev]
model = "sonnet"
color = "green"
capabilities = ["dev"]
name_pool = ["Elias", "Ada", "Linus", "Grace", "Dennis", "Margaret",
             "Alan", "Barbara", "Ken", "Edsger", "Radia", "Donald"]

[[roles]]
slug = "manager"
full_name = "Catherine Manager"
title = "manager"
description = "Default agent: triages the operator's request and routes it to the right specialist."
mission = """
…
"""
responsibilities = ["…"]
model = "opus"
color = "cyan"
is_default = true
can_spawn = true

# … the other bundled roles follow the same shape
```

Multi-line missions use TOML basic-multiline strings; absent optional fields fall back to the model
defaults.

### 3. Loader, validation, and consumers

- `load_role_catalog(squad_dir=None)` (`_roles/_loader.py`) reads the bundled TOML, and — given a
  squad directory — merges `<squad>/.overrides/roles.toml` over it through the shared engine
  (ADR-696 §4, ADR-777) before any model is built, then validates. The bundled catalog is parsed
  once per process; a squad's resolved catalog is read on first use and kept by its owner.
- `_roles/_catalog.py` keeps the catalog surface its consumers read — `PREDEFINED`, `BUNDLES`,
  `DEV_NAME_POOL`, `role_by_slug()`, `resolve_roles()` — over the bundled catalog, and the developer
  factory keeps its **logic in Python** (a proposed slug of `<tech>-dev`, a surname from the tech,
  a first name from the pool) while sourcing its data from `dev`.
- **Fail-closed validation** (raises `SquadsError`):
  1. **Unique slugs** across all roles.
  2. **Required fields present and non-empty** per role: `slug`, `full_name`, `title`,
     `description`, `mission`.
  3. **At most one `is_default = true`**.
  4. **`bundles` referential integrity:** every slug listed in any bundle is a defined role; the
     `all` bundle equals the full role set.
  5. **Dev pool well-formed:** `name_pool` is non-empty and unique; `model`/`color` are non-empty.
  6. **`model`, if set,** is one of `sonnet`/`opus`/`haiku`/`inherit`.
- A corrupt or invalid catalog refuses to run, exactly like a corrupt index or an invalid workflow
  spec.

### 4. The golden-lock contract

Frozen-snapshot tests in `tests/goldens/` assert the loaded bundled catalog — every role with every
field, the bundles and their membership, and the dev pool with its defaults — against a recorded
snapshot. They are the regression gate for any change to the bundled catalog.

### 5. Relationship to the playbook

- **The role catalog owns role DEFINITIONS** — who each role is and what it's for.
- **The playbook owns role INTERACTIONS** — which roles touch each item type, the per-type guidance,
  create-lanes — and it **references role slugs**.

The boundary implies a **referential-integrity contract**: playbook validation cross-checks every
slug it references against the catalog (joined, for a squad, by the project's own roles), failing
closed on an unknown one; a `*<capability>` subject names no slug, so it is exempt from that check
and must only be well-formed. The
catalog loads first so the playbook has a slug authority to validate against.

## Scope boundary

- **Roles are not item types**, so the reserved-vocabulary and prefix/folder invariants of the
  workflow spec do **not** apply to this catalog. Roles *do* surface as ROLE items, whose type and
  lifecycle belong to the workflow spec.
- **The developer factory's logic stays in Python** — only its data is externalized.
- **No backend/renderer change.** How roles are written to `.claude`/AGENTS.md is unchanged by where
  the role data comes from.
- **Project overrides** — per-role files and the catalog document — are ADR-85's and ADR-777's; this
  catalog's bundled content is the base every override merges onto.

## Consequences

- **Positive:** role content is one auditable, editable artifact; adding or editing a bundled role
  needs no Python edit; the golden lock guards against drift; the pattern is identical to ADR-214;
  the catalog is the slug authority the playbook validates against.
- **Cost:** a TOML round-trip and one parse per process (negligible).
- **Risk:** low — the only subtlety is faithfully encoding multi-line missions and the `agreements`
  prose in TOML, which the golden test catches if wrong.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:44:26Z] `architect` Robert Architect:
  - Amended in place; nothing retired. Mechanical rulings verified in force: `load_role_catalog`, the catalog singleton, the `PREDEFINED` shim still consumed by the CLI, `DEV_NAME_POOL` retained, and section 5s referential-integrity contract holding with the role catalog as the playbooks slug authority.
  - Narrowed the scope boundarys "the catalog is bundled-only", which is reversed in fact — `.overrides/roles/<slug>.toml` ships and `resolve_role(slug, squad_dir)` does project-override-then-bundled with a field-wise merge. This was never a contested ruling; the boundary stated that releases scope and ADR-85 is what crossed it, but the sentence reads as a standing prohibition. Path corrected to `src/squads/_specs/roles.toml`.
  - Annotated the `RoleSpec` declaration with its module, which is the correction most likely to save a reader real time: there are now two models with that name — the agent-role entry this decision defines in `_roles/_models.py`, and the status-role entry ADR-474/696 defines in `_workflow/_models.py`. A reader following this decision greps and lands on a model about status colour and settledness. Nothing behavioural diverges, and neither decision was wrong to pick the name — "role" is doing two honest jobs in this codebase.
- [2026-10-25T21:36:55Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Recorded the current model fields (`capabilities`, `defaults`) and the catalog override (`load_role_catalog(squad_dir)`, ADR-777). Replaced `to_extra` with flat attributes (ADR-1007). Corrected the capability-subject check, which validates form only. ADR-1151 (Proposed) will change `[dev]`; not folded in.
<!-- sq:discussion:end -->
