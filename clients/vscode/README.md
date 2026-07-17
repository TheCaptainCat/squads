# squads VS Code extension

Browse a [squads](https://github.com/TheCaptainCat/squads)-managed project's work items from
VS Code. The extension is a pure consumer of the CLI's frozen `sq --json` surfaces: it never
reads `.claude/` or parses `.squads.json` directly, discovers `sq` by auto-detecting the
workspace toolchain (an explicit config override, then a workspace virtualenv, `uv`,
`poetry`, and finally bare PATH as a last resort), and maps every exit code the CLI documents.

This package is self-contained: its own `package.json`, `tsconfig.json`, ESLint/Prettier
config, and lockfile, entirely disjoint from the Python core's toolchain. Nothing under
`clients/` is read by the Python gate (`pyright`/`ruff`/`pytest`) and vice versa.

Current state: read-only browse. An activity-bar tree (`src/treeDataProvider.ts`) renders the
squad hierarchy from `sq tree --json`; selecting an item opens its `sq show --raw` dossier in a
read-only `squads:` markdown preview (`src/showDocumentProvider.ts`); view-title commands filter
and group the tree by type/open-closed state and refresh it on demand (`src/commands.ts`). The
`sq` discovery module (`src/discovery.ts`) and `sq --json`/`--raw` adapter (`src/sqAdapter.ts`)
underpin all three, tested against committed fixtures (`test/fixtures/`) with no `sq` binary
required — plus an integration skew-canary layer that re-checks those fixtures against a real
`sq` (see below). Mutating the squad from the editor is a later increment.

## Development

```bash
npm install
npm run check   # tsc --noEmit && eslint --max-warnings 0 && prettier --check
npm test        # vitest — unit layer, committed fixtures only, no sq binary needed
```

### Integration skew canary

`npm run test:canary` is a separate test layer (`test/canary/`, `vitest.canary.config.ts`):
it runs a **real `sq`** against a scratch squad and checks that the committed fixtures
(`test/fixtures/tree.json`, `list.json`, `show-raw.txt`) still match the live shape of
`sq tree --json`, `sq list --json`, and `sq show <id> --raw` — the guard against the core
surface drifting away from this client's fixtures. It needs a real `sq` resolvable on
`PATH` (e.g. `source ../../.venv/bin/activate` from the repo root, or otherwise put a
provisioned `sq` on `PATH`) and **skips cleanly** (not a failure) when one isn't found, so
`npm test` stays hermetic without it. CI provisions `sq` via `uv sync` for this lane (see
`.github/workflows/vscode-client.yml`).

```bash
npm run test:canary
```

### Extension-host smoke test

The third test layer this project's architecture calls for — a `@vscode/test-electron`
smoke test confirming the extension activates and its core contributions load in a real VS
Code host — lives under `test/extensionHost/` (`runTest.ts` launches a real Extension
Development Host; `suite/index.ts` asserts activation, the `squadsTree` view registering,
and opening an item preview via the `squads:` provider without throwing). It needs a
compiled `out/` build (`npm run test:e2e` compiles first) and a display — headless CI runs
it under Xvfb (see `.github/workflows/vscode-client.yml`); there's no display in a plain
dev shell, so run it on a desktop or rely on CI.

```bash
npm run test:e2e
```
