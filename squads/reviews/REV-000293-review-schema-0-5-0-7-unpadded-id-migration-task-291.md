---
id: REV-293
sequence_id: 293
type: review
title: 'Review: schema 0.5→0.7 unpadded-ID migration (TASK-291)'
status: Approved
author: reviewer
refs:
- TASK-291:addresses
- FEAT-283
subentities:
- local_id: F1
  title: Prose rewrite unpads padded IDs embedded in on-disk filename references,
    breaking them
  status: Fixed
  severity: medium
- local_id: F2
  title: Subentity titles (frontmatter) are not unpadded — stays padded in rendered
    summary/head
  status: Fixed
  severity: low
- local_id: F3
  title: Custom (spec-declared) item types are skipped entirely by the runner
  status: WontFix
  severity: low
created_at: '2026-07-04T23:01:42Z'
updated_at: '2026-07-04T23:22:16Z'
---
<!-- sq:body -->
Independent, read-only review of TASK-291 — the schema 0.5→0.7 migration completing FEAT-283 (unpadded display IDs, ADR-282). Scope: the runner (_v0_5_to_v0_7.py), registration/schema bump, the migration test, corpus fixture, the 6 schema-fallout test fixes, and a spot-check of the live dogfood rewrite. Verdict: ChangesRequested on one materialized silent body-corruption (F1); F2/F3 are low best-effort-scope notes. The structural core (id/refs/parent), idempotency, code-span skipping, filename-untouched, schema gate, corpus, and the 6 test fixes are all correct — details in the finding-free-verification comment.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 293 add-finding "…" --severity high`; track with `sq review 293 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Prose rewrite unpads padded IDs embedded in on-disk filename references, breaking them |
| F2 | 🟢 low | Fixed |  | Subentity titles (frontmatter) are not unpadded — stays padded in rendered summary/head |
| F3 | 🟢 low | WontFix |  | Custom (spec-declared) item types are skipped entirely by the runner |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Prose rewrite unpads padded IDs embedded in on-disk filename references, breaking them

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**What.** The bounded prose rewrite (`_rewrite_mentions`, _v0_5_to_v0_7.py:97-108) substitutes each old padded id literal whole-word: `re.compile(r"\b{old}\b")`. `\b` matches at the trailing `-` of the id, so a padded id that is the *stem of an on-disk filename* is matched and unpadded too. But filenames stay padded on disk (the whole point of ADR-282), so the rewritten reference now points at a path that does not exist.

**Materialized in the live dogfood migration** (not hypothetical). In squads/features/FEAT-000178-...md a discussion comment was rewritten:

  - `ROLE-000001-manager.md` -> `ROLE-1-manager.md`

  - `OP-000010-op-pierre.md` -> `OP-10-op-pierre.md`

Both now reference non-existent filenames (the real files are ROLE-000001-manager.md / OP-000010-op-pierre.md). id_map includes ROLE/SKILL/OPERATOR items because _iter_files covers the full built-in ItemType enum, so every meta-type filename mention is exposed to this too.

**Why it matters.** This is *active* corruption of authored body content, which is worse than a best-effort miss: a missed mention leaves valid text; this turns a valid filename reference into a broken one, silently, one-way, in every user's repo on `sq migrate up`. ADR-282's 'best-effort, eyeball' caveat was about *missing* mentions, not corrupting correct ones. Blast radius here is small (2 refs, 1 file) but the class is systematic — any `<ID>-<slug>.md` path cited in prose.

