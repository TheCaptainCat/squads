---
id: TASK-442
sequence_id: 442
type: task
title: 'Devops: path-scope Python test.yml off TS-only changes'
status: Done
parent: FEAT-100
author: tech-lead
assignee: devops
refs:
- ADR-427:addresses
- REV-438:addresses
description: Add paths filter to Python CI so TS-only changes skip the OS matrix;
  weigh required-checks caveat
created_at: '2026-07-17T07:45:21Z'
updated_at: '2026-07-17T08:02:53Z'
---
<!-- sq:body -->
## Owner

Devops-flavored — intended for **Hugo Ops** (devops). Authored here for
scope/traceability; the tech lead is not implementing it.

## Goal

Close REV-438 F3 (low): the Python CI (`.github/workflows/test.yml`) has no paths
filter, so a `clients/vscode`-only (TypeScript/doc-only) change triggers the full
3-OS Python matrix unnecessarily. Scope the Python lane so TS-only changes don't
run it — **but weigh the required-checks/branch-protection caveat first**.

## Context (from REV-438 F3)

The isolation is currently one-directional: `vscode-client.yml` is path-filtered
on `clients/vscode/**` so it never runs on Python-only changes, but `test.yml`
triggers on every push/PR to `main`. So the documented "a TS failure never blocks
a Python-only change, and vice versa" holds for *blocking* (the Python jobs pass
on a clients-excluded tree — ruff/pyright exclude `clients`, pytest doesn't scan
it), but CI is still wasted on every TS/doc-only PR, and the earlier handoff claim
that `test.yml` "never runs on TS-only changes" was inaccurate.

## Required: weigh the branch-protection caveat before choosing gating vs not

Paul (REV-438) and Hugo both flagged this: **a required status check skipped by a
paths filter can sit "pending" and block merge** unless branch protection is
configured to match (GitHub required-checks semantics). So before adding a
`paths`/`paths-ignore` filter, decide and document:

- If Python `test.yml` is (or will be) a **required** check on `main`, a
  `paths-ignore: ['clients/vscode/**']` that skips it on a TS-only PR leaves the
  required check unsatisfied → PR can't merge. In that case either (a) don't
  path-filter and instead just correct the stale isolation claim, or (b)
  path-filter **and** update branch protection (e.g. a required "gate passed"
  aggregation job that always runs and short-circuits when Python is skipped).
- If it's **not** a required check, a straightforward `paths-ignore` is fine.

State the chosen option and its branch-protection implication in the PR/handoff.

## Scope

- Add a `paths` / `paths-ignore` filter (or equivalent) to `test.yml` so
  `clients/vscode/**`-only changes don't trigger the Python OS matrix — **only if**
  the required-checks analysis above permits it; otherwise correct the isolation
  claim and document why the filter was not added.
- Do not weaken the Python gate for actual Python changes.

## Acceptance criteria

- Either: `test.yml` is path-scoped so TS-only changes skip it, with the
  branch-protection implication resolved and documented; **or** the filter is
  deliberately not added, the stale "never runs on TS-only changes" claim is
  corrected, and the reasoning (required-check pending-block risk) is recorded.
- The cross-language non-blocking isolation from ADR-427 still holds either way.

## Addresses

REV-438 F3 (low).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 442 add-subtask "<title>"`; track with `sq task 442 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T07:50:36Z] Hugo Ops:
  - Checked branch protection: 'main' currently has NO required status checks configured (gh api branches/main/protection -> 404 'Branch not protected'), so path-scoping test.yml is safe today — no pending-blocked-PR risk right now.
  - Added paths-ignore: ['clients/vscode/**'] to both push and pull_request triggers in .github/workflows/test.yml, mirroring vscode-client.yml's existing path filter in the other direction.
  - Caveat documented in-file (top-of-workflow comment) and here for the record: if test.yml's jobs are EVER made required checks on main, this filter will leave them 'pending' on TS-only PRs and block merge (GitHub required-checks semantics). Before doing that, either (a) don't mark these jobs required, or (b) add an always-running, non-path-filtered 'gate passed' aggregation job for branch protection to require instead. Not configuring branch protection myself -- flagging for Pierre/ops to weigh.
  - Isolation still holds per ADR-427: vscode-client.yml is TS-only (path-filtered), test.yml is now scoped off clients/vscode/**-only changes -- corrects the prior 'never runs on TS-only changes' claim, which is now literally true rather than just non-blocking.
  - @reviewer please check the paths-ignore logic and the branch-protection reasoning.
<!-- sq:discussion:end -->
