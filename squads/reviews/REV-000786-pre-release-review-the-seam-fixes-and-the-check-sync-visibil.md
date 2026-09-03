---
id: REV-786
sequence_id: 786
type: review
title: 'Pre-release review: the seam fixes and the check/sync visibility widening'
status: Approved
author: reviewer
refs:
- TASK-782
- TASK-785
- BUG-778
- BUG-779
- BUG-780
- BUG-784
- ADR-783
subentities:
- local_id: F1
  title: Stored whitespace-only role name bricks sq sync after upgrade
  status: Verified
  severity: high
- local_id: F2
  title: AgentBackend grew an 8th abstract method against its no-growth contract
  status: Verified
  severity: medium
- local_id: F3
  title: Backend pointer rule is cross-source but skips check's confirm round
  status: Verified
  severity: low
- local_id: F4
  title: 'Warn-level rationale is false: gitignoring .claude still exits 3'
  status: Verified
  severity: low
- local_id: F5
  title: Two 0.13.1 changelog claims overstate history and scope
  status: Verified
  severity: low
- local_id: F6
  title: agents_md per-entry report names write-only files no host reads
  status: Verified
  severity: low
created_at: '2026-08-22T11:42:27Z'
updated_at: '2026-08-22T14:17:20Z'
---
<!-- sq:body -->
## Scope

Two source commits on `release/0.14`, plus the documentation commit that records them, reviewed as
one increment before the 0.13.1 cut.

| commit | change | items |
|---|---|---|
| `c6a03b2` | blank/whitespace `full_name` refused at `RoleDef.__post_init__`; the per-writer sync skew warning deduplicated by exact text; two stale comments corrected | TASK-782, BUG-778, BUG-779, BUG-780 |
| `383d5e8` | per-entry backend pointers reported by `sq check` (warn) and by `sq sync` (regenerated); `_status_drift`/`_parent_drift` folded into a general `_value_skew_issue` on `frontmatter_skew` | TASK-785, BUG-784, ADR-783 |
| `af24997` | the adopter-facing record of both | — |

## Method

Attacked input shapes, not the designs. Every claim below is labelled **driven** (reproduced
against a real `sq` invocation or an in-process probe), **read** (traced in source without
executing the failing path), or **inferred**.

Throwaway squads under a scratch directory. Before/after claims are measured against three
source trees materialised with `git archive` and installed independently — `v0.13.0` (the last
released version), `26b4134` (both commits out) and `1407126` (`c6a03b2` in, `383d5e8` out) — so
every "this is new" statement is a measured comparison rather than an assumption.

**One probe correction worth recording, because it changed a conclusion.** The first pass used
`git worktree` for those trees. The worktrees never materialised (`git worktree list` showed only
the main tree), so `uv run --project <missing-dir> sq` silently fell back to the stale `sq` on
`PATH` — version 0.12.1 — and reported it as the "before" behaviour. Three comparisons were wrong
in the same direction before the version string was checked. Every before/after number below was
re-driven against the installed trees, each verified by grepping the tree for the code under test.

Probes: a 19-shape planted-frontmatter sweep comparing `ensure_no_skew`'s refusal against
`check`'s report on the same `(text, item)` pair; a 25-shape variant over a bundled role item and
a developer role item, one per `PERMITTED_EXTRA_SKEW` member plus `description`/`is_dev`/`tech`;
a repair-honourability sweep (does the remedy the message names actually clear it); a stale-index
snapshot harness for the new backend rule; a seven-method `AgentBackend` subclass.

Targeted test runs only — the suite was reported green and was not re-run.

## The fold-in equivalence, tested in both directions

**The generalisation holds. No false negative and no false positive found, across 44 driven
shapes.** This was the highest-risk part of the increment and it is sound.

- **Item set is unchanged.** `_confirm_cross_source`'s scan moved from `on_disk.get(seq)` to
  `bodies.get(seq)`. `_scan_for_check` populates `on_disk[seq]` and `bodies[seq]` on the same
  line, after the same `Item.from_frontmatter` gate, so the two maps have identical key sets by
  construction — the fold cannot lose an item the two predicates used to see. **read.**
- **Every shape the old predicates caught is still caught, with direction naming intact.**
  **driven:** `status` and `parent` each report at `warn` with the same `_drift_message` suffix.
- **The two normalisations the old predicates did by hand survive the round trip.** `parent: ""`
  against an index `parent: None` reported nothing then and reports nothing now — `if item.parent:`
  in `_add_optional_frontmatter_fields` omits the key on both sides, which is the same answer the
  deleted `(fdata.get("parent") or None)` gave. **driven.** A re-padded `id:` reports nothing,
  because the round trip recomputes it from prefix + `sequence_id`. **driven.**
- **Seventeen more fields are now covered, and each one is a real skew.** `title`, `author`,
  `assignee`, `priority`, `labels`, `refs`, `description`, `created_at`, `updated_at`,
  `modified_session`, `extra`, `subentities` — for each, planted disk-side, `ensure_no_skew`
  raises and `check` reports, and the message names exactly the diverging key set. **driven.**
- **An absent timestamp is still not a skew.** Removing `created_at`/`updated_at` from the file
  yields no skew report from either surface — only the existing "frontmatter has no created_at"
  advisory. That matters because it is the one class `sq repair` structurally cannot heal, and
  `_invented_timestamps` keeps it out. **driven.**
