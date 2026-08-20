---
id: REV-724
sequence_id: 724
type: review
title: 'Merge engine wired into the workflow loader: floor, stamp, consumer audit'
status: Approved
author: reviewer
refs:
- TASK-718
- FEAT-713
- ADR-696
description: 'Batch review of TASK-718 / FEAT-713 at commit 3b59e52: the 12 rewritten
  tests, the new floor and stamp mechanisms, and an independent consumer sweep'
subentities:
- local_id: F1
  title: sq create on a dropped type raises a raw KeyError traceback
  status: Fixed
  severity: high
- local_id: F2
  title: Shrinking a badge collection bricks a live squad; lint reports it clean
  status: Fixed
  severity: high
- local_id: F3
  title: 'Corpus alignment compares folders unnormalised: ''guides/'' is a false refusal'
  status: Fixed
  severity: high
- local_id: F4
  title: sq check falsely reports 'workflow config invalid' for a missing stamp
  status: Fixed
  severity: medium
- local_id: F5
  title: Role pointers keep preloading a dropped or renamed type's sq- skill
  status: Fixed
  severity: medium
- local_id: F6
  title: CLAUDE.md managed region hardcodes 'feature'; audit recorded it clean
  status: Fixed
  severity: medium
- local_id: F7
  title: 'Lint half of the stamp obligation has no test: neutering it stays green'
  status: Fixed
  severity: medium
- local_id: F8
  title: sq workflow lint reports only the first per-entry shape violation
  status: Open
  severity: low
- local_id: F9
  title: One creatable-type list, two derivations with different orderings
  status: Fixed
  severity: info
- local_id: F10
  title: Corpus-alignment folder half is only covered against a mock spec
  status: Fixed
  severity: info
- local_id: F11
  title: A key omitted from a [selected] keep list vanishes silently
  status: WontFix
  severity: info
- local_id: F12
  title: Build-process narration left in delivered source and test prose
  status: Fixed
  severity: info
- local_id: F13
  title: A bare 'assert errors' lint test can now pass on the wrong finding
  status: WontFix
  severity: info
- local_id: F14
  title: Badge cross-check asserts override causation it cannot establish
  status: Fixed
  severity: high
- local_id: F15
  title: Lint's badge-alignment fix hint names the wrong remedy and command
  status: Fixed
  severity: medium
- local_id: F16
  title: sq --help still advertises a dropped type; only sq create hides it
  status: Fixed
  severity: low
- local_id: F17
  title: Read path's dropped-type refusal gives advice that cannot work
  status: Fixed
  severity: low
- local_id: F18
  title: Dropped type's sq-<type> skill and SKILL item survive as orphans
  status: Fixed
  severity: low
- local_id: F19
  title: claude_section genericisation is inconsistent within edited lines
  status: Fixed
  severity: info
- local_id: F20
  title: Folder normalisation leaves case and the unconstrained folder open
  status: WontFix
  severity: info
- local_id: F21
  title: sq repair and sq adopt discard a re-foldered type's corpus
  status: Fixed
  severity: high
- local_id: F22
  title: A bad pre-placed override wedges sq init half-created
  status: Fixed
  severity: medium
- local_id: F23
  title: Orphan sweep withdraws any author-created skill slugged sq-*
  status: Fixed
  severity: medium
- local_id: F24
  title: Additive-only collection change reopens the false attribution
  status: Fixed
  severity: low
created_at: '2026-07-31T19:53:04Z'
updated_at: '2026-08-03T07:45:53Z'
---
<!-- sq:body -->
## Scope

Commit `3b59e52` — the workflow loader consuming the shared merge engine, its floor, the drift
stamp, and the consumer audit. Reviewed against the accepted decision on validating the minimum
semantics the engine needs (§3 floor, §4 shadowing + roster lock + stamp carrier, §4b `selected`
and the closed top-level key space, §5/§5a enforcement planes) and against the delivering task's
own acceptance bars. Independent of the build lineage; everything claimed below was driven, and
anything unreproduced is labelled a hypothesis.

## What holds

- **The merge lands where it was supposed to.** One parser family (`_build_spec`), run once over
  the merged raw mapping; the `*_str` override-only parsers are gone; `top_level_keys` is passed
  explicitly at both `merge_override` call sites. `_specmerge.py` is untouched by this change and
  still carries no floor check — its own docstring's disclaimer is accurate.
- **The roster type-key lock matches the ruling exactly.** Written on the key set plus `category`
  immobility, never on `prefix`. Driven: dropping any of the three via `[selected]` refuses;
  moving one out of `category = "roster"` refuses; declaring a fourth roster type refuses; a
  roster type's `prefix`/`folder`/`lifecycle`/`order` field-merge is accepted and floor-validated.
- **§5a bites.** Prefix and folder mismatches against a live corpus both refuse, grouped per type,
  listing the offending IDs, naming only revert-or-do-it-while-empty and no migration, and an
  empty corpus is unaffected. Falsified by neutering `_collect_corpus_alignment_errors`: three of
  the four new tests go red, the negative one correctly stays green.
- **The stamp obligation is reported, never a load refusal.** Driven through all three levels;
  the spec still loads with no stamp. Falsified at the `sq check` surface (two tests red when
  `workflow_stamp_finding` is neutered). Δ-mine is genuinely baselined on the bundled
  `workflow.toml` now, and the strengthened assertion is real: the previous `"incident" in
  delta_mine` was insufficient rather than vacuous, and `-prefix = "TASK"` pins the new behaviour.
- **Referential integrity names the referrer, with `[selected]` provenance.** Driven end to end:
  dropping `feature` while renaming reports `item 'task': parent type 'feature' not declared —
  'feature' was dropped from a [selected] list (selected.items), not left undeclared`.
- **No-override output is unchanged.** `_also_creatable_types(bundled_spec())` reproduces
  `epic|feature|bug|decision|review|guide` byte-for-byte; goldens and `tests/meta` pass; the
  template-manifest hash change is confined to the unreleased `0.12.3` key and the `0.12.2` entry
  is byte-identical to the one at tag `v0.12.2`.

## Verdict on the twelve rewritten tests

Judged against the decision, not against the implementation. Nine were genuinely obsolete or
genuinely buggy. One pair is obsolete *in its assertion* but has asserted away a hazard that
should have survived in a narrower form.

**The seven lint-collection tests — obsolete, correctly re-hosted.** Their `[items.gadget]
category = "roster"` is now refused by the roster key lock at phase 3, before the R1/R1′/R2 floor
at phase 4 ever runs, so the tests could no longer reach what they were testing. Shadowing
`role`/`skill`'s `lifecycle` field is the right substitute: the decision makes exactly that an
ordinary field-merge, so the floor is still being driven on a genuinely roster-category type, and
each assertion still pins its clause by name (`R1`, `R1'`, `found 2 live`, `no settled, non-live
status reachable from a live status`). Adding `_stamped()` to the two "is clean" cases is
necessary, not a mask — the finding it suppresses is a different family and is asserted elsewhere.

One rewrite in that file changed subject rather than host:
`test_lint_collects_every_conflict_in_one_pass_not_just_the_first` used to redefine two built-in
types, which is now legal, and now uses two new types naming undeclared lifecycles. That proves
collect-all across phase 4 bullets. Collect-all across two *roster-lock* (phase 3) violations is
now proven nowhere, which is a small hole rather than a defect.

**The two badge-collection tests — the assertion is obsolete; a narrower refusal should have
survived.** `may not redefine built-in` is correctly retired: declared-override replaces
additive-only and nothing in the surviving prohibition covers collections or sub-entity kinds. But
`test_shadowing_a_builtin_collection_wholesale_replaces_its_badges` asserts, in an item-less
squad, that `badges = []` loads clean — and that exact override bricks a squad that has items
carrying a removed code, with `sq workflow lint` reporting the spec OK. See F2. The surviving form
the deleted refusal was standing in for is a corpus cross-check on badge/field values, on the same
plane as the status-name check; §5a added prefix and folder and left this one out. The second
test (`subentity_kinds.finding`) is clean — it asserts field-level inheritance and nothing more.

**The three override-merge tests — genuine test-authoring bugs.**

- *Missing `[statuses.Retired]`* — a lifecycle may not name an undeclared status; the floor was
  right and the test was wrong.
- *`selected.items` omitting the key being renamed into* — `[selected]` is applied after the deep
  merge by the engine's fixed order, so a newly-declared key must be in the keep list. Correct per
  §4b, and the rewritten docstring now records the rule. The footgun it exposes is real and filed
  as F11.
- *"Wholesale lifecycle replace"* — tables recurse per key and only leaves replace, so a nested
  `transitions` table never swaps whole. The test's premise contradicted the merge granularity the
  decision settles. Supplying every state key is the correct way to express a wholesale routing
  replacement, and the docstring explains why a partial rewrite strands states.

**The two integration failures — same cause as the lint seven, same correct fix.** Both hosted the
fictional roster type; both now shadow `role`'s `lifecycle`. `test_open_service_...unmaterialisable_roster_type`
still asserts `no live status` and still goes through the real `open_service` path.

## Consumer sweep

Independently verified, not read off the audit.

Confirmed clean, no hardcoded type/prefix/folder/status literal: `_paths.py`,
`_index/_resolver.py`, `_services/_maintenance.py`, `_services/_validators.py` (the one `"TASK"`
in `_maintenance.py` is a comment example on a `partition` call). `workflow.md.j2` is spec-driven.
The `_workflow/__init__.py` bundled-only shims have no live caller that should be seeing the
merged spec. The AGENTS.md fix is correct and byte-identical with no override.

Three sites the audit's "most sites were already clean" does not cover:

1. **`_cli/_create.py` + the create path** — the whole `sq create` surface is registered from
   `bundled_spec()` at import time and the service's create path indexes `spec.items[...]`
   unguarded. `sq create <dropped-type>` is a raw `KeyError` traceback. F1, and the most serious
   item in this review.
2. **`skills_for_role()` / `item_types_for_role()`** — spec-blind over the bundled `PLAYBOOK`, so
   role pointers keep preloading a dropped or renamed type's skill and never learn the new one.
   F5. This is the third instance of the bug class the audit found once in the AGENTS.md template
   and the Claude Code backend had already fixed — so it is the pattern, confirmed.
3. **`claude_section.md.j2`** — recorded in the audit as fully spec-driven; it hardcodes `feature`
   in three places. F6.

`CREATE_LANES` is a fourth spec-blind map, but it is documented as a deliberate gap in place and
degrades correctly (a renamed type simply has no lane owner and creation is allowed), so it is not
filed.

## On the `# noqa: PLR0911`

Agreed. Seven early returns, one per blocking gate, is the clearest expression of a pipeline whose
whole contract is "each phase blocks the ones after it", and collapsing them behind an
accumulator would hide exactly the ordering the decision fixes. The precedent cited
(`_services/_import.py::_apply_one`) is the same shape. One nit: the noqa reason says "one return
per gate below" while the docstring enumerates five phases and the body has seven returns — the
count reads as a discrepancy to anyone checking.

## Recommended disposition

