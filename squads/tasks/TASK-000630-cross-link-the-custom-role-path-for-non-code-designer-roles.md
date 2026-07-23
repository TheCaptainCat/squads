---
id: TASK-630
sequence_id: 630
type: task
title: Cross-link the custom-role path for non-code/designer roles
status: Done
parent: FEAT-574
author: tech-lead
description: 'US3: pointer from roles/agents docs to the .overrides/roles + role activate
  walkthrough'
created_at: '2026-07-23T08:03:51Z'
updated_at: '2026-07-23T09:50:16Z'
---
<!-- sq:body -->
Implements FEAT-574 **US3**. Cross-link the custom-role path for a role that isn't a
coding `--tech` (e.g. a designer/UX role), from the place an adopter looks for it.

## Scope

- Add a short pointer in `docs/roles.md` or `docs/agents.md` — wherever the "I need a
  role that isn't a coding `--tech`" question naturally lands — to the existing
  walkthrough in `docs/overrides.md`: scaffold `.overrides/roles/<slug>.toml`
  (`sq override scaffold --new <slug>`), fill in the essentials, then `sq role activate
  <slug>`. The `compliance-officer` example in `docs/overrides.md` is the worked case;
  cross-link to it rather than duplicating it.
- Cross-link only — no new mechanism, no new walkthrough.

## Notes

- This is the documentation answer to the "no bundled non-code role" gap. A *bundled*
  designer/UX role is a separate, still-open question (FEAT-575 US6, held pending the
  architect's recommendation) — do not describe or pre-empt a bundled role here; point
  only at the override path that exists today.
- Adopter-facing: no sq item / ticket / dev-process references.

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

_Add with `sq task 630 add-subtask "<title>"`; track with `sq task 630 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T09:28:48Z] Elias Python:
  - docs/roles.md already had a 'Custom non-dev roles' section pointing at the override path -- fixed its broken cross-link (it cited a nonexistent overrides.md heading, 'Role overrides merge by field', which is bold lead-in prose under Precedence rule, not its own anchor) to point at the real worked example, 'Define a custom role' (the compliance-officer walkthrough), and mentioned a designer/UX role as an example use case per the task.
  - Cross-link only, no new mechanism; the future sq dev add --kind path is not mentioned.
<!-- sq:discussion:end -->
