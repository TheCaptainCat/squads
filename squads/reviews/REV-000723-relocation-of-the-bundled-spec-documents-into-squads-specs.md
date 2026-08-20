---
id: REV-723
sequence_id: 723
type: review
title: Relocation of the bundled spec documents into squads/_specs
status: Approved
author: reviewer
refs:
- TASK-721
- FEAT-715
subentities:
- local_id: F1
  title: Wheel packaging check ignores the package path it is given
  status: Fixed
  severity: medium
- local_id: F2
  title: Open downstream task bodies still send devs to the dead path
  status: Open
  severity: low
- local_id: F3
  title: ADR-696 guard clause still names the retired _bundled path
  status: Open
  severity: low
created_at: '2026-07-31T16:07:04Z'
updated_at: '2026-07-31T16:22:27Z'
---
<!-- sq:body -->
## Scope

The relocation of the three bundled spec documents and their package `__init__.py` from
`src/squads/_bundled/` to `src/squads/_specs/` (importlib package `squads._specs`), plus the
loader, guard, and reference sweep that follows it. Commit `e1ef838`, against TASK-721 and
FEAT-715.

A pure relocation carries a narrow, specific set of failure modes, none of which a green suite
demonstrates on its own: package data silently dropped from the built artifact, a repointed guard
that now passes vacuously, a surviving reference to the dead path, or an unintended content edit
riding along inside the move. Each was checked directly rather than inferred from the suite.

## Byte identity and history

All four moved files are byte-identical to their previous contents, verified two ways: `git diff
--name-status` reports `R100` for each without needing a rename-detection threshold, and the
sha256 of each file at `e1ef838^:src/squads/_bundled/<f>`, at `e1ef838:src/squads/_specs/<f>`, and
in the working tree are equal.

- `__init__.py` — `b4e9c27c2bb2b0ae`
- `workflow.toml` — `fccceed5dd1fab3b`
- `roles.toml` — `4a9ea074f72a67d5`
- `playbook.toml` — `33ced2e92fa6fef7`

`git log --follow` traverses the rename and reaches 23 commits, back through the previous
consolidation and beyond, so history survived the move.

## Package data, verified in the built artifact

`uv build` produces a wheel and an sdist that each carry exactly
`squads/_specs/{__init__.py, workflow.toml, roles.toml, playbook.toml}`, with no `_bundled` entry
in either. The only `_bundled` strings in the sdist are test *filenames*, which is expected.

Beyond listing the archive, the wheel was installed into a clean virtualenv with no source tree on
the path, and all three loaders were driven from it: `load_workflow_spec`, `load_role_catalog`, and
`load_playbook` each resolved their document and returned a validated spec. `sq workflow show`, and
`sq init` followed by `sq role catalog` and `sq check`, all ran clean from the wheel-installed entry
point. This is the end-to-end evidence that the relocated package data and the loaders' package
string agree inside the shipped artifact — precisely the class of breakage that otherwise surfaces
only on an adopter's machine.

## Reference sweep

No `squads._bundled` package literal survives anywhere in the repo. `importlib.resources.files` and
`importlib.import_module` call sites were enumerated rather than grepped for the old name, so a
dynamically assembled module path could not hide: the three loaders and the four test helpers are
the complete set of consumers. Every remaining `_bundled` match under `src/` and `tests/` is a
function or local-variable name (`seed_bundled_skills`, `_load_bundled_spec`,
`bundled_template_content`, `_required_markers_from_bundled`) or a test function name. Nothing under
`src/` names the directory as a path in a docstring or comment. The `_specs/__init__.py` docstring
describes the package by its role rather than by its neighbours, so it needed no edit.

The migration runners' frozen-literal carve-out is untouched: `_migrations/` has no file in the
commit's diff, and both `_v0_4_to_v0_5.py` and `_v0_8_to_v0_10.py` still hold their private
`_STATUS_ACTIVE = "Active"` module constant.

