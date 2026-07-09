---
id: TASK-343
sequence_id: 343
type: task
title: Bug severity data migration extra->top-level; SCHEMA_VERSION 0.8
status: Done
parent: FEAT-327
author: tech-lead
refs:
- ADR-323
- TASK-341:depends-on
description: 'First 0.8 change: _v0_7_to_v0_8 runner + registry + manual + SCHEMA_VERSION
  0.7->0.8; frozen vocab; one-way'
subentities:
- local_id: ST1
  title: _v0_7_to_v0_8 runner + registry + manual + SCHEMA_VERSION 0.7->0.8 bump
  status: Done
  story: US3
created_at: '2026-07-09T08:20:11Z'
updated_at: '2026-07-09T13:55:41Z'
---
<!-- sq:body -->
## Scope

Ship the one-way data migration that moves item-level bug severity from
`extra[X.SEVERITY]` to the top-level `severity:` frontmatter key for every
existing bug, and **own the `SCHEMA_VERSION` 0.7 -> 0.8 bump** that goes with
it. Delivers US3.

## CRITICAL — this is the FIRST 0.8 schema change on the release line

FEAT-326 did **not** bump `SCHEMA_VERSION`: the prefix-line normalization that
was going to carry a 0.7 -> 0.8 bump was reverted, because the prefix is now
**derived from the persisted id** and needs no migration (see the FEAT-326
close). `SCHEMA_VERSION` therefore still reads `"0.7"` (verified in
`_models/_schema.py`). Unlike the prefix case, this change **moves persisted
data** (severity out of `extra` into a top-level key), so it genuinely needs a
shipped, ordered migration.

**This task OWNS, as the first 0.8 change:**
- the `SCHEMA_VERSION` `"0.7"` -> `"0.8"` bump in `_models/_schema.py`;
- a new ordered runner `_migrations/_v0_7_to_v0_8.py` with
  `migrate(paths) -> int` + a `MANUAL` runbook string;
- its `Migration` record wired into `_migrations/_registry.py::MIGRATIONS`
  (`to_schema = "0.8"`), running through `sq migrate up` then `repair` + stamp.

## Areas / files