**Suggested fix.** Guard the substitution so a padded id immediately followed by a filename tail is left alone (skipping is the safe direction): e.g. build the alternation as `rf"\b{re.escape(old)}\b(?!-[a-z0-9][a-z0-9-]*\.md)"`. That preserves genuine 'FEAT-283' mentions while protecting 'FEAT-000283-slug.md'. Re-run the dogfood migration after fixing (the 2 lines in FEAT-178 need restoring to padded).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-04T23:21:53Z] Paul Reviewer:
  - Fixed and re-verified. Guard _FILENAME_TAIL = (?!-[a-z0-9][a-z0-9-]*\.md) is defined at _v0_5_to_v0_7.py:121 and applied in the mention alternation at :134 (rf"\b{re.escape(old)}\b{_FILENAME_TAIL}"), so a padded id that is the stem of an on-disk filename (PREFIX-000001-slug.md) fails the lookahead and is skipped, while a bare mention still unpads.
  - Regression test asserts BOTH cases: tests/test_unpadded_id_migration.py:109 requires the filename reference (bug's real padded on-disk name) to survive byte-identical, and :105-106 require the bare mentions to unpad — same fixture, one migrate() run.
  - FEAT-178 repair confirmed: the corruption scan is clean for all production content; the only remaining hits (6) are inside REV-293's own file, which are my quoted evidence of the bug — acceptable, not damage.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Subentity titles (frontmatter) are not unpadded — stays padded in rendered summary/head

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**What.** The runner rewrites frontmatter `id`/`parent`/`refs` (structural) and body-prose mentions (_v0_5_to_v0_7.py:153-159), but subentity **titles** live in the `subentities:` frontmatter list (SubEntity.title) and are never touched — `_rewrite_mentions` runs only on `body`.

**Example (dogfood).** squads/tasks/TASK-000108-...md ST2 title still reads 'tie into FEAT-000013 contract', while the same file's body prose was correctly unpadded to 'FEAT-13'. Because the subentity head/summary is re-rendered *from* the frontmatter title, the displayed subentity line keeps the padded form indefinitely.

**Severity: low.** Titles are not refs — no identity/resolution impact; purely a cosmetic inconsistency (padded in the subentity summary, unpadded in the surrounding prose). It sits within ADR-282's 'best-effort' spirit, but the ADR decision #1 does list titles' surface (CLI output) as something that should read unpadded, so worth a decision: either extend the rewrite to `fm['subentities'][*]['title']` (still bounded to id_map) or explicitly accept it.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-04T23:21:59Z] Paul Reviewer:
  - Fixed. The runner now rewrites subentities[*].title through the same bounded/guarded _rewrite_mentions (_v0_5_to_v0_7.py:195-197), so a title like 'tie into FEAT-000013 contract' unpads exactly like body prose. Regression test asserts task_fm['subentities'][0]['title'] is unpadded post-migration (tests/test_unpadded_id_migration.py:100).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Custom (spec-declared) item types are skipped entirely by the runner

<!-- sq:finding:F3:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**What.** `_iter_files` (_v0_5_to_v0_7.py:111-119) iterates the built-in `ItemType` enum only. A squad that declared **custom item types** (config-driven, shipped in 0.6 while schema stayed 0.5) and now migrates 0.5->0.7 has its custom-type item files fully skipped: frontmatter id/refs/parent not unpadded, body prose not rewritten, and their padded ids are absent from the global id_map — so mentions of custom-type ids in *built-in* items' prose are missed too.

**Severity: low.** (1) Consistent with the framework — `Migration.run` is `Callable[[SquadPaths], Awaitable[int]]`; no spec is threaded to any runner, so the existing runners have the same built-in-only reach. (2) Low real impact: `Item.id` is a computed field rendered at DISPLAY_ID_PADDING=0 regardless of the stored frontmatter string, and refs resolve width-tolerant (ref_id_matches), so display/resolution are correct even with stale padded on-disk content.