- **The permitted-extra-skew exemption is unchanged and correctly per-item.** On a bundled role
  every `PERMITTED_EXTRA_SKEW` member is exempt on both surfaces; on a developer role only
  `extra.skills` is, and the other ten report on both surfaces. `extra.description` reports on
  both, for both shapes — the `_RECONCILED_EXTRA_KEYS` split behaves as its comment claims.
  **driven, 25 shapes, zero disagreement.**
- **The remedy the message names actually works.** For all ten planted shapes re-checked after
  `svc.repair()`, the drift report is gone. There is no shape where `check` tells an operator to
  run `sq repair` and `sq repair` cannot clear it. **driven.**
- **No false positive across a realistic lifecycle.** init, sync, sync again, two `dev add`s, a
  role archive/reactivate cycle, another sync, item creation with a sub-entity and a comment: 16
  consecutive `sq check` runs, zero issues. **driven.**

## What else holds up

Recorded so it is not re-derived.

- **A clean squad's output is byte-identical before and after `383d5e8`.** `sq sync` and
  `sq check` on a two-backend squad with a full roster: `diff` of the captured stdout against the
  same commands run from the `1407126` tree is empty, both at exit 0. **driven.**
- **A retirement is never reported as a fault, on either surface.** Archiving a role withdraws
  both backends' pointers; the following `sq sync` is silent and `sq check` is clean. The
  mechanism is right rather than incidentally right: the retired slug is simply absent from the
  live set both callers derive, so `managed_entry_paths` never names its pointer at all.
  **driven + read.**
- **A workflow override that drops a type does not produce a permanent false positive.** With
  `guide` dropped, `sq check` reports only the existing orphan-skill warn — never a "managed
  pointer missing" for `sq-guide` — and this stays true across the withdrawal sync, a second
  sync, and the restore sync (which reports exactly one regeneration line per backend, then goes
  quiet). That is `is_live_roster_entry`'s second clause doing its job in both callers.
  **driven.**
- **The report cannot mistake an already-present file for a regenerated one.** `missing_before`
  is snapshotted before the roster loops write anything, and the report is filtered by both
  membership in that snapshot and present-on-disk afterwards. Deleting all four per-entry
  directories on a two-backend squad reports exactly 36 lines, one per file, and the next
  `sq check` is clean. **driven.**
- **Nothing in the new path loads an index.** `is_live_roster_entry` reads only `item` and `spec`;
  both `managed_entry_paths` implementations read only `ctx.live_role_slugs`/`live_skill_slugs`
  and `ctx.root`. `_live_roster_slugs` derives them from the already-loaded `ctx.index`, and the
  rule's own test counts index loads. **read.**
- **The two backends implement `managed_entry_paths` consistently**, and each names the same path
  its own `generate_role_entry`/`generate_skill_entry` writes (`role.slug` resolves from
  `extra[X.SLUG]`, which is what the live set is keyed by). **read.**
- **The sync skew dedup is real, reachable, and tested.** Measured: with a role override changing
  `mission` plus a planted `title` skew, `26b4134` prints the identical warning twice and the
  current tree prints it once. `test_an_interrupted_index_commit_is_healed_by_repair_then_a_
  further_sync_is_silent` counts the lines rather than substring-matching, so a regression to two
  reddens it, and a sibling test pins that a textually different message about the same item still
  gets through. **driven.** (The pre-existing `test_sync_reports_a_drifted_roster_item` could not
  have caught this — it asserts only that "warning" appears — which is why the duplicate survived.)
- **Only two writers can raise the same message per role**, so exact-text collapse cannot hide a
  distinct fact: `_refresh_catalog_extra` and `_refresh_role_skills_extra` are the only
  `update_frontmatter` callers in the sweep, and every other message family in the return value
  names its own item id, file path, or backend. **read.**
- **The blank-name refusal is right on the input side.** `sq dev add --name "   "` and
  `sq role activate <slug> --name "   "` both refuse cleanly at exit 1; internal whitespace and
  surrounding whitespace around real content are unaffected; the bundled catalog's eight roles and
  `dev_role`'s pool names all construct. The `if name:` → `if name is not None:` change is correct
  for the CLI caller. **driven.** Its consequence for the *stored* value is F1.

## The edited migration test

`tests/integration/test_unpadded_id_migration.py` gained an `await svc.repair()` before its
`assert not issues`. **The justification is sound, and the edit is not masking a regression.**
Verified rather than accepted:

- The skew is real and the new rule is right to see it. `_devolve_to_padded` writes
  `fm["subentities"][0]["title"]` straight to the file, bypassing the index entirely; the
  migration then unpads that title in place. The index still holds `"placeholder"`. That is a
  genuine frontmatter/index divergence on `subentities` — the write seam refuses it too, and it is
  exactly the class the fold-in was built to stop hiding. The old two-field predicate could not
  see it, which is why the test passed before.
- The remedy matches the real flow, not just the prose. `MANUAL` step 4 says "Runs `sq repair` to
  rebuild the index", and `MaintenanceMixin.run_pending_migrations` does exactly that:
  `for m in applied: await m.run(...)` then `await self.repair()` then `_stamp_schema`. The test
  calls `_v0_5_to_v0_7.migrate(svc.paths)` directly, so it was the only step of the real sequence
  the test was skipping. **read, at both sites.**
- The skew is created by the test's own index-bypassing helper, not by the migration. A real 0.5
  corpus reaches this migration with markdown and index agreeing, and `repair()` rebuilds from
  markdown regardless.

Net: the test is now a closer simulation of `sq migrate up` than it was, and the assertion it
makes is strictly stronger (clean after migrate **and** repair, rather than clean after a partial
sequence). No coverage was traded away.

