---
id: REV-000150
sequence_id: 150
type: review
title: FEAT-000013 stability contract — independent gate
status: Approved
author: reviewer
subentities:
- local_id: F1
  title: 'Ref-kind vocabulary table is WRONG: lists nonexistent kinds, omits real
    ones'
  status: Verified
  severity: high
- local_id: F2
  title: F5 (reflog v decoupling) presented as SETTLED in Tier 1, contradicting Open-questions
    section and the bill
  status: Verified
  severity: high
- local_id: F3
  title: References section uses fabricated github.com URLs instead of item-ID references
  status: Verified
  severity: medium
- local_id: F4
  title: In-body cross-reference anchors are broken — point to heading slugs that
    do not exist
  status: Verified
  severity: high
- local_id: F5
  title: 'Migration promise not verbatim: inserts ''and beyond'' into the AC-pinned
    sentence'
  status: Verified
  severity: low
- local_id: F6
  title: ADR-114 remove-vs-cancel + ref-severance contract points not reflected in
    the doc
  status: Verified
  severity: low
- local_id: F7
  title: Official docs must not reference internal squad items or fabricated URLs
  status: Verified
  severity: high
created_at: '2026-06-17T08:03:01Z'
updated_at: '2026-06-17T08:29:38Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 150 add-finding "…" --severity high`; track with `sq review 150 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Verified |  | Ref-kind vocabulary table is WRONG: lists nonexistent kinds, omits real ones |
| F2 | 🟠 high | Verified |  | F5 (reflog v decoupling) presented as SETTLED in Tier 1, contradicting Open-questions section and the bill |
| F3 | 🟡 medium | Verified |  | References section uses fabricated github.com URLs instead of item-ID references |
| F4 | 🟠 high | Verified |  | In-body cross-reference anchors are broken — point to heading slugs that do not exist |
| F5 | 🟢 low | Verified |  | Migration promise not verbatim: inserts 'and beyond' into the AC-pinned sentence |
| F6 | 🟢 low | Verified |  | ADR-114 remove-vs-cancel + ref-severance contract points not reflected in the doc |
| F7 | 🟠 high | Verified |  | Official docs must not reference internal squad items or fabricated URLs |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Ref-kind vocabulary table is WRONG: lists nonexistent kinds, omits real ones

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
docs/stability.md line 235 lists the eight 'frozen at 1.0' ref kinds as: related, fixes, addresses, implements, blocked-by, blocks, duplicates, related-to.

The ACTUAL closed vocabulary (src/squads/_models/_item.py::VALID_REF_KINDS, the frozenset cited to ADR-000049) is: related, blocks, depends-on, implements, fixes, addresses, supersedes, duplicates.

So the contract INVENTS two kinds that do not exist (blocked-by, related-to) and OMITS two real ones (depends-on, supersedes). Confirmed independently by the CLI: 'sq review 150 ref add ... --kind reviews' errored with 'Valid kinds: addresses, blocks, depends-on, duplicates, fixes, implements, related, supersedes'. For a tier that promises this vocabulary is closed and frozen at 1.0, publishing the wrong eight kinds is a contract-breaking defect. Fix: replace the list with the real eight and re-verify against VALID_REF_KINDS.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — F5 (reflog v decoupling) presented as SETTLED in Tier 1, contradicting Open-questions section and the bill

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Tier 1 reflog body (line 95) states: 'v — schema version (currently DECOUPLED from the index SCHEMA_VERSION, per REV-000119 F5)'. The Open-questions section (line 395) states the opposite and correct fact: F5 is 'whether the reflog line v DECOUPLES from the index SCHEMA_VERSION (currently COUPLED at 0.3)'.

This is (a) an internal self-contradiction, (b) factually wrong at line 95, and (c) a violation of the review's explicit requirement that F5 'must NOT be presented as settled.' The obligations bill (FEAT-000013 comment 2026-06-15T10:24 point 4) and ADR-000149 Consequences both confirm: v is CURRENTLY COUPLED to SCHEMA_VERSION at 0.3, and decoupling is an OPEN pre-1.0-freeze question. Fix line 95 to say 'currently coupled to SCHEMA_VERSION (0.3); whether to decouple is open — see F5'.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — References section uses fabricated github.com URLs instead of item-ID references

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
The References section (lines 345-395) links every ADR/FEAT/GUIDE/REV to a hand-constructed external URL of the form https://github.com/anthropic-ai/squads/blob/main/squads/adrs/ADR-000049-....md (~30 such URLs). These are fabricated: the repo path/owner is guessed, and docs/internals.md — the house-style reference — never links externally; it cites items by bare ID. Per project convention docs reference items by ID or by 'sq' command (e.g. 'sq decision 49 show'), not guessed github URLs. Even the file paths are wrong: source lives under src/squads/, not squads/. Fix: drop the external URLs; reference by item ID (the reader runs 'sq show ADR-000049').
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — In-body cross-reference anchors are broken — point to heading slugs that do not exist

