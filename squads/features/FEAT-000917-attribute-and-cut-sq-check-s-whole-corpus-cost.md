---
id: FEAT-917
sequence_id: 917
type: feature
title: Attribute and cut sq check's whole-corpus cost
status: Draft
parent: EPIC-31
author: product-owner
priority: low
refs:
- FEAT-916
created_at: '2026-09-03T13:06:55Z'
updated_at: '2026-09-03T13:32:07Z'
---
<!-- sq:body -->
## Capability

Attribute, then reduce, `sq check`'s per-corpus cost. This is a separate
problem from FEAT-916 (pre-dispatch startup cost): `sq check` walks the
whole corpus and does real per-item work, so its cost is not the ~0.7s fixed
cost every command pays before dispatch — it is additional work scaled to
corpus size.

**Measurement-first**, same discipline as FEAT-916: attribute where the
per-corpus time actually goes (index load, per-item rule evaluation, per-rule
overhead, I/O) before proposing any mechanism. This shell does not design a
fix.

It matters because `sq check` is not an occasional command: it is the
must-pass gate every agent runs before every handoff in this repo, so its
cost is paid on the team's critical path repeatedly per session, not once.

## Evidence (driven, op-pierre, 2026-09-03, `release/0.15`, this machine, this repo's corpus)

| what | time |
|---|---|
| `uv run sq check` (whole corpus) | 3.203s |

For contrast, the fixed pre-dispatch cost FEAT-916 targets is ~0.7s
(`.venv/bin/sq --version` at 0.740s); `sq check`'s 3.203s is on top of that,
so roughly 2.5s is corpus-scan work specific to this command.

## Relationship to FEAT-916 (not scope)

Distinct problem, same discipline. FEAT-916's fixed-cost reduction (once
built) would still shave a small amount off `sq check`'s total, but the bulk
of the 3.2s is this command's own corpus walk and is untouched by that work.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 917 add-story "As a <role>, I want … so that …"`; track with `sq feature 917 story <n> update --status <Status>`._

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T13:32:07Z] Pierre Chat:
  - Held, not in 0.15. Neither is gated on the web API or the daemon -- both are local CLI work that lands independently -- but 0.15 already carries two full lines and nothing forces these early. Picked up in a later release, or alongside the daemon work when the startup cost starts hurting enough to act on. The measurements are on the record; that was the point of writing them down.
<!-- sq:discussion:end -->
