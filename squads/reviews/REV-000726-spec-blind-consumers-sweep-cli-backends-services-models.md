---
id: REV-726
sequence_id: 726
type: review
title: 'Spec-blind consumers sweep: CLI, backends, services, models'
status: Approved
author: reviewer
refs:
- TASK-718
- FEAT-713
- EPIC-538
description: Findings record from a driven sweep for hardcoded workflow vocabulary
  across every spec consumer.
subentities:
- local_id: F1
  title: sq repair drops a type's items and regresses the global counter
  status: Fixed
  severity: critical
- local_id: F2
  title: Hyphenated prefix mangles filenames in renumber, repad and offset
  status: Fixed
  severity: critical
- local_id: F3
  title: Renamed sub-entity kinds lose the story-map refusal and validator
  status: Fixed
  severity: critical
- local_id: F4
  title: Hardcoded agents/skills path defeats a relocated skill folder
  status: Fixed
  severity: high
- local_id: F5
  title: The squads skill teaches task/feature/review commands that error
  status: Fixed
  severity: high
- local_id: F6
  title: AGENTS.md teaches the same dead task commands as the squads skill
  status: Fixed
  severity: high
- local_id: F7
  title: CLAUDE.md loop stops on types and statuses that may not exist
  status: Fixed
  severity: high
- local_id: F8
  title: CLAUDE.md names roster roles and subagents the squad lacks
  status: Fixed
  severity: high
- local_id: F9
  title: Role card create_lane comes from a hardcoded CREATE_LANES table
  status: Fixed
  severity: high
- local_id: F10
  title: _default.md.j2 has no sub-entity container, so add-block fails
  status: Fixed
  severity: high
- local_id: F11
  title: Dropping task deletes the priority vocabulary from the squads skill
  status: Fixed
  severity: high
- local_id: F12
  title: Custom-type skills always claim the type has no sub-entities
  status: Fixed
  severity: high
- local_id: F13
  title: Generated role and managed text hardcode the InProgress status
  status: Fixed
  severity: high
- local_id: F14
  title: Per-kind service wrappers raise a bare KeyError on a renamed kind
  status: Fixed
  severity: high
- local_id: F15
  title: Dedicated priority kwarg bypasses the declared-field gate
  status: Fixed
  severity: high
- local_id: F16
  title: A type name may shadow a built-in CLI verb and lint calls it clean
  status: Fixed
  severity: high
- local_id: F17
  title: Playbook prose in surviving skills names dropped or renamed types
  status: WontFix
  severity: medium
- local_id: F18
  title: The tech field is unreachable once the guide type is renamed
  status: Fixed
  severity: medium
- local_id: F19
  title: sq mine uses a category-blind visibility predicate
  status: Fixed
  severity: medium
- local_id: F20
  title: Item templates hardcode region tags, headings and a field code
  status: Fixed
  severity: medium
- local_id: F21
  title: The squads skill hardcodes Done/Cancelled and the visibility rule
  status: Fixed
  severity: medium
- local_id: F22
  title: retype help lists the bundled type set, not the active one
  status: Fixed
  severity: medium
- local_id: F23
  title: Priority help on built-in create/update advertises rejected values
  status: Fixed
  severity: medium
- local_id: F24
  title: sq create completion is bundled-blind while root completion is not
  status: Fixed
  severity: medium
- local_id: F25
  title: item_is_roster and eleven sibling accessors raise a bare KeyError
  status: Fixed
  severity: medium
- local_id: F26
  title: VS Code client mis-derives the role for a role-less status
  status: Fixed
  severity: medium
- local_id: F27
  title: init and adopt never seed skill items for custom or renamed types
  status: Fixed
  severity: low
- local_id: F28
  title: The squads skill lists declared sub-entity kinds, not hosted ones
  status: Fixed
  severity: low
- local_id: F29
  title: workflow_static hardcodes a retype example and ref-kind types
  status: Fixed
  severity: low
- local_id: F30
  title: Root help epilog hardcodes the type-command alias set
  status: Fixed
  severity: low
created_at: '2026-08-01T21:16:51Z'
updated_at: '2026-08-15T15:46:59Z'
---
<!-- sq:body -->
Systematic sweep for **spec-blind consumers**: code and templates that hardcode workflow
vocabulary (type names, prefixes, folders, statuses, sub-entity kinds, badge codes, role slugs)
instead of reading the active merged spec. The premise under test is that only
`role`/`skill`/`operator` are reserved — every other item type must be droppable, renameable and
re-prefixable from an adopter's `.overrides/workflow.toml`, and every consumer must follow.

## Method

Four independent sweeps, one per surface:

| Surface | Ground covered |
|---|---|
| CLI | all of `src/squads/_cli/` |
| Backends and rendering | `src/squads/_backends/`, `src/squads/_rendering/` including every template |
| Services and index | `src/squads/_services/`, `src/squads/_index/`, `src/squads/_paths.py` |
| Models, workflow, interactions, clients | `src/squads/_models/`, `_workflow/`, `_interactions/`, `_roles/`, `_migrations/`, `clients/vscode/` |

Every finding below was **driven, not read**. Around forty throwaway squads were built outside the
repo, each with a pre-placed `<squad>/.overrides/workflow.toml` exercising one override shape:
`[selected]` drops; renames (`feature`→`capability`, `task`→`job`, `guide`→`handbook`); re-prefixes
(`TASK`→`WORK`, `GUIDE`→`RUN-BOOK`); relocated folders; brand-new types (`incident`, `audit`,
`spike`); renamed sub-entity kinds (`story`→`scenario`, `subtask`→`step`, `finding`→`issue`);
a replaced badge collection (`urgent|high|medium|low` → `p0|p1|p2`); a shadowed status role; a
minimal roster; and a type name colliding with a built-in CLI verb. Each finding carries the
override placed, the command run, and the literal output observed. The repo's own `squads/` was
never touched by the sweep.

## What is recorded here

Thirty distinct gaps, deduplicated from thirty-four raw. Three defects were found independently by
more than one surface and are merged into a single finding each, citing all the evidence:

- **`sq repair` dropping a type's items and regressing the counter** — found by the services sweep
  and again by the workflow/models sweep, from opposite directions (the swallowed `SquadsError`,
  and the bypassed loader cross-check).
- **`CREATE_LANES` / `allowed_create_types`** — found at the CLI consumer (`sq role … show`) and at
  the `_interactions` table itself; the `workflow.md.j2` cheatsheet is a third consumer of the same
  table and is folded in.
- **The missing sub-entity container in `_default.md.j2`** — found three times: as a template gap,
  as a service-layer `add_block` failure, and as a spec-validator/template contract mismatch.

Three findings — the `sq repair` counter regression, the hyphenated-prefix filename mangling, and
the orphaned story maps — overlap remediation work that was already underway when this record was
written. They are filed for completeness and flagged in place; read the current code before
starting on them.

## Deliberate behaviour — confirmed sanctioned, do not "fix"

Each of these looks like a hardcoded literal on a grep and is not one. All were verified by
driving, not by trusting the comment that claims them.

**The `_migrations/` carve-out holds — this is the one that must never be "fixed".** Every
migration runner deliberately freezes its own era's vocabulary as local literal tables, with a
standing instruction at each site: `_v0_1_to_v0_2.py:46-61`, `_v0_2_to_v0_3.py:38-59`,
`_v0_5_to_v0_7.py:61-74` ("the live spec/enum must never be re-introduced here"),
`_meta_compat.py:22-26`. A migration is a point-in-time snapshot; deriving its vocabulary from the
live spec would break it retroactively. The one live import in the package —
`_meta_compat.py:16,101` calling `bundled_spec().subentity_initial(kind)` — reads the *bundled*
spec, which no adopter override can reach, so it is frozen in the way that matters. `sq migrate up`
under an override behaves. No findings filed against `_migrations/`.

Also sanctioned:

- **Roster-type literals** `role`/`skill`/`operator` throughout `_cli/`, `_services/`, and
  `clients/vscode/src/domain/reservedTypes.ts`. Driven: `[selected] items` omitting `operator` is
  refused outright ("role/skill/operator are locked by key identity"). Re-prefixing
  `[items.operator] prefix = "HUMAN"` still yields slug `op-alice` — the `op-` convention is
  slug-derived, not prefix-derived.
- **Static import-time registration of built-in type and create commands**
  (`_cli/__init__.py:404-425`, `_cli/_create.py:276-359`) — documented as deliberate so a
  non-customized squad gets byte-identical help, with the `_CustomTypeGroup`/`_CustomCreateGroup`
  pair as the dynamic complement. Root help and root completion verified correct under override.
- **`get_command` still dispatching dropped built-ins** (`_cli/_create.py:155-173`,
  `_cli/__init__.py:113-124`) — hiding them would hand the message to Click's did-you-mean.
  Verified the refusal is the accurate "dropped from a `[selected]` list" message.
- **`bundled_spec()` last-resort fallbacks** at `_cli/_common.py:71,610`, `_cli/_main.py:1379`,
  `_cli/__init__.py:93,266`, `_index/_store.py:320-323`, `_services/_service.py:129,194` — all
  documented recovery or degrade paths, none reachable with a wrong spec in a validating call.
- **`parse_category`** and **`CATEGORY_BUNDLES`** — `ItemSpec.category` is a closed `Literal`; the
  catalog is closed by design, only its per-type assignment is open.
- **`VALID_REF_KINDS`** consumers (`_cli/_items.py:426-433`, `_services/_refs.py:74-78`) — a closed
  frozenset outside the override surface.
- **`LANED_TYPES` / `in_lane_owner`** (`_services/_base.py:519-537`) — advisory only and explicitly
  best-effort; verified both directions, a renamed type simply gets no advisory.
- **Frozen playbook prose in rich `sq-<type>` skills** (`_backends/_claude_code/_backend.py:230-236`,
  `_interactions/__init__.py:261-273`) — the *membership* half is documented and correct. The
  cross-type *prose* half is not covered by that documentation and is filed as a finding.
- **`_badges.py` graceful fallbacks** (`resolve_collection`/`field_label`/`field_default`),
  **`_retype.py:27-40` `_BUNDLED_CONTAINER_HEADINGS`**, **`_subentities.py:31`
  `_DEFAULT_FINDING_SEVERITY`**, **`_models.py:884-890` `_SIDE_PRIORITY`**, **`collection()`'s
  documented raise**, and the legacy `add-story`/`add-subtask`/`add-finding` import ops that
  de-sugar to the generic `AddSubEvent(kind=…)` — all documented in place and verified to degrade.
- **Withdrawn-but-retained skill items** — dropping a type leaves its skill body on disk while
  removing both backends' pointers, and warns with a restore-or-retire instruction. Correct and
  self-documenting.

## Observed but not filed — cosmetic

Recorded so they are not re-litigated, and so a later sweep does not re-derive them:

- `_cli/_main.py:735,876` — illustrative `TASK-<n>`/`BUG-<n>` JSON-shape docstrings rendered into
  help. `_cli/_role.py:55-56`, `_skill.py:48-50`, `_operator.py:45-46`, `_main.py:971`,
  `_memory.py:55` — epilog and option-help examples naming `Archived`, `manager`, `op-pierre`.
- `_cli/_common.py:801` — an unrecognized ID prefix is reinterpreted as a bare number, so
  `sq show NOPE-1` and `sq show GUIDE-1` (dropped type) give the identical, misleading
  "is ROLE-1 (role)" message. `dropped_via_selected()` exists to tell them apart and is not
  consulted. Clean refusal, actively misleading. Borderline — classified cosmetic by the sweep;
  a triager may reasonably promote it.
- `sq import` with a dropped type gives a bare "unknown item type", where `sq create` gives the
  full `[selected]`-aware message. Same distinction available, not used.
- `_paths.py:164` `type_for_id` splits the prefix left-to-right — the same hyphen bug filed as a
  data-loss finding in this record, but with zero production callers (test-only, already a
  dead-code candidate). Delete or fix it alongside so it is not revived as a landmine.
- `templates/agents/greeting_skill.md.j2:39` — a stale `FEAT-<n>` inside a blockquote example; the
  template is rendered without `spec` in context and nothing downstream parses it.
- `templates/agents/squads_skill.md.j2:24-28` `_kind_notes` — a literal kind→hint dict consumed only
  through `.get(kind, <generic>)`; verified an undeclared kind renders the fallback text.
- `sq override scaffold items/guide.md.j2` succeeds for a type that no longer exists, with no
  warning (the inverse of a filed finding; currently harmless).
- `sq sync` mkdirs every declared folder and never prunes, so a dropped type leaves an empty folder.

## Adjacent, outside the sweep's scope

- `sq init --backend agents_md` alone produces no skill bodies at all, while the AGENTS.md it writes
  tells agents to open them. Backend parity, not spec-blindness.
- `_agents_md/_backend.py::_read_staging_role` parses only the `**Mission:**` line, so the
  `**Skills:**` line the staging template writes never reaches AGENTS.md.
- `sq check` in every override case reported "shadowing workflow override has no
  `squads:override-base` stamp" — expected for a hand-written override; it masked none of the above.

## Not exercised

