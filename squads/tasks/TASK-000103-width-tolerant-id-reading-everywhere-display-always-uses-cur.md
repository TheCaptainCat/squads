---
id: TASK-000103
sequence_id: 103
type: task
title: Width-tolerant ID reading everywhere; display always uses current padding
status: Done
parent: FEAT-000027
author: tech-lead
assignee: python-dev
refs:
- TASK-000101:depends-on
- REV-000106:addresses
subentities:
- local_id: ST1
  title: Width-tolerant ID equality across resolver/backrefs/check
  status: Done
  story: US3
created_at: '2026-06-14T20:56:35Z'
updated_at: '2026-06-23T09:58:32Z'
---
<!-- sq:body -->
Make ID READING tolerant of any width, since repad never rewrites file contents (TASK-000102): `TASK-000007` and `TASK-0000007` must resolve to the same item everywhere an ID is read. The number is the identity; the width is presentation.

## Current state (audit)
Good news — the lexical parsers ALREADY split on the trailing digit run, so they are width-agnostic by construction; the work is to confirm, centralise, and test:
- `_parse_item_token` (`_cli/_common.py:476`) — `rpartition('-')`, digits → int. Already tolerant.
- `number_for_id` (`_paths.py:130`) — `rsplit('-',1)`, int(). Already tolerant.
- `SquadsDB._seq` (`_models/_index.py:19`) — keys by trailing number. Already tolerant.
- `split_ref` (`_item.py`) — partitions on `:`, never on width.
- `backrefs` / `refs_in` invert on the rid string compared to `item_id`.

## The real risks to fix
1. **Equality on full-ID strings**: `backrefs`/`refs_in`/`blocked`/`_check_*` compare `split_ref(r)[0] == item_id` — a literal string compare that FAILS across widths (`TASK-000007` != `TASK-0000007`). After repad, refs hold the OLD width while items report the NEW width. Normalise both sides to the sequence number (or via the resolver) before comparing, everywhere an ID is matched against another ID.
2. **`rewrite_ids`** (`_itemfile.py:53`) does `\b{old}\b` literal substitution — width-sensitive. Audit whether it needs width-tolerance (it is used by renumber, which assigns fresh ids, so possibly fine — confirm and document).
3. **Prose mentions / `sq check`**: dangling-ref and parent checks must treat mixed-width as resolved.

## Where it lands
Per FEAT-000019, centralise comparison/normalisation in the shared resolver layer (`_index/_resolver.py`) — add a normalise-to-sequence helper and route ID-equality through it. Display ALWAYS uses current padding (handled by the formatter from TASK-000101).

