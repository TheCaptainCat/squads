---
id: ADR-000266
sequence_id: 266
type: decision
title: 'Spec-derived per-type vocabulary: retire the static PREFIX/FOLDER/alias tables;
  stamp the prefix onto Item'
status: Accepted
author: architect
refs:
- FEAT-000210:addresses
- REV-000265:addresses
created_at: '2026-07-01T07:40:18Z'
updated_at: '2026-07-01T08:27:48Z'
---
<!-- sq:body -->
## Context

REV-000265 F1 (High) found that a custom type declared with `prefix = "INC"` gets a malformed
stored id — `INCIDENT-000019` instead of `INC-000019`. The root cause is `Item.id`
(`_models/_item.py:162`):

```python
prefix: str = _PREFIX_BY_TYPE.get(self.type, self.type.upper())
```

For a custom type the static `PREFIX_BY_TYPE` map has no entry, so the fallback stamps
`self.type.upper()`. `Item` is **spec-unaware by convention** — `_models` has no dependency on the
`_workflow` spec (CLAUDE.md layering + the acyclic-import invariant), so it cannot read the
spec-declared prefix. F1 is one symptom of a broader class the operator wants gone: statically-defined
per-type vocabulary tables that shadow what the spec already declares.

### The id is formatted at THREE independent sites, all with the same buggy fallback

F1 names `_item.py:162`, but the same `PREFIX_BY_TYPE.get(type, type.upper())` derivation is
duplicated:

- `_models/_item.py:162` — `Item.id` computed field (the REV site).
- `_models/_index.py:74` — `SquadsDB.format_id`, called by `allocate_id`. This is what builds the
  **filename** at create time (`_base.py:270-271`), so a custom item's file is *also* misnamed
  `INCIDENT-000019-*.md` — independent of `Item.id`.
- `_cli/_common.py:557` — a pre-callback display/parse path.

And `_services/_refs.py:93,298,351` + `_services/_items.py:303` use **bracket** access
`PREFIX_BY_TYPE[item.type]`, which does not fall back at all — it raises `KeyError` on a custom type.
Any fix that only touches `_item.py:162` leaves the filename wrong and the ref paths crashing. F1 is
a family, not a line.

### What the codebase already established (ADR-000249 / ADR-000263)

- **Models are decoupled from the spec** (ADR-249 Finding 1, proven): `Item`/`SubEntity` do no
  vocabulary lookup at construction; vocab validation lives at the `IndexStore.load()` boundary
  against `active_spec()`. This is the single most important fact — the fix must **not** re-couple
  the model to the spec.
- **The spec is resolved once per invocation** and threaded, not global: the root `--dir` callback
  binds it via `common.set_active_spec()`, and downstream reads it via `common.get_active_spec()`
  (ADR-263). The service already carries `self.spec`; `create` already resolves
  `self.paths.squad_relative(item_type, filename, spec=self.spec)` and
  `self.spec.initial_status(item_type)` — **the spec is in hand at every create/retype/load site.**
- The `ItemSpec` already declares `prefix`, `folder`, `aliases`, `is_meta`, `subentity_kind`; the
  `WorkflowSpec` already derives `prefix_to_type`. The forward `type -> prefix` is `spec.items[t].prefix`.

## Decision

**Stamp the resolved prefix onto the `Item` as a stored-but-derived field; format `Item.id` from
that field, never by looking up a type-keyed table.** The spec-unaware model receives its prefix from
whoever constructs/loads it — every such site already holds a spec (or is a built-in, covered by the
reserved map). Concretely:

1. **`Item` gains a `prefix: str` field** (excluded from JSON like `id_padding`, but written to
   frontmatter as part of the durable id). `Item.id` becomes `format_item_id(self.prefix,
   self.sequence_id, self.id_padding)` — no map lookup, no `type.upper()`. This keeps the model
   spec-decoupled: it stores a plain string handed to it, it does not *derive* vocabulary.

2. **A single reserved-vocab resolver for built-ins.** Keep exactly one authoritative map of the
   built-in prefixes (the reserved-type invariant EPIC-206 already proves) as the default source. A
   thin `_models`-local helper `prefix_for(type_str, spec=None)` returns the built-in prefix when the
   type is reserved, else `spec.items[type].prefix`, else raises. The `spec` is optional so the pure
   built-in path (and legacy callers) need no spec; custom types require one.

