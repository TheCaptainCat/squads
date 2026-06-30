---
id: ADR-000263
sequence_id: 263
type: decision
title: Registering a custom type's top-level CLI command ahead of Click's parse-time
  command resolution
status: Accepted
author: architect
refs:
- FEAT-000210:addresses
- ADR-000249
description: How to register sq <custom-type> as a top-level CLI command when the
  type name comes from a squad-dir-dependent override; chose the lazy-dispatch TyperGroup
  (Option 3) so the built-in command surface stays byte-identical.
created_at: '2026-06-30T12:06:45Z'
updated_at: '2026-06-30T12:14:54Z'
---
<!-- sq:body -->
## Context

FEAT-000210 makes a project-declared custom type (e.g. `[workflow.types.incident]` in
`.overrides/workflow.toml`) fully usable: `sq incident create "…"`, `sq list -t incident`, a custom folder, an
auto-generated `sq-incident` skill. AC#1 is the headline: *"a team that adds `incident` can run
`sq incident create …` with no code change."*

ADR-000249 / FEAT-000250 (Option A, done) already de-globalized the workflow spec into a
per-`Service`/per-invocation context: the root `--dir` callback resolves and binds the active spec
via `common.set_active_spec()` (`_cli/__init__.py:_bind_active_spec`, called at
`main_callback` line 100), and `parse_type`/`parse_status`/display helpers read it back via
`common.get_active_spec()` (`_cli/_common.py:701-729`). **That solved per-invocation value
*parsing* on already-routed commands.** It does NOT solve registering a new top-level command
*name*.

### The problem, grounded in the code

The Typer app **tree is built at module-import time**, before any invocation. In
`_cli/__init__.py:129-165`:

```python
from squads._workflow import work_types as _work_types          # reads the BUNDLED spec
_ORDERED_WORK_TYPES = [t for t in ItemType if t in _work_types()]
...
for _type in _ORDERED_WORK_TYPES:
    _type_app = _items.build_item_app(_type)
    app.add_typer(_type_app, name=_type.value, ...)
    for _alias in TYPE_ALIASES.get(_type, ()):
        app.add_typer(_type_app, name=_alias, hidden=True)
```

The command set is fixed at import from the **bundled** spec / `ItemType` enum. But a custom type's
name lives only in a **squad-dir-dependent** spec that `_bind_active_spec(dir)` resolves *inside the
root callback* — which Click runs only **after** it has parsed argv and resolved which subcommand to
dispatch. So the resolution order for `sq incident create "…"` is:

1. Click parses argv, looks up `incident` in the group's command table → **not found**.
2. Click prints `No such command 'incident'.` and exits.
3. The root callback (and therefore `_bind_active_spec`, and therefore the `incident` command) never
   runs.

Verified against HEAD: `sq incident create "x"` today prints `No such command 'incident'. Did you
mean 'init'?`. The spec is known too late by construction. This is the FEAT-250 ordering wall in its
*command-registration* form, one level earlier than the *value-parsing* form FEAT-250 solved.

A second, related fact (TASK-000257 also owns it): the alias loop reads the hardcoded
`TYPE_ALIASES` dict in `_enums.py`, not `ItemSpec.aliases` from the spec. Whatever mechanism
registers a custom type's command must also register its spec-declared aliases. This ADR's scope is
the *name-registration ordering*; the alias source-swap rides along with whichever approach wins.

### What "byte-identical" (AC#7) actually requires — measured

The built-in work-type commands **do** appear in top-level `sq --help` (measured on HEAD):

```
│ epic      Operate on a epic by number.
│ feature   Operate on a feature by number.
│ task      Operate on a task by number.
│ bug … decision … review … guide …
```

