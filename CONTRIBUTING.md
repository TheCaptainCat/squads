# Contributing to squads

Thanks for hacking on squads! `CLAUDE.md` is the terse working-reference; this file is the friendly
version. Deeper design lives in [docs/internals.md](docs/internals.md).

The repo holds **two independent toolchains**:

- the **Python core** — the `sq` CLI, Python 3.14 / `uv`, at the repo root;
- the **VS Code client** — TypeScript under `clients/vscode/`, with its own `package.json`,
  lockfile and lint config.

Neither reads the other's files, and each has its own gate. Work on the client starts at
[clients/vscode/README.md](clients/vscode/README.md), which maps that package and the conventions
specific to it; the sections below are the core unless they say otherwise.

## Setup

```bash
uv sync                 # install deps + the `sq` entry point into the project venv
uv run sq --help        # exercise the CLI
uv run pytest           # the test suite (fast; everything runs in tmp dirs)
```

## The gate (must stay green)

```bash
uv run --all-extras ruff check .
uv run --all-extras ruff format --check .
uv run --all-extras pyright            # strict mode
uv run --all-extras pytest
```

**Pass `--all-extras` on every one of them.** A bare `uv run` prunes the optional `tui` extra
(`textual`), after which `pyright` reports hundreds of phantom unresolved-import errors from
`_tui/` and the terminal-UI tests break — a confusing failure that has nothing to do with your
change.

Ruff runs an expanded ruleset (`E F I UP B W` + `C901 SIM PERF PTH RUF TRY PLR0911/12/13/15`,
`max-complexity 12`, `max-args 8`, `TRY003` ignored). Pyright is **strict**. CI (`.github/workflows`)
runs all four on pushes/PRs to `main`.

`sq check` — the tool's own linter, run against this repo's own squad — must also be clean for
whatever you touched. It is advisory for people *using* squads; here it is part of the gate.

### The VS Code client's gate

From `clients/vscode/`:

```bash
npm install
npm run check          # tsc --noEmit + eslint (zero warnings) + prettier --check
npm test               # vitest: unit layer, committed fixtures, no sq binary needed
npm run test:canary    # fixtures vs a real sq; skips cleanly when sq isn't on PATH
npm run test:e2e       # extension-host smoke test; needs a compiled build and a display
```

`npm run check` and `npm test` are the two that must be green for every client change. The canary
and the host smoke test are documented in that package's README along with how to run a dev host.

### Guard tests (`tests/meta/`)

Beyond the unit suite, a small set of repo-hygiene tests fail on things a reviewer would otherwise
have to catch by eye: a tracked-item id appearing in source or config, new module-level mutable
state, a documented CLI command that no longer resolves, a stale override manifest or template
stamp. If one of them fails, read its docstring — each explains the rule it enforces and the
sanctioned way to satisfy it.

## Conventions

- **Private layout.** Every module and subpackage is underscore-prefixed
  (`squads._service`, `squads._models._item`, …) and package `__init__`s don't re-export — import
  straight from the underscore modules. (`squads/__init__` keeps `__version__`; `_cli/__init__` the
  Typer `app`; `_backends/_claude_code/__init__` the registration side-effect.)
- **Frontmatter is the source of truth.** `.squads.json` is a rebuildable index — never store
  anything in it that can't be reconstructed from the `.md` files (`sq repair` proves it).
- **Marker-safe edits only** — touch file content via `squads._sections`; never rewrite an agent's
  body. Markers are `<!-- sq:<tag> -->` / `<!-- sq:<tag>:end -->`.
- **Forward edges only** — `item.refs`; backrefs are computed by inversion, never persisted.
- **`.claude/` is pointers + tool config**; real content lives under the squad folder.
- **Time is injectable** — use `_clock.now()` / `_clock.iso()`, never `datetime.now()`.
- **`Item.extra` keys** come from `squads._models._extras.ExtraKey` — don't hand-write the literals.
- **Escape dynamic console output** with `_cli._common.e()` (Rich treats `[...]` as markup).
- **No `from __future__ import annotations`** (Python 3.14 / PEP 649); keep the import graph
  **acyclic** — if a future edge would create a cycle, use `if TYPE_CHECKING:` + a string annotation.
