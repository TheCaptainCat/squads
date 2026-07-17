---
id: TASK-433
sequence_id: 433
type: task
title: Bundle VSIX as a release asset at the unified version
status: Done
parent: FEAT-100
author: tech-lead
assignee: devops
refs:
- ADR-427:addresses
- TASK-432:depends-on
created_at: '2026-07-16T13:51:30Z'
updated_at: '2026-07-17T08:02:52Z'
---
<!-- sq:body -->
## Owner

Devops-flavored — intended for **Hugo Ops** (devops). Authored here for scope/traceability; the tech lead is not implementing it.

## Goal

Ship the extension as part of the **one release bundle**: build the VSIX and attach it as a downloadable release asset at the **unified version**, wired into the existing release chain alongside the Python core.

## Scope

- Build the VSIX (`vsce package`) for `clients/vscode/` as a **release artifact** in the same release chain that builds/ships the core — one build, one bundled deploy.
- **Unified version**: the extension carries **no** independent semver — its version **is** the core's version, sourced the same way and set by the same single release bump. The bundle's client always matches the core it was built against.
- Attach the built VSIX to the tagged release as an installable, downloadable asset (one VSIX per release).
- Wire this into the release chain so cutting a release produces the VSIX asset as part of the normal flow.

## Out of scope for 0.10 (explicit)

- **Marketplace / Open VSX publishing** — deferred to a later, additive pipeline step (needs publisher account + CI credentials, unsettled). "Deploy the client" for 0.10 = **VSIX attached as a release asset only**; no publisher account / CI secrets needed this release. Structure the pipeline so a marketplace-publish step is a later add-on, not a re-architecture.
- Bundling the `sq` binary inside the VSIX (the extension discovers an operator/workspace `sq`).

## Acceptance criteria

- Cutting a release builds the VSIX and attaches it to the tagged release as a downloadable asset.
- The VSIX version equals the core version from the single release bump — no separate extension semver anywhere.
- The build happens in the unified release chain (not a local-only/manual step).
- Marketplace publish is demonstrably a later add-on step, not wired for 0.10.

## Release-process note

Per the project's release ownership: agents **prepare** the release (build the VSIX asset, wire the chain, green gates) but never git-tag or publish — the actual tag/publish is the release owner's call. This task delivers "VSIX asset builds and is ready to attach," not a published release.

## ADR-427 constraints this task must honor

- #4 Packaging (one bundle): VSIX as a release asset, built in the same chain as the core; marketplace publish deferred.
- #5 Versioning (unified): extension version == core version, one bump, no independent semver.
- Distinct from the dev-time CI lane (isolated); the release pipeline is the **unified** side of the two boundaries.

## Implementer note

sq/ticket IDs must not appear in source or pipeline file names — name by behavior.

Implements FEAT-100 (release/packaging, spans US1–US3). Addresses ADR-427.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 433 add-subtask "<title>"`; track with `sq task 433 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T07:50:28Z] Hugo Ops:
  - Added .github/workflows/release.yml, triggered on push tags v* only (never on every push) — separate from the dev-time vscode-client.yml gate.
  - Unified version (ADR-427 #5): core version is read from pyproject.toml via tomllib at build time, then set into clients/vscode/package.json with 'npm version <core-version> --no-git-tag-version --allow-same-version' before 'vsce package' — no independent extension semver, no reliance on the hardcoded 0.9.0.
  - Packaging (ADR-427 #4): builds VSIX with 'npx @vscode/vsce package' and attaches it via softprops/action-gh-release as a downloadable release asset. No marketplace/Open VSX publish step added — VSIX-as-asset only, per explicit 0.10 deferral.
  - Did not tag, release, or run the workflow — config only, gates green (YAML validated). @reviewer please check the unified-version injection logic and packaging step.
  - Only .github/workflows/release.yml touched; no clients/vscode/ source edits.
<!-- sq:discussion:end -->