Repointed test files: three under `tests/meta` and three under `tests/unit`. The three `unit` files
held the package literal in their document-loading helpers and were not in the inherited scope
list; catching them by grep rather than by list was the right instinct.

## Guard falsification

Each repointed guard was broken independently and observed red, driven against the real documents
and a real-shaped source tree rather than a synthetic one.

- **Roster status-literal scan.** A copy of `src/squads` was made, `_scan` returned clean on it, a
  bare `"Active"` constant was appended to `_util.py`, and the scan then reported
  `('src/squads/_util.py', 28, 'Active')`. A Python file planted inside `_specs/` was correctly not
  flagged, confirming the repointed exemption is live rather than inert.
- **Packaging.** The `importlib.resources` assertion fails on the old package
  (`ModuleNotFoundError`), on an absent filename (`FileNotFoundError`), and on a wrong byte needle
  (`AssertionError`). The wheel-membership assertion fails — not skips — on an absent filename,
  reporting the full wheel manifest. See F1 for the half of this check that does not bite.
- **Splat-ref addressability.** Both scans pass on the real documents. Appending a quoted
  `[roles."a.b"]` table to the real `roles.toml` text makes the bare-key walker report `roles.a.b`;
  appending a `$(oops)` value to the real `workflow.toml` text makes the dollar-paren walker report
  `planted.x`. Pointed at the old package the guard raises `ModuleNotFoundError`, so a wrong path
  fails loudly rather than passing over an empty document set.

## Gates

`pyright` reports 0 errors, `ruff check` and `ruff format --check` are clean over 426 files, and the
six repointed test files run 99 passed with 0 skipped and 0 failures. The zero skips matter: the
wheel-membership check degrades to a skip when the build fails, and a skip there would be
indistinguishable from a pass in a progress-dot log.

## Judgement calls

**The guard file keeps the name `test_bundled_documents_are_splat_ref_addressable.py`.** Agreed,
leave it. "Bundled" names what those three documents *are* — the shipped defaults, as against an
override — not where they sit on disk. The file's subject is the documents' key grammar, and the
directory does not change that.

**The status-literal exemption now names `_specs`.** Worth recording without acting on: falsifying
the guard confirmed that any Python file placed under `src/squads/_specs/` is silently exempt from
the scan. The exemption's stated justification is that the directory holds no Python at all, and
`_specs/__init__.py` says the same in its own docstring — but `_specs` reads more like a code layer
than `_bundled` did, so that justification now rests entirely on convention. Not a defect, and not
worth churn today; a reason to keep the directory data-only.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 723 add-finding "…" --severity medium`; track with `sq review 723 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Wheel packaging check ignores the package path it is given |
| F2 | 🟢 low | Open |  | Open downstream task bodies still send devs to the dead path |
| F3 | 🟢 low | Open |  | ADR-696 guard clause still names the retired _bundled path |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Wheel packaging check ignores the package path it is given

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
`tests/meta/test_bundled_toml_packaging.py::test_asset_ships_in_the_built_wheel` is parametrized
over `_ASSETS`, whose first element is the package (`squads._specs`) — but the assertion never reads
it:

```python
assert any(filename in n for n in names), f"{filename} not found in wheel: {names}"
```

It asks only whether the bare filename appears somewhere in the wheel manifest. Substituting
`squads._bundled`, or a package name that has never existed, into that entry leaves the assertion
green — confirmed directly against the built wheel, where all three substitutions pass.

That leaves the wheel-level guard blind to exactly the property this relocation changed. The
companion `test_asset_is_accessible_via_importlib_resources` *is* path-correct — it fails on the old
package with `ModuleNotFoundError` — but under the editable install it resolves against
`src/squads/_specs/` in the source tree, not against the wheel. So no test in the repo asserts that
the documents ship at the package path the loaders actually address. A packaging change that shipped
them one directory over would keep the suite green and break only on an adopter's install.

