---
id: ADR-226
sequence_id: 226
type: decision
title: 'Playbook spec: bundled playbook.toml + loader, slug-validated, skill-output
  golden-locked'
status: Accepted
author: architect
refs:
- FEAT-220:addresses
- FEAT-219
- ADR-221
- ADR-214
created_at: '2026-06-26T08:01:33Z'
updated_at: '2026-06-26T08:03:22Z'
---
<!-- sq:body -->
## Context

Today the `PLAYBOOK: dict[ItemType, ItemPlaybook]` in `src/squads/_interactions.py` hardcodes, per
item type, an `ItemPlaybook` (overview paragraph, lifecycle text, command examples, and an ordered
tuple of per-role `RoleGuide`s with `enter`/`do`/`handoff`/`watch` sections). `PLAYBOOK` is the
source of truth for every generated `sq-<type>` skill file, for `managed_item_types()`, for
`skills_for_role()`, and (derived from it) for `SKILL_DESCRIPTIONS`.

`FEAT-000220` (FP) externalizes the playbook into a bundled `playbook.toml`, loaded and validated as
a `PlaybookSpec`, default behavior **byte-identical to today** and golden-locked. It reuses the
load-validate-golden-lock pattern of `ADR-000214` (workflow spec) and `ADR-000221` (role catalog):
bundled-default TOML as package data via `importlib.resources` + stdlib `tomllib`, a pyright-strict
pydantic model, fail-closed validation raising `SquadsError`, and a frozen-snapshot regression gate.

FP **depends on `FEAT-000219`** (the role catalog is now the slug authority the playbook validates
against) and on `FEAT-000207` (the loader pattern). It is the bridge to `FEAT-000210` (custom
types): a custom type's playbook entry is what gives its generated skill real role guidance instead
of a thin stub.

## Decision

### 1. The `PlaybookSpec` shape (loaded, validated value object)

Pyright-strict pydantic v2 mirroring today's `ItemPlaybook` + `RoleGuide` exactly (fields read from
`_interactions.py`):

```
PlaybookSpec
    types: dict[ItemType, ItemPlaybookSpec]   # keyed by item type; work types only (see §3)

ItemPlaybookSpec
    overview:  str
    lifecycle: str                  # human lifecycle line, e.g. "Draft → Ready → … (+ Blocked)"
    commands:  list[str]
    roles:     list[RoleGuideSpec]  # ORDERED — section order in the generated skill is significant

RoleGuideSpec
    slug:    str                    # a role slug, or the "*dev" DEV sentinel
    enter:   list[str] = []         # read/confirm before acting
    do:      list[str] = []         # core actions (with concrete `sq …` commands)
    handoff: list[str] = []         # the trigger + target that moves work on
    watch:   list[str] = []         # scope discipline / pitfalls
```

Today's `RoleGuide` uses `tuple[str, ...]`; the spec uses `list[str]` (TOML arrays) and the golden
compares by value, so ordering and content are preserved. The `DEV = "*dev"` sentinel remains a
literal slug value carried through the spec (it is resolved to "developers" at skill-render time, as
today) — it is **exempt** from the role-catalog slug check in §2.

