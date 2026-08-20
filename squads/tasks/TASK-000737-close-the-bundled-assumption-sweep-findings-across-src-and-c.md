---
id: TASK-737
sequence_id: 737
type: task
title: Close the bundled-assumption sweep findings across src and clients
status: Done
author: tech-lead
priority: high
refs:
- REV-736:addresses
- EPIC-538
- TASK-674
- BUG-732
description: Fix all 29 driven findings from REV-736, one subtask per coherent surface;
  ST4 lands last because it regenerates the templates, the manifest and two managed-section
  goldens.
subentities:
- local_id: ST1
  title: 'Integrity core: marker regex, timestamps, per-file degradation'
  status: Done
  assignee: python-dev
- local_id: ST2
  title: An override is honoured or reported, never silently ignored
  status: Done
  assignee: python-dev
- local_id: ST3
  title: CLI and TUI per-type flag surfaces derive from the active spec
  status: Done
  assignee: python-dev
- local_id: ST4
  title: Generated agent text follows the active spec and live roster
  status: Done
  assignee: python-dev
- local_id: ST5
  title: 'Sync and backend integrity: index, seeding, model, mission'
  status: Done
  assignee: python-dev
- local_id: ST6
  title: VS Code client reads the spec it already fetches
  status: Done
  assignee: typescript-dev
- local_id: ST7
  title: Migration runners stop persisting state the spec never validates
  status: Done
  assignee: python-dev
created_at: '2026-08-03T15:16:11Z'
updated_at: '2026-08-15T15:47:12Z'
---
<!-- sq:body -->
Twenty-nine findings from REV-736's seven-shard bundled-assumption sweep, every one driven and
reproduced. All twenty-nine are in scope for this release — none is deferred (op-pierre: "let's
embark the rest too, no finding left for 0.14").

One subtask per coherent surface, with findings that share a root cause in the same subtask so each
reviews as one change. Subtasks carry their own assignee, which is how the TypeScript work sits here
rather than in a second task.

Read `REV-736` before starting: `sq review 736 show --full --comments` gives every finding body
(file:line, the reproduction, and the ADR or invariant each contradicts) plus two comments recording
the cosmetic and sanctioned observations, then `sq review 736 finding <Fk> show` for the one you are
on. Do not re-derive — every finding names its site and its symptom.

## Coverage map

| Subtask | Findings |
| --- | --- |
| ST1 Integrity core | F2, F3, F27 |
| ST2 Overrides honoured or reported | F1, F4, F11, F12, F13, F16, F19, F29 |
| ST3 CLI and TUI flag surfaces | F5, F15, F20, F21, F28 |
| ST4 Generated agent text | F6, F7, F8, F14, F26 |
| ST5 Sync and backend integrity | F9, F10, F24, F25 |
| ST6 VS Code client | F22, F23 |
| ST7 Migration runners | F17, F18 |

## Order of work, and why

1. **ST1, ST6 and ST7 first, in parallel.** No shared files with each other or with anything below.
   ST1 is foundational: the `find_markers` fix changes what every service-level marker read and
   write sees, so landing it first means the rest of the work is tested against a corpus the gate
   can actually see. ST6 is TypeScript with no Python overlap. ST7 touches only frozen migration
   runners, which nothing else here goes near.
2. **ST3 next.** It fixes the `_badges` collection-resolution primitives that ST2's F16 validates
   through. Fixing the consumer before the primitive means writing F16 twice.
3. **ST2 next.** It edits `_workflow/_loader.py` in the same regions as ST3's F5, so the two must
   not run concurrently.
4. **ST5 next.** `sq sync` behaviour must be final before ST4 regenerates output from it.
5. **ST4 last.** It regenerates templates, the template manifest and two managed-section goldens;
   every subtask that changes generated content must be final first so the goldens are regenerated
   once, against final behaviour.

ST6's second deliverable (declared field labels) waits on ST3's new catalog surface; its first
deliverable does not wait on anything.

## Standing rules for every subtask

- Each fixed gap earns a `tests/meta` guard so it cannot come back (board notice 10). Where a guard
  exists but scans too narrow a surface, widen that one rather than adding a second.
- Falsify your own new test before handing back: break the fix, watch it go red, restore it, watch
  it go green, and report both (board notice 7).
- Adopter-visible behaviour changes are reported, not written up: say what changed and why it
  matters to an adopter, and hand it to the tech-writer for `CHANGELOG.md` and `docs/`
  (board notice 16). Do not author adopter prose from the implementer seat.
- A new module-level dict or list trips `tests/meta`'s mutable-state guard — allowlist it as a CODE
  constant with a one-line reason, do not restructure the code to dodge it.
- Close each finding as you fix it: `sq review 736 finding <Fk> update --status Fixed`, citing the
  fix in a finding-scoped comment. Do not let them pile up as false Open debt.
- `sq check` must be clean for your work before you hand back. No `sq remove` / `sq delete`.

## Two halves are gated on decisions that have not been made

- **F29's second half** — whether an adopter may declare a ref kind of their own — is parked on
  board notice 8, which commissions the ADR for exactly that question, and ADR-49 currently states
  the vocabulary is closed for 1.0 with no escape hatch. ST2 fixes the inert-declaration half only
  and must not open the vocabulary.
- **F23's declared-label half** needs a machine surface for sub-entity field vocabulary, which does
  not exist anywhere today. ST3 adds it, ST6 consumes it. Flagged for op-pierre: this is a new
  adopter-visible JSON surface, so if it should go through the architect first, ST6's label half is
  the only work that waits.

Two agents were editing `src/`, `docs/` and the templates while this was written. Check the tree's
current state before starting a subtask — parts of F7 are already done (see ST4).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 737 add-subtask "<title>"`; track with `sq task 737 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Integrity core: marker regex, timestamps, per-file degradation |  |
| ST2 | Done | python-dev | An override is honoured or reported, never silently ignored |  |
| ST3 | Done | python-dev | CLI and TUI per-type flag surfaces derive from the active spec |  |
| ST4 | Done | python-dev | Generated agent text follows the active spec and live roster |  |
| ST5 | Done | python-dev | Sync and backend integrity: index, seeding, model, mission |  |
| ST6 | Done | typescript-dev | VS Code client reads the spec it already fetches |  |
| ST7 | Done | python-dev | Migration runners stop persisting state the spec never validates |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Integrity core: marker regex, timestamps, per-file degradation

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Three defects in the integrity core, each of which lets a corrupt or degraded corpus pass the
must-pass gate clean. Land this first — the marker fix changes what every service-level marker read
and write sees.

**F2 — `find_markers` is blind to every sub-entity marker.** The regex at `_sections.py:68` accepts
`[a-z0-9]` only, while every declared sub-entity `local_prefix` is uppercase (`US`/`ST`/`F`). On a
real repo file, 16 well-formed markers are present and `find_markers` returns 8. Widen it to accept
any declared prefix casing — including any adopter-declared kind whose prefix is not all-lowercase —
and fix the two blind consumers: `reject_markers` (`_services/_base.py:299`) currently accepts a
forged sub-entity marker inside an agent-authored item body, and the next finding-body write then
lands in the forged region and destroys the prose around it while leaving the genuine region empty,
which breaks invariant 3; `_marker_issues` (`_services/_maintenance.py:94`) cannot see a duplicated
or unclosed sub-entity marker, so `sq check` reports clean on a broken file. Keep the regex strict
about *well-formedness* — prose such as a quoted marker tag inside a role file must still not lint as
a real marker.

**F3 — an absent timestamp invents `now` and wedges the item permanently.** `_parse_dt`
(`_models/_item.py:557`) returns `datetime.now(UTC)` for a missing `created_at`/`updated_at`,
bypassing `clock.now()` — an ADR-77 violation, and the module already imports clock for `iso()`.
Because `_itemfile.frontmatter_skew` round-trips both sides through `from_frontmatter`, the disk side
re-invents `now` on every read and can never equal the index, so every mutation is refused with a
"run sq repair" pointer that repair cannot honour: repair rebuilds the index and never rewrites
markdown. Two full repair-then-mutate rounds were both refused, with `sq check` silent throughout.
Entry point is `sq adopt` or any hand-authored `.md`. The item must end up mutable, and a missing
timestamp must be healed on write or reported — never silently re-invented per read.

**F27 — `search` and `inbox` abort whole-corpus on one unreadable file.** In
`_services/_collab.py`, both the search and inbox loops call `_aio.read_text` with no per-item guard,
and `path_exists` guards a *missing* file but not an unreadable one, so the error propagates and
discards every result already accumulated from readable files. `sq search` exits 1 with empty stdout;
with `--json` it emits nothing at all, not even `[]`, so a consumer gets a parse failure on top of
the exit. Same for `sq inbox`. Meanwhile `list`, `tree`, `blocked`, `show` and `graph` all exit 0
with everything, which is why the failure looks arbitrary. The VS Code client calls search and turns
any non-zero exit into a runtime error, and its per-keystroke debounce stacks a fresh error toast per
resolution. Extend TASK-674's per-file degradation posture — same skipped-file reporting, same exit
contract — to these two commands; that task scoped four commands by name and never claimed these, so
this is a coverage gap rather than a regression.

Guards: the marker regex and the degradation coverage each need a `tests/meta` guard. For the marker
regex, drive it against a real multi-sub-entity file rather than a synthetic one-marker fixture — the
original blind spot survived because no test carried an uppercase prefix.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-08-06T19:45:48Z] Elias Python:
  - ST1 landed: F2, F3 and F27 all Fixed on REV-736, each with its own comment carrying the driven evidence, the fix, the falsification result and the tests. Summary of what changed beyond the three fixes themselves.
  - What else now behaves differently, because F2 changes every service-level marker read and write. Three consumers, all checked. reject_markers now refuses a forged sub-entity marker in an authored body - intended, and it made one previously-accepted body in this repo refuse: BUG-727's repro line quoted a well-formed marker tag inside backticks. Judged the refusal correct (the guard's own message has always said backtick-wrapping does not neutralize a tag) and de-wrapped it rather than softening the regex; a scan of every authored prose region across all 712 item files found that one instance and no other. _marker_issues now sees sub-entity markers, so sq check went from clean to reporting that same file - now clean again. And _overrides/_service.py held a verbatim copy of the old pattern, which would have stayed blind; deleted, it now calls find_markers, and a meta guard forbids a second sq-marker regex outside the primitive.
  - Two things I fixed that were adjacent rather than named. sq check now warns (not errors) on a frontmatter missing created_at/updated_at, so the invented placeholder is reported rather than silently re-invented per read until a write heals it. And _services/_import_model.utc_now_floor was a second direct wall-clock read, so an sq import with no --at ignored a forged instant; now clock.now(), which leaves _clock.py as the only wall-clock reader in the tree and lets the guard assert that with no allowlist.
  - Three tests/meta guards added, one per fixed class: single case-blind marker-recognition definition; wall-clock time only through the clock module; corpus walks must not read item files inline. Each pairs a structural AST or text scan with a behavioural probe, because a scan alone passes on a correct-looking mechanism nobody calls.
  - Gates: pyright, ruff check and ruff format all clean with --all-extras. tests/meta, tests/unit, tests/service, tests/tui: 2125 passed. tests/cli, tests/integration: 1042 passed, 1 skipped. Full suite left to the main loop as briefed. One pre-existing unrelated failure I did not touch: tests/test_scale.py::test_scale_search_completes_within_bound fails in its own setup with "author is required: the actor's slug" - reproduced with my test-side edit stashed, so it predates this work.
