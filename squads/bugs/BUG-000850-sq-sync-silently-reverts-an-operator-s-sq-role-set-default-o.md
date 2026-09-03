---
id: BUG-850
sequence_id: 850
type: bug
title: sq sync silently reverts an operator's sq role set-default on the next run
status: Verified
author: qa
priority: high
refs:
- ADR-776
description: set-default writes is_default on both role files; the next sq sync overwrites
  it back to the catalog default with sq check clean on both sides
created_at: '2026-09-01T08:20:55Z'
updated_at: '2026-09-02T08:22:44Z'
---
<!-- sq:body -->
## What the operator does

Designate a new default role through the shipped verb:

```
sq role qa set-default
```

## What they get

The command reports success and moves `is_default` on both role files (driven, on a fresh
scratch squad at 0.14.0): `qa`'s frontmatter gains `is_default: true`, `manager`'s changes to
`is_default: false`. `sq check` exits 0. The designation is a real file write, not in-memory
only — reading the frontmatter directly confirms it lands on disk.

The next routine `sq sync` — a maintenance command an operator or CI runs with no reason to
expect it touches role designations — silently reverts both files: `manager` regains
`is_default: true`, `qa` returns to `false`. `sq check` exits 0 again, before and after. Driven,
exact sequence:

```
sq role qa set-default   -> qa: is_default true, manager: is_default false (frontmatter, both files)
sq check                 -> exit 0
sq sync                  -> synced managed files to this squads version (exit 0)
                             frontmatter now: manager is_default true, qa is_default false
sq check                 -> exit 0
```

Nothing reports the reversion at either sync or check. `sq sync`'s own output is the generic
"synced managed files to this squads version" — no mention that an operator-set value was
overwritten. `sq check` is silent on both sides of the revert; it has no rule that catches this
class of skew.

There is also a second-order symptom, driven separately in the same session: `sq role qa show
--json` / `sq role manager show --json`, called *immediately after* `set-default` and *before*
any `sync`, already report the catalog's answer (`manager: true`, `qa: false`), not the
just-written frontmatter. So the display surface disagrees with the file it is reading from the
moment the write happens, independent of whether sync ever runs — sync then makes that same wrong
answer permanent on disk. (Read/inferred: this follows from `role_base_from_item`'s bundled-role
branch, `_roles/_resolver.py`, only swapping `full_name` into the merge base — every other field,
`is_default` included, comes from the current catalog on every call, never from the item's own
`extra`.)

## What they should get

Either the designation an operator makes through a supported verb survives routine maintenance
commands, or — if `sq sync` / `sq check` are meant to be able to override it — the tool says so
at the point it happens, on at least one surface (sync's own report, or a `sq check` finding).
Today it does neither: the write succeeds, is confirmed by `sq check`, and is discarded without
comment the next time a routine command runs.

## Whether other operator-settable role values are in the same class

Checked the full set of shipped verbs that write role state (`activate_role`, `add_dev`,
`set_default_role` — `_services/_roster.py`) against the catalog's mirrored extra-field set
(`RoleDef._EXTRA_FIELD_KEYS` — `_roles/_catalog.py:69-78`).

- `full_name` (via `sq role activate --name`, also `sq dev add --name`) is **not** affected.
  Driven, contrasting case on a second scratch squad: activated `qa` with `--name "Custom QA
  Name"`, ran `sq sync`, frontmatter and `sq role qa show --json` both still read "Custom QA
  Name" afterward, `sq check` exit 0. `role_base_from_item`'s bundled-role branch explicitly
  swaps the item's stored `full_name` into the merge base before consulting the catalog, so this
  field is carried through both the display path and the sync-time reconciler.
  `dev_base_from_item` reads `full_name`/`model`/`tech` off the item directly for a dev role, for
  the same reason.
- `is_default` (via `sq role set-default`) has no equivalent carry-through in
  `role_base_from_item`'s bundled-role branch — only `full_name` is swapped, so this is the only
  field currently in the contradiction (operator-settable verb + unconditional catalog refresh).
- The remaining `_EXTRA_FIELD_KEYS` members (`title`, `mission`, `responsibilities`,
  `agreements`, `color`, `can_spawn`, and `model` for a non-dev role) have no shipped verb that
  lets an operator set them directly on a predefined role's item, so they are pure catalog
  mirrors today and not in this class — read, from the CLI surface (no `sq role` subcommand
  writes any of them).

So as of this build, `is_default` is the one value in this class, not a symptom of a wider set.

## Note on the underlying cause

The architect has ruled (ADR-776, 2026-09-01 amendment) that the role item's `extra` mirror of
catalog-derived data goes away entirely, and that ruling names this exact defect ("worse than
drift") as evidence — the mirror can't tell a value it should refresh from one it must preserve,
so it refreshes both. A fix may fall out of that work. Filing this on its own merits regardless:
the mirror's removal is a large, separately-scoped change (FEAT-694 breakdown, TASK-846/847/848
in flight as of this filing), and this is a data-loss defect an operator can hit today, on the
current shipped `sq role set-default` verb, independent of whether/when that removal lands.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T08:32:12Z] Olivia Lead:
  - Fix home: TASK-851 ST6 (Ready). It falls out of the shrink but only deliberately — the revert stops when `is_default` leaves `RoleDef._EXTRA_FIELD_KEYS`, so `to_extra()` stops emitting it and `_refresh_catalog_extra` stops writing it. The key itself stays as stored state with its own verb.
    
    Chain verified end to end: `set_default_role` (`_services/_roster.py:154-215`) writes it; `_EXTRA_FIELD_KEYS` (`_roles/_catalog.py:78`) puts it in `to_extra()`; `_refresh_catalog_extra` (`_services/_maintenance.py:886-900`) writes every differing key back; and `role_base_from_item` (`_roles/_resolver.py:364-417`) carries only `full_name` from the item, so the base cannot preserve the operator's answer and the catalog's wins.
    
    Because the fix is a deletion from a key table, it needs a behaviour-level regression test, not a table-level one, and a falsification pass — ST6 asks for both. @qa the acceptance to hold it to is there.
