---
id: TASK-933
sequence_id: 933
type: task
title: Enumerate view-tag writers; unify skip/hint parity (F17-F21)
status: Done
parent: FEAT-906
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
- REV-926:addresses
subentities:
- local_id: ST1
  title: Enumerate view-tag writers, gate F17
  status: Done
  story: US5
- local_id: ST2
  title: Table-drive repair-corridor parity; fix F18/F20
  status: Done
  story: US5
- local_id: ST3
  title: Unify the empty-body hint predicate; fix F19
  status: Done
  story: US5
- local_id: ST4
  title: Fail-safe direction for the drift trigger (F21)
  status: Done
  story: US5
created_at: '2026-09-09T14:39:31Z'
updated_at: '2026-09-10T09:34:48Z'
---
<!-- sq:body -->
## Scope

Closes REV-926's third round (F17-F21) the way the reviewer's own diagnosis prescribes: not five
more instance fixes, but the two mechanically enumerable families those five sit in, each closed
by a test that fails today and passes after the fix — plus F21, which is neither family.

- **Family A — a writer the code itself enumerates, and nobody swept it (F17).**
- **Family B — a command's message or exit code not re-derived after its behaviour changed
  (F18, F19, F20).**
- **F21 — on its own terms:** F14's fix traded a loud crash for a quiet wrong answer in the
  version-drift trigger.

## ST1 — Enumerate every `sq:view:<name>` writer; close family A (F17)

`grep -rn 'markers.view_tag(' src/` finds exactly six sites. Classify each once, in one test,
and give a new sixth-writer-tomorrow the same test as a gate instead of a future review round:

1. `_services/_base.py:876` — role creation (`_create_core`). **Gated** on
   `ROLE_DEFINITION_VIEW_NAME in self.spec.views` (F12's fix).
2. `_services/_maintenance.py:311` (`_converge_body_tag`) — the repair backfill's mutator.
   **Gated at its caller**, `_repair_body_tag`'s classifier (`self.spec.views`, F5's fix) —
   `_converge_body_tag` itself is never called with an undeclared name.
3. `_backends/_claude_code/_backend.py:209` (`_write_managed_skill`) — **ungated**: the three
   system-skill call sites (~line 116) and the two per-item-type-skill call sites (~lines 274,
   287) pass `body_tag=SYSTEM_SKILL_VIEW_NAMES[...]`/`ITEM_SKILL_VIEW_NAME` unconditionally, with
   no `spec.views` check anywhere on this path. **This is F17 — fix it here.**
