---
id: ADR-1172
sequence_id: 1172
type: decision
title: 'CLI surface tests: one case per parameter, guarded coverage'
status: Accepted
author: architect
refs:
- FEAT-1096
- ADR-1025
- ADR-1225
- ADR-1250
description: 'CLI tests in-process on the bundled squad and a full-override squad:
  one case per parameter, shared registrations tested once, a marker-based coverage
  guard'
created_at: '2026-10-27T21:25:41Z'
updated_at: '2026-10-29T19:25:55Z'
---
<!-- sq:body -->
## Context

The repository keeps only its `tests/meta` guards and the shared helpers: `tests/_squads.py` (a squad built once per module, copied per test), `tests/_help_tree.py` (a walk of the live Typer command tree), `tests/_helpers.py`, `tests/conftest.py` and the root `conftest.py`. The previous suite reached about 16,000 tests and about 50 minutes on the Windows CI runner. Most of that volume came from cross products of parametrised tables (position x shape x layer), and the same seam was asserted at several layers.

The first tests to rebuild are CLI tests: every command, every parameter, run against the engine and the bundled spec. Measured on 2026-10-27, outside any squad (bundled vocabulary), with `_help_tree.command_nodes()`:

- 344 commands (groups included), 267 leaf commands, 1,079 (command, parameter) pairs counting group callbacks.
- The nine work-item groups come from one builder, `build_item_app`. Each has 11 verbs, plus 3 more on a type that hosts a sub-entity kind (`add-<kind>`, `<kind>`, the plural listing). `retype` and `remove` exist only on non-roster types.
- The comment verbs come from one registrar, `register_comment_verbs`, and are mounted on every item group, every sub-entity group and the `role`, `skill` and `operator` groups.
- `sq create <type>` takes the shared options on every type, plus one option per badge field and per create-time attribute the type declares. A create-time attribute is a settable `str`, `list` or `date` attribute in `[items.<type>.attributes]`; its option is `--<key>` with underscores as dashes, and a `bool` attribute gets none. In the bundled spec, `guide` declares `tags` and `tech` (`--tags`, `--tech`), `milestone` declares `target_date` (`--target-date`) and `review` declares `target_ref` (`--target-ref`).
- Sub-entity verbs take the same options on all three bundled kinds, except the options derived from a kind's declarations: the mapping option on a kind that maps to its parent (`subtask update --story/--no-story`), a field option per declared field (`finding update --severity`), and `--deferred-to` on a kind with a deferred status.
- Once item types, sub-entity kinds and comment hosts are each folded onto one key, 1,079 pairs become about 374, on about 111 leaf commands.

The expensive axis is therefore repetition of one registration across hosts, not the number of parameters.

## Decision

### 1. One case per parameter, combinations only where parameters interact

Each (command, parameter) pair has one case where the value takes effect, plus its boundary refusals: a value outside the accepted set, a missing required value, a malformed value. Required arguments and options appear in every case of their command because the command cannot run without them; that is not a combination.

A modifier parameter only becomes observable alongside a write: `--as`, `--json`, `--yes`, `--force`, `--append`. Its case runs the smallest write the command accepts, and asserts the modifier's own effect. That is not a combination either.

Two parameters of one command **genuinely interact** when the outcome for one depends on the value of the other:

- they exclude each other, or one cancels the other (`--parent` with `--no-parent`, `--assignee` with `--clear-assignee`, `-m` with `--file`, `--onto` with `--by`);
- one reads the other's value (`--story` resolved against the parent given with `--parent`, `--priority` with `--min-priority` on one listing, `--sort` deciding the order a `--json` array prints in);
- they touch the same value, so order or precedence decides the result (`--add-label` and `--rm-label` naming the same label, `--set` and `--unset` naming the same attribute).

Two filters that narrow the same listing independently do not interact: each is tested alone, and their intersection is not a row. A combination test names the interaction in its function name (`test_update_refuses_parent_with_no_parent`), never only the parameters.

### 2. A shared registration is tested once, on one host

A verb set that one builder or registrar mounts on several hosts is tested on one host. The other hosts are held by a `tests/meta` guard, not by repeated tests.

