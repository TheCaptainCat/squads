---
author: manager
posted_at: '2026-08-24T20:17:51Z'
until: '2026-11-01T00:00:00Z'
---
0.14 release sequence — the plan of record. Check here before starting or dispatching 0.14 work.

Hard ordering rule (ADR-781 section 6): the version bump comes BEFORE any template-manifest
regeneration. FEAT-790, FEAT-792 and FEAT-694 all touch bundled templates, so a regeneration
only happens once that work lands. Regenerating against a shipped release's manifest entry
corrupts it.

Step 0 — records and unblocking: DONE
- ADR-320, 775, 776, 777, 781 all Accepted.
- FEAT-693 and FEAT-694 reauthored against ADR-776; FEAT-694 retitled and inverted (retire the
  regions, do not convert them), and it owns the role Skills section too.
- FEAT-790 (ref kinds), FEAT-791 (override uniformity), FEAT-792 (pointers) authored — the
  build work of ADR-775/777/781, which no feature covered.
- Working version bumped to 0.14.0. Schema bump for the release is 0.11 -> 0.12.

Step 1 — parallel, no interdependencies
- FEAT-644 (docs only, tech-writer) — no gate, can start any time.
- FEAT-690 (both clients) — carries the sq memory list --json created_at fix.
- FEAT-791 (manifest widening) — critical path for FEAT-693.
- FEAT-790 (ref kinds) — critical path for FEAT-693.

Step 2 — the coupled core
- FEAT-693 + FEAT-321 land together: ONE schema bump, ONE migration runner for the MILE and
  PRD types (operator ruling). Needs FEAT-790 and FEAT-791 done first. Adopter-authored
  presentation templates are IN scope for FEAT-693 (operator ruling).
- FEAT-792 (pointers) runs alongside.

Step 3 — the collapse
- FEAT-694 rides 0.14 (operator ruling): its corpus-wide region-strip migration folds into the
  SAME runner as PRD and MILE, so the release does not cut until it lands.

Critical path: FEAT-790 + FEAT-791 -> FEAT-693/321 -> FEAT-694. FEAT-693 is the long pole.
Open: ADR-777's manifest retention window is with the architect.