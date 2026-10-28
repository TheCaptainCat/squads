---
id: REV-1216
sequence_id: 1216
type: review
title: Review the per-kind sub-entity wrapper removal
status: Approved
author: reviewer
refs:
- TASK-1215
subentities:
- local_id: F1
  title: Import comment selectors and their refusal have no test
  status: Verified
  severity: medium
- local_id: F2
  title: Stale prose about the deleted done-toggle and interactive path
  status: Verified
  severity: low
- local_id: F3
  title: Multi-selector refusal names CLI flags, omits sub
  status: Verified
  severity: low
- local_id: F4
  title: Comment selector tests never name a sub-entity by handle
  status: Verified
  severity: low
created_at: '2026-10-28T12:33:49Z'
updated_at: '2026-10-28T12:48:04Z'
---
<!-- sq:body -->
Review of TASK-1215: the removal of the 16 per-kind sub-entity service wrappers, the comment-selector fold in the importer, and the three members left without a caller.

## What was checked

- **Dead members.** `set_block_status`, `_set_block_assignee` and `WorkflowSpec.subentity_completion` were called only by the deleted wrappers at HEAD (`git grep` on HEAD over `src`, `tests`, `clients`). No `getattr` or string dispatch in `src` names them. The TUI is in `src` and does not call them. The VS Code client calls the `sq` CLI and never a Python method, and nothing in `clients/vscode/src` reads `completion`. The cores they wrapped (`_set_block_status_core`, `_set_block_assignee_core`) are still called by the importer. The deletion is sound.
- **Fixture ports.** `update_finding` and `update_subtask` passed straight through to `update_block`. `add_finding` filled the declared default severity, and the port does the same explicitly. The fixture squads are unchanged.
- **Importer probe.** Scratch squads were built by the working tree and by a HEAD worktree. 17 comment-event shapes went through `sq import`, as a dry run and for real: no selector; each of `story`, `subtask`, `finding`, `sub`; two selectors; `subtask` plus `sub`; all three; an empty `story` beside a `subtask`; two selectors that name unknown local ids; an unknown local id; an unknown handle token; the wrong kind for the item; a `sub` with an undeclared kind; an empty `sub` local id. Stdout, stderr and exit code were byte-identical between the builds. The squad files were identical too, apart from timestamps. The multi-selector refusal keeps its message and exit 1.
- **Gates.** pyright reports 0 errors, and `ruff check` and `ruff format --check` are clean. `vulture` gives the same output as HEAD apart from line numbers. `pytest -n 4 tests/meta tests/cli` gives 1426 passed. The kind-literal guard and its dead-entry test pass with both allowlist entries removed. I did not run the full suite.

The behaviour-preservation claim holds. What remains is a test gap and some prose the deletion left out of date. See the findings.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1216 add-finding "…" --severity medium`; track with `sq review 1216 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Import comment selectors and their refusal have no test

<!-- sq:finding:F1:body -->
No test exercises an import comment selector. The only import comment event in the tests is `COMMENT` in `tests/cli/test_import.py`, which names no selector. The `tests/cli/test_reflog.py` event names none either. With `tests/meta` and `tests/cli` under coverage, lines 144-147 of `_services/_import.py` are never executed: the `sub` branch of `_comment_selector` and the multi-selector refusal. Line coverage cannot show whether the per-kind comprehension resolves a selector, and no test passes one. The task's acceptance says "the import comment tests prove it". No such tests exist, so the only evidence of "no behaviour change" here is a manual probe against HEAD. A later edit to `_comment_selector` could break every selector, or drop the refusal, and still pass the suite.

Add a table-driven test to `tests/cli/test_import.py`. The cases are no selector, each of `story`/`subtask`/`finding`/`sub` (assert the comment lands in that sub-entity's discussion), two selectors (assert the refusal text, exit 1 and nothing written), and an unknown local id (assert the `no <kind> <id> in <ID>` refusal). The 17 shapes in the review body are a ready-made table.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-28T12:38:32Z] `python-dev` Elias Python:
  - Fixed: table-driven import comment tests in tests/cli/test_import.py (each selector, two selectors, unknown id); falsified by breaking _comment_selector, red then restored.
- [2026-10-28T12:41:21Z] `reviewer` Paul Reviewer:
  - Verified. I applied 5 mutations to _comment_selector and checked each against the 12 comment-event tests. Always None: 8 red. Refusal disabled: 3 red. sub ignored: 5 red. finding mapped to the subtask kind: 1 red. Handle resolution skipped: still green, filed as F4. After each mutation I restored the file and confirmed it by sha256.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Stale prose about the deleted done-toggle and interactive path

<!-- sq:finding:F2:body -->
The deletion left prose that describes code that no longer exists:

- The `_workflow/_models.py` module docstring (line 11) says `SubentityKindSpec.completion` "drives the done-toggle (`_services/_subentities.py`)". That file no longer has a done-toggle.
- The `SubentityKindSpec.completion` field docstring (line 344) and `check_completion_status` in `_workflow/_validity.py` (line 288) still call it "the done-toggle target". No code in `src` now reads `completion` except load validation and the `sq workflow subentity-kinds` listing. In practice it is a hint for clients ("the status a mark-done action should target", as `docs/workflow.md` puts it), and the prose should say that.
- The `_set_block_status_model` and `_set_block_assignee_model` docstrings in `_services/_subentities.py` (lines 236 and 380) say their core is "the interactive/apply path". The interactive wrappers are gone, so the importer's apply path is now the only caller.

Bring each sentence back to the present truth. These are docstring and comment edits only.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-28T12:38:34Z] `python-dev` Elias Python:
  - Fixed: completion and apply-path prose reworded in _models.py, _validity.py and _subentities.py.
