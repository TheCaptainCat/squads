---
id: BUG-771
sequence_id: 771
type: bug
title: sq sync silently discards an operator-set role name
status: Verified
author: qa
severity: high
refs:
- BUG-756
- REV-770
created_at: '2026-08-21T21:03:56Z'
updated_at: '2026-08-22T09:06:07Z'
---
<!-- sq:body -->
Driven on release/0.14, fresh throwaway squad, no override files:

    sq init --name architect="Ada Lovelace"
      ROLE-000002-architect.md   title: Ada Lovelace, extra.full_name: Ada Lovelace
      CLAUDE.md                  - **Ada Lovelace** — architect (`architect`)
      .squads.toml               [init.names] architect = "Ada Lovelace"

    sq sync                      (exit 0, no warning, no skipped-line report)
      ROLE-000002-architect.md   title: Robert Architect, extra.full_name: Robert Architect
      CLAUDE.md                  - **Robert Architect** — architect (`architect`)
      sq list -t role            ROLE-2 … Robert Architect
      index (.squads.json)       title: Robert Architect, extra.full_name: Robert Architect
    sq check                     exit 0

Total, silent loss: nothing on disk still says "Ada Lovelace" except `.squads.toml`'s
`[init.names]` table, which `sq sync` never reads.

## The pre-existing/new split, re-driven (not inherited)

Same sequence, driven in a `git worktree` at `v0.13.0` (`ea891a6`): after `sq sync`,
`extra.full_name` and the generated roster/pointer have already reverted to "Robert Architect",
but `item.title` (frontmatter and index) still holds "Ada Lovelace", and so does `sq list -t
role`. `sq check` exits 0 there too.

So 0.13.0 already lost half of this on the first sync — the `extra` copy, the roster, and the
`.claude/` pointer never carried the operator's name past init. What the role-projection commit
(`03c0802`, closing BUG-756) added is propagating that already-stale `extra.full_name` into
`item.title` — the one field that had, until now, still been correct — destroying the last
surviving copy. The projection is not the root cause and did not introduce the revert; it
completed it, and in doing so removed the one field `sq repair` (which trusts markdown over
the index) could have used to heal from.

## Root cause, verified in source rather than restated

`_refresh_catalog_extra` (`_services/_maintenance.py`) builds a merge base for the sync-time
resolution: `dev_base = dev_base_from_item(item) if item.extra.get(X.IS_DEV) else None`. For
every non-dev role this is unconditionally `None`.

That already loses the item's stored identity, but even patching the caller to build a base
the way `dev_base_from_item` does would not be enough on its own:
`resolve_role_with_base(slug, squad_dir, *, base)` reads:

    predefined = _PREDEFINED_BY_SLUG.get(slug)  # None for new slugs
    effective_base = predefined if predefined is not None else base

For any bundled slug, `predefined` is never `None`, so `effective_base` is unconditionally the
bundled catalog entry regardless of what `base` the caller passed — a non-dev role's own stored
identity has no path into this function at all, only a project override file does (via the
`.overrides/roles/<slug>.toml` branch a few lines below, which merges *onto* `effective_base`
rather than replacing it). The asymmetry is structural in two places, not one.

`[init.names]` confirmed unread outside `sq init`: it is written in
`_models/_config.py`/consumed in `_cli/_main.py` (the prompt/flag/config merge) and
`_services/_service.py` (creation time only) — no other module references it. It sits on disk,
correct, and nothing after `init` ever looks at it again.

Asymmetry confirmed by driving the mirror case: `sq dev add --tech python --name "Grace
Hopper"` then `sq sync` keeps "Grace Hopper" everywhere (title, extra, `CLAUDE.md`) — because
`item.extra.get(X.IS_DEV)` is true for that role, so `dev_base_from_item` supplies a base built
from the item's own stored name, and dev slugs are never in `_PREDEFINED_BY_SLUG` so that base
is not discarded by the bundled-slug shortcut above. The dev-role half of this exact function
already does, structurally, what the non-dev half needs.

## Renamed (override-declared) vs operator-named: different outcomes today

Driven side by side, one squad: `sq init --name architect="Ada Lovelace" --name qa="Sam
Reeves"`, then an `.overrides/roles/qa.toml` declaring `full_name = "Sam Reeves"` (qa only).
After `sq sync`: `architect` (name set only via `--name`/`[init.names]`, no override file) is
lost, back to "Robert Architect"; `qa` (identical name, but also present in an override file)
survives everywhere. The distinguishing factor is only whether an override file exists for
that slug — the operator-naming paths described in the docs below never create one.

## Docs promise the opposite, in so many words