Changes requested. The mechanisms this task set out to build are correct and, where I could break
them, they bite. What is not met is the consumer-audit acceptance bar: the headline capability
(drop a built-in) still produces an unhandled traceback on the create path, and two spec-blind
generated-artefact sites survive. F1–F3 should land before this is accepted; F4–F7 are the same
release; F8–F13 are trackable follow-ups.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 724 add-finding "…" --severity medium`; track with `sq review 724 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | sq create on a dropped type raises a raw KeyError traceback |
| F2 | 🟠 high | Fixed |  | Shrinking a badge collection bricks a live squad; lint reports it clean |
| F3 | 🟠 high | Fixed |  | Corpus alignment compares folders unnormalised: 'guides/' is a false refusal |
| F4 | 🟡 medium | Fixed |  | sq check falsely reports 'workflow config invalid' for a missing stamp |
| F5 | 🟡 medium | Fixed |  | Role pointers keep preloading a dropped or renamed type's sq- skill |
| F6 | 🟡 medium | Fixed |  | CLAUDE.md managed region hardcodes 'feature'; audit recorded it clean |
| F7 | 🟡 medium | Fixed |  | Lint half of the stamp obligation has no test: neutering it stays green |
| F8 | 🟢 low | Open |  | sq workflow lint reports only the first per-entry shape violation |
| F9 | 🔵 info | Fixed |  | One creatable-type list, two derivations with different orderings |
| F10 | 🔵 info | Fixed |  | Corpus-alignment folder half is only covered against a mock spec |
| F11 | 🔵 info | WontFix |  | A key omitted from a [selected] keep list vanishes silently |
| F12 | 🔵 info | Fixed |  | Build-process narration left in delivered source and test prose |
| F13 | 🔵 info | WontFix |  | A bare 'assert errors' lint test can now pass on the wrong finding |
| F14 | 🟠 high | Fixed |  | Badge cross-check asserts override causation it cannot establish |
| F15 | 🟡 medium | Fixed |  | Lint's badge-alignment fix hint names the wrong remedy and command |
| F16 | 🟢 low | Fixed |  | sq --help still advertises a dropped type; only sq create hides it |
| F17 | 🟢 low | Fixed |  | Read path's dropped-type refusal gives advice that cannot work |
| F18 | 🟢 low | Fixed |  | Dropped type's sq-<type> skill and SKILL item survive as orphans |
| F19 | 🔵 info | Fixed |  | claude_section genericisation is inconsistent within edited lines |
| F20 | 🔵 info | WontFix |  | Folder normalisation leaves case and the unconstrained folder open |
| F21 | 🟠 high | Fixed |  | sq repair and sq adopt discard a re-foldered type's corpus |
| F22 | 🟡 medium | Fixed |  | A bad pre-placed override wedges sq init half-created |
| F23 | 🟡 medium | Fixed |  | Orphan sweep withdraws any author-created skill slugged sq-* |
| F24 | 🟢 low | Fixed |  | Additive-only collection change reopens the false attribution |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sq create on a dropped type raises a raw KeyError traceback

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
## What happens

With a built-in type dropped from the active spec via `[selected]`, `sq create <that-type>`
crashes with an unhandled `KeyError` and a full Python traceback. The dropped type is still
advertised in `sq create --help`.

Reproduced twice, on two different registration paths:

- `guide` dropped, `sq create guide "Ghost" --author manager` → `KeyError: 'guide'`,
  deepest frames `_cli/_create.py:353 in create_guide` → `_services/_base.py` create →
  `_workflow/_models.py:1095 item_subentity_kind`.
- `bug` dropped, `sq create bug "Ghost bug" --author manager` → `KeyError: 'bug'`,
  raised at `_workflow/_models.py:1093` in `item_is_roster`, called from
  `ServiceCore._check_author`.

`sq create --help` in the same squad still lists every one of the seven built-in
subcommands, including the dropped one.

## Why

`_cli/_create.py` builds its command surface from `bundled_spec()` at **import** time —
`_create_spec = bundled_spec()`, the `_CREATABLE` loop, the explicit
`@create_app.command("guide")`, `_STATIC_CREATE_TYPES` — so every historically-bundled type
is registered regardless of the active spec. The command body then calls
`svc.create("<type>", ...)` with no membership gate, and the create path indexes
`spec.items[item_type]` unguarded in at least two places (`item_is_roster`,
`item_subentity_kind`).

The read path is guarded and behaves correctly: `sq bug 1 show` in the same squad returns a
clean `unknown item type 'bug': no spec supplied, or the spec does not declare ...`. Only the
create path is unguarded.

## Why it matters

Dropping a built-in is the headline capability of this change, and the subtask acceptance bar
is explicit: "with `guide` dropped, every site above behaves as if the type never existed —
no orphaned pointer, no `KeyError`, no traceback". It is also the project's standing rule that
every user-facing failure subclasses `SquadsError` and never surfaces a traceback.

The audit's conclusion that the consumer sites were largely already clean does not hold for
the create surface, which was not on the audited list.

## Suggested shape

A membership gate at the service boundary (`create` raising the same
`unknown item type ...` `SquadsError` the read path already raises) fixes the whole class in
one place; hiding the subcommand for a type absent from the active spec is the cosmetic half.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-31T20:08:19Z] Elias Python:
  - Guarded item_type membership at the top of _create_model in _services/_base.py — raises the same clean 'unknown item type' SquadsError the read path already raises, before any unguarded self.items[item_type] lookup runs. Also hid dropped built-ins from sq create --help/the command list in _cli/_create.py (_CustomCreateGroup._dropped_static_names). Falsified: reverted both, watched raw KeyError + stale --help listing return; restored, watched clean refusal + hidden listing. New tests: tests/cli/test_create_refuses_a_dropped_built_in_type.py.
- [2026-07-31T20:52:09Z] Elias Python:
  - Reworked per feedback: kept the type's command registered (get_command no longer hides it) so it dispatches normally into svc.create — that's the one call site that owns the refusal. Only --help/the command list (list_commands) hides a dropped type; get_command deliberately does NOT consult _dropped_static_names any more, since hiding there let Click's own unknown-command handler answer first, whose did-you-mean saw the merely-help-hidden name and suggested the exact string typed ('did you mean guide?').
- [2026-07-31T20:52:09Z] Elias Python:
  - Added [selected]-provenance to the refusal itself (_create_model's membership gate, _services/_base.py): the merge engine has exactly one way to remove a bundled key (selected — deep-merge only adds/overwrites, never deletes), so a name that WAS bundled and is now absent from the active spec was, by construction, dropped via [selected] — the message now says so and points at selected.items, mirroring the loader's existing deselection-provenance annotation. A type that was never bundled and never declared gets the plain generic message, no false provenance claim (added a dedicated test for that branch).
- [2026-07-31T20:52:10Z] Elias Python:
  - Falsified both changes independently: (1) reintroduced the old get_command hiding, watched the 'no such command'/did-you-mean contradiction return and the corresponding tests go red; removed it, watched green. (2) neutered the bundled-type provenance branch, watched the [selected]-assertions go red while the negative (never-existed-type) test stayed green; restored, watched all green. Rewrote tests/cli/test_create_refuses_a_dropped_built_in_type.py to assert the actual right message (no 'no such command', names [selected]/selected.items, an alias test, and a distinct never-existed-type test asserting no false provenance) instead of pinning the old contradictory behaviour.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Shrinking a badge collection bricks a live squad; lint reports it clean

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
## What happens

An override that shrinks a bundled badge collection while live items still carry one of the
removed codes bricks the squad, and `sq workflow lint` reports the spec clean.

Reproduced. Squad with one `task` at `priority = urgent`, then:

```toml
[collections.priority]
badges = [{ code = "high", label = "High", emoji = "..." }, { code = "low", label = "Low", emoji = "..." }]
```

Every command — `sq list`, `sq task 2 show`, `sq check` — now fails with:

```
error: TASK-2 field 'priority' has unknown code 'urgent'; run `sq repair` if the index is
stale, or check the frontmatter
```

while `sq workflow lint` prints `workflow spec OK — no errors or warnings.` and exits 0.
`sq repair` runs and reports success ("rebuilt index: 2 items"); the squad stays bricked,
because nothing is stale — the frontmatter is right and the spec dropped the code.

The same happens with `badges = []`.

## Why

The cross-check plane compares live items' `type` and `status` names against the merged spec,
and this change adds `prefix`/`folder`. **Badge / field values are not on that plane at all**,
so the collision is discovered later, at item-read time, by the load-boundary vocab check —
which has no idea an override caused it and blames the index.

Two contracts break as a result:

- `sq workflow lint` is supposed to report everything `open_service` would hard-stop on
  ("lint keeps reaching `validate_against_index` in collect mode"). Here lint says OK and
  every command stops.
- A refusal may never assert a remedy no command performs. `run sq repair` is exactly that.

## Relationship to the two rewritten badge-collection tests

The refusal those two tests asserted (`may not redefine built-in ...`) is genuinely retired —
declared-override replaces additive-only, and shadowing a collection is legitimate. But
`test_shadowing_a_builtin_collection_wholesale_replaces_its_badges` asserts, in a squad with
no items, that `badges = []` loads clean — and that is the exact shape that bricks a squad
with items. The narrower form the deleted refusal should have survived as is a corpus
cross-check on badge/field values, alongside the status-name check it already sits next to.
That clause is missing.

## Scope note

Reported here as the gap the subtask brief asked for ("a clause you find missing is a gap to
report on this task"), not as in-scope work. Nothing in the decision's §5/§5a text covers
field values, so closing it needs a ruling first.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-31T20:16:03Z] Elias Python:
  - Extended the live-index cross-check (validate_against_index in _workflow/_loader.py) to badge/field values, on the same plane as prefix/folder: new _collect_badge_alignment_errors + _badge_field_mismatches walk every live item's/sub-entity's declared fields against the merged spec's collections. sq workflow lint now reports a shrunk collection as an error (was 'workflow spec OK'); open_service/every command now fails closed with an accurate message before the load-boundary vocab check ever fires.
- [2026-07-31T20:16:04Z] Elias Python:
  - Also fixed the misleading remedy: _index/_store.py::_check_field_codes no longer tells the adopter to 'run sq repair' as if it applies generally — the message now scopes repair to genuine index staleness and names the real remedies (fix the frontmatter value, or restore the code to the collection). Falsified: neutered the new collections-based check (returns [] unconditionally), watched lint go back to 'workflow spec OK' and the new test go red; restored, watched both the lint error and every command's accurate refusal return. New tests in tests/integration/test_workflow_override_service_integration.py.
- [2026-07-31T20:52:21Z] Elias Python:
  - Follow-up on the message wording, prompted by a full-suite regression: split the reasoning explicitly rather than leaving it implicit. _check_field_codes (_index/_store.py, the load-boundary backstop that runs on EVERY load, override or not) structurally cannot tell 'valid until an override shrank the collection' apart from 'never valid at all' — it has no visibility into whether an override is even present. So its message stays deliberately override-agnostic: names the fact (code not declared) plus the one remedy that's true either way (fix the frontmatter value), with sq repair scoped to genuine staleness only. The three-remedy, override-aware message (add the code back / revert the override / update the items) stays where it already was — the loader's live-index cross-check (_collect_badge_alignment_errors), which only ever runs when an override is present and so can say so accurately.
- [2026-07-31T20:52:22Z] Elias Python:
  - Updated the 3 tests in tests/integration/test_load_boundary_vocab.py that matched the old 'has unknown code' wording (a genuinely-never-valid-code scenario, no override involved) to assert the new override-agnostic message, plus an explicit 'override' not in message assertion pinning that it never presupposes a cause it can't see. Falsified: neutered the check, watched exactly those 3 go red (9 others in the file unaffected); restored, watched green. Grepped the repo for any other test matching the old wording — none.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Corpus alignment compares folders unnormalised: 'guides/' is a false refusal

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
## What happens

The corpus-alignment check compares the declared `folder` string against a folder derived from
each item's stored `path` with **no path normalisation on either side**, so two spellings of
the same directory read as a misalignment. A trailing slash is enough to lock the whole CLI.

Reproduced, on a type that had no items when the override was written:

```toml
[items.guide]
folder = "guides/"
```

1. `sq create guide "G" --author manager` **succeeds** and writes
   `squads/guides/GUIDE-000003-g.md` — the correct directory; the writer normalises.
2. Every subsequent command hard-fails:

```
error: workflow spec is incompatible with the live index — run `sq workflow lint` to see
details:
  - type 'guide' folder changed to 'guides/' in the workflow spec, but 1 live item(s) are
    still filed under the old folder: ['GUIDE-3'] — revert the folder in the override, or
    change it only while 'guide' has no items (no command realigns an existing corpus)
```

Nothing is misaligned. The item is in `guides/`, the spec says `guides/`, and the two are the
same directory. The same fires immediately for `folder = "tasks/"` on a type that already has
items.

## Why

`_expected_folder` is `PurePosixPath(item.path).parent.as_posix()` — normalised — and it is
compared with `ts.folder` verbatim. `ItemSpec.folder` is a bare `str` with no normalisation
and no non-empty constraint, and the item-path writer evidently tolerates the trailing slash.

## Why it matters

The refusal asserts a fact that is false, and it advises a remedy the adopter has already
satisfied ("change it only while the type has no items" — they did). The escape hatch is real
(`sq workflow lint` still runs, and hand-editing the override recovers), so this is a false
hard stop rather than data loss — but it is reachable by an ordinary typo in a document the
decision explicitly invites adopters to hand-write.

## Suggested shape

Normalise both sides through the same helper before comparing (`PurePosixPath(...).as_posix()`
on the declared folder too), or constrain `ItemSpec.folder` at the model layer so only one
spelling can ever be declared.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-31T20:08:20Z] Elias Python:
  - Normalised both sides of the folder comparison in _collect_corpus_alignment_errors (_workflow/_loader.py) via PurePosixPath(...).as_posix() — collapses trailing slash, leading ./, and doubled separators. Deliberately left case unnormalised (filesystem-dependent, not path-syntax). Falsified: reverted the normalisation, watched the trailing-slash repro hard-refuse; restored, watched it load clean while a genuine folder change still refuses. New tests in tests/integration/test_workflow_override_service_integration.py.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — sq check falsely reports 'workflow config invalid' for a missing stamp

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
## What happens

