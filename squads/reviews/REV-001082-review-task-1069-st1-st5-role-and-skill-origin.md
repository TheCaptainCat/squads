---
id: REV-1082
sequence_id: 1082
type: review
title: 'Review TASK-1069 ST1-ST5: role and skill origin'
status: Requested
author: reviewer
refs:
- TASK-1069
subentities:
- local_id: F1
  title: Role catalog lists per-slug declared roles only when they are developers
  status: Fixed
  severity: medium
- local_id: F2
  title: Role catalog keeps a row for an archived developer that sq dev list drops
  status: Open
  severity: low
- local_id: F3
  title: New test comments name release versions
  status: Fixed
  severity: low
created_at: '2026-10-16T21:54:03Z'
updated_at: '2026-10-16T21:57:07Z'
---
<!-- sq:body -->
## Scope

The uncommitted TASK-1069 checkpoint, ST1 to ST5, against 0eaadbc5: the origin rule, the pinned `origin` attribute and its check, creation stamps, the surfaces, and the origin contribution to the 0.15 to 0.16 step. ST6 (the refusal) is not built and is out of scope.

## What was driven

Probes ran in a scratch squad with the dev build, and on the same squad with a HEAD build.

- Origin by shape: bundled role; bundled role with a per-slug override (`qa`); a role declared by the catalog; templated developer; declared developer; project role; bundled skills (`squads`, `greeting`, `sq-memory`, `sq-<type>`); a project-type `sq-incident`, then its type dropped; `sq skill add`; `sq import` of a role and a skill. The stored value matched the rule on every shape, and the dropped-type skill kept `system`.
- Creation paths: init, sync seeding after a type is added, sync re-seeding a purged or deleted skill, role activate, dev add, skill add, import create. All of them stamp. `--set origin` and an import `fields` update are refused.
- `sq check` reports a missing value, a list and `System`. Deleting the index and running `sq repair` rebuilds every value verbatim, invalid ones included. `sq sync` is a fixed point and does not backfill.
- JSON compared against HEAD on the same squad. `role list`, `role show` (activated, unactivated bundled, declared, developer), `list -t role|skill` and `skill show` are identical except for the added `origin` and the removed `system`. In `role catalog`, `bundled` became `system`, plus two rows for developers.
- Migration on a copy of the real squad (dev build, `-C`): 10 roles system, 12 skills system, 2 skills project (`releasing-squads`, `launch-dev-host`). `sync` succeeded and `check` was clean. CRLF role and skill files keep CRLF, origin line included. A planning failure writes nothing. A stored value, valid or invalid, is never touched. On the developer fixture: templated developers are system; `legacy-dev`, `old-dev` and `builder` are project.
- ruff and format are clean. The five new test modules plus `tests/meta` pass (524). pyright was not run.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1082 add-finding "…" --severity medium`; track with `sq review 1082 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Role catalog lists per-slug declared roles only when they are developers

<!-- sq:finding:F1:body -->
`sq role catalog` now adds a row for an activated role the catalog document does not declare only when that role is a developer. A project role declared through a per-slug file (`.overrides/roles/<slug>.toml`) gets a row if it holds the `dev` capability and no row if it does not.

Driven in a scratch squad: `builder` (per-slug file, `capabilities = ["dev"]`, activated) is listed with `project`; `analyst` (per-slug file, no capability, activated) is not listed. Both have the same origin and come from the same kind of file. Reading the catalog, an adopter cannot tell why one appears and the other does not. `test_the_catalog_names_no_bundled_origin` pins the gap (`assert not slugs & {"security-analyst", "sandbox-dev"}`).

The docstring also undersells what is listed: it says "plus the squad's templated developers", but declared developers are listed as well.

The implementation adds a second catalog walk: `developer_roles(...)` over `resolve_role_for_item` for every role item, plus a second `load_role_catalog`.

Suggested simplest rule: after the catalog entries, add one row for every activated role item the document does not declare. That covers templated developers, declared developers and per-slug project roles in a single line, with no developer test. If listing only developers is intended, the docstring and the FEAT-976 wording should say so explicitly.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T21:57:05Z] Elias Python:
  - Fixed: sq role catalog lists one row per role item the document does not declare, developer or not; docstring rewritten, the unreachable footer removed, surface and designation tests updated. Falsification: restoring the developers-only condition turns 5 tests red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Role catalog keeps a row for an archived developer that sq dev list drops

<!-- sq:finding:F2:body -->
The catalog's developer rows come from `list_roles()` without a live-status filter, so a developer the operator archived (`sq role go-dev status Archived`) keeps a catalog row with origin `system`. `sq dev list` drops it in the same squad (driven: after archiving, `dev list` shows only `builder` while `role catalog --json` still lists `go-dev`).

Bundled rows were already listed whatever their status, so this may be intended. If it is, say so in the docstring. If not, filter with `svc.spec.live_statuses(ROSTER_ROLE)`, as `role list`'s Live column does. Finding 1's simpler rule would raise the same question once for every non-declared row.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — New test comments name release versions

<!-- sq:finding:F3:body -->
New code comments name release versions, which the comment rule forbids (no versions or history in comments):

- `tests/integration/test_skill_migration.py`: "Only the 0.4 to 0.5 runner ran, so the 0.16 origin stamp is still to come."
- `tests/integration/test_memory_skill_migration.py`: "Only the 0.8 to 0.10 runner ran, so the 0.16 origin stamp is still to come."
- `tests/integration/test_migration_corpus.py` `_lift_extra`: "# the stamp the 0.16 step writes"

Describe what the comment means instead, e.g. "only one runner ran, so roles and skills carry no origin yet". Versions used as test data (fixture names, chlog ranges) are fine.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T21:57:07Z] Elias Python:
  - Fixed: the three comments no longer name release versions. Falsification: 0 tests, since no test reads comments; checked with rg for the old text.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T21:54:57Z] Paul Reviewer:
  - ST1-ST5 reviewed: no correctness defect found. The origin rule, stamps, check, repair round-trip, surfaces and migration contribution behave as specified on every shape driven. F1 (medium) is about catalog scope and simplicity: per-slug declared roles are listed only when they are developers. F2 and F3 are low.
  - @python-dev F1-F3 are for you; @manager recommended verdict: approve once F1 is settled (fix, or record that developers-only is intended).
- [2026-10-16T21:55:28Z] Catherine Manager:
  - F1: take the simpler rule, one catalog row for every role item the catalog document does not declare, developer or not. F2: follows from that rule (the row exists while the item does, live or retired); sq dev list stays live-only; not a defect. F3: fix.
<!-- sq:discussion:end -->
