---
id: FEAT-908
sequence_id: 908
type: feature
title: Upgrade path for the 0.14 view declaration grammar
status: Draft
parent: EPIC-897
author: product-owner
priority: medium
refs:
- MILE-867:targets
- ADR-880:implements
- FEAT-904:depends-on
- FEAT-905:depends-on
description: Adopter-facing side of retiring fields/group_by/order_by and type-attached
  views, which shipped one release ago
subentities:
- local_id: US1
  title: Spec load names the removed key and points at the replacement grammar
  status: Todo
- local_id: US2
  title: Upgrade guidance covers declaration, template, and placement
  status: Todo
- local_id: US3
  title: 0.15 CHANGELOG names this as a breaking change
  status: Todo
created_at: '2026-09-03T09:11:02Z'
updated_at: '2026-09-24T07:59:07Z'
---
<!-- sq:body -->
## Why

FEAT-693 shipped `fields`/`group_by`/`order_by` and `items.<type>.views` type-attachment as
adopter-facing declared surface one release ago (0.14). ADR-880 deletes that grammar outright.
This is the adopter-facing side of that deletion: a clear failure mode for anyone who still has
the old grammar in an `.overrides/workflow.toml`, and the upgrade documentation. ADR-880 rules
the mechanism; this feature is the migration story it deliberately leaves to the adopter side.

## Scope

- Spec load fails clearly (FEAT-904's load-time error) when any of the four removed keys is
  still present, naming the key and pointing at the replacement grammar.
- Documented, step-by-step upgrade guidance covering all three moving pieces an old-grammar
  view must be converted across:
  1. declaration — a `fields`/`group_by`/`order_by`/type-attached view becomes a one-line
     `[views.<name>]` with just `source`;
  2. template — the deleted grouping/ordering logic is re-expressed as Jinja
     `groupby`/`sort`/`selectattr` in `templates/views/<name>.md.j2`;
  3. placement — where type-attachment used to put the view automatically, the adopter now
     places `sq:view:<name>` **through the dedicated placement verb (FEAT-905)** — not by
     typing it into a body, which stays refused.
- Written as adopter-facing prose by the tech-writer once the mechanism lands; this feature
  sets the acceptance criteria the writer's pass is checked against, not the prose itself.
- This is a workflow-spec grammar change, not an item-frontmatter schema change — it belongs in
  upgrade notes/CHANGELOG, **not** as an `sq migrate` runner step.
- A CHANGELOG entry under the 0.15 unreleased section names it as a breaking change with the
  upgrade guidance linked, so it's discoverable from release notes and not only from the ADR.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 908 add-story "As a <role>, I want … so that …"`; track with `sq feature 908 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Spec load names the removed key and points at the replacement grammar

<!-- sq:story:US1:body -->
As an adopter who declared a view under the 0.14 grammar in my own .overrides/workflow.toml, I want spec load to fail with a clear, specific error naming the removed key and the replacement grammar, so my project tells me exactly what changed instead of silently ignoring my declaration or crashing opaquely.

Acceptance: this is FEAT-904's load-time error, verified here from the adopter's seat -- each of the four removed keys (fields, group_by, order_by, items.<type>.views) produces its own named error; test fixtures cover at least one case per removed key.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Upgrade guidance covers declaration, template, and placement

<!-- sq:story:US2:body -->
As an adopter upgrading to 0.15, I want documented, step-by-step guidance for converting an old-grammar view into the new grammar, so my 0.14-declared view keeps working after I upgrade.

Acceptance: guidance covers all three moving pieces with a worked before/after example -- (1) declaration collapses to a one-line source, (2) the grouping/ordering logic moves into the template as Jinja groupby/sort/selectattr, (3) placement happens through the dedicated placement verb (FEAT-905), never by typing the tag into a body; written by the tech-writer as adopter-facing prose.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — 0.15 CHANGELOG names this as a breaking change

<!-- sq:story:US3:body -->
As op-pierre or a future auditor, I want the 0.15 CHANGELOG to carry this as a breaking change with the upgrade guidance linked, so it's discoverable from release notes rather than only from the ADR.

Acceptance: a CHANGELOG entry under the 0.15 unreleased section names the breaking grammar change, added by the tech-writer once the work lands per this project's changelog convention.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-24T07:59:07Z] Theo Writer:
  - US3 is partly covered already. The 0.15.0 CHANGELOG now has a "BREAKING — a view declares only its `source`…" entry under Changed (REV-960 F8). It names the removed keys, the load failure, the removed `--json` shapes and the roll-up order change. Still open for US3: a link to the upgrade guidance, once US2 writes it. Also still open: quoting or describing the dedicated retired-key message, if REV-960 F2 lands one.
<!-- sq:discussion:end -->
