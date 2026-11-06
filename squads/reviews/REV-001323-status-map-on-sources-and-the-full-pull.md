---
id: REV-1323
sequence_id: 1323
type: review
title: Status map on sources and the full pull
status: Approved
author: reviewer
refs:
- TASK-1321
- TASK-1322
- FEAT-1320
description: Batch review of TASK-1321 and TASK-1322 (FEAT-1320)
subentities:
- local_id: F1
  title: A gate-refused status move drops the whole issue refresh
  status: Verified
  severity: medium
- local_id: F2
  title: Upgrade note omits that 0.20.0 sq check fails on a mapped squad
  status: Verified
  severity: low
- local_id: F3
  title: Full-pull help says every held item; out-of-filter ones are skipped
  status: Verified
  severity: low
- local_id: F4
  title: Create-time gate blames the mapped status for any refusal
  status: Verified
  severity: low
- local_id: F5
  title: Held item refused at its own status is never moved by the map
  status: Verified
  severity: medium
- local_id: F6
  title: Refused-status docs omit the refused-at-any-status case
  status: Verified
  severity: low
created_at: '2026-11-06T16:09:24Z'
updated_at: '2026-11-06T16:29:08Z'
---
<!-- sq:body -->
## Scope

One batch review of the opt-in status map on sources and `sq source pull --full`: the code and tests of TASK-1321 and the docs and changelog of TASK-1322, delivered as commit 862fbfc9 on `release/0.20.1`. The design authority is ADR-1274 section 15 and the op-pierre rulings on ADR-1274 and FEAT-1320. The acceptance is the FEAT-1320 stories.

## What was checked

- Correctness against section 15: side order per connector and first match wins, ordered lists and per-type resolution, fall-through, a side that maps but gives no status stopping the walk, label conflicts, the moments the map applies (create, changed issue, `show --refresh`, `relink`, `--full`), the guard for `out-of-filter` and `gone`, forced status, load validation, the manual-move warning, and a source without a map.
- The integrity invariants: every status write goes through the importer's `status` op, so markdown is written before the index commit; nothing new is stored; no schema change.
- Layering and conventions: re-exports, no status names in code, no ticket IDs or history in comments.
- The tests against ADR-1172, and the adopter docs (`docs/sources.md`, `docs/stability.md`, CHANGELOG 0.20.1) claim by claim.

## Method

Each finding was reproduced with the dev build against a loopback GitLab tracker serving the recorded fixture, on a scratch squad under the scratchpad, and against the released 0.20.0 for the upgrade claims. Gates: pyright, ruff check and ruff format are clean.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1323 add-finding "…" --severity medium`; track with `sq review 1323 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A gate-refused status move drops the whole issue refresh

<!-- sq:finding:F1:body -->
A mapped status move that the squad's per-item gate refuses takes the whole issue's refresh down with it, on every pull, and the report says the item moved.

**Failure scenario.** An adopter selects `assignee_present@error` on `task` in `.overrides/workflow.toml`, and maps `"squads" = "InProgress"` under `maps.statuses.labels`. A held task sits at `Ready` with no assignee. Its issue is retitled on the tracker:

```
$ sq source pull platform
platform: unchanged 1, dropped 1
  platform/api#12: TASK-2 moved to InProgress (labels squads)
  platform/api#12: dropped, status is InProgress but nobody is assigned
```

- The new title, description, comments and record are all dropped with the status. The record is not written, so the issue is read and dropped again on every later pull, and its tracker changes never land while the map stands. Without the map, the same pull writes the title.
- `sq task 2 show --refresh` fails outright: `error: platform/api#12: status is InProgress but nobody is assigned`.
- The first line says the item moved, and it did not.
- Creation takes the same path: `CreateEvent.status` goes through the same gate, so an issue whose mapped status the gate refuses is never created (this follows from the code; the scratch run did not drive it).
- `Compiler.refresh` calls `move_status`, which prints the line, before it converts the description. A description that fails to convert therefore drops the issue after a `moved to` line too (this follows from the code; not driven).

**Why it matters.** The status map adds a write that an adopter's own validator selections can refuse on every refresh. Board notice 7 says customisation must not be able to break squads. Section 15 already has a rule for a status the map cannot give: the status is left alone, the issue's line says so, and the rest of the refresh lands.

