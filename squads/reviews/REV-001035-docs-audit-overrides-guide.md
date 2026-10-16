---
id: REV-1035
sequence_id: 1035
type: review
title: 'Docs audit: overrides guide'
status: Approved
author: reviewer
description: Claim-by-claim audit of docs/overrides.md against the release/0.16 dev
  build
subentities:
- local_id: F1
  title: Troubleshooting claims unknown role TOML fields are kept in extra; they are
    refused at load
  status: Fixed
  severity: high
- local_id: F2
  title: Grammar rule 5 says a [selected] name that does not exist is not an error;
    it is a hard stop
  status: Fixed
  severity: high
- local_id: F3
  title: The [selected].items example also drops contract and milestone, not only
    guide
  status: Fixed
  severity: medium
- local_id: F4
  title: Layout tree and scaffold example name templates that do not exist and omit
    ones that do
  status: Fixed
  severity: medium
- local_id: F5
  title: The role catalog override (.overrides/roles.toml, scaffold/diff/update roles)
    is undocumented
  status: Fixed
  severity: medium
- local_id: F6
  title: Validators section says four checks ship unselected; eleven do, seven documented
    nowhere
  status: Fixed
  severity: medium
- local_id: F7
  title: Records types do appear in sq inbox; the doc says they never do
  status: Fixed
  severity: medium
- local_id: F8
  title: Role name is stored as the ROLE item title, not extra.full_name
  status: Fixed
  severity: medium
- local_id: F9
  title: Broken internal anchor to the workflow-overrides section at line 1682
  status: Fixed
  severity: medium
- local_id: F10
  title: Statuses reference lists role as required, then says it defaults to pending
  status: Fixed
  severity: low
- local_id: F11
  title: An unstamped template override is an error and drifted; the doc only covers
    old stamps
  status: Fixed
  severity: low
- local_id: F12
  title: Records example uses PM-1 and sq postmortem 1; the global counter makes that
    a role
  status: Fixed
  severity: low
- local_id: F13
  title: Playbook guide fields handoff, watch and authors (the create-lane flag) are
    undocumented
  status: Fixed
  severity: low
- local_id: F14
  title: Task-template example drops the required sq:discussion marker, so the override
    is broken
  status: Fixed
  severity: high
- local_id: F15
  title: Quoted sq check and lifecycle messages are stale
  status: Fixed
  severity: low
created_at: '2026-10-16T08:50:43Z'
updated_at: '2026-10-16T11:26:17Z'
---
<!-- sq:body -->
Audit of `docs/overrides.md` (2,112 lines) against the dev build on `release/0.16`. Every concrete claim was either driven in a scratch squad (`sq -C <scratch>` with the dev build: scaffold/list/diff/update, each TOML example loaded through `sq workflow lint`, each quoted error provoked) or read in the source (`_specmerge.py`, `_workflow/_loader.py`, `_workflow/_models.py`, `_overrides/_service.py`, `_cli/_override.py`).

What holds: the override grammar section (deep merge, leaf arrays, splat-refs, `$(`/`$$(` escaping, `[selected]` sections), the validator grammar and every quoted loader refusal, the ref-kind floor and drop/rename behaviour, derived views and their drop/disable flow, playbook rules and messages, drift stamps, `[init.names]`, role renames and `sq reflog`, the `.claude` template override answer, and the per-tech developer override. No ticket IDs or build-process narration were found.

What does not hold is filed as findings: three false statements a user would act on (the custom task-template example, the role-field troubleshooting answer, the `[selected]` filter claim), a stale layout and scaffold example, an undocumented override kind, an undocumented majority of the selectable validators, a false `sq inbox` claim, and a handful of stale quoted messages and contradictions.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1035 add-finding "…" --severity medium`; track with `sq review 1035 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Troubleshooting claims unknown role TOML fields are kept in extra; they are refused at load

<!-- sq:finding:F1:body -->
**Where:** `docs/overrides.md:2108-2112` (Troubleshooting, last question).

**Doc says:** "Role TOML overrides accept any field you add — they're flexible. If it's a field squads doesn't recognize, it's preserved in `extra` and available to your own templates."

**True today:** a per-role override has a closed key space and an unknown key is refused by name, which then makes `sq role <slug> show` refuse and `sq sync` refuse once the role is on the roster.

