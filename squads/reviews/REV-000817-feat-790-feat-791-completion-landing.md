---
id: REV-817
sequence_id: 817
type: review
title: FEAT-790 / FEAT-791 completion landing
status: Approved
author: reviewer
refs:
- FEAT-790:addresses
- FEAT-791:addresses
description: 'Review of e397ef5..6d27354 on release/0.14: TASK-797, 798, 800, 801,
  805, 807, 809, 810, 811, 812, 814'
subentities:
- local_id: F1
  title: Generator sweep deletes shipped store history when the running version is
    already released
  status: Fixed
  severity: high
- local_id: F2
  title: Uniformity guard cannot see a sixth kind, and omits CLI reachability
  status: Fixed
  severity: medium
- local_id: F3
  title: Roles catalog refusals blame the bundled catalog for an adopter's own override
  status: Fixed
  severity: medium
- local_id: F4
  title: Unknown-top-level-key refusal never names the running version
  status: Fixed
  severity: medium
- local_id: F5
  title: Migration import guard is bypassed by a module import plus attribute access
  status: Fixed
  severity: medium
- local_id: F6
  title: Catalog [dev] override does not reach the un-added dev-role preview
  status: Fixed
  severity: low
- local_id: F7
  title: Roles-catalog stamp finding still says the CLI has no roles verbs
  status: Fixed
  severity: low
- local_id: F8
  title: Cheatsheet lost the duplicates-are-closed-as-Cancelled guidance
  status: Fixed
  severity: low
- local_id: F9
  title: New hygiene scans carry hand-maintained literal lists unpinned to their sources
  status: Fixed
  severity: low
created_at: '2026-08-25T22:46:30Z'
updated_at: '2026-08-26T09:21:55Z'
---
<!-- sq:body -->
## Scope

Six commits on `release/0.14`, `e397ef5~1..6d27354` (the stated range `e397ef5..6d27354` excludes
`e397ef5`, which carries TASK-797 and TASK-809 — reviewed here). Eleven tasks: TASK-797, 798, 800,
801, 805, 807, 809, 810, 811, 812, 814. The earlier landing (`958974c`) is REV-808's and is not
re-reviewed.

Driven on real squads: nine scratch squads built with `sq init` and mutated through the CLI, a
copied source tree for generator write modes, and in-process probes against the shipped manifest,
content store and the two new hygiene scans. Every claim below is labelled **driven** (I ran it),
**read** (I traced the code), or **inferred**. Nothing was fixed, no source or test was edited, no
task status changed.

## Verdict

One high finding, four medium, four low. The engine work itself is sound under drive — the ref-kind
semantic binding, the undeclared-edge traversal, the refrozen runner and the skew-diagnosis
discrimination all hold when attacked. The high finding is not in the engine: it is in the
generator sweep, whose safety argument has a false premise that the repo enters the moment 0.14.0
is tagged.

## Category results

**1. Fixture edits that could mask — clean.** Read every one.

- The ~25 `WorkflowSpec` fixtures that gained a `ref_kinds` key add `{related: default, scopes:
  preload}` (or `base.ref_kinds`) and nothing else; `WorkflowSpec.ref_kinds` defaults to `{}` and
  the per-capability floor runs at load, so a directly-constructed spec that never reaches
  `default_ref_kind()` still needs no entry. No fixture's assertion changed with the key (**read**).
- `tests/unit/test_specmerge_ordered_entry_point.py`'s ~10 `top_level_keys=None` → explicit
  frozenset edits each pass exactly the fixture's own top-level keys, so the top-level check stays
  a no-op and every test asserts what it did before (**read**).
- The lint test split is real orthogonality, not a way past a failure. The renamed
  `..._with_a_stamp_the_bundle_changed_since` uses `0.13.1`, a stamp the manifest genuinely carries
  with a changed bundled `workflow.toml` behind it; the new `..._squads_carries_no_history_for`
  covers `0.0.1`. Both outcomes are separately pinned by the dedicated error/warn tests, so the
  parametrized agreement test's three vacuous (both-silent) legs cannot hide a regression (**driven**,
  see category 3).
- The row-count pin moving from `9` to `len(spec.ref_kinds)` is strictly stronger, not weaker: the
  same test now also asserts every declared code has a row, and two new tests drive the adopter
  cases (an added kind gains a row; a renamed default reads its own name) (**read**).
- `tests/service/test_remove.py`'s severing test was parametrized to `("", "blocks")`, restoring the
  bare/default-kind leg the earlier swap had dropped. Both legs exercise the width-tolerant
  predicate (**read**).
- `tests/integration/test_override_scaffold_scan_diff_update_and_check.py`'s warn→error edits are
  the intended tightening and are accompanied by two new add-only-stays-silent tests (**read**).

**2. The uniformity guard's blind spot — one medium finding (F2).** The guard drives all five kinds
through the real service entry points and each of the five parts is verified by removal, which is
good. But its kind set is a hand-written `_KIND_FIXTURES` dict pinned by regex to a hand-written
comment on `OverrideEntry.kind`; there is no registry in code for either to derive from
(`scan_overrides` is five open-coded blocks). And CLI reachability — the exact axis on which `roles`
shipped inert — is not one of the elements.

**3. The de-forked stamp finding — clean.** Drove `sq check`, `sq workflow lint`, `sq override list`
and `sq override diff workflow` over one squad across six override states: add-only unstamped,
shadowing unstamped, shadowing stamped `0.13.1` (bundled changed), shadowing stamped `0.0.1`
(unrecorded), shadowing stamped at the running version, and add-only stamped `0.13.1`. `sq check`
and `sq workflow lint` agree on level **and** message in all six (**driven**). `sq override list`'s
state classifier reports `drifted` for an unstamped add-only override where the other two stay
silent; that divergence is deliberate and documented in place at `_overrides/_service.py:220-231`
(state is not the stamp-obligation finding), so it is not filed as a defect.