## Tests (mixed-width fixture)
A fixture squad where item files were renamed to a wider padding but bodies/refs/parent keep the old width: refs resolve, backrefs invert, `sq tree`/`show` address correctly, `sq check` is clean, and display shows the current (new) width throughout.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 103 add-subtask "<title>"`; track with `sq task 103 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Width-tolerant ID equality across resolver/backrefs/check | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Width-tolerant ID equality across resolver/backrefs/check

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a teammate whose items hold old-width refs and mentions, I want ID parsing tolerant of any padding, so that content written before the raise keeps resolving forever
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Width-tolerant ID equality in resolver/backrefs/check; mixed-width refs+mentions+parent+CLI args resolve; display uses current padding; mixed-width fixture tests.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-14T21:49:41Z] Elias Python:
  - Implemented width-tolerant ID reading (FEAT-000027 / TASK-000103). Implementation is complete, 578 tests pass (15 new), pyright + ruff clean.
  - **Normalisation approach — centralised in two places:**
  - 1. _models/_index.py: Added SquadsDB._propagate_padding() (model_validator mode=after) — when a SquadsDB is deserialized from JSON (i.e. store.load()), it immediately sets id_padding=db.padding on every item. This ensures item.id always returns the current-padding-width ID everywhere, fixing the 'display uses current padding' requirement without any caller changes.
  - 2. _index/_resolver.py: Added seq_for_id() as the canonical normalisation helper, wrapping number_for_id(). This is the declared FEAT-000019 shared resolver location.
  - **Surfaces fixed:**
  - - SquadsDB.backrefs() (_models/_index.py): switched from split_ref(r)[0] == item_id string comparison to (prefix, seq) comparison — prevents cross-type false positives during renumber and tolerates width variance.
  - - RefsMixin.add_ref() / rm_ref() (_services/_refs.py): added _id_matches() helper that compares by (prefix, seq); dedup filter and removal use it instead of literal string comparison. add_ref stores the caller's to_id string (not tgt.id) to preserve the original width in frontmatter.
  - - RefsMixin.refs_in() (_services/_refs.py): switched to (prefix, seq) comparison via _id_matches().
  - - MaintenanceMixin._scan_for_check() (_services/_maintenance.py): changed on_disk dict from keyed by fid (full-ID string) to keyed by int sequence number — makes all reconciliation comparisons width-tolerant by design.
  - - MaintenanceMixin._check_reconciliation(): compares index_seqs vs on_disk seq keys.
  - - MaintenanceMixin._check_items(): looks up on_disk by item.sequence_id instead of item.id.
  - - MaintenanceMixin._check_decisions(): stores sequence numbers in has_incoming_supersedes set.
  - - _cli/_main.py tree command: extracted _build_children() helper that resolves item.parent (possibly old-width) to the current-width canonical ID via seq_to_id lookup — fixes sq tree showing old-width-parent items as roots instead of children.
  - **New files (TASK-103 only):** none — all changes are to existing files.
  - **Modified files:** src/squads/_models/_index.py, src/squads/_index/_resolver.py, src/squads/_services/_refs.py, src/squads/_services/_maintenance.py, src/squads/_cli/_main.py, tests/test_index.py (5 new tests), tests/test_service.py (10 new tests), tests/test_cli.py (3 new CLI tests).
  - **End-to-end acceptance (FEAT-27 US3):** test_end_to_end_repad_resolution builds a squad with cross-refs and parent links at width-6, runs repad(7), then asserts: all items display at width-7; old-width parent resolves; refs_in and backrefs find cross-refs; sq check is clean with no errors. The joint TASK-102/103 seam is covered.
  - @reviewer — ready for review. The key design decisions to validate: (1) _propagate_padding model validator is the right place to propagate padding to items; (2) (prefix, seq) rather than seq-only for backrefs/refs_in to prevent cross-type false positives; (3) on_disk keyed by int seq in _scan_for_check/check_reconciliation.
- [2026-06-14T21:57:41Z] Paul Reviewer:
  - REV-000106 ChangesRequested. TASK-103 owns F1 (medium, blocking) + F3 (low, test gap). F1: repair()'s missing_ids comparison breaks across a repad boundary because _propagate_padding widens prev item ids while from_frontmatter does not — 'sq repair' then warns that every file is missing. Compare by sequence_id (mirror _check_reconciliation). F3: extend test_end_to_end_repad_resolution to call repair() post-repad and assert missing_ids == []. The rest of the width-tolerant work (resolver, refs, backrefs, check, tree, cross-type guard) is correct. @python-dev
- [2026-06-14T22:00:49Z] Elias Python:
  - F1 (REV-000106, medium, blocking): Fixed spurious repair() missing_ids after repad.
  - Root cause: repair() built previous_ids as a set of full-ID strings; _propagate_padding had widened those to the new padding (e.g. 'TASK-0000003') while from_frontmatter below rebuilt items at the default width ('TASK-000003'), so the set difference was the entire corpus.
  - Fix (_maintenance.py:174-181): changed previous_ids:set[str] to previous_seq_to_id:dict[int,str] (keyed by sequence_id int). found_ids:set[str] becomes found_seqs:set[int]. missing_ids is computed as [previous_seq_to_id[s] for s in sorted(previous_seq_to_id.keys() - found_seqs)] — width-tolerant by construction, mirrors the seq-keyed approach already used in _check_reconciliation.
  - F3 (REV-000106, low, test gap): Added test_repair_after_repad_no_spurious_missing (tests/test_service.py). Confirmed it FAILED against the F1 bug (reported ['BUG-0000004', 'FEAT-0000002', 'ROLE-0000001', 'TASK-0000003']) and passes after the fix.
  - Full gate: 579 passed, 1 skipped; pyright 0 errors; ruff clean.
  - @reviewer — F1 and F3 fixed. Ready for re-review.
- [2026-06-14T22:06:25Z] Paul Reviewer:
  - REV-000106 Approved. F1 (spurious repair missing_ids across a repad boundary, medium/blocking) and F3 (missing repair-after-repad test) verified fixed — repair() compares by sequence_id; new test guards the path and provably fails against the bug. Done / ready to merge. @manager FEAT-000027 acceptance fully met.
<!-- sq:discussion:end -->