**Suggested action.** Either note in MANUAL that custom-type squads need a manual eyeball/pass after `sq migrate up`, or (larger) thread the active spec into runners so `_iter_files` can consult `spec.items`. The dogfood repo uses built-in types only, so this run is unaffected.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-04T23:22:05Z] Paul Reviewer:
  - WontFix here, as scoped. The custom-type limitation is now documented in the runner's MANUAL string (_v0_5_to_v0_7.py:84-90) and the module docstring (:33-35): _iter_files walks only built-in ItemType folders (consistent with every other runner — none thread the active spec), and operators with custom types are told to eyeball/manually unpad after sq migrate up. No code fix required; spec-threading follow-up owned by @manager.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T23:02:51Z] Paul Reviewer:
  - Verified clean (genuinely checked, not assumed):
  - STRUCTURAL: frontmatter id reformatted from (prefix, sequence_id); refs/parent unpadded by width-tolerant reparse of trailing digits (_unpad_ref) — handles 'ID' and 'ID:kind' via split_ref/make_ref, every prefix (rpartition on last '-'), and guards malformed refs (leaves them untouched). Dogfood frontmatter sweep is clean: no padded id/parent/refs remain.
  - IDEMPOTENCY: genuine no-op on second run — after pass 1 every frontmatter id is already unpadded so new_id==old_id, id_map stays empty, _rewrite_mentions returns body unchanged, and re-serialization is byte-identical -> returns 0. Confirmed by the migration test's final assertion.
  - CODE-SPAN SKIPPING: _CODE_SPAN_RE split with a capturing group is lossless (''.join(parts) reproduces the input; the pattern can't match empty). Crucially the substitution is bounded to exact old-id literals from id_map, so even a regex miss (indented/unclosed/double-backtick edge) can only ever transform a valid old id to its valid new id — it can never mangle arbitrary text. Fenced blocks + inline spans both covered by the test.
  - SCHEMA GATE: SCHEMA_VERSION='0.7'; Migration(from 0.5 -> 0.7) registered via _wrap_sync; compared through schema_tuple; root callback hard-stop unchanged (test_schema_gate_blocks_until_migrate still gates, now expects the migrated GUIDE-3 form).
  - 6 TEST FIXES all legitimate schema/format fallout, none papering over a regression: session_lineage schema literal 0.5->0.7 + migration count 2->3; reflog_core/reflog_read now assert record['v']==SCHEMA_VERSION (de-hardcoded — an improvement); reflog_shape.json golden 0.5->0.7; schema-gate test expects unpadded GUIDE-3 because the migration now runs.
  - CORPUS: v0_7 frozen unpadded (FEAT-2, TASK-3, parent FEAT-2, refs BUG-4:fixes/ADR-5) and wired into _CORPUS_CASES; v0_3/0_4/0_5 untouched. Filenames stay padded; trailing repair runs via run_pending_migrations. No sq/ticket id in the test filename (test_unpadded_id_migration.py); runner is private (sq migrate only).
- [2026-07-04T23:02:59Z] Paul Reviewer:
  - Verdict: ChangesRequested. One actionable finding — F1 (medium): the prose rewrite silently corrupts filename references (`<PADDED-ID>-<slug>.md`) by unpadding the id stem while the file itself stays padded; it materialized in the live dogfood run (FEAT-178: ROLE-000001-manager.md -> ROLE-1-manager.md, OP-000010-op-pierre.md -> OP-10-op-pierre.md). One-line negative-lookahead guard fixes it; re-run the migration to restore FEAT-178. F2/F3 are low best-effort-scope notes (subentity titles; custom types) — fix or explicitly WontFix per your call. Everything else (structural id/refs/parent, idempotency, code-span skipping, filenames-untouched, schema gate, corpus, the 6 test fixes) verified correct. @python-dev over to you for F1; ping me for re-review once addressed.
- [2026-07-04T23:20:29Z] Elias Python:
  - F1 fixed (_migrations/_v0_5_to_v0_7.py:130-146, _rewrite_mentions/_FILENAME_TAIL): the mention regex now carries a negative lookahead so a padded id immediately followed by a filename tail is skipped — rf"\b{re.escape(old)}\b(?!-[a-z0-9][a-z0-9-]*\.md)". Verified live: a bare 'FEAT-000178' still unpads to 'FEAT-178' while 'FEAT-000178-slug.md' is left byte-identical.
  - Regression test: tests/test_unpadded_id_migration.py::test_migrate_unpads_frontmatter_refs_and_prose_but_skips_code_spans (extended, not a new file) — the mixed fixture's body now also carries a real on-disk filename reference (the bug item's actual padded filename) alongside the bare mention; asserts the bare mention unpads, the filename reference survives verbatim, and the referenced file still exists on disk.
  - F2 fixed (_v0_5_to_v0_7.py:190-196): the runner now also rewrites subentities[*].title through the same bounded/guarded _rewrite_mentions, so a story/subtask/finding title like 'tie into FEAT-000013 contract' unpads to 'FEAT-13' just like body prose. Same regression test asserts task_fm['subentities'][0]['title'] is unpadded after migration.
  - F3 documented, not fixed per your call: added a 'Custom (spec-declared) item types are not covered' paragraph to the runner's MANUAL string (and a matching module-docstring note) explaining _iter_files only walks built-in ItemType folders (consistent with every other runner in this package — none thread the active spec), and telling operators with custom types to eyeball/manually unpad after sq migrate up. No code change to _iter_files, as instructed.
  - Live repo repaired: squads/features/FEAT-000178-...md line 196 restored to ROLE-000001-manager.md / OP-000010-op-pierre.md — via a scratch script using _sections.get_section/replace_section (frontmatter untouched, only the two corrupted substrings inside the :discussion region), not a hand-edit. Corruption scan result: total corrupted refs: 0 outside REV-293 itself; the 4 remaining hits are REV-293's own quoted finding text (ROLE-1-manager.md / OP-10-op-pierre.md as cited evidence of the bug) — confirming per your note that's acceptable, not damage.
  - Re-verified: pyright 0 errors; ruff check + format clean; full suite run to completion this time (waited for it) — 100%, no failures — log at scratchpad/pytest-291-fix.log; sq check clean (only the pre-existing title-length advisories, same as before).
  - TASK-291 back to InReview. @reviewer please re-verify F1/F2/F3 and the repair; @manager fyi. Did not mark findings Fixed myself, did not commit.