**Expected.** A mapped status the gate refuses is left alone and reported on the issue's line (for example `<key>: status left alone, <status> is refused: <reason>`), and the title, fields, description, comments and record still land. The `moved to` line is printed only for a move that is written. One way to do this is to run the gate on a copy of the item in `move_status`, or `create`, before the event is emitted. Add one CLI case on recorded responses: a validator at `@error` and a refused move, with the title change landing.

Reproduced: dev build, loopback GitLab fixture, scratch squad.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-06T16:14:03Z] `python-dev` Elias Python:
  - Fixed in the working tree (TASK-1321): the pull runs the squad's per-item validators on a copy of the item (or a candidate item at creation) before emitting the status move; a refusal leaves the status alone, prints 'status left alone, <Status> is refused: <reason>' and the rest of the issue lands. The description is converted before the move line is printed, so a conversion failure no longer follows a 'moved to' line. CLI case with assignee_present@error covers creation and a changed issue; falsified on both paths.
- [2026-11-06T16:18:00Z] `reviewer` Paul Reviewer:
  - Verified at 70d4c0e2 on a scratch squad. Results:
    - Refresh: a retitled issue lands its title and record, and the line reads `status left alone, InProgress is refused: ...`.
    - `show --refresh` exits 0.
    - Creation: the item starts at `Draft` with the same line, and `--dry-run` shows it too.
    - Conversion: a description that fails to convert after a mapped move now prints only `dropped, its text cannot be converted`, with no `moved to` line, because the description is converted before `move_status`.
    F4 covers a reporting defect in the new create check.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Upgrade note omits that 0.20.0 sq check fails on a mapped squad

<!-- sq:finding:F2:body -->
The upgrade note says a 0.20.0 build fails only the source commands of a squad that declares the map. 0.20.0's `sq check` also fails on that squad, so a CI gate that runs `sq check` on 0.20.0 goes red as soon as the map is declared.

**Failure scenario.** A squad declares `maps.statuses` on a source. A CI job pinned to squads 0.20.0 runs only `sq check`, not `sq source`:

```
$ sq --version            # squads 0.20.0
$ sq check; echo $?
error sources: sources config invalid: .../sources.toml: invalid sources after merge: source 'platform': unknown key 'statuses' in 'maps' — use one of the accepted keys in v0.20.0: ['fields', 'links', 'types']
3
```

The CHANGELOG 0.20.1 Migration bullet tells the adopter to "Upgrade every operator and CI job that runs `sq source` on the squad before adding the map", and says the other commands keep working. `docs/sources.md` § "Declaring a map on a source that already has items" says the same ("which fails its source commands; its other commands keep working"). An adopter who follows the note and upgrades only the jobs that pull will see a `sq check` gate fail on a job that never touches a source.

**Expected.** The CHANGELOG bullet and the docs paragraph also name `sq check`: on 0.20.0 it reports the sources document as an error and exits non-zero, so every job that runs `sq check` also needs 0.20.1. Item commands (`show`, `status`, `comment`, `list`) do work on 0.20.0; I checked them.

Reproduced: released `~/.local/bin/sq` 0.20.0 on a scratch squad that declares the map.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-06T16:12:04Z] `tech-writer` Theo Writer:
  - Fixed in CHANGELOG.md (0.20.1 Migration bullet) and docs/sources.md (the upgrade paragraph under "Declaring a map on a source that already has items"). Both now say that 0.20.0 sq check reports the sources document and exits 3, so every CI job that runs sq check also needs 0.20.1, and that item commands keep working. Verified on a nested scratch squad that declares the map: on ~/.local/bin/sq 0.20.0, check exits 3, source list exits 1 and list exits 0; the dev build check exits 0.
- [2026-11-06T16:18:01Z] `reviewer` Paul Reviewer:
  - Verified: the CHANGELOG Migration bullet and docs/sources.md now name sq check, its exit code 3 and the CI gate, and keep the item commands working. This matches the 0.20.0 run.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Full-pull help says every held item; out-of-filter ones are skipped

<!-- sq:finding:F3:body -->
The `--full` help, and one CHANGELOG sentence, say that the full pull applies the status map to every held item. It does not apply it to an `out-of-filter` or `gone` item, which is correct per section 15. So the text overclaims.

**Failure scenario.** `sq source pull --help`:

```
--full   Read every held issue in detail, not only the changed ones, and apply the status map to every held item.
```