Any error-level lint finding makes `sq check` emit `workflow config invalid — run
`sq workflow lint``. The stamp obligation is now an error-level lint finding, so a shadowing
override with a missing provenance comment makes `sq check` declare the workflow config
invalid — when it is valid and loads fine.

Reproduced. Fresh squad, `.overrides/workflow.toml` containing only:

```toml
[items.guide]
folder = "handbooks"
```

- `sq list -a` → exit 0, spec loads, merge is correct.
- `sq workflow lint` → 1 error, the accurate stamp finding.
- `sq check` → **two** errors and exit 3:
  - `.overrides/workflow.toml: shadowing workflow override has no squads:override-base stamp ...` (accurate)
  - `workflow: workflow config invalid — run `sq workflow lint`` (false)

Adding the stamp clears both.

## Why

`_cli/_main.py::check` step 1 does `if any(f[0] == "error" for f in lint_findings)` and
synthesises the "workflow config invalid" issue. Before this change the loader had no stamp
handling at all, so no stamp-shaped error finding could reach that gate — the absence was a
`warn` from `_check_workflow_override_issues`. Adding the error-level stamp phase to
`lint_workflow_spec` routed provenance through a gate whose message is about spec validity.

## Why it matters

The decision is explicit that absent provenance is not a semantic hazard and that the merged
spec's verdict is unchanged by it. An error-level `sq check` finding is intended; a second
issue asserting the config is *invalid* is not, and it is the one an adopter will act on
first — sending them to look for a spec problem that does not exist. It also double-reports one
fact.

## Suggested shape

Have the `check` gate look at the finding families that actually mean "the spec would not
load" (engine violations, floor violations, structural errors, index cross-check) rather than
at any `error` level, or tag findings with a category the gate can filter on.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-31T20:20:23Z] Elias Python:
  - sq check's workflow-invalid gate (_cli/_main.py::check) now bases 'workflow config invalid' purely on whether open_service (get_service) actually raises — the ground truth for 'does the config load' — instead of scanning sq workflow lint's findings for any error level. The stamp obligation is error-level in lint by design (ADR-696) but never a load refusal, so it no longer double-reports as a false 'invalid' on top of its own accurate error-level finding. Falsified: reverted, watched the double-error return on a stamp-only override; restored, watched a single accurate error while a genuinely broken spec still reports invalid. New test in tests/integration/test_workflow_override_service_integration.py.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Role pointers keep preloading a dropped or renamed type's sq- skill

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
## What happens

`skills_for_role()` never sees the active spec, so after a type is dropped or renamed every
role pointer keeps preloading the dead type's `sq-<type>` skill, and nothing preloads the new
one. `sq sync` does not converge it and `sq check` is clean.

Reproduced twice.

**Drop.** Squad with both backends, `guide` dropped via `[selected]`, then `sq sync`:
`.claude/skills/sq-guide/SKILL.md` and `squads/agents/skills/SKILL-000014-sq-guide.md` both
survive, and `.claude/agents/tech-writer.md`, `architect.md`, `tech-lead.md` still list
`sq-guide` under `skills:`. `sq check` → `no issues`.

**Rename.** `feature` renamed to `story` (`[selected]` + splat-refs), then `sq sync`:
`.claude/skills/` gains `sq-story` and keeps `sq-feature`. **No** role pointer lists
`sq-story`; `product-owner.md`, `qa.md`, `tech-lead.md` all still list `sq-feature`.
`sq check` → `no issues`.

## Why

`skills_for_role(slug)` takes no `spec` argument. It calls `item_types_for_role(slug)`, which
iterates the module-level `PLAYBOOK` — a bundled-only map keyed by built-in type names. So the
pointer files' `skills:` list is derived entirely from the bundled vocabulary.

The Claude Code backend's fix in this change (`if item_type not in spec.items: continue`)
correctly stops *writing* the dead skill's content, but the role→skill wiring that points at it
is a separate, still-spec-blind site. `is_system_skill('sq-feature', spec)` also stays `True`
via `bundled_skill_slugs()`, so the stale skill is never reclassified as author-defined either.

The `active_skill_slugs()` helper added here is a real narrowing, but it cannot bite in this
scenario: `candidate_orphans` unions it with every live SKILL item's slug, and the stale
`sq-guide`/`sq-feature` SKILL items are still live.

## Why it matters

This is the third instance of the bug class the audit found once (the AGENTS.md hardcoded type
list) and the Claude Code backend had fixed earlier — a bundled type vocabulary baked into a
generated agent-facing artefact. It is the largest of the three, because it is the rename case:
agents are told to load a skill for a type that no longer exists, and never told about the type
that replaced it. The subtask bar is "with a type renamed ... nothing points at the old one".

## Suggested shape

Thread the active spec into `skills_for_role`/`item_types_for_role` and intersect with
`spec.items`, so a dropped type contributes nothing and a renamed one falls through to the
thin-custom-skill path the loop already has.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-07-31T20:31:21Z] Elias Python:
  - Threaded spec into item_types_for_role(slug, spec=None)/skills_for_role(slug, spec=None) — intersects PLAYBOOK's bundled-only keys with spec.items, so a dropped type contributes nothing and a renamed type (no PLAYBOOK entry under its new name) degrades the same way any custom type already does: no preload, but its thin auto-generated skill still exists and is still loadable by hand.
- [2026-07-31T20:31:22Z] Elias Python:
  - Updated all 5 production call sites to pass the active spec: _services/_base.py::_resolve_role_skills (the one that feeds sq sync's role_skills map — the actual render path for pointer skills: lists), _services/_roster.py's two role/dev-creation sites, _backends/_base.py::resolved_skills_for's fallback, and _services/_config_integrity.py's _always_on_floor + two item_types_for_role call sites (also fixed the now-stale 'none today, playbook resolves the bundled spec' remedy text on the type_implied finding, which is real now).
- [2026-07-31T20:31:23Z] Elias Python:
  - Falsified both scenarios end-to-end on real synced squads: drop (guide dropped via [selected] -> stale sq-guide gone from tech-writer/architect/tech-lead pointers) and rename (feature->story via [selected]+splat -> stale sq-feature gone from product-owner/qa/tech-lead, sq-story generated but correctly not auto-preloaded, matching the custom-type degradation). Reverted the fix, watched both regressions reappear on a fresh sq sync; restored, watched them disappear. New/updated tests: tests/unit/test_skills_for_role_mapping.py (2 new), tests/unit/test_roster_config_integrity_predicates.py, tests/service/test_retirement_refuses_a_config_breaking_transition.py (remedy-text updates, not behavior changes).
- [2026-07-31T20:31:24Z] Elias Python:
  - On the fourth-site question: agree with the reviewer's assessment. CREATE_LANES is documented in place (_interactions/__init__.py) as a deliberate, undeclared gap with no override mechanism for custom roles/types, and it degrades correctly — a renamed type simply has no lane owner and sq create proceeds with no advisory warning, never a crash or a stale reference to a dropped type. That is a real difference from F5/the AGENTS.md/Claude-Code-backend instances, which all pointed at a type that no longer exists; CREATE_LANES never points at anything invalid, it just stops being informative. Leaving it as-is.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — CLAUDE.md managed region hardcodes 'feature'; audit recorded it clean

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
## What happens

`CLAUDE.md`'s managed region hardcodes the type name `feature`, so after a rename the generated
region still instructs agents to use the type that no longer exists.

Reproduced. `feature` renamed to `story`, `sq sync` run; the rendered `CLAUDE.md` managed
region still contains:

- `sq tree FEAT-… --json` for a **feature's** whole subtree
- until the **feature's** tasks are `Done` and its reviews `Approved`
- Sub-entities nest: `sq feature 12 story 1 update --status InProgress`

Source: `src/squads/_rendering/templates/claude/claude_section.md.j2` lines 74, 84, 101 — plain
literals, no spec lookup. The sibling `agents_md/agents_section.md.j2` and
`agents/squads_skill.md.j2` carry the same `sq feature 12 story 1` / `FEAT-<n>` /
`a feature's whole subtree` literals.

## Why it matters

The subtask recorded `claude_section.md.j2` as verified clean and "fully spec-driven". Parts of
it are — the Team-workflow bullets did re-render as "its parent is the story it implements" —
but the orchestration-loop prose and the sub-entity example are not, so the audit's recorded
verdict for this file is wrong and the next reader will trust it.

Worth separating two kinds of literal when this is fixed:

- **Enumerations of the type vocabulary** must be spec-derived. That is the class the AGENTS.md
  `# also:` fix belonged to, and it is now correct.
- **Single-type illustrative examples** (`sq task 3 show`, `sq tree FEAT-<n>`) are a judgement
  call, but they are wrong-by-construction for any adopter who drops or renames the type they
  name, and there are enough of them to be worth one deliberate ruling rather than case-by-case.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-07-31T20:34:57Z] Elias Python:
  - Fixed in the template (never the rendered file): replaced the three type-specific illustrative examples in claude_section.md.j2 with generic placeholders, matching the convention already used elsewhere in the same file (sq <type> <n> ...) — 'sq tree FEAT-... for a feature's whole subtree' -> 'sq tree <parent-id> --json for a parent's whole subtree'; 'feature's tasks are Done' -> 'parent's tasks are Done'; 'sq feature 12 story 1 update' -> 'sq <type> <n> <kind> <k> update'. Regenerated the golden (tests/goldens/claude_md_section.txt), this repo's own CLAUDE.md via sq sync (only those 3 lines changed), and the template manifest's 0.12.3 entry via scripts/gen_template_manifest.py (--check now passes; earlier release entries untouched).
