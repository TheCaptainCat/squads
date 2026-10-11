---
id: REV-995
sequence_id: 995
type: review
title: 'Behind-schema migrate up: reconcile path and run vocabulary'
status: ChangesRequested
author: reviewer
assignee: reviewer
refs:
- TASK-954:addresses
- MILE-934:targets
description: Review of TASK-954, one pass per group of subtasks; the first pass covers
  the runners opening the index under the run's resolved vocabulary.
subentities:
- local_id: F1
  title: No test fails when a runner is handed the wrong playbook
  status: Verified
  severity: medium
- local_id: F2
  title: Static guard passes code that still reads the bundled vocabulary
  status: Verified
  severity: low
- local_id: F3
  title: Digest golden cannot be reviewed or regenerated on update
  status: Verified
  severity: low
- local_id: F4
  title: Contributor guide and a runner docstring state the old contract
  status: Verified
  severity: low
- local_id: F5
  title: Re-run after a stopped run is refused on a pre-0.7 override squad
  status: Open
  severity: medium
- local_id: F6
  title: Migrated-corpus goldens store one rendered surface nine times
  status: Open
  severity: low
created_at: '2026-10-11T20:54:17Z'
updated_at: '2026-10-11T21:12:39Z'
---
<!-- sq:body -->
## Scope

Review of TASK-954, one pass per group of subtasks as they are built. Findings from every pass
are recorded here.

### Pass 1: ST6, every runner's index opened under the run's resolved vocabulary

The change read: `src/squads/_migrations/_context.py` (new), `_registry.py`, the four runners
that open the index (`_v0_4_to_v0_5.py`, `_v0_8_to_v0_10.py`, `_v0_11_to_v0_14.py`,
`_v0_14_to_v0_15.py`), `_services/_maintenance.py::run_pending_migrations`, the four new test
modules, `tests/fixtures/migrated_corpus_digests.json`, `tests/_helpers.py` and the six adapted
test modules. Uncommitted, on top of `1a96e516`.

How it was checked, beyond reading:

- **Old against new, row by row.** A probe ran `sq migrate up` through the CLI over 11 squad
  sources (corpora 0.1, 0.3, 0.4, 0.5, 0.8, 0.10, 0.11, 0.14 and fresh squads stamped 0.4, 0.8,
  0.11) by 26 override shapes (286 rows), once on `git archive 1a96e516` and once on the working tree,
  and compared exit code, output and the digest of every file and directory. A second probe
  carried one item per shape for eight more shapes over six sources (48 rows).
- **The digest fixture against the unchanged code.** The new digest test, run on the
  `1a96e516` sources, passes for all eleven corpora.
- **Mutations.** Each of the four `IndexStore(...)` constructions with `spec=` removed, one
  with `spec=None`, and the context built with a bundled spec or a bundled playbook, each run
  against the migration tests; the bundled-playbook mutation also against the whole suite.
- **The static guard**, fed fifteen shapes of code that reads the bundled vocabulary.
- **An era-shaped squad**: the 0.5 corpus with an override declaring a type and one item of it
  written by hand in the 0.5 file and index shape, migrated with the old and the new code.

### What held

- Of 334 probe rows, 254 complete on both and none of those differs in exit code, output or
  any file. 16 are refused by the unchanged code and complete on the changed code with the
  carried item kept: every one is an override that alone declares vocabulary an item carries,
  on a squad stamped below 0.14. None completes on the unchanged code and is refused on the
  changed code. 55 are refused by both with the same output and the same tree (overrides the
  loader or the index cross-check rejects, and rows whose setup is invalid by construction).
- 9 rows are refused by both with the same message and a different tree: an override that
  rebinds a badge field to a collection of its own that lacks a stored code, which the index
  cross-check does not report. The changed code refuses at the first runner that opens the
  index, before the 0.11 to 0.14 runner writes; the unchanged code refused one runner later,
  after it had written.
- The store uses its spec only to validate a load, and the last runner has opened the index
  under the squad's own spec since it shipped, over an index that only grows during a run. A
  squad that completes on the unchanged code has therefore already passed that validation, so
  passing the spec to the three older runners can turn a refusal into a pass or move it
  earlier, never the reverse.
- On the `migrate up` path the service's spec and playbook come from the root callback's
  resolution of the same files the two newest runners used to re-read, through the same
  loaders. `run_pending_migrations` has one caller.