## Verdict

**ChangesRequested**, on F1 alone.

F1 is an upgrade regression from the immediately preceding released version. A squad that named an
agent with a whitespace-only `--name` on 0.13.0 — accepted there at exit 0, durable across repeated
syncs, `sq check` clean throughout — cannot run `sq sync` or `sq role <slug> show` at all on
0.13.1. The refusal names no item, no slug, no file and no remedy; `sq check` still reports "no
issues", so the one command whose job is to say whether the squad is healthy points nowhere; and
neither `sq repair` nor archiving the role clears it. The only way out is to delete the role. A
patch release has to be a safe upgrade, and this one is not for that corpus.

F2 is worth fixing in the same pass and is cheap: the increment grew a documented-frozen ABC by
one abstract method, which two adopter-facing documents say in as many words does not happen.

F3–F6 are low and none of them loses anything.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 786 add-finding "…" --severity medium`; track with `sq review 786 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Stored whitespace-only role name bricks sq sync after upgrade

<!-- sq:finding:F1:body -->
**driven**, with the before/after measured against `v0.13.0` installed from its own source tree.

`RoleDef.__post_init__` refuses a blank/whitespace-only `full_name`. That is correct for the two
CLI flags it was written for. But the same constructor is on the **read** path for every role
item already on disk, and a whitespace-only `full_name` is a value the last released version
stores, keeps, and calls healthy. On 0.13.1 that squad cannot run `sq sync` at all.

## Driven, on v0.13.0 then on this tree

Developer role — no "forgot to sync" precondition, the value is fully durable:

    # v0.13.0
    sq init --roles core
    sq dev add --tech python --name "   "     exit 0    added     (`python-dev`) ROLE-15
    sq sync                                   exit 0    (twice; value survives both)
    ROLE-000015-python-dev.md                 title: '   '   extra.full_name: '   '
    sq check                                  exit 0    no issues
    sq role list                              python-dev  <blank>  Python developer  live

    # same squad, this tree
    sq check                                  exit 0    no issues
    sq sync                                   exit 1    error: role full_name is blank or
                                                        whitespace-only — every role needs a
                                                        real name

Bundled role, same outcome (`sq role activate devops --name "   "` on v0.13.0, then this tree):

    sq sync                exit 1   role full_name is blank or whitespace-only …
    sq role devops show    exit 1   role full_name is blank or whitespace-only …
    sq role devops regen   exit 1   role full_name is blank or whitespace-only …
    sq check               exit 0   ✓ no issues
    sq list -t role        exit 0   ROLE-15  role  Active   <blank title>

## Why this is high

- **`sq sync` regenerates nothing.** The raise happens in the role loop, so the whole sweep aborts
  on the first offending item — every other role's pointer, every skill, both compiled regions,
  the version stamp. One bad name stops the command for the entire squad.
- **`sq check` says the squad is clean.** The one command whose job is to name the problem reports
  nothing, and the error text names no item, no slug, no file, no remedy and no command. There is
  nothing to search for.
- **Neither documented remedy works.** `sq repair` exits 0 and changes nothing (the value is
  faithfully rebuilt from markdown). Archiving the role does not help either — `_refresh_catalog_extra`
  runs for every role item in the sweep regardless of status, so `sq role devops status Archived`
  followed by `sq sync` still exits 1. **driven, both.** The only exit found is destroying the
  entry: `sq role devops rm --purge`, after which `sq sync` succeeds.
- **The team already knew this corpus exists.** The 0.13.1 changelog entry for this very fix
  describes the pre-fix behaviour as "storing a name made of spaces that then rendered as an empty
  roster line and told the agent it was 'the  on this project'" — i.e. the stored value reaching
  generated files on released versions. The fix closed the input seam and turned the read of that
  same stored value into a hard refusal, with no migration, no degradation and no report.

## Mechanism, read

Two seams, one per role shape, both on the read path and both outside any handler:

- `_resolver.role_base_from_item` → `replace(predefined, full_name=full_name)` for a bundled role.
  Its guard is `if not full_name or full_name == predefined.full_name: return predefined` — which
  already forgives the *empty string* and falls back to the catalog. `"   "` is truthy, so it
  reaches `replace` and raises. The guard is one `.strip()` away from covering this shape.
- `_resolver.dev_base_from_item` → `dev_role(tech, name=item.extra[X.FULL_NAME], …)` for a
  developer role, with no equivalent guard at all. This is where `c6a03b2`'s `if name:` →
  `if name is not None:` change bites: before it, a stored blank re-derived the pool name and the
  item self-healed on the next sync; after it, the stored blank is passed through to the refusal.
  The docstring justifies the change entirely in terms of "an operator who explicitly passed a
  blank `--name`", which is not the only caller.

`_refresh_catalog_extra` computes `base_role = role_base_from_item(item)` **before** its `try`,
and its only `except` is `RoleNotFoundError` — so the sibling degrade-and-continue path for an
orphaned custom role exists three lines away and this shape does not use it.

## Not covered by a test

`tests/unit/test_role_def_refuses_a_blank_full_name.py` and
`tests/cli/test_blank_role_name_is_refused_at_the_shared_seam.py` between them cover direct
construction, `dataclasses.replace`, `dev_role(name="")`, both CLI flags, internal whitespace,
surrounding whitespace, and the bundled catalog. Neither file mentions `from_extra`,
`dev_base_from_item`, or a role item whose *stored* `full_name` is blank. Every test drives the
input side; the shape that breaks is the corpus side.

