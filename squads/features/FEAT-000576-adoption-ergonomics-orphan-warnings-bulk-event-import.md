---
id: FEAT-576
sequence_id: 576
type: feature
title: 'Adoption ergonomics: orphan warnings + bulk event import'
status: Done
author: product-owner
refs:
- REV-565
- ADR-622:implements
subentities:
- local_id: US1
  title: Orphan-pointer warning on init/adopt
  status: Done
- local_id: US2
  title: Document the pre-existing CLAUDE.md/.claude adoption runbook
  status: Done
- local_id: US3
  title: 'Import event model: schema, validate-first pre-pass, handles'
  status: Done
- local_id: US4
  title: Warn when a managed CLAUDE.md region meets pre-existing content
  status: Done
- local_id: US5
  title: 'Import apply: single transaction, per-event clock/actor, reflog'
  status: Done
- local_id: US6
  title: '`sq import` CLI: --dry-run, --json, --at/--as'
  status: Done
- local_id: US7
  title: 'Adopter docs: recovering from a failed import'
  status: Done
created_at: '2026-07-22T08:41:51Z'
updated_at: '2026-07-24T07:49:29Z'
---
<!-- sq:body -->
## Capability

Two adoption-path improvements from the same field report (REV-565), both now ready to scope into tasks.

**Adopt track (F8).** When `init`/`adopt` meets a pre-existing, non-squads-managed `CLAUDE.md`/`.claude`, it must warn instead of silently overwriting or orphaning:
- list pre-existing `.claude` agent-pointer and skill files this run did not generate, as candidate orphans — never auto-delete (crosses the backend ownership boundary)
- when inserting the managed CLAUDE.md region next to real hand-written content, warn that the two may contradict, and consider leading with the managed block so the authoritative instructions come first
- an adopter-facing runbook covering what a run overwrites, what it leaves as a candidate orphan, and how to reconcile a hand-written CLAUDE.md with the appended block

**Import track (F2, per ADR-622 v1 — Accepted).** `sq import <file>`: a JSONL event stream replayed in one process. Implements ADR-622's contract exactly — do not redesign it: validate-first pre-pass (resolve handles, simulate ID allocation, check vocab/transitions/parent/refs/actor/marker-safety, collect all errors) with `--dry-run` stopping there; single `IndexStore.transaction()` apply with per-event `at`/`as`; client-handle addressing; fresh IDs off the global counter; the v1 op set (create/status/body/comment/ref/add-story|subtask|finding/sub-status/sub-body/assign/update); `ValidatorEngine`-gated with board debt surfaced as import warnings. Out of scope (ADR-622's deferrals): idempotent/resumable re-import, source-ID preservation, `sq export`.

## Why

REV-565 (adopter-project migration, squads 0.11.1): a pre-existing hand-written CLAUDE.md/.claude corpus produced silent overwrites (slug-matching pointers) and silent orphans (non-matching ones) with no warning either way, requiring manual cleanup after the fact — `adopt` is documented "non-destructive" but that claim doesn't extend to this collision case. Separately, replaying ~460 dated events required a bespoke Python driver because there is no batch primitive — only `--at` on a single invocation. Both are barriers that show up specifically at the point of adoption, the moment a prospective adopter has the least invested and the most reason to bounce off friction. ADR-622 settled the import design; these stories implement that design, not a fresh one.

## Acceptance