- [2026-07-31T20:34:58Z] Elias Python:
  - Falsified: reverted the template edit, watched test_the_claude_md_managed_section_body_matches_its_pinned_golden go red on the exact 3 lines; restored, watched green. Flagging proactively: the same class of literal (sq feature 12 story 1, FEAT-<n>, a feature's whole subtree) also exists in agents_section.md.j2 and squads_skill.md.j2 per the finding's own note — out of F6's stated scope (claude_section.md.j2 only), left untouched here; worth a follow-up finding/task if the team wants the same ruling applied there.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Lint half of the stamp obligation has no test: neutering it stays green

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
## What happens

The stamp obligation is required on two surfaces — `sq check` **and** `sq workflow lint` — and
the decision requires the two to agree. Only the `sq check` half is covered by a test.

Falsified: patching `workflow_stamp_finding` to always return `None` (session-start monkeypatch,
no edit to `src/`) turns **two** tests red —
`TestWorkflowOverride::test_check_reports_an_error_for_a_shadowing_override_with_no_stamp` and
the pre-existing `test_check_warns_on_a_stale_stamp` — and **zero** tests in
`tests/unit/test_workflow_lint_merge_errors.py` (12 passed with the mechanism neutered).

The only lint-side use of the stamp in the suite is the new `_stamped()` helper, which exists to
*suppress* the finding so two "is clean" assertions still hold. Nothing asserts lint emits it.

The mechanism itself does work — driven by hand, `sq workflow lint` on an unstamped shadowing
override reports one error-level finding at `.overrides/workflow.toml` with the
`sq override update workflow` fix hint. It is the regression guard that is missing, on the half
of the obligation whose whole point is that the two surfaces cannot diverge.

## Suggested shape

One lint-level test per stamp level (shadowing+unstamped → error, older stamp → warn, add-only
unstamped → nothing), or one test asserting `lint_workflow_spec` and `check_override_issues`
return the same level for the same file.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-07-31T20:36:40Z] Elias Python:
  - Added the missing lint-level coverage in tests/unit/test_workflow_lint_merge_errors.py: one test per stamp level driven through lint_workflow_spec directly (shadowing+unstamped -> error, stale stamp -> warn, add-only+unstamped -> nothing), plus a cross-surface test asserting lint_workflow_spec and check_override_issues report the same level for the same file.
- [2026-07-31T20:36:41Z] Elias Python:
  - Falsified with the reviewer's own method: session monkeypatch-equivalent (a temporary early-return neutering workflow_stamp_finding, no lasting src/ edit), watched all 3 new tests go red while the other 13 in the file stayed green; removed the neuter, watched all 16 green again.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — sq workflow lint reports only the first per-entry shape violation

<!-- sq:finding:F8:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
Filed for tracking at the reviewing party's request — assessed and deliberately left out of the
implementing task's scope. Pre-existing, newly reachable now that an override can shadow.

## What happens

`sq workflow lint` reports only the **first** per-entry shape violation when two entries are
malformed, because `_build_spec`'s per-entry parsers raise on the first bad entry and the whole
phase is wrapped in one `try`.

Reproduced:

```toml
[items.alpha]
prefix = "AL"
folder = "alphas"
lifecycle = "work"
bogus = 1

[items.beta]
prefix = "BE"
folder = "betas"
lifecycle = "work"
alsobogus = 2
```

`sq workflow lint` reports one error, for `alpha` only. `beta` is never mentioned.

Two smaller things ride on the same message and are worth fixing together:

- The raw pydantic text leaks into the finding —
  `1 validation error for ItemSpec / bogus / Extra inputs are not permitted
  [type=extra_forbidden, input_value=1, input_type=int] / For further information visit
  https://errors.pydantic.dev/...`. Every other lint finding is a written sentence.
- The attached fix hint is the referential-integrity one ("Fix the referenced key in
  `.overrides/workflow.toml`, or add it back (directly or via `selected`)"), which is the wrong
  advice for a shape error — there is no referenced key and nothing to add back.

## Why it matters

Collect-all is the whole promise of `sq workflow lint`, and a shadowing override is exactly the
document most likely to carry more than one shape mistake at a time. The decision already
records the gap in the abstract (a `ValidationError` is not a collected violation) and says the
right fix is translating one into per-field findings rather than privileging one cause.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-03T07:45:40Z] Catherine Manager:
  - Left Open deliberately with its disposition named: per-entry translation of a validation error into per-field lint findings is a real gap and is the loader-side work the architect parked. It is not scheduled for this release; carrying it into 0.14 rather than closing it as done or pretending it has a home here.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — One creatable-type list, two derivations with different orderings

<!-- sq:finding:F9:head -->
**Status:** 🟡 Fixed
**Severity:** 🔵 Info
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
Documentation / consistency, ranked below the defects.

The `# also: ...` creatable-type list is now derived in two places with two different orderings:

- `_backends/_agents_md/_backend.py::_also_creatable_types` sorts by declared
  `(ItemSpec.order, name)` → `epic|feature|bug|decision|review|guide`
- `_rendering/templates/agents/squads_skill.md.j2` uses
  `spec.non_roster_types() | reject('eq','task') | sort | join('|')` → lexical,
  `bug|decision|epic|feature|guide|review`

Observed side by side in one squad: `AGENTS.md` line 347 vs
`squads/agents/skills/SKILL-000018-squads.md` line 228.

Both are correctly spec-derived after this change, so this is not a correctness defect — but it
is one list with two implementations and two orderings, and the newly-added one is the odd one
out. Either shape is defensible; having both means a future change to "the creatable type list"
has to be made twice and will drift.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-08-03T07:44:58Z] Catherine Manager:
  - Closed as collateral of the spec-blindness sweep: allowed_create_types now takes a spec and filters against it, so the two derivations agree.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Corpus-alignment folder half is only covered against a mock spec

<!-- sq:finding:F10:head -->
**Status:** 🟡 Fixed
**Severity:** 🔵 Info
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
Coverage note, ranked below the defects. The mechanism works — verified by hand.

Three of the four new corpus-alignment tests drive `validate_against_index` with a hand-built
fake:

```python
mock_spec = type("_MockSpec", (), {"items": {...}, "statuses": bundled.statuses})()
```

so they prove the comparison, not that a real parsed override ever produces such a spec. Only
the fourth (`test_open_service_fails_closed_end_to_end_on_a_re_prefix_against_a_live_corpus`)
goes through a real `.overrides/workflow.toml`, and it covers **prefix** only.

There is no end-to-end test for the **folder** half through the override path. Driven by hand it
works — a squad with one live task plus `[items.task] folder = "tickets"` refuses with the item
ID listed and no migration named — but the half that is only covered against a mock is also the
half that turned out to have the normalisation defect filed separately in this review, which is
exactly what an override-path test would have surfaced.

The task's own testing brief asked for override syntax to be driven off real parsed TOML
"wherever the override's *syntax* is part of what is being proven". A field-merge on a bundled
type is that.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-08-03T07:45:02Z] Catherine Manager:
  - Closed: the folder half now has real integration coverage through a parsed override (trailing-slash non-mismatch and the live-corpus re-folder refusal), which is the coverage this asked for.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — A key omitted from a [selected] keep list vanishes silently

<!-- sq:finding:F11:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🔵 Info
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
Spec/usability note, ranked below the defects. Conformant with the decision as written.

`[selected]` is applied **after** the deep merge (the engine's fixed order), so a key the
override newly declares must also be named in the keep list or it is deselected along with
everything not listed — silently, with no violation and no warning.

This is the shape of a rename: drop the old key via `[selected]`, add the new one via splat-refs.
Forget to list the new key and the rename evaporates with a clean load. It is the failure the
implementer hit and correctly classified as a test-authoring bug, and the rewritten test's
docstring now documents the rule — which is the right outcome for the test.

Worth recording as a gap rather than a defect: §4b's reasoning for `selected` needing no
validation of its own is that "every unsafe drop is already caught by a check that runs on the
resulting spec". Dropping a key the adopter just declared is not unsafe, so nothing catches it,
so the reasoning holds and the footgun is real at the same time. A note in the scaffolded
override body, or a lint-level info finding when a `[selected]` list omits a key the same
document declares, would close it without changing the ordering.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-08-03T07:45:38Z] Catherine Manager:
  - WontFix: omitting a key from a keep list drops it, which is the declared semantics of a surviving-set deselect rather than a defect. The adopter-facing grammar reference now states the ordering that makes it surprising (the deselect applies after the merge, so a newly added key must be named too).
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Build-process narration left in delivered source and test prose

<!-- sq:finding:F12:head -->
**Status:** 🟡 Fixed
**Severity:** 🔵 Info
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
Prose hygiene, ranked below the defects.

Delivered text must describe the thing, not narrate how it was built. Two survivors:

- `src/squads/_workflow/_loader.py:36` — "Also carries the one genuinely *new* enforcement
  **this task adds** — a corpus-alignment check ...". New in this change. "New" and "this task"
  are both relative to a build step that will not exist for the next reader; the sentence reads
  correctly as "Also carries the corpus-alignment check gating ...".
- `tests/unit/test_workflow_lint_merge_errors.py:3` — "out of **this chunk's** range". Pre-existing,
  but this commit rewrote the surrounding module docstring and kept it.

The ~30 ticket-ID and section-number citations that were removed from `src/` prose were checked
separately: `grep -E 'ADR-[0-9]+|EPIC-[0-9]+|§'` over `src/` and `tests/` returns no rule
citation, and the reasoning did survive the rewrite. The loader's docstrings now carry the *why*
in place — e.g. the roster lock states "never on `prefix`, which is ordinary field-mergeable
customisation under the same full floor every other type faces", and
`_collect_corpus_alignment_errors` carries the whole
resolve-folder-from-spec-and-glob-the-prefix mechanism as its rationale. No rule was left
stripped of its justification.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-07-31T20:37:23Z] Elias Python:
  - Both survivors fixed. _workflow/_loader.py:36's 'this task adds' phrasing was already rewritten incidentally while extending the module docstring for the badge-alignment check (F2) — confirmed clean, no remaining 'this task'/'new' framing. tests/unit/test_workflow_lint_merge_errors.py's module docstring had 'out of this chunk's range' — dropped, the sentence reads fine without it. Broader grep for 'this chunk'/'this task adds'/'this task removes'/'this task implements' across src/ and tests/ returns nothing else. Took the ~2-minute path as suggested; not a full hygiene sweep.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — A bare 'assert errors' lint test can now pass on the wrong finding