- [2026-08-06T20:12:19Z] Paul Reviewer:
  - Reviewed ST1 at 366752a in an isolated worktree at that commit. Verdict: F2 accepted, F3 accepted, F27 accepted for its stated scope with a gap (F38). Six new findings on REV-736: F38, F39 medium; F40, F41, F42, F43 low. Gates re-run at the commit: pyright 0 errors, ruff check and format clean, the 188 targeted + tests/meta tests green.
  - Falsification table confirmed exactly, each reverted and restored: the lowercase marker class reddens 21 across the two marker files; removing the skew exemption reddens 13; reverting _parse_dt reddens the 2 injectable-clock parametrisations plus the wall-clock meta guard; the pre-fix path_exists-then-read shape reddens 10.
  - F2 shape families driven: forged sub-entity markers refused in item bodies and sub-entity bodies for every declared kind, in mixed casing, and in titles and comments; duplicated and unclosed sub-entity pairs now reported by check; the placeholder prose forms still accepted. Corpus scan re-run independently over all 767 files, three passes (inline-with-prose, unrecognised standalone tag shape, marker balance): zero at the reviewed commit, and exactly one at the tree before the de-wrap, BUG-727 line 17, which is also the only file the balance pass reports. The claim of one instance and no other holds. The fix makes 10080 of the corpus's 15156 markers visible that were not before, so two thirds of the corpus was outside the guard. The override surface is unaffected: comparing the old and new tag classes across all 27 bundled templates gives an identical required-marker set for every one.
  - The strictness trade is the right one. What is newly refused is a comment-wrapped tag carrying an uppercase sub-entity prefix, and refusing it is not a style preference: the balance pass reports the one real instance as an unclosed marker, so accepting it leaves a structurally broken file. The escape hatches survive. But the judgement was argued from a message the body seam does not print, which is F43.
  - F3 matrix driven through frontmatter_skew, both fields against absent, null, YAML tilde-null, empty string, unparseable, present-equal, present-different and an unquoted PyYAML datetime: absence-only holds in every cell, an absent timestamp does not mask a divergence on another field, and the result is stable across three reads at three forged instants. End to end through the CLI: the check warning fires and names the field, the mutation succeeds, and the healed value is the index's original. F39 is the case that is not covered - a repair between the strip and the heal replaces the index's real created_at with a placeholder, and the heal then persists it.
  - F27 driven as the five causes on both commands with and without --json: permission denied, undecodable, broken symlink, genuinely-missing and a clean corpus all behave as claimed, stdout stays valid parseable JSON, and a genuinely missing file is correctly not reported. F38 is the sixth shape: an item whose path resolves outside the squad folder still loses the whole answer, because the path resolution sits outside the guard.
  - Exit 1 is the right contract. The three commands in this posture that already report a degraded read exit non-zero, memory list is the single documented exception, and a fourth answer would make the posture unlearnable. Under --json the payload has to stay a bare array, so the exit code is the only out-of-band channel left, and exiting 0 would make an incomplete search indistinguishable from a complete one to every script - the failure mode where a user concludes an item does not exist. The client toast is the client's rule to change, and this change is what makes changing it possible. One inherited weakness worth stating rather than fixing here: exit 1 is already the code for outright failure on these commands, so a script cannot separate degraded from failed. That is true of repair and board list too, so it belongs to the posture, not to ST1.
  - The three meta guards: the wall-clock guard is sound, AST-based, allowlist-free, and its planted shapes and override probe all hold. The corpus-walk guard is honest about its narrow scope and its behavioural half is real. The marker guard has two driven holes, both in F40 - a formatter-wrapped re.compile evades it in any module, and its exemption is module-granular so a new general recogniser planted in the frozen-reader module passes all six tests. The exemption itself is genuine: those readers interpolate a frozen literal prefix map and are imported only by the two migration runners.
  - Also confirmed: the scale search failure predates ST1. Reproduced at the parent commit with src and tests both checked out there, same line. It is broader than reported - all five scale tests die in the same setup call, since 2026-07-31, which is F41.
  - Nit, not filed: on a degraded corpus with no matches, the CLI still prints a confident "no matches" or "nothing for @slug" before naming the skipped files. The TUI got the honest wording in this same change; the CLI did not.
  - @python-dev F38 and F39 are the two worth a fix pass; F43 is a two-line change that closes the gap in the judgement F2 rests on. @tech-lead ST1 is done on its own scope.
- [2026-08-06T20:36:17Z] Elias Python:
  - Second round landed. F38, F39, F40 and F43 all Fixed on REV-736, each with its own comment carrying the driven evidence, the fix, the falsification result and the tests. F42 left Open — doc-only and routed to the architect. F41 untouched, duplicate of BUG-740.
  - F38 is the one worth reading twice, because it is what this round produced rather than what it inherited. The guard was placed one call too late: correct in every shape I tested, and the shape I did not test was the one where the throwing call sat in the argument list. Asked the same question of the rest of both walks call by call rather than assuming, and item_file was the only other one — is_open and item_subentity_kind are documented total, everything else in the loop is pure text. The meta guard now enforces the operation rather than one of its steps, with a planted test for the exact defeating shape.
  - Broadening that guard surfaced one genuine hit outside my area: ServiceCore._skill_paths resolves paths inline over a skill walk. Exempted rather than changed, with a reason — it feeds backend regeneration, so a silently short map would write managed files with a skill body missing, and loud refusal is right there. Function-granular exemption with a liveness test, not a module-granular one.
  - Also folded in the un-filed nit: on a degraded corpus with no matches the CLI no longer prints a confident "no matches for X" / "nothing for @slug". It says "... in what could be read — N item files skipped, listed below", matching the honesty the TUI already had. A genuinely empty result on a fully-read corpus still says so plainly, and that distinction is what the test pins.
  - One process note against myself: mid-round I ran git checkout on _collab.py to undo a falsification edit and discarded the uncommitted F38 fix with it. Caught it immediately, reapplied by hand, re-verified. Reverting a falsification by checkout is unsafe while the real fix is uncommitted in the same file — undo the exact edit instead.
  - Gates: pyright, ruff check and ruff format all clean with --all-extras. tests/meta + unit + service + tui: 2166 passed. tests/cli + integration: 1092 passed, 1 skipped, and two failures that are not mine — test_json_output_shape's workflow_types golden (the type payload has grown subentity_kind/lifecycle) and an ImportError in test_workflow_types_cli.py. Both live entirely in _cli/_workflow_cmd.py and _workflow/_models.py, which is ST3's in-flight area; none of my four changed source files is involved. Full suite left to the main loop as briefed.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — An override is honoured or reported, never silently ignored

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Eight findings, one acceptance statement: a declaration an adopter writes is either honoured or
reported — never silently ignored, and never answered with the bundled vocabulary instead.

All eight are Fixed on `REV-736`, each with its own body carrying the driven evidence, the fix
and the falsification result. What follows is the cross-cutting shape of the change.

## One boundary, two directions

`F1` and `F11` were the same seam failing in opposite directions: the spec load boundary
swallowed a resolution failure (falling soft to bundled) and leaked a malformed shape (as a raw
traceback). Both are closed at that boundary. A resolution failure is carried on
`RequestContext.spec_error` and every spec-consuming surface refuses with one shared text
(`_workflow/_loader.spec_refusal`), composed where the file and the loader's cause are both in
hand and used by `open_service` too. A malformed shape is refused by three shape guards fronting
every walk in `_build_spec`, so it becomes a lint finding at every section and nesting position.

The refusal is deliberately *not* a root-callback gate with an exemption list. That shape was
built first and broke the degradation paths `sq check` and `sq repair` are designed around: those
two take the refusal from `open_service` and report it as a finding, which is the contract.
`sq workflow lint` survives because it neither opens a service nor reads the active spec.

## Validating the declaring scope, not a global set

`F4`, `F16` and `F12` are one idea applied at three layers. A role override now merges through
the shared engine and validates against `RoleSpec` rather than being assigned untyped into a
dataclass. A stored badge value is read through `badge_value`, so every declared field is checked
and not only the two with a same-named model attribute. An entity's status is judged against the
lifecycle it is actually driven by, not the flat spec-wide status set. `F13` is the same argument
one level down: a `[selected]` keep-list entry is checked against the section's real keys.

## The judgement calls, stated rather than buried

- **The unreachable-status check is a report, not a fifth fail-closed clause.** Its remedy is a
  per-item `--force` move, reachable only while commands still run. An earlier revision made it
  fail closed and produced an item repairable only by deleting the override. Split into two named
  collectors so each is named for the question it asks. Detail on `F16`.
- **`F29`'s enforcement half is a different decision, not a fix.** Reading `ref_rules` as an
  allowlist of carriable kinds contradicts the closed-vocabulary decision's own "no project-config
  lookup on the validation path", and is contradicted by the bundled document itself: 115 live
  refs in this repo would become invalid. Routed to the commissioned ref-kind decision, with both
  reasons pinned as tests. The vocabulary is untouched. Detail on `F29`.
- **`sq workflow lint` stays quiet about a shrunk adopter-declared collection**, because the
  per-value attribution it uses has no bundled counterpart to compare against and widening it
  would assert a cause it cannot establish. The condition is already reported at exit 1 by the
  load boundary and by `sq check`. Flagged on `F16` rather than guessed at.

## Guards

Four `tests/meta` guards, one per fixed class where a durable one was possible: every override
document merges through the shared engine (structural, per loader); every scaffolded worked
example loads against the live models; no source file reads a badge value by `getattr` on a
field's code (with a liveness half and a behavioural half); the bundled container-heading table
stays paired with the plurals `workflow.toml` declares.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-08-15T14:42:16Z] Paul Reviewer:
  - Delta review of ST2 (2fed334) plus its F46 pass (b2ea93b), read at e7b25d7 in an isolated worktree. Verdict: sound, done, with two new findings against it. F48 (medium) and F50 (low) are on REV-736; F49 (medium) is a consequence of F4 and is filed there too.
  - DRIVEN, refusal contract. Broken override (declared type plus an invalid role colour, TOML verified to parse before use) swept across 34 surfaces: zero tracebacks. Read surfaces refuse with the shared text; sq workflow lint, sq --help and every --help page still render; sq check degrades and reports. Falsified: dropping the spec_error raise from get_active_spec turns 10 of the 17 cases in test_a_broken_override_is_refused_on_every_surface.py red, restored byte-identical. The parse-time-hook regression F46 caught itself is really pinned - both cases assert the absent traceback AND the presence of the refusal.
  - DRIVEN, F16 status half. A subtask on Todo under an override binding subtask to a machine without it: sq workflow lint exit 1, sq check exit 3, sq list -a exit 0. The two gates agree and the item stays reachable for the --force move, which is the split's whole argument. DRIVEN, F4 end to end: a role override carrying title, mission and responsibilities = ["$(*self)", "Sharpen the axe"] reaches the index, both compiled rosters and the role body on ONE sync with the splat spread rather than written as a token, while model = "opuss" and a typo'd key are each refused by name. Falsified F16's badge half (3 red), F13's selected-entry clause (1 red), F46's check and its clause 2 separately (12 and 4 red). All restored byte-identical, every fixture gated on sq list exiting 0 first.
  - Both contradictions on the record CHECKED INDEPENDENTLY and both hold. parent_required is not a create gate: READ, its only consumers are subtask_story_mapping, _validate_subtask_story, _kind_is_story_target and hint text; DRIVEN, sq create task with no parent succeeds at exit 0 on the bundled spec where task declares parent_required = "feature", with sq check clean. F47 is correctly filed and F46's stated consequence is correctly narrowed. The guide-to-work argument holds too: READ off workflow.toml, done is settled/hidden with colour positive while retired and superseded are settled/hidden with colour muted, so the three differ only in presentation, and guide declares no parents, no parent_required, no subentity_kind and no ref_rules - so nothing it declares is silenced. That last clause is exactly what F48 shows does NOT hold for decision-to-work, which the same body lists as deliberately permitted.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — CLI and TUI per-type flag surfaces derive from the active spec

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
ST3 delivered both halves.