- `init`/`adopt` emits a warning listing `.claude` agent-pointer and skill files present on disk that the run did not generate/manage (candidate orphans).
- `init`/`adopt` warns when it inserts the managed CLAUDE.md block alongside pre-existing non-squads content, rather than doing so silently.
- An adopter-facing docs runbook covers adopting into a pre-existing CLAUDE.md/.claude: what's overwritten, what's a candidate orphan, how to reconcile by hand.
- `sq import` implements ADR-622 v1: event schema, file-order application, handle resolution, validate-first pre-pass with `--dry-run`, single-transaction apply with per-event clock/actor and reflog entries, `--json`, and a documented recovery path for a mid-apply crash.
- Any docs produced by either track are adopter-facing only: no sq/ticket IDs, no internal dev-process content.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 576 add-story "As a <role>, I want … so that …"`; track with `sq feature 576 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Orphan-pointer warning on init/adopt |
| US2 | Done |  | Document the pre-existing CLAUDE.md/.claude adoption runbook |
| US3 | Done |  | Import event model: schema, validate-first pre-pass, handles |
| US4 | Done |  | Warn when a managed CLAUDE.md region meets pre-existing content |
| US5 | Done |  | Import apply: single transaction, per-event clock/actor, reflog |
| US6 | Done |  | `sq import` CLI: --dry-run, --json, --at/--as |
| US7 | Done |  | Adopter docs: recovering from a failed import |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Orphan-pointer warning on init/adopt

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
List pre-existing `.claude` agent-pointer files AND skill files this run did not generate/overwrite (candidate orphans), as a warning — never delete them. Today a slug match silently overwrites (e.g. `architect.md`) while a non-matching file (`lead.md`, `ux-ui-dev.md`, `.index.md`) is left with no signal either way (F8).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Document the pre-existing CLAUDE.md/.claude adoption runbook

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Adopter-facing runbook: "adopting into a project that already has CLAUDE.md/.claude" — what init/adopt overwrites (slug-matching pointers), what it leaves as a candidate orphan, and how to reconcile a hand-written CLAUDE.md with the appended managed block by hand. No sq/ticket/dev-process references — this is tool documentation for adopters (F8).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Import event model: schema, validate-first pre-pass, handles

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Per ADR-622 v1: the JSONL event model (common `op`/`at`/`as` fields inherited across lines, the v1 op set — create/status/body/comment/ref/add-story|add-subtask|add-finding/sub-status/sub-body/assign/update), client-handle addressing (handle -> allocated-id / (parent-id, local-id), resolved before literal IDs), and the validate-first pre-pass: resolve every handle, simulate ID allocation, check type/status vocab, transition legality, parent eligibility, ref kinds, actor registration, and marker-safety of every prose field — collecting ALL errors, not just the first. `--dry-run` stops exactly here (F2).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Warn when a managed CLAUDE.md region meets pre-existing content

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
When init/adopt finds a CLAUDE.md with real hand-written content but no squads markers, still insert the managed `<!-- squads:start -->` region rather than refusing — but warn that the hand-written operating model may contradict it. Consider placing the managed block at the top of the file so the authoritative instructions lead, rather than appending below existing prose (F8).
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Import apply: single transaction, per-event clock/actor, reflog

<!-- sq:story:US5:head -->
**Status:** 🟢 Done
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
Per ADR-622 v1: once the pre-pass is fully clean, apply inside one `IndexStore.transaction()` — mutate the loaded db in memory, allocate fresh IDs from the single global counter (never from IDs in the file), write each item's .md through the marker-safe section/frontmatter helpers, commit the index once at the end. Each event rebinds the ambient clock/actor via the RequestContext seam for its own `at`/`as` and still emits its own reflog entry. Every created/updated item passes the same ValidatorEngine.gate() interactive commands run; board-debt conditions (unwritten sub-entity bodies, over-long titles) surface as import warnings, not silent debt. Factor each op's mutation core into a db-taking apply-helper shared with the existing single-op service method, per the ADR's implementation note — one code path per mutation, not a parallel importer (F2).
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — `sq import` CLI: --dry-run, --json, --at/--as

<!-- sq:story:US6:head -->
**Status:** 🟢 Done
<!-- sq:story:US6:head:end -->

<!-- sq:story:US6:body -->
Top-level `sq import <file>` (`-` reads JSONL from stdin) per ADR-622 v1: `--dry-run` runs the validate pre-pass only, writes nothing, prints the handle -> id plan and per-op counts; `--json` returns per-op counts, the resolved handle -> id map, and the ordered error list on failure; `--at`/`--as` supply file-level defaults events inherit when they omit their own; `--dir` is the usual squad selector. On any validation error: exit non-zero, write nothing, list every error with its line number (F2).
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Adopter docs: recovering from a failed import

<!-- sq:story:US7:head -->
**Status:** 🟢 Done
<!-- sq:story:US7:head:end -->

<!-- sq:story:US7:body -->
ADR-622's one flagged rough edge: a mid-apply crash (rare I/O failure after the pre-pass already passed) can leave a partial write that `sq repair` folds into the index, but re-running the same file is NOT safe (v1 has no idempotency — it allocates fresh IDs and duplicates items). Add a short recovery note to the adoption/import docs: run `repair` first, inspect what was actually written before touching the file again, and don't blind-retry an import file. Adopter-facing only — no sq/ticket/dev-process references (F2).
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T07:49:29Z] Catherine Manager:
  - FEAT-576 Done: adoption ergonomics complete. Import (ADR-622): sq import JSONL engine (validate-first pre-pass + single-transaction apply, per-event at/as, client handles) + the sq import CLI (--dry-run/--json/--at/--as). Adopt: orphan-pointer + pre-existing-CLAUDE.md warnings (warn-only, non-destructive). Docs: adoption runbook + import-recovery note. Reviewed REV-641 (engine) + REV-643 (surfaces), both Approved. Full suite green. Accepted under the standing non-visual delegation.
<!-- sq:discussion:end -->
