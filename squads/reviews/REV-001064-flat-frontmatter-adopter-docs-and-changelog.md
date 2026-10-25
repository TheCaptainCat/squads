---
id: REV-1064
sequence_id: 1064
type: review
title: Flat frontmatter adopter docs and changelog
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1059
description: Claim-by-claim re-run of the flat-frontmatter, attributes and stored-role-name
  docs against the dev build
subentities:
- local_id: F1
  title: Unknown keys kept claim omits the retired role-key sweep
  status: Verified
  severity: medium
- local_id: F2
  title: Hand-added key needs sq repair before the next write
  status: Verified
  severity: low
- local_id: F3
  title: Frozen item-row shape omits the path key every row carries
  status: Verified
  severity: low
- local_id: F4
  title: Role model set through import is ignored on a bundled role
  status: Verified
  severity: low
- local_id: F5
  title: Which name wins uses title for both job title and name
  status: Verified
  severity: low
- local_id: F6
  title: Duplicate-name remedy for a role omits the final sq sync
  status: Verified
  severity: low
- local_id: F7
  title: Import rename route reports the pointer as drifted
  status: Verified
  severity: info
- local_id: F8
  title: Every item has slug and refs overclaims the file shape
  status: Verified
  severity: low
- local_id: F9
  title: Unselected-checks list omits blocked_has_blocker
  status: Verified
  severity: low
- local_id: F10
  title: No-update-verb passages go stale when FEAT-977 lands
  status: WontFix
  severity: info
- local_id: F11
  title: Repo CLAUDE.md still names ExtraKey and _extras.py
  status: Verified
  severity: low
created_at: '2026-10-16T17:05:08Z'
updated_at: '2026-10-25T19:37:13Z'
---
<!-- sq:body -->
## Scope

The adopter docs and CHANGELOG for the flat frontmatter, the attributes grammar and stored role names, as committed in 1e2c1d1e on release/0.16: `CHANGELOG.md`, `README.md`, `docs/migration.md`, `docs/overrides.md`, `docs/stability.md`, `docs/roles.md`, `docs/internals.md`, `docs/adoption.md`, `docs/faq.md`. Read against ADR-1007 (with its decision 5 note), the ADR-777 section 3 note, BUG-1049's WontFix ruling and the newest role-name ruling on TASK-1059: a role's stored name is its name, and no configuration change renames it.

## Method

Each claim was re-run with the dev build (0.16.0) on scratch squads under the session scratchpad. Each squad sat in its own git repository, and the 0.15 squads were built with the released 0.15.0. The dev build never pointed at this repository's squad.

Re-run and matching the docs:

- the flattening report lines: files flattened, keys lifted per key, the operator retitled with its file line, and the dropped-description line;
- the step summary text;
- the four flattening refusals, verbatim, joined in one "4 problem(s) found." refusal that wrote nothing;
- the two header refusals: "matches 2 entries" and "matches no roster entry". The latter shows that an operator is matched by its stored full name;
- the operator retitle row;
- retired role keys under `extra:` are dropped, and a hand key is lifted;
- the duplicate-name remedy end to end, for an operator and for a role;
- the role-name rule at creation: per-slug, then roles.toml, then bundled, through `init --default-names`, `role activate` and `dev add`, plus the pool;
- `sq sync` after the override names change renames nothing, and the model still applies;
- the rename-by-import route, with the reflog old/new entry, the pointer and the CLAUDE.md roster;
- a custom role attribute set through import;
- `--set` and import kind refusals, plus bool coercion in any case;
- `sq check` wrong-kind and missing-required messages;
- `frontmatter_key_undeclared` warn text;
- loader refusals: reserved name, `badges`, `extra`, the pinned role kind, the `extra_fields` text;
- `workflow types --json` attributes, matching the bundled list in overrides.md;
- `--json` rows with a stored `badges` kept out of the row;
- the template `item.<key>` guard, and the `extra` variable gone;
- an unquoted date normalized on write;
- a core key of the wrong type refused with the file named;
- `sq repair` stripping the mirrored role keys;
- no update verb on role, skill or operator.

Grep: `extra_fields`, `name_chosen`, `pool_name` and an available roster `update` verb are documented nowhere as current; `extra:` remains only in migration passages about the earlier shape. Anchors linked from the CHANGELOG and docs resolve.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1064 add-finding "…" --severity medium`; track with `sq review 1064 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Unknown keys kept claim omits the retired role-key sweep

