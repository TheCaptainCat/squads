---
id: TASK-801
sequence_id: 801
type: task
title: Uniform unstamped-shadowing severity and the uniformity guard
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: medium
refs:
- ADR-777:implements
- TASK-799:depends-on
- TASK-800:depends-on
description: Make an unstamped shadowing override an error for every kind, and guard
  the four-part uniformity structurally
subentities:
- local_id: ST1
  title: Raise unstamped shadowing template and role overrides to error
  status: Done
  story: US5
- local_id: ST2
  title: tests/meta uniformity guard over the override registry
  status: Done
  story: US5
- local_id: ST3
  title: Correct OverrideEntry.kind docstring
  status: Done
  story: US5
- local_id: ST4
  title: Narrow the stale playbook-override amendment note
  status: Todo
  assignee: architect
  story: US5
- local_id: ST5
  title: Restore the manifest-freshness content assertion
  status: Done
  story: US5
created_at: '2026-08-25T14:40:36Z'
updated_at: '2026-08-25T23:39:48Z'
---
<!-- sq:body -->
## Scope

ADR-777 §6 — FEAT-791 US5. One severity for a missing stamp on a shadowing override, for every
kind, plus the `tests/meta` guard that makes the uniformity itself structural instead of
assumed. Also the freshness assertion the manifest widening deleted, and the two stale
documented facts ADR-777 names.

Sequenced after TASK-799 and TASK-800 because the guard asserts a property of the whole
registry: every registered kind needs its manifest entry (TASK-799) and the roles-catalog kind
needs to exist (TASK-800) before the guard can pass.

## One severity (§6)

- **A shadowing override with no provenance stamp is an `error`-level `sq check` finding for
  every override kind.** Workflow and playbook already are; **templates and per-slug roles move
  from warn to error** (`_overrides/_service.py:938-960`, `:966-976`).
- **The roles catalog document has no stamp-obligation finding at all — this task creates it.**
  `.overrides/roles.toml` is a fifth kind and a different thing from the per-slug
  `.overrides/roles/<slug>.toml` above; both are called "roles" and only one of them exists in
  `sq check` today. `check_override_issues` calls `_check_workflow_override_issues` and
  `_check_playbook_override_issues` and then stops, with a comment at
  `_overrides/_service.py:1232-1239` recording the deferral to this task by name. There is no
  `_check_roles_catalog_override_issues` to raise the severity *of* — it is written here, at
  error level, shipping with the shadowing-vs-add-only distinction from day one rather than
  arriving at warn and being corrected. Driven: a squad carrying an unstamped
  `.overrides/roles.toml` reports nothing from `sq check` today.
- **An add-only override with no stamp still reports nothing**, unchanged.
- **A stamp older than the running version, with the bundled counterpart changed, stays a
  `warn`.**

A whole-file template override always shadows, so this turns today's unstamped-template *warn*
into an *error*. That is the intended direction: the divergent severity is how template
overrides came to be overlooked in the first place — they were the one shadowing kind whose
missing provenance reported at a level a squad could carry indefinitely.

### This changes `sq check`'s exit code for existing squads. Do not "fix" it back.

An existing squad carrying an unstamped template or role override goes from **clean or warn to
exit 3** on its first run after upgrading. **This is a deliberate tightening ruled by the
operator on ADR-777, not a regression.** Anyone who meets it in a test fixture or a dogfood run
and is tempted to soften it back to a warning is undoing the decision.

Two things soften the first encounter without weakening the finding, and both must survive:

- **The message already names the file and the fix** and must keep that shape at error level:
  the display path, then `sq override scaffold --force` to re-scaffold with a stamp, or
  `sq override update` after verifying the content (`_overrides/_service.py:938-948`). An error
  that names a file and one command is not the failure mode this clause risks.
- **One command clears a whole squad.** `sq override update` with no name re-stamps every
  structurally-valid override at once (`_overrides/_service.py:855`), which ADR-85 §3 already
  contracted as the bulk acknowledge after a review pass. The remediation is bounded at one
  command regardless of how many overrides a squad carries.

**No upgrade-keyed grace period is introduced.** A severity that depends on when a squad last
upgraded is a second rulebook, and ADR-777 §1's whole point is that there is one.