**4. The roles catalog's three layers — two medium findings (F3, F4) and one low (F6).** The
capability itself works. Driven: `sq override scaffold roles` → edit → `sq role <slug> show` picks
the catalog document up on both the **not-yet-activated** path and, after `sq sync`, on the
**activated** path (panel and rendered body both); `sq role catalog` reflects it; per-slug
`.overrides/roles/<slug>.toml` correctly wins field-by-field over the catalog document while the
catalog document's other fields survive; `sq override list/diff/update roles` and the unstamped-
shadowing error (exit 3) / add-only silence all behave. What is wrong is the diagnostics (F3), a
missing acceptance clause (F4), and one un-threaded resolver (F6).

**5. The generator sweep — one high finding (F1).** The sweep is correct for every case its tests
cover, including the sibling-task case the brief names: I edited one of the six artifacts whose only
content the `0.14.0` entry names, regenerated, and the orphan was swept with every index-named hash
still resolving (**driven**). It breaks on a case no test reaches — see F1.

**6. Adopter-facing prose — one low finding (F8); the two judgement calls assessed below.**

- **Dropping the "Direction convention" column: sound, and nothing a reader needed is lost.** The
  column's content is recoverable from what replaced it: every declared hint reads in `A <kind> B`
  form, and the derived line binds A to the item you add the edge to ("Every edge is stored on the
  item you add it to — `A <kind> B` lives on A"). The two facts the column alone carried — the
  dependency pair being one edge, and the superseded record's expected status — were moved into that
  line and render correctly (**read**, against `tests/goldens/workflow_cheatsheet.txt:110-124`). The
  stated ground (nothing in the spec declares it) is also true: there is no direction field on
  `RefKindSpec`, so a generated row could not have carried it for an adopter-declared kind.
- **`targets`' hint rendering in adopter-facing text: real, already tracked, and unique.** Grepped
  every `hint =` in `src/squads/_specs/workflow.toml`: `targets` is the only one naming a mechanism
  that does not ship (**driven**). Nothing new filed.

## Already-tracked gaps — confirmed, with a scope note

Both TASK-798 gaps now carry tasks in the working tree (TASK-815, TASK-816), and TASK-813 is Draft.
Nothing new is filed for any of them. One scope note, because the tracked description is narrower
than the instances on disk:

- The `ref_kinds` omission is **not** confined to "docs/overrides.md not naming it among the workflow
  document's sections". It recurs at `docs/overrides.md:199`, `:217`, `:222`, `:610`, `:1027` and at
  `docs/internals.md:54`; and `docs/overrides.md:226-229` quotes a **verbatim refusal the tool no
  longer emits** — the doc shows `['collections', 'items', 'lifecycles', 'roles', 'selected',
  'statuses', 'subentity_kinds']` while the real message now includes `'ref_kinds'` (**driven**).
  That last one is a different defect class from a missing list item: it is a copy-pasteable claim
  the reader can disprove in one command. Worth folding into TASK-815's scope rather than leaving it
  to be found again.
- The `targets` hint is a single instance, confirmed above.

## Nits, not filed as findings

- `tests/goldens/workflow_cheatsheet.txt` now ends without a trailing newline (the template's new
  `{% if %}` chain ends the file), where it previously did not. Cosmetic, but it is generated output
  that three goldens carry.
- `sq override diff --role architect` prints `Override: --role architect (kind: role)` — the flag is
  deliberately echoed into the label (`_cli/_override.py:369-370`) to disambiguate the per-slug kind
  from the `roles` catalog kind. Intentional; reads oddly.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 817 add-finding "…" --severity medium`; track with `sq review 817 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | Generator sweep deletes shipped store history when the running version is already released |
| F2 | 🟡 medium | Fixed |  | Uniformity guard cannot see a sixth kind, and omits CLI reachability |
| F3 | 🟡 medium | Fixed |  | Roles catalog refusals blame the bundled catalog for an adopter's own override |
| F4 | 🟡 medium | Fixed |  | Unknown-top-level-key refusal never names the running version |
| F5 | 🟡 medium | Fixed |  | Migration import guard is bypassed by a module import plus attribute access |
| F6 | 🟢 low | Fixed |  | Catalog [dev] override does not reach the un-added dev-role preview |
| F7 | 🟢 low | Fixed |  | Roles-catalog stamp finding still says the CLI has no roles verbs |
| F8 | 🟢 low | Fixed |  | Cheatsheet lost the duplicates-are-closed-as-Cancelled guidance |
| F9 | 🟢 low | Fixed |  | New hygiene scans carry hand-maintained literal lists unpinned to their sources |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Generator sweep deletes shipped store history when the running version is already released

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**Severity: high. Driven.**

`scripts/gen_template_manifest.py:176-193` sweeps every blob no index entry references, after
replacing `manifest[version]` with the current tree's hashes. Its safety argument, stated at
`:19-24` and in ADR-777 C1, is:

> A run rewrites exactly one entry, the current version's, so the only blobs a sweep can strand are
> revisions that entry alone named; historic entries are never rewritten, so no revision they name
> can become unreferenced and the sweep provably cannot reach one.

**The premise "the current version's entry is not a historic entry" is false whenever
`[project].version` names a version that has already shipped** — which is the repo's steady state
between a release cut and the next bump. `0.14.0` is unreleased today, which is the only reason this
is latent rather than live.

Driven, in a copied tree (`src`, `scripts`, `pyproject.toml` copied to a scratch dir, repo untouched):

```
# pyproject [project].version -> 0.9.0   (a shipped release; 3 blobs are named only by its entry)
$ python3 scripts/gen_template_manifest.py
wrote manifest for v0.9.0: 29 artifact hashes (0 new blob(s) inserted, 3 orphaned blob(s) swept
from the content store)
```

The three destroyed blobs are the shipped `0.9.0` revisions of
`_rendering/templates/agents/memory_skill.md.j2`, `.../agents/squads_skill.md.j2` and
`_rendering/templates/workflow.md.j2`. Before the sweep landed, the same mis-ordered regeneration
corrupted only the index entry — recoverable from the tag, which is precisely the bound the original
never-deletes clause was written to hold.

**The documented recovery no longer works, and fails silently.** Continuing the same probe: restore
the `0.9.0` index entry from HEAD (the documented fix — check the prior entry out from the tag), set
the version back to `0.14.0`, and:

```
$ python3 scripts/gen_template_manifest.py --check
manifest v0.14.0 is current (29 artifacts, store coverage ok)      # exit 0
$ python3 scripts/gen_template_manifest.py
manifest already up to date for v0.14.0 (29 artifacts)             # re-heals nothing
# 0.9.0 hashes still unresolvable: 3
```

Three reasons it stays hidden:

1. `--check` verifies store coverage only for **the running version's own entry**
   (`:140-146`), so a dangling reference from a historic entry is invisible to it.
2. `--check`'s new orphan scan is the mirror image of what is needed here — it detects extra
   blobs, never missing ones.
3. Write mode is insert-if-absent **from the current tree only**, so a hash a restored historic
   entry names but the tree no longer produces is never re-inserted.

`tests/meta/test_override_manifest_and_stamp_freshness.py:208` (`test_every_index_named_hash_resolves
_in_the_store`) would catch it in-repo — after the damage is committed, with no regeneration that
clears it.

**Why the tests cannot see the case.** Every sweep test drives `gen._current_version()`, i.e. the
repo's own `pyproject.toml` (`_run_write_mode`, `:352-355`), and the `sweep_tree` fixture copies that
file verbatim (`:328-330`). `test_a_blob_only_a_historic_entry_names_survives_the_sweep` (`:409`) is
the leg written to prove never-prune, and it too runs at the unreleased current version — so it
proves the safe half of the argument and never touches the half that is false. No test sets the
fixture's `pyproject.toml` to a version the copied manifest already carries.

**What I would want.** Either (a) the generator refuses write mode when `[project].version` already
has an index entry whose hashes differ from the current tree (the sweep's premise made checkable at
the point it is relied on), or (b) the sweep is skipped whenever the entry being replaced is not new,
or (c) at minimum `--check` verifies that **every** index entry's hashes resolve, so the corruption
is caught by the release gate rather than by a suite failure with no discharging command. Adding a
sweep test that runs at an already-carried version is the leg the guard is missing either way.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-25T23:01:59Z] Robert Architect:
  - Ruled. F1 upheld at high; ADR-777 amended in place (D1-D7). C1 sweep withdrawn: the generator steady state never deletes again, A6 never-deletes stands as written.
  - The premise is not repairable where the sweep runs. From inside the working tree, "an entry for V names hashes this run no longer names" describes an unreleased V scratch revision and a released V shipped revision identically - only publication separates them, and that is not in the tree. So scoping the sweep to blobs the run itself orphaned removes nothing (those ARE the shipped ones), and refusing an existing-and-differing entry refuses the ordinary dev loop. Published is the right discriminator, the generator is the wrong actor: a rule answering off the local tag list gives different answers per clone and fails unsafe when it cannot see a tag.
  - D3: the store is a DERIVED artifact - every hash the index names, resolved to its content, a total function of index + tags + tree. Driven on a clone: after a regeneration at 0.9.0 destroyed 3 blobs and rewrote 11 of 29 hashes, seed_content_store.py ALONE reproduced both documents byte-identically vs branch head (git diff empty), printing every correction. So removal is a rebuild from ground truth, owned by the one git-reading step A1 already sanctions - all-or-nothing, a missing tag is a refusal that deletes nothing, never a skip.
  - Correcting the finding on one point, because it sizes the fix: the corpus is NOT permanently broken. Your recovery (restore the entry from the tag) is insufficient on its own, which is what you drove; the seeder recovers fully. What is true and what carries the severity is that nothing reports the loss, nothing documents the recovery, and the corpus reads clean while broken. Same correction lands on A6, whose "no tag can restore it" was itself overstated - recorded in D7 so a later reader does not relax the rule on discovering the recovery exists.
  - D5, what --check owes: coverage verified across the WHOLE index (every version, every key) - A1 states the promise over every release the index covers, so the gate must be; the success line must state what it checked, since asserting "store coverage ok" off one entry is the defect not a wording nit; an orphan is reported and does not fail an ordinary check but fails the release gate; still writes nothing.
  - D6, coverage owed, stated so it cannot pass at the running version: the fixture takes its version as a PARAMETER and asserts it differs from the repo - that clause is what makes the rest non-vacuous. Then a case at a version the copied index already carries with hashes differing from the copied tree; a case that damages, applies the documented recovery, and asserts the whole index resolves; and a --check failure for a hash missing from a HISTORIC entry.
  - D4: an orphan-free store is a property of the release artifact, not the working tree. Your diagnosis in C1 was right - a guard with no discharging action becomes a problem - the error was giving the generator the deletion instead of moving the assertion where it is true. Between releases orphans are dev residue; the rebuild at the cut clears them; A4 ceiling measured on the rebuilt store.
  - Leaving F1 Open - not fixed until the work lands. @tech-lead for the tasks: generator sweep removal + --check widening, the rebuild mode and its refusal, the release gate, and the D6 fixture parametrisation. Repo state today: 85 blobs, 85 referenced, 0 unresolvable, 0 orphans, manifest and store clean vs git - exposed, not damaged, and the window opens the moment 0.14.0 is tagged.
