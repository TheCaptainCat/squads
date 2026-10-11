---
id: FEAT-986
sequence_id: 986
type: feature
title: 'Retire the -dev pseudo-role: a developer declares a capability'
status: Ready
author: product-owner
refs:
- MILE-934:targets
- ADR-984:implements
- BUG-985:fixes
description: Roles declare capabilities; the playbook addresses *<name>; developers
  are ordinary roles on every surface
subentities:
- local_id: US1
  title: As an adopter, I want to declare a capability on a role and address it from
    the playbook
  status: Todo
- local_id: US2
  title: As an adopter, I want declared and templated developers treated alike everywhere
  status: Todo
- local_id: US3
  title: As an adopter, I want a -dev-named role with no capability to be an ordinary
    role
  status: Todo
- local_id: US4
  title: As an operator, I want extra.is_dev gone and existing squads migrated
  status: Todo
- local_id: US5
  title: As an operator, I want existing slugs untouched and sq dev add --slug
  status: Todo
- local_id: US6
  title: As an adopter, I want an unknown slug to resolve to nothing
  status: Todo
- local_id: US7
  title: As an agent, I want generated text to name roles from the roster
  status: Todo
- local_id: US8
  title: As an adopter, I want my [dev] colour override to reach existing developers
    on sync
  status: Todo
- local_id: US9
  title: As a tool author, I want capabilities as an additive --json key
  status: Todo
- local_id: US10
  title: As an adopter, I want the docs to cover capabilities and the upgrade changes
  status: Todo
created_at: '2026-10-09T19:16:16Z'
updated_at: '2026-10-11T20:18:45Z'
---
<!-- sq:body -->
## Why

Today the engine decides "is this role a developer?" in two ways that disagree. One is a stored marker that only `sq dev add` writes; the other is whether the slug ends in `-dev`. The consequences land on adopters and agents:

- An adopter who declares their own developer role (say `platform-dev`, titled "platform engineer") gets the developer guidance on some surfaces and not on others: the pointer preloads the developer skills, yet `sq dev list` says "no developers".
- An adopter whose role is not spelled `-dev` (say `backend-engineer`) cannot receive the developer guidance at all.
- An adopter who overrides the `[dev]` table sees the colour applied when a developer is added and silently reverted for that developer by the next `sq sync`.
- Agents are told that "a developer's slug is `<tech>-dev`" in generated text, even in squads where that is false.
- `sq role go-dev show` previews a developer that does not exist, and an override file for a role that is not on the roster is accepted or rejected depending on how its slug is spelled.

The release is named "roles, not slugs". This feature makes a developer an ordinary role that declares a capability, and lets a project declare capabilities of its own.

## Scope

- A role declares zero or more capabilities by name. The playbook can address every live holder of a capability with `*<name>`; `*dev` is the first such address and keeps working in every existing playbook override.
- The bundled catalog declares one capability, `dev`. A project may declare others (for example `*reviewer` over two reviewer roles) with no engine change.
- A declared developer (a role file that declares the `dev` capability) and a templated one (made by `sq dev add --tech`) are treated alike on every surface.
- `sq dev add` gains `--slug`; existing slugs never change.
- A slug that names no role resolves to nothing, whatever its spelling.
- Generated text names roles from the roster and states no slug pattern.
- A project `[dev]` override reaches existing developers on sync for what the template supplies on every read, such as the colour (BUG-985). The model a developer was created with stays as stored.
- The stored `extra.is_dev` marker is removed and existing squads are migrated.
- `--json` gains `capabilities` on the role surfaces, additively.
- Adopter documentation covers the new vocabulary and the two upgrade changes that have no automatic fix.

## Constraints

- Must not be built in parallel with the pronouns feature (FEAT-961) or ADR-981's `[defaults]`: they extend the same role models and the same closed key space.
- Shares the release's single migration step with comment headers (FEAT-980) and origin stamping (FEAT-976). Whichever contributor lands first creates the runner; the others amend it. This feature adds no schema bump of its own.
- FEAT-976 and FEAT-977 build after this one.

## Enabling work, kept as tasks

The first steps are behaviour-neutral and not adopter-visible: an import-graph guard in `tests/meta`, moving the role views out of the backends package, and moving the role-to-type, role-to-skill and lane derivations into a named module. They are not stories. The tech lead creates them as the first tasks under this feature, ahead of any behaviour change, and each is accepted when the existing suite passes unchanged and the guard records the resulting package edges. Only the story acceptance below is user-visible.

## Does not belong here

- The developer template's prose (title, mission, responsibilities) as catalog data; it stays composed by the engine.
- Stamping `extra.model` at `sq dev add` (a later change to `[dev].model` still does not reach a developer created without `--model`).
- The `op-` slug prefix.
- A capability filter on `sq role list`, and `--json` on `sq dev list`.
- Example slugs in `--help` text.
- Renaming existing developers or changing the default suffix.
- A capability label or catalog table, and any capability name known to the engine.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 986 add-story "As a <role>, I want … so that …"`; track with `sq feature 986 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an adopter, I want to declare a capability on a role and address it from the playbook