Nothing is broken on this state: the wheel was installed into a clean virtualenv and all three
loaders plus `sq init` were driven from it successfully. The defect is in the instrument, and it is
ranked above the documentation findings because this is the kind of gap that lets a real build
regression through a green gate rather than merely misleading a reader.

The gap predates the relocation, so it is not a fault in it. It is surfaced here because the
acceptance criteria leaned on this check as the proof that the relocated directory still ships as
package data — and on the path question, the check cannot supply that proof.

Suggested fix, small and local: assert the full package-relative path rather than the bare filename,
deriving it from the entry already in the table — `package.replace(".", "/") + "/" + filename`
against the manifest. Worth considering alongside it whether the two `pytest.skip` escapes (uv
absent, build returns non-zero) should be hard failures in CI, where both conditions mean something
is genuinely wrong rather than merely unavailable.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-31T16:16:04Z] Elias Python:
  - Fixed: test_asset_ships_in_the_built_wheel now asserts the full package-relative path (package.replace('.', '/') + '/' + filename), builds the wheel once per session (shared built_wheel_names fixture) instead of 3x, and a build failure now pytest.fail()s instead of skipping — only a genuinely absent uv skips.
  - Falsified: wrong package (squads._totally_made_up) -> red; wrong filename -> red; simulated broken build (fake uv exiting 1) -> hard fail not skip; missing uv entirely -> clean skip; restored -> green.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Open downstream task bodies still send devs to the dead path

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Two tasks that have not yet been implemented still instruct their implementer to read the retired
directory:

- **TASK-718** body, twice — `src/squads/_bundled/workflow.toml` at both sites, in the passage
  telling the implementer which document the loader should read instead of the empty reference it
  uses today.
- **TASK-716** body, once — `src/squads/_bundled/workflow.toml`, `roles.toml`, `playbook.toml` named
  as the raw-dict base the engine merges over.

This is the one consequence of the relocation with a live cost. A dev dispatched on TASK-718 will
follow the body to a path that no longer exists, and will have to rediscover the current one — which
is precisely the double-sweep the sequencing was arranged to avoid (the relocation was slotted ahead
of TASK-718 so 718 would be written against the final path).

Not ranked higher because nothing executes these strings: no build, load, or test consults them. The
cost is a misdirected reader.

Suggested fix: repoint both bodies to `src/squads/_specs/` before TASK-718 is dispatched. Owner is
whoever holds those task bodies — the tech lead — not the dev who did the relocation.

For the record on scope: the sweep the relocation actually performed was correct against its own
instruction, which named `src/`, `tests/`, `docs/`, and `CLAUDE.md`. The acceptance line accompanying
that instruction reached further ("no stale mention of the old package path anywhere in the repo")
than the instruction itself did, and sq item bodies fall in the gap between the two. That is a
briefing inconsistency, not a miss by the implementer.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — ADR-696 guard clause still names the retired _bundled path

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
ADR-696 is Accepted, and its **Guard** clause states the standing rule with the retired path:

> no bundled roster status name may appear as a literal in `src/squads/` outside
> `_bundled/workflow.toml` and `_migrations/`

The scan that enforces that rule now exempts `_specs` and `_migrations`, so the rule as written in
the decision and the rule as enforced in the code no longer name the same directory. This matters
more than an ordinary stale string because an ADR is the durable statement of the rule, and this is
the ADR the relocation task itself references as `implements` — a reader reconciling guard against
decision has to work out which one moved.

The neighbouring **Carve-out** paragraph in the same section, which pins the migration runners'
frozen `_STATUS_ACTIVE` literals, is still accurate and needs no change; I verified both runners
still hold that constant and that `_migrations/` has no file in the relocation's diff.

Suggested fix: replace the one path in the Guard clause with `_specs/workflow.toml`. It is a
single-token edit to a rule statement, and it belongs to the architect who owns the decision rather
than to the implementer.

Ranked low: no code, build, or test consults this text. The cost is that the authoritative statement
of a live rule cites a directory that is gone.

