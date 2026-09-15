---
id: TASK-936
sequence_id: 936
type: task
title: Enumerate repair-corridor consumers; widen the writer scan (F23, F25)
status: Done
parent: FEAT-906
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
- REV-926:addresses
subentities:
- local_id: ST1
  title: Enumerate repair-corridor consumers, fix F23
  status: Done
  story: US5
- local_id: ST2
  title: Widen the AST filter beyond ast.Attribute (F25 gap 1)
  status: Done
  story: US5
- local_id: ST3
  title: 'Scan template literals for sq:view: tags (F25 gap 2)'
  status: Done
  story: US5
- local_id: ST4
  title: Make the gate check assert the gate, not a decoy mention (F25 gap 3)
  status: Done
  story: US5
created_at: '2026-09-10T08:27:49Z'
updated_at: '2026-09-10T09:34:52Z'
---
<!-- sq:body -->
## Scope

Closes REV-926's fourth round the way the reviewer's own diagnosis prescribes: family A (the
view-tag writer enumeration) is genuinely closed by construction — reverting the fix reddens
exactly the right row — and family B was only approximated, with a hand-written list of three
command names in place of an enumeration. This task finishes the method rather than changing it:
enumerate the fourth family-B consumer the hand-written list missed (F23), then close the three
gaps the reviewer found in family A's own closure mechanism (F25) so the guard's claim matches
what it actually checks.

- **ST1 — Enumerate every consumer of `RepairResult`/`SyncSkips`; close F23 by construction.**
- **ST2 — Widen the view-tag AST filter beyond `ast.Attribute` (F25, gap 1).**
- **ST3 — Bring template-literal tag writers into the scan (F25, gap 2).**
- **ST4 — Make the gate-check assert the gate, not a decoy mention (F25, gap 3).**

## ST1 — Enumerate every consumer of RepairResult/SyncSkips; close F23 by construction

`RepairResult` (skipped/unreadable) and `SyncSkips` (backfill_skipped) are read by four CLI
consumers, not the three TASK-933's parity test table-drove: `sq repair`
(`_cli/_main.py::repair`, the reference implementation), `sq migrate up`
(`_cli/_migrate.py::migrate_up`), `sq sync` (`_cli/_main.py::sync`), and `sq adopt`
(`_cli/_main.py::adopt`, reading `AdoptResult.repair` — `_services/_service.py:246` /
`_services/_results.py:187`). `adopt` reads `result.repair.strip_notice()` and nothing else:
`skipped` and `unreadable` are both silently dropped, and the command exits 0 regardless.

**The enumeration.** A `grep -rn` for every attribute access on a `RepairResult`/`AdoptResult`/
`SyncSkips` value across `_cli/` (`.repair.`, `.skipped`, `.unreadable`, `strip_notice(`,
`backfill_skipped`) is the same shape as TASK-933's `markers.view_tag(` scan — enumerate sites,
not commands, because a consumer that never mentions any of those names would be invisible to a
command-name list the way `sq adopt` was. Classify each site once, in one test, as one of
`reports-both-channels` / `reports-neither-channel` (a failing classification the fix must clear)
/ `not-a-reporting-site` (the service-layer callers that just build the result), and assert the
set of sites found **is** the set classified — a fifth consumer added later without a
classification fails the test outright, the same contract TASK-933's test gives an eighth
`markers.view_tag(` writer.

