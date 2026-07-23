---
id: TASK-631
sequence_id: 631
type: task
title: Add docs command-test shelling documented verbs against the CLI
status: Draft
parent: FEAT-574
author: tech-lead
description: 'US4: drift guard — extract documented sq invocations, assert each resolves;
  normal pytest gate'
created_at: '2026-07-23T08:03:52Z'
updated_at: '2026-07-23T08:03:52Z'
---
<!-- sq:body -->
Implements FEAT-574 **US4**. The durable part of the feature: a mechanical drift guard
so documented CLI verbs can't silently rot between releases. A test extracts the `sq …`
invocations shown in the docs and asserts each resolves against the live CLI, failing
the build when a documented verb no longer exists.

**Build order:** land this **last** in the 574 chain — it only passes once FEAT-575's
verbs exist AND the US1 doc fixes have removed the non-existent invocations. Until then
it (correctly) fails.

## What it checks

- **Extraction:** scan `docs/*.md` for `sq …` invocations — fenced code blocks
  (```` ```sh ```` / ```` ```bash ````) and inline `` `sq …` `` spans. From each, take
  the **command path** (the sequence of subcommand tokens before the first option/
  positional), e.g. `sq role catalog`, `sq operator list`, `sq feature <n> add-story`,
  `sq task <n> subtask <k> remove`.
- **Placeholder normalization:** replace concrete ids/numbers/quoted args with the
  metavar slot so an addressed verb like `sq feature 7 add-story "…"` normalizes to the
  `feature <n> add-story` command path. Handle the address-dispatch groups
  (`feature`/`task`/… `<n> <verb>`, sub-entity `<kind> <k> <verb>`).
- **Resolution:** resolve each normalized command path against the Typer app's command
  tree via `CliRunner` + `--help` at each level (walk the group tree), asserting the
  final token is a registered command / the `--help` exits 0. Do **not** execute
  mutating commands — resolution/`--help` only.
- Curate a small allowlist for invocations that are illustrative-not-literal (shell
  pipes, `$(...)`, placeholder-only lines) so the extractor stays high-signal; keep the
  allowlist tiny and commented with why each entry is exempt.
- **Version-string drift (secondary, best-effort):** optionally assert that any
  `override-base:<x.y.z>` literal shown in docs is not behind `squads.__version__`
  (coordinate with the FEAT-574 US2 phrasing — a `<version>` placeholder is exempt).
  Keep this a separate, clearly-scoped assertion; the verb-resolution guard is the
  primary deliverable.

## Placement / gate

- Lives under `tests/` and runs as part of the normal `uv run pytest` gate — **not**
  a separate opt-in step and **not** `slow`-marked. Name the module by behaviour
  (documented-CLI-verbs-resolve), no ticket id in the filename.
- Fast: it walks `--help`, it does not spin up squads or touch a tmp squad beyond what
  `CliRunner` needs.

## Tests-of-the-test

- Include a self-check that the extractor actually finds a known-present verb (so a
  broken extractor that silently matches nothing can't pass vacuously) — e.g. assert
  the extracted set is non-empty and contains a couple of anchor verbs like
  `role catalog` and `feature <n> add-story`.

## Conventions (apply to every deliverable)

- No status/lifecycle prose in any body/doc (frontmatter `status:` is the single
  source of truth). The category term is **roster**, never "meta".
- No ticket IDs in source or test names — name by behaviour; keep the pointer in the
  sq ref/comment. Use PEP-695 `type X = …` for any alias. User-facing errors are the
  `SquadsError` family. Escape console output via `_cli._common.e()`.
- If you add any module-level constant, run `tests/meta` in your gate (the
  mutable-state guard has tripped repeatedly). Run all gates with `uv run --all-extras`
  (pyright/ruff/pytest) — a bare `uv run` prunes the `tui` extra and floods false
  errors.
- Set sq bodies via the CLI only; if you use `--file`, verify `grep -c '</\?content>'`
  == 0 on the written body. Run `uv run sq check` clean before handing off.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 631 add-subtask "<title>"`; track with `sq task 631 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
