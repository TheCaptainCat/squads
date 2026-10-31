---
id: TASK-1126
sequence_id: 1126
type: task
title: Name every sq check finding by a registered rule
status: Done
parent: FEAT-1092
author: tech-lead
refs:
- REV-956:addresses
- TASK-1125:depends-on
- TASK-1124:depends-on
- TASK-1077:depends-on
- TASK-1104:depends-on
description: 'REV-956 F11: additive rule key in sq check --json, a rule registry,
  a guard, and adopter docs on binding rules.'
subentities:
- local_id: ST1
  title: Add the rule field, registry and guard; emit rule in --json
  status: Done
  assignee: python-dev
  maps_to: US4
- local_id: ST2
  title: Document the binding check rules for adopters
  status: Done
  assignee: tech-writer
  maps_to: US4
created_at: '2026-10-24T21:53:55Z'
updated_at: '2026-10-28T12:46:05Z'
priority: medium
---
<!-- sq:body -->
## Goal

Every `sq check` finding names the rule that produced it, and adopters can see which findings are binding. Finding F11. This is the one adopter-visible change in FEAT-1092: an additive `rule` key on each finding in `sq check --json`, which stays within the additive-only promise for `--json` shapes in `docs/stability.md`. Human output is unchanged.

## Re-measured on 2026-10-24 (working tree, read)

- `CheckIssue` is still `level`, `item`, `message` (`src/squads/_services/_results.py:145`).
- 72 `CheckIssue(` constructions: 54 in `_services/_validators.py`, 14 in `_services/_maintenance.py`, 3 in `_cli/_main.py` and 1 in `_workflow/_models.py`.
- `check` still matches a finding by message text: `message.startswith("on disk but not in index")` (`_services/_maintenance.py:3207`).
- The eight sources REV-956 F11 lists stand: the raw-text scan, the per-file load boundary, override checks, orphaned skills, duplicate ids, the per-item catalog, the squad-global catalog, and confirmed cross-source candidates, plus the three config-load findings `_cli/_main.py` adds.

## Approach

1. Add a `rule: str` field to `CheckIssue`. Add a registry module beside the check mixin, for example `src/squads/_services/_check_rules.py`, that names every non-catalog rule with its source and whether it is binding (always on) or selectable. A catalog finding's rule is the validator's own declared name, so the spec stays its single source and the registry holds no copy.
2. Every construction passes a rule. `check` matches on the rule, never on message text.
3. `sq check --json` emits `rule` on every finding.
4. Rewrite the two docstrings that describe the two kinds of finding in the plain terms TASK-1077 sets ("file checks", "the validator catalog"). Drop "pre-parse" and state the rule the file checks actually satisfy: per file, not selectable, and still reported when the frontmatter cannot be read.
5. Adopter docs (ST2, tech writer): a paragraph listing the binding rules and saying that they cannot be deselected and why, beside where `docs/overrides.md` documents the selectable validators. Note the new key in `docs/stability.md`'s `--json` section if it enumerates keys.

## Tests

- **`tests/meta` guard:** every `CheckIssue(` construction under `src/` passes a `rule` that is registered or is a declared validator name (AST scan), with a liveness row that plants an unregistered rule and sees it fail. This is the one place the rule is encoded. No per-finding test asserts its own rule name.
- **One table, "rule reaches `--json`"**, with one row per source (eight sources plus the config-load path), because each source is its own code path. Each row checks that a planted defect's finding carries the expected rule in `sq check --json`. No level-by-type cross product.
- **Goldens:** the `sq check --json` goldens gain the key. Regenerate them and review the diff to confirm it adds only `rule`.
- Falsify: drop `rule` from one source and see its row and the guard go red.

## Generated output

No generated agent file changes. The `sq check --json` shape gains one key.

## CHANGELOG substance (the writer authors the entry)

Added: every finding in `sq check --json` carries a `rule` naming the check that produced it. The docs now list the findings that are always on and cannot be deselected, and why. Tools reading `--json` can match findings by rule instead of by message text.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1126 add-subtask "<title>"`; track with `sq task 1126 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add the rule field, registry and guard; emit rule in --json

