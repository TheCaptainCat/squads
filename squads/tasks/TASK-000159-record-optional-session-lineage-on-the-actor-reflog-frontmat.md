---
id: TASK-000159
sequence_id: 159
type: task
title: Record optional session lineage on the actor (reflog + frontmatter, additive)
status: Done
parent: FEAT-000125
author: tech-lead
assignee: python-dev
subentities:
- local_id: ST1
  title: 'Structured actor record: read env session pair, additive reflog + frontmatter
    fields, schema 0.4 migration'
  status: Done
  story: US1
created_at: '2026-06-22T09:11:18Z'
updated_at: '2026-06-22T10:37:16Z'
---
<!-- sq:body -->
Implements **US1** of FEAT-000125 per **ADR-000158** (Accepted). Read both before starting; this is the data-model + schema/migration foundation that US2 (TASK-000160) builds on.

## Guarantee framing (non-negotiable wording)
squads is a **passive tool, never in the spawn path**. It only **reads** optional session ids that already happen to be in its invocation environment and **records** them. It does **not** mint, inject, spawn, or verify. Every doc/field/comment you write must call the result **best-effort, untrusted, observability-only** — never tamper-evident, never an enforcement input. A copied/forged/absent session id is indistinguishable from a real one.

## Scope (squads-side only)
Setting/propagating the env vars is the agent layer's job and is **explicitly OUT of scope** — do not touch skills/prompts/spawn logic.

### 1. Ambient session pair in `_actor.py`
`src/squads/_actor.py` today holds one module-global slug string (`_override`, default `"system"`), set via `set_actor(slug)` and read via `current_actor() -> str`. Extend it to carry an optional session pair **alongside** the slug:
- Add a one-time seed from the environment, read **once** at the CLI root callback: `SQUADS_SESSION_ID` / `SQUADS_PARENT_SESSION_ID` via `os.environ.get(...)` (both optional → `None` when absent).
- Wire it in `src/squads/_cli/__init__.py::main_callback`, right where it already calls `actor.set_actor("system")` (line ~70). The session seed must mirror the actor reset discipline so it does not leak across invocations/tests (same pattern as the `"system"` re-set; no `--at`-style flag).
- The slug-override path stays as-is: `--as`/`--author` → `set_actor(slug)` (callers in `_cli/_items.py`, `_cli/_create.py`) sets only the **human-facing slug**. The session fields come **only** from the env and are **NOT settable by any later CLI flag**.
- Expose a reader the writers can call (e.g. keep `current_actor() -> str` unchanged for the slug, add `current_session() -> tuple[str|None, str|None]` or a small dataclass). Mirror `_clock` style.

### 2. Additive reflog fields (`src/squads/_index/_reflog.py`)
- `actor` **stays a flat slug string** (back-compat — FEAT-000013 stability; existing `--json` golden shapes must remain valid).
- Add two **optional sibling top-level** fields to the written line: `session_id`, `parent_session_id` (both nullable). `append_line(...)` gains the two kwargs; omit them from the record when `None` (keep lines small) OR include as `null` — pick one and be consistent with the reader.
- `ReflogLine` dataclass gains the two optional fields; `read_lines` parses them with `data.get(...)` defaulting to `None`. **Old slug-only lines must parse as `session_id=None, parent_session_id=None`** (no forced rewrite).
- Update the call sites that build lines/entries: `_services/_maintenance.py` (~line 167, 252, 414) and `_index/_store.py` (~line 167) so the session pair flows from `_actor` into the written line. `ReflogEntry` in `_services/_results.py` (~line 108) gains the two optional fields too, populated in `read_reflog` (~`_maintenance.py:414`).

### 3. Optional item frontmatter session fields (`src/squads/_models/_item.py`)
- `Item` today stores `author: str | None` (line ~89), `created_at`, with `to_frontmatter_dict` / `from_frontmatter` (~123/155). Add optional `created_session` / `modified_session` fields — minimal footprint is fine (a single `session_id` string each, or a small `{session_id, parent_session_id}` sub-object; your call, document it).
- `to_frontmatter_dict` **omits them when unset**; `from_frontmatter` reads them as `None` when absent. **Existing item files remain valid with no rewrite.** Populate `created_session` at item create (from `current_session()`), `modified_session` on mutation, wherever `author`/`current_actor()` is sourced today.

### 4. Additive schema bump — coordinate with the migration registry (CLAUDE.md)
**RISK / READ CAREFULLY:** `_models/_schema.py::SCHEMA_VERSION` is **already `"0.3"`**, and `_migrations/_registry.py` already has a `_v0_2_to_v0_3` runner (head-region backfill). So your additive bump is **0.3 → 0.4**, NOT 0.2 → 0.3 (the ADR/feature text predates the 0.3 head migration). Do:
- Bump `SCHEMA_VERSION` to `"0.4"`.
- Add a private runner `_migrations/_v0_3_to_v0_4.py` exposing `migrate(paths) -> int` and a `MANUAL` string. It is **additive — no file rewrite needed** (the new fields are optional and back-compat); the runner can be a no-op that returns 0 touched, with a `MANUAL` runbook string explaining the additive session fields are best-effort/untrusted and require no action. Stamp happens via `sq migrate up`.
- Append a `Migration(version=..., from_schema="0.3", to_schema="0.4", summary=..., run=..., manual=...)` to `MIGRATIONS`.
- Add the changelog entry for the release.

