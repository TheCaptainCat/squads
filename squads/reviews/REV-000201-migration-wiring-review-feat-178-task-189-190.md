---
id: REV-000201
sequence_id: 201
type: review
title: 'Migration+wiring review: FEAT-178 (TASK-189/190)'
status: Approved
author: reviewer
refs:
- FEAT-000178
- TASK-000189
- TASK-000190
subentities:
- local_id: F1
  title: migrate chlog hint points at the wrong release range — 0.5 manual steps are
    unreachable
  status: Open
  severity: medium
- local_id: F2
  title: Interrupted migration can mint duplicate SKILL ids (counter persisted once
    at end, not per-allocation)
  status: Open
  severity: medium
- local_id: F3
  title: Dead/misleading manual .squads.json write in the runner — clobbered by the
    following repair()
  status: Open
  severity: low
- local_id: F4
  title: v0_5 corpus fixture is mislabeled — schema_version=0.4 on disk under a dir
    registered as 0.5
  status: Open
  severity: low
- local_id: F5
  title: _skip_skill_seed test hook is now load-bearing suite-wide; seeded state under-covered
    by default
  status: Open
  severity: low
created_at: '2026-06-24T20:32:56Z'
updated_at: '2026-06-24T21:09:52Z'
---
<!-- sq:body -->
## Scope