## Direction of fix (not prescriptive)

The refusal belongs on the input, which is where it already is at both CLI call sites. What the
read path needs is to not weaponise it against data a previous release wrote: forgive a
whitespace-only stored name the same way `role_base_from_item` already forgives an empty one (a
`.strip()` in that existing guard, plus the missing equivalent in `dev_base_from_item`), or catch
it in `_refresh_catalog_extra` alongside `RoleNotFoundError` and report the item as a skip line so
the rest of the sweep completes and the operator learns which role to rename. Either way it needs
a driven test on the sequence "a role item carrying a whitespace-only stored name, then `sq sync`"
— the current suite passes with the sweep dead.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-22T12:05:25Z] Elias Python:
  - Fixed: chose self-heal over skip-and-report. role_base_from_item/dev_base_from_item (_roles/_resolver.py) and RoleDef.from_extra (_roles/_catalog.py) now treat a stored blank/whitespace full_name the same as absent, falling back to the catalog name (bundled) or the pool name at position 0 (dev) -- exactly what the next sq sync would converge onto, matching the pre-c6a03b2 dev_role behaviour.
  - Chose self-heal, not skip-and-report: _refresh_catalog_extra already mirrors any change role_base_from_item produces straight into frontmatter+index in the same transaction, so tolerating the read produces a durable fix with zero extra plumbing -- an adopter never sees the blank again after one sq sync, vs. a skip line that would leave it blank forever until they manually renamed it.
  - Driven, bundled role (devops), planted stored blank on both frontmatter and index: before -- sq sync/show/regen all exit 1 'role full_name is blank or whitespace-only'; after -- all four (sync, show, regen, check) exit 0, and sq sync rewrites full_name back to 'Hugo Ops' on disk and in the index. A second sync is silent (no further change).
  - Driven, dev role (python-dev), same planted-blank shape: same four commands exit 0 after the fix; sync heals full_name to the pool name at position 0.
  - Confirmed the four BUG-778 input-side refusals are untouched: sq dev add --tech rust --name '' / '   ' and sq role activate qa --name '' / '   ' all still refuse at exit 1 with the same message.
  - New tests: tests/unit/test_role_resolver_tolerates_a_stored_blank_full_name.py (seam-level, both role_base_from_item/dev_base_from_item and RoleDef.from_extra, both role shapes) and tests/integration/test_stored_blank_role_name_self_heals_on_sync.py (corpus-level: plants the blank on disk+index, drives sq sync/role show/role regen/check via the CLI). 20 of 28 new tests fail against the pre-fix code, confirmed by stashing the fix and re-running.
  - Gates: pyright/ruff/ruff format clean; tests/meta clean; targeted role/sync/check/backend suite (868 tests) green; sq check clean and sq repair a stable no-op on this repo.
- [2026-08-22T12:19:54Z] Theo Writer:
  - Changelog entry written for adopters, reframed from the handoff text: "no longer breaks sq sync/role show/regen" describes a regression that never shipped, so the entry states what an adopter upgrading from 0.13.0 actually sees — a whitespace-only name stored by an older version is written back to a real one (catalog name for a bundled role, pool name for a developer) on the next sync, in both the record and the index, with nothing to run by hand.
  - Drove the self-heal myself on both shapes: planted a whitespace-only full_name on frontmatter and index for python-dev and for reviewer; sync/show/regen/check all exit 0 and the name comes back as Elias Python / Paul Reviewer; a second sync is silent.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — AgentBackend grew an 8th abstract method against its no-growth contract

<!-- sq:finding:F2:body -->
**driven** (the `TypeError`), **read** (the two documents).

`383d5e8` added `managed_entry_paths` to `AgentBackend` as an eighth `@abstractmethod`. Two
adopter-facing documents state, emphatically, that this cannot happen — and neither was updated,
nor was a changelog entry written for it, in a patch release.

`docs/stability.md`, Tier 5, "Backend ABC surface":

> Backends register behind the `AgentBackend` abstract base class. It has **exactly seven**
> abstract methods, and **it does not grow** — that no-growth promise is what makes the behaviour
> below free for a new backend rather than something each one reimplements.

followed by a seven-row table, and closing with "both satisfy the same conformance suite a
third-party backend is held to".

`docs/backends.md` ships the ABC as a code block listing the same seven methods, then:

> That is the whole ABC — seven methods, and it does not grow.

and again at line 61: "seven methods above and you inherit that behaviour".

A backend written against that documented surface no longer instantiates. Driven, with the
docs' own method list transcribed verbatim into a subclass:

    TypeError: Can't instantiate abstract class SevenMethodBackend without an
    implementation for abstract method 'managed_entry_paths'

`grep -c "@abstractmethod" src/squads/_backends/_base.py` → `8`.

## Why it is filed here rather than as a docs nit

The promise is not incidental phrasing — it is the stated reason the status-awareness contract
("Implement the seven methods and withdrawal works") is free for a backend author, and it sits in
the document that carries this project's pre-1.0 stability contract. Nothing in BUG-784 or
ADR-783 authorised growing the ABC: the bug's own hard-constraint paragraph says "whatever set of
per-entry paths a **widened `managed_paths`** (or an equivalent probe) reports on…", and ADR-783
does not mention the backend surface at all. So the growth is an implementation choice that
crossed a documented boundary without the boundary being revisited.

## Direction of fix (not prescriptive)

