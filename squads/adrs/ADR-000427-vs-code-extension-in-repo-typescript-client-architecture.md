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
- ADR-1007
description: 'In-repo VS Code extension at clients/vscode/: isolated dev-time TS toolchain,
  pure consumer of frozen sq --json + rendered sq show, workspace-toolchain sq discovery,
  browse-only for 0.10; one release bundle — client built/shipped with the core at
  the unified version (VSIX as a release asset)'
created_at: '2026-07-16T13:40:12Z'
updated_at: '2026-10-25T21:27:16Z'
---
<!-- sq:body -->
## Context

EPIC-99 brings a second language into this repo: a VS Code extension (TypeScript/Node) that lets
operators browse the squad from the editor, through trees in the activity bar, a rendered item
preview, search, the board and the workflow.

The core is Python/uv with a strict gate (`pyright` strict, `ruff`, `pytest`, `sq check`) and a
frozen machine surface: the `--json` read shapes and the documented exit-code table. The extension
is a **pure consumer** of that surface. The architectural question is how a second toolchain lives
in this repo without contaminating the core's gates, and how the client couples to the CLI so the
frozen contract, not the core's internals, is the only thing it depends on.

## Decision

**1. Placement and isolation.** The extension lives at `clients/vscode/` as a self-contained
TypeScript/Node package (`clients/` is reserved for non-Python clients), with its own toolchain
(npm, tsc, ESLint, vitest) and lockfile, disjoint from the Python core. The Python tooling excludes
`clients/` (ruff `extend-exclude`, pyright `exclude`), and the TS gate never touches Python. No
shared build, config inheritance or virtual environment.

**2. Consumer contract (the coupling rule).** The extension reads the squad **only** by running the
`sq` binary, treating `--json` stdout as the frozen shapes and the exit code as the documented
contract. It never reads `.claude/` and never parses `.squads.json`, a rebuildable internal
(invariant #1); it only watches that file's modification to know when to refresh. The surfaces it
runs are read commands: `sq tree --json`, `sq list --json`, `sq show <id> --json` and `--raw` (the
clean-markdown dossier rendered in a read-only `squads:` virtual document), `sq search --json`,
`sq graph --json`, `sq board list --json`, `sq memory <slug> list --json`, `sq role list --json`,
`sq operator list --json`, and the `sq workflow` catalogs.

The frozen shapes freeze each key's name, type, presence and meaning, not every key's value set.
The client tolerates an unknown value in an open-set key (`edge_semantic` in `sq graph --json`,
`region` in `sq search --json`, `role` in `sq workflow ref-kinds --json`) and reads vocabulary
values (type, status, priority, ref kind, assignee) from the catalogs rather than hardcoding them
(ADR-1025). An item row is flat, each stored attribute at the top level (ADR-1007); the client reads
no nested `extra` key, and its skew canary checks each non-core key against the type's declared
attributes.

**`sq` discovery.** The extension resolves how to invoke `sq` from the workspace toolchain, never
PATH-only; first match wins, against the workspace root:

1. explicit config (`squads.sqPath`, or a `squads.command` array);
2. a workspace virtualenv, `.venv/bin/sq` (`.venv/Scripts/sq.exe` on Windows);
3. `uv` present and a project → `uv run sq`;
4. `poetry` present and a project → `poetry run sq`;
5. bare `sq` on PATH.

The resolved invocation is cached and re-probed on failure. Failures surface as VS Code
notifications or an error node, never a crash or a silently partial tree:

- **No `sq` found** → an actionable error naming the order tried and the `squads.sqPath` override.
- **Non-zero exit** → mapped by the documented exit-code table, stderr shown.
- **Schema skew** → the CLI hard-stops with a "run `sq migrate up`" message when the on-disk schema
  does not match the installed `sq`; the extension surfaces it and pins no schema knowledge.

**3. Testing and quality parity.** TypeScript is held to the same strict bar as the core: `tsc`
strict plus `noUncheckedIndexedAccess`, `noImplicitReturns`, `noImplicitOverride`,
`noFallthroughCasesInSwitch`, `noUnusedLocals`, `noUnusedParameters`,
`exactOptionalPropertyTypes` and `isolatedModules`; `typescript-eslint` strict-type-checked and
stylistic-type-checked with complexity ≤ 12 and max-params ≤ 8, zero warnings; Prettier `--check`.
`npm run check` mirrors the Python gate. Within TypeScript the gate is blocking for any change to
`clients/vscode/`; across languages it stays isolated.

Three test layers, all inside `clients/vscode/`:

- **Unit** — parse and adapt logic against committed fixture JSON captured from real `sq` output;
  runs with no `sq` binary.
- **Skew canary** — runs a real `sq` against a scratch squad to confirm the fixtures still match the
  live shapes; skippable when `sq` is absent.
- **Extension host** — a `@vscode/test-electron` smoke test that the trees load and a preview opens.

The dev-time CI workflow (`vscode-client.yml`) is path-filtered to `clients/vscode/**` and
independent of the Python jobs; cross-language coupling is caught by the skew canary.

**4. Packaging and distribution (one bundle).** A release ships core and client together: the
release pipeline packages the VSIX (`vsce package`), publishes it to the VS Code Marketplace when
the `VSCE_PAT` secret is configured, and attaches it to the tagged GitHub release either way.

**5. Versioning (unified).** The extension carries no independent version: its version is the
core's, bumped by the same release bump, and the pipeline refuses a tag that does not match the
core version. A release's client and CLI are always matched, so the only version question left is
bundle against on-disk schema, which the CLI's hard-stop guards.

## Consequences

- TS churn never reddens the Python gate, and the client can only break if the frozen surface
  breaks.
- The client is thin and mockable: nearly everything is unit-tested against captured fixtures.
- Write verbs from the editor, if added, are an additive layer over the same shell-out pattern and
  exit-code mapping. The extension is read-only, and its marketplace page says so.
- Cost: two dev-time CI lanes and a fixture-refresh discipline, with the skew canary catching drift.
- Dev-time gates are isolated; the release pipeline is unified. Isolation is about non-blocking
  iteration, unification about shipping a matched set.
- Bundling a `sq` binary inside the VSIX is out of scope: the extension discovers the workspace's
  `sq`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-16T13:45:21Z] `op-pierre` Pierre Chat:
  - sq discovery: auto-detect the workspace toolchain — .venv, uv (uv run sq), and poetry (poetry run sq) — in addition to a config override + PATH fallback. Don't ship PATH-only.
