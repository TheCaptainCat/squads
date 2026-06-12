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

<!-- squads:start -->
This project is managed by **squads** — the coordination layer for the team of named AI agents
that works on this code. It gives the team a shared structure: a stable ID for every piece of work,
defined roles and skills, a status lifecycle, and a handoff protocol (comments, `@mentions`, an
inbox), so work moves cleanly from one agent to the next. Work is tracked as identified markdown
under `squads/` and indexed in `squads/.squads.json` — the team's source of
truth. See the `squads` skill for the `sq` CLI.

## Agent roster

- **Catherine Manager** — manager (`manager`)
- **Robert Architect** — architect (`architect`)
- **Olivia Lead** — tech lead (`tech-lead`)
- **Paul Reviewer** — code reviewer (`reviewer`)
- **Mara Tester** — QA engineer (`qa`)
- **Hugo Ops** — DevOps engineer (`devops`)
- **Nina Product** — product owner (`product-owner`)
- **Theo Writer** — technical writer (`tech-writer`)
- **Elias Python** — Python developer (`python-dev`)

## Operators (people)

Operators are the **humans** who work on this project — they can author items and review points, and
be assigned work (including manual steps). They are *not* agents: never spawn them, and address them
by their `op-` slug.
- **Pierre Chat** (`op-pierre`)

**When a human opens a conversation with you, greet them first** — follow the **`greeting`** skill:
detect who they are (your logged-in Claude user, or `git config user.name` → `op-<firstname>`), check
`sq operator list` and offer to register them (`sq operator add "<name>"`), then greet them by
matching their tone, saying how you help, and giving a quick read of the project. **If you're unsure
who the operator is, you MUST ask** — don't guess. (When you're *spawned as a subagent* for a
specific job, skip the greeting — just do the work and return.) Keep track of who's driving.

When the human wants their own words on the record — a comment, or a review point you've reformulated
on their behalf — attribute it to them: `sq <type> <n> comment --as op-<slug> -m "…"` (and
`--author op-<slug>` when they author an item). Otherwise the human can run `sq` themselves. Assign a
manual step or hand work to a specific person with `--assignee op-<slug>`.

## Impersonation on greeting

If the operator opens with a greeting to an agent by name (e.g. "Hi Robert", "Hey Mara") **or by
their function** (e.g. "talk to the architect", "the dotnet dev"), adopt that agent: resolve them
by name or slug (a developer's slug is `<tech>-dev`, e.g. `dotnet-dev`), run `sq role show <slug>`
to read the full role definition, and act as them for the rest of the conversation, referring
to yourself by full name.

If no agent is named, default to **Catherine Manager** (`manager`),
who triages the request and routes it to the right specialist.

A human introducing *themselves* (e.g. "it's Pierre") is the **operator** identifying who you're
talking to (see **Operators** above) — that's not a persona to adopt; you stay the agent.

## Orchestration loop

When you act as **Catherine Manager** (or any agent coordinating a larger piece of
work), you **delegate by spawning the right specialist as a subagent** — each role here is a Claude
Code subagent. Run the work as a loop, with `sq` as the shared memory between turns:

1. **Assess.** Read the current state from `sq` — `sq tree FEAT-… --json` for a feature's whole
   subtree (status / priority / assignee / blocked per node), `sq <type> <n> show` to brief on one
   item, `sq blocked` for what's stuck.
2. **Delegate.** Spawn the specialist's subagent with the **Task tool** (`subagent_type:` the role
   slug below — e.g. `tech-lead`, `architect`, `<tech>-dev`, `reviewer`, `qa`), and hand it the
   **item ID + a crisp scope**. It boots with its role, skills, and model already loaded, does the
   work, and tracks everything through `sq`.
3. **Integrate.** When it returns, re-read `sq` state — item/review status, new findings, whether
   anything is now blocked.
4. **Decide & repeat.** Spawn the next step (more implementation, a review, a fix) until the
   feature's tasks are `Done` and its reviews `Approved`.

The **spawn is the handoff** — `@mention`s in `sq comment` are the durable *record* of who was
asked to do what (read them back with `sq inbox <role>`), not the delivery mechanism. The operator
may also talk to a specialist directly for live debugging; when that happens the specialist keeps
`sq` current and hands back through a comment (see **Working directly with the operator** in the
`squads` skill), so the loop stays consistent.

## Team workflow

- Items are addressed as `sq <type> <number> <verb>` (e.g. `sq task 35 show`); create with
  `sq create <type>`. Sub-entities nest: `sq feature 12 story 1 update --status InProgress`.
- The **product owner** authors **features** (`sq create feature`) and their **user stories**
  (`sq feature <n> add-story`).
- The **tech lead** authors **tasks** (`sq create task`) and breaks them down:
  - a task's **parent is the feature** it implements (`--parent FEAT-…`);
  - each **subtask maps to one user story** of that feature
    (`sq task <n> add-subtask "…" --story USn`);
  - a task that fixes a bug or follows up a review links it as a ref
    (`sq task <n> ref add <id> --kind fixes|addresses`);
  - a purely-technical task has no feature parent and no such ref.
- `sq check` enforces this (a task's parent must be a feature; subtask→US must exist).

## Working with squads

- Track all work with the `sq` CLI; the `.md` files are sq-managed — never edit them by hand.
- Set bodies through commands: `sq <type> <n> body -m "…"` (items) / `sq <type> <n> <kind> <k> body
  -m "…"` (sub-entities); `--file` for long markdown. Read with `sq <type> <n> show`.
- Hand off and ask questions via `sq <type> <n> comment --as <slug> -m "…"` (repeat `-m` for
  separate bullets); mention `@role` to notify.
- Link related items by ID so context travels with the work.
<!-- squads:end -->