- [2026-08-25T23:11:01Z] Olivia Lead:
  - Authored as TASK-822 (Ready, urgent, python-dev, FEAT-791 US1) — "Rebuild the content store from ground truth and retire the sweep". Five subtasks: withdraw the sweep, the rebuild and its all-or-nothing refusal, the whole-index --check widening, the orphan assertion moving to the release gate, and the D6 fixture parametrisation.
  - Verified every cited line before writing. The sweep at gen_template_manifest.py:186-193 with its argument restated at :19-24 and :27-29; _check_mode binding recorded = manifest[version] at :127 so coverage is one entry, with the orphan scan at :147-152 detecting extra rather than missing and the success line at :161 claiming more; the sweep_tree fixture copying pyproject.toml verbatim at :328-330 and _run_write_mode reading _current_version() at :352-355.
  - Repo state confirmed independently: 16 indexed versions, 85 blobs, 85 referenced, 0 unresolvable, 0 orphans, no diff vs git, v0.14.0 untagged. One extra fact that shapes ST2 and is not in the ruling — all 15 non-running indexed versions are tagged locally and only 0.14.0 is not. So the happy path is reachable today, and the seeders existing skip at :145-149 is correct for exactly one version and is the forbidden skip for every other. The discriminator is stated on the subtask rather than left to be inferred.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Uniformity guard cannot see a sixth kind, and omits CLI reachability

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Severity: medium. Read, with the CLI half driven.**

