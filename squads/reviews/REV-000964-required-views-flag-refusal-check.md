---
id: REV-964
sequence_id: 964
type: review
title: 'Required views: flag, refusal, check'
status: Approved
author: reviewer
refs:
- TASK-942:addresses
- FEAT-948
subentities:
- local_id: F1
  title: Milestone body replace always refused; TODO scaffold unfillable
  status: Fixed
  severity: high
- local_id: F2
  title: 'Per-type skill legacy bodies: premise false, every pre-0.14 squad'
  status: Fixed
  severity: high
- local_id: F3
  title: Reclaim skipped by the migration chain's own mid-chain skew
  status: Fixed
  severity: medium
- local_id: F4
  title: Role-authoring remedy not moved to sq role show (ST9 unmet)
  status: Fixed
  severity: medium
- local_id: F5
  title: Repair skip corridor is dead code; delete it
  status: Fixed
  severity: medium
- local_id: F6
  title: Skip-report test file no longer tests its subject
  status: Fixed
  severity: low
- local_id: F7
  title: Append refusal rationale also describes the admitted milestone case
  status: Fixed
  severity: medium
- local_id: F8
  title: Refusal, hint and warning messages name wrong or no-op remedies
  status: Fixed
  severity: medium
- local_id: F9
  title: Docs overclaim append and the shadowed-warning remedy
  status: Fixed
  severity: low
- local_id: F10
  title: Build-process narration in standing docstrings and tests
  status: Fixed
  severity: low
- local_id: F11
  title: Single derivation holds; slug input and side lists diverge
  status: Fixed
  severity: low
- local_id: F12
  title: Narrowing shape table (ST10) not written; only role case
  status: Fixed
  severity: low
created_at: '2026-09-24T19:53:36Z'
updated_at: '2026-09-29T00:38:19Z'
---
<!-- sq:body -->
## Scope

TASK-942, the required-view flag. The whole uncommitted working tree on release/0.15 against HEAD: the `ViewSpec.required` key; the `required_view_names` / `roster_body_view_name` / `view_placement_invocation` helpers; the replace and append guards (`_reject_unwritable_body`, shared by `set_body` and the bulk importer); the `view rm` narrowing; the tier-1 `sq check` finding; the six bundled views declared required; strict convergence; the 0.14→0.15 legacy-body reclaim step; the regenerated v0_15 fixture; docs/workflow.md, docs/overrides.md and the CHANGELOG entry.

## Method

- Each refusal, hint and message was driven on a scratch squad.
- A real squad initialised with released v0.13.1 (`uvx --from git+file://…@v0.13.1`) was migrated with this tree, then synced, checked, and taken through the documented remedy.
- Copies of the v0_5, v0_8, v0_11 and v0_14 fixtures were migrated.
- The v0_15 fixture was regenerated independently from v0_14 and diffed against the committed one.
- Every guard and convergence call site was traced.

## Checked, fine

- **v0_15 fixture:** regenerating it from v0_14 with `run_pending_migrations` (clock pinned) is byte-identical to the committed fixture, apart from an uncommitted `.reflog.jsonl`. v0_1–v0_14 are byte-unchanged against HEAD.
- **Single derivation in the write path:** the write path, the importer, `view rm` and the check all go through one host-set helper. Residuals are in the single-derivation finding.
- **`view_placement_invocation`** produces real, runnable forms: `sq role|skill <slug> view add|rm`, `sq <type> <n> view add|rm`.
- **Migration step:** it is idempotent (a re-run reports 0), and scoped to roles and permanently-system skills. Empty, already-tagged and custom-skill bodies are left alone.
- **Gates:** tests/meta 303 passed; the targeted changed and new tests 192 passed, 6 skipped; pyright 0 errors; ruff check and format clean; `sq check` clean.
- **Hygiene:** no ticket IDs in src or in test filenames/docstrings; no new bare type aliases; layering respected (`_views` stays service-free).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 964 add-finding "…" --severity medium`; track with `sq review 964 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Milestone body replace always refused; TODO scaffold unfillable

<!-- sq:finding:F1:body -->
**Measured** on a fresh scratch squad: `sq create milestone "M one"` gives a body that holds the creation template's `## Objective` / `## Scope boundary` scaffold, both `_TODO:` placeholders, followed by the roll-up tag. Then:

- `sq milestone 21 body -m "hello"` is refused (exit 1), and `--force` is refused too.
- `--append` works, but it writes *after* the roll-up tag. The TODO scaffold above the tag can never be replaced.

So every milestone created from now on keeps an unfillable TODO scaffold, unless someone drops the view or overrides the template. The generated `sq-milestone` skill still tells agents "Set this item's body with `sq milestone <n> body -m`" (checked with `sq skill sq-milestone show` on this repo). Following that instruction now always fails.

**The design rests on a false premise.** The task says "there is no compliant replace to fall back to", because `reject_markers` keeps a tag out of the prose. But the tool does not need the author to type the tag. It can put the tag back itself after writing the prose, the same way `view add` and the 0.14→0.15 migration already place it. A replace that keeps the tag satisfies the invariant ("no write may produce a body missing the tag"), keeps the "no flag lifts it" property, and makes the milestone body writable again.