`sq ui` (no headless mode found) and the VS Code extension itself. The extension's domain layer was
read statically; the one finding derived from that read plus a driven CLI half says so in its body.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 726 add-finding "…" --severity medium`; track with `sq review 726 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🔴 critical | Fixed |  | sq repair drops a type's items and regresses the global counter |
| F2 | 🔴 critical | Fixed |  | Hyphenated prefix mangles filenames in renumber, repad and offset |
| F3 | 🔴 critical | Fixed |  | Renamed sub-entity kinds lose the story-map refusal and validator |
| F4 | 🟠 high | Fixed |  | Hardcoded agents/skills path defeats a relocated skill folder |
| F5 | 🟠 high | Fixed |  | The squads skill teaches task/feature/review commands that error |
| F6 | 🟠 high | Fixed |  | AGENTS.md teaches the same dead task commands as the squads skill |
| F7 | 🟠 high | Fixed |  | CLAUDE.md loop stops on types and statuses that may not exist |
| F8 | 🟠 high | Fixed |  | CLAUDE.md names roster roles and subagents the squad lacks |
| F9 | 🟠 high | Fixed |  | Role card create_lane comes from a hardcoded CREATE_LANES table |
| F10 | 🟠 high | Fixed |  | _default.md.j2 has no sub-entity container, so add-block fails |
| F11 | 🟠 high | Fixed |  | Dropping task deletes the priority vocabulary from the squads skill |
| F12 | 🟠 high | Fixed |  | Custom-type skills always claim the type has no sub-entities |
| F13 | 🟠 high | Fixed |  | Generated role and managed text hardcode the InProgress status |
| F14 | 🟠 high | Fixed |  | Per-kind service wrappers raise a bare KeyError on a renamed kind |
| F15 | 🟠 high | Fixed |  | Dedicated priority kwarg bypasses the declared-field gate |
| F16 | 🟠 high | Fixed |  | A type name may shadow a built-in CLI verb and lint calls it clean |
| F17 | 🟡 medium | WontFix |  | Playbook prose in surviving skills names dropped or renamed types |
| F18 | 🟡 medium | Fixed |  | The tech field is unreachable once the guide type is renamed |
| F19 | 🟡 medium | Fixed |  | sq mine uses a category-blind visibility predicate |
| F20 | 🟡 medium | Fixed |  | Item templates hardcode region tags, headings and a field code |
| F21 | 🟡 medium | Fixed |  | The squads skill hardcodes Done/Cancelled and the visibility rule |
| F22 | 🟡 medium | Fixed |  | retype help lists the bundled type set, not the active one |
| F23 | 🟡 medium | Fixed |  | Priority help on built-in create/update advertises rejected values |
| F24 | 🟡 medium | Fixed |  | sq create completion is bundled-blind while root completion is not |
| F25 | 🟡 medium | Fixed |  | item_is_roster and eleven sibling accessors raise a bare KeyError |
| F26 | 🟡 medium | Fixed |  | VS Code client mis-derives the role for a role-less status |
| F27 | 🟢 low | Fixed |  | init and adopt never seed skill items for custom or renamed types |
| F28 | 🟢 low | Fixed |  | The squads skill lists declared sub-entity kinds, not hosted ones |
| F29 | 🟢 low | Fixed |  | workflow_static hardcodes a retype example and ref-kind types |
| F30 | 🟢 low | Fixed |  | Root help epilog hardcodes the type-command alias set |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sq repair drops a type's items and regresses the global counter

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🔴 Critical
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**Remediation was already underway when this was recorded — read the current code before fixing.**

Found independently by two sweeps, from opposite directions: the swallowed `SquadsError` in the
service layer, and the bypassed loader cross-check from the workflow side. Merged here.

## Site

`src/squads/_services/_maintenance.py:733-741`

```python
if self.store.exists():
    try:
        prev = await self.store.load()
        ...
        known_corpus = prev
    except Exception:  # corrupt index — treat as empty
        pass
```

`IndexStore.load()` (`src/squads/_index/_store.py:401`) calls `_validate_item_vocab`, which raises
`SquadsError` (`_store.py:168-172`) precisely when an item's type is no longer declared. The blanket
`except Exception` treats that as "corrupt index", so:

- `known_corpus = None` — the corpus-alignment refusal added for exactly this class of bug never runs;
- `previous_seq_to_id = {}` — `missing_ids` is empty, so nothing is reported;
- `previous_counter = 0` — the high-water mark is lost.

`_iter_item_files` (`_maintenance.py:532`) globs only folders declared in the *active* spec, so the
dropped type's folder is never visited and `_rebuild_index_from_disk`'s own
`if item.type not in self.spec.items: raise` guard at `:670` is unreachable too. Three
correct-looking guards cancel out. `sq repair` reaching this state at all is routed by
`src/squads/_cli/_common.py:580` `get_service_bypassing_index_cross_check`, deliberately
(documented at `_cli/_main.py:631-636`).

## Driven — item loss

Fresh squad, `GUIDE-19` and `TASK-20` created, index at 20 items; *then* `guide` dropped via
`[selected]`. The normal path refuses correctly:

```
$ sq list
error: workflow spec is incompatible with the live index — run `sq workflow lint` to see details:
  - item GUIDE-19 has type 'guide' which is not declared in the workflow spec
```

Then, with the index fully intact:

```
$ sq repair
rebuilt index: 19 items, counter=20
exit=0

$ sq check
warn SKILL-14: skill 'sq-guide' is Active but type 'guide' is no longer declared …
$ sq workflow lint
workflow spec OK — no errors or warnings.
$ ls squads/guides/
GUIDE-000019-g-one.md
```

Reflog records `"missing": []`. The item is gone from every view, the markdown sits on disk, nothing
reports it.

## Driven — counter regression, then a second item lost

Second squad, default corpus with `GUIDE-21` at the high-water mark, `guide` dropped:

```
BEFORE:  items 21  counter 21   guide entries: ['GUIDE-21']
$ sq repair
rebuilt index: 20 items, counter=20
AFTER:   items 20  counter 20   guide entries: []
$ ls squads/guides/
-rw-r--r-- 365 GUIDE-000021-g.md          <-- untouched on disk
$ sq check
warn SKILL-14: skill 'sq-guide' is Active but type 'guide' is no longer declared …
                                          (nothing at all about GUIDE-21)
$ sq reflog | tail -1
… repair  actor=system  {"items":20,"missing":[]}
```

The regressed counter then reissues the freed sequence:

```
$ sq create epic "New epic reusing 21" --author manager
squads/epics/EPIC-000021-new-epic-reusing-21.md      <-- sequence 21 reissued

$ rm squads/.overrides/workflow.toml     # adopter restores the type
$ sq repair
rebuilt index: 21 items, counter=21
$ sq show EPIC-21
error: EPIC-21 is GUIDE-21 (guide)
$ sq list | tail -1
GUIDE-21  guide  Draft  G                            <-- no EPIC-21 anywhere
$ ls squads/epics/EPIC-000021-new-epic-reusing-21.md <-- file exists, unreachable
$ sq check
error TASK-20: subtask ST1 → US9 missing from FEAT-19   (pre-existing; nothing about the epic)
```

Two items lost from the board across the sequence, both files still on disk, `sq check` green about
both. This violates the global-counter invariant directly: a sequence number was reissued.

## Recovery

`sq repair --renumber` restores both (verified: `rebuilt index: 22 items`). Nothing anywhere tells
the operator that, and nothing signals that a recovery is needed.

`docs/overrides.md` promises "A drop is refused while live items still carry the type or status,
listing the offending IDs." One `sq repair` bypasses that promise silently.

## Note

This is the same shape as the already-fixed re-folder repair bug. The guard added for that fix is
intact and was verified not regressed on its own trigger (`sq adopt` with a re-prefixed guide on
disk correctly refuses, naming `GUIDE-21`). This is a different trigger reaching past the same guard.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-01T21:27:05Z] Paul Reviewer:
  - Recorded as in-flight: a fix for this was already being implemented when the finding was filed (uncommitted changes present under src/squads/_services/ and src/squads/_index/). Verify against current code before starting work, and close this as Fixed citing the change rather than re-fixing it.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Hyphenated prefix mangles filenames in renumber, repad and offset

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🔴 Critical
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Remediation was already underway when this was recorded — read the current code before fixing.**

## Sites — four hand-rolled prefix parsers, all in `_services/_maintenance.py`

- `:797` `file_prefix, _, digits_slug = stem.partition("-")` — `repad`
- `:840` `slug = stem.split("-", 2)[2]` — `_scan_records`
- `:868` `fid_prefix = fid.split("-", 1)[0]` — `_renumber_plan`
- `:998` `fid_prefix = fid.split("-", 1)[0]` — `_offset_plan`

`ItemSpec.prefix` is a bare `str` with no shape validation, and `sq workflow lint` accepts a
hyphenated prefix ("workflow spec OK — no errors or warnings"). The correct shared primitive
already exists and is hyphen-safe: `squads._models._item.prefix_from_id` uses `rpartition("-")`.
These four re-derive it in the opposite direction.

```
models.prefix_from_id('RUN-BOOK-19')  -> 'RUN-BOOK'
maintenance split('-',1)[0]           -> 'RUN'
_scan_records slug                    -> '000019-how-to-deploy'
repad prefix/digitrun                 -> 'RUN' / 'BOOK'  (isdigit: False)
```

## Override

`[items.guide] prefix = "RUN-BOOK"`, `folder = "runbooks"`, placed before any item existed — the
legal way to re-prefix.

## Driven

```
$ sq create guide "How to deploy" --author architect
squads/runbooks/RUN-BOOK-000019-how-to-deploy.md
$ sq check   →  ✓ no issues        (everything normal so far)

$ sq migrate repad 8
repad done: padding 6 → 8; 18 file(s) renamed; index rebuilt
$ ls squads/runbooks/ ; ls squads/agents/roles/ | head -1
RUN-BOOK-000019-how-to-deploy.md          <-- still width 6, silently skipped
ROLE-00000001-manager.md                  <-- width 8
$ sq check   →  ✓ no issues

$ sq renumber --from 19 --by 10
renumbered 1 item(s); counter=19
  RUN-BOOK-19 -> RUN-29
$ ls squads/runbooks/
RUN-00000029-000019-how-to-deploy.md      <-- corrupt name; prefix RUN, slug is the old digit-run
$ sq list --type guide
no items
$ sq check
✓ no issues
$ sq repair ; sq list --type guide
rebuilt index: 18 items, counter=19
no items                                  <-- unrecoverable via any sq verb
```

Frontmatter now reads `id: RUN-29` — a prefix belonging to no declared type.

## Control

Same operations on plain unhyphenated custom prefixes (`HB`, `SPK`): `sq renumber --from 20 --by 10`
→ `HB-21 -> HB-31`, files correct, `sq check` green, item still visible. The trigger is exclusively
the hyphen.

## Consequence

An item is permanently removed from the board and from the index, its file left under a name no
glob will ever match, with a green `sq check`. `repad` additionally reports `18 file(s) renamed`
while silently skipping the 19th (`continue  # malformed filename`) with no warning.

## Missing safety net — same one lost by the repair finding

`renumber` calls `_rebuild_index_from_disk(..., known_corpus=None)` deliberately (`:1050`,
documented at `:1023-1028`), so a rebuild that drops 19 items to 18 commits without comment.
Nothing anywhere asserts that the rebuilt item count must not fall.

## Related dead code

`src/squads/_paths.py:164` `type_for_id` has the identical `split("-", 1)[0]` bug with zero
production callers (test-only, already a dead-code candidate). Fix or delete it in the same pass so
it is not revived as a landmine.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-01T21:27:06Z] Paul Reviewer:
  - Recorded as in-flight: a fix for this was already being implemented when the finding was filed (uncommitted changes present under src/squads/_services/ and src/squads/_index/). Verify against current code before starting work, and close this as Fixed citing the change rather than re-fixing it.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Renamed sub-entity kinds lose the story-map refusal and validator

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🔴 Critical
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**Remediation was already underway when this was recorded — read the current code before fixing.**

## Sites — two literal-kind gates, each individually defensible, together fatal

- `src/squads/_services/_subentities.py:628` — `if kind == "story":` gates `remove_block`'s
  refusal to delete a story that subtasks still map to.
- `src/squads/_services/_validators.py:221` — `if kind != "subtask": return []` gates the
  `subtask_story_mapping` validator that would report the orphan afterwards.

Between them they are the *only* protection on the story↔subtask mapping. The declared property
that should drive both already exists — `SubentityKindSpec.maps_parent_story` — and
`_subentities.py:760-766` (`_check_maps_parent_story`) was explicitly de-literalized to use it,
with the docstring "gated by the flag rather than a `kind == "subtask"` literal". These two were
left behind.

## Override

```toml
[selected]
subentity_kinds = ["scenario", "step", "finding"]
# scenario and step declared; step carries maps_parent_story = true
[items.feature]
subentity_kind = "scenario"
[items.task]
subentity_kind = "step"
```

## Driven

Driven through the service layer, because the CLI verbs are dead in this squad (see the finding on
the hardcoded per-kind service wrappers).

```
feature hosts: scenario ; task hosts: step
added scenario: SC1 on FEAT-20
added step:     SP1 on TASK-21, story=SC1

await svc.remove_block("FEAT-20", "scenario", "SC1")
REMOVED SCENARIO WITH NO REFUSAL

$ sq repair   → rebuilt index: 21 items
$ sq check    → ✓ no issues
$ sq show TASK-21
Step  Status  Assignee  Title       Story
SP1   Todo              First step  SC1        <-- SC1 no longer exists on FEAT-20
```

## Control — bundled kind names, same operations

```
await svc.remove_block("FEAT-19", "story", "US1")
refused: SquadsError cannot remove US1: subtasks still map to it: TASK-20 ST1. …

# and, with a hand-broken map:
$ sq repair && sq check
error TASK-20: subtask ST1 → US9 missing from FEAT-19
```

Both the refusal and the after-the-fact check fire on the bundled names and neither fires on the
renamed ones.

## Consequence