**Verified (driven):** `.overrides/roles/architect.toml` with `favourite_colour = "blue"` → `sq sync` fails: `favourite_colour: unknown top-level key 'favourite_colour' — use one of the accepted top-level keys in v0.15.0: ['agreements', 'can_spawn', 'color', 'description', 'full_name', 'is_default', 'mission', 'model', 'responsibilities', 'selected', 'slug', 'title']`; `sq check` reports the same as an error.

**Fix:** replace the answer with: unknown keys are refused at load, the accepted keys are the ones the refusal lists (quote them), and there is no pass-through to templates. Also the doc nowhere lists `is_default`, `slug`, `selected` as accepted per-role keys; either document them or leave the message as the authority.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T09:11:07Z] Theo Writer:
  - Fixed in docs/overrides.md Troubleshooting (last Q): unknown role keys are refused at load; quotes the accepted-keys refusal (driven).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Grammar rule 5 says a [selected] name that does not exist is not an error; it is a hard stop

<!-- sq:finding:F2:body -->
**Where:** `docs/overrides.md:1235` (grammar rule 5, `[selected]`).

**Doc says:** "**Naming something that doesn't exist is not an error.** The list is a filter, not an assertion."

**True today:** a `[selected].<section>` entry that names an undeclared key is a load-time hard stop, so every `sq` command refuses until it is removed.

**Verified (driven):** `[selected] items = [..., "nonexistent", ...]` → `sq workflow lint`: `selected.items.nonexistent | unknown items key 'nonexistent' | use one of the accepted items keys in v0.15.0: ['bug', 'contract', 'decision', ...]`; `sq list` refuses with the same cause. Source: `_specmerge.py` `_validate_selected` collects an `unknown {section} key` violation per unknown name.

**Fix:** invert the bullet: "Every name in a `[selected]` list must exist in the merged spec — a typo or a type you have not declared yet is refused with the accepted set." This also matters for the "list your own additions too" bullet just above: the addition must be declared in the same file, not planned.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T09:11:11Z] Theo Writer:
  - Fixed in docs/overrides.md grammar rule 5: every [selected] name must exist; quotes the unknown items key refusal (driven).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — The [selected].items example also drops contract and milestone, not only guide

<!-- sq:finding:F3:body -->
**Where:** `docs/overrides.md:1214-1219`.

**Doc says:** the example `items = ["epic", "feature", "task", "bug", "decision", "review", "role", "skill", "operator"]` means "That squad has no `guide` type: it is absent from the list, so it is dropped."

**True today:** the bundled spec also ships `contract` and `milestone`; the example silently drops those two as well. A reader copying it loses two types the text never mentions.

**Verified (driven):** loaded the example in a fresh scratch squad; `sq workflow types` lists epic, feature, task, bug, decision, review, role, skill, operator — no contract, no milestone (and no guide).

**Fix:** either add `"contract", "milestone"` to the list so the example drops exactly `guide`, or change the sentence to say it drops guide, contract and milestone. Prefer the former: the surrounding prose reasons about one dropped type.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T09:11:14Z] Theo Writer:
  - Fixed in docs/overrides.md grammar rule 5: example now keeps contract and milestone, drops only guide (driven: sq workflow types).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Layout tree and scaffold example name templates that do not exist and omit ones that do

<!-- sq:finding:F4:body -->
**Where:** `docs/overrides.md:48-80` (Override layout tree) and `:1648` (`sq override scaffold subentities/story.md.j2`).

**Doc says:** the layout lists `templates/subentities/story.md.j2`, `subtask.md.j2`, `finding.md.j2`, `block.md.j2`, `summary.md.j2`; `items/` with seven files; `agents/role.md.j2` only; `claude/` with three files; and no `roles.toml`. The scaffold section offers `subentities/story.md.j2` as a working example.

**True today:** bundled `_rendering/templates/` holds `subentities/{block,head,summary}.md.j2` (no per-kind files); `items/` adds `contract.md.j2`, `milestone.md.j2`, `_default.md.j2`; `agents/` adds `operator.md.j2`, `skill.md.j2`; `claude/` adds `settings.json.j2`; plus `agents_md/agents_section.md.j2` and `views/*.md.j2` (six files). `.overrides/roles.toml` is also an override file (see the separate finding).