So AC#7 has a precise, testable meaning, and TASK-000256's golden pins it: **for a squad with no
custom types, `sq --help` must list exactly `epic/feature/task/bug/decision/review/guide` in
declaration order, and `sq <unknown>` must keep printing Click's `No such command 'X'. Did you mean
…?` + exit code.** Any approach that perturbs the no-custom-type `--help` text, the command order,
or the unknown-command error fails AC#7/#8. Custom types appear in `--help` *only* when a project
spec declares them.

### One structural complication for all options

`_items.build_item_app(item_type)` is typed `(ItemType) -> typer.Typer` and keys internal behaviour
off the **enum** (`_SUBENTITY: dict[ItemType, …]`, `item_type in _work_types()`). A custom type has
no `ItemType` member. So *every* option below shares a prerequisite refactor: `build_item_app` must
accept a **type string** and source its capability flags (subentity kind, severity, work-vs-meta)
from the spec via `get_active_spec().item_subentity_kind(t)` etc., not from enum membership. This is
spec-flag plumbing FEAT-208 already built the accessors for; it is independent of the
ordering-approach choice and should be its own sub-step of TASK-257.

---

## Options

Three approaches were identified (Olivia, FEAT-210 breakdown). Each is evaluated against the code
above, including how it answers the three behaviour questions: **`--help` enumeration**,
**`sq <unknown>` error**, and **shell completion**.

### Option 1 — Resolve the spec at import time (build the app tree from the loaded project spec during module import)

Move spec resolution *before* the app-build loop in `_cli/__init__.py`: walk up for the project
`.overrides/workflow.toml`, load+merge+validate the project spec at import, iterate
`spec.managed_types` to build the tree.

- **How does it know the squad dir at import?** It can't know `--dir` — that argv hasn't been parsed
  when the module is imported. The best it can do is the squad walk-up from `cwd`
  (`_paths.resolve(None)`, which then reads `.overrides/workflow.toml`). So `sq --dir /other/squad incident …` would still fail: the tree was
  built from the *cwd* squad, not the `--dir` one. That breaks `--dir` for custom types — a
  correctness hole, not just UX.
- **`--help` / unknown-command / completion:** would enumerate the cwd-squad's custom types; all
  three behave "correctly" *only* when cwd is the target squad and no `--dir` redirect is used.
- **Blast radius — severe.** Import of `squads._cli` would do filesystem I/O, TOML parsing, spec
  validation, and could **raise** (a malformed project `.overrides/workflow.toml` would crash *every* `sq`
  invocation, including `sq --help` and `sq migrate up` — the very command you'd run to fix it).
  Every test that imports the CLI (the whole suite via `CliRunner`) pays import-time spec resolution
  and becomes order/cwd-sensitive; `conftest` chdir-into-tmp interacts badly with import-once module
  caching (the app tree is built *once* per process, but tests chdir between squads → stale tree).
- **AC#7:** fragile. The no-custom-type path *might* be byte-identical, but the import-time failure
  mode and the `--dir` hole make it unsound.
- **Effort:** medium. **Risk: high.** **Recommendation: reject.** Import-time I/O that can crash the
  whole CLI, plus a real `--dir` correctness bug, is disqualifying.

### Option 2 — Pre-scan argv for `--dir` in `main()`, then build the tree with the resolved spec

`main()` already rewrites `sys.argv` (`_hoist_global_options`, lines 195-198), so there is a natural
home. Before building the app tree, scan argv for `--dir`/`--dir=`, resolve+load+validate the spec
for that dir (falling back to the cwd walk-up), then build the tree from `spec.managed_types`.

- **Knows the squad dir:** yes — it parses `--dir` out of argv itself, so `sq --dir /other incident`
  works. This fixes Option 1's correctness hole.
- **`--help`:** enumerates the resolved squad's custom types. For a no-custom squad, identical to
  today (bundled set) → AC#7 holds *iff* the pre-scan resolves to the bundled spec on the no-override
  path, which it does.
- **`sq <unknown>`:** the type genuinely isn't registered → Click's native `No such command` error,
  byte-identical to today. Good.
- **Shell completion:** **the weak point.** Completion does NOT go through `main()` — the shell
  invokes a separate completion entry (`_SQ_COMPLETE=...`) that imports the module and introspects
  the app object. The argv it sees is the completion protocol's, not the user's command line, so the
  `--dir` pre-scan won't fire the same way; custom-type completion would be best-effort / cwd-based.
  Built-in completion is unaffected (bundled types always registered).
- **Blast radius — moderate, and concentrated in `main()` only.** The app tree is still built once,
  but now as a side effect of `main()` rather than pure import. Key subtlety: today the module-level
  `app` is built at *import*; moving the type-loop into `main()` (or making it re-runnable) means the
  tree must be assembled per process-entry. Tests that call the app via `CliRunner` (not via
  `main()`) would bypass the pre-scan — so the build must be factored into a function callable from
  both `main()` and a test/`CliRunner` path, with the bundled set as the default. Manageable but it
  *does* move app construction out of pure import, which several tests assume.
- **AC#7:** holds for `--help` + unknown-command on no-custom squads (bundled path unchanged).
- **Effort:** medium. **Risk: medium.** Argv pre-scanning is inherently a partial re-implementation
  of Click's own parsing (e.g. `--dir` after `--`, abbreviations, `--dir=x` vs `--dir x` — the
  existing `_hoist_global_options` already handles the two value forms, so we'd reuse that). Honest
  but slightly brittle, and completion is degraded.

### Option 3 — Lazy `TyperGroup.get_command` that resolves the spec on demand (à la `AddressDispatchGroup`)

Subclass `typer.core.TyperGroup` for the **root** app (precedent: `AddressDispatchGroup` in
`_common.py:629`, already used for `role`/`skill`/`operator` to route unknown tokens to a hidden
`_addr` subgroup via `_click_resolve_command`/`get_command`). Click calls `get_command(ctx, name)`
to resolve a subcommand. Override it: built-in commands resolve from the statically-built table
(unchanged); for an **unknown** name, lazily bind the spec (the `--dir` is available on the Click
`ctx` by the time `get_command` runs for the subcommand, *or* resolve the cwd walk-up) and, if
`name in spec.managed_types`, build and return `build_item_app(name)` on the fly.

- **`AddressDispatchGroup` is the proven local pattern** for exactly this: "an unknown token at this
  group level means *resolve it dynamically*." Option 3 generalizes that from "unknown token → addr
  subgroup" to "unknown command → custom-type subapp if the spec knows it."
- **Knows the squad dir:** `get_command` runs within Click's resolution, by which point the root
  group's params have been seen; with care `--dir` is reachable from `ctx`/`ctx.parent.params`.
  Worst case it falls back to the cwd walk-up, same as `_bind_active_spec`'s own fallback. This is
  the same ordering FEAT-250 already navigates for parse_type.
- **`--help`:** **the hard question.** Click builds the top-level help by calling
  `list_commands(ctx)` (which Option 3 must also override) and then `get_command` for each. For a
  no-custom squad, `list_commands` returns exactly the static set → `--help` is byte-identical
  (AC#7 holds cleanly). For a *custom* squad, we choose whether `list_commands` enumerates the custom
  types (nice UX, requires resolving the spec during help generation) or omits them (they still
  *work* when typed, just aren't listed). **Recommended: enumerate from the resolved spec in
  `list_commands` so `sq --help` shows `incident` — matching US2's spirit that the team sees current
  vocabulary.** Crucially, the no-custom-type output path doesn't change, because the resolved spec
  *is* the bundled spec there.
- **`sq <unknown-non-type>`:** `get_command` returns the static command if found; for a truly unknown
  name not in `spec.managed_types`, it returns `None` and falls through to `super()` → Click's native
  `No such command 'X'. Did you mean …?`. **Byte-identical to today.** This is the cleanest answer of
  the three to the unknown-command question.
- **Shell completion:** Click's completion machinery calls `list_commands`/`get_command` too, so a
  correct `list_commands` override gives custom types completion "for free" to the extent the spec is
  resolvable in the completion context — strictly better than Option 2, and built-in completion is
  unchanged.
- **Blast radius — smallest and most contained.** No import-time I/O (the tree is still
  statically the bundled set at import; custom types are resolved *lazily, per-resolution*). No
  argv pre-parsing. `main()` and pure-import semantics are untouched, so the test suite's import
  assumptions hold. The change is localized to one `TyperGroup` subclass (`get_command` +
  `list_commands`) wired as `cls=` on the root `app`, mirroring the existing dispatch-group wiring.
- **AC#7:** strongest. Because the resolved spec on a no-custom squad *is* the bundled spec, the
  static table, `list_commands`, and the `super()` fall-through all produce today's exact output —
  `--help`, command order, and the unknown-command error are byte-identical by construction, and
  TASK-256's golden gates it.
- **Effort:** medium (the `get_command`/`list_commands` override + the `build_item_app(str)`
  refactor; the latter is shared by all options). **Risk: medium-low.** The known sharp edges:
  reaching `--dir` from the Click `ctx` inside `get_command` (proven tractable by FEAT-250's
  callback-ordering work), and ensuring `list_commands` resolution failures degrade to the bundled
  set rather than raising (same fail-soft contract `_bind_active_spec` already uses).

---

## Recommendation

**Option 3 — a lazy-dispatch root `TyperGroup` (`get_command` + `list_commands`) modeled on the
existing `AddressDispatchGroup`.** Pick this.

Rationale:

1. **It already has precedent in this codebase.** `AddressDispatchGroup` proves the team is
   comfortable with custom Click `Group` resolution, and it solves the structurally identical problem
   (unknown token at a group → dynamic resolution). Option 3 is "the same trick, one level up."
2. **It is the only option that keeps app construction at pure import for the built-in path**, so the
   `--help` / unknown-command output for a non-custom squad is byte-identical *by construction* (the
   resolved spec equals the bundled spec there) — the cleanest possible AC#7/#8 story. Options 1 and
   2 perturb when/how the tree is built and have to *prove* byte-identity rather than get it for free.
3. **It answers all three behaviour questions cleanly:** unknown-command falls through to Click's
   native error (identical to today); `--help` enumerates custom types from the resolved spec
   (`list_commands` override) while leaving the bundled list untouched; completion rides the same
   `list_commands`/`get_command` path (best of the three).
4. **Smallest, most contained blast radius** — one `TyperGroup` subclass, no import-time filesystem
   I/O (Option 1's fatal flaw: a bad project TOML crashing every `sq` invocation), no argv
   re-parsing (Option 2's brittleness + degraded completion).

Reject Option 1 outright (import-time I/O that can crash the whole CLI + a `--dir` correctness hole).
Hold Option 2 as the fallback if reaching `--dir` from the Click `ctx` inside `get_command` proves
harder than FEAT-250's precedent suggests — Option 2's argv pre-scan in `main()` is a known-honest
mechanism, at the cost of degraded custom-type completion and moving app construction out of pure
import.

### How AC#7 byte-identical `--help`/output is preserved

- The static command table built at import remains exactly `epic/feature/task/bug/decision/review/
  guide` in declaration order — unchanged from today.
- On a **no-custom-type squad**, the resolved spec **is** the bundled spec, so the `list_commands`
  override returns the identical set in identical order, and `get_command`'s fall-through yields
  Click's identical `No such command` error. `--help` text, command order, and unknown-command
  behaviour are byte-for-byte today's.
- Custom types are additive: they appear in `--help`/completion and resolve as commands **only** when
  a project spec declares them. They never alter the built-in surface.
- TASK-000256's characterization golden (pinned roster/clock/flags) gates every rewire; AC#8's F1
  golden stays green. The `list_commands` override must fail-soft to the bundled set on any spec
  resolution error, exactly as `_bind_active_spec` already does, so a broken project override can
  never corrupt the built-in `--help`.

### Effort / risk read for TASK-000257

- **Effort: medium.** Three sub-steps: (a) refactor `build_item_app` to accept a **type string** and
  source capability flags from `get_active_spec()` rather than `ItemType` membership (shared by all
  options; do this first); (b) the root `TyperGroup` subclass with `get_command` + `list_commands`
  overrides, fail-soft to bundled; (c) swap the alias loop from `TYPE_ALIASES` to `ItemSpec.aliases`
  and retire `TYPE_ALIASES` (coordinate the `_workflow_cmd._print_cheatsheet` + `squads_skill.md.j2`
  consumers with TASK-261).
- **Risk: medium-low**, with two named sharp edges to nail in the task: (1) reaching `--dir` from the
  Click `ctx` inside `get_command`/`list_commands` (FEAT-250's callback-ordering work is the
  precedent — confirm `ctx.parent.params`/the already-bound `set_active_dir` is readable there); (2)
  `list_commands` must degrade to the bundled set on spec-resolution failure, never raise. Shell
  completion for custom types is "best-effort" — call it out as acceptable for F4 (built-in
  completion is unchanged), and let FEAT-211 harden it if needed.
- **Dependencies:** TASK-257 depends on TASK-256 (golden gate) and TASK-258 (folder/prefix so a
  created custom item lands and parses back).

---

## Consequences

- TASK-000257 implements Option 3: `build_item_app(str)` + the lazy-dispatch root group become the
  mechanism custom types register through; `TYPE_ALIASES` retires in favour of `ItemSpec.aliases`.
- **Custom-type shell completion is best-effort** (not byte-identical to a hand-tuned completion);
  documented as a known F4 limitation, candidate for FEAT-211 hardening.
- **The built-in CLI surface is frozen by AC#7** — this decision is explicitly engineered so that
  nothing about a non-custom squad's `--help`, command order, or unknown-command error changes.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T12:08:45Z] Robert Architect:
  - Assessment ADR for the FEAT-210 startup-ordering crux (TASK-257). RECOMMENDATION: Option 3 — a lazy-dispatch root TyperGroup (get_command + list_commands), modeled on the existing AddressDispatchGroup in _common.py:629. It's the only option that keeps the built-in path at pure import, so a non-custom squad's --help / command-order / unknown-command error are byte-identical to today BY CONSTRUCTION (resolved spec == bundled spec there) — cleanest AC#7/#8 story, gated by TASK-256's golden.
  - Options in one line each: (1) resolve-spec-at-import — REJECT: import-time filesystem I/O that can crash every sq invocation on a bad project TOML, plus can't see --dir so it breaks --dir for custom types. (2) argv pre-scan in main() — FALLBACK: honest, --dir works, but partially re-implements Click parsing and degrades custom-type shell completion (completion doesn't go through main()). (3) lazy TyperGroup.get_command — PICK.
  - Behaviour questions resolved: sq <unknown> → Option 3 returns None from get_command and falls through to Click's native 'No such command X. Did you mean…?' (byte-identical to HEAD, verified). --help → a list_commands override enumerates custom types from the resolved spec while leaving the bundled list untouched; on a no-custom squad the resolved spec IS the bundled spec so output is unchanged. Completion → rides the same list_commands/get_command path, best-effort for custom types, built-in unchanged.
  - TASK-257 read: effort MEDIUM (3 sub-steps — (a) refactor build_item_app to take a type STRING + spec capability flags instead of the ItemType enum [shared by ALL options, do first]; (b) the root TyperGroup subclass; (c) alias loop TYPE_ALIASES→ItemSpec.aliases, retire TYPE_ALIASES, coordinate _print_cheatsheet + squads_skill.md.j2 consumers w/ TASK-261). Risk MEDIUM-LOW: two sharp edges — reach --dir from the Click ctx inside get_command (FEAT-250 precedent), and list_commands must fail-soft to bundled, never raise.
  - @manager Proposed, awaiting go/no-go. Drafting ≠ greenlight; TASK-257 stays blocked until accepted + approach confirmed. 256/258/259/262 proceed in parallel meanwhile.
- [2026-06-30T12:09:56Z] Catherine Manager:
  - Accepted Option 3 (lazy-dispatch root TyperGroup à la AddressDispatchGroup): keeps the built-in command path at pure import so non-custom squads are byte-identical by construction (AC#7/#8), with a fail-soft list_commands override enumerating custom types from the resolved spec. Rejected resolve-at-import (correctness hole, can't see --dir) and argv-pre-scan (degrades completion). Greenlit for TASK-000257.
- [2026-06-30T12:13:23Z] Robert Architect:
  - Post-acceptance cleanup done (per @manager): (1) status banner rewritten — now reads Accepted, Option 3 selected, TASK-257 unblocked, no go/no-go/greenlight framing; (2) frontmatter description updated to past-tense 'Accepted: chose the lazy-dispatch TyperGroup …'; (3) every .squads.toml occurrence corrected to .overrides/workflow.toml (the FEAT-209 F2 canonical, verified at _loader.py:42); (4) the 'stays blocked on this ADR' dependency line + closing line updated to reflect acceptance. Options analysis / recommendation / --help+unknown-command resolution kept intact. Re-scanned the full body: no Proposed / go-no-go / .squads.toml leftovers. The earlier Proposed-era comment is left as-authored (append-only discussion record). Note: FEAT-210's body has the same stale .squads.toml wording I copied from — flagged to @manager for routing to the PO.
- [2026-06-30T12:14:54Z] Robert Architect:
  - Second cleanup pass done (per @manager, overriding the prior banner-rewrite instruction): (1) DELETED the entire opening STATUS blockquote — the body now starts straight at ## Context. Status is sq-managed metadata (frontmatter status:), never restated in body prose, so it can't go stale. (2) frontmatter description: stripped of all status words — now 'How to register sq <custom-type> as a top-level CLI command … chose the lazy-dispatch TyperGroup', a pure what-it-decides summary. (3) removed every other lifecycle/workflow-state phrase from the body: the 'Accepted:'/'unblocked' Consequences bullet, the 'stays blocked / this ADR accepted' dependency wording, and the closing 'This ADR is Accepted' line — the body now describes only the decision + rationale. .squads.toml→.overrides/workflow.toml correction from the prior pass stands. Re-scanned the full body (excluding the append-only discussion log): the only 'Accepted' left is the frontmatter status: field, which is where it belongs.
<!-- sq:discussion:end -->
