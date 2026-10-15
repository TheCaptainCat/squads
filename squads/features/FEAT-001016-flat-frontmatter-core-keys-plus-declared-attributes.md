---
id: FEAT-1016
sequence_id: 1016
type: feature
title: 'Flat frontmatter: core keys plus declared attributes'
status: Draft
author: product-owner
refs:
- ADR-1007:implements
- MILE-934:targets
- FEAT-980:depends-on
description: No extra block; spec-declared attributes; unknown keys kept; writes remove
  only targeted keys; flattened by the 0.16 runner
subentities:
- local_id: US1
  title: As a reader, I want one flat mapping with slug as a core key
  status: Todo
- local_id: US2
  title: As an adopter, I want to declare attributes in my spec
  status: Todo
- local_id: US3
  title: As an adopter, I want attributes validated, never destroyed
  status: Todo
- local_id: US4
  title: As an adopter, I want no write to remove an untargeted key
  status: Todo
- local_id: US5
  title: As an operator, I want one meaning per name
  status: Todo
- local_id: US6
  title: As an adopter, I want old corpora flattened once, fail-loud
  status: Todo
- local_id: US7
  title: As a tool author, I want flat --json and a matching canary
  status: Todo
- local_id: US8
  title: As an adopter, I want the docs and changelog to say flat
  status: Todo
created_at: '2026-10-15T20:12:57Z'
updated_at: '2026-10-15T20:17:51Z'
---
<!-- sq:body -->
Implements the accepted decision that frontmatter is one flat mapping: core keys plus attributes declared in the spec, with unknown keys kept. The decision is the spec; the stories cite its numbered sections and add acceptance only. The nested `extra:` block goes, on every wire surface.

## Scope

- The model: `Item.attributes`, `slug` as a core key, `AttributeKey` and the item accessor (sections 1, 2, 3 and 6).
- The `[items.<type>.attributes]` grammar, the loader's pinned roster attributes, the refused names and the refusal of `extra_fields` (sections 3 and 4).
- Validation in `sq check` and the opt-in undeclared-key check (sections 5 and 11).
- The write invariant: a write never removes a key it did not target (section 7).
- Name collisions: `description`, `title`, `slug`, `tech` (section 8).
- The migration step of the 0.16 runner (section 9).
- The `--json`, render-context and client canary contract (section 10).
- Docs, changelog and the dated ADR notes (Consequences).

## Out of scope

A one-release alias for `extra_fields`; refusing unknown keys at load; per-type model subclasses. All are rejected in the decision.

## Sequencing

This is the first frontmatter step of the 0.16 migration runner that the comment-header feature creates, so it depends on that feature. It changes bundled files, so it follows the 0.16.0 version bump and precedes the corpus-guidance task, the bundled-file task, and the origin, pronouns and invocability features, each of which then writes flat keys from its first commit.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1016 add-story "As a <role>, I want … so that …"`; track with `sq feature 1016 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a reader, I want one flat mapping with slug as a core key

<!-- sq:story:US1:body -->
Acceptance (decisions 1, 2 and 6):
- A file written by the model has one flat mapping: the core keys named in the decision plus every attribute at the top level. No `extra` key is written, and `extra` appears in no `--json` row and no render context.
- `Item.attributes` holds every attribute, declared or not, in one mapping; declaredness is asked of the spec at the boundary, never a storage split. The index carries the whole mapping and `sq repair` rebuilds it from the files.
- `slug` is core: written for every roster-category item and for any other item whose file already carried it; read from frontmatter when present and from the file name otherwise. Every former `extra.get(SLUG, item.slug)` site reads `item.slug`.
- Internals read attributes through named `AttributeKey` constants and one item accessor; typed roster accessors treat a stored value of the wrong kind as unset. No reader indexes the mapping by a string literal (a guard test checks it).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an adopter, I want to declare attributes in my spec

<!-- sq:story:US2:body -->
Acceptance (decisions 3 and 4):
- `[items.<type>.attributes]` declares `kind` (`str`, `list`, `bool`, `date`), `required` (default false) and `settable` (default true), for built-in, reserved and adopter types alike. No Python table lists the keys of a type; the bundled spec declares attributes on guide, milestone, review, role and skill.
- An adopter declares a custom attribute of any kind on any type, including a roster type, and `sq update --set` writes it with kind validation.
- The loader pins the roster attributes the engine materialises into agent-host files: a resolved spec whose role or skill type lacks one, or declares it with another kind, is refused naming the key and the remedy. An override may add attributes to a roster type.
- The loader refuses an attribute or badge code that is a core key, a duplicate on the same type, a name `--json` adds to a row, `path`, `prefix` or `extra`, each naming the key.
- An override still carrying `extra_fields` is refused at load, naming `attributes` and the equivalent table. The old key is never read.
- Custom badge fields are stored top-level under their code.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an adopter, I want attributes validated, never destroyed

<!-- sq:story:US3:body -->
Acceptance (decisions 5 and 11):
- Load refuses only what the engine cannot build an item without (a core key of the wrong type), naming the file. A declared attribute of the wrong kind never makes an item unreadable.
- `sq check` reports, at error, an attribute whose stored value fails its declared kind and a required attribute that is missing. The value is kept as written; the typed accessor reads it as unset.
- `sq update --set` and `sq import` refuse an invalid value before writing; nothing is written.
- The catalog-only validator `frontmatter_key_undeclared` reports, at warn, an attribute no declaration on the item's type names. It is off by default and silent unless a project selects it; it never rewrites. A test shows a typo is reported when selected and silent otherwise.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an adopter, I want no write to remove an untargeted key

