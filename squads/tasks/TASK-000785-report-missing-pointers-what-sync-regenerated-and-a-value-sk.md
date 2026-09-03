---
id: TASK-785
sequence_id: 785
type: task
title: Report missing pointers, what sync regenerated, and a value skew
status: Done
author: tech-lead
assignee: python-dev
priority: high
refs:
- BUG-784:fixes
- ADR-783:implements
description: 'Three reporting gaps: sq check is blind to per-entry backend pointers,
  sq sync recreates them silently, and check compares only two of the two stored homes''
  fields'
subentities:
- local_id: ST1
  title: Declare and check per-entry backend pointers for live entries
  status: Done
- local_id: ST2
  title: Report a per-entry artifact sync had to regenerate
  status: Done
- local_id: ST3
  title: Report a frontmatter/index value divergence from sq check
  status: Done
created_at: '2026-08-22T10:25:05Z'
updated_at: '2026-08-22T14:17:43Z'
---
<!-- sq:body -->
Three gaps in what the tool tells an operator about the state of its own generated files and its own
two stored homes. All three land in the same area — `_services/_validators.py`,
`_services/_maintenance.py`, and the backend ABC — so they are one owner's job.

Subtask order is the order to do them in, and ST1 → ST2 is a real dependency: ST1 produces the
roster-scoped set of per-entry paths that *should* exist, and ST2 needs exactly that set to know what
was missing before it regenerated it.

## Who this is for

`sq` is a tool other teams will use; this repository's own squad only tests whether it works. So the
reader every acceptance criterion below is written against is **an adopter on a fresh clone**, not a
file someone deleted by hand here.

That distinction changes what counts as done. A hand-deleted pointer in a squad whose `.claude/` is
committed is one way to reach the broken state. The sharper one is an adopter who has gitignored
`.claude/` or `.agents_md/` — a real and supported choice this tool does not forbid — for whom the
pointer never existed on that checkout at all. Nothing was deleted; the file simply is not there, on
every clone, for every teammate. Test both shapes, and treat the fresh-clone shape as the primary
one.

## This repository's own gate

`uv run sq check` must stay clean here. Two of these subtasks add reporting, so run it before you
hand back and **report the result explicitly** — a new rule that fires on this repo's own squad is a
defect in the rule, not a finding about the squad.

## Handoff, for all three subtasks

**Do not edit `CHANGELOG.md`.** Hand the tech lead your adopter-facing entry text in your handoff
comment and it gets applied there.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 785 add-subtask "<title>"`; track with `sq task 785 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare and check per-entry backend pointers for live entries

<!-- sq:subtask:ST1:body -->
`sq check` does not notice a missing per-entry backend pointer. Driven on a fresh squad with both
backends active:

```
sq init --roles minimal --backend claude_code --backend agents_md
rm -rf .claude/agents .claude/skills .agents_md
sq check        -> exit 0, zero mentions of any missing pointer
rm CLAUDE.md
sq check        -> exit 3, reports CLAUDE.md missing
```

Partial loss behaves exactly like total loss: deleting only one role's `.claude/agents/qa.md` while
leaving `manager.md` in place is silent in the same way, as is deleting one skill's pointer directory
or one `agents_md` staging file.

**This is a scope gap in what is declared, not a defect in the comparison.** `_backend_reconciled`
(`_services/_validators.py`) reports "managed file missing — run `sq sync`" for every path a backend's
`managed_paths(ctx)` declares, and both bundled backends declare only their compiled top-level
document: `claude_code` returns `CLAUDE.md` and `.claude/settings.json`, `agents_md` returns
`AGENTS.md`. No per-entry path is declared, so the check never looks for one.

## The unreported artifacts, both backends

- `claude_code` — `.claude/agents/<slug>.md` (one per live role) and `.claude/skills/<slug>/SKILL.md`
  (one per managed skill).
- `agents_md` — `.agents_md/roles/<slug>.md` and `.agents_md/skills/<slug>.md`, the staging files
  `write_managed` compiles `AGENTS.md` from. These are **doubly silent**: their absence does not show
  in `AGENTS.md` either, so nothing anywhere reveals it.

No surface in the CLI reveals this today. `sq role <slug> show` renders a normal card from the item;
`sq list -t role` and `sq role list` (including its "Live" column) read the item's status field and
never the filesystem; `sq sync` silently regenerates the file with no word that anything was missing.

## The hard constraint — this is the whole difficulty