Asked directly: **would the guard catch a sixth kind shipping with a missing part? No — not unless
whoever adds the kind also remembers to add it to the guard.**

`tests/meta/test_override_kind_uniformity.py` enumerates kinds in exactly two places, both
hand-written:

- `_KIND_FIXTURES` (`:181-227`) — one literal row per kind;
- `OverrideEntry.kind`'s comment (`_overrides/_service.py:87-90`), which
  `test_the_registry_covers_every_kind_the_docstring_names` (`:295`) regex-scrapes and pins against
  `_KIND_FIXTURES`.

Neither derives from code that dispatches. There is **no registry**: `scan_overrides`
(`_overrides/_service.py:278-332`) is five open-coded blocks, and `check_override_issues` and
`diff_override` are likewise per-kind branches. A sixth kind added to those three functions and to
nothing else passes both the four-part test and the docstring cross-check, because both
enumerations go stale together. The guard's own docstring calls `_KIND_FIXTURES` "the registry",
which is the part I would push back on: it is a second copy of the list, not a derivation of it.

The cheap fix that would make it structural: derive the expected kind set from
`{e.kind for e in scan_overrides(squad_dir)}` on a squad carrying one override of every kind, and
assert `_KIND_FIXTURES` covers exactly that. Then a sixth kind that reaches `scan_overrides` — which
it must, to be an override kind at all — fails this file until it is wired.

**Should CLI reachability be its fifth element? Yes.** `roles` shipped with a manifest entry, a
state classifier, both diff deltas and (after TASK-801) a stamp finding, and was still unreachable
from `sq override scaffold|diff|update` — the four-part guard passed it. The guard drives
`override_service.scan_overrides` / `.check_override_issues` / `.diff_override` directly
(`_uniformity_gaps`, `:238-283`), i.e. one layer below where the gap was. A fifth element asserting
that each kind's three verbs are reachable through the CLI runner, by the argument form a human
would type, is the leg that would have caught it.

Driven today, all five kinds are reachable — this is a guard gap, not a live gap:

```
$ for k in items/task.md.j2 "--role architect" workflow playbook roles; do
    sq override scaffold $k; sq override diff $k; sq override update $k; done
# all 15 invocations exit 0, and each diff header reports the intended kind
```

Also worth noting, since it is the same shape one layer down: the `_uniformity_gaps` docstring says
each check goes "through the same top-level dispatcher every `sq override` command uses". That is
true of the service layer and not of the CLI layer, and the distinction is exactly the one that let
`roles` through.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-25T23:03:17Z] Olivia Lead:
  - Triaged to TASK-818 (Ready, FEAT-791 US5). Its own task, not a rider: this is the guard that passed an unreachable kind, so it is not something to fold into a task about the kind it missed.
  - CLI reachability becomes the fifth element. The evidence is direct — roles satisfied all four service-level parts and was still unreachable from the command line, and the guard drives the service layer one layer below where the gap was. Reachability also has to assert the resolved kind, not just exit 0: roles would have mis-routed to template.
  - The kind set is derived from scan_overrides rather than pinned to the OverrideEntry.kind comment. Pinning one hand-written list to another does not detect a kind absent from both. Deriving the per-kind registry in _overrides/_service.py is out of scope — that is a service refactor, not a guard fix.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Roles catalog refusals blame the bundled catalog for an adopter's own override

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**Severity: medium. Driven.**

Every validation failure of the **merged** role catalog is reported as a failure of the **bundled**
one. `_roles/_loader.py:212`, `:220` and `:309` all raise `Invalid bundled role catalog...`, and
`_validate` / `_build_catalog` now run on the result of merging `.overrides/roles.toml` over the
bundled base (`load_role_catalog`, `:160-194`). The wording predates the override path and was not
moved with it.

Driven — a scratch squad, `.overrides/roles.toml` carrying only a `[selected]` deselect of one
bundled role, which TASK-800 sanctions as the way to hide a role from `sq role catalog`:

```
[selected]
roles = ["manager","architect","tech-lead","reviewer","qa","devops","product-owner"]
```

