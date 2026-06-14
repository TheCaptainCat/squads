---
id: REV-000093
sequence_id: 93
type: review
title: Review TASK-000087 — override loader + precedence plumbing
status: Approved
parent: FEAT-000014
author: reviewer
refs:
- TASK-000087
description: Engine ChoiceLoader + squad-aware cache + ContextVar; verdict for the
  FEAT-014 foundation task
subentities:
- local_id: F1
  title: 'No autouse fixture resets engine module-state between tests (_active_squad_dir
    ContextVar + _env_cache dict). conftest resets the clock but not the engine: ServiceCore.__init__
    sets the _active_squad_dir ContextVar and never restores it, so a test that constructs
    a service leaves that squad dir active for any later test that calls bare render()
    without setting it. Today it doesn''t bite (override tests set it explicitly;
    fresh tmp_path keys avoid cache collisions), but it''s order-dependent coupling
    that will grow as T88/T89 add override tests. Suggest an autouse fixture that
    calls set_active_squad_dir(None) (and optionally clears _env_cache) on teardown,
    mirroring _reset_clock_override.'
  status: Fixed
  severity: low
created_at: '2026-06-12T21:10:56Z'
updated_at: '2026-06-12T21:29:05Z'
---
<!-- sq:body -->
Scope: the override loader + precedence plumbing for TASK-000087 (FEAT-000014, ADR-000085 §1/§2) — _rendering/_engine.py (ChoiceLoader + per-squad-dir Environment cache + ContextVar), _services/_base.py (ServiceCore activates the squad dir), tests/test_override_loader.py (6 tests). Unrelated working-tree changes (golden-file / TASK-000083 / _cli/_main.py / docs) were out of scope and ignored.

Verdict: APPROVED. Per-file precedence (project override → bundled, presence-is-the-override, no merge) matches ADR §2; render() and all call sites are byte-for-byte unchanged; cross-squad isolation holds (cache keyed by squad_dir, proven by the isolation test). Suite green (401 passed, 1 skipped), pyright/ruff clean. One LOW finding filed (test-isolation: no autouse reset of engine state) — non-blocking, safe to build T88/T89 on.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 93 add-finding "…" --severity high`; track with `sq review 93 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | No autouse fixture resets engine module-state between tests (_active_squad_dir ContextVar + _env_cache dict). conftest resets the clock but not the engine: ServiceCore.__init__ sets the _active_squad_dir ContextVar and never restores it, so a test that constructs a service leaves that squad dir active for any later test that calls bare render() without setting it. Today it doesn't bite (override tests set it explicitly; fresh tmp_path keys avoid cache collisions), but it's order-dependent coupling that will grow as T88/T89 add override tests. Suggest an autouse fixture that calls set_active_squad_dir(None) (and optionally clears _env_cache) on teardown, mirroring _reset_clock_override. |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — No autouse fixture resets engine module-state between tests (_active_squad_dir ContextVar + _env_cache dict). conftest resets the clock but not the engine: ServiceCore.__init__ sets the _active_squad_dir ContextVar and never restores it, so a test that constructs a service leaves that squad dir active for any later test that calls bare render() without setting it. Today it doesn't bite (override tests set it explicitly; fresh tmp_path keys avoid cache collisions), but it's order-dependent coupling that will grow as T88/T89 add override tests. Suggest an autouse fixture that calls set_active_squad_dir(None) (and optionally clears _env_cache) on teardown, mirroring _reset_clock_override.

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
_Describe the finding, its impact, and a recommendation — free-form._
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T21:11:31Z] Paul Reviewer:
  - Verification & reasoning notes (not findings):
  - Traversal guard: the .overrides/templates path is built from code-constant segments (squad_dir / '.overrides' / 'templates'), not from hand-edited frontmatter, so there's no traversal vector for abspath() to guard — and Jinja2's FileSystemLoader already rejects '../' in template names. The guard is respected by construction; routing through paths.abspath() would be belt-and-suspenders but isn't required for safety.
  - Thread/async safety: _active_squad_dir is a ContextVar (correct — per logical call stack); _env_cache is a plain module dict but is only keyed by squad_dir and only inserted/popped, so the worst race (two threads building the same key) discards a redundant Environment harmlessly — no corruption, no cross-squad leak. Jinja2 Environments are render-thread-safe. set_active_squad_dir uses .set() without a token reset (last-writer-wins) — fine for the synchronous CLI execution model; the ContextVar is the right foundation if concurrency is ever added.
  - Stale-cache hazard: _make_env decides override-vs-bundled at build time and caches per squad_dir. If .overrides/ is created after the env is first cached IN THE SAME PROCESS, the override is ignored until invalidate_squad_dir() is called. Non-issue for the per-invocation CLI (each sq run is a fresh process; scaffold runs separately). It's documented in the docstring and invalidate_squad_dir() exists as the escape hatch — worth T89's author keeping in mind when sq override scaffold writes into a live process.
<!-- sq:discussion:end -->
