# Contributing to squads

Thanks for hacking on squads! This is a Python 3.14 / `uv` project. `CLAUDE.md` is the terse
working-reference; this file is the friendly version. Deeper design lives in
[docs/internals.md](docs/internals.md).

## Setup

```bash
uv sync                 # install deps + the `sq` entry point into the project venv
uv run sq --help        # exercise the CLI
uv run pytest           # the test suite (fast; everything runs in tmp dirs)
```

## The gate (must stay green)

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright            # strict mode
uv run pytest
```

Ruff runs an expanded ruleset (`E F I UP B W` + `C901 SIM PERF PTH RUF TRY PLR0911/12/13/15`,
`max-complexity 12`, `max-args 8`, `TRY003` ignored). Pyright is **strict**. CI (`.github/workflows`)
runs all four on pushes/PRs to `main`.

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
- **Comments stay terse.** Default to no comment; keep a single short line only where something is
  genuinely non-obvious (a gotcha, an invariant, a "this looks wrong but…"). No ticket/ADR IDs in
  code or config comments — the linkage lives in the tracked item, not the source.

## How to add things

- **A template** → drop a `.j2` under `squads/_rendering/templates/`; it ships in the wheel as
  package data automatically. Render with `squads._rendering._engine.render` (StrictUndefined).
- **A command** → add it to the right `squads/_cli/_*` module (or a new one), wire it onto `app`
  in `_cli/__init__`, and route logic through `Service`.
- **An item type** → add to `ItemType` (`_models/_enums`) with its prefix + folder, give it a
  workflow in `_workflow`, an item template, and (if agents author it) a `PLAYBOOK` entry in
  `_interactions`.
- **A backend** → see [docs/backends.md](docs/backends.md).

## Tests

`pytest` with `typer.testing.CliRunner`. The `project`/`svc` fixtures (`tests/conftest.py`) init a
squad in a `tmp_path` and `chdir` into it — **all file generation stays in temp**. Cover behaviour
through the service/CLI and assert on the generated files (valid frontmatter, intact markers,
preserved body). When you add a feature, add a service-level test and a CLI smoke test. Time is
frozen via the `frozen_time` fixture; the `_reset_clock_override` autouse fixture stops a forged
`--at` from leaking between tests.

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
