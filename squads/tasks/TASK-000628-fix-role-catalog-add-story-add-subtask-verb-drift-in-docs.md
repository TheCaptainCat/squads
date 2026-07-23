---
id: TASK-628
sequence_id: 628
type: task
title: Fix role-catalog/add-story/add-subtask verb drift in docs
status: Done
parent: FEAT-574
author: tech-lead
description: 'US1: correct non-existent verbs in roles/recipes/agents/adoption/tutorial
  docs (after 575)'
created_at: '2026-07-23T08:03:50Z'
updated_at: '2026-07-23T09:50:15Z'
---
<!-- sq:body -->
Implements FEAT-574 **US1**. Correct the CLI-verb drift in the shipped docs so every
documented invocation names a verb that actually resolves. Doc correction only — the
verbs themselves are added by FEAT-575.

**Build order:** runs **after** FEAT-575 lands. `sq role list` and `sq operator list`
only become real verbs there; the doc fixes below point at them.

## Fixes

- `docs/roles.md` (lines ~55-56): `sq role list` and `sq role list --available`.
  After FEAT-575, `sq role list` is a real verb for the **active roster** — keep that
  line, it is now correct. `sq role list --available` (the bundled catalog) has no
  such flag; replace it with `sq role catalog`.
- `docs/recipes.md`, `docs/agents.md`: any `sq role list --available` / non-existent
  role-listing invocation → `sq role catalog` for the bundled catalog, `sq role list`
  for the active roster.
- `docs/adoption.md` (lines ~57-58): `story add FEAT-7 "…"` → `sq feature 7 add-story
  "…"`; `subtask add TASK-8 "…"` → `sq task 8 add-subtask "…"`.
- `docs/tutorial.md` (line ~66): the `story add`/`subtask add` prose → the real
  `add-story` / `add-subtask` verbs on the addressed item.

## Constraints

- These are **adopter-facing** docs: describe the tool for adopters — no sq item /
  ticket / GitHub references, and no repo/dev-process content (CI, dogfood, packaging,
  test internals).
- Verify every `sq …` invocation you write resolves against the current CLI (the
  FEAT-574 US4 drift-guard test will enforce this mechanically once it lands).

## Conventions (apply to every deliverable)

- No status/lifecycle prose in any body/doc (frontmatter `status:` is the single
  source of truth). The category term is **roster**, never "meta".
- No ticket IDs in source or test names — name by behaviour; keep the pointer in the
  sq ref/comment. Use PEP-695 `type X = …` for any alias. User-facing errors are the
  `SquadsError` family. Escape console output via `_cli._common.e()`.
- If you add any module-level constant, run `tests/meta` in your gate (the
  mutable-state guard has tripped repeatedly). Run all gates with `uv run --all-extras`
  (pyright/ruff/pytest) — a bare `uv run` prunes the `tui` extra and floods false
  errors.
- Set sq bodies via the CLI only; if you use `--file`, verify `grep -c '</\?content>'`
  == 0 on the written body. Run `uv run sq check` clean before handing off.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 628 add-subtask "<title>"`; track with `sq task 628 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T09:28:30Z] Elias Python:
  - Fixed CLI-verb drift across docs/roles.md, recipes.md, agents.md, adoption.md, tutorial.md, workflow.md, faq.md, internals.md, migration.md, stability.md, backends.md, overrides.md.
  - role list --available -> role catalog; story add/subtask add -> add-story/add-subtask; every bare sq body/comment/update/status/ref-add mention -> the addressed sq <type> <n> <verb> form.
  - Deeper bugs the same sweep turned up and fixed: sq role show <slug> / sq role regen|rm <id> had the address/verb word order backwards (real grammar is sq role <addr> show|regen|rm, confirmed against stability.md's own item-first spec and live CLI); same for sq operator rm; sq dev add <tech> needs --tech, not positional; sq override diff/update take one NAME, not several; sq create <type> has no --status flag; sq role update doesn't exist (there's no in-place rename verb -- pointed at the existing role-TOML-override + sq sync path instead); every vim .overrides/... path was missing the squads/ prefix (the real squad-dir-relative location) across overrides.md and roles.md; backends.md's AgentBackend ABC sample was stale (generate_role_pointer/generate_skill_pointer -> generate_role_entry/generate_skill_entry, missing managed_paths, non-async, missing the operators param, default_backend -> active_backends).
  - Verified every fix against the live sq --help tree and, for the custom-type/override-path claims, a real scratch squad.
<!-- sq:discussion:end -->
