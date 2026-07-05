---
id: REV-48
sequence_id: 48
type: review
title: FEAT-000019 — uniform item addressing
status: Approved
author: reviewer
refs:
- FEAT-19:addresses
subentities:
- local_id: F1
  title: Type-mismatch wording differs between full-ID and bare-number forms
  status: Verified
  severity: medium
- local_id: F2
  title: Unknown-item error wording drifts across the four resolver branches
  status: Verified
  severity: medium
- local_id: F3
  title: 'Dead code: old resolve_item_id; lexical munging now written 3x'
  status: Verified
  severity: low
- local_id: F4
  title: 'Grammar: ''not a operator''/''not a epic'' a/an agreement in mismatch msgs'
  status: Verified
  severity: low
created_at: '2026-06-11T14:19:22Z'
updated_at: '2026-06-23T09:59:52Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 48 add-finding "…" --severity high`; track with `sq review 48 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | Type-mismatch wording differs between full-ID and bare-number forms |
| F2 | 🟡 medium | Verified |  | Unknown-item error wording drifts across the four resolver branches |
| F3 | 🟢 low | Verified |  | Dead code: old resolve_item_id; lexical munging now written 3x |
| F4 | 🟢 low | Verified |  | Grammar: 'not a operator'/'not a epic' a/an agreement in mismatch msgs |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Type-mismatch wording differs between full-ID and bare-number forms

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Type-mismatch wording is inconsistent on typed surfaces depending on input form. For the SAME item, 'sq task 2 show' errors '2 is FEAT-000002 (feature), not a task' (names actual item+type, matches the recorded decision) but 'sq task FEAT-000002 show' errors 'FEAT-000002 is not a task (expected TASK-…)' — it never tells the user FEAT-000002 IS a feature. resolve_item_id_typed short-circuits the full-ID branch on the prefix string check (_common.py ~line 280) before the DB lookup, reusing the old wording. Acceptance requires wrong-type errors 'consistently everywhere, naming the actual item and type'. Fix: in the full-ID branch, when prefix mismatches, do the DB lookup and emit the same 'X is <id> (<type>), not a <type>' wording as the bare-number branch.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Unknown-item error wording drifts across the four resolver branches

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Unknown-item error wording drifts across the four resolver branches; acceptance demands 'both accepted forms, consistently everywhere'. Variants observed: (a) typed bare: 'no item with number 999 (use TASK-000999 or bare 999)'; (b) any bare: 'no item with number 999 (use a bare number like 999 or a full ID like TYPE-000999)'; (c) any full-ID: 'no item with number 999 (tried FEAT-000999 or bare 999)' — this one names neither form as a 'form' and omits the full-ID guidance; (d) typed full-ID uses the command prefix while any uses literal 'TYPE-'. Pick one canonical phrasing for 'mentions both forms' and use it in all four branches of resolve_item_id_typed/_any in _common.py.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Dead code: old resolve_item_id; lexical munging now written 3x

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Old resolve_item_id (_common.py:231) is now dead production code — no production caller remains after _items.py switched its verb callback to resolve_item_id_typed (only its own test_resolve_item_id references it). The two new resolvers re-implement the same lexical prefix/rpartition munging internally, so the lexical phase is now written three times. Either delete resolve_item_id (and fold its lexical assertions into the typed test) or have the new resolvers delegate to it for the lexical phase. Quality/maintainability, not correctness.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Grammar: 'not a operator'/'not a epic' a/an agreement in mismatch msgs

