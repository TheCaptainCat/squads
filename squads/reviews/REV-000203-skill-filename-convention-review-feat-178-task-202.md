---
id: REV-203
sequence_id: 203
type: review
title: 'Skill filename convention review: FEAT-178 TASK-202'
status: Approved
author: reviewer
refs:
- FEAT-178
- TASK-202
subentities:
- local_id: F1
  title: Backend swallows index-corruption errors with bare except
  status: Open
  severity: low
- local_id: F2
  title: Orphan slug.md beside a convention file is never detected or cleaned
  status: Open
  severity: low
- local_id: F3
  title: Backend reaches into IndexStore directly (layering smell)
  status: Open
  severity: low
- local_id: F4
  title: Freshly-migrated unstamped skills get an empty pointer description
  status: Open
  severity: info
created_at: '2026-06-25T08:43:18Z'
updated_at: '2026-07-06T15:18:02Z'
---
<!-- sq:body -->
## Scope

Independent review of TASK-202 — renaming skill body files to the `agents/skills/SKILL-<NNNNNN>-<slug>.md`
convention (matching ROLE/OP) and keeping the `.claude` skill pointers in sync. Did not author the code
(prior reviews on this feature: REV-191, REV-201). Reviewed the backend (`_write_managed_skill` +
`generate_skill_entry` call), `seed_bundled_skills`, the `_v0_4_to_v0_5` migration, `_iter_item_files`,
the corpus fixture wiring, and the two test files.

## Verdict: APPROVE-WITH-NITS

The core is correct and idempotent. All three migration cases dispatch cleanly and mutually exclusively
(convention-exists → skip; stamped-but-slug-named → rename + path fix + pointer rewrite, no realloc;
unstamped → allocate-in-transaction + stamp + write + unlink + pointer rewrite). I independently confirmed:

- The **repo's own state** (stamped, slug-named, no `id_padding`) migrates correctly: all 9 files renamed,
  pointers resolve, `sq check` clean, no reallocation (probe replaying the exact repo frontmatter shape).
- **Allocation stays transaction-only** — both `db.allocate_id` calls are inside `async with store.transaction()`;
  REV-201 F2 did NOT regress.
- **No import cycle**: `_index` does not import `_backends`; pyright + ruff clean on all changed files.
- **Frontmatter-preserving regen holds** (REV-191 guarantee): the stamped-file branch of `_write_managed_skill`
  touches only the `sq:body` region via `replace_section`; the migration's stamped branch uses
  `replace_frontmatter` which preserves the body verbatim.
- **Pointer path parity** between init (`generate_skill_entry` → `ctx.root_relative`) and migration
  (`f"{squad_dir_rel}/{squad_rel}"`) — both resolve to `squads/agents/skills/SKILL-...md`.
- Calling `backend.generate_skill_entry` from `seed_bundled_skills` is **layering-clean** — it is a declared
  ABC method, invoked for **every** active backend via `self._backends()`.

