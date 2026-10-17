---
id: REV-1047
sequence_id: 1047
type: review
title: 'Docs audit: cross-doc consistency'
status: Approved
author: reviewer
refs:
- REV-1032
- REV-1033
- REV-1034
- REV-1035
- REV-1036
description: Cross-file consistency of the five parallel docs-audit fixes, checked
  against each other and the release/0.16 dev build.
subentities:
- local_id: F1
  title: roles.md says a role item stores only its slug; the name is stored
  status: Fixed
  severity: low
- local_id: F2
  title: overrides layout presents head/summary templates as live presentation
  status: Fixed
  severity: medium
- local_id: F3
  title: stability stamp rules cover workflow only; overrides adds templates, roles.toml
  status: Fixed
  severity: medium
- local_id: F4
  title: 'Non-abstract backend methods: three in backends.md, two in stability'
  status: Fixed
  severity: low
- local_id: F5
  title: roles.toml full_name does not rename an active role despite stated precedence
  status: WontFix
  severity: medium
- local_id: F6
  title: tutorial says every item is authored by a role; operators author too
  status: Fixed
  severity: low
- local_id: F7
  title: 'Role definition: rendered on read vs stored under squads/'
  status: Fixed
  severity: medium
- local_id: F8
  title: 'Prose role body: faq says show prints it; it does not, and sq check errors'
  status: Fixed
  severity: medium
created_at: '2026-10-16T11:15:14Z'
updated_at: '2026-10-16T11:26:21Z'
---
<!-- sq:body -->
## Scope

The seams between the five docs-audit fixes (the uncommitted diff to `README.md`, `docs/`, `clients/vscode/README.md` and `clients/vscode/MARKETPLACE.md`): topics more than one file touches, checked against each other and against the release/0.16 dev build in a scratch squad (`sq init --roles all`, then `sq dev add`, `sq operator add`, records, overrides and `sq repair` driven there).

## What agrees

- **`sq repair` on role and skill bodies** (faq, adoption, internals): all three say an empty role or generated-skill body gets its view tag back, a body with prose is left alone, and a user-added skill is never touched. Driven: an emptied role and an emptied `greeting` skill got their tags back, a role with prose and an empty user skill were left as they were.
- **Records in `sq inbox` and `sq list`** (workflow, overrides, README): an open record shows in the inbox, drops out once Published or Accepted, stays in `sq list` while Published or Accepted, and is hidden once Rejected. Driven.
- **`--author`, `--as`, `--assignee` with `op-<slug>`** (faq, workflow, adoption, tutorial): all accept role, `<tech>-dev` and `op-<slug>` slugs. The unknown-slug message and exit 1, and the missing `--author` exit 2, match the faq word for word. Driven.
- **Twelve item types, prefixes, aliases, folders and lifecycles** (README, docs/README, internals, workflow) match `sq workflow types --json`, `sq workflow lifecycles --json` and the bundled aliases.
- **Preloaded skills per role** (README, roles, agents) match the generated `.claude/agents/*.md` for all eight roles and a `python-dev`. The tutorial's claim that IDs 1 to 20 are used by roles and skills holds.
- **Unselected checks**: overrides says eleven in all four places, and the catalog confirms it (24 validators, 13 selected by the core, a category bundle or a bundled type). workflow and stability give no count, so nothing contradicts it.
- **The three spec override documents**: stability and overrides agree on the layout, the shared grammar, and on `[selected]` being refused in the playbook (driven).
- **Hygiene**: no process narration, ticket IDs, repo or dev-process content, or status prose in the added lines. Every anchor in README and docs resolves.

## Findings

Eight findings, F1 to F8, each with both sides, what is true (driven or read), and a fix. F5 may be a code bug rather than a docs defect.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1047 add-finding "…" --severity medium`; track with `sq review 1047 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — roles.md says a role item stores only its slug; the name is stored

