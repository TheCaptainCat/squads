---
id: REV-1066
sequence_id: 1066
type: review
title: 'Review TASK-989: import-graph guard and role moves'
status: Approved
author: reviewer
refs:
- TASK-989
- ADR-984
description: Behaviour-neutral move confirmed and the guard falsified; four low findings
subentities:
- local_id: F1
  title: CLAUDE.md calls _clock a leaf; it imports _context
  status: Fixed
  severity: low
- local_id: F2
  title: Guard's blind-spot statement is incomplete and partly false
  status: Fixed
  severity: low
- local_id: F3
  title: Two doc references name a moved function's old home
  status: Fixed
  severity: low
- local_id: F4
  title: Moved docstrings carry history prose into the new module
  status: Fixed
  severity: low
created_at: '2026-10-16T18:11:15Z'
updated_at: '2026-10-16T18:14:02Z'
---
<!-- sq:body -->
Review of the commit "Guarded the package import graph and moved the roster views and role derivations to named modules" (1fd45be5 on release/0.16), against TASK-989 and ADR-984.

## What was checked, and how

- **Behaviour neutrality of the three body changes in `_interactions/_role_guidance.py`.** The old bodies read the module global `_PLAYBOOK_SPEC` directly; the new ones call `_active_playbook`, which imports `get_playbook_spec` at call time. `get_playbook_spec()` returns that same global, so the fallback object is identical. It is used only when a caller passes `playbook=None`; every production call site still passes the merged playbook, and those lines changed only their import. An active override therefore reaches the moved functions exactly as before. The function-local import of `SQUADS_SKILL`/`GREETING_SKILL`/`MEMORY_SKILL`/`item_skill_name` in `skills_for_role` resolves to the same constants. No test or source file monkeypatches `get_playbook_spec` or `_PLAYBOOK_SPEC` (checked with a grep), so the change of read path changes nothing observable. Falsified in a scratch copy of the commit: with `_active_playbook` made to ignore the threaded playbook, the characterisation table and `test_playbook_override_consumers` both go red. With the bundled fallback emptied, the characterisation rows go red.
- **The guard fails.** Run in a scratch copy of the commit: a planted `_models -> _services` import (a function-local one; the module-top version is a real cycle and errors at collection); a deleted live row; a phantom row; a statement in the empty `_backends/__init__.py`; the old `_views -> _backends` import put back (both the edge assertion and the component assertion fail); a node removed from the component set. Each produced a precise failure message.
- **Leftovers.** An AST scan of `src` and `tests` finds no `from squads._interactions import` or `from squads._backends._base import` of any moved name. A grep finds no `_RoleGuideBearing`/`_SlugBearing` and no attribute access through the old modules. The names `DEV` and `in_lane_owner`, which the init still imports, are used inside it, so they are not re-exports.
- **CLAUDE.md.** The managed region (exact marker lines) hashes the same before and after (cdbdfe00…). The non-empty-inits list and the component sentence agree with the guard's tables. One claim does not (finding 1).
- **Tests change by import line only**, apart from the three new modules. A diff with import lines filtered out shows only the module-alias rename at call sites.
- Targeted runs (`-n0`): the guard (34 passed) and the characterisation and override selectors (79 passed). Ruff check and format are clean on the touched packages.

The move is behaviour-neutral, and the guard does what it claims for the import forms it recognises. The findings are low: one false sentence in CLAUDE.md, an incomplete statement of what the guard cannot see, two stale doc references, and some history prose carried in by the move.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1066 add-finding "…" --severity medium`; track with `sq review 1066 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — CLAUDE.md calls _clock a leaf; it imports _context

<!-- sq:finding:F1:body -->
`CLAUDE.md` now says `_models` "imports only the leaf modules _clock, _errors and _util". `_clock` is not a leaf. `src/squads/_clock.py:11` imports `squads._context` at module top, and the guard records it as the row `_clock -> _context top`. The task body named this same chain (`_models/_item.py` imports `_clock`, which imports `_context`) when it scoped the correction.

The acceptance asks for each corrected passage to be checked against the edge that shows it. This one contradicts a row of the table it points to, and `CLAUDE.md` is loaded into every agent session.

