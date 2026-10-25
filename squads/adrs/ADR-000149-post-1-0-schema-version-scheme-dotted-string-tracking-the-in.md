---
id: ADR-149
sequence_id: 149
type: decision
title: 'Post-1.0 schema_version scheme: dotted-string tracking the introducing release'
status: Accepted
author: architect
refs:
- FEAT-13
- ADR-76
created_at: '2026-06-17T07:56:27Z'
updated_at: '2026-10-25T21:36:46Z'
---
<!-- sq:body -->
## Context

`schema_version` is the durable stamp on a squad's on-disk format. It is a **dotted string naming
the release that introduced the schema**, compared as a tuple via `schema_tuple()` — never as a raw
string, because `"0.10"` is not lexically greater than `"0.2"`. ADR-76 establishes this scheme and
its upgrade path: `_models/_schema.py::SCHEMA_VERSION` is the single source of truth, the root CLI
callback hard-stops on a mismatch, and `sq migrate up` runs the ordered `_migrations` registry,
then `repair`, then stamps the new version.

ADR-76 deliberately left the **post-1.0** meaning of the version open. The 1.0 stability contract
needs that meaning pinned so it can state it. This decision settles it; the direction is the
operator's call, recorded precisely.

## Decision

**The `schema_version` scheme is kept unchanged past 1.0: a dotted string naming the release that
introduced the schema, compared via `schema_tuple()`.** Concretely:

- **`SCHEMA_VERSION` in `_models/_schema.py` remains the single source of truth.** Models default to
  it; every consumer reads it from there. The rule is about where the value lives and how it is
  compared, never about the value itself.
- **Comparisons go through `schema_tuple()`, never raw-string `<`/`>`.**
- **Post-1.0, a schema change ships only with a MAJOR release** and bumps the dotted string
  accordingly. The version continues to *name the release that introduced the schema*, so the
  changelog stays the schema's documentation.
- **`sq migrate up` remains the upgrade path.** A schema bump adds an ordered `Migration` to the
  registry; the runner applies pending steps, runs `repair`, and stamps the new version.

This is a **policy/contract decision**: the constant, the comparison helper and the migration runner
implement it. It fixes the *meaning* the 1.0 contract publishes, not a mechanism.

## Trade-offs considered

Two alternatives were weighed and rejected.

**(a) A monotonic integer counter, decoupled from the app's SemVer** (e.g. `schema_version = 3`).
The conventional "opaque schema counter" pattern. Rejected: it discards the self-describing tie
between the on-disk version and the release/changelog, and it would force code churn across
`_schema`, `_config`, `_index`, and `_reflog` (the `v` stamp), plus a rename of the `_vN_to_vP`
migration-runner convention, for **no user-visible gain**.

**(b) Tie the schema version directly to the SemVer MAJOR only** (e.g. schema `1`, `2`, … tracking
the app's major). Rejected for the same reason: it loses the minor-granularity, release-named
self-description and still requires reworking the comparison/stamping surfaces. It also conflates two
axes that are usefully distinct — the app can ship MAJOR releases that *don't* touch the on-disk
format, and the dotted scheme expresses "no schema change this release" naturally.

The dotted scheme works and `schema_tuple()` orders it correctly. Keeping it costs nothing and
preserves the changelog-as-documentation property.

## Consequences

- **The `sq migrate up` durability promise is unaffected.** Any squad created on any 0.x release
  still reaches 1.0 (and beyond) intact via the same ordered runner.
- **The reflog `v` field stays coupled to `SCHEMA_VERSION`.** It is the schema version of the squad
  that wrote the line, not a separate line-format version (ADR-117 §4; ruled by op-pierre).
- **Revisitable by supersession.** If a real need for an opaque counter or a SemVer-coupled scheme
  appears later, a new decision can supersede this one and pay the reintroduction cost.
- **The stability contract publishes this scheme** — dotted string naming the introducing release,
  `schema_tuple()` comparison, schema bumps ride MAJOR releases — as the versioning rule for the
  durable `.md`/config surface.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:51:18Z] `architect` Robert Architect:
  - Restated the `SCHEMA_VERSION` line so it stops going stale: the value at writing was "0.3", and the rule is about where the value lives and how it is compared, never about the value. Substance verified — `schema_tuple` comparisons, `sq migrate up`, and the reflog `v` still coupled to `SCHEMA_VERSION`. The same stale example appears in the adopter-facing stability doc, which is the tech-writers to fix, not mine.
- [2026-10-25T21:36:46Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. The reflog `v` question (REV-119 F5) is settled: `v` stays coupled and means the writing squad's schema (op-pierre, 2026-10-25, on ADR-117). Removed the stale '0.3' context.
<!-- sq:discussion:end -->