<!-- sq:finding:F1:body -->
**One side:** `docs/roles.md:259-261` says "A role item stores only its slug (and a developer's model and tech); the rest of its definition is resolved from the catalog and your overrides."

**Other side:** `docs/overrides.md:2082` says "The chosen name is stored as the ROLE item's `title`." `docs/overrides.md` § "Which name wins" (2092-2110) also depends on a stored name, which `sq sync` keeps over the bundled one.

**Truth** (driven): the role file stores `title` (the full name) and `description` in frontmatter, next to `extra.slug`. A per-slug `full_name` override rewrites the stored `title` on `sq sync`, and the name stays after the override is deleted.

**Fix:** in roles.md, say "A role item stores its slug and name (and a developer's model and tech); the rest of its definition is resolved from the catalog and your overrides."
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T11:20:11Z] Theo Writer:
  - Fixed in docs/roles.md (How roles, skills, and items connect): a role item stores its slug and name.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — overrides layout presents head/summary templates as live presentation

<!-- sq:finding:F2:body -->
**One side:** `docs/overrides.md:64-65`, in the override layout tree, describe `subentities/head.md.j2` as "the badge line at the top of a block" and `summary.md.j2` as "the roll-up table". A reader takes this to mean overriding them changes what `show` prints.

**Other side:** `docs/internals.md:407-408` says "`head` and `summary` are kept for migrations, which still read and write the retired presentation regions". `docs/internals.md:234-237` says the badge line and roll-up are computed by `show`.

**Truth** (driven): I scaffolded both overrides, added a probe line to each, and added a story. The probe text did not appear in `show --full`, in `show --raw`, or in the item file. In the source, `set_head`/`ensure_summary` (the only users of those templates) are called only from `_migrations/_v0_1_to_v0_2.py` and `_v0_2_to_v0_3.py`. internals is right.

**Fix:** change the two overrides.md comments to say these are used only by migrations, and that overriding them does not change `show` output. Or leave them out of the layout tree.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T11:20:22Z] Theo Writer:
  - Fixed in docs/overrides.md (override layout tree): head.md.j2 and summary.md.j2 are marked as used only by migrations, with no effect on show.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — stability stamp rules cover workflow only; overrides adds templates, roles.toml

<!-- sq:finding:F3:body -->
**One side:** `docs/overrides.md:279-282` says a `roles.toml` that changes a bundled role, bundle or `[dev]` must carry the stamp, or `sq check` reports an error. `docs/overrides.md:1723-1731` says a template override with no stamp is an error.

**Other side:** the frozen-contract bullet `docs/stability.md:197-205` (Staleness & drift) names the stamp only "in a role or workflow override". It gives the stamp-required rule only for "a workflow override that shadows a built-in", and says nothing of `roles.toml`, `playbook.toml` or an unstamped template. Its own layout bullet, edited in this same diff (stability.md:150-156), now names all three spec documents.

**Truth** (driven): an unstamped template override gives `error … override has no squads:override-base stamp`. An unstamped shadowing `roles.toml` gives `error .overrides/roles.toml: shadowing role catalog override has no squads:override-base stamp`. An unstamped shadowing `playbook.toml` gives the matching playbook error.

**Fix:** widen the stability bullet. The stamp is a TOML comment in any of the three spec documents and in per-role files. A template override must always carry it. A spec document that shadows a bundled entry must carry it. An add-only one needs none.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T11:20:24Z] Theo Writer:
  - Fixed in docs/stability.md (Staleness & drift bullet): stamp format covers per-role files and all three spec documents; templates always need it, shadowing per-role files and spec documents need it, add-only ones do not. Driven: unstamped roles.toml shadow and per-role file error, a new-role per-slug file is clean.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Non-abstract backend methods: three in backends.md, two in stability

<!-- sq:finding:F4:body -->
**One side:** `docs/backends.md:48-66`: "Three more methods are non-abstract". It lists `managed_entry_paths`, `restriction_fragment` and `render_role_entry`/`render_skill_entry` (four method names in three bullets).

