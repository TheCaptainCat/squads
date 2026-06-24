---
id: REV-000191
sequence_id: 191
type: review
title: 'Foundation review: FEAT-178 skills (TASK-187/188)'
status: Approved
author: reviewer
refs:
- FEAT-000178
- TASK-000187
- TASK-000188
subentities:
- local_id: F1
  title: Regen else-branch wipes frontmatter when body region is missing/partial
  status: Open
  severity: medium
- local_id: F2
  title: 'sq check: skills added to registered-authors set is an out-of-scope semantic
    change'
  status: Open
  severity: low
- local_id: F3
  title: Existing test suite runs the non-default no-seed path; default seed-on-init
    under-tested
  status: Open
  severity: low
- local_id: F4
  title: sq adopt does not seed bundled skills; init/adopt asymmetry
  status: Open
  severity: low
- local_id: F5
  title: Counter bump before file write can leak an id on stamp failure
  status: Open
  severity: low
created_at: '2026-06-24T19:49:42Z'
updated_at: '2026-06-24T20:00:55Z'
---
<!-- sq:body -->
## Scope

Independent review of the FEAT-000178 FOUNDATION increment: TASK-000187 (frontmatter-preserving, marker-safe skill-body regen) + TASK-000188 (lexical-by-slug SKILL id allocation shared by init seeding + the future migration, and sq init seeding). Reviewed against the Accepted ADR-000181 contract. Implementation is uncommitted in the working tree; reviewer did not author it.

## Verdict: APPROVE-WITH-NITS