`SKILL_DESCRIPTIONS` stays **derived from the spec's type set** (today it iterates `for item_type in
PLAYBOOK`); the per-type `sq-<type>` description template ("Working with <type> items…") is unchanged
and continues to be generated from the playbook's type set, so the playbook spec remains the single
authority for *which* item-type skills exist and *what* they say.

### 2. Bundled TOML location & schema

Ships as package data at **`src/squads/_interactions/playbook.toml`** — promoting `_interactions.py`
into an `_interactions/` package (`__init__.py` re-exporting the current public names so import
sites are unchanged), with the TOML beside the loader. Consistent with `_workflow/
default_workflow.toml` (ADR-214) and `_roles/roles.toml` (ADR-221); swept into the wheel by the
existing `packages = ["src/squads"]` rule (verify in the build test). Loaded via
`importlib.resources.files("squads._interactions") / "playbook.toml"` + `tomllib`.

Representative schema sketch (nested tables + array-of-tables for the ordered role guides):

```toml
[types.task]
overview = "A unit of implementation work. Its parent is the feature it implements; subtasks each map to one user story."
lifecycle = "Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)"
commands = [
  'sq create task "…" --author tech-lead --parent FEAT-…',
  'sq task <n> add-subtask "…" --story US1',
  "sq task <n> ref add BUG-… --kind fixes   # or REV-… --kind addresses",
  "sq task <n> status InProgress",
]

  [[types.task.roles]]
  slug = "tech-lead"
  enter = ["confirm the parent feature exists and its stories are clear"]
  do = [
    'author the task (`sq create task "…" --author tech-lead --parent FEAT-…`)',
    "add subtasks, each mapped to a story (`add-subtask … --story USn`) — the title is a short handle; implementation detail goes in the subtask body",
    "set `--priority`/`--assignee`; sequence with `ref add … --kind blocks`",
  ]
  handoff = ["once the task is fully defined, assign the developer (`sq task <n> update --assignee <tech>-dev`) — spawn or `@<tech>-dev` to start implementation"]
  watch = ["a task's parent must be a feature; link bugs/reviews via refs, never as parent"]

  [[types.task.roles]]
  slug = "*dev"                       # the DEV sentinel → "developers" section; not slug-checked
  enter = ["read the parent feature's stories + acceptance criteria (`sq feature <n> show`)", "confirm your subtask→story mapping"]
  do = ["`sq task <n> status InProgress`", "implement with tests; tick subtasks (`subtask <k> update --status …`)"]
  handoff = ["when implementation is complete, `sq task <n> status InReview`", "comment a summary of what changed + `@reviewer`/`@qa`"]
  watch = ["don't author features/tasks — that's the product-owner/tech-lead", "file a newly-found defect as a bug; don't silently expand scope"]

  # … reviewer, qa role guides; then [types.bug], [types.feature], [types.epic], etc.
