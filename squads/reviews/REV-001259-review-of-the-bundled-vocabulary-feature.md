---
id: REV-1259
sequence_id: 1259
type: review
title: Review of the bundled vocabulary feature
status: ChangesRequested
author: reviewer
refs:
- FEAT-1249
- TASK-1251
- TASK-1252
- ADR-1250
- TASK-1253
- TASK-1254
subentities:
- local_id: F1
  title: Badge keys move after the timestamps on first rewrite; normalise once in
    the runner
  status: Fixed
  severity: medium
- local_id: F2
  title: Migration tests do not guard item top-level keys; fixture lacks priority
    and severity
  status: Fixed
  severity: medium
- local_id: F3
  title: story with an empty maps_to loses the mapping silently in the 0.19 runner
  status: Fixed
  severity: low
- local_id: F4
  title: Unknown entry keys with empty values are dropped on write
  status: Fixed
  severity: low
- local_id: F5
  title: New tests read item files and the index directly and assert substrings (ADR-1172
    rule 5)
  status: Fixed
  severity: low
- local_id: F6
  title: New priority and severity literals in services and the DTO adapter
  status: Fixed
  severity: low
- local_id: F7
  title: MANUAL point 2 awaits the wire task; refusal hint sends the adopter to the
    roster
  status: Open
  severity: info
- local_id: F8
  title: 'Generated text made vague instead of derived: review gate, findings, tree
    fields'
  status: Fixed
  severity: medium
- local_id: F9
  title: Bundled add-finding with a null or empty severity is now refused at import
  status: Fixed
  severity: medium
- local_id: F10
  title: An empty value on a derived flag is dropped silently instead of refused
  status: Fixed
  severity: medium
- local_id: F11
  title: Badge changes through update no longer reach the reflog delta
  status: Fixed
  severity: medium
- local_id: F12
  title: Three derived-name collision refusals have no case; mutations stay green
  status: Fixed
  severity: low
- local_id: F13
  title: New tests misdeclare derived-flag markers, read an item file internally,
    assert substrings
  status: Fixed
  severity: low
- local_id: F14
  title: Import refusals name add-sub, not the op written, and miss the declared selectors
  status: Fixed
  severity: low
- local_id: F15
  title: Derived options are listed after --help
  status: Fixed
  severity: info
- local_id: F16
  title: New tests read the job file internally, assert substrings, unit-test set_head;
    ST3 plural is regular
  status: Fixed
  severity: low
- local_id: F17
  title: 'Covers check: a call giving only derived options reaches the bare pair,
    so bare markers over-claim'
  status: Fixed
  severity: low
- local_id: F18
  title: Fixed article before declared names in the F8 template text and two spec-load
    messages
  status: Fixed
  severity: low
- local_id: F19
  title: 'Wire and render context differ from ADR-1250 s7: maps_to_kind, rows without
    badges, item templates'
  status: Open
  severity: low
- local_id: F20
  title: Kind-rename test renames the source kind and cannot fail on the local_prefix
    claim
  status: Fixed
  severity: low
- local_id: F21
  title: A changed local_prefix leaves entries unreachable and sq check silent
  status: Open
  severity: low
- local_id: F22
  title: 'rename-field: itself-refusal and reflog untested; empty kind name in two
    messages'
  status: Fixed
  severity: low
- local_id: F23
  title: 'rename-field has no scope: a key held on items and entries moves all or
    nothing'
  status: Open
  severity: info
- local_id: F24
  title: VS Code mapping label is made in client code and differs from the server
    label
  status: Open
  severity: medium
- local_id: F25
  title: VS Code bundled fixtures jq-trimmed, not regenerated; sub-entity shapes unexercised
  status: Open
  severity: low
created_at: '2026-10-29T21:09:02Z'
updated_at: '2026-10-29T22:41:02Z'
---
<!-- sq:body -->
## Scope

The tasks of FEAT-1249 (bundled vocabulary fully overridable), reviewed as each lands, against ADR-1250 (with the op-pierre rulings in its discussion), ADR-1172 for tests, and each task's acceptance.

- TASK-1251: generic badge and mapping storage and the 0.19 schema migration (commits 6feb2cf9 and a472109f, reviewed as `git diff 27242580..a472109f`; rebased onto release/0.19 as 228b5eaf, a4c38e57 and f408f091).
- TASK-1252: spec-derived aliases, neutral grammar names, headings and generated text (47811e26 on release/0.19). This pass covers the generated-text rewording only.
- TASK-1253: derived badge options, request fields, the list badge column, derived-name collisions and the import fronts (ce46f0eb on release/0.19).

Later tasks of the feature are added here as they land.

## Method

- Read the diff against the ADR sections it implements (section 6 storage, section 8 migration, section 1 for the generated text).
- Ran the branch's `sq migrate up` on a copy of this repository's squad, then `sq check`, `sq repair`, a second `sq migrate up`, and a write to an item, and diffed the item files.
- Probed edge inputs on scratch squads: refusal paths, empty spellings, unknown entry keys, spec-load collisions.
- Mutated the code under four of the new tests and the runner once more to see which tests go red.
- For TASK-1253: drove the dev tree on a bundled scratch squad, on one built from the override test squad's documents, and on a squad made by the released tool for comparison; mutated six sites under the new tests and the collision check on a copy of the commit.

Each finding labels its claims driven (ran it), read (read the code) or inferred.

## Results that hold