**Recommendation (needs op-pierre's ruling):** make replace on a required host keep the tag (re-insert every required tag the host carries after the new prose) instead of refusing it. At minimum, do not ship `milestone_rollup` as `required = true` until milestone prose can be edited. Both the CHANGELOG and docs/workflow.md present the milestone refusal as intended behaviour.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-28T18:32:30Z] Paul Reviewer:
  - Fixed, driven on a fresh scratch squad: `sq milestone 21 body -m "hello"` over the untouched scaffold exits 0 with no `--force`, `--append` lands above the roll-up tag, and a later replace is refused only by the ordinary authored-body guard. Matches op-pierre's ruling (tags re-placed, never typed). Code: `_services/_items.py::_body_mutate` through `_views.place_view_tags` (1e317941, guard edge-blank fix 798ae789).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Per-type skill legacy bodies: premise false, every pre-0.14 squad

<!-- sq:finding:F2:body -->
**The premise is false.** `_v0_14_to_v0_15`'s module docstring and `_LEGACY_ROSTER_VIEW_NAMES` exclude per-item-type skills on the grounds that "its definition has never been stored at any past release, so there is no legacy shape to reclaim there". That is not what the released code did: `v0.13.1:src/squads/_backends/_claude_code/_backend.py::_write_managed_skill` wrote the rendered body into the `sq:body` of **every** managed skill, `sq-<type>` included. `v0.14.0`'s sweep then deliberately left skill bodies untouched ("a stored system-skill body is never read"). The v0_14 fixture's `sq-contract` body is exactly that rendering.

**Measured with a real squad:** `uvx --from git+file://…@v0.13.1 sq init`, then this tree's `sq migrate up`, `sq sync` and `sq check`:
- 7 errors: `missing required view tag … item_skill` on sq-bug, sq-decision, sq-epic, sq-feature, sq-guide, sq-review and sq-task;
- 7 warnings: `item_skill_shadowed`.

So this is **every squad initialised before 0.14, on every per-type skill**, not a corner case.

**The documented remedy makes it worse.** `sq skill sq-bug view add item_skill` clears the error. But `sq skill sq-bug show` then renders the definition **twice**: the stale 0.13 text (line 9), then the live view (line 78). The warning stays for good, and it now claims the guidance "has nowhere to render", which is false because the tag renders. Its advice ("rename this skill or drop the type") is wrong for a bundled type. The stale text cannot be removed: replace is refused (required host), append is refused (roster classification), and repair leaves it alone (strict). The only way out is to drop `item_skill` from `[selected]`, replace the body, then restore the view. No doc describes that.

op-pierre's ruling ("keep ST12's narrow scope … per-item-type skill with legacy text is left for sq check") was given against the code's stated premise that such bodies are rare. **Recommendation:** raise this again with the corrected premise. The same release-scoped argument that licenses the role and system-skill reclaim applies to a `sq-<type>` skill whose slug named a bundled type at 0.13. Also: the tests/fixtures/corpus README's step 2 ("verify the copy passes sq check — it should") no longer holds for v0_15, which fails check with 2 errors.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-28T18:32:34Z] Paul Reviewer:
  - Fixed, driven: a real squad initialised with released v0.13.1 (`uvx --from git+file://…@v0.13.1`), migrated, synced: `sq check` clean, `sq-bug` body is tag-only, `sq skill sq-bug show` renders the guidance once. Matches op-pierre's ruling: the reclaim set is `roster_body_view_name` itself (`_migrations/_v0_14_to_v0_15.py::_reclaim_legacy_roster_bodies`, 1e317941/4d9837fe). A new consequence of the widened reclaim (authored prose on a later-declared type's skill is wiped) is filed on the follow-up review.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Reclaim skipped by the migration chain's own mid-chain skew

<!-- sq:finding:F3:body -->
`_reclaim_legacy_roster_bodies` skips any item for which `ensure_no_skew` raises, comparing against the **index as it stands mid-chain**. Earlier runners in the same `sq migrate up` rewrite frontmatter without rebuilding the index; the rebuild is the trailing repair. So in any corpus coming from an early schema, the skew check fires on the chain's own intermediate state, not on real damage.

**Measured:** a copy of `tests/fixtures/corpus/v0_5`, then `sq migrate up`, gives `skipped 3 item(s) … UNRESOLVED-1, UNRESOLVED-7, UNRESOLVED-8`. That is every role and system skill in the corpus. `sq check` then reports all three as missing their required tag. v0_8 migrates cleanly. The dev's handback names v0_1–v0_7 as affected.

Three problems follow:
- For an adopter coming from those schemas, the reclaim is a no-op: every legacy role/system-skill body survives, and each one becomes a check error.
- The skip list prints `UNRESOLVED-<n>` sentinels. An operator cannot act on those names. The tests handle this by matching sequence ids instead of fixing the output.
- The printed remedy ("a skewed one needs `sq repair`") does not work. Repair rebuilds the index, but the reclaim never runs again, and the standing sweep is now strict. The only remaining route is `view add`, which renders the legacy text and the live definition together (see the per-type skill finding).

**Recommendation:** run the reclaim against a post-rebuild state (for example, after the trailing repair, still within the migration's licence), or check skew against the on-disk file alone. Print resolvable ids. Add a corpus test asserting that v0_1–v0_7 roles are reclaimed, not just tolerated as skipped.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-09-28T18:32:37Z] Paul Reviewer:
  - Fixed, driven: copies of v0_1, v0_5, v0_7, v0_11 and v0_14 migrate with no skip rows and no seeded-view errors; skip ids print resolvable (`ROLE-1`). The step reads each file's own frontmatter at write time (`_v0_14_to_v0_15.py::_write_body_change`, 4d9837fe).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Role-authoring remedy not moved to sq role show (ST9 unmet)

<!-- sq:finding:F4:body -->
ST9's constraint 2 and FEAT-948's acceptance ("`sq role <slug> show` still surfaces the role-authoring remedy once the generalised refusal message stops carrying it") require the sentence "declare it in `.overrides/roles.toml`, or `.overrides/roles/<slug>.toml` for a project-defined role" to **move** to the role surface.

It did not move. `git diff HEAD --stat -- src/squads/_cli` is empty. `_cli/_role.py`'s empty-body hints (lines ~405–445) name `sq sync`, `sq repair` and `view add|rm`, and never `roles.toml`. No changed or new test mentions `roles.toml`. The old refusal text was deleted from `_items.py`, so the remedy now appears nowhere.

ST9 is marked Done. **Recommendation:** add the pointer to the role show hint, as specified, with a CLI test. While there, check the skill-side hint for parity, as the task asks.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-28T18:32:42Z] Paul Reviewer:
  - Fixed, driven: an empty-bodied role's `sq role qa show` hint names `.overrides/roles.toml` / `.overrides/roles/<slug>.toml` (`_cli/_role.py::_role_empty_body_hint`), and the §8 refusal carries the same surface on the write path (`_services/_items.py::_reject_unwritable_body`).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Repair skip corridor is dead code; delete it

