---
id: FEAT-976
sequence_id: 976
type: feature
title: Store role and skill origin, lock system skills
status: Ready
author: product-owner
refs:
- MILE-934:targets
subentities:
- local_id: US1
  title: As an operator, I want one stored origin on every role and skill
  status: Todo
- local_id: US2
  title: As an operator, I want existing squads stamped by a migration
  status: Todo
- local_id: US3
  title: As an operator, I want system skills refused by every write verb
  status: Todo
created_at: '2026-09-29T14:19:13Z'
updated_at: '2026-10-09T18:43:30Z'
---
<!-- sq:body -->
Whether a role or skill is system (bundled or spec-generated) or project-authored is recorded on the entity, not recomputed per surface. Today the surfaces disagree, read from source and not driven:

- `sq skill show` prints `kind:` from the roster body-view classification, while `show --json` prints `system` from a different, bundled-blind rule (see the comment near the `system` computation in the skill CLI module).
- `sq role catalog` has an `Origin` column computed as slug-in-bundled-set, which prints `bundled` or `project`. Its docstring claims it also tells apart a project-overridden bundled role; the code cannot.
- `sq skill list`, `sq list -t skill`, `sq role list` and `sq role show` carry no origin. Dev roles are absent from the catalog.

## Spec

- One stored `origin` field in the entity's frontmatter (frontmatter is the source of truth), with a small closed vocabulary: `system` and `project`. Every surface reads that field and shows it under the single name `origin`: list, show, `--json` and `role catalog`. In `role catalog` the value `bundled` becomes `system`.
- `sq repair` rebuilds the index from frontmatter and must round-trip the field.
- Creation stamps it: `sq init`, `sync` and role activation of a bundled or spec-generated role or skill stamp `system`; `sq skill add` and project-declared roles stamp `project`.
- Migration for existing squads: a schema migration stamps every existing role and skill missing the field. A role or skill that the bundled catalog or the spec's generated skills name is stamped `system`; every other one is stamped `project`. A role item carrying `extra.tech` (the generated developer template) is stamped `system`; a declared developer, a role file with the `dev` capability, is stamped `project`. The migration is idempotent and reports a count.
- An overridden bundled role keeps origin `system`: origin records where the entity came from. The `role catalog` docstring claim that it tells apart a project-overridden bundled role is dropped.
- Every content-changing write verb on a `system` skill or role is refused with an error naming the real authoring surface (the playbook for skills, the role override for roles). `comment` and `comments` are not content-changing and stay allowed on system skills and roles. The refusal reuses the classification behind the existing body refusal (`_reject_unwritable_body`), which already refuses replace and append on spec-generated roles and skills, and `--force` does not lift it. No second membership test is introduced.
- Refusal and label are two readings of the same thing and agree on every bundled or spec-generated skill and role. They diverge in one documented case only: a system skill whose view the project has dropped from `[selected]` leaves the refusal classification and is writable again, exactly as its body is today, while its origin stays `system`. The refusal follows the classification, never the stored origin, so that escape keeps working. The existing body refusal on project-declared roles (their definition lives in the role override file) is unchanged.

## Out of scope

Verbs new to roster entities (see the verb parity feature). Making system skills editable.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 976 add-story "As a <role>, I want … so that …"`; track with `sq feature 976 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator, I want one stored origin on every role and skill

<!-- sq:story:US1:body -->
Acceptance:
- Frontmatter carries origin (system or project) on every role and skill; the closed vocabulary is exactly those two values.
- list, show, --json and role catalog all print the same value under the name origin; sq role list, sq role show, sq skill list and sq list -t skill gain it; developer roles (generated and declared) appear in the catalog with their origin; sq skill show's kind line is replaced by origin, and show --json carries origin instead of the bundled-blind system flag.
- role catalog --json prints system where it printed bundled before.
- sq repair rebuilds origin from frontmatter (delete the index, repair, same values); the two divergent derivations (the kind line and the bundled-blind system flag) are gone.
- An overridden bundled role keeps origin system, and the role catalog docstring claim otherwise is dropped; a test overrides a bundled role and asserts system.
- Creation stamps: sq init, sync and activating a bundled or spec-generated role/skill give system; sq skill add and a project-declared role give project.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an operator, I want existing squads stamped by a migration

<!-- sq:story:US2:body -->
Acceptance: a migration stamps every existing role and skill lacking origin: named by the bundled catalog or spec-generated skills means system, everything else project; a role item carrying extra.tech is system, and a declared developer (a role file with the dev capability) is project; idempotent; reports counts; sq check clean afterwards; tests cover a squad with a project-authored skill, an overridden bundled role, a generated developer role and a declared developer.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an operator, I want system skills refused by every write verb

<!-- sq:story:US3:body -->
Acceptance:
- Every content-changing write verb on a system skill (update, body, remove/rm, status, view edits) is refused with exit 1 and an error naming the playbook as the authoring surface; on a system role, naming the role override. Verbs that FEAT-977 adds to skills and roles are covered by the same refusal as they land.
- comment and comments stay allowed on system skills and roles.
- The refusal comes from the same classification as the existing body refusal, and --force does not lift it; a test asserts no second membership test exists.
- Project skills stay fully writable; a system skill whose view the project dropped from [selected] is writable, as its body is today, and still shows origin system.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T14:30:18Z] Pierre Chat:
  - A project-overridden bundled role keeps origin "system": origin records where it came from. Drop the claim from role catalog's docstring.
- [2026-10-09T15:35:22Z] Nina Product:
  - 2026-10-09 readiness pass: folded in the origin-stays-system ruling (already in body and US1), the comment/comments carve-out, and the role catalog value change bundled to system. Reconciled the refusal with origin: the refusal follows the existing body-refusal classification (the code already documents that a dropped-view system skill becomes writable while staying template-owned), origin is the label. Moved to Ready.
- [2026-10-09T18:13:12Z] Pierre Chat:
  - 2026-10-09: confirmed as written. A system skill whose view the project dropped is writable again and still shows origin system: origin is provenance, the refusal follows whether the body is generated.
- [2026-10-09T18:43:30Z] Nina Product:
  - 2026-10-09 per ADR-984: migration and origin stamping now read a role carrying extra.tech as system and a declared developer (dev capability) as project; body, US1 and US2 updated. Still Ready.
<!-- sq:discussion:end -->
