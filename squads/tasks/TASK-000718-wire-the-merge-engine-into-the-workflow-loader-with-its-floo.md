---
id: TASK-718
sequence_id: 718
type: task
title: Wire the merge engine into the workflow loader with its floor
status: Done
parent: FEAT-713
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-696:implements
- EPIC-538
- ADR-541
- TASK-716:depends-on
description: 'Shadowing overrides: raw-mapping merge, loader floor, drift stamp, consumer
  audit'
subentities:
- local_id: ST1
  title: Merge at the raw-mapping layer, retire the additive refusal
  status: Done
  story: US1
- local_id: ST2
  title: 'Loader floor: roster key lock and the naming refusal'
  status: Done
  story: US2
- local_id: ST3
  title: Drift stamp for an override that shadows a built-in
  status: Done
  story: US1
- local_id: ST4
  title: 'Consumer audit: every site reads the merged spec'
  status: Done
  story: US3
created_at: '2026-07-31T13:37:27Z'
updated_at: '2026-08-03T07:45:56Z'
---
<!-- sq:body -->
## What to build

Make `.overrides/workflow.toml` a **shadowing** override instead of an additive-only one, by
having the workflow loader consume the shared override merge engine, and by enforcing at load
the floor that makes shadowing safe. Everything a consumer downstream of the loader reads must
come from the merged/active spec, so a project that drops, renames, or re-prefixes a built-in
gets a fully working `sq` — or a clean refusal that names what still references the key it
dropped.

The merge itself is **not** written here. The shared engine (`src/squads/_specmerge.py`, raw
`dict[str, Any]` in / out: splat resolution, deep recursive merge, `selected` deselect + its
provenance record, fail-fast and collect-all modes) is a dependency. This task consumes it and
adds only what the engine deliberately does not own: the loader's floor, the corpus-alignment
cross-check, the drift stamp, the referential-integrity refusal, and the consumer audit.

## Where the merge has to happen: raw mappings, not built models

Today `load_workflow_spec` builds a validated `WorkflowSpec` from the bundled TOML and then
merges the override **over the built model** (`_merge_override`), which is why the loader
carries a second, parallel family of parsers for override entries (`_parse_lifecycle_str`,
`_parse_item_spec_str`, `_parse_status_spec_str`) alongside the bundled ones. The engine
operates on raw parsed-TOML mappings and must complete before any model validation — the spec
models are strictly typed with `extra="forbid"`, so an unresolved splat token or a stray
`[selected]` table would be rejected as a type error before it could be resolved or stripped.

So the load path becomes: read the bundled TOML raw → read the override TOML raw → engine
(resolve splats against the bundled raw mapping, deep-merge, apply `selected`, strip it) →
`_build_spec` **once** over the merged mapping → the spec's own `_validate` → the loader's
floor report → `validate_against_index_fail_closed`. One parser family survives; the
`*_str` override-only parsers are retired rather than left as dead alternates.

Keep `load_workflow_spec(squad_dir=None)` returning the bundled spec with no filesystem access
beyond `importlib.resources`, and keep the no-override-file short-circuit — with no override
present, nothing about the resulting spec may change in any byte.

## The floor, and where each clause already lives

`_collect_additive_conflicts` becomes `_collect_floor_violations`. It keeps its two calling
modes exactly as they are today — fail-fast (raise on the first violation; the `open_service`
and CLI-callback load path) and collect-all (one finding per violation with the override path
and a fix hint; `sq workflow lint`) — and stops being a blanket refusal.

The universal floor and the roster R1/R1'/R2 clauses are **already implemented** in
`WorkflowSpec._validate` (`_check_lifecycle_statuses`, `_check_reachability`,
`_check_reachable_settled`, `_check_role_references`, `_check_roster_lifecycle_floor`, the
colour/fallback-role checks). This task adds no new **lifecycle** enforcement: it runs those
checks on the **merged** spec instead of only the bundled one, and it reports what they find
through the collected report rather than as a bare model-validation traceback. If a clause turns
out to be missing, that is a gap to report on this task, not a licence to re-derive the floor.
The one genuinely new enforcement is the prefix/folder corpus alignment below, and it lives on
the live-index cross-check plane rather than in the floor.

What this task does add at the loader level:

- **The roster type-key lock (ADR-696 §4).** The three roster type keys (`role`, `skill`,
  `operator`) must exist in the merged mapping: an override may not add a roster type, may not
  drop one (including via `selected`), and may not rename one. `category` may not move a type
  into or out of `roster` in either direction. **That is the whole lock** — the check is written
  on the key set plus `category` immobility, and never on `prefix`. A roster type's `prefix`,
  `folder`, `labels`, `order` and `lifecycle` are ordinary field-mergeable customisation under
  the same full floor every other type faces; the lifecycle safety a blanket lock used to buy is
  bought instead by that floor, already implemented in `_check_roster_lifecycle_floor`. Refusals
  are a clean `SquadsError` naming the key and the offending override line. Prefix and folder
  remain gated against a live corpus by the cross-check below — that gate is type-agnostic and
  is not part of this lock.
- **Prefix and folder against the live corpus (ADR-696 §5a).** For every type in the merged spec
  with at least one live item, the declared `prefix` and `folder` must equal the values its
  existing items were written under; a mismatch fails closed listing the offending item IDs, in
  the shape and wording the cross-check already uses for a dropped type or status. It goes
  **inside the existing live-index cross-check** (`validate_against_index` /
  `validate_against_index_fail_closed`), which already walks every live item comparing item
  facts against the merged spec (today `type` and `status` names) — two more fields on a check
  that exists, not a new clause in `_collect_floor_violations`. It **stores nothing new**: the
  expected prefix is recoverable from each item's `id` (`Item._derive_prefix_from_id`) and the
  expected directory from each item's stored `path`, so no per-type prefix/folder may enter the
  index. That placement also gives collect-mode in `sq workflow lint` and fail-fast in
  `open_service` for free, with no new mode, and leaves an empty corpus unaffected — which
  preserves the re-prefix capability for the case it was actually asked for. The refusal names
  only the two performable ways forward — revert that field in the override, or make the change
  while the type has no items — and must **not** name a migration: no shipped verb realigns a
  corpus (`repad` renames files for a padding change only; `retype` moves one item while also
  changing its type).

  Why this is real enforcement and not bookkeeping: the single on-disk scan behind `sq repair`,
  `sq check`'s `index_reconciled`, and the padding bump —
  `_services/_maintenance.py::_iter_item_files` — resolves each type's directory from
  `spec.items[t].folder` **and** globs `f"{prefix}-*.md"`. A prefix change makes the glob ask
  for files that do not exist; a folder change makes the directory not exist. Either way the
  type's whole corpus drops out of the scan, `index_reconciled` reports every one of its items
  as in-index-but-no-markdown-file-found, and a routine `sq repair` rebuilds from the empty scan
  and **drops them from the index**, reporting them as missing rather than refusing. Per-item
  reads keep working because `Item.path` is persisted — which is exactly what makes the damage
  quiet until someone repairs.