<!-- sq:subtask:ST1:body -->
Add `rule` to `CheckIssue` and a rule registry beside the check mixin, with catalog findings named by their declared validator. Name all 72 constructions, match on the rule instead of message text in `check`, and emit `rule` in `sq check --json`. Rewrite the two finding-kind docstrings in TASK-1077's plain terms, without "pre-parse". Add the meta guard, the per-source table, and the regenerated goldens.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Document the binding check rules for adopters

<!-- sq:subtask:ST2:body -->
Document for adopters which `sq check` findings are always on and cannot be deselected, and why, beside the selectable validators in `docs/overrides.md`. Note the additive `rule` key where `docs/stability.md` describes `--json` shapes. Write the CHANGELOG entry from the developer's handoff.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T20:04:09Z] `python-dev` Elias Python:
  - ST1 done. Every `sq check --json` finding now carries `rule`; human output is unchanged.
    
    **Mechanics.** `CheckIssue.rule` is a required fourth field. Catalog findings carry their validator's declared name (no copy). Non-catalog rules are in `_services/_check_rules.py` (`BINDING_RULES`, rule -> source; `is_registered`, `is_binding`). `check` drops the "on disk but not in index" finding of a duplicated id by `rule == "index_reconciled"`, no longer by message text. Override findings (still tuples from the overrides service) are stamped `overrides_sound` in `check`.
    
    **Binding rules (always on, cannot be selected or deselected), by source:**
    - raw-text scan: `markers_balanced`, `view_target_resolves`, `view_tag_in_region` (warn), `seeded_view_resolves`, `body_regions_present`
    - file load: `file_readable`, `frontmatter_parses`, `id_present`, `id_well_formed`, `fields_valid`, `timestamps_present` (warn)
    - override checks: `overrides_sound` (template, role, workflow, playbook and roles-catalog override files; error or warn)
    - orphaned skills: `skill_type_declared` (warn)
    - duplicate ids: `ids_unique`, `numbers_unique`
    - cross-source: `frontmatter_matches_index` (warn)
    - config load (reported by `sq check` itself when a config will not load): `playbook_loads`, `workflow_loads`, `corpus_scans`
    - squad-global catalog members that run in every squad (`ALWAYS_ON_SQUAD_GLOBAL_NAMES`): `index_reconciled`, `backend_reconciled`, `roster_config_integrity`, `default_designation_duplicated`, `roster_slug_valid`, `playbook_guide_role_live`, `display_config_valid`, `working_language_valid`, `view_transform_resolves`
    
    **Selectable:** every per-item catalog member (`VALIDATOR_NAMES`, chosen per type through its `validators` list, common core and category bundle) and the squad-global members in `SELECTABLE_SQUAD_GLOBAL_NAMES` (`type_has_live_author`, `children_settled_with_parent`, `dependency_acyclic`, `wip_limit`, `unassigned_active`, `stale_active`). Their rule is the name already documented in `docs/overrides.md`.
    
    **Why binding (for the docs):** marker integrity is what marker-safe editing depends on; an unresolvable view tag, a missing body region, a duplicate id or an unreadable file is corrupt content, not policy; the config-load rules report that the configuration itself cannot be read, so nothing could select them. Per file, not selectable, and still reported when the frontmatter cannot be read is the rule the raw-text and file-load checks satisfy.
    
    **Tests.** `tests/meta/test_every_check_finding_names_a_registered_rule.py` (AST guard over every `CheckIssue(` under `src`, a rule inside a catalog member's function must be that member's name, liveness rows, every binding rule constructed somewhere); `tests/cli/test_check_json_names_the_rule_of_each_source.py` (11 rows, one per source); `BINDING_RULES` allowlisted in the mutable-state guard; `check_squad.json` golden regenerated, diff adds only `rule`. Falsified: renaming one rule in the duplicate-ids source turned its row and the guard red. Both finding-kind docstrings (`_validators.py` module, `_scan_for_check`) rewritten without "pre-parse".
    
    **Gates.** pyright, ruff check and ruff format clean; pytest tests/meta, service, unit, cli, integration, tui all pass (never the full single run). `sq check` clean.
    
    ST2 for @tech-writer: docs/overrides.md paragraph (binding vs selectable, list above), docs/stability.md `--json` note (additive `rule` key), and the CHANGELOG entry.