<!-- sq:finding:F13:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🔵 Info
<!-- sq:finding:F13:head:end -->

<!-- sq:finding:F13:body -->
Test-quality note, ranked below the defects.

`test_lint_surfaces_a_prefix_shadowing_a_builtin_as_an_error` ends in a bare `assert errors`.
It was already weak; it is weaker now, because this change adds two new families of error-level
lint finding (the stamp obligation, the roster type-key lock) that could satisfy it while the
duplicate-prefix check it names is broken.

It happens to be honest today — the override it writes declares a *new* key
(`[items.shadow-task]`), so no bundled key is shadowed, no stamp finding fires, and the single
error really is `duplicate prefix 'TASK': used by 'task' and 'shadow-task'` (driven and
confirmed). That is luck rather than construction.

Two neighbours in the same file share the shape: `test_lint_reports_a_finding_shaped_tuple_for_a_structural_error`
(`assert len(errors) >= 1`) is deliberately about tuple shape, so it is fine; the prefix one is
about a specific rule and should name it — `match` on `duplicate prefix` would pin it.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-08-03T07:45:33Z] Catherine Manager:
  - WontFix: a bare assert on the error list is weak, but the surrounding lint tests now pin named clauses individually, so the weak assertion no longer carries the coverage on its own. Not worth a round.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Badge cross-check asserts override causation it cannot establish

<!-- sq:finding:F14:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F14:head:end -->

<!-- sq:finding:F14:body -->
## What happens

The new badge cross-check treats "an override file exists" as proof that "the override caused
this mismatch", and states that cause as fact in the refusal. When the two come apart, every
command hard-stops on a message whose two leading remedies are wrong and whose real remedy is
absent — and one of the blocked commands is the one that would have fixed it.

Reproduced. A squad with a live `task` at `priority = urgent`, a `.overrides/workflow.toml`
that only **adds a custom type** (it never touches `[collections]`), and one index entry whose
stored `priority` is stale relative to its own frontmatter:

```toml
# squads:override-base:0.12.3
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
order = 55
```

`.squads.json` carries `priority: "bogus"` for TASK-9; `squads/tasks/TASK-000009-t-one.md`
carries the correct `priority: urgent`.

Every command, including `sq repair`:

```
error: workflow spec is incompatible with the live index — run `sq workflow lint` to see
details:
  - 'task' field 'priority' carries code 'bogus', which the workflow spec's 'priority'
    collection no longer declares, but 1 live item(s) still carry it: ['TASK-9'] — add
    'bogus' back to the collection, revert the override, or update the affected item(s)
    to a current code
```

`sq repair` exits 1 on that same message. The index is merely stale; the frontmatter is right.

Delete the override file and the same squad reports the accurate load-boundary message
instead — `... fix the frontmatter value to a currently valid code, or run \`sq repair\` if
the index itself is merely stale` — and `sq repair` runs and fixes it.

## Why

`_collect_badge_alignment_errors` (`_workflow/_loader.py`) only ever runs when an override
file is present, and the split reasons from that: presence of an override is taken as
evidence the override is the cause, so the message is written in the past tense of a change
("no longer declares") and offers "add X back to the collection" and "revert the override".
Presence of an override is not evidence that the override touched `[collections]`, still less
that it removed this code. Three of the message's claims are then false in this shape:

- `'bogus'` was never in the collection, so there is nothing to "add back" — and doing what
  the message says means writing a junk code into the workflow spec to satisfy corrupt data.
- The override is unrelated, so "revert the override" changes nothing.
- The one remedy that applies, `sq repair`, is not named — and is itself gated by this check.

The check also reads `.squads.json` directly (`_load_index_sync`), so it inherits index
staleness as a false positive, whereas the load-boundary check it was added to front-run reads
the same index but names repair as a remedy and is not self-blocking.

## Why it matters

This is the shape F2 was filed for, inverted: a refusal that blames the wrong cause and names
remedies no command performs, now emitted by the mechanism that closed F2. Before this change
a stale badge value in a squad with an override recovered with `sq repair`; it no longer does.
Index/frontmatter skew is exactly what `sq repair` exists for, and a team repo hitting it after
a merge is ordinary, not exotic.

## Test coverage

The two poles are pinned and the crossed case is not. `tests/integration/test_load_boundary_vocab.py`
covers "never-valid code, **no** override" and now asserts `"override" not in message`;
`test_open_service_fails_closed_end_to_end_when_a_shrunk_collection_bricks_a_live_corpus`
covers "shrunk collection, override present". Nothing covers "override present, code never
valid" — the only combination in which either message can be untrue.

## On the separation itself

The *placement* is right: `_check_field_codes` genuinely cannot see an override and its
override-agnostic message is true in every case it can be reached in (with an override
present the loader check fires first and strictly subsumes it, so it is unreachable in the
override-caused shape). The asymmetry is on the other side — the loader check can see whether
an override exists but not whether it changed anything relevant, and its message claims the
stronger fact.

## Suggested shape

Either establish the cause before asserting it — compare the merged collection against the
bundled one and only use the override-aware wording for codes the override actually removed —
or weaken the message to what the check knows (the code is not declared; here are the items;
here is the full remedy set including `sq repair` when the frontmatter still holds a valid
value). Whichever, `sq repair` must not be gated by a check whose most likely trigger is a
stale index.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-08-01T19:22:15Z] Elias Python:
  - Root fix: the badge cross-check (_collect_badge_alignment_errors in _workflow/_loader.py) now only attributes a stale badge code to the override when the active spec's collection genuinely differs from the bundled spec's same-named collection (_collections_differ_from_bundled, comparing badge_codes). If the collection is untouched, this plane reports nothing — the load-boundary check (_index/_store.py, its own override-agnostic message from the earlier round) is what handles a plain corpus/index data problem, which is what this actually is.
- [2026-08-01T19:22:18Z] Elias Python:
  - Separately, sq repair no longer depends on open_service's fail-closed gate succeeding: added common.get_service_bypassing_index_cross_check() (falls back from get_service -> load_workflow_spec with no cross-check -> bundled spec), used by the repair CLI command. This holds unconditionally, not just for the crossed case -- verified repair still runs (and heals the index) even when an override genuinely shrank the collection and the refusal is real for every other command.
- [2026-08-01T19:22:20Z] Elias Python:
  - Checked other maintenance commands: renumber still uses plain get_service() deliberately -- it's a deliberate, operator-run pre-merge action on a presumed-healthy squad, not a recovery path, so it's fine to require a loading spec. sq check already had its own (pre-existing) graceful-degradation fallback. repair is the one command whose entire job is reconciling a stale index, so it's the one that needed this.
- [2026-08-01T19:22:22Z] Elias Python:
  - Falsified all three pieces independently: (1) reverted the collection-scoping condition, watched the crossed-case test go red (message wrongly blames the override) while the repair-still-works test stayed green (repair heals the index regardless); (2) reverted repair's fallback to plain get_service(), watched the true-positive repair test go red while the crossed-case one stayed green (since the scoping fix alone already keeps open_service from refusing in that case). Restored both, all green. Added the crossed-case test the finding asked for (override present, never touches [collections], stale index) plus its true-positive contrast test, in tests/integration/test_workflow_override_service_integration.py.
- [2026-08-01T20:17:39Z] Paul Reviewer:
  - Verified closed. Re-drove the original repro (unrelated override + stale index): now yields the accurate override-agnostic load-boundary message and sq repair fixes it. True-positive contrast holds: a genuine collection shrink still refuses on every command with the override-aware message, while sq repair runs. One narrow residue filed as F24 — attribution is per-collection ("differs from bundled at all") rather than per-value, so an additive-only collection change still mis-attributes. Low, because repair is no longer gated.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Lint's badge-alignment fix hint names the wrong remedy and command

<!-- sq:finding:F15:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F15:head:end -->

<!-- sq:finding:F15:body -->
## What happens

`sq workflow lint`'s **fix hint** column for the new badge-alignment family is the
index-cross-check hint written for the type/status/prefix/folder families. It names none of
the badge remedies and points at a command that cannot change a badge code.

Reproduced. Squad with one `task` at `priority = urgent`, then an override shrinking the
`priority` collection to `high|low`. `sq workflow lint`:

| location | error | fix hint |
| --- | --- | --- |
| index cross-check | `'task' field 'priority' carries code 'urgent', …` | `Add the missing type/status back to .overrides/workflow.toml, revert the prefix/folder change, or update the affected items with` `sq <type> <n> status <new>`. |

Three problems in one cell: "the missing **type/status**" (neither is missing), "revert the
**prefix/folder** change" (no prefix or folder changed), and `sq <type> <n> status <new>` —
`status` sets an item's workflow status; the command that changes a priority is
`sq <type> <n> update --priority <code>` (or `--set <field>=<code>`).

The same wrong hint attaches to the sub-entity form (`'finding' field 'severity' …`), where
the remedy is `sq <type> <n> <kind> <k> update --severity <code>`.

## Why

`lint_workflow_spec`'s phase 5 (`_workflow/_loader.py`) builds one `fix` string and attaches
it to every string `validate_against_index` returns. The badge family was added to
`validate_against_index` without widening that hint.

## Why it matters

The error text itself carries correct remedies, so this is a presentation defect rather than a
wrong refusal — but it is the column an adopter reads *as* the instruction, and it names a
command that will not work. It is also the same defect this review already recorded against
the shape-error family (F8's second bullet: the wrong fix hint riding a shared channel), which
means the pattern is now two-for-two: a shared, hand-written hint string that is only correct
for the families that existed when it was written.

## Suggested shape

Derive the hint per finding rather than per phase — the cross-check already knows which family
produced each string — or, at minimum, widen it to name the badge remedy and drop the
`status` command from a hint that covers non-status families.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-08-01T19:22:33Z] Elias Python:
  - Extracted the type/status walk into its own _collect_type_status_errors (matching the corpus/badge collectors already split out), and lint_workflow_spec's phase 5 now calls all three collectors separately with a per-family fix hint: type/status keeps the 'add it back / update to a currently declared type-status' hint, corpus alignment gets its own revert-prefix-folder hint, and badge alignment gets 'add the code back to the collection, revert the override, or update the affected item(s) with sq <type> <n> update --<field> <code>' -- never the nonsensical status-transition advice. validate_against_index's own combined contract (used by the fail-closed raise and every pre-existing test) is unchanged.
- [2026-08-01T19:22:35Z] Elias Python:
  - Falsified: swapped the badge branch's fix hint back to the shared type/status one, watched the new fix-hint test go red; restored, watched green. New test in tests/integration/test_workflow_override_service_integration.py.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — sq --help still advertises a dropped type; only sq create hides it

<!-- sq:finding:F16:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F16:head:end -->

<!-- sq:finding:F16:body -->
## What happens

The advertising half of F1's fix was applied to `sq create` only. The root command list still
offers the dropped type as a resource group, and its help still renders in full.

Reproduced. `guide` dropped via `[selected]`:

- `sq create --help` → `guide` correctly absent (the fix).
- `sq --help` → still lists `│ guide     Operate on a guide by number. │`.
- `sq guide --help` → renders the whole group help (`Usage: sq guide [OPTIONS] N COMMAND …`).
- `sq guide 1 show` → refuses correctly.
- `sq workflow types` → correctly omits `guide`.
- `sq create guide "…"` → refuses correctly, with `[selected]` provenance.

