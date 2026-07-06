---
id: TASK-306
sequence_id: 306
type: task
title: Add sq check rule flagging leading status/lifecycle banners in bodies
status: Done
parent: FEAT-264
author: tech-lead
assignee: python-dev
refs:
- FEAT-237
subentities:
- local_id: ST1
  title: Implement the leading-banner detector helper + wire into check
  status: Done
  story: US1
- local_id: ST2
  title: Add positive + negative detector tests
  status: Done
  story: US1
- local_id: ST3
  title: Reconcile broken fixtures/goldens without weakening the detector
  status: Done
  story: US1
created_at: '2026-07-06T12:13:33Z'
updated_at: '2026-07-06T12:31:55Z'
---
<!-- sq:body -->
**Axis 2 — the enforcement guard (`sq check` rule, the preferred primary home).** Add a new `_check_*` helper to `src/squads/_services/_maintenance.py`, sitting beside the existing check helpers and wired into the `check` pipeline next to the sibling calls. It **mirrors the shape of `_check_unwritten_subentity_bodies`** (just added by FEAT-289): reads each item's `:body` marker region from the on_disk file text via `_sections.get_section(text, "body")` (reusing the `on_disk` path scan, keyed by sequence number) and inspects `item.description` from the index; emits one **warn**-level `CheckIssue` per offending item.

**Detection heuristic — MUST be false-positive-averse. Flag ONLY a leading banner:** a body or section that *opens* with `STATUS:` / `**STATUS…**`, or a hand-written `## Status` / `### Status` heading; likewise a `description:` that opens with such a banner. Anchor the match to leading / heading position — NOT a keyword grep over the whole body.

**Do NOT flag:** lifecycle words in mid-body topical prose ('the Draft→Ready transition', 'blocks TASK-x until it lands'); lifecycle words inside fenced code / CLI examples; anything in the `sq:discussion` region (comments are exempt by design). Lint **only** `sq:body` + `description`, never `sq:discussion`.

**Severity: `warn`** (advisory, non-blocking) to match the sibling checks (`_check_unwritten_subentity_bodies`, `_check_subentity_title_lengths`). Record the severity rationale in a comment on this task, as FEAT-289 did. The AC4 warn-then-error endgame (promote to a blocking `error` once the tree is clean) is a **deferred fast-follow, out of scope here** — ship warn now.

**Message** is actionable: name the offending item and say to move the state to frontmatter / a dated discussion comment. **Guard scope is disjoint from FEAT-237's** src/ grep guard — no shared surface, patterns must not cross-fire (237 owns src/ code comments; this owns tracker bodies).

**Done when:** the helper + wiring land; warn-level; detection matches the three high-signal patterns and stays silent on the four false-positive cases above; positive+negative tests pass (see subtasks); goldens/fixtures reconciled without weakening the detector.

**Shipped SOURCE carries NO sq IDs** (helper + tests) — name tests by behavior, keep any ticket pointer in the sq comment / PR only. (This task/subtask prose may cite IDs; the code may not.)
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 306 add-subtask "<title>"`; track with `sq task 306 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Implement the leading-banner detector helper + wire into check | US1 |
| ST2 | Done |  | Add positive + negative detector tests | US1 |
| ST3 | Done |  | Reconcile broken fixtures/goldens without weakening the detector | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Implement the leading-banner detector helper + wire into check

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — The tracker's status is never contradicted by body prose
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add a `_check_*` helper in src/squads/_services/_maintenance.py mirroring _check_unwritten_subentity_bodies: iterate index items, read the `:body` region via _sections.get_section(text, "body") from the on_disk file text, and inspect item.description. Emit one warn CheckIssue per item whose body/description OPENS with a `STATUS:` / `**STATUS…**` banner or a leading `## Status`/`### Status` heading. Anchor to leading/heading position (not a whole-body grep); skip the sq:discussion region entirely. Wire into the check pipeline beside the sibling calls. Message names the item and says move state to frontmatter / a dated comment. Record the warn-severity rationale in a comment. No sq IDs in the source. Done when the helper lands, is wired, and runs at warn level.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-07-06T12:31:52Z] Elias Python:
  - Done: added _check_status_banners + _opens_with_status_banner to src/squads/_services/_maintenance.py, wired into check() beside the sibling calls. Reads the item's :body region via sections.get_section (never touches sq:discussion) and item.description; anchored to the leading line only. Warn-level.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add positive + negative detector tests

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — The tracker's status is never contradicted by body prose
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add service-level + CLI-smoke tests, named by behavior (no sq IDs in filenames or bodies). POSITIVE: a body opening with `STATUS: …`, a body with a leading `## Status` heading, and a `description:` opening with a banner each emit exactly one warn. NEGATIVE (must stay silent): a mid-body topical lifecycle mention ('the Draft→Ready transition'), a cross-reference ('blocks TASK-x until it lands'), a fenced code block containing `STATUS:`, and a banner living in the sq:discussion region. Done when both suites pass and prove the detector fires on banners and only on banners.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-07-06T12:31:53Z] Elias Python:
  - Done: added tests/test_status_banner_check.py — 6 positive-shaped assertions (STATUS: banner, ## Status heading, bold **STATUS…** banner, description banner, message wording, warn-level) and 6 negative (topical Draft→Ready mention, cross-reference to another task, STATUS: inside fenced code, banner in a discussion comment, no-body item, warn isolation) at service level, plus 4 CLI smoke tests. All pass.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Reconcile broken fixtures/goldens without weakening the detector

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — The tracker's status is never contradicted by body prose
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Like FEAT-289, adding the rule may trip existing tests/goldens whose fixtures carry banner-shaped body prose or whose golden `sq check` output changes. Reconcile them: fill/fix fixture bodies to be state-free, or update the expected golden output to include the new warn lines. NEVER relax the regex or narrow the scope just to make a test pass — the detector's precision is the deliverable. Done when the full suite is green with the detector unweakened.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-07-06T12:31:54Z] Elias Python:
  - Done: no existing fixtures/goldens carried a leading-banner shape (the golden seeded squad's descriptions/bodies are plain), so nothing needed reconciling — full suite is green with the detector unweakened.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T12:24:03Z] Elias Python:
  - Severity rationale: warn, matching the sibling advisory checks (_check_unwritten_subentity_bodies, _check_subentity_title_lengths). A self-declared status banner is a maintenance smell — it can drift from the real frontmatter status — not a structural error that should block sq check's exit code. The warn-then-error promotion (once the corpus is clean) is an explicit fast-follow, out of scope for this task per the description.
- [2026-07-06T12:31:55Z] Elias Python:
  - Helper + wiring + tests landed. Full suite green (1641 passed, 1 skipped, 0 failed). Gates clean: pyright 0 errors, ruff check all passed, ruff format all formatted. No sq IDs in shipped src/tests (verified by grep).
<!-- sq:discussion:end -->