**Other side:** `docs/stability.md:721-727`: "Two more methods are non-abstract … `restriction_fragment` and `render_role_entry`/`render_skill_entry`". It mentions `managed_entry_paths` only in passing.

**Truth** (read, `src/squads/_backends/_base.py:263-341`): four non-abstract methods have defaults: `managed_entry_paths`, `restriction_fragment`, `render_role_entry`, `render_skill_entry`.

**Fix:** use one count and one list in both files. The simplest is to name all four and drop the number, or to say "four" in both.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T11:20:27Z] Theo Writer:
  - Fixed in docs/backends.md and docs/stability.md: both now say four non-abstract methods and name managed_entry_paths, restriction_fragment, render_role_entry, render_skill_entry (counted in AgentBackend: 7 abstract, 4 with defaults).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — roles.toml full_name does not rename an active role despite stated precedence

<!-- sq:finding:F5:body -->
**One side:** `docs/overrides.md:257-259`: "Precedence, lowest to highest: the bundled catalog, then `roles.toml`, then a per-slug `.overrides/roles/<slug>.toml`. When both override files set the same field for one role, the per-slug file wins." The frozen `docs/stability.md:158-159` says the same: "a role resolves bundled, then `roles.toml`, then its per-slug file, merging field-wise". Both say `roles.toml` fields merge into the role.

**Other side:** `docs/overrides.md` § "Which name wins" (line 2100) lists only the per-slug `full_name` as renaming a role.

**Truth** (driven): a stamped `roles.toml` with `[[roles]] slug = "architect"`, `full_name = "Rita Catalog"`, followed by `sq sync`, changes `sq role catalog` to "Rita Catalog". The active ROLE item's title, and `sq role architect show`, still say "Robert Architect", and `sq check` is clean. The same `full_name` in `.overrides/roles/architect.toml` does rename the role on sync. For `full_name` on an active role, the field-wise precedence does not hold.

**Fix:** either make `roles.toml` `full_name` rename an active role the way the per-slug file does (a code change, so this would need a bug), or say in both overrides.md (the roles.toml section and "Which name wins") and stability.md that only a per-slug `full_name` renames an active role, and that a `roles.toml` name reaches only the catalog and future activations.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T11:19:17Z] Mara Tester:
  - F5 reproduced with the dev build and filed as BUG-1049. Only full_name is affected (title and mission from roles.toml do reach an active role); a newly activated role gets the roles.toml name. Cause is role_base_from_item keeping the stored title; ADR-777 section 3 states no full_name carve-out.
- [2026-10-16T11:25:49Z] Catherine Manager:
  - Home: BUG-1049 (roles.toml full_name ignored for an active role). The three passages to re-check once it is fixed are listed in the writer's REV-1047 comment.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — tutorial says every item is authored by a role; operators author too

<!-- sq:finding:F6:body -->
**One side:** `docs/tutorial.md:32` says "Every item is authored by a role: `--author` is required on every `sq create`, and takes a registered slug (`sq role list` shows them)."

**Other side:** `docs/workflow.md:55` says "must name a registered role or operator", and workflow.md:75 shows `sq create task … --author op-alice`. `docs/adoption.md:16-17` says "the slug of a registered role (or `op-<slug>` for a human operator)". `docs/faq.md:29-31` says "a human authors with `--author op-<slug>`".

**Truth** (driven): `sq create guide G1 --author op-alice` succeeds.

**Fix:** in the tutorial, write "Every item has an author: `--author` … takes a registered slug, a role (`sq role list` shows them) or `op-<slug>` for a human operator."
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T11:20:29Z] Theo Writer:
  - Fixed in docs/tutorial.md: every item has an author, a role slug or op-<slug> for a human operator. Driven: sq create epic --author op-alice succeeds.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Role definition: rendered on read vs stored under squads/

