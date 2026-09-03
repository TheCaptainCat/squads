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
  state, carried on `Item.subentities`), `_index` (`SquadsDB`), `_vocab` (`prefix_for`/`label_for` —
  the per-type vocabulary resolver; there is **no** `ItemType`/`Status` enum and no built-in
  prefix→folder map, the spec is the sole authority and folder resolution goes through
  `SquadPaths.folder_for`), `_markers` (sq anchor tags), `_config` (`.squads.toml`), `_extras`
  (`ExtraKey`).
- `_paths.py` — resolve the active squad folder (`--dir` > `.squads.toml` walk-up > default), map an
  ID/type to its location, and guard `abspath` against path traversal.
- `_index/_store.py` — the integrity core: filelock'd, atomic (`os.replace`) read-modify-write of
  `<squad-dir>/.squads.json`; `SquadsDB.allocate_id` (on the model, `_models/_index.py`) bumps the
  **single global counter**, called only inside `IndexStore.transaction()`; `load` wraps a
  corrupt index in `SquadsError`. `SquadsDB.items` is keyed by the item's **int sequence number**
  (`Item.sequence_id`, a stored field; the formatted `id` is a `@computed_field` from `type` +
  `sequence_id`). Both `id` and `sequence_id` are persisted in `.md` frontmatter; `get`/`add`
  accept/use the formatted id transparently, and a `model_validator` normalizes legacy full-id keys.
- `_sections.py` / `_itemfile.py` — marker-safe edits and frontmatter↔Item mapping.
- `_specs/` — the bundled vocabulary as package-data TOML: `workflow.toml` (types/statuses/
  lifecycles/collections), `roles.toml` (the role catalog), `playbook.toml` (the team playbook).
  Each has its own loader + spec models (`_workflow/`, `_roles/`, `_interactions/`) and its own
  `.overrides/` counterpart; `_specmerge.py` is the shared deep-merge/splat-ref engine and
  `_overrides/` the scaffold/diff/stamp surface behind `sq override`.
- `_workflow/` — `_loader.py` + `_models.py`: `WorkflowSpec` and friends. The workflow capabilities
  are **methods on the spec**; `__init__` also exposes module-level shims over the *bundled* spec —
  per-type status machines + `can_transition` + `TERMINAL`/`is_open` +
  `ALLOWED_PARENTS`/`parent_allowed`/`parent_hint` — which are **not** override-aware. For anything
  a project can customise use the threaded active spec (`Service.spec`, `_cli._common.get_active_spec()`);
  there is no process-global mutable spec.
- `_rendering/` — Jinja2 (`StrictUndefined`); templates are package data under `_rendering/templates/`.
  `_engine.py` registers `slugify` + `open_marker`/`close_marker` filters. Item files render from
  `templates/items/*.md.j2`; **sub-entity blocks + their roll-up table** render from
  `templates/subentities/{block,summary}.md.j2` (driven by `_discussion.build_block`/`render_summary`).
  **Sub-entity state (status/assignee/severity/story) lives in the parent's frontmatter**
  (`Item.subentities`, typed `SubEntity`), not the body — the block only holds prose (`:body`,
  `:discussion`) plus a derived `:head` badge line (human-readable status/severity/assignee-name/story)
  rendered from `subentities/head.md.j2` via `_discussion.set_head` (badges resolved from the
  spec's collections by `_badges.py` — `status_badge`/`badge_render`/`resolve_collection`/
  `field_label`); the service's `_refresh_head` resolves
  names/titles from the model and re-renders the head + summary on every mutation. Extend the head with more `{% if %}` lines. The
  legacy body-stored `:meta` regions survive only in `_migrations/_meta_compat.py`, used by the
  migrations.
- `_backends/` — `AgentBackend` ABC + registry; `_claude_code/` writes pointer files, managed skills
  (real body under `<squad>/agents/skills/`, thin pointer in `.claude/`), and the CLAUDE.md section;
  `_agents_md/` writes the AGENTS.md equivalent. `_managed_region.py` is the shared, backend-neutral
  managed-section wrapper both use — it stamps the `squads:start`/`squads:end` markers plus the
  "regenerated by `sq sync`" warning once, so every backend's managed file inherits it for free.
- `_roles/_catalog.py` — the 8 bundled roles + dev name pool + `dev_role()`.
- `_interactions/` — the team **playbook**: which roles interact with each item type (`*dev`
  sentinel = any `<tech>-dev` role). Drives the per-item-type managed skills (`sq-<type>`) and
  `skills_for_role()`. Workflow cheatsheet partial: `_rendering/templates/workflow.md.j2` (shared by
  the `squads` skill and `sq workflow`).