<!-- sq:finding:F5:body -->
Verified by tracing the code, as the dev claims. `_repair_body_tag` returns only `roster_body_view_name(...)`, whose possible values are `role_definition`, the three `SYSTEM_SKILL_VIEW_NAMES` values and `item_skill`. `_strict_body_convergence` returns True for exactly that set. So at both call sites (`_strip_retired_regions`, `_backfill_roster_body_tags`) `strict_empty` is always True. `_converge_body_tag`'s non-strict branch and its `SquadsError` raise cannot be reached from production, so nothing ever fills `skip_message` → `pending.skipped` → `RepairResult.skipped`, or sync's backfill-skipped list. That leaves dead code: the stamp-withholding on a backfill skip, and the `skipped` rows and exit-1 paths in `_cli/_migrate.py:102-120` and `_cli/_main.py:460-466, 769-775`. `migrate up`'s *migration-level* `MigrationRun.skipped` is a different, live channel, and is unaffected.

**False docstring:** `_converge_body_tag` says the non-strict licence "still exists, but only the one-time pre-0.14 migration step calls it now". It does not. `_reclaim_legacy_roster_bodies` does its own `find_markers` + `replace_section` inline and never calls `_converge_body_tag`. Nothing calls the non-strict branch.

**The tests keep dead code alive by bringing back what the task forbids.** Five tests (`test_repair_corridor_message_and_exit_parity.py` ×4, `test_migrate_up_reports_repair_skips.py` ×1) monkeypatch `_strict_body_convergence` to `False`. That restores the wide licence the task's fences say must not come back, only to feed a corridor production cannot reach. What they prove is that dead code still formats a message.

**Recommendation: delete.** Remove the `strict_empty` parameter (always strict), the non-strict branch and its raise, `_strict_body_convergence`, `RepairResult.skipped` and its plumbing, sync's backfill skip list and the stamp withholding it drives, the CLI rows, and the monkeypatched tests. Keep `unreadable`. If a future caller needs a non-strict convergence, it should be written against its own licence, as the migration's own inline code already is. This can be its own fix-task; it is not a correctness defect in the shipped behaviour.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-28T18:32:48Z] Paul Reviewer:
  - Fixed, read and grep-checked: `strict_empty`, `_strict_body_convergence`, `RepairResult.skipped`, `backfill_skipped` and the CLI skip rows are gone from src; the monkeypatched tests were deleted (4d9837fe). Matches op-pierre's ruling. A stale docstring that still cites the deleted symbol is listed under F10.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Skip-report test file no longer tests its subject

<!-- sq:finding:F6:body -->
`test_migrate_up_exits_non_zero_bare_on_an_unreadable_file` now tests what its **function name** says: a real subprocess, a real unreadable file, bare exit 1. But it no longer tests what the **module** is about ("migrate up must report the skipped channel … and exit non-zero on that same condition"). Nothing tests a real `skipped` exit bare, because nothing can trigger one (see the dead-corridor finding). The unreadable exit through `migrate up` is already covered in-process by `test_repair_corridor_message_and_exit_parity.py::test_migrate_up_unreadable_row`. This test only adds the bare-subprocess angle.

A second problem: `test_migrate_up_prints_the_skip_and_exits_non_zero` asserts `"SKILL-8" in result.output`. With the same seed and **no** monkeypatch, I ran `sq migrate up` on a copy of v0_11. SKILL-8 is already printed, by the 0.14→0.15 migration's own skip list, because `_reclaim_legacy_roster_bodies` skips marker-shaped content, and the exit code is 0. So that assertion no longer tells the two channels apart. Only the exit-code and "this region was left untouched" assertions still do.

**Recommendation:** once the corridor is deleted, rename the module around its surviving subject (migrate up exit parity for `unreadable`, plus the clean-run controls), or fold it into the exit-parity module. Delete the skip tests with the corridor.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-28T18:32:53Z] Paul Reviewer:
  - Fixed: the module is now `tests/cli/test_migrate_up_bare_subprocess_exit_parity.py`, built around the surviving `unreadable` exit parity, and the `SKILL-8` assertion is gone (4d9837fe).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Append refusal rationale also describes the admitted milestone case

<!-- sq:finding:F7:body -->
Design question, for a ruling. The task body says "whether a converged roster body should ever admit authored prose beside its tag … is not opened here". The current justification in `_reject_unwritable_body` is: "the tag is the document's exact rendering slot, so appended prose would sit spliced directly onto whatever renders in its place, with no marker separating the tool's content from the author's."

**That argument proves too much.** A milestone body is prose plus `sq:view:milestone_rollup`, and `--append` on a milestone is admitted and places prose right after the rendered roll-up (measured: the body ends with the tag, a blank line, then "appended prose"). The same splice is allowed there and refused on a role or skill. So the rationale does not separate the refused set from the admitted one. The original reason (repair erases appended prose) was measured false, and the dev correctly removed it. What is left is a rule without a working reason.

