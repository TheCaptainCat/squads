---
id: REV-1129
sequence_id: 1129
type: review
title: Review of the Noted and Deferred finding states
status: ChangesRequested
author: reviewer
refs:
- TASK-1105
subentities:
- local_id: F1
  title: Released 0.16 hard-stops on every command once one finding is Noted or Deferred
  status: Open
  severity: medium
- local_id: F2
  title: Import add-finding cannot seed a Deferred finding, and the refusal names
    a CLI flag
  status: Verified
  severity: low
- local_id: F3
  title: A deferred-flagged initial status lets add-<kind> create a deferred entity
    with no pointer
  status: Verified
  severity: low
- local_id: F4
  title: ADR-1102 names a :head line that is no longer written; amend the clause
  status: Verified
  severity: info
- local_id: F5
  title: _status_deferred is a fourth copy of the status-to-role lookup
  status: Verified
  severity: low
- local_id: F6
  title: 'Tests: pointer table split into functions, a cross-layer duplicate, index-only
    seeding'
  status: Verified
  severity: low
- local_id: F7
  title: Self-pointers and roster items are accepted as deferral carriers
  status: Verified
  severity: medium
created_at: '2026-10-24T22:00:20Z'
updated_at: '2026-10-24T22:23:26Z'
---
<!-- sq:body -->
## Scope

Commit 44aba7d5 (TASK-1105): the `Noted` and `Deferred` finding states, the `deferred` role flag, the `deferred_to` pointer, its remapping, and the `subentity_deferral_resolved` check, judged against ADR-1102. Docs and the CHANGELOG are out of scope.

## Method

Read the source diff and the five new test files. Drove the dev build in scratch squads: pointer shapes (missing, nonexistent, sub-entity id, self, roster item, hand-edited non-canonical and non-string values), transitions into and out of `Noted` and `Deferred` with and without the pointer and `--force`, retype and removal of a carrier, cancelled and WontFix carriers in `sq check`, import `sub-status` and `add-finding`, a project `Postponed` status, a deferred-flagged initial status, and a deferred-flagged role reached by item lifecycles. Ran released 0.16.0 against a copy of a squad written by the dev build. Ran the new and touched test files (61 passed).

## Divergences listed by the developer

- **Deferred line in the CLI instead of `:head`.** Accepted. Outside the 0.2 to 0.3 migration nothing writes the `:head` region any more, so the CLI badge line is the only place left for it. The ADR clause is stale (F4).
- **Carrier removal needs `--force` and clears the pointers.** Accepted. The ADR says removal severs the pointer as it severs incoming refs, and refs need `--force`. The finding stays Deferred with no pointer, and `sq check` reports it, which is the intended way back.
- **`--deferred-to` only on kinds that reach a deferred state.** Accepted. Option registration is already spec-driven, and Typer's unknown-option error is the refusal the ADR asks for. The service refusal still covers the API and import paths.
- **Import `add-sub`/`add-finding` without `deferred_to`.** Not accepted as is (F2). The CLI `add-<kind>` takes it, and the import refusal tells the author to pass a CLI flag.
- **Index carries `deferred_to: null`.** Accepted. It matches `story: null`, can be rebuilt from the frontmatter, and `sq repair` restores it (verified).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1129 add-finding "…" --severity medium`; track with `sq review 1129 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Released 0.16 hard-stops on every command once one finding is Noted or Deferred

<!-- sq:finding:F1:body -->
**Driven.** Copied a scratch squad written by the dev build, holding Deferred and Noted findings, then ran released 0.16.0 on the copy. `sq list` and `sq review 2 show` both fail with "item REV-2 sub-entity F1 has status 'Deferred', which the active spec no longer declares; migrate or re-type this sub-entity ... (or run `sq repair` ...)". `sq repair` also fails ("unknown status 'Deferred' ... fix the frontmatter before running `sq repair`").

ADR-1102 Consequences says an older release "ignores `deferred_to` when it reads a review, drops it the next time it writes that review, and reports Noted/Deferred as undeclared statuses". The measured behaviour is a hard stop on every command that loads the board. The error never says to upgrade squads, and it points the user at `sq repair` and at re-typing their data, both of which are the wrong fix. The drop-on-write case cannot happen, because 0.16 never loads the review.

The tech writer measured the same thing independently, and @manager has put the options to op-pierre on ADR-1102 (keep it with a CHANGELOG warning, or a schema bump with a no-op migration so that 0.16 hits the schema gate and prints "upgrade"). This finding tracks that decision on the review. Whatever the ruling, the ADR's Consequences line needs a dated correction. On this repo, no finding can be set to Noted or Deferred until the board tool is upgraded.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Import add-finding cannot seed a Deferred finding, and the refusal names a CLI flag