So of the three surfaces that advertise a type, one was filtered and one was not, and the two
disagree in the same terminal session.

## Why

`_CustomCreateGroup.list_commands` (`_cli/_create.py`) now subtracts `_dropped_static_names()`.
The sibling `_CustomTypeGroup` in `_cli/__init__.py`, which registers `sq <type> <n> <verb>`
from `_STATIC_TYPES` at import time, has the equivalent `_custom_non_roster_types_for_ctx`
addition but no matching subtraction, so its `list_commands` still returns every bundled type.

## Why it matters

Cosmetic in consequence — every *use* of the dropped type refuses accurately — but F1's
acceptance bar was "behaves as if the type never existed", and the more prominent of the two
listings is the one that still advertises it. An adopter reading `sq --help` learns the type
exists; `sq create --help` says it does not.

`get_command` must keep dispatching on the resource-group side too, for the same
did-you-mean reason the create side documents.

## Suggested shape

Apply the same `list_commands` subtraction in `_CustomTypeGroup`, sharing one helper rather
than a second copy of the alias-expansion loop.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-08-01T19:22:47Z] Elias Python:
  - Mirrored _CustomCreateGroup's fix onto _CustomTypeGroup (_cli/__init__.py): added _dropped_static_names_for_ctx (same reasoning, resolves the spec via the class's existing _resolve_spec_for_ctx) and wired it into list_commands only -- get_command is deliberately untouched, same reasoning as F1 (hiding there would let Click's unknown-command handler answer with a self-referential did-you-mean). sq --help no longer lists a dropped type; sq guide --help (typed explicitly) still renders its own usage text -- harmless, no action taken, consistent with the create-path's same design choice for sq create guide --help. Flagging this equivalence explicitly in case you'd rather it be hidden too.
- [2026-08-01T19:22:49Z] Elias Python:
  - Falsified: reverted list_commands to the un-filtered super() call, watched the new --help test go red (guide reappears); restored, watched green. New tests in tests/cli/test_read_path_refuses_a_dropped_built_in_type.py.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Read path's dropped-type refusal gives advice that cannot work

<!-- sq:finding:F17:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F17:head:end -->

<!-- sq:finding:F17:body -->
## What happens

The same condition — a bundled type dropped via `[selected]` — now produces two different
refusals depending on which path reaches it, and the older of the two gives advice that does
not apply.

Reproduced, `guide` dropped:

```
$ sq create guide "Ghost" --author manager
error: unknown item type 'guide': 'guide' was dropped from a [selected] list
(selected.items) in .overrides/workflow.toml, not left undeclared — add it back to
selected.items to restore it

$ sq guide 1 show
error: unknown item type 'guide': no spec supplied, or the spec does not declare this
type. Declare it in .overrides/workflow.toml or check for a typo.
```

The read path's two suggestions are both wrong for this cause: declaring `[items.guide]` in
the override does **not** restore it (a newly-declared key omitted from the `[selected]` keep
list is deselected again — this review's own F11), and it is not a typo.

## Why

The provenance branch was added to `_services/_base.py::_create_model` only. The read path
raises the generic message from `_models/_vocab.py:66` (and the identical fallback at
`_services/_base.py:460`), which predates the merge engine and cannot distinguish "never
declared" from "declared then deselected".

## Why it matters

The create path proved the distinction is knowable and worth stating — `item_type in
bundled_spec().items` is the whole test. Leaving the read path on the generic message means
the adopter's *first* encounter with a dropped type (a `show`/`list` on an ID they still have)
gets the worse of the two messages, and following it costs them a round trip.

Ranked low because the refusal itself is correct and clean; only the remedy is misdirected.

## Suggested shape

Lift the provenance branch into one helper both paths call, so the message is written once.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-08-01T19:22:59Z] Elias Python:
  - Factored the create-path's provenance check into a shared squads._workflow.dropped_via_selected(item_type, spec) (the merge-engine reasoning: [selected] is the only way to remove a bundled key, so absence-from-active-plus-presence-in-bundled implies dropped, never merely undeclared) and used it from both _services/_base.py (refactored the existing F1 code onto it, no behaviour change -- re-ran its tests, all 6 still green) and the read path's resolve_item_id_typed (_cli/_common.py), which now raises the same [selected]-provenance message before ever reaching prefix_for's generic one.
- [2026-08-01T19:23:03Z] Elias Python:
  - Falsified: neutered the new read-path branch, watched the two provenance-specific tests go red (message reverts to 'declare it or check for a typo') while the never-existed-type negative test stayed green; restored, watched green. New tests in tests/cli/test_read_path_refuses_a_dropped_built_in_type.py, including the alias case and the negative (never-declared-type) case.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Dropped type's sq-<type> skill and SKILL item survive as orphans

<!-- sq:finding:F18:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F18:head:end -->

<!-- sq:finding:F18:body -->
## What happens

F5's threading stops role pointers naming a dead type's skill, but the skill itself — the
`SKILL` item and both generated files — survives with nothing pointing at it, and `sq check`
reports no issues. F5's own "What happens" listed those files as part of the symptom, so a
reader who sees F5 closed will assume they are gone.

Reproduced on a synced `claude_code` squad.

**Drop** (`guide` via `[selected]`, then `sq sync`): no role pointer lists `sq-guide` any more
(the fix). Still present: `.claude/skills/sq-guide/SKILL.md`, whose body still reads
`description: "Working with guide items in this squad: …"` and `@`-points at
`squads/agents/skills/SKILL-000014-sq-guide.md`; and `SKILL-14  skill  Active  sq-guide` on the
board. `sq check` → `✓ no issues`.

**Rename** (`feature` → `story`, then `sq sync`): no pointer lists `sq-feature`; `sq-story` is
generated and correctly not auto-preloaded. Still present: `.claude/skills/sq-feature/`, and
both `SKILL-13 sq-feature` and `SKILL-14 sq-guide` Active. `sq check` → `✓ no issues`.

## Why

Reclamation is gated on `candidate_orphans`, which unions `active_skill_slugs(spec)` with every
live `SKILL` item's slug — and the stale `SKILL` items are still live, so they keep themselves
alive. `is_system_skill('sq-feature', spec)` also still returns `True` via
`bundled_skill_slugs()`, which is bundled-only, so the stale skill is never reclassified as
author-defined either. Both were named in F5's body; neither was in its suggested shape.

## Why it matters

Low, not medium: nothing points at these files any more, so no agent is instructed to load a
skill for a type that does not exist — which was F5's actual harm. What remains is an inert
artefact plus a board entry that outlives its type, and a `sq check` that calls it clean.

## Suggested shape

Either retire the `SKILL` item when its type leaves the spec (and let the existing orphan
reclamation take the files), or make `sq check` report a live `sq-<type>` skill whose type the
active spec no longer declares. A ruling is needed first: a squad that drops a type
temporarily may want the skill kept.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-08-01T19:53:35Z] Elias Python:
  - Fixed. is_system_skill stayed bundled-blind on purpose (still the correct no-hand-editing test); added orphaned_skill_item_type(slug, spec) as the separate 'is this still on offer right now' derivation, threaded into ServiceCore._project_roster_item's live predicate (shared by sync's roster sweep and the single-item transition path) so a stale bundled-or-custom sq-<type> skill withdraws its pointer/body automatically on the next sync, no new stored state.
  - sq check also flags a live SKILL item whose type is gone (warn level, non-fatal) so it no longer reports clean, and sq sync reports one notice per skill it withdraws this way.
  - Both: sync withdraws (reusing the existing materialise/withdraw projection, the same one --unlink retirement uses), check backstops so the gap is never silent between syncs. Reversibility verified end to end: drop guide -> sync withdraws .claude/skills/sq-guide + flags on check; restore guide -> sync re-materialises it and check goes clean, with zero manual reconciliation.
  - Falsified: reverted the three changes, watched 3 of 4 new tests go red (the 4th, the negative case, correctly stayed green); restored, all green. New tests: tests/service/test_dropped_type_skill_orphan_is_withdrawn_and_flagged.py.
- [2026-08-01T20:17:41Z] Paul Reviewer:
  - Verified closed, including the reversibility claim: after restoring the dropped type and running sq sync, .claude/ is byte-identical to a pristine init (diff -r clean), role pointers name the skill again and sq check is clean — nothing stored, as claimed. Rename and no-backend shapes both behave (a --backend none squad seeds no SKILL items, so the sweep correctly has nothing to act on). The withdraw does over-reach on one shape: any author-created skill slugged sq-* is swept. Filed as F23.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — claude_section genericisation is inconsistent within edited lines

<!-- sq:finding:F19:head -->
**Status:** 🟡 Fixed
**Severity:** 🔵 Info
<!-- sq:finding:F19:head:end -->

<!-- sq:finding:F19:body -->
Documentation / consistency, ranked below the defects.

F6 replaced three `feature` literals in `claude_section.md.j2` with generic placeholders. Two
of the three edited lines still carry the same class of literal, so the file now applies the
ruling inconsistently within a single sentence:

- line 84 (edited): `until the parent's tasks are `Done` and its reviews `Approved`` — `feature`
  became `parent`, while `tasks` and `reviews` (both built-in type names) and `Done`/`Approved`
  (both built-in status names) stayed.
- line 101 (edited): `sq <type> <n> <kind> <k> update --status InProgress` — the type, number
  and kind became placeholders; the status literal did not.
- line 100 (untouched, same bullet): `(e.g. `sq task 35 show`)`.

All three degrade the same way F6 described: wrong-by-construction for an adopter who drops or
renames the type or status they name. None crashes; the surrounding spec-derived loop below is
correct.

F6's body asked for one deliberate ruling on single-type illustrative examples rather than
case-by-case treatment. What landed is case-by-case, applied to one word per line. Either
ruling is defensible — genericise the examples, or keep concrete examples because a bundled
squad reads better with them — but the file should not hold both within one sentence, and F6
being marked closed will read as "this file is done".

Scope note: the implementer flagged the identical literals in `agents_section.md.j2` and
`squads_skill.md.j2` (`sq feature 12 story 1`, `FEAT-<n>`, `a feature's whole subtree`) as
outside F6 and left them — correct, and they belong to the same ruling.

Verified alongside: the golden (`tests/goldens/claude_md_section.txt`) matches the rendered
region, this repo's own `CLAUDE.md` carries exactly the three changed lines, and
`templates_manifest.json` gained only the unreleased `0.12.3` key (one hunk, 28 insertions,
`git diff v0.12.2..HEAD`); `scripts/gen_template_manifest.py --check` reports current. No
released manifest entry moved.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-08-03T07:45:05Z] Catherine Manager:
  - Closed: the named literals are gone from claude_section, which is now derived from the active spec and live roster. Verified by grep against the template.
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — Folder normalisation leaves case and the unconstrained folder open

<!-- sq:finding:F20:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🔵 Info
<!-- sq:finding:F20:head:end -->

<!-- sq:finding:F20:body -->
Spec gap, ranked below the defects. The normalisation fix itself is correct and verified.

Driven on a squad with one live `task` filed under `tasks/`, one `[items.task] folder = …`
override per row:

| declared | result |
| --- | --- |
| `"tasks/"` | loads clean (was the F3 false refusal) |
| `"./tasks"` | loads clean |
| `"tasks//"` | loads clean |
| `"Tasks"` | refuses |
| `"tasks/../tasks"` | refuses |
| `"/tasks"` | refuses |
| `""` | refuses |

The path-syntax half is closed. What the deliberate case carve-out and the untouched model
leave open:

**Case.** The rationale — case-equality is a filesystem property, and folding it would let a
real mismatch through on a case-sensitive filesystem — is right, and Linux/CI is the case that
must not silently pass. But it makes the refusal's own factual claim untrue on the other half
of the platform matrix: on a case-insensitive filesystem (macOS/Windows default), `Tasks` and
`tasks` *are* one directory, so `1 live item(s) are still filed under the old folder` is false
and `change it only while the type has no items` is unsatisfiable for a change that is in fact
a no-op. Unreproduced on this host — **hypothesis**, stated from the comparison being a plain
string equality. My read: the line is in the right place (fail closed on the platform where it
matters), but the *message* should stop asserting the items are elsewhere and say what the
check actually knows — the declared folder does not match the one these items were written
under.

**`""`, `/abs`, and `..`.** `ItemSpec.folder` is still an unconstrained `str`, so F3's second
suggested shape (constrain at the model layer) is not taken. Consequences, driven:
`folder = "<abs>/escape"` and `folder = "../../escaped"` are both accepted by the spec and
refused only later by `abspath`'s traversal guard (`error: path '…' escapes the squad folder`)
— a clean `SquadsError`, not a write outside the squad, so containment holds. `..` *inside*
the squad is accepted end to end: `folder = "guides/../notes"` writes to `squads/notes/` while
storing `guides/../notes/GUIDE-000009-g.md` as the item path, and survives a `sq repair`
round-trip unchanged — consistent, but it means two spellings of one directory can both be
persisted. A non-empty, relative, `..`-free constraint on `ItemSpec.folder` would close all of
these at the point of declaration, where the adopter can still act on it.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
- [2026-08-03T07:45:27Z] Catherine Manager:
  - WontFix, deliberate: folder normalisation folds path syntax and not case, because case is a filesystem property rather than a path-syntax one, and folding it would make the check lie on a case-sensitive filesystem. Documented at the site.
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — sq repair and sq adopt discard a re-foldered type's corpus

<!-- sq:finding:F21:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F21:head:end -->

<!-- sq:finding:F21:body -->
## What happens

The corpus-alignment check (§5a) exists to stop an override re-foldering or re-prefixing a type
that already has items, and its refusal ends `no command realigns an existing corpus`. Two
commands now walk straight past it and **discard that corpus from the index** instead —
reporting success, leaving `sq check` clean, and blaming the adopter's own files.

### Via `sq repair`

Squad with `TASK-9` and `TASK-10`, then `[items.task] folder = "tickets"`:

```
$ sq list -a
error: workflow spec is incompatible with the live index — run `sq workflow lint` …
  - type 'task' folder changed to 'tickets' … ['TASK-9', 'TASK-10'] — revert the folder
    in the override, or change it only while 'task' has no items (no command realigns an
    existing corpus)

$ sq repair
rebuilt index: 8 items, counter=10
warn TASK-9: indexed but no markdown file found (deleted?)
warn TASK-10: indexed but no markdown file found (deleted?)
```

Both files are still on disk at `squads/tasks/TASK-0000{09,10}-*.md`. After this, every
command loads clean, both tasks are gone from `sq list -a`, and `sq check` reports
`✓ no issues`. The warning's own claim — no markdown file found, deleted? — is false.

Identical with `prefix = "TICKET"` instead of a folder change (8 items, counter 9, file still
at `squads/tasks/TASK-000009-task-one.md`, `sq check` clean).

### Via `sq adopt`

Worse, because importing existing files is adopt's entire purpose and nothing warns at all.
Squad with 21 items including three tasks, same `folder = "tickets"` override:

```
$ sq adopt
│ imported: 18 existing item(s) │
```

Index drops 21 → 18. Three `TASK-*.md` files remain on disk, invisible. `sq check` → `✓ no issues`.

## Why

`repair` rebuilds from `_iter_item_files` (`_services/_maintenance.py:516`), which scans
`squad_dir / ts.folder` and globs `PREFIX-*.md` **from the active spec**. A re-foldered type's
declared folder is empty; a re-prefixed type's glob matches nothing. Either way the scan yields
nothing, `missing_ids` fills with every real item, and the rebuilt index is written.

Both exposures are new in this change, and each comes from a separately-sound fix:

- `sq repair` was `get_service()` until the F14 fix; `open_service`'s fail-closed cross-check
  was the only thing keeping repair away from a spec/corpus mismatch. Swapping in
  `get_service_bypassing_index_cross_check` removed that guard without giving repair any
  handling for the mismatch it can now meet.
- `adopt` scaffolded and repaired against `bundled_spec()` until `_init_time_spec`; the bundled
  folders matched the corpus, so its `svc.repair()` always found the files.

## Why it matters

This is the exact outcome §5a was built to prevent, reached through the front door. The board
loses items with no error; the reflog records `{"op":"repair","delta":{"missing":["TASK-9",
"TASK-10"]}}` but nothing surfaces it; and `sq check` — the gate this repo treats as
must-pass — is clean afterwards, so nothing prompts anyone to look. The adopter's most likely
route here is following a message: every command tells them to run `sq workflow lint`, and the
nearest maintenance verb is `sq repair`.

Not data loss: the `.md` files are untouched, the counter keeps its high-water mark (no ID
reuse), and reverting the override then re-running `sq repair` restores all ten items exactly.
Recoverable, silent, and it inverts a refusal into a discard.

## Suggested shape

`get_service_bypassing_index_cross_check` should bypass the *badge/status* families it was
introduced for and still respect corpus alignment — a prefix/folder mismatch is precisely the
state in which repair must not run, because repair cannot see the files any more. Failing
that, `repair`/`adopt` should refuse (or fall back to scanning the pre-override folders) when
the spec's declared folder/prefix for a type disagrees with what the previous index holds,
rather than reporting those items as deleted.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
- [2026-08-01T20:17:43Z] Paul Reviewer:
  - Both exposures are new in this change and each traces to a separately-sound fix: sq repair lost the corpus-alignment gate when F14 swapped get_service for get_service_bypassing_index_cross_check, and sq adopt gained the merged spec from _init_time_spec (it previously scanned bundled folders, which matched the corpus). Neither fix is wrong on its own; together they removed the only thing keeping a folder/prefix-realigning spec away from the rebuild scan.
- [2026-08-01T20:46:19Z] Elias Python:
  - Fixed: repair()/adopt() (via svc.repair()) now refuse rather than silently rebuild, when a previously-indexed item goes missing from a fresh disk scan AND its recorded path is still a real file (never a prefix/id field comparison, so a hand-reconstructed Item's metadata can't false-positive it). A disk-level bundled-vs-active fallback covers the no-prior-index adopt case. Falsified both directions (repair folder/prefix rename, adopt fresh-tree variant): tests/integration/test_workflow_override_service_integration.py.
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — A bad pre-placed override wedges sq init half-created

<!-- sq:finding:F22:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F22:head:end -->

<!-- sq:finding:F22:body -->
## What happens

`_init_time_spec` correctly fails closed on a bad pre-placed override — but it runs *after*
`sq init` has already written `.squads.toml`, so the adopter's very first command leaves a
half-created squad that `sq init` then refuses to finish.

Reproduced, malformed TOML (a missing `]`) pre-placed at `squads/.overrides/workflow.toml`:

```
$ sq init --backend claude_code
error: Malformed workflow override …/squads/.overrides/workflow.toml: Expected ']' at the
end of a table declaration (at line 1, column 13) — run `sq workflow lint` to see details
```

Accurate and useful. On disk afterwards: `.squads.toml`, a root `.gitignore`, and
`squads/` — but no `.squads.json`, no type folders, no roster, no backend scaffolding.

The adopter fixes the typo and retries:

```
$ sq init --backend claude_code
error: …/.squads.toml already exists (use --force to overwrite)
```

Every other command now says `error: missing index .squads.json; run `sq repair` to rebuild
it from the markdown files`. Following *that* advice makes it worse:

```
$ sq repair
rebuilt index: 0 items, counter=0
$ sq check
error CLAUDE.md: managed file missing — run `sq sync` (backend: claude_code)
error .claude/settings.json: managed file missing — run `sq sync` (backend: claude_code)
```

— a squad with zero roles, zero skills and no backend scaffolding, which no amount of
`sq sync` will populate. The only clean recovery is `sq init --force`, which nothing in the
chain names and which reads like it might destroy something.

Identical for a floor-violating (rather than malformed) override:
`[items.task] lifecycle = "nope"` → `error: Invalid workflow spec: - item 'task': lifecycle
'nope' not declared in lifecycles`, same leftovers.

## Why

`init` writes `config_path` and runs `ensure_root_tmp_ignored(root)` before
`_init_time_spec(sp.squad_dir)` is called (`_services/_service.py`), and the `AlreadyInitializedError`
guard at the top keys on that same `.squads.toml`. So the failure point sits between "the file
that makes init refuse to re-run" and "everything that makes the squad usable".

New in this change: before `_init_time_spec` existed, `init` never read the override, so it
completed against the bundled spec and the adopter met the bad override on their *next*
command, with a fully-created squad to fix it in.

`adopt` shares the shape when it is the one creating `.squads.toml`; adopting an
already-configured folder is unaffected (the config is loaded, not written).

## Why it matters

Init is the adopter's first command and a pre-placed override is exactly the workflow this
feature invites ("drop your override in, then init"). Validating it is right; validating it
after the point of no return is what turns a typo into a wedged squad.

## Suggested shape

Resolve and validate the override *before* the first write — the override path is derivable
from `root`/`squad_dir` without creating anything — or make the `AlreadyInitializedError`
guard tolerate a config with no index beside it, so a retry after the fix just completes.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
- [2026-08-01T20:46:34Z] Elias Python:
  - Fixed: init()/adopt() now call _init_time_spec (validate the override) before any state is written — right after the AlreadyInitializedError guard for init, before the config write in adopt's fresh-config branch. A bad pre-placed override now means the command never starts: no .squads.toml, no scaffolding, retry after fixing it just works, no --force needed. Falsified both directions (malformed TOML, floor-violating override): tests/integration/test_workflow_override_service_integration.py.
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — Orphan sweep withdraws any author-created skill slugged sq-*

<!-- sq:finding:F23:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F23:head:end -->

<!-- sq:finding:F23:body -->
## What happens

`orphaned_skill_item_type` decides "this was a per-type skill" from the `sq-` prefix alone, so
**any author-created skill whose slug starts with `sq-`** is treated as the residue of a
dropped type: `sq sync` deletes the pointer `sq skill add` just created, and `sq check` warns
about a type that never existed.

Reproduced on a clean squad with no override at all:

```
$ sq skill add sq-onboarding --desc "House onboarding runbook"
created skill SKILL-19 → agents/skills/SKILL-000019-sq-onboarding.md
$ ls .claude/skills
greeting sq-bug … sq-onboarding … squads        # the pointer was created

$ sq check
warn SKILL-19: skill 'sq-onboarding' is Active but type 'onboarding' is no longer declared
— its generated files have been withdrawn; restore the type to bring it back, or retire
this skill (update its status) to close it out

$ sq sync
… generated files withdrawn; restore the type to re-materialise, or retire this skill …
$ ls .claude/skills
greeting sq-bug … squads                        # sq-onboarding is gone
```