<!-- sq:story:US1:body -->
Acceptance:
- A role definition accepts `capabilities`, a list of names matching `[a-z0-9][a-z0-9-]*`, in a `[[roles]]` entry, in a per-slug role file and in the `[dev]` table; default empty. The bundled `[dev]` declares `["dev"]`; the eight bundled roles declare none.
- A malformed name (uppercase, leading hyphen, space, empty) is refused at load with exit 1 and an error naming the file.
- A playbook guide whose subject is `*<name>` addresses every live role holding `<name>`: those roles preload the type's skill; the type's section renders only while at least one holder is live and names the capability and lists the live holders; `authors = true` puts the type in every holder's create lane. This holds for the bundled `dev` and for a name the project declares (test: a project declares `reviewer` on two roles plus an override guide `*reviewer`; both roles gain the skill, section and lane, with no code change).
- Existing playbook overrides that name `*dev` load unchanged.
- A guide in an override addressing a capability that no live role holds is reported by `sq check` and `sq sync`, as a guide naming a non-live role is today. A role holding a capability no guide addresses is not reported.
- The engine source holds no capability name outside the bundled documents (grep for `"dev"` as a capability finds none in code or templates).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an adopter, I want declared and templated developers treated alike everywhere

<!-- sq:story:US2:body -->
Acceptance: for each role shape, each surface gives the same answer; the tests are a table of shape by surface.
- Shapes: templated (`sq dev add --tech rust`); declared (a role file with `capabilities = ["dev"]`, activated with `sq role activate`); suffixed `-dev` without the capability; bundled (for example `architect`).
- Surfaces: the role's pointer skill list, the per-type skill's developer section, the `CLAUDE.md` shared section and its delegate example, the create lane, `sq dev list`, and the example assignee in generated text.
- Templated and declared developers receive identical treatment on all six surfaces. `sq dev list` lists both, and lists neither a suffixed-only nor a bundled role.
- A squad whose only developer is declared still renders the developer section, a delegate example naming that role's slug, and its create lane.
- A squad with no role holding `dev` renders none of the developer sections, as it does with no developer today.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an adopter, I want a -dev-named role with no capability to be an ordinary role

<!-- sq:story:US3:body -->
Acceptance:
- A project role whose slug ends in `-dev`, created without `sq dev add` and declaring no capability, gets no `*dev` guidance: no developer skills in its pointer, not listed by `sq dev list`, not in the developer section, no developer create lane. It remains an ordinary role in the roster and can be assigned work.
- Adding `capabilities = ["dev"]` to its role file and running `sq sync` gives it the full developer treatment from story 2.
- The reverse holds: a role not ending in `-dev` that declares the capability is treated as a developer.
- `sq migrate up` reports each such role (ends in `-dev`, no `extra.tech`, no capability) by slug, rewrites no override file, and the step's manual text names the remedy (declare the capability).
- This is one of the two upgrade changes with no automatic fix and is documented as such (story 10).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an operator, I want extra.is_dev gone and existing squads migrated

<!-- sq:story:US4:body -->
Acceptance:
- After `sq migrate up`, no role item carries `extra.is_dev`; `extra.tech` and `extra.model` are untouched; a second run changes nothing.
- `extra.tech` is no longer a settable field on a role item through `sq role ... update`/`set`-style verbs; `sq dev add` remains its only writer.
- A build with this change reads an un-migrated squad correctly (a developer item still carrying `is_dev` and `tech` resolves, and `sq check` stays clean for it); no new key enters `.squads.json` and `sq repair` after deleting the index reproduces the same values.
- The migration contributes to the release's one 0.15 to 0.16 step and adds no schema bump of its own. If the runner does not yet exist the work creates it; if it does, the work amends it. Test: a squad with the comment-header and origin contributions and this one migrates in a single `sq migrate up`.
- This repository's own squad (two developer items) loses the key and passes `sq check`.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an operator, I want existing slugs untouched and sq dev add --slug

<!-- sq:story:US5:body -->
Acceptance:
- Every existing developer keeps its slug, pointer file, name and history across `sq migrate up` and `sq sync` (byte-identical pointer except for any intended content change).
- `sq dev add --tech Node.js` proposes the slug `node-js-dev`; `--slug <s>` uses `<s>` instead, compared exactly and following the reserved-slug rules (a reserved or `op-` slug is refused with exit 1 naming the rule).
- A second developer for the same tech succeeds with `--slug`; a duplicate slug is refused with exit 1.
- `--tech`, `--name`, `--model` and the name pool behave as before, and the name-pool position counts the items that carry `extra.tech`.
- `sq dev add --help` documents `--slug`.
- No read path consults the `-dev` suffix.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As an adopter, I want an unknown slug to resolve to nothing