<!-- sq:finding:F7:body -->
**One side** (repair edits plus `roles.md`): `docs/faq.md:96-99`, `docs/adoption.md:200-204` and `docs/internals.md:140-142` say a role's definition renders fresh from the catalog and your overrides. `docs/roles.md:259-261` says the same and adds that the role item stores the rest nowhere.

**Other side** (lines left as they were): `docs/README.md:66` and `docs/internals.md:336` say "(definition stored under squads/)". `docs/internals.md:65` says "ROLE-*.md (real role definitions)". `docs/internals.md:346` says "The real role definition lives under the squad folder". `docs/backends.md:137` says "ClaudeCodeBackend writes a role's real definition to `squads/agents/roles/ROLE-*.md`". `docs/overrides.md:2086` lists "The rendered **role body** in `squads/agents/roles/ROLE-*.md`".

**Truth** (driven, fresh `sq init`): `ROLE-000002-architect.md` holds frontmatter (title, description, `extra.slug`) and a body that is only the `sq:view:role_definition` view tag. `sq role architect show` renders the definition on read.

**Fix:** reword the six lines to say the role file holds the role's identity and a view tag, and that `sq role <slug> show` renders the definition. For the two diagram labels, use "(definition rendered on read)", as the skill line beside them already does. Drop the overrides.md:2086 bullet, or say the name appears in `sq role <slug> show`.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T11:20:31Z] Theo Writer:
  - Fixed in docs/README.md and docs/internals.md diagrams (definition rendered on read), docs/internals.md folder tree and role-pointer bullet, docs/backends.md (pointers, not copies), and docs/overrides.md (the role body bullet now names the sq role show heading).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Prose role body: faq says show prints it; it does not, and sq check errors

<!-- sq:finding:F8:body -->
**One side:** `docs/faq.md:96-99` says "A role or skill body that holds prose is left alone, and `show` prints that prose." `docs/adoption.md:207-209` and `docs/internals.md:140-142` say only that it is left alone.

**Other side:** none of the three says what `sq check` then does. The repair section of adoption.md promises one `sq repair` and a clean import.

**Truth** (driven): a role whose body holds prose in place of the view tag is left alone by `sq repair`. `sq role <slug> show` still renders the catalog definition, not the prose. `sq check` reports `error ROLE-…: missing seeded view tag sq:view:role_definition — the body already carries prose; the remedy …` (a four-step recipe) and exits 3. So the faq clause "`show` prints that prose" is false for a role, and none of the three pages warns about the check error.

**Fix:** in faq.md, drop "and `show` prints that prose". In faq.md and adoption.md, add one sentence: such a body fails `sq check` with a missing-view-tag error, which names its remedy.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T11:20:33Z] Theo Writer:
  - Fixed in docs/faq.md and docs/adoption.md. Re-driven: a role or generated-skill body holding prose is left alone by sq repair, show prints that prose in place of the definition, and sq check errors (missing seeded view tag, exit 3) with a remedy. The faq clause about show was true and is kept; the check error is added to both.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:25:13Z] Theo Writer:
  - Fixed F1, F2, F3, F4, F6, F7, F8 in docs/roles.md, overrides.md, stability.md, backends.md, tutorial.md, README.md, internals.md, faq.md, adoption.md. Each finding has its own comment naming where.
  - F5 left Open pending the roles.toml full_name bug. Passages it affects: overrides.md roles.toml Precedence paragraph and Which name wins; stability.md Project-level overrides Precedence bullet.
  - F8 re-driven: show prints the prose in place of the definition (role and skill), not the catalog definition; sq check errors with exit 3. Docs describe that.
  - @manager ready for your pass.
- [2026-10-16T11:26:20Z] Catherine Manager:
  - Approved: every finding Fixed (re-run by the writer on the dev build) or closed with a home; cross-doc seams checked in REV-1047.
<!-- sq:discussion:end -->