- Shapes driven with a carried item, all kept: a sub-entity badge code, a sub-entity kind of
  the squad's own with its own lifecycle and status, a type on a lifecycle of its own, a ref
  kind, a bundled type dropped and re-declared under another name, a re-prefixed and
  re-foldered bundled type, an adopter-declared field. Shapes driven without one: a playbook
  override alone, a deselected view, an added view, dropped bundled types, a custom lifecycle
  on a bundled type, a relabelled collection, a re-rooted roster lifecycle.
- The era-shaped 0.5 squad is refused by the unchanged code and completes on the changed code,
  `sq check` exits 0, and the item of the squad's own type loads. Its frontmatter keeps the
  padded id and refs, which is the manual step the 0.5 to 0.7 runbook already describes.
- The changed test helper in `test_milestone_roll_up_tag_migration.py` builds the service the
  way the CLI does. Run in its previous form against the changed code, one test of 22 fails
  (the deselected-view row), which is the difference a service built without the squad's
  vocabulary now makes; no CLI path builds one for `migrate up`.
- `_context.py` imports nothing from `_registry`, `_services` or `_cli`.

### Not covered by this pass

ST1 to ST5, which are not built. The second backend (`agents_md`), role overrides under
`.overrides/roles/`, template overrides, and squads with operators or author-created skills
were not driven. The whole suite was not re-run on the working tree; pyright and ruff were not
re-run.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 995 add-finding "…" --severity medium`; track with `sq review 995 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — No test fails when a runner is handed the wrong playbook

<!-- sq:finding:F1:body -->
**What.** The subtask's goal is that every runner works under the one spec and playbook the
run resolved. Nothing fails when a runner is handed a different playbook, and the test that
asserts the context carries the service's own spec and playbook cannot fail on that assertion.

**Evidence, demonstrated.**

- `src/squads/_services/_maintenance.py:1681`, with `playbook=self.playbook` replaced by the
  bundled playbook singleton: the four new test modules and the seven existing migration
  modules give 198 passed. The whole suite on the same scratch copy gives the same result with
  and without the mutation (6531 passed; the 10 failures and 30 errors are meta and docs tests
  that need repository files the copy lacks, the same set both times).
- That mutation changes what `sq migrate up` writes. A fresh squad stamped 0.4, 0.8 or 0.11
  whose override declares an `incident` type and whose playbook override names `manager` as
  its author gets a different `CLAUDE.md` (the team-workflow line for the type) under the
  real context than under the mutated one.
- `tests/integration/test_migrate_up_resolves_the_vocabulary_once.py:63` builds
  `Service(_paths_at(root))`, so `svc.spec` and `svc.playbook` are the bundled singletons, and
  lines 91 and 92 (`received[0].spec is svc.spec`, `received[0].playbook is svc.playbook`)
  hold for any context that carries those singletons, whoever fetched them. With the context
  built from a direct `bundled_spec()` call the test stays green (the table goes red on 50
  rows, so the spec half is pinned elsewhere; the playbook half is pinned nowhere).
- The `type-and-playbook` family in
  `tests/integration/test_migrate_up_under_the_resolved_vocabulary.py:128` asserts only that
  the item's type reads back (line 196), which the workflow override decides alone.

**Why it matters for what comes next.** The up-front vocabulary subtask rebuilds the service
for this caller through the bypass accessor, whose fallback passes no playbook today. A slip
there hands every runner the bundled playbook and nothing goes red.

**What would fix it.** Build the once-test's service under a workflow override and a playbook
override, so the two identity assertions compare objects only the run's own resolution can
produce. Add one row, through the service and through the CLI, asserting a byte only the
override playbook can produce after the run; the authoring line for the squad's own type in
the compiled region is one.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-11T21:04:19Z] Elias Python:
  - Fixed: once-test built under real overrides; playbook row asserts the compiled authoring line; bundled-playbook mutation now 7 red
- [2026-10-11T21:11:53Z] Paul Reviewer:
  - Verified on the working tree: with the bundled playbook swapped into the context, 7 tests go red (the once-test on its identity assertion, and the type-and-playbook row at built-0.4, built-0.8 and built-0.11 through the service and the CLI, each on the CLAUDE.md line). The line is absent under the same workflow override without the playbook, so the playbook alone produces it. The bundled-spec swap now turns the once-test red too.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Static guard passes code that still reads the bundled vocabulary

<!-- sq:finding:F2:body -->
**What.** `tests/meta/test_migration_runners_use_the_runs_resolved_vocabulary.py` matches
names, so code that still validates or answers under the bundled vocabulary passes it. Its
docstring (line 8) declares one blind spot, `getattr` with a built name.

**Evidence, demonstrated by feeding `_violations` each shape; every one returns no hit.**

- `IndexStore(a, b, spec=None)`, and a helper `def f(paths, spec=None)` that passes
  `spec=spec` on: line 39 checks that a `spec` keyword exists, not what it carries.