`docs/overrides.md`, "Agent naming" → "How names flow into your squad" (the section
immediately following "Naming at initialization" and "Naming roles after init", which document
exactly `sq init --name`/`[init.names]`/the interactive prompt and `sq role activate --name`):

> The chosen name is stored in the ROLE item's frontmatter (`extra.full_name`). Everything
> downstream reads from there:
> - The **Agent roster** in your `CLAUDE.md` (generated by `sq sync`).
> - The **agent pointer files** in `.claude/` (e.g., `.claude/agents/architect.md`).
> - The rendered **role body** in `squads/agents/roles/ROLE-*.md`.

All three bullets are driven false for every non-dev naming path above. `docs/roles.md` does
not repeat this promise: it documents only `sq dev add --name` (correctly durable, per the
asymmetry above) and mentions `sq role activate <slug>` without `--name` at all — so the false
guarantee lives in exactly one place, but it is the place an adopter reading about naming is
pointed to.

## Scope: which name-setting paths are affected

Lost on the next `sq sync`, driven:
- `sq init --name <slug>=<Name>` (declarative flags)
- `[init.names]` in `.squads.toml` (config file)
- the interactive naming prompt at a TTY (merges into the same `combined_names` map as the two
  above, confirmed by reading `_cli/_main.py`'s prompt loop, so it is subject to the identical
  loss even though it was not separately driven)
- `sq role activate <slug> --name "…"` — driven: `sq role activate devops --name "Hank Ops"`
  then `sq sync` reverts to "Hugo Ops" everywhere, `sq check` exit 0

Not affected, driven:
- `sq dev add --tech <t> --name "…"` — a dev role's name is durable (the asymmetry above)
- a name declared in `.overrides/roles/<slug>.toml` (`full_name = "…"`), for either a bundled
  or a developer role — this is BUG-756's fixed path and remains correct; it is what recovery
  below relies on

## Recovery for an already-damaged squad

Two sources survive the loss, driven, and between them cover every affected path:

- `.squads.toml`'s `[init.names]` table is never cleared or pruned by `sq sync` -- confirmed
  `architect = "Ada Lovelace"` was still there after the sync that reverted the live item -- but
  it exists only for names set at `sq init` (flags, config, prompt); `sq role activate --name`
  never writes it (driven: `.squads.toml` after `sq role activate devops --name "Hank Ops"` has
  no `[init.names]` entry for `devops` at all, before or after the reverting sync).
- `squads/.reflog.jsonl` carries the role's original `create` op with the operator's name in its
  `delta`, for **either** path -- driven: after `sq role activate devops --name "Hank Ops"` then
  a reverting `sq sync`, the reflog's `create` line for that role still reads
  `"delta":{"title":"Hank Ops",...}` untouched, because the reverting sync writes no reflog entry
  of its own (it is itself an instance of the "invisible to recency surfaces" gap noted below).
  This is the one recovery source that also covers `sq role activate --name`, which
  `[init.names]` does not.

Recovery, driven from either source: write the recovered value into
`.overrides/roles/<slug>.toml` as `full_name = "<the name>"` and run `sq sync` -- this heals
`title`, `extra.full_name`, the index, `CLAUDE.md`, and the `.claude/` pointer together, `sq
check` stays clean, and the name now holds because the override file (the one path this bug
does not break) is what every future sync consults.

Squarely on point: this exact defect, including both recovery sources above and a fuller
resolution-order design, is now also recorded as amendments A1-A3 on ADR-754 (dated after this
finding, read while preparing this bug) -- independent corroboration from the architect's own
pass, not something this bug needed to re-derive. A3 there additionally rules explicitly
against an automatic heal on `sync` (it would resurrect a name in a squad where the adopter
later changed it deliberately) and proposes `sq check` reporting the divergence instead of
repairing it -- a report-not-repair direction worth carrying into whatever fixes this.

## Two smaller observations from the same seam (recorded, not the focus here)

- The projection touches neither `item.updated_at` nor `modified_session`, so a silent revert
  is invisible to `sq board`/reflog/any recency-based surface.
- Once the projection has written a dev role's overridden name into `extra.full_name`, deleting
  the override file no longer reverts it — correct per the partial-dev-override change's own
  contract, but it means an override's effect on a dev role is now one-way.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T21:09:24Z] Catherine Manager:
  - Drove the recovery question directly to settle a disagreement between QA and the tech lead. On a squad initialized with a role subset, sq role activate devops --name Hank Ops activates Hank Ops, the reflog create entry carries that name, sq sync then reverts the item to Hugo Ops, and the reflog still carries Hank Ops afterwards. So the activate path IS recoverable from squads/.reflog.jsonl, and the reverting sync writes no reflog entry of its own to clobber it. The tech lead is right and this body needs correcting.
  - Also recording a probe error of my own so nobody repeats it: activating a role that sq init already made live is a documented no-op that returns the existing item untouched, so --name appears to be ignored. It is not a defect. Use sq init --roles minimal and activate a role that is not yet live when driving this.