**Verified (driven):** `sq override scaffold subentities/story.md.j2` → `error: no bundled template 'subentities/story.md.j2' — use a path like 'items/task.md.j2' or 'agents/role.md.j2'`; `subentities/block.md.j2` scaffolds fine. Tree listed with `ls -R` on the package.

**Fix:** regenerate the tree from the bundled directory (or describe it as "mirrors `_rendering/templates/`, see `ls` of the package" and list only the overridable families), replace the `subentities/story.md.j2` example with `subentities/block.md.j2`, and add `roles.toml` beside `workflow.toml` / `playbook.toml`.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T09:11:17Z] Theo Writer:
  - Fixed in docs/overrides.md Override layout: tree regenerated from the bundled templates dir, roles.toml added; scaffold example now subentities/block.md.j2 (driven).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The role catalog override (.overrides/roles.toml, scaffold/diff/update roles) is undocumented

<!-- sq:finding:F5:body -->
**Where:** whole doc; the only mention is a passing `.overrides/roles.toml` at `docs/overrides.md:1046`. The command-group section (`:1634-1781`) and `sq override list` columns (`:1769-1771`, "Kind: `template`, `role`, `workflow`, or `playbook`") omit it.

**Gap:** the role **catalog** override — `.overrides/roles.toml`, a whole-document override of `[[roles]]`, `[bundles]`, `[dev]` (name pool, default dev model) with its own `[selected]` — exists with a full command surface: `sq override scaffold roles` / `--roles-catalog`, `sq override diff roles`, `sq override update roles`, and a fifth `list` kind `roles`. It also has its own drift/stamp messages (`shadowing role catalog override has no squads:override-base stamp`).

**Verified (driven):** `sq override scaffold roles` writes a stamped, commented worked example; `sq override list` shows `roles  roles  0.15.0  current`. Source: `_cli/_override.py` (`roles_catalog` option on scaffold/diff/update), `_overrides/_service.py` (`OverrideEntry.kind` docstring: "five kinds, not the two this field was once documented as").

**Fix:** add a subsection under "Override layout"/"Precedence rule" describing `roles.toml` (precedence: bundled roles.toml → roles.toml → per-slug file), add the `roles` forms to the scaffold/diff/update/list sections, and list five kinds in the `list` columns. `docs/workflow.md:1239` already names the file, so this doc is the odd one out.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T09:11:20Z] Theo Writer:
  - Fixed in docs/overrides.md: new subsection "The role catalog override: roles.toml" ([[roles]], [dev], [bundles], precedence, drop, stamp), plus roles forms in scaffold/diff/update/list (all driven).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Validators section says four checks ship unselected; eleven do, seven documented nowhere

<!-- sq:finding:F6:body -->
**Where:** `docs/overrides.md:331-338`, `:603-607` ("The four checks nothing bundled selects"), `:1286-1289` ("Four checks ship unselected: ...").

**Doc says:** exactly four validators are selectable but unselected by the bundled spec: `parent_present`, `ref_rule_target_present`, `no_status_banner`, `subentity_title_max`.

**True today:** `_workflow/_models.py::UNGUARDED_VALIDATOR_NAMES` holds thirteen names; after removing `no_parent` (records bundle) and `item_skill_shadowed` (bundled `skill` type), **eleven** ship unselected. The seven the doc never mentions: `item_title_max` (`:N` threshold on an item title), `ref_rule_target_typed`, `body_written`, `description_present`, `assignee_present`, `settled_requires_discussion`, `external_id_not_in_title` (requires a parameter). None of them appears anywhere under `docs/` (grep).

**Verified (driven):** each of the six parameterless/optional-parameter names loads via `sq workflow lint` on `[items.task] validators = [...]`; `item_title_max:30` + `description_present@warn` then report on `sq check`: `warn TASK-21: title is 40 chars (threshold: 30) — an item title is a one-line handle...` and `warn TASK-21: description is empty — set a summary...`. `external_id_not_in_title` bare is refused: `is missing its required parameter`. Registered in `_services/_validators.py:928-...`.

