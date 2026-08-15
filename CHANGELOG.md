# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.0]

### Changed — action required

- **Retiring a role, skill or operator now withdraws it from your generated agent config.** Moving a roster entry to a status its lifecycle does not declare as live deletes the per-entry file the agent host reads — `.claude/agents/<slug>.md` for a role, `.claude/skills/<slug>/` for a skill, and the equivalent under every other host you have enabled — and rewrites every compiled region that named it: the rosters in `CLAUDE.md` and `AGENTS.md`, and the per-role sections of the generated `sq-<type>` skills. A retired role stops being spawnable and a retired skill stops being loadable, which is what retiring one was always supposed to mean. Previously the entry's status changed and the generated files stayed exactly as they were, so a retirement was a bookkeeping note the host never saw.

  **It is reversible, and reactivating is the whole of it.** `sq role <addr> status Active` re-renders the entry's file from its definition in full — description, model, colour, and its complete preloaded-skill list, custom skills scoped to it included — and puts its line back in every compiled region. There is no half-restored state to clean up and no `sq sync` to run afterwards; every enabled host is brought back into step inside the same command.

  **Action required if anything outside `sq` reads a generated file by path.** An editor setting, a script, or your own automation that opens `.claude/agents/<slug>.md` will find it gone once that role is retired. Point it at the role's definition under `squads/agents/roles/` instead — that is the durable copy, and a status change never deletes it.

- **Retiring the role that carries the default-role designation is allowed, and your generated config loses its default-role line.** Carrying the designation is not a reason to refuse a retirement, so the retirement goes through and the compiled instructions simply stop naming a default, rather than naming a role the host can no longer spawn. `sq` warns as it happens and names both ways back: designate another live role with `sq role <addr> set-default`, or reactivate the role you just retired. Until you do one of them, your generated instructions no longer say who picks up a request nobody else claims.

- **Recording who said something now requires saying so.** `--as` is mandatory on `sq <type> <n> comment`, on a sub-entity's `comment`, and on `sq board post`; a bulk-import event must carry an actor of its own, inherit one from an earlier event, or be given one with `--as`. Omitting it fails with `--as is required: the actor's slug` instead of silently recording the words in the operator's voice. Any script or automation that relied on the old default must pass an author explicitly — a role slug, or `op-<slug>` for a person. The discussion is append-only, so an attribution that lands wrong stays wrong; the flag was the only place that fact was knowable and it now has to be stated.

- **`default_role` is gone from `.squads.toml`.** Which role is the default is a property of the roster entry that carries it, so the config key was a second answer to the same question with nothing keeping the two in step. Newly initialised squads no longer write it, and a squad whose file still contains it loads unchanged — the key is ignored, with no migration to run.

- **`sq board list` and `sq repair` exit `1` when they name a file they could not read.** Both used to print `error: … is not valid UTF-8` and then exit `0`, so nothing downstream could tell a degraded listing from a clean one, or a partial rebuild from a finished one — which is the whole reason to test an exit code. Reporting an error at status `0` was the contract violation; this is the correction. In the same case `sq check` now reports the file as an error-level issue and exits `3`, where it used to abort as a runtime error at `1`. **Action required if anything branches on those exit codes** — a wrapper script, a CI step, an editor integration. No code was added or repurposed; what changed is which code these three commands hand back, so a squad carrying one unreadable file takes the failure branch where it used to take the healthy one. `sq board list --json` still writes a bare, valid JSON array to stdout and names the unreadable files on stderr, so a consumer keeps parsing what it can while `$?` tells it the read was short.

### Added

- **Roles, skills and operators can be moved through their lifecycle from the CLI.** `sq role <addr> status <S>`, `sq skill <addr> status <S>` and `sq operator <addr> status <S>` transition a roster entry much as the work-item `status` verb does, `--force` included for a transition the lifecycle itself disallows. The valid targets come from the type's own declared lifecycle, so a rejected transition names that type's states rather than a fixed list. Previously a roster entry could never leave the status it was created with.

- **A retirement can be refused, and `--unlink` is how you satisfy the refusal.** Two conditions stop a roster entry from leaving a live status. Retiring the last live role while an agent backend is enabled is refused, because the generated config would then have no agent to present. Retiring a skill that a live role still preloads is refused, because that role's file would go on naming a skill that is no longer there. Either way the message names the entry, states the condition, names the live roles a skill is still scoped to, and gives the next step where one exists.

  **`--unlink` severs the dependency rather than suppressing the check.** `sq skill <addr> status Archived --unlink` removes exactly the scoping edges the refusal enumerated, reports each one it removed, and then runs the ordinary check again — which passes on its own merits. If it still refuses, nothing changes: the flag can only remove what the refusal named. It is a real edit to your roster and not a bypass, so reactivating the skill later brings the skill back but not the scoping — re-attach it with `sq skill <addr> link-role <role>`. On a transition that is not a retirement the flag is an error rather than a no-op. `--force` overrides neither condition: it covers a transition the lifecycle itself disallows and nothing else, and neither of these is about a lifecycle edge.

  **Where no remedy exists, the refusal says so instead of inventing one.** A skill every live role preloads unconditionally cannot be retired at all, and a skill implied by a declared item type cannot be un-implied today. Both messages say that plainly rather than naming a step that would not work.

- **Your workflow override can now change the built-in vocabulary, not just add to it.** `.overrides/workflow.toml` composes over the bundled spec instead of being refused wherever it touches it. Three things follow. **Shadow** a built-in by writing only the fields you want changed — relabel `task` as "Ticket", give it an extra alias, retarget a lifecycle edge, re-prefix a type you have not started using — and everything you left out is inherited and keeps tracking the bundle. **Extend** a bundled list without copying it, using a splat-ref: `parents = ["$(*self)", "epic"]` means "everything the bundle allows, plus epics", so the list still improves when squads does. **Drop** a built-in you don't want with a top-level `[selected]` table naming the entries that survive. The reserved surface is down to what is structurally necessary — the three roster type keys `role`, `skill` and `operator` must exist and keep their category — and no status name is reserved at all, so a squad can name its lifecycle states in its own words, in any language. Previously the override could only add: shadowing a built-in type, status or lifecycle was an error, which meant the bundled vocabulary was the vocabulary.

  **Two costs come with it, both by design.** A built-in you shadow stops tracking the bundled spec, so `sq check` now asks a shadowing override to carry a `# squads:override-base:` stamp and warns when the bundled counterpart moves — `sq override diff workflow` shows what you changed and what the release changed, and `sq override update workflow` re-stamps once you have reconciled. And a broken override is a hard stop at load rather than a surprise mid-command: `sq` refuses to run until it is fixed, with `sq workflow lint` reporting every violation at once, each with a location and a fix hint. That hard stop now includes an override that is internally inconsistent rather than malformed: **a type may not declare a behaviour whose category then checks nothing.** Move `decision` to `category = "work"` and it keeps its `supersedes` rule while nothing verifies it any more — the check does not fail, it stops existing — so that is refused, as is a type hosting a sub-entity kind, or a kind declaring `maps_parent_story`, under a category that validates neither. The message names all three ways out: drop the declaration, leave the type in a category that checks it, or name the validator you want in the type's own `validators` list.

  **Two changes are refused against a squad that already has items.** A type's `prefix` and `folder` are how squads finds that type's files, so neither can change once items are filed under it; the refusal lists the affected IDs and names the two real ways forward — revert the field, or make the change while the type has no items. The same goes for dropping a type, a status, or a badge code that live items still carry. There is no command that realigns an existing corpus onto a changed prefix, and nothing pretends otherwise.

- **`sq workflow subentity-kinds --json` publishes the sub-entity vocabulary, and the type catalog gains two reference keys.** A story, subtask or finding's declared vocabulary had no machine surface at all, so a client rendering one had to hardcode it: the literal `Severity:` label, the `US`/`ST`/`F` local-id prefix, the plural in the list verb, the `## User Stories` heading, and which status a "mark done" action should target. All of it is readable now — one row per declared kind, with `fields` (`{code, label, collection}`, the same entry shape the type catalog uses), `plural`, `local_prefix`, `container_heading`, `completion` and `maps_parent_story`. Two of those exist because re-deriving them goes wrong: `container_heading` is `User Stories` where title-casing the plural gives `Stories`, and `completion` is `Fixed` for a finding but `Done` for a story.

  **`sq workflow types --json` rows gain `subentity_kind` and `lifecycle`**, both additive and both present on every row (`null` when a type hosts no kind). `subentity_kind` is the link the kind catalog needs, because a sub-entity in `sq <type> <n> show --json` carries no kind of its own — you hold the parent's `type`, and the chain is `item.type` → the type row's `subentity_kind` → the kind row's `fields[]`, matched on the code the sub-entity's `badges` map already gives you. That resolves a *declared* label instead of a hardcoded one, which is what makes a relabelled or project-declared field render correctly.

  **`lifecycle` is a grouping key in this release and nothing more.** Both new-key rows and the kind rows name the state machine they bind, and equal values mean the same machine — `epic`, `feature` and `task` all read `work`. There is no catalog to resolve that name against, and no other part of the `--json` surface exposes lifecycle membership either: `sq workflow statuses` is a flat `{status, role, badge}` list with no lifecycle field. Group and compare with it; don't go hunting for a command that expands it into states.

  The new catalog follows the same rules as its four siblings: a bare JSON array under `--json`, a Rich table without it, one row per declared entry in a documented order, every key on every row, and cross-references carried by name so you join catalogs rather than receive copies. Every published key is permanent — these payloads grow by adding keys, never by renaming, removing or retyping one. `docs/workflow.md` sets out the joins.

- **A status role declares whether entries at that status are live.** The status-role catalog gains a `live` boolean alongside `settled` and `hidden`, exposed by `sq workflow roles --json`. It is what decides whether a roster entry is presented to an agent host — so the meaning is carried by a declared property rather than by a reserved status name, and a project may name its roster states whatever it likes. It defaults to false: a status says it is live rather than being assumed to be. It is deliberately narrower than "not settled": a status can be non-settled (paused, waiting) without being live.

- **`sq role <addr> set-default` moves the default-role designation.** It designates one live role and clears every other holder in the same transaction, reports the previous holder it cleared, and refuses a non-live target — a designation the generated config cannot present is not a designation. Designating the role that already holds it is a reported no-op. It is the way back after a retirement leaves a squad with no default-role line, the only alternative being to reactivate the role that carried it.

- **`sq check` reports a roster entry whose state its generated config cannot support.** The same two conditions that refuse a retirement are also reported against state already on disk: no live role while an agent backend is enabled, and a skill that is not live while a live role still preloads it. A check on transitions cannot see either, so a squad that arrived at one some other way — an entry removed rather than retired, a skill scoped to a role after the skill was archived — is told about it instead of projecting it silently. Each report names the entry, the condition, and a remedy where one exists.