<!-- sq:finding:F4:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Every in-body citation uses an anchor link to a heading that does not exist. Examples: [ADR-000149](#adr-000149-post-10-schema_version-scheme), [ADR-000049](#adr-000049-ref-kind-vocabulary), [GUIDE-000079](#guide-000079-architecture-guide), [FEAT-000019](#feat-000019-item-addressing), [ADR-000133](#adr-000133-backends-and-pluggability), etc. The actual headings are 'Tier N: ...' and '### Ref-kind vocabulary (closed at 1.0)' — none generate the slugs the body links to. Result: nearly all ~25 cross-references render as dead links. (The single exception that happens to resolve is #exit-codes-distinct-codes-for-distinct-failures.) Fix: either link to the References-section anchors that DO exist, or to the actual section headings, or drop the fragment and cite by ID.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Migration promise not verbatim: inserts 'and beyond' into the AC-pinned sentence

<!-- sq:finding:F5:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
AC requires the migration promise VERBATIM: 'any squad created on any 0.x release reaches 1.0 intact via sq migrate up'. Line 10 reads 'Any squad created on any 0.x release reaches 1.0 AND BEYOND intact via sq migrate up.' The inserted 'and beyond' is a defensible strengthening (ADR-000149 uses '1.0 (and beyond)'), but the AC and US1 pin the exact phrase. Low severity — recommend either restoring the verbatim sentence as the canonical promise line, or keeping 'and beyond' but quoting the verbatim form once so the AC's literal text appears.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — ADR-114 remove-vs-cancel + ref-severance contract points not reflected in the doc

<!-- sq:finding:F6:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
ADR-000114 / FEAT-000023 deferral (FEAT-000013 comment 2026-06-15T09:21) lists FOUR contract points; only point (1) (IDs-never-reused / gaps-are-normal) made it into the doc (lines 48-55). Missing: (2) removal is a HARD DELETE, no Archived soft-state, and the contractual remove-vs-cancel distinction (Cancelled = considered-and-dropped, stays on the books; remove = should-never-have-existed, leaves the corpus); (3) forced removal SEVERS incoming refs in the same transaction so no dangling refs survive and sq check stays clean, children never auto-reparented. (Point 4, reflog-as-audit-trace, is covered.) Add the remove-vs-cancel rule and the ref-severance guarantee to the 'IDs are never reused' subsection.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Official docs must not reference internal squad items or fabricated URLs

<!-- sq:finding:F7:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
Operator directive (op-pierre): the shipped, user-facing docs/stability.md must NOT reference squad files / internal sq items at all, and must contain NO external github URLs. Two compounding defects:

(1) The entire 'References' section links ~30 internal items (ADR-/FEAT-/REV-/TASK-/GUIDE-/BUG-) — backlog artifacts a published-doc reader cannot access and should never see.

(2) Every link targets https://github.com/anthropic-ai/squads/... — a fabricated repo (wrong owner; the repo does not exist; source lives under src/squads/ not squads/).

Convention check: every OTHER doc in docs/ uses IDs only as illustrative examples (e.g. TASK-000007 to show ID shape) and never links to GitHub. Fix: delete the References section and all inline '(See FEAT-xxx / ADR-xxx)' parentheticals; state each guarantee on its own terms; where a cross-link genuinely helps, point to other user-facing docs/*.md by relative path (e.g. overrides.md, internals.md, migration.md). Illustrative example IDs are fine. This supersedes and broadens finding F3.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-17T08:04:39Z] Paul Reviewer:
  - VERDICT: Changes requested — NOT ready to ship with 0.3.0. The doc is structurally complete and well-organized (all five tiers present, the schema_version ADR-000149 decided and reflected, README + docs/README both link it, sq docs stability renders, all cited items resolve), but it carries factual errors in a document whose entire purpose is to be the authoritative frozen contract.
  - BLOCKERS (high): F1 — the ref-kind vocabulary table publishes the WRONG eight kinds (invents blocked-by/related-to, omits the real depends-on/supersedes); a frozen-vocabulary tier must match VALID_REF_KINDS exactly. F2 — Tier 1 line 95 presents reflog-v decoupling (REV-000119 F5) as SETTLED ('currently decoupled'), directly contradicting the Open-questions section and the bill, which say it is currently COUPLED at 0.3 and the decoupling is OPEN. F4 — almost every in-body cross-reference anchor (#adr-..., #feat-..., #guide-...) is a dead link; the slugs do not exist as headings.
  - SHOULD-FIX (medium/low): F3 — References section uses ~30 fabricated github.com URLs against house style (cite by ID, as internals.md does); paths also point at squads/ not src/squads/. F5 — migration promise inserts 'and beyond', deviating from the AC's verbatim phrasing. F6 — ADR-000114's remove-vs-cancel and ref-severance points are not in the doc.
  - Once F1/F2/F4 are corrected and F3/F5/F6 addressed, this is approvable. @tech-writer to revise; re-gate after.
- [2026-06-17T08:29:31Z] Paul Reviewer:
  - Re-gate clean — all seven findings (F1–F7) verified resolved, no coverage regression; ready to ship with 0.3.0.
<!-- sq:discussion:end -->