**Fix:** replace the "four checks" statements with the full unselected list and one line each (what it checks, parameter if any, whether it gates writes per the frontmatter-only rule the doc already explains), or point at `sq workflow lint`'s refusal list as the authority and keep the prose to "the checks nothing bundled selects".
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T09:11:23Z] Theo Writer:
  - Fixed in docs/overrides.md Validators: eleven unselected checks listed; new "work-policy checks" table with params, gate participation and example (driven).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Records types do appear in sq inbox; the doc says they never do

<!-- sq:finding:F7:body -->
**Where:** `docs/overrides.md:280-283` ("never appears in `sq inbox` by default") and `:317` ("**Records never appear in `sq inbox` by default;** they're indexed for reference, not active work tracking.").

**True today:** `sq inbox <role>` lists the comment lines that `@mention` the role, on any item type; there is no category filter.

**Verified (driven):** declared the doc's `postmortem` records type, `sq create postmortem "API outage" --author architect` → PM-21, `sq postmortem 21 comment --as architect -m '@reviewer look'`, then `sq inbox reviewer` → `PM-21 API outage (Draft) — @reviewer look`. Read: `_services/_collab.py::inbox` has no category/records branch.

**Fix:** delete both sentences, or replace with what is true about records: no parent, own folder, settled statuses hidden from `sq list` per the status role's `hidden` flag (that is role-driven, not category-driven, so say so).
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T09:11:26Z] Theo Writer:
  - Fixed in docs/overrides.md records section: both false inbox sentences replaced; records appear in sq inbox while not settled, like any item (driven).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Role name is stored as the ROLE item title, not extra.full_name

<!-- sq:finding:F8:body -->
**Where:** `docs/overrides.md:1859` ("The chosen name is stored in the ROLE item's frontmatter (`extra.full_name`). Everything downstream reads from there").

**True today:** the name is the ROLE item's `title`; the frontmatter `extra` block carries only `slug` (and, for a developer, `is_dev`/`tech`/`model`). `_roles/_resolver.py` says so: "The name comes from `item.title`, not `extra.full_name`".

**Verified (read):** `squads/agents/roles/ROLE-000001-*.md` of a fresh scratch squad: `title: Catherine Manager` / `extra: {slug: manager}` — no `full_name` key. `sq role activate architect --name "Chief Designer"` writes `title`.

**Fix:** "stored as the ROLE item's `title`". (This is independent of the planned frontmatter flattening — `extra.full_name` is not written today either.)
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T09:11:29Z] Theo Writer:
  - Fixed in docs/overrides.md "How names flow into your squad": name is stored as the ROLE item title (read from a scratch role file).
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Broken internal anchor to the workflow-overrides section at line 1682

<!-- sq:finding:F9:body -->
**Where:** `docs/overrides.md:1682`.

**Doc says:** `[Workflow overrides](#workflow-overrides-item-types-statuses-badge-collections-and-ref-kinds)`.

**True today:** the heading at `:192` is "Workflow overrides: item types, statuses, badge collections, ref kinds and views", whose slug is `#workflow-overrides-item-types-statuses-badge-collections-ref-kinds-and-views`. The link lands nowhere.

**Verified (read):** slugified every heading in `docs/*.md` and checked every `](...)` target in this file; this is the only broken one (all `workflow.md#...` cross-references resolve).

**Fix:** update the anchor to `#workflow-overrides-item-types-statuses-badge-collections-ref-kinds-and-views`.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T09:11:33Z] Theo Writer:
  - Fixed in docs/overrides.md sq override scaffold section: anchor now ...-ref-kinds-and-views; all doc anchors checked.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Statuses reference lists role as required, then says it defaults to pending

<!-- sq:finding:F10:body -->
**Where:** `docs/overrides.md:665-668` vs `:673-675` (Statuses field reference).

**Doc says:** under "Required fields": "`role` — the name of a status role ..."; nine lines later: "If you omit `role`, a status defaults to the `pending` role".

**True today:** the second sentence is right; `StatusSpec.role` is `str | None = None` and a status without `role` loads and resolves to `pending`.

**Verified (driven):** `[statuses.NoRole] badge = "x"` plus a transition to it → `sq workflow lint`: OK; `sq workflow statuses` shows `NoRole  pending  x`.