Fix: drop "leaf", e.g. "imports only `_clock`, `_errors` and `_util` (and, through `_clock`, `_context`)". Or state the rule the table enforces, without the adjective.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Guard's blind-spot statement is incomplete and partly false

<!-- sq:finding:F2:body -->
What the guard's module docstring says it cannot see is incomplete, and two of its sentences are false. Each case below was driven in a scratch copy of the commit:

- `__import__("squads._services._base")` with a **literal** argument: unseen (34 passed). The docstring names only `importlib.import_module` with a computed argument as the blind spot.
- `importlib.import_module("._base", "squads._services")`, a relative literal with `package=`: unseen (34 passed). `_node_of_dotted` drops a leading-dot name silently. The docstring says a literal `import_module` "counts as an import where it stands", and a relative `from . import` is refused loudly, so this form should be refused too, or stated.
- The docstring says `_backends` "loads its own backends that way", meaning with a literal argument. `_backends/_registry.py:25` calls `importlib.import_module(module_path)` with a loop variable: a computed argument, which the walker does not see at all. The outcome is harmless because it is a self edge, but the sentence describes a mechanism that never runs.
- "`squads` itself stands for the root `__init__` and `__main__`" is false. `_importer_of` makes `__main__` its own node, and the table has the row `__main__ -> _cli top`.

No current source uses `__import__` or a relative `import_module` (checked with a grep), so nothing is missed today. The fix is to make the statement true: refuse or resolve the relative literal, then list `__import__` and any other dynamic loader (`importlib.util`, `runpy`) as unseen. Also correct the registry and `__main__` sentences.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Two doc references name a moved function's old home

<!-- sq:finding:F3:body -->
Two doc references still name a moved function at its old home:

- `src/squads/_services/_base.py:619`: `:func:`~squads._interactions.catalog_default_slug`` now dangles. The function lives in `squads._interactions._role_guidance`.
- `tests/unit/test_playbook_source_applicability_agrees_with_item_skill_branch.py:12`: the module docstring says `_interactions.laned_types`, while the file's own import (line 32) is now from `_role_guidance`.

Found with `rg "_interactions\.(…moved names…)"`. The other `role_guidance.skills_for_role` mentions in `_backends/_base.py` and `_services/_base.py` are consistent with the module name and are fine.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Moved docstrings carry history prose into the new module

<!-- sq:finding:F4:body -->
The move copied docstrings verbatim. As a result, the new module `_interactions/_role_guidance.py` carries prose that the comment rule (one or two sentences, no history) would not let a new file carry:

- `laned_types` (line 62-65): "computed once at import off the bundled document, a renamed or project-declared type could never enter the domain, so the lane check short-circuited and lane discipline went dark". This is the before-state of a change, not what the code does.
- `item_types_for_role` (line 137): "reproduces today's behaviour exactly".
- `item_skill_role_sections` (line 195): "per the source-widening decision's guard", a pointer to a decision the reader cannot resolve.

"Bodies unchanged" was the brief for a behaviour-neutral move, so this is not a defect of the move itself. TASK-990 rewrites this module, which makes it the natural home. Disposition: fix there, and record that on this finding, rather than leaving it Open.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T18:11:53Z] Paul Reviewer:
  - Verdict recommended: approve once the four low findings each have a disposition. The move is behaviour-neutral: the playbook fallback is the same object, read through its accessor, and the threaded override path was falsified red in a scratch copy. The guard fails on a planted edge, a deleted row, a phantom row, a new non-empty init and a component change. The managed region of CLAUDE.md is byte-identical. F1 to F3 are small fixes for python-dev; F4 can go to TASK-990, which rewrites the module. Left InReview, not self-approved. @python-dev @manager
- [2026-10-16T18:13:45Z] Elias Python:
  - F1 to F4 fixed: CLAUDE.md _clock wording, guard docstring and relative import_module refusal, two stale references, role-guidance docstrings.
- [2026-10-16T18:14:01Z] Catherine Manager:
  - Approved: F1–F4 Fixed in 90822b25; behaviour neutrality and guard falsification verified by the reviewer.
<!-- sq:discussion:end -->
