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
required. Mutating the squad from the editor is a later increment.

## Development

```bash
npm install
npm run check   # tsc --noEmit && eslint --max-warnings 0 && prettier --check
npm test        # vitest
```