- Driven: on a copy of this squad, the runner changed only `story:` to `maps_to:` lines (1052 of them in 305 task files); no other line of any item file moved. `sq check` reported nothing on the corpus beyond the copy's missing agent files and the override stamp; `sq repair` and a second `migrate up` rewrote no item file. `--json` shapes of an item row and a sub-entity object match the released tool.
- Driven: a refused run (an `extra` key equal to a core key) exits 1, names the item and the key, and leaves every file, `.squads.json` included, byte-identical.
- Driven: spec load refuses a kind named `sub`, a kind field `attributes` or `badges`, an item field `status`, and an attribute named like a field of the same type.
- Driven: the MANUAL step's first point holds on release/0.19 now that TASK-1252 is in: an override spelling `maps_parent_story` stops `migrate up` before any step, naming the new spelling.
- Driven: the four sampled new tests (empty severity dropped, refusal writes nothing, unknown key kept, kind named `sub`) each go red under a mutation of their subject.
- Driven (TASK-1253): a bundled squad keeps `--priority` on create and update, `--no-priority`, `--priority`/`--min-priority` on list and tree, and `--severity`/`--no-severity` on bug, accepting and refusing the same values as the released tool, except an empty value (F10). The override squad takes `--urgency`, `--no-urgency`, `--work-size`, `--min-urgency`, and refuses `--priority` with exit 2. `--badge`, `--min-badge` and `--sort` refuse `priority` naming `urgency, work_size`.
- Driven (TASK-1253): spec load refuses two derived names on one surface (`--no-x` from fields `x` and `no_x`, `--min-urgency` from `urgency` and `min_urgency`). The fixed-name tables are held to the live commands and event models by the new `tests/meta` guard.
- Driven (TASK-1253): on the override squad, `add-outcome`, `add-action` with `impact` and `outcome`, the `action` comment selector and `add-sub` with `maps_to` all apply. `add-story`, a `kind` key on `add-action`, a mapping given twice and the old `story` key on `add-sub` are refused, nothing written.
- Read (TASK-1253): the `invoke` fixture change does not weaken the marker cross-check. It still parses the argument list statically, now against the spec of the squad the test runs in, which is what lets a derived flag resolve at all. The deleted `priority` kwarg guard has no subject left: every item-level badge write goes through `_parse_badge_code`, and surface cases refuse an invalid code on create and on update.
- Driven (TASK-1253): mutating the min-filter filing, the list column, the target-kind fold and the selector fold each turns new tests red.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1259 add-finding "…" --severity medium`; track with `sq review 1259 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Badge keys move after the timestamps on first rewrite; normalise once in the runner

<!-- sq:finding:F1:body -->
TASK-1251. Driven: after migrating a copy of this squad, a comment on TASK-1251 moved `priority: high` from after `assignee` to after `updated_at`. The item writer now emits every attribute after the timestamps and session keys, and `priority`/`severity` are attributes. 469 of the 1222 item files in this squad carry a top-level `priority` or `severity`, so each one shows a spurious two-line move the first time anything rewrites it, spread over unrelated commits, and parallel branches touching the same files get avoidable conflicts.

FEAT-1249 acceptance says a bundled squad's "item frontmatter is unchanged"; ST1 expects it "byte-identical to today". Neither holds after the first write.

Recommendation: normalise once, in the 0.19 runner. Rewrite each item file whose top-level key order differs from the writer's order, moving keys only (values untouched), so the reorder lands in the one diff an adopter already expects from `sq migrate up` and every later write shows only real changes. That needs ADR-1250 section 8 ("Item top-level keys are not touched") amended to "values are not touched; key order is normalised", which is the architect's and op-pierre's call. The alternative, keeping the old position, needs the writer to know which attributes are fields, which needs the spec in a spec-free writer, so it is the worse option. Accepting the churn instead means amending the feature acceptance.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-29T21:40:10Z] `python-dev` Elias Python:
  - Fixed in a3db5b9d on the TASK-1251 branch.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Migration tests do not guard item top-level keys; fixture lacks priority and severity

<!-- sq:finding:F2:body -->
TASK-1251. Driven: I changed the runner to sort every top-level key of each file it rewrites and to inject `priority: low` into it. All 36 tests in `tests/cli/test_migrate.py` stayed green.

The "item keys untouched" half of ADR-1250 section 8 is unguarded. `test_up_flattens_sub_entity_entries_and_leaves_the_rest_as_it_was` compares only the body after the frontmatter of the two rewritten files. Its "untouched" assertions cover the feature and the role, which carry no sub-entities and so are never planned by the runner: they cannot fail. The run on this squad shows the code is correct today (no top-level line moved); the gap is in the test.

Fixture realism: the 0.17 fixture holds no item with a top-level `priority` or `severity`, and no bug. Those are the keys this release changes, and the reorder in the key-order finding sits there.

Fix: give the rewritten task a `priority` (and add a bug with `severity`), and assert through the CLI or, if the rule-5 exception is granted, on the whole frontmatter that only the `subentities` entries changed.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-29T21:40:12Z] `python-dev` Elias Python:
  - Fixed in a3db5b9d on the TASK-1251 branch.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — story with an empty maps_to loses the mapping silently in the 0.19 runner

<!-- sq:finding:F3:body -->
TASK-1251. Driven: an entry holding `story: US1` and `maps_to: ''` migrates to `maps_to: ''`. The mapping to US1 is lost with no refusal, and the sub-entity then shows `"story": ""` in `--json`.

Read: `_flat_entry` treats an empty `maps_to` as no conflict, then copies `story` into `flat["maps_to"]` and overwrites it with the empty value when the loop reaches the `maps_to` key. The same holds for `maps_to: null`.

The input needs a hand edit, since 0.17 never wrote `maps_to`, so the severity is low. Still, it is a silent data loss in a runner, and the fix is small: skip an empty `maps_to` when `story` is set. The model should also fold an empty `maps_to` to unset, as it does for every attribute.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-29T21:40:14Z] `python-dev` Elias Python:
  - Fixed in a3db5b9d on the TASK-1251 branch.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Unknown entry keys with empty values are dropped on write

<!-- sq:finding:F4:body -->
TASK-1251. ADR-1250 section 6 says an unknown key on an entry is "kept through every write, repair and migration".

Driven: on a finding hand-edited to carry `note: ''` and `custom: keep`, `finding 1 update --status Fixed` wrote back `custom` and dropped `note`.

Read: `SubEntity._gather_attributes` drops every non-core key whose value is empty. It also merges a mapping found under a key named `attributes` into the attributes, so a hand-written `attributes: {x: 1}` comes back flattened as `x: 1`. At item level, `Item.attributes` keeps empty values as written, so the two levels disagree.

Fix: drop the empty value only for a key the spec declares as a field (or keep every key as written and let `badge_value` treat empty as unset, which it already does). Read the index's own `attributes` mapping only from the index, not from frontmatter.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-29T21:40:17Z] `python-dev` Elias Python:
  - Fixed in a3db5b9d on the TASK-1251 branch.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — New tests read item files and the index directly and assert substrings (ADR-1172 rule 5)

<!-- sq:finding:F5:body -->
TASK-1251. ADR-1172 rule 5: state is read back through the CLI, a test never opens `.squads.json`, it opens an item file only for the scaffolded hint, and it asserts the whole message line rather than a substring.