## Part 1 — the flag surfaces

One root cause across F5/F15/F20/F21/F28: the CLI parameter surface is baked from the bundled
spec at import time, and the collection resolver answered a *decision* with a fallback built for
*rendering*.

- **F5** — `RESERVED_CLI_ALIASES` (a hand-maintained alias -> owning-type table beside
  `RESERVED_CLI_VERBS`, pinned by `tests/meta`) makes the loader refuse a declared type named
  after a bundled alias, and an alias claimed by a type other than its owner. Separately,
  `get_command` on both the root group and `sq create` refuses a bundled alias the active spec
  no longer declares, dispatching into a refusal command that names the alias the owner declares
  now. A *dropped* owner type is deliberately excluded — its aliases keep routing to the
  canonical membership gate, which owns that message.
- **F15** — the sub-entity command tree rebuilds on the kind's whole SIGNATURE (name, plural,
  story mapping, and every field's code/label/collection/required/default), not just its name.
  The service's generic `fields=` door is gated the same way the item axis already was.
- **F20/F21** — the CLI's third, wrong pre-parse of `--priority` is gone; the service's
  `_check_priority` is the one gate. Help resolves through a new strict `declared_collection`,
  and `--priority`/`--no-priority` are hidden on a type declaring no priority field. The
  cross-type list/tree filter validates against the union of every declared binding, which is
  byte-identical to today for the bundled spec.
- **F28** — the TUI glance line iterates declared fields.

## Part 2 — the published catalog

`sq workflow subentity-kinds` ships, human table plus `--json`, one row per declared kind
ascending kind name, all eight keys, `fields` reusing the type row's entry shape through one
shared `FIELD_ENTRY_FIELDS` tuple and one builder. The frozen type row gains `subentity_kind`
and `lifecycle`. Golden + drift test per the family's discipline.

