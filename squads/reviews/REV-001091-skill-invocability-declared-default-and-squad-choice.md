---
id: REV-1091
sequence_id: 1091
type: review
title: 'Skill invocability: declared default and squad choice'
status: Approved
author: reviewer
refs:
- TASK-1072
subentities:
- local_id: F1
  title: Generic show/list --json publish the raw stored key, not the resolved pair
  status: WontFix
  severity: low
- local_id: F2
  title: Frozen-runner comments claim no host key, but the 0.11-0.14 runner writes
    it
  status: Fixed
  severity: low
- local_id: F3
  title: 'Stale managed-writer docstring: pointer renders from name and description
    alone'
  status: Fixed
  severity: low
- local_id: F4
  title: Roster write gate does not state the operator_invocable exemption itself
  status: Fixed
  severity: info
- local_id: F5
  title: Upgrade-path test derives its expected system set from the output under test
  status: WontFix
  severity: info
- local_id: F6
  title: Option parser lives among the attribute accessors
  status: WontFix
  severity: info
created_at: '2026-10-17T03:36:50Z'
updated_at: '2026-10-17T03:43:51Z'
---
<!-- sq:body -->
## Scope

The skill-invocability delivery for FEAT-966 (TASK-1072, ST1 to ST6) against ADR-983 and the rulings recorded on the feature: the declared defaults in `_interactions`, the resolver, the pinned `operator_invocable` attribute, `user-invocable: false` in the Claude Code pointer from all three render sites, `--operator-invocable yes|no|default` on `sq skill add` and `update`, the read surfaces, AGENTS.md silence, the upgrade path, the description resolution in `generate_skill_entry`, and the frozen migration runners. ST7 (the real-host preload check) is not in scope.

## Verified

- Defaults: one per always-on skill plus one shared per-type value, all false. The import-time assert closes `OPERATOR_INVOCABLE_DEFAULTS` against `SKILL_DESCRIPTIONS`. The membership test is `is_system_skill`, not the prefix, so an authored `sq-onboarding` resolves invocable (driven).
- Rendering: the managed writer, the item entry and the pure render agree for every combination of default, squad choice and stored value. `sq check` is clean after each set, after `sync`, and after deleting the index and running `repair` (driven). A hand-stored non-boolean resolves as absent and `sq check` reports its kind.
- Option: `Yes`, `false`, empty and `maybe` exit 1 before anything is created. `default` removes the key. Stored values survive `sync` and `repair`. On a system skill the option is accepted alone and refused together with any other option, with the file byte-identical.
- Upgrade path, on a `cp -a` copy of this repo's squad with the dev build and `-C`: `migrate up`, then `check` gives 12 drift warnings at exit 0, then `sync`, then `check` is clean. No `operator_invocable` key is stamped anywhere.
- `generate_skill_entry`: a system skill now takes the bundled description, matching the managed writer. A project skill still takes its own description after `update --desc` (driven).
- Targeted tests: the new modules, the migrated-corpus goldens and the skill-show golden pass (199 passed, 1 skipped).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1091 add-finding "…" --severity medium`; track with `sq review 1091 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Generic show/list --json publish the raw stored key, not the resolved pair

<!-- sq:finding:F1:body -->
ADR-983 clause 5: every `--json` surface that publishes a skill's own fields carries `operator_invocable` (resolved) and `operator_invocable_set`, on every row. ST4 asked the handoff to list any such surface beyond `sq skill <addr> show`; it lists none.

Driven in a scratch squad (dev build, fresh `sq init`):

- `sq list -t skill --json`: the key is absent on every skill with nothing stored (`squads`, every `sq-<type>`), and present only where a value is stored.
- `sq show SKILL-21 --json`, with a hand-stored `operator_invocable: "no"`, prints `"operator_invocable": "no"`. `sq skill mine show --json` on the same skill prints `true` / `false` (resolved as absent, which is right).

So one key name means "resolved boolean" on one surface and "raw stored value, maybe missing, maybe a string" on two others. A consumer who reads the generic surfaces gets a value that disagrees with the resolver.

Decide one of these: publish the resolved pair on the generic skill rows as well, or record on ADR-983 that clause 5 covers only `sq skill <addr> show --json` and that generic rows carry raw attributes.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-17T03:38:44Z] `manager` Catherine Manager:
  - Generic item rows (show/list --json) carry stored attributes, as pronouns already do; the resolved pair is on the skill surfaces. ADR-983 clause 5 to be narrowed by a dated architect note.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Frozen-runner comments claim no host key, but the 0.11-0.14 runner writes it

<!-- sq:finding:F2:body -->
`_v0_4_to_v0_5.py` and `_v0_8_to_v0_10.py` pass `invocable=True` with the comment "a frozen runner writes no host key; `sq sync` adds it". The dev's gate comment on TASK-1072 says the same. As a general claim this is false.