**The fix.** `sq adopt` gains the same two reporting loops `sq repair` already has (`skipped`,
`unreadable`), identical wording, printed after the "squads adopted" summary. Exit code: `adopt`'s
own sweep is the corpus repair sweep under a different name — its own code comment says so ("this
is the only route an existing folder of squads-native markdown takes — no schema stamp to
migrate, no repair anyone ran") — so match `sq repair`'s and (per F15/F20) `sq migrate up`'s exit
contract rather than `sq sync`'s: exit 1 when either channel is non-empty. Unlike `sq sync`,
`adopt` has no pre-existing 0-exit skip channel this would collide with. `adopt`'s closing summary
line should point at `sq repair`, not `sq check`, since F13 already established `sq check`
structurally cannot see this state.

**The test.** Extend (or sit beside) `tests/cli/test_repair_corridor_message_and_exit_parity.py`
with a fourth row, `(adopt, skipped)` and `(adopt, unreadable)`, built the way F23's reproduction
built it — a marker-shaped role body / an unreadable item file, present **before** `sq adopt` runs
on the folder — asserting `sq adopt`'s printed wording matches `sq repair`'s for the same input
and that its exit code is 1. Must fail today: `sq adopt` prints nothing about either channel and
exits 0.

**Driven acceptance, reviewer's exact repro:** a squads-structured folder with the manager role's
`sq:body` holding marker-shaped content, adopted — before the fix, `sq adopt` is silent and exits
0, `sq check` is clean, `sq role manager show` renders the stale content; after, `sq adopt` names
the skip and exits 1, matching `sq repair` on the identical corpus.

## ST2 — Widen the view-tag AST filter beyond ast.Attribute (F25, gap 1)

The enumeration test TASK-933 added
(`tests/meta/test_view_tag_writer_sites_are_exhaustively_classified.py`) discovers writers by
matching `ast.Call` whose `func` is an `ast.Attribute` with `attr == "view_tag"`. A bare-name
call — `from squads._models._markers import view_tag`, then `view_tag(name)`, an `ast.Name` — is
invisible to it; the reviewer added a seventh writer in that style in an isolated worktree and all
six tests passed.

**Fix.** Widen the discovery filter to also match `ast.Call` whose `func` is an `ast.Name` with
`id == "view_tag"`. No behaviour change to any of the six existing (correctly-classified) sites —
all import `_markers` aliased (`from squads._models import _markers as markers`) and call
`markers.view_tag(...)`, the attribute form — this only adds the sibling shape.

**The test.** A regression case: construct a synthetic module (a string fixture, not a file
committed under `src/`) containing a bare-name `view_tag(...)` call, run the scanner against it
directly, and assert it is found. Must fail today — the reviewer's own driven repro (a bare-name
seventh writer passing all six tests) is the falsification; reproduce it as the red case before
the fix, confirm green after, then remove the constructed writer — it is a test fixture, not a new
real site, and must not be left under `src/`.

## ST3 — Bring template-literal tag writers into the scan (F25, gap 2)

The scan globs `*.py`, so a literal `sq:view:<name>` tag written directly into a `.j2` template is
invisible by construction. One exists today: `templates/agents/role.md.j2:2`, the creation
scaffold's static `sq:view:role_definition` tag — the same site `ROLE_DEFINITION_VIEW_NAME`'s own
docstring already points at. It is not a live defect (F12's verification established
`_create_core` unconditionally overwrites a role's body region on the one path that renders this
template, so the static tag can never survive as a value), but a *second* template writer would be
silent — driven: a static tag added inside `agents/skill.md.j2`'s `sq:body` region leaves all six
of TASK-933's tests green and survives into every skill `sq skill add` creates afterward, because
nothing overwrites a skill's body region the way `_create_core` does a role's.

**Fix.** A second scan, over `_rendering/templates/**/*.j2`, for a literal `sq:view:` tag (open
marker form). Classify each hit the same way the Python scan classifies a call site — the one
bundled hit (`agents/role.md.j2:2`) gets `neutralized-by-overwrite`, citing `_create_core` and the
two facts F12's verification drove (the overwrite is unconditional for `ROSTER_ROLE`, and
`pristine_body` — `_template_for`'s only other consumer — is unreachable for a role because
`set_body` raises first). A template hit with no classification fails the test outright, the same
contract as the Python scan.

