---
id: REV-1164
sequence_id: 1164
type: review
title: Review the services comment sweep and version guard
status: Approved
author: reviewer
refs:
- TASK-1127
description: 'Commit 62518566: TASK-1127 ST1 version guard and ST2 services docstring
  sweep.'
subentities:
- local_id: F1
  title: remove_block docstring now claims a freed local id is never reissued; next_local_id
    reissues the highest
  status: Verified
  severity: medium
- local_id: F2
  title: _offset_plan lost the disjoint-range invariant that makes the single-pass
    rewrite_ids order-independent
  status: Verified
  severity: medium
- local_id: F3
  title: '_parent_acyclic lost the ordering that keeps update --no-parent working:
    clear_parent before the gate'
  status: Verified
  severity: medium
- local_id: F4
  title: 'read_body lost its caller contract: writers never read through it, so expanded
    views never reach disk'
  status: Verified
  severity: medium
- local_id: F5
  title: 'Import module docstring lost why the pre-pass reads files: a mid-apply refusal
    leaves a partial batch'
  status: Verified
  severity: medium
- local_id: F6
  title: Pure model halves dropped the throwaway-copy note that squares the importer's
    allocation with invariant 2
  status: Verified
  severity: low
- local_id: F7
  title: VALIDATOR_CONTEXT lost why error-level subentity_container_marker deliberately
    never gates writes
  status: Verified
  severity: medium
- local_id: F8
  title: 'ItemFilter.category comment mangled: stray prefix before #: and continuation
    lines lost the #: marker'
  status: Verified
  severity: low
- local_id: F9
  title: Deprecated linearize_lifecycle alias lost its removal trigger; record it
    on the board or CHANGELOG
  status: Verified
  severity: low
- local_id: F10
  title: 'History residue left in swept services files: 12 references to removed _check_*
    functions, today phrasing'
  status: Verified
  severity: low
- local_id: F11
  title: Version guard is blind to major-1 versions and to attribute docstrings
  status: Verified
  severity: low
- local_id: F12
  title: Several rewrites are now less precise than the code or wrong (alignment fallback,
    retype carry, others)
  status: Verified
  severity: low
- local_id: F13
  title: 'Fix collateral: _create_model lost the fields-after-priority rule; vocab
    comment misstates the except'
  status: Verified
  severity: low
- local_id: F14
  title: 'Residue: _repair_held comment still cites the removed _check_reconciliation'
  status: Verified
  severity: low
- local_id: F15
  title: 'Widened version guard flags legitimate prose numbers: 0.5 ratios, in 2.5
    seconds, TOML version 1.0'
  status: Verified
  severity: low
- local_id: F16
  title: Narrowed version guard catches 6 of the 15 real historical hits; a safe middle
    ground catches 11
  status: Verified
  severity: medium
created_at: '2026-10-26T12:44:43Z'
updated_at: '2026-10-26T13:17:48Z'
---
<!-- sq:body -->
Review of commit 62518566 (TASK-1127 ST1 and ST2): the release-version guard `tests/meta/test_source_comments_and_docstrings_name_no_release_version.py` and the docstring/comment sweep of `src/squads/_services/`, plus the twelve version hits cleared in `_index/_reflog.py`, `_models/_schema.py`, `_overrides/_manifest.py`, `_overrides/_stamp.py`, `_rendering/_engine.py` and `_util.py`.

## Scope and method

- Read the deleted text of every hunk in the 24 services files and the other changed files. For each removed sentence the question was whether it carried a constraint (invariant, ordering, transaction rule, why-not, caller contract, trap) the code does not show and the new text drops.
- No code change: the docstring-stripped AST of all 29 changed `src/` files equals the parent commit's. I checked this with my own script; it also strips bare string statements.
- Guard: the targeted run passes (9). A comment and a docstring planted in a copy of `_base.py` are both caught, and a string literal is not.

## Result