Independent review of the SECOND increment of FEAT-000178: TASK-189 (0.4->0.5 migration retrofitting SKILL ids onto existing agents/skills/*.md) and TASK-190 (user-facing wiring: sq skill show/refs/ref add/ref rm, SKILL ref support). Reviewed against the Accepted ADR-000181 contract. I previously reviewed the foundation (TASK-187/188) as REV-000191; this is a separate review of migration + wiring. Did not write the code.

## Verdict: APPROVE-WITH-NITS

The increment is well-built and conforms to the ADR-181 contract on every load-bearing point: skills are full Items on the meta-type profile (Active, no sub-entities); migration and init share the bundled_skill_slugs() lexical-by-slug ordering primitive so ordering parity (ADR #5) holds without asserting identical numbers; idempotence (ADR #4) is real (per-slug 'if fm.get(id): continue', verified at CLI + service level); the wiring goes through the service/ABC, uses split_ref/make_ref (no hand-parsing of ':'), special-cases nothing in the ref machinery, escapes console output with e(); check() correctly treats SKILL as a meta-type (no parent/subtask advisories). pyright + ruff clean; the 11 new tests cover stamping, idempotence, repair+check, ordering parity vs init, CLI migrate up, CLI no-op re-run, skill show (text+json), and ref round-trip in both directions. Live repro confirmed: a clean 0.4 squad migrates to 0.5, stamps both skills, lists them, passes check, and re-runs as a clean no-op.

## Why not a plain APPROVE

Two MEDIUM issues keep this short of clean-approve:

- **F1** the post-migrate 'manual steps remain' hint points at the WRONG chlog range (the new migration's version=0.5.0 is ahead of package __version__ 0.4.1), so the 0.5 MANUAL string is unreachable via the command the tool tells the user to run — reproduced live as 'sq migrate chlog v0.4.0..v0.4.1', which prints only the already-applied 0.3->0.4 steps. A release-engineering version bump (or aligning the migration's version) fixes it.
- **F2** the runner persists the index counter ONCE at the end of the stamp loop instead of per-allocation, so an interrupted-then-resumed migration can mint duplicate SKILL ids (repair then silently drops one on the seq-keyed index). The parallel seed_bundled_skills path does this correctly via IndexStore.transaction(); the runner should mirror it. F3 (the dead manual index write, clobbered by the following repair) is the same mechanism and removing it closes both.

None block correctness on the happy path, but F1 ships a broken user-facing runbook pointer for the very migration this increment adds, and F2 is a real integrity hazard the transaction pattern was designed to prevent. Recommend addressing F1+F2 before merge; F3-F5 are cleanups.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 201 add-finding "…" --severity high`; track with `sq review 201 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Open |  | migrate chlog hint points at the wrong release range — 0.5 manual steps are unreachable |
| F2 | 🟡 medium | Open |  | Interrupted migration can mint duplicate SKILL ids (counter persisted once at end, not per-allocation) |
| F3 | 🟢 low | Open |  | Dead/misleading manual .squads.json write in the runner — clobbered by the following repair() |
| F4 | 🟢 low | Open |  | v0_5 corpus fixture is mislabeled — schema_version=0.4 on disk under a dir registered as 0.5 |
| F5 | 🟢 low | Open |  | _skip_skill_seed test hook is now load-bearing suite-wide; seeded state under-covered by default |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — migrate chlog hint points at the wrong release range — 0.5 manual steps are unreachable

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**File:** src/squads/_migrations/_registry.py:58 (version="0.5.0") + src/squads/_cli/_migrate.py:49-53; src/squads/__init__.py:3 (__version__ = "0.4.1").

The new Migration record is stamped version="0.5.0" but the package __version__ is still 0.4.1. After 'sq migrate up', the hint at _migrate.py:50 builds span = f"v{config.squads_version}..v{__version__}". On a 0.4 squad that resolves to e.g. 'v0.4.0..v0.4.1'. 'sq migrate chlog' selects via version_tuple(lo) < version_tuple(m.version) <= version_tuple(hi) (_migrate.py:83), so the 0.5.0 migration falls ABOVE the upper bound and is filtered out — the user is told to run a chlog command that prints the 0.3->0.4 (already-applied) manual steps and OMITS the 0.5 SKILL-migration MANUAL string entirely.

Reproduced live: 'manual steps remain — read them with sq migrate chlog v0.4.0..v0.4.1', and that chlog shows only the session-lineage (0.4) steps.

The runner DID author a useful MANUAL (the 'missing skill body file -> run sq sync first' recovery), so it being unreachable matters. Fix: bump package __version__/pyproject to 0.5.0 in lock-step with this schema-introducing migration (then the span resolves to ..v0.5.0), or align the migration's version field with the actual shipping release. The hint logic itself is pre-existing; this increment surfaces the skew.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Interrupted migration can mint duplicate SKILL ids (counter persisted once at end, not per-allocation)

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**File:** src/squads/_migrations/_v0_4_to_v0_5.py:100-159 (the stamp loop; _write_index_sync at 158-159 runs ONCE after the loop).

The runner reads counter from .squads.json once (line 95), then in the loop does counter += 1 per skill and writes each stamped .md file immediately (line 134), but only persists the bumped counter to the index AFTER the whole loop (line 158). If the process dies mid-loop: the already-processed skill files carry ids N+1..N+k on disk, but .squads.json still has the OLD counter=N. On resume, 'sq migrate up' re-reads counter=N, skips the already-stamped files (fm.get('id') truthy), but allocates the remaining unstamped skills starting at N+1 again — COLLIDING with the ids already on disk. repair() then keys SquadsDB.add by sequence_id (_models/_index.py:93 self.items[item.sequence_id]=item), so two files sharing a seq silently overwrite — one skill disappears from the index. Violates the global-counter uniqueness invariant (CLAUDE.md #2) and bypasses 'Allocate only inside IndexStore.transaction()'.

The parallel path seed_bundled_skills (_services/_maintenance.py:212) does this correctly — allocates inside store.transaction() per skill, so each allocation is atomically persisted and resume cannot collide. Likelihood is low (single-process, ~9-file loop) but it's a real integrity defect the transaction pattern exists to prevent. Fix: reuse the transaction()/allocate_id path (mirror seed_bundled_skills), or persist the counter inside the loop per allocation.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Dead/misleading manual .squads.json write in the runner — clobbered by the following repair()

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**File:** src/squads/_migrations/_v0_4_to_v0_5.py:64-74 (_read_index_sync/_write_index_sync), 136-159 (raw['items'][...] mirror + _write_index_sync), and the module docstring lines 18-23.

run_pending_migrations (_services/_maintenance.py:160-164) calls m.run(paths) then immediately 'await self.repair()'. repair() rebuilds the index from frontmatter and sets db.counter = max(previous_counter, max_n) where max_n is computed from the stamped frontmatter ids found on disk (repair lines 312/301). Since the runner stamps id/sequence_id INTO the .md frontmatter, repair recovers the counter high-water mark from the files regardless. So the entire hand-rolled index read-modify-write (the raw['items'] dict mirroring + _write_index_sync) is dead — its effect is discarded by the repair that runs milliseconds later. The docstring justifies it as 'so the counter high-water mark is not lost between the stamp and the repair', which is incorrect (repair recovers it from frontmatter).

Beyond being dead, it's a second, non-locked, non-atomic index writer duplicating IndexStore for no net effect — and it is exactly what enables Finding F2's collision window. Removing the manual index write (stamp frontmatter only; let repair rebuild) both simplifies the runner and closes F2. Low severity because it is currently effect-neutral on the happy path.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — v0_5 corpus fixture is mislabeled — schema_version=0.4 on disk under a dir registered as 0.5

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**File:** tests/fixtures/corpus/v0_5/.squads.toml (schema_version = "0.4", squads_version = "0.4.0") + tests/test_migration_corpus.py:37 (registered as ("0.5", "v0_5")).

The fixture directory v0_5 is registered in _CORPUS_CASES as schema '0.5', but its .squads.toml on disk says schema_version = "0.4". The corpus harness contract (module docstring + fixtures/corpus/README.md) is 'one frozen squad per released schema version, captured at the schema version indicated by its directory name'. This fixture is actually a 0.4 squad carrying two unstamped skill body files (greeting.md, squads.md).

Functionally this is the lucky case — because it's at 0.4, run_pending_migrations fires the 0.4->0.5 runner, so the corpus test DOES exercise end-to-end stamping (verified: migrate up stamps both, schema -> 0.5, check green). And the v0_4 corpus has no agents/skills/ dir at all, so this mislabeled fixture is the ONLY corpus that exercises skill stamping. But: (a) the naming/contract is broken and will mislead the next schema bump, and (b) there is no genuine schema-0.5 corpus to guard the 'already current -> zero migrations' no-op path through the harness. Fix: either relabel/move this as the enriched 0.4 fixture (add skills to v0_4) and add a true 0.5 fixture, or stamp this one to a real 0.5 state. Low severity — tests pass today.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — _skip_skill_seed test hook is now load-bearing suite-wide; seeded state under-covered by default

<!-- sq:finding:F5:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**File:** src/squads/_services/_service.py:52 + tests/conftest.py:84-95 (project fixture now passes _skip_skill_seed=True); src/squads/_cli/_main.py:145-153 (hidden --no-seed-skills flag).

The internal _skip_skill_seed hook is now used by the default 'project' fixture, so the bulk of the suite runs against squads with UNSEEDED skills (no SKILL items). Only the dedicated test_skill_migration.py / test_skill_seeding.py cover the seeded state. This is a reasonable pragmatic choice (avoids re-baselining global-counter values across ~30 test files), but it makes the hook load-bearing suite-wide and leaves the production default path (init WITHOUT --no-seed-skills) thinly covered — a regression in seeding would only be caught by the few skill-specific tests rather than broadly. Also note there is no recovery path that re-stamps a squad created with --no-seed-skills once it is already at schema 0.5 (migration won't fire); it relies on a future seed/sync call. Nit: consider at least one broad fixture exercising the seeded default, and documenting the no-recovery edge. Not blocking.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T20:34:23Z] Paul Reviewer:
  - VERDICT: APPROVE-WITH-NITS. Migration + wiring conform to ADR-181 on every load-bearing point (meta-type profile, shared lexical ordering / ordering parity, idempotence, ABC/split_ref wiring, meta-type check handling); pyright/ruff clean; 11 tests + live repro green.
  - Two MEDIUM findings to address before merge: F1 — migrate-up hint points at the wrong chlog range (migration version 0.5.0 ahead of package __version__ 0.4.1), so the 0.5 MANUAL is unreachable (reproduced live as 'sq migrate chlog v0.4.0..v0.4.1'); fix by bumping the package version in lock-step. F2 — interrupted migration can mint duplicate SKILL ids because the index counter is persisted once after the loop, not per-allocation, bypassing IndexStore.transaction(); mirror seed_bundled_skills.
  - Three LOW/nit cleanups: F3 dead+misleading manual .squads.json write (clobbered by the following repair(); removing it also closes F2's window); F4 v0_5 corpus fixture mislabeled (schema_version=0.4 on disk under a dir registered as 0.5; no true 0.5 no-op corpus); F5 _skip_skill_seed hook now load-bearing suite-wide, seeded default under-covered. @tech-lead @python-dev for F1/F2.
- [2026-06-24T21:09:51Z] Catherine Manager:
  - F1-F4 all verified fixed. F2 (the integrity one): migration runner is now async and allocates each SKILL id inside IndexStore.transaction()/db.allocate_id() — confirmed in _v0_4_to_v0_5.py; manual index read/write helpers removed; invariant #2 honored. F1: __version__→0.5.0, chlog now surfaces the 0.5 MANUAL. F3: dead index write gone. F4: v0_5 corpus is now a genuine post-migration snapshot. Re-verified end-to-end on a simulated 0.4 squad: stamps 9 skills lexically, check green, idempotent re-run, ordering parity. Approving.
<!-- sq:discussion:end -->