## The uniformity guard

In the shape of the routing guard that already exists
(`tests/meta/test_every_override_document_merges_through_the_shared_engine.py`): a `tests/meta`
scan asserting that **every override kind in the registry has all four of** — a manifest entry
for its bundled counterpart, a state classifier, a stamp-obligation finding, and both diff
deltas wired. A fifth kind must not be able to ship with three of the four.

The routing axis is uniform today because it is the axis with a guard; this extends the same
reasoning to the axis that is not. It must fail loudly, naming the kind and which of the four
is missing — not merely count.

## The freshness assertion the widening deleted

The manifest widening removed the one assertion that made
`tests/meta/test_override_manifest_and_stamp_freshness.py` a *freshness* guard. Before, it
carried:

```
mismatched = {name for name, actual in installed.items() if manifest_entry.get(name) != actual}
assert not mismatched, f"manifest hashes are stale for: {sorted(mismatched)}"
```

After (`:62-83`, verified) only `missing` and `extra` survive — presence, never content. The
module's own docstring still promises the opposite: "an artifact edit without re-running the
generator script fails loudly, not silently".

Driven in the review, against a faithful simulation of the real "edited a template, forgot to
regenerate" state — the index still naming the previous release's hash for that key, and no
blob in the store for the new content: **all twelve tests in the module pass**. The control,
the same probe with the entry deleted outright, is still caught, so the probe is sound.

**Mitigated, not covered.** `scripts/gen_template_manifest.py --check` keeps its own `stale`
list (`:130-132`) and CI runs it (`.github/workflows/test.yml:36-37`), so a stale manifest
cannot reach a release. What is gone is the local net: a dev or agent whose gate is
`uv run --all-extras pytest` gets no signal, and the guard now asserts less than its name and
docstring claim.

The two are not interchangeable in either direction, which is why restoring this is not
redundant with the script: the meta guards cover every version the index names, while `--check`
verifies only the running version's own entry.

**Why here.** This task owns the guard that makes the override contract's uniformity
structural rather than assumed, and this is the same failure shape one axis over — a guard whose
docstring asserts more than its body checks. Restoring it belongs with the work that adds the
sibling guard, not filed against the widening that is already landed and reviewed.

Restore the content assertion over the whole installed set, not the four artifacts the two
surviving content checks happen to reach (`items/task.md.j2` via `template_changed_since`, and
the three spec TOMLs via `artifact_changed_since`).

## The stale documented facts

- **`OverrideEntry.kind`'s docstring** says `"template" or "role"` while four values ship
  (`_overrides/_service.py:75`), and five ship after TASK-800. Correct it.
- **ADR-226's amendment note** records "the playbook is not yet an override kind … named as the
  planned fourth". That reading was true when written and is not now — the shipped
  `.overrides/playbook.toml` overtook it. **Narrowed in place at its own end by the architect**,
  dated and naming ADR-777, not deleted and not rewritten in the body.

## Traps

- **`sq check` fixtures across the suite may carry unstamped overrides** written when warn was
  the level. Expect a broad fixture sweep, and treat each failing fixture as "does this fixture
  intend a shadowing override without a stamp?" — stamp it if yes, not lower the severity.
- **No bundled template is touched**, so no manifest regeneration and `scripts/bump_version.py`
  must not be run.

## Acceptance

- An unstamped shadowing override is an `sq check` error (exit 3) for **every** kind:
  template, per-slug role, workflow, playbook and the roles catalog document.
- The roles catalog document's finding exists at all — it distinguishes a shadowing override
  from an add-only one, and an unstamped shadowing `.overrides/roles.toml` exits 3 where it
  reports nothing today.
- An unstamped **add-only** override of any kind still reports nothing.
- A stamp older than the running version with a changed bundled counterpart is still a warn.
- The error message names the override's path and both remediation commands, at error level.
- `sq override update` with no name re-stamps every structurally-valid override in a squad and
  clears the finding.
- The uniformity guard fails, naming the kind and the missing element, when a registered kind
  lacks any one of: a manifest entry, a state classifier, a stamp-obligation finding, Δ-mine,
  Δ-upgrade. Verified by removing each of the five in turn in the test.
