---
id: ADR-427
sequence_id: 427
type: decision
title: 'VS Code extension: in-repo TypeScript client architecture'
status: Accepted
author: architect
refs:
- EPIC-99
- FEAT-100
description: 'In-repo VS Code extension at clients/vscode/: isolated dev-time TS toolchain,
  pure consumer of frozen sq --json + rendered sq show, workspace-toolchain sq discovery,
  browse-only for 0.10; one release bundle — client built/shipped with the core at
  the unified version (VSIX as a release asset)'
created_at: '2026-07-16T13:40:12Z'
updated_at: '2026-07-16T15:38:49Z'
---
<!-- sq:body -->
## Context

EPIC-99 brings a second language into this repo: a VS Code extension (TypeScript/Node) that lets
operators browse the squad from the editor. FEAT-100 is the first, browse-only increment — an
activity-bar tree plus a rendered item preview. Mutations (transition/comment/assign from context
menus) are a later increment, not a non-goal.

The core is Python/uv with a strict gate (`pyright` strict, `ruff`, `pytest`, `sq check`) and a
frozen machine surface: FEAT-15 (Done) closed the `--json` gaps, documented the exit-code table,
and pinned every read shape with golden-file tests. The extension is a **pure consumer** of that
surface. The architectural question is not *how to write TypeScript* but *how a second toolchain
lives in this repo without contaminating the core's gates, and how the client couples to the CLI
so the frozen contract — not our internals — is the only thing it depends on.*

## Decision

**1. Placement & isolation.** The extension lives at `clients/vscode/` as a self-contained
TypeScript/Node package (`clients/` reserved for future non-Python clients). It has its own
toolchain (npm/tsc/ESLint/its own test runner) and its own lockfile, entirely disjoint from the
Python core. The Python gate (`pyright`/`ruff`/`pytest`/`sq check`) never looks at `clients/`, and
the TS gate never touches Python. No shared build, no shared config inheritance, no shared virtual
env. `clients/` is added to the Python tooling's ignore set so a stray `.ts`/`node_modules` can
never fail a Python run, and vice versa.

