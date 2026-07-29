# squads VS Code extension

The VS Code client for a [squads](https://github.com/TheCaptainCat/squads)-managed project: a
read-only window onto the squad's work items, records and roster, backed entirely by the `sq` CLI.

**For what it does from a user's point of view**, see [MARKETPLACE.md](MARKETPLACE.md) — the
published listing, and the file to update when a user-visible feature changes. In one line: three
activity-bar trees (**Work Items**, **Records**, **Roster**), an owned webview panel rendering any
item's full dossier, full-text search, and auto-refresh driven by changes to the squad index on
disk.

The rest of this file is the map for working on it. The package is self-contained — its own
`package.json`, `tsconfig.json`, ESLint/Prettier config and lockfile, disjoint from the Python
core's toolchain; nothing under `clients/` is read by the Python gate, and vice versa.

## Layers

**Host layer** (`src/*.ts`) — everything allowed to import `vscode`:

| Module                                                                   | Responsibility                                                                                                       |
| ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| `extension.ts`                                                           | activation: builds the providers, registers commands, wires the watcher                                              |
| `treeDataProvider.ts`                                                    | the **Work Items** tree (hierarchy, or a flat filtered/grouped view)                                                 |
| `recordsTreeDataProvider.ts`                                             | the **Records** tree (one bucket per `records`-category type)                                                        |
| `metaTreeDataProvider.ts`                                                | the **Roster** tree (fixed Roles / Skills / Operators buckets)                                                       |
| `treeItemRendering.ts`                                                   | shared `DisplayNode` → `vscode.TreeItem` mapping (icons, colours, tooltips)                                          |
| `itemPreviewManager.ts`                                                  | the owned `WebviewPanel`s: item dossiers, per-panel back/forward history, and the separate workflow-cheatsheet panel |
| `searchQuickPick.ts`                                                     | the full-text search QuickPick over `sq search --json`                                                               |
| `commands.ts`, `commandIds.ts`                                           | command registration and the contributed command ids                                                                 |
| `squadWatcher.ts`                                                        | watches the squad index on disk and triggers one global refresh                                                      |
| `discovery.ts`, `processRunner.ts`, `sqAdapter.ts`, `nodeEnvironment.ts` | finding `sq`, invoking it, and parsing its `--json` / `--raw` output                                                 |

**Domain layer** (`src/domain/*.ts`) — pure, `vscode`-free, unit-tested directly with no host:

- **view building** — `listView`, `metaView`, `recordsView`, `treeMapping`, `displayNode`,
  `expansionTracker`, `refreshAll`
- **preview assembly** — `previewDocument`, `markdown`, `graphDiagrams`, `previewHistory`,
  `previewMessages`
- **spec-driven vocabulary** — `typeCategory`, `typeLabels`, `typeOrder`, `statusRole`,
  `badgeCatalog`, `reservedTypes`, `roleDirectory`
- **search** — `searchRunner`, `searchResults`, `searchFilterArgs`, `searchAccept`
- **misc** — `squadDir` (client-side `.squads.toml` walk-up), `idOrder`

## Conventions to preserve

1. **`src/domain/` never imports `vscode`.** That constraint is what makes the logic unit-testable
   without an extension host; anything needing the API belongs in the host layer, kept thin enough
   to be covered by the smoke test instead.
2. **Pure consumer of the CLI.** Data comes from `sq … --json` / `--raw` and nothing else: never
   read `.claude/`, and never parse the squad index for content — the watcher treats it as a change
   _trigger_ only, then re-fetches through the normal adapter calls.
3. **Read-only.** Contribute no command that mutates a squad.
4. **Spec-driven, not hardcoded.** Item types, statuses, labels, ordering and badges come from the
   workflow catalogs, so a project with custom types works with no client change. Degrade
   gracefully when a catalog is unavailable — fall back to prior behaviour rather than dropping
   items.
5. **Strict CSP, no remote content.** Webview HTML carries a per-render nonce for both its
   `<style>` and `<script>`; mermaid is vendored locally (`media/mermaid.min.js`, copied by
   `scripts/copy-mermaid.js` during `npm run compile`). Never introduce a CDN load.
6. **No squad-item ids in source, config, or this file.** `test/hygiene.test.ts` enforces it,
   mirroring the Python core's own gate, which does not reach into `clients/`.
7. **TypeScript stays on 6.0.x.** The type-aware lint layer peer-caps below 6.1; the pin lifts when
   that does, and not by dropping the type-aware gate.

## Development

```bash
npm install
npm run check   # tsc --noEmit && eslint --max-warnings 0 && prettier --check
npm test        # vitest — unit layer, committed fixtures only, no sq binary needed
```

### Running it in a dev host

Anything visual has to be seen in a real Extension Development Host, not inferred from tests:

```bash
npm run compile                     # vendors mermaid, emits out/
code --extensionDevelopmentPath=.
```

The entry point is `out/src/extension.js`, so compile before launching or the host loads a stale
build. Open a squads-managed folder in the new window to exercise the views.

**On WSL, launch the dev host as a WSL remote and leave `--disable-extensions` off.** The flag is the
documented way to isolate a dev host from your installed extensions, but it also disables Remote-WSL:
the host then runs on Windows over the UNC share, where a Linux `sq` in `.venv/bin` cannot execute, so
you get a discovery error instead of a working extension. Elsewhere, add the flag if a local
extension is interfering. Either way the visual check belongs on the desktop — a poorly rendering
host misleads more than it shows.

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