- **The team playbook is the fourth thing you can override.** `.overrides/playbook.toml` customises the per-role guidance squads compiles into the generated `sq-<type>` skills — the "here is what you check, what you do, and how you hand off" text an agent reads before it touches an item of that type. It joins templates, roles and the workflow spec on equal terms in the toolkit you already know: `sq override scaffold playbook` starts it from a stamped, commented worked example, `sq override list` shows it with its base version and drift state, `sq override diff playbook` shows both what you changed and what the release changed underneath you, `sq override update playbook` re-stamps once you have reconciled, and `sq check` warns when the bundled playbook moves. A type's prose fields — `overview`, `lifecycle`, `commands` — merge one field at a time, so you rewrite the one line you care about and inherit the rest. Which types need an entry is derived from your own vocabulary, not declared here: drop a type in `.overrides/workflow.toml` and its playbook coverage requirement goes with it.

  **Adding one role's guidance to a type is a single line.** `roles` is a list, and writing a list replaces it, which would mean restating every guide the bundle ships for that type just to add one. The splat-ref keeps them: `roles = ["$(*self)", { slug = "security-analyst", enter = [...], do = [...] }]` reads as "everything the bundle gives this type, plus mine", and the bundled guides go on tracking the release. It has to be TOML's inline-array form — the `[[types.<t>.roles]]` header form has nowhere to put the `$(*self)` token — and a slug may appear only once per type, because one slug renders one section. Changing a field of a bundled guide, rather than adding one, still means restating the array by hand; nothing pretends otherwise.

  **A role you invented can now carry guidance.** A project-defined role — the kind `sq override scaffold --new <slug>` starts — got no section in any generated item skill, because the playbook that decides who gets one was not yours to edit. Name it in a type's `roles` and it gets its section in that type's `sq-<type>` skill, and that skill is preloaded on the role's generated pointer, exactly as for a bundled role.

- **A sub-entity's discussion is machine-readable, and one sub-entity can be read on its own.** Each entry under `subentities` in `sq <type> <n> show --json` now carries a `discussion` array — author, timestamp and body per comment. Previously the JSON stopped at the sub-entity's `body`, so a client that wanted the conversation on one story or finding had to parse the rendered markdown for it. `sq <type> <n> <kind> <k> show` also gained `--json`, emitting exactly that one sub-entity's object.

- **`sq check` and `sq sync` tell you when playbook guidance you wrote is being dropped.** A generated `sq-<type>` skill renders a role's guidance only if that role is live in your roster, and quietly skipped the rest — so a guide you added in `.overrides/playbook.toml` could simply not be there, with nothing anywhere saying so. Both commands now name each dropped guide and the type it sat on, and give the two ways out: make the role live again, or remove the guide. Three situations reach it — a role scaffolded with `sq override scaffold --new` but not yet activated (the likely one, since scaffolding prints activation as the *next* step, so writing the guide first is the natural order); a role activated and later retired with its guidance left behind; and a stray or malformed file in `.overrides/roles/` whose filename is read as a slug but never becomes a role. The message names whichever revive command actually applies — `sq role activate <slug>` for a slug that has no roster entry yet, `sq role <slug> status Active` for one that has an entry and was retired, since running the wrong one of those two looks like it worked and changes nothing.

  **It reports the guides you wrote, and only those.** A guide is yours if it appears in your `.overrides/playbook.toml`, and that is the whole test — retiring a bundled role you wrote a guide for is reported like any other. What is deliberately *not* reported is squads' own bundled guidance for a role that stopped being live: those sections do disappear from the generated skill, but the bundled playbook is not yours to edit, so a warning about it would name no action you could take. Both commands exit `0` either way: this is a report, not a refusal, because neither remedy is something the command could carry out for you — reviving a role is a separate command, and `sq` never rewrites an override file you wrote.

- **The VS Code extension's item preview shows each sub-entity's discussion.** Every sub-entity in a preview — a feature's stories, a task's subtasks, a review's findings — now carries its own `Discussion (n)` block below its body, with each comment's author, timestamp and text, and item IDs and `@role` mentions linkified exactly as in the item's own discussion. Until now a pane showed the sub-entity's title, badge line and body and stopped there, so the conversation on one finding was the part of the dossier you had to leave the editor to read. Panes and their discussions open expanded. A sub-entity with no comments renders no block at all rather than an empty one.

  One difference worth knowing if you collapse things as you read: a sub-entity's **body** fold remembers being collapsed across a refresh, its **discussion** does not — it reopens. And a preview driven by an older `sq` that predates the underlying field simply shows no sub-entity comments, instead of failing to render the item.

### Changed

- **A roster lifecycle is defined by what its statuses mean, not by their names.** A lifecycle used by `role`, `skill` or `operator` must declare at least one live status, and a settled status that is not live and is reachable from a live one — so an entry can always be presented, and can always stop being presented. The bundled roster lifecycle is now `Active` and `Archived`; `Draft` is dropped from it, as nothing ever entered that state and entries are created directly at the status the lifecycle declares as its first.

  **If one of your roles, skills or operators sits at `Draft`, move it first — before `sq sync`.**
  Almost certainly none do: no released version of squads could put a roster entry there. Every
  version back to the first created roles, skills and operators directly at `Active`, and none of
  them had a `status` verb for a roster entry at all, so reaching `Draft` took a hand-edited
  frontmatter file or a custom lifecycle that declares it. `sq check` names any that exist. The fix
  is one command per entry, and there is no migration to run:

  ```
  sq role <addr> status Active --force
  ```

  The entry keeps its history, and `Draft` itself remains a declared status — the work and guide
  lifecycles still use it — so only roster entries are involved.

- **`sq mine`, `sq workload` and `sq inbox` see sub-entity assignments.** A story, subtask or finding assigned to a slug is that slug's work, and none of the three could see it. `sq mine <slug>` matched only on the item's own assignee, so someone holding three findings on a review assigned to somebody else had an empty queue and no command that would show it to them. All three now match on sub-entities as well as items, and each says which sub-entity it matched: `sq mine` in a `Matched` column (`US1 (InProgress)`) and an additive `matched_subentities` key under `--json`; `sq inbox` by naming where the mention was found (`story:US1:discussion#1`), with the same locators in a `regions` key. `sq workload` gains three columns beside its item counts — `Sub Open`, `Sub Closed`, `Sub Total`, and `subentity_open`/`subentity_closed`/`subentity_total` under `--json` — reported separately rather than folded into the item totals, since one sub-entity is not one item's worth of work.

  **Open or closed is decided per match, not per item.** Whichever assignment matched is the one whose status is tested. So a closed item appears in `sq mine` while your own sub-entity on it is still open — that work is still yours, and the item closing did not finish it — and one of your closed sub-entities on an open item stays hidden until you pass `--all`. If you have scripted around `sq mine` returning only directly-assigned items, it now returns more rows than it did.

### Fixed

- **`sq check` reports a role override that will not load.** A `.overrides/roles/<slug>.toml` with a syntax error or a bad field was invisible to `check` — `✓ no issues`, exit 0 — while `sq sync` and `sq role <slug> show` both refused it. The one command whose job is telling you the squad is sound was the one command that said it was. It is now an error naming the file and the parse failure, and it names *when* each other command refuses rather than implying both always do. **Every override file is checked, not just the ones for roles you have activated**: `sq role <slug> show` resolves an override for a bundled role your squad never added, so a broken file for one is a real failure waiting for whoever first asks about that role.

- **A type you declared yourself stops reporting as "no such command" when its override won't load.** A type that exists only in `.overrides/workflow.toml` gets its command group from that file, so when the file failed to load the group was never registered and `sq incident …` or `sq create incident …` answered `No such command 'incident'` at exit `2` — a usage error, pointing at your command rather than at the broken file that was the actual problem, and the worse message precisely for the adopter who had customised most. Both now refuse at exit `1` naming the cause, with `sq workflow lint` — which keeps working while everything else is stopped — as the way to see every problem at once. Commands for the built-in types already reported the real cause and are unchanged.

  **One consequence to expect:** while that refusal stands it answers for *any* command name, so a genuine typo reports the override problem rather than the typo. On a healthy squad a typo still gets `No such command` at exit `2`. `sq --help` and the built-in groups' `--help` still work while the file is broken, so you can read your way around; the help for a type that exists only in the override cannot, since the file that would describe it is the file that will not load.

- **`sq … body` refuses to overwrite a body someone has already written.** The verb replaces the whole body region, and it used to do that to an authored one without asking: one command, a success line, and prose that existed nowhere else was gone. It now stops before writing — naming how many lines are at stake and quoting the opening ones — and leaves the region untouched. `--append` adds to what is there, `--force` replaces it deliberately, and the refusal exits non-zero so a script or an agent can branch on it rather than needing to answer a prompt. Every door is covered: an item's body, a sub-entity's, a custom skill's, and a bulk import's `body` and `sub-body` events, which carry a `force` field of their own so re-running an import cannot quietly erase what was written since.

  **"Already written" means "differs from the scaffold", not "not empty".** A newly created item's body is not blank — it holds the rendered stub that type's template produces — so a test for emptiness would have refused every first write. squads re-renders the type's template and compares, which means the first real body always goes in cleanly, and it works the same way if you have replaced that template under `.overrides/templates/`: your own scaffold is recognised as unwritten, not mistaken for prose. The practical effect is that the plain command is now safe to try when you are not sure whether a body is occupied.

- **`sq role activate` on a retired role no longer reports success it did not deliver.** Running it against a role whose entry exists but has been retired printed `activated <Name> (ROLE-n)` and changed nothing at all — the status stayed retired, the role stayed unspawnable, and the only sign of trouble was the absence of any. It now refuses, names the status the entry is actually at, and gives the command that does revive it (`sq role <slug> status <live-status>`). Activating a role that is already live is still the harmless no-op it always was. **If a script calls `activate` to make sure a role is available, check it:** on a retired role that call used to look like it worked and now exits non-zero, which is the point, but it is a different exit code than the script saw before.

- **`sq reflog --op` documents every operation it accepts.** Two hand-maintained lists named the reflog's operations — the `--op` help text and the module's own reference — and each was missing entries the other had, including one, `retype`, that neither mentioned. `sq reflog --op retype` worked the whole time; nothing told you it existed. The names now come from a single declared vocabulary that the help text is generated from and the documented table is checked against, so the sixteen operations squads records are the sixteen it lists, and the two cannot drift apart again.

- **An override that did nothing at all now says so.** A top-level key squads did not recognise in `.overrides/workflow.toml` was silently discarded, and the commonest way to write one is a mistyped section name — `[item.task]` for `[items.task]`, `[status.Triage]` for `[statuses.Triage]`. The file parsed, every command ran, `sq workflow lint` reported a clean spec, and none of your customisation was applied: the section never reached a validator, so nothing was in a position to complain. The document's top level is now a closed set of section names, and an unrecognised key is refused by name with the accepted set listed beside it. If you have ever written an override, been sure it was right, and watched squads behave as though it were not there, this was why.