<!-- sq:finding:F1:body -->
**Where.** `docs/stability.md:85-87` ("A key no declaration names is carried through every write, `sq repair` and every migration"), `docs/overrides.md:503-505` ("No command removes a key it was not asked to change"), `CHANGELOG.md:74` (the Fixed entry: "kept on every write, by `sq repair` and by `sq migrate up`").

**Truth (driven, dev build).** A closed set of undeclared keys on a role is removed:

- `sq repair` stripped top-level `mission`, `full_name` and `color` from a role file. It kept `hand_key` and reported "stripped retired regions from 1 item file".
- The 0.16 step drops the same keys under `extra:`, as migration.md itself says.
- Once `color` was declared as a `role` attribute, `sq repair` and `sq sync` kept it.

So the sweep removes exactly the undeclared retired role keys. adoption.md and faq.md describe this, but stability.md, overrides.md and the CHANGELOG state the guarantee with no exception. In stability.md the statement sits in a frozen contract section.

**Fix.** Name the exception wherever the guarantee is stated. A role's retired definition keys (`full_name`, `mission`, `responsibilities`, `agreements`, `color`, `can_spawn`, `skills`) are removed by `sq repair`, `sq sync` and the 0.16 step unless the `role` type declares them. Link to adoption.md's list.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: docs/stability.md and docs/migration.md name the role-definition key sweep as the one exception to keeping unknown keys.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Hand-added key needs sq repair before the next write

<!-- sq:finding:F2:body -->
**Where.** `docs/overrides.md:502-505` and `CHANGELOG.md:74` say a key added by hand is carried through every write.

**Truth (driven).** I hand-added `hand_key`, `systems`, `review_date` and `badges` to a guide on a migrated squad.

- The next write (`sq guide 19 comment`) was refused: "on-disk frontmatter has diverged from the index (badges, hand_key, review_date, systems) — run `sq repair` before mutating GUIDE-19 again".
- Before the repair, `sq check` reported only drift. `frontmatter_key_undeclared` stayed silent until `sq repair` had run.
- After `sq repair`, every key survived the write.

Nothing is lost, but the documented flow skips a step the reader will hit.

**Fix.** Say that after adding a key by hand, `sq repair` brings it into the index, and that writes are refused until then (as for any hand edit). Put this in the overrides.md passage and in the Fixed entry.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: docs/overrides.md says a hand-added key needs `sq repair` before the next write to that item.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Frozen item-row shape omits the path key every row carries

<!-- sq:finding:F3:body -->
**Where.** `docs/stability.md:691-696` (Item rows: "the item's core keys, each attribute its file stores ... and the keys the command adds"), echoed in `CHANGELOG.md:35` and `docs/migration.md` § "After the upgrade".

**Truth (driven).** `sq guide 19 show --json` and `sq list -t guide --json` both carry a top-level `path` key. `path` is neither in the core-key list stability.md gives nor an attribute or an added key. The same section freezes the row shape and tells a client that a non-core key is an attribute to look up in `sq workflow types --json`, so a client following the contract finds an unexplained key in every row. (The VS Code canary must also tolerate it.)

