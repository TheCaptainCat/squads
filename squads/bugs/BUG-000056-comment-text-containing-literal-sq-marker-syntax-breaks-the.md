---
id: BUG-000056
sequence_id: 56
type: bug
title: Comment text containing literal sq marker syntax breaks the item's marker integrity
status: Verified
author: manager
priority: high
created_at: '2026-06-12T08:06:24Z'
updated_at: '2026-06-12T08:36:01Z'
---
<!-- sq:body -->
**Repro.** `sq feature 40 comment --as reviewer -m '… touches the sq:body region …'` where the message contains a *well-formed marker tag* (an HTML comment wrapping `sq:body` — not reproduced literally here, because the body guard rejects it). The comment text is appended verbatim into the discussion region, so `sq check` then reports 'duplicate marker' / 'unclosed marker' on the item file. Observed live on FEAT-000040, 2026-06-12.

**Root cause asymmetry.** `sq <type> <n> body` already rejects marker syntax ('body must not contain sq marker comments') — but `sq <type> <n> comment` has no such guard, so a comment can inject a tag that breaks marker integrity. Worse than the lint error: a later marker-based section edit could match the injected tag and corrupt the file.

**Expected.** The comment path gets the same protection as the body path: reject with the same clean SquadsError. Note that backtick-wrapping is NOT a neutralizer — `_sections.find_markers` matches a well-formed tag anywhere in the text, code spans included — so rejection (or stripping/breaking the tag on write) is the only safe option.

**Note.** There is no comment-edit command, so an injected marker requires a hand-edit to repair, which project rules otherwise forbid. The live occurrence on FEAT-000040 was repaired by hand (rewriting the tag as plain `sq:body` prose, dropping the HTML-comment wrapper) as a sanctioned one-off; this bug is the record of both the injection and the repair.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T08:06:49Z] Catherine Manager:
  - Filed from the live FEAT-000040 occurrence. @tech-lead to triage when picking the next hardening batch (candidate for FEAT-000017 1.0 hardening).
- [2026-06-12T08:19:40Z] Olivia Lead:
  - Triaged. Fix tracked as TASK-000057 (linked --kind fixes), priority high, assigned @python-dev.
  - Root cause confirmed: the body paths guard against marker syntax (find_markers) but comment messages and sub-entity titles do not. Comment text lands verbatim in the :discussion region; a sub-entity title renders into the block heading (re-derived by set_heading on every block mutation) and the :head table — so a title injection is PERSISTENT, worse than the comment case.
  - Fix contract: one shared SquadsError guard (same message family as the body guard), applied to comment messages and to sub-entity titles on create + update, rejecting BEFORE any write. Message must steer the author to drop the HTML-comment wrapper; backtick-wrapping is NOT a neutralizer. Item title/description confirmed safe (frontmatter only, not a marker region) — assert with a no-false-positive test. Full contract + path map in TASK-000057 body.
  - @python-dev over to you — TASK-000057 is Ready.
- [2026-06-12T08:26:54Z] Elias Python:
  - Fix implemented in TASK-000057 (now InReview). Shared guard reject_markers() added to src/squads/_services/_base.py; applied to comment messages in _collab.py and sub-entity titles (create + update) in _subentities.py. Existing body-guard paths unified to the same function. 295 tests pass, pyright + ruff clean.
  - New tests in tests/test_collab.py: comment with marker rejected, backtick-wrapped marker rejected, file left untouched on rejection, all -m messages validated, sub-entity-targeted comments guarded, add-story/add-subtask/add-finding titles rejected, update --title rejected, item update --title/--description false-positive check, body-guard message regression check. CLI smoke tests added to tests/test_cli.py.
  - @reviewer please review the guard function and its call sites; @qa please verify the rejection behaviour end-to-end.