- **A missing index reports what to do instead of crashing.** With no `.squads.json` on disk, every command that reads the squad raised a raw traceback, while a *corrupt* index had always failed politely. Both now say the same thing — `missing index .squads.json; run sq repair to rebuild it from the markdown files` — which matters most where the index is deliberately not kept in version control, since the first command after a fresh clone was the one that crashed.

- **`sq repair` could give a new item an ID number an older item already held.** The counter in `.squads.json` is a high-water mark: a number it has issued is never issued again, and that is the whole of what makes an ID permanent. Before rebuilding, `repair` re-read the previous counter — and treated *any* failure to read it as "there was no previous index", including the case where the index parsed perfectly well but held an item whose type, status or badge code the active spec no longer declares. That is precisely the state an edit to `.overrides/workflow.toml` puts you in, and the exact state `repair` exists to recover from. The counter fell back to the highest sequence number still visible, and the next `sq create` handed out a number that was already taken.

  **What that looked like was silence.** Two files claiming one ID, `sq check` reporting no issues, `sq list` showing one of them, and the next `sq repair` swapping which one it showed — the other left the board with its file still sitting on disk. `repair` now reads the previous index tolerantly enough to recover the counter from it even when a stored item's vocabulary no longer resolves, and never lowers the high-water mark. A structurally corrupt index — missing, unparseable, wrong schema — is still treated as absent, because there is genuinely nothing in it to recover.

- **A hyphenated `prefix` no longer breaks `renumber` and `repad`.** A workflow override may give a type a prefix with a hyphen in it — `RUN-BOOK`, `POST-MORTEM` — and squads read the prefix off an ID by splitting at its *first* hyphen, so `RUN-BOOK-000042` parsed as prefix `RUN` with the rest as its number. `sq migrate repad` silently skipped that type's files and reported success, leaving half the corpus at the old width. `sq repair --renumber`, on the path where it has to reissue a number, wrote a filename assembled from the truncated prefix and the old digit run — `RUN-000010-000009-fix-login.md` — which matched no declared prefix any more: the item dropped off the board, and every following command failed against the misaligned corpus. An ID's prefix is now read as everything before its final hyphen, so a hyphenated prefix survives both commands intact.

- **Renaming a sub-entity kind no longer drops the guard that prevents an orphaned story map.** Removing a story that subtasks map to has always been refused, so that no subtask is left pointing at a story that no longer exists. The check tested the kind's *name* — literally `story` — so a workflow override that renamed either side of the mapping removed the guard along with the name, and the removal went through, orphaning every subtask mapped to it. The guard is now derived from the mapping the spec declares rather than from a name, so it holds however you have named the two kinds.

- **A file `sq` cannot read no longer costs you every other file.** One item whose bytes are not valid UTF-8 — a bad merge, a truncated write, a stray encoding — used to abort whichever command met it. On a board of hundreds of items, `sq check` reported that one file and then stopped: no view of anything else until you had fixed it. Every read surface now degrades one file at a time. `sq check` names the unreadable file as one error-level issue and goes on to check the rest of the board. `sq repair` rebuilds the index from every file it can read and **keeps the unreadable item's existing index entry** instead of dropping it, so the item stays resolvable by ID and picks up its real values on the next repair. `sq board list` and `sq memory list` show every notice or entry they can read and name the ones they can't, rather than showing you nothing. Each message names the file, which is the one thing you need in order to fix it.

  **The two commands that rewrite identity refuse instead — and `sq migrate repad` now refuses before it touches anything.** `sq repair --renumber` and `sq migrate repad` rewrite IDs across every file at once and cannot do that for a file whose ID they cannot read, so both stop and name it. `repad` used to rename the whole corpus to the new width and store the new padding first, and only then abort on the unreadable file, leaving renamed files behind an index that had not finished rebuilding. It now refuses up front: no file is renamed, and the stored padding is left as it was.

- **A frontmatter value of the wrong shape reports the file instead of crashing.** A field holding the wrong kind of value — `id: 5` where a string belongs, `labels: abc` where a list does — used to surface as a raw Python traceback from whichever command happened to read the file first, naming an internal function rather than your file. Every verb now fails with `invalid item data in <path>` and the specific field, so the message points at what to edit. Two consequences worth knowing. `labels: abc` is now **rejected** rather than silently exploded into one label per character — the old behaviour turned a typo into the three labels `a`, `b`, `c` and `sq check` reported no issues; `labels:` with nothing after it, and `labels: ''`, still load as "no labels", deliberately, so files that loaded yesterday keep loading. And a corrupt timestamp no longer looks like a fresh one: `created_at: 5` used to be replaced with the current time, so a damaged date became today's date and nothing looked wrong; it is now read as written (`1970-01-01T00:00:05Z` — a number is a Unix epoch), which is visibly wrong and therefore fixable.

- **A malformed frontmatter `id:` is reported per file, and the scan carries on.** `sq check` used to stop at the first one it met and say only `error: malformed ID 'NOTANID'` — without naming the file it was in, which is the one thing you needed. With two broken files it reported one. It now names each file, says the value is being ignored and why — an item's identity comes from its `sequence_id` plus its type's prefix, so the `id:` line is not what squads resolves it by — and goes on to check the rest of the board, reporting every one. `sq renumber` and `sq migrate repad` refuse and name the file instead, since both rewrite identity across every file at once. Fixing the line, or deleting it, clears the report.

- **`sq inbox` shows you why an item is in your inbox.** A mention in an item's own **title, description or label** was enough to get the item listed, but the scan that collects the matching lines never looked there — so the item appeared with nothing under it, and `--json` returned it with `lines: []` and `regions: []`: a hit you could not act on or explain. Those mentions are now surfaced as item-level lines, as `sq search` already did, with `null` in the matching `regions` slot to mark an item-level hit apart from a sub-entity one (`story:US1:discussion#1`). The other half of the same fix: an item whose only `@`-looking text sits in sq-managed metadata is no longer listed at all, rather than listed with no visible reason.

- **A guide's `tech` can be changed after the guide exists.** `sq create guide --tech python` recorded it, but `sq guide <n> update --set tech=…` was refused — `'tech' is not a settable field on a guide` — so the value could be written exactly once and never corrected or cleared. It is now a settable field like `tags`, with `--unset tech` to clear it. This matters most if you have renamed or replaced the `guide` type through a workflow override: `--tech` is an option on the built-in `sq create guide` command, so under a renamed type `--set` is the only way to record the field at all.

## [0.12.3]

**No change to the `sq` CLI in this release.** The Python package behaves exactly as 0.12.2 did —
nothing to migrate, no commands or output to re-learn. What changed is the VS Code extension, the
documentation an adopter reads before installing, and the page PyPI shows for the package.

### VS Code extension

Mostly the sidebar. The two side views — Roster and Records — gained the filtering and grouping
controls only Work Items had, and every button in a view's title bar now shows the state the view
is in rather than only the action it performs.

- **A view-title toggle shows which state its view is in.** Group-by-type, show-closed and the
  rest rendered identically whether on or off, so the toolbar gave no clue how the tree in front
  of you was filtered. Each toggle now swaps its icon to reflect the current state, and its title
  names what a click will do.
- **The Roster view can be narrowed.** It had nothing but a refresh button. Archived entries are
  now hidden by default with a toggle to reveal them, and the view can be restricted to a single
  status; the active filter shows beside the view title. Filtering to a normally hidden status
  reveals it, the way `sq list --status` does without `--all`.
- **Both side views can be flattened, and Records hides what is settled.** Roster and Records
  group their entries by type as before, and each can now be flattened into a single list.
  Records — which also had only a refresh button — now hides terminal records by default:
  superseded and deprecated decisions, deprecated guides. An accepted decision or a published
  guide stays visible; those are settled but still in force. In every view, "Clear" returns it to
  these defaults rather than revealing everything.
- **One refresh covers the whole sidebar, from the sidebar or from an item.** A refresh button
  used to refresh only its own view, so keeping the sidebar current meant clicking each of them in
  turn. Any refresh now refreshes all three trees — Work Items, Records, Roster — and every open
  item preview. The preview panel has a refresh button of its own too, left of the back/forward
  arrows, so bringing the dossier you're reading up to date no longer means leaving it.
- **An open preview keeps its expanded sections across a refresh.** Sub-entity bodies and the two
  graph folds stay as you left them when the preview reloads. Since agents mutate the board while
  you are reading it, a preview left open used to collapse itself repeatedly through a session.
- **The packaged extension carries its licence, and the Marketplace listing says what it is.** The
  VSIX now ships the MIT licence text, and the listing has real categories, search keywords, and a
  description naming the extension for what it is: a read-only companion for squads-managed
  projects.

### Documentation

Corrections, not additions — each of these was wrong in a way that cost the reader an error:

- **The README's quickstart failed as written.** `sq create` requires `--author`, which the example
  omitted, so the first command an adopter copied returned `Missing option '--author'`. The
  quickstart now passes `--author`, and addresses items by the ID `sq create` prints back rather
  than by a fixed number that only matched one particular squad.
- **A bug's lifecycle was documented as the epic/feature/task one.** The table gave bugs
  `Draft → Ready → InProgress → InReview → Done`; the real machine is
  `Open → InProgress → Fixed → Verified` (+ `WontFix`, `Blocked`, `Cancelled`), so a reader
  following it hit a rejected transition. Sub-entity lifecycles are now documented alongside it.
- **The ref-kind list showed five of the nine kinds.** `depends-on`, `supersedes`, `duplicates` and
  `scopes` were missing — including the kind `sq check` looks for on a superseded record, and the
  one that records sequencing between items.
- **Three documented commands did not exist** (`sq story add`, `sq skill list`, `sq guide list`),
  and the roster commands were written verb-first when the real grammar addresses the entry first
  (`sq role <slug> show`). Commands that do exist but were undocumented are now listed, among them
  `sq show`, `sq graph`, `sq docs`, `sq ui`, `sq memory`, `sq board`, `sq migrate` and
  `sq override`.
- **The install line still said "once published".** The package has been on PyPI for several
  releases; `uv tool install squads` is now given as the instruction it is, with the `tui` extra
  named for anyone who wants `sq ui`.
- **PyPI has its own project description.** The package page is now written for someone at a
  terminal deciding whether to install the CLI — what squads is, how the model works, and a worked
  example of one piece of work moving from proposal to closed — instead of the repository's README,
  which serves GitHub visitors and contributors.

## [0.12.2]

### Fixed

- **`sq import --dry-run` no longer mutates files on disk.** A dry-run pre-pass now performs zero filesystem writes — files that would be renamed or edited stay untouched, and only the operation plan is printed.

### Changed

- **`sq check` no longer reports phantom drift or reconciliation errors while another process is mutating the board — and no longer fails with an error exit.** The check now confirms any claim that compares the on-disk files against the index with a fresh re-read before reporting it, so a mutation that lands while `check` is scanning the board resolves quietly instead of surfacing a false warning or false hard-error exit code.