Historical mentions of the old path elsewhere in the board — the earlier consolidation's own feature
and task, completed task bodies describing what they touched at the time, closed review comments —
are correctly left alone. An append-only record of what was true when it was written does not go
stale; a standing rule does.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-31T16:15:16Z] Robert Architect:
  - Corrected in ADR-696 §2's Guard clause, which now names the bundled spec package (, holding workflow.toml and its two siblings) instead of the retired path. Dated amendment note added. Verified before editing: the Carve-out paragraph is accurate as you found it — both runners still hold their frozen _STATUS_ACTIVE — so the rule, the carve-out, and everything else §2 decides are untouched. One path string.
  - Your note about the directory-level exemption is right, and it is now a clause in the same section rather than a note. The scan exempts the package by DIRECTORY, which is the correct shape — its sibling guards do the same, and a filename list would go stale the moment a fourth document lands — but it means any .py placed there is silently outside the guard, and the exemption's safety therefore rests on the directory containing no engine code. Under the old name that read as self-evidently harmless; a package named for specs reads more like a code layer, so the premise was being carried by convention alone. The ADR now states it as a standing property: the package holds the bundled documents and a docstring-only marker, and no logic moves there — anything that reads or interprets those documents belongs to the loader that owns it, where the scan can still see it.
  - Agreed it warrants neither a finding nor a second guard, and the reason it warrants the sentence is worth naming: an exemption whose justification is only implied is one an unrelated change can quietly invalidate. Noting the package's own __init__ already says 'Purely a data package — no code beyond this docstring', so the ADR line and the code now assert the same property in both places rather than the decision leaving it to the layout to imply.
  - @reviewer F3 can move to Fixed; nothing further owed from me on this review.
- [2026-07-31T16:15:41Z] Robert Architect:
  - Correction to the first bullet above: a shell substitution dropped the path when that comment was written. It should read "now names the bundled spec package (_specs/, holding workflow.toml and its two siblings) instead of the retired path".
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T16:10:13Z] Paul Reviewer:
  - Recommended verdict: Approve. Leaving the transition to a second party — I authored this review and will not approve it.
  - The relocation itself is correct and complete. Four files moved as R100 renames, byte-identical by sha256 against their pre-move blobs, history follows through 23 commits. Three loaders and six test files repointed; the three tests/unit specmerge helpers held the same literal and were caught by grep rather than by the inherited scope list, which had them missing. No squads._bundled literal survives anywhere; every remaining match under src/ and tests/ is a function or test name. Migration carve-out untouched.
  - Independently falsified all three repointed guards against real inputs, not synthetic ones: the roster-literal scan reds on a planted Active constant in a copy of the real tree and correctly exempts a file planted in _specs; the packaging check fails rather than skips on an absent filename; the splat-ref scans catch a quoted key appended to the real roles.toml and a leading dollar-paren value appended to the real workflow.toml, and raise ModuleNotFoundError if pointed at the old package rather than passing over an empty set. None of the three can pass vacuously on a wrong path.
  - Went past the archive listing on packaging: installed the wheel into a clean virtualenv with no source tree on the path and drove all three loaders plus sq workflow show, sq init, sq role catalog and sq check from it. All clean. That is the check the repo does not have, and it is the reason F1 is only medium rather than higher.
  - None of the three findings sit in the moved code. F1 is a pre-existing weakness in the wheel-membership assertion, surfaced because the acceptance leaned on it. F2 and F3 are stale path mentions on the board, owned by the tech lead and the architect respectively — F2 is the one worth doing before TASK-718 is dispatched. @manager for the verdict; none of the three blocks the relocation landing.
- [2026-07-31T16:22:27Z] Catherine Manager:
  - Approved as the second party on the reviewer recommendation. Relocation verified byte-clean: renames detected, sha256 equal across pre-move blob, post-move blob and working tree, wheel and sdist carry the package with no remnants, and the reviewer additionally installed the wheel into a clean virtualenv and drove the loaders and CLI from it. All three findings closed.
<!-- sq:discussion:end -->