- The manifest-freshness module asserts recorded-vs-actual hashes across the whole installed
  artifact set, and fails when any one entry's hash is stale — proven by a probe that leaves
  presence intact and only the content wrong.
- The module's docstring promise and what its tests assert cannot disagree.
- `OverrideEntry.kind`'s docstring names every shipping value.
- ADR-226's amendment note carries a dated narrowing naming ADR-777, authored by the architect.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 801 add-subtask "<title>"`; track with `sq task 801 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Raise unstamped shadowing template and role overrides to error

<!-- sq:subtask:ST1:body -->
A shadowing override with no provenance stamp becomes an **error**-level `sq check` finding for
every override kind. Workflow and playbook already are; templates and per-slug roles move from
warn to error (`_overrides/_service.py:938-960`, `:966-976`).

**The roles catalog document is not a severity change — its finding does not exist yet, and this
subtask writes it.** Two different kinds are both called "roles": the per-slug
`.overrides/roles/<slug>.toml` above, which has a finding to re-level, and the whole-document
`.overrides/roles.toml` catalog override, which has none. `check_override_issues` calls the
workflow and playbook checks and then stops; the comment at `_overrides/_service.py:1232-1239`
records the deferral to this task by name and says why — so the document ships with the
shadowing-unstamped=error rule from day one rather than arriving at warn and being corrected
immediately after. Driven: a squad carrying an unstamped `.overrides/roles.toml` reports nothing
from `sq check` today.

Write it in the shape the other two already share (`_check_workflow_override_issues` /
`_check_playbook_override_issues`): read the stamp, ask a stamp-obligation function for a
`(level, message)`, and return one issue. The shadowing-vs-add-only distinction it needs already
has a mechanism to reuse — the same raw key-set intersection against the bundled document the
workflow kind's gating uses — rather than a new rule invented for this kind.

Unchanged: an add-only override with no stamp reports nothing; a stamp older than the running
version with the bundled counterpart changed stays a warn.

A whole-file template override always shadows, so this turns today's unstamped-template warn
into an error. That is the intended direction — the divergent severity is how template overrides
came to be overlooked in the first place: they were the one shadowing kind whose missing
provenance reported at a level a squad could carry indefinitely.

**This changes `sq check`'s exit code for an existing squad, from clean or warn to 3, on the
first run after upgrading. It is a deliberate tightening ruled by the operator. Do not soften it
back to a warning.** Anyone who meets it in a fixture and lowers the severity is undoing the
decision; stamp the fixture instead, after deciding whether it intends a shadowing override
without a stamp.

Two things soften the first encounter and both must survive:

- The message keeps its existing shape at error level — the display path, then `sq override
  scaffold --force` to re-scaffold with a stamp, or `sq override update` after verifying the
  content (`_overrides/_service.py:938-948`).
- `sq override update` with no name re-stamps every structurally-valid override at once
  (`:855`), so remediation is bounded at one command regardless of how many overrides a squad
  carries.

**No upgrade-keyed grace period.** A severity that depends on when a squad last upgraded is a
second rulebook, and the whole point of the uniformity decision is that there is one.

Done when an unstamped shadowing override of every kind exits 3 — the roles catalog document
included, where nothing is reported today — an add-only unstamped override of every kind reports
nothing, and the message still names the file and both commands.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — tests/meta uniformity guard over the override registry

<!-- sq:subtask:ST2:body -->
Add a `tests/meta` scan in the shape of the routing guard that already exists
(`tests/meta/test_every_override_document_merges_through_the_shared_engine.py`), asserting that
**every override kind in the registry has all four of**: a manifest entry for its bundled
counterpart, a state classifier, a stamp-obligation finding, and both diff deltas wired.

The routing axis is uniform today because it is the axis with a guard; this extends the same
reasoning to the axis that is not, so a fifth kind cannot ship with three of the four.

It must fail **naming the kind and which element is missing**, not merely count — a guard that
reports "expected 5, got 4" sends the reader hunting.

Done when removing each of the four in turn, for each registered kind, fails the guard with a
message naming both the kind and the missing element.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Correct OverrideEntry.kind docstring

