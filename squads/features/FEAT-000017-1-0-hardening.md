---
id: FEAT-000017
sequence_id: 17
type: feature
title: 1.0 hardening
status: Ready
parent: EPIC-000012
author: product-owner
priority: medium
description: Migration fixture corpus in CI, ~1000-item scale sanity test, verified
  shell completion, decision on the Python >= 3.14 floor
created_at: '2026-06-10T12:41:22Z'
updated_at: '2026-06-11T07:54:53Z'
---
<!-- sq:body -->
## Problem

The strongest promise in the contract — any 0.x squad reaches 1.0 via `sq migrate up` — is
currently tested against nothing but the migrations' own unit tests. We also have no evidence sq
behaves at real-project scale, shell completion is unverified, and the Python ≥ 3.14 floor is an
implicit consequence of our annotation style rather than a recorded decision.

## Value

This is the proving ground for the rest of the epic: each item here converts a claim we *make*
into a claim CI *checks* (or a decision the record *holds*). It is what lets us tag 1.0 without
crossing our fingers.

## Scope

- **Migration fixture corpus** — one frozen, committed squad per released schema version, migrated
  up and `sq check`-ed in CI on every run; a new fixture is added with every future schema bump.
- **Scale sanity test** — a generated ~1000-item squad exercising list/tree/search/repair within
  acceptable time, so we know the index and rendering hold up beyond toy sizes.
- **Shell completion** — verified working for bash/zsh and documented in the README/docs.
- **Python floor** — a recorded decision (ADR) on requiring Python ≥ 3.14, with the trade-off
  (PEP 649 lazy annotations vs. installable audience) written down.

## Acceptance

- CI runs the fixture corpus: every released schema migrates to current and passes `sq check`.
- The scale test runs (in CI or as a marked slow test) with asserted time bounds.
- Completion install steps are documented and verified on bash and zsh.
- The Python-floor ADR is merged and linked from the stability contract.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 17 add-story "As a <role>, I want … so that …"`; track with `sq feature 17 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