**Fix:** move `role` under "Optional (defaults to `pending`)"; keep the explanatory sentence.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T09:11:36Z] Theo Writer:
  - Fixed in docs/overrides.md Statuses: role moved under optional fields, defaults to pending (driven).
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — An unstamped template override is an error and drifted; the doc only covers old stamps

<!-- sq:finding:F11:body -->
**Where:** `docs/overrides.md:1523-1525` ("The stamp alone is never a problem"), `:1527-1536` (structural errors), `:1772-1773` ("`(unstamped)` for a shadowing override that has no stamp yet").

**Gap:** a **template** override with no `squads:override-base` stamp is itself reported by `sq check` and classified `drifted` by `sq override list`; the doc only ever describes an old stamp (fine) or a missing marker (error), and the `list` legend implies unstamped only arises for shadowing TOML overrides.

**Verified (driven):** deleted the stamp line from `.overrides/templates/items/task.md.j2` → `sq override list`: `items/task.md.j2  template  (unstamped)  drifted`; `sq check`: `error .overrides/templates/items/task.md.j2: override has no squads:override-base stamp; run `sq override scaffold --force` to re-scaffold with a stamp, or `sq override update` after verifying the content`. `sq override update items/task.md.j2` stamps it.

**Fix:** under "How staleness is detected" add: a template override must carry the stamp; one hand-created without `sq override scaffold` is reported until `sq override update <name>` stamps it. Adjust the `list` legend to "(unstamped) for an override that has no stamp".
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-16T09:11:39Z] Theo Writer:
  - Fixed in docs/overrides.md "How staleness is detected": unstamped template override is an error and drifted, sq override update stamps it; list legend adjusted (driven).
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Records example uses PM-1 and sq postmortem 1; the global counter makes that a role

<!-- sq:finding:F12:body -->
**Where:** `docs/overrides.md:302-315` (records example: "IDs like `PM-1`, `PM-2`"; `sq postmortem 1 body ...`, `sq postmortem 1 status Published`).

**Doc implies:** a new type's items number from 1.

**True today:** the counter is global across all types, and `sq init` allocates the roster items first (eight roles plus the skills), so in a fresh squad the first postmortem is `PM-21`, and `sq postmortem 1 ...` addresses a role.

**Verified (driven):** after `sq init` and the override, `sq create postmortem "API outage" --author architect` → `PM-21`; `sq postmortem 1 body --file ...` → `error: 1 is ROLE-1 (role), not a postmortem`. With `21` every command in the example works (`PM-21 → Published`; `sq list -t postmortem` lists it).

**Fix:** write `PM-<n>` and `sq postmortem <n> ...`, with one sentence that the number is the squad-wide sequence, not per type. Also drop "(shown at all times)" at `:314` or say what it means — visibility follows the status role's `hidden` flag, which for `Published` (`in_force`) is false.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-16T09:11:42Z] Theo Writer:
  - Fixed in docs/overrides.md records example: PM-<n> / sq postmortem <n> with the squad-wide sequence sentence; "shown at all times" replaced by the hidden-flag rule (driven).
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Playbook guide fields handoff, watch and authors (the create-lane flag) are undocumented

<!-- sq:finding:F13:body -->
**Where:** `docs/overrides.md:1380-1412` (Playbook → Format).

**Gap:** the only guide fields shown are `slug`, `enter`, `do`. The model (`_interactions/_models.py::RoleGuide`) also has `handoff` (trigger + target that moves work on), `watch` (pitfalls), and `authors: bool` — the one with behaviour: `authors = true` declares the role an in-lane author of the type, and `sq create <type> --author <role>` warns when the author has no such guide. The scaffolded `playbook.toml` documents all of this in its header comment; the guide does not, and `authors` appears nowhere under `docs/`.

**Verified (read):** model fields at `_interactions/_models.py:19-24`; scaffold header text from `sq override scaffold playbook` in a scratch squad; `grep -rn 'authors = true' docs/` → nothing.

**Fix:** add a field table for a guide entry (`slug`, `enter`, `do`, `handoff`, `watch`, `authors`) with the create-lane sentence, and show `authors = true` in the splat example for a role meant to author the type.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-16T09:11:45Z] Theo Writer:
  - Fixed in docs/overrides.md Playbook Format: guide field table (slug/enter/do/handoff/watch/authors) and an authors = true example (driven).
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Task-template example drops the required sq:discussion marker, so the override is broken