3. **Stamp at the three construction/format boundaries where a spec is in hand:**
   - **Create** (`_base.py:270-274`): `db.allocate_id` and the `Item(...)` build both take/receive the
     resolved prefix from `self.spec` (via the resolver). `SquadsDB.format_id`/`allocate_id` grow a
     `prefix`/`spec` parameter so the filename and the counter-formatted id agree.
   - **Retype** (`_services/_retype.py`): already the only path that materialises a custom item today
     (per REV F1's repro); it re-stamps `item.prefix` from the target type's spec.
   - **Load / repair** (`from_frontmatter` + the `IndexStore.load()` boundary): `prefix` is read back
     from frontmatter when present; when absent (legacy files / rebuild), the store — which already
     reads `active_spec()` at the vocab-validation boundary (ADR-249) — resolves it via the resolver.
     `SquadsDB._propagate_padding` is the established precedent for a post-load pass that fills a
     derived field; prefix resolution rides the same seam.

4. **Retire the type-keyed lookups in the ref/id paths** (`_index.py:74`, `_common.py:557`,
   `_refs.py`, `_services/_items.py`) by routing them through the resolver or through `item.prefix`
   (the ref paths already hold the `Item`, so `item.prefix` is the direct answer — no map at all).

This resolves F1 concretely: retype a task to `incident` (spec prefix `INC`) → retype stamps
`item.prefix = "INC"` from `spec.items["incident"].prefix` → `Item.id` renders `INC-000019`, the file
is named `INC-000019-*.md`, and `sq incident INC-000019 show` round-trips. No `type.upper()` anywhere.

### Alternatives weighed

- **(b) Inject a spec/resolver into `Item.id` / `from_frontmatter`.** Rejected: it re-couples the
  model layer to the spec (or to a resolver protocol), reversing ADR-249 Finding 1 and reintroducing
  the layering pressure that decoupling bought. `Item.id` is a `@computed_field` (a pydantic property)
  and cannot take an argument, so this forces a spec handle *onto the model* — the exact thing the
  privacy/acyclic invariant resists.
- **(c) A threaded/ambient contextvar the model reads (ADR-249-style active spec).** Rejected for the
  model layer: making `Item.id` read an ambient contextvar makes a pure data model depend on
  invocation-scoped global state — worse than a stored field, and it breaks the "frontmatter is truth"
  invariant subtly (the same on-disk file renders a different id depending on ambient context). The
  contextvar is right for the *CLI pre-callback* paths (already ADR-263), not for the model.
- **(d) Keep a minimal reserved map for built-ins + require spec for custom.** This is *retained as a
  component* of the chosen approach (item 2), but rejected as the *whole* answer: on its own it still
  leaves `Item.id` deriving the prefix, so the custom case still needs a stored value. The chosen
  design is "(d)'s reserved map feeds (a)'s stored field."
- **(a) as stated (compute where spec is in hand, store the prefix).** This is the chosen approach.
  Trade-off accepted: `Item` carries one more stored field and frontmatter gains a `prefix` line; in
  exchange the model stays spec-decoupled, the three format sites converge on one value, and legacy
  files migrate cleanly (prefix re-derived on load).

## Consequences

### Artifacts this pattern retires

- `PREFIX_BY_TYPE` **as a call-site lookup** — the id/ref/display sites stop reading it; it collapses
  into the single reserved-vocab resolver (built-in defaults only). `ItemType.prefix` property and the
  reserved map survive **only** as the built-in source of truth behind the resolver.
- `TYPE_BY_PREFIX` — `_paths.type_for_id` already prefers `spec.prefix_to_type`; the static reverse
  map narrows to the built-in fallback inside the resolver (same reserved-map story).
- `FOLDER_BY_TYPE` **as a standalone table at the id/path sites** — `_paths.folder_for`/`squad_relative`
  already consult `spec.items[t].folder` for custom types; fold the built-in map into the resolver so
  folder + prefix come from one place.
- `TYPE_ALIASES` — already a documented non-authoritative shim (`_enums.py:75-83`); CLI registration
  reads `ItemSpec.aliases`. Its remaining consumers (`_workflow_cmd._print_cheatsheet`, the backend
  AGENTS/CLAUDE renderers) migrate to `spec.alias_to_type` / `ItemSpec.aliases`, then the dict is
  deleted.
- `_META_NAMES` (`_cli/_items.py:109`) — the pre-callback fallback resolves through the same reserved
  resolver (`item_is_meta` for reserved types); once every path has a spec in hand it goes away.

### Artifacts that STAY

- **The reserved built-in vocab map** (one authoritative source for the 7 built-in work types +
  role/skill/operator). It is the resolver's default and the EPIC-206 reserved-type invariant depends
  on it; it is not user-editable and never shadows the spec for custom types.
- **`_KIND_BY_TYPE` in `_migrations/_v0_2_to_v0_3.py`** — frozen migration code, keeps its static map
  (out of scope, exempt by rule: migrations pin the vocabulary of their era).

### Sequencing / feature-boundary recommendation (for @tech-lead + @manager + op-pierre)

- **Land within the FEAT-000210 corrective (this slice's follow-up task):** the `Item.prefix` field +
  the resolver + the three format-site conversions + the ref-path fix + retiring `PREFIX_BY_TYPE`/
  `TYPE_BY_PREFIX`/`FOLDER_BY_TYPE` call-site reads + the `TYPE_ALIASES` shim. These are exactly the
  "prefix/folder/type-by-prefix/meta/alias-shim" retirements F1 blocks, and they are what makes a
  custom `INC-000019` round-trip. This is the direct fix REV F1 (and the create-path F2) need.
- **Defer / do NOT pull into FEAT-210:** `_SUBENTITY_PLURAL` (`_cli/_items.py:47`). The spec has no
  sub-entity plural/singular vocabulary yet — that schema addition is FEAT-000212's `subentity_kinds`,
  and FEAT-210 explicitly scopes brand-new sub-entity kinds *out* (F6). Recommendation: **design the
  resolver so FEAT-212 reuses it** (the resolver signature already returns per-type vocab; add a
  `subentity_plural` accessor when `subentity_kinds` lands) rather than pulling the FEAT-212 vocab
  forward. Keep `_SUBENTITY_PLURAL` as the built-in fallback until FEAT-212 supplies the spec field —
  its `custom types would need to declare their own plural, but none do yet` comment is accurate and
  should stay until then.

This split keeps the FEAT-210 corrective behavior-preserving on built-ins (the reserved map still
drives them byte-identically — AC#7/#8) while making every custom-type id, folder, and alias
spec-derived. It is a recommendation, not a unilateral scope change.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T07:41:47Z] Robert Architect:
  - @manager @tech-lead ADR-000266 (Proposed) decides how spec-derived per-type vocabulary reaches the spec-unaware _models layer and resolves REV-000265 F1.
  - Decision: stamp a resolved prefix onto the Item as a stored-but-derived field (Item.prefix), and format Item.id from that field — never from a type-keyed lookup. Built-in prefixes come from ONE reserved-vocab resolver (the default); custom types get their prefix from spec.items[t].prefix, stamped at create/retype/load where the spec is already in hand (create already carries self.spec). Item stays spec-decoupled (ADR-249 Finding 1 preserved): it stores a string handed to it, it does not derive vocab. Rejected injecting a spec into Item.id (re-couples the model; computed_field can't take args) and an ambient contextvar the model reads (breaks frontmatter-as-truth).
  - F1 is NOT a one-liner: the SAME buggy PREFIX_BY_TYPE.get(type, type.upper()) is at THREE sites — _item.py:162 (Item.id), _index.py:74 (format_id → the create-time FILENAME, so the file is ALSO misnamed), and _common.py:557; plus _refs.py/_items.py use bracket PREFIX_BY_TYPE[type] which KeyErrors on custom types. Fixing only line 162 leaves the filename wrong and the ref paths crashing. Fix converges all sites on item.prefix / the resolver.
  - Retires (call-site reads): PREFIX_BY_TYPE, TYPE_BY_PREFIX, FOLDER_BY_TYPE (all fold into the single resolver's built-in defaults), the TYPE_ALIASES shim (consumers move to ItemSpec.aliases/spec.alias_to_type), and _META_NAMES. STAYS: the reserved built-in vocab map (resolver default + EPIC-206 reserved-type invariant); _KIND_BY_TYPE in _migrations/_v0_2_to_v0_3.py (frozen migration, exempt).
  - Feature boundary (recommendation, not a scope change): land prefix/folder/type-by-prefix/meta/alias-shim retirement + Item.prefix + resolver + the 3 format-site conversions + ref-path fix WITHIN the FEAT-210 corrective (this is exactly what makes INC-000019 round-trip and unblocks F1/F2). DEFER _SUBENTITY_PLURAL to FEAT-212 (subentity_kinds schema) — do NOT pull it forward; instead design the resolver so FEAT-212 reuses it (add a subentity_plural accessor when the field lands). Keep _SUBENTITY_PLURAL as the built-in fallback until then.
- [2026-07-01T08:27:48Z] Catherine Manager:
  - Accepted after reading the full Decision + Alternatives. Operator (op-pierre) confirmed the feature boundary: FEAT-210 corrective retires PREFIX_BY_TYPE / TYPE_BY_PREFIX / FOLDER_BY_TYPE / the TYPE_ALIASES shim / _META_NAMES via the Item.prefix + reserved-vocab resolver pattern; _SUBENTITY_PLURAL is DEFERRED to FEAT-212 (kept as built-in fallback), with the resolver designed so FEAT-212 adds a subentity_plural accessor when the subentity_kinds schema lands. Verified the three-site finding (_index.py:74 filename, _common.py:557, _refs.py bracket-KeyError) — the corrective is broader than REV-265 F1's single line.
<!-- sq:discussion:end -->
