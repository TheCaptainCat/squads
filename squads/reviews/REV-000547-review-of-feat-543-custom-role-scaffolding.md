---
id: REV-547
sequence_id: 547
type: review
title: Review of FEAT-543 custom-role scaffolding
status: Requested
author: reviewer
refs:
- FEAT-543
subentities:
- local_id: F1
  title: scaffold_new_role does not validate the slug — path traversal / absolute-path
    arbitrary file write
  status: Verified
  severity: medium
- local_id: F2
  title: No slug-safety test — the highest-risk edge is unpinned
  status: Verified
  severity: low
created_at: '2026-07-21T21:19:26Z'
updated_at: '2026-07-21T21:29:01Z'
---
<!-- sq:body -->
Independent review of the FEAT-543 ergonomics layer (scaffold_new_role + sq override scaffold --new/--can-spawn, catalog/help/docs discoverability). Engine (resolver new-slug path, activate, can_spawn plumbing) pre-existed and is out of scope.

Verified end-to-end in a temp squad: scaffold --new writes a stamped TOML that parses back through resolve_role; can_spawn true/false round-trips correctly (spawn-capable pointer has no disallowedTools, non-spawn gets disallowedTools: Agent); show --json exposes can_spawn at top level; catalog --json shape is unchanged by the new hint; --role/--new mutual exclusion and bundled-slug rejection work with clean SquadsError messages; clobber/--force correct. pyright/ruff/sq check clean; 30 targeted tests green.

One real defect: the --new slug is written to disk with no path-safety validation (traversal + absolute-path arbitrary write), on a newly-advertised adopter create surface. See findings.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 547 add-finding "…" --severity medium`; track with `sq review 547 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | scaffold_new_role does not validate the slug — path traversal / absolute-path arbitrary file write |
| F2 | 🟢 low | Verified |  | No slug-safety test — the highest-risk edge is unpinned |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — scaffold_new_role does not validate the slug — path traversal / absolute-path arbitrary file write

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
scaffold_new_role builds `dest = _role_overrides_dir(squad_dir) / f"{slug}.toml"` and writes to it after only one check (slug not in _BUNDLED_ROLE_SLUGS). The slug is never validated or slugified, and this write bypasses the _paths.abspath traversal guard the codebase relies on everywhere else.

Confirmed in a temp squad: `sq override scaffold --new '/tmp/claude-1000/x'` wrote /tmp/claude-1000/x.toml — entirely outside the squad (pathlib discards the left operand on an absolute right side). `--new '../../pwned'` wrote squads/pwned.toml, escaping .overrides/roles/. `--new ''` wrote a bare .toml. All exit 0.

Failure scenario: an adopter (or an agent/automation supplying the slug from config) runs `sq override scaffold --new <slug>` where slug is attacker-influenced or malformed; sq writes a file to an arbitrary absolute path or clobbers a file outside the overrides tree. It's a newly-advertised adopter-facing create surface (docs + catalog hint point straight at it).

Note: the pre-existing scaffold_role (--role) shares the identical flaw (verified: --role '/tmp/.../x' also writes outside the squad), so this is a pre-existing class the feature replicates rather than introduces. Fix once, shared: a slug validator (reject '/', '\\', '..', empty/whitespace, leading dot; or restrict to a slug charset) used by both scaffolders, mirroring the abspath is_relative_to guard.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — No slug-safety test — the highest-risk edge is unpinned

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The new tests are thorough on clobber/--force, bundled-slug rejection, --role/--new mutual exclusion, can_spawn true/false, the resolve_role round-trip, activation + pointer denylist, and catalog --json shape. But there is no test for a hostile/malformed slug (traversal '../', absolute path, empty/whitespace). That is exactly the surface F1 flags, so the regression that would catch a fix is missing.

Failure scenario: someone hardens (or later regresses) slug validation and no test notices, because the traversal/absolute/empty cases are never asserted to be rejected. Add a service-level test asserting scaffold_new_role raises SquadsError (or slugifies safely) for '../x', '/abs/x', and '' — and keep the written path is_relative_to .overrides/roles/.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T21:26:45Z] Catherine Manager:
  - F1/F2 fixed by a shared _validate_role_slug guard in _overrides/_service.py, called by both scaffold_new_role and scaffold_role (rejects empty/whitespace, path separators, '..', leading dot; is_relative_to backstop → clean SquadsError). Verified live: --new '/tmp/...', '../../pwned', '' all exit 1 with nothing written outside .overrides/roles/. Full suite green (pyright 0/0, ruff, format, pytest all pass). Left Fixed for QA to verify.
<!-- sq:discussion:end -->