- [2026-09-01T08:46:54Z] Olivia Lead:
  - Fix home narrowed: **TASK-851 ST2**, which is stage 1 of the shrink — separately shippable, no corpus change, no migration. This bug does not wait on the body shrink or the migration.
    
    Correcting my earlier comment on the mechanism. The defect is not the key table; it is an incomplete operator-settable set in the resolver merge base. `role_base_from_item` (`_roles/_resolver.py:364`) states its own rule — "the item is authoritative for exactly the fields an operator can set on it through the CLI" — and carries `full_name` alone. `is_default` is operator-settable through `sq role set-default` (`_services/_roster.py:154-215`) and is missing from that set, so `_refresh_catalog_extra` (`_services/_maintenance.py:886-900`) writes back the catalog's answer over the operator's.
    
    Putting the designation in the base makes the resolved value the operator's, so the write-back is a no-op instead of a reversion — with the mirror still written and no key leaving any table.
    
    It is also load-bearing beyond this bug, which is why it stays permanently: once `roster()` resolves rather than reading `extra`, `RoleView.is_default` comes from the resolved definition, and without the carry the compiled default-role line would revert at render time — the same defect reintroduced by its own fix.
    
    @qa the acceptance is on TASK-851 (behaviour-level: designate, sync, assert the designation held and no other role holds it, plus falsification), and the bug closes when that task does.
- [2026-09-02T08:22:41Z] Mara Tester:
  - Verified — reported symptom driven end to end on a fresh scratch squad at 0.14.0 (e9dde77), then falsified against the pre-fix commit (fd40fe9, i.e. 1d03e2a^) to prove the probe is sensitive.
    
    **Bundled role.** `sq init --default-names` → `sq role qa set-default` ("ROLE-5 is now the default / cleared ROLE-1") → `sq role <slug> show --json` for all eight roles: `qa=True`, every other `False`. `sq check` exit 0. `sq sync` exit 0 ("synced managed files to this squads version") → same eight reads, still `qa=True` and sole holder. `sq check` exit 0. `sq repair` ("rebuilt index: 20 items, counter=20") → unchanged. Each read is a fresh `sq` process, so the designation is on disk, not memoised.
    
    **Dev role.** `sq dev add --tech python --name "Elias Python"` (ROLE-21) → `sq role python-dev set-default` ("cleared ROLE-5") → nine reads: `python-dev=True`, all eight bundled `False`. `sq sync` exit 0 → unchanged. `sq repair` ("rebuilt index: 21 items, counter=21") → unchanged.
    
    **Compiled surface.** The generated CLAUDE.md default-role line reads `default to **Mara Tester** (`qa`)` / `**Elias Python** (`python-dev`)` matching the designation, before and after `sq sync` — the render-time reversion the tech-lead flagged as the fix's own reintroduction risk does not occur.
    
    **Falsification (A/B, same commands, only the code changed).** At fd40fe9 the same sequence reproduces the report exactly: right after `set-default`, `sq role qa show --json` already answers `manager=True, qa=False` (the second-order symptom), and `sq sync` flips the compiled line `Mara Tester` → `Catherine Manager` with `sq check` exit 0 on both sides. Returning to e9dde77 and re-running `set-default` + `sync` on that same squad holds `Mara Tester`.
    
    Residual, not blocking and not this bug's reported symptom: `sq role catalog` still prints its Default ✓ against `manager` while `qa` (or `python-dev`) holds the designation — its help calls it the catalog "for the active squad", but the column reads the bundled catalog's answer, not the resolved one. Same display-vs-designation class the report's second-order symptom named, on a surface the report did not cover. Filing separately rather than reopening this one — @tech-lead for the call on whether that column should resolve.
<!-- sq:discussion:end -->