<!-- sq:finding:F2:body -->
**Driven.** The import event `{"op":"add-finding","target":"REV-2","title":"x","severity":"low","status":"Deferred","as":"manager"}` is refused with "F5 cannot be Deferred without the item that carries the work; pass --deferred-to <ID>". `AddFindingEvent`/`AddSubEvent` (`_services/_import_model.py`) have no `deferred_to` field and set `extra="forbid"`, so the author cannot follow the hint: adding `"deferred_to"` is rejected as an unknown key.

The CLI `add-<kind> --status Deferred --deferred-to` exists (TASK-1105 lists it among the entry points), and import events replay the CLI verbs, so the two surfaces disagree. The workaround is an `add-finding` followed by a `sub-status` event. The refusal text is also aimed at the CLI: an import author gets a flag name, both here and in the `sub-status` refusal ("--deferred-to applies to a finding in a deferred status"). `test_an_import_defers_a_finding_only_with_a_pointer` pins that CLI wording on the import path.

Recommendation: add `deferred_to` to `AddSubEvent` (and to `AddFindingEvent.as_generic`), resolved through `handles.resolve_item` as `sub-status` does. Word the shared refusal by field and not by flag, for example "needs the item that carries the work (`--deferred-to` / `deferred_to`)".
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-24T22:13:35Z] `python-dev` Elias Python:
  - Import add-finding and add-sub take deferred_to (resolved through handles); refusals name "--deferred-to / deferred_to". Import test is now a table over sub-status and add-finding, with and without the pointer.
- [2026-10-24T22:23:20Z] `reviewer` Paul Reviewer:
  - Verified: import add-finding and add-sub with status Deferred plus deferred_to store the pointer; without it the refusal names deferred_to; the sub-status refusal names the field too.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — A deferred-flagged initial status lets add-<kind> create a deferred entity with no pointer

<!-- sq:finding:F3:body -->
**Driven.** In a scratch override, the finding lifecycle has `initial = "Parked"` and `Parked` has a role with `deferred = true`. `sq workflow lint` reports OK. A plain `sq review 2 add-finding c` creates F3 in `Parked` with no pointer, and `sq check` then warns "finding F3 is Parked but names no carrying item".

Cause: `_add_block_core` calls `_settle_deferral(..., moved=status is not None, ...)`, so an add without `--status` never runs the "entering a deferred status needs a pointer" rule, even though it enters the kind's initial status. ADR-1102 says moving into a deferred-flagged status without a pointer is refused. Every add into this lifecycle breaks that rule.

Recommendation (simplest): treat an add as an entry, and pass `moved=True` from `_add_block_core`. A plain add into a deferred initial status is then refused unless `--deferred-to` is given. The alternative is a loader refusal of a deferred-flagged initial status. One row in the loader/flag table.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-24T22:13:37Z] `python-dev` Elias Python:
  - Every add is an entry (moved=True in _add_block_model), so a plain add into a deferred initial status is refused without a pointer. Row: adding_into_a_deferred_initial_status test.
- [2026-10-24T22:23:21Z] `reviewer` Paul Reviewer:
  - Verified: with a deferred-flagged initial status, a plain add-finding is refused and add-finding --deferred-to stores it; bundled plain and --status Fixed adds are unaffected.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — ADR-1102 names a :head line that is no longer written; amend the clause

<!-- sq:finding:F4:body -->
**Read.** ADR-1102 says "The `:head` line shows 'Deferred to `<ID>` — `<title>`'". The only caller of `_discussion.set_head` is `_migrations/_v0_2_to_v0_3.py`, and `block.md.j2` no longer has a `:head` region. The developer put the line in `_cli/_common._subentity_badge_line` (`show --full`, `--raw`) and `print_subentity` (`finding <k> show`). That is the right place, and both render "Deferred to TASK-3 — Carry the work" (driven).

Under the ADR audit rule, a clause that turns out partly wrong is amended in place, with a dated comment. @architect: change the clause to "the sub-entity's display line" (the 0.16 consequence in F1 needs the same treatment). For the record: the CLAUDE.md architecture paragraph on `_rendering/` still describes `_refresh_head` re-rendering `:head` on every mutation. That is out of this review's scope.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-24T22:04:02Z] `architect` Robert Architect:
  - Fixed: ADR-1102 pointer clause amended in place to "the sub-entity's display line" (`show --full`/`--raw` badge line, "deferred to:" on `finding <k> show`), with a dated comment on ADR-1102. The 0.16 consequence is left for the F1 ruling.
- [2026-10-24T22:23:22Z] `reviewer` Paul Reviewer:
  - Verified: the ADR-1102 pointer clause now names the display line, with a dated amendment comment. The older-release clause stays with F1.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — _status_deferred is a fourth copy of the status-to-role lookup

<!-- sq:finding:F5:body -->
**Read.** `_status_deferred` (`_workflow/_models.py`) is a fourth copy of the same status-to-role lookup, after `_status_settled`, `_status_live` and `_status_blocked`. Its own docstring says it is "the same lookup as `_status_live`, reading the other flag". `WorkflowSpec.role_for` already does this resolution for the built spec. A single `_status_role(status, statuses, roles) -> RoleSpec | None` would let each check read the flag it needs, and the next role flag would not add a fifth copy.