- **An interrupted mutation leaves a repairable skew instead of a truncated file.** If a process dies mid-operation, the markdown files keep their newer values while the index lags behind. A next mutation of that item refuses with a clear `sq repair` pointer instead of silently reverting the change, and `sq sync` leaves drifted roles or skills untouched rather than overwriting them — both preserving the interrupted state.

  **The cost of this guarantee, stated plainly: that item is not mutable until you run `sq repair`.** Running repair clears the block and promotes the interrupted mutation's values into the index. The block is per-item; nothing spreads.

- **Unreadable files and stale item paths now report a clear error instead of a traceback.** A squad-data file that contains bytes that are not valid UTF-8 — an item, a board notice, a memory entry, or `.squads.toml` itself — now fails with a message naming the file instead of a raw Python traceback, on every command that reads it: `sq check`, `sq repair`, `sq renumber`, `sq sync`, `sq board list`, and `sq memory list`. Separately, an item whose file has moved out from under the index (a stale path from an interrupted rename or retype) now reports a clear error naming the item and pointing at `sq repair`, instead of failing with a traceback.

## [0.12.1]

### Added

- **Per-type display labels.** An item type can declare human-readable display labels — a
  singular and plural form (each with a lowercase variant) — in `.overrides/workflow.toml`;
  any form left out is derived from the type name. `sq workflow types --json` now exposes the
  resolved labels per type, and every client renders them: the VS Code extension's Records and
  Work (group-by-type) trees show "Decisions" / "Tasks" instead of the raw `decision` / `task`,
  the Roster tree resolves its labels from the spec, and the `sq ui` TUI's type filters and
  search results show the label too. Acronym or irregular types (e.g. an `ADR`) can pin every
  form so they stay correctly cased.

### Changed

- **Generated onboarding nudges agents to load their memory and the board on start.** A fresh
  `sq init` / `sq sync` now writes start-of-run guidance into the CLAUDE.md/AGENTS.md managed
  region and each role sheet — load your role memory (`sq memory <role> list`) and check the
  team board (`sq board list`) — and tells the coordinating manager to load the `squads` skill
  at session start and again after a context compaction.

## [0.12.0]

### Added

- **`sq ui` — a terminal UI for browsing the squad.** A new `sq ui` command opens a
  keyboard-navigable TUI: a Work/Roster tree for finding items, a reader panel with
  body/sub-entities/discussion tabs for reading one in full, a filter/sort popup for
  narrowing the tree, and a full-text search page that opens a result straight into the
  reader. Ships behind the optional `tui` extra (`pip install squads[tui]`).
- **VS Code: full-text search.** A new search QuickPick searches item bodies and
  discussions, narrowed by a single type or status, with a result opening straight into
  the preview.
- **Custom, non-dev roles.** `sq override scaffold --new <slug>` starts a wholly new role
  that isn't in the bundled catalog (e.g. `security-analyst`, `incident-commander`) with
  the essentials stubbed in; `sq role activate <slug>` turns it into a tracked role with
  its own Claude pointer. Pass `--can-spawn` to let the role spawn other agents.
- **Type category axis + pluggable validators.** Every item type now declares a `category`
  (`roster` / `work` / `records`) in place of the old `is_meta` flag, and both `sq check`
  and create/update gating run off a single pluggable validator catalog. A project can
  assign catalog validators to a type in `.overrides/workflow.toml` (a `validators` list),
  extending what `sq check` and the create/update gate enforce for that type.
- **Custom records-category types.** An adopter can define their own durable-reference item
  type — its own prefix, folder, and lifecycle — alongside the bundled decision/guide/contract
  types; `sq create`/`retype`/`list` treat it the same as any built-in records type. Records
  types take no parent.
- **Status roles.** A status's lifecycle behaviour — whether it's a resting/settled state,
  whether it's hidden from the default view, and its display colour — now comes from a named
  role declared in the workflow spec, instead of separate flags on each status. Roles are open
  vocabulary (define your own); colour is a fixed semantic palette (positive/danger/warning/
  muted/neutral/info). New `sq workflow roles --json` lists the catalog, and `sq list` / `tree`
  / `mine` / `workload` now render every status in its role's colour — so a settled-but-live
  record (e.g. an Accepted decision) stays visible and coloured instead of disappearing the
  way finished work does.
- **A Records group in the clients.** The terminal UI's browse tree and the VS Code extension
  both gained a dedicated Records group/view, and a `--category roster|work|records` filter is
  now available everywhere item lists can be filtered. Statuses render in their role's colour
  in both clients.
- **`add-finding`/`add-story`/`add-subtask` accept `--status`, and take their body the same
  way.** Set a non-default status at creation time (validated against that sub-entity kind's
  own lifecycle); all three now accept the body via `-m`, `--file`, or stdin, matching item
  creation.
- **`sq role list` / `sq operator list`.** List the active roster's roles, or the registered
  operators, each with an active/inactive marker (`--json` supported for both).
- **`sq <type> <n> comments`.** A focused read-back of just an item's discussion, without
  pulling the full dossier (`--json` supported).
- **Remove a sub-entity.** A story, subtask, or finding can now be removed with a `--yes`
  confirmation; removing a story still mapped by a subtask is refused, so a subtask is never
  left pointing at nothing.
- **`sq import <file>` — bulk event import.** Replay a JSONL event stream — one mutation per
  line (create, status change, body, comment, ref, add-story/add-subtask/add-finding,
  sub-entity update, assign, and more), each carrying its own timestamp and acting actor — in
  a single pass, so migrating an existing project's history is one file instead of hundreds
  of individual commands. Validation runs up front and collects every error before
  anything is written, so a clean file applies atomically; `--dry-run` prints the plan without
  writing, and `-` reads the stream from stdin.
- **Adoption warnings on `init`/`sync`.** Adopting into a project that already has a
  hand-written `CLAUDE.md` inserts the managed block and warns that the surrounding
  hand-written content may now contradict it — nothing is deleted. Pre-existing `.claude/`
  pointer or skill files that squads didn't generate are listed as candidate orphans
  (warn-only, never removed).

### Changed

- **`sq check` output is deterministically sorted.** Issues are emitted in a stable order
  (squad-wide issues first, then by item, then severity, then message) across runs and in
  `--json` — the set of issues is unchanged, only the ordering is now deterministic.
- **Create, update, and reparent are validated fail-closed.** These now enforce the same
  item invariants `sq check` reports (valid status for the type, parent eligibility,
  sub-entity rules), rejecting a mutation that would leave an item invalid instead of only
  flagging it after the fact.
- **`--json` no longer carries `terminal`/`is_open`.** The `sq workflow statuses --json`
  catalog no longer carries `terminal`, and item `--json` payloads no longer carry `is_open` —
  both are now derived from the status's role (`sq workflow roles --json`). A machine
  surface consuming either field should switch to resolving the status's role instead.

### Fixed

- **VS Code: bold text wrapping inline code no longer breaks rendering.** The body/comment
  renderer now gives code spans CommonMark's precedence over emphasis, so a bold-wrapped
  code span no longer breaks out partway through on an asterisk inside the code.
- **Search snippets no longer drop a match found deep in a long line.** A hit's returned
  snippet now windows around the actual match offset instead of always truncating from the
  start of the line, so `sq search`, the `sq ui` search page, and the VS Code QuickPick all
  show the matched text instead of clipping it out.

### Deprecated

- **Workflow-override `is_meta` key.** Superseded by `category` (`"roster"` / `"work"` /
  `"records"`) on an item type spec. A project override still carrying `is_meta` loads
  transparently for now (`false`/absent resolves to the `category` default; `true` on a
  non-roster type is rejected, since roster is closed to `role`/`skill`/`operator`). The
  compatibility shim is removed at 1.0 — migrate to `category`.

## [0.11.1] - 2026-07-21

### Fixed

- **The VS Code extension no longer shows an error in a non-squads workspace.** Opening the Squads
  panel (or the Roster view) in a folder that has no squad now renders a calm "No squad detected
  here" placeholder instead of a red error node and an error notification — the normal case for any
  non-squads folder is no longer treated as a failure.

## [0.11.0] - 2026-07-20

### Added

- **Custom skills can carry an authored, persistent body.** `sq skill body` sets (or `--append`s
  to) a custom skill's body text, and it survives sync/regen/repair untouched — bundled/system
  skills are unaffected and keep generating from their template as before.
- **Skills can be scoped to specific roles.** `sq skill link-role`/`unlink-role` link a skill to a
  role so that role's agents preload it (alongside the bundled skills every role already gets),
  resyncing that role's generated files immediately. A skill can be scoped to as many roles as
  needed, or none.

### Fixed

- **Doc examples now show real ID display.** README and the `docs/` guides had leftover
  zero-padded example IDs (`TASK-000008`, `FEAT-000002`, …) from before IDs display unpadded;
  every CLI example now matches what `sq` actually prints (`TASK-8`, `FEAT-2`, …).

### Changed

- **`sq workflow`'s subcommands are documented.** README and `docs/workflow.md` now list
  `sq workflow show|types|collections|statuses|lint` alongside the cheatsheet, instead of only
  the bare `sq workflow` form.
- **Generated skills and managed sections are more concise.** The agent-facing content `sq sync`
  writes into a project — the bundled skills and the CLAUDE.md/AGENTS.md managed sections — has
  been tightened for length with no loss of guidance; a fresh `sq init`/`sq sync` now produces
  leaner generated files.

### VS Code extension

- **The work-item tree keeps its expansion across refresh.** Auto-refreshing on a `.squads.json`
  change used to collapse every expanded node; expanded nodes now stay expanded across a
  refresh.
- **The item preview preserves scroll position.** Refreshing the same item's preview (e.g. after
  an edit) holds the scroll position instead of jumping back to the top; navigating to a
  *different* item still resets to the top as expected.
- **`@mentions` in the preview link to the role sheet.** A `@<slug>` mention in a body or comment
  now renders as a link that opens that role's sheet, with a hover preview of the role's details.
- **Back/forward navigation.** Each preview panel gained a sticky toolbar with back/forward
  arrows (plus a truncated title label) for moving through the items you've viewed in that
  panel, the way a browser does.

### Migration

**Schema 0.10 → 0.11 — run `sq migrate up`.** A schema-stamp-only gate: no frontmatter shape
changed, so the runner touches no files. It exists to hard-stop a pre-0.11 client with a clear
"run `sq migrate up`" before it can meet a ref kind it doesn't recognise yet. Every existing
skill (bundled or custom) and any role-scoping edge is left exactly as it was — this migration
only advances the schema stamp.

## [0.10.0] - 2026-07-19

### Added

- **`sq workflow types` — a machine-readable type catalog.** New subcommand alongside `sq
  workflow`/`sq workflow lint`: default prints a human table, `--json` emits a bare array (one
  object per declared type, work and reserved alike) with `type`/`order`/`prefix`/`reserved`,
  sorted in ascending resolved `order` (type-name tiebreak) — the same order the CLI registers
  per-type commands in. `order` is `null` for a type with no explicit order, present rather than
  omitted so the key set stays stable. Lets a consumer (e.g. the VS Code client) sort type groups
  spec-driven instead of alphabetically, with no hardcoded type list.

