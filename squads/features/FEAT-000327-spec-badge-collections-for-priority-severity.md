---
id: FEAT-327
sequence_id: 327
type: feature
title: Spec badge collections for priority/severity
status: Ready
parent: EPIC-325
author: product-owner
refs:
- ADR-323:implements
- FEAT-326:depends-on
description: Priority/Severity enums -> spec badge collections; Collection/Field/Badge
  model; CLI derives --<field> generically
subentities:
- local_id: US1
  title: Priority/severity become spec badge collections
  status: Todo
- local_id: US2
  title: CLI derives filter/sort/badges from fields
  status: Todo
- local_id: US3
  title: Bug severity migration preserves data
  status: Todo
- local_id: US4
  title: Spec load fails closed on bad field decls
  status: Todo
created_at: '2026-07-07T14:38:59Z'
updated_at: '2026-07-08T08:30:14Z'
---
<!-- sq:body -->
## What this delivers

Implements ADR-323 (Accepted): replaces the hardcoded `Priority`/`Severity`
enums with a three-level spec model — **Badge** (code+label+emoji),
**Collection** (a reusable, ordered library of badges), and **Field** (a
type's or sub-entity-kind's binding to a collection, with its own relabeling
`label`, `required`, and `default`). Priority and severity become two
bundled default collections/fields instead of special-cased code — the same
"spec is the sole vocabulary" move ADR-322 completed for types and statuses,
applied to the last two flat presentation axes. Depends on FEAT-326: fields
are declared per `spec.items[...]`/`spec.subentity_kinds[...]`, which needs
FEAT-326's generic, string-keyed item/type model rather than the old
enum-gated one.

## Scope

- Add `Collection`/`Badge`/`Field` to the workflow spec schema
  (`_workflow/_models.py`): collections at `[collections.<code>]` (label,
  `ordered`, optional collection-level `default`, an ordered `badges` list of
  `{code, label, emoji}`); fields at `[items.<type>].fields` /
  `[subentity_kinds.<kind>].fields` (`{code, label, collection, required,
  default}`).
- Bundle `priority` and `severity` as default collections, byte-identical to
  today's `Priority`/`Severity` enum values and emoji, wired onto the same
  types/kinds that carry them today (priority: every bundled work type;
  severity: `bug` item-level + `finding` sub-entity-level).
- Delete `Priority`/`Severity` (`_models/_enums.py`), `PRIORITY_EMOJI`/
  `SEVERITY_EMOJI`, `DEFAULT_SEVERITY`, and `ItemSpec.severity_field`/
  `item_has_severity()`. "Does type `t` carry severity" becomes "does
  `fields_for(t)` include a field with code `severity`" — a generic lookup,
  not a boolean flag.
- `Item`/`SubEntity` store only the badge **code** for each declared field
  (already the shape for priority; severity item-level moves off
  `extra[X.SEVERITY]` onto a top-level `severity:` frontmatter key). Label
  and emoji resolve from the spec at render time via a graceful fallback
  (missing collection/badge renders the raw code rather than crashing).
- **Data migration:** bug item-level severity moves from
  `extra[X.SEVERITY]` to a top-level `severity:` key. One-way, registered in
  `_migrations/_registry.py` with a schema bump and a `manual` runbook
  entry.