- **Work-item verbs** are tested on the reference type, `task` in the bundled squad (see Scope). It is non-roster, so it has `retype` and `remove`. It hosts a sub-entity kind (`subtask`) whose `--story` option resolves against another item (its parent feature's stories). It also carries a parent rule that `sq check` enforces. No other bundled type exercises more of the builder.
- **Sub-entity verbs** are tested on `task subtask`. A parameter that only some kinds carry is tested on a host that carries it: `--severity` and `--deferred-to` on `review finding`.
- **Comment verbs** are tested on the `task` item host. Addressing through the other host kinds is tested once each: sub-entity, role, skill and operator. Each of those cases covers the address, not the verb's parameters again.
- **`sq create <type>`** is tested on `task`. A parameter derived from a type's own declarations is tested on a type that declares it: `--tags` and `--tech` on `guide`, `--target-date` on `milestone`, `--target-ref` on `review`. No type is special-cased: every create command is built from the spec, and no test or guard names a type to exempt it.
- **Per-type differences that the spec decides**, such as which transitions a lifecycle allows, are not CLI surface. The `status` verb is tested on `task`'s lifecycle: one allowed transition and one refused transition. Whether every bundled lifecycle is well formed is the spec loader's concern, not this suite's.

The verb-set guard is a new `tests/meta` module. It enumerates the tree with `_help_tree.command_nodes()` and reads the bundled spec. For every declared work-item type it asserts two things:

- The type's verb set equals the reference type's verb set, minus what the spec decides: the `add-<kind>`, `<kind>` and plural verbs are present exactly when the type hosts a kind, and `retype`/`remove` are present exactly when the type is not roster.
- Each verb's parameter names equal the reference type's, plus the parameters derived from the type's own declarations: on `create`, one option per declared badge field and per create-time attribute; on sub-entity verbs, the kind-specific options. The guard computes both sets from the spec, and fails on a create command the shared builder did not build.

The same guard asserts that every comment host exposes the same comment verbs with the same parameters. The guard derives its expectations from the spec and stores no list of types. The existing `test_roster_body_verbs_share_one_registration` keeps holding the roster body verbs.

### 3. Coverage is declared by a marker and enforced by a guard

A CLI test declares what it covers with a marker whose arguments are string literals:

```python
@pytest.mark.covers("<type> update", "--title")
def test_update_replaces_the_title(...): ...

@pytest.mark.covers("<type> update", "--parent", "--no-parent")
def test_update_refuses_parent_with_no_parent(...): ...
```

- **Command key.** The command's path under `sq`, as `_help_tree` yields it. A work-item type name is written `<type>`, a sub-entity kind `<kind>` (`add-<kind>`, `<kinds>` for the plural listing), and the segments up to a mounted comment group `<host>` (`<host> comment edit`). The hidden `_addr` dispatcher segment that `_help_tree` yields is dropped (`task comment _addr edit` is `<host> comment edit`, `role _addr update` is `role update`), and the dispatcher's argument (`HASH`, `<slug|id|n>`) belongs to the parent key. The root callback is the empty key `""`. A group callback's own parameters belong to the group's key: `<type>` for `N`, `<host> comment` for `-m`, `--file` and `--as`.
- **Parameter name.** An option is named by its first long flag (`--title`); its short alias is not a separate parameter. An argument is named as the usage line prints it (`N`, `TITLE`), which is Click's `human_readable_name`. A parameter derived from a spec declaration is named by its derivation, so one marker holds in every squad: `--<field>`, `--no-<field>` and `--min-<field>` for a badge field, `--<target-kind>` and `--no-<target-kind>` for a sub-entity mapping, and `--<attribute:str>`, `--<attribute:list>` or `--<attribute:date>` for a create-time attribute of that kind. The `invoke` fixture records a derived flag under its derivation name.
- **Every leaf command is declared**, not only every (command, parameter) pair. A leaf with no parameters (`ui`) is declared with its command key alone: `@pytest.mark.covers("ui")`.
- **The key alone declares the bare call:** the command run with none of its own parameters. It is valid on any leaf and required only on a leaf with no parameters, so a leaf that gains a parameter keeps it: the case that runs plain `sq sync` stays `covers("sync")`, and the case that runs `sq sync --json` is `covers("sync", "--json")`. It goes stale only when the key goes.
- **Every CLI test declares.** Each test function in `tests/cli/` carries at least one `covers` marker. A test that runs no command of its own has no place in `tests/cli/`: a test of the suite's own fixtures belongs in `tests/meta/`.
- **A refusal declares the parameter it is about.** A case whose call is refused for a missing or malformed value declares that parameter (`covers("create <type>", "TITLE")` for a missing title), not a parameter the call happens to pass. A refusal squads raises itself names in its message the flag it refuses (`--as`, `--message`, `--force`), and the case declares that parameter in the same way.
- **One marker, several parameters**, is only for an interaction (rule 1). A test may carry several `covers` markers when it asserts each one's effect.

The **coverage guard** is a new `tests/meta` module:

- It enumerates the tree with `_help_tree.command_nodes()` for each test squad (see Scope), hidden parameters included, folding each node onto its key as above.
- It reads every `covers` marker from the CLI test modules with `ast`, without importing them.
- It fails, listing them, when a pair or a leaf command of the tree is declared by no test.
- It also fails when a marker names a pair or a key the tree no longer has (stale).
- It fails, listing them, on a test function in `tests/cli/` that carries no `covers` marker.
- It excludes only parameters squads does not declare: Typer's `--install-completion` and `--show-completion`. Click's `--help` is not a parameter of the tree, and the help-rule guard already holds it. The exclusion is a named constant in the guard, one reason per entry.

The marker is checked against what the test runs. The CLI `invoke` fixture resolves each argument list against the live tree and records the keys and (key, parameter) pairs it reached, plus the pair of the parameter a refusal names: one a Click usage error names (a missing or bad value), or, on a call that exits non-zero, one whose flag appears in the output, and the bare pair `(key, None)` for a call that passes none of its leaf's parameters, so a key-only marker is checked like any other. At teardown it fails the test when a declared key or pair is not among them. A marker cannot claim coverage its test does not exercise. This check is local to the test, so `-k`, `--lf` and xdist runs stay valid.

The guard proves that each pair has a test. It does not prove that the test fails when the parameter breaks. That proof is made once, when the test is written: break the parameter's effect, see the test go red, restore it. Review checks that this was done.

### 4. In-process, on a copied squad

Every CLI test runs `sq` in-process through Typer's `CliRunner` (the `runner`/`invoke` fixtures). It runs on its own copy of a squad built once per module (`copy_squad` and the builders in `tests/_squads.py`), under the frozen clock. No test starts a subprocess. A behaviour that is only observable in a separate process, such as the console-script entry point or environment latching at interpreter start, is outside this suite; it belongs to the cross-process set below. The autouse fixtures in `tests/conftest.py` stay in force for every test: the context reset, the plain-output environment, the empty starting directory and the item-file write ledger.

### 5. Assert what the user sees

A case asserts the exit code and the composed output: the whole message line or the JSON object, not a substring that would survive a wrong message. State is read back through the CLI: `sq <type> <n> show --json`, or the `--json` form of the listing or command concerned. A test never opens `.squads.json`, and opens an item file only for the hint named below. A test reads a file directly only when that file is the output the command under test produces for the user: the generated agent-facing files (`.claude/` pointers, the managed `CLAUDE.md` and `AGENTS.md` regions) written by `init`, `adopt`, `sync` and the roster verbs that regenerate pointers, and the override files that `sq override` scaffolds or restamps. One item-file read is allowed: a test may read the add and track hint that an item template scaffolds above the sub-entity region, since no sq output carries it. No other file is read; any other state goes through the CLI. A test writes an item file or `.squads.json` directly only to arrange a state that no CLI path can produce (a corrupt, legacy or drifted corpus for `repair`, `check`, `migrate`, `adopt` or `renumber`); its assertions still read state through the CLI.

### 6. Layout and names

CLI tests live in `tests/cli/`, one module per command group, named for that group's behaviour:

- `test_root_options.py` for the root callback;
- `test_item_verbs.py` for `<type> …`;
- `test_subentity_verbs.py` for `<type> <kind> …`;
- `test_comment_verbs.py` for `<host> comment …`;
- `test_create.py`, `test_list.py`, `test_role.py` and so on, one per remaining top-level group.

A top-level group with a single leaf may share a module with its nearest neighbour when both read the same squad fixture. Test function names state the behaviour. `test_test_names_carry_no_ticket_ids_or_process_words` and the ticket-reference guard already scan `tests/` and apply unchanged.

### Root and shared options

- **Root options** (`-C`, `--at`, `--version`, and the hidden removed `--dir`) belong to the root callback, key `""`. Each is covered once in `test_root_options.py`, on one ordinary command. They are not repeated per command.
- **`--json` and `--as`** are not root options. Each is declared once in `_cli/_common.py` but mounted per command, and each command's JSON payload and attribution is its own contract. So `--json` and `--as` are covered per command key, like any other parameter, with the modifier rule above.

### Coexistence with the `tests/meta` guards

The two guards above are added beside the existing ones and share `_help_tree.py`. The existing guards stay as they are, including the help-rule guard and its custom-vocabulary tree, which is a guard over the code, not a surface test. `test_shared_flags_are_declared_once` keeps holding the single declaration of `--json`, `--as` and the other shared flags. `test_squad_copies_are_isolated_in_any_order` keeps holding the copied-squad isolation that rule 4 relies on. `tests/meta/_roots.py` keeps scanning `tests/`, so `tests/cli/` is covered by the naming guards with no change.

### Scope: two squads

The suite runs on two squads, each built once per module and copied per test (rule 4): the **bundled squad**, with the bundled workflow spec, playbook and role catalog and no project override, and the **override squad**, whose workflow override drops every bundled work-item type, sub-entity kind and badge field and declares its own (ADR-1250 §10). One run uses one squad, selected for the whole run. CI runs the suite once per squad, each in its own job, under the time bound.

A case reaches its host through the squad's **profile**, never through a literal name: the reference type with its kind and target kind, a badge field, a kind with a field and a deferred status, a create-time attribute of each kind, and an alias. In the bundled squad the reference type is `task`, its kind `subtask` and its target kind `story`. A `tests/meta` guard resolves every profile entry against its squad's spec and fails on one that does not resolve, so no case skips for want of a host. The keys are type-agnostic (`<type>`, `<kind>`, `<host>`) and derived parameters are named by their derivation (rule 3), so one marker declares the same pair on both squads.

### Regression tests

Specific regression tests, one per verified bug, are a separate set in `tests/regressions/`. They follow the same rules for execution (rule 4), assertion (rule 5) and naming: each module and test is named for the behaviour the bug broke, never by its ticket. A regression test carries no `covers` marker. It neither counts toward nor replaces surface coverage, and a surface case is not removed because a regression test touches the same parameter. Each one is shown red against the unfixed code before it is kept. Their organisation beyond that is left to when they are written.

### The cross-process set

A behaviour belongs here only when no in-process test can observe it: it needs one process to start, find or outlive another, a signal, or the operating system's own way of spawning a process. Anything an in-process test can observe is tested in-process instead. These behaviours form a small, named set outside the surface suite: each test names the one behaviour it holds, and a behaviour joins only when it meets this condition. The set runs the real `sq` console script against a scratch squad and asserts as rule 5 does: exit code and whole output, state read back through `show --json`. It is named as rule 6 says. It carries no `covers` marker and neither counts toward nor replaces surface coverage. It runs in its own CI job on each OS.

The daemon's members are implicit start, discovery, fall back, no replay after a lost connection, Ctrl-C, and the detached spawn on Windows.

### The daemon's routes

The daemon's routes (ADR-1225) are a surface, but not (command, parameter) pairs. The mode-parity run covers every operation over HTTP, so route tests are kept only for what it cannot see: one case per row of the error table, a vocabulary mismatch on an unchanged and on a changed configuration, the OpenAPI document covering every operation, a partial read's envelope, the binding of each metadata header, a `GET` that does not mutate, and the admission negatives listed in ADR-1052. They follow rules 4 to 6: they run in-process, with the daemon's HTTP application served on a thread of the test process against a copied squad; they assert the whole response and read state back through the CLI; and they live in a module named for the behaviour of the route they hold. They carry no `covers` marker, because there is no pair for one to name.

### Mode parity

When the CLI answers the same commands in a second mode, currently the daemon's remote mode, parity is held by running this suite again in that mode, selected for the whole run, in its own CI job. Every existing case then asserts the same output in both modes. No case is added for parity.

### Time bound

Every CI test job runs in under 10 minutes; Windows, running the full suite, in at most 15. A target is met on an OS when every one of at least two runs on that OS is under it. The override-squad run, the remote-mode run and the cross-process set are CI test jobs under the same targets; the remote-mode run on Windows runs the full suite, so its bound is 15 minutes. There is no test-count ceiling and no row-budget guard: the time targets are the only bound, and review checks for cross products and duplicated cases.

## Why

- Repetition across hosts of one registration was the largest multiplier. Folding it onto one host with a structural guard replaces about 700 repeated pairs with one assertion per host, and the guard is stronger: a missing verb on any type fails it, where a per-type test only fails for the types someone remembered to list.
- `task` is the bundled type that exercises the most of the builder: retype, remove, a sub-entity kind, a cross-item option and a parent rule. A smaller type would leave verbs untested on the reference host.
- A marker with literal arguments can be read without running the suite. The guard is then cheap, works under partial runs, and a contributor can predict it: add an option, add a test that names it. Inferring coverage from recorded invocations alone would require a whole-suite run to decide and fail spuriously under `-k` and xdist. The invoke-fixture check closes the hole a bare marker leaves: a marker that no invocation honours.
- One case per parameter grows linearly with the surface (about 374 pairs). An effect case plus a few refusals each gives on the order of 1,000 to 1,500 in-process tests, well inside the Windows target at the earlier per-test cost.
- Reading state through `show --json` keeps the tests on the user's contract. A storage-format change then does not break surface tests, and a broken `show` does not hide behind a direct file read.

## Consequences

- Two new `tests/meta` guards: verb-set parity across hosts, and (command, parameter) coverage. The `invoke` fixture gains the marker cross-check, and `covers` is registered as a pytest marker.
- Adding an option to any command fails the coverage guard until a test declares it. Adding a verb to the builder or a registrar fails nothing per type: one test on the reference host covers it, and the parity guard holds the rest.
- A new bundled type needs no new surface tests unless it brings a parameter of a kind the suite does not test yet.
- The override squad doubles the surface run, as its own CI job; it adds no case. The regression set is later work; its location is fixed here.
- The daemon adds two CI jobs and no surface cases: the cross-process set on each OS, and the surface suite in remote mode. The coverage guard sees neither the cross-process set nor the route tests, since neither carries a `covers` marker.
- The guards prove that a case exists, not that it is strong: a vacuous case is still caught by the falsification step and by review.

## Options considered and rejected

- **A per-type parametrised table for the generic verbs.** It reproduces the cross product this decision removes, and is weaker than the parity guard for types nobody added to the table.
- **The custom-vocabulary type from `_help_tree.py` as the reference host.** One custom type inside the bundled spec does not exercise a squad whose vocabulary is entirely its own, and the literal guards cannot see what a surface run sees. The override squad (Scope) is a whole squad instead.
- **A central registry module listing every covered pair.** It is a second copy of the information the tests already carry, and it drifts from them. The marker sits on the test that does the covering.
- **Coverage inferred at session end from recorded invocations.** It is undecidable under partial or distributed runs. Recording is kept, but only as the per-test truth check of the marker.
- **Subprocess execution for realism.** It is the most expensive option on Windows. Its only extra reach is process start, which is outside this suite.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T21:26:03Z] `architect` Robert Architect:
  - Authored from the six rules op-pierre approved on 2026-10-27, scoped to the bundled spec per his refinement (relayed by manager). Beyond the rules: task is the reference host; parity guard derives expectations from the spec; covers marker with literal args read by ast, cross-checked per test by the invoke fixture; regressions go in tests/regressions without covers markers.
  - @manager ready for operator review; open questions are in the handback.