### Changed

- **`sq workflow --raw` / `sq workflow show --raw` print the cheatsheet as clean markdown.**
  Same content as the styled view (markdown tables, fenced ```mermaid``` blocks) but printed
  verbatim instead of through `rich.Markdown` — no box-drawing, no ANSI, so piping it into a
  markdown viewer renders cleanly. The default (non-`--raw`) styled view is unchanged.
- **`sq show <id> --raw` is now clean markdown.** It emits a deterministic dossier — an `#`
  title, a bullet list of metadata (status, priority/severity, assignee, parent, author, refs,
  labels), and the body verbatim, with `--comments`/`--full` appending Discussion/sub-entity
  sections — instead of the boxed panel, aligned summary table, and `=== … ===` separators it
  used to render. Piping `sq show --raw` into a markdown viewer now renders cleanly. The default
  (non-`--raw`) styled view is unchanged.
- **`sq show --json` now carries the body and discussion.** The JSON payload gained a top-level
  `body` (the raw body markdown), a top-level `discussion` (an ordered list of
  `{author, ts, body}`), and a `body` key on each entry of `subentities` — additive only, nothing
  renamed or removed.
- **`sq tree --json` and `sq list --json` carry more machine-readable state.** Every `sq tree
  --json` node now includes the item's `title` alongside `id`/`type`; both `sq list --json` and
  `sq tree --json` gain an `is_open` boolean (derived from the workflow spec's terminal-status
  set, so a custom vocabulary stays correct with no code change) — additive only, nothing renamed
  or removed.
- **`sq mine --json` also carries `is_open`.** Brings the assigned-to-me view in line with
  `sq list --json`/`sq tree --json` — additive only.
- **Trimmed the agent-facing `squads` skill.** Dropped the seven per-type lifecycle Mermaid
  diagrams from the skill (agents read it as raw text, so the diagram source was just noise);
  the compact hierarchy diagram and the one-line-per-type lifecycle table stay. `sq workflow`'s
  terminal output is unchanged and still shows the full per-type diagrams.

### Migration

**Schema 0.8 → 0.10 — run `sq migrate up`.** The bundled `sq-memory` skill predates the standard
`SKILL-<NNNNNN>-<slug>.md` naming convention used by every other bundled skill. The runner stamps
a unique `SKILL-…` id onto the legacy `agents/skills/sq-memory.md` file (if it isn't already
stamped), renames it to the convention filename, and rewrites its `.claude/` pointer to match,
then rebuilds the index. One-way and idempotent; a squad that never had the legacy file (or
already carries the convention-named one) is unaffected. No manual steps are required.

## [0.9.0] - 2026-07-15

### Added

- **Shared team knowledge — agent memory and a team bulletin board.** Each role now has its own
  committed memory notebook: `sq memory <role> list/search/show/add/forget` lets a role jot a
  durable fact, search past ones, and prune what's stale, stored as plain markdown files rather than
  in the tracked-item index. Alongside it, `sq board post/list/clear` gives the whole team a shared
  bulletin board for broadcast notices — post a short message with an optional `--until` expiry, list
  what's currently live, or take one down. Every role's briefing now points agents at their memory
  and the board at the start of a run, so accumulated context and team-wide notices surface
  naturally without cluttering any generated file.
- **Richer `sq search`.** Search now takes a `--status` filter alongside `--type` (the two compose
  together, matching the same filtering already available on `sq list`/`sq tree`), and each hit
  reports where the match was found — the title, description, body, a discussion comment, or a named
  sub-entity — plus the matched item's type and status for quick triage. Matches include a short
  in-context snippet, and `--json` output carries all of this detail for scripting. Search remains a
  plain case-insensitive substring match.
- **Inline Mermaid diagrams.** `sq graph --format mermaid-md` wraps the dependency/reference graph
  in a ready-to-paste fenced Mermaid block, and `sq workflow` now includes diagrams of the item-type
  hierarchy and each type's status lifecycle, generated from the active spec so a customized
  vocabulary renders its own shape correctly.

## [0.8.0] - 2026-07-13

### Added

- **Every work item type is now fully customizable — only `role`/`skill`/`operator` remain
  reserved.** The built-in type and status vocabularies are no longer backed by fixed enums: all
  seven bundled types (epic, feature, task, bug, decision, review, guide) and their statuses are
  ordinary spec-declared vocabulary, on equal footing with anything a project defines in
  `.overrides/workflow.toml`. A built-in type or status can be renamed, dropped, or replaced with no
  code change, and every facing surface — CLI help, generated skills, the managed `CLAUDE.md` /
  `AGENTS.md` sections, and the `sq workflow` cheatsheet — derives its wording from the active spec
  instead of a hardcoded name, so a customized vocabulary reads correctly everywhere. Behavior on
  the bundled (no-override) default is unchanged.
- **Custom sub-entity kinds.** A custom item type can now declare its own sub-entity kind (not just
  reuse story/subtask/finding) with its own lifecycle, completion status, fields, and generic CLI
  verbs — `add-<kind>`, the `<plural>` list, and the nested `show`/`update`/`body`/`comment`
  subgroup — generated with zero code change. A declared field beyond severity (e.g. an `impact` or
  `urgency` axis) is now storable and settable via `--<field>` on any sub-entity kind, not only the
  built-in ones.
- **Badge collections — priority and severity generalized into spec-defined vocabulary.** Priority
  and severity are now `Collection`/`Field`/`Badge` definitions in the workflow spec rather than
  fixed enums, so a project can declare an entirely custom badge axis (e.g. `impact`/`urgency` on a
  custom incident type) and get filtering, sorting, and colored badge rendering for free. A generic
  `--badge CODE=VALUE` / `--min-badge` escape hatch works for any declared field on `sq list` /
  `sq tree`, alongside the existing dedicated `--priority`/`--min-priority` sugar; `--sort` ranks by
  any ordered field. Bundled `priority`/`severity` behavior is byte-identical to prior releases.
- **Bulk vocabulary rename migrations — `sq migrate rename-type` and `sq migrate rename-status`.**
  Rename an existing work type (`sq migrate rename-type OLD NEW`) or relabel every item of a type at
  a given status (`sq migrate rename-status TYPE OLD_STATUS NEW_STATUS`) across an entire squad in
  one atomic operation — carrying sub-entities, status, and incoming references along, with a
  per-item audit trail. This is the escape hatch for vocabulary changes that an additive
  `.overrides/workflow.toml` merge can't express on its own (an override can add vocabulary, not
  rename or remove it).

### Changed

- **Item severity is now stored at the top level.** A bug's `severity` moves from the generic
  `extra` bag onto a proper top-level `severity:` frontmatter field, consistent with how every other
  declared badge field is now modeled. See Migration below.

### Fixed

- **A cold first CLI dispatch on a custom type could show the wrong command tree.** Running a custom
  type's command (e.g. `sq incident --help`) as the very first `sq` invocation in a process could
  render the bundled type's fallback surface instead of that type's own declared
  sub-entity/`retype` commands, because the command tree was built from a stale process-global spec
  reference before the real merged spec finished binding. Every invocation now resolves the correct,
  already-bound spec.
- **Clearer error when an item references a dropped or renamed type/status.** The vocabulary
  validation error now leads with the actual cause — a type or status no longer declared in the
  active spec — instead of pointing at `sq repair`, which cannot fix a vocabulary mismatch.