- [2026-06-12T08:30:55Z] Paul Reviewer:
  - Reviewed the marker-guard fix (TASK-000057), uncommitted in the tree. VERDICT: APPROVE — no review item, no changes required.
  - Single shared guard: reject_markers(text, what='body') in _services/_base.py. All prose-into-marker-region paths now route through it — create body (_base.py:154), set_body (_items.py:151), comment incl. sub-entity-targeted (_collab.py:38-39, every -m validated before append_to_section), add-story/subtask/finding titles+bodies (all via _add_block:79-81), update --title (_update_block:296-297), sub-entity bodies (_set_block_body:323). The old per-class _reject_markers static is removed; both update_* and add_* wrappers converge on _update_block/_add_block, so the guard sits at the one chokepoint. set_heading re-derives the stored title on every block mutation, but the title is guarded at write-time, so the persistent re-corruption vector is closed at the source.
  - Validate-before-write holds on every path: each guard runs before store.transaction() / _locked_section_edit / any file write — no partial writes possible. Confirmed by test_comment_marker_leaves_file_untouched and live probe (file byte-identical after rejection).
  - Message contract correct: what='body' yields the verbatim legacy 'body must not contain sq marker comments' string (pinned by test_body_guard_message_unchanged); other labels get the extended message steering the author to drop the HTML-comment wrapper and noting backticks do not help. Renders cleanly through @handle_errors.
  - No false positives: _sections.find_markers regex is UNCHANGED and strict (sq: + alnum start). Legit [x] checkboxes, backtick spans, and plain sq:body prose all pass (test_item_update_title_description_not_affected + live probe). No looser regex introduced.
  - Gates all green on my machine: uv run pyright (0 errors), ruff check (clean), ruff format --check (clean), pytest (295 passed, 1 skipped). New coverage: 10 service tests in test_collab.py + 4 CLI smoke tests in test_cli.py; marker tags are built at runtime so the test files themselves stay clean under sq check.
  - Live probe in a throwaway /tmp squad: comment injection, add-subtask title injection, and backtick-wrapped comment all rejected with a clean error and the task file left byte-identical; a normal comment ([x] + code spans) and a legit '[x] ... sq:body' subtask title both succeeded and sq check reported no issues. No regression.
  - Informational (out of my review scope): the working tree also carries an unrelated change mixed into these files — Service.role_body() in _base.py:257 plus _cli/_role.py, role.md.j2, _maintenance.py, _interactions.py, claude_section.md.j2 and test_role_show_includes_body_and_degrades_for_bundled in test_cli.py. That is FEAT-000040/041 'sq role show' work, not the marker guard; I did not review it here. Whoever commits should split it from the BUG-000056 fix so the bug commit stays scoped. @manager — fix approved, ready to commit (marker-guard files only).
- [2026-06-12T08:35:54Z] Mara Tester:
  - QA verification of TASK-000057 fix: verified against throwaway squad at /tmp/qa56.
  - Test matrix — all cases exercised via CLI in throwaway squad:
  - 1. ORIGINAL REPRO (sq task 9 comment --as qa with a well-formed body marker tag): rejected, exit 1, clean SquadsError message pointing to the wrapper-less prose form; file byte-count unchanged, sq check clean.
  - 2. MULTI-MESSAGE (second -m carries the tag): rejected in full before any write; first message also absent from file (pre-write validation is atomic).
  - 3. OTHER MARKER TAG IN COMMENT (sq:discussion tag): rejected, exit 1, same message.
  - 4. SUB-ENTITY TITLE ON CREATE — add-story, add-subtask, add-finding each with a tag in title: all rejected, exit 1, message says 'title must not contain sq marker comments'.
  - 5. SUB-ENTITY TITLE ON UPDATE — story/subtask/finding update --title with tag: all rejected; original titles intact in frontmatter and heading/summary table.
  - 6. SUB-ENTITY BODY REGRESSION — task subtask st1 body with tag: rejected with the original 'body must not contain sq marker comments' wording (no message change, regression held).
  - 7. ITEM BODY REGRESSION — task 9 body with tag: same body-guard message, exit 1.
  - 8. FALSE POSITIVES — backtick-wrapped sq:body prose, plain sq:body prose, [x] checkboxes, brackets: all accepted, sq check clean.
  - 9. SPLIT TAG ACROSS MESSAGES — each message alone is not a well-formed marker (regex needs both open HTML-comment and close in one string): accepted, sq check clean. Correct behaviour.
  - 10. CLOSE-MARKER TAG ALONE (sq:body:end): rejected.
  - 11. UPPERCASE VARIANT (<!-- SQ:BODY -->): accepted (regex is lowercase-only). Symmetry confirmed: find_markers uses the same strict lowercase regex, so an uppercase tag is neither rejected by the guard nor parsed as a marker by the file parser — integrity is preserved regardless.
  - Full suite: uv run pytest — 295 passed, 1 skipped, 0 failures.
  - Verdict: fix is complete and correct. Transitioning to Done.
<!-- sq:discussion:end -->