## Acceptance
- `_actor.py` reads `SQUADS_SESSION_ID`/`SQUADS_PARENT_SESSION_ID` once at `main_callback`; present → recorded, absent → slug-only exactly as today; session fields **not** settable by any later flag.
- Reflog `actor` stays a flat slug string; `session_id`/`parent_session_id` are additive optional siblings; **legacy slug-only reflog lines parse with both `None`** and `sq reflog`/`--json` still work.
- Item frontmatter gains optional `created_session`/`modified_session`; **existing item files load unchanged**; `sq repair` of legacy data still works (load + rebuild proves Invariant 1).
- `SCHEMA_VERSION == "0.4"`, the `_v0_3_to_v0_4` runner is wired into `MIGRATIONS` with a `manual` runbook + changelog entry, and **`sq migrate up` runs clean** on a 0.3 squad (additive, no data loss).
- Best-effort/untrusted wording present in the new field docstrings + reflog schema docs + the runner's `MANUAL`.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; full `uv run pytest` green.
- New tests: service-level (record + read-back a session pair; legacy slug-only line parses as `None`; item frontmatter round-trips with and without session) **and** a CLI smoke test (`sq reflog --json` shows the new fields when env set; absent when not).

Out of scope: the `--tree` view and `show --full` session surfacing (→ TASK-000160, depends on this).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 159 add-subtask "<title>"`; track with `sq task 159 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Structured actor record: read env session pair, additive reflog + frontmatter fields, schema 0.4 migration | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Structured actor record: read env session pair, additive reflog + frontmatter fields, schema 0.4 migration

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Structured actor record in the reflog (slug + session + parent)
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T09:13:16Z] Olivia Lead:
  - @python-dev US1 of FEAT-000125 / ADR-000158 (Accepted) — the read-and-record foundation. squads is a passive tool, never in the spawn path: read optional SQUADS_SESSION_ID/SQUADS_PARENT_SESSION_ID once at main_callback into _actor.py (alongside the slug; NOT settable by any later flag), record them as additive optional siblings on the reflog (actor stays a flat slug string) and as optional created_session/modified_session item frontmatter. Best-effort/untrusted/observability-only wording is mandatory in every field doc + the migration MANUAL.
  - SCHEMA RISK — read carefully: SCHEMA_VERSION is ALREADY 0.3 (a _v0_2_to_v0_3 head-region migration already shipped). Your additive bump is 0.3 -> 0.4, NOT 0.2 -> 0.3 as the older ADR/feature text implies. Add _migrations/_v0_3_to_v0_4.py (additive, no file rewrite — a no-op runner returning 0 + a MANUAL runbook is fine), wire it into MIGRATIONS, bump SCHEMA_VERSION to 0.4, add the changelog entry. Coordinate per CLAUDE.md's migration-registry rule.
  - Acceptance: legacy slug-only reflog lines parse as session=None; existing item files load unchanged (sq repair proves Invariant 1); sq migrate up runs clean on a 0.3 squad; pyright + ruff check + ruff format --check clean; full pytest green; service-level + CLI smoke tests (reflog --json shows new fields when env set, absent otherwise). The --tree view + show --full surfacing are US2/TASK-000160 — out of scope here.
- [2026-06-22T09:55:53Z] Elias Python:
  - Implementation complete. Files changed:
  - - src/squads/_actor.py — added seed_session()/current_session(); reads SQUADS_SESSION_ID/SQUADS_PARENT_SESSION_ID from env once at CLI root; set_actor() unchanged (slug-only path)
  - - src/squads/_cli/__init__.py — added actor.seed_session(from_env=True) call in main_callback alongside the existing set_actor('system') call
  - - src/squads/_index/_reflog.py — ReflogLine gains optional session_id/parent_session_id fields; append_line gains matching kwargs (omit when None); read_lines parses them; legacy lines default both to None
  - - src/squads/_services/_results.py — ReflogEntry gains optional session_id/parent_session_id
  - - src/squads/_services/_maintenance.py — read_reflog populates session fields on ReflogEntry; repair/run_pending_migrations pass session pair to append_line
  - - src/squads/_index/_store.py — transaction reflog flush passes current_session() into append_line
  - - src/squads/_models/_item.py — Item gains optional created_session/modified_session fields (omitted from frontmatter when None; read as None when absent)
  - - src/squads/_services/_base.py — create() seeds created_session+modified_session from current_session(); _locked_section_edit updates modified_session
  - - src/squads/_services/_items.py — set_status/update/link/unlink update modified_session
  - - src/squads/_services/_refs.py — add_ref/rm_ref update modified_session
  - - src/squads/_models/_schema.py — SCHEMA_VERSION bumped 0.3 -> 0.4
  - - src/squads/_migrations/_v0_3_to_v0_4.py — new no-op runner; MANUAL runbook with best-effort/untrusted wording
  - - src/squads/_migrations/_registry.py — wired new migration (version=0.5.0, 0.3->0.4)
  - - CHANGELOG.md — Unreleased section with session lineage entry + migration note
  - - tests/fixtures/corpus/v0_4/ — new corpus fixture at schema 0.4 (copied from v0_3 + stamped)
  - - tests/test_migration_corpus.py — added (0.4, v0_4) corpus case
  - - tests/test_session_lineage.py — 26 new tests: actor, reflog, item frontmatter, back-compat, migration, CLI smoke
  - - tests/test_cli.py, test_reflog_core.py, test_reflog_read.py — updated hardcoded 0.3 strings to SCHEMA_VERSION
  - - tests/goldens/ — updated golden JSON files for new session fields on Item
  - Gate results: uv run pyright: 0 errors. uv run ruff check: clean. uv run ruff format --check: clean. uv run pytest: 890 passed, 1 skipped. sq migrate up on the project: already at schema v0.4; clean. @reviewer
