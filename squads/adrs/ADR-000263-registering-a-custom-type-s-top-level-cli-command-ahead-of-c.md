---
id: ADR-263
sequence_id: 263
type: decision
title: Registering a custom type's top-level CLI command ahead of Click's parse-time
  command resolution
status: Accepted
author: architect
refs:
- FEAT-210:addresses
- ADR-249
- ADR-1009
description: How to register sq <custom-type> as a top-level CLI command when the
  type name comes from a squad-dir-dependent override; chose the lazy-dispatch TyperGroup
  (Option 3) so the built-in command surface stays byte-identical.
created_at: '2026-06-30T12:06:45Z'
updated_at: '2026-10-25T21:14:54Z'
---
<!-- sq:body -->
## Context

A project can declare its own work type in `.overrides/workflow.toml` (for example
`[items.incident]`), and the team expects `sq incident create "…"` to work with no code change.

The Typer app tree is built at module import, from the **bundled** spec. A project's custom type
name lives only in the squad's merged spec, and that spec is known only once the squad is found:
from the root group's `-C` values (ADR-1009) or the walk-up from the working directory. Click
parses argv and looks up the subcommand before the root callback that binds the active spec runs.
Without help, `sq incident …` fails with Click's `No such command 'incident'` before the spec is
ever read. Resolving per-invocation *values* on an already-routed command (ADR-249) does not solve
registering a new top-level command *name*.

Any mechanism has to answer three behaviour questions: what `sq --help` lists, what an unknown
command prints, and what shell completion offers. For a squad with no custom types, all three
must stay exactly what the bundled spec produces.

## Options considered

1. **Resolve the spec at import time** and build the whole tree from it. Rejected: import would do
   filesystem I/O, TOML parsing and validation, so a malformed project override would crash every
   `sq` invocation, including `sq --help` and the `sq migrate up` that would fix it. It also cannot
   see `-C`, which has not been parsed at import, so it would build the tree from the wrong squad.
   Every test importing the CLI would inherit a cwd-dependent, built-once tree.
2. **Pre-scan argv in `main()`** for the squad selector, then build the tree. Viable but brittle:
   it re-implements part of Click's parsing, it moves app construction out of pure import (and
   `CliRunner` tests bypass `main()`), and shell completion does not go through `main()`, so
   custom-type completion degrades.
3. **A lazy root `TyperGroup`** that overrides `get_command` and `list_commands`, the same
   technique `AddressDispatchGroup` uses one level down for `role`/`skill`/`operator`.

## Decision

**Option 3.** The root app uses `_CustomTypeGroup` (`_cli/__init__.py`):

- **Static registration at import.** Every non-roster type of the bundled spec is registered at
  import, ordered by `ItemSpec.order` (type name breaking ties), each with its hidden aliases from
  `ItemSpec.aliases`. `build_item_app(item_type: str, spec=…)` takes a plain type string and reads
  every capability (sub-entity kind, retype and remove eligibility) from the spec, so built-in and
  custom types go through the same builder.
- **Lazy dispatch for custom types.** For a name not in the static table, `get_command` resolves
  the squad's spec and, if the name is a declared non-roster type or one of its aliases
  (`spec.alias_to_type`), builds that type's app from the **same** resolved spec and returns it.
  The built command is cached keyed on the type and the spec it was built from, so another
  squad's spec never reuses it.
- **Spec resolution before the callback.** `common.resolve_spec_for_ctx` tries, in order, the
  spec the root callback already bound, the squad found from the root group's parsed `-C` values,
  and the bundled spec. It is memoised on the root context and never raises.
- **`--help` and completion.** `list_commands` returns the static commands, minus any bundled type
  (and its aliases) the active spec drops and any bundled alias it no longer declares, followed by
  the custom non-roster types in alphabetical order. Shell completion walks the same
  `list_commands`/`get_command` path. The root epilog's alias summary is regenerated from the
  resolved spec at render time.
- **Unknown names.** A name that is neither static nor declared falls through to Click's native
  `No such command 'X'. Did you mean …?`. When the squad's override failed to load, the refusal
  says so (`spec_error_command`) instead of judging the word against the bundled vocabulary. A
  bundled alias the active spec no longer declares is refused rather than dispatched.
- **Fail-soft.** Spec-resolution errors on the help/completion path degrade to the bundled set;
  only a build error for a type the spec does declare propagates.

`sq create` uses the same pattern for its per-type subcommands (`_CustomCreateGroup` in
`_cli/_create.py`), sharing `resolve_spec_for_ctx`.

## Consequences

- A custom type registers its command, aliases, help entry and completion with no code change.
- On a squad without overrides the resolved spec is the bundled spec, so `sq --help`, the command
  order and the unknown-command error are those of the bundled vocabulary by construction, and
  the CLI tests pin that the built-in surface is unperturbed when no custom type is declared.