```

Array-of-tables (`[[types.<t>.roles]]`) preserves role-guide order; absent guide sections default to
empty lists, matching the dataclass defaults.

### 3. Loader, validation (fail-closed), and consumer rewiring

- `load_playbook(catalog: RoleCatalogSpec) -> PlaybookSpec` reads the bundled TOML via
  `importlib.resources` + `tomllib`, parses, and validates against the **already-loaded role
  catalog** (FEAT-219). Cached as a module-level singleton, same lifecycle as the other specs;
  takes the catalog as input so the cross-spec check has its authority.
- **Fail-closed validation** (raises `SquadsError`):
  1. **Item-type keys valid:** every key in `types` is a real `ItemType`.
  2. **Cross-spec referential integrity (CRITICAL):** every `RoleGuideSpec.slug` referenced in any
     playbook entry **must exist in the `RoleCatalogSpec`** (FEAT-219 is the slug authority) — with
     the single exception of the `*dev` (`DEV`) sentinel, which is allowed and resolved at render
     time. An unknown slug is a spec error.
  3. **Non-meta-only requirement (scope constraint from the FEAT-220 manager note):** playbook
     entries are required **only for the work (non-meta) item types** — `epic`, `feature`, `task`,
     `bug`, `decision`, `review`, `guide`. The meta types `role` / `skill` / `operator` are
     **deliberately absent** from the playbook today, and validation **must NOT require** entries
     for them. (Today's `PLAYBOOK` already contains exactly the 7 work types — the golden encodes
     this.) A playbook entry for a non-work type is rejected; a missing entry for a meta type is
     fine.
  4. **Required text present:** each `ItemPlaybookSpec` has a non-empty `overview` and `lifecycle`.
- **Consumer rewiring** — preserve the `_interactions.py` public surface as thin shims over the
  loaded spec so call sites do not churn:
  - `PLAYBOOK` → `spec.types`; `managed_item_types()` → `list(spec.types)`;
  - `item_skill_name()` unchanged (pure string function);
  - `skills_for_role(slug)` reads the spec to compute which item-type skills a role interacts with
    (today's `item_types_for_role` scans `PLAYBOOK` role slugs — now scans `spec.types`);
  - `SKILL_DESCRIPTIONS` derived from `spec.types` (as today, from `PLAYBOOK`);
  - the backend `_write_item_skills` reads `pb = spec.types[item_type]` instead of
    `interactions.PLAYBOOK[item_type]` — its rendering logic (DEV→"developers", active-role
    filtering against the roster, the `agents/item_skill.md.j2` render call) is **unchanged**.
  - `CREATE_LANES` / `LANED_TYPES` are a **separate declarative map** today (asserted-equal-to-the-
    playbook in a pinning test); they are **out of scope for FP** and stay in Python — FP does not
    move the lane map (noted in Scope Boundary).

### 4. Golden-lock contract — TWO layers (stronger than the other two ADRs)

The playbook's real output is **skill text**, so the golden lock asserts at both layers:

- **Layer A — spec equality:** the loaded `PlaybookSpec` equals a frozen snapshot built directly
  from today's `PLAYBOOK` dict — every type, every `RoleGuide` (slug + enter/do/handoff/watch),
  every lifecycle and command string, in order.
- **Layer B — generated-output equality (the decisive one):** the **rendered `sq-<type>` skill
  content is byte-identical before and after** the externalization. Concretely: render each
  `sq-<type>` skill from the loaded spec through the same `agents/item_skill.md.j2` path the backend
  uses (with a fixed representative roster so the active-role filtering and the `developers` section
  are deterministic) and assert byte-equality against the output produced from today's Python
  `PLAYBOOK`. Layer B is what US3 demands and is the gate that actually protects users — a faithful
  spec that rendered differently would still be a regression.

### 5. Relationships

- **depends-on `FEAT-000219`** — the `RoleCatalogSpec` is the slug authority for validation rule 2.
- **depends-on `FEAT-000207`** — reuses the spec loader / `importlib.resources` + `tomllib` /
  golden pattern.
- **`FEAT-000210` (custom types) builds on this** — once the playbook is config-driven, a project
  adds a `[types.<custom>]` block (overview + per-role guides) and the generated `sq-<custom>` skill
  carries **rich role guidance instead of a thin stub**. This is the additive, reserved-vocabulary
  framing from `EPIC-000206`: built-in type playbook entries are the bundled default; custom-type
  entries are additive overlays a later feature permits. FP only establishes the *bundled* playbook
  + the slug-validation contract that a custom-type entry will have to satisfy; it does **not**
  implement project-supplied playbook entries (that is F3/F4).

## Scope boundary (what FP does NOT do)

- **Enums-intact era.** Playbook-*content* externalization only. **No custom item types** (F4/
  FEAT-210), **no de-typing / `str` widening** (F2/FEAT-208), **no project overrides** (F3) — the
  playbook is bundled-only here; US2's "project admin adds entries for custom types" is the
  *motivation* this unblocks, not something FP itself ships.
- **`CREATE_LANES` stays in Python** — the lane map is not moved by FP (its pinning test against the
  playbook continues to hold).
- **No backend/renderer change** — `agents/item_skill.md.j2` and the skill-writing logic are
  untouched; only the *source* of the playbook data moves from a Python literal to a bundled TOML.
  Layer-B golden proves this.

## Consequences

- **Positive:** the playbook becomes one auditable, editable artifact; `managed_item_types()` /
  `skills_for_role()` / skill descriptions all flow from it; the two-layer golden guarantees
  generated skills don't drift (US3); establishes the slug-validation contract that custom-type
  playbook entries (FEAT-210) must satisfy. Pattern identical to ADR-214/221.
- **Cost:** a TOML round-trip + singleton load (negligible, cached); the shim layer over
  `_interactions.py`; faithfully encoding the dense per-role prose (with backticks, `@mentions`, and
  `sq …` snippets) in TOML — Layer-B golden catches any mis-encoding.
- **Risk:** low — behavior-preserving, golden-locked at the output layer, no type-system change. The
  main subtlety is preserving exact string content and role-guide ordering through the TOML round
  trip; the byte-identical skill golden is the backstop.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