<!-- sq:story:US6:body -->
Acceptance:
- `sq role <slug> show` and `sq override scaffold --role <slug>` for a `<tech>-dev` slug with no roster item and no catalog entry exit 1 with the ordinary unknown-role error, not a generated preview.
- A partial `.overrides/roles/<slug>.toml` for a slug with no roster item and no catalog entry is reported by `sq check`, whatever the slug's spelling (a `go-dev.toml` and a `data-lead.toml` are reported alike).
- `sq dev add --tech go` still merges such a file at creation, and afterwards `sq check` is clean.
- These are the other upgrade change with no automatic fix and are documented as such (story 10).
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — As an agent, I want generated text to name roles from the roster

<!-- sq:story:US7:body -->
Acceptance:
- No generated file (`CLAUDE.md`/`AGENTS.md` managed section, pointer skills, per-type skills, bundled playbook prose, the memory skill) states a slug pattern: no "a developer's slug is `<tech>-dev`", no `<tech>-dev` placeholder, no curated list of bundled slugs.
- Delegate examples and the example assignee name concrete slugs of live roles from the roster; with a roster of `architect` and `backend-engineer` (declared developer) the examples use those slugs.
- With no developer live, the examples fall back to a live role and never print an invented slug.
- A grep gate over rendered output for a fresh squad and for a squad with only a declared developer finds no `<tech>` placeholder and no `-dev` pattern sentence.
- The section heading that read "developers" now names the capability and lists the live holders, as story 1 requires.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — As an adopter, I want my [dev] colour override to reach existing developers on sync

<!-- sq:story:US8:body -->
Acceptance (the colour half of the BUG-985 reproduction, run as written):
- With `[dev] model = "haiku"` and `color = "pink"` in `.overrides/roles.toml`, `sq dev add --tech rust` then `sq sync` leaves the pointer at haiku/pink, and a second sync changes nothing.
- A developer added before the override existed picks up the colour on the next `sq sync`; changing the override's colour later reaches existing templated developers on sync.
- The model a developer was created with stays as stored: changing `[dev].model` (haiku to opus) leaves existing developers on their stored model, and only a developer added afterwards gets opus. Tested both ways.
- A per-slug override file still merges over the template for that developer.
- `sq role <slug> show` agrees with the pointer on model and shows colour.
- The template is read from the catalog the squad resolves, not the bundled one; tested with a project catalog that changes `name_pool`.
- BUG-985 can be verified against the colour lines of this story; the model behaviour is the documented stored default, not part of the bug's fix.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — As a tool author, I want capabilities as an additive --json key

<!-- sq:story:US9:body -->
Acceptance:
- `capabilities` appears, always present as an array (possibly empty), in `--json` for `sq role catalog`, `sq role list`, `sq role <addr> show` and on each `roster[]` row of the `playbook` view payload.
- `lane.roles[].slug` keeps its type and still carries `*dev` for the bundled guides.
- `extra.is_dev` is absent from the `extra` object of the generic `show` and `list` payloads; no other existing key changes name, type or position.
- The VS Code client's skew canary still passes unchanged against the new output.
- Text output: `sq role list` and `sq role show` display the capabilities.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — As an adopter, I want the docs to cover capabilities and the upgrade changes

<!-- sq:story:US10:body -->
Acceptance:
- `docs/roles.md` and `docs/overrides.md` no longer document the suffix rule, the `*dev` sentinel, or that an override for a developer not yet added is accepted; they document `capabilities`, `*<name>`, declaring a developer, `sq dev add --slug`, and the `[dev]` template.
- `docs/stability.md` is refreshed: the role document key and the `*<name>` subject in Tier 1, the new key in Tier 3, and the additive `--json` keys. `docs/internals.md`, `docs/agents.md`, the README and the CHANGELOG follow.
- The upgrade section states, with a worked example for each, the two changes that have no automatic fix: a custom `-dev` role must declare `capabilities = ["dev"]`, and an override written before its developer is added now fails `sq check` and no longer previews. It also states that an existing developer picks up a project `[dev]` override on sync for template-supplied values such as the colour, while its model stays as stored at creation.
- Adopter docs carry no sq item references and no development-process content.
- A reader following only the docs can declare a developer role and a second capability, and `sq check` is clean.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T19:19:53Z] Nina Product:
  - 2026-10-09: prose complete against ADR-984; ready for breakdown.
- [2026-10-11T20:18:09Z] Nina Product:
  - 2026-10-11: US8 and the scope line reworded per the operator's ruling: a [dev] override reaches existing developers for template-supplied values (colour); the stored model stays as created.
<!-- sq:discussion:end -->
