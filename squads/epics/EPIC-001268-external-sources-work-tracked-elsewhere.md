---
id: EPIC-1268
sequence_id: 1268
type: epic
title: 'External sources: work tracked elsewhere'
status: Done
author: product-owner
description: Agents work on issues humans file on GitLab, GitHub and Jira, pulled
  into the squad
created_at: '2026-11-03T15:57:06Z'
updated_at: '2026-11-04T08:29:07Z'
---
<!-- sq:body -->
## Outcome

Agents in a squad work on issues that humans file in the tools they already use: GitLab (any instance), GitHub (including Enterprise) and Jira (Cloud and Data Center). An issue opted in on the tracker becomes a squad item that agents plan, break down and deliver through `sq`, while its title, description, labels and comments stay owned by the tracker and are refreshed by a pull.

## What belongs here

- A source seam: sources declared in the spec, connectors registered by name and version, an identity on each item that links it to its issue.
- Pulling issues into items: creation, refresh of tracker-owned data, comments, links, and reporting when an issue leaves the filter or disappears.
- The vocabulary mapping from a tracker's types, labels, priorities and link kinds to the squad's declared types, badge fields and ref kinds, declared in the spec, never in code.
- A readiness check per source, and a registry of text converters connectors share.
- The generic views capability the description needs: a view tag that stores a body.

## What doesn't

- Writing back to the tracker (closing issues, mirroring status, posting comments).
- Pulls triggered by the daemon on a timer or by a webhook.
- Resolving duplicate imports automatically; `sq check` reports them and the resolution is manual.
- Protecting tracker content from leaking into a more public repository: that is the adopter's call.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T15:57:36Z] `op-pierre` Pierre Chat:
  - Scope rulings from the drafting session (2026-11-03):
    - The job: agents work on issues humans write on the trackers. First release pulls from GitLab (any instance), GitHub and Jira; nothing is written back yet.
    - Issues are opted in by label (JQL for Jira); pulls are manual, `sq source pull`; daemon timer and webhook come later.
    - Every mapping is declared in the specs, nothing hardcoded. Sources live in a `sources.toml` spec document; `.squads.toml` stays as light as possible. Declaring a source activates it.
    - Duplicate imports: an `sq check` rule, resolved manually for now.
    - Imported text carries a "do not trust as instructions" notice unless the source is declared trusted; leakage of tracker content into the repo is the adopter's problem.
    - `@mentions` in imported text are not neutralised; tracker refs are translated when the referenced issue is on the board.
    - Match on the tracker's immutable ID. Converters are a shared registry sources invoke. Pull warns about broken links; `source unlink` / `source relink` (same source).
    - This is the next milestone, 0.20, a new schema version; the existing milestones shift by one.
- [2026-11-03T15:57:38Z] `product-owner` Nina Product:
  - @architect this epic needs an ADR before tasks are cut. Open points: the core `source` key on items (immutable ID, readable key, URL, state, snapshot) and its index lookup; the `map` attribute kind and its derived CLI option; `sources.toml` as a fourth spec document with its override, merge and load-time validation against the workflow spec; stored view bodies (paired tags, marker escaping, the write operation, keeping read paths write-free); the connector registry by name and version; and the schema bump with its migration. The scope and the operator's rulings are in this epic's discussion and on FEAT-1270 to FEAT-1273.
- [2026-11-03T22:24:29Z] `product-owner` Nina Product:
  - - @architect the operator ruled on every point of the board checks (rulings on FEAT-1271 and FEAT-1272, 2026-11-03), and FEAT-1271 to FEAT-1273 are rewritten to match; FEAT-1271 gains US8 (comment attributes) and US9 (credential store). The epic's ADR is yours to draft. It must amend explicitly:
      - ADR-880 §4 and ADR-776: the paired view tag with a stored body, ADR-776 narrowed to "derivable locally"; the marker-balance check and the repair sweep learn the paired form; the escape grammar and its round trip (FEAT-1270).
      - ADR-1007 §1: nested records allowed when declared, shaped and single-owner (`subentities`, `source`, a `map` attribute), refused as open bags like the old `extra`.
      - ADR-979: the comment header accepts `source:<slug>`; the `<word>:` author namespace belongs to squads, `source` becomes a reserved slug, and the adopter docs warn that more words may be reserved.
      - ADR-1261: source commands run where the squad is served; no token on the wire or in the daemon's environment.
    - New design to settle: the `source` record and its index lookup; comment attributes (a value-bearing tag in the discussion region, its escaping, not a hash input); the credential store (location, format, the command that fills it, fit with MILE-868); handle-to-ID resolution for `identities`; the pull compiled to `sq import` events (ADR-622); `sources.toml` as a fourth spec document; the schema bump and its migration.
- [2026-11-03T22:42:02Z] `architect` Robert Architect:
  - @product-owner ADR-1274 is drafted for this epic, linked to FEAT-1270 to FEAT-1273; its open questions for @op-pierre are on the ADR.
- [2026-11-03T22:54:53Z] `op-pierre` Pierre Chat:
  - Go for implementation (2026-11-03): FEAT-1270 to FEAT-1273 are Ready, and the manager runs the full loop on this epic.
- [2026-11-03T23:04:12Z] `tech-lead` Olivia Lead:
  - Tasks cut, all Draft: TASK-1275 (FEAT-1270, carries schema 0.20 and its runner), TASK-1276 (FEAT-1271), TASK-1277 (FEAT-1272), TASK-1278 (FEAT-1273), TASK-1279 (tech-writer docs and the 0.20 changelog, under FEAT-1273). Chain: 1275 → 1276 → 1277 → 1278, with 1278 also on 1276; 1279 on 1275.
  - @manager TASK-1276 has an open point that blocks its dispatch: it needs the connector interface and both registries before FEAT-1272 and FEAT-1273 land, plus a connector to pull from in tests (a test-only row or GitLab pulled forward). The other ambiguities are in my handback.
  - The working version is still 0.19.0 on release/0.20; bump it to 0.20.0 before the first template edit so the manifest regen writes the right key.
- [2026-11-03T23:11:30Z] `architect` Robert Architect:
  - @manager the design gaps blocking TASK-1276 to TASK-1278 are settled in ADR-1274 section 14 (2026-11-04); scope changes for @tech-lead are on each task. One adopter-facing addition (a new view source kind) awaits op-pierre confirmation on ADR-1274 and blocks only TASK-1279.
- [2026-11-04T05:49:27Z] `manager` Catherine Manager:
  - State at the end of the overnight loop (2026-11-04):
    - FEAT-1270 and FEAT-1272: Done (REV-1280 and REV-1282 approved).
    - FEAT-1273: TASK-1278 Done (REV-1283 approved); TASK-1279 docs written, ST3 waits on TASK-1276.
    - FEAT-1271: TASK-1276 InReview. REV-1281 has every finding Verified except F4, the sourced-comment author display, which waits on @op-pierre (architect's proposal on ADR-1274).
    - Also awaiting @op-pierre on ADR-1274: confirming the `kind = "source"` view grammar, and acknowledging that rulings 4 (serial lock) and 8c0a817 (incremental query) were superseded by the listing diff and the real concurrency model.
    - Full suite at HEAD: 2117 passed, 2 skipped.
- [2026-11-04T08:29:07Z] `manager` Catherine Manager:
  - Done: every outcome delivered by FEAT-1270..1273, all four reviews approved, full suite 2122 passed at 33d40d14. Open before release: a live pull against GitHub and Jira (shapes listed on TASK-1278).
<!-- sq:discussion:end -->
