---
id: FEAT-575
sequence_id: 575
type: feature
title: 'CLI surface completeness: roles, operators, sub-entities, comments'
status: Done
author: product-owner
refs:
- REV-565
subentities:
- local_id: US1
  title: Add sq role list (active roster, active/inactive marker)
  status: Done
- local_id: US2
  title: Add sq operator list (+ --json)
  status: Done
- local_id: US3
  title: Add guarded remove for finding/story/subtask sub-entities
  status: Done
- local_id: US4
  title: Add sq <type> <n> comments read-back verb (+ --json)
  status: Done
- local_id: US5
  title: Lock in add-finding/add-story/add-subtask body-input parity
  status: Done
- local_id: US6
  title: Bundled designer/UX role (shape TBD — architect)
  status: Cancelled
created_at: '2026-07-22T08:41:07Z'
updated_at: '2026-07-23T13:22:28Z'
---
<!-- sq:body -->
## Capability

Round out five real CLI surface gaps surfaced by the same adopter migration,
closing the enumerate/read-back/delete holes that forced workarounds, plus
track one open design question:

- `sq role list`: a real verb listing the **active** roster (distinct from `sq
  role catalog`, which lists the bundled-but-not-necessarily-active catalog),
  with an active/inactive marker per row.
- `sq operator list` (+ `--json`): there is currently no way to enumerate
  registered operators at all — only `add`/`show`/`rm`.
- Guarded `remove` for sub-entities (`finding`/`story`/`subtask`), matching the
  parent-item `remove` contract (hard-delete, `--yes` to confirm) — a
  mis-created sub-entity is currently permanent.
- `sq <type> <n> comments` (+ `--json`): a read-back verb for an item's
  discussion, so verifying/scripting against comment history doesn't require
  `show --json` plus manually indexing into the `discussion[]` array.
- Confirm and, where missing, close out body-input parity on `add-finding` /
  `add-story` / `add-subtask`: `--file` (incl. `-` for stdin) and `-m` already
  work on all three as verified against the current tree — the remaining ask
  is making sure this holds uniformly and that the placeholder-stub `sq check`
  warning fires **only** when no body was supplied at all (already the
  observed behavior; this story is the regression-test/parity-lock-in, not
  new mechanism).
- A bundled designer/UX role is a related but separate open question (no
  bundled role today; `dev add` requires a coding `--tech`). Tracked as a
  placeholder story only — its exact shape (bundled role vs. `dev add --tech
  ux --kind design`) is the architect's call, not scoped here.

**Note on `docs/stability.md`:** that doc currently states standalone
`role list`/`skill list`/`operator list` were **removed pre-1.0** in favor of
`sq list -t <type>` — a deliberate prior decision. Adding `role list` and
`operator list` back reverses that call; whoever scopes the implementation
task should reconcile this with the architect (an ADR amendment may be
warranted) and update `docs/stability.md`'s "removed" claim, not just add the
verb.

## Why

REV-565 (adopter-project migration field report) hit each of these as either a real
gap forcing a workaround (`show --json` + manual array indexing for comments;
no way to delete a spurious finding created during rework; no way to enumerate
operators at all) or a place where the docs described a command that plain
doesn't exist. Individually each is medium-to-low severity; together they're
the difference between "the CLI's CRUD surface is complete" and "there are
edges you have to route around."

## Acceptance

- `sq role list` lists the active roster with an active/inactive marker;
  `sq role catalog` is unchanged.
- `sq operator list` (and `--json`) enumerates registered operators.
- `sq review <n> finding <k> remove --yes`, `sq feature <n> story <k> remove
  --yes`, `sq task <n> subtask <k> remove --yes` hard-delete the sub-entity
  (index + frontmatter), guarded the same way parent-item `remove` is.
- `sq <type> <n> comments` (and `--json`) lists the item's discussion without
  going through full `show`.
- `docs/stability.md`'s "standalone list commands removed" claim is updated to
  match the new reality (not left contradicting the shipped CLI).
- `sq check` stays clean; existing sub-entity/comment/list tests keep passing.
- The designer/UX-role story stays a tracked placeholder until the architect's
  recommendation lands; not implemented as part of this feature's other five
  stories.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 575 add-story "As a <role>, I want … so that …"`; track with `sq feature 575 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Add sq role list (active roster, active/inactive marker) |
| US2 | Done |  | Add sq operator list (+ --json) |
| US3 | Done |  | Add guarded remove for finding/story/subtask sub-entities |
| US4 | Done |  | Add sq <type> <n> comments read-back verb (+ --json) |
| US5 | Done |  | Lock in add-finding/add-story/add-subtask body-input parity |
| US6 | Cancelled |  | Bundled designer/UX role (shape TBD — architect) |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Add sq role list (active roster, active/inactive marker)

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
New verb distinct from sq role catalog; lists activated roles with a marker column (F3).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Add sq operator list (+ --json)

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Enumerate registered operators; currently only add/show/rm exist (F4).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Add guarded remove for finding/story/subtask sub-entities

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Parity with parent-item remove: hard-delete + --yes confirmation (F13).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Add sq <type> <n> comments read-back verb (+ --json)

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
List an item's discussion without going through full show --json (F15).
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Lock in add-finding/add-story/add-subtask body-input parity

<!-- sq:story:US5:head -->
**Status:** 🟢 Done
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
Verify --file/-/-m already satisfy the non-stub path uniformly across all three add-* commands; add regression coverage (F10).
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Bundled designer/UX role (shape TBD — architect)

<!-- sq:story:US6:head -->
**Status:** ⚫ Cancelled
<!-- sq:story:US6:head:end -->

<!-- sq:story:US6:body -->
F7: no bundled designer/UX role today; dev add requires a coding --tech. Track the gap here; exact shape (bundled role vs. dev add --tech ux --kind design) is the architect's call — don't build ahead of that decision.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
- [2026-07-23T13:22:23Z] Catherine Manager:
  - Cancelled: F7 (designer/UX role) is resolved by FEAT-543's custom non-dev roles + the FEAT-574 docs pointer — no bundled role or dev-add path to build.
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T08:40:50Z] Catherine Manager:
  - FEAT-575 Done: sq role list, sq operator list, sq <type> <n> comments, add-* body parity, and a guarded sub-entity remove (marker-safe remove_section + atomic remove_block with dangling-story refusal). Reviewed REV-632 (Approved; remove correctness + store._log + json fidelity verified, F1/F2 nits fixed). Full suite green. Accepted under the standing non-visual delegation.
<!-- sq:discussion:end -->