<!-- sq:subtask:ST3:body -->
`OverrideEntry.kind`'s docstring documents the value as `"template" or "role"`
(`_overrides/_service.py:75`) while four values ship today and five ship once the roles catalog
document lands.

Correct it to name every shipping value, and phrase it so it does not go stale the same way —
the registry is the authority on which kinds exist, and the docstring should say so rather than
re-listing a set that will move again.

Done when the docstring names every value the registry carries and the uniformity guard's kind
list and the docstring cannot disagree.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Narrow the stale playbook-override amendment note

<!-- sq:subtask:ST4:body -->
The playbook decision's amendment note records "the playbook is not yet an override kind … named
as the planned fourth". That reading was true when written and is not now — the shipped
`.overrides/playbook.toml` overtook it.

Narrow it in place at its own end, dated and naming the uniformity decision. **Not deleted, and
not rewritten in the body** — the original reading stays legible as what was true at the time.

**This is an amendment to an accepted decision record, so the architect authors it**, not the
developer.

Done when the note carries a dated narrowing at its own end naming the superseding decision,
with the original text intact above it.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Restore the manifest-freshness content assertion

<!-- sq:subtask:ST5:body -->
Restore the assertion that made `tests/meta/test_override_manifest_and_stamp_freshness.py` a
freshness guard.

The manifest widening deleted it. Before, the module carried:

```
mismatched = {name for name, actual in installed.items() if manifest_entry.get(name) != actual}
assert not mismatched, f"manifest hashes are stale for: {sorted(mismatched)}"
```

After (`:62-83`) only `missing` and `extra` survive — presence, never content — while the
module docstring still promises "an artifact edit without re-running the generator script fails
loudly, not silently".

