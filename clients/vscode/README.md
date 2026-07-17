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
squad hierarchy from `sq tree --json`; selecting an item opens its `sq show --raw` dossier,
rendered to HTML, in an owned `WebviewPanel` (`src/itemPreviewManager.ts`) — a dedicated tab
that's never hijacked by opening another markdown file, unlike VS Code's built-in dynamic
preview. Parent/ref item ids in the dossier render as navigable links: a click opens that item
in the same panel, a middle-click (or ctrl/cmd-click) opens it in a new one — the webview
posts a message back to the extension host, which routes it (`src/domain/previewMessages.ts`)
and re-renders. Below the dossier, two independently collapsible mermaid diagrams
(`src/domain/graphDiagrams.ts`) render the item's children/subtree (`sq tree <id> --json`) and
its ref graph (`sq graph <id> --json`); the mermaid renderer is bundled as a local webview
asset (`media/mermaid.min.js`, vendored by `npm run compile` — see `scripts/copy-mermaid.js`),
loaded through the same strict CSP, no CDN. The markdown -> HTML rendering
(`src/domain/markdown.ts`) and the panel's HTML document (`src/domain/previewDocument.ts`,
strict per-render-nonce CSP, no remote content) are vscode-free and unit-tested directly.
View-title commands filter and group the tree by type/open-closed state and refresh it on
demand (`src/commands.ts`). The `sq` discovery module (`src/discovery.ts`) and
`sq --json`/`--raw` adapter (`src/sqAdapter.ts`) underpin all of this, tested against
committed fixtures (`test/fixtures/`) with no `sq` binary required — plus an integration
skew-canary layer that re-checks those fixtures against a real `sq` (see below). Mutating the
squad from the editor is a later increment.

## Development

```bash
npm install
npm run check   # tsc --noEmit && eslint --max-warnings 0 && prettier --check
npm test        # vitest — unit layer, committed fixtures only, no sq binary needed
```

### Integration skew canary

`npm run test:canary` is a separate test layer (`test/canary/`, `vitest.canary.config.ts`):
it runs a **real `sq`** against a scratch squad and checks that the committed fixtures
(`test/fixtures/tree.json`, `graph.json`, `list.json`, `show-raw.txt`) still match the live
shape of `sq tree --json`, `sq graph --json`, `sq list --json`, and `sq show <id> --raw` — the
guard against the core surface drifting away from this client's fixtures. It needs a real `sq`
resolvable on
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
and opening an item's owned preview webview without throwing). It needs a
compiled `out/` build (`npm run test:e2e` compiles first) and a display — headless CI runs
it under Xvfb (see `.github/workflows/vscode-client.yml`); there's no display in a plain
dev shell, so run it on a desktop or rely on CI.

```bash
npm run test:e2e
```