- **Sub-entity ownership resolution when two types share the same sub-entity kind.** A project that
  declares two work types mapped to the same sub-entity kind (for example a custom ticket type
  mirroring `task`'s subtasks) previously had `add-subtask`/`add-finding` and similar commands
  reject one of the two types' items. Ownership is now resolved per-item against the active spec, so
  both types work correctly.

### Migration

**Schema 0.7 → 0.8 — run `sq migrate up`.** The runner relocates every bug's `severity` from the
generic `extra` bag onto the top-level `severity:` frontmatter field it now belongs on, dropping the
old copy. One-way and idempotent; if both the old and new locations are somehow present, the
top-level value wins. Non-bug items are untouched.

## [0.7.0] - 2026-07-06

### Added

- **`sq renumber` — pre-merge ID block-shift.** A standalone verb that shifts a branch's
  locally-created IDs into a contiguous block disjoint from another branch's counter before a
  merge, preserving referential intent that the existing post-merge `repair --renumber` cannot
  (that remap is keyed by the old-ID string and blindly repoints every ref to a single winner).
  `--onto` computes the disjoint offset automatically (`delta = max(mine, counterpart) + 1 - mine`);
  `--by` is refused, with no files touched, if the requested shift would still collide. The
  operation is counter-neutral and shares its apply-path with `repair --renumber`; a single
  append-only reflog event records it. `sq` remains git-agnostic — inputs are plain integers, never
  branch refs.
- **`sq check` flags unwritten placeholder sub-entity bodies.** A new advisory rule reads each
  sub-entity-bearing item and warns, one issue per sub-entity, when a story/subtask/finding still
  carries its kind's placeholder stub instead of a written body — surfacing backlog debt that was
  previously invisible to `sq check`.
- **Guard against stale status/lifecycle prose in item bodies.** A new advisory `sq check` rule
  flags a body or `description:` that opens with a `STATUS:`/`**STATUS**`/`## Status` banner
  declaring the item's own current workflow state — prose that inevitably goes stale once the real
  (frontmatter) status moves on. Topical lifecycle discussion, cross-references to another item's
  status, and fenced-code examples are left alone; only a leading self-declared banner is flagged,
  and the discussion region is never scanned.

### Changed

- **Unpadded display IDs, decoupled from filename padding.** Every human-facing surface —
  frontmatter `id:`, refs, ID mentions in body prose, CLI output, and tables — now renders an
  item's ID unpadded (`FEAT-42`, not `FEAT-000042`). On-disk filenames are unaffected: they keep
  their existing zero-padded width, which remains purely a filename-sorting concern, reconstructable
  from disk exactly as before (`sq repair` / `sq migrate repad`). No new configuration surface.
- **The "regenerated by `sq sync` — do not edit" warning now lives on the files that are actually
  overwritten.** The warning previously sat on the (redundant) generated squad-skill bodies; it now
  stamps the agent-facing files a backend actually regenerates on sync — the `CLAUDE.md`/`AGENTS.md`
  managed regions and the `.claude/` pointer files — as a cross-backend `AgentBackend` contract, so
  an agent editing one of those files in-session is told plainly that an edit there will be
  overwritten.

### Migration

**Schema 0.5 → 0.7 — run `sq migrate up`.** The runner unpads every human-facing ID across the
corpus: it reformats each item's own frontmatter `id:`, unpads `refs:`/`parent:` entries, and
substitutes exact old-form ID literals in body and sub-entity-title prose (skipping fenced code
blocks, inline code spans, and filename-tail mentions, which stay padded). On-disk filenames are
never renamed by this step. Idempotent — once every mention is unpadded, a re-run is a no-op.

## [0.6.0] - 2026-07-02

### Added

- **Custom item types defined in TOML.**  A squad can now define brand-new item types
  (e.g. `incident`, `change-request`, `finding`) in a bundled or project-override `workflow.toml`.
  Each custom type carries its own prefix (`INC`, `CHG`, `FND`), folder, lifecycle, parent rules,
  and aliases; they are usable end-to-end with `sq create incident`, `sq list -t incident`,
  `sq incident <n> show`, `sq incident <n> retype`, and refs. An auto-generated per-type skill
  appears immediately via `sq sync`. Built-in types remain unchanged and byte-identical in output.

- **Custom statuses and auto-linearized lifecycles.**  Define brand-new statuses in the workflow spec
  (e.g. `Triage`, `Mitigating`, `Resolved` for an incident type), each with its own open/terminal
  and role classification. Lifecycles are automatically linearized into a directed acyclic graph
  with reachability validation; all status-driven filters (`sq list --status`, default closed-item
  hiding, `sq blocked`, `sq inbox` role views) respect custom open/terminal classification without
  code changes. Status badges render dynamically from the live spec with a neutral fallback.

- **Externalized and overridable workflow, role catalog, and playbook.**  The previously hardcoded
  type list, statuses, lifecycle state machines, role definitions (name, mission, responsibilities),
  and per-type/per-role guidance (enter/do/handoff/watch) now live in bundled TOML files
  (`default_workflow.toml`, `roles.toml`, `playbook.toml`). A squad can override them via
  `.overrides/workflow.toml` using an additive merge — define new types/statuses without redefining
  built-ins. **Stability guarantee:** the bundled defaults and all built-in type output remain
  byte-identical to v0.5.x; existing squads see no change unless they author overrides.

- **`sq workflow lint`** — validates that every status in a custom lifecycle is reachable from its
  initial state, and reports name conflicts between builtin and override definitions. Catches
  unreachable-terminal problems that would otherwise trap items in a dead state.

- **Spec-driven `sq workflow` cheatsheet, CLAUDE.md, and AGENTS.md.**  The `sq workflow` command
  renders the live loaded workflow spec, so a custom setup immediately sees its custom types,
  statuses, and lifecycles. The managed CLAUDE.md workflow section, the AGENTS.md backend output,
  and the generated `squads` skill likewise render from the live spec, keeping them always in sync
  with what `sq` actually enforces. The static prose (ref kinds, retype, remove-vs-cancel semantics)
  remains literal and never becomes editable — that stability is explicit in the codebase.

### Changed

- **Review state machine permitting `ChangesRequested → Approved` transition.**  The workflow spec
  now matches what was already advertised in the cheatsheet, skills, and playbook: a reviewer
  can go directly from requested changes to approved without re-drafting as `Draft` first. This
  closes a workflow deadlock in some review patterns.

### Fixed

- **Custom-status badge rendering no longer crashes on unknown status values.**  Badges now
  resolve with a neutral default (`⚪`) instead of failing when a status is not in the built-in
  set. Allows safe fallback for novel statuses.

### Migration

**No migration required — `schema_version` stays `0.5`** (this release introduces no on-disk format change).
Custom types persist their prefix in frontmatter only; built-in items derive it on load.

## [0.5.0] - 2026-06-28

### Added

- **Skills are first-class, ID'd entities.**  A skill is now a full `Item`
  on the role/operator meta-type profile (`Active` / `Archived`, no sub-entities), stored as
  `SKILL-NNNNNN-slug.md` with frontmatter as the source of truth and a thin `.claude` pointer
  resolved from it.  A single skill-description registry feeds the backend, seeding, and migration.
  New surface: `sq list -t skill`, `sq skill show`, and `SKILL-…` as a ref target.

- **Per-role spawn attenuation — leaf roles can no longer spawn sub-agents.**
  Roles now carry a `can_spawn` capability, held only by `manager` and `tech-lead`.  Every other
  role (developers, reviewer, QA, architect, …) is rendered with `disallowedTools: Agent` in its
  Claude Code agent definition, so a spawned specialist structurally cannot re-delegate.  The
  capability is visible via `sq role <slug> show`.

- **Optional session lineage on every recorded operation.**
  squads now reads two optional environment variables — `SQUADS_SESSION_ID` and
  `SQUADS_PARENT_SESSION_ID` — once at the CLI root callback and carries them through the
  invocation.  When present, both the reflog line (as additive sibling fields `session_id` /
  `parent_session_id` alongside the flat `actor` string, back-compat preserved) and the item
  frontmatter (as optional `created_session` / `modified_session` fields) record them.  When
  absent the behaviour is identical to before — actor is still just the slug.  Session fields
  are **not** settable by `--as` / `--author` or any later CLI flag; env vars are the only path.
  **Guarantee: best-effort, untrusted, observability-only.**  squads is a passive tool, never in
  the spawn path; it reads and records whatever its invocation environment carries.  A forged,
  copied, or absent session id is indistinguishable from a real one — these fields must never be
  used as an authorisation input.

- **`sq reflog --tree` and session surfacing in `show --full`.**  `sq reflog --tree`
  renders the recorded spawn lineage as a nested, best-effort tree; operations with no or unknown
  parent session appear as forest roots, and forged cycles degrade gracefully without dropping any
  entry.  `sq <type> <n> show --full` surfaces the creating and last-modifying session when present.

- **Advisory create-lane warnings.**  `sq create` now emits a best-effort advisory
  warning when a role authors an item type outside its lane (for example a developer creating a
  feature), names the expected owner role, and proceeds anyway (exit 0; the warning is recorded in
  the reflog).  Lanes are derived from the team playbook; `manager` and operators are exempt, and
  each role's create-lane is shown in `sq role <slug> show`.  **Advisory only — keyed on the
  self-declared actor, never an authorisation boundary.**

- **`sq graph` — ego-centric ref-graph view** of an item's neighbourhood, with `dot` and `mermaid`
  export.

- **`sq tree` filters.**  Filter the subtree by status, priority, assignee, and type, with
  `--depth`; the same filters are shared with `sq list`.

- **Advisory warnings for over-long sub-entity titles.**  A 120-char
  warn-and-proceed advisory on `add-story` / `add-subtask` / `add-finding`, a matching `sq check`
  audit rule, and skill guidance that a title is a one-line handle and prose belongs in the body.
  Advisory only — never gating body presence.

- **Async end-to-end.**  The service layer, index store, and file IO are now async,
  with synchronous code confined to the CLI entry edge.

### Fixed

- **`--json` output is now ANSI-free regardless of `FORCE_COLOR`.**  All 22 `--json`
  emission sites route through a plain serializer instead of the colorizing rich console, so
  machine-readable output parses cleanly even when a parent process forces color.  Regression-tested.

- **Recursive self-spawn cascade.**  A spawned developer subagent no longer
  re-delegates to a same-role child many levels deep instead of doing the work — leaf roles now
  structurally lack the spawn tool (see the spawn-attenuation entry above).

### Migration

**Schema 0.3 → 0.5 — run `sq migrate up`.**  The runner applies both steps in order: additive
session-lineage fields (0.3 → 0.4, no file rewrites; all new fields optional) and the
skills-as-entities conversion (0.4 → 0.5, which allocates IDs, renames skill files to
`SKILL-NNNNNN-slug.md`, and backfills frontmatter — idempotently, preserving existing frontmatter).
Existing item and reflog files remain valid throughout.

## [0.4.0] - 2026-06-17

### Added

- **Uniform item addressing.** Every command accepts both the full formatted ID (`TASK-000035`) and
  the bare sequence number (`35`); the type word validates it, so there is no ambiguity.
  `sq <type> <number> <verb> …` works identically whether you pass `35`, `000035`, or `TASK-000035`.
- **Typed ref-kind vocabulary.** Forward references now carry a validated kind chosen from eight
  closed terms: `related`, `blocks`, `depends-on`, `implements`, `fixes`, `addresses`, `supersedes`,
  `duplicates`. Unknown kinds are rejected at set-time; consumers validate that the kind makes sense
  for the edge (e.g. only a task/bug can `implements` a feature, only a task can `addresses` a
  decision).
- **Explicit ID padding stored in the index.** All ID formatting goes through a single formatter
  driven by a padding width stored in `.squads.json`; `sq migrate repad <width>` is a one-way command
  that renames every item file to the new width and rebuilds the index with contents byte-untouched.
  ID reads are width-tolerant by sequence number, so old and new padding can coexist during
  migration. An exhaustion guard checks the index for capacity under the new width.
- **Type-command aliases in the CLI grammar.** Shorthand aliases provide full verb and sub-entity
  equivalence with the canonical form: `e` (epic), `feat`/`f` (feature), `t` (task), `b` (bug),
  `dec`/`d` (decision), `rev`/`r` (review), `g` (guide). Aliases render into the workflow cheatsheet
  with an add-only evolution rule to preserve documentation stability.
- **`sq <type> <n> retype <new-type>`** — flip an item's type while preserving its sequence number as
  durable identity. The file is moved, incoming edges are rewritten, and the entire operation is
  atomic inside the index lock. Useful when an issue is initially misfiled.
- **Sanctioned item removal — `sq <type> <n> remove`** hard-deletes the item file, unlinks it from
  the index, and updates `.squads.json` atomically. Pass `--force` to sever incoming references; by
  default, removal is rejected if anything points to the item. IDs are never reused, so a gap in the
  sequence is a normal artifact of removal.
- **Operation reflog — `<squad>/.reflog.jsonl`** is an append-only log written after every index
  commit inside the lock (logged-without-applied impossible; applied-without-logged tolerated under
  crash). Entries record the actor (ambient per-invocation), the operation (create/update/remove/…),
  item(s) affected, and a timestamp. An `sq reflog` reader tolerates partial lines and filters by
  type/actor. The reflog is advisory (not a source of truth) and gitignored per-clone.
- **Project-level overrides — `.overrides/templates/` and `.overrides/roles/`** let squads customize
  the generated item templates and role definitions without forking the package. A stamped update
  workflow (`sq override scaffold/diff/update/list`) detects drift from the release version and
  manages upgrades; the CLI rejects any override at load-time if its stamp is newer than the release
  (unknown future version). Template and role manifests are generated and shipped with every release.
  Agent naming via overrides is supported.
- **Frozen machine-readable surface — `--json` on every read command** emits valid JSON; the CLI
  documents its exit-code table (0: success, 1: squads runtime error, 2: usage error, 3: check failure) and all
  JSON shapes are golden-file tested. This gives agents and scripts a stable contract to consume.
- **Shell completion enabled and verified for bash and zsh** via the entry-point shim. Completion
  works out of the box after install and is documented in the README.
- **Second agent backend — a generic `AGENTS.md` backend** proves the `AgentBackend` ABC is honest
  before the 1.0 freeze. The de-Claude-ified ABC (`generate_*_entry` instead of pointer-specific
  names, backend-owned root files via `ctx.root` instead of hard-coded `claude_dir`) works for both
  the Claude Code backend and the new AGENTS.md backend; both pass a shared conformance suite. The
  agents_md backend renders roster, workflow, and role missions into a single idempotent,
  marker-safe `AGENTS.md`.
- **Multi-active agent backends.** `.squads.toml` now carries `active_backends: [list]` instead of a
  singular `default_backend`; a squad maintains zero or more backends at once. Sync / scaffold /
  check / roster / regen / remove fan out over every active backend. An empty list is valid (a
  squad-only mode with no agent files). Legacy configs with singular `default_backend` read
  transparently as a single-element list — no breaking change for users. `sq init --backend` is
  repeatable with a `none` sentinel for empty; the list is deduped on first-occurrence.
- **Bugs get a real lifecycle.** A new bug-specific workflow (`Open → InProgress → Fixed → Verified`,
  terminal states `WontFix` / `Cancelled`) replaces the generic machine. Status-setting is validated
  against the type's workflow at set-time (independent of `--force`, which relaxes only the edge,
  never the vocabulary). This closes the prior hole that let bugs reach invalid statuses.