An adopter who renames the story/subtask vocabulary loses the refusal that prevents orphaning a
mapping *and* the check that would report it afterwards. Deleting one item silently corrupts a
sibling, and every subsequent `sq check` says the squad is fine.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-01T21:27:07Z] Paul Reviewer:
  - Recorded as in-flight: a fix for this was already being implemented when the finding was filed (uncommitted changes present under src/squads/_services/ and src/squads/_index/). Verify against current code before starting work, and close this as Fixed citing the change rather than re-fixing it.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Hardcoded agents/skills path defeats a relocated skill folder

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
## Site

`src/squads/_backends/_claude_code/_backend.py:25-26` and `:150-152` —
`_AGENTS = "agents"` / `_SKILLS = "skills"`, and the pre-seed fallback path
`ctx.squad_dir / _AGENTS / _SKILLS / f"{name}.md"`. The skill body location is a module constant,
not `spec.items["skill"].folder`.

## Override — placed before init

```toml
[items.skill]
folder = "team/skills"
[items.role]
folder = "team/roles"
```

## Driven

```
$ sq init --default-names --roles minimal --backend claude_code
$ sq list
ROLE-1  role  Active  manager
                                       <-- zero SKILL items
$ sq check
                                       <-- reports nothing
$ sq sync
                                       <-- does not repair it; a second sync does not either
```

On disk:

- the role landed correctly at `squads/team/roles/ROLE-000001-manager.md`;
- **`squads/team/skills/` does not exist at all**;
- ten unstamped, un-indexed files sit at `squads/agents/skills/{squads,greeting,sq-memory,sq-bug,…}.md`;
- `.claude/skills/squads/SKILL.md` points at `@squads/agents/skills/squads.md` — outside the
  declared folder.

## Root cause confirmed

`src/squads/_services/_maintenance.py:357` computes
`skills_folder = squad_dir / spec.items["skill"].folder` (= `team/skills`), and at `:367-369` looks
for the legacy `<slug>.md` there. The backend wrote it to the hardcoded `agents/skills/`, so every
slug hits `continue` — a silent, total seeding failure with no warning on any surface.

## Consequence

An adopter who relocates the skill folder gets a squad with no skill items at all: nothing in the
index, no `sq-<type>` skills, no orphan warning, and pointer files aimed outside the declared
folder. `sq check` is green. Not recoverable by re-syncing.

This is the worst of the agent-facing-contract gaps: the roster half of the squad silently does not
exist, and every downstream surface that resolves a skill by ID has nothing to resolve.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-01T21:54:48Z] Elias Python:
  - Fixed: _write_managed_skill's pre-seed fallback now reads spec.items[ROSTER_SKILL].folder (falling back to bundled_spec() when ctx.spec is None) instead of the hardcoded agents/skills constants. Falsified: relocated-folder squad now lands all 10 skill bodies + indexes them under the declared folder, .claude/ pointers resolve there, sq check clean, second sync stable; control (no override) unaffected.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The squads skill teaches task/feature/review commands that error

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
## Site

`src/squads/_rendering/templates/agents/squads_skill.md.j2` — hardcoded type literals at `:7`
(`` `TASK-<n>` ``), `:39` (`sq task 35 update --status Done`), `:40`
(`sq feature 12 story 1 update --status InProgress`), `:82` (`sq review N finding 1 comment`), and
the entire **Common commands** block at `:113-125` (`sq create task …`, `sq task 3 show/status/
update/body/comment`, `sq list --type task`, `sq tree FEAT-<n>`).

## Override

`[selected] items = ["epic","feature","bug","decision","review","guide","role","skill","operator"]`
— `task` dropped.

## Driven

Generated `squads/agents/skills/SKILL-000018-squads.md`, lines 226-233:

```
sq create task "Title" --author <your-slug> [--parent FEAT-<n>] …  # also: bug|decision|epic|feature|guide|review
sq task 3 show --full --comments
```

The derived `# also:` list correctly omits `task` while the command it annotates *is* `task`.
Running it:

```
$ sq create task "T" --author tech-lead
error: unknown item type 'task': 'task' was dropped from a [selected] list …
```

Under the `feature`→`capability` rename, generated line 27 still reads
`sq feature 12 story 1 update --status InProgress`. Under a `review` drop, generated line 69 still
reads `sq review N finding 1 comment`.

## Why this is not cosmetic residue

This is the canonical command cheatsheet the agent copies from — the `squads` skill is loaded at
session start by every role, and its **Common commands** block is the single most-copied text in the
whole generated corpus. Every command in it errors out on a squad that dropped or renamed the
anchor types. The template mixes a spec-derived list and a hardcoded literal *on the same line*,
which is the sharpest possible demonstration that the derivation was available and not used.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-01T23:23:16Z] Elias Python:
  - Fixed: introduced interactions.cheatsheet_anchor_type/cheatsheet_anchor_context — a generically-scored (sub-entity kind + required parent + ordered field) anchor type, replacing every hardcoded 'task'/'feature'/'review' literal in squads_skill.md.j2 (the ID example, Golden rules examples, the operator scoped-question example, and the whole Common commands block). On the bundled spec the anchor resolves to task, so every derived line is byte-identical to before (verified by diffing the regenerated skill against a fresh un-patched baseline squad). Falsified by dropping task ([selected] without it): the anchor recalculates to feature and every command in the regenerated Common commands block is genuinely runnable (create/show/update/status/list/tree all driven and succeeded). workflow.md.j2's own sibling 'sq task 35 show' bullet (shared by the squads skill's include and sq workflow/AGENTS.md) had the identical defect and is fixed the same way.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — AGENTS.md teaches the same dead task commands as the squads skill

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
## Sites

- `src/squads/_rendering/templates/agents_md/agents_section.md.j2:37-44` — hardcodes
  `sq create task`, `sq task 3 …`, `sq list --type task`, `sq tree FEAT-<n>`, `--priority high`,
  `--assignee qa`.
- `src/squads/_backends/_agents_md/_backend.py:37` — `_also_creatable_types` filters `t != "task"`;
  the anchor type is hardcoded in Python, not derived.

## Override

`[selected] items` dropping `task`.

## Driven

`sq sync`, then AGENTS.md lines 326-332 — byte-for-byte the same broken block as the `squads`
skill's Common-commands block, on the sibling backend. Running the advertised
`sq create task "T" --author tech-lead` gives
`error: unknown item type 'task': 'task' was dropped from a [selected] list …`.

## Consequence

The same defect class shipped twice, once per backend. AGENTS.md is the whole agent-facing contract
for the `agents_md` backend — an adopter on that backend has no other generated onboarding surface,
so every command an agent is taught fails.

Fix them together; the `_also_creatable_types` anchor and the template literals are one change.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-01T23:23:18Z] Elias Python:
  - Fixed: _also_creatable_types now takes the anchor type (no longer hardcoded != 'task'); agents_section.md.j2's Common commands block rewired the same way as the squads skill, sharing cheatsheet_anchor_context so both backends derive identically. Falsified: dropping task regenerates AGENTS.md anchored on feature with every command runnable (create/update driven and succeeded); byte-identical for the bundled roster/spec (also corrected an existing high vs urgent priority-value inconsistency between the two backends' examples — now both derive the same value). Goldens (agents_md_section, claude_md_section, workflow_cheatsheet, workflow_cheatsheet_raw) and the template manifest (0.12.3 only; 0.12.2 diffed byte-identical) regenerated.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — CLAUDE.md loop stops on types and statuses that may not exist

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
## Site

`src/squads/_rendering/templates/claude/claude_section.md.j2:84` — the orchestration loop's
termination condition:

> "until the parent's tasks are `Done` and its reviews `Approved`."

Four literals in one sentence: two type names, two status names.

## Override

```toml
[selected]
items = [ … no "review" … ]
[statuses.Done]
role = "in_force"
```

## Driven

```
$ sq sync
$ grep -n "Approved" CLAUDE.md
78:  … until the parent's tasks are `Done` and its reviews `Approved`.
```

On a squad with no `review` type at all, and where no lifecycle can reach `Approved`. Independently
broken by a `task` drop, which removes the other half of the same sentence.

## Consequence

This is the stop condition of the orchestration loop itself. An agent following CLAUDE.md is told to
loop until a state that no item in the squad can ever enter, on a type that does not exist — so the
loop has no defined termination. Of every hardcoded literal in the generated corpus, this is the one
with the largest behavioural blast radius, because it governs when a coordinating agent stops
spawning.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-01T23:22:59Z] Elias Python:
  - Fixed: reworded to the concept ("the parent's own work is settled: every child item closed out, every linked review resolved") instead of naming task/review/Done/Approved literally. Falsified: a squad with review dropped and task renamed regenerates a CLAUDE.md with no dead type/status names in this sentence; byte-identical structure for the bundled squad modulo the intended wording change (golden regenerated).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — CLAUDE.md names roster roles and subagents the squad lacks

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
## Sites

- `src/squads/_rendering/templates/claude/claude_section.md.j2:78` —
  `` `subagent_type:` the role slug below — e.g. `tech-lead`, `architect`, `<tech>-dev`, `reviewer`, `qa` ``
  is a hardcoded roster list.
- `claude_section.md.j2:107` and `src/squads/_rendering/templates/workflow.md.j2:13` — the
  authoring bullets call `authoring_owner()`, which reads the **bundled role catalog**, not the
  live roster.

## Driven

```
$ sq init --default-names --roles minimal --backend claude_code --backend agents_md
$ ls .claude/agents/
manager.md                                 <-- the entire roster
$ grep -n "subagent_type" CLAUDE.md
65: … subagent_type: the role slug below — e.g. tech-lead, architect, <tech>-dev, reviewer, qa
$ grep -n "authors" CLAUDE.md
93: The **architect** authors **decisions**
94: The **code reviewer** authors **reviews**
```

Neither role is on the roster.

## Consequence

The manager reads its own orchestration section, spawns `subagent_type: tech-lead`, and Claude Code
fails — four of the five suggested agents do not exist. The authoring bullets separately name roles
that cannot be addressed, so an operator following them gets a refusal from `--author`.

Both halves are the same defect: generated agent-facing text describing a roster the squad does not
have. The roster is available in the render context; the bundled catalog is what is being read.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-01T22:58:36Z] Elias Python:
  - Fixed both halves. (1) claude_section.md.j2's subagent_type example clause is now built from the live roster (curated order, filtered to slugs actually present; <tech>-dev shown only when a dev role exists), empty when the roster has none of the candidates. (2) authoring_owner() takes an optional roster_slugs filter; threaded through claude_section.md.j2's own authoring-bullet loop, the shared workflow.md.j2 cheatsheet (now also passed roles= from the squads-skill render and from sq workflow's CLI, which best-effort reads the live roster and degrades to unfiltered outside a squad). Falsified: a minimal (manager-only) squad's CLAUDE.md/squads skill/sq workflow no longer name tech-lead/architect/reviewer/qa/<tech>-dev anywhere; byte-identical for the standard full roster (diffed CLAUDE.md, AGENTS.md, the squads skill, and sq workflow --raw). Updated two unit tests that asserted authoring prose with an empty roles=[] fixture (now roster-aware) and regenerated the workflow_cheatsheet_raw golden (minimal-roster project fixture correctly loses its phantom authoring bullets).
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Role card create_lane comes from a hardcoded CREATE_LANES table

<!-- sq:finding:F9:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
Found independently by two sweeps — at the CLI consumer and at the `_interactions` table itself.
A third consumer, the `workflow.md.j2` cheatsheet, shares the root cause and is folded in here.

## Sites

- `src/squads/_interactions/__init__.py:167-174` (`CREATE_LANES`) — a hardcoded map of the seven
  built-in type literals.
- `src/squads/_interactions/__init__.py:192-203` (`allowed_create_types`) — **no `spec`
  parameter**.
- Consumed at `src/squads/_cli/_role.py:242,257,269` — the human panel and the `create_lane` key of
  `sq role … show --json`.
- Third consumer: `src/squads/_rendering/templates/workflow.md.j2` role bullets, rendered into both
  the `squads` skill and `sq workflow`.

Its sibling twenty lines down, `item_types_for_role` (`:258-284`), **does** take a `spec` and
explicitly filters, with the docstring: "a type PLAYBOOK still names but spec has dropped … is
filtered out here, so a role's preload list never keeps naming a type that no longer exists."
`allowed_create_types` never got that treatment.

## Driven — dropped types

Override drops `guide` (and `review`), renames `guide`→`handbook`, adds custom `incident`:

```
$ sq role architect show   | grep creates
  creates: decision, guide
$ sq role tech-writer show | grep creates
  creates: guide
$ sq role architect show --json
  "create_lane": [ "decision", "guide" ],

$ sq create guide "g" --author architect
error: unknown item type 'guide': 'guide' was dropped from a [selected] list
(selected.items) in .overrides/workflow.toml, not left undeclared
```

## Driven — renamed type

`task` renamed to `job`:

```
$ sq role tech-lead show --json | jq .create_lane
['task']
```

## Driven — the inverse direction

`handbook` and `incident` never appear in any role's lane, and creating them is silently
un-lane-checked: `sq create handbook --author architect` and `sq create incident --author qa`
produced no advisory. The mechanism does still work for built-ins —
`sq create bug "b1" --author architect` →
`advisory: 'architect' is not the in-lane author for 'bug' items (expected: 'qa')`.

## Driven — the third consumer

In the same squad, the `workflow.md.j2` role bullets correctly dropped the `guide` bullet but
mention neither `handbook` nor `incident` — an adopter's custom types are invisible in the
"who writes what" section.

## Consequence

An agent reading its own role card — the canonical "what am I supposed to author" surface, and a
`--json` key that an orchestrating client consumes — is instructed to run a command every path
refuses. `sq sync` correctly withdrew the `sq-guide` skill and the role preload list in the same
squad, so this is the one remaining surface still naming the dead type.

## Scope note

The *other* half of the same table degrades correctly and is sanctioned: `_services/_base.py:521-529`
gates the out-of-lane advisory on `item_type in LANED_TYPES`, documented at
`_interactions/__init__.py:410-414`. Only the advertising half is broken. The fix belongs in
`_interactions` (give `allowed_create_types` a `spec`), which covers all three consumers.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-08-01T22:58:34Z] Elias Python:
  - Fixed: allowed_create_types(slug, spec=None) now filters CREATE_LANES by spec membership, mirroring item_types_for_role's own filter; updated the three _cli/_role.py call sites to pass svc.spec. Falsified: sq role architect show now drops guide from create_lane (and the --json key) in a squad dropping guide, byte-identical for a plain squad. workflow.md.j2's role bullets (the third consumer, shared root cause) are covered by the F8 fix below since both go through authoring_owner.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — _default.md.j2 has no sub-entity container, so add-block fails