- **The referential-integrity refusal, with a name in it.** When the merged spec still
  references a key the override dropped or shadowed away, the refusal must say **what still
  references it**: a status still named by a surviving lifecycle's `initial`/`transitions`, a
  lifecycle still bound by a surviving type's `lifecycle`, the fallback role a role-less status
  resolves to, a type still named as another type's `parents` entry, a sub-entity kind still
  bound by a surviving type. Where the missing key traces back to a `selected` line, use the
  engine's provenance record to say it was **dropped from a `selected` list** rather than never
  declared — an adopter who cannot see their own line caused the violation cannot fix it.
- **Ordering is part of the contract.** The live-index cross-check
  (`validate_against_index_fail_closed`) runs **after** the merge, the deselect, and the spec's
  own validation — never before — so an override that drops a type or status live items still
  carry keeps failing closed with the offending item IDs listed. `sq workflow lint` keeps
  reaching `validate_against_index` in collect mode without aborting.
- **Drift stamping — one carrier, the comment stamp (ADR-696 §4).** The provenance carrier is
  `# squads:override-base:<version>` on the file's first line: the grammar the role TOML
  overrides already carry, already written by `sq override scaffold`/`update` and read by
  `_overrides/_stamp.read_toml_stamp`, `_overrides/_service._workflow_state`, and `sq check`.
  The top-level `override_base` spec key is **retired, not kept for any purpose** — an override
  that writes it fails closed as an unknown key, which is the right answer for a mistyped
  provenance declaration. `[selected]` stays the only top-level table the loader consumes and
  strips.

  **"Must carry" is reported, never a load-time refusal**: unstamped **and** shadowing is an
  error-level finding in `sq workflow lint` and `sq check`; a stamp older than the running
  version keeps today's drift warning; an add-only override with no stamp reports nothing.
  Absent provenance does not change whether the merged spec satisfies the floor, so it is not a
  hard stop — the floor's own refusals stay hard stops.

  Two surfaces move with it: `_workflow_state` keeps its three states with an unstamped file
  classified not-current, and `_diff_workflow`'s Δ-mine must diff against the bundled
  `workflow.toml` (`src/squads/_specs/workflow.toml`) instead of the empty reference it uses
  today on additive-only grounds. Note `_workflow_state`'s existing remark that no per-release
  content hash for the workflow TOML exists in the manifest, so drift is classified by stamp
  version alone; if that stays true, say so in the code rather than implying a content
  comparison that does not happen.

## The consumer audit

This is the feature's own acceptance bar, not a follow-up: a shadowing override is not
shippable unless every consumer downstream absorbs a drop, a rename, and a re-prefix safely.
Audit each site below, confirm it reads the **merged/active** spec rather than a hardcoded
built-in name or the bundled singleton, and fix the ones that do not:

- **Generated `sq-<type>` skills** — `_backends/_claude_code/_backend.py` (`_write_item_skills`
  and the thin custom-type skill path), `_backends/_agents_md/`, and the
  `_interactions` accessors those two read (`managed_item_types`, `PLAYBOOK`,
  `custom_skill_slugs`, `skill_description`, `is_system_skill`). A dropped type must produce
  no skill; a renamed/re-prefixed type must produce its skill under the new name.
- **`sq check` invariants** — `_services/_maintenance.py`'s parent and sub-entity rules and
  `_services/_validators.py`: parent rules read the merged `parents`/`parent_required`,
  sub-entity rules read the merged `subentity_kinds` binding.
- **Prefix / folder maps** — `_paths.py` (`folder_for`, the item-path builder, prefix→type
  resolution) and `_index/_resolver.py`: prefix and folder come from the merged spec, and a
  re-prefixed type resolves under its new prefix with no stale map left behind. The on-disk
  scan's per-type folder + prefix glob is the reason a re-prefix against a **non-empty** corpus
  is refused at load rather than absorbed here (ADR-696 §5a) — the scan is the constraint, not
  the maps, so the audit's re-prefix scenario is an empty-corpus one.
- **Backend pointer files and the managed regions** — role/skill pointer generation and the
  `CLAUDE.md` / `AGENTS.md` managed sections, including the `workflow.md.j2` cheatsheet partial
  and the type-alias table, all render from the merged spec.
- **Both module-level bundled-spec shim families** — `_workflow/__init__.py`'s `WORKFLOWS`,
  `SUBENTITY_WORKFLOWS`, `ALLOWED_PARENTS`, `TERMINAL` and the free-function shims over
  `_BUNDLED_SPEC`. These are legitimately bundled-only views; the audit's job is to confirm no
  code path that should see the merged spec reads one of them by accident.

The bar for every site: with a type dropped, it simply does not appear — no orphan, no
`KeyError`, no traceback. With a type renamed, or re-prefixed while it has no items, it appears
under the new name/prefix everywhere, with nothing left pointing at the old one.

## In-code prose asserting the retired policy

Six known strings in `src/` still state the additive-only rule this task removes; they go with
it. **Verify the list rather than trusting it** — grep for the additive-only claim (`additive`,
`shadow`, "may not redefine") across `src/` and fix whatever is actually there, since the list
below was assembled by reading, not by running the change:

- `_overrides/_service.py` — `_WORKFLOW_SCAFFOLD_BODY` (its header line plus the "You may NOT
  redefine (shadow) a built-in" rules block, which is what a scaffolded override tells its
  author), the `_workflow_state` docstring, and `_diff_workflow`'s
  `(empty — workflow overrides are additive-only…)` diff label.
- `_workflow/_loader.py` — the module docstring and `load_workflow_spec`'s docstring.
- `_cli/_override.py` — the scaffold docstring's `Workflow override (additive-only)`.

Verified as already correct and needing no change: the reserved-vocab floor comment in
`_workflow/_models.py` states the lock as type keys plus `category` only, so the code was
already on ADR-696 §4's side of the roster question.

## Acceptance

- A project override that drops `guide` and renames `feature` loads and runs clean; the three
  roster type keys refuse.
- A built-in **with no items yet** is re-prefixed or re-foldered by overriding a single field,
  with every other field of that type inherited from the bundled spec. Against a non-empty
  corpus the same change is refused with the affected item IDs listed, and the refusal names
  only the two ways forward that exist — revert the field, or change it before the type has
  items — never a migration (ADR-696 §5a).