**What the refusal costs:** combined with the unforceable replace refusal, every role, system skill and per-item-type skill body becomes fully immutable while its view is declared. That is what strands the legacy text in the per-type skill finding.

**A reason that would hold:** a role's or system skill's content has one authoring surface. For a role that is `.overrides/roles.toml` / `.overrides/roles/<slug>.toml`; for a skill it is the playbook overrides. Prose appended to the body would be a second, undeclared source of the definition that agents read. If that is the ruling, key the message on it and name the real authoring surface. That also covers the lost role remedy. If it is not the ruling, admit append (it keeps the tag, so the required invariant holds) and drop the separate rule.

Either way the current text should not ship: its reason also describes a case the code permits.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-09-28T18:32:57Z] Paul Reviewer:
  - Fixed per op-pierre's option A ruling (ADR-880 seventh amendment §8): replace and append are both refused on a roster-classified body, and the message names the real authoring surface instead of the spliced-render rationale. Driven for a role (via `sq import`), `squads`, `greeting`, `sq-memory` and `sq-bug`, with and without `--force`.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Refusal, hint and warning messages name wrong or no-op remedies

<!-- sq:finding:F8:body -->
The messages this change added or made stale, each measured on a scratch squad or read against the code:

1. **`view rm` refusal on a role or skill**: "drop the view from `[selected]`, or override the creation template that seeds it, to lift the requirement". For a roster host the second escape is false. `required_view_names` asks `roster_body_view_name`, which never reads a template, and docs/workflow.md itself says "this route does not apply to them". The message also omits `required = false`, the most direct escape and the first one the docs list. Measured on `sq role manager view rm role_definition` and `sq skill sq-bug view rm item_skill`.
2. **Replace refusal**: "…Use `--append`, or restore it with `sq milestone 21 view add milestone_rollup`." It fires on every replace, including when the tag is present. Running the named command then prints "already present, unchanged", and the replace stays refused. "Restore" is not a way to unblock this write.
3. **Migration skip text** (`_cli/_migrate.py:62-72`): written for the milestone step. It gives no remedy for the reclaim step's new skip reason (marker-shaped content). It names a generic `sq <type> <n> view add <name>` where a roster host needs `sq role|skill <slug> …`. It lists `UNRESOLVED-<n>` ids (see the mid-chain skew finding). Its "a skewed one needs `sq repair`" does not lead to a reclaim.
4. **Role and skill empty-body hints** (`_cli/_role.py`, `_cli/_skill.py`): still say "Try `sq repair`, which converges an already-tagged or plain-legacy body regardless of drift". Under the strict licence repair no longer converges a plain-legacy body.
5. **`item_skill_shadowed`**: when the tag is present beside legacy text, it still says the guidance "has nowhere to render", which is false because the view renders, and advises "rename this skill or drop the type", which is wrong for a bundled type.

**Recommendation:** route every remedy through the escapes that actually apply to the host kind (`required = false`, a `[selected]` drop, a template override for non-roster types only), and update the hints and the validator text for the strict licence.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-09-28T18:33:02Z] Paul Reviewer:
  - Fixed, item by item: (1) `view rm` is retired, so its message is gone; (2) the replace refusal is gone; (3) migrate skip text drops the repair remedy, prints resolvable ids and names the `sq role|skill <slug>` form (`_cli/_migrate.py`); (4) the role and skill hints no longer name `sq repair … plain-legacy`; (5) `item_skill_shadowed` has a tag-present message and a single remedy (45c3b2a2). Problems in the new messages are filed on the follow-up review.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Docs overclaim append and the shadowed-warning remedy

<!-- sq:finding:F9:body -->
Docs and prose that overclaim:

- **docs/overrides.md** ("Making a view required": "`--append` is untouched, since it keeps the whole existing region") and **docs/workflow.md** (field reference: "`--append` is unaffected"). Append is refused on every role, permanently-system skill and per-item-type skill, which are five of the six bundled views' hosts. Neither page says so; workflow.md only says "On a milestone, `body --append` still works". The CHANGELOG gets this right ("`--append` is unaffected on an ordinary item").
- **docs/workflow.md** upgrade subsection: "`sq check` also warns that the skill 'carries authored content of its own'; the warning names what to do about it". The warning's advice (rename the skill or drop the type) is wrong for a bundled `sq-<type>` skill, and after `view add` the warning's own claim is false (see the per-type skill finding). As written, the guide sends the reader to a dead end.
- **docs/workflow.md**: "`sq migrate up` places the tag for you on every milestone". It skips skewed, region-less and tag-outside-region milestones, and a later paragraph says so, so this is minor.
- **`ItemsMixin.set_body` docstring** still says append is refused "because the repair sweep converges that region and would silently discard appended prose". The dev measured that false and corrected `_reject_unwritable_body`'s docstring, but not this sibling. The old sentence survives one method down.
- **CHANGELOG**: "A role's … body … now follows the declared flag: set `required = false` … and an authored body is accepted". A role has no `body` verb on the CLI, so the only route is `sq import`. Consider saying so.

No ticket IDs or process narration in docs/ or the CHANGELOG entry: checked, fine.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-09-28T18:33:07Z] Paul Reviewer:
  - Fixed, read against docs/overrides.md, docs/workflow.md and CHANGELOG.md in the range: the append overclaims and the required-flag prose are gone, the upgrade subsection lists the migration's real exceptions, the `set_body` docstring no longer claims repair erases appended prose, and the CHANGELOG says a role takes a `sq import` body event (19631075). One new sample-output mismatch is filed on the follow-up review.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Build-process narration in standing docstrings and tests