**The test.** Extend the same meta test module with the second scan and its own known-positive
check (the false-zero rule applies here too — collapse whitespace before matching, and validate
against a constructed positive first, since a template tag can span a line-wrap the way the Python
call can). Must fail today for a constructed second template writer (`agents/skill.md.j2`, driven
by the reviewer): add a static `sq:view:milestone_rollup` tag to that template's body region in
the test fixture, confirm the extended scan catches it as unclassified, then confirm the real
corpus (just `agents/role.md.j2`) passes with its one classified hit.

## ST4 — Make the gate-check assert the gate, not a decoy mention (F25, gap 3)

`test_a_gated_sites_declared_target_actually_carries_a_views_gate` proves a
`\bspec\s*\.\s*views\b` mention exists somewhere in a `gated` site's source, not that the mention
guards the seed. Driven: with the three real gates removed and one *unused* `in spec.views`
mention added to each target, all six tests still pass — a plausible refactor (a function
computing a declared-views list for one purpose while seeding a tag for another) satisfies the
proxy.

What actually catches that decoy today is the *behavioural* test
(`tests/service/test_skill_creation_seeds_no_tag_for_an_undeclared_view.py`), not the meta one —
three of its rows go red on the same reverted build, including the finding-count growth assertion.

**Ruling.** Strengthening the source-text proxy further chases a shape that stays gameable (the
next plausible refactor looks just as innocent) — the honest fix is to stop claiming the meta test
verifies the gate *works* and make it verify the gate is *provably tested*, deferring enforcement
to the named behavioural test rather than re-deriving it.

**Fix.** Each `gated` classification entry gains a required `behavioural_test` field naming the
exact test that falsifies its gate (module path + test function, e.g.
`tests/service/test_skill_creation_seeds_no_tag_for_an_undeclared_view.py::test_repeated_skill_creation_under_a_dropped_view_adds_no_check_findings`).
The meta test asserts that name resolves to a real, collected test (imports the module, confirms
the function exists) — it does **not** run it and does **not** claim to prove the gate holds; its
own docstring says exactly that division of labour, so it cannot be read as asserting a property
it does not check. Delete the source-text `spec.views` regex search entirely rather than keep it
alongside the citation — a passing decoy proxy is worse than no proxy, since it is what let this
gap read as closed.

**The test.** A `gated` entry whose `behavioural_test` names a function that does not exist (typo,
or the test gets deleted/renamed later) fails the meta test — must fail today on a constructed
dangling citation, pass once the six real entries' citations are real. Regression control: the
three genuinely gated sites (`_create_core`, `_repair_body_tag`, `_write_managed_skill`'s three
call sites) keep their existing behavioural coverage; this task adds no new behavioural test of
its own, only the citation and the check that it is not dangling.

## Testing

**Falsify every new and changed test, both directions**, and report both.

**Test selection:** grep each changed/added name across `tests/` — `RepairResult`, `AdoptResult`,
`strip_notice`, `backfill_skipped`, `markers.view_tag`, `ast.Name`, `neutralized-by-overwrite`,
`behavioural_test` — union the hits, plus the unconditional floor: `tests/meta`,
`tests/integration`, `tests/cli`, since ST1 touches `_cli/_main.py` (`adopt`).

**False-zero rule.** ST1's and ST3's closures are both completeness claims over a grep; scan with
internal whitespace collapsed and validate each scan against a constructed known positive before
trusting a zero or an exact count from it — the same rule TASK-933 applied to the six-site count,
now applied to the fourth consumer and the template scan.

**No docstring or comment claiming coverage that doesn't exist, and none asserting a property
nothing enforces** — this is F25's own diagnosis; ST4 exists because of it. Say what each test
actually checks, not what the mechanism is hoped to guarantee.

## Refs

