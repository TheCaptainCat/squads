---
id: REV-1157
sequence_id: 1157
type: review
title: 'Review TASK-1153 ST8: mention hover reads sq role list --json'
status: Approved
author: reviewer
refs:
- TASK-1153
description: 'Review of commit 91218ad1: the VS Code mention hover reads name and
  description from sq role list --json.'
subentities:
- local_id: F1
  title: 'Archived roles become mention targets: sq role list --json includes them,
    the old default list view did not'
  status: Verified
  severity: high
- local_id: F2
  title: Skew canary pins role list keys without description and now fails; new guard
    clauses untested
  status: Verified
  severity: medium
- local_id: F3
  title: 'Preview wiring is unpinned: feeding sq list rows to roleDirectoryFrom compiles
    and passes all tests'
  status: Verified
  severity: low
created_at: '2026-10-26T02:39:33Z'
updated_at: '2026-10-26T02:48:47Z'
---
<!-- sq:body -->
## Scope

Commit 91218ad1 on `release/0.17`: TASK-1153 ST8, the VS Code `@mention` hover reading a role's name and one-line description from `sq role list --json` (ADR-1151 decision 3, client leg). Changes under `clients/vscode/` only.

## Method

- Drove the dev build in a scratch squad: `init`, `sq dev add --tech python`, `sq role add release-captain` (item-defined), `sq operator add`, then archived the item-defined role. Compared `sq role list --json` with `sq list -t role --json` row by row.
- Ran `npm run test:canary -t "roster identities"` against the dev build.
- Mutated a scratch copy of `clients/vscode` (not the repo): (a) `buildRoleDirectory` falls back to `title` when `full_name` is absent; (b) the preview feeds `sq list --all` rows into `roleDirectoryFrom`.
- Gates in `clients/vscode`: `npm run lint` clean, `npm test` 742 passed.

## Verified

- Row shape: every `sq role list --json` row carries `id`, `slug`, `full_name` and `description`, all strings. Catalog, template and item-defined roles all resolve a non-empty description, while `sq list -t role --json` carries `''` on catalog and template roles. The guard accepts every row.
- Skipping rows without `id`/`full_name`: operators are not in `sq role list`; `--name ""` and `--desc ""` are refused by `sq role add`, so no live row has a blank name. The skip only drops foreign row shapes.
- Dropping the `sq list -t role` fetch: the preview read only the role directory from it; pronouns and heading identities already came from `sq role list --json`. `tsc` and the tests confirm nothing else read `roleList`. One behaviour went with the fetch, though (F1).
- Mutation (a) fails the shape canary in `roleDirectory.test.ts`. Mutation (b) passes `tsc` and the whole suite (F3).
- Conventions: no ticket IDs in code or tests. The doc comments describe current behaviour.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1157 add-finding "…" --severity medium`; track with `sq review 1157 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Archived roles become mention targets: sq role list --json includes them, the old default list view did not

<!-- sq:finding:F1:body -->
**What.** `buildRoleDirectory` (`clients/vscode/src/domain/roleDirectory.ts`) now builds the mention directory from every `sq role list --json` row. That list includes archived roles (`status` on each row), so `@<slug>` for an archived role becomes a link to its item, with a hover. The removed `sq list -t role` fetch ran the default view, which hides terminal statuses. The removed `itemPreviewManager.ts` doc comment gave that as the reason: "an archived role is not a mention target".

**Evidence.** Scratch squad on the dev build: after `sq role release-captain status Archived`, `sq role list --json` still emits the row with `"status": "Archived"`, and `sq list -t role --json` leaves it out. Nothing in `buildRoleDirectory` or `roleDirectoryFrom` reads `status`, and `SqRosterIdentity` has no `status` field.

**Fix.** Keep only rows whose status is live for the role type: the CLI's own `svc.spec.live_statuses(ROSTER_ROLE)`, or the client's status catalog. Do not hardcode `Archived`. Add a row with a terminal status to the table, expecting no entry.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T02:44:52Z] `typescript-dev` Ada Typescript:
  - Fixed. buildRoleDirectory takes the status vocabulary (status catalog + roles catalog, fetched by the preview) and leaves out any role whose status resolves to a hidden role; no status name is hardcoded. If either catalog fetch fails every role stays a target. Tests: a hidden-status row is dropped, and an unavailable vocabulary keeps all rows (roleDirectory.test.ts).
- [2026-10-26T02:48:42Z] `reviewer` Paul Reviewer:
  - Verified on c10a6f40: on the dev build with release-captain Archived, the live role list, statuses and roles JSON pass the guards, and buildRoleDirectory keeps 8 of 9 roles, release-captain out. When the catalogs fail, all 9 stay targets. I accept that: it only shows a link, and it matches how the other catalog joins degrade.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Skew canary pins role list keys without description and now fails; new guard clauses untested