A source has a filter that rejects issue #12, so TASK-2 is held with the record state `out-of-filter`. The adopter hand-sets TASK-2 to `Ready` and runs `sq source pull platform --full`, expecting the map to bring every held item in line as the help says. The pull answers `platform: unchanged 3`, and TASK-2 stays `Ready`.

- The issue is not read in detail either. `_triage` sends only held issues the source selects, and section 15 and `docs/sources.md` say "every held, selected issue".
- The CHANGELOG "When the map applies" bullet ends with "and on every held item under `--full`". The next sentence qualifies it, but the bullet itself overclaims in the same way.

**Expected.** Say "every held issue the source selects" in the `--full` help (`src/squads/_cli/_source.py`) and in that CHANGELOG bullet, matching the docs and `SourcePullRequest`'s docstring.

Reproduced: dev build, loopback GitLab fixture with a `labels = "not bug"` filter.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-06T16:12:04Z] `tech-writer` Theo Writer:
  - Docs part done. The CHANGELOG "When the map applies" bullet now says "every held issue the source still selects under --full". The --full bullet says it moves each of those items, and that an out-of-filter or gone item is not moved. In docs/sources.md, the full-pull "overrides statuses set by hand" bullet now names items whose issue the source still selects and states that out-of-filter and gone items are not moved. The cost line in both files says "per held issue the source selects". The --help text in src is the developer's part.
- [2026-11-06T16:14:04Z] `python-dev` Elias Python:
  - Fixed in the code: the --full help now says 'every held issue the source selects'. For the writer: the CHANGELOG bullet 'and on every held item under --full' should read 'and on every held issue the source selects under --full'.
- [2026-11-06T16:18:02Z] `reviewer` Paul Reviewer:
  - Reopened. The second clause is fixed, but the help still opens with "Read every held issue in detail". A held issue the source no longer selects (`out-of-filter`) is not read under `--full`: in the scratch run the pull answered `unchanged 3` and made no detail read for it. Say "Read every held issue the source selects in detail, not only the changed ones, and apply the status map to each". `docs/sources.md` and the CHANGELOG already say it this way.
- [2026-11-06T16:21:22Z] `python-dev` Elias Python:
  - Fixed: the --full help now reads 'Read every held issue the source selects in detail, not only the changed ones, and apply the status map to it.'
- [2026-11-06T16:24:13Z] `reviewer` Paul Reviewer:
  - Verified at 5ebcd381: the help now reads 'Read every held issue the source selects in detail, not only the changed ones, and apply the status map to it.'
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Create-time gate blames the mapped status for any refusal

<!-- sq:finding:F4:body -->
The create-time gate check blames the mapped status when the squad would refuse the item at any status. Each issue then gets a false "status left alone" line before its real drop line.

**Failure scenario.** An adopter selects `parent_present@error` on `task`, which is status-independent. The source maps `closed = ["Done"]` and `"squads" = "InProgress"`. The first pull reports:

```
platform: dropped 2
  platform/api#12: status left alone, InProgress is refused: task requires a parent of type feature
  platform/api#13: status left alone, Done is refused: task requires a parent of type feature
  ...
  platform/api#12: dropped, task requires a parent of type feature
  platform/api#13: dropped, task requires a parent of type feature
```

No item is created at any status, so the status was never the problem. An adopter reading the first two lines would fix the map, or the assignee rule, instead of the parent rule. The cause is that `Compiler.create` gates only the candidate at the mapped status.

**Expected.** Report `status left alone, <status> is refused` only when the candidate passes the gate at its type's initial status and fails at the mapped one. When it fails at both, keep the mapped choice and say nothing, and the create's own `dropped` line names the real reason. The refresh path is unaffected, since a held item's status move really is refused there.

Reproduced: dev build at 70d4c0e2, loopback GitLab fixture, scratch squad.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-06T16:21:23Z] `python-dev` Elias Python:
  - Fixed in Compiler.create (src/squads/_services/_pull.py): the status refusal is reported only when the item passes at its type's initial status and fails at the mapped one; a refusal at any status prints only the pull's own dropped line. The refresh path does the same against the item's current status. New CLI case test_a_refusal_that_holds_at_every_status_is_not_blamed_on_the_mapped_status (parent_present@error), falsified.
- [2026-11-06T16:24:13Z] `reviewer` Paul Reviewer:
  - Verified at 5ebcd381: under parent_present@error the pull prints only the link line and the two dropped lines, with no status line. The new symmetric early return in move_status is not right; see F5.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Held item refused at its own status is never moved by the map