Dropping `@abstractmethod` and giving the base a `return []` default keeps the promise literally
true, keeps both bundled backends exactly as they are, and makes the field defaults'
already-documented behaviour ("an empty *ctx* means an empty result") the base-class behaviour
too. If growing the ABC is the deliberate call instead, then both documents and a `Changed` entry
need to say so — and it is worth asking whether an eighth abstract method belongs in a patch at
all rather than in 0.14.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-22T12:05:36Z] Elias Python:
  - Fixed: took the reviewer's own remedy -- dropped @abstractmethod on managed_entry_paths (_backends/_base.py) and gave it a concrete default returning []. AgentBackend is back to exactly the seven documented methods; both bundled backends (ClaudeCodeBackend, AgentsMdBackend) still override it unchanged.
  - Proof: a subclass implementing only the seven methods docs/stability.md and docs/backends.md list now instantiates cleanly (it TypeError'd before the fix -- verified by stashing it). AgentBackend.__abstractmethods__ is exactly that seven-name frozenset; managed_entry_paths is confirmed absent from it.
  - New test: tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py -- pins the seven-name abstract set against the documents' own list, instantiates a seven-method-only subclass, checks the base default returns [], and asserts both shipped backends still define their own override (vars(ClaudeCodeBackend)/vars(AgentsMdBackend)).
  - docs/stability.md and docs/backends.md untouched, per the boundary -- they were already correct.
  - Gates: pyright/ruff/ruff format clean; tests/meta clean; targeted role/sync/check/backend suite (868 tests) green; sq check clean and sq repair a stable no-op on this repo.
- [2026-08-22T12:19:46Z] Theo Writer:
  - Changelog entry written, but reframed: the eighth abstract method never appeared in a release, so an adopter upgrading from 0.13.0 never saw a backend break and "works again" would be a false history. The entry says what is true relative to 0.13.0 — the interface gains one optional managed_entry_paths with a base default, the seven abstract methods are unchanged, and a backend that does not implement it simply reports no per-entry pointers. Verified: the abstract set is the same seven names at the tag and now.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Backend pointer rule is cross-source but skips check's confirm round

<!-- sq:finding:F3:body -->
**driven** (the false positive, via a stale-snapshot harness), **read** (the confirm-round set).

`check()`'s own docstring states the rule this new report does not follow:

> Its **cross-source** issues — status/parent drift and both directions of index/disk
> reconciliation, each a claim comparing the on-disk scan against the index snapshot loaded above
> — are candidates, not findings: they are confirmed by exactly one cheap re-read
> (`_confirm_cross_source`) before being reported, so a mutation racing the scan can no longer
> produce a false drift warning.

`backend_reconciled` was not cross-source before this commit: `managed_paths` is derived from
`ctx.paths.config.active_backends` alone, so a racing mutation could not move it. `_live_roster_slugs`
makes it index-derived for the first time, and it is reported straight from the scan — only
`index_reconciled` is held back for confirmation (`squad_global = {k: v for k, v in
SQUAD_GLOBAL_CATALOG.items() if k != "index_reconciled"}`).

Driven — a retirement committing between the snapshot `check()` takes and the disk probe:

    index = await svc.store.load()                      # the snapshot check() takes
    ctx   = SquadGlobalContext(index=index, …)
    _backend_reconciled(ctx)                            -> []            (before)

    # a second service retires the role; its pointer is withdrawn
    await svc2.set_status(devops_role_id, "Archived")
    Path(".claude/agents/devops.md").exists()           -> False

    _backend_reconciled(ctx)                            ->
      warn  .claude/agents/devops.md  managed pointer missing — run `sq sync` (backend: claude_code)

    await svc.check()                                   -> []            (a fresh run is clean)

Filed low, not higher: it is warn-level, so the exit code is unaffected; it clears on the next
run; and the window is one index load wide. But it is exactly the false positive
`_confirm_cross_source` exists to eliminate, the message tells the operator to run a command that
will do nothing, and `check`'s docstring now under-describes its own behaviour — a future reader
will believe every cross-source claim in this command is confirmed.

The confirm round is already keyed by item id and re-reads item files, so folding a
path-existence claim into it is not a natural fit; re-probing only the paths that came back
missing, against a freshly loaded index, would be the cheap equivalent. Either way the docstring
should stop promising what this rule does not do.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-22T12:21:16Z] Elias Python:
  - Fixed: split _backend_reconciled (_services/_validators.py) into two. The top-level managed_paths loop stays there, unconfirmed (disk+config only, cannot flicker). The per-entry managed_entry_paths loop moved out into two new functions, backend_entry_candidates (scan-time candidates) and backend_entry_missing (single-candidate confirm predicate, same shape as on_disk_not_indexed/not_on_disk) -- both routed through check()'s existing _confirm_cross_source, which now reloads the index once and recomputes each backend's live-roster set fresh before re-checking any candidate.
  - check()'s own docstring updated to name the per-entry pointer claim alongside status/parent drift and index/disk reconciliation as one of the confirmed cross-source claims -- it no longer under-describes its own behaviour.
  - Driven, the exact false positive from the finding, reproduced with two real coroutines and a real transaction (not a stale-snapshot harness): activate qa, race check() against a concurrent retirement (set_status Archived) that commits while check's scan is paused right after its index snapshot loads. Before the fix: warn '.claude/agents/qa.md managed pointer missing'. After the fix: no issue reported -- the confirm round's fresh reload sees qa as Archived and drops the candidate.
  - New test: tests/service/test_check_confirms_cross_source_claims.py::test_backend_entry_pointer_candidate_from_a_racing_retirement_is_not_reported, in the same file/section as the existing drift/reconciliation racing tests. Confirmed it reddens against the pre-fix code (stashed the fix, re-ran, got the exact false-positive warn line back).
  - Existing tests/service/test_backend_reconciled_per_entry_pointers.py drove per-entry warn behaviour by calling backend_reconciled directly (bypassing the confirm round entirely) -- updated the 7 that asserted per-entry behaviour to go through svc.check() instead, the real confirmed path; the 3 that test only the top-level/error/scoping behaviour of the trimmed backend_reconciled were untouched and still pass.
  - Gates: pyright/ruff/ruff format clean; tests/meta clean; targeted role/sync/check/backend/validators suite (916 tests) green; sq check clean on this repo.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Warn-level rationale is false: gitignoring .claude still exits 3