The increment meets the ADR contract. The riskiest change (decision #3 / #4 — making skill-body regen frontmatter-preserving and sync idempotent) is implemented correctly on the happy path and proven by a dedicated double-sync idempotence test that asserts id/sequence_id are unchanged. Allocation is a single shared lexical-by-slug primitive (interactions.bundled_skill_slugs) consumed by both init seeding and — per design — the future migration, satisfying decision #5's ordering-parity intent. Seeding is idempotent (decision #4): re-seeding returns an empty list and never reallocates, with a test to match.

Invariants hold: ids are allocated only inside IndexStore.transaction() (single global counter, invariant 2); frontmatter is the source of truth and repair round-trips (test_repair_after_seeding_rebuilds_cleanly); edits go through _sections marker-safe helpers (invariant 3); .claude/ stays pointers (invariant 5); backend work goes through the ABC; clock.now() is used, not datetime.now(); no 'from __future__ import annotations'. pyright strict, ruff check, ruff format and the full suite are all green.

## Why not a clean APPROVE

One MEDIUM latent edge (F1): the regen else-branch blunt-overwrites the whole file — including stamped frontmatter — when a file has frontmatter but a missing/partial sq:body region. This is precisely the identity-loss decision #3 guards against; it is unreachable on the normal flow but should fail safe by preserving frontmatter unconditionally when present. Plus four LOW notes: an out-of-scope sq check author-validation widening (F2), thin coverage of the default seed-on-init path because the suite was flipped to --no-seed-skills (F3), init/adopt seeding asymmetry (F4), and a non-transactional counter bump vs file write (F5).

None of the LOW items block. F1 is a fail-safe hardening I recommend before this ships, but it does not affect correctness on any exercised path — hence APPROVE-WITH-NITS rather than CHANGES-REQUESTED. If the team prefers the regen path to be provably safe under a corrupted body region, fixing F1 would lift this to a clean approve.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 191 add-finding "…" --severity high`; track with `sq review 191 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Open |  | Regen else-branch wipes frontmatter when body region is missing/partial |
| F2 | 🟢 low | Open |  | sq check: skills added to registered-authors set is an out-of-scope semantic change |
| F3 | 🟢 low | Open |  | Existing test suite runs the non-default no-seed path; default seed-on-init under-tested |
| F4 | 🟢 low | Open |  | sq adopt does not seed bundled skills; init/adopt asymmetry |
| F5 | 🟢 low | Open |  | Counter bump before file write can leak an id on stamp failure |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Regen else-branch wipes frontmatter when body region is missing/partial

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
File: src/squads/_backends/_claude_code/_backend.py:132-145 (_write_managed_skill).

The body-region regen guards on `if fm and sections.has_section(existing, markers.BODY)`. When that condition is FALSE the else-branch does `await _aio.write_text(body_path, body_with_markers)` — a full-file overwrite that discards any existing frontmatter.

The dangerous case is a file that HAS stamped frontmatter (a real SKILL id) but whose body region is absent or has a partial/garbled marker pair (has_section needs BOTH the open and close marker present). In that state a single sq sync silently overwrites the file with a bare body and NO frontmatter, destroying the id/sequence_id — exactly the identity loss ADR-000181 decision #3 exists to prevent. The happy path is safe (init writes markers, then stamps fm, so both are present — the idempotence test passes), so this is a latent edge, not a routine failure.

Recommended fix: when frontmatter is present, never blunt-overwrite. Re-emit preserved frontmatter + the freshly-rendered body-with-markers via join_frontmatter(fm, body_with_markers) (the 'round-trip through preserved frontmatter' form the ADR describes). That repairs a missing body region instead of nuking identity. Reserve the bare body_with_markers write for the genuinely-unstamped case (no fm).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — sq check: skills added to registered-authors set is an out-of-scope semantic change

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
File: src/squads/_services/_maintenance.py:615-619 (_check_items).

This increment adds ItemType.SKILL to the 'registered' set used to validate item.author/assignee, so a skill's own slug now counts as a registered author. The visible effect is in tests/goldens/check_squad.json: the previously-asserted warning "author 'golden-skill' is not a registered agent or operator" is now gone.

Assessment: this is arguably CORRECT and consistent — roles and operators were already in the set, all meta-types self-author (see _roster.py:42/71/105/128: 'a skill authors itself'), and seed_bundled_skills sets author=slug. Without this change every seeded skill would warn. So I am not asking to revert it.

The concern is scope/transparency: it is a behavior change to sq check semantics bundled into a 'foundation' increment for 187/188, and it silently removes a warning a golden test used to assert. The warning message still reads 'agent or operator' while skills are neither. Action: keep the change but (a) note it explicitly in the task/commit, and (b) consider widening the message wording (e.g. 'registered agent, operator, or skill') so the check's intent stays honest. Low severity.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Existing test suite runs the non-default no-seed path; default seed-on-init under-tested

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Files: tests/conftest.py (project fixture now passes _skip_skill_seed=True) + ~17 test files sprinkled with 'init --no-seed-skills'.

The shared 'project' fixture and the bulk of the CLI suite now exercise init WITH seeding disabled. That means the production default (sq init seeds skills) is only covered by tests/test_skill_seeding.py and 3 CLI smoke tests; the rest of the suite runs a path real users will not hit.

This is a defensible call — seeding consumes global-counter values, so leaving it on would shift every downstream id (FEAT-000002, TASK-000003, …) and force a much larger, noisier golden/assertion rewrite. The dev chose minimal churn. It does NOT paper over a behavior change (the seeding is genuinely new and gated), but it does leave the default path thin on coverage.

Recommendation (non-blocking): keep the flag, but flip at least one or two representative end-to-end CLI tests to the seeded default so the real init path has regression coverage beyond the dedicated suite, and add a comment in conftest pointing to the seeded fixture as the canonical default. The _skip_skill_seed hook is correctly hidden and documented as test-only.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — sq adopt does not seed bundled skills; init/adopt asymmetry

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
File: src/squads/_services/_service.py — init() (line ~98) calls seed_bundled_skills(); adopt() (line ~160) calls refresh_managed() but NOT seed_bundled_skills().

Effect: a freshly init'd squad carries stamped SKILL ids; an adopt'd squad has bundled skill body files with sq:body markers but no frontmatter/ids until 'sq migrate up' runs. repair()/check() correctly skip slug-named unstamped skill files (the _iter_item_files / _disk_state / check changes handle this with no error), so this does not break anything today.

This is likely intentional given the migration (TASK-189) is the seam that stamps existing squads, and is out of this increment's scope. Flagging only so it is a conscious decision and gets a test/doc note: confirm adopt is meant to defer to migrate, and that an adopt'd-then-never-migrated squad with unstamped skills is an acceptable interim state. Low severity.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Counter bump before file write can leak an id on stamp failure

<!-- sq:finding:F5:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
File: src/squads/_services/_maintenance.py:205-235 (seed_bundled_skills).

Inside the transaction, allocate_id() bumps the global counter, then the code builds the Item, renders frontmatter, and writes the file BEFORE db.add(item). If join_frontmatter/to_frontmatter_dict/write_text raised, the counter was already incremented — leaving a one-off gap in the sequence (a skipped number). Not a correctness/idempotence bug (gaps are benign; the counter is monotonic, not dense) and the transaction would roll back the in-memory db, but the on-disk file write is not transactional with the counter.

Minor: consider building+validating the Item and rendering the frontmatter string before allocate_id, or doing db.add before the file write, so a render failure can't consume a counter value. Lowest severity — note only.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T19:51:07Z] Paul Reviewer:
  - VERDICT: APPROVE-WITH-NITS.
  - The 187/188 foundation meets ADR-000181. Happy-path regen is frontmatter-preserving and idempotent (double-sync test green), allocation is a single shared lexical-by-slug primitive, seeding is idempotent, invariants hold, full suite + pyright + ruff green.
  - 1 MEDIUM (F1, recommend before ship): _write_managed_skill else-branch overwrites the whole file — wiping stamped frontmatter — when a stamped file's sq:body region is missing/partial. Fail safe via join_frontmatter(fm, body_with_markers) when fm is present. Unreachable on the normal flow, so non-blocking.
  - 4 LOW notes (F2 sq check author-set widening = out-of-scope but reasonable; F3 default seed path under-tested after the --no-seed-skills flip; F4 adopt does not seed, init/adopt asymmetry; F5 counter bump precedes file write). None block.
  - @python-dev @tech-lead — F1 is the one worth addressing in this increment; the rest are notes for the record / TASK-189 (migration) follow-up. Not changing task or feature status.
- [2026-06-24T20:00:55Z] Catherine Manager:
  - F1 verified fixed (else-branch now re-emits frontmatter via join_frontmatter when present — confirmed at _backend.py). Idempotence re-checked on a clean init: ids unchanged across 2x sync, sq check green. F2/F4/F5 accepted as notes-for-record; F4 (adopt defers stamping to migration) is the intended interim state, addressed by TASK-189. Approving the foundation increment.
<!-- sq:discussion:end -->
