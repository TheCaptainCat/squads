---
id: ADR-226
sequence_id: 226
type: decision
title: 'Playbook spec: bundled playbook.toml + loader, slug-validated'
status: Accepted
author: architect
refs:
- FEAT-220:addresses
- FEAT-219
- ADR-221
- ADR-214
- ADR-322
created_at: '2026-06-26T08:01:33Z'
updated_at: '2026-10-27T21:05:25Z'
---
<!-- sq:body -->
## Context

The team **playbook** says, per item type, what the type is for (an overview, a lifecycle line,
command examples) and how each role interacts with it (an ordered list of per-role guides with
`enter`/`do`/`handoff`/`watch` sections). It is the source of every generated `sq-<type>` skill, of
`managed_item_types()`, and of `skills_for_role()`.

`FEAT-000220` externalizes the playbook into a bundled `playbook.toml`, loaded and validated as a
`PlaybookSpec`, with default behavior identical to the Python literal it replaced. It reuses the
load-and-validate pattern of ADR-214 (workflow spec) and ADR-221 (role catalog): a bundled TOML as
package data via `importlib.resources` + stdlib `tomllib`, a pyright-strict pydantic model, and
fail-closed validation raising `SquadsError`.

The playbook **depends on the role catalog** (ADR-221), the slug authority it validates against, and
on the workflow spec, the authority on which types exist. A custom type's playbook entry is what
gives its generated skill real role guidance instead of a thin stub.

## Decision

### 1. The `PlaybookSpec` shape (loaded, validated value object)

Pyright-strict pydantic v2 models in `_interactions/_models.py`:

```
PlaybookSpec
    types: Mapping[str, ItemPlaybookSpec]   # keyed by item-type name; non-roster types only (§3)

ItemPlaybookSpec
    overview:  str
    lifecycle: str                  # human lifecycle line, e.g. "Draft → Ready → … (+ Blocked)"
    commands:  list[str]
    roles:     list[RoleGuideSpec]  # ORDERED — section order in the generated skill is significant

RoleGuideSpec
    slug:    str                    # a role slug, or `*<capability>` for every role holding it
    enter:   list[str] = []         # read/confirm before acting
    do:      list[str] = []         # core actions (with concrete `sq …` commands)
    handoff: list[str] = []         # the trigger + target that moves work on
    watch:   list[str] = []         # scope discipline / pitfalls
    authors: bool = False           # this role is the in-lane author of the type (ADR-163)
```

A `*<capability>` subject (e.g. `*dev`) addresses every role that declares that capability
(ADR-984); it is resolved at skill-render time and is **exempt** from the role-catalog slug check in
§3. The playbook's type set is the single authority for *which* `sq-<type>` skills exist; their
description follows one generic pattern derived from the type.

### 2. Bundled TOML location & schema

Ships as package data at **`src/squads/_specs/playbook.toml`**, beside `workflow.toml` and
`roles.toml`, swept into the wheel with the other package data.

Representative schema sketch (nested tables + array-of-tables for the ordered role guides):

```toml
[types.task]
overview = "A unit of implementation work. Its parent is the feature it implements; subtasks each map to one user story."
lifecycle = "Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)"
commands = [
  'sq create task "…" --author tech-lead --parent FEAT-…',
  'sq task <n> add-subtask "…" --story US1',
]

  [[types.task.roles]]
  slug = "tech-lead"
  authors = true
  enter = ["confirm the parent feature exists and its stories are clear"]
  do = ['author the task (`sq create task "…" --author tech-lead --parent FEAT-…`)']
  handoff = ["…"]
  watch = ["a task's parent must be a feature; link bugs/reviews via refs, never as parent"]

  [[types.task.roles]]
  slug = "*dev"                       # every role holding the `dev` capability; not slug-checked
  enter = ["read the parent feature's stories + acceptance criteria (`sq feature <n> show`)"]
  do = ["…"]

  # … reviewer, qa role guides; then [types.bug], [types.feature], [types.epic], etc.
```

Array-of-tables (`[[types.<t>.roles]]`) preserves role-guide order; absent guide sections default to
empty lists.