- `from squads._index._store import IndexStore as Store` then `Store(a, b)`; `cls = IndexStore`
  then `cls(a, b)`; `functools.partial(IndexStore, a, b)()`: line 38 matches the callee's
  spelling.
- Resolution through a helper outside the banned set: `Service(paths)` (bundled spec and
  playbook by default), `open_service()`, `resolve_playbook(...)`, `_init_time_spec(...)`,
  `get_active_spec()`, the `squads._workflow` module shims (`TERMINAL`, `is_open`,
  `can_transition`) and `squads._interactions.PLAYBOOK`.

For the four runners that exist, the behavioural table covers the first group: `spec=None` in
the 0.4 to 0.5 runner turns ten rows red while this guard stays green. A runner added later
has no table row until someone writes one, so there the guard is the only check.

**The exemption.** `_FROZEN_LEGACY_READERS` (line 21) switches off all four resolver names for
the whole of `_meta_compat.py`. One call of one name needs it
(`_meta_compat.py:101`, `bundled_spec().subentity_initial(kind)`). The exemption is justified:
the module serves only the two oldest file-walking runners, which take paths. It is wider
than it needs to be. The scan also globs `*.py` without recursing (lines 70 and 77), so a
subpackage would not be read.

**What would fix it.** Treat a literal `None` as no `spec`; follow `import ... as` and a plain
rebinding of `IndexStore`; add the other entry points to the banned names, or better, pin it
behaviourally by recording the spec every `IndexStore` is built with while each registered
runner runs under a non-bundled spec and asserting it is the context's. Narrow the exemption to
`{"_meta_compat.py": {"bundled_spec"}}`. List in the docstring what the scan cannot see.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-11T21:04:23Z] Elias Python:
  - Fixed: guard flags None spec, aliases, rebinding, more entry points; exemption narrowed to one name; limits documented
- [2026-10-11T21:11:57Z] Paul Reviewer:
  - Verified: every evasion from the first pass is now flagged (None spec, import alias, rebinding once and twice, partial, passing the class as an argument, Service, open_service, resolve_playbook, get_active_spec, PLAYBOOK), the scan recurses, and a second resolver planted in _meta_compat.py turns the guard red. Still unseen and declared in the docstring: an optional-default helper, an unlisted helper, getattr. One residual it does not name: a rebinding through a module attribute (mk = store_module.IndexStore, then mk(a, b)).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Digest golden cannot be reviewed or regenerated on update

<!-- sq:finding:F3:body -->
**What.** `tests/fixtures/migrated_corpus_digests.json` stores a sha256 per file of each
migrated corpus. The digests are right today: the new test, run on the unchanged sources at
`1a96e516`, passes for all eleven corpora, and changing one written field in the 0.11 to 0.14
runner turns nine rows red. The problem is what happens the first time it legitimately changes.

**Evidence, read.**

- `tests/CONVENTIONS.md`, section 6: a golden's source of truth is a reviewed reference
  render, updating one is an intentional reviewed act, and it lives in its own file "so a diff
  on update is reviewable on its own terms". A diff of this file is a column of hashes; a
  reviewer cannot tell a wanted change from a regression.
- Nothing records how the file was produced. The test
  (`tests/integration/test_migrate_up_output_is_unchanged_for_every_corpus.py`) only reads it.
- It pins bytes this migration does not own. `CLAUDE.md`, the `.claude/skills/*/SKILL.md`
  pointers and the seeded skill bodies are rendered from today's templates by the 0.11 to 0.14
  runner, and `.squads.toml` and `.squads.json` carry the schema stamp. The next template edit
  or schema bump turns up to eleven rows red with no way to regenerate except an ad hoc
  script, which is how a golden ends up anchored to the code it guards.

**What it covers and leaves out.** Every file under the corpus root except `.reflog.jsonl`
(line 26); directories are not recorded (line 33), so a folder a runner creates and leaves
empty is invisible. Every corpus has an entry and the clock is frozen. All eleven corpora
carry no override and use `squad_dir = "."`, and the service is built on the bundled defaults
(line 47), which is the one population for which this change is a no-op by construction: both
the old and the new code resolve the same bundled singletons. The claim that no byte changes
for a squad with an override rests on the argument and probes in this review's body, not on
this test.

**What would fix it.** Record the capture procedure beside the fixture, or give the test a
documented regeneration switch. On a mismatch, show a content diff for the differing files
(keep the migrated tree, or compare against a committed tree instead of hashes). Say in the
docstring that it covers squads without overrides only.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-11T21:04:27Z] Elias Python:
  - Fixed: golden is now reviewed text copies under tests/goldens/migrated_corpus with UPDATE_GOLDENS regeneration and a diff on mismatch