Most of the sweep is a real judgement. The skew-direction, unlink-before-commit, confirm-round, rename-atomicity, third-state, Mermaid-escape and delta-scoped retirement constraints all survive in one or two sentences. The findings are the places where a constraint was cut, where a rewrite is now wrong or garbled, and some residue that was missed.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1164 add-finding "…" --severity medium`; track with `sq review 1164 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — remove_block docstring now claims a freed local id is never reissued; next_local_id reissues the highest

<!-- sq:finding:F1:body -->
`src/squads/_services/_subentities.py`, `remove_block` docstring, new text:

> a freed local id is not reissued in the same run (see :func:`discussion.next_local_id`)

This is false. `next_local_id` (`_discussion.py:366`) recomputes from the live set's max, so removing the highest-numbered sub-entity frees its number for the next `add-<kind>`. Its own docstring says so. The deleted text kept that caveat ("never reissued to a *different* future sub-entity ... see the note on next_local_id for the one case that isn't fully covered"). The rewrite drops the caveat and states the opposite.

Fix: say that a removed non-highest id stays a gap and that the highest one can be reissued, or just point to `next_local_id` without claiming anything.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T12:59:37Z] `python-dev` Elias Python:
  - Fixed: remove_block now says a removed id below the highest stays a gap and removing the highest frees its number (next_local_id).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — _offset_plan lost the disjoint-range invariant that makes the single-pass rewrite_ids order-independent

<!-- sq:finding:F2:body -->
`src/squads/_services/_maintenance.py`, `_offset_plan` docstring. The deleted text:

> Because the new range sits strictly above the old local range, no new id string in the remap ever equals an old one, so the single-pass whole-word `rewrite_ids` substitution is order-independent — no high-to-low ordering machinery is needed here, unlike an in-place/overlapping shift would require.

This is the invariant that makes `_apply_remap`'s single substitution pass correct for `sq renumber`. The code shows the delta formula but not why the range has to be disjoint. If someone relaxes `delta` (for example to allow an overlapping `--by`), chained substitutions corrupt ids silently. The new docstring keeps the safety arithmetic but loses this reason. Restore it in one sentence.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T12:59:40Z] `python-dev` Elias Python:
  - Fixed: _offset_plan states the new range sits above the old, so no new id equals an old one and the single-pass rewrite_ids is order-independent.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — _parent_acyclic lost the ordering that keeps update --no-parent working: clear_parent before the gate

<!-- sq:finding:F3:body -->
`src/squads/_services/_validators.py`, `_parent_acyclic` docstring. The new text says "An item in a cycle cannot be updated, but `update --no-parent` works". The deleted text gave the reason:

> it is safe because `clear_parent` nulls `item.parent` before the gate reads it, so `update --no-parent` still succeeds on an item inside a cycle.

That is an ordering requirement on `ItemsMixin._update_model` (`clear_parent` applied before `ValidatorEngine.gate`). Without it, a reorder turns every cycle into a lock-out with no CLI way out. The new sentence states the outcome as a fact and drops the ordering it depends on. Restore the ordering clause, here or as a comment at the `clear_parent` site in `_update_model`.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T12:59:42Z] `python-dev` Elias Python:
  - Fixed: _parent_acyclic says update --no-parent works because _update_model applies clear_parent before the gate; a comment at the clear_parent site records the ordering. Checked against _update_model.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — read_body lost its caller contract: writers never read through it, so expanded views never reach disk

<!-- sq:finding:F4:body -->
`src/squads/_services/_items.py`, `read_body` docstring. The deleted text:

> Read-only: the body-*write* path (`set_body`'s `mutate` closure) reads the region directly and never through here, so expanded bytes never reach disk.

The new text keeps only "It is read-only". The constraint is a caller contract, not a property of the method: no writer may source its text from `read_body`, or rendered view output (an expanded `sq:view:<name>` tag) gets persisted over the tag. Nothing in `read_body`'s code shows that. Restore the "writers never read through here" clause.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T12:59:45Z] `python-dev` Elias Python:
  - Fixed: read_body states no writer may source its text from here, or expanded view output is persisted over the tag.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Import module docstring lost why the pre-pass reads files: a mid-apply refusal leaves a partial batch

<!-- sq:finding:F5:body -->
`src/squads/_services/_import.py`, module docstring. The new text says that the pre-pass "pre-flights the skew guard by reading each targeted pre-existing `.md` once", but no longer says why. The deleted reason:

> This keeps a mid-apply refusal — which would leave the batch partially applied, since the markdown writes of everything already applied stand per the write-path ordering rule — off the table entirely: a drifted target is reported as a pre-pass issue instead, and the apply pass never runs.

This is the design rule of the importer: anything that could refuse during apply has to be pre-flighted, because apply cannot roll back markdown that is already written. A reader adding a new op will not find that rule anywhere else. Keep one sentence of it.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T12:59:47Z] `python-dev` Elias Python:
  - Fixed: the import module docstring says the pre-pass reads each target file because an apply-time refusal would leave the batch partly applied.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Pure model halves dropped the throwaway-copy note that squares the importer's allocation with invariant 2

<!-- sq:finding:F6:body -->
The pure `_X_model` halves no longer say that the importer runs them against a throwaway, never-persisted index copy:

- `_services/_base.py`, `_create_model`: lost "against a throwaway, never-persisted `db` copy ... including the id allocation, invariant #2's 'simulate only' contract". The new text reads "Shared by `_create_core` and the bulk importer's pre-pass".
- `_services/_items.py`, `_set_status_model`: now "Shared with the importer's pre-pass".
- `_services/_subentities.py`, `_add_block_model`: now "Shared by `_add_block_core` and the bulk importer's pre-pass".

`_create_model` calls `db.allocate_id`. Invariant #2 allows allocation only inside `IndexStore.transaction()`, and the only reason this pure half may allocate is that the second caller passes a disposable copy. Read as written now, the method looks like an allocation outside a transaction. `_update_model` and two other pure halves in `_subentities.py` still mention the throwaway copy, so the rewrites are inconsistent with each other too. The import module docstring does state it, but a reader of `_create_model` does not get there. Restore the clause at least on `_create_model`.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-26T12:59:50Z] `python-dev` Elias Python:
  - Fixed: _create_model, _set_status_model and _add_block_model say the importer runs them on a throwaway db copy; _create_model ties it to invariant 2.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — VALIDATOR_CONTEXT lost why error-level subentity_container_marker deliberately never gates writes

<!-- sq:finding:F7:body -->
`src/squads/_services/_validators.py`, the `#:` comment above `VALIDATOR_CONTEXT`. The deleted text explained why `subentity_container_marker` reports at **error** level yet never gates create/update:

> its condition is a corpus/spec disagreement no create or update causes and none can cure, and gating would refuse ordinary edits on every item of the type at once

The new comment says only "Listed members sit the create/update gate out". An error-level member that does not gate looks like a bug someone should fix by dropping its context requirement, and the consequence of doing so (every edit on the type refused) is exactly what the deleted sentence warned against. Keep that why-not in one sentence.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-26T12:59:52Z] `python-dev` Elias Python:
  - Fixed: the VALIDATOR_CONTEXT comment says subentity_container_marker is error-level yet sits the gate out because no edit causes or cures its mismatch, so gating would block every edit on the type.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — ItemFilter.category comment mangled: stray prefix before #: and continuation lines lost the #: marker

<!-- sq:finding:F8:body -->
`src/squads/_services/_base.py:156`, `ItemFilter.category`:

```
    #     #: Category filter (``roster``/``work``/``records``): matches when the item's type
    # declares it, and never matches without ``spec``, like ``badge_min``. The value is validated at
    # the CLI edge against ``squads._workflow.CATEGORIES``.
```

This is a botched rewrite. A stray `#     ` prefix sits in front of the `#:` marker, and the continuation lines lost `#:`, so this no longer reads as an attribute doc comment like its neighbours (`badges`, `badge_min`). Restore the `#:` prefix on all three lines and drop the duplicate marker.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-26T12:59:55Z] `python-dev` Elias Python:
  - Fixed: ItemFilter.category comment restored to a three-line #: doc comment.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Deprecated linearize_lifecycle alias lost its removal trigger; record it on the board or CHANGELOG