<!-- sq:finding:F10:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
Found three times independently — as a template gap, as a service-layer `add_block` failure, and as
a spec-validator/template contract mismatch. Merged here.

## Sites

- `src/squads/_rendering/templates/items/_default.md.j2` (whole file) — emits `## Description`,
  `sq:body` and `sq:discussion` only. No `sq:summary`, no sub-entity container region.
- `src/squads/_services/_base.py:317-334` (`_template_for`) — the template is selected by the
  **type-name string**, `items/<type>.md.j2`, falling back to `_default.md.j2`. `ItemSpec` has no
  `template` declaration, so the `items/` directory listing *is* the vocabulary.
- No `_ensure_subentity_container` call anywhere on the create path. The primitive exists and is
  used correctly at `src/squads/_services/_retype.py:288-297`.
- `src/squads/_workflow/_models.py:630-643` (`_check_subentity_kinds`) happily accepts
  `subentity_kind` on any type, so lint declares the spec valid.
- `subentity_container_map` (`_base.py:89-91`) resolves the container tag from the kind's declared
  `plural`; `items/feature.md.j2` hardcodes an `sq:stories` region and a `## User Stories` heading. The two
  contracts disagree.

Refusal site: `src/squads/_services/_subentities.py:218`.

## Driven — a brand-new type

Override: `[items.incident] prefix="INC" folder="incidents" lifecycle="incident"
subentity_kind="subtask"`, plus its `[lifecycles.incident]`.

```
$ sq create incident "Outage"
$ sq incident 20 add-subtask "mitigate"
error: no subtasks section in INC-20
```

Same shape with `[items.audit] subentity_kind = "finding"`:

```
$ sq create audit "Q3 audit" --author reviewer
squads/audits/AUD-000019-q3-audit.md
# file contains only sq:body + sq:discussion — no findings container
await svc.add_block("AUD-19", "finding", "A finding", body="b")
ERROR: SquadsError no findings section in AUD-19
```

## Driven — a renamed built-in

Override: `[selected].items` drops `feature`; `[items.capability]` re-declares it verbatim with
`subentity_kind = "story"`; `[items.task] parents` retargeted.

```
$ sq create capability "Login"
$ sq capability 20 add-story "…"
error: no stories section in CAP-20
```

And `task` renamed to `job` — an identical spec, `subentity_kind = "subtask"`:

```
$ sq workflow lint
workflow spec OK — no errors or warnings.
$ sq create job "Jx" --author tech-lead
created JOB-21 → …/squads/jobs/JOB-000021-jx.md
$ sq job 21 add-subtask "s1"
error: no subtasks section in JOB-21
```

The created file confirms it: `sq:body`, `## Discussion`, `sq:discussion`, nothing else.

## Driven — a renamed sub-entity kind on a surviving built-in

`[items.feature] subentity_kind = "scenario"` still renders from `items/feature.md.j2`, which wrote
`sq:stories`: `SquadsError: no scenarios section in FEAT-20`. The template *does* derive the
adjacent prose from `spec.item_subentity_kind` — it is half-derived, which is exactly why it looks
right and behaves wrong. A rename of `feature` also silently drops the `## User Stories` block and
both marker regions.

## Consequence

Sub-entities are unusable for every type an adopter adds or renames, while the same sync's
generated AGENTS.md advertises them (line 43: `` `incident` → `subtask` ``, `` `capability` → `story` ``).
The spec says the type hosts them, `sq workflow lint` says the spec is fine, `sq check` says the
squad is fine, and the feature is permanently dead behind an error message that names neither cause
nor remedy.

## Workaround exists and is undiscoverable

Hand-placing `squads/.overrides/templates/items/job.md.j2` fixes it (verified: `added ST1 to JOB-24`).
The command that would lead an adopter there refuses:

```
$ sq override scaffold items/job.md.j2
error: no bundled template 'items/job.md.j2' — use a path like 'items/task.md.j2' or 'agents/role.md.j2'
```
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-08-01T22:05:16Z] Elias Python:
  - Fixed: added ensure_subentity_container_text (_services/_base.py) — a template-agnostic primitive that appends a working container (correct tag+heading from the active spec) after create-rendering, reusing the exact retype primitive (_ensure_subentity_container now delegates to it, so the two paths can't drift). Also de-hardcoded the bundled task/feature/review templates' container tag+heading (spec.subentity_plural + new WorkflowSpec.subentity_container_heading) so a renamed kind on a surviving bundled type no longer emits a dead stale region beside a second correct one.
- [2026-08-01T22:05:17Z] Elias Python:
  - Falsified: brand-new type (no template) + custom kind now hosts add-subtask end to end; feature renamed to capability + subentity_kind=story works via add-story; feature kept + subentity_kind renamed to scenario emits ONLY the scenario container (no orphaned sq:stories) and add_block succeeds via the service layer (CLI verb registration for a renamed kind is a separate, already-documented gap). Bundled/default squad output is byte-identical to pre-fix (verified feature/task/review). Golden fixture + template manifest regenerated for the 3 changed bundled templates; full targeted test slice (601 tests: template/golden/create/subentity/retype/override) green.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Dropping task deletes the priority vocabulary from the squads skill

<!-- sq:finding:F11:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
## Site

`src/squads/_rendering/templates/agents/squads_skill.md.j2:10` — `spec.fields_for('task')`. The
type used to *discover* the priority axis is hardcoded, so the axis exists in the generated skill
only if a type literally named `task` is declared.

## Override

`[selected] items` dropping `task`. Every surviving type — `epic`, `feature`, `bug`, `decision`,
`review`, `guide` — still declares `priority`.

## Driven

`diff` of the generated `SKILL-000018-squads.md` against the same file from an un-overridden squad:

```
< sq task 3 update --assignee qa --priority urgent --parent FEAT-<n>
> sq task 3 update --assignee qa --parent FEAT-<n>
< …Set importance with `--priority urgent|high|medium|low`.
> …
```

## Consequence

Dropping one unrelated type silently deletes the entire priority vocabulary from the `squads`
skill. Agents lose `--priority` — not because it stopped working (it works on all six surviving
types) but because the only place that teaches it probed a type that no longer exists.

This is the discovery-anchor shape: a template asking one arbitrary type what the whole spec's
vocabulary is. The correct source is the union across declared types, or the collection catalog
directly.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-08-01T23:23:01Z] Elias Python:
  - Fixed: added _badges.first_ordered_field, scanning every non-roster type (declaration order) for the first ordered-collection field instead of probing 'task' alone; wired into cheatsheet_anchor_context, used by both squads_skill.md.j2 and AGENTS.md. Falsified: dropping task from a squad's selected list keeps --priority urgent|high|medium|low in the regenerated squads skill (now sourced from feature); byte-identical for a plain squad. Added tests/unit/test_generated_text_anchor_type_derivation.py.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Custom-type skills always claim the type has no sub-entities

<!-- sq:finding:F12:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
## Site

`src/squads/_backends/_claude_code/_backend.py:300-305` — the custom-type skill branch passes
`overview=""`, `commands=interactions.custom_item_skill_commands(ctype)`, `subentity_kind=None`,
`subentity_plural=None` **unconditionally**, ignoring `ctx.spec.item_subentity_kind(ctype)`. The
PLAYBOOK branch about fifteen lines up derives both correctly.

`templates/agents/item_skill.md.j2` is itself fully parameterised and correct; the wrongness is
entirely in the caller's arguments.

## Overrides

- A custom `[items.incident]` with `subentity_kind = "subtask"`.
- `feature` renamed to `capability`, `subentity_kind = "story"`.

## Driven

Generated `squads/agents/skills/SKILL-000019-sq-capability.md`: the lifecycle is correct, but the
closing paragraph reads

> "Read anything back with `sq capability <n> show --full --comments`"

and stops. The `{% if subentity_kind %}` branch never fires, so there is no `add-story` guidance and
no `sq capability <n> story <k> body` guidance — compare `SKILL-000016-sq-review.md:56-59`, which
does emit exactly that block for a bundled type.

Meanwhile the same sync's AGENTS.md line 43 says `` `capability` → `story` `` and
`` `incident` → `subtask` ``.

## Consequence

The per-type skill an agent is told to open before acting on that type contradicts AGENTS.md about
whether the type has sub-entities at all — and the skill is the more authoritative surface, because
it is the one the role definition points at. An agent following it will never discover the
sub-entity verbs.

Note this compounds with the missing `_default.md.j2` container: on a custom type the verbs are
both undocumented *and* non-functional, so nothing surfaces the breakage.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-08-01T23:40:37Z] Elias Python:
  - Fixed: custom-type skill branch in _backend.py now derives subentity_kind/subentity_plural from ctx.spec.item_subentity_kind(ctype) instead of passing None/None unconditionally (mirrors the PLAYBOOK branch 15 lines up).
  - Falsified: custom incident type with subentity_kind=subtask now gets add-subtask/subtask guidance in its generated skill (was silent, stopped after the lifecycle line). Control (bundled minimal-roster squad, no custom types) diffed byte-identical before/after.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Generated role and managed text hardcode the InProgress status

<!-- sq:finding:F13:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F13:head:end -->

<!-- sq:finding:F13:body -->
## Sites

- `src/squads/_rendering/templates/agents/role.md.j2:71` — "Keep status honest: move items to
  `InProgress` when you start"
- `src/squads/_rendering/templates/agents/squads_skill.md.j2:63`
- `src/squads/_rendering/templates/claude/claude_section.md.j2:101` — `--status InProgress`
- `src/squads/_rendering/templates/agents_md/agents_section.md.j2:39`

Four templates, one literal, reaching every role definition and both backends' managed sections.

## Override

A custom `[items.incident]` whose lifecycle is `Triage → Mitigating → Resolved`.

## Driven

```
$ grep -n InProgress squads/agents/roles/ROLE-000006-devops.md
92: - Keep status honest: move items to `InProgress` when you start, not before.

$ sq incident 20 status InProgress
error: 'InProgress' is not a valid status for incident
       (allowed: Cancelled, Mitigating, Resolved, Triage)
```

## Consequence

Every role definition in the squad instructs the agent to make a transition that does not exist on
the type it is working. The instruction is generic advice ("keep status honest") welded to one
lifecycle's status name — the advice is right, the literal is not derivable from any single status
because the correct value depends on the item's type.