**The declared set must be scoped to the roster's currently-live entries, never to a fixed or
historical slug list.** Retirement is a deliberate removal and behaves correctly today: retiring a
role withdraws its pointer via each backend's `remove_artifacts` and `sq check` stays clean on both
sides of the transition; reactivating regenerates it and check stays clean throughout. A fix keyed on
the wrong list turns every retire/reactivate cycle into a false positive on the retired side, or a
false negative on the reactivated side.

The predicate to reuse is the one `_project_roster_item` (`_services/_base.py`) already uses, in full:

- `item.status in self.spec.live_statuses(item.type)`, **and**
- for a `SKILL` item, additionally `orphaned_skill_item_type(slug, self.spec) is None` — a skill whose
  slug no longer names a type the active spec declares is withdrawn deliberately, so it must not be
  reported as missing.

Miss the second clause and a squad whose workflow override dropped a type reports a permanent false
positive that no `sq sync` can clear.

## Layering — the roster comes from the service, not from the backend

Backends read no index. `BackendContext` already carries `skill_paths` and `role_skills` precisely
because the service resolves them from the index and hands them over; whatever roster-derived input
the per-entry declaration needs follows that same pattern. `SquadGlobalContext` already holds
`index`, so `_backend_reconciled` has what it needs to derive the live set without new I/O and
without a backend loading anything itself.

Update the ABC's `managed_paths` contract text if its meaning widens — it currently says
implementations "should scope this to the always-present top-level files" and describes a
present-only check. Whatever shape you choose, the ABC must describe what a backend is now expected
to declare, so the next backend author gets it right without reading this item.

## The level, and its exit-code consequence — state it, do not assume it

`_backend_reconciled` reports at **error**, which gates `sq check`'s exit code. Applying that level to
per-entry paths means an adopter who has gitignored `.claude/` goes from exit 0 to a failing
`sq check` on a fresh clone, on a patch upgrade — a CI break they did not ask for.

**Do not silently pick.** Implement it, then state in your handoff: the level you used, and what
happens to the exit code for a fresh clone whose `.claude/` is gitignored. If you believe that case
should not fail the gate, say so with your reasoning rather than quietly choosing `warn` — the level
is a decision the tech lead is routing, and your measurement of the consequence is the input to it.

## Acceptance criteria

- With one live role's pointer absent, `sq check` names that file and that backend. Same for one
  skill's pointer directory, for an `agents_md` staging file, and for whole directories.
- **Partial loss is reported per entry**: two live roles, one pointer missing, and the report names
  the missing one and not the present one.
- **Both backends**, each reported independently and each naming itself.
- **The retirement case stays clean, driven as a cycle, not a snapshot**: activate, check clean;
  retire, check clean; reactivate, check clean. This is the criterion that fails on a fix keyed on the
  wrong list, so it is the first test to write.
- **A skill whose type the active spec no longer declares is not reported** — the second clause of the
  predicate, with its own test.
- **The fresh-clone shape is covered, not only the deleted-file shape**: a checkout where the
  per-entry files were never present reports the same way as one where they were removed. The
  acceptance is about a reader who never had the file, so a test that deletes a file it just created
  does not fully cover it.
- A squad with `active_backends = []` reports nothing, and a squad with one of two backends active
  reports only for that one.
- **No new I/O in the validator**: the live set is derived from the index snapshot the check already
  holds. Assert that the rule performs no additional index load.
- The ABC contract text describes what backends must now declare.
- The level and its fresh-clone exit-code consequence are reported in the handoff.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean **on this repository** and the result is reported.

Implementation: added `is_live_roster_entry(item, spec)` (squads/_interactions/__init__.py) as the single shared predicate — reused verbatim by `ServiceCore._project_roster_item` (squads/_services/_base.py) and the new `AgentBackend.managed_entry_paths` ABC method (squads/_backends/_base.py), implemented per backend in _claude_code and _agents_md. `_backend_reconciled` (squads/_services/_validators.py) derives live role/skill slugs from the already-loaded index (no new I/O) and reports an absent per-entry pointer at warn, while the existing top-level managed_paths files stay error. Retire/reactivate driven end to end and stays clean at every step; the orphaned-skill-type second clause has its own test; fresh-clone shape covered via a literal directory-copy clone, not just deletion.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Report a per-entry artifact sync had to regenerate

<!-- sq:subtask:ST2:body -->
`sq sync` silently recreates a missing per-entry pointer. Driven as part of the same investigation:
with a role's pointer deleted, `sq sync` regenerates it and says nothing — a clean, silent fix that
reveals neither that there was a fault nor that anything changed on disk.