- [2026-10-25T20:15:48Z] `tech-writer` Theo Writer:
  - ST2 done.
    - `docs/overrides.md`: new section "Checks outside every list: files, ids, overrides and configuration", right after "Squad-wide checks". Three tables (file checks, squad checks, config checks) list every rule in `BINDING_RULES`, each with what it reports, its level and why it cannot be turned off; the nine always-on squad-wide validators are pointed back to the existing table. A closing paragraph says every `--json` finding carries `rule` and that tools match by rule, not message.
    - `docs/stability.md`: unchanged. Tier 3 lists `check` among frozen commands but enumerates no `check` keys, so there is nothing to add the key to.
    - `CHANGELOG.md` 0.17.0 Added: one entry, last in the section.
    - Example: real `sq check --json` from the dev build on a scratch squad (unclosed `sq:discussion` marker, a copied feature file, a ref to a missing task) giving `markers_balanced`, `ids_unique`, `dangling_ref`; ids swapped for placeholders, which the ticket-ref guard requires. Also ran a broken workflow override (`overrides_sound`, `workflow_loads`) and a missing `updated_at` (`timestamps_present`). Scratch squad deleted.
    - Rule names cross-checked with `is_registered`: all registered, every binding rule documented. Doc guards pass (23).
    - @python-dev, two things I saw: `timestamps_present` comes out as `"level": "warning"`, while every other finding says `warn` (human output too). And `workflow_loads` for an unknown validator name printed `Invalid workflow spec: (<path>)` with no cause. I documented the level as `warn`.
- [2026-10-25T20:35:17Z] `python-dev` Elias Python:
  - Correction to the ST1 handoff, for @tech-writer (REV-1150 F4, F6):
    
    - The per-item common core (`item_status_valid`, `dangling_ref`, `ref_kind_valid`, `agent_registered`, `parent_acyclic`, `attribute_valid`) and each category bundle's members are always on for a type of that category: a type's `validators` list extends them and can only change their level, never drop them. Only the members a type adds beyond them are selectable. Squad-global: the always-on set is binding, the six in `SELECTABLE_SQUAD_GLOBAL_NAMES` are selectable.
    - `overrides_sound` no longer exists. Override findings use `override_stamped` (error: a shadowing override with no stamp), `override_current` (warn: drifted from the bundled base) and `override_loads` (error: unreadable, missing required markers, or does not load). An out-of-region view tag in a template override is `view_tag_in_region`.
    - `timestamps_present` is level warn. `workflow_loads` now names the cause (for example an unknown validator name).
    - `sq import --json` issues carry `rule` as well.
- [2026-10-25T21:16:00Z] `tech-writer` Theo Writer:
  - Docs updated for the REV-1150 changes, `docs/overrides.md` "Checks outside every list" and `CHANGELOG.md` only:
    - The `overrides_sound` row is now three rows: `override_stamped` (error), `override_current` (warn) and `override_loads` (error). A note says a workflow or playbook override that will not load reports `workflow_loads`/`playbook_loads`, with a real quoted `workflow_loads` finding for an unknown validator, cause included.
    - New paragraph from e44b241: the common core and each category bundle, every name listed from `COMMON_CORE`/`CATEGORY_BUNDLES`, are always on, and a type's list can change their level within the floor but never drop them. Only additions are selectable.
    - CHANGELOG line: adds `sq import --json` issues carrying `rule`, and the always-on validators to the docs summary.
    - Driven on a scratch squad with the dev build, now deleted: `override_stamped`, `override_loads` (role and roles catalog), `override_current` (a template stamped 0.10.0), `workflow_loads`, `playbook_loads`, `dangling_ref@error` on task (exit 3), and `sq import --json` issues with `rule`. Every rule name in the section passes `is_registered`, and every `BINDING_RULES` entry is documented. Doc guards: 23 passed.
- [2026-10-25T21:16:19Z] `manager` Catherine Manager:
  - Done: ST1 in 61b1f474, 12ce57b2, 3e7c5a83 (REV-1150 Approved); ST2 docs in ab6cfbfa and this commit.
<!-- sq:discussion:end -->