- **Stability contract — `docs/stability.md`** and `sq docs stability` tiers five public surfaces
  — durable `.md` format, CLI grammar, `--json` shapes, Python import paths (not public), and
  generated `.claude/` files — and states the migration promise: any squad created on any 0.x
  release reaches 1.0 intact via `sq migrate up`. The schema version post-1.0 follows a dotted-string
  scheme (the release that introduced it), and post-1.0 schema bumps ride the MAJOR version.
- **Rendered `sq show` output** displays items as markdown panes (title, summary, body, metadata
  badges) with a `--full` dossier (frontmatter fields in a sidebar) and `--comments` facet (full
  discussion thread). Sub-entity `show` (e.g. `sq feature 12 story 1 show`) renders the block
  (heading, state badges, body, discussion). This is the canonical read for an agent briefing on an
  item before acting on it.
- **Python >= 3.14 is now required.** The floor is PEP 649 lazy annotations (Python 3.14+) so
  forward references work unquoted in type hints. This is a deliberate architecture choice to keep
  the import graph acyclic and annotation handling simple.

### Changed

- **Bug lifecycle introduces per-type status validation.** Status-setting is now validated against the
  item type's workflow at set-time, independent of `--force` (which relaxes only the edge, never the
  vocabulary).

### Fixed

- **`sq check` no longer flags operator authors/assignees.** The check validated `author`/`assignee`
  against registered *roles* only, while the write gate accepts roles **or operators** — so any
  operator-authored item drew a bogus `not a registered agent` warning. The check now uses the same
  participant set as the gate.
- **Marker injection is now guarded.** Comments and sub-entity titles are scanned for sq marker tags
  (`<!-- sq:* -->`) at set-time and rejected if found, preventing users from breaking the parsing
  machinery via a quoted marker in a comment or title.
- **Stale inbox mentions are cleared.** Accepted decisions and published guides are terminal; they
  now leave the work views (`sq inbox <role>`) so agents don't revisit settled items looking for an
  update that won't come.

### Migration

**No migration required — `schema_version` stays `0.3`** (this release introduces no on-disk format change).

## [0.3.0] - 2026-06-10

### Added

- **Bugs carry a `severity`.** A bug's severity (`critical|high|medium|low|info`) is a validated
  per-type field: `sq bug <n> update --set severity=high` (`--unset severity` clears it), shown as a
  colored badge in `sq bug <n> show`. Invalid values are rejected with the valid list.
- **Sub-entities get a full `update` metadata entry point — `sq <type> <n> <kind> <k> update …`.**
  Mirroring item-level `update`, it sets `--title`, `--status` (+`--force`), and
  `--assignee`/`--clear-assignee` on any story/subtask/finding, **plus the two fields that were
  previously write-once at `add`**: a subtask's `--story`/`--no-story` (validated against the parent
  feature) and a finding's `--severity`. Every change re-renders the block's heading, its `:head`
  badges, and the parent's summary-table row from the stored value.
- **Item bodies are sq-managed too — the workflow needs no hand-editing.** Set or revise any item's
  body with `sq body <ID> -m "…"` / `--file PATH` (`--file -` for stdin) / `--append`, set it at
  creation via the same flags on `sq create`, and read it with `sq show`. `--desc` now sets only the
  short one-line **summary** (shown in `sq list`); it no longer seeds the body, so the two never
  drift. (Role/skill bodies stay generated from their fields.)