- [2026-10-28T12:41:22Z] `reviewer` Paul Reviewer:
  - Verified. The prose in _models.py (lines 11 and 344), _validity.py (288) and _subentities.py (236 and 380) now states present truth: completion is the status a mark-done action targets, and the cores serve the apply path.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Multi-selector refusal names CLI flags, omits sub

<!-- sq:finding:F3:body -->
The refusal `target only one of --story / --subtask / --finding` can now be raised only from `sq import`. It names CLI flags that `sq <type> <n> comment` does not have, and it leaves out `sub`, one of the four import fields it guards. An adopter whose JSONL event sets `subtask` and `sub` gets a message about flags they never passed. TASK-1215 kept the message unchanged on purpose, so this is outside its scope and not a defect of this change. A follow-up could word the refusal in terms of the event's fields, for example "a comment event names at most one of story / subtask / finding / sub". The test from F1 would then pin the new wording.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-28T12:38:36Z] `python-dev` Elias Python:
  - Fixed: refusal now reads "a comment event names at most one of story / subtask / finding / sub"; pinned by the F1 test.
- [2026-10-28T12:41:24Z] `reviewer` Paul Reviewer:
  - Verified. The refusal now reads "a comment event names at most one of story / subtask / finding / sub", and the three two-selector cases pin the exact output.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Comment selector tests never name a sub-entity by handle

<!-- sq:finding:F4:body -->
The new tests for import comment selectors name the sub-entity only by its local id (`US1`, `ST1`, `F1`), never by a handle. The import format also accepts a handle as a selector, and the example in `docs/adoption.md` uses one: `{"op": "comment", "target": "form", "message": "…", "subtask": "render"}`. To falsify this, I replaced `handles.resolve_local(target, local)` in `_comment_selector` with the raw `local`. All 12 comment-event tests still passed. A change that stops comment selectors from resolving handles would therefore pass the suite.

Add one case where the selector names a handle declared by an `add-sub` event earlier in the same file. Cover both the per-kind field spelling (`"subtask": "<handle>"`) and the `sub` spelling (`"sub": ["subtask", "<handle>"]`), and assert that the comment lands on that sub-entity.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-28T12:43:12Z] `python-dev` Elias Python:
  - Fixed: handle-named selectors (field and sub forms, all three kinds) added to the import comment tests; skipping handle resolution in _comment_selector turns 6 of them red.
- [2026-10-28T12:44:49Z] `reviewer` Paul Reviewer:
  - Verified. Skipping handle resolution in the per-kind field branch of _comment_selector: 3 tests fail. Skipping it in the sub branch: 3 fail. I restored the file after each mutation and confirmed it by sha256.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T12:34:38Z] `reviewer` Paul Reviewer:
  - @python-dev @manager Verdict ChangesRequested. The no-behaviour-change claim holds: across 17 comment shapes, sq import output and the squad files match HEAD, and the three extra deletions are dead. Open: F1 (medium) is the missing import selector and refusal test. F2 (low) is stale done-toggle/interactive-path prose. F3 (low) is a follow-up on the refusal wording, outside the task scope.
- [2026-10-28T12:41:28Z] `reviewer` Paul Reviewer:
  - @manager @python-dev Re-review: F1, F2 and F3 are Verified. One new low finding, F4: no test passes a handle as a comment selector, and a mutation that skips handle resolution passes the suite. The docs example uses exactly that form. One more parametrized case closes it. tests/meta and tests/cli with -n 4: 1438 passed. Note for the changelog: the user-visible import refusal wording changed, and CHANGELOG.md has no entry for it. Verdict stays ChangesRequested until F4 is fixed.
- [2026-10-28T12:43:14Z] `python-dev` Elias Python:
  - @reviewer @manager F4 fixed and marked Fixed. Gates: pyright 0 errors, ruff clean, tests/meta+cli+check passed.
- [2026-10-28T12:44:51Z] `reviewer` Paul Reviewer:
  - @manager F4 is Verified, so F1-F4 are all Verified. tests/meta and tests/cli with -n 4: 1444 passed. I recommend Approved and have left REV-1216 in InReview: as its author I do not approve my own review, so the Approved transition is yours.
<!-- sq:discussion:end -->
