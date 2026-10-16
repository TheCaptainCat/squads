---
id: FEAT-980
sequence_id: 980
type: feature
title: Comment headers carry the author's permanent slug
status: Done
author: product-owner
refs:
- ADR-979:implements
- ADR-971
- FEAT-977
- MILE-934:targets
subentities:
- local_id: US1
  title: As a reader, I want comment headers that name the author's slug
  status: Done
- local_id: US2
  title: As an operator, I want slugs permanent on every write path
  status: Done
- local_id: US3
  title: As an adopter, I want legacy headers migrated once, fail-loud
  status: Done
- local_id: US4
  title: As a tool author, I want author_slug in the discussion JSON
  status: Done
- local_id: US5
  title: As an adopter, I want the header grammar documented
  status: Todo
created_at: '2026-09-29T14:58:15Z'
updated_at: '2026-10-16T14:38:52Z'
---
<!-- sq:body -->
Implements the accepted decision on comment headers: each header names the author's permanent slug, so attribution survives a display-name change. The decision is the spec; the stories below cite its numbered decisions and add acceptance only.

## Scope

- The header grammar and the single shared parser (decision 2), which also removes the disagreement between the discussion split and the search header scan (Context, "The two parsers disagree").
- Slug permanence on every write path, plus the reserved slugs (decisions 1 and 6).
- A one-time corpus migration with no dual-read parser (decision 4).
- `author_slug` in the discussion JSON (decision 5).
- Documentation (Consequences, "Docs").

## Out of scope

A slug-mapping option on the migration (declined in the decision). Any change to search or inbox JSON. Rewriting the name in a header already written.

## Sequencing

This work creates the release's migration step (0.15 to 0.16) and the 0.16 schema; the developer-role retirement and the origin stamping add their contributions to that step afterwards, and neither bumps the schema.

The verb parity feature's comment verbs write this grammar and its update verbs must never touch a slug, so the two are coordinated.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 980 add-story "As a <role>, I want … so that …"`; track with `sq feature 980 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a reader, I want comment headers that name the author's slug

<!-- sq:story:US1:body -->
Acceptance (decisions 2, 3): format_comment writes the header grammar with slug and name; one column-0 pattern with no stripping is shared by the discussion split, match_comment_header and the search/inbox header scan; the name is resolved at write time, line breaks collapsed, slug as fallback; table-driven tests cover names with colons, backticks and accents, and an indented checkbox that is not a header; a round trip per writer (comment core, rename, retype with the squads slug, bulk importer); human renders show name then slug.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an operator, I want slugs permanent on every write path

<!-- sq:story:US2:body -->
Acceptance (decisions 1, 6): no verb, option, override, migration or repair path writes a different slug to an existing roster entry; no update verb takes a slug option; role creation refuses operator, squads and any slug starting with op-; an override document whose slug key differs from its file name is refused naming the file; retype and rename keep refusing roster types; repair never derives or writes a slug; tests attack each path.

Not guarded, by ruling: a slug freed by rm --purge may be taken by a new entity, and creation does not consult comment history; headers written earlier then show the new entity's slug. A test pins that creation succeeds in that case, so nobody adds the check later as a bug fix.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an adopter, I want legacy headers migrated once, fail-loud

<!-- sq:story:US3:body -->
Acceptance (decision 4): this work creates the release's 0.15 to 0.16 migration step, registered so that sq migrate up runs it, and that step scans every discussion region, top-level and each sub-entity's, and resolves every legacy header name across the whole corpus (live and retired roles and operators, plus Operator and squads) before writing anything; a name matching no entry, a name matching several, and a header-shaped column-0 line with a bad timestamp each fail; on any failure nothing is written and sq migrate up exits 1 listing every failure as file:line with a count; only the header line is rewritten and bullets stay byte-identical; already-migrated headers are skipped; the manual runbook names the remedy (add or reactivate the missing entry, or give one of the colliding entries a distinct display name for the run); the schema version the migration stamps is 0.16, introduced here; there is no map option; tests cover each failure kind with no file written.

Also, on its own: on a 0.15 squad holding only this story's work, sq migrate up runs this step alone, exits 0 and stamps 0.16; a squad already at 0.16 reports nothing to migrate; the step is a single entry that later contributions extend, and a test that appends a second contribution to it sees both run in one sq migrate up.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As a tool author, I want author_slug in the discussion JSON

<!-- sq:story:US4:body -->
Acceptance (decision 5): every discussion entry in show --json (item and sub-entity) and every comments --json entry gains author_slug while author keeps the display name; search and inbox JSON are unchanged; the VS Code SqDiscussionEntry gains an optional author_slug and still accepts an older sq that omits it.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an adopter, I want the header grammar documented

<!-- sq:story:US5:body -->
Acceptance (Consequences, Docs; authored by the tech writer): docs/stability.md Tier 1 gains the header grammar and the slug permanence rule and Tier 3 notes author_slug; the comment line in docs/internals.md uses the new grammar; docs/migration.md and the 0.16 CHANGELOG describe the migration and its failure report. Adopter-facing text carries no item IDs and no build-process narration.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T15:35:33Z] Nina Product:
  - 2026-10-09 readiness pass: checked every story against the Accepted ADR-979 text (grammar, reserved slugs, migration failure kinds, author_slug, docs). Matched. Added the explicit slug-reuse-after-purge non-guard (Pierre's ruling in the ADR) and the sub-entity scan scope to the migration acceptance. Moved to Ready.
- [2026-10-12T06:31:58Z] Nina Product:
  - 2026-10-12: build order reversed: this feature creates the release's migration step and the 0.16 schema; story 3 and the sequencing section say so.
- [2026-10-16T14:38:51Z] Catherine Manager:
  - Moved to Done under the manager's delegation: TASK-1004, 1005, 1006 and 1048 Done, their reviews approved, the VS Code preview checked by op-pierre in the dev host on 2026-10-16.
<!-- sq:discussion:end -->