```
$ sq role catalog
error: Invalid bundled role catalog:
  - bundle 'all' references unknown slug 'tech-writer'
  - 'all' bundle has unknown slugs: ['tech-writer']
                                                       # exit 1
```

Three things are wrong with that as a diagnosis, and the first is the one that matters:

1. **It names the wrong document.** The adopter can open the bundled `roles.toml` and see
   `tech-writer` declared and named by `all`. This is the standing rule ADR-775 A4 introduced in
   this very range — *a refusal may not assert a cause the reader can disprove* — applied to the
   sibling axis. It also names no file at all, so there is no path to the file that is actually at
   fault.
2. **It never mentions `[selected]`,** the mechanism that caused it. Nothing in the two lines tells
   the reader that deselecting a role also requires deselecting or rewriting every bundle that names
   it.
3. **The remedy is not stated.** TASK-800's design is that the existing floor does the work "with no
   deselect-specific guard, exactly as ADR-696 §4b intends" — which is right, but only if the floor's
   message reaches the adopter as guidance. As it stands, the sanctioned capability
   (`[selected] roles`) is discoverable only by trial and error: deselecting a single role produces
   two errors about a document the adopter did not write, and deselecting most of them produces
   eight (**driven**).

Suggested shape: carry the origin into `_validate`/`_build_catalog` so the message reads
`.overrides/roles.toml: role catalog invalid after merge: ...`, and give `_check_bundles` a hint line
when the unknown slug is one `[selected]` removed.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-25T23:03:30Z] Olivia Lead:
  - Triaged to TASK-820 ST1 (Ready, FEAT-791 US3). Verified: all three raise sites say "Invalid bundled role catalog" and _validate/_build_catalog run on the merged mapping, so a [selected] deselect is reported against a document the adopter can open and disprove.
  - Accepted as ADR-775 A4 applied one axis over — a refusal may not assert a cause the reader can disprove. Two more gaps carried into the task: the message names no file at all, and it never mentions [selected], the mechanism that caused it. The floor doing the work with no deselect-specific guard stays; only the diagnosis changes.
  - Acceptance includes the inverse leg: a genuinely invalid bundled catalog must still say bundled. Carrying the origin, not swapping one wrong document name for the other.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Unknown-top-level-key refusal never names the running version

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**Severity: medium. Driven, then read.**

FEAT-791's acceptance: *"A role override naming a key `RoleSpec` does not declare is refused, naming
the key **and version**."* TASK-800 repeats it, and ADR-777 §4 makes the version the load-bearing
half of the whole argument for closing the key space:

> The forward-compatibility case is served by the refusal telling the adopter **which key and which
> version**, not by discarding it.

The refusal names the key. It never names the version. Driven, on both roles kinds:

```
$ printf 'nonsense = 1\n' > squads/.overrides/roles/architect.toml
$ sq role architect show
error: .../architect.toml: nonsense: unknown top-level key 'nonsense' — use one of the accepted
top-level keys: ['agreements','can_spawn','color','description','full_name','is_default',
'mission','model','responsibilities','selected','slug','title']          # exit 1

$ printf 'nonsense = 1\n' > squads/.overrides/roles.toml
$ sq check
error corpus: could not scan the corpus: .../roles.toml: nonsense: unknown top-level key
'nonsense' — use one of the accepted top-level keys: ['bundles','dev','roles','selected']  # exit 3
```

**Read:** `_specmerge.py:523-554::_unknown_key_violations` builds the whole message
(`unknown {what} {key!r}` + `use one of the accepted {what}s: {sorted(accepted)}`) and
`squads.__version__` appears nowhere in `_specmerge.py`. Every override kind's unknown-key refusal
inherits the same shape, so this is not confined to roles.

Why the omission matters rather than being cosmetic: the accepted-set list alone tells an adopter
their key is not accepted, but not whether it is a typo, a key from a newer squads, or a key from an
older one. "…accepted top-level keys **in v0.14.0**" is the single word that converts the refusal
into the forward-compatibility answer the decision claims it already is. As written, the code ships
the closure without the compensation the decision traded for it.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-25T23:03:31Z] Olivia Lead:
  - Triaged to TASK-821 (Ready, FEAT-791 US4).
  - Pre-existing debt, not new. _unknown_key_violations landed in 2f8b1ab (2026-08-15), before this range begins, and squads.__version__ has never appeared in _specmerge.py. What is new is the promise: the roles catalog work applied the shared refusal to a fifth key space and wrote the naming-the-version acceptance clause against it without adding it.
  - Scoped at the shared helper rather than the roles layer, so one message change discharges the clause for role, roles catalog, workflow and playbook at once. Confirmed squads/__init__.py imports nothing internal, so importing __version__ into _specmerge.py introduces no cycle.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Migration import guard is bypassed by a module import plus attribute access

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**Severity: medium. Driven falsification of the guard.**

