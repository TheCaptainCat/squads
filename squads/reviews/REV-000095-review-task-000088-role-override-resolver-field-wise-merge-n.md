---
id: REV-000095
sequence_id: 95
type: review
title: 'Review TASK-000088: role override resolver (field-wise merge + new slugs)'
status: Approved
author: reviewer
refs:
- TASK-000088
subentities:
- local_id: F1
  title: New-slug admission checks key presence only, not non-emptiness
  status: Open
  severity: low
- local_id: F2
  title: 'RoleDef frozen dataclass: scalar override values not type-validated'
  status: Open
  severity: low
created_at: '2026-06-12T21:32:57Z'
updated_at: '2026-06-23T09:59:41Z'
---
<!-- sq:body -->
Review of TASK-000088 (role override resolver) under FEAT-000014, against ADR-000085 §2 (field-wise merge by slug, project→bundled) and §4 (slugs canonical, non-renamable).



VERDICT: Approved with two low-severity nits (non-blocking). Safe to build TASK-000089 on.



Scope reviewed: _roles/_resolver.py (new), _services/_roster.py, _services/_maintenance.py, _services/_base.py, _cli/_role.py, tests/conftest.py (REV-093 F1 fix), tests/test_role_resolver.py. T90 init-naming changes (_config.py, _main.py, _engine.py override loader from T87) ignored as out of scope.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 95 add-finding "…" --severity high`; track with `sq review 95 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | New-slug admission checks key presence only, not non-emptiness |
| F2 | 🟢 low | Open |  | RoleDef frozen dataclass: scalar override values not type-validated |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — New-slug admission checks key presence only, not non-emptiness

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
New-slug admission checks key presence only, not non-emptiness. A TOML with required keys present but empty (title="", mission="") admits a degenerate role with blank fields. _apply_override uses [f for f in _REQUIRED_FOR_NEW if f not in data]; an empty string passes. Inconsistent with the NonEmpty guard used for titles elsewhere. ADR §2 does not strictly mandate non-empty, and the project owns its own TOML, so non-blocking.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — RoleDef frozen dataclass: scalar override values not type-validated

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
RoleDef is a frozen dataclass, so scalar override values are not type-validated. e.g. model=42 in a TOML is accepted and stored verbatim, flowing to extra/pointer; only TypeError (unknown/missing kwargs) is caught and wrapped. Low risk (project-owned file), but a wrong-typed model/color/is_default passes silently. Consider validating scalar types or coercing in _apply_override.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T21:33:39Z] Paul Reviewer:
  - VERDICT: Approved. The resolver implements ADR-000085 §2/§4 correctly: field-wise merge over PREDEFINED (only TOML-set fields change, rest inherited — verified for scalars and tuple fields), new-slug admission requires full_name/title/description/mission, the slug key is genuinely ignored (filename stem is canonical), and malformed TOML raises SquadsError (exit 1, clear message with path).
  - All role-producing paths route through the resolver: activate_role→resolve_role, add_dev→resolve_dev_role (explicit name kwarg correctly wins over TOML full_name), _refresh_catalog_extra→resolve_role (RoleNotFoundError caught for dev/unknown slugs — correct, it subclasses SquadsError), author() fallback→resolve_role, and sq role show display+json→resolve_role with e()-escaping on every dynamic field. sq role catalog intentionally lists the bundled PREDEFINED menu (not project-resolved) — acceptable. init/adopt use resolve_roles for the bundled --roles menu but only consume .slug, and activate_role re-resolves through the override, so bundled-slug overrides apply at init; new slugs are added post-init via sq role activate (in scope, works).
  - REV-093 F1 conftest teardown is correct: _env_cache.clear() is pure-memoization (rebuild-on-access, can't change behaviour) and set_active_squad_dir(None) resets the ContextVar post-test; it cleans up rather than pre-seeds, so it cannot mask a bug within the test under run — it kills exactly the order-dependent coupling it targets.
  - Conventions clean: private module, no from __future__, acyclic imports, RoleDef reused (not re-modeled), pyright/ruff clean on the whole review surface. Two LOW non-blocking findings filed on REV-000095 (F1: new-slug empty-string required fields admitted; F2: scalar override values not type-validated). Neither gates approval.
  - NOTE: uv run pyright reports 2 errors in src/squads/_models/_config.py ([init.names] dict typing) — that is unrelated T90 init-naming work in the tree, outside this review surface, and does not gate TASK-000088. Flagging so it is addressed in T90's review.
<!-- sq:discussion:end -->