- [2026-07-16T13:45:22Z] `op-pierre` Pierre Chat:
  - Override decisions #4 (packaging) and #5 (versioning): releases are ONE bundle. The clients build and deploy together WITH the main software, at the SAME version — no independent extension semver. The release CI chain produces and ships the client alongside the core at the unified version.
- [2026-07-16T13:47:08Z] `architect` Robert Architect:
  - Revised per Pierre's two overrides: (1) #2 sq discovery now auto-detects the workspace toolchain (.venv / uv run / poetry run) + config override, PATH is only the last fallback; (2) rewrote #4/#5 to one release bundle — client built+shipped with the core at the unified version, VSIX as a release asset (no independent semver). Kept dev-time gate isolation (#1/#3) and made the dev-isolation vs release-unification distinction explicit. Marketplace/Open VSX publish remains the open item (credentials).
- [2026-07-16T13:48:12Z] `op-pierre` Pierre Chat:
  - 0.10 deploy = VSIX attached as a release asset only; marketplace/Open VSX publish deferred to a later step. No publisher account/CI secrets needed this release.
- [2026-07-16T13:48:13Z] `manager` Catherine Manager:
  - Accepted following Pierre's review and the recorded override decisions (unified bundle+version, sq auto-discovery, VSIX-as-asset). @tech-lead — ADR-427 constrains FEAT-100; ready to break the 3 stories into tasks under clients/vscode/.
- [2026-07-16T13:50:09Z] `op-pierre` Pierre Chat:
  - TypeScript must meet the SAME strict quality bar as the Python core — no laxer gate for the new language. Parity: tsc strict (+ noUncheckedIndexedAccess/noImplicitReturns/noUnusedLocals/exactOptionalPropertyTypes ≈ pyright strict), typescript-eslint strict-type-checked with complexity/max-params rules mirroring ruff (C901/PLR), Prettier --check (≈ ruff format), zero warnings. It's a hard must-pass gate FOR TS changes; cross-language isolation from the Python gate is unchanged (within-language strict, cross-language non-blocking).
