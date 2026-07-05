---
id: ADR-76
sequence_id: 76
type: decision
title: Dotted 0.x schema-version scheme with the sq migrate runner
status: Accepted
author: architect
refs:
- FEAT-27
- FEAT-13
- GUIDE-79
description: Schema version names the release that introduced it, compared as a tuple;
  upgrades run through ordered sq migrate steps
created_at: '2026-06-12T14:23:11Z'
updated_at: '2026-06-12T14:29:32Z'
---
<!-- sq:body -->
## Context

The on-disk format — frontmatter shape, ref encoding, marker layout, sub-entity storage — evolves,
and an existing squad on an older format has to upgrade safely. squads needed a way to version the
schema and a runner to move a squad forward. Two questions had to be answered: how to number the
schema, and how to apply the changes.

While the project is pre-1.0, the schema is not yet a frozen contract, so an opaque integer counter
("schema 3") would carry no meaning. We chose instead to tag the schema with the **release that
introduced it** — a dotted string like `"0.1"`, `"0.2"` — so the version is self-describing and ties
the on-disk format to the changelog. Because it is dotted, it must be compared as a tuple, never as a
raw string (`"0.10"` is not less than `"0.2"` lexically). For applying changes, an ordered registry of
migration steps is safer and more auditable than ad-hoc upgrade code: each step is a recorded,
testable transformation with a human runbook for the parts a machine cannot do.

## Decision

**The schema version is a dotted 0.x string naming the release that introduced the schema, compared
as a tuple, and upgrades run through the `sq migrate` runner.** `_models/_schema.py::SCHEMA_VERSION`
is the single source of truth (models default to it); comparisons go through `schema_tuple`, never
`<`/`>` on the raw string. The root CLI callback hard-stops on a schema mismatch and directs the
operator to `sq migrate up`.

`sq migrate` is a small Typer app over an ordered `MIGRATIONS` registry. Each entry is a `Migration`
record pairing a private `migrate(paths)` step with a `manual` runbook string for non-deterministic
parts. `up` runs the pending steps in order, then runs `repair`, then stamps the new version;
`chlog vA..vB` prints the manual steps for a release range; `help` lists the changelog index. The
runner modules are private — they are reached only through `sq migrate`, never run as modules
directly.

## Consequences

What this binds today:

- **Schema-version comparisons must use `schema_tuple`.** Any code that branches on the version
  compares tuples; comparing the raw dotted string is a latent ordering bug once a two-digit minor
  appears.
- **A format change is a registry entry, not ad-hoc code.** Adding a migration means appending an
  ordered `Migration` with its deterministic step and, where needed, a manual runbook — so every
  upgrade is recorded, testable, and replayable, and `up` always runs `repair` + stamps at the end.
- **The version is meaningful while alpha**: it points at the release that introduced the format, so
  the changelog is the schema's documentation. Post-1.0, the scheme for the frozen contract is a
  separate decision this ADR does not pre-empt (the stability work, FEAT-13, and the padding
  migration work, FEAT-27, both build on this runner).
- **The mismatch hard-stop is a guardrail, not an inconvenience** — it prevents a newer tool from
  silently writing an older squad into an inconsistent state.

## Status note

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(the schema-version-and-migrations gotcha) and the migration docs. It is documented here as a
decision already **in force**, not newly debated in-tool. Left **Proposed** for the manager to accept
with the set.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