**Fix.** Name `path` in the row definition as a field every row carries (the file's path relative to the squad). Alternatively, drop it from rows in code, which is a code decision. Either way the frozen text and the payload must agree.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: docs/stability.md item-row contract describes the `path` key.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Role model set through import is ignored on a bundled role

<!-- sq:finding:F4:body -->
**Where.** `docs/overrides.md:447-449`: "Roles, skills and operators have no `update` verb, so their attributes are set through `sq import`."

**Truth (driven).** `{"op":"update","target":"ROLE-4","fields":{"model":"haiku"}}` on the bundled reviewer:

- imported fine and wrote `model: haiku` to the role file;
- `sq sync` kept it;
- `sq role reviewer show` and `.claude/agents/reviewer.md` still say `model: opus`;
- `sq check` is clean.

The same import on a developer (`python-dev`) did take effect. For a bundled role, `model` is a declared, settable attribute whose stored value is ignored.

**Fix.** Doc side: say that a bundled role's `model` comes from its definition, so it is set in `.overrides/roles/<slug>.toml` or `roles.toml`, and that the stored attribute counts only for a developer. Code side, for the tech lead to weigh: make the import refuse it on a bundled role, or have `sq check` report a stored model that the definition overrides.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T17:50:56Z] `qa` Mara Tester:
  - Filed as BUG-1065 (low): the import should refuse model on a non-developer role.
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: docs/overrides.md says a role's model is set in its role overrides; the import-side refusal stays with BUG-1065.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Which name wins uses title for both job title and name

<!-- sq:finding:F5:body -->
**Where.** `docs/overrides.md:2220-2223` (What `sq sync` keeps: "Everything else in a role's definition — its title, mission, ... — is refreshed from the bundled definition") against `docs/overrides.md:2226` ("Renaming an active role sets its stored `title`") and `docs/adoption.md:197` ("A role keeps its `title` (its name)").

**Truth.** On a role item `title` is the agent's name, and the catalog's `title` is the job title. In one section, "its title" means the job title (refreshed on every sync) and four lines later the stored `title` is the name (never refreshed). A reader cannot tell which survives a sync.

**Fix.** Say "its job title" in the sync paragraph, or name the catalog field explicitly ("the catalog `title`, the job title").
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: docs/overrides.md "Which name wins" separates the job title from the stored name.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Duplicate-name remedy for a role omits the final sq sync

<!-- sq:finding:F6:body -->
**Where.** `docs/migration.md:302-304`: the duplicate-name remedy ends with "Edit that `title:` line back to the real name and run `sq repair`".

**Truth (driven, role variant).** I renamed the role `tech-lead` for the run, ran `sq migrate up` and `sq sync` (as the migration's own output tells you), then edited `title:` back and ran `sq repair`. `sq check` then warned `.claude/agents/tech-lead.md: managed pointer had drifted — run sq sync`. The pointer and the CLAUDE.md roster still carried the name typed for the run until `sq sync` ran. The operator variant needs no sync and ended clean.

**Fix.** End the remedy with "then `sq sync`" (needed for a role, harmless for an operator).
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: docs/migration.md's duplicate-name remedy ends with `sq sync`.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Import rename route reports the pointer as drifted

<!-- sq:finding:F7:body -->
**Where.** `docs/overrides.md:2226-2235` and `CHANGELOG.md:39`: rename through an `sq import` `update` event, "then run `sq sync`".

**Truth (driven).** The route works: the title changed, the reflog recorded old and new, and the pointer and CLAUDE.md roster followed after sync. Between the import and the sync, though, `sq check` warns "managed pointer had drifted — run `sq sync`". The sync itself then prints "warning: .claude/agents/architect.md: had drifted — regenerated by this sync". The docs present the route as clean, so the "drifted" wording reads like an unexpected hand edit.

**Fix.** Either say in the docs that the sync reports the pointer as drifted and regenerates it, or (code) have the sync not call a pointer stale from a title change "drifted". Low impact: the remedy text is right.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: renames now go through `sq role <slug> update --title`, which refreshes the pointer and roster at once (driven on 0.17, no drift).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Every item has slug and refs overclaims the file shape

<!-- sq:finding:F8:body -->
**Where.** `CHANGELOG.md:31` ("Every item now has the core keys (`id`, `type`, `title`, `slug`, `status`, `refs`, …)") and `docs/migration.md:166` ("the core keys every item has (`id`, `type`, `title`, `slug`, `status`, `parent`, `refs`, …)").

**Truth (driven).** After the 0.16 step, `guides/GUIDE-000019-g1.md` stores no `slug`, `refs` or `parent`. Both passages sit in a sentence about what an item file keeps, so a reader takes the list as keys every file holds. stability.md and overrides.md say this correctly: `slug` is written on roster items and on files that carried it, and empty keys are omitted.

**Fix.** "the core keys it has a value for", or drop `slug`/`refs`/`parent` from the examples.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: CHANGELOG and docs/migration.md say a file holds the core keys it has a value for.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Unselected-checks list omits blocked_has_blocker

<!-- sq:finding:F9:body -->
**Where.** `docs/overrides.md:543-555`. The rewritten sentence ("These checks are not selected for you anywhere in the bundled spec, so naming one ... is the only way it ever runs") introduces a list that reads as complete, and it still counts "Seven policy checks".

**Truth (read).** `WORK_POLICY_VALIDATOR_NAMES` in `src/squads/_workflow/_models.py:265-275` has eight names, and includes `blocked_has_blocker`. `src/squads/_specs/workflow.toml` selects it nowhere. docs/ never mentions it, so an adopter cannot find it.

**Fix.** Add `blocked_has_blocker` with a one-line description and change "Seven" to "Eight". Do the same at the later mention (~line 1572, "the seven work-policy checks"). This needs the check's owner to supply the description if the writer cannot derive it.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: docs/overrides.md lists and documents `blocked_has_blocker`.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — No-update-verb passages go stale when FEAT-977 lands

<!-- sq:finding:F10:body -->
**Where.** `docs/overrides.md:449`, `:2226`, `:2471` and `CHANGELOG.md:39` document `sq import` as the way to rename a role or set a roster attribute, and say roles, skills and operators "have no `update` verb".

**Truth.** This is true of the build today (driven: `sq role ROLE-2 update`, `sq skill squads update` and `sq operator op-bob update` all exit with "No such command 'update'"). But the ruling of 2026-10-16 on TASK-1059 and the ADR-777 note name the role's update verb (FEAT-977) as the rename route, and FEAT-977 targets the same release (MILE-934, Ready). Once it lands, these four passages become false in the same unreleased section.

**Fix.** No change in this commit. Give FEAT-977's docs work these four passages to rewrite, so the release does not ship "no update verb" next to the verb.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T17:07:19Z] `manager` Catherine Manager:
  - Home: FEAT-977 (comment lists the passages).
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Repo CLAUDE.md still names ExtraKey and _extras.py

<!-- sq:finding:F11:body -->
**Where.** Repository `CLAUDE.md:36` ("`_extras` (`ExtraKey`)") and `CLAUDE.md:153` ("`Item.extra` keys come from `_models/_extras.py::ExtraKey`").

**Truth (read).** `_models/_extras.py` no longer exists; the module is `_models/_attributes.py` (`AttributeKey`, read through `item.attribute(...)`). This is contributor guidance, outside ST10's adopter-doc scope. The writer already flagged it, but it has no home, and every agent working on this repo reads it.

**Fix.** Re-point both lines at `AttributeKey`/`item.attribute()` and the "no string-literal reads" rule. The edit belongs to whoever owns CLAUDE.md (outside the managed region).
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-25T19:37:13Z] `reviewer` Paul Reviewer:
  - Holds: CLAUDE.md names `_attributes`/AttributeKey and no longer cites ExtraKey or _extras.py.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T17:06:31Z] `reviewer` Paul Reviewer:
  - ChangesRequested on one medium: F1, the "unknown keys are kept" guarantee in stability.md, overrides.md and the CHANGELOG Fixed entry leaves out the retired role-key sweep that sq repair, sq sync and the 0.16 step apply. Driven on a scratch squad.
  - Eight lows and two infos: F2 to F6, F8, F9 and F11 are doc fixes. F4 and F7 also carry a code question for the tech lead. F10 is a hand-off to FEAT-977 docs.
  - Everything else re-ran true on the dev build: every quoted refusal and report line, the duplicate-name remedy for both an operator and a role, role names at creation, sync renaming nothing, the import rename route, attribute --set, import, check and loader refusals, --json rows and templates. Not re-driven: the skill-description drop and differ lines, and the importer-shape operator row.
  - @tech-writer F1-F3, F5, F6, F8, F9. @tech-lead F4, F7, F11 and F10 routing.
- [2026-10-16T17:11:38Z] `tech-writer` Theo Writer:
  - Fixed in f3802eaf: F1 (the role-definition key sweep named as the one exception in stability, overrides, migration and the CHANGELOG Fixed entry), F2 (sq repair before the next write after a hand edit), F3 (path in the item-row contract, CHANGELOG and migration), F4 (re-run: a stored model is ignored on a bundled role and on a project role, and used on a developer; documented under settable), F5 (job title vs stored title), F6 (final sq sync in the remedy), F7 (drift report between import and sync; re-run), F8 (core keys the file has a value for), F9 (blocked_has_blocker added with its table row and driven warn text; Seven to Eight in three places, checked against WORK_POLICY_VALIDATOR_NAMES), F11 (CLAUDE.md outside the managed region now names _attributes, AttributeKey and item.attribute). Also corrected the ordered-collection default in overrides.md and workflow.md (an unordered collection is refused at load). The code questions in F4 and F7 stay with the tech lead. @reviewer
- [2026-10-16T17:12:10Z] `manager` Catherine Manager:
  - Approved: F1–F9 and F11 Fixed (claims re-run by the writer), F10 WontFix with home FEAT-977. Commit f3802eaf.
<!-- sq:discussion:end -->