- CLI (`_cli/_common.py`, `_cli/_main.py`, `_cli/_items.py`): `--<field>`
  create/update value, `--<field>` list/tree filter, `--min-<field>` (when
  the field's collection is `ordered`), sort, and badge-column rendering all
  derive generically from `fields_for(type_or_kind)` — no more hand-written
  `parse_priority`/`parse_severity`/`priority_badge`/`_severity_badge` pairs
  per axis. Adding a third badge axis in a project spec gets the same CLI
  surface for free.
- Fail-closed spec-load validation: field `code` uniqueness within a type/
  kind, no field `code` colliding with a reserved key (`status`, `priority`
  only if not itself the declared field, `id`, etc. — the exact reserved set
  per ADR-323), and every field's `collection` reference resolves to a
  declared collection (referential integrity).

## Non-goals

- Status badges — already spec-declared via `StatusSpec.badge`; untouched
  (ADR-323 constraint 1).
- Custom sub-entity kinds themselves — FEAT-212's scope; this feature only
  ensures FEAT-212 has a shared Field schema to consume rather than forking
  its own (see the FEAT-212 discussion note).

## Acceptance criteria

1. `Collection`/`Badge`/`Field` exist in the spec schema; `[collections.*]`
   and `.fields` on `[items.*]`/`[subentity_kinds.*]` parse and validate.
2. `Priority`/`Severity` enums, `*_EMOJI` maps, `DEFAULT_SEVERITY`, and
   `ItemSpec.severity_field`/`item_has_severity()` no longer exist in
   `src/squads/`.
3. The bundled default spec's `priority`/`severity` collections and fields
   are byte-identical in codes/labels/emoji/defaults to today's enum-backed
   behavior — a no-override squad shows the same badges, filters, and sort
   order as before this feature.
4. Item/sub-entity storage holds only the badge code per field; label/emoji
   resolve from the spec at render time, falling back gracefully (raw code,
   no crash) if a collection or badge is missing.
5. The bug item-level severity migration moves `extra[X.SEVERITY]` →
   top-level `severity:` for every existing bug, registered as a schema-
   bumped migration with a `manual` runbook entry; `sq check`/`sq repair`
   clean after.
6. CLI `--<field>`, `--min-<field>` (ordered collections only), sort, and
   badge columns work for any field declared in the spec — verified for at
   least one custom badge axis beyond priority/severity in a test spec, not
   just the two bundled ones.
7. Spec load fails closed on: a duplicate field `code` within one type/kind,
   a field `code` colliding with a reserved key, and a field whose
   `collection` reference doesn't resolve to a declared collection — each
   with a clear, actionable error.
8. `uv run pyright && uv run ruff check . && uv run ruff format --check .`
   all clean.

## Provenance

Implements ADR-323 (Accepted), which depends on ADR-322. Depends on
FEAT-326 (the ADR-322 implementation) for the generic string-keyed item/type
model that field declarations attach to. FEAT-212 (custom sub-entity kinds)
must consume this feature's Field schema for its own sub-entity fields
rather than fork one — see the discussion note left on FEAT-212.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 327 add-story "As a <role>, I want … so that …"`; track with `sq feature 327 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Priority/severity become spec badge collections |
| US2 | Todo |  | CLI derives filter/sort/badges from fields |
| US3 | Todo |  | Bug severity migration preserves data |
| US4 | Todo |  | Spec load fails closed on bad field decls |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Priority/severity become spec badge collections

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want priority and severity to be ordinary spec-defined badge collections so I can rename, relabel, or add axes without code changes.

**Acceptance:** Priority/Severity enums, *_EMOJI maps, DEFAULT_SEVERITY, and ItemSpec.severity_field/item_has_severity() are deleted. The bundled default spec's priority/severity collections and fields are byte-identical in codes/labels/emoji/defaults to today's enum-backed behavior — a no-override squad shows identical badges, filters, and sort order.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — CLI derives filter/sort/badges from fields

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a developer, I want the CLI's filter/sort/badge support to derive generically from declared fields.

**Acceptance:** --<field>, --min-<field> (ordered collections only), sort, and badge-column rendering work for any field declared in the spec, verified for at least one custom badge axis beyond priority/severity in a test spec — not hand-written per-axis parse/render pairs.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Bug severity migration preserves data

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an existing squads user, I want my bug severities preserved exactly across the storage migration.

**Acceptance:** the data migration moves bug item-level severity from extra[X.SEVERITY] to a top-level severity: frontmatter key for every existing bug, registered with a schema bump and a manual runbook entry in _migrations/_registry.py; sq check and sq repair are clean after.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Spec load fails closed on bad field decls

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As a project admin, I want spec loading to reject invalid badge field declarations with a clear error.

**Acceptance:** spec load fails closed with an actionable error on a duplicate field code within one type/kind, a field code colliding with a reserved key, or a field whose collection reference doesn't resolve to a declared collection.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
