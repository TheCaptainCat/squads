---
id: FEAT-000177
sequence_id: 177
type: feature
title: Pluggable item-file serialization format (JSON/XML)
status: Draft
parent: EPIC-000031
author: product-owner
refs:
- FEAT-000176
- FEAT-000032
description: Allow JSON or XML as the serialization format for item files in place
  of markdown-with-comment-tags, configured via .squads.toml
subentities:
- local_id: US1
  title: As a team using agent tooling, I want item files stored as JSON so that I
    can use standard JSON tooling and skip the markdown parser
  status: Todo
- local_id: US2
  title: As a team integrating with XML-based systems, I want item files stored as
    XML so that I can pipe squad data into existing XML toolchains without conversion
  status: Todo
created_at: '2026-06-23T12:33:42Z'
updated_at: '2026-06-23T12:59:51Z'
---
<!-- sq:body -->
## Problem

Item files are currently markdown with YAML frontmatter and sq comment markers. This format was chosen so files are human-readable in a text editor or on GitHub. But as the team grows more agent-driven, the files are increasingly read and written by sq — the human-readability constraint may no longer be worth the parser complexity.

## Value

Offering JSON or XML as an alternative serialization format would simplify the storage layer (no markdown parser, no marker regex), enable schema validation at the file level, and open the door to tooling that already speaks those formats. Configured via `.squads.toml`.

## PREREQUISITE: Architect ADR required before any implementation

This feature collides with two core engine invariants and cannot be built without resolving them first. An architect ADR is a hard prerequisite dependency on this feature — do not author that ADR here; route this to the architect.

**Invariant 1 — Frontmatter is the source of truth.**

The engine states: the per-item .md file is the source of truth; .squads.json is a rebuildable cache. A JSON/XML format still needs to satisfy this guarantee, but 'frontmatter' is a markdown-specific term. The ADR must define what 'source of truth' means for each format and how `sq repair` rebuilds the index from non-markdown files.

**Invariant 2 — Marker-safe edits only.**

The engine states: touch file content solely via `_sections.py`; never rewrite an agent-authored body. The sq marker machinery (the comment tags that delimit managed vs. agent-authored prose regions) is markdown-specific. In a JSON/XML format, markers become moot: the body and prose regions become named fields, not delimited text spans. The storage abstraction must therefore define a **format-neutral contract for 'the item and its editable body/prose regions'** that works across formats, so `_sections.py`'s role can be fulfilled by a format-appropriate equivalent. Without this contract, the invariant is silently violated for non-markdown stores.

## Scope (pending ADR)

- A format selector in `.squads.toml` (`format = json | xml | markdown`), defaulting to `markdown`.

- A format-neutral storage contract (defined in the ADR) that generalizes the marker-safe edit role currently owned by `_sections.py`.

- JSON and XML serializers/deserializers that satisfy the contract and pass a format-conformance suite.

- Migration path: `sq repair` can ingest any supported format and rebuild the index regardless of which format is active.

## Out of scope

ID prefix and layout changes — those are tracked in FEAT-000176 and can ship independently.

## Acceptance (conditional on ADR)

- An architect ADR is approved that defines the format-neutral storage contract and resolves both invariant collisions.

- A squad configured for JSON (or XML) passes the same command/CLI test matrix as a markdown squad.

- `sq repair` rebuilds the index from JSON/XML files alone; the rebuild is reversible to markdown with no data loss.

- The format-conformance suite passes for every supported format.

- Existing markdown squads are unaffected (no migration required for the default).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 177 add-story "As a <role>, I want … so that …"`; track with `sq feature 177 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a team using agent tooling, I want item files stored as JSON so that I can use standard JSON tooling and skip the markdown parser |
| US2 | Todo |  | As a team integrating with XML-based systems, I want item files stored as XML so that I can pipe squad data into existing XML toolchains without conversion |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a team using agent tooling, I want item files stored as JSON so that I can use standard JSON tooling and skip the markdown parser

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance (all conditional on the architect ADR being approved):**

- `format = json` in `.squads.toml` switches item files to JSON serialization.

- All sq commands pass the full CLI test matrix against a JSON-format squad.

- The JSON store passes the format-conformance suite.

- `sq repair` rebuilds the index from JSON files alone.

- The format-neutral body/prose contract is honored: body regions are named fields, editable only through sq commands, never overwritten wholesale.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a team integrating with XML-based systems, I want item files stored as XML so that I can pipe squad data into existing XML toolchains without conversion

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance (all conditional on the architect ADR being approved):**

- `format = xml` in `.squads.toml` switches item files to XML serialization.

- All sq commands pass the full CLI test matrix against an XML-format squad.

- The XML store passes the format-conformance suite.

- `sq repair` rebuilds the index from XML files alone.

- The format-neutral body/prose contract is honored: body regions are named elements, editable only through sq commands.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T12:34:58Z] Nina Product:
  - This feature has a hard prerequisite: an architect ADR resolving the two invariant collisions (source-of-truth semantics for non-markdown formats, and a format-neutral contract replacing the markdown-specific marker machinery). Implementation must not begin until that ADR is approved. @architect please author the ADR when this feature reaches Ready.
- [2026-06-23T12:59:51Z] Robert Architect:
  - @product-owner ADR-000180 now exists, resolving both invariant collisions: it restates source-of-truth and marker-safety format-neutrally, splits the store into a format-agnostic locator and a pluggable codec, and defines body/prose regions as named fields/elements (not markdown text spans) so JSON/XML can honor the no-clobber guarantee. It cross-references ADR-000179 (FEAT-000176) — the two share the ItemStore seam. Left Proposed for review — not Accepted, no tasks created.
<!-- sq:discussion:end -->