<!-- sq:finding:F4:body -->
**driven.**

The warn level chosen for the per-entry report is right. The reason recorded for it, in shipped
source and in the shipped changelog, is not true of the default backend.

`_backend_reconciled`'s new docstring:

> A per-entry roster pointer (`managed_entry_paths`) is **warn** — an adopter who has deliberately
> gitignored `.claude/`/`.agents_md/` made a real, supported choice, so a fresh clone must not
> fail this repo's own gate, or any adopter's, over that choice.

`AgentBackend.managed_paths`' new docstring says the same thing, and the 0.13.1 changelog says it
to adopters: "leaving the exit code alone, because not tracking generated config is a supported
choice".

Driven on a two-backend squad, simulating exactly that adopter by removing the gitignored
directory:

    rm -rf .claude
    sq check      exit 3
      error  .claude/settings.json: managed file missing — run `sq sync` (backend: claude_code)
      warn   … 18 per-entry pointer lines …

`.claude/settings.json` is a declared `managed_paths` entry, reported at error. So the adopter
whose choice this rationale is written to protect fails the gate anyway, at exit 3 — and did
before this change too, which means the exit-code regression the warn level was chosen to avoid
never existed for that shape. (`sq init` does not gitignore `.claude/` itself; its `.gitignore`
contains only `.squads.toml.*.tmp`. The adopter has to opt in, which is the case the rationale
names.)

Filed low because the *ruling* still stands on its own merits — warn is the right level for a
per-entry pointer, and this does not add a new error to anyone's gate. What is wrong is the
justification, stated three times, in the place a future maintainer will read when deciding
whether to raise the level later, plus once in adopter-facing text where it reads as a guarantee.
This is the same defect class as BUG-779/780 (a comment asserting something the code does not
do), reintroduced by the commit that fixed those.

Either correct the three statements to say what is actually true (warn because a per-entry
pointer's absence is recoverable by `sq sync` and does not by itself mean the backend was never
scaffolded), or take up the question the rationale implies and the manager's own note on BUG-784
left open — whether erroring on `settings.json` for an adopter who deliberately does not track
generated config is defensible.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-22T12:19:45Z] Theo Writer:
  - Adopter-facing half is corrected: the changelog no longer justifies the warn level by the gitignore argument. It now says the level plainly — a missing per-entry pointer is warn because running sq sync recovers it and it does not by itself mean the backend was never set up, so your exit code is unchanged; a missing top-level managed file is still an error, so a backend directory deleted wholesale still fails.
  - Driven on a two-backend-free squad after the tree came back green: one pointer removed gives warn at exit 0; rm -rf .claude gives error on .claude/settings.json plus warns, exit 3 — which is your finding, stated as behaviour rather than as a rationale.
  - Note the source side of your finding is partly still open: _base.py managed_paths docstring (around the managed_entry_paths reference) still carries the gitignore rationale, while _validators.py backend_entry_candidates has been corrected. Out of my boundary this pass — flagging for whoever owns src. @reviewer
- [2026-08-22T12:21:29Z] Elias Python:
  - Fixed: corrected both false docstrings, level unchanged (still warn).
  - AgentBackend.managed_paths (_backends/_base.py): dropped the 'an adopter who has deliberately gitignored ... must not fail the gate over that choice' claim. Corrected wording: gitignoring does not escape sq check -- the same backend's top-level managed_paths entry (e.g. claude_code's .claude/settings.json) is already error and already fails a fully gitignored directory, before and after the per-entry rule existed. The honest reason: a per-entry pointer going untracked while the top-level files stayed tracked was previously invisible to sq check altogether (not error, not warn, nothing); warn keeps that previously-silent shape's exit code unchanged rather than adding a new error to a patch release.
  - _backend_reconciled's docstring (_services/_validators.py) -- as part of the F3 split, the per-entry rationale moved to backend_entry_candidates' own docstring, restated there in the same corrected wording (not the false one).
  - Driven, re-confirming the repro cited in the finding still holds after the docstring fix (unaffected by it, since only comments changed): two-backend squad, rm -rf .claude, sq check -> exit 3, error on .claude/settings.json, warn lines on the per-entry pointers.
  - No CHANGELOG entry -- this is a comment-only correction with no adopter-visible behavior change; the manager has already corrected the adopter-facing text and the tech-writer is auditing it.
  - Gates: pyright/ruff/ruff format clean; tests/meta clean; targeted role/sync/check/backend/validators suite (916 tests) green; sq check clean on this repo.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Two 0.13.1 changelog claims overstate history and scope

<!-- sq:finding:F5:body -->
**read** (both claims), **driven** (the writer count).

Two statements in the 0.13.1 changelog do not hold. Both are adopter-facing, and one is
contradicted by another entry in the same section.