<!-- sq:story:US4:body -->
Acceptance (decision 7): a write removes or changes only the frontmatter keys its command names.
- One table-driven test. Rows are write paths: update of another field, `--set` of another attribute, status, comment, body, sub-entity add and update, `ref add`, retype, type rename, renumber, import, `sq sync` on a role, `sq role set-default`, `sq repair` then a write, and the 0.16 runner.
- Columns are key shapes: declared then removed from an override; never declared (hand-added); declared with a value whose kind no longer matches; carried onto a retype target that does not declare it; named like a `--json`-only key; a nested mapping value; a list; an explicit null.
- Each cell sets up the key, applies the column's change, runs the write path, and asserts the key is in the file with an equal value, in `--json` (except a `--json`-only name, which stays in the file) and in the rebuilt index.
- One control per row targets the key (`--set`, and an import unset) and shows the write does change it, so the table cannot pass on a path that never runs.
- The writer serialises core plus the whole attribute mapping and never consults the spec. The sync sweep removes only the closed named set of retired role keys, re-pointed at top-level names. The skew guard compares round-tripped frontmatter with unknown keys on both sides.
- Falsification: making the writer drop undeclared keys turns the table red for the undeclared and removed-from-override columns.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an operator, I want one meaning per name

<!-- sq:story:US5:body -->
Acceptance (decision 8):
- A skill's `description` is the item's short summary; `extra.description` is folded in, not promoted, and the Claude Code backend reads `description` then `title`. After a description edit the stale copy no longer wins (test).
- `full_name` is stored on no item. Operators fold it into `title`, and every operator surface (CLI, template, card) reads `title`.
- `tech` is one attribute name with a separate declaration on `guide` and on `role`, same kind; nothing shares meaning across types.
- The role catalog's job-title key is untouched.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As an adopter, I want old corpora flattened once, fail-loud

<!-- sq:story:US6:body -->
Acceptance (decision 9): one step of the 0.15 to 0.16 runner, the first to touch frontmatter, with no second schema bump.
- Each `extra` key is lifted to the top level with its value unchanged, declared or not, except: `ref_kinds` folded into inline refs; `severity` to top-level `severity` (top-level wins when both exist); `slug` to `slug`; a skill's `description` dropped when the top-level one is non-empty, otherwise lifted unless equal to the title; an operator's `full_name` dropped, with `title` taking its value when they differ and the file reported; retired role keys dropped.
- The stray top-level `path:` on the nine system skills is removed. `tech` is lifted and kept on roles and guides. The `extra` key is removed.
- Idempotent: a second run changes no file, and a file with no `extra` is left byte-identical.
- Pre-flight refuses before any file is written, naming each file and key, when `extra` is not a mapping, when a lifted key collides with a top-level key holding a different value, or when a roster item's `extra.slug` differs from its file name.
- Runs on a copy of this repository's squad: every item loads, `sq check` is clean, and a census shows no `extra` key left. The legacy readers move under `_migrations/` as a compat reader; the model reads no `extra`, and a hand-pasted `extra:` in a 0.16 file is an unknown key kept like any other.
- Migrated files round-trip: load then write produces the same bytes.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — As a tool author, I want flat --json and a matching canary

<!-- sq:story:US7:body -->
Acceptance (decision 10):
- A generic item row (`list`, `show`, `create`, `mine`) is the core keys without `extra`, plus each stored attribute flat at the top level, plus the keys the command already adds. An unknown key named like an added key stays in the file and is left out of the row.
- `sq workflow --json` type entries gain `attributes`: name to `{kind, required, settable}`. Roster card payloads are unchanged.
- Render contexts expose the flat item and the `extra` variable is gone; the bundled role, skill, operator and review templates read flat keys and render identically for a migrated corpus (golden comparison).
- The VS Code skew canary drops `extra` from `LIST_ROW_KEYS`, asserts the exact core set plus, for every other key, membership in that type's declared attributes, and adds `attributes` to `TYPE_ENTRY_KEYS`. The client reads no `extra`, so no client code changes.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — As an adopter, I want the docs and changelog to say flat

<!-- sq:story:US8:body -->
Acceptance (Consequences section):
- The tech writer refreshes the adopter docs named in the decision: overrides (the `extra` and full-name passages, the `attributes` grammar), roles, internals, migration (a 0.16 upgrade note on the flat frontmatter, the `extra_fields` break, the `--json` row change and the `extra.<key>` to `<key>` template change), adoption, faq, and stability (flat frontmatter and the grammar named as contract).
- One CHANGELOG entry per adopter-visible break, in the unreleased section.
- The dated notes listed in the decision are added to the sixteen earlier decisions it names, each with a related ref back. The five features that describe their keys as `extra.<key>` read as top-level keys.
- Docs and changelog describe the result, with no ticket IDs and no development-process content.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T20:13:59Z] Nina Product:
  - 2026-10-15: drafted from the accepted flat-frontmatter decision. Eight stories; no tasks yet. depends-on FEAT-980 because the flattening is the first frontmatter step of the runner that feature creates; it also follows the 0.16.0 bump (no item to ref) and precedes the corpus-guidance task and the bundled-file task. @manager: the story on the migration is sized as one tech-lead task with subtasks; the invariant table is its own story so it can be reviewed independently.
- [2026-10-15T20:17:51Z] Catherine Manager:
  - For the developer: the dated note on ADR-979 says an operator looked up by title after flattening returns the name full_name held. That holds only if the 0.16 runner flattens before it rewrites comment headers; verify the step order and keep that note true.
<!-- sq:discussion:end -->