- **Type aliases use the PEP-695 `type` statement** (`type X = …`), not bare assignment.
- **Comments stay terse.** Default to no comment; keep a single short line only where something is
  genuinely non-obvious (a gotcha, an invariant, a "this looks wrong but…"). No ticket/ADR IDs in
  code or config comments — the linkage lives in the tracked item, not the source.
- **No "meta" for the roster-type concept.** Say "roster" / "roster category" / "roster type"
  (role/skill/operator), never "meta-type(s)". The legacy body-stored sub-entity `:meta` marker
  region is an unrelated, still-current concept — that one keeps its name.

## Writing `--help` text

A command function's docstring is its `--help` screen, and every `help=` string is a line in its
options panel. That text is documentation for someone who has the tool and not this repository,
about to type the command. It answers three questions, in this order: what does this do, what do I
type, and what do I get back or lose. A sentence that answers none of them belongs somewhere else.

| Content | Home |
|---|---|
| What it does, what to type, what comes back or is lost | help |
| Why the code is built this way | a comment at that code, or the helper's or module's docstring |
| Field lists, exit-code mechanics, anything a script depends on | `docs/`, pointed at from help |

The rules, one per part of the screen:

1. **Summary.** The first paragraph is one sentence on one source line, 72 characters or fewer,
   verb first, saying what the reader gets. A parent's Commands table prints it alone, so it names
   no mechanism, holds no parenthesis and makes no comparison with a sibling.
2. **Body.** Optional; most commands need none. A sentence earns its place if a reader would type
   something different, or read the output differently, for having read it: a default that
   surprises, what is written or destroyed and whether it can be undone, when the command refuses
   and the way out, the one sibling it gets confused with, one example where the shape of the
   invocation is not obvious. The first three lines after the summary answer the commonest
   question. Count a body's source lines after the summary paragraph and before any form feed,
   leaving blank lines out: past 10, the body needs a reason a reviewer accepts, and "it has
   nowhere else to live" is not one.
3. **Never in help.** Why the implementation is built as it is, a defence of the design, the name
   of a function, class, module, package path or internal type, history ("legacy", "the old",
   "today there is no"), or an invariant the reader cannot observe. Put it in a comment or the
   helper's docstring. A note that must stay in the command function's own docstring goes after a
   form feed (`\f`), which Typer does not render.
4. **Options and arguments.** Every one has a description: one line saying what the value is and
   what it does here, with where the legal values come from (`see sq workflow statuses`) or their
   format (`CODE=VALUE`). It never restates the default or the required marker the panel prints.
   A flag is described once, in its `help=`; the body adds only how flags combine. A flag with the
   same meaning on several commands has the same words everywhere, from one shared definition.
5. **`--json`.** Described on every command that takes it, in one line naming the top-level shape
   (an array with one object per row, or one object).
6. **JSON fields.** The field reference lives in `docs/stability.md`. Help keeps the `--json`
   line, any sentence a caller needs in order not to misuse the payload, and the pointer
   `Fields: sq docs stability`.
7. **Exit codes.** A command with no code of its own says nothing about exit codes. A command with
   one says one line, `Exit codes: 3 error-level issues found. See sq docs faq.`, and the
   mechanics stay in the docs. The one exception, kept to two lines: a code that is non-zero
   although the work was applied.
8. **Markup.** Plain text, single backticks around anything typed literally. No doubled backticks,
   asterisks, `::` line endings or cross-reference roles. Angle brackets for a placeholder, a bar
   between alternatives. Help renders through Rich console markup, so a square-bracketed span
   starting with a lowercase letter, `#`, `/` or `@` is read as a tag and silently vanishes.
9. **Layout.** Wrap body paragraphs at 78 columns after dedent. Text that depends on its line
   structure, such as a block of examples, goes in a no-rewrap block (a `\b` line before it) and
   stays under 78 columns. No unbreakable enumeration longer than the description column.