<!-- sq:finding:F4:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Minor grammar in type-mismatch messages: 'not a operator' / 'not a epic' (a/an agreement) — produced for OPERATOR and EPIC types. The recorded example is 'not a task' so it reads fine for most types but not vowel-initial ones. Low cosmetic; can be folded with the F1/F2 wording cleanup.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T14:23:05Z] Paul Reviewer:
  - Verdict: ChangesRequested. Core implementation is sound — one shared resolver pair (resolve_item_id_typed / resolve_item_id_any) in _cli/_common.py, threaded svc cleanly (mirrors resolve_slug_or_raise), every inventory surface wired, all gates green (259 passed/1 skipped, pyright 0, ruff clean), and live spot-checks pass: bare numbers work on tree/--parent/ref add/--ref/role/skill/operator/--story, type mismatch closes the silent-obey hole, --ref '2:blocks' resolves+keeps kind. Invariants respected: SquadsError throughout, split_ref/make_ref used (no hand-parsing), backends untouched, no datetime.now().
  - Two must-fix mediums — both are FEAT-19 acceptance-criterion gaps on wording CONSISTENCY (the feature's stated acceptance: wrong-type errors 'consistently everywhere, naming the actual item and type'; unknown-item errors mention both forms 'consistently'):
  - F1 (medium): typed surface gives two different wrong-type messages for the SAME item by input form — 'sq task 2 show' → '2 is FEAT-000002 (feature), not a task' but 'sq task FEAT-000002 show' → 'FEAT-000002 is not a task (expected TASK-…)', which never names that it's a feature. Make the full-ID branch do the DB lookup and emit the same '<tok> is <id> (<type>), not a <type>' wording.
  - F2 (medium): four divergent unknown-item phrasings across the resolver branches (one — any/full-ID — doesn't clearly name both forms). Pick one canonical 'mentions both forms' phrasing and use it in all four branches.
  - Two lows (fold into the wording cleanup): F3 — old resolve_item_id is now dead production code with triplicated lexical munging (delete or delegate); F4 — 'not a operator'/'not a epic' a/an grammar.
  - Tasks stay InReview. @python-dev please address F1+F2 (lows welcome alongside), update resolve_item_id_typed/_any in _common.py, then mark findings Fixed and @reviewer for re-review. Tests already cover the surfaces well — add/adjust assertions for the unified wording.
- [2026-06-11T14:29:10Z] Elias Python:
  - Fixed all four findings in `src/squads/_cli/_common.py`.
  - **F1** — typed resolver's full-ID branch now does a DB lookup on prefix mismatch and emits the same template as the bare-number branch: `FEAT-000002 is FEAT-000002 (feature), not a task`. Both forms are now identical in shape.
  - **F2** — unified unknown-item wording across all four branches via a shared template. Typed resolver: `no item with number {seq} (use {prefix}-{seq:06d} or bare {seq})`. Type-less resolver: `no item with number {seq} (use a full ID like TYPE-{seq:06d} or bare {seq})`. Both forms name both accepted forms explicitly.
  - **F3** — deleted `resolve_item_id` (dead production code). Extracted `_parse_item_token(token) -> (seq, prefix_or_None)` as the single lexical helper; both resolvers delegate to it — munging is written once. Also added `_mismatch_msg` to de-duplicate the type-mismatch string. Tests now cover the lexical assertions (bare number, zero-padded, full ID, case-insensitive prefix) inside `test_resolve_item_id_typed`.
  - **F4** — added `_article(word) -> 'a'|'an'` (vowel-initial check); all mismatch messages go through `_mismatch_msg` which calls it. `not an epic`, `not an operator` now correct.
  - Gates: 258 passed (1 skipped), 0 pyright errors, ruff clean. TASK-46/047 stay InReview. @reviewer — ready for re-review.
- [2026-06-11T14:32:32Z] Paul Reviewer:
  - Re-review: APPROVED. All four findings verified fixed in src/squads/_cli/_common.py; gates green repo-wide (258 passed/1 skipped, pyright 0, ruff check + format clean).
  - F1 (Verified): typed full-ID mismatch now does the DB lookup and emits the same '<tok> is <id> (<type>), not a/an <type>' template as the bare-number branch — confirmed live: 'sq task 2 show' and 'sq task FEAT-000002 show' both → '… is FEAT-000002 (feature), not a task'. The self-referential 'FEAT-000002 is FEAT-000002 (feature)' is accepted by design: the leading token echoes exactly what the user typed (the uniform template always prefixes with the input token), and naming a feature 'is a feature' in the full-ID branch would re-introduce the very form-dependent divergence F1 was filed against. Uniformity > the cosmetic echo.
  - F2 (Verified): one canonical 'mentions both forms' phrasing per resolver family, consistent across bare/full. Typed: 'no item with number N (use TASK-0000NN or bare N)'; type-less: 'no item with number N (use a full ID like TYPE-0000NN or bare N)'. The prefix difference is correct — the type-less surface has no concrete prefix to offer.
  - F3 (Verified): old resolve_item_id deleted; lexical munging lives once in _parse_item_token, both resolvers delegate; _mismatch_msg de-duplicates the mismatch string. (Nit, not blocking: the resolve_slug_or_raise docstring at _common.py:~328 still says 'Mirrors :func:`resolve_item_id`' — a dangling ref to the deleted symbol; sweep when convenient.)
  - F4 (Verified): _article() drives a/an agreement — confirmed 'not an epic' and 'not an operator' live.
  - TASK-46 + TASK-47 → Done. Nothing blocking for QA; the resolver-adoption sweep (TASK-47) added broad CLI smoke coverage across every ID-accepting surface (tree/--parent/ref add+rm/--ref/role/skill/operator/--story). @qa — if you do a pass, exercise the type-mismatch error path on a vowel-initial type (epic/operator) and the both-forms unknown-item wording, since those are the consistency contracts the feature is graded on.
<!-- sq:discussion:end -->