<!-- sq:finding:F2:body -->
**What.** `test/canary/skewCanary.test.ts` pins the exact key set of a `sq role list --json` row (`ROLE_LIST_KEYS`), and that set does not include `description`. Against the dev build, `npm run test:canary -t "roster identities"` fails: `expected [ 'capabilities', 'description', ... ] to deeply equal [ 'capabilities', 'full_name', ... ]`. This commit makes `description` a field the client relies on but leaves the canary that pins the surface unchanged. The canary also never checks that `description` is a non-empty string on catalog, template and item-defined rows, which is the property the hover depends on.

**Also.** The new `full_name`/`description` clauses in `isSqRosterIdentity` have no cases in `test/sqAdapter.test.ts` (around line 1357). A non-string value is not shown to be rejected. Because `runSqJson` rejects the whole array if any row fails the guard, a regression there would also drop pronouns in the preview and the roster tree.

**Fix.** Add `description` to `ROLE_LIST_KEYS`. Assert a non-empty `description` on the manager row, a `sq dev add` row and a `sq role add` row. Add accept and reject cases for `full_name`/`description` to the guard test.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T02:44:55Z] `typescript-dev` Ada Typescript:
  - Fixed. ROLE_LIST_KEYS gains description; the canary now also asserts a non-empty description on every row after adding a template (python-dev) and an item-defined role, and uses the new isSqRoleListRow guard. sqAdapter.test.ts: accept and reject cases for the role-row guard (non-string description, full_name, missing status or id, generic list row) and a test that one bad row rejects the whole array as parse-error, which is intended. The role-list canary passes on the dev build. The full canary still has one failure outside this work: the sq workflow roles entry now carries a deferred field the committed expectation lacks.
- [2026-10-26T02:48:44Z] `reviewer` Paul Reviewer:
  - Verified: npm run test:canary passes 85 of 85 against the dev build, the deferred expectation included. The guard cases are in sqAdapter.test.ts.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Preview wiring is unpinned: feeding sq list rows to roleDirectoryFrom compiles and passes all tests

<!-- sq:finding:F3:body -->
**What.** `roleDirectoryFrom` takes `SqOutcome<readonly SqRosterIdentity[]>`. Because `full_name` and `description` are optional there, a `SqListItem` (`id`, `slug`, `description`) fits it structurally. Wiring the preview back to a generic list fetch compiles and passes every test, and the result is an empty directory: no mention links and no error.

**Evidence.** Mutation in a scratch copy: `roleDirectoryFrom(itemList, …)` in `itemPreviewManager.ts` (the `sq list --all` rows). `tsc --noEmit` passed, and `npm test` gave 742 of 742 passing. The canary in `roleDirectory.test.ts` covers `buildRoleDirectory` on its own, not which fetch the preview passes it. That is the half of "the hover is not reading the old surface" the spec asked to pin.

**Fix (either).** Give `buildRoleDirectory` and `roleDirectoryFrom` a role-row type with a required `full_name` (narrowed by the guard), so a list row is a type error. Or add one test that drives the preview render through a stub runner and asserts the hover text comes from the `role list` payload.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T02:44:57Z] `typescript-dev` Ada Typescript:
  - Fixed by type: sq role list rows are now SqRoleListRow with required id, full_name and status; getRoleIdentities returns them and buildRoleDirectory/roleDirectoryFrom accept only that type, so passing sq list rows is a type error (a generic list row has no full_name, and the guard rejects it at runtime too).
- [2026-10-26T02:48:45Z] `reviewer` Paul Reviewer:
  - Verified: passing itemList to roleDirectoryFrom in a scratch copy now fails tsc with TS2345 (SqListItem[] is not assignable to SqRoleListRow[]).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T02:40:13Z] `reviewer` Paul Reviewer:
  - Request changes: 3 findings. F1 (high): archived roles are now mention targets because sq role list --json includes them; filter on live statuses. F2 (medium): the skew canary pins the role list keys without description and fails on the dev build; the new guard clauses have no tests. F3 (low): the preview wiring is not pinned, so feeding sq list rows to roleDirectoryFrom compiles and passes. Row shape, the skip rule and dropping the fetch otherwise check out. Lint is clean and npm test passes 742. @typescript-dev
- [2026-10-26T02:48:46Z] `reviewer` Paul Reviewer:
  - Re-review of c10a6f40: F1 to F3 verified, no new findings. In clients/vscode, lint and tsc are clean, npm test passes 746 and test:canary passes 85 against the dev build. Approving.
<!-- sq:discussion:end -->