<!-- sq:finding:F9:body -->
`src/squads/_rendering/_engine.py` (~line 124), the DEPRECATED `linearize_lifecycle` global alias. The old comment gave a concrete removal trigger ("Drop this line (and only this line) once 0.15.x is no longer a supported upgrade source"). The new comment says "Drop this line once that form is no longer supported", which nobody can act on: nothing says when that is.

Removing the version from source prose is correct under the rule, but the trigger has to live somewhere. Record it on the board (an item to remove the alias, naming the release) or in the CHANGELOG deprecation note, and keep the comment pointing at that record, not at a version.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-26T12:59:57Z] `python-dev` Elias Python:
  - Fixed: the code was not what held the trigger. The old trigger (a supported-upgrade-source policy) has no record in the CHANGELOG, the board or docs, so the comment now says no removal trigger is defined and the alias is dropped only when the project declares such overrides unsupported.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — History residue left in swept services files: 12 references to removed _check_* functions, today phrasing

<!-- sq:finding:F10:body -->
History residue is still present in swept `_services/` files:

- `_validators.py`: 12 docstrings still open with `← _check_items` / `← _check_*`, naming the pre-catalog functions each validator replaced. Those functions no longer exist (`grep "def _check_items"` returns nothing). The task approach says names of methods that do not exist move out of the code. The sweep removed one (`_backend_reconciled`'s `← _check_backends`) and left the other twelve.
- "today" phrasing: `_check.py:359` ("keeps today's wording"), `_validators.py:235` ("today's lenient 'any parent or none'"), `_config_integrity.py:115`, `_retirement.py:64`.

Clear these in ST2's scope, or carry them explicitly into ST5.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-26T13:00:00Z] `python-dev` Elias Python:
  - Fixed: removed the 12 "<- _check_*" openers in _validators.py (each now states what the validator checks) and the "today" phrasing in _check, _validators, _config_integrity and _retirement.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Version guard is blind to major-1 versions and to attribute docstrings

<!-- sq:finding:F11:body -->
`tests/meta/test_source_comments_and_docstrings_name_no_release_version.py`. The liveness rows are real: I planted `# removed in 0.16` and a `Since v0.12.1` docstring in a copy of `_base.py`, and both were caught; a string literal `"since 0.15"` was not. The guard has two blind spots, though:

1. `_VERSION` only matches major-zero versions (`v?0\.N`). The sweep itself shows this: `_util.py`'s example changed from `0.14 == 0.14.0` to `1.4 == 1.4.0`, which the pattern does not see, and neither will it see any real release reference once squads reaches 1.x. Consider `v?[0-9]+\.[0-9]{1,2}(\.[0-9]+)?` with an anchoring word ("in", "since", "v", "release") or an explicit allowlist of example numbers. At the least, name the major-0 limit in the module docstring.
2. Only module, class and function docstrings are read. The tree has 27 bare string statements used as attribute docstrings, which the scan skips. None of them holds a version today, so this is a coverage gap, not a current escape.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-26T13:00:02Z] `python-dev` Elias Python:
  - Fixed: the guard now matches major-zero 0.N, any vN.N, and N.N after in/since/from/until/before/after/release/version/squads, and reads bare string statements (attribute docstrings). New liveness rows: attribute docstring, v1.2.0, "release 2.10", plus negatives for Python 3.14 and other numbers. The tree has no hits. _util.py example no longer uses a version-shaped number.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Several rewrites are now less precise than the code or wrong (alignment fallback, retype carry, others)

<!-- sq:finding:F12:body -->
Some rewrites are now less precise than the code, or wrong:

- `_maintenance.py`, `_corpus_alignment_refusals`: "With `known_corpus`, ... ; otherwise the bundled location is checked on disk." The code runs the bundled-location fallback for every type absent from `known_types`, even when `known_corpus` is given (a type the previous index held zero items for). "Otherwise" says it runs only without `known_corpus`.
- `_retype.py`, `retype`: "Status is carried when both types share a workflow". It also requires the current status to be a state of the new workflow (`_carry_or_reset_status`).
- `_base.py`, `_section_edit_core`: "``base`` is captured before ``mutate`` for the skew guard, the second write seam after update_frontmatter" is garbled: it is the method, not `base`, that is the second frontmatter write seam. It also dropped the `mutate` contract ("sync callable — may raise to abort before any write").
- `_maintenance.py`, `_repair_held`, the `validate_vocab=False` comment: "repair recovers from vocab drift that the fail-closed load() would raise on, losing the counter high-water mark" no longer says that the loss lets a freed sequence number be reissued, and it reads as though repair loses the mark.
- `_base.py`, `reject_markers`: "needs told what to write instead" is ungrammatical.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-26T13:00:05Z] `python-dev` Elias Python:
  - Fixed: alignment fallback now covers every type absent from known_corpus; retype says the status must be a state of the new workflow; _section_edit_core attributes the seam to the method and restores the mutate contract; the validate_vocab comment says the loss lets a freed number be reissued; reject_markers wording fixed.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Fix collateral: _create_model lost the fields-after-priority rule; vocab comment misstates the except

<!-- sq:finding:F13:body -->
The F6 and F12 fixes cost two constraints the sweep had kept:

- `_services/_base.py`, `_create_model`: the sentence "``fields`` is a badge-code map applied after ``priority``" is gone. It was the remnant of "additive, so a code also present in `fields` simply wins": a caller passing both `priority=` and `fields={"priority": ...}` gets the `fields` value, and the code alone does not tell you that is intended. Restore it.
- `_services/_maintenance.py` (~line 1458), the `validate_vocab=False` comment now ends with "An unreadable index still raises." The previous wording said "still raises into the except below", and that matters: the `except SquadsError` right after it swallows the error and treats the index as empty, so read on its own the new sentence says the opposite of what happens. Say it is caught and treated as absent.

Minor, and no action needed: `VALIDATOR_CONTEXT`'s comment no longer mentions that a `tests/meta` guard re-derives the table. The guard still exists and will tell anyone who adds a member.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-26T13:13:22Z] `python-dev` Elias Python:
  - Fixed: _create_model says fields is applied after priority so it wins on a repeated code; the validate_vocab comment now says a genuinely unreadable index is caught below and treated as empty.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Residue: _repair_held comment still cites the removed _check_reconciliation

<!-- sq:finding:F14:body -->
`src/squads/_services/_maintenance.py:1452-1453`, in `_repair_held`:

```
# Keyed by sequence_id (int) so the comparison is width-tolerant: a repadded index widens id
# strings while from_frontmatter rebuilds at the default width (mirrors
# _check_reconciliation).
```

`_check_reconciliation` no longer exists (`grep -rn "def _check_reconciliation" src` finds nothing); it became the `index_reconciled` validator. This is the same class as F10, in a file F10's sweep did not reach. Point it at `_index_reconciled` or drop the parenthesis.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-26T13:13:25Z] `python-dev` Elias Python:
  - Fixed: the _check_reconciliation reference now reads "as index_reconciled does".
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Widened version guard flags legitimate prose numbers: 0.5 ratios, in 2.5 seconds, TOML version 1.0

<!-- sq:finding:F15:body -->
I planted versions in the widened `_VERSION` (`tests/meta/test_source_comments_and_docstrings_name_no_release_version.py`) in a copy of `_base.py` and in snippets.

Caught, as intended: `# removed in 0.16`, a `Since v0.12.1` docstring, an attribute docstring "Changed in 0.15", `v1.0`, `since 1.2`, `squads 1.3.0`, and "since" wrapped onto the next docstring line before 1.2.

Not flagged, correctly: `Python 3.14`, a `"since 0.15"` string literal, a PEP 440 example, the `"1.2"` schema example and `1.5x`.

False positives on legitimate prose numbers:

- `"Fails when more than 0.5 of the rows differ."` flags `0.5`, and `# waits 0.25 s before retrying` flags `0.25`. The bare major-zero branch matches every decimal below 1.
- `"Retries in 2.5 seconds."` flags `in 2.5`, `# clamps from 1.0 to 2.0` flags `from 1.0`, and `"Parses TOML version 1.0 documents."` flags `version 1.0`. These are the anchor words used for measurements and third-party versions.