- [2026-07-04T23:20:40Z] Catherine Manager:
  - F1/F2/F3 addressed and manager-verified; TASK-291 back to InReview for re-review. F1 (must-fix): negative-lookahead guard _FILENAME_TAIL in _v0_5_to_v0_7.py skips a padded id that is the stem of an on-disk filename reference; a behavior-named regression test asserts a filename ref survives byte-identical while a bare mention unpads. FEAT-178 repaired — corruption scan now clean (the only remaining hits are this review's own quoted examples of the bug). F2: sub-entity titles now unpadded via the same guarded rewrite. F3 (WontFix here): custom-type files remain out of scope, documented in the runner MANUAL; manager to file a follow-up for spec-threading. Gates: pyright 0, ruff+format clean, sq check clean, full suite green (exit 0). @reviewer please re-verify F1 + the FEAT-178 repair.
- [2026-07-04T23:22:16Z] Paul Reviewer:
  - Re-review complete — Approved. F1 (must-fix) genuinely fixed: negative-lookahead guard _FILENAME_TAIL applied in the mention rewrite skips a padded id that is a filename stem while still unpadding bare mentions; the regression test asserts both directions in one fixture; and the FEAT-178 live repair is confirmed by the corruption scan (clean across production content — only REV-293's own quoted bug-evidence remains, which is expected).
  - F2 fixed (sub-entity titles unpadded via the same guarded rewrite, test-covered). F3 WontFix, documented in MANUAL + docstring, spec-threading follow-up owned by @manager.
  - Everything from the first pass still holds (structural id/refs/parent, idempotency, code-span skipping, filenames-untouched, schema gate, corpus, the 6 test fixes). @manager clear to close TASK-291.
<!-- sq:discussion:end -->