<!-- sq:finding:F5:body -->
`move_status` now returns early and silently whenever the held item fails the gate at its own current status. That covers the case where the current status is the cause, so the map can no longer move an item out of a refused status, even into one the gate accepts.

**Failure scenario.** A source maps `closed = ["Done"]`. TASK-2 sits at `InProgress` with no assignee, and the adopter then selects `assignee_present@error` on `task`. Issue #12 closes on the tracker:

```
$ sq source pull platform
platform: refreshed 1, unchanged 1
  platform/api#12: closed; TASK-2 stays
$ sq task 2 show          # status: InProgress
$ sq task 2 status Done --force
TASK-2 → Done             # the gate accepts Done
```

- Section 15 says the pull moves the item to `Done`, and 70d4c0e2 did.
- Here the item stays `InProgress`, and no line says why. Only the record changed, so no other event is gated, and the "pull's own drop line" that the code comment relies on never appears.
- `--full` and `show --refresh` cannot move it either.
- The items stuck this way are the ones that sit in a status the squad's rules now refuse, which are exactly the ones the map should resolve.

**Expected.** Apply the same rule as `create`, keyed on the candidate. If the mapped status passes the gate, move. If it is refused and the item also fails at its own status, say nothing, because the drop line covers it. If it is refused and the item passes at its own status, print the `status left alone, X is refused` line. Add one CLI case on recorded responses: the item at `InProgress` with no assignee under `assignee_present@error`, the issue closing, and the item moving to `Done`.

Reproduced: dev build at 5ebcd381, loopback GitLab fixture, scratch squad.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-06T16:26:07Z] `python-dev` Elias Python:
  - Fixed in Compiler.move_status (src/squads/_services/_pull.py): the decision is on the mapped status. It moves when the mapped status passes; when it fails and the current status passes it leaves the status alone and prints the left-alone line; when both fail it prints no status line. CLI case test_an_item_failing_a_validator_at_its_status_still_moves_to_one_that_passes, falsified.
- [2026-11-06T16:29:02Z] `reviewer` Paul Reviewer:
  - Verified at 4deba53f: an unassigned InProgress task under assignee_present@error whose issue closes now moves to Done (dry-run: would move; pull: moved to Done (state closed)). When an item fails the check at both its current and its mapped status, the refresh is silent and its record lands. When only the mapped status is refused (Done to InReview), the pull prints the status-left-alone line and the record lands.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Refused-status docs omit the refused-at-any-status case

<!-- sq:finding:F6:body -->
`docs/sources.md` ("A status the squad's checks refuse is left alone") and the CHANGELOG sentence describe one outcome only. They say the status is left alone, the line gives the reason, and the title, fields, description, comments and record still land. Since 5ebcd381 that holds only when the mapped status itself is the cause.

**Failure scenario.** An adopter selects `parent_present@error` on `task`. That rule refuses the item at every status, so the pull prints no `status left alone` line. The issue is dropped (`platform/api#12: dropped, task requires a parent of type feature`) and nothing lands, not even at creation. An adopter who has read the paragraph expects a status line and a landed refresh, and gets neither.

**Expected.** Add one sentence to both places. For example: "A check that refuses the item whatever its status is not a status matter: the issue is dropped as for any refused change, and its line names the check." Re-read the paragraph against the behaviour once F5 lands.

Reproduced: dev build at 5ebcd381, scratch squad.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-11-06T16:25:24Z] `tech-writer` Theo Writer:
  - Fixed in docs/sources.md and the CHANGELOG 0.20.1 "When the map applies" bullet. Both now give three cases, checked against move_status and create in _pull.py with the F5 change in the tree. (1) The checks accept the mapped status: the item moves, even out of a refused current status. (2) The mapped status is refused but the current status, or the initial one for a new item, passes: the status is left alone, the "status left alone, X is refused" line appears and the rest lands. (3) Refused at both statuses: the status is left alone with no status line, and the other changes are gated like any write, so a refused change drops the issue with its line naming the check. A new item is then not created. I did not write "always dropped": F5 itself shows that a held item whose only change is the record gets no drop line.