Nothing in the tree hits any of these today, so the suite is green. But the guard has no allowlist and its failure message does not say what to do, so the first docstring documenting a 0.5 threshold or a TOML 1.0 dependency will be forced into awkward rewording.

Suggested fix, pick one:
- Narrow the bare branch to release-shaped tokens (`0.N.N`, `0.N.x`, or `0.N` followed by a word such as "release" or "upgrade").
- Exclude an anchor followed by a unit or a known third-party name.
- At minimum, put the remedy in the assertion message.

Add the negatives above as rows.
Missed (the gap is acceptable, but should be noted in the module docstring): an anchor placed after the number, as in "the 1.2 release".
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-26T13:13:27Z] `python-dev` Elias Python:
  - Fixed: the guard matches only a v-prefixed number, a three-part N.N.N, or N.N right after squads, release or schema. Negative rows added for ratio, seconds, "in 2.5 seconds", "from 1.0 to 2.0", "TOML version 1.0", Python 3.14 and a string literal; liveness rows kept for real shapes. The failure message gives a one-line remedy, and the module docstring states what is deliberately not caught (bare two-part numbers named only by context, such as "added in 0.15" or "the 1.2 release").
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — Narrowed version guard catches 6 of the 15 real historical hits; a safe middle ground catches 11

<!-- sq:finding:F16:body -->
The F15 fix fixed the false positives but narrowed the guard further than needed. This project's releases are two-part `0.N`, so the shapes its own prose actually uses are now mostly invisible.

I measured the narrowed `_VERSION` against the parent-of-62518566 text of the seven files ST1 cleared. These are the real hits the guard exists for: 15 occurrences, ST1's "12" counted per site.

| Regex | Caught | Notes |
|---|---|---|
| ST1 `v?0.N` | 15 | false positives on ratios |
| narrowed (HEAD) | 6 | `0.13.0`, `0.4.0`, `0.3.0`, `0.15.0`, `0.14.0`, `schema 0.4` |
| middle ground below | 11 | |

What the narrowed guard misses:
- `_index/_reflog.py`: "schema < 0.4", twice. The comparator breaks the `schema` anchor.
- `_rendering/_engine.py`: "scaffolded ... on 0.14.x" and "once 0.15.x is no longer a supported upgrade source". These are genuine release references, and that comment block was caught only through a neighbouring `0.15.0`.
- `_overrides/_manifest.py`: "first tracked at 0.13.0" is still caught; a "since 0.4" phrasing would not be.
- Correctly let through: the `"v": "0.4"` sample value in the reflog docstring and the `0.1`/`0.2` schema examples in `_models/_schema.py`. These are format examples, not release references.

A middle ground that adds no false positive:

```
\bv[0-9]+\.[0-9]+(?:\.[0-9]+)?\b
|\b[0-9]+\.[0-9]+\.(?:[0-9]+|x)\b
|\b(?:squads|release|schema)\s*(?:[<>]=?|==)?\s*[0-9]+\.[0-9]+\b
|\b(?:since|until)\s+[0-9]+\.[0-9]+\b
```

It adds the `.x` suffix, an optional comparator after the anchor word, and `since`/`until`. It leaves out `in`/`from`/`after`, which are where measurements live. On the same corpus it catches 11 of 15; the 4 misses are the format examples above.

It flags none of these: "0.5 of the rows", "0.25 s", "in 2.5 seconds", "from 1.0 to 2.0", "TOML version 1.0", "in 0.5 s", "from 0.1 to 0.9", "Python 3.14", "1.5 and 10.4". It has no hits on the current tree.

One thing both shapes share: the three-part branch matches inside an IPv4 address (`192.168.0.1`). There are none in source prose, so this is not an issue today.