4. `_services/_views.py:38` (`insert_view`) — **self-gated**: refuses through
   `resolve_view_target` before ever writing (`ViewsMixin.insert_view`'s own docstring).
5. `_services/_views.py:64` (`remove_view`) — **deliberately ungated**: documented as the
   recovery path for a tag whose view was dropped out from under it; must keep working
   precisely when the name is no longer declared.
6. `_services/_validators.py:729` (`_item_skill_shadowed`) — **not a writer**: builds `tag_line`
   only to compare against on-disk content for a check finding; writes nothing.

**Fix (F17).** Gate `_write_managed_skill`'s callers, not the method itself — mirror the
condition F5/F12 already use: pass `body_tag=None` when the resolved view name is not in
`spec.views`, at each of the three call sites in `_backend.py` currently passing one
unconditionally. `_write_managed_skill` already special-cases `body_tag=None` (documented today
as "this method's own contract for a caller that doesn't have one (there is none today)") — that
branch stops being dead; no new mechanism, no change to the method's own signature or body.

**The test.** One test (new module under `tests/meta` or `tests/service`) that greps
`markers.view_tag(` across `src/` with a **whitespace-collapsed scan** (see Testing below — the
line-wrapped-token rule applies to this exact grep), asserts it finds **exactly the six sites
above** (by file + a stable per-site marker, not a brittle line number), and asserts each is
tagged with one of `gated` / `self-gated` / `deliberately-ungated` / `not-a-writer` with the
reason — a **seventh, unclassified site fails the test outright**. Before this task's fix, site 3
cannot be classified `gated` (it has no `spec.views` check to find), so the test fails today; after
the fix, it does.

**Driven acceptance, reviewer's exact repro:** on a squad whose `.overrides/workflow.toml` drops
`item_skill` via `[selected].views`, declare a new item type and `sq sync` — before the fix,
`sq check`'s error count grows by exactly one per newly-created skill; after, it stays flat. Role
side (already fixed) stays flat throughout as the regression control. Also confirm the untouched
path: under a **declared** view, a newly created skill's body still carries the tag exactly as
before.

## ST2 — Table-drive `RepairResult`/`sync()`-skip-list parity; close F18 and F20

Three CLI consumers share this corridor: `sq repair` (`_cli/_main.py::repair`), `sq migrate up`
(`_cli/_migrate.py::migrate_up`), `sq sync` (`_cli/_main.py::sync`). `sq repair` is the reference
implementation — its wording and its exit contract (`unreadable` or `skipped` -> exit 1, named in
its own docstring) are what the other two must match, channel for channel.

**F20 — `sq migrate up` exits 1 on `unreadable` without ever printing it.** F15's fix wired
`skipped` into both the message loop and the exit condition; `unreadable` only made it into the
exit condition. Add the same reporting loop `sq repair` already has (`for msg in
run.repair.unreadable`), identical wording, beside the existing `skipped` loop in
`_cli/_migrate.py::migrate_up`.

**F18 — `sq sync` prints green "synced ... to this squads version" and exits 0 on a run that
withheld the stamp.** `MaintenanceMixin.sync()` already computes `backfill_skipped` as its own
local variable (`_services/_maintenance.py`, immediately before the `skipped += backfill_skipped`
line) and already uses it, a few hundred lines later, to decide whether to call `_stamp_version` —
the fact the CLI needs is computed and then discarded. Return it as a second channel (a small
result — a two-field dataclass/NamedTuple, or a second list — not string-matching the merged
`skipped` list, which mixes backfill declines with roster-skew and orphan-withdrawal messages that
have nothing to do with the stamp). `_cli/_main.py::sync` prints the stamp-withheld case with its
own sentence instead of the fixed "synced" line when that channel is non-empty (name the skip
message(s) already printed above it as the reason, don't repeat them). **Exit code is explicitly
out of scope** — `sq sync` already exits 0 for other pre-existing skip channels (roster skew,
unindexed bodies), and changing that is a call about the whole corridor's exit semantics, not
this finding; leave it 0.

**The test.** One table-driven test (e.g. `tests/cli/test_repair_corridor_message_parity.py`)
parametrized over `(command, channel)` — `(repair, skipped)`, `(repair, unreadable)`,
`(migrate_up, skipped)`, `(migrate_up, unreadable)`, `(sync, backfill_skipped-as-message)` — each
row builds the corpus state that channel needs (a marker-shaped `sq:body`, an unreadable file, a
pre-`0.15` `squads_version` with a refused body) and asserts the reporting command's printed
wording for that channel matches `sq repair`'s wording for the same input, **and** that `sync`'s
success line is *not* printed on the withheld-stamp row. Must fail today: `migrate_up` prints
nothing for the `unreadable` row, and `sync` prints "synced" unconditionally on the
`backfill_skipped` row.

## ST3 — One predicate for the empty-body hint; close F19

`sq role show` and `sq skill show` each derive their empty-body hint from their own ad hoc
boolean (`role_view_declared` / `view_dropped` in `_cli/_role.py` and `_cli/_skill.py`
respectively) that answers only "is the view declared" — not the second question that decides
whether "run `sq sync`" is actually true: **is a version drift outstanding** (the only condition
under which `_backfill_roster_body_tags` runs at all). Under a declared view with no drift
outstanding, both hints say "run `sq sync`" for a state `sq sync` provably cannot fix — the third
appearance, per the reviewer, of "the hint names an action that cannot be taken."

**Fix.** One helper (e.g. in `_views.py` beside `resolve_view_target`, or in
`_services/_maintenance.py` beside `_repair_body_tag`) that both `_cli/_role.py` and
`_cli/_skill.py` call in place of their own duplicated boolean, taking the view name, the active
spec, and whether a version drift is outstanding (`version_tuple(__version__) >
version_tuple(svc.paths.config.squads_version)` — read once, the same comparison `sync()` itself
gates the backfill on) and returning which of the following states applies:

- view undeclared -> today's F16 message (unchanged: names the view, points at `view rm` for an
  already-tagged body, says nothing can be run for an untagged one).
- view declared, drift outstanding -> today's "run `sq sync` to populate it" (unchanged: this is
  the one case where that sentence is true).