- `_migrations/_v0_7_to_v0_8.py` — for each bug `.md` file, move the severity
  value from the legacy `extra[X.SEVERITY]` (the body/`extra` `:meta` location
  `_meta_compat.py` handles) to a top-level `severity:` frontmatter key, and
  drop the `extra` entry. **One-way.** Only bug item files carry item-level
  severity; finding severity (already `severity:` in the sub-entity block) and
  priority (already top-level) are untouched — do not walk them.
  - **Freeze the vocabulary point-in-time.** The runner inlines the severity
    codes it needs as **frozen local constants** — it must NEVER read the live
    spec or any collection (which a project can rename/re-badge after this
    migration ships). A migration transforms files as they were at the version
    it targets; its vocabulary is pinned, not re-derived. This mirrors
    ADR-322's migration-freeze discipline.
  - The runner only relocates the stored **code** string; it does not validate
    it against a collection (that is the load-boundary's job) and does not
    touch label/emoji.
- `_migrations/_registry.py` — add the `Migration` record (`version`,
  `to_schema = "0.8"`, `run = _wrap_sync(_v0_7_to_v0_8.migrate)`,
  `manual = _v0_7_to_v0_8.MANUAL`) after the `_v0_5_to_v0_7` entry.
- `_models/_schema.py` — `SCHEMA_VERSION = "0.8"`.
- `MANUAL` runbook string — describe the extra -> top-level severity move for
  operators (what changes on disk, that it's automatic, and the one-line
  what-if-you-hand-edited note), consistent with the existing runners' manual
  entries. Also add the changelog index entry per the `sq migrate` runbook.

## Done criteria

- `SCHEMA_VERSION` is `"0.8"`; the root CLI callback's current-schema gate
  passes only after `sq migrate up` on a 0.7 squad.
- `sq migrate up` on a squad with pre-migration bugs (severity in
  `extra[X.SEVERITY]`) moves every bug's severity to the top-level `severity:`
  key, leaving priority and finding severity untouched; `sq check` and
  `sq repair` are clean after.
- The runner uses inline frozen local constants for its severity vocabulary,
  never the live spec.
- A migration test reproduces the move on a fixture 0.7 squad and asserts the
  resulting frontmatter (top-level `severity:`, no `extra` severity, values
  preserved exactly).
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean;
  full suite green.

## Sequencing note

Depends-on the enum-deletion/generic-storage task: the model there already
reads/writes top-level `severity:` and tolerantly backfills the legacy `extra`
location at load, so this migration normalizes disk to match a model that
already understands both. Lands **last** on the feature (it stamps the 0.8
schema). Independent of the CLI task — can land before or after it. Coordinate
the changelog/manifest bookkeeping with the release owner (Pierre owns the tag;
agents only prep).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 343 add-subtask "<title>"`; track with `sq task 343 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | _v0_7_to_v0_8 runner + registry + manual + SCHEMA_VERSION 0.7->0.8 bump | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — _v0_7_to_v0_8 runner + registry + manual + SCHEMA_VERSION 0.7->0.8 bump

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Bug severity migration preserves data
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add _v0_7_to_v0_8.py (bug extra[X.SEVERITY] -> top-level severity:, one-way, frozen vocab), wire the Migration record into MIGRATIONS (to_schema 0.8) with MANUAL runbook + changelog index, and bump SCHEMA_VERSION 0.7->0.8. First 0.8 change on the line.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T13:26:34Z] Elias Python:
  - Shipped the runner: src/squads/_migrations/_v0_7_to_v0_8.py walks only bugs/*.md, relocates extra[severity] to a top-level severity: key verbatim (one-way, idempotent, never overwrites an already-set top-level value), drops the extra entry (and the whole extra map if it was the only member); no vocab lookup — the two literals (bug folder/prefix, legacy extra key) are frozen locals.
  - Registry + schema: wired as the last Migration record (to_schema=0.8) in _migrations/_registry.py with a MANUAL runbook; bumped SCHEMA_VERSION 0.7->0.8 in _models/_schema.py. pyproject package version untouched.
  - Tests: tests/test_bug_severity_migration.py (relocate+drop-extra, keeps sibling extra keys, noop when no legacy severity, never overwrites an existing top-level value, leaves findings/priority/other types untouched); new tests/fixtures/corpus/v0_8 fixture (built by running sq migrate up on a v0_7 copy with a legacy extra.severity bug added) wired into test_migration_corpus.py's _CORPUS_CASES; test_session_lineage.py's schema-version assertion and applied-migration count/order updated (0.8, 4 migrations); tests/goldens/reflog_shape.json's schema_version bumped.
  - Dogfood squad migrated: sq migrate up on this repo's own squad moved BUG-11 and BUG-183's severity out of extra onto the top-level key (only textual diff on those two files: 'extra:\n  severity: medium' -> 'severity: medium'); .squads.json items are byte-identical (the model already normalized severity in memory pre-migration) — only its schema_version stamp and .squads.toml's schema_version changed. sq check clean before/after (only pre-existing unrelated advisories); sq repair clean.
  - Gates: pyright/ruff check/ruff format clean; test_squad_ref_hygiene green; targeted suite (bug-severity migration, migrations, corpus, session_lineage, unpadded-id migration, load-boundary vocab, skill migration, reflog) green. Manually verified sq migrate up + sq repair + sq check on both the dogfood squad and a fresh scratch squad end-to-end (fresh squad inits straight at 0.8; sq migrate up on it is a correct no-op).
  - Unverified by me: the full suite — leaving that to the main loop per instructions.
- [2026-07-09T13:35:39Z] Paul Reviewer:
  - APPROVE (independent review, TASK-343 uncommitted diff on release/0.8). Migration correctness, schema bump, dogfood, corpus/goldens, and hygiene all verified. Gates re-run clean: pyright 0/0, ruff check + format clean; targeted suite 66 passed (bug-severity migration, migrations, corpus, session_lineage, load_boundary, ref-hygiene). Full suite left to main loop per brief.
  - Migration correctness: _v0_7_to_v0_8.migrate relocates extra[severity]->top-level severity: for bugs only (walks bugs/*.md), never clobbers an existing top-level value (if not fm.get('severity')), drops the extra entry and the whole extra map only when severity was its sole key, preserves sibling extra keys, is idempotent (2nd run = 0), no-ops on bugs without legacy severity, leaves findings/priority/non-bug types untouched. Frozen point-in-time: local _BUG_PREFIX/_BUG_FOLDER/_LEGACY_EXTRA_KEY, no live-spec read. The 'already top-level + stale extra copy' case correctly keeps the canonical top-level value and discards the stale extra copy — matches _read_severity's top-level-wins precedence, so no loss of the authoritative value. Body preserved verbatim (replace_frontmatter).
  - Schema bump: SCHEMA_VERSION='0.8'; Migration record wired LAST (from_schema 0.7 -> to_schema 0.8). Verified end-to-end on a scratch v0_7 copy with an injected legacy extra.severity+sibling: migrate moved severity to top-level, kept the sibling extra key, stamped 0.8, sq check + sq repair clean, re-run is 'already at schema v0.8; nothing to migrate'. Fresh sq init lands directly at 0.8; migrate up there is a no-op. pyproject package version untouched (still 0.7.0).
  - Dogfood minimal + lossless: semantic (parsed) diff of squads/.squads.json shows the ONLY item-content change is TASK-343's own status bookkeeping (Draft->InReview, ST1 Todo->Done); BUG-11 and BUG-183 index entries are byte-identical (model already normalized severity in memory). On disk the two bugs' severity relocated cleanly (extra:\n  severity -> severity). Heads-up (informational, not a defect): the raw .squads.json diff is ~1218 lines but is PURE reordering churn from migrate's repair step (same item keyset before/after) — repair also reconciled pre-existing committed-but-unindexed backlog items. Noisy but correct; the eventual committer should know it's a rebuild, not new data.
  - Corpus + goldens: v0_8 fixture is genuine migrate output (v0_7 shape + injected legacy severity, then sq migrate up; schema 0.8, bug severity top-level, findings keep their own severity), wired into _CORPUS_CASES; test_session_lineage now asserts 4 applied migrations with correct from/to including 0.7->0.8 and SCHEMA_VERSION=='0.8'; reflog_shape golden bumped to 0.8; all historical corpus/migration tests reproduce green.
  - Release-owner note (informational): the 'sq migrate up' completion hint prints 'sq migrate chlog v0.7.0..v0.7.0' because that span is keyed on the package version (correctly left at 0.7.0), so the 0.8 MANUAL entry only surfaces via chlog once pyproject bumps to 0.8.0 at release. Pre-existing release-gating, consistent with 'agents prep, Pierre owns the tag' — verified the 0.8.0 entry renders correctly via 'sq migrate chlog v0.7.0..v0.8.0'.
<!-- sq:discussion:end -->
