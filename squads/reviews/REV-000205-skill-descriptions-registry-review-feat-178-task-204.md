---
id: REV-000205
sequence_id: 205
type: review
title: 'Skill descriptions registry review: FEAT-178 TASK-204'
status: Approved
author: reviewer
refs:
- FEAT-000178
- TASK-000204
subentities:
- local_id: F1
  title: Migration reimplements pointer rendering instead of delegating to backend
  status: Open
  severity: low
- local_id: F2
  title: Registry sq-type comprehension and bundled_skill_slugs use two independent
    type filters
  status: Open
  severity: low
- local_id: F3
  title: Description write semantics inconsistent across the three migration paths
    (fill-if-empty vs overwrite)
  status: Open
  severity: low
created_at: '2026-06-25T09:53:57Z'
updated_at: '2026-06-25T09:58:23Z'
---
<!-- sq:body -->
Independent review of TASK-204 (single skill-description registry; carry descriptions onto SKILL items so .claude pointers and sq list -t skill keep rich text). I authored REV-191/201/203 on this feature; this review is scoped to TASK-204 only. Did not write the code.

VERDICT: APPROVE-WITH-NITS. The fix is correct, well-tested, and regression-safe. All three nits are LOW severity and non-blocking.

Single source of truth (CONFIRMED): SKILL_DESCRIPTIONS + skill_description() in _interactions.py is the only home for these strings. Grep confirms the backend's three former literals (squads/greeting at _backend.py:72/84, and the templated sq-<type> at :230) all now read interactions.skill_description(); zero hardcoded description strings remain. Registry covers exactly the 9 bundled slugs (greeting, squads, sq-bug/decision/epic/feature/guide/review/task) with no gaps and no extras. Unknown slug -> sensible fallback to the slug itself (no KeyError/crash).

Backfill correctness & case dispatch (CONFIRMED MUTUALLY EXCLUSIVE): convention-file-exists -> _backfill_description (fill-if-empty, idempotent); else legacy slug file with id -> _rename_stamped_legacy; else unstamped -> allocate+stamp; else skip. Live repo state is convention-named + description-missing -> backfill path fires and repairs the degraded pointers on migrate up (verified: current .claude pointers are bare slugs, item frontmatter has no description key). Backfill is idempotent (second run no-op once description present). Pointer path built in the migration (squad_dir_rel/squad_rel) matches generate_skill_entry's ctx.root_relative(item).

No regressions to prior fixes (CONFIRMED): transaction-only allocation intact (allocate_id only inside store.transaction() in both seed and migrate — REV-201 F2); frontmatter-preserving body-region regen intact (REV-191 — _write_managed_skill replaces only sq:body when frontmatter present, fail-safe re-emits frontmatter); filename convention + pointer resolution intact (REV-203); backend still does NOT import _index/IndexStore — descriptions reach it via the registry, not the index (F3 layering).

Invariants (CONFIRMED): frontmatter is source of truth (description now on the item, sq repair reconstructs); marker-safe edits (sections helpers only); no from __future__; acyclic imports — the backend's new imports (_sections, _markers) are leaf-level and _interactions imports cause no cycle (verified by import); clock.now() used (no datetime.now()).

Tests (STRONG): assert pointer description == registry text after BOTH init and migrate; sq list -t skill non-empty + not-bare-slug descriptions; backfill case + its idempotence; double-sync preserves ids/filenames; corpus v0_5 fixture carries the rich descriptions. pyright + ruff clean on all touched files; the 7 new TASK-204 tests + full skill suite pass (35 passed). I confirm the operator's hands-on verification.

