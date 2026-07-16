# squads VS Code extension

Browse a [squads](https://github.com/TheCaptainCat/squads)-managed project's work items from
VS Code. The extension is a pure consumer of the CLI's frozen `sq --json` surfaces: it never
reads `.claude/` or parses `.squads.json` directly, discovers `sq` by auto-detecting the
workspace toolchain (an explicit config override, then a workspace virtualenv, `uv`,
`poetry`, and finally bare PATH as a last resort), and maps every exit code the CLI documents.

This package is self-contained: its own `package.json`, `tsconfig.json`, ESLint/Prettier
config, and lockfile, entirely disjoint from the Python core's toolchain. Nothing under
`clients/` is read by the Python gate (`pyright`/`ruff`/`pytest`) and vice versa.

Current state: foundation only — the `sq` discovery module (`src/discovery.ts`) and the
`sq --json` adapter (`src/sqAdapter.ts`), tested against committed fixtures
(`test/fixtures/`) with no `sq` binary required. The activity-bar tree, item preview, and
filter/group commands land in later tasks on top of this foundation.

## Development

```bash
npm install
npm run check   # tsc --noEmit && eslint --max-warnings 0 && prettier --check
npm test        # vitest
```