Driven against a faithful "edited a template, forgot to regenerate" state (index still naming
the previous release's hash for that key, no blob in the store for the new content): all twelve
tests in the module pass. The control — the same probe with the entry deleted outright — is
still caught.

Restore the content assertion over the **whole installed set**, not the four artifacts the two
surviving content checks happen to reach (`items/task.md.j2` via `template_changed_since`, and
the three spec TOMLs via `artifact_changed_since`).

`scripts/gen_template_manifest.py --check` keeps its own `stale` list and CI runs it, so this is
not the only net — but it verifies only the running version's own entry, while these guards
cover every version the index names. Restoring this is not redundant with the script.

Prove it the way the review did: a probe that leaves presence intact and corrupts only content
must fail the module, and the entry-deleted control must keep failing on its existing message.

Done when a stale recorded hash for any installed artifact fails this module, the probe above is
part of the suite, and the module's docstring promise matches what its tests assert.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T18:01:01Z] Olivia Lead:
  - Folded REV-808 F2 in as ST5. Verified the citation myself: tests/meta/test_override_manifest_and_stamp_freshness.py:62-83 now computes only missing and extra, while the module docstring at :4 still promises that an artifact edit without re-running the generator fails loudly. The reviewer drove it - a faithful edited-but-never-regenerated state passes all twelve tests in the module, and the entry-deleted control is still caught, so the probe is sound.
  - Why here rather than filed against the widening that removed it: this task already owns the guard that makes the override contract uniformity structural instead of assumed, and F2 is the same failure shape one axis over - a guard whose docstring asserts more than its body checks. The widening is landed and reviewed; reopening it to restore an assertion would desync that review.
  - Recorded as mitigated, not covered: gen_template_manifest.py --check keeps its own stale list and CI runs it, so a stale manifest cannot reach a release. What is gone is the local net, and the two are not interchangeable - the meta guards cover every version the index names while --check only verifies the running version entry. Severity of the task is unchanged.
- [2026-08-25T21:06:47Z] Olivia Lead:
  - Extended for the roles catalog document rather than authoring something new, per the coordinator. Checked first whether this task already covered it: the acceptance did name the roles catalog among the kinds, and ST2 uniformity guard would fail without a stamp-obligation finding for it - but ST1 prose framed the whole job as RAISING severity ("templates and roles move from warn to error"), and the roles there means the per-slug .overrides/roles/<slug>.toml kind. The catalog document has no finding to re-level.
  - Verified in code and by drive: check_override_issues calls the workflow and playbook checks and stops, with a comment at _overrides/_service.py:1232-1239 deferring to this task by name; a squad carrying an unstamped .overrides/roles.toml reports nothing from sq check today. So ST1 and the body now say plainly that this task WRITES that finding, at error level, with the shadowing-vs-add-only distinction from day one - and both places now distinguish the two kinds that are both called roles.
  - One thing I did NOT fold in, flagged rather than decided: the uniformity guard four elements (manifest entry, state classifier, stamp-obligation finding, both diff deltas) do not include CLI reachability, which is exactly how the roles kind reached InReview with no way for a human to invoke it. TASK-814 covers the wiring; whether the guard should gain a fifth element so the next kind cannot repeat it is a scope question for this task, not something I widened on my own. @architect
- [2026-08-25T21:26:39Z] Elias Python:
  - ST1: unstamped-shadowing is error for every kind (template/role/workflow/playbook/roles). Wired the roles-catalog stamp-obligation finding entirely (TASK-800 left it) via new _roles_catalog_override_shadows_bundled (key intersection over roles/bundles/dev). Role shadow-check is roster-aware (role_base_from_item, mirroring _check_role_override_resolves) - a naive slug-shape check misfired on an activated non-dev role whose slug happens to end in -dev.
  - Exit-code change driven end to end: unstamped shadowing items/task.md.j2 -> sq check exit 3, names file + both remediation commands -> sq override update (bulk) clears -> exit 0. Same for an unstamped roles.toml catalog override.
  - ST2: tests/meta/test_override_kind_uniformity.py - fixture-driven, real-dispatcher checks (scan_overrides/check_override_issues/diff_override) for all 5 kinds x 5 parts, plus parametrized removal (sabotage) tests proving detection. Verified against the real pre-fix bug: reverting the roles wiring makes it fail naming {'roles': ['stamp-obligation finding (shadowing must error)']}. Also pins the registry's kind set against OverrideEntry.kind's docstring.
  - ST5/F2: restored the mismatched-hash assertion in test_override_manifest_and_stamp_freshness.py over the whole installed set, plus a driven proof test (fakes _load_manifest to name a stale hash) confirming it fails, with the entry-deleted control still caught separately.
  - ST3 already done by TASK-800's own commit (docstring names all 5 kinds) - verified, not re-touched. ST4 (ADR-226 amendment) is architect's, left untouched.
  - Gates clean: pyright/ruff check/ruff format --all-extras, sq check. Targeted tests only, ~409 across touched+adjacent files, all green.
  - Left undone, flagged for whoever picks it up: _cli/_override.py has no 'roles' positional match for scaffold/diff/update (also flagged by TASK-800); ADR-226 amendment narrowing (ST4).
- [2026-08-25T21:33:56Z] Elias Python:
  - Fixed: the five ADR-777 refs in src/squads/_overrides/_service.py comments/docstrings (lines 1135, 1232, 1308, 1336, 1366) rewritten to cite the rule by content - 'the uniform severity contract' / 'shadowing-vs-add-only' - not the decision id. Also caught and fixed the same pattern in my own test docstrings (missed by my targeted run): tests/meta/test_override_kind_uniformity.py, tests/meta/test_override_manifest_and_stamp_freshness.py, tests/integration/test_override_scaffold_scan_diff_update_and_check.py, tests/integration/test_roles_catalog_override_lifecycle.py, tests/integration/test_new_slug_validation_narrows_to_the_undecidable_dev_shape.py - ADR-777, section-symbol refs, ST3, REV-808/F2 all reworded to describe the mechanism instead.
  - Ran tests/meta in full this time (225 passed) - the only remaining red is src/squads/_itemfile.py, src/squads/_services/_maintenance.py and tests/service/test_stale_index_encoding_reported_as_such.py, none of which are mine (TASK-811's territory, confirmed untouched by me).
  - Gates re-verified clean after the rewrite: pyright, ruff check, ruff format --all-extras, sq check. Targeted: 124 tests across the five files I edited, all green.
  - Noted for next time: full tests/meta run before handoff whenever src/ is touched, not just the tests I added.
<!-- sq:discussion:end -->