- [2026-11-06T16:29:03Z] `reviewer` Paul Reviewer:
  - Verified: the docs/sources.md three-case list and the CHANGELOG bullet match the code. The writer's choice not to say always dropped is accurate. I reproduced it: a held item that fails the check at both its current and its mapped status, with a record-only change, got refreshed 1, no status line and no drop line, and the next pull was unchanged. A gated write (a title change, or a create) is what drops the issue, which is what the text says.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-06T16:10:38Z] `reviewer` Paul Reviewer:
  - @manager review done. Recommended verdict: ChangesRequested, on one medium finding and two low ones. Each was reproduced on a scratch squad against the loopback GitLab fixture, and F2 also against released 0.20.0.
    
    - **F1 (medium, python-dev):** a mapped status move that an adopter's `@error` validator refuses drops the issue's whole refresh, on every pull. The report says `moved to` just before the `dropped` line, and `show --refresh` errors.
    - **F2 (low, tech-writer):** the CHANGELOG and docs upgrade note say a 0.20.0 build fails only `sq source`. Its `sq check` also exits 3 on a squad that declares the map.
    - **F3 (low, python-dev, plus one CHANGELOG sentence for tech-writer):** the `--full` help says "every held item". `out-of-filter` items are skipped, correctly.
    
    Sound, checked against section 15: side order and first match wins, ordered lists resolved per type, fall-through, a side that maps but gives no status stopping the walk, label conflicts, every moment the map applies, the `out-of-filter`/`gone` guard, forced status, load validation (collect-all, enums, connector-default refusal), the warning, and a source without a map unchanged (`mapped_status` returns early, and `_triage` is identical without `--full`). Every write goes through the importer, so the integrity invariants hold, with no schema change and nothing new stored. Re-exports and conventions are clean, with no status names in code. The seven new CLI cases cover each acceptance point and each would go red if its guard broke. Gates: pyright, ruff check and ruff format are clean, and `sq check` is clean.
    
    On the writer's three gaps:
    1. The conflict line names statuses, not values. **Not a defect.** It mirrors the field-conflict line (`priority left alone, its values map to high, low`), where the ADR's own "values it found" means the mapped outputs. Section 15's wording reads the same way.
    2. `--dry-run` does not show a created item's status. **Not a defect.** Section 15 and US2/US6 ask `--dry-run` to list moves, and a creation is not a move. It could be a later nicety.
    3. The warning also fires on `update --status`. **Correct.** It is the same status write by another verb, and TASK-1321 asked for it. Without it, the ownership rule would be easy to get around unwarned.
- [2026-11-06T16:18:09Z] `reviewer` Paul Reviewer:
  - @manager re-review of 70d4c0e2: ChangesRequested again, on two low findings. F1 and F2 are Verified. F1 holds on refresh, show --refresh, creation, --dry-run and the conversion-order case. F3 is reopened: the --full help still opens with 'Read every held issue in detail', and it should say every held issue the source selects. F4 is new and low: the create-time gate check reports 'status left alone, X is refused' even when the item is refused at any status, for example parent_present@error, so the line blames the status before the real drop line. Both fixes are a few lines for python-dev. Gates are clean.
- [2026-11-06T16:24:15Z] `reviewer` Paul Reviewer:
  - @manager re-review of 5ebcd381: still ChangesRequested. F3 and F4 are Verified (the parent_present@error scenario reproduced clean, and the help is fixed). F5 is new and medium, for python-dev: the symmetric early return in move_status skips silently whenever the item fails the gate at its own status. An unassigned InProgress task under assignee_present@error whose issue closes stays InProgress with only 'closed; TASK-2 stays', although Done passes the gate. It should key on the candidate, as create does. F6 is new and low, for tech-writer: the refused-status paragraph in docs/sources.md and the CHANGELOG omits the refused-at-any-status case, where the issue is dropped and nothing lands. The two-return merge itself is behaviour-neutral.
- [2026-11-06T16:29:08Z] `reviewer` Paul Reviewer:
  - @manager REV-1323 is Approved at 4deba53f, as you asked. All six findings are Verified. F5 reproduced: the unassigned InProgress task whose issue closes now moves to Done. F6: the three-case docs and CHANGELOG text match the code, and the hedged drop wording is accurate (a held item that fails at both statuses with a record-only change refreshes with no drop line). The fixes introduce no new defect. Gates are clean (pyright, ruff check, ruff format, sq check). TASK-1321 and TASK-1322 can close.
<!-- sq:discussion:end -->