`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py` was re-derived under
TASK-809, and the re-derivation is genuinely better: the rule now turns on category ("can anything
in the live tree change what this name makes a frozen runner write?") rather than on today's
implementation, `split_ref`/`make_ref`'s permanent exemption is gone, and constants are in scope.
The **enforcement** did not follow the reasoning.

`_imported_forbidden_names` (`:87-99`) walks the AST and inspects `ast.ImportFrom` only. A plain
module import plus attribute access is invisible. Driven, against the guard's own `_scan` with a
planted runner:

```python
# src/squads/_migrations/_bypass.py
import squads._models._item as _item
def use(): return _item.make_ref('X', 'related')
```
```
_scan(tmp) -> []          # not flagged

from squads import _models
def use(): return _models._item.make_ref('X', 'related')
_scan(tmp) -> []          # not flagged

from squads._models._item import make_ref as _mr     # aliased ImportFrom
_scan(tmp) -> [('src/squads/_migrations/_bypass.py', 'make_ref')]   # caught
```

So aliasing is handled and module-level import is not. Both bypasses are the same one line a
developer writes without thinking about it, and both re-open the exact defect the guard exists to
prevent — a frozen runner whose on-disk bytes move when the live tree is refactored underneath it,
with a green suite. The docstring's claim that the forbidden set applies "unconditionally, with no
per-name exemption" is true of names and not of import forms.

Secondary, same file: `_WIRE_ENCODING_PRIMITIVES` (`:71-81`) is a hand-maintained list of six names
and nothing pins it to `squads._models._item`. Renaming any of the six would make the guard silently
vacuous for it. I verified all six currently resolve (**driven**: `[n for n in
_WIRE_ENCODING_PRIMITIVES if not hasattr(squads._models._item, n)] == []`), so this is latent, but
the assertion costs one line and the file's whole premise is that a future refactor moves things.

Suggested: extend the scan to `ast.Import` of `squads._models[...]` plus any `ast.Attribute` access
naming a forbidden identifier, and add the resolves-in-`_models._item` pin.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-25T23:03:33Z] Olivia Lead:
  - Triaged to TASK-819 ST1 (Ready, FEAT-790 US2). Verified: _imported_forbidden_names walks ast.ImportFrom only; an aliased ImportFrom is caught and a module import plus attribute access is not.
  - Grouped with F9 rather than left with the guard that re-derived it, because F5s secondary half and F9s second bullet are the same one-line pin in the same file — two tasks would have put two developers in tests/meta on the same lines. TASK-809 is linked as related.
  - Acceptance requires a no-false-positive leg: a migration module importing squads._models without naming a forbidden attribute must stay unflagged, or the next author suppresses the guard.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Catalog [dev] override does not reach the un-added dev-role preview

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
**Severity: low. Driven.**

ADR-777 §3's stated defect is that `[bundles]` and `[dev]` — "the bundle selection and the developer
name pool, model and colour" — cannot be overridden at all. `[dev]` is now honoured where a dev role
is **created**, and not where one is **previewed**.

Driven, scratch squad, `.overrides/roles.toml` carrying `[dev] model = "haiku"`, `color = "purple"`:

```
$ sq role python-dev show          # python-dev not yet added
  (unassigned — run `sq dev add --tech python`) (`python-dev`)
  title: Python developer
  model: sonnet                    # bundled default; the override says haiku

$ sq dev add --tech rust --name "Zed Probe"
$ sq role rust-dev show
  Zed Probe (`rust-dev`)
  model: haiku                     # override honoured here
```

So the preview tells the adopter one thing and `sq dev add` does another.

**Read — the cause.** `dev_base_for_slug` (`_roles/_resolver.py:419-426`) takes no `squad_dir` and
calls the bundled `dev_role(...)`, while its sibling `resolve_dev_role` (`:429-460`) does thread
`squad_dir` through `load_role_catalog(squad_dir).dev`. All three call sites of
`dev_base_for_slug` have a `squad_dir` in hand and none passes it:

- `_cli/_role.py:265` — `sq role <tech>-dev show` for an unactivated slug (the observable above);
  the line directly above it, `role_base_from_item(it, squad_dir)`, does thread it.
- `_overrides/_service.py:882` — `_role_def_as_toml`, the scaffold base for
  `sq override scaffold --role <tech>-dev`.
- `_overrides/_service.py:1450` — the base a per-slug dev override resolves against, so an override
  is diffed and shadow-classified against bundled dev defaults rather than the project's.

The scaffold path emits no field values today, so the visible consequence is confined to
`sq role <tech>-dev show`; the other two are latent. This is the same class as TASK-814's gap 2
(a resolver not threaded with `squad_dir`), one path over.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-25T23:03:44Z] Olivia Lead:
  - Triaged to TASK-820 ST3 (Ready, FEAT-791 US3). Folded in with F3 and F7 rather than given its own task: all three land in _roles/ and _overrides/_service.py, and splitting them puts two developers in the same file.
  - One correction to the finding, carried into the subtask: the three call sites are not uniform. _cli/_role.py:265 and _overrides/_service.py:1450 do have squad_dir in hand, but :882 sits inside _shadowed_bundled_role_toml(slug), which takes none — its callers are _diff_role (has one) and _role_override_shadows_bundled (has none), so threading there means changing signatures. Also flagged: the same functions bundled branch calls role_by_slug(slug), equally un-threaded; the subtask asks for a stated in-or-out call rather than a silent one.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Roles-catalog stamp finding still says the CLI has no roles verbs

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
**Severity: low. Driven, then read.**

`_overrides/_service.py:1232-1245` — `_roles_catalog_stamp_finding_gated`'s docstring states, as
current fact:

> The remediation commands named here are the **bulk** forms (`sq override update` / `sq override
> diff` with no name) rather than `... roles` — `_cli/_override.py` has no dedicated `roles`
> positional match yet (left to the task that wires the CLI verbs for this kind), so a named
> invocation would silently mis-route to the `template` kind.

That was true when TASK-800 landed it (`da55f1c`) and stopped being true one commit later, when
TASK-814 wired the verbs (`e8d35df`). Driven:

```
$ sq override update roles
re-stamped roles → v0.14.0                      # exit 0, correct kind
$ sq override diff roles
Override: roles  (kind: roles)                  # exit 0, correct kind
```

Two consequences, in order of how much they matter:

1. **The emitted `sq check` messages are worse than they need to be.** Both arms name the bulk form
   — `run \`sq override update\` to re-stamp` (`:1247-1250`) and `run \`sq override diff\` to review,
   then \`sq override update\`` (`:1256-1259`) — where every other kind names its own object
   (`sq override update workflow`, `sq override diff --role <slug>`, `sq override diff <template>`).
   A squad carrying several overrides is told to re-stamp all of them to clear a finding about one.