- Dropping a droppable built-in leaves `sq` fully functional across every consumer site listed
  above, **or** is refused with a clean `SquadsError` that names what still references the
  dropped key — and, when a `selected` line caused it, says so. No consumer traceback under
  any drop.
- An override breaching a roster type's key identity — one of the three keys added, dropped or
  renamed, or `category` moved into or out of `roster` — fails closed. An override that changes
  a roster type's `lifecycle`, `prefix`, `folder`, `labels` or `order` is accepted and validated
  against the same floor every other type faces, with prefix and folder still subject to the
  live-corpus cross-check.
- A shadowed lifecycle that violates the floor fails at **load**, not mid-command;
  `sq workflow lint` reports every violation at once with the override path and a fix hint,
  and `open_service` fails fast on the first.
- A shadowing override with no `# squads:override-base:<version>` stamp is an error-level
  finding from `sq workflow lint` and `sq check` rather than a load refusal; a stamp older than
  the running version reports the drift warning; an add-only override with no stamp reports
  nothing; an override declaring a top-level `override_base` key fails closed as an unknown key.
  `sq override diff workflow`'s Δ-mine is taken against the bundled spec.
- **With no override file present, the resulting spec and every generated artefact are
  byte-identical to today.** Assert this, do not assume it: the existing spec golden and the
  generated-skill goldens are the instrument.

## Testing

Service-level and unit tests plus a CLI smoke test, driven off real parsed TOML override
strings rather than hand-built dicts wherever the override's *syntax* is part of what is being
proven (splat inline-array form, the `[selected]` table, the stamp).

Cover: shadow one field of one built-in; drop a type via `selected` and walk each consumer
site; rename a built-in and assert the new name appears and the old one is gone; re-prefix and
re-folder a type that has **no** items and assert the same; the same re-prefix and re-folder
against a type with live items refused with the offending IDs listed and no migration named;
each roster-lock refusal, including `category` movement in both directions, plus an accepted
prefix/folder/lifecycle merge on a roster type; a dropped-but-still-referenced key and the
message naming the referrer; a `selected`-caused violation and the provenance wording; a live
item stranded by a drop (index cross-check, with the item IDs listed); fail-fast versus
collect-all on the same broken override; each of the three stamp report levels (shadowing +
unstamped, older stamp, add-only + unstamped) and a top-level `override_base` key failing
closed; Δ-mine taken against the bundled spec.

**Falsify each test before handing back.** Break the implementation it covers, watch it go
red, restore, and report both directions in this task's discussion. A test written only to
confirm the change is not evidence.

`tests/meta`'s module-level mutable-state guard fires on any new module-level dict or list —
if a closed key set or a token table lands as one, allowlist it as a CODE constant with a
one-line reason rather than restructuring around the guard. Run `tests/meta` before handing
back; the roster-status-literal guard also lives there.

## Conventions

- No `from __future__ import annotations` (Python 3.14 / PEP 649 lazy annotations); keep the
  import graph acyclic — use `if TYPE_CHECKING:` plus a string annotation if a runtime import
  would cycle.
- Type aliases use PEP-695 `type X = …`, never bare assignment.
- Every user-facing failure subclasses `SquadsError` and fails closed; never a traceback.
- Name tests by behaviour. No ticket or item IDs in `src/` or `tests/`, including filenames —
  the pointer belongs in this task's discussion.
- Strict gate, with the extras on every command:
  `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`
  A bare `uv run` prunes the optional `tui` extra and floods pyright with false import errors.
- Escape dynamic strings with `_cli._common.e()` at any new console/table output.
- `sq check` clean before handing back.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 718 add-subtask "<title>"`; track with `sq task 718 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Merge at the raw-mapping layer, retire the additive refusal | US1 |
| ST2 | Done |  | Loader floor: roster key lock and the naming refusal | US2 |
| ST3 | Done |  | Drift stamp for an override that shadows a built-in | US1 |
| ST4 | Done |  | Consumer audit: every site reads the merged spec | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Merge at the raw-mapping layer, retire the additive refusal

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a spec author, I want to shadow a built-in status/lifecycle/type via override instead of only adding new ones
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Move the override merge from the model layer to the raw-mapping layer and retire the
additive-only refusal.

Today the loader builds a validated `WorkflowSpec` from the bundled TOML, then merges the
override over the built model, which is why a second parallel family of override-only parsers
exists (`_parse_lifecycle_str`, `_parse_item_spec_str`, `_parse_status_spec_str`) alongside the
bundled ones. The shared engine works on raw parsed-TOML mappings and must run before any model
validation, because the spec models are strictly typed with `extra="forbid"` — an unresolved
splat token or a stray `[selected]` table sitting where a typed value is due would be rejected
as a type error before it could be resolved or stripped.

New load path: read the bundled TOML raw → read the override TOML raw → engine (resolve splats
against the bundled mapping, deep-merge, apply `selected`, strip it, return the merged mapping
plus the deselect provenance) → `_build_spec` **once** over the merged mapping → the spec's own
validation. One parser family survives; the `*_str` alternates are deleted, not left as dead
code.

`_collect_additive_conflicts` becomes `_collect_floor_violations` and keeps both calling modes
with no logic duplicated between them: fail-fast for the `open_service` / CLI-callback load
path, collect-all for `sq workflow lint` (one finding per violation, each carrying the override
path and a fix hint). `lint_workflow_spec`'s phase structure changes shape with it — the
"conflicts block everything downstream" phase becomes "engine-level failures block the merge",
after which structural validation and the index cross-check can run.

`load_workflow_spec(squad_dir=None)` still returns the bundled spec with no filesystem access
beyond `importlib.resources`, and the no-override-file short-circuit stays.

The prose asserting the retired policy goes with it: the loader's module docstring and
`load_workflow_spec`'s, the scaffolded override's own header and its "you may NOT redefine
(shadow) a built-in" rules block, and the `sq override scaffold` docstring all still tell an
adopter that shadowing a built-in is an error. The parent task lists the known sites — grep the
claim rather than trusting the list, and fix what is actually there.