Two reasons that silence costs something now. An operator who ran `sq sync` for an unrelated reason
never learns their agent configuration had been broken, so they never ask why. And the per-entry files
are committed artifacts in a default squad, so a regeneration means **a commit is owed** — a
regeneration nobody is told about is a working tree that quietly diverges from the branch.

## Scope — reporting only

This subtask adds no new regeneration behaviour and changes no write. `sq sync` already recreates
these files correctly; the deliverable is that it says what it did.

**And `sq sync` must not become chatty about a no-op run.** A sync over a healthy squad prints exactly
what it prints today. The notice fires only where a file that should exist was absent before this run
wrote it — the fault case, not the ordinary case. A message per live role on every sync would make the
signal worthless within one release.

## The channel already exists — decide whether it fits, and say so

`Service.sync()` returns `list[str]`, and the CLI prints each entry via `_print_scaffold_warnings` as
`warning: <text>`. The list already collapses exact duplicates order-preservingly.

That channel is warning-shaped, and the message here is arguably a warning (a fault was found) rather
than mere information. Reusing it is the cheap, coherent option. But **decide deliberately and state
the choice**: either the notice is a warning and rides the existing channel, or it is informational
and needs its own rendering — in which case say why the existing channel could not carry it, rather
than adding a second output path by reflex. Do not leave a reader guessing which category a
"regenerated" line belongs to.

## Knowing what was missing

`Artifact` carries `path`, `kind`, `backend` and an optional `warning`; there is no created-versus-
updated signal, so "was this absent before we wrote it?" has to be established somewhere.

The set ST1 builds — the roster-scoped paths that should exist — is exactly the input this needs, which
is why ST1 comes first. Derive the answer from that rather than adding an independent probe, so the
two cannot disagree about which files are expected. If you find a cleaner seam, use it and say why,
but the anti-goal is two separately-maintained notions of "the pointer that should be here".

## Acceptance criteria

- After a pointer, skill directory, or `agents_md` staging file is absent, `sq sync` regenerates it
  **and reports it**, naming the file and the backend.
- **A healthy sync is byte-identical in output to today's.** Assert it: capture a sync's output on a
  clean squad before and after the change and diff. This is the criterion that fails on an
  implementation that reports per entry unconditionally.
- Reported per file, so a partial loss names only what was actually missing.
- **Both backends**, each naming itself.
- **A retirement is not a fault and is never reported.** Retiring a role withdraws its pointer by
  design; a later `sq sync` must say nothing about it. Drive the retire → sync → reactivate → sync
  cycle and assert silence at every step.
- The exit code of `sq sync` is unchanged in every case, including when it reports a regeneration —
  this is a report, not a gate.
- The channel decision is stated in the handoff, with the reason.
- Duplicate suppression still holds: one missing file produces one line, not one per writer that
  touched the item.
- **The fresh-clone shape**: on a checkout where the per-entry files were never present, the first
  `sq sync` reports what it created rather than treating a never-existed file as ordinary. Say what
  that output looks like for a whole roster at once, and whether it is proportionate — a first sync
  after a clone reporting every role may be correct, or may be the chatty case in disguise. Decide,
  and state which.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean on this repository and the result is reported.