<!-- sq:finding:F10:body -->
Read the added docstrings and comments as someone who has never seen the diff. Sentences that only make sense against the diff:

- `_services/_items.py::_reject_unwritable_body`: "This is the narrowing the `ROSTER_ROLE`/system-skill retirement introduces, not a like-for-like substitution … the branches it replaces asked nothing about the spec … are now admitted to a write those branches refused". The branches exist only in the diff.
- `_services/_maintenance.py::_converge_body_tag`: "**The standing sweep now passes `strict_empty=True` …** since the required-view write refusal … narrows what it refuses"; `_strict_body_convergence`: "every roster-body view now, not only …"; the `_strip_retired_regions` comment "Every roster-body view converges under the narrower, strict_empty licence now".
- Tests: `test_migrate_up_reports_repair_skips.py` ("the raise that used to feed", "reach any more", "is repointed at the sibling"), `test_repair_corridor_message_and_exit_parity.py`, `test_sync_withholds_the_stamp_after_a_body_tag_skip.py` ("no longer triggers a skip"), and `test_migration_corpus.py` ("before this cycle's real 0.14->0.15 migration made that fixture").

Migration-module prose ("Before this release, …") passes, because a migration describes a release delta the reader can observe. Standing service code does not. Keep the durable fact in the present tense (for example "every roster body converges under strict_empty; the one non-strict licence belongs to a migration") and cut the delta. Several of these go away if the dead corridor is deleted.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-09-28T18:33:14Z] Paul Reviewer:
  - Still open. The instances this finding named in service code are rewritten, but a named test instance survives, and new narration landed in standing code:
    - `tests/integration/test_migration_corpus.py:534` still says "before this cycle's real 0.14->0.15 migration made that fixture"; `:587` cites the deleted `_strict_body_convergence`, and `:594`/`:600` still speak of a "required-view gap".
    - `src/squads/_views.py`: `place_view_tags` says "**Spacing** (op-pierre's ruling)"; `ConflictingViewStateError` says "(none does, today)"; `expand_view_tags` cites "the second amendment's" errors.
    - `src/squads/_services/_views.py::disable_view` says "the recovery role the second amendment gave ``view rm`` (retired outright by this amendment…)".
    - `src/squads/_migrations/_v0_14_to_v0_15.py` says "(op-pierre's ruling)" twice, "(reversing an earlier narrow scope)" and "as an earlier version of this runner did". These describe how the code was built, not a release delta.
    - `src/squads/_services/_validators.py` module docstring still names `_required_view_issues` and "a ``required = true`` view". ST7 asked for this paragraph to be updated.
- [2026-09-28T22:11:52Z] Elias Python:
  - Fixed: removed every 'op-pierre's ruling'/'this amendment'/'(none does, today)' citation, the migration docstring's redundant ruling-parenthetical, and the two stale test_migration_corpus.py references ('this cycle', the deleted _strict_body_convergence). Reworded 5 further build-process-narration sentences found in a full stranger-test read of every added line across the whole task range ('the reviewer's...', 'this task...', 'the dev's handback' style phrasing) into durable, present-tense statements. Grepped each old fragment across the tree after rewriting; none remain.
- [2026-09-28T22:51:57Z] Paul Reviewer:
  - Re-verified against HEAD, still Open. Fixed: `test_migration_corpus.py` no longer says "this cycle" or cites `_strict_body_convergence`; the `_validators.py` tier-1 paragraph now describes `_seeded_view_issues`; "op-pierre's ruling" and "this amendment" are gone from src. Still present:
    - `src/squads/_migrations/_v0_14_to_v0_15.py:43` "(reversing an earlier narrow scope)" and `:126` "Driven: skipping here…". The first was named in this finding's last comment.
    - `tests/integration/test_migration_corpus.py:136,158,592` still say "required-view gap", the retired concept.
    - New narration from the fix commits: `_views.py::roster_slug` and `_maintenance.py::_check_slug` ("Before this existed, the write path read…"), `_converge_body_tag` ("used to reach … `KeyError`", "now tries"), `_absent_body_region_issues` ("the one that used to crash", "now try").
    - The adopter-facing MANUAL (`sq migrate chlog v0.14.0..v0.15.0`) says "`view disable <name>` alone is **not** this remedy any more". No release ever shipped that remedy, so the sentence narrates the build to the adopter.
- [2026-09-28T23:45:50Z] Elias Python:
  - Fixed the four named items and re-swept the whole diff (git diff 1e317941~1 -- src tests,
    including this batch and the F1/F15 fix commit) with the stranger test:
    
    - migration module: dropped "(reversing an earlier narrow scope)" and the "Driven:" aside in
      favor of plain present-tense statements of what the reclaim does and why.
    - tests/integration/test_migration_corpus.py: the retired "required-view gap" phrase is gone
      from all four prose sites (lines 136/158/592/598-599 in the pre-fix numbering), replaced with
      "seeded-view gap" -- the current vocabulary the check message itself uses. Left the
      `_expected_required_view_gap_files` helper's own name untouched (a symbol rename is a
      different, larger surface than this narration fix).
    - docstrings added by the fix commits: rewrote `_views.py::roster_slug`,
      `_maintenance.py::_check_slug`/`_converge_body_tag`/`_absent_body_region_issues` to state the
      current mechanism directly, dropping every "before this existed"/"used to"/"now tries"
      comparison against a prior version of the same code.
    - the adopter-facing MANUAL: "`view disable` alone is not this remedy any more" -> "does not
      achieve this" (no release ever shipped the old remedy, so there is nothing to compare against).
    
    Full re-sweep also caught two more instances the keyword list didn't name explicitly: the
    _validators.py module docstring's "despite an earlier version of this sentence" and "not only the
    first it originally asked about" (both citing the docstring's/name's own prior draft), and my own
    "...exactly the false positive reopening this finding" line from the F1 fix commit (review-status
    narration, not a code fact) -- all rewritten to state the durable fact plainly.
    
    Left untouched, on purpose: the "Regression: X used to say/print Y" test-docstring convention
    (11 instances) -- these describe a past bug a regression test pins against, comprehensible with
    zero diff context, and the standing review's own two full re-review passes never flagged this
    established idiom; and every "no longer declares"/"originally there"/"before this call" instance
    that turned out to be domain vocabulary (a view's spec declaration, a runtime input's own prior
    state) rather than build-process narration, checked one by one against blame to confirm each was
    actually inside this task's diff range before judging it.
    
    Grepped every rewritten fragment across src/ and tests/ afterward: all zero, validated against a
    known positive first (a "used to print" hit inside a kept Regression-style test docstring) to
    confirm the grep mechanism itself works.
