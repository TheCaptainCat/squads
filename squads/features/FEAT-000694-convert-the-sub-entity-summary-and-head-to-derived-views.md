---
id: FEAT-694
sequence_id: 694
type: feature
title: Convert the sub-entity summary and head to derived views
status: Draft
author: product-owner
refs:
- FEAT-693:depends-on
description: Replace the two hand-rolled sub-entity projections with declared derived
  views on the body sink, output byte-identical
created_at: '2026-07-29T13:52:49Z'
updated_at: '2026-07-29T14:22:17Z'
---
<!-- sq:body -->
## The problem

The sub-entity roll-up summary and the head badge line are hand-rolled projections: a table and a
badge line derived from state held in the parent's frontmatter, assembled by dedicated code and
templates rather than by any general facility. Once derived views exist, that is two
implementations of one idea — and the bespoke pair is the one nobody will remember to extend.

## Shape

Both surfaces become declared derived views on the `body` sink: the summary as a table projection
over the parent's sub-entity collection, the head as a single-row projection over one sub-entity.
The bespoke assembly path is deleted rather than left in place beside the general one.

Nothing about the rendered result changes. This is a substitution of mechanism underneath output
that stays exactly as it is.

## Acceptance

- Rendered output is byte-identical to what the bespoke path produced: existing golden files pass
  unchanged, and any golden that needs editing is treated as a defect in the conversion rather
  than as an expected update.
- Refresh-on-mutation still holds: every sub-entity change re-renders the head and summary before
  the transaction returns.
- The bespoke assembly code and its direct templates are removed, not orphaned.
- Marker-safe editing is preserved — the materialized regions stay inside their anchors and no
  agent-authored body content is touched.
- Whether a migration is required is settled explicitly. Rendering-only changes should need none;
  that needs proving, not assuming.

## Risk

This is load-bearing rendering with goldens and migration history behind it, and it delivers no
user-visible change. The whole value is having one code path instead of two, which makes
byte-identical output the bar rather than a nice-to-have. If the general mechanism cannot reproduce
the existing output exactly, that is a finding about the mechanism's design, not a reason to adjust
the output.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 694 add-story "As a <role>, I want … so that …"`; track with `sq feature 694 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T14:22:17Z] Pierre Chat:
  - Parked with FEAT-693; both land in 0.14.
<!-- sq:discussion:end -->