Code-quality only, no behaviour change.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-24T22:13:40Z] `python-dev` Elias Python:
  - One _status_role lookup in _workflow/_models.py; _status_settled/live/blocked/deferred each read their flag from it.
- [2026-10-24T22:23:24Z] `reviewer` Paul Reviewer:
  - Verified: one _status_role resolver; the four flag helpers read it.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Tests: pointer table split into functions, a cross-layer duplicate, index-only seeding

<!-- sq:finding:F6:body -->
**Read**, against the brief's rule (one table per behaviour, boundary and failure rows only, no duplicate coverage across layers).

- **Pointer on update** is seven separate test functions in `test_a_deferred_finding_names_the_item_that_carries_the_work.py`, not one table. The rows are sound boundaries, but the behaviour is split, so a missing row (F7's self-pointer, F3's add-without-status) is hard to see. A table keyed by shape, with (setup, call, expected status/pointer or error fragment), would hold them all.
- **Duplicate across layers.** `test_a_deferred_finding_reads_back_its_carrier_in_the_detail` (service, `carrier_title`) is fully subsumed by the CLI `test_the_display_line_names_the_carrier_and_its_title`: breaking `carrier_title` turns both red. One of them can go. The CLI bare-number row repeats the service `bare-number` row, but the task asked for that one, so it stays.
- **State seeded through the index only.** The `subentity_deferral_resolved` table and the stray-pointer test set `deferred_to`/`status` inside `store.transaction()` without touching the file, which leaves the index ahead of the frontmatter. A hand edit (the case the rows stand for) lands in the file and reaches the index through `sq repair`. Seeding through the frontmatter plus `repair` exercises the real path, and does not depend on `check` reading the index rather than the file.
- **Pins a misleading message**: see F2.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-24T22:13:42Z] `python-dev` Elias Python:
  - Pointer-on-update is one table over 11 shapes; the duplicated carrier_title service test is dropped; the check table seeds through the frontmatter plus repair, with rows for own-review and a pointer on an open finding.
- [2026-10-24T22:23:26Z] `reviewer` Paul Reviewer:
  - Verified: the pointer shapes are one table, the duplicate carrier_title test is gone, and the check table seeds through the frontmatter plus repair. 39 targeted tests pass.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Self-pointers and roster items are accepted as deferral carriers

<!-- sq:finding:F7:body -->
**Driven.** In a scratch squad, `sq review 2 finding F1 update --status Deferred --deferred-to REV-2` succeeds and stores `deferred_to: REV-2`, so the finding is deferred to its own review. `sq check` stays silent. `--deferred-to 1` (a role item, `ROLE-1`) is also accepted, and the display reads "Deferred to ROLE-1 — Catherine Manager".

ADR-1102 says `--deferred-to` "resolves it like a ref", and a ref refuses this shape: `sq review 2 ref add REV-2` fails with "an item cannot reference itself". `_settle_deferral` (`_services/_subentities.py`) only runs `require_item`.

Impact:
- A self-pointer closes the finding as handed on while the work has gone nowhere. It passes the check, which is the very thing the pointer exists to make verifiable.
- `deferral_holders` then counts the review as its own referrer, so `sq review 2 remove` is refused with "it is referenced by: REV-2". Removal needs `--force`.
- A roster item (role, skill, operator) carries no work either.

Recommendation: in `_settle_deferral`, refuse a carrier that is the sub-entity's own parent, with the same wording as the ref guard. Refuse a roster-category carrier too, keyed on the type's category and not on a type name. Have `subentity_deferral_resolved` report a self-pointer that arrives through a hand edit. Add one row to the pointer table and one to the check table.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-24T22:13:45Z] `python-dev` Elias Python:
  - _settle_deferral refuses a self-pointer and a roster carrier; subentity_deferral_resolved reports a hand-edited self-pointer. Rows in the pointer table and the check table.
- [2026-10-24T22:23:19Z] `reviewer` Paul Reviewer:
  - Verified on 7576d2d1: self (REV-4, bare 4) and ROLE-1 are refused on update and import add-finding; a hand-edited self-pointer warns after repair; removal with a pointer elsewhere is not blocked.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T22:02:16Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested. Code fixes for @python-dev: F7 (refuse a self or roster carrier), F2 (deferred_to on import add-sub, refusal worded by field), F3 (an add enters its status, so the pointer rule applies). F5 and F6 are cleanups, cheap to fold in. F1 is the op-pierre ruling already raised on ADR-1102. F4 and F1 need a dated amendment on ADR-1102 from @architect. The five listed divergences: four accepted, the import one is F2. Targeted tests: 61 passed.
<!-- sq:discussion:end -->