The findings below are all low-severity robustness/cleanliness nits; none block. Tests cover all three
migration cases (incl. the repo's stamped-but-slug-named case), the init pointer-resolves assertion, and
double-sync filename stability.

## Tested

`tests/test_skill_migration.py`, `tests/test_skill_seeding.py`, `tests/test_migration_corpus.py`,
`tests/test_cli.py`, `tests/test_service.py` — all green. `sq check` on the live repo: 0 errors.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 203 add-finding "…" --severity high`; track with `sq review 203 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Backend swallows index-corruption errors with bare except |
| F2 | 🟢 low | Open |  | Orphan slug.md beside a convention file is never detected or cleaned |
| F3 | 🟢 low | Open |  | Backend reaches into IndexStore directly (layering smell) |
| F4 | 🔵 info | Open |  | Freshly-migrated unstamped skills get an empty pointer description |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Backend swallows index-corruption errors with bare except

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The backend's skill-writing path resolves IDs by reading the index, and wraps that read in a broad/bare `except` that swallows every error — including the `SquadsError` a corrupt index raises on load.

Impact (low): an index-corruption condition is masked here rather than surfacing as the intended hard-stop; the write silently skips or proceeds on incomplete data instead of failing loudly. Not reachable on the happy path exercised by this task, hence non-blocking.

Recommendation: narrow the catch to the expected lookup-miss case and let index-corruption / `SquadsError` propagate so the CLI's error handling reports it.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Orphan slug.md beside a convention file is never detected or cleaned

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The migration's "convention file already exists" branch skips cleanly (correct, idempotent), but it does not check for a leftover slug-named body file sitting beside the convention-named one. If both are present, the orphan `<slug>.md` is neither detected nor removed.

Impact (low): a stale orphan skill file can linger next to the canonical `SKILL-<NNNNNN>-<slug>.md`. It is inert (pointers resolve to the convention file), so this is cleanliness, not correctness — non-blocking.

Recommendation: in the skip branch, detect and `unlink` an orphan slug-named sibling so a partial/interrupted prior run self-heals on the next migrate.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Backend reaches into IndexStore directly (layering smell)

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
The skill backend reaches into `IndexStore` directly to resolve IDs rather than receiving a resolved value or going through the service layer. This crosses the intended `_cli → _services → (index store, backends)` layering, where backends are meant to be driven by the service, not to open the store themselves.

Impact (low): a layering smell, not a bug — it works and stays transaction-clean (verified: allocation remains inside `store.transaction()`, REV-201 F2 did not regress). It just couples the backend to the store's shape, making future store changes leak into backends.

Recommendation: have the service resolve the ID and hand the backend the value it needs, keeping the backend store-agnostic.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Freshly-migrated unstamped skills get an empty pointer description

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
In the unstamped-skill migration branch (allocate + stamp + write + unlink + pointer rewrite), the freshly written `.claude` pointer gets an empty description, whereas the init path populates it via `generate_skill_entry`. The two paths reach parity on file location but not on pointer description.

Impact (info): purely cosmetic — the pointer resolves correctly; only its human-readable description line is blank until the next `sq sync` regenerates it. No functional effect.

Recommendation: populate the description in the migration's unstamped branch from the same source the init path uses, so migrated pointers match init output without waiting for a resync.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T08:44:23Z] Paul Reviewer:
  - VERDICT: APPROVE-WITH-NITS. TASK-202 is correct and idempotent across all three migration cases, including this repo's own stamped-but-slug-named state (independently replayed: 9 files renamed, pointers resolve, check clean, no reallocation). Allocation stays transaction-only (REV-201 F2 not regressed), no import cycle, pyright/ruff/tests green, frontmatter-preserving regen (REV-191) intact, pointer paths parity between init and migration. Four low/info nits only — none blocking: (F1) bare except swallows index corruption in the backend; (F2) orphan slug.md after an interrupted rename is never detected/cleaned; (F3) backend reads IndexStore directly (layering smell); (F4) empty pointer description on freshly-migrated unstamped skills. Confirmed @tech-lead's verification (fresh-init pointers, migration rename+pointer+idempotence, double-sync stable, check green) — all hold. Recommend merging; F1/F2 are good cheap follow-ups.
- [2026-06-25T09:22:43Z] Catherine Manager:
  - Verified F1+F3 fixes hands-on. F3: backend no longer references IndexStore (skill paths now flow via BackendContext.skill_paths, resolved in _services); layering invariant restored. F1: the swallowing except is gone entirely. Re-verified end-to-end: fresh init → all 9 pointers resolve, 0 non-convention files; migrate up on a 0.4 squad → rename + pointer resolves + no realloc; double-sync filenames stable; check clean; pyright/ruff green. F2 (orphan slug.md on interrupted rename) and F4 (empty pointer description) accepted as documented nits. Approving.
<!-- sq:discussion:end -->