The fix likely means rewording to the concept rather than templating the name (the "first working
state" of the item's own lifecycle), since the role file is not written per-type.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-08-01T23:23:03Z] Elias Python:
  - Fixed: added WorkflowSpec.first_active_status/first_settled_status (walk the lifecycle's happy-path spine for the first live/settled role) plus a shared lifecycle_spine() extracted from linearize_lifecycle. role.md.j2/squads_skill.md.j2's generic 'keep status honest' advisory now describes the concept ('move to its lifecycle's first working state') since those files aren't per-type; claude_section.md.j2/agents_section.md.j2's per-type command examples now show the anchor type's own derived status instead of a literal InProgress. Falsified against a custom lifecycle (Triage→Mitigating→Resolved) and against decision/guide (whose happy path never reaches InProgress); byte-identical for the bundled squad modulo the intended reword (goldens regenerated). Added tests/unit/test_first_active_status_derivation.py.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Per-kind service wrappers raise a bare KeyError on a renamed kind

<!-- sq:finding:F14:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F14:head:end -->

<!-- sq:finding:F14:body -->
## Sites

- `src/squads/_services/_subentities.py:48-93` — `add_story` / `add_subtask` / `add_finding`
- `src/squads/_services/_subentities.py:257-358` — `stories` / `subtasks` / `findings` /
  `set_*_status` / `toggle` / `get_*`
- Crash sites: `:202`, `:623`, `:698` — `container = self.subentity_container[kind]` is a raw dict
  index that runs **before** `_check_type`.

## Override

`[selected] subentity_kinds = ["scenario","step","finding"]`; `[items.feature] subentity_kind =
"scenario"`; `[items.task] subentity_kind = "step"`.

## Driven

```
$ sq feature 20 add-story "A scenario"
… _services/_subentities.py:202 in _add_block_core
KeyError: 'story'                                   <-- raw traceback, not a SquadsError

$ sq feature 20 stories
error: FEAT-20 is a feature, which does not host storys (features host scenarios)
```

Two doors into the same operation: one refuses cleanly, one raises an unhandled `KeyError` out of
the service layer.

## Consequence

- An unhandled traceback escapes to the user — the one thing the CLI boundary is supposed to
  guarantee never happens. (A separate ~60-invocation traceback sweep across drops, renames, custom
  types and name collisions found no *other* traceback anywhere; this is the only one.)
- Every sub-entity verb is unreachable for a squad with a renamed kind, which is what forced the
  orphaned-story-map finding to be driven through the service layer rather than the CLI.

## Trigger versus defect

The CLI registering `add-story` on a feature that hosts `scenario` comes from
`src/squads/_cli/_create.py:276` `_create_spec = bundled_spec()` at import time (and `:416`
indexing `_create_spec.items["guide"].aliases`, a hardcoded type-name index into the bundled spec).
That is the trigger. The defect recorded here is that the service layer answers a bad kind with a
bare `KeyError` instead of a `SquadsError` — the dict index must move after `_check_type`, or become
a `.get()` with a clean raise. Both halves want fixing; they are separable.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-08-01T22:07:50Z] Elias Python:
  - Fixed: added SubentitiesMixin._container_for(kind) (a clean .get()-with-raise wrapper) and replaced all three raw self.subentity_container[kind] indices (_add_block_core, remove_block, _write_block_file) with it. An unknown kind now raises SquadsError('<kind> is not a declared sub-entity kind') instead of a bare KeyError, regardless of call order relative to _check_type.
- [2026-08-01T22:07:51Z] Elias Python:
  - Falsified: svc.add_block(FEAT, 'story', ...) on a squad hosting scenario/step now raises clean SquadsError (was traceback); the type-mismatch door (_check_type, e.g. get_block with a real-but-wrong kind) and the matching-kind door both still behave/succeed as before — no regression.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Dedicated priority kwarg bypasses the declared-field gate

<!-- sq:finding:F15:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F15:head:end -->

<!-- sq:finding:F15:body -->
## Sites

- `src/squads/_services/_items.py:261-264` (`update`) — assigns `item.priority` unconditionally.
- `src/squads/_services/_base.py:503` (`create`) — same.
- `src/squads/_services/_base.py:513-514` — the generic `fields` map calls
  `item.set_badge_value(code, value)`, likewise unchecked.

The sibling door is gated: `_apply_extra` (`_items.py:373-389`) goes through
`_badge_field`/`_parse_badge_code` against `spec.fields_for(item.type)`. The dedicated `--priority`
kwarg bypasses that gate entirely.

## Override

`[items.task] fields = []` — the task type declares no badge fields at all.

## Driven

```
$ sq task 20 update --set priority=low
error: 'priority' is not a settable field on a task; valid: (none)     <-- correct

$ sq task 20 update --priority high
updated TASK-20  tasks/TASK-000020-t.md
$ grep priority squads/tasks/TASK-000020-t.md   →  priority: high

$ sq create task "T2" --author tech-lead --parent FEAT-19 --priority urgent
$ grep priority squads/tasks/TASK-000021-t2.md  →  priority: urgent

$ sq check → ✓ no issues
$ sq list --type task
TASK-20  task  Draft   🟠 high   T   FEAT-19          <-- rendered as if declared
```

## Consequence

Two doors into the same field, one gated and one not. Undeclared badge data is persisted to
frontmatter and rendered in list views as though the type declared it. Not data *loss* — the item is
intact — but the frontmatter carries a field the spec says the type does not have, and every reader
believes it.

## Why the load-boundary backstop cannot catch it

`src/squads/_index/_store.py:126-135` iterates only the **declared** fields when cross-checking, so
an undeclared stored code is never visited. The backstop is structurally unable to see this
direction.

## Related

`_subentities.py:31` `_DEFAULT_FINDING_SEVERITY = "medium"` is sanctioned as a documented last
resort, but it *writes* `severity: "medium"` rather than omitting the field — so on a spec that
dropped the severity field it produces this same shape. Worth handling in the same pass.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-08-01T23:47:21Z] Elias Python:
  - Fixed: moved _badge_field/_parse_badge_code to ServiceCore (_base.py) and added _check_priority, routing the dedicated --priority kwarg through the same declared-field gate as --set on both create (_base.py _create_model) and update (_items.py _update_model). Also gated create's generic fields= map (was item.set_badge_value(code, value) unchecked) the same way.
  - Falsified: a task with fields=[] now refuses --priority urgent on both create and update identically to --set priority=... ('not a settable field on a task; valid: (none)'); control squad (priority declared normally) unaffected, both --priority and --set still work.
  - Guard added: tests/meta/test_priority_kwarg_goes_through_declared_field_gate.py — AST scan forbidding a raw priority kwarg/attribute passthrough into the model outside _check_priority.
  - Left as-is: _DEFAULT_FINDING_SEVERITY writing severity unconditionally on sub-entity add_block (_subentities.py) is the same shape one layer down (item-level vs sub-entity-level) but not in this finding's cited sites; flagging as a follow-up, not folding in given scope.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — A type name may shadow a built-in CLI verb and lint calls it clean

<!-- sq:finding:F16:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F16:head:end -->

<!-- sq:finding:F16:body -->
## Site

`src/squads/_workflow/_models.py:717-751` (`_check_item_refs`) validates prefix, folder and alias
uniqueness **among declared types**, and never against the built-in command table. A type name
silently doubles as a CLI verb — naming-convention-as-declaration, with no guard.

## Override

A custom type named `check`, with alias `list`.

## Driven

```
$ sq workflow lint
workflow spec OK — no errors or warnings.

$ sq create check "c1" --author manager
created CHK-19 → …/squads/checks/CHK-000019-c1.md

$ sq check 19 show
Usage: sq check [OPTIONS]
Error: Got unexpected extra argument(s) (19 show)

$ sq list 19 show
Usage: sq list [OPTIONS]
Error: Got unexpected extra argument(s) (19 show)
```

`sq show CHK-19` still works, so the item is reachable by ID.

## Consequence

The item's entire per-type verb surface — `status`, `update`, `body`, `comment`, `ref`, `retype`,
`remove` — is permanently unreachable, and the generated `sq-check` skill instructs the agent to use
exactly that surface. No traceback, clean refusals, and a squad that `sq workflow lint` declares
valid and that cannot be operated.

The alias axis is the same hole: `list`, `show`, `check`, `sync`, `repair`, `init`, `mine`,
`tree`, `board`, `memory` and friends are all claimable as a type name or alias today.

## Suggested shape

`_check_item_refs` already owns the uniqueness checks; the built-in command names are enumerable
from the Typer app. This should be a lint error at declaration time, not a discovery at first use.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-08-01T23:51:53Z] Elias Python:
  - Fixed: added RESERVED_CLI_VERBS (_workflow/_models.py) — the fixed non-item-type top-level command names (role/skill/operator excluded, since those ARE the roster types by design) — and a new _check_item_refs clause refusing a type name or alias that collides with one, at spec-validation time (runs on every WorkflowSpec construction, so it's a load-time refusal, not a first-use discovery).
  - Falsified: a custom type named check (alias list) now fails sq init / sq workflow lint / sq create with a clear 'shadows the built-in sq check command' message instead of silently succeeding; bundled spec and a non-colliding custom type (incident) both still lint/create clean.
  - Guard added: tests/meta/test_reserved_cli_verbs_matches_the_live_command_table.py pins the hand-maintained constant against the actual live Click command table (minus bundled item-type names/aliases) in both directions — it already caught one drift (tree was missing) before this landed.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Playbook prose in surviving skills names dropped or renamed types

<!-- sq:finding:F17:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟡 Medium
<!-- sq:finding:F17:head:end -->

<!-- sq:finding:F17:body -->
## Sites

`src/squads/_specs/playbook.toml` lines 87-88, 117-121, 128-133, 146-151, 164, 194, 214, 281, 308 —
loaded via `src/squads/_interactions/_loader.py`; plus
`src/squads/_rendering/templates/agents/squads_skill.md.j2:113`.

## What is and is not already handled

The **membership** half is handled and documented (`item_types_for_role`,
`_interactions/__init__.py:258-284`): a dropped type's own skill stops being preloaded, and
`sq sync` correctly withdraws `.claude/skills/sq-task/`. What is not handled is cross-type prose
*inside surviving types'* skills.

## Override

`task` renamed to `job`.

## Driven — after `sq sync`

```
squads/agents/skills/SKILL-000013-sq-feature.md:61:
  - create tasks with this feature as parent (`sq create task … --parent FEAT-<n>`)
squads/agents/skills/SKILL-000016-sq-review.md:29:  sq task <n> ref add REV-… --kind addresses
squads/agents/skills/SKILL-000010-sq-bug.md:26:     sq task <n> ref add BUG-… --kind fixes
CLAUDE.md:94:  … (e.g. `sq task 35 show`)
```

`sq-feature` is preloaded for `product-owner` in that squad and instructs it to run a refused
command.

The template line is the sharpest instance, because it mixes a spec-derived list with a hardcoded
literal on one line:

```jinja
sq create task "Title" … # also: {{ spec.non_roster_types() | reject('eq', 'task') | sort | join('|') }}
```

Rendered: `# also: bug|decision|epic|feature|guide|incident|job|review` — correct, because
`reject('eq','task')` now matches nothing — sitting beside an example command that no longer exists.

## Consequence

A role is preloaded with a skill for a type it does own, and that skill tells it to operate on a
type that was renamed away. The instruction is confidently wrong rather than absent.

## Scope note

`_interactions/__init__.py:261-269` documents PLAYBOOK's bundled-only nature honestly, but scopes
the claim to *membership*. The prose consequence is undocumented, so this is not covered by the
sanctioned carve-out. The remedy may be a documented limitation plus a narrowing of the prose rather
than templating it — worth a design call rather than a mechanical fix.

---

## Disposition: not already fixed — but narrowed to two lines, and closed as the documented limitation the operator ruled for.

**Established before touching anything, driven end to end**: fresh squad, full roster,
`.overrides/workflow.toml` renaming `task` → `job` (dropped from `[selected]`, re-declared under
the new key), real `sq sync`, then read off `.claude/skills/` — the pointer set is what actually
decides which guidance an agent boots with.

- **Membership half: confirmed handled.** `.claude/skills/` carries `sq-job` and no `sq-task`.
- **Template half: confirmed closed.** No hardcoded type literal survives in the squads-skill
  line the finding called the sharpest instance; the anchor-type derivation closed it.
- **Prose half: survives, and is now exactly two lines**, both in `sq-feature`'s product-owner
  guide — `create tasks with this feature as parent (sq create task … --parent FEAT-<n>)` and
  `map each subtask to one user story (sq task <n> add-subtask … --story USk)`. Down from four
  sites across three skills plus a template plus CLAUDE.md.

Worth recording because it cost a wrong result once: this text is **roster-dependent**. A
manager-only squad renders no product-owner section at all, so a minimal-roster read reports the
limitation as already fixed. The first probe here did exactly that; the fixture pins the full
roster and says why.

So the two survivors are precisely the ones the writer argued are load-bearing, and the operator
ruled: accepted as a limitation, no templating and no placeholder DSL, reduce gratuitous
cross-references instead. That work is done and `FEAT-714` shipped the remedy — the playbook is
overridable, so an adopter who renames a type rewrites those lines alongside the rename.

**What was genuinely still missing** is the finding's own scope note: the limitation was
undocumented. `_interactions/_loader.py`'s docstring described the structural contract in detail
and said nothing about prose, so the carve-out did not cover it. It now states the limitation,
the remedy, and why templating was declined — and `_interactions/__init__.py` points at it, so
the two halves are scoped apart in writing rather than only in behaviour.

**Guarded, not just documented.** A new integration test pins the *bound*: after the rename, the
set of preloaded skills still issuing a runnable command against the dropped type is exactly
`{sq-feature}`. A gratuitous cross-reference added to any other guide fails it — falsified by
planting one in `decision`'s tech-lead guide, watching it redden, and removing it. That is the
regression this area can actually suffer, and nothing was watching for it.

**Not built, and deliberately: a lint.** There is a precedent-shaped fix available —
`playbook_guide_role_live` is already a squad-global warn validator catching a playbook entry
that names a non-live *role*; the type analogue would turn this silence into a warning with a
named remedy, without templating anything. I did not build it, because the operator's ruling was
explicit and recent and reporting-instead-of-fixing was not what it asked for. Offered here as
the named next step if the team wants the silence removed.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-08-02T20:16:13Z] Catherine Manager:
  - Narrowed by later work and re-scoped. The template half (the squads-skill line mixing a spec-derived list with a hardcoded literal) is closed by the anchor-type derivation — verified, no hardcoded type literal remains in that template. What survives is exclusively the bundled playbook: 63 cross-type command references in _specs/playbook.toml, which go stale under a rename or drop. Resolving this belongs to FEAT-714, which makes the playbook the fourth overridable kind: an adopter who renames a type overrides the playbook prose alongside it, so this becomes a documented limitation with a supported remedy rather than an unbounded templating problem. Not to be fixed independently.
- [2026-08-03T07:40:22Z] Pierre Chat:
  - Accepted as a limitation, not a defect to engineer around: an adopter who removes or renames a type should rewrite the playbook too. No templating, no placeholder DSL. Worth doing instead: reduce gratuitous cross-references in the bundled playbook prose so there is less to go stale.