**1. "matching how a role override has always treated a blank field"** — from the blank-`--name`
entry. The role-override blank-field refusal is not long-standing behaviour: it ships in this same
release. Four entries further down the same `### Fixed` list:

> **A role override declaring an empty or whitespace-only value is refused, not rendered.**
> `full_name = ""`, `title = ""`, `mission = ""` … used to pass validation silently and reach
> every generated surface broken

Confirmed against the released tree: `_refuse_blank_strings` is absent from `v0.13.0`
(`472e7b6`, unreleased at the tag). An adopter reads "has always" as "this is the long-standing
convention the CLI now conforms to", when in fact both halves are new in the same version. Say
"matching the blank-field refusal introduced alongside it" and the sentence is both shorter and
true.

**2. "produced the same 'run `sq repair`' warning two or three times in one run, once per refresh
writer that hit the same guard"** — from the dedup entry. There are exactly two such writers.
`grep -n "update_frontmatter" src/squads/_services/{_base,_maintenance}.py` gives two call sites
reachable from the sweep — `_refresh_catalog_extra` (`_maintenance.py`) and
`_refresh_role_skills_extra` (`_base.py`) — and the sync loop calls each once per role. Driven:
the pre-fix tree prints the line exactly twice, never three times. "Twice" is the accurate number
and is no less alarming.

Filed low — nothing is broken, and the entries describe the right fixes. Filed at all because a
changelog is what an adopter benchmarks against and files a bug on, and this is the third
consecutive review on this branch to find an overclaiming entry (REV-757 F13, REV-770 F2). The
pattern is worth naming, not just the instances.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-22T12:19:34Z] Theo Writer:
  - Reauthored the whole 0.13.1 section as its owner: 2 Added + 10 Fixed, every history claim re-checked against the v0.13.0 tree rather than the working tree.
  - Your two corrections hold. (1) _refuse_blank_strings is absent from v0.13.0, so "has always" was false — I resolved it structurally instead of by rewording: the flag refusal and the override-field refusal are now one entry, so the relationship is shown rather than asserted. (2) Exactly two writers today (_refresh_catalog_extra + _refresh_role_skills_extra, dedup by exact text), so "twice" is right; that entry is now merged into the check-side divergence entry, since one divergence reported by two commands is one adopter story.
  - Fourth overclaim of the same family, found and fixed: the role-override entry said a declared one-line description was "previously ignored no matter what it said". False at the tag — activate_role wrote extra.description from the resolved role, so a description declared before activation did reach the pointer. What never happened was a later edit reaching it, because description was not in RoleDef._EXTRA_FIELD_KEYS at v0.13.0 and so was never reconciled on sync. Entry now says that.
  - Also fixed: a garbled double-splice in the per-entry pointer entry (the warn clause and the top-level clause each appeared twice); an index-parse count written as "two rather than three (and the addressed form five)", which I re-measured to 1 read + 2 parses with an override and 1 without; and two adjacent name entries that read as contradicting each other on whether a lost name self-heals.
- [2026-08-22T13:49:27Z] Catherine Manager:
  - Fixed. The tech-writer now owns this section and reauthored it end to end, verifying every historical claim against the v0.13.0 tree rather than the working tree. He found a fourth overclaim this finding did not name - the role-override entry claimed a declared description was previously ignored no matter what it said, when in fact a description declared before activation did reach the pointer and only a later edit never did - and he repaired a garbled double-splice that was mine, from editing the same sentence twice by hand. I have recorded the process correction: I stop splicing dev-handed prose into that file.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — agents_md per-entry report names write-only files no host reads