- Import stays free of filesystem I/O, and a broken project override cannot take down `--help`.
- Custom-type completion is best-effort: it works wherever the squad can be resolved from the
  completion context, and falls back to the built-in set otherwise.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T12:08:45Z] `architect` Robert Architect:
  - Assessment ADR for the FEAT-210 startup-ordering crux (TASK-257). RECOMMENDATION: Option 3 — a lazy-dispatch root TyperGroup (get_command + list_commands), modeled on the existing AddressDispatchGroup in _common.py:629. It's the only option that keeps the built-in path at pure import, so a non-custom squad's --help / command-order / unknown-command error are byte-identical to today BY CONSTRUCTION (resolved spec == bundled spec there) — cleanest AC#7/#8 story, gated by TASK-256's golden.
  - Options in one line each: (1) resolve-spec-at-import — REJECT: import-time filesystem I/O that can crash every sq invocation on a bad project TOML, plus can't see --dir so it breaks --dir for custom types. (2) argv pre-scan in main() — FALLBACK: honest, --dir works, but partially re-implements Click parsing and degrades custom-type shell completion (completion doesn't go through main()). (3) lazy TyperGroup.get_command — PICK.
  - Behaviour questions resolved: sq <unknown> → Option 3 returns None from get_command and falls through to Click's native 'No such command X. Did you mean…?' (byte-identical to HEAD, verified). --help → a list_commands override enumerates custom types from the resolved spec while leaving the bundled list untouched; on a no-custom squad the resolved spec IS the bundled spec so output is unchanged. Completion → rides the same list_commands/get_command path, best-effort for custom types, built-in unchanged.
  - TASK-257 read: effort MEDIUM (3 sub-steps — (a) refactor build_item_app to take a type STRING + spec capability flags instead of the ItemType enum [shared by ALL options, do first]; (b) the root TyperGroup subclass; (c) alias loop TYPE_ALIASES→ItemSpec.aliases, retire TYPE_ALIASES, coordinate _print_cheatsheet + squads_skill.md.j2 consumers w/ TASK-261). Risk MEDIUM-LOW: two sharp edges — reach --dir from the Click ctx inside get_command (FEAT-250 precedent), and list_commands must fail-soft to bundled, never raise.
  - @manager Proposed, awaiting go/no-go. Drafting ≠ greenlight; TASK-257 stays blocked until accepted + approach confirmed. 256/258/259/262 proceed in parallel meanwhile.
- [2026-06-30T12:09:56Z] `manager` Catherine Manager:
  - Accepted Option 3 (lazy-dispatch root TyperGroup à la AddressDispatchGroup): keeps the built-in command path at pure import so non-custom squads are byte-identical by construction (AC#7/#8), with a fail-soft list_commands override enumerating custom types from the resolved spec. Rejected resolve-at-import (correctness hole, can't see --dir) and argv-pre-scan (degrades completion). Greenlit for TASK-257.
- [2026-06-30T12:13:23Z] `architect` Robert Architect:
  - Post-acceptance cleanup done (per @manager): (1) status banner rewritten — now reads Accepted, Option 3 selected, TASK-257 unblocked, no go/no-go/greenlight framing; (2) frontmatter description updated to past-tense 'Accepted: chose the lazy-dispatch TyperGroup …'; (3) every .squads.toml occurrence corrected to .overrides/workflow.toml (the FEAT-209 F2 canonical, verified at _loader.py:42); (4) the 'stays blocked on this ADR' dependency line + closing line updated to reflect acceptance. Options analysis / recommendation / --help+unknown-command resolution kept intact. Re-scanned the full body: no Proposed / go-no-go / .squads.toml leftovers. The earlier Proposed-era comment is left as-authored (append-only discussion record). Note: FEAT-210's body has the same stale .squads.toml wording I copied from — flagged to @manager for routing to the PO.
- [2026-06-30T12:14:54Z] `architect` Robert Architect:
  - Second cleanup pass done (per @manager, overriding the prior banner-rewrite instruction): (1) DELETED the entire opening STATUS blockquote — the body now starts straight at ## Context. Status is sq-managed metadata (frontmatter status:), never restated in body prose, so it can't go stale. (2) frontmatter description: stripped of all status words — now 'How to register sq <custom-type> as a top-level CLI command … chose the lazy-dispatch TyperGroup', a pure what-it-decides summary. (3) removed every other lifecycle/workflow-state phrase from the body: the 'Accepted:'/'unblocked' Consequences bullet, the 'stays blocked / this ADR accepted' dependency wording, and the closing 'This ADR is Accepted' line — the body now describes only the decision + rationale. .squads.toml→.overrides/workflow.toml correction from the prior pass stands. Re-scanned the full body (excluding the append-only discussion log): the only 'Accepted' left is the frontmatter status: field, which is where it belongs.
- [2026-10-25T21:14:54Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the decision (lazy root TyperGroup) is unchanged. Removed the pre-implementation code description (ItemType enum, TYPE_ALIASES in _enums.py, line numbers), the --dir option analysis and the dated ADR-1009 note; folded in what the code does today (_CustomTypeGroup in _cli/__init__.py: static loop ordered by ItemSpec.order, aliases from ItemSpec.aliases, build_item_app(str), resolve_spec_for_ctx order with -C, spec-keyed command cache, dropped bundled types and stale aliases hidden, spec_error_command on a failed override, _CustomCreateGroup sharing the pattern). Dropped the TASK/AC planning sections.
<!-- sq:discussion:end -->