- **Items record an `author`** — the registered agent who created them. `sq create` now requires
  `--author <slug>`, and the author must be a registered agent (a role in the squad) or it's
  rejected. Roles/skills self-author; `sq show` displays it and `sq check` warns if an author's role
  was later removed. (Distinct from `--assignee` = who's responsible.)
- **`sq update` is the one metadata entry point.** Beyond title/description/assignee/labels it now
  sets `--author`, `--status` (validated; `--force`), `--parent`/`--no-parent`, and **per-item-type
  fields** via `--set key=value` / `--unset key` (e.g. a review's `target_ref`, a guide's `tags`, a
  role's `model`/`color`), validated against a declared schema. Editing a role/skill regenerates its
  `.claude` pointer.
- **`sq comment` can target a review finding** (`--finding F1`), completing comment support across
  every sub-entity — user stories (`--story`), subtasks (`--subtask`), and findings (`--finding`).
- **Human-readable header on every sub-entity.** Each story / subtask / finding now carries an
  sq-owned `:head` region under its heading that renders its state prettily — `**Status:** 🟡 In
  Progress`, `**Assignee:** <full name>`, `**Severity:** 🟠 High` (findings), `**Implements:** US2 —
  <story title>` (subtasks) — kept in sync on every status/assignee change while the machine values
  stay in `:meta`. It's a template (`subentities/head.md.j2`); add an attribute by passing a value
  from `set_head` and adding a line.
- **Sub-entity bodies are sq-managed — no manual markdown editing.** Set or revise a user story /
  subtask / finding body with `sq story|subtask|finding body <ID> <LID> -m "…"` (repeatable
  paragraphs) or `--file PATH` (`--file -` reads stdin), `--append` to add to it; set it at creation
  via the same flags on `add`; and read the whole block (meta + body + discussion) with
  `sq <kind> show <ID> <LID>`. Bodies containing sq marker comments are rejected.
- **`assignee` is validated against the roster.** Setting an item's assignee (at `create` or via
  `sq update --assignee`) now requires a registered agent, just like `author`; `sq check` warns when
  an assignee's role was later removed.
- **Sub-entities carry their own assignee**, so a task's subtasks (and a feature's stories, a
  review's findings) can be parcelled out to different agents. Set it at creation (`--assignee
  <slug>`) or reassign with `sq subtask|story|finding assign <PARENT> <LID> <slug>` (`--clear` to
  unassign); it's validated against the roster, stored in the block's sq-owned `:meta` region, and
  shown in both `… list` and the parent's roll-up summary table.
- **Items carry a `priority`.** An optional `priority` (`urgent|high|medium|low`) is a first-class
  field, independent of status: set it at creation (`sq create … --priority high`) or with
  `sq <type> <n> update --priority high` / `--no-priority`. It shows as a colored badge in
  `sq <type> <n> show` and a new **Priority** column in `sq list`, and filters with
  `sq list --priority high`. (Additive frontmatter field — old items read back as unset and no
  migration is needed.)
- **Closed items are hidden by default.** `sq list` and `sq tree` now show only open items; pass
  `--all`/`-a` to include closed (Done/Cancelled/…) ones, or filter directly with an explicit
  `--status`. This keeps day-to-day views focused without deleting anything — items are "archived"
  simply by reaching a terminal status.
- **`sq search TEXT`** — find items by matching their title, summary, and body/discussion prose
  (case-insensitive), printed with the matching lines (`--type` to scope, `--json` for machine use).
- **`sq blocked`** — surface what's stuck: open items that have at least one *open* blocker via the
  `blocks` ref kind (`A ref add B --kind blocks` reads "A blocks B"), each shown with its blockers.
- **`sq mine [ROLE]`** — items assigned to a role (defaults to the squad's configured default role);
  honors the same closed-hiding (`--all` to include) as `sq list`.
- **`sq workload`** — open/closed/total work-item counts per assignee, busiest first.
- **`sq tree … --json`** — emit the nested subtree (`id/type/status/priority/assignee/blocked` +
  `children`), honoring a root id and `--all`. This is the one read an orchestrating agent uses to
  see a feature's whole state and decide what to do next.
- **Precise per-actor guidance in every item skill.** Each `sq-<type>` skill now gives every actor
  that touches the item (e.g. tech-lead / developer / reviewer / QA on a task) structured guidance
  under fixed labels — **Enter** (what to read first), **Do** (the steps, with concrete `sq`
  commands), **Hand off** (the trigger + target), and **Watch for** (scope discipline) — instead of
  a one-line summary. The shared **developers** section appears only once the squad has a
  `<tech>-dev` role (added/removed live with `sq dev add` / `sq role rm`).
- **`greeting` skill — agents greet the operator on arrival.** A new always-preloaded managed skill
  has every role, when a human opens a conversation, detect who they're talking to (Claude user /
  `git config user.name` → `op-<firstname>`), register them if needed (`sq operator add`), then greet
  — **matching the human's tone** ("Hello Robert" → "Good morning, Alice"; "Hi Mara!" → "Hey
  Alice!"), saying how they can help, and giving a quick read of the project. Subagents spawned for
  internal work skip the greeting. (Preloaded alongside `squads` for all roles.)
- **Operators — humans as first-class participants.** A new `operator` item type represents the
  people who work on the project (slug `op-<firstname>`). Register them with `sq operator add
  "<name>"` (`list`/`rm` too); an `op-` slug is then a valid `--author`/`--assignee` on items and
  sub-entities and `--as` on comments — the assignment gates accept registered **roles or
  operators**. Operators are not agents: never spawned, no `.claude/agents` pointer, no skills, and
  they're excluded from `workload`. `CLAUDE.md` gains an "Operators (people)" roster and a
  session-start ritual (work out who the human is, `sq operator list`, ask to register, **ask if
  unsure**). Additive — no migration.
- **Reinforced role entry points.** Every role's definition now carries the operating contract
  (keep an item's status current; hand back through a `sq comment`; follow your `sq-<type>` skill's
  section), and the `squads` skill gains a **"Working directly with the operator"** rule for when the
  operator bypasses the manager. The greeting/impersonation also accepts a role by *function*
  ("the dotnet dev" → `dotnet-dev`), not just by name.
- **Orchestration-loop guidance.** The generated `CLAUDE.md` now teaches the manager/default agent
  to run work as a loop — *assess via `sq` → delegate by spawning the specialist as a Claude Code
  subagent (`subagent_type: <role-slug>`) with the item ID → integrate the result → repeat until
  done*. `@mention`/`inbox` are framed as the durable record of who-was-asked-what; the spawn is the
  handoff. (Each squads role is already a spawnable subagent with its model/skills preloaded.)

### Changed

- **Prose edits are now concurrency-safe.** `sq comment`, `sq <type> <n> body`, and sub-entity
  bodies write the `.md` file *inside the index lock* (atomically with the `updated_at` bump),
  instead of an unlocked read-modify-write. Parallel `sq` callers — e.g. several dev subagents
  working at once — can no longer silently drop each other's comments or body edits.

- **BREAKING — the sub-entity shortcut verbs are removed; `update` is the single entry point.**
  `sq <type> <n> <kind> <k> status …`, `… assign …`, and the subtask `… done` are gone — use
  `… update --status …` (`--force` to override / replace `done`), `… update --assignee …`
  (`--clear-assignee`). The remaining sub-entity verbs are `show`, `update`, `body`, `comment`.
  (Item-level `status` is unaffected.)
- **Sub-entity state moved from body markers to frontmatter.** A story / subtask / finding's machine
  state — status, assignee, severity, mapped story, and title — is now a typed `subentities:` list in
  its parent item's YAML frontmatter, single-sourced and pydantic-validated like every other item
  field. The index therefore **sees sub-entities** (so `sq list`/`sq check` and transition validation
  read them without parsing bodies), and `sq repair` reconstructs them from frontmatter. Only the
  prose (`:body` / `:discussion`) and the derived presentation (`:head` badge line, `:summary` table)
  stay in the markdown body; the per-block `:meta` region is gone. (`sq <type> <n> show` and the
  `… <kind> show` views are unchanged.)
- **BREAKING — resource-oriented CLI grammar.** Items are now addressed as `sq <type> <number>
  <verb> …`, with sub-entities nested one level deeper. The flat and sub-app commands are removed and
  replaced:
  - `sq show/update/status/comment/body ID` → `sq <type> <n> show|update|status|comment|body`
  - `sq link/unlink ID` → `sq <type> <n> update --parent/--no-parent`
  - `sq refs ID` / `sq ref add FROM TO` → `sq <type> <n> refs` / `sq <type> <n> ref add TARGET`
  - `sq story|subtask|finding add PARENT …` → `sq <type> <n> add-story|add-subtask|add-finding …`
  - `sq story|subtask|finding <op> PARENT LID …` → `sq <type> <n> story|subtask|finding <k> <op> …`
  - `sq guide add` → `sq create guide`
  The number may be bare (`35`), padded (`000035`), or the full id (`TASK-000035`); the type word
  validates it. `create`, `list`, `tree`, `init`/`adopt`, `check`/`repair`/`sync`, `docs`,
  `workflow`, `inbox`, and the `role`/`dev`/`skill`/`migrate` groups are unchanged. (Examples
  throughout the Added section below use the new grammar.)
- **An item's integer `sequence_id` is now its real identity; the formatted `id` is derived.**
  `Item.sequence_id` (the global counter number) is a stored field persisted in both `.md`
  frontmatter and `.squads.json`; `id` (`TASK-000007`) is computed from `type` + `sequence_id`. The
  index keys items by `sequence_id` (`items: {7: …}`) rather than the formatted id. The loader
  normalizes legacy full-id index keys, and the **0.2 → 0.3 migration backfills `sequence_id`** into
  existing frontmatter, so existing squads upgrade cleanly via `sq migrate up`.
- **`schema_version` now tracks the alpha release that introduced the schema** (`"0.1"`, `"0.2"`)
  instead of an opaque integer counter (`1`, `2`), in both `.squads.toml` and `.squads.json`. Existing
  alpha squads must update the value by hand (`schema_version = 2` → `schema_version = "0.2"` in
  `.squads.toml`; `sq repair` then restamps `.squads.json`).
- **Comments read better with multiple points.** Each repeated `-m` is its own bullet under the
  timestamp (now shown in the help + agent guidance), and a multi-line `-m` value keeps its
  continuation lines nested under its bullet — including fenced code blocks (internal blank lines
  stay indented) — instead of breaking the list.

### Migration

- **`schema_version` → `"0.3"`.** `sq migrate up` applies the new **0.2 → 0.3** step automatically:
  it backfills the integer `sequence_id`, **lifts each sub-entity's `:meta` state into the new
  `subentities:` frontmatter list and deletes the `:meta` markers**, and renders the `:head` region
  (status / assignee-name / severity / story badges), resolving names from the role files and story
  titles from parent features. Fully automatic and idempotent. (An out-of-date squad is gated until
  you run it — `sq migrate help` / `chlog` list every step.)

### Fixed

- **Global `--at` / `--dir` now work after the subcommand too** (e.g. `sq create task "X" --at
  2024-01-01`), not only before it. They're hoisted to the front at the entry point, so position no
  longer matters.

## [0.2.0] - 2026-06-08

### Added

- **`sq docs`** — list the bundled documentation, and `sq docs <name>` prints any page straight to
  the terminal so agents (and humans) can read the full docs **offline, with no fetch**. Raw
  markdown by default; `--rich` pretty-prints. The docs ship inside the wheel as package data.
- **Status state machines for sub-entities, tracked by `sq`.** Subtasks and user stories now have a
  status (`Todo → InProgress → Done`, + `Blocked`, `Cancelled`): `sq subtask status TASK STn <Status>`,
  `sq story status FEAT USn <Status>` (transitions validated; `--force` to override).
- **Review findings are first-class.** `sq finding add REV "…" --severity high|…`,
  `sq finding status REV Fn <Status>` (`Open → Fixed → Verified`, + `WontFix`), `sq finding list`.
- **`sq`-managed summary tables.** Tasks/features/reviews carry a top-of-section table rolling up
  their subtasks/stories/findings (status, and severity for findings), regenerated on every change.

### Changed

- **Ref kinds are now stored inline with the edge.** A reference is `ID` (the default `related`) or
  `ID:kind` (e.g. `BUG-000009:fixes`) in an item's `refs`, replacing the separate
  `extra.ref_kinds` map. The `sq ref`/`sq refs` interface is unchanged. (`schema_version` → 2.)
- **Sub-entity state lives in scoped markers, not the heading.** Each subtask/story/finding block
  keeps its status (and severity/story map) in an sq-owned `:meta` region — the heading is plain
  prose. `subtask done` is kept as a shortcut.
- **Discussion sections now carry a heading** at the right depth — `##` at item top level, `####`
  inside a story/subtask/finding.

### Migration

- On an out-of-date squad, `sq` **stops and tells you to run `sq migrate up`**, the new migration
  command group: `up` runs the automatic runners (rebuild index + restamp), `help` lists the
  migration changelog, and `chlog vA..vB` prints the manual steps for a release range. The `v1 → v2`
  runner folds legacy `extra.ref_kinds` into inline refs, upgrades sub-entity headings (`[ ]`/`[x]`
  checkboxes and `(→ USn)` suffixes) into the new `:meta` regions, builds the summary tables, and
  gives legacy reviews an empty findings container.
- **One manual step (LLM-assisted):** a pre-2 review's free-form prose findings can't be structured
  automatically — `sq migrate up` prepares the container, then an agent recreates each as
  `sq finding add … --severity …`. Read it with `sq migrate chlog v0.1.1..v0.2.0`.

## [0.1.1] - 2026-06-08

### Fixed

- **Windows: every write command crashed** (`sq init`, `create`, `status`, `repair`, …). The atomic
  index write called `os.fsync()` on a read-only file handle, which Windows rejects with
  `OSError [Errno 9]`; it now fsyncs the write handle that produced the bytes.
- **Windows: non-ASCII output crashed** under the legacy cp1252 console (`UnicodeEncodeError` on
  `→`/`•`/`—`, e.g. from `sq workflow`). The CLI now forces UTF-8 stdio on Windows.
- **Windows: reading squad files crashed or silently corrupted non-ASCII content.** `sq check`
  (and any read path) used `Path.read_text()` with no encoding, so on a non-UTF-8 locale (e.g.
  cp1252) a heading such as `### ST1 — … (→ US1)` either raised `UnicodeDecodeError` or decoded the
  `→` to mojibake — breaking subtask/story validation. All file I/O is now pinned to
  `encoding="utf-8"`.

## [0.1.0] - 2026-06-08

Initial release.

### Added

- **CLI** (`squads` / `sq`) for managing a team of AI agents as identified markdown with a
  JIRA-like, globally-unique ID system. Item types: epic, feature, task, bug, decision (ADR),
  review, guide, role, skill.
- **Index** — a single `<squad>/.squads.json` with one global monotonic counter and all item
  metadata; filelock'd, atomic writes. The `.md` frontmatter is the durable source of truth; the
  index is rebuildable (`sq repair`, `sq repair --renumber`).
- **Commands** — `init`, `adopt`, `create`, `list`, `show`, `tree`, `link`/`unlink`, `update`,
  `status`, `comment`, `story`, `subtask`, `ref`/`refs`, `inbox`, `role`, `dev`, `skill`, `guide`,
  `check`, `repair`, `sync`, `workflow`. Global `--dir` (target a squad) and `--at` (forge
  timestamps for history-preserving migration).
- **Workflow** — per-type status machines with validated transitions; parent rules
  (task → feature, feature → epic); typed forward refs with computed backrefs; user stories &
  subtasks with their own discussion; `@mention` inbox.
- **Claude Code backend** — thin `.claude/` pointers to real definitions under the squad folder,
  bundled `squads` skill + per-item-type skills, a managed `CLAUDE.md` section with
  greeting-based impersonation, and a non-clobbering `settings.json` merge.
- **8 bundled roles** + on-demand stack developers (`sq dev add`); the role↔item-type playbook.
- **Docs** — README, plus `docs/` (workflow, internals, adoption, agents, tutorial, roles,
  backends, recipes, faq); `py.typed`; MIT licensed.

[0.13.0]: https://github.com/TheCaptainCat/squads/compare/v0.12.3...HEAD
[0.12.3]: https://github.com/TheCaptainCat/squads/compare/v0.12.2...v0.12.3
[0.12.2]: https://github.com/TheCaptainCat/squads/compare/v0.12.1...v0.12.2
[0.12.1]: https://github.com/TheCaptainCat/squads/compare/v0.12.0...v0.12.1
[0.12.0]: https://github.com/TheCaptainCat/squads/compare/v0.11.1...v0.12.0
[0.11.1]: https://github.com/TheCaptainCat/squads/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/TheCaptainCat/squads/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/TheCaptainCat/squads/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/TheCaptainCat/squads/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/TheCaptainCat/squads/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/TheCaptainCat/squads/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/TheCaptainCat/squads/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/TheCaptainCat/squads/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/TheCaptainCat/squads/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/TheCaptainCat/squads/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/TheCaptainCat/squads/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/TheCaptainCat/squads/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/TheCaptainCat/squads/releases/tag/v0.1.0