- [2026-08-03T07:55:03Z] Theo Writer:
  - Playbook prose narrowed: 64 cross-type references down to 50 (13 sites reworded). sq-decision, sq-review and sq-guide now render with zero references to another type name — a task rename leaves them fully correct. The two ref-kind command lines that named the fixing item by type now read `sq <type> <n> ref add BUG-…/REV-… --kind fixes/addresses` with a comment naming the relationship, matching the placeholder register the `squads` skill already uses.
  - Kept as load-bearing: the epic->feature and feature->task parent chains, the authorship lanes (product-owner authors features, tech-lead authors tasks, qa files bugs, reviewer opens reviews), and the "track the fix on a task, never off the bug" rule. Stripping the type name from these costs an actionable command an agent cannot reconstruct, which is worse than a stale one it can adapt.
  - Goldens regenerated after review of the diff (playbook_spec.json + 6 skill_body_sq-*.txt); full suite 2369 passed. Template manifest unaffected — playbook.toml is not under _rendering/templates/ so it is not hashed.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — The tech field is unreachable once the guide type is renamed

<!-- sq:finding:F18:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F18:head:end -->

<!-- sq:finding:F18:body -->
## Sites

`src/squads/_cli/_create.py:280` (`if t != "guide"`), `:361`, `:364`, `:395`, `:416`. The generic
`_make` / `_build_create_cmd` path has no `--tech`, no `--tag`, and no `--set`.

## Driven — the bundled type

```
$ sq create guide "g1" --author tech-writer --tech python --tag a
$ sq guide 11 show --json → extra = {'tech': 'python', 'tags': ['a']}
$ sq guide 11 update --set tech=rust
error: 'tech' is not a settable field on a guide; valid: tags
```

So even on the type the flag is welded to, `--set` cannot reach `tech` after creation.

## Driven — the same type renamed

Override renames `guide`→`handbook` (prefix `HB`, folder `handbooks`, alias `hb`), otherwise
verbatim.

```
$ sq create handbook --help
  … no --tech, no --tag …
$ sq handbook 11 update --set tags=alpha     → ok
$ sq handbook 11 update --set tech=python
error: 'tech' is not a settable field on a handbook; valid: tags
```

## Consequence

`tags` survives via `update --set`. `tech` has **no CLI path at all** once the type is not literally
named `guide` — it cannot be set at create time and cannot be set afterwards. An adopter who renames
or replaces the guide type permanently loses that field, with no error explaining why.

The remedy is either to declare `tech` as a proper spec field (so `--set` reaches it) or to derive
the extra flags from the type's declaration rather than from its name.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-08-01T23:58:26Z] Elias Python:
  - Decision: registered tech in the generic --set door rather than generalising the dedicated --tech/--tag create-time flags. tags already had exactly this shape (dedicated flag at create, generic --set afterward, no flag survives a rename) — tech now matches it instead of inventing a second mechanism for one field.
  - Fixed: added tech to guide's extra_fields in workflow.toml, and registered X.TECH in _models/_metadata.py's _GENERIC_FIELDS (it was declared as an ExtraKey but never wired into the settable-fields catalog, unlike tags/target_ref).
  - Falsified: sq guide N update --set tech=rust now works on the bundled type; on a guide renamed to handbook via [items.handbook] (+selected.items), --set tech=... and --set tags=... both work post-creation, and neither has a dedicated create-time flag — the same, now-consistent shape tags already had. Updated tests/unit/test_type_spec_capability_flags.py's stale assertion.
  - Guard added: tests/meta/test_dedicated_create_flags_stay_settable_via_generic_set.py scans _create.py for extra[X.<KEY>] assignments and asserts each is registered in _GENERIC_FIELDS, so a future dedicated flag can't reintroduce this shape.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — sq mine uses a category-blind visibility predicate

<!-- sq:finding:F19:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F19:head:end -->

<!-- sq:finding:F19:body -->
## Site

`src/squads/_cli/_main.py:983` — `items = [i for i in items if spec.is_open(i.status)]`.

Every other view uses the category-aware `spec.hidden_by_default(i.type, i.status)`
(`_main.py:127`, and `list` / `tree` via the service).

## Driven

```
$ sq decision 10 status Accepted     → ADR-10 → Accepted
$ sq list -t decision
ADR-10  decision  Accepted   d1   architect
$ sq mine architect
nothing assigned to architect
```

## Consequence

`records`-category items are terminal-but-shown by design — `_main.py:428-429` states exactly that
for `sq list` — and `sq mine` hides them. An architect with an accepted decision assigned sees an
empty inbox for it.

This **reproduces on the stock spec**, so it is a live bug today, not only an adopter-facing one.
An adopter declaring their own `records`-category type hits it for that type too.

The fix is a one-predicate swap to the category-aware helper the rest of the CLI already uses.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-08-01T23:54:10Z] Elias Python:
  - Fixed: sq mine (_cli/_main.py) swapped its is_open(status) filter for the same category-aware spec.hidden_by_default(type, status) predicate sq list/tree already use.
  - Falsified on the stock spec (no override needed, per the finding): an Accepted decision assigned to an agent now shows in sq mine by default (was empty); a Done task still hides by default and appears with --all. Added tests/cli/test_slug_validation_surfaces.py::TestMine::test_a_terminal_records_category_item_still_shows_by_default and ::test_a_done_task_still_hides_by_default_and_surfaces_with_all as regression coverage.
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — Item templates hardcode region tags, headings and a field code

<!-- sq:finding:F20:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F20:head:end -->

<!-- sq:finding:F20:body -->
## Sites

- `src/squads/_rendering/templates/items/review.md.j2:14,16,21-22`
- `src/squads/_rendering/templates/items/task.md.j2:7,15-16`
- `src/squads/_rendering/templates/items/feature.md.j2:7,12-16`

Each file derives *some* of its prose from `spec.item_subentity_kind` and hardcodes the region tag,
the heading, and the field flag beside it — so a single generated file contradicts itself.

## Override A — renamed sub-entity kinds

`[subentity_kinds.step]` and `[subentity_kinds.issue]` (the latter with field `impact`), then
`[items.task] subentity_kind = "step"`, `[items.review] subentity_kind = "issue"`.

Generated `TASK-000021-t.md`:

- heading `## Subtasks` and an `sq:subtasks` region (both hardcoded)
- sitting directly under derived prose: "Add with `sq task 21 add-step`"

Generated `REV-000022-r.md`: derived kind is `issue`, but the line reads
"Add with `sq review 22 add-finding "…" --severity medium`" and the region is `sq:findings`.

```
$ sq review 22 add-finding …
error: REV-22 is a review, which does not host findings (reviews host issues)
```

## Override B — a renamed *field* on the bundled kind, the CLI-supported shape

```toml
[subentity_kinds.finding]
fields = [{ code = "impact", label = "Impact", collection = "severity", default = "high" }]
```

The generated review file still prints `_Severity:_` and `--severity medium`, because `:14` and
`:16` pass the literal field code `'severity'` to `field_label` / `field_default`, which then fall
back rather than reading the kind's declared field. The declared label `Impact` and default `high`
never appear anywhere.

## Caveat recorded during the sweep

Override A's shape is not fully usable today — the CLI does not register `add-step` / `add-issue` /
`--impact` either — so the kind-rename half is latent. Override B is a live, visible wrongness on a
shape the CLI does support.

## Scope note

