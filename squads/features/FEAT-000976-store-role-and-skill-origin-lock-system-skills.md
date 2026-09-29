---
id: FEAT-976
sequence_id: 976
type: feature
title: Store role and skill origin, lock system skills
status: Draft
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
updated_at: '2026-09-29T14:32:08Z'
---
<!-- sq:body -->
Whether a role or skill is system (bundled or spec-generated) or project-authored is recorded on the entity, not recomputed per surface. Today the surfaces disagree, read from source and not driven:

- `sq skill show` prints `kind:` from the roster body-view classification, while `show --json` prints `system` from a different, bundled-blind rule (see the comment near the `system` computation in the skill CLI module).
- `sq role catalog` has an `Origin` column computed as slug-in-bundled-set. Its docstring claims it also tells apart a project-overridden bundled role; the code cannot.
- `sq skill list`, `sq list -t skill`, `sq role list` and `sq role show` carry no origin. Dev roles are absent from the catalog.

## Spec

- One stored `origin` field in the entity's frontmatter (frontmatter is the source of truth), with a small closed vocabulary: `system` and `project`. Every surface reads that field and shows it under the single name `origin`: list, show, `--json` and `role catalog`.
- `sq repair` rebuilds the index from frontmatter and must round-trip the field.
- Creation stamps it: `sq init`, `sync` and role activation of a bundled or spec-generated role or skill stamp `system`; `sq skill add` and project-declared roles stamp `project`.
- Migration for existing squads: a schema migration stamps every existing role and skill missing the field. A role or skill that the bundled catalog or the spec's generated skills name is stamped `system`; every other one is stamped `project`. Dev roles (`<tech>-dev`) are stamped `system`. The migration is idempotent and reports a count.
- Every write verb on a `system` skill is refused with an error naming the real authoring surface (the playbook for skills, the role override for roles). The refusal reuses the classification behind the existing body refusal (`_reject_unwritable_body`), which already refuses replace and append on spec-generated roles and skills, and `--force` does not lift it. No second membership test is introduced.

- An overridden bundled role keeps origin `system`: origin records where the entity came from. The `role catalog` docstring claim that it tells apart a project-overridden bundled role is dropped.

## Out of scope

Verbs new to roster entities (see the verb parity feature). Making system skills editable.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 976 add-story "As a <role>, I want … so that …"`; track with `sq feature 976 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator, I want one stored origin on every role and skill

<!-- sq:story:US1:body -->
Acceptance: frontmatter carries origin (system or project) on every role and skill; list, show, --json and role catalog all print the same value under the name origin; role list, role show, skill list and sq list -t skill gain it; dev roles appear with their origin; sq repair rebuilds it from frontmatter; the two divergent derivations are gone; an overridden bundled role keeps origin system and the role catalog docstring claim otherwise is dropped.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an operator, I want existing squads stamped by a migration

<!-- sq:story:US2:body -->
Acceptance: a migration stamps every existing role and skill lacking origin: named by the bundled catalog or spec-generated skills means system (dev roles included), everything else project; idempotent; reports counts; sq check clean afterwards; tests cover a squad with a project-authored skill and an overridden bundled role.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an operator, I want system skills refused by every write verb

<!-- sq:story:US3:body -->
Acceptance: every content-changing write verb on a system skill (update, body, remove, status, view edits) is refused with an error naming the playbook as the authoring surface; roles name the role override; comment and comments stay allowed; the refusal comes from the same classification as the existing body refusal and --force does not lift it; project skills stay fully writable; a test asserts no second membership test exists.
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
<!-- sq:discussion:end -->