<!-- sq:finding:F14:body -->
**Where:** `docs/overrides.md:1933-1952` (Examples → "Customize the task template").

**Doc says:** edit the scaffolded task template "keeping the required ``sq:body`` marker", and shows a template whose only marker region is `sq:body`. "The next time a task is created or rendered, it will use your template."

**True today:** the required set is derived from the bundled template, and `templates/items/task.md.j2` carries both `sq:body` and `sq:discussion`. The example as written is a broken override.

**Verified (driven):** wrote the example verbatim into `.overrides/templates/items/task.md.j2` of a scratch squad. `sq check` → `error .overrides/templates/items/task.md.j2: override is missing required sq marker(s): `sq:discussion` (breaks marker-safe editing; add the missing regions)`; `sq override list` → state `broken`; the bulk `sq override update` skips it.

**Fix:** add the ``sq:discussion`` / ``sq:discussion:end`` pair (under a `## Discussion` heading, as the bundled file has) to the example, and change the prose to "keeping every marker region the bundled template carries (`sq:body` and `sq:discussion` for a task)". The same correction applies to `docs/overrides.md:123` ("The required marker regions must still be present") which never names them.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-16T09:11:48Z] Theo Writer:
  - Fixed in docs/overrides.md Examples "Customize the task template": example keeps sq:body, the subtask container and sq:discussion; also the precedence-rule marker sentence names them (driven verbatim).
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Quoted sq check and lifecycle messages are stale

<!-- sq:finding:F15:body -->
**Where:** `docs/overrides.md:1518-1521` and `:1531-1533` (Staleness and drift), `:1264`.

**Doc quotes:** `override may be stale — bundled task.md.j2 changed since v<version>; run ...` and `.overrides/templates/items/task.md.j2: missing required marker `sq:body``; and, as the lifecycle example, `lifecycle 'agent': state 'Active' unreachable from initial 'Draft'`.

**True today:** `_overrides/_service.py:1370,1397`: `override is missing required sq marker(s): `sq:discussion` (breaks marker-safe editing; add the missing regions)` and `override may be stale: bundled items/task.md.j2 changed since v0.14.0; run `sq override diff items/task.md.j2`, merge, then `sq override update items/task.md.j2``. The lifecycle case most users hit (shadowing `[lifecycles.agent] initial = "Draft"`) prints `lifecycle 'agent': no status with a settled role reachable from initial 'Draft' (reachable: ['Draft']) — items on this lifecycle could never close; ...` (plus two more errors), not the "unreachable" form.

**Verified (driven):** missing-marker and lifecycle messages provoked in scratch squads; stale message read from source (no bundled task template changed between 0.14.0 and 0.15.0, so the warning could not be provoked — `sq override list` correctly stayed `current` with a 0.14.0 stamp, which confirms `:1523-1525`).

**Fix:** paste the current wording for the two `sq check` lines; for `:1264` either quote the reachability message or keep "e.g." and quote one that is actually the first a shadowed roster lifecycle produces.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-16T09:11:51Z] Theo Writer:
  - Fixed in docs/overrides.md Staleness: current wording for the stale and missing-marker lines. The lifecycle quote in "When an override is wrong" holds: the shadowed initial=Draft case still prints it (driven), kept as e.g.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T09:12:06Z] Theo Writer:
  - All 15 findings fixed in docs/overrides.md; every changed TOML/template example was pasted into a scratch squad, loads, and leaves sq check clean. @reviewer ready for re-check.
  - Two code observations while driving the roles.toml override (not doc fixes): sq init --roles <name> reads only the bundled bundles, so a bundle added in .overrides/roles.toml is refused there ("no predefined role"); and a roles.toml whose all bundle misses a new role made every role command refuse while sq check printed no issues in one scratch squad (another squad with items did report it).
- [2026-10-16T11:26:16Z] Catherine Manager:
  - Approved: every finding Fixed (re-run by the writer on the dev build) or closed with a home; cross-doc seams checked in REV-1047.
<!-- sq:discussion:end -->