The `_badges.py:65-96` fallbacks these calls land in are documented as deliberate and are
**sanctioned**. The defect is the hardcoded field code passed *into* them from the template, not the
helper's behaviour when it receives one.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
- [2026-08-02T00:05:08Z] Elias Python:
  - Decision: fixed the live half only (field-label/default), per the finding's own scope note — the kind-rename half (add-<kind>/--<field> CLI verbs for a renamed sub-entity kind) is a separate CLI-registration gap, not a template one.
  - Fixed: added _badges.primary_field_code(kind, spec) (first declared field on the kind, falling back to 'severity') and rewired review.md.j2 to derive the field code once and pass it everywhere instead of the literal 'severity' — the legend label, the collection, the CLI hint's --flag name and its default all now track it. Also derived the add-<kind> verb name itself (was hardcoded add-finding), matching task.md.j2/feature.md.j2's already-derived add-{{ kind }} shape. task.md.j2/feature.md.j2 needed no change — F10's remediation had already de-hardcoded their tag/heading before this finding was filed.
  - Falsified: rendering items/review.md.j2 against the bundled spec before/after the fix is byte-identical (diffed directly). Against the finding's exact Override B ([subentity_kinds.finding] fields = impact/severity/high), driven end to end via sq create review: the generated file now reads '_Impact:_ ...' and 'add-finding "…" --impact high' instead of Severity/--severity.
  - Guard added: tests/meta/test_item_templates_never_hardcode_a_field_code_literal.py scans items/*.md.j2 for a quoted field-code literal passed to field_label/field_default/resolve_collection.
  - Same class still outstanding, newly observed (not filed, out of this finding's scope): sq review N add-finding is a statically-registered command built from the bundled finding-kind fields at import time — overriding the kind's fields (as in Override B) doesn't change its --severity/--impact flag, only the generated file's prose. The dynamic-verb fallback added for F10's add-<kind> gap only fires when the verb NAME isn't statically registered, not when a same-named verb's field set changes underneath it.
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — The squads skill hardcodes Done/Cancelled and the visibility rule

<!-- sq:finding:F21:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F21:head:end -->

<!-- sq:finding:F21:body -->
## Site

`src/squads/_rendering/templates/agents/squads_skill.md.j2:128-129`:

> "Closed items (Done/Cancelled/…) drop out of `sq list`/`sq tree` by default — pass `--all`…"

Two hardcoded status names, plus a hardcoded claim about *visibility* that is not derived from the
status roles that actually govern it.

## Override — a status-role shadow

```toml
[statuses.Done]
role = "in_force"      # settled = true, hidden = false
```

## Driven

```
$ sq sync
$ sq task 21 status InProgress
$ sq task 21 status Done
$ sq list
TASK-21   task   Done   T   FEAT-20         <-- listed by a bare `sq list`
```

Generated line 242 of `SKILL-000018-squads.md` still asserts it drops out.

## Consequence

Agents add `--all` needlessly and mis-read what the default view contains — the opposite failure to
the usual one, since the default view here is *more* complete than the skill claims. Both the status
names and the visibility rule are derivable: the roles catalog carries `hidden` per role, and
`hidden_by_default` is the live predicate.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
- [2026-08-02T00:07:26Z] Elias Python:
  - Fixed: reworded squads_skill.md.j2's closed-item-visibility sentence from the literal 'Closed items (Done/Cancelled/…)' to describe the concept (status hidden-by-default) instead — same reword-to-concept shape as the InProgress/task/review fixes earlier in this sweep.
  - Falsified: on the finding's exact override ([statuses.Done] role = in_force), a task moved to Done now shows in a bare sq list, and the generated squads skill no longer claims otherwise; bundled squad's generated text still correctly describes the default (Done items hidden without --all).
  - Template manifest (0.12.3 only) regenerated for agents/squads_skill.md.j2.
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — retype help lists the bundled type set, not the active one

<!-- sq:finding:F22:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F22:head:end -->

<!-- sq:finding:F22:body -->
## Site

`src/squads/_cli/_items.py:297` — `_cmd_retype` builds `targets` from the `spec` passed into
`build_item_app`, which for statically registered built-ins is the **import-time**
`common.get_active_spec()`, i.e. the bundled spec (`src/squads/_cli/__init__.py:404,410,414`).

## Override

`review` dropped; `guide` renamed to `handbook` (prefix `HB`, folder `handbooks`, alias `hb`);
custom `incident` added.

## Driven

```
$ sq task 10 retype --help
  new_type  NEW-TYPE  Target type (non-roster: work or records):
                      epic|feature|task|bug|decision|review|guide.

$ sq incident 9 retype --help          # lazily built custom type
  new_type  NEW-TYPE  Target type (non-roster: work or records):
                      epic|feature|task|bug|incident|decision|review…
```

`guide` does not exist in this squad; `handbook` and `incident` do. The lazily built custom-type
path is correct in the same squad — only the statically registered built-ins are stale.

Enforcement itself is correct:

```
$ sq task 10 retype handbook
retyped TASK-10 → HB-10
$ sq task 9 retype review                 # in a squad that dropped review
error: unknown type 'review'
```

## Consequence

Help is wrong in **both** directions: it advertises a type that will be refused, and hides the ones
that work.

This directly contradicts the invariant asserted in place at `_items.py:100-111`:

> "every command builder below (retype's target-type help, update's `--priority` help) derives its
> help text from the same spec used to decide eligibility — help and enforcement can never
> disagree."

They do. The comment should either become true or stop making the claim.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
- [2026-08-01T22:44:36Z] Elias Python:
  - Fixed: help now built via a spec-aware Click Command (common.spec_aware_command_cls) that re-derives retype's target list at --help render time from the live per-invocation spec, instead of the spec captured at import-time registration. Falsified: retype --help now lists incident/handbook, omits review, in a squad dropping review + adding incident; byte-identical for a plain squad (diffed against pre-fix output).
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — Priority help on built-in create/update advertises rejected values

<!-- sq:finding:F23:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F23:head:end -->

<!-- sq:finding:F23:body -->
## Sites

- `src/squads/_cli/_create.py:38-48` (`_priority_help`, read at import time)
- `src/squads/_cli/_items.py:178` (`_cmd_update`, same import-time spec)

## Override

`[collections.priority]` badges replaced with `p0 | p1 | p2`.

## Driven

```
$ sq create task --help  | grep -i priority
  --priority  TEXT  Priority: urgent|high|medium|low.
$ sq task 9 update --help | grep -i priority
  --priority  TEXT  Priority: urgent|high|medium|low.

$ sq create task y --author tech-lead --priority high
error: unknown priority 'high' (one of: p0, p1, p2)
$ sq task 9 update --priority high
error: unknown priority 'high' (one of: p0, p1, p2)
$ sq create task z --author tech-lead --priority p1     # works, undocumented
```

The lazily built custom-type path is correct in the same squad:

```
$ sq create incident --help  | grep -i priority
  --priority  TEXT  Priority: p0|p1|p2.
$ sq incident 11 update --help | grep -i priority
  --priority  TEXT  Priority: p0|p1|p2.
```

## Consequence

Every documented value is rejected and every accepted value is undocumented — on the built-in types,
which is where nearly all real usage lives.

## Why this is not sanctioned

`_create.py:38-48`'s docstring acknowledges the bundled read ("byte-identical to the previous
hardcoded text there") and documents it as a *fact*, not as correct behaviour. It does not say the
resulting help may be false. The static-registration carve-out covers keeping non-customized help
byte-identical; it does not extend to printing values the parser refuses.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
- [2026-08-01T22:44:38Z] Elias Python:
  - Fixed: same spec_aware_command_cls mechanism applied to --priority help on create/update (both static built-ins and the lazy custom path). Falsified: sq create task --help / sq task N update --help now show the override's p0|p1|p2 in a squad replacing the priority collection, matching what the parser actually accepts; byte-identical for a plain squad.
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — sq create completion is bundled-blind while root completion is not

<!-- sq:finding:F24:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F24:head:end -->

<!-- sq:finding:F24:body -->
## Site

`src/squads/_cli/_create.py:175,198,235` — `_CustomCreateGroup._dropped_static_names`,
`_custom_non_roster_types` and `get_command` all call `common.get_active_spec()` only. On the
completion path the root callback never runs, so nothing is ever bound and it silently returns the
bundled spec.

The sibling `_CustomTypeGroup` has `_resolve_spec_for_ctx(ctx)`
(`src/squads/_cli/__init__.py:51-100`) built precisely for this case. `_CustomCreateGroup` has no
equivalent.

## Override

Custom `incident` added; separately, `guide` dropped and renamed to `handbook`.

## Driven

```
$ _SQ_COMPLETE=complete_bash COMP_WORDS="sq " COMP_CWORD=1 sq | tail -3
review
guide
incident            <-- root completion: correct, sees the override

$ _SQ_COMPLETE=complete_bash COMP_WORDS="sq create " COMP_CWORD=2 sq | tail -3
decision
review
guide               <-- create completion: bundled list; no `incident`
```

Same in the rename squad: create-completion offers `guide` (dropped) and omits `handbook` and
`incident` (both live).

`sq create --help` is correct in both squads — the callback *does* run there — so this is
completion-only.

## Consequence

An adopter tab-completing a custom type gets nothing, and tab-completes types that will be refused.
Root completion already gets this right in the same process, which makes the asymmetry the
strongest argument for the fix: the mechanism exists twenty lines away.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
- [2026-08-01T22:44:40Z] Elias Python:
  - Fixed: added common.resolve_spec_for_ctx (the _CustomTypeGroup._resolve_spec_for_ctx logic, now shared) and switched _CustomCreateGroup's list_commands/get_command to it. Falsified via _SQ_COMPLETE=complete_bash: sq create <TAB> now offers a custom incident type and omits a dropped guide/review, matching root completion; byte-identical for a plain squad.
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — item_is_roster and eleven sibling accessors raise a bare KeyError

<!-- sq:finding:F25:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F25:head:end -->

<!-- sq:finding:F25:body -->
## Site

`src/squads/_workflow/_models.py:1091-1093`

```python
def item_is_roster(self, item_type: str) -> bool:
    """True when *item_type*'s category is roster (role, skill, operator)."""
    return self.items[item_type].category == "roster"
```

Directly below it, `item_subentity_kind` (`:1095-1107`) was given a membership gate and a docstring
promising it — "Also returns None (rather than raising) when item_type isn't declared in this spec
at all — a dropped/renamed type must cleanly lose its sub-entity check, not crash the caller."
`item_is_roster` was named in the same original crash report, did not get the same treatment, and
has no docstring saying which contract it holds.

## Driven — probing every accessor against a merged spec with `guide` dropped

```
guide in spec: False
  OK   item_subentity_kind: None
  OK   item_extra_fields: []
  RAISE item_is_roster: KeyError: 'guide'
  RAISE machine_for: KeyError: 'guide'
  RAISE item_parent_required: KeyError: 'guide'
  RAISE item_ref_rules: KeyError: 'guide'
  RAISE parent_allowed: KeyError: 'guide'
  RAISE parent_hint: KeyError: 'guide'
  RAISE live_statuses: KeyError: 'guide'
  RAISE role_for(bad status): KeyError: 'Parked'
  RAISE hidden_by_default: KeyError: 'Parked'
  RAISE subentity_completion: KeyError: 'nope'
  RAISE subentity_plural: KeyError: 'nope'
  RAISE collection: KeyError: 'nope'
```

Of the fourteen accessors probed, only the two already fixed degrade.

## Reachability — latent, not live

None of these could be reached from a driven command. `sq create`, `sq <type> <n> …`,
`sq list -t/-s`, `sq tree -t/-s`, `sq migrate rename-type`, `sq migrate rename-status` and
`sq import` were all driven with dropped, unknown and roster types; every one gated first and
refused with a clean `SquadsError`.

## Why it is still a gap

`item_is_roster` has 15+ call sites across `_services`, `_cli` and `_backends`, and
`src/squads/_cli/_items.py:144` already hand-rolls the workaround at the call site:

```python
spec.item_is_roster(item_type) if item_type in spec.items else item_type in ROSTER_TYPES
```

That is exactly the shape the original crash report was about — a caller compensating for an
accessor that will not degrade. Every new call site is a new chance to forget it.

`role_for` / `hidden_by_default` are the same story on the status axis: `role_for`'s docstring
promises only that the *role-name* lookup never raises, and is silent about `self.statuses[status]`.

`collection()` (`:1069-1071`) documents its raise in place and is **sanctioned** — the point is not
that everything must degrade, it is that the contract must be stated and consistent within a family.
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
- [2026-08-01T22:15:03Z] Elias Python:
  - Fixed: split the eleven siblings into two documented families. DEGRADE (mirrors item_subentity_kind's precedent): item_is_roster->False, item_parent_required->None, item_ref_rules->[], parent_allowed->False (fail-closed), parent_hint->generic message, live_statuses->frozenset(), role_for->fallback role for an undeclared status too (was already promised for the role-name half). RAISE, documented like collection() (vocabulary-by-code lookup, no sensible default): machine_for, subentity_completion, subentity_plural, subentity_container_heading. hidden_by_default needed no code change — it only ever goes through role_for, so it inherited the fix.
- [2026-08-01T22:15:06Z] Elias Python:
  - Simplified _cli/_items.py:144's hand-rolled workaround to a direct spec.item_is_roster(item_type) call now that it degrades safely — removes the exact anti-pattern the finding cites as evidence of the gap. Added tests/unit/test_workflow_spec_accessor_degrade_contract.py asserting each accessor's contract (both directions) so a future accessor can't silently regress into a bare KeyError.
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->

<!-- sq:finding:F26 -->
### F26 — VS Code client mis-derives the role for a role-less status

<!-- sq:finding:F26:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F26:head:end -->

<!-- sq:finding:F26:body -->
**Evidence note:** this is the one finding derived from *reading* the client plus *driving* the CLI
half. The extension itself was not run — no visual or runtime confirmation of the rendering claim.

## Site

`clients/vscode/src/domain/statusRole.ts:77-86` (`resolveRole`) — the single place in the client
that resolves a status's behaviour. It is otherwise exemplary; its documented contract is factually
wrong:

> Returns `null` when either catalog hasn't loaded, `status` is unrecognized, or its role name
> doesn't (yet) appear in the roles catalog — every one of those cases degrades the same way: no
> settled/hidden/colour behaviour, **matching a status with no declared role at all (the spec's
> fail-safe-visible default)**.

The spec's actual default for a role-less status is not "no behaviour" — it is the
`FALLBACK_ROLE_NAME` role (`"pending"`, `src/squads/_workflow/_models.py:81`, resolved at `:1041`),
which is ordinary overridable vocabulary. `sq workflow statuses --json` emits the **declared** role,
so the client receives `null` and cannot tell the two cases apart.

## Override

`[roles.pending]` shadowed to `hidden = true, color = "muted"`, plus a role-less `[statuses.Parked]`.

## Driven — CLI half

```
$ sq workflow statuses --json
[{'status': 'Draft',  'role': 'pending', 'badge': None},
 {'status': 'Parked', 'role': None,      'badge': None}]

$ sq task 19 status Parked
TASK-19 → Parked

$ sq list -t task
1 closed items hidden — use --all

$ sq list -t task --all
TASK-19  task  Parked  Parked one
```

The CLI hides it, because `Parked` resolves through the fallback role, which the override made
hidden.

## Read half

Given `role: null`, the client computes `hidden: false, colorIntent: null`
(`domain/listView.ts:105`, `domain/treeMapping.ts:58`) and renders the item undimmed with no colour.

## Blast radius

Confined to show-closed mode (`treeDataProvider.ts:223` passes `--all`). In default mode the CLI has
already filtered server-side, so the trees agree.

## Fix shape

Either emit the **resolved** role name on the `sq workflow statuses --json` catalog surface — which
also removes the client's need to re-derive anything — or correct the claim in the docstring and
handle the fallback explicitly. The first is preferable: it is the only place in the whole client
domain layer that re-derives spec behaviour locally, and every other taxonomy surface
(`typeCategory.ts`, `typeOrder.ts`, `typeLabels.ts`, `badgeCatalog.ts`) sources from the CLI with an
explicit degrade-gracefully default.
<!-- sq:finding:F26:body:end -->

#### Discussion

<!-- sq:finding:F26:discussion -->
- [2026-08-02T00:11:42Z] Elias Python:
  - Fixed on the server (preferred fix shape per the finding): _cli/_workflow_cmd.py's _status_catalog now emits the RESOLVED role name (st.role or FALLBACK_ROLE_NAME) instead of the bare, possibly-null declared field — so a role-less status now reads role: pending on the wire, same as one that names pending explicitly. Corrected statusRole.ts's docstring to match (null is now only a stale/partial-fetch signal, never 'this status has no role by design'); no client logic change was needed since resolveRole's existing degrade path was already correct given a resolved input.
  - Falsified on the finding's exact override ([roles.pending] hidden=true + a role-less [statuses.Parked]): sq workflow statuses --json now returns role: pending for Parked instead of null. Bundled spec unaffected (every bundled status already declares its own role) — tests/cli/test_workflow_statuses_cli.py passed unchanged.
  - Verification note (same caveat the finding itself carries): the CLI-side fix + the client-side pure-function unit tests (test/statusRole.test.ts, ran via vitest, added a regression case for this exact shape) are what I could run and did run; the extension itself was never launched, so the rendering claim (undimmed vs dimmed in an actual VS Code tree view) is still a static/unit-level check, not a driven one. That check belongs to the operator on their own machine.
<!-- sq:finding:F26:discussion:end -->
<!-- sq:finding:F26:end -->

<!-- sq:finding:F27 -->
### F27 — init and adopt never seed skill items for custom or renamed types

<!-- sq:finding:F27:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F27:head:end -->

<!-- sq:finding:F27:body -->
## Sites

- `src/squads/_services/_service.py:143-145` — `init` calls `seed_bundled_skills()` only.
- `src/squads/_services/_service.py:206-211` — `adopt` calls neither.
- `seed_custom_skills` is reachable only from `sync` (`_services/_maintenance.py:398`).

Its docstring's rationale — "not at init, which only knows about bundled types" — is now stale:
`_init_time_spec` was added precisely so that init sees the merged spec.

## Override

Declares custom types `handbook` and `spike`.

## Driven

```
$ sq init
$ ls squads/agents/skills
SKILL-000009-greeting.md … SKILL-000017-squads.md
sq-handbook.md   sq-spike.md           <-- unstamped, no SKILL item, no index entry

$ sq check   → ✓ no issues
$ sq repair  → rebuilt index: 17 items          (both files ignored)
$ sq sync    → SKILL-000018-sq-handbook.md, SKILL-000019-sq-spike.md
```

## Consequence

A fresh squad with a custom type sits with untracked skill body files that are invisible to both
`check` and `repair` until someone happens to run `sync`. Self-healing once `sync` runs, so the
severity is low — but until then the roster is quietly incomplete, and an operator has no signal
that `sync` is required.

`adopt` is the worse of the two, since it seeds nothing at all and is the path an existing project
takes.
<!-- sq:finding:F27:body:end -->

#### Discussion

<!-- sq:finding:F27:discussion -->
- [2026-08-02T00:23:12Z] Elias Python:
  - Fixed: init() now calls seed_custom_skills() right after seed_bundled_skills() (same _skip_skill_seed gate); adopt() previously called neither and now calls both. Updated seed_custom_skills' stale docstring rationale ('not at init, which only knows about bundled types') to reflect that _init_time_spec already resolves the merged spec at both entry points.
  - Falsified on the finding's exact override (custom handbook/spike types): sq init now indexes sq-handbook/sq-spike as SKILL items immediately (sq check clean, sq repair a stable no-op, no sq sync needed); sq adopt on the same override now seeds both bundled and custom skills (previously seeded nothing). Bundled-only squad unaffected (11 skill items either way, byte-for-byte same as before) — 84 existing init/adopt/seed tests passed unchanged.
  - Guard added: tests/meta/test_init_and_adopt_seed_both_bundled_and_custom_skills.py (AST scan asserting both functions call both seed_* methods); verified it flags the pre-fix code (init missing seed_custom_skills, adopt missing both) and passes on the fix. Also added two integration regression tests (test_init_itself_seeds_a_custom_type_skill_with_no_sync_needed, test_adopt_seeds_both_bundled_and_custom_type_skills) in tests/integration/test_custom_type_skill_generation.py.
<!-- sq:finding:F27:discussion:end -->
<!-- sq:finding:F27:end -->

<!-- sq:finding:F28 -->
### F28 — The squads skill lists declared sub-entity kinds, not hosted ones

<!-- sq:finding:F28:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F28:head:end -->

<!-- sq:finding:F28:body -->
## Site

`src/squads/_rendering/templates/agents/squads_skill.md.j2:67, 74-76` — the loop iterates
`spec.subentity_kinds` (every *declared* kind) rather than the kinds reachable from a live item
type.

## Override

`[selected] items` dropping `review` — its kind `finding` stays declared in the kinds catalog but no
surviving type hosts it.

## Driven

Generated lines 54 and 63 of `SKILL-000018-squads.md` still list `findings`, and emit the row:

```
| One finding | sq <type> <n> finding <k> comment |
```

with a literal `<type>` placeholder, because `_kind_to_type` found no host.

## Consequence

The skill documents a sub-entity kind no item in the squad can carry, and the row it renders is not
even a runnable command shape. Low impact — an agent reading it finds nothing to apply it to — but
it is noise in the most-read generated file, and the `.get(_kind, "<type>")` fallback shows the
author already anticipated the mismatch rather than removing its cause.

The fix is to drive the loop from hosted kinds (types → `item_subentity_kind`) instead of the
declared catalog.
<!-- sq:finding:F28:body:end -->

#### Discussion

<!-- sq:finding:F28:discussion -->
- [2026-08-02T00:14:06Z] Elias Python:
  - Fixed: squads_skill.md.j2's 'Scope your comment' table and its field/--story hint list both switched from iterating spec.subentity_kinds (every declared kind) to iterating the already-computed _kind_to_type map (only kinds a live item type actually hosts).
  - Falsified: reviews dropped ([selected] items without review) — the generated skill's table/hints no longer mention finding or the stray sq <type> <n> finding <k> comment row; bundled squad's generated skill is byte-identical (diffed, only the timestamp + the unrelated F21 wording differ).
  - Template manifest (0.12.3 only) regenerated for agents/squads_skill.md.j2.
  - Left alone, out of this finding's cited scope: the 'Finding things across the board' section's generic sentence ('story/subtask/finding blocks') still names all three kind words regardless of hosting — a separate, always-present static sentence, not the two sites this finding cited.
<!-- sq:finding:F28:discussion:end -->
<!-- sq:finding:F28:end -->

<!-- sq:finding:F29 -->
### F29 — workflow_static hardcodes a retype example and ref-kind types

<!-- sq:finding:F29:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F29:head:end -->

<!-- sq:finding:F29:body -->
## Sites

`src/squads/_rendering/templates/workflow_static.md.j2:8` and `:90-92`.

## Override

`[selected] items` dropping `task`.

## Driven

`sq sync`, then generated AGENTS.md:

```
263: sq <type> <n> retype <new-type>   # e.g. sq task 7 retype bug
271: Valid targets: epic, feature, bug, decision, review, guide
```

Eight lines apart: a hardcoded copy-pasteable example naming `task`, immediately above the
spec-derived target list that correctly excludes it.

Lines 315-316 keep describing the `fixes` / `addresses` ref kinds in terms of `task` / `bug` /
`review` after those types are dropped.

## Consequence

No command *fails* from the ref table — it is descriptive prose — but the retype example is
copy-pasteable and wrong, sitting directly against derived text that proves the derivation was
available.

Lowest tier of the generated-text findings, but it is in the same file as the `squads`-skill
breakage and should be swept in the same pass.
<!-- sq:finding:F29:body:end -->

#### Discussion

<!-- sq:finding:F29:discussion -->
- [2026-08-02T00:18:20Z] Elias Python:
  - Fixed: workflow_static.md.j2's retype example now derives its source/target pair from the already-computed non-roster retype_targets list (first two entries) instead of the literal 'sq task 7 retype bug'; the fixes/addresses ref-kind table rows reworded to describe the relationship generically instead of naming task/bug/review.
  - Falsified: dropping task ([selected] without it) regenerates the derived example as 'sq epic 7 retype feature' (no reference to the dropped type) and the ref-kind rows no longer name task/bug/review. Golden mismatch caught a trim_blocks newline bug on first pass (the inline {% if %}...{% endif %} ate the newline before the closing code-fence, gluing it onto the example line) — fixed with the project's {% endif +%} idiom (matches F5/F8's precedent) before landing.
  - Goldens (workflow_cheatsheet, agents_md_section) and the template manifest (0.12.3 only) regenerated for the intentional text changes.
<!-- sq:finding:F29:discussion:end -->
<!-- sq:finding:F29:end -->

<!-- sq:finding:F30 -->
### F30 — Root help epilog hardcodes the type-command alias set

<!-- sq:finding:F30:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F30:head:end -->

<!-- sq:finding:F30:body -->
## Site

`src/squads/_cli/__init__.py:224` — the root help epilog:

```
"Type-command aliases (e/f/t/b/d/r/g, feat/dec/rev) are hidden from this list …"
```

A fixed alias list in the epilog of the first screen a user sees.

## Driven

```
$ sq --help | tail -3            # squad with `review` dropped
 Type-command aliases (e/f/t/b/d/r/g, feat/dec/rev) are hidden from this list …

$ sq g 1 show                    # squad with guide renamed to handbook
error: unknown item type 'guide': 'guide' was dropped …
```

In the rename squad the epilog advertises `g` and `r`/`rev` (all dead) and omits `hb` and `inc`
(both live) — wrong in both directions.

## Consequence

Low impact: it is a pointer sentence, and the `sq workflow` alias table it points at is fully
spec-driven and was verified correct in every override case. But it is help text built from a fixed
list, on the most-read screen in the CLI, and the correct list is one call away.
<!-- sq:finding:F30:body:end -->

#### Discussion

<!-- sq:finding:F30:discussion -->
- [2026-08-01T22:44:42Z] Elias Python:
  - Fixed: root epilog's alias clause is now derived from the spec (_alias_summary/root_epilog) and refreshed at --help render time via _CustomTypeGroup.format_help, not a fixed literal. Falsified: sq --help now shows only live aliases (adds hb/inc, drops g/r/rev) under a drop+rename+custom-type squad; byte-identical for a plain squad.
<!-- sq:finding:F30:discussion:end -->
<!-- sq:finding:F30:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-01T21:27:36Z] Paul Reviewer:
  - Findings record from a systematic four-surface sweep for spec-blind consumers. Thirty distinct gaps, deduplicated from thirty-four raw: 3 critical, 13 high, 10 medium, 4 low. Every one was driven against a throwaway squad with a real override, never read off the source — each body carries the site, the override placed, the command run, and the literal output.
  - Three defects were found by more than one surface and are merged, each citing all its evidence: F1 (sq repair counter regression — found from the swallowed SquadsError and again from the bypassed loader cross-check), F9 (CREATE_LANES / allowed_create_types — found at the CLI consumer and at the table, with the workflow.md.j2 cheatsheet folded in as a third consumer), and F10 (the missing sub-entity container — found as a template gap, a service add_block failure, and a validator/template contract mismatch).
  - F1-F3 are the data-loss tier and overlap remediation already underway; each carries a comment saying so. Do not double-fix them.
  - The review body carries what was deliberately NOT filed: the sanctioned list, verified by driving rather than by trusting the comment that claims it, plus the cosmetic list. The _migrations/ carve-out was confirmed to hold by all four surfaces and must not be "fixed" — every migration runner freezes its own era vocabulary on purpose, and deriving it from the live spec would break migrations retroactively.
  - Two things I could not settle from the evidence, left flagged in place rather than dropped: F20 kind-rename half is latent (the CLI registers neither add-step nor --impact, so only its field-label/default half is live today), and F26 is the one finding derived from reading the VS Code client plus driving the CLI half — the extension itself was never run, so its rendering claim is unconfirmed.
  - Awaiting triage. @tech-lead for scheduling; @architect for the two that want a design call before a mechanical fix: F17 (playbook cross-type prose — likely a documented limitation rather than templating) and F16 (type names shadowing built-in CLI verbs — needs a declaration-time lint rule and a call on the alias axis).
- [2026-08-01T22:23:37Z] Catherine Manager:
  - Adjacent gap worth tracking discretely, driven just now: the CLI registers sub-entity add-* verbs from the bundled spec, so a squad whose feature hosts a renamed kind still gets add-story and has no add-scenario. With the container fix landed, this is now the remaining reason a renamed sub-entity kind is unusable end to end. Documented in this review body but not carried as its own finding; folding it into the derive-help-from-the-active-spec work.
- [2026-08-01T23:34:23Z] Elias Python:
  - Fixed the sub-entity add-* verb gap Catherine flagged (folded into this derive-help-from-the-active-spec work, not its own numbered finding): build_item_app now wraps a type's group in a dynamic TyperGroup (_dynamic_subentity_group_cls) that falls back to a freshly-built command (against the live resolved spec) whenever a requested add-<kind>/<kind>/<kind-plural> verb isn't in the statically-baked tree, and hides the stale bundled-kind verbs from --help/completion while keeping them dispatchable to an accurate refusal (mirrors the dropped-type precedent). Falsified: renaming feature's story kind to scenario via override makes 'sq feature N add-scenario' work end to end (create/list/update all driven), 'sq feature N add-story' still exists but refuses accurately, and --help lists scenario/scenarios/add-scenario while hiding story/stories/add-story. Verified list_commands preserves original registration order (not alphabetized) so a plain squad's --help stays byte-identical — confirmed by diff against a pre-fix baseline for both feature and task. Added tests/cli/test_renamed_subentity_kind_on_a_static_type_cli.py.
- [2026-08-03T13:08:58Z] Theo Writer:
  - Not a finding — flagging a spec-blind crash I hit while driving the release notes, so it lands somewhere discoverable rather than only in a chat. @manager to route.
  - Repro: a workflow override renames the parent type sub-entity kind away from `story` (e.g. `[subentity_kinds.requirement]` + `[items.feature] subentity_kind = "requirement"`). Then `sq task <n> add-subtask "…" --story RQ1` raises an unhandled `KeyError: 'story'` with a Rich traceback, not a SquadsError. Same on the update path.
  - Site: `_cli/_items.py:727` and `:838` pass the literal `"story"` into `resolve_local_id`, which does an unguarded `spec.subentity_kinds[kind]` lookup in `_discussion.local_id_for`. The comment above line 727 states the intent ("stays wired to the built-in story kind ... a bounded built-in"), so the hardcoding is deliberate — but the lookup has no guard for the kind being absent from the active spec, which a rename makes true.
  - Consequence for release verification: the renamed-target-kind path of the story-map removal guard cannot be exercised end to end, because the mapping cannot be created in the first place. I verified that guard against a renamed *mapping* kind instead, and said so in the notes rather than claiming the wider case.
- [2026-08-03T13:12:53Z] Catherine Manager:
  - New spec-blind consumer found by the writer while driving the override docs, and it is an unhandled traceback rather than a wrong answer: under an override that renames the story kind, sq task <n> add-subtask with --story crashes with KeyError story, because the CLI passes the literal string into resolve_local_id whose subentity_kinds lookup is unguarded. Sites are _cli/_items.py around lines 727 and 838. Same class as this sweep and it breaks the governing invariant that a dropped or renamed item never produces a traceback. Queued for the next code pass.
- [2026-08-15T15:42:59Z] Elias Python:
  - F17 WontFix — established before implementing, per the brief. It is NOT already fixed, but it is narrowed. Driven end to end: full-roster squad, .overrides/workflow.toml renaming task to job, real sq sync, read off .claude/skills/. Membership half confirmed handled (sq-job present, sq-task withdrawn); template half confirmed closed by the anchor-type derivation; prose half survives as exactly two lines, both in sq-feature product-owner guide.
  - Those two are precisely the ones the writer argued are load-bearing, and op-pierre ruled: accepted as a limitation, no templating, no placeholder DSL, reduce gratuitous cross-references instead — which is done, and FEAT-714 shipped the remedy. So the disposition follows the ruling rather than re-litigating it.
  - What was genuinely still missing is the finding own scope note: the limitation was undocumented. _interactions/_loader.py now states it, the remedy, and why templating was declined; _interactions/__init__.py points at it. Plus a regression guard — an integration test pins the bound at exactly {sq-feature} after the rename, so a newly added gratuitous cross-reference fails. Falsified by planting one in the decision guide and watching it redden.
  - Worth knowing for anyone probing this area: the generated text is roster-dependent. A manager-only squad renders no product-owner section, so a minimal-roster read reports this limitation as already fixed. My first probe did exactly that; the fixture pins the full roster and says why.
  - Not built, deliberately, and offered as the named next step: playbook_guide_role_live is already a squad-global warn validator for a playbook entry naming a non-live ROLE. The type analogue would turn this silence into a warning with a named remedy, no templating involved. I did not build it because the operator ruling was explicit and recent. @manager your call whether to file it.
- [2026-08-15T15:46:57Z] Catherine Manager:
  - Approved as second party. Its last open finding, F17, is WontFix on evidence rather than deferral: the prose limitation is now bounded to exactly two lines in sq-feature product-owner guide, both load-bearing, with op-pierres ruling that no templating is wanted. The limitation is documented in the loader and pinned by a regression guard so the bound cannot widen silently.
<!-- sq:discussion:end -->