Implements ADR-880 (the enumeration TASK-933 established for family A, extended here to family B
and hardened against the three gaps the reviewer found in family A's own mechanism). Addresses
REV-926 F23, F25.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 936 add-subtask "<title>"`; track with `sq task 936 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Enumerate repair-corridor consumers, fix F23

<!-- sq:subtask:ST1:body -->
Enumerate every CLI consumer of RepairResult/SyncSkips (grep for .repair./.skipped/.unreadable/strip_notice(/backfill_skipped across _cli/) the same way TASK-933 enumerated view-tag writers; assert a fifth consumer with no classification fails the test. Fix: sq adopt gains the same skipped/unreadable reporting loops sq repair has, matching wording, and exits 1 when either is non-empty (it is the corpus-repair sweep under a different name, per its own code comment). Full detail in the task body's ST1 section.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Widen the AST filter beyond ast.Attribute (F25 gap 1)

<!-- sq:subtask:ST2:body -->
The view-tag writer scan only matches attribute-style markers.view_tag(...) calls; a bare-name import + view_tag(name) call (ast.Name) is invisible to it, driven by the reviewer as a seventh unclassified writer that still passes all six tests. Widen the filter to also match ast.Name with id == 'view_tag'. Full detail in the task body's ST2 section.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Scan template literals for sq:view: tags (F25 gap 2)

<!-- sq:subtask:ST3:body -->
The writer scan globs *.py only, so a literal sq:view:<name> tag in a .j2 template is invisible by construction; templates/agents/role.md.j2:2 is one such site today (neutralized only because _create_core unconditionally overwrites a role's body region). Add a second scan over _rendering/templates/**/*.j2, classify that one hit, fail on an unclassified second one. Full detail in the task body's ST3 section.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Make the gate check assert the gate, not a decoy mention (F25 gap 3)

<!-- sq:subtask:ST4:body -->
The gate-check test proves a spec.views mention exists in a gated site's source, not that it guards the seed; an unused mention added to each target still passes all six tests. Require each gated entry to name a real behavioural test (module + function) that the meta test confirms exists, rather than re-deriving proof of the gate from source text; drop the regex search. Full detail in the task body's ST4 section.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-10T08:53:54Z] Elias Python:
  - Round four done, all falsified both directions.
    
    **ST1 (F23).** Enumeration is `tests/meta/test_repair_corridor_consumer_sites_are_exhaustively_classified.py` — AST scan for attribute reads shaped `.repair`/`.skipped`/`.unreadable`/`.backfill_skipped`/`strip_notice(` across `_cli/`, grouped per (file, function). Discovers **five** sites, not the hand-listed four: `repair`, `migrate_up`, `sync`, `adopt`, and a fifth the list never named — `renumber`, which only matches because it shares the `strip_notice()` method name with a different, channel-less result type (`RenumberResult`). Classified `not-a-reporting-site` with that reasoning. Falsified: deleting `renumber`'s classification entry reddens the exhaustiveness test; restored, green.
    
    Fix: `adopt` in `_cli/_main.py` gained the same `unreadable`/`skipped` loops `sq repair` has, verbatim wording, exit 1 when either fires, closing hint skipped on that path (it points at `sq repair`, not `sq check`, which can't see this state). Red before: reviewer's exact repro (marker-shaped manager role body, adopted) — silent, exit 0, `sq role manager show` renders stale text. Green after: names the skip, exits 1, matches `sq repair` on the identical corpus byte for byte. Two new rows in `tests/cli/test_repair_corridor_message_and_exit_parity.py` (`test_adopt_skipped_row`, `test_adopt_unreadable_row`) plus a clean-row regression control — both red-before/green-after, driven.
    
    **ST2.** Widened `test_view_tag_writer_sites_are_exhaustively_classified.py`'s discovery filter to match `ast.Name` (bare `view_tag(...)`) alongside `ast.Attribute`. Red before: reviewer's exact repro reconstructed as a synthetic-string fixture run through the real scanner — 0 sites found. Green after: 1. All six pre-existing sites unaffected (still exactly six real, no accidental new match in the live tree).
    
    **ST3.** Second scan added to the same file, over `_rendering/templates/**/*.j2`, whitespace-tolerant regex `sq\s*:\s*view\s*:\s*(name)` (survives a wrapped tag). One bundled hit, `agents/role.md.j2` → `role_definition`, classified `neutralized-by-overwrite` citing `_create_core`'s unconditional role-body overwrite. Falsified twice: (a) a non-tolerant regex misses a constructed line-wrapped tag — red, tolerant version green; (b) a copied-fixture tree with a constructed second writer seeded into `agents/skill.md.j2`'s body region is caught unclassified — red for the fixture, green for the real (untouched) corpus in the same test.
    
    **ST4.** Deleted the `spec.views` source-text regex proxy entirely (`_GATE_RE`/`_gate_targets`/the old parametrized test) — driven: with all three real gates removed and an unused `in spec.views` mention added to each target, the old proxy passed all three, which is the gap. Replaced with `GATED_BEHAVIOURAL_TESTS`: each `gated` entry now cites one real test (`module::function`) whose own falsification proves that gate; a new AST-based check (`_cited_test_exists`, no import/execution) asserts only that the name resolves to a real top-level test function — never that it passes, never that it proves the gate, stated in both the module note and the test's own docstring. Combined falsification: reverted all three gates + added the decoy mentions, ran everything — the meta file stayed **fully green** (12/12, it no longer reads source text at all) while all three cited tests, and their siblings in the same files, went red. That's the proof the citations are honest, not decorative. Separately: a dangling citation (typo'd function name) reddens the resolution check; restored, green.
    
    **Selection:** grepped `RepairResult`/`AdoptResult`/`strip_notice`/`backfill_skipped`/`markers.view_tag`/`ast.Name`/`neutralized-by-overwrite`/`behavioural_test` across `tests/`, unioned with the floor (`tests/meta`, `tests/integration`, `tests/cli`) plus the specific `tests/service`/`tests/unit` files the grep surfaced outside the floor. 2172 passed, 7 skipped, 0 failed.
    
    **False-zero:** no `identifier_wrap_scan.py` was present in the scratchpad path named in the brief (checked — not there), so I built the validation directly into each new scan: ST1's and ST3's false-zero tests each construct a wrapped/split adversarial fixture, assert the raw substring is absent, then assert the real scanner still finds it — same pattern as the existing family-A validation, extended to the two new scan surfaces.
    
    **Gates:** pyright/ruff check/ruff format clean. `sq check` clean.
    
    **Scope:** did not touch `_cli/_migrate.py`, `_cli/_common.py`, or `_overrides/_manifest.py` — F22/F24 untouched, confirmed by grep.
    
    Files: `src/squads/_cli/_main.py`, `tests/cli/test_repair_corridor_message_and_exit_parity.py`, `tests/meta/test_view_tag_writer_sites_are_exhaustively_classified.py`, `tests/meta/test_repair_corridor_consumer_sites_are_exhaustively_classified.py` (new).
- [2026-09-10T09:25:29Z] Elias Python:
  - Fifth-round closure done (F26 + corridor widening + rename), all falsified both directions. No production code touched — this round is entirely test/gate infrastructure plus a pytest marker registration.
    
    **Closure 1 (F26).** Inverted the citation: behavioural tests now self-declare via `@pytest.mark.gate_for("<relpath>::<function>")` (registered in pyproject.toml's `markers`), applied to the three real gated tests. The meta module builds its map by scanning `tests/` for the marker via AST rather than reading a hand-maintained dict; `GATED_BEHAVIOURAL_TESTS` and `_cited_test_exists` are gone.
    
    - Drive 1 (re-point): added the marker to the real uninvolved sibling (`test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag`) alongside the true owner — red: `test_every_gated_site_has_exactly_one_behavioural_test_citation` fails on ambiguous ownership (two claimants for one site). Reverted, green.
    - Drive 2 (skip): added `@pytest.mark.skip` to the real cited test, marker left in place — red: `test_every_gate_for_citation_is_collected_and_live` fails, citation flagged excluded-from-default-collection. Reverted, green.
    - Re-verified F25 still holds under the new mechanism: reverted all three real gates (`_create_core`, `_repair_body_tag`'s role branch, `_write_managed_skill`'s system-skill caller) — meta module stayed 13/13 (it reads no source text), all three cited tests reddened. Restored, all green (diff clean before/after — verified with `git diff --stat`).
    - What this deliberately does NOT claim, stated in the module docstring and each test's own: whether a live, uniquely-owned citation's assertions actually falsify the gate is a mutation-testing question, not a static one. An edit that removes the marker from the true owner and adds it only to an uninvolved test (a genuine swap, not a duplicate) is not caught — nothing static can tell a moved false claim from a moved true one. Drive 3 (self-declared `not-a-writer` scope) is untouched by this closure, per the brief's own scope.
    
    **Closure 2 (corridor widening).** Added the producer names (`sync`, `run_pending_migrations`) to `_TARGET_ATTRS` and bare-name `svc_adopt` matching (`ast.Name`) to `_collect` — same widening shape as F25 gap 1, applied to the scan that hadn't learned it yet.
    
    Discovery list, driven against `_sites_in_module` directly:
    - FOUND `.unreadable` (known positive, unchanged)
    - FOUND `svc.repair()`, reads nothing (accidental, `repair` doubles as a channel name — unchanged)
    - was MISSED, now FOUND: `svc.sync()`, reads nothing
    - was MISSED, now FOUND: `svc.run_pending_migrations()`, reads nothing
    - was MISSED, now FOUND: bare-name `svc_adopt(...)`, reads nothing
    - still MISSED, not claimed closed: a channel read via `getattr`/`dataclasses.asdict` — stated explicitly in the module docstring as out of scope; no mechanism here catches it
    
    Falsified: reverted the widening (stripped the two producer names and emptied `_BARE_NAME_TARGETS`), the three new discovery tests went red (`set() == {...}` — nothing found); restored, green. The real `_cli/` corpus still resolves to exactly the same 5 sites — no new real site, only closed scan coverage for a hypothetical sixth.
    
    **Closure 3 (rename).** `reports-both-channels` -> `reports-every-channel` throughout the corridor module (CLASSIFICATIONS values, `_VALID_CLASSIFICATIONS`, the `sync` entry's "both channels" -> "every channel" phrase). Whitespace-collapsed repo scan (hyphens preserved, known positive validated first) finds zero remaining occurrences of the old label in src/ or tests/; the two hits outside code are historical sq item text (task/review bodies), left alone as the record.
    
    **Selection.** `gate_for`/`reports-every-channel`/`svc_adopt`/`run_pending_migrations`/`_BARE_NAME_TARGETS`/`_TARGET_ATTRS` grepped across tests/, unioned with the floor (tests/meta, tests/integration, tests/cli) plus the two tests/service migration files the `run_pending_migrations` grep surfaced outside the floor: 2015 passed, 7 skipped, 0 failed. `grep -cE "^FAILED"` validated against a known-positive line before trusting the zero.
    
    **Gates.** pyright/ruff check/ruff format clean. `sq check` clean.
    
    **Scope.** No changes under `_cli/_migrate.py`, `_cli/_common.py`, or `_overrides/_manifest.py` (F22/F24 untouched — confirmed by diff, nothing under src/ changed at all this round).
    
    Files: `pyproject.toml`, `tests/meta/test_view_tag_writer_sites_are_exhaustively_classified.py`, `tests/meta/test_repair_corridor_consumer_sites_are_exhaustively_classified.py`, `tests/service/test_role_activation_seeds_no_tag_for_an_undeclared_view.py`, `tests/service/test_repair_body_tag_backfill_respects_a_dropped_view_declaration.py`, `tests/service/test_skill_creation_seeds_no_tag_for_an_undeclared_view.py`.
    
    @reviewer for re-review.
<!-- sq:discussion:end -->
