---
id: ADR-000149
sequence_id: 149
type: decision
title: 'Post-1.0 schema_version scheme: dotted-string tracking the introducing release'
status: Accepted
author: architect
refs:
- FEAT-000013
- ADR-000076
created_at: '2026-06-17T07:56:27Z'
updated_at: '2026-06-17T08:30:12Z'
---
<!-- sq:body -->
## Context

`schema_version` is the durable stamp on a squad's on-disk format. Today it is a **dotted string
naming the release that introduced the schema** (currently `"0.3"`), compared as a tuple via
`schema_tuple()` — never as a raw string, because `"0.10"` is not lexically greater than `"0.2"`.
This scheme and its upgrade path were established by **ADR-000076** (the in-force mechanism ADR):
`_models/_schema.py::SCHEMA_VERSION` is the single source of truth, the root CLI callback hard-stops
on a mismatch, and `sq migrate up` runs the ordered `_migrations` registry, then `repair`, then
stamps the new version.

ADR-000076 deliberately left the **post-1.0** meaning of the version open: while alpha, the dotted
0.x string is self-describing against the changelog, but it did not pre-empt what versioning a
*frozen* contract should look like. The road-to-1.0 freeze (FEAT-000013, the stability contract)
needs that post-1.0 meaning pinned so the contract can state it. **This ADR settles it.** The
direction is the operator's call; this ADR records it precisely.

## Decision

**The `schema_version` scheme is kept unchanged past 1.0: a dotted string naming the release that
introduced the schema, compared via `schema_tuple()`.** Concretely:

- **`SCHEMA_VERSION` in `_models/_schema.py` remains the single source of truth.** Models default to
  it; every consumer reads it from there. Its current value is `"0.3"`.
- **Comparisons go through `schema_tuple()`, never raw-string `<`/`>`.** This is unchanged from
  ADR-000076 and stays a standing rule.
- **Post-1.0, a schema change ships only with a MAJOR release** and bumps the dotted string
  accordingly. The version continues to *name the release that introduced the schema* — the same
  semantics it has had since 0.1 — so the changelog stays the schema's documentation.
- **`sq migrate up` remains the upgrade path.** A schema bump adds an ordered `Migration` to the
  registry exactly as today; the runner applies pending steps, runs `repair`, and stamps the new
  version.

This is a **policy/contract decision with zero code change** — the existing constant, comparison
helper, and migration runner already implement it. The ADR fixes the *meaning* the 1.0 freeze must
publish, not any mechanism.

## Trade-offs considered

Two alternatives were weighed and rejected.

**(a) A monotonic integer counter, decoupled from the app's SemVer** (e.g. `schema_version = 3`).
This is the conventional "opaque schema counter" pattern. Rejected: it discards the
self-describing tie between the on-disk version and the release/changelog that has served well since
0.1, and it would force moderate code churn across `_schema`, `_config`, `_index`, and `_reflog`
(the `v` stamp), plus a rename of the `_vN_to_vP` migration-runner convention — all landing right
before the 0.3.0 release, for **no user-visible gain**.

**(b) Tie the schema version directly to the SemVer MAJOR only** (e.g. schema `1`, `2`, … tracking
the app's major). Rejected for the same reason: it loses the minor-granularity, release-named
self-description and still requires reworking the comparison/stamping surfaces. It also conflates two
axes that are usefully distinct — the app can ship MAJOR releases that *don't* touch the on-disk
format, and the dotted scheme already expresses "no schema change this release" naturally.

The dotted scheme already works and `schema_tuple()` already orders it correctly. Keeping it costs
nothing and preserves the changelog-as-documentation property. That is why the trade-off resolves in
favour of the status quo.

## Consequences

- **The `sq migrate up` durability promise is unaffected.** Any squad created on any 0.x release
  still reaches 1.0 (and beyond) intact via the same ordered runner; this ADR changes none of that
  machinery.
- **The reflog `v` field stays coupled to `SCHEMA_VERSION`.** Whether to *decouple* the reflog line's
  `v` field from the schema version is **REV-000119 F5**, an open pre-1.0-freeze question left
  explicitly open and **out of scope here**. This ADR neither resolves nor pre-empts it.
- **Revisitable by supersession.** If a real need for an opaque counter or a SemVer-coupled scheme
  appears later, this ADR can be superseded by a new one that pays the reintroduction cost. Per
  project convention, supersede rather than edit an accepted ADR.
- **FEAT-000013 obligation:** the stability contract must publish this scheme — dotted-string-names-
  introducing-release, `schema_tuple()` comparison, schema bumps ride MAJOR releases — as the
  versioning rule for the durable `.md`/config surface.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
