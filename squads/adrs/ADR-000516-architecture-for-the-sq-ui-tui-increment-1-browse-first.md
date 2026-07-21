---
id: ADR-516
sequence_id: 516
type: decision
title: 'Architecture for the sq ui TUI (increment 1: browse-first)'
status: Accepted
parent: EPIC-28
author: architect
created_at: '2026-07-21T09:12:54Z'
updated_at: '2026-07-21T09:14:56Z'
---
<!-- sq:body -->
# Context

EPIC-28 ships `sq ui`, an in-terminal TUI for browsing a squad: the item tree on
one side, the selected item on the other (body, sub-entities and discussion as tabs,
rendered markdown, status at a glance). Increment 1 is **browse-first / read-only**;
mutation (transition, comment, assign) is a later increment that this architecture
must leave the door open to, not a non-goal.

The TUI is a pure consumer of surfaces we already froze: the `--json` shapes and the
shared id resolver (FEAT-15 / FEAT-19). It must fit the codebase's hard constraints —
the `_cli → _services → (store, backends, rendering)` layering, the acyclic import
graph, the leading-underscore module-privacy convention, and a core install that stays
lean for the many agents who will never open a TUI.

One premise in the epic framing needs correcting up front, because it drives the
packaging decision: **Textual is not "already transitively present via rich."** Rich is
a *dependency of* Textual, not the reverse — Textual is a separate Textualize package,
and it is not installed today (`rich` 15.0 is present; `textual` is absent). So the TUI
framework is a genuinely new dependency we are adding, which is exactly why it belongs
behind an optional extra rather than in the core dependency list.

# Decision

## 1. Stack — Textual, behind a floor pin

The TUI is built on **Textual** (Textualize, rich's sibling). Its `Tree`,
`TabbedContent` and `Markdown` widgets map one-to-one onto the tree / tabbed-reader /
rendered-body needs, and it composes with the `rich` renderables we already produce.
Textual depends on `rich`, so there is no second rendering stack and no version tug-of-war
with our existing `rich>=13.7` (Textual pulls a compatible rich; our installed 15.0
satisfies it).

Dependency approach: pin a **lower floor only** (e.g. `textual>=0.60`), consistent with
how every other dependency here is pinned (`>=`, no upper cap), so adopters resolve a
current Textual. The exact floor is the tech-lead's to set against the widgets actually
used; the rule pinned here is "floor pin, no ceiling."

## 2. Packaging — optional extra `squads[tui]`, lazy import, clean failure

Textual is declared under `[project.optional-dependencies]` as the **`tui`** extra, not
in core `dependencies`. `pip install squads` stays lean; `pip install squads[tui]` (or
`uv sync --extra tui` in this repo) pulls Textual in.

Two hard rules follow:

- **Lazy import.** `textual` (and the `squads._tui` package, which imports it at module
  top) must be imported **only inside the `sq ui` command body**, never at CLI import
  time. Core startup, `sq --help`, and the import-graph acyclicity check must be
  unaffected whether or not the extra is installed. The codebase already uses
  function-local imports pervasively (e.g. `_CustomTypeGroup`), so this is idiomatic.

- **Clean failure when the extra is missing.** `sq ui` first attempts the lazy import
  inside a `try: import textual` guard. On `ModuleNotFoundError` it raises a
  `SquadsError` with an actionable install hint (e.g. *"the sq ui terminal UI needs the
  optional 'tui' extra — install it with `pip install squads[tui]`"*). The user must
  see that clean one-line message and exit 1, **never** a raw `ImportError` traceback.
  `SquadsError` is the right vehicle: the CLI's error bridge already turns it into
  `error: …` + `typer.Exit(1)`.

## 3. Data access — in-process, straight to the read layer (read-only)

The TUI runs **in-process and calls the `Service` read layer directly** — the same
`open_service()` / `Service` the CLI commands use via `get_service()`. It does **not**
shell out to `sq … --json`.

Rationale, weighed against the subprocess boundary the VS Code client uses:

- The VS Code client is a *separate process in another language* (TypeScript/Node); a
  process boundary over `--json` is the only option it has. The TUI is Python running in
  the same interpreter — a subprocess boundary would buy nothing and cost a fork + JSON
  round-trip per navigation, plus re-parsing shapes back into untyped dicts we already
  have as typed models.
- In-process gives typed access to `Item` / `SubEntity` / result dataclasses and the
  same validated, filelock'd store the CLI trusts — no drift risk between two read paths.

Constraint for increment 1: **read-only**. The TUI calls only read/query methods
(get / list / tree / discussion-formatting); it makes **no mutating service calls**.
This is a discipline rule for the increment, not an architectural wall — the same
in-process `Service` handle is exactly what a later mutation increment will call
(inside the store's locked transactions), so choosing in-process now is what keeps that
door open rather than closing it.

## 4. Module placement & wiring

- TUI code lives in a new **private `squads/_tui/` package** (Textual `App` subclass,
  screens, widgets). It sits at the same layer as `_cli`: it is a *presentation* layer
  that consumes `_services`. It may import from `_services` / `_models` / `_rendering`;
  it must **not** be imported *by* `_services` or below. This keeps the
  `_cli/_tui → _services → …` layering and the acyclic import graph intact (the
  acyclicity check must still pass).

- `sq ui` is wired as a **top-level command in `_cli`** (a thin `@app.command("ui")` in
  a small module, e.g. `_cli/_ui.py`, registered like the other `_cli` sub-modules). The
  command function does only: resolve the active squad (surfacing the normal
  not-a-squad `SquadsError`), run the missing-extra guard from §2, then hand off into
  `squads._tui`. All heavy TUI imports happen *inside* it.

- **Event-loop note for the tech-lead:** Textual's `App.run()` drives its own asyncio
  loop, so `sq ui` must **not** go through the CLI's `command` async bridge (which wraps
  the body in `anyio.run(...)` — nesting loops would fail). `sq ui` is a plain sync Typer
  command: do the synchronous validation (squad resolution + extra guard) with its own
  `try/except SquadsError` → clean message + `typer.Exit(1)`, then call the Textual
  app's blocking `.run()` outside any `anyio.run`.

# Consequences

- Core install and agent startup are unchanged; only `squads[tui]` users pull Textual.
  The import graph and its acyclicity check are unaffected because nothing in the core
  path imports `_tui` or `textual` at module load.
- There is a single read path (the `Service` layer) shared by CLI and TUI — no second
  serialization/parse path to keep in sync, and the frozen `--json` shapes remain the
  contract for *out-of-process* clients (VS Code), not for the in-process TUI.
- The missing-extra experience is a documented, testable one-liner, not a traceback —
  assertable with a monkeypatched-absent `textual` in a normal service/CLI test.
- A later mutation increment plugs into the same in-process `Service` (locked
  transactions) and the same `_tui` package; no boundary has to be renegotiated.
- Adopter docs (install matrix / `sq ui`) will need a note that the TUI requires the
  extra — a downstream doc task, not part of this decision.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T09:14:55Z] Catherine Manager:
  - Accepted after a full read of the body. Rules stand: Textual behind the optional `tui` extra (lazy import + clean SquadsError on missing extra), in-process Service read layer (read-only for increment 1), private `squads/_tui/` presentation package + thin `_cli/_ui.py` command, floor-pin only. The event-loop note (sync command, Textual owns its loop — not the anyio bridge) is a build rule the tech-lead must carry into the tasks. Corrected epic premise noted: Textual is a genuinely new dependency.
<!-- sq:discussion:end -->