- `_services/` — orchestration, the logic behind each command. A shared `_base.ServiceCore`
  (create/get/list + backend + role/skill lookups + roster) plus one concern **mixin** per file
  (`_import`, `_items`, `_collab`, `_subentities`, `_refs`, `_roster`, `_maintenance`, `_retype`,
  `_rename`, `_memory`, `_board` — the 11 `Service` bases, in MRO order); `_service.py` composes
  them into the flat `Service` façade and holds `init`/`adopt`/`open_service`; `_results.py` has the
  result dataclasses. Non-mixin helpers live alongside: `_validators.py` (the `sq check` rules),
  `_retirement.py`, `_config_integrity.py`, `_import_model.py`.
- `_discussion.py` — top-level, not under `_services/`: comment formatting + `@mention` extraction,
  and the prose/presentation of a sub-entity block for **any** declared kind — `kind` is a parameter
  throughout and its prefix/placeholder/columns resolve from the spec, so don't reintroduce a
  literal `story`/`subtask` here.
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
7. **Every backend stamps its own generated agent-facing files as tool-generated.** A managed
   region (the `CLAUDE.md`/`AGENTS.md` section) or a whole owned file (a `.claude/` pointer) must
   say plainly it's regenerated by `sq sync` — distinct from the global "squad data is sq-managed"
   rule (#5/#6 above cover *what* is generated; this covers *saying so* in the file itself, so an
   agent editing it in-session doesn't lose the edit unknowingly). Generated files remain
   regenerable/never-migrated; this only makes that fact visible in place.
8. **Markdown is never behind the index.** Within a transaction, every markdown write happens
   before it returns; the index commit is always last. See the full skew-direction rule (and its
   exemptions) in `_index/_store.py`'s module docstring.

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
- **No status/lifecycle prose in bodies.** An item/ADR/review/doc **body** — or its `description:`
  summary — must never declare its own workflow position: no `STATUS: Proposed` banners, no
  hand-written `## Status` headings, no "this is a draft" / "blocked until accepted" / "if accepted,
  then…" self-declarations. The frontmatter `status:` field (shown by `sq … show`) is the single
  source of truth; state declared as prose goes stale the moment the real status changes.
  Timestamped **discussion comments** recording state-at-a-point-in-time are fine and encouraged —
  the discussion is an append-only history, so a dated "moved to Accepted because…" comment never
  goes stale. The line: **declaring** the item's own current state in the body = banned;
  **discussing** lifecycle as a topic (e.g. describing "the Draft→Ready transition" a feature is
  building) or citing *another* item's status as context = fine.
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
  `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`.
  `--all-extras` is required on each — a bare `uv run` prunes the optional `tui` extra
  (`textual`), and pyright then reports hundreds of false import errors under `_tui/`. Annotate
  bare `dict`/`list` (e.g. `dict[str, Any]`); Typer's `Option/Argument` call-defaults are why
  `B008` is ignored under `_cli/`.

## Testing

`pytest` with `typer.testing.CliRunner`; the `project`/`svc` fixtures (`tests/conftest.py`) init a
squad in a `tmp_path` and `chdir` into it — **all file generation stays in temp**. Cover behaviour
through the service/CLI, and assert generated files (valid YAML frontmatter, intact markers,
preserved body). When adding a feature, add a service-level test and a CLI smoke test.

`uv run pytest` runs under `pytest-xdist` (`-n auto` in `addopts`) by default — every test is
already isolated in its own `tmp_path` (frontmatter files, `.squads.json`, the clock override),
so distributing tests across worker processes is safe with no per-test opt-in needed. Use `-n0`
to force serial (not `-p no:xdist`, which unloads the plugin but leaves `-n auto` in `addopts`,
so it errors as an unrecognized arg), e.g. under `--pdb`.

The `slow`-marked scale-bound tests (`tests/test_scale.py`) are **skipped by default** (a
`conftest.py` `pytest_collection_modifyitems` hook), so a bare `uv run pytest` is fast (~30s, not
a hang). Pass `--run-slow` to opt in and run them too (adds ~2 minutes). Run either **once**,
redirect to a file, and read the file (`uv run --all-extras pytest > "$CLAUDE_JOB_DIR/tmp/pytest.log" 2>&1`,
then `tail`/`grep` the log) — never re-run the whole suite just to reslice its output. While
iterating on a fix, use `--lf` / `-x` / a path selector instead of the full sweep (all compose
fine with the default `-n auto`, and with `--run-slow`).

**Do not add `-q` on the command line.** `addopts` already supplies it; a second `-q` drops pytest
past the verbosity that prints the trailing `N passed` / `N failed` count, so the log ends in
progress dots and looks indistinguishable from a pass. **The summary line is the result** — read
it, plus `grep -cE "^FAILED"`. And if you background the run, note that `pytest … > log; echo $?`
reports the *`echo`'s* status, not pytest's: a compound command's exit code is its last element's,
so a wrapper like that reports success no matter what the suite did. Either run it in the
foreground, or read the log.

### Dead-code scan (vulture) — periodic, non-gating

`uv run vulture` finds dead top-level functions/classes/constants that ruff/pyright can't
(they only catch unused *locals* and *imports*). It is **not** part of the `pyright`/`ruff`
commit gate and is **not** wired into CI — run it periodically (e.g. during a hygiene sweep)
and triage its output by hand, the same way you'd read a linter report someone hands you.
`[tool.vulture]` in `pyproject.toml` suppresses the known false-positive *categories* so a
run stays near-pure signal: `ignore_decorators` covers every Typer command/callback shape,
and `ignore_names` lists identifiers vulture can't see used because the call site is a
runtime `getattr(obj, f"...")` dispatch rather than a static reference (pydantic's
`model_config`, and the sub-entity `Service` methods dispatched from `_cli/_items.py`).
When a new run surfaces an intentional false positive, add its exact name to `ignore_names`
(or a decorator pattern to `ignore_decorators`) with a one-line reason — don't silence it by
editing the flagged code, and prefer a real pattern only when one exists without masking
genuinely dead code (e.g. don't add a broad `get_*`/`list_*` wildcard just to cover one or
two names). Vulture also cannot parse this project's Python 3.14 PEP 758 parenthesis-less
`except A, B:` — the (rare) multi-exception sites are parenthesized (`except (A, B):`) with
a `# fmt: skip` so ruff's py314-target formatter doesn't strip the parens back off; this is
now the project convention for any new multi-exception handler.

## Build scope

This codebase implements all three originally planned build phases. The one explicitly deferred
feature is project-level template/role overrides (e.g. `squads/.templates/`); the full design and
that deferral decision live in the approved plan referenced from the project memory.

## The `sq check` gate

`sq check` is advisory for *adopters* of squads, but a **must-pass gate for this repo**. Before any
handoff — subagent → main loop, agent → agent, or a release cut — run `sq check` and leave it
**clean for the work you touched**: no unwritten sub-entity bodies, no over-long finding/story titles
(put the detail in the body, not the title), no broken parent/sub-entity rules. A warning here is a
defect to fix, not an advisory to explain away — don't let board debt pile up on terminal items.

<!-- squads:start -->
<!-- managed by squads — regenerated by `sq sync`; do not edit by hand. -->
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
- **Ada Typescript** — Typescript developer (`typescript-dev`)

## Operators (people)

Operators are the **humans** who work on this project — they can author items and review points, and
be assigned work (including manual steps). They are *not* agents: never spawn them, and address them
by their `op-` slug.
- **Pierre Chat** (`op-pierre`)

**When a human opens a conversation, greet them first** — follow the **`greeting`** skill to
detect the operator, match their tone, explain your role, and give a quick read of the project.
**If you're unsure who the operator is, you MUST ask** — don't guess. (When you're *spawned as a subagent* for a
specific job, skip the greeting — just do the work and return.) Keep track of who's driving.

When the human wants their own words on the record — a comment, or a review point you've reformulated
on their behalf — attribute it to them: `sq <type> <n> comment --as op-<slug> -m "…"` (and
`--author op-<slug>` when they author an item). Otherwise the human can run `sq` themselves. Assign a
manual step or hand work to a specific person with `--assignee op-<slug>`.

## Impersonation on greeting

If the operator opens with a greeting to an agent by name (e.g. "Hi Robert", "Hey Mara") **or by
their function** (e.g. "talk to the architect", "the dotnet dev"), adopt that agent: resolve them
by name or slug (a developer's slug is `<tech>-dev`, e.g. `dotnet-dev`), run `sq role <slug> show`
to read the full role definition, and act as them for the rest of the conversation, referring
to yourself by full name.

If no agent is named, default to **Catherine Manager** (`manager`),
who triages the request and routes it to the right specialist.

A human introducing *themselves* (e.g. "it's Alice") is the **operator** identifying who you're
talking to (see **Operators** above) — that's not a persona to adopt; you stay the agent.

## Start of a run

At the start of a run, load your role memory — `sq memory <role> list`, then `sq memory <role>
show <slug>` for relevant entries — and check the team board with `sq board list`. Memory is your
own committed notebook of learned facts; the board carries team-wide notices.

Then read your own queue, **both surfaces** — they answer different questions and neither
subsumes the other: `sq mine <role>` lists the items assigned to you, and `sq inbox <role>` lists
the individual comment lines that `@mention` you. An item can be in one and not the other.

## Orchestration loop

When you act as **Catherine Manager** (or any agent coordinating a larger piece of
work), you **delegate by spawning the right specialist as a subagent** — each role here is a Claude
Code subagent. Load the `squads` skill immediately at session start, and again after any context
compaction (compaction drops loaded skills). Run the work as a loop, with `sq` as the shared memory
between turns:

1. **Assess.** Read the current state from `sq` — `sq tree <parent-id> --json` for a parent's whole
   subtree (status / priority / assignee / blocked per node), `sq <type> <n> show --full --comments`
   to brief on one item (body + sub-entities + discussion), `sq blocked` for what's stuck.
2. **Delegate.** Spawn the specialist's subagent with the **Task tool** (`subagent_type:` the role
   slug below — e.g. `tech-lead`, `architect`, `<tech>-dev`, `reviewer`, `qa`), and hand it the
   **item ID + a crisp scope**. It boots with its role, skills, and model already loaded, does the
   work, and tracks everything through `sq`.
3. **Integrate.** When it returns, re-read `sq` state — item/review status, new findings, whether
   anything is now blocked.
4. **Decide & repeat.** Spawn the next step (more implementation, a review, a fix) until the
   parent's own work is settled: every child item closed out, every linked review resolved.
5. **Sweep for process-narration before closing.** Before an increment is committed/accepted, run
   one final subagent pass that *reads* the new delivered text — item/sub-entity bodies, code
   comments and docstrings, CHANGELOG, docs — for internal build-process references that seeped in:
   phase / round / wave / increment language, "this pass", "the reviewer's finding", "withheld
   until a later phase", "as discussed above", and the like. This is the judgment-level residue the
   auto-grep hygiene gate (which only catches ticket-IDs) cannot see. Delivered text must describe
   the thing, not narrate how it was built — strip what the pass finds. (Historical discussion
   comments recording state-at-a-point-in-time are exempt — the discussion is an append-only log;
   this targets the durable body/comment/doc/code prose that outlives the build.)

The operator may also speak directly to a specialist for live debugging; the specialist keeps
`sq` current and hands back through a comment, so the loop stays consistent.

## Team workflow

- Items are addressed as `sq <type> <number> <verb>` (e.g. `sq task 35 show`);
  create with `sq create <type>`. Sub-entities nest: `sq <type> <n> <kind> <k> update --status <status>`.
- The **product owner** authors **epics** (`sq create epic`).
- The **product owner** authors **features** (`sq create feature`), breaking work into `add-story`.
- The **tech lead** authors **tasks** (`sq create task`); its parent is the feature it implements (`--parent FEAT-…`), breaking work into `add-subtask` (`--story USn` maps one to a parent story), and links fixes/follow-ups via `ref add <id> --kind fixes|addresses`.
- The **QA engineer** authors **bugs** (`sq create bug`).
- The **architect** authors **decisions** (`sq create decision`), and links fixes/follow-ups via `ref add <id> --kind supersedes`.
- The **code reviewer** authors **reviews** (`sq create review`), breaking work into `add-finding`.
- `sq check` enforces each declared parent/sub-entity rule (task).

## Working with squads

- Track all work with the `sq` CLI; the `.md` files are sq-managed — never edit them by hand, and
  read them through `sq <type> <n> show`, never by opening the file: the command resolves state the
  file does not carry, so a direct read returns strictly less than the command.
- Set bodies through commands: `sq <type> <n> body -m "…"` (items) / `sq <type> <n> <kind> <k> body
  -m "…"` (sub-entities); `--file` for long markdown. Read with `sq <type> <n> show --full --comments`
  (full dossier including discussion).
- Hand off and ask questions via `sq <type> <n> comment --as <slug> -m "…"` (repeat `-m` for
  separate bullets); mention `@role` to notify.
- Link related items by ID so context travels with the work.
<!-- squads:end -->