- [2026-09-29T00:04:49Z] Paul Reviewer:
  - Re-verified against HEAD, still Open for two in-range sentences: `src/squads/_migrations/_v0_14_to_v0_15.py:82` "(as an earlier version of this runner did, via ``ensure_no_skew``)", named in this finding's earlier comment, and `src/squads/_services/_views.py:67` "is not refused outright any more" (added in 61a95690). Everything else named before is gone. The `_expected_required_view_gap_files` helper name in `tests/integration/test_migration_corpus.py` still uses the retired "required" vocabulary. That's minor, but worth renaming in the same pass.
- [2026-09-29T00:18:39Z] Elias Python:
  - Fixed the three named items: dropped 'as an earlier version of this runner did' from the migration module (restated the mid-chain-skew bug as a general fact, no reference to a prior code version); '_services/_views.py's 'not refused outright any more' -> states the current refusal condition directly; renamed tests/integration/test_migration_corpus.py's _expected_required_view_gap_files to _expected_seeded_view_gap_files (9 sites) to match the current 'seeded-view gap' vocabulary. Re-swept the pre-filter (any more|earlier version|used to|no longer|now ) across the full 1e317941~1..HEAD added-lines set (61 hits after excluding a content_store.json data blob) and read each one: found and fixed one more standing-code instance outside the named three (test_sync_always_stamps_the_config.py's module docstring, 'stamp-withholding channel any more' -> 'stamp-withholding channel'); every other hit was either domain vocabulary (a view no longer declared, a runtime state within one test's own scenario), migration-module release-delta prose (the standing carve-out), or the accepted 'Regression: X used to Y' test-docstring convention. Grepped all four rewritten fragments afterward: zero.
- [2026-09-29T00:25:50Z] Paul Reviewer:
  - Re-verified at HEAD 611f6988. The three named sentences are gone: the migration's "earlier version of this runner", `_services/_views.py`'s "not refused outright any more", and the `_expected_required_view_gap_files` name. Still Open for two test docstrings added in this range (cddec435) that narrate the fix rather than describe the behaviour:
    - `tests/service/test_absent_body_region_recovery.py:1-6`: "…hand-deleted entirely used to crash `sq repair`, `sq sync` and `sq migrate up` … the corpus-wide sweeps no longer crash, `sq check` now reports…"
    - `tests/unit/test_repair_body_tag_convergence_pure_function.py:100-104`: "The regression this finding exists to hold … used to reach `sections.replace_section`'s own `KeyError` … Now the pair is reinstated…" This one also points at a review finding.
    
    Present-tense rewrites would close this: "A roster file whose `sq:body` pair is missing does not crash repair/sync/migrate; the pair is reinstated around a safe tag run, and `sq check` reports the absent region."
- [2026-09-29T00:35:27Z] Elias Python:
  - Fixed the two named docstrings (test_absent_body_region_recovery.py's module docstring,
    test_repair_body_tag_convergence_pure_function.py's), then read every test module docstring and
    test docstring added or changed in 1e317941~1..HEAD for the same history-telling shape --
    including the "Regression: X used to Y" convention itself this time, per the reviewer's reading.
    
    Found and rewrote 19 in-scope files (~28 sites): every remaining "Regression:"-prefixed docstring
    in the diff (17 of them) lost that label and its used-to/now framing, restated as a plain
    present-tense statement of the behaviour under test; two more standing docstrings ("_write_managed
    _skill now routes...", "views.roster_slug is now the one derivation...") and a handful of
    used-to-phrased comments/helper docstrings were rewritten the same way. Left untouched: one
    pre-existing "Regression:" docstring (test_show_command_renders_body_and_subentities.py:148) that
    predates this task's range, and several "no longer"/"now" instances that describe a test's own
    just-applied scenario state (e.g. "declare: 'widget' now names a real type" two lines after the
    override that does it) or plain domain vocabulary (a view the spec no longer declares), neither of
    which narrates the fix's own history.
    
    Docstring-only changes; ran all 19 touched test files (1125 tests) plus ruff -- all green, since
    nothing behavioural moved.
- [2026-09-29T00:38:13Z] Paul Reviewer:
  - Verified at HEAD bafd1bed. Both named docstrings (`test_absent_body_region_recovery.py:1-8`, `test_repair_body_tag_convergence_pure_function.py:100-104`) now state behaviour in the present tense, and the 19-file sweep reads clean. A re-grep of the range for used to / no longer / any more / now / earlier version / finding references finds only spec-state wording ("a view the spec no longer declares"), the migration's release-delta prose, and "this finding" meaning the check finding itself.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Single derivation holds; slug input and side lists diverge

<!-- sq:finding:F11:body -->
**Checked, mostly fine.** The replace refusal (`_body_mutate` and the importer's `_sim_body`, both via `_reject_unwritable_body`), `view rm` (`remove_view`), the tier-1 check (`_required_view_issues`) and the repair classification (`_repair_body_tag`) all go through `views.required_view_names` / `views.roster_body_view_name`. No `is_system_skill` or `ROSTER_ROLE` membership test is left in the write path, the importer, the check or `view rm`. The importer and single-item messages are asserted identical.

**What remains:**
- **The slug input differs by caller.** The write path and `view rm` read a skill's slug from `extra.slug`. The check tier reads the filename segment (`_stem_slug`, which also re-implements `_models/_item.py::_slug_from_path` with a spec-prefix lookup rather than sharing it). These agree for every file the tool writes. They diverge on a hand-renamed skill file: the check then classifies by the file name while the write path classifies by the frontmatter. Low, but it is the same kind of drift the task set out to prevent.
- **Parallel membership lists, not derivations:** `_strict_body_convergence`'s hard-coded view set, the migration's `_LEGACY_ROSTER_VIEW_NAMES`, and `sq skill show`'s `kind:` row, which still uses bundled-blind `is_system_skill` (so a stale `sq-bug` whose type was dropped shows "system (template-owned)" while its body is writable, as measured). None of these gates a write, so no refusal can be wrong because of them. The first goes away if the dead corridor is deleted.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-09-28T18:33:16Z] Paul Reviewer:
  - Partly fixed. Fixed: the `kind:` row now goes through `roster_body_view_name`; `_strict_body_convergence` and `_LEGACY_ROSTER_VIEW_NAMES` are gone; `_stem_slug` and `_slug_from_path` share `slug_from_stem`. Still open: the slug still comes from two sources. The write path reads `extra.slug` and the check tier reads the filename, and the new docstring describes the disagreement without choosing a winner, which ST2 asked for. Driven: rename `SKILL-000010-sq-bug.md` to `SKILL-000010-bugnotes.md` and empty its body. `sq check` is then clean, while `sq skill sq-bug body -m x` is refused as a per-item-type skill and `sq skill sq-bug show` hints that the item_skill tag is missing.
- [2026-09-28T22:11:54Z] Elias Python:
  - Fixed: added views.roster_slug(item_type, slug, extra) as the one derivation (a skill's extra.slug when set, else the plain slug), replacing 8 duplicated inline ternaries across 4 files. The check tier's own _check_slug now reads frontmatter early (falling back to the filename-only _stem_slug only when frontmatter can't parse at all), so it agrees with the write path even on a hand-renamed sq-<type> skill file. Reproduced the exact repro (rename SKILL-...-sq-bug.md to ...-bugnotes.md, empty its tag) red-then-green.
- [2026-09-28T22:51:59Z] Paul Reviewer:
  - Verified against HEAD (cddec435). I hand-renamed `SKILL-000010-sq-bug.md` to `SKILL-000010-bugnotes.md`, removed its tag and ran `sq repair`. `sq check` now classifies it by `extra.slug` (it names `sq skill sq-bug …`), and the write path refuses the same file as `sq-bug`. The two agree through `views.roster_slug`/`_check_slug`, and the filename is only a fallback for unparseable frontmatter.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Narrowing shape table (ST10) not written; only role case

<!-- sq:finding:F12:body -->
ST10 requires "the narrowing, as a behaviour change … table-driven over the three documents rather than one example of one": a role with `role_definition` dropped, a permanently-system skill with its view dropped, a stale **historically-bundled** `sq-<type>` whose type is dropped, and a **project-declared** stale `sq-widget` asserted **unchanged**, each with the authored prose surviving sync, repair and version-drift backfill.

Only the role case exists (`test_role_definition_view_narrowing_round_trip.py`, 6 tests). No new or changed test drives a dropped system-skill view write, the stale `sq-bug` write, or the `sq-widget` "unchanged" control. (`test_repair_body_tag_backfill_respects_a_dropped_view_declaration.py` covers the classifier and empty bodies, not the write narrowing.)

**Behaviour checked by hand, fine:** on a scratch squad with `bug` dropped from `[selected].items`, `sq skill sq-bug body -m … --force` succeeds and reads back. With `decision` still declared, the same write to `sq-decision` is refused. So the code does what ST2 says. The gap is only that no test pins it. Add the table.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-09-28T18:33:12Z] Paul Reviewer:
  - Fixed: `tests/service/test_admitted_roster_shapes_survive_convergence.py` (cb8c9a53) drives the dropped system-skill view, the stale `sq-bug`, and the project-declared `sq-widget` through write, repair, version-drift sync and re-declaration. The role row stays in `test_role_definition_view_narrowing_round_trip.py`. The targeted run passed.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-24T19:56:55Z] Paul Reviewer:
  - @manager REV-964 on TASK-942. Recommended verdict: **ChangesRequested**. Review status left at Requested; the approval transition is not mine to take.
    
    - **High, 2.** F1: a replace on any required host is refused unconditionally, so a milestone's Objective/Scope TODO scaffold can never be filled, and the sq-milestone skill's "set the body with body -m" instruction now always fails. The "no compliant replace" premise is false: the tool can put the tag back itself. F2: released 0.13.1 stored rendered bodies in every sq-<type> skill. A real 0.13.1 squad migrated with this tree ends with 7 check errors and 7 warnings. The documented remedy, view add, renders the definition twice and leaves a permanent warning whose claim is false. The ST12 scope ruling rests on a premise the code states wrongly, so it needs op-pierre again.
    - **Medium, 5.** F3: the reclaim is skipped for every role and system skill when migrating from v0_1–v0_7 (mid-chain skew, reported as UNRESOLVED-n ids). F4: the role-authoring remedy was never moved to sq role show; _cli is untouched. F5: the repair skip corridor is dead; recommend deleting it together with its monkeypatched tests. F7: the append-refusal rationale also describes the milestone append it admits (design question for a ruling). F8: several messages name wrong or no-op remedies.
    - **Low, 5.** F6, F9, F10, F11, F12: the test module's subject, docs overclaims, narration, derivation side lists, and the missing narrowing test table.
    - Checked fine: the v0_15 fixture regenerates byte-identically and v0_1–v0_14 are unchanged, gates are clean, the write path uses a single derivation, and view_placement_invocation's command forms are real. sq check is clean.
- [2026-09-24T20:16:50Z] Pierre Chat:
  - Ruling on REV-964 F1 (how a replace works on a required host):
    
    - View tags stay forbidden in body input (`reject_markers` unchanged).
    - A view declaration gains an optional `position` key, default `"bottom"`. Values: `"top"`, `"bottom"`, `"after(<regex>)"`, and possibly others later.
    - After a body write, the tool inserts each required view's tag at its declared position. Several views go in declaration order; an explicit order key may come later.
    - After the write, a check requires every required view to be present, and no view to appear more than once.
- [2026-09-24T20:25:59Z] Pierre Chat:
  - Rulings, following the `position` ruling above:
    
    - **Drop `required`.** A document's seeded views (its creation template, or its roster classification for a role or skill) are kept for good. Storing a flag for that duplicates what the seeding already says.
    - **Disabled, never deleted.** Disabling a view does not remove its tag. It marks it with a colon suffix, `<!-- sq:view:<name>:disabled -->`, which stays inside `MARKER_RE`'s character set (brackets would make the tag invisible to `find_markers`/`reject_markers`). A disabled view renders nothing. The verbs become enable/disable; `view add` places or re-enables.
    - **Every body write re-places the tags.** Replace and append alike: read all view tags (enabled and disabled), strip them, apply the prose edit, then re-insert each at its view's `position`, in declaration order, each keeping its state. So a `bottom` view moves back below appended prose. Hand-placed and disabled tags survive.
    - **Post-write check:** each seeded view is present exactly once (enabled or disabled), and no view appears twice. `sq check` reports the same two conditions.
- [2026-09-24T20:35:25Z] Pierre Chat:
  - Rulings on REV-964:
    
    - **F2 — yes.** The 0.14 to 0.15 migration also reclaims per-item-type `sq-<type>` skills carrying legacy stored text (0.13.1 wrote the rendered body into every managed skill). This reverses the earlier narrow-scope ruling, which rested on the premise that those skills never stored a body.
    - **F5 — yes.** Delete the dead body-tag skip-report channel (`RepairResult.skipped` from the non-strict convergence branch, sync's stamp-withholding on it, the CLI skip rows), together with the monkeypatched tests that re-enable the wide convergence to feed it.
    - **F7 — open.** Undecided whether append stays refused on roles and system skills. The architect should put the options in the ADR-880 amendment.
    - **`position = "after(<regex>)"`:** no match falls back silently to `bottom`; several matches means after the first.
- [2026-09-28T18:36:28Z] Paul Reviewer:
  - @manager Close-out pass on REV-964 against the committed range `1e317941~1..HEAD`, checked in the code and on scratch squads rather than from the handoffs.
    
    - **Fixed (10):** F1, F2, F3, F4, F5, F6, F7, F8, F9, F12. Each finding's comment cites its evidence. The code matches op-pierre's rulings on F1 (tags re-placed on every write, never typed), F2 (the reclaim set is the roster classification), F5 (the skip channel is deleted) and F7 (option A: roster bodies take no prose).
    - **Still Open (2, both low):** F10 and F11. F10: a named test instance survives, new narration landed in standing src, and the `_validators.py` tier-1 docstring still describes `_required_view_issues`/`required = true`. F11: the slug still comes from two sources (the write path reads `extra.slug`, the check tier reads the filename). Driven with a hand-renamed skill file.
    - REV-964 stays at Requested, because two findings have no disposition yet. Once F10 and F11 are settled, it can go to its terminal status.
    - New findings from the full-range review are on REV-967.
- [2026-09-28T22:52:37Z] Paul Reviewer:
  - @manager Re-review of REV-964 against HEAD 5897ba45. F11 is verified Fixed (a hand-renamed skill is now classified by `extra.slug` in both check and the write path). F10 is reopened: the migration's "(reversing an earlier narrow scope)" and "Driven:", the "required-view gap" test comments, the new "Before this existed / used to / now tries" docstrings, and "not this remedy any more" in the adopter-facing MANUAL. Status is ChangesRequested.
- [2026-09-29T00:05:04Z] Paul Reviewer:
  - @manager Second re-verification: F10 is still Open for two in-range sentences (migration line 82 "an earlier version of this runner", `_services/_views.py:67` "not refused outright any more"). F11 is verified. Stays ChangesRequested, not Approved.
- [2026-09-29T00:25:55Z] Paul Reviewer:
  - @manager Third pass at 611f6988: the three named F10 sentences are gone, but two test docstrings from this range still narrate the fix (test_absent_body_region_recovery.py:1-6, test_repair_body_tag_convergence_pure_function.py:100-104). F10 stays Open, so REV-964 is not moved to Approved.
- [2026-09-29T00:38:19Z] Paul Reviewer:
  - @manager F10 verified at bafd1bed; every finding on REV-964 is Fixed, so REV-964 is Approved.
<!-- sq:discussion:end -->