2. **The docstring asserts the reverse of what ships.** That is the defect class ADR-777 §4 spends a
   whole section on (`OverrideEntry.kind`'s docstring, ADR-226's stale note, ADR-696 §4b's clause) —
   worth not reintroducing in the same feature that retires three instances of it.

Also stale for the same reason: `_overrides/_service.py:1290-1293`'s reference to the split.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-25T23:03:45Z] Olivia Lead:
  - Triaged to TASK-820 ST2 (Ready, FEAT-791 US3). Verified both halves: _cli/_override.py now matches roles at :172, :326-327 and :444-445, and the sibling kinds all name their own object (_workflow/_loader.py:1069,1076; _overrides/_service.py:1397-1398) while roles names the bulk form.
  - One citation I could not confirm: the second stale reference at :1290-1293. That range is check_override_issues docstring on the dev_base_for_slug roster fallback and reads accurate to me — no "split" reference anywhere in the file. Scoped the subtask to the one instance I verified at :1237, plus a grep sweep for the same claim shape.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Cheatsheet lost the duplicates-are-closed-as-Cancelled guidance

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
**Severity: low. Read, against the goldens.**

Not the Direction-convention column — that call is sound (assessed in the review body). This is a
second, unremarked loss from making the **Meaning** column the spec's declared `hint` verbatim.

Before (`tests/goldens/workflow_cheatsheet.txt`, pre-`6d27354`):

```
| `duplicates` | A (a later filing) duplicates B (the original); A is usually closed as Cancelled | ... |
```

After (`:122`):

```
| `duplicates` | A (a later filing) duplicates B (the original) | Navigation |
```

The `; A is usually closed as {{ dropped }}` clause was template-supplied and spec-derived (it
resolved the squad's own dropped status), and it is the only place the cheatsheet told an author what
to *do* with a duplicate. It is not in the declared hint, not in the derived line under the table,
and not anywhere else in the section — `grep -i "usually closed\|duplicat"` over the golden returns
the table row alone.

Two comparable clauses survived the same rewrite and are the reason this one reads as an oversight
rather than a decision: `supersedes`' "B's status should be Superseded" moved into the derived line
("`sq check` reads `supersedes` on the newer record and expects the older one at Superseded"), and
`depends-on`'s "Equivalent to `B blocks A`" is carried in substance by the two-spellings sentence.
TASK-798's handoff comment names exactly two facts as moved; this third one was not noticed.

Reach: the cheatsheet is also the body of the `squads` skill every agent in an adopting squad reads
(`squads/agents/skills/SKILL-000200-squads.md` here), so the guidance is gone from the agent-facing
copy too.

If it should stay, the honest home is a `dropped`-status clause on the derived line, resolved the way
the supersession clause is — not back in a hand-written row.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-25T23:04:01Z] Olivia Lead:
  - Reasoning. Verified the loss: the clause lived at workflow_static.md.j2:103 as "; A is usually closed as {{ dropped or \"dropped\" }}", spec-resolved through spec.first_dropped_status, and went when the Meaning column became the declared hint verbatim. The two clauses that survived survived because they describe engine bindings the spec declares as semantic roles — supersession keys sq checks rule, the dependency pair keys sq blocked. duplicates has no binding, so the derived line has nothing to key off.
  - The spec offers exactly two homes and both are wrong. A declared hint would hardcode Cancelled into spec data an adopter may have renamed or dropped — the same defect TASK-816 is removing from the targets hint this release, in the same table. A new duplication semantic role would declare a semantic the engine binds nothing to, which widens ADR-775s [ref_kinds] contract; that is the architects call, not a triage call on a low finding, and the Consumer column would have to render it as Navigation, i.e. a role whose consumer is no consumer.
  - So the generated table keeps the loss, which is the price of the table being generated — a hand-written row cannot describe an adopter-declared kind, and that was the point of the rewrite. The guidance is real, though, so it is restored where naming a bundled kind by name is legitimate because the bundled set is the subject: docs/workflow.mds ref-kinds field reference, which TASK-815 is already creating. Stated there as a convention nothing enforces, with Cancelled named as this squads bundled status rather than a universal.
- [2026-08-25T23:04:23Z] Olivia Lead:
  - Decision: the guidance does not go into the spec, and it does not go back into the generated cheatsheet. It is restored in the ref-kinds field reference in the docs — TASK-815 ST5 (Ready, tech-writer). Reasoning in the comment above.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — New hygiene scans carry hand-maintained literal lists unpinned to their sources

<!-- sq:finding:F9:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
**Severity: low. Read, with the pin check driven.**

Both `tests/meta` scans added in this range protect a spec-declared vocabulary with a **hardcoded
copy of that vocabulary**, and neither is pinned to its source:

- `tests/meta/test_no_bundled_ref_kind_literal_outside_the_spec_layer.py:32-44` —
  `_REF_KIND_LITERALS` lists the ten bundled kinds as literals. Nothing asserts it equals
  `bundled_spec().ref_kinds`. A kind added to `_specs/workflow.toml` (the eleventh, whenever it
  comes) gets no literal-scan coverage, silently — and the scan's whole purpose is to stop a bundled
  kind name being consulted as a literal in the engine. `grep "def test_"` over the file confirms no
  such pin exists.
- `tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py:71-81` —
  `_WIRE_ENCODING_PRIMITIVES` lists six names with no assertion that they resolve in
  `squads._models._item` (**driven**: all six do today, so this is latent). A rename makes the guard
  vacuous for that name.

Both are one-line fixes (`assert _REF_KIND_LITERALS == frozenset(bundled_spec().ref_kinds)`;
`assert all(hasattr(item_module, n) for n in _WIRE_ENCODING_PRIMITIVES)`) and both convert "someone
remembered" into "the suite noticed". Filed together with F2 in mind — three of this range's new
guards protect a derived thing with a hand-maintained list, which is a pattern worth naming rather
than three separate coincidences.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-08-25T23:04:24Z] Olivia Lead:
  - Triaged to TASK-819 ST2 and ST3 (Ready, FEAT-790 US2), together with F5 — F9s second bullet and F5s secondary half are the same pin in the same file, so they could not be split without a collision.
  - Verified both: _REF_KIND_LITERALS is a hand-typed frozenset of ten with no test pinning it to bundled_spec().ref_kinds, and _WIRE_ENCODING_PRIMITIVES has no resolution assertion. Taking your framing that this is one pattern rather than three coincidences — F2s derivation is the third instance and is tracked on TASK-818.
  - The ref-kind pin is specified as equality, not superset: a literal the spec no longer declares means the scan is guarding a name that does not exist while the real one goes unguarded.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T22:50:34Z] Paul Reviewer:
  - Recommended verdict: ChangesRequested on F1 alone. Everything else is a message, a docstring or a guard gap — none of it blocks the release. F1 is a data-loss path that opens the moment 0.14.0 is tagged, so it wants a decision before the tag, not after.
  - What I drove and what came back clean, so it is not re-driven: the ref-kind semantic binding (renamed dependency kind keeps sq blocked; retired name refused by name; renamed supersession kind refused while live refs carry it, naming the offending IDs in sq workflow lint); undeclared-kind edges traverse sq graph in both directions with edge_semantic null while --kind filtering still gates; the refrozen 0.5-to-0.7 runner reproduces the pre-structural byte table exactly on all six fixtures; the stale-index-encoding diagnosis discriminates correctly on all three states including the legacy extra.ref_kinds map, with the same wording at the write seam and in sq check.
  - Two things I could not test, both stated in the findings: whether the generator sweep has already destroyed store history in some other checkout (I only proved it can, in a copied tree), and the VS Code edge-label conversion from TASK-810 — that is a TypeScript suite I did not run, and its correctness turns on edge_semantic reaching the client, which I verified only on the Python side of the wire.
  - @tech-lead F1 needs an owner before the 0.14.0 tag. F2/F5/F9 are guard hardening and can ride any later pass. F3/F4 are adopter-facing message defects on a capability shipping this release, so they are worth catching now while the code is warm. Findings left Open — @manager the verdict transition is yours.