Read, in the new tests:
- `test_migrate.py` and the later `test_up_flattens_the_mapping_of_a_squad_with_its_own_vocabulary`, `test_subentity_verbs.py` and `test_item_verbs.py` read item frontmatter through the internal `squads._itemfile.read_frontmatter`.
- `test_up_flattens_sub_entity_entries_and_leaves_the_rest_as_it_was` opens `.squads.json` to check `schema_version`. That check is redundant, since the `show --json` calls before it already prove the index was rebuilt.
- Both refusal tests assert `"... " in result.output`.

The file reads were prescribed by the task brief: ST2 says "read back with show --json and the file's frontmatter". The stored shape is the subject here, and no CLI output carries it while the wire adapter keeps the old keys. So this needs a ruling, not just a rewrite: either op-pierre extends the rule-5 exception to a storage or migration test reading the item file the command rewrote, or the tests move to the CLI once the wire task exposes the stored keys. Either way, the `.squads.json` read and the substring asserts go now.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-29T21:40:20Z] `python-dev` Elias Python:
  - Fixed in a3db5b9d on the TASK-1251 branch.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — New priority and severity literals in services and the DTO adapter

<!-- sq:finding:F6:body -->
TASK-1251. ADR-1250 section 1: no code outside `_specs/` and `_migrations/` names a bundled field. Read: the change replaces the typed slots with new string literals:
- `badge_value("priority")` / `set_badge_value("priority", ...)` in `_services/_base.py` (create), `_services/_items.py` (update), `_services/_refs.py` (two graph-node sites) and `_services/_item_read_dto.py` (tree node);
- `badge_value("severity")` in `_services/_item_read_dto.py`;
- `rest.pop("severity", None)` in the `SubentityRow` adapter in `_api/_dto/_items.py`.

They bridge to the `--priority` options and the wire keys, which the badge-options and wire tasks remove, so they are acceptable for now. No guard catches them, though: the bundled-literal guard covers kind names, not field codes. Recorded so that those tasks delete each site and the derived guard catches field codes. Close this finding when they do.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-29T21:45:22Z] `reviewer` Paul Reviewer:
  - Read at ce46f0eb (TASK-1253): the create and update sites in _services/_base.py and _services/_items.py are gone with the --priority options. Five remain, all for the wire task (TASK-1254): _services/_refs.py lines 194 and 440, _services/_item_read_dto.py lines 84 and 271, and the SubentityRow adapter in _api/_dto/_items.py line 101. The changed code of TASK-1253 adds no bundled literal. Stays Open until TASK-1254 lands and the derived guard (TASK-1256) covers field codes.
- [2026-10-29T22:00:40Z] `reviewer` Paul Reviewer:
  - Read at 4ca21036: the five remaining sites are gone. The tree and graph nodes no longer carry `priority`, `_item_read_dto` no longer reads `severity`, and the `SubentityRow` adapter is removed. `rg 'badge_value\("'` finds no call with a literal code in `src`. Closing.
    
    The derived guard on field codes is TASK-1256's. Two older literals it should catch, both outside this finding's scope: `_badges.primary_field_code(default="severity")`, and `sq review` written literally in `templates/items/review.md.j2`.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — MANUAL point 2 awaits the wire task; refusal hint sends the adopter to the roster

<!-- sq:finding:F7:body -->
TASK-1251, the migration's `manual` text.

Point (1) holds on release/0.19 (driven: `maps_parent_story` in an override stops `migrate up` before any step, naming `maps_to_parent`).

Point (2) describes a template context that does not exist yet (read: `subentities/head.md.j2` still receives `severity`, `severity_label` and `story`). The wire task changes that context, so the text must be checked against what it ships, and corrected if the names differ, before the release.

Also driven, older than this change: a refusal from this runner ends with "Change the roster with a squads release that reads schema v0.17". `_maintenance._earlier_steps_note` prints that for any step's refusal, and for a sub-entity entry refusal it sends the adopter to the roster. It should say to fix the named entries and re-run.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-29T21:40:21Z] `python-dev` Elias Python:
  - Hint fixed in a3db5b9d: an entry refusal no longer prints the roster note. MANUAL point 2 stays open until the wire task settles the template context names.
- [2026-10-29T22:00:24Z] `reviewer` Paul Reviewer:
  - Verified at 4ca21036 (TASK-1254 landed). The refusal hint is fixed: a refused entry prints no roster note, and the whole-line refusal tests hold it.
    
    MANUAL point 2, head part: holds. `subentities/head.md.j2` receives `fields` (code, label, badge) and `mapping` (label, value), as the text says.
    
    MANUAL point 2, item and sub-entity part: not exact. Driven with an override `items/bug.md.j2` on a bundled scratch squad:
    - `{{ item.priority }}` still renders when the bug stores a priority. `render` wraps the item in `_FlatItem`, which serves stored attributes as fields. It fails only on an item that does not store one (`_FlatItem object has no attribute 'priority'`), where 0.17 rendered `None`. So the template breaks on some items and not others, which is harder to catch than the text suggests.
    - `{{ item.badge_value("priority") }}` renders `high`, or `None` when unset. The recommendation is right.
    - A sub-entity's `.severity` is gone too: view templates get raw `SubEntity` objects, so it fails on every entry. The text names only `.story` and `.extra`.
    
    Fix: say that `item.<code>` resolves only while the item stores the value, and that `badge_value('<code>')` is the form that works on every item. Add a sub-entity's `.severity` with `.badge_value('severity')`. ADR-1250 section 8 lists the same names and needs the same correction. Stays Open until the wording lands.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Generated text made vague instead of derived: review gate, findings, tree fields

<!-- sq:finding:F8:body -->
TASK-1252, ST5. ADR-1250 section 1: "Every human-facing word reads the declared vocabulary." Several lines of the generated text dropped their vocabulary instead of deriving it, so a bundled squad now reads vaguer guidance than before (read, 47811e26):
- CLAUDE.md orchestration loop, step 4: "every linked review resolved" became "every linked follow-up resolved". This is the gate of the loop, and in a bundled squad it means reviews.
- Step 3: "item/review status, new findings" became "the item's status, new sub-entities".
- Step 1: `sq tree` "status / priority / assignee / blocked per node" lost "priority". Tree nodes carry every declared field, so the line can list the declared fields.
- Operators "author items and review points" became "raise points on them"; "a review point you've reformulated" became "a point".
- The squads skill's per-kind comment guidance (the finding's "fix rationale, reproduction notes, agreed, closing this one") became one generic sentence for every kind.