`_v0_11_to_v0_14.py` (`_regenerate_surface`, line ~232, and the seeding loop at ~298) calls the live `write_managed` and `generate_skill_entry`. Those now write `user-invocable: false`. So any corpus older than 0.14 gets the host line during `sq migrate up`. The regenerated golden `tests/goldens/migrated_corpus/_shared/.claude/skills/squads/SKILL.md` (shared by v0_1, v0_4, v0_8 and v0_11) shows it: the line comes from migrate, not from sync. A 0.14 or 0.15 corpus gets no line until `sq sync`, which I confirmed on a copy of the real squad.

The behaviour is acceptable. Pointers are generated, the line is the resolved default, and no `operator_invocable` frontmatter key is stamped (checked: no skill file or index row carries it after migrate and sync). The fix is the prose. Either drop the inline comments or reword them to say what the call does, for example "renders the pointer as an invocable skill, with no host key". Correct the claim on the task too.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Stale managed-writer docstring: pointer renders from name and description alone

<!-- sq:finding:F3:body -->
`_backends/_claude_code/_backend.py`, the `_write_managed_skill` docstring still ends: "the pointer never needed either shape: ``claude/pointer_skill.md.j2`` renders from *name* and *description* alone."

The template now also takes `invocable`, and this writer receives it as a required keyword. Reword it to name the three inputs (name, description, resolved invocability), or cut the clause. `_render_skill_pointer` already documents the shared render.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Roster write gate does not state the operator_invocable exemption itself

<!-- sq:finding:F4:body -->
The gate decision is sound. `--operator-invocable` has its own service parameter. `parse_invocable_choice` admits only `yes`/`no`/`default`, and `_apply_operator_invocable` sets or pops one key, so the option cannot write any other field. `--set`/`--unset operator_invocable` is refused by `settable = false`. Neither `sq skill <addr> update` nor create exposes `--set`, and the importer goes through `require_settable`. That matches TASK-1069's rule: the value is the squad's choice, not content that config supplies.

The weak spot is that `_gate_roster_update` does not state this exemption. Its docstring says the attributes the bundled spec declares count as supplied, and `operator_invocable` is now one of them, so it sits in `supplied`. The exemption holds only because the dedicated parameter never reaches `touched`. Pronouns get an explicit `supplied.discard(AttributeKey.PRONOUNS)` with a one-line reason. Add the same discard for `OPERATOR_INVOCABLE`, so the gate states the rule itself and a later refactor that routes the option through `set_attributes` does not start refusing it on system skills.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Upgrade-path test derives its expected system set from the output under test

<!-- sq:finding:F5:body -->
`tests/integration/test_an_upgraded_squad_receives_the_host_key_through_sync_alone.py` builds its expected set from the output under test (`system = [p for p in pointers if LINE in ...]`) and then checks only `len(system) > len(authored)`, a floor of 3. If a system skill lost its line on all three sites, it would drop out of `system` and the test would stay green. The render-site table does catch that case, because it compares against `SHAPES`, so nothing is uncovered today. This test is weaker than it reads, though. It also simulates the earlier release by stripping the line from a current squad. It does not migrate a 0.15 corpus, which the ST6 approach named.

Suggested fix: assert `{p.parent.name for p in system} == set(SYSTEM_SLUGS)` (the slugs `_invocable_squad` already exports).

Independent check of the real path (dev build, `-C`, a `cp -a` copy of this repo's squad): `migrate up` -> `check` gives 12 "managed pointer had drifted" warnings, one per system skill pointer, none for `releasing-squads` or `launch-dev-host`, exit 0 -> `sync` -> `check` clean. The 12 pointers gain exactly the one line.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Option parser lives among the attribute accessors

<!-- sq:finding:F6:body -->
`_models/_attributes.py` now holds `INVOCABLE_CHOICES` and `parse_invocable_choice`, which parse CLI option text and raise an error that names the `--operator-invocable` flag. The rest of that module is typed attribute accessors. The parallel option, pronouns, keeps its rule in its own module (`squads._pronouns.checked_pronouns`). This is a cohesion cleanup only: the import edge (`_models` -> `_errors`) is allowed, and behaviour is correct. Consider moving the parser beside the CLI option or into a small module of its own.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T03:38:06Z] `reviewer` Paul Reviewer:
  - Reviewed fd482453 (the TASK-1072 delivery, identical to the uncommitted diff I started on). 6 findings: 3 low (F1 generic --json surfaces carry the raw stored key; F2 frozen-runner comments are false for the 0.11-0.14 runner; F3 stale managed-writer docstring), 3 info (F4 gate exemption not stated in the gate; F5 upgrade test self-derives its expected set; F6 parser placement). No correctness defect in the resolver, the render sites, the option or the upgrade path. Recommended verdict: approve once F1-F3 have a disposition. @tech-lead @manager
- [2026-10-17T03:43:30Z] `manager` Catherine Manager:
  - Approved: no correctness defects; F2-F4 fixed, F1/F5/F6 dispositioned; full suite 13739 passed, 0 failed.
<!-- sq:discussion:end -->