- [2026-06-22T10:10:02Z] Paul Reviewer:
  - Approved, ready for QA. @qa — independent review recorded as REV-000161 (Approved). This implements FEAT-000125 US1 under ADR-000158.
  - Verified: schema 0.3->0.4 bump + _v0_3_to_v0_4 no-op runner wired into MIGRATIONS with MANUAL runbook + changelog; sq migrate up idempotent and clean on a real 0.3 corpus (json+toml both stamp to 0.4). Back-compat holds — legacy slug-only reflog lines parse with session fields None, items without created/modified_session load fine, to_frontmatter omits when None, sq repair rebuilds. actor stays a flat slug string; session_id/parent_session_id are additive optional siblings. Session fields are env-only (seed_session(from_env=True) at main_callback) and NOT settable by --as/--author or any flag; empty-string env coerced to None. Best-effort/untrusted/observability-only wording present in all surfaces. modified_session propagation complete across set_status/update/link/unlink/add_ref/rm_ref/_locked_section_edit.
  - Gates re-run by me: pyright 0 errors; ruff check clean; ruff format --check clean; full pytest green (two runs exit 0). 
  - One LOW, non-blocking finding (REV-000161 F1): the new tests/fixtures/corpus/v0_4/ fixture has .squads.json still at schema_version 0.3 while its .squads.toml is 0.4 — fixture hygiene only, no runtime/back-compat impact (the corpus test passes; a real migration stamps both consistently). @python-dev can re-stamp the fixture json to 0.4 at convenience; does not block QA.
- [2026-06-22T10:11:22Z] Catherine Manager:
  - REV-000161 finding F1 (v0_4 corpus fixture .squads.json stamped 0.3 vs toml 0.4) fixed: re-stamped schema_version to 0.4; corpus migration tests green. Ready for QA. @qa
- [2026-06-22T10:37:16Z] Mara Tester:
  - QA verification PASSED — TASK-000159 closes.
  - Full suite: 890 passed, 1 skipped. Specific suites: test_session_lineage.py (26 tests) and test_migration_corpus.py (9 tests) both 100% green.
  - Migration (v0_3→v0_4): copied v0_3 corpus fixture to a temp dir, ran `sq migrate up` (from within the dir so .squads.toml is found). Runner stamped both .squads.toml and .squads.json to schema_version 0.4. `sq check` returned no issues. Second `sq migrate up` correctly returned 'already at schema v0.4; nothing to migrate' (idempotent). `sq repair` rebuilt index (6 items, counter=6 — no loss). v0_4 corpus fixture F1 confirmed fixed: both .squads.toml and .squads.json now consistently at 0.4.
  - End-to-end lineage recording: fresh sq init, then `sq create feature 'x' --author product-owner` WITH SQUADS_SESSION_ID=test-session-abc SQUADS_PARENT_SESSION_ID=parent-session-xyz. Reflog line carries exactly: actor='product-owner', session_id='test-session-abc', parent_session_id='parent-session-xyz'. Control op (same command, no env vars): reflog line has actor only, session fields ABSENT. Item frontmatter FEAT-000009 carries created_session=test-session-abc and modified_session=test-session-abc; FEAT-000010 (no env) has no session fields.
  - Env-only invariant: `sq feature 9 comment --as product-owner -m ...` (no env vars) produces reflog line with actor only, no session fields. --as/--author does NOT populate session.
  - Back-compat: test_session_lineage.py test_legacy_slug_only_lines_parse_with_none_session and test_mixed_legacy_and_new_lines_parse_correctly both green. Items without created/modified_session load with None. sq repair on legacy data succeeds.
  - Untrusted wording: best-effort/untrusted/observability-only confirmed in _actor.py, _reflog.py (schema docs + field docstrings), _v0_3_to_v0_4.py (module docstring + MANUAL), _item.py (field docstrings), _results.py (ReflogEntry). No tamper-evidence or enforcement claim found anywhere.
<!-- sq:discussion:end -->