Each has a spec source: the type the `review` capability's role creates (from the playbook), the kind that type hosts, and the declared fields. A neutral fallback is only for when the spec declares none. Per-kind guidance can come from the spec or the playbook, or stay generic if that is judged not worth a new key, but the review gate in the loop should name the review type.

Ordinary English words were also reworded because they equal a type name ("stability contract" became "stability guarantee", "rolled-back decision" became "rolled-back change"). That is harmless, but it shows the generated-text guard matching words rather than vocabulary references, which the guards task should not carry forward.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-29T21:46:07Z] `python-dev` Elias Python:
  - Fixed in 9f1e72f5: loop gate, tree fields and operator wording derive from the roster capability, playbook and spec; ordinary English restored. Per-kind comment guidance stays generic (a new spec key was judged not worth it).
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Bundled add-finding with a null or empty severity is now refused at import

<!-- sq:finding:F9:body -->
TASK-1253, ST5. ST5 expects that "a bundled squad's existing import files run unchanged", and ADR-1250 section 6 says an empty value of a declared field is unset.

Driven, on a bundled scratch squad, `sq import --dry-run` with:

```
{"op":"add-finding","target":"r","title":"F a","severity":null}
{"op":"add-finding","target":"r","title":"F b","severity":""}
```

- The released tool (0.17) accepts both lines and adds each finding with no severity.
- This commit refuses both, nothing written: `add-sub.fields.severity: Input should be a valid string` and `invalid severity '' (one of: critical, high, medium, low, info)`.

Read: `_add_kind_data` in `_services/_import_model.py` moves every top-level field key into `fields` whatever its value. The removed `AddFindingEvent.as_generic` dropped a falsy `severity`.

Fix: in `_add_kind_data`, drop a top-level field key whose value is null or empty instead of moving it into `fields`. Add a bundled case with `"severity": null` and `"severity": ""` on `add-finding`, since no bundled-format case covers this.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — An empty value on a derived flag is dropped silently instead of refused

<!-- sq:finding:F10:body -->
TASK-1253, ST1 and ST2. An empty value given to a derived value option is dropped without a word.

Driven, bundled scratch squad:

- `sq create task "T" --parent FEAT-2 --priority "" --author manager` exits 0 and creates the task with no priority. The released tool refuses it: `error: invalid priority '' (one of: urgent, high, medium, low)`.
- `sq task 5 update --priority "" --title "T two b"` exits 0, renames the task and leaves the priority as it was. The released tool refuses it. Alone, `update --priority ""` now says `nothing to update`.

Read: `_filer` in `_cli/_field_options.py` files a value only `if value`. The removed `_remember_field` used `value is not None`, and the removed update code had a comment saying that `--priority ""` counts as a supplied value.

Fix: file a value option when `value is not None`. The `--no-<code>` flags default to `False`, so they keep the truth test, or get their own callback. Add the boundary refusal case for an empty value.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Badge changes through update no longer reach the reflog delta

<!-- sq:finding:F11:body -->
TASK-1253, ST1. The reflog no longer records a badge change made through `update`.

Driven: on the released tool, `sq task 3 update --priority high` logs `delta: {"priority": "high"}`, and `sq reflog` prints it. On this commit, the same command logs `delta: {}`, so `sq reflog` shows an update with nothing in it.

Read: the removed `priority` branch of `_update_model` wrote `delta["priority"]`. Values now travel through `set_attributes` and `unset_attributes`, and `_apply_attributes` writes nothing to `delta`. That gap already existed for `--set` and `--unset` before this commit; routing `--<code>` through the same path widens it to the bundled flags.

Fix: have `_apply_attributes` record each set value and each unset key in `delta`, field or attribute, so every update door logs what it changed. Add a case that reads the update back through `sq reflog`.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Three derived-name collision refusals have no case; mutations stay green

<!-- sq:finding:F12:body -->
TASK-1253, ST4. Three of the refusals in `_workflow/_derived_names.py` have no case:

- two derived names on one surface (the `elif name in seen` branch of `_collisions`);
- a target kind against the fixed options of `add-<kind>` and `<kind> update`;
- a kind selector against the fixed keys of the import `comment` op.

Driven, on a copy of the commit: with the first branch disabled, `tests/cli`, `tests/meta`, `tests/check` and `tests/regressions` stay green. With the other two disabled together, they stay green too (the only failures were the manifest tests, which need a git checkout). The code is right: on a scratch squad, fields `x` and `no_x` are refused as both giving `--no-x`, and `urgency` and `min_urgency` as both giving `--min-urgency`.

ADR-1172 rule 1 asks for a case per boundary refusal. Fix: add one `workflow lint` case per branch, for example fields `x` and `no_x` on one type, a kind whose target kind is named `status`, and a kind named `target`.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — New tests misdeclare derived-flag markers, read an item file internally, assert substrings

<!-- sq:finding:F13:body -->
TASK-1253, the new tests. Read against ADR-1172 rules 3 and 5:

- **Markers.** The override-squad cases declare a pair the test is not about: `create <type> --author` on the cases for `--work-size` and `--urgency`, `<type> update --json` on the case for `--urgency`, `--work-size` and `--no-work-size`, and `list --json` / `tree --json` on the cases for `--urgency` and `--min-urgency`. Rule 3 names a derived flag by its derivation (`--<field>`, `--no-<field>`, `--min-<field>`), and the fixture does not record that name yet. That belongs to TASK-1256 (the CLI suite on the override squad). Until it lands, these markers claim coverage of pairs other cases own. They should be re-declared under the derivation names in that task.
- **File read.** `test_import.py` reads the job's file through the internal `squads._itemfile.read_frontmatter` (`_stored_action`). As amended, rule 5 allows that only to a migration test, as plain text. `job 9 action 3 show --json` already carries the field badges and the mapping (under `story` until TASK-1254 renames it).
- **Substrings.** `"No such option: --priority" in ...` (create, update, list, tree), `"add-outcome: 1" in output`, `"story: Extra inputs are not permitted" in ...` and `"urgency: Extra inputs are not permitted" in ...`. Rule 5 asks for the whole message lines.

