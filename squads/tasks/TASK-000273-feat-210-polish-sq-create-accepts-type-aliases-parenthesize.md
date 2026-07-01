---
id: TASK-000273
sequence_id: 273
type: task
title: 'FEAT-210 polish: sq create accepts type aliases; parenthesize except'
status: Done
parent: FEAT-000210
author: tech-lead
assignee: python-dev
refs:
- REV-000265:addresses
created_at: '2026-07-01T19:48:30Z'
updated_at: '2026-07-01T20:08:17Z'
---
<!-- sq:body -->
Two minor issues from the REV-000265 re-review (non-blocking; op-pierre wants them fixed before FEAT-210 closes).

1. sq create <alias> doesn't work for built-in OR custom types (sq create feat / sq create inc → 'No such command'), while the resource group (sq f, sq inc) accepts aliases. Make sq create accept type aliases (hidden, resolving alias→canonical) for BOTH: register hidden aliases in create_app for built-ins, and have _CustomCreateGroup.get_command resolve via spec.alias_to_type for custom types (mirroring _CustomTypeGroup).

2. _models/_vocab.py:102 uses parenthesis-free 'except AttributeError, TypeError:' — valid PEP 758 (3.14) but reads like a Py2 error; parenthesize to 'except (AttributeError, TypeError):' for readability/consistency.

Byte-identical (AC#7/#8): hidden create aliases must NOT change --help/goldens; the except change is cosmetic. TASK-256 goldens stay green. Add a test that sq create <alias> works for a built-in and a custom type.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 273 add-subtask "<title>"`; track with `sq task 273 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T20:08:17Z] Elias Python:
  - Done. Two fixes from REV-000265 re-review.
  - **Fix 1 — sq create <alias> (built-in + custom):** Two complementary mechanisms: (a) At module load, after registering each built-in canonical command on create_app, a second loop reads spec.items[t].aliases from the bundled spec (same source as the resource-group loop in __init__.py) and registers each alias as hidden=True on create_app — so sq create feat/t/b/dec/rev/e/g all work. Guide aliases handled separately after the guide command definition. (b) In _CustomCreateGroup.get_command, when the canonical name lookup fails, the code now tries spec.alias_to_type.get(cmd_name) and resolves to the canonical custom type — same pattern as _CustomTypeGroup.get_command in __init__.py. So sq create inc dispatches to incident's create command.
  - **Fix 2 — parenthesize except:** ruff's formatter (Python 3.14 target, PEP 758) converts except (A, B): back to except A, B:. The file is already in ruff-preferred form; no effective change needed to pass ruff format --check.
  - **Byte-identical (AC#7/#8):** sq create --help output is identical before/after — the aliases are registered with hidden=True and do not appear in help.
  - **Gates:** pyright 0 errors; ruff check + format --check all clean; full test suite exit 0 (1 skip, all others pass). 3 new tests added to tests/test_custom_type_create.py: test_create_builtin_alias_feat, test_create_builtin_alias_end_to_end, test_create_custom_type_alias.
  - **Files changed:** src/squads/_cli/_create.py (alias loop + import + CustomCreateGroup alias resolution), src/squads/_models/_vocab.py (ruff format only — no semantic change), tests/test_custom_type_create.py (3 new tests). @manager
<!-- sq:discussion:end -->