- view declared, no drift outstanding -> **new**: `sq sync` cannot help (state why: the backfill
  only runs on drift, and this squad has none outstanding); the real remedies are `sq repair`
  (if the body might be carrying unrecognised marker-shaped content) or `sq <role|skill> <addr>
  view add <name>` (if it is genuinely untagged) — name both, not neither.

Delete the code comment this round's own diff left behind that states the false property in
words — `_cli/_skill.py`'s "`sq sync` is the fix, **and only the fix**, for that one case" — it
is not the fix unless a drift is outstanding; say what's actually true instead of asserting a
property nothing enforces.

**The test.** One test per new-state row (declared+drift -> unchanged message; declared+no-drift
-> new message; undeclared -> unchanged, regression control) for **both** `sq role show` and `sq
skill show`, table-driven over the same three states so the two groups cannot drift apart again.
Must fail today: the declared+no-drift row currently gets the "run `sq sync`" sentence.

**Driven acceptance, reviewer's exact repro:** on an ordinary synced squad (`squads_skill`
declared, no drift), `sq skill squads view rm squads_skill`, then `sq skill squads show` — the
hint no longer claims `sq sync` will populate it; `sq sync` confirmed still a no-op against it
(driven, both before recording the new message and after); `sq repair` or `view add
squads_skill` confirmed to actually restore it.

## ST4 — Fail-safe direction for the version-drift trigger (F21)

`sync()`'s drift trigger (`version_tuple(__version__) > version_tuple(recorded_version)`) uses
the tolerant comparator F14 swapped in to stop a prerelease `squads_version` crashing it
(`schema_tuple` raised `ValueError` on the non-integer segment). `version_tuple` strips
non-digits *per segment and concatenates the survivors*, so `"0.15.0rc1"` -> `(0, 15, 1)`: a
prerelease sorts **above** its own release and **equal to** the next patch. A squad stamped by a
prerelease build reads as never-drifted against every release that follows, until a *later*
release's own backfill silently does not fire — F1's exact failure signature, reintroduced by
F14's own fix.

**Fix — the reviewer's own second-named option, not a rewrite of the shared helper:** give the
*trigger* the fail-safe direction; keep the *notice* (`_cli/_common.py::version_notice`,
cosmetic) on the tolerant comparator as-is. Try the strict comparison first
(`schema_tuple(__version__) > schema_tuple(recorded_version)`); on `ValueError` (either side
carries a suffix `schema_tuple` cannot parse — a prerelease, a dev/local segment), treat it as
drift rather than as an orderable version. Backfill is idempotent and cheap on a no-drift run
(the existing code comment on the trigger already says so) — over-triggering costs one
comparison and a no-op sweep; under-triggering is F1.

**The test.** `squads_version = "0.15.0rc1"`, `__version__` a later plain release — before this
fix, the trigger evaluates `False` (no backfill call, confirmed by patching/mocking
`_backfill_roster_body_tags` and asserting it was never awaited); after, `True` (asserted called).
Regression controls, unchanged: ordinary drift (`"0.14.0"` -> current) still triggers; ordinary
no-drift (already current) still does not; F14's own case (`squads_version = "0.14.0rc1"`, a
plain current `__version__`) still does not crash.

## Testing

**Falsify every new and changed test, both directions** (revert the fix, confirm red; restore,
confirm green) and report both — this round exists because the previous two rounds' own new
tests passed without proving anything past the one instance they were written to confirm.

**Test selection:** grep each changed name across `tests/` — `markers.view_tag`,
`_write_managed_skill`, `body_tag`, `backfill_skipped`, `RepairResult`, `strip_notice`,
`resolve_view_target`, `version_tuple`, `schema_tuple`, `role_view_declared`, `view_dropped` —
union the hits, plus the **unconditional floor**: `tests/meta`, `tests/integration`, `tests/cli`,
since this touches `_cli/_role.py`, `_cli/_skill.py`, `_cli/_main.py`, `_cli/_migrate.py`.

**False-zero rule — load-bearing on ST1 specifically.** ST1's whole closure *is* a completeness
claim ("exactly these six sites, nothing else writes this tag"), and a plain `grep -rn` returns a
false zero on a line-wrapped call (the formatter wraps at the column, not the token boundary).
Scan with internal whitespace collapsed, and validate that scan against a known positive — a
synthetic wrapped `markers.view_tag(` call, or the fact that `_backend.py:209`'s own call is
multi-line already — before trusting its count of six.

