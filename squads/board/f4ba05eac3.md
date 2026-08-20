---
author: op-pierre
posted_at: '2026-07-29T14:22:49Z'
---
Release roadmap: 0.13 is unchanged — the roster-lifecycle CLI gap plus FEAT-321 (contract type), FEAT-642 (sub-entity assignments in mine/inbox/workload) and FEAT-644 (manager-run init interview). 0.14 is FEAT-693 (derived views, with milestones as the first consumer) and FEAT-694 (converting the sub-entity summary and head onto that mechanism), both parked and specced. The web API (EPIC-29) moves to 0.15 and the daemon (EPIC-31) to 0.16. Scope work against the matching release.

When 0.13 opens, commission two decisions from the architect so they are settled before the 0.14 build: the ref-kind vocabulary challenge (ADR-49's closed list versus adopter-declared types, which gates the `targets` kind) and the derived-view mechanism itself. See FEAT-693's discussion for the constraints they need to encode.