Findings: F1 (low) migration reimplements pointer rendering vs delegating to backend; F2 (low) registry sq-type filter and bundled_skill_slugs use two independent type-set definitions (agree today, latent divergence risk); F3 (low) description write policy inconsistent across migration paths (fill-if-empty vs overwrite) — cosmetic, no idempotence/correctness impact. None block.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 205 add-finding "…" --severity high`; track with `sq review 205 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Migration reimplements pointer rendering instead of delegating to backend |
| F2 | 🟢 low | Open |  | Registry sq-type comprehension and bundled_skill_slugs use two independent type filters |
| F3 | 🟢 low | Open |  | Description write semantics inconsistent across the three migration paths (fill-if-empty vs overwrite) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Migration reimplements pointer rendering instead of delegating to backend

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
src/squads/_migrations/_v0_4_to_v0_5.py:93-111 (_rewrite_pointer) hand-rolls the .claude pointer write via render('claude/pointer_skill.md.j2', ...) + oneline(), duplicating ClaudeCodeBackend.generate_skill_entry. seed_bundled_skills (the init path) correctly delegates to backend.generate_skill_entry; the migration does not. Currently the path/format match (verified: ctx.root_relative(item) == f'{squad_dir_rel}/{squad_rel}'), so no live bug. But this is a soft duplication of the very pointer-derivation TASK-204 tried to centralize, and it bypasses the backend ABC (invariant 6 — though migrations reaching into a specific backend is a known, defensible pattern since they are frozen-in-time). Acceptable as-is for a migration; flagging so a future pointer-template change knows this second copy exists.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Registry sq-type comprehension and bundled_skill_slugs use two independent type filters

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
src/squads/_interactions.py SKILL_DESCRIPTIONS builds the sq-<type> entries by iterating ItemType and EXCLUDING (ROLE, SKILL, OPERATOR), whereas bundled_skill_slugs() derives the same sq-<type> set from managed_item_types() (= PLAYBOOK keys). These are two independent definitions of 'which item types get a managed skill'. They agree today (verified: registry keys == bundled_skill_slugs(), 9 slugs, no gaps). But if a future ItemType is added that is in PLAYBOOK-or-not but not in the exclude tuple, the two lists silently diverge: a slug bundled_skill_slugs() yields with no registry entry falls back to skill_description()->slug (re-introducing exactly this regression), or the registry grows an sq-<type> nobody seeds. Low risk, latent coupling. Suggest deriving the registry comprehension from managed_item_types() too, so there is one source for the type set.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Description write semantics inconsistent across the three migration paths (fill-if-empty vs overwrite)

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
The migration writes the description through three code paths with two different policies: (a) _backfill_description (convention file already present, _v0_4_to_v0_5.py:128) is fill-if-empty — 'if cfm.get("description"): return False' — so a hand-edited description is preserved; (b) _rename_stamped_legacy (:156) unconditionally overwrites fm['description']=desc; (c) the unstamped-allocate branch sets desc on a brand-new item. Fill-if-empty is the correct/safe policy for a backfill. The overwrite in (b) does NOT break idempotence (a stamped-legacy file is renamed to a convention file and thereafter only ever hits path (a)), and a user-edited description on a still-slug-named stamped file is an extremely unlikely state, so this is cosmetic. Worth aligning (b) to fill-if-empty for consistency and to never clobber operator edits. Note: the live repo state is description-missing (None), not description==slug, so _backfill_description's truthy-check fires correctly and repairs the degraded pointers on migrate up — verified .claude pointers are currently bare slugs and item frontmatter has no description key.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T09:55:11Z] Paul Reviewer:
  - VERDICT: APPROVE-WITH-NITS. TASK-204 is correct, regression-safe, and well-covered. Single registry (SKILL_DESCRIPTIONS/skill_description in _interactions.py) is genuinely the only home for the strings — backend's 3 former literals all removed and now read the registry; all 9 bundled slugs covered; unknown-slug fallback returns the slug (no crash). Backfill case-dispatch is mutually exclusive and idempotent; the live degraded state (description-missing, bare-slug pointers) is exactly what the convention-file backfill path repairs on migrate up. No regressions to REV-191/201/203 fixes; transaction-only allocation, frontmatter-preserving regen, filename convention, and the no-index-in-backend layering all intact. No import cycle. Tests assert pointer==registry after both init and migrate, list-non-empty, backfill+idempotence, double-sync stability; pyright/ruff clean; 35 skill tests pass. Confirmed the operator's hands-on verification.
  - 3 LOW nits, none blocking: F1 migration hand-rolls pointer rendering instead of delegating to backend.generate_skill_entry (duplication, but format/path match and migrations are frozen-in-time — acceptable). F2 registry's sq-type comprehension excludes (ROLE,SKILL,OPERATOR) while bundled_skill_slugs uses managed_item_types() — two independent type-set definitions that agree today but could silently diverge on a future ItemType; suggest deriving both from managed_item_types(). F3 _rename_stamped_legacy unconditionally overwrites description while _backfill_description is fill-if-empty — cosmetic, no idempotence impact, but aligning to fill-if-empty avoids clobbering operator edits.
  - @tech-lead these are optional polish; safe to mark TASK-204 Done as-is. I did not change task/feature status.
- [2026-06-25T09:58:22Z] Catherine Manager:
  - F2+F3 verified. F2: SKILL_DESCRIPTIONS sq-<type> set now iterates PLAYBOOK (same source managed_item_types wraps) — registry keys == bundled_skill_slugs (9, confirmed), no divergence risk. F3: _rename_stamped_legacy now fill-if-empty, consistent with _backfill_description — won't clobber operator edits. F1 accepted as documented nit (frozen-migration pointer rendering). pyright/ruff clean, desc/backfill tests green. Approving.
<!-- sq:discussion:end -->
