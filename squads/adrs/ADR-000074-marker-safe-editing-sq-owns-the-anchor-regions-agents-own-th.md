---
id: ADR-74
sequence_id: 74
type: decision
title: 'Marker-safe editing: sq owns the anchor regions, agents own the prose'
status: Accepted
author: architect
refs:
- BUG-56
- ADR-71
- GUIDE-79
description: File content is mutated only through the sections layer; anchor tags
  delimit managed regions; agent prose is never rewritten
created_at: '2026-06-12T14:23:04Z'
updated_at: '2026-08-03T08:41:20Z'
---
<!-- sq:body -->
## Context

squads and the agents working through it share the same files: the tool writes frontmatter, headings,
status badges, and summary tables, while agents author prose — descriptions, comments, sub-entity
bodies. Both need to edit the same `.md` file without destroying each other's work. The design
question was how to draw that boundary so the tool can rewrite its regions precisely while never
touching an agent's words.

A naive "regenerate the whole file from the model" approach would erase agent prose on every update;
free-text find-and-replace would be fragile against edits. The chosen mechanism is explicit,
machine-findable boundaries: invisible HTML-comment anchors that delimit each region the tool owns,
so edits are scoped to exactly those regions and everything between an agent's anchors is preserved
verbatim.

## Decision

**Marker-safe editing: sq owns the anchor regions, agents own the prose, and all edits go through the
sections layer.** Regions are delimited by invisible HTML-comment anchors of the form open-tag and
matching close-tag (written here as plain prose — the body anchor pair, the discussion anchor pair,
a sub-entity's block/head/body/discussion anchors). `_sections.py` is the **only** place file content
is mutated: `get_section`, `replace_section`, `append_to_section`, `region_lines`, and the
frontmatter split/join/replace helpers. Agents never edit the `.md` directly — they author through
commands (`sq body`, `sq <kind> body`, `sq comment`), which route to the sections layer.

The marker regex is deliberately strict (`sq:` followed by an alphanumeric start) so that documentation
prose mentioning anchor syntax inside backticks is not mistaken for a real marker, and so a comment
that contains literal anchor-tag syntax cannot break a file's marker integrity.

## Consequences

What this binds today:

- **No code rewrites a whole item file.** `update_frontmatter` rewrites only the frontmatter and
  preserves the body verbatim; region edits go through the sections helpers; agent prose between the
  anchors is never regenerated. Any feature that needs to change file content adds or edits a region
  through this layer — it does not reach for the raw file.
- **The anchor tags are part of the on-disk contract.** Their names and the strict matching rule are
  load-bearing; `sq check` lints for unbalanced or duplicated markers, and the strict regex is what
  lets prose safely *mention* marker syntax.
- **Sub-entity blocks are anchor-scoped too** — heading, head badges, body, and discussion each have
  their own region, so the tool can re-render the derived parts (heading, head, summary) while the
  agent's body prose stays put.
- **Prose carrying literal marker syntax is refused, not sanitized**, because a stored comment or
  body that reproduced a well-formed anchor would otherwise corrupt the region machinery (the failure
  mode fixed in BUG-56). One guard covers every prose input that lands inside a marked region — body,
  comment message and title — and it raises rather than rewriting what the author wrote.
  *Corrected 2026-08-03: this consequence said "sanitized". The shipped mechanism is refusal
  (`reject_markers`), which is the stronger and more honest form — silently altering an author's text
  to make it storable is exactly the class of edit the rest of this decision forbids.*

## Provenance

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(invariant 3 and the marker-regex gotcha) and `docs/internals.md` (§5). It is documented here as a
decision already **in force**, not newly debated in-tool.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:41:20Z] Robert Architect:
  - Dropped the "Left **Proposed** for the manager to accept with the set" closer and retitled the section from "Status note" to "Provenance". Status prose in a body is forbidden here and this one had been false since the day the set was accepted. The provenance itself is kept and is worth keeping — this decision predates squads tracking itself and lived only in CLAUDE.md and docs/internals.md, which is why the body reads retroactively. Part of one sweep across the ten retroactive decisions (49, 71-78, 85), not ten tickets.
  - Corrected the fourth consequence: it said comment text is "sanitized" against literal marker syntax. The shipped mechanism is refusal — `reject_markers` at `_services/_base.py:286` raises for body, comment message and title alike. Worth fixing rather than glossing, because refusal is the stronger form and silently altering an authors text to make it storable is exactly the class of edit the rest of this decision forbids.
  - Everything else verified: the strict marker regex at `_sections.py:68`, all the named section helpers, and the marker lint in `sq check`.
<!-- sq:discussion:end -->