Every finding is closed against its own body on REV-736 with the mechanism and the falsification
result. Adopter-visible surface changes are listed in the handoff comment on TASK-737.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-08-03T15:37:33Z] Robert Architect:
  - The sub-entity field catalog ST3 flagged for the architect is now specified: ADR-738 §3 (Proposed). Read it before building — the shape is wider than "code, label, bound collection": the row is `{subentity_kind, lifecycle, plural, local_prefix, container_heading, completion, maps_parent_story, fields}`, and §5 adds `subentity_kind` to the type row (ADR-459's frozen catalog, declared as an extension in ADR-738's own body per that catalog's rule). `placeholder` is deliberately not published.
  - Reasons the row is whole rather than `fields`-only are in §9: each landing is a Tier-3 event with its own golden, drift test and adopter entry, and one design should not make an adopter watch one row grow keys twice. BUG-732's `lifecycles` catalog is the same family under the same grammar but is 0.14 — do not build it here.
- [2026-08-06T20:51:45Z] Elias Python:
  - ST3 landed. F5, F15, F20, F21, F28 all Fixed on REV-736 with the mechanism and the falsification result in each finding body, plus the ADR-738 catalog.
  - Every finding was DRIVEN first on a throwaway squad with the override in <squad-dir>/.overrides/workflow.toml, then re-driven after the fix. All five reproduced exactly as written. Nothing was inferred from reading.
  - Falsified all fifteen changed behaviours by breaking each one and watching the intended tests redden, then restoring: both loader clauses, the stale-alias dispatch, the signature rebuild, the sub-entity service gate, the create/update/filter priority parses, the priority advertisement, the glance loop, the type-row join key, the kind row values, the row order, the widened field-code guard, and the alias-table pin. Two probes were themselves wrong first and I fixed the probes: my alias-collision test was passing on the pre-existing duplicate-alias error rather than the new check, and one override was silently ignored because a multi-line TOML inline table is invalid, which the fail-soft spec resolution turns into a silent fall back to bundled. The override writers in my new modules now load the spec eagerly so a broken fixture is a setup error, not a misleading pass.
  - Guards added, one per fixed class: tests/meta/test_reserved_cli_aliases_matches_the_bundled_alias_table.py pins the alias table against the bundled declarations AND the live root/create command tables in both directions; the existing field-code guard was WIDENED in place (renamed to test_render_paths_never_hardcode_a_field_code_literal.py) to cover src/squads/_tui/ and src/squads/_cli/ alongside the item templates, to recognise the strict declared_collection sibling, and to carry a small sanctioned list (the two --priority sites, each with a reason) plus a no-stale-entry test so the exemption cannot outlive its code.
  - Gates: pyright 0 errors, ruff check clean, ruff format --check clean, sq check clean. Targeted suites green: tests/cli tests/tui tests/unit tests/meta tests/service tests/integration = 3293 passed, 1 skipped, 0 failed. I did not run the full suite or the slow scale tests, per the brief.
- [2026-08-06T20:59:48Z] Robert Architect:
  - Ruled **keep** on the §5/§9 tension you flagged: shipping both type-row keys is correct, nothing to revert, and the golden stands. Your instinct was right for a better reason than the compat one — §9 already ships a dangling `lifecycle` on the kind row deliberately, so the only real question was whether the type row gets the same treatment, and it does. ADR-738 amended in place: rule 6 now states the forward-reference rule generally, §5's bullet is annotated, §9 rewritten so it no longer contradicts §5. My own earlier note on this subtask carried the same ambiguity — "one design should not make an adopter watch one row grow keys twice" alongside "`lifecycles` is 0.14" — so the fork was mine to close.
  - One follow-up the ruling creates, and it is not yours to absorb silently: `sq workflow statuses --json` is a flat `{status, role, badge}` payload with no lifecycle field, so in 0.13 nothing lets an adopter resolve a `lifecycle` value to its states. §9 now requires 0.13's adopter-facing entry and `docs/workflow.md`'s join table to say the reference has no catalog to join yet. @manager to route that doc line — it is the condition that makes shipping the key early safe.
- [2026-08-06T21:06:11Z] Theo Writer:
  - Adopter-facing half written for ST3. Three surfaces: the 0.13.0 CHANGELOG entry, `docs/workflow.md`s new "Joining the catalogs" section, and `docs/stability.md`s Tier-3 catalog table. Read ADR-738 §2/§3/§5/§8/§9 first, then verified every claim against the shipped payload rather than against the ADR or the brief.
  - Drove the whole F23 chain end to end rather than describing it from the ADR: item.type "review" -> type row subentity_kind "finding" -> kind row fields[] {severity: "Severity"} -> the sub-entity badges {"severity": "high"} rendering as "Severity: high". Also checked the claims I make about the derivation traps: container_heading is "User Stories" where `"stories".title()` gives "Stories" (and I confirmed sq really writes `## User Stories` into a feature file), and completion is "Fixed" for a finding but "Done" for a story. Confirmed the kind row fields entry shape is key-identical to the type row (code/collection/label), that all ten type rows carry the same key set with subentity_kind null on seven, and that local_prefix is US/ST/F.
  - The forward-reference obligation from §9 is discharged on all three surfaces, and I verified the premise myself before writing it: `sq workflow statuses --json` is `{status, role, badge}` with 23 rows and no lifecycle field, and there is no `lifecycles` sub-command in the family. Each surface says the same thing — lifecycle is a grouping key and nothing more, equal values mean the same machine, nothing in the 0.13 --json surface exposes lifecycle membership, so do not go looking for a command that expands it. No surface mentions a future release; the stability table also gained the two new type-row keys, which it was missing.
- [2026-08-15T14:42:42Z] Paul Reviewer:
  - Delta review of ST3 (669d427), read at e7b25d7 in an isolated worktree. Verdict: sound, done, no new findings. Reviewed at the lower depth the brief set.
  - DRIVEN. F5: an override renaming feature's aliases to ["ft"] makes sq feat 19 show and sq create feat both refuse at exit 1 naming the alias the owner declares now, while sq ft 19 show works and sq feature is untouched. F20 and F21: with task's priority bound to a tshirt collection and bug declaring no fields, --priority m is accepted on task, --priority high is refused naming s, m, l, --priority on bug is refused as not a settable field, --priority is hidden from sq create bug --help and reads "Priority: s|m|l" on sq create task --help, and sq list --priority m filters correctly. The published subentity-kinds catalog carries all eight keys per row in ascending kind order with the type row's field entry shape. Every fixture gated on sq list exiting 0 first; my first fixture was itself wrong (a colour key Badge does not declare) and the loader caught it, which is the setup gate doing its job.
  - One observation, not a finding, because it is the half ST6 owns: the --priority help text and the sq list column both still read "Priority" where the field declares label = "Size". The codes are spec-derived; the label is not yet.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Generated agent text follows the active spec and live roster

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Five findings in the text squads generates for the agents that use it — skills, the CLAUDE.md and
AGENTS.md managed regions, the workflow cheatsheet — plus the operator's diagram removal and the
regeneration this subtask owns. One acceptance statement: **generated agent text follows the
active spec, the active playbook and the live roster, never the bundled defaults.**

All five findings are Fixed on `REV-736`, each with its own body carrying the driven evidence,
the fix, the falsification result and the guard. What follows is the cross-cutting shape.

## Declaration, not derivation-by-convention

Three of the five had the seam already threaded and simply unused (`roles` into the squads-skill
render, `squad_dir` into the memory-skill render, the parent kind's `local_prefix` one attribute
away on an object the loop already held). Those are one-line reads once you look.

The fourth, the create-lane, was different in kind: the data did not exist to derive from. The
lane lived in a hand-maintained slug→type map beside the playbook, with a module-level frozenset
of laned types computed at import. It now lives in the playbook itself, as a declared `authors`
flag on a role guide — the sole source, per call, off the active merged document.

A declared flag rather than the prose scan the governing decision offered as its primary
mechanism, because the scan does not reproduce the table it was meant to derive: the create verb
for a type is not always written in that type's own section, and one bundled lane has no create
verb in its guide at all. It is also the exact anti-pattern this sweep is about — a naming
convention standing in for a declaration.

## The lifecycle diagrams are gone

Both diagram blocks in the cheatsheet, plus the `mermaid_id` filter and the
`lifecycle_states_in_order`/`lifecycle_edges` template globals, which nothing else consumed
(checked, not assumed — `sq graph`'s mermaid export has its own separate `_safe_id`).

The `## Type lifecycles` table stays; it is what agents actually read, and the hierarchy the
flowchart drew is already in the prose bullet directly above it. The linearization is lossy
against the real edge set, and the machine-readable replacement is a later release — exact
transitions stay discoverable from a refusal message until then.

## What the guards cover

The two new `tests/meta` guards are behavioural, not text scans, because a text scan cannot
tell a literal from a derivation that agrees with it on the bundled spec:

- every agent-facing surface is rendered against a squad sharing no vocabulary with the bundled
  documents — moved squad dir, renamed retired/superseded statuses, renamed sub-entity prefix —
  across two rosters (one carrying no bundled slug, one carrying the bundled authoring slugs),
  and no bundled literal may survive. A floor test asserts the probe renders its own vocabulary,
  so the scan cannot pass on an empty render;
- the bundled template tree is scanned against **this squad's own operator roster read off
  disk**, so an operator registered later is covered with no edit to the guard.

The lane guard exercises an override-declared authoring role end to end, at the service layer
and through the CLI, in both directions — with the flag and without it — which is precisely
what the old test's pinning-to-a-literal-table could not do.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-08-15T14:20:02Z] Robert Architect:
  - Ruled **keep** on the `authors` flag — nothing to revert. Your reasoning holds, and the strongest form of it is one you had within reach: you did not depart from ADR-163 §2, you delivered its headline. "Derived from the playbook, never duplicated" was right; the prose scan and the co-located map both duplicated, in different ways. Yours is the only one of the three that puts the fact in the playbook. Also worth having: the `tech-writer`/`guide` case is your decisive argument, not the `reviewer`/`review` one — a whole-document scan recovers reviewer, but nothing recovers a lane the prose never states. Lead with that one next time.
  - ADR-163 amended in place: §2's mechanism rewritten to the declared flag, §5's exemption moved off the literal `manager` onto the designated default role (which needed amending too — as written it hardcoded the slug twice, so shipping your change against the old text would have left the ADR naming a mechanism we did not build), plus a dated entry under **Amendment note**. The `authors` key is declared in §2 as an extension of ADR-696's playbook override key space, with `related` refs both ways — the rule being that the decision owning a key's meaning hosts it, and the decision owning the key space gets the declared extension and a reciprocal ref. No separate ADR needed.
- [2026-08-15T14:42:43Z] Paul Reviewer:
  - Delta review of ST4 (18bb40d + e7b25d7), read at e7b25d7 in an isolated worktree. Verdict: sound, done, one low finding (F51 on REV-736). Implementation only; the ADR-163 mechanism question is the architect's per the brief.
  - The declared authors flag reproduces the product table exactly - READ against the eight guides in playbook.toml: product-owner {epic, feature}, tech-lead {task}, qa {bug}, architect {decision, guide}, reviewer {review}, tech-writer {guide}. The reviewer's lane is now declared on the review type's own guide rather than inferred across sections, which is the case the prose scan could not reach. DRIVEN falsifications: ignoring the flag reddens 9 cases across the unit and integration suites; example_assignee_slug returning the bundled literal reddens 3 meta cases; reverting the story prefix to US reddens 13, including the floor test. All restored byte-identical.
  - Goldens checked for correctness, not currency. The AGENTS.md golden's mission and responsibilities are built in the test from get_catalog() plus dev_role("python"), so they are derived rather than transcribed; I confirmed the same values arrive by the real path - sq init with both backends, then AGENTS.md read against sq role architect show --json and against roles.toml, all three identical. The manifest changed only the 0.12.3 block and only the touched templates; I recomputed every sha256 in that block against the tree and all match, with no template missing an entry and no earlier release entry touched. sq sync at e7b25d7 is a byte no-op, so the repo's own managed files really are in step with the templates.
  - The deleted meta guard is not a coverage loss - test_no_bundled_task_literal_in_generated_agent_text_templates.py was folded into test_generated_agent_text_names_no_bundled_vocabulary.py verbatim and WIDENED to cover workflow_static.md.j2 as a fifth template. for_skill is gone from src and tests together with no orphan reference. One probe smell worth knowing, not a defect: _probe_spec renames Superseded to Retired while the agent lifecycle already declares Retired, so the two collapse into one statuses entry - the assertions still mean what they say, but the probe spec is slightly incoherent.
  - Two observations that are not findings. ItemSpec's class docstring still says the capability flags "are not yet consumed by the engine", which category and subentity_kind now contradict. And is_lane_exempt(slug, None) cannot distinguish "the caller did not look" from "this squad has no live default role", so a squad that retired its coordinator exempts the bundled manager slug; the docstring calls that a legitimate state and the create would fail the agent_registered gate anyway, so I am recording it rather than filing it.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Sync and backend integrity: index, seeding, model, mission

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Sync and backend integrity: four findings, one shape — generated state and the index disagreed
with the durable record, and nothing said so. Each fix closes the gap at the surface that
*produces* the divergence, and each earns a report where there was silence.

## What changed

**The index is no longer allowed to lag the frontmatter it was built from.** `sync`'s
catalog merge (`_refresh_catalog_extra`) writes inside `store.transaction()` and commits the
merged item — markdown first, index commit last. Every roster consumer reads the index, so this
is what carries a project role override's title into `CLAUDE.md`, `AGENTS.md` and `sq list` on
the sync that merged it rather than after an unrelated `sq repair`.

**Every managed skill body a run writes ends that run indexed.** `sync` seeds bundled and custom
slugs, not only custom — which also removes the per-type migration a future release adding a
bundled type would otherwise owe. Anything still bare afterwards is named in sync's report.

**A value the agent host cannot render is reported, not dropped.** The Claude Code backend
returns a WARN-only notice on the `Artifact` when a declared model falls outside what its agent
frontmatter accepts; `_project_roster_item` returns those notices and `sync` prints them. It
refuses nothing — the override resolver stays the single refusal, so two layers can never
disagree about one value.

**A backend's generated output is output.** `RoleView` carries `mission` and `responsibilities`,
so the AGENTS.md backend no longer recovers a role's mission by string-matching a formatting
convention out of markdown it generated a step earlier. The responsibilities half of that
re-parse had been returning an empty list unconditionally, so that block of the section template
had never rendered.

## Two calls worth reading before the diff

**The exemption I was asked to bound, and did not.** `_is_legacy_skill_body` exempts any
unstamped slug-named skill body from `sq check`'s missing-`id` error, and its docstring claimed
that shape is pre-migration only. I tried two bounds (schema era; "has any stamped sibling") and
both are wrong for the same reason: `init`'s internal `_skip_skill_seed` hook manufactures the
defect shape on purpose, to hold the global counter still for the test corpus, so any
discriminator that reports the defect also reports that hook's output. The second bound turned
16 service tests and the `check` JSON golden red — and that golden's own fixture, `init
--no-seed-skills` plus a hand-authored `sq skill add`, is the counterexample in miniature:
stamped and unstamped siblings in one folder, legitimately. The report therefore lives on `sync`,
which knows it just wrote the body and just ran both seeders; `check` cannot know either. The
docstring now states the real width and points at the sync-side report. Narrowing it properly
means retiring `_skip_skill_seed`, which shifts every id assertion in the suite.

**PERMITTED_EXTRA_SKEW kept, for a different reason than it was written for.** With the catalog
merge now mirrored, its stated justification (this writer never opens a transaction) is false for
that half. It stays because a squad last synced by an older release already has a lagging index,
and comparing those keys would refuse the very sync that converges it. The prose says exactly
this now, so the next reader is not misled about which half is structural.

## Verification

Falsification as a battery: 10 breaks, one per fix and one per distinct mechanism, each patched
in place, the intended tests run, then the exact reverse substitution applied and the line
verified back. Never a `git checkout` — the fixes were uncommitted in those same files. All 10
went red.

Gates: pyright 0 errors, ruff check and ruff format clean, `sq check` clean. The full non-slow
suite was run in an isolated copy of HEAD carrying only these files (another agent was editing
`_workflow/_models.py` and `_services/_validators.py` in the shared tree throughout): 3474
passed, 6 skipped, 0 failed.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-08-15T14:43:11Z] Paul Reviewer:
  - Delta review of ST5 (b2ea93b), read at e7b25d7 in an isolated worktree. Verdict: sound, done, no new findings against it.
  - DRIVEN. F9 and F25 in one pass: a role override carrying title, mission and responsibilities reaches the index, CLAUDE.md's roster line and AGENTS.md's compiled section on ONE sync, with the responsibilities block rendering for the first time - I compared the AGENTS.md block against the role item's own extra and against roles.toml and all three agree. F10: init with a [selected] override dropping guide, then removing it, then sync, now stamps and indexes SKILL-000018-sq-guide; a stray slug-named body is reported by name on the next sync while check stays quiet as documented. The transaction shape is right - markdown write then db.add inside store.transaction(), whose contextmanager reaches _atomic_write only on a clean body, so an interruption leaves the skew direction repair heals.
  - Falsified independently: removing the transaction wrapper and the db.add reddens 7 across the integration, meta and skew-guard suites; dropping seed_bundled_skills from sync reddens 2; removing mission from RoleView reddens 13. All restored byte-identical.
  - The _is_legacy_skill_body reasoning CHECKED INDEPENDENTLY and it HOLDS, with one correction to the numbers. I implemented the "has any stamped sibling on disk" bound myself and ran it: the check JSON golden goes red exactly as described and for exactly the stated reason - its fixture is init --no-seed-skills plus sq skill add, which is stamped and unstamped siblings in one folder, legitimately - but tests/service stayed fully green at 1246 passed. The "16 service tests" figure matches removing the exemption OUTRIGHT, which I also ran: 14 service failures plus the golden. So the conclusion is right and the blast radius is attributed to the wrong bound. Caveat: this is MY implementation of the sibling bound, which may differ from the one that was tried.
  - Two notes, neither a finding. PERMITTED_EXTRA_SKEW's retained justification is the right call and the prose now says which half is structural. And sq sync exits 0 on the unindexed-body warning while sq check stays silent, so an adopter gating CI on check alone never sees it - documented, and the reasoning above is why, but worth knowing when a check-side report becomes available.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — VS Code client reads the spec it already fetches

<!-- sq:subtask:ST6:head -->
**Status:** 🟢 Done
**Assignee:** Ada Typescript
<!-- sq:subtask:ST6:head:end -->

<!-- sq:subtask:ST6:body -->
Two findings in the VS Code client, both the same shape: the client already fetches spec data from
`sq`, shape-guards it, and then renders from a hardcoded grammar or a hardcoded field name instead of
reading what it fetched. No Python file overlap with any other subtask, so this can run alongside ST1.

**F22 — the client id regex breaks any hyphenated declared prefix.** `ITEM_ID_PATTERN`
(`clients/vscode/src/domain/markdown.ts:36,40`) encodes an id *grammar* the engine does not enforce:
`ItemSpec.prefix` is a bare `str` with no validator, and `_models/_item.py:527` explicitly supports a
hyphenated prefix. Driven through the real production functions: with `prefix = "MY-WIDGET"`,
`workflow lint` says OK and `sq create` yields `MY-WIDGET-19`. In prose the preview then mangles the
visible text (`MY-` orphaned) and emits an affirmatively broken link to a nonexistent `WIDGET-19`; in
link form `FULL_ITEM_ID_PATTERN` rejects it, so `renderLink` drops the link entirely and an authored
cross-reference silently disappears. No ADR pins a prefix grammar, and ADR-696 calls re-prefixing an
adoption-time freedom. No new core surface needed: the client already fetches and shape-guards
`SqTypeCatalogEntry.prefix` and never reads it — resolve prefixes from that catalog instead of a
hardcoded character class, and keep the no-catalog path degrading to today's behaviour rather than
rendering nothing.

**F23 — the preview sub-entity head hardcodes the severity field code and label.**
`previewDocument.ts:602-603` prints `Severity: <value>` from a modelled `severity` property, bypassing
the generic badges machinery the item level uses correctly. With the finding kind's field redeclared as
code `impact` label `Impact`, every other surface honours it — item markdown, roll-up column,
`sq show`, the TUI — while the preview head shows no badge entry at all, and `severity: null` passes
the shape guard cleanly. Two halves, both in scope, and the split is deliberate:

- **First, no dependency.** The payload already carries a spec-resolved `badges` map per sub-entity
  (`_cli/_common.py:610`, `build_subentity_json` calling `resolve_badges`), which `SqSubEntity` does
  not model. Model it and render every declared field generically from that map, dropping the
  `severity` literal. `resolve_badges` returns `{code: value}`, so the visible text is the code —
  which is what `buildSubEntityHeadLine`'s own docstring already commits to ("plain text, not the
  spec's rendered badge glyph … same raw-code convention"). Keep the shape guard tolerant of an older
  `sq` payload that omits `badges`, exactly the way it already tolerates a missing `discussion`.
- **Then, after ST3.** The declared `Field.label` is unreachable today: sub-entity field vocabulary has
  no machine surface at all, since `sq workflow` exposes only types, collections, statuses and roles.
  ST3 adds a sub-entity field catalog carrying code, label and bound collection; once it lands, join it
  here so a relabelled axis shows its declared label rather than its raw code. Do not hold the first
  half back waiting for it, and do not hand-maintain a label map in the client as a stopgap — that is
  the same class of defect as the literal being removed.

Gate: `npm run` type-check, lint and vitest under `clients/vscode`, with the type-aware strict lint
intact — board notice 4 holds TypeScript at 6.0.3 for that reason, so do not bump it here. Add a test
per finding: a hyphenated-prefix id in both prose and link form for F22, and a relabelled sub-entity
field for F23.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-08-06T19:34:58Z] Ada Typescript:
  - F22 and F23 are Fixed on REV-736 (each finding body carries the mechanism, the driven evidence and its falsification). Gates from clients/vscode: typecheck clean, lint clean, 557 tests pass in 31 files.
  - F23 landed WHOLE, label half included, written against ADR-738 sections 3 and 5: badgeCatalog.buildSubEntityFieldBindings joins item.type -> type row subentity_kind -> kind row fields, and resolveItemBadges (the item-level function, unforked) renders it. The severity literal and the modelled severity property are both gone; no client-side label map. Until ST3 ships sq workflow subentity-kinds --json the fetch fails (driven: exit 2, No such command), bindings stay empty and each badge shows its raw field code — the value renders either way and the label switches on by itself when the catalog lands.
  - Two extra fixes the routing brief added, which are NOT filed findings on REV-736 (F22 and F23 are the only VS Code ones there) — see my comment on the review for both: Records now fails loud instead of blank, and the squad_dir TOML reader accepts every spelling sq does.
  - Leaving ST6 InProgress rather than Done for one reason: the label join has no live surface to verify against yet. When ST3 lands, add one skewCanary case plus a committed fixture for the kind row and the type row new key — adding it now would fail CI against a sub-command that does not exist. @manager your call whether that closes here or as a follow-up.
- [2026-08-06T21:40:59Z] Ada Typescript:
  - ST6 is complete. Canary landed now that ST3 shipped: three cases in test/canary/skewCanary.test.ts — the live kind row shape and its eight keys, subentity_kind present on every type row (null where a type hosts none), and the join itself, every non-null subentity_kind naming a kind the kind catalog publishes. Both catalog fixtures recaptured from live output; test/fixtures/subentity-kinds-catalog.json is new and type-catalog.json gained the two additive keys, which also let one unit test drive the real bundled join instead of hand-built rows.
  - F23 verified end to end, twice, not just against the ADR shape: this repo renders Status: Open · Severity: high with the label resolved from the kind row, and a separate squad whose override redeclares the finding field as code impact label Impact renders Impact: high with no occurrence of Severity — the finding own reproduction, now passing. Body updated on the finding.
  - lifecycle on the type row is deliberately NOT modelled, per your ruling: no resolver, no guard, nothing pointing at it. The reason is recorded in SqTypeCatalogEntry doc so a later reader does not complete it by accident. The canary asserts subentity_kind and stays silent on lifecycle.
  - I took F32 and marked it Fixed. It was cheap where I was: mermaidNodeId now escapes each non-alphanumeric character as _ plus four hex digits instead of folding, which also stops two ids differing only by hyphen-versus-underscore from merging into ONE diagram node before any click happens — the bigger half of that defect, and not what the finding reported. Encoder and the inlined webview decoder share one exported pattern constant and a test asserts the emitted page carries it, so they cannot drift.
  - Gates from clients/vscode: typecheck clean, lint clean, prettier clean, 584 unit tests pass in 31 files, 19 canary tests pass against live sq. Each fix falsified: restoring the fold turns 26 tests red, requiring a key sq does not emit turns the new canary cases red. Not committed. @manager ST6 done — three findings closed here in total (F22, F23, F32).
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Migration runners stop persisting state the spec never validates

<!-- sq:subtask:ST7:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
<!-- sq:subtask:ST7:head:end -->

<!-- sq:subtask:ST7:body -->
Two findings, one surface: a frozen migration runner writes durable frontmatter that the live model
would never write and that nothing validates afterwards, so the file lies while every gate exits 0.
Invariant 1 is the point of both. No overlap with any other subtask — this can run alongside ST1 and
ST6.

**Regrouping note.** This subtask was scoped as "TUI and migrations". The TUI glance line (F28) moved
to ST3, where both its root cause and its `tests/meta` guard already live; grouping it here would have
been grouping by "not the main surfaces", which is not a reviewable hat. What is left is one coherent
change.

**F17 — a migration writes legacy sub-entity statuses with no mapping to the spec.** The 0.2-to-0.3
runner (`_migrations/_v0_2_to_v0_3.py:123`) writes frozen legacy sub-entity statuses straight into
durable `subentities` frontmatter with no mapping to, and no validation against, the active spec. On a
0.2 squad whose override replaces the story lifecycle with `Pending`/`Doing`/`Complete`,
`sq migrate up` exits 0 and stamps `status: Done` — so the sub-entity sits in a state the active
lifecycle does not declare, every declared target is unreachable, and both `sq check` and
`sq workflow lint` exit 0 with nothing reported. Narrow but not closed: the override cannot be authored
via `sq override scaffold` at a stale schema, but a hand-written or template-copied
`.overrides/workflow.toml` *is* loaded and validated during `sq migrate up`. Migration runners are
frozen by convention, so the fix is a mapping-or-report at the boundary — plus the migration's `manual`
runbook text if a case genuinely needs the operator — not a rewrite of the historical runner's intent.

**F18 — migrations persist a derivable path key that then goes stale.** `_v0_4_to_v0_5.py:161` and
`_v0_8_to_v0_10.py:149` write `fm["path"]` into durable item frontmatter. `path` is fully derivable from
the file's own location, the live model never writes it, and `_reserved_item_keys`' own docstring calls
it model-only, never written to frontmatter. Nothing validates it, so it silently goes stale: after the
migration stamps `path`, `sq migrate repad` renames the file and leaves contents byte-untouched per its
own contract, so the committed frontmatter now lies while `sq check` exits 0. Secondary half, and the
reason this is not merely cosmetic: `_backfill_description` uses `cfm.get("path", "")` as its only
pointer-target source, so on any file written by a build that does not emit `path` — which is every
current build — the `.claude` pointer rewrite is silently skipped. Fix both: stop persisting the
derivable key, and derive the pointer target from the file's own location.

Standing rule for this pair: do not silence either half by widening a guard exemption. A guard should
assert that no migration runner writes a model-only key into frontmatter, and that no runner writes a
status the active spec's lifecycle for that kind does not declare.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-08-06T19:26:26Z] Elias Python:
  - F17 fixed: _v0_2_to_v0_3.py now checks the carried-forward status against the active spec (best-effort, read-only) and flags a mismatch with a dated discussion comment instead of writing it mute; value itself is never rewritten. MANUAL runbook updated.
  - F18 fixed: both runners stop writing fm["path"] (and strip a stale copy); _backfill_description derives the pointer target from the file's own location instead of a frontmatter path key that current builds never emit.
  - Falsified each fix (reverted, watched the new/strengthened test assert red, restored, green). Gates clean: pyright, ruff check, ruff format --check, tests/meta, targeted migration test modules (24 + 96 passing). sq check clean.
- [2026-08-06T19:42:37Z] Paul Reviewer:
  - Reviewed ST7 at b870482 (worktree-isolated; ST1/ST6 in-flight edits excluded). Verdict: NOT done. F18 mechanism verified and falsified; F17 works as built but rests on a false premise.
  - Both fixes drove clean on the shape families and the gates (pyright, ruff check, ruff format, tests/meta all green at the commit).
  - Blocking: F33 — the derived pointer target uses the OS separator, so the new backfill test fails on the windows-latest CI leg. One-word fix (as_posix).
  - Judgement call: F34 — reverting the frozen-runner spec read is the right close for F17, because sq check already runs the identical check on the identical spec. F35 and F37 fall away with it; F36 is a scope decision on F18.
  - Scope call on the validation-layer gap CONFIRMED correct: sq workflow lint and validate_against_index_fail_closed do validate against global spec.statuses, the runner cannot close that, and it belongs with F16. Note the gap is lint-only — sq check is not affected.
  - @tech-lead @python-dev
- [2026-08-06T19:58:31Z] Elias Python:
  - F33 fixed: _v0_4_to_v0_5.py's pointer-target derivation now uses a _posix_rel helper (.relative_to().as_posix()) instead of bare str(); pinned with a PureWindowsPath unit test that fails on Linux CI too on a regression (falsified: reverted, red; restored, green).
  - F34: reverted the F17 runner mechanism entirely per the reviewer's recommendation -- _v0_2_to_v0_3.py no longer threads the active spec; MANUAL kept, reworded to point at sq check (which already validates the identical predicate). F17's own body corrected to say the premise was wrong.
  - F35 auto-resolved by the revert (verified by reading _v0_5_to_v0_7.py/_v0_7_to_v0_8.py's sibling claims are true again). F37 marked WontFix -- moot, nothing left in the runner for the swallow to guard.
  - F36: my call was to strip the stale path key unconditionally in _backfill_description (not just accept the residue) -- reasoning on the finding body. Corrected F18's own body, which had overstated the original fix's reach.
  - All landed: pyright/ruff check/ruff format clean, tests/meta clean (106), targeted migration tests green (26 + 40), sq check clean. Each new/changed assertion falsified red-before/green-after.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T15:22:14Z] Olivia Lead:
  - Parentless, deliberately. A task parent must be the feature it implements; this implements no feature, it repairs defects across seven layers (integrity core, spec loader, CLI, templates, backends, migrations, VS Code client), so no existing feature covers it and a synthetic one would be a container, not a requirement. EPIC-538 is InProgress rather than Done (FEAT-714 is still open), so nothing is reopened; it is linked related. Same shape as TASK-674, the last review-fix task: parentless, addresses the review. Refs: addresses REV-736, related EPIC-538, related TASK-674 (ST1 extends its per-file degradation to search and inbox), related BUG-732 (the adjacent machine-surface gap ST3 sits beside).
  - Order of work is in the body with the reasoning per step. Two deviations from the read handed to me: ST3 goes before ST2, not after, because ST2 F16 validates through the _badges collection resolution ST3 fixes, and doing it the other way means writing F16 twice; and ST3 and ST2 must not run concurrently at all, since both edit the same regions of _workflow/_loader.py. ST1, ST6 and ST7 are the parallel wave; ST4 stays last for the golden regeneration.
  - Grouping I changed: F28 (TUI glance line) moved from the migrations group into ST3. The seventh subtask was scoped as TUI plus migrations, which grouped by "not the main surfaces"; F28 shares both its root cause and its tests/meta guard with F20/F21, and what is left in ST7 is one real hat, a frozen migration runner persisting state the live model would never write. Groupings I would not change: ST2 is large but reviews against one acceptance statement, and ST3 is three mechanisms with one cause, the CLI parameter surface baked from the bundled spec at import.
  - Flagged for op-pierre: ST3 adds a sub-entity field catalog to sq workflow, a new adopter-visible JSON surface, so that ST6 can render a declared label instead of a raw code. If that needs the architect first, ST6 second deliverable is the only work that waits; the first half of F23 needs nothing new. @manager over to you for dispatch.
- [2026-08-03T15:24:22Z] Catherine Manager:
  - Ruling on the question the tech lead raised, so ST3 and ST6 are not blocked on me: the sub-entity field catalog goes through the architect first, as one decision covering BOTH it and BUG-732 (no JSON surface exposes a type per-status lifecycle/transitions). Reason: they are adjacent published surfaces answering the same question -- what workflow vocabulary does sq expose machine-readably -- and designed separately they will diverge in shape. Published JSON shape is stability-contract territory, so it lands in an ADR rather than in a task.
  - Consequence for sequencing: ST3 fixes the flag surfaces as briefed and does NOT add the catalog; ST6 drops the severity literal now by modelling the badges map the payload already ships, which the tech lead confirmed is available today. Only the declared-LABEL half waits on the ADR. Nothing else in the task is gated. If the ADR lands before ST6 finishes, fold the label half in; if not, it is the one piece that carries past this task and it needs a named home at that point rather than sitting Open.
- [2026-08-03T15:39:00Z] Catherine Manager:
  - Correction to ST3s brief, from the architect while designing ADR-738 and verified by me at the source: the type-row subentity_kind key is LOAD-BEARING, not a convenience. SubEntity carries local_id, title and status and has no kind field, and the clients SqShowJson hands over a flat subentities array with no kind either -- so without that key the sub-entity kind catalog has no join key at all and F23s label lookup has no starting point. ST3 must ship the type-row key alongside the catalog, or ST6 cannot consume it.
  - Also updating my own earlier ruling on this task: I said only F23s code half was in scope and the declared-label half waited on the ADR. The architect resolved it the other way -- the split follows the consumer, so subentity-kinds plus the type-row key land in 0.13 (F23 needs exactly that catalog and nothing else, and ST3 already owns it), while lifecycles goes to 0.14 where BUG-732 already assigns itself. F23 therefore has NO residue: both halves ship in 0.13. ADR-738 is Proposed and op-pierre reads ADR bodies before accepting, so treat the catalog work as designed-but-not-yet-approved until then.
- [2026-08-06T19:02:28Z] Catherine Manager:
  - ADR-738 Accepted by op-pierre, with both open judgement calls ruled: states IS published (its ordering is the contract; a client computing off a frozenset reshuffles between runs), and the sub-entity kind row ships WHOLE in 0.13 rather than growing across two landings.
  - So ST3 gains a concrete deliverable it did not have when written: sq workflow subentity-kinds --json, one row per declared kind, all eight keys (subentity_kind, lifecycle, plural, local_prefix, container_heading, completion, maps_parent_story, fields), plus the two additive keys on the frozen type row -- subentity_kind and lifecycle. Follow ADR-738 section 2s row grammar exactly; it is descriptive of the four shipped catalogs, so deviating from it is a defect not a choice. The lifecycles catalog is NOT in this task: BUG-732s own body assigns itself 0.14 and nothing shipped consumes it.
  - ST6 then closes F23 with no residue: resolve the label through item.type -> type row -> subentity_kind -> kind row -> fields[].label, keyed by the code the sub-entity badges map already carries. Drop the severity literal and the modelled severity property; do not build a client-side label map.
- [2026-08-06T19:27:42Z] Catherine Manager:
  - ST7 landed and committed. Cross-subtask dependency it surfaced, recorded before it gets lost: the ST7 dev deliberately did NOT force the F17 fix into the migration runner, because the real gap is at the validation layer -- _collect_type_status_errors in _workflow/_loader.py validates a status against the GLOBAL spec.statuses set rather than against the owning type or kind own lifecycle. That is why an unreachable sub-entity status escapes both sq check and sq workflow lint. The runner now reports the mismatch; it does not and should not close the hole.
  - That validation-layer fix belongs to ST2, and it is the same root cause as F16 (the load boundary skipping adopter-declared badge fields via getattr by code). Whoever takes ST2 should treat the two as one mechanism -- validating declared vocabulary against the DECLARING scope rather than a global set -- not as two separate patches. Flagging because ST2s body was written before ST7 ran.
- [2026-08-06T19:44:53Z] Catherine Manager:
  - Correcting my own earlier note on the ST7-to-ST2 dependency, from the ST7 delta review: the unreachable-sub-entity-status gap is LINT-ONLY. sq check is NOT affected -- _services/_validators.py::_subentity_status_valid already computes ctx.spec.subentity_workflow(kind).states and reports it as an item-scoped error at exit 3. Only sq workflow lint misses it, because _collect_type_status_errors checks against the flat frozenset(spec.statuses). That narrows F16s blast radius and it narrows what ST2 has to build -- my earlier framing said both gates were blind and it was wrong.
- [2026-08-06T20:52:07Z] Elias Python:
  - ST3 done: the five flag-surface findings plus the ADR-738 catalog. Detail is on the subtask and in each finding body; this comment carries the cross-cutting parts.
  - ADR-738 deviation to rule on, flagged rather than hidden. Section 9 puts the type row lifecycle key in 0.14 alongside the lifecycles catalog ("each landing touches the frozen type row exactly once"), while section 5 and the dispatch I was given both name TWO additive keys now. I shipped both, because the dispatch is operative, an extra key cannot break a hand-trimming client while a missing one can, and the alternative touches the frozen row twice anyway. If the architect wants section 9 honoured literally, dropping "lifecycle" from _type_catalog plus its golden entry is a two-line revert. @architect
  - Adopter-visible for the writer: (1) NEW sq workflow subentity-kinds, human table by default and a bare JSON array under --json, one row per declared kind ascending kind name, keys subentity_kind, lifecycle, plural, local_prefix, container_heading, completion, maps_parent_story, fields; placeholder deliberately unpublished. (2) TWO new keys on sq workflow types --json rows: subentity_kind (the kind this type hosts, or null - the join key into the new catalog) and lifecycle (the machine it binds). Tier 2 for the sub-command, Tier 3 for both payloads, per ADR-738 section 8: docs/stability.md gains a Tier-3 row for the new catalog and the joins belong in docs/workflow.md. (3) BEHAVIOUR CHANGE an adopter can see: --priority and --no-priority are now hidden on a type declaring no priority field (still parse, still refused by the service gate), and --priority values are validated against the collection the type actually binds rather than the one named priority. (4) REFUSALS an adopter can now hit: a declared type or alias named after a bundled alias (e f t b d r g feat dec rev) fails spec validation, and a bundled alias an override renames away stops dispatching. I touched no docs/ or CHANGELOG.md - both out of scope for this subtask. @tech-writer
  - Two adjacent gaps I did NOT act on, noted so they are not rediscovered. First: sq create has no --set door, so a custom type whose only badge field is not called priority can only get a value via <type> N update --set code=value after creation - the create surface offers the dedicated priority sugar and nothing generic. Second: Service.add_finding still names severity in its signature; it now degrades correctly (omits the field when the kind declares none, refuses an explicit value the kind does not declare) but it is a test-only wrapper whose name outlived its axis. Neither is a REV-736 finding.
  - Working-tree note for the coordinator: another agent was editing _services/_base.py, _collab.py, _maintenance.py and their tests in this same checkout while I worked. Our file sets are disjoint and I touched none of theirs, but tests/meta/test_corpus_walking_reads_degrade_per_file.py was red mid-session from their in-flight state and green again later - if the full-suite run shows anything in that family, check there first, not here. @tech-lead @manager
- [2026-08-06T20:54:11Z] Elias Python:
  - Shared-tree consequence, recorded so the diff reads correctly: commit 5855b9a (the ST1 dev, in this same checkout) swept my src/squads/_cli/_main.py edit into their commit. That file is the F20 cross-type filter change (_build_badge_filters now calls parse_filter_badge_code). Nothing is lost and the content is exactly mine, but ST3 will not appear to own that file - the rest of ST3 is still uncommitted in the working tree. Also note both of us genuinely edited _main.py this session, so it is not a pure mis-stage. @tech-lead
- [2026-08-06T21:06:16Z] Pierre Chat:
  - Remove the mermaid graphs from the workflow cheatsheet. They are ugly. I will think about a visual way later -- if the lifecycle workflow surface is enough for agents, that is all I ask.
- [2026-08-06T21:06:17Z] Catherine Manager:
  - Folding this into ST4, which owns the template tree and the golden/manifest regeneration and lands last -- doing it separately means regenerating both twice. Scope: both mermaid blocks in _rendering/templates/workflow.md.j2, the hierarchy flowchart around line 88 and the per-type stateDiagram-v2 around line 143, plus the mermaid_id filter and the lifecycle_states_in_order/lifecycle_edges template globals if nothing else consumes them after the removal (check, do not assume).
  - Answering the operators condition from the code: agents are already covered and one of the two is actively harmful to them. The lifecycle diagrams are guarded by for_skill and never reach the agent-facing skill -- the templates own comment says agents read the skill as raw text, mermaid does not render there, and the one-line lifecycle table conveys the same statuses and transitions. The HIERARCHY flowchart has no such guard, so agents currently receive raw mermaid markup in their skill while the prose Hierarchy bullets directly above already say the same thing.
  - Known cost, accepted rather than overlooked: the ## Type lifecycles table linearizes a machine into a chain, which is lossy against the real edge set, and the stateDiagram was the only place the actual transitions were visible. Its machine-readable replacement (sq workflow lifecycles, transitions as from/to pairs) is 0.14 per ADR-738. Between now and then exact edges are discoverable only by attempting a transition and reading the refusal, which does name the legal targets. Keep the ## Type lifecycles table -- it is what agents actually read.
- [2026-08-06T21:44:09Z] Catherine Manager:
  - ST2 STOPPED MID-WORK by op-pierre (quota). Revive the same agent by id rather than spawning fresh -- the working state is uncommitted and only that agent knows what is verified. Agent id: ab2ce9453977a904f. Its last reported position, verbatim: "Now the F29 test for the inert-declaration half, then falsification."
  - State on disk, deliberately NOT committed because it is unfalsified and its gates were never run: 14 modified files under src/ (_cli/__init__.py, _cli/_common.py, _cli/_role.py, _context.py, _index/_store.py, _overrides/_service.py, _roles/_catalog.py, _roles/_loader.py, _roles/_resolver.py, _services/_service.py, _services/_validators.py, _specmerge.py, _workflow/_loader.py, _workflow/_models.py), 3 modified tests, and 3 new integration tests (a_broken_override_is_refused_on_every_surface, a_malformed_override_shape_becomes_a_lint_finding, a_renamed_subentity_plural_is_reported_against_the_corpus). All eight findings F1 F4 F11 F12 F13 F16 F19 F29 are still Open on REV-736 -- he had not marked any Fixed, so the board is honest about what is proven, which is nothing yet.
  - Two things carried in his brief that must survive the revive. First, a stray ticket reference at _workflow/_loader.py:287 -- "(ADR-49)" in a comment -- trips the stray-ticket-reference meta guard; the reasoning stays, the ID goes. Second, he renamed or added _cli/_common.require_loadable_spec mid-edit and sq was transiently unrunnable for other agents; that half-landed state may still be on disk. Nothing else is editing this tree now, so a resumed agent owns it cleanly.
- [2026-08-15T12:52:40Z] Elias Python:
  - ST2 landed: F1, F4, F11, F12, F13, F16, F19 and F29 all Fixed on REV-736, each with its own body carrying the driven evidence, the fix, the falsification result and the tests. The subtask body carries the cross-cutting shape. This comment carries what a reader of the diff needs that is not in either.
  - Falsification, done as a battery rather than case by case: 13 breaks, one per fix (and one per distinct mechanism where a finding had two), each patched in place, the intended tests run, then the exact reverse substitution applied and the file verified byte-identical. Never a git checkout — the real fixes are uncommitted in those same files. Two breaks came back STILL GREEN, which is the whole reason for doing it: my array-shape test asserted only 'did not raise', and a string IS iterable, so the unguarded walk validated 'o' as a field and reported field[0] — a refusal, just a nonsensical one; and my unknown-role-key test passed with the top level left open, because the model's own extra=forbid refuses it anyway. Both tests now assert the property only the fix provides (the container named and no invented element index; the accepted key set named in the message). All 13 red afterwards.
  - One design call I made against my own first implementation, because it is the kind of thing that reads as a regression in review. F1 was first built as a root-callback hard stop with an exemption list. It broke tests/integration/test_check_reports_its_config_findings_when_the_corpus_cannot_load.py and the repair-under-a-shrunk-collection cases — sq check and sq repair are BUILT to open the service, catch the refusal and report it as a finding, and a callback gate pre-empts that. Replaced with: the refusal lives on get_active_spec() and open_service, which are the surfaces that answer questions about the squad. No exemption list to maintain, the degradation paths keep working, and lint stays reachable because it consults neither.
  - Second one, same category. F16's per-lifecycle status check was first folded into the fail-closed cross-check. That made an item resting on an unreachable status hard-stop every command under an override — and the remedy is a per-item --force move, so the item became repairable only by deleting the override first. Split into two collectors: the fail-closed one keeps the flat set (can the spec still READ this corpus), and a new lint-only one reports the unreachable case (can this entity ever leave this state). Check and lint now agree; nothing new refuses at load.
  - ADOPTER-VISIBLE, for the writer — five, in descending order of blast radius. (1) A workflow override that fails to load is now a hard stop on EVERY surface, not just the ones that open a service: sq workflow types/statuses/collections/roles/subentity-kinds and the cheatsheet used to exit 0 describing the bundled spec. The message names the file, the key-level cause and the action, and says sq workflow lint is what still runs. sq check and sq repair still run and report it as a finding. (2) A role override is now validated: an unknown key, a wrong type, a model outside the whitelist and a slug disagreeing with the filename are all refused by name, where they used to be discarded or stored; can_spawn = "false" now means false. The append idiom responsibilities = ["$(*self)", ...] now works in a role TOML. (3) NEW sq check error: an item whose file lacks the container marker its kind's declared plural names — fires when a plural is renamed against an existing corpus, in either direction. (4) sq workflow lint now reports an item or sub-entity resting on a status its own lifecycle cannot reach, which sq check already reported. (5) A misspelled [selected] keep-entry, and a ref_rules kind outside the vocabulary, are now refused at load instead of silently dropping the key / carrying an inert rule. The scaffolded workflow override activates as written again (it declared a retired key) and now demonstrates role. I touched no docs/ and no CHANGELOG.md. @tech-writer
  - Gates, all with --all-extras: pyright 0 errors, ruff check and ruff format clean, sq check clean. tests/meta + unit + service + cli + integration + tui: 3443 passed, 1 skipped, 0 failed. Full suite left to the main loop as briefed. Working tree is uncommitted: 15 modified src files, 3 modified tests, 7 new test modules (4 tests/meta guards, 3 integration + 1 unit behavioural). @tech-lead @manager
- [2026-08-15T13:03:12Z] Catherine Manager:
  - Reopening ST2 for one finding found AFTER the decomposition was written. QA verified EPIC-538 outcome by outcome and found outcome 7s consistency hard-stop does not exist -- filed as REV-736 F46 (high). It belongs in ST2 rather than a new subtask: same theme (an override is honoured or reported, never silently ignored), same file (_workflow/_loader.py), same family as F16 (validate a declaration against its declaring scope, not a global set).
  - This is the finding that would have closed EPIC-538 wrongly for the second time. Its acceptance bullet and ADR-541 both require the hard-stop verbatim, FEAT-569 was scoped narrowly enough that it never carried it, and nothing on REV-736, REV-726 or the bug list tracked it. Worth noting as a pattern: both wrong closes of this epic came from an outcome bullet with no feature actually carrying it, not from incomplete children.
- [2026-08-15T13:20:37Z] Elias Python:
  - F46 fixed and closed; ST2 is complete again. The finding body carries the full reasoning — this comment carries what a coordinator needs plus two corrections to the report and one defect I found in my own earlier work.
  - The fix: a Plane-1 check in WorkflowSpec._validate written against a type's EFFECTIVE VALIDATOR SET rather than its category name. That framing is the design call worth reviewing — read across the tree, every category consumer outside the validator bundle branches only on 'roster vs not', so work and records differ in exactly one respect: which validators they turn on. Writing the check that way makes it category-agnostic (it catches a work type that adds no_parent to its own validators while declaring parents, no reassignment involved) and removes any second table to keep in step. Two clauses: a type whose effective set includes no_parent may not declare parents/parent_required; a type declaring a subentity_kind must keep at least one validator whose subject is that kind. COMMON_CORE/CATEGORY_BUNDLES/effective_validator_names moved from _services/_validators.py to _workflow/_models.py so the Plane-1 pass resolves the same set the engine runs — same layering argument that already put VALIDATOR_NAMES there.
  - CORRECTION 1, driven: QA case 3 (guide -> work) is NOT a defect and I left it loading. Its basis — 'a lifecycle that never reaches Done' — is not expressible from any declared property. Read off the bundled spec: role 'done' is settled=True hidden=True live=False, and so are 'retired' and 'superseded'; identical on every declared flag, differing only in color, which is presentation. Distinguishing a burn-down terminal needs either a literal role-name binding (forbidden outright by the governing semantics decision) or a new declared flag on the status role — a spec-format change nobody has decided. Driven besides: guide-as-work declares no parents, no parent_required, no subentity_kind, so the work bundle adds only vacuous checks; it creates, transitions to its settled state, sq check clean. Nothing it declares is silenced. Case 2 IS still caught, but by the sub-entity clause (review hosts findings), not by the lifecycle argument. If the team wants the burn-down axis validated, that is a new declared flag and an architect call — flagged, not folded in.
  - CORRECTION 2, driven: half the reported consequence does not hold. 'sq create task with no parent now succeeds where it was previously required' — it succeeded BEFORE the reassignment too. parent_required is not a create gate at all; it is read only by subtask_story_mapping and for hint text. What the reassignment actually killed is the parents allowlist: --parent FEAT-n goes from accepted to 'task takes no parent' while the spec still reports parents=['feature']. The finding's core is untouched and fixed; that one direction was overstated, and my test pins the accurate behaviour rather than restating the claim. Separately: parent_required being much weaker than it reads is a REAL pre-existing gap that nobody owns — same inert-declaration family as F29. Not opened by me; @tech-lead worth triaging.
  - DEFECT I INTRODUCED IN F1 AND FIXED HERE, found by writing the F46 test rather than by review. sq create <type> and sq <type> <n> update re-derive --priority's help from the active spec inside Click's get_params, which runs BEFORE the command body and so outside the boundary that turns a SquadsError into a clean message. Once get_active_spec started refusing, that hook escaped as a full traceback — the one outcome the refusal contract rules out — on a squad whose only problem was a bad override. The help refresh is now fail-soft (contextlib.suppress): presentation degrades to its baked text and the refusal fires from the command body. Same division the completion/help path already uses. Two regression tests: no traceback from create/update, and --help still renders. Worth knowing that F1's blast radius reached a parse-time hook I had not considered.
  - Falsification: 5 breaks — the check not called, each clause disabled separately, the check rewritten against the category NAME instead of the validator set, and the help refresh allowed to raise. All 5 reddened the intended tests; each reverted by exact reverse substitution with the file verified byte-identical, never git checkout.
  - ADOPTER-VISIBLE for the writer, one item: a workflow override that moves a built-in between work and records is now REFUSED AT LOAD if the result contradicts itself — a type left with parents/parent_required under a category that forbids a parent, or left hosting sub-entities under a category that validates none. Reassignment itself is unchanged and still supported in both directions; the refusal names the type, the category, the offending field(s), and the ways out (drop the field, choose another category, or name the checks you want in the type's own validators list). @tech-writer
  - Gates with --all-extras: pyright 0 errors, ruff check and format clean, sq check clean. tests/meta + unit + service + cli + integration + tui: 3492 passed, 1 skipped, 0 failed. Full suite left to the main loop. NOTE ON THE SHARED TREE: another dev is live in _services/_maintenance.py, _itemfile.py, _base.py and the backends. I touched none of those. Mid-run I saw two pyright errors and one test failure in their in-flight files, both gone by the time I re-ran, and one xdist 'different tests collected between workers' abort caused by files appearing during collection — if the full-suite run shows anything in that family, check there first, not here. @tech-lead @manager
- [2026-08-15T13:28:12Z] Elias Python:
  - ST5 landed: F9, F10, F24 and F25 all Fixed on REV-736, each with its own body carrying the re-driven evidence, the fix, the falsification result and the tests. The subtask body carries the cross-cutting shape and the two judgment calls. This comment carries what a reader of the diff needs that is in neither.
  - ONE FINDING'S GUARD WAS NOT DELIVERED AS ASKED, deliberately. F10's brief required bounding the _is_legacy_skill_body exemption so an unstamped skill body stops reading as clean. I tried two bounds (schema era; 'has any stamped sibling on disk') and both are wrong for the same reason: init's internal _skip_skill_seed hook manufactures the exact defect shape on purpose, to hold the global counter still for the test corpus. Every discriminator that reports the defect also reports that hook's output — the second bound turned 16 service tests and the check JSON golden red, and that golden's own fixture (init --no-seed-skills plus a hand-authored sq skill add) is a folder with stamped and unstamped siblings side by side, legitimately. So the report moved to sync, which knows it just wrote the body and just ran both seeders; check cannot know either. It covers the class, not just the slugs a vocabulary names. Bounding it properly requires retiring _skip_skill_seed, which shifts every id assertion in the suite — a separate piece of work, not ST5's.
  - Falsification, as a battery: 10 breaks, one per fix and one per distinct mechanism, each patched in place, the intended tests run, then the exact reverse substitution applied and the line verified back. Never a git checkout. All 10 went red — no repeat of ST2's two still-green tests. The ones worth naming: dropping seed_bundled_skills from sync fails the widened meta guard AND the restored-type case; discarding _unindexed_skill_bodies' return instead of appending it fails only the residue case, which is why they are two separate breaks; and computing model_drop_warning without attaching it to the Artifact fails separately from sync not collecting it, because those are two different silences.
  - SHARED-TREE NOTE for the coordinator. Another agent was editing _workflow/_models.py, _services/_validators.py and two of their tests in this same checkout throughout my session — our file sets are disjoint and I touched none of theirs. Early on I used a git stash round trip to isolate a test failure and it swept their in-flight work in and back out; the pop was clean and their content is intact (verified by diff), but that was a mistake in a shared tree and I did not repeat it. Everything after that was verified in an isolated copy of HEAD carrying only my files. If anything in the validator/category-bundle family shows up in the full run, it is not from here.
  - Gates: pyright 0 errors, ruff check and ruff format clean, sq check clean. Full non-slow suite in the isolated copy: 3474 passed, 6 skipped, 0 failed. I did not run the full suite in the working tree, as briefed — @tech-lead @manager, that is yours with --run-slow. Working tree from me: 7 modified src files, 2 modified test files, 4 new test modules, 1 renamed meta guard.
- [2026-08-15T13:28:28Z] Elias Python:
  - ADOPTER-VISIBLE, for the writer — four, in descending order of blast radius. (1) A project role override's title/model/mission now reaches every generated file on the sync that merges it. Previously it landed in the role item's .md but not in .squads.json, so CLAUDE.md, AGENTS.md and sq list kept showing the bundled value until an unrelated sq repair happened to rebuild the index — at which point the next sync changed the rendered roster with no visible cause. An adopter upgrading will see one roster change on their first sync: the correction they had already declared. (2) AGENTS.md now renders each role's RESPONSIBILITIES under its mission. That section has always been in the template and had never once rendered — this is new content in a generated file, not a formatting change. (3) NEW sq sync warning: a role declaring a model Claude Code's agent frontmatter does not accept (anything outside sonnet|opus|haiku|inherit) is named, with the value, and told that the generated pointer omits the model line so the agent runs on the session default. Reachable via sq dev add --model, an import, or a migrated corpus; a role OVERRIDE naming one is refused outright instead (that refusal is ST2's). (4) NEW sq sync warning: a skill body under the skills folder that no SKILL item indexes is named, with the note that sq repair cannot recover it (no frontmatter to rebuild from). Same command: sq sync now also seeds bundled skills, so a type restored after init gets its skill indexed instead of sitting invisible — sq skill <slug> show used to exit 1 on it forever. I touched no docs/ and no CHANGELOG.md. @tech-writer
  - Two adjacent gaps I did NOT act on, noted so they are not rediscovered. First: sq dev add --model and sq role activate call generate_role_entry directly and discard the returned Artifact, so a dropped model is reported on the NEXT sq sync rather than at the moment of the add — wiring them means changing their return signatures up through the CLI. Second: sq init's ensure_scaffold writes the AGENTS.md placeholder and the very next inject then warns that the file 'had pre-existing hand-written content with no squads markers' — squads warning about its own scaffold, on every fresh init with the agents_md backend. Neither is a REV-736 finding.
- [2026-08-15T13:30:28Z] Elias Python:
  - Shared-tree consequence, recorded so the diff reads correctly: commit d07de4c (authored while I worked) swept my staged git-mv of the seeding meta guard into itself — tests/meta/test_init_and_adopt_seed_both_bundled_and_custom_skills.py is committed as tests/meta/test_every_skill_seeding_entry_point_seeds_bundled_and_custom.py with zero content change, because the rename was staged before I rewrote the file. Nothing is lost: the widened content (init, adopt AND sync) is still uncommitted in my working tree under the new name. So that commit appears to contain a bare rename with no reason attached; the reason is F10.
  - Re-verified after that commit, not before it: the isolated full non-slow suite was re-run against the CURRENT HEAD carrying only my files — 3474 passed, 6 skipped, 0 FAILED. pyright, ruff check, ruff format and sq check re-run against the live working tree, all clean.
- [2026-08-15T13:31:21Z] Catherine Manager:
  - Recording a mistake of mine so it is on the record rather than only in an agent report: commit d07de4c swept the ST5 devs staged git mv of the seeding meta guard, so that commit carries a bare rename with no reason attached. The reason is F10 and the widened content landed properly in b2ea93b. Fourth time this session I have swept another agents in-flight work by staging a directory rather than named paths; the history condensation will absorb it, but the habit is the defect.
- [2026-08-15T14:08:39Z] Elias Python:
  - ST4 landed, the last subtask. F6, F7, F8, F14 and F26 all Fixed on REV-736, each with its own body carrying the driven evidence, the fix, the falsification result and the guard. The subtask body carries the cross-cutting shape. This comment carries what a coordinator needs plus three things a reader of the diff will not otherwise see.
  - F7 WAS ALREADY DONE, template half included — read, not assumed. Commit 8473abf ("took the operator name out of shipped source") had already moved greeting_skill.md.j2:27,37 and claude_section.md.j2:50 onto the Alice placeholder AND moved the worked greeting to a fictional payments API, along with all six CLI-help sites the finding names. My brief said the template half was the remainder; it was not. A grep for the name and slug across src/, docs/, README.md and PYPI.md returns nothing. What I added is the check that was missing: a meta guard that derives the forbidden identities from THIS squad operator roster on disk, so a person registered later is covered with no edit.
  - F14 DESIGN CALL worth reviewing, because I went against the primary mechanism ADR-163 section 2 names. That ADR offers a prose scan of the guides do bullets for "sq create <type>" as the mechanism and the declarative map only as a fallback. The scan does NOT reproduce the product table: the create verb is not always in its own type section (the reviewer sq create review lives in the task playbook), and tech-writer authors guide per the table while its guide carries no create verb at all — so a scan would have silently dropped that lane. I added a declared authors flag on the playbook role guide instead. That satisfies the ADR real invariant (one source, in the playbook, test-locked to it), makes the lane overridable by construction, and avoids the naming-convention-standing-in-for-a-declaration shape this whole sweep is about. It is an additive key on the playbook schema; the bundled document declares it on eight guides and reproduces the old table exactly, so bundled behaviour is unchanged. @architect if you want the prose scan instead, the flag is a clean revert.
  - TWO CONSEQUENCES BEYOND THE FINDINGS. First, is_lane_exempt no longer names manager: it takes the squad own is_default role slug (ServiceCore._default_role_slug reads it off the live roster, falling back to the catalog designation), so sq role <slug> default moves the exemption with it. Second, authoring_owner now takes an optional live slug-to-title map, consulted ONLY when the catalog has no entry — a role declared solely in .overrides/roles/ now gets its authoring bullet instead of its type silently losing one. The catalog stays first on purpose: its titles are the lower-case sentence forms the prose is written around, and a live RoleView carries the display-cased form. I found that by watching a test go red, not by reasoning.
  - MERMAID REMOVAL, per op-pierre. Both blocks gone from workflow.md.j2, plus the mermaid_id filter and the lifecycle_states_in_order/lifecycle_edges globals — checked that nothing else consumed them (sq graph mermaid export has its own separate _safe_id in _services/_refs.py, untouched, and F44 depends on that one, not on what I deleted). The Type lifecycles table stays. One residue I did NOT touch because it is the client dev area and I cannot run the TS gate: clients/vscode/test/fixtures/workflow-raw.txt is a frozen copy of the old sq workflow --raw output, and its test is named "renders the real sq workflow --raw fixture ... with every diagram live". The mermaid rendering path it covers is still genuinely needed for sq graph, so the honest fix is to re-point that test at a graph fixture rather than refresh this one. @typescript-dev @tech-lead.
  - REGENERATION, all in this one pass as briefed: templates_manifest.json (0.12.3 entry rewritten, all 12 prior release entries preserved), the three text goldens (workflow_cheatsheet, workflow_cheatsheet_raw, claude_md_section, agents_md_section) and playbook_spec.json. I also ran sq sync, so the repo own CLAUDE.md, the ten role files and the squads/sq-memory skill bodies now carry the new text — leaving them stale would have made the next sync an unexplained diff. The AGENTS.md golden now pins REAL mission/responsibilities instead of empty strings: ST5 made that block reachable for the first time and a golden pinned on empty values would have kept it dead. It renders correctly.
  - Gates with --all-extras: pyright 0 errors, ruff check and ruff format clean, sq check clean. tests/unit + service + cli + integration + meta + tui: 3516 passed, 1 skipped, 0 failed. Full suite left to the main loop with --run-slow as briefed. Falsification: 9 breaks — 4 on the lane derivation (bundled laned_types, bundled allowed_create_types, ignoring the authors flag, the hardcoded manager exemption) and 5 on the templates (assignee slug, dropped status, superseded status, story prefix, memory path) — every one reddened its intended tests and every one was reverted by exact reverse substitution with the file verified byte-identical. Never a git checkout. @tech-lead @manager
- [2026-08-15T15:47:09Z] Catherine Manager:
  - All seven subtasks Done, all 51 REV-736 findings dispositioned, review Approved as second party. Full suite 3603 passed with --run-slow, pyright/ruff/format clean, sq check exit 0.
<!-- sq:discussion:end -->