Fix now: the file read and the substring assertions. Fix the markers with TASK-1256.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Import refusals name add-sub, not the op written, and miss the declared selectors

<!-- sq:finding:F14:body -->
TASK-1253, ST5. ADR-1250 section 4: an op or selector for an undeclared kind is unknown, and the refusal names what is declared. Driven on the override squad:

- `{"op":"comment",...,"story":"OC1"}` gives `comment.story: Extra inputs are not permitted`, which names neither the declared selectors (`outcome`, `action`, `sub`) nor the fact that `story` is a kind this squad does not declare. The new test pins this message as expected.
- `{"op":"add-action",...,"severity":"high"}` gives `add-sub.severity: Extra inputs are not permitted`, and an `impact` key on `add-outcome` gives `add-sub.impact: ...`. Both name `add-sub`, an op the file never wrote. A bundled `add-finding` with a stray key now reports `add-sub.<key>` where 0.17 said `add-finding.<key>`.
- The old `story` key on `add-sub` (the BREAKING change) is refused as `add-sub.story: Extra inputs are not permitted`, with no pointer to `maps_to`.

Fix: report a pydantic location under `ResolvedEvent.op_name` (the op the file wrote). For a comment key that is not a field, name the declared selectors. For `story` on `add-sub`, say to use `maps_to`.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Derived options are listed after --help

<!-- sq:finding:F15:body -->
TASK-1253. Driven: in `sq create task --help`, `sq task <n> update --help`, `sq list --help` and `sq tree --help`, the derived options are listed after `--help`. `get_params` appends them after Click's help option. In the released tool, `--priority` and `--no-priority` sat among the other options. Cosmetic: insert the derived options before the help option.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-29T22:33:55Z] `reviewer` Paul Reviewer:
  - - Reopened after a check at 7632d602. `_extended` in `_cli/_field_options.py` now places the derived options before Click's help option for `update`, `list` and `tree`; driven, they are fixed. `_create_command_cls` in `_cli/_create.py` still appends them after `--help`. Driven: `sq create task --help` lists `--priority` after `--help`, and `sq create job --help` on the override squad lists `--work-size` and `--owner-team` after it. Fix: route the create path through the same insertion.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — New tests read the job file internally, assert substrings, unit-test set_head; ST3 plural is regular

<!-- sq:finding:F16:body -->
TASK-1254, the new tests, read against ADR-1172 rules 3 and 5 as amended.

- **Internal file read.** `_job_entries` in `tests/cli/test_subentity_verbs.py` reads the job file through the internal `squads._itemfile.read_frontmatter`, in four override-squad tests (mapping option, clear flag). `job <n> action <k> show --json` now carries `maps_to` and the flat `impact`, so the read-back can go through the CLI.
- **Substrings.** `"No such option: --story" in ...`, `"No such option: --no-severity" in ...`, `"outcome: OC1" in shown`, `"story" not in (...)`. Rule 5 asks for the whole message lines.
- **Unit tests.** The two head tests in `tests/regressions/test_a_sub_entity_head_shows_the_declared_fields_and_mapping.py` call the internal `discussion.set_head`. The handback says why: no command renders a head any more. Read: the only caller of `set_head` is the frozen 0.2 to 0.3 runner. So these tests guard a renderer only that runner reaches.
- **ST3 case.** ST3 asked for a refusal on "a vowel-initial label with an irregular plural". The case uses `action`/`actions`, a regular plural, so a plural made by appending "s" in code would still pass.

Fix: read back through `show --json`, assert whole lines, and use a kind with an irregular plural in the ST3 case (the override squad can declare one). For the head tests, either keep them as the one documented exception or drop them with the dead head path. That is a ruling for op-pierre or the architect.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Covers check: a call giving only derived options reaches the bare pair, so bare markers over-claim

<!-- sq:finding:F17:body -->
Test infrastructure, `tests/_cli_surface.py` `reached_pairs` with the new `known` filter (TASK-1254).

Read: the per-test check is `declared - reached`, so dropping pairs from `reached` only makes it stricter, with one exception. The bare pair is added when `level` is empty (`reached |= {(key, None)} if not level`), and `level` is computed after the filter. So an override-squad call that passes only squad-derived options (`--outcome`, `--no-impact`) now reaches the bare pair. A marker such as `covers("<type> <kind> update")` then claims the bare call, which in the bundled tree means "update with no option": the "nothing to update" refusal.

Five markers use this: `tests/cli/test_check.py:84` and `tests/cli/test_subentity_verbs.py` at lines 992, 1010, 1020 and 1063. Each test passes `--outcome`/`--no-outcome`/`--impact`. The bundled bare-update case (line 631) still exists, so nothing is uncovered today. But the coverage guard can no longer tell a bare call from a call with options.

Fix: decide the bare pair from what the call gave, before the filter. A call that gave any option reaches no bare pair. Then the override-squad tests declare nothing, or the derivation names that TASK-1256 introduces (F13).
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Fixed article before declared names in the F8 template text and two spec-load messages

<!-- sq:finding:F18:body -->
ADR-1250 section 1: messages "are phrased so they need no article chosen in code". The article sweep (4aa383a7) covered the services and CLI messages. Read: these sites still put a fixed "a" before a declared name:

- `templates/claude/claude_section.md.j2`, added by the F8 fix (e679b838): step 4 renders `'a ' ~ _gate.type` ("more implementation, a review, a fix"), and the operator line renders "a {{ _gate.type }} point". A review type named `audit` gives "a audit".
- `_workflow/_validity.py:969`: "so a {kind} mapping to a sub-entity ...", a spec-load refusal naming the declared kind ("a action mapping" on the override squad's kind).
- `_workflow/_validity.py:1347`: "but a {item_type!r} item hosts ...".

Lines 786 and 1259 of the same file put "a" before engine words (a parameter kind, a view source kind), not vocabulary. They are fine.

Help text still calls the `article()` heuristic before a declared type: `_cli/_create.py:149` and `:331` ("Create an initiative."), and `_cli/_common.py:680` (`type_group_help`). It picks right for ordinary words, but it is an article chosen in code. A neutral wording costs nothing ("Create a new initiative." keeps the article before "new"; "Operate on one initiative by number or ID."). `address_epilog` names a reserved roster type, so it can stay.

Fix: reword the four vocabulary sites. Reword the help sites too, unless the architect reads section 1 as covering messages only.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — Wire and render context differ from ADR-1250 s7: maps_to_kind, rows without badges, item templates

<!-- sq:finding:F19:body -->
TASK-1254, ST4 and ST5, against ADR-1250 section 7. Driven on an override scratch squad and on a bundled one.

- **`display.maps_to_kind`** (on `<kind> <k> show` only) is not in section 7. It is needed: the show renderer labels the mapping line ("outcome: OC1") and may not read the spec, and nothing else in the DTO names the target kind. Two things should follow: list the key in section 7, and consider typing it as a `KindDisplay` like `display.kind`, so clients get the label and not only the name.
- **List rows carry no `badges`.** `<type> <n> <kinds> --json` entries and the `subentities` rows of `list --json` item rows carry each field only under its flat code (`"impact": "large"`). They have no `badges`, only `display.badges` (labels, without the raw code). The last paragraph of section 7 says clients read values from `badges` and "never from a field-named key". On these two surfaces a client can do neither. Either add `badges` to `SubentityRow`, or amend section 7 to say rows carry the flat keys.
- **Item templates** get no `fields` list. Section 7 says "the sub-entity head and the item templates receive the declared fields as a list of {code, label, badge}". Item templates receive `item` (stored attributes flat, plus `item.badge_value(code)`) and `spec`, as before. Amend section 7, or pass `fields`.

These are differences in the letter of the ADR, not defects in what ships. Route to the architect to amend section 7, or to the dev where the ADR stands.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — Kind-rename test renames the source kind and cannot fail on the local_prefix claim

<!-- sq:finding:F20:body -->
TASK-1255, ST2: `test_a_kind_renamed_with_the_same_prefix_keeps_its_entries_and_mappings`. ADR-1250 section 6 claims that a renamed kind needs no data move "while `local_prefix` is unchanged". The test cannot fail on that claim:

- It renames `action`, the kind the mapping starts from. The mapping value `OC1` points at an `outcome`, and the kind name never appears in the stored mapping. The rename the fixed `maps_to` key exists for is a rename of the **target** kind.
- It asserts `check --json` is `[]` and the raw `maps_to` values. Both stay the same when `local_prefix` changes too. Driven on a copy of the override squad, with `action` renamed to `step_kind` and `local_prefix` changed to `SK`: `sq check` reports no issues and `job 9 show --json` still gives `[("AC1", "OC1"), ("AC2", None)]`. But `job 9 step_kind 1 show` fails with "no step_kind SK1 in JOB-9", and `add-step_kind` creates SK1 next to AC1.

Driven, the meaningful case: rename `outcome` to `goal`, keeping `OC` and the plural. `job 9 action 1 show` then labels the mapping "goal: OC1" and `check` is clean.

Fix: rename the target kind, keep its prefix and plural, and assert through the CLI that the mapping is labelled by the new kind (the head line, or `display.maps_to_kind` once it is a KindDisplay) and that `<new kind> 1 show` reaches OC1.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — A changed local_prefix leaves entries unreachable and sq check silent

<!-- sq:finding:F21:body -->
ADR-1250 section 6, the kind-rename paragraph, relies on `local_prefix` staying unchanged. Nothing reports when it changes. Driven on the override squad, with `outcome` renamed to `goal`, `local_prefix` changed from OC to GO, and the plural kept:

- `sq check` reports no issues, exit 0.
- `initiative 8 goal 1 show` fails with "no goal GO1 in INI-8". The stored OC1 and OC2 can no longer be reached by number.
- `job 9 action 1 update --goal OC2` is accepted, but `--goal GO1` is refused with "goal GO1 not found in INI-8". A mapping can still name the old ids and cannot name the new ones.

This is mostly older than this feature: any `local_prefix` change already broke reachability. But the ADR now states the precondition and gives adopters a rename story, so the gap is in the path they are told to use.

Fix (architect's call): a `sq check` rule for an entry whose `local_id` does not carry its kind's `local_prefix`, or a `maps_to` whose prefix is not the target kind's. Alternatively, say in section 6 that changing `local_prefix` needs a data move and name it.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — rename-field: itself-refusal and reflog untested; empty kind name in two messages

<!-- sq:finding:F22:body -->
TASK-1255, ST2. The operation wiring, the refusal before any write, the rollback, the reflog line and the system comment all hold. Driven on both squads: refusals write nothing (git status clean); an entry-only move changes only that key, `updated_at`, one reflog line `rename-field JOB-9 {"old","new"}` and the index; a bundled `sev` to `severity` move on a finding works; a move to `priority` on a finding is refused. Gaps:

- **Boundary refusal without a case.** "cannot rename field 'x' to itself" (exit 1) has no test. ADR-1172 rule 1 asks for one case per boundary refusal.
- **The reflog line and the system comment are untested.** No case reads `sq reflog` or the discussion after a move. The rename-type and rename-status tests read theirs.
- **An empty kind name in two messages.** An entry on a type that hosts no kind (a record carrying a hand-written `subentities` list) is refused with "X1 of REC-10: '' does not declare 'impact'". `sq check` says "is not declared on any kind". Name the type instead, for example "REC-10 hosts no sub-entity kind".

Fix: add the itself-refusal case and one reflog read-back, and word the no-kind messages.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — rename-field has no scope: a key held on items and entries moves all or nothing

<!-- sq:finding:F23:body -->
TASK-1255 against ADR-1250 section 6, for the architect. `rename-field OLD NEW` applies to every holder of OLD in one batch, with no scope. When OLD sits on items and on entries, and NEW is declared on only one of them, the move is refused as a whole. There is no command to move only part of it.

Driven: with `weight` on JOB-9 and on its entry AC1, `rename-field weight impact` is refused with "JOB-9: 'job' does not declare 'impact'" (exit 1, nothing written), although AC1's kind declares `impact`. The adopter must either hand-edit the file or declare `impact` on jobs for a while.

This is the ADR's letter, implemented correctly. Consider an optional `--type`/`--kind` scope, or say in section 6 that a key shared across types moves in one go.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — VS Code mapping label is made in client code and differs from the server label

<!-- sq:finding:F24:body -->
TASK-1257, ST2. The preview's mapping label is built in client code: the target kind is found from the `maps_to` prefix through the catalog's `local_prefix`, then its name is capitalised (`mappingLabel` in `src/domain/badgeCatalog.ts`). ADR-1250 section 7 says the clients read "labels from `display` and the catalogs". The code makes a label of its own instead, and it differs from the server's:

- Driven: for a kind named `step_kind`, `<kind> <k> show --json` gives `display.kind.label` = "Step_Kind". The client's rule gives "Step_kind".
- The server already resolves the target kind (`display.maps_to_kind` on `<kind> <k> show`, which the amended section 7 types as a KindDisplay). The client resolves it again from the prefix, so it depends on the unenforced `local_prefix` (F21).

The preview reads `sq show --json`, whose sub-entity rows carry `display.maps_to` (the value) but no target-kind label, and the kind catalog has no label column. So the data the client should read does not yet exist on the surface it uses.

Fix: the architect names the source, for example `maps_to_kind` as a KindDisplay on the `show` sub-entity rows too, or a `label` per kind in `sq workflow subentity-kinds --json`. Then the client reads that label, falls back to "Maps to" when it is absent, and drops `buildMappingKinds` and the prefix lookup.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — VS Code bundled fixtures jq-trimmed, not regenerated; sub-entity shapes unexercised

<!-- sq:finding:F25:body -->
TASK-1257. The bundled fixtures were edited with jq, not regenerated. They no longer match what `sq` emits, so unit tests pass on shapes that never occur:

- `show-json.json` has no top-level `badges`, `display` or `views` (the dev tree emits all three), and its `subentities` list is empty. On the bundled side, no unit test sees a sub-entity object with `maps_to`, `deferred_to` or a flat field.
- `list.json` has no row with sub-entities. The `SubentityRow` shape (flat keys today, `badges` after the F19 fix) is not exercised.
- `tree.json` and `graph.json` were trimmed of `priority` only. The rewrite also re-encoded every `\u` escape in `show-json.json` as UTF-8, which is diff noise and not a shape change.

Regenerate from the dev tree, after the TASK-1254 wire fixes (F19: `badges` on every sub-entity row, `maps_to_kind` as a KindDisplay) land: `show-json.json` (on an item with a mapped sub-entity), `list.json` (with a sub-entity row), `tree.json`, `graph.json`, `subentity-kinds-catalog.json`, and the three `override-*` fixtures. The canary passes against the dev tree today (90 passed, run with `SQ_CANARY_CMD`).
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T21:10:18Z] `reviewer` Paul Reviewer:
  - Verdict on TASK-1251: changes requested. Storage and the runner are correct on this squad (driven: only story-to-maps_to lines change, refusal writes nothing, check and repair clean). Open before acceptance: F1 (key-order churn, a ruling on normalising once in the runner, ADR-1250 section 8), F2 (migration tests cannot fail on touched item keys), F3, F4, F5 (rule-5 ruling needed), F7 (re-check MANUAL point 2 when the wire task lands). F6 tracks literals the badge-options and wire tasks remove.
  - TASK-1252 generated text: F8 (medium). The rewording dropped the vocabulary where the spec can supply it, so the bundled loop gate no longer names reviews.
  - @manager route F1 and F5 to @architect and op-pierre for the rulings, F2 to F4 and F7 to the TASK-1251 dev, F8 to the TASK-1252 dev. Approval stays with you once the findings are dispositioned.
- [2026-10-29T21:11:25Z] `manager` Catherine Manager:
  - Manager rulings under the operator delegation for this drive (2026-10-29, flagged for op-pierre in the morning summary): F1: the 0.19 runner normalises key order once, moving top-level badge keys to the position the writer now uses, so the churn happens in the migration diff and never again; values untouched. The architect amends ADR-1250 section 8. F5: a migration test may read item files as plain text (the rewritten files are what migrate up produces), never through an internal function; .squads.json is never read and refusals assert whole lines. The architect amends ADR-1172 rule 5. Fix routing once pair 2 lands (dev cap 2): F2, F3, F4, F7 and the F1 runner change to the TASK-1251 dev; F8 to the TASK-1252 dev; F6 closes with the badge-options and wire tasks.
- [2026-10-29T21:45:23Z] `reviewer` Paul Reviewer:
  - TASK-1253 (ce46f0eb) reviewed. Verdict: changes requested, three medium findings. The derived options, list column, collision check and import fronts work on both squads (driven), and the invoke fixture change and the deleted priority guard are sound (see Results that hold).
  - F9: bundled add-finding import lines with a null or empty severity are now refused. F10: an empty --<code> value is dropped silently (0.17 refused it). F11: update --<code> no longer reaches the reflog delta. Low: F12 (three collision refusals have no case), F13 (markers, an internal file read, substring asserts), F14 (import refusals name add-sub, not the op written). Info: F15. F6 partly closed by this task; comment on F6.
  - @manager route F9 to F14 to the TASK-1253 dev. The F13 markers wait for TASK-1256. Approval stays with you once the findings are dispositioned.
- [2026-10-29T21:55:06Z] `python-dev` Elias Python:
  - F9 to F15 fixed in f636eebe (F13 markers wait for the CLI-suite-on-override task).
- [2026-10-29T22:00:42Z] `reviewer` Paul Reviewer:
  - Second pass at 4ca21036 (origin/release/0.19).
    
    - **F1 to F5 verified Fixed.** Driven: the branch's `migrate up` on a fresh copy of this squad changed 623 item files. A YAML diff of each one shows identical top-level values and identical body bytes. The only key moves are `priority` and/or `severity` (469 files: 411 priority, 22 severity, 36 both). The sub-entity entries differ only in `story` becoming `maps_to`. With the schema stamp reset, a second runner pass rewrote no item file. After the migration, a comment on TASK-1251 changed only `updated_at` and the discussion. Read: an empty `maps_to` is dropped or folded (F3), unknown entry keys are kept as written (F4), and the migration tests compare whole-file text with no internal reads (F2, F5).
    - **F8 verified Fixed.** In the bundled CLAUDE.md, the loop gate names reviews and findings again, and the tree line lists the field. The new template text puts a fixed "a" before the type name: see F18.
    - **F6 Fixed** (comment on F6). **F7**: the hint is fixed; MANUAL point 2 holds for the head but not for items and sub-entities (comment on F7). Stays Open.
    - **TASK-1254 verdict: changes requested, low severity only** (F16 to F19). The option, messages, wire shapes and head context work on both squads (driven: `--outcome`/`--no-outcome`, `--story` refused with exit 2 on the override squad, "outcome OC9 not found in INI-15", flat `impact` with `maps_to` always present, no `priority` on tree nodes). `display.maps_to_kind` is needed, since the renderer cannot derive the target kind from the DTO, but section 7 should list it (F19). The `known` filter weakens only the bare pairs (F17).
    - @manager route F16 to F18 to the TASK-1254 dev, F19 to @architect (amend section 7 or ask for code), and F7's wording to whoever owns the 0.19 runner text. F9 to F15 remain with the TASK-1253 dev. Approval stays with you.
- [2026-10-29T22:01:39Z] `manager` Catherine Manager:
  - Ruling on F18 (operator: nothing hardcoded): help text counts too; no article is chosen in code anywhere, help included: phrase help and messages so they need none. F19 and F7 point 2 go to the architect (amend ADR-1250 sections 7 and 8 or call for code); F16-F18 to the TASK-1254 dev once a developer slot frees.
- [2026-10-29T22:05:16Z] `architect` Robert Architect:
  - ADR-1250 amended in place 2026-10-29 for F7, F18 and F19 (sections 1, 7, 8; see its latest architect comment). F19 now has code to implement: badges on every sub-entity row, and maps_to_kind as a KindDisplay. F7 needs the runner MANUAL point 2 replaced by the exact text in section 8. F18 stands as ruled, and section 1 now states it. @manager route to the devs.
- [2026-10-29T22:24:59Z] `python-dev` Elias Python:
  - F16 to F18 fixed in f254f57c, with the F19 code changes and MANUAL point 2 text. Head tests dropped: only the frozen 0.2 to 0.3 runner reaches that renderer and its own migration guards it.
- [2026-10-29T22:33:56Z] `reviewer` Paul Reviewer:
  - - Third pass, at 7632d602 (origin/release/0.19), driven with the dev tree on fresh bundled and override scratch squads.
    - **F9 to F14 verified Fixed.** F9: on the bundled squad, add-finding lines with a null or empty severity import and create findings with no severity. F10: an empty `--priority` or `--work-size` is refused on create and update, as in 0.17. F11: the reflog records `--<code>`, `--no-<code>`, `--set` and `--unset` changes. F12: the three lint cases assert whole messages. F13: the internal file read and the substring asserts are gone; the markers wait for TASK-1256. F14: refusals name the op the file wrote, a comment selector names the declared selectors, and `story` on add-sub points to `maps_to`. The `bundled_known()` cache fix in tests/_cli_surface.py unbinds the active spec, which is sound. **F15 reopened**: create help still lists the derived options after `--help` (comment on F15).
    - **TASK-1255: changes requested, low and info only.** The operation, binding, handler, refusal before any write, rollback, reflog line and system comment hold on both squads. The check rule scans entries and names the verb; it does not flag `deferred_to`. F20: the kind-rename test cannot fail on its claim. F21: a changed `local_prefix` is silent (architect). F22: test and wording gaps. F23 (info, architect): the move has no scope.
    - **TASK-1257: changes requested.** npm test 768 passed and test:canary 90 passed against the dev tree in a throwaway copy. Client source carries no bundled vocabulary in the diff. F24 (medium): the mapping label is made in code ("Step_kind" vs the server's "Step_Kind"), and the show rows the preview reads carry no label to use, so the architect must name a source. F25: the fixtures to regenerate after the TASK-1254 wire fixes.
    - Notes, not findings (pre-existing): `src/domain/displayNode.ts` maps bundled type names to icons; `sq create <custom-type> --help` shows `--install-completion`/`--show-completion` (the temporary Typer in `_build_create_cmd`, since b2f4c1cb).
    - @manager route F15 to the TASK-1253 dev, F20 and F22 to the TASK-1255 dev, F21, F23 and F24 to @architect (F24's client change follows that ruling and the F19 code), and F25 to the TASK-1257 dev once TASK-1254 lands. Approval stays with you.
- [2026-10-29T22:39:32Z] `python-dev` Elias Python:
  - F15, F20 and F22 fixed in eefd60e7 (create routes its derived options through the same insertion as update; target-kind rename test; itself-refusal, reflog plus system comment, and no-kind wording cases). Observed, not fixed: after renaming the target kind outcome to goal, show on a goal prints "(no body yet)" for entries that had a body, since block markers are named by kind. @architect for F21/F23 context.
- [2026-10-29T22:40:44Z] `architect` Robert Architect:
  - F21, F23 and F24 ruled; ADR-1250 amended in place 2026-10-29 (sections 3, 6, 7, 11 and options; see its latest architect comment).
    
    - F24: a kind's label is the declared `label`, else its title-cased name, from one spec resolver. Every sub-entity `display` carries `maps_to_kind` (a `KindDisplay`, null when the kind does not map), so the preview reads `display.maps_to_kind.label` from the `show` row it renders. The catalog rows gain `label`. The client drops `buildMappingKinds` and `mappingLabel` and shows the mapping line only when `maps_to_kind` is set, with no fallback text. The CLI renderers stop lowercasing and title-casing labels.
    - F21: a kind's name, plural and local prefix are stored spellings (block markers, container marker, local ids and `maps_to`). New verb `sq migrate rename-kind <old> <new>` moves them; new check rule `subentity_kind_mismatch` reports a stale one and names the verb. Section 6's "a renamed kind needs no data move" was wrong and is replaced.
    - F23: `rename-field` gains `--type` and `--kind` scopes, repeatable; unscoped behaviour is unchanged. The `frontmatter_key_undeclared` finding names the scoped command.
    
    @manager route to the devs: F24 server side with the TASK-1254 dev and the client side with the TASK-1257 dev; F21 and F23 with the TASK-1255 dev.
- [2026-10-29T22:41:02Z] `architect` Robert Architect:
  - The kind-rename body orphaning (outcome to goal, prefix kept) is covered by the same ADR-1250 section 6 ruling as F21: block markers stay keyed by kind name; `sq migrate rename-kind outcome goal` rewrites them marker-safely, and `subentity_kind_mismatch` reports a block marker whose kind tag is not the hosted kind, naming that command. The "renamed kind needs no data move" sentence is gone.
<!-- sq:discussion:end -->