- [2026-08-21T21:37:04Z] Catherine Manager:
  - Fix landed in cc6c506 on release/0.14 (TASK-772). Four sites plus a stale docstring, not the two the review found: the same IS_DEV gating pattern also sat in sq role show and sq check. Verified myself on a minimal-roster squad: role activate architect --name Ada Lovelace survives two consecutive syncs across frontmatter, index, sq list and the CLAUDE.md roster; an override declaring full_name still renames over it, so tier 1 still wins; sq check exits 0. The catalog-refresh guard passes, which is what proves the fix did not freeze the whole definition. Full suite green with --run-slow at 3818 passed, pyright and ruff clean.
- [2026-08-21T21:37:07Z] Theo Writer:
  - Docs for the exposed gap landed in docs/overrides.md: a new "Which name wins" section under Agent naming states the three-level precedence (override full_name > the name stored on the role, however set > bundled catalog / dev pool), what sync keeps vs refreshes, that a rename moves updated_at and shows in the reflog, and the recovery for a squad already showing the bundled name (write full_name into the override, sync once). Also noted three traps in the same section and cross-referenced from docs/roles.md.
  - Driven in throwaway squads: init --name, [init.names] (needs init --force when the file pre-exists; flag beats table; table is init-only), activate --name on a not-yet-live role, dev add --name/--model — all survive three syncs; tampered mission/responsibilities/can_spawn/model/skills on a bundled role are all restored from the catalog while full_name is held; a developer keeps its --model too; an override full_name renames over a stored name once (updated_at moves, reflog logs old->new) and deleting the override afterwards does NOT restore the previous name.
  - One doc-relevant behaviour worth a look: activating an already-live role reports success and silently ignores --name. Documented as a trap; @reviewer if that should refuse instead.
- [2026-08-21T21:42:29Z] Mara Tester:
  - Verified against the bug's own reproduction on cc6c506, all in throwaway squads. Both name-setting paths, each on a genuinely not-yet-live role (sq init --roles minimal then activate, avoiding the no-op trap): sq init --name architect="Ada Lovelace" and sq role activate devops --name "Hank Ops".
  - Two consecutive syncs, every surface (frontmatter title/extra.full_name, index, sq list -t role, sq role show, CLAUDE.md, AGENTS.md, .claude/agents/<slug>.md): both names held identically after sync #1 and #2. sq check clean throughout.
  - Tier 1 confirmed on both role kinds: an override declaring full_name still renames over an operator-set name -- devops Hank Ops -> Zoe Ops via override, and a dev role (python-dev) Grace Hopper -> Zoe Python via override, both applied on sync.
  - Tier 3 confirmed: sq role qa show with no override/item resolves to the bundled default (Mara Tester); dev_base_for_slug('rust-dev') resolves to the pool name (Elias Python-style pick, verified 'Elias Rust' directly against the resolver) for a dev slug with no item -- the CLI's role show blanks that preview to null by design (a different, intentional mechanism, read in _cli/_role.py's _dev_preview_full_name, not a defect).
  - The regression check I most wanted to drive myself: hand-staled extra.mission/responsibilities/can_spawn (plus the matching frontmatter) on an operator-named architect item, then ran one sync. All three reconverged to the current bundled catalog values on that same sync, while extra.full_name/title stayed "Ada Lovelace" throughout -- the fix is narrow, not a whole-definition freeze.
  - sq dev add --name remains durable across two syncs, unregressed (Priya Dotnet held).
  - Visibility confirmed: the mission/responsibilities/can_spawn reconvergence bumped updated_at and appended a real reflog update entry with the exact before/after delta; a pure full_name override-rename did the same (Hank Ops -> Zoe Ops logged). In both cases the role's original create reflog entry, carrying the operator's chosen name, stayed intact and readable directly above the update entry -- confirms the recovery path BUG-771's own body describes still holds.
- [2026-08-22T09:06:07Z] Pierre Chat:
  - Not filing the activate --name no-op. Activating an already-live role reports success and silently discards a --name the operator passed; it is documented as a trap in docs/overrides.md and that is where it stays for now. Do not re-raise it as a defect without new evidence that an adopter hit it.
<!-- sq:discussion:end -->
