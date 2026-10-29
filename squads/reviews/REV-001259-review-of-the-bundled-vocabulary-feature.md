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
subentities:
- local_id: F1
  title: Badge keys move after the timestamps on first rewrite; normalise once in
    the runner
  status: Open
  severity: medium
- local_id: F2
  title: Migration tests do not guard item top-level keys; fixture lacks priority
    and severity
  status: Open
  severity: medium
- local_id: F3
  title: story with an empty maps_to loses the mapping silently in the 0.19 runner
  status: Open
  severity: low
- local_id: F4
  title: Unknown entry keys with empty values are dropped on write
  status: Open
  severity: low
- local_id: F5
  title: New tests read item files and the index directly and assert substrings (ADR-1172
    rule 5)
  status: Open
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
  status: Open
  severity: medium
created_at: '2026-10-29T21:09:02Z'
updated_at: '2026-10-29T21:11:25Z'
---
<!-- sq:body -->
## Scope

The tasks of FEAT-1249 (bundled vocabulary fully overridable), reviewed as each lands, against ADR-1250 (with the op-pierre rulings in its discussion), ADR-1172 for tests, and each task's acceptance.

- TASK-1251: generic badge and mapping storage and the 0.19 schema migration (commits 6feb2cf9 and a472109f, reviewed as `git diff 27242580..a472109f`; rebased onto release/0.19 as 228b5eaf, a4c38e57 and f408f091).
- TASK-1252: spec-derived aliases, neutral grammar names, headings and generated text (47811e26 on release/0.19). This pass covers the generated-text rewording only.

Later tasks of the feature are added here as they land.

## Method

- Read the diff against the ADR sections it implements (section 6 storage, section 8 migration, section 1 for the generated text).
- Ran the branch's `sq migrate up` on a copy of this repository's squad, then `sq check`, `sq repair`, a second `sq migrate up`, and a write to an item, and diffed the item files.
- Probed edge inputs on scratch squads: refusal paths, empty spellings, unknown entry keys, spec-load collisions.
- Mutated the code under four of the new tests and the runner once more to see which tests go red.

Each finding labels its claims driven (ran it), read (read the code) or inferred.

## Results that hold

- Driven: on a copy of this squad, the runner changed only `story:` to `maps_to:` lines (1052 of them in 305 task files); no other line of any item file moved. `sq check` reported nothing on the corpus beyond the copy's missing agent files and the override stamp; `sq repair` and a second `migrate up` rewrote no item file. `--json` shapes of an item row and a sub-entity object match the released tool.
- Driven: a refused run (an `extra` key equal to a core key) exits 1, names the item and the key, and leaves every file, `.squads.json` included, byte-identical.
- Driven: spec load refuses a kind named `sub`, a kind field `attributes` or `badges`, an item field `status`, and an attribute named like a field of the same type.
- Driven: the MANUAL step's first point holds on release/0.19 now that TASK-1252 is in: an override spelling `maps_parent_story` stops `migrate up` before any step, naming the new spelling.
- Driven: the four sampled new tests (empty severity dropped, refusal writes nothing, unknown key kept, kind named `sub`) each go red under a mutation of their subject.
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
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T21:10:18Z] `reviewer` Paul Reviewer:
  - Verdict on TASK-1251: changes requested. Storage and the runner are correct on this squad (driven: only story-to-maps_to lines change, refusal writes nothing, check and repair clean). Open before acceptance: F1 (key-order churn, a ruling on normalising once in the runner, ADR-1250 section 8), F2 (migration tests cannot fail on touched item keys), F3, F4, F5 (rule-5 ruling needed), F7 (re-check MANUAL point 2 when the wire task lands). F6 tracks literals the badge-options and wire tasks remove.
  - TASK-1252 generated text: F8 (medium). The rewording dropped the vocabulary where the spec can supply it, so the bundled loop gate no longer names reviews.
  - @manager route F1 and F5 to @architect and op-pierre for the rulings, F2 to F4 and F7 to the TASK-1251 dev, F8 to the TASK-1252 dev. Approval stays with you once the findings are dispositioned.
- [2026-10-29T21:11:25Z] `manager` Catherine Manager:
  - Manager rulings under the operator delegation for this drive (2026-10-29, flagged for op-pierre in the morning summary): F1: the 0.19 runner normalises key order once, moving top-level badge keys to the position the writer now uses, so the churn happens in the migration diff and never again; values untouched. The architect amends ADR-1250 section 8. F5: a migration test may read item files as plain text (the rewritten files are what migrate up produces), never through an internal function; .squads.json is never read and refusals assert whole lines. The architect amends ADR-1172 rule 5. Fix routing once pair 2 lands (dev cap 2): F2, F3, F4, F7 and the F1 runner change to the TASK-1251 dev; F8 to the TASK-1252 dev; F6 closes with the badge-options and wire tasks.
<!-- sq:discussion:end -->