- [2026-10-11T21:12:04Z] Paul Reviewer:
  - Verified: text goldens with a unified diff on mismatch, the repo's UPDATE_GOLDENS switch, coverage stated in the docstring. The goldens match the unchanged code: the test passes against them on the 1a96e516 sources for all eleven corpora. A changed written field turns nine rows red with a readable diff. No golden file is git-ignored. I read the 0.14 corpus's copy; it equals the committed 0.15 fixture apart from the frozen-clock timestamps. The duplication across corpora is recorded separately as F6.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Contributor guide and a runner docstring state the old contract

<!-- sq:finding:F4:body -->
**What.** Two statements of the runner contract are no longer true.

- `CLAUDE.md:169` describes each migration as a private module with `migrate(paths)->int`.
  Four of the ten runners now take the run's `MigrationContext`, and that is the signature a
  new runner that needs vocabulary has to use. This is the paragraph a developer adding the
  next runner reads first.
- `src/squads/_migrations/_v0_5_to_v0_7.py:35-36` explains that custom types are not covered
  "matching every other runner in this package (none of them thread the active spec)". Four
  runners are handed the active spec.

**Evidence.** Read.

**What would fix it.** In `CLAUDE.md`, state both shapes: a file-walking runner takes
`SquadPaths` and is wrapped, a runner that needs the index or the vocabulary takes the
context. In the 0.5 to 0.7 docstring, drop the parenthesis or limit it to the file-walking
runners.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-11T21:04:31Z] Elias Python:
  - Fixed: CLAUDE.md runner sentence and the 0.5 to 0.7 docstring state both runner shapes
- [2026-10-11T21:12:12Z] Paul Reviewer:
  - Verified by reading: CLAUDE.md line 169 states both runner shapes, and the 0.5 to 0.7 docstring now compares itself to the other file-walking runners only.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Re-run after a stopped run is refused on a pre-0.7 override squad

<!-- sq:finding:F5:body -->
**What.** A squad stamped below 0.7 that carries any workflow override, and whose first
`sq migrate up` is stopped after the 0.11 to 0.14 runner, is refused on every later run with a
false cause. This predates the change reviewed in the first pass: the unchanged code at
`1a96e516` and the changed code behave identically. It is recorded here because it is a
dead end inside this task's subject that the task's reproduction table does not list.

**Evidence, demonstrated** (steps 1 and 2 on the unchanged and on the changed code, the
corrected re-runs on the changed code). The 0.5 corpus, plus an override that only adds a ref kind
(`[ref_kinds.mirrors]`), plus the task file hand-edited to `status: Triaged`.

1. First run: every runner writes, the trailing repair refuses with
   `item TASK-3 has unknown status 'Triaged' ...; fix the frontmatter before running sq repair`.
   Schema stays 0.5. The index now holds `UNRESOLVED-1` to `UNRESOLVED-8` as ids.
2. Second run, before and after the frontmatter is corrected: refused before any runner with
   `workflow spec is incompatible with the live index`, one line per type of the form
   `type 'bug' prefix changed to 'BUG' in the workflow spec, but 1 live item(s) are still
   filed under the old prefix: ['UNRESOLVED-4']`, closing on `sq workflow lint`.
3. With the frontmatter corrected and the override file moved aside, the run completes and
   stamps the current schema. Nothing in the refusal points an operator there.

**Mechanism, read.** An index entry written before schema 0.7 stores neither `id` nor
`prefix`. Loaded by today's model it has an empty prefix, and `Item.id` renders the
`UNRESOLVED` sentinel (`src/squads/_models/_item.py:53`). The seeding transaction in
`src/squads/_migrations/_v0_11_to_v0_14.py:267` writes the whole index back, which persists
that sentinel as each entry's `id`. On the next invocation the root callback's cross-check
(`src/squads/_cli/_common.py:343`) derives the prefix from the stored id and reports every
type as re-prefixed. Without an override the cross-check does not run, which is why step 3
completes. The 0.4 to 0.5 and 0.8 to 0.10 transactions write the index back the same way.

**What would fix it.** Either of the two changes this task already plans removes the dead
end: rebuilding the index from the frontmatter before the runners, and checking the
vocabulary after that rebuild instead of in the root callback. What is missing is the row:
a squad stamped below 0.7 with an override, stopped once by the trailing repair, then re-run,
in the end-to-end table.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-11T20:58:23Z] Catherine Manager:
  - Home for this one is TASK-954 itself: the reconcile and the up-front vocabulary check (ST2, ST4) are expected to remove it, and ST3's shape table takes a row for a stopped run on a pre-0.7 squad with an override, re-run to completion. It stays Open until that row is green.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Migrated-corpus goldens store one rendered surface nine times

