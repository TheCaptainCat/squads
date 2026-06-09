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
_cli → _services → (index store, backends, rendering)
_models  shared, no internal deps
```

**Module privacy convention.** Every implementation module and subpackage is **private** —
leading-underscore names (`_service.py`, `_models/`, `_backends/_claude_code/`, …). Package
`__init__.py` files do **not** re-export (this is a CLI, not yet a library API), so internal code
imports straight from the underscore modules (`from squads._models._item import Item`). The only
non-empty inits are `squads/__init__` (`__version__`), `_cli/__init__` (the Typer `app`, the entry
point `squads._cli:app`), and `_backends/_claude_code/__init__` (backend registration side-effect).
Namespace-style imports use an alias to keep call sites readable: `from squads import _clock as clock`.

- `_models/` — pydantic v2. `_item` (`Item`), `_subentity` (`SubEntity` — a story/subtask/finding's
  state, carried on `Item.subentities`), `_index` (`SquadsDB`), `_enums` (`ItemType`/`Status`
  + prefix→folder maps), `_markers` (sq anchor tags), `_config` (`.squads.toml`), `_extras`
  (`ExtraKey`).
- `_paths.py` — resolve the active squad folder (`--dir` > `.squads.toml` walk-up > default), map an
  ID/type to its location, and guard `abspath` against path traversal.
- `_index/_store.py` — the integrity core: filelock'd, atomic (`os.replace`) read-modify-write of
  `<squad-dir>/.squads.json`; `allocate_id` bumps the **single global counter**; `load` wraps a
  corrupt index in `SquadsError`. `SquadsDB.items` is keyed by the item's **int sequence number**
  (`Item.sequence_id`, a stored field; the formatted `id` is a `@computed_field` from `type` +
  `sequence_id`). Both `id` and `sequence_id` are persisted in `.md` frontmatter; `get`/`add`
  accept/use the formatted id transparently, and a `model_validator` normalizes legacy full-id keys.
- `_sections.py` / `_itemfile.py` — marker-safe edits and frontmatter↔Item mapping.
- `_workflow.py` — per-type status machines + `can_transition` + `TERMINAL`/`is_open` +
  `ALLOWED_PARENTS`/`parent_allowed`/`parent_hint`.
- `_rendering/` — Jinja2 (`StrictUndefined`); templates are package data under `_rendering/templates/`.
  `_engine.py` registers `slugify` + `open_marker`/`close_marker` filters. Item files render from
  `templates/items/*.md.j2`; **sub-entity blocks + their roll-up table** render from
  `templates/subentities/{block,summary}.md.j2` (driven by `_discussion.build_block`/`render_summary`).
  **Sub-entity state (status/assignee/severity/story) lives in the parent's frontmatter**
  (`Item.subentities`, typed `SubEntity`), not the body — the block only holds prose (`:body`,
  `:discussion`) plus a derived `:head` badge line (human-readable status/severity/assignee-name/story)
  rendered from `subentities/head.md.j2` via `_discussion.set_head` (badges from
  `STATUS_EMOJI`/`SEVERITY_EMOJI`); the service's `_refresh_head` resolves names/titles from the model
  and re-renders the head + summary on every mutation. Extend the head with more `{% if %}` lines. The
  legacy body-stored `:meta` regions survive only in `_migrations/_meta_compat.py`, used by the
  migrations.
- `_backends/` — `AgentBackend` ABC + registry; `_claude_code/` writes pointer files, managed skills
  (real body under `<squad>/agents/skills/`, thin pointer in `.claude/`), and the CLAUDE.md section.
- `_roles/_catalog.py` — the 8 bundled roles + dev name pool + `dev_role()`.
- `_interactions.py` — the team **playbook**: which roles interact with each item type (`*dev`
  sentinel = any `<tech>-dev` role). Drives the per-item-type managed skills (`sq-<type>`) and
  `skills_for_role()`. Workflow cheatsheet partial: `_rendering/templates/workflow.md.j2` (shared by
  the `squads` skill and `sq workflow`).
- `_services/` — orchestration, the logic behind each command. A shared `_base.ServiceCore`
  (create/get/list + backend + role/skill lookups + roster) plus one concern **mixin** per file
  (`_items`, `_collab`, `_subentities`, `_refs`, `_roster`, `_maintenance`); `_service.py` composes
  them into the flat `Service` façade and holds `init`/`adopt`/`open_service`; `_results.py` has the
  result dataclasses. `_discussion.py` — comment/story/
  subtask formatting + `@mention` extraction.
- `_cli/` — Typer app (`__init__` wires sub-typers + the `--dir` callback + version notice);
  one `_module` per command group; `_common.py` has the shared console/error decorator/parsers.

## Invariants — keep these true

1. **Frontmatter is the source of truth.** `.squads.json` is a rebuildable index; never store
   anything in it that can't be reconstructed from the `.md` files (`sq repair` proves this). This
   includes **sub-entity state** (`Item.subentities`): status/assignee/severity/story live in the
   frontmatter, only prose stays in the body markers.
2. **Global counter.** One monotonic counter for all types; an ID's number is globally unique.
   Allocate only inside `IndexStore.transaction()`.
3. **Marker-safe edits only.** Touch file content solely via `_sections.py`; never rewrite an
   agent-authored body. Markers are `<!-- sq:<tag> -->` / `<!-- sq:<tag>:end -->`.
4. **Forward edges only.** `item.refs` holds outgoing refs; backrefs are computed by inversion
   (`SquadsDB.backrefs`), never persisted.
5. **`.claude/` files are pointers**, not content. Real definitions live under `squads/`.
6. **Backends are pluggable.** Don't reach into `.claude/` outside a backend; go through the ABC.

## Conventions / gotchas

- **Escape dynamic output.** Rich treats `[...]` (e.g. a `[x]` checkbox) as markup — always wrap
  user/content strings with `_cli._common.e()` when printing to the console or a table.
- **Time is injectable.** Use `clock.now()` / `clock.iso()` so tests can freeze it
  (`frozen_time` fixture); never call `datetime.now()` directly.
- **Marker regex is strict.** `_sections.find_markers` only matches well-formed tags so prose like
  `` `<!-- sq:* -->` `` in role files isn't linted as a real marker.
- **User-facing errors** subclass `SquadsError`; the CLI's `@handle_errors` turns them into a clean
  message + exit 1. Raise those, not bare exceptions.
- **Templates are package data** — adding one means dropping a `.j2` under `_rendering/templates/`;
  the wheel includes them automatically (verified in build).
- **No `from __future__ import annotations`** — we target Python 3.14 (PEP 649 lazy annotations),
  so forward refs work unquoted. Keep the import graph **acyclic** (verified); if a future edge
  would create a cycle, use `if TYPE_CHECKING:` + a string annotation rather than a runtime import.
- **`Item.extra` keys** come from `_models/_extras.py::ExtraKey` (imported as `X`) — never hand-write
  the string keys; that's where role/dev/skill metadata field names live.
- **Refs carry their kind inline** (`schema_version` 0.2): `item.refs` entries are `"ID"` or
  `"ID:kind"`; use `split_ref`/`make_ref` from `_models/_item.py`, never parse the `:` by hand. The
  pre-0.2 `extra.ref_kinds` map is read transparently and folded by `from_frontmatter`.
- **Schema version & migrations.** `_models/_schema.py::SCHEMA_VERSION` is the single source of
  truth (models default to it). While alpha it's a **dotted string tracking the release that
  introduced the schema** (`"0.1"`, `"0.2"`), not an integer counter — compare with `schema_tuple`,
  never `<`/`>` on the raw string. The root CLI callback hard-stops on a mismatch (`require_current_schema` →
  run `sq migrate up`). The `sq migrate` Typer app (`_cli/_migrate.py`): `up` runs the ordered
  `_migrations/_registry.py::MIGRATIONS` (each a `Migration` record with a private
  `_vN_M_to_vP_Q.py` `migrate(paths)->int` + a `manual` runbook string) then `repair` + stamps;
  `help` lists the changelog index; `chlog vA..vB` prints `manual` steps for a release range.
  Runner modules are **private** — never `python -m`; only through `sq migrate`.
- **Strict typing** — `pyright` runs in strict mode and `ruff` (E/F/I/UP/B/W + C901/SIM/PERF/PTH/RUF/TRY/PLR0911-15,
  max-complexity 12, max-args 8, TRY003 ignored) must stay clean:
  `uv run pyright && uv run ruff check . && uv run ruff format --check .`. Annotate bare `dict`/
  `list` (e.g. `dict[str, Any]`); Typer's `Option/Argument` call-defaults are why `B008` is
  ignored under `_cli/`.

## Testing

`pytest` with `typer.testing.CliRunner`; the `project`/`svc` fixtures (`tests/conftest.py`) init a
squad in a `tmp_path` and `chdir` into it — **all file generation stays in temp**. Cover behaviour
through the service/CLI, and assert generated files (valid YAML frontmatter, intact markers,
preserved body). When adding a feature, add a service-level test and a CLI smoke test.

## Status

All three planned phases are built and green. The only explicitly-deferred feature is
project-level template/role overrides (e.g. `squads/.templates/`). The full design lives in the
approved plan referenced from the project memory.
