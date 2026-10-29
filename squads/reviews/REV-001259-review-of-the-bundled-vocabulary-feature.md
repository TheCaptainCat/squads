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
  status: Open
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
  status: Open
  severity: medium
- local_id: F10
  title: An empty value on a derived flag is dropped silently instead of refused
  status: Open
  severity: medium
- local_id: F11
  title: Badge changes through update no longer reach the reflog delta
  status: Open
  severity: medium
- local_id: F12
  title: Three derived-name collision refusals have no case; mutations stay green
  status: Open
  severity: low
- local_id: F13
  title: New tests misdeclare derived-flag markers, read an item file internally,
    assert substrings
  status: Open
  severity: low
- local_id: F14
  title: Import refusals name add-sub, not the op written, and miss the declared selectors
  status: Open
  severity: low
- local_id: F15
  title: Derived options are listed after --help
  status: Open
  severity: info
created_at: '2026-10-29T21:09:02Z'
updated_at: '2026-10-29T21:46:08Z'
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
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->
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
<!-- sq:discussion:end -->