<!-- sq:finding:F6:body -->
**What.** The migrated-corpus goldens under `tests/goldens/migrated_corpus/` are 319 files
holding 59 distinct contents. The other 260 are byte-identical copies, because nine of the
eleven corpora pass through the same 0.11 to 0.14 runner and it writes the same rendered
surface into each.

**Evidence, measured on the working tree.**

| Files | Copies | Distinct |
|---|---|---|
| `CLAUDE.md` | 9 | 1 |
| `.claude/**` | 117 | 13 |
| `agents/skills/**` | 112 | 14 |
| item files | 50 | 18 |
| `.squads.json`, `.squads.toml` | 20 | 12 |

One stub skill body alone is stored 63 times. The bytes are small (246 KB in all); the cost
is in the update. `tests/CONVENTIONS.md` section 6 asks for one golden per distinct rendering
path and calls goldens that differ only in one input redundant. Every edit to the managed
section, a pointer or a skill template will regenerate up to nine identical copies, and the
reviewer of that update reads the same hunk nine times, which is how a golden update stops
being read.

The goldens themselves are right: the test passes against them on the unchanged sources at
`1a96e516`, a changed written field turns nine rows red with a readable diff, and none of the
files is git-ignored.

**What would fix it.** Record the rendered surface (`CLAUDE.md`, `.claude/**`,
`agents/skills/**`) once, from one corpus that passes through the 0.11 to 0.14 runner, and for
the other corpora assert their copy equals that one; keep per-corpus goldens for what really
differs between them (item files, the index, the config). That is about 60 files with the same
coverage and a single hunk per template edit.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-11T20:56:45Z] Paul Reviewer:
  - @manager first pass done, ST6 only. Verdict: ChangesRequested on one test gap; no defect found in the source change.
    
    - **The source change holds.** Old code against new over 334 rows of squad source by override shape: 254 complete on both with no byte, output or exit-code difference; 16 refused before now complete with the item kept; none goes the other way. The digests reproduce on the unchanged code at 1a96e516. The claim that no byte changes for a squad that migrates today is sound, including for squads with overrides, which the digest test does not represent.
    - **F1 (medium) should land before the up-front vocabulary subtask.** Handing every runner the bundled playbook leaves the whole suite green while changing CLAUDE.md for a squad with a playbook override, and the once-test's identity assertions cannot fail. That subtask rebuilds the service for this caller, through an accessor that passes no playbook today. @python-dev
    - **F2, F3, F4 (low)** can ride with the task: the static guard's blind spots and wide exemption, the hash-only golden, two stale statements of the runner contract.
    - **F5 (medium) is not this subtask's.** It predates the change and is closed by the reconcile and the relocated vocabulary check; it needs a row in the end-to-end table. @tech-lead
    - The changed helper in the milestone roll-up test is faithful: it builds the service as the CLI does. A service built without the squad's vocabulary now migrates under the bundled one where the two newest runners used to re-read the override; no CLI path builds one for migrate up today, and the up-front vocabulary subtask has to keep it that way.
    - Not filed, small: tests/_helpers.py gains the module's first top-level squads imports where every other helper imports locally. No changelog entry for the adopter-visible fix yet.
    - Not covered: the agents_md backend, role and template overrides, squads with operators or custom skills. The whole suite, pyright and ruff were not re-run here.
- [2026-10-11T21:12:39Z] Paul Reviewer:
  - @manager F1 to F4 verified against the working tree; the first subtask is clear to commit and build on.
    
    - **F1** Verified: the bundled-playbook swap now turns 7 tests red, each on the intended assertion.
    - **F2** Verified: every earlier evasion is flagged; what a static scan cannot see is declared.
    - **F3** Verified: text goldens, regenerable and reviewable, and they match the unchanged code at 1a96e516.
    - **F4** Verified by reading.
    - **F6** (low, new, not blocking): 260 of the 319 golden files are byte-identical copies of one rendered surface. About 60 files would give the same coverage. @python-dev, with the rest of the task.
    - **F5** stays Open for the later subtasks.
    - Source is unchanged since the first pass apart from one docstring, so the old-against-new comparison there still stands.
    - Status left at ChangesRequested: F5 and F6 are open and the task is unfinished, and the lifecycle has no state for a pass that is clear with more to come.
<!-- sq:discussion:end -->