<!-- sq:finding:F6:body -->
**read** (the write-only property, from the backend's own two docstrings), **driven** (the counts).

A premise question about half the new report, not a correctness bug in it.

The `agents_md` backend's `.agents_md/roles/<slug>.md` and `.agents_md/skills/<slug>.md` files
exist only so `generate_role_entry`/`generate_skill_entry` can satisfy the `Artifact` contract.
The backend says so twice, in as many words:

> The staging files under `.agents_md/roles/` are output only — one file per role so
> `generate_role_entry` satisfies the `Artifact` contract — and are never read back.
> (`write_managed`)

> It builds that entirely from the `RoleView`s it is passed — the staging files are write-only
> artifacts, never an input, so this backend never reads back its own output. (module docstring)

Nothing reads them: not `sq`, and not the non-Claude agent tools, which consume `AGENTS.md`. So
their absence has no effect on any consumer, which is a stronger statement than the justification
`managed_entry_paths` gives for reporting them ("their own absence is invisible in `AGENTS.md`
itself, which is exactly why this method exists") — invisible *and* inconsequential.

Driven, on a squad with `agents_md` enabled and a full roster:

    rm -rf .agents_md          # every staging file, nothing else
    sq check                   exit 0, 18 warn lines, "run `sq sync`"
    sq sync                    18 "was missing — regenerated by this sync (backend: agents_md)"
    AGENTS.md                  complete and correct throughout — roster, missions, cheatsheet

The count scales with the roster, and it lands on a gate this repo treats as must-be-clean. The
`claude_code` half of the report is a different thing entirely and is clearly worth having: a
missing `.claude/agents/<slug>.md` means the agent host genuinely cannot dispatch that role.

The changelog's framing collapses the two: "reported nothing at all, so a clone could claim a full
roster while the agent host found none of it — one role's agent pointer, a skill pointer, an
`AGENTS.md` staging file". For the staging file the agent host finds the whole roster, because it
reads `AGENTS.md`.

Two directions worth considering rather than one recommendation. Either the report is right and
the framing should distinguish "the host cannot see this role" from "this backend's bookkeeping is
incomplete"; or the `agents_md` staging files should not be declared here at all, which raises the
sharper question of whether files nothing ever reads should be written in the first place, or
whether the `Artifact` contract they exist to satisfy is the thing to relax.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-22T14:13:19Z] Elias Python:
  - Decision (op-pierre): stop generating the .agents_md/roles|skills staging files at all, rather than reword the report or delete only the files.
  - generate_role_entry/generate_skill_entry write nothing now; each returns a pathless Artifact naming the (unwritten) legacy path — the ABC/Artifact contract needed no path-must-exist change, so neither stop condition fired. managed_entry_paths override dropped for agents_md -> falls to the ABC default ([]), so check/sync no longer name these files (F6's own resolution, confirmed not coded separately).
  - Pre-existing .agents_md files on an upgraded squad: generate_role_entry/generate_skill_entry and remove_artifacts now delete-if-exists at that legacy path, so one ordinary sq sync cleans up any leftover file for a role/skill still in the roster (live or retired). A leftover file whose item was removed outright is never visited by sync; candidate_orphans (unchanged logic) still reports it on sq adopt -- driven end to end in a scratch squad (copied old-build leftovers in, ran sq sync, matching-slug files gone, stray unknown-slug file survived and was flagged by sq adopt).
  - AGENTS.md verified byte-identical: fresh init+sync and a role-rename-via-override scenario, diffed against the pre-change build, both empty. Retire/reactivate cycle and sq check/sq repair stay clean on both backends.
  - Commit a3fa3a9 on release/0.14 (src/squads + tests only).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T11:47:11Z] Paul Reviewer:
  - ChangesRequested on F1 alone. Do not cut 0.13.1 from this state.
  - F1, driven against v0.13.0 installed from its own tree: a squad that named an agent with a whitespace-only --name on the last released version cannot run sq sync or sq role <slug> show at 0.13.1. The value is durable on 0.13.0 across repeated syncs with sq check clean; on 0.13.1 the sweep aborts on the first offending role and regenerates nothing, sq check still says "no issues", and neither sq repair nor archiving the role clears it - only deleting the entry does. Both role shapes are affected; the developer shape needs no precondition at all. The refusal is right on the input side, where it already is at both CLI sites; what needs fixing is the read path weaponising it against data a previous release wrote.
  - F2 is cheap and worth doing in the same pass: the increment added an eighth abstract method to AgentBackend, which docs/stability.md and docs/backends.md both state does not happen, and the docs own seven-method example no longer instantiates. Dropping the abstractmethod decorator for a return-empty default keeps the promise and changes nothing else. F3-F6 are low; none of them loses anything.
  - The fold-in equivalence holds: 44 driven shapes, seam-refuses matches check-reports in both directions, exemptions and invented timestamps intact, sq repair clears every reported shape, and no false positive across a 16-step lifecycle. A clean squad sync and check output is byte-identical to the pre-commit tree. The retirement and dropped-type paths are correct, and the sync dedup is both reachable and properly tested (the new test counts lines rather than substring-matching).
  - The edited migration test is justified: the skew it now repairs away is real, is created by the test own index-bypassing helper, and run_pending_migrations does call repair() after every migration - so the assertion is strictly stronger than before, not weakened.
  - @python-dev for F1 and F2. @manager: the release-gate answer is no until F1 is closed.
- [2026-08-22T11:49:24Z] Catherine Manager:
  - F1 confirmed independently and accepted as a release blocker. Drove it by planting a stored blank name in both the frontmatter and the index - the state v0.13.0 allowed - then running this build: sq sync exits 1 and regenerates nothing, sq role show exits 1, and sq check reports no issues at exit 0, so the operator is told neither what is wrong nor how to clear it. Cutting 0.13.1 in this state would brick sq sync for any adopter who did what the previous release permitted.
  - The principle the fix must follow, and it is already this codebase convention: validate at the input boundary, tolerate at the read boundary. Item.from_frontmatter tolerates loose spellings for exactly this reason. Our refusal belongs where an operator supplies a name, not where stored data is read back.
  - F2 accepted too: docs/stability.md and docs/backends.md both promise exactly seven abstract methods and that the set does not grow, and a patch release that grows it makes a published contract false. Taking the reviewers own remedy - a default implementation rather than an eighth abstractmethod - which keeps the promise and changes nothing else.
- [2026-08-22T14:17:19Z] Catherine Manager:
  - Closing this review. All six findings are fixed and each was driven by me as well as by its author. F1 was the release blocker and the reason this review existed: a stored whitespace-only name, legal on 0.13.0, made sq sync exit 1 and regenerate nothing while sq check reported no issues - we would have shipped a patch that bricked sync for any adopter who did what the previous release allowed. The fix tolerates stored data at the read boundary and heals it on the next sync, while the input-side refusal stays.
  - Three of the six were a stale rationale outliving the code it described - the warn level justified by an argument untrue of the default backend, a comment claiming nothing ever wrote extra.description, and a docstring arguing the stream choice was a --json concern. A wrong explanation propagates further than a wrong line, so each correction was required rather than optional.
  - Two pre-existing tests were found asserting their own defect: one pinned board list stdout stream, one pinned the inbox and search error text in stdout. Both would have made the defect permanent and both surfaced only because someone changed the behaviour they pinned.
<!-- sq:discussion:end -->