**2. Consumer contract (the coupling rule).** The extension talks to the squad **only** by shelling
out to the `sq` binary with `--json`, treating stdout as the frozen 1.0 shapes and the exit code as
the documented contract. It MUST NOT read `.claude/` and MUST NOT parse `.squads.json` — the index
is a rebuildable internal, not a frozen surface (invariant #1). Concretely, FEAT-100 depends on
exactly three surfaces:
  - `sq tree <root> --json` — drives the sidebar tree (id/type/status/assignee/blocked/children).
  - `sq list --json` — feeds the flat/filtered/grouped views (US3).
  - `sq show <id> --raw` — its clean-markdown dossier (H1 title + metadata block + body markdown,
    no Rich chrome) piped into a **read-only `squads:` virtual document** opened in VS Code's
    markdown preview (US2): clean prose, no frontmatter or `<!-- sq:* -->` marker noise. This
    depends on two core surface changes landing first — `sq show --raw` emitting genuinely clean
    markdown (dropping its box-panel header) and `sq show --json` growing the item `body`
    (+ discussion) — specified as a prerequisite core task.

  **`sq` discovery.** The extension resolves how to invoke `sq` by auto-detecting the workspace
  toolchain — never PATH-only. Resolution order (first that works wins), against the workspace root:
  1. explicit config override (`squads.sqPath`, or a `squads.command` array);
  2. a workspace virtualenv — `.venv/bin/sq` (`.venv/Scripts/sq.exe` on Windows);
  3. `uv` present + a project → `uv run sq`;
  4. `poetry` present + a project → `poetry run sq`;
  5. bare `sq` on PATH (fallback).

  The resolved invocation is cached and re-probed on failure. Failure modes, all surfaced as VS Code
  notifications (never a crash, never a partial silent tree):
  - **No `sq` found by any strategy** → actionable error naming the order tried and the
    `squads.sqPath` override, tree shows an error node, no throw.
  - **Non-zero exit** → map by the frozen table: `2` usage (our bug — log the argv), `3` check
    failure (irrelevant to read paths but surfaced verbatim), `1`/other runtime (show stderr).
  - **Version/schema skew** → the CLI already hard-stops with exit `1` and a "run `sq migrate up`"
    message when the on-disk schema mismatches the installed `sq`; the extension surfaces that
    message rather than trying to reason about schema itself. It pins **no** schema knowledge.

**3. Testing strategy + quality parity.** TypeScript is held to the **same strict bar as the Python
core** — no laxer gate for the new language. Parity: `tsc` strict + strict-plus flags
(`noUncheckedIndexedAccess`, `noImplicitReturns`, `noImplicitOverride`, `noFallthroughCasesInSwitch`,
`noUnusedLocals`, `noUnusedParameters`, `exactOptionalPropertyTypes`, `isolatedModules`) ≈ pyright
strict; `typescript-eslint` strict-type-checked + stylistic-type-checked with complexity ≤12 and
max-params ≤8 (mirroring ruff C901/PLR), import ordering, bugbear/simplify rules, **zero warnings**;
Prettier `--check` (≈ `ruff format --check`). A single `npm run check` mirrors
`pyright && ruff check && ruff format --check`. **Enforcement nuance (consistent with #1):**
within TypeScript this gate is strict and **blocking** — must-pass for any change touching
`clients/vscode/`; **cross-language it stays isolated** — a TS failure never blocks a Python-only
change, and vice versa.

Tested inside `clients/vscode/` with its own runner, three layers:
  - **Unit** — parse/adapt logic (JSON → TreeItem, error/exit-code mapping) against **committed
    fixture JSON captured from real `sq … --json` output**. This is the bulk of the value and runs
    with no `sq` binary present.
  - **Integration (thin)** — a small suite that runs a real `sq` against a scratch squad to confirm
    the fixtures still match the live shapes (skew canary); skippable when `sq` is absent.
  - **Extension host** — a minimal `@vscode/test-electron` smoke test that the tree loads and a
    preview opens.

  **Dev-time** CI: a **separate workflow/job keyed on `clients/vscode/**`** paths, running the TS
  gate. It is **independent of and non-gating for the Python core** — a red TS job never blocks a
  Python-only change and vice versa. Cross-language coupling is caught only by the integration skew
  canary, by design. (This dev-time isolation is distinct from the release pipeline, which unifies
  the two — see #4/#5.)

**4. Packaging / distribution (one bundle).** A release is a **single bundle**: the release pipeline
builds AND ships the client alongside the core, in the same chain, at the same version. It builds the
VSIX (`vsce package`) as a **release artifact** — not a local-only, not-deferred thing — and attaches
it to the tagged release (a downloadable, installable VSIX per release). "Deploy the client" for 0.10
means **the VSIX is a published release asset**; **marketplace publishing** (VS Code Marketplace /
Open VSX) is the open item — it needs a publisher account and credentials in CI that aren't settled
here (see Open Questions). The pipeline is structured so marketplace publish is a later add-on step,
not a re-architecture.

**5. Versioning (unified).** The extension does **not** carry an independent semver. Its version
**is** the core's version, sourced the same way and bumped by the same single release bump — one
version for the whole bundle. The client therefore always ships matched to the core it was built
against, so no `--json`-contract skew can exist between a release's client and its CLI. (The
CLI's own on-disk-schema hard-stop from #2 still guards an operator running a bundle against a
squad written by a *different* version.)

## Consequences

- A clean second-toolchain boundary: TS churn can never redden the Python gate, and the client can
  only break if the *frozen* surface breaks — which the golden tests already forbid silently.
- The client is thin and mockable: nearly everything is unit-tested against captured fixtures, so it
  builds and tests without a live `sq`.
- The mutation increment is a clean additive layer — same shell-out pattern, adding *write* verbs
  (`sq <type> <n> transition|comment|assign`) behind command palette / context menus, reusing the
  exit-code mapping. Nothing here needs revisiting to add it.
- Cost: two dev-time CI lanes and a fixture-refresh discipline (the skew canary is what catches a
  drifted shape between the two languages).
- Two boundaries that must not be confused: **dev-time gates stay isolated** (a TS-only failure
  won't block a Python-only change), while the **release pipeline is unified** (one build, one
  version, one bundled deploy). The isolation is about fast, non-cross-blocking iteration; the
  unification is about shipping a matched set.
- The unified version removes a whole class of skew: a release's client and CLI are always the same
  version, so the only version story to reason about is bundle-vs-on-disk-schema, not client-vs-CLI.

## Deferred (out of scope for this ADR / 0.10)

- **Marketplace / Open VSX publishing** — the pipeline attaches the VSIX to the release now;
  publishing to a marketplace is a later, additive pipeline step pending the credentials decision.
- All mutation flows (write verbs from the editor).
- Bundling the `sq` binary itself inside the VSIX — the extension discovers an operator/workspace
  `sq` (decision #2); shipping a vendored `sq` is not in scope.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-16T13:45:21Z] Pierre Chat:
  - sq discovery: auto-detect the workspace toolchain — .venv, uv (uv run sq), and poetry (poetry run sq) — in addition to a config override + PATH fallback. Don't ship PATH-only.
- [2026-07-16T13:45:22Z] Pierre Chat:
  - Override decisions #4 (packaging) and #5 (versioning): releases are ONE bundle. The clients build and deploy together WITH the main software, at the SAME version — no independent extension semver. The release CI chain produces and ships the client alongside the core at the unified version.
- [2026-07-16T13:47:08Z] Robert Architect:
  - Revised per Pierre's two overrides: (1) #2 sq discovery now auto-detects the workspace toolchain (.venv / uv run / poetry run) + config override, PATH is only the last fallback; (2) rewrote #4/#5 to one release bundle — client built+shipped with the core at the unified version, VSIX as a release asset (no independent semver). Kept dev-time gate isolation (#1/#3) and made the dev-isolation vs release-unification distinction explicit. Marketplace/Open VSX publish remains the open item (credentials).
- [2026-07-16T13:48:12Z] Pierre Chat:
  - 0.10 deploy = VSIX attached as a release asset only; marketplace/Open VSX publish deferred to a later step. No publisher account/CI secrets needed this release.
- [2026-07-16T13:48:13Z] Catherine Manager:
  - Accepted following Pierre's review and the recorded override decisions (unified bundle+version, sq auto-discovery, VSIX-as-asset). @tech-lead — ADR-427 constrains FEAT-100; ready to break the 3 stories into tasks under clients/vscode/.
- [2026-07-16T13:50:09Z] Pierre Chat:
  - TypeScript must meet the SAME strict quality bar as the Python core — no laxer gate for the new language. Parity: tsc strict (+ noUncheckedIndexedAccess/noImplicitReturns/noUnusedLocals/exactOptionalPropertyTypes ≈ pyright strict), typescript-eslint strict-type-checked with complexity/max-params rules mirroring ruff (C901/PLR), Prettier --check (≈ ruff format), zero warnings. It's a hard must-pass gate FOR TS changes; cross-language isolation from the Python gate is unchanged (within-language strict, cross-language non-blocking).
- [2026-07-16T15:26:12Z] Robert Architect:
  - CLI readiness audit for FEAT-100 (ran the real commands; verdicts below). Bottom line: one HIGH gap blocks US2; US1/US3 + all cross-cutting checks are READY.
  - US1 tree — READY. sq tree --json carries id/type/status/priority/assignee/blocked/children and nests correctly (rooted + no-root; FEAT-100 sits under EPIC-99). --all reveals closed. Rough-edge (low): no-root forest mixes the 3 reserved meta types (role/skill/operator) with work items and there's no server-side 'work-items' filter nor a machine-readable type catalog (sq workflow --json doesn't exist); client excludes the 3 reserved types (-t is repeatable as an alternative). Not a blocker.
  - US2 preview — GAP, HIGH (blocks US2). No clean-markdown mode exists. sq show default AND --raw both emit a Rich box-drawing header panel (~180 box chars) + space-aligned summary table + '=== US ===' separators — terminal chrome, not markdown. sq show --json carries NO body/discussion (metadata + sub-entity state only); --full/--comments don't add prose to JSON. Reading .md is contract-forbidden. So item prose is unreachable as markdown via any sq surface. Fix: new 'sq show --format md' (H1 title + metadata block + body markdown verbatim; --comments/--full append discussion/sub-entities). Body is already stored as raw markdown between markers, metadata == show --json data → small, additive, reusable (sq web/MCP). Must be golden-frozen like the rest.
  - US3 filter/group/refresh — READY. sq list --json carries type+status (+priority/assignee/parent/labels); -t/-s filter, -a includes closed; refresh = re-invoke. Enough to group by type and open/closed.
  - Cross-cutting — all READY. FORCE_COLOR=3 clean (0 ESC bytes, valid JSON on tree/list/show --json — BUG-183 holds). Exit codes: 0 ok / 1 runtime / 2 usage / 3 check-errors (warnings-only=0), all confirmed empirically. Schema-skew HARD-STOPS reads with exit 1 + actionable stderr in BOTH directions (behind=migrate up, ahead=upgrade pkg) — this is the guard ADR-427 #2 relies on. sq --version works. stdout=data / stderr=errors cleanly separated (stdout empty on error).
  - CORRECTION to a pre-checked item: closed-root 'sq tree EPIC-12 --json' is exit **1** (stable over 3 runs), NOT 0 — stdout empty, stderr an actionable 'add --all' message. A machine consumer distinguishes it by exit code; the earlier exit-0 reading was almost certainly a pipeline's exit code, not sq's. Defensible per the contract; not a violation. (Minor asymmetry vs list's []-exit-0 on no-match; optional nicety, not a blocker.)
- [2026-07-16T15:36:39Z] Pierre Chat:
  - US2 preview resolution — do NOT add a new --md flag. Instead fix the two existing surfaces: (1) sq show --raw must emit genuinely clean output (drop the Rich box-drawing header panel it still renders; it already advertises 'plain text' — make that true) — this becomes the markdown feed for the preview; (2) sq show --json must include the item BODY (and discussion) too, so the structured surface is complete rather than metadata-only. The extension's US2 preview reads sq show --raw. Both are surface changes to golden-freeze; assess back-compat of the --raw behavior change.
- [2026-07-16T15:38:49Z] Robert Architect:
  - US2 core-prerequisite surface spec (per Pierre: fix the two existing surfaces, NO new --md flag). For the tech lead to cut a core task from.
  - (A) sq show <id> --raw — new behavior: emit a deterministic, markdown-preview-clean dossier with ZERO Rich chrome (no box-drawing header panel, no space-aligned summary table, no '=== US … ===' separators). Structure: '# TYPE-N — <title>' (H1); then a metadata block as a bullet list of bold-key lines ('- **status:** …' for status/priority/assignee/parent/author/refs/labels, omitting absent fields — chosen over a md table: deterministic, no column-width ambiguity, clean omission); blank line; then the body markdown verbatim. --comments appends '## Discussion' with each comment as '### <author> — <ISO ts>' + its md. --full appends one '## <Kind> <local_id> — <title>' section per sub-entity (badge line + body md). Only --raw changes; default styled mode keeps its Rich rendering for terminal humans.
  - (B) sq show <id> --json — ADDITIVE superset (new keys only, nothing renamed/removed): add top-level 'body' (raw body markdown) and 'discussion' (ordered list of {author, ts, body}); add 'body' to each object in the existing 'subentities' array (currently state-only: assignee/extra/local_id/severity/status/story/title). Include these UNCONDITIONALLY — not gated by --comments/--full — to preserve the current invariant that 'show --json' is byte-identical across --raw/--comments/--full (test_json_output_is_byte_identical_regardless_of_raw_or_comments_flags).
  - (C) Back-compat of the --raw change: no current test/consumer asserts the box-panel chrome — the two --raw tests (test_show_command_renders_body_and_subentities, test_body_content_source_and_mutual_exclusion_cli) only assert body substrings ('## Section' passthrough), which the clean output preserves. --raw is human-facing plain text, OUTSIDE FEAT-15's frozen machine surface (that froze --json shapes + exit codes), so this is NOT a frozen-surface break — but it IS a user-visible formatting change that warrants a CHANGELOG note. The --json additions are additive, so they don't break the freeze either.
  - (D) Golden-freeze: --raw currently has NO golden — ADD new raw-text goldens (e.g. item_show_raw.txt covering an item with body + sub-entities + a comment, deterministic under frozen clock). The --json additions change bytes of the existing per-type goldens — UPDATE feature_show.json / task_show.json (+ any show --json golden that now carries body/discussion) in the same PR. Both surfaces then carry FEAT-15-style golden coverage.
<!-- sq:discussion:end -->