- [2026-10-27T21:28:19Z] `op-pierre` Pierre Chat:
  - Validated ADR-1172 and its three open points: the invoke fixture checks each declared pair was actually run; hidden parameters count as pairs and each gets a refusal test; --as is tested on every write command, not one case plus a guard.
- [2026-10-27T21:39:53Z] `architect` Robert Architect:
  - Rule 3 clarified per the FEAT-1173 manager decision (comment e4d4615): every leaf is declared (key-only covers for parameterless leaves), keys drop the hidden _addr segment, and the guard carries a shrinking pending list during the build.
- [2026-10-27T23:51:04Z] `architect` Robert Architect:
  - Rule 5 amended per REV-1198 F14: a test may read the output files its command produces (agent files from init/adopt/sync/roster regen, override files); item files and .squads.json stay CLI-only.
- [2026-10-28T19:15:58Z] `architect` Robert Architect:
  - Amended per the op-pierre rulings on FEAT-1140 (a6fcbde, 2026-10-28): rule 4 points out-of-process behaviours to a new "cross-process set" section (what qualifies, small and named, no covers marker, own CI job per OS; the daemon members listed); a "daemon command endpoint" section puts endpoint tests under rules 4-6 without covers markers; a "mode parity" section reruns the suite in remote mode in its own CI job with no new cases; the time bound places both new jobs under the existing targets; Consequences gains the two-jobs line.