"Added in 0.15" stays out of reach. Accepting that is fine, and the docstring says so. But the comparator, `.x` and since/until cases are cheap and unambiguous. Adopt them, and add the reflog, engine and since/until shapes as positive rows.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-26T13:16:57Z] `python-dev` Elias Python:
  - Fixed: the guard also matches a three-part number ending in .x and an optional comparison operator after squads/release/schema/since/until; in/from/after stay out. Liveness rows added for "schema < 0.4", "on 0.14.x", "since 0.15", "until 0.16"; negatives kept plus "in 0.5 s" and "from 0.1 to 0.9". The docstring lists what is still deliberately missed.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T12:45:23Z] `reviewer` Paul Reviewer:
  - Verdict: changes needed, so the review stays InReview. The diff changes no code: the docstring-stripped ASTs of all 29 changed files match the parent commit. The guard is live and does not flag string literals. The sweep keeps most of the integrity constraints. What remains is 12 findings: 7 medium and 5 low, prose-only.
    
    - One rewrite is now false (F1, remove_block local-id reissue).
    - Five integrity or ordering constraints were cut and need one sentence back each: F2 renumber disjointness, F3 clear_parent before the gate, F4 read_body writer contract, F5 the importer's pre-flight rationale, F7 why an error-level validator never gates.
    - The lows are an invariant-2 note (F6), a mangled comment (F8), a deprecation trigger with no record (F9), residue in swept files (F10), guard blind spots (F11) and imprecise rewrites (F12).
    
    @python-dev: these are all docstring and comment fixes in `src/squads/_services/` plus one test regex, so they fit before ST3 starts. Re-grep the deleted wording of any other cut why-not you find while you are in there.
- [2026-10-26T13:00:08Z] `python-dev` Elias Python:
  - All 12 findings addressed, prose and one test regex only; AST of changed src files equals the pre-sweep AST. pyright, ruff and every test directory at -n 4 pass; sq check run below.
- [2026-10-26T13:10:57Z] `reviewer` Paul Reviewer:
  - Re-review of eb68ffe5: F1 to F12 are Verified and three new low findings are filed, so the review stays InReview.
    
    - Each restored sentence matches the code. F1: reissue of the highest id. F2: the disjoint range. F3: `clear_parent` before the gate, now stated at both sites. F4: no writer reads through `read_body`. F5: a refusal during apply leaves a partial batch. F6: throwaway copy on all three pure halves. F7: why the error-level marker check never gates. F9's "no trigger defined" is now true, which is acceptable. The F12 corrections match `_corpus_alignment_refusals` and `_carry_or_reset_status`.
    - No code changed: the docstring-stripped AST matches the parent for all 12 `src/` files, by my own check. A scan of every file touched since 62518566 found no broken comment prefixes, merged lines or doubled words. A few docstrings wrap their first line early, which is cosmetic.
    - New findings: F13, the fix commit dropped `_create_model`'s fields-after-priority rule, and the `validate_vocab` comment now says the error raises where the code catches it. F14, a `_check_reconciliation` reference is left in `_repair_held`. F15, the widened guard catches every planted release version, including major-1 and attribute docstrings, but flags `0.5` ratios, "in 2.5 seconds" and "TOML version 1.0".
    
    @python-dev: F13 to F15 are prose plus the guard regex.
- [2026-10-26T13:15:13Z] `reviewer` Paul Reviewer:
  - Re-review of 3b6d8e27: F13–F15 are Verified. F13: the fields-after-priority rule is restored, and the comment now says the except catches the error and treats the index as empty. F14: the comment points at `index_reconciled`. F15: the five prose numbers no longer match, and the assertion carries the remedy. The guard tests pass (19).
    
    New finding F16 (medium): the narrowed guard catches 6 of the 15 real version hits ST1 cleared. It misses "schema < 0.4" and the "0.14.x"/"0.15.x" upgrade-source lines. The middle ground in F16 (`.x` suffix, a comparator after the anchor word, since/until) catches 11, still matches none of the false-positive probes, and is clean on the current tree. Review stays InReview until that lands. @python-dev
- [2026-10-26T13:17:47Z] `reviewer` Paul Reviewer:
  - Verified 8fcfdf60: the guard now catches 11 of the 15 historical version hits; the 4 it misses are format examples. It flags none of the 10 false-positive probes, finds nothing in the current tree, and its tests pass (25). All 16 findings are Verified. Approved.
<!-- sq:discussion:end -->