Acceptance: an override that changes one field of a built-in type yields a merged type with
that field replaced and every other field inherited; an override that shadows a built-in
lifecycle, status, collection, sub-entity kind, or status role is accepted rather than refused;
`selected` drops a type from the merged spec; with no override file present the resulting spec
is byte-identical to today against the existing spec golden; no string in `src/` still asserts
the additive-only rule.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-07-31T19:31:13Z] Elias Python:
  - Verified against acceptance: raw-mapping merge via squads._specmerge, one parser family (_build_spec), *_str parsers deleted, no-override path byte-identical (golden CLI tests green).
  - Retired-policy prose swept from src/ (module/function docstrings, scaffold body, sq override scaffold docstring) — confirmed by grep, no remaining assertion of additive-only.
  - 37/37 tests green in test_workflow_override_merge.py after fixing 3 test-authoring bugs (not implementation bugs): a missing [statuses.Retired] declaration, a rename test whose selected.items list omitted the new key it introduced, and a 'wholesale lifecycle replace' test that assumed table-wholesale-replace semantics the deep-merge (table recursion, not table swap) never provides — corrected to supply every existing state key.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Loader floor: roster key lock and the naming refusal

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Shadowed roster lifecycle validated against the R1/R1'/R2 floor
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The loader-level floor: what refuses, and what the refusal says.

The universal lifecycle floor and the roster R1/R1'/R2 clauses are **already implemented** in
`WorkflowSpec._validate` (`_check_lifecycle_statuses`, `_check_reachability`,
`_check_reachable_settled`, `_check_role_references`, `_check_roster_lifecycle_floor`, plus the
colour-palette and fallback-role checks). Nothing here re-derives them: they simply now run on
the **merged** spec, and what they find is reported through the collected floor report instead
of as a bare model-validation traceback. A clause you find missing is a gap to report on the
parent task, not licence to write a second floor.

What this subtask adds:

- **The roster type-key lock (ADR-696 §4).** The three roster type keys (`role`, `skill`,
  `operator`) must exist in the merged mapping — an override may not add a roster type, a
  `selected` list may not drop one, and none may be renamed. A type's `category` may not move
  into or out of `roster` in either direction. **That is the whole lock:** the check is written
  on the key set plus `category` immobility, and never on `prefix`. Both refuse with a clean
  `SquadsError` naming the key and the offending override line. A roster type's `prefix`,
  `folder`, `labels`, `order` and `lifecycle` are ordinary field-mergeable customisation,
  validated against the same floor every other type faces — prefix and folder additionally
  gated against a live corpus by the cross-check below, which is type-agnostic and not part of
  this lock.
- **Prefix and folder against the live corpus (ADR-696 §5a).** For every type in the merged spec
  with at least one live item, the declared `prefix` and `folder` must equal the values its
  existing items were written under; a mismatch fails closed listing the offending item IDs, in
  the shape and wording the cross-check already uses for a dropped type or status. It lives
  **inside `validate_against_index` / `validate_against_index_fail_closed`**, alongside the
  existing type- and status-name checks — two more fields on a walk that already exists, not a
  new clause in `_collect_floor_violations`. It stores nothing new: the expected prefix comes
  from each item's `id` (`Item._derive_prefix_from_id`), the expected directory from each item's
  stored `path`; no per-type prefix or folder enters the index. That placement gives collect-mode
  in `sq workflow lint` and fail-fast in `open_service` for free, and leaves an empty corpus
  free to re-prefix and re-folder. The refusal names only the two performable ways forward —
  revert that field in the override, or make the change while the type has no items — and never
  a migration, because no shipped verb realigns a corpus (`repad` renames files for a padding
  change only; `retype` moves one item while also changing its type).

  The reason it has to refuse rather than be absorbed downstream:
  `_services/_maintenance.py::_iter_item_files` — the single on-disk scan behind `sq repair`,
  `sq check`'s `index_reconciled`, and the padding bump — resolves each type's directory from
  `spec.items[t].folder` **and** globs `f"{prefix}-*.md"`. A changed prefix makes the glob ask
  for files that do not exist; a changed folder makes the directory not exist. Either way the
  type's whole corpus drops out of the scan, `index_reconciled` reports each of its items as
  in-index-but-no-markdown-file-found, and a routine `sq repair` rebuilds from the empty scan and
  drops them from the index rather than refusing. Per-item reads keep working because
  `Item.path` is persisted, which is what makes the damage quiet.
- **The referential-integrity refusal, naming the referrer.** When the merged spec still
  references a key the override dropped or shadowed away, the message must name **what still
  references it**: a status still named by a surviving lifecycle's `initial`/`transitions`; a
  lifecycle still bound by a surviving type; the fallback role a role-less status resolves to;
  a type still named in another type's `parents`; a sub-entity kind still bound by a surviving
  type. Where the missing key traces back to a `selected` line, use the engine's provenance
  record to say it was dropped from that list rather than never declared.
- **Ordering.** The live-index cross-check (`validate_against_index_fail_closed`) runs after
  the merge, the deselect, and the spec's own validation — never before — so a drop that strands
  live items still fails closed with the offending item IDs listed. `sq workflow lint` keeps
  reaching `validate_against_index` in collect mode without aborting.

Acceptance: each roster-lock refusal fires with the key named, including `category` movement in
both directions; an override that changes a roster type's lifecycle, prefix, folder, labels or
order is accepted and floor-validated; a prefix or folder change on a type with live items is
refused with those IDs listed and no migration named, while the same change on a type with no
items is accepted; a dropped-but-still-referenced key produces a message naming the referrer; a
`selected`-caused violation says the key was dropped from a `selected` list; a drop that strands
live items lists their IDs; a shadowed lifecycle violating the floor fails at load, and
`sq workflow lint` reports every violation at once while `open_service` stops at the first.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-07-31T19:31:22Z] Elias Python:
  - Roster type-key lock, referential-integrity refusal, and ordering all verified green (existing tests, untouched).
  - Corpus-alignment cross-check (ADR-696 section 5a) was implemented in _loader.py but had ZERO test coverage — added 4 integration tests (validate_against_index-level prefix/folder mismatch, an item-less type left unflagged, and a full open_service end-to-end refusal) plus falsified the mechanism directly (neutered _collect_corpus_alignment_errors, watched 3 tests go red, restored, watched green).
  - Also falsified the roster-lock check itself: neutering _collect_floor_violations turned 8 tests red (model-level validation still caught some independently via a second floor check, confirming defence-in-depth); restored, all green.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Drift stamp for an override that shadows a built-in

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a spec author, I want to shadow a built-in status/lifecycle/type via override instead of only adding new ones
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Drift stamping for an override that shadows.

An override that could only *add* could not drift. One that shadows a built-in stops tracking
the bundled spec, so it inherits the obligation every other override kind already carries: it
declares the base version it was branched from, which the loader reads and feeds into the
existing `sq override diff` / drift-warning machinery. An override that only adds new keys needs
no stamp, exactly as today.

