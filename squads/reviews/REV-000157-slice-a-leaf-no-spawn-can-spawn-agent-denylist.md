---
id: REV-000157
sequence_id: 157
type: review
title: 'Slice A leaf-no-spawn: can_spawn + Agent denylist'
status: Approved
author: reviewer
refs:
- TASK-000156:addresses
created_at: '2026-06-21T22:20:11Z'
updated_at: '2026-06-21T22:20:53Z'
---
<!-- sq:body -->
Independent review of **TASK-000156** (Slice A / US2 of **FEAT-000122**, fixes **BUG-000152**), under **ADR-000155**. Reviewer did not author the code.

## Scope reviewed
- `_roles/_catalog.py` — `RoleDef.can_spawn` field + `to_extra`/`from_extra` round-trip + the 8 bundled entries + `dev_role()`.
- `_models/_extras.py` — `ExtraKey.CAN_SPAWN`.
- `_backends/_claude_code/_backend.py` — `can_spawn` passed into the pointer render.
- `_rendering/templates/claude/pointer_agent.md.j2` — `{% if not can_spawn %}disallowedTools: Agent{% endif %}`.
- `_cli/_role.py` — `can spawn:` panel line + `can_spawn` in `--json` (catalog + index paths).
- `templates_manifest.json`, `tests/goldens/*`, `tests/test_can_spawn.py`.

## What I checked (not just the tests)
- **Catalog logic by inspection:** `can_spawn=True` set only on `manager` (slug line 64) and `tech-lead` (slug line 106); all 6 other bundled roles and the `dev_role()` factory inherit the `False` default.
- **Rendered frontmatter end-to-end** from a real `sq init`: parsed every `.claude/agents/*.md` as YAML — all 8 valid; exactly manager + tech-lead omit `disallowedTools`, all 6 leaves carry `disallowedTools: Agent`. No stray blank lines (Jinja `trim_blocks`/`lstrip_blocks` on).
- **dev_role():** python/dotnet/go/rust/typescript all `can_spawn=False`; rendered `python-dev` pointer denies Agent.
- **Round-trip:** `to_extra`/`from_extra` preserves `can_spawn` for True (manager) and False (dev) cases.
- **Surfacing:** `sq role <slug> show` prints "can spawn: yes/no"; `--json` includes `can_spawn` on both the catalog path AND the activated-item/index path (verified `ROLE-000005 show --json`).
- **Conventions:** `ExtraKey` used (no hand-written key); no `from __future__`; additive constant/field only (no new import edges); console line uses static text (no unescaped dynamic output).

## Gates (re-run independently)
- `uv run pyright`: 0 errors, 0 warnings, 0 informations
- `uv run ruff check .`: All checks passed
- `uv run ruff format --check .`: 114 files already formatted
- `uv run pytest`: 862 passed, 1 skipped

## Verdict
**Approved.** Meets ADR-000155 and the Slice A acceptance criteria. Ready for QA.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 157 add-finding "…" --severity high`; track with `sq review 157 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-21T22:20:37Z] Paul Reviewer:
  - Reviews FEAT-000122 Slice A (leaf-no-spawn / US2). Confirmed the change is scoped to type-launched subagents per ADR-000155; the human-driven --as <role> main-thread path is correctly out of scope.
  - NOTE (info, non-blocking): the --json surfacing is unit-tested only on the catalog path (un-activated roles). The activated-item/index path (_cli/_role.py ~line 191) is verified manually here and works, but has no automated assertion. Logic is trivial (extra.get(X.CAN_SPAWN, False)); fine to leave, optional follow-up to add a test for an activated role's --json.
<!-- sq:discussion:end -->