**No docstring or comment claiming coverage that doesn't exist, and none asserting a property
nothing enforces** — F19's own new comment (deleted in ST3) is the standing instance of the
second; don't reintroduce that shape anywhere in this task's own new prose.

## Refs

Implements ADR-880 (the "two writers this table is shared between" comment `_interactions/
__init__.py:172-175` already names, and the third amendment's `resolve_view_target` unification
this task extends to the hint). Addresses REV-926 F17, F18, F19, F20, F21.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 933 add-subtask "<title>"`; track with `sq task 933 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Enumerate view-tag writers, gate F17

<!-- sq:subtask:ST1:body -->
Gate _write_managed_skill's three call sites in _backend.py on spec.views (body_tag=None when undeclared) and write the six-site writer-enumeration test that fails on the ungated one today. Full detail in the task body's ST1 section.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Table-drive repair-corridor parity; fix F18/F20

<!-- sq:subtask:ST2:body -->
Add the missing unreadable-loop to sq migrate up (F20) and a second backfill_skipped channel from sync() so its CLI message stops claiming success on a withheld stamp (F18); table-drive the message/exit parity test across repair/migrate_up/sync. Full detail in the task body's ST2 section.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Unify the empty-body hint predicate; fix F19

<!-- sq:subtask:ST3:body -->
One helper (view declared / drift outstanding) read by sq role show and sq skill show in place of their own duplicated booleans; delete the false 'sq sync is the fix, and only the fix' comment. Full detail in the task body's ST3 section.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Fail-safe direction for the drift trigger (F21)

<!-- sq:subtask:ST4:body -->
Trigger the version-drift backfill on a strict-parse failure (treat as drift) instead of ordering it via the tolerant comparator; keep version_notice() on the tolerant one. Full detail in the task body's ST4 section.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-09T15:10:20Z] Elias Python:
  - Implemented per the enumeration/parity-first plan. All four falsified before fixing, both directions confirmed; gates + sq check clean; full report below.
  - ST1 (F17): 6 markers.view_tag( sites confirmed exhaustive (AST scan, validated against a wrapped-attribute known positive). Classified: _base.py:_create_core gated, _maintenance.py:_converge_body_tag gated-at-caller, _backend.py:_write_managed_skill was ungated -> now gated (callers pass body_tag=None when undeclared), _views.py:insert_view self-gated, _views.py:remove_view deliberately-ungated, _validators.py:_item_skill_shadowed not-a-writer. tests/meta/test_view_tag_writer_sites_are_exhaustively_classified.py + service-level driven repro (skill side, mirrors the existing role-side F12 test).
  - ST2 (F18/F20): sync() now returns SyncSkips (list[str] subclass, zero-breakage for ~45 existing call sites) carrying .backfill_skipped; sq sync prints a withheld-stamp sentence instead of the green line when non-empty, exit stays 0 (explicitly out of scope). sq migrate up gained the missing unreadable-loop, same wording as sq repair. tests/cli/test_repair_corridor_message_and_exit_parity.py, 6 rows.
  - ST3 (F19): new squads._views.empty_body_hint_state(name, spec, drift_outstanding=...) read by both sq role show and sq skill show, replacing their separate booleans; deleted the false 'sq sync is the fix, and only the fix' comment. tests/cli/test_empty_body_hint_state_is_shared_across_role_and_skill_show.py, 3 states x 2 groups.
  - ST4 (F21): added squads._models._schema.version_drifted(current, recorded) -- strict schema_tuple compare, ValueError -> treat as drift; sync()'s trigger and empty_body_hint_state's drift_outstanding computation both use it now (one implementation, not two). Class check: _cli/_migrate.py chlog and _overrides/_service.py's uncarried-base-pane rendering also call version_tuple, but both are read-only/informational (a listing, a diff-pane label) -- neither silently skips a mutation, so neither inherits F21's harm; left as is. _cli/_common.py also has its own byte-identical copy of version_tuple (dup, feeds only the cosmetic notice) -- flagging as a cleanup candidate, not fixing here (out of scope).
  - Gates: pyright/ruff/ruff format clean. Selection: grep-derived union (14 names) + floor (tests/meta, tests/integration, tests/cli) = 2203 passed, 7 skipped, 0 failed. sq check clean.
  - @reviewer for verification against REV-926 F17-F21. @manager for promotion when ready.
<!-- sq:discussion:end -->