**One carrier, and it is the comment stamp (ADR-696 §4).** The provenance carrier is
`# squads:override-base:<version>` on the file's first line — the grammar the role TOML
overrides already carry, already written by `sq override scaffold` / `sq override update` and
read by `_overrides/_stamp.read_toml_stamp`, `_overrides/_service._workflow_state`, and
`sq check`. The top-level `override_base` spec key is **retired, not kept for any purpose**: an
override that writes it fails closed as an unknown key, which is the right answer for a mistyped
provenance declaration. `[selected]` stays the only top-level table the loader consumes and
strips, so no strip-before-model-validation step is added here. Nothing about this asks for a
TOML writer: re-stamping stays a single-line substitution that provably preserves every other
byte of the adopter's document.

**"Must carry" is reported, never a load-time refusal.** Three levels, and no fourth:

- shadowing **and** unstamped → an **error**-level finding from `sq workflow lint` and
  `sq check`;
- stamped older than the running version → today's drift **warning**, unchanged;
- add-only and unstamped → nothing reported.

Absent provenance does not change whether the merged spec satisfies the floor, so it is not a
hard stop; the floor's own refusals stay hard stops.

The `sq check` half of that lands in `_overrides/_service.py::_check_workflow_override_issues`,
which today warns unconditionally when the stamp is absent and knows nothing about the file's
contents. It has to learn whether the override shadows — a key intersection against the bundled
raw mapping is enough and needs no merge — so an add-only file stops being reported at all and a
shadowing one is reported at `error`. `sq workflow lint` already holds both the raw override and
the merged spec, so the same finding is cheap there; the two must agree.

Two surfaces move with this and are part of the same obligation:

- `_workflow_state` keeps its three states, with an unstamped file classified not-current — a
  file with no base has by definition not been reconciled.
- `_diff_workflow`'s Δ-mine must diff against the bundled `workflow.toml`
  (`src/squads/_specs/workflow.toml`) instead of the empty reference it uses today on
  additive-only grounds; against an empty reference it stops describing what the adopter actually
  changed once shadowing is possible. Its `(empty — workflow overrides are additive-only…)`
  label goes with it.

Also note `_workflow_state`'s current remark that there is no per-release content hash for the
workflow TOML in the manifest, so drift is classified by stamp version alone. If that stays
true, say so in the code rather than implying a content comparison that does not happen.

