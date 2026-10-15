---
id: FEAT-1017
sequence_id: 1017
type: feature
title: Comments are shown, edited and removed by short hash
status: Draft
author: product-owner
refs:
- ADR-1013:implements
- MILE-934:targets
- FEAT-980:depends-on
- FEAT-977:depends-on
description: 'Address a comment by derived short hash: comment <hash> show|edit|remove,
  by its author, on every type'
created_at: '2026-10-15T20:17:43Z'
updated_at: '2026-10-15T20:17:43Z'
---
<!-- sq:body -->
Implements the accepted decision on comment addressing: a comment is shown, edited and removed by a short hash, only by its author, on every type. The decision is the spec; the stories below cite its numbered sections and add acceptance only.

## Scope

- The address grammar `sq <type> <n> [<kind> <k>] comment <hash> show|edit|remove` and the hash itself (decisions 1, 2, 3).
- `show`, `edit` and `remove`, with the author match, the edit mark and the duplicate rules (decisions 3 to 6, 9).
- Marker-safe line-span splices and the two reflog ops (decisions 7, 8, 10).
- The hash in every render, in `comments --json`, in `show --json`, in search and in inbox hits, plus the VS Code client fields (decision 11).
- Roster types: skills, roles and operators (decision 3).
- Documentation, bundled guidance and the dated notes the decision lists.

## Out of scope

Per-bullet addressing. Import events that edit or remove. Access control beyond the author match: `--as` is unauthenticated, and no text may call the match a permission. A tombstone on removal. A stored comment id. Any migration of existing comments, and any millisecond timestamp.

## Sequencing

Needs the slug header (the hash takes the slug) and the roster comment verbs (this work extends them), and changes bundled guidance, so it comes after the 0.16.0 bump. Order in the release: after the verb parity feature, before the pronouns and invocability features. It adds nothing to the schema or the migration runner; the edit mark extends the header grammar by one optional group, shipped in the same release as the slug header.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1017 add-story "As a <role>, I want … so that …"`; track with `sq feature 1017 story <n> update --status <Status>`._

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