Implementation: sync() (squads/_services/_maintenance.py) computes the same roster-scoped managed_entry_paths set (per backend) once up front, snapshots which of those paths are absent BEFORE the roster loops write anything, then after the loops appends one 'was missing — regenerated by this sync (backend: <name>)' line per path that was absent-before and present-after. Reporting only — no write-path change. Channel: reuses the existing warning channel (sync()'s returned list, rendered as 'warning: ...' by the CLI) rather than a new rendering — the message is a fault report exactly like the existing drift-skip lines already on that channel. A healthy sync's output is unchanged (asserted directly). Retirement is never reported (the retired slug simply is not in the live set on either side). Fresh-clone shape: a whole-roster regeneration report (one line per live role/skill) is proportionate, not chatty — it fires once, only on the run that actually had work to do.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Report a frontmatter/index value divergence from sq check

<!-- sq:subtask:ST3:body -->
`sq check` says "no issues" on a squad whose own `sq sync`, seconds earlier, said to run `sq repair`.
ADR-783 §3–§6 settles the rule and is Accepted; read it in full, including the operator comment
approving the level. The constraints below are its rulings restated as acceptance.

## What is actually wrong

Check already does cross-source value comparison — on exactly two hand-picked fields. `_drift_issues`
runs `_status_drift` and `_parent_drift` against the on-disk frontmatter, through the
candidate/confirm round. So the defect is not "check has no skew rule"; it is that check compares two
fields of the two stored homes while the write seam refuses on all of them. An interrupted write that
landed on `title`, `description`, `priority`, `assignee` or `refs` is invisible to the one command
whose job is to say whether the squad is healthy.

Scoping a new rule to projected fields would be arbitrary for the same reason: the state is about an
interrupted write, not about projection. This rule **generalises the existing drift family**.

## The three rulings that are not negotiable

**1. `frontmatter_skew`, reused verbatim.** Check must not invent its own comparison. Reusing
`frontmatter_skew(text, item)` guarantees check reports exactly the set the write seam would refuse
on — no more (an operator told to repair a state nothing objects to) and no less (today's gap) — and
inherits the exemptions and the round-trip normalisation for free. Fold the two existing drift
predicates into it, so their raw-value comparison is replaced by the normalised one.

**2. Warn level.** Both existing drift predicates are `warn`; both existence directions of
`_index_reconciled` are `error`. A value divergence belongs to the drift family, not the
reconciliation family — the entry exists on both sides and one side is simply older — so it takes
`warn` and **`sq check`'s exit code is unchanged**. Carry over `_drift_message`'s existing habit of
naming the skew direction when the two `updated_at` values order it.

**3. No new I/O, and no new race.** `_scan_for_check` already keeps each file's raw text and its
parsed frontmatter, and check already holds the index snapshot. The rule is a cross-source claim, so
it is a candidate confirmed by the existing single re-read round exactly like its siblings — a sync
committing between scan and check resolves the candidate instead of producing a false warning, and a
clean board pays for no second load.

Nothing in the skew guard, `PERMITTED_EXTRA_SKEW`, or the projection changes.

## Acceptance criteria

- **The interrupted-write shape, driven end to end**: markdown ahead on a top-level field, index
  behind, then `sq check` names the item and the diverging key. Delete the rule and that test goes red
  on a clean report — drive it and report both directions.
- **The same assertion for a field with no bespoke predicate today** (`title` and `priority`). A rule
  that only generalises `status`/`parent` in name passes a test written against those two, so this is
  the criterion that proves the generalisation is real.
- **A pre-fix corpus is asserted clean**: an override declaring `full_name` and `mission`, never
  synced, reports nothing. This is the test that keeps the widening honest, and the one that would
  catch a rule built on "stored title vs resolved name" instead of on the two stored homes. Assert it
  again after `sq sync` — still clean.
- **Equivalence with the write seam, as one property rather than two lists**: for a given
  `(text, item)` pair, check reports precisely when `ensure_no_skew` raises. A test asserting the
  message text on both sides is not the same test and does not replace it.
- **The confirm round**: a candidate whose skew is resolved between the scan and the confirm — by a
  concurrent `sq repair` — is not reported.
- **Exit code unchanged** on a squad whose only issue is a value divergence, asserted directly on the
  process exit status rather than through a pipeline.
- The folded-in `status`/`parent` drift cases still report, with their direction naming intact — the
  two existing predicates' coverage must not be lost in the generalisation.
- No change to `PERMITTED_EXTRA_SKEW`, `_without_permitted_extra_skew`, `frontmatter_skew` itself, or
  the projection. Assert the guard's membership is unchanged.
- **No new index load and no new file read** — assert the counts, since the whole rule is built on
  data the scan already holds.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean **on this repository** and the result is reported. The rule was
  measured to fire zero times on a pre-fix corpus, so a hit here is a defect in the rule.

Implementation: _status_drift/_parent_drift folded into one _value_skew_issue(item, text, fdata) (squads/_services/_maintenance.py) that calls frontmatter_skew(text, item) verbatim and reports at warn, naming every diverging top-level key (direction-naming via the existing _drift_direction/_drift_message, now field-list-aware). The scan-side candidate detection and the one confirm pass both call frontmatter_skew against the same raw text _scan_for_check already holds in bodies[seq] — no new index load, no new file read; _confirm_cross_source now also threads that bodies map through. Equivalence with ensure_no_skew is asserted as one property. status/parent's own coverage and direction-naming are preserved (existing tests updated only where a field other than status/parent also genuinely diverged in the same write). No change to PERMITTED_EXTRA_SKEW/frontmatter_skew/the projection; a permanently-exempt extra key (role skills cache) still never reported, driven end to end.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T10:25:49Z] Olivia Lead:
  - One task, three subtasks. ST1 to ST2 is a real dependency, not just an ordering preference: ST1 produces the roster-scoped set of paths that should exist, and ST2 needs exactly that set to know what was absent before it wrote it (Artifact carries no created-versus-updated signal). Body forbids two separately-maintained notions of "the pointer that should be here".
  - ST1 grounded from source: the live predicate to reuse is item.status in spec.live_statuses(item.type) AND, for a SKILL item, orphaned_skill_item_type(slug, spec) is None. The second clause is easy to miss and missing it gives a squad whose workflow override dropped a type a permanent false positive no sync can clear — it is its own acceptance criterion. Layering is also constrained: backends read no index, so the roster-derived input arrives via BackendContext the way skill_paths and role_skills already do; SquadGlobalContext already holds index, so no new I/O.
  - Raised in ST1 rather than left to the dev: _backend_reconciled reports at error, which gates the exit code. Applying that to per-entry paths means an adopter who gitignores .claude/ goes from exit 0 to a failing sq check on a fresh clone, on a patch upgrade. The body requires the dev to implement, then report the level and that exit-code consequence explicitly, and forbids quietly choosing warn instead — see my handback, this one needs a ruling.
- [2026-08-22T11:08:09Z] Elias Python:
  - All three subtasks done; sq check clean on this repo throughout (gates below).
  - ST1 - shared predicate is_live_roster_entry(item, spec) (_interactions/__init__.py) extracted from _project_roster_item, reused verbatim by a new AgentBackend.managed_entry_paths(ctx) (implemented in both backends) and by backend_reconciled (live slugs from the already-loaded index, no new I/O). Level: warn for per-entry paths, error unchanged for the existing top-level managed_paths files (per op-pierre ruling on BUG-784).
  - ST1 fresh-clone exit code, measured: built a real two-backend squad, copied it into a second dir excluding .claude/agents, .claude/skills, .agents_md/roles, .agents_md/skills (the gitignored-clone shape), ran sq check there: 22 warn lines (one per live role/skill pointer, both backends), exit 0.
  - ST1 retire/reactivate, driven live via the real CLI: sq role activate qa -> check clean -> sq role qa status Archived (pointers withdrawn, both backends) -> check clean -> sq role qa status Active (pointers regenerated) -> check clean. Full cycle, not a snapshot. The orphaned-skill-type second clause has its own dedicated test.
  - ST1 tests: 13 new (test_backend_reconciled_per_entry_pointers.py) + 6 new backend conformance tests for managed_entry_paths (test_backend_lifecycle_contract.py).
  - ST2 - reporting only, write path untouched. sync() snapshots the same roster-scoped managed_entry_paths set before its roster loops run, then reports each path absent-before and present-after as: <path>: was missing - regenerated by this sync (backend: <name>).
  - ST2 channel decision: reused the existing sync() -> list[str] -> "warning:" channel, no new rendering. Reasoning: this is a fault report, same class as the existing drift-skip lines on that channel; a second output path would only fragment operator-facing text for no benefit.
  - ST2 clean-squad sync diff: captured a healthy squads sq sync output twice in a row and diffed - byte-identical ("synced managed files to this squads version", nothing else) both before and after this change.
  - ST2 retirement-is-never-a-fault, driven: retire -> sync -> reactivate -> sync, silent at every step (the role-status verb already materialises/withdraws immediately outside sync, so sync has nothing left to do). The case where sync itself must regenerate a reactivated pointer (an override-dropped-then-restored type) is exercised in test_dropped_type_skill_orphan_is_withdrawn_and_flagged.py, updated to expect the notice.
  - ST2 fresh-clone shape, measured on the same clone as ST1: first sq sync printed 22 "was missing - regenerated" lines (one per live role/skill pointer, both backends), exit 0; the very next sq sync on the now-healthy clone was silent. One line per file, proportionate, never chatty.
  - ST2 tests: 10 new (test_sync_reports_regenerated_per_entry_pointers.py).
  - ST3 - status/parent drift folded into one _value_skew_issue(item, text, fdata), built on frontmatter_skew(text, item) verbatim - no new comparison invented, inherits the exemptions and round-trip normalisation for free. Level warn, exit code unchanged (verified directly on the process exit status via invoke(["check"]), not through a pipe).
  - ST3 no new I/O: the scan-side candidate reads the raw text _scan_for_check already collects in bodies[seq] (threaded into _confirm_cross_source, which gained a bodies parameter); the confirm round still does its one existing re-read, nothing more - asserted with an index-load counter and a read-path-uniqueness check.
  - ST3 equivalence property asserted directly: for a table of (text, item) pairs, check reports a divergence iff ensure_no_skew raises - not merely a similar message.
  - ST3 falsification driven: title and priority (a field with no bespoke predicate before) both reported; folded status/parent predicates still report with direction naming intact; a pre-fix corpus (an override declaring full_name/mission, never synced) reports nothing before and after sq sync; a permanently-exempt extra.skills divergence (link_role resync) is still never reported; a skew resolved by a racing sq repair between scan and confirm is not reported.
  - ST3 side effects: two pre-existing drift tests needed a message-format update (a multi-field divergence now joins the field list, e.g. "status, updated_at", where the old single-field predicate only ever said "status"); one migration test needed an await svc.repair() added before its final check(), matching that migrations own documented step 4 - its fixture had a genuine, pre-existing skew on a sub-entity title the old two-field rule never saw.
  - ST3 tests: 9 new (test_check_reports_frontmatter_index_value_skew.py).
  - CHANGELOG text for the unreleased section (I did not edit CHANGELOG.md myself, per the boundary): sq check now also flags a missing per-entry backend pointer (one role Claude Code agent file, one skill pointer, an AGENTS.md staging file, etc) for a live role or skill, at warn level, since a gitignored .claude or .agents_md is a supported adopter choice; sq sync now reports each per-entry backend pointer it found missing and had to regenerate, naming the file and the backend, and a healthy syncs output is unchanged; sq check now flags a frontmatter/index value divergence on any field, not only status or parent, at warn level.
  - Gates: pyright 0 errors/0 warnings; ruff check all checks passed; ruff format --check all files already formatted; pytest tests/meta 181 passed; targeted validators/check/sync/backend + new-test run across 32 files: 450 passed; sq check on this repo clean (exit 0) throughout; sq repair a stable no-op (one pre-existing gap unrelated to this change - TASK-785 itself not yet folded into the committed index snapshot - picked up once, a second run made no further change).
- [2026-08-22T12:05:57Z] Elias Python:
  - F1/F2 from REV-786 fixed (commit 74a847e), unblocking the 0.13.1 release.
  - F1: role_base_from_item/dev_base_from_item and RoleDef.from_extra now tolerate a stored blank/whitespace full_name (self-heal to catalog/pool name on next sq sync) instead of raising -- the input-side refusal on sq dev add --name/sq role activate --name is untouched, all four BUG-778 cases still refuse. See REV-786 F1 comment for the driven before/after.
  - F2: managed_entry_paths is no longer @abstractmethod (concrete default: return []); AgentBackend is back to exactly the seven documented methods, both bundled backends unchanged. See REV-786 F2 comment for the instantiation proof.
  - New tests: tests/unit/test_role_resolver_tolerates_a_stored_blank_full_name.py, tests/integration/test_stored_blank_role_name_self_heals_on_sync.py, tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py.
  - Gates clean: pyright, ruff check, ruff format --check, tests/meta, and the full role/sync/check/backend test set (868 tests). sq check clean on this repo, sq repair a stable no-op.
  - CHANGELOG text (for tech lead to apply, unreleased section): Fixed -- "A role or developer name made only of spaces, if already stored from an earlier release, no longer breaks sq sync, sq role show, or sq role regen; it is repaired automatically on the next sync." Fixed -- "A custom agent backend written to the documented seven-method interface works again; an eighth method added in this release is now optional."
- [2026-08-22T14:13:29Z] Elias Python:
  - REV-786 F6 (agents_md staging files) fixed on top of this task: agents_md no longer stages .agents_md/roles|skills files at all -- per op-pierre's ruling, not just a reworded report.
  - generate_role_entry/generate_skill_entry write nothing; managed_entry_paths override dropped for agents_md (falls to the ABC default []), so sq check's per-entry warn and sq sync's regeneration report no longer name it. claude_code's per-entry pointer reporting from this task is untouched.
  - Upgraded squads: materialise/withdraw now delete-if-exists any legacy .agents_md file, so a plain sq sync cleans up leftovers for any role/skill still in the roster; candidate_orphans still flags a leftover from a fully-removed item on sq adopt.
  - AGENTS.md verified byte-identical before/after (fresh init+sync, and a role rename). Commit a3fa3a9 on release/0.14.
<!-- sq:discussion:end -->