- [2026-10-28T21:47:38Z] `architect` Robert Architect:
  - Amended in place on the acceptance of ADR-1225 (op-pierre 2f9041b, 3fbbd10), per its section 8; board rule 6, linked related. The section "The daemon's command endpoint" becomes "The daemon's routes". Route tests are kept only for what the parity run cannot see: error-table rows, a vocabulary mismatch on an unchanged and on a changed configuration, the OpenAPI coverage, a partial read's envelope, header binding, a GET that does not mutate, and the ADR-1052 admission negatives. They still follow rules 4 to 6, with no covers marker. The Consequences bullet now says "route tests". The cross-process set and the mode-parity job are unchanged.
- [2026-10-29T04:29:14Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for the REV-1235 test audit (35950c3, F29/F30), board rule 6. Status unchanged.
  - Rule 3: the key-only marker declares the bare call, meaning the command run with none of its own parameters. It is valid on any leaf and required only on a leaf with no parameters. A leaf that gains `--json` keeps `covers("<key>")` on its plain case and adds `covers("<key>", "--json")` for the JSON case. The parameterless example is now `ui` (`sync` gained `--json`).
  - Rule 3: every test function in `tests/cli/` carries at least one `covers` marker, and the coverage guard fails on one that has none. The `invoke` fixture records `(key, None)` for a call that passes none of its leaf's parameters, so a key-only marker is checked against the call like any other.
- [2026-10-29T04:53:22Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for the audit-fix questions on REV-1235 (F27-F31), board rule 6. Status unchanged.
  - Rule 3: a refusal case declares the parameter the refusal is about. The `invoke` fixture counts as reached the parameter a Click usage error names. A refusal squads raises itself about an absent value declares the key alone, or the parameters the call passes.
  - Rule 3: a test of the suite's own fixtures belongs in `tests/meta/`, not `tests/cli/`.
- [2026-10-29T05:08:56Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F38 (board rule 6). Status unchanged. Rule 3: a refusal that squads raises itself names the flag it refuses, and its case declares that parameter. The `invoke` fixture records a parameter whose flag appears in the output of a call that exits non-zero. There is no new marker argument.
- [2026-10-29T17:11:44Z] `architect` Robert Architect:
  - Prepared amendment for REV-1247 F3 (op-pierre a856fab, 2026-10-29: `create guide` is derived from the spec like every type). Body edit lands after the code; replacement text below.
    
    **Context, bullet 4.** Replace "`sq create <type>` takes the same options on eight types. `guide` differs: it takes `--tag` and `--tech`, and has no `--label`, `--priority` or `--ref`." with:
    
    > `sq create <type>` takes the shared options on every type, plus one option per badge field and per create-time attribute the type declares. A create-time attribute is a settable attribute in `[items.<type>.attributes]`. In the bundled spec, `guide` declares `tags` and `tech`, `milestone` declares `target_date` and `review` declares `target_ref`.
    
    **Rule 2, the create bullet.** Replace "**`sq create <type>`** is tested on `task`. A parameter only some types carry is tested on a type that carries it: `--tag` and `--tech` on `guide`." with:
    
    > **`sq create <type>`** is tested on `task`. A parameter derived from a type's own declarations is tested on a type that declares it, with one case per attribute kind the derivation handles. In the bundled spec those are `guide` for a list and a string attribute, and `milestone` for a date. No type is special-cased: no type has a hand-written create command, and no test or guard names a type in order to exempt it.
    
    **Verb-set guard, second assertion.** Replace "Each verb's parameter names equal the reference type's, except the parameters derived from the type's own declarations: create-time attributes and the kind-specific sub-entity options." with:
    
    > Each verb's parameter names equal the reference type's, plus the parameters derived from the type's own declarations: on `create`, one option per declared badge field and per create-time attribute; on sub-entity verbs, the kind-specific options. The guard computes both sets from the spec and has no branch for a hand-written command.
    
    **Form.** Amend in place, Status unchanged, and record it with an "Amended in place" comment. This follows board rule 6 (a decision that is partly wrong is amended) and this ADR's own record: 08ce16a, dc10aa3, 4c1a406, 3bb44e7, 8298874, e107804 and d2fb3ec are all in-place amendments. Only the guide exception changes. Rules 1-6 still stand, so a superseding ADR is not warranted.
    
    **For the dev (TASK-1246), not part of the ADR text:**
    - The rule reaches `milestone` (`--target-date`) and `review` (`--target-ref`), not only guide.
    - A flag named after its key makes guide's `--tag` become `--tags`. That renames a published flag. Keeping `--tag` would need a per-key flag name in the spec grammar, which is a separate decision. My recommendation: `--<key>` plus a CHANGELOG line, with op-pierre's OK.
    - The guard branch to drop: `CREATE_CORE` and the else-branch of `create_problems` in `tests/meta/test_every_work_item_type_and_comment_host_exposes_the_reference_verbs.py`. `test_dedicated_create_flags_stay_settable_via_generic_set.py` reads `guide` by name and should iterate over every creatable type.
    
    **Other type literals in `src/squads/_cli` (reported only, not fixed):**
    - `_create.py:304`, `:365`, `:368-411`: the guide exclusion, `_STATIC_CREATE_TYPES` and the hand-written command with its aliases. This is the F3 scope.
    - `_items.py:897` and `:1016`: `resolve_local_id(story, "story")`. `--story` is gated by the spec's `maps_parent_story`, but it resolves against the literal kind `story`, so a project that renames the story kind breaks it. The comment at `:895` calls this "a bounded built-in". Under the rule above it is a special case, and it should resolve against the kind the parent type hosts.
    - No other work-item type literal appears in `_cli`.
    
    @manager
- [2026-10-29T17:28:46Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1247 F3 (op-pierre a856fab; flag naming per the operator ruling relayed with e3bb9356 and 14c77354). This follows board rule 6 and supersedes the plan in d5e503c. Status unchanged.
    - Context: `sq create <type>` takes the shared options plus one option per badge field and per create-time attribute. A create-time attribute is a settable `str`, `list` or `date` attribute. Its flag is `--<key>` with underscores as dashes, and a `bool` attribute gets no flag. The bundled flags are `--tags` and `--tech` on guide, `--target-date` on milestone and `--target-ref` on review. The guide exception is gone.
    - Rule 2: a parameter derived from a type's declarations is tested on a type that declares it, and every derived flag is named. No type is special-cased.
    - Verb-set guard: it adds the derived parameters computed from the spec, and fails on a create command the shared builder did not build.
    - Consequences: a new type needs new surface tests only for a parameter of a kind the suite does not test yet.
- [2026-10-29T19:02:53Z] `op-pierre` Pierre Chat:
  - 2026-10-29: rule 5 exception: a test may read the scaffolded add/track hint from an item file, since no sq output carries it (BUG-1248 tests).
- [2026-10-29T19:04:38Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 per op-pierre b819805 (board rule 6). Status unchanged. Rule 5: a test never opens `.squads.json`; it may open an item file only to read the add and track hint an item template scaffolds above the sub-entity region, since no sq output carries it. Any other item state still goes through the CLI.
- [2026-10-29T19:25:55Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 per op-pierre ca59f6b on FEAT-1249 (the audit override squad becomes a permanent test squad and the CLI surface suite also runs on it), board rule 6, linked related to ADR-1250. Status unchanged.
    - "Scope: bundled spec only" becomes "Scope: two squads": the bundled squad and an override squad that drops every bundled work-item type, kind and field. One squad per run, one CI job each. Cases reach their host through a per-squad profile, held by a new `tests/meta` guard.
    - Rule 3: a derived parameter is named by its derivation (`--<field>`, `--no-<field>`, `--min-<field>`, `--<target-kind>`, `--no-<target-kind>`, `--<attribute:KIND>`), so one marker holds on both squads; the coverage guard enumerates each squad's tree.
    - Context, rule 2, the time bound, Consequences and the rejected custom-type option follow.
<!-- sq:discussion:end -->