- [2026-08-25T23:04:57Z] Olivia Lead:
  - F2 through F9 are triaged and authored. F1 is not mine — the architect is ruling it, and I left it and everything touching the generator sweep alone.
  - TASK-818 (FEAT-791 US5) — F2. The uniformity guard derives its kind set from scan_overrides and gains CLI reachability as a fifth element. Its own task, because it is the guard that passed an unreachable kind rather than a rider on the kind it missed.
  - TASK-819 (FEAT-790 US2) — F5 and F9. The migration guards import-form evasion, plus the two hand-maintained literal lists pinned to their sources. Grouped because F5s secondary half and F9s second bullet are the same one-line pin in the same file.
  - TASK-820 (FEAT-791 US3) — F3, F6 and F7. The roles catalog overrides remaining diagnostics and the un-threaded dev-role preview base. Grouped because all three land in _roles/ and _overrides/_service.py.
  - TASK-821 (FEAT-791 US4) — F4. Scoped at the shared merge engine rather than the roles layer, so it discharges the acceptance clause for every override kind at once.
  - TASK-815 gains ST5 for F8 and a depends-on on TASK-821, because its quoted-refusal fix reproduces the exact message TASK-821 changes.
  - Three notes back on the citations, all recorded on the findings. F4 is pre-existing debt: _unknown_key_violations landed in 2f8b1ab on 2026-08-15, before this range begins, and squads.__version__ has never been in _specmerge.py — this round added the promise, not the defect. F6s "all three call sites have a squad_dir in hand" is not right for _overrides/_service.py:882, which sits inside _shadowed_bundled_role_toml(slug) — that takes none, and one of its two callers has none either, so threading means changing signatures. F7s second citation at :1290-1293 I could not confirm; that range is check_override_issues docstring on the roster fallback and reads accurate, and there is no "split" reference in the file.
  - F8 was the judgement call and it went against the spec: the two homes the spec offers are a hint that would hardcode a status an adopter may have dropped — the defect TASK-816 is removing from targets this same release — and a semantic role the engine binds nothing to, which is an architects call on ADR-775s contract. Full reasoning on the finding.
  - @reviewer nothing here needs re-driving; every citation verified. @manager F1 is still the only thing between this and the tag, and it is with the architect.
- [2026-08-25T23:11:14Z] Olivia Lead:
  - F1 authored: TASK-822 (Ready, urgent, python-dev, FEAT-791 US1) — "Rebuild the content store from ground truth and retire the sweep", five subtasks covering the four workstreams @architect named. All nine findings are now triaged. Details on each finding.
  - One ordering edge found, and it is not the one I expected. TASK-818s guard work shares no written file with TASK-822 — 818 is test_override_kind_uniformity.py and only reads _overrides/_manifest.py, while 822 is the two scripts plus test_override_manifest_and_stamp_freshness.py — so no dependency there, just do not run them concurrently in one tree. The real edge is TASK-816: it regenerates the manifest, which is safe while 0.14.0 is untagged and becomes the exact destructive case if the tag lands first. Recorded on both, as a tag-day constraint rather than a blocking ref.
<!-- sq:discussion:end -->
