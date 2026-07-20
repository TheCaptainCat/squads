---
id: REV-500
sequence_id: 500
type: review
title: 'TASK-494: scopes kind + role-skill resolver'
status: Approved
author: reviewer
refs:
- TASK-494:addresses
subentities:
- local_id: F1
  title: Resolver re-loads the index O(roles) times per sync
  status: Fixed
  severity: low
created_at: '2026-07-20T09:51:08Z'
updated_at: '2026-07-20T12:30:05Z'
---
<!-- sq:body -->
Independent review of TASK-494 (unstaged working tree): the `scopes` ref kind + the service-layer role->skill preload resolver. Scope: _models/_item.py (VALID_REF_KINDS += scopes), _services/_base.py (resolved_skills_for_role, _role_skills_map, refresh_managed wiring), _services/_maintenance.py (sync computes the map, persists extra.skills, role-scoped ctx), _backends/_base.py (BackendContext.role_skills + resolved_skills_for), both backends' generate_role_entry, agents_md/role_entry.md.j2, and the two new tests. TASK-493 code (skill-body authoring) and the templates_manifest regen were out of scope and not reviewed.

Verdict: APPROVE. Resolver correctness, kind-filtering, dedup/ordering, backend layering, and both-backends consistency are all sound; zero-scope-edge output is byte-identical to skills_for_role. One low-severity (non-blocking) efficiency finding on redundant index loads.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 500 add-finding "…" --severity medium`; track with `sq review 500 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | Resolver re-loads the index O(roles) times per sync |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Resolver re-loads the index O(roles) times per sync

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
_services/_base.py: _role_skills_map() calls resolved_skills_for_role() once per role, and each call loads the index twice — once via _role_item(slug) and again via 'db = await self.store.load()'. IndexStore.load() is uncached (full JSON parse + counter-backfill + vocab/badge re-validation on every call), so a full sync / refresh_managed does 1 + 2*N full index parses for N roles.

Why it matters: the sibling helper this one names as its 'Companion', _skill_paths(), loads once (a single list_items) and builds its map from the already-loaded items. resolved_skills_for_role standing alone reasonably loads its own snapshot, but the map builder could hoist a single db.load() and pass it in, matching _skill_paths. Output is correct either way, so this is non-blocking — a quality/efficiency cleanup, not a correctness defect.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T09:52:06Z] Paul Reviewer:
  - @manager verdict: APPROVE. Findings: 1 low (F1, non-blocking), 0 critical/high/medium.
  - TASK-494 is sound. Kind-filtering is real (backrefs is kind-agnostic; the resolver requires kind=='scopes' AND ref_id_matches to the role, so a related/blocks edge to the role does not leak in — proven by the different-kind test). Dedup is system-first, scoped tail sorted lexically; a skill that is both system and scoped is dropped from the tail via seen=set(system). Zero scope edges yields output byte-identical to skills_for_role (list splat of the same order; role-not-found returns system directly).
  - No layering violation: _backends/_base.py imports only the pure, index-blind skills_for_role for the fallback (no _index/SquadsDB import); both generate_role_entry implementations read ctx.resolved_skills_for(role.slug) identically, and the fallback fires for bare-ctx sites (activate_role/add_dev/retype), so those paths are unchanged. extra.skills is a re-derivable cache written only-on-change by sync; repair needs no new logic. Scope discipline holds: no link-role/unlink-role, no partial-sync hook, no schema bump, no ticket IDs in source/tests.
  - F1 (low, non-blocking): _role_skills_map calls resolved_skills_for_role per role, each doing two uncached store.load() parses, so a full sync does 1+2*N index parses vs the single-load sibling _skill_paths. Correct output — a cleanup, your call whether to spawn a fix or WontFix.
<!-- sq:discussion:end -->