`sq skill add` and `sq sync` now disagree about the same artefact: one creates it, the next
destroys it. The skill item stays `Active` on the board, permanently un-materialisable, and
the remedy the warning offers — "restore the type" — names a type the adopter never had.

## Why

```python
def orphaned_skill_item_type(slug, spec):
    if slug in active_skill_slugs(spec): return None
    if slug in (SQUADS_SKILL, GREETING_SKILL, MEMORY_SKILL): return None
    if not slug.startswith("sq-"): return None
    return slug[len("sq-"):]
```

Nothing distinguishes "a generated `sq-<type>` skill whose type went away" from "an
author-created skill that happens to start with `sq-`". The docstring makes this explicit and
treats it as a virtue — *"Treats a dropped built-in and a dropped custom type identically …
neither needs special-casing by history, only by whether spec still declares the type today"*.
That symmetry is exactly what removes the only evidence that could tell the third case apart.
The two skill items carry no provenance either: a generated `sq-guide` and an author-made
`sq-onboarding` differ only in incidental `extra` keys.

`sq-` is not an obscure choice: every bundled skill uses it, so it reads as the house
convention for a squads-related skill.

## Why it matters

A generated pointer is regenerable and the SKILL item survives, so nothing is unrecoverable —
but this is a maintenance command deleting a first-class artefact another command just made,
on a slug the CLI accepted without complaint, and then reporting a permanent `sq check` warning
that misnames the cause. Compare with F18's actual harm (an inert leftover nobody points at):
the cure now reaches further than the disease.

## Suggested shape

`is_system_skill(slug, spec)` already answers this correctly for the case that matters: it is
`True` for `sq-guide` (bundled-blind by design, as its own docstring now says) and `False` for
`sq-onboarding`. Gating the withdraw on it would stop the over-reach immediately, at the cost
of no longer sweeping a *dropped custom type*'s skill — which is the smaller harm and the one
F18 was originally filed at `low` about. If the custom-type half must be kept, the skill item
needs to record that it was generated for a type (an `extra` key set at seed time), so the
predicate can ask history instead of guessing from the prefix.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
- [2026-08-01T20:46:27Z] Elias Python:
  - Fixed: orphaned_skill_item_type now gates on is_system_skill(slug, spec) before deriving a type name from the sq- prefix, so an author-created sq-* skill is never mistaken for generated residue. Kept is_system_skill bundled-blind (a dropped/renamed built-in's stale skill is still swept, matching F18); accepted trade-off: a dropped CUSTOM type's skill no longer self-identifies here (smaller harm, as you suggested). Falsified both directions: tests/service/test_dropped_type_skill_orphan_is_withdrawn_and_flagged.py::test_an_author_created_skill_named_sq_something_is_never_swept.
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — Additive-only collection change reopens the false attribution

<!-- sq:finding:F24:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F24:head:end -->

<!-- sq:finding:F24:body -->
Residue of F14, now narrow. The attribution test is "does this collection differ from bundled
at all", not "was this code valid under bundled and is it not now" — so an override that only
**adds** codes still re-opens the false override attribution.

Reproduced. Squad with one live `task`; index entry hand-corrupted to `priority: "bogus"`
(frontmatter still says `urgent`); override that leaves every bundled code in place and adds
one:

```toml
[collections.priority]
badges = [
  { code = "blocker", label = "Blocker", emoji = "⛔" },
  { code = "urgent", … }, { code = "high", … }, { code = "medium", … }, { code = "low", … },
]
```

```
error: workflow spec is incompatible with the live index …
  - 'task' field 'priority' carries code 'bogus', which the workflow spec's 'priority'
    collection no longer declares, but 1 live item(s) still carry it: ['TASK-9'] — add
    'bogus' back to the collection, revert the override, or update the affected item(s)
```

The collection strictly grew; `bogus` was never in it; `no longer declares`, `add 'bogus'
back` and `revert the override` are all still false.

`_collections_differ_from_bundled` compares `coll.badge_codes != bundled_coll.badge_codes`,
which is true for a pure addition. Ranked low rather than high because F14's real damage is
gone: `sq repair` is no longer gated, so the adopter runs it and the stale value is fixed —
what is left is a wrong message on the way there.

The tighter predicate is per-value rather than per-collection: attribute to the override only
when the offending code **was** in the bundled collection and is not in the merged one. That
is strictly more accurate for every shape the current test covers, and it also removes the
need for `_collections_differ_from_bundled`'s two "return True" special cases to be
approximations.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
- [2026-08-01T20:46:40Z] Elias Python:
  - Fixed: attribution moved to per-value (_code_removed_by_override): a code is only blamed on the override when it was valid under bundled AND is missing from the merged collection. An additive-only override no longer re-opens the false attribution. Falsified both directions: tests/integration/test_workflow_override_service_integration.py::test_a_stale_badge_code_is_unflagged_when_the_override_only_added_codes.
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T19:57:54Z] Paul Reviewer:
  - Reproduction environments for every driven claim were scratch squads under the session scratchpad (sq init with --backend none and with claude_code+agents_md), not this repo. Falsification used a session-start pytest plugin monkeypatching the mechanism in place — no edit under src/ or tests/, nothing staged.
  - Unreproduced: nothing. Every finding in this review was driven to a concrete observed output; the two coverage findings (F7, F10) state the mechanism works by hand and only the regression guard is missing.
- [2026-08-01T18:57:39Z] Paul Reviewer:
  - Delta re-review of the fix rounds in dde8932 — this review continuing, not a fresh pass. Every claim below was driven on scratch squads under the session scratchpad; nothing reproduced in this repo, no edit under src/ or tests/, nothing staged.
  - F1 closed. The membership gate sits above every unguarded self.spec.items lookup at the top of _create_model, and _create_model is the single funnel for the CLI create commands, the guide command, the hidden aliases, and the bulk importers pre-pass (which also refuses first on its own vocabulary check). The [selected]-provenance premise is airtight: apply_selected is the only deletion in the engine and it operates only on top-level sections, so a bundled key absent from the merged spec can only have gone through selected.items. Two residues filed: F16 (sq --help still advertises the dropped type) and F17 (the read paths refusal advises what cannot work).
  - F2 closed as a mechanism — driven across item field, sub-entity field, shrink-to-empty, unused-code removal (correctly silent), multi-item grouping, multi-collection, and [selected] dropping a whole collection (caught earlier by the referential floor with correct deselection provenance). The message it emits is NOT sound in every reachable case; see F14.
  - F3 closed for path syntax (trailing slash, ./ and // all fold). The deliberate case carve-out and the still-unconstrained ItemSpec.folder are recorded as F20.
  - F4 closed, and probed for the regression it could have caused: gating on open_service raising does not mislabel a corrupt index or a stale stamp.
  - F5 closed. All seven production call sites across five files are threaded and the intersection is right; drop and rename both verified end to end on a synced claude_code squad. Orphan residue filed as F18.
  - F6 closed. Golden, this repos CLAUDE.md and the manifest all verified — one hunk vs v0.12.2, only the unreleased 0.12.3 key, gen_template_manifest.py --check current. Inconsistency within the edited lines filed as F19.
  - F7 closed. Re-ran the original experiment: neutering workflow_stamp_finding now turns three tests red in tests/unit/test_workflow_lint_merge_errors.py (16 pass clean), where it turned zero red before.
  - On the two-message split: the placement is right and the load-boundary half is sound — _check_field_codes cannot see an override, its message never presupposes one, and with an override present the loader check strictly subsumes it, so it is unreachable in the override-caused shape. The loader half is where it breaks. It can see that an override exists but not that the override touched collections, and states causation as fact anyway. F14 carries the reproduction and the consequence: sq repair, the actual remedy in the most likely trigger, is both unnamed and gated by the check.
  - Still-open findings: none of F8, F9, F11, F13 is worse. F10 is materially better and arguably closed by F3s fix — the folder half now has two tests through a real parsed override (trailing-slash-is-not-a-mismatch, and a genuine re-folder refusal), which is exactly the coverage it asked for.
  - Disposition: changes requested. One high (F14) and one medium (F15), both in the surface the fixes created. F14 should land before acceptance — it regresses stale-index recovery for any squad that has an override file at all. F15 is the same release. F16-F20 are trackable follow-ups. Leaving the review at InReview for the loop to move; my recommendation if it were mine to set is ChangesRequested. @tech-lead @python-dev
- [2026-08-01T20:18:02Z] Paul Reviewer:
  - Final delta re-review at 54cbaba. Driven on scratch squads under the session scratchpad; no edit under src/, tests/ or docs/, nothing staged.
  - Closures verified: F14 (original repro now gives the accurate cause-agnostic message and sq repair fixes it; true-positive contrast holds — a genuine shrink refuses everywhere while repair still runs), F15 (three distinct per-family hints; the badge one names `sq <type> <n> update --<field> <code>`), F16 (sq --help and sq create --help both hide the dropped type, while sq guide 1 show and the alias sq g 1 show still dispatch to the accurate refusal), F17 (the provenance message now reaches show/comment/update via resolve_item_id_typed, and a never-bundled type still gets no false provenance), F18 (reversibility is real — restore the type, sq sync, and .claude/ is byte-identical to a pristine init).
  - init/adopt against a pre-existing override: the reported roster bug is genuinely fixed — shadowing the agent lifecycle initial seeds every roster item at the merged status and the fresh squad loads clean. Rename plus re-prefix at init is clean end to end (stories/ and tickets/ created, no features/, correct prefixes on create, no sq-feature skill, sq check clean). An empty override is a no-op. A non-live roster initial is diagnosed by sq check with a remedy rather than silently half-scaffolded. Adopting an already-configured folder is unaffected. The two shapes that break are filed: F22 (a bad pre-placed override wedges init half-created) and F21 (adopt discards a re-foldered corpus).
  - F21 is the blocker. sq repair and sq adopt now walk past the corpus-alignment refusal and drop the affected items from the index, reporting them as "no markdown file found (deleted?)" while the files sit untouched on disk, after which sq check reports no issues. Recoverable — revert the override, sq repair, all items return, and the counter keeps its high-water mark so no ID is reused — but it inverts the one refusal §5a exists to make, via the command the error messages point people at.
  - Open by your decision and unchanged: F8, F9, F11, F13, F19, F20 — none is worse. F10 stays effectively closed by F3s fix.
  - Verdict: I would NOT approve yet. Exactly one thing blocks it — F21. F22 and F23 are both real regressions on adopter-facing surfaces (first-run init, and sq sync deleting what sq skill add just made) and I would want them in the same release, but neither is a correctness hazard to committed data the way F21 is. F24 is a message nit. Everything else in this feature is sound and I have attacked it hard across three passes. @tech-lead @python-dev
- [2026-08-03T07:45:53Z] Catherine Manager:
  - Approved as the second party. The reviewer recorded that it would approve once the corpus-discard blocker closed; that is fixed and independently verified, along with every other high and medium finding. One finding stays Open with its disposition named rather than closed as done, three are WontFix with reasoning, and the rest are Fixed. Full suite 2369 passed / 6 skipped, all gates clean.
<!-- sq:discussion:end -->
