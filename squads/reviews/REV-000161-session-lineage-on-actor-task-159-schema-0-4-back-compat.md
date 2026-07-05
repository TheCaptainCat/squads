---
id: REV-161
sequence_id: 161
type: review
title: 'Session lineage on actor (TASK-159): schema 0.4 + back-compat'
status: Approved
author: reviewer
priority: medium
refs:
- TASK-159:addresses
subentities:
- local_id: F1
  title: 'v0_4 corpus fixture: .squads.json stuck at schema 0.3 (toml says 0.4)'
  status: Open
  severity: low
created_at: '2026-06-22T10:08:44Z'
updated_at: '2026-06-22T10:09:50Z'
---
<!-- sq:body -->
Independent review of TASK-159 (Record optional session lineage on the actor) — implements FEAT-125 US1 under ADR-158. Did not author this code.

## Scope reviewed
Integrity-core change: env-seeded session pair in `_actor.py`, additive reflog fields, optional item frontmatter fields, schema bump 0.3->0.4 + `_v0_3_to_v0_4` no-op runner, and propagation across the mutation paths.

## What I checked (all pass)
1. **Schema bump + migration.** `SCHEMA_VERSION` "0.3"->"0.4"; runner wired into MIGRATIONS (version 0.5.0, from_schema 0.3, to_schema 0.4) with a MANUAL runbook; CHANGELOG Added+Migration entries. Runner is a genuine no-op (returns 0) and that is correct here — all new fields are optional/back-compat, old files stay valid. `sq migrate up` is idempotent on the repo squad (already 0.4) AND runs clean on a real copied v0_3 corpus (stamps 0.4, json+toml both consistent after). Root callback gate uses `schema_tuple()` comparison, never raw string `<`/`>`.
2. **Back-compat (Invariant 1).** Legacy slug-only reflog lines parse with session fields None (reader uses `data.get(...)`); items without created/modified_session load fine (`from_frontmatter` defaults None); `to_frontmatter_dict` OMITS them when None so existing files don't churn; `sq repair` rebuilds from frontmatter. Tests cover all three.
3. **Additive, not nesting.** `actor` stays a flat slug string on the reflog; session_id/parent_session_id are optional top-level SIBLINGS, omitted when None. reflog_shape golden bumped only the version string; its `fields` list stays minimal (does not advertise the optional siblings) — additive and clean.
4. **Env-only invariant.** session_id/parent_session_id read ONLY in `seed_session(from_env=True)`, called only from `main_callback`. The `--as`/`--author` path calls `set_actor(slug)` only — verified no flag path touches session. Empty-string env is coerced to None.
5. **Untrusted wording.** Best-effort/untrusted/observability-only framing present in `_actor` docstrings, reflog schema docs, Item field docstrings, ReflogEntry, the runner MANUAL, and the changelog. No tamper-evidence/enforcement claim anywhere.
6. **Conventions.** `modified_session` propagation complete and consistent across set_status/update/link/unlink/add_ref/rm_ref and `_locked_section_edit` (which covers comment + subentity paths); `created_session` seeded at create. Uses `clock`; no `datetime.now()`; no `from __future__`; pyright/ruff/format clean.

## Gates (re-run myself)
- pyright: 0 errors. ruff check: clean. ruff format --check: 116 files formatted.
- pytest: full suite green (two independent runs exit 0; dev reported 890 passed / 1 skipped).
- `sq migrate up`: idempotent; clean on a real 0.3 corpus.

## Verdict
Approve. One LOW finding on the v0_4 corpus fixture (see review points) — non-blocking.

## Out of scope (intermingled in working tree)
The branch also carries TASK-156 `can_spawn` changes (`_catalog.py`, `_extras.py`, `_role.py`, `_backend.py`, pointer_agent template, several goldens). Not part of TASK-159; flagged to manager, not reviewed here.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 161 add-finding "…" --severity high`; track with `sq review 161 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | v0_4 corpus fixture: .squads.json stuck at schema 0.3 (toml says 0.4) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — v0_4 corpus fixture: .squads.json stuck at schema 0.3 (toml says 0.4)

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The new fixture tests/fixtures/corpus/v0_4/ has .squads.toml stamped schema_version="0.4" but its .squads.json still carries "schema_version": "0.3". Other corpus fixtures (v0_3) are internally consistent (toml and json agree). The corpus README states each fixture ships ".squads.json with the index at that version's shape" — this fixture violates that contract: it is a copy-and-stamp artifact where only the toml was re-stamped.

Impact: NON-BLOCKING. The migration corpus test still passes because starting at 0.4 finds nothing to migrate, then repair re-stamps the json from frontmatter during the run. I independently confirmed a real 0.3->0.4 migration produces json+toml both at 0.4 and consistent, so runtime/back-compat is unaffected. The issue is fixture hygiene/faithfulness only — a true frozen 0.4 snapshot should already have json at 0.4.

Fix: re-stamp tests/fixtures/corpus/v0_4/.squads.json schema_version to "0.4" so the fixture is a faithful 0.4 capture. Optional: add v0_4 to the README directory-layout list.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T10:09:50Z] Paul Reviewer:
  - Approved. Independent review of TASK-159 (session lineage / schema 0.4). All six review priorities verified: schema bump + no-op migration correct (idempotent + clean on a real 0.3 corpus), back-compat holds (legacy reflog lines and items load None), additive-not-nesting (actor stays a flat slug, siblings omitted when None), env-only invariant (session set only via seed_session(from_env) at main_callback, never a flag), untrusted wording everywhere, modified_session propagation complete. Gates green: pyright/ruff/format clean, full pytest green. One LOW non-blocking finding (F1): v0_4 corpus fixture's .squads.json left at schema 0.3 while its toml is 0.4 — fixture hygiene, no runtime impact.
<!-- sq:discussion:end -->
