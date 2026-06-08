# CLAUDE.md — working on the squads codebase

`squads` (`sq`) is a Python/uv Typer CLI that manages a team of AI agents on a code project:
it bootstraps roles/skills and tracks work as identified markdown with a JIRA-like ID system.
Claude Code is the first pluggable backend. This file guides work **on squads itself**.

## Commands

```bash
uv sync                 # install deps + the sq entry point
uv run pytest           # full suite (fast, all in tmp dirs)
uv run sq <cmd>         # exercise the CLI
uv build                # wheel/sdist (templates ship as package data)
```

## Architecture & layering

```
cli → service → (index store, backends, rendering)
models  shared, no internal deps
```

- `models/` — pydantic v2. `Item`, `SquadsDB` (the index), `enums` (`ItemType`/`Status` + the
  prefix→folder maps), `markers` (sq anchor tags), `config` (`.squads.toml`).
- `paths.py` — resolve the active squad folder (`--dir` > `.squads.toml` walk-up > default) and map
  an ID/type to its on-disk location.
- `index/store.py` — the integrity core: filelock'd, atomic (`os.replace`) read-modify-write of
  `<squad-dir>/.squads.json`; `allocate_id` bumps the **single global counter**.
- `sections.py` / `itemfile.py` — marker-safe edits and frontmatter↔Item mapping.
- `workflow.py` — per-type status machines + `can_transition` + `TERMINAL`/`is_open`.
- `rendering/` — Jinja2 (`StrictUndefined`); templates are package data under `templates/`.
- `backends/` — `AgentBackend` ABC + registry; `claude_code/` writes pointer files, the managed
  `squads` skill, and the CLAUDE.md managed section.
- `roles/catalog.py` — the 8 bundled roles + dev name pool + `dev_role()`.
- `interactions.py` — the team **playbook**: which roles interact with each item type (the `*dev`
  sentinel = any `<tech>-dev` role). Drives the per-item-type managed skills (`sq-<type>`, one
  role-directed section each) and `skills_for_role()` (which skills a role's pointer preloads). A
  role that doesn't manage a type gets no skill for it. Workflow cheatsheet partial:
  `rendering/templates/workflow.md.j2` (shared by the `squads` skill and `sq workflow`).
- `service.py` — orchestration; the logic behind each command. `discussion.py` — comment/story/
  subtask formatting + `@mention` extraction.
- `cli/` — Typer app (`__init__` wires sub-typers + the `--dir` callback + version notice);
  one module per command group; `common.py` has the shared console/error decorator/parsers.

## Invariants — keep these true

1. **Frontmatter is the source of truth.** `.squads.json` is a rebuildable index; never store
   anything in it that can't be reconstructed from the `.md` files (`sq repair` proves this).
2. **Global counter.** One monotonic counter for all types; an ID's number is globally unique.
   Allocate only inside `IndexStore.transaction()`.
3. **Marker-safe edits only.** Touch file content solely via `sections.py`; never rewrite an
   agent-authored body. Markers are `<!-- sq:<tag> -->` / `<!-- sq:<tag>:end -->`.
4. **Forward edges only.** `item.refs` holds outgoing refs; backrefs are computed by inversion
   (`SquadsDB.backrefs`), never persisted.
5. **`.claude/` files are pointers**, not content. Real definitions live under `squads/`.
6. **Backends are pluggable.** Don't reach into `.claude/` outside a backend; go through the ABC.

## Conventions / gotchas

- **Escape dynamic output.** Rich treats `[...]` (e.g. a `[x]` checkbox) as markup — always wrap
  user/content strings with `cli.common.e()` when printing to the console or a table.
- **Time is injectable.** Use `clock.now()` / `clock.iso()` so tests can freeze it
  (`frozen_time` fixture); never call `datetime.now()` directly.
- **Marker regex is strict.** `sections.find_markers` only matches well-formed tags so prose like
  `` `<!-- sq:* -->` `` in role files isn't linted as a real marker.
- **User-facing errors** subclass `SquadsError`; the CLI's `@handle_errors` turns them into a clean
  message + exit 1. Raise those, not bare exceptions.
- **Templates are package data** — adding one means dropping a `.j2` under `rendering/templates/`;
  the wheel includes them automatically (verified in build).
- **No `from __future__ import annotations`** — we target Python 3.14 (PEP 649 lazy annotations),
  so forward refs work unquoted. Keep the import graph **acyclic** (verified); if a future edge
  would create a cycle, use `if TYPE_CHECKING:` + a string annotation rather than a runtime import.
- **Strict typing** — `pyright` runs in strict mode and `ruff` (E/F/I/UP/B/W) must stay clean:
  `uv run pyright && uv run ruff check . && uv run ruff format --check .`. Annotate bare `dict`/
  `list` (e.g. `dict[str, Any]`); Typer's `Option/Argument` call-defaults are why `B008` is
  ignored under `cli/`.

## Testing

`pytest` with `typer.testing.CliRunner`; the `project`/`svc` fixtures (`tests/conftest.py`) init a
squad in a `tmp_path` and `chdir` into it — **all file generation stays in temp**. Cover behaviour
through the service/CLI, and assert generated files (valid YAML frontmatter, intact markers,
preserved body). When adding a feature, add a service-level test and a CLI smoke test.

## Status

All three planned phases are built and green. The only explicitly-deferred feature is
project-level template/role overrides (e.g. `squads/.templates/`). The full design lives in the
approved plan referenced from the project memory.