### 3. Loader, validation (fail-closed), and consumers

- `load_playbook(catalog, spec, squad_dir=None, …)` (`_interactions/_loader.py`) reads the bundled
  TOML and — given a squad directory — merges `<squad>/.overrides/playbook.toml` over it through the
  shared engine (ADR-696 §4), then validates against the **already-loaded role catalog** and the
  **active workflow spec**.
- **Fail-closed validation** (raises `SquadsError`):
  1. **Type keys valid:** every key in `types` is a non-roster type the active spec declares; an
     entry for anything else is rejected.
  2. **Cross-spec referential integrity:** every guide slug **must exist in the role catalog**
     (joined, for a squad, by the project's own roles), except a `*<capability>` subject, which must
     only be well-formed. An unknown slug is a spec error.
  3. **Coverage:** every bundled non-roster type still active in the spec has a playbook entry.
     Roster types (`role`, `skill`, `operator`) have none, and validation never requires one. A
     custom type without an entry gets a thin generated skill.
  4. **Required text present:** each entry has a non-empty `overview` and `lifecycle`.
  5. **No duplicate guide slug** within one type's `roles`.
- **Consumers read the merged playbook** a service resolved: `managed_item_types(playbook)`,
  `skills_for_role(role, spec, playbook)`, the create-lane helpers (ADR-163), and the backends'
  per-type skill writers, which render each `sq-<type>` skill from it.

### 4. Relationships

- **The role catalog (ADR-221)** is the slug authority for validation rule 2.
- **The workflow spec (ADR-214)** is the authority on which types exist and which are roster.
- **Custom types** gain rich role guidance by adding a `[types.<custom>]` block in the playbook
  override.

## Scope boundary

- **Content, not rendering.** The skill-writing logic and its templates are not this decision's;
  only the *source* of the playbook data is.
- **Project overrides** of the playbook are ADR-696's and ADR-777's; the bundled playbook is the base
  an override merges onto.

## Consequences

- **Positive:** the playbook is one auditable, editable artifact; `managed_item_types()` /
  `skills_for_role()` / the generated skills all flow from it; custom-type entries are held to the same slug-validation contract.
- **Cost:** a TOML round-trip per load (negligible), and faithfully encoding the dense per-role prose
  (with backticks, `@mentions`, and `sq …` snippets) in TOML.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:48:39Z] `architect` Robert Architect:
  - Two citations refreshed: the spec files live at `src/squads/_specs/`, and `PlaybookSpec.types` is `dict[str, ItemPlaybookSpec]` since ADR-322 removed the enum. `load_playbook` also gained a `spec` parameter, so playbook membership is filtered against the types an adopter still declares — a narrowing of section 3s coverage rule in the adopters favour, not a reversal.
  - Recorded one thing deliberately as NOT a finding, so it does not get re-raised: "the playbook is bundled-only" is still true in fact. `sq override scaffold` supports templates, roles and workflow only. ADR-541 and ADR-696 section 4c both name the playbook as the planned fourth kind and ADR-696 records it as blocked on the playbook resolving against the active spec — so this is a live forward dependency this decision is correctly still on the near side of, not stale prose.
- [2026-08-22T09:31:08Z] `architect` Robert Architect:
  - The amendment note here records the playbook as not yet an override kind and correctly a forward dependency. That is overtaken: .overrides/playbook.toml ships, merges through the shared engine (_interactions/_loader.py:213-221) and is scaffoldable. ADR-777 (Proposed) carries the correction along with the rest of the uniformity work.
- [2026-10-25T21:36:57Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. The playbook is an override kind (ADR-696/777): the 'bundled-only' boundary was false. Subjects are `*<capability>`, guides carry `authors` (ADR-163, which replaces CREATE_LANES), and coverage runs against the spec's non-roster types. The goldens are `playbook_spec.json` and `skill_body_sq-*.txt`.
- [2026-10-27T21:05:25Z] `architect` Robert Architect:
  - Removed the test-suite clauses (op-pierre ruling 2026-10-27, FEAT-1096); the decision is unchanged.
<!-- sq:discussion:end -->