**Reviewing a help change.** Render the command at 80 columns (`COLUMNS=80 sq <command> --help`)
and read the screen, not the diff. Does the first screen answer the three questions? Is any name
on it something an adopter cannot type or open? Is every cell of the options panel filled?

## How to add things

- **A template** → drop a `.j2` under `squads/_rendering/templates/`; it ships in the wheel as
  package data automatically. Render with `squads._rendering._engine.render` (StrictUndefined).
- **A command** → add it to the right `squads/_cli/_*` module (or a new one), wire it onto `app`
  in `_cli/__init__`, and route logic through `Service`. Write its help to
  [Writing `--help` text](#writing---help-text).
- **An item type** → declare it in the bundled workflow spec (`squads/_specs/workflow.toml`):
  prefix, folder, category, lifecycle, and any parent/ref rules. Add its item template, and — if
  agents author it — a `[types.<name>]` entry in `squads/_specs/playbook.toml` so the type gets its
  managed `sq-<type>` skill. Both TOMLs are golden-locked by a test under `tests/unit/`; update the
  golden in the same change. (A *project* adds its own types through `.overrides/workflow.toml`
  instead — see [docs/overrides.md](docs/overrides.md) — and needs no code change at all.)
- **A backend** → see [docs/backends.md](docs/backends.md).

## Tests

`pytest` with `typer.testing.CliRunner`. The `project`/`svc` fixtures (`tests/conftest.py`) init a
squad in a `tmp_path` and `chdir` into it — **all file generation stays in temp**. Cover behaviour
through the service/CLI and assert on the generated files (valid frontmatter, intact markers,
preserved body). When you add a feature, add a service-level test and a CLI smoke test. Time is
frozen via the `frozen_time` fixture; the `_reset_clock_override` autouse fixture stops a forged
`--at` from leaking between tests.

The suite is laid out by kind — `tests/unit/`, `tests/service/`, `tests/cli/`, `tests/integration/`,
`tests/tui/`, plus the `tests/meta/` guards above; [tests/CONVENTIONS.md](tests/CONVENTIONS.md) sets
out how tests are named and where a new one belongs. It runs under `pytest-xdist` by default, which
is safe because every test owns its own `tmp_path`; pass `-n0` to force serial (for `--pdb`, say).
The scale-bound tests marked `slow` are skipped unless you pass `--run-slow`, so a bare run stays
quick. Redirect a full run to a file and read the file rather than re-running the suite to see a
different slice of its output.

## Commits / PRs

Keep the gate green. PRs target `main` and run the `test` workflow. Releases are tagged `v*`, which
triggers `publish.yml` (PyPI trusted publishing). Bump `__version__` (in `squads/__init__.py` and
`pyproject.toml`) and add a [CHANGELOG.md](CHANGELOG.md) entry when behaviour or the managed
templates change — a version bump is also what nudges existing squads to `sq sync`.

## Cutting a release

1. Bump `__version__` in `src/squads/__init__.py` and `pyproject.toml` to the new version.
2. Add a `CHANGELOG.md` entry.
3. Regenerate the template manifest (required whenever bundled templates change, harmless otherwise):

   ```bash
   python scripts/gen_template_manifest.py
   ```

   This updates `src/squads/_rendering/templates_manifest.json`.  Commit the result alongside
   any template changes.  The manifest ships automatically as package data — `uv build` picks it
   up from the same directory.

4. Commit, tag `v<version>`, and push.  The `publish` workflow runs `python
   scripts/gen_template_manifest.py` (write mode) then `uv build` then `uv publish`.

**Verification (optional local check):**

```bash
python scripts/gen_template_manifest.py --check   # exits 0 if manifest is current, 1 if stale
uv build
python -c "import zipfile, glob; z=zipfile.ZipFile(glob.glob('dist/*.whl')[0]); print([n for n in z.namelist() if 'templates_manifest' in n])"
```

The `test` CI also runs `python scripts/gen_template_manifest.py --check` as a named lint step, so
a stale-manifest PR is caught before it reaches the release tag.