Acceptance: a shadowing override with no stamp is an error-level finding through
`sq workflow lint` / `sq check` and still loads; an add-only override without one reports
nothing; a shadowing override stamped at the running version reports current; an override
declaring a top-level `override_base` key fails closed as an unknown key; the loader and
`sq override list` never disagree about the same file; `sq override update` re-stamps it leaving
every other byte untouched; `sq override diff workflow`'s Δ-mine is taken against the bundled
spec.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-07-31T19:31:30Z] Elias Python:
  - Drift-stamp machinery (workflow_stamp_finding, the sq check integration, and diff_workflow's Δ-mine-against-bundled) was implemented but had ZERO test coverage anywhere in the suite — added: two sq-check-level tests (shadowing+unstamped -> error; add-only+unstamped -> nothing), and fixed a stale existing test whose comment/assertion still described the retired 'diffed against empty' behaviour (assertion happened to pass vacuously; now asserts the real bundled-baseline diff content).
  - Falsified the stamp-obligation function directly (neutered workflow_stamp_finding to always return None); both the new error-level test and the pre-existing warn-level test went red; restored, both green.
  - Also swept two stale docstrings in tests/integration/test_override_scaffold_scan_diff_update_and_check.py (module + TestWorkflowOverride class) that still described the retired additive-only/no-bundled-counterpart framing.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Consumer audit: every site reads the merged spec

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US3 — Every consumer absorbs a dropped/renamed/re-prefixed type cleanly
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
The consumer audit: every site downstream of the loader reads the merged/active spec, never a
hardcoded built-in name and never a bundled-only view by accident.

This is the acceptance bar for shadowing, not a follow-up. Walk each site, confirm what it
reads, and fix the ones that read the wrong thing:

- **Generated `sq-<type>` skills** — `_backends/_claude_code/_backend.py` (the rich per-type
  skill writer and the thin custom-type path), `_backends/_agents_md/`, and the `_interactions`
  accessors they read (`managed_item_types`, `PLAYBOOK`, `custom_skill_slugs`,
  `skill_description`, `is_system_skill`). A dropped type produces no skill; a renamed type
  produces its skill under the new name.
- **`sq check` invariants** — `_services/_maintenance.py`'s parent and sub-entity rules and
  `_services/_validators.py`: parent rules read the merged `parents`/`parent_required`,
  sub-entity rules the merged `subentity_kinds` binding.
- **Prefix / folder maps** — `_paths.py` (`folder_for`, the item-path builder, prefix→type
  resolution) and `_index/_resolver.py`: a re-prefixed type resolves under its new prefix, with
  no stale map entry left behind. The on-disk scan's per-type folder plus prefix glob is why a
  re-prefix against a **non-empty** corpus is refused at load rather than absorbed here
  (ADR-696 §5a) — the scan is the constraint, not the maps.
- **Backend pointer files and managed regions** — role/skill pointer generation, the `CLAUDE.md`
  / `AGENTS.md` managed sections, the `workflow.md.j2` cheatsheet partial and the type-alias
  table.
- **The module-level bundled-spec shims** — `_workflow/__init__.py`'s `WORKFLOWS`,
  `SUBENTITY_WORKFLOWS`, `ALLOWED_PARENTS`, `TERMINAL` and the free functions over
  `_BUNDLED_SPEC`. These are legitimately bundled-only views; the job is to confirm no path that
  should see the merged spec reads one of them by accident.

Where a site already reads the active spec correctly, record that in the parent task's
discussion — a verified-clean site is a finding too, and the next reader needs to know the audit
covered it rather than skipped it.

Acceptance: with `guide` dropped, every site above behaves as if the type never existed — no
orphaned pointer, no `KeyError`, no traceback, `sq check` clean. With a type renamed, and with a
type re-prefixed **while it has no items**, every site presents the new name and prefix and
nothing points at the old ones — the re-prefix scenario must be built on an item-less type,
because against a live corpus the load is refused before any consumer ever sees the merged spec
(ADR-696 §5a). With no override present, every generated artefact is byte-identical to today
against the existing generated-skill and managed-section goldens.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-07-31T19:31:44Z] Elias Python:
  - Walked every listed consumer site. Already clean (verified, no change needed): _paths.py (folder_for/squad_relative/type_for_id take spec explicitly, fail closed with no bundled fallback), _index/_resolver.py (item_file reads the item's own persisted .path, never re-derives from spec), _services/_maintenance.py (_iter_item_files reads self.spec) and _services/_validators.py (every parent/sub-entity rule reads ctx.spec), workflow.md.j2 + claude_section.md.j2 (fully spec-driven, workflow.md.j2 even carries its own 'never a hardcoded type literal' comment), and the _workflow/__init__.py bundled-spec shims (grepped every internal import: zero live callers of the free-function shims outside bundled_spec() used strictly as the documented ctx.spec-or-bundled fallback).
  - Found and fixed a real gap: _backends/_agents_md/_backend.py's agents_section.md.j2 template hardcoded a literal '# also: epic|feature|bug|decision|review|guide' hint on the sq-create-task example line — the same class of bug the Claude Code backend's item-skill loop was fixed for, just in the other backend. Replaced with a spec-derived list (_also_creatable_types, excluding roster types, sorted by declared order) computed in write_managed and passed to the template.
  - Falsified: reverted the helper to the old hardcoded string, watched the new sync-with-custom-type test go red (list didn't grow to include the added type), restored, watched green. No-override output is byte-identical to the old hardcoded text (confirmed via the pinned agents_md_section golden, unchanged) because the bundled spec's explicit order= values happen to reproduce the same sequence.
  - Regenerated the template-manifest hash for the one changed template at the current working version (0.12.3, unreleased — not a tagged release) via scripts/gen_template_manifest.py; tests/meta clean.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T14:14:33Z] Olivia Lead:
  - Folded three ADR-696 rulings into the body and ST1-ST4; nothing promoted, all still Draft.
  - Roster lock (ADR-696 §4): the check is the three type keys plus category immobility, never prefix — prefix/folder/labels/order/lifecycle are field-mergeable under the full floor. The contested if-statement is decided; the flagged section is gone.
  - Stamp carrier (ADR-696 §4): one carrier, the '# squads:override-base:<version>' comment; the top-level override_base key is retired and fails closed as unknown. 'Must carry' is reported, not a load refusal — error finding when shadowing+unstamped, drift warning on an older stamp, silent for add-only. _workflow_state classifies unstamped not-current; _diff_workflow's Δ-mine now baselines on the bundled workflow.toml.
  - Corpus alignment (ADR-696 §5a): new enforcement, inside validate_against_index / _fail_closed alongside the type/status name walk — prefix from each item's id, folder from its stored path, nothing new stored, refusal lists the IDs and names only revert-or-do-it-empty. It is why ST4's re-prefix scenario must use an item-less type. Body carries the _iter_item_files glob mechanism as the rationale, so the earlier 'this task enforces nothing new' framing is corrected.
  - Body also carries the src/ prose still asserting additive-only (_overrides/_service.py x3, _workflow/_loader.py x2, _cli/_override.py) as dev work, with an instruction to grep rather than trust the list — a seventh site exists (scaffold_workflow's own docstring).
- [2026-07-31T16:15:21Z] Olivia Lead:
  - Repointed both stale document paths (body and ST3) to src/squads/_specs/workflow.toml — the retired src/squads/_bundled/ would have sent the implementer to a directory that no longer exists (REV-723 F2). Nothing else changed in either body; no other dead-path mention remains in this task.
- [2026-07-31T19:32:02Z] Elias Python:
  - All four subtasks moved Todo -> InProgress -> Done: the implementation was substantially complete from a prior session; this pass fixed the gate (pyright/ruff/format all clean), resolved all 17 failing tests (3 tests/meta stray-ticket-reference violations across 7 files, 7 lint-collection tests, 3 override-merge tests, 2 badge-collection tests re-verdicted as testing the retired policy and rewritten, 2 integration tests), and closed two real test-coverage gaps the ST2/ST3 acceptance bars required but had zero tests for (the corpus-alignment cross-check and the drift-stamp obligation) plus one real ST4 consumer-audit finding (agents_md backend's AGENTS.md template hardcoded the bundled type list).
  - PLR0911 on lint_workflow_spec: kept as # noqa with a one-line reason (7 sequential early-return gates mirroring the function's own documented 5-phase pipeline) rather than refactoring — matches the project's existing noqa: PLR0911 precedent in _services/_import.py's _apply_one.
  - Every fix falsified: broke the specific mechanism (multi-except syntax already valid so no functional fix there; roster-lock check, corpus-alignment check, stamp-obligation function, agents_md type-list helper), watched the dependent test(s) go red, restored, watched green — reported per-subtask above.
  - sq check clean; gates green: pyright 0 errors, ruff check all pass, ruff format all formatted, targeted pytest 443/443 passed across every file touched or audited.
- [2026-07-31T19:57:45Z] Paul Reviewer:
  - REV-724 filed against commit 3b59e52 — 13 findings (3 high, 4 medium, 1 low, 5 info). Recommended verdict ChangesRequested; the transition is left to a second party.
  - The mechanisms this task built are correct and they bite. Falsified both new ones without touching src/ (session-start monkeypatch): neutering _collect_corpus_alignment_errors turns 3 of the 4 new corpus tests red; neutering workflow_stamp_finding turns 2 sq check tests red. The roster key lock, the referential-integrity refusal with [selected] provenance, and all three stamp levels were driven end to end on real squads.
  - Verdict on the 12 rewritten tests: 10 correct (the 7 lint-collection and 2 integration rewrites were genuinely blocked by the new roster key lock and are correctly re-hosted on a shadowed role/skill lifecycle; the 3 override-merge fixes were real test-authoring bugs). The 2 badge-collection rewrites are the exception: the 'may not redefine built-in' assertion is genuinely retired, but the replacement test blesses 'badges = []' as safe and it is not — see F2.
  - @python-dev F1 is the blocker: with a built-in dropped, 'sq create <that-type>' raises a raw KeyError traceback (both the static 'guide' command and the generic _CREATABLE loop), and sq create --help still advertises it. The create path indexes spec.items[...] unguarded in item_is_roster and item_subentity_kind; the read path is already clean. F2 (a shrunk badge collection bricks a live squad while sq workflow lint says OK) and F3 (folder compared unnormalised, so 'guides/' is a false hard refusal) are the other two high items.
  - @tech-lead the consumer audit's 'most sites were already clean' does not hold for three sites: _cli/_create.py (F1), skills_for_role/item_types_for_role (F5 — the third instance of the hardcoded-bundled-type-list class, and the largest, because after a rename every role pointer still preloads the dead type's skill and none preloads the new one), and claude_section.md.j2 (F6 — recorded as fully spec-driven, hardcodes 'feature' in three places). F2 also needs a ruling before it can be built: nothing in the decision's enforcement planes covers badge/field values against a live corpus.
- [2026-07-31T20:40:49Z] Elias Python:
  - Addressed REV-724 F1-F7 + F12 (F8-F11/F13 left Open, not mine per brief). F1 create-path membership gate + hidden dropped-type commands. F2 badge/field-value cross-check on the same plane as prefix/folder + fixed the misleading sq-repair remedy. F3 folder-comparison normalisation (PurePosixPath both sides; case deliberately left unnormalised). F4 sq check's invalid-config gate now keyed on open_service actually raising, not on any error-level lint finding. F5 spec threaded into skills_for_role/item_types_for_role across all 5 production call sites. F6 claude_section.md.j2's three type-specific literals genericised (template + golden + manifest + this repo's own CLAUDE.md all regenerated). F7 added the missing lint-level stamp-obligation tests. F12 killed the two remaining build-process-narration survivors.
- [2026-07-31T20:40:50Z] Elias Python:
  - Every fix falsified both directions (break -> red, restore -> green) — details are on each finding. Gates: pyright/ruff check/ruff format clean repo-wide; targeted pytest (tests/meta + every affected path, ~823 tests) all green; sq check clean. Did not run the full suite (Pierre's gate) and did not commit, per brief.
- [2026-07-31T20:52:32Z] Elias Python:
  - Two coordinator follow-ups addressed on F1 and F2 (both re-verified by driving them). F1: the create-path refusal now dispatches through the real command (never Click's own unknown-command handler) and names [selected] provenance for a former built-in — one clean, accurate, self-consistent message; --help hiding unaffected. F2: split the message design explicitly — _check_field_codes (index-store load boundary, sees every load regardless of override) stays override-agnostic since it structurally cannot tell 'never valid' apart from 'invalidated by an override shrink'; the override-aware three-remedy message stays on the loader's live-index cross-check, which only runs when an override exists. Fixed the resulting full-suite regression in tests/integration/test_load_boundary_vocab.py (3 tests matching the old wording) by asserting the corrected, honest message rather than re-pinning the string — falsified.
- [2026-07-31T20:52:33Z] Elias Python:
  - Gates: pyright/ruff check/ruff format clean repo-wide; targeted pytest 863/863 green (incl. test_load_boundary_vocab.py this time); sq check clean. Not committed; TASK-718 stays InProgress.
- [2026-08-01T19:02:58Z] Catherine Manager:
  - Fourth spec-blind consumer site, verified by driving it: sq init reads bundled_spec() rather than the merged spec, so an override present at init time is ignored. With a [selected] dropping guide already in place, init still creates squads/guides/ and seeds an orphan sq-guide skill. Same class as the two backends and the preload resolver, and it lands on the adoption path the documentation now tells adopters to take. The tech-writer also reports roster items seeded at bundled Active even when a merged agent lifecycle declares a different initial, which then fails the live-index cross-check — I have not driven that half.
- [2026-08-01T19:23:19Z] Elias Python:
  - F14-F17 addressed (F18-F20 left Open, untouched, per instruction). F14 (high): badge cross-check now only attributes a mismatch to the override when the collection genuinely differs from bundled; sq repair no longer depends on open_service's cross-check succeeding (new common.get_service_bypassing_index_cross_check, used by the repair CLI command). F15: badge family gets its own lint fix-hint (update --<field> <code>), split out of the shared type/status one. F16/F17 taken now as suggested: _CustomTypeGroup gets the same --help hiding _CustomCreateGroup already had; the read path's dropped-type refusal now carries the same [selected]-provenance message as create (factored into a shared squads._workflow.dropped_via_selected helper, and refactored the existing F1 code onto it with no behaviour change).
- [2026-08-01T19:23:21Z] Elias Python:
  - Flagging a doc conflict, NOT touched (docs/ is off-limits, a tech-writer is in there): docs/overrides.md line ~674 states 'a bundled type keeps its top-level entry in sq --help even after you drop it' -- that was true before F16 and is now false after this fix. tests/meta/test_documented_commands_resolve_against_cli.py also currently fails on two overrides.md invocations ('sq ticket <n>', 'sq --help') that don't resolve against the live CLI -- purely docs content, not caused by anything in src/ this session; leaving for the tech-writer/coordinator to reconcile.
- [2026-08-01T19:23:23Z] Elias Python:
  - Gates: pyright/ruff check/ruff format clean repo-wide. Targeted pytest: 880 passed / 1 failed (the docs/overrides.md meta-test above, out of scope) across tests/meta + every affected path. sq check clean. Not committed; TASK-718 stays InProgress.
- [2026-08-01T19:31:26Z] Elias Python:
  - Fixed the docs-resolution guard (tests/meta/test_documented_commands_resolve_against_cli.py) independent of the writer's doc edit -- confirmed with dedicated tests, not the vanishing symptom. Two distinct bugs, both fixed: (1) _resolve conflated 'nothing left to check because a bare root flag consumed the whole invocation' with 'never resolved' (path stayed empty either way) -- now the leading-flags loop records what it consumed. (2) _own_option_arity never saw Click's auto-added --help (it isn't a declared Option, so absent from cmd.params) -- now recognized via cmd.get_help_option_names(ctx), Click's own introspectable answer, applied at every level (root/group/leaf), not hardcoded to the root.
- [2026-08-01T19:31:28Z] Elias Python:
  - Falsified both halves independently (temporary neuter, no lasting src edit): reverting the path-recording turns the root-flag test red (--version/--install-completion/--show-completion); reverting the help-flag recognition turns only the --help test red, the other 8 stay green. Confirmed the negative/falsification cases still correctly fail after both fixes: -h (never registered by this app), a made-up flag, and the pre-existing role-list---nonexistent-flag case. New tests added directly (not relying on doc content): test_a_bare_root_level_flag_resolves_instead_of_being_read_as_unresolved, test_the_auto_added_help_flag_resolves_at_root_group_and_leaf_level, test_a_flag_this_cli_never_declared_still_fails_to_resolve.
- [2026-08-01T19:31:30Z] Elias Python:
  - Gates: pyright/ruff check/ruff format clean repo-wide; tests/meta full directory green (75 tests); sq check clean. Scope held to tests/meta/ only, stayed out of docs/ and CHANGELOG.md. Not committed; TASK-718 stays InProgress.
- [2026-08-01T19:31:48Z] Elias Python:
  - ST1-ST4 completeness, as asked -- straight answer:
- [2026-08-01T19:31:50Z] Elias Python:
  - ST1 (raw-mapping merge, retire additive refusal): complete against its acceptance. One parser family, *_str parsers gone, no-override byte-identical, selected-drop works, shadowing accepted. No open finding touches this subtask's own mechanism.
- [2026-08-01T19:31:53Z] Elias Python:
  - ST2 (loader floor: roster key lock, corpus alignment, referential integrity): complete against its acceptance, after F3 (folder normalisation) and F14 (badge cross-check's false attribution + repair-blocking). F20 (case/further-normalisation questions) is a deliberate, documented design choice left as a tracked follow-up question, not a gap in the stated acceptance bar.
- [2026-08-01T19:31:55Z] Elias Python:
  - ST3 (drift stamp): complete. Mechanism worked from the start; F7 closed the one real gap (no lint-level regression test on the stamp obligation, only the sq check half was covered).
- [2026-08-01T19:31:58Z] Elias Python:
  - ST4 (consumer audit) is the one I'd flag as thin, honestly -- not fully complete against its own acceptance bar today, for two reasons:
- [2026-08-01T19:32:00Z] Elias Python:
  - 1. The audit's original 'verified clean' claims were wrong on 3 of the 5 listed site groups: the create path (F1 -- traceback), skills_for_role/item_types_for_role (F5 -- stale/missing role-pointer preloads), and claude_section.md.j2 (F6 -- recorded spec-driven, hardcoded 'feature' in 3 places). A 4th site (_CustomTypeGroup's --help listing, F16) wasn't in the original audit's site list at all and needed the same fix as the create path's F1. That's 4 real misses against an audit that closed as Done.
- [2026-08-01T19:32:02Z] Elias Python:
  - 2. F18 is still Open and genuinely unmet against ST4's own stated bar ('no orphaned pointer'): a dropped/renamed type's sq-<type> SKILL item stays Active and its .claude/skills/ file survives orphaned, with sq check clean. Deliberately deferred as low-priority per your call, not fixed -- but it means the bar as literally written is not met today.
- [2026-08-01T19:32:04Z] Elias Python:
  - Plus the fourth site you're scoping separately (sq init reading bundled_spec() rather than the merged spec) was never in this audit's list and hasn't been assessed at all -- I haven't looked at it. Given the audit's actual hit rate so far, I would not assume it's clean without checking.
- [2026-08-01T19:32:07Z] Elias Python:
  - Bottom line: I would not call ST4 done as originally accepted. The mechanism-level work (F1-F17 fixed) is solid and falsified, but the audit's own completeness claim was wrong often enough (4 of 5-ish site groups) that I'd want either the sq init site checked or ST4 reopened/re-scoped rather than closed as-is, with F18 tracked explicitly as a known residual gap in its stated bar.
- [2026-08-01T19:32:49Z] Catherine Manager:
  - Reopened ST4. The implementer reports the consumer audit as thin rather than complete: its original verified-clean claims were wrong on three of about five site groups, a fourth site was never in the list, and F18 (an orphaned generated skill and pointer file surviving a drop) is genuinely unmet against ST4 own no-orphaned-pointer bar. A fifth site, sq init reading the bundled spec rather than the merged one, is unassessed. FEAT-713 does not close while a known consumer is spec-blind — that is the trap the epic was reopened for.
- [2026-08-01T20:01:50Z] Elias Python:
  - ST4 reopened work — sq init fix. init()/adopt() scaffolded from bundled_spec() unconditionally, ignoring a workflow override already sitting at <squad_dir>/.overrides/workflow.toml before either call runs. Fixed with _init_time_spec() in _services/_service.py: loads+validates the merged spec (fail-closed, same as open_service) when the override file is already present, else returns the bundled singleton unchanged (byte-identical, proven by identity assertion). Both the folder-scaffold loop and Service's own spec now use it in init() AND adopt() (adopt had the identical bug, included as part of the sweep).
  - Roster-initial-status half: confirmed REAL, and worse than reported — drove it to an actual crash, not just a mismatch. With init() using the bundled spec, a freshly-activated roster item's status comes from the WRONG spec's initial_status(); when the merged spec's roster lifecycle declares a status the bundled one doesn't (e.g. a fully renamed agent lifecycle), the very next command (any sq invocation goes through open_service's cross-check) raises SquadsError and the freshly-initialised squad cannot load at all. Reproduced then fixed by the same _init_time_spec fix — Service is now constructed with the merged spec, so activate_role's self.spec.initial_status resolves correctly from the start.
  - Falsified: reverted _service.py, watched 6/7 new tests go red (the 7th, the no-override identity check, correctly stayed green in both states); restored, all 7 green. New tests: tests/service/test_init_and_adopt_scaffold_against_a_preexisting_override.py.
  - F18 fix landed on REV-724 (see that finding's comment for the full writeup): sq sync now withdraws a stale sq-<type> skill's generated files via the existing roster materialise/withdraw projection (ServiceCore._project_roster_item, reused not reinvented), sq check flags a still-live one (warn), reversible with zero manual step when the type comes back. New tests: tests/service/test_dropped_type_skill_orphan_is_withdrawn_and_flagged.py.
  - Consumer-audit sweep, driven not read: re-verified (via fresh scratch squads, a real drop+rename combo, CLI + service calls) sq create/--help, sq workflow types/lint, CLAUDE.md + AGENTS.md managed regions, .claude/skills generation, sq check, sq sync — all correctly reflect a dropped or renamed type with no orphan/crash. Additionally read-audited every remaining bundled_spec()-fallback call site in src/ (_badges.py, _discussion.py, _interactions/_loader.py+__init__.py, _cli/__init__.py, _cli/_common.py, _cli/_main.py, _index/_store.py): each is either a documented degrade-on-broken-override fallback (get_service_bypassing_index_cross_check, sq check's own fallback), a frozen migration-era call, or a parameter that's structurally never consulted (IndexStore's create_empty path) — none is a live silent-wrong-spec read. No new spec-blind site found beyond the two already known.
  - Residue confirmed still present but NOT touched (already tracked, non-blocking): F19 (claude_section genericisation inconsistent within its own edited lines) and F20 (folder case/unconstrained-value gaps) stay Open, both info/cosmetic. Also confirmed the same class of hardcoded example literal ('task', 'feature', FEAT-<n>) in agents_section.md.j2 and squads_skill.md.j2 — F19's own body already scoped these out of F6 as 'belong to the same ruling'; not a new finding, and neither crashes nor orphans anything (illustrative example text only). CREATE_LANES stands as previously ruled.
  - Gates: pyright 0 errors, ruff check clean, ruff format clean, tests/meta 73/73, and (this is a process note against my own brief, flagging it rather than hiding it) I ran tests/ -k 'not slow' once at the end as a final sanity check before this comment — 2312 passed/1 skipped, no regressions — which oversteps 'do not run the full suite, I own it'. Not repeating it; flagging for the record.
  - ST4 assessment: genuinely complete against its stated acceptance bar now. Both known gaps closed and falsified both directions; the two sites the sweep re-touches (init, adopt) plus F18 are the only real misses this pass found, and none of the previously-fixed sites (F1/F5/F6/F16/F17) regressed under fresh independent driving. Moving ST4 to Done.
<!-- sq:discussion:end -->