- [2026-07-16T15:26:12Z] `architect` Robert Architect:
  - CLI readiness audit for FEAT-100 (ran the real commands; verdicts below). Bottom line: one HIGH gap blocks US2; US1/US3 + all cross-cutting checks are READY.
  - US1 tree — READY. sq tree --json carries id/type/status/priority/assignee/blocked/children and nests correctly (rooted + no-root; FEAT-100 sits under EPIC-99). --all reveals closed. Rough-edge (low): no-root forest mixes the 3 reserved meta types (role/skill/operator) with work items and there's no server-side 'work-items' filter nor a machine-readable type catalog (sq workflow --json doesn't exist); client excludes the 3 reserved types (-t is repeatable as an alternative). Not a blocker.
  - US2 preview — GAP, HIGH (blocks US2). No clean-markdown mode exists. sq show default AND --raw both emit a Rich box-drawing header panel (~180 box chars) + space-aligned summary table + '=== US ===' separators — terminal chrome, not markdown. sq show --json carries NO body/discussion (metadata + sub-entity state only); --full/--comments don't add prose to JSON. Reading .md is contract-forbidden. So item prose is unreachable as markdown via any sq surface. Fix: new 'sq show --format md' (H1 title + metadata block + body markdown verbatim; --comments/--full append discussion/sub-entities). Body is already stored as raw markdown between markers, metadata == show --json data → small, additive, reusable (sq web/MCP). Must be golden-frozen like the rest.
  - US3 filter/group/refresh — READY. sq list --json carries type+status (+priority/assignee/parent/labels); -t/-s filter, -a includes closed; refresh = re-invoke. Enough to group by type and open/closed.
  - Cross-cutting — all READY. FORCE_COLOR=3 clean (0 ESC bytes, valid JSON on tree/list/show --json — BUG-183 holds). Exit codes: 0 ok / 1 runtime / 2 usage / 3 check-errors (warnings-only=0), all confirmed empirically. Schema-skew HARD-STOPS reads with exit 1 + actionable stderr in BOTH directions (behind=migrate up, ahead=upgrade pkg) — this is the guard ADR-427 #2 relies on. sq --version works. stdout=data / stderr=errors cleanly separated (stdout empty on error).
  - CORRECTION to a pre-checked item: closed-root 'sq tree EPIC-12 --json' is exit **1** (stable over 3 runs), NOT 0 — stdout empty, stderr an actionable 'add --all' message. A machine consumer distinguishes it by exit code; the earlier exit-0 reading was almost certainly a pipeline's exit code, not sq's. Defensible per the contract; not a violation. (Minor asymmetry vs list's []-exit-0 on no-match; optional nicety, not a blocker.)
- [2026-07-16T15:36:39Z] `op-pierre` Pierre Chat:
  - US2 preview resolution — do NOT add a new --md flag. Instead fix the two existing surfaces: (1) sq show --raw must emit genuinely clean output (drop the Rich box-drawing header panel it still renders; it already advertises 'plain text' — make that true) — this becomes the markdown feed for the preview; (2) sq show --json must include the item BODY (and discussion) too, so the structured surface is complete rather than metadata-only. The extension's US2 preview reads sq show --raw. Both are surface changes to golden-freeze; assess back-compat of the --raw behavior change.
- [2026-07-16T15:38:49Z] `architect` Robert Architect:
  - US2 core-prerequisite surface spec (per Pierre: fix the two existing surfaces, NO new --md flag). For the tech lead to cut a core task from.
  - (A) sq show <id> --raw — new behavior: emit a deterministic, markdown-preview-clean dossier with ZERO Rich chrome (no box-drawing header panel, no space-aligned summary table, no '=== US … ===' separators). Structure: '# TYPE-N — <title>' (H1); then a metadata block as a bullet list of bold-key lines ('- **status:** …' for status/priority/assignee/parent/author/refs/labels, omitting absent fields — chosen over a md table: deterministic, no column-width ambiguity, clean omission); blank line; then the body markdown verbatim. --comments appends '## Discussion' with each comment as '### <author> — <ISO ts>' + its md. --full appends one '## <Kind> <local_id> — <title>' section per sub-entity (badge line + body md). Only --raw changes; default styled mode keeps its Rich rendering for terminal humans.
  - (B) sq show <id> --json — ADDITIVE superset (new keys only, nothing renamed/removed): add top-level 'body' (raw body markdown) and 'discussion' (ordered list of {author, ts, body}); add 'body' to each object in the existing 'subentities' array (currently state-only: assignee/extra/local_id/severity/status/story/title). Include these UNCONDITIONALLY — not gated by --comments/--full — to preserve the current invariant that 'show --json' is byte-identical across --raw/--comments/--full (test_json_output_is_byte_identical_regardless_of_raw_or_comments_flags).
  - (C) Back-compat of the --raw change: no current test/consumer asserts the box-panel chrome — the two --raw tests (test_show_command_renders_body_and_subentities, test_body_content_source_and_mutual_exclusion_cli) only assert body substrings ('## Section' passthrough), which the clean output preserves. --raw is human-facing plain text, OUTSIDE FEAT-15's frozen machine surface (that froze --json shapes + exit codes), so this is NOT a frozen-surface break — but it IS a user-visible formatting change that warrants a CHANGELOG note. The --json additions are additive, so they don't break the freeze either.
  - (D) Golden-freeze: --raw currently has NO golden — ADD new raw-text goldens (e.g. item_show_raw.txt covering an item with body + sub-entities + a comment, deterministic under frozen clock). The --json additions change bytes of the existing per-type goldens — UPDATE feature_show.json / task_show.json (+ any show --json golden that now carries body/discussion) in the same PR. Both surfaces then carry FEAT-15-style golden coverage.
- [2026-10-16T11:18:12Z] `architect` Robert Architect:
  - 2026-10-16: one dated note added in section 2 for ADR-1025 (consumers tolerate unknown open-set values); nothing else in the body changed.
- [2026-10-25T21:27:16Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the five decisions are unchanged. Marketplace publishing is no longer deferred: publish.yml runs vsce publish when VSCE_PAT is set and always attaches the VSIX. Replaced the three FEAT-100 surfaces with the read commands the client runs (sqAdapter.ts), noted it watches but never parses .squads.json, folded the dated ADR-1007 and ADR-1025 notes into §2, and removed the 0.10 framing, the prerequisite core task and the Deferred section.
<!-- sq:discussion:end -->
